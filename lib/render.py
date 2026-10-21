"""Block registry and page shell. A page is an ordered list of block functions per tab; a block returns a dict or None (None = no heading, no source line, nothing).
Visible text is a source value with unit and time, a label from this file, or a verbatim source string (escaped). No composed sentences.
"""
import statistics, os, re, json, math, collections, hashlib, datetime, zoneinfo
from lib.common import *

SOURCES = {s["id"]: s for s in json.load(open(os.path.join(DATA, "sources.json"), encoding="utf-8"))["sources"]}
CSS = open(os.path.join(ROOT, "templates", "site.css"), encoding="utf-8").read()
LABELS = {"00010": "Water temperature", "00300": "Dissolved oxygen", "63680": "Turbidity", "00400": "pH", "00095": "Specific conductance", "99133": "Nitrate plus nitrite", "00045": "Rain at the gauge (precipitation)", "00055": "Water velocity", "72255": "Water velocity", "00480": "Salinity"}
UNITS = {"degC": "°C", "deg C": "°C", "mg/l": "mg/L", "_FNU": "FNU", "uS/cm": "µS/cm", "pH Units": "pH units", "ft3/s": "cfs"}
TAGS = {"agency": "Agency data", "live": "Live gauge", "official": "Official NWS", "model": "Model guidance", "hist": "Historical record", "map": "Mapped layer", "obs": "Weather station", "calc": "Computed"}
PADMAN = {"USFS": "US Forest Service", "NPS": "National Park Service", "BLM": "Bureau of Land Management", "FWS": "US Fish and Wildlife Service", "SDNR": "State natural resources agency",
          "SFW": "State fish and wildlife agency", "SPR": "State parks", "SLB": "State land board", "LOC": "Local government", "CITY": "City", "CNTY": "County", "NGO": "Nonprofit", "PVT": "Private",
          "TRIB": "Tribal", "REG": "Regional or county agency", "UNK": "Unknown manager", "UNKL": "Unknown manager", "JNT": "Joint management", "DOD": "Department of Defense", "USACE": "Army Corps of Engineers"}
ACCESS = {"OA": "Open access", "RA": "Restricted access", "XA": "Closed", "UK": "Access unknown"}
DISCLAIMER = ("Percentile is estimated from USGS published daily percentiles. Readings are provisional until USGS reviews them. Not endorsed by USGS, NOAA or the National Weather Service. "
              "Not for navigation or safety-of-life decisions; the absence of an alert is not a statement that conditions are safe.")


IGNORED_ALERTS = {"Test Message", "Administrative Message"}


ADS = False  # the empty ADVERTISEMENT slots render only when an ad network is live
PREVIEW = False  # build.py --preview: show blocks whose source is not cleared, into dist_preview/ (review only, never published)


class CriticalFail(Exception):
    pass


def tzl(dt, zone, date=True):
    d = dt.astimezone(zone)
    s = d.strftime("%b %d, %I:%M %p %Z") if date else d.strftime("%I:%M %p %Z")
    s = s.replace(" 0", " ", 1).lstrip("0").replace("  ", " ")
    return s.replace(" ", "\u00a0").replace(",\u00a0", ", ")  # a long date wraps after the comma, never inside the time


def age_text(dt, now):
    m = int((now - dt).total_seconds() / 60)
    return "%d min" % m if m < 180 else ("%.0f h" % (m / 60) if m < 2880 else "%d d" % (m // 1440))


def hours_old(iso_s, now):
    try:
        return (now - parse_t(iso_s)).total_seconds() / 3600
    except Exception:
        return None


QUAL = {"ICE": "ice at the gauge, reading affected", "EQUIP": "equipment problem", "ESTIMATED": "estimated, not measured", "BACKWATER": "backwater from downstream, flow uncertain",
        "RATINGDEV": "flow rating under review", "SEASONAL": "seasonal gauge", "DISCONTINUED": "discontinued", "UNAVAIL": "reading unavailable"}


def qual_text(r):
    """USGS qualifier on one reading, in plain words; '' when none. The flag is printed wherever the number is: an iced gauge must never read as a plain number."""
    q = (r or {}).get("qualifier")
    if isinstance(q, str):
        q = [q]
    if not isinstance(q, list):
        return ""
    words = [QUAL.get(str(x).upper(), str(x)) for x in q if str(x).strip()]
    return ("USGS flag: " + "; ".join(esc(w) for w in words)) if words else ""


def series(rec, code):
    out = []
    for r in rec["usgs"]["rows"]:
        if r["parameter_code"] == code:
            try:
                if float(r["value"]) > -900:  # USGS sentinel values (-999999) are not readings
                    out.append((parse_t(r["time"]), float(r["value"]), r))
            except (TypeError, ValueError):
                pass
    out.sort(key=lambda x: x[0])
    return out


def oscillating(fl):
    """True when the last 48 h of flow holds 3 or more separate peaks of at least 20% of the mean (tidal or other sub-daily cycles): a 24 h change then compares two phases of a cycle."""
    t1 = fl[-1][0]
    hrs = collections.OrderedDict()
    for t, v, _ in fl:
        if t >= t1 - datetime.timedelta(hours=48):
            hrs.setdefault(int(t.timestamp() // 3600), []).append(v)
    h = [sum(v) / len(v) for _, v in sorted(hrs.items())]
    if len(h) < 40:
        return False
    mean = sum(h) / len(h)
    if mean <= 0:
        return False
    peaks = 0
    for i in range(4, len(h) - 4):
        if h[i] >= max(h[i - 4:i + 5]) and h[i] - min(h[i - 4:i]) >= 0.2 * mean and h[i] - min(h[i + 1:i + 5]) >= 0.2 * mean:
            peaks += 1
    return peaks >= 3


USGS_TZ = {("PST", "Y"): "America/Los_Angeles", ("MST", "Y"): "America/Denver", ("MST", "N"): "America/Phoenix", ("CST", "Y"): "America/Chicago", ("EST", "Y"): "America/New_York",
           ("AKST", "Y"): "America/Anchorage", ("HST", "N"): "Pacific/Honolulu", ("HST", "Y"): "America/Adak", ("AST", "N"): "America/Puerto_Rico"}


def usgs_tz(rec):
    """The time zone USGS publishes for the monitoring location (the NWS point zone can differ on a zone boundary)."""
    loc = ((rec.get("meta") or {}).get("loc")) or {}
    return USGS_TZ.get((loc.get("time_zone_abbreviation"), loc.get("uses_daylight_savings")))


_SCALAR_KEYS = ("site", "stats_source", "tz", "fetched_at", "lat", "lon", "year")
try:
    _SHAPE = json.load(open(os.path.join(DATA, "cache_shape.json"), encoding="utf-8"))
except Exception:
    _SHAPE = {}


def _normalise(rec):
    """A source record is a dict; each field keeps the type real data has for it (list, dict, string, number, ISO time: data/cache_shape.json). Anything else, an API that changed shape, counts as empty."""
    out = {k: (None if k not in _SCALAR_KEYS and not isinstance(v, (dict, type(None))) else v) for k, v in rec.items()}
    for k, sub in _SHAPE.items():
        v = out.get(k)
        if isinstance(v, dict):
            v = dict(v)
            for sk, want in sub.items():
                x = v.get(sk)
                if x is None:
                    continue
                if want in ("list", "dict"):
                    if not isinstance(x, list if want == "list" else dict):
                        v[sk] = [] if want == "list" else {}
                elif want == "num":
                    if isinstance(x, bool) or not isinstance(x, (int, float)):
                        v[sk] = None
                elif not isinstance(x, str):  # "str" and "iso"
                    v[sk] = None
                elif want == "iso":
                    try:
                        datetime.datetime.fromisoformat(x)
                    except ValueError:
                        v[sk] = None
            out[k] = v
    return out


def ctx(site, row, rec, now):
    """Everything derived once per gauge; blocks only read this."""
    rec = _normalise(rec)
    tzname = usgs_tz(rec) or rec.get("tz") or "UTC"
    zone = zoneinfo.ZoneInfo(tzname)
    fl, sg = series(rec, "00060"), series(rec, "00065")
    if not fl:
        raise CriticalFail("no flow series")
    lt, lv, lrow = fl[-1]
    age_min = (now - lt).total_seconds() / 60
    if age_min > 30 * 24 * 60:
        raise CriticalFail("latest flow older than 30 days (%.0f d)" % (age_min / 1440))
    stats = rec.get("stats")
    ldate = lt.astimezone(zone).date()
    mmdd = ldate.isoformat()[5:10]
    srow = stats.get(mmdd) if stats else None
    win = [x for x in fl if x[0] > lt - datetime.timedelta(hours=24)]
    basis, method = lv, "latest reading vs USGS daily percentiles for calendar date %s" % mmdd
    if len(win) >= 4:
        steps = sorted((win[i][0] - win[i - 1][0]).total_seconds() for i in range(1, len(win)))
        step = steps[len(steps) // 2] or 900
        if len(win) >= 0.8 * 86400 / step and (win[-1][0] - win[0][0]).total_seconds() >= 20 * 3600:
            basis = sum(x[1] for x in win) / len(win)
            method = "trailing 24 h mean vs USGS daily percentiles for calendar date %s" % mmdd
            if basis and abs(lv / basis - 1) > 0.3 and not oscillating(fl):  # the day's mean says little about a river that has just moved by a third or more: judge the latest reading (tidal and oscillating gauges keep the mean)
                basis, method = lv, "latest reading vs USGS daily percentiles for calendar date %s" % mmdd
    p = interp_pct(srow, basis) if srow else None
    ago = min(fl, key=lambda x: abs((x[0] - (lt - datetime.timedelta(hours=24))).total_seconds()))
    steps = sorted((fl[i][0] - fl[i - 1][0]).total_seconds() for i in range(max(1, len(fl) - 200), len(fl)))
    tol = max(1200, 0.6 * (steps[len(steps) // 2] if steps else 900))
    osc = oscillating(fl)
    wc24 = b3.window_change(fl, lt, 24)
    chg = wc24[2] if (not osc) and wc24 and abs((ago[0] - (lt - datetime.timedelta(hours=24))).total_seconds()) <= tol else None  # the same smoothed value as the rate table
    out = {"site": site, "row": row, "rec": rec, "now": now, "zone": zone, "tzname": tzname, "fl": fl, "sg": sg, "lt": lt, "lv": lv, "lrow": lrow, "age_min": age_min, "stats": stats, "ldate": ldate,
            "srow": srow, "p": p, "method": method, "chg": chg, "obs": tzl(lt, zone), "flow_then24": (wc24[1] if (not osc) and wc24 else None), "river": row["river"], "place": row["place"], "st": row["state"],
            "lat": rec["lat"], "lon": rec["lon"], "has_forecast": bool(((rec.get("nwps") or {}).get("forecast") or {}).get("points")), "fc_page": bool(((rec.get("nwps") or {}).get("forecast") or {}).get("points")), "offline": age_min > 24 * 60, "osc": osc, "basis": basis, "basis_mean": method.startswith("trailing")}
    if flow_jitter(out):
        out["chg"] = None  # flow that does not follow the gage height gives no honest 24 h percent
    return out


def credit_line(b):
    """The credit sentence the source's terms ask for (data/sources.json `credit`), printed once under every block of that source; '' when the register has none."""
    out = []
    for sid in [b.get("src_id")] + list(b.get("also") or []):
        c = (SOURCES.get(sid) or {}).get("credit")
        if c and c not in out:
            out.append(c)
    return "".join(" Credit: %s." % esc(c.rstrip(".")) for c in out)


def block(bid, heading, tag, body, source, src_id, as_of=None, amber=False):
    return {"id": bid, "heading": heading, "tag": tag, "body": body, "source": source, "src_id": src_id, "as_of": as_of, "amber": amber}


LIMIT_TEXT = {"alerts": "3 h", "air_obs": "3 h", "rain_totals": "6 h", "river_forecast": "24 h"}


# colour means one thing on every page: now (live gauge, weather station), fc (official forecasts, model guidance), rec (records, computed comparisons), area (agency data, map layers), safe (alerts, impacts, offline gauge)
FAMILY = {"live": "now", "obs": "now", "official": "fc", "model": "fc", "hist": "rec", "calc": "rec", "agency": "area", "map": "area"}
FAMILY_BY_ID = {"alerts": "safe", "flood_impacts": "safe", "offline": "safe"}


def render_block(b):
    amber = (' <span class="tag amber">Older than %s</span>' % LIMIT_TEXT.get(b["id"], "12 h")) if b.get("amber") else ""
    return ('<section class="card blk" data-f="%s" id="%s"><h2>%s <span class="tag t-%s">%s</span>%s<a class="pl" href="#%s" aria-label="Link to this section">#</a></h2>%s<details class="srcd"><summary>Where this comes from</summary><p class="src">%s%s</p></details></section>' % (FAMILY_BY_ID.get(b["id"]) or FAMILY.get(b["tag"], "now"), b["id"], esc(b["heading"]), b["tag"], esc(TAGS[b["tag"]]), amber, b["id"], b["body"], b["source"], credit_line(b)))


def table(heads, rows, right=(), hide=(), stack=False):
    th = "".join('<th scope="col"%s>%s</th>' % (' class="r"' if i in right else "", esc(h)) for i, h in enumerate(heads))
    names = ["hc%d" % i for i in hide]
    if len(heads) - len(hide) >= 4 or stack:  # on a phone a wide table becomes stacked rows (label: value) instead of columns cut off at the edge
        names.append("stk")

        def add(chunk):
            n = [-1]

            def sub(m):
                n[0] += 1
                return '<td data-l="%s"%s>' % (esc(heads[n[0]]) if n[0] < len(heads) else "", m.group(1) or "")
            return re.sub(r'<td( class="r")?>', sub, chunk)
        rows = "</tr>".join(add(c) for c in rows.split("</tr>"))
    cls = (' class="%s"' % " ".join(names)) if names else ""
    return '<div class="scroll"><table%s><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (cls, th, rows)


_DATE = r"[A-Z][a-z]{2} \d{1,2}, \d{4}"


def _keep(c):
    """Table text: a one-day span shows one date; a date or a station id never breaks across lines."""
    c = re.sub(r"(%s) to \1(?![0-9])" % _DATE, r"\1", c)
    c = re.sub(_DATE, lambda m: m.group(0).replace(" ", " "), c)
    return re.sub(r"\b([A-Za-z]+)-(\d{6,})\b", r"\1‑\2", c)


def card(label, value, sub="", cls=""):
    """One card of a rail: small label, big value, small note. All three are already-escaped text or tiny markup."""
    return '<div class="rc%s"><span class="rt">%s</span><b>%s</b>%s</div>' % ((" " + cls) if cls else "", label, value, ("<small>%s</small>" % sub) if sub else "")


def rail(cards, label):
    """Sideways row of same-shaped cards (a weather-widget strip): scroll-snap, next card peeking, no JavaScript, reachable by keyboard."""
    return '<div class="rail" role="region" aria-label="%s" tabindex="0">%s</div>' % (esc(label), "".join(cards))


def more(summary, inner):
    """The long version of a rail: the full table, closed, one tap away; the content stays in the page."""
    return '<details class="more"><summary>%s</summary>%s</details>' % (summary, inner)


def tr(cells, right=()):
    return "<tr>%s</tr>" % "".join('<td%s>%s</td>' % (' class="r"' if i in right else "", _keep(c)) for i, c in enumerate(cells))


# ---------------------------------------------------------------- hero
def fc_points(f):
    """NWS forecast points as (time, stage_ft or None, flow_cfs or None). NWS lists the stage first for most gauges but the flow first (kcfs or cfs) for some, so units decide, never position."""
    pu, su = (f.get("primary_units") or "").lower(), (f.get("secondary_units") or "").lower()
    out = []
    for p in f.get("points") or []:
        stage = flow = None
        for val, u in ((p.get("primary"), pu), (p.get("secondary"), su)):
            if not isinstance(val, (int, float)) or val <= -900:
                continue
            if u in ("ft", "feet"):
                stage = val
            elif u == "kcfs":
                flow = val * 1000
            elif u == "cfs":
                flow = val
        out.append((parse_t(p["t"]), stage, flow))
    return out


TAILWATER = re.compile(r"\b(below|bl|blw|downstream of)\b.*\b(dam|lake|lk|reservoir|res|powerplant|power plant)\b|\btailwater\b", re.I)


def _swing_note(G):
    """Flow that varies by a factor of 1.5 or more inside 24 h (hydropower or release cycles): a change over a few hours depends on the hour of the day."""
    t0 = G["lt"] - datetime.timedelta(hours=24)
    v = [x[1] for x in G["fl"] if x[0] >= t0 and x[1] > 0]
    if len(v) >= 20 and max(v) / min(v) >= 1.5:
        return '<small>Flow varied between %s and %s cfs in the last 24 h, so a change over a few hours depends on the time of day.</small>' % (fmt(min(v)), fmt(max(v)))
    return ""


def flow_jitter(G):
    """Flow that swings more than 1.8x inside 24 h while it does not move with the gage height (correlation under 0.5 over the aligned readings): lock-and-dam, tide or backwater effects, so the flow is not a reliable direction.
    Gauges where flow and stage rise and fall together (dam releases, floods) are never flagged. Returns (low, high, correlation) or None."""
    if G["osc"] or not G["sg"] or (G["sg"][-1][2].get("unit_of_measure") or "").lower() not in ("ft", "feet"):
        return None
    t0 = G["lt"] - datetime.timedelta(hours=24)
    fl = {x[0]: x[1] for x in G["fl"] if x[0] >= t0 and x[1] > 0}
    sg = {x[0]: x[1] for x in G["sg"] if x[0] >= t0}
    ks = [k for k in fl if k in sg]
    if len(ks) < 20:
        return None
    a_, b_ = [fl[k] for k in ks], [sg[k] for k in ks]
    if max(a_) / min(a_) < 1.8 or len(set(b_)) < 3 or len(set(a_)) < 3:
        return None
    r_ = statistics.correlation(a_, b_)
    return (min(a_), max(a_), r_) if r_ < 0.5 else None


def datum_gap(G):
    """(NWS stage, USGS stage) when the two agencies read the same gauge on different zero points (latest readings within 30 minutes of each other differ by more than 0.3 ft); None when they agree or one is missing."""
    o = (G["rec"].get("nwps") or {}).get("obs_stage")
    sg = G["sg"]
    if not o or not sg or (sg[-1][2].get("unit_of_measure") or "").lower() not in ("ft", "feet"):
        return None
    try:
        t, v = parse_t(o["t"]), float(o["v"])
    except (KeyError, TypeError, ValueError):
        return None
    u = min(sg, key=lambda x: abs((x[0] - t).total_seconds()))
    if abs((u[0] - t).total_seconds()) > 1800:
        return None
    return (v, u[1], t) if abs(v - u[1]) > 0.3 else None


def miles_between(la1, lo1, la2, lo2):
    la1, lo1, la2, lo2 = map(math.radians, (la1, lo1, la2, lo2))
    return 3958.8 * 2 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))


def nws_point_note(G):
    """When the NWS forecast point is named for another place than this gauge (Hudson River at Troy for the gauge at Green Island), say so: its flood stages and impact statements belong to that point."""
    n = G["rec"].get("nwps") or {}
    def norm(t):
        t = re.sub(r"\b(st|saint)\b\.?", "saint", (t or "").lower())
        t = re.sub(r"\bmt\b\.?", "mount", t)
        t = re.sub(r"\bft\b\.?", "fort", t)
        return re.sub(r"[^a-z0-9 ]", " ", t).split()
    nm, pl = norm(n.get("name")), norm(G["place"])
    if not nm or not pl:
        return ""
    if all(w in nm for w in pl):  # every word of the gauge's place is in the NWS name
        return ""
    return "The NWS links its forecast point %s to this USGS gauge but names it \u201c%s\u201d, for a nearby place. Its flood stages and impact statements are on the NWS stage scale; where the NWS and USGS read this gauge on different zero points, the margins below use the NWS reading." % (n.get("lid") or "", n.get("name"))


def dam_count(G):
    """Dams the EPA counts upstream, or None when StreamCat has no value for this gauge (silence must not read as no dams)."""
    sc = ((G["rec"].get("streamcat") or {}).get("vals") or {}).get("damdensws")
    area = G["row"].get("drainage_sqmi") or ((G["rec"].get("meta") or {}).get("loc") or {}).get("drainage_area")
    return None if sc is None or not area else upstream_dams(G)


def dams_txt(n):
    """A modelled count (dam density x drainage area): thousands separator, and no false precision above 100."""
    return "{:,}".format(int(round(n, -1)) if n >= 100 else n)


def upstream_dams(G):
    """About how many dams the EPA counts in the watershed upstream of the gauge (density per sq km x drainage area); 0 when unknown."""
    sc = ((G["rec"].get("streamcat") or {}).get("vals") or {}).get("damdensws")
    area = G["row"].get("drainage_sqmi") or ((G["rec"].get("meta") or {}).get("loc") or {}).get("drainage_area")  # the inventory lacks the area for some gauges; USGS station metadata has it
    try:
        return round(float(sc) * float(area or 0) * 2.58999)
    except (TypeError, ValueError):
        return 0


def hero(G, pages=None):
    from lib import ui
    c = b3.conditions(G, pages)
    p, srow = G["p"], G["srow"]
    pv = ("below 5th" if p == -1 else "above 95th" if p == 101 else ordinal(p)) if p is not None else "–"
    if p is not None and srow:
        pct_med = "%.0f%% of the median" % (G["basis"] / srow[5] * 100) if srow[5] else ""
        what = ("the trailing 24 h mean (%s cfs)" % fmt(G["basis"])) if G["basis_mean"] else ("the %s reading" % tzl(G["lt"], G["zone"], date=False))
        cap = "Estimated from %s against %d years of USGS daily statistics for %s." % (what, srow[0], G["ldate"].strftime("%b %d"))
    else:
        pct_med, cap = "", "No percentile: no published statistics for this date."
    sg = G["sg"]
    stage_txt = ("%.2f" % sg[-1][1]) if sg else "–"
    stage_unit = UNITS.get(sg[-1][2].get("unit_of_measure"), sg[-1][2].get("unit_of_measure") or "ft") if sg else "ft"
    chg = G["chg"]
    ndam = upstream_dams(G)
    if p is not None and ndam >= 1:
        cap += " Upstream dams may have changed flows during this record."
    if p is not None and G["osc"]:
        cap += " This gauge is tidal: the comparison uses the daily mean."
    if p is not None and TAILWATER.search(G["row"].get("raw_name") or ""):
        cap += " This gauge is below a dam, so flow follows releases, and the record may include years before the dam."
    d24 = G["lt"] - datetime.timedelta(hours=24)
    cmp_ = None  # tiles are assembled flow, stage, direction, comparison, then the rest
    strip = ""
    bcls = "" if p is None else "b-la" if p != 101 and p < 25 else "b-lp" if p == 101 or p > 75 else "b-lb"
    tiles = ui.tile("flow", "flow", "Latest flow", '<span data-live="flow">%s</span> <small><abbr title="cubic feet per second">cfs</abbr></small>' % fmt(G["lv"]), ui.spark([x[1] for x in G["fl"] if x[0] >= d24]) + "@@DIR@@", bcls)
    tiles += ui.tile("stage", "stage", "Gage height", '<span data-live="stage">%s</span> <small>%s</small>' % (stage_txt, esc(stage_unit)),
                     (ui.spark([x[1] for x in sg if x[0] >= d24]) if sg else "") + '<small>%s</small>%s' % ((('<b class="qual">%s</b>' % qual_text(sg[-1][2])) if sg and qual_text(sg[-1][2]) else "") or next_impact(G) or "Level relative to the gauge\'s zero", "" if sg else ""))
    if p is None:
        word, plain = "–", ""
    else:
        word = "Very low" if p == -1 else "Very high" if p == 101 else "Below normal" if p < 25 else "Above normal" if p > 75 else "Normal range"
        yrs = srow[0] if srow else 0
        on = G["ldate"].strftime("%b %d")
        plain = ("Lower than at least 95%% of the %d years on record for %s." % (yrs, on) if p == -1 else
                 "Higher than at least 95%% of the %d years on record for %s." % (yrs, on) if p == 101 else
                 "Lower than %d%% of the %d years on record for %s." % (100 - round(p), yrs, on) if p < 50 else
                 "Higher than %d%% of the %d years on record for %s." % (round(p), yrs, on))
        cap += ""
    norm_word, norm_plain = word, plain  # the trend tile below reuses the name `word`
    pre, dir_chip, word_note = tiles, "", ""
    if G["osc"]:
        v24 = [x[1] for x in G["fl"] if x[0] > G["lt"] - datetime.timedelta(hours=24)]
        tiles += ui.tile("trend", "steady", "24 h range", '<span class="rng">%s to %s</span> <small>cfs</small>' % (fmt(min(v24)), fmt(max(v24))), '<small id="ccap">Lowest to highest reading in 24 h (tidal cycle)</small>')
    elif flow_jitter(G) and c.get("sg6") is not None:
        lo_, hi_, rg_ = flow_jitter(G)
        d6 = c["sg6"]
        word, ico = ("Rising", "up") if d6 > 0.1 else ("Falling", "down") if d6 < -0.1 else ("Steady", "steady")
        dir_chip = "%s: gage height %+.2f ft in 6 h" % (word, d6)
        tiles += ui.tile("trend " + word.lower(), ico, "Gage height, last 6 h", '%s%.2f <small>ft</small> <small class="word">%s</small>' % ("+" if d6 > 0 else "", d6, word),
                         '<small id="ccap">Flow readings here swing between %s and %s cfs within 24 h and do not move with the gage height (correlation %.2f), so the flow is not a reliable direction and the gage height is used.</small>' % (fmt(lo_), fmt(hi_), rg_))
    else:
        if chg is None:
            tiles += ui.tile("trend", "steady", "24 h change", "–", '<small id="ccap">No reading 24 h earlier</small>')
        else:
            c6 = c["chg"].get(6)
            use, span = (c6, "6 h") if c6 is not None else (chg, "24 h")
            c1 = c["chg"].get(1)
            word, ico = ("Rising", "up") if use > 1 else ("Falling", "down") if use < -1 else ("Steady", "steady")
            if c1 is not None and word != "Steady":
                if abs(c1) >= 2 and (c1 > 0) != (use > 0):
                    word, ico = "Unsteady", "steady"  # the last hour points the other way from the last 6 h
                elif abs(c1) < 0.5 and abs(use) >= 3:
                    word, ico = "Levelling off", "steady"  # it moved, and has stopped
            sgd = c.get("sg6")
            if word in ("Rising", "Falling") and sgd is not None and abs(sgd) >= 0.05 and (sgd > 0) != (use > 0) and abs(use) < 5:
                word, ico = "Unclear", "steady"  # a small flow change that the gage height contradicts is noise, not a direction
                word_note = "<small>Flow changed %+.1f%% in %s but the gage height moved %+.2f ft the other way, so the direction is unclear.</small>" % (use, span, sgd)
            turned = c6 is not None and abs(chg) >= 5 and abs(c6) >= 2 and (chg > 0) != (c6 > 0)
            other = [("24 h", chg)] + [("%d h" % h, v) for h, v in sorted(c["chg"].items()) if h == 1 and span == "6 h"]
            parts = " &middot; ".join("%s: %s%.1f%%" % (n, "+" if v >= 0 else "", v) for n, v in other)
            uz = round(use)
            dir_chip = ("Steady: no change in %s" % span) if word == "Steady" and abs(use) < 0.05 else "%s: %s%.1f%% flow in %s" % (("%s, levelling off" % ("Falling" if use < 0 else "Rising")) if word == "Levelling off" else word, "+" if use > 0 else "-" if use < 0 else "", abs(use), span)
            word_note = word_note or {"Levelling off": "<small>It moved over %s but has changed by less than 0.5%% in the last hour.</small>" % span, "Unsteady": "<small>The last hour points the other way from the last %s.</small>" % span}.get(word, "")
            tiles += ui.tile("trend " + word.lower().split()[0], ico, "Change, last %s" % span, '%s%.1f%% <small class="word">%s</small>' % ("+" if use > 0 else "-" if use < 0 else "", abs(use), word),
                             '<small>%s</small>' % parts + (word_note if word == "Unclear" else "") + '<small id="ccap" hidden>Flow 24 h earlier: %s cfs.</small>' % fmt(G["flow_then24"] if G.get("flow_then24") else G["lv"] / (1 + chg / 100)))
    norm_html = ui.tile("norm", "map", "Is this normal for %s?" % G["ldate"].strftime("%b %d").replace(" 0", " "), norm_word,
                     ('<small class="nt">%s</small>' % esc(norm_plain) if norm_plain else "") + ui.rangebar(p) + '<small id="pcap">%s</small>' % esc(cap), ("wide " + bcls).strip())
    nwl = (G["rec"].get("nwps") or {}).get("lid")
    trend_html = tiles[len(pre):]
    tiles = pre.replace("@@DIR@@", "<small>%s</small>" % (('<b class="qual">%s</b>' % qual_text(G["fl"][-1][2])) if G["fl"] and qual_text(G["fl"][-1][2]) else esc(dir_chip or "Last 24 hours"))) + norm_html  # the trend lives in the answer pills and the change tile; the flow tile spells out its unit (a hover title does not work on a phone)  # flow, stage, comparison: the answer on the first phone screen
    strip = trend_html + strip  # change, then forecast, alerts, air, rain, sunset ride in one swipe row
    if c["fc"]:
        fcw = c["fc"]
        unit = fcw["unit"]
        above = fcw["cur"] is not None and fcw["cur"] > fcw["v"] + (0.05 if unit == "ft" else 0.02 * abs(fcw["v"]))
        val = ('%.1f <small>ft</small>' % fcw["v"]) if unit == "ft" else ('%s <small>cfs</small>' % fmt(fcw["v"]))
        _pn = nws_point_note(G)
        sub = '<small>%s%s &middot; NWS point %s%s</small>' % ("first reached " if fcw["repeat"] else "", esc(fcw["t"]), esc(fcw["lid"]), (' (named \u201c%s\u201d, not this gauge\u2019s place)' % esc((G["rec"].get("nwps") or {}).get("name") or "")) if _pn else "")
        if fcw["repeat"]:
            sub += '<small>Reached again later: a regular cycle.</small>'
        rating_txt = (" (about %s cfs by the NWS rating)" % fmt(fcw["flow_at"])) if fcw.get("flow_at") and not _pn and not G["osc"] else ""  # a rating belongs to its own forecast point: another place, or a tidal reach, makes the cfs disagree with this gauge
        turn_txt = "; falling now, the NWS expects a rise" if unit == "ft" and fcw["cur"] is not None and not fcw["datum"] and fcw["v"] - fcw["cur"] >= 0.5 and c.get("sg6") is not None and c["sg6"] < -0.1 else ""
        if G["osc"]:
            sub += '<small>This reach is tidal: the NWS forecast is a net level, so compare it with the day\'s range, not with one reading.</small>'
        elif unit == "ft" and fcw["cur"] is not None and not fcw["datum"] and abs(fcw["v"] - fcw["cur"]) >= 0.05 and not above:
            sub += '<small>%.1f ft above the latest reading%s%s.</small>' % (abs(fcw["v"] - fcw["cur"]), rating_txt, turn_txt)
        if fcw["falls"] and not (above and not G["osc"]):
            sub += '<small>Then falls to %s by %s.</small>' % ((("%.1f ft" % fcw["end_v"]) if unit == "ft" else ("%s cfs" % fmt(fcw["end_v"]))), esc(fcw["end_t"]))
        if fcw["datum"]:
            sub += '<small>At %s the NWS read this gauge at %.2f ft and the USGS at %.2f ft (different zero points); the forecast is in NWS stage.</small>' % (esc(tzl(fcw["datum"][2], G["zone"], date=False)), fcw["datum"][0], fcw["datum"][1])
        if fcw.get("offset"):
            o = fcw["offset"]
            sub += '<small class="fcnote">For %s the forecast was %s; the gauge reads %s now. Forecasts at gauges below dams and in tidal reaches can run out of step with the readings.</small>' % (esc(o["t"]), esc(o["f"]), esc(o["c"]))
        if above and not G["osc"]:
            sub += '<small class="fcnote">%s below the latest reading (%s): the NWS expects a fall%s.</small>' % (("%.1f ft" % (fcw["cur"] - fcw["v"])) if unit == "ft" else ("%s cfs" % fmt(fcw["cur"] - fcw["v"])), ("%.2f ft" % fcw["cur"]) if unit == "ft" else ("%s cfs" % fmt(fcw["cur"])), (" to %s by %s" % ((("%.1f ft" % fcw["end_v"]) if unit == "ft" else ("%s cfs" % fmt(fcw["end_v"]))), esc(fcw["end_t"]))) if fcw["falls"] else "")
        strip += ui.tile("fcst", "crest", ("NWS forecast" if above and not G["osc"] else ("Forecast high (NWS stage)" if fcw["datum"] else "Forecast high")) if unit == "ft" else ("NWS forecast flow" if above and not G["osc"] else "Forecast high flow"), val, sub)
    elif nwl and G["has_forecast"]:
        strip += ui.tile("fcst none", "crest", "River forecast", "Out of date", '<small>The latest NWS forecast for point %s is old or not in feet, so it is not shown. The weather forecast below is not a river forecast.</small>' % esc(nwl))
    elif nwl:
        strip += ui.tile("fcst none", "crest", "River forecast", "Not issued", '<small>NWS forecast point %s has no current river forecast. The weather forecast below is not a river forecast.</small>' % esc(nwl))
    else:
        strip += ui.tile("fcst none", "crest", "River forecast", "Not linked", '<small>No NWS river forecast point is linked to this gauge in our data. The weather forecast below is not a river forecast.</small>')
    if c["alerts"] is not None and not c["alerts"]["n"] and c["alerts"].get("age_h") is not None and c["alerts"]["age_h"] > 3:  # a fresh "none" is said by the pill and the alerts block; an old answer is said here
        al = c["alerts"]
        old = al.get("age_h") is not None and al["age_h"] > 3  # the alert source has not answered for over 3 h: "none" must not read as current
        strip += ui.tile("alrt " + ("on" if al["n"] else "off") + (" stale" if old else ""), "bell", "NWS alerts", str(al["n"]) if al["n"] else "No alerts", '<small>%s</small>' % (esc("; ".join(al["names"])) if al["n"] else ("No alerts in the last answer from the NWS, as of %s. The alert service has not answered since; check weather.gov." % esc(al["asof"]) if old else "No alerts active here")))
    elif c["alerts"] is None:
        strip += ui.tile("alrt unknown", "bell", "NWS alerts", "Unknown", '<small>We have no answer from the National Weather Service alert service for this location. Check weather.gov.</small>')
    if c["wt"]:
        wf = c["wt"]["f"]
        cold = ('<small class="cold">Below 50&deg;F: cold-water shock and loss of swimming ability within minutes of immersion (<a href="https://www.weather.gov/safety/coldwater" rel="noopener">NWS cold water safety</a>).</small>' if wf < 50 else
                '<small class="cold">Below 60&deg;F: cold-water shock risk on immersion; a wetsuit or PFD matters (<a href="https://www.weather.gov/safety/coldwater" rel="noopener">NWS cold water safety</a>).</small>' if wf < 60 else "")
        strip += ui.tile("wtemp", "thermo", "Water temperature", '%.0f&deg;<small>F</small>' % wf, cold + '<small>USGS sensor, %s</small>' % esc(c["wt"]["t"]))
    nw = G["rec"].get("near_wtemp")
    if not c["wt"] and nw and nw.get("t") and (G["now"] - parse_t(nw["t"])).total_seconds() < 48 * 3600:
        strip += ui.tile("wtemp near", "thermo", "Water temperature nearby", '%.0f&deg;<small>F</small>' % nw["f"], '<small>No sensor at this gauge. Nearest on this river: %s, %.0f mi away, USGS sensor %s, %s</small>' % (esc(re.sub(r", (\w\w)$", lambda m: ", " + m.group(1).upper(), nw["name"].title())), nw["mi"], esc(nw["site"]), esc(tzl(parse_t(nw["t"]), G["zone"]))))
    if c["up"]:
        up = c["up"]
        strip += ui.tile("upst", "up", "Upstream gauge now", '%s <small>cfs</small>' % fmt(up["flow"]), '<small><a href="%s">%s</a>%s</small>' % (up["url"], esc(up["name"]), (" &middot; measured lag about %d h" % up["lag"]) if up.get("lag") else "") + ('<small>A much smaller stream than this river: a tributary, not a stand-in for the water on its way.</small>' if G["lv"] and up["flow"] < 0.2 * G["lv"] else ""))
    ban = ui.banner(c["alerts"]["n"], esc("; ".join(c["alerts"]["names"]))) if c["alerts"] and c["alerts"]["n"] else ""
    al_ = c["alerts"]
    if al_ is None:
        a_txt, a_cls = "NWS alerts unknown", "ax"
    elif al_["n"]:
        a_txt, a_cls = "%d active NWS alert%s" % (al_["n"], "" if al_["n"] == 1 else "s"), "ay"
    elif al_.get("age_h") is not None and al_["age_h"] > 3:
        a_txt, a_cls = "NWS alert check is old", "ax"
    else:
        a_txt, a_cls = "No active NWS alerts", "an"
    band_cls = "" if p is None else "la" if p != 101 and p < 25 else "lp" if p == 101 or p > 75 else "lb"
    fc_ = c.get("fc") or {}
    if fc_.get("cur") is not None and fc_.get("v") is not None and fc_.get("t"):
        fu_ = "ft" if fc_["v"] < 100 and fc_["cur"] < 100 else "cfs"
        big_rise = (fc_["v"] - fc_["cur"] >= 1.0) if fu_ == "ft" else (fc_["cur"] > 0 and fc_["v"] >= 1.25 * fc_["cur"])
        if big_rise:
            dir_chip = (dir_chip or "Direction unclear") + "; NWS forecast rises to %s by %s" % (("%.1f ft" % fc_["v"]) if fu_ == "ft" else ("%s cfs" % fmt(fc_["v"])), fc_["t"])
    answer = ('<p class="answer" aria-label="Summary"><span class="a1">%s</span><span class="a2 %s">%s</span><span class="a3 %s">%s</span></p>' % (
        esc(dir_chip or "Direction unclear"), band_cls, esc(("%s for %s" % (norm_word, G["ldate"].strftime("%b %d").replace(" 0", " "))) if p is not None else "No past-years comparison for this date"), a_cls, esc(a_txt)))
    if c["rain"]:
        strip += ui.tile("rain", "drop", "Rain, last 24 h", '%.2f <small>in</small>' % c["rain"]["in"], '<small>NWS RFC estimate%s</small>' % ((" to " + esc(c["rain"]["to"])) if c["rain"]["to"] else ""))
    if c["air"]:
        a = c["air"]
        wtxt = ", ".join(x for x in (("wind: calm" if a["wind"] < 1 else "wind %.0f mph %s" % (a["wind"], esc(a["dir"]))) if a["wind"] is not None else "", ("gusts %.0f mph" % a["gust"]) if a["gust"] is not None else "") if x)
        # a station name that opens with a sensor code ("070W10895RWS1RP1 at Canyon Creek Rd") keeps only the place
        strip += ui.tile("air", "wind", "Air temperature", '%.0f<small>&deg;F</small>' % a["f"], ('<small>%s</small>' % wtxt if wtxt else "") + '<small>Weather station %s%s%s, %s</small>' % (esc(a["st"]), (" (" + esc(re.sub(r"^\S*\d\S*\s+(at|near)\s+", "", a["name"])) + ")") if a.get("name") else "", (", %d mi away" % a["mi"]) if a.get("mi") is not None else "", esc(a["t"])))
    st_ = sun_times(G["lat"], G["lon"], G["ldate"])
    if st_:
        sh, _, sz = tzl(st_[1], G["zone"], date=False).replace("\u00a0", " ").rpartition(" ")
        strip += ui.tile("sun", "sun", "Sunset today", '%s <small>%s</small>' % (esc(sh), esc(sz)), '<small>Sunrise %s%s &middot; %s, %.0f%% lit &middot; computed from location and date</small>' % (esc(tzl(st_[0], G["zone"], date=False)), (" &middot; last light " + esc(tzl(ct_[1], G["zone"], date=False))) if (ct_ := sun_times(G["lat"], G["lon"], G["ldate"], -6.0)) else "", moon_phase(G["ldate"])[0].lower(), moon_phase(G["ldate"])[1]))
    gone = []
    if not c["wt"] and not (nw and nw.get("t") and (G["now"] - parse_t(nw["t"])).total_seconds() < 48 * 3600):
        gone.append("water temperature (no USGS temperature sensor at this gauge or within 40 mi on this river)")
    if b_quality(G) is None:
        gone.append("clarity (no USGS turbidity or water-quality sensor at this gauge)")
    if not c["rain"]:
        gone.append("rain estimate (no NWS precipitation estimate in the last 6 h)")
    if not c["air"]:
        gone.append("air observation (no NWS station report in the last 12 h)")
    if not ((G["rec"].get("nws") or {}).get("hourly")):
        gone.append("hourly weather (no NWS hourly forecast for this location)")
    if G["osc"] and not (G["rec"].get("tides") or {}).get("rows"):
        gone.append("tide predictions (no NOAA station within 50 mi)")
    strip_html = (('<div class="cstrip" role="group" aria-label="Conditions at the gauge" tabindex="0">%s</div>' % strip) if strip else "") + (('<p class="gaps">Not measured at this gauge: %s.</p>' % "; ".join(gone)) if gone else "")
    return ban + answer + '<div class="hero hero2" data-t="%s">%s</div>' % (iso(G["lt"]), tiles) + strip_html


# ---------------------------------------------------------------- blocks (each returns a block dict or None)
def tf(v, ticks=None):
    """Axis tick label: zero is 0, not 0.00. With the tick list, use the fewest decimals that show every tick exactly (12.5 is never printed as 12)."""
    if abs(v) < 1e-9:
        return "0"
    if ticks and len(ticks) > 1:
        d = next((k for k in (0, 1, 2, 3) if all(abs(t - round(t, k)) < 1e-9 for t in ticks)), 3)
        if d > 0 or abs(v) < 100:
            return "{:,.{d}f}".format(v, d=d)
    return fmt(v)


def nice_ticks(lo, hi, n=5):
    """Round axis: returns (axis_min, axis_max, ticks) on a 1/2/2.5/5 x 10^k step that covers [lo, hi]."""
    lo, hi = float(lo), float(hi)
    if hi <= lo:
        hi = lo + 1.0
    raw = (hi - lo) / (n - 1)
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    a = math.floor(lo / step) * step
    b = math.ceil(hi / step) * step
    ticks, v = [], a
    while v <= b + step * 1e-9:
        ticks.append(round(v, 10))
        v += step
    return a, b, ticks


def steps_med(pts):
    st = sorted((pts[i][0] - pts[i - 1][0]).total_seconds() for i in range(1, len(pts)))
    return st[len(st) // 2] if st else None


def _chart_svg(G, W, Hh, fs, nx, cls):
    fl, zone, lt = G["fl"], G["zone"], G["lt"]
    t1 = lt
    t0 = max(fl[0][0], lt - datetime.timedelta(days=7))
    pts = [x for x in fl if x[0] >= t0]
    L, B = (56, 30) if W > 500 else (46, 28)
    vals = [v for _, v, _ in pts]
    bp = []
    if G["stats"]:
        for d in sorted({x[0].astimezone(zone).date() for x in pts}):
            rr = G["stats"].get(d.isoformat()[5:10])
            if rr:
                bp.append((d, rr[4], rr[6], rr[5]))
        for d, a, c, m in bp:
            vals += [a, c]
    vmin, vmax, ticks = nice_ticks(min(vals), max(vals))
    span = (t1 - t0).total_seconds() or 1
    X = lambda t: L + (t - t0).total_seconds() / span * (W - L - 14)
    Y = lambda v: 12 + (1 - (v - vmin) / ((vmax - vmin) or 1)) * (Hh - B - 12)
    band = []
    if bp:
        def at(d):
            if d == bp[0][0]: return t0
            if d == bp[-1][0]: return t1
            return min(t1, max(t0, datetime.datetime.combine(d, datetime.time(12), zone)))
        up = " ".join("%.1f,%.1f" % (X(at(d)), Y(c)) for d, a, c, m in bp)
        dn = " ".join("%.1f,%.1f" % (X(at(d)), Y(a)) for d, a, c, m in reversed(bp))
        md = " ".join("%.1f,%.1f" % (X(at(d)), Y(m)) for d, a, c, m in bp)
        band = ['<polygon points="%s %s" fill="var(--soft)"/>' % (up, dn), '<polyline points="%s" fill="none" stroke="var(--mut)" stroke-dasharray="4 4"/>' % md]
    step = max(1, len(pts) // 220)
    thin = pts[::step] + [pts[-1]]
    gap_s = max(10800, 4 * (steps_med(pts) or 900))
    segs, cur = [], [thin[0]]
    for a_, b_ in zip(thin, thin[1:]):
        if (b_[0] - a_[0]).total_seconds() > gap_s:
            segs.append(cur)
            cur = []
        cur.append(b_)
    segs.append(cur)
    line = "".join('<polyline points="%s" fill="none" stroke="var(--accent)" stroke-width="2.4"/>' % " ".join("%.1f,%.1f" % (X(t), Y(v)) for t, v, _ in sg_) for sg_ in segs if len(sg_) > 1)
    grid = "".join('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--line)"/><text x="%d" y="%.1f" font-size="%d" fill="var(--mut)" text-anchor="end">%s</text>' % (L, W - 14, Y(tv), Y(tv), L - 6, Y(tv) + 4, fs, (tf(tv, ticks) + " cfs") if tv == ticks[-1] else tf(tv, ticks)) for tv in ticks)
    xl = ""
    mids, d0 = [], t0.astimezone(zone).date() + datetime.timedelta(days=1)
    while datetime.datetime.combine(d0, datetime.time(0), zone) < t1:
        mids.append(datetime.datetime.combine(d0, datetime.time(0), zone))
        d0 += datetime.timedelta(days=1)
    for m in mids[::max(1, -(-len(mids) // nx))]:  # one label per local midnight (every second one on a phone)
        x_ = X(m)
        xl += '<text x="%.1f" y="%d" font-size="%d" fill="var(--mut)" text-anchor="%s">%s</text>' % (x_, Hh - 8, fs, "start" if x_ < L + 16 else "end" if x_ > W - 30 else "middle", m.strftime("%b %d").replace(" 0", " "))
    return ('<svg class="%s" viewBox="0 0 %d %d" width="100%%" role="img" aria-label="Flow in cfs over the last 7 days with the 25th to 75th percentile band">%s%s%s%s'
           '<circle cx="%.1f" cy="%.1f" r="5" fill="var(--accent)"/></svg>' % (cls, W, Hh, "".join(band), grid, xl, line, X(lt), Y(G["lv"])))


def b_flow_chart(G):
    svg = _chart_svg(G, 760, 250, 11, 7, "cw") + _chart_svg(G, 340, 250, 12, 4, "cn")
    return block("flow_chart", "Last 7 days", "live", svg, "Source: USGS Water Data API (continuous values), observed to %s. Shaded band: 25th to 75th percentile of USGS daily statistics for each date; dashed: median. Flow in cfs." % esc(G["obs"]), "usgs")


def b_daily(G):
    fl, zone = G["fl"], G["zone"]
    steps = sorted((fl[i][0] - fl[i - 1][0]).total_seconds() for i in range(1, len(fl)))
    exp_n = 86400 / ((steps[len(steps) // 2] if steps else 900) or 900)
    official = {r_[0]: r_[1] for r_ in ((G["rec"].get("year") or {}).get("rows") or [])}
    by = collections.OrderedDict()
    for t, v, _ in fl:
        by.setdefault(t.astimezone(zone).date(), []).append(v)
    rows, n_off = "", 0
    for d, vs in reversed(list(by.items())):
        full = len(vs) >= 0.8 * exp_n
        o = official.get(d.isoformat())
        if o is not None:
            n_off += 1
            val, note = fmt(o) + " cfs", ""
        elif full:
            val, note = fmt(sum(vs) / len(vs)) + " cfs", "Mean of readings, not yet published by USGS"
        else:
            val, note = "–", "Partial day"
        rows += tr([d.strftime("%b %d, %Y").replace(" 0", " "), val, note], right=(1,))
    return block("daily_readings", "Daily mean flow", "live", table(["Date (gauge-local)", "Mean flow", "Note"], rows, right=(1,)),
                 "Source: USGS Water Data API (daily values where USGS has published them; otherwise the mean of continuous readings on that gauge-local date, shown only with at least 80% of expected readings).", "usgs")


def human_span(days):
    if days < 45:
        return "%d day%s" % (days, "" if days == 1 else "s")
    if days < 730:
        return "%d months" % round(days / 30.4)
    return "%d years" % round(days / 365.25)


def fdate(iso_d):
    return datetime.date.fromisoformat(iso_d).strftime("%b %d, %Y").replace(" 0", " ")


def b_record(G):
    r = G["rec"].get("record")
    if not r:
        return None
    pk = r["peak"]
    cards = [card("Peak, last 7 days", "%s <small>cfs</small>" % fmt(pk["value"]), fdate(pk["date"]))]
    if r.get("prior"):
        cards.append(card("Last this high", "%s <small>cfs</small>" % fmt(r["prior"]["value"]), "%s (%s before this peak)" % (fdate(r["prior"]["date"]), human_span(r["prior"]["days_before"]))))
    else:
        cards.append(card("Last this high", "No earlier day", "Record begins %d" % r["first_year"]))
    if r.get("last_p90"):
        cards.append(card("Last day above the 90th percentile", fdate(r["last_p90"]["date"]), "%s earlier" % human_span(r["last_p90"]["days_before"])))
    if r.get("above_p75"):
        cards.append(card("Days above the 75th percentile", "%d of %d" % (r["above_p75"]["n"], r["above_p75"]["of"]), "last %d days" % r["above_p75"]["of"]))
    if r.get("month"):
        m = r["month"]
        cards.append(card("%s 1 to %d, mean flow" % (m["month"], m["dom"]), "%s <small>cfs</small>" % fmt(m["mean"]), "rank %d highest of %d years" % (m["rank"], m["years"])))
    return block("record_comparison", "Compared with this gauge’s record", "hist", rail(cards, "Compared with this gauge’s record"),
                 "Source: USGS daily mean flows (Water Data API), %d to %d (%s days), data through %s; method %s. Percentiles are USGS daily statistics. Recent days are provisional." % (
                     r["first_year"], r["last_year"], "{:,}".format(r["n_days"]), fdate(r["as_of"]), esc(r["method"])), "usgs")


def b_quality(G):
    rows = ""
    for code, lab in LABELS.items():
        s = series(G["rec"], code)
        if s:
            t, v, r = s[-1]
            unit = UNITS.get(r.get("unit_of_measure"), r.get("unit_of_measure") or "")
            shown = ("%.1f °F (%.1f °C)" % (v * 9 / 5 + 32, v)) if (code == "00010" and unit == "°C") else ("%s %s" % (fmt(v), esc(unit)))
            rows += tr([esc(lab), shown + ((' <b class="qual">%s</b>' % qual_text(r)) if qual_text(r) else ""), esc(tzl(t, G["zone"]))], right=(1,))
    if not rows:
        return None
    return block("quality_sensors", "Water quality sensors", "live", table(["Measure", "Latest value", "Observed"], rows, right=(1,)), "Source: USGS Water Data API (continuous values). Values as reported by the gauge, provisional.", "usgs")


def b_related(G, pages):
    items = (G["rec"].get("related") or {}).get("items") or []
    rows = ""
    for x in items:
        pr = pages.get(x["site"])
        if not pr or not pr.get("_built"):
            continue
        lag = ("about %d h (r %.2f)" % (x["lag_h"], x["lag_r"])) if x.get("lag_h") else "–"
        rows += tr(['<a href="%s">%s</a>' % (pr["water_url"], esc(river_at(pr["river"], pr["place"]))), x["relation"].capitalize(), "%s cfs" % fmt(x["flow"]), esc(tzl(parse_t(x["time"]), G["zone"])), lag], right=(2,))
    if not rows:
        return None
    from lib import ui
    nodes = []
    for rel in ("upstream", "downstream"):
        if rel == "downstream":
            nodes.append({"name": "<span>This gauge</span>", "flow": "%s cfs" % fmt(G["lv"]), "sub": esc(G["obs"]), "cur": True})
        for x in items:
            pr = pages.get(x["site"])
            if x["relation"] == rel and pr and pr.get("_built"):
                nodes.append({"name": '<a href="%s">%s</a>' % (pr["water_url"], esc(river_at(pr["river"], pr["place"]))), "flow": "%s cfs" % fmt(x["flow"]),
                              "sub": x["relation"].capitalize() + " &middot; " + esc(tzl(parse_t(x["time"]), G["zone"])) + ((" &middot; lag about %d h" % x["lag_h"]) if x.get("lag_h") else ""), "cur": False})
    return block("related_gauges", "Upstream and downstream gauges", "live", ui.strip(nodes),
                 "Source: USGS NLDI river network and USGS Water Data API. Relation is along the NLDI main stem; only gauges on this site that report flow are listed. Observed lag is the shift, up to 72 h, that best matches hourly flow at the two gauges over the last 8 days (r = correlation, shown only at 0.85 or higher); it is empirical, not a travel time.", "usgs")


def b_flood_stages(G):
    n = G["rec"].get("nwps") or {}
    cats = n.get("categories") or {}
    if not cats:
        return None
    rows = "".join(tr([k.capitalize(), "%.1f ft" % cats[k]], right=(1,)) for k in ("action", "minor", "moderate", "major") if k in cats)
    return block("flood_stages", "Flood stages", "official", table(["Category", "Gage height (ft)"], rows, right=(1,)),
                 "Source: National Weather Service forecast point %s (%s), fetched %s. Compare with the gage height above; thresholds belong to that forecast point." % (esc(n.get("lid") or ""), esc(n.get("name") or ""), esc(tzl(parse_t(n["fetched_at"]), G["zone"]))), "nwps")


def b_river_forecast(G):
    n = G["rec"].get("nwps") or {}
    fc = n.get("forecast")
    if not fc or not fc.get("points"):
        return None
    age = hours_old(fc.get("issued"), G["now"]) if fc.get("issued") else None
    if age is not None and age > 72:
        return None
    rows = ""
    fut = [x for x in fc_points(fc) if x[0] >= G["now"] - datetime.timedelta(hours=1)]
    if not fut:
        return None
    gap = datum_gap(G)
    keep = list(range(len(fut)))
    thin = ""
    if len(fut) > 48:
        step = max(2, (len(fut) - 24) // 24)
        top = max(range(len(fut)), key=lambda i: (fut[i][1] if fut[i][1] is not None else (fut[i][2] or 0)))
        keep = sorted(set(range(24)) | set(range(24, len(fut), step)) | {top, len(fut) - 1})
        thin = " After the first day the table shows about every %d hours; the highest forecast value and the last point are always included." % step
    for t_, s_, f_ in [fut[i] for i in keep]:
        rows += tr([esc(tzl(t_, G["zone"])), ("%.1f ft" % s_) if s_ is not None else "–", ("%s cfs" % fmt(f_)) if f_ is not None else "–"], right=(1, 2))
    if gap:
        rows += tr(["NWS and USGS read this gauge on different zero points", "NWS %.2f ft at %s" % (gap[0], esc(tzl(gap[2], G["zone"], date=False))), "USGS %.2f ft at that time" % gap[1]], right=(1, 2))
    issued = esc(tzl(parse_t(fc["issued"]), G["zone"])) if fc.get("issued") else "time not stated"
    lead = ""
    pts_ = fc_points(fc)
    if pts_:
        near = min(pts_, key=lambda x: abs((x[0] - G["lt"]).total_seconds()))
        if abs((near[0] - G["lt"]).total_seconds()) <= 5400 and near[2] and G["lv"] and abs(near[2] - G["lv"]) > 0.25 * max(near[2], G["lv"]):
            lead = '<p class="src">At %s the NWS forecast flow is %s cfs; the USGS measured %s cfs at %s. The NWS converts its stage forecast to flow with its own rating, which can differ from the USGS flow at the same level.</p>' % (esc(tzl(near[0], G["zone"], date=False)), fmt(near[2]), fmt(G["lv"]), esc(tzl(G["lt"], G["zone"], date=False)))
    sel = [fut[i] for i in keep]
    top_i = max(range(len(sel)), key=lambda i: (sel[i][1] if sel[i][1] is not None else (sel[i][2] or 0)))
    pick = list(range(len(sel))) if len(sel) <= 10 else sorted({round(k * (len(sel) - 1) / 9) for k in range(10)} | {top_i})  # whole span, not only the first hours
    pick.sort(key=lambda i: i != top_i)  # the highest forecast point is the first card
    fcards = []
    for i in pick:
        t_, s_, f_ = sel[i]
        main = ("%.1f <small>ft</small>" % s_) if s_ is not None else (("%s <small>cfs</small>" % fmt(f_)) if f_ is not None else "–")
        subf = ("%s cfs" % fmt(f_)) if (s_ is not None and f_ is not None) else ""
        fcards.append(card(("Highest forecast &middot; " if i == top_i else "") + esc(tzl(t_, G["zone"])), main, subf, "crest" if i == top_i else ""))
    ftable = table(["Time (gauge-local)", "Gage height (NWS)", "Flow (NWS value)"], rows, right=(1, 2))
    return block("river_forecast", "River forecast", "official", lead + rail(fcards, "River forecast points") + more("All %d forecast points" % len(sel), ftable),
                 "Source: National Weather Service forecast point %s, issued %s. Official forecasts change as rain and releases change. NWS flow values come from the NWS rating for its point and can differ from USGS flow readings.%s" % (esc(n.get("lid") or ""), issued, thin), "nwps", amber=(age is not None and age > 24))


def b_nwm(G):
    if (G["rec"].get("nwps") or {}).get("forecast"):
        return None
    n = G["rec"].get("nwm") or {}
    pts = n.get("points") or []
    if len(pts) < 4:
        return None
    age = hours_old(n.get("reference_time"), G["now"]) if n.get("reference_time") else None
    if age is not None and age > 72:
        return None
    fut = [p for p in pts if parse_t(p["t"]) >= G["now"] - datetime.timedelta(hours=1)]
    if len(fut) < 4:
        return None
    rows = "".join(tr([esc(tzl(parse_t(p["t"]), G["zone"])), "%s cfs" % fmt(p["flow"])], right=(1,)) for p in fut[::3][:8])
    ref = esc(tzl(parse_t(n["reference_time"]), G["zone"])) if n.get("reference_time") else "time not stated"
    return block("nwm_guidance", "Model guidance", "model", table(["Time (gauge-local)", "Modelled flow"], rows, right=(1,)),
                 "Source: NOAA National Water Model, reach %s, run %s. Model guidance, not an official forecast and not a measurement." % (esc(str(n["comid"])) if isinstance(n.get("comid"), (int, str)) and str(n.get("comid")).strip() else "id not stated", ref), "nwm", amber=(age is not None and age > 12))


def b_rain(G):
    n = G["rec"].get("rain") or {}
    v = n.get("inches") or {}
    if not v:
        return None
    age = hours_old(n["fetched_at"], G["now"])
    if age is not None and age > 24:
        return None
    labs = (("last_24h", "Last 24 h"), ("last_2d", "Last 2 days"), ("last_3d", "Last 3 days"))
    vt = n.get("valid_through") or {}
    rows = "".join(tr(["%s, to %s" % (lab, esc(tzl(parse_t(vt[k]), G["zone"]))) if vt.get(k) else lab, "%.2f in" % v[k]], right=(1,)) for k, lab in labs if k in v)
    from lib import ui
    vmax = max(0.5, max(v[k] for k, _ in labs if k in v))
    wid = ui.bars([(lab, v[k], "%.2f in" % v[k]) for k, lab in labs if k in v], vmax)
    rcards = [card(lab, "%.2f <small>in</small>" % v[k], ("to %s" % esc(tzl(parse_t(vt[k]), G["zone"]))) if vt.get(k) else "") for k, lab in labs if k in v]
    return block("rain_totals", "Recent rain at the gauge location", "official", wid,
                 "Source: NWS River Forecast Center multisensor precipitation estimate, 4 km grid at the gauge location, fetched %s. Estimate, not a gauge at the stream. Each window is a separate NWS product with its own end time (hourly and daily products), so a longer window can end earlier than a shorter one and show less rain." % esc(tzl(parse_t(n["fetched_at"]), G["zone"])), "rfc", amber=(age is not None and age > 6))


def storm_line(G):
    """Lightning is the on-water danger that river levels do not show: the hours in the next 24 that the NWS hourly forecast calls thunderstorms, or an explicit 'none' (silence would read as fine). Text comes from the NWS short forecast, not from us."""
    n = G["rec"].get("nws") or {}
    hr = n.get("hourly") or []
    age = hours_old(n.get("hourly_updated"), G["now"]) if n.get("hourly_updated") else None
    if not hr or age is None:
        return ""
    if age > 12:
        return '<p class="storm warn">Thunderstorm outlook: the NWS hourly forecast for this location is %d h old, so hours with thunderstorms are not listed. Check weather.gov before going on the water.</p>' % age
    nxt = [p for p in hr if parse_t(p["startTime"]) > G["now"] - datetime.timedelta(hours=1)][:24]
    if len(nxt) < 12:
        return ""
    runs, cur = [], None
    for p in nxt:
        hit = "thunder" in (p.get("shortForecast") or "").lower()
        t = parse_t(p["startTime"])
        if hit and cur is None:
            cur = [t, t]
        elif hit:
            cur[1] = t
        elif cur is not None:
            runs.append(cur)
            cur = None
    if cur is not None:
        runs.append(cur)
    if not runs:
        return '<p class="storm ok">Thunderstorms: none in the National Weather Service forecast for the next %d hours.</p>' % len(nxt)
    when = "; ".join("%s to %s" % (tzl(a, G["zone"], date=(b - a) >= datetime.timedelta(hours=11)), tzl(b + datetime.timedelta(hours=1), G["zone"], date=(b - a) >= datetime.timedelta(hours=11))) if a != b else tzl(a, G["zone"], date=False) for a, b in runs)
    return '<p class="storm warn"><b>Thunderstorms in the forecast:</b> %s (gauge-local time).</p>' % esc(when)


def area_short(s, n=6, county=None):
    parts = [p.strip() for p in s.split(";") if p.strip()]
    if county:
        c = county.lower().replace(" county", "").replace(" parish", "").strip()
        mine = [p for p in parts if p.lower() == c or p.lower().endswith(" " + c)]
        parts = mine + [p for p in parts if p not in mine]
    return s if len(parts) <= n and not county else "; ".join(parts[:n]) + (("; and %d more areas" % (len(parts) - n)) if len(parts) > n else "")


def b_alerts(G):
    n = G["rec"].get("nws") or {}
    al = n.get("alerts")
    if al:
        al = [a for a in al if (a.get("event") or "") not in IGNORED_ALERTS]  # NWS system test messages are not alerts
    zone = G["zone"]
    when = esc(tzl(parse_t(n["fetched_at"]), zone)) if n.get("fetched_at") else "time not stated"
    age = hours_old(n.get("fetched_at"), G["now"]) if n.get("fetched_at") else None
    if al is None:
        body = '<p>Alerts could not be loaded at the last fetch.</p>'
    elif not al:
        body = '<p>No active National Weather Service alerts were returned for this location. This is not a statement that conditions are safe.</p>'
    else:
        items = ""
        for a in al:
            ends = esc(tzl(parse_t(a["ends"] or a["expires"]), zone)) if (a.get("ends") or a.get("expires")) else "not stated"
            items += '<div class="alert sev-%s"><b>%s</b> &middot; %s &middot; %s<br>%s<br>Ends %s</div>' % ((a.get("severity") or "unknown").lower(), esc(a.get("event") or ""), esc(a.get("severity") or "severity not stated"), esc(area_short(a.get("areaDesc") or "", 6, (((G["rec"].get("meta") or {}).get("loc")) or {}).get("county_name")) + ((" (" + ", ".join(a["states"]) + ")") if a.get("states") else "")), esc(a.get("headline") or ""), ends)
        body = items
    return block("alerts", "Weather alerts", "official", body, "Source: National Weather Service alerts for the gauge location, fetched %s." % when, "nws", amber=(age is not None and age > 3))


def b_land(G):
    land = G["rec"].get("land")
    if not land or not land.get("rows"):
        return None
    seen_l, uniq = set(), []
    for t in land["rows"]:
        if tuple(t) not in seen_l:
            seen_l.add(tuple(t))
            uniq.append(t)
    rows = "".join(tr([esc(u), esc(PADMAN.get(m, m or "n/a")), esc(ACCESS.get(a, a or "n/a"))]) for u, m, a in uniq[:12])
    return block("public_land", "Public land at this gauge", "map", table(["Unit", "Managed by", "Public access"], rows),
                 "Source: USGS Protected Areas Database (PAD-US), within about half a mile of the gauge, downloaded %s. Mapped land is not proof of legal access." % fdate(land["downloaded"]), "padus")


# ---------------------------------------------------------------- final-form blocks
COMP = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
YCOL = ["var(--accent)", "#d9822b", "#2e9d6a", "#8a6bd1"]
YDASH = ["", "7 3", "2 3", "10 3 2 3"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def compass(d):
    return COMP[int((d % 360) / 22.5 + 0.5) % 16]


def tint(frac):
    return "color-mix(in srgb,var(--accent) %d%%,var(--card))" % round(max(0, min(1, frac)) * 55)


def _multi_svg(ser, years, asof, span, W, Hh, fs, nx, cls):
    L, B = (56, 30) if W > 500 else (46, 28)
    vals = [v for y in years for v in ser[y] if v is not None]
    vmin, vmax, ticks = nice_ticks(min(vals), max(vals))
    X = lambda i: L + i / (span - 1) * (W - L - 14)
    Y = lambda v: 12 + (1 - (v - vmin) / ((vmax - vmin) or 1)) * (Hh - B - 12)
    grid = "".join('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--line)"/><text x="%d" y="%.1f" font-size="%d" fill="var(--mut)" text-anchor="end">%s</text>' % (
        L, W - 14, Y(tv), Y(tv), L - 6, Y(tv) + 4, fs, tf(tv, ticks)) for tv in ticks)
    start = asof - datetime.timedelta(days=span - 1)
    xl = ""
    for k in range(nx):
        i = round((span - 1) * k / (nx - 1))
        xl += '<text x="%.1f" y="%d" font-size="%d" fill="var(--mut)" text-anchor="%s">%s</text>' % (X(i), Hh - 8, fs, "start" if k == 0 else "end" if k == nx - 1 else "middle", (start + datetime.timedelta(days=i)).strftime("%b %d").replace(" 0", " "))
    lines = ""
    for n, y in reversed(list(enumerate(years))):
        seg, segs = [], []
        for i, v in enumerate(ser[y]):
            if v is None:
                if seg:
                    segs.append(seg)
                seg = []
            else:
                seg.append("%.1f,%.1f" % (X(i), Y(v)))
        if seg:
            segs.append(seg)
        for s in segs:
            lines += '<polyline points="%s" fill="none" stroke="%s" stroke-width="%s"%s/>' % (" ".join(s), YCOL[n], "2.8" if n == 0 else "1.8", (' stroke-dasharray="%s"' % YDASH[n]) if YDASH[n] else "")
    return '<svg class="%s" viewBox="0 0 %d %d" width="100%%" role="img" aria-label="Daily mean flow in cfs for the same %d-day window in %d years">%s%s%s</svg>' % (cls, W, Hh, span, len(years), grid, xl, lines)


def b_multiyear(G):
    m = G["rec"].get("multiyear")
    if not m:
        return None
    ser, span = m["series"], m["span"]
    years = sorted(ser, reverse=True)
    asof = datetime.date.fromisoformat(m["as_of"])
    if (G["ldate"] - asof).days > 10:
        return None
    svg = _multi_svg(ser, years, asof, span, 760, 260, 11, 6, "cw") + _multi_svg(ser, years, asof, span, 340, 260, 12, 4, "cn")
    legend = '<p class="legend">%s</p>' % " &nbsp; ".join('<b><span style="color:%s" aria-hidden="true">%s</span>&nbsp;%s</b>' % (YCOL[n], "&#9473;" if not YDASH[n] else "&#9548;", esc(y)) for n, y in enumerate(years))
    rows = ""
    for y in years:
        v = [x for x in ser[y] if x is not None]
        if len(v) >= 0.8 * span:
            rows += tr([esc(y), "%s cfs" % fmt(sum(v) / len(v)), "%s cfs" % fmt(max(v))], right=(1, 2))
    start = asof - datetime.timedelta(days=span - 1)
    return block("multi_year", "The same %d days in earlier years" % span, "hist", svg + legend + table(["Year", "Mean flow", "Highest day"], rows, right=(1, 2)),
                 "Source: USGS daily mean flows (Water Data API). Each line is the %d days from %s to %s, shifted to the same calendar dates in earlier years; gaps are days without a published value. Recent days are provisional." % (
                     span, start.strftime("%b %d").replace(" 0", " "), asof.strftime("%b %d").replace(" 0", " ")), "usgs")


def b_peaks(G):
    p = G["rec"].get("peaks")
    rows = [r for r in (p or {}).get("rows", []) if r[1] is not None]
    if len(rows) < 5:
        return None
    top = "".join(tr([fdate(r[0]), "%s cfs" % fmt(r[1]), ("%.2f ft" % r[2]) if r[2] is not None else "–"], right=(1, 2)) for r in sorted(rows, key=lambda r: -r[1])[:10])
    recent = "".join(tr([fdate(r[0]), "%s cfs" % fmt(r[1]), ("%.2f ft" % r[2]) if r[2] is not None else "–"], right=(1, 2)) for r in sorted(rows, key=lambda r: r[0], reverse=True)[:5])
    heads = ["Date", "Peak flow", "Gage height at peak"]
    dec = {}
    for r in rows:
        dec.setdefault(r[0][:3] + "0s", []).append(r[1])
    drows = "".join(tr([d, str(len(v)), "%s cfs" % fmt(sorted(v)[len(v) // 2] if len(v) % 2 else (sorted(v)[len(v) // 2 - 1] + sorted(v)[len(v) // 2]) / 2), "%s cfs" % fmt(max(v))], right=(1, 2, 3)) for d, v in sorted(dec.items()) if len(v) >= 5)
    by_decade = ("<h3>Median annual peak by decade (calendar year of the peak date)</h3>" + table(["Decade", "Peaks on file", "Median peak", "Largest peak"], drows, right=(1, 2, 3))) if drows else ""
    return block("annual_peaks", "Largest annual peaks", "hist", "<h3>Ten largest peaks of record</h3>" + table(heads, top, right=(1, 2)) + "<h3>Five most recent annual peaks</h3>" + table(heads, recent, right=(1, 2)) + by_decade,
                 "Source: USGS annual peak streamflow (Water Data API), %d annual peaks, %s to %s. A water year's peak is its highest instantaneous flow. Gage height at older peaks can be on a different datum. Decades with fewer than 5 peaks are left out." % (len(rows), rows[0][0][:4], rows[-1][0][:4]), "usgs")


def b_wtemp(G):
    w = G["rec"].get("wtemp")
    if not w or not w.get("months"):
        return None
    cards = "".join('<div class="fc"><div>%s</div><b>%.0f&deg;F</b><div class="legend">%s days%s</div></div>' % (MONTHS[int(m) - 1], c * 9 / 5 + 32, fmt(n), " (few)" if n < 150 else "") for m, (c, n) in sorted(w["months"].items(), key=lambda x: int(x[0])))
    return block("water_temp_months", "Typical water temperature by month", "hist", '<div class="fcs">%s</div>' % cards,
                 "Source: USGS daily mean water temperature (parameter 00010, Water Data API), %s to %s, mean of all published daily values in each calendar month (days counted under each month; (few) means fewer than 150 daily values)." % (esc(w["first_year"]), esc(w["last_year"])), "usgs")


def crest_date(t, zone):
    if str(t).endswith("T00:00:00Z"):  # date-only value stored as midnight UTC: not a moment, so no zone shift
        return fdate(str(t)[:10])
    return fdate(parse_t(t).astimezone(zone).date().isoformat())


def b_crests(G):
    n = G["rec"].get("nwps") or {}
    cr = n.get("crests") or []
    if not cr:
        return None
    unit = (n.get("stage_units") or "ft").lower()
    rows = "".join(tr([crest_date(c["t"], G["zone"]) if c.get("t") else "–", "%.2f %s" % (c["stage"], esc(unit)), ("%s cfs" % fmt(c["flow"])) if isinstance(c.get("flow"), (int, float)) and c["flow"] > 0 else "–"], right=(1, 2)) for c in cr)
    return block("historic_crests", "Historic crests", "official", table(["Date", "Crest stage", "Flow"], rows, right=(1, 2)),
                 "Source: National Weather Service forecast point %s (%s), historic crests as published by the NWS; the NWS may have recorded them on an older gauge datum. The USGS annual peaks above are a separate record and can differ in date, flow and datum." % (esc(n.get("lid") or ""), esc(n.get("name") or "")), "nwps")


def next_impact(G):
    """The next NWS impact statement above the latest reading, short, for the gage tile: the first thing a wader or boater wants to know about the level."""
    n = G["rec"].get("nwps") or {}
    im = n.get("impacts") or []
    if not im or not G["sg"]:
        return ""
    gap = datum_gap(G)
    cur = gap[0] if gap else G["sg"][-1][1]
    unit = (n.get("stage_units") or "ft").lower()
    ahead = sorted((i for i in im if isinstance(i.get("stage"), (int, float)) and i["stage"] > cur and len((i.get("statement") or "").strip()) >= 30), key=lambda i: i["stage"])
    if not ahead:
        return ""
    i = ahead[0]
    txt = i["statement"].strip()
    end = txt.find(". ")
    if 20 <= end < 160:
        txt = txt[:end + 1]
    elif len(txt) > 160:
        cut = txt.rfind(" ", 0, 157)
        txt = txt[:cut if cut > 40 else 157] + "\u2026"
    return "Next NWS impact at %.1f %s, %.1f %s above" % (i["stage"], esc(unit), i["stage"] - cur, esc(unit))


def b_impacts(G):
    n = G["rec"].get("nwps") or {}
    im = n.get("impacts") or []
    if not im:
        return None
    unit = (n.get("stage_units") or "ft").lower()
    by = {}
    for i in im:
        by.setdefault(i["stage"], [])
        if i["statement"] not in by[i["stage"]]:
            by[i["stage"]].append(i["statement"])
    rows = "".join(tr(["%.1f %s" % (s_, esc(unit)), "<br>".join(esc(x) for x in by[s_])], right=(0,)) for s_ in sorted(by))
    pn = nws_point_note(G)
    gap_ = datum_gap(G)
    cur_ = gap_[0] if gap_ else (G["sg"][-1][1] if G["sg"] else None)  # the reading on the NWS scale
    ss = sorted(by)
    below_ = [x for x in ss if cur_ is not None and x <= cur_]
    start = ss.index(below_[-1]) if below_ else 0
    icards = []
    for s_ in ss[start:start + 6]:
        txt = " / ".join(by[s_])
        short, cut = txt, False
        if len(txt) > 260:  # cut only at the end of a sentence and say so; never mid-sentence
            k = txt.rfind(". ", 0, 260)
            if k > 60 and txt[k - 1] != ".":
                short, cut = txt[:k + 1], True
        margin = "" if cur_ is None else ("reached at the latest reading" if s_ <= cur_ else "%.1f %s above the latest reading" % (s_ - cur_, esc(unit)))
        if cut:
            margin = (margin + "; " if margin else "") + "rest of the statement in the full list below"
        icards.append(card("%s%s" % ("At " if s_ <= (cur_ if cur_ is not None else -1e9) else "Next: ", "%.1f %s" % (s_, esc(unit))), esc(short), margin))
    itable = table(["Stage", "National Weather Service impact statement"], rows, right=(0,))
    return block("flood_impacts", "Flood impacts by stage", "official", (('<p class="src">%s</p>' % esc(pn)) if pn else "") + rail(icards, "Flood impacts by stage") + more("All %d impact statements in full" % len(ss), itable),
                 "Source: National Weather Service forecast point %s (%s). Statements are quoted from the NWS and describe that forecast point." % (esc(n.get("lid") or ""), esc(n.get("name") or "")), "nwps")


def b_snotel(G):
    s = G["rec"].get("snotel") or {}
    st = [x for x in s.get("stations", []) if (G["ldate"] - datetime.date.fromisoformat(x["date"])).days <= 5]
    if not st:
        return None
    rows = ""
    for x in st:
        med = x.get("median_in")
        pct = ("%.0f%%" % (x["swe_in"] / med * 100)) if med else "–"
        rows += tr([esc(x["name"]), "%d mi" % round(x["km"] * 0.621371), ("%s ft" % fmt(x["elev_ft"])) if x.get("elev_ft") else "–", "%.1f in" % x["swe_in"], ("%.1f in" % med) if med is not None else "–", pct, fdate(x["date"])], right=(1, 2, 3, 4, 5))
    from lib import ui
    sb = ui.bars([(esc(x["name"]), (x["swe_in"] / x["median_in"] * 100) if x.get("median_in") else None, ("%.0f%% of median (%.1f in, median %.1f in)" % (x["swe_in"] / x["median_in"] * 100, x["swe_in"], x["median_in"])) if x.get("median_in") else "%.1f in, no median" % x["swe_in"]) for x in st], 150, mark=100)
    return block("snowpack", "Snow water equivalent at nearby SNOTEL stations", "obs", sb + table(["Station", "Distance", "Elevation", "Snow water now", "Median for date", "Of median", "Date"], rows, right=(1, 2, 3, 4, 5), hide=(1, 2)),
                 "Source: USDA Natural Resources Conservation Service SNOTEL stations within 37 miles of the gauge (AWDB web service), fetched %s. Provisional data; stations may not drain to this gauge." % esc(tzl(parse_t(s["fetched_at"]), G["zone"])), "nrcs")


def b_cpc(G):
    rows = ""
    ocards = []
    src_bits = []
    for key, name in (("cpc610", "6 to 10 day"), ("cpc", "8 to 14 day")):
        c = G["rec"].get(key)
        if not c or not (c.get("temp") or c.get("precip")) or not c.get("issued"):
            continue
        try:
            iss = datetime.datetime.strptime(c["issued"], "%m/%d/%Y").date()
            a_, z_ = (datetime.datetime.strptime(c[k], "%m/%d/%Y").date() for k in ("start", "end"))
        except (KeyError, ValueError):
            continue
        if (G["ldate"] - iss).days > 3:
            continue
        span = "%s to %s" % (a_.strftime("%b %d").replace(" 0", " "), z_.strftime("%b %d").replace(" 0", " "))
        for k, lab in (("temp", "Temperature"), ("precip", "Precipitation")):
            if c.get(k):
                rows += tr([name, span, lab, esc(c[k]["category"] or "–"), "%d%%" % c[k]["prob"]], right=(4,))
                ocards.append(card("%s &middot; %s" % (name, lab), esc(c[k]["category"] or "–"), "%s &middot; probability %d%%" % (span, c[k]["prob"])))
        src_bits.append("%s for %s" % (name, span))
    if not rows:
        return None
    return block("cpc_outlook", "Temperature and precipitation outlooks", "official", rail(ocards, "Temperature and precipitation outlooks"),
                 "Source: NOAA Climate Prediction Center outlooks at the gauge location (%s), issued %s. A probability is the chance of the leaning category (above, near or below normal) for the whole period, not an amount." % ("; ".join(src_bits), iss.strftime("%b %d").replace(" 0", " ")), "cpc")


def b_map(G):
    lat, lon, R = G["lat"], G["lon"], 6378137.0
    half = 8000 / math.cos(math.radians(lat))
    cx, cy = R * math.radians(lon), R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    bbox = "%.0f,%.0f,%.0f,%.0f" % (cx - half, cy - half * 0.5625, cx + half, cy + half * 0.5625)
    src = "https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/export?bbox=%s&bboxSR=3857&imageSR=3857&size=640,360&format=png&f=image" % bbox
    return block("gauge_map", "Gauge location", "map", '<div class="mapimg"><img src="%s" alt="USGS topographic map centred on %s, about 10 miles across" width="640" height="360" loading="lazy"><i aria-hidden="true"></i></div>' % (src, esc(G["place"])),
                 "Source: Map services and data available from U.S. Geological Survey, National Geospatial Program (USGS Topo). Map about 10 miles across, centred on the gauge at %.4f, %.4f." % (lat, lon), "natmap")


# ---------------------------------------------------------------- tabs
TABS = {
    "dashboard": {"label": "Conditions", "title": "%s, %s: river level and flow", "desc": "%s, %s: current flow, gage height, how it compares with past years, alerts, history and flood record from USGS gauge %s.", "hero": True},
    "forecast": {"label": "Forecast", "title": "%s, %s: river forecast", "desc": "%s, %s: river forecast, rain, radar and weather forecast for USGS gauge %s.", "hero": False},
}


def b_nearby(G, pages):
    """Other gauges on the site close to this one (up to five within 60 miles, nearest first), each with latest flow and the plain-word comparison. Upstream and downstream gauges are in their own strip and are skipped here."""
    skip = {G["site"]} | {x["site"] for x in ((G["rec"].get("related") or {}).get("items") or [])}
    out = []
    for s, p in pages.items():
        if s in skip or not p.get("_built") or not p.get("_ll"):
            continue
        la1, lo1, la2, lo2 = map(math.radians, (G["lat"], G["lon"], p["_ll"][0], p["_ll"][1]))
        mi = 3958.8 * 2 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))
        if mi <= 60:  # nearby means a short drive: the first reviews called 107 and 127 miles not nearby
            out.append((mi, p))
    if not out:
        return None
    out.sort(key=lambda x: x[0])
    lis = "".join('<li><a href="%s">%s</a><span>%s cfs &middot; %s &middot; %d mi away</span></li>' % (p["water_url"], esc(river_at(p["river"], p["place"]) + ", " + p["state"]), fmt(p["_lv"]), esc(p["_band"].lower()), round(mi)) for mi, p in out[:5])
    return block("nearby_gauges", "Other gauges nearby", "live", '<ul class="nbr">%s</ul>' % lis,
                 "Source: USGS Water Data API latest readings at the gauges on this site, as of this page's build; the comparison is our estimate from USGS daily statistics for the date. Distance is straight-line from this gauge.", "usgs")


def b_official_links(G):
    """Where to go next: the source pages for this gauge, opened in a new tab."""
    n = G["rec"].get("nwps") or {}
    lid = n.get("lid")
    links = [("USGS page for this gauge", "https://waterdata.usgs.gov/monitoring-location/%s/" % G["site"]), ("USGS WaterAlert: text or email when this gauge crosses a level you choose", "https://waterdata.usgs.gov/nwis/wateralert")]
    if lid:
        links.append(("NWS river page for forecast point %s" % lid, "https://water.noaa.gov/gauges/%s" % lid))
    links.append(("NWS forecast for this location", "https://forecast.weather.gov/MapClick.php?lat=%.4f&lon=%.4f" % (G["lat"], G["lon"])))
    links.append(("NWS active alerts for this location", "https://alerts.weather.gov/search?point=%.4f,%.4f" % (G["lat"], G["lon"])))
    body = '<ul class="olinks">%s</ul>' % "".join('<li><a href="%s" rel="noopener" target="_blank">%s</a></li>' % (esc(h), esc(t)) for t, h in links)
    return block("official_links", "Official pages for this gauge", "agency", body, "Source: links to the agencies that publish the data on this page (USGS, NOAA National Weather Service); they open in a new tab.", "usgs")


def sun_times(lat, lon, d, alt=-0.833):
    jd0 = (datetime.datetime(d.year, d.month, d.day, tzinfo=datetime.timezone.utc).timestamp() / 86400) + 2440587.5
    n = math.ceil(jd0 - 2451545.0 + 0.0008)
    js = n + 0.0009 - lon / 360
    rad = math.radians
    M = (357.5291 + 0.98560028 * js) % 360
    C = 1.9148 * math.sin(rad(M)) + 0.02 * math.sin(rad(2 * M)) + 0.0003 * math.sin(rad(3 * M))
    lam = (M + C + 180 + 102.9372) % 360
    jt = 2451545.0 + js + 0.0053 * math.sin(rad(M)) - 0.0069 * math.sin(rad(2 * lam))
    dec = math.asin(math.sin(rad(lam)) * math.sin(rad(23.4397)))
    cw = (math.sin(rad(alt)) - math.sin(rad(lat)) * math.sin(dec)) / (math.cos(rad(lat)) * math.cos(dec))
    if cw < -1 or cw > 1:
        return None
    w = math.degrees(math.acos(cw))
    to = lambda J: datetime.datetime.fromtimestamp((J - 2440587.5) * 86400, datetime.timezone.utc)
    return to(jt - w / 360), to(jt + w / 360)


def moon_phase(d):
    """Moon phase from the date (computed, mean synodic month from the 2000-01-06 new moon): name and percent lit."""
    age = ((datetime.datetime(d.year, d.month, d.day, 12, tzinfo=datetime.timezone.utc).timestamp() / 86400 + 2440587.5) - 2451550.1) % 29.530588853
    names = ["New moon", "Waxing crescent", "First quarter", "Waxing gibbous", "Full moon", "Waning gibbous", "Last quarter", "Waning crescent"]
    return names[int((age / 29.530588853) * 8 + 0.5) % 8], 50 * (1 - math.cos(2 * math.pi * age / 29.530588853))


def b_sun(G):
    st = sun_times(G["lat"], G["lon"], G["ldate"])
    if not st:
        return None
    z = G["zone"]
    rows = tr(["Sunrise", esc(tzl(st[0], z, date=False))], right=(1,)) + tr(["Sunset", esc(tzl(st[1], z, date=False))], right=(1,))
    return block("sun", "Sun", "calc", table(["Event", "Time (gauge-local)"], rows, right=(1,)), "Source: computed from the gauge location and date %s. No external data." % G["ldate"].isoformat(), "usgs")


def b_air(G):
    o = (G["rec"].get("nws") or {}).get("obs")
    if not o:
        return None
    age = hours_old(o["timestamp"], G["now"])
    if age is not None and age > 12:
        return None
    rows = []
    if o.get("temp_c") is not None:
        rows.append(("Air temperature", "%.0f °F" % (o["temp_c"] * 9 / 5 + 32)))
    if o.get("wind_kmh") is not None:
        mph = o["wind_kmh"] * 0.621371
        d = o.get("wind_dir")
        comp = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"][int((d % 360) / 22.5 + 0.5) % 16] + " " if d is not None else ""
        rows.append(("Wind", "Calm" if mph < 1 else "%s%.0f mph" % (comp, mph)))
    if o.get("gust_kmh") is not None:
        rows.append(("Gusts", "%.0f mph" % (o["gust_kmh"] * 0.621371)))
    if o.get("pressure_pa") is not None:
        inhg = o["pressure_pa"] / 3386.389
        tr_txt = ""
        if o.get("pressure_prev_pa") is not None:
            dl = (o["pressure_pa"] - o["pressure_prev_pa"]) / 3386.389
            tr_txt = ", steady" if abs(dl) < 0.02 else ", rising" if dl > 0 else ", falling"
        rows.append(("Pressure", "%.2f inHg%s" % (inhg, tr_txt)))
    if o.get("visibility_m") is not None:
        rows.append(("Visibility", "%.0f mi" % (o["visibility_m"] / 1609.34)))
    if not rows:
        return None
    body = table(["Measure", "Value"], "".join(tr([esc(a), esc(b)], right=(1,)) for a, b in rows), right=(1,))
    return block("air_obs", "Air conditions", "obs", body, "Source: National Weather Service station %s, observed %s." % (esc(o["station"]), esc(tzl(parse_t(o["timestamp"]), G["zone"]))), "nws", amber=(age is not None and age > 3))


def b_radar(G):
    st = (G["rec"].get("nws") or {}).get("radar")
    if not st:
        return None
    return block("radar", "Radar", "official", '<img src="https://radar.weather.gov/ridge/standard/%s_loop.gif" alt="Radar loop, station %s" width="600" height="550" loading="lazy" style="max-width:100%%;height:auto">' % (esc(st), esc(st)),
                 "Source: National Weather Service radar, station %s. The loop is served live by the NWS and shows its own frame times." % esc(st), "rfc")


def b_weather(G, n_periods=14):
    n = G["rec"].get("nws") or {}
    per = n.get("periods") or []
    if not per:
        return None
    age = hours_old(n.get("forecast_updated"), G["now"]) if n.get("forecast_updated") else None
    if age is not None and age > 48:
        return None
    cards = ""
    live = []
    for p in per:
        try:
            gone_ = p.get("endTime") and parse_t(p["endTime"]) <= G["now"]
        except (TypeError, ValueError):
            gone_ = False
        if not gone_ and not (not p.get("endTime") and p.get("isDaytime") and G["now"].astimezone(G["zone"]).hour >= 19):
            live.append(p)
    for p in live[:n_periods]:
        pop = p.get("pop")
        cards += ('<div class="fc"><div>%s</div><b>%s&deg;%s</b><div>%s</div><div class="legend">Wind %s %s</div><div class="legend">%s</div></div>' % (
            esc(p.get("name") or ""), esc(str(p.get("temperature"))), esc(p.get("temperatureUnit") or "F"), esc(p.get("shortForecast") or ""), esc(p.get("windSpeed") or ""), esc(p.get("windDirection") or ""),
            ("%s%% rain" % pop) if pop is not None else ""))
    upd = esc(tzl(parse_t(n["forecast_updated"]), G["zone"])) if n.get("forecast_updated") else "time not stated"
    return block("weather_forecast", "Weather forecast", "official", '<div class="fcs">%s</div>' % cards, "Source: National Weather Service point forecast, updated %s." % upd, "nws", amber=(age is not None and age > 12))


def b_hourly(G):
    n = G["rec"].get("nws") or {}
    hr = n.get("hourly") or []
    age = hours_old(n.get("hourly_updated"), G["now"]) if n.get("hourly_updated") else None
    if not hr or age is None or age > 72:
        return None
    rows = ""
    for p in [p for p in hr if parse_t(p["startTime"]) > G["now"] - datetime.timedelta(hours=1)][:24]:
        pop = p.get("pop")
        rows += tr([esc(tzl(parse_t(p["startTime"]), G["zone"], date=False)), "%s °%s" % (esc(str(p.get("temperature"))), esc(p.get("temperatureUnit") or "F")),
                    "%s %s" % (esc(p.get("windDirection") or ""), esc(p.get("windSpeed") or "")), "%s%%" % pop if pop is not None else "–", esc(p.get("shortForecast") or "")], right=(1, 3))
    if not rows:
        return None
    return block("hourly_forecast", "Hourly forecast, next 24 hours", "official", storm_line(G) + table(["Hour", "Temp", "Wind", "Rain chance", "Sky"], rows, right=(1, 3)),
                 "Source: National Weather Service hourly point forecast, updated %s." % esc(tzl(parse_t(n["hourly_updated"]), G["zone"])), "nws", amber=(age > 12))


def b_heatmap(G):
    n = G["rec"].get("nws") or {}
    g = n.get("grid") or {}
    age = hours_old(g.get("updated"), G["now"]) if g.get("updated") else None
    hrs = [h for h in g.get("hours", []) if parse_t(h["t"]) > G["now"] - datetime.timedelta(hours=1)][:24]
    if len(hrs) < 12 or (age is not None and age > 72):
        return None
    pop = {}
    for p in n.get("hourly") or []:
        pop[parse_t(p["startTime"]).replace(minute=0, second=0, microsecond=0)] = p.get("pop")
    zone = G["zone"]
    head = "<th></th>"
    for h in hrs:
        d = parse_t(h["t"]).astimezone(zone)
        head += "<th>%s</th>" % ("%s 12a" % d.strftime("%a") if d.hour == 0 else "%d%s" % (d.hour % 12 or 12, "a" if d.hour < 12 else "p"))
    mph = lambda k: (lambda v: None if v is None else v * 0.621371)(k)
    spec = (("Temp &deg;F", lambda h: None if h.get("temp_c") is None else h["temp_c"] * 9 / 5 + 32, lambda v: (v - 20) / 90, "%.0f"),
            ("Wind mph", lambda h: mph(h.get("wind_kmh")), lambda v: v / 30, "%.0f"),
            ("Gust mph", lambda h: mph(h.get("gust_kmh")), lambda v: v / 40, "%.0f"),
            ("Direction", lambda h: h.get("dir"), None, None),
            ("Cloud %", lambda h: h.get("sky"), lambda v: v / 100, "%.0f"),
            ("Thunder %", lambda h: h.get("thunder"), lambda v: v / 100, "%.0f"),
            ("Humidity %", lambda h: h.get("rh"), lambda v: v / 100, "%.0f"),
            ("Heat index &deg;F", lambda h: None if h.get("heat_c") is None else h["heat_c"] * 9 / 5 + 32, lambda v: (v - 20) / 90, "%.0f"),
            ("Visibility mi", lambda h: None if h.get("vis_m") is None else h["vis_m"] / 1609.344, lambda v: v / 10, "%.0f"),
            ("Rain in/h", lambda h: None if h.get("qpf_mm") is None else h["qpf_mm"] / 25.4, lambda v: v / 0.1, "%.2f"),
            ("Rain chance %", lambda h: pop.get(parse_t(h["t"])), lambda v: v / 100, "%.0f"))
    rows = ""
    for lab, get, sc, f in spec:
        cells = ""
        for h in hrs:
            v = get(h)
            if v is None:
                cells += "<td>&ndash;</td>"
            elif sc is None:
                cells += "<td>%s</td>" % compass(v)
            else:
                cells += '<td style="background:%s">%s</td>' % (tint(sc(v)), (f % v) if not (lab == "Rain in/h" and v < 0.005) else "0")
        rows += "<tr><th>%s</th>%s</tr>" % (lab, cells)
    upd = esc(tzl(parse_t(g["updated"]), zone)) if g.get("updated") else "time not stated"
    return block("hourly_heatmap", "Hourly forecast, next 24 hours", "official", storm_line(G) + '<div class="scroll"><table class="hm"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (head, rows),
                 "Source: National Weather Service gridpoint forecast, updated %s; rain chance from the NWS hourly point forecast. Hours are gauge-local. Darker cells mean a higher value in that row." % upd, "nws", amber=(age is not None and age > 12))

def tab_blocks(tab, G, pages):
    if tab == "dashboard":  # one page per gauge, ordered by what a person at the water asks: is it dangerous, what is the water like, what is coming, how does it compare; "SEC:" is a heading, "FOLD:" a closed group
        has_al = any((x.get("event") or "") not in IGNORED_ALERTS for x in ((G["rec"].get("nws") or {}).get("alerts") or []))
        return [b2.b_offline(G)] + ([b_alerts(G)] if has_al else []) + [
                "SEC:What the water is like now", b_quality(G), b3.b_tides(G), b_heatmap(G) or b_hourly(G), b_weather(G, 6), b_air(G), b_rain(G), b_radar(G),
                "SEC:Level, flow and flood risk", b_flow_chart(G), b2.b_stage_chart(G), b_impacts(G)] + ([] if has_al else [b_alerts(G)]) + ["AD", b2.b_rate(G)] + ([
                "SEC:Forecast", b_river_forecast(G), b_nwm(G), b2.b_nwm_medium(G), b2.b_noforecast(G), b3.b_wpc(G), b3.b_acis(G), b2.b_qpf(G), b2.b_atlas14(G), b_cpc(G)]) + [
                "SEC:How today compares with past years", b3.b_month_chart(G), b3.b_year_chart(G), b_multiyear(G), b_record(G), b_wtemp(G), b_snotel(G),
                "FOLD:Flood record and history", b_peaks(G), b3.b_stage_years(G), b3.b_floodfreq(G), b_crests(G), b3.b_flood_outlook(G),
                "FOLD:Daily values, measurements and rating", b_daily(G), b3.b_field_meas(G), b2.b_rating(G), b3.b_rise(G),
                "FOLD:Watershed, water quality and land", b2.b_drought(G), b2.b_attains(G), b3.b_streamcat(G), b3.b_dams(G), b3.b_fema_zone(G), b_land(G),
                b_related(G, pages), b_nearby(G, pages), b3.b_nws_point(G, pages), b_map(G), b_official_links(G), b2.b_about(G)]
    return []  # only the dashboard tab is built (one page per gauge)


def footer():
    return ('<footer><span>%s &middot; Data: USGS, NOAA, NWS.</span><span><a href="/about/">About</a> &middot; <a href="/data-sources/">Data sources</a> &middot; <a href="/disclaimer/">Disclaimer</a> &middot; '
            '<a href="/faq/">FAQ</a> &middot; <a href="/methodology/">Methodology</a> &middot; <a href="/privacy/">Privacy</a> &middot; <a href="/glossary/">Glossary</a> &middot; <a href="/status/">Data status</a></span></footer>' % esc(BRAND))


def og_tags(title, desc, url):
    return ('<meta property="og:type" content="website"><meta property="og:site_name" content="%s"><meta property="og:title" content="%s"><meta property="og:description" content="%s"><meta property="og:url" content="%s"><meta property="og:image" content="%s/og.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="River Water Levels: current flow, gage height and how it compares with normal for US river gauges"><meta name="twitter:card" content="summary_large_image">'
            % (esc(BRAND), esc(title), esc(desc), esc(url), SITE_URL))


def mk_title(base):
    return base  # one pattern on every page; the brand sits in the nav


def humanize_iso(text):
    return re.sub(r"\d{4}-\d{2}-\d{2}", lambda m: fdate(m.group(0)), text)


def nav():
    return '<a class="skip" href="#main">Skip to content</a><nav class="nav" aria-label="Site"><a class="brand" href="/"><span class="logo"></span>%s</a><span class="tabs"><a href="/">Rivers</a><a href="/about/">About</a></span><span class="ns"><input id="gq" type="search" placeholder="Find a river or place" aria-label="Find a river or place" autocomplete="off"><span id="gr" class="gr" hidden></span></span><button type="button" class="themebtn" id="themebtn" aria-label="Switch between dark and light" title="Dark or light">&#9680;</button></nav>' % esc(BRAND) + THEME_JS + NAVSEARCH_JS + FOLD_JS


def sources_block(blocks, G):
    ids = []
    for b in blocks:
        for sid in [b["src_id"]] + list(b.get("also") or []):
            if sid not in ids:
                ids.append(sid)
    if "usgs" not in ids:
        ids.insert(0, "usgs")
    lis = ""
    for i in ids:
        s = SOURCES[i]
        lis += '<li>%s. <a href="%s" rel="noopener">Terms</a></li>' % (esc((s.get("credit") or s["name"]).rstrip(".")), esc(s["terms_url"]))
    stats_src = G["rec"].get("stats_source")
    return ('<details class="card fold srcall" data-g="data" id="sources"><summary><b>Sources and method</b><span>%d data sources, how the percentile is calculated, disclaimer</span></summary><ul>%s</ul><p class="src">%s</p><p class="src">Percentile method: %s.</p><p class="src">%s</p></details>' % (
        len(ids), lis, esc(humanize_iso(stats_src) if stats_src else "USGS daily statistics: not available for this gauge."), esc(G["method"]), esc(DISCLAIMER)))


LIVE_JS = """<script>(function(){var ID="USGS-@SITE@",Z="@TZ@",hero=document.querySelector('.hero');if(!hero||!window.fetch)return;var snap=Date.parse(hero.getAttribute('data-t')),n=0;
function q(k){return document.querySelector('[data-live="'+k+'"]')}
function f(v){var a=Math.abs(v);return a>=100?Math.round(v).toLocaleString('en-US'):a>=10?v.toFixed(0):a<1?v.toFixed(2):v.toFixed(1)}
function lt(d){return d.toLocaleString('en-US',{timeZone:Z,month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'})}
function age(d){var m=Math.round((Date.now()-d)/60000);return m<180?m+' min':m<2880?Math.round(m/60)+' h':Math.round(m/1440)+' d'}
var ag=q('age');if(ag)ag.textContent=age(new Date(snap));
function run(){fetch('https://api.waterdata.usgs.gov/ogcapi/v0/collections/latest-continuous/items?monitoring_location_id='+ID+'&parameter_code=00060,00065&f=json').then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(j){var F=null,S=null;(j.features||[]).forEach(function(x){var p=x.properties,v=parseFloat(p.value);if(isNaN(v))return;if(p.parameter_code==='00060')F={v:v,t:new Date(p.time)};if(p.parameter_code==='00065')S={v:v,t:new Date(p.time)}});
if(F&&F.t.getTime()>=snap){q('flow').textContent=f(F.v);var fo=q('flowobs');if(fo)fo.textContent=lt(F.t);q('obs').textContent=lt(F.t);if(ag)ag.textContent=age(F.t);var st=q('stage'),so=q('stageobs');if(S&&st&&S.t.getTime()>=snap){st.textContent=S.v.toFixed(2);if(so)so.textContent=lt(S.t)}if(F.t.getTime()>snap){[].slice.call(document.querySelectorAll('.fcnote')).forEach(function(e){e.hidden=true});var bn=document.getElementById('lbn');if(!bn){bn=document.createElement('p');bn.id='lbn';bn.className='src lf2';bn.textContent='Flow and gage height at the top updated '+lt(F.t)+'. Charts, tables and comparisons below are as of the page build, '+lt(new Date(snap))+'.';hero.parentNode.insertBefore(bn,hero.nextSibling)}[].slice.call(document.querySelectorAll('.answer .a1,.answer .a2')).forEach(function(e){if(e.textContent.indexOf(' (as of ')<0)});var nt=' The flow above is newer than this comparison, which is as of '+lt(new Date(snap))+'.',pc=document.getElementById('pcap'),cc=document.getElementById('ccap');if(pc){pc.setAttribute('data-n','1')}if(cc&&cc.getAttribute('data-n')!=='1'){cc.textContent+=nt;cc.setAttribute('data-n','1')}}}}).catch(function(){var a=q('age'),hh=document.querySelector('.hero2'),old=hh&&(Date.now()-new Date(hh.getAttribute('data-t')))>3600000;if(a&&old&&!document.getElementById('lf')){var s=document.createElement('span');s.id='lf';s.className='lf';s.textContent=' \u00b7 live check did not answer; showing the page as built';a.parentNode.parentNode.appendChild(s)}})}
run();var iv=setInterval(function(){if(++n>6)return clearInterval(iv);run()},600000)})();</script>"""
AGE_JS = """<script>(function(){var a=document.querySelector('[data-live="age"][data-t]');if(!a)return;var t=Date.parse(a.getAttribute('data-t'));function u(){var m=Math.round((Date.now()-t)/60000);a.textContent=m<180?m+' min':m<2880?Math.round(m/60)+' h':Math.round(m/1440)+' d'}u();setInterval(u,60000)})();</script>"""
SAFETY = '<p class="src safety">Information from government sources, shown with the time it was observed or issued. It is not a flood warning and it does not decide for you: no alert does not mean conditions are safe. It shows the readings a person uses to judge whether to fish, paddle, swim, tube or wade today; the judgement is yours. <a href="/disclaimer/">Disclaimer</a></p>'
# the phone tab of a block: by id, because a gauge with no river forecast has no "Forecast" heading to start the weather group
# phone tab of a block: its "SEC:" heading decides (What the water / Level, flow = Now; Forecast = Forecast; How today = History; folds and the side column = Data / Area); these few ids override their section
GROUP_OF = {"rate_of_change": "history", "snowpack": "data", "water_temp_months": "data", "forecast_rain_totals": "weather", "wpc_outlooks": "weather", "cpc_outlook": "weather"}
RANGE_JS = """<script>(function(){var s=document.querySelectorAll('.rseg');if(!s.length)return;document.documentElement.classList.add('js');s.forEach(function(g){var b=g.parentNode;g.addEventListener('click',function(e){var t=e.target.closest('button');if(!t)return;var r=t.getAttribute('data-r');g.querySelectorAll('button').forEach(function(x){var on=x===t;x.classList.toggle('on',on);x.setAttribute('aria-pressed',on)});b.querySelectorAll('.rg').forEach(function(p){p.classList.toggle('on',p.getAttribute('data-r')===r)})})})})();</script>"""
GTABS_JS = """<script>(function(){var bar=document.querySelector('.gtabs');if(!bar||location.search.indexOf('tabs=off')>=0)return;var m=window.matchMedia('(max-width:760px)'),btns=[].slice.call(bar.querySelectorAll('button')),top=document.getElementById('tabtop');
function grp(el){var g=el&&el.closest?el.closest('[data-g]'):null;return g?g.getAttribute('data-g'):null}
function set(g,scroll){document.querySelectorAll('[data-g]').forEach(function(e){e.classList.toggle('gon',e.getAttribute('data-g')===g)});btns.forEach(function(b){b.classList.toggle('on',b.getAttribute('data-t')===g);b.setAttribute('aria-pressed',b.getAttribute('data-t')===g)});if(scroll&&top)top.scrollIntoView()}
function on(){document.documentElement.classList.add('tabsjs');var h=location.hash.slice(1),t=h&&document.getElementById(h),g=grp(t)||'now';set(g,false);if(t)t.scrollIntoView()}
function off(){document.documentElement.classList.remove('tabsjs')}
function sync(){m.matches?on():off()}
btns.forEach(function(b){b.addEventListener('click',function(){set(b.getAttribute('data-t'),true)})});
window.addEventListener('hashchange',function(){if(!m.matches)return;var t=document.getElementById(location.hash.slice(1)),g=grp(t);if(g){set(g,false);t.scrollIntoView()}});
document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a[href^="#"]');if(!a||!m.matches||a.getAttribute('href').length<2)return;var t=document.getElementById(a.getAttribute('href').slice(1)),g=grp(t);if(g){set(g,false);t.scrollIntoView()}});
window.addEventListener('beforeprint',off);window.addEventListener('afterprint',sync);if(m.addEventListener)m.addEventListener('change',sync);sync()})();</script>"""
FOLD_JS = """<script>(function(){function o(){var h=location.hash.slice(1),e=h&&document.getElementById(h),d=e&&e.closest('details');if(d&&!d.open){d.open=true;e.scrollIntoView()}}
window.addEventListener('hashchange',o);o();window.addEventListener('beforeprint',function(){[].slice.call(document.querySelectorAll('details.fold')).forEach(function(d){d.open=true})})})();</script>"""
THEME_JS = """<script>(function(){var r=document.documentElement,b=document.getElementById('themebtn');try{var s=localStorage.getItem('rwl_theme');if(s==='light'||(!s&&window.matchMedia&&matchMedia('(prefers-color-scheme: light)').matches))r.setAttribute('data-theme','light')}catch(e){}if(b)b.addEventListener('click',function(){var l=r.getAttribute('data-theme')==='light';if(l)r.removeAttribute('data-theme');else r.setAttribute('data-theme','light');try{localStorage.setItem('rwl_theme',l?'dark':'light')}catch(e){}})})();</script>"""
NAVSEARCH_JS = """<script>(function(){var i=document.getElementById('gq'),o=document.getElementById('gr'),d=null;if(!i||!o||!window.fetch)return;function load(){if(d)return Promise.resolve(d);return fetch('/gauges.json').then(function(r){return r.json()}).then(function(j){d=j;return j}).catch(function(){d=[];return d})}
function show(q){q=q.toLowerCase().replace(/\\bst\\.? /g,'saint ').trim();o.textContent='';if(q.length<2){o.hidden=true;return}load().then(function(j){var n=0,hits=[];j.forEach(function(g){if((g[0]+' '+(g[4]||'')).toLowerCase().replace(/[,.]/g,' ').replace(/\\bst\\.? /g,'saint ').replace(/\\s+/g,' ').indexOf(q.replace(/[,.]/g,' ').replace(/\\s+/g,' '))>=0){hits.push(g)}});hits.sort(function(a,b){return (a[0].toLowerCase().indexOf(q)===0?0:1)-(b[0].toLowerCase().indexOf(q)===0?0:1)});hits.slice(0,8).forEach(function(g){var a=document.createElement('a');a.href=g[1];a.textContent=g[0];o.appendChild(a);n++});if(!n){var s=document.createElement('span');s.innerHTML='No match: this site has '+j.length+' gauges so far. <a href="https://water.noaa.gov/" rel="noopener">Look up any river at water.noaa.gov</a>';o.appendChild(s)}o.hidden=false})}
i.addEventListener('input',function(){show(i.value)});i.addEventListener('keydown',function(e){if(e.key==='Enter'){var as=o.querySelectorAll('a[href^="/river/"]'),a=null;for(var k=0;k<as.length;k++){if(as[k].getAttribute('href')!==location.pathname){a=as[k];break}}if(a){e.preventDefault();location.href=a.getAttribute('href')}}});i.addEventListener('focus',load);document.addEventListener('click',function(e){if(!o.contains(e.target)&&e.target!==i)o.hidden=true})})();</script>"""
ALERTS_JS = """<script>(function(){var b=document.getElementById('alerts');if(!b||!window.fetch)return;var Z="@TZ@",CTY="@CTY@",IG=['Test Message','Administrative Message'];
function lt(d){return d.toLocaleString('en-US',{timeZone:Z,month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'})}
function ast(p){var s=[];((p.geocode&&p.geocode.UGC)||[]).forEach(function(u){var k=u.slice(0,2);if(s.indexOf(k)<0)s.push(k)});return s.length?' ('+s.sort().join(', ')+')':''}
function as(s){var a=s.split(';').map(function(x){return x.trim()}).filter(Boolean),c=CTY.toLowerCase().replace(/ (county|parish)$/,'');if(c){var m=a.filter(function(x){var y=x.toLowerCase();return y===c||y.slice(-c.length-1)===' '+c});a=m.concat(a.filter(function(x){return m.indexOf(x)<0}))}return a.length<=6&&!c?s:a.slice(0,6).join('; ')+(a.length>6?'; and '+(a.length-6)+' more areas':'')}
function el(t,c,x){var e=document.createElement(t);if(c)e.className=c;if(x)e.textContent=x;return e}
fetch('https://api.weather.gov/alerts/active?point=@LAT@,@LON@',{headers:{Accept:'application/geo+json'}}).then(function(r){return r.json()}).then(function(j){if(!j||!j.features)return;
var al=j.features.map(function(f){return f.properties}).filter(function(p){return IG.indexOf(p.event)<0}),src=b.querySelector('.srcd')||b.querySelector('.src'),sp=b.querySelector('.src');if(!src||!sp)return;
Array.prototype.slice.call(b.children).forEach(function(c){if(c.tagName!=='H2'&&c!==src)b.removeChild(c)});
if(!al.length){b.insertBefore(el('p','','No active National Weather Service alerts were returned for this location. This is not a statement that conditions are safe.'),src)}
al.forEach(function(p){var d=el('div','alert'),e=p.ends||p.expires;d.appendChild(el('b','',p.event||''));d.appendChild(document.createTextNode(' \\u00b7 '+(p.severity||'severity not stated')+' \\u00b7 '+(as(p.areaDesc||'')+ast(p))));d.appendChild(document.createElement('br'));d.appendChild(document.createTextNode(p.headline||''));d.appendChild(document.createElement('br'));d.appendChild(document.createTextNode('Ends '+(e?lt(new Date(e)):'not stated')));b.insertBefore(d,src)});
var bn=document.querySelector('a.abanner'),hr=document.querySelector('.hero');if(al.length){if(!bn&&hr){bn=el('a','abanner');bn.href='#alerts';hr.parentNode.insertBefore(bn,hr)}if(bn){bn.textContent='';bn.appendChild(el('b','',al.length+' active National Weather Service alert'+(al.length===1?'':'s')));bn.appendChild(el('span','',al.map(function(p){return p.event}).join('; ')));bn.appendChild(el('em','','Details'))}}else if(bn){bn.parentNode.removeChild(bn)}
var t=document.querySelector('.tile.alrt');if(t){var tv=t.querySelector('b'),ts=t.querySelector('small');t.className='tile alrt '+(al.length?'on':'off');if(tv)tv.textContent=al.length||'No alerts';if(ts)ts.textContent=al.length?al.map(function(p){return p.event}).join('; '):'No alerts active here. Checked live '+lt(new Date())+'.'}
var pl=document.querySelector('.answer .a3');if(pl){pl.className='a3 '+(al.length?'ay':'an');pl.textContent=al.length?al.length+' active NWS alert'+(al.length===1?'':'s'):'No active NWS alerts'}
sp.textContent='Source: National Weather Service alerts for the gauge location, fetched '+lt(new Date())+' (live from the NWS when this page loaded).'}).catch(function(){})})();</script>"""
INDEX_CFG = None  # set by build.py from data/index-allow.json


def robots_meta(path):
    from lib import indexing
    return indexing.robots_meta(path, INDEX_CFG) if INDEX_CFG is not None else ""


HEAD_EXTRA = '<link rel="icon" href="/favicon.svg" type="image/svg+xml"><meta name="theme-color" content="#1d5fa8">'


def crumb_ld(items):
    """BreadcrumbList markup that mirrors the visible breadcrumb exactly (name, absolute URL)."""
    els = [{"@type": "ListItem", "position": i + 1, "name": n, **({"item": SITE_URL + u} if u else {})} for i, (n, u) in enumerate(items)]
    return '<script type="application/ld+json">%s</script>' % json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": els}, separators=(",", ":")).replace("</", "<" + chr(92) + "/")


JUMP = (("alerts", "Alerts"), ("flow_chart", "7 days"), ("stage_chart", "Gage height"), ("river_forecast", "River forecast"), ("hourly_heatmap", "Hourly forecast"), ("month_chart", "30 days"), ("multi_year", "Earlier years"),
        ("record_comparison", "Record"), ("annual_peaks", "Flood record"), ("related_gauges", "Upstream and downstream"), ("nearby_gauges", "Nearby gauges"), ("about_gauge", "About"))


CHART_RANGES = (("flow_chart", "7 days"), ("month_chart", "30 days"), ("year_chart", "12 months"), ("multi_year", "Earlier years"))


def merge_charts(blocks):
    """The same flow series drawn four times (7 days, 30 days, 12 months, earlier years) becomes ONE block with a range switch. Every panel keeps its own chart, table and Source line in the HTML."""
    have = {b["id"]: b for b in blocks if isinstance(b, dict) and b["id"] in dict(CHART_RANGES)}
    if "flow_chart" not in have or len(have) < 2:
        return blocks
    first = have["flow_chart"]
    ordered = [(i, lab, have[i]) for i, lab in CHART_RANGES if i in have]
    seg = '<div class="rseg" role="group" aria-label="Time range">%s</div>' % "".join('<button type="button" data-r="%s"%s>%s</button>' % (i, ' class="on" aria-pressed="true"' if k == 0 else ' aria-pressed="false"', lab) for k, (i, lab, _) in enumerate(ordered))
    panels = "".join('<div class="rg%s" data-r="%s"><h3 class="rgh">%s</h3>%s</div>' % (" on" if k == 0 else "", i, lab, b["body"]) for k, (i, lab, b) in enumerate(ordered))
    merged = dict(first, heading="Flow over time", body=seg + panels,
                  source=" ".join("%s: %s" % (lab, b["source"]) for i, lab, b in ordered), also=sorted({x for i, lab, b in ordered for x in [b["src_id"]] + list(b.get("also") or [])} - {first["src_id"]}))
    out = []
    for b in blocks:
        if isinstance(b, dict) and b["id"] in have:
            if b["id"] == "flow_chart":
                out.append(merged)
            continue
        out.append(b)
    return out


def build_tab(tab, G, pages):
    T = TABS[tab]
    row = G["row"]
    raw = tab_blocks(tab, G, pages)
    ok = lambda b: b and (PREVIEW or SOURCES[b["src_id"]]["status"] in ("quoted", "owner-permission"))
    blocks = []
    for b in raw:
        if isinstance(b, str) and b.startswith(("SEC:", "FOLD:")):
            blocks.append(b)
        elif isinstance(b, tuple):  # ("PAIR", a, b): two blocks side by side from 900 px up; a lone survivor renders as a normal block
            g = [x for x in b[1:] if ok(x)]
            blocks.append(g if len(g) > 1 else (g[0] if g else None))
        elif b == "AD" or ok(b):
            blocks.append(b)
    blocks = [b for b in blocks if b]
    blocks = merge_charts(blocks)
    flat = [x for b in blocks for x in (b if isinstance(b, list) else [b])]
    shown = [b for b in flat if isinstance(b, dict)]
    river, place, st = G["river"], G["place"], G["st"]
    rp = river_at(river, place)
    title = mk_title(T["title"] % (rp, st))
    desc = T["desc"] % (rp, st, G["site"])
    url = SITE_URL + row[tab + "_url"] if tab != "dashboard" else SITE_URL + row["dashboard_url"]
    amber = ""  # the age chip in the same line already says how old and colours by age (design review 2026-10-21: one statement of age)
    avail = ("dashboard",)  # one page per gauge: no tabs
    tabs_html = ""  # a lone tab is a dead pill: show tabs only when a Forecast page exists
    for t in (avail if len(avail) > 1 else ()):
        cur = ' class="on" aria-current="page"' if t == tab else ""
        tabs_html += '<a href="%s"%s>%s</a> ' % (row[t + "_url"], cur, TABS[t]["label"])
    tabbar = "" if len(avail) == 1 else '<nav class="tabbar" aria-label="Gauge tabs">%s<a href="/">Rivers</a></nav>' % "".join('<a href="%s"%s>%s</a>' % (row[t + "_url"], ' aria-current="page"' if t == tab else "", ("<b>%s</b>" if t == tab else "%s") % TABS[t]["label"]) for t in avail)
    hub_part = "" if row.get("_single") else '<a href="%s">%s</a> / ' % (row["hub_url"], esc(river))
    crumb = '<div class="crumb"><a href="/">Home</a> / <a href="/rivers/%s/">%s</a> / %s%s</div>' % (st.lower(), esc(st), hub_part, esc(place))
    drain = (" &middot; drainage %s sq mi" % fmt(float(row["drainage_sqmi"]))) if float(row["drainage_sqmi"] or 0) > 0 else ""
    sub = 'USGS gauge %s%s &middot; observed <span data-live="obs">%s</span> &middot; <span class="ab %s"><span data-live="age" data-t="%s">%s</span> old</span>%s' % (G["site"], drain, esc(G["obs"]), "fresh" if G["age_min"] <= 90 else "ageing" if G["age_min"] <= 360 else "stale", iso(G["lt"]), age_text(G["lt"], G["now"]), amber)
    ld_items = [("Home", "/"), (st, "/rivers/%s/" % st.lower())] + ([] if row.get("_single") else [(river, row["hub_url"])]) + [(place, None)]
    ld = crumb_ld(ld_items) + '<script type="application/ld+json">%s</script>' % json.dumps({"@context": "https://schema.org", "@type": "WebPage", "name": title, "url": url, "dateModified": iso(G["lt"]), "isPartOf": {"@type": "WebSite", "name": BRAND, "url": SITE_URL}})
    ids = {b["id"] for b in shown}
    jl = [(i, t) for i, t in JUMP if i in ids]
    jump_html = ('<nav class="jump" aria-label="On this page">%s</nav>' % " ".join('<a href="#%s">%s</a>' % (i, t) for i, t in jl)) if tab == "dashboard" and len(jl) >= 4 else ""
    SIDE = {"related_gauges", "nearby_gauges", "nws_forecast_point", "flood_stages", "public_land", "about_gauge", "gauge_map", "sun", "air_obs", "official_links"}
    body = ""
    side = ""
    fold = None  # [title, rendered blocks, headings] while inside a FOLD: group
    grp = ["now"]
    used = {"now"}

    def gtag(h, g):
        used.add(g)
        return re.sub(r"^<(\w+)", lambda m: '<%s data-g="%s"' % (m.group(1), g), h, count=1)

    pending = None  # a "SEC:" heading is written only when a block follows it

    def flush():
        nonlocal body, fold
        if fold and fold[1]:
            body += gtag('<details class="fold"><summary><b>%s</b><span>%d section%s: %s</span></summary>%s</details>' % (esc(fold[0]), len(fold[2]), "" if len(fold[2]) == 1 else "s", esc(", ".join(fold[2])), fold[1]), "history" if fold[0].startswith("Flood record") else "data")
        fold = None
    for b in blocks:
        if isinstance(b, str) and b.startswith("SEC:"):
            flush()
            grp[0] = "weather" if b[4:].startswith("Forecast") else "history" if b[4:].startswith("How today") else "now" if b[4:].startswith(("What the water", "Level, flow")) else grp[0]
            pending = gtag('<h2 class="secth">%s</h2>' % esc(b[4:]), grp[0])
            continue
        if isinstance(b, str) and b.startswith("FOLD:"):
            flush()
            pending = None
            fold = [b[5:], "", []]
            continue
        if T["hero"] and isinstance(b, dict) and b["id"] in SIDE:
            side += gtag(render_block(b), "area")
            continue
        html = ('<div class="ad">ADVERTISEMENT</div>' if ADS else "") if b == "AD" else ('<div class="pair">%s</div>' % "".join(render_block(x) for x in b)) if isinstance(b, list) else render_block(b)
        if fold is not None and isinstance(b, dict):
            fold[1] += html
            fold[2].append(b["heading"])
        else:
            if pending and isinstance(b, (dict, list)):
                body += pending
                pending = None
            gid = GROUP_OF.get(b["id"] if isinstance(b, dict) else (b[0]["id"] if isinstance(b, list) and b and isinstance(b[0], dict) else ""), grp[0])
            body += gtag(html, gid) if html else html
    flush()
    gt_html = ""
    if T["hero"] and len(used) > 1:
        names = [("now", "Now"), ("weather", "Forecast"), ("history", "History"), ("data", "Data"), ("area", "Area")]
        gt_html = '<div id="tabtop"></div><nav class="gtabs" aria-label="Page sections">%s</nav>' % "".join('<button type="button" data-t="%s">%s</button>' % (k, v) for k, v in names if k in used)
    if T["hero"] and side:
        body = '<div class="cols"><div class="main2">%s</div><aside class="side" aria-label="Around this gauge">%s</aside></div>' % (body, side)
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>%s</title><meta name="description" content="%s">'
            '<link rel="canonical" href="%s">%s<style>%s</style></head><body>%s<main id="main">%s<h1>%s, %s</h1><p class="sub">%s</p><p><span class="tabs">%s</span></p>%s%s%s</main>%s%s</body></html>' % (
                esc(title), esc(desc), url, HEAD_EXTRA + og_tags(title, desc, url) + ld + robots_meta(row[tab + "_url"]), CSS, nav(), crumb, esc(rp), esc(st), sub, tabs_html, (hero(G, pages) + SAFETY + jump_html + gt_html) if T["hero"] else "", body, sources_block(shown, G) + (LIVE_JS.replace("@SITE@", G["site"]).replace("@TZ@", G["tzname"]) + GTABS_JS + RANGE_JS if T["hero"] else AGE_JS) + (ALERTS_JS.replace("@LAT@", "%.4f" % G["lat"]).replace("@LON@", "%.4f" % G["lon"]).replace("@TZ@", G["tzname"]).replace("@CTY@", ((((G["rec"].get("meta") or {}).get("loc")) or {}).get("county_name") or "").replace('"', "")) if any(b["id"] == "alerts" for b in shown) else ""), footer(), tabbar))
    meta = {"site": G["site"], "tab": tab, "url": row[tab + "_url"] if tab != "dashboard" else row["dashboard_url"], "title": title, "blocks": [b["id"] for b in shown], "age_min": round(G["age_min"]),
            "hash": hashlib.sha256(page.encode()).hexdigest()[:16]}
    return page, meta


from lib import blocks2 as b2  # noqa: E402  (blocks added after the fresh-eyes review; uses the helpers above)
from lib import blocks3 as b3  # noqa: E402


# One malformed optional record (a source that changed its shape, a half-written cache) must hide ITS block, never stop the page or the build.
# Every block function b_* is wrapped: an exception hides that block and is logged in BLOCK_ERRORS (build.py reports it, truth_tests.py requires none on the real caches).
BLOCK_ERRORS = []
SAFETY_BLOCKS = ("b_alerts", "b_river_forecast", "b_impacts", "b_stage_chart", "b_flow_chart", "b_offline", "b_flood_stages", "b_noforecast", "b_nws_point")  # a hidden one of these fails the gauge instead of shipping a page that looks complete


def _safe(fn):
    import functools

    @functools.wraps(fn)
    def w(*a, **k):
        try:
            return fn(*a, **k)
        except CriticalFail:
            raise
        except Exception as e:
            G = a[0] if a and isinstance(a[0], dict) else {}
            BLOCK_ERRORS.append("%s: %s: %s %s" % (G.get("site", "?"), fn.__name__, type(e).__name__, str(e)[:90]))
            return None
    w._guarded = True
    return w


def _guard_blocks():
    import sys
    for mod in (sys.modules[__name__], b2, b3):
        for name, fn in list(vars(mod).items()):
            if name.startswith("b_") and callable(fn) and not getattr(fn, "_guarded", False):
                setattr(mod, name, _safe(fn))


_guard_blocks()
