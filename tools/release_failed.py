"""After a release whose refresh did not pass even on the second try (readiness debate 2026-11-07: Nov 6 retried the same 25 picks five times,
Nov 7 three times, each try spending the USGS hourly budget): today's picks get gate 'retry after <today>: ...', so tomorrow's release takes them
again by itself (tools/release.py open_gate), and data/last-release.txt says today is done. Run on the committed data/waves.csv (the workflow
undoes the release first). Exit 0 always: it only records; the workflow commits.
Usage: python -I tools/release_failed.py [reason]    Self-test: --selftest"""
import csv, datetime, io, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def gate(text, picks, today, reason):
    rows = list(csv.DictReader(io.StringIO(text)))
    n = 0
    for r in rows:
        if r["site"] in picks and r["status"] == "queue" and not r["gate"]:
            r["gate"], n = ("retry after %s: %s" % (today, reason))[:300], n + 1
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=list(rows[0].keys()), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return out.getvalue(), n


def main():
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    reason = " ".join(a for a in sys.argv[1:]) or "release undone, the refresh did not pass"
    try:
        picks = {l.strip() for l in open(os.path.join(ROOT, "state", "release-picks.txt")) if l.strip()}
    except OSError:
        picks = set()
    p = os.path.join(ROOT, "data", "waves.csv")
    text, n = gate(open(p, encoding="utf-8", newline="").read(), picks, today, reason)
    open(p, "w", encoding="utf-8", newline="").write(text)
    open(os.path.join(ROOT, "data", "last-release.txt"), "w").write(today + "\n")
    print("release_failed: %d pick(s) wait until after %s; today marked released" % (n, today))


def selftest():
    t = "status,site,gate\nqueue,A,\nqueue,B,old gate\nlive,C,\nqueue,D,\n"
    out, n = gate(t, {"A", "B", "C"}, "2026-11-07", "x")
    assert n == 1 and "queue,A,retry after 2026-11-07: x" in out and "queue,B,old gate" in out and "live,C," in out and "queue,D,\n" in out, out
    g = lambda s, today: not s or (s.startswith("retry after ") and s[12:22] < today)  # the rule release.py uses
    assert not g("retry after 2026-11-07: x", "2026-11-07") and g("retry after 2026-11-07: x", "2026-11-08") and not g("page-check: y", "2026-11-08")
    print("release_failed selftest OK")


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main()
