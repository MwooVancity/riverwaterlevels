"""SVG chart helpers and the chart blocks."""
import statistics, os, re, json, math, collections, hashlib, datetime, zoneinfo
from lib.common import *
from lib.core import *


# ---------------------------------------------------------------- blocks (each returns a block dict or None)
def axis_l(L, fs, ticks):
    """Left margin wide enough for the widest tick label (hater w3: "400,000" clipped)."""
    return max(L, 10 + int(0.6 * fs * max(len(tf(tv, ticks)) for tv in ticks)))


def tf(v, ticks=None):
    """Axis tick label: zero is 0, not 0.00. With the tick list, use the fewest decimals that show every tick exactly (12.5 is never printed as 12)."""
    if abs(v) < 1e-9:
        return "0"
    if ticks and len(ticks) > 1:
        d = next((k for k in (0, 1, 2, 3) if all(abs(t - round(t, k)) < 1e-9 for t in ticks)), 3)
        if d > 0 or abs(v) < 100:
            return "{:,.{d}f}".format(v, d=d)
    return fmt(v)


def nice_ticks(lo, hi, n=5):
    """Round axis: returns (axis_min, axis_max, ticks) on a 1/2/2.5/5 x 10^k step that covers [lo, hi]."""
    lo, hi = float(lo), float(hi)
    if hi <= lo:
        hi = lo + 1.0
    raw = (hi - lo) / (n - 1)
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    a = math.floor(lo / step) * step
    b = math.ceil(hi / step) * step
    ticks, v = [], a
    while v <= b + step * 1e-9:
        ticks.append(round(v, 10))
        v += step
    return a, b, ticks


def steps_med(pts):
    st = sorted((pts[i][0] - pts[i - 1][0]).total_seconds() for i in range(1, len(pts)))
    return st[len(st) // 2] if st else None


def _chart_svg(G, W, Hh, fs, nx, cls):
    fl, zone, lt = G["fl"], G["zone"], G["lt"]
    t1 = lt
    t0 = max(fl[0][0], lt - datetime.timedelta(days=7))
    pts = [x for x in fl if x[0] >= t0]
    L, B = (56, 30) if W > 500 else (46, 28)
    vals = [v for _, v, _ in pts]
    bp = []
    if G["stats"]:
        for d in sorted({x[0].astimezone(zone).date() for x in pts}):
            rr = G["stats"].get(d.isoformat()[5:10])
            if rr:
                bp.append((d, rr[4], rr[6], rr[5]))
        for d, a, c, m in bp:
            vals += [a, c]
    vmin, vmax, ticks = nice_ticks(min(vals), max(vals))
    L = axis_l(L, fs, ticks)
    span = (t1 - t0).total_seconds() or 1
    X = lambda t: L + (t - t0).total_seconds() / span * (W - L - 14)
    Y = lambda v: 12 + (1 - (v - vmin) / ((vmax - vmin) or 1)) * (Hh - B - 12)
    band = []
    if bp:
        def at(d):
            if d == bp[0][0]: return t0
            if d == bp[-1][0]: return t1
            return min(t1, max(t0, datetime.datetime.combine(d, datetime.time(12), zone)))
        up = " ".join("%.1f,%.1f" % (X(at(d)), Y(c)) for d, a, c, m in bp)
        dn = " ".join("%.1f,%.1f" % (X(at(d)), Y(a)) for d, a, c, m in reversed(bp))
        md = " ".join("%.1f,%.1f" % (X(at(d)), Y(m)) for d, a, c, m in bp)
        band = ['<polygon points="%s %s" fill="var(--soft)"/>' % (up, dn), '<polyline points="%s" fill="none" stroke="var(--mut)" stroke-dasharray="4 4"/>' % md]
    step = max(1, len(pts) // 220)
    thin = [pts[i] for i in sorted(set(range(0, len(pts), step)) | {len(pts) - 1, max(range(len(pts)), key=lambda i: pts[i][1]), min(range(len(pts)), key=lambda i: pts[i][1])})]  # the peak card's reading is on the line
    gap_s = max(10800, 4 * (steps_med(pts) or 900))
    segs, cur = [], [thin[0]]
    for a_, b_ in zip(thin, thin[1:]):
        if (b_[0] - a_[0]).total_seconds() > gap_s:
            segs.append(cur)
            cur = []
        cur.append(b_)
    segs.append(cur)
    line = "".join('<polyline points="%s" fill="none" stroke="var(--accent)" stroke-width="2.4"/>' % " ".join("%.1f,%.1f" % (X(t), Y(v)) for t, v, _ in sg_) for sg_ in segs if len(sg_) > 1)
    grid = "".join('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--line)"/><text x="%d" y="%.1f" font-size="%d" fill="var(--mut)" text-anchor="end">%s</text>' % (L, W - 14, Y(tv), Y(tv), L - 6, Y(tv) + 4, fs, tf(tv, ticks)) for tv in ticks) + '<text x="%d" y="10" font-size="%d" fill="var(--mut)">cfs</text>' % (L + 4, fs)  # the unit once, top-left: "12,000 cfs" on the top tick overflowed the margin and showed ",000 cfs" (hater 2026-10-27)
    xl = day_axis(t0, t1, zone, X, nx, fs, Hh, L, W)
    return ('<svg class="%s" viewBox="0 0 %d %d" width="100%%" role="img" aria-label="Flow in cfs over the last 7 days with the 25th to 75th percentile band">%s%s%s%s'
           '<circle cx="%.1f" cy="%.1f" r="5" fill="var(--accent)"/></svg>' % (cls, W, Hh, "".join(band), grid, xl, line, X(lt), Y(G["lv"])))



def day_axis(t0, t1, zone, X, nx, fs, Hh, L, W):
    """Date labels at local midnight, the same on every time chart (hater r5: flow and gage charts put "Oct 24" in different places)."""
    mids, d0 = [], t0.astimezone(zone).date() + datetime.timedelta(days=1)
    while datetime.datetime.combine(d0, datetime.time(0), zone) < t1:
        mids.append(datetime.datetime.combine(d0, datetime.time(0), zone))
        d0 += datetime.timedelta(days=1)
    xl = ""
    for m in mids[::max(1, -(-len(mids) // nx))]:  # one label per local midnight (every second one on a phone)
        x_ = X(m)
        xl += '<text x="%.1f" y="%d" font-size="%d" fill="var(--mut)" text-anchor="%s">%s</text>' % (x_, Hh - 8, fs, "start" if x_ < L + 16 else "end" if x_ > W - 30 else "middle", m.strftime("%b %d").replace(" 0", " "))
    return xl


def b_flow_chart(G):
    svg = _chart_svg(G, 760, 250, 11, 7, "cw") + _chart_svg(G, 340, 250, 12, 4, "cn")
    return block("flow_chart", "Last 7 days", "live", svg + (LEG if G["rec"].get("stats") else ""), "Source: USGS Water Data API (continuous values), observed to %s.%s Flow in cfs." % (esc(G["obs"]), " Shaded band: 25th to 75th percentile of USGS daily statistics for each date; dashed: median." if G["rec"].get("stats") else ""), "usgs")


def b_daily(G):
    fl, zone = G["fl"], G["zone"]
    steps = sorted((fl[i][0] - fl[i - 1][0]).total_seconds() for i in range(1, len(fl)))
    exp_n = 86400 / ((steps[len(steps) // 2] if steps else 900) or 900)
    official = {r_[0]: r_[1] for r_ in ((G["rec"].get("year") or {}).get("rows") or [])}
    by = collections.OrderedDict()
    for t, v, _ in fl:
        by.setdefault(t.astimezone(zone).date(), []).append(v)
    rows, n_off = "", 0
    for d, vs in reversed(list(by.items())):
        full = len(vs) >= 0.8 * exp_n
        o = official.get(d.isoformat())
        if o is not None:
            n_off += 1
            val, note = fmtc(o) + " cfs", ""
        elif full:
            val, note = fmtc(sum(vs) / len(vs)) + " cfs", "Mean of readings, not yet published by USGS"
        else:
            val, note = "–", "Partial day"
        rows += tr([d.strftime("%b %d, %Y").replace(" 0", " "), val, note], right=(1,))
    return block("daily_readings", "Daily mean flow", "live", table(["Date (gauge-local)", "Mean flow", "Note"], rows, right=(1,)),
                 "Source: USGS Water Data API (daily values where USGS has published them; otherwise the mean of continuous readings on that gauge-local date, shown only with at least 80% of expected readings).", "usgs")


LEG = '<p class="src leg">Shaded: the normal range for each date (25th to 75th percentile of past years) &middot; dashed line: the median.</p>'  # hater 2026-10-27: band and dashed line had no visible label on a phone


def b_record(G):
    r = G["rec"].get("record")
    if not r:
        return None
    pk = r["peak"]
    end = fdate(r["as_of"]) if r.get("as_of") else "the last published day"
    cards = [card("Highest daily mean, 7 days to %s" % end, "%s <small>cfs</small>" % fmtc(pk["value"]), "%s (USGS daily means lag a day or two)" % fdate(pk["date"]))]
    if r.get("prior"):
        cards.append(card("Last day as high as this week's %s cfs" % fmtc(pk["value"]), esc(fdate(r["prior"]["date"])), "daily mean %s cfs, %s before" % (fmtc(r["prior"]["value"]), human_span(r["prior"]["days_before"]))))
    else:
        cards.append(card("Last day as high as this week's %s cfs" % fmtc(pk["value"]), "None on record", "record begins %d" % r["first_year"]))
    if r.get("last_p90"):
        cards.append(card("Before these 7 days, last day above the 90th percentile", fdate(r["last_p90"]["date"]), "%s before that 7-day high" % human_span(r["last_p90"]["days_before"])))
    if r.get("above_p75"):
        cards.append(card("Days above the 75th percentile", "%s of %s" % (format(r["above_p75"]["n"], ","), format(r["above_p75"]["of"], ",")), "last %s days" % format(r["above_p75"]["of"], ",")))
    if r.get("month"):
        m = r["month"]
        cards.append(card("%s 1 to %d, mean flow" % (m["month"][:3], m["dom"]), "%s <small>cfs</small>" % fmtc(m["mean"]), (("%s highest of the %d years with USGS daily values for these dates" % (ordinal(m["rank"]), m["years"])) if m["rank"] <= m["years"] / 2 else ("%s lowest of the %d years with USGS daily values for these dates" % (ordinal(m["years"] - m["rank"] + 1), m["years"])))))
    return block("record_comparison", "Compared with this gauge’s record", "hist", rail(cards, "Compared with this gauge’s record"),
                 "Source: USGS daily mean flows (Water Data API), %d to %d (%s days), data through %s. Percentiles are USGS daily statistics. Recent days are provisional." % (
                     r["first_year"], r["last_year"], "{:,}".format(r["n_days"]), fdate(r["as_of"])), "usgs")


def _multi_svg(ser, years, asof, span, W, Hh, fs, nx, cls):
    L, B = (56, 30) if W > 500 else (46, 28)
    vals = [v for y in years for v in ser[y] if v is not None]
    vmin, vmax, ticks = nice_ticks(min(vals), max(vals))
    L = axis_l(L, fs, ticks)
    X = lambda i: L + i / (span - 1) * (W - L - 14)
    Y = lambda v: 12 + (1 - (v - vmin) / ((vmax - vmin) or 1)) * (Hh - B - 12)
    grid = "".join('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--line)"/><text x="%d" y="%.1f" font-size="%d" fill="var(--mut)" text-anchor="end">%s</text>' % (
        L, W - 14, Y(tv), Y(tv), L - 6, Y(tv) + 4, fs, tf(tv, ticks)) for tv in ticks)
    start = asof - datetime.timedelta(days=span - 1)
    xl = ""
    for k in range(nx):
        i = round((span - 1) * k / (nx - 1))
        xl += '<text x="%.1f" y="%d" font-size="%d" fill="var(--mut)" text-anchor="%s">%s</text>' % (X(i), Hh - 8, fs, "start" if k == 0 else "end" if k == nx - 1 else "middle", (start + datetime.timedelta(days=i)).strftime("%b %d").replace(" 0", " "))
    lines = ""
    for n, y in reversed(list(enumerate(years))):
        seg, segs = [], []
        for i, v in enumerate(ser[y]):
            if v is None:
                if seg:
                    segs.append(seg)
                seg = []
            else:
                seg.append("%.1f,%.1f" % (X(i), Y(v)))
        if seg:
            segs.append(seg)
        for s in segs:
            lines += '<polyline points="%s" fill="none" stroke="%s" stroke-width="%s"%s/>' % (" ".join(s), YCOL[n], "2.8" if n == 0 else "1.8", (' stroke-dasharray="%s"' % YDASH[n]) if YDASH[n] else "")
    return '<svg class="%s" viewBox="0 0 %d %d" width="100%%" role="img" aria-label="Daily mean flow in cfs for the same %d-day window in %d years">%s%s%s</svg>' % (cls, W, Hh, span, len(years), grid, xl, lines)


def b_multiyear(G):
    m = G["rec"].get("multiyear")
    if not m:
        return None
    ser, span = m["series"], m["span"]
    years = [y for y in sorted(ser, reverse=True) if any(x is not None for x in ser[y])]  # a year with no published value draws nothing
    if not years:
        return None
    asof = datetime.date.fromisoformat(m["as_of"])
    if (G["ldate"] - asof).days > 10:
        return None
    svg = _multi_svg(ser, years, asof, span, 760, 260, 11, 6, "cw") + _multi_svg(ser, years, asof, span, 340, 260, 12, 4, "cn")
    legend = '<p class="legend">%s</p>' % " &nbsp; ".join('<b><span style="color:%s" aria-hidden="true">%s</span>&nbsp;%s</b>' % (YCOL[n], "&#9473;" if not YDASH[n] else "&#9548;", esc(y)) for n, y in enumerate(years))
    rows = ""
    for y in years:
        v = [x for x in ser[y] if x is not None]
        if len(v) >= 0.8 * span:
            rows += tr([esc(y), "%s cfs" % fmtc(sum(v) / len(v)), "%s cfs" % fmtc(max(v))], right=(1, 2))
    start = asof - datetime.timedelta(days=span - 1)
    return block("multi_year", "The same %d days in earlier years" % span, "hist", svg + legend + table(["Year", "Mean flow", "Highest day"], rows, right=(1, 2)),
                 "Source: USGS daily mean flows (Water Data API). Each line is the %d days from %s to %s, shifted to the same calendar dates in earlier years; gaps are days without a published value. Recent days are provisional." % (
                     span, start.strftime("%b %d").replace(" 0", " "), asof.strftime("%b %d").replace(" 0", " ")), "usgs")


def b_peaks(G):
    p = G["rec"].get("peaks")
    rows = [r for r in (p or {}).get("rows", []) if r[1] is not None]
    if len(rows) < 5:
        return None
    top = "".join(tr([fdate(r[0]), "%s cfs" % fmtc(r[1]), ("%.2f ft" % r[2]) if r[2] is not None else "–"], right=(1, 2)) for r in sorted(rows, key=lambda r: -r[1])[:10])
    recent = "".join(tr([fdate(r[0]), "%s cfs" % fmtc(r[1]), ("%.2f ft" % r[2]) if r[2] is not None else "–"], right=(1, 2)) for r in sorted(rows, key=lambda r: r[0], reverse=True)[:5])
    heads = ["Date", "Peak flow", "Gage height at peak"]
    dec = {}
    for r in rows:
        dec.setdefault(r[0][:3] + "0s", []).append(r[1])
    drows = "".join(tr([d, str(len(v)), "%s cfs" % fmtc(sorted(v)[len(v) // 2] if len(v) % 2 else (sorted(v)[len(v) // 2 - 1] + sorted(v)[len(v) // 2]) / 2), "%s cfs" % fmtc(max(v))], right=(1, 2, 3)) for d, v in sorted(dec.items()) if len(v) >= 5)
    by_decade = ("<h3>Median annual peak by decade (calendar year of the peak date)</h3>" + table(["Decade", "Peaks on file", "Median peak", "Largest peak"], drows, right=(1, 2, 3))) if drows else ""
    return block("annual_peaks", "Largest annual peaks", "hist", "<h3>Ten largest peaks of record</h3>" + table(heads, top, right=(1, 2)) + "<h3>Five most recent annual peaks</h3>" + table(heads, recent, right=(1, 2)) + by_decade,
                 "Source: USGS annual peak streamflow (Water Data API), %d annual peaks, %s to %s. A water year's peak is its highest instantaneous flow. Gage height at older peaks can be on a different datum. Decades with fewer than 5 peaks are left out." % (len(rows), rows[0][0][:4], rows[-1][0][:4]), "usgs")


def b_wtemp(G):
    w = G["rec"].get("wtemp")
    if not w or not w.get("months"):
        return None
    w = dict(w, months={m: v for m, v in w["months"].items() if isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v)})  # a malformed month is left out, never the block
    if not w["months"]:
        return None
    cards = "".join('<div class="fc"><div>%s</div><b>%.0f&deg;F</b><div class="legend">%s days%s</div></div>' % (MONTHS[int(m) - 1], c * 9 / 5 + 32, format(round(n), ","), " (few)" if n < 150 else "") for m, (c, n) in sorted(w["months"].items(), key=lambda x: int(x[0])))
    mf = {int(m): c * 9 / 5 + 32 for m, (c, n) in w["months"].items()}
    def under(lo, hi):
        ms = [("<b>%s (this month)</b>" if m == G["ldate"].month else "%s") % MONTHS[m - 1][:3] for m in sorted(mf) if lo <= round(mf[m]) < hi]  # the row for today is marked; banded on the rounded value shown (full review)
        return ", ".join(ms) if ms else "none"
    # Lakebrief comparison 2026-10-21: the thresholds a swimmer or paddler reads against this table, quoted from the guide, no verdict of ours
    guide = table(["Typical water temperature", "National Center for Cold Water Safety category (quoted)", "Months in that band here"], tr(["Under 50&deg;F", "colder than the guide's coldest band (50 to 60&deg;F, &ldquo;Very Dangerous / Immediately Life-threatening&rdquo;); NWS: cold-water shock and loss of swimming ability within minutes of immersion", under(-100, 50)]) + tr(["50 to 60&deg;F", "&ldquo;Very Dangerous / Immediately Life-threatening&rdquo;", under(50, 60)]) + tr(["60 to 70&deg;F", "&ldquo;Dangerous&rdquo;", under(60, 70)]) + tr(["70&deg;F and above", "above the guide's caution line: it says to treat any water below 70&deg;F with caution", under(70, 200)]))
    return block("water_temp_months", "Typical water temperature by month", "hist", '<div class="fcs mgrid">%s</div>' % cards + "<h3>Cold-water guidance against these months</h3>" + guide,
                 "Source: USGS daily mean water temperature (Water Data API), %s to %s, mean of all published daily values in each calendar month (days counted under each month; (few) means fewer than 150 daily values). Categories quoted from the <a href=\"https://www.coldwatersafety.org/water-temperature-safety-guide\" rel=\"noopener\">National Center for Cold Water Safety water temperature safety guide</a>; a monthly mean says nothing about a given day." % (esc(w["first_year"]), esc(w["last_year"])), "usgs")


def b_snotel(G):
    s = G["rec"].get("snotel") or {}
    st = [x for x in s.get("stations", []) if (G["ldate"] - datetime.date.fromisoformat(x["date"])).days <= 5]
    if not st:
        return None
    rows = ""
    for x in st:
        med = x.get("median_in")
        pct = ("%.0f%%" % (x["swe_in"] / med * 100)) if med else "–"
        rows += tr([esc(x["name"]), "%d mi" % round(x["km"] * 0.621371), ("%s ft" % fmt(x["elev_ft"])) if x.get("elev_ft") else "–", "%.1f in" % x["swe_in"], ("%.1f in" % med) if med is not None else "–", pct, fdate(x["date"])], right=(1, 2, 3, 4, 5))
    from lib import ui
    zero = [x for x in st if not x.get("median_in")]
    st_b = [x for x in st if x.get("median_in")]  # full review: a zero or missing median drew an empty bar and a median tick
    sb = "".join('<p class="src">%s: %.1f in of snow water now; %s.</p>' % (esc(x["name"]), x["swe_in"], "median for this date 0.0 in" if x.get("median_in") == 0 else "no median published") for x in zero)
    sb = (ui.bars([("%s, %d mi" % (esc(x["name"]), round(x["km"] * 0.621371)), (x["swe_in"] / x["median_in"] * 100) if x.get("median_in") else None, ("%.0f%% of median (%.1f in, median %.1f in)" % (x["swe_in"] / x["median_in"] * 100, x["swe_in"], x["median_in"])) if x.get("median_in") else ("%.1f in; median 0.0 in" % x["swe_in"] if x.get("median_in") == 0 else "%.1f in, no median" % x["swe_in"])) for x in st_b], 150, mark=100) if st_b else "") + sb
    return block("snowpack", "Snow water equivalent at nearby SNOTEL stations", "obs", sb + more("Each station: distance, elevation and date", table(["Station", "Distance", "Elevation", "Snow water now", "Median for date", "Of median", "Date"], rows, right=(1, 2, 3, 4, 5), hide=(1, 2))),
                 "Source: USDA Natural Resources Conservation Service SNOTEL stations within 37 miles of the gauge (AWDB web service), fetched %s. Provisional data; stations may not drain to this gauge." % esc(tzl(parse_t(s["fetched_at"]), G["zone"])), "nrcs")
