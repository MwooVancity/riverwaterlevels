"""SVG chart helpers and the chart blocks."""
import statistics, os, re, json, math, collections, hashlib, datetime, zoneinfo
from lib.common import *
from lib.core import *


# ---------------------------------------------------------------- blocks (each returns a block dict or None)
def river_svg(series, zone, W, Hh, fs, nx, cls, what="Flow in cfs"):
    """Several gauges' last 7 days on one time axis (river hub, owner 2026-11-11 option 2): series = [(label, [(datetime, cfs), ...])], up to 4 lines.
    Same axis rules as the gauge chart: round ticks, labels in the gauge's own time zone. ponytail: linear axis; a log axis if a river's gauges differ 100-fold."""
    pts = [p for _, s in series for p in s]
    t0, t1 = min(p[0] for p in pts), max(p[0] for p in pts)
    span = (t1 - t0).total_seconds() or 1
    vmin, vmax, ticks = nice_ticks(min(p[1] for p in pts), max(p[1] for p in pts))
    L, B = (56, 30) if W > 500 else (46, 28)
    L = axis_l(L, fs, ticks)
    X = lambda t: L + (t - t0).total_seconds() / span * (W - L - 14)
    Y = lambda v: 12 + (1 - (v - vmin) / ((vmax - vmin) or 1)) * (Hh - B - 12)
    grid = "".join('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--line)"/><text x="%d" y="%.1f" font-size="%d" fill="var(--mut)" text-anchor="end">%s</text>' % (
        L, W - 14, Y(tv), Y(tv), L - 6, Y(tv) + 4, fs, tf(tv, ticks)) for tv in ticks)
    xl = "".join('<text x="%.1f" y="%d" font-size="%d" fill="var(--mut)" text-anchor="%s">%s</text>' % (
        X(t0 + datetime.timedelta(seconds=span * k / (nx - 1))), Hh - 8, fs, "start" if k == 0 else "end" if k == nx - 1 else "middle",
        (t0 + datetime.timedelta(seconds=span * k / (nx - 1))).astimezone(zone).strftime("%b %d").replace(" 0", " ")) for k in range(nx))
    lines = "".join('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.2"%s/>' % (
        " ".join("%.1f,%.1f" % (X(t), Y(v)) for t, v in s), YCOL[n], (' stroke-dasharray="%s"' % YDASH[n]) if YDASH[n] else "") for n, (_, s) in enumerate(series))
    return '<svg class="%s" viewBox="0 0 %d %d" width="100%%" role="img" aria-label="%s at %d gauges over the last 7 days">%s%s%s</svg>' % (cls, W, Hh, what, len(series), grid, xl, lines)


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


def tap_attr(pts, X, Y, label):
    """PLAN 6 (2026-11-03 gap research: "what was it at 7 am"): the drawn readings, each with its own value and time, so a tap shows the
    nearest real reading (never an interpolated one). pts = [(time, value, suffix)]; TAP_JS formats the time in the gauge's zone."""
    return ' data-tap="%s"' % "|".join("%.0f;%.0f;%s%s;%d" % (X(t), Y(v), label(v), s, t.timestamp()) for t, v, s in pts)


# One script for every chart with data-tap: tap or drag shows the nearest drawn reading and its local time; vertical scrolling stays the page's.
TAP_JS = ('<script>(function(){var f=new Intl.DateTimeFormat("en-US",{timeZone:"@TZ@",month:"short",day:"numeric",hour:"numeric",minute:"2-digit",timeZoneName:"short"}),N="http://www.w3.org/2000/svg";'
          'document.querySelectorAll("svg[data-tap]").forEach(function(s){var P=s.getAttribute("data-tap").split("|").map(function(r){return r.split(";")}),W=s.viewBox.baseVal.width,c=document.createElementNS(N,"circle"),t=document.createElementNS(N,"text");'
          'c.setAttribute("r","7");c.setAttribute("fill","none");c.setAttribute("stroke","var(--ink)");c.setAttribute("stroke-width","2");c.style.display="none";'
          't.setAttribute("font-size","14");t.setAttribute("font-weight","600");t.setAttribute("fill","var(--ink)");t.setAttribute("stroke","var(--card)");t.setAttribute("stroke-width","4");t.setAttribute("paint-order","stroke");t.setAttribute("y","28");'
          's.appendChild(c);s.appendChild(t);s.style.touchAction="pan-y";s.style.cursor="crosshair";'
          'function mv(e){var r=s.getBoundingClientRect(),x=(e.clientX-r.left)/r.width*W,b=P[0],d=1e9;P.forEach(function(p){var k=Math.abs(p[0]-x);if(k<d){d=k;b=p}});'
          'c.setAttribute("cx",b[0]);c.setAttribute("cy",b[1]);c.style.display="";t.textContent=b[2]+", "+f.format(new Date(b[3]*1e3));var e2=b[0]>W/2;t.setAttribute("text-anchor",e2?"end":"start");t.setAttribute("x",e2?b[0]-10:+b[0]+10)}'
          's.addEventListener("pointerdown",mv);s.addEventListener("pointermove",function(e){if(e.buttons||e.pointerType=="mouse")mv(e)})})})();</script>')


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
            if rr and None not in (rr[4], rr[5], rr[6]):  # practice 2026-11-08 (Big Hole at Wisdom): a USGS stats row with a blank percentile crashed the chart and held the page
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
    return ('<svg class="%s" viewBox="0 0 %d %d" width="100%%" role="img" aria-label="Flow in cfs over the last 7 days with the 25th to 75th percentile band"%s>%s%s%s%s'
           '<circle cx="%.1f" cy="%.1f" r="5" fill="var(--accent)"/></svg>' % (cls, W, Hh, tap_attr([(t, v, "") for t, v, _ in thin], X, Y, lambda v: fmtc(v) + " cfs"), "".join(band), grid, xl, line, X(lt), Y(G["lv"])))



def day_axis(t0, t1, zone, X, nx, fs, Hh, L, W):
    """Date labels at local midnight, the same on every time chart (hater r5: flow and gage charts put "Oct 24" in different places)."""
    mids, d0 = [], t0.astimezone(zone).date() + datetime.timedelta(days=1)
    while datetime.datetime.combine(d0, datetime.time(0), zone) < t1:
        mids.append(datetime.datetime.combine(d0, datetime.time(0), zone))
        d0 += datetime.timedelta(days=1)
    xl = ""
    for m in mids[::max(1, -(-len(mids) // nx))]:  # one label per local midnight (every second one on a phone)
        x_ = X(m)
        if x_ - 2.4 * fs < L - 4 or x_ + 2.4 * fs > W - 4:  # "Oct 22" is about 4.8 font sizes wide
            continue
        xl += '<text x="%.1f" y="%d" font-size="%d" fill="var(--mut)" text-anchor="middle">%s</text>' % (x_, Hh - 8, fs, md(m))
    return xl


def b_flow_chart(G):
    if G.get("stage_only") or not G["fl"]:  # no flow readings (tide tables): no chart
        return None
    svg = _chart_svg(G, 760, 250, 11, 7, "cw") + _chart_svg(G, 340, 250, 12, 4, "cn")
    return block("flow_chart", "Last 7 days", "live", svg + (LEG if G["rec"].get("stats") else ""), "Source: USGS Water Data API (continuous values), observed to %s. Flow in cfs." % esc(G["obs"]), "usgs")  # the band is explained by LEG under the chart; the note said it again


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
            val, note = "–", "Partial day (%d of about %d readings)" % (len(vs), round(exp_n))
        rows += tr([d.strftime("%b %d, %Y").replace(" 0", " "), val, note], right=(1,))
    if not rows:
        return None
    return block("daily_readings", "Daily mean flow", "live", table(["Date (gauge-local)", "Mean flow", "Note"], rows, right=(1,)),
                 "Source: USGS Water Data API (daily values where USGS has published them; otherwise the mean of continuous readings on that gauge-local date, shown only with at least 80% of expected readings).", "usgs")


LEG = '<p class="src leg">Shaded: the typical range for each date (25th to 75th percentile of past years) &middot; dashed line: the median.</p>'  # hater 2026-10-27: band and dashed line had no visible label on a phone


def b_record(G):
    r = G["rec"].get("record")
    if not r:
        return None
    pk = r["peak"]
    end = fdate(r["as_of"]) if r.get("as_of") else "the last published day"
    cards = [card("Highest daily average, 7 days to %s" % end, "%s <small>cfs</small>" % fmtc(pk["value"]), "%s (USGS daily averages lag a day or two)" % fdate(pk["date"]))]
    if r.get("prior"):
        cards.append(card("Last day as high as this week's %s cfs (daily average)" % fmtc(pk["value"]), esc(fdate(r["prior"]["date"])), "daily average %s cfs, %s before" % (fmtc(r["prior"]["value"]), human_span(r["prior"]["days_before"]))))
    else:
        cards.append(card("Last day as high as this week's %s cfs (daily average)" % fmtc(pk["value"]), "Highest since records began", "record begins %d" % r["first_year"]))
    if r.get("last_p90"):
        cards.append(card("Last day in the top 10% of flows (above the 90th percentile) before this week", fdate(r["last_p90"]["date"]), "%s before this week's high" % human_span(r["last_p90"]["days_before"])))  # audit 2026-11-10 #11: "Before these 7 days, last day flow was..." read backwards
    if r.get("above_p75"):
        cards.append(card("Days above the 75th percentile", "%s of %s" % (format(r["above_p75"]["n"], ","), format(r["above_p75"]["of"], ",")), "last %s days" % format(r["above_p75"]["of"], ",")))
    if r.get("month"):
        m = r["month"]
        cards.append(card("%s 1 to %d, average daily flow" % (m["month"][:3], m["dom"]), "%s <small>cfs</small>" % fmtc(m["mean"]), (("%s highest of the %d years with USGS daily values for these dates" % (ordinal(m["rank"]), m["years"])) if m["rank"] <= m["years"] / 2 else ("%s lowest of the %d years with USGS daily values for these dates" % (ordinal(m["years"] - m["rank"] + 1), m["years"])))))
    return block("record_comparison", "Compared with this gauge’s record", "hist", rail(cards, "Compared with this gauge’s record"),
                 "Source: USGS daily mean flows (Water Data API), %d to %d (%s days), data through %s. Percentiles are USGS daily statistics. Recent days are provisional." % (
                     r["first_year"], r["last_year"], "{:,}".format(r["n_days"]), fdate(r["as_of"])), "usgs")


def _multi_svg(ser, years, asof, span, W, Hh, fs, nx, cls, what="Daily mean flow in cfs"):
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
    return '<svg class="%s" viewBox="0 0 %d %d" width="100%%" role="img" aria-label="%s for the same %d-day window in %d years">%s%s%s</svg>' % (cls, W, Hh, what, span, len(years), grid, xl, lines)


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
    pc = m.get("pc", "00060")
    lake = pc != "00060"
    if lake and pc != G.get("lake"):  # PLAN 0i: the history must be in the same code and datum as the level the page shows, never another
        return None
    what, unit, val = ("Daily mean lake level in ft", "ft", lambda x: "%.2f ft" % x) if lake else ("Daily mean flow in cfs", "cfs", lambda x: "%s cfs" % fmtc(x))
    svg = _multi_svg(ser, years, asof, span, 760, 260, 11, 6, "cw", what) + _multi_svg(ser, years, asof, span, 340, 260, 12, 4, "cn", what)
    legend = '<p class="legend">%s</p>' % " &nbsp; ".join('<b><span style="color:%s" aria-hidden="true">%s</span>&nbsp;%s</b>' % (YCOL[n], "&#9473;" if not YDASH[n] else "&#9548;", esc(y)) for n, y in enumerate(years))
    rows = ""
    for y in years:
        v = [x for x in ser[y] if x is not None]
        if len(v) >= 0.8 * span:
            rows += tr([esc(y), val(sum(v) / len(v)), val(max(v))], right=(1, 2))
    start = asof - datetime.timedelta(days=span - 1)
    src = ("Source: USGS daily mean lake elevation (Water Data API, parameter %s, %s). " % (esc(pc), esc(LAKE_DATUM.get(pc, "the gauge's own datum"))) if lake else "Source: USGS daily mean flows (Water Data API). ")
    return block("multi_year", "The same %d days in earlier years" % span, "hist", svg + legend + table(["Year", "Mean level" if lake else "Mean flow", "Highest day"], rows, right=(1, 2)),
                 src + "Each line is the %d days from %s to %s, shifted to the same calendar dates in earlier years; gaps are days without a published value. Recent days are provisional." % (
                     span, md(start), md(asof)), "usgs")


def b_like_today(G, near=0.25, ahead=7, least=5):
    """What happened next in earlier years that were like today (owner 2026-11-12, slabcalc idea: our own calculation from the gauge's record).
    Years whose daily mean on today's date was within 25% of today's flow; their flow 7 days later. History, never a forecast; flow only (a lake's level is not compared in %)."""
    m = G["rec"].get("multiyear") or {}
    nx, F = m.get("next") or {}, G.get("basis")
    if m.get("pc", "00060") != "00060" or G.get("lake") or G.get("coast") or G.get("osc") or G.get("offline") or G.get("stage_only") or not nx.get("years") or not F or F <= 0:
        return None
    s0 = datetime.date.fromisoformat(nx["start"])
    off = (G["ldate"] - s0).days
    if not 0 <= off <= len(next(iter(nx["years"].values()))) - 1 - ahead:
        return None  # the weekly window no longer holds today and a week on
    have = [(y, s[off], s[off + ahead]) for y, s in nx["years"].items() if s[off] is not None and s[off + ahead] is not None]
    like = sorted([h for h in have if abs(h[1] - F) <= near * F], reverse=True)
    if len(like) < least or len(have) < 10:
        return None  # too few years to say anything
    moves = collections.Counter("about the same" if abs(b - a) < FLAT_CFS or abs(b - a) / a * 100 < FLAT_PCT else "higher" if b > a else "lower" for _, a, b in like)
    pct = statistics.median((b - a) / a * 100 for _, a, b in like)
    d0 = G["ldate"]
    d7 = d0 + datetime.timedelta(days=ahead)
    lead = ("<p><b>In %d of %d years on record, the flow on %s was within %d%% of today's %s cfs. A week later it was higher in %d, about the same in %d and lower in %d of them (median change %+.0f%%).</b> "
            "This is what happened in those years, not a forecast: rain, snowmelt and dam releases differ every year.</p>") % (
        len(like), len(have), md(d0), round(near * 100), fmtc(F), moves["higher"], moves["about the same"], moves["lower"], pct)
    rows = "".join(tr([esc(y), "%s cfs" % fmtc(a), "%s cfs" % fmtc(b), "%+.0f%%" % ((b - a) / a * 100)], right=(1, 2, 3)) for y, a, b in like)
    return block("like_today", "What happened next in years like this one", "hist", lead + table(["Year", md(d0), md(d7), "Change"], rows, right=(1, 2, 3)),
                 "Source: USGS daily mean flows (Water Data API), %d years with both dates published. Our calculation: years whose daily mean on %s was within %d%% of today's %s, and their daily mean %d days later. "
                 "'About the same' is a change under %d%% or under %d cfs, as on the rest of the page." % (len(have), md(d0), round(near * 100), "24 h average" if G.get("basis_mean") else "latest reading", ahead, FLAT_PCT, FLAT_CFS), "usgs")


def b_floods(G):
    """PLAN 19d: the gauge's largest floods inside its daily record, day by day (collect.big_floods). The peak is USGS's instantaneous annual peak; the days are daily means, which run lower."""
    f = (G["rec"].get("floods") or {}).get("floods") or []
    if not f or G.get("lake") or G.get("coast"):
        return None
    rows = ""
    for x in f:
        d0, half = datetime.date.fromisoformat(x["date"]), x["peak"] / 2
        days = [(datetime.date.fromisoformat(t), v) for t, v in x["days"] if v is not None]
        top = max(days, key=lambda dv: dv[1])
        above = sum(1 for _, v in days if v >= half)
        back = next((t for t, v in days if t > d0 and v < half), None)
        rows += tr([fdate(x["date"]), "%s cfs" % fmtc(x["peak"]), "%s cfs on %s" % (fmtc(top[1]), md(top[0])), str(above),
                    md(back) if back else "not by %s" % md(days[-1][0])], right=(1, 2, 3))
    big = f[0]
    lead = "<p><b>The largest flood in this gauge's daily record peaked at %s cfs on %s.</b> For each of the biggest floods: how high the daily flow ran and how long it stayed above half the peak.</p>" % (fmtc(big["peak"]), fdate(big["date"]))
    return block("big_floods", "The biggest floods here, day by day", "hist", lead + table(["Flood", "Peak (USGS)", "Highest daily mean", "Days above half the peak", "Back under half the peak"], rows, right=(1, 2, 3)),
                 "Source: USGS annual peak streamflow (instantaneous peaks; peaks USGS codes as historic, a daily mean, a dam failure, a lower or upper bound, or with an unknown date are left out) and USGS daily mean flows (Water Data API), from 3 days before to 10 days after each peak; "
                 "floods before the daily record began are skipped. A daily mean averages the whole day, so it runs below the instantaneous peak. Two peaks within 14 days count as one flood. Days are counted inside that 14-day window.", "usgs")


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
        return ", ".join(ms) if ms else ("none of the months with data" + ("" if len(mf) == 12 else " (no data for %s)" % ", ".join(MONTHS[m - 1][:3] for m in range(1, 13) if m not in mf)))
    # Lakebrief comparison 2026-10-21: the thresholds a swimmer or paddler reads against this table, quoted from the guide, no verdict of ours
    guide = table(["Typical water temperature", "National Center for Cold Water Safety category (quoted)", "Months in that band here"], tr(["<b class=\"qual\">Under 50&deg;F (coldest)</b>", "Below 50&deg;F: colder than the guide's coldest listed band; the guide already calls 50 to 60&deg;F 'Very Dangerous / Immediately Life-threatening'. NWS: cold-water shock and loss of swimming ability within minutes of immersion", under(-100, 50)]) + tr(["50 to 60&deg;F", "&ldquo;Very Dangerous / Immediately Life-threatening&rdquo;", under(50, 60)]) + tr(["60 to 70&deg;F", "&ldquo;Dangerous&rdquo;", under(60, 70)]) + tr(["70&deg;F and above", "above the guide's caution line: it says to treat any water below 70&deg;F with caution", under(70, 200)]))
    _who = '<p class="src">Measured by this gauge\u2019s own water temperature sensor, %s to %s%s.</p>' % (esc(str(w.get("first_year") or "?")), esc(str(w.get("last_year") or "?")), (" (%s years with data; it no longer reports)" % esc(str(w["years"]))) if w.get("years") and str(w.get("last_year")) < str(G["ldate"].year - 1) and not series(G["rec"], "00010") else "")  # phone review 2026-11-07 (Champlain): "no longer reports" beside a live sensor reading  # CI 2026-10-29: years are ints in the cloud cache
    return block("water_temp_months", "Typical water temperature by month", "hist", _who + '<div class="fcs mgrid">%s</div>' % cards + "<h3>Cold-water guidance against these months</h3>" + guide,
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
        rows += tr([esc(x["name"]) + '<div class="src">%d mi away%s</div>' % (round(km_mi(x["km"])), (", %s ft up" % fmt(x["elev_ft"])) if x.get("elev_ft") else ""), "%.1f in" % x["swe_in"], ("%s of %.1f in" % (pct, med)) if med else "–", fdate(x["date"])], right=(1, 2))  # readable at a glance: 4 columns (was 7)
    from lib import ui
    zero = [x for x in st if not x.get("median_in")]
    st_b = [x for x in st if x.get("median_in")]  # full review: a zero or missing median drew an empty bar and a median tick
    sb = "".join('<p class="src">%s, %d mi: %.1f in of snow water now; %s.</p>' % (esc(x["name"]), round(km_mi(x["km"])), x["swe_in"], "median for this date 0.0 in" if x.get("median_in") == 0 else "no median published") for x in zero)
    sb = (ui.bars([("%s, %d mi" % (esc(x["name"]), round(km_mi(x["km"]))), (x["swe_in"] / x["median_in"] * 100) if x.get("median_in") else None, ("%.0f%% of median (%.1f in, median %.1f in)" % (x["swe_in"] / x["median_in"] * 100, x["swe_in"], x["median_in"])) if x.get("median_in") else ("%.1f in; median 0.0 in" % x["swe_in"] if x.get("median_in") == 0 else "%.1f in, no median" % x["swe_in"])) for x in st_b], 150, mark=100) if st_b else "") + sb
    return block("snowpack", "Snow water equivalent at nearby SNOTEL stations", "obs", sb + more("Each station: distance, elevation and date", table(["Station", "Snow water now", "Median for this date", "Date"], rows, right=(1, 2))),
                 "Source: USDA Natural Resources Conservation Service SNOTEL stations within 37 miles of the gauge (AWDB web service), fetched %s. Provisional data; stations may not drain to this gauge." % esc(tzl(parse_t(s["fetched_at"]), G["zone"])), "nrcs")
