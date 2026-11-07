"""Self-heal for our own code (owner 2026-11-07: "I don't think we have a self healing if GitHub fails"). When a code change makes every refresh
fail the same way (2026-11-07: the Shasta contract, the deleted-new-page bug), the site stays on its last good build and stops updating until a
person fixes the code. This restores the code files to the version the live site was built from (status.json "sha"), keeps every data file,
commits why, and asks for a refresh. Run hourly by watchdog.yml.
Rolls back only when ALL hold:
- the live build is over STALE_H hours old (refresh is failing, not just slow);
- the newest main commit differs from the live build's commit AND changed code (data-only commits, such as a daily release, never trigger it);
- GitHub really ran: at least MIN_RUNS refresh runs started after that commit (a GitHub outage runs nothing, so it never triggers);
- the newest commit is not already a rollback (one rollback, then a person: never a loop).
Usage: python -I tools/rollback.py [--apply]   (without --apply: prints the decision only).  Self-test: --selftest"""
import datetime, json, os, subprocess, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STALE_H, MIN_RUNS = 3, 2
CODE = ("*.py", "lib/", "tools/", "worker/", "templates/", ".github/", "package.json", "package-lock.json", "wrangler.toml", "wrangler.jsonc")


def decide(age_h, head, ok_sha, code_changed, runs_after, head_msg):
    """('rollback', why) or ('no', why)."""
    if not ok_sha:
        return "no", "the live build records no commit (older build)"
    if age_h is None or age_h < STALE_H:
        return "no", "live build %s h old: healthy" % (None if age_h is None else round(age_h, 1))
    if head == ok_sha or head.startswith(ok_sha) or ok_sha.startswith(head):
        return "no", "the live build is the newest commit: the failure is not new code (a feed or GitHub); the watchdog report names it"
    if head_msg.startswith("rollback:"):
        return "no", "already rolled back once and still failing: needs a person"
    if not code_changed:
        return "no", "commits since the live build changed data only"
    if runs_after < MIN_RUNS:
        return "no", "only %d refresh run(s) since the new code: wait (GitHub may be down)" % runs_after
    return "rollback", "live build %.1f h old, %d refresh runs since the new code, none deployed" % (age_h, runs_after)


def git(*a):
    return subprocess.check_output(["git"] + list(a), cwd=ROOT, text=True, encoding="utf-8").strip()


def main():
    st = json.loads(urllib.request.urlopen(urllib.request.Request("https://riverwaterlevels.com/status.json", headers={"User-Agent": "riverwaterlevels.com rollback"}), timeout=30).read())
    ok_sha = st.get("sha") or ""
    age_h = (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(st["built_at"])).total_seconds() / 3600
    head, head_msg, head_t = git("rev-parse", "HEAD"), git("log", "-1", "--format=%s"), git("log", "-1", "--format=%cI")
    changed = []
    if ok_sha:
        try:
            changed = [f for f in git("diff", "--name-only", ok_sha, "HEAD", "--", *CODE).splitlines() if f]
        except subprocess.CalledProcessError:
            changed = []
    runs_after = 0
    try:  # one API call an hour
        rs = json.loads(subprocess.check_output(["gh", "run", "list", "--workflow", "refresh.yml", "-L", "10", "--json", "createdAt"], cwd=ROOT, text=True))
        runs_after = sum(1 for r in rs if r["createdAt"] > datetime.datetime.fromisoformat(head_t).astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    except Exception as e:
        print("rollback: cannot read GitHub runs (%s): no decision" % str(e)[:60])
        return 0
    act, why = decide(age_h, head, ok_sha, bool(changed), runs_after, head_msg)
    print("rollback: %s: %s" % (act, why))
    if act != "rollback" or "--apply" not in sys.argv:
        return 0
    gone = [f for f in changed if subprocess.call(["git", "cat-file", "-e", "%s:%s" % (ok_sha, f)], cwd=ROOT, stderr=subprocess.DEVNULL) != 0]
    keep = [f for f in changed if f not in gone]
    if keep:
        git("checkout", ok_sha, "--", *keep)
    if gone:
        git("rm", "-q", "--", *gone)
    git("add", "-A", "--", *changed)
    git("-c", "user.name=riverwaterlevels-bot", "-c", "user.email=actions@users.noreply.github.com", "commit", "-q", "-m",
        "rollback: %s; code restored to the live build %s (%d files: %s); data kept. A person re-applies the change with its fix." % (why, ok_sha[:7], len(changed), ", ".join(changed[:8])))
    git("pull", "--rebase", "--autostash", "-q", "origin", "main")
    git("push", "-q", "origin", "HEAD:main")
    print("rollback: committed and pushed; a refresh is dispatched by the watchdog")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        open(out, "a").write("rolled=1\n")
    return 0


def selftest():
    d = lambda **k: decide(**dict(dict(age_h=5, head="bbb", ok_sha="aaa", code_changed=True, runs_after=3, head_msg="fix x"), **k))[0]
    assert d() == "rollback", "a code change that failed 3 runs for 5 h was not rolled back"
    assert d(age_h=1) == "no" and d(head="aaa") == "no" and d(code_changed=False) == "no" and d(runs_after=1) == "no" and d(head_msg="rollback: x") == "no" and d(ok_sha="") == "no", "rolled back when it must not (healthy, same code, data only, GitHub not running, loop, no record)"
    print("rollback selftest OK")


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
