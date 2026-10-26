"""The one list of gates, in THREE gates. refresh.py runs 1 and 2 before every deploy and 3 after it; `python -I gate.py` runs them by hand with one table and one exit code.
Add a check HERE and nowhere else. Order inside a gate: cheap and offline first. A gate passes only if every check in it passes.
  1 it builds       the page builds, the page rules hold (Source line, units, times, sizes, structured data, sitemap, secrets), the edge worker bundles
  2 it is true      numbers on a page agree with each other, and with a fresh USGS and NWS fetch
  3 it is live      after the deploy: live pages against USGS and NWS
Gates block only what would show a reader something wrong. Everything that can heal (site not rebuilt, missing gauges, a dead feed,
stale edge readings) is tools/watchdog.py, hourly, which heals and reports and never blocks a deploy (2026-10-25: a blocking
source-health gate and a whole-site abort on one missing cache froze all 53 pages)."""
import os, sys

PY = [sys.executable.replace("pythonw.exe", "python.exe"), "-I"]
NPX = "npx.cmd" if os.name == "nt" else "npx"

GATE_1 = [("build", PY + ["build.py"]), ("page checks", PY + ["check.py"]), ("page rules self-test", PY + ["check.py", "--selftest"]),
          ("edge worker bundles", [NPX, "wrangler", "deploy", "--dry-run", "--outdir", ".wrangler/dry"])]
GATE_2 = [("truth contracts", PY + ["truth_tests.py"]), ("built pages vs USGS/NWS", PY + ["tools/truth_live.py", "--dir", "dist_next"])]
GATE_3 = [("live pages vs USGS/NWS", PY + ["tools/truth_live.py"])]  # after the deploy

GATES = [("1 build and sources", GATE_1), ("2 numbers", GATE_2)]
GATES_LIVE = [("3 live", GATE_3)]

# flat lists for refresh.py (it collects, builds, checks and publishes between them)
ALWAYS = [c for _, c in GATE_1 if "--selftest" in c or "--dry-run" in c] + [c for _, c in GATE_2]
SOFT = [c for _, c in GATE_3]
