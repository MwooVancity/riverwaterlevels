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
live_ = {r["site"]: r for r in csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8"))}
picks = [r for r in csv.DictReader(open(lst, encoding="utf-8")) if live_.get(r["site"], {}).get("status") == "queue" and not live_.get(r["site"], {}).get("gate")] if os.path.exists(lst) else []
seen_ = {r["site"] for r in picks}
picks += sorted((dict(r, category=r.get("activity") or "") for r in live_.values() if r["status"] == "queue" and not r.get("gate") and r["site"] not in seen_),
                key=lambda r: -float(r.get("score") or 0))  # after the owner's list: the scored queue, best first
picks = picks[:n]
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
import json
dead = set()
for s_ in sorted(sites):  # practice run 2026-10-29: Arkansas at Parkdale and Snake at Hells Canyon returned no USGS rows; they go back to the queue with a gate so tomorrow picks others
    try:
        c_ = json.load(open(os.path.join(ROOT, "cache", s_ + ".json"), encoding="utf-8"))
        ok_ = isinstance(c_, dict) and bool((c_.get("usgs") or {}).get("rows") if isinstance(c_.get("usgs"), dict) else c_.get("usgs"))
    except (OSError, ValueError):
        ok_ = False
    if not ok_:
        dead.add(s_)
if dead:
    rows = list(csv.DictReader(open(wp, encoding="utf-8")))
    for r in rows:
        if r["site"] in dead:
            r["status"], r["gate"] = "queue", "no-usgs-rows"
    with open(wp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("not released (no USGS readings): %s" % ", ".join(sorted(dead)))
    picks = [r for r in picks if r["site"] not in dead]
subprocess.call(PY + [os.path.join(ROOT, "tools", "sync_legacy.py")], cwd=ROOT)  # CI builds from the repo: the new gauges' daily stats and land files must be committed with the wave (push legacy/ too)
rc = subprocess.call(PY + [os.path.join(ROOT, "build.py")], cwd=ROOT)
if rc:
    sys.exit("build failed (%d)" % rc)


def page_check(picks_):
    """{site: first message} for each new gauge whose built page fails check.py's page checks (the same functions the site gate runs per page)."""
    os.chdir(ROOT)
    ck = {"__file__": os.path.join(ROOT, "check.py"), "__name__": "check"}
    exec(compile(open("check.py", encoding="utf-8").read().rsplit("\nmain()", 1)[0], "check.py", "exec"), ck)
    out = {}
    for r in picks_:
        u = r.get("url")
        f = os.path.join(ROOT, "dist_next", u.strip("/").replace("/", os.sep), "index.html") if u else ""
        if not f or not os.path.exists(f):
            out[r["site"]] = "no built page at %s" % u
            continue
        h = open(f, encoding="utf-8").read().replace("\u00a0", " ")  # as check_dir reads it (times use no-break spaces)
        bad = ck["check_html"](h, os.path.relpath(f, os.path.join(ROOT, "dist_next"))) + ck["rank_checks"](h, u) + ck["hater_rules"](h)
        if bad:
            out[r["site"]] = bad[0]
    return out


def truth_check(picks_):
    """{site: message} for each new gauge that breaks a truth contract (truth_tests.py, per-gauge contracts only): the same rules the gate runs, so the gate never meets a failure the release could have sent back."""
    import truth_tests
    truth_tests.bad.clear()
    truth_tests.main(only={r["site"] for r in picks_})
    out = {}
    for b_ in truth_tests.bad:
        site_, _, msg_ = b_.partition(": ")
        out.setdefault(site_, "truth: " + msg_)
    return out


failed = page_check(picks)  # robustness (owner 2026-10-29): one bad page must never block the day's release; it goes back to the queue with its reason and the rest ship
for s_, m_ in truth_check([r for r in picks if r["site"] not in failed]).items():
    failed[s_] = m_
if failed:
    rows = list(csv.DictReader(open(wp, encoding="utf-8")))
    for r in rows:
        if r["site"] in failed:
            r["status"], r["gate"] = "queue", (failed[r["site"]] if failed[r["site"]].startswith("truth: ") else "page-check: " + failed[r["site"]]).replace("\n", " ")[:300]
    with open(wp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    for s_, m_ in sorted(failed.items()):
        print("not released (%s): %s  %s" % ("truth contract" if m_.startswith("truth: ") else "page check", s_, m_))
    picks = [r for r in picks if r["site"] not in failed]
    rc = subprocess.call(PY + [os.path.join(ROOT, "build.py")], cwd=ROOT)
    if rc:
        sys.exit("rebuild failed (%d)" % rc)
urls = [r["url"] for r in picks if r.get("url")]
print("\nbuilt: %d new page(s). Now: push (deploys), python -I tools/open_wave.py %d --apply, push again." % (len(urls), len(urls)))
