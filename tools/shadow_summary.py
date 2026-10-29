"""Shadow collect summary (collect-shadow.yml): read every shard's report and timing from DIR/shard-*/, merge the shards' cache files into DIR/merged
(a site file written by two shards is a failure; state-XX.json may repeat), print the totals and the top time sinks.
Usage: python -I tools/shadow_summary.py DIR WORKFLOW_WALL_SECONDS
"""
import sys, os, json, glob, shutil

d, wall = sys.argv[1], float(sys.argv[2])
tot = {"gauges": 0, "stale": 0, "rows_off": 0, "unreadable": 0, "no_base": 0}
miss, fails, lab, walls, bad = {}, {}, {}, [], []
os.makedirs(os.path.join(d, "merged"), exist_ok=True)
for sh in sorted(glob.glob(os.path.join(d, "shard-*"))):
    r = json.load(open(os.path.join(sh, "report.json")))
    t = json.load(open(os.path.join(sh, "timing.json")))
    tot["gauges"] += r["gauges"]; tot["stale"] += len(r["stale"]); tot["rows_off"] += len(r["rows_off"]); tot["unreadable"] += len(r["unreadable"]); tot["no_base"] += len(r["new_gauge"])
    for k, v in r["missing_source"].items():
        miss.setdefault(k, []).extend(v)
    for k, v in r["new_failures"].items():
        fails.setdefault(k, []).append(v)
    walls.append(t["wall_s"])
    for k, (n, sec) in t["labels"].items():
        a = lab.setdefault(k, [0, 0.0]); a[0] += n; a[1] += sec
    for f in os.listdir(os.path.join(sh, "cache")):
        dst = os.path.join(d, "merged", f)
        if os.path.exists(dst) and not f.startswith("state-"):
            bad.append(f)
        shutil.copy(os.path.join(sh, "cache", f), dst)
print("shards %d, slowest collect %.0f s (%.1f min), mean %.0f s, workflow wall %.1f min" % (len(walls), max(walls), max(walls) / 60, sum(walls) / len(walls), wall / 60))
print("gauges compared %d, stale %d, rows off %d, unreadable %d, no base record %d, merge collisions %d" % (tot["gauges"], tot["stale"], tot["rows_off"], tot["unreadable"], tot["no_base"], len(bad)))
print("sources the base had and the shadow lacks: %s" % ({k: len(v) for k, v in miss.items()} or "none"))
print("new failures: %s" % (fails or "none"))
print("time sinks, summed over shards (calls, seconds):")
for k, (n, sec) in sorted(lab.items(), key=lambda kv: -kv[1][1])[:22]:
    print("  %-62s %6d %8.0f" % (k, n, sec))
sys.exit(1 if bad or tot["unreadable"] else 0)
