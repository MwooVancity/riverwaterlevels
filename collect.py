"""Collector: the only code that touches the network. Writes cache/<site>.json.
Each source is fetched independently; a failed source keeps its previous cached value (and old fetched_at), it never blanks the record.
Usage: python -I collect.py [site ...]   (default: wave 0)
"""
import collections
import email.utils
import csv, os, sys, json, math, re, html, datetime, urllib.parse, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.common import *
from lib import wx
import zoneinfo

CODES = "00060,00065,00010,00300,63680,00400,00095,99133,00045,00055,72255,00480,62614,62615,72020,00062,00054"  # last five: lake elevation (62614 and 72020 NGVD29, 62615 NAVD88, 00062 above the reservoir datum) and storage
BASE = "https://api.waterdata.usgs.gov/ogcapi/v1/collections/"
NWS_H = {"User-Agent": "riverwaterlevels.com (https://riverwaterlevels.com/about/)", "Accept": "application/geo+json"}
NWPS = "https://api.water.noaa.gov/nwps/v1/"
NWPS_H = {"User-Agent": NWS_H["User-Agent"], "Accept": "application/json"}  # 2026-10-26: geo+json made reaches/{id}/streamflow?series= return only the reach summary (no medium range on any gauge)


_last = [0.0]
_last_host = {}
import time as _time, zlib, copy, threading
_tl = threading.Lock()  # NEXT runs a gauge's sources in threads: counters and per-host gaps are guarded
_host_lock = {}
NEXT = os.environ.get("COLLECT_NEXT") == "1"  # shadow design (check branch): per-run memo of shared GETs, staggered 3-hourly NWS forecast, daily retry of gauges NWPS does not know. Off = today's behaviour exactly.
HOURLY_ONLY = "--hourly-only" in sys.argv  # shadow only: a gauge with no cache gets a seeded record with every slow source marked just-fetched, so the run measures the steady hourly cost
TIME = {}  # label -> [calls, seconds]; written to state/collect-timing.json (2026-10-29: the run log showed only the total)
MEMO = {}


def _tick(label, sec, n=1):
    with _tl:
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
        host = urllib.parse.urlparse(url).netloc if NEXT else ""  # NEXT: one gap per host; today: one gap for all hosts
        with _host_lock.setdefault(host, threading.Lock()):  # the sleep is inside the lock: threads of one host queue up, other hosts go on
            wait = gap - (time.time() - (_last_host.get(host, 0.0) if NEXT else _last[0]))
            if wait > 0:
                _tick("~gap sleep", wait, 0)
                time.sleep(wait)
            _last[0] = _last_host[host] = time.time()
        try:
            r = http_json(url, headers, timeout)
            if NEXT and "api.weather.gov" in url:
                MEMO[url] = r
            return r
        except urllib.error.HTTPError as e:
            if e.code == 429 and "api.waterdata.usgs.gov" in url:
                USGS_OUT[0] = True
                raise
            if e.code not in (429, 500, 502, 503, 504) or i == tries - 1:
                raise
            ra = e.headers.get("Retry-After") or ""
            b = min(60, float(ra) if ra.replace(".", "", 1).isdigit() else 3 * 2 ** i)
            _tick("~backoff sleep", b)
            time.sleep(b)
        except (urllib.error.URLError, OSError):  # timeout, reset, DNS (HTTPError was handled above); retried in the new design only
            if not NEXT or i == tries - 1:
                raise
            b = min(30, 2 * 2 ** i)
            _tick("~backoff sleep", b)
            time.sleep(b)
    raise RuntimeError("unreachable")


def retry_json(url, headers=None, timeout=60, tries=3):
    """http_json for the NOAA map services (WPC outlooks, rain identify) that thr_json does not throttle. New design: 3 tries on 429/5xx, timeouts and resets, waits 2 s then 8 s plus up to 1 s of jitter (so 20 shards do not retry in step). Today: one try, as before."""
    for i in range(tries if NEXT else 1):
        try:
            return http_json(url, headers, timeout)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or i == tries - 1 or not NEXT:
                raise
        except (urllib.error.URLError, OSError):
            if i == tries - 1 or not NEXT:
                raise
        b = 2 * 4 ** i + (zlib.crc32(url.encode()) % 100) / 100
        _tick("~retry sleep", b)
        _time.sleep(b)


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
            rf_at = p0.get("rf_at")
            try:
                if NEXT and rflow and rf_at and not due(rf_at, 20 + zlib.crc32(site.encode()) % 8):
                    raise StopIteration  # the upstream/downstream neighbour list does not change hourly
                rf_at = now_iso()
                rf = thr_json(NWPS + "gauges/%s/riverflow" % x["lid"], NWPS_H)
                # NWPS lists upstream farthest first and downstream nearest first: keep the six nearest of each
                allp = {k: [{"LID": i.get("LID"), "Name": i.get("Name")} for i in (rf.get(k) or []) if isinstance(i, dict)] for k in ("upstream", "downstream")}
                rflow = {"upstream": allp["upstream"][-6:], "downstream": allp["downstream"][:6], "upstream_n": len(allp["upstream"]), "downstream_n": len(allp["downstream"])}
            except StopIteration:
                pass
            except Exception as e:
                rf_at = p0.get("rf_at")
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
                    "riverflow": rflow, "rf_at": rf_at, "obs_stage": obs_stage, "obs_series": obs_series, "stage_units": fl.get("stageUnits"), "crests": hist, "impacts": sorted(imp, key=lambda i: i["stage"]),
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
    for attempt in range(2):  # Overpass public API rate-limits (429); one polite retry, then leave it for the next run (the block self-hides)
        try:
            r = urllib.request.urlopen(urllib.request.Request("https://overpass-api.de/api/interpreter", data=urllib.parse.urlencode({"data": q}).encode(), headers={"User-Agent": "riverwaterlevels.com river gauge access points"}), timeout=35)
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


NWM_EMPTY = [0]  # empty National Water Model answers this run (nwm_due)


def fetch_nwm(site, prev=None):
    d = http_json("https://api.water.usgs.gov/nldi/linked-data/nwissite/USGS-%s?f=json" % site)
    comid = d["features"][0]["properties"].get("comid")
    if not comid:
        return {"fetched_at": now_iso(), "comid": None}
    j = thr_json(NWPS + "reaches/%s/streamflow?series=short_range" % comid, NWPS_H)
    s = (j.get("shortRange") or {}).get("series") or {}
    if not s.get("data"):
        NWM_EMPTY[0] += 1
    pts =[{"t": p.get("validTime"), "flow": p.get("flow")} for p in (s.get("data") or []) if isinstance(p.get("flow"), (int, float)) and p["flow"] >= 0]
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
    j = retry_json(layer_url + "/query?" + urllib.parse.urlencode(q))
    if "error" in j:
        raise RuntimeError("esri query error")
    return [f["attributes"] for f in j.get("features", [])]


def fetch_wpc(lat, lon, prev=None, site=""):
    """WPC significant river flood outlook and excessive rainfall outlook (days 1 to 3) at the gauge point, and NWS flood or flash flood local storm reports within 50 miles in the last 72 h."""
    def ms(v):
        return datetime.datetime.fromtimestamp(v / 1000, datetime.timezone.utc).isoformat() if isinstance(v, (int, float)) else None
    outlooks = []
    slow = not NEXT or not isinstance(prev, dict) or prev.get("outlooks") is None or (datetime.datetime.now(datetime.timezone.utc).hour + zlib.crc32(site.encode())) % 3 == 0
    for name, url in (("Significant river flood outlook", MAPS + "outlooks/sig_riv_fld_outlk/MapServer/0"), ("Excessive rainfall outlook, day 1", MAPS + "hazards/wpc_precip_hazards/MapServer/0"),
                      ("Excessive rainfall outlook, day 2", MAPS + "hazards/wpc_precip_hazards/MapServer/1"), ("Excessive rainfall outlook, day 3", MAPS + "hazards/wpc_precip_hazards/MapServer/2")):
        if not slow:
            outlooks = prev["outlooks"]
            break
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


def fetch_rain(lat, lon, again=NEXT):
    g = urllib.parse.quote(json.dumps({"x": lon, "y": lat, "spatialReference": {"wkid": 4326}}))
    j = retry_json("https://mapservices.weather.noaa.gov/raster/rest/services/obs/rfc_qpe/MapServer/identify?geometry=%s&geometryType=esriGeometryPoint&sr=4326&layers=all:7,8,15,16,19,20,23,24,27,28,35,36,39,40&tolerance=1&mapExtent=-125,24,-66,50&imageDisplay=1000,500,96&returnGeometry=false&f=json" % g, NWS_H)
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
        if again:  # 20 shards at once: the map service sometimes answers an empty result list; one more try after 2 s (new design only)
            _time.sleep(2)
            return fetch_rain(lat, lon, False)
        raise RuntimeError("no rain values")
    return {"fetched_at": now_iso(), "inches": vals, "valid_through": {lab: issued.get(lid[k] - 1) for k, lab in want.items() if k in by}}


def fetch_land(lat, lon):
    """Public land within 800 m of the gauge, from the USGS-hosted PAD-US fee managers layer. An ArcGIS error arrives as HTTP 200 with an "error" key: raise so the previous value stays."""
    q = urllib.parse.urlencode({"geometry": "%.5f,%.5f" % (lon, lat), "geometryType": "esriGeometryPoint", "inSR": 4326, "distance": 800, "units": "esriSRUnit_Meter", "spatialRel": "esriSpatialRelIntersects",
                                "outFields": "Unit_Nm,Mang_Name,Pub_Access", "returnGeometry": "false", "resultRecordCount": 50, "f": "json"})
    j = retry_json("https://services.arcgis.com/v01gqwM5QqNysAAi/ArcGIS/rest/services/Fee_Managers_PADUS/FeatureServer/0/query?" + q)
    if "error" in j or "features" not in j:
        raise RuntimeError("PAD-US: %s" % str(j.get("error"))[:60])
    rows = []
    for f in j["features"]:
        a = f["attributes"]
        x = [a.get("Unit_Nm"), a.get("Mang_Name"), a.get("Pub_Access")]
        if x not in rows and not (x[1] in ("UNK", "UNKL") and x[2] in ("UK", None)):
            rows.append(x)
    return {"downloaded": datetime.date.today().isoformat(), "rows": rows} if rows else None


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
    try:
        old = json.load(gzip.open(p, "rt")) if os.path.exists(p) else []
    except (OSError, EOFError, ValueError):
        old = []  # a damaged file is pulled again in full
    if old:  # only what changed (owner 2026-11-06): keep the stored record and re-pull the last 400 days, the window in which USGS still revises provisional values
        cut = (datetime.date.today() - datetime.timedelta(days=400)).isoformat()
        if not pull("&time=%s/%s" % (cut, datetime.date.today().isoformat())):
            return old  # an empty answer is an outage, never a reason to drop the last 400 days
        rows = [r for r in old if r[0] < cut] + rows
    elif pull("") >= 50000:  # the API answers at most 50,000 rows, in no time order, and refuses paging past that: a record that long (St. Louis since 1861) is pulled in 40-year windows instead
        rows = []
        for y in range(1850, datetime.date.today().year + 1, 40):
            pull("&time=%d-01-01/%d-12-31" % (y, min(y + 39, datetime.date.today().year)))
    rows = [list(x) for x in sorted({r[0]: r for r in rows}.values())]
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(rows, gzip.open(p + ".tmp", "wt"), separators=(",", ":"))
    os.replace(p + ".tmp", p)  # a run killed mid-write never leaves a broken file that every later run trips on
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
DAILY = {"snotel", "cpc", "cpc610", "usdm", "attains", "floodfreq", "acis", "ridb", "streamcat", "stocking", "rating", "uv", "dam_rise", "glsea", "usbr_lc"}
WEEKLY = {"meta", "peaks", "wtemp", "record", "year", "fieldmeas", "multiyear", "wqp"}  # wqp: samples come weekly at most; daily at 14,000 gauges would be ~40,000 portal calls a day behind a firewall that blocks bursts  # USGS history, about 6 calls per gauge: daily would be 2,300 calls/h at 9,100 gauges on a 1,000/h key; weekly in 168 slots is 325/h
USGS_OUT = [False]  # the key's hourly quota answered 429: this run stops asking for history, so live readings and the edge keep what is left
MONTHLY = {"access", "land", "cdec_res"}  # places that change over years; the slowest source when daily (Overpass took 101 of 192 s in a shard, 2026-10-31). 303 calls a day at 9,100 gauges.


RUN = {}  # ponytail: outcome counts per source for this process (one collect run per process); written by write_health()


def note(src, outcome, err=""):
    with _tl:
        c = RUN.setdefault(src, {"ok": 0, "absent": 0, "failed": 0, "err": ""})
        c[outcome] += 1
        if err:
            c["err"] = str(err)[:80]


DOWN = {}  # source -> failures in a row this run (a 404 or an empty answer is a gauge without it, not a down source)
DOWN_AFTER = 3  # the 2026-11-04 release spent 32 of 33 min on the boat-ramp source timing out at every gauge; at 3 in a row the rest of the run keeps previous values


def run_source(rec, key, fn, log):
    """Fetch one source into rec[key]. A failure keeps the previous value AND is recorded as failed: kept-previous is never counted as success."""
    t0 = _time.time()
    try:
        if DOWN.get(key, 0) >= DOWN_AFTER:
            raise OSError("skipped: failed %d times in a row this run" % DOWN[key])
        v = fn()
    except Exception as e:
        _tick("src " + key, _time.time() - t0)
        if not str(e).startswith("skipped") and "404" not in str(e) and "out of range" not in str(e):
            DOWN[key] = DOWN.get(key, 0) + 1
        log.append("%s FAILED (%s), kept previous" % (key, str(e)[:60]))
        note(key, "failed", e)
        return False
    DOWN[key] = 0
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
    The model reruns every 6 h; fetch at most every 3 h. After 3 empty answers in one run the service is out (2026-11-03: 20 s a call, empty,
    296 of 354 s of a shard): the rest wait for the next run, keeping what they have, so an outage never stretches a run toward the 45-minute brake."""
    if NWM_EMPTY[0] >= 3:
        return False
    try:
        return (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(rec["nwm"]["fetched_at"])).total_seconds() > 3 * 3600
    except (KeyError, TypeError, ValueError):
        return True


DAMS = {k: v for k, v in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "dams.json"), encoding="utf-8")).items() if not k.startswith("_")}


def fetch_dam(site, kind):
    """Dam release for the few gauges hand-matched in data/dams.json. USBR RISE: daily means (flow cfs, pool ft); USACE CWMS: latest hour or 15 minutes. None for any other gauge or kind."""
    d = DAMS.get(site)
    if not d or d["kind"] != kind:
        return None
    out = {"fetched_at": now_iso(), "dam": d["dam"], "agency": d["agency"], "kind": kind}
    today = datetime.date.today()
    if kind == "rise":
        for k, item in (("flow", d["flow"]), ("pool", d["pool"])):
            j = json.loads(get_text("https://data.usbr.gov/rise/api/result/download?type=json&itemId=%s&after=%s&before=%s" % (item, today - datetime.timedelta(days=5), today + datetime.timedelta(days=1))))
            pts = [(v["dateTime"][:10], v["result"]) for x, v in j.items() if x.isdigit() and v.get("result") is not None]
            if pts:
                t, v = max(pts)
                out[k] = {"v": v, "day": t, "unit": j.get("Units")}
        return out if out.get("flow") else None
    q = urllib.parse.urlencode({"name": d["ts"], "office": "NWDP", "begin": (datetime.datetime.utcnow() - datetime.timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ"), "end": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")})
    j = json.loads(get_text("https://cwms-data.usace.army.mil/cwms-data/timeseries?" + q, headers={"Accept": "application/json;version=2", "User-Agent": "riverwaterlevels.com"}))
    pts = [(t, v) for t, v, *_ in j.get("values") or [] if v is not None]
    if not pts:
        return None
    t, v = max(pts)
    out["flow"] = {"v": v, "t": datetime.datetime.fromtimestamp(t / 1000, datetime.timezone.utc).isoformat(), "unit": j.get("units"), "daily": "~1Day" in d["ts"]}
    return out


def fetch_wqp(site):
    """The last 3 E. coli results (last 3 years) at Water Quality Portal stations on THIS river's channel, 15 km upstream and downstream, found by NLDI river navigation (not a map box)."""
    sites = {}
    for nav in ("UM", "DM"):
        j = json.loads(get_text("https://api.water.usgs.gov/nldi/linked-data/nwissite/USGS-%s/navigation/%s/wqp?distance=15" % (site, nav)))
        for f in j.get("features", []):
            p = f["properties"]
            sites[p["identifier"]] = p.get("name") or p["identifier"]
    rows = []
    if sites:
        # WQX 3.0 profile (ChatGPT audit 2026-11-06, proven live): the legacy /data/Result/search (WQX 2.2) has no USGS results after 2024-03-11;
        # at Chattahoochee at Atlanta it returned 0 E. coli results since 2025 while WQX 3.0 returned 81, the newest from the day before
        import csv, io
        seen, ids, text = set(), list(sites), ""
        for i in range(0, len(ids), 40):  # 140 stations in one body answered "Request Entity Too Large" (Louisville); a failed chunk raises and the previous cache stays
            if i:
                _time.sleep(2)  # the portal's firewall answers 429 to bursts (seen 2026-11-06)
            body = json.dumps({"siteid": ids[i:i + 40], "characteristicName": ["Escherichia coli"], "startDateLo": (datetime.date.today() - datetime.timedelta(days=1095)).strftime("%m-%d-%Y"), "mimeType": "csv", "dataProfile": "basicPhysChem"}).encode()
            r = urllib.request.urlopen(urllib.request.Request("https://www.waterqualitydata.us/wqx3/Result/search", data=body, headers={"Content-Type": "application/json", "Accept": "text/csv", "User-Agent": "riverwaterlevels.com"}), timeout=120)
            part = r.read().decode("utf-8", "ignore")
            text += part if not text else part.partition("\n")[2]  # later chunks repeat the CSV header
        for x in csv.DictReader(io.StringIO(text)):
            v = x.get("Result_Measure") or ""
            if v == "ND" or not v:
                v = x.get("Result_ResultDetectionCondition") or ""
            k = (x.get("Location_Identifier"), x.get("Activity_StartDate"), v)
            if not v or k in seen or not k[0] or not k[1]:
                continue
            seen.add(k)
            rows.append({"date": k[1], "value": v, "unit": "" if (x.get("Result_MeasureUnit") or "").lower() == "none" else x.get("Result_MeasureUnit") or "", "site": sites.get(k[0], x.get("Location_Name") or k[0]), "id": k[0], "status": x.get("Result_MeasureStatusIdentifier") or ""})
        rows.sort(key=lambda r: r["date"], reverse=True)
    return {"fetched_at": now_iso(), "n_sites": len(sites), "rows": rows[:3]}


def fetch_uv(rec):
    """EPA daily UV index for today by ZIP; the ZIP comes from the Census geocoder once per gauge and is kept."""
    z = (rec.get("uv") or {}).get("zip")
    if not z:
        j = json.loads(get_text("https://geocoding.geo.census.gov/geocoder/geographies/coordinates?x=%.5f&y=%.5f&benchmark=Public_AR_Current&vintage=Current_Current&layers=all&format=json" % (rec["lon"], rec["lat"])))
        zs = [x.get("ZCTA5") for k, v in j["result"]["geographies"].items() if "ZIP Code" in k for x in v]
        z = zs[0] if zs and zs[0] else None
        if not z:
            return None
    j = json.loads(get_text("https://data.epa.gov/efservice/getEnvirofactsUVDAILY/ZIP/%s/JSON" % z))
    if not j:
        return {"zip": z, "fetched_at": now_iso()}
    d = datetime.datetime.strptime(j[0]["DATE"], "%b/%d/%Y").date().isoformat()
    return {"zip": z, "index": int(j[0]["UV_INDEX"]), "date": d, "fetched_at": now_iso()}


LAKE_TWDB = {r["site"]: r.get("twdb") for r in csv.DictReader(open(os.path.join(ROOT, "data", "lakes.csv"), encoding="utf-8"))}
COAST_KEYS = {"cpc", "cpc610", "usdm", "acis", "tides", "airnow", "uv", "access", "land", "twdb", "cdec_res", "glsea", "usbr_lc"}  # sources asked by place; the rest are USGS-id lookups a CO-OPS id would only waste
COAST_BUOY = {r["site"]: (r["buoy"], r["buoy_owner"], r["buoy_km"]) for r in csv.DictReader(open(os.path.join(ROOT, "data", "coasts.csv"), encoding="utf-8")) if r.get("buoy")}  # hand-checked: owner terms read (NDBC = NWS public domain, SCRIPPS = CDIP 'not altered' + credit); partner buoys with unread terms are left out
COASTS = {r["site"] for r in csv.DictReader(open(os.path.join(ROOT, "data", "coasts.csv"), encoding="utf-8"))}  # NOAA CO-OPS stations with a coast page (plan 2026-11-06 step 2)
AGENCY = {r["site"]: r["source"] for r in csv.DictReader(open(os.path.join(ROOT, "data", "lakes.csv"), encoding="utf-8")) if r.get("source")}  # lakes read from their operator's own feed (cdec:SHA); USGS has no gauge there
NOUSGS = COASTS | set(AGENCY)  # ids USGS does not know: every USGS-id call is skipped for them


def fetch_cdec(sta):
    """California Data Exchange Center hourly reservoir elevation (sensor 6, ft) and storage (sensor 15, acre-ft), last 3 days.
    CDEC's own data page (wsSensorData, read 2026-11-07): 'Dates, times, and output will always be Pacific Standard Time', so every time is -08:00 all year.
    -9999 is CDEC's missing value: dropped, never shown as a number. 1 call per run."""
    today = datetime.date.today()
    j = http_json("https://cdec.water.ca.gov/dynamicapp/req/JSONDataServlet?Stations=%s&SensorNums=6,15&dur_code=H&Start=%s&End=%s" % (sta, today - datetime.timedelta(days=3), today + datetime.timedelta(days=1)), {}, 60)
    pst, code = datetime.timezone(datetime.timedelta(hours=-8)), {6: ("AGY", "ft"), 15: ("00054", "acre-ft")}
    rows = [{"parameter_code": code[x["SENSOR_NUM"]][0], "time": datetime.datetime.strptime(x["date"], "%Y-%m-%d %H:%M").replace(tzinfo=pst).isoformat(), "value": str(x["value"]),
             "unit_of_measure": code[x["SENSOR_NUM"]][1], "qualifier": None, "approval_status": "Provisional"}
            for x in j if x.get("SENSOR_NUM") in code and isinstance(x.get("value"), (int, float)) and x["value"] != -9999 and x.get("stationId") == sta]
    if not any(r["parameter_code"] == "AGY" for r in rows):
        raise RuntimeError("CDEC %s: no elevation rows" % sta)
    return {"fetched_at": now_iso(), "rows": rows, "truncated": [], "agency": "cdec", "station": sta}


def fetch_rise(item):
    """U.S. Bureau of Reclamation RISE daily lake elevation, last 10 days. The file states 'Timestep': 'daily', 'Aggregation': 'instant' and
    'Datetime values are presented as UTC' (Mead: 07:00 UTC = midnight Arizona). A unit other than ft raises: the page never guesses a unit. 1 call per run."""
    today = datetime.date.today()
    j = json.loads(get_text("https://data.usbr.gov/rise/api/result/download?type=json&itemId=%s&after=%s&before=%s" % (item, today - datetime.timedelta(days=10), today + datetime.timedelta(days=1))))
    if j.get("Units") != "ft" or "UTC" not in (j.get("Note") or ""):
        raise RuntimeError("RISE %s: unit %r or time note changed" % (item, j.get("Units")))
    rows = [{"parameter_code": "AGY", "time": v["dateTime"].replace(" ", "T") + "+00:00", "value": str(v["result"]), "unit_of_measure": "ft", "qualifier": None, "approval_status": "Provisional"}
            for k, v in j.items() if k.isdigit() and isinstance(v.get("result"), (int, float))]
    if not rows:
        raise RuntimeError("RISE %s: no elevation rows" % item)
    return {"fetched_at": now_iso(), "rows": sorted(rows, key=lambda r: r["time"]), "truncated": [], "agency": "rise", "station": item}


_TWDB = {}


def twdb_rows(slug):
    """TWDB 30-day file rows, fetched once per 10 minutes: the reading series and the reservoir card read the same file (review 2026-11-07 #9: it was downloaded twice a run).
    ponytail: one dict entry per lake, about 10 KB each; a long-lived process keeps at most one copy per lake."""
    k = int(_time.time() // 600)
    if _TWDB.get(slug, (None,))[0] != k:
        _TWDB[slug] = (k, [l.split(",") for l in http_raw("https://www.waterdatafortexas.org/reservoirs/individual/%s-30day.csv" % slug, 60).decode("utf-8", "replace").splitlines() if l and not l.startswith("#")])
    return _TWDB[slug][1]


def fetch_twdb_series(slug):
    """TWDB 30-day file for one reservoir: 'Estimated daily average data' (file header), so each row is a whole day, dated, with no clock time.
    Stored at local midnight (Texas, America/Chicago); the page prints the date with 'TWDB daily average', never the midnight time. 1 call per run."""
    rows_ = twdb_rows(slug)
    hd, zone = rows_[0], zoneinfo.ZoneInfo("America/Chicago")
    rows = []
    for r in (dict(zip(hd, x)) for x in rows_[1:]):
        t = datetime.datetime.combine(datetime.date.fromisoformat(r["date"]), datetime.time(0), tzinfo=zone).isoformat()
        for k, code, unit in (("water_level", "AGY", "ft"), ("reservoir_storage", "00054", "acre-ft")):
            if r.get(k) not in (None, "", "NA"):
                rows.append({"parameter_code": code, "time": t, "value": r[k], "unit_of_measure": unit, "qualifier": None, "approval_status": "Provisional"})
    if not any(r["parameter_code"] == "AGY" for r in rows):
        raise RuntimeError("TWDB %s: no water level rows" % slug)
    return {"fetched_at": now_iso(), "rows": rows, "truncated": [], "agency": "twdb", "station": slug}


def fetch_cdec_res(sta):
    """CDEC's reservoir profile page (dynamicapp/profile?s=SHA&type=res): capacity and the 1991-2020 monthly average storage, as CDEC prints them.
    Read monthly. Raises when the capacity or any of the 12 months is missing, so the block hides instead of guessing."""
    t = html.unescape(re.sub(r"<[^>]+>", " ", http_raw("https://cdec.water.ca.gov/dynamicapp/profile?s=%s&type=res" % sta, 60).decode("utf-8", "replace")))
    t = re.sub(r"\s+", " ", t)
    cap = re.search(r"Capacity ([0-9,]+) af", t)
    yrs = re.search(r"Start Year Avg\. (\d{4}) End Year Avg\. (\d{4})", t)
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    avg = {i + 1: re.search(r"%s ([0-9,]+) af" % m, t) for i, m in enumerate(months)}
    if not cap or not yrs or not all(avg.values()):
        raise RuntimeError("CDEC profile %s: capacity or monthly averages missing" % sta)
    return {"fetched_at": now_iso(), "cap_af": int(cap.group(1).replace(",", "")), "avg_from": yrs.group(1), "avg_to": yrs.group(2), "avg_af": {k: int(v.group(1).replace(",", "")) for k, v in avg.items()}}


def fetch_coops_lake(st):
    """NOAA CO-OPS Great Lakes station: 3 days of 6-minute water level above IGLD 1985 (the datum CO-OPS names for its Great Lakes stations; no tides,
    so no MLLW and no predictions) and the latest water temperature where the station has the sensor. 2 calls per run."""
    t = lambda s: s.replace(" ", "T") + ":00+00:00"
    wl = coops_get(st, "product=water_level&datum=IGLD&range=72")
    rows = [{"parameter_code": "IGLD", "time": t(r["t"]), "value": r["v"], "unit_of_measure": "ft", "qualifier": None, "approval_status": "Preliminary" if r.get("q") == "p" else "Verified" if r.get("q") == "v" else "Unknown"} for r in wl if r.get("v") not in (None, "")]
    if not rows:
        raise RuntimeError("no CO-OPS IGLD water level rows for %s" % st)
    wt = [r for r in coops_get(st, "product=water_temperature&range=72") if r.get("v") not in (None, "")]
    if wt and not wt_suspect([float(r["v"]) for r in wt]):  # a swinging sensor is held, never shown as the lake
        rows.append({"parameter_code": "00010", "time": t(wt[-1]["t"]), "value": str(round((float(wt[-1]["v"]) - 32) / 1.8, 2)), "unit_of_measure": "degC", "qualifier": None, "approval_status": "Preliminary"})
    return {"fetched_at": now_iso(), "rows": rows, "truncated": [], "agency": "coops", "station": st}


GLSEA_LAKE = {"Lake Superior": "s", "Lake Michigan": "m", "Lake Huron": "h", "Lake Erie": "e", "Lake Ontario": "o"}
LAKE_NAME = {r["site"]: r["lake"] for r in csv.DictReader(open(os.path.join(ROOT, "data", "lakes.csv"), encoding="utf-8"))}


def fetch_glsea(letter):
    """NOAA GLERL CoastWatch GLSEA lake-wide average surface water temperature (satellite analysis), one CSV per lake: day of year, the 1995-<last year>
    average, then this year's daily values in deg F (header ',Average (1995-2025),2026', read 2026-11-07, 10 KB). The newest filled day is the reading;
    its date is the day of year in the header's year. The file lags 1-2 days. A header that is not 'Average (yyyy-yyyy),yyyy' raises: never a guessed column."""
    t = http_raw("https://apps.glerl.noaa.gov/coastwatch/webdata/statistic/csv/avgtemps-%s_1995-%d_F.csv" % (letter, datetime.date.today().year), 60).decode("utf-8", "replace")
    lines = [l.split(",") for l in t.splitlines() if l.strip()]
    m = re.fullmatch(r"Average \((\d{4})-(\d{4})\)", lines[0][1].strip()) if len(lines[0]) == 3 else None
    if not m or not re.fullmatch(r"\d{4}", lines[0][2].strip()):
        raise RuntimeError("GLSEA header changed: %r" % lines[0])
    yr = int(lines[0][2])
    got = [(int(d), float(a), float(v)) for d, a, v in (l[:3] for l in lines[1:] if len(l) >= 3) if d.strip().isdigit() and v.strip() and a.strip()]
    if not got:
        raise RuntimeError("GLSEA %s: no %d values" % (letter, yr))
    doy, avg, val = got[-1]
    day = datetime.date(yr, 1, 1) + datetime.timedelta(days=doy - 1)
    return {"fetched_at": now_iso(), "lake": letter, "date": day.isoformat(), "temp_f": val, "avg_f": avg, "avg_from": m.group(1), "avg_to": m.group(2)}


def fetch_lc_mead():
    """Reclamation Lower Colorado Region daily table (usbr.gov/lc/region/g4000/hourly/levels.html, read 2026-11-07): 'AVAILABLE RESERVOIR ELEVATIONS AND
    CONTENTS FOR <MONTH YEAR>', Lake Mead 'AVAILABLE CAPACITY IN A.F. *26120000' at 'ELEVATION IN FEET 1219.6' ('* BOTTOM OF EXCLUSIVE FLOOD CONTROL SPACE'),
    and one row per day: day, total system storage, available space, Hoover elevation (ft), content (1000 A.F.). The newest row is used. 1 call a day.
    Any of these not found raises: the block hides, nothing is guessed."""
    t = re.sub(r"<[^>]+>", "", http_raw("https://www.usbr.gov/lc/region/g4000/hourly/levels.html", 60).decode("utf-8", "replace"))
    hd = re.search(r"AVAILABLE RESERVOIR ELEVATIONS AND CONTENTS FOR ([A-Z]+) (\d{4})", t)
    if not hd:
        raise RuntimeError("Reclamation LC table header not found")
    part = t[hd.end():]
    cap = re.search(r"AVAILABLE CAPACITY IN A\.F\.\s+\*?(\d+)", part)
    cel = re.search(r"ELEVATION IN FEET\s+([\d.]+)", part)
    rows = re.findall(r"^\s+(\d{1,2})\s+[\d.]+\s+[\d.]+\s+(\d{3,4}\.\d+)\s+(\d{3,5})\s+\d+", part.split("BOTTOM OF EXCLUSIVE")[0], re.M)
    if not cap or not cel or not rows:
        raise RuntimeError("Reclamation LC table: capacity, its elevation or day rows missing")
    mon = datetime.datetime.strptime(hd.group(1).title(), "%B").month
    days = {datetime.date(int(hd.group(2)), mon, int(d)).isoformat(): [float(el), int(kaf) * 1000] for d, el, kaf in rows}  # every day of the month: the page matches the day RISE last published
    return {"fetched_at": now_iso(), "days": days, "cap_af": int(cap.group(1)), "cap_elev_ft": float(cel.group(1))}


def fetch_agency(site):
    kind, sid = AGENCY[site].split(":", 1)
    return {"cdec": fetch_cdec, "rise": fetch_rise, "twdb": fetch_twdb_series, "coops": fetch_coops_lake}[kind](sid)  # a source with no fetch here raises: the cache is kept, the page is never built from nothing
COOPS = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?station=%s&time_zone=gmt&units=english&format=json&application=riverwaterlevels.com&"


def coops_get(st, q):
    """One CO-OPS product; NOAA answers a missing product with an error object, which becomes an empty list (Unknown on the page, never zero)."""
    j = http_json(COOPS % st + q, NWS_H, 60)
    return j.get("data") or j.get("predictions") or []


def fetch_buoy(st):
    """The newest row of the station's hand-checked buoy (NDBC realtime2 standard meteorological file): wave height, dominant period, mean wave
    direction, sea temperature, in the units the file states (m, s, degT, degC). 'MM' (missing) stays None, shown Unknown, never zero. 1 call."""
    b = COAST_BUOY.get(st)
    if not b:
        return None
    lines = [l.split() for l in http_raw("https://www.ndbc.noaa.gov/data/realtime2/%s.txt" % b[0], 60).decode("utf-8", "replace").splitlines()]
    hd, row = lines[0], next(l for l in lines[2:] if len(l) == len(lines[0]))
    d = dict(zip([h.lstrip("#") for h in hd], row))
    num = lambda k: float(d[k]) if d.get(k) not in (None, "MM") else None
    return {"fetched_at": now_iso(), "id": b[0], "owner": b[1], "km": float(b[2]), "time": "%s-%s-%sT%s:%s:00+00:00" % (d["YY"], d["MM"], d["DD"], d["hh"], d["mm"]),
            "wvht_m": num("WVHT"), "dpd_s": num("DPD"), "mwd_deg": num("MWD"), "wtmp_c": num("WTMP")}


def fetch_coops(st):
    """NOAA CO-OPS coast station: 3 days of 6-minute observed water level above MLLW (quality flag kept: 'p' = preliminary), the same span of
    6-minute predictions (observed minus predicted is the page's 'compared with the tide forecast', our calculation), the next 3 days of
    high and low tide predictions, and the latest water temperature. 4 calls per station per run; a product the station lacks is an empty list."""
    t = lambda s: s.replace(" ", "T") + ":00+00:00"
    wl = coops_get(st, "product=water_level&datum=MLLW&range=72")
    if not wl:
        raise RuntimeError("no CO-OPS water level rows for %s" % st)
    rows = [{"parameter_code": "MLLW", "time": t(r["t"]), "value": r["v"], "unit_of_measure": "ft", "qualifier": None, "approval_status": "Preliminary" if r.get("q") == "p" else "Verified" if r.get("q") == "v" else "Unknown"} for r in wl if r.get("v") not in (None, "")]
    wt = [r for r in coops_get(st, "product=water_temperature&range=72") if r.get("v") not in (None, "")]
    vs = [float(r["v"]) for r in wt]
    suspect = wt_suspect(vs)  # held, never shown as the sea
    for r in ([] if suspect else wt[-1:]):
        if r.get("v") not in (None, ""):
            rows.append({"parameter_code": "00010", "time": t(r["t"]), "value": str(round((float(r["v"]) - 32) / 1.8, 2)), "unit_of_measure": "degC", "qualifier": None, "approval_status": "Preliminary"})
    begin = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=3)).strftime("%Y%m%d %H:%M")
    pred = coops_get(st, "product=predictions&datum=MLLW&interval=6&begin_date=%s&range=96" % urllib.parse.quote(begin))
    hilo = coops_get(st, "product=predictions&datum=MLLW&interval=hilo&begin_date=%s&range=72" % datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d"))
    return {"fetched_at": now_iso(), "rows": rows, "truncated": []}, {"fetched_at": now_iso(), "station": st, "pred": [[t(p["t"]), float(p["v"])] for p in pred], "hilo": [[t(p["t"]), float(p["v"]), p["type"]] for p in hilo], "wt_suspect": [min(vs), max(vs)] if suspect else None}


def fetch_twdb(slug):
    """Texas Water Development Board daily reservoir estimate (last 30 days file): its % of conservation capacity, storages and area.
    TWDB defines percent_full = conservation storage / conservation capacity (header of the file); the page names that basis."""
    rows = twdb_rows(slug)
    hd, last = rows[0], rows[-1]
    r = dict(zip(hd, last))
    if r.get("date", "")[:2] != "20" or not r.get("percent_full"):
        raise RuntimeError("TWDB file parsed to nothing")
    num = lambda k: float(r[k]) if r.get(k) not in (None, "", "NA") else None
    return {"date": r["date"], "elev_ft": num("water_level"), "area_ac": num("surface_area"), "storage_af": num("reservoir_storage"), "cons_storage_af": num("conservation_storage"),
            "pct_cons": num("percent_full"), "cons_cap_af": num("conservation_capacity"), "dead_pool_af": num("dead_pool_capacity"), "slug": slug, "fetched_at": now_iso()}


def fetch_extras(site, rec, h, log):
    """Blocks added in the final-form pass. Each source is independent; a failure keeps the previous cached value."""
    lat, lon = rec["lat"], rec["lon"]
    for gone in ("echo", "openfema", "storms"):  # sources no page shows any more (owner 2026-10-20): drop them from caches restored from older runs
        rec.pop(gone, None)
    want = next((a[7:].split(",") for a in sys.argv if a.startswith("--keys=")), None)
    for key, fn in (("meta", lambda: fetch_meta(site, h)), ("peaks", lambda: fetch_peaks(site, h)), ("wtemp", lambda: fetch_wtemp(site, h)), ("snotel", lambda: fetch_snotel(lat, lon)), ("cpc", lambda: fetch_cpc(lat, lon)), ("usdm", lambda: fetch_usdm(rec)), ("attains", lambda: fetch_attains(lat, lon)),
                    ("record", lambda: record_summary(fetch_daily(site, h), rec.get("stats"))), ("year", lambda: fetch_year(site, h)), ("fieldmeas", lambda: fetch_fieldmeas(site, h)), ("floodfreq", lambda: fetch_floodfreq(site)), ("cpc610", lambda: fetch_cpc(lat, lon, "cpc_6_10_day_outlk")),
                    ("related", lambda: related_lag(rec, h)), ("acis", lambda: fetch_acis(rec)), ("tides", lambda: fetch_tides(lat, lon)), ("cameras", lambda: fetch_cameras(site, h)), ("airnow", lambda: fetch_airnow(lat, lon)), ("ridb", lambda: fetch_ridb(lat, lon)), ("near_wtemp", lambda: fetch_near_wtemp(site, lat, lon, rec.get("river_name"), h)),
                    ("streamcat", lambda: fetch_streamcat(site, rec)), ("stocking", lambda: fetch_stocking(lat, lon)), ("access", lambda: fetch_access(lat, lon)), ("land", lambda: fetch_land(lat, lon)),
                    ("rating", lambda: fetch_rating(site)), ("wqp", lambda: fetch_wqp(site)), ("uv", lambda: fetch_uv(rec)),
                    *(((("dam_" + DAMS[site]["kind"]), lambda: fetch_dam(site, DAMS[site]["kind"])),) if site in DAMS else ()),
                    *((("twdb", lambda: fetch_twdb(LAKE_TWDB[site])),) if LAKE_TWDB.get(site) else ()),
                    *((("cdec_res", lambda: fetch_cdec_res(AGENCY[site][5:])),) if AGENCY.get(site, "").startswith("cdec:") else ()),
                    *((("usbr_lc", fetch_lc_mead),) if AGENCY.get(site) == "rise:6123" else ()),
                    *((("glsea", lambda: fetch_glsea(GLSEA_LAKE[LAKE_NAME[site]])),) if LAKE_NAME.get(site) in GLSEA_LAKE else ()),
                    ("multiyear", lambda: multiyear(fetch_daily(site, h)))):
        if want and key not in want:
            continue
        if site in NOUSGS and key not in COAST_KEYS:
            continue
        stamp = rec.setdefault("_fetched", {})
        if key in WEEKLY and USGS_OUT[0]:
            continue
        if not want and not (due(stamp.get(key), 720) if key in MONTHLY else week_due(stamp.get(key), site) if key in WEEKLY else daily_due(stamp.get(key)) if key in DAILY else due(stamp.get(key), 24 if NEXT and key in ("related", "near_wtemp", "cameras") else 6)):
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
    coast = site in COASTS
    if coast:
        rec["usgs"], rec["coops"] = fetch_coops(site)  # critical: raises, cache kept
        try:
            rec["buoy"] = fetch_buoy(site)
        except Exception as e:  # waves hide alone; the page still ships
            note("buoy", "failed", e)
    elif site in AGENCY:
        rec["usgs"] = fetch_agency(site)  # critical: raises, cache kept
    else:
        rec["usgs"] = fetch_usgs(site, h)  # critical: raises, cache kept
    log = []
    for key, fn in (("related", lambda: fetch_related(site, inv, h, rec.get("related"))), ("nwps", lambda: fetch_nwps(site, lat, lon, rec.get("nwps"))), ("nws", lambda: fetch_nws(lat, lon, rec.get("nws"), site)), ("rain", lambda: fetch_rain(lat, lon)), ("wpc", lambda: fetch_wpc(lat, lon, rec.get("wpc"), site))):
        if site in NOUSGS and key in ("related", "nwps"):  # a CO-OPS or CDEC id is not a USGS or NWPS gauge id: those calls would spend the USGS key for nothing
            continue
        run_source(rec, key, fn, log)
    if nwm_due(rec) and site not in NOUSGS:
        run_source(rec, "nwm", lambda: fetch_nwm(site, rec.get("nwm")), log)
    sp = os.path.join(LEGACY, "stats", site + ".json")
    note("stats", "ok" if os.path.exists(sp) else "absent")  # input file, not a fetch: absent here means "is this normal" shows "-" (2026-10-25: 28 gauges)
    if os.path.exists(sp):
        _sj = json.load(open(sp))
        rec["stats"], rec["stats_code"] = _sj["d"], _sj.get("code", "00060")
        rec["stats_source"] = "USGS daily statistics, downloaded " + datetime.date.fromtimestamp(os.path.getmtime(sp)).isoformat()
    if site not in NOUSGS:
        run_source(rec, "record", lambda: record_summary(fetch_daily(site, h), rec.get("stats")), log)
    fetch_extras(site, rec, h, log)
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


def merge_rows(old, new):
    """USGS's newest word on each reading wins: (rows, new count, corrected count). A provisional value can change after we first saw it."""
    rows = {(r["parameter_code"], r["time"]): r for r in old}
    add = fixed = 0
    for r in new:
        k = (r["parameter_code"], r["time"])
        if k not in rows:
            add += 1
        elif (rows[k].get("value"), rows[k].get("qualifier")) != (r.get("value"), r.get("qualifier")):
            fixed += 1
        rows[k] = r
    return list(rows.values()), add, fixed


def add_latest(rows, latest):
    """The reading the edge shows (latest-continuous) joins the page's series when the series lacks that time; a continuous row of the same time wins."""
    have = {(r["parameter_code"], r["time"]) for r in rows}
    return rows + [r for r in latest if (r["parameter_code"], r["time"]) not in have]


def fast_usgs(sites, h, q="continuous/items?time=P8D&last_modified=PT6H&parameter_code=" + CODES):
    """Every reading USGS wrote or corrected in the last 6 hours for every gauge, in bulk (a correction rewrites days of old readings: Animas 2026-11-02, 352 rows): 300 ids per call (URL stays ~5 KB) with next-link paging, so
    nothing is dropped past 10,000 rows. Rows in the same shape as fetch_usgs. One or two calls at today's size; it replaces the
    per-gauge fast_fill calls (2026-10-25 review: about one call per gauge per run, ~18,000/h at 9,099 gauges)."""
    out = {}
    for i in range(0, len(sites), 300):
        url, pages = BASE + q + "&monitoring_location_id=%s&limit=10000&skipGeometry=true&f=json" % ",".join("USGS-" + s for s in sites[i:i + 300]), 0
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


SLOW_KEYS = sorted(DAILY | MONTHLY | {"related", "tides", "cameras", "airnow", "near_wtemp"}) + ["usgs_full", "related_list"]


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
    usites = [s for s in sites if s not in NOUSGS]  # coast stations (NOAA CO-OPS) and agency lakes (CDEC) are refreshed per station below
    try:
        new = fast_usgs(usites, h)
    except Exception as e:  # USGS unavailable or rate-limited: still refresh the weather sources
        print("FAIL usgs bulk", str(e)[:100])
        note("usgs", "failed", e)
        new = {}
    latest = fast_usgs(usites, h, "latest-continuous/items?parameter_code=00060,00065")  # what the Worker shows; 1 call per 300 gauges (47/h at 14,000)
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
            cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=8)).isoformat()
            if s in COASTS:  # the whole 3-day CO-OPS window every run: 4 calls, no USGS key
                try:
                    cu_, rec["coops"] = fetch_coops(s)
                    new[s] = cu_["rows"]
                    rec["buoy"] = fetch_buoy(s)
                except Exception as e:
                    log.append("coops FAILED (%s), kept previous" % str(e)[:60])
                    note("coops", "failed", e)
            if s in AGENCY:  # the operator's 3-day window every run: 1 call
                try:
                    new[s] = fetch_agency(s)["rows"]
                    note(AGENCY[s].split(":")[0], "ok")
                except Exception as e:
                    log.append("agency FAILED (%s), kept previous" % str(e)[:60])
                    note(AGENCY[s].split(":")[0], "failed", e)
            rows, add, fixed = merge_rows(rec["usgs"]["rows"], new.get(s, []))
            rec["usgs"]["rows"] = [r for r in rows if str(r["time"]) >= cutoff]
            if add or fixed:
                rec["usgs"]["fetched_at"] = now_iso()
            if fixed:
                rec["_revised"] = now_iso()  # build.py rebuilds this page at once
            note("usgs", "ok" if s in new else "absent")
            srcs = [("nwps", lambda: fetch_nwps(s, rec["lat"], rec["lon"], rec.get("nwps"))), ("nws", lambda: fetch_nws(rec["lat"], rec["lon"], rec.get("nws"), s)), ("rain", lambda: fetch_rain(rec["lat"], rec["lon"])), ("wpc", lambda: fetch_wpc(rec["lat"], rec["lon"], rec.get("wpc"), s))]
            if s in NOUSGS:
                srcs = [x for x in srcs if x[0] != "nwps"]
            elif nwm_due(rec):
                srcs.append(("nwm", lambda: fetch_nwm(s, rec.get("nwm"))))
            if NEXT:  # the sources of one gauge wait on different hosts: run them side by side (each key is its own rec field; the per-host gap lock keeps the politeness)
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(len(srcs)) as ex:
                    list(ex.map(lambda kf: run_source(rec, kf[0], kf[1], log), srcs))
            else:
                for key, fn in srcs:
                    run_source(rec, key, fn, log)
            stamp = rec.setdefault("_fetched", {})
            if s not in NOUSGS and day_due(stamp.get("usgs_full"), s):  # once a day, in this gauge's own hour, the whole 8-day series again: USGS revises provisional readings
                try:
                    rec["usgs"], stamp["usgs_full"] = fetch_usgs(s, h), now_iso()
                except Exception as e:
                    log.append("usgs_full FAILED (%s), kept previous" % str(e)[:60])
                    note("usgs_full", "failed", e)
            rec["usgs"]["rows"] = add_latest(rec["usgs"]["rows"], [r for r in latest.get(s, []) if str(r["time"]) >= cutoff])  # the service returns decades-old values for dead sensors
            if s not in NOUSGS and day_due(stamp.get("related_list"), s) and run_source(rec, "related", lambda: fetch_related(s, inv, h, rec.get("related")), log):
                stamp["related_list"] = now_iso()
            sp = os.path.join(LEGACY, "stats", s + ".json")
            note("stats", "ok" if os.path.exists(sp) else "absent")  # same input-file note as the full path, so the doctor sees it every run
            if os.path.exists(sp):
                _sj = json.load(open(sp))
                rec["stats"], rec["stats_code"] = _sj["d"], _sj.get("code", "00060")
                rec["stats_source"] = "USGS daily statistics, downloaded " + datetime.date.fromtimestamp(os.path.getmtime(sp)).isoformat()
            fetch_extras(s, rec, h, log)
            rec["tz"] = (rec.get("nws") or {}).get("tz") or rec.get("tz")
            rec["fetched_at"] = now_iso()
            json.dump(rec, open(path + ".tmp", "w"), separators=(",", ":"))
            os.replace(path + ".tmp", path)
            print("ok", s, "new usgs rows", add, "corrected", fixed, "; ".join(log))
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
    if not any(a.startswith("--shard=") and not a.startswith("--shard=0/") for a in sys.argv):
        fetch_twdb_state()
        fetch_world()
        write_health("run", len(sites))  # world feeds run last: without this no alarm could see them
        fetch_census()


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


ECCC_ZONE = {"BC": "America/Vancouver", "AB": "America/Edmonton", "SK": "America/Regina", "MB": "America/Winnipeg", "ON": "America/Toronto", "QC": "America/Toronto", "NB": "America/Halifax", "NS": "America/Halifax", "PE": "America/Halifax", "NL": "America/St_Johns", "YT": "America/Whitehorse", "NT": "America/Edmonton", "NU": "America/Toronto"}


def eccc_zone(p, lon, lat=None):
    """Province zone, split where a province spans zones by the station's standard offset in the feed: east BC, northwest Ontario, Labrador, Nunavut's three, Quebec east of 63 W
    (Lower North Shore, no daylight time) and the Magdalen Islands (Atlantic with daylight time, south of 48 N), west Saskatchewan (Lloydminster). Review 2026-11-04: Nunavut read Toronto."""
    prov, std = p["PROV_TERR_STATE_LOC"], (p.get("DATETIME_LST") or "")[-6:]
    if prov == "BC" and (lon or -130) > -117.5:
        return "America/Edmonton"
    return {("ON", "-06:00"): "America/Winnipeg", ("NL", "-04:00"): "America/Halifax", ("NU", "-05:00"): "America/Iqaluit", ("NU", "-06:00"): "America/Rankin_Inlet", ("NU", "-07:00"): "America/Cambridge_Bay",
            ("QC", "-04:00"): "America/Blanc-Sablon" if (lat or 0) >= 48 else "America/Halifax", ("SK", "-07:00"): "America/Edmonton"}.get((prov, std)) or ECCC_ZONE.get(prov, "UTC")


def fetch_eccc(sid, prev):
    """One Canadian gauge: 8 days of 5-minute level and flow, and monthly means once a week. Canada publishes no low or high label, so ours is a rank among past years, said as ours."""
    api = "https://api.weather.gc.ca/collections/"
    live = http_json(api + "hydrometric-realtime/items?f=json&STATION_NUMBER=%s&limit=2400&sortby=-DATETIME&properties=DATETIME,DATETIME_LST,LEVEL,LEVEL_SYMBOL_EN,DISCHARGE,STATION_NAME,PROV_TERR_STATE_LOC" % sid, {}, 30)["features"]
    pts = [f["properties"] for f in live if f["properties"].get("LEVEL") is not None][::-1]
    if not pts:
        raise RuntimeError("no Canadian readings")
    prev = prev or {}
    months = prev.get("months")
    if not months or due(prev.get("months_at"), 168) or "peaks" not in prev:  # "peaks" added 2026-11-04: one early refresh per gauge
        hist = http_json(api + "hydrometric-monthly-mean/items?f=json&STATION_NUMBER=%s&limit=1500" % sid, {}, 30)["features"]
        months = {}
        for f in sorted(hist, key=lambda f: f["properties"]["DATE"]):
            p = f["properties"]
            if p.get("MONTHLY_MEAN_LEVEL") is not None:
                months.setdefault(p["DATE"][5:7], []).append(round(p["MONTHLY_MEAN_LEVEL"], 3))
        years = [f["properties"] for f in http_json(api + "hydrometric-annual-statistics/items?f=json&STATION_NUMBER=%s&limit=400" % sid, {}, 30)["features"] if f["properties"].get("DATA_TYPE_EN") == "Water Level"]
        tops, lows = [p["MAX_VALUE"] for p in years if p.get("MAX_VALUE") is not None], [p["MIN_VALUE"] for p in years if p.get("MIN_VALUE") is not None]
        try:  # instantaneous yearly peaks (HYDAT); flagged peaks (ice B, estimated E, partial A) are left out, never shown as plain values
            prev = dict(prev, peaks=sorted([int(p["IDENTIFIER"].split(".")[1]), round(p["PEAK"], 3), (p.get("DATE") or "")[:10]] for p in (f["properties"] for f in http_json(api + "hydrometric-annual-peaks/items?f=json&STATION_NUMBER=%s&limit=500" % sid, {}, 30)["features"])
                                         if p.get("DATA_TYPE_EN") == "Water Level" and p.get("PEAK_CODE_EN") == "Maximum" and p.get("PEAK") is not None and not p.get("SYMBOL_EN"))[-15:])
        except Exception as e:
            print("annual peaks failed", sid, str(e)[:100])
            prev = dict(prev, peaks=prev.get("peaks") or [])  # keep the last good list; [] stops a retry every run until the weekly refresh
        prev = dict(prev, years=[[int(p["IDENTIFIER"].split(".")[1]), round(p["MAX_VALUE"], 3), p.get("MAX_DATE"), round(p["MIN_VALUE"], 3), p.get("MIN_DATE")] for p in years if p.get("MAX_VALUE") is not None and p.get("MIN_VALUE") is not None][-15:], record=dict({"HHW": round(max(tops), 3)} if tops else {}, **({"NNW": round(min(lows), 3)} if lows else {})), drainage=(http_json(api + "hydrometric-stations/items?f=json&STATION_NUMBER=%s&limit=1" % sid, {}, 30)["features"] or [{"properties": {}}])[0]["properties"].get("DRAINAGE_AREA_GROSS"))
    if not prev.get("days") and HISTORY_LEFT[0] > 0:
        HISTORY_LEFT[0] -= 1
        try:
            prev = dict(prev, **wx.day_stats(http_json(api + "hydrometric-daily-mean/items?f=json&STATION_NUMBER=%s&limit=60000&skipGeometry=true&properties=DATE,LEVEL" % sid, {}, 60)["features"]))
        except Exception as e:
            print("history failed", sid, str(e)[:100])
    last = pts[-1]
    geo = (live[0].get("geometry") or {}).get("coordinates") or [None, None]
    series = [[p["DATETIME"], p["LEVEL"]] for p in pts[::-3][::-1]]  # counted back from the newest so the chart ends on the reading the tiles show
    day_ago = datetime.datetime.fromisoformat(last["DATETIME"].replace("Z", "+00:00")) - datetime.timedelta(days=1)
    then = next((p["LEVEL"] for p in pts if datetime.datetime.fromisoformat(p["DATETIME"].replace("Z", "+00:00")) >= day_ago), None)
    return {"name": sid, "title": re.sub(r" (At|Near|Above|Below) ", lambda m: m.group(0).lower(), last["STATION_NAME"].title()), "km": 0, "lat": geo[1], "lon": geo[0], "unit": "m", "flag": last.get("LEVEL_SYMBOL_EN"), "zone": eccc_zone(last, geo[0], geo[1]), "cm": last["LEVEL"], "time": last["DATETIME"], "then": then,
            "state": None, "marks": {}, "months": months, "months_at": prev.get("months_at") if months is prev.get("months") else now_iso(), "week": [p["LEVEL"] for p in pts[::36]], "series": series,
            "record": prev.get("record") or {}, "drainage": prev.get("drainage"), "days": prev.get("days"), "deciles": prev.get("deciles"), "day_years": prev.get("day_years"), "years": prev.get("years"), "peaks": prev.get("peaks"), "flow": [[p["DATETIME"], p["DISCHARGE"]] for p in [p for p in pts if p.get("DISCHARGE") is not None][::-6][::-1]],  # every 6th counted back from the newest, so "Latest" is the agency's latest (audit 2026-11-05: Ottawa showed 526 beside 517)
            "also": dict({"Q": [last["DISCHARGE"], "m³/s", "Flow"]} if last.get("DISCHARGE") is not None else {}, **({"DRAIN": [prev["drainage"], "km²", "Drainage area"]} if prev.get("drainage") else {}))}


EA = "https://environment.data.gov.uk/flood-monitoring/"
EA_RAIN_KM = 15  # ponytail: 1,044 EA rain stations across England (live 2026-11-03) sit about 11 km apart; past 15 km a gauge says little about rain on this reach. Wider for hill rivers if readers ask
EA_NEAR_M = 150  # ponytail: a gauge sits in the channel and warning areas cover the banks; areas named for the gauge's own place lay 9 to 88 m off (Colwick, Kingston, 2026-11-03). A wider channel needs more.


def ea_measures(st):
    """(level, flow, tidal) for an Environment Agency station: the main stage in metres above the stage datum and flow in m³/s, each the measure with the newest reading.
    A station with any tidal measure is tidal: a tide is never shown as a river level."""
    ms = st.get("measures") or []
    ms = ms if isinstance(ms, list) else [ms]
    if any(m.get("qualifier") == "Tidal Level" for m in ms):
        return None, None, True
    live = sorted((m for m in ms if isinstance(m.get("latestReading"), dict)), key=lambda m: m["latestReading"].get("dateTime") or "", reverse=True)
    pick = lambda p, q, u: next((m["notation"] for m in live if m.get("parameter") == p and (q is None or m.get("qualifier") == q) and m.get("unitName") == u), None)
    return pick("level", "Stage", "mASD"), pick("flow", None, "m3/s"), False


EA_HYD = "https://environment.data.gov.uk/hydrology/"


def ea_history(rloi, sid):
    """An English gauge's daily lowest and highest stage since it opened (Hydrology API, 2 CSV calls of about 4 MB). Shown only when the archive's 15-minute level equals
    our live stage on the archive's last day (4 times within 5 mm): another datum would make every past level wrong. {} when there is no match, no archive or under 10 years."""
    st = http_json(EA_HYD + "id/stations.json?RLOIid=%s" % urllib.parse.quote(rloi), {}, 30)["items"]
    ms = [m.get("@id", "") for m in (st[0].get("measures") or [])] if len(st) == 1 else []
    get = lambda end: next((m for m in ms if m.endswith(end)), None)
    lo, hi, inst = get("-level-min-86400-m-qualified"), get("-level-max-86400-m-qualified"), get("-level-i-900-m-qualified")
    if not (lo and hi and inst):
        return {}
    last = http_json(inst + "/readings.json?latest", {}, 30)["items"]
    day = last[0]["date"] if last else None
    arch = {i["dateTime"][:16]: i["value"] for i in http_json(inst + "/readings.json?date=%s&_limit=200" % day, {}, 30)["items"] if isinstance(i.get("value"), (int, float))} if day else {}
    live = {i["dateTime"][:16]: i["value"] for i in http_json(EA + "id/stations/%s/readings?date=%s&parameter=level&_limit=500" % (urllib.parse.quote(sid), day), {}, 30)["items"]
            if i.get("measure", "").endswith("-level-stage-i-15_min-mASD") and isinstance(i.get("value"), (int, float))} if day else {}
    both = [t for t in arch if t in live]
    if len(both) < 4 or any(abs(arch[t] - live[t]) > 0.005 for t in both):
        print("EA history datum not proven", rloi, day, len(both))
        return {}
    import csv, io
    rows = lambda m: list(csv.DictReader(io.StringIO(http_raw(m + "/readings.csv?_limit=200000", 120).decode("utf-8"))))
    return wx.ea_days(rows(lo), rows(hi), datetime.date.today().year)


def ea_name(st):
    s = lambda v: re.sub(r"\s+", " ", v).strip() if isinstance(v, str) else ""
    return ("%s at %s" % (s(st.get("riverName")), s(st.get("label")))) if s(st.get("riverName")) and s(st.get("label")) else s(st.get("label"))


def fetch_ea(sid, prev):
    """One English gauge, about one call an hour: readings since the last one we hold (6 h overlap, the agency sends in batches), all 8 days once a day so a late correction lands,
    and the station's measures and typical range once a week. The label is the agency's own typical range, as Check for flooding shows it. A tidal gauge is kept but never shown."""
    prev = prev or {}
    if prev.get("tidal"):
        return prev  # sticky: a gauge once seen with the tide stays out, and costs no call
    now = datetime.datetime.now(datetime.timezone.utc)
    meta = prev.get("ea")
    if not meta or due(prev.get("ea_at"), 168):
        st = http_json(EA + "id/stations/" + urllib.parse.quote(sid), {}, 30)["items"]
        lv, fl, tide = ea_measures(st)
        sc = st.get("stageScale") if isinstance(st.get("stageScale"), dict) else {}
        num = lambda v: v if isinstance(v, (int, float)) else None
        meta = {"title": ea_name(st), "lat": num(st.get("lat")), "lon": num(st.get("long")), "rloi": st.get("RLOIid") if isinstance(st.get("RLOIid"), str) else None, "level": lv, "flow": fl, "tidal": tide, "wt": "-temperature-water-" in json.dumps(st.get("measures")),
                "scale": {k: sc.get(k) for k in ("typicalRangeLow", "typicalRangeHigh", "maxOnRecord", "minOnRecord", "highestRecent")}}
        prev = dict(prev, ea=meta, ea_at=now_iso())
    if meta["tidal"]:
        return dict(prev, name=sid, tidal=True)
    if not meta["level"]:
        raise RuntimeError("no river stage in metres above the stage datum with a reading")
    full = not prev.get("series") or due(prev.get("full_at"), 24)
    since = (now - datetime.timedelta(days=8)) if full else datetime.datetime.fromisoformat(prev["series"][-1][0].replace("Z", "+00:00")) - datetime.timedelta(hours=6)
    got = http_json(EA + "id/stations/%s/readings?_sorted&_limit=10000&since=%s" % (urllib.parse.quote(sid), since.strftime("%Y-%m-%dT%H:%M:%SZ")), {}, 30)["items"]
    keep = lambda old, m, days: sorted((t, v) for t, v in dict(([] if full else [tuple(p) for p in old or []]) + [(i["dateTime"], i["value"]) for i in got if i.get("measure", "").endswith("/" + m) and isinstance(i.get("value"), (int, float))]).items()
                                       if datetime.datetime.fromisoformat(t.replace("Z", "+00:00")) >= now - datetime.timedelta(days=days))
    series = [list(p) for p in keep(prev.get("series"), meta["level"], 8)]
    if not series:
        raise RuntimeError("no level readings in 8 days")
    flow = [list(p) for p in keep(prev.get("flow"), meta["flow"], 7)] if meta["flow"] else []
    flow_bad = any(p[1] < 0 for p in flow)  # Kingston 2026-11-03: -66 to 58 m³/s in a week of 2 to 9; a river flow below zero is a fault or another quantity, so none is shown
    flow = [] if flow_bad else flow
    if len(series) >= 192 and wx.tidal(series):
        print("tidal, kept off the site:", sid)
        return dict(prev, name=sid, tidal=True)
    t, v = series[-1]
    day_ago = datetime.datetime.fromisoformat(t.replace("Z", "+00:00")) - datetime.timedelta(days=1)
    then = next((p[1] for p in series if datetime.datetime.fromisoformat(p[0].replace("Z", "+00:00")) >= day_ago), None)
    sc = meta["scale"]
    lo, hi = sc.get("typicalRangeLow"), sc.get("typicalRangeHigh")
    ok = isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and lo < hi
    rec = lambda k: sc[k] if isinstance(sc.get(k), dict) and isinstance(sc[k].get("value"), (int, float)) and sc[k].get("dateTime") else None  # a record with no date is not shown
    marks, dates = dict({"TRL": lo, "TRH": hi} if ok else {}), {}
    for k, m in (("maxOnRecord", "HHW"), ("minOnRecord", "NNW"), ("highestRecent", "HREC")):
        if rec(k):
            marks[m], dates[m] = rec(k)["value"], rec(k)["dateTime"][:10]
    hist = {k: prev[k] for k in ("days", "years", "day_years", "hist_at") if prev.get(k)}
    if meta.get("rloi") and due(prev.get("hist_at"), 2160) and HISTORY_LEFT[0] > 0:  # every 90 days: past years change only when the archive adds a month
        HISTORY_LEFT[0] -= 1
        try:
            hist = dict(ea_history(meta["rloi"], sid), hist_at=now_iso())
        except Exception as e:
            print("EA history failed", sid, str(e)[:100])
            hist["hist_at"] = iso(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2160 - 168))  # retry in 7 days, not every run: a dead archive must not eat the shared history slots
    return {"name": sid, "title": meta["title"], "km": 0, "lat": meta["lat"], "lon": meta["lon"], "unit": "m", "zone": "Europe/London", "rloi": meta["rloi"], **hist, "cm": v, "time": t, "then": then,
            "state": ("low" if v < lo else "high" if v > hi else "normal") if ok else None, "range": [lo, hi] if ok else None, "marks": marks, "mark_dates": dates, "series": series, "week": [p[1] for p in series[::96]], "flow": flow, "flow_bad": flow_bad,
            "also": {"Q": [flow[-1][1], "m³/s", "Flow", flow[-1][0]]} if flow and flow[-1][0] == t else {},  # the also table prints the level's time: a flow of another time stays in the flow chart only
            "ea": meta, "ea_at": prev.get("ea_at") or now_iso(), "full_at": now_iso() if full else prev.get("full_at")}


def ea_alert_list():
    """Every Environment Agency flood warning and alert in force, with its area shape: one call, plus one per area newly in force. Shapes of areas still in force are kept
    in cache/_ea-areas.json across runs; an area that leaves force drops out, so the file holds at most what is in force now. None (Unknown) when any part fails."""
    floods = wx.ea_floods(http_json(EA + "id/floods", {}, 60))
    if floods is None:
        raise RuntimeError("flood warning list cut short")
    p = os.path.join(CACHE, "_ea-areas.json")
    try:
        old = json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        old = {}
    rings = {}
    for f in floods:
        code = f["floodAreaID"]
        if code not in rings:
            rings[code] = old.get(code) or wx.ea_rings(http_json(EA + "id/floodAreas/%s/polygon" % urllib.parse.quote(code), {}, 60))
    json.dump(rings, open(p + ".tmp", "w", encoding="utf-8"), separators=(",", ":"))
    os.replace(p + ".tmp", p)
    return wx.ea_alerts(floods, rings)


def wx_england(r, w, ctx):
    """Flood warnings by point test against each area in force, rain from the nearest EA rain gauge, and the Met Office forecast at the gauge."""
    al = once(ctx, "ea-alerts", ea_alert_list)
    if al is not None:
        w["alerts"], w["fetched_at"] = wx.alerts_at(r["lat"], r["lon"], al, EA_NEAR_M), now_iso()
    try:
        met(r, w)
    except Exception as e:
        note("met-office", "failed", e)
    w["no_weather"] = None if w.get("hourly") or w.get("periods") else "no Met Office forecast collected yet"
    ea_rain(r, w, ctx)


MET = "https://data.hub.api.metoffice.gov.uk/sitespecific/v0/point/"
MET_DAY = 300  # calls a day; the free plan stops at 360 (FAQ read 2026-11-03), 60 spare


def met(r, w):
    """Met Office Global Spot, hourly and daily: 2 calls a gauge. Each gauge waits max(3 h, 24 h x 2 x gauges / MET_DAY) between calls, so the day's calls fit the plan
    at any count: hourly turns amber past 75 English gauges (12 h), the daily cards hide past 300 (48 h), the hourly past 450 (72 h). The ledger counts a call before it is made."""
    key = os.environ.get("METOFFICE_SITE_KEY")
    if not key:
        return
    p = os.path.join(CACHE, "_ea-met.json")  # the _ea- prefix: a collect shard carries it back (sharded.yml)
    try:
        led = json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        led = {}
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    if led.get("day") != day:  # the plan resets at 00:00 UTC; a gauge unseen for a week leaves the count
        led = {"day": day, "n": 0, "last": {k: v for k, v in (led.get("last") or {}).items() if v and not due(v, 168)}}
    last = led["last"]
    last.setdefault(r["name"], None)
    if not due(last[r["name"]], max(3, 24 * 2 * len(last) / MET_DAY)) or led["n"] + 2 > MET_DAY:
        json.dump(led, open(p, "w", encoding="utf-8"))
        return
    led["n"] += 2
    last[r["name"]] = now_iso()
    json.dump(led, open(p, "w", encoding="utf-8"))
    q = "?latitude=%.4f&longitude=%.4f&includeLocationName=true" % (r["lat"], r["lon"])
    hd = {"apikey": key, "accept": "application/json", "User-Agent": "riverwaterlevels.com"}
    hourly, daily = http_json(MET + "hourly" + q, hd, 30), http_json(MET + "daily" + q, hd, 30)
    got = wx.met_forecast(hourly, daily, zoneinfo.ZoneInfo("Europe/London"))
    keys = lambda j: sorted(((((j or {}).get("features") or [{}])[0].get("properties") or {}).get("timeSeries") or [{}])[0])
    print("met", r["name"], "hourly", len(got.get("hourly") or []), "periods", len(got.get("periods") or []), "hourly fields", keys(hourly), "daily fields", keys(daily))  # the live proof of the field names
    w.update(got)


def ea_rain_store():
    """Every EA rainfall reading of the last 26 h, kept in cache/_ea-rain.json: one bulk call a run (the newest 10,000 readings of all rain gauges, about 2.7 h, 3.5 MB,
    3 to 45 s measured 2026-11-03), never one call per station (the API reference asks for bulk calls). Runs up to 2.7 h apart leave no hole; a longer gap leaves one,
    and ea_rain fills it for the stations pages use, RAIN_FILL a run. The file stays near 3 MB whatever the page count."""
    p = os.path.join(CACHE, "_ea-rain.json")
    try:
        old = json.load(open(p, encoding="utf-8")).get("r") or {}
    except (OSError, ValueError, AttributeError):
        old = {}
    got = http_json(EA + "data/readings?parameter=rainfall&_sorted&_limit=10000", {}, 120)["items"]
    if len(got) < 5000:
        raise RuntimeError("rain readings cut short (%d)" % len(got))
    cut = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=26)).strftime("%Y-%m-%dT%H:%M:%SZ")
    keep = {m: {t: v for t, v in s.items() if t >= cut} for m, s in old.items()}
    for i in got:
        if isinstance(i.get("dateTime"), str) and i["dateTime"] >= cut:
            keep.setdefault(i["measure"].rsplit("/", 1)[-1], {})[i["dateTime"]] = i.get("value") if isinstance(i.get("value"), (int, float)) else None
    keep = {m: s for m, s in keep.items() if s}
    ea_rain_save(keep)
    return keep


def ea_rain_save(keep):
    p = os.path.join(CACHE, "_ea-rain.json")
    json.dump({"at": now_iso(), "r": keep}, open(p + ".tmp", "w", encoding="utf-8"), separators=(",", ":"))
    os.replace(p + ".tmp", p)


RAIN_FILL = [20]  # ponytail: per-station calls a run to fill a hole (first run, a missed run) for a station a page uses; at about 700 stations for 2,421 English gauges a full refill takes 35 h


def ea_rain(r, w, ctx):
    """w["ea_rain"]: the 24 h total of the nearest EA rain gauge within EA_RAIN_KM that has every reading, with its station, distance and end time;
    else the nearest one's reason. A failed list or store keeps the last answer, which ages into Unknown on the page."""
    store = once(ctx, "ea-rain", ea_rain_store)
    st = listing("ea-rain-stations", EA + "id/stations?parameter=rainfall&_limit=10000", wx.ea_rain_stations) if store is not None else None
    if not st:
        return
    near = sorted((wx.km(r["lat"], r["lon"], s[0], s[1]), k) for k, s in st.items() if abs(s[0] - r["lat"]) < 0.3)
    near = [(d, k) for d, k in near if d <= EA_RAIN_KM]
    if not near:
        w["ea_rain"] = {"why": "No Environment Agency rain gauge within %d km" % EA_RAIN_KM}
        return
    first = None
    for d, k in near:
        name = k if st[k][2] in ("", "Rainfall station") else "%s (%s)" % (st[k][2], k)
        for m, per in st[k][3]:
            mm, end = wx.rain_total(store.get(m) or {}, per)
            if mm is None and first is None and RAIN_FILL[0] > 0:  # the nearest station only: a hole in our store, not the agency's, is filled from its own readings
                RAIN_FILL[0] -= 1
                try:
                    since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=26)).strftime("%Y-%m-%dT%H:%M:%SZ")
                    for i in http_json(EA + "id/measures/%s/readings?_sorted&_limit=200&since=%s" % (urllib.parse.quote(m), since), {}, 30)["items"]:
                        store.setdefault(m, {})[i["dateTime"]] = i.get("value") if isinstance(i.get("value"), (int, float)) else None
                    ctx["ea-rain-filled"] = True
                    mm, end = wx.rain_total(store.get(m) or {}, per)
                except Exception as e:
                    note("world-wx", "failed", e)
            if mm is not None:
                w["ea_rain"] = {"station": name, "km": round(d, 1), "mm": mm, "to": end}
                return
            first = first or {"station": name, "km": round(d, 1), "mm": None, "why": end}
    w["ea_rain"] = first


def ea_probe(ctx, areas=20):
    """England's alert proof, found by the run itself: the first warning in force whose area holds an English level station, by the same test the pages use.
    Recorded once in cache/_ea-proof.json (build.py publishes it as /_proofs.json; read back from there when the cache is lost), then never asked again.
    Costs the warning list call wx_england already makes, plus one station call per area in force until a proof is found, at most `areas` a run."""
    p = os.path.join(CACHE, "_ea-proof.json")
    if not os.path.exists(p):
        try:
            got = json.loads(http_raw("https://riverwaterlevels.com/_proofs.json", 30))
            if isinstance(got, dict):
                json.dump(got, open(p, "w", encoding="utf-8"), ensure_ascii=False)
        except Exception:  # a 404 is the normal state before any proof; the probe below looks again
            pass
    try:
        if (json.load(open(p, encoding="utf-8")).get("ea") or {}).get("alerts"):
            return
    except (OSError, ValueError):
        pass
    al = once(ctx, "ea-alerts", ea_alert_list)  # None (cut short, a shape missing, a failure) and [] prove nothing
    for a in (al or [])[:areas]:  # wx.ea_floods dropped level 4; wx.ea_proof checks the level again
        b = [min(x[0] for x in a["boxes"]), max(x[1] for x in a["boxes"]), min(x[2] for x in a["boxes"]), max(x[3] for x in a["boxes"])]
        lat, lon = (b[0] + b[1]) / 2, (b[2] + b[3]) / 2
        reach = wx.km(lat, lon, b[1], b[3]) + 1  # every station the area can hold, and the 150 m beside it
        try:
            hit = wx.ea_proof([a], http_json(EA + "id/stations?parameter=level&lat=%.5f&long=%.5f&dist=%.1f" % (lat, lon, reach), {}, 60)["items"], EA_NEAR_M)
        except Exception as e:
            note("world-wx", "failed", e)
            continue
        if hit:
            w, s = hit
            at = now_iso()
            rec = {"ea": {"alerts": "Environment Agency %s (level %s) for %s, area %s, held station %s %s by the point test plus %d m, seen %s" % (w["event"], w["level"], w["areaDesc"], w["id"], s["notation"], s.get("label") or "", EA_NEAR_M, at[:16]),
                          "warning": w["id"], "area": w["areaDesc"], "level": w["level"], "station": s["notation"], "at": at}}
            json.dump(rec, open(p + ".tmp", "w", encoding="utf-8"), ensure_ascii=False)
            os.replace(p + ".tmp", p)
            print("England alert proof recorded:", rec["ea"]["alerts"])
            return


def side_readings(series):
    """A station's other readings, each with its own time, gone after 24 h."""
    now = datetime.datetime.now(datetime.timezone.utc)
    return {t["shortname"]: [t["currentMeasurement"]["value"], t.get("unit"), t["longname"].title(), t["currentMeasurement"]["timestamp"]] for t in series
            if t["shortname"] != "W" and t.get("currentMeasurement") and (now - datetime.datetime.fromisoformat(t["currentMeasurement"]["timestamp"])).total_seconds() < 86400}


def usgs_low():
    """The key is shared with the Worker's live poll: under 300 calls left this hour, this run leaves history alone. The site reports the budget; no answer means no pause."""
    try:
        rem = urllib.request.urlopen(urllib.request.Request("https://riverwaterlevels.com/live/00000000.json", headers={"User-Agent": "riverwaterlevels.com"}), timeout=20).headers.get("x-rwl-usgs-remaining")
        return rem is not None and float(rem) < 300
    except (OSError, ValueError):
        return False


def fresh_raw(url, hours, timeout=45):
    """The file, or an error when its Last-Modified is older than the block's limit: a stuck feed must read Unknown, not none."""
    r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "riverwaterlevels.com"}), timeout=timeout)
    age = datetime.datetime.now(datetime.timezone.utc) - email.utils.parsedate_to_datetime(r.headers["Last-Modified"])
    if age.total_seconds() > hours * 3600:
        raise RuntimeError("feed file %d h old" % (age.total_seconds() / 3600))
    return r.read()


def http_raw(url, timeout=45):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "riverwaterlevels.com"}), timeout=timeout).read()


def listing(name, url, parse, hours=168):
    """A slow-changing station list, kept in cache/ a week: one call, never one per gauge, and a failure is tried once a run."""
    if name in LISTED:
        return LISTED[name]
    LISTED[name] = _listing(name, url, parse, hours)
    return LISTED[name]


LISTED = {}
HISTORY_LEFT = [3]  # gauges a run may pull full daily history for: a Canadian gauge's past is 1.4 MB and 9 s, once ever, so 2,627 gauges take 37 days


def _listing(name, url, parse, hours):
    p = os.path.join(CACHE, "_%s.json" % name)
    try:
        d = json.load(open(p, encoding="utf-8"))
        if not due(d["at"], hours):
            return d["spots"]
    except (OSError, ValueError, KeyError):
        d = None
    try:
        spots = parse(http_raw(url))
        json.dump({"at": now_iso(), "spots": spots}, open(p + ".tmp", "w", encoding="utf-8"), separators=(",", ":"))
        os.replace(p + ".tmp", p)
        return spots
    except Exception as e:
        note("world-wx", "failed", e)
        print("world-wx failed", name, str(e)[:120])
        return d["spots"] if d else {}


def once(ctx, key, get):
    """One fetch per run per city, station or country, whatever the gauge count. A failure is remembered as None for this run and leaves the row's last answer and its old time."""
    if key not in ctx:
        try:
            ctx[key] = get()
            note("world-wx", "ok")  # without it one 410 a run read as "never worked" (watchdog 2026-11-07) while air quality was live
        except Exception as e:
            note("world-wx", "failed", e)
            print("world-wx failed", key, str(e)[:120])
            ctx[key] = None
    return ctx[key]


def wx_canada(r, w, ctx):
    api = "https://api.weather.gc.ca/collections/"
    al = once(ctx, "ca-alerts", lambda: wx.canada_alerts(http_json(api + "weather-alerts/items?f=json&lang=en&limit=5000", {}, 90)))
    if al is not None:
        w["alerts"], w["fetched_at"] = wx.alerts_at(r["lat"], r["lon"], al), now_iso()
    cities = listing("ca-cities", api + "citypageweather-realtime/items?f=json&limit=2000&properties=identifier", lambda b: {f["id"]: f["geometry"]["coordinates"][1::-1] for f in json.loads(b)["features"]})
    cid = wx.nearest(r["lat"], r["lon"], cities)[0]
    w["no_weather"] = None if cid else "no weather city within %d km" % wx.NEAR_KM
    if cid:
        got = once(ctx, "city-" + cid, lambda: http_json(api + "citypageweather-realtime/items/%s?f=json&lang=en" % cid, {}, 30)["properties"])
        if got:
            w.update(wx.canada_city(got, r["lat"], r["lon"]), city_url=wx.en(got.get("url")))
    aq = once(ctx, "ca-aq", lambda: {f["id"]: f["geometry"]["coordinates"][1::-1] + [f["properties"]["location_name_en"], f["properties"]["aqhi"], f["properties"]["observation_datetime"]] for f in http_json(api + "aqhi-observations-realtime/items?f=json&latest=true&limit=500", {}, 45)["features"]})
    if aq:
        i, d = wx.nearest(r["lat"], r["lon"], aq)
        w["aq"] = {"value": "%.1f on 1 to 10+" % aq[i][3], "scale": "Air Quality Health Index, 1 to 10+", "place": aq[i][2], "km": d, "t": aq[i][4], "src": "Environment and Climate Change Canada"} if i else None


def wx_germany(r, w, ctx):
    b = "https://opendata.dwd.de/weather/"
    cat = listing("de-stations", "https://www.dwd.de/DE/leistungen/met_verfahren_mosmix/mosmix_stationskatalog.cfg?view=nasPublication&nn=16102", lambda t: wx.dwd_stations(t.decode("latin1")))
    near = wx.nearest(r["lat"], r["lon"], cat, 40)[0]
    w["abroad"] = not (near and wx.german(near))
    if near and wx.german(near):  # DWD warns for Germany only: a gauge past its border gets no answer, never a false none
        al = once(ctx, "de-alerts", lambda: wx.dwd_alerts(fresh_raw(b + "alerts/cap/DISTRICT_DWD_STAT/Z_CAP_C_EDZW_LATEST_PVW_STATUS_PREMIUMDWD_DISTRICT_EN.zip", 3)))
        if al is not None:
            w["alerts"], w["fetched_at"] = wx.alerts_at(r["lat"], r["lon"], al), now_iso()
    beob = listing("de-beob", b + "weather_reports/poi/", lambda t: re.findall(r'href="([^"]+)-BEOB\.csv"', t.decode("latin1")))
    obs = wx.nearest(r["lat"], r["lon"], {k: v for k, v in cat.items() if k.ljust(5, "_") in beob or k in beob})[0]
    w["no_weather"] = None if near else "no forecast point within 40 km"
    if near:
        got = once(ctx, "fc-" + near, lambda: wx.dwd_forecast(http_raw(b + "local_forecasts/mos/MOSMIX_L/single_stations/%s/kml/MOSMIX_L_LATEST_%s.kmz" % (near, near)), zoneinfo.ZoneInfo("Europe/Berlin")))
        w.update(got or {})
    if obs:
        got = once(ctx, "obs-" + obs, lambda: wx.dwd_obs(http_raw(b + "weather_reports/poi/%s-BEOB.csv" % obs.ljust(5, "_")).decode("utf-8", "ignore"), obs, cat[obs]))
        w.update(got or {})
    day, back = datetime.date.today().isoformat(), (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    aqs = listing("de-aq", "https://www.umweltbundesamt.de/api/air_data/v3/meta/json?lang=en&use=airquality&date_from=%s&time_from=1&date_to=%s&time_to=1" % (back, back), lambda t: {k: [float(v[8]), float(v[7]), v[2]] for k, v in json.loads(t)["stations"].items() if v[6] is None and v[7]})
    i, d = wx.nearest(r["lat"], r["lon"], aqs, 30)
    if i:
        got = once(ctx, "aq-" + i, lambda: http_json("https://www.umweltbundesamt.de/api/air_data/v3/airquality/json?station=%s&date_from=%s&time_from=1&date_to=%s&time_to=24&lang=en" % (i, back, day), {}, 30)["data"].get(i))
        if got and any(v[1] is not None for v in got.values()):
            t = max(k for k, v in got.items() if v[1] is not None)
            w["aq"] = {"value": "%d, on the agency's scale from 0 (very good) to 4 (very bad)" % got[t][1], "scale": "German air quality index, 0 very good to 4 very bad", "place": aqs[i][2], "km": d, "t": t.replace(" ", "T") + "+01:00", "src": "Umweltbundesamt with data from the networks of the states and the federal government"}  # "0 of 0 to 4" was unreadable (UI review 2026-11-04)


def wx_fill(page, rows, old, ctx):
    """Every gauge page's weather, alerts and air quality on its row, cached across runs: a dead source leaves the last answer and its real age, and the block goes Unknown or hides by the US limits."""
    for r in rows:
        if r["name"] not in (page.get("gauge_pages") or []) or r.get("lat") is None or r.get("tidal"):
            continue
        w = dict((old.get(r["name"]) or {}).get("wx") or {})
        try:
            {"eccc": wx_canada, "ea": wx_england}.get(page.get("feed"), wx_germany)(r, w, ctx)
        except Exception as e:
            note("world-wx", "failed", e)
        r["wx"] = w
        world_extras(page, r, old.get(r["name"]) or {}, ctx)


ACCESS_LEFT = [5]  # Overpass gauges a run: public server, 2,627 Canadian gauges take a week the first time, then monthly


def world_extras(page, r, prev, ctx):
    """Blocks on slow clocks, each kept from the last run: access and normals monthly, drought with the monthly map, 30 days of water temperature daily. A failure keeps the old answer and the block says its age."""
    canada = page.get("feed") == "eccc"
    for k in ("access", "access_at", "normals", "normals_at", "drought", "drought_map", "drought_v", "wt30", "wt30_at"):
        if k in prev:
            r[k] = prev[k]
    if due(r.get("access_at"), 720) and ACCESS_LEFT[0] > 0:
        ACCESS_LEFT[0] -= 1
        try:
            r["access"], r["access_at"] = fetch_access(r["lat"], r["lon"]), now_iso()
            note("world-access", "ok")
        except Exception as e:
            note("world-access", "failed", e)
    if page.get("feed") == "ea":
        pass  # England: climate normals are a next item in lib/world.py COVER (Met Office), never a German station
    elif due(r.get("normals_at"), 720) or (canada and (r.get("normals") or {}).get("v") != 2):
        try:
            r["normals"], r["normals_at"] = (normals_canada if canada else normals_germany)(r), now_iso()
            note("world-normals", "ok")
        except Exception as e:
            note("world-normals", "failed", e)
    if canada:
        try:
            m = listing("ca-drought2", CDM + "%d/" % datetime.date.today().year, drought_latest, 72)
            if m and (m["map"] != r.get("drought_map") or r.get("drought_v") != 2):
                r["drought"], r["drought_map"], r["drought_v"] = wx.drought_at(r["lat"], r["lon"], m["polys"]), m["map"], 2
        except Exception as e:
            note("world-drought", "failed", e)
    elif "WT" in (r.get("also") or {}) and due(r.get("wt30_at"), 20):
        try:
            pts = http_json("https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations/%s/WT/measurements.json?start=P30D" % urllib.parse.quote(r["name"]), {}, 30)
            r["wt30"], r["wt30_at"] = {"low": min(p["value"] for p in pts), "high": max(p["value"] for p in pts), "first": pts[0]["timestamp"], "last": pts[-1]["timestamp"]} if pts else None, now_iso()
        except Exception as e:
            note("world-wtemp", "failed", e)


CDM = "https://agriculture.canada.ca/atlas/data_donnees/canadianDroughtMonitor/data_donnees/geoJSON/areasofDrought/"


def drought_latest(index):
    """The newest monthly map in this year's folder, or last year's in January."""
    names = re.findall(r'href="(cdm_(\d{4})_[^"]*\.zip)"', index.decode("utf-8", "ignore"))
    folder = CDM + "%d/" % datetime.date.today().year
    if not names:
        folder = CDM + "%d/" % (datetime.date.today().year - 1)
        names = re.findall(r'href="(cdm_(\d{4})_[^"]*\.zip)"', http_raw(folder).decode("utf-8", "ignore"))
    name, stamp = max(names, key=lambda n: n[1])
    return {"map": stamp, "polys": wx.drought_map(http_raw(folder + name, 120))}


def normals_canada(r):
    """The nearest station within about 50 km with a current normal for temperature and rain; one call a gauge a month."""
    api = "https://api.weather.gc.ca/collections/climate-normals/items?f=json&limit=2000&CURRENT_FLAG=Y&bbox=%.3f,%.3f,%.3f,%.3f&NORMAL_ID=%%d&properties=CLIMATE_IDENTIFIER,STATION_NAME,MONTH,VALUE,PERIOD_BEGIN,PERIOD_END,YEAR_COUNT_NORMAL_PERIOD" % (r["lon"] - .7, r["lat"] - .5, r["lon"] + .7, r["lat"] + .5)
    temp, rain = http_json(api % 1, {}, 30)["features"], http_json(api % 56, {}, 30)["features"]
    full = lambda fs: {i for i, n in collections.Counter(f["properties"]["CLIMATE_IDENTIFIER"] for f in fs if f["properties"]["MONTH"] <= 12 and f["properties"]["VALUE"] is not None and (f["properties"]["YEAR_COUNT_NORMAL_PERIOD"] or 0) >= 15).items() if n == 12}  # Seymour Falls: one October, one year, shown as a normal
    both = full(temp) & full(rain)
    spots = {f["properties"]["CLIMATE_IDENTIFIER"]: [f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0]] for f in temp if f["properties"]["CLIMATE_IDENTIFIER"] in both}
    sid, away = wx.nearest(r["lat"], r["lon"], spots, 50)
    if not sid:
        return None
    pick = lambda fs: {str(f["properties"]["MONTH"]): f["properties"]["VALUE"] for f in fs if f["properties"]["CLIMATE_IDENTIFIER"] == sid and f["properties"]["MONTH"] <= 12}
    p = next(f["properties"] for f in temp if f["properties"]["CLIMATE_IDENTIFIER"] == sid)
    t, m = pick(temp), pick(rain)
    return {"v": 2, "place": p["STATION_NAME"].title(), "km": away, "period": "%s to %s" % (p["PERIOD_BEGIN"], p["PERIOD_END"]), "temp": t, "rain": m}


def normals_table(blob):
    """A DWD 1991-2020 multi-annual file: {station: [Jan..Dec]}; -999 or blank is None."""
    out = {}
    for line in blob.decode("latin1").splitlines()[1:]:
        c = [x.strip() for x in line.split(";")]
        if len(c) > 15:
            out[c[0]] = [None if x in ("", "-999", "-999.0") else float(x) for x in c[3:15]]
    return out


def normals_germany(r):
    b = "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/multi_annual/mean_91-20/"
    rain, temp = listing("de-rain-normal", b + "Niederschlag_1991-2020.txt", normals_table, 8760), listing("de-temp-normal", b + "Temperatur_1991-2020.txt", normals_table, 8760)
    st = listing("de-normal-stations", b + "Temperatur_1991-2020_Stationsliste.txt", lambda t: {c[0].strip(): [float(c[2]), float(c[3]), c[1].strip()] for c in (l.split(";") for l in t.decode("latin1").splitlines()[1:]) if len(c) > 3}, 8760)
    sid, away = wx.nearest(r["lat"], r["lon"], {k: v for k, v in st.items() if k in rain and k in temp}, 50)
    if not sid:
        return None
    months = lambda v: {str(i + 1): x for i, x in enumerate(v) if x is not None}
    return {"place": st[sid][2], "km": away, "period": "1991 to 2020", "temp": months(temp[sid]), "rain": months(rain[sid])}


def archive(page, rows):
    """Each river's daily low and high by year, kept by us because the agencies keep 30 days. Published beside the pages and read back when the cache is gone, so a lost cache loses no history.
    ponytail: one file per river per year, about 25 bytes a gauge a day; a flat hub near 2,500 gauges nears Cloudflare's 25 MB a file, split it by province then."""
    year = datetime.date.today().year
    for y in range(2026, year):
        old = os.path.join(CACHE, "_archive-%s-%d.json" % (page["slug"], y))
        if not os.path.exists(old):  # a lost cache must not drop past years from the next deploy
            try:
                open(old, "wb").write(http_raw("https://riverwaterlevels.com/archive/" + os.path.basename(old)[1:], 30))
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    open(old, "w").write("{}")
            except Exception as e:
                print("archive failed", old, str(e)[:120])
    name = "archive-%s-%d.json" % (page["slug"], year)
    p = os.path.join(CACHE, "_" + name)
    try:
        a = json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        try:
            a = json.loads(http_raw("https://riverwaterlevels.com/archive/" + name, 30))
        except urllib.error.HTTPError as e:
            if e.code != 404:
                return print("archive failed", name, e)
            a = {}  # the first day of this file
        except Exception as e:
            return print("archive failed", name, str(e)[:120])
    for r in rows:
        if r.get("cm") is not None and r.get("time") and not r.get("tidal"):
            wx.day_add(a, r["name"], r["time"][:10], r["cm"])
    json.dump(a, open(p + ".tmp", "w", encoding="utf-8"), separators=(",", ":"))
    os.replace(p + ".tmp", p)


def fetch_census():
    """Once a day: every active USGS site with a flow or a level, and every NOAA tide station, counted as built or not buildable by our code
    (lib/census.py). About 100 USGS calls and 1 NOAA call a day, whatever our page count. A state that fails is named in "unknown", never counted as zero."""
    import csv
    from lib import census
    path = os.path.join(CACHE, "_census.json")
    prev = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    if not daily_due(prev.get("fetched_at")):
        return
    # USGS Water Data API (waterservices.usgs.gov retires Q1 2027): every site with a reading in the last 30 days, nationally, in about 3 calls
    # (2026-11-06: 8,918 flow sites, 11,603 with a level), then the site type of the level-only ones, 300 ids a call (about 10 calls)
    h, unknown = usgs_headers(), []
    def ids(pc):
        url, got, pages = BASE + "latest-continuous/items?parameter_code=%s&time=P30D&skipGeometry=true&properties=monitoring_location_id&limit=10000&f=json" % pc, set(), 0
        while url and pages < 10:
            d = http_json(url, h, 180)
            pages += 1
            got |= {str(f["properties"]["monitoring_location_id"])[5:] for f in d.get("features", [])}
            url = next((l.get("href") for l in d.get("links", []) if l.get("rel") == "next"), None)
        if url:
            raise RuntimeError("census page cap reached")
        return got
    try:
        flow = ids("00060")
        lv = ids("00065,62614,62615,72020,00062,72279")
        only = sorted(lv - flow)
        level = {s: "" for s in lv & flow}
        for i in range(0, len(only), 300):
            for f in http_json(BASE + "monitoring-locations/items?id=%s&properties=monitoring_location_number,site_type_code&skipGeometry=true&limit=500&f=json" % ",".join("USGS-" + s for s in only[i:i + 300]), h, 120).get("features", []):
                level[f["properties"]["monitoring_location_number"]] = f["properties"].get("site_type_code") or ""
        level.update({s: "" for s in only if s not in level})  # a site the location call did not return counts as level-only, never as zero
    except Exception as e:  # the whole national count is Unknown, never a partial number read as the truth
        print("census FAILED", str(e)[:100])
        return
    built = {r["site"] for r in csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8")) if r["status"] == "live"}
    out = {"fetched_at": now_iso(), "usgs": dict(census.classify(flow, level, built), unknown=unknown)}
    try:
        n = len(json.loads(http_raw("https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json?type=waterlevels", 60))["stations"])
        nb = len(built & COASTS)  # coast pages since 2026-11-06
        out["noaa_tides"] = {"tidal": n, "built": nb, "code_cannot": n - nb}
    except Exception as e:
        out["noaa_tides"] = {"unknown": str(e)[:80]}
    json.dump(out, open(path + ".tmp", "w", encoding="utf-8"))
    os.replace(path + ".tmp", path)
    print("census", json.dumps(out)[:300])


def fetch_world():
    """cache/_river-<slug>.json for the pages in data/world-pages.json: PEGELONLINE (WSV), no key. Shard 0 only. A gauge that fails keeps its last row;
    three failures in a row stop asking, so a dead feed stales only these pages and never holds the shard for minutes."""
    base, miss, ctx = "https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations/", {}, {}  # failures in a row per feed: a dead PEGELONLINE once skipped Canada and England too (review 2026-11-04)
    if os.path.exists(os.path.join(CACHE, "_rhine.json")) and not os.path.exists(os.path.join(CACHE, "_river-rhine.json")):
        os.replace(os.path.join(CACHE, "_rhine.json"), os.path.join(CACHE, "_river-rhine.json"))
    pages = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "world-pages.json"), encoding="utf-8"))
    for page in pages:
        path = os.path.join(CACHE, "_river-%s.json" % page["slug"])
        try:
            old = {r["name"]: r for r in json.load(open(path, encoding="utf-8"))["rows"]}
        except (OSError, ValueError, KeyError):
            old = {}
        rows = []
        for name in page["stations"]:
            q = urllib.parse.quote(name)
            try:
                feed = page.get("feed", "pegelonline")
                if miss.get(feed, 0) >= 3:
                    raise RuntimeError("feed down this run")
                if page.get("feed") in ("eccc", "ea"):
                    rows.append((fetch_eccc if page["feed"] == "eccc" else fetch_ea)(name, old.get(name)))
                    miss[feed] = 0
                    note(page["feed"], "ok")
                    continue
                st = retry_json(base + q + ".json?includeTimeseries=true&includeCurrentMeasurement=true&includeCharacteristicValues=true", {}, 30)
                w = next(t for t in st["timeseries"] if t["shortname"] == "W")
                cur, marks = w["currentMeasurement"], {c["shortname"]: c["value"] for c in w.get("characteristicValues") or []}
                past = retry_json(base + q + "/W/measurements.json?start=P8D", {}, 30)
                day_ago = datetime.datetime.fromisoformat(cur["timestamp"]) - datetime.timedelta(days=1)
                then = next((p["value"] for p in past if datetime.datetime.fromisoformat(p["timestamp"]) >= day_ago), None)
                past = past[-672:]  # the table's line stays 7 days
                flow = []
                if name in (page.get("gauge_pages") or []) and any(t["shortname"] == "Q" for t in st["timeseries"]):
                    flow = [[p["timestamp"], p["value"]] for p in retry_json(base + q + "/Q/measurements.json?start=P7D", {}, 30)[::-8][::-1]]  # counted back from the newest: the chart's "Latest" is the agency's latest (dry run 2026-11-05: Frankfurt 92 beside 60)
                try:
                    fc = retry_json(base + q + "/WV/measurements.json", {}, 30) if name in (page.get("gauge_pages") or []) else []
                except urllib.error.HTTPError:
                    fc = []  # the Federal Institute of Hydrology forecasts a few gauges; the rest answer 404
                rows.append({"name": name, "uuid": st["uuid"], "number": st.get("number"), "flow": flow, "ship": cur.get("stateNswHsw"), "fc": {"at": fc[0]["initialized"], "pts": [[p["timestamp"], p["value"], p["type"]] for p in fc]} if fc else None, "km": st["km"], "lat": st.get("latitude"), "lon": st.get("longitude"), "cm": cur["value"], "time": cur["timestamp"], "state": cur.get("stateMnwMhw"), "then": then,
                             "glw": marks.get("GlW"), "nnw": marks.get("NNW"), "mw": marks.get("MW"), "week": [p["value"] for p in past[::8]], "marks": marks, "also": side_readings(st["timeseries"]), **({"series": [[p["timestamp"], p["value"]] for p in past]} if name in (page.get("gauge_pages") or []) else {})})
            except Exception as e:
                miss[feed] = miss.get(feed, 0) + 1
                note(page.get("feed", "pegelonline"), "failed", e)
                if name in old:
                    rows.append(old[name])
            else:
                miss[feed] = 0
                note("pegelonline", "ok")
        if rows:
            wx_fill(page, rows, old, ctx)
            archive(page, rows)
            json.dump({"fetched_at": now_iso(), "rows": rows}, open(path + ".tmp", "w", encoding="utf-8"), separators=(",", ":"))
            os.replace(path + ".tmp", path)
    if ctx.get("ea-rain-filled") and ctx.get("ea-rain"):
        ea_rain_save(ctx["ea-rain"])
    if any(p.get("feed") == "ea" for p in pages):
        try:
            ea_probe(ctx)
        except Exception as e:  # the proof waits for the next run; nothing on a page depends on it
            note("world-wx", "failed", e)


def fetch_twdb_state():
    """Every Texas reservoir TWDB tracks, one 73 KB file (122 reservoirs, 2026-11-06) for the /lakes/tx/ hub ('texas lake levels' 10K-100K a month).
    TWDB updates daily: fetched at most every 6 h (4 calls a day). A bad answer keeps the last good file; the page prints each reservoir's own date."""
    p = os.path.join(CACHE, "twdb-texas.json")
    try:  # age from the file's own fetched_at: a cache restore can reset mtimes and freeze the data forever
        if (datetime.datetime.now(datetime.timezone.utc) - parse_t(json.load(open(p, encoding="utf-8"))["fetched_at"])).total_seconds() < 6 * 3600:
            return
    except Exception:
        pass
    try:
        d = json.loads(http_raw("https://www.waterdatafortexas.org/reservoirs/recent-conditions.json", 60).decode("utf-8"))
        if not isinstance(d, dict) or len(d) < 50 or sum(1 for v in d.values() if isinstance(v, dict) and v.get("timestamp")) < 50:
            raise ValueError("TWDB answered %s entries with dates" % (len(d) if isinstance(d, dict) else type(d).__name__))
        json.dump({"fetched_at": now_iso(), "rows": d}, open(p + ".tmp", "w", encoding="utf-8"), separators=(",", ":"))
        os.replace(p + ".tmp", p)
        print("ok twdb texas", len(d))
    except Exception as e:
        print("FAIL twdb texas", str(e)[:100])


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
    for f_ in ("lakes.csv", "coasts.csv"):  # lakes and coast stations are not in the legacy river inventory
        for r in csv.DictReader(open(os.path.join(ROOT, "data", f_), encoding="utf-8")):
            inv[r["site"]] = {"lat": r["lat"], "lon": r["lon"], "name": r["raw_name"]}
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


if __name__ == "__main__":
    USGS_OUT[0] = usgs_low()
    main()
