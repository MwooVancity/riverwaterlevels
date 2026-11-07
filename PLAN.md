# PLAN: riverwaterlevels.com

## Goal
The most useful page for a person deciding about this river today, anywhere (reader: CLAUDE.md). Objective: AdSense earnings from people helped.
Scarce resource: Claude time. From 2026-11-20 the owner moves from Max to Pro (owner 2026-11-03): sessions continue but far fewer, so growth slows, never stops; everything must run alone between sessions, and the costly builds (world release, limits) belong before Nov 20.
Bottleneck: AdSense approval, then readers. Earns $0 until approved; calcscrape and asmrregistry were rejected as low value content, so approval outranks page count.

## Numbers
- Live 2026-11-01 21:07 UTC (`status.json`): 119 gauges, 181 pages.
- Search Console 10-20 to 10-29: 359 impressions, 1 click, position 15.7, 60% Albuquerque.
- AdSense 2026-11-01: "Getting ready". Ads.txt shows Not found there; the live file is correct. Consent message shown 0 times.
- US: `data/waves.csv` 9,099 rows, 25 a day by itself, about 8,900 pages by late 2027. Held out: 283 names, 490 short-record, 546 tiny-basin, 206 canals and drains.
- Target: about 13,900 gauges (US 7,564; Canada 2,627; England 2,421; Germany 786; Ireland 467), about May 2028 at 25 a day. Judgment, not measured.
- Queue: `data/world-queue.csv` 20,000 rows by `tools/world_queue.py`: 7,445 US (ready), 12,555 foreign (not ready). `docs/research/priority/picks.csv` is the US part; `tools/release.py` reads it first, so reordering needs no code.
- Bytes 2026-10-31: gauge page 50 KB; Google tag 181 KB; ad script 206 KB, 89% of a phone's download. Ad script is the biggest cut if approval does not need it (owner).

## World guarantee (2026-11-02)
Contract built: `COVER` in `lib/world.py`, 34 real world pages 0 faults 0 block crashes on the laptop run. Weather, alerts, air quality for Canada (ECCC) and Germany (DWD, UBA), official river forecast (`WV`, Kaub), rain, not-reporting banner. Near-duplicate now counts numbers.
Steps: (a) collect runs in the cloud, read `wx` in the cache; (b) set `world.GATE = True`; (c) clear `next` items in `COVER`, Canada history first, then `FROZEN` opens that country.
Open global risks, each tied to the country that hits it: tidal gauges (England), reservoir normal (Lake Constance is natural, others not), one river in two feeds, English names (Rhine/Rhein), no English alert text outside Germany and Canada, licence re-read, feed moves after 2026-11-20, disputed places (owner decides), countries with no feed. All-pairs near-duplicate breaks near 3,000 world gauges: compare within a country. Weather calls: at most 844 Canadian cities and one bulk alert file an hour; German forecasts one call per gauge page, split before 500.

## Superior helpfulness (2026-11-02)
`COVER` only proves equal to the US page. Superior needs: (1) own archive of daily low and high, `collect.py` `archive`, published at `/archive/`, read back if the cache is lost; agencies keep 30 days, so every day lost is gone; page block once a year exists: same date last year, days below a mark. (2) Census of every agency's datasets: used, or no reader because why. (3) Reader table: about 12 readers, their real questions, a block or a gap per country, a machine check. (4) Whole river across borders in one unit: Rhine, Danube. (5) Emergency number per country. (6) Bathing water, EU and England. (7) Coming down the river: upstream rise with lag measured from our archive, labelled ours. (8) Bridge clearance, locks, notices to skippers. (9) Canada ice, smoke, algae, 100+ years of history. (10) Past flood dates against today. Sources for 5 to 10 unproven. Only readers prove what is missing: 1 click so far.
Done 2026-11-02: own archive live, flow, Canada history table, emergency numbers. `COVER` next items left: Canada climate normals, drought, boat access, nearby gauges; Germany water temperature history, rain totals, climate normals, drought, locks and notices. `FROZEN` holds new gauges until those are done.
Review 2026-11-02 left: chart axis in feet on world pages, flow and water temperature tiles, hub time column clipped, Basel Unknown, hourly table reads long, cruise reader needs shipping state (`stateNswHsw`), English agency pages for WSV.
Truth guards 2026-11-02: `suspect`, alert canary, `truth_world` compares alerts and alarms at 01 and 13 UTC. Edge batch 2026-11-02: station moves checked 300 a run (5 km), Canada rank on the latest 20 years so an old datum cannot skew it, UBA times are CET all year (the feed says so), USGS links use the current form. Terms and emergency numbers are re-read by hand only: yearly owner item, no code can do it. Still open: daily count split US and world (stage 4).
2026-11-02: a stray colon in `watchdog.yml` stopped the watchdog about 2.5 hours; the dry run now fails on any workflow file that does not parse. Percentiles need a published 10th and 90th, and "below 5th" needs a published 5th; 24 stats files cleaned of NaN.
Alarm 2026-11-02: GitHub ran only 9 of 22 alarm hours in 11 days, so the alarm now fires on the first run in 01-06 or 13-18 UTC, once per half day. Watchdog adds an empty commit after 45 quiet days. If GitHub itself stops, nothing emails: outside uptime monitor is owner-only.
Fresh review 2026-11-02, 13 findings fixed: world age ticks, Canadian agency flags, side readings keep their time and die at 24 h, frozen DWD file reads Unknown, emergency line by country, Kenora and Labrador zones, carry at 5%, watchdog steps time-limited, live world pages never held, past archive years restored, three more alarms. Owner: Workers Paid before about 1,500 gauges, about 2026-12-26; alarm at 1,200.
Edge batch 2026-11-02, also: latest GitHub action versions, `WORKERS_PAID` repo variable lifts the file stop to 100,000 and the CPU stop, `tools/worker_load.py` counts Worker runs Cloudflare stopped (release waits at 10 a day, replaces the guessed 1,500 gauges), measured at 142 gauges p50 2 ms, p99 8.9 ms, max 15 ms, 0 stopped; history pauses under 300 USGS calls left; watchdog alarms on a rejected or expiring build key; `tools/edge_tests.py` fixtures in `check.py --selftest`: ice flag, frozen file, side readings, zones, outage over a live page, lost archive in a later year. Fixture proof only until a real event.
Stage 1 2026-11-02: COVER clear, `FROZEN` no longer limits either country; Germany drought is the one new `none`. Master GitHub audit, 12 findings fixed or staged: carried pages keep their real age, Worker and site outages and dead feeds alarm, 80,000 requests alarm, failed cache restore never saved, shard crashes counted, truth samples no longer capped at 24 batches, a release that added nothing is not a release, skip reason in the alarm, truth_world false alarms cut, `ubuntu-latest`. Accepted: a day that sends back 24 of 25 still counts; a permanent truth fault repeats twice a day.
Animas miss 2026-11-02: USGS corrected 10,500 to 11,000 cfs at 21:41 UTC; `fast()` kept the first value and its 3 h window could not see older corrections, so a page stayed wrong up to a day. Now the hourly fetch reads by last-modified over 6 h, the newest USGS word wins, a correction rebuilds its page, the edge swaps same-time corrections, and flow ending before gage height shows a block at the top. Worker starts the watchdog hourly because GitHub's schedule left an 11 h 53 min gap; accepted gap now 2 h.
New country checklist: reading against the agency's page, time zone against the agency, alert coverage on a real active alert, unit and zero point named, terms read, water type labelled (river, lake, reservoir, tidal).

HARD rule (owner 2026-11-03): highest search volume first, any country, one ranking; make money fastest. England moves up: River Trent 5,000 a month and 17 English rivers at 500 lead the world queue. Canada added by hand 2026-11-03: James River near Sundre, Mississippi River at Appleton, Chilliwack River at Vedder Crossing; St. Lawrence and St. Croix (NS) have no matching real-time station, skipped, never guessed.

Stage 4 start 2026-11-03: `tools/world_match.py` matches Canadian queue rows to ECCC stations (strict: river name pattern, province, one province or skip, keyword not shared with a US gauge, largest drainage, one gauge per river); first run 12 ready, 50 skipped with reasons. `tools/release.py` sorts US and world by search tier in one list, world gauges become data rows, capped at 400 world gauges (shard 0 time). With today's tiers, 581 US gauges at 500 or more come before the first Canadian 50; England (Trent 5,000) is the volume lever.

England 2026-11-03 (branch `england`, not merged): feed `ea` (Environment Agency flood-monitoring API, OGL v3.0, attribution quoted), `fetch_ea` about 1 call a gauge an hour, label is the agency's normal range (as GOV.UK Check for flooding), dated records, tidal gauges held (tidal measure or 12.4 h tide test on readings), flood warnings and alerts point-tested against each area in force plus 150 m (gauges sit in the channel; Colwick's own area lies 78 m off). No weather (Met Office needs a key, owner). Proven on live data: Colwick, Kingston, Ross-on-Wye pages equal API and GOV.UK; Gainsborough and Keadby held as tidal. Not proven: a real warning (none in force), so `world.room("ea")` is 0 and the release and matcher add no English gauge. The switch-on needs no person: `collect.py` `ea_probe` records the first real level 1 to 3 warning whose area holds an active non-tidal English level station (same point test plus 150 m) in `cache/_ea-proof.json`, published as `/_proofs.json` and read back if the cache is lost; `release.py` commits it into the england row of `data/world-pages.json` with the first gauge, so a lost cache never relocks live pages; `world.listing` keeps an unlisted country out of the proof gate. COVER England: 9 have, 23 none, 27 next, FROZEN 20. Scale: per-gauge calls break shard 0 near 900 English gauges (3.9 s a call); switch to one `readings?latest` call a run (1.7 MB, 19 s) before 400.

State 2026-11-03 06 UTC, read live: main 9e0d47e, watchdog clean except world-wx noise (failure-only notes, no email), truth ok on 142. Practice release passed: 25 picked by searches per gauge (all US today), 3 sent back by page checks, 22 pass. England code live and locked: it unlocks by itself when a real EA warning (level 1-3) covers an EA level station (`cache/_ea-proof.json`, `/_proofs.json`), then up to 20 English gauges, Trent at Colwick first. Not proven until that warning comes. Fixed tonight from live findings: USGS corrections now reach pages, flow-behind banner, DWD empty newest row, flood wording past the 90th, coverage alarm only for blocks on nearly every page.

Country cap cut 2026-11-03 (owner): `FROZEN` deleted; a `COVER` next item is a to-do the gaps line names (`world.TODO`), never a cap. In its place a per-page floor, `world.thin`: a new world page needs 8 reader blocks with data (Unknown and could-not-load do not count), a reading with time and unit, the alerts block, history or a normal label, and weather or rain with a value; under it the page is held by `choose`, listed in status.json `world.thin`, named by the watchdog (never an alarm), never shipped or noindexed. A country whose every listed gauge is thin adds no more (`room`, from live status.json; unread status adds no world gauge).
Floor evidence, every live page read 2026-11-03 15 UTC: blocks with data US 164 pages median 35 (min 24), Canada 8 pages median 12 (min 11), Germany 29 pages median 12 (min 9); main-text words US median 6,972, Canada min 1,413, Germany min 1,377. The US median is out of reach abroad (about 21 of 35 are US-only products), so the floor is one under the thinnest live world page. Words are measured, not gated (mostly template). Live Kelheim lacks history and a normal label; live pages are never pulled.
England 2026-11-03: alert proof no longer needed to ship (`UNKNOWN_UNTIL_PROVEN`): until `ea_probe` records a live warning, the alert block, tile and flood line say Unknown with the GOV.UK link and never "no warnings"; with a proof the point test answers by itself (fixture `edge_tests.england_page`). Rain wired: 24 h total of the nearest EA rain gauge within 15 km with all 96 readings, station, distance and end time; one bulk call a run (newest 10,000 readings, 3.5 MB, 3 to 45 s) into `cache/_ea-rain.json` (about 3 MB, fixed), 20 hole-filling station calls a run. Proven: Colwick 0.8 mm at gauge 3771 0.9 km off = the API's own 96 readings. Result on live data, 19 English candidates: 15 rain totals, 4 Unknown with reason; 3 to 5 blocks each, so 0 of 19 pass the floor. England cannot pass without Met Office weather (owner key): held, one daily slot spent once (Trent at Colwick), then `room` closes until a page passes. Hydrology API (history) not wired: it adds 1 block, still under 8. Left for it: read https://environment.data.gov.uk/hydrology/doc/reference terms and live daily means for 4009, map to `wx.day_stats` as Canada does, `COVER` b_multiyear have.
Canada matching 2026-11-03: a keyword shared with a US gauge is allowed when the queue row is Canadian by its own words (bracket names a province, territory or Canada, or Canada is its only country) and the station sits in that province; stations outside the provinces never match. 19 Canadian rows ready (12 before): Cedar (ON), Current (ON), Eagle (YT), Grand at Brantford (ON), Meadow (SK), Snake (YT), Vermilion (AB) added; all checked against the ECCC station record (name, province, coordinates, active, real-time).
Watch: "river thames level" matches Hannington Bridge (a small upstream gauge) and "river severn level" matches Sharpness (estuary; passed the tide test). Both held thin today; review before England can pass the floor.

State 2026-11-03 evening (owner): every page, any country, ships with everything its data allows; no block-count floor; held only without a reading (time, unit) or the alerts block, or when `missing` finds data not on the page. Release order is money: searches x `RATE`. Any failing page (US or world) keeps its live copy (`check.py` `CARRYABLE`). England unlocked with alerts Unknown + GOV.UK link until a real warning; rain wired; Thames = Kingston 3400TH, Severn = Shrewsbury 2077. Every new-page hold counts in `room()`.
Done 2026-11-04 00 UTC (main 10d579c, refresh success, _built.json 201 at 00:48Z): Met Office Global Spot wired for England weather (owner subscribed, secret `METOFFICE_SITE_KEY`): hourly and daily, 2 calls a gauge, ledger `cache/_ea-met.json` caps 300 a day (plan 360); cadence max(3 h, 0.16 h x gauges): hourly amber past 75 English gauges, daily cards hide past 300, hourly past 450. No sky words (code table not read from the Met Office); thunderstorm "none" line off without sky words. Not yet proven live: no England gauge page yet, so no call made. Next: after the first England release, read the refresh log line `met <gauge> ... hourly fields [...] daily fields [...]` and the page; a field name missing there is a fix in `wx.met_forecast`. Done 2026-11-03 evening (main 4f497a4, refresh success, _built.json 201 entries at 18:45Z, Animas Farmington page live with cfs readings): a failed EA history fetch retries in 7 days, not every run. Done 2026-11-03 late (main f6113bf): (1) hourly collect adds the USGS latest-continuous reading when the series lacks that time (1 call per 300 gauges, 47/h at 14,000); Animas Durango live 6,390 cfs = USGS latest; (2) world pages enter `_built.json` by URL and a carried one keeps its old time, so the existing 6 h "not rebuilt" alarm covers them (37 world entries live), no new watchdog code; (3a) England history from the EA Hydrology API (daily lowest/highest level, no daily mean so no median), datum re-proven per gauge against the live stage; Colwick, Kingston, Shrewsbury proven; read it on the first England page. Next, in order: (3b) remaining open no-key England sources: Defra UK-AIR air quality, NRFA statistics (terms first), EA water temperature (2 of 7,439 measures, low value); (4) owner keys: Met Office DataHub (6 English blocks), SEPA, NRW, OPW.

## Fresh review of the queue release, 2026-11-04 (one agent, read-only, code checked, not PLAN)
Fixed same night: a country with no live page opens 2 a day (`world.room`), not every ready row. Still open, in build order:
1. `check.py near_dupes` compares every page with every other on every run (about 1 ms a pair): 200 pages 20 s, 1,000 about 8 min, 2,000 about 35 min (45-min brake stops releases), 3,000 over 80 min (deploys stop, every page stale). Fix: compare new or rebuilt pages only, against same river or state.
2. World supply ends near 100 gauges: `tools/world_match.py` skips rows with no keyword (12,271 of 12,555 world rows); Germany has no matcher (699 rows, hand edits). Fix: ready rows from each agency's station list (one per river, active, non-tidal). Also: held world gauges stay in `gauge_pages` forever (drop after 7 days with the reason); the stall alarm counts US rows only (count world rows waiting).
3. One-liners: `fetch_world` shares one failure counter across feeds (3 PEGELONLINE failures skip Canada and England, blamed on the wrong agency): count per feed. `release.py` lacks open_wave's 10-year rule: 540 of 7,445 US picks would ship and stay noindexed (11194152, 05341498 already). World URLs bypass `open_wave` (indexable on first build).
Later: Canadian rows sharing a US keyword (Cedar, Grand, Snake, Vermilion) take US searches; Worker CPU 8.9 ms p99 of 10 at 142 gauges (Workers Paid, owner); GitHub cache about 1.5 GB at 9,100 gauges vs 10 GB (one fixed key; a lost cache resets the Met Office ledger); shard 0 fetches world gauges one at a time (about 35 min at 400); `world_match.py | head -3 || true` hides matcher errors; `tools/quarter/` keyword refresh is manual.

## World to US level: full matrix, 2026-11-04 (machine-made)
Made by a script, not by people spotting gaps. For every block on live US pages: its b_* function, COVER per feed, and how many of 37 world pages show it with data. The owner's rule is that nothing gets missed, so the list comes from the code and the live site.

A. COVER says "have" but the page does not show it. These are broken promises: fix the cause, then enforce.
1. about_gauge: all three countries, live 0/37.
2. nearby_gauges: all three, live 0/37.
3. county_station_rain (b_acis): Canada and Germany, live 0/37. They show climate_normals 37/37 instead; declare that as the substitute or fix it.
4. annual_peaks (b_peaks): Canada, live 0.
5. flood_stage_years: Canada and England, live 0.
6. flow_duration: Canada, live 0.
7. record_comparison: Canada, live 0.
8. quality_sensors: Germany, live 0 (also_measured 33/37 may carry it: declare it).
9. rain_totals: Germany and England, live 0.
10. water_temp_months: Germany, live 0 (water_temp_recent 8/37).
11. related_gauges: Germany, live 0 (along_river 17/37).
12. flow_chart: all three, live 23/37. Name which gauges have flow but no chart.

B. "none:" answers that are dodges: the page's own data or an open official source can fill them.
1. rate_of_change: computable from the series.
2. gauge_map: coordinates are known; a map needs an open source with terms read.
3. hourly_heatmap: from the hourly forecast we already hold.
4. daily_readings: Canada's daily means, and our own daily values from the 30-day series, labelled ours.
5. historic_crests: Canada's annual statistics publish yearly maxima.
6. sustained_flow and flow_duration: Canada's daily-mean history.
7. radar: DWD radar open data; ECCC GeoMet radar (terms to read).
8. cpc_outlook: ECCC and DWD seasonal outlooks (terms to read).
9. public_land and recreation_sites: Parks Canada and CPCAD open data; Germany's protected areas (terms to read).
10. water_samples and water_quality_assessment: ECCC long-term freshwater quality; England's Water Quality Archive and Catchment Data Explorer (already listed as next).

C. England "next:" items: real to-dos.
- NRFA statistics (peaks, frequency, duration, sustained flow).
- Defra air quality.
- Met Office observations, rain totals and radar.
- Impact levels.
- Flood Forecasting Centre outlook.
- Drought status.
- Water temperature at 2 gauges.
- Water quality archive.
- Land cover.
- The English counterparts never checked for cpc, wpc, nwm, nws_point, dam releases, recreation and streamcat.

D. Fair "none": no counterpart exists or it is wrong for the reader.
- US federal only: wpc, nwm, nws_point, attains, streamcat.
- snowpack, tides, camera.
- rating curves and field measurements: no agency record.
- low_water: covered by official marks.
Each one stays only with a reason a reader would accept.

E. The forcing guard. These are its own edge cases, adversarial:
1. Every US block needs a per-feed status: have (must render, or say Unknown with the gauge's reason), substitute (a declared world id, never a regex guess), none (a reviewed reason) or next. A new US block already fails at import without a COVER row.
2. check.py on every world page in dist, carried pages included. A "have" block that is absent fails the page as carryable: the live copy stays, the watchdog names it, never noindexed.
3. A "have" block showing Unknown on over half of a country's pages is a broken promise: the watchdog alarms. Unknown on every page is not "have".
4. A stale or outage hide never fails the deploy (heal rule). Only a block missing with fresh data fails.
5. A daily live audit (the script that made this matrix) compares the live site against COVER, because built pages can drift from live.
6. A new country cannot ship until its COVER column passes the live audit on its first 2 pages (room opens 2 a day).
7. A substitute has to answer the same reader question; one reviewer reads each substitute once.
8. Selftest fixtures: a page missing about_gauge fails; a page with Unknown plus a reason passes; a declared substitute passes; an undeclared one fails.

F. Pipeline gaps from the two reviews (see the sections below): URL collision, Canada time zones, phone refresh mixing numbers, truth_world before deploy, per-feed failure counter, world supply from station lists, held gauges returned, world URLs through open_wave, world hubs (fixed), first-day cap (fixed).

## 2026-11-04 afternoon batch
Done (on check, dry run "refresh OK" 6a68ebb): forcing guard `world.promise_faults` (a COVER have no rule enforces fails selftest); false haves (about, nearby, Canada yearly peaks/flow stats, England yearly values) are now next items on the gaps line; owed() demands the rain tile and along-the-river strip. Met Office proven live on River Trent at Colwick (hourly + 7-day, "Powered by Met Office data"). Live on main 2898acb (refresh success, built 15:11Z, index_live 0 mismatches, read live): no blank Sky column on Colwick (0 Sky cells, 24 hourly rows); status page cap 300 (185 links live); home anchors "All 3 Arizona gauges", 0 "1 gauges".

Internal links, live crawl of 285 pages: world pages have 1-5 inbound links (US median 8), 4 link only home/hub/disclaimer; US and world never link each other (fix = nearby block, border rivers). Scale: state and country hubs 700 links (CA/TX near 5-6k US gauges, England near 650); Cloudflare 20,000 files at about 6,500 gauges (3 files each: page, embed, data.json), no check yet; near_dupes O(n^2) about 2,000 pages. Unmeasured: KV writes/day, Actions minutes, build time per page.

Evening batch 2026-11-04, all live on main 9b2e523 (refresh success, built 16:53Z, index_live 0 mismatches, status.json world gaps {} thin {}; England, Kaub, Ottawa, Credit River read live). Lesson: the first forcing guard demanded a rain tile Canada cannot have and named 14 live pages; fixtures passed, only status.json showed it. Each fixture fails without its fix:
- UI: no empty Lower/Typical/Higher scale; England range sentence fixed; Rhine shipping row "Between them"; England one short Unknown line, to-do list below the data; hourly table 3-hour steps; units keep their case; level and feet never split; footer dots gone; jump links on England; German air quality index in words.
- World blocks: nearby gauges on other rivers (100 km, 1-degree squares, 0.1 s at full size), About this gauge (agency station record, coordinates open OpenStreetMap), rate of change (our arithmetic), Canada yearly highs and lows without daily history. COVER: b_nearby, b_about, b_rate have; Canada b_stage_years have; b_map none with a usable reason.
- Pipeline: a source failing 3 times in a row is skipped for the run (the release spent 32 of 33 min on dead boat-ramp calls); world fetch stop-counter per feed (PEGELONLINE down skipped Canada and England) with retries; Canadian zones by the station's offset (Nunavut, Quebec east, west Saskatchewan); two gauges with one address: the second is held; world level must equal its cached reading (check.py world_claims); world in-browser level swap and the Worker's world poll deleted (mixed times on one page); open_wave --pull works for world pages; Cloudflare file_limit check.
Done 2026-11-04 night (main b755fc7, sharded finish refresh OK 23:59Z; index_live 0 mismatches of 185; status.json world listed 42 shown 38 gaps {} thin {}; all 8 Canadian pages show annual_peaks, Ottawa 2024 59.44 m on 2024-04-18 = feed 59.437; tile CSS live in the hashed site.css):
- near_dupes: one-permutation MinHash (320 bins, 40 bands of 8) picks candidates, exact Jaccard decides. Measured: 3,000 pages ~3 s (was ~80 min); 14,000 about 15 s. Memory 320 numbers a page, not ~4,000 shingles. Misses a pair at exactly 80% about 6 in 10,000; above 90% never in practice. Breaks: a bug making ~1,000 identical pages costs ~8 min of exact checks (the build already fails). Fixture: one 85% twin among 200 template pages.
- Held world gauges: the release dates each hold in `world-pages.json` ("held"); after 7 days the gauge leaves `gauge_pages`/`stations` with its reason in "dropped", never re-matched. Known edge: a day whose only change is a hold date writes `last-release.txt`, which could hide a release stall for that day.
- Canada yearly peak levels (HYDAT annual peaks, flagged peaks left out): block `annual_peaks`, COVER b_peaks have, enforced by owed(). owed() no longer skips history and peaks on pages without weather.
- Phone tiles: equal row heights; a lone last tile spans the row. Not yet seen on a screen.
- WaterAlert link: already on every US page (lib/page.py official links); item closed.
Still open, in order: world desktop first row (needs screenshots); along-the-river cards vs tables; drop embed copies before about 6,500 gauges; Worker reads the whole live key per visitor (about 10,000 gauges); tools: touch-readable charts, England impact levels, activity-limit coverage study; England next items (Defra, Met Office obs, NRFA, impact levels, FFC, drought, water temperature); Canada flow statistics (HYDAT).

Scale, measured 2026-11-04 (221 gauges live):
- Cloudflare files: 3 per gauge, refused past 20,000 (about 6,500 gauges). check.py `file_limit` now warns at 15,000 files and fails at 19,000. Fix before then: drop the embed copies (about 10,000 gauges), then serve data.json from the Worker.
- KV writes: at most 480 + 96 + 24 a day; one key, so they do not grow with gauges. Shared with asmrregistry: their writes not counted here.
- Worker: every visitor's request parses the whole "live" key (worker line 94). About 70 bytes a gauge, so 1 MB at 14,000; CPU limit 10 ms, likely over near 10,000 gauges (then numbers stop refreshing; the page stays). The cron makes 1 USGS call per 300 gauges; the Worker's 50-subrequest cap hits about 14,000. Both already marked ponytail in the code at 1,500.
- GitHub: public repo, so Actions minutes are free. Cache 6.3 GB of 10 GB (465 entries, 24 saves a day, about 35 MB data cache at 221 gauges). LRU eviction keeps the newest. About 160 KB a gauge, so 1 GB a save near 6,000 gauges: restore and save time grows every run.
- Run time: hourly refresh 8 to 25 min; the 11 UTC release run took 42 min (45-min brake). Measure where the release run spends its time before the next country.
- near_dupes all pairs: about 2,000 pages hits the 45-min brake. A bottom-k shortcut would miss template pages that differ only in readings, so it needs MinHash with banding and a fixture of two pages differing only in numbers.

UI review (light, live, 3 pages, 2026-11-04), worst first, open:
1. World hourly forecast is 24 stacked phone cards; US uses a compact 3-hour table. Give world the same table.
2. England: "Unknown" alerts said 4 times plus a 90-word "Not on this page yet" list above the data; shorten, move below.
3. England/Rhine "Is this normal" bar has no marker; England line "above the bottom 95% ... and above the top 5%" contradicts itself.
4. England tiles "River forecast: Not shown" and "Alerts: Unknown" full width, no reason.
5. Rhine "Also measured" says agency label Normal while headline says Low.
6. Unit style differs between tiles; lone "M" after 1.05 reads as million.
7. "260 cm (2.5 / ft)" breaks inside the unit on phone; long compare labels wrap 4 lines.
8. Along-the-river is cards beside tables; Rhine weather alerts paragraph sits outside a card; air quality "INDEX 0 of 0 to 4" unreadable.
9. Rhine observed time "GMT+1" beside "CET".
10. Ragged half-width tiles on phone (all pages); England jump pills missing; world desktop first row stops at 940 px.
11. Footer "·" dangles at line ends; England credit sentence repeated.

## SEO audit 2026-11-05 (6 agents; full plan in reports/riverwaterlevels.com-audit/ACTION-PLAN.md)
Score 73/100: technical 86, content 71, schema 52, speed 74 (est.), AI search 52. Owner: publisher name + contact email (/contact/ 404; AdSense trust risk). gtag: keep (owner 2026-11-05); revisit only if Search Console Core Web Vitals flags mobile pages. Code next, in order: Louisville "Typical" chip compares the 24 h mean beside +168% (truth); Ottawa 517 vs 526 m3/s on one page (truth); world schema graph + home WebSite/Organization; home and llms.txt say US only; 307 to 301; world titles add country and id; fold 1-2 gauge hubs; lastmod per page.

## Whole world, every water (approved 2026-11-05; this order wins)

## Context
Owner 2026-11-05:
- Rivers, lakes and oceans, the whole world including the US. Every keyword gets measured.
- Compete with everyone (Lakebrief, SNOFLO, USGS, NWS, NOAA, tide and surf sites), but only where our page has more sourced data.

A fresh review proved we lose today on Lakebrief's top 5 lakes (Norman, Choke Canyon, Oroville, Folsom), and not on data: our code can't build a lake page. The US page refuses any gauge without flow (`lib/hero.py:10-23`), `collect.py:13` never fetches lake elevation or storage, and "is this normal" is flow-only (`collect.py:876`).

The deeper problem: what we can't build is skipped silently, so we never know how much we're missing. Lakebrief's real weaknesses:
- 30 days of history only, "no long-term normal".
- Readings a day old.
- Water temperature stuck on "Reading…".
- Its Lake Norman page is mostly "Loading…".
- Storage estimated, 3.4% off the official figure at Folsom.

Each is a win once we can build lakes.

## Step 1. Coverage census (first: it measures the hole)
- `tools/census.py`, run daily in the cloud job (no new cron). It counts every official site per feed:
  - USGS: rivers, lakes, tide sites by state, about 50 calls.
  - NOAA tide stations (one call).
  - ECCC, EA and WSV (lists we already fetch).
- Each site is either `built`, or `held:<reason>`. Reasons: no reading, no time, unit unknown, not water, terms unread, or `code_cannot` (our page can't build this type).
- status.json gets `census` totals per feed. A gate fails when `code_cannot` grows, so a silent skip becomes a number. The selftest has a fixture.
- At 14,000 pages: the calls are per feed, not per page (about 55 a day). A dead inventory endpoint shows Unknown, never zero.

## Step 2. One page for any gauge (the refactor)
- The headline becomes whatever the agency measures: flow, river level, lake elevation or tide. Reuse the level-first path world pages already use (`lib/world.py` feed, `G["feed"]`), not a third template.
- `collect.py` adds codes 62614/62615/72020 (lake elevation) and 00054 (storage), plus daily statistics for them, so "is this normal for today's date" works for lakes.
- Lake wording swaps in (the Lake Constance swap at `lib/world.py:128`). No "River forecast" tile on a lake.
- `b_reservoir`: full pool, % full, storage and the operator's range, from an official source with a `data/sources.json` row.
- Gate: a dammed lake shows the operator's range or Unknown, never our own percentile "normal".
- First test: Choke Canyon (USGS 08206900, 27 years), checked side by side with Lakebrief's page. Then Oroville and Folsom once the California water agency's (CDEC) terms are read.
- Lake Norman is held: Duke Energy is not a government source.

## Step 3. Keyword Planner: every keyword
- Done: rivers (28,068 world plus 10,717 US) and the top non-US lakes (9,900). US lakes (2,824) submitted and processing.
- Queued, one upload after another, about 5 minutes each:
  - Batches 1-4: the rest of the lakes plus "dam level" and "how full is" phrasings (16,731).
  - Batches 4-5: oceans, 8,198 places from NOAA tide stations and Wikidata beaches and harbours, each as "tide times", "tides" and "water temperature" (24,594).
- Then add the river phrasings missing so far: "river height" and "gauge" in the UK, Australia, New Zealand and Ireland.
- Every download goes to the temporary folder and is deleted after merging. Results join `data/keyword-tiers.csv`.
- `tools/world_queue.py` builds one money list across rivers, lakes and oceans: tier × country rate. A shared name (Lake Murray SC vs Papua New Guinea) steps down one tier.

## Step 4. Oceans on the same page
- NOAA CO-OPS (US, public domain) first: water level, tide predictions, water temperature and alerts.
- Abroad: national tide feeds, each with its terms read (`PROVED` rules in `lib/world.py`).
- The same competitor bar applies: tide sites show predictions only; we add observed level, temperature, NWS marine alerts and weather.

## Step 5. Competitor gate and one-reading gate
- `data/competitors.json` lists every item Lakebrief, SNOFLO, USGS, NWS and the tide sites show. Each item is answered have, next or none, and an unanswered item fails the build.
- A weekly scan inside the watchdog flags new competitor items.
- A page ships only with every "have" item its data allows.
- One-reading gate: every reading is printed through one stamp (measure and time). A measure never shows two different "latest" values on one page.

## Order
1. Census.
2. Refactor plus Choke Canyon.
3. Keyword batches, running alongside.
4. Money list.
5. Competitor gate.
6. Oceans.
7. California feed.

Each step: gate, cloud dry run, deploy, live read, PLAN.md.

## Verification
- `check.py --selftest` fixtures: a census `code_cannot` increase fails; a lake page renders level-first with no flow; a reservoir showing a percentile "normal" fails; an unanswered competitor item fails; two different latest readings fail.
- Cloud dry run "refresh OK", then main.
- Live: Choke Canyon ours vs Lakebrief (fresher reading, storage, 27-year normal); status.json `census` totals; one ocean page vs a top tide site.

Progress 2026-11-06 (commit 4424981): lakes 6-13, 17 and 1 built in local preview from USGS + TWDB, not live (enter Google only via open_wave after review): Canyon 907.24 ft typical (TWDB 96.2%), Corpus Christi 91.17 ft typical (78.8%), Medina 1018.59 ft typical (26.8%), Hartwell 647.72 ft below normal, Lanier 1062.69 ft typical, Kerr 287.62 ft below the 10th percentile (NWS KERV2 reads 287.61: real drought), Great Salt Lake 4190.00 ft much below normal, Powell 3537.30 ft NGVD29 below the 25th (only 25-75th published, 7 years). TWDB levels matched USGS within 0.05 ft on all four Texas lakes. HELD: Travis (USGS has no live lake series since 1993; LCRA terms unread), Tahoe (USGS 10337000 publishes gage height only: needs a lake-on-stage path), Mead (no USGS gauge: needs USBR RISE items 6123/6124; RISE terms: usbr.gov disclaimer uses DOI policy, doi.gov/copyright says federal materials are public domain, read 2026-11-06; RISE disclaimer: provisional), Shasta (RISE or CDEC). Reviewer (fresh agent, 97k tokens) on the 9 phone screenshots: FIXED a tile of '–' beside a caption that compares (now the band word: Powell 'Below normal', Kerr 'Much below normal'), 'Last 24 hours' under storage, lakes listed as '– cfs' in nearby lists (now ft), 'Level, flow and flood risk' heading, the reservoir-operator sentence on Great Salt Lake (lakes.csv natural=1), an all-dash Flow column in NWS record lows. Checked and true: Powell +1.3 ft a day (Reclamation's daily values rise the same), Great Salt Lake reads to 0.1 ft (not stuck), Kerr 287.6 ft (NWS agrees). Open from the review: full pool / % full on non-Texas lakes (USACE or NWS published pool needed, never from memory); NWS 'action stage' 1071 ft at Lanier reads as flood level, not full pool. LIVE 2026-11-06 20:19 UTC (main 76647f6, status.json 0 failed): Burkesville KY tile 'Much below normal' (was '–' beside a 'below the 10th percentile' caption); truth gate allows a comparison past the published percentiles only when beyond() proves it and the strip matches the tile; lake pages are checked for a storage tile, not a flow notice. Daily USGS work spread over 24 hours is live. QUEUED: the 9 lakes are rows in data/waves.csv (queue) and data/world-queue.csv (tier 50,000; Great Salt Lake 5,000), so the cloud's daily release takes them first, inside the 25 a day, and open_wave opens them.

## MASTER PLAN 2026-11-06 (deep research, 5 researchers + parity reviewer): docs/research/2026-11-sources/master-plan-2026-11-06.md (laptop only: docs/research is gitignored; with the 6 research notes and the 2026-11-05 API-key audit, terms quotes kept). Order by money:
1. DONE this batch: doubled 'for' ('Typical for this date for Nov 6', live on river pages); lake go-live blockers: title says 'water level' (release page_check gated all 9 lakes in the 2026-11-06 release, gates cleared), open_wave reads lake record years from legacy/stats (min 5: Powell 7), truth_live checks /lake/ elevations against USGS lake codes, index_live uses lib/indexing GAUGE, --pull of /lake/ reversible, link count counts /lake/, lake crumb skips a missing state page, lake direction chip from the 24 h elevation change, E. coli lines in lake words.
2. US coasts on NOAA CO-OPS (public domain, no key; San Diego 9410170 read live), NWS alerts + Surf Zone rip current line (only 22 offices issue it: else 'Not issued'), NOAA-owned buoys only until partner terms are read; CDIP 'not altered' + credit. 19 of 41 top coasts have no water-level station within 15 km: predictions-only with distance shown.
3. USACE CWMS pool + guide curve for Hartwell, Lanier (filed as Buford), Allatoona, Cumberland (Wolf Creek), Table Rock: feed works live, no key; TERMS UNREAD (bot-blocked) = owner reads usace.army.mil disclaimer.
4. Mead and Powell storage from USBR RISE (terms: DOI copyright page says federal materials public domain; RISE page itself unread). 5. Great Lakes on CO-OPS (IGLD 1985). 6. Germany Danube/Rhine normal + flood stages. 7. Canada HYDAT statistics. 8. Ireland, Australia, NZ, France (open terms, low rate guess).
HELD/LINK-OUT: Plymouth, Portsmouth and all UK tide predictions (UKHO barred, NTSLF all rights reserved); Canada CHS tides (non-commercial); LCRA (all rights reserved: Travis via TWDB); TVA (written permission); Poland IMGW; BoM river heights and warnings; India, South Africa tide tables.
OWNER: read 3 bot-blocked terms pages in a browser (USACE disclaimer, water.ca.gov Conditions of Use, USBR RISE); Wales NRW 1-year storage limit (default: accept, keep 12 months); keys later (Norway NVE, NZ Canterbury, Wales NRW); OPW courtesy email before Irish pages; Workers Paid before ~5,300 gauges.
AU/NZ terms quotes saved in docs/research/2026-11-sources/api-keys-audit-2026-11-05.md (2026-11-06).
ChatGPT round 1 on the master plan (2026-11-06), conceded and added: coast pages print CO-OPS quality flag ('q':'p' = Preliminary, read live at 9410170), never 'official reading'; Great Lakes primary block = lake-wide average, shoreline gauge labelled local; rip current adds the NWS Hazardous Weather Outlook, zone and issue time; coast station needs a representativeness check, not only 15 km; NEW WALL: the Worker runs on every page request, so Workers Free caps page views at 100,000 a day (owner: Workers Paid fixes this and the 20,000 files, measured 801 files for 339 pages); open_wave exits 0 while skipping every page: must alarm (watchdog); AdSense approval is the top money risk, publisher name and contact email (owner) are the known gap; Keyword Planner run for 'river height', 'river level', 'gauge', 'dam release', 'water temperature' phrasings. Rejected with evidence: 25 a day stays (owner); NWS stage datum at Lanier/Hartwell/Medina matches USGS to 0.01 ft at the same minute; USGS calls are already batched (8,800 is per-gauge daily work); USACE owner-permission row covers only NW outflow. Round 2 prompt: runs/chatgpt-round2.md.
ChatGPT round 2 (2026-11-06): conceded 25 a day, the 8,800 estimate, the arithmetic, NWS datum pairs, USACE scope, the product promise, and withdrew the doorway and silent-failure claims. DEBATE CLOSED, we won. Kept refinements: say '22 offices returned by the NWS query on <date>'; coast station = shoreline-geometry candidate filter + manual approval of the first 40; USGS statistics labelled 'USGS-published', not proof of an unchanged record; if shown, USGS last_modified is 'USGS record last refreshed', never 'published'. Only open: AdSense approval unproven until Google decides (no documented missing element). FIXED: open_wave writes data/open-wave-last.json with live pages stuck for a fixable reason; watchdog alarms on them (selftest).

COAST PILOT 2026-11-06 (commit after 5da5f57): /coast/san-diego/ on NOAA CO-OPS 9410170, built on the lake path; queued at tier 50,000 ('san diego tides'). Phone review (fresh agent, 85k tokens) FIXED: today's four NOAA tides on the first screen, next tide in the answer strip, no 24 h change or direction chip on a tide, no dead river forecast tile, 'station' not 'gauge', heading 'Compared with NOAA's predicted tide'. OPEN from that review: predicted tide as a dashed line on the water level chart (the caption's solid/dashed promise), full tide table from today 00:00 retitled for 9410170, drop the county drought section on coasts, moon phase/moonrise prominence, waves/swell (NDBC/CDIP terms), 'what the water is like' heading with one row. Norfolk (Sewells Point 8638610) and Myrtle Beach (Springmaid Pier 8661070) built, phone-reviewed (fresh agent, 94k tokens) and queued at tier 50,000. FIXED from that review: tide tile one tide per line, no freshwater fishing link on saltwater stations, 'Tide predictions at this NOAA station', station time, tide-comparison wording. OPEN from it: flash-flood storm reports beside 'No active NWS alerts' (both true; say report times), AQI 0 readings not marked, ramps and marinas inland of an ocean pier, near-identical marina rows, 'Public land at this station' with no distance, nearby list across the country. Census moved off waterservices.usgs.gov to the Water Data API (3 national calls + about 10 site-type calls; 2026-11-06: 8,918 flow sites, 0 states Unknown; a failure keeps yesterday's file and the watchdog flags it after 48 h); noaa_tides built now counts coast pages. Edge at 14,000: 4 CO-OPS calls per coast per hour (300 coasts = 28,800 a day; no published limit: watch 429s); 6-min predictions cached 4 days per station (~30 KB); two coasts with one place name would share /coast/<place>/ (only one today: add -state on a clash like lakes).

ChatGPT data-coverage audit round 3 (2026-11-06), checked against the code and live APIs:
- RIGHT, FIXED (proven live): E. coli used the legacy Water Quality Portal profile (WQX 2.2), which holds no USGS results after 2024-03-11. Chattahoochee at Atlanta: legacy 0 results since 2025, WQX 3.0 81, newest 2026-11-05 at 1,700 MPN/100mL. fetch_wqp now calls /wqx3/Result/search (basicPhysChem), 40 stations a request (140 answered 'Request Entity Too Large' at Louisville), 2 s apart, weekly not daily (the portal's firewall 429s bursts: our test tripped it). Live re-test of the chunked path pending (laptop IP still blocked).
- RIGHT, ALREADY PLANNED: waterservices.usgs.gov retires Q1 2027; our only caller is fetch_census (Years-long sweep item 4).
- ALREADY ON PAGES (ChatGPT could not see the code): dissolved oxygen 00300, pH 00400, conductance 00095, turbidity 63680, nitrate 99133, salinity 00480, water temperature, SNOTEL, NLDI upstream/downstream, EPA ATTAINS, E. coli with sample dates (lab samples are dated, never shown as live).
- WORTH ADDING, ranked by reader value: NDBC waves on coasts (NOAA-owned buoys first), CO-OPS currents and salinity where the station has them (same API, no key), state HAB advisories (California first), USGS Samples API for discrete sediment and nutrients (low reader value, later).
- REJECTED: GLEON (research network, not a government source), lake depth profiles (a handful of lakes have them), biological surveys and HydroLAKES (no reading a visitor at the water uses today), Copernicus and NASA satellite products until their reuse terms are read.

KEYWORD DEBATE 2026-11-06 (fresh agent, 2 rounds, 231k tokens; closed: it conceded 3, 6, 9 and Lake Michigan, I conceded the rest). BUILT: release.py gives the first gauge on a keyword its whole band and every other gauge 5% (an equal split put 15 Guadalupe gauges under 250-search creeks); a row naming several countries gets 0 until one is chosen; check.py queue_over fails a queue row above its Keyword Planner tier (caught 'myrtle beach tides' at 50,000 vs 5,000: now 'myrtle beach tide times'); coast titles lead with '<place> tides and tide times today' and promise water temperature only where NOAA has the sensor; 10 more coasts built and queued (Fort Lauderdale, Chatham, Monterey, Pensacola, Panama City Beach, Port Angeles, New York, Atlantic City, Boston, Galveston Pier 21). AGREED, NOT BUILT YET: lift world_queue CAP for 'water level'/'level' phrasings with a water-type match (Danube 50,000 is capped to 5,000; 'tenis level' must stay out); after first-gauge, keep exactly one ambiguity penalty (drop STEP where a keyword is split); a river name in several US states at 5,000+ is held until hand-picked (Lake Fork TX vs OH/CO/IL creeks, Buffalo AR vs TN, James, Wolf; Sabine/Shenandoah tagged NZ); hand-check the 23 river keywords at 5,000+; Keyword Planner run for 'tide times', 'water temperature', 'river level today', 'dam release', 'gauge' on the top 100 names with 12 monthly values (seasonality: lakes and tides before May); nearby list same basin first; lake and tide state hubs at 3+ pages a state. 10-coast phone review (fresh agent, 144k tokens) FIXED: NOAA water temperature held when it swings over 10 F in 3 days or passes 95 F (Fort Lauderdale read 82.4 to 99.5 F; its title and keyword now say tides), chart breaks the line at 30-min gaps in 6-minute data (Atlantic City drew a 1 h 48 min gap as a 1.6 ft step), thunderstorm line quotes the NWS sentence that names thunder (was 'says Rain Likely'; river pages too), one tide per row, no 'USGS sensor ... rivers' line on coasts. OPEN: Port Angeles air monitor in Canada labelled EPA. HELD: Sarasota, Vero Beach, Virginia Beach (no water-level station within 15 km), Lake Michigan (no lake-wide-average source with read terms), Cape May and Galveston Railroad Bridge (no live water level today).

KEYWORD PLANNER US 2026-11-06 (account livedatacalc, United States, Oct 2025-Sep 2026; ranges only: no running campaign, so NO monthly values, seasonality unmeasurable until the owner runs ads). Batch 1, 488 phrasings on the top 100 queue names + 9 lakes + 13 coasts: 'dam release' 350/mo total, 'gauge' 3,700, 'level today' 10,850 (near zero: no page or title chases them); '<water> water temperature' 90,350 (22 at 100+); 'tide chart' 1K-10K at all 13 coasts. Batch 2, 300 never-measured phrasings (fresh agent's list, runs/kp-unmeasured.txt): 'texas lake levels' 10K-100K, kentucky/oklahoma lake levels, oregon river levels, 'lake levels', 'river levels', 'river flows' 1K-10K (STATE HUBS: biggest open money); '<coast> water temp' (San Diego 10K-100K; 13 places 1K-10K); '<coast> surf report' 1K-10K (San Diego, La Jolla, Galveston, Pensacola, Panama City Beach, Virginia Beach: waves block only at San Diego); 'rip current', 'marine forecast', 'cfs' 10K-100K generic; '<lake> fishing report' 1K-10K (no official source: gap); 'lake michigan water temp' 10K-100K (Great Lakes gap). 403 new rows in data/keyword-tiers-water.csv. Fresh agent (129k tokens): names with a tier 50+ keyword AND a feed we use = 1,276 (lakes 341, coasts 152, US rivers 745, world 38); all names with demand about 3,920; 10,000 keyword-backed pages not reachable on measured demand (more countries or new phrasings needed). BUILT: titles name water temperature only while the tile shows a fresh reading (d7900dd); coasts 'tides, tide times and tide chart'; block order follows searches: coast = tide chart, tide table, waves first; lake = storage, level chart (400265f).

## NEXT BUILD: daily-agency lake pages (queue rows 1-3 unbuilt: Lake Mead, Lake Travis, Shasta Lake, all 10K-100K; owner 2026-11-07 "do all")
Sources proven 2026-11-07 (live read): Mead = USBR RISE catalog item 6123 'Lake Mead Hoover Dam and Powerplant Daily Lake/Reservoir Elevation-ft', 1,039.29 ft for 2026-11-04 (lastUpdate 2026-11-05 13:58 UTC; GET https://data.usbr.gov/rise/api/result?itemId=6123&dateTime[after]=YYYY-MM-DD&order=DESC, header Accept: application/vnd.api+json; 'provisional' disclaimer). Terms read in Chrome 2026-11-07: usbr.gov/main/disclaimer.html -> DOI policy; doi.gov/copyright 'Generally, materials produced by federal agencies are in the public domain and may be reproduced without permission' (asks a link, credit). Travis = TWDB (quoted) 677.15 ft, 93.5% for 2026-11-06 (USGS 08154500 is 'LCRA Lk Travis': LCRA all rights reserved, never used). Shasta = RISE Shasta items stop 2026-06-05 (stale, unusable); CDEC station SHA next: water.ca.gov/Conditions-of-Use read 2026-11-07 states only a disclaimer, no reuse limit (no ads/commercial/cache bar) -> sources.json row 'quoted' with that summary, then fetch CDEC SHA daily or hourly storage/elevation (endpoint not yet read).
Design (coast path is the template, lib/pages.py + collect.py COASTS): data/lakes.csv gets a 'source' column (usgs default, twdb, rise:<item>, cdec:<sta>) and a synthetic site id (TWDB-travis, RISE-6123, CDEC-SHA); collect writes rec['usgs']['rows'] with parameter_code 'AGY' (daily, unit ft) and skips related, nwps, record and stats (no USGS id); LAKE_CODES/LAKE_DATUM gain 'AGY' = 'feet as <agency> publishes (datum not stated in its file)'. Failure list to guard, each with a fixture: a daily value 1-2 days old must say its date, never 'not reporting' (age chip and stale rules read a per-source cadence: daily = stale after 72 h); no 6 h change or direction chip from daily data; truth_live and index_live compare against the agency, not USGS; open_wave lake years and release page_check accept the synthetic id; storage % from TWDB on Travis only. Edge at 14,000: 1 call per agency lake per 6 h; RISE has no published limit.

Progress 2026-11-07 (commit 61ac8ba): agency-lake path built, proven first on Shasta Lake (CDEC SHA, not daily: hourly elevation sensor 6 and storage sensor 15; CDEC: "Dates, times, and output will always be Pacific Standard Time"; DWR terms from the Internet Archive copy of 2026-10-21, the live page answers 403 to scripts: disclaimer only, no reuse bar; sources.json row "cdec"). lakes.csv "source" column (cdec:SHA), site id CDEC-SHA, collect.py fetch_agency + NOUSGS (no USGS, NWPS, NWM or record calls), lake code "AGY" with datum "the datum the operator uses (its feed does not name one)", page.py agency_words names CDEC on every reading line and link (USGS kept for PAD-US and Topo only), check.py foreign_usgs (fixture), truth_live CDEC branch (tamper test: 971.60 vs 971.57 caught), live-sites.json numeric ids only (the Worker poll sends every id to USGS in one request). Local page: 971.57 ft at Nov 6 4:00 PM PST = CDEC 16:00 value; storage 2,255,210 acre-ft shown 2,260,000 (site rounding). waves.csv queue row added: enters with the next daily release (a dry run has no fresh collect, so live proof only after it).
Scale (14,000 pages): 1 CDEC call per agency lake per run; CDEC publishes no rate limit; a dead CDEC feed stales only its page (cache kept). Open on Shasta: info gain vs Lakebrief/CDEC not yet scored (rule 5: no info gain, no page); "how the percentile is calculated" link on a page with no percentile; footer "Data: USGS, NOAA, NWS"; DWR terms read from the archive copy, live page 403s to scripts (owner may read it in a browser).
Health fixes 2026-11-07 (c832a18, live): world-wx now counts successes (live _health: 85 ok, 1 failed: one UBA station 410 per run, cloud only, cause unknown, old answer kept); world-normals/world-access judged on 750 h. Still flagged, not investigated: nwm.medium empty for all 77, stocking empty for all 9, wtemp empty 1, Tionesta 0.89 vs USGS 0.91.
Next on this path: Mead (rise:6123, daily instant at 07:00 UTC, value 1.5-3 days old when read: needs a per-source age limit, else "Gauge not reporting" at 24 h), Travis (TWDB date only, no time: needs a date-only reading line), Shasta info gain vs Lakebrief/CDEC (% of capacity 4,552,000 AF and % of historical average from CDEC, read first).

## SITE STRUCTURE AT FULL SCALE (owner 2026-11-07: "how it looks at maxed scale, silo structure")
Live today (sitemap 2026-11-07): 213 gauge pages /river/<river>/<place>/, 24 river hubs /river/<river>/, 38 state hubs /rivers/<st>/, world pages under /rhine/ /main/ /moselle/ /danube/ /lake-constance/ (Germany: river as top folder) and /canada/ /england/ (country as top folder), 1 lake state hub /lakes/tx/. Lakes /lake/<slug>/ and coasts /coast/<place>/ go live 2026-11-07.
Target silo, one rule for every country and water type (rule 2: one standard):
- L0 home -> L1 country (/us/ is the home today; /de/, /ca/, /gb-eng/ ...) -> L2 region x type hub (/rivers/tx/, /lakes/tx/, /coasts/tx/; world /de/rivers/<land>/) -> L3 water body (/river/<river>/ hub when 2+ gauges, /lake/<lake>/, /coast/<place>/) -> L4 gauge page. Max click depth 4 (today 3).
- Up: every page crumbs to its L3, L2, L1. Down: a hub lists every child it has, never a child that was not built this run (check.py dead-link gate; caught /lakes/tx/ 2026-11-07). Across: 3-5 nearby pages same basin first, lake <-> its inflow/outflow river gauge, coast <-> river mouth gauge.
- Hubs are made by ONE generator from data: a (country, region, type) hub is emitted when it has 3+ built children (keyword debate rule); a statewide official file (TWDB) only adds rows. Today /lakes/tx/ is hand-wired: replace with the generator before the second lake state.
- Queue = one money list over every page kind: gauge, lake, coast AND hub rows ('texas lake levels' 10K-100K was missing because the queue is one row per gauge). world_queue.py reads lakes.csv, coasts.csv and hub keywords.
Fix before scale (cost grows with every page): world URLs to country silos (/rhine/x/ -> /de/rhine/x/, 44 pages, 301 each; '/main/' already collides with any future 'main' slug); lake and coast slug clash rule (-<st> suffix) in one place.
Breaks at full size (14,000 pages): Cloudflare Workers Free 20,000 files at 2.4 files a page = about 8,300 pages and 100,000 requests a day (owner: Workers Paid); USGS daily work about 8,800 gauges; release 25 a day = 560 days to 14,000 (owner cap); a state hub over about 600 rows (California rivers) passes 90 KB gzipped only near 2,000 rows (measured 27 KB raw for 122 rows) but is unusable on a phone: split by basin above 150 rows; sitemap files 50,000 URLs each (fine).
Measured demand (2026-11-06): 1,276 names have a 10+ search keyword AND a feed we use; about 3,920 have demand at all. Pages beyond demand come from new countries and hubs, never from zero-search gauges.

## NEXT SESSION: top 25 new pages, lakes and oceans (owner 2026-11-05: "run it all")
Start prompt: "Read PLAN.md 'NEXT SESSION: top 25' and do it in order; report after each stage with live proof."

Goal: the 25 highest-money new pages from `data/keyword-tiers-water.csv` (tier, then bid), each beating the best competing page on sourced data, each screenshot-checked. No bulk publish: they enter Google through `tools/open_wave.py`.

The 25 (place, kind, Keyword Planner tier, top bid C$, source):
1 Lake Powell, lake, 10K-100K, 13.07, USBR RISE item 508 elevation (parameterId 2), 509 storage, location 393 (daily, provisional) + USGS 09379900 supporting
2 Lake Mead, lake, 10K-100K, 4.35, USBR RISE location 3514, items 6123/6124 (not on USGS)
3 San Diego, ocean, 10K-100K, 4.02, NOAA CO-OPS 9410170 + CDIP 46254 ("Data courtesy of CDIP", unaltered, linked)
4 Norfolk, ocean, 10K-100K, 1.53, CO-OPS Sewells Point + NDBC 44099 labelled offshore with distance
5 Myrtle Beach, ocean, 10K-100K, 0.03, CO-OPS Springmaid Pier + NDBC 41013 offshore (about 58 nm)
6 Canyon Lake TX, USGS 08167700 + TWDB % of conservation capacity
7 Choke Canyon, USGS 08206900 + TWDB (first proof page; side by side with Lakebrief)
8 Hartwell, USGS 02187010 + USACE Savannah guide curve (656 ft, restriction noted, dated)
9 Kerr, USGS 02079490 + USACE 2016 plan guide curve, labelled "published seasonal guide curve", revision date shown
10 Corpus Christi, USGS 08210500 + TWDB
11 Lanier, USGS 02334400 + USACE action zones (no target number unless published)
12 Travis, USGS 08154500 (measurement origin LCRA, labelled) + LCRA 681 ft top of conservation pool; LCRA reuse terms read first
13 Medina, USGS 08179500 + TWDB
14 Shasta, not on USGS: USBR RISE (check catalogue) or CDEC (terms read first)
15 Plymouth (UK), ocean: EA tide gauge observed level (OGL); tide predictions need UKHO (owner key, below)
16 Portsmouth (UK), same as 15
17 Great Salt Lake, USGS lake site (Saltair) + datum
18 Sarasota, ocean, 1K-10K, 23.51, nearest active CO-OPS station (confirm one exists; else held)
19 Lake Michigan, NOAA CO-OPS Great Lakes stations (IGLD 1985 datum named)
20 Lake Tahoe, USGS Tahoe City
21 Brighton (UK), ocean, EA Newhaven gauge + UKHO predictions
22 Virginia Beach, CO-OPS + NDBC offshore labelled
23 Vero Beach, nearest CO-OPS (Trident Pier) with distance shown
24 Panama City Beach, CO-OPS 8729210 area
25 Fort Lauderdale, CO-OPS Port Everglades with distance
(Next: Fort Lauderdale 26, Gulf Shores, Galveston, Chatham, Bodega Bay, Chesapeake Bay, Cape May, Pensacola, Monterey, Key West.) A place whose page cannot beat its competitor is held and the next row takes its slot.

Order (each stage: gates once, push check, dry run "refresh OK", main, live read, PLAN proof):
1. Lake path: CODES += 62614,62615,72020,00062,00054; `lib/hero.py` ctx uses lake elevation when no 00065 (the existing stage_only path); lake wording (reuse `lib/world.py:128` swap); datum named from the parameter code; USGS daily stats for 62614/62615/00054 so "normal for this date" works; lakes added to the gauge list from the census site list (one page per lake, primary series named, others as supporting readings).
2. Source roles in `data/sources.json` and per series: host, station operator, measurement origin, funding cooperator, official reference (Travis proves one "agency" field is not enough). Owner rule applied: created by law and publicly owned = government (LCRA, TVA, USACE, USBR); investor-owned utilities (Duke, Georgia Power) never carry a government label and stay out under the current rule.
3. `b_reservoir`: storage, % only with a named basis (TWDB "% of conservation capacity"), full or conservation pool, operator guide curve when published (dated, versioned file for document-only curves, never "today's target" unless the operator publishes it), feet from pool.
4. USBR RISE fetch (Powell, Mead, Shasta check): daily, provisional, labelled "daily".
5. Ocean path: NOAA CO-OPS station as the gauge (observed level vs predictions kept apart, MLLW named), water temperature, NWS marine alerts (rip current, high surf, coastal flood, small craft), CO-OPS flood thresholds and high-tide flooding outlook, nearest buoy with distance and "offshore" label past 5 km. UK pages wait for tide predictions (UKHO key).
6. New gates (check.py, each with a fixture from the ChatGPT round-3 list, trimmed): datum named on every elevation, both-datum disagreement; observed / predicted / derived kind on every value; source role (a utility never labelled government); % full basis; buoy distance; storage-curve monotonic; pool boundaries; schema drift (missing time = Unknown); time without an offset = Unknown. Reservoir "normal": rule curve and percentile shown apart; percentile suppressed across a datum or operations change.
7. Competitor gate (`data/competitors.json`): Lakebrief items (level, full pool, % full, storage, 7-day trend, recent table, wind) and tide-site items (next high and low, tide chart, water temperature, sunrise) each answered have / next / none.
8. Build the 25. Info-gain score per page by script: count of sourced blocks with data vs the competitor page for the same place (Lakebrief for lakes, tide-forecast.com or NOAA for coasts); a page below its competitor is held.
9. Screenshots: every one of the 25 at phone width, no cap (owner 2026-11-05); a reviewer who did not build them reads `tools/review_brief.md` and lists missing data, misleading labels and empty tiles; fix, then release through `tools/open_wave.py`.

HARD (owner 2026-11-05): no source whose terms bar ads, commercial use or caching; no permission requests; alternative official source or link-out. Every new sources.json row records ads / commercial / cache as allowed or barred from its terms page (gate `reuse_barred`).
Progress 2026-11-05 late (commit 692ab3a on check, dry run pending): stage 1 lake path built and screenshot at phone width on Choke Canyon (local preview, not live): storage 139,000 acre-ft, elevation 190.37 ft above NGVD 1929, 7-day chart, 24 h change, NWS point, rain, air, sunrise, key facts. Still to beat Lakebrief there: USGS daily statistics for 62614/00054 ("Is this normal" is empty), TWDB % of conservation capacity and conservation pool 220.5 ft, direction chip ("Direction unclear" at -0.03 ft), lake words in section headings, a 24 h spark on the storage tile. Live swap in worker/index.js covers /river/ only: extend to /lake/.
Progress 2026-11-06 early: Choke Canyon local page now has "Is this normal" from USGS's own lake-elevation percentiles (26 years; reads Much below normal, with the reservoir caveat) and a TWDB block (20.9% of conservation capacity, named basis; TWDB terms read: free to copy and distribute, credit asked; sources.json ads/commercial/cache allowed). Next in order: inflow and dam-release gauges, record high/low and multi-year elevation chart, direction chip, lake headings, live swap for /lake/ in the Worker, then lakes 2-14 (USGS + TWDB for Texas; RISE for Powell, Mead), then the ocean path, then screenshots of every page and release via open_wave.
Years-long sweep 2026-11-06 (fresh agent, read-only; 203 gauges, 314 pages, 750 files). Corrections: git is not a risk (8 MB after 469 commits; legacy/stats is write-once, about 110 MB at 14,000; 1 GB is 4+ years out); truth_live/truth_world are capped; selftest passes with the clock +400 and +800 days. Breaks, soonest first (dates at 25 gauges a day):
1. USGS key 1,000 calls/h. MEASURED 2026-11-06 11:10 UTC: 951 left (Worker header); a shard spends 3 keyed calls an hour (bulk, 300 ids a call), the Worker 20; the sweep's 300/h was the 09-12 UTC burst of the daily 8-day re-pull plus neighbour list (2-3 calls a gauge in 3 hours). FIXED: lib/common.py day_due puts that work in each gauge's own hour (selftest). Now about 2.5 calls x gauges / 24 an hour: breaks near 8,800 gauges; next step then is the 8-day re-pull in bulk per hour slot (fast_usgs, page cap raised). Ledger already exists: state/collect-timing.json per shard (artifact timing.json).
2. 09-12 UTC daily burst: shard 60-min timeout near 3,600 gauges (about Mar 2027). Fix: daily sources in 24 hash slots (as WEEKLY), static ones (floodfreq, streamcat, attains, rating, ridb) monthly.
3. Cloudflare 20,000 files: release pauses at 70% near 3,600 gauges (about Mar 2027), hard stop near 5,300 (about Jun 2027). Fix: owner buys Workers Paid ($5/month) before then; one archive file per river, not per year.
4. waterservices.usgs.gov retires 2027-02-22: the census (collect.py fetch_census) reads Unknown. Fix: api.waterdata monitoring-locations.
5. Preview APIs statistics/v0 and nims/v0: a 404 from a retired endpoint reads as "USGS publishes no statistics", a false sentence. Fix: canary gauge; endpoint 404 = Unknown.
6. Shard artifacts about 5.4 GB a day (every shard re-uploads all shared files). Fix: upload only files rewritten this run; shared files from shard 0.
7. Full daily record re-download: FIXED df4490d (last 400 days only; Louisville 9 new days, 1.2 s).
8. Actions cache 41 MB a copy now, 2.8 GB at 14,000; runner disk is the wall near 12-15k gauges. Fix: gzip cache JSON, delta merge.
9. Cache lost after 7 days idle forces a full recollect (84 h of key at 14,000). Fix: cap first-collects per hour.
10. Worker poll subrequests hit 50 near 14,000. Fix: same as 1.
11. US queue empties about Aug 2027 with no alarm. Fix: alarm when release has nothing to release.
12. 18 runner-hours a day at 203 gauges, linear; alarms only reach the owner through GitHub. Fix: outside uptime monitor (owner).
13. Node EOL Apr 2027, Python EOL Oct 2028: bump Python, Node and wrangler once a year.
14. runs/refresh.log appends forever on the laptop: keep the last 4,000 lines.
Order: (1) USGS key, (2) only-what-changed through shards and merge, (3) file count, (4) failure honesty (canary, release-stopped alarm, recollect cap, outside monitor), (5) dated retirements as data in data/limits.json.
Lake adversarial review 2026-11-06 (fresh agent; 14 findings). FIXED: (1) two lakes sharing /lake/<name>/ (now -state-site on a name clash; lakes never form river hubs); (2) stats of another code or datum compared (stats file carries "code", page uses it only on a match, no fallback after a failed call; core _SCALAR_KEYS keeps stats_code); (3) 72020 is NGVD29 per USGS (was "the reservoir's own datum"); (4) /lake/ pages bypassed the release gate (indexing GAUGE covers /lake/, embed excluded; preview now noindex until open_wave); (5) lake pages skipped gauge checks (kind_of lake = gauge); (14) daily .gz written atomically, a damaged file is re-pulled. FIXED 2026-11-06 df5234c (preview read: no cfs, no gage height, no NWM; cite says 190.37 ft above NGVD 1929; data.json carries 765 elevation and storage rows; embed titled lake level): (6) lake_words in embed_page; (7) beyond() in ft for lakes; (8) data.json lake series and units, JSON-LD and data link say lake elevation and storage; (9) TWDB block held unless its level matches USGS the same day within 0.5 ft (Choke Canyon 190.38 vs 190.38; selftest); (10) a lake never listed as a flow neighbour, 'This gauge' shows ft; (11) a lakes.csv row uses the lake code and fails alone when USGS has none; (12) lakes and ice gauges get the age script, not the live poll (no false 'could not be loaded'); (13) cite line, NWM blocks hidden on lakes, gauge-datum label only for 00062, alert section never reworded. OPEN: one-reading stamp for two storage numbers (USGS live vs TWDB daily, each with its own time today).
Lake info-gain critique 2026-11-05 (after "Is this normal" landed, commit d2efe45): we lead Lakebrief on 26-year normal, fresher storage, alerts, rain, weather, NWS point, key facts. Short, each a block to build in order: (1) TWDB % of conservation capacity and conservation pool (Texas), USACE CWMS pools elsewhere; (2) inflow and dam-release USGS gauges (related block for lakes); (3) record high and low elevation and multi-year chart from USGS daily values; (4) water temperature: satellite lake surface temperature (Copernicus Land LSWT or NOAA CoastWatch), terms first; (5) TPWD weekly fishing report per lake, terms first; (6) state HAB advisories and boat-ramp closures, terms first; (7) direction chip from the 24 h elevation change. Oceans: no page type yet (stage 5). Sources still to read for "no API missed": TPWD fishing reports, satellite lake temperature, NOAA GLERL (Great Lakes levels and ice), NWS Surf Zone Forecast (rip current risk), state beach advisories, CWMS lake pools per USACE lake.
Site structure (owner 2026-11-05): separate silos /river/, /lake/, /coast/; hubs per state for lakes and coasts; links lake to inflow and outflow rivers and to nearby coasts; one design system; check.py link budget per silo. Plan it with the competitor gate in stage 7.

Keys, from the API-key audit 2026-11-05 (fresh agent, terms pages read; full table in runs/api-keys-audit.md, temporary):
- Do NOT sign up for UKHO ADMIRALTY UK Tidal API: the free tier bars caching and its terms bar commercial use (developer.admiralty.co.uk/faqs, /TandC). UK tide times: link out; England shows observed tides from the EA gauges we hold. Rows 15 Plymouth, 16 Portsmouth and 21 Brighton are held unless their page still beats the top tide site without predictions; Gulf Shores, Galveston and Chatham take their slots.
- Owner 2026-11-05: use Met Office for UK weather. When secret METOFFICE_SITE_KEY exists: read the DataHub T&C PDF first (ads clause; record ads/commercial/cache in sources.json for the reuse_barred gate); if allowed, a daily UK weather fetch within the free 55 calls a day (weather only: Met Office has no tide predictions).
- Met Office DataHub Site Specific: the free plan is 55 calls a day for one site; hourly coverage of 300 coasts needs the £198/month plan. Not needed for the 25 (NWS covers the US). The pasted key still must be regenerated.
- Free keys for later countries (owner signs up): Natural Resources Wales (api-portal.naturalresources.wales/products), Environment Canterbury NZ (apidevelopers.ecan.govt.nz), Bangladesh FFWC (api.ffwc.gov.bd, terms shown only after sign-up). SEPA needs no key (Referer header). Ireland OPW wants a courtesy email with our server IPs (owner sends; this is their stated condition, not a permission request).
- Keyless and allowed, biggest money: Texas Water Development Board (about 6 places with 10K+ searches, 20 with 1K+), CDEC, Hub'Eau, LINZ tides, Irish tides, Australian state portals, BoM tide tables (credit plus two disclaimers).
- Barred, alternative in brackets: UKHO tides (link out), Canada CHS tides (link out; Bay of Fundy), France SHOM tides (link out), BoM river-height and warning pages (state portals; warnings link out), Goulburn-Murray Water (Victoria portal), Gladstone water board (Lake Awoonga), India, South Africa and Philippines tide tables, utility lakes.
- Unverified (read before use): India CWC and INCOIS, South Africa DWS, NZ councils and LAWA, WaterNSW, TVA, Israel Water Authority, GRDA, LCRA, FFWC terms, Northern Ireland feed, SHOM observed tides, Met Office commercial clause, UK observed tides outside England.

Edge case at 14,000 pages: RISE is daily (about 50 lake calls a day), CO-OPS one call per station per hour (300 stations = 300 an hour, 7,200 a day, no published limit: ramp and watch 429s), USGS lake codes ride the existing calls. Screenshots never scale: the competitor gate and info-gain script decide past the first 25.

## Debate with ChatGPT, rounds 1-3, outcome (2026-11-05)
- ChatGPT conceded 15 points (Met Office, USGS before USACE/USBR, our permissions, CO-OPS already ours, Allatoona = USACE, one page type, Lakebrief history claim, river ranking, rate limits, its false "already in audit" claim, Hub'Eau wording, guide curves, RISE IDs, fixtures).
- Verified by us: USGS 08154500 marks Travis data "obtained from LCRA"; RISE item 508 is Lake Powell daily elevation, parameterId 2.
- Our position kept against it: LCRA is a public authority created by the Texas Legislature, so government under our rule (same as TVA); its "suppress Travis" fixture is rejected. Its DST fixtures guard a case our feeds never produce (all times carry offsets); one fixture (time without offset = Unknown) is kept. Debate closed: what remains are one-request checks done in the build step that uses them (LCRA terms, Kerr plan revision, other operator-origin USGS lakes, beach flags, Hub'Eau producer licences, CDIP terms read on CDIP's page).

## ChatGPT data-gap audit, 2026-11-05, with rebuttal (nothing below is verified until read on the agency's own page)
- Wrong or stale in it: "Met Office DataPoint retired" (our row is Site Specific; the real fix is a new key, the pasted one is burned); "start with USACE/USBR" (USGS already has elevation, storage and daily stats for 736 lakes, our own feed; USACE `cwms` and USBR `usbr` are already owner-permission rows); "NOAA CO-OPS is new" (`coops` quoted; the gap is ocean pages, census 302); Lake Allatoona as Georgia Power (it is USACE); "four separate page models" (owner order: one standard page, blocks by data); most of its 27 gates already exist (country proof, four states, stale limits, one_latest, unit allowlist, suspect, empty = Unknown).
- Kept, added to step 2/4 work, each a check.py gate with a fixture: (1) datum named on every elevation, mismatch blocks (Lakebrief shows Lanier in NGVD29); (2) observed / predicted / derived kind on every value, a tide prediction never prints as a reading; (3) source owner class, a utility (Duke, LCRA) never carries a government label; (4) % full only with a named basis (conservation pool vs total) from an official source; (5) buoy distance to the beach always shown, never "at the beach".
- Kept as blocks: NOAA CO-OPS flood thresholds and high-tide flooding outlook (metadata and derived-product APIs) on ocean pages; HAB advisories and beach closures as separate dated blocks (California first; other states one by one).
- Licence warnings to verify before any use: CHS IWLS (Canada tides) and IOC SLSMF read as non-commercial; Australia BoM varies by data owner; Hub'Eau (France) licence not stated; SEPA 5,000 anonymous credits a day; NVE needs registration.
- Missed by it: USGS lake codes and stats (cheapest win); the blocker is our flow-only page code, not data; scale limits (USACE about 1,500 calls a day; district migration changes shapes).

## Keyword Planner, lakes and oceans, 2026-11-05 (account livedatacalc, all locations, Oct 2025 to Sep 2026)
- Asked 53,963 keywords in 7 uploads: Wikidata lakes with an English article (10,753 names), USGS lake sites plus Lakebrief lake names (US), NOAA tide stations, Wikidata beaches, bays and harbours (8,198 places as "tide times", "tides", "water temperature"), and "dam level" / "how full is" phrasings.
- 4,332 have searches (`data/keyword-tiers-water.csv`: keyword, tier, top-of-page bid in CAD, kind). 10K-100K: 25 lake searches (Lake Powell, Mead, Lanier, Travis, Shasta, Choke Canyon, Corpus Christi, Medina, Canyon, Hartwell, Kerr) and 7 ocean (San Diego tides, Norfolk tides, Myrtle Beach tide times). 1K-10K: 141 lake, 261 ocean.
- Lakes and oceans carry ad bids; rivers mostly did not (Great Salt Lake up to C$28, Sarasota tides C$23.51, Brighton tides C$12.95).
- Census first run: USGS 9,605 flow gauges (203 built); our code cannot build 1,747 level-only, 736 lakes, 91 tidal, plus 302 NOAA water-level stations.
- Fresh review: today we would build none of Lakebrief's top 5 lakes (no lake path). Choke Canyon is the first fix (USGS 08206900, 27 years).
- Rivers not re-asked: 28,068 world plus 10,717 US keywords from 2026-11-01 stand. Missing river phrasings ("river height", "gauge" in GB, AU, NZ, IE) are next.

## 2026-11-05 evening batch (main 4b41fe9, dry run refresh OK, refresh success; live read)
- Truth: normal tile names the latest reading when its band differs from the 24 h average (Louisville). Canada and Germany 7-day flow thinned from the newest point, so "Latest" is the agency's latest; a side reading of another time names its own time. Gate `one_latest` (check.py, gauge and world pages, fixture): failed 8+ German pages on its first cloud run (Frankfurt 92 beside 60 m3/s), all pass now. Live: Mainz 487 m3/s in both places.
- Why the truth gate missed it: truth_live checks each number against the agency alone; two true readings 15 min apart passed. Coverage today: flow only, chart vs "also measured". Systemic next: every reading printed through one stamp (measure + time) and one gate over every page and measure.
- SEO: 301 redirects (live: Louisville no-slash 301). Home H1, description and llms.txt name every country with a built page (live: Canada, England and Germany).
- Lakes (owner 2026-11-05): non-US lakes join the one money ranking. Wikidata: 10,753 lake names with an English article; top 4,950 by language count sent to Keyword Planner (9,900 keywords). Then ChatGPT scrutiny of the top 50, feed match, reservoir gate before the first reservoir ships.

## 2026-11-05 early batch (main 9dfa532, refresh OK; live read)
- truth_live: parallel fetches, live mode 300 pages an hour rotating: 28 s at 185 pages (was 92-313 s, 5-min limit). Every page within 47 h at 14,000. The --dir gate still checks every built page; its NWS calls run 8 at a time (~9 min at 14,000 if every page has a forecast point: next limit).
- Run-time ledger (audit item 1): `lib/ledger.py`, cache/_ledger.jsonl; refresh steps and slowest shard; status.json `ledger` names the page count where each stage breaks; watchdog alarms when under pages + 750. Live first reading: shard collect 231 s at 288 pages, breaks near 3,367 pages. Release stage not yet timed.
- Key facts (owner 2026-11-04, for Google AI answers): stable sourced sentences, never the live reading; check.py fails a page with a station record and no Key facts, or Key facts with a live number or a word for now. Live: Louisville (drainage, record span, 1937 peak, NWS stages), Ottawa (2019 peak 60.70 m = agency 60.701 m on 2019-04-30), Kaub (agency record 825 cm). World link budget 60 -> 125 (one standard page).
Next: limits file + code scanner (audit items 2-3); 9-area status line.

## Machinery audit, 2026-11-04 night (fresh agent, read-only; its numbers, not yet re-checked)
Why missed: every heavy step is continue-on-error, so runs read green; no per-stage time is recorded (refresh.py log stays local, release collect writes no timing, shard timing.json unread); the 45-min brake reads whole-run wall clock incl. queue wait and never sees the release; 22 ponytail ceilings are comments, no script compares today's count to them; the scale rule is a sentence, not a measurement; same failure class fixed 4 times one-off.
Master audit to build (unattended, no new cron):
1. `tools/ledger.py`: every stage appends run id, gauges, seconds, calls per host (data cache, 90 days); projects to 14,000 and to 60 days at 25/day; fails a stage past 45 of 60 min or a quota past 70% (USGS 1,000/h, Met Office 360/day, Worker 50 subrequests, KV 1,000/day). Replaces the brake's gh read.
2. `tools/scale_lint.py` in `check.py --selftest`: page loop in page loop, network call in a gauge loop without a total budget, retry without deadline, counter shared across feeds, a ceiling comment with no `data/limits.json` row.
3. `data/limits.json` + checker: each ceiling as data (where today's value is read, limit, growth per gauge); watchdog alarms when the break is under 30 days away.
4. A check that times out is a fail: Unknown in status.json and an alarm.
Then delete: PLAN "Limits"/"Scale, measured" prose, the per-change 14,000 paragraph, agent scale reviews.
Breaks found, soonest first:
1. truth_live (watchdog.yml:48; tools/truth_live.py:70-76, :136 one NWS call per page, serial): 92-313 s at 185 pages, timed out 2 of 12 runs today, log-only. Every run at ~300 pages (~Nov 9).
2. 09 UTC USGS burst (collect.py:1484 usgs_full, daily_due :1160): over the 1,000/h key at ~900 gauges (~Dec 1); Worker poll then freezes live numbers; a 429 never sets USGS_OUT.
3. Same 09 UTC burst for 14 daily sources: shard collect 4,030 s vs 1,249 s at 08; shards die ~4,000 gauges (45 min ~3,000).
4. Code change rebuilds every page (build.py:107): ~0.8 s/gauge, 90-min limit ~6,700 gauges (estimate).
5. Hourly refresh parses every cache 3 times (build, check, truth_tests, coverage): brake ~3,400 gauges (estimate).
6. Worker cron parses live-sites.json (98 B/gauge) + live key every 3 min: 10 ms CPU ~5,000-8,000 gauges (estimate).
7. Worker parses single-rivers.json on every /river/ 404: ~5,000 gauges under bots (estimate).
8. Release collect serial, untimed, builds up to 3 times; flaky source can again cost ~33 min (does not grow).
9. Every shard downloads the full data cache (186 KB/gauge): ~52 GB/h at 14,000 (estimate).
10. Yearly archive per country passes Cloudflare 25 MB at ~2,700 gauges in one country.
11. World pages rendered twice per run; flat-country along() all pairs (behind WORLD_MAX 400).
12. gauges.json 117 B/gauge, 1.6 MB at 14,000 on phones' missed search (not in the 90 KB count).

## Live block audit, 2026-11-04 02 UTC (script, every gauge page in the sitemap: 162 US, 37 world)
Blocks with data, US / world:
- rate_of_change 157/0
- gauge_map 162/0
- nearby_gauges 162/0 (world along_river 17/37)
- about_gauge 162/0
- record_comparison 161/0 (world official_marks 36/37)
- world_history 2/37 world
- flow_chart 162/23
- river_forecast 99/8
- drought 160/8
- camera 29/0
- hourly_forecast 0/162 US: check, likely a different US block id; not proven a gap.

Most US-only rows are federal products with no foreign twin (cpc, wpc, nwm, radar, snowpack, tides). The world gaps the page's own data could fill: rate of change, gauge map, about this gauge, nearby gauges, and history for Germany and Canada.

Research report `reports/River page tool gaps.md`, also read by ChatGPT. Build order agreed after the debate:
1. Charts readable by touch.
2. A WaterAlert link for this exact gauge, once the URL is verified.
3. England impact levels; feed and terms first.
4. A coverage study of agency activity limits on 100 top gauges before building any.

## US vs world parity audit, 2026-11-04 (second read-only agent, 17 stages, code checked)
Fixed same night: country and river hubs had the 60-link budget of a prose page, so the 46th gauge on /canada/ (23 links live) would refuse every deploy; now kind "country", budget 700, carryable.
World gaps still open, worst first:
1. Two world gauges whose titles slug alike share one URL; the second overwrites the first (build.py about 207).
2. Canada zone is America/Toronto for every province: Nunavut 1-2 h off, east Quebec 1 h. Take the offset from the feed.
3. Phone refresh swaps only the cm number: feet line, 24 h change and label stay from the build with no note; keyed by name, Moselle names mixed case may never refresh. `pollWorld` reads PEGELONLINE only (Canada and England never refresh between builds); one URL for all ids, about 400 gauges at 16 KB.
4. truth_world.py runs after deploy only, tolerance 0.5 m (a m/ft slip under 0.23 m passes), no time check, 40 pages a run. Move into GATE_2 on dist_next, about 0.05 m, check reading time.
5. No world claims-vs-cache, rank_checks, hater_rules, truth_tests or break_blocks case.
6. Lost dist/ cache: `choose` treats live pages as new and a gap pulls them; lost `_river-<slug>.json` drops that river's pages and hub, alarm only past a quarter of world gauges. Add world URLs to failed_urls.
7. WORLD_MAX 400 counts held gauges. A day where every US pick fails exits 1 and drops the world adds. World fetch has no retry or 429 wait (`retry_json`).
8. Watchdog: world pages rebuild every run, so the 6 h alarm misses a weeks-old reading; one dead station never alarms; outside links unchecked. A dead or renamed station keeps its last row forever. `open_wave --pull` cannot pull a world page.
Not checked: corrections, PEGELONLINE name casing and URL limit, world "not reporting" age.
Next: the mechanical parity script (owner approved 2026-11-04): list every US/world branch and every check that skips world pages; build one German, Canadian and English page and run every US check on it; render world pages with the clock shifted 2 days and across a clock change; feed each world source empty, cut short and failing and prove only its country goes Unknown.

## Road to autopilot (approved 2026-11-02; this order wins over the numbers below)
One session per stage. Each batch: `check`, dry run, main, read live, update here.
1. Done 2026-11-03: `FROZEN` cut; next items are page to-dos; the thin floor decides per page.
2. Nov 5-7: match foreign queue rows to agency station lists in `tools/world_queue.py`; ambiguous stays not ready; 15-row sample.
3. Nov 7: one ranking, tier x country rate x can show ads.
4. Nov 7-11: unattended world release: `world-pages.json` generated from the queue, `release.py` picks world gauges inside the 25 a day, per-gauge holds back to the queue, wrong-gauge guard, feed-driven `fetch_world` and `pollWorld`, daily count split US and world. Dry run, 5 a day, then 25.
5. Nov 11-12: limits: world past 150; one national USGS query before about 7,850 gauges. Measured 2026-11-03 at 164 gauges: build, check and deploy 35 s; a shard collects 8 gauges in 40-50 s (about 5.5 s a gauge, NWS forecast and rain the biggest), so the 45-minute brake sits near 9,800 gauges, not 2,200. A National Water Model outage made one run 354 s (20 s an empty call); `NWM_EMPTY` now stops it after 3 empty answers. Next measure: a model-due run with the service healthy.
6. Nov 12-14: England as data, no custom code.
7. Nov 14-16: trim CLAUDE.md, runbook for an owner with no Claude, `/code-review high`, fresh website audit.
Nov 17-20 spare. Short of time, cut England first, then past-150 limits, then `none` answers. Never stage 4 or truth guards. Done means three days with no session open: site grows, no false alarm.
Owner by date: contact email and AdSense consent mode now; SEPA, OPW, NRW sign-ups before Nov 12; uptime monitor before Nov 20; Workers Paid when the alarm says.

## Next steps (in order; full speed)
Done 2026-11-01: one template live, `lib/world.py`, Kaub and Konstanz, phone width read. Canada next: ECCC `api.weather.gc.ca/collections/hydrometric-realtime` (no key, 5-min level and flow, 8,840 rows per station, 30 days) plus `hydrometric-stations` (coordinates, drainage), `hydrometric-daily-mean`, `hydrometric-annual-statistics`: can fill the US flow path, not only stage-only; add a FEEDS row and label our normal as ours, not official. Credit: Data Source: Environment and Climate Change Canada. Canada live with 2 of 5 test gauges, hub `/canada/`, level label is our rank against monthly means (level datum shifts across decades can skew it: move to flow if a label looks wrong). `lib/world.py` `choose` holds any world page over 75% alike, in `gauge_pages` order, so text drift never blocks a deploy; a held gauge returns by itself. More unique data per gauge lets more publish. 4 Austrian Danube gauges have no coordinates in the feed. Last step: spawn a fresh website-expert audit, project wide, top 15 defects, no edits.
0. Done, kept for the record: one template. `world_gauge_page` is a hand-built copy and looks worse than US pages. Convert feed readings into the record `lib/hero.py` reads, use the stage-only path, and build world gauges with `render.build_tab`; each feed supplies agency name, credit, unit and label. Delete `world_gauge_page`, `world_rules`, cut river tables to gauge, level, change, label. All 119 US pages must build unchanged. Phone-width screenshot before ship. World gauges share the 25 a day through one ranking (decision 2026-11-01).
1. Done 2026-11-02: file stop follows `WORKERS_PAID`.
2. Release that picks world gauges itself, unattended. Done: shared page `world_gauge_page`, Kaub and Konstanz, `world_rules`, 80% rule. Missing: `tools/release.py` knows only US gauges; world gauges enter by hand through `gauge_pages`; `collect.py` and `pollWorld` read PEGELONLINE only, so a new country is still code. Make it data.
3. Second country by feed. Terms paraphrased, read 2026-11-01. Pass: Canada (ECCC api.weather.gc.ca, no key, commercial use allowed, no thresholds; ad use is our reading), England (EA flood-monitoring, no key, OGL, typical range), Scotland (SEPA KiWIS, OGL, free registration: owner), Ireland (OPW, CC BY 4.0, courtesy email: owner, stations 00001-41000 only), Germany. Wales: NRW free key (owner), OGL, feed unread. Fail: Australia (test station ended, scraping barred), NZ (no national feed, a council bars ads). Unread: India; Switzerland FOEN (31 lakes with flood marks, hydrodaten.admin.ch geojson, no key; terms PDFs 404, so unused until read).
4. Match foreign queue rows to each agency's station list before ranking: many carry US searches (15 Canada-only and 3 NZ-only rows share a keyword with a US row; Yellow River is almost certainly China).
5. Publish order: one ranking, score = search tier x country ad rate x can show ads now. Rates are guesses until AdSense gives ours: US 1.0, Canada, UK, Ireland, Germany 0.8, India 0.1. No-number gauges last. Live hubs: Rhine, Moselle, Main, Danube (WSV reaches below Vienna), Lake Constance; next cruise rivers as feeds pass. Cruise competition seen 2026-11-01: one manual site, one app, no government-feed table.
6. `/code-review high` before 2026-11-20, with the reader review of ice and label pages, then hands off.
Then: official thresholds on 5 famous rivers; outreach drafts (owner sends).
Demand ideas, no numbers yet: Como, Garda, Maggiore, Geneva, Titicaca, Panama Canal, Gatun Lake, Victoria Falls, Seine, Rhone, Douro, Mekong, Nile.
Stopped: web push, favorites, units switch. No custom code per country.

## Queue notes
Keyword Planner worldwide (Oct 2025 to Sep 2026, account livedatacalc) plus Wikidata rivers with an English article. Upload limits: 9,900 works, 28,068 fails silently; defaults to Canada; ranges only; no ad-value signal. Search numbers miss real demand (Albuquerque "no data"), so Search Console overrules once it has data. Quarterly repeat is manual: `tools/quarter/`.

## Limits (dates at 25 a day)
1. USGS 1,000 calls/h: history weekly in 168 slots, 325 calls/h at 9,100; a 429 stops history for that run.
2. Data cache: 16 MB at 97 gauges, about 1.5 GB at 9,100. GitHub evicts oldest; no pause rule.
3. NWS about 5 calls/gauge/hour: fetch on the 2 h rebuild rhythm. Before 2,000.
4. GitHub 20 free parallel jobs, all taken by 20 shards: use 16.
5. `check.py` and `truth_live` on rebuilt pages only. Before 3,000 (not measured).
6. Cloudflare 20,000 files, 3 per gauge: Workers Paid (100,000) or one shared embed page. Before 6,000, about July 2027. 14,000 gauges is 42,000 files.
7. Release pauses over 70% of plan files, a refresh over 45 min, or 10 Worker stops a day on the free plan; each holds growth, never a page.
8. World Worker refresh: station names in one URL break near 150 gauges; a whole-feed reply (786 stations, about 650 KB) risks the 10 ms CPU. Before 150: per-feed copies from the hourly build, or Workers Paid. Each country adds one feed call per poll.
9. World history in `collect.py`: 2 calls per gauge per hour on shard 0, one job; about 2 h at 6,000. Before 500: bulk current reading, weekly marks, split across shards.
10. KV: USGS at most 480 writes a day plus world 96, of 1,000 shared.
11. `_redirects`: rules after the first dynamic one count against 100; single-gauge forwards live in `single-rivers.json` plus the Worker. Link budgets: home 300, state 700.

## Open data
NWPS `mediumRange` empty: the page says Not issued, which is true; no change due. Off: NID, TVA schedules, NPS alerts (needs key). Left out: Atlas 14, Wild and Scenic, lock status, American Whitewater (verdicts), FEMA zones (owner), inundation link. Open: access points, bacteria advisories, unit allowlist fixture.

## Owner only
- Workers Paid ($5/mo), then GitHub variable `WORKERS_PAID`=1: 100,000 files; free is 100,000 requests a day shared, past it error 1027 until midnight UTC.
- Publisher name and contact address; `data/publisher.json` email is empty.
- AdSense: turn on consent mode in Privacy & messaging (flags are off by default); add a contact email, then build `/contact/` and link it in the footer.
- AdSense decision. CSP stays report-only while ads are on pages.
- Free sign-ups: SEPA registration, OPW courtesy email, NRW key.
- Replace the Google robot key `livedatacalc-automation` (printed in chat 2026-10-31); old key starts 73f0baf9.
- Confirm a phone visit in Analytics Realtime (owner's Chrome blocks the tag). Confirm the test alarm email arrived.
- Delete `river-pipeline-for-chatgpt.zip` from the Desktop.
- Outreach emails; domain renews 2027-10-16; source-permission visits (USACE, TVA, Recreation.gov, NID).

## Done recently
- 2026-11-01: world hubs and shared gauge page live.
- Unverified: new queue order first releases from 11 UTC 2026-11-02; ice stage-only page has no live gauge yet; retry after a failed deploy.
- Deploy freezes show green on GitHub; only the watchdog alarm caught them.
