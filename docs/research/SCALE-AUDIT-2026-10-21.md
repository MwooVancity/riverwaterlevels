# Scale audit: 25 -> 2,000 -> 20,000 gauges (2026-10-21, read-only)

Measured today: 25 gauges, 49 pages, 62 files in dist (6.0 MB), cache/ 25 MB (14.9 MB main JSON = 595 KB/gauge, 4.6 MB cache/daily gz). Fast run ~10 min, full run 43-70 min. Candidate list: 7,857 queue+held+live rows in data/waves.csv (51 states, TX 519 gauges / 261 rivers, biggest river 22 gauges, 1,408 hub pages at full list).

## First break

**Fast collect at about 70 gauges.** `collect.py --fast` is sequential (collect.py:1080) and every NWS/NWPS call goes through `thr_json` with a 1.5 s minimum gap (collect.py:19-27). Per gauge in fast mode: NWS 8 calls (points, radar, forecast, hourly, grid, alerts, stations, observations: collect.py:596-631), NWPS 1-4 (collect.py:95,108-136), rain 1, WPC 2, NWM 0-3, USGS fill 0-2: 13-20 calls, ~12 of them throttled = 18 s floor; measured 10 min / 25 = **24 s per gauge**. 30 min minus ~3 min build/deploy = 27 min / 24 s = **~70 gauges**. After that the 30-min cron (refresh.yml:9) only queues behind the running job (concurrency group `refresh`, cancel-in-progress false, refresh.yml:17-19); `timeout-minutes: 150` kills the run at ~370 gauges; GitHub's 6 h job cap at ~900.

Cheapest fix (ladder):
1. Delete: radar station lookup and observation-station lookup are static per gauge (fetch once, keep in cache); alerts per gauge -> one `alerts/active?area=XX` call per state (51 calls instead of 20,000). NWS calls per gauge 8 -> 4.
2. Change a number: fast lane = USGS bulk only (40 ids per call, collect.py:1035; 20,000 gauges = 500 calls at 1 s gap = ~9 min). Weather, NWPS, rain, WPC move to the 6 h lane. The reader's number (flow, stage) stays 30 min fresh; the forecast is 6 h old at worst (NWS issues twice a day).
3. Same tool differently: the 6 h lane becomes a GitHub matrix job sharded by state (51 shards, each its own cache key; a final job merges caches and builds). Free on a public repo, no new tool. Needed at ~150 gauges for the full lane (see table).
Cost to owner: zero dollars; one editing session on collect.py and refresh.yml.

## Layers

(a) GitHub Actions time. Fast 24 s/gauge, full 103-168 s/gauge (43-70 min / 25; ~50 HTTP calls per gauge: collect.py:905-960). 2,000: fast 13 h, full 57-93 h. 20,000: fast 133 h, full 570-930 h. Limits: 6 h per job (docs.github.com/en/actions/reference/limits), job timeout 150 min (refresh.yml:25), public-repo minutes unlimited and runner is 4 vCPU/16 GB/14 GB SSD (docs.github.com/en/actions/reference/runners/github-hosted-runners). **BREAKS at ~70 (fast cadence), ~150 (full within 6 h, 6 h cron at refresh.yml:10).** Fix: above, plus per-source TTLs: atlas14, NID, FEMA zone, StreamCat, floodfreq, rating, meta, land are static or yearly; fetch once and reuse (`fetch_daily` already has the 20 h TTL pattern, collect.py:702-706). That cuts full-mode calls from ~50 to ~15 per gauge.

(b) actions/cache. 1 MB raw per gauge (0.6 MB main JSON + 0.2 MB daily gz + misc). 2,000: 2 GB raw, ~130 MB zstd (JSON gzips 16x, measured); 20,000: 20 GB raw, ~1.3 GB compressed. Cap 10 GB per repo, LRU eviction, 7-day unused eviction (docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching); a new key per run (refresh.yml:43,74) is fine because restore-keys takes the newest. **Compressed size HOLDS; the runner's 14 GB SSD BREAKS at ~8,000 gauges** (20 GB raw cache + dist/dist_next/dist_prev at 240 KB per page, 3 copies). Fix: store cache/<site>.json gzipped (json.load(gzip.open) as in cache/daily, collect.py:707) and do not keep dist_prev on CI (a fresh checkout has none anyway, build.py:24). Restore/extract of 20 GB raw tar adds several minutes per run; gzipped files remove that too.

(c) Cloudflare Workers static assets. Files per Worker version: 20,000 on Free, 100,000 on Paid ($5/month), 25 MiB per file, Wrangler >= 4.34 for the higher cap (developers.cloudflare.com/workers/platform/limits/, developers.cloudflare.com/changelog/post/2025-09-02-increased-static-asset-limits/). Files = gauges + hubs + 51 states + ~12. 2,000 -> ~2,450 HOLDS. 20,000 -> ~23,700 BREAKS; build.py:13 `FILE_BUDGET = 19000` stops it first at ~16,000 gauges. Fix: Workers Paid, raise FILE_BUDGET, `npm i wrangler@latest`. Largest page 212 KB (check.py MAX_BYTES 260,000) is far under 25 MiB.

(d) Upstream APIs (evidence: search-result unless noted).
- api.weather.gov: "rate limit is not public and is set generously for typical use", retry after ~5 s (weather.gov/documentation/services-web-api). Fast lane today: 8 calls per gauge per 30 min; 2,000 gauges = 8.9 calls/s sustained, 20,000 = 89/s. Not "typical use". Fix as in First break (4 static-per-gauge calls removed, state-level alerts, weather on the 6 h lane sharded).
- USGS OGC API: keyed, hourly limit shown in `X-RateLimit-Limit`, example value 1000 (api.waterdata.usgs.gov/docs/ogcapi/keys); third-party says 1000/hour. Fast lane bulk 40 ids per call HOLDS (500 calls per 20,000). Full lane ~8 USGS calls per gauge (usgs, meta x2, peaks, wtemp, daily, year, fieldmeas, related): 2,000 gauges in 6 h = 2,700/h BREAKS at ~750 per run. Fix: weekly TTL on meta, peaks, fieldmeas, year, wtemp; read the header and sleep when Remaining is low.
- NWPS (api.water.noaa.gov): no published limit found. 1-4 calls per gauge. Treat like NWS.
- AirNow: 500 calls per hour per key (docs.airnowapi.org/faq says per-service hourly cap; 500 is the widely cited number). 1 call per gauge per full run: 2,000 in 6 h = 333/h HOLDS; 20,000 BREAKS at ~3,000. Fix: daily TTL and shard across runs (20,000/24 = 833/h still over): 2-day TTL, or drop the block (observations change hourly, the page is 6 h old anyway).
- RIDB: 50 requests per minute (third-party, docs.airbyte.com). Static data: fetch once per gauge (TTL 30 days). 20,000 at 6 h = 55/min BREAKS only without the TTL.
- NOAA CO-OPS: no rate figure published, only data-span caps (tidesandcurrents.noaa.gov/web_services_info.html). Only coastal gauges call it. HOLDS with a 0.5 s gap.
- ACIS: nothing published found. Already one MultiStnData POST per gauge; daily TTL.

(e) build.py and check.py. build.py keeps every gauge's record in memory at once (`Gs`, build.py:48-58, 79). Measured: a 2.5 MB cache file is 12.2 MB as Python objects (4.7x); average gauge ~2.9 MB. 2,000 -> ~6 GB (fits 16 GB); 20,000 -> ~58 GB. **BREAKS at ~5,000 gauges.** Fix: render each gauge page as soon as its context is built and keep only the dozen fields the directory pages read (lat, lon, lv, p, age_min, obs, chg, nwps forecast flag); `related.close` needs only `related.items` and `lv`. check.py is one pass, sets and dicts, no page-vs-page loop (check.py:133-150, 165-173); the BFS (check.py:215-223) is O(links). It runs twice per release (gates.py:13 and publish.py:46), plus gzip per gauge page (check.py:120): linear, estimate minutes at 20,000, not hours. truth_tests.py reads every cache file (truth_tests.py:28): linear.

(f) Sitemap. 50,000 URLs / 50 MB per file, index for more (developers.google.com/search/docs/crawling-indexing/sitemaps/large-sitemaps). directory.py:281-291 already splits at 10,000 per file into an index; check.py:163 accepts sitemap-1..19 (190,000 URLs). HOLDS to 20,000.

(g) Links and depth. Budgets check.py:13: gauge 110, hub 80, state 480, home 200, depth <= 4 (check.py:227). Home at >150 gauges lists one link per state (directory.py:126-128) HOLDS. State page = ~14 fixed links + 1 per river (directory.py:139-154; CO today: 2 rivers, 16 links). TX at the full candidate list 261 rivers -> ~275 HOLDS; at 20,000 gauges (2.5x) ~650 BREAKS the 480 budget at ~14,000 gauges. Fix: raise the number, or split a state page over 400 rivers by first letter. Hub page 1 link per gauge + ~14; largest river 22 gauges HOLDS. Depth home -> state -> hub -> gauge = 3 HOLDS. gauges.json (build.py:117) grows to ~2.3 MB at 20,000; the "near me" button downloads it: acceptable, or cap to lat/lon/url.

(h) Git. Nothing per gauge is committed: `git ls-files cache runs` = 0; .git is 4 MB. Tracked data/pages-all.csv 2.4 MB grows ~300 B per gauge (6 MB at 20,000). runs/ is pruned to 14 days (refresh.py:42-48) and never committed. data/geo 298 MB is untracked. HOLDS.

(i) Post-deploy checks. tools/truth_live.py fetches **every** gauge page one by one (truth_live.py:63-64) and one NWPS call per forecast point (line 107); tools/index_live.py fetches every allowed and every not-allowed gauge page (index_live.py:39-50). ~0.4 s per fetch: 2,000 gauges = 2 x 13 min + NWPS ~7 min = ~35 min added to each run; 20,000 = ~6 h alone. **BREAKS the 150-min job at ~5,000, and watchdog.yml (timeout 5 min, runs truth_live hourly, watchdog.yml:14,21) BREAKS at ~400 gauges.** truth_live --dir (pre-deploy) is local for pages but still one NWPS call per lid. Fix: a number: check a sample (every page whose hash changed in `state/lastmod.json` is already known, build.py:100-104; sample 100 of them plus 20 random), and compare flood stages against the cached NWPS record instead of refetching.

## Table

| Layer | 25 (measured) | 2,000 | 20,000 | Limit (source) | Verdict | Cheapest fix |
|---|---|---|---|---|---|---|
| (a) GHA fast run | 10 min | 13 h | 133 h | 30 min cron; 150 min timeout refresh.yml:25; 6 h job cap (GitHub docs) | BREAKS at ~70 | fast lane = USGS bulk only; static NWS lookups cached; alerts per state |
| (a) GHA full run | 43-70 min | 57-93 h | 570-930 h | 6 h cron refresh.yml:10; 6 h job cap | BREAKS at ~150 | per-source TTLs (static once, slow daily) + matrix shard by state |
| (b) actions/cache | 25 MB raw (~2 MB zstd) | 2 GB raw / ~130 MB | 20 GB raw / ~1.3 GB | 10 GB per repo (GitHub docs); runner disk 14 GB | compressed HOLDS; disk BREAKS at ~8,000 | gzip cache files; no dist_prev on CI |
| (c) Cloudflare assets | 62 files | ~2,450 | ~23,700 | 20,000 Free / 100,000 Paid, 25 MiB per file (developers.cloudflare.com/workers/platform/limits/); FILE_BUDGET 19000 build.py:13 | BREAKS at ~16,000 | Workers Paid $5/mo, raise FILE_BUDGET, wrangler >= 4.34 |
| (d) api.weather.gov | 200 calls / 30 min | 16,000 / 30 min (8.9/s) | 160,000 / 30 min (89/s) | unpublished, "typical use" (weather.gov/documentation/services-web-api) | BREAKS (politeness) at ~100s | 8 -> 4 calls per gauge, 6 h lane, sharded |
| (d) USGS OGC | ~200/full run | ~16,000 per 6 h (2,700/h) | 27,000/h | ~1,000/h keyed, header X-RateLimit-Limit (api.waterdata.usgs.gov/docs/ogcapi/keys) | BREAKS at ~750 per full run | weekly TTL on meta/peaks/fieldmeas/year/wtemp; honor the header |
| (d) AirNow | 25 per 6 h | 333/h | 3,333/h | 500/h per key (docs.airnowapi.org/faq; secondary) | BREAKS at ~3,000 | 2-day TTL or drop |
| (d) RIDB | 25 per 6 h | 5.5/min | 55/min | 50/min (secondary) | BREAKS at ~18,000 without TTL | 30-day TTL (static data) |
| (d) NWPS, CO-OPS, ACIS | few/gauge | - | - | none published | unknown; treat as NWS | same lane as NWS |
| (e) build.py memory | ~75 MB | ~6 GB | ~58 GB | 16 GB runner | BREAKS at ~5,000 | render per gauge, keep a 10-field summary |
| (e) check.py | seconds | minutes | ~10-20 min, runs twice | linear, no O(n^2) | HOLDS | run once (publish.py:46 repeats gate 1) |
| (f) sitemap | 49 URLs, 1 file | 1 file | 3 files + index | 50,000 / 50 MB (Google); split at 10,000 directory.py:282 | HOLDS | none |
| (g) state page links | 16 (CO) | TX ~275 | TX ~650 | 480 check.py:13 | BREAKS at ~14,000 | raise budget or split big states |
| (g) home / hub / depth | 103 / ~36 / 3 | state list only | same | 200 / 80 / 4 | HOLDS | none |
| (h) git | 4 MB, 0 per-gauge files | +0.6 MB csv | +6 MB csv | n/a | HOLDS | none |
| (i) truth_live + index_live | ~1 min | ~35 min | ~6 h | inside 150 min job; watchdog 5 min | BREAKS at ~400 (watchdog), ~5,000 (job) | sample changed pages; flood stages from cache |
