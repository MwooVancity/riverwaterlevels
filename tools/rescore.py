"""Planning tool (not part of the site build): the release order, one gauge at a time. Output: data/waves.csv and data/waves-report.txt.
Run `python -I tools/fetch_geo.py` first (coordinates, Wild and Scenic and Nationwide Rivers lines, Census places). Usage: python -I tools/rescore.py

S = Gate x (0.45 Activity + 0.15 Reach + 0.25 Decision + 0.15 Quality) - duplicate penalty        (all 0-100; review of 2026-10-18, docs/research/FRESH-REVIEW-PLAN.md)
Gate (a rule, not a weight): real record of 3+ years, not a ditch/canal/drain/outfall/floodway/spillway name, drainage 5 sq mi or more (unknown drainage passes only with an NWS point), name confidence not low.
Activity = the best of: Wild and Scenic segment with a recreation value within 3 km 100, with a fish value 90, any Wild and Scenic segment 90; Nationwide Rivers Inventory segment within 3 km 60;
  a river on the hand list (data/recreation-rivers.txt) counts 70/100 (weight 1/2) in the states the list names for it, or in any state when the list names none (generic river names are state-qualified in the file);
  tailwater by name (below a dam, lake or reservoir) 65; Nationwide Rivers Inventory description mentions paddling 85 or fishing 75; else drainage 20 to 5,000 sq mi 30, other sizes 10.
Reach = nearest large Census place within 25 km (population log-scaled, distance-discounted) 60%, Wikipedia river article views 40% (validated match only; unknown is not zero, the population term then stands alone).
Decision = NWS forecast point 40 + tailwater 20 + drainage 20 to 3,000 sq mi (flashy, changes within a day) 30.   Quality = record years (60 = 100) 70% + name confidence 30%.
Duplicate penalty: a river's second gauge loses 10 unless its drainage is 2x a better gauge on the same river, every gauge after the second loses 10 more. At most one gauge of a river per release day.
Not yet in the score (no free bulk source read yet): boat ramps and put-ins (Recreation.gov RIDB needs a key), PAD-US public land, state trout lists, flow variability per gauge (needs the full history, collected at S4)."""
import os, sys, csv, json, math, re, collections
from shapely.geometry import shape
from shapely.strtree import STRtree
from shapely import transform

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lib.pages import WAVE0, load_effective

GEO = os.path.join(ROOT, "data", "geo")
PER_DAY = 25
KM = 3.0
BAD = re.compile(r"\b(ditch|canal|drain|drainage|outfall|floodway|wasteway|spillway|diversion|sewer|storm|channel)\b", re.I)
TAIL = re.compile(r"\b(below|bl|blw|downstream of|ds of)\b.*\b(dam|lake|reservoir|lk|res|powerplant|power plant)\b|\btailwater\b", re.I)
RIVER_WORD = re.compile(r"(River|Creek|Brook|Run|Fork|Branch|Bayou|Stream|Rio)")


def lonlat_km(lon, lat):
    return lon * 111.32 * math.cos(math.radians(38)), lat * 110.57  # flat map for distances of a few km inside the lower 48; Alaska and Hawaii are approximate (3 km tests only)


ST = {"Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY", "Puerto Rico": "PR"}
PADDLE = re.compile(r"kayak|canoe|raft|float|whitewater|white water|paddl|tubing|rapids|boating", re.I)
FISH = re.compile(r"fish|trout|salmon|steelhead|angl", re.I)


def load_lines(name):
    """Line geometries (projected to km) with their tags: the river's own name and state (for the state-qualified fame join) and whether the agency's description mentions paddling or fishing."""
    import numpy as np
    d = json.load(open(os.path.join(GEO, name), encoding="utf-8"))
    geoms, tags = [], []
    for f in d["features"]:
        if not f.get("geometry"):
            continue
        g = shape(f["geometry"])
        geoms.append(transform(g, lambda a: np.column_stack(lonlat_km(a[:, 0], a[:, 1]))))
        p = f.get("properties") or {}
        nm = (p.get("River") or p.get("GNIS_Name") or p.get("GNIS_NAME") or p.get("WSR_RIVER_SHORTNAME") or "").lower().strip()
        sts = [ST.get(p.get(k)) for k in ("State1", "State2", "STATE") if p.get(k)]
        txt = (p.get("Description") or "") + " " + (p.get("ORV_LIST") or "")
        tags.append((nm, sts, bool(PADDLE.search(txt)), bool(FISH.search(txt))))
    return geoms, STRtree(geoms), tags


def near(tree, geoms, pt, km=KM):
    from shapely.geometry import Point
    p = Point(*pt)
    return [i for i in tree.query(p.buffer(km)) if geoms[i].distance(p) <= km]


def named_set(*tag_lists):
    """(river name, state) pairs that the Wild and Scenic and Nationwide Rivers lists record: a hand-list river counts as famous only in a state where one of these lists names it."""
    return {(t[0], st) for tags in tag_lists for t in tags for st in t[1] if t[0] and st}


def load_demand():
    out = {}
    for r in csv.DictReader(open(os.path.join(ROOT, "data", "demand.csv"), encoding="utf-8")):
        t = r["title"]
        if r["status"] != "found" or not r["views_12m"] or t.startswith("List_of") or ",_" in t:
            continue
        first = re.split(r"[ _]", r["river"])[0].lower()
        if first not in t.lower():
            continue
        out[(r["river"], r["state"])] = int(r["views_12m"])
    return out


def load_fame():
    out = []
    for l in open(os.path.join(ROOT, "data", "recreation-rivers.txt"), encoding="utf-8"):
        l = l.strip()
        if l and not l.startswith("#") and "|" in l:
            parts = l.split("|")
            out.append((re.compile(r"(^|\s)" + re.escape(parts[1].strip().lower()) + r"(\s|$)"), int(parts[0]), set(parts[2].split(",")) if len(parts) > 2 else None))
    return out


def main():
    rows, _ = load_effective()
    geo = {r["site"]: r for r in csv.DictReader(open(os.path.join(GEO, "gauge-geo.csv"), encoding="utf-8"))}
    places = []
    for r in csv.DictReader(open(os.path.join(GEO, "places.csv"), encoding="utf-8")):
        places.append((float(r["lat"]), float(r["lon"]), int(r["pop2023"])))
    big = [p for p in places if p[2] >= 2500]
    pk = [lonlat_km(p[1], p[0]) + (p[2],) for p in big]
    pxy = [(x, y) for x, y, _ in pk]
    from shapely.geometry import MultiPoint, Point
    ptree = STRtree([Point(x, y) for x, y in pxy])
    wsr, wsr_t, wsr_g = load_lines("wsr.geojson")
    wsr_rec, wsr_rec_t, _ = load_lines("wsr-recreation.geojson")
    wsr_fish, wsr_fish_t, _ = load_lines("wsr-fish.geojson")
    nri, nri_t, nri_g = load_lines("nri.geojson")
    named = named_set(wsr_g, nri_g)
    demand = load_demand()
    vmax = math.log10(1 + max(demand.values())) if demand else 1
    fame = load_fame()
    sites = [s for s in rows if s in geo]
    out = []
    for s in sites:
        r, g = rows[s], geo[s]
        lat, lon = float(g["lat"]), float(g["lon"])
        xy = lonlat_km(lon, lat)
        a = float(r["drainage_sqmi"] or 0)
        yrs = int(r["years_record"] or 0)
        name = (r["river"] + " " + r["place"] + " " + r["raw_name"]).lower()
        is_wsr, is_rec, is_fish = bool(near(wsr_t, wsr, xy)), bool(near(wsr_rec_t, wsr_rec, xy)), bool(near(wsr_fish_t, wsr_fish, xy))
        nri_hits = near(nri_t, nri, xy)
        is_nri = bool(nri_hits)
        n_paddle = any(nri_g[i][2] for i in nri_hits)
        n_fish = any(nri_g[i][3] for i in nri_hits)
        tail = bool(TAIL.search(r["raw_name"]))
        rn = r["river"].lower()
        hit = max([w for rx, w, sts in fame if rx.search(rn) and (sts is None or r["state"] in sts)] or [0])
        pt = Point(*xy)
        pop = 0.0
        for i in ptree.query(pt.buffer(25)):
            d = pt.distance(ptree.geometries[i])
            pop = max(pop, pk[i][2] / (1 + d / 8))
        gate_why = ""
        if BAD.search(r["raw_name"]) or re.search(r"\b(wash|ditch)$", r["river"], re.I):
            gate_why = "excluded-name"
        elif yrs < 3:
            gate_why = "short-record"
        elif (a and a < 5) or (not a and not r["nws_lid"]):
            gate_why = "tiny-basin"
        act = 10
        if 20 <= a <= 5000:
            act = 30
        if tail:
            act = max(act, 65)
        if is_nri:
            act = max(act, 60)
        if n_fish:
            act = max(act, 75)
        if n_paddle:
            act = max(act, 85)
        verified = (rn, r["state"]) in named
        if hit:
            act = max(act, 100 if hit == 2 else 70)
        if is_wsr:
            act = max(act, 90)
        if is_fish:
            act = max(act, 90)
        if is_rec:
            act = max(act, 100)
        v = demand.get((r["river"], r["state"]))
        popscore = min(100.0, 100 * math.log10(1 + pop) / math.log10(1_000_000)) if pop else 0.0
        reach = popscore if v is None else 0.6 * popscore + 0.4 * (100 * math.log10(1 + v) / vmax)
        dec = (40 if r["nws_lid"] else 0) + (20 if tail else 0) + (30 if 20 <= a <= 3000 else 0)
        qual = 0.7 * min(100, yrs / 60 * 100) + 0.3 * {"high": 100, "human": 100, "auto2": 95, "medium": 60, "low": 20}[r["name_confidence"]]
        score = 0.45 * act + 0.15 * reach + 0.25 * dec + 0.15 * qual
        out.append({"site": s, "river": r["river"], "place": r["place"], "state": r["state"], "raw": score, "act": act, "reach": round(reach), "dec": dec, "area": a, "name": r["name_confidence"], "gate": gate_why,
                    "views": v if v is not None else "", "url": r["dashboard_url"], "why": ",".join(k for k, f in (("wsr-rec", is_rec), ("wsr-fish", is_fish), ("wsr", is_wsr), ("nri", is_nri), ("nri-paddle", n_paddle), ("nri-fish", n_fish), ("tail", tail), ("fame", bool(hit))) if f)})
    by_river = collections.defaultdict(list)
    for x in out:
        by_river[(x["river"], x["state"])].append(x)
    for g in by_river.values():
        g.sort(key=lambda x: -x["raw"])
        for i, x in enumerate(g):
            pen = 0
            if i >= 1 and not any(x["area"] and y["area"] and x["area"] >= 2 * y["area"] or (x["area"] and y["area"] and y["area"] >= 2 * x["area"]) for y in g[:i]):
                pen += 10
            if i >= 2:
                pen += 10
            x["score"] = round(max(0.0, x["raw"] - pen), 1)
    try:
        now_ = {r["site"]: r["status"] for r in csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8"))}
    except OSError:
        now_ = {}
    live = {s for s, st in now_.items() if st == "live"} if now_ else set(WAVE0)
    for x in out:
        x["status"] = "live" if x["site"] in live else "queue" if now_.get(x["site"]) == "queue" and not x["gate"] else ("excluded" if x["gate"] else "held-names" if x["name"] == "low" else "queue")
    queue = sorted([x for x in out if x["status"] == "queue"], key=lambda x: -x["score"])
    day, pending = 1, list(queue)
    while pending:
        take, seen, rest = [], set(), []
        for x in pending:
            k = (x["river"], x["state"])
            if len(take) < PER_DAY and k not in seen:
                take.append(x)
                seen.add(k)
            else:
                rest.append(x)
        for x in take:
            x["day"] = day
        pending, day = rest, day + 1
    for x in out:
        x.setdefault("day", "")
    order = sorted(out, key=lambda x: (x["status"] != "live", {"queue": 0, "live": 0, "held-names": 1, "excluded": 2}[x["status"]], x["day"] if x["day"] != "" else 9999, -x["score"]))
    with open(os.path.join(ROOT, "data", "waves.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["status", "day", "site", "river", "place", "state", "score", "activity", "reach", "decision", "signals", "gate", "wikipedia_views_12m", "name_confidence", "url"])
        for x in order:
            w.writerow([x["status"], x["day"], x["site"], x["river"], x["place"], x["state"], x["score"], x["act"], x["reach"], x["dec"], x["why"], x["gate"], x["views"], x["name"], x["url"]])
    cnt = collections.Counter(x["status"] for x in out)
    rep = ["gauges scored %d: %s; queue spans %d days at %d a day" % (len(out), dict(cnt), day - 1, PER_DAY)]
    rep.append("signals in the first 300 queue gauges: " + str(collections.Counter(t for x in queue[:300] for t in x["why"].split(",") if t)))
    rep.append("signals in the whole queue: " + str(collections.Counter(t for x in queue for t in x["why"].split(",") if t)))
    pos = {x["site"]: i for i, x in enumerate(queue)}
    expect = [l.strip() for l in open(os.path.join(ROOT, "data", "backtest.txt"), encoding="utf-8") if l.strip() and not l.startswith("#")]
    rep.append("back-test (data/backtest.txt: river|place|state should sit in the first 1500 queue positions (60 days)):")
    hit_n = 0
    for e in expect:
        rv, pl, st = [t.strip() for t in e.split("|")]
        m = [x for x in out if x["state"] == st and x["river"].lower() == rv.lower() and pl.lower() in x["place"].lower()]
        p = min([pos[x["site"]] for x in m if x["site"] in pos] or [None], key=lambda v: 10 ** 9 if v is None else v)
        ok = (p is not None and p < 1500) or any(x["status"] == "live" for x in m)
        hit_n += ok
        rep.append("  %-4s %-28s %-24s %s" % ("OK" if ok else "MISS", rv, pl, ("position %d" % p) if p is not None else ("not queued (%s)" % ",".join(sorted({x["status"] + ":" + (x["gate"] or x["name"]) for x in m})) if m else "no such gauge")))
    rep.append("back-test: %d of %d in the first 1500" % (hit_n, len(expect)))
    rep.append("day 1: " + "; ".join("%s at %s %s (%s)" % (x["river"], x["place"], x["state"], x["why"]) for x in queue[:PER_DAY]))
    open(os.path.join(ROOT, "data", "waves-report.txt"), "w", encoding="utf-8").write("\n".join(rep) + "\n")
    print("\n".join(rep))


main()
