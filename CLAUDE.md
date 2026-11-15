# River Water Levels (riverwaterlevels.com)

Status: PLAN.md (history docs/plan-history.md). Calcscrape rules do not apply. Where a rule names code, the code is the rule.

## HARD, FIRST: the reader (owner 2026-11-14, said twice)
A swimmer, kayaker, sailor, surfer, angler, tuber or boater going out on this water for fun today, on a phone, 30 seconds. Water fun first on every template: a live alert, then water now, weather, level and flow, getting on the water, forecast, past years. Flood material only when near, alerted, forecast or unknown (`impacts_near`), else in the bottom fold. Judge every page as that person, never as a hydrologist or flood planner. One static page per gauge, official data, English.

## HARD, ABOVE ALL: the three tests (owner 2026-11-09)
(1) Maximum helpfulness to that reader, (2) information gain over what ranks, (3) Google's helpful-content review (HCU). Every change, rule, gate, block and link is judged on all three before build and ship; fail one = not built, or deleted. One line per change: "Helpful / Gain / HCU". Nothing for a count or ranking trick: no forced links, no padding, no block for Google but not the reader.

## HARD: truth first (owner 2026-11-02)
A false page is worse than none. Every fact proven on live agency data, else it does not ship or says Unknown. A feed down, cut short, out of area or parsed to nothing is Unknown, never safe. A wrong time, unit, place or gauge is the top defect. Our math says ours. A false-looking reading is held (future time) or marked (stuck, jump): `lib/wx.py` `suspect`, `lib/world.py` `PROVED`, `tools/truth_world.py`.

## HARD: readable at a glance (owner 2026-11-09)
After 5 seconds on a phone a person can say what the water is doing (reference: Weather Channel / Apple Weather). First screen: place, one plain status sentence, the number. Each block: an answer sentence first, the table is proof (`check.py` `wide_tables`, `colour_contrast`). A new layout ships after Claude's 5-second test on the cloud phone shots; never asked of the owner.

## HARD: drawing board first (owner 2026-11-08)
Before any build and on "what's missing", state for this site (measured), owner, next action: 1 Demand 2 Intent 3 Better than #1 4 Trust 5 Links (who, by name) 6 Discovery 7 Click 8 Experience 9 Proof. "Not started" or "nobody owns it" goes before all polish.

## HARD: argue (owner 2026-11-14 "you agree too much... I say dumb shit on purpose")
Every owner request is tested against the reader, the three tests, truth and the data before acting. If it is wrong, half-right or costs more than it moves, say so first with the evidence and the better option, then do the better one; agreeing to be agreeable is a failure.

## Owner decisions (2026)
1. (11-01) Helpfulness decides content; AdSense money decides build order among items that pass the three tests.
2. (11-01) One standard page and gates for every water and country; a missing source says "Not issued" or "Unknown", never blank. Summary tables are hubs.
3. (11-01) Ships: a recent reading with unit, time, source, saying what is missing. Held: no reading, no time, unit unknown, never reported, not a river or lake. (11-08) A tide station with predictions only ships, each tide labelled a prediction.
4. (11-08, 11-09) A different river, lake or place is its own page even on a shared gauge, if it carries something of its own (name and distance, own nearby water, weather point, access); a name swap is a doorway page (`check.py` doorway census).
5. (11-01) World queue at full speed, never waiting on traffic; agency feed and reuse terms required; never bulk-publish.
6. (11-03, 11-05) One keyword ranking (Keyword Planner): searches x ad rate (`tools/release.py` `RATE`). No information gain, no page.
7. (11-05) Never a source whose terms bar ads, commercial use or caching; no permission requests; else link out (`check.py` `reuse_barred`).
8. Consent follows visitor location; every indexable page carries the same tags.

## Page rules
- No verdicts ("safe", "runnable", "fishable"): labels and attributed source text only (`check.py` BANNED); delete a sentence no source can check.
- Weight: `check.py` MAX_GZ; ads and Analytics load after the page is readable; cut the biggest, never river data.
- Every reliable public dataset a reader here could use, with source and time; withhold only if wrong, misleading, padding or no mechanism.
- Every number has unit, time, Source line; a block shows only if its `data/sources.json` row is `quoted` or `owner-permission`. States: valid, valid-empty, unavailable ("Unknown"), stale (real age; `lib/core.py` STALE_H/HIDE_H). `SAFETY_BLOCKS` failing keeps the old page; other blocks hide alone, named in the gaps line.
- Non-US: own sources row, local unit + feet, agency labels; a dead feed stales only its page. New country: `lib/world.py` `PROVED`, `COVER`; outages never pull live pages.
- UI: one colour, white cards, agency status colours from `lib/common.py` OFFICIAL on a border, bar or swatch with the word beside; a flood warning reads bold red (`lib/core.py` FLOOD_RED; advisories and watches keep agency colours) and every alert links the official NWS page (owner 11-14). Nothing collapsed on Now (readers with ADHD or autism); tiles: flow, gage height, is-this-normal, 6 h change, NWS forecast or "Not issued", water temperature, rain 24 h, air, sunset.

## HARD: internal links (owner 2026-11-08, 11-09)
A link exists only because this reader would tap it next, from data in code, never for a count. Tree home > country > region > hub > page, breadcrumb (`crumb_ld`), depth <= 4, no orphans. Out: up to 5 waters within `lib/page.py` NEAR_MI / `lib/world.py` NEAR_KM, same watershed first, distance shown; same river up/downstream; only built, indexable pages (`nb_urls`). Anchor = the searched name plus the reading. Sizes: `check.py` BUDGET.

## System rules
- No cloaking: the Worker never reads user agent, client hints, country, IP or bot score; JS only refreshes numbers. Visitors spend no API calls of ours: the Worker calls out only from its */3 cron; phones read `/live/<site>.json`.
- HARD laptop (11-08): collect, build, screenshots and speed tests run in the cloud. Local only to debug one gauge, deleted that session; `cache/` + `dist*/` capped at 50 MB.
- `collect.py` is the only build-side network code; `build.py` reads `cache/`. Keys: calcscrape `.env`, secret `GSC_KEY_JSON`; never in pages, docs, commits or output. Repo is public.
- Scale: a change to collect, build, the Worker or a job states how it fails today and at 14,000 pages (calls, CPU, URL length, files, KV writes, run time) and the breaking number. From 2026-11-20 Claude is on Pro: unattended work runs for weeks alone.
- Cloudflare free, per account (shared with asmrregistry): 5 crons (4 used), 1,000 KV writes/day, 100k requests/day, 20,000 files, 10 ms CPU.
- Google: `check.py` `GOOGLE` maps every Google policy and HCU question to its check; a new Google rule gets a row and a check the day it is read.
- A rule not in `gates.py`/`check.py` is a note; a new check ships a fixture (`--selftest`). What can heal never blocks (`tools/watchdog.py` hourly). No alarms or emails. Fix the cause, never loosen a check. Wrong number: `tools/source_fix.md`.
- Windows: no `&&` in PowerShell; `MSYS_NO_PATHCONV=1` in Git Bash; `python -I`.

## Commands and every change
- Session start: `python -I tools/watchdog.py`. Gates once per batch, in the cloud. Dashboard: watchdog run Summary tab (`tools/ops_summary.py`), no secrets.
- Pages enter Google only via `tools/open_wave.py`. Release daily in the cloud (`refresh.yml`); by hand `tools/release.py N`, `open_wave.py N --apply`. `tools/index_live.py` by hand only.
- Change: batch into one push to `check`; a passing run promotes to main and deploys (dryrun.yml). On its notice read the live page; proof into PLAN.md.
- PLAN.md markers: DONE, LIVE, CLOSED, DECIDED, WAITING <date>, OWNER; finished items move to docs/plan-history.md; the Stop hook pushes on while any other item is open.
- New source: `data/sources.json` row (quoted terms, credit, `read_on`), `collect.py` `fetch_extras`, `tools/gen_cache_shape.py`, one `b_*` block, four states. Breakage: `docs/RUNBOOK.md`.
- Cloud runs: `gh workflow run dryrun.yml --ref check -f review="<ids or paths>"` (phone shots) or `-f speed="<paths>"`. Nightly practice release adds one queued page of each kind (`tools/release.py --every-kind`).

## Reviews
- HARD (11-14): no code reaches `check` unreviewed. `tools/review_gate.py` refuses a push while code changed since `data/last-review`; run `/code-review medium`, fix, then commit HEAD there. A mark without a review is lying.
- Phone shots once per template variant (`lib/pages.py` `variant`, `data/reviewed.json`) and new block type, before Google (`tools/review_brief.md`).
- A defect found twice becomes a `check.py` rule; delete a gate with no catch in 10 runs. Gates hold only the wrong page.
