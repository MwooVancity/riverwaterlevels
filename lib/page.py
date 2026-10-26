"""Tab assembly, navigation, footer, live scripts and the page template."""
import statistics, os, re, json, math, collections, hashlib, datetime, zoneinfo
from lib.common import *
from lib.core import *
from lib.hero import *
from lib.core import _safe
from lib.charts import *
from lib.weather import *
from lib.forecast import *


def b_related(G, pages):
    items = (G["rec"].get("related") or {}).get("items") or []
    rows = ""
    for x in items:
        pr = pages.get(x["site"])
        if not pr or not pr.get("_built"):
            continue
        lag = ("about %d h (r %.2f)" % (x["lag_h"], x["lag_r"])) if x.get("lag_h") else "–"
        rows += tr(['<a href="%s">%s</a>' % (pr["water_url"], esc(river_at(pr["river"], pr["place"]))), x["relation"].capitalize(), "%s cfs" % fmtc(x["flow"]), esc(tzl(parse_t(x["time"]), G["zone"])), lag], right=(2,))
    if not rows:
        return None
    from lib import ui
    nodes = []
    for rel in ("upstream", "downstream"):
        if rel == "downstream":
            nodes.append({"name": "<span>This gauge</span>", "flow": "%s cfs" % fmtc(G["lv"]), "sub": esc(G["obs"]), "cur": True})
        for x in items:
            pr = pages.get(x["site"])
            if x["relation"] == rel and pr and pr.get("_built"):
                nodes.append({"name": '<a href="%s">%s</a>' % (pr["water_url"], esc(river_at(pr["river"], pr["place"]))), "flow": "%s cfs" % fmtc(x["flow"]),
                              "sub": x["relation"].capitalize() + " &middot; " + esc(tzl(parse_t(x["time"]), G["zone"])) + ((" &middot; lag about %d h" % x["lag_h"]) if x.get("lag_h") else ""), "cur": False})
    return block("related_gauges", "Upstream and downstream gauges", "live", ui.strip(nodes),
                 "Source: USGS NLDI river network and USGS Water Data API. Relation is along the NLDI main stem; only gauges on this site that report flow are listed. Observed lag is the shift, up to 72 h, that best matches hourly flow at the two gauges over the last 8 days (r = correlation, shown only at 0.85 or higher); it is empirical, not a travel time.", "usgs")


def b_land(G):
    land = G["rec"].get("land")
    if not land or not land.get("rows"):
        return None
    seen_l, uniq = set(), []
    for t in land["rows"]:
        if tuple(t) not in seen_l:
            seen_l.add(tuple(t))
            uniq.append(t)
    rows = "".join(tr([esc(u), esc(PADMAN.get(m, m or "n/a")), esc(ACCESS.get(a, a or "n/a"))]) for u, m, a in uniq[:12])
    return block("public_land", "Public land at this gauge", "map", table(["Unit", "Managed by", "Public access"], rows),
                 "Source: USGS Protected Areas Database (PAD-US), within about half a mile of the gauge, downloaded %s. Mapped land is not proof of legal access." % fdate(land["downloaded"]), "padus")


def b_map(G):
    lat, lon, R = G["lat"], G["lon"], 6378137.0
    half = 8000 / math.cos(math.radians(lat))
    cx, cy = R * math.radians(lon), R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    bbox = "%.0f,%.0f,%.0f,%.0f" % (cx - half, cy - half * 0.5625, cx + half, cy + half * 0.5625)
    src = "https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/export?bbox=%s&bboxSR=3857&imageSR=3857&size=640,360&format=png&f=image" % bbox
    return block("gauge_map", "Gauge location", "map", '<div class="mapimg"><img src="%s" alt="USGS topographic map centered on %s, about 10 miles across" width="640" height="360" loading="lazy"><i aria-hidden="true"></i></div>' % (src, esc(G["place"])),
                 "Source: Map services and data available from U.S. Geological Survey, National Geospatial Program (USGS Topo). Map about 10 miles across, centered on the gauge at %.4f, %.4f." % (lat, lon), "natmap")


# ---------------------------------------------------------------- tabs
TABS = {
    "dashboard": {"label": "Conditions", "title": "%s, %s: river level and flow", "desc": "%s, %s: current flow, gage height, how it compares with past years, alerts, history and flood record from USGS gauge %s.", "hero": True},
    "forecast": {"label": "Forecast", "title": "%s, %s: river forecast", "desc": "%s, %s: river forecast, rain, radar and weather forecast for USGS gauge %s.", "hero": False},
}


def b_nearby(G, pages):
    """Other gauges on the site close to this one (up to five within 60 miles, nearest first), each with latest flow and the plain-word comparison. Upstream and downstream gauges are in their own strip and are skipped here."""
    skip = {G["site"]} | {x["site"] for x in ((G["rec"].get("related") or {}).get("items") or [])}
    def dist(p):
        la1, lo1, la2, lo2 = map(math.radians, (G["lat"], G["lon"], p["_ll"][0], p["_ll"][1]))
        return 3958.8 * 2 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))
    usable = lambda s, p: s not in skip and p.get("_built") and p.get("_ll")
    # bounding box before the haversine: 60 mi is under 1 deg lat and ~2 deg lon in CONUS, so only distance-test the handful in the box (was an O(n) trig scan per page = O(n^2) per build)
    box = [(dist(p), p) for s, p in pages.items() if usable(s, p) and abs(p["_ll"][0] - G["lat"]) <= 1.0 and abs(p["_ll"][1] - G["lon"]) <= 2.0]
    out = sorted((x for x in box if x[0] <= 60), key=lambda x: x[0])  # nearby means a short drive: the first reviews called 107 and 127 miles not nearby
    same, far = [], []
    if len(out) < 5:  # fewer than five truly-nearby: fall back to the full set for the dead-end backfill (Lakebrief comparison 2026-10-21). This full scan fires only where gauges are sparse, so it fades out as areas fill in.
        cand = [(dist(p), p) for s, p in pages.items() if usable(s, p)]
        if len(out) < 3:  # the nearest gauges in the same state, up to eight
            seen = {id(p) for _, p in out}
            same = sorted((x for x in cand if x[1].get("state") == G["st"] and id(x[1]) not in seen), key=lambda x: x[0])[:8]
        shown = {id(p) for _, p in out[:5] + same}
        far = sorted((x for x in cand if id(x[1]) not in shown), key=lambda x: x[0])[:max(0, 5 - len(out[:5]) - len(same))]  # pSEO check 2026-10-21: fill to five with the nearest anywhere, distance shown
    if not out and not same and not far:
        return None
    li = lambda grp: "".join('<li><a href="%s">%s</a><span>%s cfs &middot; %s &middot; %d mi away</span></li>' % (p["water_url"], esc(river_at(p["river"], p["place"]) + ", " + p["state"]), fmtc(p["_lv"]), esc(p["_band"].lower()), round(mi)) for mi, p in grp)
    lis = li(out[:5])
    if same:
        lis += '</ul><p class="src">Other rivers in %s on this site</p><ul class="nbr">' % esc(G["st"]) + li(same)
    if far:
        lis += '</ul><p class="src">Nearest gauges elsewhere on this site</p><ul class="nbr">' + li(far)
    return block("nearby_gauges", "Other gauges nearby" if out else "Other gauges on this site", "live", '<ul class="nbr">%s</ul>' % lis,
                 "Source: USGS Water Data API latest readings at the gauges on this site, as of this page's build; the comparison is our estimate from USGS daily statistics for the date. Distance is straight-line from this gauge.", "usgs")


def b_official_links(G):
    """Where to go next: the source pages for this gauge, opened in a new tab."""
    n = G["rec"].get("nwps") or {}
    lid = n.get("lid")
    links = [("USGS page for this gauge", "https://waterdata.usgs.gov/monitoring-location/%s/" % G["site"]), ("USGS WaterAlert: text or email when this gauge crosses a level you choose", "https://waterdata.usgs.gov/nwis/wateralert")]
    if lid:
        links.append(("NWS river page for forecast point %s" % lid, "https://water.noaa.gov/gauges/%s" % lid))
    links.append(("NWS forecast for this location", "https://forecast.weather.gov/MapClick.php?lat=%.4f&lon=%.4f" % (G["lat"], G["lon"])))
    links.append(("NWS active alerts for this location", "https://alerts.weather.gov/search?point=%.4f,%.4f" % (G["lat"], G["lon"])))
    links.append(("This page's data as JSON: 7-day flow and gage height readings, daily mean flow by year (USGS, provisional)", G["row"]["dashboard_url"] + "data.json"))
    links.append(("Put this gauge's live panel on your own site (free embed, links back here)", "/embed" + G["row"]["dashboard_url"]))
    body = '<ul class="olinks">%s</ul>' % "".join('<li><a href="%s" rel="noopener" target="_blank">%s</a></li>' % (esc(h), esc(t)) for t, h in links)
    return block("official_links", "Official pages for this gauge", "agency", body, "Source: links to the agencies that publish the data on this page (USGS, NOAA National Weather Service); they open in a new tab.", "usgs")


def tab_blocks(tab, G, pages):
    if tab == "dashboard":  # one page per gauge, ordered by what a person at the water asks: is it dangerous, what is the water like, what is coming, how does it compare; "SEC:" is a heading, "FOLD:" a closed group
        has_al = any((x.get("event") or "") not in IGNORED_ALERTS for x in ((G["rec"].get("nws") or {}).get("alerts") or []))
        return [b2.b_offline(G)] + ([b_alerts(G)] if has_al else []) + [
                "SEC:What the water is like now", b3.b_camera(G), b_quality(G), b3.b_tides(G), b_heatmap(G) or b_hourly(G), b_weather(G, 6), b_air(G), b3.b_air_quality(G), b3.b_uv(G), b_rain(G), b_radar(G),
                "SEC:Level, flow and flood risk", b_flow_chart(G), b2.b_stage_chart(G), b_impacts(G)] + ([] if has_al else [b_alerts(G)]) + ["AD", b2.b_rate(G)] + ([
                "SEC:Forecast", b_river_forecast(G), b_nwm(G), b2.b_nwm_medium(G), b2.b_noforecast(G), b3.b_wpc(G), b3.b_acis(G), b2.b_qpf(G), b2.b_atlas14(G), b_cpc(G)]) + [
                "SEC:How today compares with past years", b3.b_month_chart(G), b3.b_year_chart(G), b_multiyear(G), b3.b_sustained(G), b_record(G), b_wtemp(G), b3.b_stocking(G), b_snotel(G),
                "FOLD:Flood record and history", b_peaks(G), b3.b_stage_years(G), b3.b_floodfreq(G), b_crests(G), b3.b_flood_outlook(G),
                "FOLD:Daily values, measurements and rating", b_daily(G), b3.b_field_meas(G), b2.b_rating(G), b3.b_rise(G),
                "FOLD:Watershed, water quality and land", b2.b_drought(G), b2.b_attains(G), b3.b_streamcat(G), b3.b_dams(G), b3.b_fema_zone(G), b_land(G),
                b3.b_access(G), b3.b_recreation(G), b_related(G, pages), b_nearby(G, pages), b3.b_nws_point(G, pages), b_map(G), b_official_links(G), b2.b_about(G)]
    return []  # only the dashboard tab is built (one page per gauge)


def embed_page(G, pages):
    """The hero (alert banner, one-line answer, tiles) alone, for an iframe on a club, outfitter or county page; links back to the full page (Lakebrief comparison 2026-10-21: their one link-earning device)."""
    row = G["row"]
    rp, st = river_at(G["river"], G["place"]), G["st"]
    full = SITE_URL + row["dashboard_url"]
    h = hero(G, pages)
    h = h.split('<div class="cstrip"')[0]  # tiles only, no strip, no cite
    title = "%s, %s: water level and flow (embed)" % (rp, st)
    desc = "Embeddable panel: current flow and gage height at USGS gauge %s, %s, %s, from riverwaterlevels.com." % (G["site"], rp, st)
    body = '<h1>%s, %s</h1><p class="sub">USGS gauge %s &middot; observed %s</p>%s<p class="src"><a href="%s" target="_top" rel="noopener">Live page with forecast, history and flood record on riverwaterlevels.com</a></p>' % (esc(rp), esc(st), G["site"], esc(G["obs"]), h, full)
    return ('<!doctype html><html lang="en" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>%s</title><meta name="description" content="%s"><link rel="canonical" href="%s">%s<meta name="robots" content="noindex,follow"><style>%s</style></head><body><main id="main" class="embed">%s</main></body></html>' % (
        esc(title), esc(desc), SITE_URL + "/embed" + row["dashboard_url"], HEAD_EXTRA + og_tags(title, desc, full), CSS, body))


def footer():
    return ('<footer><span>%s &middot; Data: USGS, NOAA, NWS.</span><span><a href="/about/">About</a> &middot; <a href="/data-sources/">Data sources</a> &middot; <a href="/disclaimer/">Disclaimer</a> &middot; '
            '<a href="/faq/">FAQ</a> &middot; <a href="/methodology/">Methodology</a> &middot; <a href="/privacy/">Privacy</a> &middot; <a href="/glossary/">Glossary</a> &middot; <a href="/status/">Data status</a> &middot; <a href="/embed/">Add to your site</a></span></footer>' % esc(BRAND))


def og_tags(title, desc, url):
    return ('<meta property="og:type" content="website"><meta property="og:site_name" content="%s"><meta property="og:title" content="%s"><meta property="og:description" content="%s"><meta property="og:url" content="%s"><meta property="og:image" content="%s/og.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="River Water Levels: current flow, gage height and how it compares with normal for US river gauges"><meta name="twitter:card" content="summary_large_image">'
            % (esc(BRAND), esc(title), esc(desc), esc(url), SITE_URL))


def mk_title(base):
    return base  # one pattern on every page; the brand sits in the nav


def humanize_iso(text):
    return re.sub(r"\d{4}-\d{2}-\d{2}", lambda m: fdate(m.group(0)), text)


def nav():
    return '<a class="skip" href="#main">Skip to content</a><nav class="nav" aria-label="Site"><a class="brand" href="/"><span class="logo"></span>%s</a><span class="tabs"><a href="/">Rivers</a><a href="/about/">About</a></span><span class="ns"><input id="gq" type="search" placeholder="Find a river or place" aria-label="Find a river or place" autocomplete="off"><span id="gr" class="gr" hidden></span></span><button type="button" class="themebtn" id="themebtn" aria-label="Switch between dark and light" title="Dark or light">&#9680;</button></nav>' % esc(BRAND) + THEME_JS + NAVSEARCH_JS + FOLD_JS


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
    return ('<details class="card fold srcall" data-g="data" id="sources"><summary><b>Sources and method</b><span>%d data sources, how the percentile is calculated, disclaimer</span></summary><ul>%s</ul><p class="src">%s</p><p class="src">Percentile method: %s.</p><p class="src">%s</p></details>' % (
        len(ids), lis, esc(humanize_iso(stats_src) if stats_src else "USGS daily statistics: not available for this gauge."), esc(G["method"]), esc(DISCLAIMER)))


LIVE_JS = """<script>(function(){var ID="USGS-@SITE@",Z="@TZ@",hero=document.querySelector('.hero');if(!hero||!window.fetch)return;var snap=Date.parse(hero.getAttribute('data-t')),n=0;
function q(k){return document.querySelector('[data-live="'+k+'"]')}
function f(v){var a=Math.abs(v);return a>=100?Math.round(v).toLocaleString('en-US'):a>=10?v.toFixed(0):a<1?v.toFixed(2):v.toFixed(1)}
function lt(d){return d.toLocaleString('en-US',{timeZone:Z,month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'})}
function age(d){var m=Math.round((Date.now()-d)/60000);return m<180?m+' min':m<2880?Math.round(m/60)+' h':Math.round(m/1440)+' d'}
var ag=q('age');if(ag)ag.textContent=age(new Date(snap));
function usgs(){return fetch('https://api.waterdata.usgs.gov/ogcapi/v0/collections/latest-continuous/items?monitoring_location_id='+ID+'&parameter_code=00060,00065&f=json').then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(j){var F=null,S=null;(j.features||[]).forEach(function(x){var p=x.properties,v=parseFloat(p.value);if(isNaN(v))return;if(p.parameter_code==='00060')F={v:v,t:new Date(p.time)};if(p.parameter_code==='00065')S={v:v,t:new Date(p.time)}});return [F,S]})}
function edge(){return fetch('/live.json').then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(j){var g=j&&j.g&&j.g[ID.slice(5)];if(!g||!g.f)throw 0;return [{v:g.f[0],t:new Date(g.f[1])},g.h?{v:g.h[0],t:new Date(g.h[1])}:null]})}
function apply(a){var F=a[0],S=a[1];
if(F&&F.t.getTime()>=snap){q('flow').textContent=f(F.v);var fo=q('flowobs');if(fo)fo.textContent=lt(F.t);q('obs').textContent=lt(F.t);if(ag)ag.textContent=age(F.t);var st=q('stage'),so=q('stageobs');if(S&&st&&S.t.getTime()>=snap){st.textContent=S.v.toFixed(2);if(so)so.textContent=lt(S.t)}if(F.t.getTime()>snap){[].slice.call(document.querySelectorAll('.fcnote')).forEach(function(e){e.hidden=true});var bn=document.getElementById('lbn');if(!bn){bn=document.createElement('p');bn.id='lbn';bn.className='src lf2';bn.textContent='Flow and gage height at the top updated '+lt(F.t)+'. Charts, tables and comparisons below are as of the page build, '+lt(new Date(snap))+'.';hero.parentNode.insertBefore(bn,hero.nextSibling)}var nt=' The flow above is newer than this comparison, which is as of '+lt(new Date(snap))+'.',pc=document.getElementById('pcap'),cc=document.getElementById('ccap');if(pc){pc.setAttribute('data-n','1')}if(cc&&cc.getAttribute('data-n')!=='1'){cc.textContent+=nt;cc.setAttribute('data-n','1')}}}}
function fail(){var a=q('age'),hh=document.querySelector('.hero2'),old=hh&&(Date.now()-new Date(hh.getAttribute('data-t')))>3600000;if(a&&old&&!document.getElementById('lf')){var s=document.createElement('span');s.id='lf';s.className='lf';s.textContent=' \u00b7 live check did not answer; showing the page as built';a.parentNode.parentNode.appendChild(s)}}
function run(){edge().catch(usgs).then(apply).catch(fail)}
run();setInterval(function(){if(!document.hidden)run()},120000)})();</script>"""


AGE_JS = """<script>(function(){var a=document.querySelector('[data-live="age"][data-t]');if(!a)return;var t=Date.parse(a.getAttribute('data-t'));function u(){var m=Math.round((Date.now()-t)/60000);a.textContent=m<180?m+' min':m<2880?Math.round(m/60)+' h':Math.round(m/1440)+' d'}u();setInterval(u,60000)})();</script>"""


SAFETY = '<p class="src safety">Government data, shown with the time it was observed or issued. It is not a flood warning, and it does not decide for you: no alert does not mean conditions are safe. <a href="/disclaimer/">Disclaimer</a></p>'


# the phone tab of a block: by id, because a gauge with no river forecast has no "Forecast" heading to start the weather group
# phone tab of a block: its "SEC:" heading decides (What the water / Level, flow = Now; Forecast = Forecast; How today = History; folds and the side column = Data / Area); these few ids override their section
GROUP_OF = {"rate_of_change": "history", "snowpack": "data", "water_temp_months": "data", "forecast_rain_totals": "weather", "wpc_outlooks": "weather", "cpc_outlook": "weather"}


RANGE_JS = """<script>(function(){var s=document.querySelectorAll('.rseg');if(!s.length)return;document.documentElement.classList.add('js');s.forEach(function(g){var b=g.parentNode;g.addEventListener('click',function(e){var t=e.target.closest('button');if(!t)return;var r=t.getAttribute('data-r');g.querySelectorAll('button').forEach(function(x){var on=x===t;x.classList.toggle('on',on);x.setAttribute('aria-pressed',on)});b.querySelectorAll('.rg').forEach(function(p){p.classList.toggle('on',p.getAttribute('data-r')===r)})})})})();</script>"""


GTABS_JS = """<script>(function(){var bar=document.querySelector('.gtabs');if(!bar||location.search.indexOf('tabs=off')>=0)return;var m=window.matchMedia('(max-width:760px)'),btns=[].slice.call(bar.querySelectorAll('button')),top=document.getElementById('tabtop');
function grp(el){var g=el&&el.closest?el.closest('[data-g]'):null;return g?g.getAttribute('data-g'):null}
function set(g,scroll){document.querySelectorAll('[data-g]').forEach(function(e){e.classList.toggle('gon',e.getAttribute('data-g')===g)});btns.forEach(function(b){b.classList.toggle('on',b.getAttribute('data-t')===g);b.setAttribute('aria-pressed',b.getAttribute('data-t')===g)});if(scroll&&top)top.scrollIntoView()}
function on(){document.documentElement.classList.add('tabsjs');var h=location.hash.slice(1),t=h&&document.getElementById(h),g=grp(t)||'now';set(g,false);if(t)t.scrollIntoView()}
function off(){document.documentElement.classList.remove('tabsjs')}
function sync(){m.matches?on():off()}
btns.forEach(function(b){b.addEventListener('click',function(){set(b.getAttribute('data-t'),true)})});
window.addEventListener('hashchange',function(){if(!m.matches)return;var t=document.getElementById(location.hash.slice(1)),g=grp(t);if(g){set(g,false);t.scrollIntoView()}});
document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a[href^="#"]');if(!a||!m.matches||a.getAttribute('href').length<2)return;var t=document.getElementById(a.getAttribute('href').slice(1)),g=grp(t);if(g){set(g,false);t.scrollIntoView()}});
window.addEventListener('beforeprint',off);window.addEventListener('afterprint',sync);if(m.addEventListener)m.addEventListener('change',sync);sync()})();</script>"""


FOLD_JS = """<script>(function(){function o(){var h=location.hash.slice(1),e=h&&document.getElementById(h),d=e&&e.closest('details');if(d&&!d.open){d.open=true;e.scrollIntoView()}}
window.addEventListener('hashchange',o);o();window.addEventListener('beforeprint',function(){[].slice.call(document.querySelectorAll('details.fold')).forEach(function(d){d.open=true})})})();</script>"""


THEME_JS = """<script>(function(){var r=document.documentElement,b=document.getElementById('themebtn');try{var s=localStorage.getItem('rwl_theme');if(s==='light'||(!s&&window.matchMedia&&matchMedia('(prefers-color-scheme: light)').matches))r.setAttribute('data-theme','light')}catch(e){}if(b)b.addEventListener('click',function(){var l=r.getAttribute('data-theme')==='light';if(l)r.removeAttribute('data-theme');else r.setAttribute('data-theme','light');try{localStorage.setItem('rwl_theme',l?'dark':'light')}catch(e){}})})();</script>"""


CITE_JS = """<script>(function(){var b=document.querySelector('[data-cite]');if(!b||!navigator.clipboard)return;b.addEventListener('click',function(){navigator.clipboard.writeText(b.parentNode.querySelector('small').textContent.replace(/^Cite: /,'')).then(function(){b.textContent='Copied'})})})();</script>"""
NAVSEARCH_JS = """<script>(function(){var i=document.getElementById('gq'),o=document.getElementById('gr'),d=null;if(!i||!o||!window.fetch)return;function load(){if(d)return Promise.resolve(d);return fetch('/gauges.json').then(function(r){return r.json()}).then(function(j){d=j;return j}).catch(function(){d=[];return d})}
function show(q){q=q.toLowerCase().replace(/\\bst\\.? /g,'saint ').trim();o.textContent='';if(q.length<2){o.hidden=true;return}load().then(function(j){var n=0,hits=[];j.forEach(function(g){if((g[0]+' '+(g[4]||'')).toLowerCase().replace(/[,.]/g,' ').replace(/\\bst\\.? /g,'saint ').replace(/\\s+/g,' ').indexOf(q.replace(/[,.]/g,' ').replace(/\\s+/g,' '))>=0){hits.push(g)}});hits.sort(function(a,b){return (a[0].toLowerCase().indexOf(q)===0?0:1)-(b[0].toLowerCase().indexOf(q)===0?0:1)});hits.slice(0,8).forEach(function(g){var a=document.createElement('a');a.href=g[1];a.textContent=g[0];o.appendChild(a);n++});if(!n){var s=document.createElement('span');s.innerHTML='No match: this site has '+j.length+' gauges so far. <a href="https://water.noaa.gov/" rel="noopener">Look up any river at water.noaa.gov</a>';o.appendChild(s)}o.hidden=false})}
i.addEventListener('input',function(){show(i.value)});i.addEventListener('keydown',function(e){if(e.key==='Enter'){var as=o.querySelectorAll('a[href^="/river/"]'),a=null;for(var k=0;k<as.length;k++){if(as[k].getAttribute('href')!==location.pathname){a=as[k];break}}if(a){e.preventDefault();location.href=a.getAttribute('href')}}});i.addEventListener('focus',load);document.addEventListener('click',function(e){if(!o.contains(e.target)&&e.target!==i)o.hidden=true})})();</script>"""


ALERTS_JS = """<script>(function(){var b=document.getElementById('alerts');if(!b||!window.fetch)return;var Z="@TZ@",CTY="@CTY@",IG=['Test Message','Administrative Message'];
function lt(d){return d.toLocaleString('en-US',{timeZone:Z,month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'})}
function ast(p){var s=[];((p.geocode&&p.geocode.UGC)||[]).forEach(function(u){var k=u.slice(0,2);if(s.indexOf(k)<0)s.push(k)});return s.length?' ('+s.sort().join(', ')+')':''}
function as(s){var a=s.split(';').map(function(x){return x.trim()}).filter(Boolean),c=CTY.toLowerCase().replace(/ (county|parish)$/,'');if(c){var m=a.filter(function(x){var y=x.toLowerCase();return y===c||y.slice(-c.length-1)===' '+c});a=m.concat(a.filter(function(x){return m.indexOf(x)<0}))}return a.length<=6&&!c?s:a.slice(0,6).join('; ')+(a.length>6?'; and '+(a.length-6)+' more areas':'')}
function el(t,c,x){var e=document.createElement(t);if(c)e.className=c;if(x)e.textContent=x;return e}
fetch('https://api.weather.gov/alerts/active?point=@LAT@,@LON@',{headers:{Accept:'application/geo+json'}}).then(function(r){return r.json()}).then(function(j){if(!j||!j.features)return;
var al=j.features.map(function(f){return f.properties}).filter(function(p){return IG.indexOf(p.event)<0}),src=b.querySelector('.srcd')||b.querySelector('.src'),sp=b.querySelector('.src');if(!src||!sp)return;
Array.prototype.slice.call(b.children).forEach(function(c){if(c.tagName!=='H2'&&c!==src)b.removeChild(c)});
if(!al.length){b.insertBefore(el('p','','No active National Weather Service alerts were returned for this location. This is not a statement that conditions are safe.'),src)}
al.forEach(function(p){var d=el('div','alert'),e=p.ends||p.expires;d.appendChild(el('b','',p.event||''));d.appendChild(document.createTextNode(' \\u00b7 '+(p.severity||'severity not stated')+' \\u00b7 '+(as(p.areaDesc||'')+ast(p))));d.appendChild(document.createElement('br'));d.appendChild(document.createTextNode(p.headline||''));d.appendChild(document.createElement('br'));d.appendChild(document.createTextNode('Ends '+(e?lt(new Date(e)):'not stated')));b.insertBefore(d,src)});
var bn=document.querySelector('a.abanner'),hr=document.querySelector('.hero');if(al.length){if(!bn&&hr){bn=el('a','abanner');bn.href='#alerts';hr.parentNode.insertBefore(bn,hr)}if(bn){bn.textContent='';bn.appendChild(el('b','',al.length+' active National Weather Service alert'+(al.length===1?'':'s')));bn.appendChild(el('span','',al.map(function(p){return p.event}).join('; ')));bn.appendChild(el('em','','Details'))}}else if(bn){bn.parentNode.removeChild(bn)}
var t=document.querySelector('.tile.alrt');if(t){var tv=t.querySelector('b'),ts=t.querySelector('small');t.className='tile alrt '+(al.length?'on':'off');if(tv)tv.textContent=al.length||'No alerts';if(ts)ts.textContent=al.length?al.map(function(p){return p.event}).join('; '):'No alerts active here. Checked live '+lt(new Date())+'.'}
var pl=document.querySelector('.answer .a3');if(pl){pl.className='a3 '+(al.length?'ay':'an');pl.textContent=al.length?al.length+' active NWS alert'+(al.length===1?'':'s'):'No active NWS alerts'}
sp.textContent='Source: National Weather Service alerts for the gauge location, fetched '+lt(new Date())+' (live from the NWS when this page loaded).'}).catch(function(){})})();</script>"""


INDEX_CFG = None  # set by build.py from data/index-allow.json


def robots_meta(path):
    from lib import indexing
    return indexing.robots_meta(path, INDEX_CFG) if INDEX_CFG is not None else ""


HEAD_EXTRA = '<link rel="icon" href="/favicon.svg" type="image/svg+xml"><meta name="theme-color" content="#1d5fa8">'


def crumb_ld(items):
    """BreadcrumbList markup that mirrors the visible breadcrumb exactly (name, absolute URL)."""
    els = [{"@type": "ListItem", "position": i + 1, "name": n, **({"item": SITE_URL + u} if u else {})} for i, (n, u) in enumerate(items)]
    return '<script type="application/ld+json">%s</script>' % json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": els}, separators=(",", ":")).replace("</", "<" + chr(92) + "/")


JUMP = (("alerts", "Alerts"), ("flow_chart", "7 days"), ("stage_chart", "Gage height"), ("river_forecast", "River forecast"), ("hourly_heatmap", "Hourly forecast"), ("month_chart", "30 days"), ("multi_year", "Earlier years"),
        ("record_comparison", "Record"), ("annual_peaks", "Flood record"), ("related_gauges", "Upstream and downstream"), ("nearby_gauges", "Nearby gauges"), ("about_gauge", "About"))


CHART_RANGES = (("flow_chart", "7 days"), ("month_chart", "30 days"), ("year_chart", "12 months"), ("multi_year", "Earlier years"))


def merge_charts(blocks):
    """The same flow series drawn four times (7 days, 30 days, 12 months, earlier years) becomes ONE block with a range switch. Every panel keeps its own chart, table and Source line in the HTML."""
    have = {b["id"]: b for b in blocks if isinstance(b, dict) and b["id"] in dict(CHART_RANGES)}
    if "flow_chart" not in have or len(have) < 2:
        return blocks
    first = have["flow_chart"]
    ordered = [(i, lab, have[i]) for i, lab in CHART_RANGES if i in have]
    seg = '<div class="rseg" role="group" aria-label="Time range">%s</div>' % "".join('<button type="button" data-r="%s"%s>%s</button>' % (i, ' class="on" aria-pressed="true"' if k == 0 else ' aria-pressed="false"', lab) for k, (i, lab, _) in enumerate(ordered))
    panels = "".join('<div class="rg%s" data-r="%s"><h3 class="rgh">%s</h3>%s</div>' % (" on" if k == 0 else "", i, lab, b["body"]) for k, (i, lab, b) in enumerate(ordered))
    merged = dict(first, heading="Flow over time", body=seg + panels,
                  source=" ".join("%s: %s" % (lab, b["source"]) for i, lab, b in ordered), also=sorted({x for i, lab, b in ordered for x in [b["src_id"]] + list(b.get("also") or [])} - {first["src_id"]}))
    out = []
    for b in blocks:
        if isinstance(b, dict) and b["id"] in have:
            if b["id"] == "flow_chart":
                out.append(merged)
            continue
        out.append(b)
    return out


def build_tab(tab, G, pages):
    T = TABS[tab]
    row = G["row"]
    raw = tab_blocks(tab, G, pages)
    ok = lambda b: b and (PREVIEW or SOURCES[b["src_id"]]["status"] in ("quoted", "owner-permission"))
    blocks = []
    for b in raw:
        if isinstance(b, str) and b.startswith(("SEC:", "FOLD:")):
            blocks.append(b)
        elif isinstance(b, tuple):  # ("PAIR", a, b): two blocks side by side from 900 px up; a lone survivor renders as a normal block
            g = [x for x in b[1:] if ok(x)]
            blocks.append(g if len(g) > 1 else (g[0] if g else None))
        elif b == "AD" or ok(b):
            blocks.append(b)
    blocks = [b for b in blocks if b]
    blocks = merge_charts(blocks)
    flat = [x for b in blocks for x in (b if isinstance(b, list) else [b])]
    shown = [b for b in flat if isinstance(b, dict)]
    river, place, st = G["river"], G["place"], G["st"]
    rp = river_at(river, place)
    # SEO review 2026-10-21: the query is "<river> water level"; the one templated competitor that ranks carries the reading in its title
    reading = ", ".join(x for x in (("water level %.2f ft" % G["sg"][-1][1]) if G["sg"] else "", ("flow %s cfs" % fmtc(G["lv"])) if G["lv"] is not None else "") if x) or "water level and flow"
    title = mk_title("%s, %s: %s" % (rp, st, reading)) if tab == "dashboard" else mk_title(T["title"] % (rp, st))
    if tab == "dashboard":  # dynamic meta description: lead with the live reading + comparison so the SERP snippet / AI citation carries the number, not boilerplate
        cls = band_word(G["p"]) if G.get("p") is not None else ""
        norm = (", %s for %s" % (cls.lower(), G["ldate"].strftime("%b %d").replace(" 0", " "))) if cls and cls != "–" else ""
        desc = "%s, %s: %s%s." % (rp, st, reading, norm)
        tail = " Live USGS flow, gage height and how it compares with past years."
        if len(desc) + len(tail) <= 198:  # check.py caps the meta description at 200 chars; keep the valuable reading lead, add the tail only when it fits
            desc += tail
    else:
        desc = T["desc"] % (rp, st, G["site"])
    url = SITE_URL + row[tab + "_url"] if tab != "dashboard" else SITE_URL + row["dashboard_url"]
    amber = ""  # the age chip in the same line already says how old and colours by age (design review 2026-10-21: one statement of age)
    avail = ("dashboard",)  # one page per gauge: no tabs
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
    fl7 = [x[0] for x in G["fl"]]
    ld = crumb_ld(ld_items) + '<script type="application/ld+json">%s</script>' % json.dumps({
        "@context": "https://schema.org", "@type": "WebPage", "name": title, "url": url, "dateModified": iso(G["lt"]), "isPartOf": {"@type": "WebSite", "name": BRAND, "url": SITE_URL, "publisher": {"@type": "Organization", "name": BRAND, "url": SITE_URL}},
        "about": {"@type": "Place", "name": "%s, %s" % (rp, st), "geo": {"@type": "GeoCoordinates", "latitude": round(G["lat"], 4), "longitude": round(G["lon"], 4)}},
        "mainEntity": {"@type": "Dataset", "name": "USGS gauge %s, %s, %s: flow and gage height" % (G["site"], rp, st), "description": "7-day flow and gage height readings and daily mean flow by year at USGS gauge %s, provisional data subject to revision." % G["site"],
                       "url": url, "license": "https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits", "creator": {"@type": "Organization", "name": "U.S. Geological Survey", "url": "https://www.usgs.gov/"},
                       "temporalCoverage": ("%s/%s" % (iso(min(fl7)), iso(G["lt"]))) if fl7 else iso(G["lt"]), "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": url + "data.json"}]}})
    ids = {b["id"] for b in shown}
    jl = [(i, t) for i, t in JUMP if i in ids]
    jump_html = ('<nav class="jump" aria-label="On this page">%s</nav>' % " ".join('<a href="#%s">%s</a>' % (i, t) for i, t in jl)) if tab == "dashboard" and len(jl) >= 4 else ""
    SIDE = {"recreation_sites", "related_gauges", "nearby_gauges", "nws_forecast_point", "flood_stages", "public_land", "about_gauge", "gauge_map", "sun", "air_obs", "official_links"}
    body = ""
    side = ""
    fold = None  # [title, rendered blocks, headings] while inside a FOLD: group
    grp = ["now"]
    used = {"now"}

    def gtag(h, g):
        used.add(g)
        return re.sub(r"^<(\w+)", lambda m: '<%s data-g="%s"' % (m.group(1), g), h, count=1)

    pending = None  # a "SEC:" heading is written only when a block follows it

    def flush():
        nonlocal body, fold
        if fold and fold[1]:
            body += gtag('<details class="fold"><summary><b>%s</b><span>%d section%s: %s</span></summary>%s</details>' % (esc(fold[0]), len(fold[2]), "" if len(fold[2]) == 1 else "s", " &middot; ".join(esc(x) for x in fold[2]), fold[1]), "history" if fold[0].startswith("Flood record") else "data")
        fold = None
    for b in blocks:
        if isinstance(b, str) and b.startswith("SEC:"):
            flush()
            grp[0] = "weather" if b[4:].startswith("Forecast") else "history" if b[4:].startswith("How today") else "now" if b[4:].startswith(("What the water", "Level, flow")) else grp[0]
            pending = gtag('<h2 class="secth">%s</h2>' % esc(b[4:]), grp[0])
            continue
        if isinstance(b, str) and b.startswith("FOLD:"):
            flush()
            pending = None
            fold = [b[5:], "", []]
            continue
        if T["hero"] and isinstance(b, dict) and b["id"] in SIDE:
            side += gtag(render_block(b), "area")
            continue
        html = ('<div class="ad">ADVERTISEMENT</div>' if ADS else "") if b == "AD" else ('<div class="pair">%s</div>' % "".join(render_block(x) for x in b)) if isinstance(b, list) else render_block(b)
        if fold is not None and isinstance(b, dict):
            fold[1] += html
            fold[2].append(b["heading"])
        else:
            if pending and isinstance(b, (dict, list)):
                body += pending
                pending = None
            gid = GROUP_OF.get(b["id"] if isinstance(b, dict) else (b[0]["id"] if isinstance(b, list) and b and isinstance(b[0], dict) else ""), grp[0])
            body += gtag(html, gid) if html else html
    flush()
    gt_html = ""
    if T["hero"] and len(used) > 1:
        names = [("now", "Now"), ("weather", "Forecast"), ("history", "History"), ("data", "Data"), ("area", "Area")]
        gt_html = '<div id="tabtop"></div><nav class="gtabs" aria-label="Page sections">%s</nav>' % "".join('<button type="button" data-t="%s">%s</button>' % (k, v) for k, v in names if k in used)
    if T["hero"] and side:
        body = '<div class="cols"><div class="main2">%s</div><aside class="side" aria-label="Around this gauge">%s</aside></div>' % (body, side)
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>%s</title><meta name="description" content="%s">'
            '<link rel="canonical" href="%s">%s<style>%s</style></head><body>%s<main id="main">%s<h1>%s, %s</h1><p class="sub">%s</p><p><span class="tabs">%s</span></p>%s%s%s</main>%s%s</body></html>' % (
                esc(title), esc(desc), url, ADSENSE + HEAD_EXTRA + og_tags(title, desc, url) + ld + robots_meta(row[tab + "_url"]), CSS, nav(), crumb, esc(rp), esc(st), sub, tabs_html, (hero(G, pages) + SAFETY + jump_html + gt_html) if T["hero"] else "", body, sources_block(shown, G) + (LIVE_JS.replace("@SITE@", G["site"]).replace("@TZ@", G["tzname"]) + GTABS_JS + RANGE_JS + CITE_JS if T["hero"] else AGE_JS) + (ALERTS_JS.replace("@LAT@", "%.4f" % G["lat"]).replace("@LON@", "%.4f" % G["lon"]).replace("@TZ@", G["tzname"]).replace("@CTY@", ((((G["rec"].get("meta") or {}).get("loc")) or {}).get("county_name") or "").replace('"', "")) if any(b["id"] == "alerts" for b in shown) else ""), footer(), tabbar))
    meta = {"site": G["site"], "tab": tab, "url": row[tab + "_url"] if tab != "dashboard" else row["dashboard_url"], "title": title, "blocks": [b["id"] for b in shown], "age_min": round(G["age_min"]),
            "hash": hashlib.sha256(page.encode()).hexdigest()[:16]}
    return page, meta


from lib import blocks2 as b2  # noqa: E402  (blocks added after the fresh-eyes review; uses the helpers above)
from lib import blocks3 as b3  # noqa: E402
import lib.hero as _hero
_hero.b3 = b3  # hero reads b3.window_change / b3.conditions; blocks3 itself imports the facade, so it can only be loaded after hero


SAFETY_BLOCKS = ("b_alerts", "b_river_forecast", "b_impacts", "b_stage_chart", "b_flow_chart", "b_offline", "b_flood_stages", "b_noforecast", "b_nws_point")  # a hidden one of these fails the gauge instead of shipping a page that looks complete


def _guard_blocks():
    # Wrap each b_* once; rebind the wrapper in every module that holds the original so internal calls stay guarded.
    import sys
    mods = [sys.modules[n] for n in ("lib.core", "lib.hero", "lib.charts", "lib.weather", "lib.forecast", "lib.page", "lib.render", "lib.blocks2", "lib.blocks3") if n in sys.modules]
    wrapped = {}
    for mod in mods:
        for name, fn in list(vars(mod).items()):
            if name.startswith("b_") and callable(fn):
                if getattr(fn, "_guarded", False):
                    continue
                w = wrapped.get(id(fn))
                if w is None:
                    w = wrapped[id(fn)] = _safe(fn)
                setattr(mod, name, w)
