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


def england(row, page):
    """An English page against the Environment Agency: the stage now, and warnings by the agency's own map filter (areas within 10 m of the gauge), a path our point test never uses."""
    sid, shown = re.search(r'data-n="([^"]+)"', page).group(1), re.search(r'data-live="stage">(-?[\d.]+)', page)
    items = json.loads(get("https://environment.data.gov.uk/flood-monitoring/id/stations/%s/readings?latest&parameter=level" % urllib.parse.quote(sid)))["items"]
    live = next((i["value"] for i in items if i.get("measure", "").endswith("-level-stage-i-15_min-mASD")), None)
    ok = not shown or live is None or abs(float(shown.group(1)) - live) <= 0.5  # no live stage proves nothing; "not reporting" is a true page
    print(row[1], shown.group(1) if shown else "not reporting", "feed", live, "ok" if ok else "FAULT")
    near = [f for f in json.loads(get("https://environment.data.gov.uk/flood-monitoring/id/floods?lat=%.6f&long=%.6f&dist=0.01" % (row[2], row[3])))["items"] if f.get("severityLevel") in (1, 2, 3)]
    if near and "No flood warnings in force" in page:  # the agency's filter is wide (an area 1.3 km off Colwick came back, 2026-11-03): only an area the page's own rule covers is a fault
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import collect
        from lib import wx
        near = [f for f in near if wx.alerts_at(row[2], row[3], [{"rings": wx.ea_rings(json.loads(get("https://environment.data.gov.uk/flood-monitoring/id/floodAreas/%s/polygon" % f["floodAreaID"])))}], collect.EA_NEAR_M)]
    if near and "No flood warnings in force" in page:
        print(row[1], "FAULT page says no flood warnings, agency has", len(near))
        return 2 - bool(ok)
    return int(not ok)


def check(row):
    """Faults on one world page."""
    canada = "Canada" in str(row[4:5])
    page = get("https://riverwaterlevels.com" + row[1])
    if "England" in str(row[4:5]):
        return england(row, page)
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
        return int(not ok) + canada_blocks(row, page)
    name, shown = re.search(r'data-n="([^"]+)"', page).group(1), re.search(r'data-live="stage">(-?\d+)', page)
    cur = json.loads(get("https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations/%s/W/currentmeasurement.json" % urllib.parse.quote(name)))["value"]
    ok = not shown or abs(int(shown.group(1)) - cur) <= 50
    print(row[1], shown.group(1) if shown else "not reporting", "feed", cur, "ok" if ok else "FAULT")
    return int(not ok) + wt_block(name, page, row)


def block_text(page, bid):
    m = re.search(r'id="%s".*?</section>' % bid, page, re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(0))) if m else ""


def drought_gap(word, pixel):
    """Classes between the page and AAFC's raster, on a scale where no drought is -1. The raster is a coarser copy, so one class apart at an edge is normal."""
    d = re.search(r"\bD(\d)\b", word)
    return abs((int(d.group(1)) if d else -1) - (int(pixel) if str(pixel).isdigit() else -1))


def canada_blocks(row, page):
    """Drought against AAFC's raster service, a path our polygon code never touches, once the month's map is out; the January normal against ECCC, which must rest on at least 15 years."""
    bad = 0
    word = block_text(page, "drought_monitor")
    if word and time.gmtime().tm_mday >= 15:
        q = urllib.parse.quote(json.dumps({"x": row[3], "y": row[2], "spatialReference": {"wkid": 4326}}))
        v = json.loads(get("https://www.agr.gc.ca/imagery-images/rest/services/canadian_drought_monitor/ImageServer/identify?geometryType=esriGeometryPoint&returnGeometry=false&returnCatalogItems=false&f=json&geometry=" + q))["value"]
        if drought_gap(word, v) >= 2:
            print(row[1], "FAULT drought on the page differs from AAFC raster value", v)
            bad += 1
    txt = block_text(page, "climate_normals")
    m = re.search(r"station (.+?), \d+ km", txt)
    j = re.search(r"January (-?[\d.]+) ", txt)
    if m and j:
        rows = json.loads(get("https://api.weather.gc.ca/collections/climate-normals/items?f=json&limit=500&CURRENT_FLAG=Y&NORMAL_ID=1&MONTH=1&skipGeometry=true&properties=STATION_NAME,VALUE,YEAR_COUNT_NORMAL_PERIOD&bbox=%.3f,%.3f,%.3f,%.3f" % (row[3] - .7, row[2] - .5, row[3] + .7, row[2] + .5)))["features"]
        hit = [f["properties"] for f in rows if f["properties"]["STATION_NAME"].title() == m.group(1)]
        if hit and (abs(hit[0]["VALUE"] - float(j.group(1))) > 0.06 or (hit[0]["YEAR_COUNT_NORMAL_PERIOD"] or 0) < 15):
            print(row[1], "FAULT normal differs from ECCC or rests on too few years:", hit[0])
            bad += 1
    return bad


def wt_block(name, page, row):
    """The 30-day water temperature range against PEGELONLINE; the page may lag a day, so 1.5 degrees is allowed."""
    m = re.search(r"Lowest (-?[\d.]+) °C Highest (-?[\d.]+) °C", block_text(page, "water_temp_recent"))
    if not m:
        return 0
    pts = [p["value"] for p in json.loads(get("https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations/%s/WT/measurements.json?start=P30D" % urllib.parse.quote(name)))]
    if pts and (abs(min(pts) - float(m.group(1))) > 1.5 or abs(max(pts) - float(m.group(2))) > 1.5):
        print(row[1], "FAULT water temperature range differs from the feed", min(pts), max(pts))
        return 1
    return 0


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
    rows = [r for r in every if "Europe" in str(r[4:5]) or "Canada" in str(r[4:5]) or "England" in str(r[4:5])]
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
    en = [0, "/e/", 52.95, -1.08, "England UK"]
    get = lambda u: '<i data-n="4009"></i><b data-live="stage">3.05</b>' if "/e/" in u else '{"items": [{"measure": "x/4009-level-stage-i-15_min-mASD", "value": 1.05}]}' if "readings" in u else '{"items": []}'
    assert check(en) == 1, "a wrong English level passed"
    poly = lambda lat: '{"type": "Polygon", "coordinates": [[[-1.1, %s], [-1.0, %s], [-1.0, %s], [-1.1, %s], [-1.1, %s]]]}' % (lat, lat, lat + 1, lat + 1, lat)
    for lat, faults in ((52.9, 1), (53.5, 0)):
        get = lambda u: '<i data-n="4009"></i><b data-live="stage">1.05</b> No flood warnings in force' if "/e/" in u else '{"items": [{"measure": "x/4009-level-stage-i-15_min-mASD", "value": 1.07}]}' if "readings" in u else poly(lat) if "polygon" in u else '{"items": [{"severityLevel": 2, "floodAreaID": "A"}]}'
        assert check(en) == faults, "a page saying no warnings beside a live agency warning passed, or an area far off by the agency's wide filter alarmed"
    get = lambda u: '<i data-n="4009"></i><b data-live="stage">1.05</b> No flood warnings in force' if "/e/" in u else '{"items": [{"measure": "x/4009-level-stage-i-15_min-mASD", "value": 1.07}]}' if "readings" in u else '{"items": [{"severityLevel": 4}]}'
    assert check(en) == 0, "a true English page failed, or a warning no longer in force counted"
    assert drought_gap("Not in a mapped drought area", "2") == 3 and drought_gap("D2 Severe Drought", "1") == 1 and drought_gap("Not in a mapped", "NoData") == 0, "drought comparison wrong"
    get = lambda u: '{"features": [{"properties": {"STATION_NAME": "SEYMOUR FALLS", "VALUE": 9.9, "YEAR_COUNT_NORMAL_PERIOD": 1}}]}'
    assert canada_blocks([0, "/x/", 49.0, -123.0], '<section id="climate_normals">station Seymour Falls, 9 km January 9.9 °C</section>') == 1, "a one-year normal passed"
    get = lambda u: '[{"value": 5.0}, {"value": 20.0}]'
    assert wt_block("X", '<section id="water_temp_recent">Lowest 5.0 °C Highest 9.0 °C</section>', [0, "/x/"]) == 1, "a wrong water temperature range passed"
    get = lambda u: '{"features": [{"properties": {"monitoring_location_number": "01"}, "geometry": {"coordinates": [-72.0, 40.0]}}]}'
    assert moved([["n", "/u/", 40.0, -72.0, "Ohio OH 01"]]) == 0, "a gauge in place was called moved"
    assert moved([["n", "/u/", 41.0, -72.0, "Ohio OH 01"]]) == 1, "a moved gauge passed"
    assert moved([["n", "/u/", 41.0, -72.0, "Germany Europe"]]) == 0, "a world row reached USGS"
    get = real
    print("selftest OK")


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
