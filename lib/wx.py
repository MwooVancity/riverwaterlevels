"""Weather, alerts and air quality for gauges outside the US: agency formats into the record the US blocks read (rec["nws"]). Parsers only, no network: collect.py fetches, one call per city or station, never per gauge."""
import csv, datetime, io, json, math, re, zipfile
import xml.etree.ElementTree as ET

NEAR_KM = 60  # a station further than this says nothing about the water here
UTC = datetime.timezone.utc


from lib.common import km  # noqa: E402  the one distance formula; wx.km stays for lib/world.py and collect.py


def nearest(lat, lon, spots, limit=NEAR_KM):
    """(id, km) of the closest {id: [lat, lon, ...]}, or (None, None) past the limit."""
    best = min(((km(lat, lon, s[0], s[1]), i) for i, s in spots.items()), default=None)
    return (best[1], round(best[0])) if best and best[0] <= limit else (None, None)


def drought_map(blob):
    """The Canadian Drought Monitor zip, one GeoJSON per class in EPSG:3857, into [[class, [lat, lon box, rings]]]. Coordinates stay whole: rounding opened false gaps inside solid areas."""
    z, out = zipfile.ZipFile(io.BytesIO(blob)), []
    to_ll = lambda p: [math.degrees(2 * math.atan(math.exp(p[1] / 6378137.0)) - math.pi / 2), math.degrees(p[0] / 6378137.0)]
    for n in sorted(z.namelist()):
        d = json.loads(z.read(n))
        assert d["crs"]["properties"]["name"].endswith("3857"), "drought map changed projection"
        for f in d["features"]:
            g = f["geometry"]
            for poly in ([g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]):
                rings = [[to_ll(p) for p in r] for r in poly]
                out.append([f["properties"]["DM"], [min(p[0] for p in rings[0]), max(p[0] for p in rings[0]), min(p[1] for p in rings[0]), max(p[1] for p in rings[0])], rings])
    return out


def drought_at(lat, lon, polys):
    """The worst class mapped at a point, or None. Holes count by even-odd. ponytail: the box skips most shapes; run once a month per gauge."""
    worst = None
    for dm, box, rings in polys:
        if box[0] <= lat <= box[1] and box[2] <= lon <= box[3] and sum(inside(lat, lon, r) for r in rings) % 2 and (worst is None or dm > worst):
            worst = dm
    return worst


def inside(lat, lon, ring):
    """Ray cast; ring is [(lat, lon), ...]."""
    hit, n = False, len(ring)
    for i in range(n):
        (y1, x1), (y2, x2) = ring[i], ring[i - 1]
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def edge_m(lat, lon, ring):
    """Metres from a point to the nearest edge of a ring, flat-earth: good to a few metres at a few hundred."""
    k, best = 111320 * math.cos(math.radians(lat)), float("inf")
    for (y1, x1), (y2, x2) in zip(ring, ring[1:] + ring[:1]):
        ax, ay, bx, by = (x1 - lon) * k, (y1 - lat) * 110540, (x2 - lon) * k, (y2 - lat) * 110540
        dx, dy = bx - ax, by - ay
        t = max(0, min(1, -(ax * dx + ay * dy) / (dx * dx + dy * dy))) if dx or dy else 0
        best = min(best, math.hypot(ax + t * dx, ay + t * dy))
    return best


def alerts_at(lat, lon, items, within_m=0):
    """Alerts whose area holds the point, or, with within_m, comes that close: a gauge stands in the channel and English warning areas cover the land beside it."""
    out, pad = {}, within_m / 60000  # degrees, wide on purpose: the box only skips what is surely far
    for a in items:
        boxes = a.get("boxes") or [None] * len(a["rings"])
        if any((b is None or b[0] - pad <= lat <= b[1] + pad and b[2] - pad <= lon <= b[3] + pad) and (inside(lat, lon, r) or (within_m and edge_m(lat, lon, r) <= within_m)) for r, b in zip(a["rings"], boxes)):
            out.setdefault((a.get("event"), a.get("headline")), {k: v for k, v in a.items() if k not in ("rings", "boxes")})
    return list(out.values())


def en(o):
    """Canada writes every value as {"en": .., "fr": ..}."""
    if isinstance(o, dict):
        return o["en"] if "en" in o and "fr" in o else {k: en(v) for k, v in o.items()}
    return [en(v) for v in o] if isinstance(o, list) else o


def num(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def canada_alerts(d):
    """Active alerts with their shapes, or None when the reply is cut short: a partial list must never read as 'no alerts'."""
    feats = d.get("features")
    if feats is None or d.get("numberMatched", len(feats)) > len(feats):
        return None
    out = []
    for f in feats:
        p, g = f["properties"], f.get("geometry") or {}
        if (p.get("status_en") or "").lower() in ("ended", "cancelled", "canceled"):  # only a stated end drops an alert: a word we have not seen must show, never hide
            continue
        polys = [g["coordinates"]] if g.get("type") == "Polygon" else g.get("coordinates") or []
        out.append({"rings": [[(y, x) for x, y, *_ in poly[0]] for poly in polys], "event": (p.get("alert_name_en") or "").capitalize(), "severity": {"yellow": "Moderate", "orange": "Severe", "red": "Extreme"}.get((p.get("risk_colour_en") or "").lower(), "Unknown"),
                    "headline": (p.get("alert_text_en") or "").split("\n\n")[0][:300], "areaDesc": p.get("feature_name_en") or "", "ends": p.get("event_end_datetime"), "expires": p.get("expiration_datetime")})
    return None if out and not any(a["rings"] for a in out) else out  # alerts with no usable shapes reach nobody: unknown, never none


EA_CLS = {1: "extreme", 2: "severe", 3: "moderate"}  # the card colour only; the words are the agency's


def ea_floods(d):
    """Environment Agency warnings in force (levels 1 to 3), or None when the reply is cut short or not a list: a partial list must never read as 'no warnings'.
    Level 4 is 'no longer in force' and drops; a level we have not seen shows, never hides."""
    items, lim = d.get("items"), (d.get("meta") or {}).get("limit")
    if not isinstance(items, list) or (lim and len(items) >= lim):
        return None
    return [i for i in items if i.get("severityLevel") != 4 and i.get("floodAreaID")]


def ea_rings(geo):
    """A flood area's GeoJSON into outer rings [(lat, lon), ...]. ponytail: holes are ignored, so a gauge inside a hole is shown the warning; a missed warning is the worse error."""
    out = []
    for f in geo.get("features") or [geo]:
        g = f.get("geometry") or f
        for poly in ([g["coordinates"]] if g.get("type") == "Polygon" else g.get("coordinates") or [] if g.get("type") == "MultiPolygon" else []):
            out.append([(p[1], p[0]) for p in poly[0]])
    return out


def ea_alerts(floods, rings):
    """Warnings in force with their shapes, as alerts_at reads them; rings is {area id: rings}. One area with no shape makes the whole answer unknown."""
    if floods is None or any(not rings.get(f["floodAreaID"]) for f in floods):
        return None
    box = lambda r: [min(p[0] for p in r), max(p[0] for p in r), min(p[1] for p in r), max(p[1] for p in r)]  # ponytail: 2,421 gauges x 300 areas in force tests boxes, not every vertex
    return [{"rings": rings[f["floodAreaID"]], "boxes": [box(r) for r in rings[f["floodAreaID"]]], "event": f.get("severity") or "Flood warning", "severity": "Severity level %s, 1 is highest" % f.get("severityLevel", "not stated"), "cls": EA_CLS.get(f.get("severityLevel"), "unknown"),
             "headline": (f.get("message") or "").strip()[:300], "areaDesc": f.get("description") or f.get("eaAreaName") or "", "ends": None, "expires": None, "id": f["floodAreaID"], "level": f.get("severityLevel")} for f in floods]


def ea_station_ok(s):
    """An active river level station in metres above its stage datum, with no tidal measure: the kind of gauge an English page shows."""
    ms = s.get("measures") or []
    ms = ms if isinstance(ms, list) else [ms]
    return (str(s.get("status", "")).endswith("statusActive") and isinstance(s.get("lat"), (int, float)) and isinstance(s.get("long"), (int, float))
            and not any(m.get("qualifier") == "Tidal Level" for m in ms) and any(m.get("qualifier") == "Stage" and m.get("unitName") == "mASD" for m in ms))


def ea_proof(alerts, stations, within_m):
    """(warning, station) for the first warning in force (level 1 to 3) whose area holds a station of the kind a page shows, by the pages' own rule; else None.
    The alert proof England needs: a real warning reaching the point test. None, an empty list, level 4 or a station far off never prove it."""
    for a in alerts or []:
        if a.get("level") in (1, 2, 3):
            for s in stations:
                if ea_station_ok(s) and alerts_at(s["lat"], s["long"], [a], within_m):
                    return a, s
    return None


def ea_rain_stations(raw):
    """{station: [lat, lon, name, [[measure, period s], ...]]} from the EA rainfall station list: only measures that are mm totals per 15 min or per hour (notation '-t-')."""
    out = {}
    for s in json.loads(raw)["items"]:
        ms = s.get("measures") or []
        ms = [[m["@id"].rsplit("/", 1)[-1], m["period"]] for m in (ms if isinstance(ms, list) else [ms]) if isinstance(m, dict) and m.get("parameter") == "rainfall" and m.get("unitName") == "mm"
              and m.get("period") in (900, 3600) and "-t-" in m.get("@id", "")]
        if ms and isinstance(s.get("lat"), (int, float)) and isinstance(s.get("long"), (int, float)):
            out[s["notation"]] = [s["lat"], s["long"], s.get("label") if isinstance(s.get("label"), str) else "", ms]
    if len(out) < 500:
        raise ValueError("rain station list cut short (%d)" % len(out))
    return out


def rain_total(series, period):
    """(mm, end time) of the 24 h ending at a measure's newest reading, or (None, reason). Every period must be there with a value: a missing one is Unknown, never 0."""
    if not series:
        return None, "no reading in the last day"
    last = max(series)
    end = datetime.datetime.fromisoformat(last.replace("Z", "+00:00"))
    win = [v for t, v in series.items() if 0 <= (end - datetime.datetime.fromisoformat(t.replace("Z", "+00:00"))).total_seconds() < 86400]
    need = 86400 // period
    if len(win) < need:
        return None, "%d of the %d readings of the 24 h to its last one" % (len(win), need)
    if any(not isinstance(v, (int, float)) or v < 0 for v in win):
        return None, "a reading of the last 24 h has no value"
    return round(sum(win), 1), last


def tidal(series):
    """True when the level rises and falls with the tide: its 15-minute steps repeat every 12.4 h and reverse at half that. A river stage does neither.
    Measured 2026-11-03 on 8 days: Gainsborough and Carlton on Trent (tidal) 0.77 and 0.81 at 12.4 h; Colwick, Kingston, Ross-on-Wye at most 0.5, with a larger 6 h value. None: too few readings to say."""
    v = {int(datetime.datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp() // 60): x for t, x in series}
    d = {m: v[m + 15] - v[m] for m in v if m + 15 in v}

    def r(lags):
        best = None
        for lag in lags:
            pairs = [(d[m], d[m + lag * 15]) for m in d if m + lag * 15 in d]
            if len(pairs) < 150:
                continue
            a, b = zip(*pairs)
            ma, mb = sum(a) / len(a), sum(b) / len(b)
            sa, sb = sum((x - ma) ** 2 for x in a) ** .5, sum((y - mb) ** 2 for y in b) ** .5
            c = sum((x - ma) * (y - mb) for x, y in pairs) / (sa * sb) if sa and sb else 0
            best = c if best is None else max(best, c)
        return best
    tide, half = r(range(48, 52)), r(range(24, 26))
    return None if tide is None or half is None else tide >= 0.6 and tide - half >= 0.5


def canada_city(props, lat, lon):
    """citypageweather item into rec["nws"] parts; a value the agency leaves out stays out."""
    p = en(props)
    out, cc = {"place": p.get("name") or ""}, p.get("currentConditions") or {}
    st, w = cc.get("station") or {}, cc.get("wind") or {}
    if cc.get("timestamp"):
        ll = None
        m = re.match(r"([\d.]+)([NS])", str(st.get("lat") or "")), re.match(r"([\d.]+)([EW])", str(st.get("lon") or ""))
        if m[0] and m[1]:
            ll = [float(m[1][1]) * (-1 if m[1][2] == "W" else 1), float(m[0][1]) * (-1 if m[0][2] == "S" else 1)]
        speed = (w.get("speed") or {}).get("value")
        out["obs"] = {"station": str(st.get("code") or "").upper(), "name": st.get("value") or "", "ll": ll, "timestamp": cc["timestamp"], "temp_c": num((cc.get("temperature") or {}).get("value")), "wind_kmh": 0 if speed == "calm" else num(speed),
                      "wind_dir": num((w.get("bearing") or {}).get("value")), "gust_kmh": num((w.get("gust") or {}).get("value")), "pressure_pa": (lambda v: None if v is None else v * 1000)(num((cc.get("pressure") or {}).get("value")))}
    fg = p.get("forecastGroup") or {}
    per, start = [], datetime.datetime.fromisoformat(fg["timestamp"].replace("Z", "+00:00")) if fg.get("timestamp") else None
    for n_, f in enumerate(fg.get("forecasts") or []):
        t = ((f.get("temperatures") or {}).get("temperature") or [{}])[0]
        wind = ((f.get("winds") or {}).get("periods") or [{}])[0]
        ab = f.get("abbreviatedForecast") or {}
        per.append({"name": (f.get("period") or {}).get("textForecastName") or "", "temperature": t.get("value"), "temperatureUnit": "C", "isDaytime": t.get("class") == "high", "shortForecast": ab.get("textSummary") or "", "detailedForecast": f.get("textSummary") or "",
                    "pop": num((ab.get("pop") or {}).get("value")), "windSpeed": "%s km/h" % (wind.get("speed") or {}).get("value") if (wind.get("speed") or {}).get("value") is not None else "", "windDirection": wind.get("direction") or "", "endTime": (start + datetime.timedelta(hours=12 * (n_ + 1) + 6)).isoformat() if start else None})
    if per and fg.get("timestamp"):
        out["periods"], out["forecast_updated"] = per, fg["timestamp"]
    hg = p.get("hourlyForecastGroup") or {}
    hr = [{"startTime": h["timestamp"], "temperature": (h.get("temperature") or {}).get("value"), "temperatureUnit": "C", "pop": (h.get("lop") or {}).get("value"), "shortForecast": h.get("condition") or "",
           "windSpeed": "%s km/h" % (h.get("wind") or {}).get("speed", {}).get("value"), "windDirection": ((h.get("wind") or {}).get("direction") or {}).get("value") or ""} for h in hg.get("hourlyForecasts") or [] if h.get("timestamp")]
    if hr and hg.get("timestamp"):
        out["hourly"], out["hourly_updated"] = hr, hg["timestamp"]
    return out


NS = {"c": "urn:oasis:names:tc:emergency:cap:1.2"}


def dwd_alerts(blob):
    """DWD's English CAP zip, one alert per file. A zip that will not open raises, so the caller keeps the last answer and its old time."""
    out = []
    z = zipfile.ZipFile(io.BytesIO(blob))
    for name in z.namelist():
        x = ET.fromstring(z.read(name))
        if x.findtext("c:status", "", NS) != "Actual" or x.findtext("c:msgType", "", NS) == "Cancel":
            continue
        for i in x.findall("c:info", NS):
            for area in i.findall("c:area", NS):  # one warning covers many counties: the page names the one holding this gauge
                rings = [[tuple(float(v) for v in pt.split(",")) for pt in (a.text or "").split()] for a in area.findall("c:polygon", NS)]
                out.append({"rings": [r for r in rings if len(r) > 2], "event": (i.findtext("c:event", "", NS) or "").capitalize(), "severity": i.findtext("c:severity", "Unknown", NS), "headline": " ".join(x for x in (i.findtext("c:headline", "", NS), i.findtext("c:description", "", NS)) if x)[:300],
                            "areaDesc": area.findtext("c:areaDesc", "", NS), "ends": i.findtext("c:expires", None, NS), "expires": i.findtext("c:expires", None, NS)})
    if out and not any(a["rings"] for a in out):
        raise ValueError("DWD alerts with no shapes")  # the caller keeps the last answer, which ages into Unknown
    return out


def german(sid):
    """WMO block 10 is Germany; letter ids are DWD's own points. The nearest forecast point decides, so a Swiss or Austrian gauge gets no German all-clear."""
    return sid[:2] == "10" or not sid[:5].isdigit()


def dwd_stations(text):
    """The MOSMIX catalogue: {id: [lat, lon, name]}. Its positions are degrees.minutes, not decimals (Jan Mayen 70.56 is 70 deg 56 min)."""
    dm = lambda v: (abs(v) // 1 + (abs(v) % 1) * 100 / 60) * (-1 if v < 0 else 1)
    out = {}
    for line in text.splitlines()[2:]:
        m = re.match(r"(\S{4,5})\s+\S+\s+(.+?)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+-?\d+\s*$", line)
        if m:
            out[m.group(1)] = [round(dm(float(m.group(3))), 4), round(dm(float(m.group(4))), 4), m.group(2).title()]
    return out


def dwd_obs(text, sid, spot):
    """Latest row of a BEOB file, plus the 24 h rain total when every hour reported. Decimal commas, --- for no value."""
    rows = list(csv.reader(io.StringIO(text), delimiter=";"))
    head, data = rows[0], [r for r in rows[3:] if len(r) == len(rows[0])]
    if not data:
        return {}
    col = lambda r, k: num(r[head.index(k)]) if k in head else None
    when = lambda r: datetime.datetime.strptime(r[0] + " " + r[1], "%d.%m.%y %H:%M").replace(tzinfo=UTC)
    r = next((x for x in data if col(x, "dry_bulb_temperature_at_2_meter_above_ground") is not None), data[0])  # the newest row can be all "---" (Geisenheim 02:00, 2026-11-03)
    vis, hpa = col(r, "horizontal_visibility"), col(r, "pressure_reduced_to_mean_sea_level")
    out = {"obs": {"station": sid, "name": spot[2], "ll": [spot[1], spot[0]], "timestamp": when(r).isoformat(), "temp_c": col(r, "dry_bulb_temperature_at_2_meter_above_ground"), "wind_kmh": col(r, "mean_wind_speed_during last_10_min_at_10_meters_above_ground"),
                   "wind_dir": col(r, "mean_wind_direction_during_last_10 min_at_10_meters_above_ground"), "gust_kmh": col(r, "maximum_wind_speed_last_hour"), "pressure_pa": None if hpa is None else hpa * 100, "visibility_m": None if vis is None else vis * 1000}}
    day = [(when(x), col(x, "precipitation_amount_last_hour")) for x in data if (when(r) - when(x)).total_seconds() < 86400]
    if len(day) >= 24 and all(v is not None for _, v in day):
        out["rain"] = {"inches": {"last_24h": round(sum(v for _, v in day) / 25.4, 3)}, "valid_through": {"last_24h": when(r).isoformat()}, "fetched_at": when(r).isoformat()}
    return out


SKY = ((95, 99, "Thunderstorm"), (85, 86, "Snow showers"), (83, 84, "Sleet showers"), (80, 82, "Rain showers"), (70, 79, "Snow"), (68, 69, "Sleet"), (66, 67, "Freezing rain"), (61, 65, "Rain"), (56, 57, "Freezing drizzle"), (50, 55, "Drizzle"), (45, 49, "Fog"))
COMPASS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def sky(ww, cloud):
    """DWD's present-weather code, in English. Codes below 45 say nothing falls, so the cloud share decides."""
    for a, b, word in SKY:
        if ww is not None and a <= ww <= b:
            return word
    return "" if cloud is None else "Clear" if cloud < 25 else "Partly cloudy" if cloud < 60 else "Mostly cloudy" if cloud < 90 else "Cloudy"


def dwd_forecast(blob, zone):
    """MOSMIX_L kmz into hourly rows and day and night periods. Wind is m/s, temperature kelvin; '-' is no value."""
    z = zipfile.ZipFile(io.BytesIO(blob))
    text = z.read(z.namelist()[0]).decode("latin1")
    times = [datetime.datetime.fromisoformat(t.replace(".000Z", "+00:00")) for t in re.findall(r"<dwd:TimeStep>([^<]+)", text)]
    issued = re.search(r"<dwd:IssueTime>([^<]+)", text)
    if not times or not issued:
        return {}
    def series(k):
        m = re.search(r'elementName="%s">\s*<dwd:value>([^<]*)' % k, text)
        return [num(v) for v in m.group(1).split()] if m else [None] * len(times)
    t, ff, dd, n, ww, pop, rain = (series(k) for k in ("TTT", "FF", "DD", "N", "ww", "wwP", "RRdc"))  # RRdc, the 24 h total: hourly RR1c counts only rain tied to the forecast weather and read 3.6 mm where the daily totals said 9.6
    hours = []
    for i, when in enumerate(times):
        if t[i] is None:
            continue
        hours.append({"startTime": when.isoformat(), "temperature": round(t[i] - 273.15), "temperatureUnit": "C", "pop": None if pop[i] is None else round(pop[i]), "shortForecast": sky(ww[i], n[i]), "windSpeed": "" if ff[i] is None else "%d km/h" % round(ff[i] * 3.6),
                      "windDirection": "" if dd[i] is None else COMPASS[int((dd[i] % 360) / 45 + 0.5) % 8], "_kmh": ff[i] and ff[i] * 3.6, "_ww": ww[i], "_t": t[i], "_local": when.astimezone(zone)})
    groups = {}
    for h in hours:
        day = 6 <= h["_local"].hour < 18
        key = h["_local"].date() if h["_local"].hour >= 6 else h["_local"].date() - datetime.timedelta(days=1)
        groups.setdefault((key, not day), []).append(h)
    periods = []
    for (d, night), hs in sorted(groups.items())[:14]:
        worst = max(hs, key=lambda h: (h["_ww"] or 0))
        top = max(hs, key=lambda h: h["_kmh"] or 0)
        periods.append({"name": d.strftime("%A") + (" night" if night else ""), "temperature": round((min if night else max)(h["_t"] for h in hs) - 273.15), "temperatureUnit": "C", "isDaytime": not night, "shortForecast": worst["shortForecast"], "pop": max((h["pop"] or 0) for h in hs),
                        "windSpeed": top["windSpeed"], "windDirection": top["windDirection"], "endTime": (hs[-1]["_local"] + datetime.timedelta(hours=1)).astimezone(UTC).isoformat()})
    for h in hours:
        for k in ("_kmh", "_ww", "_t", "_local"):
            del h[k]
    return {"hourly": hours[:48], "hourly_updated": issued.group(1).replace(".000Z", "+00:00"), "periods": periods, "forecast_updated": issued.group(1).replace(".000Z", "+00:00"), "rain_days": {"updated": issued.group(1), "days": [[when.isoformat(), rain[k]] for k, when in enumerate(times) if rain[k] is not None]}}


def met_forecast(hourly, daily, zone):
    """Met Office Global Spot (DataHub site-specific, GeoJSON) into the rows the weather blocks read. Wind m/s, temperature °C.
    No sky words: the significant weather code table is not read from the Met Office yet. A field we do not find stays out, never guessed."""
    props = lambda j: (((j or {}).get("features") or [{}])[0] or {}).get("properties") or {}
    n = lambda v: v if isinstance(v, (int, float)) else None
    at = lambda s: datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    kmh = lambda v: "" if n(v) is None else "%d km/h" % round(v * 3.6)
    way = lambda v: "" if n(v) is None else COMPASS[int((v % 360) / 45 + 0.5) % 8]
    h, d = props(hourly), props(daily)
    out = {}
    if h.get("modelRunDate"):
        out["hourly"] = [{"startTime": at(x["time"]).isoformat(), "temperature": round(x["screenTemperature"]), "temperatureUnit": "C", "pop": n(x.get("probOfPrecipitation")), "shortForecast": "",
                          "windSpeed": kmh(x.get("windSpeed10m")), "windDirection": way(x.get("windDirectionFrom10m"))} for x in h.get("timeSeries") or [] if x.get("time") and n(x.get("screenTemperature")) is not None][:48]
        out["hourly_updated"] = at(h["modelRunDate"]).isoformat()
    if d.get("modelRunDate"):
        periods = []
        for x in d.get("timeSeries") or []:
            day = at(x["time"]).astimezone(zone).date() if x.get("time") else None
            for night, t, p, ws, wd in ((False, "dayMaxScreenTemperature", "dayProbabilityOfPrecipitation", "midday10MWindSpeed", "midday10MWindDirection"), (True, "nightMinScreenTemperature", "nightProbabilityOfPrecipitation", "midnight10MWindSpeed", "midnight10MWindDirection")):
                if day and n(x.get(t)) is not None:
                    end = datetime.datetime.combine(day + datetime.timedelta(days=1 if night else 0), datetime.time(6 if night else 18), zone)
                    periods.append({"name": day.strftime("%A") + (" night" if night else ""), "temperature": round(x[t]), "temperatureUnit": "C", "isDaytime": not night, "shortForecast": "", "pop": n(x.get(p)),
                                    "windSpeed": kmh(x.get(ws)), "windDirection": way(x.get(wd)), "endTime": end.astimezone(UTC).isoformat()})
        out["periods"], out["forecast_updated"] = periods[:14], at(d["modelRunDate"]).isoformat()
    for rows, t in (("hourly", "hourly_updated"), ("periods", "forecast_updated")):
        if not out.get(rows):  # a time with no rows would date the last run's rows as new
            out.pop(rows, None), out.pop(t, None)
    return out


def suspect(series, unit, now):
    """(hold, note) for a reading that may be false, from its own series. A time in the future is wrong, so it holds; a flat week or a jump in one step may be real, so the page says so and shows it."""
    if not series:
        return False, ""
    pts = [(datetime.datetime.fromisoformat(t.replace("Z", "+00:00")), v) for t, v in series]
    if pts[-1][0] > now + datetime.timedelta(hours=1):
        return True, "reading time is in the future"
    big = 50 if unit == "cm" else 0.5
    if len(pts) >= 2 and abs(pts[-1][1] - pts[-2][1]) > big and (pts[-1][0] - pts[-2][0]).total_seconds() <= 7200:
        return False, "Latest reading jumped sharply from the one before; it may be a sensor fault. "
    if len(pts) >= 96 and (pts[-1][0] - pts[0][0]).days >= 6 and len({v for _, v in pts}) == 1:
        return False, "Reading has not changed in %d days; the sensor may be stuck. " % (pts[-1][0] - pts[0][0]).days
    return False, ""


def day_stats(feats):
    """A gauge's whole daily record into what a page needs: low, median and high for each calendar date, and the deciles of every day on record."""
    by, every = {}, []
    for f in feats:
        p = f["properties"]
        if p.get("LEVEL") is not None:
            by.setdefault(p["DATE"][5:10], []).append(round(p["LEVEL"], 3))
            every.append(p["LEVEL"])
    if len(every) < 3650:
        return {}
    every.sort()
    return {"days": {k: [min(v), sorted(v)[len(v) // 2], max(v), len(v)] for k, v in by.items() if len(v) >= 10}, "deciles": [round(every[i * (len(every) - 1) // 10], 3) for i in range(11)], "day_years": len(every) // 365}


def ea_days(lows, highs, this_year):
    """An English gauge's daily lowest and highest stage (EA Hydrology API rows) into each calendar date's lowest and highest across years, and each past year's
    highest and lowest with dates. The agency publishes no daily mean, so there is no median. Suspect, Missing and incomplete days are left out; a date needs 10 years, a year 300 days."""
    def clean(rows, pick):
        out = {}
        for r in rows:
            if r.get("completeness") != "Complete" or r.get("quality") not in ("Good", "Estimated", "Unchecked"):
                continue
            try:
                v = float(r["value"])
            except (KeyError, TypeError, ValueError):
                continue
            out[r["date"]] = pick(v, out.get(r["date"], v))  # the agency repeats a date at times: its lowest low, its highest high
        return out
    lo, hi = clean(lows, min), clean(highs, max)
    by = {}
    for i, rows in enumerate((lo, hi)):
        for d, v in rows.items():
            by.setdefault(d[5:10], ([], []))[i].append(v)
    days = {k: [round(min(a), 3), None, round(max(b), 3), min(len(a), len(b))] for k, (a, b) in by.items() if len(a) >= 10 and len(b) >= 10}
    if not days:
        return {}
    years = []
    for y in sorted({int(d[:4]) for d in lo} & {int(d[:4]) for d in hi}):
        a, b = {d: v for d, v in lo.items() if d.startswith(str(y))}, {d: v for d, v in hi.items() if d.startswith(str(y))}
        if y < this_year and len(a) >= 300 and len(b) >= 300:
            hd, ld = max(b, key=b.get), min(a, key=a.get)
            years.append([y, round(b[hd], 3), hd, round(a[ld], 3), ld])
    return {"days": days, "years": years[-15:], "day_years": len({d[:4] for d in lo})}


def day_add(a, name, day, v):
    """One reading into a gauge's daily low and high: {gauge: {date: [low, high]}}."""
    lo, hi = a.setdefault(name, {}).get(day, [v, v])
    a[name][day] = [min(lo, v), max(hi, v)]


def demo():
    """Each guard fails without its line."""
    box = [(0, 0), (0, 10), (10, 10), (10, 0)]
    fake = [{"properties": {"DATE": "%d-06-01" % y, "LEVEL": float(y % 7)}} for y in range(1900, 1915)]
    assert day_stats(fake) == {}, "under 10 years says nothing"
    many = [{"properties": {"DATE": "%d-%02d-%02d" % (y, m, d), "LEVEL": float(d)}} for y in range(2000, 2012) for m in range(1, 13) for d in range(1, 29)]
    got = day_stats(many)
    assert got["days"]["03-05"][:3] == [5.0, 5.0, 5.0] and got["deciles"][0] == 1.0 and got["deciles"][10] == 28.0
    two = [{"rings": [box], "event": "x", "headline": "h", "areaDesc": "here"}, {"rings": [box], "event": "x", "headline": "h", "areaDesc": "also"}, {"rings": [[(50, 50), (50, 60), (60, 60)]], "event": "x", "headline": "h", "areaDesc": "far"}]
    assert [a["areaDesc"] for a in alerts_at(5, 5, two)] == ["here"], "one line per alert, named for the county that holds the gauge"
    t0 = datetime.datetime(2026, 11, 2, 12, tzinfo=UTC)
    at = lambda h: (t0 + datetime.timedelta(hours=h)).isoformat()
    assert suspect([[at(5), 10]], "cm", t0)[0], "a future reading holds"
    assert "jumped" in suspect([[at(-1), 10], [at(0), 200]], "cm", t0)[1] and not suspect([[at(-1), 10], [at(0), 200]], "cm", t0)[0], "a jump shows, marked"
    assert "not changed" in suspect([[at(-i), 10] for i in range(168, -1, -1)], "cm", t0)[1], "a flat week is marked"
    assert suspect([[at(-i), 10 + i % 3] for i in range(168, -1, -1)], "cm", t0) == (False, "")
    assert canada_alerts({"numberMatched": 1, "features": [{"properties": {"status_en": "issued"}, "geometry": None}]}) is None, "alerts with no shapes are unknown"
    arc = {}
    for v in (5, 9, 2):
        day_add(arc, "g", "2026-11-02", v)
    assert arc == {"g": {"2026-11-02": [2, 9]}}, "a day keeps its low and its high"
    assert inside(5, 5, box) and not inside(15, 5, box) and not inside(5, -1, box)
    assert alerts_at(5, 5, [{"rings": [box], "event": "x"}]) == [{"event": "x"}] and alerts_at(50, 5, [{"rings": [box]}]) == []
    assert canada_alerts({"numberMatched": 2, "features": []}) is None, "a cut-short list must be unknown, never none"
    ended = {"numberMatched": 1, "features": [{"properties": {"status_en": "ended"}, "geometry": None}]}
    assert canada_alerts(ended) == [], "an ended alert must not show"
    ring = {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]}
    for word in ("issued", "continued", "some new word", None):
        got = canada_alerts({"numberMatched": 1, "features": [{"properties": {"status_en": word, "alert_name_en": "fog advisory"}, "geometry": ring}]})
        assert alerts_at(5, 5, got) and alerts_at(5, 5, got)[0]["event"] == "Fog advisory", "a live alert must reach the page"
    assert nearest(50, 8, {"far": [60, 8, "x"]}) == (None, None), "a far station must not stand in for this river"
    assert canada_city({"currentConditions": {"timestamp": "t", "wind": {"speed": {"value": "calm"}}, "temperature": {"value": None}}}, 0, 0)["obs"]["wind_kmh"] == 0, "calm is a value"
    assert dwd_stations("h\n-\n01001 ENJA JAN MAYEN             70.56   -8.40    10\n")["01001"][:2] == [70.9333, -8.6667], "catalogue positions are degrees.minutes"
    assert german("10513") and german("K2861") and not german("06660") and not german("11120"), "a station past the border must not speak for Germany"
    assert sky(61, 100) == "Rain" and sky(3, 10) == "Clear" and sky(None, None) == ""
    csvh = "a;b;dry_bulb_temperature_at_2_meter_above_ground;precipitation_amount_last_hour\nx\ny\n"
    rows = "".join("%02d.11.26;%02d:00;7,5;%s\n" % (2 if h <= 12 else 1, (12 - h) % 24, "1" if h else "---") for h in range(24))
    assert "rain" not in dwd_obs(csvh + rows, "1", [0, 0, "n"]), "a gap in the hours must not read as a dry day"
    assert dwd_obs(csvh + rows.replace("---", "0"), "1", [0, 0, "n"])["rain"]["inches"]["last_24h"] == round(23 / 25.4, 3)
    assert dwd_obs(csvh, "1", [0, 0, "n"]) == {}


if __name__ == "__main__":
    demo()
    print("wx ok")
