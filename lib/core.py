"""Primitives used by every section: formatting, source registry, block shell, tables."""
import statistics, os, re, json, math, collections, hashlib, datetime, zoneinfo
from lib.common import *


SOURCES = {s["id"]: s for s in json.load(open(os.path.join(DATA, "sources.json"), encoding="utf-8"))["sources"]}


CSS = open(os.path.join(ROOT, "templates", "site.css"), encoding="utf-8").read()


LABELS = {"00010": "Water temperature", "00300": "Dissolved oxygen", "63680": "Turbidity", "00400": "pH", "00095": "Specific conductance", "99133": "Nitrate plus nitrite", "00045": "Rain at the gauge (precipitation)", "00055": "Water velocity", "72255": "Water velocity", "00480": "Salinity"}


UNITS = {"degC": "°C", "deg C": "°C", "mg/l": "mg/L", "_FNU": "FNU (turbidity units)", "uS/cm": "µS/cm (conductance)", "pH Units": "pH units", "ft3/s": "cfs"}


TAGS = {"agency": "Agency data", "live": "Live gauge", "official": "Official NWS", "model": "Model guidance", "hist": "Historical record", "map": "Mapped layer", "obs": "Weather station", "calc": "Computed", "noaa": "NOAA tide table", "epa": "EPA monitor"}


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
FAMILY = {"live": "now", "obs": "now", "official": "fc", "model": "fc", "hist": "rec", "calc": "rec", "agency": "area", "map": "area", "noaa": "fc", "epa": "now"}


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


def miles_between(la1, lo1, la2, lo2):
    la1, lo1, la2, lo2 = map(math.radians, (la1, lo1, la2, lo2))
    return 3958.8 * 2 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))


def human_span(days):
    if days < 45:
        return "%d day%s" % (days, "" if days == 1 else "s")
    if days < 730:
        return "%d months" % round(days / 30.4)
    return "%d years" % round(days / 365.25)


def fdate(iso_d):
    return datetime.date.fromisoformat(iso_d).strftime("%b %d, %Y").replace(" 0", " ")


def area_short(s, n=6, county=None):
    parts = [p.strip() for p in s.split(";") if p.strip()]
    if county:
        c = county.lower().replace(" county", "").replace(" parish", "").strip()
        mine = [p for p in parts if p.lower() == c or p.lower().endswith(" " + c)]
        parts = mine + [p for p in parts if p not in mine]
    return s if len(parts) <= n and not county else "; ".join(parts[:n]) + (("; and %d more areas" % (len(parts) - n)) if len(parts) > n else "")


# ---------------------------------------------------------------- final-form blocks
COMP = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


YCOL = ["var(--accent)", "#d9822b", "#2e9d6a", "#8a6bd1"]


YDASH = ["", "7 3", "2 3", "10 3 2 3"]


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def compass(d):
    return COMP[int((d % 360) / 22.5 + 0.5) % 16]


def tint(frac):
    return "color-mix(in srgb,var(--accent) %d%%,var(--card))" % round(max(0, min(1, frac)) * 55)


# One malformed optional record (a source that changed its shape, a half-written cache) must hide ITS block, never stop the page or the build.
# Every block function b_* is wrapped: an exception hides that block and is logged in BLOCK_ERRORS (build.py reports it, truth_tests.py requires none on the real caches).
BLOCK_ERRORS = []


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
