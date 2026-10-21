# River Water Levels (riverwaterlevels.com)

One static page per USGS river gauge. Government data only (USGS, NOAA/NWS, USDA, EPA). Ad-supported later. The owner is a non-coder and never runs commands: do the work, short plain replies, no "Next:" line, decide defaults yourself. This folder is its own project; the car-repair site's rules do not apply here.

## The procedure (HARD, owner 2026-10-21: "it's just APIs on pages, it shouldn't keep fucking up")
Every change, no exceptions:
1. Say in one line what will change. Nothing that runs gates, a reviewer or a deploy starts until the owner says go.
2. Change code through a script file (Write, then run), never a shell heredoc. One batch of edits, then one check run.
3. Build. Screenshot one page (`PICK=<slug> node <rand_shot>` or the review tools). Look at it before anything else runs.
4. `python -I gate.py` once. A failure is fixed at its cause, never by loosening or deleting the check. A third failure on one check means stop and report the cause.
5. One reviewer round on the template hash (docs/REVIEW-1ST.md; resume the same agent to re-verify). Sign.
6. Commit with explicit paths. A push is a deploy. Read the live page. "Done" means read live this turn.
7. One line in docs/OPEN-ITEMS.md's done log with the proof.
Adding gauges: `python -I tools/release.py N` prints the full gauge names; read them (wrong place or wrong gauge: fix the list first); it collects and builds the pages held; one reviewer round; sign the pages; push; `tools/open_wave.py N --apply`; push; `tools/index_live.py`.
A rule without a check is a note. A check not in `gates.py` does not exist.

## Reader (Line 0, owner 2026-10-20: "every data block for every water activity, in priority for the user")
A person at or near this river today, on a phone, about to fish, paddle, swim, tube, wade, boat, row, dive, pan, hunt, camp, guide, or who lives, drives or rescues beside it. Flood watchers are one reader among twenty, not the first. Every page answers, in this order: is it dangerous now, what is the water like, is it normal, what is coming, how today compares. Correct is necessary, never enough: the page must be understood in seconds and look made by a person (design review 2026-10-21 against Lakebrief: one page colour, white 12 px cards, one label style, one numeral face, unit beside the number, one line under each number, the data age said once).

## Every gauge page, in this order, nothing collapsed on the Now tab
1. Alert banner (NWS, live) when one is active.
2. H1, gauge id, one age chip ("56 min old"), one observed time. Age is stated once.
3. Tiles: latest flow, gage height (sparklines), is-this-normal (percentile bar, words), 6 h change, NWS forecast high or "Not issued", water temperature (or the nearest same-river sensor, or "not measured"), rain 24 h, air (temperature, wind, gusts), sunset (sunrise, last light, moon). Every tile: label, number, unit, one line, time.
4. What the water is like now: sensors (temperature, turbidity, dissolved oxygen, pH, conductance, salinity, velocity, nitrate; USGS qualifiers such as Ice printed), tides on tidal reaches (detected: flow cycles within the day, `oscillating()`), hourly weather with thunder and humidity, rain here and at nearby stations.
5. Level, flow and flood risk: 7-day chart with a range switch (`merge_charts` folds 30 days, 12 months and earlier years into it), gage height with the flood-stage ladder, NWS impact statements, rate of change.
6. Forecast on every river: NWS river forecast or "Not issued", National Water Model guidance, rain outlooks.
7. How today compares: month, year, same dates in earlier years, record, water temperature by month, snowpack.
8. Closed folds: flood record, daily values and rating, watershed and land. Right column (the "Area" phone tab): upstream and downstream, nearby, NWS point, map, official links, about. Phone tabs Now / Forecast / History / Data / Area come from `GROUP_OF` and the `SEC:` headings in `lib/render.py`.

## Never shown
"Safe", "runnable", "fishable" or any verdict; composed sentences other than labels and verbatim attributed source text; a number without unit, time and Source line; a block whose source in `data/sources.json` is not `quoted` or `owner-permission` (`off` sources are built, never shown); a missing source as silence (the gaps line says "Not measured at this gauge: ..."); data older than its limit as current (flow 24 h "not reporting", 30 d not rebuilt; river forecast amber 24 h hidden 72 h; weather obs 3 h / 12 h; hourly forecast amber 12 h hidden 72 h; alerts 3 h; rain 6 h; water temperature tile only under 24 h; the Methodology page states the limits). NWS "Test Message" and "Administrative Message" alerts are ignored (`IGNORED_ALERTS`).

## Every block has four states (tests enforce them)
valid: value, unit, time, Source line. valid-empty: the source said "nothing", printed as a sentence, never silence. unavailable: "Unknown" or "unavailable", never "none"; a block that cannot build is hidden by the guard and logged, and the gaps line names it. stale: the real age, marked old. `SAFETY_BLOCKS` (alerts, river forecast, impacts, stage and flow charts, offline, flood stages, no-forecast, NWS point) fail the gauge and keep its previous page; every other block hides alone. A source record is a dict with the field types in `data/cache_shape.json`; anything else counts as empty.

## How a change ships
- `collect.py` is the only network code (`--fast` every 30 min refreshes flow and stage only; sensors refresh every 6 h). `build.py` reads `cache/` only (`--preview` shows uncleared blocks). Keys live in the calcscrape `.env`, read by `lib/common.py` only; never in pages, zips or docs.
- Batch edits, then `python -I gate.py` ONCE per batch (`--quick` skips the fuzzer; `--live` adds post-deploy checks). Every gate lives in `gates.py` and nowhere else; `refresh.py` runs the same list. A rule that is not in `gates.py` is a note. Mechanical limits in force: `data/ui-budget.json` (repeat 2, first screen 200 words, tile 380 chars, Now tab 5,800 px), `check.py` page weight 90 KB gzipped. They fail the build; change the number in the file with a reason, never silently.
- A template change (`lib/`, `templates/`, `build.py`; any edit, even a docstring, changes the hash) needs a fresh-context reviewer answering `docs/REVIEW-1ST.md` (resume the same agent for a re-verify) and a signed SHIP: `MSYS_NO_PATHCONV=1 python -I tools/record_review.py SHIP docs/research/<report>` plus `--pages-only --pages=<urls>` for live pages; `gate.py` and `publish.py` refuse otherwise. The signature is a hash over the report; it proves the report was not edited, not who wrote it.
- Deploys run only through `.github/workflows/refresh.yml` (push to main, schedule, or `gh workflow run refresh.yml -f mode=fast`). Then: `curl /_template.txt` equals the signed hash, `python -I tools/index_live.py` reports 0 mismatches, read one live page body. "Live" means read this turn.
- The editor gate judges the page as built (external requests blocked); `truth_fuzz.py` skips itself until `lib/*` changes. Windows: PowerShell has no `&&`; Git Bash needs `MSYS_NO_PATHCONV=1` for `/paths/`; `python -I` drops the script folder from `sys.path` (scripts insert ROOT). Never write code through a shell heredoc; write a script file.
- Commit with explicit paths; `git add -f docs/research/<report>` (that folder is git-ignored). Trailer per the current attribution reminder.

## Adding gauges (the site grows here)
- `python -I tools/release.py N` takes the next N gauges from the priority list (`docs/research/priority/picks.csv`, the owner's order; the formula in `tools/rescore.py` is a tiebreaker), marks them live in `data/waves.csv`, collects them in full and builds them held. A new page goes live only with a signed SHIP (`tools/record_review.py --pages-only`) and into Google only through `tools/open_wave.py N --apply`. One river, one gauge first: the gauge nearest the put-in or the fishing town; more gauges on the same river come later.
- The scheduled refresh covers EVERY gauge with a cache file (`collect.py` with no site arguments; never a hard-coded list). A page that is not refreshed every 30 minutes is a wrong page.
- Pace: 25 a wave; the next wave opens when the last one has been crawled and no number incident happened. Order is re-cut from Search Console queries once the owner verifies the property.

## New data source
Row in `data/sources.json` with the quoted terms, credit line and `read_on` (research by WebSearch, evidence level recorded; nothing from memory); fetch in `collect.py` (`fetch_extras` tuple); `python -I tools/gen_cache_shape.py`; one `b_*` block with its four states; one line in `tools/line0_gate.py`; new hash, new review. Held sources and why: `data/sources.json` `off` rows (access points, ramps, cameras, dams, rainfall frequency, reservoir releases, flood zones: terms unclear or an owner key).

## Everything burns tokens (HARD, owner 2026-10-20)
Nothing is free: a script costs its call, output, completion notice and the turn that reads it. One background job at a time; its completion notice is the wake-up; no peeking, no polling. One call that answers three questions beats three. Short replies. Hand off before 70% context.

## Owner alone decides
Publisher name and contact email (waived for the first pages in `data/publisher.json`); opening or pulling pages from the index (`tools/open_wave.py`, record each opening in `docs/OPEN-ITEMS.md`); ads and the consent banner; source-permission visits and keys (USACE, TVA, Recreation.gov, USGS HIVIS, AirNow); cutting any block; running gates when they are paused. Everything still missing is in `docs/OPEN-ITEMS.md` (run `python -I tools/open_items.py` at session start). There is no plan document; do not create one.

## Files
`lib/render.py` blocks, `tab_blocks`, hero, live JS; `lib/blocks2.py`, `lib/blocks3.py` more blocks and `conditions()`; `lib/ui.py` widgets; `lib/directory.py` home, state, hub, trust pages, sitemap; `lib/pages.py` page set and names; `lib/related.py`; `lib/indexing.py`; `lib/reviewgate.py`; `templates/site.css` (base, then the one "ONE SYSTEM" block: the only skin); `gates.py`, `gate.py`; `tools/line0_gate.py`, `tools/agent_gate.py`, `tools/index_live.py`, `tools/review/*.mjs` browser gates; `docs/RUNBOOK.md` what the owner does when something breaks and how indexing is opened; `docs/CORRECTIONS.md`; `docs/REVIEW-1ST.md`.
