"""Run-time ledger (machinery audit 2026-11-04): every stage of every cloud run appends its seconds and the page count; build.py puts the report in
status.json and tools/watchdog.py alarms when a stage would pass its limit within 30 days of growth. Nothing here guesses: it is the clock, per run.
ponytail: linear in pages, so fixed costs (wrangler deploy) project high; that only makes the alarm early, never late."""
import datetime, json, os

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache", "_ledger.jsonl")
LIMIT_S = {"shard collect": 45 * 60, "shard 0 collect": 45 * 60, "release": 30 * 60}  # a shard job dies at 60 min; the release shares the 45-min brake with the refresh
DEFAULT_S = 45 * 60  # any other stage: the 45-min brake
GROWTH = 25 * 30  # pages added in 30 days at the daily 25
KEEP = 4000  # lines: ~24 runs x ~8 stages a day = 90 days at most


def add(stage, seconds, pages, path=PATH):
    """One line per stage per run. A missing or full file never fails a run."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "stage": stage, "s": round(seconds, 1), "n": int(pages or 0)}) + "\n")
        lines = open(path, encoding="utf-8").read().splitlines()
        if len(lines) > KEEP:
            open(path, "w", encoding="utf-8").write("\n".join(lines[-KEEP:]) + "\n")
    except OSError as e:
        print("ledger: not written (%s)" % e)


def report(path=PATH, now=None, hours=24):
    """Per stage over the last day: slowest run, its seconds per page, and the page count where it passes its limit. "soon" names stages that break within GROWTH pages."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    worst = {}
    try:
        for l in open(path, encoding="utf-8"):
            try:
                r = json.loads(l)
                if r["n"] > 0 and (now - datetime.datetime.fromisoformat(r["at"])).total_seconds() < hours * 3600 and r["s"] > worst.get(r["stage"], {}).get("s", -1):
                    worst[r["stage"]] = r
            except (ValueError, KeyError):
                continue
    except OSError:
        return {"stages": {}, "soon": [], "unread": True}
    out, soon = {}, []
    for st, r in sorted(worst.items()):
        lim = LIMIT_S.get(st, DEFAULT_S)
        breaks = int(lim / (r["s"] / r["n"])) if r["s"] > 0 else None
        out[st] = {"s": r["s"], "pages": r["n"], "limit_s": lim, "breaks_at_pages": breaks}
        if breaks is not None and breaks < r["n"] + GROWTH:
            soon.append("%s: %d s at %d pages, passes %d min near %d pages" % (st, r["s"], r["n"], lim // 60, breaks))
    return {"stages": out, "soon": soon}


def last_run_s(path=PATH):
    """The release brake (audit 2026-11-10 #40): seconds of the newest refresh, its "refresh total" plus the "shard collect" logged before it,
    from one run, not the worst of each in 24 h. None when either line is missing (lost cache, unreadable file): the brake then holds the release."""
    rows = []
    try:
        for l in open(path, encoding="utf-8"):
            try:
                rows.append(json.loads(l))
            except ValueError:
                continue
    except OSError:
        return None
    i = next((k for k in range(len(rows) - 1, -1, -1) if rows[k].get("stage") == "refresh total"), None)
    sh = next((r for r in reversed(rows[:i]) if r.get("stage") == "shard collect"), None) if i is not None else None
    return rows[i]["s"] + sh["s"] if sh else None


if __name__ == "__main__" and "--last-run-min" in __import__("sys").argv:  # sharded.yml release brake: minutes, or nothing when unknown
    s_ = last_run_s()
    print("" if s_ is None else int(s_ // 60))
elif __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "l.jsonl")
        assert report(p)["unread"], "a missing ledger read as fine"
        add("build", 60, 200, p)
        add("shard collect", 2000, 200, p)
        add("build", 30, 200, p)
        r = report(p)
        assert r["stages"]["build"]["s"] == 60 and r["stages"]["build"]["breaks_at_pages"] == 9000, r
        assert len(r["soon"]) == 1 and r["soon"][0].startswith("shard collect"), "a shard at 2,000 s of 2,700 with 750 pages of growth ahead was not named: %s" % r["soon"]
        old = report(p, now=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=2))
        assert not old["stages"], "runs older than a day still decide"
        assert last_run_s(p) is None, "no refresh total yet, but the brake got a number"
        add("refresh total", 900, 200, p)
        add("shard collect", 100, 200, p)
        add("refresh total", 300, 200, p)
        assert last_run_s(p) == 400, "the brake did not read the newest run (300 s) plus its shard collect (100 s): %s" % last_run_s(p)
        assert last_run_s(os.path.join(d, "none.jsonl")) is None, "a missing ledger read as a fast run"
    print("ledger selftest OK")
