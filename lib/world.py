"""Gauges outside the US on the US page: a feed row becomes the record lib/hero.py reads (stage only, no flow), the US builder makes the page, this file only swaps agency words.
One template, so every fix to the gauge page reaches these too. A new feed adds a FEEDS row and a fetch in collect.py."""
import datetime, re
from lib import render
import os, zoneinfo
from lib import core, ui, wx
from lib.common import parse_t
from lib.core import HIDE_H, hours_old
from lib.directory import esc, world_gauge_url, world_slug

FEEDS = {"pegelonline": {"agency": "WSV", "name": "German Federal Waterways and Shipping Administration (WSV)", "api": "PEGELONLINE", "unit": "cm", "zone": "Europe/Berlin", "src": "pegelonline", "emergency": "Emergency in Germany: 112 fire and ambulance, 110 police.", "wx": "DWD", "wx_site": "dwd.de", "wx_credit": "Weather and alerts: Deutscher Wetterdienst (DWD), CC BY 4.0, shortened and converted."},
         "eccc": {"agency": "ECCC", "name": "Environment and Climate Change Canada", "api": "Water Survey of Canada", "unit": "m", "zone": "America/Toronto", "src": "eccc", "emergency": "Emergency in Canada: 911 where available.", "wx": "Environment Canada", "wx_site": "weather.gc.ca", "wx_credit": "Weather and alerts: Environment and Climate Change Canada."}}
LABEL = {"low": "Low", "normal": "Normal", "high": "High"}
MARKS = (("HHW", "Highest on record"), ("HW", "Agency reference high (HW)"), ("HSW", "Highest level for shipping"), ("M_II", "High-water shipping mark II"), ("M_I", "High-water shipping mark I"), ("MHW", "Mean high water"),
         ("MW", "Average level"), ("MNW", "Mean low water"), ("GlW", "Equivalent low water (GlW)"), ("NW", "Agency reference low (NW)"), ("NNW", "Lowest on record"), ("MMAX", "Highest monthly mean for this month"), ("MAVG", "Average monthly mean for this month"), ("MMIN", "Lowest monthly mean for this month"))
ROW = {"name_confidence": "high", "nws_lid": "", "place_final": "", "raw_name": "", "score": "0", "wave": "", "years_record": "0", "drainage_sqmi": "0"}


def ready(r):
    """The ship test: a real recent reading with its time. The series draws the chart; marks are shown when the agency has them."""
    return r.get("cm") is not None and bool(r.get("time")) and r.get("lat") is not None and r.get("lon") is not None and len(r.get("series") or []) >= 8


def to_ft(v, unit):
    return v / 30.48 if unit == "cm" else v * 3.28084


def fmt_level(v, unit):
    return "%.0f cm" % v if unit == "cm" else "%.2f m" % v


def canada_label(r, when):
    """Canada publishes no label. Ours: today's level ranked among past monthly means for this month, needing 10 years; the page says it is our calculation."""
    every = (r.get("months") or {}).get("%02d" % when.month) or []
    past = sorted(every[-20:])  # oldest first from collect: a gauge's zero can shift across decades, so only the latest 20 years rank today
    if len(past) < 10:
        return "Unknown", "Canada publishes no normal range, and this gauge has too few years to compare.", {}
    q1, q3 = past[len(past) // 4], past[3 * len(past) // 4]
    word = "Low" if r["cm"] < q1 else "High" if r["cm"] > q3 else "Normal"
    return word, "Our calculation: today's level against the latest %d years of monthly means for %s, from ECCC data." % (len(past), when.strftime("%B")), {"MMAX": max(every), "MAVG": round(sum(every) / len(every), 3), "MMIN": min(every)}


def to_rec(page, r):
    key = page.get("feed", "pegelonline")
    f = dict(FEEDS[key])
    f["unit"], f["zone"] = r.get("unit", f["unit"]), r.get("zone", f["zone"])
    if key == "eccc":
        label, note, marks = canada_label(r, datetime.datetime.fromisoformat(r["time"].replace("Z", "+00:00")))
        marks = dict(marks, **(r.get("record") or {}))
    else:
        label, note, marks = LABEL.get(r.get("state"), "Unknown"), "%s label, against this gauge's mean low and mean high water." % f["agency"], r.get("marks") or {}
    rows = [{"parameter_code": "00065", "time": t, "value": str(round(to_ft(v, f["unit"]), 3)), "unit_of_measure": "ft", "qualifier": None, "approval_status": "Provisional"} for t, v in r["series"]]
    seen, kept = set(), {}
    for k in ("HHW", "NNW") + tuple(m[0] for m in MARKS):  # the agency repeats a value under several marks: the record name wins
        if k in marks and k not in kept and marks[k] not in seen:
            seen.add(marks[k])
            kept[k] = marks[k]
    marks = kept
    if marks.get("NNW") is not None and r["cm"] < marks["NNW"]:
        note = "Below the lowest level on record, %s. " % fmt_level(marks["NNW"], f["unit"]) + note
    elif marks.get("HHW") is not None and r["cm"] > marks["HHW"]:
        note = "Above the highest level on record, %s. " % fmt_level(marks["HHW"], f["unit"]) + note
    if r.get("flag"):
        note = "Agency flag on this reading: %s. " % r["flag"] + note
    wt = (r.get("also") or {}).get("WT")
    if wt and isinstance(wt[0], (int, float)):
        rows.append({"parameter_code": "00010", "time": wt[3] if len(wt) > 3 else r["time"], "value": str(wt[0]), "unit_of_measure": "degC", "qualifier": None, "approval_status": "Provisional"})
    w = r.get("wx") or {}
    links = [("Official gauge page (%s)" % f["agency"], "https://wateroffice.ec.gc.ca/report/real_time_e.html?stn=%s" % r["name"] if key == "eccc" else "https://www.pegelonline.wsv.de/gast/stammdaten?pegelnr=%s" % r.get("number"))] if key == "eccc" or r.get("number") else []
    links.append(("Weather warnings (%s)" % f["wx"], w.get("city_url") or ("https://weather.gc.ca/" if key == "eccc" else "https://dwd.de/warnungen")))
    return {"site": f["agency"] + "-" + world_slug(r["name"]), "lat": r["lat"], "lon": r["lon"], "tz": f["zone"], "usgs": {"fetched_at": r["time"], "rows": rows, "truncated": False}, "_fetched": {}, "access": r.get("access"), "nws": w, "rain": w.get("rain") or {},
            "feed": dict(f, emergency="Emergency: call the local emergency number." if w.get("abroad") else f["emergency"], label=label, label_note=note, norm="%s, %s" % (label, "our calculation" if key == "eccc" else "%s label" % f["agency"]), ship=r.get("ship"), marks=marks, station=r["name"], wt30=r.get("wt30"), normals=r.get("normals"), drought=r.get("drought"), drought_map=r.get("drought_map"), normals_by="Environment and Climate Change Canada" if key == "eccc" else "Deutscher Wetterdienst", normals_src="eccc" if key == "eccc" else "dwd", fc=r.get("fc"), flow=r.get("flow"), days=r.get("days"), deciles=r.get("deciles"), day_years=r.get("day_years"), years=r.get("years"), aq=w.get("aq"), links=links, no_weather=w.get("no_weather"))}


def to_row(page, r):
    u = world_gauge_url(page, r.get("title") or r["name"])
    place = r.get("title") or r["name"].replace(" UP", "").title()
    return dict(ROW, site=FEEDS[page.get("feed", "pegelonline")]["agency"] + "-" + world_slug(r["name"]), river=page["river"], place=place, state="ZZ", river_slug=page["slug"], place_slug=world_slug(r.get("title") or r["name"]), dashboard_url=u, water_url=u, forecast_url=u + "forecast/",
                hub_url="/%s/" % page["slug"], hub_slug=page["slug"], _built=True, _hub=False, _single=True, _ll=(r["lat"], r["lon"]), _lv=None, _band="–")


SWAP = (("No active NWS alerts", "No active @WX@ weather alerts"), ("No active National Weather Service alerts were returned for this location.", "No active @WX@ weather alerts were returned for this location. River flood warnings are issued locally and are not in this feed."), ("The newest USGS flow reading", "The newest reading"), ("when USGS publishes", "when the agency publishes"), ("Latest USGS gage height", "Latest water level"), ("Solid line: USGS readings.", "Solid line: official readings."), ("NWS alerts unknown", "Official alerts unknown"), ("NWS alerts", "Official alerts"),
        ("Gage height", "Water level"), ("gage height", "water level"), ("The National Weather Service has no river forecast point for this gauge. The weather forecast below is not a river forecast.", "No river forecast is shown for this gauge."),
        ("We have no answer from the National Weather Service alert service for this location. Check weather.gov.", "No official alert feed is connected for this gauge. Check local authorities."),
        ('<span>River forecast</span><b>Not linked</b>', '<span>River forecast</span><b>Not issued</b>'), ("Data: USGS, NOAA, NWS.", "Data: official agencies, listed on each page."), ("within about 15 miles of the gauge", "within about 25 km of the gauge"), (' <a href="#gauge_map">Map of the gauge location</a>', ""))
LIVE = """<script>(function(){var w=document.querySelector('.hero'),a=document.querySelector('[data-live=age]');function tick(t){if(a){var m=Math.round((Date.now()-Date.parse(t))/60000);a.textContent=m<180?m+' min':m<2880?Math.round(m/60)+' h':Math.round(m/1440)+' d'}}if(!w)return;tick(w.dataset.t);if(!window.fetch)return;fetch('/live/world.json').then(function(r){return r.json()}).then(function(j){var g=(j.g||{})['@N@'];if(!g||Date.parse(g[1])<=Date.parse(w.dataset.t))return;tick(g[1]);
var e=document.querySelector('[data-live=stage]');if(e)e.textContent=g[0].toFixed(@D@);e=document.querySelector('[data-live=obs]');if(e)e.textContent=new Date(g[1]).toLocaleString('en-US',{timeZone:'@Z@',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'})}).catch(function(){})})();</script>"""


def metric(h):
    """Local units first, US in brackets, in one place, so the US template stays as it is. Every °F, mph, mi, in and inHg the US blocks print passes here."""
    temp = lambda m: "%.0f °C (%s °F)" % ((float(m.group(2)) - 32) * 5 / 9, m.group(2))
    h = re.sub(r'(<span data-wx="temp0">)(-?\d+)(</span>)<small>&deg;F</small>', lambda m: "%s%.0f%s<small>&deg;C (%s &deg;F)</small>" % (m.group(1), (float(m.group(2)) - 32) * 5 / 9, m.group(3), m.group(2)), h)
    h = re.sub(r"(-?\d+)<small>&deg;F</small>", lambda m: "%.0f<small>&deg;C (%s &deg;F)</small>" % ((float(m.group(1)) - 32) * 5 / 9, m.group(1)), h)
    h = re.sub(r"(?<![\w(.])()(-?\d+)(?: °F|&deg;F)", temp, h)
    h = re.sub(r"(\d+) mph", lambda m: "%.0f km/h (%s mph)" % (float(m.group(1)) * 1.609, m.group(1)), h)
    h = re.sub(r"(?<![\d.])(\d+(?:\.\d)?) mi\b", lambda m: ("%.1f km" if "." in m.group(1) else "%.0f km") % (float(m.group(1)) * 1.609), h)
    h = re.sub(r"([\d.]+) inHg", lambda m: "%.0f hPa" % (float(m.group(1)) * 33.864), h)
    h = re.sub(r"(\d+\.\d\d) <small>in</small>", lambda m: "%.1f <small>mm</small>" % (float(m.group(1)) * 25.4), h)
    return re.sub(r"(\d+\.\d\d) in(?=[,<])", lambda m: "%.1f mm" % (float(m.group(1)) * 25.4), h)


def localize(h, feed, river, place, hub, flat=False):
    """The US builder's page, in this agency's words. A US word that survives here fails check.py world_rules, so nothing slips through."""
    for a, b in SWAP:
        h = h.replace(a, b.replace("@WX@", feed["wx"]))
    h = re.sub(r"Is this normal for [A-Z][a-z]+ \d+\?", "Is this normal?", h)
    h = re.sub(r"<p>The [^<]*publishes no flood stages[^<]*</p>", "", h)
    h = h.replace('<div class="legend">Wind </div>', "")
    if feed.get("lake"):
        h = h.replace("Weather at the river", "Weather at the lake").replace("<span>River forecast</span>", "<span>Level forecast</span>").replace(">River forecast<", ">Level forecast<")
    h = re.sub(r'<small class="cold">.*?</small>', "", h, flags=re.S)  # the US line cites NWS; no agency here says it
    h = re.sub(r"<script>\(function\(\)\{var (?:m=document\.querySelector\('\[data-wxst\]'\)|b=document\.getElementById\('alerts'\))(?:(?!</script>).)*</script>", "", h, flags=re.S)  # those two refresh from the US weather service: never from a phone abroad
    h = re.sub(r" Credit: [^<]*?subject to copyright\.", "", h).replace(">Official NWS<", ">Official<")  # the US credit is a false statement about any other agency's data
    h = h.replace("National Weather Service", feed["wx"]).replace("USGS sensor", "%s sensor" % feed["agency"]).replace("check weather.gov", "check " + feed["wx_site"]).replace("NWS RFC estimate", "Station rain total")
    h = h.replace("NWS forecast", "forecast").replace("NWS station", "Station").replace("NWS ", feed["wx"] + " ")
    h = h.replace('fill="var(--mut)">ft</text>', 'fill="var(--mut)">%s</text>' % feed["unit"])
    h = metric(h).replace("Government data, shown with", esc(feed["emergency"]) + " Government data, shown with", 1)
    credit = "Source: %s, %s" % (feed["api"], feed["name"])
    head = esc(place) if flat else "%s at %s" % (esc(river), esc(place))
    h = re.sub(r"Source: USGS Water Data API[^<]*", credit + ".", h)
    h = re.sub(r'<div class="crumb">.*?</div>', '<div class="crumb"><a href="/">Home</a> / <a href="%s">%s</a> / %s</div>' % (hub, esc(river), esc(place)), h, count=1)
    h = re.sub(r"<h1>[^<]*</h1>", "<h1>%s water level today</h1>" % head, h, count=1)
    h = re.sub(r"<title>[^<]*</title>", "<title>%s water level today | River Water Levels</title>" % head, h, count=1)
    h = re.sub(r'<meta name="description" content="[^"]*"', '<meta name="description" content="%s: current level, 24 h change and how it compares. Source: %s."' % (head, esc(feed["api"])), h, count=1)
    title = "%s water level today" % head
    h = re.sub(r'(<meta (?:property|name)="(?:og|twitter):(?:title|description)" content=")[^"]*', lambda m: m.group(1) + title, h)
    h = re.sub(r'<p class="cite">.*?</p>', "", h, flags=re.S)
    h = re.sub(r'<script type="application/ld\+json">(?:(?!</script>).)*"mainEntity".*?</script>', "", h, flags=re.S)
    h = re.sub(r"USGS gauge [^&<]*", "Gauge %s " % esc(feed["station"]), h)
    h = re.sub(r'<p class="gaps">.*?</p>', '<p class="gaps">Not published for this gauge: %s.</p>' % ", ".join(feed["gaps"]) if feed.get("gaps") else "", h, flags=re.S)
    h = h.replace("<p>The National Weather Service publishes no flood stages for this gauge, so none are drawn.</p>", "")
    h = re.sub(r'<details[^>]*id="sources">.*?</details>', '<p class="src">Data: %s, %s. %s Readings can be revised by the agency. Not endorsed by the agency. Not for navigation or safety-of-life decisions.</p>' % (esc(feed["agency"]), esc(feed["api"]), esc(feed["wx_credit"])), h, flags=re.S)
    h = h.replace('class="hero hero2"', 'class="hero hero2" data-n="%s"' % esc(feed["station"]), 1)
    h = re.sub(r'<script type="application/ld\+json">(?:(?!</script>).)*"BreadcrumbList".*?</script>', lambda m: render.crumb_ld([("Home", "/"), (river, hub), (place, None)]), h, flags=re.S)
    h = h.replace("Not endorsed by the agency.", TERMS[feed["src"]] + " Not endorsed by the agency.", 1)
    h = re.sub(r'<script>\(function\(\)\{var ID="USGS-.*?</script>', lambda m: LIVE.replace("@N@", feed["station"]).replace("@Z@", feed["zone"]).replace("@D@", "2" if feed["unit"] == "m" else "0"), h, flags=re.S)
    return h


PROOFS = ("reading", "time", "alerts", "unit", "terms", "water")
PROVED = {  # what a person or script saw on live data, one line each; a country with a gap fails check.py before any of its pages ship. An alert proof means a real live alert reached the code, not an empty list
    "pegelonline": {"reading": "tools/truth_world.py 0 faults 2026-11-02", "time": "Kaub page 3:00 AM CET against feed timestamp +01:00, 2026-11-02", "alerts": "Kaub frost warning from the DWD zip reached the point test, Zurich none, 2026-11-02", "unit": "cm above gauge zero, PEGELONLINE", "terms": "DL-DE-Zero-2.0; DWD CC BY 4.0, read 2026-11-02", "water": "inland rivers and Lake Constance, no tidal gauge listed"},
    "eccc": {"reading": "tools/truth_world.py 0 faults 2026-11-02", "time": "Squamish 02:05Z feed against page; BC is permanent UTC-7 since 2026 (IANA 2026b), shown as PT", "alerts": "real fog advisory at Berens River hit the point test 2026-11-02; status words are issued and continued", "unit": "metres; Ottawa on a survey datum, not gauge zero", "terms": "open licence, read 2026-11-01", "water": "inland rivers; test gauges not tidal"}}


def proof_faults(feeds, proved):
    return ["%s has no proof of %s" % (f, k) for f in feeds for k in PROOFS if len((proved.get(f) or {}).get(k) or "") < 10]


US_ONLY = "none: US federal product, no counterpart in this country's open feeds"
NO_GAUGE = "none: the agency publishes no such record for its gauges"
COVER = {  # every block on a US gauge page, per country (eccc, pegelonline). have = on the page; none = no official source, with the reason; next = a source exists and is not wired, so no new gauges for that country (check.py)
    "b_offline": ("have", "have"),
    "b_flow_behind": ("none: the headline is water level, and the flow chart carries its own reading times", "none: the headline is water level, and the flow chart carries its own reading times"),
    "b_alerts": ("have", "have"), "b_stage_chart": ("have", "have"), "b_official_marks": ("have", "have"),
    "b_hourly": ("have", "have"), "b_weather": ("have", "have"), "b_air": ("have", "have"), "b_air_quality": ("have", "have"), "b_official_links": ("have", "have"),
    "b_flow_chart": ("have", "have"),
    "b_rate": ("none: the 24 h change tile and the flow line carry it", "none: the 24 h change tile and the flow line carry it"),
    "b_rain": ("none: city pages carry no rain total; the SWOB record at Ottawa airport carried none on 2026-11-02", "have"),
    "b_river_forecast": ("none: river forecasts are provincial in Canada, with no national open feed", "have"),
    "b_quality": ("none: the Water Office real-time feed publishes level and flow only", "have"),
    "b_wtemp": ("none: the Water Office real-time feed publishes level and flow only", "have"),
    "b_qpf": ("none: city forecast text carries rain chance, no totals", "have"),
    "b_acis": ("have", "have"),
    "b_month_chart": ("none: the history table carries this date against every year", "none: PEGELONLINE keeps 30 days and no history"),
    "b_year_chart": ("none: the history table lists each recent year", "none: PEGELONLINE keeps 30 days and no history"),
    "b_multiyear": ("have", "none: PEGELONLINE keeps 30 days and no history"),
    "b_sustained": ("none: US block reads flow percentiles, which Canada does not publish", "none: PEGELONLINE keeps 30 days and no history"),
    "b_record": ("have", "none: record marks are shown in official marks"),
    "b_flowdur": ("have", "none: PEGELONLINE keeps 30 days and no history"),
    "b_peaks": ("have", "none: PEGELONLINE publishes marks, not annual peaks"),
    "b_stage_years": ("have", "none: PEGELONLINE publishes marks, not yearly values"),
    "b_daily": ("none: published daily means end over a year back; the chart and our archive cover recent days", "none: PEGELONLINE keeps 30 days and no history"),
    "b_drought": ("have", "none: DWD publishes crop soil moisture and a climate index, no drought class for a place"),
    "b_access": ("have", "have"),
    "b_related": ("none: stations in the feed carry no upstream or downstream order", "have"), "b_nearby": ("have", "have"),
    "b_about": ("have", "have"),
    "b_map": ("none: the map service is USGS, US only; links open the agency map", "none: the map service is USGS, US only; links open the agency map"),
    "b_radar": ("none: the official links point to the agency radar", "none: the official links point to the agency radar"),
    "b_flood_stages": ("none: flood stages are provincial, with no national open feed", "none: flood stages are set by the states; shipping marks are in official marks"),
    "b_low_water": ("none: no national low-water thresholds", "none: mean low water is in official marks"),
    "b_impacts": (NO_GAUGE, NO_GAUGE), "b_camera": ("none: no national gauge camera feed", "none: no national gauge camera feed"), "b_tides": ("none: test gauges are inland", "none: gauges on the list are inland"),
    "b_snotel": ("none: snow pillows are provincial", "none: no gauge-linked snow feed"), "b_floodfreq": (NO_GAUGE, NO_GAUGE), "b_crests": (NO_GAUGE, NO_GAUGE), "b_flood_outlook": ("none: provincial", "none: state flood centres, no national open feed"),
    "b_field_meas": (NO_GAUGE, NO_GAUGE), "b_rating": (NO_GAUGE, NO_GAUGE), "b_samples": (NO_GAUGE, NO_GAUGE), "b_attains": (US_ONLY, US_ONLY), "b_streamcat": (US_ONLY, US_ONLY), "b_land": (US_ONLY, US_ONLY),
    "b_heatmap": ("none: the feed has no hourly grid; the hourly table carries it", "none: covered by the hourly table"), "b_nwm": (US_ONLY, US_ONLY), "b_nwm_medium": (US_ONLY, US_ONLY), "b_noforecast": ("none: the river forecast tile says so", "none: the river forecast tile says so"),
    "b_recreation": (US_ONLY, US_ONLY), "b_stocking": (US_ONLY, US_ONLY), "b_dam": (US_ONLY, US_ONLY), "b_wpc": (US_ONLY, US_ONLY), "b_cpc": (US_ONLY, US_ONLY), "b_nws_point": (US_ONLY, US_ONLY)}
FROZEN = {"eccc": 5, "pegelonline": 33}  # gauge pages each country may list while it still has a next item; finishing them is what opens the queue


def cover_faults(blocks, pages, cover=None):
    """The guarantee: every US block is answered for every country, and a country with work left adds no gauges."""
    cover = COVER if cover is None else cover
    out = ["no country answer for US block %s" % b for b in blocks if b not in cover]
    for b, row in cover.items():
        out += ["%s: an answer must be have, next: or none: with its reason" % b for v in row if v != "have" and not (v[:6] in ("none: ", "next: ") and len(v) > 12)]
    for i, feed in enumerate(FEEDS if len(next(iter(cover.values()))) == len(FEEDS) else ()):
        left = [b for b, row in cover.items() if row[("eccc", "pegelonline").index(feed)].startswith("next")]
        n = sum(len(p.get("gauge_pages") or []) for p in pages if p.get("feed", "pegelonline") == feed)
        if left and n > FROZEN[feed]:
            out.append("%s lists %d gauges, more than %d, with %d blocks not wired: %s" % (feed, n, FROZEN[feed], len(left), ", ".join(left[:5])))
    return out


GATE = True
ALIKE = 0.75  # check.py fails a site over 0.80; held back at 0.75 here, so a gauge whose text drifts skips itself and never blocks a deploy


def shingles(h):
    """check.py's near-duplicate text: 5-word runs of the page body, numbers kept."""
    b = h.split("<main", 1)[1].split("</main>")[0] if "<main" in h else h
    w = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style|svg)\b.*?</\1>", " ", b))).lower().split()
    return {" ".join(w[i:i + 5]) for i in range(len(w) - 4)}


def alike(a, b):
    return bool(a and b) and len(a & b) / len(a | b) > ALIKE


TERMS = {"eccc": 'Terms: <a href="https://eccc-msc.github.io/open-data/licence/readme_en/">ECCC data</a>, <a href="https://open.canada.ca/en/open-government-licence-canada">Open Government Licence - Canada</a>.',
         "pegelonline": 'Terms: <a href="https://www.pegelonline.wsv.de/gast/nutzungsbedingungen">PEGELONLINE</a>, <a href="https://creativecommons.org/licenses/by/4.0/">DWD, CC BY 4.0</a>, <a href="https://www.govdata.de/dl-de/by-2-0">Umweltbundesamt, dl-de/by-2-0</a>.'}
GAPS = {}  # gauge -> blocks its data allows and its page lacks, live or held; build.py writes it to status.json and the watchdog alarms


def choose(pages, now):
    """Names per page that may publish: first pass over every gauge, a page too like one already kept waits. ponytail: all pairs, fine to about 3,000 world gauges; past that compare within a feed."""
    kept, names = [], {}
    for p, d in pages:
        names[p["slug"]] = set()
        order = p.get("gauge_pages") or []  # the list's order is priority: a famous gauge wins over a quiet one
        for r in sorted((x for x in d["rows"] if x["name"] in order), key=lambda x: order.index(x["name"])):
            broke = len(core.BLOCK_ERRORS)
            try:
                got = page(p, r, now, d["rows"])
            except Exception as e:
                print("world gauge skipped: %s %s" % (r.get("name"), str(e)[:100]))
                continue
            if not got:
                continue
            gone = missing(got[1], r) + core.BLOCK_ERRORS[broke:]  # a block that crashed is never a quiet gap
            if gone:
                GAPS[r["name"]] = gone
            live = os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist", world_gauge_url(p, r.get("title") or r["name"]).strip("/"), "index.html"))  # holds stop new gauges; an outage never pulls a page
            if gone and GATE and not live:
                print("world gauge held, page lacks what its data allows: %s %s" % (r["name"], ", ".join(gone)))
                continue
            s = shingles(got[1])
            if not live and any(alike(s, o) for o in kept):
                print("world gauge held, too like another page: %s" % r["name"])
                continue
            kept.append(s)
            names[p["slug"]].add(r["name"])
    return names


def along(p, r, rows, keep=()):
    """The two nearest gauges each way on this river, with their readings: what is coming down to a reader here. A flat list has no river order, so it shows the four closest within 100 km."""
    names = [x["name"] for x in rows]
    i = names.index(r["name"])
    out = []
    near = sorted((x for x in rows if x is not r and x.get("lat") is not None and x.get("cm") is not None and wx.km(r["lat"], r["lon"], x["lat"], x["lon"]) <= 100), key=lambda x: wx.km(r["lat"], r["lon"], x["lat"], x["lon"]))[:4] if p.get("flat") else rows[max(0, i - 2):i] + rows[i + 1:i + 3]
    for x in near:
        out.append(("Nearby" if p.get("flat") else "Upstream" if names.index(x["name"]) < i else "Downstream", x.get("title") or x["name"].replace(" UP", "").title(), fmt_level(x["cm"], x.get("unit", "cm")), fmt_level(x["cm"] - x["then"], x.get("unit", "cm")).replace("-", "-") if x.get("then") is not None else None, LABEL.get(x.get("state"), "Unknown"), world_gauge_url(p, x.get("title") or x["name"]) if x["name"] in keep else None))
    return out


def fc_top(f, now):
    """(time words, level) of the forecast's highest point, or None when there is none or it is past the US hide limit."""
    c = f.get("fc") or {}
    age = hours_old(c.get("at"), now) if c.get("at") else None
    pts = [p for p in c.get("pts") or [] if parse_t(p[0]) >= now]
    if not pts or age is None or age > HIDE_H["river_forecast"]:
        return None
    t, v, _ = max(pts, key=lambda p: p[1])
    return parse_t(t).astimezone(zoneinfo.ZoneInfo(f["zone"])).strftime("%b %-d, %-I %p" if os.name != "nt" else "%b %#d, %#I %p"), v


def fresh(w, key, t, bid):
    return bool(w.get(key)) and t is not None and (hours_old(t, datetime.datetime.now(datetime.timezone.utc)) or 0) <= HIDE_H[bid]


def owed(r):
    """Block ids this gauge's data entitles a reader to. Age counts: past the US hide limit a block is rightly gone, so an outage never pulls a page. A gauge the weather collect never reached owes it all."""
    w = r.get("wx")
    if not w or (not w.get("fetched_at") and not w.get("periods")):
        return ["weather not collected yet"]
    out = ["alerts", "official_links", "stage_chart"]
    if w.get("no_weather"):
        return out
    for key, t, bid in (("obs", (w.get("obs") or {}).get("timestamp"), "air_obs"), ("periods", w.get("forecast_updated"), "weather_forecast"), ("hourly", w.get("hourly_updated"), "hourly_forecast")):
        if fresh(w, key, t, bid):
            out.append(bid)
    if fresh(w, "aq", (w.get("aq") or {}).get("t"), "air_quality"):
        out.append("air_quality")
    if fc_top({"fc": r.get("fc"), "zone": "UTC"}, datetime.datetime.now(datetime.timezone.utc)):
        out.append("river_forecast")
    if any(k in (r.get("marks") or {}) for k, _ in MARKS) or r.get("months") or r.get("record"):
        out.append("official_marks")
    if r.get("also"):
        out.append("also_measured")
    if len(r.get("flow") or []) >= 8:
        out.append("flow_chart")
    if r.get("deciles"):
        out.append("world_history")
    if (r.get("access") or {}).get("rows"):
        out.append("access_points")
    if (r.get("normals") or {}).get("temp"):
        out.append("climate_normals")
    if r.get("drought_map") and (datetime.date.today() - datetime.date(2000 + int(r["drought_map"][:2]), int(r["drought_map"][2:]), 1)).days <= 105:
        out.append("drought_monitor")
    if r.get("wt30") and hours_old(r["wt30"]["last"], datetime.datetime.now(datetime.timezone.utc)) <= 72:
        out.append("water_temp_recent")
    g = w.get("rain_days") or {}
    if g.get("updated") and hours_old(g["updated"], datetime.datetime.now(datetime.timezone.utc)) <= HIDE_H["forecast_rain_totals"] and any(parse_t(d[0]) >= datetime.datetime.now(datetime.timezone.utc) for d in g.get("days", [])):
        out.append("forecast_rain_totals")
    return out


def missing(h, r):
    """What this page owes and does not show. Any entry holds a new gauge back; this is the rule that says a world page got everything its data allows."""
    return [b for b in owed(r) if 'id="%s"' % b not in h]


def page(p, r, now, rows=(), keep=()):
    """(url, html) for one gauge, or None when it fails the ship test."""
    if not ready(r):
        return None
    hold, odd = wx.suspect(r["series"], r.get("unit", "cm"), now)
    if hold:
        return None
    row, rec = to_row(p, r), to_rec(p, r)
    rec["feed"]["label_note"] = odd + rec["feed"]["label_note"]
    rec["feed"]["lake"] = p.get("lake")
    rec["feed"]["gaps"] = [w for w, have in (("rain total", (r.get("wx") or {}).get("rain")), ("water temperature", (r.get("also") or {}).get("WT")), ("river forecast", r.get("fc")), ("flow", r.get("flow"))) if not have]
    rec["feed"]["along"] = along(p, r, list(rows), keep) if rows else []
    rec["feed"]["also"] = r.get("also") or {}
    G = render.ctx(row["site"], row, rec, now)
    html, meta = render.build_tab("dashboard", G, {row["site"]: row})
    top = fc_top(rec["feed"], now)
    if top:
        html = re.sub(r'<div class="tile fcst none">.*?</small></div>', ui.tile("fcst", "crest", "River forecast", fmt_level(top[1], rec["feed"]["unit"]), "<small>Highest in the forecast, %s. Federal Institute of Hydrology</small>" % esc(top[0])), html, count=1, flags=re.S)
    html = html.replace("Height above the gauge's zero point, not water depth", "%.1f ft. %s" % (to_ft(r["cm"], rec["feed"]["unit"]), "On this gauge's own scale, often a height above sea level, not water depth" if rec["feed"]["src"] == "eccc" else "Height above the gauge's zero point, not water depth"), 1)
    return row["dashboard_url"], localize(html, rec["feed"], p["river"], row["place"], row["hub_url"], p.get("flat"))
