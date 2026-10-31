# PLAN: riverwaterlevels.com

## Goal
Most useful page for a person deciding about this river today, anywhere. Rivers only, never lakes (Lakebrief has them).
Objective: weekly clicks plus returning visitors. Baseline 2026-10-29: 74 gauges, 0 clicks a week; Search Console week 1: 64 impressions.
Bottleneck: readers, not pages. Scarce resource: about 3 weeks of Claude (subscription ends about 2026-11-20); after that nobody changes code.
US: every USGS flow gauge, `data/waves.csv` 9,099 rows, 25 a day, about 8,900 pages by late 2027. Queue: 7,498 queued; 283 held-names after a name fix; 490 short-record; 546 tiny-basin; 206 canals and drains stay out.
Global: new build work goes here first (below).

## Next steps (in order; user report 2026-10-31)
1. Wrong text: About says rebuilt every 30 min; runs are hourly.
2. Reader labels: "Normal range" to "Typical flow for <date>", plus Rising/Falling fast at 25% in 6 h; word 13 unworded USGS flags, "less than" on LESSTHAN; clearer "Not issued"; "Measured at this gauge".
3. Ice gauges by 2026-11-15: USGS withholds flow, `lib/hero.py` raises "no flow series" and the page freezes (1,922 gauges in cold states). Build stage-only mode; proof: `tools/break_blocks.py` ice variant renders.
4. Rhine test page (below), during the 2026 record low.
5. USGS quota brake and weekly history, by 2026-11-10 (cliff about 500 gauges, 2026-11-16).
6. Retire gauges dead 31+ days; frozen-page count in the watchdog; spike flag; hold 12355000, 05106000, 04127885 (foreign or wrong state).
7. Empty-cache test; 13 UTC alarm delay. Remove the review-signature gate.
8. Owner runs `/code-review ultra` once, then no more code changes.
If time remains: official thresholds on 5 famous rivers; outreach drafts (owner sends).
Stopped: web push, favorites, units switch, more countries until the Rhine has visits. Ad script off pages until AdSense approval: owner decision.
Queue order 2026-10-31: still the guess score. ChatGPT's list (37 rows, 0 search numbers) is not evidence, so nothing moved; reorder only from bulk search numbers per river, via `tools/release.py`'s owner list. One Google Trends test, US, 12 months: Salt highest average, Guadalupe one July spike, Russian lowest; Salt sits at queue place 1,296.
Search Console 10-20 to 10-29: 359 impressions, 1 click, position 15.7, 60% Albuquerque. Quarterly repeat: `tools/quarter/`.

## Global
Rank: searches a month x chance of ranking x clicks per ranking / build days. Only searches are measured; the rest are guesses until Search Console has data.
Order: Rhine; if visits, Moselle, Main and German Danube from the same source; then the next river passing all three: demand number, official feed, reuse terms read from the agency. Danube elsewhere and other cruise rivers: no demand number, research only. No custom code per country in the time left. ChatGPT answers are leads until checked at the source.

### Rhine page
Reader: English-speaking river-cruise passenger. Ahrefs US estimates (competitor River Cruise App), about 2,160 a month: rhine river water levels today 1K; ...for cruise ships 600; rhine water levels 450; river levels in europe 60; rhine river levels 50. Snoflo shows none in the 2 sitemaps checked.
Standalone `/rhine/`, outside the gauge pipeline: 8-10 cruise gauges upstream to downstream (Basel, Mainz, Kaub, Koblenz, Koeln), level in cm and feet, 24 h change, official low/normal/high label, time, source; a gauge reading is not depth; no sailing verdict. No Analytics or ads until a consent banner; measure by Search Console.
Data: PEGELONLINE (WSV), no key, tested 2026-10-31: `pegelonline.wsv.de/webservices/rest-api/v2/stations/KAUB.json?includeTimeseries=true&includeCurrentMeasurement=true`; `stations.json?waters=RHEIN` (36 stations, 786 in Germany).
Before building: step 1 done; WSV terms read 2026-10-31: DL-DE-Zero-2.0, no attribution required, liability disclaimed; look at the top result. Forecast terms unread: no forecast on the page.

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
- 2026-10-31: pipeline batch, dry run 41201312317 refresh OK, first to pass every gate. `access` and `land` now monthly (303 calls a day at 9,100); land fetched from USGS PAD-US in collect.py, 77 legacy files gone; rule fails a gauge number in a page name; Apple River and Mad River names fixed, old Apple address redirects; release date committed in `data/last-release.txt`; shadow compare step and caches gone; cache pause removed; forecast table row uses the shared word.
- 2026-10-31: first real release, run 41195016454: 23 added, 97 gauges, 149 pages, refresh OK, commit 61c81ab; 07094500 and 13290450 held (no USGS rows). Apple River live, read this turn, no "no published statistics". Pipeline audit, last 5 runs: 3-7 min wall on normal runs; build, gates, deploy 46-54 s; release 34 min (89 s per gauge). Nothing changed.
- 2026-10-31: Google Analytics live, G-96RG42R07G, property 561723165: tag read on home, privacy, one gauge; 120 of 120 main pages carry it once. CLAUDE.md and PLAN.md rewritten for bytes.
- 2026-10-31 00:08 UTC: 14 h deploy freeze ended (E. coli unit "None", a new gauge with no earlier page). Fixed with unit text, `tools/quarantine.py`, one retry per failed release, break test in dry runs only.
- 2026-10-30: rolling rebuild live; failure email back on; failed release undone before refresh; carry limit max(10, 5% of gauge pages).
