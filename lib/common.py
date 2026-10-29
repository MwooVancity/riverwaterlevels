"""Shared paths, data loading and helpers for the River Water Levels build."""
import os, re, csv, json, math, datetime, html, urllib.request, urllib.parse

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CACHE = os.path.join(ROOT, "cache")
DIST = os.path.join(ROOT, "dist")
DATA = os.path.join(ROOT, "data")
BRAND = "River Water Levels"
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
    if not pts:
        return None
    if v < pts[0][1]:
        return -1
    if v > pts[-1][1]:
        return 101
    for (p0, v0), (p1, v1) in zip(pts, pts[1:]):
        if v0 <= v <= v1:
            return p0 if v1 == v0 else p0 + (p1 - p0) * (v - v0) / (v1 - v0)
    return None


def ordinal(n):
    n = int(round(n))
    return "%d%s" % (n, "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def prep_lower(place):
    """USGS names put 'Near', 'At', 'Above', 'Below' (and river names 'Of', 'The', 'And') in capitals inside a name ('Glenwood Bridge Near Boise', 'Red River Of The North'): as small words they are lower case."""
    return re.sub(r"(?<=\S )(Near|At|Above|Below|Of|The|And)(?= \S)", lambda m: m.group(1).lower(), place or "")


def river_at(river, place):
    """'Gauley River above Belva', 'Penns Creek', 'Missouri River at Kansas City': the place already names its preposition or the river."""
    p = prep_lower((place or "").strip())
    if not p or p.lower() == river.lower():
        return river
    first = p.split(" ", 1)[0].lower()
    if first in ("above", "below", "near", "at"):
        return "%s %s%s" % (river, first, p[len(first):])
    return "%s at %s" % (river, p)


ADSENSE = '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8997828618122077" crossorigin="anonymous"></script>'  # AdSense site loader (owner 2026-10-23); head of indexable pages only, never the embed panel or 404


PCT_PHRASE = {"Much above normal": "much above normal", "Above normal": "above normal", "Normal range": "in the normal range", "Below normal": "below normal", "Much below normal": "much below normal", "\u2013": "not classed"}


def sig3(v):
    """A model guess shown to 3 significant figures (hater 2026-10-27: '280,917 cfs' is false precision)."""
    return float("%.3g" % v) if v else v


BAND_CUTS = (10, 25, 75, 90)  # percentile cut-offs of the five classes (USGS WaterWatch): under 10 much below, under 25 below, 25 to 75 normal, up to 90 above, over 90 much above. band_word, band_cls and the glossary all read this.


def band_glossary():
    """The glossary sentence for the five headline words, generated from BAND_CUTS."""
    a, b, c, d = BAND_CUTS
    return ("Much below normal means below the %dth percentile, Below normal from the %dth up to the %dth, Normal range from the %dth to the %dth, "
            "Above normal above the %dth up to the %dth, and Much above normal above the %dth percentile." % (a, a, b, b, c, c, d, d))


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
        return "Normal range"
    return "Above normal"


def dir_lv(G):
    """The flow a list row shows: on a tidal reach the latest reading is a moment in the tide cycle (Freeport swings 1,090 to 12,500 cfs in a day), so lists show the 24 h mean the comparison uses; the gauge page shows the day's range.
    Every list of gauges (home, state, hub, nearby, upstream and downstream) calls this."""
    return G["basis"] if G.get("osc") and G.get("basis_mean") else G["lv"]


def band_cls(p):
    """Colour class of a percentile, one cut for every page: 'la' under the 25th, 'lp' over the 75th, 'lb' between, '' unknown."""
    return "" if p is None else "la" if p < 25 else "lp" if p > 75 else "lb"
