# River Water Levels (riverwaterlevels.com)

Status and next steps: PLAN.md. Read at session start, update after every batch. This folder is its own project; calcscrape rules do not apply.

## Reader
A person at or near this river today, on a phone, with 30 seconds: to fish, paddle, swim, tube, wade, boat, camp, guide, or living, driving or rescuing beside it. The page answers, in order: is it dangerous now, what is the water like, is it normal, what is coming, how today compares. One static page per gauge, official government data only.

## Priorities
- USER, NOT GOOGLE: judge every decision by that person. Reject a change that helps ranking but not them. No SEO gaming, stuffing, doorway or padding. Noindex never fixes a thin page.
- GLOBAL (2026-10-31): new build work goes to non-US rivers first, by real English search demand. A river needs a demand number, an official feed and reuse terms read from the agency. One test page per country before scaling; English only. The US factory keeps publishing 25 a day, untouched.
- Non-US pages: own `data/sources.json` row, local unit plus feet, the agency's own low/high labels, no sailing verdict. A dead foreign feed stales only its page. No Google Analytics or ads on EU-reader pages until a consent banner exists.
- OPTIMIZE: state the objective (weekly clicks from people helped), constraints and scarce resource (build time). Measure first, fix only the current bottleneck, rank by gain per cost, label guesses, re-measure.
- COUNT THE BYTES: a reader on one bar pays for every byte. Measure what a phone downloads, third-party scripts included; cut the biggest item first. River data is never the waste. Page limit 90 KB gzipped (`check.py`). These two docs obey it too: every line must change a decision.
- Five steps on every change: question the requirement, delete, simplify, accelerate, automate last. Delete applies to code and process, never river data.
- Owner is a non-coder: do the work, decide defaults, short plain replies, no "Next:" line.

## Page rules
- Line 0: every reliable public dataset a reader at this river could use goes on the page with exact source and time. Withhold only if wrong, misleading, padding or no mechanism.
- Clean UI: one page colour, white cards, one label and numeral style, unit beside the number, one line under each number, data age said once.
- Order, nothing collapsed on Now: alert banner; H1, gauge id, one age chip; tiles (flow, gage height, is-this-normal, 6 h change, NWS forecast or "Not issued", water temperature, rain 24 h, air, sunset); water now; level, flow and flood risk; forecast; how today compares; closed folds. Right column = Area tab.
- Never "safe", "runnable", "fishable" or any verdict; no composed sentences except labels and attributed source text.
- Every number has a unit, a time and a Source line. A block shows only if its `data/sources.json` row is `quoted` or `owner-permission`.
- Four block states: valid, valid-empty (a sentence), unavailable ("Unknown", never "none"), stale (real age, marked old). `SAFETY_BLOCKS` failing keeps the previous page; other blocks hide alone and the gaps line names them.
- Stale limits: flow 24 h "not reporting"; river forecast amber 24 h, hidden 72 h; weather obs 3 h/12 h; hourly forecast amber 12 h, hidden 72 h; alerts 3 h; rain 6 h; water temperature tile under 24 h. Ignore NWS Test/Administrative alerts.
- Truth against the source: `tools/truth_live.py` checks readings, flood stages, NWS lines and zero points against live APIs. A sentence no source can check is deleted.
- A derived line needing a third fix is deleted. A fix needing a third iteration has the wrong target: stop and report the cause.
- Near-duplicate pages (over 80% shared text) fail the build.

## System rules
- No cloaking: the Worker never reads user agent, client hints, country, IP or bot score. JS only refreshes numbers.
- Visitors spend no API calls: the Worker calls outside only from its */3 cron; phones read `/live/<site>.json`.
- `collect.py` is the only network code; `build.py` reads `cache/` only. Keys live in the calcscrape `.env`, never in pages, zips or docs; never print them.
- Refresh covers every gauge with a cache file, never a hard-coded list.
- One gauge per river first. New pages enter Google only via `tools/open_wave.py`. Never bulk-publish.
- Cloudflare free limits are per account (shared with asmrregistry): 5 crons, 100k requests/day, 20,000 files.
- A rule not in `gates.py`/`check.py` is a note. Every new check ships with a fixture (`check.py --selftest`).
- Gates block only what shows a reader something wrong. What can heal never blocks; `tools/watchdog.py` heals hourly. Fix failures at the cause, never by loosening a check.
- Laptop stays clean; prefer cloud output. One background job, no polling.
- Windows: no `&&` in PowerShell; `MSYS_NO_PATHCONV=1` in Git Bash; `python -I`; code through a script file, never a heredoc.

## Commands
- Session start: `python -I tools/watchdog.py`.
- Build: `python -I build.py` (`--preview` shows uncleared blocks). Gates: `python -I gates.py` once per batch.
- Release: `python -I tools/release.py N` (read the printed names), push, `python -I tools/open_wave.py N --apply`, push, `python -I tools/index_live.py`. Pull a page: `python -I tools/open_wave.py --pull <url>`.
- Deploy: only `refresh.yml` (push main, schedule, or `gh workflow run refresh.yml`), then `tools/index_live.py` (0 mismatches) and read one live page. "Live" = read this turn.
- New source: row in `data/sources.json` (quoted terms, credit, `read_on`, WebSearch evidence, nothing from memory), fetch in `collect.py` `fetch_extras`, `python -I tools/gen_cache_shape.py`, one `b_*` block with four states.

## Every change
1. Say what will change in one line. Write how it fails first.
2. One batch through script files; `python -I gates.py` once.
3. Commit explicit paths, push branch `check`; `dryrun.yml` runs itself. Read "refresh OK", then push main in a separate step. A push to main is a deploy.
4. Read the live page. Update PLAN.md with the proof.

Failures already seen: laptop data differs from cloud data (only the dry run proves); one rule in several places (grep first, truth_tests and check.py included); a check matching too much (run on all pages first); a file only on the laptop (`git ls-files` every input); day 30 / 1,000 gauges limits; two workflows on one concurrency group; old data shown as now (render with the clock shifted 2 days); risky collect or deploy changes (shadow run first).

## Reviews
- Machines check, agents rarely look. Default: gates plus cloud dry run. A screenshot review needs a reason a machine cannot see. At most one full (~170k tokens) a day and one light (~80k) a batch; say the cost first.
- `check.py` `review_gaps`: every live gauge needs a signed PASS; a change to `lib/`, `templates/`, `build.py`, `collect.py` or `worker/index.js` needs a fresh `_template` PASS before deploy.
- None or `--level=machine`: nothing a reader sees changed, or a check covers it. New gauges ship on machine gates. Light: wording, label, format. Full: new block, layout, chart or source (`python -I tools/hater_sample.py`).
- `node tools/hater_shots.mjs [sites]`, a reviewer who did not build it reads `tools/review_brief.md`, then `python -I tools/review_sign.py <site|_template> PASS|FAIL "defects" --level=first|full`. One reader-visible defect = FAIL, off the site until PASS.
- A defect found twice becomes a `check.py` rule that batch. Delete a gate with no real catch in 10 runs.
- Helpfulness checklist: `tools/helpful_audit.md` (A-Q); each batch checks the categories it touches.

## Owner alone
Publisher name and contact email; opening or pulling pages from the index; ads and consent banner; Search Console; source-permission visits and keys; domain renewal; Cloudflare plan; outside uptime monitor; cutting any block. When something breaks: `docs/RUNBOOK.md`. Corrections: `docs/CORRECTIONS.md`.

## Files
Blocks `lib/render.py`, `blocks2.py`, `blocks3.py`, `ui.py`; site pages `lib/directory.py`; indexing `lib/indexing.py` + `data/index-allow.json`; skin `templates/site.css` ("ONE SYSTEM" only); edge `worker/index.js`.
