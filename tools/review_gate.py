"""PreToolUse hook (owner 2026-11-14: "I don't want to ship nonperfect pages"): a git push is refused while code changed since the last bug review.
The review is /code-review medium on <last>..HEAD; after its findings are fixed, HEAD is written to data/last-review. Exit 2 = blocked (Claude Code reads stderr).
Only pushes are judged; any other command passes. A missing or unreadable mark blocks (fail closed), naming how to set it."""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARK = os.path.join(ROOT, "data", "last-review")  # committed, so the cloud promote reads the same record (--ci): a push from any machine is judged
CODE = ("*.py", "*.js", "*.yml", "*.yaml", "*.html", "*.css", "*.sh", "*.toml", "data/sources.json", "data/state-rules.json")  # code, plus the rule files that switch reader blocks on or off


def git(*a):
    return subprocess.run(("git",) + a, cwd=ROOT, capture_output=True, text=True)


def verdict(cmd, mark):
    """None = allow, else the reason to block."""
    bare = re.sub(r"(?s)(-m|--message|-F)\s+('[^']*'|\"(?:[^\"\\]|\\.)*\")", r"\1 ''", cmd)  # a commit message naming a push is not a command; other quoted text (bash -c "git push") is still read
    if not re.search(r"(?:^|[;&|(\s'\"])git\s+(?:-\S+\s+(?:[^-\s]\S*\s+)?)*push\b", bare):
        return None
    if not mark:
        return "No bug review mark (data/last-review). Run /code-review medium on the unpushed commits, fix the findings, then write HEAD to data/last-review."
    r = git("diff", "--name-only", mark, "HEAD", "--", *CODE)
    if r.returncode != 0:
        return "The bug review mark %s is not a commit here (%s). Review again and write HEAD to data/last-review." % (mark, r.stderr.strip()[:120])
    files = [f for f in r.stdout.split() if f]
    if files:
        return ("Code changed since the last bug review (%s): %s. Run /code-review medium on %s..HEAD, fix the findings, then write HEAD to data/last-review."
                % (mark[:7], ", ".join(files[:8]) + (" and %d more" % (len(files) - 8) if len(files) > 8 else ""), mark[:7]))
    return None


def main(ci=False):
    if ci:  # dryrun.yml promote: the commit about to go live is judged as a push
        cmd = "git push"
    else:
        try:
            cmd = (json.load(sys.stdin).get("tool_input") or {}).get("command") or ""
        except ValueError:
            return 0
    try:
        mark = open(MARK, encoding="utf-8").read().strip()
    except OSError:
        mark = ""
    why = verdict(cmd, mark)
    if why:
        print(why, file=sys.stderr)
        return 2
    return 0


def selftest():
    head = git("rev-parse", "HEAD").stdout.strip()
    assert verdict("git status", "") is None, "a non-push command was judged"
    assert verdict("git push -q origin check", head) is None, "a push with no code change since the review was blocked"
    assert verdict("git push -q origin check", "") and verdict("git push", "nope") , "a push with no mark, or a bad mark, passed"
    first = git("rev-list", "--max-parents=0", "HEAD").stdout.split()[0]
    assert verdict("cd x; git push origin check", first) and verdict("git -C . push", first) and verdict("a && git push", first), "a push with code changed since an old review passed"
    assert verdict('bash -c "git push -q origin check"', first) and verdict("powershell -Command 'git push'", first), "a push inside a quoted command string passed"
    assert verdict('git commit -m "a git push is refused"', first) is None and verdict("git commit -m 'git push gate'", first) is None, "a commit message naming a push was blocked as a push"
    print("review_gate selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        sys.exit(main("--ci" in sys.argv))
