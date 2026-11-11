"""Google 'Request indexing' queue for the daily scheduled task (PLAN 0h). One writer per file:
  data/reindex-queue.txt  the backlog of 2026-11-09 (never edited again)
  data/reindex-new.txt    pages each daily release opened (written only by refresh.yml, via --queue)
  data/reindex-done.txt   "url<TAB>date" per request Google confirmed (written only by the scheduled task, via done)
  data/index-inspect.json Google's last URL Inspection answer per page (written only by tools/index_inspect.py; read here for the order)
The task reads main's copies (git fetch origin main), so a stale laptop checkout never repeats or skips pages.

python -I tools/reindex.py next 10        -> the next URLs to request: 'Excluded by noindex' first, then not indexed, then never inspected; newest release pages first within each
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


def rank(state):
    """Request order by Google's last URL Inspection answer (data/index-inspect.json, tools/index_inspect.py; audit 2026-11-10 #19):
    0 'Excluded by noindex' (the pre-launch header crawl of 10-17; the page is open now), 1 discovered or crawled, not indexed, 2 never inspected or no answer,
    3 any other state (redirect, duplicate, ...); None = indexed, no request needed."""
    s = (state or "").lower()
    return 0 if "noindex" in s else 1 if "not indexed" in s else 2 if not s or s.startswith("no answer") else None if "indexed" in s else 3


def pick(queue, new, done, n, seen_state=None):
    """New release pages, then the backlog, then every other page the inspection found not indexed; ordered by rank (stable, so new pages lead
    within a rank); never a URL already confirmed, twice, or one Google already indexed."""
    st = seen_state or {}
    seen, out = {d.split("\t")[0] for d in done}, []
    for u in list(reversed(new)) + queue + sorted(st):
        if u not in seen and rank((st.get(u) or {}).get("state")) is not None:
            seen.add(u)
            out.append(u)
    return sorted(out, key=lambda u: rank((st.get(u) or {}).get("state")))[:n]


def inspected():
    """{url: {state, date}} as main has it, else the local file; {} when neither can be read (the old order then)."""
    subprocess.run(["git", "fetch", "-q", "origin", "main"], cwd=ROOT, capture_output=True)
    r = subprocess.run(["git", "show", "origin/main:data/index-inspect.json"], cwd=ROOT, capture_output=True, text=True)
    p = os.path.join(ROOT, "data", "index-inspect.json")
    try:
        return json.loads(r.stdout) if r.returncode == 0 else json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def local_done():
    return [l.strip() for l in open(F["done"], encoding="utf-8")] if os.path.exists(F["done"]) else []


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["--selftest"]:
        assert pick(["https://x/a/", "https://x/b/"], ["https://x/n1/", "https://x/n2/"], ["https://x/a/\t2026-11-10"], 3) == ["https://x/n2/", "https://x/n1/", "https://x/b/"], "reindex: new pages not first, a done page repeated, or the backlog lost"
        S = {"https://x/b/": {"state": "Excluded by ‘noindex’ tag"}, "https://x/n1/": {"state": "Submitted and indexed"}, "https://x/z/": {"state": "Crawled - currently not indexed"}, "https://x/y/": {"state": "Indexed, not submitted in sitemap"}}
        assert pick(["https://x/a/", "https://x/b/"], ["https://x/n1/", "https://x/n2/"], [], 5, S) == ["https://x/b/", "https://x/z/", "https://x/n2/", "https://x/a/"], "reindex: noindex pages not first, an indexed page requested, or a not-indexed page outside the queue missed"
        print("selftest OK")
    elif a[:1] == ["next"]:
        print("\n".join(pick(main_copy("queue"), main_copy("new"), main_copy("done") + local_done(), int(a[1]) if a[1:] else 10, inspected())))
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
