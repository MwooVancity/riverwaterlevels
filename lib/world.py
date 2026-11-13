"""Gauges outside the US on the US page: a feed row becomes the record lib/hero.py reads (stage only, no flow), the US builder makes the page, this file only swaps agency words.
One template, so every fix to the gauge page reaches these too. A new feed adds a FEEDS row and a fetch in collect.py."""
import inspect
import datetime, json, re
from lib import render
import os, zoneinfo
from lib import core, ui, wx
from lib import common
from lib.common import parse_t
from lib.core import HIDE_H, hours_old
from lib.directory import esc, world_gauge_url, world_slug

FEEDS = {"pegelonline": {"agency": "WSV", "name": "German Federal Waterways and Shipping Administration (WSV)", "api": "PEGELONLINE", "unit": "cm", "zone": "Europe/Berlin", "src": "pegelonline", "emergency": "Emergency in Germany: 112 fire and ambulance, 110 police.", "wx": "DWD", "wx_site": "dwd.de", "wx_credit": "Weather and alerts: Deutscher Wetterdienst (DWD), CC BY 4.0, shortened and converted."},
         "eccc": {"agency": "ECCC", "name": "Environment and Climate Change Canada", "api": "Water Survey of Canada", "unit": "m", "zone": "America/Toronto", "src": "eccc", "emergency": "Emergency in Canada: 911 where available.", "wx": "Environment Canada", "wx_site": "weather.gc.ca", "wx_credit": "Weather and alerts: Environment and Climate Change Canada."},
         # England: the alerts block carries the agency's own flood warnings and alerts, so its words say flood, never weather; the weather forecast is the Met Office's (page() names it)
         "ea": {"agency": "Environment Agency", "name": "Environment Agency (England)", "api": "Environment Agency real-time flood-monitoring API (Beta)", "unit": "m", "zone": "Europe/London", "hist_src": "ea-hydrology",
                "hist_line": "Source: Environment Agency Hydrology API, each day's lowest and highest level at this gauge (Good, Estimated and Unchecked days with complete data). Our calculation from those records; the year table ends before this year.", "src": "ea", "emergency": "Emergency in the UK: 999 or 112. Floodline: 0345 988 1188.",
                "wx": "Environment Agency", "wx_site": "GOV.UK Check for flooding", "wx_credit": "Flood warnings and alerts, and rain: Environment Agency. Weather forecast: Met Office Global Spot, Powered by Met Office data.",
                "flood_line": '<p class="gaps" data-flood><b>Flood warnings on this page are the Environment Agency\'s</b>, for warning areas that hold this gauge or lie within 150 m of it. Check <a href="https://check-for-flooding.service.gov.uk/alerts-and-warnings">all warnings in England on GOV.UK</a>.</p>',
                "swap": (("No active Environment Agency weather alerts were returned for this location. River flood warnings are issued locally and are not in this feed.", "No Environment Agency flood warning or flood alert is in force for an area that holds this gauge or lies within 150 m of it."),
                         ("No active Environment Agency weather alerts", "No flood warnings in force"), ("<h2>Weather alerts", "<h2>Flood warnings and alerts"), ("Link to Weather alerts", "Link to Flood warnings and alerts"), ("Environment Agency message valid until not stated", "No end time stated by the Environment Agency"),
                         ("<span>River forecast</span><b>Not issued</b><small>No river forecast is shown for this gauge.</small>", "<span>River forecast</span><b>Not shown</b><small>GOV.UK Check for flooding shows an agency forecast at some stations.</small>"),
                         ("Source: Environment Agency alerts for the gauge location", "Source: Environment Agency flood warnings and alerts in force, for warning areas that hold the gauge or lie within 150 m of it, from each area's map"))},
         # PLAN 7c: Irish harbour tide gauges; sea level, so the page says tide, never river
         "imi": {"agency": "Marine Institute", "name": "Marine Institute (Ireland), Irish National Tide Gauge Network", "api": "Marine Institute ERDDAP", "unit": "m", "zone": "Europe/Dublin", "src": "imi",
                 "emergency": "Emergency in Ireland: 112 or 999; at sea ask for the Coast Guard.", "wx": "Met Eireann", "wx_site": "met.ie", "wx_credit": "Weather warnings: see Met Eireann (met.ie).",
                 "swap": (("River flood warnings are not on this page.", "Weather warnings are not on this page yet."), ("Weather at the river", "Weather at the harbour"), (" water level today", " tide and sea level today"),
                          ("<span>Water level</span>", "<span>Sea level</span>"),
                          ("Below the gauge's zero point, a fixed reference level, not the riverbed", "Below Ordnance Datum Malin, Ireland's mean-sea-level reference; not depth"),
                          ("Above the gauge's zero point, a fixed reference level, not the riverbed", "Above Ordnance Datum Malin, Ireland's mean-sea-level reference; not depth"),
                          ("<span>River forecast</span><b>Not issued</b><small>No river forecast is shown for this gauge.</small>", "<span>Tide forecast</span><b>Not shown yet</b><small>Marine Institute predicted high and low tides are coming to this page.</small>"),
                          ("No official alert feed is connected for this gauge. Check local authorities.", "Met Eireann weather warnings are not on this page yet: check met.ie/warnings."))}}
LABEL = {"low": "Low", "normal": "Normal", "high": "High"}
MARKS = (("HHW", "Highest on record"), ("HREC", "Highest in recent years (agency: typically the last 5 years)"), ("TRH", "Top of normal range (Environment Agency)"), ("TRL", "Bottom of normal range (Environment Agency)"), ("HW", "Agency reference high (HW)"), ("HSW", "Highest level for shipping"), ("M_II", "High-water shipping mark II"), ("M_I", "High-water shipping mark I"), ("MHW", "Mean high water"),
         ("MW", "Average level"), ("MNW", "Mean low water"), ("GlW", "Equivalent low water (GlW)"), ("NW", "Agency reference low (NW)"), ("NNW", "Lowest on record"), ("MMAX", "Highest monthly mean for this month"), ("MAVG", "Average monthly mean for this month"), ("MMIN", "Lowest monthly mean for this month"))
ROW = {"name_confidence": "high", "nws_lid": "", "place_final": "", "raw_name": "", "score": "0", "wave": "", "years_record": "0", "drainage_sqmi": "0"}


def ready(r):
    """The ship test: a real recent reading with its time. The series draws the chart; marks are shown when the agency has them."""
    return not r.get("tidal") and r.get("cm") is not None and bool(r.get("time")) and r.get("lat") is not None and r.get("lon") is not None and len(r.get("series") or []) >= 8


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
    elif key == "ea":
        rng = r.get("range")
        label, marks = LABEL.get(r.get("state"), "Unknown"), r.get("marks") or {}
        note = ("Environment Agency label, against its normal range for this gauge, %s to %s: on record, the level is above %s about 95%% of the time and above %s about 5%% of the time." %(fmt_level(rng[0], "m"), fmt_level(rng[1], "m"), fmt_level(rng[0], "m"), fmt_level(rng[1], "m"))) if rng else "The Environment Agency publishes no normal range for this gauge."
    elif key == "imi":  # a tide gauge has no normal range: the sea rises and falls about twice a day (never a made-up label)
        label, note, marks = "Tidal", "Sea level at a harbour tide gauge, above Ordnance Datum Malin; it rises and falls with the tide about twice a day, so no normal range applies.", {}
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
    if key == "ea":
        links = ([("Official station page (Environment Agency, GOV.UK Check for flooding)", "https://check-for-flooding.service.gov.uk/station/%s" % r["rloi"])] if r.get("rloi") else []) + [
            ("Flood warnings and alerts in force in England (GOV.UK)", "https://check-for-flooding.service.gov.uk/alerts-and-warnings"), ("Sign up for free flood warnings by phone, text or email (GOV.UK)", "https://www.gov.uk/sign-up-for-flood-warnings")]
    elif key == "imi":
        links = [("Irish National Tide Gauge Network (Marine Institute)", "https://erddap.marine.ie/erddap/tabledap/IrishNationalTideGaugeNetwork.html"),  # the dataset page itself (the marine.ie overview URL 404ed 2026-11-09)
                 ("Weather warnings for Ireland (Met Eireann)", "https://www.met.ie/warnings")]
    else:
        links = [("Official gauge page (%s)" % f["agency"], "https://wateroffice.ec.gc.ca/report/real_time_e.html?stn=%s" % r["name"] if key == "eccc" else "https://www.pegelonline.wsv.de/gast/stammdaten?pegelnr=%s" % r.get("number"))] if key == "eccc" or r.get("number") else []
        links.append(("Weather warnings (%s)" % f["wx"], w.get("city_url") or ("https://weather.gc.ca/" if key == "eccc" else "https://dwd.de/warnungen")))
    return {"site": f["agency"] + "-" + world_slug(r["name"]), "lat": r["lat"], "lon": r["lon"], "tz": f["zone"], "usgs": {"fetched_at": r["time"], "rows": rows, "truncated": False}, "_fetched": {}, "access": r.get("access"), "nws": w, "rain": {} if key == "ea" else w.get("rain") or {},  # England's rain tile is drawn in mm by ea_rain_tile, never through inches
            "feed": dict(f, flood=FLOOD["abroad" if w.get("abroad") else key], emergency="Emergency: call the local emergency number." if w.get("abroad") else f["emergency"], label=label, label_note=note, norm=("Tidal: rises and falls about twice a day" if key == "imi" else "%s, %s" % (label, "our calculation" if key == "eccc" else "%s label" % f["agency"])), ship=r.get("ship"), marks=marks, mark_dates=r.get("mark_dates") or {}, station=r["name"], wt30=r.get("wt30"), normals=r.get("normals"), drought=r.get("drought"), drought_map=r.get("drought_map"), normals_by="Environment and Climate Change Canada" if key == "eccc" else "Deutscher Wetterdienst", normals_src="eccc" if key == "eccc" else "dwd", fc=r.get("fc"), flow=r.get("flow"), days=r.get("days"), deciles=r.get("deciles"), day_years=r.get("day_years"), years=r.get("years"), peaks=r.get("peaks"), aq=w.get("aq"), links=links, no_weather=w.get("no_weather"))}


def to_row(page, r):
    u = world_gauge_url(page, r.get("title") or r["name"])
    place = r.get("title") or r["name"].replace(" UP", "").title()
    return dict(ROW, site=FEEDS[page.get("feed", "pegelonline")]["agency"] + "-" + world_slug(r["name"]), river=page["river"], place=place, state="ZZ", river_slug=page["slug"], place_slug=world_slug(r.get("title") or r["name"]), dashboard_url=u, water_url=u, forecast_url=u + "forecast/",
                hub_url="/%s/" % page["slug"], hub_slug=page["slug"], _built=True, _hub=False, _single=True, _ll=(r["lat"], r["lon"]), _lv=None, _band="–")


def world_ld(page, r, url, feed, html):
    """WebPage, Place and Dataset markup for a world gauge page, as a US gauge page carries (audit 2026-11-10 #25, owner decision 2: one standard page).
    localize() drops the US block (it names USGS as creator); this one names the agency. The name is the page's own <title>, so the two never disagree."""
    from html import unescape
    from lib.directory import COUNTRY
    t = re.search(r"<title>([^<]*)</title>", html)
    where = "%s, %s" % (feed["head"], COUNTRY.get(page.get("feed"), "Germany"))
    j = {"@context": "https://schema.org", "@type": "WebPage", "name": unescape(t.group(1)) if t else where, "url": common.SITE_URL + url, "dateModified": r["time"],
         "isPartOf": {"@type": "WebSite", "name": common.BRAND, "url": common.SITE_URL, "publisher": {"@type": "Organization", "name": common.BRAND, "url": common.SITE_URL}},
         "about": {"@type": "Place", "name": where, "geo": {"@type": "GeoCoordinates", "latitude": round(r["lat"], 4), "longitude": round(r["lon"], 4)}},
         "mainEntity": {"@type": "Dataset", "name": "%s gauge %s, %s: water level" % (feed["agency"], feed["station"], where), "url": common.SITE_URL + url,
                        "description": "Recent water level readings at %s gauge %s (%s); the agency can revise them." % (feed["agency"], feed["station"], feed["api"]),
                        "creator": {"@type": "Organization", "name": feed["name"]}, "temporalCoverage": r["time"]}}
    return '<script type="application/ld+json">%s</script>' % json.dumps(j, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")


SWAP = (("No active NWS alerts", "No active @WX@ weather alerts"), ("No active National Weather Service alerts were returned for this location.", "No active @WX@ weather alerts were returned for this location. River flood warnings are issued locally and are not in this feed."), ("The newest USGS flow reading", "The newest reading"), ("when USGS publishes", "when the agency publishes"), ("Latest USGS gage height", "Latest water level"), ("Solid line: USGS readings.", "Solid line: official readings."), ("NWS alerts unknown", "Official alerts unknown"), ("NWS alerts", "Official alerts"),
        ("Gage height", "Water level"), ("gage height", "water level"), ("The National Weather Service has no river forecast point for this gauge. The weather forecast below is not a river forecast.", "No river forecast is shown for this gauge."),
        ("We have no answer from the National Weather Service alert service for this location. Check weather.gov.", "No official alert feed is connected for this gauge. Check local authorities."),
        ('<span>River forecast</span><b>Not linked</b>', '<span>River forecast</span><b>Not issued</b>'), ("Data: USGS, NOAA, NWS.", "Data: official agencies, listed on each page."), ("within about 15 miles of the gauge", "within about 25 km of the gauge"), (' <a href="#gauge_map">Map of the gauge location</a>', ""))
LIVE = """<script>(function(){var w=document.querySelector('.hero'),a=document.querySelector('[data-live=age]');if(!w||!a)return;var m=Math.round((Date.now()-Date.parse(w.dataset.t))/60000);a.textContent=m<180?m+' min':m<2880?Math.round(m/60)+' h':Math.round(m/1440)+' d'})();</script>"""  # the age only: a swapped level beside the build's feet, change and label mixed two times on one page (review 2026-11-04); world pages rebuild every hour


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
    h = h.replace("National Weather Service", feed["wx"]).replace("USGS sensor", "%s sensor" % feed["agency"]).replace("check weather.gov", "check " + feed["wx_site"]).replace("NWS estimate for this spot", "Station rain total")
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
    later = '<p class="gaps">Not on this page yet: %s.</p>' % ", ".join(feed["later"]) if feed.get("later") else ""
    h = h.replace('<section data-g="now"', (feed.get("flood_line") or '<p class="gaps" data-flood><b>River flood warnings are not on this page.</b> Check the %s.</p>' % feed["flood"]) + ("" if 'id="official_links"' in h else later) + '<section data-g="now"', 1)
    h = re.sub(r'(<section[^>]*id="official_links")', lambda m: later + m.group(1), h, count=1)  # the to-do list sits after the data, by the agency links, never above the reading
    h = re.sub(r'<script>\(function\(\)\{var ID="USGS-.*?</script>', lambda m: LIVE, h, flags=re.S)
    h = re.sub(r"(\d) (cm|m) \((-?[\d.,]+) ft\)", "\\1\u00a0\\2 (\\3\u00a0ft)", h)  # a level and its feet never break apart on a phone, "260 cm (2.5 / ft)" (UI review 2026-11-04)
    for a, b in feed.get("swap") or ():  # last: the country's own words over the general ones
        h = h.replace(a, b)
    return h


PROOFS = ("reading", "time", "alerts", "unit", "terms", "water")
PROVED = {  # what a person or script saw on live data, one line each; a country with a gap fails check.py before any of its pages ship. An alert proof means a real live alert reached the code, not an empty list
    "pegelonline": {"reading": "tools/truth_world.py 0 faults 2026-11-02", "time": "Kaub page 3:00 AM CET against feed timestamp +01:00, 2026-11-02", "alerts": "Kaub frost warning from the DWD zip reached the point test, Zurich none, 2026-11-02", "unit": "cm above gauge zero, PEGELONLINE", "terms": "DL-DE-Zero-2.0; DWD CC BY 4.0, read 2026-11-02", "water": "inland rivers and Lake Constance, no tidal gauge listed"},
    "ea": {"reading": "Colwick 1.049, Kingston 4.421, Ross-on-Wye 0.41 m built pages = API latest = GOV.UK station pages within one reading, 2026-11-03", "time": "API 02:45Z shown 2:45 AM GMT; BST and both 2026 clock changes rendered right by zoneinfo Europe/London",
           "alerts": "", "unit": "metres above the stage datum (mASD), the gauge's own zero, as GOV.UK shows it", "terms": "OGL v3.0 and the agency's attribution, API reference and licence read 2026-11-03",
           "water": "rivers only: Gainsborough held by the tide test on its readings, Keadby by its tidal measure, live 2026-11-03"},  # alerts stays empty here: collect.py ea_probe records it when a real level 1 to 3 warning holds an English station (proved() reads it); until then England pages say Unknown (UNKNOWN_UNTIL_PROVEN), never none
    "imi": {"reading": "ERDDAP IrishNationalTideGaugeNetwork read 2026-11-09: 22 stations, Dublin Port -0.409 m OD Malin at 03:10Z (collect.py fetch_imi_live)", "time": "feed times in UTC (units row 'UTC'); pages show Europe/Dublin (GMT in winter, IST in summer) through zoneinfo",
            "alerts": "", "unit": "metres above Ordnance Datum Malin (the units row says metres; the column names the datum)", "terms": "CC BY 4.0 from the dataset's own licence attribute, read 2026-11-09",
            "water": "sea level at harbour tide gauges: these pages are tide pages, never shown as a river"},
    "eccc": {"reading": "tools/truth_world.py 0 faults 2026-11-02", "time": "Squamish 02:05Z feed against page; BC is permanent UTC-7 since 2026 (IANA 2026b), shown as PT", "alerts": "real fog advisory at Berens River hit the point test 2026-11-02; status words are issued and continued", "unit": "metres; Ottawa on a survey datum, not gauge zero", "terms": "open licence, read 2026-11-01", "water": "inland rivers; test gauges not tidal"}}


UNKNOWN_UNTIL_PROVEN = ("ea", "imi")  # owner 2026-11-03: England ships before a live warning proves the point test; until then its alert block says Unknown with the GOV.UK link (page below), never none


def proof_faults(feeds, proved):
    return ["%s has no proof of %s" % (f, k) for f in feeds for k in PROOFS if len((proved.get(f) or {}).get(k) or "") < 10 and not (k == "alerts" and f in UNKNOWN_UNTIL_PROVEN)]


def alerts_proven(p):
    """True once a real live alert reached this feed's point test (PROVED, collect.py ea_probe, or the proof committed with the first gauge)."""
    return len((proved([p]).get(p.get("feed", "pegelonline")) or {}).get("alerts") or "") >= 10


def recorded(pages):
    """Alert proofs a run saw on live data (collect.py ea_probe: cache/_ea-proof.json, published as /_proofs.json), or carried into data/world-pages.json by the release that listed
    the country's first gauge, so a lost cache never relocks a country with live pages."""
    out = {}
    try:
        out.update({k: v for k, v in json.load(open(os.path.join(common.CACHE, "_ea-proof.json"), encoding="utf-8")).items() if isinstance(v, dict)})
    except (OSError, ValueError, AttributeError):
        pass
    for p in pages:
        if isinstance(p.get("proof"), dict):
            out[p.get("feed", "pegelonline")] = p["proof"]
    return out


def proved(pages):
    """PROVED, with each alert proof a run recorded: what the release, the matcher and check.py read."""
    rec = recorded(pages)
    return {f: dict(v, alerts=v.get("alerts") or (rec.get(f) or {}).get("alerts") or "") for f, v in PROVED.items()}


US_ONLY = "none: US federal product, no counterpart in this country's open feeds"
NOT_CHECKED = "next: an English counterpart was not checked (2026-11-03)"
NO_GAUGE = "none: the agency publishes no such record for its gauges"
MAP = "none: no open map we may embed was read; the coordinates in About this gauge open OpenStreetMap at the gauge, and the official links open the agency map"
HYDAT = "next: Water Office flow statistics (HYDAT daily flows, same API); not wired"
COVER = {  # every block on a US gauge page, per country (eccc, pegelonline). have = on the page; none = no official source, with the reason; next = a source exists and is not wired: a to-do the page's gaps line names (TODO), never a cap
    "b_offline": ("have", "have"),
    "b_flow_behind": ("none: the headline is water level, and the flow chart carries its own reading times", "none: the headline is water level, and the flow chart carries its own reading times"),
    "b_alerts": ("have", "have"), "b_stage_chart": ("have", "have"), "b_official_marks": ("have", "have"),
    "b_hourly": ("have", "have"), "b_weather": ("have", "have"), "b_air": ("have", "have"), "b_air_quality": ("have", "have"), "b_official_links": ("have", "have"),
    "b_flow_chart": ("have", "have"),
    "b_rate": ("have", "have"),
    "b_rain": ("none: city pages carry no rain total; the SWOB record at Ottawa airport carried none on 2026-11-02", "have"),
    "b_river_forecast": ("none: river forecasts are provincial in Canada, with no national open feed", "have"),
    "b_quality": ("none: the Water Office real-time feed publishes level and flow only", "have"),
    "b_wtemp": ("none: the Water Office real-time feed publishes level and flow only", "have"),
    "b_qpf": ("none: city forecast text carries rain chance, no totals", "have"),
    "b_acis": ("have", "have"),
    "b_month_chart": ("none: the history table carries this date against every year", "none: PEGELONLINE keeps 30 days and no history"),
    "b_year_chart": ("none: the history table lists each recent year", "none: PEGELONLINE keeps 30 days and no history"),
    "b_multiyear": ("have", "none: PEGELONLINE keeps 30 days and no history"),
    "b_floods": (HYDAT, "none: PEGELONLINE keeps 30 days and no history"),
    "b_speed": ("none: the Water Office publishes no channel velocity measurements", "none: PEGELONLINE publishes no channel velocity measurements"),
    "b_like_today": (HYDAT, "none: PEGELONLINE keeps 30 days and no history"),
    "b_sustained": ("none: US block reads flow percentiles, which Canada does not publish", "none: PEGELONLINE keeps 30 days and no history"),
    "b_record": ("have", "none: record marks are shown in official marks"),
    "b_flowdur": (HYDAT, "none: PEGELONLINE keeps 30 days and no history"),
    "b_peaks": ("have", "none: PEGELONLINE publishes marks, not annual peaks"),
    "b_stage_years": ("have", "none: PEGELONLINE publishes marks, not yearly values"),
    "b_daily": ("none: published daily means end over a year back; the chart and our archive cover recent days", "none: PEGELONLINE keeps 30 days and no history"),
    "b_drought": ("have", "none: DWD publishes crop soil moisture and a climate index, no drought class for a place"),
    "b_access": ("have", "have"),
    "b_related": ("none: stations in the feed carry no upstream or downstream order", "have"), "b_nearby": ("have", "have"),
    "b_about": ("have", "have"),
    "b_key_facts": ("have", "have"),
    "b_reservoir": ("none: shown for US reservoirs with a state or operator capacity basis; no Canadian lake feed in use publishes one", "none: PEGELONLINE publishes levels, not reservoir storage"),
    "b_waves": ("none: coast pages only; these are river and lake gauges", "none: coast pages only; these are river and lake gauges"),
    "b_moon": ("none: coast pages only; these are river and lake gauges", "none: coast pages only; these are river and lake gauges"),
    "b_kingtide": ("none: coast pages only; these are river and lake gauges", "none: coast pages only; these are river and lake gauges"),
    "b_surf": ("none: coast pages only; these are river and lake gauges", "none: coast pages only; these are river and lake gauges"),
    "b_lake_temp": ("none: Great Lakes pages only (NOAA GLERL lake-wide average); Canadian pages here are river gauges", "none: Great Lakes pages only; these are German rivers and Lake Constance, which GLERL does not cover"),
    "b_map": (MAP, MAP),
    "b_radar": ("none: the official links point to the agency radar", "none: the official links point to the agency radar"),
    "b_flood_stages": ("none: flood stages are provincial, with no national open feed", "none: flood stages are set by the states; shipping marks are in official marks"),
    "b_low_water": ("none: no national low-water thresholds", "none: mean low water is in official marks"),
    "b_impacts": (NO_GAUGE, NO_GAUGE), "b_camera": ("none: no national gauge camera feed", "none: no national gauge camera feed"), "b_tides": ("none: test gauges are inland", "none: gauges on the list are inland"),
    "b_snotel": ("none: snow pillows are provincial", "none: no gauge-linked snow feed"), "b_floodfreq": (NO_GAUGE, NO_GAUGE), "b_crests": (NO_GAUGE, NO_GAUGE), "b_flood_outlook": ("none: provincial", "none: state flood centres, no national open feed"),
    "b_depth": ("none: no open channel-measurement feed known (not yet searched, 2026-11-09)", "none: no open channel-measurement feed known (not yet searched, 2026-11-09)"), "b_field_meas": (NO_GAUGE, NO_GAUGE), "b_rating": (NO_GAUGE, NO_GAUGE), "b_samples": (NO_GAUGE, NO_GAUGE), "b_attains": (US_ONLY, US_ONLY), "b_streamcat": (US_ONLY, US_ONLY), "b_land": (US_ONLY, US_ONLY),
    "b_heatmap": ("none: the feed has no hourly grid; the hourly table carries it", "none: covered by the hourly table"), "b_nwm": (US_ONLY, US_ONLY), "b_nwm_medium": (US_ONLY, US_ONLY), "b_noforecast": ("none: the river forecast tile says so", "none: the river forecast tile says so"),
    "b_recreation": (US_ONLY, US_ONLY), "b_limits": (NOT_CHECKED, NOT_CHECKED), "b_stocking": (US_ONLY, US_ONLY), "b_dam": (US_ONLY, US_ONLY), "b_dam_facts": (US_ONLY, US_ONLY), "b_wpc": (US_ONLY, US_ONLY), "b_cpc": (US_ONLY, US_ONLY), "b_nws_point": (US_ONLY, US_ONLY)}
MET = "next: Met Office Global Spot rain amounts and map images, same key; fields not proven live"
MET_OBS = "next: Met Office Land Observations, a separate free DataHub plan (owner sign-up)"
NRFA = "next: UK National River Flow Archive (UKCEH) station statistics; terms not read"
IMPACT = "next: GOV.UK Check for flooding lists impact levels per station (Colwick: property flooding possible above 4.30 m, read 2026-11-03); no open feed read"
ENGLAND = {  # read on the live API and its reference 2026-11-03; each none says what was read
    "b_offline": "have", "b_key_facts": "have", "b_reservoir": "none: the EA publishes levels, not reservoir storage", "b_waves": "none: coast pages only; these are river gauges", "b_moon": "none: coast pages only; these are river gauges", "b_kingtide": "none: coast pages only; these are river gauges", "b_surf": "none: coast pages only; these are river gauges", "b_lake_temp": "none: Great Lakes pages only; these are English river gauges", "b_flow_behind": COVER["b_flow_behind"][0], "b_alerts": "have", "b_stage_chart": "have", "b_official_marks": "have", "b_official_links": "have", "b_flow_chart": "have", "b_access": "have", "b_nearby": "have", "b_about": "have",
    "b_hourly": "have", "b_weather": "have", "b_air": MET_OBS, "b_qpf": MET, "b_radar": MET, "b_heatmap": "none: covered by the hourly table",  # Met Office Global Spot, wired 2026-11-03; sky words wait for the code table
    "b_air_quality": "next: Defra UK-AIR hourly air quality index, open data; terms not read",
    "b_rate": "have",
    "b_rain": "have",  # the rain tile: 24 h total of the nearest EA rain gauge within 15 km (collect.py ea_rain, lib/world.py ea_rain_tile)
    "b_river_forecast": "next: GOV.UK Check for flooding shows an agency model forecast at some stations (Colwick 2026-11-03); no open feed read",
    "b_quality": "none: the flood-monitoring API measures level, flow, rainfall, temperature, wind and velocity only, all 7,439 measures read 2026-11-03",
    "b_wtemp": "next: water temperature at 2 of 7,439 measures in the same API, read 2026-11-03; not wired",
    "b_acis": "next: Met Office 1991-2020 climate averages per station; terms not read",
    "b_month_chart": "none: the history table carries this date against every year", "b_year_chart": "none: the history table lists each recent year", "b_multiyear": "have", "b_like_today": "next: the Environment Agency daily means after today's date in earlier years; not wired", "b_speed": "none: the Environment Agency publishes no channel velocity measurements", "b_floods": "next: the Environment Agency daily means around its annual peaks; not wired",
    "b_daily": "none: the Hydrology API publishes each day's lowest and highest level, carried by the history table; no daily mean", "b_sustained": NRFA, "b_flowdur": NRFA, "b_peaks": NRFA, "b_stage_years": NRFA, "b_floodfreq": NRFA,
    "b_record": "none: the agency's highest and lowest on record, with dates, are in official marks",
    "b_drought": "next: Environment Agency drought status by area, in monthly water situation reports; no point dataset read",
    "b_related": "none: station records carry no upstream or downstream order, read 2026-11-03",
    "b_map": COVER["b_map"][0], "b_flood_stages": IMPACT, "b_impacts": IMPACT,
    "b_low_water": "none: the agency publishes no low-water threshold; the bottom of its normal range is in official marks",
    "b_camera": "none: the agency's open API reference lists no camera, read 2026-11-03", "b_snotel": "none: the agency's 7,439 measures include no snow, read 2026-11-03",
    "b_tides": "none: tidal gauges are kept off the site; a tide is never shown as a river level",
    "b_crests": "none: the agency's highest on record and highest recent level are in official marks",
    "b_flood_outlook": "next: Flood Forecasting Centre five-day flood risk on GOV.UK; no open feed read",
    "b_depth": "none: the flood-monitoring API reference lists no field measurements, read 2026-11-03", "b_field_meas": "none: the flood-monitoring API reference lists no field measurements, read 2026-11-03", "b_rating": "none: the flood-monitoring API reference lists no rating curves, read 2026-11-03",
    "b_samples": "next: Environment Agency Water Quality Archive sampling points, open; not read", "b_attains": "next: Environment Agency Catchment Data Explorer water body status, open; not read",
    "b_land": "next: UKCEH Land Cover Map; licence not read", "b_noforecast": COVER["b_noforecast"][0],
    "b_streamcat": NOT_CHECKED, "b_nwm": NOT_CHECKED, "b_nwm_medium": NOT_CHECKED, "b_recreation": NOT_CHECKED, "b_limits": NOT_CHECKED, "b_stocking": NOT_CHECKED, "b_dam": NOT_CHECKED, "b_dam_facts": US_ONLY, "b_wpc": NOT_CHECKED, "b_cpc": NOT_CHECKED, "b_nws_point": NOT_CHECKED}
COVER = {b: row + (ENGLAND[b],) for b, row in COVER.items()}  # a block missing from ENGLAND fails here, at import
IMI_NONE = "none: the Marine Institute tide gauge network publishes sea level only (read 2026-11-09)"
MET_IE = "next: Met Eireann open data (CC BY 4.0, read 2026-11-09); not wired"
IRELAND = dict({b: IMI_NONE for b in COVER}, **{  # PLAN 7c, Irish live tide gauges (Marine Institute ERDDAP, CC BY 4.0); each have/none read 2026-11-09
    "b_offline": "have", "b_stage_chart": "have", "b_official_links": "have", "b_rate": "have", "b_about": "have", "b_key_facts": "have", "b_nearby": "have", "b_access": "none: no Irish open access-point feed read",
    "b_alerts": "next: Met Eireann warnings JSON (warning_IRELAND.json) read 2026-11-09 with no warning in force; shown Unknown with the met.ie link until a real warning is parsed",
    "b_hourly": MET_IE, "b_weather": MET_IE, "b_air": MET_IE, "b_qpf": MET_IE, "b_rain": MET_IE, "b_acis": MET_IE, "b_radar": MET_IE, "b_heatmap": "none: covered by the hourly table",
    "b_air_quality": "next: EPA Ireland air quality index; terms not read",
    "b_tides": "have",  # the next three Marine Institute highs and lows, in the forecast tile (page(); 2026-11-09)
    "b_official_marks": "none: the network publishes no station marks; heights are above OD Malin",
    "b_flow_behind": COVER["b_flow_behind"][0], "b_map": COVER["b_map"][0], "b_noforecast": COVER["b_noforecast"][0],
    "b_attains": US_ONLY, "b_streamcat": US_ONLY, "b_land": US_ONLY, "b_nwm": US_ONLY, "b_nwm_medium": US_ONLY, "b_recreation": US_ONLY, "b_limits": NOT_CHECKED, "b_stocking": US_ONLY, "b_dam": US_ONLY, "b_dam_facts": US_ONLY, "b_wpc": US_ONLY, "b_cpc": US_ONLY, "b_nws_point": US_ONLY,
    "b_moon": "next: USNO moon phase works anywhere; not wired for world pages", "b_waves": "next: Marine Institute Irish weather buoy network (M2-M6); not read"})
COVER = {b: row + (IRELAND[b],) for b, row in COVER.items()}
ORDER = ("eccc", "pegelonline", "ea", "imi")  # the column order of COVER
TODO_IE = {MET_IE: "weather, rain and forecasts (Met Eireann)", IRELAND["b_alerts"]: "weather warnings (Met Eireann; see met.ie until one is proven here)",
           IRELAND["b_air_quality"]: "air quality (EPA Ireland)",            IRELAND["b_moon"]: "moon phase", IRELAND["b_waves"]: "offshore waves (Marine Institute weather buoys)"}
TODO = {HYDAT: "flow statistics (Water Survey of Canada archive)", ENGLAND["b_like_today"]: "what happened next in earlier years (Environment Agency daily flows)", ENGLAND["b_floods"]: "the biggest floods day by day (Environment Agency daily flows)",
        MET: "rain forecast totals and radar (Met Office)", MET_OBS: "air observations (Met Office)",
        ENGLAND["b_acis"]: "climate averages (Met Office)", ENGLAND["b_air_quality"]: "air quality (Defra UK-AIR)",
        ENGLAND["b_river_forecast"]: "river forecast (GOV.UK Check for flooding shows one at some stations)", ENGLAND["b_wtemp"]: "water temperature (the agency measures it at a few gauges)",
        NRFA: "flow statistics and yearly peaks (UK National River Flow Archive)", IMPACT: "flood impact levels (GOV.UK Check for flooding lists them per station)",
        ENGLAND["b_drought"]: "drought status (Environment Agency)", ENGLAND["b_flood_outlook"]: "five-day flood risk (Flood Forecasting Centre)", ENGLAND["b_samples"]: "water quality samples (Environment Agency)",
        ENGLAND["b_attains"]: "water body status (Environment Agency Catchment Data Explorer)", ENGLAND["b_land"]: "land cover (UKCEH)", NOT_CHECKED: "fish stocking, dam releases, recreation sites and long-range outlooks (English sources not yet checked)"}
TODO.update(TODO_IE)


FC_NONE = re.compile(r'<div class="tile fcst none[^"]*">.*?</small></div>', re.S)  # the 'Not issued' tile a world forecast replaces; ui.tile may add classes (na)
SHOWN_AS = {"b_acis": "climate_normals", "b_multiyear": "world_history", "b_stage_years": "world_history", "b_quality": "also_measured", "b_wtemp": "water_temp_recent", "b_related": "along_river", "b_record": "official_marks", "b_rain": 'class="tile rain', "b_tides": 'class="tile fcst"'}  # the world block that answers the US block's question, reviewed once 2026-11-04
ONLY_WHEN = {"b_offline": "shows only while the gauge is not reporting"}  # a have that is a state, not a block a page always owes


def marker(b, ids):
    """What a page carries when it shows US block b: its own section id (read from the b_ function by check.py) or the world block that answers it."""
    m = SHOWN_AS.get(b) or ids[b]
    return m if m.startswith("class=") else 'id="%s"' % m


def promise_faults(ids):
    """The forcing guard (owner 2026-11-04): every have in COVER must be a block owed() demands, so missing() holds or names any page without it. A have nothing enforces is how about_gauge read have while 0 of 37 pages showed it."""
    src = inspect.getsource(owed)
    out = []
    for b, row in COVER.items():
        for feed, v in zip(ORDER, row):
            m = marker(b, ids)
            if v == "have" and b not in ONLY_WHEN and (m if m.startswith("class=") else '"%s"' % m[4:-1]) not in src:
                out.append("%s %s: COVER says have and owed() never demands %s, so no page is held or named without it" % (feed, b, marker(b, ids)))
    return out


def todo(feed):
    """What a country's pages lack and an open source could fill: each COVER next item in reader words, once. The page's gaps line names them; they never stop a gauge (owner 2026-11-03)."""
    col = ORDER.index(feed)
    return list(dict.fromkeys(TODO[row[col]] for row in COVER.values() if row[col].startswith("next")))


def cover_faults(blocks, pages, cover=None):
    """The guarantee: every US block is answered for every country, and every next item has the reader words the gaps line prints. A shorter row in a test table covers the first countries of ORDER."""
    cover = COVER if cover is None else cover
    out = ["no country answer for US block %s" % b for b in blocks if b not in cover]
    for b, row in cover.items():
        out += ["%s: an answer must be have, next: or none: with its reason" % b for v in row if v != "have" and not (v[:6] in ("none: ", "next: ") and len(v) > 12)]
        out += ["%s: a next item with no reader words in TODO, so the gaps line could not name it" % b for v in row if v.startswith("next: ") and v not in TODO]
    return out


def listing(pages):
    """Feeds with at least one gauge page: only these must hold every proof, so a country being built can never fail a gate."""
    return sorted({p.get("feed", "pegelonline") for p in pages if p.get("gauge_pages")})


def live_thin():
    """The gauges the live build held as thin (status.json world.thin), or None when the site does not answer: then no world gauge is added this run."""
    import urllib.request
    try:
        s = json.load(urllib.request.urlopen(urllib.request.Request("https://riverwaterlevels.com/status.json", headers={"User-Agent": "riverwaterlevels.com"}), timeout=30))
        return (s.get("world") or {}).get("thin") or {}
    except Exception as e:
        print("live status.json unread, no world gauge added:", str(e)[:80])
        return None


def room(feed, pages, thin=None):
    """Gauges the release and the matcher may still add for a feed: none while a proof is missing; none while every gauge the feed lists was held as thin
    (status.json world.thin), so a country whose pages cannot reach the floor spends one daily slot, not 25 a day; none when that list could not be read (thin None)."""
    if proof_faults([feed], proved(pages)) or thin is None:
        return 0
    have = [n for p in pages if p.get("feed", "pegelonline") == feed for n in p.get("gauge_pages") or []]
    if not have:  # a country with no page yet opens 2 a day, so its first pages are read live before the rest follow (review 2026-11-04)
        return 2
    return 0 if all(n in thin for n in have) else 10 ** 6


DROP_DAYS = 7


def drop_held(pages, thin, today):
    """A gauge held since its first build never shipped and kept a slot under WORLD_MAX forever (PLAN 2026-11-04). The daily release dates each hold
    in the page row ("held"); after DROP_DAYS it leaves gauge_pages and stations with its reason in "dropped", which the matcher and release never re-add.
    A live page is never held (choose), so this only ever removes gauges no reader has seen. thin None (status unread) changes nothing."""
    out = []
    if thin is None:
        return out
    for p in pages:
        held = p.get("held") or {}
        for s in list(p.get("gauge_pages") or []):
            if s not in thin:
                held.pop(s, None)
                continue
            since = held.setdefault(s, today)
            if (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(since)).days >= DROP_DAYS:
                for k in ("stations", "gauge_pages"):
                    if s in (p.get(k) or []):
                        p[k].remove(s)
                p.setdefault("dropped", {})[s] = "held %s to %s: %s" % (since, today, "; ".join(thin[s])[:160])
                held.pop(s)
                out.append(s)
        if held:
            p["held"] = held
        else:
            p.pop("held", None)
    return out


GATE = True


FLOOD = {"eccc": '<a href="https://www.canada.ca/en/environment-climate-change/services/water-overview/quantity/floods/forecasting-centres.html">provincial flood forecasting centres</a>', "pegelonline": '<a href="https://www.hochwasserzentralen.de/">German state flood portal</a>',
         "ea": '<a href="https://check-for-flooding.service.gov.uk/alerts-and-warnings">Environment Agency flood warnings on GOV.UK</a>', "abroad": "local flood authority",
         "imi": '<a href="https://www.met.ie/warnings">Met Eireann weather warnings</a> and <a href="https://www.floodinfo.ie/">floodinfo.ie</a>'}
TERMS = {"eccc": 'Terms: <a href="https://eccc-msc.github.io/open-data/licence/readme_en/">ECCC data</a>, <a href="https://open.canada.ca/en/open-government-licence-canada">Open Government Licence - Canada</a>.',
         "pegelonline": 'Terms: <a href="https://www.pegelonline.wsv.de/gast/nutzungsbedingungen">PEGELONLINE</a>, <a href="https://creativecommons.org/licenses/by/4.0/">DWD, CC BY 4.0</a>, <a href="https://www.govdata.de/dl-de/by-2-0">Umweltbundesamt, dl-de/by-2-0</a>.',
         "ea": 'This uses Environment Agency flood and river level data from the real-time data API (Beta). This uses Environment Agency rainfall data from the real-time data API (Beta). Terms: <a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/">Open Government Licence v3.0</a>.',
         "imi": 'Tide data: Marine Institute, Irish National Tide Gauge Network. Terms: <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.'}
EA_LINK = '<a href="https://check-for-flooding.service.gov.uk/alerts-and-warnings">flood warnings and alerts in force in England on GOV.UK</a>'
EA_UNPROVEN_LINE = '<p class="gaps" data-flood><b>Flood warnings: Unknown on this page.</b> See %s.</p>' % EA_LINK  # the why is in the alerts block; four long Unknowns above the data read unfinished (UI review 2026-11-04)
EA_UNPROVEN = (("<p>Alerts could not be loaded at the last fetch.</p>", "<p>Unknown. This page does not show Environment Agency flood warnings yet: our check of warning areas against this gauge has not been seen working on a real warning. See %s. This is not a statement that conditions are safe.</p>" % EA_LINK),
               ("Source: Environment Agency alerts for the gauge location, fetched time not stated.", "Source: not read onto this page yet; the Environment Agency publishes warnings on GOV.UK Check for flooding."),
               ("No official alert feed is connected for this gauge. Check local authorities.", "Not shown here yet. See %s." % EA_LINK))


def ea_rain_tile(g, now, zone):
    """Rain, last 24 h, from the nearest Environment Agency rain gauge (collect.py ea_rain): its own total in mm, its station, distance and end time.
    Four states: a total (0.0 mm is a measured total), Unknown and old past 6 h, Unknown with the reason when no station near reported every period, Unknown when never collected."""
    z = zoneinfo.ZoneInfo(zone)
    if not g or not g.get("station"):
        return ui.tile("rain stale", "drop", "Rain, last 24 h", "Unknown", "<small>%s.</small>" % esc((g or {}).get("why") or "No Environment Agency rain gauge read for this gauge yet"))
    where = "Environment Agency rain gauge %s, %.1f km away" % (esc(g["station"]), g["km"])
    if g.get("mm") is None:
        return ui.tile("rain stale", "drop", "Rain, last 24 h", "Unknown", "<small>%s: %s.</small>" % (where, esc(g.get("why") or "no complete 24 h total")))
    age = hours_old(g["to"], now)
    to = esc(core.tzl(parse_t(g["to"]), z))
    if age is None or age > core.stale_after("rain_totals"):
        return ui.tile("rain stale", "drop", "Rain, last 24 h", "Unknown", '<small>Last total %s ago.</small><small class="old">Old value: %.1f mm, %s, to %s</small>' % (esc(core.age_words(parse_t(g["to"]), now)), g["mm"], where, to))
    return ui.tile("rain", "drop", "Rain, last 24 h", "%.1f <small>mm</small>" % g["mm"], '<small data-h="%.1f">%s, 24 h to %s</small>' % (age, where, to))


GAPS = {}  # gauge -> blocks its data allows and its page lacks, live or held; build.py writes it to status.json and the watchdog alarms
THIN = {}  # gauge -> why its new page is under the floor (thin); build.py writes it to status.json world.thin, the watchdog names the count, release.py reads it back


META = ("official_links", "about_gauge", "gauge_map", "offline")  # links and page facts, not a reading a reader can use
HISTORY = ("world_history", "official_marks", "record_comparison", "flow_duration", "sustained_flow", "month_chart", "year_chart", "multiyear", "daily_readings", "annual_peaks")
WEATHER = ("hourly_forecast", "weather_forecast", "air_obs", "rain_totals", "forecast_rain_totals", "hourly_heatmap")
# No block-count floor (owner 2026-11-03: "the minimum is everything we can do for that page"). Measured for the record on every live page 2026-11-03 (PLAN.md): blocks with data US median 35 (min 24), Canada min 11, Germany min 9; main-text words Canada min 1,413, Germany min 1,377.
# The US median is out of reach abroad: about 21 of its 35 blocks are US federal products COVER answers none for. So the floor sits one block under the thinnest live world page.
# Words are measured, not gated: most are template text, so a word count would pass padding and fail a short true page.


def thin_stats(h):
    """The thinness floor's measure of one built page: reader blocks with real data (valid or valid-empty; Unknown and could-not-load do not count), main-text words,
    and the must-haves a world page needs: a reading with time and unit, the alerts block, history or a normal label, and weather or rain with a value."""
    secs = re.findall(r'<section[^>]*\bclass="card blk[^"]*"[^>]*\bid="([^"]+)"[^>]*>(.*?)</section>', h, re.S)
    text = lambda x: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style|svg)\b.*?</\1>", " ", x)))
    real = [i for i, body in secs if i not in META and not re.search(r"\bUnknown\b|could not be loaded", text(body)[:400])]
    tiles = dict(re.findall(r'<div class="tile [^"]*"><i class="ic">.*?</i><span>([^<]+)</span><b>(.*?)</b>', h, re.S))
    val = lambda k: k in tiles and bool(re.search(r"\d", re.sub(r"<[^>]+>", "", tiles[k]))) and "Unknown" not in tiles[k]
    main = h.split("<main", 1)[1].split("</main>")[0] if "<main" in h else h
    words = len(text(re.sub(r"(?is)<(nav|footer|header)\b.*?</\1>", " ", main)).split())
    faults = []
    if not (re.search(r'class="hero[^"]*"[^>]*data-t="[^"]+"', h) and any(val(k) for k in ("Water level", "Gage height", "Flow", "Lake level", "Sea level"))):  # Sea level: Irish tide gauges (2026-11-09: the rename held Dublin Port as 'no reading')
        faults.append("no reading with its time and unit")
    if 'id="alerts"' not in h:
        faults.append("no alerts block")
    if not (any(i in real for i in HISTORY) or (tiles.get("Is this normal?") and "Unknown" not in tiles["Is this normal?"])):
        faults.append("no history and no normal label")
    if not (any(i in real for i in WEATHER) or val("Rain, last 24 h") or val("Air temperature")):
        faults.append("no weather and no rain with a value")
    return {"blocks": len(real), "words": words, "faults": faults}


def thin(h):
    """Why a world page cannot ship, or []. Owner 2026-11-08: "no such thing as thin content if it's literally a different river/lake"; only the ship test
    holds a page: a reading with its time and unit. Alerts, history and weather are counted in thin_stats, never a hold (a missing one says Unknown)."""
    return [f for f in thin_stats(h)["faults"] if f == "no reading with its time and unit"]


_CK = {}


def page_faults(url, h):
    """check.py's own per-page rules on a world page that was never published (2026-11-10 Dublin Port: a failing page with no live copy
    to carry stopped every deploy). Held here like a thin page instead: not built, not linked, named in the log. A checker that cannot load
    holds nothing (check.py still runs on the whole build)."""
    try:
        if not _CK:
            import sys
            if common.ROOT not in sys.path:
                sys.path.insert(0, common.ROOT)
            import check  # a module since full audit #47 (its main() runs only as a script)
            _CK.update(vars(check))
        h = common.NEG_ZERO.sub(r"\1", h).replace(" ", " ")  # as build.py writes it and check_dir reads it
        return _CK["page_checks"](h, url.strip("/") + "/index.html") + _CK["world_rules"](h) + _CK["one_latest"](h)
    except Exception as e:
        print("world page pre-check could not run: %s" % str(e)[:100])
        return []


def choose(pages, now):
    """Names per page that may publish: first pass over every gauge; a second gauge on an address already taken waits."""
    names, urls = {}, set()
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
            gone = missing(got[1], r) + ([] if "data-flood" in got[1] else ["flood warning note"]) + core.BLOCK_ERRORS[broke:]  # a block that crashed is never a quiet gap
            if gone:
                GAPS[r["name"]] = gone
            live = os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist", world_gauge_url(p, r.get("title") or r["name"]).strip("/"), "index.html"))  # holds stop new gauges; an outage never pulls a page
            if gone and GATE and not live:
                THIN[r["name"]] = gone  # every hold of a new page counts in room(), so held pages never keep spending the daily slots (review 2026-11-03)
                print("world gauge held, page lacks what its data allows: %s %s" % (r["name"], ", ".join(gone)))
                continue
            short = [] if live else (thin(got[1]) or page_faults(got[0], got[1]))  # the per-page floor that replaced the country cap (owner 2026-11-03): a thin page is held, never shipped and never noindexed; a new page failing check.py's page rules is held the same way (a live one is carried by check.py instead)
            if short:
                THIN[r["name"]] = short
                print("world gauge held, thin page: %s %s" % (r["name"], "; ".join(short)))
                continue
            # owner 2026-11-08: a page like another (same feed, same gauge, near-same text) is still the page a reader searched for; only the same address waits
            if got[0] in urls:  # two titles that slug alike: the second would overwrite the first page (review 2026-11-04); the list order decides, the second waits
                THIN[r["name"]] = ["same address as another gauge: %s" % got[0]]
                print("world gauge held, same address as another gauge: %s %s" % (r["name"], got[0]))
                continue
            urls.add(got[0])
            names[p["slug"]].add(r["name"])
    return names


def along(p, r, rows, keep=()):
    """The two nearest gauges each way on this river, with their readings: what is coming down to a reader here. A flat list has no river order, so it shows the four closest within 100 km."""
    names = [x["name"] for x in rows]
    i = names.index(r["name"])
    out = []
    near = sorted((x for x in rows if x is not r and not x.get("tidal") and x.get("lat") is not None and x.get("cm") is not None and wx.km(r["lat"], r["lon"], x["lat"], x["lon"]) <= 100), key=lambda x: wx.km(r["lat"], r["lon"], x["lat"], x["lon"]))[:4] if p.get("flat") else rows[max(0, i - 2):i] + rows[i + 1:i + 3]
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
    t, v, typ = max(pts, key=lambda p: p[1])  # typ: PEGELONLINE's own row type; an estimate is said as one (full audit #9)
    return parse_t(t).astimezone(zoneinfo.ZoneInfo(f["zone"])).strftime("%b %-d, %-I %p" if os.name != "nt" else "%b %#d, %#I %p"), v, "estim" in str(typ or "").lower()


def fresh(w, key, t, bid):
    return bool(w.get(key)) and t is not None and (hours_old(t, datetime.datetime.now(datetime.timezone.utc)) or 0) <= HIDE_H[bid]


def owed(r):
    """Block ids this gauge's data entitles a reader to. Age counts: past the US hide limit a block is rightly gone, so an outage never pulls a page. A gauge the weather collect never reached owes it all."""
    w = r.get("wx")
    if not w or (not w.get("no_weather") and not w.get("fetched_at") and not w.get("periods")):  # Ireland: weather is a COVER 'next', never 'not collected'
        return ["weather not collected yet"]
    rain = r.get("ea") is not None or ((w.get("rain") or {}).get("inches") or {}).get("last_24h") is not None  # England's tile has four states and always shows; elsewhere a total shows its tile, fresh or marked old. Canada has none (live 2026-11-04: 14 pages named for a tile they could not have)
    out = ["alerts", "official_links", "stage_chart"] + (['class="tile rain'] if rain else []) + (["along_river"] if r.get("_along") else []) + (["nearby_gauges"] if r.get("_near") else []) + ["about_gauge", "key_facts"]
    for key, t, bid in () if w.get("no_weather") else (("obs", (w.get("obs") or {}).get("timestamp"), "air_obs"), ("periods", w.get("forecast_updated"), "weather_forecast"), ("hourly", w.get("hourly_updated"), "hourly_forecast")):
        if fresh(w, key, t, bid):
            out.append(bid)
    if not w.get("no_weather") and fresh(w, "aq", (w.get("aq") or {}).get("t"), "air_quality"):
        out.append("air_quality")
    if fc_top({"fc": r.get("fc"), "zone": "UTC"}, datetime.datetime.now(datetime.timezone.utc)):
        out.append("river_forecast")
    if any(k in (r.get("marks") or {}) for k, _ in MARKS) or r.get("months") or r.get("record"):
        out.append("official_marks")
    if r.get("also"):
        out.append("also_measured")
    if any(parse_t(x[0]) > datetime.datetime.now(datetime.timezone.utc) for x in r.get("hilo") or []):  # Ireland: a station with predictions owes the next-tide tile
        out.append('class="tile fcst"')
    if len(r.get("flow") or []) >= 8:
        out.append("flow_chart")
    if len(r.get("series") or []) >= 8:
        out.append("rate_of_change")
    if r.get("deciles") or r.get("days") or r.get("years"):
        out.append("world_history")
    if r.get("peaks"):
        out.append("annual_peaks")
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
    return [b for b in owed(r) if (b if b.startswith("class=") else 'id="%s"' % b) not in h]


def near_index(wpages, keep):
    """Every published world gauge by 1-degree square: (lat, lon, name, url, level, label). ponytail: world only; US gauges near a border join when a world page can show a US reading in local units."""
    out = {}
    for p, d in wpages:
        for r in d["rows"]:
            if r["name"] in keep.get(p["slug"], ()) and r.get("lat") is not None and not r.get("tidal"):
                name = r.get("title") or "%s at %s" % (p["river"], r["name"].replace(" UP", "").title())
                lev = fmt_level(r["cm"], r.get("unit", "cm")) if r.get("cm") is not None else None
                out.setdefault((int(r["lat"] // 1), int(r["lon"] // 1)), []).append((r["lat"], r["lon"], name, world_gauge_url(p, r.get("title") or r["name"]), lev, LABEL.get(r.get("state"), "Unknown")))
    return out


NEAR_KM = 100  # same reader distance as lib/page.py NEAR_MI (60 mi, about an hour's drive)


def near(r, idx, skip, n=5):
    """The n nearest gauges at any distance, skipping urls in skip (owner 2026-11-08: every water page links its neighbours; live census: a Canada page linked no other gauge
    because none was within 100 km). Rings of 1-degree squares widen until n are found or the whole index is searched; the distance is printed beside each.
    ponytail: the n-th found in the first full ring may not be the true n-th nearest at a ring's corner; harmless for a 'nearest first' list."""
    la, lo = int(r["lat"] // 1), int(r["lon"] // 1)
    rad, got, total = 1, [], sum(len(v) for v in idx.values())  # review 2026-11-08: a small index stops as soon as every gauge is found
    while True:
        got = [(wx.km(r["lat"], r["lon"], a, b), name, u, lev, lab) for i in range(la - rad, la + rad + 1) for j in range(lo - 2 * rad, lo + 2 * rad + 1) for a, b, name, u, lev, lab in idx.get((i, j), ()) if u not in skip]
        if len(got) >= min(n, total - len(skip & {e[3] for v in idx.values() for e in v})) or rad > 180:
            break
        rad *= 2
    return [(round(k), name, u, lev, lab) for k, name, u, lev, lab in sorted(got)[:n] if k <= NEAR_KM]  # owner 2026-11-09 "no forced internal links": only within a short drive; hubs reach the rest


def page(p, r, now, rows=(), keep=(), idx=None):
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
    rec["feed"]["later"] = todo(p.get("feed", "pegelonline"))  # every COVER next item, named for the reader: a to-do, never a cap
    if p.get("feed") == "imi":  # a tide gauge measures sea level only; rain and forecasts are Met Eireann 'next' items (in later), never 'not published'
        rec["feed"]["gaps"] = []
    if p.get("feed") == "ea":  # England publishes some forecasts we do not show yet: never "not published"
        wt = (r.get("ea") or {}).get("wt")
        rec["feed"]["gaps"] = [w for w, have in (("water temperature", wt), ("flow", (r.get("ea") or {}).get("flow"))) if not have]
        rec["feed"]["later"] += ["flow (the agency's last 7 days include values below zero, so none is shown)"] if r.get("flow_bad") else []
        if not alerts_proven(p):  # owner 2026-11-03: until a live warning proves the point test, Unknown with the GOV.UK link; an empty list must never read as no warnings
            rec["nws"] = dict(rec["nws"], alerts=None, fetched_at=None)
            rec["feed"]["flood_line"], rec["feed"]["swap"] = EA_UNPROVEN_LINE, EA_UNPROVEN + FEEDS["ea"]["swap"]
            rec["feed"]["wx_credit"] = "Rain: Environment Agency. Weather forecast: Met Office Global Spot, Powered by Met Office data."
    rec["feed"]["along"] = along(p, r, list(rows), keep) if rows else []
    r["_along"] = bool(rec["feed"]["along"])  # owed() then demands the strip
    own = world_gauge_url(p, r.get("title") or r["name"])
    rec["feed"]["near"] = near(r, idx, {own} | {x[5] for x in rec["feed"]["along"] if x[5]}) if idx and r.get("lat") is not None else []
    r["_near"] = bool(rec["feed"]["near"])
    feed_key = p.get("feed", "pegelonline")
    rec["feed"]["about"] = [(k, v) for k, v in (
        ("Agency", rec["feed"]["name"]),
        ("Station number", r.get("number") or r["name"]),
        ("Station name in the agency's list", r["name"] if feed_key == "pegelonline" else r.get("title")),
        ("River kilometre (the marker on the bank)", ("%.2f" % r["km"]) if feed_key == "pegelonline" and isinstance(r.get("km"), (int, float)) and r["km"] > 0 else None),
        ("Years of daily values on record", str(r["day_years"]) if r.get("day_years") else None),
        ("Coordinates", "%.4f, %.4f" % (r["lat"], r["lon"]) if r.get("lat") is not None else None)) if v]  # every fact read from the agency's station record in this run's cache, never typed
    rec["feed"]["also"] = r.get("also") or {}
    rec["feed"]["head"] = row["place"] if p.get("flat") else "%s at %s" % (p["river"], row["place"])  # the H1 name, as localize writes it
    G = render.ctx(row["site"], row, rec, now)
    html, meta = render.build_tab("dashboard", G, {row["site"]: row})
    top = fc_top(rec["feed"], now)
    if top:
        html = FC_NONE.sub(ui.tile("fcst", "crest", "River forecast", fmt_level(top[1], rec["feed"]["unit"]), "<small>Highest in the forecast%s, %s. Federal Institute of Hydrology</small>" % (" (an estimate)" if top[2] else "", esc(top[0]))), html, count=1)
    if p.get("feed") == "ea":  # the weather is the Met Office's, never the Environment Agency's (localize names feed["wx"] for every NWS word)
        html = html.replace("Source: National Weather Service hourly point forecast", "Source: Met Office Global Spot hourly forecast for the gauge location, Powered by Met Office data").replace("Source: National Weather Service point forecast", "Source: Met Office Global Spot daily forecast for the gauge location, Powered by Met Office data")
        html = html.replace('<div class="tile sun', ea_rain_tile((r.get("wx") or {}).get("ea_rain"), now, rec["feed"]["zone"]) + '<div class="tile sun', 1)
    html = html.replace("Height above the gauge's zero point, not water depth", "%.1f ft. %s" %(to_ft(r["cm"], rec["feed"]["unit"]), "On this gauge's own scale, often a height above sea level, not water depth" if rec["feed"]["src"] == "eccc" else "Height above the gauge's zero point, not water depth"), 1)
    if p.get("feed") == "imi":  # over 24 h a tide compares two points of its cycle: '+0.60 m in 24 h' reads as a rising sea (PLAN 7c), so the summary does not say it
        html = re.sub(r'<span class="a1 dv">[+\-][\d.]+ m in 24 h</span>', "", html, count=1)
        html = re.sub(r'<div class="tile trend"><i class="ic">.*?</svg></i><span>24 h change</span>.*?</div>', "", html, count=1, flags=re.S)
        nxt_ = [x for x in (r.get("hilo") or []) if datetime.datetime.fromisoformat(x[0]) > now][:3]
        if nxt_:  # Marine Institute predictions, labelled as predictions, times in Irish time
            z_ = zoneinfo.ZoneInfo("Europe/Dublin")
            w_ = lambda x: "%s %.2f m (%.1f ft) at %s" % ("High" if x[2] == "H" else "Low", x[1], x[1] * 3.28084, render.tzl(datetime.datetime.fromisoformat(x[0]), z_, date=False))
            html = FC_NONE.sub(ui.tile("fcst", "crest", "Next tide (prediction)", "%s %.2f <small>m</small>" % ("High" if nxt_[0][2] == "H" else "Low", nxt_[0][1]),
                          "<small>At %s (%.1f ft)</small><small>Then: %s. Marine Institute prediction above OD Malin; weather can move the sea away from it.</small>" % (esc(render.tzl(datetime.datetime.fromisoformat(nxt_[0][0]), z_, date=False)), nxt_[0][1] * 3.28084,esc("; ".join(w_(x) for x in nxt_[1:])))), html, count=1)
    html = localize(html, rec["feed"], p["river"], row["place"], row["hub_url"], p.get("flat"))
    return row["dashboard_url"], html.replace("</head>", world_ld(p, r, row["dashboard_url"], rec["feed"], html) + "</head>", 1)
