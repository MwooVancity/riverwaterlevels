"""One-command refresh: collect -> build -> check -> gates -> publish -> deploy. Stops at the first failing step; the live site stays on the last good release.
Usage: python -I refresh.py [--dry] [--no-collect]    Log: runs/refresh.log. GitHub's "refresh" concurrency group keeps it to one run at a time.
"""
import os, sys, subprocess, datetime, shutil, time, json

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from gates import PY, NPX, GATES, census, catches  # the one list of gates (gates.py)
GATE_NAMES = {n_ for _, g in GATES for n_, _c in g}

os.makedirs(os.path.join(ROOT, "runs"), exist_ok=True)
# the break test feeds invented data to test CODE: it runs in dry runs only; on a deploy it could only freeze real, good pages (2026-10-30)
DRY = "--dry" in sys.argv  # dryrun.yml: every gate on the cloud's last data, no collect, no publish, no deploy (2026-10-29: laptop data passed what the cloud failed, 3 times)
NOCOLLECT = DRY or "--no-collect" in sys.argv  # sharded.yml: the shard jobs already collected and merged
STEPS = ([] if NOCOLLECT else [("collect", PY + ["collect.py"])]) + [(n_, c) for _, g in GATES for n_, c in g if DRY or n_ != "break every input"] + ([] if DRY else [("publish", PY + ["publish.py"]), ("deploy", [NPX, "wrangler", "deploy"])])
CARRIED = os.path.join(ROOT, "dist_next", "_carried.json")  # check.py, truth_live and truth_world each add the pages they swapped for the live copy


def carried():
    return open(CARRIED, encoding="utf-8").read() if os.path.exists(CARRIED) else ""


code = 0
with open(os.path.join(ROOT, "runs", "refresh.log"), "a", encoding="utf-8") as log:
    log.write("\n=== %s ===\n" % datetime.datetime.now().isoformat(timespec="seconds"))
    from lib import ledger  # machinery audit: every step's seconds, so a step that grows is named before it hits the brake
    try:
        n_pages = len(json.load(open(os.path.join(ROOT, "dist", "_urls.json")))["urls"])
    except (OSError, ValueError, KeyError):
        n_pages = 0
    t_run = time.time()
    checked = None
    caught = {}  # gate -> what it caught this run; a gate the run never reached is not counted
    for name, s in STEPS:
        t0 = time.time()
        if name == "publish" and checked == carried():
            s = s + ["--checked"]  # audit 2026-11-10 #35: no gate carried a page in after the page checks, so publish does not run check.py again (40 min at 14,000 pages)
        p = subprocess.run(s, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
        log.write("$ %s -> %d\n%s\n" % (" ".join(s), p.returncode, (p.stdout + p.stderr)[-1500:]))
        census(p.stdout)
        if name in GATE_NAMES:
            caught[name] = catches(name, p.stdout, p.returncode)
        if name == "page checks" and not p.returncode:
            checked = carried()
        if not DRY:
            ledger.add(name, time.time() - t0, n_pages)  # the gate's own name (audit #40: the node self-test had none, the worker bundle was logged as "deploy")
        if p.returncode:
            code = p.returncode
            log.write("STOPPED at %s\n" % " ".join(s[1:3]))
            break
if not DRY:
    ledger.add("refresh total", time.time() - t_run, n_pages)
    ledger.add_catches(caught)  # build.py puts the last 10 runs in status.json; watchdog and ops_summary name a gate that caught nothing
for d in os.listdir(os.path.join(ROOT, "runs")):  # keep 14 days of per-run folders
    p = os.path.join(ROOT, "runs", d)
    if os.path.isdir(p) and time.time() - os.path.getmtime(p) > 14 * 86400:
        shutil.rmtree(p, ignore_errors=True)
if code:  # CI cannot see runs/refresh.log: print the failing step's tail so the cause is in the run log
    print(open(os.path.join(ROOT, "runs", "refresh.log"), encoding="utf-8").read()[-4000:])
print("refresh", "OK" if code == 0 else "FAILED (see runs/refresh.log)")
sys.exit(code)
