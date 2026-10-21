"""The one list of gates, in SIX gates. refresh.py runs them before every deploy; `python -I gate.py` runs them by hand with one table and one exit code.
Add a check HERE and nowhere else. Order inside a gate: cheap and offline first. A gate passes only if every check in it passes.
  1 build and rules   the page builds, the page rules hold, the template is signed
  2 truth             numbers, gauge types, time edge cases, release logic, junk-data fuzz
  3 sources           the built pages against a fresh USGS and NWS fetch (and after deploy: live pages, indexing state)
  4 reader browser    layout, contrast, taps, tables, search, live updates, tab heights, detail checks
  5 agent             a fresh agent answered "would this reach #1" for this template
  6 watch             the hourly watchdog (staleness, failed gauges, mismatch with live)"""
import sys

PY = [sys.executable.replace("pythonw.exe", "python.exe"), "-I"]
NODE = ["node"]

GATE_1 = [
    ("LINE 0: every water-activity item shown or declared", PY + ["tools/line0_gate.py"]),
    ("template stamp", PY + ["tools/stamp_template.py"]),
    ("template signed review", PY + ["tools/template_hash.py", "--check"]),
    ("page rules self-test", PY + ["check.py", "--selftest"]),
]
GATE_2 = [
    ("truth contracts (22)", PY + ["truth_tests.py"]),
    ("gauge types (10)", PY + ["truth_types.py"]),
    ("time edge cases", PY + ["truth_time.py"]),
    ("release logic (8)", PY + ["tests_logic.py"]),
]
GATE_2_SLOW = [("fuzzer (9,000 junk renders)", PY + ["truth_fuzz.py"])]  # only when the template changed
GATE_3 = [("built pages vs USGS/NWS", PY + ["tools/truth_live.py", "--dir", "dist_next"])]
GATE_3_LIVE = [("live pages vs USGS/NWS", PY + ["tools/truth_live.py"]), ("live indexing state", PY + ["tools/index_live.py"])]  # after the deploy
GATE_4 = [
    ("UI: contrast, taps, first screen", NODE + ["ui_gates.mjs"]),
    ("tables never scroll sideways", NODE + ["tools/review/clip_all.mjs"]),
    ("search", NODE + ["tools/review/search_test.mjs"]),
    ("live alerts", NODE + ["tools/review/alerts_live_test.mjs"]),
    ("live flow", NODE + ["tools/review/live_flow_test.mjs"]),
    ("reader budget: tab heights", NODE + ["tools/review/reader_budget.mjs"]),
    ("editor: detail checks", NODE + ["tools/review/editor_gate.mjs"]),
]
GATE_5 = [("agent: would a river user pick it (#1)", PY + ["tools/agent_gate.py"])]  # needs a fresh Claude agent (a script cannot start one); gate.py runs it, CI does not
GATE_6 = [("watchdog (hourly, network)", PY + ["tools/watchdog.py"])]  # gate.py --live only; CI runs it hourly on its own

GATES = [("1 build and rules", GATE_1), ("2 truth", GATE_2 + GATE_2_SLOW), ("3 sources", GATE_3), ("4 reader browser", GATE_4), ("5 agent", GATE_5)]
GATES_LIVE = [("3 sources (live)", GATE_3_LIVE), ("6 watch", GATE_6)]

# flat lists for refresh.py (it builds, checks and publishes between them)
ALWAYS = [c for _, c in GATE_1 + GATE_2 + GATE_3]
BROWSER = [c for _, c in GATE_4 + GATE_2_SLOW]
SOFT = [c for _, c in GATE_3_LIVE]
