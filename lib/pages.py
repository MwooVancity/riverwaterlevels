"""Effective page table: pages-all.csv (first-pass cleaner) plus human name overrides; slugs and hub membership recomputed from the full inventory
so a URL never depends on build order. Slug rules per MASTER-SPEC section 1."""
import os, re, csv, collections
from lib.common import DATA, SITE_URL, prep_lower

WAVE0 = "06893000 07010000 03294500 14105700 09380000 06192500 13334300 13317000 07109500 01463500 01646500 01358000 01576000 01636500 03185400 03192000 02336000 09498500 09506000 14103000 09085000 06041000 11447650 03011800 01555000".split()


def slug(s):
    s = s.lower().replace("&", " and ").replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def load_effective():
    rows = {r["site"]: dict(r) for r in csv.DictReader(open(os.path.join(DATA, "pages-all.csv"), encoding="utf-8"))}
    for r in csv.DictReader(open(os.path.join(DATA, "lakes.csv"), encoding="utf-8")):  # lakes and reservoirs (plan 2026-11-05 step 1): one page per lake at /lake/<name>/
        rows[r["site"]] = {"wave": "", "site": r["site"], "state": r["state"], "river": r["lake"], "place": r["place"], "name_confidence": "human", "score": "0", "years_record": "", "nws_lid": "",
                           "drainage_sqmi": "", "raw_name": r["raw_name"], "lake": "1", "natural": r.get("natural") or ""}
    for r in csv.DictReader(open(os.path.join(DATA, "coasts.csv"), encoding="utf-8")):  # NOAA CO-OPS coast stations (plan 2026-11-06 step 2): /coast/<place>/, built on the lake path (level first, no flow)
        rows[r["site"]] = {"wave": "", "site": r["site"], "state": r["state"], "river": r["name"], "place": r["place"], "name_confidence": "human", "score": "0", "years_record": "", "nws_lid": "",
                           "drainage_sqmi": "", "raw_name": r["raw_name"], "lake": "1", "coast": "1", "natural": "1"}
    ov = {r["site"]: r for r in csv.DictReader(open(os.path.join(DATA, "name-overrides.csv"), encoding="utf-8"))}
    fx_p = os.path.join(DATA, "name-fixes.csv")  # name cleaner v2 (tools/clean_names.py): low-confidence names it could read; human overrides win, live gauges are never renamed
    fx = {r["site"]: r for r in csv.DictReader(open(fx_p, encoding="utf-8"))} if os.path.exists(fx_p) else {}
    for s, r in rows.items():
        if s in ov:
            r["river"], r["place"], r["name_confidence"] = ov[s]["river"], ov[s]["place"], "human"
        elif s in fx and s not in WAVE0:
            r["river"], r["place"], r["name_confidence"] = fx[s]["river"], fx[s]["place"], "auto2"
    for r in rows.values():
        r["river"] = prep_lower(r["river"])
    by_rs = collections.defaultdict(set)
    for r in rows.values():
        r["river_slug"] = slug(r["river"])
        r["place_slug"] = slug(r["place"])
        by_rs[r["river_slug"]].add(r["state"])
    hubs = collections.defaultdict(list)
    lake_n = collections.Counter(r["river_slug"] for r in rows.values() if r.get("lake"))  # two lakes with one name (Clear Lake CA and IA) never share an address
    for r in rows.values():
        r["hub_slug"] = ("lake-" + r["site"]) if r.get("lake") else r["river_slug"] + ("-" + r["state"].lower() if len(by_rs[r["river_slug"]]) > 1 else "")  # a lake is never grouped into a river hub
        hubs[(r["hub_slug"], r["state"])].append(r)
    for g in hubs.values():
        seen = collections.Counter(x["place_slug"] for x in g)
        for x in g:
            x["place_final"] = x["place_slug"] + ("-" + x["site"] if seen[x["place_slug"]] > 1 or not x["place_slug"] else "")
            base = ("/coast/%s/" % x["place_slug"]) if x.get("coast") else ("/lake/%s/" % (x["river_slug"] + ("" if lake_n[x["river_slug"]] == 1 else "-" + x["state"].lower() + "-" + x["site"]))) if x.get("lake") else "/river/%s/%s/" % (x["hub_slug"], x["place_final"])
            x["hub_url"] = base if x.get("lake") else "/river/%s/" % x["hub_slug"]
            x["dashboard_url"], x["water_url"], x["forecast_url"] = base, base, base + "forecast/"  # one page per gauge; /water/ redirects here
    return rows, hubs
