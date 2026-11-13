"""Research pages (owner 2026-11-12: original posts, as slabcalc publishes research; PLAN 14 lists the edge cases). Each one is our own calculation
across every gauge page, from data already in the cache (USGS annual peaks); rebuilt every run, so it grows with the site. A finding with too few gauges is not published."""
import calendar, datetime, statistics, collections
from lib.common import *
from lib.core import table, tr
from lib.directory import shell, crumb_ld, STATE_NAMES

MIN_PEAKS = 20  # water years of annual peaks a gauge needs before its peak month is counted
WIN = 20  # water years in each period of the recent-vs-earlier comparison
MIN_IN_WIN = 15  # of the 20, how many must have a published peak
MIN_GAUGES = 10  # below this a finding is not published
ROW_CAP = 1000  # ponytail: one table of every gauge, about 150 KB at 1,000 rows; per-state pages when the site passes 1,000 river gauges
URLS = ("/research/", "/research/peak-month/", "/research/peak-change/")
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
        p = _peaks(G)
        if p:
            seen.add(r["site"])
            out.append((r, p))
    return sorted(out, key=lambda x: (x[0]["state"], x[0]["river"], x[0]["place"]))


def _link(r):
    return '<a href="%s">%s at %s</a>' % (r["dashboard_url"], esc(r["river"]), esc(r["place"]))


def _cap(n):
    return "<p>%d more gauges are not listed here; each gauge page has its own annual peaks.</p>" % (n - ROW_CAP) if n > ROW_CAP else ""


def _page(title, slug, desc, body, through):
    """No build date on the page: the same data must give the same page (Google: fresh dates without change)."""
    url = "/research/%s/" % slug if slug else "/research/"
    crumbs = [("Home", "/"), ("Research", None)] if not slug else [("Home", "/"), ("Research", "/research/"), (title, None)]
    vis = '<a href="/">Home</a> / Research' if not slug else '<a href="/">Home</a> / <a href="/research/">Research</a> / %s' % esc(title)
    return url, shell(title + " | " + BRAND, desc, url, '<div class="crumb">%s</div><div class="prose"><h1>%s</h1><p class="sub">USGS annual peaks through water year %d, for the US river gauges on this site.</p>%s</div>' % (
        vis, esc(title), through, body), ld=crumb_ld(crumbs))


def _months(ms):
    return " and ".join(MN[m] for m in ms)


def peak_month(gl, through):
    """Which month each river's yearly high most often falls in."""
    rows, lead_n, by_state, ties = [], collections.Counter(), collections.defaultdict(collections.Counter), 0
    for r, p in gl:
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
        tr([_link(r), esc(r["state"]), "%s (%d of %d years, %d%%%s)" % (_months(ms), n, k, round(100 * n / k), " each" if len(ms) > 1 else ""), "%d (%d to %d)" % (k, y0, y1)], right=(3,)) for r, ms, n, k, y0, y1 in rows[:ROW_CAP]), right=(3,))
    body = (lead + "<h2>By month</h2>" + months + "<h2>By state</h2>" + table(["State", "Gauges", "Most common peak month"], st, right=(1,)) +
            "<h2>Every gauge</h2><p>Find your river: the month its yearly high has come most often, and how often.</p>" + gt + _cap(len(rows)) +
            "<h2>How this was worked out</h2><p>Source: USGS annual peak streamflow (Water Data API), as each gauge page's Largest annual peaks block shows it. An annual peak is the highest instantaneous flow in a water year (October to September); where USGS lists more than one peak in a water year, the highest is used. "
            "Peaks without a full date are left out. A peak can come from a storm, snowmelt or a dam release; USGS codes peaks affected by dams or other changes, and this count does not filter them. "
            "The most common month is not a forecast; in many years the high comes in another month, as the share shows.</p>")
    return _page("When US rivers reach their yearly high", "peak-month", "The month each river's yearly high flow most often falls in, from USGS annual peaks at %d US river gauges." % len(rows), body, through)


def peak_change(gl, today, through):
    """Median yearly peak in the last 20 complete water years against the 20 before, per gauge."""
    end = _wy(today) - 1  # the last complete water year; changes once a year, on Oct 1
    rows = []
    for r, p in gl:
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
    rw = lambda xs: "".join(tr([_link(r), "%s cfs" % fmtc(a), "%s cfs" % fmtc(b), "%+.0f%%" % c], right=(1, 2, 3)) for r, a, b, c in xs)
    meth = ("<h2>How this was worked out</h2><p>Source: USGS annual peak streamflow (Water Data API). For each gauge we took the highest peak in each water year (October to September), "
            "then the median of the %d water years %s and of the %d before, and kept only gauges with at least %d years published in each period (USGS publishes the newest year's peak months after it ends). A median is the middle year, so one huge flood does not move it. "
            "Reasons a gauge changes include rain and snow patterns, new or removed dams, water use, land development and gauge moves; USGS codes some of these on its peak records and this comparison does not filter them. "
            "Two 20-year medians are not a trend test.</p>") % (WIN, span(end - WIN + 1, end), WIN, MIN_IN_WIN)
    body = (lead + ("<h2>Largest rises</h2>" + table(hd, rw(sorted(up, key=lambda x: -x[3])[:15]), right=(1, 2, 3)) if up else "") +
            ("<h2>Largest falls</h2>" + table(hd, rw(sorted(dn, key=lambda x: x[3])[:15]), right=(1, 2, 3)) if dn else "") +
            "<h2>Every gauge</h2>" + table(hd, rw(rows[:ROW_CAP]), right=(1, 2, 3)) + _cap(len(rows)) + meth)
    return _page("Are yearly river floods getting bigger?", "peak-change", "The median yearly peak flow of the last 20 water years against the 20 before, at %d US river gauges, from USGS annual peaks." % len(rows), body, through)


def pages(built, Gs, today=None):
    """{url: html}: the research index and every finding with enough gauges; {} when none has (build.py then carries the published copies)."""
    today = today or datetime.date.today()
    gl = gauges(built, Gs)
    if not gl:
        return {}
    through = max(max(p) for _, p in gl)
    got = [x for x in (peak_month(gl, through), peak_change(gl, today, through)) if x]
    if not got:
        return {}
    items = "".join('<li><a href="%s">%s</a></li>' % (u, esc(h.split("<title>")[1].split(" | ")[0])) for u, h in got)
    idx = _page("Research", "", "Original findings from the river gauges on River Water Levels: our own calculations from USGS records.", "<p>Findings worked out from the records behind every gauge page on this site. Each page says how it was calculated and what it cannot tell you.</p><ul>%s</ul>" % items, through)
    return dict([idx] + got)
