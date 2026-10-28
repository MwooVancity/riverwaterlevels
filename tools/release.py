"""Add the next gauges from the priority list to the site, in one command.
Usage: python -I tools/release.py N [--dry] [--list docs/research/priority/picks.csv]
Steps: pick the first N rows of the list that have no cache yet -> mark them live in data/waves.csv -> python -I collect.py <sites> (full) -> python -I build.py
-> print the new page URLs. A new page stays out of Google until `tools/open_wave.py N --apply` lists it. --dry prints the picks and stops.
"""
import os, sys, csv, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
args = [a for a in sys.argv[1:] if not a.startswith("--")]
n = int(args[0]) if args else 25
lst = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--list=")), os.path.join(ROOT, "docs", "research", "priority", "picks.csv"))
dry = "--dry" in sys.argv
PY = [sys.executable, "-I"]

cached = {f[:-5] for f in os.listdir(os.path.join(ROOT, "cache")) if f.endswith(".json")}
picks = [r for r in csv.DictReader(open(lst, encoding="utf-8")) if r["site"] not in cached][:n]
if not picks:
    sys.exit("nothing to add: every gauge in %s already has a cache" % lst)
print("adding %d gauges:" % len(picks))
for r in picks:
    print("  %s  %s at %s, %s  (%s)" % (r["site"], r["river"], r["place"], r["state"], r["category"]))
if dry:
    sys.exit(0)

# bookkeeping: data/waves.csv status queue -> live for these sites
wp = os.path.join(ROOT, "data", "waves.csv")
rows = list(csv.DictReader(open(wp, encoding="utf-8")))
sites = {r["site"] for r in picks}
for r in rows:
    if r["site"] in sites and r["status"] == "queue":
        r["status"] = "live"
with open(wp, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

subprocess.call(PY + [os.path.join(ROOT, "tools", "fetch_stats.py")] + sorted(sites), cwd=ROOT)  # wave 3: "is this normal" blank because new gauges had no stats file
rc = subprocess.call(PY + [os.path.join(ROOT, "collect.py")] + sorted(sites), cwd=ROOT)
if rc:
    sys.exit("collect failed (%d); nothing built" % rc)
subprocess.call(PY + [os.path.join(ROOT, "tools", "sync_legacy.py")], cwd=ROOT)  # CI builds from the repo: the new gauges' daily stats and land files must be committed with the wave (push legacy/ too)
rc = subprocess.call(PY + [os.path.join(ROOT, "build.py")], cwd=ROOT)
if rc:
    sys.exit("build failed (%d)" % rc)
urls = [r["url"] for r in picks if r.get("url")]
print("\nbuilt: %d new page(s). Now: push (deploys), python -I tools/open_wave.py %d --apply, push again." % (len(urls), len(urls)))
