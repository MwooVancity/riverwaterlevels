# Lakebrief vs riverwaterlevels.com, fresh-eyes comparison (2026-10-21, read-only)

Owner question: "Did we max out helpfulness and not for Google. Did we max out backlink strategy on page and internal links. Look at lakebrief fresh brain for ideas."

Evidence fetched this session (curl, Mozilla UA; Lakebrief dashboards are React, so the Lanier dashboard was also read rendered in a browser tab):
- Ours: https://riverwaterlevels.com/river/potomac-river-md/little-falls/ (225 KB raw), https://riverwaterlevels.com/, https://riverwaterlevels.com/rivers/md/
- Lakebrief: https://lakebrief.com/lake/lanier (famous), /lake/lanier/water, /lake/lanier/forecast, https://lakebrief.com/lake/oconomowoc-lake (obscure), /lake/oconomowoc-lake/water, /lakes/ga, /, /about, /embed, /embed/lake/lanier/panel, sitemap.xml (3,796 URLs: 1,243 lakes x 3 tabs + 51 state pages + 10 glossary + 7 trust pages), robots.txt.

## What Lakebrief shows (recorded, in order)

Dashboard tab `/lake/lanier` (rendered):
1. Nav: logo, "Spruce Run"/last lake chip, tabs Dashboard / Water / Forecast / Lakes. Breadcrumb only on state pages ("Home / Georgia").
2. Photo with credit ("Photo: PBT1981 / CC BY-SA 3.0 (Wikimedia Commons)"), "SET AS HOME".
3. Tiles: TODAY BEST WINDOW "5pm-7pm avg score 78"; WIND VELOCITY "4 KTS, Gusts 6 kt"; DIRECTION NW; AIR TEMP 74°F; RAIN "Dry, No rain expected".
4. 24-hour strip: SAILING SCORE per hour (0-100), WIND SPEED (kts), DIR, GUSTS, RAINFALL (mm), TEMPERATURE.
5. "Water Level Status, LAST 14 DAYS" chart: "Full pool · 1071.0 ft", "CURRENT: 1063.52 FT · 7.48 ft below full", "7-DAY ▼ -0.28 ft".
6. LIVE RADAR "OBSERVED · 3:00 PM".
7. "About Lake Lanier" paragraph (acreage, year, manager, gauge id, launches, clubs).
8. "Lake guide": LIVE CAMERA (club webcam link), RAMPS (4, each "MAP · INFO" to Google Maps and recreation.gov/state park), CHARTS (USACE PDF, gpsnauticalcharts), CONTACT & RULES (agency page; Oconomowoc shows a phone number with tel: link), BOATING & YACHT CLUBS (2, "VISIT"), MARINAS (10, "VISIT"); on the obscure lake: "We haven't found any marinas for Oconomowoc Lake yet. Know one? Recommend a marina." (mailto).
9. "Report an issue with this lake's data" (mailto with lake prefilled).
10. Footer: About this project, Disclaimer, FAQ, Privacy, Glossary, Add to your site (/embed), All lakes, Request a lake (mailto).
No source line per block on the dashboard; no observed time on the water tiles; the sailing score is a composed verdict ("stay-ashore rationale", About page).

Water tab `/lake/lanier/water` (prerendered, so it is the SEO page): H1 "Lake Lanier water level". First sentence: "Lake Lanier is currently at 1063.52 ft (NGVD29), 7.5 ft below full pool of 1071 ft, about 75% full, on a falling 7-day trend (-0.28 ft). Last reading 10/18/2026, 5:00:00 PM from USGS gauge 02334400." Tiles: Current Elevation, below full pool, Storage Capacity 74.7%, Estimated Storage 784,407 AC-FT of 1,049,400, 7-Day Trend. "Past 30 Days" chart; "Multi-year history isn't available from this lake's data source". Table: 12 daily readings with Change column. "Telemetry Snapshot": latest, 24h delta, "Source: USGS site 02334400 (Lake Lanier), parameter 00062 (elevation, NGVD29). Last sample: 10/18/2026, 5:00:00 PM." Then surface area, year built, sensor, coordinates. The reading shown was 3 days old (Oct 18 on Oct 21) and the page did not say so.
Obscure water tab: NASA SWOT satellite elevation, "Readings arrive every 1-2 weeks", and a "water temperature by month" table from a USGS 40-year model with "Cold-water caution applies in roughly half the year, when the typical temperature is below 60°F" (derived line with its basis and threshold stated).
Forecast tab: prerendered body is "Loading forecast…" only.

Title / H1 / first sentence: titles are query-shaped ("Lake Lanier water level today — current elevation, trend & history | Lakebrief"; "Oconomowoc Lake water level & water temperature today"). No meta description on any page fetched. Canonical absent in the raw HTML (set by JS). JSON-LD on the water tab: WebSite, WebPage, BreadcrumbList, BodyOfWater+Place+GeoCoordinates, Organization, Dataset with DataDownload, FAQPage (5 Question/Answer). Dashboard: the same minus FAQ/DataDownload.

Freshness: "Last reading 10/18/2026, 5:00:00 PM" (raw timestamp, no age, no staleness flag); radar "OBSERVED · 3:00 PM".
Publisher and contact: footer "© 2026 Lakebrief. All rights reserved."; contact is mailto:info@lakebrief.com in three places per page (report issue, request a lake, recommend a marina). About page names the sources and the score formula; no person named.
Link invitations: /embed ("Free for clubs & marinas. Put live lake conditions on your club's website"; iframe `src="/embed/lake/<slug>/panel" 330x440` or `/dashboard`, and a script tag `<div data-lakebrief="<slug>" data-preset="dashboard"></div><script src="https://lakebrief.com/embed.js" async>`; per-platform paste instructions for WordPress, Wix, Squarespace, Weebly, Google Sites). The embedded panel links back to lakebrief.com. No cite-this, no CSV/JSON download link in the body (Dataset/DataDownload is schema only), no badge, no public API doc, no per-chart permalinks.
robots.txt: allows OAI-SearchBot, ChatGPT-User, PerplexityBot, Claude-SearchBot, Claude-User; blocks GPTBot, CCBot, ClaudeBot, Google-Extended, Amazonbot (answer engines yes, training crawlers no).

Internal links per page (anchor count in raw HTML): Lanier dashboard 43 (17 internal, 24 external, 0 anchors); water tab 18 (16 internal); forecast 17; Oconomowoc 27 (17 internal, 6 external); state page /lakes/ga 42 (41 internal); home 1,386 (every lake, grouped by region and state). Internal shapes: the three tabs of the same lake (x2-3 each), "Lakes" browse, footer trust pages, embed. No nearby lakes, no same-state list, no same-river-system, no breadcrumb on lake pages. The state page is the only lateral link shape.

## What we show (Little Falls, in order)
Breadcrumb "Home / MD / Little Falls", H1, line "USGS gauge 01646500 · drainage 11,560 sq mi · observed Oct 21, 3:50 PM EDT · 63 min old", three chips (Falling -2.7% in 6 h, Above normal for Oct 21, No active NWS alerts), tiles (Latest flow, Gage height with "Next NWS impact at 3.5 ft (0.2 ft higher)", Is this normal (78% of 96 years), Change 6 h, Forecast high, Water temperature, Upstream gauge now with lag, Rain 24 h, Air temperature, Sunset, Calm daylight hours), disclaimer line, jump links, then 40-odd blocks each with "Where this comes from" source, time and credit: water quality sensors, tides, hourly forecast, weather, air quality, rain, radar, flow chart (7 d/30 d/12 m/earlier years), gage height and flood stages, NWS impacts (all 14 quoted), alerts, rate of change, river forecast table, station rain, forecast rain, daily values, field measurements, rating curve, drought, EPA assessments, StreamCat, public land, recreation sites (RIDB, federal only), upstream/downstream strip, NWS point, map, official pages, about gauge, sources list. Links: 93 total, 16 internal (home x3, /rivers/md/, upstream gauge x2, trust pages), 47 anchors (`#chart_id` permalinks via the "#" on every block heading, lib/core.py:188), 30 external to the exact records (USGS monitoring location, NWS gauge, ATTAINS reports, recreation.gov campgrounds, terms pages). JSON-LD: BreadcrumbList only. Home: 103 links (25 gauges x3, 15 state pages). /rivers/md/: 15 links (one gauge).

## 1. Helpfulness for the person at the river

What Lakebrief does that we do not, ranked by reader value, each tested against our rule (no verdict, no composed prose, every number with unit, time and source):

1. Where to get on the water: ramps with map link and agency info link, marinas, clubs, rules page, phone. We show RIDB federal campgrounds only ("state and private ramps are not in it") and PAD-US polygons. Fits: yes as a sourced table (name, type, managed by, distance, map link, source record). Data exists publicly: USGS/state DNR boat-ramp layers, NPS/USACE ramp feeds, the National Boating Access inventory where a state publishes one, RIDB facilities (not just campgrounds). Show as "Access points within 10 miles" with the agency source per row; no editorial descriptions.
2. A live camera. Lakebrief links a club webcam; we have b_camera (USGS NIMS) but Little Falls shows none. Fits: yes, image with time and source. Add NPS/DOT/USGS public cameras where a public URL exists.
3. "Full pool" style reference line on the chart: "7.48 ft below full". Our river equivalent is the NWS impact ladder and we already print "Next NWS impact at 3.5 ft (0.2 ft higher)" in the hero, so this is covered, arguably better (quoted thresholds with a source).
4. Water temperature by month with a stated cold-water threshold ("below 60°F ... roughly half the year", USGS 185k-lake model). We have b_wtemp / water_temp_months (block exists, source USGS sensor). Fits as a sourced threshold table: the NCWSA cold-water guidance (under 60°F / 50°F) as quoted thresholds beside the monthly sensor record; the threshold is the source's, not ours.
5. Hourly strip with wind in knots and gusts, which paddlers and rowers read. We have the same NWS grid in mph with gusts; the difference is units, not data. Add a knots column? Only if a source quotes thresholds in knots; otherwise no.
6. Contact and feedback per page ("Report an issue with this lake's data", "Request a lake", "Recommend a marina") with the page prefilled. We have no per-page contact. Fits: yes, it is not prose; data/publisher.json already exists (lib/directory.py:195).
7. Photo of the place with credit. Fits: yes if a Wikimedia Commons CC image with credit line; it helps the reader confirm "this is the spot". Low value against the USGS topo map we already show.

What we do that Lakebrief does not (all reader-facing): observed time and age on every number, source and credit under every block, staleness rules, flood stage ladder with all NWS impact statements quoted, "is this normal" against 96 years, rate of rise/fall table, upstream gauge with measured lag, NWS official forecast table, water-quality sensors, tides, air quality, drought, EPA assessments, flood frequency, historic crests, field measurements, rating curve, per-block permalinks, breadcrumb, state pages, status page, methodology, and no verdict. Lakebrief's sailing score is the kind of composed verdict our CLAUDE.md "Never shown" bans; nothing to copy there.

Verdict on "maxed out": on data, yes beyond Lakebrief. The one real reader gap is access points (ramps, put-ins, marinas) and a camera; the second is a way to tell us something is wrong.

## 2. Internal links

Counts: ours 16 internal per gauge page vs Lakebrief 16-17 per lake page, nearly equal; but 10 of theirs are the same lake's three tabs and nav, and the rest footer; they have zero lateral links (no nearby, no same-state, no same-system). Ours: 1 lateral (upstream gauge) plus the state page. Our budgets: check.py:13 `BUDGET = {"gauge": 110, "hub": 80, "state": 480, "home": 200, "trust": 40}`; Little Falls uses 93 of 110 (47 are anchors). b_nearby (lib/page.py:68) lists up to 5 gauges within 60 miles but Little Falls has none on the site today, so the block is hidden (block returns None). Lakebrief's state page lists every lake in the state with acreage and manager (41 links); ours lists gauges with drainage, flow and observed time (15 links, one gauge in MD). Lakebrief home lists all 1,243 lakes (1,386 links); ours lists 25 gauges x3.

What we lack and the cheapest change at 25 gauges, holding at 20,000:
- Nearby block already exists; it fills itself as gauges are added. Nothing to build.
- Same-river hub (`/river/<slug>/`) exists in lib/directory.py:158 and check.py enforces hub reciprocity; Potomac has one gauge so no hub. Fills itself.
- Same-state strip on the gauge page: no. Cheapest: a one-line "Other rivers in MD" list capped at 8 in b_nearby's position, from pages dict, sorted by distance (reuse the haversine in b_nearby). Budget: +8 links, fine at 20,000 because the cap is per page.
- NWS upstream/downstream forecast points are printed as plain text ("Potomac River at Edwards Ferry; ...") on the NWS point block; when those gauges join the site they should become links. Cheap: look each up in pages by NWS lid (data/nws-crosswalk.json) and link when built.
- Breadcrumb middle link is "MD" to /rivers/md/; a river hub crumb appears only when a hub exists. Fine.
Anchor links (47) count against the 110 budget (check.py:150 counts every `<a `); at 20,000 gauges that does not change. No change needed to budgets.

## 3. On-page link earning

| Feature | Lakebrief | Us | Cheap? |
|---|---|---|---|
| Embed widget (iframe + script, per-platform instructions, links back) | yes, /embed, embed.js, `/embed/lake/<slug>/panel` | no | Medium. A static `/embed/<slug>/` HTML (hero tiles only, our CSS, link back) is one template in lib/page.py plus an `/embed/` instructions page; iframe only, no embed.js. Fits rules: it is the hero. 2-3 h. |
| Per-chart permalink | no | yes, `#<block_id>` on every heading (lib/core.py:188) | done |
| Cite this (plain text with URL, source, observed time) | no | no | Cheap: one line under the hero built from fields already in G (title, USGS id, observed time, URL). 30 min. |
| Data download of the page's series (CSV/JSON) | schema DataDownload only, no link | `/gauges.json` (site list), `/status.json`; no per-gauge series file | Cheap: write `cache/<site>.json` subset (7-day readings, daily means) to `dist/river/<slug>/<place>/data.json` and link it in the official-links block; 1 h; adds 20,000 files at scale, each a few KB. |
| Badge for marinas/outfitters | no | no | Skip (YAGNI until someone asks). |
| API | no | no (USGS is the API; we link to it) | Skip. |
| "Last verified against USGS" line | no (raw timestamp, 3 days stale unflagged) | yes: "observed Oct 21, 3:50 PM EDT · 63 min old", status page, in-browser recheck | done |
| Schema: Dataset, BodyOfWater, Place, FAQPage, Organization | yes | BreadcrumbList only | Cheap: Dataset + Place/GeoCoordinates from existing fields in the shell; 45 min. FAQPage: no (our FAQ is a trust page, not per gauge). |
| Contact per page (report issue, request a gauge) | yes, mailto prefilled | footer About only | Cheap: one mailto in footer() or b_about using data/publisher.json; 20 min. |
| robots: allow answer-engine bots | explicit | not checked this session (not fetched) | Check `robots()` in lib/directory.py:301; 10 min. |
| Photo with CC credit | yes | no | Skip; map covers it. |

## 4. Ranked list, worst gap first

1. Access points table (ramps, put-ins, marinas, with map and agency links). Reader value: highest, it is the question after "is it dangerous". Fits rules: yes (sourced table, no descriptions). Effort: hours (source discovery per state, one fetch script, one block); start with RIDB facilities of all types and USACE/NPS ramp layers, state DNR layers later. File: lib/page.py (new b_access beside b3.b_recreation), collect.py fetch, data/sources.json row.
2. Embed widget (static iframe of the hero + `/embed/` how-to page). Reader value: medium for outfitters, clubs, county pages; the only on-page link-earning device Lakebrief has that we lack, and it links back from every host site. Fits: yes. Effort: 2-3 h. Files: lib/page.py (embed template), lib/directory.py (trust page), check.py (kind_of for /embed/, budget "trust").
3. Per-gauge data download (data.json or CSV of 7-day readings and daily means, linked in "Official pages for this gauge"). Reader value: medium (researchers, teachers, local news). Fits: yes. Effort: 1 h. Files: build.py write, lib/page.py b_official_links link, check.py static set.
4. "Cite this page" line (title, USGS id, observed time, URL, "data: USGS/NWS"). Reader value: low-medium; it is how a local paper or forum post links. Fits: yes. Effort: 30 min. File: lib/hero.py (under the hero) or lib/page.py b_about.
5. Dataset + Place JSON-LD from existing fields. Reader value: none directly; it is what Lakebrief ships and what answer engines read. Fits: yes. Effort: 45 min. File: lib/directory.py shell() / lib/page.py og_tags.
6. Per-page "Report a problem with this page" mailto from data/publisher.json, prefilled with the gauge. Reader value: medium (it is how wrong data gets found). Fits: yes. Effort: 20 min. File: lib/page.py footer() or b2.b_about.
7. Same-state "other rivers" strip (cap 8, nearest first) so a page is never a dead end when b_nearby is empty, and link the NWS upstream/downstream forecast points when those gauges are on the site. Reader value: low-medium today (25 gauges), rises with coverage. Fits: yes. Effort: 1 h. Files: lib/page.py b_nearby, b3.b_nws_point, data/nws-crosswalk.json.
8. Cold-water threshold rows beside the monthly water temperature block (quoted NCWSA/USCG thresholds with their source). Reader value: medium for swimmers and paddlers in shoulder season. Fits: yes if quoted, no if we write "caution". Effort: 1 h. File: lib/page.py water_temp_months, data/sources.json.
9. Live camera where a public NPS/DOT/USGS camera exists near the gauge. Reader value: high where available, rare. Fits: yes. Effort: hours (source discovery). File: lib/blocks3 b_camera.
10. Check robots.txt allows the answer-engine user agents Lakebrief allows. Effort: 10 min. File: lib/directory.py:301.

Not recommended: sailing-score style verdict, "best window" composite, photo, badge, API, knots column.

Not looked at myself: Lakebrief's Forecast tab rendered (prerender is "Loading forecast…"), its embed.js source, our robots.txt, the rendered contact sheet of Little Falls (text only this session).
