"""Source-health gate (owner 2026-10-25: "we should always have all the data;
a missing source means something is broken, not a missing block").

Reads state/source-health.json (written by a FULL collect) and fails the build, by name, when:
  1. any source ERRORED (exception: bad/missing key, 404, parse error) on > FAIL_RATE of gauges — a systemic fault; or
  2. a UNIVERSAL source returned data on < MIN_COVER of gauges — endpoint moved, key dead, or schema changed (empty 200s).

A source listed `off` in data/sources.json is a documented gap (no working public feed) and is exempt.
No health file yet (fresh repo, or only fast runs so far) = pass with a note, so this never blocks before a full run exists.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.common import ROOT
from lib.source_list import UNIVERSAL

FAIL_RATE = 0.15   # a source erroring on more than this share of gauges is a systemic break
MIN_COVER = 0.85   # a universal source must return data on at least this share of gauges
MIN_GAUGES = 10    # below this, one transient 429/500/502 skews the rate; too thin to judge (a full run is ~50+)

hp = os.path.join(ROOT, "state", "source-health.json")
if not os.path.exists(hp):
    print("source-health: no health file yet (no full collect recorded) — skipping")
    sys.exit(0)

h = json.load(open(hp, encoding="utf-8"))
srcs = h.get("sources") or {}
n = max((c.get("ok", 0) + c.get("absent", 0) + c.get("failed", 0) for c in srcs.values()), default=0)
if n < MIN_GAUGES:
    print("source-health: only %d gauges collected (< %d) - sample too thin to judge, skipping (a full run decides)" % (n, MIN_GAUGES))
    sys.exit(0)

off = set()
try:
    sj = json.load(open(os.path.join(ROOT, "data", "sources.json"), encoding="utf-8"))
    rows = sj if isinstance(sj, list) else sj.get("sources", sj)
    items = rows.items() if isinstance(rows, dict) else [(r.get("id", r.get("key")), r) for r in rows]
    off = {k for k, v in items if isinstance(v, dict) and v.get("status") == "off"}
except Exception:
    pass

fails = []
for src, c in sorted(srcs.items()):
    if src in off:
        continue
    ok, absent, failed = c.get("ok", 0), c.get("absent", 0), c.get("failed", 0)
    tot = ok + absent + failed or 1
    if failed / tot > FAIL_RATE:
        fails.append("%s: errored on %d/%d gauges (%.0f%%) - endpoint, key or schema broken" % (src, failed, tot, 100 * failed / tot))
    elif src in UNIVERSAL and ok / tot < MIN_COVER:
        fails.append("%s: data on only %d/%d gauges (%.0f%%); a universal source should be ~100%% - endpoint moved or returning empty" % (src, ok, tot, 100 * ok / tot))

if fails:
    print("SOURCE-HEALTH GATE FAILED (health recorded %s, %d gauges):" % (h.get("at", "?"), h.get("gauges", 0)))
    for f in fails:
        print("  x " + f)
    print("Fix the source, or if no working public feed exists set it `off` in data/sources.json with a dated reason (then it is a documented gap, not a silent failure).")
    sys.exit(1)

print("source-health: all sources healthy across %d gauges" % h.get("gauges", 0))
sys.exit(0)
