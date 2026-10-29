"""Primitives used by every section: formatting, source registry, block shell, tables."""
import statistics, os, re, json, math, collections, hashlib, datetime, zoneinfo
from lib.common import *


_SJ = json.load(open(os.path.join(DATA, "sources.json"), encoding="utf-8"))
SOURCES = {s["id"]: s for s in _SJ["sources"]}
SOURCES_READ_ON = _SJ["read_on"]  # the date the terms were read for every source without its own read_on


CSS = open(os.path.join(ROOT, "templates", "site.css"), encoding="utf-8").read()


LABELS = {"00010": "Water temperature", "00300": "Dissolved oxygen", "63680": "Turbidity", "00400": "pH", "00095": "Dissolved salts (specific conductance)", "99133": "Nitrate plus nitrite", "00045": "Rain at the gauge (precipitation)", "00055": "Water velocity", "72255": "Water velocity", "00480": "Salinity"}


UNITS = {"degC": "°C", "deg C": "°C", "mg/l": "mg/L", "_FNU": "FNU (turbidity units)", "uS/cm": "µS/cm", "pH Units": "pH units", "ft3/s": "cfs"}


TAGS = {"agency": "Agency data", "live": "Live gauge", "last": "Last report", "official": "Official NWS", "usdm": "U.S. Drought Monitor","model": "Model guidance", "hist": "Historical record", "map": "Mapped layer", "obs": "Weather station", "calc": "Computed", "noaa": "NOAA tide table", "epa": "EPA monitor"}


PADMAN = {"USFS": "US Forest Service", "NPS": "National Park Service", "BLM": "Bureau of Land Management", "FWS": "US Fish and Wildlife Service", "SDNR": "State natural resources agency",
          "SFW": "State fish and wildlife agency", "SPR": "State parks", "SLB": "State land board", "LOC": "Local government", "CITY": "City", "CNTY": "County", "NGO": "Nonprofit", "PVT": "Private",
          "TRIB": "Tribal", "REG": "Regional or county agency", "UNK": "Unknown manager", "UNKL": "Unknown manager", "JNT": "Joint management", "DOD": "Department of Defense", "USACE": "Army Corps of Engineers"}
PADMAN = {**json.load(open(os.path.join(DATA, "padus_managers.json"), encoding="utf-8")), **PADMAN}  # full PAD-US Mang_Name domain (Fee_Manager service, read 2026-10-27); hand names win (hater r4: "RWD")


ACCESS = {"OA": "Public land (mapped); river access not confirmed", "RA": "Restricted access", "XA": "Closed", "UK": "Access unknown"}


DISCLAIMER = ("Percentile is estimated from USGS published daily percentiles. Readings are provisional until USGS reviews them. Not endorsed by USGS, NOAA or the National Weather Service. "
              "Not for navigation or safety-of-life decisions; the absence of an alert is not a statement that conditions are safe.")


IGNORED_ALERTS = {"Test Message", "Administrative Message"}


def live_alerts(G):
    """The NWS alerts still in force at build time: system test messages and alerts past their end (or message expiry) are left out. None when alerts could not be loaded."""
    al = (G["rec"].get("nws") or {}).get("alerts")
    if al is None:
        return None
    out = []
    for a in al:
        if (a.get("event") or "") in IGNORED_ALERTS:
            continue
        try:
            if (a.get("ends") or a.get("expires")) and parse_t(a.get("ends") or a.get("expires")) < G["now"]:
                continue
        except (TypeError, ValueError):
            pass
        out.append(a)
    return out


ADS = False  # the empty ADVERTISEMENT slots render only when an ad network is live


PREVIEW = False  # build.py --preview: show blocks whose source is not cleared, into dist_preview/ (review only, never published)


class CriticalFail(Exception):
    pass


FLOOD_LEVELS = '<p class="src">NWS flood levels on this gauge\'s scale: Action = NWS starts watching; Minor, Moderate, Major = increasing flooding of land and roads.</p>'  # one line under every flood-stage block


def md(d):
    """'Oct 5': month and day, no leading zero. Every date on a page is written this way (w-reviews: 'for Oct 05')."""
    return "%s %d" % (d.strftime("%b"), d.day)


def clock(d, tz, date=True):
    """'Oct 5, 3:07 PM EDT' from a wall-clock time and its zone name: tzl, and the AirNow and tide times that arrive as local text."""
    s = ("%d:%s %s" % (d.hour % 12 or 12, d.strftime("%M %p"), tz)).strip()
    s = ("%s, %s" % (md(d), s) if date else s).strip()
    return s.replace(" ", "\u00a0").replace(",\u00a0", ", ")  # a long date wraps after the comma, never inside the time


def tzl(dt, zone, date=True):
    d = dt.astimezone(zone)
    return clock(d, d.strftime("%Z"), date)


def age_text(dt, now):
    """The age chip's text; AGE_FN (lib/page.py) and worker/index.js print the same, rounded the same way."""
    m = round_half_up((now - dt).total_seconds() / 60)
    return "%d min" % m if m < 180 else ("%d h" % round_half_up(m / 60) if m < 2880 else "%d d" % round_half_up(m / 1440))


AGE_UNIT = {"min": "minute", "h": "hour", "d": "day"}


def age_words(dt, now):
    """The same age as age_text, in words ("2 days", "7 hours"), for sentences."""
    n, u = age_text(dt, now).split()
    return "%s %s%s" % (n, AGE_UNIT[u], "" if n == "1" else "s")


def flow_is_old(age_min):
    """A flow reading older than 8 x the USGS stale limit (24 h): "not reporting" banner, no "live" in the title, an age marker on list rows. One rule for all three."""
    return age_min > stale_after("usgs") * 8 * 60


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


def stage_is_ft(row):
    """True when a gage-height reading is in feet: the one test every stage comparison uses (a missing unit is feet, the USGS and NWS default)."""
    return (row.get("unit_of_measure") or "ft").lower() in ("ft", "feet")


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


def block(bid, heading, tag, body, source, src_id, as_of=None, amber=False, empty=False):
    """empty=True: a valid-empty state (one sentence such as "no river forecast issued"), drawn as one grey line, not a card."""
    if not isinstance(amber, bool):  # an age in hours: old by the one table
        amber = amber is not None and amber > stale_after(bid)
    return {"id": bid, "heading": heading, "tag": tag, "body": body, "source": source, "src_id": src_id, "as_of": as_of, "amber": amber, "empty": empty}


STALE_H = {"usgs": 3, "camera": 3, "alerts": 3, "air_obs": 3, "rain_totals": 6, "river_forecast": 24,  # hours after which a source is old; any other block: 12 h. The only list: amber tags, live badges and the break test read it
           "chip_fresh": 1.5, "chip_ageing": 6}  # the age chip by the H1: fresh to 1.5 h, ageing to 6 h, then stale (page, LIVE_JS and worker/index.js all read these)


def stale_after(bid):
    return STALE_H.get(bid, 12)


def age_chip(age_min):
    """The age chip's colour class (gauge page and status page): STALE_H, the same cut-offs as LIVE_JS and worker/index.js."""
    return "fresh" if age_min <= STALE_H["chip_fresh"] * 60 else "ageing" if age_min <= STALE_H["chip_ageing"] * 60 else "stale"


HIDE_H = {"river_forecast": 72, "nwm_guidance": 72, "nwm_medium_range": 72, "forecast_rain_totals": 72, "hourly_forecast": 72, "hourly_heatmap": 72,
          "weather_forecast": 48, "air_obs": 12, "air_quality": 12, "wpc_outlooks": 6}  # hours after which a source is too old to show at all: the only list of hide limits


# colour means one thing on every page: now (live gauge, weather station), fc (official forecasts, model guidance), rec (records, computed comparisons), area (agency data, map layers), safe (alerts, impacts, offline gauge)
FAMILY = {"live": "now", "obs": "now", "official": "fc", "usdm": "fc", "model": "fc", "hist": "rec", "calc": "rec", "agency": "area", "map": "area", "noaa": "fc", "epa": "now"}


FAMILY_BY_ID = {"alerts": "safe", "flood_impacts": "safe", "offline": "safe"}


def render_block(b):
    amber = (' <span class="tag amber">%s</span>' % (b.get("age_tag") or "Older than %d h" % stale_after(b["id"]))) if b.get("amber") else ""
    src = '<details class="srcd"><summary>Source</summary><p class="src">%s%s</p></details>' % (b["source"], credit_line(b))  # one small toggle in the heading row; opens under the heading
    fam = FAMILY_BY_ID.get(b["id"]) or FAMILY.get(b["tag"], "now")
    if b.get("empty"):
        return '<section class="card blk emp" data-f="%s" id="%s"><h2>%s</h2>%s%s</section>' % (fam, b["id"], esc(b["heading"]), b["body"], src)
    return ('<section class="card blk" data-f="%s" id="%s"><h2>%s <span class="tag t-%s">%s</span>%s<a class="pl" href="#%s" aria-label="Link to this section">#</a></h2>%s%s</section>' % (fam, b["id"], esc(b["heading"]), b["tag"], esc(TAGS[b["tag"]]), amber, b["id"], src, b["body"]))


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
    if "href=" in c:  # ponytail: a station id inside a link must keep its real hyphen or the URL breaks; the non-breaking hyphen is cosmetic only
        return c
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
        return "%d month%s" % (round(days / 30.4), "" if round(days / 30.4) == 1 else "s")
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


def wind_arrow(d):
    """NWS gives the direction the wind comes FROM; the arrow points where it blows TO. The compass letters stay for screen readers and on hover."""
    return '<span class="wa" role="img" aria-label="from %s" title="Wind from %s" style="transform:rotate(%ddeg)">&#8593;</span>' % (compass(d), compass(d), round(d + 180) % 360)


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
    has_turb = False
    for code, lab in LABELS.items():
        s = series(G["rec"], code) if code != "00045" else None  # precipitation is shown in the rain tile, not as water quality (full review)
        if s:
            if code == "63680":
                has_turb = True
            t, v, r = s[-1]
            unit = UNITS.get(r.get("unit_of_measure"), r.get("unit_of_measure") or "")
            shown = ("%.1f °F (%.1f °C)" % (v * 9 / 5 + 32, v)) if (code == "00010" and unit == "°C") else ("%s %s" % (fmt(v), esc(unit)))
            rows += tr([esc(lab), shown + ((' <b class="qual">%s</b>' % qual_text(r)) if qual_text(r) else ""), esc(tzl(t, G["zone"]))], right=(1,))
    if not rows:
        return None
    # clarity frame for anglers, where turbidity is measured: a sourced fact, not a verdict (no federal recreation cutoff exists)
    note = '<p class="src">Reading turbidity: USGS notes rivers at base flow usually run under about 10 turbidity units (NTU/FNU); a higher reading means more suspended sediment, usually after rain or snowmelt. <a href="https://www.usgs.gov/special-topics/water-science-school/science/turbidity-and-water" rel="noopener">USGS Water Science School</a>.</p>' if has_turb else ""
    return block("quality_sensors", "Water quality sensors", "live", table(["Measure", "Latest value", "Observed"], rows, right=(1,)) + note, "Source: USGS Water Data API (continuous values). Values as reported by the gauge, provisional.", "usgs")
