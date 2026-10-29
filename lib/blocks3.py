"""Blocks for the second wave of government sources (NWS forecast point facts, FEMA declarations, NCEI storm events, dams, Reclamation releases, ACIS rain, StreamCat, FEMA flood zones).
Same registry rules as render.py and blocks2.py. Each block is gated by its source row in data/sources.json.
"""
import collections, datetime, re
from lib.render import *  # block, table, tr, esc, fmt, tzl, parse_t, fdate, SOURCES, ...



def b_nws_point(G, pages=None):
    n = G["rec"].get("nwps") or {}
    if not n.get("lid"):
        return None
    rows = tr(["Forecast point", "%s, %s" % (esc(n["lid"]), esc(n.get("name") or ""))])
    nm = lambda x: ("%s (%s)" % (x.get("name"), x.get("abbreviation")) if x.get("name") and x.get("abbreviation") else (x.get("abbreviation") or x.get("name") or "")) if isinstance(x, dict) else (x or "")
    if n.get("wfo"):
        rows += tr(["Weather Forecast Office", esc(nm(n["wfo"]))])
    if n.get("rfc"):
        rows += tr(["River Forecast Center", esc(nm(n["rfc"]))])
    if n.get("reliability") and (n.get("forecast") or {}).get("points"):
        rows += tr(["Forecast reliability, as published", esc(n["reliability"])])
    rows += tr(["Flood inundation maps", '<a href="https://water.noaa.gov/gauges/%s" rel="noopener">Check this forecast point at water.noaa.gov</a>' % esc(n["lid"])])
    for key, lab in (("upstream", "Upstream forecast points"), ("downstream", "Downstream forecast points")):
        rfl = n.get("riverflow") or {}
        on_site = {(p.get("nws_lid") or "").upper(): p for p in (pages or {}).values() if p.get("_built") and p.get("nws_lid")}

        def nm_link(x):
            nm = esc(re.sub(r"\s*\(IN MLLW\)", "", x.get("Name") or x.get("LID") or "", flags=re.I))
            p = on_site.get((x.get("LID") or "").upper())
            return '<a href="%s">%s</a>' % (p["water_url"], nm) if p else nm
        raw_ = [x for x in (rfl.get(key) or []) if isinstance(x, dict)]
        nm_list = [x for i, x in enumerate(raw_) if (x.get("LID") or x.get("Name")) not in [(y.get("LID") or y.get("Name")) for y in raw_[:i]]]  # hater w5, Boise: two points listed three times each
        if nm_list:
            total = (rfl.get(key + "_n") or len(nm_list)) if len(nm_list) == len(raw_) else len(nm_list)
            if key == "upstream":  # stored farthest first: list nearest first
                nm_list = nm_list[::-1]
            if total > len(nm_list):
                lab = "%s (nearest %d of %d)" % (lab, len(nm_list), total)
            rows += tr([lab, "<br>".join(nm_link(x) for x in nm_list)])  # one point per line (hater 2026-10-27: a "; " wrapped to the start of a phone line after a link)
    return block("nws_forecast_point", "National Weather Service forecast point", "official", table(["Item", "Value"], rows),
                 "Source: National Weather Service National Water Prediction Service, forecast point %s, fetched %s." % (esc(n["lid"]), esc(tzl(parse_t(n["fetched_at"]), G["zone"]))), "nwps")


def sustained_pct(G, days):
    """Average percentile of the last N daily mean flows vs USGS daily statistics for those dates: 'has flow sat low/normal/high over the week/month', for irrigators and anglers."""
    rec = G["rec"]
    stats, m = rec.get("stats"), rec.get("multiyear") or {}
    if not stats or not m.get("as_of"):
        return None
    as_of = datetime.date.fromisoformat(m["as_of"])
    ser = (m.get("series") or {}).get(str(as_of.year)) or []
    if len(ser) < days:
        return None
    pcts = []
    for i in range(1, days + 1):
        v = ser[-i]
        if v is None:
            continue
        srow = stats.get((as_of - datetime.timedelta(days=i - 1)).isoformat()[5:10])
        if srow:
            p = interp_pct(srow, v)
            if p is not None:
                pcts.append(max(0, min(100, p)))  # interp_pct returns -1/101 sentinels for below/above all published percentiles; clamp so the averaged percentile never prints as "-1th"/"101st"
    return round(sum(pcts) / len(pcts)) if len(pcts) >= max(3, days - 3) else None


def b_sustained(G):
    p7, p28 = sustained_pct(G, 7), sustained_pct(G, 28)
    if p7 is None and p28 is None:
        return None
    def band(p):  # the headline's USGS WaterWatch bands, so the two never disagree (hater 2026-10-27)
        return PCT_PHRASE[band_word(p)]
    def ordp(p):
        suf = "th" if 10 <= p % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(p % 10, "th")
        return "%d%s percentile" % (p, suf)
    parts = []
    if p7 is not None:
        parts.append("Past 7 days: %s, %s" % (ordp(p7), band(p7)))
    if p28 is not None:
        parts.append("Past 28 days: %s, %s" % (ordp(p28), band(p28)))
    return block("sustained_flow", "Flow over recent weeks", "hist", "<p>%s</p>" % " &middot; ".join(parts) + '<p class="src">Each day is placed among past years for that date and the placings are averaged. The month-to-date rank below instead compares this month\'s mean flow with each year\'s mean for the same dates, so the two can land in different bands.</p>',
                 "Source: USGS daily mean flow for each date through %s compared with USGS daily statistics for those same dates; the percentile shown is the average of the daily percentiles over the window." % esc(fdate(G["rec"]["multiyear"]["as_of"])), "usgs")


def b_access(G):
    """Boat ramps, put-ins and marinas near the gauge (OpenStreetMap). Where people get on the water."""
    a = G["rec"].get("access")
    if not a or not a.get("rows"):
        return None
    pri = {"Boat ramp": 0, "Whitewater put-in": 0, "Canoe/kayak put-in": 0, "Marina": 1}  # actual launch points before marinas, nearest first
    ordered = sorted(a["rows"], key=lambda x: (pri.get(x["type"], 2), x["mi"]))
    rows = "".join(tr([esc(x["name"] or "(unnamed)"), esc(x["type"]), "%.1f mi" % x["mi"]], right=(2,)) for x in ordered)
    return block("access_points", "Boat ramps, put-ins and marinas nearby", "map",
                 table(["Name", "Type", "Distance"], rows, right=(2,)),
                 "Source: OpenStreetMap (boat ramps, canoe and whitewater put-ins, marinas) within about 15 miles of the gauge, %d found, nearest shown, fetched %s. © OpenStreetMap contributors, ODbL. Positions are community-mapped and may be approximate." % (a["count"], esc(tzl(parse_t(a["fetched_at"]), G["zone"]))), "osm")



def _on_river(water, river):
    """True when a stocked water is this river: its name carries the river's own name and is not a pond, lake or reservoir."""
    import re as _re
    key = _re.sub(r"(?i)\b(river|creek|fork|north|south|east|west|middle|branch|the)\b", " ", river).split()
    return bool(key) and all(k.lower() in water.lower() for k in key) and not _re.search(r"(?i)\b(pond|lake|reservoir|res\.?)\b", water)


def b_stocking(G):
    """Recent hatchery stocking near the gauge (species, date, count, water), from the state's public stocking layer. Hidden where the state has no adapter or no recent record."""
    s = G["rec"].get("stocking")
    if not s or not s.get("rows"):
        return None
    # hater 2026-10-27: ponds and lakes 14-35 mi away, 2025 rows under "Recent", "6.0" fish, duplicate rows. A pond release has no link
    # to this river (no mechanism): keep flowing waters only, the last 12 months, one row per water, date and species, whole fish.
    import re as _re
    cut = (G["now"] - datetime.timedelta(days=365)).date().isoformat()
    seen, keep = set(), []
    for x in s["rows"]:
        k = (x.get("date"), (x.get("species") or "").strip().lower(), (x.get("water") or "").strip().lower())
        if k in seen or str(x.get("date") or "") < cut or not _on_river(x.get("water") or "", G["river"]):
            continue
        seen.add(k)
        keep.append(x)
    if not keep:
        return None
    rows = "".join(tr([fdate(x["date"]), esc(re.sub(r"\((?=\S)", " (", x["species"] or "–")), fmt(round(x["num"])) if x.get("num") else "–", esc(x["water"] or "–"),
                       ("%.1f mi" % x["mi"]) if x.get("mi") is not None else "–"], right=(2, 4)) for x in keep)
    return block("stocking", "Recent fish stocking nearby", "hist",
                 table(["Date", "Species", "Number", "Water", "Distance"], rows, right=(2, 4)),
                 "Source: %s, hatchery stocking records within about %d miles of the gauge, most recent first, fetched %s. Credit: %s. Stocking is a release event, not a measure of fish now present in the river." % (
                     esc(s["source"]), s.get("miles", 35), esc(tzl(parse_t(s["fetched_at"]), G["zone"])), esc(s["credit"])), "stocking")


def acis_name(n):
    """ACIS station names arrive in capitals: title-case the place, keep the compass suffix ("CHEVY CHASE 1.2 SW" -> "Chevy Chase 1.2 SW")."""
    import re
    t = re.sub(r"\bAp\b", "Airport", (n or "").title())
    return re.sub(r"\b(\d+(?:\.\d+)?) ([NSEW]{1,3})\b", lambda m: m.group(1) + " " + m.group(2).upper(), t, flags=re.I)


def b_acis(G):
    a = G["rec"].get("acis")
    if not a or not a.get("stations"):
        return None
    heads = ["Station", "Distance"] + [datetime.date.fromisoformat(d).strftime("%b %d").replace(" 0", " ") for d in a["days"]]
    cell = lambda v: (lambda w: "not reported" if w in ("M", "S", "A") else ("trace" if w == "T" else "%s in" % w if w.replace(".", "", 1).isdigit() else esc(w)))(v.rstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ") if v[:1].isdigit() else v)  # a trailing ACIS flag letter ("0.00A") is a source code, not part of the value
    _seen = set()
    a = dict(a, stations=[x for x in a["stations"] if not ((acis_name(x["name"]), round(x["km"], 1)) in _seen or _seen.add((acis_name(x["name"]), round(x["km"], 1))))])  # full review: one station twice, 0.00 vs trace
    _nm = collections.Counter(acis_name(x["name"]) for x in a["stations"])
    rows = "".join(tr([esc(acis_name(x["name"]) + ((" (%s)" % (x.get("sid") or x.get("id") or "%.1f mi" % km_mi(x["km"]))) if _nm[acis_name(x["name"])] > 1 else "")), "%.0f mi" % km_mi(x["km"])] + [cell(v) for v in x["vals"]], right=tuple(range(1, 9))) for x in a["stations"])
    return block("county_station_rain", "Measured daily rain at nearby weather stations", "obs", ('<p class="src">Each date is one station observation day, which often ends in the morning, so it does not line up with the rain totals for the gauge location above.</p>' if (G["rec"].get("rain") or {}).get("inches") else "") + table(heads, rows, right=tuple(range(1, 9))),
                 "Source: NOAA Regional Climate Centers ACIS, daily precipitation at the nearest county weather stations, fetched %s. Each value is a 24-hour total for the station's observation day; trace means less than 0.01 in. Where ACIS lists two reports for one station, the first is shown." % esc(tzl(parse_t(a["fetched_at"]), G["zone"])), "acis")


def b_streamcat(G):
    s = G["rec"].get("streamcat")
    if not s or not s.get("vals"):
        return None
    v = s["vals"]
    spec = (("pctimp2019ws", "Impervious surface, 2019", lambda x: "%.1f%%" % x), ("pcturbmd2019ws", "Medium-intensity urban land, 2019", lambda x: "%.1f%%" % x), ("pctcrop2019ws", "Cropland, 2019", lambda x: "%.1f%%" % x),
            ("pctwdwet2019ws", "Woody wetland, 2019", lambda x: "%.1f%%" % x), ("elevws", "Mean elevation", lambda x: "%s ft" % fmt(x * 3.28084)), ("precip8110ws", "Mean annual precipitation, 1981 to 2010", lambda x: "%.1f in" % (x / 25.4)),
            ("runoffws", "Mean annual runoff", lambda x: "%.1f in" % (x / 25.4)), ("bfiws", "Base-flow index", lambda x: "%.0f%%" % x), ("damdensws", "Dam density", lambda x: "%.3f per sq mi" % (x * 2.58999)))
    rows = "".join(tr([lab, f(v[k])], right=(1,)) for k, lab, f in spec if k in v)
    from lib import ui
    pc = [(l, k) for k, l in (("pctimp2019ws", "Impervious surface, 2019"), ("pcturbmd2019ws", "Medium-intensity urban land, 2019"), ("pctcrop2019ws", "Cropland, 2019"), ("pctwdwet2019ws", "Woody wetland, 2019"), ("bfiws", "Base-flow index (share of streamflow from groundwater)")) if k in v]
    wid = ui.bars([(l, v[k], "%.1f%%" % v[k]) for l, k in pc], 100) if pc else ""
    ch = ui.chips([(l, f(v[k])) for k, l, f in spec if k in ("elevws", "precip8110ws", "runoffws", "damdensws") and k in v])
    return block("watershed_characteristics", "Upstream watershed characteristics", "agency", wid + ch,
                 "Source: U.S. EPA StreamCat ), watershed-wide metrics; land cover from the 2019 National Land Cover Database. Static values, fetched %s." % (esc(tzl(parse_t(s["fetched_at"]), G["zone"]))), "epa")


def _year_svg(rows, stats, W, Hh, fs, nx, cls, xfmt="%b %Y", period="12 months"):
    L, B = (56, 30) if W > 500 else (46, 28)
    D = datetime.date.fromisoformat
    d0, d1 = D(rows[0][0]), D(rows[-1][0])
    span = max((d1 - d0).days, 1)
    vals = [v for _, v in rows]
    band = []
    if stats:
        for i in range(span + 1):
            r_ = stats.get((d0 + datetime.timedelta(days=i)).isoformat()[5:10])
            if r_ and r_[4] is not None and r_[6] is not None and r_[5] is not None:
                band.append((i, r_[4], r_[6], r_[5]))
        for _, a, c, _m in band:
            vals += [a, c]
    vmin, vmax, ticks = nice_ticks(min(vals), max(vals))
    X = lambda i: L + i / span * (W - L - 14)
    Y = lambda v: 12 + (1 - (v - vmin) / ((vmax - vmin) or 1)) * (Hh - B - 12)
    grid = "".join('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--line)"/><text x="%d" y="%.1f" font-size="%d" fill="var(--mut)" text-anchor="end">%s</text>' % (L, W - 14, Y(tv), Y(tv), L - 6, Y(tv) + 4, fs, tf(tv, ticks)) for tv in ticks)
    xl = ""
    for k in range(nx):
        i = round(span * k / (nx - 1))
        xl += '<text x="%.1f" y="%d" font-size="%d" fill="var(--mut)" text-anchor="%s">%s</text>' % (X(i), Hh - 8, fs, "start" if k == 0 else "end" if k == nx - 1 else "middle", (d0 + datetime.timedelta(days=i)).strftime(xfmt).replace(" 0", " "))
    shape = ""
    if band:
        up = " ".join("%.1f,%.1f" % (X(i), Y(c)) for i, a, c, m in band)
        dn = " ".join("%.1f,%.1f" % (X(i), Y(a)) for i, a, c, m in reversed(band))
        md = " ".join("%.1f,%.1f" % (X(i), Y(m)) for i, a, c, m in band)
        shape = '<polygon points="%s %s" fill="var(--soft)"/><polyline points="%s" fill="none" stroke="var(--mut)" stroke-dasharray="4 4"/>' % (up, dn, md)
    segs, cur, prev = [], [], None
    for ds, v in rows:
        i = (D(ds) - d0).days
        if prev is not None and i - prev > 3:
            segs.append(cur)
            cur = []
        cur.append("%.1f,%.1f" % (X(i), Y(v)))
        prev = i
    segs.append(cur)
    line = "".join('<polyline points="%s" fill="none" stroke="var(--accent)" stroke-width="1.8"/>' % " ".join(s) for s in segs if len(s) > 1)
    return '<svg class="%s" viewBox="0 0 %d %d" width="100%%" role="img" aria-label="Daily mean flow in cfs over the last %s with the 25th to 75th percentile band for each date">%s%s%s%s</svg>' % (cls, W, Hh, period, shape, grid, xl, line)


def b_month_chart(G):
    y = G["rec"].get("year")
    rows = (y or {}).get("rows") or []
    if len(rows) < 300 or (G["ldate"] - datetime.date.fromisoformat(rows[-1][0])).days > 10:
        return None
    last = rows[-30:]
    if (datetime.date.fromisoformat(last[-1][0]) - datetime.date.fromisoformat(last[0][0])).days < 20:
        return None
    svg = _year_svg(last, G["stats"], 760, 250, 11, 5, "cw", "%b %d", "30 days") + _year_svg(last, G["stats"], 340, 250, 12, 3, "cn", "%b %d", "30 days")
    return block("month_chart", "Last 30 days", "hist", svg + (LEG if G["rec"].get("stats") else ""),
                 "Source: USGS daily mean flows (Water Data API), %s to %s. Shaded band: 25th to 75th percentile of USGS daily statistics for each date; dashed: median. Gaps are days without a published value; recent days are provisional. Flow in cfs." % (esc(fdate(last[0][0])), esc(fdate(last[-1][0]))), "usgs")


def b_year_chart(G):
    y = G["rec"].get("year")
    if not y or len(y.get("rows") or []) < 300:
        return None
    if (G["ldate"] - datetime.date.fromisoformat(y["rows"][-1][0])).days > 10:
        return None
    svg = _year_svg(y["rows"], G["stats"], 760, 250, 11, 5, "cw") + _year_svg(y["rows"], G["stats"], 340, 250, 12, 3, "cn")
    return block("year_chart", "Last 12 months", "hist", svg,
                 "Source: USGS daily mean flows (Water Data API), %s to %s. Shaded band: 25th to 75th percentile of USGS daily statistics for each date; dashed: median. Gaps are days without a published value; recent days are provisional." % (fdate(y["rows"][0][0]), fdate(y["rows"][-1][0])), "usgs")


def b_field_meas(G):
    f = G["rec"].get("fieldmeas")
    if not f or not f.get("rows"):
        return None
    rows = "".join(tr([fdate(r["t"][:10]), "%s cfs" % fmtc(r["flow"]), ("%.2f ft" % r["stage"]) if r.get("stage") is not None else "–", esc(r.get("rating") or "–")], right=(1, 2)) for r in f["rows"][:10])
    return block("field_measurements", "USGS field measurements", "hist", table(["Date", "Measured flow", "Gage height", "Rated"], rows, right=(1, 2)),
                 "Source: USGS Water Data API field measurements, the %d most recent site-visit measurements with a flow value, fetched %s. The rating shown is the USGS measurement rating as published." % (min(10, len(f["rows"])), esc(tzl(parse_t(f["fetched_at"]), G["zone"]))), "usgs")


def window_change(fl, lt, h):
    """Flow change over h hours: the latest reading against the reading closest to h hours earlier (within 20 minutes or 60% of the reporting interval), exactly what the rate table shows and what anyone can read off USGS. Returns (latest, earlier, percent) or None.
    A noisy gauge is not smoothed here: it is recognised (flow_jitter in lib/render.py, or the gage height contradicting the flow) and the headline says so. The headline tile, the rate table and the home and hub tables all use this."""
    if len(fl) < 2:
        return None
    steps = sorted((fl[i][0] - fl[i - 1][0]).total_seconds() for i in range(max(1, len(fl) - 200), len(fl)))
    tol = max(1200, 0.6 * (steps[len(steps) // 2] if steps else 900))
    tgt = lt - datetime.timedelta(hours=h)
    near = min(fl, key=lambda x: abs((x[0] - tgt).total_seconds()))
    if abs((near[0] - tgt).total_seconds()) > tol or not near[1] or near[1] <= 0:
        return None
    return fl[-1][1], near[1], (fl[-1][1] - near[1]) / near[1] * 100


def _fc_offset(G, pts, unit, gap):
    """The forecast point nearest the latest reading, compared with that reading: a forecast that is hours out of step with the gauge (dam releases, tide) must say so. None when they agree."""
    if not pts or (unit == "ft" and gap):
        return None
    t0 = G["lt"]
    near = min(pts, key=lambda x: abs((x[0] - t0).total_seconds()))
    if abs((near[0] - t0).total_seconds()) > FC_NEAR_S:
        return None
    if unit == "ft":
        if not near[1] or not G["sg"] or (G["sg"][-1][2].get("unit_of_measure") or "").lower() not in ("ft", "feet"):
            return None
        cur, fv = G["sg"][-1][1], near[1]
        if abs(cur - fv) <= max(0.5, 0.05 * abs(cur)):
            return None
        return {"t": tzl(near[0], G["zone"], date=False), "f": "%.1f ft" % fv, "c": "%.2f ft" % cur}
    cur, fv = G["lv"], near[2]
    if not fv or abs(cur - fv) <= FC_OFF_REL * max(cur, fv):
        return None
    return {"t": tzl(near[0], G["zone"], date=False), "f": "%s cfs" % fmtc(fv), "c": "%s cfs" % fmtc(cur)}


def conditions(G, pages=None):
    """Current conditions beyond flow and stage that the stat tiles show: change over 1, 6 and 24 h, forecast high, alert names, rain, each with its source time. Missing values are simply absent."""
    from lib.blocks2 import _at
    zone, fl, lt, lv, rec = G["zone"], G["fl"], G["lt"], G["lv"], G["rec"]
    ok = lambda sid: SOURCES[sid]["status"] in ("quoted", "owner-permission")
    out = {"chg": {}, "fc": None, "alerts": None, "rain": None, "wt": None, "air": None, "up": None}
    wts = series(rec, "00010")
    if wts and (G["now"] - wts[-1][0]).total_seconds() <= 24 * 3600 and (wts[-1][2].get("unit_of_measure") or "").lower().replace(" ", "") in ("degc", "°c"):
        out["wt"] = {"f": wts[-1][1] * 9 / 5 + 32, "t": tzl(wts[-1][0], zone)}
    ob = (rec.get("nws") or {}).get("obs")
    if ob and ok("nws") and ob.get("temp_c") is not None and hours_old(ob.get("timestamp"), G["now"]) is not None and hours_old(ob.get("timestamp"), G["now"]) <= HIDE_H["air_obs"]:
        wk = ob.get("wind_kmh")
        dirs = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")
        wd = dirs[int((ob["wind_dir"] % 360) / 22.5 + 0.5) % 16] if ob.get("wind_dir") is not None else ""
        out["air"] = {"f": ob["temp_c"] * 9 / 5 + 32, "wind": km_mi(wk) if wk is not None else None, "gust": km_mi(ob["gust_kmh"]) if ob.get("gust_kmh") is not None else None, "dir": wd, "st": ob.get("station") or "", "name": ob.get("name") or "", "mi": round(miles_between(G["lat"], G["lon"], ob["ll"][1], ob["ll"][0])) if ob.get("ll") else None, "t": tzl(parse_t(ob["timestamp"]), zone), "iso": ob["timestamp"]}
    if pages:
        for x in ((rec.get("related") or {}).get("items") or []):
            pr = pages.get(x["site"])
            if x.get("relation") == "upstream" and pr and pr.get("_built") and x.get("flow") is not None and x.get("time") and (hours_old(x["time"], G["now"]) or 1e9) <= 24:
                out["up"] = {"flow": x["flow"], "name": river_at(pr["river"], pr["place"]), "url": pr["water_url"], "lag": x.get("lag_h"), "time": tzl(parse_t(x["time"]), zone) if x.get("time") else ""}
                break
    if len(fl) >= 8 and not G.get("osc"):
        for h in (1, 3, 6, 24):
            wc = window_change(fl, lt, h)
            if wc:
                out["chg"][h] = wc[2]
    sgl = G["sg"]
    out["sg6"] = None
    if len(sgl) >= 8 and (sgl[-1][2].get("unit_of_measure") or "").lower() in ("ft", "feet"):
        a6 = _at(sgl, sgl[-1][0] - datetime.timedelta(hours=6), 1800)
        out["sg6"] = (sgl[-1][1] - a6[1]) if a6 else None
    n = rec.get("nwps") or {}
    f = n.get("forecast") if ok("nwps") else None
    if f and f.get("points"):
        age = hours_old(f.get("issued"), G["now"]) if f.get("issued") else None
        pts = [x for x in fc_points(f) if x[0] >= G["now"]]
        stage = [(t_, s_) for t_, s_, _ in pts if s_ is not None]
        flow = [(t_, f_) for t_, _, f_ in pts if f_ is not None]
        gap = datum_gap(G)
        fut, unit = (stage, "ft") if stage else (flow, "cfs")
        if fut and (age is None or age <= HIDE_H["river_forecast"]):
            hi = max(fut, key=lambda x: x[1])
            near = [i for i, (_, v_) in enumerate(fut) if v_ >= hi[1] - (0.05 if unit == "ft" else 0.01 * abs(hi[1]))]
            lo_f = min(v_ for _, v_ in fut)
            depth = max(0.15 if unit == "ft" else 0.03 * abs(hi[1]), 0.25 * (hi[1] - lo_f))  # a second peak needs a valley at least a quarter as deep as the whole rise, not a wobble on a plateau
            peaks = 1 + sum(1 for a_, b_ in zip(near, near[1:]) if min(v_ for _, v_ in fut[a_:b_ + 1]) < hi[1] - depth)
            end = fut[-1]
            first_hi = near[0]
            out["fc"] = {"v": hi[1], "unit": unit, "t": tzl(hi[0], zone), "lid": n.get("lid") or "", "repeat": peaks >= 2, "issued": tzl(parse_t(f["issued"]), zone) if f.get("issued") else "at a time not stated",
                         "falls": end[1] <= hi[1] - (0.5 if unit == "ft" else 0.1 * abs(hi[1])) and (end[0] - hi[0]).total_seconds() > 6 * 3600 and peaks < 2, "end_v": end[1], "end_t": tzl(end[0], zone),
                         "swing": (lo_f, tzl(end[0], zone)) if peaks >= 2 and hi[1] - lo_f >= (0.5 if unit == "ft" else 0.1 * abs(hi[1])) else None,
                         "datum": gap, "word": fc_word([v_ for _, v_ in fut], __import__("lib.hero", fromlist=["fc_cur"]).fc_cur(G, gap) if unit == "ft" else G["lv"], unit),
                         "flow_at": next((x[2] for x in pts if x[0] == hi[0]), None) if unit == "ft" else None,
                         "offset": _fc_offset(G, pts, unit, gap),
                         "cur": (gap[0] if gap else (G["sg"][-1][1] if G["sg"] and (G["sg"][-1][2].get("unit_of_measure") or "").lower() in ("ft", "feet") else None)) if unit == "ft" else G["lv"]}
    nws = rec.get("nws") or {}
    if ok("nws") and nws.get("alerts") is not None and nws.get("fetched_at"):
        al = live_alerts(G) or []
        out["alerts"] = {"n": len(al), "names": [x.get("event") or "" for x in al[:3]], "age_h": hours_old(nws["fetched_at"], G["now"]), "asof": tzl(parse_t(nws["fetched_at"]), zone)}
    rn = rec.get("rain") or {}
    if ok("rfc") and (rn.get("inches") or {}).get("last_24h") is not None:
        vt = (rn.get("valid_through") or {}).get("last_24h")
        out["rain"] = {"in": rn["inches"]["last_24h"], "to": tzl(parse_t(vt), zone) if vt else None}
    return out



def b_camera(G):
    """USGS gaging-station camera at this site: the newest image (720 px), with the timelapse link and the HIVIS page."""
    c = G["rec"].get("cameras")
    if not c or not c.get("cams"):
        return None
    body, ages = "", []
    for x in c["cams"]:
        try:
            h = hours_old(x["taken"], G["now"])
            taken = tzl(parse_t(x["taken"]), G["zone"]) + (" (%s before this page was built)" % human_span(int(h // 24)) if h > 24 else "")
            ages.append(h)
        except (KeyError, TypeError, ValueError):
            taken = "time not stated"
        body += '<figure class="cam"><a href="%s" rel="noopener"><img src="%s" alt="USGS camera: %s" width="720" height="405" loading="lazy" style="max-width:100%%;height:auto"></a><figcaption>%s &middot; taken %s%s</figcaption></figure>' % (
            esc(x["page"]), esc(x["small"]), esc(x["name"]), esc(x["name"]), esc(taken), (' &middot; <a href="%s" rel="noopener">timelapse video</a>' % esc(x["timelapse"])) if x.get("timelapse") else "")
    fresh = len(ages) == len(c["cams"]) and all(h <= stale_after("camera") for h in ages)
    return block("camera", "Camera at the gauge" if fresh else "Camera at the gauge, newest image", "live" if fresh else "agency", body,
                 "Source: U.S. Geological Survey HIVIS camera (NIMS API), newest image at build time; the image file is served by USGS. Fetched %s." % esc(tzl(parse_t(c["fetched_at"]), G["zone"])), "hivis")


def _aq_site(s):
    return "not stated" if not s or s.strip().upper() in ("NEW", "N/A") else s


def _aq_where(r):
    s = _aq_site(r.get("site"))
    if r.get("county") and not re.search("[a-z]", s):  # an all-capitals site code is no place name
        s = "monitor in " + r["county"]
    if "id" not in r:  # cache from before the distance was fetched
        return s
    if not r["id"]:
        return s + " (AirNow reporting area; no single monitor named)"
    return s + ((", %d mi from the gauge" % r["mi"]) if r.get("mi") is not None else ", distance not published")


def _aq_time(r):
    if not r.get("date") or not r.get("hour"):
        return "time not stated"
    try:
        d = datetime.datetime.strptime("%s %s" % (r.get("date"), r.get("hour")), "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return "%s %s %s" % (r.get("date") or "", r.get("hour") or "", r.get("tz") or "")
    return ("%s %s" % (d.strftime("%b %d, %I:%M %p").replace(" 0", " ").replace(", 0", ", "), r.get("tz") or "")).strip()


def b_air_quality(G):
    """EPA AirNow NowCast AQI per pollutant at the nearest reporting site: the air a person breathes on the water today."""
    a = G["rec"].get("airnow")
    if not a or not a.get("rows"):
        return None
    def _fresh(r):
        try:
            d = datetime.datetime.strptime("%s %s" % (r.get("date"), r.get("hour")), "%Y-%m-%d %H:%M").replace(tzinfo=G["zone"])
        except (TypeError, ValueError):
            return True
        return (G["now"] - d).total_seconds() <= HIDE_H["air_quality"] * 3600
    a = dict(a, rows=[r for r in a["rows"] if _fresh(r) and isinstance(r.get("aqi"), (int, float))])  # full review: "Air quality now" from a reading 26 h old
    if not a["rows"]:
        return None
    a = dict(a, rows=[dict(r, site=r.get("site") if _aq_site(r.get("site")) != "not stated" else r.get("area")) for r in a["rows"]])  # hater r4: "MONITOR not stated" while AirNow names the reporting area
    rows = "".join(tr([esc(("PM2.5" if r["pollutant"] == "PM2.5" else (r["pollutant"] or "").title()) if r["pollutant"] not in ("OZONE", "PM10") else r["pollutant"].replace("OZONE", "Ozone")), str(r["aqi"]), esc(r["category"] or ""), esc(_aq_where(r)), esc(_aq_time(r))], right=(1,)) for r in a["rows"])
    worst = max(a["rows"], key=lambda r: r["aqi"] or 0)
    return block("air_quality", "Air quality now", "epa", '<p class="aq">AQI %s, %s (%s)%s</p>' % (esc(str(worst["aqi"])), esc(worst["category"] or ""), esc(worst["pollutant"] or ""), (", at " + esc(_aq_where(worst))) if _aq_site(worst.get("site")) != "not stated" else "") + table(["Pollutant", "Air quality index (NowCast)", "Category", "Monitor", "Observed"], rows, right=(1,)),
                 "Source: EPA AirNow, reporting agency %s, nearest monitor to the gauge; preliminary data, subject to change. Fetched %s." % (esc(worst.get("agency") or "not stated"), esc(tzl(parse_t(a["fetched_at"]), G["zone"]))), "airnow")


def _ridb_name(n):
    return re.sub(r"\(([A-Za-z]{2})\)$", lambda m: "(" + m.group(1).upper() + ")", n.title()) if n.isupper() else n



def _phone(p):
    """One format for a US number ("1(406) 683-8000", "406-683-8000" are one line); anything else as listed."""
    m = re.search(r"\(?\d{3}\)?[\s.-]*\d{3}[\s.-]*\d{4}", p or "")
    d = re.sub(r"\D", "", m.group(0) if m else (p or ""))  # full review: "FOR RESERVATIONS, PLEASE CALL: 1 (877) 444-6777." on 9 cards
    d = d[1:] if len(d) == 11 and d[0] == "1" else d
    return "(%s) %s-%s" % (d[:3], d[3:6], d[6:]) if len(d) == 10 else (p or "").strip()


def b_recreation(G):
    """Recreation.gov facilities within 15 mi that list a water activity, are campgrounds, or are ramps: where a person gets on or stays by this river."""
    r = G["rec"].get("ridb")
    if not r or not r.get("sites"):
        return None
    seen, sites = set(), []
    for x in r["sites"]:  # the same site listed twice by RIDB shows once (hater 2026-10-27, Ocoee)
        k = _ridb_name(x["name"]).lower()
        if k not in seen and not any("Privately Owned" in a and "Hotel" in a for a in x.get("activities") or []):  # hater r4: "The Peabody Memphis ... Swimming"
            seen.add(k)
            sites.append(x)
    r = dict(r, sites=sites)
    r = dict(r, sites=[dict(x, phone=_phone(x.get("phone")), type=("Day-use area" if x.get("type") == "Campground" and re.search(r"(?i)picnic|day use|pavilion|shelter", x["name"]) else x.get("type"))) for x in r["sites"]])
    if not r["sites"]:
        return None  # hater r5: Memphis showed a heading with no rows after the hotel left
    rows = "".join(tr([('<a href="%s" rel="noopener">%s</a>' % (esc(x["url"]), esc(_ridb_name(x["name"])))) if str(x.get("url") or "").startswith("https://") else esc(_ridb_name(x["name"])), esc(x["type"] or ""), "%.1f mi" % x["mi"], esc(", ".join(x["water"] or x["activities"][:3]) or "not listed"), esc("not listed" if (x.get("phone") or "").strip().upper() in ("", "N/A", "NA") else x["phone"])], right=(2,)) for x in r["sites"])
    return block("recreation_sites", "Recreation sites within %d miles" % r["radius_mi"], "agency", table(["Site", "Type", "Distance", "Activities listed", "Phone"], rows, right=(2,)),
                 "Source: Recreation.gov Recreation Information Database (RIDB), federal sites only; state and private ramps are not in it. Distances are straight-line from the gauge.%s Fetched %s." % ("", esc(tzl(parse_t(r["fetched_at"]), G["zone"]))), "ridb")  # was a table row that phones showed as a fake site card (hater 2026-10-27)


def _tide_t(s, with_date):
    d = datetime.datetime.strptime(s, "%Y-%m-%d %H:%M")
    return (d.strftime("%b %d, %I:%M %p") if with_date else d.strftime("%I:%M %p")).replace(" 0", " ").lstrip("0")


def b_tides(G):
    """High and low tide predictions at the nearest NOAA station, shown on reaches whose flow cycles within the day (tidal)."""
    t = G["rec"].get("tides")
    if not t or not t.get("rows") or not (G.get("osc") or t.get("mi", 99) <= 10):  # tidal by the flow cycle, or a NOAA prediction station within 10 mi (Hudson at Green Island sits 2.5 mi from the Troy station below the Federal Dam)
        return None
    now_l = G["now"].astimezone(G["zone"]).strftime("%Y-%m-%d %H:%M")  # station local time; past rows dropped (hater 2026-10-27: past tides under "next two days")
    t = dict(t, rows=[r for r in t["rows"] if r["t"] >= now_l])
    if not t["rows"]:
        return None
    rows = "".join(tr([esc(_tide_t(r["t"], i == 0 or r["t"][:10] != t["rows"][i - 1]["t"][:10])), "High tide" if r["type"] == "H" else "Low tide", "%.1f ft" % (r["v"] + 0.0 if round(r["v"], 1) else 0.0)], right=(2,)) for i, r in enumerate(t["rows"]))
    near = "" if G.get("osc") else '<p class="src">The flow at this gauge shows no tidal cycle; the table is for the nearest NOAA tide station, %.0f mi away, where the river is tidal.</p>' % t["mi"]
    return block("tides", "%s at %s, %s" % ("Tides" if G.get("osc") else "Tides nearby", esc(t["name"] or t["station"]), "next two days" if len({r["t"][:10] for r in t["rows"]}) >= 2 else "rest of today" if t["rows"][0]["t"][:10] == now_l[:10] else _tide_t(t["rows"][0]["t"], True).rsplit(",", 1)[0]), "noaa", near + table(["Time (station local)", "Tide", "Height above the tide datum (MLLW)"], rows, right=(2,)),
                 "Source: NOAA National Ocean Service, CO-OPS tide predictions for station %s (%s), %.0f mi from the gauge, fetched %s. Predictions, not observations; the river level here also depends on flow from upstream." % (esc(t["station"]), esc(t["name"] or ""), t["mi"], esc(tzl(parse_t(t["fetched_at"]), G["zone"]))), "coops")


def b_wpc(G):
    """WPC flood and excessive rainfall outlooks that cover the gauge point, and recent NWS flood reports within 50 miles. Hidden when there is nothing to show."""
    w = G["rec"].get("wpc")
    if not w:
        return None
    age = hours_old(w.get("fetched_at"), G["now"]) if w.get("fetched_at") else None
    if age is None or age > HIDE_H["wpc_outlooks"]:
        return None
    zone = G["zone"]
    body = ""
    if w.get("outlooks"):
        def loc(s_):
            """WPC gives either an ISO UTC time or a bare MM/DD/YYYY date: times show in the gauge's zone, dates stay dates."""
            if not s_:
                return "–"
            try:
                if "T" in s_ or " " in s_:  # ISO with Z, or 'YYYY-MM-DD HH:MM:SS' (both UTC; the ERO valid times are 12:00 UTC)
                    t_ = parse_t(s_.replace("Z", "+00:00").replace(" ", "T"))
                    return tzl(t_ if t_.tzinfo else t_.replace(tzinfo=datetime.timezone.utc), zone)
                return datetime.datetime.strptime(s_, "%m/%d/%Y").strftime("%b %d, %Y").replace(" 0", " ")
            except ValueError:
                return s_
        rows = "".join(tr([esc(o["name"]), esc((o.get("category") or "").title()), esc(loc(o["issued"])), "%s to %s" % (esc(loc(o["start"])), esc(loc(o["end"])))]) for o in w["outlooks"])
        ocards = [card(esc(o["name"]), esc((o.get("category") or "–").title()), "issued %s &middot; valid %s to %s" % (esc(loc(o["issued"])), esc(loc(o["start"])), esc(loc(o["end"])))) for o in w["outlooks"]]
        body += "<h3>Outlooks covering this location</h3>" + rail(ocards, "Flood outlooks covering this location") + more("Outlooks as a table", table(["Outlook", "Category", "Issued", "Valid"], rows))
    if w.get("reports"):
        rows = "".join(tr([esc(tzl(parse_t(r["t"]), zone)) if r.get("t") else "–", esc(r["type"] or ""), esc("%s, %s" % (r["where"], r["state"]) if r["where"] else (r["state"] or "")), esc(r["remarks"] or "–")]) for r in w["reports"])
        rcards = [card(esc(r["type"] or "Report"), esc("%s, %s" % (r["where"], r["state"]) if r["where"] else (r["state"] or "–")), esc(tzl(parse_t(r["t"]), zone)) if r.get("t") else "") for r in w["reports"][:6]]
        body += "<h3>Flood reports within 50 miles, last 72 hours (%d)</h3>" % len(w["reports"]) + rail(rcards, "Flood reports within 50 miles") + more(("All %d reports with the text as received" if len(w["reports"]) != 1 else "The %d report with the text as received") % len(w["reports"]), table(["Reported", "Type", "Location", "Report as received"], rows))
    if not body:
        return None
    out_b = block("wpc_outlooks", "Flood outlooks and reports", "official", body,
                  "Source: NOAA Weather Prediction Center significant river flood outlook and excessive rainfall outlooks (a point inside a published area), and National Weather Service local storm reports (preliminary, unverified reports from trained spotters, emergency managers and the public), fetched %s. An area is regional: it does not say this gauge will flood, and a report nearby may not concern this river." % esc(tzl(parse_t(w["fetched_at"]), zone)), "nws")
    return out_b


def b_stage_years(G):
    """Years whose annual peak stage reached each NWS flood category. Shown only when USGS and NWS stages are on the same datum (latest readings agree within 0.10 ft) and the NWS publishes flood stages."""
    n = G["rec"].get("nwps") or {}
    p = G["rec"].get("peaks")
    cats = n.get("categories") or {}
    obs = n.get("obs_stage")
    if not (SOURCES["nwps"]["status"] in ("quoted", "owner-permission") and p and obs and "minor" in cats and G["sg"]):
        return None
    t_us, v_us, meta = G["sg"][-1]
    if (meta.get("unit_of_measure") or "ft") != "ft" or abs((parse_t(obs["t"]) - t_us).total_seconds()) > 5400 or abs(obs["v"] - v_us) > 0.10:
        return None
    rows = [r for r in p["rows"] if r[2] is not None and (not r[3] or r[3].replace(" ", "") == "['ESTIMATED']")] if all(len(r) > 3 for r in p["rows"]) else []  # any other USGS qualifier (different datum, backwater, not the annual maximum) can misstate the peak stage
    if len(rows) < 10:
        return None
    out = ""
    for k in ("minor", "moderate", "major"):
        if k in cats:
            out += tr(["%s flood stage" % k.capitalize(), "%.1f ft" % cats[k], "%d of %d" % (sum(1 for r in rows if r[2] >= cats[k]), len(rows))], right=(1, 2))
    out_b = block("flood_stage_years", "Annual peaks that reached flood stage", "hist", table(["NWS category", "Stage", "Years reaching it"], out, right=(1, 2)),
                 "Source: USGS annual peak gage heights (%d years with a recorded peak stage, %s to %s; peaks that USGS marks with any qualifier other than estimated are left out) compared with National Weather Service flood stages for forecast point %s. Shown because the latest USGS and NWS stage readings agree within 0.10 ft. Older stages can be on an older gauge datum." % (
                     len(rows), esc(rows[0][0][:4]), esc(rows[-1][0][:4]), esc(n.get("lid") or "")), "usgs")
    out_b["also"] = ["nwps"]
    return out_b


def b_floodfreq(G):
    f = G["rec"].get("floodfreq")
    if not f or not f.get("rows") or f.get("conflict"):
        return None  # regulated gauges show with USGS's own caveat (2026-10-26: hiding them withheld published statistics)
    has_ci = any(r.get("lo") is not None and r.get("hi") is not None for r in f["rows"])
    rows = "".join(tr(["%s%%" % ("%g" % r["aep"]), "%s years" % "{:,g}".format(round(100 / r["aep"], 1)), "%s cfs" % fmtc(r["q"])]
                      + ([("%s to %s cfs" % (fmtc(r["lo"]), fmtc(r["hi"]))) if r.get("lo") is not None and r.get("hi") is not None else "–"] if has_ci else []), right=(2, 3)) for r in f["rows"] if r["aep"] <= 50)
    if not rows:
        return None
    _url = re.match(r"https?://\S+?(?=https?://|$)", f.get("url") or "")  # StreamStats sends "null" or the same URL twice run together
    rec = ("record %s%s" % (esc(f["range"]), (", %s years" % fmt(f["years"])) if f.get("years") else "")) if f.get("range") else "record years not stated"
    return block("flood_frequency", "Flood frequency of peak flows", "hist", table(["Chance in any year", "Average spacing", "Peak flow"] + (["Confidence interval, as published"] if has_ci else []), rows, right=(2, 3)),
                 "Source: USGS StreamStats gage statistics (peak-flow statistics, annual exceedance probability), %s. %s. Long-run statistics, not a forecast or a schedule.%s Fetched %s." % (
                     rec, esc((f.get("citation") or "citation not stated").rstrip(". ")) + ((" " + esc(_url.group(0))) if _url else ""),
                     " USGS marks this gauge as regulated (dams or diversions upstream change its flow)." if f.get("regulated") else "", esc(tzl(parse_t(f["fetched_at"]), G["zone"]))), "usgs")


def b_flowdur(G):
    f = G["rec"].get("floodfreq") or {}
    want = (5, 10, 25, 50, 75, 90, 95)
    d = [r for r in f.get("dur") or [] if r["p"] in want]
    if len(d) < 4:
        return None
    rows = "".join(tr(["%g%% of days" % r["p"], "%s cfs" % fmtc(r["q"])], right=(1,)) for r in d)
    rng = next((r["range"] for r in d if r.get("range")), "")
    yrs = re.findall(r"\d{4}", rng)
    return block("flow_duration", "How often each flow is reached" + ((", %s to %s" % (yrs[0], yrs[-1])) if len(yrs) >= 2 else " (USGS, years not stated)"), "hist", table(["Flow at or above this on", "Flow"], rows, right=(1,)),
                 "Source: USGS StreamStats gage statistics (flow-duration statistics)%s. The flow equalled or exceeded on that share of days over the period.%s Fetched %s." % (
                     (", " + esc(rng.replace(" ", " to "))) if rng else "", " USGS marks this gauge as regulated." if f.get("regulated") else "", esc(tzl(parse_t(f["fetched_at"]), G["zone"]))), "usgs")


SEASONS = {"JFM": "January to March", "FMA": "February to April", "MAM": "March to May", "AMJ": "April to June", "MJJ": "May to July", "JJA": "June to August", "JAS": "July to September", "ASO": "August to October",
           "SON": "September to November", "OND": "October to December", "NDJ": "November to January", "DJF": "December to February"}


def _chance(v):
    if isinstance(v, (int, float)):
        return "%.0f%%" % (v * 100)
    s = str(v).strip()
    try:
        return ("less than %.0f%%" % (float(s.lstrip("<").strip()) * 100)) if s.startswith("<") else "%.0f%%" % (float(s) * 100)
    except ValueError:
        return esc(s)


def b_flood_outlook(G):
    n = G["rec"].get("nwps") or {}
    lro = n.get("lro")
    if not lro or not any(lro.get(k) is not None for k in ("minorCS", "moderateCS", "majorCS")):
        return None
    period = SEASONS.get(str(lro.get("interval") or "").upper())
    rows = "".join(tr([lab, _chance(lro[k])], right=(1,)) for k, lab in (("minorCS", "Minor flooding"), ("moderateCS", "Moderate flooding"), ("majorCS", "Major flooding")) if lro.get(k) is not None)
    when = (" produced %s" % fdate(str(lro["producedTime"])[:10])) if lro.get("producedTime") else ""
    _od = (G["ldate"] - datetime.date.fromisoformat(str(lro["producedTime"])[:10])).days if lro.get("producedTime") else None
    _old = ('<p class="src">The NWS produced this outlook %d days ago, on %s, and has not published a newer one for this point.</p>' % (_od, esc(fdate(str(lro["producedTime"])[:10])))) if _od is not None and _od > 120 else ""
    return block("flood_outlook", "Long-range flood outlook%s" % ((", " + period) if period else ""), "official", _old + table(["Category", "Chance at this forecast point"], rows, right=(1,)),
                 "Source: National Weather Service long-range river flood outlook for forecast point %s,%s; the published chance of flooding in each category during the outlook period. Fetched %s." % (esc(n.get("lid") or ""), when, esc(tzl(parse_t(n["fetched_at"]), G["zone"]))), "nwps")
