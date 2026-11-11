# River Water Levels (riverwaterlevels.com)

Status: PLAN.md (history docs/plan-history.md). Calcscrape rules do not apply. Where a rule names code, the code is the rule.

## HARD, ABOVE ALL: the three tests (owner 2026-11-09)
Only (1) maximum helpfulness to the reader at this water, (2) information gain over what ranks, (3) passing Google's helpful-content review (HCU). Every change, rule, gate, block and link is judged on all three before build and before ship; fail one = not built, or deleted. One line per change: "Helpful / Gain / HCU". Nothing for a count or ranking trick: no forced links, no padding, no block for Google but not the reader. These win over every rule below.

## HARD: truth first (owner 2026-11-02)
A false page is worse than none. Every fact proven on live agency data, else it does not ship or says Unknown. A feed down, cut short, out of area or parsed to nothing is Unknown, never safe. A wrong time, unit, place or gauge is the top defect. Our math says ours. A false-looking reading is held (future time) or marked (stuck, jump): `lib/wx.py` `suspect`, `lib/world.py` `PROVED`, `tools/truth_world.py`.

## Scale (owner 2026-11-01, 11-03)
A change to collect, build, the Worker or a scheduled job states how it fails today and at 14,000 pages (calls, CPU, URL length, files, KV writes, run time, dead feed) and the breaking number. From 2026-11-20 Claude is on Pro: unattended work runs for weeks alone.

## Owner decisions (2026)
1. (11-01) Helpfulness decides page content; AdSense money decides build order, only among items that pass the three tests.
2. (11-01) One standard page, block states and gates for every water, any country; a missing source shows "Not issued" or "Unknown", never blank or a lighter template. Summary tables are hubs.
3. (11-01) Ship test: a recent reading with unit, time, source ships, saying what is missing. Block only: no reading, no time, unit unknown, never reported, not a river or lake. (11-08) A NOAA tide station with predictions, no live level, ships; each tide labelled a prediction.
4. (11-08, narrowed 11-09) A different river, lake or searched place is its own page even when it shares a feed, gauge or numbers; similarity alone never blocks it. HCU limit: it carries something of its own (name and distance to the gauge, own nearby water, weather point or access); a name-swap copy is a doorway page, not built (`check.py` doorway census).
5. (11-01) World queue at full speed; never wait on traffic. Agency feed and reuse terms required. Never bulk-publish.
6. (11-03, 11-05) One ranking of every keyword (US, world; rivers, lakes, oceans; Keyword Planner): searches x ad rate (`tools/release.py` `RATE`). Compete only with more sourced data; no info gain, no page.
7. (11-05) Never a source whose terms bar ads, commercial use or caching; no permission requests; another open official source, else link out. Takedowns and AdSense risk outrank any page (`check.py` `reuse_barred`).
8. Consent follows visitor location; every indexable page carries the same tags.

## Reader
At this water today, on a phone, 30 seconds: fish, paddle, swim, tube, wade, boat, camp, guide, live, drive, rescue. Answer in order: dangerous now, water like, normal, coming, today vs past. One static page per gauge, official data, English.

## HARD: drawing board first (owner 2026-11-08)
Before any build, and on "what's missing", answer for THIS site: state (measured), owner, next action (PLAN.md "Drawing board"): 1 Demand 2 Intent 3 Better than #1 4 Trust 5 Links (who, by name) 6 Discovery 7 Click 8 Experience 9 Proof. "Not started", "nobody owns it" or "owner only, no plan" goes before ALL polish; an owner-only item gets a full plan, the owner only clicks.

## HARD: readable at a glance (owner 2026-11-09)
A page fails if a person can't say what the river is doing after 5 seconds on a phone. Reference: the Weather Channel / Apple Weather, not agency pages. First screen: place, one plain status sentence, the number. Each block: one answer sentence first, the table is proof. Table rules: `check.py` `wide_tables`, `colour_contrast`, first-screen rule; tools/source_fix.md "Tables a person can read". A new layout ships after one 5-second test by a person who is not Claude.

## Page rules
- Nothing that helps ranking but not the reader. No verdicts ("safe", "runnable", "fishable"): labels and attributed source text only (`check.py` BANNED); delete a sentence no source can check.
- Weight: `check.py` MAX_GZ; ads and Analytics load after the page is readable; cut the biggest, never river data.
- Line 0: every reliable public dataset a reader here could use, exact source and time; withhold only if wrong, misleading, padding or no mechanism.
- Every number has unit, time, Source line; a block shows only if its `data/sources.json` row is `quoted` or `owner-permission`. States: valid, valid-empty, unavailable ("Unknown", never "none"), stale (real age; limits `lib/core.py` STALE_H/HIDE_H, ignored alerts IGNORED_ALERTS). `SAFETY_BLOCKS` failing keeps the old page; other blocks hide alone, named in the gaps line.
- Non-US: own `data/sources.json` row, local unit + feet, agency low/high labels, no sailing verdict; a dead feed stales only its page. New country: `lib/world.py` `PROVED`, `COVER` (England `UNKNOWN_UNTIL_PROVEN`); `thin`/`missing` hold only new pages; outages never pull live pages.
- UI: one colour, white cards, one label and numeral style, unit beside number, data age once. Order, nothing collapsed on Now except a tile's later lines behind "More" (owner 2026-11-09, readers with ADHD or autism): alert banner; H1, gauge id, age chip; tiles (flow, gage height, is-this-normal, 6 h change, NWS forecast or "Not issued", water temperature, rain 24 h, air, sunset); water now; level, flow and flood risk; forecast; how today compares; closed folds.

## HARD: internal links (owner 2026-11-08, 11-09 "I don't want internal links if it's forced")
A link exists only because a reader here would tap it next; links come from data in code, never to reach a count. Tree home > country > region > hub > page, breadcrumb (`crumb_ld`), hubs list all children, depth <= 4, no orphans. Out: up to 5 other waters of any kind within `lib/page.py` NEAR_MI / `lib/world.py` NEAR_KM, same watershed first, distance shown, none nearby = no list; same river named upstream/downstream; nearest of each other kind both ways; no reverse lists. Only built, indexable pages are linked; a changed list rebuilds its pages the same run (`nb_urls`). Anchor = the searched name plus the reading. Sizes: `check.py` BUDGET; the links census is information, never a target. A new rule ships with its check.

## System rules
- No cloaking: the Worker never reads user agent, client hints, country, IP or bot score; JS only refreshes numbers. Visitors spend no API calls: the Worker calls out only from its */3 cron; phones read `/live/<site>.json`.
- HARD laptop (owner 2026-11-08): collect, build, screenshots and speed tests run in the cloud; Claude reads their output. Local only to debug one gauge, deleted that session; `cache/` + `dist*/` capped at 50 MB.
- `collect.py` is the only build-side network code; `build.py` reads `cache/` only. Keys: calcscrape `.env`, GitHub secret `GSC_KEY_JSON`; never in pages, docs, commits or output.
- Pages enter Google only via `tools/open_wave.py`.
- Cloudflare free, per account (shared with asmrregistry): 5 crons (4 used), 1,000 KV writes/day, 100k requests/day, 20,000 files, 10 ms CPU.
- Wrong or odd number on any page: `tools/source_fix.md`.
- Google (owner 2026-11-11): `check.py` `GOOGLE` maps every Google spam policy, helpful-content question and structured-data rule to the check that enforces it, or says why none can; `google_rules` runs on every page. A new Google rule gets a row and a check the day it is read; no separate Google doc.
- A rule not in `gates.py`/`check.py` is a note; a new check ships a fixture (`--selftest`). What can heal never blocks; `tools/watchdog.py` heals hourly. No alarms or emails; the owner reads the dashboard daily. Fix the cause, never loosen a check.
- Windows: no `&&` in PowerShell; `MSYS_NO_PATHCONV=1` in Git Bash; `python -I`.

## Commands and every change
- Session start: `python -I tools/watchdog.py`. Gates: `python -I gates.py` once per batch.
- Owner dashboard (owner 2026-11-10): the watchdog run Summary tab (`tools/ops_summary.py`); the repo is public, so the dashboard shows no secrets and nothing private.
- Release: daily in the cloud (`refresh.yml`); by hand `tools/release.py N`, `tools/open_wave.py N --apply`; pull `open_wave.py --pull <url>`. `tools/index_live.py` runs only by hand (nothing in the cloud runs it).
- Change: batch finished items into one push to `check`, start the next at once, never wait on the run. A passing run promotes itself to main and deploys (dryrun.yml). On a run's notice, read the live page and run index_live; proof into PLAN.md. The session merges conflicts with main.
- PLAN.md markers: DONE, LIVE, CLOSED, DECIDED, and WAITING <date> or OWNER for an item nothing can move today; the Stop hook pushes a session on while any other item is open.
- New source: `data/sources.json` row (quoted terms, credit, `read_on`, evidence), `collect.py` `fetch_extras`, `tools/gen_cache_shape.py`, one `b_*` block, four states. Breakage: `docs/RUNBOOK.md`.
- Cloud runs: `gh workflow run dryrun.yml --ref check -f review="<site ids>"` (phone shots) or `-f speed="<paths>"` (Lighthouse mobile).
- HARD practice every kind (owner 2026-11-08): the nightly practice release (`-f release=true`, `tools/release.py --every-kind`) adds one queued page of each kind and collects world feeds; a new kind or feed joins the day it is added; a kind with none queued is named in PLAN.md.

## Reviews
- Phone shots once per template variant (`lib/pages.py` `variant`, `data/reviewed.json`) and new block type, before Google (reviewer brief `tools/review_brief.md`); a reviewed variant publishes on machine gates alone.
- A defect found twice becomes a `check.py` rule that batch; delete a gate with no catch in 10 runs (`tools/helpful_audit.md`). Gates hold only the wrong page; only a whole-site fault stops a deploy. Fresh gate audit after a new kind or feed.
