# Master plan: from 25 pilot gauges to the 20,000-file site (end to end, no surprises)

Status: draft 1 for debate (2026-10-17). Owner: the site owner; every Claude and ChatGPT review reads this file first. Companion files: `docs/MASTER-FINAL.md` (what a finished page holds), `docs/MISSING-LIST.md` (everything not built), `docs/PLAN.md` (living status).

## 0. What "20,000" means here
Cloudflare Workers free plan serves at most 20,000 static files per deploy. A gauge is ONE page (Dashboard and Water merged, jump links) plus a Forecast page only where NWS issues a river forecast (6,436 of 9,099 gauges); river hubs, state pages, trust pages and sitemaps add about 1,700. All 9,099 gauges are about 17,200 files, so the whole inventory fits the free limit and no cap is needed. Order is by water-sports popularity (`data/waves.csv`). 1,801 gauges with unreliable names are held until the name cleaner is rerun. Lakes are phase 2. If the owner later pays for Workers ($5 a month, 100,000 files), the cap is a config value, not a redesign.

## 1. The staircase (each step opens only when the gate above it is green)
| Step | Gauges | Pages | Earliest | What changes | Gate to enter |
|---|---|---|---|---|---|
| S0 | 25 | 98 | now | pilot, noindex hold on | all P0 items in section 11 done |
| S1 | 25 to 50 | to about 200 | owner lifts noindex | first indexing test, Search Console live | review packet passed, identity page live, watchdog green 7 days |
| S2 | 100 | about 400 | S1 plus 14 days | tiered refresh live | at least 80 percent of S1 pages indexed, no duplicate or soft-404 flags, freshness alerts quiet |
| S3 | 300 | about 1,200 | S2 plus 14 days | home page becomes state links, state pages paginate | impressions growing beyond the first cohort, CWV good, no source-terms issue |
| S4 | 1,000 | about 4,000 | S3 plus 30 days | R2 data store, sharded collect, sitemap index | stable indexing rate above 60 percent, accuracy audit clean |
| S5 | 3,000 | about 11,000 | S4 plus 60 days | AdSense live (if approved), alerts product | traffic and revenue test, no manual action |
| S6 | 5,500 | about 17,700 | S5 plus 90 days | cap reached, maintenance mode | all gates, owner decision on raising the cap |
Release rate inside a step: at most 25 new gauges a day, and never faster than the refresh can keep every released gauge current. Time to reach S6 at the maximum rate is about 220 days; the staircase gates make it longer, which is the intent.

## 2. Risk register by domain (trigger, early warning, fix, kill switch)
### 2.1 Google and indexing
- Scaled-content or low-value classification of the whole host (the owner's other site fell about 99 percent overnight on 2026-09-14, cause unproven). Trigger: any release of many similar pages. Early warning: Search Console "crawled, not indexed" above 40 percent of a cohort, impressions per page falling, sitewide impression drop above 30 percent in 7 days. Fix: stop releases, find the common template element, strengthen distinct data per tab, withhold thin tabs. Kill switch: per-wave `X-Robots-Tag: noindex` by path prefix in `templates/_headers`, one commit, deploy within 30 minutes.
- Crawl budget and discovery: sitemap index, internal links at depth 2 from home through state pages, hubs only when at least 2 gauges are released, IndexNow ping for new pages.
- Duplicate or near-duplicate pages: each tab must carry distinct data (Dashboard conditions and alerts; Water history and statistics; Forecast forecast products only). Check: automated block-overlap report per release (fail above 60 percent shared blocks between tabs).
- Titles and descriptions: unique per page, under 60 characters, no stuffing; river names that repeat across states carry the state.
- Stale pages: a gauge not reporting for 24 hours shows the notice; after 30 days the page leaves the build and 410s only if the owner approves (default: stays out of sitemap, returns 404 page).
- Structured data: BreadcrumbList, WebSite, WebPage with honest `dateModified`; Dataset only on national summary pages.
- Core Web Vitals: radar and map images lazy with fixed sizes, no layout shift, fonts system, JS under 30 KB; field data watched in Cloudflare Web Analytics.
- Manual action or policy hit: pre-written response plan, evidence file of data provenance, contact address live.

### 2.2 Data sources and APIs
| Source | Used for | Limit or risk | Fallback |
|---|---|---|---|
| USGS Water Data API (OGC) | readings, stats, peaks, daily, field measurements | 429 on bursts; key gives higher limit; bulk latest-continuous | keep last value with age shown; backoff 1.5 s to 6 tries; bulk calls |
| USGS StreamStats | flood frequency, low flow | endpoint changes, regulated gauges | hide block |
| NWS api.weather.gov | forecast, hourly, alerts, obs | unpublished rate limit, needs identifying User-Agent | alerts by state not per gauge; ETag; retry-after |
| NWPS (api.water.noaa.gov) | flood stages, forecasts, crests, riverflow | per-gauge calls | only gauges with a forecast point; batch with retry |
| NOAA CPC, RFC QPE, WPC, LSR (mapservices) | outlooks, rain, flood reports | ArcGIS service changes | hide block; version check |
| NRCS AWDB, NCEI, OpenFEMA, EPA, USGS National Map | snow, storms, declarations, water quality, topo | terms, availability | hide block |
Rules: no source may block a deploy; each source has a per-run time budget; a source failing 3 runs in a row raises an alert; every block states its source time; schema checks (field presence, units) run on each fetch and reject bad payloads instead of publishing them.
Terms register: `data/sources.json` is the single list; status quoted, owner-permission, unclear, not-permitted; hidden sources (Drought Monitor, dams, Reclamation, ACIS, Atlas 14, FEMA zones) stay hidden until the owner has written answers. Esri flood zones are not permitted for commercial use.

### 2.3 Freshness
Target: released gauges update within 30 minutes (tier 1), others hourly or 6-hourly. Mechanism: GitHub Actions cron every 30 minutes (fast) and 6 hours (full), one deployer, concurrency group, watchdog workflow fails the run and emails the owner when the live site data age is above 3 hours or the page count shrinks by more than 2 percent. Browser-side refresh of flow and alerts stays as a bonus, never the only freshness.

### 2.4 Build, deploy, hosting, storage
- Build writes only changed pages (content hash in meta), the checker streams pages one at a time, sitemap files hold at most 10,000 URLs.
- File limit 20,000: enforced in `build.py` (refuse to build above 19,000 files) and in the release script.
- Data store: GitHub Actions cache is enough to about 1,000 gauges; beyond that Cloudflare R2 (free 10 GB) with one gzip per gauge, trimmed of build-unneeded fields.
- Collect shards: matrix of shards above 1,000 gauges, one shared USGS key, per-shard time budget, merge-and-build job.
- Rollback: `wrangler rollback` to the previous version, documented in the runbook; releases kept; staging deploy to workers.dev before production.

### 2.5 Accuracy and safety of life
- Automated: numeric unit tests (percentile, change, flood stage, flood frequency), stale-data tests, per-run reconciliation of flow and stage against USGS for every released gauge, anomaly rules (flatline over 6 hours, spike over 10x, negative flow, impossible stage) that hide the value and flag the page.
- Manual: weekly audit of 10 random gauges against USGS and NWS pages; monthly audit of the percentile method against USGS statistics.
- Wording: no verdicts; safety line under every hero; disclaimer page; not-a-warning labels; corrections page and email.
- Legal: terms of use, copyright and takedown contact, accessibility statement, credit lines per source.

### 2.6 Money and policy
AdSense: apply only at S5 with 1,000-plus indexed pages and 90 days of traffic; ad slots reserve space; ads off on pages with fewer than 6 data blocks; consent banner for EEA and UK before any ad tag; `ads.txt` after approval; privacy page updated before the tag. Costs (target zero): Cloudflare free, GitHub public repo free, R2 free tier, domain renewal yearly; alarms at 80 percent of any free limit. Revenue is unproven; the plan does not depend on it.

### 2.7 Operations and people
Owner is a non-coder: one runbook (`docs/RUNBOOK.md`) with what to check weekly, what each alert means, how to roll back, who to ask; alerts go to one email; no step requires the owner to run commands. Bus factor: repo public, docs complete, secrets listed with where they live and how to rotate. Security: pinned GitHub Actions, secret scanning, token rotation yearly, SPF and DMARC for the contact address, domain auto-renew and expiry alert.

### 2.8 Reputation and growth
Trust: named publisher, contact, corrections, methodology with changelog, an outside hydrologist reviewing the methodology (a person, named). Authority: data stories from national summary pages ("rivers above flood stage now", "lowest flows for the date"), outreach to paddling clubs, fly shops, outfitters, state agencies, local emergency pages for real links; nothing paid, no link schemes. Distribution: no automated social posting until the data is proven right for 60 days.

## 3. What changes at each size (playbook)
- 25 to 100: tiered refresh, per-wave kill switch, status page, contact page, search baseline.
- 100 to 300: home page state links only, state pages paginate at 100, near-me data per state, rank tracking set up (Search Console plus a rank tool).
- 300 to 1,000: R2, shards, scale test in CI (2,000 and 10,000 fake gauges, fail above 10 minutes or 2 GB), anomaly detection live.
- 1,000 to 3,000: alerts product (Workers, KV, Email Sending), national summary pages daily, ads decision, accuracy audit by sampling bot plus human.
- 3,000 to 5,500: cap management, quality sweep (remove gauges that never earn impressions or that lose data), refresh of recreation ranking with Search Console queries, raise-the-cap decision.

## 4. Quality bar for every page that ships (30-point preflight, checked by script where possible)
Right-now table present; flow, stage, percentile reconcile with USGS; every block has a source line with time; no block from an uncleared source; unique title and description; canonical; JSON-LD valid; no horizontal scroll at 390 px; dark mode contrast; no console errors; tab blocks distinct; stale flags correct; safety line present; links resolve; sitemap includes it; page under 150 KB; images sized; focus order; print CSS; data age under limit; county and state labels consistent; units shown; time zone is USGS's; flood-frequency hidden when regulated; WPC and flood-report blocks hidden when empty; no composed prose; credit lines right; redirects for single-gauge hubs; noindex state matches the wave plan.

## 5. Decision log and owner-only items (with the date each is needed)
| Decision | Needed by | Default if no answer |
|---|---|---|
| Publisher name and contact email | before S1 | do not lift noindex |
| Lift noindex for S1 | owner only | stays on |
| Four terms emails (Drought Monitor, NID, Reclamation, FEMA) | before any hidden block ships | blocks stay hidden |
| Pay for Workers ($5) to pass 20,000 files | not needed under the cap | stay under cap |
| AdSense application | S5 | no ads |
| Hydrologist reviewer | before S3 | methodology stays labelled as ours |
| Lakes and reservoirs | after S6 | out of scope |

## 6. Unknowns to resolve by experiment (not guesses)
Real search volume and SERP features (one SERP-API pull of about 50 queries, or Search Console after S1); whether Google indexes all three tabs or only one; whether Dashboard alone ranks better than three tabs (A/B by cohort); actual USGS and NWS rate limits at 300 and 1,000 gauges; ad revenue per 1,000 views for this audience; CWV field values.

## 7. Positions for ChatGPT to attack (debate list)
1. Cap at 5,500 gauges and ordering by recreation fame first. 2. Three tabs per gauge versus one page per gauge. 3. Staircase gates and their thresholds. 4. 25 pages a day maximum. 5. Hide blocks instead of showing weak data. 6. Data-only pages with no verdicts versus activity pages. 7. Public GitHub repo. 8. Cloudflare free plan as the whole platform. 9. GitHub Actions as the only deployer. 10. AdSense only at S5. 11. National summary pages as the link engine. 12. Kill switch by path prefix. 13. Release before backlinks exist. 14. Treating American Whitewater and USGS as links, not competitors. 15. Alerts as the return-visit engine. 16. What the plan is missing entirely.
