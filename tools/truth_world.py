"""World gauge pages against the live PEGELONLINE feed (log only, as truth_live.py is for the US). The built number may lag an hour; a gap over 50 cm is a fault."""
import json, re, sys, urllib.parse, urllib.request

UA = {"User-Agent": "riverwaterlevels.com truth check"}


def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode("utf-8")


def main():
    bad = 0
    for row in json.loads(get("https://riverwaterlevels.com/gauges.json")):
        if "Europe" not in str(row[4:5]):
            continue
        page = get("https://riverwaterlevels.com" + row[1])
        name, shown = re.search(r'data-n="([^"]+)"', page).group(1), re.search(r'data-w="cm">(-?\d+)', page)
        cur = json.loads(get("https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations/%s/W/currentmeasurement.json" % urllib.parse.quote(name)))["value"]
        ok = shown and abs(int(shown.group(1)) - cur) <= 50
        print(row[1], shown.group(1) if shown else "not reporting", "feed", cur, "ok" if ok else "FAULT")
        bad += not ok
    print("world truth: %d fault(s)" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
