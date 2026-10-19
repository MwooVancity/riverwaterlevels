"""Pre-deploy review gate for NEW gauge pages: a gauge page (or its Forecast page) that is not in the live release may only go live when state/reviews.json records a SHIP verdict
from a fresh-brain reader review (docs/REVIEW-PROMPT.md) for it. Pages already live are not blocked, so the 30-minute data refresh is never held up by this gate."""
import re

GAUGE = re.compile(r"^/river/[^/]+/[^/]+/(forecast/)?$")


def unreviewed_new_pages(next_urls, live_urls, reviews):
    """next_urls and live_urls are lists of URL paths; reviews is the parsed state/reviews.json. Returns the new gauge pages without a SHIP verdict."""
    pages = (reviews or {}).get("pages", {})
    live = set(live_urls)
    out = []
    for u in sorted(next_urls):
        if GAUGE.match(u) and u not in live and pages.get(u, {}).get("verdict") != "SHIP":
            out.append(u)
    return out
