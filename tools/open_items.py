"""Session-start hook (PLAN 16, unattended): open PLAN.md Next steps (same rule as ~/.claude/hooks/plan-gate.mjs) and whether the daily release is still running.
A stall shows here the first time anyone opens a session, with its age; nothing is fetched (data/last-success.txt is committed by the release)."""
import datetime, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINISHED = re.compile(r"^(DONE|LIVE|CLOSED|DECIDED|WAITING|OWNER)\b")  # same markers as ~/.claude/hooks/plan-gate.mjs


def open_steps(txt):
    m = re.search(r"^## Next\b[^\n]*\n(.*?)(?=^## |\Z)", txt, re.M | re.S)
    return [x for x in re.findall(r"^(\d+[a-z]?\. .{0,80})", m.group(1) if m else "", re.M) if not FINISHED.match(x.split(". ", 1)[1])]


def release_line(today, last):
    if not last:
        return "release: never recorded (data/last-success.txt missing)"
    days = (today - datetime.date.fromisoformat(last)).days
    return "release: last new pages %s (%d days ago)%s" % (last, days, " STALLED: read the refresh log" if days >= 2 else "")


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["--selftest"]:
        t = "## Next steps\n0a. DONE x\n1. Open y\n2. DECIDED z\n## Owner only\n3. no\n"
        assert [s.split(".")[0] for s in open_steps(t)] == ["1"], "open_items: a finished item counted as open, or an owner item counted"
        assert "STALLED" in release_line(datetime.date(2026, 11, 9), "2026-11-07") and "STALLED" not in release_line(datetime.date(2026, 11, 9), "2026-11-08"), "open_items: a 2-day stall not shown, or a 1-day gap shown as one"
        print("selftest OK")
    else:
        steps = open_steps(open(os.path.join(ROOT, "PLAN.md"), encoding="utf-8").read())
        lp = os.path.join(ROOT, "data", "last-success.txt")
        last = open(lp, encoding="utf-8").read().strip() if os.path.exists(lp) else ""
        import subprocess
        age = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools", "reindex.py"), "age"], capture_output=True, text=True).stdout.strip()
        ri = "Request-indexing job: never ran" if age in ("", "-1") else "Request-indexing job: last %s day(s) ago%s" % (age, " STALLED: open Chrome and the Claude app, or run the task by hand" if age.isdigit() and int(age) >= 2 else "")
        print("RIVER PLAN: %d open next steps. %s. %s. First: %s" % (len(steps), release_line(datetime.date.today(), last), ri, " | ".join(steps[:3])))
