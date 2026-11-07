"""World gauge pages against the live PEGELONLINE feed (log only, as truth_live.py is for the US). The built number may lag an hour; a gap over 50 cm is a fault."""
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

UA = {"User-Agent": "riverwaterlevels.com truth check"}
BATCH = 40


LOCAL = sys.argv[sys.argv.index("--dir") + 1] if "--dir" in sys.argv else None  # readiness 2026-11-07: before deploy, built pages (dist_next) against the live feeds


def get(u):
    if LOCAL and u.startswith("https://riverwaterlevels.com/"):
        p = u[len("https://riverwaterlevels.com/"):].strip("/")
        return open(os.path.join(LOCAL, p) if p.endswith(".json") else os.path.join(LOCAL, p, "index.html"), encoding="utf-8").read()
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
    t = page_t(page)
    items = json.loads(get("https://environment.data.gov.uk/flood-monitoring/id/stations/%s/readings?parameter=level&%s" % (urllib.parse.quote(sid), ("since=%s&_sorted&_limit=20" % t) if t else "latest")))["items"]
    live = next((i["value"] for i in items if i.get("measure", "").endswith("-level-stage-i-15_min-mASD") and (not t or str(i.get("dateTime", "")).replace("+00:00", "Z") == t)), None)
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


def page_t(page):
    """The page's reading time as the feeds write it (2026-11-07T13:35:00Z), or None. Each feed is asked for that same minute: against the newest value,
    a river rising in rain (Squamish, 1.3 m in hours) read as a wrong page, and the older live copy would have replaced a right one."""
    m = re.search(r'data-live="age" data-t="([^"]+)"', page)
    if not m:
        return None
    import datetime
    return datetime.datetime.fromisoformat(m.group(1)).astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check(row):
    """Faults on one world page."""
    canada = "Canada" in str(row[4:5])
    page = get("https://riverwaterlevels.com" + row[1])
    if "England" in str(row[4:5]):
        return england(row, page)
    if canada:
        sid, shown = re.search(r'data-n="([^"]+)"', page).group(1), re.search(r'data-live="stage">(-?[\d.]+)', page)
        t = page_t(page)
        fs = json.loads(get("https://api.weather.gc.ca/collections/hydrometric-realtime/items?f=json&STATION_NUMBER=%s&limit=1&%sproperties=LEVEL" % (sid, ("datetime=%s&" % t) if t else "sortby=-DATETIME&")))["features"]
        live = fs[0]["properties"]["LEVEL"] if fs else None
        ok = not shown or live is None or abs(float(shown.group(1)) - live) <= 0.5  # "not reporting" is a true page; no feed value for the page's minute proves nothing
        print(row[1], shown.group(1) if shown else "not reporting", "feed", live, "ok" if ok else "FAULT")
        near = json.loads(get("https://api.weather.gc.ca/collections/weather-alerts/items?f=json&lang=en&limit=20&skipGeometry=true&properties=status_en&bbox=%.3f,%.3f,%.3f,%.3f" % (row[3] - .01, row[2] - .01, row[3] + .01, row[2] + .01)))["features"]
        live_al = [f for f in near if f["properties"].get("status_en") not in ("ended", "cancelled")]
        if live_al and "No active Environment Canada" in page:
            print(row[1], "FAULT page says no alerts, agency has", len(live_al))
            return 2 - bool(ok)
        return int(not ok) + canada_blocks(row, page)
    name, shown = re.search(r'data-n="([^"]+)"', page).group(1), re.search(r'data-live="stage">(-?\d+)', page)
    t = page_t(page)
    if t:
        ms = json.loads(get("https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations/%s/W/measurements.json?start=%s&end=%s" % (urllib.parse.quote(name), t, t)))
        cur = ms[0]["value"] if ms else None
    else:
        cur = json.loads(get("https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations/%s/W/currentmeasurement.json" % urllib.parse.quote(name)))["value"]
    ok = not shown or cur is None or abs(int(shown.group(1)) - cur) <= 50
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
    if not LOCAL:
        try:
            bad += moved(every)
        except Exception as e:
            print("station check skipped, no answer:", str(e)[:80])
    rows = [r for r in every if "Europe" in str(r[4:5]) or "Canada" in str(r[4:5]) or "England" in str(r[4:5])]
    start = int(time.time() // 3600) * BATCH % max(1, len(rows))
    faulty = []
    for row in (rows if LOCAL else (rows[start:] + rows[:start])[:BATCH]):  # ponytail: 40 a run after deploy; before deploy every world page, until the time limit
        if time.time() - begun > (420 if LOCAL else 180):  # a slow feed must not trip the step limit and read as a wrong number; ceiling: about 1 s a page, so past ~400 world pages the rest wait for the hourly run
            print("stopped at the time limit")
            break
        try:
            n_ = check(row)
        except Exception as e:  # a feed down proves nothing about the page: the page says its own age, and only a real mismatch counts
            print(row[1], "skipped, no answer:", str(e)[:80])
            continue
        bad += n_
        if n_:
            faulty.append(row[1])
    print("world truth: %d fault(s)" % bad)
    if LOCAL and faulty:
        return 0 if carry(faulty, len(rows)) else 1
    return 1 if bad else 0


def carry(urls, n):
    """Before deploy: each world page whose number does not match its agency keeps its live copy; a new page with none is left out of this build (the
    next build tries again). More than max(3, 5%) of world pages is a parser or feed fault for everyone: the deploy stops. True when the rest may ship."""
    import shutil
    if len(urls) > max(3, n // 20):
        print("world truth: %d pages disagree with their agency; the deploy stops" % len(urls))
        return False
    cp = os.path.join(LOCAL, "_carried.json")
    try:
        done = set(json.load(open(cp)))
    except (OSError, ValueError):
        done = set()
    for u in urls:
        dst = os.path.join(LOCAL, u.strip("/"), "index.html")
        try:
            html = urllib.request.urlopen(urllib.request.Request("https://riverwaterlevels.com" + u, headers=UA), timeout=30).read()
        except urllib.error.HTTPError as e:
            if e.code != 404:
                print("world truth: could not carry", u, str(e)[:60])
                return False
            print("NEW WORLD PAGE FAILED", u, "(its number did not match the agency; no live copy; this try stops and the release's second try is built without the new gauges)")
            return False  # release 2026-11-07: deleting a page left its links and sitemap entry and stopped the publish anyway
        except Exception as e:
            print("world truth: could not carry", u, str(e)[:60])
            return False
        open(dst, "wb").write(html)
        done.add(u.strip("/") + "/index.html")
        print("CARRIED previous live page for", u, "(its number did not match the agency)")
    json.dump(sorted(done), open(cp, "w"))
    return True


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
    pg = '<i data-n="08GA022"></i><b data-live="stage">1.73</b><span data-live="age" data-t="2026-11-07T05:35:00-08:00">'
    get = lambda u: pg if "/c/" in u else ('{"features": [{"properties": {"LEVEL": 1.731}}]}' if "datetime=2026-11-07T13:35:00Z" in u else '{"features": [{"properties": {"LEVEL": 3.046}}]}') if "hydrometric" in u else '{"features": []}'
    assert check([0, "/c/", 49.8, -123.2, "Canada"]) == 0, "a right page read against a newer reading (river rising) counted as wrong"
    get = lambda u: pg if "/c/" in u else ('{"features": [{"properties": {"LEVEL": 3.046}}]}' if "hydrometric" in u else '{"features": []}')
    assert check([0, "/c/", 49.8, -123.2, "Canada"]) == 1, "a wrong number at the page's own minute passed"
    assert carry(["/a/", "/b/", "/c/", "/d/"], 40) is False, "four of 40 world pages disagreeing did not stop the deploy"  # max(3, 5%) = 3
    get = real
    print("selftest OK")


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
