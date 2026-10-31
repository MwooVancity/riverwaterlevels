"""After a refresh failed on a release day: send the new gauges that failed back to the queue, so the retry ships the rest.
Reads dist_next/_failed.json (written by check.py). Exit 0: every failure was a new gauge, now queued with its reason. Exit 1: something else failed
(an existing page or a site-level rule), so the workflow undoes the whole release instead. 2026-10-30: one new gauge with no earlier page froze all deploys for 13 h."""
import csv, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lib.pages import load_effective

WAVES, ALLOW = os.path.join(ROOT, "data", "waves.csv"), os.path.join(ROOT, "data", "index-allow.json")


def main():
    try:
        failed = json.load(open(os.path.join(ROOT, "dist_next", "_failed.json"), encoding="utf-8"))
    except (OSError, ValueError):
        sys.exit("no _failed.json: the failure was not a page check")
    pages = {k.replace("\\", "/"): v for k, v in (failed.get("pages") or {}).items()}
    if failed.get("site") or not pages:
        sys.exit("site-level failure or no failing page: %s" % str(failed.get("site"))[:200])
    was = {r["site"] for r in csv.DictReader(subprocess.check_output(["git", "show", "HEAD:data/waves.csv"], cwd=ROOT, text=True, encoding="utf-8").splitlines()) if r["status"] == "live"}
    rows, _ = load_effective()
    rel = {rows[s]["dashboard_url"].strip("/") + "/index.html": s for s in rows}
    bad = {rel.get(k[6:] if k.startswith("embed/") else k): v for k, v in pages.items()}  # a gauge's embed page fails with it (2026-10-31)
    if None in bad or any(s in was for s in bad):
        sys.exit("a failing page is not a new gauge: %s" % sorted(pages)[:5])
    all_ = list(csv.DictReader(open(WAVES, encoding="utf-8")))
    for r in all_:
        if r["site"] in bad:
            r["status"], r["gate"] = "queue", ("site-check: " + bad[r["site"]][0]).replace("\n", " ")[:300]
    with open(WAVES, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(all_[0].keys()))
        w.writeheader()
        w.writerows(all_)
    cfg = json.load(open(ALLOW, encoding="utf-8"))
    gone = {rows[s]["dashboard_url"] for s in bad}
    cfg["allow"] = [u for u in cfg["allow"] if u not in gone]
    json.dump(cfg, open(ALLOW, "w", encoding="utf-8"), indent=1)
    print("back to the queue: %s" % ", ".join(sorted(bad)))


main()
