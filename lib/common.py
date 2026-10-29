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
esc = html.escape

# wave 0 slice: gauges chosen to exercise every case (full sensors, no sensors, multi-gauge river, snowmelt, small creek)


def template_hash():
    """Fingerprint of the code that decides what a page shows (hater review: a change here needs a fresh signed review). Line endings are
    normalised so a Windows checkout and CI agree."""
    import glob, hashlib
    files = sorted(glob.glob(os.path.join(ROOT, "lib", "*.py")) + glob.glob(os.path.join(ROOT, "templates", "*")) + [os.path.join(ROOT, f) for f in ("build.py", "collect.py", "worker/index.js", "data/name-fixes.csv", "data/name-overrides.csv", "data/index-allow.json", "data/sources.json")])
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
        return "%.2f" % v  # 0.45 cfs is not "0 cfs" (live numbers review: read as a dry creek)
    return "{:,.0f}".format(float("%.3g" % v) if abs(v) >= 1000 else v)  # hater 2026-10-27: computed means printed as "280,917 cfs"


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


def fc_word(vals, cur, unit="ft"):
    """'steady' when every forecast value prints the same, 'high' when the highest is above the latest reading, else 'at or below'.
    The single source for "Forecast high" (w11-w13 reviews: three places chose the word three ways)."""
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    if len({("%.1f" % v) if unit == "ft" else fmtc(v) for v in vals}) == 1:
        return "steady"
    return "high" if cur is None or max(vals) > cur + (0.05 if unit == "ft" else 0.02 * abs(cur)) else "below"


FC_LABEL = {"steady": "NWS forecast (steady)", "high": "Forecast high", "below": "NWS forecast (at or below the latest reading)"}


def r1(x):
    """A difference of two stages rounded half up to 0.1 before printing with %.1f."""
    return math.floor(x * 10 + 0.5 + 1e-9) / 10


def fmtd(v):
    """A difference in cfs, exact to the whole cfs (w10 review: 4,200 - 235 printed as 3,960)."""
    return "–" if v is None else "%.2f" % v if 0 < abs(v) < 1 else "{:,.0f}".format(v)


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


def river_at(river, place):
    """'Gauley River above Belva', 'Penns Creek', 'Missouri River at Kansas City': the place already names its preposition or the river."""
    p = (place or "").strip()
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


def band_word(p):
    """Plain-word USGS WaterWatch class of today's flow against the same date in past years (p = percentile 0-100, -1 below the 5th, 101 above the 95th, None unknown). Boundaries follow USGS WaterWatch: <10 much below, 10-24 below, 25-75 normal, 76-90 above, >90 much above."""
    if p is None:
        return "–"
    if p == 101 or p > 90:
        return "Much above normal"
    if p == -1 or p < 10:
        return "Much below normal"
    if p < 25:
        return "Below normal"
    if p <= 75:
        return "Normal range"
    return "Above normal"
