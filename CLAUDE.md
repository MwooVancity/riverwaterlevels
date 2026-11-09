# River Water Levels (riverwaterlevels.com)

Status: PLAN.md (history docs/plan-history.md). Calcscrape rules do not apply.

## HARD: truth first (owner 2026-11-02)
A false page is worse than none. Every fact proven on live agency data, else it does not ship or says Unknown. A feed down, cut short, out of area or parsed to nothing is Unknown, never safe. A wrong time, unit, place or gauge is the top defect. Our math says ours. A false-looking reading is held (future time) or marked (stuck, jump). Code: `lib/wx.py` `suspect`, `lib/world.py` `PROVED`, `tools/truth_world.py`.

## Scale (owner 2026-11-01, 11-03)
Every change states how it fails today and at 14,000 pages (calls, CPU, URL length, files, KV writes, run time, dead feed) and the breaking number. From 2026-11-20 Claude is on Pro: unattended work runs for weeks alone.

## Owner decisions (2026)
1. (11-01) Helpfulness decides page content; AdSense money decides build order.
2. (11-01) One standard page, block states and gates for every water, any country; a missing source shows "Not issued" or "Unknown", never blank or a lighter template. Summary tables are hubs.
3. (11-01) Ship test: a recent reading with unit, time, source ships, saying what is missing. Block only: no reading, no time, unit unknown, never reported, not a river or lake. (11-08) A NOAA tide station with predictions, no live level, ships; each tide labelled a prediction.
4. (11-08) No thin-content or duplicate gate: a different river, lake or searched place is its own page even with the same feed, gauge, numbers or text ("someone is looking for that specific page for a reason"). Similarity never blocks, holds or returns a page (`tools/coast_match.py`, release).
5. (11-01) World queue at full speed; never wait on traffic. Agency feed and reuse terms required. Never bulk-publish.
6. (11-03, 11-05) One ranking of every keyword (US, world; rivers, lakes, oceans; Keyword Planner): searches x ad rate (`RATE`, `tools/release.py`). Compete only with more sourced data; no info gain, no page.
7. (11-05) Never a source whose terms bar ads, commercial use or caching; no permission requests; another open official source, else link out. Takedowns and AdSense risk outrank any page (`check.py` `reuse_barred`).
8. Consent follows visitor location; every indexable page carries the same tags.

## Reader
At this water today, on a phone, 30 seconds: fish, paddle, swim, tube, wade, boat, camp, guide, live, drive, rescue. Answer in order: dangerous now, water like, normal, coming, today vs past. One static page per gauge, official data, English.

## HARD: drawing board first (owner 2026-11-08)
Before any build, and whenever asked "what's missing", answer each for THIS site: state (measured), owner, next action (PLAN.md "Drawing board"): 1 Demand (words, searches) 2 Intent (what wins today) 3 Better than #1 4 Trust 5 Links (who, by name) 6 Discovery (crawl, index) 7 Click 8 Experience (phone speed) 9 Proof (which number, when). "Not started", "nobody owns it" or "owner only, no plan" goes before ALL polish; an owner-only item gets a full plan, the owner only clicks.

## Page rules
- Nothing that helps ranking but not the reader (stuffing, doorway, padding).
- Phone download (third-party too) under 90 KB gzipped (`check.py`); cut the biggest, never river data.
- Line 0: every reliable public dataset a reader here could use, exact source and time; withhold only if wrong, misleading, padding or no mechanism.
- Non-US: own `data/sources.json` row, local unit + feet, agency low/high labels, no sailing verdict; a dead feed stales only its page.
- UI: one colour, white cards, one label and numeral style, unit beside number, data age once.
- Order, nothing collapsed on Now (except a tile's second and later lines behind "More": owner 2026-11-09, readers with ADHD or autism): alert banner; H1, gauge id, one age chip; tiles (flow, gage height, is-this-normal, 6 h change, NWS forecast or "Not issued", water temperature, rain 24 h, air, sunset); water now; level, flow and flood risk; forecast; how today compares; closed folds.
- No verdicts ("safe", "runnable", "fishable"); only labels and attributed source text. Delete a sentence no source can check.
- Every number has unit, time, Source line; a block shows only if its `data/sources.json` row is `quoted` or `owner-permission`.
- Block states: valid, valid-empty, unavailable ("Unknown", never "none"), stale (real age). `SAFETY_BLOCKS` failing keeps the old page; other blocks hide alone, named in the gaps line.
- Stale: flow 24 h "not reporting"; river forecast amber 24 h, hidden 72 h; weather obs 3/12 h; hourly forecast amber 12 h, hidden 72 h; alerts 3 h; rain 6 h; water temperature 24 h. Ignore NWS Test/Administrative alerts.
- New country: `PROVED` needs reading, time, a real live alert, unit, terms, water type seen live (England `UNKNOWN_UNTIL_PROVEN`: alerts Unknown + GOV.UK link). `COVER` answers each US block per country (have / none: reason / next; next = a `TODO` in the gaps line). `thin` holds only a new world page with no reading; `missing` a new gauge lacking its data; outages never pull live pages.

## HARD: internal links (owner 2026-11-08 "godlike")
Links come from data in code; a link exists because a reader here would tap it next.
1. Tree: home > country > state or region > hub > gauge page; breadcrumb on every water page (`crumb_ld`); hubs list all children; depth <= 4, no orphans (`check.py`).
2. Out, 3+ water pages, nearest first, distance shown, any country or kind (`lib/page.py` `nb_pick`, `lib/world.py` `near`); "Nearby" only within 100 km / 60 mi.
3. Same river: upstream and downstream named as such. Rivers, lakes and coasts list the nearest of each other kind, both ways.
4. In, 3+ from other water pages: a page few list is added to its nearest pages' lists, neediest first (`link_index` `REV_N`).
5. A page added or held rebuilds every page whose list changes, same run (`nb_urls` in `_built.json`). Only built, indexable pages are linked.
6. Anchor = the name a searcher types plus the reading, never "click here" or a bare id. Fixed list sizes (`check.py` BUDGET).
7. Proof: `check.py` prints "links census" (inbound/outbound min, median per kind) every run; copy it into PLAN.md Numbers after each batch. A new rule ships with its check.

## System rules
- No cloaking: the Worker never reads user agent, client hints, country, IP or bot score; JS only refreshes numbers.
- Visitors spend no API calls: the Worker calls out only from its */3 cron; phones read `/live/<site>.json`.
- HARD laptop (owner 2026-11-08 "downloading data at the absolute minimum"): collect, build, screenshots and speed tests run in the cloud; Claude reads their output, never re-downloads. Local only to debug one gauge, deleted that session; `cache/` + `dist*/` capped at 50 MB.
- `collect.py` is the only build-side network code; `build.py` reads `cache/` only. Keys: calcscrape `.env` only, never in pages, docs or output.
- Pages enter Google only via `tools/open_wave.py`.
- Cloudflare free, per account (shared with asmrregistry): 5 crons (4 used), 1,000 KV writes/day, 100k requests/day, 20,000 files, 10 ms CPU.
- Wrong or odd number on any page: follow `tools/source_fix.md` (fix in the feed reader, every edge case, fixture, live proof).
- A rule not in `gates.py`/`check.py` is a note; a new check ships a fixture (`--selftest`). What can heal never blocks; `tools/watchdog.py` heals hourly, alarms at most twice a day. Fix the cause, never loosen a check.
- Windows: no `&&` in PowerShell; `MSYS_NO_PATHCONV=1` in Git Bash; `python -I`.

## Commands and every change
- Session start: `python -I tools/watchdog.py`. Gates: `python -I gates.py` once per batch.
- Release: daily in the cloud (`refresh.yml`); by hand `tools/release.py N`, `tools/open_wave.py N --apply`, `tools/index_live.py`. Pull: `open_wave.py --pull <url>`.
- Change: commit explicit paths, push `check`, read "refresh OK", push main (= deploy), `tools/index_live.py` 0 mismatches, read one live page; proof into PLAN.md.
- New source: `data/sources.json` row (quoted terms, credit, `read_on`, evidence), `collect.py` `fetch_extras`, `tools/gen_cache_shape.py`, one `b_*` block, four states. Breakage: `docs/RUNBOOK.md`.
- Cloud runs: `gh workflow run dryrun.yml --ref check -f review="<site ids>"` (phone shots, artifact `review`) and `-f speed="<paths>"` (Lighthouse mobile, log lines "speed").
- HARD practice every kind (owner 2026-11-08 "don't miss a type"): the practice release (`-f release=true`, nightly) adds one queued page of each kind, gated or not (`tools/release.py --every-kind`), and collects world feeds. A new kind or feed joins the day it is added; a kind with none queued is named in PLAN.md.

## Reviews
- Phone shots once per template variant (`lib/pages.py` `variant`, `data/reviewed.json`) and new block type, before Google; a fresh reviewer reads `tools/review_brief.md`. A reviewed variant publishes on machine gates alone.
- A defect found twice becomes a `check.py` rule that batch; delete a gate with no catch in 10 runs. Checklist `tools/helpful_audit.md`.
- Gates hold only the wrong page (carried or sent back, US and world); only a whole-site fault stops a deploy. Fresh gate audit after a new kind or feed.
