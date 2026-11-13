"""Research pages (owner 2026-11-12: original posts, as slabcalc publishes research; 'PubMed worthy'). Edge cases: PLAN 14, 15, 17.
Each page is our own calculation across every gauge page, from data already in the cache (USGS annual peaks with their qualifier codes, flood statistics,
water temperature; NWS flood stages); rebuilt every run, so it grows with the site. Each states its sample, its tests and its limits, and publishes its table as CSV.
A finding with too few gauges is not published."""
import calendar, collections, csv, io, math, re, statistics
import datetime
from lib.common import *
from lib.core import table, tr
from lib.directory import shell, crumb_ld, STATE_NAMES

MIN_PEAKS = 20  # water years of annual peaks a gauge needs before its peak month is counted
WIN = 20  # water years in each period of the recent-vs-earlier comparison
MIN_IN_WIN = 15  # of the 20, how many must have a usable peak
MIN_GAUGES = 10  # below this a finding is not published
ALPHA = 0.05  # two-sided significance level of the per-gauge test
ROW_CAP = 1000  # ponytail: one table of every gauge, about 150 KB at 1,000 rows; per-state pages when the site passes 1,000 river gauges
HL = 25  # rows in a linked highlight table (check.py BUDGET trust 60, with the nav and footer)
URLS = ("/research/", "/research/peak-month/", "/research/peak-change/", "/research/100-year-floods/", "/research/flood-stage-years/", "/research/water-temperature/")
MN = calendar.month_name
# USGS peak qualifier codes (read live 2026-11-12 on 01646500, 09380000, 07289000, 03294500)
DROP = {"HISTORIC", "MAXDAILYMEAN", "DAMFAILURE", "MONTHUNKNOWN"}  # outside the systematic record, a daily mean not an instantaneous peak, a dam break, no month
REG = {"REGULATED", "UNKNOWNREGULATION"}  # flow changed by dams or diversions: studied apart
KEEP = {"ESTIMATED", "REVISED", "DAYUNKNOWN"}  # USGS's own value stands
SAMPLE = ("<p class=\"src\"><b>Sample:</b> the US river gauges that have a page on this site, chosen by what people search for. They are not a random or representative sample of US rivers, "
          "so the results describe these gauges, not the country.</p>")


def _wy(y, m):
    """USGS water year: Oct 1 to Sep 30, named for the year it ends in."""
    return y + (1 if m >= 10 else 0)


def _codes(fq):
    return set(str(fq or "").split())


def _peaks(G):
    """{water year: (month, flow, regulated)}: the highest usable flow peak in each water year. None when the cache row has no qualifier field
    (written before 2026-11-12): without the codes a daily-mean or historic peak cannot be told apart, so the gauge waits for its weekly refresh."""
    rows = (G["rec"].get("peaks") or {}).get("rows") or []
    if any(len(r) < 5 for r in rows):
        return None
    out = {}
    for r in rows:
        t, v, c = str(r[0]), r[1], _codes(r[4])
        try:
            y, m = int(t[:4]), int(t[5:7])
        except ValueError:
            continue
        if v is None or v <= 0 or not 1 <= m <= 12 or c & DROP or any("THAN" in x for x in c):
            continue  # stage-only peak, unknown month, or a code that misstates the value (LESSTHAN / GREATERTHAN)
        w = _wy(y, m)
        if w not in out or v > out[w][1]:
            out[w] = (m, float(v), bool(c & REG))
    return out


def unknown_codes(gl):
    """Peaks carrying a code this module does not know: counted on every page, never silently used or dropped."""
    n = collections.Counter()
    for _, _, G in gl:
        for r in (G["rec"].get("peaks") or {}).get("rows") or []:
            if len(r) >= 5:
                for x in _codes(r[4]) - DROP - REG - KEEP:
                    if "THAN" not in x:
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
    rank, i, ties = {}, 0, 0.0
    ranks = [0.0] * len(allv)
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1][0] == allv[i][0]:
            j += 1
        for k in range(i, j + 1):
            ranks[k] = (i + j) / 2 + 1
        t = j - i + 1
        ties += t ** 3 - t
        i = j + 1
    r1 = sum(rk for rk, (_, g) in zip(ranks, allv) if g == 0)
    u = r1 - n1 * (n1 + 1) / 2
    n = n1 + n2
    var = n1 * n2 / 12 * ((n + 1) - ties / (n * (n - 1)))
    if var <= 0:
        return 1.0
    z = (abs(u - n1 * n2 / 2) - 0.5) / math.sqrt(var)
    return min(1.0, math.erfc(max(z, 0) / math.sqrt(2)))


def poisson_tail(k, lam):
    """Chance of a count at least k (k >= lam) or at most k (k < lam) when the count is Poisson with mean lam; in log space (no underflow at lam = 300)."""
    if lam <= 0:
        return 1.0
    terms = range(0, k) if k >= lam else range(0, k + 1)
    logs = [-lam + i * math.log(lam) - math.lgamma(i + 1) for i in terms]
    if not logs:
        s = 0.0
    else:
        mx = max(logs)
        s = math.exp(mx) * sum(math.exp(x - mx) for x in logs)
    return max(0.0, min(1.0, 1 - s if k >= lam else s))


def _link(r):
    return '<a href="%s">%s at %s</a>' % (r["dashboard_url"], esc(r["river"]), esc(r["place"]))


def _name(r):
    """Full tables name the gauge without a link (check.py BUDGET trust 60): only the short highlight tables link, and the site search finds any river."""
    return "%s at %s" % (esc(r["river"]), esc(r["place"]))


def _cap(n, what="annual peaks"):
    return "<p>%d more gauges are not listed here; each gauge page has its own %s, and the CSV lists them all.</p>" % (n - ROW_CAP, what) if n > ROW_CAP else ""


def _csv(head, rows):
    """CSV text; a text cell starting with = + - @ gets an apostrophe so a spreadsheet never runs it as a formula (numbers are written as numbers)."""
    b = io.StringIO()
    w = csv.writer(b, lineterminator="\n")
    w.writerow(head)
    for r in rows:
        w.writerow([("'" + c) if isinstance(c, str) and c[:1] in "=+-@" else c for c in r])
    return b.getvalue()


def _g(r):
    return [r["site"], r["river"], r["place"], r["state"], SITE_URL + r["dashboard_url"]]


G_HEAD = ["usgs_site", "river", "place", "state", "page"]


def _page(title, slug, desc, body, sub, data=None, unk=None):
    """(url, html, csv or None). No build date on the page: the same data must give the same page (Google: fresh dates without change)."""
    url = "/research/%s/" % slug if slug else "/research/"
    crumbs = [("Home", "/"), ("Research", None)] if not slug else [("Home", "/"), ("Research", "/research/"), (title, None)]
    vis = '<a href="/">Home</a> / Research' if not slug else '<a href="/">Home</a> / <a href="/research/">Research</a> / %s' % esc(title)
    extra = ""
    if slug:
        extra += SAMPLE
        if unk:
            extra += '<p class="src">USGS codes this page does not yet sort: %s. Those peaks are counted as USGS published them.</p>' % ", ".join("%s (%d peaks)" % (esc(k), v) for k, v in sorted(unk.items()))
        if data:
            extra += '<p><a href="data.csv">Download the data for every gauge (CSV)</a>, one row per gauge, for checking or reuse with a link back.</p>'
    return url, shell(title + " | " + BRAND, desc, url, '<div class="crumb">%s</div><div class="prose"><h1>%s</h1><p class="sub">%s</p>%s%s</div>' % (
        vis, esc(title), sub, body, extra), ld=crumb_ld(crumbs)), data


def _months(ms):
    return " and ".join(MN[m] for m in ms)


def peak_month(gl, sub, unk):
    """Which month each river's yearly high most often falls in; regulated gauges counted apart."""
    rows, lead_n, by_state, ties = [], collections.Counter(), collections.defaultdict(collections.Counter), 0
    for r, p, _ in gl:
        if not p or len(p) < MIN_PEAKS:
            continue
        reg = sum(1 for v in p.values() if v[2]) > len(p) / 2
        c = collections.Counter(v[0] for v in p.values())
        n = max(c.values())
        ms = sorted(m for m, k in c.items() if k == n)
        if not reg:
            if len(ms) == 1:
                lead_n[ms[0]] += 1
                by_state[r["state"]][ms[0]] += 1
            else:
                ties += 1
        rows.append((r, ms, n, len(p), min(p), max(p), reg))
    nat = [x for x in rows if not x[6]]
    if len(nat) < MIN_GAUGES:
        return None
    top = lead_n.most_common(3)
    lead = "<p><b>Of %d US river gauges on this site with %d or more usable years of USGS annual peaks and no regulation code on most of them, the yearly high most often comes in %s (%d gauges)%s.</b> " % (
        len(nat), MIN_PEAKS, MN[top[0][0]], top[0][1], "".join(", %s %s (%d)" % ("then" if i == 1 else "and", MN[m], k) for i, (m, k) in enumerate(top[1:], 1))) if top else "<p>"
    lead += "For each gauge we took the highest usable peak of every water year on file and counted the months they fell in.%s%s</p>" % (
        " %d gauge%s split evenly between two or more months and %s not counted in the totals." % (ties, "" if ties == 1 else "s", "is" if ties == 1 else "are") if ties else "",
        " %d gauges whose peaks USGS mostly marks as affected by dams or diversions are listed but not counted." % (len(rows) - len(nat)) if len(rows) > len(nat) else "")
    months = table(["Month", "Gauges whose yearly high most often falls in it"], "".join(tr([MN[m], str(lead_n.get(m, 0))], right=(1,)) for m in range(1, 13)), right=(1,))
    st = ""
    for s, c in sorted(by_state.items()):
        k = max(c.values())
        st += tr([esc(STATE_NAMES.get(s, s)), str(sum(c.values())), "%s (%d of %d)" % (_months(sorted(m for m, v in c.items() if v == k)), k, sum(c.values()))], right=(1,))
    gt = table(["Gauge", "State", "Peak month most often", "Water years used"], "".join(
        tr([_name(r) + (" (regulated)" if rg else ""), esc(r["state"]), "%s (%d of %d years, %d%%%s)" % (_months(ms), n, k, round(100 * n / k), " each" if len(ms) > 1 else ""), "%d (%d to %d)" % (k, y0, y1)], right=(3,))
        for r, ms, n, k, y0, y1, rg in rows[:ROW_CAP]), right=(3,))
    data = _csv(G_HEAD + ["peak_month_most_often", "years_in_that_month", "water_years_used", "first_water_year", "last_water_year", "regulated"],
                [_g(r) + [" and ".join(MN[m] for m in ms), n, k, y0, y1, rg] for r, ms, n, k, y0, y1, rg in rows])
    body = (lead + "<h2>By month</h2>" + months + "<h2>By state</h2>" + table(["State", "Gauges", "Most common peak month"], st, right=(1,)) +
            "<h2>Every gauge</h2><p>Find your river: the month its yearly high has come most often, and how often. Each gauge page has the full list of its annual peaks.</p>" + gt + _cap(len(rows)) +
            "<h2>How this was worked out</h2><p>Source: USGS annual peak streamflow (Water Data API), as each gauge page's Largest annual peaks block shows it, with USGS's qualifier codes. An annual peak is the highest instantaneous flow in a water year (October to September); where USGS lists more than one peak in a water year, the highest is used. "
            "Left out: peaks USGS codes as historic (outside the regular record), as a maximum daily mean instead of an instantaneous peak, as a dam failure, as less than or greater than the value shown, or with an unknown month. "
            "A gauge counts as regulated when USGS codes most of its peaks as affected by regulation or diversion. The most common month is not a forecast; in many years the high comes in another month, as the share shows.</p>")
    return _page("When US rivers reach their yearly high", "peak-month", "The month each river's yearly high flow most often falls in, from USGS annual peaks at %d US river gauges." % len(nat), body, sub, data, unk)


def peak_change(gl, today, sub, unk):
    """Median yearly peak in the last 20 complete water years against the 20 before, per gauge, with a two-sided Mann-Whitney test."""
    end = _wy(today.year, today.month) - 1  # the last complete water year; changes once a year, on Oct 1
    rows = []
    for r, p, _ in gl:
        if not p:
            continue
        rec = [p[y] for y in range(end - WIN + 1, end + 1) if y in p]
        old = [p[y] for y in range(end - 2 * WIN + 1, end - WIN + 1) if y in p]
        if len(rec) >= MIN_IN_WIN and len(old) >= MIN_IN_WIN:
            a, b = statistics.median(v[1] for v in old), statistics.median(v[1] for v in rec)
            rows.append((r, a, b, (b - a) / a * 100, mwu_p([v[1] for v in old], [v[1] for v in rec]), any(v[2] for v in rec + old), len(old), len(rec)))
    nat = [x for x in rows if not x[5]]
    if len(nat) < MIN_GAUGES:
        return None
    span = lambda a, b: "%d to %d" % (a, b)
    P1, P2 = span(end - 2 * WIN + 1, end - WIN), span(end - WIN + 1, end)
    sig_up = [x for x in nat if x[4] < ALPHA and x[2] > x[1]]
    sig_dn = [x for x in nat if x[4] < ALPHA and x[2] < x[1]]
    lead = ("<p><b>At %d US river gauges on this site with enough usable peaks in both periods and no regulation code, the median yearly peak of water years %s differed from %s by a statistically significant amount at %d: higher at %d, lower at %d. "
            "Chance alone would flag about %.0f of %d.</b> The middle gauge changed by %+.0f%%. This compares typical yearly floods, not the largest ones, and does not say why they changed.%s</p>") % (
        len(nat), P2, P1, len(sig_up) + len(sig_dn), len(sig_up), len(sig_dn), ALPHA * len(nat), len(nat), statistics.median(x[3] for x in nat),
        (" %d gauges with peaks USGS codes as affected by dams or diversions are listed apart, not counted." % (len(rows) - len(nat))) if len(rows) > len(nat) else "")
    hd = ["Gauge", "Median peak %s" % P1, "Median peak %s" % P2, "Change (p)"]
    rw = lambda xs, f=_link: "".join(tr([f(r) + (" (regulated)" if rg else ""), "%s cfs" % fmtc(a), "%s cfs" % fmtc(b), "%+.0f%% (%s)" % (c, "%.3f" % pv if pv >= 0.001 else "&lt;0.001")], right=(1, 2, 3)) for r, a, b, c, pv, rg, _, _ in xs)
    meth = ("<h2>How this was worked out</h2><p>Source: USGS annual peak streamflow (Water Data API), with USGS's qualifier codes. For each gauge we took the highest usable peak in each water year (October to September), "
            "then compared the %d water years %s with the %d before, keeping gauges with at least %d usable years in each period (USGS publishes the newest year's peak months after it ends). "
            "Left out: peaks coded historic, maximum daily mean, dam failure, less than or greater than, or with an unknown month. A gauge with any peak coded as affected by regulation or diversion in either period is listed apart. "
            "The test is a two-sided Mann-Whitney U test (normal approximation, corrected for ties) of the two periods' peaks, significant at p &lt; %.2f; p is the chance of a difference this large if both periods came from the same distribution. "
            "Testing many gauges at once means about 1 in 20 shows a significant difference by chance, which is why the expected count is given. Peaks in neighbouring years and at neighbouring gauges are not independent, so the tests are approximate. "
            "Reasons a gauge changes include rain and snow patterns, water use, land development and gauge moves. This is a comparison of two periods, not a trend analysis of the whole record.</p>") % (WIN, P2, WIN, MIN_IN_WIN, ALPHA)
    data = _csv(G_HEAD + ["median_peak_cfs_%s" % P1.replace(" to ", "_"), "median_peak_cfs_%s" % P2.replace(" to ", "_"), "change_pct", "mann_whitney_p", "regulated", "years_used_first_period", "years_used_second_period"],
                [_g(r) + [round(a, 1), round(b, 1), round(c, 1), round(pv, 4), rg, n1, n2] for r, a, b, c, pv, rg, n1, n2 in rows])
    body = (lead + ("<h2>Largest significant rises</h2>" + table(hd, rw(sorted(sig_up, key=lambda x: -x[3])[:12]), right=(1, 2, 3)) if sig_up else "") +
            ("<h2>Largest significant falls</h2>" + table(hd, rw(sorted(sig_dn, key=lambda x: x[3])[:12]), right=(1, 2, 3)) if sig_dn else "") +
            "<h2>Every gauge</h2>" + table(hd, rw(rows[:ROW_CAP], _name), right=(1, 2, 3)) + _cap(len(rows)) + meth)
    return _page("Are yearly river floods getting bigger?", "peak-change", "The median yearly peak flow of the last 20 water years against the 20 before, tested gauge by gauge, at %d US river gauges, from USGS annual peaks." % len(nat), body, sub, data, unk)


def _yr_end(rng):
    ys = [int(y) for y in re.findall(r"\d{4}", rng or "")]
    return ys[-1] if ys else None


def hundred_year(gl, unk):
    """How often the USGS 1%-chance ('100-year') flow was reached in the years after the record USGS computed it from (out of sample), with a Poisson test."""
    rows = []
    for r, p, G in gl:
        if not p:
            continue
        f = G["rec"].get("floodfreq") or {}
        one = next((x for x in f.get("rows") or [] if x.get("aep") == 1 and x.get("q")), None)
        end = _yr_end(f.get("range"))
        if f.get("conflict") or not one or not end:
            continue  # as the gauge page: a conflicting statistic is not shown; no 1% row or no record years = nothing to test
        after = sorted((y, v[1], v[2]) for y, v in p.items() if y > end)
        if len(after) < 5:
            continue
        reg = bool(f.get("regulated")) or any(x[2] for x in after)
        lo, hi = one.get("lo"), one.get("hi")
        rows.append((r, one["q"], end, after, [y for y, v, _ in after if v >= one["q"]], reg, lo, hi,
                     sum(1 for _, v, _ in after if lo and v >= lo) if lo and hi else None, sum(1 for _, v, _ in after if hi and v >= hi) if lo and hi else None))
    nat, reg = [x for x in rows if not x[5]], [x for x in rows if x[5]]
    if len(nat) < MIN_GAUGES:
        return None
    def say(xs, what):
        yrs, hit = sum(len(x[3]) for x in xs), sum(len(x[4]) for x in xs)
        if not xs:
            return ""
        return ("At %d %s, the 1%%-chance flow was reached in %d of %d gauge-years after the records USGS computed it from; a 1%% chance each year implies about %.1f "
                "(chance of a count this far from that or farther, if every gauge-year were an independent 1%% chance: %s).") % (len(xs), what, hit, yrs, yrs / 100, "%.3f" % poisson_tail(hit, yrs / 100) if poisson_tail(hit, yrs / 100) >= 0.001 else "under 0.001")
    ci = [x for x in nat if x[8] is not None]
    cis = ("<p>Against USGS's own confidence interval for the 1%%-chance flow, published at %d of these gauges: %d gauge-years reached its lower bound and %d its upper bound, of %d gauge-years (expected under 1%% chance: %.1f).</p>" % (
        len(ci), sum(x[8] for x in ci), sum(x[9] for x in ci), sum(len(x[3]) for x in ci), sum(len(x[3]) for x in ci) / 100)) if len(ci) >= MIN_GAUGES else ""
    lead = "<p><b>%s</b> %s A '100-year flood' is a flow with a 1%% chance of being reached in any year, not one flood per century.</p>" % (
        say(nat, "US river gauges on this site with no regulation flag from USGS"), say(reg, "gauges USGS flags as affected by dams or diversions"))
    hit = sorted([x for x in rows if x[4]], key=lambda x: (-len(x[4]), x[0]["river"]))
    hd = ["Gauge", "1%-chance flow (USGS)", "Record USGS used ends", "Years since", "Years at or above it"]
    tb = table(hd, "".join(tr([_link(x[0]) + (" (regulated)" if x[5] else ""), "%s cfs" % fmtc(x[1]), "Water year %d" % x[2], str(len(x[3])), ", ".join(str(y) for y in x[4])], right=(1, 3)) for x in hit[:HL]), right=(1, 3)) if hit else "<p>None of these gauges has reached its 1%-chance flow since.</p>"
    data = _csv(G_HEAD + ["q_1pct_cfs", "q_1pct_lower_cfs", "q_1pct_upper_cfs", "statistic_record_ends_wy", "water_years_after", "years_at_or_above_q_1pct", "years_at_or_above_lower", "years_at_or_above_upper", "regulated"],
                [_g(x[0]) + [x[1], x[6] or "", x[7] or "", x[2], len(x[3]), " ".join(str(y) for y in x[4]), "" if x[8] is None else x[8], "" if x[9] is None else x[9], x[5]] for x in rows])
    body = (lead + cis + "<h2>Gauges that reached it since</h2>" + tb + ("<p>%d more gauges; the CSV lists them all.</p>" % (len(hit) - HL) if len(hit) > HL else "") +
            "<h2>How this was worked out</h2><p>Sources: USGS StreamStats gage statistics (peak-flow statistics: 1% annual exceedance probability flow, its confidence interval where published, and the record years USGS states) and USGS annual peak streamflow (Water Data API) with its qualifier codes, as each gauge page shows them. "
            "For each gauge we took the highest usable peak of every water year after the last year of the record the statistic was computed from, so the test uses only years the statistic never saw, and counted the years at or above the 1% flow; gauges with fewer than 5 such years are left out. "
            "Left out: peaks coded historic, maximum daily mean, dam failure, less than or greater than, or with an unknown month; statistics USGS publishes in conflicting versions. A gauge USGS flags as regulated, or with a later peak coded as affected by regulation, is counted apart. "
            "The chance shown is a one-sided Poisson tail on the total count. It assumes every gauge-year is an independent 1% chance; neighbouring gauges flood in the same storms, so the true spread is wider and the chance shown is too small.</p>")
    return _page("How often do '100-year floods' happen?", "100-year-floods", "How often the USGS 100-year (1%%-chance) flood flow was reached after USGS computed it, tested against chance, at %d US river gauges." % len(nat), body,
                 "USGS flood statistics and annual peaks, for the US river gauges on this site.", data, unk)


def flood_stage(gl):
    """Share of years whose peak stage reached NWS minor flood stage: the same rule as the gauge page (lib/blocks3.stage_years, one peak per water year)."""
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
    data = _csv(G_HEAD + ["nws_minor_flood_stage_ft", "water_years_peak_reached_it", "water_years_with_peak_stage", "first_year", "last_year"], [_g(x[0]) + [x[1], x[2], x[3], x[4], x[5]] for x in rows])
    body = (lead + "<h2>Gauges that reach flood stage most often</h2>" + table(hd, "".join(map(row(_link), top)), right=(1, 2)) +
            "<h2>Every gauge</h2>" + table(hd, "".join(map(row(_name), rows[:ROW_CAP])), right=(1, 2)) + _cap(len(rows), "flood record") +
            "<h2>How this was worked out</h2><p>Sources: USGS annual peak gage heights (Water Data API) and National Weather Service flood stages (National Water Prediction Service), as each gauge page's Annual peaks that reached flood stage block shows them. "
            "A gauge is counted only where the NWS-observed stage and the USGS gage height read within 0.3 ft of each other, so both are on the same zero point; peaks USGS marks with any qualifier other than estimated are left out, each water year counts once at its highest stage, and gauges with fewer than 10 usable water years are left out. "
            "Record lengths differ from gauge to gauge, so shares cover different periods. Older peaks can be on an older gauge datum, and flood stages are set for today's channel.</p>")
    return _page("How often do rivers reach flood stage?", "flood-stage-years", "The share of years each river's yearly peak reached National Weather Service minor flood stage, at %d US river gauges." % len(rows), body,
                 "USGS annual peak stages and NWS flood stages, for the US river gauges on this site.", data)


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
    hd = ["Gauge", "January", "April", "July", "October"]  # 5 columns (check.py wide_tables): the record years sit under the gauge name
    row = lambda g: lambda x: tr(['%s<div class="src">Sensor record %s to %s</div>' % (g(x[0]), x[2], x[3])] + [f(m, x[1]) for m in (1, 4, 7, 10)], right=(1, 2, 3, 4))
    by = sorted(rows, key=lambda x: x[1][7])
    data = _csv(G_HEAD + ["mean_f_%s" % MN[m].lower() for m in range(1, 13)] + ["first_year", "last_year"], [_g(x[0]) + [round(x[1][m], 1) if m in x[1] else "" for m in range(1, 13)] + [x[2], x[3]] for x in rows])
    body = (lead + "<h2>Coldest in July</h2>" + table(hd, "".join(map(row(_link), by[:HL // 2])), right=(1, 2, 3, 4)) +
            "<h2>Warmest in July</h2>" + table(hd, "".join(map(row(_link), by[::-1][:HL // 2])), right=(1, 2, 3, 4)) +
            "<h2>Every gauge</h2>" + table(hd, "".join(map(row(_name), rows[:ROW_CAP])), right=(1, 2, 3, 4)) + _cap(len(rows), "water temperature by month") +
            "<h2>How this was worked out</h2><p>Source: USGS daily mean water temperature (Water Data API), as each gauge page's Typical water temperature by month block shows it: the mean of every published daily value in each calendar month over the record years shown. "
            "A month with fewer than 150 daily values is shown as a dash. Sensor records cover different years at different gauges, so gauges are not compared over the same period, and years with more readings weigh more in a mean. "
            "A sensor can sit in a deep or shaded spot, and a dam upstream can release cold water from the bottom of its lake, so the water where you get in can differ.</p>")
    return _page("How warm are US rivers?", "water-temperature", "Typical January, April, July and October water temperature at %d US river gauges, from USGS sensor records." % len(rows), body,
                 "USGS water temperature records, for the US river gauges on this site.", data)


def pages(built, Gs, today=None):
    """({url: html}, {url: csv text}): the research index and every finding with enough gauges; ({}, {}) when none has (build.py then carries the published copies)."""
    today = today or datetime.date.today()
    gl = gauges(built, Gs)
    if not gl:
        return {}, {}
    unk = unknown_codes(gl)
    wys = [max(p) for _, p, _ in gl if p]
    sub = "USGS annual peaks through water year %d, for the US river gauges on this site." % max(wys) if wys else "USGS annual peaks, for the US river gauges on this site."
    got = [x for x in (peak_month(gl, sub, unk), peak_change(gl, today, sub, unk), hundred_year(gl, unk), flood_stage(gl), water_temp(gl)) if x]
    if not got:
        return {}, {}
    items = "".join('<li><a href="%s">%s</a></li>' % (u, esc(h.split("<title>")[1].split(" | ")[0])) for u, h, _ in got)
    idx = _page("Research", "", "Original findings from the river gauges on River Water Levels: our own calculations from USGS records.",
                "<p>Findings worked out from the records behind every gauge page on this site. Each page states its sample, its method and tests, and what it cannot tell you, and offers its data as a CSV file.</p><ul>%s</ul>" % items + SAMPLE,
                "Our own calculations from USGS and National Weather Service records.")
    return dict((u, h) for u, h, _ in [idx] + got), dict((u, d) for u, _, d in got if d)
