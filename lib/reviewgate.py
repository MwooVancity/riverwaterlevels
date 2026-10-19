"""Pre-deploy review gate for NEW gauge pages: a gauge page (or its Forecast page) that is not in the live release may only go live when data/reviews.json records a SHIP verdict
from a fresh-brain reader review (docs/REVIEW-PROMPT.md) for it. Pages already live are not blocked, so the 30-minute data refresh is never held up by this gate."""
import re

GAUGE = re.compile(r"^/river/[^/]+/[^/]+/(forecast/)?$")
OK = ("SHIP", "GRANDFATHERED")  # GRANDFATHERED = live before the gate existed; it never unlocks INDEXING (check.py needs SHIP for that)


def unreviewed_new_pages(next_urls, live_urls, reviews):
    """next_urls and live_urls are lists of URL paths; reviews is the parsed data/reviews.json. Returns the new gauge pages without a SHIP verdict."""
    pages = (reviews or {}).get("pages", {})
    live = set(live_urls)
    out = []
    for u in sorted(next_urls):
        if GAUGE.match(u) and u not in live and pages.get(u, {}).get("verdict") not in OK:
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
        if d not in live and pages.get(d, {}).get("verdict") not in OK:
            skip_g.add(site)
        elif (has_fc_page is None or site in has_fc_page) and f not in live and pages.get(f, {}).get("verdict") not in OK:
            skip_f.add(site)
    return skip_g, skip_f
