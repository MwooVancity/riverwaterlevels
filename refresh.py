"""One-command refresh: collect -> build -> check -> gates -> publish -> deploy. Stops at the first failing step; the live site stays on the last good release.
Usage: python -I refresh.py    Log: runs/refresh.log. GitHub's "refresh" concurrency group keeps it to one run at a time.
"""
import os, sys, subprocess, datetime, shutil, time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from gates import PY, NPX, GATES  # the one list of gates (gates.py)

os.makedirs(os.path.join(ROOT, "runs"), exist_ok=True)
STEPS = [PY + ["collect.py"]] + [c for _, g in GATES for _, c in g] + [PY + ["publish.py"], [NPX, "wrangler", "deploy"]]
code = 0
with open(os.path.join(ROOT, "runs", "refresh.log"), "a", encoding="utf-8") as log:
    log.write("\n=== %s ===\n" % datetime.datetime.now().isoformat(timespec="seconds"))
    for s in STEPS:
        p = subprocess.run(s, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
        log.write("$ %s -> %d\n%s\n" % (" ".join(s), p.returncode, (p.stdout + p.stderr)[-1500:]))
        if p.returncode:
            code = p.returncode
            log.write("STOPPED at %s\n" % " ".join(s[1:3]))
            break
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
