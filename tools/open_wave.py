"""Open the next batch of gauge pages to search engines, in priority order (data/waves.csv, highest score first).
Usage: python tools/open_wave.py 25            dry run: prints the next 25 gauge pages that are live and not yet allowed
       python tools/open_wave.py 25 --apply    writes them into data/index-allow.json and sets open true (site_pages stays as it is)
       python tools/open_wave.py --pull /river/x/y/ [...]   removes pages from the allow list (the kill switch for a batch)
Then run build.py, check.py and deploy. Search engines act on a change only when they recrawl, so release small batches and measure each one."""
import csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IX = os.path.join(ROOT, "data", "index-allow.json")


def load(p, default):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def held_kinds(states, kind_of, today, least=3, share=0.15, max_age=14):
    """Kinds of page Google is calling thin (owner 2026-11-15 "never push out thin pages again"): {kind: (declined, judged)} for each kind where
    Google's URL Inspection says 'Crawled - currently not indexed' for at least `least` pages and `share` of the pages it has judged (indexed or declined).
    Pages never crawled ('Discovered'), noindex-era pages and pages of unknown kind are not judged. States older than `max_age` days count for nothing
    (no file, or a stale one = no hold: the page checks still stand, and a pause on old news would stop growth for nothing). The fix is the page, never noindex."""
    import datetime
    old = (datetime.date.fromisoformat(today) - datetime.timedelta(days=max_age)).isoformat()
    tally = {}
    for u, v in (states or {}).items():
        k, st = kind_of.get(u.replace("https://riverwaterlevels.com", "")), str((v or {}).get("state") or "")
        if not k or str((v or {}).get("date") or "") < old:
            continue
        if st == "Submitted and indexed" or st.startswith("Crawled"):
            d, j = tally.get(k, (0, 0))
            tally[k] = (d + st.startswith("Crawled"), j + 1)
    return {k: dj for k, dj in tally.items() if dj[0] >= least and dj[0] >= share * dj[1]}


def kinds():
    """{url: kind} for every page a release can add: US gauges by template variant ('river', 'lake-usgs', 'coast-tables'...), world gauge pages by feed
    ('world-ea', 'world-eccc'...; data/world-pages.json slug = the first path part)."""
    from lib import pages as pages_
    out = {r["url"]: pages_.variant(r["site"], r["url"]) or "river" for r in csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8")) if r.get("url")}
    feed = {p["slug"]: "world-" + (p.get("feed") or "pegelonline") for p in load(os.path.join(ROOT, "data", "world-pages.json"), [])}
    return out, feed


def kind_of_url(u, us, feed):
    return us.get(u) or feed.get(u.strip("/").split("/")[0]) if u.count("/") == 3 else us.get(u)


def held_now():
    """The kinds held today (see held_kinds), from the committed Google states."""
    import datetime
    us, feed = kinds()
    st = load(os.path.join(ROOT, "data", "index-inspect.json"), {})
    return held_kinds(st, {u.replace("https://riverwaterlevels.com", ""): kind_of_url(u.replace("https://riverwaterlevels.com", ""), us, feed) for u in st}, datetime.date.today().isoformat())


def main():
    cfg = load(IX, {"open": False, "site_pages": False, "allow": []})
    if "--pull" in sys.argv:
        gone = [a for a in sys.argv[sys.argv.index("--pull") + 1:]]
        cfg["allow"] = [u for u in cfg["allow"] if u not in gone]
        cfg["pulled"] = sorted(set(cfg.get("pulled") or []) | {u for u in gone if not u.startswith(("/river/", "/lake/", "/coast/"))})  # a world page is not on the allow list: it is pulled by name
        json.dump(cfg, open(IX, "w", encoding="utf-8"), indent=1)
        print("pulled %d page(s); %d remain allowed. Deploy to take effect." % (len(gone), len(cfg["allow"])))
        return
    n = int(next((a for a in sys.argv[1:] if a.isdigit()), 25))
    pub = load(os.path.join(ROOT, "data", "publisher.json"), {})
    if "--apply" in sys.argv and "@" not in str(pub.get("email") or "") and not pub.get("waived"):
        sys.exit("refused: data/publisher.json has no contact email and no owner waiver. A page may not be indexed without a named publisher and a corrections contact unless the owner waives it in writing there (docs/RUNBOOK.md, precondition 6).")
    D = max((os.path.join(ROOT, x) for x in ("dist", "dist_next") if os.path.exists(os.path.join(ROOT, x, "_urls.json"))), key=lambda p: os.path.getmtime(os.path.join(p, "_urls.json")), default=os.path.join(ROOT, "dist"))
    live = set(load(os.path.join(D, "_urls.json"), {"urls": []})["urls"])
    have = set(cfg["allow"])
    pick = []
    skipped = {"gate": 0, "not reviewed": 0}
    unreviewed = []  # live lake and coast pages waiting for their screenshot review: the next session's to-do
    from lib import pages as pages_
    rv = pages_.reviewed(os.path.join(ROOT, "data", "reviewed.json"))  # urls and template variants that passed a phone review; a missing file opens no lake or coast
    rows_ = list(csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8")))
    kind_of = kinds()[0]
    held = held_now()
    for k_, (d_, j_) in sorted(held.items()):
        print("HELD KIND %s: Google declined %d of the %d pages it judged ('Crawled - currently not indexed'); no new %s page opens until its pages are improved" % (k_, d_, j_, k_))
    stuck = []  # live pages held for a reason a fix can clear (not a river's short record, which is by design): the watchdog alarms on these (ChatGPT round 1: open_wave exited 0 while skipping every lake)
    for row in rows_:
        u = row["url"]
        if u in have or u not in live:
            continue
        # indexability (docs/research/FRESH-REVIEW-PLAN.md 3.4): a page is released only if it passed the queue gate, shows enough data blocks and has a record long enough for a meaningful comparison
        if row["status"] != "live":  # only a gauge actually marked live is deployed; a queue gauge must not enter the index
            skipped["gate"] += 1
            continue
        if not pages_.review_ok(row["site"], u, rv):  # CLAUDE.md: every new page kind is screenshotted at phone width before Google; a lake or coast opens only once its review passed (data/reviewed.json)
            skipped["not reviewed"] += 1
            unreviewed.append(u)
            continue
        if kind_of.get(u) in held:  # owner 2026-11-15: Google is declining this kind as thin; opening more of it would teach Google the site is thin
            skipped["kind Google declines"] = skipped.get("kind Google declines", 0) + 1
            continue
        # owner 2026-11-08: "no such thing as thin content if it's literally a different river/lake": no block-count or years-of-record gate; the page says what it lacks
        pick.append((u, row["river"], row["place"], row["score"]))
        if len(pick) >= n:
            break
    print("next %d gauge pages (live, by score):" % len(pick))
    for u, r, p, s in pick:
        print("  %s  %s at %s  score %s" % (u, r, p, s))
    print("not eligible: %s" % skipped)
    if not pick:
        print("none: no live page is eligible")
    if "--apply" in sys.argv:
        json.dump({"at": __import__("datetime").date.today().isoformat(), "opened": len(pick), "stuck": stuck, "unreviewed": unreviewed}, open(os.path.join(ROOT, "data", "open-wave-last.json"), "w", encoding="utf-8"), indent=1)
    if stuck:
        print("STUCK (live, never opened): %d: %s" % (len(stuck), "; ".join(stuck[:5])))
    if "--apply" in sys.argv and pick:
        cfg["open"] = True
        cfg["allow"] = sorted(have | {u for u, *_ in pick})
        json.dump(cfg, open(IX, "w", encoding="utf-8"), indent=1)
        print("written to data/index-allow.json (open=true, %d pages allowed). Now build, check, deploy." % len(cfg["allow"]))


if __name__ != "__main__":
    pass
elif sys.argv[1:] == ["--selftest"]:
    S = {"https://riverwaterlevels.com/lake/a/": {"state": "Crawled - currently not indexed", "date": "2026-11-15"}}
    K = {"/lake/%s/" % c: "lake-usgs" for c in "abcdefghij"} | {"/river/r/x/": "river"}
    S.update({"https://riverwaterlevels.com/lake/%s/" % c: {"state": "Crawled - currently not indexed", "date": "2026-11-15"} for c in "bc"})
    S.update({"https://riverwaterlevels.com/lake/%s/" % c: {"state": "Submitted and indexed", "date": "2026-11-15"} for c in "defg"})
    S["https://riverwaterlevels.com/lake/h/"] = {"state": "Discovered - currently not indexed", "date": "2026-11-15"}
    S["https://riverwaterlevels.com/river/r/x/"] = {"state": "Crawled - currently not indexed", "date": "2026-11-15"}
    assert held_kinds(S, K, "2026-11-15") == {"lake-usgs": (3, 7)}, "thin gate: 3 of 7 lakes declined did not hold lakes, or 1 declined river held rivers, or a never-crawled page counted"
    assert held_kinds(S, K, "2026-12-15") == {} and held_kinds({}, K, "2026-11-15") == {}, "thin gate: stale or missing Google states held a kind"
    more = {"/lake/m%d/" % i: "lake-usgs" for i in range(14)}
    K.update(more)
    S.update({"https://riverwaterlevels.com" + u: {"state": "Submitted and indexed", "date": "2026-11-15"} for u in more})
    assert held_kinds(S, K, "2026-11-15") == {}, "thin gate: 3 declined of 21 judged (under 15%) held lakes"
    assert kind_of_url("/river/a/b/", {"/river/a/b/": "river"}, {}) == "river" and kind_of_url("/rivers/co/", {}, {}) is None, "thin gate: a gauge page lost its kind, or a hub got one"
    assert kind_of_url("/england/river-trent-at-colwick/", {}, {"england": "world-ea"}) == "world-ea", "thin gate: a world page has no kind, so Google declining it held nothing"
    print("selftest OK")
else:
    main()
