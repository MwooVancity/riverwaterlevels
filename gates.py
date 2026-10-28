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

GATE_1 = [("build", PY + ["build.py"]), ("page checks", PY + ["check.py"]), ("page rules self-test", PY + ["check.py", "--selftest"]),
          ("edge worker bundles", [NPX, "wrangler", "deploy", "--dry-run", "--outdir", ".wrangler/dry", "--assets", "dist_next"])]  # dist/ does not exist yet in CI at gate time
GATE_2 = [("truth contracts", PY + ["truth_tests.py"]), ("built pages vs USGS/NWS", PY + ["tools/truth_live.py", "--dir", "dist_next"])]
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
