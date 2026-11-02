# PLAN: riverwaterlevels.com

## Goal
The most useful page for a person deciding about this river today, anywhere (reader: CLAUDE.md). Objective: AdSense earnings from people helped.
Scarce resource: Claude ends about 2026-11-20; after that nobody changes code, so everything must run alone.
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
Truth guards 2026-11-02: `suspect`, alert canary, `truth_world` compares alerts and alarms at 01 and 13 UTC. Still open: US release needs a machine count of new gauges per day; station moves; datum skew; stale facts in code after 2026-11-20.
2026-11-02: a stray colon in `watchdog.yml` stopped the watchdog about 2.5 hours; the dry run now fails on any workflow file that does not parse. Percentiles need a published 10th and 90th, and "below 5th" needs a published 5th; 24 stats files cleaned of NaN.
Alarm 2026-11-02: GitHub ran only 9 of 22 alarm hours in 11 days, so the alarm now fires on the first run in 01-06 or 13-18 UTC, once per half day. Watchdog adds an empty commit after 45 quiet days. If GitHub itself stops, nothing emails: outside uptime monitor is owner-only.
Fresh review 2026-11-02, 13 findings fixed: world age ticks, Canadian agency flags, side readings keep their time and die at 24 h, frozen DWD file reads Unknown, emergency line by country, Kenora and Labrador zones, carry at 5%, watchdog steps time-limited, live world pages never held, past archive years restored, three more alarms. Owner: Workers Paid before about 1,500 gauges, about 2026-12-26; alarm at 1,200.
New country checklist: reading against the agency's page, time zone against the agency, alert coverage on a real active alert, unit and zero point named, terms read, water type labelled (river, lake, reservoir, tidal).

## Road to autopilot (approved 2026-11-02; this order wins over the numbers below)
One session per stage. Each batch: `check`, dry run, main, read live, update here.
1. Nov 3-5: clear every `COVER` `next:` item or answer `none: reason` until `FROZEN` is empty.
2. Nov 5-7: match foreign queue rows to agency station lists in `tools/world_queue.py`; ambiguous stays not ready; 15-row sample.
3. Nov 7: one ranking, tier x country rate x can show ads.
4. Nov 7-11: unattended world release: `world-pages.json` generated from the queue, `release.py` picks world gauges inside the 25 a day, per-gauge holds back to the queue, wrong-gauge guard, feed-driven `fetch_world` and `pollWorld`, daily count split US and world. Dry run, 5 a day, then 25.
5. Nov 11-12: limits: plan-based file stop, world past 150, USGS pause under 300, Worker CPU measured.
6. Nov 12-14: England as data, no custom code.
7. Nov 14-16: stale facts, station moves, datum skew, trim CLAUDE.md, runbook for an owner with no Claude, `/code-review high`, fresh website audit.
Nov 17-20 spare. Short of time, cut England first, then past-150 limits, then `none` answers. Never stage 4 or truth guards. Done means three days with no session open: site grows, no false alarm.
Owner by date: contact email and AdSense consent mode now; SEPA, OPW, NRW sign-ups before Nov 12; uptime monitor before Nov 20; Workers Paid about Dec 26.

## Next steps (in order; full speed)
Done 2026-11-01: one template live, `lib/world.py`, Kaub and Konstanz, phone width read. Canada next: ECCC `api.weather.gc.ca/collections/hydrometric-realtime` (no key, 5-min level and flow, 8,840 rows per station, 30 days) plus `hydrometric-stations` (coordinates, drainage), `hydrometric-daily-mean`, `hydrometric-annual-statistics`: can fill the US flow path, not only stage-only; add a FEEDS row and label our normal as ours, not official. Credit: Data Source: Environment and Climate Change Canada. Canada live with 2 of 5 test gauges, hub `/canada/`, level label is our rank against monthly means (level datum shifts across decades can skew it: move to flow if a label looks wrong). `lib/world.py` `choose` holds any world page over 75% alike, in `gauge_pages` order, so text drift never blocks a deploy; a held gauge returns by itself. More unique data per gauge lets more publish. 4 Austrian Danube gauges have no coordinates in the feed. Last step: spawn a fresh website-expert audit, project wide, top 15 defects, no edits.
0. Done, kept for the record: one template. `world_gauge_page` is a hand-built copy and looks worse than US pages. Convert feed readings into the record `lib/hero.py` reads, use the stage-only path, and build world gauges with `render.build_tab`; each feed supplies agency name, credit, unit and label. Delete `world_gauge_page`, `world_rules`, cut river tables to gauge, level, change, label. All 119 US pages must build unchanged. Phone-width screenshot before ship. World gauges share the 25 a day through one ranking (decision 2026-11-01).
1. Lift the file stop: `refresh.yml` hard-codes a release skip over 14,000 files (about 4,660 gauges, May 2027). It must follow the plan limit or growth stops with nobody to fix it.
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
7. Release pauses over 14,000 files or a refresh over 45 min.
8. World Worker refresh: station names in one URL break near 150 gauges; a whole-feed reply (786 stations, about 650 KB) risks the 10 ms CPU. Before 150: per-feed copies from the hourly build, or Workers Paid. Each country adds one feed call per poll.
9. World history in `collect.py`: 2 calls per gauge per hour on shard 0, one job; about 2 h at 6,000. Before 500: bulk current reading, weekly marks, split across shards.
10. KV: USGS at most 480 writes a day plus world 96, of 1,000 shared.
11. `_redirects`: rules after the first dynamic one count against 100; single-gauge forwards live in `single-rivers.json` plus the Worker. Link budgets: home 300, state 700.

## Open data
NWPS `mediumRange` empty; if still empty 2026-11-29, use NWM bulk files. Off: NID, TVA schedules, NPS alerts (needs key). Left out: Atlas 14, Wild and Scenic, lock status, American Whitewater (verdicts), FEMA zones (owner), inundation link. Open: access points, bacteria advisories, unit allowlist fixture. `truth_world.py` only logs faults.

## Owner only
- Workers Paid ($5/mo): 100,000 files; free is 100,000 requests a day shared, past it error 1027 until midnight UTC.
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
