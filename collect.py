"""Collector: the only code that touches the network. Writes cache/<site>.json.
Each source is fetched independently; a failed source keeps its previous cached value (and old fetched_at), it never blanks the record.
Usage: python -I collect.py [site ...]   (default: wave 0)
"""
import os, sys, json, math, re, datetime, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.common import *
from lib.pages import WAVE0

CODES = "00060,00065,00010,00300,63680,00400,00095,99133"
BASE = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/"
NWS_H = {"User-Agent": "riverwaterlevels.com (https://riverwaterlevels.com/about/)", "Accept": "application/geo+json"}
NWPS = "https://api.water.noaa.gov/nwps/v1/"


_last = [0.0]


def thr_json(url, headers=None, timeout=60, gap=1.5, tries=6):
    """Throttled GET for the NWS/NOAA hosts: minimum gap between calls, honours Retry-After, exponential backoff on 429/5xx."""
    import time, urllib.error
    for i in range(tries):
        wait = gap - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            return http_json(url, headers, timeout)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or i == tries - 1:
                raise
            time.sleep(min(60, float(e.headers.get("Retry-After") or 3 * 2 ** i)))
    raise RuntimeError("unreachable")


def now_iso():
    return iso(datetime.datetime.now(datetime.timezone.utc))


def haversine(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(x))


def fetch_usgs(site, h):
    rows, trunc, wrong = [], [], None
    for code in CODES.split(","):
        d = http_json(BASE + "continuous/items?monitoring_location_id=USGS-%s&parameter_code=%s&time=P8D&limit=4000&f=json" % (site, code), h, 120)
        fs = d.get("features", [])
        if len(fs) >= 4000:
            trunc.append(code)
        for f in fs:
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


def fetch_related(site, inv, h):
    out = []
    for nav, rel in (("UM", "upstream"), ("DM", "downstream")):
        try:
            d = http_json("https://api.water.usgs.gov/nldi/linked-data/nwissite/USGS-%s/navigation/%s/nwissite?f=json&distance=150" % (site, nav))
        except Exception:
            continue
        for f in d.get("features", []):
            sid = str(f["properties"].get("identifier", "")).replace("USGS-", "")
            if sid in inv and sid != site and sid not in [x["site"] for x in out]:
                out.append({"site": sid, "relation": rel})
    res = []
    for x in out[:12]:
        try:
            fs = http_json(BASE + "latest-continuous/items?monitoring_location_id=USGS-%s&parameter_code=00060&f=json" % x["site"], h).get("features", [])
            if fs:
                p = fs[0]["properties"]
                x["flow"], x["time"] = float(p["value"]), p["time"]
                res.append(x)
        except Exception:
            pass
    return {"fetched_at": now_iso(), "items": res}


def fetch_nwps(site, lat, lon):
    """NWPS answers /gauges/<USGS id> directly; the returned usgsId must equal the gauge, so a coordinate match is never used."""
    import urllib.error, math
    cw = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "nws-crosswalk.json"))).get(site)
    try:
        det = thr_json(NWPS + "gauges/%s" % site, NWS_H)
    except urllib.error.HTTPError as e:
        if e.code not in (400, 404):
            raise
        det = None
        if cw:  # NWPS has the point but no usgsId on it: accept the crosswalk entry only when it sits within 1 km of this gauge
            det = thr_json(NWPS + "gauges/%s" % cw, NWS_H)
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
            fc = None
            try:
                j = thr_json(NWPS + "gauges/%s/stageflow/forecast" % x["lid"], NWS_H)
                pts = [{"t": p.get("validTime"), "primary": p.get("primary"), "secondary": p.get("secondary")} for p in (j.get("data") or []) if isinstance(p.get("primary"), (int, float)) and p["primary"] > -990]
                if pts:
                    fc = {"issued": j.get("issuedTime"), "primary_units": j.get("primaryUnits"), "secondary_units": j.get("secondaryUnits"), "points": pts[:400]}
            except Exception:
                pass
            rflow = {}
            try:
                rf = thr_json(NWPS + "gauges/%s/riverflow" % x["lid"], NWS_H)
                # NWPS lists upstream farthest first and downstream nearest first: keep the six nearest of each
                allp = {k: [{"LID": i.get("LID"), "Name": i.get("Name")} for i in (rf.get(k) or []) if isinstance(i, dict)] for k in ("upstream", "downstream")}
                rflow = {"upstream": allp["upstream"][-6:], "downstream": allp["downstream"][:6], "upstream_n": len(allp["upstream"]), "downstream_n": len(allp["downstream"])}
            except Exception:
                pass
            obs_stage = None
            try:
                ob = thr_json(NWPS + "gauges/%s/stageflow/observed" % x["lid"], NWS_H)
                col = "primary" if (ob.get("primaryUnits") or "").lower() == "ft" else "secondary" if (ob.get("secondaryUnits") or "").lower() == "ft" else None  # the height column is found by its units, not its position
                pts = [p for p in (ob.get("data") or []) if col and isinstance(p.get(col), (int, float)) and p[col] > -900]
                if pts:
                    obs_stage = {"t": pts[-1]["validTime"], "v": pts[-1][col]}
            except Exception:
                pass
            fl = det.get("flood") or {}
            hist = [{"t": c.get("occurredTime"), "stage": c.get("stage"), "flow": c.get("flow")} for c in ((fl.get("crests") or {}).get("historic") or []) if isinstance(c.get("stage"), (int, float))][:10]
            imp = [{"stage": i.get("stage"), "statement": i.get("statement")} for i in (fl.get("impacts") or []) if isinstance(i.get("stage"), (int, float)) and i.get("statement")]
            return {"fetched_at": now_iso(), "lid": x["lid"], "name": det.get("name"), "reach_id": det.get("reachId"), "categories": cats, "forecast": fc,
                    "riverflow": rflow, "obs_stage": obs_stage, "stage_units": fl.get("stageUnits"), "crests": hist, "impacts": sorted(imp, key=lambda i: i["stage"]),
                    "wfo": det.get("wfo"), "rfc": det.get("rfc"), "reliability": det.get("forecastReliability"), "fim": bool((det.get("inundation") or {}).get("enabled")), "lro": fl.get("lro")}
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
    req = urllib.request.Request("https://waterdata.usgs.gov/nwisweb/get_ratings?site_no=%s&file_type=exsa" % site, headers={"User-Agent": "riverwaterlevels.com (https://riverwaterlevels.com/about/)"})
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


def fetch_atlas14(lat, lon):
    """NOAA Atlas 14 point precipitation frequency depth (inches, partial duration series)."""
    import urllib.request
    req = urllib.request.Request("https://hdsc.nws.noaa.gov/cgi-bin/new/fe_text_mean.csv?lat=%.4f&lon=%.4f&type=pf&data=depth&units=english&series=pds" % (lat, lon), headers={"User-Agent": "riverwaterlevels.com (https://riverwaterlevels.com/about/)"})
    txt = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "ignore")
    ari, rows = None, {}
    for l in txt.split("\n"):
        l = l.strip()
        if l.lower().startswith("by duration for ari"):
            ari = [int(float(x)) for x in l.split(":", 1)[1].split(",") if x.strip()]
        elif ari and l.split(":", 1)[0] in ("60-min", "6-hr", "24-hr", "2-day", "7-day"):
            vals = [float(x) for x in l.split(":", 1)[1].split(",") if x.strip()]
            if len(vals) == len(ari):
                rows[l.split(":", 1)[0]] = vals
    return {"fetched_at": now_iso(), "ari": ari, "rows": rows} if (ari and rows) else None


def get_text(url, headers=None, timeout=90):
    import urllib.request
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers or {"User-Agent": "riverwaterlevels.com"}), timeout=timeout).read().decode("utf-8", "ignore")


def county_codes(rec):
    loc = ((rec.get("meta") or {}).get("loc")) or {}
    if loc.get("state_code") and loc.get("county_code"):
        return str(loc["state_code"]).zfill(2), str(loc["county_code"]).zfill(3)
    ugc = (rec.get("nws") or {}).get("county_ugc") or ""
    if len(ugc) != 6 or ugc[:2] not in STATE_FIPS:
        return None
    return STATE_FIPS[ugc[:2]], ugc[3:]


def fetch_openfema(rec):
    """Federal flood disaster declarations for the gauge's county (OpenFEMA DisasterDeclarationsSummaries)."""
    cc = county_codes(rec)
    if not cc:
        return None
    flt = "fipsStateCode eq '%s' and fipsCountyCode eq '%s' and (incidentType eq 'Flood' or substringof('FLOOD',declarationTitle))" % cc
    q = urllib.parse.urlencode({"$filter": flt, "$orderby": "declarationDate desc", "$top": "12", "$inlinecount": "allpages",
                                "$select": "femaDeclarationString,declarationDate,incidentBeginDate,incidentEndDate,declarationTitle,paProgramDeclared,iaProgramDeclared,designatedArea"}, quote_via=urllib.parse.quote)
    j = json.loads(get_text("https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries?" + q))
    items = [{"id": x.get("femaDeclarationString"), "date": str(x.get("declarationDate"))[:10], "begin": str(x.get("incidentBeginDate"))[:10], "end": str(x.get("incidentEndDate"))[:10], "title": x.get("declarationTitle"),
              "pa": x.get("paProgramDeclared"), "ia": x.get("iaProgramDeclared"), "area": x.get("designatedArea")} for x in j.get("DisasterDeclarationsSummaries", [])]
    return {"fetched_at": now_iso(), "count": (j.get("metadata") or {}).get("count", len(items)), "items": items}


def _money(v):
    v = str(v or "").strip().upper()
    if not v:
        return 0.0
    mult = {"K": 1e3, "M": 1e6, "B": 1e9}.get(v[-1], 1)
    try:
        return float(v[:-1] if v[-1] in "KMB" else v) * mult
    except ValueError:
        return 0.0


def ncei_year(year):
    """County-level Flood and Flash Flood rows of one Storm Events year file (NOAA NCEI bulk csv.gz), cached compactly under cache/_ncei/."""
    import gzip, io, csv, urllib.request
    path = os.path.join(CACHE, "_ncei", "%d.json" % year)
    if os.path.exists(path) and (datetime.datetime.now().timestamp() - os.path.getmtime(path)) < 20 * 86400:
        return json.load(open(path))
    base = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
    names = re.findall(r"StormEvents_details-ftp_v1\.0_d%d_c\d+\.csv\.gz" % year, get_text(base, timeout=60))
    if not names:
        return []
    raw = urllib.request.urlopen(urllib.request.Request(base + max(names), headers={"User-Agent": "riverwaterlevels.com (https://riverwaterlevels.com/about/)"}), timeout=300).read()
    rows = []
    for r in csv.DictReader(io.TextIOWrapper(gzip.GzipFile(fileobj=io.BytesIO(raw)), encoding="utf-8", errors="replace")):
        if r.get("EVENT_TYPE") in ("Flood", "Flash Flood") and r.get("CZ_TYPE") == "C":
            try:
                d = datetime.datetime.strptime(r["BEGIN_DATE_TIME"], "%d-%b-%y %H:%M:%S").date().isoformat()
            except ValueError:
                d = "%s-%s" % (r.get("BEGIN_YEARMONTH", "")[:4], r.get("BEGIN_YEARMONTH", "")[4:6])
            rows.append([r["STATE_FIPS"], r["CZ_FIPS"], d, r["EVENT_TYPE"], int(r.get("DEATHS_DIRECT") or 0) + int(r.get("DEATHS_INDIRECT") or 0),
                         int(r.get("INJURIES_DIRECT") or 0) + int(r.get("INJURIES_INDIRECT") or 0), _money(r.get("DAMAGE_PROPERTY")) + _money(r.get("DAMAGE_CROPS")), r.get("FLOOD_CAUSE") or "", (r.get("CZ_NAME") or "").replace(" (C)", ""), r.get("BEGIN_LOCATION") or ""])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(rows, open(path, "w"), separators=(",", ":"))
    return rows


def fetch_storms(rec, years=10):
    """Flood and flash flood events recorded for the gauge's county over the last `years` years (NOAA NCEI Storm Events Database)."""
    cc = county_codes(rec)
    if not cc:
        return None
    sf, cf = cc
    last = datetime.date.today().year
    ev = []
    for y in range(last - years, last + 1):
        try:
            ev += [r for r in ncei_year(y) if r[0].lstrip("0") == sf.lstrip("0") and r[1].lstrip("0") == cf.lstrip("0")]
        except Exception:
            continue
    ev.sort(key=lambda r: r[2], reverse=True)
    return {"fetched_at": now_iso(), "years": [last - years, last], "n": len(ev), "deaths": sum(r[4] for r in ev), "injuries": sum(r[5] for r in ev), "damage": sum(r[6] for r in ev),
            "county": ev[0][8] if ev else None, "kind": "City" if int(cf) >= 500 else "County", "recent": ev[:10]}


def fetch_echo(lat, lon):
    """EPA ECHO: Clean Water Act individual-permit facilities within 5 miles (summary counts only)."""
    q = urllib.parse.urlencode({"output": "JSON", "p_lat": "%.4f" % lat, "p_long": "%.4f" % lon, "p_radius": "5", "p_act": "Y", "p_ptype": "NPD"})
    j = json.loads(get_text("https://echodata.epa.gov/echo/cwa_rest_services.get_facilities?" + q))
    r = j.get("Results", j)
    keys = ("QueryRows", "SVRows", "CVRows", "V3Rows", "INSPRows", "VioLast4QRows", "TotalPenalties")
    out = {k: r.get(k) for k in keys}
    return {"fetched_at": now_iso(), "counts": out} if out.get("QueryRows") is not None else None


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


def fetch_nid(lat, lon, miles=15):
    """USACE National Inventory of Dams: dams within `miles` of the gauge, nearest first (decoded text fields)."""
    q = urllib.parse.urlencode({"where": "1=1", "geometry": "%.5f,%.5f" % (lon, lat), "geometryType": "esriGeometryPoint", "inSR": "4326", "distance": str(miles), "units": "esriSRUnit_StatuteMile",
                                "outFields": "NIDID,NAME,RIVER_OR_STREAM,NID_HEIGHT,NID_STORAGE,YEAR_COMPLETED,HAZARD_POTENTIAL,DATA_UPDATED", "returnGeometry": "true", "outSR": "4326", "resultRecordCount": "200", "f": "json"})
    j = json.loads(get_text("https://geospatial.sec.usace.army.mil/dls/rest/services/NID/National_Inventory_of_Dams_Public_Service/FeatureServer/0/query?" + q))
    dams = []
    for f in j.get("features", []):
        a, g = f.get("attributes") or {}, f.get("geometry") or {}
        if g.get("x") is None:
            continue
        dams.append({"id": a.get("NIDID"), "name": a.get("NAME"), "river": a.get("RIVER_OR_STREAM"), "height_ft": a.get("NID_HEIGHT"), "storage_af": a.get("NID_STORAGE"), "year": a.get("YEAR_COMPLETED"),
                     "hazard": a.get("HAZARD_POTENTIAL"), "mi": round(hav_km(lat, lon, g["y"], g["x"]) * 0.621371, 1)})
    dams.sort(key=lambda d: d["mi"])
    return {"fetched_at": now_iso(), "miles": miles, "count": len(dams), "dams": dams[:15]}


def fetch_fema_zone(lat, lon):
    """FEMA flood hazard zones within 500 m of the gauge (Esri Living Atlas copy of the FIRM data; generalised, not parcel level)."""
    q = urllib.parse.urlencode({"geometry": "%.5f,%.5f" % (lon, lat), "geometryType": "esriGeometryPoint", "inSR": "4326", "distance": "500", "units": "esriSRUnit_Meter",
                                "outFields": "FLD_ZONE,ZONE_SUBTY,SFHA_TF", "returnGeometry": "false", "f": "json"})
    j = json.loads(get_text("https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/USA_Flood_Hazard_Reduced_Set_gdb/FeatureServer/0/query?" + q))
    zones = sorted({(a.get("FLD_ZONE") or "", a.get("ZONE_SUBTY") or "", a.get("SFHA_TF") or "") for a in (f.get("attributes") or {} for f in j.get("features", []))})
    return {"fetched_at": now_iso(), "meters": 500, "zones": [list(z) for z in zones]}


RISE_MAP = {"09380000": {"name": "Glen Canyon Dam (Lake Powell)", "loc": 393, "items": (("Total release", 4315, "cfs"), ("Powerplant release", 507, "cfs"), ("Spillway release", 4391, "cfs"), ("Bypass release", 4392, "cfs"), ("Lake Powell elevation", 508, "ft"))}}


def fetch_rise(site):
    """Bureau of Reclamation RISE daily dam operations for gauges mapped to a dam (the API ignores location filters, so item ids are mapped by hand)."""
    m = RISE_MAP.get(site)
    if not m:
        return None
    after = (datetime.date.today() - datetime.timedelta(days=14)).isoformat()
    series = {}
    for label, item, unit in m["items"]:
        q = "itemId=%d&dateTime%%5Bafter%%5D=%s&order%%5BdateTime%%5D=desc&itemsPerPage=20" % (item, after)
        j = json.loads(get_text("https://data.usbr.gov/rise/api/result?" + q))
        data = j.get("data") if isinstance(j, dict) else j
        rows = []
        for x in data or []:
            a = (x.get("attributes") or x) if isinstance(x, dict) else {}
            if a.get("result") is not None:
                rows.append([str(a.get("dateTime"))[:10], a.get("result")])
        if rows:
            series[label] = {"unit": unit, "rows": rows}
    return {"fetched_at": now_iso(), "dam": m["name"], "series": series} if series else None


def fetch_floodfreq(site):
    """USGS StreamStats gage statistics: annual exceedance probability (AEP) peak flows with their published confidence intervals.
    Not shown (regulated=True or conflict=True) when the station is regulated or when USGS publishes more than one preferred set that disagree by over 10% at the 1% flow."""
    j = thr_json("https://streamstats.usgs.gov/gagestatsservices/stations/" + site, None, 60, gap=1.0)
    groups = {}
    for s in j.get("statistics") or []:
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
    if not groups:
        return None
    best = max(groups.values(), key=lambda g: (any(r["pref"] for r in g.values()), max(re.findall(r"\d{4}", next(iter(g.values()))["range"]) or ["0"]), len(g)))
    one = [g[1.0]["q"] for g in groups.values() if 1.0 in g and any(r["pref"] for r in g.values())]
    conflict = len(one) > 1 and max(one) > 1.1 * min(one)
    first = next(iter(best.values()))
    yrs = re.findall(r"\d{4}", first["range"])
    cit = first["cit"]
    return {"fetched_at": now_iso(), "regulated": bool(j.get("isRegulated")), "conflict": conflict, "range": ("%s to %s" % (yrs[0], yrs[1])) if len(yrs) >= 2 else None, "years": first["years"],
            "citation": cit.get("title"), "url": cit.get("citationURL"),
            "rows": sorted([{k: v for k, v in r.items() if k in ("aep", "q", "lo", "hi")} for r in best.values()], key=lambda r: -r["aep"])}


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


def fetch_nwm(site):
    d = http_json("https://api.water.usgs.gov/nldi/linked-data/nwissite/USGS-%s?f=json" % site)
    comid = d["features"][0]["properties"].get("comid")
    if not comid:
        return {"fetched_at": now_iso(), "comid": None}
    j = thr_json(NWPS + "reaches/%s/streamflow?series=short_range" % comid, NWS_H)
    s = (j.get("shortRange") or {}).get("series") or {}
    pts = [{"t": p.get("validTime"), "flow": p.get("flow")} for p in (s.get("data") or []) if isinstance(p.get("flow"), (int, float)) and p["flow"] >= 0]
    out = {"fetched_at": now_iso(), "comid": comid, "reference_time": s.get("referenceTime"), "points": pts[:60]}
    try:
        m = thr_json(NWPS + "reaches/%s/streamflow?series=medium_range" % comid, NWS_H)
        mm = (m.get("mediumRange") or {}).get("mean") or {}
        mp = [{"t": p.get("validTime"), "flow": p.get("flow")} for p in (mm.get("data") or []) if isinstance(p.get("flow"), (int, float)) and p["flow"] >= 0]
        if mp:
            out["medium"], out["medium_reference_time"] = mp[:120], mm.get("referenceTime") or (m.get("mediumRange") or {}).get("referenceTime")
    except Exception:
        pass
    return out


def grid_hours(gp, hours=168):
    """Expand NWS gridpoint interval values to one row per hour: temp, wind, gust, direction, sky cover and rain amount (mm per hour)."""
    keys = {"temperature": "temp_c", "windSpeed": "wind_kmh", "windGust": "gust_kmh", "windDirection": "dir", "skyCover": "sky", "quantitativePrecipitation": "qpf_mm"}
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


def fetch_nws(lat, lon):
    pt = thr_json("https://api.weather.gov/points/%.4f,%.4f" % (lat, lon), NWS_H).get("properties", {})
    out = {"fetched_at": now_iso(), "tz": pt.get("timeZone"), "county_ugc": (pt.get("county") or "").rsplit("/", 1)[-1], "radar": pt.get("radarStation"), "radar_ll": None, "periods": [], "alerts": None, "obs": None}
    try:
        if pt.get("radarStation"):
            out["radar_ll"] = thr_json("https://api.weather.gov/radar/stations/%s" % pt["radarStation"], NWS_H).get("geometry", {}).get("coordinates")
    except Exception:
        pass
    try:
        f = thr_json(pt["forecast"], NWS_H)["properties"]
        out["forecast_updated"] = f.get("updateTime") or f.get("generatedAt")
        out["periods"] = [{k: p.get(k) for k in ("name", "startTime", "endTime", "temperature", "temperatureUnit", "shortForecast", "windSpeed", "windDirection", "isDaytime")} | {"pop": (p.get("probabilityOfPrecipitation") or {}).get("value")} for p in f.get("periods", [])[:14]]
    except Exception:
        pass
    try:
        hf = thr_json(pt["forecastHourly"], NWS_H)["properties"]
        out["hourly_updated"] = hf.get("updateTime") or hf.get("generatedAt")
        out["hourly"] = [{k: p.get(k) for k in ("startTime", "temperature", "temperatureUnit", "shortForecast", "windSpeed", "windDirection")} | {"pop": (p.get("probabilityOfPrecipitation") or {}).get("value")} for p in hf.get("periods", [])[:36]]
    except Exception:
        pass
    try:
        gp = thr_json(pt["forecastGridData"], NWS_H)["properties"]
        out["grid"] = grid_hours(gp)
    except Exception:
        pass
    try:
        a = thr_json("https://api.weather.gov/alerts/active?point=%.4f,%.4f" % (lat, lon), NWS_H)
        out["alerts"] = [dict({k: (x["properties"].get(k)) for k in ("event", "severity", "areaDesc", "headline", "ends", "expires", "senderName")},
                              states=sorted({u[:2] for u in ((x["properties"].get("geocode") or {}).get("UGC") or [])})) for x in a.get("features", [])]
    except Exception:
        pass
    try:
        st = thr_json(pt["observationStations"], NWS_H)["features"][0]
        o = thr_json(st["id"] + "/observations?limit=8", NWS_H)
        obs = [f["properties"] for f in o.get("features", []) if (f["properties"].get("temperature") or {}).get("value") is not None]
        if obs:
            x = obs[0]
            def v(k): return (x.get(k) or {}).get("value")
            old = next((y for y in obs if (y.get("barometricPressure") or {}).get("value") is not None and (parse_t(x["timestamp"]) - parse_t(y["timestamp"])).total_seconds() >= 2.5 * 3600), None)
            out["obs"] = {"name": (st.get("properties") or {}).get("name"), "ll": (st.get("geometry") or {}).get("coordinates"), "station": st["id"].rsplit("/", 1)[-1], "timestamp": x["timestamp"], "temp_c": v("temperature"), "wind_kmh": v("windSpeed"), "wind_dir": v("windDirection"), "gust_kmh": v("windGust"),
                          "pressure_pa": v("barometricPressure"), "pressure_prev_pa": (old.get("barometricPressure") or {}).get("value") if old else None, "visibility_m": v("visibility")}
    except Exception:
        pass
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


def fetch_rain(lat, lon):
    g = urllib.parse.quote(json.dumps({"x": lon, "y": lat, "spatialReference": {"wkid": 4326}}))
    j = http_json("https://mapservices.weather.noaa.gov/raster/rest/services/obs/rfc_qpe/MapServer/identify?geometry=%s&geometryType=esriGeometryPoint&sr=4326&layers=all:7,8,15,16,19,20,23,24,27,28,35,36,39,40&tolerance=1&mapExtent=-125,24,-66,50&imageDisplay=1000,500,96&returnGeometry=false&f=json" % g, NWS_H)
    by, issued, lid = {}, {}, {}
    for r in j.get("results", []):
        a = r.get("attributes") or {}
        if a.get("idp_issueddate"):  # each image layer N has a footprint layer N-1 carrying the product's issue (valid-through) time, UTC
            issued[r["layerId"]] = datetime.datetime.strptime(a["idp_issueddate"], "%m/%d/%Y %I:%M:%S %p").replace(tzinfo=datetime.timezone.utc).isoformat()
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


def fetch_extras(site, rec, h, log):
    """Blocks added in the final-form pass. Each source is independent; a failure keeps the previous cached value."""
    lat, lon = rec["lat"], rec["lon"]
    want = next((a[7:].split(",") for a in sys.argv if a.startswith("--keys=")), None)
    for key, fn in (("meta", lambda: fetch_meta(site, h)), ("peaks", lambda: fetch_peaks(site, h)), ("wtemp", lambda: fetch_wtemp(site, h)), ("snotel", lambda: fetch_snotel(lat, lon)), ("cpc", lambda: fetch_cpc(lat, lon)), ("usdm", lambda: fetch_usdm(rec)), ("attains", lambda: fetch_attains(lat, lon)),
                    ("record", lambda: record_summary(fetch_daily(site, h), rec.get("stats"))), ("year", lambda: fetch_year(site, h)), ("fieldmeas", lambda: fetch_fieldmeas(site, h)), ("floodfreq", lambda: fetch_floodfreq(site)), ("cpc610", lambda: fetch_cpc(lat, lon, "cpc_6_10_day_outlk")),
                    ("related", lambda: related_lag(rec, h)), ("openfema", lambda: fetch_openfema(rec)), ("storms", lambda: fetch_storms(rec)), ("echo", lambda: fetch_echo(lat, lon)), ("acis", lambda: fetch_acis(rec)),
                    ("streamcat", lambda: fetch_streamcat(site, rec)), ("nid", lambda: fetch_nid(lat, lon)), ("fema_zone", lambda: fetch_fema_zone(lat, lon)), ("rise", lambda: fetch_rise(site)),
                    ("rating", lambda: fetch_rating(site)), ("atlas14", lambda: fetch_atlas14(lat, lon)),
                    ("multiyear", lambda: multiyear(fetch_daily(site, h)))):
        if want and key not in want:
            continue
        try:
            rec[key] = fn()
        except Exception as e:
            log.append("%s FAILED (%s), kept previous" % (key, str(e)[:60]))


def collect(site, inv):
    h = usgs_headers()
    path = os.path.join(CACHE, site + ".json")
    rec = json.load(open(path)) if os.path.exists(path) else {"site": site}
    g = inv[site]
    lat, lon = float(g["lat"]), float(g["lon"])
    rec["lat"], rec["lon"] = lat, lon
    rec["usgs"] = fetch_usgs(site, h)  # critical: raises, cache kept
    log = []
    for key, fn in (("related", lambda: fetch_related(site, inv, h)), ("nwps", lambda: fetch_nwps(site, lat, lon)), ("nws", lambda: fetch_nws(lat, lon)), ("rain", lambda: fetch_rain(lat, lon)), ("wpc", lambda: fetch_wpc(lat, lon))):
        try:
            rec[key] = fn()
        except Exception as e:
            log.append("%s FAILED (%s), kept previous" % (key, str(e)[:60]))
    if not (rec.get("nwps") or {}).get("forecast"):
        try:
            rec["nwm"] = fetch_nwm(site)
        except Exception as e:
            log.append("nwm FAILED (%s)" % str(e)[:60])
    sp = os.path.join(LEGACY, "stats", site + ".json")
    if os.path.exists(sp):
        rec["stats"] = json.load(open(sp))["d"]
        rec["stats_source"] = "USGS daily statistics, downloaded " + datetime.date.fromtimestamp(os.path.getmtime(sp)).isoformat()
    try:
        rec["record"] = record_summary(fetch_daily(site, h), rec.get("stats"))
    except Exception as e:
        log.append("record FAILED (%s), kept previous" % str(e)[:60])
    fetch_extras(site, rec, h, log)
    land = fetch_land(site)
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
    """One bulk latest-continuous call: newest reading per gauge and parameter, as rows in the same shape as fetch_usgs. Readings older than the 8-day window are ignored (the service returns decades-old values for dead sensors)."""
    d = thr_json(BASE + "latest-continuous/items?monitoring_location_id=%s&parameter_code=%s&limit=1000&f=json" % (",".join("USGS-" + s for s in sites), CODES), h, 120, gap=1.0)
    cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=8)).isoformat()
    out = {}
    for f in d.get("features", []):
        p = f["properties"]
        if p.get("value") in (None, "") or str(p.get("time") or "") < cutoff:
            continue
        out.setdefault(p["monitoring_location_id"][5:], []).append({k: p.get(k) for k in ("parameter_code", "time", "value", "unit_of_measure", "qualifier", "approval_status") if k in p})
    return out


def fast_fill(rec, site, h):
    """The bulk latest call returns one reading per gauge, so between full collects the series gets one point per run and the 15-minute readings in between are missing (highest and lowest readings, charts and changes would be computed from a thinned tail). When the last 6 hours of flow or stage have gaps over 20 minutes, fetch those 6 hours for the two main parameters and merge them."""
    now = datetime.datetime.now(datetime.timezone.utc)
    t0 = (now - datetime.timedelta(hours=6)).isoformat()
    need = False
    for code in ("00060", "00065"):
        ts = sorted(r["time"] for r in rec["usgs"]["rows"] if r["parameter_code"] == code and str(r["time"]) >= t0)
        if code == "00060" or ts:
            pts = [datetime.datetime.fromisoformat(t.replace("Z", "+00:00")) for t in ts]
            if len(pts) < 2 or any((b_ - a_).total_seconds() > 1200 for a_, b_ in zip(pts, pts[1:])):
                need = True
    if not need:
        return 0
    have = {(r["parameter_code"], r["time"]) for r in rec["usgs"]["rows"]}
    added = 0
    for code in ("00060", "00065"):
        d = http_json(BASE + "continuous/items?monitoring_location_id=USGS-%s&parameter_code=%s&time=PT6H&limit=4000&f=json" % (site, code), h, 120)
        for f in d.get("features", []):
            p = f["properties"]
            if p.get("value") in (None, "") or (code, p["time"]) in have:
                continue
            rec["usgs"]["rows"].append({k: p.get(k) for k in ("parameter_code", "time", "value", "unit_of_measure", "qualifier", "approval_status") if k in p})
            have.add((code, p["time"]))
            added += 1
    return added


def fast(inv, sites):
    h = usgs_headers()
    try:
        new = fast_usgs(sites, h)
    except Exception as e:  # USGS unavailable or rate-limited: still refresh the weather sources
        print("FAIL usgs bulk", str(e)[:100])
        new = {}
    for s in sites:
        path = os.path.join(CACHE, s + ".json")
        rec, log = json.load(open(path)), []
        have = {(r["parameter_code"], r["time"]) for r in rec["usgs"]["rows"]}
        add = [r for r in new.get(s, []) if (r["parameter_code"], r["time"]) not in have]
        cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=8)).isoformat()
        rec["usgs"]["rows"] = [r for r in rec["usgs"]["rows"] + add if str(r["time"]) >= cutoff]
        if add:
            rec["usgs"]["fetched_at"] = now_iso()
        try:
            filled = fast_fill(rec, s, h)
            if filled:
                rec["usgs"]["rows"] = [r for r in rec["usgs"]["rows"] if str(r["time"]) >= cutoff]
                rec["usgs"]["fetched_at"] = now_iso()
                log.append("filled %d readings" % filled)
        except Exception as e:
            log.append("fill FAILED (%s), kept the thinned tail" % str(e)[:60])
        for key, fn in (("nwps", lambda: fetch_nwps(s, rec["lat"], rec["lon"])), ("nws", lambda: fetch_nws(rec["lat"], rec["lon"])), ("rain", lambda: fetch_rain(rec["lat"], rec["lon"])), ("wpc", lambda: fetch_wpc(rec["lat"], rec["lon"]))):
            try:
                rec[key] = fn()
            except Exception as e:
                log.append("%s FAILED (%s), kept previous" % (key, str(e)[:60]))
        if not (rec.get("nwps") or {}).get("forecast"):
            try:
                rec["nwm"] = fetch_nwm(s)
            except Exception as e:
                log.append("nwm FAILED (%s)" % str(e)[:60])
        rec["tz"] = (rec.get("nws") or {}).get("tz") or rec.get("tz")
        rec["fetched_at"] = now_iso()
        json.dump(rec, open(path + ".tmp", "w"), separators=(",", ":"))
        os.replace(path + ".tmp", path)
        print("ok fast", s, "new usgs rows", len(add), "; ".join(log))
    recs = {s: json.load(open(os.path.join(CACHE, s + ".json"))) for s in sites}
    try:
        fast_related(recs, h)
        for s, r in recs.items():
            json.dump(r, open(os.path.join(CACHE, s + ".json.tmp"), "w"), separators=(",", ":"))
            os.replace(os.path.join(CACHE, s + ".json.tmp"), os.path.join(CACHE, s + ".json"))
        print("ok fast related flows")
    except Exception as e:
        print("FAIL related flows", str(e)[:100])


def main():
    inv = {}
    for l in open(os.path.join(LEGACY, "gauges-all.tsv"), encoding="utf-8").read().split("\n")[1:]:
        c = l.split("\t")
        if len(c) > 10 and c[1]:
            inv[c[1]] = {"lat": c[4], "lon": c[5], "name": c[2]}
    os.makedirs(CACHE, exist_ok=True)
    if "--fast" in sys.argv:  # freshest-possible refresh: one bulk USGS latest call for every gauge, then NWS, NWPS forecast and rain; the slow history is left as cached
        fast(inv, [a for a in sys.argv[1:] if not a.startswith("--")] or WAVE0)
        return
    if "--extras-only" in sys.argv:  # new-source blocks plus NWPS and NWS; skips the critical USGS series so it cannot trip that rate limit
        h = usgs_headers()
        for s in [a for a in sys.argv[1:] if not a.startswith("--")] or WAVE0:
            path = os.path.join(CACHE, s + ".json")
            rec, log = json.load(open(path)), []
            for key, fn in (("nwps", lambda: fetch_nwps(s, rec["lat"], rec["lon"])), ("nws", lambda: fetch_nws(rec["lat"], rec["lon"]))):
                if any(a.startswith("--keys=") for a in sys.argv):
                    continue
                try:
                    rec[key] = fn()
                except Exception as e:
                    log.append("%s FAILED (%s)" % (key, str(e)[:60]))
            fetch_extras(s, rec, h, log)
            json.dump(rec, open(path + ".tmp", "w"), separators=(",", ":"))
            os.replace(path + ".tmp", path)
            print("ok extras", s, "peaks", len((rec.get("peaks") or {}).get("rows") or []), "wtemp", bool(rec.get("wtemp")), "snotel", len((rec.get("snotel") or {}).get("stations") or []), "cpc", bool(rec.get("cpc")),
                  "multiyear", bool(rec.get("multiyear")), "crests", len((rec.get("nwps") or {}).get("crests") or []), "impacts", len((rec.get("nwps") or {}).get("impacts") or []), "grid", len(((rec.get("nws") or {}).get("grid") or {}).get("hours") or []), "; ".join(log))
        return
    if "--nws-only" in sys.argv:  # refresh only the NWS block (no USGS calls) when USGS rate-limits
        for s in [a for a in sys.argv[1:] if not a.startswith("--")] or WAVE0:
            path = os.path.join(CACHE, s + ".json")
            rec = json.load(open(path))
            try:
                rec["nws"] = fetch_nws(rec["lat"], rec["lon"])
            except Exception as e:
                print("FAIL nws", s, str(e)[:80])
                continue
            json.dump(rec, open(path + ".tmp", "w"), separators=(",", ":"))
            os.replace(path + ".tmp", path)
            print("ok nws", s, "hourly", len(rec["nws"].get("hourly") or []))
        return
    for s in sys.argv[1:] or WAVE0:
        try:
            rec, log = collect(s, inv)
        except Exception as e:
            print("FAIL", s, str(e)[:100], "(cache kept)")
            continue
        tmp = os.path.join(CACHE, s + ".json.tmp")
        json.dump(rec, open(tmp, "w"), separators=(",", ":"))
        os.replace(tmp, os.path.join(CACHE, s + ".json"))
        n = rec
        print("ok %s rows %d tz %s | nwps %s fc %s | nwm %s | nws periods %d alerts %s obs %s | rain %s | related %d | land %s %s" % (
            s, len(n["usgs"]["rows"]), n.get("tz"), (n.get("nwps") or {}).get("lid"), bool((n.get("nwps") or {}).get("forecast")), bool((n.get("nwm") or {}).get("points")),
            len((n.get("nws") or {}).get("periods") or []), len((n.get("nws") or {}).get("alerts") or []) if (n.get("nws") or {}).get("alerts") is not None else None, bool((n.get("nws") or {}).get("obs")),
            bool(n.get("rain")), len((n.get("related") or {}).get("items") or []), len((n.get("land") or {}).get("rows") or []) if n.get("land") else 0, "; ".join(log)))


main()
