# PLAN: riverwaterlevels.com

## Goal
Most useful page for a person deciding about this river today, anywhere. Rivers only, never lakes (Lakebrief has them).
Objective: weekly clicks plus returning visitors. Baseline 2026-10-29: 74 gauges, 0 clicks a week; Search Console week 1: 64 impressions.
Bottleneck: readers, not pages. Scarce resource: about 3 weeks of Claude (subscription ends about 2026-11-20); after that nobody changes code.
US: every USGS flow gauge, `data/waves.csv` 9,099 rows, 25 a day, about 8,900 pages by late 2027. Queue: 7,498 queued; 283 held-names after a name fix; 490 short-record; 546 tiny-basin; 206 canals and drains stay out.
Global: new build work goes here first (below).

## Next steps (in order)
1. Read the first real release after 11:00 UTC 2026-10-31: gauges added, Apple River WI ("no published statistics" despite stats) queued, live count.
2. Fix the break-test fault (nwps stale26h, 01426500: "Forecast high" plus steady) so dry runs reach Gate 2.
3. Rhine test page (below).
4. USGS quota brake and weekly history, by 2026-11-10 (cliff about 500 gauges, 2026-11-16).
5. Ice gauges by 2026-12-01: USGS withholds flow, `lib/hero.py` raises "no flow series" and the page freezes. Build stage-only mode; proof: `tools/break_blocks.py` ice variant renders.
6. Compact the data cache: [time, value] pairs instead of verbose records.
7. Empty-cache test; 13 UTC alarm delay; 07094500 and 13290450 have no USGS rows.
8. Remove the review-signature gate (it needs a human after any code change).
9. Keep readers: web push alerts (approved; VAPID keys as Worker secrets, subscriptions in KV, watch 1,000 KV writes a day), favorites, units switch.
10. Owner runs `/code-review ultra` once, then no more code changes.
If time remains: answer top Search Console queries on the first screen; share card; "checked against USGS at <time>" line; `/ops/` owner dashboard; outreach drafts (embed panel to clubs, outfitters, towns; owner sends).

## Global
Rank: searches a month x chance of ranking x clicks per ranking / build days. Only searches are measured; the rest are guesses until Search Console has data.
Order: Rhine; if visits, Moselle, Main and German Danube from the same source; then the next river passing all three: demand number, official feed, reuse terms read from the agency. Danube elsewhere and other cruise rivers: no demand number, research only. No custom code per country in the time left. ChatGPT answers are leads until checked at the source.

### Rhine page
Reader: English-speaking river-cruise passenger. Ahrefs US estimates (competitor River Cruise App), about 2,160 a month: rhine river water levels today 1K; ...for cruise ships 600; rhine water levels 450; river levels in europe 60; rhine river levels 50. Snoflo shows none in the 2 sitemaps checked.
Standalone `/rhine/`, outside the gauge pipeline: 8-10 cruise gauges upstream to downstream (Basel, Mainz, Kaub, Koblenz, Koeln), level in cm and feet, 24 h change, official low/normal/high label, time, source; a gauge reading is not depth; no sailing verdict. No Analytics or ads until a consent banner; measure by Search Console.
Data: PEGELONLINE (WSV), no key, tested 2026-10-31: `pegelonline.wsv.de/webservices/rest-api/v2/stations/KAUB.json?includeTimeseries=true&includeCurrentMeasurement=true`; `stations.json?waters=RHEIN` (36 stations, 786 in Germany).
Before building: step 1 done; WSV terms read (a catalog says CC BY 4.0, unconfirmed); look at the top result.

## Byte audit (2026-10-31, over the wire)
Gauge page 50 KB; Google tag 181 KB; ad script 206 KB: 89% of a phone's download, both background-loaded. Of a sample page's 46 KB: charts 20 KB (river data, already one decimal), shared scripts 5 KB. Ad script is the biggest cut if AdSense approval does not need it (owner decision). Cache file 324 KB, 78% USGS history; GitHub already compresses it.

## Factory limits (dates at 25 a day)
1. USGS 1,000 calls/h: history about 6 calls/gauge/day = 2,300/h at 9,100. Brake near 800/h, weekly history. Before 500 gauges.
2. Data cache 687 KB per gauge, about 6 GB at 9,100 vs GitHub 10 GB; eviction means a full re-collect. Before 2,000.
3. NWS about 5 calls/gauge/hour: fetch on the 2 h rebuild rhythm. Before 2,000.
4. GitHub 20 free parallel jobs, all taken by 20 shards: use 16. 
5. `check.py` and `truth_live` on rebuilt pages only. Before 3,000 (not measured).
6. Cloudflare 20,000 files, 3 per gauge: Workers Paid or one shared embed page. Before 6,000, about July 2027.
Release pauses over 14,000 files, 7,000 MB cache, or refresh over 45 min.

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
- 2026-10-31: Google Analytics live, G-96RG42R07G, property 561723165: tag read on home, privacy, one gauge; 120 of 120 main pages carry it once. CLAUDE.md and PLAN.md rewritten for bytes.
- 2026-10-31 00:08 UTC: 14 h deploy freeze ended (E. coli unit "None", a new gauge with no earlier page). Fixed with unit text, `tools/quarantine.py`, one retry per failed release, break test in dry runs only.
- 2026-10-30: rolling rebuild live; failure email back on; failed release undone before refresh; carry limit max(10, 5% of gauge pages).
