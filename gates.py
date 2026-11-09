"""The one list of gates, and the one command that runs them: python -I gates.py
Two gates, both before any deploy; refresh.py runs the same list. Add a check HERE and nowhere else. Cheap and offline first.
  1 it builds   the page builds, the page rules hold (Source line, units, times, sizes, structured data, sitemap, secrets), the edge worker bundles
  2 it is true  numbers on a page agree with each other, and with a fresh USGS and NWS fetch (writes _truth.json for the doctor)
Gates block only what would show a reader something wrong. Whatever can heal (a slow build, a dead feed, stale edge readings) is reported by
tools/watchdog.py at session start and never blocks a deploy. A post-deploy gate was deleted 2026-10-26: it could not block anything and
gate 2 already checks the same numbers before the deploy."""
import os, subprocess, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = [sys.executable, "-I"]
NPX = "npx.cmd" if os.name == "nt" else "npx"

def census(out):
    """CLAUDE.md links rule 7: the links census reaches every run's log, pass or fail (refresh.py and gates.py both call this)."""
    for ln in out.splitlines():
        if ln.startswith(("links census", "readability census", "doorway census", "truth_live:", "truth_live air:", "truth_live forecast:", "truth_live rain:", "world truth:", "truth tests:", "truth_live WARNING", "WARNING", "CARRIED", "NEW PAGE FAILED", "NEW WORLD")) or " FAULT" in ln or "MISMATCH" in ln:  # what each truth check compared, pass or fail (practice 2026-11-08: Lake Michigan compared or skipped was unknowable)
            print("      " + ln[:200], flush=True)


GATE_1 = [("build", PY + ["build.py"]), ("page checks", PY + ["check.py", "--carry"]), ("page rules self-test", PY + ["check.py", "--selftest"]),
          ("break every input", PY + ["tools/break_blocks.py", "--gate"]),  # missing, stale, empty, duplicated data on 4 sample gauges (owner 2026-10-28)
          ("edge worker bundles", [NPX, "wrangler", "deploy", "--dry-run", "--outdir", ".wrangler/dry", "--assets", "dist_next"]),
          ("edge one-gauge read self-test", ["node", "tools/worker_slice_test.mjs"])]  # dist/ does not exist yet in CI at gate time
GATE_2 = [("truth fixtures", PY + ["tools/truth_fixtures.py"]), ("operator feed self-test", PY + ["tools/truth_live.py", "--selftest"]), ("info gain self-test", PY + ["tools/info_gain.py", "--selftest"]), ("truth contracts", PY + ["truth_tests.py"]), ("built pages vs USGS/NWS", PY + ["tools/truth_live.py", "--dir", "dist_next"]), ("world pages vs their agency", PY + ["tools/truth_world.py", "--dir", "dist_next"]), ("world truth self-test", PY + ["tools/truth_world.py", "--selftest"]), ("release failed self-test", PY + ["tools/release_failed.py", "--selftest"]), ("practice keep self-test", PY + ["tools/practice_keep.py", "--selftest"]), ("release rules self-test", PY + ["tools/check_rules.py", "--selftest"]), ("rollback self-test", PY + ["tools/rollback.py", "--selftest"])]
GATES = [("1 build and sources", GATE_1), ("2 numbers", GATE_2)]


def run(cmd):
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    except subprocess.TimeoutExpired:
        return False, time.time() - t0, "timed out after 30 min", "timed out"
    last = ((p.stdout.strip().splitlines() or p.stderr.strip().splitlines() or [""])[-1])[:100]
    return p.returncode == 0, time.time() - t0, last, p.stdout + p.stderr


if __name__ == "__main__":
    bad, details = [], []
    for gname, checks in GATES:
        results = []
        for name, cmd in checks:
            ok, secs, last, out = run(cmd)
            results.append((name, ok, secs, last))
            census(out)
            if not ok:
                details.append("--- %s / %s ---\n%s" % (gname, name, "\n".join(out.strip().splitlines()[-20:])))
        ok_all = all(r[1] for r in results)
        print("%s  gate %-20s %d/%d checks  %4.0fs" % ("PASS" if ok_all else "FAIL", gname, sum(r[1] for r in results), len(results), sum(r[2] for r in results)), flush=True)
        for name, ok, secs, last in results:
            print("      %s %-34s %s" % ("ok  " if ok else "FAIL", name, last if not ok else ""))
        if not ok_all:
            bad.append(gname)
    print("\n%d gates, %d failed%s" % (len(GATES), len(bad), (": " + ", ".join(bad)) if bad else ""))
    for d in details:
        print("\n" + d)
    sys.exit(1 if bad else 0)
