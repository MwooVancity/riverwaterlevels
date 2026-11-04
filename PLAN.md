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
Done 2026-11-04 night (commits 2ff7069, f370ed9, 7a6e437; live proof below when deployed):
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
