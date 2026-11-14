"""Tab assembly, navigation, footer, live scripts and the page template."""
import statistics, os, re, json, math, collections, hashlib, datetime, zoneinfo
from lib.common import *
from lib.core import *
from lib.hero import *
from lib.core import _safe
from lib.charts import *
from lib.weather import *
from lib.forecast import *
STATE_RULES = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "state-rules.json"), encoding="utf-8"))["states"]


def b_related(G, pages):
    items = (G["rec"].get("related") or {}).get("items") or []
    rows = ""
    rel_ = lambda x, pr: "Tributary upstream" if x["relation"] == "upstream" and pr["river"].split()[0].lower() != G["river"].split()[0].lower() else x["relation"].capitalize()  # same rule as the hero tile
    old_ = lambda x: (lambda h: h is None or h > 24)(hours_old(x["time"], G["now"]))
    away = lambda pr: (" &middot; %d mi away" % round(miles_between(G["lat"], G["lon"], pr["_ll"][0], pr["_ll"][1]))) if pr.get("_ll") else ""  # hater w4: chain gauges with no distance
    # PLAN 39 (Albuquerque, 2026-11-13): a same-river gauge without a page of its own is still the reading a reader checks next; it is named
    # without a link (links rule: only built pages are linked), so the block no longer vanishes where the neighbours are not released yet
    nm_ = lambda pr: ('<a href="%s">%s</a>' % (pr["water_url"], esc(river_at(pr["river"], pr["place"])))) if pr.get("_built") else esc(river_at(pr["river"], pr["place"]))
    for x in items:
        pr = pages.get(x["site"])
        if not pr:
            continue
        lag = ("about %d h (r %.2f)" % (x["lag_h"], x["lag_r"])) if x.get("lag_h") else "–"
        rows += tr([nm_(pr), rel_(x, pr), "%s cfs" % fmtc(x["flow"]), esc(tzl(parse_t(x["time"]), G["zone"])), lag], right=(2,))
    if not rows:
        return None
    from lib import ui
    nodes = []
    for rel in ("upstream", "downstream"):
        if rel == "downstream":
            nodes.append({"name": "<span>This gauge</span>", "flow": ("%.2f ft" % G["sg"][-1][1]) if G.get("lake") and G["sg"] else "%s cfs" % fmtc(dir_lv(G)), "sub": esc(G["obs"]), "cur": True})
        for x in items:
            pr = pages.get(x["site"])
            if x["relation"] == rel and pr:
                nodes.append({"name": nm_(pr), "flow": "%s cfs" % fmtc(x["flow"]),
                              "sub": rel_(x, pr) + away(pr) + " &middot; " + esc(tzl(parse_t(x["time"]), G["zone"])) + (" (older than 24 h)" if old_(x) else ""), "cur": False})
    # the block also shows "This gauge" with its own reading: an old own reading is not live either (break_blocks stale26h, 2026-11-14)
    own_old = not G.get("lt") or (G["now"] - G["lt"]).total_seconds() > 24 * 3600  # the same 24 h cut as the neighbour rows' "(older than 24 h)"
    stale = own_old or any(old_(x) for x in items if pages.get(x["site"]))
    dirs_ = {x["relation"] for x in items if pages.get(x["site"])}
    return block("related_gauges", "Upstream and downstream gauges" if len(dirs_) == 2 else ("Upstream gauge" if "upstream" in dirs_ else "Downstream gauge") + ("s" if sum(1 for x in items if x["relation"] in dirs_ and pages.get(x["site"])) > 1 else ""), "agency" if stale else "live", ui.strip(nodes),
                 "Source: USGS NLDI river network and USGS Water Data API. Relation is along the NLDI main stem; gauges that report flow are listed; those without a page on this site are named without a link.", "usgs")


def b_land(G):
    land = G["rec"].get("land")
    if not land or not land.get("rows"):
        return None
    seen_l, uniq = set(), []
    for t in land["rows"]:
        u = re.sub(r"\b(\w+) \1\b", r"\1", re.sub(r"\s*\bUnknown\b\s*", " ", t[0] or "").strip()) or "Unnamed unit"  # PAD-US: "Clackamas County County Facility or Land"
        if re.match(r"(?i)private land owner", u) or (t[1] or "").upper() == "PVT":
            continue  # a private owner is not public land (hater 2026-10-27: "Private Land Owner 1", "Isles Unknown")
        if u.lower() not in seen_l:
            seen_l.add(u.lower())
            uniq.append((u, t[1], t[2]))
    if not uniq:
        return None
    uniq.sort(key=lambda r: {"OA": 0, "RA": 1, "XA": 3}.get((r[2] or "").upper(), 2))  # PLAN 0b (weak rows): land a reader can walk onto first, closed land (military, utility) last; PAD-US order otherwise
    known = any(PADMAN.get(m, m) not in ("Unknown manager", "Unknown", None, "") for _, m, _ in uniq[:12])
    rows = "".join(tr([esc(u)] + ([esc(PADMAN.get(m, m or "n/a"))] if known else []) + [esc(ACCESS.get(a, a or "n/a"))]) for u, m, a in uniq[:12])
    return block("public_land", "Public land at this gauge", "map", table(["Unit"] + (["Managed by"] if known else []) + ["Public access"], rows),
                 "Source: USGS Protected Areas Database (PAD-US), within about half a mile of the gauge, downloaded %s. Mapped land is not proof of legal access." % fdate(land["downloaded"]), "padus")


def b_map(G):
    lat, lon = G["lat"], G["lon"]
    half = 8000 / math.cos(math.radians(lat))
    cx, cy = merc(lat, lon)
    bbox = "%.0f,%.0f,%.0f,%.0f" % (cx - half, cy - half * 0.5625, cx + half, cy + half * 0.5625)
    src = "https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/export?bbox=%s&bboxSR=3857&imageSR=3857&size=640,360&format=png&f=image" % bbox
    return block("gauge_map", "Gauge location", "map", '<div class="mapimg"><img src="%s" alt="USGS topographic map centered on %s, about 10 miles across" width="640" height="360" loading="lazy" decoding="async"><i aria-hidden="true"></i></div>' % (src, re.sub(r"^at ", "", where_(G))),
                 "Source: Map services and data available from U.S. Geological Survey, National Geospatial Program (USGS Topo). Map about 10 miles across, centered on the gauge at %.4f, %.4f." % (lat, lon), "natmap")


# ---------------------------------------------------------------- tabs
TABS = {
    "dashboard": {"label": "Conditions", "title": "%s, %s: river level and flow", "desc": "%s, %s: current flow, gage height, how it compares with past years, alerts, history and flood record from USGS gauge %s.", "hero": True},
    "forecast": {"label": "Forecast", "title": "%s, %s: river forecast", "desc": "%s, %s: river forecast, rain, radar and weather forecast for USGS gauge %s.", "hero": False},
}


KIND_NAME = {"river": "Nearest river gauge on this site", "lake": "Nearest lake on this site", "coast": "Nearest tide station on this site"}
TITLE_TODAY = {"08330000"}  # Rio Grande at Albuquerque; one page, so the change can be measured
NEAR_MI = 60  # owner 2026-11-09 "no forced internal links": other water a reader here could drive to today (about an hour; reviewers called 107 and 127 mi not nearby); the same river at any distance is the upstream/downstream strip; farther pages are reached through the hubs
_IX = {}


def kind_of_g(G):
    return "coast" if G.get("coast") else "lake" if G.get("lake") else "river"


def _skip(s, G):
    return {s} | {x["site"] for x in (((G or {}).get("rec") or {}).get("related") or {}).get("items") or []}  # upstream/downstream have their own strip


def link_index(pages, Gs=None):
    """1-degree grid of the built pages (all kinds and per kind), every page's own lists, and the reverse lists; made once per build after every page's
    _built/_ll/_kind is set. Was an O(n) scan per page (14,000 pages = 196M distance tests a run); a grid query reads 15 squares.
    No reverse lists (owner 2026-11-09): a page is never added to another page's list because it needs inbound links."""
    grid, kinds = collections.defaultdict(list), collections.defaultdict(lambda: collections.defaultdict(list))
    built = [(s, p) for s, p in pages.items() if p.get("_built") and p.get("_ll")]
    for s, p in built:
        key = (int(p["_ll"][0] // 1), int(p["_ll"][1] // 1))
        grid[key].append((s, p))
        kinds[p.get("_kind", "river")][key].append((s, p))
    _IX.clear()
    _IX.update(pages=id(pages), grid=grid, kinds=kinds, base={})
    _IX["members"] = {id(g): {s for v in g.values() for s, _ in v} for g in [grid] + list(kinds.values())}
    for s, p in built:
        _IX["base"][s] = _base(p["_ll"], p.get("state"), p.get("_kind", "river"), _skip(s, (Gs or {}).get(s)), p.get("_huc", ""))
    return _IX


def nearest(ll, grid, skip, n):
    """The n nearest pages in a grid, at any distance: rings of squares widen until n are found or the grid is exhausted.
    ponytail: at a ring's corner the n-th may not be the true n-th nearest; harmless for a nearest-first list (same as lib/world.py near)."""
    la, lo = int(ll[0] // 1), int(ll[1] // 1)
    members = _IX.get("members", {}).get(id(grid)) or {s for v in grid.values() for s, _ in v}  # counted once per build, not per call (O(n) per page = O(n^2))
    avail = len(members) - len(members & skip)
    rad = 1
    while True:
        got = [(miles_between(ll[0], ll[1], p["_ll"][0], p["_ll"][1]), p) for i in range(la - rad, la + rad + 1) for j in range(lo - 2 * rad, lo + 2 * rad + 1) for s, p in grid.get((i, j), ()) if s not in skip]
        if len(got) >= min(n, avail) or rad > 180:
            return sorted(got, key=lambda x: x[0])[:n]
        rad *= 2


def _base(ll, st, kind, skip, huc=""):
    """A page's own lists: up to five within 60 miles, the same-state and anywhere backfill where gauges are sparse, and the nearest page of each other kind."""
    dist = lambda p: miles_between(ll[0], ll[1], p["_ll"][0], p["_ll"][1])
    la, lo = int(ll[0] // 1), int(ll[1] // 1)
    # 60 mi is under 1 deg lat and ~2 deg lon in CONUS: only the 15 squares around the gauge are read
    box = [(dist(p), p) for i in range(la - 1, la + 2) for j in range(lo - 2, lo + 3) for s, p in _IX["grid"].get((i, j), ()) if s not in skip]
    out = sorted((x for x in box if x[0] <= NEAR_MI), key=lambda x: (not (huc and x[1].get("_huc") == huc), x[0]))[:5]  # PLAN 12: the same watershed (USGS HUC8) first, then by distance; an angler moving within a basin shares its weather and runoff  # nearby means a short drive: the first reviews called 107 and 127 miles not nearby
    shown = {p["site"] for _, p in out} | skip
    groups = [(None, out)]  # owner 2026-11-09: no backfill to five from the same state or anywhere (a link a reader here would not tap); the breadcrumb hub lists the rest
    for k, grid in sorted(_IX["kinds"].items()):  # links rule 3: rivers, lakes and coasts link the nearest of each other kind, both ways, within NEAR_MI
        if k != kind:
            hit = [x for x in nearest(ll, grid, shown, 1) if x[0] <= NEAR_MI]
            if hit:
                groups.append((KIND_NAME[k], hit))
                shown.add(hit[0][1]["site"])
    return [g for g in groups if g[1]]


def nb_pick(G, pages):
    """Which water pages this page lists, as (heading or None, [(miles, page)]) groups. One function for the block and for build.py's rebuild test
    (CLAUDE.md links rule 5: a page whose list changed is rebuilt the same run, never carried with a stale or broken link)."""
    if _IX.get("pages") != id(pages):
        link_index(pages)
    s = G["site"]
    return _IX["base"].get(s) or _base((G["lat"], G["lon"]), G.get("st"), kind_of_g(G), _skip(s, G))


def nb_urls(G, pages):
    """The water pages this page links (nearby lists and the built upstream/downstream gauges): build.py rebuilds the page when this set changes."""
    rel = [x["site"] for x in ((G["rec"].get("related") or {}).get("items") or []) if pages.get(x["site"], {}).get("_built")]
    return sorted({p["water_url"] for _, grp in nb_pick(G, pages) for _, p in grp} | set(rel))


def b_nearby(G, pages):
    """Other gauges on the site close to this one (up to five within 60 miles, nearest first), each with latest flow and the plain-word comparison, then the nearest
    page of each other water kind and the pages that list this one as their nearest. Upstream and downstream gauges are in their own strip and are skipped here."""
    groups = nb_pick(G, pages)
    if not groups:
        return None
    out = groups[0][1] if groups[0][0] is None else []
    skip = {G["site"]} | {x["site"] for x in ((G["rec"].get("related") or {}).get("items") or [])}
    li = lambda grp: "".join('<li><a href="%s">%s</a><span>%s%s &middot; %d mi away</span></li>' % (p["water_url"], esc((lambda pl: river_at(p["river"], pl[0]) + ", " + pl[1])(usgs_place(p, {}))), esc(p.get("_val") or fmtc(p["_lv"]) + " cfs"), (" &middot; " + esc(p["_band"].lower())) if p["_band"] not in ("–", "-", "") else "", round(mi)) for mi, p in grp)
    lis = li(out)
    for h, grp in groups:  # the same-state heading, not the state's name: a border gauge USGS files under SC sits in GA (hater review 2026-11-07)
        if h:
            lis += '</ul><p class="src">%s</p><ul class="nbr">' % h + li(grp)
    head = "Other water nearby (within %d mi)" % NEAR_MI  # every list is within NEAR_MI (owner 2026-11-09: no forced links)
    return block("nearby_gauges", head, "live", ('<ul class="nbr">%s</ul>' % lis).replace('<ul class="nbr"></ul>', ""),
                 "Source: USGS Water Data API latest readings at the gauges on this site, as of this page's build; the comparison is our estimate from USGS daily statistics for the date. Distance is straight-line from this gauge.", "usgs")


def embed_snippet(url, name):
    """The code a club, marina or county page pastes (owner 2026-11-08 backlinks): the live panel in an iframe plus one plain, visible link under it,
    because a link inside an iframe sits on our own domain and earns nothing. The anchor is the place's name, never stuffed keywords (Google: widget links
    must be visible and natural)."""
    return ('<iframe src="%s/embed%s" width="100%%" height="520" loading="lazy" title="%s"></iframe>\n<p>Live data from <a href="%s%s" rel="nofollow">River Water Levels</a></p>'
            % (SITE_URL, url, esc(name), SITE_URL, url))


def embed_code(G):
    """A closed fold under the official links with this page's own embed code, ready to copy. None on a world page: build.py writes no embed panel for it."""
    if G.get("feed"):
        return ""
    name = "%s water level" % river_at(G["river"], G["place"])
    return '<details class="emb"><summary>Embed this live panel on your site</summary><textarea readonly rows="4" aria-label="Embed code" style="width:100%%;font:12px monospace">%s</textarea><small>Free. The credit line under the panel is optional.</small></details>' % esc(embed_snippet(G["row"]["dashboard_url"], name))


# Each URL fetched 2026-11-11 by the PLAN 8 research; a state not listed had no verified program page.
BEACH_WATER = {"TX": ("Texas Beach Watch (General Land Office)", "https://www.texasbeachwatch.com/"),
               "FL": ("Florida Healthy Beaches (Department of Health)", "https://www.floridahealth.gov/HealthyBeaches"),
               "NJ": ("NJ Beaches (NJ Department of Environmental Protection)", "https://njbeaches.org/"),
               "WA": ("Swimming safety and the BEACH program (Washington Department of Ecology)", "https://ecology.wa.gov/water-shorelines/water-monitoring-research/swimming-safety"),
               "HI": ("Clean Water Branch (Hawaii Department of Health)", "https://health.hawaii.gov/cwb/"),
               "SC": ("Beach Monitoring (South Carolina Department of Environmental Services)", "https://des.sc.gov/programs/bureau-water/aquatic-science/beach-monitoring"),
               "VA": ("Beach Monitoring (Virginia Department of Health)", "https://www.vdh.virginia.gov/waterborne-hazards-control/beach-monitoring/"),
               "MA": ("Beach water quality (Massachusetts Department of Public Health)", "https://www.mass.gov/beachdata"),
               "ME": ("Maine Healthy Beaches (Maine Department of Environmental Protection)", "https://www.maine.gov/dep/water/beaches/"),
               "OR": ("Oregon Beach Monitoring Program (Oregon Health Authority)", "https://www.oregon.gov/oha/PH/HEALTHYENVIRONMENTS/RECREATION/BEACHWATERQUALITY/Pages/status.aspx"),
               "AK": ("Beach Program (Alaska Department of Environmental Conservation)", "https://dec.alaska.gov/water/water-quality/beach-program"),
               "CA": ("Safe to Swim (California Water Quality Monitoring Council)", "https://mywaterquality.ca.gov/safe-to-swim/"),
               "DE": ("Recreational Water Monitoring (Delaware DNREC)", "https://dnrec.delaware.gov/watershed-stewardship/assessment/recreational-water-monitoring/"),
               "CT": ("State park beach monitoring (Connecticut DEEP; town beaches are tested by local health departments)", "https://portal.ct.gov/deep/water/inland-water-monitoring/beach-monitoring"),
               "AL": ("Coastal Alabama Beach Monitoring Program (ADEM and Alabama Department of Public Health)", "https://adem.alabama.gov/coastal/ademadph-coastal-alabama-beach-monitoring-program"),
               "GA": ("Georgia Healthy Beaches (Georgia DNR Coastal Resources Division)", "https://coastalgadnr.org/HealthyBeaches"),
               "NC": ("Recreational Water Quality and swimming advisory map (NC Department of Environmental Quality)", "https://www.deq.nc.gov/recreational-water-quality"),
               "NY": ("NYC Beach Water Quality (NYC Health Department; beaches outside the city are tested by county health departments)", "https://a816-dohbesp.nyc.gov/IndicatorPublic/Beaches/")}  # tools/edge_tests.py: every state in data/coasts.csv has a row, so a new coast state never ships without its program  # 2026-11-12: all seven are the states' own BEACH Act program pages (search results on each agency's domain); MA and AK refuse automated reads (403), read in search results only


def b_official_links(G):
    """Where to go next: the source pages for this gauge, opened in a new tab."""
    n = G["rec"].get("nwps") or {}
    lid = n.get("lid")
    links = [("NOAA Tides and Currents page for this station", "https://tidesandcurrents.noaa.gov/stationhome.html?id=%s" % G["site"])] if G.get("coast") else [("USGS page for this gauge", "https://waterdata.usgs.gov/monitoring-location/USGS-%s/" % G["site"]), ("USGS WaterAlert: text or email when this gauge crosses a level you choose", "https://accounts.waterdata.usgs.gov/wateralert/")]
    lv_ = (G["rec"].get("coops") or {}).get("level") if G.get("coast") else None
    if lv_:
        links.append(("NOAA Tides and Currents page for %s (%s), where this page's water level is read" % (lv_["name"], lv_["id"]), "https://tidesandcurrents.noaa.gov/stationhome.html?id=%s" % lv_["id"]))
    if G.get("agy"):  # a CDEC id on a USGS address is a dead link
        links = [("%s page for %s %s" % (G["agy"]["short"], G["agy"]["label"].split()[-1], G["agy_st"]), G["agy"]["page"] % G["agy_st"])]
    if G.get("agy") and G["agy"].get("short") == "Reclamation" and re.search(r"\b(Mead|Powell)\b", G.get("river") or ""):  # PLAN 0i: the official projection of these two lakes is a monthly PDF whose tables move; linked, never copied (truth first)
        links.append(("Reclamation 24-Month Study: projected end-of-month elevations of Lake Powell and Lake Mead", "https://www.usbr.gov/lc/region/g4000/24mo/index.html"))
    if re.search(r"\bLake Powell\b", G.get("river") or ""):  # PLAN 9 (2026-11-11): the operator's own monthly release plan (read live: anticipated monthly volumes, updated Oct 15, 2026); Yellowtail's newest plan is 2023, so not linked as upcoming
        links.append(("Reclamation: Glen Canyon Dam release plan, this month and the water year", "https://www.usbr.gov/uc/water/crsp/cs/gcd.html"))
    if str(G.get("site", "")).startswith("COOPS-") and G.get("lake"):  # PLAN 8b: the lake-wide average (all coordinated gauges) is monthly on NOAA GLERL's page; linked, not copied
        links.append(("NOAA GLERL Great Lakes water levels: lake-wide averages and long-term records", "https://www.glerl.noaa.gov/data/wlevels/"))
    if lid:
        links.append(("NWS river page for the %s" % nws_pt(n), "https://water.noaa.gov/gauges/%s" % lid))
    links.append(("NWS forecast and active alerts for this location", "https://forecast.weather.gov/MapClick.php?lat=%.4f&lon=%.4f" % (G["lat"], G["lon"])))
    bw = BEACH_WATER.get(G["row"]["state"]) if G.get("coast") else None  # PLAN 8: swimmers ask "can I swim today?"; the state's own advisories, linked (TX terms bar reuse, FL is HTML only, CA's open file is months old)
    if bw:
        links.append(("Swim advisories and beach water samples: %s" % bw[0], bw[1]))
    if G.get("coast") and G["row"]["state"] == "WA":  # PLAN 33b: WDFW creel counts (fish per angler at each ramp) are linked, not copied: wdfw.wa.gov/privacy allows non-commercial use only
        links.append(("Puget Sound creel reports: fish caught per angler at each ramp (WDFW)", "https://wdfw.wa.gov/fishing/reports/creel/puget"))
    if G.get("coast") and G["row"]["state"] == "FL":  # PLAN 30: FWC's red tide samples, linked: its data terms ask anyone sharing it further to email FWC first (owner decision 7: no permission requests), read 2026-11-13 on the Hub item
        links.append(("Red tide: FWC's Karenia brevis samples near the coast, last 8 days, updated daily", "https://myfwc.com/research/redtide/statewide/"))
    from lib.directory import STATE_NAMES  # here, not at the top: directory imports render
    for k, what in (("fish", "Fishing rules"), ("boat", "Boating rules")):  # owner 2026-10-29: the official state page an angler or boater needs next (data/state-rules.json, each URL from a search result and curl-checked)
        e = None if G.get("coast") else (STATE_RULES.get(G["row"]["state"]) or {}).get(k)  # coast review: the state list holds the freshwater agency; saltwater rules are another agency's, not read yet
        if e:
            links.append(("%s in %s (%s)" % (what, STATE_NAMES.get(G["row"]["state"], G["row"]["state"]), e["agency"]), e["url"]))
    links.append(("This page's data as JSON: 3-day water level readings (NOAA CO-OPS, preliminary)" if G.get("coast") else "This page's data as JSON: 7-day flow and gage height readings, daily mean flow by year (USGS, provisional)", G["row"]["dashboard_url"] + "data.json"))
    links.append(("Put this gauge's live panel on your own site (free embed, links back here)", "/embed" + G["row"]["dashboard_url"]))
    body = cite_line(G) + '<ul class="olinks">%s</ul>' % "".join('<li><a href="%s" rel="noopener" target="_blank">%s</a></li>' % (esc(h), esc(t)) for t, h in links) + embed_code(G)
    return block("official_links", "Official pages for this gauge", "agency", body, "Source: links to the agencies that publish the data on this page (USGS, NOAA National Weather Service); they open in a new tab.", "usgs")


def data_meta(G, name, page_url, observed):
    """data.json's source, terms, credit and citation (backlinks asset 2: open, cite us). Credit and terms are the register's own (data/sources.json), verbatim."""
    sid = "coops" if G.get("coast") else G["agy"]["src"] if G.get("agy") else "usgs"
    lv = level_of(G) if G.get("coast") else None
    src = ("NOAA CO-OPS tide predictions above MLLW (no water level is measured at this station)" if G.get("tables") else
           "NOAA CO-OPS water level above MLLW at station %s, %s, %.1f km away (this station has tide predictions only), preliminary data not yet quality-checked by NOAA" % (lv["id"], lv["name"], lv["km"]) if lv else
           "NOAA CO-OPS water level above MLLW, preliminary data not yet quality-checked by NOAA" if G.get("coast")
           else ("%s station %s, provisional" % (G["agy"]["name"], G["agy_st"])) if G.get("agy") else "USGS Water Data API, provisional data subject to revision")
    s = SOURCES.get(sid) or {}
    return {"source": src, "credit": s.get("credit") or "", "terms": s.get("terms_url") or "",
            "cite": "%s water data, %s. %s%s. %s" % (name, BRAND, src, (", observed %s" % observed) if observed else "", page_url)}


REVIEW_BLOCKS = {"like_today", "water_speed", "big_floods"}  # PLAN 20: a new block type shows only after its phone review passes (data/reviewed.json "blocks"); add each new block id here the day it is built


@__import__("functools").lru_cache(maxsize=1)
def reviewed_blocks():
    """Block ids that passed a phone review; a missing or torn file reviews none (new blocks stay hidden, old ones are unaffected)."""
    try:
        return frozenset(json.load(open(os.path.join(ROOT, "data", "reviewed.json"), encoding="utf-8")).get("blocks") or [])
    except (OSError, ValueError, AttributeError):
        return frozenset()


def block_ready(bid):
    """False only for a new block type not yet reviewed; review builds (RWL_REVIEW, dryrun review=) show it so it can be reviewed."""
    return bid not in REVIEW_BLOCKS or bid in reviewed_blocks() or bool(os.environ.get("RWL_REVIEW"))


def tab_blocks(tab, G, pages):
    if tab == "dashboard" and G.get("feed"):  # a gauge outside the US: same page, only the blocks its feed can fill; each country's sources join this list
        has_al = bool(live_alerts(G))
        return [b2.b_offline(G)] + ([b_alerts(G)] if has_al else []) + [b3.b_key_facts(G), "SEC:Level and official marks", b3.b_also(G), b2.b_stage_chart(G), b3.b_world_flow(G), b3.b_world_rate(G), b3.b_world_forecast(G), b3.b_official_marks(G), b3.b_world_history(G), b3.b_world_peaks(G), b3.b_world_wt30(G), b3.b_world_drought(G), b3.b_along(G), b3.b_world_near(G), b3.b_access(G)] + ([] if has_al else [b_alerts(G)]) + [
                "SEC:Weather at the river", b_hourly(G), b_weather(G), b3.b_world_rain(G), b_air(G), b3.b_world_aq(G), b3.b_world_normals(G), b3.b_world_links(G), b3.b_world_about(G)]
    if tab == "dashboard":  # one page per gauge, ordered by what a person at the water asks: is it dangerous, what is the water like, what is coming, how does it compare; "SEC:" is a heading, "FOLD:" a closed group
        cam = b3.b_camera(G)
        cam_now, cam_old = (cam, None) if cam and cam["tag"] == "live" else (None, cam)
        has_al = bool(live_alerts(G))
        # Search order (Keyword Planner, fresh agent 2026-11-06): coasts 'tides' 1.15M + 'tide times' 620k + 'tide chart' 96k a month, so the
        # tide chart and table lead; lakes 'water level' + 'level' 2.2M, so the level chart follows the storage block. Rivers unchanged.
        coast, lake, sc = G.get("coast"), G.get("lake"), b2.b_stage_chart(G)
        # Page order debate 2026-11-13 (owner asked; ChatGPT as editor, converged in 2 rounds): decisions first, history after. Coast: tide table, the
        # live level, surf, red tide, king tides; key facts (history) moved to 'How today compares'; snowpack to the outlook (it says what is coming).
        lead = ([b3.b_tides(G), sc, b3.b_surf(G), b3.b_redtide(G), b3.b_kingtide(G), b3.b_waves(G), b3.b_moon(G)] if coast else
                [b3.b_lake_temp(G), b3.b_reservoir(G), sc, b3.b_dam_facts(G), b3.b_waves(G)] if lake else
                [b3.b_dam_facts(G), b3.b_reservoir(G), b3.b_waves(G)])
        return [b2.b_offline(G), b2.b_flow_behind(G)] + ([b_alerts(G)] if has_al else []) + [b3.b_limits(G)] + lead + [
                "SEC:Level, flow and flood risk", b_flow_chart(G), (None if coast or lake else sc) or (None if sc else b_flood_stages(G)), b3.b_official_marks(G), b_impacts(G), b_low_water(G), b2.b_rate(G)] + ([] if has_al else [b_alerts(G)]) + [
                "SEC:What the water is like now", cam_now, b_quality(G), b3.b_depth(G), b3.b_speed(G), None if coast else b3.b_tides(G),
                "SEC:Weather at the river", b_heatmap(G) or b_hourly(G), b_weather(G), b_air(G), b3.b_air_quality(G), b_rain(G), b_radar(G),
                "SEC:River forecast", b_river_forecast(G), b_nwm(G), b2.b_nwm_medium(G), b2.b_noforecast(G), b_like_today(G), "AD",
                "SEC:Rain and longer outlook", b3.b_wpc(G), b3.b_acis(G), b2.b_qpf(G), b_snotel(G), b_cpc(G),
                "SEC:Getting on the water", b3.b_access(G), b3.b_recreation(G), b_land(G), b3.b_stocking(G), b3.b_fish(G), b3.b_moonphase(G), b3.b_dam(G),
                "SEC:Camera at the gauge", cam_old, "SEC:How today compares with past years", b3.b_key_facts(G), b3.b_month_chart(G), b3.b_year_chart(G), b_multiyear(G), b3.b_sustained(G), b_record(G), b3.b_flowdur(G), b_wtemp(G),
                "FOLD:Flood record and history", b_peaks(G), b_floods(G), b3.b_stage_years(G), b3.b_floodfreq(G), b_crests(G), b3.b_flood_outlook(G),
                "FOLD:Daily values, measurements and rating", b_daily(G), b3.b_field_meas(G), b2.b_rating(G),
                "FOLD:Watershed, water quality and land", b3.b_samples(G), b2.b_drought(G), b2.b_attains(G), b3.b_streamcat(G),
                b_related(G, pages), b_nearby(G, pages), b3.b_nws_point(G, pages), b_map(G), b_official_links(G), b2.b_about(G)]
    return []  # only the dashboard tab is built (one page per gauge)


def embed_page(G, pages):
    """The hero (alert banner, one-line answer, tiles) alone, for an iframe on a club, outfitter or county page; links back to the full page (Lakebrief comparison 2026-10-21: their one link-earning device)."""
    row = G["row"]
    rp, st = river_at(G["river"], G["place"]), G.get("st_shown") or G["st"]
    full = SITE_URL + row["dashboard_url"]
    h = hero(G, pages)
    h = h.split('<p class="src gloss"')[0]  # tiles only: no unit line, no strip
    title = "%s, %s: water level and flow (embed)" % (rp, st)
    desc = "Embeddable panel: current flow and gage height at USGS gauge %s, %s, %s, from riverwaterlevels.com." % (G["site"], rp, st)
    if G.get("tables"):
        title, desc = "%s, %s: tide times (embed)" % (rp, st), "Embeddable panel: NOAA high and low tide predictions at tide station %s, %s, %s, from riverwaterlevels.com." % (G["site"], rp, st)
    body = '<h1>%s, %s</h1><p class="sub">USGS gauge %s &middot; observed %s</p>%s<p class="src"><a href="%s" target="_top" rel="noopener">Live page with forecast, history and flood record on riverwaterlevels.com</a></p>' % (esc(rp), esc(st), G["site"], esc(G["obs"]), h, full)
    if G.get("tables"):
        body = body.replace("USGS gauge %s &middot; observed %s" % (G["site"], esc(G["obs"])), "NOAA tide station %s &middot; tide predictions" % G["site"]).replace("Live page with forecast, history and flood record", "Full page with the 7-day tide table")
    out = ('<!doctype html><html lang="en" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>%s</title><meta name="description" content="%s"><link rel="canonical" href="%s">%s<meta name="robots" content="noindex,follow"><style>%s</style></head><body><main id="main" class="embed">%s</main></body></html>' % (
        esc(title), esc(desc), SITE_URL + "/embed" + row["dashboard_url"], HEAD_EXTRA + og_tags(title, desc, full), CSS, body))
    return lake_words(out, G) if G.get("lake") else out  # lake review #6: the embed copy said flow and gage height


@__import__("functools").lru_cache(maxsize=1)
def research_open():
    """PLAN 20, links rule: the footer links /research/ only when Google may index it (open_wave added it to the allow list)."""
    from lib import indexing
    try:
        return indexing.indexable("/research/", indexing.load(ROOT))
    except (OSError, ValueError):
        return False


def footer():
    return ('<footer><span>%s &middot; Data: USGS, NOAA, NWS.</span><span><a href="/about/">About</a><a href="/data-sources/">Data sources</a><a href="/disclaimer/">Disclaimer</a>'
            '<a href="/faq/">FAQ</a><a href="/methodology/">Methodology</a>%s<a href="/privacy/">Privacy</a><a href="/terms/">Terms</a><a href="/glossary/">Glossary</a><a href="/status/">Data status</a><a href="/embed/">Add to your site</a>%s</span></footer>' % (esc(BRAND), '<a href="/research/">Research</a>' if research_open() else "", '<a href="/contact/">Contact</a>' if publisher().get("email") else ""))


def og_tags(title, desc, url):
    return ('<meta property="og:type" content="website"><meta property="og:site_name" content="%s"><meta property="og:title" content="%s"><meta property="og:description" content="%s"><meta property="og:url" content="%s"><meta property="og:image" content="%s/og.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="River Water Levels: current flow, gage height and how it compares with normal for US river gauges"><meta name="twitter:card" content="summary_large_image">'
            % (esc(BRAND), esc(title), esc(desc), esc(url), SITE_URL))


def mk_title(base):
    return base  # one pattern on every page; the brand sits in the nav


def dash_tail(wt, fc, tb=False):
    """Title words after 'water level and flow', each only while its block shows: never a promise the page breaks."""
    return (", tubing rules" if tb else "") + (", NWS forecast" if fc else "") + (", water temperature" if wt else "")


def flood_stage_txt(n):
    """'flood stage 30 ft' from the NWS minor flood category (static: no reading), '' when unset, zero or not a number."""
    v = (n.get("categories") or {}).get("minor")
    return ("flood stage %g %s" % (round(v, 1), (n.get("stage_units") or "ft").lower())) if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 else ""


assert flood_stage_txt({"categories": {"minor": 30.0}}) == "flood stage 30 ft" and flood_stage_txt({"categories": {"minor": 23.5}, "stage_units": "FT"}) == "flood stage 23.5 ft", "page: flood stage text"
assert flood_stage_txt({}) == "" and flood_stage_txt({"categories": {"minor": -9999}}) == "" and flood_stage_txt({"categories": {"action": 5}}) == "" and flood_stage_txt({"categories": {"minor": True}}) == "", "page: flood stage unset"


TUBING_RULE = re.compile(r"tubing|all recreation|all water activities", re.I)  # PLAN 25b: an agency rule that covers tubing ('<river> tubing' 1K-10K at Comal, Guadalupe, Chattahoochee)
assert dash_tail(True, True) == ", NWS forecast, water temperature" and dash_tail(False, False) == "" and dash_tail(False, True, True) == ", tubing rules, NWS forecast", "page: title tail"
assert TUBING_RULE.search("tubing within city limits") and TUBING_RULE.search("All water activities") and not TUBING_RULE.search("expert paddlers only") and not TUBING_RULE.search("life jackets"), "page: tubing rule match"


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
    if "usgs" not in ids and not G.get("coast"):
        ids.insert(0, "usgs")
    lis = ""
    for i in ids:
        s = SOURCES[i]
        lis += '<li>%s. <a href="%s" rel="noopener">Terms</a></li>' % (esc(s["name"].rstrip(".")), esc(s["terms_url"]))  # black-hat review 2026-11-11: the credit sentence is already under each block (core.credit_line); the list names the source
    stats_src = G["rec"].get("stats_source")
    return ('<details class="card fold srcall" data-g="data" id="sources"><summary><b>Sources and method</b><span>%d data sources, how the percentile is calculated, disclaimer</span></summary><ul>%s</ul><p class="src">%s</p><p class="src">Percentile method: %s.</p><p class="src">%s</p></details>' % (
        len(ids), lis, esc(humanize_iso(stats_src) if stats_src else "Tide comparison: NOAA CO-OPS 6-minute predictions for this station; the difference is our calculation." if G.get("coast") else "USGS daily statistics: not available for this gauge."), esc(G["method"]), esc(DISCLAIMER)))


# the age chip in the browser: the same text and rounding as age_text() in lib/core.py; worker/index.js carries this exact line (check.py --selftest)
# a time in the browser, written as tzl() in lib/core.py writes it: no-break spaces except after the comma (Intl uses narrow ones); Z is the gauge's zone
LT_FN = "function lt(d){return d.toLocaleString('en-US',{timeZone:Z,month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'}).replace(/\\s/g,'\\u00a0').replace(/,\\u00a0/g,', ')}"
AGE_FN = "function age(d){var m=Math.round((Date.now()-d)/60000);return m<180?m+' min':m<2880?Math.round(m/60)+' h':Math.round(m/1440)+' d'}"


LIVE_JS = """<script>(function(){var ID="USGS-@SITE@",Z="@TZ@",hero=document.querySelector('.hero');if(!hero||!window.fetch)return;var snap=Date.parse(hero.getAttribute('data-t')),n=0;
function q(k){return document.querySelector('[data-live="'+k+'"]')}
function f(v){var a=Math.abs(v);return a>=1000?Number(v.toPrecision(3)).toLocaleString('en-US'):a<1&&v!==0?v.toFixed(2):Math.round(v).toLocaleString('en-US')}
""" + LT_FN + """
""" + AGE_FN + """
var ag=q('age'),ag0=ag&&Date.parse(ag.getAttribute('data-t'));if(ag)ag.textContent=age(new Date(ag0||snap));
function edge(){return fetch('/live/'+ID.slice(5)+'.json').then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(j){var g=j&&j.g&&j.g[ID.slice(5)];if(!g||!g.f||g.f[2]||!(g.f[0]>-999)||!j.t||Date.now()-Date.parse(j.t)>1800000)throw 0;return [{v:g.f[0],t:new Date(g.f[1])},g.h&&!g.h[2]&&g.h[0]>-999?{v:g.h[0],t:new Date(g.h[1])}:null]})}
function apply(a){var F=a[0],S=a[1];
if(F&&F.t.getTime()>=snap){q('flow').textContent=f(F.v);var ld=q('lead');if(ld)ld.textContent=f(F.v)+' cfs';var fo=q('flowobs');if(fo)fo.textContent=lt(F.t);q('obs').textContent=lt(F.t);[].slice.call(document.querySelectorAll('[data-cf]')).forEach(function(e){e.textContent=f(F.v)});[].slice.call(document.querySelectorAll('[data-co]')).forEach(function(e){e.textContent=lt(F.t)});if(ag)ag.textContent=age(F.t);var mn=(Date.now()-F.t)/60000;[].slice.call(document.querySelectorAll('span.ab')).forEach(function(e){e.className='ab '+(mn<=@FRESH@?'fresh':mn<=@AGEING@?'ageing':'stale')});var st=q('stage'),so=q('stageobs');if(S&&st&&S.t.getTime()>=snap){st.textContent=S.v.toFixed(2);[].slice.call(document.querySelectorAll('[data-cs]')).forEach(function(e){e.textContent=S.v.toFixed(2)});if(so)so.textContent=lt(S.t)}if(Date.now()-F.t.getTime()<@LIVE_MS@)[].slice.call(document.querySelectorAll('.tag.t-last')).forEach(function(e){e.className='tag t-live';e.textContent='Live gauge'});if(F.t.getTime()>snap){[].slice.call(document.querySelectorAll('.fcnote')).forEach(function(e){e.hidden=true});var bn=document.getElementById('lbn');if(!bn){bn=document.createElement('p');bn.id='lbn';bn.className='src lf2';var an=document.querySelector('p.answer')||hero;an.parentNode.insertBefore(bn,an.nextSibling)}bn.textContent=(S&&st&&S.t.getTime()>=snap?'Flow and gage height':'Flow')+' at the top updated '+lt(F.t)+'. Charts, tables and comparisons below are as of the page build, '+lt(new Date(snap))+'.';var nt=' The flow above is newer than this comparison, which is as of '+lt(new Date(snap))+'.',pc=document.getElementById('pcap'),cc=document.getElementById('ccap');if(pc){pc.setAttribute('data-n','1')}if(cc&&cc.getAttribute('data-n')!=='1'){cc.textContent+=nt;cc.setAttribute('data-n','1')}}}}
function fail(){var a=q('age'),hh=document.querySelector('.hero2'),old=hh&&(Date.now()-new Date(hh.getAttribute('data-t')))>3600000;if(a&&old&&!document.getElementById('lf')){var s=document.createElement('span');s.id='lf';s.className='lf';s.textContent=' \u00b7 the newest reading could not be loaded just now';a.parentNode.parentNode.appendChild(s)}}
function run(){edge().then(apply).catch(fail)}
run();document.addEventListener('visibilitychange',function(){if(!document.hidden)run()});setInterval(function(){if(!document.hidden)run()},300000)})();</script>""".replace(
    "@FRESH@", "%d" % (STALE_H["chip_fresh"] * 60)).replace("@AGEING@", "%d" % (STALE_H["chip_ageing"] * 60)).replace("@LIVE_MS@", "%d" % (STALE_H["usgs"] * 3600000))  # cut-offs from the one table


AGE_JS = """<script>(function(){var a=document.querySelector('[data-live="age"][data-t]');if(!a)return;var t=Date.parse(a.getAttribute('data-t'));""" + AGE_FN + """function u(){a.textContent=age(t)}u();setInterval(u,60000)})();</script>"""
# audit 2026-11-10 #15: a carried coast page can sit for hours; once the shown "next tide" has passed, step to the next one in the tile's own NOAA list (data-tides, lib/hero.py), or say none is left
TIDE_JS = """<script>(function(){var e=document.querySelector('[data-tides]');if(!e)return;var Z="@TZ@",h=document.querySelector('[data-tideh]'),w=document.querySelector('[data-tidet]');""" + LT_FN + """function u(){var L=e.getAttribute('data-tides').split(';'),n=Date.now(),i,p;for(i=0;i<L.length;i++){p=L[i].split('|');if(Date.parse(p[0])>n)break}if(i===0)return;if(i>=L.length){e.textContent='Unknown';if(h)h.textContent='';if(w)w.textContent='No later NOAA prediction on this page';return}e.setAttribute('data-tide',p[0]+'|'+p[1]);e.setAttribute('data-tides',L.slice(i).join(';'));e.textContent=p[2]==='H'?'High':'Low';if(h)h.textContent=(Math.round(+p[1]*10)/10+0).toFixed(1)+' ft';if(w)w.textContent=lt(new Date(p[0]))}u();setInterval(u,60000)})();</script>"""


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


THEME_JS = """<script>(function(){var r=document.documentElement,b=document.getElementById('themebtn');try{if(localStorage.getItem('rwl_theme')==='dark')r.removeAttribute('data-theme')}catch(e){}if(b)b.addEventListener('click',function(){var l=r.getAttribute('data-theme')==='light';if(l)r.removeAttribute('data-theme');else r.setAttribute('data-theme','light');try{localStorage.setItem('rwl_theme',l?'dark':'light')}catch(e){}})})();</script>"""


CITE_JS = """<script>(function(){var b=document.querySelector('[data-cite]');if(!b||!navigator.clipboard)return;b.addEventListener('click',function(){navigator.clipboard.writeText(b.parentNode.querySelector('small').textContent.replace(/^Cite: /,'')).then(function(){b.textContent='Copied'})})})();</script>"""
NAVSEARCH_JS = """<script>window.RWS=(function(){function nz(s){return String(s||'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/\\bst\\.? /g,'saint ').replace(/[^a-z0-9]+/g,' ').trim()}
function e1(a,b){if(a===b)return 1;var x=a.length,y=b.length,i=0;if(Math.abs(x-y)>1)return 0;while(i<x&&i<y&&a[i]===b[i])i++;return x===y?a.slice(i+1)===b.slice(i+1):x>y?a.slice(i+1)===b.slice(i):a.slice(i)===b.slice(i+1)}
function tm(t,ws){for(var k=0;k<ws.length;k++){var w=ws[k];if(w.indexOf(t)>=0)return 1;if(t.length>=5&&(e1(t,w)||e1(t,w.slice(0,t.length))||e1(t,w.slice(0,t.length-1))||e1(t,w.slice(0,t.length+1))))return 1}return 0}
function fm(q,h){var ts=nz(q).split(' ').filter(Boolean),ws=nz(h).split(' ');return ts.every(function(t){return tm(t,ws)})}
function bg(s){var o={};for(var k=0;k<s.length-1;k++)o[s.substr(k,2)]=1;return o}
function uq(l){var s={};return l.filter(function(g){if(s[g[1]])return false;s[g[1]]=1;return true})}
function near(q,l,n){var a=bg(nz(q));var r=l.map(function(g){var b=bg(nz(g[0])),c=0,na=0,nb=0,m;for(m in a)na++;for(m in b){nb++;if(a[m])c++}return [2*c/((na+nb)||1),g]}).sort(function(x,y){return y[0]-x[0]}).map(function(x){return x[1]});return uq(r).slice(0,n)}
return {nz:nz,fm:fm,near:near,uq:uq}})();
(function(){var i=document.getElementById('gq'),o=document.getElementById('gr'),d=null;if(!i||!o||!window.fetch)return;function load(){if(d)return Promise.resolve(d);return fetch('/gauges.json').then(function(r){return r.json()}).then(function(j){d=j;return j}).catch(function(){d=[];return d})}
function ln(g){var a=document.createElement('a');a.href=g[1];a.textContent=g[0];o.appendChild(a)}
function show(q){var nq=RWS.nz(q);o.textContent='';if(nq.length<2){o.hidden=true;return}load().then(function(j){var hits=j.filter(function(g){return RWS.fm(q,g[0]+' '+(g[4]||''))});hits.sort(function(a,b){return (RWS.nz(a[0]).indexOf(nq)===0?0:1)-(RWS.nz(b[0]).indexOf(nq)===0?0:1)});RWS.uq(hits).slice(0,8).forEach(ln);if(!hits.length){var s=document.createElement('span');s.textContent='No gauge name matches. Nearest names:';o.appendChild(s);RWS.near(q,j,5).forEach(ln);var t=document.createElement('span');t.innerHTML='This site has '+j.length+' gauges so far. <a href="https://water.noaa.gov/" rel="noopener">Look up any river at water.noaa.gov</a>';o.appendChild(t)}o.hidden=false})}
i.addEventListener('input',function(){show(i.value)});i.addEventListener('keydown',function(e){if(e.key==='Enter'){var as=o.querySelectorAll('a[href^="/river/"]'),a=null;for(var k=0;k<as.length;k++){if(as[k].getAttribute('href')!==location.pathname){a=as[k];break}}if(a){e.preventDefault();location.href=a.getAttribute('href')}}});i.addEventListener('focus',load);document.addEventListener('click',function(e){if(!o.contains(e.target)&&e.target!==i)o.hidden=true})})();</script>"""


WX_JS = """<script>(function(){var m=document.querySelector('[data-wxst]');if(!m||!window.fetch)return;var st=m.getAttribute('data-wxst'),t0=Date.parse(m.getAttribute('data-t')),Z="@TZ@",C=['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW'];
""" + LT_FN + """
function put(k,v){[].slice.call(document.querySelectorAll('[data-wx="'+k+'"]')).forEach(function(e){e.textContent=v})}
function run(){fetch('https://api.weather.gov/stations/'+encodeURIComponent(st)+'/observations/latest',{headers:{Accept:'application/geo+json'}}).then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(j){var p=j&&j.properties,t=p&&Date.parse(p.timestamp);if(!t||!(t>t0))return;var V=function(k){return p[k]&&typeof p[k].value==='number'?p[k].value:null},c=V('temperature'),w=V('windSpeed'),d=V('windDirection'),g=V('windGust'),b=V('barometricPressure'),v=V('visibility');if(c===null)return;var NR='not reported',mph=w!==null?w*0.621371:null,wd=mph===null?NR:mph<1?'Calm':(d!==null?C[Math.floor(((d%360)/22.5)+0.5)%16]+' ':'')+Math.round(mph)+' mph';
put('temp',Math.round(c*9/5+32)+' \u00b0F');put('temp0',Math.round(c*9/5+32));put('wind',wd);put('gust',g!==null?Math.round(g*0.621371)+' mph':NR);put('pres',b!==null?(b/3386.389).toFixed(2)+' inHg':NR);put('vis',v!==null?Math.round(v/1609.34)+' mi':NR);
put('wind0',(mph===null?'':mph<1?'wind calm':'wind '+wd.replace(' mph','')+' mph')+(g!==null?', gusts '+Math.round(g*0.621371)+' mph':''));[].slice.call(document.querySelectorAll('[data-wx="note"]')).forEach(function(e){e.remove()});put('t',lt(new Date(t)));t0=t;
var s=m.closest('section');if(s)[].slice.call(s.querySelectorAll('.tag.amber')).forEach(function(e){e.remove()})}).catch(function(){})}
run();document.addEventListener('visibilitychange',function(){if(!document.hidden)run()});setInterval(function(){if(!document.hidden)run()},600000)})();</script>"""


ALERTS_JS = """<script>(function(){var b=document.getElementById('alerts');if(!b||!window.fetch)return;var Z="@TZ@",CTY="@CTY@",IG=['Test Message','Administrative Message'];
""" + LT_FN + """
function ast(p){var s=[];((p.geocode&&p.geocode.UGC)||[]).forEach(function(u){var k=u.slice(0,2);if(s.indexOf(k)<0)s.push(k)});return s.length?' ('+s.sort().join(', ')+')':''}
function as(s){var a=s.split(';').map(function(x){return x.trim()}).filter(Boolean),c=CTY.toLowerCase().replace(/ (county|parish)$/,'');if(c){var m=a.filter(function(x){var y=x.toLowerCase();return y===c||y.slice(-c.length-1)===' '+c});a=m.concat(a.filter(function(x){return m.indexOf(x)<0}))}return a.length<=6&&!c?s:a.slice(0,6).join('; ')+(a.length>6?'; and '+(a.length-6)+' more areas':'')}
function el(t,c,x){var e=document.createElement(t);if(c)e.className=c;if(x)e.textContent=x;return e}
Promise.all(['point=@LAT@,@LON@'].concat('@MZ@'?['zone=@MZ@']:[]).map(function(q){return fetch('https://api.weather.gov/alerts/active?'+q,{headers:{Accept:'application/geo+json'}}).then(function(r){return r.json()})})).then(function(a){var j=a[0];if(!j||!j.features||(a.length>1&&!(a[1]&&a[1].features)))return;var ids=j.features.map(function(f){return f.id});(a[1]?a[1].features:[]).forEach(function(f){if(ids.indexOf(f.id)<0)j.features.push(f)});
var al=j.features.map(function(f){return f.properties}).filter(function(p){return IG.indexOf(p.event)<0}),src=b.querySelector('.srcd')||b.querySelector('.src'),sp=b.querySelector('.src');if(!src||!sp)return;
Array.prototype.slice.call(b.children).forEach(function(c){if(c.tagName!=='H2'&&c!==src)b.removeChild(c)});
b.classList.toggle('emp',!al.length);if(!al.length){b.insertBefore(el('p','','No active National Weather Service alerts were returned for this location. This is not a statement that conditions are safe.'),src)}
al.forEach(function(p){var d=el('div','alert'),e=p.ends||p.expires;d.appendChild(el('b','',p.event||''));d.appendChild(document.createTextNode(' \\u00b7 '+(p.severity||'severity not stated')+' \\u00b7 '+(as(p.areaDesc||'')+ast(p))));d.appendChild(document.createElement('br'));d.appendChild(document.createTextNode(p.headline||''));d.appendChild(document.createElement('br'));d.appendChild(document.createTextNode('Ends '+(e?lt(new Date(e)):'not stated')));b.insertBefore(d,src)});
var bn=document.querySelector('a.abanner'),hr=document.querySelector('.hero');if(al.length){if(!bn&&hr){bn=el('a','abanner');bn.href='#alerts';hr.parentNode.insertBefore(bn,hr)}if(bn){bn.textContent='';bn.appendChild(el('b','',al.length+' active National Weather Service alert'+(al.length===1?'':'s')));bn.appendChild(el('span','',al.map(function(p){return p.event}).join('; ')));bn.appendChild(el('em','','Details'))}}else if(bn){bn.parentNode.removeChild(bn)}
var t=document.querySelector('.tile.alrt');if(t){var tv=t.querySelector('b'),ts=t.querySelector('small');t.className='tile alrt '+(al.length?'on':'off');if(tv)tv.textContent=al.length||'No alerts';if(ts)ts.textContent=al.length?al.map(function(p){return p.event}).join('; '):'No alerts active here. Checked live '+lt(new Date())+'.'}
var pl=document.querySelector('.answer .a3');if(pl){pl.className='a3 '+(al.length?'ay':'an');pl.textContent=al.length?al.length+' active NWS alert'+(al.length===1?'':'s'):'No active NWS alerts'}
sp.textContent='Source: National Weather Service alerts for the gauge location'+('@MZ@'?' and marine zone @MZ@':'')+', fetched '+lt(new Date())+' (live from the NWS when this page loaded).'}).catch(function(){})})();</script>"""


INDEX_CFG = None  # set by build.py from data/index-allow.json


def agency_words(h, G):
    """A lake read from its operator's feed (CDEC): every line that named USGS as the reading's source names the operator's feed; USGS stays only where it
    is the real source (PAD-US public land, USGS Topo map). Sentences about USGS sensors or statistics this page never searched for are deleted, not reworded."""
    a, st, s = G["agy"]["short"], G["agy_st"], G["site"]
    for x, y in (("USGS lake gauge %s" % s, "%s %s" % (G["agy"]["label"], st)), ("USGS gauge %s" % s, "%s %s" % (G["agy"]["label"], st)), ("(USGS %s" % s, "(%s %s" % (a, st)),
                 ("Water stored in the reservoir, USGS", "Water stored in the reservoir, %s" % a), ("Solid line: USGS readings", "Solid line: %s readings" % a), ("Latest USGS lake elevation", "Latest %s lake elevation" % a),
                 ("Source: USGS Water Data API (continuous lake elevation)", "Source: %s, station %s, %s %s" % (G["agy"]["name"], st, G["agy"]["every"], G["agy"].get("what", "reservoir elevation and storage, provisional"))),
                 ("(USGS, provisional)", "(%s, provisional)" % a), ("(USGS, NOAA National Weather Service)", "(%s, NOAA National Weather Service)" % a), ("Data: USGS, NWS.", "Data: %s, NWS." % a),
                 ("Percentile is estimated from USGS published daily percentiles. Readings are provisional until USGS reviews them.", "Readings are provisional; %s may revise them." % a)):
        h = h.replace(x, y)
    said = []  # release 2026-11-07: the same parenthesis three times on the first screen (Lake Travis) is clutter; it is said once, the later copies are dropped
    h = re.sub(r" ?\(no USGS (?:temperature|turbidity or water-quality) sensor[^)]*\)", lambda m: "" if said else (said.append(1) or " (not in the %s feed this page reads)" % a), h)  # never "publishes none": nobody searched the agency's whole catalogue
    h = h.replace("USGS publishes no storage for this lake.", G["agy"].get("no_storage", "Not in the %s feed this page reads." % a))
    if G["agy"].get("day_avg"):  # TWDB rows are daily averages stored at local midnight: the midnight clock time is ours, never TWDB's, so every printed copy becomes the date
        dz = zoneinfo.ZoneInfo(G["agy"].get("day_tz") or G["tzname"])  # the agency's own day (Reclamation: Arizona; 07:00 UTC Nov 4 is Nov 3, 11 PM on a Pacific page)
        sw = [(tzl(t_, G["zone"]), tzl(t_, dz).split(",")[0] + " (%s daily %s)" % (a, G["agy"].get("day_word", "average"))) for t_ in {parse_t(r["time"]) for r in G["rec"]["usgs"]["rows"]}]
        def day_(m):  # review 2026-11-07 #2: only the reading's own blocks; an NWS alert or forecast at midnight keeps its real time
            if m.group(1) not in ("stage_chart", "reservoir", "sources", "official_links", None):
                return m.group(0)
            s_ = m.group(0)
            for x, y in sw:
                s_ = s_.replace(x, y)
            return s_
        h = re.sub(r'<section[^>]*? id="([a-z_0-9]+)".*?</section>|(?:(?!<section).)+', day_, h, flags=re.S)
    return re.sub(r"(?:USGS daily statistics: not available for this gauge|Percentile method: latest reading compared with USGS daily percentiles for [^.<]*)\. ?", "", h)


def lake_words(h, G):
    """A lake page in lake words (plan 2026-11-05 step 1). The elevation is height above a named datum, never "the gauge's zero point": that line would be false here."""
    d = lake_datum(G)
    al = re.search(r'<section class="card blk[^"]*" data-f="[^"]*" id="alerts">.*?</section>', h, re.S)  # lake review #13: quoted NWS alert text is never reworded
    if al:
        return lake_words(h[:al.start()], G) + al.group(0) + lake_words(h[al.end():], G)
    st_ = bool(series(G["rec"], "00054"))  # 72036 (thousand acre-ft) counts: lib/core.py series
    sto = " and storage" if st_ else ""  # Lake Michigan review 2026-11-11 (blocker): "storage readings" on a lake with no storage contradicted its own tile
    h = re.sub(r"7-day flow and gage height readings(?:,| and) daily mean flow by year", "7-day lake elevation%s readings" % sto, h)  # lake review #8: data.json and JSON-LD said flow
    h = h.replace("flow and gage height", "lake elevation" + sto)
    h = h.replace(", flow not reporting (USGS", " above %s (USGS" % d)  # lake review #13: the cite line said flow is not reporting; a lake has none
    h = re.sub(r"cfs = cubic feet of water passing the gauge each second\. Gage height is the gauge(?:’|&rsquo;|')s own scale, not water depth\.", "Lake elevation is the water surface above %s, in feet; it is not depth." % d, h)
    h = re.sub(r" About (?:1 dam|[\d,]+ dams) upstream \(our estimate: [^)]*\) may have changed flows during this record\.", "", h)  # a reservoir is itself the dam
    if G["lake"] in ("62614", "62615", "72020"):  # hater review 2026-11-07 (Powell 3,719 ft, Barren 500 ft): the reading is already above a sea-level datum, so the USGS gauge-zero altitude reads as a contradiction
        h = re.sub(r"<tr><td>Altitude of the gauge(?:'|&#x27;|&#39;|’|&rsquo;)s zero point</td><td>[^<]*</td></tr>", "", h)
    if G["lake"] == "00062":  # only this code is read above the gauge datum; 62614, 62615 and 72020 are above sea-level datums, so the row keeps its own true label
        h = re.sub(r"Altitude of the gauge(?:'|&#x27;|&#39;|’|&rsquo;)s zero point", "Gauge datum (lake readings are heights above it)", h)
    for a, b in (("river access not confirmed", "shore access not confirmed"), ("Every stage and reading in a table", "Every reading in a table"),  # Lake Michigan review 2026-11-11: river words on a lake page
                 ("how the percentile is calculated", "how the percentile is calculated" if G.get("p") is not None else "how each number is calculated"),
                 ("Data: USGS, NOAA, NWS.", "Data: NOAA, NWS." if G["lake"] == "IGLD" else "Data: USGS, NOAA, NWS."),  # a Great Lake page reads no USGS data
                 ("water level and flow", "water level, elevation and storage" if st_ else "water level and elevation"),  # release gate: the title names the search ("water level"); storage only where USGS publishes it
                 ("E. coli results at stations on this river within", "E. coli results at stations on the rivers within"), ("E. coli samples on this stretch", "E. coli samples nearby"), ("within 40 mi on this river", "within 40 mi on the rivers here"), ("for this stretch", "near this lake"), ("Gage height", "Lake elevation"), ("gage height", "lake elevation"),
                 ("Height above the gauge's zero point, not water depth", "Water surface above %s, not depth" % d),
                 ("cfs = cubic feet of water passing the gauge each second. Gage height is the gauge’s own scale, not water depth.", "Lake elevation is the water surface above %s, in feet; it is not depth." % d),
                 ("<span>River forecast</span>", "<span>Level forecast</span>"), (">River forecast<", ">Level forecast<"), ("Weather at the river", "Weather at the lake"), ("Level, flow and flood risk", "Lake level and flood risk"),
                 ("USGS gauge %s" % G["site"], "USGS lake gauge %s" % G["site"])):
        h = h.replace(a, b)
    if G.get("agy"):
        h = agency_words(h, G)
    if G.get("lake") == "IGLD":  # a Great Lake: the search is the water temperature ('lake michigan water temp' 10K-100K); the title names it only while GLERL's lake-wide value is in the cache
        h = h.replace("water level and elevation", "water level")  # the title's water-temperature words come from the fresh-reading rule (d7900dd), never twice
        for a, b in (("USGS sensor", "NOAA shoreline sensor"), ("Source: USGS Water Data API (continuous values)", "Source: NOAA CO-OPS shoreline station (preliminary)")):
            h = h.replace(a, b)
    if G.get("coast"):  # a coast page: the lake path's words in coast words, and the reading's source is NOAA CO-OPS, never USGS
        for a, b in (("water level and elevation", "tide times, water level and water temperature" if b3.conditions(G).get("wt") else "tide times and water level"), ("USGS lake gauge %s" % G["site"], "NOAA tide station %s" % G["site"]), ("(USGS %s)" % G["site"], "(NOAA %s)" % G["site"]), ("(USGS %s, observed" % G["site"], "(NOAA CO-OPS %s, observed" % G["site"]),
                     ("Data: USGS, NWS.", "Data: NOAA CO-OPS, NWS."), ("USGS sensor", "NOAA sensor"), ("Solid line: USGS readings", "Solid line: NOAA readings (preliminary)"), (" &middot; dashed curve: NWS forecast", " &middot; dashed curve: NOAA predicted tide, next 24 h"), ("Source: USGS Water Data API (continuous lake elevation)", "Source: NOAA CO-OPS 6-minute water level above MLLW, preliminary data that NOAA has not quality-checked"), ("Source: USGS Water Data API (continuous values)", "Source: NOAA CO-OPS (preliminary)"),
                     ("Percentile is estimated from USGS published daily percentiles. Readings are provisional until USGS reviews them.", "Water levels are preliminary until NOAA verifies them."),
                     ("The National Weather Service has no river forecast point for this gauge. The weather forecast below is not a river forecast.", "The National Weather Service has no forecast point for this station. NOAA tide predictions are under Tides."),
                     ("Lake elevation", "Water level"), ("lake elevation", "water level"), ("Weather at the lake", "Weather at the coast"), ("Lake level and flood risk", "Weather and flood alerts"), ("near this lake", "near this station"),
                     ("Latest USGS water level", "Latest NOAA water level"), (" Predictions, not observations; the river level here also depends on flow from upstream.", " Predictions, not observations."),
                     ("river access not confirmed", "shore access not confirmed"), ("Live gauge", "Live station"), ("this gauge", "this station"), ("the gauge location", "the station location"), ("from the gauge", "from the station"), ("Gauge location", "Station location"), ("this gauge's", "this station's"), ("this gauge&#x27;s", "this station&#x27;s"),
                     ("The National Weather Service publishes no flood stages for this station, so none are drawn.", ""), ("(USGS, NOAA National Weather Service)", "(NOAA CO-OPS, NOAA National Weather Service)")):
            h = h.replace(a, b)
        h = re.sub(r"[^.<>]*the table is for the nearest NOAA tide station, [\d.]+ mi away, where the river is tidal\.", "NOAA high and low tide predictions for this station.", h)
        h = re.sub(r"Tides nearby at [^<\"]*, next two days", "Tide predictions at this NOAA station, next two days", h)
        for a, b in (("gauge-local time", "station time"), ("live water temperature (no USGS temperature sensor at this station or within 40 mi on the rivers here)", "live water temperature (none in NOAA's water temperature feed for this station in the last 3 days)"), ("clarity (no USGS turbidity or water-quality sensor at this station)", "clarity (no NOAA water-quality sensor at this station)"), ("Hours are gauge-local;", "Hours are station time;"), ("how the percentile is calculated", "how the tide comparison is calculated"), ("a report nearby may not concern this river.", "a report nearby may not concern this stretch of coast."), ("Other gauges on this site (none on this river within 100 mi)", "Other gauges and stations on this site")):
            h = h.replace(a, b)
        h = re.sub(r"Percentile method: [^<]*", "Comparison method: the latest NOAA reading against NOAA's predicted tide for the same 6-minute time (our calculation).", h)
        lv = (G["rec"].get("coops") or {}).get("level")
        if lv:  # prediction-only station (owner 2026-11-08): every reading line names the nearby station it comes from; high and low tides stay this station's own
            h = h.replace(">Live station<", ">Live at %s<" % esc(lv["name"]))  # fresh review 2026-11-08: a 'Live station' badge on a predictions-only station read as its own reading
            at = "NOAA station %s, %s" % (esc(lv["id"]), esc(lv["name"]))  # the distance is said once, on the water level tile (hater rule: one phrase 3 times on the first screen)
            for a, b in (("NOAA tide station %s &middot; observed" % G["site"], "NOAA tide station %s, tide predictions &middot; water level at %s, observed" % (G["site"], at)),  # review 2026-11-08 blocker 1: the own id beside an observed time
                         ("(NOAA CO-OPS %s, observed" % G["site"], "(NOAA CO-OPS %s, %s, observed" % (esc(lv["id"]), esc(lv["name"]))),  # blocker 2: the citation named the page's own station
                         ("Water quality sensors", "Water quality sensors at %s" % esc(lv["name"])),  # major 5
                         ("Source: NOAA CO-OPS 6-minute water level above MLLW,","Source: NOAA CO-OPS 6-minute water level above MLLW at %s," % at), ("Source: NOAA CO-OPS (preliminary)", "Source: NOAA CO-OPS (preliminary), readings at %s" % at),
                         ("Tide comparison: NOAA CO-OPS 6-minute predictions for this station;", "Tide comparison: NOAA CO-OPS 6-minute predictions for %s, where the water level is read;" % at), ("NOAA sensor", "NOAA sensor at %s" % esc(lv["name"])), ("NOAA tidal datum at this station)", "NOAA tidal datum at %s)" % esc(lv["name"])),
                         ("Latest NOAA water level", "Latest NOAA water level, at %s," % at), ("Solid line: NOAA readings (preliminary)", "Solid line: NOAA readings at %s (preliminary)" % at), ("dashed curve: NOAA predicted tide, next 24 h", "dashed curve: NOAA predicted tide there, next 24 h"),
                         ("3-day water level readings (NOAA CO-OPS, preliminary)", "3-day water level readings at NOAA station %s (NOAA CO-OPS, preliminary)" % esc(lv["id"])),
                         ("the latest NOAA reading against NOAA's predicted tide for the same 6-minute time", "the latest NOAA reading at %s against NOAA's predicted tide there for the same 6-minute time" % at)):
                h = h.replace(a, b)
        if G.get("tables"):  # tide tables (owner decision 3): no reading here, so no reading words, comparison or embed of a 'live' level
            for a, b in (("This page&#x27;s data as JSON: 3-day water level readings (NOAA CO-OPS, preliminary)", "This page&#x27;s data as JSON: 7 days of NOAA high and low tide predictions"),
                         ('<p class="src">Tide comparison: NOAA CO-OPS 6-minute predictions for this station; the difference is our calculation.</p>', ""),
                         ("Water levels are preliminary until NOAA verifies them.", "NOAA tide predictions do not include wind, air pressure or river flow, so the water can be higher or lower than predicted."),
                         ("this station&#x27;s live panel", "this station&#x27;s tide panel"), ("Embed this live panel", "Embed this tide panel"),
                         (">Live station<", ">On this site<"), ("title=&quot;%s water level&quot;" % esc(G["river"]), "title=&quot;%s tide times&quot;" % esc(G["river"])), ("tide times and water level", "tide times and tide table"),
                         ("Water level is the water surface above mean lower low water", "Tide heights are above mean lower low water"), ("in feet; it is not depth.", "in feet; not water depth."), (", how the tide comparison is calculated", "")):
                h = h.replace(a, b)
            h = re.sub(r'<p class="src">Comparison method: [^<]*</p>', "", h)
    return h


def robots_meta(path):
    from lib import indexing
    return indexing.robots_meta(path, INDEX_CFG) if INDEX_CFG is not None else ""


# the radar loop is a ~1 MB animated image: it loads when the reader taps the button (the button is a plain link to the loop when scripts are off)
RADAR_JS = """<script>(function(){var b=document.querySelector('[data-radar]'),i=document.querySelector('[data-radar-img]');if(!b||!i)return;b.addEventListener('click',function(){i.src=b.getAttribute('data-radar');i.hidden=false;b.hidden=true})})();</script>"""
HEAD_EXTRA = '<link rel="icon" href="/favicon.svg" type="image/svg+xml"><meta name="theme-color" content="#1d5fa8">'


def crumb_ld(items):
    """BreadcrumbList markup that mirrors the visible breadcrumb exactly (name, absolute URL)."""
    els = [{"@type": "ListItem", "position": i + 1, "name": n, **({"item": SITE_URL + u} if u else {})} for i, (n, u) in enumerate(items)]
    return '<script type="application/ld+json">%s</script>' % json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": els}, separators=(",", ":")).replace("</", "<" + chr(92) + "/")


JUMP = (("alerts", "Alerts"), ("flow_chart", "7 days"), ("stage_chart", "Gage height"), ("official_marks", "Official marks"), ("river_forecast", "River forecast"), ("hourly_heatmap", "Hourly forecast"), ("hourly_forecast", "Hourly forecast"),
        ("weather_forecast", "7-day weather"), ("month_chart", "30 days"), ("multi_year", "Earlier years"), ("world_history", "Earlier years"),
        ("record_comparison", "Record"), ("annual_peaks", "Flood record"), ("related_gauges", "Upstream and downstream"), ("along_river", "Along the river"), ("nearby_gauges", "Nearby gauges"), ("about_gauge", "About"))  # world ids too: England had no jump links (UI review 2026-11-04)


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
    ok = lambda b: b and (PREVIEW or SOURCES[b["src_id"]]["status"] in ("quoted", "owner-permission")) and block_ready(b["id"])
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
    if G.get("coast"):  # the readings on a coast page are NOAA CO-OPS; USGS stays only where it is the real source (protected areas, topo map)
        for b in shown:
            if b["src_id"] == "usgs" and b["id"] not in ("public_land", "gauge_map"):
                b["src_id"] = "coops"
    if G.get("agy"):  # the same for an agency lake: the credit line under each reading block is the operator's
        for b in shown:
            if b["src_id"] == "usgs" and b["id"] not in ("public_land", "gauge_map"):
                b["src_id"] = G["agy"]["src"]
    if G["age_min"] > stale_after("usgs") * 60:  # break test 2026-10-28: a gauge not reporting for 3 h wears no live badge on any block
        for b in shown:
            if b["tag"] == "live" and b["id"] not in ("related_gauges", "nearby_gauges"):
                b["tag"] = "last"
    river, place, st = G["river"], G["place"], G.get("st_shown") or G["st"]
    rp = river_at(river, place)
    # Title and meta description carry NO reading (2026-10-26): Google shows them from its last crawl, days or weeks old, and the edge
    # cannot update them, so a number there becomes a stale number in search results under our name (snoflo's snippets showed weeks-old
    # readings). The live number lives in the page body, where the edge keeps it current for every visitor, Googlebot included.
    live = "" if G["age_min"] > stale_after("usgs") * 2 * 60 else "live "  # a reading over 6 h old is not live (audit run 1 row 2; run 5 row 4: the title is static, the Worker only refreshes the number)
    # Keyword Planner 2026-11-06 (US): '<water> water temperature' beats 'level today', 'gauge' and 'dam release' (22 of 122 at 100+, those three near 0).
    # The title names water temperature only while the tile shows it (fresh under 24 h, Celsius, not held as suspect): never a promise the page breaks.
    wt_ = bool(b3.conditions(G).get("wt"))
    # Keyword Planner 2026-11-13 (US): '<river> forecast' is the largest river phrasing on live waters (PLAN 25a); named only while the forecast block shows
    fc_ = tab == "dashboard" and not G.get("coast") and b_river_forecast(G) is not None
    tb_ = tab == "dashboard" and not G.get("coast") and any(TUBING_RULE.search(r["activity"]) for r in b3.limits_for(G["site"])) and b3.b_limits(G) is not None
    # PLAN 39 (page-two gap 2026-11-13): the gauge id sat past Google's ~60-character cut on every river title; it stays only where two gauges
    # share a river, place and state (their address carries the id), so two pages never share a title (check.py duplicate title)
    _id = (" (USGS %s)" % G["site"]) if G["site"] in (G["row"].get("dashboard_url") or "") else ""
    title = mk_title("%s, %s: %swater level and flow%s%s" % (rp, st, live, dash_tail(wt_, fc_, tb_), _id)) if tab == "dashboard" else mk_title(T["title"] % (rp, st))
    if tab == "dashboard" and G["site"] in TITLE_TODAY and live:  # PLAN 0k test 2026-11-09: Search Console's top query on this page is "rio grande water level albuquerque today" (49 of 364 impressions); read clicks after 28 days (gsc_read)
        title = title.replace(": live water level and flow", ": water level and flow today", 1)
    if G.get("coast"):  # keyword debate 2026-11-06: the title leads with the searched words ("san diego tides" 50,000), the station after; 'tide chart' 5,000 at all 13 coasts
        stn = river if [w for w in re.findall(r"[A-Za-z]{4,}", river) if w.lower() not in place.lower()] else ""  # "Sewells Point at Norfolk": the station's own name is in the H1, so the title carries it (release 2026-11-11); "San Diego Bay" adds no word
        # Keyword Planner 2026-11-13 (US): '<place> tide chart' 1K-10K at all 30 live coasts (PLAN 25c); named only while the chart draws NOAA's predicted tide
        _sc = None if G.get("tables") else b2.b_stage_chart(G)
        tc_ = "tide chart, " if _sc and "predicted tide" in _sc["body"] else ""
        title = mk_title("%s tides: %s%stide times and water level%s, %s" % (place, (stn + " ") if stn else "", tc_, ", water temperature" if wt_ else "", st))  # audit #27: was up to 141 characters with the place twice; searched words first. Must keep every H1 word (check.py rank_checks: the 60-char cut broke the gate 2026-11-11); a tide-table page's swap turns "tide times and water level" into "tide times and tide table"
    if tab == "dashboard":
        _np = (G["rec"].get("nwps") or {})
        _yrs = (G["rec"].get("record") or {}).get("first_year")
        # GSC week 1: "rio grande water level albuquerque today" is the top query; no number here (a cached snippet would go stale)
        # PLAN 39: a fixed NWS number, never stale (the no-reading rule above holds); only where the page proved the NWS and USGS read one scale
        # (a 30 ft flood stage beside a 72.5 ft USGS gage height on another zero point would mislead: Baxley, audit 2026-11-10 #5)
        _fs = flood_stage_txt(_np) if stage_pair(G) is not None and datum_gap(G) is None and scale_clash(G) is None else ""
        _nw = ((", NWS forecast and " if _np.get("forecast") else ", NWS ") + _fs) if _fs else (", NWS forecast and flood stages" if _np.get("forecast") else (", NWS flood stages" if _np.get("categories") else ""))
        _ys = (", vs records since %s" % _yrs) if _yrs else ""
        _head = "%s, %s: today's flow and water level, %sfrom USGS gauge %s" % (rp, st, live, G["site"])
        # SEO review: Google cuts descriptions near 155 characters; drop the records span first, then the NWS part (PLAN 39: the flood stage outranks the span)
        desc = next(d_ for d_ in (_head + _ys + _nw + ".", _head + _nw + ".", _head + ".") if len(d_) <= 155 or d_ == _head + ".")
        if G.get("stage_only"):
            desc = desc.replace("today's flow and water level", "today's water level")
        if G.get("coast"):  # review 2026-11-09: coast descriptions said "flow"
            desc = ("%s, %s: high and low tide times for the next 7 days, NOAA predictions for tide station %s." if G.get("tables") else "%s, %s: today's high and low tide times and the live water level from NOAA tide station %s.") % (rp, st, G["site"])
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
    last = place if hub_part else river_at(river, place)  # full review: "HOME / NE / AT OMAHA" had no river
    st_hub = any(p.get("_built") and not p.get("lake") and p.get("state") == G["st"] for p in pages.values())  # /rivers/<st>/ is built only for states with a river gauge; a lake in another state (Mead, NV) must not link a missing page. ponytail: lake state hubs come with the /lake/ silo
    from lib.directory import STATE_NAMES  # here, not at the top: directory imports render
    st_name = STATE_NAMES.get(G["st"], G["st"])  # audit #25: the state hub's own name ("Minnesota"), never "MN"
    crumb = '<div class="crumb"><a href="/">Home</a> / %s%s%s</div>' % (('<a href="/rivers/%s/">%s</a> / ' % (G["st"].lower(), esc(st_name))) if st_hub else "", hub_part, esc(last))
    sub = 'USGS gauge %s &middot; observed <span data-live="obs">%s</span> &middot; <span class="ab %s"><span data-live="age" data-t="%s">%s</span> old</span>%s' % (G["site"], esc(G["obs"]), age_chip(G["age_min"]), iso(G["lt"]), age_text(G["lt"], G["now"]), amber)  # audit 2026-11-10 #7: drainage area is in Key facts, not on the first screen
    if G.get("tables"):  # tide tables (owner decision 3): no reading, so no observed time; the age is the predictions' fetch
        sub = 'NOAA tide station %s &middot; tide predictions, times in %s &middot; fetched %s &middot; <span class="ab %s">%s old</span>' % (G["site"], G["now"].astimezone(G["zone"]).strftime("%Z"), esc(G["obs"]), age_chip(G["age_min"]), age_text(G["lt"], G["now"]))
    ld_items = [("Home", "/")] + ([(st_name, "/rivers/%s/" % G["st"].lower())] if st_hub else []) + ([] if row.get("_single") else [(river, row["hub_url"])]) + [(last, None)]
    fl7 = [x[0] for x in G["fl"]]
    ld = crumb_ld(ld_items) + '<script type="application/ld+json">%s</script>' % (lambda j: j.replace("</", "<\\/"))(json.dumps({
        "@context": "https://schema.org", "@type": "WebPage", "name": title, "url": url, "dateModified": iso(G["lt"]), "isPartOf": {"@type": "WebSite", "name": BRAND, "url": SITE_URL, "publisher": {"@type": "Organization", "name": BRAND, "url": SITE_URL}},
        "about": {"@type": "Place", "name": "%s, %s" % (rp, st), "geo": {"@type": "GeoCoordinates", "latitude": round(G["lat"], 4), "longitude": round(G["lon"], 4)}},
        "mainEntity": ({"@type": "Dataset", "name": "NOAA tide station %s, %s, %s: %s" % (G["site"], rp, st, "tide predictions" if G.get("tables") else "water level and tide predictions"),
                        "description": ("7 days of high and low tide predictions at NOAA tide station %s; no water level is measured there." % G["site"] if G.get("tables") else
                                        "Tide predictions at NOAA tide station %s and 3-day water level readings above MLLW from NOAA station %s, %s, %.1f km away, preliminary data." % (G["site"], level_of(G)["id"], level_of(G)["name"], level_of(G)["km"]) if level_of(G) else
                                        "3-day water level readings above MLLW and tide predictions at NOAA tide station %s, preliminary data." % G["site"]),  # black-hat review 2026-11-11: Clearwater named the predictions-only station as the readings' source
                        "creator": {"@type": "Organization", "name": "NOAA National Ocean Service, CO-OPS", "url": "https://tidesandcurrents.noaa.gov/"}} if G.get("coast") else  # review 2026-11-09: every coast page named USGS as the data's creator
                       {"@type": "Dataset", "name": "USGS gauge %s, %s, %s: flow and gage height" % (G["site"], rp, st), "description": "7-day flow and gage height readings and daily mean flow by year at USGS gauge %s, provisional data subject to revision." % G["site"],
                        "license": "https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits", "creator": {"@type": "Organization", "name": "U.S. Geological Survey", "url": "https://www.usgs.gov/"}}) | {"url": url,
                       "temporalCoverage": ("%s/%s" % (iso(min(fl7)), iso(G["lt"]))) if fl7 else iso(G["lt"]), "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": url + "data.json"}]}}))
    off_html = "".join(render_block(b) for b in shown if b["id"] == "gauge_not_reporting")  # the not-reporting banner sits right under the H1, above the tiles
    ids = {b["id"] for b in shown}
    jl = [(i, t) for i, t in JUMP if i in ids]
    jump_html = ('<nav class="jump" aria-label="On this page">%s</nav>' % " ".join('<a href="#%s">%s</a>' % (i, t) for i, t in jl)) if tab == "dashboard" and len(jl) >= 4 else ""
    SIDE = {"related_gauges", "nearby_gauges", "nws_forecast_point", "flood_stages", "about_gauge", "gauge_map", "sun", "official_links"}  # 2026-11-13: recreation sites, public land and station air readings stay in their sections (on a phone the side column falls to the very bottom)
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
        if isinstance(b, dict) and b["id"] == "gauge_not_reporting":
            continue
        if isinstance(b, str) and b.startswith("SEC:"):
            flush()
            grp[0] = "weather" if b[4:].startswith("Forecast") else "history" if b[4:].startswith("How today") else "now" if b[4:].startswith(("What the water", "Level, flow")) else grp[0]
            pending = gtag('<h2 class="secth">%s</h2>' % esc(b[4:]), grp[0])  # 'Every page its own' 1 (2026-11-11): the 30-word window key repeated what each card already names; it lives once on /methodology/#windows
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
    page = ('<!doctype html><html lang="en" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>%s</title><meta name="description" content="%s">'
            '<link rel="canonical" href="%s">%s%s</head><body>%s<main id="main">%s<h1>%s, %s: water level and flow</h1><p class="sub">%s</p><p><span class="tabs">%s</span></p>%s%s%s%s</main>%s%s</body></html>' % (
                esc(title), esc(desc), url, ADSENSE + HEAD_EXTRA + PWA_HEAD + og_tags(title, desc, url) + ld + robots_meta(row[tab + "_url"]), CSS_LINK, nav(), crumb, esc(rp), esc(st), sub, tabs_html, off_html, (hero(G, pages) + SAFETY + jump_html + gt_html) if T["hero"] else "", body, sources_block(shown, G) + (((AGE_JS if G.get("lake") or G.get("stage_only") else LIVE_JS.replace("@SITE@", G["site"]).replace("@TZ@", G["tzname"])) + GTABS_JS + TAP_JS.replace("@TZ@", G["tzname"]) + RANGE_JS + CITE_JS + (TIDE_JS.replace("@TZ@", G["tzname"]) if G.get("coast") else "")) if T["hero"] else AGE_JS) + (WX_JS.replace("@TZ@", G["tzname"]) if (G["rec"].get("nws") or {}).get("obs") else "") + (ALERTS_JS.replace("@LAT@", "%.4f" % G["lat"]).replace("@LON@", "%.4f" % G["lon"]).replace("@MZ@", re.sub(r"[^A-Z0-9]", "", (((G["rec"].get("nws") or {}).get("static") or {}).get("marine") or ""))).replace("@TZ@", G["tzname"]).replace("@CTY@", ((((G["rec"].get("meta") or {}).get("loc")) or {}).get("county_name") or "").replace('"', "")) if any(b["id"] == "alerts" for b in shown) else "") + (RADAR_JS if any(b["id"] == "radar" for b in shown) else ""), footer(), tabbar))
    if G.get("lake"):
        page = lake_words(page, G)
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
