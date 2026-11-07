"""Nightly practice release (owner 2026-11-07: "build the infrastructure so we have no GitHub issues publishing"). After the practice run of
tomorrow's picks (release.py page_check and truth_check, the full gates, quarantine.py), keep ONLY the gates it wrote on picks that failed,
so the real 11:00 release never meets them; every other change of the practice (pages marked live, Google allow list) is dropped.
Reads the committed data/waves.csv (git HEAD) and the practice's working copy; writes HEAD's rows plus the new gates. Prints what it kept.
Usage: python -I tools/practice_keep.py     Self-test: --selftest"""
import csv, io, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def keep(head_text, work_text, today):
    """(csv text, [(site, gate)]): HEAD rows, with a gate added only where HEAD had none and the practice left the row queued and gated."""
    work = {r["site"]: r for r in csv.DictReader(io.StringIO(work_text))}
    rows = list(csv.DictReader(io.StringIO(head_text)))
    kept = []
    for r in rows:
        w = work.get(r["site"])
        if w and r["status"] == "queue" and not r["gate"] and w["status"] == "queue" and w["gate"]:
            r["gate"] = ("retry after %s: practice: %s" % (today, w["gate"]))[:300]  # expires: tomorrow's practice tests it again (an outage heals by itself; a real defect is sent back again)
            kept.append((r["site"], r["gate"]))
    out = io.StringIO()
    wr = csv.DictWriter(out, fieldnames=list(rows[0].keys()), lineterminator="\n")
    wr.writeheader()
    wr.writerows(rows)
    return out.getvalue(), kept


def main():
    p = os.path.join(ROOT, "data", "waves.csv")
    head = subprocess.check_output(["git", "show", "HEAD:data/waves.csv"], cwd=ROOT, text=True, encoding="utf-8")
    import datetime
    text, kept = keep(head, open(p, encoding="utf-8").read(), datetime.datetime.now(datetime.timezone.utc).date().isoformat())
    subprocess.call(["git", "checkout", "--", "data/", "legacy/"], cwd=ROOT)  # every other practice change goes
    subprocess.call(["git", "clean", "-fdq", "legacy/"], cwd=ROOT)
    open(p, "w", encoding="utf-8", newline="").write(text)
    print("practice: %d pick(s) sent back before the release" % len(kept))
    for s, g in kept:
        print("  ", s, g)


def selftest():
    h = "status,site,gate\nqueue,A,\nqueue,B,\nqueue,C,old\nlive,D,\n"
    w = "status,site,gate\nqueue,A,page-check: x\nlive,B,\nqueue,C,new\nlive,D,\n"
    t, k = keep(h, w, "2026-11-08")
    assert k == [("A", "retry after 2026-11-08: practice: page-check: x")] and "queue,B,\n" in t and "queue,C,old" in t and "live,D," in t, (t, k)
    print("practice_keep selftest OK")


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main()
