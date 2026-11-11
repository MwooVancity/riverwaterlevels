"""Stop hook (owner 2026-11-11 "why didn't it catch site fuckups ... improve it"): check runs stay green by rule (no red runs, no emails),
so on 2026-11-11 a failing gate and then a check/main conflict kept 27 commits off the live site all day while sessions reported done.
This blocks a session's stop while check holds code main lacks and the newest finished check run says why, quoting its stop lines.

Edge cases: gh missing, offline or not signed in -> passes (a hook fault never blocks); a run still building -> passes (its verdict is not
known; the next stop re-checks); already blocked once this reply (stop_hook_active) -> passes, never a loop; check equal to main -> passes
with one API call. Cost per stop: one API call, plus one log download only while check is ahead.
python -I tools/deploy_gate.py            (reads the hook JSON on stdin)
python -I tools/deploy_gate.py --selftest
"""
import json, re, subprocess, sys


def gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90).stdout


def verdict(log):
    """('ok'|'conflict'|'failed', stop lines) from a dryrun log."""
    lines = [re.sub(r"^.*?Z ", "", ln).strip() for ln in log.splitlines()]
    lines = [ln for ln in lines if "36;1m" not in ln]
    if any(ln.startswith("promoted ") for ln in lines):
        return "ok", []
    if any(ln.startswith("refresh OK") for ln in lines):
        return "conflict", [ln for ln in lines if ln.startswith(("promote skipped", "PROMOTE FAILED"))][-2:]
    keep = [ln[:200] for ln in lines if re.match(r"(STOPPED|SITE FAIL|FAIL |refresh FAILED|\d+ gauges \| |[A-Za-z]*Error:)", ln)]
    return "failed", keep[-8:]


def reason(state, lines, ahead, run_id):
    head = "%d commit(s) on check are not on the live site (newest check run %s): " % (ahead, run_id)
    if state == "conflict":
        return head + "gates passed but promotion to main hit a merge conflict. Merge origin/main into check (git fetch; git merge origin/main), resolve, push. " + " | ".join(lines)
    return head + "its gates failed, so nothing deploys. Fix the cause and push before stopping: " + " | ".join(lines)


def main(raw):
    inp = json.loads(raw or "{}")
    if inp.get("stop_hook_active"):
        return
    ahead = int(gh("api", "repos/{owner}/{repo}/compare/main...check", "-q", ".ahead_by").strip() or 0)
    if not ahead:
        return
    run = json.loads(gh("run", "list", "--workflow", "dryrun.yml", "--event", "push", "--limit", "1", "--json", "databaseId,status") or "[]")
    if not run or run[0]["status"] != "completed":
        return
    state, lines = verdict(gh("run", "view", str(run[0]["databaseId"]), "--log"))
    if state != "ok":
        print(json.dumps({"decision": "block", "reason": reason(state, lines, ahead, run[0]["databaseId"])}))


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        z = "dryrun\tstep\t2026-11-11T16:27:26.5Z "
        assert verdict(z + "refresh OK\n" + z + "promoted abc to main; refresh started")[0] == "ok"
        s, ln = verdict(z + "refresh OK\n" + z + "promote skipped: check and main conflict, a session merges")
        assert s == "conflict" and ln == ["promote skipped: check and main conflict, a session merges"], (s, ln)
        s, ln = verdict(z + " 1 gauges | (unbroken page) none | title 'x' does not match\n" + z + "STOPPED at -I tools/break_blocks.py\n" + z + "refresh FAILED (see runs/refresh.log)\n" + z + "\x1b[36;1mif ! grep -q \"refresh OK\"")
        assert s == "failed" and ln[-1] == "refresh FAILED (see runs/refresh.log)" and len(ln) == 3, (s, ln)
        assert "merge conflict" in reason("conflict", [], 27, 1) and "gates failed" in reason("failed", ["STOPPED"], 1, 2)
        print("deploy_gate selftest OK")
    else:
        try:
            main(sys.stdin.read())
        except Exception:
            pass  # a hook fault never blocks a stop
