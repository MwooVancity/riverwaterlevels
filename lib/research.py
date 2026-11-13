"""Research pages (owner 2026-11-12: original posts, as slabcalc publishes research; PLAN 14 lists the edge cases). Each one is our own calculation
across every gauge page, from data already in the cache (USGS annual peaks, flood statistics, water temperature; NWS flood stages; PLAN 15); rebuilt every run, so it grows with the site. A finding with too few gauges is not published."""
import calendar, datetime, statistics, collections
from lib.common import *
from lib.core import table, tr
from lib.directory import shell, crumb_ld, STATE_NAMES

MIN_PEAKS = 20  # water years of annual peaks a gauge needs before its peak month is counted
WIN = 20  # water years in each period of the recent-vs-earlier comparison
MIN_IN_WIN = 15  # of the 20, how many must have a published peak
MIN_GAUGES = 10  # below this a finding is not published
ROW_CAP = 1000  # ponytail: one table of every gauge, about 150 KB at 1,000 rows; per-state pages when the site passes 1,000 river gauges
URLS = ("/research/", "/research/peak-month/", "/research/peak-change/", "/research/100-year-floods/", "/research/flood-stage-years/", "/research/water-temperature/")
MN = calendar.month_name


def _wy(d):
    """USGS water year: Oct 1 to Sep 30, named for the year it ends in."""
    return d.year + (1 if d.month >= 10 else 0)


def _peaks(G):
    """{water year: (date, flow)}, the highest flow peak in each water year (some gauges list secondary peaks)."""
    out = {}
    for r in ((G["rec"].get("peaks") or {}).get("rows") or []):
        try:
            d = datetime.date.fromisoformat(str(r[0])[:10])
        except ValueError:
            continue  # USGS writes an unknown month or day as 00
        if r[1] is None or r[1] <= 0:
            continue  # a stage-only peak, or no flow
        w = _wy(d)
        if w not in out or r[1] > out[w][1]:
            out[w] = (d, float(r[1]))
    return out


def gauges(built, Gs):
    """US river gauge pages Google may index, each gauge once (two waters can share one gauge), with their peaks."""
    out, seen = [], set()
    for r in built:
        G = Gs.get(r["site"])
        if not G or not r.get("_built") or G.get("lake") or G.get("coast") or r["site"] in seen:
            continue
        seen.add(r["site"])
        out.append((r, _peaks(G), G))  # p may be empty: the water temperature page needs no peaks
    return sorted(out, key=lambda x: (x[0]["state"], x[0]["river"], x[0]["place"]))


def _link(r):
    return '<a href="%s">%s at %s</a>' % (r["dashboard_url"], esc(r["river"]), esc(r["place"]))


def _name(r):
    """Full tables name the gauge without a link (check.py BUDGET trust 60): only the short highlight tables link, and the site search finds any river."""
    return "%s at %s" % (esc(r["river"]), esc(r["place"]))


def _cap(n):
    return "<p>%d more gauges are not listed here; each gauge page has its own annual peaks.</p>" % (n - ROW_CAP) if n > ROW_CAP else ""


def _page(title, slug, desc, body, sub):
    """No build date on the page: the same data must give the same page (Google: fresh dates without change)."""
    url = "/research/%s/" % slug if slug else "/research/"
    crumbs = [("Home", "/"), ("Research", None)] if not slug else [("Home", "/"), ("Research", "/research/"), (title, None)]
    vis = '<a href="/">Home</a> / Research' if not slug else '<a href="/">Home</a> / <a href="/research/">Research</a> / %s' % esc(title)
    return url, shell(title + " | " + BRAND, desc, url, '<div class="crumb">%s</div><div class="prose"><h1>%s</h1><p class="sub">%s</p>%s</div>' % (
        vis, esc(title), sub, body), ld=crumb_ld(crumbs))


def _months(ms):
    return " and ".join(MN[m] for m in ms)


def peak_month(gl, sub):
    """Which month each river's yearly high most often falls in."""
    rows, lead_n, by_state, ties = [], collections.Counter(), collections.defaultdict(collections.Counter), 0
    for r, p, _ in gl:
        if len(p) < MIN_PEAKS:
            continue
        c = collections.Counter(d.month for d, _ in p.values())
        n = max(c.values())
        ms = sorted(m for m, k in c.items() if k == n)
        if len(ms) == 1:
            lead_n[ms[0]] += 1
            by_state[r["state"]][ms[0]] += 1
        else:
            ties += 1
        rows.append((r, ms, n, len(p), min(p), max(p)))
    if len(rows) < MIN_GAUGES:
        return None
    top = lead_n.most_common(3)
    lead = "<p><b>Of %d US river gauges on this site with %d or more years of USGS annual peaks, the yearly high most often comes in %s (%d gauges)%s.</b> " % (
        len(rows), MIN_PEAKS, MN[top[0][0]], top[0][1], "".join(", %s %s (%d)" % ("then" if i == 1 else "and", MN[m], k) for i, (m, k) in enumerate(top[1:], 1))) if top else "<p>"
    lead += "For each gauge we took the highest peak of every water year on file and counted the months they fell in.%s</p>" % (
        " %d gauge%s split evenly between two or more months and %s not counted in the totals." % (ties, "" if ties == 1 else "s", "is" if ties == 1 else "are") if ties else "")
    months = table(["Month", "Gauges whose yearly high most often falls in it"], "".join(tr([MN[m], str(lead_n.get(m, 0))], right=(1,)) for m in range(1, 13)), right=(1,))
    st = ""
    for s, c in sorted(by_state.items()):
        k = max(c.values())
        st += tr([esc(STATE_NAMES.get(s, s)), str(sum(c.values())), "%s (%d of %d)" % (_months(sorted(m for m, v in c.items() if v == k)), k, sum(c.values()))], right=(1,))
    gt = table(["Gauge", "State", "Peak month most often", "Water years on file"], "".join(
        tr([_name(r), esc(r["state"]), "%s (%d of %d years, %d%%%s)" % (_months(ms), n, k, round(100 * n / k), " each" if len(ms) > 1 else ""), "%d (%d to %d)" % (k, y0, y1)], right=(3,)) for r, ms, n, k, y0, y1 in rows[:ROW_CAP]), right=(3,))
    body = (lead + "<h2>By month</h2>" + months + "<h2>By state</h2>" + table(["State", "Gauges", "Most common peak month"], st, right=(1,)) +
            "<h2>Every gauge</h2><p>Find your river: the month its yearly high has come most often, and how often. Each gauge page has the full list of its annual peaks.</p>" + gt + _cap(len(rows)) +
            "<h2>How this was worked out</h2><p>Source: USGS annual peak streamflow (Water Data API), as each gauge page's Largest annual peaks block shows it. An annual peak is the highest instantaneous flow in a water year (October to September); where USGS lists more than one peak in a water year, the highest is used. "
            "Peaks without a full date are left out. A peak can come from a storm, snowmelt or a dam release; USGS codes peaks affected by dams or other changes, and this count does not filter them. "
            "The most common month is not a forecast; in many years the high comes in another month, as the share shows.</p>")
    return _page("When US rivers reach their yearly high", "peak-month", "The month each river's yearly high flow most often falls in, from USGS annual peaks at %d US river gauges." % len(rows), body, sub)


def peak_change(gl, today, sub):
    """Median yearly peak in the last 20 complete water years against the 20 before, per gauge."""
    end = _wy(today) - 1  # the last complete water year; changes once a year, on Oct 1
    rows = []
    for r, p, _ in gl:
        rec = [p[y][1] for y in range(end - WIN + 1, end + 1) if y in p]
        old = [p[y][1] for y in range(end - 2 * WIN + 1, end - WIN + 1) if y in p]
        if len(rec) >= MIN_IN_WIN and len(old) >= MIN_IN_WIN:
            a, b = statistics.median(old), statistics.median(rec)
            rows.append((r, a, b, (b - a) / a * 100))
    if len(rows) < MIN_GAUGES:
        return None
    up = [x for x in rows if x[3] > 10]
    dn = [x for x in rows if x[3] < -10]
    span = lambda a, b: "%d to %d" % (a, b)
    lead = ("<p><b>At %d US river gauges on this site with enough peaks in both periods, the median yearly peak of water years %s was more than 10%% higher than in %s at %d gauges, more than 10%% lower at %d, and within 10%% at %d. "
            "The middle gauge changed by %+.0f%%.</b> This compares typical yearly floods, not the largest ones, and does not say why they changed.</p>") % (
        len(rows), span(end - WIN + 1, end), span(end - 2 * WIN + 1, end - WIN), len(up), len(dn), len(rows) - len(up) - len(dn), statistics.median(x[3] for x in rows))
    hd = ["Gauge", "Median peak %s" % span(end - 2 * WIN + 1, end - WIN), "Median peak %s" % span(end - WIN + 1, end), "Change"]
    rw = lambda xs, f=_link: "".join(tr([f(r), "%s cfs" % fmtc(a), "%s cfs" % fmtc(b), "%+.0f%%" % c], right=(1, 2, 3)) for r, a, b, c in xs)
    meth = ("<h2>How this was worked out</h2><p>Source: USGS annual peak streamflow (Water Data API). For each gauge we took the highest peak in each water year (October to September), "
            "then the median of the %d water years %s and of the %d before, and kept only gauges with at least %d years published in each period (USGS publishes the newest year's peak months after it ends). A median is the middle year, so one huge flood does not move it. "
            "Reasons a gauge changes include rain and snow patterns, new or removed dams, water use, land development and gauge moves; USGS codes some of these on its peak records and this comparison does not filter them. "
            "Two 20-year medians are not a trend test.</p>") % (WIN, span(end - WIN + 1, end), WIN, MIN_IN_WIN)
    body = (lead + ("<h2>Largest rises</h2>" + table(hd, rw(sorted(up, key=lambda x: -x[3])[:15]), right=(1, 2, 3)) if up else "") +
            ("<h2>Largest falls</h2>" + table(hd, rw(sorted(dn, key=lambda x: x[3])[:15]), right=(1, 2, 3)) if dn else "") +
            "<h2>Every gauge</h2>" + table(hd, rw(rows[:ROW_CAP], _name), right=(1, 2, 3)) + _cap(len(rows)) + meth)
    return _page("Are yearly river floods getting bigger?", "peak-change", "The median yearly peak flow of the last 20 water years against the 20 before, at %d US river gauges, from USGS annual peaks." % len(rows), body, sub)


HL = 25  # rows in a linked highlight table (check.py BUDGET trust 60, with the nav and footer)


def _yr_end(rng):
    ys = [int(y) for y in __import__("re").findall(r"\d{4}", rng or "")]
    return ys[-1] if ys else None


def hundred_year(gl):
    """How often the USGS 1%-chance ('100-year') flow was passed in the years after the record USGS computed it from (out of sample)."""
    rows = []
    for r, p, G in gl:
        f = G["rec"].get("floodfreq") or {}
        q = next((x["q"] for x in f.get("rows") or [] if x.get("aep") == 1 and x.get("q")), None)
        end = _yr_end(f.get("range"))
        if f.get("conflict") or not q or not end:
            continue  # as the gauge page: a conflicting statistic is not shown; no 1% row or no record years = nothing to test
        after = sorted((y, v) for y, (d, v) in p.items() if y > end)
        if len(after) < 5:
            continue
        rows.append((r, q, end, after, [y for y, v in after if v >= q], bool(f.get("regulated"))))
    if len(rows) < MIN_GAUGES:
        return None
    def part(xs):
        yrs = sum(len(x[3]) for x in xs)
        return len(xs), yrs, sum(len(x[4]) for x in xs), yrs / 100
    nat, reg = [x for x in rows if not x[5]], [x for x in rows if x[5]]
    def say(xs, what):
        g, yrs, hit, exp = part(xs)
        return "At %d %s, the 1%%-chance flow was reached or passed in %d of %d gauge-years after the records USGS computed it from; a 1%% chance each year implies about %.0f." % (g, what, hit, yrs, exp) if g else ""
    lead = "<p><b>%s</b> %s A '100-year flood' is a flow with a 1%% chance of being reached in any year, not one flood per century.</p>" % (
        say(nat, "US river gauges on this site that USGS does not mark as regulated"), say(reg, "gauges USGS marks as regulated (dams or diversions upstream)"))
    hit = sorted([x for x in rows if x[4]], key=lambda x: (-len(x[4]), x[0]["river"]))
    hd = ["Gauge", "1%-chance flow (USGS)", "Record USGS used ends", "Years since", "Years at or above it"]
    tb = table(hd, "".join(tr([_link(r), "%s cfs" % fmtc(q), "Water year %d" % end, str(len(after)), ", ".join(str(y) for y in yrs) + (" (regulated)" if rg else "")], right=(1, 3)) for r, q, end, after, yrs, rg in hit[:HL]), right=(1, 3)) if hit else "<p>None of these gauges has reached its 1%-chance flow since.</p>"
    body = (lead + "<h2>Gauges that reached it since</h2>" + tb + (_cap_hl(len(hit))) +
            "<h2>How this was worked out</h2><p>Sources: USGS StreamStats gage statistics (peak-flow statistics, 1% annual exceedance probability, with the record years USGS states) and USGS annual peak streamflow (Water Data API), as each gauge page shows them. "
            "For each gauge we took the highest peak of every water year after the last year of the record the statistic was computed from, and counted the years at or above the 1% flow; gauges with fewer than 5 such years are left out. "
            "Statistics that USGS publishes in conflicting versions are left out, as on the gauge pages. Regulated gauges are counted apart because dams change their peaks. The expected number assumes each gauge-year is a separate 1% chance; nearby gauges flood in the same storms, so the real spread is wider.</p>")
    return _page("How often do '100-year floods' happen?", "100-year-floods", "How often the USGS 100-year (1%%-chance) flood flow was reached after USGS computed it, at %d US river gauges." % len(rows), body,
                 "USGS flood statistics and annual peaks, for the US river gauges on this site.")


def _cap_hl(n):
    return "<p>%d more gauges; each gauge page has its own flood statistics.</p>" % (n - HL) if n > HL else ""


def flood_stage(gl):
    """Share of years whose peak stage reached NWS minor flood stage: the same rule as the gauge page (lib/blocks3.stage_years)."""
    from lib.blocks3 import stage_years
    rows = []
    for r, p, G in gl:
        got = stage_years(G)
        if got:
            sr, cats, n = got
            k = sum(1 for x in sr if x[2] >= cats["minor"])
            rows.append((r, cats["minor"], k, len(sr), sr[0][0][:4], sr[-1][0][:4]))
    if len(rows) < MIN_GAUGES:
        return None
    sh = [100 * k / n for _, _, k, n, _, _ in rows]
    lead = ("<p><b>At %d US river gauges on this site where the USGS and National Weather Service stages agree, the yearly peak reached NWS minor flood stage in a median %.0f%% of years. "
            "It did so in at least half the years at %d gauges, and never at %d.</b> Minor flood stage is the NWS's lowest flood category for each forecast point.</p>") % (
        len(rows), statistics.median(sh), sum(1 for x in sh if x >= 50), sum(1 for x in sh if x == 0))
    hd = ["Gauge", "NWS minor flood stage", "Years a peak reached it", "Peak stages on file"]
    row = lambda f: lambda x: tr([f(x[0]), "%.1f ft" % x[1], "%d of %d (%d%%)" % (x[2], x[3], round(100 * x[2] / x[3])), "%s to %s" % (x[4], x[5])], right=(1, 2))
    top = sorted(rows, key=lambda x: (-x[2] / x[3], x[0]["river"]))[:HL]
    body = (lead + "<h2>Gauges that reach flood stage most often</h2>" + table(hd, "".join(map(row(_link), top)), right=(1, 2)) +
            "<h2>Every gauge</h2>" + table(hd, "".join(map(row(_name), rows[:ROW_CAP])), right=(1, 2)) + _cap(len(rows)) +
            "<h2>How this was worked out</h2><p>Sources: USGS annual peak gage heights (Water Data API) and National Weather Service flood stages (National Water Prediction Service), as each gauge page's Annual peaks that reached flood stage block shows them. "
            "A gauge is counted only where the NWS-observed stage and the USGS gage height read within 0.3 ft of each other, so both are on the same zero point; peaks USGS marks with any qualifier other than estimated are left out, and so are gauges with fewer than 10 usable peak stages. "
            "Older peaks can be on an older gauge datum, and flood stages are set for today's channel.</p>")
    return _page("How often do rivers reach flood stage?", "flood-stage-years", "The share of years each river's yearly peak reached National Weather Service minor flood stage, at %d US river gauges." % len(rows), body,
                 "USGS annual peak stages and NWS flood stages, for the US river gauges on this site.")


def water_temp(gl):
    """Typical water temperature by month per gauge: USGS monthly means as the gauge page shows them; a month under 150 daily values is not used."""
    rows = []
    for r, p, G in gl:
        w = G["rec"].get("wtemp") or {}
        ms = {}
        for m, v in (w.get("months") or {}).items():
            if isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v) and v[1] >= 150:
                ms[int(m)] = v[0] * 9 / 5 + 32
        if 7 in ms:
            rows.append((r, ms, str(w.get("first_year") or "?"), str(w.get("last_year") or "?")))
    if len(rows) < MIN_GAUGES:
        return None
    jul = [x[1][7] for x in rows]
    lead = ("<p><b>Across %d US river gauges on this site with a USGS water temperature record, the July average at the middle gauge is %.0f&deg;F. July averages under 60&deg;F at %d gauges and 70&deg;F or warmer at %d.</b> "
            "A monthly average says nothing about a given day; each gauge page shows the latest reading where the sensor reports.</p>") % (len(rows), statistics.median(jul), sum(1 for t in jul if t < 60), sum(1 for t in jul if t >= 70))
    f = lambda m, ms: "%.0f&deg;F" % ms[m] if m in ms else "–"
    hd = ["Gauge", "January", "April", "July", "October", "Record"]
    row = lambda g: lambda x: tr([g(x[0])] + [f(m, x[1]) for m in (1, 4, 7, 10)] + ["%s to %s" % (x[2], x[3])], right=(1, 2, 3, 4))
    by = sorted(rows, key=lambda x: x[1][7])
    body = (lead + "<h2>Coldest in July</h2>" + table(hd, "".join(map(row(_link), by[:HL // 2])), right=(1, 2, 3, 4)) +
            "<h2>Warmest in July</h2>" + table(hd, "".join(map(row(_link), by[::-1][:HL // 2])), right=(1, 2, 3, 4)) +
            "<h2>Every gauge</h2>" + table(hd, "".join(map(row(_name), rows[:ROW_CAP])), right=(1, 2, 3, 4)) + _cap(len(rows)) +
            "<h2>How this was worked out</h2><p>Source: USGS daily mean water temperature (Water Data API), as each gauge page's Typical water temperature by month block shows it: the mean of every published daily value in each calendar month over the record years shown. "
            "A month with fewer than 150 daily values is shown as a dash. A sensor can sit in a deep or shaded spot, and a dam upstream can release cold water from the bottom of its lake, so the water where you get in can differ.</p>")
    return _page("How warm are US rivers?", "water-temperature", "Typical January, April, July and October water temperature at %d US river gauges, from USGS sensor records." % len(rows), body,
                 "USGS water temperature records, for the US river gauges on this site.")


def pages(built, Gs, today=None):
    """{url: html}: the research index and every finding with enough gauges; {} when none has (build.py then carries the published copies)."""
    today = today or datetime.date.today()
    gl = gauges(built, Gs)
    if not gl:
        return {}
    wys = [max(p) for _, p, _ in gl if p]
    sub = "USGS annual peaks through water year %d, for the US river gauges on this site." % max(wys) if wys else ""
    got = [x for x in (peak_month(gl, sub), peak_change(gl, today, sub), hundred_year(gl), flood_stage(gl), water_temp(gl)) if x]
    if not got:
        return {}
    items = "".join('<li><a href="%s">%s</a></li>' % (u, esc(h.split("<title>")[1].split(" | ")[0])) for u, h in got)
    idx = _page("Research", "", "Original findings from the river gauges on River Water Levels: our own calculations from USGS records.", "<p>Findings worked out from the records behind every gauge page on this site. Each page says how it was calculated and what it cannot tell you.</p><ul>%s</ul>" % items, "Our own calculations from USGS and National Weather Service records.")
    return dict([idx] + got)
