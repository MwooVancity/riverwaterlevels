# River Water Levels (riverwaterlevels.com)

Status and next steps: PLAN.md. This folder is its own project; calcscrape rules do not apply.

## HARD: truth first (owner 2026-11-02)
A false page is worse than no page; anything untrue is unhelpful. Every fact on a page is proven on live data from the agency, never from memory, a search result or fake fixtures alone. No proof: it does not ship or it says Unknown. Silence never reads as safe: a feed down, cut short, outside its area or parsed to nothing is Unknown. A wrong time, unit, place or gauge is a defect of the highest rank. Our calculations say they are ours. A reading that looks false is held (future time) or marked (stuck, jump). `lib/wx.py` `suspect`, `lib/world.py` `PROVED`, `COVER`, `missing`, `tools/truth_world.py`.

## HARD: edge case at scale (owner 2026-11-01)
Every change states how it fails today AND at 14,000 pages (calls, CPU, URL length, file count, KV writes, run time, a dead feed) with the number where it breaks. From 2026-11-20 Claude drops from Max to Pro (owner 2026-11-03): code still changes, on a much smaller budget, so anything unattended must run for weeks without a session and growth must not wait on one.

## Owner decisions (2026-11-01)
1. Priorities: be helpful and make the owner the most money. Helpfulness decides what goes on a page; AdSense potential decides what gets built first.
2. One standard for every river or lake in any country: same gauge page, block states, gates. A source a country lacks shows "Not issued" or "Unknown", never a blank or a lighter template. Summary tables are hubs, never the standard page.
3. Ship test: does it answer the water level? A real recent reading with unit, time and source ships, marks or no marks, and says what is missing. Block only what is wrong: no reading, no time, unit unknown, never reported, near-duplicate, or not a river or lake.
4. World queue at full speed. Global rivers and non-US lakes are first priority for build time. Never wait on traffic numbers; Search Console reorders, never pauses. Official feed and reuse terms read from the agency stay required. Never bulk-publish.
5. HARD (owner 2026-11-03): "world" is the whole keyword list, US and non-US, one ranking; the only order is money: searches x country ad rate (`RATE` in `tools/release.py`, guesses from PLAN.md until AdSense reports ours). Lakes join the same ranking, US included. Owner 2026-11-05: rivers, lakes and oceans, whole world including the US; every keyword measured in Keyword Planner; compete with every site (Lakebrief, SNOFLO, USGS, NWS, NOAA, tide and surf sites, apps) on any water, only where our page holds more sourced data than the best competing page for that search; no info gain, no page.
6. Reviews are `/code-review high`, never ultra.
8. HARD (owner 2026-11-05): a source whose terms bar ads, commercial use or caching is never used; no permission requests. Use another official source with open terms, else show what is allowed and link out to the agency for the rest. Takedowns and AdSense risk outrank any page. Gate: `check.py` `reuse_barred` fails the build if a `data/sources.json` row marked `"ads"`, `"commercial"` or `"cache": "barred"` is quoted or owner-permission.
7. AdSense: site is under review ("Getting ready"), earns $0 until approved; sibling sites rejected for low value content. Consent message published since 2026-10-23; consent follows the visitor's location, so all indexable pages carry the same tags.

## Reader
A person at or near this river today, on a phone, with 30 seconds: to fish, paddle, swim, tube, wade, boat, camp, guide, or living, driving or rescuing beside it. The page answers, in order: is it dangerous now, what is the water like, is it normal, what is coming, how today compares. One static page per gauge, official government data only, English only.

## Choosing work
- Reject what helps ranking but not the reader: no gaming, stuffing, doorway or padding. Noindex never fixes a thin page.
- The US factory publishes 25 a day by itself; leave it alone. Build time goes to `data/world-queue.csv`.
- Count what a phone downloads, third-party scripts included; cut the biggest first, never river data. Page limit 90 KB gzipped (`check.py`).

## Page rules
- Line 0: every reliable public dataset a reader at this river could use goes on the page with exact source and time. Withhold only if wrong, misleading, padding or no mechanism.
- Non-US pages: own `data/sources.json` row, local unit plus feet, the agency's own low/high labels, no sailing verdict. A dead foreign feed stales only its page.
- Clean UI: one page colour, white cards, one label and numeral style, unit beside the number, one line under each number, data age said once.
- Order, nothing collapsed on Now: alert banner; H1, gauge id, one age chip; tiles (flow, gage height, is-this-normal, 6 h change, NWS forecast or "Not issued", water temperature, rain 24 h, air, sunset); water now; level, flow and flood risk; forecast; how today compares; closed folds. Right column = Area tab.
- Never "safe", "runnable", "fishable" or any verdict; no composed sentences except labels and attributed source text.
- Every number has a unit, a time and a Source line. A block shows only if its `data/sources.json` row is `quoted` or `owner-permission`.
- Four block states: valid, valid-empty (a sentence), unavailable ("Unknown", never "none"), stale (real age, marked old). `SAFETY_BLOCKS` failing keeps the previous page; other blocks hide alone and the gaps line names them.
- Stale limits: flow 24 h "not reporting"; river forecast amber 24 h, hidden 72 h; weather obs 3 h/12 h; hourly forecast amber 12 h, hidden 72 h; alerts 3 h; rain 6 h; water temperature tile under 24 h. Ignore NWS Test/Administrative alerts.
- A sentence no source can check is deleted. A derived line needing a third fix is deleted. Over 80% shared text, numbers included, fails the build: a gauge's own readings are its own content (owner 2026-11-02).
- New country: `PROVED` in `lib/world.py` needs reading, time, alerts, unit, terms and water type seen on live data; an alert proof needs a real live alert, never an empty list. England (`UNKNOWN_UNTIL_PROVEN`) may ship before it; its alerts then say Unknown with the GOV.UK link.
- World guarantee: `lib/world.py` `COVER` answers every US block per country (have, none: reason, next: source). A US block with no answer fails `check.py`; a next item is a to-do the gaps line names (`TODO`), never a cap. A new world page under the floor (`thin`) is held, never noindexed; a country whose every listed gauge is thin adds none (`room`). `missing` holds a new gauge whose data is not on its page; an outage never pulls a live page. `world_rules` is an allowlist of hosts and units.

## System rules
- No cloaking: the Worker never reads user agent, client hints, country, IP or bot score. JS only refreshes numbers.
- Visitors spend no API calls: the Worker calls outside only from its */3 cron; phones read `/live/<site>.json`.
- `collect.py` is the only build-side network code; `build.py` reads `cache/` only. Keys live in the calcscrape `.env`, never in pages, zips or docs; never print them.
- Refresh covers every gauge with a cache file, never a hard-coded list.
- One gauge per river first. New pages enter Google only via `tools/open_wave.py`.
- Cloudflare free limits are per account (shared with asmrregistry): 5 crons (4 used), 1,000 KV writes/day, 100k requests/day, 20,000 files, 10 ms CPU.
- A rule not in `gates.py`/`check.py` is a note. Every new check ships with a fixture (`check.py --selftest`).
- Gates block only what shows a reader something wrong; what can heal never blocks. `tools/watchdog.py` heals hourly and alarms the owner at most twice a day. Fix failures at the cause, never by loosening a check.
- Windows: no `&&` in PowerShell; `MSYS_NO_PATHCONV=1` in Git Bash; `python -I`.

## Commands
- Session start: `python -I tools/watchdog.py`.
- Build: `python -I build.py` (`--preview` shows uncleared blocks). Gates: `python -I gates.py` once per batch.
- Release runs daily in the cloud. By hand: `python -I tools/release.py N` (read the printed names), push, `python -I tools/open_wave.py N --apply`, push, `python -I tools/index_live.py`. Pull a page: `python -I tools/open_wave.py --pull <url>`.
- Deploy: only `refresh.yml` (push main, schedule, or `gh workflow run refresh.yml`), then `tools/index_live.py` (0 mismatches) and read one live page.
- World page on an existing feed: one row in `data/world-pages.json`; `gauge_pages` lists its gauges.
- New source: row in `data/sources.json` (quoted terms, credit, `read_on`, WebSearch evidence, nothing from memory), fetch in `collect.py` `fetch_extras`, `python -I tools/gen_cache_shape.py`, one `b_*` block with four states.

## Every change
1. One batch through script files; `python -I gates.py` once.
2. Commit explicit paths, push branch `check`; `dryrun.yml` runs itself. Read "refresh OK", then push main in a separate step. A push to main is a deploy.
3. Read the live page and status.json `world.gaps`/`thin` (a new rule can pass every fixture and still name live pages). Update PLAN.md with the proof.

Failures seen: laptop data differs from cloud data (only the dry run proves); one rule in several places (grep first, `truth_tests.py` included); a file only on the laptop (`git ls-files` every input); old data shown as now (render with the clock shifted 2 days).

## Reviews
- No signature gate: paperwork never blocks a deploy.
- Screenshots (owner 2026-11-05: no daily cap): every new page and every new block type is screenshotted at phone width before it opens to Google; name the token cost first. `python -I tools/hater_sample.py`, `node tools/hater_shots.mjs [sites]`, then a reviewer who did not build it reads `tools/review_brief.md`.
- A defect found twice becomes a `check.py` rule that batch. Delete a gate with no real catch in 10 runs.
- Helpfulness checklist: `tools/helpful_audit.md` (A-Q); each batch checks the categories it touches.

## Owner alone
Publisher name and contact email; pages opened to Google beyond the daily 25; ads and consent; Search Console; source-permission visits and keys; domain renewal; Cloudflare plan; outside uptime monitor; cutting any block. Breakage: `docs/RUNBOOK.md`. Corrections: `docs/CORRECTIONS.md`.

## Files
Blocks `lib/render.py`, `lib/blocks2.py`, `lib/blocks3.py`, `lib/ui.py`; pages `lib/page.py`, `lib/directory.py`; indexing `lib/indexing.py` + `data/index-allow.json`; skin `templates/site.css` ("ONE SYSTEM" only); edge `worker/index.js`.
