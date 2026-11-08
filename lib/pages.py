"""Effective page table: pages-all.csv (first-pass cleaner) plus human name overrides; slugs and hub membership recomputed from the full inventory
so a URL never depends on build order. Slug rules per MASTER-SPEC section 1."""
import os, re, csv, collections
from lib.common import DATA, SITE_URL, prep_lower

WAVE0 = "06893000 07010000 03294500 14105700 09380000 06192500 13334300 13317000 07109500 01463500 01646500 01358000 01576000 01636500 03185400 03192000 02336000 09498500 09506000 14103000 09085000 06041000 11447650 03011800 01555000".split()


@__import__("functools").lru_cache(maxsize=1)
def _pred_only():
    return frozenset(r["site"] for r in csv.DictReader(open(os.path.join(DATA, "coasts.csv"), encoding="utf-8")) if r.get("level_from"))


def variant(site, url):
    """The page template a lake or coast review covers (owner 2026-11-08 fully automatic: review once per variant, not per page). None for a river or world page.
    An agency lake id is not all digits (CDEC-SHA, RISE-6123, TWDB-travis); a prediction-only coast has level_from in data/coasts.csv."""
    if url.startswith("/coast/"):
        return "coast-prediction" if site in _pred_only() else "coast-live"
    if url.startswith("/lake/"):
        return "lake-usgs" if site[:1].isdigit() else "lake-great" if site.startswith("COOPS-") else "lake-agency"  # review 2026-11-08: a Great Lakes page (IGLD, GLERL) is its own template
    return None


def reviewed(path):
    """(urls, variants) that passed a phone review, from data/reviewed.json; a missing or torn file reviews nothing."""
    import json
    try:
        d = json.load(open(path, encoding="utf-8"))
        return set(d.get("passed") or {}), set(d.get("variants") or {})
    except (OSError, ValueError, AttributeError):
        return set(), set()


def review_ok(site, url, rv):
    """True when the page needs no review (river, world) or its url or its variant passed one."""
    v = variant(site, url)
    return v is None or url in rv[0] or v in rv[1]


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
    coast_n = collections.Counter(x["place_slug"] for x in rows.values() if x.get("coast"))  # gate audit 2026-11-08: Newport RI and Newport OR both became /coast/newport/ and one overwrote the other
    coast_ns = collections.Counter((x["place_slug"], x["state"]) for x in rows.values() if x.get("coast"))
    cslug = lambda x: x["place_slug"] + ("" if coast_n[x["place_slug"]] == 1 else "-" + x["state"].lower() + ("" if coast_ns[(x["place_slug"], x["state"])] == 1 else "-" + x["site"]))
    for g in hubs.values():
        seen = collections.Counter(x["place_slug"] for x in g)
        for x in g:
            x["place_final"] = x["place_slug"] + ("-" + x["site"] if seen[x["place_slug"]] > 1 or not x["place_slug"] else "")
            base = ("/coast/%s/" % cslug(x)) if x.get("coast") else ("/lake/%s/" % (x["river_slug"] + ("" if lake_n[x["river_slug"]] == 1 else "-" + x["state"].lower() + "-" + x["site"]))) if x.get("lake") else "/river/%s/%s/" % (x["hub_slug"], x["place_final"])
            x["hub_url"] = base if x.get("lake") else "/river/%s/" % x["hub_slug"]
            x["dashboard_url"], x["water_url"], x["forecast_url"] = base, base, base + "forecast/"  # one page per gauge; /water/ redirects here
    taken = {}
    for x in sorted(rows.values(), key=lambda x: x["site"]):  # never two gauges at one address (one page would overwrite the other): the later gets its id, said in the log
        if x["dashboard_url"] in taken:
            print("WARNING address clash: %s and %s both at %s; %s moves to its id" % (taken[x["dashboard_url"]], x["site"], x["dashboard_url"], x["site"]))
            x["dashboard_url"] = x["water_url"] = x["dashboard_url"].rstrip("/") + "-" + x["site"] + "/"
            x["forecast_url"] = x["dashboard_url"] + "forecast/"
        taken[x["dashboard_url"]] = x["site"]
    return rows, hubs
