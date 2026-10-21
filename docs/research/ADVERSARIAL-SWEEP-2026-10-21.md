# Adversarial sweep, 2026-10-21 (read-only; nothing run, nothing edited)

Target: "max freshness without breaking at scale" (2,000 then 20,000 gauges). Measured today: 25 gauges, 49 pages. Fast run 12.6 min end to end (refresh step of run 39660155771: 19:16:28 to 19:29:07), full run 48 to 54 min (run 39617735187: 14:33:23 to 15:21:57; run 39571408405: 54 min). status.json at 19:34 UTC: built 19:27, newest reading 28 min, median 43, oldest 88 min. Live pages read: /river/arkansas-river-co/avondale-07109500/, /river/colorado-river-az/lees-ferry/, /river/hudson-river/green-island/. Evidence level: `file` = read in the repo this session; `live` = fetched this session; `gh` = `gh run list/view` this session; `search` = web search result (secondary).

## Findings, worst first

### 1. The list of live gauges exists only in the GitHub Actions cache (and an untracked CSV)
Evidence: `collect.py:902-905` `default_sites()` = whatever `cache/*.json` exists, else the hard-coded 25 in `lib/pages.py:6` (`WAVE0`). `build.py:35` builds only cached gauges. `.gitignore:13` ignores `data/waves.csv`, the only record of which gauges are live (`tools/release.py:26-27`). `refresh.yml:46-48` restores by prefix `rwl-data-`; `refresh.yml:54` falls back to a full run when the cache is empty. Today `data/waves.csv` says 41 live, the site has 25 pages, and 16 "live" rows have no cache file (checked this session). The cache is on a 10 GB LRU with a new key every run (`refresh.yml:46,70`, 48 keys a day).
Why it matters: at 2,000 gauges a lost or evicted cache means `mode=full` for 2,000 gauges = 57 to 93 h (SCALE-AUDIT table a), killed by `timeout-minutes: 150` (`refresh.yml:25`); `Save the data cache` runs `if: always()` and stores the partial cache; the next run is `fast` on the partial set and `build.py` publishes a site with only the gauges that got collected: every other gauge page disappears from Cloudflare (static assets deploy is the full file set). The only guard is `MIN_PAGES = 40` in `tools/watchdog.py:11`, hand-set.
Cheapest fix: delete `.gitignore:13` (track `data/waves.csv`), make `default_sites()` read the `live` rows of it, and make `build.py` exit non-zero when `len(cached) < live rows` (one number compared). A missing cache then collects only the missing gauges, not everything. Effort: 20 min.

### 2. On CI a gauge whose safety block fails is removed from the live site, not "kept"
Evidence: `publish.py:24-29` carries a failed gauge's previous page only if `dist/<url>/index.html` exists. `dist/` is gitignored and not in the cache (`refresh.yml:43-45`: cache and state only), so on every CI run `dist/` does not exist and nothing is carried. `build.py:2` ("its previous pages stay in dist/"), `build.py:48,82` ("previous page stays live") and `CLAUDE.md:33` ("fail the gauge and keep its previous page") are all false on CI. `build.py:21-29` `live_urls()` (fetch `/_urls.json` from the live site) is defined and never called.
Why it matters: an NWS or NWPS outage during collect raises in a `SAFETY_BLOCKS` block, the gauge is "kept", and its URL goes 404 on the next deploy, with its sitemap entry (publish.py:30-41 only patches the sitemap when `kept` is non-empty). Google sees a 404 on a page you just opened for indexing.
Cheapest fix: in `publish.py:26`, when `old` is missing, `urllib.request.urlopen(SITE_URL + u)` and write that body as the new file (5 lines; the live site is the previous release). Effort: 20 min.

### 3. The uncommitted ThreadPoolExecutor patch: do not commit as is
Evidence (`git diff collect.py`, file):
- Thread safety: `_last` and `GAP` are read and written under `_lock` (`collect.py:25-29`); sleeping inside the lock makes the lock a global token bucket, which is correct. `http_json` (`lib/common.py:37-39`) is plain urllib, thread-safe. `fetch_nwps` re-reads `data/nws-crosswalk.json` per call (`collect.py:96`), harmless. No other module global is written in the fast lane (`_COOPS`, `snotel_stations` are full-lane only).
- Backoff is per thread: on a 429 one thread sleeps `Retry-After` (`collect.py:35`) while the other five keep calling at 4/s. NWS asks clients to back off; this does the opposite under load.
- Exceptions: `one()` (`collect.py:1083-1115`) has no outer `try`. `json.load` of a half-written or missing cache file, a missing `rec["usgs"]`/`rec["lat"]`, or any error outside the inner `try`s propagates through `list(ex.map(...))` (`collect.py:1118`), the executor waits for in-flight gauges, then `collect.py` exits 1: `refresh.py:34-37` stops before build, no deploy. One bad gauge stops the whole site's refresh. The sequential loop had the same hole; the patch keeps it.
- Partial writes: `json.dump` to `.tmp` then `os.replace` per gauge (`collect.py:1113-1114`) is atomic and per thread; the second phase (`collect.py:1120-1127`) is sequential. Safe.
- Stdout: `print("ok fast", s, ...)` with several arguments (`collect.py:1115`) writes piecewise; lines interleave across threads. Cosmetic (CI log only); one preformatted string fixes it.
- Unthrottled calls now run six wide: `fast_fill` (`collect.py:1064`) and `fetch_rain`/`fetch_wpc` (`collect.py:650,676`) use `http_json` with no gap. `fast_fill` is the real problem: `need` is true whenever two flow readings are more than 20 min apart in the last 6 h (`collect.py:1057-1060`), so every gauge that reports hourly or half-hourly (Avondale and Lees Ferry report on the hour, live) fetches two USGS P6H series every run, forever. 2,000 gauges = up to 4,000 USGS calls per 30 min = 8,000/h against a key limit of about 1,000/h (SCALE-AUDIT d).
- NWS tolerance (search): no published number. The official page says the limit is unpublished and generous for typical use (weather.gov/documentation/services-web-api, cited in SCALE-AUDIT). A secondary catalog says throttled requests "typically clear within 5 seconds" and that a unique identifying User-Agent is required (apis.io/rate-limits/noaa-gov/noaa-gov-rate-limits/). 4 calls/s sustained for 100 min from one IP is not "typical use". Unverified either way; the per-thread backoff above is what turns a throttle into a storm.
- Run time: ~12 throttled calls per gauge x 0.25 s = 3 s per gauge site-wide (the gap binds before the six threads do). 25 gauges ~1.5 min (from 10); 250 ~13 min; 2,000 ~100 min; the 30-min cron breaks at ~500 gauges, the 150-min timeout at ~2,800. The next breaks after the patch: `fast_fill` USGS volume (~250 gauges, 1,000 calls/h), then gate 2 and gate 3 `truth_live` (sequential, one NWPS call per forecast point, `tools/truth_live.py:63,107`; SCALE-AUDIT i).
Verdict: the patch multiplies load by six without removing a call. The audit's step 1 is cheaper and removes load: cache the static per-gauge lookups (points, radar, stations: 3 of 8 NWS calls) in the record and fetch alerts once per state (`alerts/active?area=XX`, 51 calls). That alone takes the fast lane from ~12 to ~5 throttled calls per gauge at the old 1.5 s gap (~8 s per gauge, ~200 gauges per 30 min) with no threads, no new failure modes. If threads are still wanted afterwards: wrap the body of `one()` in `try/except` that logs and returns; on 429 set `GAP[0] = max(GAP[0], retry_after)` under `_lock` so every thread backs off; fix `need` to compare with the gauge's own reporting interval; one-string print. Effort: deletion 1 h; thread hardening 30 min.

### 4. Alerts are the most time-critical data and the slowest to reach the reader
Evidence: alerts are fetched only at collect (`collect.py:618-621`) and rendered static; the browser JS refreshes flow, stage, observed time and the age chip (`lib/page.py:161-165`, `AGE_JS`), never alerts. Worst-case alert age at build = cron delay (observed 22 to 27 min: run 39617735187 created 14:32 for the 14:05 cron; 39518293887 at 23:57 for 23:35) + 30 min + 12.6 min run, plus up to 54 min when a full run holds the concurrency group, plus a whole slot when a push cancels the pending schedule (run at 19:22 cancelled by the 19:25 push, gh). That is 1.5 to 2.5 h for a Tornado Watch; the page says "Unknown" only past 3 h (`lib/hero.py:239,264`). Live, Lees Ferry showed "2 active National Weather Service alerts Tornado Watch; Flood Watch" with "fetched Oct 21, 12:22 PM MST" at 12:34 MST; a cancellation at 12:30 would stay on the page until the next deploy.
Cheapest gain: one `fetch("https://api.weather.gov/alerts/active?point=lat,lon")` in the existing live script, updating the banner and the tile. The CSP already allows it: `templates/_headers` `connect-src ... https://api.weather.gov`. Then the fast lane can drop its per-gauge alerts call entirely (the server-side copy is only the no-JS fallback, refreshed by the state-level call). Effort: 1 h.

### 5. Freshness today, per source (worst case = source lag + cron delay 27 min + 30 min slot + 12.6 min run; +54 min when a full run is in the way)
| Source | Updates | Worst age on the live page today | Limit (CLAUDE.md:30) | Loss and cheapest gain |
|---|---|---|---|---|
| USGS flow/stage | 15 min (many gauges post hourly: "observed 1:00 PM MDT", live) | build: 60 min reading lag + 70 min pipeline = ~2.2 h (oldest 88 min at 19:27 today); browser: minutes (live JS) | 24 h "not reporting" | fine for JS readers; the baked value is what Google and curl see. Gain: deploy is already incremental (wrangler hashes), so the only lever is the run time (finding 3). |
| NWS alerts | minutes | 1.5 to 2.5 h | 3 h "Unknown" | finding 4 (client fetch), state-level server call |
| NWS obs | hourly | 1 h + 70 min = ~2.2 h | 3 h / 12 h (`lib/blocks3.py:239` uses 12) | acceptable; a 1 h chip reads "2 h old" |
| RFC rain | hourly | ~2.2 h ("estimate to 12:00 PM MDT" at 1:34 PM, live) | 6 h (`lib/blocks3.py:370`) | fine |
| NWS river forecast | 1 to 2 a day | 70 min + issue cadence | amber 24 h, hidden 72 h (`lib/blocks2.py:70`, `blocks3.py:269`) | fine; could move to the 6 h lane with no visible loss |
| NWM, WPC, hourly grid | 1 to 6 h | ~2 h | 12 h amber, 72 h | fine; 6 h lane candidates |
| sensors, 30-day, daily stats | 6 h lane, crons observed 1 to 5 h late (full-mode runs at 20 Oct 14:22, 19:21, 23:57, 21 Oct 08:43, 14:32 for crons at 03:20/09:20/15:20/21:20, gh) | 7 to 11 h | 30 d | fine |
Biggest loss: alerts (finding 4). Second: the 27-min cron drift, which no code can fix; a 15-min fast cron would halve the slot but doubles runs, so only after finding 3's deletion.

### 6. Push runs cancel the pending scheduled run (one pending slot per group)
Evidence (gh): the 19:22 scheduled run was cancelled at 19:25:53 when the "docs: scale ceilings" push landed while the 19:16 push run was still in progress; the 00:42 dispatch was cancelled the same way. `refresh.yml:18-20` `cancel-in-progress: false` keeps the running job but GitHub keeps only one pending run per group (secondary: github.com/boto/botocore/issues/3413 comment; official docs not found by search). Pushes run `mode=fast` (`refresh.yml:52-53`) so flow stays fresh, but a pending FULL run replaced by a docs push slips to the next 6 h cron (+ drift). Two of today's seven pushes were docs-only.
Cheapest fix: `on.push.paths-ignore: ["docs/**", "*.md"]` (two lines). Then decide full/fast from a `state/last_full.txt` age (> 6 h = full) instead of the cron string, so a lost or displaced full cron self-heals. Effort: 15 min.

### 7. Watchdog emails the owner for any hidden block and dies at ~400 gauges
Evidence: `tools/watchdog.py:34-35` fails on any `block_errors`; two failures today (15:14, 04:45, gh). `watchdog.yml:14` `timeout-minutes: 5` with `tools/truth_live.py` fetching every page and one NWPS call per forecast point sequentially (`truth_live.py:63-64,107`).
Cheapest fix: watchdog = status.json checks only (delete the truth step from `watchdog.yml`); keep truth in gate 3 on a sample (SCALE-AUDIT i). Effort: 10 min.

### 8. "Rollback" does not touch the live site
Evidence: `publish.py:8-14` renames local `dist/` and `dist_prev/`; nothing deploys. `docs/RUNBOOK.md:7` tells the owner Claude "rolls back if needed (`python -I publish.py --rollback`)". On CI there is no `dist_prev/`. The real rollback is Cloudflare Workers versions (`npx wrangler rollback`).
Cheapest fix: replace the RUNBOOK line; delete the `--rollback` branch. Effort: 5 min.

### 9. A fabricated date on the live Data sources page
Evidence: `lib/directory.py:270` `"Terms read " + (s.get("read_on") or "2026-10-16")`. Five quoted sources have no `read_on` (usgs, nws, natmap, nrcs, cpc; checked this session). Live `/data-sources/` prints "Terms read 2026-10-16" five times.
Cheapest fix: delete the fallback; print "Terms read: date not recorded" or fill `read_on` from the git log of `data/sources.json`. Effort: 10 min.

### 10. A past "Forecast high" reads as future
Evidence (live, Lees Ferry at 12:34 MST, page built 12:27 MST): "Forecast high 8.1 ft first reached Oct 21, 12:00 PM MST · NWS point CLFA3 0.2 ft above now". `lib/blocks3.py:264` keeps forecast points from `now - 1 h`, so a peak 27 min in the past is the "forecast high".
Cheapest fix: change `hours=1` to 0 in that filter. Effort: 5 min.

### 11. Correctness traps checked on three live pages: none of the serious ones found
Checked and clean: zones (Avondale "1:00 PM MDT", Lees Ferry "12:00 PM MST" (Arizona, no DST), Hudson "2:15 PM EDT"); units beside every number sampled ("285 cfs", "970 µS/cm", "30.19 inHg", "0.46 in"); no "None"/"undefined" (`check.py:12` bans them); "none" only as valid-empty sentences ("Thunderstorms: none in the National Weather Service forecast", "Last 20% rise: none in the last 7 days"); the Unknown tile exists for a missing alert answer (`lib/hero.py:243`); `status.json` `block_errors: []` and `failed_urls: []`; the gaps line names what is missing ("Not measured at this gauge: water temperature ..."); no `X-Robots-Tag` on the live page (the `_headers` noindex rules are stripped by `lib/indexing.py:38-52`); robots.txt allows all and names the sitemap; 404 returns 404; every USGS link is `waterdata.usgs.gov/monitoring-location/...` (301 to the new site, fine). Remaining nit: the baked age chip ("27 min old") is what no-JS readers and Google see; the JS rewrites it every minute (`lib/page.py:165`).

### 12. Smaller embarrassments
- `data/waves.csv` says 41 live, 16 of them without a cache file: `tools/release.py:26-27` marks rows live before collect succeeds. Mark live after the cache file exists.
- Dead code: `build.py:21-29` `live_urls` unused; `collect.py:115` `if True:`; `refresh.py:7-8` Windows scheduler PATH and `CREATE_NO_WINDOW` on a Linux runner; `lib/common.py:13-15` the owner's desktop paths hard-coded (`_PC_LEGACY`, `ENV_FILE`).
- Secrets: handled correctly (env on CI, `.env` locally, `check.py:259-264` scans the build). The AirNow key travels in a query string (`collect.py:845`); `get_text` errors (`collect.py:360-362`) do not include the URL, so it is never logged. Fine.
- Sitemap `lastmod` is today for every URL (gauge pages change every run; trust pages changed today); harmless, but it carries no signal.
- `tools/fetch_geo.py:27` uses the legacy `waterservices.usgs.gov/nwis/site` service; its decommission date was not verified here (search needed before the next bulk geo pull).
- `legacy/` 1.7 MB and `redirect-www/` are tracked; not checked further.

## Do this, in order
1. Track `data/waves.csv` (delete `.gitignore:13`); `default_sites()` reads its `live` rows; `build.py` fails when cached gauges < live rows. (finding 1)
2. `publish.py`: fetch the live page when `dist/` has no copy of a failed gauge. (finding 2)
3. Do NOT commit the thread patch. Instead: store `points`/`radar`/`stations` once per gauge in the record, alerts once per state. (finding 3)
4. Fix `fast_fill`'s `need` to the gauge's own reporting interval, or delete `fast_fill` and let the bulk call carry the point. (finding 3)
5. Add the alerts fetch to the live JS; then drop the per-gauge alerts call from the fast lane. (finding 4)
6. `refresh.yml`: `paths-ignore` docs and markdown on push; full/fast from the age of the last full run. (finding 6)
7. `watchdog.yml`: status checks only; truth on a sample in gate 3. (finding 7)
8. RUNBOOK rollback line -> `npx wrangler rollback`; delete `publish.py --rollback`. (finding 8)
9. Delete the `"2026-10-16"` fallback in `lib/directory.py:270`; fill `read_on`. (finding 9)
10. `lib/blocks3.py:264`: forecast points from now, not now minus 1 h. (finding 10)
Only after 3 and 4 hold at 250 gauges: consider threads (with the `try` in `one()`, the shared 429 backoff) or the per-state matrix job from SCALE-AUDIT.
