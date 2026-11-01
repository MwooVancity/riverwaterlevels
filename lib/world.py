"""Gauges outside the US on the US page: a feed row becomes the record lib/hero.py reads (stage only, no flow), the US builder makes the page, this file only swaps agency words.
One template, so every fix to the gauge page reaches these too. A new feed adds a FEEDS row and a fetch in collect.py."""
import re
from lib import render
from lib.directory import esc, world_gauge_url, world_slug

FEEDS = {"pegelonline": {"agency": "WSV", "name": "German Federal Waterways and Shipping Administration (WSV)", "api": "PEGELONLINE", "unit": "cm", "zone": "Europe/Berlin"}}
LABEL = {"low": "Low", "normal": "Normal", "high": "High"}
MARKS = (("HHW", "Highest on record"), ("HW", "Highest in the agency's latest 10-year period"), ("HSW", "Highest level for shipping"), ("M_II", "High-water shipping mark II"), ("M_I", "High-water shipping mark I"), ("MHW", "Mean high water"),
         ("MW", "Average level"), ("MNW", "Mean low water"), ("GlW", "Equivalent low water (GlW)"), ("NW", "Lowest in the agency's latest 10-year period"), ("NNW", "Lowest on record"))
ROW = {"name_confidence": "high", "nws_lid": "", "place_final": "", "raw_name": "", "score": "0", "wave": "", "years_record": "0", "drainage_sqmi": "0"}


def ready(r):
    """The ship test: a real recent reading with its time. The series draws the chart; marks are shown when the agency has them."""
    return r.get("cm") is not None and bool(r.get("time")) and r.get("lat") is not None and r.get("lon") is not None and len(r.get("series") or []) >= 8


def to_rec(page, r):
    label = LABEL.get(r.get("state"), "Unknown")
    rows = [{"parameter_code": "00065", "time": t, "value": str(round(v / 30.48, 3)), "unit_of_measure": "ft", "qualifier": None, "approval_status": "Provisional"} for t, v in r["series"]]
    return {"site": "WSV-" + world_slug(r["name"]), "lat": r["lat"], "lon": r["lon"], "tz": FEEDS["pegelonline"]["zone"], "usgs": {"fetched_at": r["time"], "rows": rows, "truncated": False}, "_fetched": {},
            "feed": dict(FEEDS["pegelonline"], label=label, label_note="%s label, against this gauge's mean low and mean high water." % FEEDS["pegelonline"]["agency"], marks=r.get("marks") or {}, station=r["name"])}


def to_row(page, r):
    u = world_gauge_url(page, r["name"])
    place = r["name"].replace(" UP", "").title()
    return dict(ROW, site="WSV-" + world_slug(r["name"]), river=page["river"], place=place, state="DE", river_slug=page["slug"], place_slug=world_slug(r["name"]), dashboard_url=u, water_url=u, forecast_url=u + "forecast/",
                hub_url="/%s/" % page["slug"], hub_slug=page["slug"], _built=True, _hub=False, _single=True, _ll=(r["lat"], r["lon"]), _lv=None, _band="–")


SWAP = (("Latest USGS gage height", "Latest water level"), ("Solid line: USGS readings.", "Solid line: official readings."), ("NWS alerts unknown", "Official alerts unknown"), ("NWS alerts", "Official alerts"),
        ("Gage height", "Water level"), ("gage height", "water level"), ("The National Weather Service has no river forecast point for this gauge. The weather forecast below is not a river forecast.", "No river forecast is shown for this gauge."),
        ("We have no answer from the National Weather Service alert service for this location. Check weather.gov.", "No official alert feed is connected for this gauge. Check local authorities."),
        ('<span>River forecast</span><b>Not linked</b>', '<span>River forecast</span><b>Not issued</b>'), ("Data: USGS, NOAA, NWS.", "Data: official agencies, listed on each page."))
LIVE = """<script>(function(){var w=document.querySelector('.hero');if(!w||!window.fetch)return;fetch('/live/world.json').then(function(r){return r.json()}).then(function(j){var g=(j.g||{})['@N@'];if(!g||Date.parse(g[1])<=Date.parse(w.dataset.t))return;
var e=document.querySelector('[data-live=stage]');if(e)e.textContent=Math.round(g[0]);e=document.querySelector('[data-live=obs]');if(e)e.textContent=new Date(g[1]).toLocaleString('en-US',{timeZone:'@Z@',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'})}).catch(function(){})})();</script>"""


def localize(h, feed, river, place, hub):
    """The US builder's page, in this agency's words. A US word that survives here fails check.py world_rules, so nothing slips through."""
    for a, b in SWAP:
        h = h.replace(a, b)
    credit = "Source: %s, %s" % (feed["api"], feed["name"])
    h = re.sub(r"Source: USGS Water Data API[^<]*", credit + ".", h)
    h = re.sub(r'<div class="crumb">.*?</div>', '<div class="crumb"><a href="/">Home</a> / <a href="%s">%s</a> / %s</div>' % (hub, esc(river), esc(place)), h, count=1)
    h = re.sub(r"<h1>[^<]*</h1>", "<h1>%s at %s water level today</h1>" % (esc(river), esc(place)), h, count=1)
    h = re.sub(r"<title>[^<]*</title>", "<title>%s at %s water level today | River Water Levels</title>" % (esc(river), esc(place)), h, count=1)
    h = re.sub(r'<meta name="description" content="[^"]*"', '<meta name="description" content="%s at %s: current level in cm and feet, 24 h change and official high and low marks. %s."' % (esc(river), esc(place), esc(feed["api"])), h, count=1)
    title = "%s at %s water level today" % (esc(river), esc(place))
    h = re.sub(r'(<meta (?:property|name)="(?:og|twitter):(?:title|description)" content=")[^"]*', lambda m: m.group(1) + title, h)
    h = re.sub(r'<p class="cite">.*?</p>', "", h, flags=re.S)
    h = re.sub(r'<script type="application/ld\+json">(?:(?!</script>).)*"mainEntity".*?</script>', "", h, flags=re.S)
    h = re.sub(r"USGS gauge [^&<]*", "Gauge %s " % esc(feed["station"]), h)
    h = re.sub(r'<p class="gaps">.*?</p>', "", h, flags=re.S)
    h = h.replace("<p>The National Weather Service publishes no flood stages for this gauge, so none are drawn.</p>", "")
    h = re.sub(r'<details[^>]*id="sources">.*?</details>', '<p class="src">Data: %s, %s. Readings can be revised by the agency. Not endorsed by the agency. Not for navigation or safety-of-life decisions.</p>' % (esc(feed["agency"]), esc(feed["api"])), h, flags=re.S)
    h = h.replace('class="hero hero2"', 'class="hero hero2" data-n="%s"' % esc(feed["station"]), 1)
    h = re.sub(r'<script>\(function\(\)\{var ID="USGS-.*?</script>', lambda m: LIVE.replace("@N@", feed["station"]).replace("@Z@", feed["zone"]), h, flags=re.S)
    return h


def along(p, r, rows):
    """The two nearest gauges each way on this river, with their readings: what is coming down to a reader here."""
    names = [x["name"] for x in rows]
    i = names.index(r["name"])
    out = []
    for x in rows[max(0, i - 2):i] + rows[i + 1:i + 3]:
        out.append(("Upstream" if names.index(x["name"]) < i else "Downstream", x["name"].replace(" UP", "").title(), x["cm"], x["cm"] - x["then"] if x.get("then") is not None else None, LABEL.get(x.get("state"), "Unknown"), world_gauge_url(p, x["name"]) if ready(x) and x["name"] in (p.get("gauge_pages") or []) else None))
    return out


def page(p, r, now, rows=()):
    """(url, html) for one gauge, or None when it fails the ship test."""
    if not ready(r):
        return None
    row, rec = to_row(p, r), to_rec(p, r)
    rec["feed"]["along"] = along(p, r, list(rows)) if rows else []
    rec["feed"]["also"] = r.get("also") or {}
    G = render.ctx(row["site"], row, rec, now)
    html, meta = render.build_tab("dashboard", G, {row["site"]: row})
    html = html.replace("Height above the gauge's zero point, not water depth", "%.1f ft. Height above the gauge's zero point, not water depth" % (r["cm"] / 30.48), 1)
    return row["dashboard_url"], localize(html, rec["feed"], p["river"], row["place"], row["hub_url"])
