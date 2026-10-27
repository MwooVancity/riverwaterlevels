"""Planning-data download (not part of the site build): free federal data that the release score (tools/rescore.py) needs.
Writes to data/geo/ (raw sources are not committed, see .gitignore): gauge-geo.csv (USGS site coordinates for every gauge in data/pages-all.csv), wsr*.geojson (National Wild and Scenic River segments with recreation and fish values, NPS),
nri.geojson (Nationwide Rivers Inventory lines, NPS), places.csv (Census 2023 Gazetteer places with 2023 population estimates). Usage: python -I tools/fetch_geo.py [gauges|wsr|nri|places]
Sources are recorded in data/sources.json (planning inputs only; nothing here is shown on a page)."""
import csv, io, json, os, sys, time, urllib.parse, urllib.request, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "geo")
UA = {"User-Agent": "riverwaterlevels.com planning data (https://riverwaterlevels.com/about/)"}


def get(url, tries=3):
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()
        except Exception as e:
            err = e
            time.sleep(2 + 3 * i)
    raise err


def gauges():
    sites = [r["site"] for r in csv.DictReader(open(os.path.join(ROOT, "data", "pages-all.csv"), encoding="utf-8"))]
    rows = {}
    for i in range(0, len(sites), 100):
        chunk = sites[i:i + 100]
        # USGS Water Data API (waterservices.usgs.gov retires 2027-02-22)
        d = json.loads(get("https://api.waterdata.usgs.gov/ogcapi/v1/collections/monitoring-locations/items?id=%s&properties=monitoring_location_number,monitoring_location_name,hydrologic_unit_code&limit=500&f=json"
                           % ",".join("USGS-" + s for s in chunk)))
        for f in d.get("features", []):
            p, (lon, lat) = f["properties"], f["geometry"]["coordinates"][:2]
            rows[p["monitoring_location_number"]] = (lat, lon, p.get("hydrologic_unit_code"), p.get("monitoring_location_name"))
        print("gauges", min(i + 100, len(sites)), "/", len(sites), end="\r")
    with open(os.path.join(OUT, "gauge-geo.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["site", "lat", "lon", "huc", "usgs_name"])
        for s in sites:
            if s in rows:
                w.writerow([s] + list(rows[s]))
    print("\ngauge coordinates:", len(rows), "of", len(sites))


def arcgis(url, out, extra=""):
    feats, off = [], 0
    while True:
        q = url + "/query?where=1%3D1&outFields=*&outSR=4326&f=geojson&resultOffset=" + str(off) + "&resultRecordCount=1000" + extra
        d = json.loads(get(q))
        fs = d.get("features") or []
        feats += fs
        if len(fs) < 1000 and not d.get("exceededTransferLimit"):
            break
        off += len(fs) or 1000
        print(out, len(feats), end="\r")
    json.dump({"type": "FeatureCollection", "features": feats}, open(os.path.join(OUT, out), "w"))
    print("\n%s: %d features" % (out, len(feats)))


def places():
    z = zipfile.ZipFile(io.BytesIO(get("https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_place_national.zip")))
    gz = z.read(z.namelist()[0]).decode("utf-8", "replace").splitlines()
    head = [h.strip() for h in gz[0].split("\t")]
    pl = {}
    for l in gz[1:]:
        v = dict(zip(head, [x.strip() for x in l.split("\t")]))
        pl[v["GEOID"]] = (v["USPS"], v["NAME"], v["INTPTLAT"], v["INTPTLONG"])
    pop = {}
    txt = get("https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/cities/totals/sub-est2023.csv").decode("latin-1")
    for r in csv.DictReader(io.StringIO(txt)):
        if r["SUMLEV"] == "162":
            pop[r["STATE"].zfill(2) + r["PLACE"].zfill(5)] = int(r["POPESTIMATE2023"])
    with open(os.path.join(OUT, "places.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["geoid", "state", "name", "lat", "lon", "pop2023"])
        for g, (st, nm, la, lo) in pl.items():
            if g in pop:
                w.writerow([g, st, nm, la, lo, pop[g]])
    print("places with population:", sum(1 for g in pl if g in pop), "of", len(pl))


def main():
    os.makedirs(OUT, exist_ok=True)
    what = sys.argv[1:] or ["gauges", "wsr", "nri", "places"]
    if "gauges" in what:
        gauges()
    if "wsr" in what:
        base = "https://services1.arcgis.com/fBc8EJBxQRMcHlei/ArcGIS/rest/services/WildScenicRiversV2_AGOL/FeatureServer/"  # NPS: layer 3 = classified segments, 5 = recreation ORV, 7 = fish ORV (outstandingly remarkable values)
        arcgis(base + "3", "wsr.geojson")
        arcgis(base + "5", "wsr-recreation.geojson")
        arcgis(base + "7", "wsr-fish.geojson")
    if "nri" in what:
        arcgis("https://services1.arcgis.com/fBc8EJBxQRMcHlei/ArcGIS/rest/services/Nationwide_Rivers_Inventory_Official/FeatureServer/0", "nri.geojson")
    if "places" in what:
        places()


main()
