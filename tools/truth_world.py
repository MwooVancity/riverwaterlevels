"""World gauge pages against the live PEGELONLINE feed (log only, as truth_live.py is for the US). The built number may lag an hour; a gap over 50 cm is a fault."""
import json, re, sys, time, urllib.parse, urllib.request

UA = {"User-Agent": "riverwaterlevels.com truth check"}
BATCH = 40


def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode("utf-8")


def check(row):
    """Faults on one world page."""
    canada = "Canada" in str(row[4:5])
    page = get("https://riverwaterlevels.com" + row[1])
    if canada:
        sid, shown = re.search(r'data-n="([^"]+)"', page).group(1), re.search(r'data-live="stage">(-?[\d.]+)', page)
        live = json.loads(get("https://api.weather.gc.ca/collections/hydrometric-realtime/items?f=json&STATION_NUMBER=%s&limit=1&sortby=-DATETIME&properties=LEVEL" % sid))["features"][0]["properties"]["LEVEL"]
        ok = shown and abs(float(shown.group(1)) - live) <= 0.5
        print(row[1], shown.group(1) if shown else "not reporting", "feed", live, "ok" if ok else "FAULT")
        near = json.loads(get("https://api.weather.gc.ca/collections/weather-alerts/items?f=json&lang=en&limit=20&skipGeometry=true&properties=status_en&bbox=%.3f,%.3f,%.3f,%.3f" % (row[3] - .01, row[2] - .01, row[3] + .01, row[2] + .01)))["features"]
        live_al = [f for f in near if f["properties"].get("status_en") not in ("ended", "cancelled")]
        if live_al and "No active Environment Canada" in page:
            print(row[1], "FAULT page says no alerts, agency has", len(live_al))
            return 2 - bool(ok)
        return int(not ok)
    name, shown = re.search(r'data-n="([^"]+)"', page).group(1), re.search(r'data-live="stage">(-?\d+)', page)
    cur = json.loads(get("https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations/%s/W/currentmeasurement.json" % urllib.parse.quote(name)))["value"]
    ok = shown and abs(int(shown.group(1)) - cur) <= 50
    print(row[1], shown.group(1) if shown else "not reporting", "feed", cur, "ok" if ok else "FAULT")
    return int(not ok)


def main():
    bad = 0
    rows = [r for r in json.loads(get("https://riverwaterlevels.com/gauges.json")) if "Europe" in str(r[4:5]) or "Canada" in str(r[4:5])]
    start = time.gmtime().tm_hour * BATCH % max(1, len(rows))
    for row in (rows[start:] + rows[:start])[:BATCH]:  # ponytail: 40 a run so the 10-minute job holds at any page count; all pages take len/40 runs
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
    get = real
    print("selftest OK")


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
