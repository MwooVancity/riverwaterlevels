"""Match unlinked US tide keywords in data/world-queue.csv to NOAA CO-OPS stations that publish a live water level (queue audit 2026-11-07:
~135 US lake and coast rows at 1K+ had no station). Strict, so no page answers the wrong place (keyword debate 2026-11-07):
- the keyword's place must equal a station name (or the name before a comma/parenthesis), case-folded;
- exactly ONE water-level station in the whole NOAA list may carry that name (Long Beach x4 is refused);
- a name that is also a non-US tide place in the queue's foreign rows is refused (Plymouth, Portland, Dunedin...).
Prints proposed coasts.csv rows; --apply appends them. One NOAA call (the station list). Read-only without --apply."""
import csv, json, math, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


def match(rows, sts, have):
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
    got, why = match(q, stations(), have)
    for r, s in got:
        print("MATCH %-28s tier %-6s -> %s %s, %s (%.4f, %.4f)" % (r["keyword"], r["tier"], s["id"], s["name"], s["state"], s["lat"], s["lng"]))
    for k, w in sorted(why.items()):
        print("skip  %-28s %s" % (k, w))
    if "--apply" in sys.argv and got:
        with open(os.path.join(ROOT, "data", "coasts.csv"), "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for r, s in got:
                place = re.split(r"[,(]", s["name"])[0].strip()
                w.writerow([s["id"], s["state"], s["name"], place, s["lat"], s["lng"], "%s, %s" % (s["name"], s["state"]), "", "", ""])
        print("appended %d rows to data/coasts.csv" % len(got))


def km(a, b):
    p = 0.017453292519943295
    x = (float(b["lng"]) - float(a["lng"])) * p * math.cos((float(a["lat"]) + float(b["lat"])) / 2 * p)
    return 6371 * math.hypot(x, (float(b["lat"]) - float(a["lat"])) * p)


def pred_pick(picks, pred, wl, have, ref_km=10, level_km=25):
    """Prediction-only tide pages (owner 2026-11-08; handoff 2026-11-08a). Only SERP-proven picks (data/tide-picks.csv verdict US); the station must have
    no live level of its own; a subordinate station only when no reference station is within ref_km; the page's one real reading is the nearest NOAA live
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
        elif s.get("type") == "S" and any(km(s, r) <= ref_km for r in refs):
            why[k["keyword"]] = "subordinate with a reference station within %d km" % ref_km
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
    got, why = pred_pick(picks, get("tidepredictions"), get("waterlevels"), have)  # owner 2026-11-08: a nearby page on the same feed is no reason to refuse a searched place; check.py's 80% rule judges real copies
    for k, s, lv, d in got:
        near = min(rows, key=lambda r: km(s, {"lat": r["lat"], "lng": r["lon"]}))
        print("PICK %-30s %s %s, %s (%s) level from %s %s, %.1f km; nearest coast page %s %.1f km" % (k["keyword"], s["id"], s["name"], s["state"], s.get("type"), lv["id"], lv["name"], d, near["site"], km(s, {"lat": near["lat"], "lng": near["lon"]})))
    for k, w in sorted(why.items()):
        print("skip %-30s %s" % (k, w))
    if "--apply" in sys.argv and got:  # the same four files a live-level coast joins by (Panama City, 6f560a3); release still waits for the phone review (data/reviewed.json)
        cols = list(rows[0].keys()) + [c for c in ("level_from", "level_name", "level_km") if c not in rows[0]]
        qp = os.path.join(ROOT, "data", "world-queue.csv")
        q = list(csv.DictReader(open(qp, encoding="utf-8")))
        for k, s, lv, d in got:
            name = re.split(r"[,(]", s["name"])[0].strip()
            rows.append({"site": s["id"], "state": s["state"], "name": name, "place": name, "lat": s["lat"], "lon": s["lng"], "raw_name": "%s, %s" % (s["name"], s["state"]),
                         "level_from": lv["id"], "level_name": lv["name"], "level_km": d})
            for r in q:
                if r["keyword"] == k["keyword"]:
                    r.update(place=name, region=s["state"], country="US", gauge=s["id"], feed="NOAA CO-OPS", ready="yes")
            with open(os.path.join(ROOT, "data", "waves.csv"), "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["queue", "", s["id"], name, name, s["state"], "0", "", "", "0", "coast", "", "", "human", "/coast/%s/" % re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")])
            with open(os.path.join(ROOT, "docs", "research", "priority", "picks.csv"), "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([s["id"], name, name, s["state"], "ocean"])
        for p, data, hd in ((os.path.join(ROOT, "data", "coasts.csv"), rows, cols), (qp, q, list(q[0].keys()))):
            with open(p, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, hd)
                w.writeheader()
                w.writerows(data)
        print("applied %d prediction-only stations" % len(got))


def selftest():
    P = [{"id": "R1", "name": "Ref", "state": "FL", "lat": 27.0, "lng": -82.0, "type": "R"}, {"id": "S1", "name": "Sub near", "state": "FL", "lat": 27.05, "lng": -82.0, "type": "S"},
         {"id": "S2", "name": "Sub far", "state": "FL", "lat": 28.0, "lng": -82.0, "type": "S"}, {"id": "R2", "name": "Lonely", "state": "AK", "lat": 60.0, "lng": -150.0, "type": "R"}]
    W = [{"id": "W1", "name": "Level", "state": "FL", "lat": 27.1, "lng": -82.0}, {"id": "W2", "name": "Level2", "state": "FL", "lat": 28.1, "lng": -82.0}]
    k = lambda kw, st, v="US": {"keyword": kw, "station": st, "verdict": v, "meant_place": "x"}
    got, why = pred_pick([k("ref tides", "R1"), k("ref tide times", "R1"), k("near tides", "S1"), k("far tides", "S2"), k("lonely tides", "R2"), k("kinsale tides", "R1", "FOREIGN")], P, W, set())
    assert [(a["keyword"], c["id"]) for a, b, c, d in got] == [("ref tides", "W1"), ("far tides", "W2")], got
    assert "subordinate" in why["near tides"] and "within 25" in why["lonely tides"] and "FOREIGN" in why["kinsale tides"] and "already" in why["ref tide times"], why
    print("coast_match pred selftest OK")
    sts = [{"id": "1", "name": "Biloxi", "state": "MS", "lat": 30.4, "lng": -88.9}, {"id": "2", "name": "Long Beach", "state": "CA", "lat": 0, "lng": 0},
           {"id": "3", "name": "Long Beach", "state": "WA", "lat": 0, "lng": 0}, {"id": "4", "name": "Portland", "state": "ME", "lat": 0, "lng": 0}]
    rows = [{"keyword": "biloxi tides", "tier": "5000", "gauge": ""}, {"keyword": "long beach tides", "tier": "5000", "gauge": ""},
            {"keyword": "portland tide times", "tier": "5000", "gauge": ""}, {"keyword": "biloxi tide chart", "tier": "50", "gauge": ""}]
    got, why = match(rows, sts, set())
    assert [s["id"] for _, s in got] == ["1"] and "2 NOAA" in why["long beach tides"] and "foreign" in why["portland tide times"], (got, why)
    print("coast_match selftest OK")


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else pred_main() if "--predictions" in sys.argv else main()
