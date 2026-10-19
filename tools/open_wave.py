"""Open the next batch of gauge pages to search engines, in priority order (data/waves.csv, highest score first).
Usage: python tools/open_wave.py 25            dry run: prints the next 25 gauge pages that are live, reviewed SHIP and not yet allowed
       python tools/open_wave.py 25 --apply    writes them into state/index-allow.json and sets open true (site_pages stays as it is)
       python tools/open_wave.py --pull /river/x/y/ [...]   removes pages from the allow list (the kill switch for a batch)
Then run build.py, check.py and deploy. check.py refuses the build if an allowed page has no SHIP review. Search engines act on a change only when they recrawl, so release small batches and measure each one."""
import csv, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IX = os.path.join(ROOT, "state", "index-allow.json")


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
    live = set(load(os.path.join(ROOT, "dist", "_urls.json"), {"urls": []})["urls"])
    pages = load(os.path.join(ROOT, "state", "reviews.json"), {}).get("pages", {})
    have = set(cfg["allow"])
    pick = []
    for row in csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8")):
        u = row["url"].replace("/water/", "/")  # waves.csv still carries the old three-tab address
        if u in have or u not in live:
            continue
        if pages.get(u, {}).get("verdict") != "SHIP":
            continue
        pick.append((u, row["river"], row["place"], row["score"]))
        if len(pick) >= n:
            break
    print("next %d gauge pages (live, reviewed SHIP, by score):" % len(pick))
    for u, r, p, s in pick:
        print("  %s  %s at %s  score %s" % (u, r, p, s))
    if not pick:
        print("none: pages need a SHIP verdict in state/reviews.json first (docs/REVIEW-PROMPT.md)")
    if "--apply" in sys.argv and pick:
        cfg["open"] = True
        cfg["allow"] = sorted(have | {u for u, *_ in pick})
        json.dump(cfg, open(IX, "w", encoding="utf-8"), indent=1)
        print("written to state/index-allow.json (open=true, %d pages allowed). Now build, check, deploy." % len(cfg["allow"]))


main()
