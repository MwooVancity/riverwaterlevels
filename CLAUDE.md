# River Water Levels (riverwaterlevels.com)

Strategy and status: PLAN.md (read at session start, update after every batch).

## Reader
A person at or near this river today, on a phone, with 30 seconds: about to fish, paddle, swim, tube, wade, boat, camp, guide, or living, driving or rescuing beside it (flood watchers are one reader of many). The page answers, in order: is it dangerous now, what is the water like, is it normal, what is coming, how today compares. One static page per USGS gauge, government data only (USGS, NOAA/NWS, USDA, EPA). This folder is its own project; calcscrape rules do not apply.

## Hard rules
- Owner is a non-coder: do the work, decide defaults, short plain replies, no "Next:" line.
- Line 0: every reliable public dataset a reader at this river could use goes on the page with its exact source and time. Withhold only if wrong, misleading, padding or no mechanism; show the rest with its caveat.
- User first, never Google first: no SEO gaming, stuffing, doorway or padding. Noindex is never the fix for a thin page; make it richer.
- Clean UI: one page colour, white cards, one label and numeral style, unit beside the number, one line under each number, data age said once.
- Page order, nothing collapsed on the Now tab: alert banner; H1, gauge id, one age chip; tiles (flow, gage height, is-this-normal, 6 h change, NWS forecast or "Not issued", water temperature, rain 24 h, air, sunset); water now; level, flow and flood risk; forecast on every river; how today compares; closed folds. Right column = Area tab.
- Never show "safe", "runnable", "fishable" or any verdict; no composed sentences except labels and attributed source text.
- Every number has a unit, a time and a Source line. A block shows only if its `data/sources.json` row is `quoted` or `owner-permission`.
- Every block has four states: valid, valid-empty (a sentence, never silence), unavailable ("Unknown", never "none"), stale (real age, marked old). `SAFETY_BLOCKS` failing keeps the previous page; other blocks hide alone and the gaps line names them.
- Stale limits: flow 24 h "not reporting"; river forecast amber 24 h, hidden 72 h; weather obs 3 h/12 h; hourly forecast amber 12 h, hidden 72 h; alerts 3 h; rain 6 h; water temperature tile under 24 h. Ignore NWS Test/Administrative alerts.
- Truth against the source, never against ourselves: `tools/truth_live.py` checks readings, flood stages, NWS stage/impact lines and zero points against the APIs fetched now. A sentence no source can check is deleted.
- Five steps on every change: question the requirement, delete, simplify, accelerate, automate last. Delete applies to code and process, never to river data.
- A derived line (not river data) that needs a third fix is deleted. A fix needing a third iteration has the wrong target: stop and report the cause.
- A rule not in `gates.py` / `check.py` is a note. Every new check ships with a planted-bug fixture (`check.py --selftest`). A hater defect class found twice with no rule is a process failure.
- Gates block only what shows a reader something wrong. What can heal (stale build, dead feed, missing gauge) never blocks; `tools/watchdog.py` heals hourly and never emails.
- Page weight limit 90 KB gzipped (`check.py`); change it only in the file with a reason.
- Near-duplicate pages (over 80% shared text) fail the build.
- No cloaking: the Worker never reads user agent, client hints, country, IP or bot score; Googlebot and a phone get the same HTML; JS only refreshes numbers.
- Visitors never spend API calls: the Worker calls outside services only from its */3 cron; phones read `/live/<site>.json`, never USGS.
- `collect.py` is the only network code; `build.py` reads `cache/` only. Keys live in the calcscrape `.env` (read by `lib/common.py`), never in pages, zips or docs.
- The scheduled refresh covers every gauge with a cache file; never a hard-coded list.
- One gauge per river first (nearest the put-in or fishing town). New pages enter Google only via `tools/open_wave.py`. Never bulk-publish.
- Cloudflare free limits are per account (shared with asmrregistry): 5 crons, 100k requests/day, 20,000 files.
- Laptop stays clean: prefer cloud output; delete screenshots once signed. One background job at a time, no polling.
- Windows: no `&&` in PowerShell; `MSYS_NO_PATHCONV=1` in Git Bash; `python -I`; code through a script file, never a heredoc.

## Commands
- Session start: read PLAN.md; `python -I tools/watchdog.py` (live health, problems first).
- Build: `python -I build.py` (`--preview` shows uncleared blocks).
- Gates: `python -I gates.py` once per batch (two gates; `refresh.py` runs the same list). Fix failures at the cause, never by loosening a check.
- Release gauges: `python -I tools/release.py N` (next N from `docs/research/priority/picks.csv`; read the printed names, fix wrong ones first; it collects and builds), then push, then `python -I tools/open_wave.py N --apply`, push, `python -I tools/index_live.py`.
- Pull a page from Google: `python -I tools/open_wave.py --pull <url>`.
- Deploy: only `.github/workflows/refresh.yml` (push to main, schedule, or `gh workflow run refresh.yml`). Then `python -I tools/index_live.py` (0 mismatches) and read one live page body. "Live" = read this turn.
- New data source: row in `data/sources.json` (quoted terms, credit, `read_on`, WebSearch evidence, nothing from memory), fetch in `collect.py` `fetch_extras`, `python -I tools/gen_cache_shape.py`, one `b_*` block with its four states.

## Procedure (every change)
1. Say in one line what will change.
2. One batch of edits through script files, then one check run.
3. Build; look at the phone and desktop screenshots of one page.
4. `python -I gates.py` once.
5. Commit with explicit paths; a push is a deploy; read the live page.
6. Update PLAN.md (status and "Done recently") with the proof.

## Reviews and gates: first principles (HARD, owner 2026-10-29: "be like elon musk when it comes to review/gates. we've blown a million tokens")
- Machines check, agents rarely look. Default for any change = the gate set + the cloud dry run (`dryrun.yml`); a screenshot review is the exception and needs a reason a machine cannot see.
- Evidence 2026-10-28/29: every deploy-breaking bug was caught by a machine (cloud dry run, truth_tests); reviews mostly returned notes. Notes never start a review round.
- Budget: at most ONE full review per day and one light review per batch; say the cost (~170k full, ~80k light) before launching. Over budget = batch it for tomorrow.
- Delete a gate or review step that has not caught a real defect in its last 10 runs; a defect a review finds twice becomes a check the same batch, so reviews shrink over time.
- Non-visual changes (robots/index tags, tools, CI, docs, type fixes covered by a check) are signed `--level=machine` by the builder, never screenshot-reviewed.

## Review (signed-review gate)
- Enforced in `check.py` `review_gaps`: every live gauge needs a signed PASS in `state/reviews/<site>.json`; any change to page code (`lib/`, `templates/`, `build.py`, `collect.py`, `worker/index.js`: `template_hash()`) needs a fresh `_template` PASS before deploy. Signatures append to `state/reviews/_log.jsonl`.
- Size the review to the change (global CLAUDE.md "Size every review to the change"); say the level and cost in one line first:
  - None: nothing a reader sees changed, or a machine check covers it.
  - Light / FIRST mode: phone and desktop first screen plus all page text against the FAIL LIST (F1-F8). Every new gauge; wording, label, format, meta changes.
  - FULL mode: every screenshot. The `_template` sample (`python -I tools/hater_sample.py`) and any gauge with a data shape no reviewed page had; new block, layout, chart or source.
  - Once per batch, never per fix; a FAIL re-reviews only that page; a gauge's PASS stands (code changes: `_template` sample + `check.py` on all pages).
- `node tools/hater_shots.mjs [sites]` writes `.cache/review/<site>/`; a reviewer who did NOT build the change reads what the mode requires with `tools/review_brief.md`, then `python -I tools/review_sign.py <site|_template> PASS|FAIL "defects, worst first" --level=first|full`. Never sign unseen; over 2 unseen phone slices = FAIL.
- One defect a reader would notice = FAIL; a FAIL takes the gauge off the site until a PASS. A machine-catchable FAIL type becomes a `check.py` rule with a fixture in the same batch. Reviewers: 3 pages each, 2 at a time.
- Brief core: "You hate this site; you are at this river with 30 seconds on a phone. FAIL any wrong or contradicting number, missing unit/time/source, unclear label, cut-off text, jargon, repetition, block that does not help today, fillable 'not measured', anything snoflo.org, water.noaa.gov or USGS shows better; judge as a Google quality rater for '<river> <place> water level'. Quote text and image, worst first."

## Owner alone
Publisher name and contact email (`data/publisher.json`, waived for now); opening or pulling pages from the index; ads and consent banner; Search Console verification; source-permission visits and keys (USACE, TVA, Recreation.gov, USGS HIVIS, AirNow, NID); GitHub dispatch token (`GH_DISPATCH_TOKEN`); domain renewal; Cloudflare plan (Workers Paid); outside uptime monitor; cutting any block; running gates when paused. What the owner does when something breaks: `docs/RUNBOOK.md`. Corrections log: `docs/CORRECTIONS.md`.

## Files
Blocks and tabs `lib/render.py` (+ `blocks2.py`, `blocks3.py`, `ui.py`); site pages `lib/directory.py`; indexing `lib/indexing.py` + `data/index-allow.json`; skin `templates/site.css` ("ONE SYSTEM" only); edge `worker/index.js`.
