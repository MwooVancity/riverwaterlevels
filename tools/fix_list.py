"""What is held back and why, biggest cause first: the daily job's fix list (owner 2026-11-15: "I don't want a page ever blocked. We need to make sure shit gets fixed").
A hold is only allowed while this list names it; the daily session job fixes the top cause the same day.

python -I tools/fix_list.py        -> one line per cause: count, cause, three example gauges
python -I tools/fix_list.py --selftest

After a cause is fixed in code, add "date<TAB>cause" (the cause as printed here) to data/fixed-causes.txt: releases pick those gauges again for 3 days (tools/release.py open_gate).
Causes read: queue gauges carrying a gate in data/waves.csv (a page or truth check sent them back), kinds Google is declining
(tools/open_wave.py held_kinds), and single pages Google crawled and declined (data/index-inspect.json). A 'retry after' gate heals by itself
the next day and is not listed; a feed with no readings ('no-usgs-rows') is listed apart, since only the agency can fix it.
"""
import collections, csv, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))


def cause(gate):
    """A gate message reduced to its cause: numbers, urls and quoted text out, so 30 pages with one bug read as one line."""
    g = re.sub(r"https?://\S+", "<url>", gate or "")
    g = re.sub(r"'[^']*'|\"[^\"]*\"", "'...'", g)
    g = re.sub(r"\d+(\.\d+)?", "N", g)
    return g.split(" near ")[0][:90].strip()


BUG = ("page-check:", "truth:", "site-check:")  # a check sent the page back: code or data to fix; any other gate is a decision (wrong state, tiny basin, queue audit) and stays


def tally(rows):
    """{cause: [sites]} for queue gauges held by a gate, retry-after gates left out (they return tomorrow by themselves)."""
    out = collections.defaultdict(list)
    for r in rows:
        g = r.get("gate") or ""
        if r.get("status") == "queue" and g.startswith(BUG):
            out[cause(g)].append(r["site"])
    return out


def main():
    import subprocess
    subprocess.run(["git", "fetch", "-q", "origin", "main"], cwd=ROOT, capture_output=True)
    r_ = subprocess.run(["git", "show", "origin/main:data/waves.csv"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")  # the cloud release writes it; the laptop copy is stale
    rows = list(csv.DictReader(r_.stdout.splitlines() if r_.returncode == 0 else open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8")))
    t = tally(rows)
    import open_wave
    held = open_wave.held_now()
    st = open_wave.load(os.path.join(ROOT, "data", "index-inspect.json"), {})
    declined = sorted(u for u, v in st.items() if str((v or {}).get("state") or "").startswith("Crawled"))
    lines = sorted(((len(s), c, s[:3]) for c, s in t.items()), reverse=True)
    for k, (d, j) in sorted(held.items()):
        print("FIX FIRST  kind %s: Google declined %d of %d judged pages" % (k, d, j))
    for n, c, ex in lines:
        print("%4d  %s  (e.g. %s)" % (n, c, ", ".join(ex)))
    if declined:
        print("%4d  Google crawled and declined: %s" % (len(declined), ", ".join(u.replace("https://riverwaterlevels.com", "") for u in declined[:5])))
    if not (lines or held or declined):
        print("nothing held")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        R = [{"site": "a", "status": "queue", "gate": "page-check: info gain: missing tide chart that https://x.com/1 shows"},
             {"site": "b", "status": "queue", "gate": "page-check: info gain: missing tide chart that https://x.com/2 shows"},
             {"site": "c", "status": "queue", "gate": "retry after 2026-11-14: x"}, {"site": "d", "status": "live", "gate": ""},
             {"site": "e", "status": "queue", "gate": "page-check: doubled word 'on on' near 'x'"}, {"site": "f", "status": "queue", "gate": "foreign-or-wrong-state"}]
        t = tally(R)
        assert t == {"page-check: info gain: missing tide chart that <url> shows": ["a", "b"], "page-check: doubled word '...'": ["e"]}, "fix list: one bug counted twice, a self-healing gate or a decision hold listed, or a live page listed (%s)" % dict(t)
        print("selftest OK")
    else:
        main()
