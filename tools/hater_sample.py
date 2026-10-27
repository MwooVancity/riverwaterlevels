"""Hater review sample for a code change: the fewest gauge pages that together show every block and every page situation.
A situation is a block id, a tile kind, or a state the hero can be in (tidal or rising-and-falling, no forecast, stage from NWS, not
measured, stale, active alert, below a dam). Greedy set cover over the built pages; prints the sites, then what each one adds.
Usage: python -I tools/hater_sample.py [dist dir]    Then: node tools/hater_shots.mjs <sites>"""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "dist_next")
STATES = {"tidal": "Tidal reach:", "rose-and-fell": "Rose and fell:", "nws-stage": "NWS observed at", "not-measured": "Not measured",
          "no-forecast": "has no current river forecast", "not-linked": "Not linked", "stale": "Older than", "alert": "active NWS alert",
          "below-dam": "below a dam", "impact-reached": "reached at the latest reading", "reading-of": "Reading of", "flag": "USGS flag"}
live = {u: s for s, u, *_ in json.load(open(os.path.join(D, "live-sites.json"), encoding="utf-8"))}
feats = {}
for u, s in live.items():
    p = os.path.join(D, u.strip("/").replace("/", os.sep), "index.html")
    if not os.path.exists(p):
        continue
    h = open(p, encoding="utf-8").read()
    f = {"block:" + b for b in re.findall(r'<section class="card blk" data-f="[^"]*" id="([^"]+)"', h)}
    f |= {"tile:" + t for t in re.findall(r'<div class="tile ([a-z]+)', h)}
    f |= {"state:" + k for k, v in STATES.items() if v in h}
    feats[s] = f
need = set().union(*feats.values())
pick = []
while need:
    s = max(feats, key=lambda k: (len(feats[k] & need), k))
    pick.append((s, sorted(feats[s] & need)))
    need -= feats[s]
print(" ".join(s for s, _ in pick))
for s, add in pick:
    print("  %s adds %d: %s" % (s, len(add), ", ".join(add)[:300]))
