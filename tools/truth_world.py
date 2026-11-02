"""World gauge pages against the live PEGELONLINE feed (log only, as truth_live.py is for the US). The built number may lag an hour; a gap over 50 cm is a fault."""
import json, os, re, sys, time, urllib.parse, urllib.request

UA = {"User-Agent": "riverwaterlevels.com truth check"}
BATCH = 40


def get(u):
    key = {"X-Api-Key": os.environ["USGS_API_KEY"]} if "waterdata" in u and os.environ.get("USGS_API_KEY") else {}
    return urllib.request.urlopen(urllib.request.Request(u, headers=dict(UA, **key)), timeout=30).read().decode("utf-8")


def moved(rows):
    """US gauges whose USGS location sits over about 5 km from ours: a moved station is a wrong place. One call, 300 gauges a run, so every gauge within len/300 runs."""
    us = [(r[4].rsplit(" ", 1)[-1], r) for r in rows if str(r[4]).rsplit(" ", 1)[-1].isdigit()]
    start = int(time.time() // 3600) * 300 % max(1, len(us))
    part = dict((us[start:] + us[:start])[:300])
    if not part:
        return 0
    bad = 0
    for f in json.loads(get("https://api.waterdata.usgs.gov/ogcapi/v1/collections/monitoring-locations/items?id=%s&properties=monitoring_location_number&limit=500&f=json" % ",".join("USGS-" + s for s in part)))["features"]:
        r, (lon, lat) = part.get(f["properties"]["monitoring_location_number"]), f["geometry"]["coordinates"][:2]
        if r and abs(lat - r[2]) + abs(lon - r[3]) > 0.05:
            print(r[1], "FAULT USGS now places this gauge at", lat, lon, "we say", r[2], r[3])
            bad += 1
    return bad


def check(row):
    """Faults on one world page."""
    canada = "Canada" in str(row[4:5])
    page = get("https://riverwaterlevels.com" + row[1])
    if canada:
        sid, shown = re.search(r'data-n="([^"]+)"', page).group(1), re.search(r'data-live="stage">(-?[\d.]+)', page)
        live = json.loads(get("https://api.weather.gc.ca/collections/hydrometric-realtime/items?f=json&STATION_NUMBER=%s&limit=1&sortby=-DATETIME&properties=LEVEL" % sid))["features"][0]["properties"]["LEVEL"]
        ok = not shown or abs(float(shown.group(1)) - live) <= 0.5  # "not reporting" is a true page
        print(row[1], shown.group(1) if shown else "not reporting", "feed", live, "ok" if ok else "FAULT")
        near = json.loads(get("https://api.weather.gc.ca/collections/weather-alerts/items?f=json&lang=en&limit=20&skipGeometry=true&properties=status_en&bbox=%.3f,%.3f,%.3f,%.3f" % (row[3] - .01, row[2] - .01, row[3] + .01, row[2] + .01)))["features"]
        live_al = [f for f in near if f["properties"].get("status_en") not in ("ended", "cancelled")]
        if live_al and "No active Environment Canada" in page:
            print(row[1], "FAULT page says no alerts, agency has", len(live_al))
            return 2 - bool(ok)
        return int(not ok)
    name, shown = re.search(r'data-n="([^"]+)"', page).group(1), re.search(r'data-live="stage">(-?\d+)', page)
    cur = json.loads(get("https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations/%s/W/currentmeasurement.json" % urllib.parse.quote(name)))["value"]
    ok = not shown or abs(int(shown.group(1)) - cur) <= 50
    print(row[1], shown.group(1) if shown else "not reporting", "feed", cur, "ok" if ok else "FAULT")
    return int(not ok)


def main():
    bad = 0
    try:
        every = json.loads(get("https://riverwaterlevels.com/gauges.json"))
    except Exception as e:  # the watchdog's own checks cover a dead site
        print("no gauge list:", str(e)[:80])
        return 0
    begun = time.time()
    try:
        bad += moved(every)
    except Exception as e:
        print("station check skipped, no answer:", str(e)[:80])
    rows = [r for r in every if "Europe" in str(r[4:5]) or "Canada" in str(r[4:5])]
    start = int(time.time() // 3600) * BATCH % max(1, len(rows))
    for row in (rows[start:] + rows[:start])[:BATCH]:  # ponytail: 40 a run so the 10-minute job holds at any page count; all pages take len/40 runs
        if time.time() - begun > 180:  # a slow feed must not trip the step limit and read as a wrong number
            print("stopped at the time limit")
            break
        try:
            bad += check(row)
        except Exception as e:  # a feed down proves nothing about the page: the page says its own age, and only a real mismatch may email the owner
            print(row[1], "skipped, no answer:", str(e)[:80])
    print("world truth: %d fault(s)" % bad)
    return 1 if bad else 0


def selftest():
    global get
    real, get = get, lambda u: (_ for _ in ()).throw(OSError("down")) if "gauges.json" not in u else '[[0, "/x/", 1, 2, "Canada"]]'
    assert main() == 0, "a dead feed counted as a fault"
    get = lambda u: '[[0, "/x/", 1, 2, "Canada"]]' if "gauges.json" in u else '<i data-n="A"></i><b data-live="stage">9.0' if "/x/" in u else '{"features": [{"properties": {"LEVEL": 1.0}}]}'
    assert main() == 1, "a wrong number passed"
    get = lambda u: '{"features": [{"properties": {"monitoring_location_number": "01"}, "geometry": {"coordinates": [-72.0, 40.0]}}]}'
    assert moved([["n", "/u/", 40.0, -72.0, "Ohio OH 01"]]) == 0, "a gauge in place was called moved"
    assert moved([["n", "/u/", 41.0, -72.0, "Ohio OH 01"]]) == 1, "a moved gauge passed"
    assert moved([["n", "/u/", 41.0, -72.0, "Germany Europe"]]) == 0, "a world row reached USGS"
    get = real
    print("selftest OK")


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
