"""Weather, alerts and air quality for gauges outside the US: agency formats into the record the US blocks read (rec["nws"]). Parsers only, no network: collect.py fetches, one call per city or station, never per gauge."""
import csv, datetime, io, math, re, zipfile
import xml.etree.ElementTree as ET

NEAR_KM = 60  # a station further than this says nothing about the water here
UTC = datetime.timezone.utc


def km(lat, lon, lat2, lon2):
    a = math.sin(math.radians(lat2 - lat) / 2) ** 2 + math.cos(math.radians(lat)) * math.cos(math.radians(lat2)) * math.sin(math.radians(lon2 - lon) / 2) ** 2
    return 12742 * math.asin(math.sqrt(a))


def nearest(lat, lon, spots, limit=NEAR_KM):
    """(id, km) of the closest {id: [lat, lon, ...]}, or (None, None) past the limit."""
    best = min(((km(lat, lon, s[0], s[1]), i) for i, s in spots.items()), default=None)
    return (best[1], round(best[0])) if best and best[0] <= limit else (None, None)


def inside(lat, lon, ring):
    """Ray cast; ring is [(lat, lon), ...]."""
    hit, n = False, len(ring)
    for i in range(n):
        (y1, x1), (y2, x2) = ring[i], ring[i - 1]
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def alerts_at(lat, lon, items):
    return [{k: v for k, v in a.items() if k != "rings"} for a in items if any(inside(lat, lon, r) for r in a["rings"])]


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
        if p.get("status_en") != "active":
            continue
        polys = [g["coordinates"]] if g.get("type") == "Polygon" else g.get("coordinates") or []
        out.append({"rings": [[(y, x) for x, y, *_ in poly[0]] for poly in polys], "event": (p.get("alert_name_en") or "").capitalize(), "severity": {"yellow": "Moderate", "orange": "Severe", "red": "Extreme"}.get((p.get("risk_colour_en") or "").lower(), "Unknown"),
                    "headline": (p.get("alert_text_en") or "").split("\n\n")[0][:300], "areaDesc": p.get("feature_name_en") or "", "ends": p.get("event_end_datetime"), "expires": p.get("expiration_datetime")})
    return out


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
    per = []
    for f in fg.get("forecasts") or []:
        t = ((f.get("temperatures") or {}).get("temperature") or [{}])[0]
        wind = ((f.get("winds") or {}).get("periods") or [{}])[0]
        ab = f.get("abbreviatedForecast") or {}
        per.append({"name": (f.get("period") or {}).get("textForecastName") or "", "temperature": t.get("value"), "temperatureUnit": "C", "isDaytime": t.get("class") == "high", "shortForecast": ab.get("textSummary") or "", "detailedForecast": f.get("textSummary") or "",
                    "pop": num((ab.get("pop") or {}).get("value")), "windSpeed": "%s km/h" % (wind.get("speed") or {}).get("value") if (wind.get("speed") or {}).get("value") is not None else "", "windDirection": wind.get("direction") or ""})
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
            rings = [[tuple(float(v) for v in pt.split(",")) for pt in (a.text or "").split()] for a in i.findall("c:area/c:polygon", NS)]
            out.append({"rings": [r for r in rings if len(r) > 2], "event": (i.findtext("c:event", "", NS) or "").capitalize(), "severity": i.findtext("c:severity", "Unknown", NS), "headline": " ".join(x for x in (i.findtext("c:headline", "", NS), i.findtext("c:description", "", NS)) if x)[:300],
                        "areaDesc": i.findtext("c:area/c:areaDesc", "", NS), "ends": i.findtext("c:expires", None, NS), "expires": i.findtext("c:expires", None, NS)})
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
    r, when = data[0], lambda r: datetime.datetime.strptime(r[0] + " " + r[1], "%d.%m.%y %H:%M").replace(tzinfo=UTC)
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
    t, ff, dd, n, ww, pop = (series(k) for k in ("TTT", "FF", "DD", "N", "ww", "wwP"))
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
    return {"hourly": hours[:48], "hourly_updated": issued.group(1).replace(".000Z", "+00:00"), "periods": periods, "forecast_updated": issued.group(1).replace(".000Z", "+00:00")}


def demo():
    """Each guard fails without its line."""
    box = [(0, 0), (0, 10), (10, 10), (10, 0)]
    assert inside(5, 5, box) and not inside(15, 5, box) and not inside(5, -1, box)
    assert alerts_at(5, 5, [{"rings": [box], "event": "x"}]) == [{"event": "x"}] and alerts_at(50, 5, [{"rings": [box]}]) == []
    assert canada_alerts({"numberMatched": 2, "features": []}) is None, "a cut-short list must be unknown, never none"
    ended = {"numberMatched": 1, "features": [{"properties": {"status_en": "ended"}, "geometry": None}]}
    assert canada_alerts(ended) == [], "an ended alert must not show"
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
