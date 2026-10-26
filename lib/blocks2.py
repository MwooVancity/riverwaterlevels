"""Blocks added after the fresh-eyes review. Imported at the bottom of lib/render.py.
Same registry rules as render.py: a block returns a dict or None, shows only values with units and times, carries a Source line, and appears only when its source is cleared in data/sources.json.
"""
import math, datetime
from lib.render import *  # block, table, tr, esc, fmt, tzl, parse_t, hours_old, fdate, nice_ticks, SOURCES, ...

OK_STATUS = ("quoted", "owner-permission")
CATS = ("action", "minor", "moderate", "major")
DROUGHT = (("No drought", 1), ("Abnormally dry (D0)", 2), ("Moderate drought (D1)", 3), ("Severe drought (D2)", 4), ("Extreme drought (D3)", 5), ("Exceptional drought (D4)", 6))
AMBER = "var(--amber)"


def cleared(src_id):
    return SOURCES[src_id]["status"] in OK_STATUS


def _time_svg(obs, fc, hl, vmin, vmax, ticks, t0, t1, zone, W, Hh, fs, nx, cls, label):
    """Time series (observed solid, forecast dashed) with dashed horizontal threshold lines; the y axis is the caller's round axis."""
    L, B = (56, 30) if W > 500 else (46, 28)
    span = (t1 - t0).total_seconds() or 1
    X = lambda t: L + (t - t0).total_seconds() / span * (W - L - 14)
    Y = lambda v: 12 + (1 - (v - vmin) / ((vmax - vmin) or 1)) * (Hh - B - 12)
    grid = "".join('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--line)"/><text x="%d" y="%.1f" font-size="%d" fill="var(--mut)" text-anchor="end">%s</text>' % (L, W - 14, Y(tv), Y(tv), L - 6, Y(tv) + 4, fs, tf(tv, ticks)) for tv in ticks)
    xl = ""
    for k in range(nx):
        tt = t0 + (t1 - t0) * k / (nx - 1)
        xl += '<text x="%.1f" y="%d" font-size="%d" fill="var(--mut)" text-anchor="%s">%s</text>' % (X(tt), Hh - 8, fs, "start" if k == 0 else "end" if k == nx - 1 else "middle", tt.astimezone(zone).strftime("%b %d").replace(" 0", " "))
    lines = ""
    for name, v in hl:
        lines += '<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="%s" stroke-dasharray="6 4"/><text x="%d" y="%.1f" font-size="%d" fill="%s" text-anchor="end">%s %s</text>' % (L, W - 14, Y(v), Y(v), AMBER, W - 16, Y(v) - 4, fs, AMBER, esc(name), fmt(v))
    step = max(1, len(obs) // 220)
    gaps = sorted((b[0] - a[0]).total_seconds() for a, b in zip(obs, obs[1:]))
    gmax = max(7200, 3 * gaps[len(gaps) // 2]) if gaps else 7200  # a gap over 3x the usual step (min 2 h) breaks the line
    segs, cur_seg = [], [obs[0]]
    for a, b in zip(obs, obs[1:]):
        if (b[0] - a[0]).total_seconds() > gmax:
            segs.append(cur_seg)
            cur_seg = []
        cur_seg.append(b)
    segs.append(cur_seg)
    for sg_ in segs:
        o = sg_[::step] + ([sg_[-1]] if sg_[-1] is not sg_[::step][-1] else [])
        if len(o) == 1:
            lines += '<circle cx="%.1f" cy="%.1f" r="2" fill="var(--accent)"/>' % (X(o[0][0]), Y(o[0][1]))
        else:
            lines += '<polyline points="%s" fill="none" stroke="var(--accent)" stroke-width="2.4"/>' % " ".join("%.1f,%.1f" % (X(t), Y(v)) for t, v in o)
    if fc:
        pts = [obs[-1]] + fc
        lines += '<polyline points="%s" fill="none" stroke="var(--accent)" stroke-width="2.4" stroke-dasharray="7 4"/>' % " ".join("%.1f,%.1f" % (X(t), Y(v)) for t, v in pts)
        lines += '<line x1="%.1f" x2="%.1f" y1="12" y2="%d" stroke="var(--mut)" stroke-dasharray="2 3"/>' % (X(obs[-1][0]), X(obs[-1][0]), Hh - B)
    lines += '<circle cx="%.1f" cy="%.1f" r="5" fill="var(--accent)"/>' % (X(obs[-1][0]), Y(obs[-1][1]))
    return '<svg class="%s" viewBox="0 0 %d %d" width="100%%" role="img" aria-label="%s">%s%s%s</svg>' % (cls, W, Hh, esc(label), grid, xl, lines)


def b_stage_chart(G):
    sg = G["sg"]
    if len(sg) < 8 or (sg[-1][2].get("unit_of_measure") or "ft") != "ft":
        return None
    zone, now = G["zone"], G["now"]
    t1 = sg[-1][0]
    t0 = max(sg[0][0], t1 - datetime.timedelta(days=7))
    obs = [(t, v) for t, v, _ in sg if t >= t0]
    n = G["rec"].get("nwps") or {}
    nws = cleared("nwps")
    fc, issued = [], None
    f = n.get("forecast") if nws else None
    gap = datum_gap(G)  # NWS and USGS stages on different zero points: the forecast and the flood stages belong to the NWS scale, so they are never drawn on the USGS axis
    if f and f.get("points") and not gap:
        age = hours_old(f.get("issued"), now) if f.get("issued") else None
        if age is None or age <= 72:
            issued = f.get("issued")
            fc = [(t_, s_) for t_, s_, _ in fc_points(f) if s_ is not None and t_ > t1]
    cats = (n.get("categories") or {}) if nws else {}
    vals = [v for _, v in obs] + [v for _, v in fc]
    lo, hi = min(vals), max(vals)
    if hi - lo < 1.0:  # a tiny rise must not look like a flood: keep at least one foot of axis
        lo, hi = (lo + hi) / 2 - 0.5, (lo + hi) / 2 + 0.5
    vmin, vmax, ticks = nice_ticks(lo, hi)
    hl = [(k.capitalize(), cats[k]) for k in CATS if k in cats and vmin <= cats[k] <= vmax] if not gap else []
    tend = fc[-1][0] if fc else t1
    label = "Gage height in feet over the last 7 days" + (" and the National Weather Service forecast" if fc else "")
    svg = _time_svg(obs, fc, hl, vmin, vmax, ticks, t0, tend, zone, 760, 250, 11, 6, "cw", label) + _time_svg(obs, fc, hl, vmin, vmax, ticks, t0, tend, zone, 340, 250, 12, 4, "cn", label)
    cur = obs[-1][1]
    from lib.render import nws_point_note
    pn_ = nws_point_note(G) if cats else ""
    rows = (tr(["Flood stages from", "NWS", esc(pn_)], right=(1,)) if pn_ else "") + tr(["Latest USGS gage height", "%.2f ft" % cur, esc(tzl(obs[-1][0], zone))], right=(1,))
    if gap:
        cur = gap[0]  # flood stages are NWS stages: measure them against the NWS reading
        rows += tr(["Stage read by the NWS", "%.2f ft" % gap[0], "%s: NWS and USGS read this gauge on different zero points (USGS %.2f ft at that time)%s" % (esc(tzl(gap[2], zone)), gap[1], "; the flood stages below are NWS stages" if cats else "")], right=(1,))
    for k in CATS:
        if k in cats:
            d = cats[k] - cur
            rows += tr(["%s stage" % k.capitalize(), "%.1f ft" % cats[k], ("%.1f ft above the latest gage height" % d) if d > 0 else ("latest gage height is %.1f ft above it" % -d)], right=(1,))
    if fc:
        hi = max(fc, key=lambda x: x[1])
        rows += tr(["Forecast high", "%.1f ft" % hi[1], esc(tzl(hi[0], zone))], right=(1,))
    if gap and f and f.get("points"):
        fs_ = [(t_, s_) for t_, s_, _ in fc_points(f) if s_ is not None and t_ > t1]
        if fs_:
            hi = max(fs_, key=lambda x: x[1])
            rows += tr(["Forecast high (NWS stage)", "%.1f ft" % hi[1], esc(tzl(hi[0], zone))], right=(1,))
    from lib import ui
    lad = ui.ladder({k: cats[k] for k in CATS if k in cats}, cur, max(fc, key=lambda x: x[1])[1] if fc else None, "Latest, %s:" % tzl(G["sg"][-1][0], G["zone"], date=False).replace(" ", " ")) if cats else ""
    body = ("" if (cats or not nws) else "<p>The National Weather Service publishes no flood stages for this gauge, so none are drawn.</p>") + lad + svg + more("Every stage and reading in a table", table(["Measure", "Gage height", "Note"], rows, right=(1,)))  # the ladder and chart carry the answer; the table is one tap away
    src = "Source: USGS Water Data API (continuous gage height), observed to %s." % esc(tzl(t1, zone))
    if cats or fc:
        what = " and ".join(x for x in (("Flood stages" if cats else ""), ("the forecast (dashed curve)" if fc else "")) if x)
        what = what[:1].upper() + what[1:]
        src += " %s from National Weather Service forecast point %s%s.%s" % (
            what, esc(n.get("lid") or ""), (", forecast issued %s" % esc(tzl(parse_t(issued), zone))) if issued else "",
            " Dashed horizontal lines are drawn only where they fall inside the axis; all stages are in the table." if cats else "")
    out = block("stage_chart", "Gage height and flood stages" if cats else "Gage height", "live", body, src, "usgs")
    if cats or fc:
        out["also"] = ["nwps"]
    return out


def _at(series, t, tol):
    best = min(series, key=lambda x: abs((x[0] - t).total_seconds()))
    return best if abs((best[0] - t).total_seconds()) <= tol else None


def _arrow(pct):
    return "&#9650;" if pct > 1 else "&#9660;" if pct < -1 else "&rarr;"


def b_rate(G):
    fl, sg = G["fl"], G["sg"]
    if len(fl) < 8 or G.get("osc"):  # flow that cycles within the day (tides): a change over 1 to 24 h compares two phases of the cycle
        return None
    steps = sorted((fl[i][0] - fl[i - 1][0]).total_seconds() for i in range(1, len(fl)))
    tol = max(1200, 0.6 * steps[len(steps) // 2])
    t1 = fl[-1][0]
    rows = ""
    cards = []
    for h in (1, 3, 6, 12, 24):
        fa = _at(fl, t1 - datetime.timedelta(hours=h), tol)
        if not fa:
            continue
        from lib.blocks3 import window_change
        wc = window_change(fl, t1, h)  # the same function the headline tile uses
        d = fl[-1][1] - fa[1]
        pct = wc[2] if wc else (d / fa[1] * 100 if fa[1] else 0)
        sa = _at(sg, sg[-1][0] - datetime.timedelta(hours=h), tol) if sg else None
        sd = ("%+.2f ft" % (sg[-1][1] - sa[1])) if sa else "–"
        cards.append(card("Last %d h" % h, "%s %+.1f%%" % (_arrow(pct), pct), "%s%s cfs, from %s cfs%s" % ("+" if d >= 0 else "-", fmtc(abs(d)), fmtc(fa[1]), (", height %s" % sd) if sa else "")))
        rows += tr(["%d h" % h, "%s cfs" % fmtc(fa[1]), "%s %s%s cfs (%+.1f%%)" % (_arrow(pct), "+" if d >= 0 else "-", fmtc(abs(d)), pct), ("%.2f ft" % sa[1]) if sa else "–", sd], right=(1, 2, 3, 4))
    if not rows:
        return None
    week = [x for x in fl if x[0] >= t1 - datetime.timedelta(days=7)]
    hi, lo = max(week, key=lambda x: x[1]), min(week, key=lambda x: x[1])
    ago = lambda t: ("%.0f h earlier" % ((t1 - t).total_seconds() / 3600)) if (t1 - t).total_seconds() >= 3600 else "within the last hour"
    ext = tr(["Highest reading", "%s cfs" % fmtc(hi[1]), esc(tzl(hi[0], G["zone"])), ago(hi[0])], right=(1,)) + tr(["Lowest reading", "%s cfs" % fmtc(lo[1]), esc(tzl(lo[0], G["zone"])), ago(lo[0])], right=(1,))
    from lib.render import flow_jitter
    note = '<p class="src">Flow readings at this gauge swing without following the gage height (lock, tide or backwater effects): read the direction from the Height change column.</p>' if flow_jitter(G) else ""
    cards += [card("Highest, 7 days", "%s <small>cfs</small>" % fmtc(hi[1]), "%s, %s" % (esc(tzl(hi[0], G["zone"])), ago(hi[0]))), card("Lowest, 7 days", "%s <small>cfs</small>" % fmtc(lo[1]), "%s, %s" % (esc(tzl(lo[0], G["zone"])), ago(lo[0])))]
    body = note + rail(cards, "Change over the last hours") + more("Full table", table(["Window", "Flow then", "Flow change", "Gage height then", "Height change"], rows, right=(1, 2, 3, 4), hide=(1, 3)) + "<h3>Last 7 days</h3>" + table(["Measure", "Flow", "Time", "Relative to latest reading"], ext, right=(1,), hide=(3,)))
    return block("rate_of_change", "Rate of rise and fall", "live", body,
                 "Source: computed from USGS continuous readings (Water Data API) to %s. Each row compares the latest reading with the reading closest to that many hours earlier; the arrow is steady (&rarr;) when the change is within 1%%." % esc(tzl(t1, G["zone"])), "usgs")


def _xy_svg(pts, cur, W, Hh, fs, cls, label):
    L, B = (60, 34) if W > 500 else (50, 30)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, x1, xt = nice_ticks(min(xs), max(xs), 9 if W > 500 else 6)
    y0, y1, yt = nice_ticks(min(ys), max(ys), 5)
    X = lambda v: L + (v - x0) / ((x1 - x0) or 1) * (W - L - 14)
    Y = lambda v: 12 + (1 - (v - y0) / ((y1 - y0) or 1)) * (Hh - B - 12)
    grid = "".join('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--line)"/><text x="%d" y="%.1f" font-size="%d" fill="var(--mut)" text-anchor="end">%s</text>' % (L, W - 14, Y(v), Y(v), L - 6, Y(v) + 4, fs, tf(v, yt)) for v in yt)
    grid += "".join('<text x="%.1f" y="%d" font-size="%d" fill="var(--mut)" text-anchor="middle">%s</text>' % (X(v), Hh - 12, fs, tf(v, xt)) for v in xt)
    line = '<polyline points="%s" fill="none" stroke="var(--accent)" stroke-width="2.4"/>' % " ".join("%.1f,%.1f" % (X(a), Y(b)) for a, b in pts)
    dot = ('<circle cx="%.1f" cy="%.1f" r="5.5" fill="%s" stroke="var(--card)" stroke-width="1.5"/>' % (X(cur[0]), Y(cur[1]), AMBER)) if cur and x0 <= cur[0] <= x1 and y0 <= cur[1] <= y1 else ""
    return '<svg class="%s" viewBox="0 0 %d %d" width="100%%" role="img" aria-label="%s">%s%s%s</svg>' % (cls, W, Hh, esc(label), grid, line, dot)


def b_rating(G):
    r = G["rec"].get("rating")
    if not r or len(r.get("pts") or []) < 8 or not G["sg"]:
        return None
    pts = [tuple(p) for p in r["pts"]]
    cur = (G["sg"][-1][1], G["lv"])
    lbl = "USGS stage-discharge rating: gage height in feet against flow in cfs"
    svg = _xy_svg(pts, cur, 760, 280, 11, "cw", lbl) + _xy_svg(pts, cur, 340, 280, 12, "cn", lbl)
    legend = '<p class="legend">Line: current USGS rating, gage height (ft, horizontal) to flow (cfs, vertical). <b style="color:%s">&#9679;</b> latest reading, %.2f ft and %s cfs.</p>' % (AMBER, cur[0], fmtc(cur[1]))
    return block("stage_flow_rating", "Gage height to flow rating", "hist", svg + legend,
                 "Source: USGS rating table for the gauge, thinned for display), fetched %s. Ratings are provisional and change with the channel." % (esc(tzl(parse_t(r["fetched_at"]), G["zone"]))), "usgs")


def b_about(G):
    m = G["rec"].get("meta")
    if not m:
        return None
    loc = m.get("loc") or {}
    ts = m.get("ts") or {}
    rows = ""
    items = [("USGS site name", loc.get("monitoring_location_name")), ("Site type", loc.get("site_type")), ("Agency", loc.get("agency_name")),
             ("County and state", ", ".join(x for x in (loc.get("county_name"), loc.get("state_name")) if x)),
             ("Drainage area", ("%s sq mi" % fmt(loc["drainage_area"])) if loc.get("drainage_area") else None),
             ("Altitude", ("%s ft (%s)" % (fmt(loc["altitude"]), loc.get("vertical_datum") or "datum not stated")) if loc.get("altitude") is not None else None),
             ("Hydrologic unit code", loc.get("hydrologic_unit_code")), ("Coordinates", "%.4f, %.4f" % (G["lat"], G["lon"]))]
    for key, lab in (("flow_daily", "Daily mean flow record"), ("flow_inst", "Instantaneous flow record"), ("stage_inst", "Instantaneous gage height record")):
        if ts.get(key):
            items.append((lab, "%s to %s" % (fdate(ts[key][0]), fdate(ts[key][1]))))
    pk = [x for x in ((G["rec"].get("peaks") or {}).get("rows") or []) if x[1] is not None]
    if pk:
        items.append(("Annual peaks on file", "%d, %s to %s" % (len(pk), pk[0][0][:4], pk[-1][0][:4])))
    for k, v in items:
        if v not in (None, "", "None"):
            rows += tr([esc(k), esc(v)])
    return block("about_gauge", "About USGS gauge %s" % G["site"], "hist", table(["Item", "Value"], rows),
                 "Source: USGS Water Data API monitoring-locations and time-series-metadata, fetched %s." % esc(tzl(parse_t(m["fetched_at"]), G["zone"])), "usgs")


def b_nwm_medium(G):
    n = G["rec"].get("nwm") or {}  # shown beside the NWS forecast too: it reaches days 4 to 10, past the official horizon
    pts = n.get("medium") or []
    if len(pts) < 4:
        return None
    age = hours_old(n.get("medium_reference_time"), G["now"]) if n.get("medium_reference_time") else None
    if age is not None and age > 72:
        return None
    fut = [p for p in pts if parse_t(p["t"]) >= G["now"] - datetime.timedelta(hours=1)]
    if len(fut) < 4:
        return None
    dt = (parse_t(fut[1]["t"]) - parse_t(fut[0]["t"])).total_seconds() or 3600
    stride = max(1, round(43200 / dt))
    rows = "".join(tr([esc(tzl(parse_t(p["t"]), G["zone"])), "%s cfs" % fmtc(p["flow"])], right=(1,)) for p in fut[::stride][:20])
    ref = esc(tzl(parse_t(n["medium_reference_time"]), G["zone"])) if n.get("medium_reference_time") else "time not stated"
    return block("nwm_medium_range", "Model guidance, days 1 to 10", "model", table(["Time (gauge-local)", "Modeled flow (ensemble mean)"], rows, right=(1,)),
                 "Source: NOAA National Water Model medium-range ensemble mean, reach %s, run %s. Model guidance, not an official forecast and not a measurement; error is larger on small basins." % (esc(str(n.get("comid"))), ref), "nwm", amber=(age is not None and age > 12))


def b_noforecast(G):
    n = G["rec"].get("nwps")
    if n is None:
        return None
    has_nwm = len((G["rec"].get("nwm") or {}).get("points") or []) >= 4
    if (n.get("forecast") or {}).get("points") or has_nwm:
        return None
    if n.get("lid"):
        msg = "National Weather Service forecast point %s currently has no river forecast issued." % esc(n["lid"])
    else:
        msg = "No National Weather Service river forecast point is linked to this USGS gauge."
    return block("no_river_forecast", "River forecast availability", "official", "<p>%s</p>" % msg,
                 "Source: National Weather Service National Water Prediction Service lookup for USGS gauge %s, checked %s." % (G["site"], esc(tzl(parse_t(n["fetched_at"]), G["zone"]))), "nwps")


def b_qpf(G):
    g = (G["rec"].get("nws") or {}).get("grid") or {}
    age = hours_old(g.get("updated"), G["now"]) if g.get("updated") else None
    start = G["now"].replace(minute=0, second=0, microsecond=0)
    hrs = [h for h in g.get("hours", []) if parse_t(h["t"]) >= start and h.get("qpf_mm") is not None]
    if len(hrs) < 24 or (age is not None and age > 72):
        return None
    rows = ""
    for h, lab in ((6, "Next 6 hours"), (12, "Next 12 hours"), (24, "Next 24 hours"), (48, "Next 48 hours"), (72, "Next 72 hours"), (168, "Next 7 days")):
        if len(hrs) >= h * 0.9:
            rows += tr([lab, "%.2f in" % (sum(x["qpf_mm"] for x in hrs[:h]) / 25.4)], right=(1,))
    if not rows:
        return None
    upd = esc(tzl(parse_t(g["updated"]), G["zone"])) if g.get("updated") else "time not stated"
    return block("forecast_rain_totals", "Forecast rain totals", "official", table(["Window", "Forecast rain"], rows, right=(1,)),
                 "Source: National Weather Service gridpoint quantitative precipitation forecast at the gauge location, updated %s. A forecast, not a measurement." % upd, "nws", amber=(age is not None and age > 12))


def b_atlas14(G):
    a = G["rec"].get("atlas14")
    if not a or not a.get("rows"):
        return None
    want = [2, 10, 25, 100]
    ix = [a["ari"].index(w) for w in want if w in a["ari"]]
    if not ix:
        return None
    rows = "".join(tr([esc(d)] + ["%.2f in" % v[i] for i in ix], right=tuple(range(1, len(ix) + 1))) for d, v in a["rows"].items())
    return block("rainfall_frequency", "Rainfall frequency at the gauge location", "hist", table(["Duration"] + ["%d-year" % a["ari"][i] for i in ix], rows, right=tuple(range(1, len(ix) + 1))),
                 "Source: NOAA Atlas 14 point precipitation frequency estimates (partial duration series, depth in inches) for the gauge location, fetched %s. A %d-year value is the depth expected once every %d years on average." % (esc(tzl(parse_t(a["fetched_at"]), G["zone"])), want[0], want[0]), "hdsc")


def b_drought(G):
    d = G["rec"].get("usdm")
    if not d or not d.get("rows"):
        return None
    cur = d["rows"][0]
    if (G["ldate"] - datetime.date.fromisoformat(cur[0])).days > 21:
        return None
    prev = d["rows"][1] if len(d["rows"]) > 1 else None
    rows = ""
    for lab, i in DROUGHT:
        rows += tr([esc(lab), "%.1f%%" % cur[i], ("%.1f%%" % prev[i]) if prev else "–"], right=(1, 2))
    return block("drought_monitor", "Drought Monitor, %s County" % esc(str(d.get("county") or "").replace(" County", "")), "official",
                 table(["Category", "Share of county area, week of %s" % fdate(cur[0]), "Previous week"], rows, right=(1, 2)),
                 "Source: U.S. Drought Monitor weekly county statistics (National Drought Mitigation Center, USDA, NOAA), map date %s, fetched %s." % (fdate(cur[0]), esc(tzl(parse_t(d["fetched_at"]), G["zone"]))), "usdm")


def b_attains(G):
    a = G["rec"].get("attains")
    if not a or not a.get("units"):
        return None
    rows = "".join(tr([esc(u.get("name") or u["id"]), esc(u.get("status") or "–"), esc(u.get("category") or "–"), esc(u.get("impaired") or "–"), esc(u.get("tmdl") or "–"), esc(u.get("cycle") or "–"),
                       ('<a href="%s" rel="noopener">EPA report</a>' % esc(u["link"])) if str(u.get("link") or "").startswith("https://") else "–"]) for u in a["units"])
    return block("water_quality_assessment", "State water quality assessments near the gauge", "agency", "<p>This is the state's Clean Water Act designated-use assessment (a multi-year regulatory status), not a current swim, bacteria or recreation advisory.</p>" + table(["Assessment unit", "Overall status", "Category", "Impaired", "Has a cleanup plan (TMDL)", "Assessment cycle", "Report"], rows),
                 "Source: EPA ATTAINS assessment units within about a quarter mile of the gauge, as reported by the state, fetched %s. Values are the state's assessment, quoted." % esc(tzl(parse_t(a["fetched_at"]), G["zone"])), "epa")


def b_offline(G):
    """Shown at the top of every tab when the newest USGS flow reading is more than 24 hours old (up to 30 days); beyond that the gauge is no longer rebuilt."""
    if not G.get("offline"):
        return None
    days = G["age_min"] / 1440
    return block("gauge_not_reporting", "Gauge not reporting", "live",
                 "<p>The newest USGS flow reading for this gauge is from %s, %.1f days ago. The values on this page are that last reading.</p>" % (esc(tzl(G["lt"], G["zone"])), days),
                 "Source: USGS Water Data API, checked %s. The page updates when USGS publishes a newer reading." % esc(tzl(parse_t(G["rec"]["usgs"]["fetched_at"]), G["zone"])), "usgs", amber=True)
