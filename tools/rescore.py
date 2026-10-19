"""Planning tool (not part of the site build): rollout order at 25 pages per day.
Reads pages-all.csv (inventory with drainage, record years, NWS forecast point, name confidence) and data/demand.csv (Wikipedia 12-month page views per river name; unknown is NOT zero).
Score (owner 2026-10-17: water activities first): recreation fame 35 (data/recreation-rivers.txt), Wikipedia demand 20, data completeness 15, record length 10, NWS forecast point 10, name confidence 10; at most 3 gauges of one river per day.
Pilot gauges (lib/pages.py WAVE0) are status "live". Low-confidence names are "held-names" until the name cleaner is rerun. Output: data/waves.csv. Usage: python -I tools/rescore.py
"""
import os, sys, csv, math, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lib.pages import WAVE0

PAGES = r"C:\Users\mwoo7\Desktop\calcscrape\docs\research\prototypes\data\pages-all.csv"
PER_DAY, PER_RIVER_DAY = 25, 3
# One page per gauge plus a Forecast page where NWS issues a river forecast: all 9,099 gauges are about 17,200 files, inside the Cloudflare free limit of 20,000 per deploy (build.py refuses above 19,000).
MAX_GAUGES = 9099


def load_recreation():
    out = []
    for l in open(os.path.join(ROOT, "data", "recreation-rivers.txt"), encoding="utf-8"):
        l = l.strip()
        if l and not l.startswith("#") and "|" in l:
            w, name = l.split("|", 1)
            out.append((name.strip().lower(), int(w)))
    return out


def main():
    demand = {}
    dp = os.path.join(ROOT, "data", "demand.csv")
    if os.path.exists(dp):
        for r in csv.DictReader(open(dp, encoding="utf-8")):
            if r["status"] == "found" and r["views_12m"]:
                demand[(r["river"], r["state"])] = int(r["views_12m"])
    rows = list(csv.DictReader(open(PAGES, encoding="utf-8")))
    rec_names = load_recreation()
    vmax = math.log10(1 + max(demand.values())) if demand else 1
    amax = math.log10(max(float(r["drainage_sqmi"] or 1) for r in rows))
    out = []
    for r in rows:
        a = float(r["drainage_sqmi"] or 0)
        area = 100 * math.log10(a) / amax if a > 1 else 0
        v = demand.get((r["river"], r["state"]))
        if v is not None:
            known, basis = 100 * math.log10(1 + v) / vmax, "wikipedia"
        else:
            known, basis = min(60.0, 0.6 * area), "drainage-fallback"  # unknown is not zero, but cannot outrank a measured famous river
        yrs = int(r["years_record"] or 0)
        comp = 100 if yrs else 0
        rec = min(100, yrs / 60 * 100)
        fc = 100 if r["nws_lid"] else 0
        nm = {"high": 100, "medium": 60, "low": 20}[r["name_confidence"]]
        rn = r["river"].lower()
        hit = max([w for n, w in rec_names if n in rn] or [0])
        fame = {0: 0, 1: 70, 2: 100}[hit]
        score = 0.35 * fame + 0.20 * known + 0.15 * comp + 0.10 * rec + 0.10 * fc + 0.10 * nm
        out.append({"site": r["site"], "river": r["river"], "place": r["place"], "state": r["state"], "score": round(score, 1), "views": v if v is not None else "", "basis": basis, "name": r["name_confidence"], "url": r["water_url"].replace("/water/", "/"), "fame": hit})
    live = set(WAVE0)
    ranked = sorted([x for x in out if x["site"] not in live and x["name"] != "low"], key=lambda x: -x["score"])
    queue, beyond = ranked[:max(0, MAX_GAUGES - len(live))], ranked[max(0, MAX_GAUGES - len(live)):]
    beyond_ids = {x["site"] for x in beyond}
    held = sorted([x for x in out if x["site"] not in live and x["name"] == "low"], key=lambda x: -x["score"])
    for x in out:
        x["day"] = ""
        x["status"] = "live" if x["site"] in live else "held-names" if x["name"] == "low" and x["site"] not in live else "beyond-cap" if x["site"] in beyond_ids else "queue"
    day, pending = 1, list(queue)
    while pending:
        take, per, rest = [], collections.Counter(), []
        for x in pending:
            if len(take) < PER_DAY and per[x["river"]] < PER_RIVER_DAY:
                take.append(x)
                per[x["river"]] += 1
            else:
                rest.append(x)
        for x in take:
            x["day"] = day
        pending, day = rest, day + 1
    with open(os.path.join(ROOT, "data", "waves.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["status", "day", "site", "river", "place", "state", "score", "wikipedia_views_12m", "demand_basis", "name_confidence", "url"])
        for x in sorted(out, key=lambda x: (x["status"] != "live", x["status"] in ("held-names", "beyond-cap"), x["day"] if x["day"] != "" else 9999, -x["score"])):
            w.writerow([x["status"], x["day"], x["site"], x["river"], x["place"], x["state"], x["score"], x["views"], x["basis"], x["name"], x["url"]])
    print("demand found for %d rivers; queue %d over %d days (cap %d gauges); beyond the cap %d; held for names %d; live %d" % (len(demand), len(queue), day - 1, MAX_GAUGES, len(beyond), len(held), len(live)))
    first = [x for x in out if x["day"] == 1]
    print("day 1:", "; ".join("%s at %s %s (%s)" % (x["river"], x["place"], x["state"], x["views"] or "no wiki") for x in first[:10]))


main()
