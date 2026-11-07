"""Match unlinked US tide keywords in data/world-queue.csv to NOAA CO-OPS stations that publish a live water level (queue audit 2026-11-07:
~135 US lake and coast rows at 1K+ had no station). Strict, so no page answers the wrong place (keyword debate 2026-11-07):
- the keyword's place must equal a station name (or the name before a comma/parenthesis), case-folded;
- exactly ONE water-level station in the whole NOAA list may carry that name (Long Beach x4 is refused);
- a name that is also a non-US tide place in the queue's foreign rows is refused (Plymouth, Portland, Dunedin...).
Prints proposed coasts.csv rows; --apply appends them. One NOAA call (the station list). Read-only without --apply."""
import csv, json, os, re, sys, urllib.request

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


def selftest():
    sts = [{"id": "1", "name": "Biloxi", "state": "MS", "lat": 30.4, "lng": -88.9}, {"id": "2", "name": "Long Beach", "state": "CA", "lat": 0, "lng": 0},
           {"id": "3", "name": "Long Beach", "state": "WA", "lat": 0, "lng": 0}, {"id": "4", "name": "Portland", "state": "ME", "lat": 0, "lng": 0}]
    rows = [{"keyword": "biloxi tides", "tier": "5000", "gauge": ""}, {"keyword": "long beach tides", "tier": "5000", "gauge": ""},
            {"keyword": "portland tide times", "tier": "5000", "gauge": ""}, {"keyword": "biloxi tide chart", "tier": "50", "gauge": ""}]
    got, why = match(rows, sts, set())
    assert [s["id"] for _, s in got] == ["1"] and "2 NOAA" in why["long beach tides"] and "foreign" in why["portland tide times"], (got, why)
    print("coast_match selftest OK")


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main()
