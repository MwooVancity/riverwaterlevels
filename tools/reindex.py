"""Google 'Request indexing' queue for the daily scheduled task (PLAN 0h). One writer per file:
  data/reindex-queue.txt  the backlog of 2026-11-09 (never edited again)
  data/reindex-new.txt    pages each daily release opened (written only by refresh.yml, via --queue)
  data/reindex-done.txt   "url<TAB>date" per request Google confirmed (written only by the scheduled task, via done)
The task reads main's copies (git fetch origin main), so a stale laptop checkout never repeats or skips pages.

python -I tools/reindex.py next 10        -> the next URLs to request, newest release pages first
python -I tools/reindex.py done <url>...  -> record confirmed requests
python -I tools/reindex.py --queue        -> (release) append the pages this release adds to the allow list
python -I tools/reindex.py age            -> days since the last confirmed request (session-start line)
"""
import datetime, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://riverwaterlevels.com"
F = {k: os.path.join(ROOT, "data", "reindex-%s.txt" % k) for k in ("queue", "new", "done")}


def main_copy(name):
    """Lines of a data file as main has it (the bot's latest), falling back to the local file when git cannot answer."""
    subprocess.run(["git", "fetch", "-q", "origin", "main"], cwd=ROOT, capture_output=True)
    r = subprocess.run(["git", "show", "origin/main:data/reindex-%s.txt" % name], cwd=ROOT, capture_output=True, text=True)
    text = r.stdout if r.returncode == 0 else (open(F[name], encoding="utf-8").read() if os.path.exists(F[name]) else "")
    return [l.strip() for l in text.splitlines() if l.strip()]


def pick(queue, new, done, n):
    """New release pages first (newest last in the file, so reversed), then the backlog; never a URL already confirmed or twice."""
    seen, out = {d.split("\t")[0] for d in done}, []
    for u in list(reversed(new)) + queue:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out[:n]


def local_done():
    return [l.strip() for l in open(F["done"], encoding="utf-8")] if os.path.exists(F["done"]) else []


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["--selftest"]:
        assert pick(["https://x/a/", "https://x/b/"], ["https://x/n1/", "https://x/n2/"], ["https://x/a/\t2026-11-10"], 3) == ["https://x/n2/", "https://x/n1/", "https://x/b/"], "reindex: new pages not first, a done page repeated, or the backlog lost"
        print("selftest OK")
    elif a[:1] == ["next"]:
        print("\n".join(pick(main_copy("queue"), main_copy("new"), main_copy("done") + local_done(), int(a[1]) if a[1:] else 10)))
    elif a[:1] == ["done"]:
        with open(F["done"], "a", encoding="utf-8") as f:
            for u in a[1:]:
                f.write("%s\t%s\n" % (u, datetime.date.today().isoformat()))
        print("recorded", len(a) - 1)
    elif a == ["--queue"]:
        head = subprocess.run(["git", "show", "HEAD:data/index-allow.json"], cwd=ROOT, capture_output=True, text=True).stdout
        before = set((json.loads(head) if head.strip() else {}).get("allow") or [])
        now = set(json.load(open(os.path.join(ROOT, "data", "index-allow.json"), encoding="utf-8")).get("allow") or [])
        add = sorted(now - before)
        with open(F["new"], "a", encoding="utf-8") as f:
            for u in add:
                f.write(SITE + u + "\n")
        print("reindex queue: %d new pages" % len(add))
    elif a == ["age"]:
        ds = [l.split("\t")[1] for l in main_copy("done") + local_done() if "\t" in l]
        print((datetime.date.today() - datetime.date.fromisoformat(max(ds))).days if ds else -1)
