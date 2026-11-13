"""Blocks for the second wave of government sources (NWS forecast point facts, FEMA declarations, NCEI storm events, dams, Reclamation releases, ACIS rain, StreamCat, FEMA flood zones).
Same registry rules as render.py and blocks2.py. Each block is gated by its source row in data/sources.json.
"""
import collections, datetime, math, re
from lib.render import *  # block, table, tr, esc, fmt, tzl, parse_t, fdate, SOURCES, ...
from lib.hero import cdec_avg


def cleared(src_id):
    return SOURCES[src_id]["status"] in ("quoted", "owner-permission")



def b_nws_point(G, pages=None):
    n = G["rec"].get("nwps") or {}
    if not n.get("lid"):
        return None
    rows = tr(["Forecast point", esc(n.get("name") or "Name not published")])
    nm = lambda x: ("%s (%s)" % (x.get("name"), x.get("abbreviation")) if x.get("name") and x.get("abbreviation") else (x.get("abbreviation") or x.get("name") or "")) if isinstance(x, dict) else (x or "")
    if n.get("wfo"):
        rows += tr(["Weather Forecast Office", esc(nm(n["wfo"]))])
    if n.get("rfc"):
        rows += tr(["River Forecast Center", esc(nm(n["rfc"]))])
    if n.get("reliability") and (n.get("forecast") or {}).get("points"):
        rows += tr(["Forecast reliability, as published", esc(n["reliability"])])
    rows += tr(["Flood inundation maps", '<a href="https://water.noaa.gov/gauges/%s" rel="noopener" title="NWS point %s">Check this forecast point at water.noaa.gov</a>' % (esc(n["lid"]), esc(n["lid"]))])
    for key, lab in (("upstream", "Upstream forecast points"), ("downstream", "Downstream forecast points")):
        rfl = n.get("riverflow") or {}
        on_site = {(p.get("nws_lid") or "").upper(): p for p in (pages or {}).values() if p.get("_built") and p.get("nws_lid")}

        def nm_link(x):
            nm = esc(re.sub(r"\s*\(IN MLLW\)", "", x.get("Name") or x.get("LID") or "", flags=re.I))
            p = on_site.get((x.get("LID") or "").upper())
            return '<a href="%s">%s</a>' % (p["water_url"], nm) if p else nm
        raw_ = [x for x in (rfl.get(key) or []) if isinstance(x, dict)]
        nm_list = [x for i, x in enumerate(raw_) if (x.get("LID") or x.get("Name")) not in [(y.get("LID") or y.get("Name")) for y in raw_[:i]]]  # hater w5, Boise: two points listed three times each
        if nm_list:
            total = (rfl.get(key + "_n") or len(nm_list)) if len(nm_list) == len(raw_) else len(nm_list)
            if key == "upstream":  # stored farthest first: list nearest first
                nm_list = nm_list[::-1]
            if total > len(nm_list):
                lab = "%s (nearest %d of %d)" % (lab, len(nm_list), total)
            rows += tr([lab, "<br>".join(nm_link(x) for x in nm_list)])  # one point per line (hater 2026-10-27: a "; " wrapped to the start of a phone line after a link)
    return block("nws_forecast_point", "Forecast point for this gauge", "official", table(["Item", "Value"], rows),
                 "Source: National Weather Service National Water Prediction Service, forecast point %s, fetched %s." % (esc(n["lid"]), esc(tzl(parse_t(n["fetched_at"]), G["zone"]))), "nwps")


def sustained_pct(G, days):
    """Average percentile of the last N daily mean flows vs USGS daily statistics for those dates: 'has flow sat low/normal/high over the week/month', for irrigators and anglers."""
    rec = G["rec"]
    stats, m = rec.get("stats"), rec.get("multiyear") or {}
    if m.get("pc", "00060") != "00060":  # flow statistics only; a lake's elevation series (PLAN 0i) is never compared with them
        return None
    if not stats or not m.get("as_of"):
        return None
    as_of = datetime.date.fromisoformat(m["as_of"])
    ser = (m.get("series") or {}).get(str(as_of.year)) or []
    if len(ser) < days:
        return None
    pcts = []
    for i in range(1, days + 1):
        v = ser[-i]
        if v is None:
            continue
        srow = stats.get((as_of - datetime.timedelta(days=i - 1)).isoformat()[5:10])
        if srow:
            p = interp_pct(srow, v)
            if p is not None:
                pcts.append(max(0, min(100, p)))  # interp_pct returns -1/101 sentinels for below/above all published percentiles; clamp so the averaged percentile never prints as "-1th"/"101st"
    return round(sum(pcts) / len(pcts)) if len(pcts) >= max(3, days - 3) else None


def b_sustained(G):
    p7, p28 = sustained_pct(G, 7), sustained_pct(G, 28)
    if p7 is None and p28 is None:
        return None
    def band(p):  # the headline's USGS WaterWatch bands, so the two never disagree (hater 2026-10-27)
        return PCT_PHRASE[band_word(p)]
    def ordp(p):
        suf = "th" if 10 <= p % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(p % 10, "th")
        return "%d%s percentile" % (p, suf)
    parts = []
    if p7 is not None:
        parts.append("Past 7 days: %s, %s" % (ordp(p7), band(p7)))
    if p28 is not None:
        parts.append("Past 28 days: %s, %s" % (ordp(p28), band(p28)))
    return block("sustained_flow", "Flow over recent weeks", "hist", "<p>%s</p>" % " &middot; ".join(parts) + '<p class="src">Each day is placed among past years for that date and the placings are averaged. The month-to-date rank below instead compares this month\'s mean flow with each year\'s mean for the same dates, so the two can land in different bands.</p>',
                 "Source: USGS daily mean flow for each date through %s compared with USGS daily statistics for those same dates; the percentile shown is the average of the daily percentiles over the window." % esc(fdate(G["rec"]["multiyear"]["as_of"])), "usgs")


def b_access(G):
    """Boat ramps, put-ins and marinas near the gauge (OpenStreetMap). Where people get on the water."""
    a = G["rec"].get("access")
    if not a or not a.get("rows"):
        return None
    pri = {"Boat ramp": 0, "Whitewater put-in": 0, "Canoe/kayak put-in": 0, "Marina": 1}  # actual launch points before marinas, nearest first
    ordered = sorted(a["rows"], key=lambda x: (pri.get(x["type"], 2), x["mi"]))
    seen_ = set()
    named = [x for x in ordered if (x.get("name") or "").strip() and not (k_ := (x["name"].strip().lower(), x["type"], round(x["mi"], 1))) in seen_ and not seen_.add(k_)]  # review 2026-11-09: one marina mapped twice was listed twice
    unnamed = [x for x in ordered if not (x.get("name") or "").strip()]  # audit run 1, row 12: seven "(unnamed)" rows read as padding; they become one line
    rows = "".join(tr([esc(x["name"]), esc(x["type"]), "%.1f mi" % x["mi"]], right=(2,)) for x in named)
    body = table(["Name", "Type", "Distance"], rows, right=(2,)) if named else ""
    if unnamed:
        far = max(x["mi"] for x in unnamed)
        body += '<p>%d %sunnamed %s within %.1f mi. <a href="#gauge_map">Map of the gauge location</a></p>' % (len(unnamed), "more " if named else "", "ramp or access point" if len(unnamed) == 1 else "ramps or access points", far)
    return block("access_points", "Boat ramps, put-ins and marinas nearby", "map", body,
                 "Source: OpenStreetMap (boat ramps, canoe and whitewater put-ins, marinas) within about 15 miles of the gauge, %d found, nearest shown, fetched %s. © OpenStreetMap contributors, ODbL. Positions are community-mapped and may be approximate." % (a["count"], esc(tzl(parse_t(a["fetched_at"]), G["zone"]))), "osm")



def _on_river(water, river):
    """True when a stocked water is this river: its name carries the river's own name and is not a pond, lake or reservoir."""
    import re as _re
    key = _re.sub(r"(?i)\b(river|creek|fork|north|south|east|west|middle|branch|the)\b", " ", river).split()
    return bool(key) and all(_re.search(r"(?i)\b%s\b" % _re.escape(k), water) for k in key) and not _re.search(r"(?i)\b(pond|lake|reservoir|res\.?)\b", water)


def _on_lake(water, lake):
    """True when a stocked water is this lake (PLAN 36 edge case, 2026-11-13: lake pages never showed their own stocking because every lake was dropped).
    Whole words only: 'Lake Mead' must not match 'Meadow Pond'."""
    import re as _re
    key = _re.sub(r"(?i)\b(lake|reservoir|res|pond|the|of)\b\.?", " ", lake).split()
    return bool(key) and all(_re.search(r"(?i)\b%s\b" % _re.escape(k), water) for k in key) and not _re.search(r"(?i)\b(river|creek|brook|stream)\b", water)


def b_stocking(G):
    """Recent hatchery stocking near the gauge (species, date, count, water), from the state's public stocking layer. Hidden where the state has no adapter or no recent record."""
    s = G["rec"].get("stocking")
    if not s or not s.get("rows"):
        return None
    # hater 2026-10-27: ponds and lakes 14-35 mi away, 2025 rows under "Recent", "6.0" fish, duplicate rows. A pond release has no link
    # to this river (no mechanism): keep flowing waters only, the last 12 months, one row per water, date and species, whole fish.
    import re as _re
    cut = (G["now"] - datetime.timedelta(days=365)).date().isoformat()
    seen, keep = set(), []
    for x in s["rows"]:
        k = (x.get("date"), (x.get("species") or "").strip().lower(), (x.get("water") or "").strip().lower())
        if k in seen or str(x.get("date") or "") < cut or not (_on_lake if G.get("lake") else _on_river)(x.get("water") or "", G["river"]):
            continue
        seen.add(k)
        keep.append(x)
    if not keep:
        return None
    rows = "".join(tr([fdate(x["date"]), esc(re.sub(r"\((?=\S)", " (", x["species"] or "–")), fmt(round(x["num"])) if x.get("num") else "–", esc(x["water"] or "–"),
                       ("%.1f mi" % x["mi"]) if x.get("mi") is not None else "–"], right=(2, 4)) for x in keep)
    return block("stocking", "Recent fish stocking nearby", "hist",
                 table(["Date", "Species", "Number", "Water", "Distance"], rows, right=(2, 4)),
                 "Source: %s, hatchery stocking records within about %d miles of the gauge, most recent first, fetched %s. Credit: %s. Stocking is a release event, not a measure of fish now present in the river." % (
                     esc(s["source"]), s.get("miles", 35), esc(tzl(parse_t(s["fetched_at"]), G["zone"])), esc(s["credit"])), "stocking")


def acis_name(n):
    """ACIS station names arrive in capitals and code: plain words for a reader (PLAN 0b, tide re-review: "San Diego 6.6 S" read as jargon).
    "CHEVY CHASE 1.2 SW" -> "1.2 mi southwest of Chevy Chase"; "NORTH ISLAND NAS" -> "North Island Naval Air Station"; "X AP" -> "X Airport"."""
    import re
    t = (n or "").title()
    for a, b in ((r"\bWfo\b", "NWS office"), (r"\bAp\b", "Airport"), (r"\bIntl\b", "International"), (r"\bNas\b", "Naval Air Station"), (r"\bAfb\b", "Air Force Base"), (r"\bMcas\b", "Marine Corps Air Station"), (r"\bRs\b", "Ranger Station"), (r"\bCo-?Op\b", "co-op station")):
        t = re.sub(a, b, t)
    words = {"N": "north", "S": "south", "E": "east", "W": "west", "NE": "northeast", "NW": "northwest", "SE": "southeast", "SW": "southwest", "NNE": "north-northeast", "ENE": "east-northeast", "ESE": "east-southeast", "SSE": "south-southeast", "SSW": "south-southwest", "WSW": "west-southwest", "WNW": "west-northwest", "NNW": "north-northwest"}
    m = re.fullmatch(r"(.+?) (\d+(?:\.\d+)?) ([NSEW]{1,3})", t, flags=re.I)
    d = words.get(m.group(3).upper()) if m else None
    if d:
        return "%s mi %s of %s" % (m.group(2), d, m.group(1))
    return re.sub(r"\b(\d+(?:\.\d+)?) ([NSEW]{1,3})\b", lambda m: m.group(1) + " " + m.group(2).upper(), t, flags=re.I)  # 'NNE' and other three-letter points stay as the agency writes them


def b_dam(G):
    """Release from the dam hand-matched to this gauge (data/dams.json): latest outflow, and lake level where the agency gives it. Hidden for every gauge without a dam."""
    d = G["rec"].get("dam_rise") or G["rec"].get("dam_cwms")
    f = (d or {}).get("flow")
    if not f:
        return None
    sid = "usbr" if d["kind"] == "rise" else "cwms"
    if not cleared(sid):
        return None
    if d["kind"] == "rise":
        t = datetime.datetime.combine(datetime.date.fromisoformat(f["day"]), datetime.time(12), tzinfo=G["zone"])
        when = "daily mean for %s" % fdate(f["day"])
    else:
        t = parse_t(f["t"])
        when = ("daily mean ending %s" if f.get("daily") else "%s") % tzl(t, G["zone"])
    src = "Source: %s, %s, fetched %s. %s." % (esc(d["agency"]), "Reclamation Information Sharing Environment (RISE)" if sid == "usbr" else "USACE Water Management CWMS Data API", esc(tzl(parse_t(d["fetched_at"]), G["zone"])), "Release is the water the dam lets out, not the flow at this gauge")
    if (G["now"] - t).total_seconds() > 3 * 86400:
        return block("dam_releases", "Dam release upstream", "agency", "<p>The latest release reported for %s is from %s, older than 3 days, so it is not shown.</p>" % (esc(d["dam"]), esc(fdate(t.date().isoformat()))), src, sid, empty=True)
    rows = tr(["Outflow (release)", "%s cfs" % fmtc(f["v"]), esc(when)])
    p = d.get("pool")
    if p and (G["now"] - datetime.datetime.combine(datetime.date.fromisoformat(p["day"]), datetime.time(12), tzinfo=G["zone"])).total_seconds() <= 3 * 86400:
        rows += tr(["Lake level (elevation above sea level)", "%s ft" % fmt(p["v"]), "reading for %s" % esc(fdate(p["day"]))])
    return block("dam_releases", "Dam release upstream: %s" % esc(d["dam"]), "agency", table(["Measure", "Value", "Time"], rows, right=(1,)), src, sid)


def b_dam_facts(G):
    """The lake's dam, or the dam a river gauge sits below, as the USACE National Inventory of Dams states it (collect.py nid_match).
    No match, two equal candidates, or never fetched: no block (we do not know a dam is there). Matched with no facts: one grey line. Older than 75 days: amber.
    Hazard potential is left out on purpose: it rates harm if the dam failed, and beside a lake it reads as a danger verdict."""
    d = G["rec"].get("nid") or {}
    m = d.get("match")
    if not m or not cleared("nid"):
        return None
    ac = lambda v, u: "{:,.0f} {}".format(v, u)
    rows = [(k, v) for k, v in (
        ("Year completed", m.get("year") and str(m["year"])),
        ("Owner", m.get("owner") or (m.get("owner_type") and "%s (NID owner type)" % m["owner_type"])),
        ("Operator", m.get("operator")),
        ("Purposes", m.get("purposes")),
        ("River or stream", m.get("river")),
        ("Dam height (NID height: the largest of its dam, structural and hydraulic heights)", m.get("height_ft") is not None and ac(m["height_ft"], "ft")),
        ("Lake surface area at normal pool", m.get("area_ac") is not None and ac(m["area_ac"], "acres")),
        ("Normal storage (below the normal pool, including dead storage)", m.get("normal_af") is not None and ac(m["normal_af"], "acre-ft")),
        ("Maximum storage (below the highest possible water surface)", m.get("max_af") is not None and ac(m["max_af"], "acre-ft")),
        ("Distance from this gauge (our calculation)", "%.1f mi" % m["mi"])) if v]
    name = m.get("name") or m["id"]
    also = " (%s)" % m["other"] if m.get("other") and m["other"].lower() != name.lower() else ""
    src = "Source: USACE National Inventory of Dams, record %s%s, fetched %s. Values as the NID states them; the distance is our calculation." % (
        esc(m["id"]), (", NID data updated %s" % esc(fdate(m["updated"]))) if m.get("updated") else "", esc(fdate(d["fetched_at"][:10])))
    age_h = (G["now"] - parse_t(d["fetched_at"])).total_seconds() / 3600
    if len(rows) == 1:  # only our distance: the NID record carries none of the facts
        return block("dam_facts", "The dam: %s" % esc(name), "hist", "<p>The National Inventory of Dams lists %s%s (record %s) but states none of its size, age or purposes.</p>" % (esc(name), esc(also), esc(m["id"])), src, "nid", empty=True)
    lead = '<p class="lead">%s%s%s, %.1f mi from this gauge.</p>' % (esc(name), esc(also), (", completed in %d" % m["year"]) if m.get("year") else "", m["mi"])
    return block("dam_facts", "The dam: %s" % esc(name), "hist", lead + table(["Measure", "Value"], "".join(tr([esc(a), esc(b)], right=(1,)) for a, b in rows), right=(1,)), src, "nid", amber=age_h)


def b_samples(G):
    """Last 3 E. coli results on this river's channel (15 km up and down, NLDI river navigation), none older than 3 years. No verdict."""
    w = G["rec"].get("wqp")
    if not w or "n_sites" not in w or not cleared("wqp"):  # a cache from before 2026-10-29 holds the old bounding-box shape
        return None
    cut = (G["now"] - datetime.timedelta(days=1095)).date().isoformat()
    rows = [r for r in w.get("rows") or [] if r["date"] >= cut]
    src = "Source: Water Quality Portal (EPA, USGS and state agencies), E. coli results at stations on this river within 9 miles upstream and downstream, found by USGS NLDI river navigation, fetched %s." % esc(tzl(parse_t(w["fetched_at"]), G["zone"]))
    if not rows:
        return block("water_samples", "E. coli samples on this stretch", "agency", "<p>No E. coli samples on file for this stretch in the last 3 years (Water Quality Portal).</p>", src, "wqp", empty=True)
    body = table(["Sample date", "E. coli", "Station"], "".join(tr([esc(fdate(r["date"])), esc(("%s %s" % (r["value"], r["unit"]) if r["unit"] and r["unit"].lower() != "none" else "%s (unit not reported)" % r["value"]) if r["value"][:1].isdigit() else r["value"]), esc("%s (%s)" % (r["site"], r["id"]))]) for r in rows))
    return block("water_samples", "E. coli samples on this stretch", "agency", body, src, "wqp")


def b_acis(G):
    a = G["rec"].get("acis")
    if not a or not a.get("stations"):
        return None
    keep = [i for i, d in enumerate(a["days"]) if d <= G["now"].astimezone(G["zone"]).date().isoformat()]  # collect asks ACIS up to today in UTC: after midnight UTC a US page showed tomorrow as 'not reported' (review 2026-11-09)
    a = dict(a, days=[a["days"][i] for i in keep], stations=[dict(x, vals=[x["vals"][i] for i in keep if i < len(x["vals"])]) for x in a["stations"]])
    heads = ["Station", "Distance"] + [md(datetime.date.fromisoformat(d)) for d in a["days"]]
    cell = lambda v: (lambda w: "not reported" if w in ("M", "S", "A") else ("trace" if w == "T" else "%s in" % w if w.replace(".", "", 1).isdigit() else esc(w)))(v.rstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ") if v[:1].isdigit() else v)  # a trailing ACIS flag letter ("0.00A") is a source code, not part of the value
    _seen = set()
    a = dict(a, stations=[x for x in a["stations"] if not ((acis_name(x["name"]), round(x["km"], 1)) in _seen or _seen.add((acis_name(x["name"]), round(x["km"], 1))))])  # full review: one station twice, 0.00 vs trace
    _nm = collections.Counter(acis_name(x["name"]) for x in a["stations"])
    # owner 2026-11-09 ("hard to read at a first glance"): days run down, the 3 nearest stations across (was 5 stations x 7 days sideways), one answer sentence first
    st3 = sorted(a["stations"], key=lambda x: x["km"])[:3]
    nm = lambda x: esc(acis_name(x["name"]) + ((" (%s)" % (x.get("sid") or x.get("id") or "%.1f mi" % km_mi(x["km"]))) if _nm[acis_name(x["name"])] > 1 else ""))
    heads = ["Day"] + ["%s (%.0f mi away)" % (nm(x), km_mi(x["km"])) for x in st3]
    rows = "".join(tr([md(datetime.date.fromisoformat(d))] + [cell(x["vals"][i]) if i < len(x["vals"]) else "not reported" for x in st3], right=tuple(range(1, 4))) for i, d in reversed(list(enumerate(a["days"]))))
    num = lambda v: (lambda w: float(w) if w.replace(".", "", 1).isdigit() else (0.0 if w == "T" else None))(v.rstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ") if v[:1].isdigit() else v)
    got = [(d, num(v)) for d, v in zip(a["days"], st3[0]["vals"]) if num(v) is not None]
    if got:
        tot, wet = sum(v for _, v in got), max(got, key=lambda x: x[1])
        lead = '<p class="lead">%s, %.0f mi away: %s over the last %d day%s%s.</p>' % (nm(st3[0]), km_mi(st3[0]["km"]), ("%.2f in" % tot) if tot >= 0.01 else "no measurable rain", len(got), "" if len(got) == 1 else "s", (", most on %s (%.2f in)" % (md(datetime.date.fromisoformat(wet[0])), wet[1])) if wet[1] >= 0.01 else "")
    else:
        lead = '<p class="lead">%s, %.0f mi away: no reports in the last %d day%s.</p>' % (nm(st3[0]), km_mi(st3[0]["km"]), len(a["days"]), "" if len(a["days"]) == 1 else "s")
    return block("county_station_rain", "Measured daily rain at nearby weather stations", "obs", lead + ('<p class="src">Each date is one station observation day, which often ends in the morning, so it does not line up with the rain totals for the gauge location above.</p>' if (G["rec"].get("rain") or {}).get("inches") else "") + table(heads, rows, right=(1, 2, 3)),
                 "Source: NOAA Regional Climate Centers ACIS, daily precipitation at the nearest county weather stations, fetched %s. Each value is a 24-hour total for the station's observation day; trace means less than 0.01 in. Where ACIS lists two reports for one station, the first is shown." % esc(tzl(parse_t(a["fetched_at"]), G["zone"])), "acis")


def b_streamcat(G):
    s = G["rec"].get("streamcat")
    if not s or not s.get("vals"):
        return None
    v = s["vals"]
    spec = (("pctimp2019ws", "Impervious surface, 2019 (pavement and roofs)", lambda x: "%.1f%%" % x), ("pcturbmd2019ws", "Medium-intensity urban land, 2019", lambda x: "%.1f%%" % x), ("pctcrop2019ws", "Cropland, 2019", lambda x: "%.1f%%" % x),
            ("pctwdwet2019ws", "Woody wetland, 2019", lambda x: "%.1f%%" % x), ("elevws", "Mean elevation", lambda x: "%s ft" % fmt(x * 3.28084)), ("precip8110ws", "Mean annual precipitation, 1981 to 2010", lambda x: "%.1f in" % (x / 25.4)),
            ("runoffws", "Mean annual runoff (rain that leaves as streamflow)", lambda x: "%.1f in" % (x / 25.4)), ("bfiws", "Base-flow index (share of streamflow from groundwater)", lambda x: "%.0f%%" % x), ("damdensws", "Dam density (dams per square mile of watershed)", lambda x: "%.3f per sq mi" % (x * 2.58999)))
    rows = "".join(tr([lab, f(v[k])], right=(1,)) for k, lab, f in spec if k in v)
    from lib import ui
    pc = [(l, k) for k, l in (("pctimp2019ws", "Impervious surface, 2019 (pavement and roofs)"), ("pcturbmd2019ws", "Medium-intensity urban land, 2019"), ("pctcrop2019ws", "Cropland, 2019"), ("pctwdwet2019ws", "Woody wetland, 2019"), ("bfiws", "Base-flow index (share of streamflow from groundwater)")) if k in v]
    wid = ui.bars([(l, v[k], "%.1f%%" % v[k]) for l, k in pc], 100) if pc else ""
    ch = ui.chips([(l, f(v[k])) for k, l, f in spec if k in ("elevws", "precip8110ws", "runoffws", "damdensws") and k in v])
    return block("watershed_characteristics", "Upstream watershed characteristics", "agency", wid + ch,
                 "Source: U.S. EPA StreamCat, watershed-wide metrics; land cover from the 2019 National Land Cover Database. Static values, fetched %s." % (esc(tzl(parse_t(s["fetched_at"]), G["zone"]))), "epa")


def _year_svg(rows, stats, W, Hh, fs, nx, cls, xfmt="%b %Y", period="12 months"):
    L, B = (56, 30) if W > 500 else (46, 28)
    D = datetime.date.fromisoformat
    d0, d1 = D(rows[0][0]), D(rows[-1][0])
    span = max((d1 - d0).days, 1)
    vals = [v for _, v in rows]
    band = []
    if stats:
        for i in range(span + 1):
            r_ = stats.get((d0 + datetime.timedelta(days=i)).isoformat()[5:10])
            if r_ and r_[4] is not None and r_[6] is not None and r_[5] is not None:
                band.append((i, r_[4], r_[6], r_[5]))
        for _, a, c, _m in band:
            vals += [a, c]
    vmin, vmax, ticks = nice_ticks(min(vals), max(vals))
    X = lambda i: L + i / span * (W - L - 14)
    Y = lambda v: 12 + (1 - (v - vmin) / ((vmax - vmin) or 1)) * (Hh - B - 12)
    grid = "".join('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--line)"/><text x="%d" y="%.1f" font-size="%d" fill="var(--mut)" text-anchor="end">%s</text>' % (L, W - 14, Y(tv), Y(tv), L - 6, Y(tv) + 4, fs, tf(tv, ticks)) for tv in ticks)
    xl = ""
    for k in range(nx):
        i = round(span * k / (nx - 1))
        xl += '<text x="%.1f" y="%d" font-size="%d" fill="var(--mut)" text-anchor="%s">%s</text>' % (X(i), Hh - 8, fs, "start" if k == 0 else "end" if k == nx - 1 else "middle", (d0 + datetime.timedelta(days=i)).strftime(xfmt).replace(" 0", " "))
    shape = ""
    if band:
        up = " ".join("%.1f,%.1f" % (X(i), Y(c)) for i, a, c, m in band)
        dn = " ".join("%.1f,%.1f" % (X(i), Y(a)) for i, a, c, m in reversed(band))
        md = " ".join("%.1f,%.1f" % (X(i), Y(m)) for i, a, c, m in band)
        shape = '<polygon points="%s %s" fill="var(--soft)"/><polyline points="%s" fill="none" stroke="var(--mut)" stroke-dasharray="4 4"/>' % (up, dn, md)
    segs, cur, prev = [], [], None
    for ds, v in rows:
        i = (D(ds) - d0).days
        if prev is not None and i - prev > 3:
            segs.append(cur)
            cur = []
        cur.append("%.1f,%.1f" % (X(i), Y(v)))
        prev = i
    segs.append(cur)
    line = "".join('<polyline points="%s" fill="none" stroke="var(--accent)" stroke-width="1.8"/>' % " ".join(s) for s in segs if len(s) > 1)
    return '<svg class="%s" viewBox="0 0 %d %d" width="100%%" role="img" aria-label="Daily mean flow in cfs over the last %s with the 25th to 75th percentile band for each date">%s%s%s%s</svg>' % (cls, W, Hh, period, shape, grid, xl, line)


def b_month_chart(G):
    y = G["rec"].get("year")
    rows = (y or {}).get("rows") or []
    if len(rows) < 300 or (G["ldate"] - datetime.date.fromisoformat(rows[-1][0])).days > 10:
        return None
    last = rows[-30:]
    if (datetime.date.fromisoformat(last[-1][0]) - datetime.date.fromisoformat(last[0][0])).days < 20:
        return None
    svg = _year_svg(last, G["stats"], 760, 250, 11, 5, "cw", "%b %d", "30 days") + _year_svg(last, G["stats"], 340, 250, 12, 3, "cn", "%b %d", "30 days")
    return block("month_chart", "Last 30 days", "hist", svg + (LEG if G["rec"].get("stats") else ""),
                 "Source: USGS daily mean flows (Water Data API), %s to %s. Gaps are days without a published value; recent days are provisional. Flow in cfs." % (esc(fdate(last[0][0])), esc(fdate(last[-1][0]))), "usgs")


def b_year_chart(G):
    y = G["rec"].get("year")
    if not y or len(y.get("rows") or []) < 300:
        return None
    if (G["ldate"] - datetime.date.fromisoformat(y["rows"][-1][0])).days > 10:
        return None
    svg = _year_svg(y["rows"], G["stats"], 760, 250, 11, 5, "cw") + _year_svg(y["rows"], G["stats"], 340, 250, 12, 3, "cn")
    return block("year_chart", "Last 12 months", "hist", svg,
                 "Source: USGS daily mean flows (Water Data API), %s to %s. Shaded band: 25th to 75th percentile of USGS daily statistics for each date; dashed: median. Gaps are days without a published value; recent days are provisional." % (fdate(y["rows"][0][0]), fdate(y["rows"][-1][0])), "usgs")


def b_field_meas(G):
    f = G["rec"].get("fieldmeas")
    if not f or not f.get("rows"):
        return None
    rows = "".join(tr([fdate(r["t"][:10]), "%s cfs" % fmtc(r["flow"]), ("%.2f ft" % r["stage"]) if r.get("stage") is not None else "–", esc(r.get("rating") or "–")], right=(1, 2)) for r in f["rows"][:10])
    return block("field_measurements", "USGS field measurements", "hist", table(["Date", "Measured flow", "Gage height", "USGS measurement quality"], rows, right=(1, 2)),
                 "Source: USGS Water Data API field measurements, the %d most recent site-visit measurements with a flow value, fetched %s. The measurement quality shown is the USGS measurement rating as published." % (min(10, len(f["rows"])), esc(tzl(parse_t(f["fetched_at"]), G["zone"]))), "usgs")


def depth_rows(G):
    """USGS channel measurements within a mile of the gauge (collect.chan_rows), newest first, plus the one whose flow is closest to the latest reading."""
    c = (G["rec"].get("fieldmeas") or {}).get("chan")
    if not c:
        return None, None
    lv = G.get("lv")
    near = min(c, key=lambda r: abs(math.log(r[1] / lv))) if lv and lv > 0 else None
    return c, near


_LIMITS = None


def limits_for(site):
    """data/activity-limits.csv rows for this gauge (hand-checked official quotes, PLAN 7). A rule past its `until` date is dropped."""
    global _LIMITS
    if _LIMITS is None:
        import csv, os
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "activity-limits.csv")
        _LIMITS = list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else []
    today = datetime.date.today().isoformat()
    return [r for r in _LIMITS if r["site"] == site and not (r.get("until") and r["until"] < today)]


def b_limits(G):
    """PLAN 7 (2026-11-03 gap research rank 1): an agency's own published limit or closure for this reach, quoted word for word with its source
    and date. Today's reading sits beside the threshold only when the agency names this gauge and the unit matches; never our verdict."""
    rows = limits_for(G["site"])
    if not rows:
        return None
    now_v = {"cfs": G.get("lv") if not G.get("stage_only") else None, "ft": G["sg"][-1][1] if G.get("sg") else None}
    out, used = "", set()
    for r in rows:
        v = now_v.get(r["unit"]) if r["agency_gauge"] == G["site"] else None
        thr = float(r["threshold"]) if r.get("threshold") else None
        cmp_ = ""
        if v is not None and thr is not None:  # phone review 2026-11-11: the reading and its time once in the lead, one short word per rule, the agency's own number
            used.add(r["unit"])
            cmp_ = " <i>Now %s %s %s.</i>" % ("above" if v > thr else "below" if v < thr else "at", esc(r["threshold"]), r["unit"])
        elif r["agency_gauge"] and r["agency_gauge"] != G["site"]:
            cmp_ = " This rule names %s, not this gauge." % esc(r["agency_gauge"])
        out += '<p><b>%s</b> (%s%s): &ldquo;%s&rdquo;%s</p>' % (esc(r["source_name"]), esc(r["activity"]), (", " + esc(r["season"])) if r.get("season") else "", esc(r["quote"]), cmp_)
    lead = "%d rule%s from %s." % (len(rows), "" if len(rows) == 1 else "s", " and ".join(sorted({r["source_name"] for r in rows})))
    for u in sorted(used):
        lead += " Now at this gauge: %s %s (%s)." % (fmtc(now_v[u]) if u == "cfs" else "%.2f" % now_v[u], u, esc(G["obs"]))
    out = "<p><b>%s</b> The agency's own words; rules change, so check the source before you go.</p>" % lead + out
    src = "; ".join('<a href="%s" rel="noopener">%s</a> (%s, read %s)' % (esc(r["source_url"]), esc(r["source_name"]), esc(r["page_date"] or "no date on the page"), esc(fdate(r["read_on"]))) for r in {r["source_url"]: r for r in rows}.values())  # one source line per agency page, however many rules it carries
    return block("limits", "Rules the agencies publish for this water", "agency",
                 out,
                 "Source: %s. Quoted word for word." % src, "local_rules")


def b_depth(G):
    """How deep and wide the river is at the gauge: USGS hydrographers' measured width and cross-section area; average depth = area / width is our math."""
    c, near = depth_rows(G)
    if c is None:
        return None
    if not c:  # USGS has measurements, none within a mile of the gauge with width and area
        return None
    d = lambda r: r[3] / r[2]
    where = lambda r: "at the gauge" if r[5] < 50 else "%s ft %s" % (fmtc(r[5]), {"Upstream": "upstream", "Downstream": "downstream"}.get(r[6], "away"))
    say = lambda r: "on %s, at %s cfs, USGS measured the river %s ft wide with an average depth of %.1f ft" % (fdate(r[0][:10]), fmtc(r[1]), fmtc(r[2]), d(r))
    first = near or c[0]  # the reader asks how deep it is today: the measurement at the flow nearest today's leads (phone review 2026-11-09)
    lead = "<p><b>About %.0f ft deep on average</b> %s: %s (%s). An average across the whole channel (area divided by width): pools and the main channel are deeper, edges shallower, and depth changes with the flow.</p>" % (d(first), "at a flow like today's (%s cfs)" % fmtc(G["lv"]) if near else "when last measured", say(first), where(first))  # fresh review 2026-11-09: an average read as a wading depth
    if first is not c[0]:
        lead += "<p>Latest measurement: %s (%s).</p>" % (say(c[0]), where(c[0]))
    rows = "".join(tr([fdate(r[0][:10]), "%s cfs" % fmtc(r[1]), "%.1f ft" % d(r), "%s ft" % fmtc(r[2])], right=(1, 2, 3)) for r in c[:10])
    return block("depth", "How deep and wide the river is here", "hist", lead + more("All %d recent measurements" % min(10, len(c)), table(["Date", "Flow", "Average depth", "Width"], rows, right=(1, 2, 3))),
                 "Source: USGS Water Data API channel measurements (hydrographer site visits within a mile of the gauge; the main channel of each visit), fetched %s. Average depth = area &divide; width, our math." % esc(tzl(parse_t(G["rec"]["fieldmeas"]["fetched_at"]), G["zone"])), "usgs")


SPEED_NEAR, SPEED_MIN, SPEED_YEARS = 0.25, 3, 20  # visits within 25% of today's flow; at least 3; none older than 20 years (the channel moves)


def _hm(mins):
    m = int(round(mins))
    return "%d min" % m if m < 60 else "%d h %02d min" % (m // 60, m % 60)


def b_speed(G):
    """How fast the water moves here at flows like today's (owner 2026-11-12, PLAN 19a): USGS hydrographers' measured mean velocity on visits within a mile
    of the gauge at flows within 25% of the latest reading; the float times are our arithmetic from that range. Not a trip time."""
    c = (G["rec"].get("fieldmeas") or {}).get("chan") or []
    lv = G.get("lv")
    if not c or not lv or lv <= 0 or G.get("offline") or G.get("osc") or G.get("tidal") or G.get("lake") or G.get("coast") or G.get("stage_only"):
        return None
    cut = (G["ldate"] - datetime.timedelta(days=365 * SPEED_YEARS)).isoformat()
    near = [r for r in c if abs(r[1] - lv) <= SPEED_NEAR * lv and 0 < r[4] <= 20 and r[0][:10] >= cut]
    if len(near) < SPEED_MIN:
        return None
    lo, hi = min(r[4] for r in near), max(r[4] for r in near)
    mph = lambda v: v * 3600 / 5280
    per = lambda v, mi: 5280 * mi / v / 60
    rows = "".join(tr(["%d mile%s" % (mi, "" if mi == 1 else "s"), ("about %s" % _hm(per(hi, mi))) if abs(hi - lo) < 0.05 else "%s to %s" % (_hm(per(hi, mi)), _hm(per(lo, mi)))], right=(1,)) for mi in (1, 3, 5, 10))
    lead = ("<p><b>At flows like today's, the water here has moved about %.1f to %.1f mph</b> (%.1f to %.1f ft/s, average across the channel, measured by USGS on %d visits at %s to %s cfs). "
            "The main current and the surface run faster than the average; pools, eddies and the edges run slower, and wind and stops add time.</p>") % (
        mph(lo), mph(hi), lo, hi, len(near), fmtc(min(r[1] for r in near)), fmtc(max(r[1] for r in near)))
    return block("water_speed", "How fast the water moves here", "hist", lead + table(["Distance", "Time drifting at that speed"], rows, right=(1,)),
                 "Source: USGS Water Data API channel measurements (hydrographer site visits within a mile of the gauge, main channel, last %d years) at flows within %d%% of the latest reading, %s cfs. "
                 "Mean velocity is the flow divided by the channel's cross-section area at one spot on one day; the times are our arithmetic (distance divided by that speed), not a trip time for any stretch." % (SPEED_YEARS, round(SPEED_NEAR * 100), fmtc(lv)), "usgs")


def window_change(fl, lt, h):
    """Flow change over h hours: the latest reading against the reading closest to h hours earlier (within 20 minutes or 60% of the reporting interval), exactly what the rate table shows and what anyone can read off USGS. Returns (latest, earlier, percent) or None.
    A noisy gauge is not smoothed here: it is recognised (flow_jitter in lib/render.py, or the gage height contradicting the flow) and the headline says so. The headline tile, the rate table and the home and hub tables all use this."""
    if len(fl) < 2:
        return None
    steps = sorted((fl[i][0] - fl[i - 1][0]).total_seconds() for i in range(max(1, len(fl) - 200), len(fl)))
    tol = max(1200, 0.6 * (steps[len(steps) // 2] if steps else 900))
    tgt = lt - datetime.timedelta(hours=h)
    near = min(fl, key=lambda x: abs((x[0] - tgt).total_seconds()))
    if abs((near[0] - tgt).total_seconds()) > tol or not near[1] or near[1] <= 0:
        return None
    return fl[-1][1], near[1], (fl[-1][1] - near[1]) / near[1] * 100


def _fc_offset(G, pts, unit, gap):
    """The forecast point nearest the latest reading, compared with that reading: a forecast that is hours out of step with the gauge (dam releases) must say so. None when they agree,
    across zero points, and in a tidal reach, where one reading against a daily forecast says nothing (hater 2026-10-27, Freeport)."""
    if not pts or (unit == "ft" and gap) or G["osc"]:
        return None
    t0 = G["lt"]
    near = min(pts, key=lambda x: abs((x[0] - t0).total_seconds()))
    if abs((near[0] - t0).total_seconds()) > FC_NEAR_S:
        return None
    if unit == "ft":
        if not near[1] or not G["sg"] or not stage_is_ft(G["sg"][-1][2]):
            return None
        cur, fv = G["sg"][-1][1], near[1]
        if abs(cur - fv) <= max(0.5, 0.05 * abs(cur)):
            return None
        return {"t": tzl(near[0], G["zone"], date=False), "f": "%.1f ft" % fv, "c": "%.2f ft" % cur}
    cur, fv = G["lv"], near[2]
    if not fv or abs(cur - fv) <= FC_OFF_REL * max(cur, fv):
        return None
    return {"t": tzl(near[0], G["zone"], date=False), "f": "%s cfs" % fmtc(fv), "c": "%s cfs" % fmtc(cur)}


def conditions(G, pages=None):
    """Current conditions beyond flow and stage that the stat tiles show: change over 1, 6 and 24 h, forecast high, alert names, rain, each with its source time. Missing values are simply absent."""
    from lib.blocks2 import _at
    zone, fl, lt, lv, rec = G["zone"], G["fl"], G["lt"], G["lv"], G["rec"]
    ok = lambda sid: SOURCES[sid]["status"] in ("quoted", "owner-permission")
    out = {"chg": {}, "fc": None, "alerts": None, "rain": None, "wt": None, "air": None, "up": None, "old": {}}  # old: tiles hidden for age -> the age in words, so the gaps line names them
    wts = series(rec, "00010")
    if wts and (G["now"] - wts[-1][0]).total_seconds() <= 24 * 3600 and (wts[-1][2].get("unit_of_measure") or "").lower().replace(" ", "") in ("degc", "°c"):
        out["wt"] = {"f": wts[-1][1] * 9 / 5 + 32, "t": tzl(wts[-1][0], zone)}
    elif wts:
        out["old"]["wt"] = age_words(wts[-1][0], G["now"])
    ob = (rec.get("nws") or {}).get("obs")
    if ob and ok("nws") and ob.get("temp_c") is not None and hours_old(ob.get("timestamp"), G["now"]) is not None and hours_old(ob.get("timestamp"), G["now"]) <= HIDE_H["air_obs"]:
        wk = ob.get("wind_kmh")
        dirs = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")
        wd = dirs[int((ob["wind_dir"] % 360) / 22.5 + 0.5) % 16] if ob.get("wind_dir") is not None else ""
        out["air"] = {"f": ob["temp_c"] * 9 / 5 + 32, "wind": km_mi(wk) if wk is not None else None, "gust": km_mi(ob["gust_kmh"]) if ob.get("gust_kmh") is not None else None, "dir": wd, "st": ob.get("station") or "", "name": ob.get("name") or "", "mi": round(miles_between(G["lat"], G["lon"], ob["ll"][1], ob["ll"][0])) if ob.get("ll") else None, "t": tzl(parse_t(ob["timestamp"]), zone), "iso": ob["timestamp"]}
    elif ob and ok("nws") and ob.get("temp_c") is not None and ob.get("timestamp"):
        out["old"]["air"] = age_words(parse_t(ob["timestamp"]), G["now"])
    if pages:
        for x in ((rec.get("related") or {}).get("items") or []):
            pr = pages.get(x["site"])
            if x.get("relation") == "upstream" and pr and pr.get("_built") and x.get("flow") is not None and x.get("time") and (hours_old(x["time"], G["now"]) or 1e9) <= 24:
                out["up"] = {"flow": x["flow"], "name": river_at(pr["river"], pr["place"]), "url": pr["water_url"], "lag": x.get("lag_h"), "time": tzl(parse_t(x["time"]), zone) if x.get("time") else ""}
                break
    if len(fl) >= 8 and not G.get("osc"):
        for h in (1, 3, 6, 24, 168):
            wc = window_change(fl, lt, h)
            if wc:
                out["chg"][h] = wc[2]
    sgl = G["sg"]
    out["sg6"] = None
    if len(sgl) >= 8 and stage_is_ft(sgl[-1][2]):
        a6 = _at(sgl, sgl[-1][0] - datetime.timedelta(hours=6), 1800)
        out["sg6"] = (sgl[-1][1] - a6[1]) if a6 else None
    n = rec.get("nwps") or {}
    f = n.get("forecast") if ok("nwps") else None
    if f and f.get("points"):
        age = hours_old(f.get("issued"), G["now"]) if f.get("issued") else None
        pts = [x for x in fc_points(f) if x[0] >= G["now"]]
        stage = [(t_, s_) for t_, s_, _ in pts if s_ is not None]
        flow = [(t_, f_) for t_, _, f_ in pts if f_ is not None]
        gap = datum_gap(G)
        fut, unit = (stage, "ft") if stage else (flow, "cfs")
        if fut and (age is None or age <= HIDE_H["river_forecast"]):
            hi = max(fut, key=lambda x: x[1])
            near = [i for i, (_, v_) in enumerate(fut) if v_ >= hi[1] - (0.05 if unit == "ft" else 0.01 * abs(hi[1]))]
            lo_f = min(v_ for _, v_ in fut)
            depth = max(0.15 if unit == "ft" else 0.03 * abs(hi[1]), 0.25 * (hi[1] - lo_f))  # a second peak needs a valley at least a quarter as deep as the whole rise, not a wobble on a plateau
            peaks = 1 + sum(1 for a_, b_ in zip(near, near[1:]) if min(v_ for _, v_ in fut[a_:b_ + 1]) < hi[1] - depth)
            end = fut[-1]
            first_hi = near[0]
            cur = fc_cur(G, gap) if unit == "ft" else G["lv"]  # the word, the tile and its margins judge one reading
            out["fc"] = {"v": hi[1], "unit": unit, "t": tzl(hi[0], zone), "lid": n.get("lid") or "", "repeat": peaks >= 2, "issued": tzl(parse_t(f["issued"]), zone) if f.get("issued") else "at a time not stated", "age_h": age, "ago": age_words(parse_t(f["issued"]), G["now"]) if f.get("issued") else None,
                         "falls": end[1] <= hi[1] - (0.5 if unit == "ft" else 0.1 * abs(hi[1])) and (end[0] - hi[0]).total_seconds() > 6 * 3600 and peaks < 2, "end_v": end[1], "end_t": tzl(end[0], zone),
                         "swing": (lo_f, tzl(end[0], zone)) if peaks >= 2 and hi[1] - lo_f >= (0.5 if unit == "ft" else 0.1 * abs(hi[1])) else None,
                         "datum": gap, "word": fc_word([v_ for _, v_ in fut], cur, unit),
                         "flow_at": next((x[2] for x in pts if x[0] == hi[0]), None) if unit == "ft" else None,
                         "offset": _fc_offset(G, pts, unit, gap),
                         "cur": cur}
    nws = rec.get("nws") or {}
    if ok("nws") and nws.get("alerts") is not None and nws.get("fetched_at"):
        al = sorted(live_alerts(G) or [], key=alert_rank)  # NWS priority order: the banner names and colours the most serious first
        out["alerts"] = {"n": len(al), "names": [x.get("event") or "" for x in al[:3]], "col": alert_col(al), "age_h": hours_old(nws["fetched_at"], G["now"]), "ago": age_words(parse_t(nws["fetched_at"]), G["now"]), "asof": tzl(parse_t(nws["fetched_at"]), zone)}
    rn = rec.get("rain") or {}
    if ok("rfc") and (rn.get("inches") or {}).get("last_24h") is not None:
        vt = (rn.get("valid_through") or {}).get("last_24h")
        rt = vt or rn.get("fetched_at")  # the estimate's own end time, else when we fetched it
        out["rain"] = {"in": rn["inches"]["last_24h"], "to": tzl(parse_t(vt), zone) if vt else None, "age_h": hours_old(rt, G["now"]) if rt else None, "ago": age_words(parse_t(rt), G["now"]) if rt else None}
    return out



def b_camera(G):
    """USGS gaging-station camera at this site: the newest image (720 px), with the timelapse link and the HIVIS page."""
    c = G["rec"].get("cameras")
    if not c or not c.get("cams"):
        return None
    body, ages = "", []
    for x in c["cams"]:
        try:
            h = hours_old(x["taken"], G["now"])
            taken = tzl(parse_t(x["taken"]), G["zone"]) + (" (%s before this page was built)" % human_span(int(h // 24)) if h > 24 else "")
            ages.append(h)
        except (KeyError, TypeError, ValueError):
            taken = "time not stated"
        body += '<figure class="cam"><a href="%s" rel="noopener"><img src="%s" alt="USGS camera: %s" width="720" height="405" loading="lazy" decoding="async" style="max-width:100%%;height:auto"></a><figcaption>%s &middot; taken %s%s</figcaption></figure>' % (
            esc(x["page"]), esc(x["small"]), esc(x["name"]), esc(x["name"]), esc(taken), (' &middot; <a href="%s" rel="noopener">timelapse video</a>' % esc(x["timelapse"])) if x.get("timelapse") else "")
    fresh = len(ages) == len(c["cams"]) and all(h <= stale_after("camera") for h in ages)
    return block("camera", "Camera at the gauge" if fresh else "Camera at the gauge, newest image", "live" if fresh else "agency", body,
                 "Source: U.S. Geological Survey HIVIS camera (NIMS API), newest image at build time; the image file is served by USGS. Fetched %s." % esc(tzl(parse_t(c["fetched_at"]), G["zone"])), "hivis")


def _aq_site(s):
    return "not stated" if not s or s.strip().upper() in ("NEW", "N/A") else s


def _aq_where(r):
    s = _aq_site(r.get("site"))
    if r.get("county") and not re.search("[a-z]", s):  # an all-capitals site code is no place name
        s = "monitor in " + r["county"]
    if "id" not in r:  # cache from before the distance was fetched
        return s
    if not r["id"]:
        return s + " (AirNow reporting area; no single monitor named)"
    return s + ((", %d mi from the gauge" % r["mi"]) if r.get("mi") is not None else ", distance not published")


def _aq_time(r):
    if not r.get("date") or not r.get("hour"):
        return "time not stated"
    try:
        d = datetime.datetime.strptime("%s %s" % (r.get("date"), r.get("hour")), "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return "%s %s %s" % (r.get("date") or "", r.get("hour") or "", r.get("tz") or "")
    return clock(d, AQ_TZ.get(r.get("tz"), r.get("tz") or ""))


AQ_TZ = {"KST": "AKST", "KDT": "AKDT"}  # AirNow labels Alaska time 'KST' (Anchorage 2026-11-07: hour 17:00 'KST' fetched 02:56 UTC = 17:56 AKST; Korea time would be 19 h old): never print Korea's abbreviation on an Alaska page


AQI_RGB = OFFICIAL["aqi"]


def b_air_quality(G):
    """EPA AirNow NowCast AQI per pollutant at the nearest reporting site: the air a person breathes on the water today."""
    a = G["rec"].get("airnow")
    if not a or not a.get("rows"):
        return None
    def _fresh(r):
        try:
            d = datetime.datetime.strptime("%s %s" % (r.get("date"), r.get("hour")), "%Y-%m-%d %H:%M").replace(tzinfo=G["zone"])
        except (TypeError, ValueError):
            return True
        return (G["now"] - d).total_seconds() <= HIDE_H["air_quality"] * 3600
    a = dict(a, rows=[r for r in a["rows"] if _fresh(r) and isinstance(r.get("aqi"), (int, float))])  # full review: "Air quality now" from a reading 26 h old
    if not a["rows"]:
        return None
    a = dict(a, rows=[dict(r, site=r.get("site") if _aq_site(r.get("site")) != "not stated" else r.get("area")) for r in a["rows"]])  # hater r4: "MONITOR not stated" while AirNow names the reporting area
    pol = lambda r: esc(("PM2.5" if r["pollutant"] == "PM2.5" else (r["pollutant"] or "").title()) if r["pollutant"] not in ("OZONE", "PM10") else r["pollutant"].replace("OZONE", "Ozone"))
    one = len({(_aq_where(r), _aq_time(r)) for r in a["rows"]}) == 1  # phone review 2026-11-09: one monitor and time repeated on every row made 3 stacked cards; say them once
    same_t = len({_aq_time(r) for r in a["rows"]}) == 1
    rows = "".join(tr([pol(r) + ("" if one else '<br><small>%s%s</small>' % (esc(_aq_where(r)), "" if same_t else ", " + esc(_aq_time(r)))), str(r["aqi"]), esc(r["category"] or "")], right=(1,)) for r in a["rows"])  # always 3 columns; the time once when all readings share it
    rows_note = '' if one or not same_t else '<p class="src">All observed %s.</p>' % esc(_aq_time(a["rows"][0]))
    aq_tab = (('<p class="src">Monitor: %s &middot; observed %s</p>' % (esc(_aq_where(a["rows"][0])), esc(_aq_time(a["rows"][0])))) + table(["Pollutant", "AQI (of 500)", "EPA category"], rows, right=(1,))) if one else table(["Pollutant and monitor", "AQI (of 500)", "EPA category"], rows, right=(1,)) + rows_note
    worst = max(a["rows"], key=lambda r: r["aqi"] or 0)
    dot = AQI_RGB.get((worst["category"] or "").strip().lower())  # AirNow guidelines: AQI shown in the EPA's own colours (AQI technical assistance document, 2018); an unknown category gets no dot
    return block("air_quality", "Air quality now", "epa", '<p class="aq">%s%s: AQI %s of 500 (%s, EPA)</p>' % ('<i style="background:%s"></i>' % dot if dot else "", esc(worst["category"] or "Not rated"), esc(str(worst["aqi"])), esc((worst["pollutant"] or "").replace("OZONE", "Ozone"))) + aq_tab,
                 "Source: EPA AirNow NowCast AQI, reporting agency %s, nearest monitor to the gauge; preliminary data, subject to change. Fetched %s." % (esc(worst.get("agency") or "not stated"), esc(tzl(parse_t(a["fetched_at"]), G["zone"]))), "airnow")


def _ridb_name(n):
    return re.sub(r"\(([A-Za-z]{2})\)$", lambda m: "(" + m.group(1).upper() + ")", n.title()) if n.isupper() else n



def _phone(p):
    """One format for a US number ("1(406) 683-8000", "406-683-8000" are one line); anything else as listed."""
    m = re.search(r"\(?\d{3}\)?[\s.-]*\d{3}[\s.-]*\d{4}", p or "")
    d = re.sub(r"\D", "", m.group(0) if m else (p or ""))  # full review: "FOR RESERVATIONS, PLEASE CALL: 1 (877) 444-6777." on 9 cards
    d = d[1:] if len(d) == 11 and d[0] == "1" else d
    return "(%s) %s-%s" % (d[:3], d[3:6], d[6:]) if len(d) == 10 else (p or "").strip()


def b_recreation(G):
    """Recreation.gov facilities within 15 mi that list a water activity, are campgrounds, or are ramps: where a person gets on or stays by this river."""
    r = G["rec"].get("ridb")
    if not r or not r.get("sites"):
        return None
    seen, sites = set(), []
    for x in r["sites"]:  # the same site listed twice by RIDB shows once (hater 2026-10-27, Ocoee)
        k = _ridb_name(x["name"]).lower()
        if k not in seen and not any("Privately Owned" in a and "Hotel" in a for a in x.get("activities") or []):  # hater r4: "The Peabody Memphis ... Swimming"
            seen.add(k)
            sites.append(x)
    r = dict(r, sites=sites)
    r = dict(r, sites=[dict(x, phone=_phone(x.get("phone")), type=("Day-use area" if x.get("type") == "Campground" and re.search(r"(?i)picnic|day use|pavilion|shelter", x["name"]) else x.get("type"))) for x in r["sites"]])
    if not r["sites"]:
        return None  # hater r5: Memphis showed a heading with no rows after the hotel left
    r = dict(r, sites=[x for x in r["sites"] if x["mi"] <= r["radius_mi"]])  # a facility farther than the stated radius is never listed under it
    if not r["sites"]:
        return None
    said = {}  # 28 pages held 2026-11-12: sites run by one office share an address or description; the second says whose it is, never the text again
    rows = "".join(tr([_ridb_site(x, said), "%.1f mi" % x["mi"], _ridb_fee(x), esc("not listed" if (x.get("phone") or "").strip().upper() in ("", "N/A", "NA") else x["phone"])], right=(1,)) for x in r["sites"])
    shared = '<p class="src">Text that several of these sites share on Recreation.gov (an office address, a booking note) is listed once, under the first site that has it.</p>' if said.get("_dropped") else ""
    return block("recreation_sites", "Recreation sites within %d miles" % r["radius_mi"], "agency",
                 '<p>%d federal site%s within %d miles, nearest %s at %.1f mi. Fees, reservations and directions are as Recreation.gov lists them.</p>' % (len(r["sites"]), "" if len(r["sites"]) == 1 else "s", r["radius_mi"], esc(_ridb_name(r["sites"][0]["name"])), r["sites"][0]["mi"])
                 + table(["Site", "Distance", "Fees and reservations", "Phone"], rows, right=(1,)) + shared,
                 "Source: Recreation.gov Recreation Information Database (RIDB), federal sites only; state and private ramps are not in it. Fees, reservations, addresses, directions and descriptions are Recreation.gov's own words. Distances are straight-line from the gauge. Fetched %s." % esc(tzl(parse_t(r["fetched_at"]), G["zone"])), "ridb")  # was a table row that phones showed as a fake site card (hater 2026-10-27)


def _ridb_ok(t):
    """RIDB text a page can carry: check.py BANNED holds a page on a bare 'None' and on the word licence (builder jargon), so a field saying either is left out, never reworded."""
    return bool(t) and not re.search(r"(?i)licen[cs]e", t) and t.strip().strip(".").upper() not in ("NONE", "N/A", "NA", "TBD") and not re.search(r"(?i)\b(\w+) \1\b", t) and t.count("(") == t.count(")") and t.count("[") == t.count("]")  # 2026-11-12: RIDB's own 'and and', 'pavilion Pavilion' and a lone bracket held pages; such a field is left out, never rewritten  # ponytail: two of BANNED's patterns copied; import check.BANNED if a third bites


def _ridb_site(x, said=None):
    """Name (linked to its Recreation.gov page when there is one), type and agency, activities; the rest of what RIDB says behind More."""
    nm = esc(_ridb_name(x["name"]))
    h = ('<a href="%s" rel="noopener">%s</a>' % (esc(x["url"]), nm)) if str(x.get("url") or "").startswith("https://") else nm
    h += "<br><small>%s</small>" % " &middot; ".join(esc(v) for v in (x.get("type"), x.get("org")) if v)
    acts = ", ".join(x.get("water") or (x.get("activities") or [])[:3])
    h += "<br><small>%s</small>" % esc(("Activities: " + acts) if acts else "Activities not listed")
    det = [("About", x.get("about")), ("Address", x.get("address")), ("Directions", x.get("directions"))]
    said = {} if said is None else said
    out = ""
    for k, v in det:
        if not _ridb_ok(v):
            continue
        parts = [" ".join(v.split())] if k == "Address" else re.split(r"(?<=[a-z0-9)][.!?])\s+(?=[A-Z])", " ".join(v.split()))  # an address is one piece (P.O. Box split it, 2026-11-12)
        keep = []
        for sn in parts:
            key = sn.lower()
            if len(sn.split()) >= 3 and key in said:
                said["_dropped"] = True  # said once under the first site; the block notes it once
                continue
            keep.append(sn)
            said.setdefault(key, True)
        if keep:
            out += "<p><b>%s:</b> %s</p>" % (k, esc(" ".join(keep)))
    det = out
    if x.get("email"):
        det += '<p><b>Email:</b> <a href="mailto:%s">%s</a></p>' % (esc(x["email"]), esc(x["email"]))
    return h + ('<details class="tmore"><summary>More</summary>%s</details>' % det if det else "")


def _ridb_fee(x):
    """RIDB's fee text as written (or that it states none), then what it says about reservations: no verdict, no reworded price."""
    if "fee" not in x:  # a cache written before 2026-11-10 never asked: Unknown, never "not stated"
        return "Unknown"
    fee = x["fee"]  # None = stated but too long to show whole
    f = esc(fee) if _ridb_ok(fee) else "Fee not stated by Recreation.gov" if fee is not None and (not fee or fee.strip().strip(".").upper() in ("NONE", "N/A", "NA", "TBD")) else "Fees: see the site on Recreation.gov"
    if not x.get("reservable"):
        return f + "<br><small>Not listed as reservable</small>"
    u = x.get("res_url") or ""
    return f + "<br><small>%s</small>" % (('<a href="%s" rel="noopener">Reservable on Recreation.gov</a>' % esc(u)) if u.startswith("https://") else "Recreation.gov lists it as reservable")


def _tide_t(s, with_date):
    d = datetime.datetime.strptime(s, "%Y-%m-%d %H:%M")
    return clock(d, "", with_date)


def b_tides(G):
    """High and low tide predictions at the nearest NOAA station, shown on reaches whose flow cycles within the day (tidal)."""
    t = G["rec"].get("tides")
    if G.get("tables"):  # tide tables (owner decision 3): this station's own 7 days of NOAA highs and lows, not the 2-day nearest-station table
        c = G["rec"]["coops"]
        t = {"station": G["site"], "name": G["row"]["raw_name"].rsplit(",", 1)[0], "mi": 0, "fetched_at": c["fetched_at"],
             "rows": [{"t": parse_t(x[0]).astimezone(G["zone"]).strftime("%Y-%m-%d %H:%M"), "v": x[1], "type": x[2]} for x in c["hilo"]]}
    if not t or not t.get("rows") or not (G.get("tidal") or G.get("coast") or t.get("mi", 99) <= 10):  # tidal by the 12.4 h test (audit 2026-11-10 #2: a dam's daily cycle is not a tide), or a NOAA prediction station within 10 mi (Hudson at Green Island sits 2.5 mi from the Troy station below the Federal Dam)
        return None
    now_l = G["now"].astimezone(G["zone"]).strftime("%Y-%m-%d %H:%M")  # station local time; past rows dropped (hater 2026-10-27: past tides under "next two days")
    t = dict(t, rows=[r for r in t["rows"] if r["t"] >= now_l])
    if not t["rows"]:
        return None
    rows = "".join(tr([esc(_tide_t(r["t"], i == 0 or r["t"][:10] != t["rows"][i - 1]["t"][:10])), "High tide" if r["type"] == "H" else "Low tide", "%.1f ft" % (r["v"] + 0.0 if round(r["v"], 1) else 0.0)], right=(2,)) for i, r in enumerate(t["rows"]))
    near = "" if G.get("tidal") or G.get("coast") else '<p class="src">The flow at this gauge shows no tidal cycle; the table is for the nearest NOAA tide station, %.0f mi away, where the river is tidal.</p>' % t["mi"]
    stn = esc(t["name"] or t["station"])
    kind = "Tides" if G.get("tidal") else "Tides nearby"
    fa = hours_old(t.get("fetched_at"), G["now"]) if t.get("fetched_at") else None
    nd = len({r["t"][:10] for r in t["rows"]})
    if G.get("tables") and nd >= 3:
        head = "Tide table at %s, next %d days" % (stn, min(nd, 7))  # 168 h from midnight UTC: the rest of today and 7 days, the last one partly
    elif nd >= 2:
        head = "%s at %s, next two days" % (kind, stn)
    elif t["rows"][0]["t"][:10] == now_l[:10] and not (fa is not None and fa > 12):  # an old fetch cannot say "rest of today": name the date
        head = "%s at %s, rest of today" % (kind, stn)
    else:  # rows for another day than today in the gauge's zone: the heading names that day
        head = "%s for %s at %s" % (kind, _tide_t(t["rows"][0]["t"], True).rsplit(",", 1)[0], stn)
    if fa is not None and fa > 12:
        head += " (fetched %d h ago)" % fa
    return block("tides", head, "noaa", near + table(["Time (station local)", "Tide", "Height above the tide datum (MLLW)"], rows, right=(2,)),
                 "Source: NOAA National Ocean Service, CO-OPS tide predictions for station %s (%s), %sfetched %s. Predictions, not observations; the river level here also depends on flow from upstream." % (esc(t["station"]), esc(t["name"] or ""), ("%.0f mi from the gauge, " % t["mi"]) if t["mi"] >= 0.5 else "", esc(tzl(parse_t(t["fetched_at"]), G["zone"]))), "coops", amber=fa)


NWS_TZ = {"EST": -5, "EDT": -4, "CST": -6, "CDT": -5, "MST": -7, "MDT": -6, "PST": -8, "PDT": -7, "AKST": -9, "AKDT": -8, "HST": -10, "AST": -4, "SST": -11, "CHST": 10}


def nws_issued(d, t):
    """'11/13/2026' + '500 PM EST' -> aware datetime; None when NWS writes anything else (shown as NWS wrote it, with no age)."""
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", (d or "").strip()), re.fullmatch(r"(\d{1,2})(\d\d) ([AP]M) ([A-Za-z]+)", (t or "").strip())
    if not all(m) or m[1].group(4).upper() not in NWS_TZ:
        return None
    hh = int(m[1].group(1)) % 12 + (12 if m[1].group(3) == "PM" else 0)
    return datetime.datetime(int(m[0].group(3)), int(m[0].group(1)), int(m[0].group(2)), hh, int(m[1].group(2)), tzinfo=datetime.timezone(datetime.timedelta(hours=NWS_TZ[m[1].group(4).upper()])))


def b_surf(G):
    """PLAN 31, coast pages: the NWS Surf Zone Forecast for the beach zones within 15 km: rip current risk and surf height in NWS's own words, attributed.
    States: valid; valid-empty (NWS issues none here now: said, never a low risk); stale (issued over 36 h ago: age shown, amber); hidden past 72 h
    and unavailable (not read) = Unknown."""
    if not G.get("coast") or not cleared("nws"):
        return None
    s = G["rec"].get("surf")
    head = "Surf zone forecast"
    if not s:
        return block("surf", head, "official", "<p>Unknown: the National Weather Service surf zone forecast was not read in this build.</p>", "Source: National Weather Service Surf Zone Forecast.", "nws")
    src = "Source: National Weather Service Surf Zone Forecast, beach zones within 15 km of the station, read %s" % esc(tzl(parse_t(s["fetched_at"]), G["zone"]))
    rows = s.get("rows") or []
    if not rows:
        return block("surf", head, "official", "<p><b>The National Weather Service issues no surf zone forecast for this stretch of coast now.</b> Many offices issue one only in the beach season.</p>", src + ".", "nws", empty=True)
    at = nws_issued(rows[0].get("productdat"), rows[0].get("producttim"))
    age = (G["now"] - at).total_seconds() / 3600 if at else None
    if age is not None and age > 72:
        return block("surf", head, "official", "<p>Unknown: the newest National Weather Service surf zone forecast read here was issued %d days ago.</p>" % round(age / 24), src + ".", "nws")
    issued = esc(tzl(at, G["zone"])) if at else esc("%s %s" % (rows[0].get("productdat"), rows[0].get("producttim")))
    first = rows[0]
    lead = "NWS rip current risk at %s, %s: %s. Surf: %s" % (esc(first["beachname"]), esc(first["period"].lower() if first["period"] in ("Today", "Tonight", "Rest of today") else first["period"]), esc(first["rip"]), esc((first.get("surf") or "Unknown").rstrip(".") + "."))
    body = "<p><b>%s</b></p>" % lead + table(["Beach zone", "Period", "Rip current risk (NWS)", "Surf (NWS)"], "".join(tr([esc(r["beachname"]), esc(r["period"]), esc(r["rip"]), esc(r.get("surf") or "Unknown")]) for r in rows[:6]))
    return block("surf", head, "official", body, src + ", issued %s by NWS %s. Rip current risk and surf height are the National Weather Service's words. <a href=\"%s\" rel=\"noopener\">Full NWS product</a>." % (
        issued, esc((first.get("sitename") or "").replace("WFO ", "")), esc(first.get("srfprod") or "https://www.weather.gov/beach/")), "nws", amber=age)


def b_redtide(G):
    """PLAN 30, Gulf and Florida coast pages: Karenia brevis (red tide) samples within 25 km in the last 14 days (NOAA NCEI HABSOS; FWC and partners).
    States: valid (highest count and the latest sample at each site, HABSOS's own category words); valid-empty (no sample nearby: said, never 'no red
    tide'); unavailable (not read) = Unknown. Dates only: the service does not state its clock zone. Counts are cells per liter as sampled."""
    if not G.get("coast") or G["row"].get("state") not in ("FL", "AL", "MS", "TX") or not cleared("habsos"):
        return None
    r = G["rec"].get("redtide")
    head = "Red tide (Karenia brevis) samples nearby"
    src = "Source: NOAA National Centers for Environmental Information, HABSOS cell counts; samples collected by the Florida Fish and Wildlife Conservation Commission and partners"
    if not r:
        return block("redtide", head, "agency", "<p>Unknown: NOAA's red tide sample records were not read in this build.</p>", src + ".", "habsos")
    src += ", read %s. Sample dates as recorded; categories are HABSOS's own words" % esc(tzl(parse_t(r["fetched_at"]), G["zone"]))
    rows = r.get("rows") or []
    if not rows:
        return block("redtide", head, "agency", "<p><b>No red tide sample was recorded within 25 km of this station in the last 14 days.</b> No sample is not the same as no red tide.</p>", src + ".", "habsos", empty=True)
    latest = {}
    for x in sorted(rows, key=lambda x: x["date"], reverse=True):
        latest.setdefault(x["site"], x)
    top = max(rows, key=lambda x: x["count"])
    cnt = lambda c: "{:,.0f}".format(c)
    if top["count"] > 0:
        lead = "Highest red tide count within 25 km in the last 14 days: %s cells per liter (%s) at %s on %s, %.0f km away." % (cnt(top["count"]), esc(top["cat"] or "no category"), esc(top["site"]), esc(fdate(top["date"])), top["km"])
    else:
        lead = "None of the %d red tide samples within 25 km in the last 14 days found Karenia brevis cells (newest %s)." % (len(rows), esc(fdate(max(x["date"] for x in rows))))
    trs = "".join(tr([esc(x["site"]), "%.0f km" % x["km"], esc(fdate(x["date"])), cnt(x["count"]), esc(x["cat"] or "Unknown")], right=(1, 3)) for x in sorted(latest.values(), key=lambda x: x["km"])[:8])
    return block("redtide", head, "agency", "<p><b>%s</b></p>" % lead + table(["Sample site", "Distance", "Latest sample", "Cells per liter", "Category (HABSOS)"], trs, right=(1, 3)), src + ".", "habsos")


def b_fish(G):
    """PLAN 33a: fish species with records within 10 km since 2000 (GBIF, CC0 and CC BY records; common names from ITIS). States: valid; valid-empty
    (no record: said as no record, never 'no fish'); unavailable = Unknown. 'Recorded within 10 km' always: a record can be from another water nearby."""
    if not cleared("gbif"):
        return None
    f = G["rec"].get("fish")
    head = "Fish species recorded nearby"
    src = "Source: GBIF.org occurrence records (CC0 and CC BY licensed), common names from ITIS"
    if not f:
        return block("fish", head, "agency", "<p>Unknown: fish records near here were not read in this build.</p>", src + ".", "gbif")
    src += ", read %s" % esc(tzl(parse_t(f["fetched_at"]), G["zone"]))
    if not f.get("rows"):
        return block("fish", head, "agency", "<p><b>No fish record within %d km since %d is in GBIF.</b> No record is not the same as no fish.</p>" % (f["km"], f["since"]), src + ".", "gbif", empty=True)
    n = ("%d or more" % f["species"]) if f.get("capped") else "%d" % f["species"]
    nm = lambda r: esc(r[1].split(", ")[0] if r[1] else r[0])
    lead = "%s fish species have records within %d km since %d. Most recorded: %s." % (n, f["km"], f["since"], ", ".join(nm(r) for r in f["rows"][:4]))
    trs = "".join(tr([esc(r[1] or "No common name listed"), "<i>%s</i>" % esc(r[0]), "{:,}".format(r[2])], right=(2,)) for r in f["rows"])
    sets = "; ".join("%s (%s records)" % (esc(t), "{:,}".format(c)) for t, c in f.get("datasets") or [])
    return block("fish", head, "agency", "<p><b>%s</b></p>" % lead + table(["Fish (ITIS common names)", "Scientific name", "Records"], trs, right=(2,)) +
                 '<p class="src">Records come from surveys, museum collections and checked public sightings, and can be from other water within %d km. Largest sources here: %s.</p>' % (f["km"], sets or "Unknown"),
                 src + ". Counts are records, not fish caught.", "gbif")


def b_moonphase(G):
    """PLAN 32 (anglers ask for the moon; coast pages have b_moon): the next principal moon phases from the U.S. Naval Observatory, UT shown in local time.
    States: valid; unavailable (not read, or no phase ahead in the list) = Unknown. Only future phases; no 'good fishing' words."""
    if G.get("coast") or not cleared("usno"):
        return None
    m, z = G["rec"].get("moonphase") or {}, G["zone"]
    src = "Source: U.S. Naval Observatory, Astronomical Applications Department, moon phases"
    nx = [(ph, parse_t(t)) for ph, t in m.get("phases") or [] if parse_t(t) > G["now"]]
    if not nx:
        return block("moonphase", "Moon phases", "agency", "<p>Unknown: the U.S. Naval Observatory's moon phases were not read in this build.</p>", src + ".", "usno")
    full = next((t for ph, t in nx if ph == "Full Moon"), None)
    new = next((t for ph, t in nx if ph == "New Moon"), None)
    lead = "; ".join(x for x in ("Next full moon: %s" % esc(tzl(full, z)) if full else "", "next new moon: %s" % esc(tzl(new, z)) if new else "") if x)
    rows = "".join(tr([esc(ph), esc(tzl(t, z))]) for ph, t in nx[:4])
    return block("moonphase", "Moon phases", "agency", "<p><b>%s.</b></p>" % (lead[:1].upper() + lead[1:]) + table(["Phase", "Date and time"], rows),
                 src + ", read %s. USNO gives the times in UT; local time is our conversion." % esc(tzl(parse_t(m["fetched_at"]), z)), "usno")


def b_kingtide(G):
    """PLAN 29, coast pages: the highest predicted tides of the next 12 months (king tides) against NOAA's minor flood level at this station.
    States: valid (highest tides, and the ones at or above the level); valid-empty (none reach it: the gap is said); no level published (said, never
    'no flooding tides'); unavailable (Unknown: not read). Only future tides are shown, so a week-old fetch never shows a past tide as coming."""
    if not G.get("coast") or not cleared("coops"):
        return None
    f, z = G["rec"].get("floodtide") or {}, G["zone"]
    head = "Highest tides in the next 12 months"
    src = "Source: NOAA National Ocean Service, CO-OPS high tide predictions for station %s and its published flood levels" % esc(G["site"])
    fut = lambda xs: [(parse_t(t), v) for t, v in xs or [] if parse_t(t) > G["now"]]
    top, over = sorted(fut(f.get("top")), key=lambda x: -x[1]), fut(f.get("over"))
    if not top:
        return block("kingtide", head, "noaa", "<p>Unknown: NOAA's 12-month tide predictions for this station were not read in this build.</p>", src + ".", "coops")
    lv = f.get("level")
    whose = "NOAA's minor high-tide flooding level" if f.get("who") == "nos" else "the National Weather Service's minor flood level"
    when = lambda t: esc(tzl(t, z))
    if lv is None:
        lead = "The highest predicted tide in the next 12 months is %.1f ft on %s. NOAA publishes no flood level for this station." % (top[0][1], when(top[0][0]))
    elif over:
        lead = "%d predicted high %s in the next 12 months %s %s (%.1f ft above MLLW); the first is %.1f ft on %s." % (
            len(over), "tide" if len(over) == 1 else "tides", "reaches" if len(over) == 1 else "reach", whose, lv, over[0][1], when(over[0][0]))
    else:
        lead = "The highest predicted tide in the next 12 months is %.1f ft on %s, %.1f ft below %s (%.1f ft above MLLW)." % (top[0][1], when(top[0][0]), lv - top[0][1], whose, lv)
    gap = lambda v: "Unknown" if lv is None else ("%.1f ft above" % (v - lv) if v > lv else "at the level" if v == lv else "%.1f ft below" % (lv - v))
    rows = "".join(tr([when(t), "%.1f ft" % v, gap(v)], right=(1,)) for t, v in (over or sorted(top))[:5])  # the tides at the level, in date order, prove the lead; else the highest five
    return block("kingtide", head, "noaa", "<p><b>%s</b></p>" % lead + table(["Date and time", "Predicted high tide (above MLLW)", "Compared with the flood level"], rows, right=(1,)),
                 src + ", read %s. NOAA gives the flood level on the station datum; moving it to MLLW with NOAA's published datums is our calculation. Predictions include no wind, air pressure or river flow, which can raise the water above them." % esc(tzl(parse_t(f["fetched_at"]), z)), "coops")


def b_wpc(G):
    """WPC flood and excessive rainfall outlooks that cover the gauge point, and recent NWS flood reports within 50 miles. Hidden when there is nothing to show."""
    w = G["rec"].get("wpc")
    if not w:
        return None
    age = hours_old(w.get("fetched_at"), G["now"]) if w.get("fetched_at") else None
    if age is None or age > HIDE_H["wpc_outlooks"]:
        return None
    zone = G["zone"]
    body = ""
    if w.get("outlooks"):
        def loc(s_):
            """WPC gives either an ISO UTC time or a bare MM/DD/YYYY date: times show in the gauge's zone, dates stay dates."""
            if not s_:
                return "–"
            try:
                if "T" in s_ or " " in s_:  # ISO with Z, or 'YYYY-MM-DD HH:MM:SS' (both UTC; the ERO valid times are 12:00 UTC)
                    t_ = parse_t(s_.replace("Z", "+00:00").replace(" ", "T"))
                    return tzl(t_ if t_.tzinfo else t_.replace(tzinfo=datetime.timezone.utc), zone)
                return datetime.datetime.strptime(s_, "%m/%d/%Y").strftime("%b %d, %Y").replace(" 0", " ")
            except ValueError:
                return s_
        rows = "".join(tr([esc(o["name"]), esc((o.get("category") or "").title()), esc(loc(o["issued"])), "%s to %s" % (esc(loc(o["start"])), esc(loc(o["end"])))]) for o in w["outlooks"])
        ocards = [card(esc(o["name"]), esc((o.get("category") or "–").title()), "issued %s &middot; valid %s to %s" % (esc(loc(o["issued"])), esc(loc(o["start"])), esc(loc(o["end"])))) for o in w["outlooks"]]
        body += "<h3>Outlooks covering this location</h3>" + rail(ocards, "Flood outlooks covering this location") + more("Outlooks as a table", table(["Outlook", "Category", "Issued", "Valid"], rows))
    if w.get("reports"):
        rows = "".join(tr([esc(tzl(parse_t(r["t"]), zone)) if r.get("t") else "–", esc(r["type"] or ""), esc("%s, %s" % (lsr_where(r["where"]), r["state"]) if r["where"] else (r["state"] or "")), esc(r["remarks"] or "–")]) for r in w["reports"])
        rcards = [card(esc(r["type"] or "Report"), esc("%s, %s" % (lsr_where(r["where"]), r["state"]) if r["where"] else (r["state"] or "–")), esc(tzl(parse_t(r["t"]), zone)) if r.get("t") else "") for r in w["reports"][:6]]
        body += "<h3>Flood reports within 50 miles, last 72 hours (%d)</h3>" % len(w["reports"]) + rail(rcards, "Flood reports within 50 miles") + more(("All %d reports with the text as received" if len(w["reports"]) != 1 else "The %d report with the text as received") % len(w["reports"]), table(["Reported", "Type", "Location", "Report as received"], rows))
    if not body:
        return None
    out_b = block("wpc_outlooks", "Flood outlooks and reports", "official", body,
                  "Source: NOAA Weather Prediction Center significant river flood outlook and excessive rainfall outlooks (a point inside a published area), and National Weather Service local storm reports (preliminary, unverified reports from trained spotters, emergency managers and the public), fetched %s. An area is regional: it does not say this gauge will flood, and a report nearby may not concern this river." % esc(tzl(parse_t(w["fetched_at"]), zone)), "nws")
    return out_b


def wy_of(r):
    """USGS water year of a peak row (Oct 1 to Sep 30, named for the year it ends in)."""
    return int(r[0][:4]) + (1 if r[0][5:7] >= "10" else 0)


def stage_years(G):
    """(peak rows with a usable stage, NWS flood categories, nwps record), or None: the one rule for the gauge page block and /research/flood-stage-years/."""
    n = G["rec"].get("nwps") or {}
    p = G["rec"].get("peaks")
    cats = n.get("categories") or {}
    if not (SOURCES["nwps"]["status"] in ("quoted", "owner-permission") and p and "minor" in cats and stage_pair(G)) or datum_gap(G):
        return None
    rows = [r for r in p["rows"] if r[2] is not None and (not r[3] or r[3].replace(" ", "") == "['ESTIMATED']")] if all(len(r) > 3 for r in p["rows"]) else []  # any other USGS qualifier (different datum, backwater, not the annual maximum) can misstate the peak stage
    drop = DROP | {"MAXDAILYMEAN"}  # lib/common: one code list; peer review 2026-11-12 #1: USGS codes HISTORIC on the flow row only; a historic stage (Louisville 1832) entered 'X of Y years'
    rows = [r for r in rows if len(r) < 5 or not (set(str(r[4] or "").split()) & drop)]
    dd = [r[0] for r in p["rows"] if r[3] and "DIFFDATUM" in r[3]]
    if dd:  # stages before the last datum change can sit on another zero point: only the years after it count
        rows = [r for r in rows if r[0] > max(dd)]
    wy = {}
    for r in rows:  # PLAN 17: a water year counts once, at its highest stage ('X of Y years' counted secondary peaks as years)
        y = wy_of(r)
        if y not in wy or r[2] > wy[y][2]:
            wy[y] = r
    rows = [wy[y] for y in sorted(wy)]
    return (rows, cats, n) if len(rows) >= 10 else None


def b_stage_years(G):
    """Years whose annual peak stage reached each NWS flood category. Shown only when USGS and NWS stages are on the same datum (datum_gap finds no gap between two comparable readings) and the NWS publishes flood stages."""
    got = stage_years(G)
    if not got:
        return None
    rows, cats, n = got
    out = ""
    for k in ("minor", "moderate", "major"):
        if k in cats:
            out += tr(["%s flood stage" % k.capitalize(), "%.1f ft" % cats[k], "%d of %d years had a peak at or above it" % (sum(1 for r in rows if r[2] >= cats[k]), len(rows))], right=(1, 2))
    out_b = block("flood_stage_years", "Annual peaks that reached flood stage", "hist", table(["NWS category", "Stage", "Annual peaks"], out, right=(1, 2)),
                 "Source: USGS annual peak gage heights (%d water years with a recorded peak stage, water years %d to %d, the highest stage of each; peaks that USGS marks with any stage qualifier other than estimated, or as historic, a daily mean or a dam failure, are left out%s) compared with National Weather Service flood stages for forecast point %s. Shown because the USGS and NWS stage readings agree within %.1f ft. Older stages can be on an older gauge datum." % (
                     len(rows), wy_of(rows[0]), wy_of(rows[-1]), "; only years after USGS's last change of gauge datum count" if any(r[3] and "DIFFDATUM" in r[3] for r in (G["rec"].get("peaks") or {}).get("rows") or []) else "", esc(n.get("lid") or ""), DATUM_TOL_FT), "usgs")
    out_b["also"] = ["nwps"]
    return out_b


def b_floodfreq(G):
    f = G["rec"].get("floodfreq")
    if not f or not f.get("rows") or f.get("conflict"):
        return None  # regulated gauges show with USGS's own caveat (2026-10-26: hiding them withheld published statistics)
    has_ci = any(r.get("lo") is not None and r.get("hi") is not None for r in f["rows"])
    rows = "".join(tr(["%s%%" % ("%g" % r["aep"]), "%s years" % "{:,g}".format(round(100 / r["aep"], 1)), "%s cfs" % fmtc(r["q"])]
                      + ([("%s to %s cfs" % (fmtc(r["lo"]), fmtc(r["hi"]))) if r.get("lo") is not None and r.get("hi") is not None else "–"] if has_ci else []), right=(2, 3)) for r in f["rows"] if r["aep"] <= 50)
    if not rows:
        return None
    _url = re.match(r"https?://\S+?(?=https?://|$)", f.get("url") or "")  # StreamStats sends "null" or the same URL twice run together
    rec = ("record %s%s" % (esc(f["range"]), (", %s years" % fmt(f["years"])) if f.get("years") else "")) if f.get("range") else "record years not stated"
    return block("flood_frequency", "Flood frequency of peak flows", "hist", table(["Chance in any year", "Average spacing", "Peak flow"] + (["Confidence interval, as published"] if has_ci else []), rows, right=(2, 3)),
                 "Source: USGS StreamStats gage statistics (peak-flow statistics, annual exceedance probability), %s. %s. Long-run statistics, not a forecast or a schedule.%s Fetched %s." % (
                     rec, esc((f.get("citation") or "citation not stated").rstrip(". ")) + ((" " + esc(_url.group(0))) if _url else ""),
                     " USGS marks this gauge as regulated (dams or diversions upstream change its flow)." if f.get("regulated") else "", esc(tzl(parse_t(f["fetched_at"]), G["zone"]))), "usgs")


def b_flowdur(G):
    if G.get("lake"):  # phone review 2026-11-07 (Lake Champlain): a lake page has no flow; USGS flow-duration rows for the outlet read as the lake's
        return None
    f = G["rec"].get("floodfreq") or {}
    want = (5, 10, 25, 50, 75, 90, 95)
    d = [r for r in f.get("dur") or [] if r["p"] in want]
    if len(d) < 4:
        return None
    rows = "".join(tr(["Flow is at least %s cfs" % fmtc(r["q"]), "on %g%% of all days on record" % r["p"]]) for r in d)
    rng = next((r["range"] for r in d if r.get("range")), "")
    yrs = re.findall(r"\d{4}", rng)
    return block("flow_duration", "How often the flow reaches each level" + ((", %s to %s" % (yrs[0], yrs[-1])) if len(yrs) >= 2 else " (USGS, years not stated)"), "hist", table(["Flow level", "How often"], rows),
                 "Source: USGS StreamStats gage statistics (flow-duration statistics)%s. The flow equalled or exceeded on that share of days over the period.%s Fetched %s." % (
                     (", " + esc(rng.replace(" ", " to "))) if rng else "", " USGS marks this gauge as regulated." if f.get("regulated") else "", esc(tzl(parse_t(f["fetched_at"]), G["zone"]))), "usgs")


SEASONS = {"JFM": "January to March", "FMA": "February to April", "MAM": "March to May", "AMJ": "April to June", "MJJ": "May to July", "JJA": "June to August", "JAS": "July to September", "ASO": "August to October",
           "SON": "September to November", "OND": "October to December", "NDJ": "November to January", "DJF": "December to February"}


def _chance(v):
    if isinstance(v, (int, float)):
        return "%.0f%%" % (v * 100)
    s = str(v).strip()
    try:
        return ("less than %.0f%%" % (float(s.lstrip("<").strip()) * 100)) if s.startswith("<") else "%.0f%%" % (float(s) * 100)
    except ValueError:
        return esc(s)


def lro_ended(G):
    """The produced date (text) of a long-range flood outlook whose three-month period ended before today at the gauge; None when there is none, when it is current, or when its period cannot be worked out (then it stays shown)."""
    lro = (G["rec"].get("nwps") or {}).get("lro")
    if not isinstance(lro, dict) or not any(lro.get(k) is not None for k in ("minorCS", "moderateCS", "majorCS")):
        return None
    try:
        pt = datetime.date.fromisoformat(str(lro["producedTime"])[:10])
        s0 = list(SEASONS).index(str(lro.get("interval") or "").upper()) + 1  # SEASONS is in order of start month
    except (KeyError, ValueError):
        return None
    for y0 in (pt.year - 1, pt.year, pt.year + 1):  # the first occurrence of the period that had not ended when the outlook was produced
        end = datetime.date(y0 + (s0 + 2) // 12, (s0 + 2) % 12 + 1, 1) - datetime.timedelta(days=1)  # last day of its third month
        if end >= pt:
            break
    return fdate(pt.isoformat()) if end < G["now"].astimezone(G["zone"]).date() else None


def b_flood_outlook(G):
    n = G["rec"].get("nwps") or {}
    lro = n.get("lro")
    if not lro or not any(lro.get(k) is not None for k in ("minorCS", "moderateCS", "majorCS")) or lro_ended(G):
        return None
    period = SEASONS.get(str(lro.get("interval") or "").upper())
    rows = "".join(tr([lab, _chance(lro[k])], right=(1,)) for k, lab in (("minorCS", "Minor flooding"), ("moderateCS", "Moderate flooding"), ("majorCS", "Major flooding")) if lro.get(k) is not None)
    when = (" produced %s" % fdate(str(lro["producedTime"])[:10])) if lro.get("producedTime") else ""
    _od = (G["ldate"] - datetime.date.fromisoformat(str(lro["producedTime"])[:10])).days if lro.get("producedTime") else None
    _old = ('<p class="src">The NWS produced this outlook %d days ago, on %s, and has not published a newer one for this point.</p>' % (_od, esc(fdate(str(lro["producedTime"])[:10])))) if _od is not None and _od > 120 else ""
    return block("flood_outlook", "Long-range flood outlook%s" % ((", " + period) if period else ""), "official", _old + table(["Category", "Chance at this forecast point"], rows, right=(1,)),
                 "Source: National Weather Service long-range river flood outlook for forecast point %s,%s; the published chance of flooding in each category during the outlook period. Fetched %s." % (esc(n.get("lid") or ""), when, esc(tzl(parse_t(n["fetched_at"]), G["zone"]))), "nwps")


def b_official_marks(G):
    """The agency's own marks for a gauge outside the US, or for Canada monthly means, against today."""
    f = G["feed"]
    if not f.get("marks"):
        return None
    from lib.world import MARKS, fmt_level, to_ft
    u = f["unit"]
    now = G["sg"][-1][1] * (30.48 if u == "cm" else 0.3048)
    when = f.get("mark_dates") or {}
    rows = "".join(tr([lab + ((", %s" % esc(fdate(when[k]))) if when.get(k) else ""), ("%s (%.1f ft)" % (fmt_level(f["marks"][k], u), to_ft(f["marks"][k], u))).replace(" ", " "), ("%+.0f cm" if u == "cm" else "%+.2f m") % (now - f["marks"][k])], right=(1, 2)) for k, lab in sorted(MARKS, key=lambda m: -(f["marks"].get(m[0]) or 0)) if f["marks"].get(k) is not None)
    return block("official_marks", "How today compares", "agency", table(["Mark", "Level", "Today against it"], rows, right=(1, 2)), "Source: %s, %s." % (f["api"], f["name"]), f["src"])


def b_also(G):
    """What else the agency measures at this gauge right now: flow, water temperature, air temperature."""
    f = G["feed"]
    words = {"Q": "Flow", "WT": "Water temperature", "LT": "Air temperature at the gauge (the weather tile is the nearest weather station)", "DFH": "Clearance under the bridge", "VA": "Flow speed", "VM": "Flow speed", "LF": "Conductivity", "PH": "pH", "O2": "Oxygen", "TR": "Turbidity"}
    own = lambda v: (", %s" % esc(tzl(parse_t(v[3]), G["zone"]))) if len(v) > 3 and v[3] and G["sg"] and parse_t(v[3]) != G["sg"][-1][0] else ""  # a reading of another time than the level names its own time, never the level's
    rows = "".join(tr([words.get(k, esc(v[2])) + own(v), "%s %s" % (fmt(v[0]), esc(v[1] or ""))], right=(1,)) for k, v in sorted(f.get("also", {}).items()) if isinstance(v[0], (int, float)))
    if f.get("ship") in ("low", "normal", "high"):
        rows += tr(["Against the agency's lowest and highest shipping levels (not a sailing decision)", {"low": "Below the lowest", "normal": "Between them", "high": "Above the highest"}[f["ship"]]], right=(1,))  # "Normal" here sat beside a headline "Low" against mean low water (UI review 2026-11-04)
    return block("also_measured", "Also measured here now", "agency", table(["Measure", "Latest"], rows, right=(1,)), "Source: %s, %s, with the reading at %s." % (f["api"], f["name"], esc(G["obs"])), f["src"]) if rows else None


def b_along(G):
    """Nearest gauges up and down this river, with their readings."""
    f = G["feed"]
    if not f.get("along"):
        return None
    rows = "".join(tr([w, ('<a href="%s">%s</a>' % (u, esc(n))) if u else esc(n), cm, c if c is not None else "–", lab], right=(2, 3)) for w, n, cm, c, lab, u in f["along"])
    return block("along_river", "Other gauges nearby" if f["along"][0][0] == "Nearby" else "Along the river", "agency", table(["Where", "Gauge", "Level", "24 h change", "Label"], rows, right=(2, 3)), "Source: %s, %s." % (f["api"], f["name"]), f["src"])


def b_world_about(G):
    """Station facts from the agency's own record: number, its name for the gauge, river kilometre, record length, position."""
    f = G["feed"]
    if len(f.get("about") or ()) < 2:
        return None
    return block("about_gauge", "About this gauge", "agency", table(["Fact", "Value"], "".join(tr([esc(k), ('<a href="https://www.openstreetmap.org/?mlat=%s&amp;mlon=%s#map=14/%s/%s" rel="noopener" target="_blank">%s, on OpenStreetMap</a>' % (tuple(v.split(", ")) * 2 + (esc(v),))) if k == "Coordinates" else esc(v)]) for k, v in f["about"])), "Source: %s station record, %s." % (esc(f["api"]), esc(f["name"])), f["src"])


def b_world_rate(G):
    """Level change over 1 to 24 hours and the week's highest and lowest, from the agency's own readings; our arithmetic, said as ours (the US page's rate of change, 0 of 37 world pages had it 2026-11-04)."""
    f, sg = G["feed"], G["sg"]
    if len(sg) < 8:
        return None
    from lib.world import fmt_level
    u = f["unit"]
    k = 30.48 if u == "cm" else 0.3048  # the chart series is in feet; back to the agency's unit
    lv = lambda ft: fmt_level(ft * k, u)
    ch = lambda d: ("%+.0f cm" if u == "cm" else "%+.2f m") % (d * k)
    t1, v1 = sg[-1][0], sg[-1][1]
    rows = ""
    for h in (1, 3, 6, 12, 24):
        want = t1 - datetime.timedelta(hours=h)
        past = [x for x in sg if x[0] <= want]
        if past and (want - past[-1][0]).total_seconds() <= 3 * 3600:  # a gap in the feed is never bridged by a reading hours older
            rows += tr(["Last %d h" % h, lv(past[-1][1]), ch(v1 - past[-1][1])], right=(1, 2))
    if not rows:
        return None
    week = [x for x in sg if x[0] >= t1 - datetime.timedelta(days=7)]
    hi, lo = max(week, key=lambda x: x[1]), min(week, key=lambda x: x[1])
    ext = tr(["Highest in 7 days, %s" % esc(tzl(hi[0], G["zone"])), lv(hi[1]), ch(v1 - hi[1])], right=(1, 2)) + tr(["Lowest in 7 days, %s" % esc(tzl(lo[0], G["zone"])), lv(lo[1]), ch(v1 - lo[1])], right=(1, 2))
    return block("rate_of_change", "How fast the level is changing", "calc", table(["Compared with", "Level then", "Change to now"], rows + ext, right=(1, 2)),
                 "Source: %s readings, %s; the changes are our arithmetic on them." % (esc(f["api"]), esc(f["name"])), f["src"])


def b_world_near(G):
    """Up to five gauges on other rivers at any distance, nearest first, each with its latest reading and a link: a reader whose river is quiet checks the next one over (the US page has had this since 2026-10-21).
    The heading says 'Nearby' only when every one is within 100 km; past that it would be false."""
    f = G["feed"]
    if not f.get("near"):
        return None
    rows = "".join(tr(['<a href="%s">%s</a>' % (u, esc(n)), "%d km" % k, lev or "–", lab], right=(1, 2)) for k, n, u, lev, lab in f["near"])
    return block("nearby_gauges", "Nearby gauges on other rivers" if all(x[0] <= 100 for x in f["near"]) else "Other gauges on this site, nearest first", "agency", table(["Gauge", "Distance", "Level", "Label"], rows, right=(1, 2)), "Source: each gauge's agency, latest reading as on that gauge's page; distance in a straight line.", f["src"])


def b_world_forecast(G):
    """The official river forecast where the agency publishes one: forecast and estimate kept apart, as it marks them."""
    f = G["feed"]
    c = f.get("fc") or {}
    from lib.world import fmt_level, to_ft
    pts = [p for p in c.get("pts") or [] if parse_t(p[0]) >= G["now"]]
    age = hours_old(c.get("at"), G["now"]) if c.get("at") else None
    if not pts or age is None or age > HIDE_H["river_forecast"]:
        return None
    rows = "".join(tr([esc(tzl(parse_t(t), G["zone"])), ("%s (%.1f ft)" % (fmt_level(v, f["unit"]), to_ft(v, f["unit"]))).replace(" ", " "), "Estimate" if kind == "estimate" else "Forecast"], right=(1,)) for t, v, kind in [p for i, p in enumerate(pts) if i % 6 == 0 or p is max(pts, key=lambda x: x[1])])
    return block("river_forecast", "River forecast", "official", table(["Time", "Level", "Type"], rows, right=(1,)), "Source: Federal Institute of Hydrology (BfG) through %s, issued %s. Estimates are less certain than forecasts." % (f["api"], esc(tzl(parse_t(c["at"]), G["zone"]))), f["src"], amber=age)


def b_world_aq(G):
    """Air quality at the nearest official station, in the agency's own index."""
    f = G["feed"]
    a = f.get("aq")
    age = hours_old(a["t"], G["now"]) if a else None
    if not a or age is None or age > HIDE_H["air_quality"]:
        return None
    return block("air_quality", "Air quality near the river", "official", table(["Station", "Index", "Distance"], tr([esc(a["place"]), esc(a["value"]), "%d km" % a["km"]], right=(1, 2)), right=(1, 2)), "Source: %s, %s, measured %s." % (esc(a["src"]), esc(a["scale"]), esc(tzl(parse_t(a["t"]), G["zone"]))), "uba" if f["src"] == "pegelonline" else f["src"], amber=age)


def b_world_links(G):
    """Where to check this gauge at the agency itself."""
    return block("official_links", "Official pages for this gauge", "agency", '<ul class="olinks">%s</ul>' % "".join('<li><a href="%s" rel="noopener" target="_blank">%s</a></li>' % (esc(u), esc(t)) for t, u in G["feed"]["links"]), "Source: links to the agencies that publish the data on this page; they open in a new tab.", G["feed"]["src"])


def b_world_flow(G):
    """Flow over the last days, where the gauge publishes it."""
    from lib import ui
    f = G["feed"]
    pts = f.get("flow") or []
    if len(pts) < 8:
        return None
    v = [p[1] for p in pts]
    return block("flow_chart", "Flow, last 7 days", "agency", ui.spark(v, 300, 60) + table(["Measure", "Flow"], "".join(tr([a, "%s m³/s" % fmt(b)], right=(1,)) for a, b in (("Latest, %s" % esc(tzl(parse_t(pts[-1][0]), G["zone"])), v[-1]), ("Highest", max(v)), ("Lowest", min(v)))), right=(1,)), "Source: %s, %s." % (f["api"], f["name"]), f["src"])


def b_world_wt30(G):
    """Germany keeps 30 days of water temperature: the range a swimmer or paddler has seen this month."""
    f, w = G["feed"], G["feed"].get("wt30")
    if not w or hours_old(w["last"], G["now"]) > 72:
        return None
    return block("water_temp_recent", "Water temperature, last 30 days", "agency", table(["Measure", "Temperature"], tr(["Lowest", "%.1f °C" % w["low"]], right=(1,)) + tr(["Highest", "%.1f °C" % w["high"]], right=(1,)), right=(1,)), "Source: %s, %s, from %s to %s." % (f["api"], f["name"], esc(w["first"][:10]), esc(w["last"][:10])), f["src"])


def b_world_rain(G):
    """DWD's forecast rain, as the 24 h totals it publishes."""
    r = (G["rec"].get("nws") or {}).get("rain_days") or {}
    days = [d for d in r.get("days") or [] if parse_t(d[0]) >= G["now"]]
    if not days or hours_old(r.get("updated"), G["now"]) > HIDE_H["forecast_rain_totals"]:
        return None
    rows = "".join(tr(["24 hours to %s" % esc(tzl(parse_t(t), G["zone"])), "%.1f mm" % mm], right=(1,)) for t, mm in days)
    return block("forecast_rain_totals", "Forecast rain totals", "official", table(["Period", "Forecast rain"], rows, right=(1,)), "Source: Deutscher Wetterdienst, MOSMIX forecast for the nearest forecast station, issued %s. A forecast, not a measurement." % esc(tzl(parse_t(r["updated"]), G["zone"])), "dwd")


def b_world_normals(G):
    """The official climate normal for each month at the nearest climate station."""
    f, n = G["feed"], G["feed"].get("normals")
    if not n or not n.get("temp"):
        return None
    now = G["ldate"].month
    rows = "".join(tr([("<b>%s</b>" if m == now else "%s") % datetime.date(2001, m, 1).strftime("%B"), "%.1f °C" % n["temp"][str(m)] if str(m) in n["temp"] else "–", "%.0f mm" % n["rain"][str(m)] if str(m) in n.get("rain", {}) else "–"], right=(1, 2)) for m in range(1, 13))
    return block("climate_normals", "Climate normals by month", "agency", table(["Month", "Mean temperature", "Precipitation"], rows, right=(1, 2)), "Source: %s, climate normals %s, station %s, %d km from the gauge." % (f["normals_by"], esc(n["period"]), esc(n["place"]), n["km"]), f["normals_src"])


DROUGHT_WORDS = ("D0 Abnormally Dry", "D1 Moderate Drought", "D2 Severe Drought", "D3 Extreme Drought", "D4 Exceptional Drought")


def b_world_drought(G):
    """The Canadian Drought Monitor class at the gauge, on the newest monthly map; hidden once the map is over 75 days old."""
    f = G["feed"]
    m = f.get("drought_map")
    if not m:
        return None
    y, mo = 2000 + int(m[:2]), int(m[2:])
    if (G["ldate"] - datetime.date(y, mo, 1)).days > 105:
        return None
    d = f.get("drought")
    word = DROUGHT_WORDS[d] if d is not None else "Not in a mapped drought area"
    return block("drought_monitor", "Canadian Drought Monitor", "agency", table(["Map", "At this gauge"], tr([datetime.date(y, mo, 1).strftime("%B %Y"), esc(word)]), right=()), "Source: Agriculture and Agri-Food Canada, Canadian Drought Monitor, monthly map.", "aafc")


def b_world_history(G):
    """Today against every year on record: this calendar date, all days, and recent years."""
    f = G["feed"]
    if not f.get("deciles") and not f.get("days") and not f.get("years"):  # Canada's yearly highs and lows stand alone: 6 of 8 Canadian pages hid them for want of daily history (2026-11-04)
        return None
    from lib.world import fmt_level
    u, now = f["unit"], G["sg"][-1][1] * 0.3048
    d = (f.get("days") or {}).get(G["ldate"].strftime("%m-%d"))
    rows = tr(["Today", fmt_level(now, u)], right=(1,))
    if d:
        rows += "".join(tr(["%s, this date in %d years" % (a, d[3]), fmt_level(b, u)], right=(1,)) for a, b in (("Lowest", d[0]), ("Median", d[1]), ("Highest", d[2])) if b is not None)  # England publishes daily lows and highs, no mean: no median
    body = table(["Measure", "Level"], rows, right=(1,))
    if f.get("deciles"):
        body += '<p class="src">Today is above about %d%% of %d years of daily means.</p>' % (10 * sum(1 for x in f["deciles"][1:] if now >= x), f.get("day_years") or 0)
    if f.get("years"):
        body += table(["Year", "Highest", "Date", "Lowest", "Date"], "".join(tr([str(y), fmt_level(hi, u), esc((hd or "")[:10]), fmt_level(lo, u), esc((ld or "")[:10])], right=(1, 3)) for y, hi, hd, lo, ld in reversed(f["years"])), right=(1, 3))
    return block("world_history", "How today compares with past years", "agency", body, f.get("hist_line") or "Source: %s, %s, daily means and annual statistics. Our calculation from those records; published records end before this year." % (f["api"], f["name"]), f.get("hist_src") or f["src"])


def b_world_peaks(G):
    """Canada's yearly instantaneous peak level (HYDAT annual peaks): the US annual_peaks question, answered from the agency's own archive."""
    f = G["feed"]
    if not f.get("peaks"):
        return None
    from lib.world import fmt_level
    rows = "".join(tr([str(y), fmt_level(v, f["unit"]), esc(d)], right=(1,)) for y, v, d in reversed(f["peaks"]))
    return block("annual_peaks", "Highest level each year", "agency", table(["Year", "Peak level", "Date"], rows, right=(1,)),
                 "Source: %s, %s, annual instantaneous peaks (HYDAT), last %d years on file; peaks the agency marks with a data symbol are left out." % (f["api"], f["name"], len(f["peaks"])), f["src"])


def lc_day(G):
    """(date, elevation ft, storage acre-ft) from Reclamation's Lower Colorado table for the day of the newest RISE reading, or None. Both are Reclamation's own
    daily numbers, so the row is the day whose elevation equals RISE's newest (Nov 4 1,039.29 = 1,039.29); a time-zone date guess once picked Nov 3."""
    m = G["rec"].get("usbr_lc")
    if not G.get("lake") or not m or not m.get("days") or not G.get("sg") or not cleared("usbr"):
        return None
    v_ = G["sg"][-1][1]
    day_ = max((d for d, x in m["days"].items() if isinstance(x, list) and len(x) >= 2 and isinstance(x[0], (int, float)) and isinstance(x[1], (int, float)) and abs(x[0] - v_) <= 0.02), default=None)  # break test 2026-11-07: an empty row crashed the page
    if not day_:  # the table was read before Reclamation added the day RISE already has (fetched 11:27 UTC, Nov 8 row missing): its own newest row, with its own date
        day_ = max((d for d, x in m["days"].items() if isinstance(x, list) and len(x) >= 2 and isinstance(x[0], (int, float)) and isinstance(x[1], (int, float))), default=None)
        if day_ and abs(m["days"][day_][0] - v_) > 0.5:  # Mead moves about 0.1 ft a day; a bigger gap is another lake or datum: hidden, never guessed
            day_ = None
    return (day_, m["days"][day_][0], m["days"][day_][1]) if day_ else None


def usace_full(G):
    """(full pool ft, datum, USACE estimate?, latest - full) for a USGS lake gauge whose datum USACE also publishes, or None. PLAN 9a.
    The gauge's own datum decides (00062 at 0 ft above NAVD88 or NGVD29, 62614 NGVD29, 62615 NAVD88); any other datum, or a gap over 30 ft
    (another project or a scale mismatch), shows nothing: a full-pool number on the wrong datum is a wrong number."""
    p = G["rec"].get("usace_pool")
    if not G.get("lake") or not p or not G.get("sg") or not cleared("usace_cwms"):
        return None
    loc = ((G["rec"].get("meta") or {}).get("loc")) or {}
    vd = str(loc.get("vertical_datum") or "").replace(" ", "").upper()
    datum = {"62614": "NGVD29", "62615": "NAVD88"}.get(G["lake"]) or (vd if G["lake"] == "00062" and vd in ("NAVD88", "NGVD29") and loc.get("altitude") is not None and abs(float(loc["altitude"])) < 0.05 else None)  # 0.0 ft is a real altitude (falsy-zero caught by the fixture)
    full = (p.get(datum) or {}) if datum else {}
    if full.get("ft") is None or abs(G["sg"][-1][1] - full["ft"]) > 30:
        return None
    return full["ft"], datum, bool(full.get("estimated")), G["sg"][-1][1] - full["ft"]


def b_reservoir(G):
    """How full a reservoir is, on the operator's or state's own basis (plan 2026-11-05 step 3). Texas: TWDB's daily estimate, whose percent is
    conservation storage / conservation capacity; a percent is never shown without that basis named. No source for this lake: no block."""
    ca = cdec_avg(G)
    if G.get("lake") and ca and cleared("cdec"):  # CDEC lake: capacity and 1991-2020 monthly average from CDEC's reservoir profile; both percents are our calculation, said so
        c, v, t_, avg, mon = ca["c"], ca["v"], ca["t"], ca["avg"], ca["mon"]
        rows = "".join(tr([a, b], right=(1,)) for a, b in (
            ("Storage now (CDEC)", "{:,.0f} acre-ft".format(v)), ("Capacity (CDEC)", "{:,.0f} acre-ft".format(c["cap_af"])), ("Percent of capacity (our calculation)", ca["pct_cap"]),
            ("%s average storage, %s-%s (CDEC)" % (mon, c["avg_from"], c["avg_to"]), "{:,.0f} acre-ft".format(avg) if avg else "Unknown"), ("Percent of the %s average (our calculation)" % mon, ca["pct_avg"])))
        return block("reservoir", "How full the reservoir is", "agency", table(["Measure", esc(tzl(t_, G["zone"]))], rows, right=(1,)),
                     "Source: California Data Exchange Center reservoir profile for station %s (capacity, %s-%s monthly averages, read %s) and its hourly storage. The two percents are our calculation: storage divided by CDEC's capacity, and by CDEC's average for the month." % (esc(G.get("agy_st") or ""), c["avg_from"], c["avg_to"], esc(fdate(c["fetched_at"][:10]))), "cdec")
    uf = usace_full(G)
    if uf:  # PLAN 9a: USACE's normal full pool (top of conservation; it moves with the season)
        ft, dat, est, gap = uf
        lead = '<p class="lead">%.2f ft %s full pool today (US Army Corps of Engineers).</p>' % (abs(gap), "below" if gap < 0 else "above")
        rows = "".join(tr([a, b], right=(1,)) for a, b in (("Full pool today: USACE top of conservation, ft %s%s" % (dat, ", USACE's own estimate" if est else ""), "{:,.2f} ft".format(ft)),
                                                          ("Latest reading (USGS)", "{:,.2f} ft".format(G["sg"][-1][1])),
                                                          ("Difference (our calculation)", "%+.2f ft" % gap)))
        return block("reservoir", "How full the lake is", "agency", lead + table(["Measure", "Value"], rows, right=(1,)),
                     "Source: US Army Corps of Engineers, Corps Water Management System, %s %s 'Top of Conservation', fetched %s; preliminary, for general information only. The lake reading is USGS's on the same datum; the difference is our calculation." % (esc(G["rec"]["usace_pool"]["office"]), esc(G["rec"]["usace_pool"]["loc"]), esc(fdate(G["rec"]["usace_pool"]["fetched_at"][:10]))), "usace_cwms")
    hit = lc_day(G)
    if hit:  # Lake Mead: Reclamation Lower Colorado Region's daily table
        m = dict(G["rec"]["usbr_lc"], date=hit[0], elev_ft=hit[1], content_af=hit[2])
        if True:
            rows = "".join(tr([a, b], right=(1,)) for a, b in (
                ("Water stored (Reclamation)", "{:,.0f} acre-ft".format(m["content_af"])),
                ("Capacity to the bottom of the flood-control space, %s ft (Reclamation)" % "{:,.1f}".format(m["cap_elev_ft"]), "{:,.0f} acre-ft".format(m["cap_af"])),
                ("Percent of that capacity (our calculation)", "%.1f%%" % (100 * m["content_af"] / m["cap_af"])),
                ("Feet below %s ft (our calculation)" % "{:,.1f}".format(m["cap_elev_ft"]), "%.2f ft" % (m["cap_elev_ft"] - m["elev_ft"]))))
            age_h = (G["now"] - datetime.datetime.fromisoformat(m["date"] + "T12:00:00+00:00")).total_seconds() / 3600
            return block("reservoir", "How full the reservoir is", "agency", table(["Measure", esc(fdate(m["date"]))], rows, right=(1,)),
                         "Source: U.S. Bureau of Reclamation, Lower Colorado Region, 'Available reservoir elevations and contents' (usbr.gov/lc/region/g4000/hourly/levels.html), Hoover Dam row for %s (content given in thousand acre-feet), read %s. Capacity is the table's figure at the bottom of the exclusive flood-control space. The percent and the feet below are our calculation." % (
                             esc(fdate(m["date"])), esc(tzl(parse_t(m["fetched_at"]), G["zone"]))), "usbr", amber=age_h)
    t = twdb_now(G)
    if not t:
        return None
    age_h = (G["now"] - datetime.datetime.fromisoformat(t["date"] + "T12:00:00+00:00")).total_seconds() / 3600
    rows = "".join(tr([a, b], right=(1,)) for a, b in (
        ("Share of conservation capacity", "%.1f%%" % t["pct_cons"] if t.get("pct_cons") is not None else "Unknown"),
        ("Conservation storage", "{:,.0f} acre-ft".format(t["cons_storage_af"]) if t.get("cons_storage_af") is not None else "Unknown"),  # the agency's own figure, never rounded to 3 figures (owner 2026-11-07)
        ("Total storage, all pools" + ("" if ((G["rec"].get("usgs") or {}).get("rows") and series(G["rec"], "00054")) else " (the first-screen tile)"),"{:,.0f} acre-ft".format(t["storage_af"]) if t.get("storage_af") is not None else "Unknown"),  # phone review 2026-11-07 (Georgetown, Texana, Lavon): the tile's TWDB total and this table's conservation storage differed with nothing naming which was which
        ("Conservation capacity", "{:,.0f} acre-ft".format(t["cons_cap_af"]) if t.get("cons_cap_af") is not None else "Unknown"),
        ("Surface area", "{:,.0f} acres".format(t["area_ac"]) if t.get("area_ac") is not None else "Unknown"),
        ("Water level (TWDB daily)", "%.2f ft" % t["elev_ft"] if t.get("elev_ft") is not None else "Unknown")))
    return block("reservoir", "How full the reservoir is", "agency", table(["Measure", "%s" % fdate(t["date"])], rows, right=(1,)),
                 "Source: Texas Water Development Board, Water Data for Texas, daily estimate for %s. TWDB's percent is conservation storage divided by conservation capacity; flood storage is not counted. TWDB values are estimates built from several data providers.%s" % (esc(fdate(t["date"])), "" if G.get("agy") else " TWDB's water level matches the USGS lake elevation (%s) for that day within 0.5 ft." % lake_datum(G)),  # an agency lake's reading is TWDB itself: no USGS to match
                 "twdb", amber=age_h)


def twdb_now(G):
    """TWDB's daily record for this lake, or None: the one rule for the page block and /research/lake-levels/ (lake review #9: TWDB's level must match USGS's the same day, or the file may be another lake or datum)."""
    t = G["rec"].get("twdb")
    if not G.get("lake") or not t or not cleared("twdb"):
        return None
    same = [v for d, v, _ in G["sg"] if d.date().isoformat() == t["date"]]
    if not same or t.get("elev_ft") is None or abs(sum(same) / len(same) - t["elev_ft"]) > 0.5:
        return None
    return t


def b_lake_temp(G):
    """Great Lakes pages: NOAA GLERL's lake-wide average surface water temperature (GLSEA satellite analysis, daily, deg F as the file gives it, deg C our
    conversion) and GLERL's 1995-<year> average for the same day; the difference is our subtraction. A shoreline sensor is local and is labelled so elsewhere.
    States: valid; stale (amber past 4 days, the file lags 1-2 days); hidden past 10 days (no old lake shown as now); unavailable = 'Unknown', never silence."""
    if not G.get("lake") or G["row"].get("river") not in ("Lake Superior", "Lake Michigan", "Lake Huron", "Lake Erie", "Lake Ontario") or not cleared("glerl"):
        return None
    g = G["rec"].get("glsea")
    src = "Source: NOAA Great Lakes Environmental Research Laboratory (GLERL) CoastWatch, GLSEA average surface water temperature for the whole lake"
    if not g or not g.get("date") or g.get("temp_f") is None:
        return block("lake_temp", "%s surface water temperature, lake-wide average" % esc(G["row"]["river"]), "agency", "<p>Unknown: GLERL's lake-average file was not read in this build.</p>", src + ".", "glerl")
    age_h = (G["now"] - datetime.datetime.fromisoformat(g["date"] + "T12:00:00+00:00")).total_seconds() / 3600
    if age_h > 240:
        return None
    f, a = g["temp_f"], g.get("avg_f")
    rows = "".join(tr([x, y], right=(1,)) for x, y in (
        ("Lake-wide average, %s (GLERL)" % fdate(g["date"]), "%.1f °F (%.1f °C)" % (f, (f - 32) / 1.8)),
        ("Average for this day, %s-%s (GLERL)" % (g["avg_from"], g["avg_to"]), "%.1f °F" % a if a is not None else "Unknown"),
        ("Difference (our calculation)", "%+.1f °F" % (f - a) if a is not None else "Unknown")))
    return block("lake_temp", "%s surface water temperature, lake-wide average" % esc(G["row"]["river"]), "agency", table(["Measure", "Value"], rows, right=(1,)),
                 src + ", daily satellite analysis for %s, read %s. Degrees Celsius and the difference from the %s-%s average are our calculation. A shoreline sensor can read several degrees off the lake-wide average." % (
                     esc(fdate(g["date"])), esc(tzl(parse_t(g["fetched_at"]), G["zone"])), g["avg_from"], g["avg_to"]), "glerl", amber=age_h)


def lsr_where(w):
    """An NWS local storm report place as received, marked when the NWS field cut it short (phone review 2026-11-07, The Battery: '1 S Point Pleasant Beac'):
    the field holds at most 23-24 characters, so a name that fills it is shown with an ellipsis, never as if whole. ponytail: length test, a gazetteer if names of exactly that length prove whole."""
    w = (w or "").strip()
    return w + "…" if len(w) >= 23 else w


def b_moon(G):
    """Coast pages: today's moonrise and moonset at the station (USNO predictions, UTC instants shown in station time by us) and the closest principal phase.
    States: valid; valid-empty (the fetched window covers today and holds no rise or set: 'none today', which happens about once a month);
    unavailable ('Unknown': not fetched, or the window does not cover today); old answers drop out by the window rule, never shown as today."""
    if not G.get("coast") or not cleared("usno"):
        return None
    u, z = G["rec"].get("usno") or {}, G["zone"]
    src = "Source: U.S. Naval Observatory, Astronomical Applications Department, Sun and Moon data for one day at the station's position"
    loc = G["now"].astimezone(z)
    d0 = datetime.datetime.combine(loc.date(), datetime.time(0), tzinfo=z)
    d1 = d0 + datetime.timedelta(days=1)
    dates = sorted(d["date"] for d in u.get("days") or [])
    covered = bool(dates) and datetime.datetime.fromisoformat(dates[0] + "T00:00:00+00:00") <= d0 and d1 <= datetime.datetime.fromisoformat(dates[-1] + "T00:00:00+00:00") + datetime.timedelta(days=1)
    if not covered:
        return block("moon", "Moon today", "agency", "<p>Unknown: the U.S. Naval Observatory's moon times for today were not read in this build.</p>", src + ".", "usno")
    ev = sorted((parse_t(t), ph) for d in u["days"] for ph, t in d["moon"])
    today_ = lambda ph: [t for t, p in ev if p == ph and d0 <= t < d1]
    tm = lambda ts, w: ", ".join(esc(tzl(t, z, date=False)) for t in ts) or "No %s today" % w  # "None" reads as a code leak (break gate 2026-11-07)
    cps = sorted({tuple(d["closest"]) for d in u["days"] if d.get("closest")}, key=lambda c: abs((parse_t(c[1]) - G["now"]).total_seconds()))
    overhead = [(t, ph) for t, ph in ev if ph == "Upper Transit"]  # PLAN 35: fetched since 2026-11-13; an older cache has none, so the row waits rather than saying 'none'
    rows = "".join(tr([a, b], right=(1,)) for a, b in (("Moonrise today", tm(today_("Rise"), "moonrise")), ("Moonset today", tm(today_("Set"), "moonset")),
                                                      *((("Moon overhead today", tm(today_("Upper Transit"), "moon overhead")),) if overhead else ()),
                                                      ("Moon phase, nearest principal phase", ("%s, %s" % (esc(cps[0][0]), esc(tzl(parse_t(cps[0][1]), z)))) if cps else "Unknown")))
    sol = ('<p class="src">Solunar tables, from John Alden Knight\'s 1926 theory that fish feed more when the moon is overhead, underfoot or at the horizon, are built from these times. '
           'The theory is disputed, and sources give different period lengths, so none is shown.</p>') if overhead else ""
    return block("moon", "Moon today", "agency", table(["Measure", esc(fdate(loc.date().isoformat()))], rows, right=(1,)) + sol,
                 src + ", read %s. USNO gives the times in UTC; station time is our conversion." % esc(tzl(parse_t(u["fetched_at"]), z)), "usno")


def b_waves(G):
    """Coast pages: the newest reading of the station's hand-checked offshore buoy, in the file's units first (CDIP asks that data is not altered),
    feet and Fahrenheit beside, the buoy's distance always named (a buoy is never 'at the beach'). Hidden after 6 h; amber after 2 h."""
    b = G["rec"].get("buoy")
    if not G.get("coast") or not b or not b.get("time"):
        return None
    src = "cdip" if b.get("owner") == "SCRIPPS" else "ndbc"
    if not cleared(src):
        return None
    t = parse_t(b["time"])
    age = (G["now"] - t).total_seconds() / 3600
    if age > 6:
        return None
    u = lambda v, f: f(v) if v is not None else "Unknown"
    rows = "".join(tr([a, c], right=(1,)) for a, c in (
        ("Wave height (significant)", u(b.get("wvht_m"), lambda v: "%.1f m (%.1f ft)" % (v, v * 3.28084))),
        ("Dominant wave period", u(b.get("dpd_s"), lambda v: "%.0f s" % v)),
        ("Wave direction (coming from)", u(b.get("mwd_deg"), lambda v: "%.0f° true" % v)),
        ("Sea surface temperature at the buoy", u(b.get("wtmp_c"), lambda v: "%.1f °C (%.0f °F)" % (v, v * 1.8 + 32)))))
    credit = ' <a href="https://cdip.ucsd.edu/" rel="noopener">Data courtesy of CDIP</a>.' if src == "cdip" else ""
    return block("waves", "Waves offshore", "live", table(["Buoy %s, %.0f km offshore" % (esc(b["id"]), b["km"]), esc(tzl(t, G["zone"]))], rows, right=(1,)),
                 "Source: %s buoy %s, %.0f km from this station, newest reading %s; values as the buoy reports them.%s" % (
                     "CDIP (Scripps Institution of Oceanography) via NOAA NDBC" if src == "cdip" else "NOAA National Data Buoy Center", esc(b["id"]), b["km"], esc(tzl(t, G["zone"])), credit), src, amber=age > 2)


def b_key_facts(G):
    """Facts that do not change by the hour, as plain sentences with their source: what Google's AI answers can quote without going stale (owner 2026-11-04).
    Never the live reading: a cached copy of it would read as today's level. Each sentence is built only from a value in this run's cache; none, no block."""
    rp = river_at(G["river"], G["place"])
    lines, srcs = [], []
    if G["feed"]:
        from lib.world import fmt_level, to_ft
        f = G["feed"]
        lv = lambda v: "%s (%.1f ft)" % (fmt_level(v, f["unit"]), to_ft(v, f["unit"]))
        about = dict(f.get("about") or ())
        rp = f.get("head") or rp
        if about.get("Station number"):
            lines.append("%s is %s station %s%s." % (rp, f["name"], about["Station number"], (", with %s years of daily values on record" % about["Years of daily values on record"]) if about.get("Years of daily values on record") else ""))
        if f.get("peaks"):
            y, v, d = max(f["peaks"], key=lambda x: x[1])
            lines.append("Highest yearly peak level in the last %d years on file: %s on %s." % (len(f["peaks"]), lv(v), fdate(d)))
        if f.get("src") == "pegelonline" and (f.get("marks") or {}).get("HHW") is not None:
            hd = (f.get("mark_dates") or {}).get("HHW")
            lines.append("Highest level on the agency's record: %s%s." % (lv(f["marks"]["HHW"]), (" on %s" % fdate(hd[:10])) if hd else ""))
        srcs.append("%s, %s" % (f["api"], f["name"]))
    else:
        loc = ((G["rec"].get("meta") or {}).get("loc")) or {}
        where = ", ".join(x for x in (loc.get("county_name"), loc.get("state_name")) if x)
        da = loc.get("drainage_area") or G["row"].get("drainage_sqmi")  # the inventory's area when station metadata lacks it (audit 2026-11-10 #7: no longer on the first screen)
        try:
            da = float(da) if da and float(da) > 0 else None
        except (TypeError, ValueError):
            da = None
        if where:
            lines.append("%s is USGS gauge %s in %s%s." % (rp, G["site"], where, ("; it drains %s square miles" % fmt(da)) if da else ""))
        fd = ((G["rec"].get("meta") or {}).get("ts") or {}).get("flow_daily")
        if fd:
            lines.append("USGS daily flow records here run from %s to %s." % (fdate(fd[0]), fdate(fd[1])))
        pk = [r for r in ((G["rec"].get("peaks") or {}).get("rows") or []) if r[1] is not None]
        if pk:
            t, q = max(pk, key=lambda r: r[1])[:2]
            lines.append("Highest annual peak flow on USGS file: %s cfs on %s (%d annual peaks, %s to %s)." % (fmtc(q), fdate(t[:10]), len(pk), pk[0][0][:4], pk[-1][0][:4]))
        if lines:
            srcs.append("USGS Water Data API and USGS annual peak streamflow")
        n = G["rec"].get("nwps") or {}
        cats = [(k, n["categories"][k]) for k in ("action", "minor", "moderate", "major") if isinstance((n.get("categories") or {}).get(k), (int, float)) and n["categories"][k] > 0]
        if cats and n.get("lid") and SOURCES["nwps"]["status"] in ("quoted", "owner-permission"):
            lines.append("National Weather Service flood stages at this gauge: %s." % ", ".join("%s %s ft" % (k, "{:,.2f}".format(v).rstrip("0").rstrip(".")) for k, v in cats))  # as the NWS publishes them: fmt rounded 99.5 and 100.5 both to "100" (phone review 2026-11-07, Lake Champlain)
            srcs.append("NWS National Water Prediction Service, forecast point %s" % n["lid"])
    if not lines:
        return None
    return block("key_facts", "Key facts", "hist", "<ul class=\"facts\">%s</ul>" % "".join("<li>%s</li>" % esc(l) for l in lines),
                 "Sources: %s." %"; ".join(srcs), "eccc" if G["feed"] and G["feed"].get("src") == "eccc" else (G["feed"]["src"] if G["feed"] else "usgs"))
