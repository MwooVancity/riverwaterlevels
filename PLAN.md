# PLAN: riverwaterlevels.com

History (dated batch logs, audits, debates, research, old step lists): `docs/plan-history.md`. Rules: `CLAUDE.md`.

## Goal
The most useful page for a person deciding about this river today, anywhere (reader: CLAUDE.md). Objective: AdSense earnings from people helped.
Scarce resource: Claude time. From 2026-11-20 the owner moves from Max to Pro (owner 2026-11-03): sessions continue but far fewer, so growth slows, never stops; everything must run alone between sessions, and the costly builds (world release, limits) belong before Nov 20.
Bottleneck: AdSense approval, then readers. Earns $0 until approved; calcscrape and asmrregistry were rejected as low value content, so approval outranks page count.

## Reader
A person at or near this water today, on a phone, with 30 seconds (full text: CLAUDE.md "Reader"). One page per place people search for, even when it shows the same feed or gauge as another page (owner 2026-11-08).

## Numbers
- Live 2026-11-08 09:08 UTC (`status.json`, sha ec8f169): 216 gauges, 340 pages, 802 files, 0 failed URLs, 0 block errors, 20 shards 0 failed; world 48 listed, 44 shown, gaps {}, thin {}; median reading age 38 min.
- Phone reviews: `data/reviewed.json` 77 pages passed (2026-11-07 night).
- Search Console 10-20 to 10-29: 359 impressions, 1 click, position 15.7, 60% Albuquerque (no newer read).
- AdSense 2026-11-01: "Getting ready". Consent message shown 0 times.
- Queue: `data/world-queue.csv` 20,000 rows (`tools/world_queue.py`); about 2,500 non-US lake and ocean rows, none built (2026-11-07). US factory: `data/waves.csv` 25 a day by itself.
- Ad rate guesses (`RATE` in `tools/release.py`) until AdSense reports ours: US 1.0; Canada, UK, Ireland, Germany 0.8; India 0.1.
- Demand (2026-11-06): 1,276 names have a 10+ search keyword AND a feed we use; about 3,920 have demand at all.
- Target: about 13,900 gauges (US 7,564; Canada 2,627; England 2,421; Germany 786; Ireland 467), about May 2028 at 25 a day. Judgment, not measured.
- Tide prediction-only (2026-11-08): 3,264 NOAA prediction-only stations (2,242 subordinate, which answer only `interval=hilo`); 59 tide keywords at 1K+/mo match one station; 9 pass the build rules (`data/tide-picks.csv`).
- Bytes 2026-10-31: gauge page 50 KB; Google tag 181 KB; ad script 206 KB, 89% of a phone's download.

## Next steps (in order; full speed)
1. Tide prediction-only pages: 9 stations committed (e3a6893; Mission Bay re-added, owner 2026-11-08: same gauge as a nearby page is fine), not yet collected, built or phone-reviewed. Next: collect (hilo for subordinate stations), build, phone screenshots + fresh reviewer, then release. Rules (owner decided 2026-11-08 "they have other data blocks, should be fine"): keyword 1K+/mo on one station in one state; reference station first, a subordinate names its reference and claims no observed level; a real NOAA reading within 25 km named with distance; every tide labelled a prediction; predictions fetched weekly; 25-page pilot, past ~100 only after AdSense approval. Before linking: prediction-only truth check (next high/low vs NOAA) and a `break_blocks` sample.
2. Internal links (owner 2026-11-08 "godlike"; rules live in CLAUDE.md and check.py gates, no separate doc). Measured live 2026-11-08, 336 sitemap pages: 0 orphans; US river pages median 8 inbound, 7 outbound to other water pages (nearby_gauges by distance + breadcrumb Home > state > river hub when one exists); world pages weak: Canada median 2 inbound and 0-1 outbound (Credit River page links only /canada/), England 0-3, Lake Constance 0. Build in order: (a) nearby_gauges on every world page from the same generator as US (nearest built pages, any country, any water type), gate: every water page links 3+ other water pages; (b) cross-type links: a river page names the nearest built lake and coast pages and back, once lakes/coasts are live; (c) same-river up/downstream links named as such where the river has 2+ pages; (d) hub pages (river, state, country) list every child, gate: every water page has a hub parent in its breadcrumb; (e) home and state hubs link the top pages by searches. Anchor = the place name the searcher typed, never 'click here'.
3. Daily, before the 11:00 UTC release: the next 25 queue rows linked, built, phone-reviewed, info-gain scored.
4. Country of every ocean and lake queue row (script) and a systemic foreign-namesake rule (searcher country from Keyword Planner, or a gazetteer; kinsale = Ireland, botany bay = Sydney, dungeness = Kent), never more list entries.
5. Ireland coast path: Marine Institute ERDDAP tide predictions (CC BY 4.0, heights above OD Malin, datum named), Met Éireann weather and warnings (terms read live first), USNO moon; `/coast/<place>/`; Kinsale first (5,000/mo). CO-OPS IGLD branch in `truth_live` before the first Great Lake page.
6. Missing sources in queue order: Great Lakes (CO-OPS IGLD + GLERL lake-wide), USGS-less lakes (USACE CWMS or state feed), NOAA/CDIP buoys at the surf-report coasts, then the line-0 gaps a queued page lacks.
7. Lake and coast page gaps from reviews: full pool and surface area (Lakebrief has both), NWS impacts on lake scales (Lanier, Allatoona, Corpus Christi, Barren), moonrise and moon phase on coasts, predicted tide dashed on the chart, Port Angeles air monitor in Canada labelled EPA. Notes (not fails): duplicate ramp rows, nearby rows '–', buoy sea temperature not in the gaps line, 'Next 24 h' times without weekday.
8. Keyword promise table (keyword ending -> required block): water temp -> own reading under 24 h; surf report -> buoy waves; dam release -> outflow gauge; fishing report -> never ready; generic words -> home or hub; barred-only answer -> score 0.
9. Hubs from ONE generator: a (country, region, type) hub at 3+ built children; replace hand-wired `/lakes/tx/` before the second lake state; state lake/river hubs are the biggest open money ('texas lake levels' 10K-100K); hold a hub row when '<state> lake/river' is a real name (Kentucky Lake); 413 keywords on 2+ gauges in one state target their river hub.
10. Keyword debate items agreed, not built: lift `world_queue` CAP for 'water level' phrasings with a water-type match (Danube 50,000 capped to 5,000); one ambiguity penalty after first-gauge; hand-check the 23 river keywords at 5,000+; nearby list same basin first.
11. Structure before scale: world URLs to country silos (`/rhine/x/` -> `/de/rhine/x/`, 44 pages, 301 each; `/main/` collides with any future 'main' slug); lake and coast slug-clash suffix in one place.
12. Scale, each before its number: ~400 world gauges: world fetches across shards, WORLD_MAX up; ~3,600 gauges (about Mar 2027): daily sources in 24 hash slots, release file pause; ~4,000: Worker national changed-since USGS query; ~5,300-5,900: Workers Paid (owner) and fewer files a page; ~8,800: USGS 8-day re-pull in bulk per hour slot; also preview-API 404 canary (endpoint 404 = Unknown), shard artifacts upload only changed files, gzip cache JSON, cap first-collects per hour, alarm when release has nothing to release, `runs/refresh.log` last 4,000 lines.
13. Reviews at scale (~15.6k tokens a page): review once per template variant (feed x kind x block set) plus a machine check that a new page matches a reviewed sibling's blocks and labels.
14. Unattended: a stall signal the owner sees at session start (watchdog report); sitemap entry of a dropped new page.
15. England: remaining no-key sources (Defra UK-AIR, NRFA statistics, terms first).
16. `/code-review high` before 2026-11-20, a runbook for an owner with no Claude, fresh website audit.

## Competitor: Lakebrief (measured 2026-11-08)
- Sitemap 3,805 URLs: 1,246 lakes, each at 3 addresses (`/lake/<slug>`, `/lake/<slug>/water`, `/lake/<slug>/forecast`), all in the sitemap. Lastmod values are real and vary (2,601 at 2026-10-20, 635 at 2026-11-07, 364 at 2026-11-06).
- Live numbers load in the browser ("Loading live conditions…"); the static HTML (~28 KB) holds a short About paragraph naming the gauge ("Live water-surface elevation comes from USGS gauge 08286900"), hand-listed boat ramps with owner, surface and notes, depth-chart link, the managing office phone and address, rules link, marinas and clubs ("We haven't found any... Recommend a marina").
- Titles: "<Lake> sailing conditions — wind & water level | Lakebrief". Ad slots coded, auto ads off.
- 49-lake sample: 19 named a gauge (USGS ids or NWS ids like GASN7, KAWO2); none shared one gauge across two lakes (sample too small to say whether they ever do).
- Candidates that fit our rules (not decisions): (a) separate addresses per reader question only where each holds its own sourced data; (b) hand-checked local access info (ramps, managing office, rules) from official sources with a Source line. Not copied: numbers that exist only after JavaScript (ours stay in the static HTML), anything that is not official data, any visitor-side API call.

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
12. NOAA CO-OPS: 4 calls per coast per hour, no published limit (300 coasts = 28,800 a day): watch 429s. RISE and CDEC publish no limit.

## Owner only
- Owner alone decides: publisher name and contact email; pages opened to Google beyond the daily 25; ads and consent; Search Console; source keys; domain renewal; Cloudflare plan; outside uptime monitor; cutting any block.
- Workers Paid ($5/mo), then GitHub variable `WORKERS_PAID`=1: 100,000 files; free is 100,000 requests a day shared, past it error 1027 until midnight UTC. Needed before ~5,300 gauges.
- Publisher name and contact address; `data/publisher.json` email is empty.
- AdSense: turn on consent mode in Privacy & messaging (flags are off by default); add a contact email, then build `/contact/` and link it in the footer.
- AdSense decision. CSP stays report-only while ads are on pages.
- Free sign-ups: SEPA registration, OPW courtesy email (with our server IPs, before Irish river pages), NRW key (Wales 1-year storage limit: default accept, keep 12 months). Later keys: Norway NVE, NZ Canterbury.
- Read the USACE disclaimer in a browser (bot-blocked; CWMS pools wait on it).
- Outside uptime monitor; GitHub Actions failure-email setting; a running Keyword Planner campaign for exact monthly volumes.
- Decide: a daily scheduled Claude routine that reads GitHub failures and the watchdog report and fixes code (costs tokens daily).
- Replace the Google robot key `livedatacalc-automation` (printed in chat 2026-10-31); old key starts 73f0baf9.
- Confirm a phone visit in Analytics Realtime (owner's Chrome blocks the tag). Confirm the test alarm email arrived.
- Delete `river-pipeline-for-chatgpt.zip` from the Desktop.
- Outreach emails; domain renews 2027-10-16; source-permission visits (USACE, TVA, Recreation.gov, NID).
