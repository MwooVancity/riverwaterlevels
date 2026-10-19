"""Blocks for the second wave of government sources (NWS forecast point facts, FEMA declarations, NCEI storm events, dams, Reclamation releases, ACIS rain, StreamCat, FEMA flood zones).
Same registry rules as render.py and blocks2.py. Each block is gated by its source row in data/sources.json.
"""
import datetime
from lib.render import *  # block, table, tr, esc, fmt, tzl, parse_t, fdate, SOURCES, ...

ZONE_NAMES = {"A": "Special flood hazard area, no base flood elevation", "AE": "Special flood hazard area with base flood elevation", "AH": "Shallow flooding (ponding)", "AO": "Shallow flooding (sheet flow)",
              "X": "Outside the special flood hazard area", "VE": "Coastal high hazard area", "D": "Possible but undetermined flood hazard"}


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
            nm = esc(x.get("Name") or x.get("LID") or "")
            p = on_site.get((x.get("LID") or "").upper())
            return '<a href="%s">%s</a>' % (p["water_url"], nm) if p else nm
        nm_list = [x for x in (rfl.get(key) or []) if isinstance(x, dict)]
        if nm_list:
            total = rfl.get(key + "_n") or len(nm_list)
            if key == "upstream":  # stored farthest first: list nearest first
                nm_list = nm_list[::-1]
            if total > len(nm_list):
                lab = "%s (nearest %d of %d)" % (lab, len(nm_list), total)
            rows += tr([lab, "; ".join(nm_link(x) for x in nm_list)])
    return block("nws_forecast_point", "National Weather Service forecast point", "official", table(["Item", "Value"], rows),
                 "Source: National Weather Service National Water Prediction Service, forecast point %s, fetched %s." % (esc(n["lid"]), esc(tzl(parse_t(n["fetched_at"]), G["zone"]))), "nwps")


def b_declarations(G):
    d = G["rec"].get("openfema")
    if not d:
        return None
    items = d.get("items") or []
    area = ((items[0].get("area") if items else None) or "this county").replace(" (County)", " County")
    rows = "".join(tr([esc(i["id"] or ""), fdate(i["date"]) if i["date"][:4].isdigit() else "–", "%s to %s" % (fdate(i["begin"]), fdate(i["end"])) if i["begin"][:4].isdigit() and i["end"][:4].isdigit() else "–", esc(i["title"] or ""),
                       esc(", ".join(x for x, f in (("Public assistance", i.get("pa")), ("Individual assistance", i.get("ia"))) if f) or "–")]) for i in items)
    body = ("<p>%d federal flood disaster declarations on file for %s.</p>" % (d["count"], esc(area))) + (table(["Declaration", "Declared", "Incident period", "Title", "Programs"], rows, hide=(4,)) if rows else "")  # four visible columns: on a phone the site stacks them as label-and-value rows instead of clipping
    return block("flood_declarations", "Federal flood disaster declarations", "hist", body,
                 "Source: This product uses the Federal Emergency Management Agency's OpenFEMA API, but is not endorsed by FEMA. Dataset: Disaster Declarations Summaries, endpoint https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries (v2), accessed %s. Declarations whose type is Flood or whose title contains FLOOD; the 12 most recent are listed." % esc(tzl(parse_t(d["fetched_at"]), G["zone"])), "openfema")


def _usd(v):
    return "$%s" % fmt(v) if v else "$0"


def b_storms(G):
    s = G["rec"].get("storms")
    if not s:
        return None
    raw = s.get("county") or ""
    county = raw.title().replace(" (C)", "")
    kind = s.get("kind") or "County"
    summary = tr([str(s["n"]), str(s["deaths"]), str(s["injuries"]), _usd(s["damage"])], right=(0, 1, 2, 3))
    body = table(["Flood and flash flood events", "Deaths", "Injuries", "Property and crop damage"], summary, right=(0, 1, 2, 3))
    if s.get("recent"):
        rows = "".join(tr([fdate(r[2]) if r[2][:4].isdigit() and len(r[2]) == 10 else esc(r[2]), esc(r[3]), esc(r[7] or "–"), esc(((r[9] if len(r) > 9 else "") or "–").title()), str(r[4]), _usd(r[6])], right=(4, 5)) for r in s["recent"])
        body += "<h3>Most recent events</h3>" + table(["Date", "Type", "Cause", "Location", "Deaths", "Damage"], rows, right=(4, 5))
    return block("storm_events", "Flood events in %s %s, %d to %d" % (esc(county or "this"), kind, s["years"][0], s["years"][1]), "hist", body,
                 "Source: NOAA National Centers for Environmental Information, Storm Events Database (county-level Flood and Flash Flood events), %d to %d, fetched %s. Deaths include direct and indirect; damage is as reported to NCEI. NCEI data are in the public domain in the United States." % (
                     s["years"][0], s["years"][1], esc(tzl(parse_t(s["fetched_at"]), G["zone"]))), "ncei")


def b_dams(G):
    d = G["rec"].get("nid")
    if not d or not d.get("dams"):
        return None
    rows = "".join(tr([esc(x["name"] or ""), esc(x["river"] or "–"), ("%s ft" % fmt(x["height_ft"])) if x.get("height_ft") else "–", ("%s acre-ft" % fmt(x["storage_af"])) if x.get("storage_af") else "–",
                       str(x["year"]) if x.get("year") else "–", esc(x["hazard"] or "–"), "%.1f mi" % x["mi"]], right=(2, 3, 6)) for x in d["dams"])
    return block("dams_nearby", "Dams within %d miles" % d["miles"], "map", table(["Dam", "Stream", "Height", "Storage", "Completed", "Hazard potential", "Distance"], rows, right=(2, 3, 6)),
                 "Source: U.S. Army Corps of Engineers National Inventory of Dams, %d dams within %d miles of the gauge (nearest %d shown), fetched %s. Hazard potential describes the consequence of failure, not the condition of the dam." % (
                     d["count"], d["miles"], len(d["dams"]), esc(tzl(parse_t(d["fetched_at"]), G["zone"]))), "nid")


def b_rise(G):
    r = G["rec"].get("rise")
    if not r or not r.get("series"):
        return None
    dates = sorted({x[0] for s in r["series"].values() for x in s["rows"]}, reverse=True)[:10]
    labs = list(r["series"])
    rows = ""
    for dt in dates:
        cells = [fdate(dt)]
        for lab in labs:
            v = next((x[1] for x in r["series"][lab]["rows"] if x[0] == dt), None)
            cells.append("–" if v is None else "%s %s" % (fmt(v), r["series"][lab]["unit"]))
        rows += tr(cells, right=tuple(range(1, len(labs) + 1)))
    return block("dam_releases", "%s daily operations" % esc(r["dam"]), "agency", table(["Date"] + labs, rows, right=tuple(range(1, len(labs) + 1))),
                 "Source: U.S. Bureau of Reclamation RISE, daily values for %s (date is the UTC day of the record), fetched %s." % (esc(r["dam"]), esc(tzl(parse_t(r["fetched_at"]), G["zone"]))), "usbr")


def b_acis(G):
    a = G["rec"].get("acis")
    if not a or not a.get("stations"):
        return None
    heads = ["Station", "Distance"] + [datetime.date.fromisoformat(d).strftime("%b %d").replace(" 0", " ") for d in a["days"]]
    cell = lambda v: "–" if v in ("M", "S", "A") else ("trace" if v == "T" else "%s in" % v if v.replace(".", "", 1).isdigit() else esc(v))
    rows = "".join(tr([esc((x["name"] or "").title()), "%.0f mi" % (x["km"] * 0.621371)] + [cell(v) for v in x["vals"]], right=tuple(range(1, 9))) for x in a["stations"])
    return block("county_station_rain", "Measured daily rain at nearby weather stations", "obs", table(heads, rows, right=tuple(range(1, 9))),
                 "Source: NOAA Regional Climate Centers ACIS, daily precipitation at the nearest county weather stations, fetched %s. Each value is a 24-hour total for the station's observation day; trace means less than 0.01 in." % esc(tzl(parse_t(a["fetched_at"]), G["zone"])), "acis")


def b_streamcat(G):
    s = G["rec"].get("streamcat")
    if not s or not s.get("vals"):
        return None
    v = s["vals"]
    spec = (("pctimp2019ws", "Impervious surface, 2019", lambda x: "%.1f%%" % x), ("pcturbmd2019ws", "Medium-intensity urban land, 2019", lambda x: "%.1f%%" % x), ("pctcrop2019ws", "Cropland, 2019", lambda x: "%.1f%%" % x),
            ("pctwdwet2019ws", "Woody wetland, 2019", lambda x: "%.1f%%" % x), ("elevws", "Mean elevation", lambda x: "%s ft" % fmt(x * 3.28084)), ("precip8110ws", "Mean annual precipitation, 1981 to 2010", lambda x: "%.1f in" % (x / 25.4)),
            ("runoffws", "Mean annual runoff", lambda x: "%.1f in" % (x / 25.4)), ("bfiws", "Base-flow index", lambda x: "%.0f%%" % x), ("damdensws", "Dam density", lambda x: "%.3f per sq km" % x))
    rows = "".join(tr([lab, f(v[k])], right=(1,)) for k, lab, f in spec if k in v)
    from lib import ui
    pc = [(l, k) for k, l in (("pctimp2019ws", "Impervious surface, 2019"), ("pcturbmd2019ws", "Medium-intensity urban land, 2019"), ("pctcrop2019ws", "Cropland, 2019"), ("pctwdwet2019ws", "Woody wetland, 2019"), ("bfiws", "Base-flow index (share of streamflow from groundwater)")) if k in v]
    wid = ui.bars([(l, v[k], "%.1f%%" % v[k]) for l, k in pc], 100) if pc else ""
    ch = ui.chips([(l, f(v[k])) for k, l, f in spec if k in ("elevws", "precip8110ws", "runoffws", "damdensws") and k in v])
    return block("watershed_characteristics", "Upstream watershed characteristics", "agency", wid + ch,
                 "Source: U.S. EPA StreamCat (NHDPlus reach %s), watershed-wide metrics; land cover from the 2019 National Land Cover Database. Static values, fetched %s." % (esc(str(s["comid"])), esc(tzl(parse_t(s["fetched_at"]), G["zone"]))), "epa")


def b_fema_zone(G):
    z = G["rec"].get("fema_zone")
    if not z or not z.get("zones"):
        return None
    rows = "".join(tr([esc(a), esc(ZONE_NAMES.get(a, "Zone as published")), esc(b or "–"), "Yes" if c == "T" else "No" if c == "F" else "–"]) for a, b, c in z["zones"])
    return block("flood_zones", "FEMA flood hazard zones within %d m" % z["meters"], "map", table(["Zone", "Meaning", "Subtype", "Special flood hazard area"], rows),
                 "Source: FEMA National Flood Hazard Layer data as republished by Esri (USA Flood Hazard, reduced set, generalised polygons), zones intersecting a %d m circle around the gauge, fetched %s. Not a flood determination; the FIRM is the official designation." % (z["meters"], esc(tzl(parse_t(z["fetched_at"]), G["zone"]))), "fema_nfhl")


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
    return block("month_chart", "Last 30 days", "hist", svg,
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
    rows = "".join(tr([fdate(r["t"][:10]), "%s cfs" % fmt(r["flow"]), ("%.2f ft" % r["stage"]) if r.get("stage") is not None else "–", esc(r.get("rating") or "–")], right=(1, 2)) for r in f["rows"][:10])
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
    if abs((near[0] - t0).total_seconds()) > 5400:
        return None
    if unit == "ft":
        if not near[1] or not G["sg"] or (G["sg"][-1][2].get("unit_of_measure") or "").lower() not in ("ft", "feet"):
            return None
        cur, fv = G["sg"][-1][1], near[1]
        if abs(cur - fv) <= max(0.5, 0.05 * abs(cur)):
            return None
        return {"t": tzl(near[0], G["zone"], date=False), "f": "%.1f ft" % fv, "c": "%.2f ft" % cur}
    cur, fv = G["lv"], near[2]
    if not fv or abs(cur - fv) <= 0.25 * max(cur, fv):
        return None
    return {"t": tzl(near[0], G["zone"], date=False), "f": "%s cfs" % fmt(fv), "c": "%s cfs" % fmt(cur)}


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
    if ob and ok("nws") and ob.get("temp_c") is not None and hours_old(ob.get("timestamp"), G["now"]) is not None and hours_old(ob.get("timestamp"), G["now"]) <= 12:
        wk = ob.get("wind_kmh")
        dirs = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")
        wd = dirs[int((ob["wind_dir"] % 360) / 22.5 + 0.5) % 16] if ob.get("wind_dir") is not None else ""
        out["air"] = {"f": ob["temp_c"] * 9 / 5 + 32, "wind": (wk * 0.621371) if wk is not None else None, "gust": (ob["gust_kmh"] * 0.621371) if ob.get("gust_kmh") is not None else None, "dir": wd, "st": ob.get("station") or "", "name": ob.get("name") or "", "mi": round(miles_between(G["lat"], G["lon"], ob["ll"][1], ob["ll"][0])) if ob.get("ll") else None, "t": tzl(parse_t(ob["timestamp"]), zone)}
    if pages:
        for x in ((rec.get("related") or {}).get("items") or []):
            pr = pages.get(x["site"])
            if x.get("relation") == "upstream" and pr and pr.get("_built") and x.get("flow") is not None:
                out["up"] = {"flow": x["flow"], "name": river_at(pr["river"], pr["place"]), "url": pr["water_url"], "lag": x.get("lag_h")}
                break
    if len(fl) >= 8 and not G.get("osc"):
        for h in (1, 6, 24):
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
        pts = [x for x in fc_points(f) if x[0] >= G["now"] - datetime.timedelta(hours=1)]
        stage = [(t_, s_) for t_, s_, _ in pts if s_ is not None]
        flow = [(t_, f_) for t_, _, f_ in pts if f_ is not None]
        gap = datum_gap(G)
        fut, unit = (stage, "ft") if stage else (flow, "cfs")
        if fut and (age is None or age <= 72):
            hi = max(fut, key=lambda x: x[1])
            near = [i for i, (_, v_) in enumerate(fut) if v_ >= hi[1] - (0.05 if unit == "ft" else 0.01 * abs(hi[1]))]
            lo_f = min(v_ for _, v_ in fut)
            depth = max(0.15 if unit == "ft" else 0.03 * abs(hi[1]), 0.25 * (hi[1] - lo_f))  # a second peak needs a valley at least a quarter as deep as the whole rise, not a wobble on a plateau
            peaks = 1 + sum(1 for a_, b_ in zip(near, near[1:]) if min(v_ for _, v_ in fut[a_:b_ + 1]) < hi[1] - depth)
            end = fut[-1]
            first_hi = near[0]
            out["fc"] = {"v": hi[1], "unit": unit, "t": tzl(hi[0], zone), "lid": n.get("lid") or "", "repeat": peaks >= 2, "issued": tzl(parse_t(f["issued"]), zone) if f.get("issued") else "at a time not stated",
                         "falls": first_hi <= 2 and end[1] <= hi[1] - (0.5 if unit == "ft" else 0.1 * abs(hi[1])) and (end[0] - hi[0]).total_seconds() > 6 * 3600, "end_v": end[1], "end_t": tzl(end[0], zone),
                         "datum": gap,
                         "flow_at": next((x[2] for x in pts if x[0] == hi[0]), None) if unit == "ft" else None,
                         "offset": _fc_offset(G, pts, unit, gap),
                         "cur": (gap[0] if gap else (G["sg"][-1][1] if G["sg"] and (G["sg"][-1][2].get("unit_of_measure") or "").lower() in ("ft", "feet") else None)) if unit == "ft" else G["lv"]}
    nws = rec.get("nws") or {}
    if ok("nws") and nws.get("alerts") is not None and nws.get("fetched_at"):
        al = [x for x in nws["alerts"] if (x.get("event") or "") not in IGNORED_ALERTS]
        out["alerts"] = {"n": len(al), "names": [x.get("event") or "" for x in al[:3]]}
    rn = rec.get("rain") or {}
    if ok("rfc") and (rn.get("inches") or {}).get("last_24h") is not None:
        vt = (rn.get("valid_through") or {}).get("last_24h")
        out["rain"] = {"in": rn["inches"]["last_24h"], "to": tzl(parse_t(vt), zone) if vt else None}
    return out


def b_wpc(G):
    """WPC flood and excessive rainfall outlooks that cover the gauge point, and recent NWS flood reports within 50 miles. Hidden when there is nothing to show."""
    w = G["rec"].get("wpc")
    if not w:
        return None
    age = hours_old(w.get("fetched_at"), G["now"]) if w.get("fetched_at") else None
    if age is None or age > 6:
        return None
    zone = G["zone"]
    body = ""
    if w.get("outlooks"):
        rows = "".join(tr([esc(o["name"]), esc((o.get("category") or "").title()), esc(o["issued"] or "–"), "%s to %s" % (esc(o["start"] or "–"), esc(o["end"] or "–"))]) for o in w["outlooks"])
        body += "<h3>Outlooks covering this location</h3>" + table(["Outlook", "Category", "Issued", "Valid"], rows)
    if w.get("reports"):
        rows = "".join(tr([esc(tzl(parse_t(r["t"]), zone)) if r.get("t") else "–", esc(r["type"] or ""), esc("%s, %s" % (r["where"], r["state"]) if r["where"] else (r["state"] or "")), esc(r["remarks"] or "–")]) for r in w["reports"])
        body += "<h3>Flood reports within 50 miles, last 72 hours (%d)</h3>" % w["n_reports"] + table(["Reported", "Type", "Location", "Report as received"], rows)
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
    if not f or not f.get("rows") or f.get("regulated") or f.get("conflict"):
        return None
    has_ci = any(r.get("lo") is not None and r.get("hi") is not None for r in f["rows"])
    rows = "".join(tr(["%s%%" % ("%g" % r["aep"]), "%s years" % "{:,g}".format(round(100 / r["aep"], 1)), "%s cfs" % fmt(r["q"])]
                      + ([("%s to %s cfs" % (fmt(r["lo"]), fmt(r["hi"]))) if r.get("lo") is not None and r.get("hi") is not None else "–"] if has_ci else []), right=(2, 3)) for r in f["rows"] if r["aep"] <= 50)
    if not rows:
        return None
    rec = ("record %s%s" % (esc(f["range"]), (", %s years" % fmt(f["years"])) if f.get("years") else "")) if f.get("range") else "record years not stated"
    return block("flood_frequency", "Flood frequency: peak flows", "hist", table(["Chance in any year", "Average spacing", "Peak flow"] + (["Confidence interval, as published"] if has_ci else []), rows, right=(2, 3)),
                 "Source: USGS StreamStats gage statistics (peak-flow statistics, annual exceedance probability), %s. %s. Long-run statistics, not a forecast or a schedule. Fetched %s." % (
                     rec, esc(f.get("citation") or "citation not stated") + ((" " + esc(f["url"])) if f.get("url") else ""), esc(tzl(parse_t(f["fetched_at"]), G["zone"]))), "usgs")


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
    return block("flood_outlook", "Long-range flood outlook%s" % ((", " + period) if period else ""), "official", table(["Category", "Chance at this forecast point"], rows, right=(1,)),
                 "Source: National Weather Service long-range river flood outlook for forecast point %s,%s; the published chance of flooding in each category during the outlook period. Fetched %s." % (esc(n.get("lid") or ""), when, esc(tzl(parse_t(n["fetched_at"]), G["zone"]))), "nwps")
