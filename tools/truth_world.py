"""World gauge pages against the live PEGELONLINE feed (log only, as truth_live.py is for the US). The built number may lag an hour; a gap over 50 cm is a fault."""
import json, re, sys, urllib.parse, urllib.request

UA = {"User-Agent": "riverwaterlevels.com truth check"}


def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode("utf-8")


def main():
    bad = 0
    for row in json.loads(get("https://riverwaterlevels.com/gauges.json")):
        canada = "Canada" in str(row[4:5])
        if "Europe" not in str(row[4:5]) and not canada:
            continue
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
                bad += 1
            bad += not ok
            continue
        name, shown = re.search(r'data-n="([^"]+)"', page).group(1), re.search(r'data-live="stage">(-?\d+)', page)
        cur = json.loads(get("https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations/%s/W/currentmeasurement.json" % urllib.parse.quote(name)))["value"]
        ok = shown and abs(int(shown.group(1)) - cur) <= 50
        print(row[1], shown.group(1) if shown else "not reporting", "feed", cur, "ok" if ok else "FAULT")
        bad += not ok
    print("world truth: %d fault(s)" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
