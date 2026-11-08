"""One log line per Lighthouse mobile run (dryrun.yml input 'speed'; drawing board 8). Usage: python -I tools/lh_line.py lh.json <path>
Prints score, LCP, CLS, TBT, bytes, the LCP element, and the three third parties that block longest, so the next fix names its cause."""
import json, sys

r = json.load(open(sys.argv[1], encoding="utf-8"))
a = r["audits"]
dv = lambda k: (a.get(k) or {}).get("displayValue", "?")
try:
    el = a["largest-contentful-paint-element"]["details"]["items"][0]["items"][0]["node"].get("snippet", "?")[:90]
except (KeyError, IndexError, TypeError):
    el = "unknown"
try:
    tp = sorted(a["third-party-summary"]["details"]["items"], key=lambda x: -(x.get("blockingTime") or 0))[:3]
    tps = "; ".join("%s %d KB %d ms" % ((x.get("entity") or {}).get("text", x.get("entity")) if isinstance(x.get("entity"), dict) else x.get("entity"), (x.get("transferSize") or 0) // 1024, x.get("blockingTime") or 0) for x in tp)
except (KeyError, TypeError):
    tps = "unknown"
print("speed %s: score %d, LCP %s, CLS %s, TBT %s, %s; LCP element %s; third parties %s" % (
    sys.argv[2], round((r["categories"]["performance"]["score"] or 0) * 100), dv("largest-contentful-paint"), dv("cumulative-layout-shift"), dv("total-blocking-time"), dv("total-byte-weight"), el, tps))
