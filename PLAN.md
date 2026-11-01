# PLAN: riverwaterlevels.com

## Goal
Most useful page for a person deciding about this river today, anywhere. Rivers only, never lakes (Lakebrief has them).
Objective: weekly clicks plus returning visitors. Baseline 2026-10-29: 74 gauges, 0 clicks a week; Search Console week 1: 64 impressions.
Bottleneck: readers, not pages. Scarce resource: about 3 weeks of Claude (subscription ends about 2026-11-20); after that nobody changes code.
US (earns the ads): every USGS flow gauge, `data/waves.csv` 9,099 rows, publishes 25 a day by itself in search-demand order, about 8,900 pages by late 2027. Needs no build time. Held out: 283 names, 490 short-record, 546 tiny-basin, 206 canals and drains.
World: all build time goes here because the US runs itself. EU and UK pages carry no ads until a consent banner exists.

## Target (independent review 2026-11-01)
The page unit is a gauge, not a river name. Live counts: US 7,564; Canada 2,627 active real-time; England 2,421 river-named; Germany 786; Ireland 467: about 13,900, some lakes and tidal still inside. Scotland, Wales, Australia, NZ uncounted; if their feeds and terms pass, 20,000 is reachable. Keep 25 a day: 14,000 finishes about May 2028. Pace stays; order changes. Target and order are judgment, not measured.

## Next steps (in order; full speed, owner 2026-11-01)
1. Lift the file stop: release pauses over 14,000 files (about 4,660 gauges, May 2027) and nobody can edit it after 2026-11-20. It must follow the plan limit. Owner buys Workers Paid (100,000 files).
2. Feed and terms check per country (agent report in progress): official feed, terms read from the agency, source row.
3. One shared world gauge page and a release that picks world gauges itself, unattended, so adding a country is data, not code. Replaces the `/rhine/` code path; `/rhine/` stays as the river summary.
4. Test one page per country against the 80% rule: level-only pages may fail it (guess).
5. Publish order: no country order. One ranking of gauges: search tier first, then can it earn now (US, Canada yes; UK and EU only after the banner), then page richness. Every gauge with a number goes before any without. Among no-number gauges, US pages (richer) go before Canada. Australia and NZ only if a real-time feed and terms pass.
6. `/code-review high` before 2026-11-20 (never ultra), with the reader review of ice and label pages, then hands off.
If time remains: official thresholds on 5 famous rivers; outreach drafts (owner sends).
Stopped: web push, favorites, units switch. Owner: consent banner is what lets EU and UK pages earn; until then they carry no ads or Analytics.
Queue 2026-11-01: `data/world-queue.csv`, 20,000 rows, built by `tools/world_queue.py` from Keyword Planner worldwide (Oct 2025 to Sep 2026, account livedatacalc, no spend) and Wikidata rivers with an English article (40,951 rivers, 25,478 names kept). `docs/research/priority/picks.csv` is its US part (7,448 gauges left on 2026-11-01), and `tools/release.py` publishes from it first, so reordering needs no code. Keywords: 7,048 US, then 28,068 worldwide; 1,476 had a number (only 284 non-US rivers), so 17,114 rows have no demand number. The US part publishes now; world rows are the build queue, in rank order. Groups: first gauge of a river by tier, next gauge lower, no-data US by old score, foreign no-data last (12,243, English-speaking countries first, no feed checked). Edge rules: top tier capped at 1K-10K ("yellow river flow" 500K is trivia); flow alone cannot reach the top tier; a name in 2+ states, abroad, or starting "Lake" drops a tier. Keyword Planner limits seen: 9,900 per upload works, 28,068 fails silently; it defaults to Canada; monthly columns come back empty; bids on only 4 of 7,048 keywords, so no ad-value signal; ranges only. Not done: "flow" and plural wording for foreign rivers; top-result reading; Wikipedia tie-break. Same-river gauges in two states each count as a first gauge. Foreign rows become ready as step 2 lands.
Search numbers miss real demand (Albuquerque no data, 60% of our impressions), so Search Console overrules this order once it has data. Quarterly repeat of the upload is manual, Claude only.
Search Console 10-20 to 10-29: 359 impressions, 1 click, position 15.7, 60% Albuquerque. Quarterly repeat: `tools/quarter/`.

## Global
Rank: searches a month x chance of ranking x clicks per ranking / build days. Only searches are measured; the rest are guesses until Search Console has data.
Every new river must pass all three: demand number, official feed, reuse terms read from the agency. Danube outside Germany (many feeds), Marikina, Kelani (flood readers): not built. No custom code per country in the time left. ChatGPT answers are leads until checked at the source.
`/rhine/`: reader is an English-speaking cruise passenger. Ahrefs US estimates about 2,160 a month (rhine river water levels today 1K; ...for cruise ships 600; rhine water levels 450). Top results on 2026-11-01 are news stories, no live gauge table. Data: PEGELONLINE (WSV), no key, no sign-up, DL-DE-Zero-2.0, terms read 2026-10-31. No forecast (terms unread), no sailing verdict, no Analytics or ads; measured by Search Console only.

## Byte audit (2026-10-31, over the wire)
Gauge page 50 KB; Google tag 181 KB; ad script 206 KB: 89% of a phone's download, both background-loaded. Of a sample page's 46 KB: charts 20 KB (river data, already one decimal), shared scripts 5 KB. Ad script is the biggest cut if AdSense approval does not need it (owner decision). Cache file 324 KB, 78% USGS history; GitHub already compresses it.

## Factory limits (dates at 25 a day)
1. USGS 1,000 calls/h: history about 6 calls/gauge/day = 2,300/h at 9,100. Brake near 800/h, weekly history. Before 500 gauges.
2. Data cache: one saved copy 16 MB at 97 gauges, about 1.5 GB at 9,100. GitHub evicts oldest and keeps the newest, so no pause rule. Compacting was dropped: a cache file is already 324 KB to 29 KB compressed.
3. NWS about 5 calls/gauge/hour: fetch on the 2 h rebuild rhythm. Before 2,000.
4. GitHub 20 free parallel jobs, all taken by 20 shards: use 16. 
5. `check.py` and `truth_live` on rebuilt pages only. Before 3,000 (not measured).
6. Cloudflare 20,000 files, 3 per gauge: Workers Paid or one shared embed page. Before 6,000, about July 2027.
Release pauses over 14,000 files or a refresh over 45 min.

## Open data
10-day NOAA model: NWPS `mediumRange` empty everywhere; if still empty 2026-11-29, use NWM bulk files. Off: NID, TVA schedules (refuse scripts), NPS alerts (needs key). Left out: Atlas 14, Wild and Scenic, lock status, American Whitewater (verdicts), FEMA zones (owner), inundation link (no site list). Open: access points, bacteria advisories (terms, no national feed); unit allowlist fixture. Audit polish left: Memphis empty columns, chart aria values, maskable icon, "168 h" wording, ramps sort.

## Owner only
- Workers Paid ($5/mo) before real traffic: free is 100,000 requests a day shared; past it, error 1027 until midnight UTC.
- Consent banner and AdSense decision. CSP stays report-only while ads are on pages.
- Replace the Google robot key `livedatacalc-automation` (printed in chat 2026-10-31); old key starts 73f0baf9.
- Contact address for "Report a wrong number"; publisher name.
- Confirm a visit in Analytics Realtime from a phone: the owner's Chrome blocks the tag (503).
- Confirm the test alarm email arrived. Delete `river-pipeline-for-chatgpt.zip` from the Desktop.
- Send outreach emails; Search Console Average position; domain renews 2027-10-16; source-permission visits (USACE, TVA, Recreation.gov, NID).

## Done recently
- 2026-11-01: `/rhine/` live, read 19:17 UTC: 10 WSV gauges, Kaub 20 cm (agency lowest 25 cm), no Analytics or ads, in sitemap, linked from home. Fed by `fetch_rhine` on shard 0, `cache/_rhine.json`. Home link budget 300 (201 links froze the Rhine deploy; 144 gauges would have frozen the site). Practice run with a full release passed at 144 gauges.
- 2026-11-01 batches: "Typical for this date", Rising/Falling fast (a quarter in 6 h and 10 cfs), USGS flags worded, About says hourly, 3 foreign gauges gated. Ice: stage-only page when flow is gone or over 30 days old (break gate proves it; no live gauge shows it yet, reader review owed). USGS history weekly in 168 slots (325 calls/h at 9,100); a 429 stops history for that run. Dead gauges keep a not-reporting page instead of retiring. Alarm 01 and 13 UTC. Review signature gate removed. Empty cache: build exits, nothing published (read locally). Spike flag dropped; frozen-page count already in the watchdog.
- 2026-11-01: 8 h deploy freeze ended (built_at 09:38 to 17:21 UTC, read live; numbers kept updating at the edge). Cloudflare counted every rule after the first dynamic one in `_redirects` against the 100 limit; 25 new gauges made 101. Single-gauge river forwards moved to `single-rivers.json` plus the Worker, 4 rules left, `/river/kinzua-creek/` 301 read live. Retry after a failed deploy now rebuilds all pages (untested: runs only when a deploy fails). GitHub shows these runs green; only the watchdog alarm caught it. State pages: "Most searched" line above tables of 13+ rivers (off everywhere today), state link budget 700 (Texas reaches 480 gauges). New queue order on main, commit e50eccb, built_at 17:32 UTC read live, 119 gauges; first release in the new order runs from 11 UTC 2026-11-02 (unverified until then).
- 2026-10-31: pipeline batch, dry run 41201312317 refresh OK, first to pass every gate. `access` and `land` now monthly (303 calls a day at 9,100); land fetched from USGS PAD-US in collect.py, 77 legacy files gone; rule fails a gauge number in a page name; Apple River and Mad River names fixed, old Apple address redirects; release date committed in `data/last-release.txt`; shadow compare step and caches gone; cache pause removed; forecast table row uses the shared word.
- 2026-10-31: first real release, run 41195016454: 23 added, 97 gauges, 149 pages, refresh OK, commit 61c81ab; 07094500 and 13290450 held (no USGS rows). Apple River live, read this turn, no "no published statistics". Pipeline audit, last 5 runs: 3-7 min wall on normal runs; build, gates, deploy 46-54 s; release 34 min (89 s per gauge). Nothing changed.
- 2026-10-31: Google Analytics live, G-96RG42R07G, property 561723165: tag read on home, privacy, one gauge; 120 of 120 main pages carry it once. CLAUDE.md and PLAN.md rewritten for bytes.
- 2026-10-31 00:08 UTC: 14 h deploy freeze ended (E. coli unit "None", a new gauge with no earlier page). Fixed with unit text, `tools/quarantine.py`, one retry per failed release, break test in dry runs only.
- 2026-10-30: rolling rebuild live; failure email back on; failed release undone before refresh; carry limit max(10, 5% of gauge pages).
