"""Collector: the only code that touches the network. Writes cache/<site>.json.
Each source is fetched independently; a failed source keeps its previous cached value (and old fetched_at), it never blanks the record.
Usage: python -I collect.py [site ...]   (default: wave 0)
"""
import os, sys, json, math, re, html, datetime, urllib.parse, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.common import *

CODES = "00060,00065,00010,00300,63680,00400,00095,99133,00045,00055,72255,00480"
BASE = "https://api.waterdata.usgs.gov/ogcapi/v1/collections/"
NWS_H = {"User-Agent": "riverwaterlevels.com (https://riverwaterlevels.com/about/)", "Accept": "application/geo+json"}
NWPS = "https://api.water.noaa.gov/nwps/v1/"
NWPS_H = {"User-Agent": NWS_H["User-Agent"], "Accept": "application/json"}  # 2026-10-26: geo+json made reaches/{id}/streamflow?series= return only the reach summary (no medium range on any gauge)


_last = [0.0]
import time as _time, zlib, copy
NEXT = os.environ.get("COLLECT_NEXT") == "1"  # shadow design (check branch): per-run memo of shared GETs, staggered 3-hourly NWS forecast, daily retry of gauges NWPS does not know. Off = today's behaviour exactly.
HOURLY_ONLY = "--hourly-only" in sys.argv  # shadow only: a gauge with no cache gets a seeded record with every slow source marked just-fetched, so the run measures the steady hourly cost
TIME = {}  # label -> [calls, seconds]; written to state/collect-timing.json (2026-10-29: the run log showed only the total)
MEMO = {}


def _tick(label, sec, n=1):
    c = TIME.setdefault(label, [0, 0.0])
    c[0] += n
    c[1] += sec


def _label(url):
    u = urllib.parse.urlparse(url)
    return u.netloc + "/" + "/".join("#" if re.search(r"\d", x) or len(x) > 20 else x for x in u.path.split("/") if x)[:70]


def _timed(fn):
    def w(url, *a, **k):
        t = _time.time()
        try:
            return fn(url, *a, **k)
        finally:
            _tick(_label(url), _time.time() - t)
    return w


http_json = _timed(http_json)


def thr_json(url, headers=None, timeout=60, gap=1.5, tries=6):
    """Throttled GET for the NWS/NOAA hosts: minimum gap between calls, honours Retry-After, exponential backoff on 429/5xx."""
    import time, urllib.error
    if NEXT and url in MEMO:  # the same forecast, grid or station URL asked for by two gauges of one run
        _tick("~memo hit", 0)
        return copy.deepcopy(MEMO[url])
    for i in range(tries):
        wait = gap - (time.time() - _last[0])
        if wait > 0:
            _tick("~gap sleep", wait, 0)
            time.sleep(wait)
        _last[0] = time.time()
        try:
            r = http_json(url, headers, timeout)
            if NEXT and "api.weather.gov" in url:
                MEMO[url] = r
            return r
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or i == tries - 1:
                raise
            ra = e.headers.get("Retry-After") or ""
            b = min(60, float(ra) if ra.replace(".", "", 1).isdigit() else 3 * 2 ** i)
            _tick("~backoff sleep", b)
            time.sleep(b)
    raise RuntimeError("unreachable")


def now_iso():
    return iso(datetime.datetime.now(datetime.timezone.utc))


def haversine(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(x))


def fetch_usgs(site, h):
    """All parameters in one request, following the API's next links (2026-10-25: was one request per parameter code, 12 per gauge, most empty, which used up the hourly key quota)."""
    rows, trunc, wrong = [], [], None
    url, pages = BASE + "continuous/items?monitoring_location_id=USGS-%s&parameter_code=%s&time=P8D&limit=10000&f=json" % (site, CODES), 0
    while url:
        d = http_json(url, h, 120)
        pages += 1
        url = next((l.get("href") for l in d.get("links", []) if l.get("rel") == "next"), None) if pages < 10 else None
        if url is None and pages >= 10:
            trunc.append("page cap")
        for f in d.get("features", []):
            p = f["properties"]
            if p.get("value") in (None, ""):
                continue
            if p.get("monitoring_location_id") not in (None, "USGS-" + site):  # the API filters by id; a row for another gauge is dropped, never shown
                wrong = p.get("monitoring_location_id")
                continue
            rows.append({k: p.get(k) for k in ("parameter_code", "time", "value", "unit_of_measure", "qualifier", "approval_status") if k in p})
    if not rows:
        raise RuntimeError("no USGS rows" + (" for USGS-%s (the API returned %s)" % (site, wrong) if wrong else ""))
    return {"fetched_at": now_iso(), "rows": rows, "truncated": trunc}


def fetch_related(site, inv, h, prev=None):
    out = []
    for nav, rel in (("UM", "upstream"), ("DM", "downstream")):
        try:
            d = http_json("https://api.water.usgs.gov/nldi/linked-data/nwissite/USGS-%s/navigation/%s/nwissite?f=json&distance=150" % (site, nav))
        except Exception as e:
            note("related.nldi", "failed", e)
            continue
        for f in d.get("features", []):
            sid = str(f["properties"].get("identifier", "")).replace("USGS-", "")
            if sid in inv and sid != site and sid not in [x["site"] for x in out]:
                out.append({"site": sid, "relation": rel})
    res, out = [], [x for x in out if x["relation"] == "upstream"][:6] + [x for x in out if x["relation"] == "downstream"][:6]
    lag0 = {x["site"]: x for x in ((prev or {}).get("items") or []) if x.get("lag_h")}
    got = {}
    if out:  # one bulk call for every neighbour (was one call each, up to 12 per gauge)
        try:
            for f in http_json(BASE + "latest-continuous/items?monitoring_location_id=%s&parameter_code=00060&limit=100&f=json" % ",".join("USGS-" + x["site"] for x in out), h).get("features", []):
                p = f["properties"]
                if p.get("value") not in (None, ""):
                    got[str(p.get("monitoring_location_id", ""))[5:]] = (float(p["value"]), p["time"])
        except Exception as e:
            note("related.latest", "failed", e)
    for x in out:
        if x["site"] in got:
            x["flow"], x["time"] = got[x["site"]]
            if x["site"] in lag0:  # related_lag refreshes these on its own timer
                x["lag_h"], x["lag_r"] = lag0[x["site"]]["lag_h"], lag0[x["site"]].get("lag_r")
            res.append(x)
    return {"fetched_at": now_iso(), "items": res}


def fetch_nwps(site, lat, lon, prev=None):
    """NWPS answers /gauges/<USGS id> directly; the returned usgsId must equal the gauge, so a coordinate match is never used."""
    import urllib.error, math
    if NEXT and isinstance(prev, dict) and prev.get("lid") is None and prev.get("fetched_at") and not due(prev["fetched_at"], 20 + zlib.crc32(site.encode()) % 8):
        return prev  # 404 from NWPS every hour for the ~3 in 4 gauges that have no forecast point; asked again daily, spread over 8 hours
    cw = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "nws-crosswalk.json"))).get(site)
    try:
        det = thr_json(NWPS + "gauges/%s" % site, NWPS_H)
    except urllib.error.HTTPError as e:
        if e.code not in (400, 404):
            raise
        det = None
        if cw:  # NWPS has the point but no usgsId on it: accept the crosswalk entry only when it sits within 1 km of this gauge
            det = thr_json(NWPS + "gauges/%s" % cw, NWPS_H)
            la1, lo1, la2, lo2 = map(math.radians, (lat, lon, det.get("latitude") or 0, det.get("longitude") or 0))
            km = 6371 * 2 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))
            if km > 1.0:
                det = None
            else:
                det["usgsId"] = site
        if not det:
            return {"fetched_at": now_iso(), "lid": None}
    if str(det.get("usgsId") or "") == site and det.get("lid"):
        x = {"lid": det["lid"]}
        if True:
            cats = {}
            for k, v in ((det.get("flood") or {}).get("categories") or {}).items():
                if isinstance(v, dict) and isinstance(v.get("stage"), (int, float)) and v["stage"] > -990:
                    cats[k] = v["stage"]
            p0 = prev if isinstance(prev, dict) and prev.get("lid") == x["lid"] else {}  # a failed sub-request keeps the previous value
            fc = p0.get("forecast")
            try:
                j = thr_json(NWPS + "gauges/%s/stageflow/forecast" % x["lid"], NWPS_H)
                fc = None
                pts = [{"t": p.get("validTime"), "primary": p.get("primary"), "secondary": p.get("secondary")} for p in (j.get("data") or []) if isinstance(p.get("primary"), (int, float)) and p["primary"] > -990]
                if pts:
                    fc = {"issued": j.get("issuedTime"), "primary_units": j.get("primaryUnits"), "secondary_units": j.get("secondaryUnits"), "points": pts[:400]}
            except Exception as e:
                note("nwps.forecast", "failed", e)
            rflow = p0.get("riverflow") or {}
            try:
                rf = thr_json(NWPS + "gauges/%s/riverflow" % x["lid"], NWPS_H)
                # NWPS lists upstream farthest first and downstream nearest first: keep the six nearest of each
                allp = {k: [{"LID": i.get("LID"), "Name": i.get("Name")} for i in (rf.get(k) or []) if isinstance(i, dict)] for k in ("upstream", "downstream")}
                rflow = {"upstream": allp["upstream"][-6:], "downstream": allp["downstream"][:6], "upstream_n": len(allp["upstream"]), "downstream_n": len(allp["downstream"])}
            except Exception as e:
                note("nwps.reach_flow", "failed", e)
            obs_stage, obs_series = p0.get("obs_stage"), p0.get("obs_series") or []
            try:
                ob = thr_json(NWPS + "gauges/%s/stageflow/observed" % x["lid"], NWPS_H)
                obs_stage, obs_series = None, []
                col = "primary" if (ob.get("primaryUnits") or "").lower() == "ft" else "secondary" if (ob.get("secondaryUnits") or "").lower() == "ft" else None  # the height column is found by its units, not its position
                pts = [p for p in (ob.get("data") or []) if col and isinstance(p.get(col), (int, float)) and p[col] > -900]
                if pts:
                    obs_stage = {"t": pts[-1]["validTime"], "v": pts[-1][col]}
                    t7 = datetime.datetime.fromisoformat(pts[-1]["validTime"].replace("Z", "+00:00")) - datetime.timedelta(days=7)
                    obs_series = [[p["validTime"], p[col]] for p in pts if datetime.datetime.fromisoformat(p["validTime"].replace("Z", "+00:00")) >= t7]
            except Exception as e:
                note("nwps.obs_stage", "failed", e)
            fl = det.get("flood") or {}
            hist = [{"t": c.get("occurredTime"), "stage": c.get("stage"), "flow": c.get("flow")} for c in ((fl.get("crests") or {}).get("historic") or []) if isinstance(c.get("stage"), (int, float))][:10]
            imp = [{"stage": i.get("stage"), "statement": demoji(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(i["statement"]))).strip())} for i in (fl.get("impacts") or []) if isinstance(i.get("stage"), (int, float)) and i.get("statement")]
            return {"fetched_at": now_iso(), "lid": x["lid"], "name": det.get("name"), "reach_id": det.get("reachId"), "categories": cats, "forecast": fc,
                    "riverflow": rflow, "obs_stage": obs_stage, "obs_series": obs_series, "stage_units": fl.get("stageUnits"), "crests": hist, "impacts": sorted(imp, key=lambda i: i["stage"]),
                    "wfo": det.get("wfo"), "rfc": det.get("rfc"), "reliability": det.get("forecastReliability"), "fim": bool((det.get("inundation") or {}).get("enabled")), "lro": fl.get("lro"),
                    "low_impacts": [{"value": str(i.get("value") or "").strip(), "impact": demoji(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(str(i.get("impact") or "")))).strip())} for i in (det.get("impactsLowWaters") or []) if isinstance(i, dict) and i.get("impact")],
                    "hydronotes": [{"text": demoji(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(str(h_.get("statement") or "")))).strip()), "from": h_.get("effective"), "to": h_.get("expiration")} for h_ in (det.get("hydronotes") or []) if isinstance(h_, dict) and h_.get("statement")],
                    "low_hist": [{"t": c.get("occurredTime"), "stage": c.get("stage"), "flow": c.get("flow")} for c in ((fl.get("lowWaters") or {}).get("historic") or []) if isinstance(c, dict) and isinstance(c.get("stage"), (int, float))][:10],
                    "status": {k: {"cat": ((det.get("status") or {}).get(k) or {}).get("floodCategory"), "t": ((det.get("status") or {}).get(k) or {}).get("validTime")} for k in ("observed", "forecast")}}
    return {"fetched_at": now_iso(), "lid": None}


def fetch_peaks(site, h):
    """USGS annual peak streamflow and peak stage of record, merged by date."""
    d = thr_json(BASE + "peaks/items?monitoring_location_id=USGS-%s&limit=1000&f=json" % site, h, 120)
    by = {}
    for f in d.get("features", []):
        q = f["properties"]
        try:
            v = float(q["value"])
        except (KeyError, TypeError, ValueError):
            continue
        k = {"00060": "flow", "00065": "stage"}.get(q.get("parameter_code"))
        if k and q.get("time"):
            by.setdefault(str(q["time"])[:10], {})[k] = v
            if k == "stage" and q.get("qualifier"):
                by[str(q["time"])[:10]]["sq"] = str(q["qualifier"])
    if not by:
        return None
    return {"fetched_at": now_iso(), "rows": [[t, v.get("flow"), v.get("stage"), v.get("sq")] for t, v in sorted(by.items())]}


def fetch_wtemp(site, h):
    """Mean of USGS daily-mean water temperature by calendar month across the record (needs 3+ years)."""
    d = thr_json(BASE + "daily/items?monitoring_location_id=USGS-%s&parameter_code=00010&statistic_id=00003&limit=50000&f=json" % site, h, 240)
    mon, yrs, n, seen_days = {}, set(), 0, set()
    for f in d.get("features", []):
        q = f["properties"]
        try:
            v, t = float(q["value"]), str(q["time"])[:10]
        except (KeyError, TypeError, ValueError):
            continue
        if t in seen_days:  # some gauges publish duplicate series for the same day
            continue
        seen_days.add(t)
        mon.setdefault(int(t[5:7]), []).append(v)
        yrs.add(t[:4])
        n += 1
    if len(yrs) < 3 or n < 300:
        return None
    return {"fetched_at": now_iso(), "years": len(yrs), "first_year": min(yrs), "last_year": max(yrs), "months": {str(m): [round(sum(v) / len(v), 1), len(v)] for m, v in sorted(mon.items())}}


def multiyear(rows, span=50, back=3):
    """Same calendar window of the daily-mean flow for this year and the previous `back` years (None for missing days)."""
    if len(rows) < 3650:
        return None
    D = datetime.date.fromisoformat
    last = D(rows[-1][0])
    if (datetime.date.today() - last).days > 10:
        return None
    val = dict((r[0], r[1]) for r in rows)
    out = {}
    for k in range(back + 1):
        end = last.replace(year=last.year - k) if not (last.month == 2 and last.day == 29) else last.replace(year=last.year - k, day=28)
        out[str(end.year)] = [val.get((end - datetime.timedelta(days=span - 1 - i)).isoformat()) for i in range(span)]
    if sum(1 for v in out[str(last.year)] if v is not None) < span * 0.8 or sum(1 for y, s in out.items() if y != str(last.year) and sum(1 for v in s if v is not None) >= span * 0.8) < 1:
        return None
    return {"as_of": last.isoformat(), "span": span, "series": out}


def hav_km(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))


def snotel_stations(h=None):
    p = os.path.join(CACHE, "_snotel_stations.json")
    if os.path.exists(p) and (datetime.datetime.now().timestamp() - os.path.getmtime(p)) < 7 * 86400:
        return json.load(open(p))
    j = http_json("https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1/stations?activeOnly=true&networkCds=SNTL&returnForecastPointMetadata=false&returnReservoirMetadata=false&returnStationElements=false", None, 120)
    st = [{k: x.get(k) for k in ("stationTriplet", "name", "latitude", "longitude", "elevation", "stateCode")} for x in j if str(x.get("stationTriplet", "")).endswith(":SNTL") and x.get("latitude") is not None]  # the service ignores networkCds
    json.dump(st, open(p, "w"), separators=(",", ":"))
    return st


def fetch_snotel(lat, lon, radius_km=60):
    """Snow water equivalent now and the station's median for the date, for the 3 nearest SNOTEL stations within radius_km."""
    near = sorted(((hav_km(lat, lon, s["latitude"], s["longitude"]), s) for s in snotel_stations()), key=lambda x: x[0])[:3]
    near = [(km, s) for km, s in near if km <= radius_km]
    if not near:
        return {"fetched_at": now_iso(), "stations": []}
    today = datetime.date.today()
    j = http_json("https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1/data?stationTriplets=%s&elements=WTEQ&duration=DAILY&beginDate=%s&endDate=%s&centralTendencyType=MEDIAN" % (
        urllib.parse.quote(",".join(s["stationTriplet"] for _, s in near)), (today - datetime.timedelta(days=6)).isoformat(), today.isoformat()), None, 60)
    got = {}
    for x in j:
        for d in x.get("data", []):
            vs = [v for v in d.get("values", []) if v.get("value") is not None]
            if vs:
                got[x["stationTriplet"]] = vs[-1]
    out = []
    for km, s in near:
        v = got.get(s["stationTriplet"])
        if v:
            out.append({"name": s["name"], "triplet": s["stationTriplet"], "state": s["stateCode"], "km": round(km), "elev_ft": s.get("elevation"), "date": v["date"], "swe_in": v["value"], "median_in": v.get("median")})
    return {"fetched_at": now_iso(), "stations": out}


def fetch_cpc(lat, lon, service="cpc_8_14_day_outlk"):
    g = urllib.parse.quote(json.dumps({"x": lon, "y": lat, "spatialReference": {"wkid": 4326}}))
    j = http_json("https://mapservices.weather.noaa.gov/vector/rest/services/outlooks/%s/MapServer/identify?geometry=%s&geometryType=esriGeometryPoint&sr=4326&layers=all:0,1&tolerance=1&mapExtent=-125,24,-66,50&imageDisplay=1000,500,96&returnGeometry=false&f=json" % (service, g), NWS_H)
    out = {"fetched_at": now_iso()}
    for r in j.get("results", []):
        a = r.get("attributes") or {}
        k = "temp" if r.get("layerId") == 0 else "precip"
        try:
            out[k] = {"category": a.get("Category"), "prob": int(float(a.get("Probability")))}
        except (TypeError, ValueError):
            continue
        out["start"], out["end"], out["issued"] = a.get("Start Date"), a.get("End Date"), a.get("Forecast Date")
    return out if ("temp" in out or "precip" in out) else None


STATE_FIPS = {"AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08", "CT": "09", "DE": "10", "DC": "11", "FL": "12", "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21",
              "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28", "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33", "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
              "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46", "TN": "47", "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53", "WV": "54", "WI": "55", "WY": "56"}


def fetch_usdm(rec):
    """U.S. Drought Monitor weekly county statistics (percent of county area in each category) for the county of the gauge; last 6 weeks."""
    ugc = (rec.get("nws") or {}).get("county_ugc") or ""
    if len(ugc) != 6 or ugc[:2] not in STATE_FIPS:
        return None
    fips = STATE_FIPS[ugc[:2]] + ugc[3:]
    today = datetime.date.today()
    j = http_json("https://usdmdataservices.unl.edu/api/CountyStatistics/GetDroughtSeverityStatisticsByAreaPercent?aoi=%s&startdate=%s&enddate=%s&statisticsType=1" % (
        fips, (today - datetime.timedelta(days=42)).strftime("%m/%d/%Y"), today.strftime("%m/%d/%Y")), {"Accept": "application/json"}, 60)
    rows = sorted(([r["mapDate"][:10], r["none"], r["d0"], r["d1"], r["d2"], r["d3"], r["d4"]] for r in j), reverse=True)
    if not rows:
        return None
    return {"fetched_at": now_iso(), "fips": fips, "county": j[0].get("county"), "state": j[0].get("state"), "rows": rows}


def fetch_attains(lat, lon):
    """EPA ATTAINS assessed river segments within about 400 m of the gauge (state water quality assessments)."""
    g = urllib.parse.quote(json.dumps({"x": lon, "y": lat, "spatialReference": {"wkid": 4326}}))
    ext = ",".join(str(round(v, 4)) for v in (lon - 0.05, lat - 0.05, lon + 0.05, lat + 0.05))
    j = http_json("https://gispub.epa.gov/arcgis/rest/services/OW/ATTAINS_Assessment/MapServer/identify?geometry=%s&geometryType=esriGeometryPoint&sr=4326&layers=all:0,1,2&tolerance=25&mapExtent=%s&imageDisplay=1000,1000,96&returnGeometry=false&f=json" % (g, ext), None, 90)
    units = {}
    for r in j.get("results", []):
        a = r.get("attributes") or {}
        k = a.get("Assessment Unit Identifier")
        if k and k not in units:
            units[k] = {"id": k, "name": a.get("Assessment Unit Name"), "state": a.get("State"), "cycle": a.get("Reporting Cycle"), "category": a.get("IR Category"), "status": a.get("Overall Status"),
                        "impaired": a.get("Is Impaired"), "on_303d": a.get("On 303d List"), "tmdl": a.get("Has TMDL"), "link": a.get("Waterbody Report Link")}
    return {"fetched_at": now_iso(), "units": list(units.values())[:6]}


def fetch_meta(site, h):
    """USGS monitoring-location facts and the period of record of each series."""
    loc = thr_json(BASE + "monitoring-locations/items?id=USGS-%s&f=json" % site, h, 60, gap=1.0)["features"][0]["properties"]
    keep = {k: loc.get(k) for k in ("monitoring_location_name", "agency_name", "site_type", "county_name", "state_name", "drainage_area", "altitude", "vertical_datum", "hydrologic_unit_code", "time_zone_abbreviation", "uses_daylight_savings", "state_code", "county_code")}
    ts = thr_json(BASE + "time-series-metadata/items?monitoring_location_id=USGS-%s&parameter_code=00060,00065&f=json&limit=50" % site, h, 60, gap=1.0)
    out = {}
    for f in ts.get("features", []):
        q = f["properties"]
        key = {("00060", "00003"): "flow_daily", ("00060", "00011"): "flow_inst", ("00065", "00011"): "stage_inst"}.get((q.get("parameter_code"), q.get("statistic_id")))
        if key and q.get("begin") and q.get("end"):
            b, e = str(q["begin"])[:10], str(q["end"])[:10]
            if key in out:
                b, e = min(b, out[key][0]), max(e, out[key][1])
            out[key] = [b, e]
    return {"fetched_at": now_iso(), "loc": keep, "ts": out}


def fetch_rating(site):
    """USGS expanded shifted rating table (gage height to flow), thinned to at most 90 points."""
    import urllib.request
    # NWISWeb get_ratings retires winter 2026-27; the USGS STAC file is the same file (byte-identical, checked 2026-10-27)
    req = urllib.request.Request("https://api.waterdata.usgs.gov/stac-files/ratings/USGS.%s.exsa.rdb" % site, headers={"User-Agent": "riverwaterlevels.com (https://riverwaterlevels.com/about/)"})
    txt = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "ignore")
    rows = [l.split("\t") for l in txt.split("\n") if l.strip() and not l.startswith("#")]
    if len(rows) < 3 or "INDEP" not in rows[0] or "DEP" not in rows[0]:
        return None
    ix, dx = rows[0].index("INDEP"), rows[0].index("DEP")
    pts = []
    for r in rows[2:]:
        try:
            pts.append([float(r[ix]), float(r[dx])])
        except (ValueError, IndexError):
            pass
    if len(pts) < 8:
        return None
    step = max(1, len(pts) // 90)
    thin = pts[::step]
    if thin[-1] != pts[-1]:
        thin.append(pts[-1])
    return {"fetched_at": now_iso(), "n": len(pts), "pts": thin}


def get_text(url, headers=None, timeout=90):
    import urllib.request
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers or {"User-Agent": "riverwaterlevels.com"}), timeout=timeout).read().decode("utf-8", "ignore")


get_text = _timed(get_text)


def county_codes(rec):
    loc = ((rec.get("meta") or {}).get("loc")) or {}
    if loc.get("state_code") and loc.get("county_code"):
        return str(loc["state_code"]).zfill(2), str(loc["county_code"]).zfill(3)
    ugc = (rec.get("nws") or {}).get("county_ugc") or ""
    if len(ugc) != 6 or ugc[:2] not in STATE_FIPS:
        return None
    return STATE_FIPS[ugc[:2]], ugc[3:]


def fetch_acis(rec):
    """NOAA RCC ACIS: measured daily rain at the five nearest county weather stations, last 7 days."""
    import urllib.request
    cc = county_codes(rec)
    if not cc:
        return None
    end = datetime.date.today()
    body = json.dumps({"county": cc[0] + cc[1], "sdate": (end - datetime.timedelta(days=6)).isoformat(), "edate": end.isoformat(), "elems": [{"name": "pcpn"}], "meta": "name,ll"}).encode()
    req = urllib.request.Request("https://data.rcc-acis.org/MultiStnData", data=body, headers={"Content-Type": "application/json", "User-Agent": "riverwaterlevels.com"})
    j = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    days = [(end - datetime.timedelta(days=6 - i)).isoformat() for i in range(7)]
    st = []
    for x in j.get("data", []):
        m = x.get("meta") or {}
        ll = m.get("ll")
        vals = [v[0] if isinstance(v, list) and v else v for v in (x.get("data") or [])]
        if not ll or len(vals) != 7 or sum(1 for v in vals if str(v)[:1].isdigit() or str(v) == "T") < 3:
            continue
        st.append({"name": m.get("name"), "km": round(hav_km(rec["lat"], rec["lon"], ll[1], ll[0]), 1), "vals": [str(v) for v in vals]})
    st.sort(key=lambda r: r["km"])
    return {"fetched_at": now_iso(), "days": days, "stations": st[:5]} if st else None


def fetch_streamcat(site, rec):
    """EPA StreamCat upstream-watershed metrics for the gauge's NHDPlus reach."""
    comid = rec.get("comid") or (rec.get("nwm") or {}).get("comid")
    if not comid:
        d = http_json("https://api.water.usgs.gov/nldi/linked-data/nwissite/USGS-%s?f=json" % site)
        comid = d["features"][0]["properties"].get("comid")
        rec["comid"] = comid
    names = "pctimp2019ws,pctcrop2019ws,pcturbmd2019ws,pctwdwet2019ws,elevws,bfiws,precip8110ws,runoffws,damdensws"
    base = ",".join(n[:-2] for n in names.split(","))  # the service takes base metric names and returns the cat and ws variants
    j = json.loads(get_text("https://api.epa.gov/StreamCat/streams/metrics?name=%s&comid=%s" % (base, comid)))
    row = j[0] if isinstance(j, list) else (j.get("items") or [j])[0] if isinstance(j, dict) else None
    if not row:
        return None
    vals = {k: row.get(k) for k in names.split(",") if isinstance(row.get(k), (int, float))}
    return {"fetched_at": now_iso(), "comid": comid, "vals": vals} if vals else None


STOCK_SOURCES = [
    # Per-state fish-stocking point layers. Each is one ArcGIS query by envelope around the gauge. Add a state = one entry (bbox gate, field map, credit). All verified to return point geometry + date + species + count.
    {"id": "mt", "name": "Montana FWP fish stocking records", "url": "https://fwp-gis.mt.gov/arcgis/rest/services/fish/fishViewer/MapServer/38/query",
     "bbox": (-116.1, 44.3, -104.0, 49.1), "credit": "Montana Fish, Wildlife & Parks",
     "f": {"species": "SPECIES", "date": "PLANTDATE", "num": "NUMFISH", "water": "WATERBODY", "size": "FISHSIZE"}},
    {"id": "md", "name": "Maryland DNR trout stocking", "url": "https://dnr.geodata.md.gov/dnrdata/rest/services/Fisheries/TroutStockingActivities/MapServer/0/query",
     "bbox": (-79.5, 37.8, -74.9, 39.8), "credit": "Maryland Department of Natural Resources",
     "f": {"species": "Species", "date": "ActivityDate", "num": "NumOfFish", "water": "LOCATION", "size": None}},
    {"id": "nd", "name": "North Dakota Game & Fish stocking", "url": "https://ndgishub.nd.gov/arcgis/rest/services/Applications/GNF_FishingWaters/MapServer/3/query",
     "bbox": (-104.2, 45.8, -96.5, 49.1), "credit": "North Dakota Game and Fish Department",
     "f": {"species": "Species", "date": "StockDate", "num": "Total_Stocked", "water": "Lake_Name", "size": "StockSizeDescription"}},
]


def fetch_stocking(lat, lon, miles=35):
    """Recent hatchery stocking near the gauge, from the state's public stocking layer (species, date, count, water). Returns None where the state has no adapter or no record. Stocking is a release event, not a fish-population measure."""
    for s in STOCK_SOURCES:
        x0, y0, x1, y1 = s["bbox"]
        if not (x0 <= lon <= x1 and y0 <= lat <= y1):
            continue
        fm, dd = s["f"], miles / 69.0
        q = urllib.parse.urlencode({"geometry": "%.4f,%.4f,%.4f,%.4f" % (lon - dd, lat - dd, lon + dd, lat + dd), "geometryType": "esriGeometryEnvelope", "inSR": "4326", "outSR": "4326",
                                    "spatialRel": "esriSpatialRelIntersects", "outFields": ",".join(v for v in fm.values() if v), "returnGeometry": "true", "resultRecordCount": "500", "f": "json"})
        j = json.loads(get_text(s["url"] + "?" + q))
        cut = (datetime.date.today() - datetime.timedelta(days=550)).isoformat()
        rows = []
        for ft in j.get("features", []):
            a, g = ft.get("attributes") or {}, ft.get("geometry") or {}
            d = a.get(fm["date"])
            iso = (datetime.datetime(1970, 1, 1) + datetime.timedelta(milliseconds=d)).date().isoformat() if isinstance(d, (int, float)) else (str(d)[:10] if d else "")
            if not iso or iso < cut:
                continue
            mi = round(hav_km(lat, lon, g["y"], g["x"]) * 0.621371, 1) if g.get("y") is not None and g.get("x") is not None else None
            if mi is not None and mi > miles:
                continue
            rows.append({"species": a.get(fm["species"]), "date": iso, "num": a.get(fm.get("num", "")), "water": a.get(fm.get("water", "")),
                         "size": a.get(fm["size"]) if fm.get("size") else None, "mi": mi})
        rows.sort(key=lambda r: r["date"], reverse=True)
        if rows:
            return {"fetched_at": now_iso(), "source": s["name"], "credit": s["credit"], "url": s["url"], "miles": miles, "rows": rows[:12]}
    return None


def fetch_access(lat, lon, radius_m=25000):
    """Boat ramps, canoe/kayak and whitewater put-ins and marinas near the gauge, from OpenStreetMap (Overpass). Where paddlers, anglers and boaters get on the water. ODbL, attributed."""
    parts = []
    for sel in ('node["leisure"="slipway"]', 'way["leisure"="slipway"]', 'node["canoe"="put_in"]', 'node["whitewater"="put_in"]', 'node["leisure"="marina"]', 'way["leisure"="marina"]'):
        parts.append("%s(around:%d,%.4f,%.4f);" % (sel, radius_m, lat, lon))
    q = "[out:json][timeout:25];(" + "".join(parts) + ");out center tags;"
    els = None
    for attempt in range(2):  # Overpass public API rate-limits (429); one polite retry, then leave it for the next 6 h run (the block self-hides)
        try:
            r = urllib.request.urlopen(urllib.request.Request("https://overpass-api.de/api/interpreter", data=urllib.parse.urlencode({"data": q}).encode(), headers={"User-Agent": "riverwaterlevels.com river gauge access points"}), timeout=50)
            els = json.loads(r.read().decode("utf-8", "replace")).get("elements", [])
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 0:
                import time
                time.sleep(8)
                continue
            raise
    if els is None:
        raise RuntimeError("Overpass gave no answer")
    rows = []
    for e in els:
        t = e.get("tags", {})
        y = e.get("lat") if e.get("lat") is not None else (e.get("center") or {}).get("lat")
        x = e.get("lon") if e.get("lon") is not None else (e.get("center") or {}).get("lon")
        if y is None or x is None:
            continue
        label = "Whitewater put-in" if t.get("whitewater") == "put_in" else "Canoe/kayak put-in" if t.get("canoe") == "put_in" else "Marina" if t.get("leisure") == "marina" else "Boat ramp"
        rows.append({"name": t.get("name"), "type": label, "mi": round(hav_km(lat, lon, y, x) * 0.621371, 1)})
    rows.sort(key=lambda r: (r["name"] is None, r["mi"]))  # named first, then nearest
    if not rows:
        return None
    return {"fetched_at": now_iso(), "count": len(rows), "rows": rows[:10]}






def fetch_floodfreq(site):
    """USGS StreamStats gage statistics: annual exceedance probability (AEP) peak flows with their published confidence intervals.
    Not shown (regulated=True or conflict=True) when the station is regulated or when USGS publishes more than one preferred set that disagree by over 10% at the 1% flow."""
    j = thr_json("https://streamstats.usgs.gov/gagestatsservices/stations/" + site, None, 60, gap=1.0)
    groups, dur = {}, {}
    for s in j.get("statistics") or []:
        md = re.match(r"^([\d.]+) Percent Duration$", (s.get("regressionType") or {}).get("name") or "")
        if s.get("statisticGroupTypeID") == 5 and md and s.get("value") is not None and (s.get("unitType") or {}).get("abbreviation") == "ft^3/s":
            p = float(md.group(1))  # flow-duration: the flow equalled or exceeded on this share of days
            if p not in dur or (s.get("isPreferred") and not dur[p]["pref"]):
                dur[p] = {"p": p, "q": s["value"], "pref": bool(s.get("isPreferred")), "range": " ".join(re.findall(r"\d{1,2}/\d{1,2}/\d{4}", s.get("comments") or "")[:2])}
            continue
        if s.get("statisticGroupTypeID") != 2:
            continue
        m = re.match(r"^(?:Alternate )?([\d.]+)-percent AEP flood$", (s.get("regressionType") or {}).get("name") or "")
        pi = s.get("predictionInterval") or {}
        if not m or s.get("value") is None or (s.get("unitType") or {}).get("abbreviation") != "ft^3/s":
            continue
        row = {"aep": float(m.group(1)), "q": s["value"], "lo": pi.get("lowerConfidenceInterval"), "hi": pi.get("upperConfidenceInterval"), "pref": bool(s.get("isPreferred")),
               "years": s.get("yearsofRecord"), "range": (s.get("comments") or ""), "cit": s.get("citation") or {}}
        g = groups.setdefault(s.get("citationID"), {})
        if row["aep"] not in g or (row["pref"] and not g[row["aep"]]["pref"]):
            g[row["aep"]] = row
    groups = {k: v for k, v in groups.items() if v}
    durs = sorted(dur.values(), key=lambda r: r["p"])
    if not groups:
        return {"fetched_at": now_iso(), "regulated": bool(j.get("isRegulated")), "rows": [], "dur": durs} if durs else None
    best = max(groups.values(), key=lambda g: (any(r["pref"] for r in g.values()), max(re.findall(r"\d{4}", next(iter(g.values()))["range"]) or ["0"]), len(g)))
    one = [g[1.0]["q"] for g in groups.values() if 1.0 in g and any(r["pref"] for r in g.values())]
    conflict = len(one) > 1 and max(one) > 1.1 * min(one)
    first = next(iter(best.values()))
    yrs = re.findall(r"\d{4}", first["range"])
    cit = first["cit"]
    return {"fetched_at": now_iso(), "regulated": bool(j.get("isRegulated")), "conflict": conflict, "range": ("%s to %s" % (yrs[0], yrs[1])) if len(yrs) >= 2 else None, "years": first["years"],
            "citation": cit.get("title"), "url": cit.get("citationURL"),
            "rows": sorted([{k: v for k, v in r.items() if k in ("aep", "q", "lo", "hi")} for r in best.values()], key=lambda r: -r["aep"]), "dur": durs}


def fetch_fieldmeas(site, h):
    """Latest USGS field measurements (discharge and gage height measured by staff on a site visit)."""
    d = thr_json(BASE + "field-measurements/items?monitoring_location_id=USGS-%s&limit=300&sortby=-time&f=json" % site, h, 90, gap=1.0)
    visits = {}
    for f in d.get("features", []):
        q = f["properties"]
        try:
            v = float(q["value"])
        except (KeyError, TypeError, ValueError):
            continue
        k = q.get("field_visit_id") or str(q.get("time"))[:16]
        row = visits.setdefault(k, {"t": str(q.get("time")), "flow": None, "stage": None, "rating": None})
        if q.get("parameter_code") == "00060":
            row["flow"], row["rating"] = v, q.get("measurement_rated") or row["rating"]
        elif q.get("parameter_code") == "00065":
            row["stage"] = v
    rows = sorted((r for r in visits.values() if r["flow"] is not None), key=lambda r: r["t"], reverse=True)[:12]
    return {"fetched_at": now_iso(), "rows": rows} if rows else None


def fetch_year(site, h):
    r = fetch_daily(site, h)
    return {"fetched_at": now_iso(), "rows": r[-366:]} if len(r) > 300 else None


def fetch_nwm(site, prev=None):
    d = http_json("https://api.water.usgs.gov/nldi/linked-data/nwissite/USGS-%s?f=json" % site)
    comid = d["features"][0]["properties"].get("comid")
    if not comid:
        return {"fetched_at": now_iso(), "comid": None}
    j = thr_json(NWPS + "reaches/%s/streamflow?series=short_range" % comid, NWPS_H)
    s = (j.get("shortRange") or {}).get("series") or {}
    pts = [{"t": p.get("validTime"), "flow": p.get("flow")} for p in (s.get("data") or []) if isinstance(p.get("flow"), (int, float)) and p["flow"] >= 0]
    out = {"fetched_at": now_iso(), "comid": comid, "reference_time": s.get("referenceTime"), "points": pts[:60]}
    try:
        m = thr_json(NWPS + "reaches/%s/streamflow?series=medium_range" % comid, NWPS_H)
        mm = (m.get("mediumRange") or {}).get("mean") or {}
        mp = [{"t": p.get("validTime"), "flow": p.get("flow")} for p in (mm.get("data") or []) if isinstance(p.get("flow"), (int, float)) and p["flow"] >= 0]
        if mp:
            out["medium"], out["medium_reference_time"] = mp[:120], mm.get("referenceTime") or (m.get("mediumRange") or {}).get("referenceTime")
        else:
            note("nwm.medium", "absent")
    except Exception as e:
        note("nwm.medium", "failed", e)
    if not out.get("medium") and (prev or {}).get("medium") and (prev or {}).get("comid") == out.get("comid"):
        out["medium"], out["medium_reference_time"] = prev["medium"], prev.get("medium_reference_time")
    return out


def grid_hours(gp, hours=168):
    """Expand NWS gridpoint interval values to one row per hour: temp, wind, gust, direction, sky cover and rain amount (mm per hour)."""
    keys = {"temperature": "temp_c", "windSpeed": "wind_kmh", "windGust": "gust_kmh", "windDirection": "dir", "skyCover": "sky", "quantitativePrecipitation": "qpf_mm", "probabilityOfThunder": "thunder", "relativeHumidity": "rh", "heatIndex": "heat_c", "visibility": "vis_m"}
    now = datetime.datetime.now(datetime.timezone.utc).replace(minute=0, second=0, microsecond=0)
    rows = [{"t": (now + datetime.timedelta(hours=i)).isoformat()} for i in range(hours)]
    for src, dst in keys.items():
        for iv in (gp.get(src) or {}).get("values", []):
            st, dur = iv["validTime"].split("/")
            st = parse_t(st)
            m = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?)?", dur)
            n = (int(m.group(1) or 0) * 24 + int(m.group(2) or 0)) if m else 1
            n = max(n, 1)
            v = iv.get("value")
            if v is None:
                continue
            for i, r in enumerate(rows):
                k = (parse_t(r["t"]) - st).total_seconds() / 3600
                if 0 <= k < n:
                    r[dst] = round(v / n, 2) if dst == "qpf_mm" else v
    return {"updated": gp.get("updateTime"), "hours": [r for r in rows if len(r) > 1]}


def nws_static(lat, lon, prev):
    """The /points lookup, the radar station position and the nearest observation station do not change: fetched once a week and kept in nws["static"] (sweep 2026-10-21: 3 of the 8 NWS calls per gauge per 30-min run were these)."""
    old = (prev.get("static") or {}) if isinstance(prev, dict) else {}
    try:
        if old.get("points") and old.get("station") and (datetime.datetime.now(datetime.timezone.utc) - parse_t(old["fetched_at"])).total_seconds() < 7 * 86400:
            return old
    except (TypeError, ValueError, KeyError):
        pass
    pt = thr_json("https://api.weather.gov/points/%.4f,%.4f" % (lat, lon), NWS_H).get("properties", {})
    out = {"fetched_at": now_iso(), "points": {k: pt.get(k) for k in ("timeZone", "county", "radarStation", "forecast", "forecastHourly", "forecastGridData", "observationStations")}, "radar_ll": old.get("radar_ll"), "station": old.get("station")}
    try:
        if pt.get("radarStation"):
            out["radar_ll"] = thr_json("https://api.weather.gov/radar/stations/%s" % pt["radarStation"], NWS_H).get("geometry", {}).get("coordinates")
    except Exception as e:
        note("nws.radar", "failed", e)
    try:
        st = thr_json(pt["observationStations"], NWS_H)["features"][0]
        out["station"] = {"id": st["id"], "name": (st.get("properties") or {}).get("name"), "ll": (st.get("geometry") or {}).get("coordinates")}
    except Exception as e:
        note("nws.station", "failed", e)
    return out


def fetch_nws(lat, lon, prev=None, site=""):
    S = nws_static(lat, lon, prev)
    pt = S["points"]
    out = {"fetched_at": now_iso(), "static": S, "tz": pt.get("timeZone"), "county_ugc": (pt.get("county") or "").rsplit("/", 1)[-1], "radar": pt.get("radarStation"), "radar_ll": S["radar_ll"], "periods": [], "alerts": None, "obs": None}
    p0 = prev if isinstance(prev, dict) else {}
    for k in ("periods", "forecast_updated", "hourly", "hourly_updated", "grid", "obs"):  # alerts are not carried: an old alert must never read as active
        if p0.get(k) is not None:
            out[k] = p0[k]
    slow = not NEXT or not p0.get("periods") or not p0.get("hourly") or not p0.get("grid") or (datetime.datetime.now(datetime.timezone.utc).hour + zlib.crc32(("%s%.3f" % (site, lon)).encode())) % 3 == 0  # first fetch, or this gauge's turn
    try:
        if not slow:
            raise StopIteration
        f = thr_json(pt["forecast"], NWS_H)["properties"]
        out["forecast_updated"] = f.get("updateTime") or f.get("generatedAt")
        out["periods"] = [{k: p.get(k) for k in ("name", "startTime", "endTime", "temperature", "temperatureUnit", "shortForecast", "detailedForecast", "windSpeed", "windDirection", "isDaytime")} | {"pop": (p.get("probabilityOfPrecipitation") or {}).get("value")} for p in f.get("periods", [])[:14]]
    except StopIteration:
        pass
    except Exception as e:
        note("nws.forecast", "failed", e)
    try:
        if not slow:
            raise StopIteration
        hf = thr_json(pt["forecastHourly"], NWS_H)["properties"]
        out["hourly_updated"] = hf.get("updateTime") or hf.get("generatedAt")
        out["hourly"] = [{k: p.get(k) for k in ("startTime", "temperature", "temperatureUnit", "shortForecast", "windSpeed", "windDirection")} | {"pop": (p.get("probabilityOfPrecipitation") or {}).get("value")} for p in hf.get("periods", [])[:36]]
    except StopIteration:
        pass
    except Exception as e:
        note("nws.hourly", "failed", e)
    try:
        if not slow:
            raise StopIteration
        gp = thr_json(pt["forecastGridData"], NWS_H)["properties"]
        out["grid"] = grid_hours(gp)
    except StopIteration:
        pass
    except Exception as e:
        note("nws.grid", "failed", e)
    try:
        a = thr_json("https://api.weather.gov/alerts/active?point=%.4f,%.4f" % (lat, lon), NWS_H)
        out["alerts"] = [dict({k: (x["properties"].get(k)) for k in ("event", "severity", "areaDesc", "headline", "ends", "expires", "senderName")},
                              states=sorted({u[:2] for u in ((x["properties"].get("geocode") or {}).get("UGC") or [])})) for x in a.get("features", [])]
    except Exception as e:
        note("nws.alerts", "failed", e)
    try:
        st = S["station"]
        o = thr_json(st["id"] + "/observations?limit=8", NWS_H)
        obs = [f["properties"] for f in o.get("features", []) if (f["properties"].get("temperature") or {}).get("value") is not None]
        if obs:
            x = obs[0]
            def v(k): return (x.get(k) or {}).get("value")
            old = next((y for y in obs if (y.get("barometricPressure") or {}).get("value") is not None and (parse_t(x["timestamp"]) - parse_t(y["timestamp"])).total_seconds() >= 2.5 * 3600), None)
            out["obs"] = {"name": st.get("name"), "ll": st.get("ll"), "station": st["id"].rsplit("/", 1)[-1], "timestamp": x["timestamp"], "temp_c": v("temperature"), "wind_kmh": v("windSpeed"), "wind_dir": v("windDirection"), "gust_kmh": v("windGust"),
                          "pressure_pa": v("barometricPressure"), "pressure_prev_pa": (old.get("barometricPressure") or {}).get("value") if old else None, "visibility_m": v("visibility")}
    except Exception as e:
        note("nws.obs", "failed", e)
    return out


MAPS = "https://mapservices.weather.noaa.gov/vector/rest/services/"


def esri_point(layer_url, lat, lon, where="1=1", fields="*", dist=None):
    q = {"where": where, "geometry": "%.4f,%.4f" % (lon, lat), "geometryType": "esriGeometryPoint", "inSR": "4326", "spatialRel": "esriSpatialRelIntersects", "outFields": fields, "returnGeometry": "false", "f": "json"}
    if dist:
        q.update({"distance": str(dist), "units": "esriSRUnit_StatuteMile"})
    j = http_json(layer_url + "/query?" + urllib.parse.urlencode(q))
    if "error" in j:
        raise RuntimeError("esri query error")
    return [f["attributes"] for f in j.get("features", [])]


def fetch_wpc(lat, lon):
    """WPC significant river flood outlook and excessive rainfall outlook (days 1 to 3) at the gauge point, and NWS flood or flash flood local storm reports within 50 miles in the last 72 h."""
    def ms(v):
        return datetime.datetime.fromtimestamp(v / 1000, datetime.timezone.utc).isoformat() if isinstance(v, (int, float)) else None
    outlooks = []
    for name, url in (("Significant river flood outlook", MAPS + "outlooks/sig_riv_fld_outlk/MapServer/0"), ("Excessive rainfall outlook, day 1", MAPS + "hazards/wpc_precip_hazards/MapServer/0"),
                      ("Excessive rainfall outlook, day 2", MAPS + "hazards/wpc_precip_hazards/MapServer/1"), ("Excessive rainfall outlook, day 3", MAPS + "hazards/wpc_precip_hazards/MapServer/2")):
        for a in esri_point(url, lat, lon):
            outlooks.append({"name": name, "category": a.get("outlook"), "issued": a.get("issue_time"), "start": a.get("start_time"), "end": a.get("end_time")})
    reports = []
    for a in esri_point(MAPS + "obs/nws_local_storm_reports/MapServer/2", lat, lon, where="descript IN ('Flash Flood','Flood')", dist=50):
        reports.append({"t": ms(a.get("lsr_validtime")), "type": a.get("descript"), "where": (a.get("loc_desc") or "").strip(), "state": a.get("state"), "office": a.get("wfo"),
                        "remarks": (a.get("remarks") or "").strip()[:220]})
    reports.sort(key=lambda r: r["t"] or "", reverse=True)
    return {"fetched_at": now_iso(), "outlooks": outlooks, "reports": reports[:8], "n_reports": len(reports)}


def _parse_issued(s):
    """The RFC QPE footprint's issue time, UTC. NOAA has sent it as '%m/%d/%Y %I:%M:%S %p', 24-hour, and date-only; try each and return None rather than raise, so a format change never loses the precip values."""
    for fmt in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %I:%M %p", "%m/%d/%Y"):
        try:
            return datetime.datetime.strptime(s, fmt).replace(tzinfo=datetime.timezone.utc).isoformat()
        except ValueError:
            continue
    return None


def fetch_rain(lat, lon):
    g = urllib.parse.quote(json.dumps({"x": lon, "y": lat, "spatialReference": {"wkid": 4326}}))
    j = http_json("https://mapservices.weather.noaa.gov/raster/rest/services/obs/rfc_qpe/MapServer/identify?geometry=%s&geometryType=esriGeometryPoint&sr=4326&layers=all:7,8,15,16,19,20,23,24,27,28,35,36,39,40&tolerance=1&mapExtent=-125,24,-66,50&imageDisplay=1000,500,96&returnGeometry=false&f=json" % g, NWS_H)
    by, issued, lid = {}, {}, {}
    for r in j.get("results", []):
        a = r.get("attributes") or {}
        if a.get("idp_issueddate"):  # each image layer N has a footprint layer N-1 carrying the product's issue (valid-through) time, UTC
            iss = _parse_issued(a["idp_issueddate"])  # tolerant: a date-only or reformatted value must not abort the whole precip fetch (NOAA changed the format 2026-10)
            if iss:
                issued[r["layerId"]] = iss
            continue
        try:
            v = float(a.get("Service Pixel Value"))
        except (TypeError, ValueError):
            continue
        if a.get("name") and v >= 0:
            by[a["name"]], lid[a["name"]] = v, r["layerId"]
    want = {"nws_precip_last24hours_conus": "last_24h", "nws_precip_last2days_conus": "last_2d", "nws_precip_last3days_conus": "last_3d"}
    vals = {lab: by[k] for k, lab in want.items() if k in by}
    if not vals:
        raise RuntimeError("no rain values")
    return {"fetched_at": now_iso(), "inches": vals, "valid_through": {lab: issued.get(lid[k] - 1) for k, lab in want.items() if k in by}}


def fetch_land(site):
    p = os.path.join(LEGACY, "land", site + ".json")
    if not os.path.exists(p):
        return None
    rows = json.load(open(p))
    rows = [x for x in rows if not (x[1] in ("UNK", "UNKL") and x[2] in ("UK", None))]
    return {"downloaded": datetime.date.fromtimestamp(os.path.getmtime(p)).isoformat(), "rows": rows}


def fetch_daily(site, h):
    """Full daily-mean flow record, pulled at most once per 20 h per gauge and stored gzipped under cache/daily/. The summary below is derived from it."""
    import gzip
    p = os.path.join(CACHE, "daily", site + ".json.gz")
    if os.path.exists(p) and (datetime.datetime.now().timestamp() - os.path.getmtime(p)) < 20 * 3600:
        return json.load(gzip.open(p, "rt"))
    rows = []

    def pull(extra):
        d = thr_json(BASE + "daily/items?monitoring_location_id=USGS-%s&parameter_code=00060&statistic_id=00003&limit=50000&f=json%s" % (site, extra), h, 240)
        feats = d.get("features", [])
        for f in feats:
            q = f["properties"]
            try:
                rows.append([str(q["time"])[:10], float(q["value"])])
            except (KeyError, TypeError, ValueError):
                pass
        return len(feats)
    if pull("") >= 50000:  # the API answers at most 50,000 rows, in no time order, and refuses paging past that: a record that long (St. Louis since 1861) is pulled in 40-year windows instead
        rows = []
        for y in range(1850, datetime.date.today().year + 1, 40):
            pull("&time=%d-01-01/%d-12-31" % (y, min(y + 39, datetime.date.today().year)))
    rows = [list(x) for x in sorted({r[0]: r for r in rows}.values())]
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(rows, gzip.open(p, "wt"), separators=(",", ":"))
    return rows


def record_summary(rows, stats):
    """Derived comparison of this week's flow with the gauge's own daily record (method id 'record-v1'). None when the record is too short or not current."""
    if len(rows) < 3650:
        return None
    D = datetime.date.fromisoformat
    last_d = D(rows[-1][0])
    if (datetime.date.today() - last_d).days > 6:
        return None
    recent = [r for r in rows if (last_d - D(r[0])).days < 7]
    pk_d, pk_v = max(recent, key=lambda r: r[1])
    pk_date = D(pk_d)
    before = [r for r in rows if (last_d - D(r[0])).days >= 7]  # every day before the 7-day window that holds the peak
    out = {"method": "record-v1", "computed_at": now_iso(), "first_year": int(rows[0][0][:4]), "last_year": int(rows[-1][0][:4]), "n_days": len(rows), "as_of": rows[-1][0], "peak": {"date": pk_d, "value": pk_v}}
    prior = [r for r in before if r[1] >= pk_v]
    out["prior"] = {"date": prior[-1][0], "value": prior[-1][1], "days_before": (pk_date - D(prior[-1][0])).days} if prior else None
    hi = None
    if stats:
        for dd, v in before:
            r = stats.get(dd[5:10])
            if r and r[8] is not None and v > r[8]:
                hi = dd
    out["last_p90"] = {"date": hi, "days_before": (pk_date - D(hi)).days} if hi else None
    n30 = [r for r in rows if 0 <= (last_d - D(r[0])).days < 30]
    if stats and len(n30) >= 25:
        out["above_p75"] = {"n": sum(1 for dd, v in n30 if stats.get(dd[5:10]) and stats[dd[5:10]][6] is not None and v > stats[dd[5:10]][6]), "of": len(n30)}
    else:
        out["above_p75"] = None
    m, dom = last_d.month, last_d.day
    yrs = {}
    for dd, v in rows:
        dt = D(dd)
        if dt.month == m and dt.day <= dom:
            yrs.setdefault(dt.year, []).append(v)
    full = {y: sum(v) / len(v) for y, v in yrs.items() if len(v) >= 0.8 * dom}
    if last_d.year in full and len(full) >= 20:
        out["month"] = {"month": last_d.strftime("%B"), "dom": dom, "mean": full[last_d.year], "rank": 1 + sum(1 for y, v in full.items() if v > full[last_d.year]), "years": len(full)}
    else:
        out["month"] = None
    return out


_COOPS = {}


def fetch_tides(lat, lon, miles=50):
    """NOAA CO-OPS tide predictions (public domain, attribution requested): the nearest harmonic prediction station within `miles`, today's and tomorrow's highs and lows."""
    if "st" not in _COOPS:
        j = json.loads(get_text("https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json?type=tidepredictions"))
        _COOPS["st"] = [(s["id"], s.get("name"), float(s["lat"]), float(s["lng"])) for s in j.get("stations", []) if s.get("lat") is not None]
    best = min(((haversine(lat, lon, a, b), i, n) for i, n, a, b in _COOPS["st"]), default=None)
    if not best or best[0] > miles:
        return None
    d0 = datetime.date.today()
    url = ("https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=predictions&station=%s&datum=MLLW&time_zone=lst_ldt&units=english&interval=hilo&begin_date=%s&end_date=%s&format=json"
           % (best[1], d0.strftime("%Y%m%d"), (d0 + datetime.timedelta(days=1)).strftime("%Y%m%d")))
    p = json.loads(get_text(url)).get("predictions") or []
    rows = [{"t": x["t"], "v": float(x["v"]), "type": x["type"]} for x in p if x.get("type") in ("H", "L")]
    return {"fetched_at": now_iso(), "station": best[1], "name": best[2], "mi": round(best[0], 1), "rows": rows} if rows else None


def fetch_near_wtemp(site, lat, lon, river, h):
    """When this gauge has no temperature sensor: the nearest USGS gauge on the same river (name match) reporting water temperature now, within about 40 miles."""
    if series_has(site, "00010", h):
        return None
    d = thr_json(BASE + "latest-continuous/items?parameter_code=00010&bbox=%.3f,%.3f,%.3f,%.3f&limit=400&f=json" % (lon - 0.6, lat - 0.6, lon + 0.6, lat + 0.6), h, 120)
    _skip = {"e", "w", "n", "s", "ne", "nw", "se", "sw", "east", "west", "north", "south", "fk", "fork", "little", "lt", "br", "branch", "middle", "m", "nf", "sf", "mf", "the", "lower", "upper"}
    word = next((w for w in re.findall(r"[a-z]+", (river or "").lower()) if w not in _skip and len(w) > 2), "")  # "E FK CARSON R" matches on carson, never on "e"
    cands = []
    for f in d.get("features", []):
        q, g = f["properties"], (f.get("geometry") or {}).get("coordinates") or []
        try:
            v, mi = float(q["value"]), haversine(lat, lon, float(g[1]), float(g[0]))
        except (KeyError, TypeError, ValueError, IndexError):
            continue
        if q.get("monitoring_location_id") == "USGS-" + site or mi > 40:
            continue
        cands.append((mi, q["monitoring_location_id"], v, q.get("time"), q.get("unit_of_measure")))
    for mi, sid, v, t, unit in sorted(cands)[:8]:
        m = thr_json(BASE + "monitoring-locations/items?id=%s&f=json" % sid, h, 60)
        name = ((m.get("features") or [{}])[0].get("properties") or {}).get("monitoring_location_name") or ""
        if word and re.search(r"\b%s\b" % re.escape(word), name.lower()) and (unit or "").lower() in ("degc", "deg c", "°c", "c", "degf", "deg f", "°f", "f"):
            c = v if (unit or "").lower() in ("degc", "deg c", "°c", "c") else (v - 32) * 5 / 9
            return {"fetched_at": now_iso(), "site": sid.replace("USGS-", ""), "name": name, "c": round(c, 1), "f": round(c * 9 / 5 + 32, 1), "t": t, "mi": round(mi, 1)}
    return None


def series_has(site, code, h):
    try:
        d = thr_json(BASE + "latest-continuous/items?monitoring_location_id=USGS-%s&parameter_code=%s&f=json" % (site, code), h, 60)
        return bool(d.get("features"))
    except Exception:
        raise  # unknown: the caller fails and keeps its previous value (never a guess)


def secret(name):
    """A key from the environment (CI secrets) or the owner's .env (lib.common.ENV_FILE), never logged or written to a page; '' when absent."""
    v = os.environ.get(name)
    if v:
        return v.strip()
    try:
        for l in open(ENV_FILE, encoding="utf-8-sig"):
            if l.startswith(name + "="):
                return l.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return ""


AQ_SITES = {}


def aq_sites():
    """AQS site id -> (lat, lon) from the AirNow monitoring-site file (public, keyless, about 4 MB), loaded once per run."""
    if not AQ_SITES:
        AQ_SITES[""] = None  # tried: a failed download is not retried for every gauge
        for l in get_text("https://files.airnowtech.org/airnow/today/Monitoring_Site_Locations_V2.dat").splitlines()[1:]:
            c = l.split("|")
            try:
                for k in c[:3]:  # AirNow returns either the 9-digit AQS id or the 12-digit full id
                    AQ_SITES[k] = (float(c[11]), float(c[12]), "%s County, %s" % (c[21].strip().title(), c[19].strip()))
            except (IndexError, ValueError):
                pass
    return AQ_SITES


def fetch_airnow(lat, lon):
    """EPA AirNow current observation nearest the gauge (service /aq/observation/current/ziplatlong/, the 2026-10-01 replacement): NowCast AQI per pollutant with its category and reporting agency. Needs AIRNOW_API_KEY."""
    k = secret("AIRNOW_API_KEY")
    if not k:
        return None
    j = json.loads(get_text("https://www.airnowapi.org/aq/observation/current/ziplatlong/?format=application/json&latitude=%.4f&longitude=%.4f&API_KEY=%s" % (lat, lon, k)))
    if not isinstance(j, list):
        return None
    rows = [{"pollutant": x.get("parameterName"), "aqi": x.get("nowcastAQI"), "category": x.get("aqiCategoryName"), "area": x.get("reportingAreaName"), "site": x.get("siteName"), "agency": x.get("reportingAgency"),
             "date": x.get("dateObserved"), "hour": x.get("hourObserved"), "tz": x.get("localTimeZone"), "id": x.get("siteID")} for x in j if isinstance(x, dict) and x.get("nowcastAQI") is not None]
    try:
        for r in rows:
            p = aq_sites().get(r["id"] or "") if r["id"] else None
            r["mi"] = round(haversine(lat, lon, p[0], p[1])) if p else None
            r["county"] = p[2] if p else None
    except Exception as e:
        note("airnow.sites", "failed", e)
    return {"fetched_at": now_iso(), "rows": rows} if rows else None


def fetch_ridb(lat, lon, radius_mi=15):
    """Recreation.gov RIDB: federal recreation facilities within radius_mi of the gauge (campgrounds, ramps, visitor centers, trailheads) with their listed activities. Needs RIDB_API_KEY (header apikey)."""
    k = secret("RIDB_API_KEY")
    if not k:
        return None
    j = json.loads(get_text("https://ridb.recreation.gov/api/v1/facilities?latitude=%.4f&longitude=%.4f&radius=%d&limit=50&full=true" % (lat, lon, radius_mi), {"apikey": k, "User-Agent": "riverwaterlevels.com"}))
    out = []
    for f in j.get("RECDATA") or []:
        try:
            flat, flon = float(f.get("FacilityLatitude")), float(f.get("FacilityLongitude"))
        except (TypeError, ValueError):
            continue
        acts = sorted({(a.get("ActivityName") or "").title() for a in f.get("ACTIVITY") or [] if a.get("ActivityName")})
        water = [a for a in acts if any(w in a.upper() for w in ("BOAT", "FISH", "PADDL", "SWIM", "KAYAK", "CANOE", "RAFT", "TUB", "WATER"))]
        typ = f.get("FacilityTypeDescription") or ""
        if not water and typ not in ("Campground",) and "ramp" not in (f.get("FacilityName") or "").lower():
            continue
        addr = (f.get("FACILITYADDRESS") or [{}])[0]
        out.append({"name": f.get("FacilityName"), "type": typ, "mi": round(haversine(lat, lon, flat, flon), 1), "activities": acts[:8], "water": water[:6],
                    "city": addr.get("City"), "phone": (f.get("FacilityPhone") or "").strip(), "url": f.get("FacilityReservationURL") or ("https://www.recreation.gov/camping/campgrounds/%s" % f["FacilityID"] if typ == "Campground" and f.get("FacilityID") else ""),
                    "id": f.get("FacilityID")})
    out.sort(key=lambda x: x["mi"])
    return {"fetched_at": now_iso(), "radius_mi": radius_mi, "sites": out[:12]} if out else None


def fetch_cameras(site, h):
    """USGS NIMS / HIVIS: the gaging-station cameras at this site (api.waterdata.usgs.gov/nims/v0, key sent in X-Api-Key), with the newest 720 px image URL, the thumbnail and the timelapse video."""
    import urllib.error
    try:
        cams = thr_json("https://api.waterdata.usgs.gov/nims/v0/cameras?siteId=%s" % site, h, 60)
    except urllib.error.HTTPError as e:
        if e.code == 404:  # the NIMS API answers 404 for a site with no camera: that is "none", not a failure
            return None
        raise
    out = []
    for c in (cams if isinstance(cams, list) else []):
        if c.get("hideCam") or not c.get("camId") or not c.get("smallDir"):
            continue
        files = thr_json("https://api.waterdata.usgs.gov/nims/v0/listFiles?camId=%s&limit=1&recent=true" % c["camId"], h, 60)
        fn = files[0] if isinstance(files, list) and files and isinstance(files[0], str) else None
        if not fn:
            continue
        out.append({"camId": c["camId"], "name": c.get("camName") or c["camId"], "taken": c.get("newestImageDT"), "tz": c.get("tz"),
                    "small": c["smallDir"] + fn, "thumb": (c.get("thumbDir") or c["smallDir"]) + fn,
                    "timelapse": (c["tlDir"] + c["camId"] + "_720.mp4") if c.get("TL_enabled") and c.get("tlDir") else None,
                    "page": "https://apps.usgs.gov/hivis/camera/%s" % c["camId"]})
    return {"fetched_at": now_iso(), "cams": out} if out else None


def default_sites():
    """Every gauge marked live in data/waves.csv (tracked in git): the scheduled refresh covers all of them, cache or no cache (sweep 2026-10-21: the live list must not depend on the CI cache surviving)."""
    import csv
    return sorted(r["site"] for r in csv.DictReader(open(os.path.join(os.path.dirname(CACHE), "data", "waves.csv"), encoding="utf-8")) if r["status"] == "live")


# Slow history and reference data: refreshed at most once a day (owner 2026-10-25), in the 09:00-12:00 UTC full run, after USGS has
# computed yesterday's daily values everywhere in CONUS and before eastern-morning readers. A value older than 36 h refreshes on any run.
DAILY = {"meta", "peaks", "wtemp", "snotel", "cpc", "cpc610", "usdm", "attains", "record", "year", "fieldmeas", "floodfreq", "acis",
         "ridb", "streamcat", "stocking", "access", "rating", "multiyear"}


RUN = {}  # ponytail: outcome counts per source for this process (one collect run per process); written by write_health()


def note(src, outcome, err=""):
    c = RUN.setdefault(src, {"ok": 0, "absent": 0, "failed": 0, "err": ""})
    c[outcome] += 1
    if err:
        c["err"] = str(err)[:80]


def run_source(rec, key, fn, log):
    """Fetch one source into rec[key]. A failure keeps the previous value AND is recorded as failed: kept-previous is never counted as success."""
    t0 = _time.time()
    try:
        v = fn()
    except Exception as e:
        _tick("src " + key, _time.time() - t0)
        log.append("%s FAILED (%s), kept previous" % (key, str(e)[:60]))
        note(key, "failed", e)
        return False
    _tick("src " + key, _time.time() - t0)
    rec[key] = v
    note(key, "ok" if v else "absent")
    return True


def write_health(mode, attempted):
    """state/source-health.json (published as /_health.json): every source's outcome on this run plus when it last worked and last failed, merged across runs, so a dead feed shows as hours since last_ok_at instead of hiding behind kept-previous data."""
    p = os.path.join(ROOT, "state", "source-health.json")
    try:
        prev = json.load(open(p)).get("sources") or {}
    except Exception:
        prev = {}
    now = now_iso()
    for src, c in RUN.items():
        old = prev.get(src) if isinstance(prev.get(src), dict) else {}
        s = {k: old[k] for k in ("last_ok_at", "last_fail_at", "last_error") if k in old}
        s["last_run"] = {"ok": c["ok"], "absent": c["absent"], "failed": c["failed"], "at": now, "mode": mode}
        if c["ok"]:
            s["last_ok_at"] = now
        if c["failed"]:
            s["last_fail_at"], s["last_error"] = now, c["err"]
        prev[src] = s
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump({"at": now, "mode": mode, "attempted": attempted, "sources": prev}, open(p, "w"), indent=1)


def daily_due(ts):
    if not ts:
        return True
    try:
        age = (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))).total_seconds() / 3600
    except ValueError:
        return True
    return age > 36 or (age > 12 and 9 <= datetime.datetime.now(datetime.timezone.utc).hour < 12)


def due(ts, hours):
    try:
        return (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))).total_seconds() > hours * 3600
    except (AttributeError, ValueError):
        return True


def nwm_due(rec):
    """Every gauge gets the model's days 1 to 10 (2026-10-26: it was fetched only where NWS issues no forecast, hiding days 4 to 10).
    The model reruns every 6 h; fetch at most every 3 h."""
    try:
        return (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(rec["nwm"]["fetched_at"])).total_seconds() > 3 * 3600
    except (KeyError, TypeError, ValueError):
        return True


def fetch_extras(site, rec, h, log):
    """Blocks added in the final-form pass. Each source is independent; a failure keeps the previous cached value."""
    lat, lon = rec["lat"], rec["lon"]
    for gone in ("echo", "openfema", "storms"):  # sources no page shows any more (owner 2026-10-20): drop them from caches restored from older runs
        rec.pop(gone, None)
    want = next((a[7:].split(",") for a in sys.argv if a.startswith("--keys=")), None)
    for key, fn in (("meta", lambda: fetch_meta(site, h)), ("peaks", lambda: fetch_peaks(site, h)), ("wtemp", lambda: fetch_wtemp(site, h)), ("snotel", lambda: fetch_snotel(lat, lon)), ("cpc", lambda: fetch_cpc(lat, lon)), ("usdm", lambda: fetch_usdm(rec)), ("attains", lambda: fetch_attains(lat, lon)),
                    ("record", lambda: record_summary(fetch_daily(site, h), rec.get("stats"))), ("year", lambda: fetch_year(site, h)), ("fieldmeas", lambda: fetch_fieldmeas(site, h)), ("floodfreq", lambda: fetch_floodfreq(site)), ("cpc610", lambda: fetch_cpc(lat, lon, "cpc_6_10_day_outlk")),
                    ("related", lambda: related_lag(rec, h)), ("acis", lambda: fetch_acis(rec)), ("tides", lambda: fetch_tides(lat, lon)), ("cameras", lambda: fetch_cameras(site, h)), ("airnow", lambda: fetch_airnow(lat, lon)), ("ridb", lambda: fetch_ridb(lat, lon)), ("near_wtemp", lambda: fetch_near_wtemp(site, lat, lon, rec.get("river_name"), h)),
                    ("streamcat", lambda: fetch_streamcat(site, rec)), ("stocking", lambda: fetch_stocking(lat, lon)), ("access", lambda: fetch_access(lat, lon)),
                    ("rating", lambda: fetch_rating(site)),
                    ("multiyear", lambda: multiyear(fetch_daily(site, h)))):
        if want and key not in want:
            continue
        stamp = rec.setdefault("_fetched", {})
        if not want and not (daily_due(stamp.get(key)) if key in DAILY else due(stamp.get(key), 24 if NEXT and key in ("related", "near_wtemp", "cameras") else 6)):
            continue
        if run_source(rec, key, fn, log) or (log and ("404" in log[-1] or "out of range" in log[-1])):  # collect review #7: a source this gauge does not have (404, empty list) waits for its timer, not every hourly run
            stamp[key] = now_iso()


def collect(site, inv):
    h = usgs_headers()
    path = os.path.join(CACHE, site + ".json")
    rec = json.load(open(path)) if os.path.exists(path) else {"site": site}
    g = inv[site]
    lat, lon = float(g["lat"]), float(g["lon"])
    rec["lat"], rec["lon"] = lat, lon
    rec["river_name"] = g.get("name")
    rec["usgs"] = fetch_usgs(site, h)  # critical: raises, cache kept
    log = []
    for key, fn in (("related", lambda: fetch_related(site, inv, h, rec.get("related"))), ("nwps", lambda: fetch_nwps(site, lat, lon, rec.get("nwps"))), ("nws", lambda: fetch_nws(lat, lon, rec.get("nws"), site)), ("rain", lambda: fetch_rain(lat, lon)), ("wpc", lambda: fetch_wpc(lat, lon))):
        run_source(rec, key, fn, log)
    if nwm_due(rec):
        run_source(rec, "nwm", lambda: fetch_nwm(site, rec.get("nwm")), log)
    sp = os.path.join(LEGACY, "stats", site + ".json")
    note("stats", "ok" if os.path.exists(sp) else "absent")  # input file, not a fetch: absent here means "is this normal" shows "-" (2026-10-25: 28 gauges)
    if os.path.exists(sp):
        rec["stats"] = json.load(open(sp))["d"]
        rec["stats_source"] = "USGS daily statistics, downloaded " + datetime.date.fromtimestamp(os.path.getmtime(sp)).isoformat()
    run_source(rec, "record", lambda: record_summary(fetch_daily(site, h), rec.get("stats")), log)
    fetch_extras(site, rec, h, log)
    land = fetch_land(site)
    note("land", "ok" if land else "absent")
    if land:
        rec["land"] = land
    rec["tz"] = (rec.get("nws") or {}).get("tz") or rec.get("tz")
    rec["fetched_at"] = now_iso()
    return rec, log


def hourly_flow(pairs):
    """UTC-hour means from (iso time, value) pairs, keyed by integer hours since the epoch."""
    by = {}
    for t, v in pairs:
        k = int(datetime.datetime.fromisoformat(str(t).replace("Z", "+00:00")).timestamp() // 3600)
        by.setdefault(k, []).append(v)
    return {k: sum(v) / len(v) for k, v in by.items()}


def pearson(a, b):
    n = len(a)
    if n < 2:
        return 0.0
    ma, mb = sum(a) / n, sum(b) / n
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((y - mb) ** 2 for y in b))
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb) if sa and sb else 0.0


def best_lag(mine, other, relation, max_lag=72):
    """Empirical shift (hours) that best aligns hourly flow at two gauges over the last 8 days; needs real variation, 96+ overlapping hours and r >= 0.85. Not a travel time."""
    for ser in (mine, other):
        vals = list(ser.values())
        if len(vals) < 120 or (sum(vals) / len(vals)) <= 0 or math.sqrt(sum((v - sum(vals) / len(vals)) ** 2 for v in vals) / len(vals)) / (sum(vals) / len(vals)) < 0.03:
            return None
    best = None
    for L in range(1, max_lag + 1):
        lead, lag = (other, mine) if relation == "upstream" else (mine, other)  # the upstream series leads
        ks = [k for k in lag if (k - L) in lead]
        if len(ks) < 96:
            continue
        r = pearson([lag[k] for k in ks], [lead[k - L] for k in ks])
        if best is None or r > best[1]:
            best = (L, r)
    return (best[0], round(best[1], 2)) if best and best[1] >= 0.85 else None


def related_lag(rec, h):
    items = (rec.get("related") or {}).get("items") or []
    mine = hourly_flow([(r["time"], float(r["value"])) for r in rec["usgs"]["rows"] if r["parameter_code"] == "00060"])
    done = {"upstream": 0, "downstream": 0}
    for x in items:
        x.pop("lag_h", None)
        x.pop("lag_r", None)
        if done[x["relation"]] >= 3:
            continue
        done[x["relation"]] += 1
        d = thr_json(BASE + "continuous/items?monitoring_location_id=USGS-%s&parameter_code=00060&time=P8D&limit=4000&f=json" % x["site"], h, 120, gap=1.0)
        other = hourly_flow([(f["properties"]["time"], float(f["properties"]["value"])) for f in d.get("features", []) if f["properties"].get("value") not in (None, "")])
        got = best_lag(mine, other, x["relation"])
        if got:
            x["lag_h"], x["lag_r"] = got
    return rec["related"]


def fast_related(recs, h):
    """Refresh latest flow of every upstream/downstream gauge in the caches with bulk latest-continuous calls (40 ids per call)."""
    ids = sorted({x["site"] for r in recs.values() for x in (r.get("related") or {}).get("items") or []})
    got = {}
    for i in range(0, len(ids), 40):
        d = thr_json(BASE + "latest-continuous/items?monitoring_location_id=%s&parameter_code=00060&limit=1000&f=json" % ",".join("USGS-" + x for x in ids[i:i + 40]), h, 120, gap=1.0)
        for f in d.get("features", []):
            p = f["properties"]
            if p.get("value") not in (None, ""):
                got[p["monitoring_location_id"][5:]] = (float(p["value"]), p["time"])
    for r in recs.values():
        for x in (r.get("related") or {}).get("items") or []:
            if x["site"] in got:
                x["flow"], x["time"] = got[x["site"]]


def fast_usgs(sites, h):
    """Every reading of the last 3 hours for every gauge, in bulk: 300 ids per call (URL stays ~5 KB) with next-link paging, so
    nothing is dropped past 10,000 rows. Rows in the same shape as fetch_usgs. One or two calls at today's size; it replaces the
    per-gauge fast_fill calls (2026-10-25 review: about one call per gauge per run, ~18,000/h at 9,099 gauges)."""
    out = {}
    for i in range(0, len(sites), 300):
        url, pages = BASE + "continuous/items?monitoring_location_id=%s&parameter_code=%s&time=PT3H&limit=10000&skipGeometry=true&f=json" % (",".join("USGS-" + s for s in sites[i:i + 300]), CODES), 0
        while url and pages < 20:
            try:
                d = thr_json(url, h, 120, gap=1.0)
            except Exception as e:  # this chunk's gauges get no new rows this run; the others keep theirs
                note("usgs.chunk", "failed", e)
                break
            pages += 1
            for f in d.get("features", []):
                p = f["properties"]
                if p.get("value") in (None, ""):
                    continue
                out.setdefault(str(p.get("monitoring_location_id", ""))[5:], []).append({k: p.get(k) for k in ("parameter_code", "time", "value", "unit_of_measure", "qualifier", "approval_status") if k in p})
            url = next((l.get("href") for l in d.get("links", []) if l.get("rel") == "next"), None)
        if url:
            note("usgs.chunk", "failed", "20-page cap reached: later rows of this chunk wait for the next run")
    return out


SLOW_KEYS = sorted(DAILY | {"related", "tides", "cameras", "airnow", "near_wtemp"}) + ["usgs_full", "related_list"]


def seed_record(s, inv, rows):
    """Shadow only: the record a gauge would have after its first full collect, minus the slow sources (all marked just fetched), so a run measures the steady hourly cost."""
    now = now_iso()
    g = inv[s]
    nwm_age = 4 if zlib.crc32(s.encode()) % 3 == 0 else 1  # a third of the gauges are due for the 3-hourly model each run
    return {"site": s, "lat": float(g["lat"]), "lon": float(g["lon"]), "river_name": g.get("name"), "usgs": {"fetched_at": now, "rows": [], "truncated": []},
            "_fetched": {k: now for k in SLOW_KEYS}, "nwm": {"fetched_at": iso(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=nwm_age)), "comid": None}}


def fast(inv, sites):
    h = usgs_headers()
    t_phase = _time.time()
    try:
        new = fast_usgs(sites, h)
    except Exception as e:  # USGS unavailable or rate-limited: still refresh the weather sources
        print("FAIL usgs bulk", str(e)[:100])
        note("usgs", "failed", e)
        new = {}
    _tick("phase usgs bulk", _time.time() - t_phase)
    t_phase = _time.time()
    for s in sites:
        try:  # collect review #3: one gauge's bad cache or locked file is that gauge's failure, never the whole run's
            path = os.path.join(CACHE, s + ".json")
            if not os.path.exists(path) and not HOURLY_ONLY:  # a new live gauge: its first run is a full collect
                try:
                    rec, log = collect(s, inv)
                except Exception as e:
                    print("FAIL new gauge", s, str(e)[:100], "(retried next run)")
                    note("usgs", "failed", e)
                    continue
                note("usgs", "ok")
                json.dump(rec, open(path + ".tmp", "w"), separators=(",", ":"))
                os.replace(path + ".tmp", path)
                print("ok new gauge", s, "; ".join(log))
                continue
            rec, log = (json.load(open(path)) if os.path.exists(path) else seed_record(s, inv, new.get(s))), []
            have = {(r["parameter_code"], r["time"]) for r in rec["usgs"]["rows"]}
            add = [r for r in new.get(s, []) if (r["parameter_code"], r["time"]) not in have]
            cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=8)).isoformat()
            rec["usgs"]["rows"] = [r for r in rec["usgs"]["rows"] + add if str(r["time"]) >= cutoff]
            if add:
                rec["usgs"]["fetched_at"] = now_iso()
            note("usgs", "ok" if s in new else "absent")
            for key, fn in (("nwps", lambda: fetch_nwps(s, rec["lat"], rec["lon"], rec.get("nwps"))), ("nws", lambda: fetch_nws(rec["lat"], rec["lon"], rec.get("nws"), s)), ("rain", lambda: fetch_rain(rec["lat"], rec["lon"])), ("wpc", lambda: fetch_wpc(rec["lat"], rec["lon"]))):
                run_source(rec, key, fn, log)
            if nwm_due(rec):
                run_source(rec, "nwm", lambda: fetch_nwm(s, rec.get("nwm")), log)
            stamp = rec.setdefault("_fetched", {})
            if daily_due(stamp.get("usgs_full")):  # once a day the whole 8-day series again: USGS revises provisional readings
                try:
                    rec["usgs"], stamp["usgs_full"] = fetch_usgs(s, h), now_iso()
                except Exception as e:
                    log.append("usgs_full FAILED (%s), kept previous" % str(e)[:60])
                    note("usgs_full", "failed", e)
            if daily_due(stamp.get("related_list")) and run_source(rec, "related", lambda: fetch_related(s, inv, h, rec.get("related")), log):
                stamp["related_list"] = now_iso()
            sp = os.path.join(LEGACY, "stats", s + ".json")
            if os.path.exists(sp):
                rec["stats"] = json.load(open(sp))["d"]
                rec["stats_source"] = "USGS daily statistics, downloaded " + datetime.date.fromtimestamp(os.path.getmtime(sp)).isoformat()
            fetch_extras(s, rec, h, log)
            land = fetch_land(s)
            if land:
                rec["land"] = land
            rec["tz"] = (rec.get("nws") or {}).get("tz") or rec.get("tz")
            rec["fetched_at"] = now_iso()
            json.dump(rec, open(path + ".tmp", "w"), separators=(",", ":"))
            os.replace(path + ".tmp", path)
            print("ok", s, "new usgs rows", len(add), "; ".join(log))
        except Exception as e:
            print("FAIL gauge", s, type(e).__name__, str(e)[:100], "(its previous cache stays)")
            note("gauge", "failed", e)
    _tick("phase per-gauge sources", _time.time() - t_phase)
    t_phase = _time.time()
    recs = {s: json.load(open(os.path.join(CACHE, s + ".json"))) for s in sites if os.path.exists(os.path.join(CACHE, s + ".json"))}
    try:
        fast_related(recs, h)
        for s, r in recs.items():
            json.dump(r, open(os.path.join(CACHE, s + ".json.tmp"), "w"), separators=(",", ":"))
            os.replace(os.path.join(CACHE, s + ".json.tmp"), os.path.join(CACHE, s + ".json"))
        print("ok fast related flows")
    except Exception as e:
        print("FAIL related flows", str(e)[:100])
    _tick("phase related flows", _time.time() - t_phase)
    write_health("run", len(sites))
    t_phase = _time.time()
    fetch_states(sites)  # statewide alerts + drought for each state hub
    _tick("phase state hubs", _time.time() - t_phase)


STATE_FIPS = {"AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08", "CT": "09", "DE": "10", "DC": "11", "FL": "12", "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21", "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28", "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33", "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39", "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46", "TN": "47", "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53", "WV": "54", "WI": "55", "WY": "56"}


def fetch_state(st):
    """Statewide conditions for a state hub: active NWS alerts and the latest U.S. Drought Monitor percentages. Both public, sourced, no verdict."""
    out = {"st": st, "fetched_at": now_iso()}
    try:
        j = json.loads(get_text("https://api.weather.gov/alerts/active?area=%s" % st, {"User-Agent": "riverwaterlevels.com (https://riverwaterlevels.com/about/)", "Accept": "application/geo+json"}, 60))
        ev = {}
        for f in j.get("features", []):
            e = (f.get("properties") or {}).get("event")
            if e:
                ev[e] = ev.get(e, 0) + 1
        out["alerts"] = {"n": sum(ev.values()), "events": sorted(ev.items(), key=lambda kv: -kv[1])}
    except Exception as e:
        out["alerts_err"] = str(e)[:80]
    fips = STATE_FIPS.get(st.upper())
    if fips:
        try:
            end = datetime.date.today()
            start = end - datetime.timedelta(days=28)
            url = "https://usdmdataservices.unl.edu/api/StateStatistics/GetDroughtSeverityStatisticsByAreaPercent?aoi=%s&startdate=%s&enddate=%s&statisticsType=1" % (fips, start.strftime("%m/%d/%Y"), end.strftime("%m/%d/%Y"))
            rows = json.loads(get_text(url, {"Accept": "application/json", "User-Agent": "riverwaterlevels.com"}, 60))
            if rows:
                r0 = rows[0]
                out["drought"] = {"mapDate": str(r0.get("mapDate"))[:10], "none": r0.get("none"), "d0": r0.get("d0"), "d1": r0.get("d1"), "d2": r0.get("d2"), "d3": r0.get("d3"), "d4": r0.get("d4")}
        except Exception as e:
            out["drought_err"] = str(e)[:80]
    return out


def states_of(sites):
    """States that have at least one of these gauges, from the page rows (data/pages-all.csv)."""
    import csv
    want, out = set(sites), set()
    try:
        for r in csv.DictReader(open(os.path.join(ROOT, "data", "pages-all.csv"), encoding="utf-8")):
            if r.get("site") in want and r.get("state"):
                out.add(r["state"])
    except Exception as e:
        print("states_of FAILED", str(e)[:80])
    return out


def fetch_states(sites):
    for st in sorted(states_of(sites)):
        try:
            d = fetch_state(st)
            p = os.path.join(CACHE, "state-%s.json" % st.lower())
            json.dump(d, open(p + ".tmp", "w"), separators=(",", ":"))
            os.replace(p + ".tmp", p)
            print("ok state", st, "alerts", (d.get("alerts") or {}).get("n"), "drought D1+%", (d.get("drought") or {}).get("d1"))
        except Exception as e:
            print("FAIL state", st, str(e)[:80])


def pick_sites(inv):
    """The live gauges; --queue=N adds the first N queued gauges (shadow timing only); --shard=i/N keeps the i-th of N equal slices of that list sorted by state then site, so a shard's gauges are neighbours (shared NWS grid, station and alert URLs)."""
    import csv
    arg = lambda k: next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--%s=" % k)), None)
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8")))
    sites = [r["site"] for r in rows if r["status"] == "live"]
    if arg("queue"):
        sites += [r["site"] for r in rows if r["status"] == "queue" and r["site"] in inv][:int(arg("queue"))]
    if arg("shard"):
        i, n = map(int, arg("shard").split("/"))
        st = {r["site"]: r["state"] for r in rows}
        sites = sorted(sites, key=lambda x: (st.get(x, ""), x))
        sites = sites[i * len(sites) // n:(i + 1) * len(sites) // n]
    return sorted(sites)


def write_timing(wall):
    """state/collect-timing.json: seconds and calls per endpoint and per source, for finding where the minutes go."""
    out = {"at": now_iso(), "wall_s": round(wall, 1), "next": NEXT, "args": [a for a in sys.argv[1:] if a.startswith("--")], "labels": {k: [v[0], round(v[1], 1)] for k, v in sorted(TIME.items(), key=lambda kv: -kv[1][1])}}
    os.makedirs(os.path.join(ROOT, "state"), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, "state", "collect-timing.json"), "w"), indent=1)
    print("TIMING wall %.0f s; top: %s" % (wall, "; ".join("%s %d calls %.0f s" % (k, v[0], v[1]) for k, v in list(out["labels"].items())[:12])))


def main():
    inv = {}
    for l in open(os.path.join(LEGACY, "gauges-all.tsv"), encoding="utf-8").read().split("\n")[1:]:
        c = l.split("\t")
        if len(c) > 10 and c[1]:
            inv[c[1]] = {"lat": c[4], "lon": c[5], "name": c[2]}
    os.makedirs(CACHE, exist_ok=True)
    sites = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--print-sites" in sys.argv:  # collect-shadow.yml: which gauges this shard owns
        print(chr(10).join(pick_sites(inv)))
        return
    if not sites:  # the hourly run: every live gauge, each source on its own timer (2026-10-26: one lane replaced the 30-min fast + 6-h full lanes)
        t0 = _time.time()
        fast(inv, pick_sites(inv))
        write_timing(_time.time() - t0)
        return
    for s in sites:
        try:
            rec, log = collect(s, inv)
        except Exception as e:
            print("FAIL", s, str(e)[:100], "(cache kept)")
            note("usgs", "failed", e)  # the critical series (a 429 here is the key quota): the gauge is not collected this run
            continue
        note("usgs", "ok")
        tmp = os.path.join(CACHE, s + ".json.tmp")
        json.dump(rec, open(tmp, "w"), separators=(",", ":"))
        os.replace(tmp, os.path.join(CACHE, s + ".json"))
        n = rec
        print("ok %s rows %d tz %s | nwps %s fc %s | nwm %s | nws periods %d alerts %s obs %s | rain %s | related %d | land %s %s" % (
            s, len(n["usgs"]["rows"]), n.get("tz"), (n.get("nwps") or {}).get("lid"), bool((n.get("nwps") or {}).get("forecast")), bool((n.get("nwm") or {}).get("points")),
            len((n.get("nws") or {}).get("periods") or []), len((n.get("nws") or {}).get("alerts") or []) if (n.get("nws") or {}).get("alerts") is not None else None, bool((n.get("nws") or {}).get("obs")),
            bool(n.get("rain")), len((n.get("related") or {}).get("items") or []), len((n.get("land") or {}).get("rows") or []) if n.get("land") else 0, "; ".join(log)))
    write_health("partial", len(sites))
    fetch_states(sites)  # statewide alerts + drought for each state hub


main()
