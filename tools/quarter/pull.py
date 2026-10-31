# Report data pull. Key read from calcscrape .env, never printed. Output goes to scratchpad only.
import csv, json, os, re, time, urllib.request, urllib.parse, concurrent.futures as cf
OUT = "C:/Users/mwoo7/Desktop/riverwaterlevels/runs/quarter"
os.makedirs(OUT + "/live", exist_ok=True)
R = "C:/Users/mwoo7/Desktop/riverwaterlevels/"
key = None
for l in open("C:/Users/mwoo7/Desktop/calcscrape/.env", encoding="utf-8"):
    if l.startswith("USGS_API_KEY="):
        key = l.split("=", 1)[1].strip().strip('"\'')
UA = "riverwaterlevels.com (https://riverwaterlevels.com/about/)"


def get(url, h=None, t=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA, **(h or {})}), timeout=t).read()


rows = list(csv.DictReader(open(R + "data/waves.csv", encoding="utf-8")))
sites = [r["site"] for r in rows]
latest = {}
calls = 0
for i in range(0, len(sites), 300):
    nxt = "https://api.waterdata.usgs.gov/ogcapi/v1/collections/latest-continuous/items?monitoring_location_id=" + ",".join("USGS-" + s for s in sites[i:i + 300]) + "&parameter_code=00060,00065&skipGeometry=true&properties=monitoring_location_id,parameter_code,value,time,qualifier&limit=10000&f=json"
    while nxt:
        try:
            j = json.loads(get(nxt, {"X-Api-Key": key}))
        except Exception as e:
            print("usgs fail", i, type(e).__name__)
            break
        calls += 1
        for f in j.get("features", []):
            p = f["properties"]
            latest.setdefault(p["monitoring_location_id"][5:], {})[p["parameter_code"]] = [p.get("value"), p.get("time"), p.get("qualifier")]
        nxt = next((l["href"] for l in j.get("links", []) if l.get("rel") == "next"), None)
json.dump(latest, open(OUT + "/latest.json", "w"))
print("usgs calls", calls, "sites with data", len(latest), "of", len(sites))

try:
    b = get("https://api.water.noaa.gov/nwps/v1/gauges", t=170)
    open(OUT + "/nwps.json", "wb").write(b)
    print("nwps bytes", len(b))
except Exception as e:
    print("nwps fail", type(e).__name__, e)

sm = get("https://riverwaterlevels.com/sitemap.xml").decode()
urls = re.findall(r"<loc>(.*?)</loc>", sm)
print("sitemap urls", len(urls))


def page(u):
    try:
        b = get(u, t=40)
        n = re.sub(r"[^a-z0-9]+", "_", u.split(".com")[1].lower()).strip("_") or "home"
        open(OUT + "/live/" + n + ".html", "wb").write(b)
        return len(b)
    except Exception as e:
        print("page fail", u, e)
        return 0


with cf.ThreadPoolExecutor(6) as ex:
    print("html bytes", sum(ex.map(page, urls)))
