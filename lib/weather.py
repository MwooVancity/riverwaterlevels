"""Weather, air, rain, radar and outlook blocks."""
import statistics, os, re, json, math, collections, hashlib, datetime, zoneinfo
from lib.common import *
from lib.core import *
from lib.hero import *


def b_rain(G):
    n = G["rec"].get("rain") or {}
    v = n.get("inches") or {}
    if not v:
        return None
    age = hours_old(n["fetched_at"], G["now"])
    if age is not None and age > 24:
        return None
    labs = (("last_24h", "Last 24 h"), ("last_2d", "Last 2 days"), ("last_3d", "Last 3 days"))
    vt = n.get("valid_through") or {}
    rows = "".join(tr(["%s, to %s" % (lab, esc(tzl(parse_t(vt[k]), G["zone"]))) if vt.get(k) else lab, "%.2f in" % v[k]], right=(1,)) for k, lab in labs if k in v)
    from lib import ui
    vmax = max(0.5, max(v[k] for k, _ in labs if k in v))
    wid = ui.bars([(lab, v[k], "%.2f in" % v[k]) for k, lab in labs if k in v], vmax)
    rcards = [card(lab, "%.2f <small>in</small>" % v[k], ("to %s" % esc(tzl(parse_t(vt[k]), G["zone"]))) if vt.get(k) else "") for k, lab in labs if k in v]
    return block("rain_totals", "Recent rain at the gauge location", "official", wid,
                 "Source: NWS River Forecast Center multisensor precipitation estimate, 4 km grid at the gauge location, fetched %s. Estimate, not a gauge at the stream. Each window is a separate NWS product with its own end time (hourly and daily products), so a longer window can end earlier than a shorter one and show less rain." % esc(tzl(parse_t(n["fetched_at"]), G["zone"])), "rfc", amber=(age is not None and age > 6))


def b_cpc(G):
    rows = ""
    ocards = []
    src_bits = []
    for key, name in (("cpc610", "6 to 10 day"), ("cpc", "8 to 14 day")):
        c = G["rec"].get(key)
        if not c or not (c.get("temp") or c.get("precip")) or not c.get("issued"):
            continue
        try:
            iss = datetime.datetime.strptime(c["issued"], "%m/%d/%Y").date()
            a_, z_ = (datetime.datetime.strptime(c[k], "%m/%d/%Y").date() for k in ("start", "end"))
        except (KeyError, ValueError):
            continue
        if (G["ldate"] - iss).days > 3:
            continue
        span = "%s to %s" % (a_.strftime("%b %d").replace(" 0", " "), z_.strftime("%b %d").replace(" 0", " "))
        for k, lab in (("temp", "Temperature"), ("precip", "Precipitation")):
            if c.get(k):
                rows += tr([name, span, lab, esc(c[k]["category"] or "–"), "%d%%" % c[k]["prob"]], right=(4,))
                ocards.append(card("%s &middot; %s" % (name, lab), esc(c[k]["category"] or "–"), "%s &middot; probability %d%%" % (span, c[k]["prob"])))
        src_bits.append("%s for %s" % (name, span))
    if not rows:
        return None
    return block("cpc_outlook", "Temperature and precipitation outlooks", "official", rail(ocards, "Temperature and precipitation outlooks"),
                 "Source: NOAA Climate Prediction Center outlooks at the gauge location (%s), issued %s. A probability is the chance of the leaning category (above, near or below normal) for the whole period, not an amount." % ("; ".join(src_bits), iss.strftime("%b %d").replace(" 0", " ")), "cpc")


def b_air(G):
    o = (G["rec"].get("nws") or {}).get("obs")
    if not o:
        return None
    age = hours_old(o["timestamp"], G["now"])
    if age is not None and age > 12:
        return None
    rows = []
    if o.get("temp_c") is not None:
        rows.append(("Air temperature", "%.0f °F" % (o["temp_c"] * 9 / 5 + 32)))
    if o.get("wind_kmh") is not None:
        mph = o["wind_kmh"] * 0.621371
        d = o.get("wind_dir")
        comp = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"][int((d % 360) / 22.5 + 0.5) % 16] + " " if d is not None else ""
        rows.append(("Wind", "Calm" if mph < 1 else "%s%.0f mph" % (comp, mph)))
    if o.get("gust_kmh") is not None:
        rows.append(("Gusts", "%.0f mph" % (o["gust_kmh"] * 0.621371)))
    if o.get("pressure_pa") is not None:
        inhg = o["pressure_pa"] / 3386.389
        tr_txt = ""
        if o.get("pressure_prev_pa") is not None:
            dl = (o["pressure_pa"] - o["pressure_prev_pa"]) / 3386.389
            tr_txt = ", steady" if abs(dl) < 0.02 else ", rising" if dl > 0 else ", falling"
        rows.append(("Pressure", "%.2f inHg%s" % (inhg, tr_txt)))
    if o.get("visibility_m") is not None:
        rows.append(("Visibility", "%.0f mi" % (o["visibility_m"] / 1609.34)))
    if not rows:
        return None
    body = table(["Measure", "Value"], "".join(tr([esc(a), esc(b)], right=(1,)) for a, b in rows), right=(1,))
    return block("air_obs", "Air conditions", "obs", body, "Source: National Weather Service station %s, observed %s." % (esc(o["station"]), esc(tzl(parse_t(o["timestamp"]), G["zone"]))), "nws", amber=(age is not None and age > 3))


def b_radar(G):
    st = (G["rec"].get("nws") or {}).get("radar")
    if not st:
        return None
    return block("radar", "Radar", "official", '<img src="https://radar.weather.gov/ridge/standard/%s_loop.gif" alt="Radar loop, station %s" width="600" height="550" loading="lazy" style="max-width:100%%;height:auto">' % (esc(st), esc(st)),
                 "Source: National Weather Service radar, station %s. The loop is served live by the NWS and shows its own frame times." % esc(st), "rfc")


def b_weather(G, n_periods=14):
    n = G["rec"].get("nws") or {}
    per = n.get("periods") or []
    if not per:
        return None
    age = hours_old(n.get("forecast_updated"), G["now"]) if n.get("forecast_updated") else None
    if age is not None and age > 48:
        return None
    cards = ""
    live = []
    for p in per:
        try:
            gone_ = p.get("endTime") and parse_t(p["endTime"]) <= G["now"]
        except (TypeError, ValueError):
            gone_ = False
        if not gone_ and not (not p.get("endTime") and p.get("isDaytime") and G["now"].astimezone(G["zone"]).hour >= 19):
            live.append(p)
    for p in live[:n_periods]:
        pop = p.get("pop")
        cards += ('<div class="fc"><div>%s</div><b>%s&deg;%s</b><div>%s</div><div class="legend">Wind %s %s</div><div class="legend">%s</div></div>' % (
            esc(p.get("name") or ""), esc(str(p.get("temperature"))), esc(p.get("temperatureUnit") or "F"), esc(p.get("shortForecast") or ""), esc(p.get("windSpeed") or ""), esc(p.get("windDirection") or ""),
            ("%s%% rain" % pop) if pop is not None else ""))
    upd = esc(tzl(parse_t(n["forecast_updated"]), G["zone"])) if n.get("forecast_updated") else "time not stated"
    return block("weather_forecast", "Weather forecast", "official", '<div class="fcs">%s</div>' % cards, "Source: National Weather Service point forecast, updated %s." % upd, "nws", amber=(age is not None and age > 12))


def b_hourly(G):
    n = G["rec"].get("nws") or {}
    hr = n.get("hourly") or []
    age = hours_old(n.get("hourly_updated"), G["now"]) if n.get("hourly_updated") else None
    if not hr or age is None or age > 72:
        return None
    rows = ""
    for p in [p for p in hr if parse_t(p["startTime"]) > G["now"] - datetime.timedelta(hours=1)][:24]:
        pop = p.get("pop")
        rows += tr([esc(tzl(parse_t(p["startTime"]), G["zone"], date=False)), "%s °%s" % (esc(str(p.get("temperature"))), esc(p.get("temperatureUnit") or "F")),
                    "%s %s" % (esc(p.get("windDirection") or ""), esc(p.get("windSpeed") or "")), "%s%%" % pop if pop is not None else "–", esc(p.get("shortForecast") or "")], right=(1, 3))
    if not rows:
        return None
    return block("hourly_forecast", "Hourly forecast, next 24 hours", "official", storm_line(G) + table(["Hour", "Temp", "Wind", "Rain chance", "Sky"], rows, right=(1, 3)),
                 "Source: National Weather Service hourly point forecast, updated %s." % esc(tzl(parse_t(n["hourly_updated"]), G["zone"])), "nws", amber=(age > 12))


def b_heatmap(G):
    n = G["rec"].get("nws") or {}
    g = n.get("grid") or {}
    age = hours_old(g.get("updated"), G["now"]) if g.get("updated") else None
    hrs = [h for h in g.get("hours", []) if parse_t(h["t"]) > G["now"] - datetime.timedelta(hours=1)][:24]
    if len(hrs) < 12 or (age is not None and age > 72):
        return None
    pop = {}
    for p in n.get("hourly") or []:
        pop[parse_t(p["startTime"]).replace(minute=0, second=0, microsecond=0)] = p.get("pop")
    zone = G["zone"]
    head = "<th></th>"
    for h in hrs:
        d = parse_t(h["t"]).astimezone(zone)
        head += "<th>%s</th>" % ("%s 12a" % d.strftime("%a") if d.hour == 0 else "%d%s" % (d.hour % 12 or 12, "a" if d.hour < 12 else "p"))
    mph = lambda k: (lambda v: None if v is None else v * 0.621371)(k)
    spec = (("Temp &deg;F", lambda h: None if h.get("temp_c") is None else h["temp_c"] * 9 / 5 + 32, lambda v: (v - 20) / 90, "%.0f"),
            ("Wind mph", lambda h: mph(h.get("wind_kmh")), lambda v: v / 30, "%.0f"),
            ("Gust mph", lambda h: mph(h.get("gust_kmh")), lambda v: v / 40, "%.0f"),
            ("Direction", lambda h: h.get("dir"), None, None),
            ("Cloud %", lambda h: h.get("sky"), lambda v: v / 100, "%.0f"),
            ("Thunder %", lambda h: h.get("thunder"), lambda v: v / 100, "%.0f"),
            ("Humidity %", lambda h: h.get("rh"), lambda v: v / 100, "%.0f"),
            ("Heat index &deg;F", lambda h: None if h.get("heat_c") is None else h["heat_c"] * 9 / 5 + 32, lambda v: (v - 20) / 90, "%.0f"),
            ("Visibility mi", lambda h: None if h.get("vis_m") is None else h["vis_m"] / 1609.344, lambda v: v / 10, "%.0f"),
            ("Rain in/h", lambda h: None if h.get("qpf_mm") is None else h["qpf_mm"] / 25.4, lambda v: v / 0.1, "%.2f"),
            ("Rain chance %", lambda h: pop.get(parse_t(h["t"])), lambda v: v / 100, "%.0f"))
    rows = ""
    for lab, get, sc, f in spec:
        cells = ""
        for h in hrs:
            v = get(h)
            if v is None:
                cells += "<td>&ndash;</td>"
            elif sc is None:
                cells += "<td>%s</td>" % compass(v)
            else:
                cells += '<td style="background:%s">%s</td>' % (tint(sc(v)), (f % v) if not (lab == "Rain in/h" and v < 0.005) else "0")
        rows += "<tr><th>%s</th>%s</tr>" % (lab, cells)
    upd = esc(tzl(parse_t(g["updated"]), zone)) if g.get("updated") else "time not stated"
    return block("hourly_heatmap", "Hourly forecast, next 24 hours", "official", storm_line(G) + '<div class="scroll"><table class="hm"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (head, rows),
                 "Source: National Weather Service gridpoint forecast, updated %s; rain chance from the NWS hourly point forecast. Hours are gauge-local. Darker cells mean a higher value in that row." % upd, "nws", amber=(age is not None and age > 12))
