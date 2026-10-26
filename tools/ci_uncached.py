"""Print the count of LIVE gauges that have no cache file yet.
CI uses this to force a full run (which collects them) instead of a fast run
that would silently skip cacheless gauges and never deploy their pages.
No river is refused deploy for a missing cache: a nonzero count means collect them.
"""
import csv, os, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
waves = os.path.join(ROOT, "data", "waves.csv")
live = {r["site"] for r in csv.DictReader(open(waves, encoding="utf-8")) if r.get("status") == "live"}
have = {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(ROOT, "cache", "*.json"))}
missing = sorted(live - have)
if missing:
    print(len(missing))  # stdout: the number CI reads
    import sys
    print("uncached live gauges -> forcing full: " + ", ".join(missing), file=sys.stderr)
else:
    print(0)
