"""Weather, air, rain, radar and outlook blocks."""
import statistics, os, re, json, math, collections, hashlib, datetime, zoneinfo
from lib.common import *
from lib.core import *
from lib.hero import *


def _wind(p, label=True):
    sp, d = (p.get("windSpeed") or "").strip(), (p.get("windDirection") or "").strip()
    if sp.startswith("0 "):
        return "calm" if label else "Calm"
    return esc(("%s %s" % (d, sp)).strip())


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
    wid = ui.bars([(lab + ((" <small>to %s</small>" % esc(tzl(parse_t(vt[k]), G["zone"]))) if vt.get(k) else ""), v[k], "%.2f in" % v[k]) for k, lab in labs if k in v], vmax)
    ks = [k for k, _ in labs if k in v]
    if any(v[b] < v[a] - 0.005 for a, b in zip(ks, ks[1:])):  # full review: "24 h 0.03 in" above "2 days 0.00 in"
        wid += '<p class="src">The longer windows end earlier than the last-24-h estimate, so they do not include the most recent rain.</p>' 
    rcards = [card(lab, "%.2f <small>in</small>" % v[k], ("to %s" % esc(tzl(parse_t(vt[k]), G["zone"]))) if vt.get(k) else "") for k, lab in labs if k in v]
    return block("rain_totals", "Recent rain at the gauge location", "official", wid,
                 "Source: NWS River Forecast Center multisensor precipitation estimate, about 2.5-mile grid at the gauge location, fetched %s. Estimate, not a gauge at the stream. Each window is a separate NWS product with its own end time (hourly and daily products), so a longer window can end earlier than a shorter one and show less rain." % esc(tzl(parse_t(n["fetched_at"]), G["zone"])), "rfc", amber=age)


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
        span = "%s to %s" % (md(a_), md(z_))
        for k, lab in (("temp", "Temperature"), ("precip", "Precipitation")):
            if c.get(k):
                rows += tr([name, span, lab, esc(c[k]["category"] or "–"), "%d%%" % c[k]["prob"]], right=(4,))
                ocards.append(card("%s &middot; %s" % (name, lab), (esc(c[k]["category"] or "–") if (c[k].get("prob") or 0) > 34 else "Near equal chances"), "%s &middot; probability %d%%" % (span, c[k]["prob"])))
        src_bits.append("%s for %s, issued %s" % (name, span, md(iss)))
    if not rows:
        return None
    return block("cpc_outlook", "Temperature and precipitation outlooks", "official", rail(ocards, "Temperature and precipitation outlooks"),
                 "Source: NOAA Climate Prediction Center outlooks at the gauge location (%s). A probability is the chance of the leaning category (above, near or below normal) for the whole period, not an amount." % "; ".join(src_bits), "cpc")


def b_air(G):
    o = (G["rec"].get("nws") or {}).get("obs")
    if not o:
        return None
    age = hours_old(o["timestamp"], G["now"])
    if age is not None and age > HIDE_H["air_obs"]:
        return None
    rows = []
    if o.get("temp_c") is not None:
        rows.append(("temp", "Air temperature", "%.0f °F" % (o["temp_c"] * 9 / 5 + 32)))
    if o.get("wind_kmh") is not None:
        mph = km_mi(o["wind_kmh"])
        d = o.get("wind_dir")
        comp = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"][int((d % 360) / 22.5 + 0.5) % 16] + " " if d is not None else ""
        rows.append(("wind", "Wind", "Calm" if mph < 1 else "%s%.0f mph" % (comp, mph)))
    if o.get("gust_kmh") is not None:
        rows.append(("gust", "Gusts", "%.0f mph" % km_mi(o["gust_kmh"])))
    if o.get("pressure_pa") is not None:
        inhg = o["pressure_pa"] / 3386.389
        tr_txt = ""
        if o.get("pressure_prev_pa") is not None:
            dl = (o["pressure_pa"] - o["pressure_prev_pa"]) / 3386.389
            tr_txt = ", steady" if abs(dl) < 0.02 else ", rising" if dl > 0 else ", falling"
        rows.append(("pres", "Pressure", "%.2f inHg%s" % (inhg, tr_txt)))
    if o.get("visibility_m") is not None:
        rows.append(("vis", "Visibility", "%.0f mi" % (o["visibility_m"] / 1609.34)))
    if not rows:
        return None
    mi = (", %d mi from the gauge" % round(miles_between(G["lat"], G["lon"], o["ll"][1], o["ll"][0]))) if o.get("ll") else ""
    body = '<p class="src">NWS station %s%s%s, observed <span data-wx="t">%s</span>.</p><span hidden data-wxst="%s" data-t="%s"></span>' % (esc(o["station"]), (" (%s)" % esc(o["name"])) if o.get("name") else "", mi, esc(tzl(parse_t(o["timestamp"]), G["zone"])), esc(o["station"]), esc(o["timestamp"])) + table(["Measure", "Value"], "".join(tr([esc(a), '<span data-wx="%s">%s</span>' % (k, esc(b))], right=(1,)) for k, a, b in rows), right=(1,))
    return block("air_obs", "Air conditions at weather station %s" % esc(o["station"]), "obs", body, "Source: National Weather Service station %s, observed <span data-wx=\"t\">%s</span>." % (esc(o["station"]), esc(tzl(parse_t(o["timestamp"]), G["zone"]))), "nws", amber=age)


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
    if age is not None and age > HIDE_H["weather_forecast"]:
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
    live = live[:n_periods]
    days = []
    for p in live:  # a day card is a daytime period and the night after it; a leading night stands alone
        if days and not p.get("isDaytime") and days[-1][0].get("isDaytime") and len(days[-1]) == 1:
            days[-1].append(p)
        else:
            days.append([p])
    deg = lambda p: "&ndash;" if p.get("temperature") is None else "%s&deg;" % esc(str(p.get("temperature")))
    for d in days:
        hi = d[0] if d[0].get("isDaytime") else None
        lo = d[-1] if not d[-1].get("isDaytime") else None
        unit = esc(d[0].get("temperatureUnit") or "F")
        temps = "%s <small>/ %s%s</small>" % (deg(hi), deg(lo), unit) if hi and lo else "%s%s" % (deg(d[0]), unit)
        tlab = "High / low" if hi and lo else "High" if hi else "Low"
        rain = ("Rain or snow %s" % " / ".join(("%s%%" % x["pop"]) if x.get("pop") is not None else "&ndash;" for x in d)) if any(x.get("pop") is not None for x in d) else ""
        cards += ('<div class="fc"><div>%s</div><b>%s</b><div class="legend">%s</div><div>%s</div><div class="legend">%s</div><div class="legend">Wind %s</div></div>' % (
            esc(d[0].get("name") or ""), temps, tlab, esc(d[0].get("shortForecast") or ""), rain, _wind(d[0])))
    rows = "".join(tr([esc(p.get("name") or ""), "%s%s" % (deg(p), esc(p.get("temperatureUnit") or "F")), _wind(p, False), ("%s%%" % p["pop"]) if p.get("pop") is not None else "&ndash;", esc(p.get("detailedForecast") or p.get("shortForecast") or "")]) for p in live)
    upd = esc(tzl(parse_t(n["forecast_updated"]), G["zone"])) if n.get("forecast_updated") else "time not stated"
    return block("weather_forecast", "Weather forecast", "official", '<div class="fcs" role="region" aria-label="Weather forecast by day" tabindex="0">%s</div>' % cards + more("Every NWS forecast period, in full", table(["Period", "Temp", "Wind", "Rain or snow", "Forecast"], rows)),
                 "Source: National Weather Service point forecast, updated %s. Each card is one day: the daytime period and the night after it (high / low, and the chance of rain or snow for each)." % upd, "nws", amber=age)


def b_hourly(G):
    n = G["rec"].get("nws") or {}
    hr = n.get("hourly") or []
    age = hours_old(n.get("hourly_updated"), G["now"]) if n.get("hourly_updated") else None
    if not hr or age is None or age > HIDE_H["hourly_forecast"]:
        return None
    rows = ""
    for p in [p for p in hr if parse_t(p["startTime"]) > G["now"] - datetime.timedelta(hours=1)][:24]:
        pop = p.get("pop")
        rows += tr([esc(tzl(parse_t(p["startTime"]), G["zone"], date=False)), "%s °%s" % (("–" if p.get("temperature") is None else esc(str(p.get("temperature")))), esc(p.get("temperatureUnit") or "F")),
                    _wind(p, False), "%s%%" % pop if pop is not None else "–", esc(p.get("shortForecast") or "")], right=(1, 3))
    if not rows:
        return None
    return block("hourly_forecast", "Hourly forecast, next 24 hours", "official", storm_line(G) + table(["Hour", "Temp", "Wind", "Rain chance", "Sky"], rows, right=(1, 3)),
                 "Source: National Weather Service hourly point forecast, updated %s." % esc(tzl(parse_t(n["hourly_updated"]), G["zone"])), "nws", amber=age)


def b_heatmap(G):
    n = G["rec"].get("nws") or {}
    g = n.get("grid") or {}
    age = hours_old(g.get("updated"), G["now"]) if g.get("updated") else None
    hrs = [h for h in g.get("hours", []) if parse_t(h["t"]) > G["now"] - datetime.timedelta(hours=1)][:24]
    if len(hrs) < 12 or (age is not None and age > HIDE_H["hourly_heatmap"]):
        return None
    pop, sky = {}, {}
    for p in n.get("hourly") or []:
        pop[parse_t(p["startTime"]).replace(minute=0, second=0, microsecond=0)] = p.get("pop")
        sky[parse_t(p["startTime"]).replace(minute=0, second=0, microsecond=0)] = p.get("shortForecast")
    zone = G["zone"]
    def head_of(hs):
        out = "<th></th>"
        for h in hs:
            d = parse_t(h["t"]).astimezone(zone)
            out += "<th>%s</th>" % ("%s 12a" % d.strftime("%a") if d.hour == 0 else ("%s %d%s" % (d.strftime("%a"), d.hour % 12 or 12, "a" if d.hour < 12 else "p")) if h is hs[0] else "%d%s" % (d.hour % 12 or 12, "a" if d.hour < 12 else "p"))
        return out
    mph = lambda k: (lambda v: None if v is None else km_mi(v))(k)
    spec = (("Temp &deg;F", lambda h: None if h.get("temp_c") is None else h["temp_c"] * 9 / 5 + 32, lambda v: (v - 20) / 90, "%.0f"),
            ("Wind mph", lambda h: mph(h.get("wind_kmh")), lambda v: v / 30, "%.0f"),
            ("Gust mph", lambda h: mph(h.get("gust_kmh")), lambda v: v / 40, "%.0f"),
            ("Direction", lambda h: h.get("dir"), None, None),
            ("Cloud %", lambda h: h.get("sky"), lambda v: v / 100, "%.0f"),
            ("Thunder %", lambda h: h.get("thunder"), lambda v: v / 100, "%.0f"),
            ("Humidity %", lambda h: h.get("rh"), lambda v: v / 100, "%.0f"),
            ("Heat index &deg;F", lambda h: None if h.get("heat_c") is None else h["heat_c"] * 9 / 5 + 32, lambda v: (v - 20) / 90, "%.0f"),
            ("Visibility mi", lambda h: None if not h.get("vis_m") else h["vis_m"] / 1609.344, lambda v: v / 10, "%.1f"),  # fog under a mile is not "0" (full review)
            ("Rain/snow in/h", lambda h: None if h.get("qpf_mm") is None else h["qpf_mm"] / 25.4, lambda v: v / 0.1, "%.2f"),
            ("Rain/snow %", lambda h: pop.get(parse_t(h["t"])), lambda v: v / 100, "%.0f"))
    PEAK_ROWS = ("Wind mph", "Gust mph", "Thunder %", "Rain/snow in/h", "Rain/snow %")
    def rows_of(groups, quiet):
        out = ""
        for lab, get, sc, f in spec:
            vals = [get(h) for h in hrs]
            if sum(v is None for v in vals) > len(vals) / 2 or (lab == "Visibility mi" and all(not v for v in vals)):
                continue  # a row of dashes (or a grid that reports 0 mi visibility every hour) says nothing (hater 2026-10-27)
            if quiet and lab in quiet:
                continue  # zero all day: said once in the summary line instead
            cells = ""
            for grp in groups:
                gv = [x for x in (get(h) for h in grp) if x is not None]
                v = (max(gv) if gv else None) if lab in PEAK_ROWS and len(grp) > 1 else get(grp[0])
                if v is None:
                    cells += "<td>&ndash;</td>"
                elif sc is None:
                    cells += "<td>%s</td>" % compass(v)
                else:
                    cells += '<td style="background:%s">%s</td>' % (tint(sc(v)), (f % v) if not (lab == "Rain/snow in/h" and v < 0.01) else ("0" if v < 0.001 else "&lt;0.01"))
            out += "<tr><th>%s</th>%s</tr>" % (lab, cells)
        return out
    col = {lab: [v for v in (get(h) for h in hrs) if v is not None] for lab, get, sc, f in spec}
    quiet = {lab for lab in ("Thunder %", "Rain/snow in/h", "Heat index &deg;F") if col.get(lab) and max(col[lab]) < 0.005} | ({"Humidity %", "Cloud %"})
    def peak(lab):
        v = col.get(lab)
        if not v:
            return None
        i = max(range(len(hrs)), key=lambda k: (spec_get[lab](hrs[k]) or -1))
        return max(v), parse_t(hrs[i]["t"]).astimezone(zone)
    spec_get = {lab: get for lab, get, sc, f in spec}
    bits = []
    if col.get("Temp &deg;F"):
        bits.append("%.0f to %.0f&deg;F" % (min(col["Temp &deg;F"]), max(col["Temp &deg;F"])))
    gp = peak("Gust mph") or peak("Wind mph")
    if gp:
        bits.append("%s to %.0f mph (%s)" % ("gusts" if col.get("Gust mph") else "wind", gp[0], "%d %s" % (gp[1].hour % 12 or 12, "AM" if gp[1].hour < 12 else "PM")))
    if col.get("Rain/snow %"):
        rp = peak("Rain/snow %")
        bits.append("rain or snow chance up to %.0f%%%s" % (rp[0], (" (%d %s)" % (rp[1].hour % 12 or 12, "AM" if rp[1].hour < 12 else "PM")) if rp[0] >= 10 else ""))
    if col.get("Thunder %") and max(col["Thunder %"]) >= 1:  # "thunder up to 0%" said nothing (Boise, 2026-10-29)
        bits.append("thunder up to %.0f%%" % max(col["Thunder %"]))
    summary = ('<p class="lead">Next 24 h: %s.</p>' % " &middot; ".join(bits)) if bits else ""
    every3 = [hrs[i:i + 3] for i in range(0, len(hrs), 3)]
    upd = esc(tzl(parse_t(g["updated"]), zone)) if g.get("updated") else "time not stated"
    hp = [v for v in (pop.get(parse_t(h["t"]).replace(minute=0, second=0, microsecond=0)) for h in hrs) if v is not None]
    per = [p for p in n.get("periods") or [] if p.get("pop") is not None and parse_t(p["startTime"]) <= parse_t(hrs[-1]["t"]) - datetime.timedelta(hours=6) and parse_t(p.get("endTime") or p["startTime"]) > max(G["now"], parse_t(hrs[0]["t"])) + datetime.timedelta(hours=6)]  # full review: "Tonight" from a 17 h old forecast
    big = max(per, key=lambda p: p["pop"]) if per else None
    popnote = ('<p class="src">The NWS gives %s a %d%% chance of rain or snow for the whole period; the highest single hour below is %d%%. A period chance counts rain or snow at any time in it, so it runs higher than any one hour.</p>' % (esc(big["name"]), big["pop"], max(hp))) if big and hp and big["pop"] > max(hp) + 15 else ""  # hater r5: "Tonight 93%" over hourly cells that peak at 69
    grid = lambda gs, q: '<div class="scroll"><table class="hm"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (head_of([g_[0] for g_ in gs]), rows_of(gs, q))
    def gmax(lab, grp):
        v = [x for x in (spec_get[lab](h) for h in grp) if x is not None]
        return max(v) if v else None
    has_t = bool(col.get("Thunder %")) and max(col["Thunder %"]) >= 1
    has_v = bool(col.get("Visibility mi")) and min(col["Visibility mi"]) < 5
    has_r = bool(col.get("Rain/snow %"))
    sky_of = lambda grp: sky.get(parse_t(grp[0]["t"]).replace(minute=0, second=0, microsecond=0))
    has_s = any(sky_of(grp) for grp in every3)  # old caches without the NWS short forecast: no Sky column
    heads = ["Time", "Temp"] + (["Rain %"] if has_r else []) + ["Wind mph", "Gusts mph"] + (["Thunder %"] if has_t else []) + (["Visibility"] if has_v else []) + (["Sky"] if has_s else [])
    lrows = ""
    for grp in every3:
        d = parse_t(grp[0]["t"]).astimezone(zone)
        t0 = spec_get["Temp &deg;F"](grp[0])
        w, g_, dr = gmax("Wind mph", grp), gmax("Gust mph", grp), spec_get["Direction"](grp[0])
        cells = ["%s%d %s" % (("%s " % d.strftime("%a")) if (d.hour < 3 or grp is every3[0]) else "", d.hour % 12 or 12, "AM" if d.hour < 12 else "PM"),
                 ("%.0f&deg;F" % t0) if t0 is not None else "&ndash;"]
        if has_r:
            r_ = gmax("Rain/snow %", grp)
            cells.append(("%.0f" % r_) if r_ is not None else "&ndash;")
        cells += [(("%s " % wind_arrow(dr)) if dr is not None else "") + (("%.0f" % w) if w is not None else "&ndash;"), ("%.0f" % g_) if g_ is not None else "&ndash;"]
        if has_t:
            th = gmax("Thunder %", grp)
            cells.append(("%.0f" % th) if th else "")
        if has_v:
            vv = [x for x in (spec_get["Visibility mi"](h) for h in grp) if x is not None]
            cells.append(("%.1f mi" % min(vv)) if vv else "&ndash;")
        if has_s:
            cells.append(esc(sky_of(grp) or "") or "&ndash;")
        lrows += tr(cells, right=tuple(range(1, len(cells) - has_s)))
    lst = '<div class="scroll"><table class="hm hlist%s"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (" hsky" if has_s else "", "".join("<th>%s</th>" % h_ for h_ in heads), lrows)  # .hm never stacks into cards on a phone: one line per 3 hours
    return block("hourly_heatmap", "Hourly forecast, next 24 hours", "official", storm_line(G) + summary + popnote + lst + more("Every hour, every NWS value", grid([[h] for h in hrs], set())),
                 "Source: National Weather Service gridpoint forecast, updated %s; chance of rain or snow from the NWS hourly point forecast. Amounts are liquid water, the NWS 6-hour totals spread evenly over each hour. A day or night forecast chance covers the whole period, so it can be higher than any single hour. Hours are gauge-local; each row covers 3 hours (temperature at its first hour; wind, gusts, rain and thunder the highest in the 3 hours; visibility the lowest; sky is the NWS hourly short forecast for the first hour; the arrow points where the wind blows), and every hour is one tap below. Darker cells mean a higher value in that row." % upd, "nws", amber=age)
