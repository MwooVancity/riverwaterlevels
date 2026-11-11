"""Match unlinked US tide keywords in data/world-queue.csv to NOAA CO-OPS stations that publish a live water level (queue audit 2026-11-07:
~135 US lake and coast rows at 1K+ had no station). Strict, so no page answers the wrong place (keyword debate 2026-11-07):
- the keyword's place must equal a station name (or the name before a comma/parenthesis), case-folded;
- exactly ONE water-level station in the whole NOAA list may carry that name (Long Beach x4 is refused);
- a name that is also a non-US tide place in the queue's foreign rows is refused (Plymouth, Portland, Dunedin...).
Prints proposed coasts.csv rows; --apply appends them. One NOAA call (the station list). Read-only without --apply."""
import csv, json, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lib.common import km as _km  # noqa: E402
TIDE = re.compile(r"^(.*?)\s+(?:tides?|tide times|tide chart|tide table|tides today|harbor tides)$")
FOREIGN = {"plymouth", "portsmouth", "portland", "dunedin", "aberdeen", "bangor", "belfast", "brighton", "dover", "hull", "newport", "richmond", "freeport",
           "westport", "avalon", "brunswick", "falmouth", "weymouth", "exmouth", "whitby", "scarborough", "southport", "bournemouth", "torquay", "penzance", "vancouver", "beaufort"}  # Vancouver means BC; Beaufort is NC and SC
HELD = {"8536110": "no live water level (2026-11-06)", "8726674": "no live water level (2026-11-06)"}


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", s.lower())).strip()


def stations():
    j = json.loads(urllib.request.urlopen(urllib.request.Request("https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json?type=waterlevels",
                                                                 headers={"User-Agent": "riverwaterlevels.com coast_match"}), timeout=60).read())
    return [s for s in j["stations"] if s.get("state")]


GEONAMES = "https://download.geonames.org/export/dump/cities5000.zip"  # every populated place over 5,000 people, CC BY 4.0; read for matching only, nothing shown


ABROAD_MIN = 20000


def abroad(lines):
    """Names whose biggest town outside the US is bigger than any US town of that name (PLAN step 6: a systemic namesake rule instead of a longer FOREIGN list).
    lines: GeoNames cities rows (tab separated: 1 name, 2 ascii name, 8 country, 14 population). Plymouth UK 260k vs Plymouth MA 60k -> abroad."""
    us, other = {}, {}
    for ln in lines:
        f = ln.rstrip("\n").split("\t")
        if len(f) < 15:
            continue
        try:
            pop = int(f[14] or 0)
        except ValueError:
            continue
        d = us if f[8] == "US" else other
        for nm in {norm(f[1]), norm(f[2])}:
            if nm and pop > d.get(nm, -1):
                d[nm] = pop
    return {nm for nm, p in other.items() if p >= ABROAD_MIN and p >= 3 * us.get(nm, 0)}  # a small foreign town never outweighs a US place too small to be listed (Bandon OR vs Bandon IE 6,600: real run 2026-11-09)


def gazetteer():
    """abroad() over the GeoNames download (about 5 MB, once per weekly run); an empty set when it fails, and the hand FOREIGN list still applies."""
    import io, zipfile
    try:
        raw = urllib.request.urlopen(urllib.request.Request(GEONAMES, headers={"User-Agent": "riverwaterlevels.com coast_match"}), timeout=120).read()
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            return abroad(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8"))
    except Exception as e:
        print("GeoNames not read (%s): only the hand FOREIGN list applies this run" % str(e)[:80])
        return set()


def match(rows, sts, have, away=frozenset()):
    by = {}
    for s in sts:
        for nm in {norm(s["name"]), norm(re.split(r"[,(]", s["name"])[0])}:
            by.setdefault(nm, []).append(s)
    out, why = [], {}
    for r in rows:
        if r["gauge"] or int(r["tier"] or 0) < 1000:
            continue
        m = TIDE.match(r["keyword"].strip().lower())
        if not m:
            continue
        place = norm(m.group(1))
        cands = by.get(place, [])
        if place in FOREIGN:
            why[r["keyword"]] = "name also a foreign tide place"
        elif place in away:
            why[r["keyword"]] = "a bigger town of this name is outside the US (GeoNames)"
        elif len({c["id"] for c in cands}) != 1:
            why[r["keyword"]] = "%d NOAA water-level stations carry this name" % len({c["id"] for c in cands})
        elif cands[0]["id"] in HELD:
            why[r["keyword"]] = HELD[cands[0]["id"]]
        elif cands[0]["id"] in have:
            why[r["keyword"]] = "station already has a page"
        else:
            out.append((r, cands[0]))
    return out, why


def main():
    q = list(csv.DictReader(open(os.path.join(ROOT, "data", "world-queue.csv"), encoding="utf-8")))
    have = {r["site"] for r in csv.DictReader(open(os.path.join(ROOT, "data", "coasts.csv"), encoding="utf-8"))}
    got, why = match(q, stations(), have, gazetteer())
    for r, s in got:
        print("MATCH %-28s tier %-6s -> %s %s, %s (%.4f, %.4f)" % (r["keyword"], r["tier"], s["id"], s["name"], s["state"], s["lat"], s["lng"]))
    for k, w in sorted(why.items()):
        print("skip  %-28s %s" % (k, w))
    if "--apply" in sys.argv and got:
        join_queue([(r["keyword"], s, {}) for r, s in got])


def join_queue(adds):
    """The four files a coast page joins the release by (Panama City 6f560a3 was done by hand): data/coasts.csv, data/waves.csv (queue), the keyword's
    data/world-queue.csv row (gauge, feed, ready) and docs/research/priority/picks.csv (tracked though its folder is ignored). adds: (keyword, station, extra columns)."""
    cp, qp = os.path.join(ROOT, "data", "coasts.csv"), os.path.join(ROOT, "data", "world-queue.csv")
    rows, q = list(csv.DictReader(open(cp, encoding="utf-8"))), list(csv.DictReader(open(qp, encoding="utf-8")))
    cols = list(rows[0].keys()) + [c for c in ("level_from", "level_name", "level_km", "tables") if c not in rows[0]]
    have = {r["site"] for r in rows}
    for kw, s, extra in adds:
        if s["id"] in have:
            continue
        have.add(s["id"])
        name = re.split(r"[,(]", s["name"])[0].strip()
        name = name.title() if name.isupper() else name  # NOAA lists some stations in capitals (SAVANNAH, GA): a page title never shouts
        rows.append(dict({"site": s["id"], "state": s["state"], "name": name, "place": name, "lat": s["lat"], "lon": s["lng"], "raw_name": "%s, %s" % (s["name"], s["state"])}, **extra))
        for r in q:
            if r["keyword"] == kw:
                r.update(place=name, region=s["state"], country="US", gauge=s["id"], feed="NOAA CO-OPS", ready="yes")
        with open(os.path.join(ROOT, "data", "waves.csv"), "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["queue", "", s["id"], name, name, s["state"], "0", "", "", "0", "coast", "", "", "human", "/coast/%s/" % re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")])
        with open(os.path.join(ROOT, "docs", "research", "priority", "picks.csv"), "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([s["id"], name, name, s["state"], "ocean"])
        print("joined the queue: %s %s (%s)" % (s["id"], name, kw))
    for p, data, hd in ((cp, rows, cols), (qp, q, list(q[0].keys()))):
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, hd)
            w.writeheader()
            w.writerows(data)


def km(a, b):
    """Two NOAA station dicts ({lat, lng}): lib/common.km (was a flat-earth copy; under 0.1% apart at these 10-25 km limits)."""
    return _km(float(a["lat"]), float(a["lng"]), float(b["lat"]), float(b["lng"]))


def pred_pick(picks, pred, wl, have, ref_km=10, level_km=25):
    """Prediction-only tide pages (owner 2026-11-08; handoff 2026-11-08a). Only SERP-proven picks (data/tide-picks.csv verdict US); the station must have
    no live level of its own (a subordinate station too, even beside a reference station: owner decision 4); the page's one real reading is the nearest NOAA live
    water level within level_km of the station itself (edge case 7), named with its distance. One page per station (edge case 9)."""
    by = {s["id"]: s for s in pred}
    refs = [s for s in pred if s.get("type") == "R"]
    wl_ids = {s["id"] for s in wl}
    out, why, seen = [], {}, set()
    for k in picks:
        s = by.get(k["station"])
        if k["verdict"] != "US":
            why[k["keyword"]] = "search shows %s (%s)" % (k["verdict"], k["meant_place"])
        elif not s:
            why[k["keyword"]] = "not a NOAA prediction station"
        elif s["id"] in wl_ids or s["id"] in have or s["id"] in seen:
            why[k["keyword"]] = "station already has a page or a live level"
        else:
            lv = min(wl, key=lambda w: km(s, w), default=None)
            if not lv or km(s, lv) > level_km:
                why[k["keyword"]] = "no live NOAA water level within %d km" % level_km
            else:
                seen.add(s["id"])
                out.append((k, s, lv, round(km(s, lv), 1)))
    return out, why


def pred_main():
    get = lambda t: [s for s in json.loads(urllib.request.urlopen(urllib.request.Request("https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json?type=" + t,
                     headers={"User-Agent": "riverwaterlevels.com coast_match"}), timeout=60).read())["stations"] if s.get("state")]
    have = {r["site"] for r in csv.DictReader(open(os.path.join(ROOT, "data", "coasts.csv"), encoding="utf-8"))}
    picks = list(csv.DictReader(open(os.path.join(ROOT, "data", "tide-picks.csv"), encoding="utf-8")))
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "coasts.csv"), encoding="utf-8")))
    pred, wl = get("tidepredictions"), get("waterlevels")
    got, why = pred_pick(picks, pred, wl, have)  # owner 2026-11-08: a nearby page on the same feed is no reason to refuse a searched place, even when the pages match
    for k, s, lv, d in got:
        near = min(rows, key=lambda r: km(s, {"lat": r["lat"], "lng": r["lon"]}))
        print("PICK %-30s %s %s, %s (%s) level from %s %s, %.1f km; nearest coast page %s %.1f km" % (k["keyword"], s["id"], s["name"], s["state"], s.get("type"), lv["id"], lv["name"], d, near["site"], km(s, {"lat": near["lat"], "lng": near["lon"]})))
    for k, w in sorted(why.items()):
        print("skip %-30s %s" % (k, w))
    by, far = {s["id"]: s for s in pred}, []
    for k in picks:  # tide tables (owner decision 3, 2026-11-08): no live level within 25 km, so the page shows the station's own predictions only; level_* names the nearest live station (a link, never a reading)
        if "within" in why.get(k["keyword"], "") and k["station"] not in {f[1]["id"] for f in far}:
            s = by[k["station"]]
            lv = min(wl, key=lambda w: km(s, w))
            far.append((k, s, lv, round(km(s, lv), 1)))
            print("TABLES %-28s %s %s, %s nearest live %s %s %.1f km" % (k["keyword"], s["id"], s["name"], s["state"], lv["id"], lv["name"], km(s, lv)))
    if any(a.startswith("--tables") for a in sys.argv):
        got = [(k, s, lv, d, "1") for k, s, lv, d in far[:int(next((a[9:] for a in sys.argv if a.startswith("--tables=")), "999"))]]
    else:
        got = [(k, s, lv, d, "") for k, s, lv, d in got]
    if "--apply" in sys.argv and got:  # release still waits for the variant review (data/reviewed.json variants: coast-prediction)
        join_queue([(k["keyword"], s, {"level_from": lv["id"], "level_name": lv["name"], "level_km": d, "tables": tb}) for k, s, lv, d, tb in got])


def selftest():
    P = [{"id": "R1", "name": "Ref", "state": "FL", "lat": 27.0, "lng": -82.0, "type": "R"}, {"id": "S1", "name": "Sub near", "state": "FL", "lat": 27.05, "lng": -82.0, "type": "S"},
         {"id": "S2", "name": "Sub far", "state": "FL", "lat": 28.0, "lng": -82.0, "type": "S"}, {"id": "R2", "name": "Lonely", "state": "AK", "lat": 60.0, "lng": -150.0, "type": "R"}]
    W = [{"id": "W1", "name": "Level", "state": "FL", "lat": 27.1, "lng": -82.0}, {"id": "W2", "name": "Level2", "state": "FL", "lat": 28.1, "lng": -82.0}]
    k = lambda kw, st, v="US": {"keyword": kw, "station": st, "verdict": v, "meant_place": "x"}
    got, why = pred_pick([k("ref tides", "R1"), k("ref tide times", "R1"), k("near tides", "S1"), k("far tides", "S2"), k("lonely tides", "R2"), k("kinsale tides", "R1", "FOREIGN")], P, W, set())
    assert [(a["keyword"], c["id"]) for a, b, c, d in got] == [("ref tides", "W1"), ("near tides", "W1"), ("far tides", "W2")], got  # owner 2026-11-08: a searched place gets its page even beside a reference station (decision 4)
    assert "within 25" in why["lonely tides"] and "FOREIGN" in why["kinsale tides"] and "already" in why["ref tide times"], why
    print("coast_match pred selftest OK")
    sts = [{"id": "1", "name": "Biloxi", "state": "MS", "lat": 30.4, "lng": -88.9}, {"id": "2", "name": "Long Beach", "state": "CA", "lat": 0, "lng": 0},
           {"id": "3", "name": "Long Beach", "state": "WA", "lat": 0, "lng": 0}, {"id": "4", "name": "Portland", "state": "ME", "lat": 0, "lng": 0}]
    rows = [{"keyword": "biloxi tides", "tier": "5000", "gauge": ""}, {"keyword": "long beach tides", "tier": "5000", "gauge": ""},
            {"keyword": "portland tide times", "tier": "5000", "gauge": ""}, {"keyword": "biloxi tide chart", "tier": "50", "gauge": ""}]
    got, why = match(rows, sts, set())
    gz = ["	".join(["1", n, n, "", "", "", "", "", c, "", "", "", "", "", str(p)]) for n, c, p in (("Plymouth", "GB", 260000), ("Plymouth", "US", 60000), ("Biloxi", "US", 46000), ("Kinsale", "IE", 5300), ("Bandon", "IE", 6600), ("Cork", "IE", 190000))]
    assert abroad(gz) == {"plymouth", "cork"}, abroad(gz)
    g2, w2 = match([{"keyword": "cork tides", "tier": "5000", "gauge": ""}, {"keyword": "biloxi tides", "tier": "5000", "gauge": ""}], sts + [{"id": "9", "name": "Cork", "state": "VA", "lat": 0, "lng": 0}], set(), abroad(gz))
    assert [s["id"] for _, s in g2] == ["1"] and "GeoNames" in w2["cork tides"], (g2, w2)
    assert [s["id"] for _, s in got] == ["1"] and "2 NOAA" in why["long beach tides"] and "foreign" in why["portland tide times"], (got, why)
    print("coast_match selftest OK")


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else pred_main() if "--predictions" in sys.argv else main()
