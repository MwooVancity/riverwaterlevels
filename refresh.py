"""One-command refresh: collect -> build -> check -> gates -> publish -> deploy. Stops at the first failing step; the live site stays on the last good release.
Usage: python -I refresh.py [--dry] [--no-collect]    Log: runs/refresh.log. GitHub's "refresh" concurrency group keeps it to one run at a time.
"""
import os, sys, subprocess, datetime, shutil, time, json

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from gates import PY, NPX, GATES, census  # the one list of gates (gates.py)

os.makedirs(os.path.join(ROOT, "runs"), exist_ok=True)
# the break test feeds invented data to test CODE: it runs in dry runs only; on a deploy it could only freeze real, good pages (2026-10-30)
DRY = "--dry" in sys.argv  # dryrun.yml: every gate on the cloud's last data, no collect, no publish, no deploy (2026-10-29: laptop data passed what the cloud failed, 3 times)
NOCOLLECT = DRY or "--no-collect" in sys.argv  # sharded.yml: the shard jobs already collected and merged
STEPS = ([] if NOCOLLECT else [PY + ["collect.py"]]) + [c for _, g in GATES for n_, c in g if DRY or n_ != "break every input"] + ([] if DRY else [PY + ["publish.py"], [NPX, "wrangler", "deploy"]])
code = 0
with open(os.path.join(ROOT, "runs", "refresh.log"), "a", encoding="utf-8") as log:
    log.write("\n=== %s ===\n" % datetime.datetime.now().isoformat(timespec="seconds"))
    from lib import ledger  # machinery audit: every step's seconds, so a step that grows is named before it hits the brake
    try:
        n_pages = len(json.load(open(os.path.join(ROOT, "dist", "_urls.json")))["urls"])
    except (OSError, ValueError, KeyError):
        n_pages = 0
    t_run = time.time()
    for s in STEPS:
        t0 = time.time()
        p = subprocess.run(s, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
        log.write("$ %s -> %d\n%s\n" % (" ".join(s), p.returncode, (p.stdout + p.stderr)[-1500:]))
        census(p.stdout)
        if not DRY:
            ledger.add("deploy" if s[0] == NPX else " ".join(os.path.basename(a).replace(".py", "") for a in s[len(PY):len(PY) + 2] if not a.startswith("--") or a == s[len(PY) + 1]), time.time() - t0, n_pages)
        if p.returncode:
            code = p.returncode
            log.write("STOPPED at %s\n" % " ".join(s[1:3]))
            break
if not DRY:
    ledger.add("refresh total", time.time() - t_run, n_pages)
if not DRY:  # the watchdog can dispatch a refresh: never from a practice run
    w = subprocess.run(PY + ["tools/watchdog.py"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
    print((w.stdout + w.stderr)[-3000:])  # the doctor's report in every run log; never changes the run's outcome
for d in os.listdir(os.path.join(ROOT, "runs")):  # keep 14 days of per-run folders
    p = os.path.join(ROOT, "runs", d)
    if os.path.isdir(p) and time.time() - os.path.getmtime(p) > 14 * 86400:
        shutil.rmtree(p, ignore_errors=True)
if code:  # CI cannot see runs/refresh.log: print the failing step's tail so the cause is in the run log
    print(open(os.path.join(ROOT, "runs", "refresh.log"), encoding="utf-8").read()[-4000:])
print("refresh", "OK" if code == 0 else "FAILED (see runs/refresh.log)")
sys.exit(code)
