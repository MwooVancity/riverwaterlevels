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
SOFT = [PY + ["tools/truth_live.py"]]  # after the deploy: every live gauge page against USGS and NWS; logged, the watchdog alerts on it
PLAN = subprocess.run(PY + ["tools/gate_plan.py"], cwd=ROOT, capture_output=True, text=True, creationflags=NOWIN).stdout.strip() or "full"  # light = same template as the live site: a data refresh
# Always run, they block a deploy: the template needs a signed fresh-brain SHIP (docs/REVIEW-PROMPT.md); every gauge page's contracts (truth_tests.py); the built pages against a fresh USGS and NWS fetch (a USGS or NWS outage only warns).
ALWAYS = [PY + ["tools/stamp_template.py"], PY + ["tools/template_hash.py", "--check"], PY + ["truth_tests.py"], PY + ["truth_types.py"], PY + ["tools/truth_live.py", "--dir", "dist_next"]]
# Only when the template changed (or the live template cannot be read): browser layout gates. They passed for this exact template when it was released, so a font or browser hiccup can never freeze fresh data.
BROWSER = [["node", "ui_gates.mjs"], ["node", "tools/review/search_test.mjs"], ["node", "tools/review/clip_all.mjs"], ["node", "tools/review/alerts_live_test.mjs"], ["node", "tools/review/range_test.mjs"], PY + ["truth_fuzz.py"]]
STEPS[3:3] = ALWAYS + (BROWSER if PLAN == "full" else [])
STEPS.append(SOFT[0])
code = 0
try:
    log.write("\n=== %s %s, gates: %s ===\n" % (datetime.datetime.now().isoformat(timespec="seconds"), "fast" if FAST else "full", PLAN))
    for s in STEPS:
        p = subprocess.run(s, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, creationflags=NOWIN)
        log.write("$ %s -> %d\n%s\n" % (" ".join(s), p.returncode, (p.stdout + p.stderr)[-1500:]))
        if p.returncode and s in SOFT:
            log.write("SOFT GATE FAILED (not blocking): %s\n" % " ".join(s[-2:]))
        elif p.returncode:
            code = p.returncode
            log.write("STOPPED at %s\n" % s[2] if len(s) > 2 else "STOPPED\n")
            break
finally:
    log.close()
    os.remove(LOCK)
print("refresh", "OK" if code == 0 else "FAILED (see runs/refresh.log)")
sys.exit(code)
