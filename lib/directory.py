"""Home, state, river hub, trust pages, sitemap, robots, redirects. Only gauges that have built pages are linked, so no link can 404."""
import os, json, math, datetime, collections
from lib.common import *
from lib.core import SOURCES_READ_ON
from lib.render import robots_meta, CSS, SOURCES, DISCLAIMER, nav, footer, TABS, HEAD_EXTRA, crumb_ld, series, LABELS, og_tags

STATE_NAMES = {"AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida",
               "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
               "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
               "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
               "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin",
               "WY": "Wyoming", "PR": "Puerto Rico"}
REGIONS = {"Northeast": "CT ME MA NH RI VT NJ NY PA", "Midwest": "IL IN IA KS MI MN MO NE ND OH SD WI", "South": "AL AR DE DC FL GA KY LA MD MS NC OK SC TN TX VA WV", "West": "AK AZ CA CO HI ID MT NV NM OR UT WA WY"}
EXTRA_CSS = """
.row{display:flex;gap:14px;overflow-x:auto;padding-bottom:6px}.pop{min-width:210px;flex:1;display:block;color:var(--ink)}.pop b{font:600 1.8rem Georgia,serif}.pop small{color:var(--mut);display:block}
.search{display:flex;gap:10px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:6px 14px}.search input{flex:1;border:0;background:transparent;color:var(--ink);font:inherit;padding:8px 0;outline:none}
.pills{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}.pill{border:1px solid var(--line);background:var(--card);border-radius:99px;padding:5px 12px;font-size:.85rem;color:var(--ink)}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:0 48px}.item{display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid var(--line);color:var(--ink)}.item small{display:block;color:var(--mut);font-size:.78rem}
.stateh{display:flex;justify-content:space-between;align-items:baseline;border-bottom:2px solid var(--line);margin-top:28px}.stateh h2{margin:0 0 6px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.gc{display:block;color:var(--ink)}.gc b{font:600 1.1rem Georgia,serif;display:block}.gc small{color:var(--mut);font-size:.78rem}
button.pill{font:inherit;cursor:pointer}.pill.on{background:var(--navy);color:#fff;border-color:var(--navy)}.prose{max-width:720px}.gmap{position:relative;line-height:0}.gmap img{width:100%;height:auto;border-radius:8px;display:block}.dot{position:absolute;width:14px;height:14px;margin:-7px 0 0 -7px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 0 1px var(--navy)}.d-lo{background:#d9822b}.d-mid{background:var(--accent)}.d-hi{background:#6b3fa0}.d-na{background:#9aa5b1}.keyrow{font-size:.82rem;color:var(--mut);margin-top:8px;line-height:1.6}.keyrow b{display:inline-block;width:11px;height:11px;border-radius:50%;margin:0 4px 0 12px;vertical-align:-1px}.prose h2{margin-top:26px}.prose p,.prose li{color:var(--ink)}
@media(max-width:760px){.cols{grid-template-columns:1fr}.grid{grid-template-columns:1fr}}
"""
SEARCH_JS = """<script>(function(){var i=document.getElementById('q'),act={},nm=document.getElementById('nomatch');function ap(){var v=i?i.value.toLowerCase().replace(/\\bst\\.? /g,'saint ').replace(/[,.]/g,' ').trim():'',tk=v.split(/\\s+/).filter(Boolean);document.querySelectorAll('[data-s]').forEach(function(e){var hay=e.getAttribute('data-s').replace(/[,.]/g,' '),ok=tk.every(function(t){return hay.indexOf(t)>=0});for(var k in act){if(act[k]&&e.getAttribute('data-'+k)!=='1')ok=false}e.style.display=ok?'':'none'});document.querySelectorAll('section.st').forEach(function(s){s.style.display=s.querySelector('[data-s]:not([style*="none"])')?'':'none'});if(nm)nm.hidden=!!document.querySelector('[data-s]:not([style*="none"])');var gc=document.getElementById('gcount'),tb=document.querySelectorAll('#alltab tbody tr');if(gc&&tb.length){var n=0;tb.forEach(function(x){if(x.style.display!=='none')n++});gc.textContent=n+(n===1?' gauge':' gauges')}}
if(i)i.addEventListener('input',ap);document.querySelectorAll('[data-f]').forEach(function(b){b.addEventListener('click',function(){var k=b.getAttribute('data-f');act[k]=!act[k];b.classList.toggle('on',act[k]);ap()})})})();</script>"""


def shell(title, desc, url, body, extra_main_class="", ld=""):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>%s</title><meta name="description" content="%s">'
            '<link rel="canonical" href="%s">%s<style>%s%s</style></head><body>%s<main id="main"%s>%s</main>%s</body></html>' % (
                esc(title), esc(desc), SITE_URL + url, ADSENSE + HEAD_EXTRA + og_tags(title, desc, SITE_URL + url) + ld + robots_meta(url), CSS, EXTRA_CSS, nav(), (' class="%s"' % extra_main_class) if extra_main_class else "", body, footer()))


def dir_lv(G):
    """The flow a list row shows: on a tidal reach the latest reading is a moment in the tide cycle (Freeport swings 1,090 to 12,500 cfs in a day), so lists show the 24 h mean the comparison uses; the gauge page shows the day's range."""
    return G["basis"] if G.get("osc") and G.get("basis_mean") else G["lv"]


NEAR_JS = """<script>(function(){var b=document.getElementById('nearbtn'),o=document.getElementById('near');if(!b||!o||!navigator.geolocation||!window.fetch)return;b.hidden=false;
function hv(a,c,d,e){var p=Math.PI/180,x=Math.sin((d-a)*p/2),y=Math.sin((e-c)*p/2);return 7926*Math.asin(Math.sqrt(x*x+Math.cos(a*p)*Math.cos(d*p)*y*y))}
b.addEventListener('click',function(){b.disabled=true;navigator.geolocation.getCurrentPosition(function(pos){fetch('/gauges.json').then(function(r){return r.json()}).then(function(g){var la=pos.coords.latitude,lo=pos.coords.longitude;
g.forEach(function(x){x.d=hv(la,lo,x[2],x[3])});g.sort(function(a,c){return a.d-c.d});o.textContent='';if(g[0].d>500){o.textContent='No gauges on this site within 500 miles of you yet.';o.hidden=false;b.disabled=false;return}var h=document.createElement('h2');h.textContent='Gauges nearest you';o.appendChild(h);
g.slice(0,8).forEach(function(x,i){var a=document.createElement('a');a.href=x[1];a.textContent=x[0]+' ('+Math.round(x.d)+' mi)';o.appendChild(a);if(i<7)o.appendChild(document.createTextNode(' \\u00b7 '))});o.hidden=false;b.disabled=false}).catch(function(){b.disabled=false})},function(){b.disabled=false;b.textContent='Location not available'})})})();</script>"""


def conus_map(built, Gs, cap=120):
    """USGS Topo image of the lower 48 with a link dot per gauge (the largest `cap` by drainage area), coloured by percentile bucket."""
    R = 6378137.0
    mx = lambda lon: R * math.radians(lon)
    my = lambda lat: R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    lon0, lon1, lat0, lat1 = -125.0, -66.5, 24.0, 49.6
    x0, x1, y0, y1 = mx(lon0), mx(lon1), my(lat0), my(lat1)
    h = round(1000 * (y1 - y0) / (x1 - x0))
    src = "https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/export?bbox=%.0f,%.0f,%.0f,%.0f&bboxSR=3857&imageSR=3857&size=1000,%d&format=jpg&f=image" % (x0, y0, x1, y1, h)
    dots, shown = "", 0
    for r in sorted(built, key=lambda r: -float(r["drainage_sqmi"] or 0))[:cap]:
        G = Gs[r["site"]]
        if not (lon0 <= G["lon"] <= lon1 and lat0 <= G["lat"] <= lat1):
            continue
        p = G["p"]
        cls = "d-na" if p is None else "d-lo" if p < 25 else "d-hi" if p > 75 else "d-mid"
        lab = "%s, %s" % (river_at(r["river"], r["place"]), r["state"]) + ((", flow compared with past years on this date: %s" % band_word(p).lower()) if p is not None else "")
        dots += '<a class="dot %s" tabindex="-1" style="left:%.2f%%;top:%.2f%%" href="%s" title="%s" aria-label="%s"></a>' % (cls, (mx(G["lon"]) - x0) / (x1 - x0) * 100, (y1 - my(G["lat"])) / (y1 - y0) * 100, r["water_url"], esc(lab), esc(lab))
        shown += 1
    if not shown:
        return ""
    key = '<div class="keyrow">Gauge color, flow compared with past years on this date: <b class="d-lo"></b>below normal (including very low) <b class="d-mid"></b>normal range <b class="d-hi"></b>above normal (including very high) <b class="d-na"></b>no comparison available. %d gauges shown.</div>' % shown
    return ('<div class="card" style="margin-top:14px"><h2>Gauges on this site</h2><div class="gmap"><img src="%s" alt="USGS topographic map of the lower 48 states with a marker for each gauge" width="1000" height="%d" loading="lazy">%s</div>%s'
            '<p class="src">Source: map services and data available from U.S. Geological Survey, National Geospatial Program (USGS Topo). Percentiles are estimates from USGS daily statistics.</p></div>' % (src, h, dots, key))


ALLTAB_JS = """<script>(function(){var t=document.getElementById('alltab');if(!t)return;var hs=t.querySelectorAll('th[data-k]');hs.forEach(function(h,c){h.style.cursor='pointer';h.tabIndex=0;function go(){var d=h.getAttribute('data-d')==='1'?-1:1,b=t.tBodies[0],r=[].slice.call(b.rows),i=parseInt(h.getAttribute('data-i'));hs.forEach(function(x){x.removeAttribute('data-d');x.removeAttribute('aria-sort')});h.setAttribute('data-d',d===1?'1':'0');h.setAttribute('aria-sort',d===1?'ascending':'descending');r.sort(function(x,y){var a=x.cells[i].getAttribute('data-v'),z=y.cells[i].getAttribute('data-v');if(h.getAttribute('data-k')==='n'){a=a===''?-1e18:parseFloat(a);z=z===''?-1e18:parseFloat(z);if(a===-1e18)return 1;if(z===-1e18)return -1;return (a-z)*d}return a.localeCompare(z)*d});r.forEach(function(x){b.appendChild(x)})}h.addEventListener('click',go);h.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();go()}})})})();</script>"""


def all_gauges_table(built, Gs):
    """Every built gauge in one table: flow, percentile, 24 h change and observed time, sortable in the browser."""
    rows = ""
    for r in sorted(built, key=lambda r: (STATE_NAMES.get(r["state"], r["state"]), r["river"], r["place"])):
        G = Gs[r["site"]]
        p = G["p"]
        ptxt = band_word(p)
        pv = "" if p is None else str({-1: 0, 101: 100}.get(p, p))
        chg = G["chg"]
        large = "1" if float(r["drainage_sqmi"] or 0) >= 1000 else "0"
        fcf = "1" if ((G["rec"].get("nwps") or {}).get("forecast")) else "0"
        wqf = "1" if any(series(G["rec"], c) for c in LABELS if c != "00045") else "0"
        rows += ('<tr data-s="%s" data-large="%s" data-fc="%s" data-wq="%s"><td data-v="%s"><a href="%s">%s</a></td><td class="hmob" data-v="%s">%s</td><td class="r" data-v="%s">%s</td><td class="r" data-v="%s">%s</td><td class="r" data-v="%s">%s</td><td class="hmob" data-v="%s">%s</td></tr>' % (
            esc((r["river"] + " " + r["place"] + " " + STATE_NAMES.get(r["state"], r["state"]) + " " + r["state"] + " " + r["site"]).lower().replace("st. ", "saint ")), large, fcf, wqf,
            esc((r["river"] + " " + r["place"]).lower()), r["water_url"], esc(river_at(r["river"], r["place"])), r["state"], r["state"], "%.0f" % dir_lv(G), fmt(dir_lv(G)), pv, ptxt,
            "" if (chg is None or G.get("osc")) else "%.0f" % chg, "–" if (chg is None or G.get("osc")) else ("%+d%%" % round(chg) if round(chg) else "0%"), G["lt"].isoformat(), esc(G["obs"])))
    heads = (("Gauge", "s"), ("State", "s"), ("Flow, cfs", "n"), ("Compared with normal", "n"), ("24 h change", "n"), ("Observed", "s"))
    th = "".join('<th scope="col"%s data-k="%s" data-i="%d">%s</th>' % (' class="r"' if k == "n" else ' class="hmob"' if i in (1, 5) else "", k, i, h) for i, (h, k) in enumerate(heads))
    return ('<div class="card"><h2>All gauges on this site</h2><div class="scroll"><table id="alltab"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>'
            '<p class="src">Source: USGS Water Data API latest readings; the comparison is our estimate from USGS daily statistics for the date (below normal is under the 25th percentile, above normal over the 75th). Select a column heading to sort.</p></div>%s' % (th, rows, ALLTAB_JS))


def item_line(g, Gs):
    """One line under a river on the home list: its flow and percentile when there is one gauge, else the count."""
    if len(g) > 1:
        return "%d gauges on this site" % len(g)
    G = Gs[g[0]["site"]]
    p = G["p"]
    return "%s cfs%s" % (fmt(dir_lv(G)), "" if p is None else ", %s" % band_word(p).lower())


def home(built, Gs):
    cards = ""
    for r in sorted(built, key=lambda r: -float(r["drainage_sqmi"] or 0))[:12]:
        G = Gs[r["site"]]
        pv = ""
        if G["p"] is not None:
            pos = 1 if G["p"] == -1 else 99 if G["p"] == 101 else max(1, min(99, G["p"]))
            pv = '<div class="bar"><u></u><i style="left:%.0f%%"></i></div>' % pos
        cards += '<a class="card pop" href="%s"><small>%s</small><b>%s <small style="display:inline">cfs</small></b>%s<small>%s, %s</small></a>' % (r["water_url"], esc(r["river"]), fmt(dir_lv(G)), pv, esc(r["place"]), r["state"])
    by_state = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in built:
        by_state[r["state"]][(r["hub_slug"], r["river"])].append(r)
    jump = '<p class="sub regions">Gauges by region: ' + " &middot; ".join('%s <b>%d</b>' % (k, sum(len(v) for st in ss.split() for v in by_state.get(st, {}).values())) for k, ss in REGIONS.items()) + '</p>'
    secs = ""
    for st in sorted(by_state, key=lambda s: STATE_NAMES.get(s, s)):
        items = ""
        for (hs, rv), g in sorted(by_state[st].items(), key=lambda kv: kv[0][1]):
            href = g[0]["hub_url"] if g[0].get("_hub") else g[0]["water_url"]
            large = "1" if any(float(x["drainage_sqmi"] or 0) >= 1000 for x in g) else "0"
            fc = "1" if any(((Gs[x["site"]]["rec"].get("nwps") or {}).get("forecast")) for x in g) else "0"
            wq = "1" if any(series(Gs[x["site"]]["rec"], c) for x in g for c in LABELS) else "0"
            items += '<a class="item" href="%s" data-s="%s" data-large="%s" data-fc="%s" data-wq="%s"><span>%s<small>%s</small></span><span>&rarr;</span></a>' % (href, esc((rv + " " + STATE_NAMES.get(st, st) + " " + " ".join(x["place"] for x in g)).lower().replace("st. ", "saint ")), large, fc, wq, esc(rv), item_line(g, Gs))
        secs += '<section class="st"><div class="stateh"><h2>%s</h2><a href="/rivers/%s/">View state &rarr;</a></div><div class="cols">%s</div></section>' % (STATE_NAMES.get(st, st), st.lower(), items)
    if len(built) > 150:
        secs = "".join('<section class="st"><div class="stateh"><h2>%s</h2><a href="/rivers/%s/">View all %d gauges &rarr;</a></div></section>' % (
            STATE_NAMES.get(st, st), st.lower(), sum(len(v) for v in by_state[st].values())) for st in sorted(by_state, key=lambda s: STATE_NAMES.get(s, s)))
    tools = ('<div class="search"><input id="q" type="search" placeholder="Search rivers, places or states" aria-label="Search rivers, places or states"><span class="sub" id="gcount" style="margin:0">%d gauges</span></div>'
             '<p id="nomatch" class="sub" hidden>No rivers match that search.</p><div class="pills" aria-label="Filters"><button type="button" class="pill" data-f="large">Large rivers</button>'
             '<button type="button" class="pill" data-f="fc">Has river forecast</button><button type="button" class="pill" data-f="wq">Has water quality sensors</button></div>%s' % (len(built), jump))
    body = ('<h1>River levels and flows for US rivers and creeks</h1><p class="sub">Flow and water level at %d USGS gauges across the US, with National Weather Service forecasts and alerts.</p>'
            '<p><button type="button" class="pill" id="nearbtn" hidden>Find gauges near me</button></p><div id="near" class="card" hidden></div>%s%s%s<h2 class="bst">Browse by state</h2>%s%s'
            % (len(built), conus_map(built, Gs), tools, all_gauges_table(built, Gs) if len(built) <= 60 else "", secs, SEARCH_JS + NEAR_JS))
    return shell("River levels and flows | " + BRAND, "Flow, gage height and how it compares with normal for US river gauges, from USGS and the National Weather Service.", "/", body)


def state_page(st, rows, Gs, sd=None):
    groups = collections.defaultdict(list)
    for r in rows:
        groups[(r["hub_slug"], r["river"])].append(r)
    name = STATE_NAMES.get(st, st)
    # rollup from our own data: how this state's gauges compare with the same date in past years, right now
    bands = collections.Counter(band_word(Gs[r["site"]]["p"]) for r in rows)
    order = ["Much above normal", "Above normal", "Normal range", "Below normal", "Much below normal"]
    parts = ["%d %s" % (bands[b], b.lower()) for b in order if bands.get(b)]
    nun = bands.get("–", 0)
    roll = "%d gauge%s on this site in %s. Compared with this date in past years: %s%s." % (
        len(rows), "" if len(rows) == 1 else "s", esc(name), ", ".join(parts) if parts else "no past-years comparison available",
        ("; %d with no comparison for this date" % nun) if nun else "")
    # statewide conditions beyond our own gauges: active NWS alerts and the latest U.S. Drought Monitor percentages (both sourced, no verdict)
    sw = ""
    if sd:
        al = sd.get("alerts") or {}
        if al.get("events"):
            sw += '<p class="sub">Active National Weather Service alerts in %s: %d &mdash; %s. Source: National Weather Service (api.weather.gov).</p>' % (
                esc(name), al.get("n", 0), ", ".join("%d %s" % (c, esc(e)) for e, c in al["events"][:6]))
        elif "alerts" in sd:
            sw += '<p class="sub">No active National Weather Service alerts in %s right now. Source: National Weather Service (api.weather.gov).</p>' % esc(name)
        dr = sd.get("drought")
        if dr and dr.get("d0") is not None:
            sw += '<p class="sub">U.S. Drought Monitor, week of %s: %.0f%% of %s is abnormally dry or worse (D0 or above), %.0f%% in moderate drought or worse (D1 or above), %.0f%% in severe drought or worse (D2 or above). Source: U.S. Drought Monitor (National Drought Mitigation Center, USDA, NOAA).</p>' % (
                esc(dr.get("mapDate", "")), dr.get("d0") or 0, esc(name), dr.get("d1") or 0, dr.get("d2") or 0)
    # one conditions row per gauge across the state (flow, how it compares, 24 h change, whether NWS issues a river forecast, observed time)
    trs = ""
    for (hs, rv), g in sorted(groups.items(), key=lambda kv: kv[0][1]):
        for r in sorted(g, key=lambda x: -float(x["drainage_sqmi"] or 0)):
            G = Gs[r["site"]]
            chg = G["chg"]
            ch = "–" if (chg is None or G.get("osc")) else ("%+d%%" % round(chg) if round(chg) else "0%")
            fcst = "Yes" if ((G["rec"].get("nwps") or {}).get("forecast")) else "No"
            trs += '<tr><td><a href="%s">%s</a><div class="src">USGS %s</div></td><td class="r">%s cfs</td><td class="r">%s</td><td class="r">%s</td><td>%s</td><td>%s</td></tr>' % (
                r["water_url"], esc(river_at(r["river"], r["place"])), r["site"], fmt(dir_lv(G)), band_word(G["p"]), ch, fcst, esc(G["obs"]))
    body = ('<div class="crumb"><a href="/">Home</a> / %s</div><h1>%s river levels: %d river%s, %d gauge%s</h1>'
            '<p class="sub">%s Source: USGS Water Data API, with flow compared with USGS daily statistics for this date.</p>%s'
            '<div class="card scroll"><table><thead><tr><th>Gauge</th><th class="r">Latest flow</th><th class="r">Compared with normal</th><th class="r">24 h change</th><th>NWS river forecast</th><th>Observed</th></tr></thead><tbody>%s</tbody></table></div>' % (
                esc(name), esc(name), len(groups), "" if len(groups) == 1 else "s", len(rows), "" if len(rows) == 1 else "s", roll, sw, trs))
    return shell("%s river levels and flows | %s" % (name, BRAND), "Current flow, how it compares with normal, and 24-hour change for every river gauge in %s, from USGS data." % name, "/rivers/%s/" % st.lower(), body, ld=crumb_ld([("Home", "/"), (name, None)]))


def hub_page(hub_slug, st, rows, inv_count, Gs):
    rows = sorted(rows, key=lambda r: float(r["drainage_sqmi"] or 0))
    trs = ""
    for r in rows:
        G = Gs[r["site"]]
        pv = band_word(G["p"])
        chg = None if G.get("osc") else G["chg"]
        ch = ("%s %s" % ("&#9650;" if chg >= 2 else "&#9660;" if chg <= -2 else "&#9644;", ("%+d%%" % round(chg) if round(chg) else "0%"))) if chg is not None else "–"
        fcst = "Yes" if ((G["rec"].get("nwps") or {}).get("forecast")) else "No"
        trs += '<tr><td><a href="%s">%s</a><div class="src">USGS %s</div></td><td class="r">%s cfs</td><td class="r">%s</td><td class="r">%s</td><td class="r">%s</td><td class="r">%s</td><td>%s</td></tr>' % (
            r["water_url"], esc(r["place"]), r["site"], fmt(dir_lv(G)), pv, ch, (fmt(float(r["drainage_sqmi"])) if float(r["drainage_sqmi"] or 0) > 0 else "–"), fcst, esc(G["obs"]))
    river, name = rows[0]["river"], STATE_NAMES.get(st, st)
    body = ('<div class="crumb"><a href="/">Home</a> / <a href="/rivers/%s/">%s</a> / %s</div><h1>%s in %s</h1><p class="sub">%d of %d gauges in %s are on this site. Source: USGS Water Data API; percentile estimated from USGS daily statistics.</p>'
            '<div class="card scroll"><table><thead><tr><th>Gauge</th><th class="r">Latest flow</th><th class="r">Compared with normal</th><th class="r">24 h change</th><th class="r">Drainage sq mi</th><th class="r">NWS river forecast</th><th>Observed</th></tr></thead><tbody>%s</tbody></table></div>' % (
                st.lower(), esc(name), esc(river), esc(river), esc(name), len(rows), inv_count, esc(name), trs))
    return shell("%s in %s: gauges, levels and flows | %s" % (river, name, BRAND), "Every %s gauge in %s on this site, with current flow." % (river, name), "/river/%s/" % hub_slug, body, ld=crumb_ld([("Home", "/"), (name, "/rivers/%s/" % st.lower()), (river, None)]))


# ----------------------------------------------------------------------------- trust pages (reviewed prose)
def prose_page(title, url, html_body, desc):
    return shell(title + " | " + BRAND, desc, url, '<div class="crumb"><a href="/">Home</a> / %s</div><div class="prose"><h1>%s</h1>%s</div>' % (esc(title), esc(title), html_body), ld=crumb_ld([("Home", "/"), (title, None)]))


def status_page(built, Gs, built_at):
    """Data freshness for every gauge on the site: the page a reader or the watchdog opens to see whether the numbers are current."""
    trs = ""
    for r in sorted(built, key=lambda r: -Gs[r["site"]]["age_min"]):
        m = Gs[r["site"]]["age_min"]
        cls = "fresh" if m <= 90 else "ageing" if m <= 360 else "stale"
        trs += '<tr><td><a href="%s">%s</a></td><td>%s</td><td class="r"><span class="ab %s">%s</span></td></tr>' % (r["dashboard_url"], esc(river_at(r["river"], r["place"]) + ", " + r["state"]), esc(r["site"]), cls, ("%d min" % m) if m < 180 else ("%d h" % round(m / 60)))
    built_at = datetime.datetime.fromisoformat(built_at).strftime("%b %d, %I:%M %p UTC").replace(" 0", " ")
    body = ('<p>Site built %s. Age is the time since the newest USGS flow reading at each gauge when the page was built; pages also re-check USGS in the reader\'s browser. Green: newest reading under 90 minutes old; amber: under 6 hours; red: older. Machine-readable: <a href="/status.json">status.json</a>.</p>'
            '<div class="scroll"><table><thead><tr><th scope="col">Gauge</th><th scope="col">USGS site</th><th scope="col" class="r">Newest reading is</th></tr></thead><tbody>%s</tbody></table></div>' % (esc(built_at), trs))
    return prose_page("Data status", "/status/", body, "Age of the newest USGS reading at every gauge on River Water Levels, as of the last build.")


def _publisher_line():
    """The publisher contact from data/publisher.json, or the recorded waiver in one plain sentence."""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "publisher.json"), encoding="utf-8") as f:
            pub = json.load(f)
    except (OSError, ValueError):
        pub = {}
    if pub.get("email"):
        return "Publisher contact: %s." % esc(pub["email"])
    return "Publisher contact: not yet listed; the owner has waived it for this first release."


def trust_pages(built_count, built_rows):
    t = {}
    t["/about/"] = prose_page("About", "/about/", (
        "<p>%s shows current river conditions for individual USGS stream gauges: flow, gage height, how today's flow compares with the gauge's own record for the date, forecasts and alerts from the National Weather Service, and nearby public land. "
        "Each gauge has one page with its conditions, history and flood record. Every page has a Forecast section: the National Weather Service river forecast where one is issued, otherwise the words Not issued, with the weather forecast and rain outlooks.</p><h2>Where the numbers come from</h2><p>Gauge readings and daily statistics come from the U.S. Geological Survey. Forecasts, alerts, weather observations and rain estimates come from the "
        "National Weather Service and NOAA. The <a href=\"/data-sources/\">data sources</a> page lists each source and the terms we checked.</p><h2>What this site adds to the source pages</h2><p>Each item below appears on a gauge page only where its data exists for that gauge; a gauge page lists what is not available for it.</p><ul><li>Today's flow ranked against the same calendar date across the gauge's whole USGS record, as a percentile.</li><li>Rise and fall over 1, 3, 6, 12 and 24 hours, and the last time the flow was this high.</li><li>The same 50 days in earlier years, the last 30 days and 12 months, annual peaks by decade and, where USGS publishes them, flood-frequency flows.</li><li>Upstream and downstream gauges that are also on this site, with the measured travel lag where the match is strong, and the National Weather Service forecast point for the gauge.</li><li>USGS, NWS, NOAA, EPA and USDA records for one location joined on one page, each with its source and time.</li></ul><h2>How current it is</h2><p>Every block shows the time of its data in the gauge's local time. "
        "USGS gauges typically report about every 15 minutes. A scheduled job rebuilds the site about every 30 minutes; if it stops, the time on each block shows how old its data is. Your browser re-checks the newest USGS reading and National Weather Service alerts when the page loads. A block older than its limit is marked, and readings older than 24 hours are not shown as current. See the <a href=\"/methodology/\">methodology</a> for how every number is calculated.</p><h2>What this site is not</h2><p>It is not a government site and is not endorsed by USGS, NOAA or the National Weather Service. "
        "It is not a flood warning service. For emergencies, follow official warnings.</p><p>%s Corrections are handled as described on the Methodology page.</p>" % (esc(BRAND), _publisher_line())), "About River Water Levels: current river conditions from USGS and National Weather Service data.")
    t["/disclaimer/"] = prose_page("Disclaimer", "/disclaimer/", "<p>%s</p><p>Data is shown as received from the named sources, with the time it was observed or issued. Provisional USGS data are subject to revision. "
                                   "Forecasts change. Percentiles and other comparisons on this site are our calculations from published USGS statistics and are labeled as estimates.</p>" % esc(DISCLAIMER), "Data, accuracy and safety disclaimer for River Water Levels: provisional USGS data, changing forecasts, and not a flood warning service.")
    t["/embed/"] = prose_page("Add to your site", "/embed/", (
        "<p>Every gauge page has a small live panel you can put on your own site: the current flow, gage height, how today compares with the record, and any active NWS alert, rebuilt about every 30 minutes. It is free; the panel links back to the full page.</p>"
        "<h2>How</h2><p>Open the gauge page you want, click <b>Put this gauge's live panel on your own site</b> under Official pages, and copy its address. Then paste this where you want the panel, with that address:</p>"
        "<pre class=\"card\">&lt;iframe src=\"%s/embed/river/&lt;river&gt;/&lt;place&gt;/\" width=\"100%%\" height=\"520\" loading=\"lazy\" title=\"River conditions from %s\"&gt;&lt;/iframe&gt;</pre>"
        "<p>Example for the Potomac River at Little Falls: <code>%s/embed/river/potomac-river-md/little-falls/</code>.</p>"
        "<h2>Terms</h2><p>Free for any site. Keep the link to the full page that is inside the panel. The data stays the agencies' (USGS, NOAA National Weather Service), shown with its observed time; it is not a flood warning.</p>" % (SITE_URL, esc(BRAND), SITE_URL)), "Put a free live panel of a river gauge (flow, gage height, alerts) on your own site with one iframe.")
    t["/privacy/"] = prose_page("Privacy", "/privacy/", "<p>This site shows advertising served by Google AdSense. Third-party vendors, including Google, use cookies to serve ads based on your prior visits to this website and other websites. Google's use of advertising cookies enables it and its partners to serve ads to you based on your visit to this site and other sites on the internet.</p>"
                                "<p>You can opt out of personalized advertising by visiting Google Ads Settings (<a href=\"https://adssettings.google.com\" rel=\"nofollow noopener\">adssettings.google.com</a>). You can opt out of a third-party vendor's use of cookies for personalized advertising at <a href=\"https://www.aboutads.info\" rel=\"nofollow noopener\">aboutads.info</a>. The site is served by Cloudflare, which keeps standard server logs (your IP address and browser details, as with any web request).</p>"
                                "<p>Your browser contacts government servers directly when a page loads: radar images from radar.weather.gov, camera images from USGS (usgs-nims-images.s3.amazonaws.com), map images from basemap.nationalmap.gov, and, to show the newest readings and alerts, the USGS Water Data API (api.waterdata.usgs.gov) and the National Weather Service API (api.weather.gov). Those servers receive your IP address and browser details, as with any web request.</p>"
                                "<p>The dark or light theme choice is kept in your browser's local storage, on your device only. The Find gauges near me button on the home page asks your browser for your location only when you press it; the position is used in your browser to sort a list and is not sent anywhere.</p>", "How River Water Levels handles privacy: Google and third-party advertising cookies and how to opt out, which government servers your browser contacts, and the theme choice kept on your device.")
    t["/glossary/"] = prose_page("Glossary", "/glossary/", "".join("<h2>%s</h2><p>%s</p>" % (a, b) for a, b in (
        ("cfs", "Cubic feet per second: the volume of water passing the gauge each second."),
        ("Gage height", "The height of the water surface above a fixed reference at the gauge, in feet. USGS spells it gage."),
        ("Percentile for date", "Where the current flow falls among the gauge's published daily percentiles for the same calendar date. Our estimate, interpolated between the USGS percentiles (5th, 10th, 20th, 25th, 50th, 75th, 80th, 90th, 95th)."),
        ("Below normal, Normal range, Above normal", "The headline on each gauge page. It compares today's flow with the same calendar date in every year on record: Below normal means lower than three quarters of those years (under the 25th percentile), Normal range means between the 25th and 75th percentile, Above normal means higher than three quarters of them. Very low and Very high mean below the 5th or above the 95th percentile. The sentence under the headline states the same thing as a share of years."),
        ("Forecast high, Forecast high flow", "The highest value in the National Weather Service river forecast that is still ahead, with the time it first occurs and when the forecast was issued. Some forecast points are published in flow (cfs) instead of height, and then the card says so. If the latest reading is already above it, the card says that too. A forecast is the NWS's, not ours, and changes as rain and releases change."),
        ("Rising, Falling, Steady, Leveling off, Unsteady, Unclear", "The word on the change card describes the last 6 hours of flow, from the latest reading and the reading about 6 hours earlier: Rising or Falling when flow moved more than 1%, Steady when it did not, Leveling off when it moved but has stopped in the last hour, Unsteady when the last hour points the other way, Unclear when a small flow change is contradicted by the gage height. The 24-hour and 1-hour changes are printed under it."),
        ("Upstream and downstream gauges, lag", "Gauges on this site that sit on the same river network (USGS NLDI). The lag is the shift in hours, up to 72, that best matches the hourly flow at the two gauges over the last 8 days; it is measured from the data, not a travel-time promise, and is shown only when the match is strong (r of 0.85 or more). A pair is listed on both pages."),
        ("Different zero points (NWS and USGS stage)", "A gauge can be read by the USGS and by the National Weather Service on different datums, so the two heights differ by a fixed amount. Flood stages and NWS forecasts are on the NWS scale. When the two readings differ by more than 0.3 ft the page says so and measures flood stages against the NWS reading."),
        ("Median for date","The 50th percentile of flow for the calendar date over the gauge's record."),
        ("Provisional", "A USGS reading that has not yet been reviewed and may change."),
        ("Daily mean flow", "The average of the readings on one gauge-local date. Days with fewer than 80% of expected readings are marked partial."),
        ("Drainage area", "The land area, in square miles, that drains to the gauge."),
        ("Forecast point", "A location where the National Weather Service publishes river stage and flow forecasts and flood stages."),
        ("Model guidance", "Output of the NOAA National Water Model for the river reach. It is not an official forecast and not a measurement."),
        ("Gauge-local time", "Times are shown in the time zone of the gauge, with the zone abbreviation."))), "Plain-language definitions of the river terms used on River Water Levels: cfs, gage height, percentile, flood stage, forecast point and more.")
    t["/faq/"] = prose_page("FAQ", "/faq/", "".join("<h2>%s</h2><p>%s</p>" % (a, b) for a, b in (
        ("How often is the data updated?", "USGS gauges typically report about every 15 minutes. Each block shows the time of its own data, and blocks older than their limit are marked."),
        ("Why does a daily table row say partial day?", "The mean is shown only when the day has at least 80% of the expected readings. Today is usually partial."),
        ("Why is there no percentile on some gauges?", "A percentile needs USGS daily statistics for the date. Gauges without them show a dash."),
        ("Why are some blocks missing on a page?", "A block appears only when its source returned usable data for that gauge. In its place the page names the main gaps (such as water temperature, flood stages, rain, dams and nearby gauges) in a line under the tiles; smaller blocks are simply left out."),
        ("Is this a flood warning service?", "No. Use official National Weather Service warnings for emergencies. No alert shown does not mean conditions are safe."),
        ("Which time zone are times in?", "The gauge's local time zone, with the abbreviation shown."))), "Frequently asked questions about River Water Levels: where the numbers come from, how current they are, time zones, and what percentiles mean.")
    meth = (
        "<h2>Gauge readings</h2><p>Flow (cfs) and gage height (ft) are the latest continuous readings from the USGS Water Data API, shown with the time they were observed in the gauge's local time. USGS gauges report about every 15 minutes, some hourly. Readings are provisional until USGS reviews them.</p>"
        "<h2>Percentile for the date</h2><p>USGS publishes daily statistics for each calendar date from the gauge's record: the 5th, 10th, 20th, 25th, 50th, 75th, 80th, 90th and 95th percentiles of flow. We place the current flow between those published values by linear interpolation. The flow used is the trailing 24-hour mean when the last 24 hours hold at least 80% of the expected readings and span at least 20 hours, and the page says which; otherwise it is the latest reading. Values below the 5th or above the 95th percentile are shown as such. The number is our estimate, not a USGS value.</p>"
        "<h2>Daily means</h2><p>Each daily mean averages the readings on one gauge-local date and is shown only with at least 80% of the expected readings.</p>"
        "<h2>Comparison with the gauge's record</h2><p>Computed from the USGS daily mean flow record : the highest daily mean of the last 7 days, the last day before those 7 days with a daily mean that high or higher, the last day before those 7 days above the 90th percentile for its date, the days above the 75th percentile in the last 30 days, and the rank of this month's mean among the same days in other years (years with at least 80% of days).</p>"
        "<h2>Earlier years, annual peaks and the rating</h2><p>The same 50 days in earlier years are USGS daily means shifted to the same calendar dates. Annual peaks are USGS annual peak streamflow, with the median and largest peak by decade for decades with at least five peaks. The rating curve is the USGS gage height to flow table for the gauge, thinned for display; the dot is the latest reading. The 12-month chart is USGS daily means with the 25th to 75th percentile band and median for each date.</p>"
        "<h2>Rate of rise and fall</h2><p>The latest reading minus the reading closest to 1, 3, 6, 12 and 24 hours earlier (within 20 minutes or 60% of the reporting interval). The arrow is steady when the flow changed by 1% or less. Where flow cycles several times a day within a tide the change is not shown, because it would compare two phases of a cycle; the 24-hour range is shown instead. Where flow readings swing without following the gage height (lock-and-dam or backwater effects), the headline uses the gage height and says so; the table still lists the flow changes.</p>"
        "<h2>Flood stages, crests, impacts and outlook</h2><p>Flood stages, historic crests, impact statements, the long-range flood outlook and river forecasts are National Weather Service products for the forecast point linked to the USGS gauge, shown as published. Crest dates that the NWS gives without a time are shown as that date. Dashed lines on the gage height chart are drawn only where they fall inside the chart's range.</p>"
        "<h2>Rain</h2><p>Recent rain totals are NWS River Forecast Center multisensor estimates on an about 2.5-mile grid at the gauge location. The 24-hour product is hourly; the 2-day and 3-day products are daily, so each window shows its own end time. Forecast rain totals and the hourly heatmap come from the NWS gridpoint forecast.</p>"
        "<h2>Snow, water temperature, outlook, watershed</h2><p>Snow water equivalent is from the three nearest USDA SNOTEL stations within 37 miles; a station may not drain to the gauge. Water temperature by month is the mean of all published daily mean values in each calendar month; months with fewer than 150 values are marked. The 8 to 14 day and 6 to 10 day outlooks are NOAA Climate Prediction Center products at the gauge location. Watershed characteristics and water quality assessments are U.S. EPA StreamCat and ATTAINS values for the reach and for assessment units within about a quarter mile of the gauge, shown as published.</p>"
        "<h2>Public land and maps</h2><p>Public land is from the USGS Protected Areas Database (PAD-US) within about half a mile of the gauge; mapped land is not proof of legal access. Maps are U.S. Geological Survey National Map services.</p>"
        "<h2>Freshness limits</h2><p>A gauge whose latest flow is more than 24 hours old shows a Gauge not reporting notice with the time of its last reading; after 30 days without a reading the page is no longer rebuilt. River forecasts older than 24 hours are marked and older than 72 hours hidden; hourly weather forecasts older than 12 hours are marked and older than 72 hours hidden. Weather observations older than 3 hours are marked and older than 12 hours hidden. Rain estimates older than 6 hours are marked and older than 24 hours hidden. Alerts older than 3 hours are marked. Snow data older than 5 days and outlooks older than 3 days are hidden.</p>"
        "<h2>What we do not do</h2><p>We do not make our own forecasts and we do not rate conditions as good or bad. Forecasts, outlooks and impact statements shown are National Weather Service products quoted as published; every other number is a source value or a calculation described on this page.</p>"
        "<h2>Corrections</h2><p>Errors that come from a source are the source's to correct; we show the source's current value on the next refresh. Errors in our calculations are corrected as soon as they are found. Last reviewed Oct 17, 2026.</p>")
    t["/methodology/"] = prose_page("Methodology", "/methodology/", meth, "How River Water Levels calculates percentiles, comparisons, rates and lags, and its freshness limits.")
    upd = (("USGS gauge readings", "About every 15 minutes (some gauges hourly)", "Every 30 minutes, and in your browser when the page loads"),
           ("NWS alerts", "As issued", "Every 30 minutes, and in your browser when the page loads"),
           ("NWS forecasts, observations, gridpoint data", "As issued, typically hourly", "Every 30 minutes"),
           ("NWS river forecasts and National Water Model", "As issued by the River Forecast Centers; model runs hourly and every 6 hours", "Every 30 minutes"),
           ("Rain estimates", "Hourly and daily products", "Every 30 minutes"),
           ("USGS record, annual peaks, rating, water temperature", "Daily or less often", "On a slower schedule than the readings; each block's Source line gives its fetch date"),
           ("SNOTEL, 6 to 10 and 8 to 14 day outlooks", "Daily", "Every 6 hours"),
           ("Public land (PAD-US)", "Periodic releases", "Downloaded occasionally; the block gives its download date"))
    updrows = "".join("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % u for u in upd)
    rows = ""
    for s in SOURCES.values():
        if s["status"] in ("quoted", "owner-permission") and s.get("id") not in ("openfema", "ncei"):  # terms read, but no block on any page shows them yet
            basis = {"quoted": "Terms read " + (s.get("read_on") or SOURCES_READ_ON), "owner-permission": "Written permission reported by the site owner"}[s["status"]]
            rows += '<tr><td>%s</td><td>%s</td><td>%s</td><td><a href="%s" rel="noopener">Terms</a></td></tr>' % (esc(s["name"]), esc(s.get("credit") or ""), esc(basis), esc(s["terms_url"]))
    t["/data-sources/"] = prose_page("Data sources", "/data-sources/", '<div class="card scroll"><table><thead><tr><th>Source</th><th>Credit</th><th>Basis for reuse</th><th>Link</th></tr></thead><tbody>%s</tbody></table></div>'
                                     '<h2>How often each source updates</h2><div class="card scroll"><table><thead><tr><th>Source</th><th>Source updates</th><th>This site refreshes</th></tr></thead><tbody>%s</tbody></table></div>'
                                     '<p class="src">NWS material is public domain and not subject to copyright. Sources whose terms are not yet settled are not used on the site.</p>' % (rows, updrows), "The data sources used by River Water Levels and the terms checked.")
    return t


SITEMAP_MAX = 10000


def sitemap_files(urls, lastmod):
    """{file name: xml}. At most 10,000 URLs per file (Google allows 50,000); more than that becomes an index at /sitemap.xml."""
    urls = sorted(urls)
    if len(urls) <= SITEMAP_MAX:
        return {"sitemap.xml": sitemap(urls, lastmod)}
    out, idx = {}, ""
    for i in range(0, len(urls), SITEMAP_MAX):
        name = "sitemap-%d.xml" % (i // SITEMAP_MAX + 1)
        out[name] = sitemap(urls[i:i + SITEMAP_MAX], lastmod)
        idx += "<sitemap><loc>%s/%s</loc></sitemap>" % (SITE_URL, name)
    out["sitemap.xml"] = '<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</sitemapindex>' % idx
    return out


def sitemap(urls, lastmod):
    items = "".join("<url><loc>%s%s</loc><lastmod>%s</lastmod></url>" % (SITE_URL, u, lastmod.get(u, datetime.date.today().isoformat())) for u in sorted(urls))
    return '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>' % items


def llms(built):
    """llms.txt: what the site is, where the pages and the data files are, how to credit the sources."""
    lines = ["# %s" % BRAND, "", "> One page per USGS river gauge: current flow and gage height, how today compares with the gauge's own record, NWS forecasts, alerts and flood record. Government data only (USGS, NOAA/NWS), every number with its observed time and source.", "",
             "- Sitemap: %s/sitemap.xml" % SITE_URL, "- Each gauge page has a machine-readable copy at <page URL>data.json (7-day flow and gage height, daily mean flow by year).", "- Embeddable panel per gauge at %s/embed/river/<river>/<place>/" % SITE_URL,
             "- Credits: Data: U.S. Geological Survey; NOAA National Weather Service. Provisional USGS data are subject to revision.", "- Methodology: %s/methodology/ ; data sources and terms: %s/data-sources/" % (SITE_URL, SITE_URL), "", "## Gauge pages", ""]
    lines += ["- [%s, %s](%s%s)" % (river_at(r["river"], r["place"]), r["state"], SITE_URL, r["dashboard_url"]) for r in sorted(built, key=lambda r: (r["state"], r["river"], r["place"]))]
    return "\n".join(lines) + "\n"


def robots():
    return "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % SITE_URL


def not_found():
    body = '<h1>Page not found</h1><p class="sub">That page is not on %s. Try the <a href="/">home page</a> or search for a river.</p>' % esc(BRAND)
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Page not found | %s</title><meta name="robots" content="noindex">%s<style>%s%s</style></head><body>%s<main>%s</main>%s</body></html>' % (
        esc(BRAND), HEAD_EXTRA, CSS, EXTRA_CSS, nav(), body, footer()))


FAVICON = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#1d5fa8"/><path d="M5 20c4-5 7-5 11 0s7 5 11 0" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round"/><path d="M5 12c4-5 7-5 11 0s7 5 11 0" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity=".6"/></svg>'
