"""Pre-deploy review gate for NEW gauge pages: a gauge page (or its Forecast page) that is not in the live release may only go live when data/reviews.json records a SHIP verdict
from a fresh-brain reader review (docs/REVIEW-PROMPT.md) for it. Pages already live are not blocked, so the 30-minute data refresh is never held up by this gate."""
import hashlib, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STRICT = True  # tests may switch it off for pure logic tests; production never does


def sign(verdict, report, key):
    """Signature of one verdict: the report file's content hash, the verdict and what it covers (a URL or a template hash). tools/record_review.py writes it; a hand-edited verdict has none and does not count."""
    p = os.path.join(ROOT, report)
    if not os.path.isfile(p):
        return ""
    return hashlib.sha256(("%s|%s|%s|%s" % (verdict, report, hashlib.sha256(open(p, "rb").read()).hexdigest(), key)).encode()).hexdigest()[:24]


def is_ship(entry, key):
    """True only for a SHIP verdict whose signature matches its report file (the report still exists and is unchanged)."""
    e = entry or {}
    if e.get("verdict") != "SHIP":
        return False
    return (not STRICT) or (bool(e.get("sig")) and e.get("sig") == sign("SHIP", e.get("report", ""), key))


def is_ok(entry, key):
    return (entry or {}).get("verdict") == "GRANDFATHERED" or is_ship(entry, key)


GAUGE = re.compile(r"^/river/[^/]+/[^/]+/(forecast/)?$")
# GRANDFATHERED = live before the gate existed; it never unlocks INDEXING (check.py needs a signed SHIP for that)


def unreviewed_new_pages(next_urls, live_urls, reviews):
    """next_urls and live_urls are lists of URL paths; reviews is the parsed data/reviews.json. Returns the new gauge pages without a SHIP verdict."""
    pages = (reviews or {}).get("pages", {})
    live = set(live_urls)
    out = []
    for u in sorted(next_urls):
        if GAUGE.match(u) and u not in live and not is_ok(pages.get(u), u):
            out.append(u)
    return out


def hold_back(rows_by_site, live_urls, reviews, has_fc_page=None):
    """For build.py: which new, unreviewed pages to leave out of THIS build so that the other pages still ship (a data refresh must never be blocked by a new page waiting for review).
    Returns (gauges_to_skip, forecast_pages_to_skip). A page is held when it is not in the live release AND has no SHIP or GRANDFATHERED verdict. When the live release cannot be read (empty list) only the verdicts decide, so existing pages stay (they are GRANDFATHERED). No verdict file at all = the gate has not started: nothing is held."""
    pages = (reviews or {}).get("pages", {})
    if not pages:
        return set(), set()
    live = set(live_urls)
    skip_g, skip_f = set(), set()
    for site, row in rows_by_site.items():
        d, f = row["dashboard_url"], row["forecast_url"]
        if d not in live and not is_ok(pages.get(d), d):
            skip_g.add(site)
        elif (has_fc_page is None or site in has_fc_page) and f not in live and not is_ok(pages.get(f), f):
            skip_f.add(site)
    return skip_g, skip_f
