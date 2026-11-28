# PLAN: riverwaterlevels.com

History: `docs/plan-history.md` (the whole pre-trim file is there under "Trimmed 2026-11-27"). Rules: `CLAUDE.md`.

## NOW
- LIVE 2026-11-27 CORPS TARGET (lake pages): dryrun 46096851287 + deploy refresh 46097986647 success; /lake/allatoona-lake/ reads "Corps seasonal target today (Top of Conservation) 831.73 ft, USGS 829.82 ft, -1.9 ft, bottom 800.08 ft", Source CWMS SAM read Nov 27 9:27 PM EST.
- LIVE 2026-11-27 SPAIN BOATING RULES: 12 pages (7 Ebro CHE, 5 Guadiana BOE) from data/es-boat.json; 2 Opus truth reviews (3 wrong rules fixed first). Re-read sources about quarterly (block hides after 365 days). Unverified: CHE PDF board and one-year lines. Tajo/Jucar held (legal notice unread). Next: EEA bathing sites cloud download test.
- LIVE 2026-11-27 SPAIN ROUND 2: capacity fix (comparisons only on weeks within 10% of today capacity; Contreras/Mequinenza/La Serena etc. were mixing scales), weeks-after table on 43 pages, parking/water/toilets/motorhome (OSM, edited >=2021, 3 nearest, edge distance). Opus review SAFE. Next candidates: boating rules Ebro+Guadiana 12 pages (CHE/BOE), EEA bathing sites (needs cloud download test). Rejected: hub 4-week, last-time-this-full, picnic/food (stale OSM).
- Cloudflare daily cap (100,000, whole account), FOUND 11-27 (Cloudflare analytics, UTC days 11-16..11-27): asmrregistry is 90-95% on the over-cap days (11-16 102k, 11-18 131k, 11-19 127k, 11-26 102k); this site 7-12k a day. 11-18/19 match the Googlebot errors (cause of the 11-20 search fall still unproven). Fix at source: asmrregistry (folder 'Downloads/claude files', wrangler.toml runs the Worker first on /creators/*; why it is called so often: not read). Own session there. Backup here (not built): take /river/* off the Worker (keep redirects, headers, live numbers). Or $5/mo Workers Paid (owner).
- OWNER 11-27: "fixed the site issue from cloudflare" (what changed: not stated). Read 11-27 12:29 UTC: 8 pages and a live JSON answer 200, Googlebot user-agent 200 on one river page, robots.txt open. Cap fix NOT verified: read full UTC-day totals for 11-27 and 11-28. Same read: USGS calls left on the Worker key 11 (one sample; check against the release stall).
- OWNER 11-27: "I killed asmrregistry" (not verified here: read request totals for full UTC day 11-28; this site alone ran 7-12k a day).
- Spain sameness, live 11-27 (5-word runs, 50 pages): with numbers no identical pair, closest 63%, median 22% of a page found on it alone. Words only, name removed: 2 identical pairs (Barrios de Luna = Porma; Alcorlo = Buendia), 17 pairs 95%+: one template, the difference is the data.
- Google fall 11-20: no manual action, no security issue (11-27). Cause unproven. Compare again 12-03.
- LIVE 2026-11-27 SPAIN MAX HELPFUL (owner: no pause): places from OpenStreetMap (27 of 50 pages; refresh by hand about quarterly, tools/es_access.py; block hides after a year) and fill month by month, last 10 years (50 pages). Read live: 50 pages, place links match data, none noindex; two independent reviews, phone shots read (first read FAIL on the month table, fixed and live).
  Not built: official bathing list (ministry download has a bot check: owner downloads censoaguasbano_2025.zip, CC BY 4.0); weather warnings (AEMET key and warning-feed terms unconfirmed); fishing and boating rules per reservoir (reuse unconfirmed, not researched per reservoir). Still no ads on /es/. Map-place edge cases open: distance uses outline corners; names not checked on the ground; one beach name may appear twice when over 300 m apart.
- Bug, not fixed: collect.py fetch_es does not wait a day after a parse or zip failure (re-downloads hourly). Nits: chart aria label lower-cases names; CLAUDE.md still says English only and "same tags" (Spain has no ad loader).
- NEXT BUILD (3-way consensus 11-27, packet docs/chatgpt-prompts/2026-11-27-number-one.md; ChatGPT and Gemini read to last line): lake pages show full pool + today's USACE guide curve + "ft above/below" each, labelled, sourced. VERIFIED: USACE CWMS API has Allatoona.Elev-Guide Curve.Inst.1Day (office SAM, to 2029) and Elev Raw-USGS (same scale as USGS 02393500, both 829.67 on 11-27 per lakelevels.info). Edge cases: datum mismatch (USGS vs USACE) = held; lake with no CWMS curve = line omitted, not guessed; summer full pool shown in winter reads as "low" = show seasonal curve first; CWMS down = Unknown. Then title alias (Lake Allatoona / Allatoona Lake). Agreed by all three: Google drop is site-wide, not this page; read GSC position by query once 12-01 (one full week after the update ended). UNVERIFIED: ChatGPT's "Nov 10-24 core update". Disagreed: both AIs say slow or pause the 25/day release; kept (owner rule). Gemini flags ad near the top: CLS guard in place (unfilled slot keeps its space).
- Candidate: Kinneret (Sea of Galilee) level page, Israel Water Authority daily level; first read its reuse terms (decision 7), then demand check. Edge cases: Hebrew-only source, level below sea level (negative metres), red-line thresholds quoted only from the agency.
- Open Spain gaps: no Spanish consent or privacy page; Analytics consent-denied pings UNVERIFIED; first changed weekly file not yet seen.

## Goal
OBJECTIVE ABOVE ALL (owner 2026-11-20): make as much money as possible. Release 25 pages a day until the queue is empty (owner 2026-11-20); no keyword or water is dropped for being small. The most useful page for a person deciding about this river today, anywhere (reader: CLAUDE.md), is how the money is earned. AdSense earnings from people helped.
Earns $0 from AdSense until approved. Plan figure after approval: $150-$250 a month average (model, 2026-11-21, made before the 11-20 fall was measured); owner goal $1,500 a month by 2027-11-10.
Release: 25 a day (owner 2026-11-24 "25 a day keep it").

## Reader
A person at or near this water today, on a phone, with 30 seconds (full text: CLAUDE.md "Reader"). One page per place people search for, even when it shows the same feed or gauge as another page (owner 2026-11-08).

## Dated numbers
- Search impressions a day (API, read 11-27): about 200 until 11-19 (187); 8-19 from 11-20 to 11-26. Queries: 615 (11-12..19), 28 (11-20..27).
- Bing did not fall (about 1.2K impressions a day, read 11-24).
- Crawl stats to 11-24: 6.75K requests, 74 server errors (73 on 11-18 and 11-19: 57 /river/, 17 /live/; both Worker-first paths). Three failed pages read 200 on 11-27.
- Worker requests in 24 h of 100,000 (watchdog logs): 167,181 peak seen 11-18; 98,536 on 11-26; 81,926 on 11-27. Earlier note: asmrregistry used 123,517 on 11-18 and /river/ answered 429 until midnight UTC.
- Adsterra: 11-24 107 impressions $0.08; 11-25 partial 59, $0.04. 11-27 LIVE: banner moved under the reading on Now tabs (proof: /coast/fort-lauderdale/ slot before footer); compare daily impressions 11-28 vs 11-24.

## Checkpoints (tools/gsc_read.py)
| Date | Pages | Views/month | Google clicks/month | Lever if missed |
| 2027-01-10 | ~1,800 | 8,000 | 2,000 | AdSense approved? indexing (index_inspect) |
| 2027-04-10 | ~4,000 | 40,000 | 12,000 | position: page-two pages vs top results, links |
| 2027-07-10 | ~6,300 | 100,000 | 35,000 | CTR on pages at position 1-5 |
| 2027-11-10 | ~9,000 | 200,000 | 70,000 | RPM: measure; more lakes and coasts (higher searches) |

## Next steps

## Waiting
- 2026-12-07: Rio Grande at Albuquerque title test (clicks and CTR vs the 28 days before). Read 2026-11-15: the page left results for every 'albuquerque' query on Nov 5 (109 impressions Oct 25-Nov 4, 0 since; ~40 a day to ~2), four days BEFORE the title change of Nov 9, so the 28-day baseline is not comparable; still 'Submitted and indexed', canonical and title fine. Likely new-site ranking churn; compare against Nov 9-Dec 7 only.
- 2026-12-11: Search Console Links (referring domains) after outreach.
- 2026-12-21: tide-table pages, impressions after 6 weeks; a page with none is improved or pulled.
- 2027-01-06: refresh run time reaches its 45 min limit near 1,761 pages (live ledger 2026-11-11, worst runs: shard collect 553 s and truth_live 433 s at 367 pages; was 1,011 before 16 shards). Fix then: data/pipeline.json shards 16 to 20 (GitHub free cap on parallel jobs); past that, truth_live checks a sample of unchanged pages. The watchdog warns 30 days ahead.
- 2026-12-03 main Search Console re-read; 12-04 and 12-25 /es/ re-read.
- 2026-12-11 outreach replies (FWC email, batch 3). Dana Richardson: E-Z Boat Storage consent for the Lake Conroe camera.
- Stocking pages for GA, MA, NH: read the first page the release opens there. Float-time, floods and "years like this one" blocks: phone reviews as they fill (history, items 13, 19, 36, 37).
- Embeds pitch (item 38): reply to Dana drafted, needs owner "send".

## Limits (dates at 25 a day)
1. USGS 1,000 calls/h: history weekly in 168 slots, 325 calls/h at 9,100; a 429 stops history for that run.
2. Data cache: 16 MB at 97 gauges, about 1.5 GB at 9,100. GitHub evicts oldest; no pause rule.
6. Cloudflare 20,000 files, 3 per gauge: Workers Paid (100,000) or one shared embed page. Before 6,000, about July 2027. 14,000 gauges is 42,000 files.
7. Release pauses over 70% of plan files, a refresh over 45 min, or 10 Worker stops a day on the free plan; each holds growth, never a page.
8. World Worker refresh: station names in one URL break near 150 gauges; a whole-feed reply (786 stations, about 650 KB) risks the 10 ms CPU. Before 150: per-feed copies from the hourly build, or Workers Paid. Each country adds one feed call per poll.
9. PARTLY DONE 2026-11-11: world feeds spread across shards, PEGELONLINE bulk current reading; the 8-day history is still one call per station (about 6,000 an hour at 6,000 world gauges); split the station list near 500 stations on one page.
10. KV: USGS at most 480 writes a day plus world 96, of 1,000 shared.
11. `_redirects`: rules after the first dynamic one count against 100; single-gauge forwards live in `single-rivers.json` plus the Worker. Link budgets: home 300, state 700.
12. NOAA CO-OPS: 4 calls per coast per hour, no published limit (300 coasts = 28,800 a day): watch 429s. RISE and CDEC publish no limit.

## Owner only
- AdSense: reapply possible since 11-26 (owner's call; advice: after the traffic cause is clearer). Turn on consent mode in Privacy & messaging.
- Cloudflare Workers Paid $5 a month, if the free fix for the request cap is not enough. Needed anyway before about 5,300 gauges (WORKERS_PAID=1).
- Replace Google robot key livedatacalc-automation (shown in chat 2026-10-31, starts 73f0baf9).
7. Five outreach forms with a CAPTCHA (Claude may not solve): upstateca.com/contact-us, callvillebay.com/contact, cartersvillemuseumcity.com/contact-us, kerrlakeguide.com/contact-us, Lake Canyon Yacht Club. Text in docs/outreach-emails.md.
8. Phone check: open the site on your phone, Claude confirms the visit in Analytics Realtime (your desktop Chrome blocks the tag).
9. Say "send" and Claude emails AirNow one line (site, URL, contact@); optional.
10. Free sign-ups in your name before those countries: SEPA (Scotland), OPW courtesy email (Ireland), NRW key (Wales); later Norway NVE, NZ Canterbury.
- Decisions that stay yours: publisher name, pages to Google beyond 25 a day, ads and consent, keys, money, cutting a block.
