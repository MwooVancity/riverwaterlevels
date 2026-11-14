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
MIN_GAUGES = 10  # below this a finding is not published
MIN_FEW = 5  # lakes and tide stations are few on this site: 5 is the floor for those pages
# Cut 2026-11-14 (owner, information-gain test): 'Are floods getting worse?' and '100-year floods' answered national questions from a small, search-picked
# sample while USGS, EPA and FEMA publish the same on thousands of gauges. data/research-gain.json now holds every finding's gain line; no line, no page.
ROW_CAP = 1000  # ponytail: one table of every gauge, about 150 KB at 1,000 rows; per-state pages when the site passes 1,000 river gauges
HL = 25  # rows in a linked highlight table (check.py BUDGET trust 60, with the nav and footer)
URLS = ("/research/", "/research/peak-month/", "/research/flood-stage-years/", "/research/water-temperature/", "/research/lake-levels/", "/research/tides/")
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


def gain_ok(url):
    """True only for a finding with a 'keep' verdict, an 'exists' line and a 'gain' line in data/research-gain.json (owner 2026-11-14: the information-gain test
    comes before any polish). A missing or torn file builds no finding (fail closed); the index needs no line."""
    if url == "/research/":
        return True
    try:
        g = __import__("json").load(open(__import__("os").path.join(ROOT, "data", "research-gain.json"), encoding="utf-8")).get(url) or {}
    except (OSError, ValueError):
        return False
    return g.get("verdict") == "keep" and bool(str(g.get("exists") or "").strip()) and bool(str(g.get("gain") or "").strip())


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
    return '<a href="%s">%s</a>' % (r["dashboard_url"], esc(river_at(r["river"], r["place"])))  # read-through 2026-11-14: 'Garibaldi at Garibaldi'; the site's one naming rule


def _name(r):
    """Full tables name the gauge without a link (check.py BUDGET trust 60): only the short highlight tables link, and the site search finds any river."""
    return esc(river_at(r["river"], r["place"]))


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
    return _page("Flood season: when US rivers reach their yearly high", "peak-month", "The month each river's yearly high flow most often falls in, its average date and how tightly peaks cluster, from USGS annual peaks at %d US river gauges." % len(nat), body, sub, data, unk)




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
            "The National Weather Service defines flood stage as the gage height at a given place above which rising water begins to threaten lives, property or commerce; its flood warnings are tied to it, and it is not necessarily the level at which the river leaves its banks (NWS glossary). Minor flood stage is the lowest of its flood categories for each forecast point. This is the record of past years, not a forecast: for flooding now, follow the National Weather Service warnings for your area.</p>") % (
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
    return _page("What is flood stage, and how often do rivers reach it?", "flood-stage-years", "The share of water years each river's yearly peak reached National Weather Service minor flood stage, at %d US river gauges." % len(nat), body,
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
    return _page("River temperature: how warm US rivers are by month", "water-temperature", "Typical January, April, July and October water temperature at %d US river gauges, from USGS sensor records." % len(rows), body,
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
    return _page(("Texas lake levels and other US lakes: how full each one is right now" if sum(1 for r, G, got in rows if r["state"] == "TX") * 2 >= len(rows) else "Lake levels: how full US lakes are right now"), "lake-levels", "Every US lake on River Water Levels against its agency's own full mark right now: %d lakes, each basis named." % len(rows), body,
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
            "Across %d NOAA stations on this site, the median gap between observed water and prediction was %+.2f ft (a plus means the water stood that much higher than the tide table said, so a predicted high tide reached that much higher on a beach, ramp or seawall). Part of a gap can be steady: local sea level differs from the long-term level NOAA's tide datums are referenced to (at most US stations it has risen since; where the land is rising, as in parts of Alaska, it has fallen), and a season can run above or below its normal level; wind, air pressure and river flow add the rest.%s</p>") % (
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
    return _page("Tide predictions vs actual water: how far the sea ran from NOAA's predicted tide", "tides", "Observed water against NOAA tide predictions over the last %s at %d NOAA stations, with the predicted tide range in the same span." % (span, len(rows)), body,
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
    lead = ("<p><b>Right now, counted country by country: %s.</b> "
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
    return _page("River levels in %s: low or high right now?" % (", ".join(lab_c[:-1]) + " and " + lab_c[-1] if len(lab_c) > 1 else lab_c[0]), "world-rivers",
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
        g = re.search(r": ([+-]\d+\.\d\d) ft at", lead)
        md = re.search(r"median gap between observed water and prediction was ([+-]\d+\.\d\d) ft", html)
        top_ = max(float(r["max_gap_ft"]) for r in rows) if rows else None
        if not g or top_ is None or abs(float(g.group(1)) - top_) > 0.011:  # final check 2026-11-13: the headline gap itself, not only the station count (CSV rounds to 0.01)
            bad.append("tide headline gap %r against CSV max %r" % (g and g.group(1), top_))
        if not md or abs(float(md.group(1)) - statistics.median(float(r["median_gap_ft"]) for r in rows)) > 0.011:
            bad.append("tide median gap %r against CSV" % (md and md.group(1)))
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
    got = [x for x in ((peak_month(gl, sub, unk), flood_stage(gl), water_temp(gl)) if gl else ()) + (lake_levels(built, Gs), tides(built, Gs)) if x]
    got = [x for x in got if gain_ok(x[0])]  # no gain line, no page
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
