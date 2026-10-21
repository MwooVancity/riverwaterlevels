"""ONE command for every gate: python -I gate.py [--quick] [--live]
Rebuilds dist_next, runs the SIX gates in gates.py, prints one table (a gate fails if any check in it fails) and exits 1 if any gate failed.
 --quick  skips the slow fuzzer
 --live   also runs the post-deploy checks against the live site (network): live pages vs the sources, indexing state, the watchdog"""
import os, subprocess, sys, time
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)  # python -I leaves the script folder off the path
import gates

quick, live = "--quick" in sys.argv, "--live" in sys.argv


def run(cmd):
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    except subprocess.TimeoutExpired:
        return False, time.time() - t0, "timed out after 30 min", "timed out"
    last = ((p.stdout.strip().splitlines() or p.stderr.strip().splitlines() or [""])[-1])[:100]
    return p.returncode == 0, time.time() - t0, last, p.stdout + p.stderr


groups = [("0 build", [("build", gates.PY + ["build.py"]), ("page checks", gates.PY + ["check.py"])])] + gates.GATES + (gates.GATES_LIVE if live else [])
bad, details = [], []
for gname, checks in groups:
    results = []
    for name, cmd in checks:
        if quick and "fuzz" in name:
            continue
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
print("\n%d gates, %d failed%s" % (len(groups), len(bad), (": " + ", ".join(bad)) if bad else ""))
for d in details:
    print("\n" + d)
sys.exit(1 if bad else 0)
