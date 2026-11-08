# River Water Levels (riverwaterlevels.com)

Status: PLAN.md (history docs/plan-history.md). Own project: calcscrape rules do not apply; global CLAUDE.md not repeated.

## HARD: truth first (owner 2026-11-02)
A false page is worse than none. Every fact is proven on live agency data (never memory, search or fixtures alone), else it does not ship or says Unknown. A feed down, cut short, out of area or parsed to nothing is Unknown, never safe. A wrong time, unit, place or gauge is the top defect. Our math says ours. A false-looking reading is held (future time) or marked (stuck, jump). Code: `lib/wx.py` `suspect`, `lib/world.py` `PROVED`, `tools/truth_world.py`.

## Scale (owner 2026-11-01, 2026-11-03)
Every change states how it fails today and at 14,000 pages (calls, CPU, URL length, files, KV writes, run time, dead feed) and the breaking number. From 2026-11-20 Claude is on Pro: unattended work runs for weeks alone.

## Owner decisions (2026)
1. (11-01) Helpfulness decides page content; AdSense money decides build order.
2. (11-01) One standard page, block states and gates for every water, any country; a missing source shows "Not issued" or "Unknown", never blank or a lighter template. Summary tables are hubs.
3. (11-01) Ship test: a recent reading with unit, time, source ships, saying what is missing. Block only: no reading, no time, unit unknown, never reported, not a river or lake. (11-08) A NOAA tide station with predictions, no live level, ships; each tide labelled a prediction. (11-08) No thin-content or duplicate gate: a different river, lake or place is its own page even with the same gauge, numbers or text ("someone is looking for that specific page for a reason").
4. (11-01) World queue at full speed; never wait on traffic (Search Console reorders). Agency feed and reuse terms required. Never bulk-publish.
5. (11-03, 11-05) One ranking of every keyword (US, world; rivers, lakes, oceans; Keyword Planner): searches x ad rate (`RATE`, `tools/release.py`). Compete with any site only with more sourced data; no info gain, no page.
6. (11-05) Never a source whose terms bar ads, commercial use or caching; no permission requests; use another open official source, else link out. Takedowns and AdSense risk outrank any page. Gate `check.py` `reuse_barred`.
7. (11-08) A searched place gets its page even with the same feed, gauge or near-same text as another ("They're looking for that specific page still"). Similarity never blocks, holds or returns a page; one page per searched place (`tools/coast_match.py`, release).
8. Consent follows visitor location, so every indexable page carries the same tags.

## Reader
At this water today, on a phone, 30 seconds: fish, paddle, swim, tube, wade, boat, camp, guide, live, drive, rescue. Answer in order: dangerous now, water like, normal, coming, today vs past. One static page per gauge, official government data, English.

## Page rules
- Nothing that helps ranking but not the reader (stuffing, doorway, padding). The US factory publishes 25 a day alone; build time goes to `data/world-queue.csv`.
- Count all a phone downloads, third-party too; cut the biggest, never river data. 90 KB gzipped (`check.py`).
- Line 0: every reliable public dataset a reader here could use, exact source and time; withhold only if wrong, misleading, padding or no mechanism.
- Non-US: own `data/sources.json` row, local unit + feet, agency low/high labels, no sailing verdict; a dead feed stales only its page.
- UI: one colour, white cards, one label and numeral style, unit beside number, one line under it, data age once.
- Order, nothing collapsed on Now: alert banner; H1, gauge id, one age chip; tiles (flow, gage height, is-this-normal, 6 h change, NWS forecast or "Not issued", water temperature, rain 24 h, air, sunset); water now; level, flow and flood risk; forecast; how today compares; closed folds. Right column = Area tab.
- No verdicts ("safe", "runnable", "fishable"); no composed sentences but labels and attributed source text. Delete a sentence no source can check, or a derived line needing a third fix.
- Every number has unit, time, Source line; a block shows only if its `data/sources.json` row is `quoted` or `owner-permission`.
- Block states: valid, valid-empty (a sentence), unavailable ("Unknown", never "none"), stale (real age, marked). `SAFETY_BLOCKS` failing keeps the old page; other blocks hide alone, named in the gaps line.
- Stale: flow 24 h "not reporting"; river forecast amber 24 h, hidden 72 h; weather obs 3 h/12 h; hourly forecast amber 12 h, hidden 72 h; alerts 3 h; rain 6 h; water temperature tile 24 h. Ignore NWS Test/Administrative alerts.
- New country: `PROVED` needs reading, time, alerts (a real live alert), unit, terms, water type seen live. England (`UNKNOWN_UNTIL_PROVEN`) ships first, alerts Unknown + GOV.UK link.
- `COVER` answers each US block per country (have / none: reason / next); none fails `check.py`; next = a `TODO` in the gaps line, never a cap. `thin` holds only a new world page with no reading (time, unit); `missing` holds a new gauge lacking its data; outages never pull live pages. `world_rules` allowlists hosts, units.

## HARD: internal links (owner 2026-11-08: "godlike", written here so it is followed)
Every page kind, block and generator obeys these; links come from data in code, never hand-wired. A link exists because a reader here would tap it next.
1. Tree: home > country > state or region > river, lake or coast hub > gauge page. Every water page names its parents in the breadcrumb (BreadcrumbList, `crumb_ld`); every hub lists all its children; no page over 4 clicks from home, no orphans (`check.py`).
2. Out, 3+ water pages each, nearest first, distance shown, any country or water type (`lib/world.py` `near`, `lib/page.py` nearby_gauges); "Nearby" only when all are within 100 km.
3. Same river, 2+ pages: upstream and downstream named as such (what is coming down). Rivers, lakes and coasts link their nearest of each other kind both ways (a tidal river and its tide station; a lake and its inflow).
4. In, 3+ from other water pages each: a page nobody lists nearest (remote, last of its region) is added to its nearest pages' lists. Inbound is measured, not only outbound.
5. Adding or holding a page rebuilds its hub and the pages whose lists change, in the same run (a "only what changed" build must not leave stale lists). Only built, indexable pages are linked; a held, pulled or noindex page never is.
6. Anchor = the name a searcher types ("Mission Bay tides", "Snake River at Heise"), plus the reading beside it, never "click here" or a bare id. Each list has a fixed size, so links per page never grow with the site (`check.py` BUDGET).
7. Proof: after each batch, census the live site (orphans, depth, inbound and outbound min/median per kind) into PLAN.md Numbers. `check.py` `few_neighbours` warns on rule 2; a new rule ships with its check.

## System rules
- No cloaking: the Worker never reads user agent, client hints, country, IP or bot score; JS only refreshes numbers.
- Visitors spend no API calls: the Worker calls out only from its */3 cron; phones read `/live/<site>.json`.
- HARD laptop (owner 2026-11-08 "downloading data at the absolute minimum"): collecting, building and screenshotting run in the cloud (dry run on `check`); Claude reads their output, never re-downloads it. Local only to debug one gauge, files deleted that session; `cache/` + `dist*/` capped at 50 MB, cleared when over.
- `collect.py` is the only build-side network code; `build.py` reads `cache/` only. Keys: calcscrape `.env` only, never in pages, zips, docs or output.
- Refresh covers every gauge with a cache file, no hard-coded list. One gauge per river first. Pages enter Google only via `tools/open_wave.py`.
- Cloudflare free, per account (shared with asmrregistry): 5 crons (4 used), 1,000 KV writes/day, 100k requests/day, 20,000 files, 10 ms CPU.
- A rule not in `gates.py`/`check.py` is a note; a new check ships a fixture (`check.py --selftest`). What can heal never blocks; `tools/watchdog.py` heals hourly, alarms at most twice a day. Fix the cause, never loosen a check.
- Windows: no `&&` in PowerShell; `MSYS_NO_PATHCONV=1` in Git Bash; `python -I`.

## Commands
- Session start: `python -I tools/watchdog.py`.
- Build: `python -I build.py` (`--preview` shows uncleared blocks). Gates: `python -I gates.py` once per batch.
- Release: daily in the cloud; by hand `python -I tools/release.py N` (read the names), push, `python -I tools/open_wave.py N --apply`, push, `python -I tools/index_live.py`. Pull: `python -I tools/open_wave.py --pull <url>`.
- Deploy: only `refresh.yml` (push main, schedule, `gh workflow run refresh.yml`), then `tools/index_live.py` (0 mismatches), read one live page.
- World page on a known feed: a `data/world-pages.json` row; `gauge_pages` lists its gauges.
- New source: `data/sources.json` row (quoted terms, credit, `read_on`, WebSearch evidence), `collect.py` `fetch_extras`, `python -I tools/gen_cache_shape.py`, one `b_*` block, four states.

## Every change
1. Commit explicit paths, push branch `check`; `dryrun.yml` runs. Read "refresh OK", then push main separately (a deploy).
2. Read the live page and status.json `world.gaps`/`thin`; PLAN.md gets the proof.
Seen: laptop data differs from cloud (only the dry run proves); one rule in several places (grep, `truth_tests.py` too); a laptop-only file (`git ls-files`); old data as now (clock +2 days).

## Reviews
- No signature gate. Screenshots (owner 2026-11-05: no cap): new pages and block types at phone width before Google, cost named: `python -I tools/hater_sample.py`, `node tools/hater_shots.mjs [sites]`, a reviewer who did not build it reads `tools/review_brief.md`.
- A defect found twice becomes a `check.py` rule that batch; delete a gate with no catch in 10 runs. Checklist `tools/helpful_audit.md` (A-Q).

## Files
Owner-only items: PLAN.md. Breakage `docs/RUNBOOK.md`, corrections `docs/CORRECTIONS.md`. Blocks `lib/render.py`, `lib/blocks2.py`, `lib/blocks3.py`, `lib/ui.py`; pages `lib/page.py`, `lib/directory.py`; indexing `lib/indexing.py` + `data/index-allow.json`; skin `templates/site.css` ("ONE SYSTEM" only); edge `worker/index.js`.
