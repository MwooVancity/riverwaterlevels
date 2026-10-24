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
SLICE = ["06893000", "01646500", "06192500", "03011800", "01555000"]


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


def load_pages():
    rows = list(csv.DictReader(open(os.path.join(DATA, "pages-all.csv"), encoding="utf-8")))
    return {r["site"]: r for r in rows}


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
    return "–" if v is None else "{:,.0f}".format(v)


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
