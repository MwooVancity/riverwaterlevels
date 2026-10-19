"""Record a fresh-brain review verdict (docs/REVIEW-PROMPT.md) in state/reviews.json.
Usage: python tools/record_review.py SHIP docs/research/FRESH-REVIEW-7.md            marks the current template hash and every NEW gauge page in dist_next (not yet live)
       python tools/record_review.py HOLD docs/research/FRESH-REVIEW-7.md            records a HOLD (nothing unlocks)
Only run it after the report is written and its P0 list is empty; publish.py refuses new gauge pages without a SHIP entry."""
import json, os, sys, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from lib.reviewgate import GAUGE  # noqa: E402
from template_hash import template_hash  # noqa: E402


def urls(d):
    f = os.path.join(ROOT, d, "_urls.json")
    return json.load(open(f))["urls"] if os.path.exists(f) else []


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("SHIP", "HOLD"):
        sys.exit(__doc__)
    verdict, report = sys.argv[1], sys.argv[2]
    if not os.path.exists(os.path.join(ROOT, report)):
        sys.exit("report not found: " + report)
    p = os.path.join(ROOT, "state", "reviews.json")
    rv = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    rv.setdefault("templates", {}); rv.setdefault("pages", {})
    entry = {"verdict": verdict, "report": report, "date": datetime.date.today().isoformat()}
    rv["templates"][template_hash()] = dict(entry)
    live = set(urls("dist"))
    new = [u for u in urls("dist_next") if GAUGE.match(u) and u not in live]
    for u in new:
        rv["pages"][u] = dict(entry, template=template_hash())
    json.dump(rv, open(p, "w", encoding="utf-8"), indent=1)
    print("%s recorded for template %s and %d new gauge page(s)" % (verdict, template_hash(), len(new)))


main()
