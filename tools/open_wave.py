"""Open the next batch of gauge pages to search engines, in priority order (data/waves.csv, highest score first).
Usage: python tools/open_wave.py 25            dry run: prints the next 25 gauge pages that are live and not yet allowed
       python tools/open_wave.py 25 --apply    writes them into data/index-allow.json and sets open true (site_pages stays as it is)
       python tools/open_wave.py --pull /river/x/y/ [...]   removes pages from the allow list (the kill switch for a batch)
Then run build.py, check.py and deploy. Search engines act on a change only when they recrawl, so release small batches and measure each one."""
import csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IX = os.path.join(ROOT, "data", "index-allow.json")
MIN_BLOCKS, MIN_YEARS = 15, 10  # the pilot pages render 26 to 38 blocks; re-set after a sample of tail gauges has been built


def load(p, default):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def main():
    cfg = load(IX, {"open": False, "site_pages": False, "allow": []})
    if "--pull" in sys.argv:
        gone = [a for a in sys.argv[sys.argv.index("--pull") + 1:]]
        cfg["allow"] = [u for u in cfg["allow"] if u not in gone]
        json.dump(cfg, open(IX, "w", encoding="utf-8"), indent=1)
        print("pulled %d page(s); %d remain allowed. Deploy to take effect." % (len(gone), len(cfg["allow"])))
        return
    n = int(next((a for a in sys.argv[1:] if a.isdigit()), 25))
    pub = load(os.path.join(ROOT, "data", "publisher.json"), {})
    if "--apply" in sys.argv and "@" not in str(pub.get("email") or "") and not pub.get("waived"):
        sys.exit("refused: data/publisher.json has no contact email and no owner waiver. A page may not be indexed without a named publisher and a corrections contact unless the owner waives it in writing there (docs/RUNBOOK.md, precondition 6).")
    live = set(load(os.path.join(ROOT, "dist", "_urls.json"), {"urls": []})["urls"])
    have = set(cfg["allow"])
    pick = []
    blocks = load(os.path.join(ROOT, "dist", "_blocks.json"), {})
    years = {r["site"]: int(r["years_record"] or 0) for r in csv.DictReader(open(os.path.join(ROOT, "data", "pages-all.csv"), encoding="utf-8"))}
    skipped = {"gate": 0, "few blocks": 0, "short record": 0}
    for row in csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8")):
        u = row["url"]
        if u in have or u not in live:
            continue
        # indexability (docs/research/FRESH-REVIEW-PLAN.md 3.4): a page is released only if it passed the queue gate, shows enough data blocks and has a record long enough for a meaningful comparison
        if row["status"] != "live":  # only a gauge actually marked live is deployed; a queue gauge must not enter the index
            skipped["gate"] += 1
            continue
        if blocks.get(u, 0) < MIN_BLOCKS:
            skipped["few blocks"] += 1
            continue
        if years.get(row["site"], 0) < MIN_YEARS:
            skipped["short record"] += 1
            continue
        pick.append((u, row["river"], row["place"], row["score"]))
        if len(pick) >= n:
            break
    print("next %d gauge pages (live, by score):" % len(pick))
    for u, r, p, s in pick:
        print("  %s  %s at %s  score %s" % (u, r, p, s))
    print("not eligible: %s" % skipped)
    if not pick:
        print("none: no live page is eligible")
    if "--apply" in sys.argv and pick:
        cfg["open"] = True
        cfg["allow"] = sorted(have | {u for u, *_ in pick})
        json.dump(cfg, open(IX, "w", encoding="utf-8"), indent=1)
        print("written to data/index-allow.json (open=true, %d pages allowed). Now build, check, deploy." % len(cfg["allow"]))


main()
