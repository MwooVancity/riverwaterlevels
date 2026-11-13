"""Shared paths, data loading and helpers for the River Water Levels build."""
import zlib
import os, re, csv, json, math, datetime, html, urllib.request, urllib.parse

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CACHE = os.path.join(ROOT, "cache")
DIST = os.path.join(ROOT, "dist")
DATA = os.path.join(ROOT, "data")
NEG_ZERO = re.compile(r"(?<![\w.])[-−](0\.0+)(?![\d])(?=(?:\s|&nbsp;| )*(?:ft|m|cm|in|°))")  # '-0.0 ft' (a -0.04 reading) -> '0.0 ft'; the same pattern as check.py neg_zero; applied by build.py write() to every page (2026-11-10)
BRAND = "River Water Levels"


@__import__("functools").lru_cache(maxsize=1)
def publisher():
    """data/publisher.json ({name, email}); {} when missing. The owner fills the email; /contact/ and its footer link appear only then (drawing board: trust)."""
    try:
        return json.load(open(os.path.join(DATA, "publisher.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return {}
DOMAIN = "riverwaterlevels.com"
SITE_URL = "https://" + DOMAIN
# read-only sources inside the older research folder (copied into the cache by collect.py, never edited)
# in the repository (GitHub Actions) they live in ./legacy; on the owner's PC they are read from the older research folder
_PC_LEGACY = r"C:\Users\mwoo7\Desktop\calcscrape\docs\research\prototypes\data"
LEGACY = os.environ.get("RWL_LEGACY") or (_PC_LEGACY if os.path.isdir(_PC_LEGACY) else os.path.join(ROOT, "legacy"))
ENV_FILE = r"C:\Users\mwoo7\Desktop\calcscrape\.env"  # key is read here (or from the USGS_API_KEY environment variable), server side only, never copied or logged
PCT = [5, 10, 20, 25, 50, 75, 80, 90, 95]
DOUBLE_PREP = re.compile(r"\b(at|near|above|below|of) \1\b", re.I)


def esc(s, quote=True):
    """html.escape for every shown string, and a government name that doubles its preposition ('Frio River at at Leakey', NWS point FILT2) reads once: one place, so no block can print 'at at'."""
    return DOUBLE_PREP.sub(r"\1", html.escape(s, quote))


# wave 0 slice: gauges chosen to exercise every case (full sensors, no sensors, multi-gauge river, snowmelt, small creek)


def template_hash():
    """Fingerprint of the code that decides what a page shows (hater review: a change here needs a fresh signed review). Line endings are
    normalised so a Windows checkout and CI agree."""
    import glob, hashlib
    files = sorted(glob.glob(os.path.join(ROOT, "lib", "*.py")) + glob.glob(os.path.join(ROOT, "templates", "*")) + [os.path.join(ROOT, f) for f in ("build.py", "collect.py", "worker/index.js", "data/name-fixes.csv", "data/name-overrides.csv", "data/sources.json")])
    h = hashlib.sha256()
    for f in files:
        h.update(os.path.relpath(f, ROOT).replace("\\", "/").encode() + b"\0" + open(f, "rb").read().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:12]


def usgs_headers():
    h = {"User-Agent": "riverwaterlevels-build"}
    if os.environ.get("USGS_API_KEY"):
        h["X-Api-Key"] = os.environ["USGS_API_KEY"].strip()
        return h
    try:
        for l in open(ENV_FILE, encoding="utf-8-sig"):
            if l.startswith("USGS_API_KEY="):
                h["X-Api-Key"] = l.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return h


def http_open(url, headers=None, timeout=40, tries=3):
    """urlopen that retries a reset, timeout or 5xx twice (5 s, then 20 s) before raising: one hiccup on our own site must not turn a run red (run 39672840649, 2026-10-21)."""
    import time, urllib.request
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=headers or {"User-Agent": "riverwaterlevels.com check"}), timeout=timeout)
        except Exception as e:
            if i == tries - 1 or getattr(e, "code", 0) not in (0, 429, 500, 502, 503, 504):
                raise
            time.sleep(5 if i == 0 else 20)


def http_json(url, headers=None, timeout=90):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "riverwaterlevels-build"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def load_cache(site):
    p = os.path.join(CACHE, site + ".json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def iso(dt):
    return dt.isoformat()


def parse_t(s):
    return datetime.datetime.fromisoformat(s)


def fmt(v):
    if v is None:
        return "\u2013"
    return "{:,.0f}".format(v) if abs(v) >= 100 else ("%.0f" % v if abs(v) >= 10 else "%.2f" % v if abs(v) < 1 else "%.1f" % v)


def fmtc(v):
    """Whole cfs with a thousands comma (style sheet 6); fmt keeps decimals for sensor values."""
    if v is None:
        return "–"
    if 0 < abs(v) < 1:
        return "%.2f" % math.copysign(round_half_up(abs(v), 2), v)  # 0.45 cfs is not "0 cfs" (live numbers review: read as a dry creek); toFixed(2) rounds the size half up
    if abs(v) >= 1000:  # hater 2026-10-27: computed means printed as "280,917 cfs"; 3 significant figures, half up like toPrecision(3) in LIVE_JS and the worker
        q = 10 ** (math.floor(math.log10(abs(v))) - 2)
        return "{:,.0f}".format(math.copysign(round_half_up(abs(v) / q) * q, v))
    return "{:,.0f}".format(round_half_up(v))  # Math.round


MOJI = re.compile("Ã[\u0080-\u00bf]|â€|â‚¬|Â[\u0080-\u00bf]")


def demoji(s):
    """Undo UTF-8 text decoded as Windows-1252, as often as it was done (w11 review: NWS low-water text)."""
    for _ in range(3):
        if not isinstance(s, str) or not MOJI.search(s):
            break
        try:
            s = bytes(b for ch in s for b in (ch.encode("cp1252") if ch not in "\x81\x8d\x8f\x90\x9d" and ord(ch) > 127 else bytes([ord(ch)]) if ord(ch) < 256 else ch.encode("utf-8"))).decode("utf-8")
        except (UnicodeError, ValueError):
            break
    return s


FC_TOL_FT, FC_TOL_REL = 0.05, 0.02  # a forecast within 0.05 ft (stage) or 2 % (flow) of the reading is level with it


def fc_cmp(v, cur, unit="ft"):
    """'above', 'level' or 'below': a forecast value against the latest reading, the tolerance always taken from the READING. Every forecast-vs-now word uses this."""
    tol = FC_TOL_FT if unit == "ft" else FC_TOL_REL * abs(cur)
    return "above" if v > cur + tol else "below" if v < cur - tol else "level"


def fc_word(vals, cur, unit="ft"):
    """'steady' when every forecast value prints the same, 'high' when the highest is above the latest reading, else 'below' (no rise above the latest reading).
    The single source for "Forecast high" (w11-w13 reviews: three places chose the word three ways)."""
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    if len({("%.1f" % v) if unit == "ft" else fmtc(v) for v in vals}) == 1:
        return "steady"
    return "high" if cur is None or fc_cmp(max(vals), cur, unit) == "above" else "below"


FC_LABEL = {"steady": "NWS forecast (steady)", "high": "Forecast high", "below": "NWS forecast: no rise above the latest reading"}


def nws_pt(n):
    """'forecast point Mississippi River at Memphis': the NWS point by its name. Its 5-character code (MEMT1) belongs in Source text and link titles only."""
    return "forecast point " + n["name"] if (n or {}).get("name") else "forecast point"


FLAT_PCT, FLAT_CFS = 2, 5  # a flow change under 2 % or under 5 cfs is steady (headline word, rate-table and hub arrows)
FC_NEAR_S, FC_OFF_REL = 5400, 0.25  # a forecast point within 90 min of the reading whose flow is more than 25 % off it is out of step
NEAR_WTEMP_H = 48  # a nearby gauge's water temperature older than this is not shown


def flow_dir(pct, d=None):
    """'up', 'down' or 'steady' for a flow change in percent (d: the same change in cfs, when known). One cut-off for the headline word and every arrow."""
    if d is not None and abs(d) < FLAT_CFS:
        return "steady"
    return "up" if pct >= FLAT_PCT else "down" if pct <= -FLAT_PCT else "steady"


def km_mi(km):
    """Kilometres to miles: one factor for every distance and wind speed."""
    return km * 0.621371


def km(lat, lon, lat2, lon2, r=6371):
    """Great-circle (haversine) distance in km; r=3958.8 gives miles. The one distance formula (audit 2026-11-10 #49: was 4 copies)."""
    a = math.sin(math.radians(lat2 - lat) / 2) ** 2 + math.cos(math.radians(lat)) * math.cos(math.radians(lat2)) * math.sin(math.radians(lon2 - lon) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def merc(lat, lon):
    """Web Mercator (EPSG:3857) metres for a point: the USGS map exports' bbox."""
    return 6378137.0 * math.radians(lon), 6378137.0 * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def round_half_up(x, nd=0):
    """Round half up, as JavaScript's Math.round does: the page and its live refresh must print the same number (Python's round() and %-format round half to even)."""
    q = 10 ** nd
    return math.floor(x * q + 0.5) / q if nd else math.floor(x + 0.5)


def r1(x):
    """A difference of two stages rounded half up to 0.1 before printing with %.1f."""
    return math.floor(x * 10 + 0.5 + 1e-9) / 10


def fmtd(v):
    """A difference in cfs, exact to the whole cfs (w10 review: 4,200 - 235 printed as 3,960)."""
    return "–" if v is None else "%.2f" % math.copysign(round_half_up(abs(v), 2), v) if 0 < abs(v) < 1 else "{:,.0f}".format(round_half_up(v))  # half up, as fmtc


def interp_pct(stats_row, v):
    """Percentile of v within a published daily-percentile row [years, p5, p10, p20, p25, p50, p75, p80, p90, p95]."""
    pts = [(p, stats_row[i + 1]) for i, p in enumerate(PCT) if stats_row[i + 1] is not None]
    if not pts or pts[0][0] > 10 or pts[-1][0] < 90:  # a 2-year row has only the median; records under 20 years publish 10th to 90th
        return None
    if v < pts[0][1]:
        return -1 if pts[0][0] == 5 else None  # "below 5th" needs a published 5th
    if v > pts[-1][1]:
        return 101 if pts[-1][0] == 95 else None
    for (p0, v0), (p1, v1) in zip(pts, pts[1:]):
        if v0 <= v <= v1:
            return p0 if v1 == v0 else p0 + (p1 - p0) * (v - v0) / (v1 - v0)
    return None


def ordinal(n):
    n = int(round(n))
    return "%d%s" % (n, "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def prep_lower(place):
    """USGS names put 'Near', 'At', 'Above', 'Below' (and river names 'Of', 'The', 'And') in capitals inside a name ('Glenwood Bridge Near Boise', 'Red River Of The North'): as small words they are lower case."""
    s = re.sub(r"(?<=\S )(Near|At|Above|Below|Of|The|And)(?= \S)", lambda m: m.group(1).lower(), place or "")
    return re.sub(r"\bthe (?=Dalles|Woodlands)", "The ", s).replace("L&d", "L&D")  # black-hat review 2026-11-11: "at the Dalles", "Claiborne L&d" read as scraped; display only, slugs are lower case


def river_at(river, place):
    """'Gauley River above Belva', 'Penns Creek', 'Missouri River at Kansas City': the place already names its preposition or the river."""
    p = prep_lower((place or "").strip())
    if not p or p.lower() == river.lower():
        return river
    first = p.split(" ", 1)[0].lower()
    if first in ("above", "below", "near", "at"):
        return "%s %s%s" % (river, first, p[len(first):])
    return "%s at %s" % (river, p)


EEA_UK_CH = "AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE IS LI NO GB CH".split()
CONSENT = '<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}gtag("consent","default",{ad_storage:"denied",ad_user_data:"denied",ad_personalization:"denied",analytics_storage:"denied",wait_for_update:500,region:%s})</script>' % json.dumps(EEA_UK_CH, separators=(",", ":"))  # German pages reach EU readers: no cookie before Google's consent message answers
ADSENSE = CONSENT + '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8997828618122077" crossorigin="anonymous"></script>'  # AdSense site loader (owner 2026-10-23); head of indexable pages only, never the embed panel or 404
ADSENSE += '<script>gtag("js",new Date());gtag("config","G-96RG42R07G");addEventListener("load",function(){var s=document.createElement("script");s.async=1;s.src="https://www.googletagmanager.com/gtag/js?id=G-96RG42R07G";document.head.appendChild(s)})</script>'  # Google Analytics, same tag as calcscrape (owner 2026-10-31); same pages as the ad loader. Loaded after the page (Lighthouse 2026-11-08: 176 KB, 444 ms blocking on a gauge page); its queued calls run when it arrives. The ad loader stays in the head for AdSense review.


PCT_PHRASE = {"Much above normal": "much above normal", "Above normal": "above normal", "Typical for this date": "typical for this date", "Below normal": "below normal", "Much below normal": "much below normal", "\u2013": "not classed"}


def sig3(v):
    """A model guess shown to 3 significant figures (hater 2026-10-27: '280,917 cfs' is false precision)."""
    return float("%.3g" % v) if v else v


BAND_CUTS = (10, 25, 75, 90)  # percentile cut-offs of the five classes (USGS WaterWatch): under 10 much below, under 25 below, 25 to 75 normal, up to 90 above, over 90 much above. band_word, ww_cls, the range bar and the glossary all read this.


# Each agency's own published colours for its own status classes, read 2026-11-13 from the URL beside each (owner 2026-11-13: "use colors every single API channel would use").
# One table: page CSS (official_css), the flood ladder, the alert banner, drought, AQI and UV all read it. Colour never stands alone: the agency's word is always beside it.
OFFICIAL = {
    # USGS Water Data for the Nation percentile colours ('WDFN_stats' schema in USGS hyswap, github.com/DOI-USGS/hyswap hyswap/utils.py retrieve_schema; WaterWatch itself is retired).
    # Our five classes are the middle five; -1 and 101 take much below / much above, as band_word says.
    "ww": {"w1": ("Much below normal", "#8e704f"), "w2": ("Below normal", "#c7a97b"), "w3": ("Normal", "#ddf9c7"), "w4": ("Above normal", "#aacdec"), "w5": ("Much above normal", "#4f97d1")},
    # NWS water.noaa.gov map colours (its own bundle.js: {major:"#cc33ff",moderate:"#ff0000",minor:"#ff9900",action:"#f1f100"...}).
    "nws_flood": {"action": "#f1f100", "minor": "#ff9900", "moderate": "#ff0000", "major": "#cc33ff"},
    # NWS hazard map colours, weather.gov/help-map table; nws_order lists them in that table's priority order (highest first).
    "nws_order": ["tornado warning", "extreme heat warning", "hurricane warning", "storm surge warning", "tropical storm warning", "flash flood warning", "flash flood statement", "severe thunderstorm warning",
                  "storm surge watch", "hurricane watch", "tropical storm watch", "coastal flood warning", "flood warning", "flood statement", "winter storm warning", "red flag warning", "extreme heat watch",
                  "flash flood watch", "flood watch", "coastal flood watch", "heat advisory", "flood advisory", "coastal flood advisory", "coastal flood statement", "high surf advisory", "rip current statement",
                  "freeze warning", "wind advisory", "dense fog advisory", "small craft advisory", "special weather statement", "air quality alert", "hydrologic outlook"],
    "nws": {"tornado warning": "#ff0000", "severe thunderstorm warning": "#ffa500", "flash flood warning": "#8b0000", "flash flood statement": "#8b0000", "flash flood watch": "#2e8b57", "flood warning": "#00ff00",
            "flood watch": "#2e8b57", "flood advisory": "#00ff7f", "flood statement": "#00ff00", "hydrologic outlook": "#90ee90", "coastal flood warning": "#228b22", "coastal flood watch": "#66cdaa",
            "coastal flood advisory": "#7cfc00", "coastal flood statement": "#6b8e23", "winter storm warning": "#ff69b4", "extreme heat warning": "#c71585", "extreme heat watch": "#800000", "heat advisory": "#ff7f50",
            "rip current statement": "#40e0d0", "high surf advisory": "#ba55d3", "small craft advisory": "#d8bfd8", "special weather statement": "#ffe4b5", "red flag warning": "#ff1493", "dense fog advisory": "#708090",
            "wind advisory": "#d2b48c", "freeze warning": "#483d8b", "air quality alert": "#808080", "hurricane warning": "#dc143c", "hurricane watch": "#ff00ff", "tropical storm warning": "#b22222",
            "tropical storm watch": "#f08080", "storm surge warning": "#b524f7", "storm surge watch": "#db7ff7"},
    # U.S. Drought Monitor colour scheme, droughtmonitor.unl.edu/DmData/Metadata.aspx.
    "usdm": {"d0": "#ffff00", "d1": "#fcd37f", "d2": "#ffaa00", "d3": "#e60000", "d4": "#730000"},
    # EPA AQI Technical Assistance Document (EPA-403/B-26-003), Table 2 standard colours (RGB there, hex here).
    "aqi": {"good": "#00e400", "moderate": "#ffff00", "unhealthy for sensitive groups": "#ff7e00", "unhealthy": "#ff0000", "very unhealthy": "#8f3f97", "hazardous": "#7e0023"},
    # EPA UV index scale page's own CSS, epa.gov/sunsafety/uv-index-scale-0.
    "uv": {"low": "#55cc1e", "moderate": "#ffdf32", "high": "#ffa600", "very high": "#e60073", "extreme": "#9370fe"},
}


def ww_cls(p):
    """WaterWatch class of a percentile for its colour (OFFICIAL["ww"]): the same cuts and the same -1/101 rule as band_word, '' when unknown."""
    if p is None:
        return ""
    return "w5" if p == 101 or p > BAND_CUTS[3] else "w1" if p == -1 or p < BAND_CUTS[0] else "w2" if p < BAND_CUTS[1] else "w3" if p <= BAND_CUTS[2] else "w4"


def alert_rank(a):
    """Place of an NWS alert in the weather.gov/help-map priority table (event name trimmed, case-blind); an event not in the table sorts last."""
    o, ev = OFFICIAL["nws_order"], " ".join((a.get("event") or "").lower().split())
    return o.index(ev) if ev in o else len(o)


def alert_col(alerts):
    """Left-border colour of the alert banner: the NWS map colour of the highest-priority alert (the banner names alerts in this same order).
    None when that alert is not in the table (a new or renamed event): the banner keeps its plain warning border, never a guessed colour."""
    al = sorted(alerts or [], key=alert_rank)
    return OFFICIAL["nws"].get(" ".join((al[0].get("event") or "").lower().split())) if al else None


def official_css():
    """Page CSS for every agency colour, generated from OFFICIAL so no second copy lives in site.css. Colour sits on a border, bar or swatch, never under text."""
    out = ""
    for k, (_, hx) in OFFICIAL["ww"].items():
        out += ".tile.b-%s{border-top:4px solid %s}.status.%s{border-left:6px solid %s;padding-left:10px}.dot.%s,.keyrow b.%s,.rb>.%s{background:%s}" % (k, hx, k, hx, k, k, k, hx)
    return out + ".sw{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px;box-shadow:0 0 0 1px rgba(0,0,0,.25)}"


def band_glossary():
    """The glossary sentence for the five headline words, generated from BAND_CUTS."""
    a, b, c, d = BAND_CUTS
    return ("Much below normal means below the %dth percentile, Below normal from the %dth up to the %dth, Typical for this date from the %dth to the %dth, "
            "Above normal above the %dth up to the %dth, and Much above normal above the %dth percentile." % (a, a, b, b, c, c, d, d))


LAKE_CODES = ("62614", "62615", "72020", "00062", "AGY", "IGLD")  # NGVD29 first (the datum Reclamation and USACE quote pools in: Powell 3,700 ft full pool), then NAVD88, then the gauge datum
AGENCIES = {"cdec": {"short": "CDEC", "name": "California Data Exchange Center (California Department of Water Resources)", "page": "https://cdec.water.ca.gov/dynamicapp/staMeta?station_id=%s", "every": "hourly", "label": "CDEC station", "src": "cdec"},
            "rise": {"short": "Reclamation", "name": "U.S. Bureau of Reclamation (RISE)", "page": "https://data.usbr.gov/time-series/search?itemId=%s", "every": "daily", "label": "Reclamation RISE item", "src": "usbr", "day_avg": True, "day_word": "value", "day_tz": "America/Phoenix", "no_storage": "Not shown: Reclamation's storage file (RISE item 6124) states acre-feet but gives 6,904, which cannot be acre-feet for Lake Mead."},
            "twdb": {"short": "TWDB", "name": "Texas Water Development Board (Water Data for Texas)", "page": "https://www.waterdatafortexas.org/reservoirs/individual/%s", "every": "daily average", "label": "TWDB reservoir", "src": "twdb", "day_avg": True},
            "coops": {"short": "NOAA", "name": "NOAA CO-OPS (National Ocean Service), shoreline station", "page": "https://tidesandcurrents.noaa.gov/stationhome.html?id=%s", "every": "6-minute", "label": "NOAA station", "src": "coops", "what": "water level above IGLD 1985 and water temperature at this shoreline station, preliminary", "no_storage": "Not applicable: a Great Lake has no reservoir storage."}}  # a lake read from its operator's feed (collect.py fetch_agency): the name every USGS line on its page is swapped for
LAKE_DATUM = {"MLLW": "mean lower low water (MLLW, NOAA tidal datum at this station)", "62615": "NAVD 1988", "62614": "NGVD 1929", "72020": "NGVD 1929", "00062": "the reservoir's own datum", "AGY": "the datum the operator uses (its feed does not name one)", "IGLD": "IGLD 1985 (International Great Lakes Datum, as NOAA CO-OPS publishes it)"}


def wt_suspect(vs):
    """A NOAA water temperature series that swings over 10 F in 3 days or passes 95 F is a sensor problem, never the sea (Fort Lauderdale 2026-11-06: 82.4 to 99.5 F)."""
    return bool(vs) and (max(vs) - min(vs) > 10 or max(vs) > 95)


def lake_datum(G):
    """What a lake elevation is measured above. 00062 is above the gauge datum, so the gauge's own altitude and datum from USGS are named
    (Lanier 0.0 ft NAVD88, Hartwell -0.04 ft NAVD88); without that metadata it says the gauge datum, never a guessed sea-level datum."""
    if G.get("lake") != "00062":
        return LAKE_DATUM.get(G.get("lake"), "the reservoir's own datum")
    loc = ((G["rec"].get("meta") or {}).get("loc")) or {}
    if loc.get("altitude") is not None and loc.get("vertical_datum"):
        return "the gauge datum (USGS lists it at %s ft %s)" % (("%.2f" % loc["altitude"]).rstrip("0").rstrip("."), loc["vertical_datum"])
    return "the gauge datum"


def latest_band_note(srow, lv, word, when=""):
    """' The latest reading, X cfs, is <band>.' when the latest reading sits in another band than the 24 h average the headline judges; else ''.
    Audit 2026-11-05: Louisville read "Typical for this date" beside +168% in 24 h."""
    pl = interp_pct(srow, lv) if srow and lv is not None else None
    if pl is None or band_word(pl) == word:
        return ""
    return " The latest reading, %s cfs%s, is %s." % (fmtc(lv), (" at " + when) if when else "", PCT_PHRASE[band_word(pl)])


def band_word(p):
    """Plain-word USGS WaterWatch class of today's flow against the same date in past years (p = percentile 0-100, -1 below the 5th, 101 above the 95th, None unknown). Boundaries follow USGS WaterWatch: <10 much below, 10-24 below, 25-75 normal, 76-90 above, >90 much above."""
    if p is None:
        return "–"
    if p == 101 or p > BAND_CUTS[3]:
        return "Much above normal"
    if p == -1 or p < BAND_CUTS[0]:
        return "Much below normal"
    if p < BAND_CUTS[1]:
        return "Below normal"
    if p <= BAND_CUTS[2]:
        return "Typical for this date"
    return "Above normal"


def week_due(ts, site, now=None):
    """Each gauge's history comes due in its own hour of the week, so calls spread evenly over 168 hours. A new gauge comes due at once;
    a run GitHub skipped costs one week, never more (14 days is due on any run)."""
    if not ts:
        return True
    now = now or datetime.datetime.now(datetime.timezone.utc)
    try:
        age = (now - datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))).total_seconds() / 3600
    except ValueError:
        return True
    return age > 336 or (age > 24 and now.weekday() * 24 + now.hour == zlib.crc32(site.encode()) % 168)


ROLL_H = 2  # build.py rolling rebuild: a page's static parts (weather observations among them) are rebuilt every ROLL_H hours in its own slot


def roll_slot(site, now):
    """This gauge's rebuild hour (build.py) and its weather-observation hour (collect.py fetch_nws): one rule, so the observation is fresh when the page is built."""
    return int(__import__("hashlib").md5(site.encode()).hexdigest(), 16) % ROLL_H == now.hour % ROLL_H


def obs_due(obs, site, alerts, now=None):
    """PLAN limit 3: the NWS station observation is fetched in the page's rebuild slot, every ROLL_H hours, not every hour (off-slot fetches no page
    showed). Always fetched: no observation yet, alerts unknown (None) or active (a page rebuilt 'hot' during a storm shows the latest), or the one kept
    is over 150 min old (a station that lags; obs turn amber at 3 h)."""
    if not obs or alerts is None or alerts:
        return True
    now = now or datetime.datetime.now(datetime.timezone.utc)
    try:
        age = (now - datetime.datetime.fromisoformat(obs["timestamp"].replace("Z", "+00:00"))).total_seconds() / 60
    except (KeyError, TypeError, AttributeError, ValueError):
        return True
    return age > 150 or roll_slot(site, now)


def day_due(ts, site, now=None):
    """Daily USGS work (8-day re-pull, neighbour list) in the gauge's own hour of the day, so the key's 1,000 calls an hour are never spent in one
    burst (was 09-12 UTC for every gauge: about 650 gauges filled the hour). A new gauge is due at once; a skipped run costs one day (36 h is due on any run)."""
    if not ts:
        return True
    now = now or datetime.datetime.now(datetime.timezone.utc)
    try:
        age = (now - datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))).total_seconds() / 3600
    except ValueError:
        return True
    return age > 36 or (age > 12 and now.hour == zlib.crc32(site.encode()) % 24)


def dir_lv(G):
    """The flow a list row shows: on a tidal reach the latest reading is a moment in the tide cycle (Freeport swings 1,090 to 12,500 cfs in a day), so lists show the 24 h mean the comparison uses; the gauge page shows the day's range.
    Every list of gauges (home, state, hub, nearby, upstream and downstream) calls this."""
    return G["basis"] if G.get("osc") and G.get("basis_mean") else G["lv"]


def new_fail(d, u, msgs):
    """Record a new page whose number did not match its source in <d>/_failed.json (the file check.py writes), as a page failure quarantine.py can send back."""
    import json, os
    p = os.path.join(d, "_failed.json")
    try:
        f = json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        f = {"pages": {}, "site": []}
    f.setdefault("pages", {})[u.strip("/") + "/index.html"] = msgs or ["numbers did not match the source"]
    f["site"] = f.get("site") or []
    json.dump(f, open(p, "w", encoding="utf-8"))
    print("NEW PAGE FAILED", u, "(its numbers did not match the source; the second try sends it back to the queue)")


# USGS peak qualifier codes (read live 2026-11-12 on 01646500, 09380000, 07289000, 03294500): one list for collect.py, lib/research.py and the blocks
DROP = {"HISTORIC", "DAMFAILURE", "MONTHUNKNOWN", "YEARUNKNOWN"}  # outside the systematic record, a dam break, no month or year
LOWER = {"MAXDAILYMEAN", "GREATERTHAN"}  # the true peak is at least this value (review #4): a lower bound, never a plain peak
UPPER = {"LESSTHAN"}  # the true peak is at most this value
REG = {"REGULATED", "UNKNOWNREGULATION"}  # flow changed by dams or diversions: studied apart
KEEP = {"ESTIMATED", "REVISED", "DAYUNKNOWN"}  # USGS's own value stands
