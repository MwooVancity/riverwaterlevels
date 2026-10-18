"""Block registry and page shell. A page is an ordered list of block functions per tab; a block returns a dict or None (None = no heading, no source line, nothing).
Visible text is a source value with unit and time, a label from this file, or a verbatim source string (escaped). No composed sentences.
"""
import os, re, json, math, collections, hashlib, datetime, zoneinfo
from lib.common import *

SOURCES = {s["id"]: s for s in json.load(open(os.path.join(DATA, "sources.json"), encoding="utf-8"))["sources"]}
CSS = open(os.path.join(ROOT, "templates", "site.css"), encoding="utf-8").read()
LABELS = {"00010": "Water temperature", "00300": "Dissolved oxygen", "63680": "Turbidity", "00400": "pH", "00095": "Specific conductance", "99133": "Nitrate plus nitrite"}
UNITS = {"degC": "°C", "deg C": "°C", "mg/l": "mg/L", "_FNU": "FNU", "uS/cm": "µS/cm", "pH Units": "pH units", "ft3/s": "cfs"}
TAGS = {"agency": "Agency data", "live": "Live gauge", "official": "Official NWS", "model": "Model guidance", "hist": "Historical record", "map": "Mapped layer", "obs": "Weather station", "calc": "Computed"}
PADMAN = {"USFS": "US Forest Service", "NPS": "National Park Service", "BLM": "Bureau of Land Management", "FWS": "US Fish and Wildlife Service", "SDNR": "State natural resources agency",
          "SFW": "State fish and wildlife agency", "SPR": "State parks", "SLB": "State land board", "LOC": "Local government", "CITY": "City", "CNTY": "County", "NGO": "Nonprofit", "PVT": "Private",
          "TRIB": "Tribal", "REG": "Regional or county agency", "UNK": "Unknown manager", "UNKL": "Unknown manager", "JNT": "Joint management", "DOD": "Department of Defense", "USACE": "Army Corps of Engineers"}
ACCESS = {"OA": "Open access", "RA": "Restricted access", "XA": "Closed", "UK": "Access unknown"}
DISCLAIMER = ("Percentile is estimated from USGS published daily percentiles. Readings are provisional until USGS reviews them. Not endorsed by USGS, NOAA or the National Weather Service. "
              "Not for navigation or safety-of-life decisions; the absence of an alert is not a statement that conditions are safe.")


IGNORED_ALERTS = {"Test Message", "Administrative Message"}


ADS = False  # the empty ADVERTISEMENT slots render only when an ad network is live
PREVIEW = False  # build.py --preview: show blocks whose source is not cleared, into dist_preview/ (review only, never published)


class CriticalFail(Exception):
    pass


def tzl(dt, zone, date=True):
    d = dt.astimezone(zone)
    s = d.strftime("%b %d, %I:%M %p %Z") if date else d.strftime("%I:%M %p %Z")
    s = s.replace(" 0", " ", 1).lstrip("0").replace("  ", " ")
    return s.replace(" ", "\u00a0").replace(",\u00a0", ", ")  # a long date wraps after the comma, never inside the time


def age_text(dt, now):
    m = int((now - dt).total_seconds() / 60)
    return "%d min" % m if m < 180 else ("%.0f h" % (m / 60) if m < 2880 else "%d d" % (m // 1440))


def hours_old(iso_s, now):
    try:
        return (now - parse_t(iso_s)).total_seconds() / 3600
    except Exception:
        return None


def series(rec, code):
    out = []
    for r in rec["usgs"]["rows"]:
        if r["parameter_code"] == code:
            try:
                out.append((parse_t(r["time"]), float(r["value"]), r))
            except (TypeError, ValueError):
                pass
    out.sort(key=lambda x: x[0])
    return out


def oscillating(fl):
    """True when the last 48 h of flow holds 3 or more separate peaks of at least 20% of the mean (tidal or other sub-daily cycles): a 24 h change then compares two phases of a cycle."""
    t1 = fl[-1][0]
    hrs = collections.OrderedDict()
    for t, v, _ in fl:
        if t >= t1 - datetime.timedelta(hours=48):
            hrs.setdefault(int(t.timestamp() // 3600), []).append(v)
    h = [sum(v) / len(v) for _, v in sorted(hrs.items())]
    if len(h) < 40:
        return False
    mean = sum(h) / len(h)
    if mean <= 0:
        return False
    peaks = 0
    for i in range(4, len(h) - 4):
        if h[i] >= max(h[i - 4:i + 5]) and h[i] - min(h[i - 4:i]) >= 0.2 * mean and h[i] - min(h[i + 1:i + 5]) >= 0.2 * mean:
            peaks += 1
    return peaks >= 3


USGS_TZ = {("PST", "Y"): "America/Los_Angeles", ("MST", "Y"): "America/Denver", ("MST", "N"): "America/Phoenix", ("CST", "Y"): "America/Chicago", ("EST", "Y"): "America/New_York",
           ("AKST", "Y"): "America/Anchorage", ("HST", "N"): "Pacific/Honolulu", ("HST", "Y"): "America/Adak", ("AST", "N"): "America/Puerto_Rico"}


def usgs_tz(rec):
    """The time zone USGS publishes for the monitoring location (the NWS point zone can differ on a zone boundary)."""
    loc = ((rec.get("meta") or {}).get("loc")) or {}
    return USGS_TZ.get((loc.get("time_zone_abbreviation"), loc.get("uses_daylight_savings")))


def ctx(site, row, rec, now):
    """Everything derived once per gauge; blocks only read this."""
    tzname = usgs_tz(rec) or rec.get("tz") or "UTC"
    zone = zoneinfo.ZoneInfo(tzname)
    fl, sg = series(rec, "00060"), series(rec, "00065")
    if not fl:
        raise CriticalFail("no flow series")
    lt, lv, lrow = fl[-1]
    age_min = (now - lt).total_seconds() / 60
    if age_min > 30 * 24 * 60:
        raise CriticalFail("latest flow older than 30 days (%.0f d)" % (age_min / 1440))
    stats = rec.get("stats")
    ldate = lt.astimezone(zone).date()
    mmdd = ldate.isoformat()[5:10]
    srow = stats.get(mmdd) if stats else None
    win = [x for x in fl if x[0] > lt - datetime.timedelta(hours=24)]
    basis, method = lv, "latest reading vs USGS daily percentiles for calendar date %s" % mmdd
    if len(win) >= 4:
        steps = sorted((win[i][0] - win[i - 1][0]).total_seconds() for i in range(1, len(win)))
        step = steps[len(steps) // 2] or 900
        if len(win) >= 0.8 * 86400 / step and (win[-1][0] - win[0][0]).total_seconds() >= 20 * 3600:
            basis = sum(x[1] for x in win) / len(win)
            method = "trailing 24 h mean vs USGS daily percentiles for calendar date %s" % mmdd
    p = interp_pct(srow, basis) if srow else None
    ago = min(fl, key=lambda x: abs((x[0] - (lt - datetime.timedelta(hours=24))).total_seconds()))
    steps = sorted((fl[i][0] - fl[i - 1][0]).total_seconds() for i in range(max(1, len(fl) - 200), len(fl)))
    tol = max(1200, 0.6 * (steps[len(steps) // 2] if steps else 900))
    osc = oscillating(fl)
    chg = (lv - ago[1]) / ago[1] * 100 if (not osc) and abs((ago[0] - (lt - datetime.timedelta(hours=24))).total_seconds()) <= tol and ago[1] > 0 else None
    return {"site": site, "row": row, "rec": rec, "now": now, "zone": zone, "tzname": tzname, "fl": fl, "sg": sg, "lt": lt, "lv": lv, "lrow": lrow, "age_min": age_min, "stats": stats, "ldate": ldate,
            "srow": srow, "p": p, "method": method, "chg": chg, "obs": tzl(lt, zone), "river": row["river"], "place": row["place"], "st": row["state"],
            "lat": rec["lat"], "lon": rec["lon"], "has_forecast": bool(((rec.get("nwps") or {}).get("forecast") or {}).get("points")), "offline": age_min > 24 * 60, "osc": osc, "basis": basis, "basis_mean": method.startswith("trailing")}


def block(bid, heading, tag, body, source, src_id, as_of=None, amber=False):
    return {"id": bid, "heading": heading, "tag": tag, "body": body, "source": source, "src_id": src_id, "as_of": as_of, "amber": amber}


LIMIT_TEXT = {"alerts": "3 h", "air_obs": "3 h", "rain_totals": "6 h", "river_forecast": "24 h"}


def render_block(b):
    amber = (' <span class="tag amber">Older than %s</span>' % LIMIT_TEXT.get(b["id"], "12 h")) if b.get("amber") else ""
    return ('<section class="card blk" id="%s"><h2>%s <span class="tag t-%s">%s</span>%s<a class="pl" href="#%s" aria-label="Link to this section">#</a></h2>%s<p class="src">%s</p></section>' % (b["id"], esc(b["heading"]), b["tag"], esc(TAGS[b["tag"]]), amber, b["id"], b["body"], b["source"]))


def table(heads, rows, right=(), hide=()):
    th = "".join('<th scope="col"%s>%s</th>' % (' class="r"' if i in right else "", esc(h)) for i, h in enumerate(heads))
    names = ["hc%d" % i for i in hide]
    if len(heads) - len(hide) >= 4:  # on a phone a wide table becomes stacked rows (label: value) instead of columns cut off at the edge
        names.append("stk")

        def add(chunk):
            n = [-1]

            def sub(m):
                n[0] += 1
                return '<td data-l="%s"%s>' % (esc(heads[n[0]]) if n[0] < len(heads) else "", m.group(1) or "")
            return re.sub(r'<td( class="r")?>', sub, chunk)
        rows = "</tr>".join(add(c) for c in rows.split("</tr>"))
    cls = (' class="%s"' % " ".join(names)) if names else ""
    return '<div class="scroll"><table%s><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (cls, th, rows)


def tr(cells, right=()):
    return "<tr>%s</tr>" % "".join('<td%s>%s</td>' % (' class="r"' if i in right else "", c) for i, c in enumerate(cells))


# ---------------------------------------------------------------- hero
def hero(G, pages=None):
    from lib import ui
    c = b3.conditions(G, pages)
    p, srow = G["p"], G["srow"]
    pv = ("below 5th" if p == -1 else "above 95th" if p == 101 else ordinal(p)) if p is not None else "–"
    if p is not None and srow:
        pct_med = "%.0f%% of the median" % (G["basis"] / srow[5] * 100) if srow[5] else ""
        what = ("the trailing 24 h mean (%s cfs)" % fmt(G["basis"])) if G["basis_mean"] else ("the %s reading" % tzl(G["lt"], G["zone"], date=False))
        cap = "Estimated from %s against %d years of USGS daily statistics for %s." % (what, srow[0], G["ldate"].strftime("%b %d"))
    else:
        pct_med, cap = "", "No percentile: no published statistics for this date."
    sg = G["sg"]
    stage_txt = ("%.2f" % sg[-1][1]) if sg else "–"
    stage_unit = UNITS.get(sg[-1][2].get("unit_of_measure"), sg[-1][2].get("unit_of_measure") or "ft") if sg else "ft"
    chg = G["chg"]
    d24 = G["lt"] - datetime.timedelta(hours=24)
    tiles = ui.tile("flow", "flow", "Latest flow", '<span data-live="flow">%s</span> <small><abbr title="cubic feet per second">cfs</abbr></small>' % fmt(G["lv"]), ui.spark([x[1] for x in G["fl"] if x[0] >= d24]) + '<small>Observed <span data-live="flowobs">%s</span></small>' % esc(G["obs"]))
    tiles += ui.tile("stage", "stage", "Gage height", '<span data-live="stage">%s</span> <small>%s</small>' % (stage_txt, esc(stage_unit)),
                     (ui.spark([x[1] for x in sg if x[0] >= d24]) if sg else "") + '<small>%s</small>' % (('Observed <span data-live="stageobs">' + esc(tzl(sg[-1][0], G["zone"])) + "</span>") if sg else "No stage reported"))
    if p is None:
        word, plain = "–", ""
    else:
        word = "Very low" if p == -1 else "Very high" if p == 101 else "Below normal" if p < 25 else "Above normal" if p > 75 else "Normal range"
        yrs = srow[0] if srow else 0
        on = G["ldate"].strftime("%b %d")
        plain = ("Lower than 95%% or more of the %d years on record for %s." % (yrs, on) if p == -1 else
                 "Higher than 95%% or more of the %d years on record for %s." % (yrs, on) if p == 101 else
                 "Higher than %d%% of the %d years on record for %s." % (round(p), yrs, on))
        cap += " That is the %s percentile." % pv if p not in (-1, 101) else ""
    tiles += ui.tile("norm", "map", "Compared with past years", word,
                     ('<small class="nt">%s</small>' % esc(plain) if plain else "") + ui.dial(p) + ui.dial_legend() + ('<small class="nt">%s</small>' % pct_med if pct_med else "") + '<small id="pcap">%s</small>' % esc(cap), "wide")
    if G["osc"]:
        v24 = [x[1] for x in G["fl"] if x[0] > G["lt"] - datetime.timedelta(hours=24)]
        tiles += ui.tile("trend", "steady", "24 h range", '<span class="rng">%s to %s</span> <small>cfs</small>' % (fmt(min(v24)), fmt(max(v24))), '<small id="ccap">Lowest to highest reading in 24 h (tidal cycle)</small>')
    else:
        if chg is None:
            tiles += ui.tile("trend", "steady", "24 h change", "–", '<small id="ccap">No reading 24 h earlier</small>')
        else:
            word, ico = ("Rising", "up") if chg > 5 else ("Falling", "down") if chg < -5 else ("Steady", "steady")
            parts = " &middot; ".join("%s%.1f%% in %d h" % ("+" if v >= 0 else "", v, h) for h, v in sorted(c["chg"].items()) if h in (1, 6))
            tiles += ui.tile("trend " + word.lower(), ico, "24 h change", '%s%.0f%% <small class="word">%s</small>' % ("+" if chg >= 0 else "", chg, word),
                             ('<small>%s</small>' % parts if parts else "") + '<small id="ccap">Flow 24 h earlier: %s cfs</small>' % fmt(G["lv"] / (1 + chg / 100)))
    if c["fc"]:
        tiles += ui.tile("fcst", "crest", "Forecast high", '%.1f <small>ft</small>' % c["fc"]["v"], '<small>%s &middot; NWS point %s</small>' % (esc(c["fc"]["t"]), esc(c["fc"]["lid"])))
    if c["alerts"] is not None and not c["alerts"]["n"]:  # with an active alert the banner above the tiles carries it
        al = c["alerts"]
        tiles += ui.tile("alrt " + ("on" if al["n"] else "off"), "bell", "NWS alerts", str(al["n"]), '<small>%s</small>' % (esc("; ".join(al["names"])) if al["n"] else "No alerts active here"))
    if c["wt"]:
        tiles += ui.tile("wtemp", "thermo", "Water temperature", '%.0f&deg;<small>F</small>' % c["wt"]["f"], '<small>USGS sensor, %s</small>' % esc(c["wt"]["t"]))
    if c["air"]:
        a = c["air"]
        tiles += ui.tile("air", "wind", "Air temperature", '%.0f<small>&deg;F</small>' % a["f"], '<small>%s</small>' % ((("wind calm, " if a["wind"] < 1 else "wind %.0f mph %s, " % (a["wind"], esc(a["dir"]))) if a["wind"] is not None else "") + ("gusts %.0f mph, " % a["gust"] if a["gust"] is not None else "")) + '<small>NWS station %s, %s</small>' % (esc(a["st"]), esc(a["t"])))
    if c["up"]:
        up = c["up"]
        tiles += ui.tile("upst", "up", "Upstream gauge now", '%s <small>cfs</small>' % fmt(up["flow"]), '<small><a href="%s">%s</a>%s</small>' % (up["url"], esc(up["name"]), (" &middot; measured lag about %d h" % up["lag"]) if up.get("lag") else ""))
    if c["rain"]:
        tiles += ui.tile("rain", "drop", "Rain, last 24 h", '%.2f <small>in</small>' % c["rain"]["in"], '<small>NWS RFC estimate%s</small>' % ((" to " + esc(c["rain"]["to"])) if c["rain"]["to"] else ""))
    st_ = sun_times(G["lat"], G["lon"], G["ldate"])
    if st_:
        tiles += ui.tile("sun", "sun", "Sunset today", esc(tzl(st_[1], G["zone"], date=False)), '<small>Sunrise %s &middot; computed from location and date</small>' % esc(tzl(st_[0], G["zone"], date=False)))
    ban = ui.banner(c["alerts"]["n"], esc("; ".join(c["alerts"]["names"]))) if c["alerts"] and c["alerts"]["n"] else ""
    return ban + '<div class="hero hero2" data-t="%s">%s</div>' % (iso(G["lt"]), tiles)


# ---------------------------------------------------------------- blocks (each returns a block dict or None)
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
    thin = pts[::step] + [pts[-1]]
    gap_s = max(10800, 4 * (steps_med(pts) or 900))
    segs, cur = [], [thin[0]]
    for a_, b_ in zip(thin, thin[1:]):
        if (b_[0] - a_[0]).total_seconds() > gap_s:
            segs.append(cur)
            cur = []
        cur.append(b_)
    segs.append(cur)
    line = "".join('<polyline points="%s" fill="none" stroke="var(--accent)" stroke-width="2.4"/>' % " ".join("%.1f,%.1f" % (X(t), Y(v)) for t, v, _ in sg_) for sg_ in segs if len(sg_) > 1)
    grid = "".join('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--line)"/><text x="%d" y="%.1f" font-size="%d" fill="var(--mut)" text-anchor="end">%s</text>' % (L, W - 14, Y(tv), Y(tv), L - 6, Y(tv) + 4, fs, tf(tv, ticks)) for tv in ticks)
    xl = ""
    for k in range(nx):
        tt = t0 + (t1 - t0) * k / (nx - 1)
        xl += '<text x="%.1f" y="%d" font-size="%d" fill="var(--mut)" text-anchor="%s">%s</text>' % (X(tt), Hh - 8, fs, "start" if k == 0 else "end" if k == nx - 1 else "middle", tt.astimezone(zone).strftime("%b %d").replace(" 0", " "))
    return ('<svg class="%s" viewBox="0 0 %d %d" width="100%%" role="img" aria-label="Flow in cfs over the last 7 days with the 25th to 75th percentile band">%s%s%s%s'
           '<circle cx="%.1f" cy="%.1f" r="5" fill="var(--accent)"/></svg>' % (cls, W, Hh, "".join(band), grid, xl, line, X(lt), Y(G["lv"])))


def b_flow_chart(G):
    svg = _chart_svg(G, 760, 250, 11, 7, "cw") + _chart_svg(G, 340, 250, 12, 4, "cn")
    return block("flow_chart", "Last 7 days", "live", svg, "Source: USGS Water Data API (continuous values), observed to %s. Shaded band: 25th to 75th percentile of USGS daily statistics for each date; dashed: median. Flow in cfs." % esc(G["obs"]), "usgs")


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
            val, note = fmt(o) + " cfs", ""
        elif full:
            val, note = fmt(sum(vs) / len(vs)) + " cfs", "Mean of readings, not yet published by USGS"
        else:
            val, note = "–", "Partial day"
        rows += tr([d.strftime("%b %d, %Y").replace(" 0", " "), val, note], right=(1,))
    return block("daily_readings", "Daily mean flow", "live", table(["Date (gauge-local)", "Mean flow", "Note"], rows, right=(1,)),
                 "Source: USGS Water Data API (daily values where USGS has published them; otherwise the mean of continuous readings on that gauge-local date, shown only with at least 80% of expected readings).", "usgs")


def human_span(days):
    if days < 45:
        return "%d day%s" % (days, "" if days == 1 else "s")
    if days < 730:
        return "%d months" % round(days / 30.4)
    return "%d years" % round(days / 365.25)


def fdate(iso_d):
    return datetime.date.fromisoformat(iso_d).strftime("%b %d, %Y").replace(" 0", " ")


def b_record(G):
    r = G["rec"].get("record")
    if not r:
        return None
    pk = r["peak"]
    rows = tr(["Peak daily flow, last 7 days", "%s cfs" % fmt(pk["value"]), fdate(pk["date"])], right=(1,))
    if r.get("prior"):
        rows += tr(["Last time, before the last 7 days, that daily flow was this high or higher", "%s cfs" % fmt(r["prior"]["value"]), "%s (%s earlier)" % (fdate(r["prior"]["date"]), human_span(r["prior"]["days_before"]))], right=(1,))
    else:
        rows += tr(["Last time, before the last 7 days, that daily flow was this high or higher", "None in record", "Record begins %d" % r["first_year"]], right=(1,))
    if r.get("last_p90"):
        rows += tr(["Last day above the 90th percentile for its date, before the last 7 days", fdate(r["last_p90"]["date"]), "%s earlier" % human_span(r["last_p90"]["days_before"])], right=(1,))
    if r.get("above_p75"):
        rows += tr(["Days above the 75th percentile for their date", "%d of %d" % (r["above_p75"]["n"], r["above_p75"]["of"]), "last %d days" % r["above_p75"]["of"]], right=(1,))
    if r.get("month"):
        m = r["month"]
        rows += tr(["%s 1 to %d, mean flow" % (m["month"], m["dom"]), "%s cfs" % fmt(m["mean"]), "rank %d highest of %d years" % (m["rank"], m["years"])], right=(1,))
    return block("record_comparison", "Compared with this gauge’s record", "hist", table(["Measure", "Value", "When or rank"], rows, right=(1,)),
                 "Source: USGS daily mean flows (Water Data API), %d to %d (%s days), data through %s, computed %s; method %s. Percentiles are USGS daily statistics. Recent days are provisional." % (
                     r["first_year"], r["last_year"], "{:,}".format(r["n_days"]), fdate(r["as_of"]), fdate(r["computed_at"][:10]), esc(r["method"])), "usgs")


def b_quality(G):
    rows = ""
    for code, lab in LABELS.items():
        s = series(G["rec"], code)
        if s:
            t, v, r = s[-1]
            unit = UNITS.get(r.get("unit_of_measure"), r.get("unit_of_measure") or "")
            shown = ("%.1f °F (%.1f °C)" % (v * 9 / 5 + 32, v)) if (code == "00010" and unit == "°C") else ("%s %s" % (fmt(v), esc(unit)))
            rows += tr([esc(lab), shown, esc(tzl(t, G["zone"]))], right=(1,))
    if not rows:
        return None
    return block("quality_sensors", "Water quality sensors", "live", table(["Measure", "Latest value", "Observed"], rows, right=(1,)), "Source: USGS Water Data API (continuous values). Values as reported by the gauge, provisional.", "usgs")


def b_related(G, pages):
    items = (G["rec"].get("related") or {}).get("items") or []
    rows = ""
    for x in items:
        pr = pages.get(x["site"])
        if not pr or not pr.get("_built"):
            continue
        lag = ("about %d h (r %.2f)" % (x["lag_h"], x["lag_r"])) if x.get("lag_h") else "–"
        rows += tr(['<a href="%s">%s</a>' % (pr["water_url"], esc(river_at(pr["river"], pr["place"]))), x["relation"].capitalize(), "%s cfs" % fmt(x["flow"]), esc(tzl(parse_t(x["time"]), G["zone"])), lag], right=(2,))
    if not rows:
        return None
    from lib import ui
    nodes = []
    for rel in ("upstream", "downstream"):
        if rel == "downstream":
            nodes.append({"name": "<span>This gauge</span>", "flow": "%s cfs" % fmt(G["lv"]), "sub": esc(G["obs"]), "cur": True})
        for x in items:
            pr = pages.get(x["site"])
            if x["relation"] == rel and pr and pr.get("_built"):
                nodes.append({"name": '<a href="%s">%s</a>' % (pr["water_url"], esc(river_at(pr["river"], pr["place"]))), "flow": "%s cfs" % fmt(x["flow"]),
                              "sub": x["relation"].capitalize() + " &middot; " + esc(tzl(parse_t(x["time"]), G["zone"])) + ((" &middot; lag about %d h" % x["lag_h"]) if x.get("lag_h") else ""), "cur": False})
    return block("related_gauges", "Upstream and downstream gauges", "live", ui.strip(nodes),
                 "Source: USGS NLDI river network and USGS Water Data API. Relation is along the NLDI main stem; only gauges on this site that report flow are listed. Observed lag is the shift, up to 72 h, that best matches hourly flow at the two gauges over the last 8 days (r = correlation, shown only at 0.85 or higher); it is empirical, not a travel time.", "usgs")


def b_flood_stages(G):
    n = G["rec"].get("nwps") or {}
    cats = n.get("categories") or {}
    if not cats:
        return None
    rows = "".join(tr([k.capitalize(), "%.1f ft" % cats[k]], right=(1,)) for k in ("action", "minor", "moderate", "major") if k in cats)
    return block("flood_stages", "Flood stages", "official", table(["Category", "Gage height (ft)"], rows, right=(1,)),
                 "Source: National Weather Service forecast point %s (%s), fetched %s. Compare with the gage height above; thresholds belong to that forecast point." % (esc(n.get("lid") or ""), esc(n.get("name") or ""), esc(tzl(parse_t(n["fetched_at"]), G["zone"]))), "nwps")


def b_river_forecast(G):
    n = G["rec"].get("nwps") or {}
    fc = n.get("forecast")
    if not fc or not fc.get("points"):
        return None
    age = hours_old(fc.get("issued"), G["now"]) if fc.get("issued") else None
    if age is not None and age > 72:
        return None
    kc = "kcfs" in (fc.get("secondary_units") or "").lower()
    rows = ""
    fut = [x for x in fc["points"] if parse_t(x["t"]) >= G["now"] - datetime.timedelta(hours=1)]
    if not fut:
        return None
    for p in fut[:28]:
        sec = p.get("secondary")
        flow = ("%s cfs" % fmt(sec * 1000 if kc else sec)) if isinstance(sec, (int, float)) and sec >= 0 else "–"
        rows += tr([esc(tzl(parse_t(p["t"]), G["zone"])), "%.1f %s" % (p["primary"], esc(fc.get("primary_units") or "ft")), flow], right=(1, 2))
    issued = esc(tzl(parse_t(fc["issued"]), G["zone"])) if fc.get("issued") else "time not stated"
    return block("river_forecast", "River forecast", "official", table(["Time (gauge-local)", "Gage height", "Flow"], rows, right=(1, 2)),
                 "Source: National Weather Service forecast point %s, issued %s. Official forecasts change as rain and releases change." % (esc(n.get("lid") or ""), issued), "nwps", amber=(age is not None and age > 24))


def b_nwm(G):
    if (G["rec"].get("nwps") or {}).get("forecast"):
        return None
    n = G["rec"].get("nwm") or {}
    pts = n.get("points") or []
    if len(pts) < 4:
        return None
    age = hours_old(n.get("reference_time"), G["now"]) if n.get("reference_time") else None
    if age is not None and age > 72:
        return None
    fut = [p for p in pts if parse_t(p["t"]) >= G["now"] - datetime.timedelta(hours=1)]
    if len(fut) < 4:
        return None
    rows = "".join(tr([esc(tzl(parse_t(p["t"]), G["zone"])), "%s cfs" % fmt(p["flow"])], right=(1,)) for p in fut[::3][:8])
    ref = esc(tzl(parse_t(n["reference_time"]), G["zone"])) if n.get("reference_time") else "time not stated"
    return block("nwm_guidance", "Model guidance", "model", table(["Time (gauge-local)", "Modelled flow"], rows, right=(1,)),
                 "Source: NOAA National Water Model, reach %s, run %s. Model guidance, not an official forecast and not a measurement." % (esc(str(n.get("comid"))), ref), "nwm", amber=(age is not None and age > 12))


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
    return block("rain_totals", "Recent rain at the gauge location", "official", wid + table(["Window and end time", "Rain"], rows, right=(1,)),
                 "Source: NWS River Forecast Center multisensor precipitation estimate, 4 km grid at the gauge location, fetched %s. Estimate, not a gauge at the stream. Each window is a separate NWS product with its own end time (hourly and daily products), so a longer window can end earlier than a shorter one and show less rain." % esc(tzl(parse_t(n["fetched_at"]), G["zone"])), "rfc", amber=(age is not None and age > 6))


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
    for p in per[:n_periods]:
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
    return block("hourly_forecast", "Hourly forecast, next 24 hours", "official", table(["Hour", "Temp", "Wind", "Rain chance", "Sky"], rows, right=(1, 3)),
                 "Source: National Weather Service hourly point forecast, updated %s." % esc(tzl(parse_t(n["hourly_updated"]), G["zone"])), "nws", amber=(age > 12))


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


def sun_times(lat, lon, d):
    jd0 = (datetime.datetime(d.year, d.month, d.day, tzinfo=datetime.timezone.utc).timestamp() / 86400) + 2440587.5
    n = math.ceil(jd0 - 2451545.0 + 0.0008)
    js = n + 0.0009 - lon / 360
    rad = math.radians
    M = (357.5291 + 0.98560028 * js) % 360
    C = 1.9148 * math.sin(rad(M)) + 0.02 * math.sin(rad(2 * M)) + 0.0003 * math.sin(rad(3 * M))
    lam = (M + C + 180 + 102.9372) % 360
    jt = 2451545.0 + js + 0.0053 * math.sin(rad(M)) - 0.0069 * math.sin(rad(2 * lam))
    dec = math.asin(math.sin(rad(lam)) * math.sin(rad(23.4397)))
    cw = (math.sin(rad(-0.833)) - math.sin(rad(lat)) * math.sin(dec)) / (math.cos(rad(lat)) * math.cos(dec))
    if cw < -1 or cw > 1:
        return None
    w = math.degrees(math.acos(cw))
    to = lambda J: datetime.datetime.fromtimestamp((J - 2440587.5) * 86400, datetime.timezone.utc)
    return to(jt - w / 360), to(jt + w / 360)


def b_sun(G):
    st = sun_times(G["lat"], G["lon"], G["ldate"])
    if not st:
        return None
    z = G["zone"]
    rows = tr(["Sunrise", esc(tzl(st[0], z, date=False))], right=(1,)) + tr(["Sunset", esc(tzl(st[1], z, date=False))], right=(1,))
    return block("sun", "Sun", "calc", table(["Event", "Time (gauge-local)"], rows, right=(1,)), "Source: computed from the gauge location and date %s. No external data." % G["ldate"].isoformat(), "usgs")


def area_short(s, n=6, county=None):
    parts = [p.strip() for p in s.split(";") if p.strip()]
    if county:
        c = county.lower().replace(" county", "").replace(" parish", "").strip()
        mine = [p for p in parts if p.lower() == c or p.lower().endswith(" " + c)]
        parts = mine + [p for p in parts if p not in mine]
    return s if len(parts) <= n and not county else "; ".join(parts[:n]) + (("; and %d more areas" % (len(parts) - n)) if len(parts) > n else "")


def b_alerts(G):
    n = G["rec"].get("nws") or {}
    al = n.get("alerts")
    if al:
        al = [a for a in al if (a.get("event") or "") not in IGNORED_ALERTS]  # NWS system test messages are not alerts
    zone = G["zone"]
    when = esc(tzl(parse_t(n["fetched_at"]), zone)) if n.get("fetched_at") else "time not stated"
    age = hours_old(n.get("fetched_at"), G["now"]) if n.get("fetched_at") else None
    if al is None:
        body = '<p>Alerts could not be loaded at the last fetch.</p>'
    elif not al:
        body = '<p>No active National Weather Service alerts were returned for this location. This is not a statement that conditions are safe.</p>'
    else:
        items = ""
        for a in al:
            ends = esc(tzl(parse_t(a["ends"] or a["expires"]), zone)) if (a.get("ends") or a.get("expires")) else "not stated"
            items += '<div class="alert sev-%s"><b>%s</b> &middot; %s &middot; %s<br>%s<br>Ends %s</div>' % ((a.get("severity") or "unknown").lower(), esc(a.get("event") or ""), esc(a.get("severity") or "severity not stated"), esc(area_short(a.get("areaDesc") or "", 6, (((G["rec"].get("meta") or {}).get("loc")) or {}).get("county_name")) + ((" (" + ", ".join(a["states"]) + ")") if a.get("states") else "")), esc(a.get("headline") or ""), ends)
        body = items
    return block("alerts", "Weather alerts", "official", body, "Source: National Weather Service alerts for the gauge location, fetched %s." % when, "nws", amber=(age is not None and age > 3))


def b_land(G):
    land = G["rec"].get("land")
    if not land or not land.get("rows"):
        return None
    rows = "".join(tr([esc(u), esc(PADMAN.get(m, m or "n/a")), esc(ACCESS.get(a, a or "n/a"))]) for u, m, a in land["rows"][:12])
    return block("public_land", "Public land at this gauge", "map", table(["Unit", "Managed by", "Public access"], rows),
                 "Source: USGS Protected Areas Database (PAD-US), within about half a mile of the gauge, downloaded %s. Mapped land is not proof of legal access." % fdate(land["downloaded"]), "padus")


# ---------------------------------------------------------------- final-form blocks
COMP = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
YCOL = ["var(--accent)", "#d9822b", "#2e9d6a", "#8a6bd1"]
YDASH = ["", "7 3", "2 3", "10 3 2 3"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def compass(d):
    return COMP[int((d % 360) / 22.5 + 0.5) % 16]


def tint(frac):
    return "color-mix(in srgb,var(--accent) %d%%,var(--card))" % round(max(0, min(1, frac)) * 55)


def _multi_svg(ser, years, asof, span, W, Hh, fs, nx, cls):
    L, B = (56, 30) if W > 500 else (46, 28)
    vals = [v for y in years for v in ser[y] if v is not None]
    vmin, vmax, ticks = nice_ticks(min(vals), max(vals))
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
    years = sorted(ser, reverse=True)
    asof = datetime.date.fromisoformat(m["as_of"])
    if (G["ldate"] - asof).days > 10:
        return None
    svg = _multi_svg(ser, years, asof, span, 760, 260, 11, 6, "cw") + _multi_svg(ser, years, asof, span, 340, 260, 12, 4, "cn")
    legend = '<p class="legend">%s</p>' % " &nbsp; ".join('<b><span style="color:%s" aria-hidden="true">%s</span>&nbsp;%s</b>' % (YCOL[n], "&#9473;" if not YDASH[n] else "&#9548;", esc(y)) for n, y in enumerate(years))
    rows = ""
    for y in years:
        v = [x for x in ser[y] if x is not None]
        if len(v) >= 0.8 * span:
            rows += tr([esc(y), "%s cfs" % fmt(sum(v) / len(v)), "%s cfs" % fmt(max(v))], right=(1, 2))
    start = asof - datetime.timedelta(days=span - 1)
    return block("multi_year", "The same %d days in earlier years" % span, "hist", svg + legend + table(["Year", "Mean flow", "Highest day"], rows, right=(1, 2)),
                 "Source: USGS daily mean flows (Water Data API). Each line is the %d days from %s to %s, shifted to the same calendar dates in earlier years; gaps are days without a published value. Recent days are provisional." % (
                     span, start.strftime("%b %d").replace(" 0", " "), asof.strftime("%b %d").replace(" 0", " ")), "usgs")


def b_peaks(G):
    p = G["rec"].get("peaks")
    rows = [r for r in (p or {}).get("rows", []) if r[1] is not None]
    if len(rows) < 5:
        return None
    top = "".join(tr([fdate(r[0]), "%s cfs" % fmt(r[1]), ("%.2f ft" % r[2]) if r[2] is not None else "–"], right=(1, 2)) for r in sorted(rows, key=lambda r: -r[1])[:10])
    recent = "".join(tr([fdate(r[0]), "%s cfs" % fmt(r[1]), ("%.2f ft" % r[2]) if r[2] is not None else "–"], right=(1, 2)) for r in sorted(rows, key=lambda r: r[0], reverse=True)[:5])
    heads = ["Date", "Peak flow", "Gage height at peak"]
    dec = {}
    for r in rows:
        dec.setdefault(r[0][:3] + "0s", []).append(r[1])
    drows = "".join(tr([d, str(len(v)), "%s cfs" % fmt(sorted(v)[len(v) // 2] if len(v) % 2 else (sorted(v)[len(v) // 2 - 1] + sorted(v)[len(v) // 2]) / 2), "%s cfs" % fmt(max(v))], right=(1, 2, 3)) for d, v in sorted(dec.items()) if len(v) >= 5)
    by_decade = ("<h3>Median annual peak by decade (calendar year of the peak date)</h3>" + table(["Decade", "Peaks on file", "Median peak", "Largest peak"], drows, right=(1, 2, 3))) if drows else ""
    return block("annual_peaks", "Largest annual peaks", "hist", "<h3>Ten largest peaks of record</h3>" + table(heads, top, right=(1, 2)) + "<h3>Five most recent annual peaks</h3>" + table(heads, recent, right=(1, 2)) + by_decade,
                 "Source: USGS annual peak streamflow (Water Data API), %d annual peaks, %s to %s. A water year's peak is its highest instantaneous flow. Gage height at older peaks can be on a different datum. Decades with fewer than 5 peaks are left out." % (len(rows), rows[0][0][:4], rows[-1][0][:4]), "usgs")


def b_wtemp(G):
    w = G["rec"].get("wtemp")
    if not w or not w.get("months"):
        return None
    cards = "".join('<div class="fc"><div>%s</div><b>%.0f&deg;F</b><div class="legend">%s days%s</div></div>' % (MONTHS[int(m) - 1], c * 9 / 5 + 32, fmt(n), " (few)" if n < 150 else "") for m, (c, n) in sorted(w["months"].items(), key=lambda x: int(x[0])))
    return block("water_temp_months", "Water temperature by month", "hist", '<div class="fcs">%s</div>' % cards,
                 "Source: USGS daily mean water temperature (parameter 00010, Water Data API), %s to %s, mean of all published daily values in each calendar month (days counted under each month; (few) means fewer than 150 daily values)." % (esc(w["first_year"]), esc(w["last_year"])), "usgs")


def crest_date(t, zone):
    if str(t).endswith("T00:00:00Z"):  # date-only value stored as midnight UTC: not a moment, so no zone shift
        return fdate(str(t)[:10])
    return fdate(parse_t(t).astimezone(zone).date().isoformat())


def b_crests(G):
    n = G["rec"].get("nwps") or {}
    cr = n.get("crests") or []
    if not cr:
        return None
    unit = (n.get("stage_units") or "ft").lower()
    rows = "".join(tr([crest_date(c["t"], G["zone"]) if c.get("t") else "–", "%.2f %s" % (c["stage"], esc(unit)), ("%s cfs" % fmt(c["flow"])) if isinstance(c.get("flow"), (int, float)) and c["flow"] > 0 else "–"], right=(1, 2)) for c in cr)
    return block("historic_crests", "Historic crests", "official", table(["Date", "Crest stage", "Flow"], rows, right=(1, 2)),
                 "Source: National Weather Service forecast point %s (%s), historic crests as published by the NWS; the NWS may have recorded them on an older gauge datum. The USGS annual peaks above are a separate record and can differ in date, flow and datum." % (esc(n.get("lid") or ""), esc(n.get("name") or "")), "nwps")


def b_impacts(G):
    n = G["rec"].get("nwps") or {}
    im = n.get("impacts") or []
    if not im:
        return None
    unit = (n.get("stage_units") or "ft").lower()
    rows = "".join(tr(["%.1f %s" % (i["stage"], esc(unit)), esc(i["statement"])], right=(0,)) for i in im)
    return block("flood_impacts", "Flood impacts by stage", "official", table(["Stage", "National Weather Service impact statement"], rows, right=(0,)),
                 "Source: National Weather Service forecast point %s (%s). Statements are quoted from the NWS and describe that forecast point." % (esc(n.get("lid") or ""), esc(n.get("name") or "")), "nwps")


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
        head += "<th>%s</th>" % (d.strftime("%a") if d.hour == 0 else "%d%s" % (d.hour % 12 or 12, "a" if d.hour < 12 else "p"))
    mph = lambda k: (lambda v: None if v is None else v * 0.621371)(k)
    spec = (("Temp &deg;F", lambda h: None if h.get("temp_c") is None else h["temp_c"] * 9 / 5 + 32, lambda v: (v - 20) / 90, "%.0f"),
            ("Wind mph", lambda h: mph(h.get("wind_kmh")), lambda v: v / 30, "%.0f"),
            ("Gust mph", lambda h: mph(h.get("gust_kmh")), lambda v: v / 40, "%.0f"),
            ("Direction", lambda h: h.get("dir"), None, None),
            ("Cloud %", lambda h: h.get("sky"), lambda v: v / 100, "%.0f"),
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
    return block("hourly_heatmap", "Hourly forecast, next 24 hours", "official", '<div class="scroll"><table class="hm"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (head, rows),
                 "Source: National Weather Service gridpoint forecast, updated %s; rain chance from the NWS hourly point forecast. Hours are gauge-local. Darker cells mean a higher value in that row." % upd, "nws", amber=(age is not None and age > 12))


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
    sb = ui.bars([(esc(x["name"]), (x["swe_in"] / x["median_in"] * 100) if x.get("median_in") else None, ("%.0f%% of median" % (x["swe_in"] / x["median_in"] * 100)) if x.get("median_in") else "%.1f in, no median" % x["swe_in"]) for x in st], 150, mark=100)
    return block("snowpack", "Snow water equivalent at nearby SNOTEL stations", "obs", sb + table(["Station", "Distance", "Elevation", "Snow water now", "Median for date", "Of median", "Date"], rows, right=(1, 2, 3, 4, 5), hide=(1, 2)),
                 "Source: USDA Natural Resources Conservation Service SNOTEL stations within 37 miles of the gauge (AWDB web service), fetched %s. Provisional data; stations may not drain to this gauge." % esc(tzl(parse_t(s["fetched_at"]), G["zone"])), "nrcs")


def b_cpc(G):
    rows = ""
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
        src_bits.append("%s for %s" % (name, span))
    if not rows:
        return None
    return block("cpc_outlook", "Temperature and precipitation outlooks", "official", table(["Outlook", "Period", "Variable", "Leaning", "Probability"], rows, right=(4,)),
                 "Source: NOAA Climate Prediction Center outlooks at the gauge location (%s), issued %s. A probability is the chance of the leaning category (above, near or below normal) for the whole period, not an amount." % ("; ".join(src_bits), iss.strftime("%b %d").replace(" 0", " ")), "cpc")


def b_map(G):
    lat, lon, R = G["lat"], G["lon"], 6378137.0
    half = 8000 / math.cos(math.radians(lat))
    cx, cy = R * math.radians(lon), R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    bbox = "%.0f,%.0f,%.0f,%.0f" % (cx - half, cy - half * 0.5625, cx + half, cy + half * 0.5625)
    src = "https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/export?bbox=%s&bboxSR=3857&imageSR=3857&size=640,360&format=png&f=image" % bbox
    return block("gauge_map", "Gauge location", "map", '<div class="mapimg"><img src="%s" alt="USGS topographic map centred on %s, about 10 miles across" width="640" height="360" loading="lazy"><i aria-hidden="true"></i></div>' % (src, esc(G["place"])),
                 "Source: Map services and data available from U.S. Geological Survey, National Geospatial Program (USGS Topo). Map about 10 miles across, centred on the gauge at %.4f, %.4f." % (lat, lon), "natmap")


# ---------------------------------------------------------------- tabs
TABS = {
    "dashboard": {"label": "Conditions", "title": "%s, %s: river level and flow", "desc": "%s, %s: current flow, gage height, how it compares with past years, alerts, history and flood record from USGS gauge %s.", "hero": True},
    "forecast": {"label": "Forecast", "title": "%s, %s: river forecast", "desc": "%s, %s: river forecast, rain, radar and weather forecast for USGS gauge %s.", "hero": False},
}


def b_official_links(G):
    """Where to go next: the source pages for this gauge, opened in a new tab."""
    n = G["rec"].get("nwps") or {}
    lid = n.get("lid")
    links = [("USGS page for this gauge", "https://waterdata.usgs.gov/monitoring-location/%s/" % G["site"]), ("USGS WaterAlert: text or email when this gauge crosses a level you choose", "https://waterdata.usgs.gov/nwis/wateralert")]
    if lid:
        links.append(("NWS river page for forecast point %s" % lid, "https://water.noaa.gov/gauges/%s" % lid))
    links.append(("NWS forecast for this location", "https://forecast.weather.gov/MapClick.php?lat=%.4f&lon=%.4f" % (G["lat"], G["lon"])))
    links.append(("NWS active alerts for this location", "https://alerts.weather.gov/search?point=%.4f,%.4f" % (G["lat"], G["lon"])))
    body = '<ul class="olinks">%s</ul>' % "".join('<li><a href="%s" rel="noopener" target="_blank">%s</a></li>' % (esc(h), esc(t)) for t, h in links)
    return block("official_links", "Official pages for this gauge", "agency", body, "Source: links to the agencies that publish the data on this page (USGS, NOAA National Weather Service); they open in a new tab.", "usgs")


def tab_blocks(tab, G, pages):
    if tab == "dashboard":  # one page per gauge: ordered by reader question (how high now, how fast, how unusual, what happened before, what is around it)
        return [b2.b_offline(G), b_alerts(G), b_flow_chart(G), b2.b_stage_chart(G), "AD", b2.b_rate(G), b3.b_rise(G), b3.b_month_chart(G), b3.b_year_chart(G), b_daily(G), b_multiyear(G),
                b_record(G), b_peaks(G), b3.b_stage_years(G), b3.b_floodfreq(G), b_crests(G), b3.b_field_meas(G), b3.b_storms(G), b3.b_declarations(G), b2.b_rating(G), b_snotel(G), b_wtemp(G), b_quality(G),
                b_related(G, pages), b3.b_nws_point(G, pages), b3.b_flood_outlook(G), b_impacts(G), b2.b_drought(G), b2.b_attains(G), b3.b_streamcat(G), b3.b_dams(G), b3.b_fema_zone(G),
                ((b_heatmap(G) or b_hourly(G)) if not G["has_forecast"] else None), b_radar(G), b_map(G), b_weather(G, 3), b_land(G), b_official_links(G), b2.b_about(G)]
    return [b2.b_offline(G), b_river_forecast(G), b_nwm(G), b2.b_nwm_medium(G), b2.b_noforecast(G), b_rain(G), b3.b_wpc(G), b3.b_acis(G), b2.b_qpf(G), b2.b_atlas14(G), b_cpc(G), b_heatmap(G) or b_hourly(G), b_weather(G), b_air(G), b_sun(G)]


def footer():
    return ('<footer><span>%s &middot; Data: USGS, NOAA, NWS.</span><span><a href="/about/">About</a> &middot; <a href="/data-sources/">Data sources</a> &middot; <a href="/disclaimer/">Disclaimer</a> &middot; '
            '<a href="/faq/">FAQ</a> &middot; <a href="/methodology/">Methodology</a> &middot; <a href="/privacy/">Privacy</a> &middot; <a href="/glossary/">Glossary</a> &middot; <a href="/status/">Data status</a></span></footer>' % esc(BRAND))


def og_tags(title, desc, url):
    return ('<meta property="og:type" content="website"><meta property="og:site_name" content="%s"><meta property="og:title" content="%s"><meta property="og:description" content="%s"><meta property="og:url" content="%s"><meta property="og:image" content="%s/og.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="River Water Levels: current flow, gage height and percentile for US river gauges"><meta name="twitter:card" content="summary_large_image">'
            % (esc(BRAND), esc(title), esc(desc), esc(url), SITE_URL))


def mk_title(base):
    full = base + " | " + BRAND
    return full if len(full) <= 62 else base


def humanize_iso(text):
    return re.sub(r"\d{4}-\d{2}-\d{2}", lambda m: fdate(m.group(0)), text)


def nav():
    return '<a class="skip" href="#main">Skip to content</a><div class="nav"><a class="brand" href="/"><span class="logo"></span>%s</a><span class="tabs"><a href="/">Rivers</a><a href="/about/">About</a></span><span class="ns"><input id="gq" type="search" placeholder="Find a river or place" aria-label="Find a river or place" autocomplete="off"><span id="gr" class="gr" hidden></span></span></div>' % esc(BRAND) + NAVSEARCH_JS


def sources_block(blocks, G):
    ids = []
    for b in blocks:
        for sid in [b["src_id"]] + list(b.get("also") or []):
            if sid not in ids:
                ids.append(sid)
    if "usgs" not in ids:
        ids.insert(0, "usgs")
    lis = ""
    for i in ids:
        s = SOURCES[i]
        lis += '<li>%s. <a href="%s" rel="noopener">Terms</a></li>' % (esc((s.get("credit") or s["name"]).rstrip(".")), esc(s["terms_url"]))
    stats_src = G["rec"].get("stats_source")
    return ('<div class="card" style="margin-top:14px"><h2>Sources and method</h2><ul>%s</ul><p class="src">%s</p><p class="src">Percentile method: %s.</p><p class="src">%s</p></div>' % (
        lis, esc(humanize_iso(stats_src) if stats_src else "USGS daily statistics: not available for this gauge."), esc(G["method"]), esc(DISCLAIMER)))


LIVE_JS = """<script>(function(){var ID="USGS-@SITE@",Z="@TZ@",hero=document.querySelector('.hero');if(!hero||!window.fetch)return;var snap=Date.parse(hero.getAttribute('data-t')),n=0;
function q(k){return document.querySelector('[data-live="'+k+'"]')}
function f(v){var a=Math.abs(v);return a>=100?Math.round(v).toLocaleString('en-US'):a>=10?v.toFixed(0):a<1?v.toFixed(2):v.toFixed(1)}
function lt(d){return d.toLocaleString('en-US',{timeZone:Z,month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'})}
function age(d){var m=Math.round((Date.now()-d)/60000);return m<180?m+' min':m<2880?Math.round(m/60)+' h':Math.round(m/1440)+' d'}
var ag=q('age');if(ag)ag.textContent=age(new Date(snap));
function run(){fetch('https://api.waterdata.usgs.gov/ogcapi/v0/collections/latest-continuous/items?monitoring_location_id='+ID+'&parameter_code=00060,00065&f=json').then(function(r){return r.json()}).then(function(j){var F=null,S=null;(j.features||[]).forEach(function(x){var p=x.properties,v=parseFloat(p.value);if(isNaN(v))return;if(p.parameter_code==='00060')F={v:v,t:new Date(p.time)};if(p.parameter_code==='00065')S={v:v,t:new Date(p.time)}});
if(F&&F.t.getTime()>=snap){q('flow').textContent=f(F.v);q('flowobs').textContent=lt(F.t);q('obs').textContent=lt(F.t);if(ag)ag.textContent=age(F.t);var st=q('stage'),so=q('stageobs');if(S&&st&&S.t.getTime()>=snap){st.textContent=S.v.toFixed(2);if(so)so.textContent=lt(S.t)}if(F.t.getTime()>snap){var nt=' Flow above is newer; percentile and change are as of '+lt(new Date(snap))+'.',pc=document.getElementById('pcap'),cc=document.getElementById('ccap');if(pc&&pc.getAttribute('data-n')!=='1'){pc.textContent+=nt;pc.setAttribute('data-n','1')}if(cc&&cc.getAttribute('data-n')!=='1'){cc.textContent+=nt;cc.setAttribute('data-n','1')}}}}).catch(function(){})}
run();var iv=setInterval(function(){if(++n>6)return clearInterval(iv);run()},600000)})();</script>"""
AGE_JS = """<script>(function(){var a=document.querySelector('[data-live="age"][data-t]');if(!a)return;var t=Date.parse(a.getAttribute('data-t'));function u(){var m=Math.round((Date.now()-t)/60000);a.textContent=m<180?m+' min':m<2880?Math.round(m/60)+' h':Math.round(m/1440)+' d'}u();setInterval(u,60000)})();</script>"""
SAFETY = '<p class="src safety">Information from government sources, shown with the time it was observed or issued. It is not a flood warning or a safety determination: no alert does not mean conditions are safe. <a href="/disclaimer/">Disclaimer</a></p>'
NAVSEARCH_JS = """<script>(function(){var i=document.getElementById('gq'),o=document.getElementById('gr'),d=null;if(!i||!o||!window.fetch)return;function load(){if(d)return Promise.resolve(d);return fetch('/gauges.json').then(function(r){return r.json()}).then(function(j){d=j;return j}).catch(function(){d=[];return d})}
function show(q){q=q.toLowerCase().replace(/\\bst\\.? /g,'saint ').trim();o.textContent='';if(q.length<2){o.hidden=true;return}load().then(function(j){var n=0;j.forEach(function(g){if(n>=8)return;if(g[0].toLowerCase().replace(/\\bst\\.? /g,'saint ').indexOf(q)>=0){var a=document.createElement('a');a.href=g[1];a.textContent=g[0];o.appendChild(a);n++}});if(!n){var s=document.createElement('span');s.textContent='No match yet';o.appendChild(s)}o.hidden=false})}
i.addEventListener('input',function(){show(i.value)});i.addEventListener('focus',load);document.addEventListener('click',function(e){if(!o.contains(e.target)&&e.target!==i)o.hidden=true})})();</script>"""
ACTS = '<p class="acts"><button type="button" class="pill" id="savebtn" hidden>Save gauge</button> <button type="button" class="pill" id="csvbtn" data-site="@SITE@" hidden>Download last 7 days (CSV)</button></p>'
TOOLS_JS = """<script>(function(){var sb=document.getElementById('savebtn'),cb=document.getElementById('csvbtn'),K='rwl_saved';
function ld(){try{return JSON.parse(localStorage.getItem(K))||[]}catch(e){return[]}}
if(sb){var u=location.pathname.replace(/(water|forecast)\\/$/,''),n=document.querySelector('h1').textContent;function ref(){sb.textContent=ld().some(function(x){return x.u===u})?'Saved \\u2713':'Save gauge'}
try{localStorage.getItem(K);sb.hidden=false;ref();sb.addEventListener('click',function(){var a=ld(),i=a.findIndex(function(x){return x.u===u});if(i>=0)a.splice(i,1);else a.unshift({u:u,n:n});try{localStorage.setItem(K,JSON.stringify(a.slice(0,8)))}catch(e){}ref()})}catch(e){}}
if(cb&&window.fetch&&window.Blob){cb.hidden=false;cb.addEventListener('click',function(){var s=cb.getAttribute('data-site'),rows=[],ps=['00060','00065'],lab=cb.textContent;cb.disabled=true;cb.textContent='Preparing file...';
function get(p,n){return fetch('https://api.waterdata.usgs.gov/ogcapi/v0/collections/continuous/items?monitoring_location_id=USGS-'+s+'&parameter_code='+p+'&time=P7D&limit=4000&f=json').then(function(r){if(!r.ok)throw new Error(r.status);return r.json()}).catch(function(e){if(n<2)return new Promise(function(res){setTimeout(res,1500)}).then(function(){return get(p,n+1)});throw e})}
ps.reduce(function(pr,p){return pr.then(function(){return get(p,0).then(function(j){(j.features||[]).forEach(function(x){var q=x.properties;if(q.value!==null&&q.value!=='')rows.push([q.time,q.parameter_code,q.value,q.unit_of_measure])})})})},Promise.resolve()).then(function(){rows.sort(function(a,b){return a[0]<b[0]?-1:a[0]>b[0]?1:0});var out=['time_utc,parameter_code,value,unit'].concat(rows.map(function(r){return r.join(',')}));var a=document.createElement('a');a.href=URL.createObjectURL(new Blob([out.join('\\n')+'\\n'],{type:'text/csv'}));a.download='usgs-'+s+'-last-7-days.csv';a.click();cb.textContent=lab;cb.disabled=false}).catch(function(){cb.textContent='Download failed, try again';cb.disabled=false})})}})();</script>"""
ALERTS_JS = """<script>(function(){var b=document.getElementById('alerts');if(!b||!window.fetch)return;var Z="@TZ@",CTY="@CTY@",IG=['Test Message','Administrative Message'];
function lt(d){return d.toLocaleString('en-US',{timeZone:Z,month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'})}
function ast(p){var s=[];((p.geocode&&p.geocode.UGC)||[]).forEach(function(u){var k=u.slice(0,2);if(s.indexOf(k)<0)s.push(k)});return s.length?' ('+s.sort().join(', ')+')':''}
function as(s){var a=s.split(';').map(function(x){return x.trim()}).filter(Boolean),c=CTY.toLowerCase().replace(/ (county|parish)$/,'');if(c){var m=a.filter(function(x){var y=x.toLowerCase();return y===c||y.slice(-c.length-1)===' '+c});a=m.concat(a.filter(function(x){return m.indexOf(x)<0}))}return a.length<=6&&!c?s:a.slice(0,6).join('; ')+(a.length>6?'; and '+(a.length-6)+' more areas':'')}
function el(t,c,x){var e=document.createElement(t);if(c)e.className=c;if(x)e.textContent=x;return e}
fetch('https://api.weather.gov/alerts/active?point=@LAT@,@LON@',{headers:{Accept:'application/geo+json'}}).then(function(r){return r.json()}).then(function(j){if(!j||!j.features)return;
var al=j.features.map(function(f){return f.properties}).filter(function(p){return IG.indexOf(p.event)<0}),src=b.querySelector('.src');if(!src)return;
Array.prototype.slice.call(b.children).forEach(function(c){if(c.tagName!=='H2'&&c!==src)b.removeChild(c)});
if(!al.length){b.insertBefore(el('p','','No active National Weather Service alerts were returned for this location. This is not a statement that conditions are safe.'),src)}
al.forEach(function(p){var d=el('div','alert'),e=p.ends||p.expires;d.appendChild(el('b','',p.event||''));d.appendChild(document.createTextNode(' \\u00b7 '+(p.severity||'severity not stated')+' \\u00b7 '+(as(p.areaDesc||'')+ast(p))));d.appendChild(document.createElement('br'));d.appendChild(document.createTextNode(p.headline||''));d.appendChild(document.createElement('br'));d.appendChild(document.createTextNode('Ends '+(e?lt(new Date(e)):'not stated')));b.insertBefore(d,src)});
src.textContent='Source: National Weather Service alerts for the gauge location, fetched '+lt(new Date())+' (live from the NWS when this page loaded).'}).catch(function(){})})();</script>"""
SAVED_JS = """<script>(function(){var d=document.getElementById('saved');if(!d)return;try{var a=JSON.parse(localStorage.getItem('rwl_saved'))||[];if(!a.length)return;d.innerHTML='<h2>Your saved gauges</h2>'+a.filter(function(x){return String(x.u).charAt(0)==='/'}).map(function(x){var l=document.createElement('a');l.href=x.u;l.textContent=x.n;return l.outerHTML}).join(' &middot; ');d.hidden=false}catch(e){}})();</script>"""
HEAD_EXTRA = '<link rel="icon" href="/favicon.svg" type="image/svg+xml"><meta name="theme-color" content="#1d5fa8">'


def crumb_ld(items):
    """BreadcrumbList markup that mirrors the visible breadcrumb exactly (name, absolute URL)."""
    els = [{"@type": "ListItem", "position": i + 1, "name": n, **({"item": SITE_URL + u} if u else {})} for i, (n, u) in enumerate(items)]
    return '<script type="application/ld+json">%s</script>' % json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": els}, separators=(",", ":")).replace("</", "<" + chr(92) + "/")


JUMP = (("right_now", "Right now"), ("alerts", "Alerts"), ("flow_chart", "7 days"), ("stage_chart", "Gage height"), ("month_chart", "30 days"), ("year_chart", "12 months"), ("multi_year", "Earlier years"),
        ("record_comparison", "Record"), ("annual_peaks", "Peaks"), ("flood_frequency", "Flood frequency"), ("storm_events", "Flood history"), ("stage_flow_rating", "Rating"), ("related_gauges", "Nearby gauges"),
        ("nws_forecast_point", "NWS point"), ("watershed_characteristics", "Watershed"), ("gauge_map", "Map"), ("about_gauge", "About"))


def build_tab(tab, G, pages):
    T = TABS[tab]
    row = G["row"]
    raw = tab_blocks(tab, G, pages)
    ok = lambda b: b and (PREVIEW or SOURCES[b["src_id"]]["status"] in ("quoted", "owner-permission"))
    blocks = []
    for b in raw:
        if isinstance(b, tuple):  # ("PAIR", a, b): two blocks side by side from 900 px up; a lone survivor renders as a normal block
            g = [x for x in b[1:] if ok(x)]
            blocks.append(g if len(g) > 1 else (g[0] if g else None))
        elif b == "AD" or ok(b):
            blocks.append(b)
    blocks = [b for b in blocks if b]
    flat = [x for b in blocks for x in (b if isinstance(b, list) else [b])]
    shown = [b for b in flat if b != "AD"]
    river, place, st = G["river"], G["place"], G["st"]
    rp = river_at(river, place)
    title = mk_title(T["title"] % (rp, st))
    desc = T["desc"] % (rp, st, G["site"])
    url = SITE_URL + row[tab + "_url"] if tab != "dashboard" else SITE_URL + row["dashboard_url"]
    amber = ' <span class="tag amber">Older than 2 h</span>' if G["age_min"] > 120 else ""
    avail = ("dashboard", "forecast") if G["has_forecast"] else ("dashboard",)
    tabs_html = ""  # a lone tab is a dead pill: show tabs only when a Forecast page exists
    for t in (avail if len(avail) > 1 else ()):
        cur = ' class="on" aria-current="page"' if t == tab else ""
        tabs_html += '<a href="%s"%s>%s</a> ' % (row[t + "_url"], cur, TABS[t]["label"])
    tabbar = "" if len(avail) == 1 else '<nav class="tabbar" aria-label="Gauge tabs">%s<a href="/">Rivers</a></nav>' % "".join('<a href="%s"%s>%s</a>' % (row[t + "_url"], ' aria-current="page"' if t == tab else "", ("<b>%s</b>" if t == tab else "%s") % TABS[t]["label"]) for t in avail)
    hub_part = "" if row.get("_single") else '<a href="%s">%s</a> / ' % (row["hub_url"], esc(river))
    crumb = '<div class="crumb"><a href="/">Home</a> / <a href="/rivers/%s/">%s</a> / %s%s</div>' % (st.lower(), esc(st), hub_part, esc(place))
    drain = (" &middot; drainage %s sq mi" % fmt(float(row["drainage_sqmi"]))) if float(row["drainage_sqmi"] or 0) > 0 else ""
    sub = 'USGS gauge %s%s &middot; observed <span data-live="obs">%s</span> &middot; <span class="ab %s"><span data-live="age" data-t="%s">%s</span> old</span>%s' % (G["site"], drain, esc(G["obs"]), "fresh" if G["age_min"] <= 90 else "ageing" if G["age_min"] <= 360 else "stale", iso(G["lt"]), age_text(G["lt"], G["now"]), amber)
    ld_items = [("Home", "/"), (st, "/rivers/%s/" % st.lower())] + ([] if row.get("_single") else [(river, row["hub_url"])]) + [(place, None)]
    ld = crumb_ld(ld_items) + '<script type="application/ld+json">%s</script>' % json.dumps({"@context": "https://schema.org", "@type": "WebPage", "name": title, "url": url, "dateModified": iso(G["lt"]), "isPartOf": {"@type": "WebSite", "name": BRAND, "url": SITE_URL}})
    ids = {b["id"] for b in shown}
    jl = [(i, t) for i, t in JUMP if i in ids]
    jump_html = ('<nav class="jump" aria-label="On this page">%s</nav>' % " ".join('<a href="#%s">%s</a>' % (i, t) for i, t in jl)) if tab == "dashboard" and len(jl) >= 4 else ""
    SIDE = {"related_gauges", "nws_forecast_point", "flood_stages", "public_land", "about_gauge", "gauge_map", "sun", "air_obs", "official_links"}
    body = ""
    side = ""
    first = True
    for b in blocks:
        if T["hero"] and isinstance(b, dict) and b["id"] in SIDE:
            side += render_block(b)
            continue
        body += ('<div class="ad">ADVERTISEMENT</div>' if ADS else "") if b == "AD" else ('<div class="pair">%s</div>' % "".join(render_block(x) for x in b)) if isinstance(b, list) else render_block(b)
    if T["hero"] and side:
        body = '<div class="cols"><div class="main2">%s</div><aside class="side" aria-label="Around this gauge">%s</aside></div>' % (body, side)
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>%s</title><meta name="description" content="%s">'
            '<link rel="canonical" href="%s">%s<style>%s</style></head><body>%s<main id="main">%s<h1>%s, %s</h1><p class="sub">%s</p><p><span class="tabs">%s</span></p>%s%s%s</main>%s%s</body></html>' % (
                esc(title), esc(desc), url, HEAD_EXTRA + og_tags(title, desc, url) + ld, CSS, nav(), crumb, esc(rp), esc(st), sub, tabs_html, (ACTS.replace("@SITE@", G["site"]) + hero(G, pages) + SAFETY + jump_html) if T["hero"] else "", body, sources_block(shown, G) + (LIVE_JS.replace("@SITE@", G["site"]).replace("@TZ@", G["tzname"]) + TOOLS_JS if T["hero"] else AGE_JS) + (ALERTS_JS.replace("@LAT@", "%.4f" % G["lat"]).replace("@LON@", "%.4f" % G["lon"]).replace("@TZ@", G["tzname"]).replace("@CTY@", ((((G["rec"].get("meta") or {}).get("loc")) or {}).get("county_name") or "").replace('"', "")) if any(b["id"] == "alerts" for b in shown) else ""), footer(), tabbar))
    meta = {"site": G["site"], "tab": tab, "url": row[tab + "_url"] if tab != "dashboard" else row["dashboard_url"], "title": title, "blocks": [b["id"] for b in shown], "age_min": round(G["age_min"]),
            "hash": hashlib.sha256(page.encode()).hexdigest()[:16]}
    return page, meta


from lib import blocks2 as b2  # noqa: E402  (blocks added after the fresh-eyes review; uses the helpers above)
from lib import blocks3 as b3  # noqa: E402
