"""One-command refresh: collect -> build -> check -> publish -> deploy -> livecheck. Stops at the first failing step; live site stays on the last good release.
Usage: python -I refresh.py        Log: runs/refresh.log. A lock file stops two runs at once.
"""
import os, sys, subprocess, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
os.environ["PATH"] = os.pathsep.join([r"C:\Program Files\nodejs", os.path.join(os.environ.get("APPDATA", ""), "npm"), os.environ.get("PATH", "")])  # the scheduler starts with a bare PATH
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # no console flashes when run by the scheduler
LOCK = os.path.join(ROOT, "runs", "refresh.lock")
os.makedirs(os.path.join(ROOT, "runs"), exist_ok=True)
if os.path.exists(LOCK) and (datetime.datetime.now().timestamp() - os.path.getmtime(LOCK)) < 2700:
    sys.exit("another refresh is running (runs/refresh.lock)")
open(LOCK, "w").write(str(os.getpid()))
log = open(os.path.join(ROOT, "runs", "refresh.log"), "a", encoding="utf-8")
PY = [sys.executable.replace("pythonw.exe", "python.exe"), "-I"]
FAST = ["--fast"] if "--fast" in sys.argv else []  # fast = bulk USGS latest + NWS/NWPS/rain only (every 30 min); no flag = everything (every 6 h)
STEPS = [PY + ["collect.py"] + FAST, PY + ["build.py"], PY + ["check.py"], PY + ["publish.py"],
         ["npx.cmd" if os.name == "nt" else "npx", "wrangler", "deploy"], PY + ["livecheck.py"]]
# Always run, they block a deploy: every gauge page's contracts (truth_tests.py); the built pages against a fresh USGS and NWS fetch (a USGS or NWS outage only warns).
sys.path.insert(0, ROOT)
from gates import ALWAYS, SOFT  # the one list of gates (gates.py); `python -I gate.py` runs the same list by hand
STEPS[3:3] = ALWAYS
STEPS.extend(SOFT)
code = 0
soft_failed = []  # post-deploy live gates: the deploy already happened, but a failure must turn the run red so the owner gets the email
try:
    log.write("\n=== %s %s, gates: %s ===\n" % (datetime.datetime.now().isoformat(timespec="seconds"), "fast" if FAST else "full", "3 gates"))
    for s in STEPS:
        p = subprocess.run(s, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, creationflags=NOWIN)
        log.write("$ %s -> %d\n%s\n" % (" ".join(s), p.returncode, (p.stdout + p.stderr)[-1500:]))
        if p.returncode and s in SOFT:
            log.write("LIVE GATE FAILED after the deploy (run turns red, site stays up): %s\n" % " ".join(s[-2:]))
            soft_failed.append(" ".join(s[-2:]))
        elif p.returncode:
            code = p.returncode
            log.write("STOPPED at %s\n" % s[2] if len(s) > 2 else "STOPPED\n")
            break
finally:
    log.close()
    os.remove(LOCK)
    try:  # runs/ retention: keep 14 days of per-run folders (repo audit 2026-10-20: 476 folders, unbounded growth)
        import shutil, time
        for d in os.listdir(os.path.join(ROOT, "runs")):
            p = os.path.join(ROOT, "runs", d)
            if os.path.isdir(p) and time.time() - os.path.getmtime(p) > 14 * 86400:
                shutil.rmtree(p, ignore_errors=True)
    except OSError:
        pass
if code == 0 and soft_failed:
    print("refresh DEPLOYED, but a live gate failed afterwards: %s (see runs/refresh.log)" % "; ".join(soft_failed))
    sys.exit(2)
print("refresh", "OK" if code == 0 else "FAILED (see runs/refresh.log)")
sys.exit(code)
