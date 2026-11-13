"""Research pages (owner 2026-11-12: original posts, as slabcalc publishes research; 'PubMed worthy'). Edge cases: PLAN 14, 15, 17, 18; peer review 2026-11-12 fixes marked 'review #n'.
Each page is our own calculation across every page of its kind, from data already in the cache (USGS annual peaks with their qualifier codes, StreamStats flood
statistics, water temperature; NWS flood stages; agency lake figures; NOAA tides; world agency labels); rebuilt every run, so it grows with the site.
Each states its sample, its tests and its limits, and publishes its table as CSV. A finding with too few gauges is not published."""
import calendar, collections, csv, io, math, re, statistics
import datetime
from lib.common import *
from lib.core import table, tr, tzl, fdate
from lib.directory import shell, crumb_ld, STATE_NAMES, utc_day

MIN_PEAKS = 20  # water years of annual peaks a gauge needs before its peak month is counted
WIN = 20  # water years in each period of the two-period comparison
MIN_IN_WIN = 15  # of the 20, how many must have a usable peak
MIN_GAUGES = 10  # below this a finding is not published
MIN_FEW = 5  # lakes and tide stations are few on this site: 5 is the floor for those pages
ALPHA = 0.05  # two-sided significance level of the per-gauge test
FDR = 0.10  # Benjamini-Hochberg false discovery rate across gauges
ROW_CAP = 1000  # ponytail: one table of every gauge, about 150 KB at 1,000 rows; per-state pages when the site passes 1,000 river gauges
HL = 25  # rows in a linked highlight table (check.py BUDGET trust 60, with the nav and footer)
URLS = ("/research/", "/research/peak-month/", "/research/peak-change/", "/research/100-year-floods/", "/research/flood-stage-years/", "/research/water-temperature/", "/research/lake-levels/", "/research/tides/")
WORLD_URL = "/research/world-rivers/"
MN = calendar.month_name
SAMPLE = ("<p class=\"src\"><b>Sample:</b> the US river gauges that have a page on this site, chosen by what people search for. They are not a random or representative sample of US rivers: "
          "searches rise after floods, so rivers that flooded recently may be over-represented. The results describe these gauges, not the country, and they change as gauges are added.</p>")
SAMPLE_LAKE = ("<p class=\"src\"><b>Sample:</b> the US lakes that have a page on this site and an agency figure for how full they are. They are not every US reservoir, "
               "so the results describe these lakes only.</p>")
SAMPLE_TIDE = ("<p class=\"src\"><b>Sample:</b> the NOAA tide stations that have their own reading and a page on this site. They are not every US station, "
               "so the results describe these stations only.</p>")
CURRENT_H = 72  # an agency figure older than 3 days is not 'today'
METHOD = "2026-11-13b"  # default only; each page's own version is in data/research-methods.json (raise a page's version the day its text or method changes: its review then reopens alone)
METHODS = __import__("json").load(open(__import__("os").path.join(ROOT, "data", "research-methods.json"), encoding="utf-8"))


def method_of(url):
    return METHODS.get(url, METHOD)  # raise when a page's method changes: build.py carries a published copy only when it carries this same mark (a copy made by an older method can be wrong: truth first)


def _wy(y, m):
    """USGS water year: Oct 1 to Sep 30, named for the year it ends in."""
    return y + (1 if m >= 10 else 0)


def _codes(fq):
    return set(str(fq or "").split())


def _peaks(G):
    """{water year: (month, flow, regulated, lower_bound, day of year)}: the highest flow peak of each water year, lower bounds included and marked.
    None when a cache row has no qualifier field (written before 2026-11-12): without the codes a daily-mean or historic peak cannot be told apart."""
    rows = (G["rec"].get("peaks") or {}).get("rows") or []
    if any(len(r) < 5 for r in rows):
        return None
    out = {}
    for r in rows:
        t, v, c = str(r[0]), r[1], _codes(r[4])
        try:
            y, m = int(t[:4]), int(t[5:7])
            d = int(t[8:10]) or 15  # DAYUNKNOWN can write day 00: mid-month for the date average
        except ValueError:
            continue
        if v is None or v <= 0 or not 1 <= m <= 12 or c & DROP or c & UPPER:
            continue
        try:
            doy = datetime.date(y, m, min(d, 28 if m == 2 else 30 if m in (4, 6, 9, 11) else 31)).timetuple().tm_yday
        except ValueError:
            continue
        w = _wy(y, m)
        if w not in out or v > out[w][1]:
            out[w] = (m, float(v), bool(c & REG), bool(c & LOWER), doy)
    return out


def _plain(p):
    """Years with a plain instantaneous peak (no lower bound): what the month and two-period comparisons use."""
    return {y: v for y, v in (p or {}).items() if not v[3]}


def regulated(G, p, years):
    """One rule for every page (review #5): USGS StreamStats flags the station as regulated, or any peak used is coded as affected by regulation or diversion."""
    return bool((G["rec"].get("floodfreq") or {}).get("regulated")) or any(p[y][2] for y in years if y in p)


def unknown_codes(gl):
    """Peaks carrying a code this module does not know: counted on every page, never silently used or dropped."""
    n = collections.Counter()
    for _, _, G in gl:
        for r in (G["rec"].get("peaks") or {}).get("rows") or []:
            if len(r) >= 5:
                for x in _codes(r[4]) - DROP - LOWER - UPPER - REG - KEEP:
                    n[x] += 1
    return n


def gauges(built, Gs):
    """US river gauge pages Google may index, each gauge once (two waters can share one gauge). p is None for an old cache row, {} for no peaks."""
    out, seen = [], set()
    for r in built:
        G = Gs.get(r["site"])
        if not G or not r.get("_built") or G.get("lake") or G.get("coast") or r["site"] in seen:
            continue
        seen.add(r["site"])
        out.append((r, _peaks(G), G))
    return sorted(out, key=lambda x: (x[0]["state"], x[0]["river"], x[0]["place"]))


def mwu_p(a, b):
    """Two-sided Mann-Whitney U test, normal approximation with tie correction and continuity correction. 1.0 when every value is tied."""
    n1, n2 = len(a), len(b)
    allv = sorted([(v, 0) for v in a] + [(v, 1) for v in b])
    ranks, i, ties = [0.0] * len(allv), 0, 0.0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1][0] == allv[i][0]:
            j += 1
        for k in range(i, j + 1):
            ranks[k] = (i + j) / 2 + 1
        t = j - i + 1
        ties += t ** 3 - t
        i = j + 1
    u = sum(rk for rk, (_, g) in zip(ranks, allv) if g == 0) - n1 * (n1 + 1) / 2
    n = n1 + n2
    var = n1 * n2 / 12 * ((n + 1) - ties / (n * (n - 1)))
    if var <= 0:
        return 1.0
    z = (abs(u - n1 * n2 / 2) - 0.5) / math.sqrt(var)
    return min(1.0, math.erfc(max(z, 0) / math.sqrt(2)))


def hodges_lehmann(a, b):
    """Median of every later-minus-earlier difference: the shift the Mann-Whitney test is about (review #6). 400 pairs at 20 x 20."""
    return statistics.median(y - x for x in a for y in b)


def bh_count(ps, q=FDR):
    """How many p-values survive the Benjamini-Hochberg false discovery rate q."""
    s, k = sorted(ps), 0
    for i, p in enumerate(s, 1):
        if p <= q * i / len(s):
            k = i
    return k


def poisson_tail(k, lam):
    """Chance of a count at least k (k >= lam) or at most k (k < lam) when the count is Poisson with mean lam; in log space (no underflow at lam = 300)."""
    if lam <= 0:
        return 1.0
    terms = range(0, k) if k >= lam else range(0, k + 1)
    logs = [-lam + i * math.log(lam) - math.lgamma(i + 1) for i in terms]
    s = 0.0
    if logs:
        mx = max(logs)
        s = math.exp(mx) * sum(math.exp(x - mx) for x in logs)
    return max(0.0, min(1.0, 1 - s if k >= lam else s))


def poisson_two(k, lam):
    """Two-sided (review #3): twice the smaller tail, at most 1."""
    up = poisson_tail(k, lam) if k >= lam else 1.0
    dn = poisson_tail(k, lam) if k < lam else 1 - poisson_tail(k + 1, lam) if k + 1 >= lam else 1.0
    return min(1.0, 2 * min(up, dn))


def circ(doys):
    """(mean day of year, concentration 0 to 1) of peak dates on the annual circle (Burn 1997): 1 = every peak on the same date, 0 = spread through the year."""
    xs = [2 * math.pi * (d - 0.5) / 365.25 for d in doys]
    c, s = sum(map(math.cos, xs)) / len(xs), sum(map(math.sin, xs)) / len(xs)
    ang = math.atan2(s, c) % (2 * math.pi)
    return ang * 365.25 / (2 * math.pi) + 0.5, math.hypot(c, s)


def _doy_name(d):
    return (datetime.date(2001, 1, 1) + datetime.timedelta(days=int(round(d)) - 1)).strftime("%b %d").replace(" 0", " ")


def _pv(p):
    return "%.3f" % p if p >= 0.001 else "&lt;0.001"


def _link(r):
    return '<a href="%s">%s at %s</a>' % (r["dashboard_url"], esc(r["river"]), esc(r["place"]))


def _name(r):
    """Full tables name the gauge without a link (check.py BUDGET trust 60): only the short highlight tables link, and the site search finds any river."""
    return "%s at %s" % (esc(r["river"]), esc(r["place"]))


def _cap(n, what="annual peaks"):
    return "<p>%d more gauges are not listed here; each gauge page has its own %s, and the CSV lists them all.</p>" % (n - ROW_CAP, what) if n > ROW_CAP else ""


def _cred(*ids):
    """The credit each source's terms ask for, verbatim from data/sources.json (harm audit #2: OGL and CC BY require attribution wherever the data goes)."""
    from lib.render import SOURCES
    return "; ".join((SOURCES.get(i) or {}).get("credit") or {"usace_cwms": "Data: U.S. Army Corps of Engineers, Corps Water Management System"}.get(i, i) for i in ids)


def _csv(head, rows, credit=None):
    """CSV text; a text cell starting with = + - @ gets an apostrophe so a spreadsheet never runs it as a formula (numbers are written as numbers).
    credit: a string, or a function of the row, written as the last column of every row."""
    b = io.StringIO()
    w = csv.writer(b, lineterminator="\n")
    w.writerow(list(head) + (["credit"] if credit else []))
    for r in rows:
        r = list(r) + ([credit(r) if callable(credit) else credit] if credit else [])
        w.writerow([("'" + c) if isinstance(c, str) and c and c[0] in "=+-@" else c for c in r])  # an empty cell stays empty
    return b.getvalue()


def _g(r):
    return [r["site"], r["river"], r["place"], r["state"], SITE_URL + r["dashboard_url"]]


def _fa(G, key):
    return str((G["rec"].get(key) or {}).get("fetched_at") or "")


G_HEAD = ["usgs_site", "river", "place", "state", "page"]


def _page(title, slug, desc, body, sub, data=None, unk=None, sample=None):
    """(url, html, csv or None). No build date on the page: the same data must give the same page (Google: fresh dates without change)."""
    url = "/research/%s/" % slug if slug else "/research/"
    crumbs = [("Home", "/"), ("Research", None)] if not slug else [("Home", "/"), ("Research", "/research/"), (title, None)]
    vis = '<a href="/">Home</a> / Research' if not slug else '<a href="/">Home</a> / <a href="/research/">Research</a> / %s' % esc(title)
    extra = ""
    if slug:
        extra += sample or SAMPLE
        if unk:
            extra += '<p class="src">USGS codes this page does not yet sort: %s. Those peaks are counted as USGS published them.</p>' % ", ".join("%s (%d peaks)" % (esc(k), v) for k, v in sorted(unk.items()))
        if data:
            extra += '<p><a href="data.csv">Download the data for every gauge (CSV)</a>, one row per gauge with its source fetch time, for checking or reuse with a link back.</p>'
    return url, shell(title + " | " + BRAND, desc, url, '<div class="crumb">%s</div><div class="prose" data-method="%s"><h1>%s</h1><p class="sub">%s</p>%s%s</div>' % (
        vis, method_of(url), esc(title), sub, body, extra), ld=crumb_ld(crumbs)), data


def _pl(n, one, many):
    """'1 regulated gauge is' / '3 regulated gauges are': a count of 1 reads right (verification 2026-11-13)."""
    return "%d %s" % (n, one if n == 1 else many)


def _months(ms):
    return " and ".join(MN[m] for m in ms)


EXCL = ("Left out: peaks USGS codes as historic (outside the regular record), as a dam failure, as less than the value shown, or with an unknown month or year; "
        "peaks coded as a maximum daily mean or as greater than the value shown are lower bounds and are not used as plain peaks.")


def peak_month(gl, sub, unk):
    """Which month each river's yearly high most often falls in, with the circular mean date and concentration; regulated gauges counted apart."""
    rows, lead_n, by_state, ties = [], collections.Counter(), collections.defaultdict(collections.Counter), 0
    for r, p, G in gl:
        q = _plain(p)
        if len(q) < MIN_PEAKS:
            continue
        reg = regulated(G, p, q)
        c = collections.Counter(v[0] for v in q.values())
        n = max(c.values())
        ms = sorted(m for m, k in c.items() if k == n)
        md_, rr = circ([v[4] for v in q.values()])
        if not reg:
            if len(ms) == 1:
                lead_n[ms[0]] += 1
                by_state[r["state"]][ms[0]] += 1
            else:
                ties += 1
        rows.append((r, ms, n, len(q), min(q), max(q), reg, md_, rr, G))
    nat = [x for x in rows if not x[6]]
    if len(nat) < MIN_GAUGES:
        return None
    top = lead_n.most_common(3)
    lead = "<p><b>The yearly high on these rivers most often comes in %s: at %d of %d gauges%s.</b> " % (
        MN[top[0][0]], top[0][1], len(nat), "".join(", %s %s (%d)" % ("then" if i == 1 else "and", MN[m], k) for i, (m, k) in enumerate(top[1:], 1))) if top else "<p>"
    lead += "Counted at US river gauges on this site with %d or more years of plain USGS annual peaks and no regulation flag; for each we took the highest peak of every water year and counted the months.%s%s</p>" % (
        MIN_PEAKS, " %d gauge%s split evenly between two or more months and %s not counted." % (ties, "" if ties == 1 else "s", "is" if ties == 1 else "are") if ties else "",
        " %s listed but not counted." % _pl(len(rows) - len(nat), "regulated gauge is", "regulated gauges are") if len(rows) > len(nat) else "")
    months = table(["Month", "Gauges whose yearly high most often falls in it"], "".join(tr([MN[m], str(lead_n.get(m, 0))], right=(1,)) for m in range(1, 13)), right=(1,))
    st = ""
    for s, c in sorted(by_state.items()):
        k = max(c.values())
        st += tr([esc(STATE_NAMES.get(s, s)), str(sum(c.values())), "%s (%d of %d)" % (_months(sorted(m for m, v in c.items() if v == k)), k, sum(c.values()))], right=(1,))
    gt = table(["Gauge", "Peak month most often", "Average peak date", "How tightly peaks cluster (0 to 1)", "Water years used"], "".join(
        tr([_name(r) + (" (regulated)" if rg else ""), "%s (%d of %d years, %d%%%s)" % (_months(ms), n, k, round(100 * n / k), " each" if len(ms) > 1 else ""), _doy_name(md_) if rr >= 0.3 else "&ndash; (peaks not clustered around one date)", "%.2f" % rr, "%d (%d to %d)" % (k, y0, y1)], right=(3, 4))
        for r, ms, n, k, y0, y1, rg, md_, rr, G in rows[:ROW_CAP]), right=(3, 4))
    data = _csv(G_HEAD + ["peak_month_most_often", "years_in_that_month", "water_years_used", "first_water_year", "last_water_year", "mean_peak_day_of_year", "concentration_r", "regulated", "source", "peaks_fetched_at"],
                [_g(r) + [" and ".join(MN[m] for m in ms), n, k, y0, y1, round(md_, 1), round(rr, 3), rg, "USGS annual peak streamflow (Water Data API)", _fa(G, "peaks")] for r, ms, n, k, y0, y1, rg, md_, rr, G in rows], _cred("usgs"))
    body = (lead + "<h2>By month</h2>" + months + "<h2>By state</h2>" + table(["State", "Gauges", "Most common peak month"], st, right=(1,)) +
            "<h2>Every gauge</h2><p>Find your river: the month its yearly high has come most often, the average date, and how tightly the peaks cluster around it.</p>" + gt + _cap(len(rows)) +
            "<h2>How this was worked out</h2><p>Source: USGS annual peak streamflow (Water Data API), as each gauge page's Largest annual peaks block shows it, with USGS's qualifier codes. An annual peak is the highest instantaneous flow in a water year (October to September); where USGS lists more than one peak in a water year, the highest is used. "
            + EXCL + " A gauge counts as regulated when USGS StreamStats flags the station as regulated or any peak used is coded as affected by regulation or diversion. "
            "The average date and the clustering figure treat each peak date as a point on the yearly circle (the seasonality measure of Burn, 1997): 1 means every peak fell on the same date, 0 means they are spread evenly through the year; under 0.3 no average date is shown, because peaks spread through the year or split between two seasons have no meaningful average date. "
            "The most common month is not a forecast; in many years the high comes in another month, as the share shows.</p>")
    return _page("When US rivers reach their yearly high", "peak-month", "The month each river's yearly high flow most often falls in, its average date and how tightly peaks cluster, from USGS annual peaks at %d US river gauges." % len(nat), body, sub, data, unk)


def peak_change(gl, today, sub, unk):
    """Yearly peaks of the last 20 complete water years against the 20 before, per gauge: Mann-Whitney test, Hodges-Lehmann shift, Benjamini-Hochberg across gauges."""
    end = _wy(today.year, today.month) - 1  # the last complete water year; changes once a year, on Oct 1
    have = [p for _, p, _ in gl if p]
    if have and sum(1 for p in have if end in p) < len(have) / 2:
        end -= 1  # hostile review #11: USGS publishes a year's peaks months after it ends; the period ends at the last water year most gauges have
    rows = []
    for r, p, G in gl:
        q = _plain(p)
        rec = [q[y][1] for y in range(end - WIN + 1, end + 1) if y in q]
        old = [q[y][1] for y in range(end - 2 * WIN + 1, end - WIN + 1) if y in q]
        if len(rec) >= MIN_IN_WIN and len(old) >= MIN_IN_WIN:
            a, b = statistics.median(old), statistics.median(rec)
            rows.append((r, a, b, (b - a) / a * 100, mwu_p(old, rec), regulated(G, p, range(end - 2 * WIN + 1, end + 1)), len(old), len(rec), hodges_lehmann(old, rec), G))
    nat = [x for x in rows if not x[5]]
    if len(nat) < MIN_GAUGES:
        return None
    span = lambda a, b: "%d to %d" % (a, b)
    P1, P2 = span(end - 2 * WIN + 1, end - WIN), span(end - WIN + 1, end)
    sig_up = [x for x in nat if x[4] < ALPHA and x[8] > 0]
    sig_dn = [x for x in nat if x[4] < ALPHA and x[8] < 0]
    ps = [x[4] for x in nat]
    k = bh_count(ps)
    thr = sorted(ps)[k - 1] if k else -1
    bh_up, bh_dn = sum(1 for x in nat if x[4] <= thr and x[8] > 0), sum(1 for x in nat if x[4] <= thr and x[8] < 0)
    exp = ALPHA / 2 * len(nat)
    if not k:  # harm audit 2026-11-12 #1: 3 up and 1 down of 87 was called 'more than chance' while chance gives about 2.2 each way
        head = ("<b>Across %d gauges, no gauge's change in yearly peaks between water years %s and %s stands out from chance after the correction for testing many gauges at once.</b> "
                "%d tested higher and %d lower at p &lt; %.2f, about what chance gives (about %.1f each way), and none survives the Benjamini-Hochberg correction (false discovery rate %d%%). "
                "A test on about 20 years a period can miss a real change, so this is not evidence that nothing changed. "
                ) % (len(nat), P1, P2, len(sig_up), len(sig_dn), ALPHA, exp, round(FDR * 100))
    else:
        head = ("<b>At %d of %d gauges, yearly peaks in water years %s differ from %s by more than chance alone explains: %d higher, %d lower.</b> "
                "That is after the Benjamini-Hochberg correction for testing many gauges at once (false discovery rate %d%%); before it, %d tested higher and %d lower at p &lt; %.2f, against about %.1f each way by chance. "
                ) % (k, len(nat), P2, P1, bh_up, bh_dn, round(FDR * 100), len(sig_up), len(sig_dn), ALPHA, exp)
    lead = "<p>" + head + "This compares the typical yearly peak in two periods; it does not say why they changed.%s</p>" % (
        (" %s listed apart, not counted." % _pl(len(rows) - len(nat), "regulated gauge is", "regulated gauges are")) if len(rows) > len(nat) else "")
    hd = ["Gauge", "Median peak %s" % P1, "Median peak %s" % P2, "Shift (Hodges-Lehmann)", "p"]
    rw = lambda xs, f=_link: "".join(tr([f(r) + (" (regulated)" if rg else ""), "%s cfs" % fmtc(a), "%s cfs" % fmtc(b), "%s%s cfs" % ("+" if hl_ > 0 else "", fmtc(hl_)), _pv(pv)], right=(1, 2, 3, 4)) for r, a, b, c, pv, rg, _, _, hl_, G in xs)
    meth = ("<h2>How this was worked out</h2><p>Source: USGS annual peak streamflow (Water Data API), with USGS's qualifier codes. For each gauge we took the highest plain peak in each water year (October to September), "
            "then compared the %d water years %s with the %d before, keeping gauges with at least %d plain peaks in each period (USGS publishes the newest year's peak months after it ends). " + EXCL + " "
            "A gauge USGS StreamStats flags as regulated, or with any peak in either period coded as affected by regulation or diversion, is listed apart. "
            "The test is a two-sided Mann-Whitney U test (normal approximation, corrected for ties) of whether one period's peaks tend to be larger than the other's, significant at p &lt; %.2f; the shift is the Hodges-Lehmann estimate, the median of every later-minus-earlier difference, and its sign gives the direction. "
            "Testing many gauges at once lets some differences appear by chance, so the expected chance count and the Benjamini-Hochberg count are given. Peaks in neighbouring years and at neighbouring gauges are not independent, so every p is approximate and tends to be too small. "
            "Reasons a gauge changes include rain and snow patterns, water use, land development and gauge moves. This is a comparison of two periods, not a trend analysis of the whole record.</p>") % (WIN, P2, WIN, MIN_IN_WIN, ALPHA)
    data = _csv(G_HEAD + ["median_peak_cfs_wy%s" % P1.replace(" to ", "_"), "median_peak_cfs_wy%s" % P2.replace(" to ", "_"), "change_pct", "hodges_lehmann_shift_cfs", "mann_whitney_p", "regulated", "plain_peaks_first_period", "plain_peaks_second_period", "source", "peaks_fetched_at"],
                [_g(r) + [round(a, 1), round(b, 1), round(c, 1), round(hl_, 1), round(pv, 4), rg, n1, n2, "USGS annual peak streamflow (Water Data API)", _fa(G, "peaks")] for r, a, b, c, pv, rg, n1, n2, hl_, G in rows], _cred("usgs"))
    body = (lead + ("<h2>Higher at p &lt; 0.05 (before the correction; some are chance)</h2>" + table(hd, rw(sorted(sig_up, key=lambda x: -x[8])[:12]), right=(1, 2, 3, 4)) if sig_up else "") +
            ("<h2>Lower at p &lt; 0.05 (before the correction; some are chance)</h2>" + table(hd, rw(sorted(sig_dn, key=lambda x: x[8])[:12]), right=(1, 2, 3, 4)) if sig_dn else "") +
            "<h2>Every gauge</h2>" + table(hd, rw(rows[:ROW_CAP], _name), right=(1, 2, 3, 4)) + _cap(len(rows)) + meth)
    return _page("Yearly river peaks: water years %s against %s" % (P2, P1), "peak-change", "Yearly peak flows of water years %s against %s, tested gauge by gauge, at %d US river gauges, from USGS annual peaks." % (P2, P1, len(nat)), body, sub, data, unk)


def hundred_year(gl, unk):
    """How often the USGS 1%-chance ('100-year') flow was reached in the years after the record USGS computed it from (out of sample)."""
    rows = []
    for r, p, G in gl:
        if not p:
            continue
        f = G["rec"].get("floodfreq") or {}
        one = next((x for x in f.get("rows") or [] if x.get("aep") == 1 and x.get("q")), None)
        r1 = f.get("range1")  # review #7: the 1% row's own 'Statistic Date Range', never another row's comment
        if f.get("conflict") or not one or not r1:
            continue
        end, Q = r1[1], one["q"]
        yrs, hit = [], []
        for y in sorted(p):
            if y <= end:
                continue
            m, v, rg, lb, _ = p[y]
            if lb and v < Q:
                continue  # a lower bound under the 1% flow: whether the true peak reached it is unknown, so the year is not counted either way
            yrs.append(y)
            if v >= Q:
                hit.append(y)  # review #4: a lower bound at or above the 1% flow is a certain exceedance
        if len(yrs) < 5:
            continue
        lo, hi = one.get("lo"), one.get("hi")
        rows.append((r, Q, end, yrs, hit, regulated(G, p, yrs), lo, hi,
                     sum(1 for y in yrs if p[y][1] >= lo) if lo and hi else None, sum(1 for y in yrs if p[y][1] >= hi) if lo and hi else None, G, f))
    nat, reg = [x for x in rows if not x[5]], [x for x in rows if x[5]]
    if len(nat) < MIN_GAUGES:
        return None
    gy, hits = sum(len(x[3]) for x in nat), sum(len(x[4]) for x in nat)
    storms = len({y for x in nat for y in x[4]})
    lead = ("<p><b>At %d US river gauges on this site, USGS's '100-year' flow was reached in %d of %d gauge-years after the last year of the record it was computed from.</b> "
            "If every gauge-year were a separate 1%% chance, about %.1f would be expected.%s "
            "A '100-year flood' is a flow with a 1%% chance of being reached in any year, not one flood per century.</p>") % (len(nat), hits, gy, gy / 100, (" The %d fell in only %s, so some came in the same water year and may be the same storms." % (hits, _pl(storms, "water year", "water years"))) if hits > storms else "")
    lead += ("<p>Two things push the count above 1%% even when nothing has changed: the 1%% flow is itself estimated from a limited record, so it is reached somewhat more often than its label says, most of all at gauges with short records (the expected-probability effect; Beard, 1960); "
             "and gauges on this site were added where people search, which rises after floods. The two-sided chance of a count this far from %.1f, if every gauge-year were an independent 1%% chance, is %s; neighbouring gauges flood in the same storms, so that chance is too small and is shown only for reference.%s</p>") % (
        gy / 100, _pv(poisson_two(hits, gy / 100)),
        (" At %s, counted apart: %d of %d gauge-years." % (_pl(len(reg), "regulated gauge", "regulated gauges"), sum(len(x[4]) for x in reg), sum(len(x[3]) for x in reg))) if reg else "")
    ci = [x for x in nat if x[8] is not None]
    cis = ("<p>Against the interval USGS publishes with the 1%% flow at %d of these gauges (the interval's level is not stated in the data we read): %d gauge-years reached its lower end and %d its upper end, of %d gauge-years.</p>" % (
        len(ci), sum(x[8] for x in ci), sum(x[9] for x in ci), sum(len(x[3]) for x in ci))) if len(ci) >= MIN_GAUGES else ""
    hit = sorted([x for x in rows if x[4]], key=lambda x: (-len(x[4]), x[0]["river"]))
    hd = ["Gauge", "1%-chance flow (USGS StreamStats)", "USGS record used ends", "Water years since", "Years it was reached"]
    tb = table(hd, "".join(tr([_link(x[0]) + (" (regulated)" if x[5] else ""), "%s cfs" % fmtc(x[1]), "Water year %d" % x[2], str(len(x[3])), ", ".join(str(y) for y in x[4])], right=(1, 3)) for x in hit[:HL]), right=(1, 3)) if hit else "<p>None of these gauges has reached its 1%-chance flow since.</p>"
    data = _csv(G_HEAD + ["q_1pct_cfs", "interval_lower_cfs", "interval_upper_cfs", "statistic_record_start_wy", "statistic_record_end_wy", "water_years_counted", "years_reached", "years_at_or_above_lower", "years_at_or_above_upper", "regulated", "statistic_citation", "streamstats_fetched_at", "peaks_fetched_at"],
                [_g(x[0]) + [x[1], x[6] or "", x[7] or "", x[11]["range1"][0], x[2], len(x[3]), " ".join(str(y) for y in x[4]), "" if x[8] is None else x[8], "" if x[9] is None else x[9], x[5], x[11].get("citation") or "", _fa(x[10], "floodfreq"), _fa(x[10], "peaks")] for x in rows], _cred("usgs"))
    body = (lead + cis + "<h2>Gauges that reached it since</h2>" + tb + ("<p>%d more gauges; the CSV lists them all.</p>" % (len(hit) - HL) if len(hit) > HL else "") +
            "<h2>How this was worked out</h2><p>Sources: USGS StreamStats gage statistics (the '1-percent AEP flood' statistic for the gauge, the preferred one where USGS publishes several, as each gauge page shows it; the interval published with it; and the 'Statistic Date Range' stated on that statistic) and USGS annual peak streamflow (Water Data API) with its qualifier codes, as each gauge page shows them. "
            "For each gauge we took the highest peak of every water year after the last year of the statistic's own date range, so the count uses only years the statistic never saw; gauges with fewer than 5 such years, or whose statistic states no date range, are left out. "
            "A peak coded as a lower bound (maximum daily mean, or greater than) counts as reaching the 1% flow when it is already at or above it, and its year is left out when it is below. "
            "Left out: peaks coded historic, dam failure, less than, or with an unknown month or year; statistics USGS publishes in conflicting versions. A gauge USGS flags as regulated, or with a later peak coded as affected by regulation or diversion, is counted apart.</p>")
    return _page("How often do '100-year floods' happen?", "100-year-floods", "How often the USGS 100-year (1%%-chance) flood flow was reached after USGS computed it, at %d US river gauges, with the limits of the count." % len(nat), body,
                 "USGS flood statistics and annual peaks, for the US river gauges on this site.", data, unk)


def flood_stage(gl):
    """Share of water years whose peak stage reached NWS minor flood stage: the same rule as the gauge page (lib/blocks3.stage_years)."""
    from lib.blocks3 import stage_years, wy_of
    rows = []
    for r, p, G in gl:
        got = stage_years(G)
        if got and all(len(x) >= 5 for x in (G["rec"].get("peaks") or {}).get("rows") or []):  # research needs the flow codes (historic stages, review #1)
            sr, cats, n = got
            k = sum(1 for x in sr if x[2] >= cats["minor"])
            rows.append((r, cats["minor"], k, len(sr), wy_of(sr[0]), wy_of(sr[-1]), n.get("lid") or "", G, regulated(G, p or {}, list(p or {}))))
    nat = [x for x in rows if not x[8]]  # hostile review #13: regulated gauges apart, as on the other pages
    if len(nat) < MIN_GAUGES:
        return None
    sh = [100 * x[2] / x[3] for x in nat]
    lead = ("<p><b>On a typical one of these rivers, the yearly peak reached minor flood stage in %.0f%% of years.</b> "
            "That is the median across %d US river gauges on this site where the USGS and National Weather Service stages agree and USGS flags no regulation; it happened in at least half the years at %d gauges, and never at %d.%s "
            "Minor flood stage is the NWS's lowest flood category for each forecast point. This is the record of past years, not a forecast: for flooding now, follow the National Weather Service warnings for your area.</p>") % (
        statistics.median(sh), len(nat), sum(1 for x in sh if x >= 50), sum(1 for x in sh if x == 0), (" %s listed but not counted." % _pl(len(rows) - len(nat), "regulated gauge is", "regulated gauges are")) if len(rows) > len(nat) else "")
    hd = ["Gauge", "NWS minor flood stage", "Water years a peak reached it", "Water years on file"]
    row = lambda f: lambda x: tr([f(x[0]) + (" (regulated)" if x[8] else ""), "%.1f ft" % x[1], "%d of %d (%d%%)" % (x[2], x[3], round(100 * x[2] / x[3])), "%d to %d" % (x[4], x[5])], right=(1, 2))
    top = sorted(nat, key=lambda x: (-x[2] / x[3], x[0]["river"]))[:HL]
    data = _csv(G_HEAD + ["nws_forecast_point", "nws_minor_flood_stage_ft", "water_years_peak_reached_it", "water_years_with_peak_stage", "first_water_year", "last_water_year", "regulated", "source", "peaks_fetched_at", "nws_fetched_at"],
                [_g(x[0]) + [x[6], x[1], x[2], x[3], x[4], x[5], x[8], "USGS annual peak gage heights; NWS National Water Prediction Service flood categories", _fa(x[7], "peaks"), _fa(x[7], "nwps")] for x in rows], _cred("usgs", "nwps"))
    body = (lead + "<h2>Gauges that reach flood stage most often</h2>" + table(hd, "".join(map(row(_link), top)), right=(1, 2)) +
            "<h2>Every gauge</h2>" + table(hd, "".join(map(row(_name), rows[:ROW_CAP])), right=(1, 2)) + _cap(len(rows), "flood record") +
            "<h2>How this was worked out</h2><p>Sources: USGS annual peak gage heights (Water Data API) and National Weather Service flood stages (National Water Prediction Service), as each gauge page's Annual peaks that reached flood stage block shows them. "
            "A gauge is counted only where the NWS-observed stage and the USGS gage height read within 0.3 ft of each other, so both are on the same zero point today; where USGS records a change of gauge datum, only the water years after the last one count. "
            "Each water year counts once, at its highest stage. Left out: stages USGS marks with any stage qualifier other than estimated (a conservative rule: some real flood stages, such as backwater stages, are dropped with them), and stages whose flow peak is coded historic, a daily mean or a dam failure; gauges with fewer than 10 usable water years. "
            "Record lengths differ from gauge to gauge, so shares cover different periods, and flood stages are set for today's channel.</p>")
    return _page("How often do rivers reach flood stage?", "flood-stage-years", "The share of water years each river's yearly peak reached National Weather Service minor flood stage, at %d US river gauges." % len(nat), body,
                 "USGS annual peak stages and NWS flood stages, for the US river gauges on this site.", data)


def water_temp(gl):
    """Typical water temperature by month per gauge: USGS monthly means as the gauge page shows them; a month under 150 daily values is not used."""
    rows = []
    for r, p, G in gl:
        w = G["rec"].get("wtemp") or {}
        ms, ns = {}, {}
        for m, v in (w.get("months") or {}).items():
            if isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v) and v[1] >= 150:
                ms[int(m)], ns[int(m)] = v[0] * 9 / 5 + 32, int(v[1])
        if 7 in ms:
            rows.append((r, ms, str(w.get("first_year") or "?"), str(w.get("last_year") or "?"), ns, G))
    if len(rows) < MIN_GAUGES:
        return None
    jul = [x[1][7] for x in rows]
    lead = ("<p><b>In July, the median gauge on these rivers averages %.0f&deg;F.</b> Across %d US river gauges on this site with a USGS water temperature record, July averages under 60&deg;F at %d gauges and 70&deg;F or warmer at %d. "
            "A monthly average says nothing about a given day; each gauge page shows the latest reading where the sensor reports.</p>") % (statistics.median(jul), len(rows), sum(1 for t in jul if t < 60), sum(1 for t in jul if t >= 70))
    f = lambda m, ms: "%.0f&deg;F" % ms[m] if m in ms else "–"
    hd = ["Gauge", "January", "April", "July", "October"]  # 5 columns (check.py wide_tables): the record years sit under the gauge name
    row = lambda g: lambda x: tr(['%s<div class="src">Sensor record %s to %s</div>' % (g(x[0]), x[2], x[3])] + [f(m, x[1]) for m in (1, 4, 7, 10)], right=(1, 2, 3, 4))
    by = sorted(rows, key=lambda x: x[1][7])
    data = _csv(G_HEAD + ["mean_f_%s" % MN[m].lower() for m in range(1, 13)] + ["daily_values_%s" % MN[m].lower() for m in range(1, 13)] + ["first_year", "last_year", "source", "fetched_at"],
                [_g(x[0]) + [round(x[1][m], 1) if m in x[1] else "" for m in range(1, 13)] + [x[4].get(m, "") for m in range(1, 13)] + [x[2], x[3], "USGS daily mean water temperature (Water Data API)", _fa(x[5], "wtemp")] for x in rows], _cred("usgs"))
    body = (lead + "<h2>Coldest in July</h2>" + table(hd, "".join(map(row(_link), by[:HL // 2])), right=(1, 2, 3, 4)) +
            "<h2>Warmest in July</h2>" + table(hd, "".join(map(row(_link), by[::-1][:HL // 2])), right=(1, 2, 3, 4)) +
            "<h2>Every gauge</h2>" + table(hd, "".join(map(row(_name), rows[:ROW_CAP])), right=(1, 2, 3, 4)) + _cap(len(rows), "water temperature by month") +
            "<h2>How this was worked out</h2><p>Source: USGS daily mean water temperature (Water Data API), as each gauge page's Typical water temperature by month block shows it: the mean of every published daily value in each calendar month over the record years shown; where USGS publishes two temperature series for one gauge, the first it returns is used. "
            "A month with fewer than 150 daily values is shown as a dash. Sensor records cover different years at different gauges, so gauges are not compared over the same period, and years with more readings weigh more in a mean. "
            "A sensor can sit in a deep or shaded spot, and a gauge below a dam can read the cold water released from the bottom of the lake, so a cold July figure can come from dam releases, and the water where you get in can differ.</p>")
    return _page("How warm are US rivers?", "water-temperature", "Typical January, April, July and October water temperature at %d US river gauges, from USGS sensor records." % len(rows), body,
                 "USGS water temperature records, for the US river gauges on this site.", data)


def waters(built, Gs, kind):
    """Lake or coast pages Google may index, each gauge once."""
    out, seen = [], set()
    for r in built:
        G = Gs.get(r["site"])
        if not G or not r.get("_built") or r["site"] in seen or not (G.get("coast") if kind == "coast" else (G.get("lake") and not G.get("coast"))):
            continue
        seen.add(r["site"])
        out.append((r, G))
    return sorted(out, key=lambda x: (x[0]["state"], x[0]["river"]))


def _age_h(G, t):
    return (G["now"] - t).total_seconds() / 3600


def lake_full(G):
    """[(basis, below_full: bool, text, as-of datetime)] from the same helpers the lake page's reservoir block uses; [] when none is current."""
    from lib.blocks3 import usace_full, lc_day, twdb_now
    from lib.hero import cdec_avg
    out = []
    ca = cdec_avg(G)
    if ca and ca["c"].get("cap_af"):
        pa = 100 * ca["v"] / ca["c"]["cap_af"]
        out.append(("CDEC capacity", pa < 100, "%.1f%% of capacity%s" % (pa, ("; %s of the %s average" % (ca["pct_avg"], ca["mon"])) if ca.get("avg") else ""), ca["t"], False))
    uf = usace_full(G)
    if uf:
        out.append(("USACE full pool", uf[3] < 0, "%.2f ft %s full pool" % (abs(uf[3]), "below" if uf[3] < 0 else "above"), G["sg"][-1][0], False))
    hit = lc_day(G)
    if hit:
        m = G["rec"]["usbr_lc"]
        out.append(("Reclamation capacity", hit[2] < m["cap_af"], "%.1f%% of capacity to %s ft" % (100 * hit[2] / m["cap_af"], "{:,.0f}".format(m["cap_elev_ft"])), datetime.datetime.fromisoformat(hit[0] + "T12:00:00+00:00"), True))  # daily: shown as a date, never a made-up time (hostile review #7)
    t = twdb_now(G)
    if t and t.get("pct_cons") is not None:
        out.append(("TWDB conservation capacity", t["pct_cons"] < 100, "%.1f%% of conservation capacity" % t["pct_cons"], datetime.datetime.fromisoformat(t["date"] + "T12:00:00+00:00"), True))
    return [x for x in out if _age_h(G, x[3]) <= CURRENT_H]


def lake_levels(built, Gs):
    """Every US lake on the site against its agency's own full mark today; each basis named, never mixed into one number."""
    rows, stale = [], 0
    for r, G in waters(built, Gs, "lake"):
        got = lake_full(G)
        if got:
            rows.append((r, G, got))
        elif any(G["rec"].get(k) for k in ("cdec_res", "usace_pool", "usbr_lc", "twdb")):
            stale += 1
    if len(rows) < MIN_FEW:
        return None
    below = [x for x in rows if all(b[1] for b in x[2])]
    lead = ("<p><b>%d of %d US lakes on this site sit below their agency's full mark right now.</b> "
            "Each agency measures 'full' its own way (feet from the Corps of Engineers' full pool, or a percent of capacity), so the table names the basis for every lake.%s</p>") % (
        len(below), len(rows), (" %d more lake%s an agency figure older than 3 days and %s left out." % (stale, " has" if stale == 1 else "s have", "is" if stale == 1 else "are")) if stale else "")
    hd = ["Lake", "How full, as the agency measures it", "As of"]
    body = (lead + table(hd, "".join(tr([_link(r), "<br>".join(esc(b[2]) for b in got), "<br>".join(esc(fdate(b[3].date().isoformat()) + " (daily figure)" if b[4] else tzl(b[3], G["zone"])) for b in got)]) for r, G, got in rows)) +
            "<h2>How this was worked out</h2><p>Sources, as each lake page's How full block shows them: US Army Corps of Engineers Corps Water Management System top of conservation (full pool) against the USGS lake reading on the same datum; "
            "California Data Exchange Center storage against its stated capacity and its 1991-2020 average for the month; U.S. Bureau of Reclamation Lower Colorado Region daily contents; Texas Water Development Board daily percent of conservation capacity, used only when its level matches USGS's the same day. "
            "Differences and percents not published by the agency are our calculation. Below the full mark is not by itself a shortage: some reservoirs are lowered on purpose, and the Corps' full pool can move with the season.</p>")
    data = _csv(G_HEAD + ["basis", "below_full_mark", "figure", "as_of (date for a daily figure, else UTC time)"], [_g(r) + [b[0], b[1], b[2], b[3].date().isoformat() if b[4] else b[3].astimezone(datetime.timezone.utc).isoformat()] for r, G, got in rows for b in got],
                lambda row: _cred({"CDEC capacity": "cdec", "USACE full pool": "usace_cwms", "Reclamation capacity": "usbr", "TWDB conservation capacity": "twdb"}.get(row[len(G_HEAD)], "usgs"), "usgs"))
    asof = max(b[3] for _, _, got in rows for b in got)
    return _page("How full are US lakes?", "lake-levels", "Every US lake on River Water Levels against its agency's own full mark right now: %d lakes, each basis named." % len(rows), body,
                 "Agency lake and reservoir figures, for the US lakes on this site; newest figure %s UTC. These figures change as agencies publish; cite them with that date and time." % utc_day(asof), data, sample=SAMPLE_LAKE)


def tides(built, Gs):
    """Every NOAA station with its own reading: how far the water ran from NOAA's prediction over the readings we hold (matched 6-minute times), and the predicted range inside that same span.
    Hostile review 2026-11-13: the span is named from the readings themselves (the feed holds about 3 days), never 'this week'."""
    from lib.hero import level_of
    rows, left = [], 0
    for r, G in waters(built, Gs, "coast"):
        c = G["rec"].get("coops") or {}
        if level_of(G) or not G.get("sg"):
            left += 1  # a prediction-only station reads a neighbour's water: the gap would mix two places
            continue
        pr = dict((parse_t(t), v) for t, v in c.get("pred") or [])
        gaps = [(t, v - pr[t]) for t, v, *_ in G["sg"] if t in pr and v is not None]
        if len(gaps) < 240:  # under 24 hours of matched 6-minute readings
            left += 1
            continue
        t0, t1 = gaps[0][0], gaps[-1][0]
        hl = [(parse_t(t), v, k) for t, v, k in c.get("hilo") or [] if t0 <= parse_t(t) <= t1]
        hi_, lo_ = [v for _, v, k in hl if k == "H"], [v for _, v, k in hl if k == "L"]
        rng = (max(hi_) - min(lo_)) if hi_ and lo_ else None
        up, dn = max(gaps, key=lambda x: x[1]), min(gaps, key=lambda x: x[1])
        rows.append((r, G, rng, up, dn, statistics.median(g for _, g in gaps), len(gaps), (t1 - t0).total_seconds() / 86400))
    if len(rows) < MIN_FEW:
        return None
    days = statistics.median(x[7] for x in rows)
    span = "%d days" % round(days) if days >= 1.5 else "%d hours" % round(days * 24)
    top = max(rows, key=lambda x: x[3][1])
    lead = ("<p><b>Over the last %s, the sea ran " + ("furthest above its tide prediction" if top[3][1] > 0 else "nearest to rising above its tide prediction") + " at %s: %+.2f ft at %s.</b> "
            "Across %d NOAA stations on this site, the median gap between observed water and prediction was %+.2f ft. Part of a gap can be steady: local sea level differs from the long-term level NOAA's tide datums are referenced to (at most US stations it has risen since; where the land is rising, as in parts of Alaska, it has fallen), and a season can run above or below its normal level; wind, air pressure and river flow add the rest.%s</p>") % (
        span, _link(top[0]), top[3][1], esc(tzl(top[3][0], top[1]["zone"])), len(rows), statistics.median(x[5] for x in rows),
        (" %s left out (tide predictions only, or under 24 hours of matched readings)." % _pl(left, "station was", "stations were")) if left else "")
    hd = ["Station", "Predicted range in that span", "Highest (observed minus predicted)", "Lowest (observed minus predicted)", "Median gap"]
    body = (lead + table(hd, "".join(tr([_link(r), ("%.1f ft" % rng) if rng is not None else "–", "%+.2f ft<div class=\"src\">%s</div>" % (up[1], esc(tzl(up[0], G["zone"]))),
                                         "%+.2f ft<div class=\"src\">%s</div>" % (dn[1], esc(tzl(dn[0], G["zone"]))), "%+.2f ft" % md_]) for r, G, rng, up, dn, md_, n, d_ in rows), right=(1, 2, 3, 4)) +
            "<h2>How this was worked out</h2><p>Source: NOAA CO-OPS (Tides and Currents) water level observations and tide predictions for each station, the same data its page shows, on the station datum, in feet. "
            "Each gap is the observed level minus the predicted tide at the same 6-minute time, over the readings this site holds for the station (the span is named above); times missing from either series are skipped, and stations with under 24 hours of matched readings are left out. "
            "A positive gap means the water stood above the prediction; the lowest gap can still be positive. The predicted range is the highest predicted high tide minus the lowest predicted low tide inside the same span. Observations are preliminary until NOAA verifies them. Stations that publish predictions only are left out, because their level comes from another place.</p>")
    data = _csv(["noaa_station", "name", "state", "page", "span_days", "predicted_range_ft_in_span", "max_gap_ft", "max_gap_utc", "min_gap_ft", "min_gap_utc", "median_gap_ft", "matched_readings", "fetched_at"],
                [[r["site"], r["river"], r["state"], SITE_URL + r["dashboard_url"], round(d_, 2), "" if rng is None else round(rng, 2), round(up[1], 2), up[0].astimezone(datetime.timezone.utc).isoformat(), round(dn[1], 2), dn[0].astimezone(datetime.timezone.utc).isoformat(), round(md_, 2), n, _fa(G, "coops")]
                 for r, G, rng, up, dn, md_, n, d_ in rows], _cred("coops"))
    return _page("How far did the sea run from its tide prediction?", "tides", "Observed water against NOAA tide predictions over the last %s at %d NOAA stations, with the predicted tide range in the same span." % (span, len(rows)), body,
                 "NOAA water levels and tide predictions, last %s, for the stations on this site; newest reading %s UTC. These figures change every few minutes; cite them with that date and time." % (span, utc_day(max(x[1]["sg"][-1][0] for x in rows))), data, sample=SAMPLE_TIDE)


COUNTRY = {"eccc": "Canada", "pegelonline": "Germany", "ea": "England", "imi": "Ireland"}
BASIS = {"eccc": "Our calculation: today's level ranked among this gauge's past monthly means for the month (Water Survey of Canada publishes no label).",
         "pegelonline": "German Federal Waterways and Shipping Administration (WSV) label: the reading against the gauge's mean low water and mean high water marks.",
         "ea": "The reading against the Environment Agency's own typical range for the gauge, as its Check for flooding service shows it.",
         "imi": "Tidal: the sea rises and falls twice a day, so no low, normal or high label applies."}


def world_rivers(wpages, wkeep, now):
    """(url, html, csv) or None: every published non-US gauge by its agency's own label right now, counted per country, never pooled (each label has its own basis)."""
    from lib.directory import world_live
    by = collections.defaultdict(collections.Counter)
    rows = []
    for page, d in wpages:
        feed = page.get("feed") or "pegelonline"
        keep = wkeep.get(page["slug"]) or set()
        for r in d.get("rows") or []:
            if r.get("name") not in keep:
                continue
            live = world_live(r, now)
            lab = "tidal" if feed == "imi" else (r.get("state") if live and r.get("state") in ("low", "normal", "high") else "not reporting" if not live else "no label")
            by[feed][lab] += 1
            rows.append((feed, page, r, lab))
    labelled = [x for x in rows if x[3] in ("low", "normal", "high")]
    if len(labelled) < MIN_FEW:
        return None
    cs = [f for f in ("eccc", "pegelonline", "ea", "imi") if f in by]

    def share(c, k):
        n = c["low"] + c["normal"] + c["high"]
        return ("%d of %d" % (c[k], n)) if n >= 3 else ("%d" % c[k] if n else "–")
    tb = table(["Country", "Low", "Normal", "High", "Not reporting, tidal or no label"], "".join(
        tr([COUNTRY[f], share(by[f], "low"), share(by[f], "normal"), share(by[f], "high"), str(by[f]["not reporting"] + by[f]["tidal"] + by[f]["no label"])], right=(1, 2, 3, 4)) for f in cs), right=(1, 2, 3, 4))
    lc_ = [f for f in cs if by[f]["low"] + by[f]["normal"] + by[f]["high"]]
    lead = ("<p><b>Right now, by each country's own label: %s.</b> "
            "Each label has its own basis: %s. So the counts are kept country by country and never added across countries.</p>") % (
        "; ".join("%s, %d of %d gauges low and %d high" % (COUNTRY[f], by[f]["low"], by[f]["low"] + by[f]["normal"] + by[f]["high"], by[f]["high"]) for f in lc_),
        "; ".join({"pegelonline": "the WSV's own marks in Germany", "ea": "the Environment Agency's own typical range in England", "eccc": "our rank against past monthly means in Canada, where Water Survey of Canada publishes no label"}[f] for f in ("pegelonline", "ea", "eccc") if by[f]["low"] + by[f]["normal"] + by[f]["high"]))
    nm_ = lambda p: p.get("river") or p["slug"]
    hubs = "".join('<li><a href="/%s/">%s</a>%s</li>' % (esc(p["slug"]), esc(nm_(p)), "" if nm_(p) == COUNTRY.get(p.get("feed") or "pegelonline") else " (%s)" % COUNTRY.get(p.get("feed") or "pegelonline", "")) for p, d in wpages[:30] if wkeep.get(p["slug"]))
    basis = "".join("<li><b>%s:</b> %s</li>" % (COUNTRY[f], esc(BASIS[f])) for f in cs)
    times = sorted(parse_t(x[2]["time"].replace("Z", "+00:00")) for x in labelled)
    body = (lead + tb + "<h2>What each label means</h2><ul>%s</ul>" % basis + "<h2>The rivers and coasts behind these numbers</h2><ul>%s</ul>" % hubs +
            ("<h2>How this was worked out</h2><p>Sources, as each gauge page shows them: Water Survey of Canada real-time levels (Environment and Climate Change Canada), PEGELONLINE (WSV, Germany), the Environment Agency flood-monitoring API (England, Open Government Licence v3.0) and the Marine Institute Irish National Tide Gauge Network (CC BY 4.0). "
             "A reading older than 24 hours is counted as not reporting and gets no label. Labelled readings run from %s to %s UTC. Shares are shown only for a country with at least 3 labelled gauges.</p>") % (
                utc_day(times[0]), utc_day(times[-1])))  # check.py BANNED: no raw machine timestamp shown to a reader
    data = _csv(["country", "page_slug", "gauge", "label", "reading_utc", "label_basis"],
                [[COUNTRY.get(f, f), p["slug"], r.get("title") or r.get("name"), lab, parse_t(r["time"].replace("Z", "+00:00")).astimezone(datetime.timezone.utc).isoformat() if r.get("time") else "", BASIS.get(f, "")] for f, p, r, lab in rows],
                lambda row: _cred({v: k for k, v in COUNTRY.items()}.get(row[0], row[0])))
    sample = ("<p class=\"src\"><b>Sample:</b> the gauges outside the US that have a page on this site, in %s. They are not every gauge in those countries, so the results describe these gauges only.</p>" % ", ".join(COUNTRY[f] for f in cs))
    lab_c = [COUNTRY[f] for f in cs if by[f]["low"] + by[f]["normal"] + by[f]["high"]]  # hostile review #12: the title names only countries with a labelled gauge
    return _page("Are rivers in %s low or high right now?" % (", ".join(lab_c[:-1]) + " and " + lab_c[-1] if len(lab_c) > 1 else lab_c[0]), "world-rivers",
                 "Gauges outside the US on River Water Levels by a low, normal or high label right now, each label's basis named, counted country by country.", body,
                 "Agency river levels in %s, for the gauges on this site; newest reading %s UTC. These labels change as the agencies publish; cite them with that date and time." % (", ".join(COUNTRY[f] for f in cs), utc_day(times[-1])), data, sample=sample)


def title_of(html):
    """The page's own title without the brand, or '' (the index links the world page by its real title)."""
    m = re.search(r"<title>(.*?) \| ", html or "")
    return __import__("html").unescape(m.group(1)) if m else ""


def _lead(html):
    m = re.search(r"<p>(?:<[^>]+>)*?<b>(.*?)</b>", html.split('class="prose"', 1)[-1], re.S)
    return re.sub(r"<[^>]+>", "", m.group(1)) if m else ""


def _num(s):
    return float(s.replace(",", ""))


def verify(url, html, data):
    """PLAN 22 lock 2: the page's headline numbers recomputed from its own published CSV. [] when they match; else what differs (build.py then drops the page).
    Each finding is checked from the CSV alone, the way an outside reader would check it."""
    if not data:
        return [] if url == "/research/" else ["no CSV"]
    rows = list(csv.DictReader(io.StringIO(data)))
    lead, bad = _lead(html), []
    T = lambda v: str(v).strip().lower() == "true"
    if url.endswith("/peak-month/"):
        nat = [r for r in rows if not T(r["regulated"])]
        c = collections.Counter(r["peak_month_most_often"] for r in nat if " and " not in r["peak_month_most_often"])
        m = re.search(r"comes in (\w+): at (\d+) of (\d+) gauges", lead)
        if not m or c.most_common(1)[0] != (m.group(1), int(m.group(2))) or len(nat) != int(m.group(3)):
            bad.append("peak month lead %r against CSV %s of %d" % (m and m.group(0), c.most_common(1), len(nat)))
    elif url.endswith("/peak-change/"):
        nat = [r for r in rows if not T(r["regulated"])]
        up = sum(1 for r in nat if float(r["mann_whitney_p"]) < ALPHA and float(r["hodges_lehmann_shift_cfs"]) > 0)
        dn = sum(1 for r in nat if float(r["mann_whitney_p"]) < ALPHA and float(r["hodges_lehmann_shift_cfs"]) < 0)
        k = bh_count([float(r["mann_whitney_p"]) for r in nat])
        m = re.search(r"(\d+) tested higher and (\d+) lower", html) or re.search(r"before it, (\d+) tested higher and (\d+) lower", html)
        g = re.search(r"Across (\d+) gauges|of (\d+) gauges, yearly peaks", lead)
        if not m or (int(m.group(1)), int(m.group(2))) != (up, dn) or not g or int(g.group(1) or g.group(2)) != len(nat) or (k == 0) != ("stands out from chance" in lead):
            bad.append("peak change counts on the page differ from the CSV (up %d, down %d, gauges %d, corrected %d)" % (up, dn, len(nat), k))
    elif url.endswith("/100-year-floods/"):
        nat = [r for r in rows if not T(r["regulated"])]
        hit, yrs = sum(len(r["years_reached"].split()) for r in nat), sum(int(r["water_years_counted"]) for r in nat)
        m = re.search(r"At (\d+) US river gauges.*?reached in (\d+) of (\d+) gauge-years", lead)
        if not m or (int(m.group(1)), int(m.group(2)), int(m.group(3))) != (len(nat), hit, yrs):
            bad.append("100-year lead %r against CSV %d gauges, %d of %d" % (m and m.group(0), len(nat), hit, yrs))
    elif url.endswith("/flood-stage-years/"):
        sh = [100 * int(r["water_years_peak_reached_it"]) / int(r["water_years_with_peak_stage"]) for r in rows if not T(r.get("regulated"))]
        m = re.search(r"in (\d+)% of years", lead)
        if not m or int(m.group(1)) != round(statistics.median(sh)):
            bad.append("flood stage lead %r against CSV median %.0f%%" % (m and m.group(0), statistics.median(sh)))
    elif url.endswith("/water-temperature/"):
        m = re.search(r"averages (\d+)", lead)
        jul = [float(r["mean_f_july"]) for r in rows if r["mean_f_july"]]
        if not m or int(m.group(1)) != round(statistics.median(jul)):
            bad.append("water temperature lead %r against CSV July median %.1f" % (m and m.group(0), statistics.median(jul)))
    elif url.endswith("/lake-levels/"):
        by = collections.defaultdict(list)
        for r in rows:
            by[r["usgs_site"]].append(T(r["below_full_mark"]))
        m = re.search(r"(\d+) of (\d+) US lakes", lead)
        if not m or (int(m.group(1)), int(m.group(2))) != (sum(1 for v in by.values() if all(v)), len(by)):
            bad.append("lake lead %r against CSV" % (m and m.group(0)))
    elif url.endswith("/tides/"):
        m = re.search(r"Across (\d+) NOAA stations", html)
        if not m or int(m.group(1)) != len(rows):
            bad.append("tide station count against CSV %d" % len(rows))
    elif url.endswith("/world-rivers/"):
        got_ = {c: (int(a), int(b), int(h)) for c, a, b, h in re.findall(r"(\w+), (\d+) of (\d+) gauges low and (\d+) high", lead)}
        want_ = {}
        for r in rows:
            if r["label"] in ("low", "normal", "high"):
                lo_, n_, hi_ = want_.get(r["country"], (0, 0, 0))
                want_[r["country"]] = (lo_ + (r["label"] == "low"), n_ + 1, hi_ + (r["label"] == "high"))
        if got_ != want_:
            bad.append("world lead %r against CSV %r" % (got_, want_))
    else:
        bad.append("no reproducibility check for %s: a new research page needs one" % url)
    return bad


FAILED = []  # [(url, why)] from the last pages() call: pages dropped because their CSV did not reproduce their headline (build.py names them on the dashboard)


def pages(built, Gs, today=None, world=False):
    """({url: html}, {url: csv text}): the research index and every finding with enough data; ({}, {}) when none has (build.py then carries the published copies)."""
    today = today or datetime.date.today()
    gl = gauges(built, Gs)
    unk = unknown_codes(gl)
    wys = [max(p) for _, p, _ in gl if p]
    sub = "USGS annual peaks through water year %d at most gauges, for the US river gauges on this site." % statistics.median_low(wys) if wys else "USGS annual peaks, for the US river gauges on this site."  # review #10: the typical newest year, not the newest at any one gauge
    got = [x for x in ((peak_month(gl, sub, unk), peak_change(gl, today, sub, unk), hundred_year(gl, unk), flood_stage(gl), water_temp(gl)) if gl else ()) + (lake_levels(built, Gs), tides(built, Gs)) if x]
    FAILED.clear()
    for x in list(got):  # PLAN 22 lock 2: a page whose headline its own CSV does not reproduce is never published
        why = verify(*x)
        if why:
            FAILED.append((x[0], "; ".join(why)))
            got.remove(x)
    if not got:
        return {}, {}
    items = "".join('<li><a href="%s">%s</a></li>' % (u, esc(title_of(h))) for u, h, _ in got)  # title_of unescapes, so a title is escaped once (final check 2026-11-13: '&amp;#x27;' showed as text)
    items += ('<li><a href="%s">%s</a></li>' % (WORLD_URL, esc(world))) if isinstance(world, str) and world else ""  # the world page's own title (verification 2026-11-13: a hard-coded title named Ireland)
    idx = _page("Research", "", "Original findings from the rivers, lakes and coasts on River Water Levels: our own calculations from agency records.",
                "<p>Findings worked out from the records behind every page on this site. Each page states its sample, its method and tests, and what it cannot tell you, and offers its data as a CSV file.</p><ul>%s</ul>" % items,
                "Our own calculations from USGS, NOAA, National Weather Service and other agency records.")
    return dict((u, h) for u, h, _ in [idx] + got), dict((u, d) for u, _, d in got if d)
