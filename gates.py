"""The one list of gates, in THREE gates. refresh.py runs 1 and 2 before every deploy and 3 after it; `python -I gate.py` runs them by hand with one table and one exit code.
Add a check HERE and nowhere else. Order inside a gate: cheap and offline first. A gate passes only if every check in it passes.
  1 build and sources   the page builds; the page rules (Source line, units, times, sizes, structured data, sitemap, secrets) hold
  2 numbers             numbers on a page agree with each other, and with a fresh USGS and NWS fetch
  3 live                after the deploy: live pages against the sources, indexing state (the hourly watchdog.yml runs on its own)"""
import sys

PY = [sys.executable.replace("pythonw.exe", "python.exe"), "-I"]

GATE_1 = [("build", PY + ["build.py"]), ("page checks", PY + ["check.py"]), ("page rules self-test", PY + ["check.py", "--selftest"])]
GATE_2 = [("truth contracts", PY + ["truth_tests.py"]), ("built pages vs USGS/NWS", PY + ["tools/truth_live.py", "--dir", "dist_next"])]
GATE_3 = [("live pages vs USGS/NWS", PY + ["tools/truth_live.py"]), ("live indexing state", PY + ["tools/index_live.py"])]  # after the deploy

GATES = [("1 build and sources", GATE_1), ("2 numbers", GATE_2)]
GATES_LIVE = [("3 live", GATE_3)]

# flat lists for refresh.py (it collects, builds, checks and publishes between them)
ALWAYS = [c for _, c in GATE_1 if "--selftest" in c] + [c for _, c in GATE_2]
SOFT = [c for _, c in GATE_3]
