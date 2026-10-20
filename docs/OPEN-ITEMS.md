# OPEN ITEMS: everything still missing (read at the start of EVERY session; update before ending one)

Owner rule 2026-10-20: "this should be in the harness of CLAUDE.md so I never forget we still got stuff." Nothing here is done until the artifact was checked in the same turn (file read, command output, live page). Tick an item only with its proof; move it to the DONE log at the bottom with the date and the proof.

## A. In flight (working tree, not shipped)
- [ ] UI release A: one-line answer, slim range bar, conditions strip, quiet source lines, phone tabs, band colour. Needs: gate fixes, phone screenshots looked at, fresh signed review, ship, live check.
- [ ] UI release B: ONE flow chart with a 7d/30d/12m/earlier-years switch; ONE weather block with a horizontal hourly strip; ONE flood block (ladder + impacts + peaks bar; declarations and storm events show 3 most recent with "all N").
- [ ] UI release C: horizontal-scroll time-series tables with pinned first column; text tables capped at 5 rows with "show all"; colour system (band colours, alerts amber, accents, dark mode); remove jargon (NWS RFC, StreamCat, NHDPlus, "rating", "watershed characteristics").

## B. Reader and product gaps
- [ ] READER-QUALITY GATES (new, blocking): phone page height budget, repeated-fact limit, fine-print share, answer visible by 900 px, tiles count, tabs present. Ratchet: numbers may only go down. (docs/UI-REDESIGN.md baseline: Gauley 13,365 px, Hudson 17,396 px; 28 blocks; sources 22%.)
- [ ] Units toggle (cfs/m3s, ft/m, F/C).
- [ ] Share button and permalinks per block; saved-gauges page; gauges near me; glossary link on every abbreviation. (all unverified: check what exists)
- [ ] Dark mode and print checked on the new layout.
- [ ] Range box tested on a real phone.

## C. Gates still open
- [ ] `check.py --selftest` and `tests.py` into the release chain (split `tests.py` first: it rewrites the real dist/ and cache/).
- [ ] Fixtures: DST transition, leap day, irregular sampling, duplicate percentile values.
- [ ] Unit allowlist gate (reject unknown units for every field), forecast time-alignment gate, NWS/USGS datum gate (not only wording).
- [ ] Pre-deploy truth check can still skip on a USGS outage without blocking: decide a limit (for example block after 2 consecutive skipped builds).
- [ ] Reviewer independence: record the independent (ChatGPT) review per template hash in data/reviews.json with `--reviewer=`.
- [ ] One deployer and a shared lock (GitHub + two Windows tasks can race; runs/refresh.lock is local to the PC).
- [ ] truth_fuzz deep run (all 25 gauges) by hand or nightly; fuzz covers only 3 gauges in quick mode.
- [ ] Block guard: flood outlook, NWM medium range and storm reports are not in SAFETY_BLOCKS (decide).

## D. Data and safety
- [ ] Flood-stage margin wording (reviewer P2): say which zero point the margin uses on THIS page.
- [ ] Stuck sensor is only a printed note (decided weak on purpose).
- [ ] Gauge types never exercised on real data: ice-affected, canal, estuary.
- [ ] Ohio and Gauley NWS point/datum cross-check against water.noaa.gov (reviewer could not open the NWS pages).

## E. Operations
- [ ] Outside uptime monitor on /status.json and /_truth.json (owner signs up; free service).
- [ ] Confirm GitHub failure emails reach the owner (docs/RUNBOOK.md assumes it).
- [ ] Search Console property verified for riverwaterlevels.com (owner).

## F. Docs
- [ ] docs/PLAN.md, WORK-LIST.md, RISKS-AND-STAGES.md still describe older numbers: reconcile with INDEXING-RULES.md and this file.
- [ ] Owner fills publisher name and contact in docs/CORRECTIONS.md and About.
- [ ] Rebuild the ChatGPT zip after every UI release (`python -I tools/pack_review.py`) and inspect it.

## G. Owner only
- [ ] Publisher name, contact email, corrections page text live on About.
- [ ] Source-permission emails: Drought Monitor, NID, Reclamation, FEMA.
- [ ] Consent banner before any ads; AdSense decision.
- [ ] Five real river users try a page on a phone (docs/UNIQUE-VALUE.md).
- [ ] Switch off the second deployer once the outside monitor exists.
- [ ] Lift noindex: wave 0 per docs/INDEXING-RULES.md.

## H. Unproven (strategy)
- [ ] Are the pages better than USGS or American Whitewater for a real task? (needs G: real users)
- [ ] Demand and keywords: needs the first indexed cohort and Search Console data; do not write a keyword file from guesses.
- [ ] Revenue: about 200,000 pageviews a month for $1,000 at a $5 RPM is a guess until measured.

## I. Prompts, tools and hooks you keep forgetting (printed at every session start by `tools/open_items.py --brief`; this section is not a to-do list)
- ChatGPT prompts (docs/packet/prompts/, all inside river-review-packet.zip; new chat, upload the zip, paste): PROMPT-BUGHUNT (find every bug, browse + run code), PROMPT-TEMPLATE (browse live UI, design Fort Knox template), PROMPT-ALL (everything, in parts, say "continue"), PROMPT-1 strategy, -2 verify claims, -3 gates, -4 missions.
- Rebuild the zip after every UI release: `python -I tools/pack_review.py` (inspect it, key scan must be empty).
- Session start: `python -I tools/open_items.py`; gates by hand: build.py, check.py, tests.py, truth_tests.py, truth_types.py, truth_fuzz.py (7 min), node ui_gates.mjs, tools/review/{clip_all,search_test,alerts_live_test,range_test}.mjs.
- Template change = new hash = fresh reviewer + `python -I tools/record_review.py SHIP <report>` + commit with `git add -f docs/research/<report>` + push + `gh workflow run refresh.yml` + read the run and the live `_template.txt`.
- Indexing: docs/INDEXING-RULES.md (open_wave.py N, --apply, --pull). Alerts: docs/RUNBOOK.md. Corrections: docs/CORRECTIONS.md.
- Hooks live in `.claude/settings.json` (session-start reminder only; a per-turn reminder would cost tokens every turn).

## DONE log (date, item, proof)
- 2026-10-19 template review chain S/R/Q/P signed; CI green; live `_template.txt` = signed hash.
- 2026-10-19 `_truth.json` records skipped checks; watchdog reads it (live file seen).
- 2026-10-20 block guard + failure isolation + page carried forward (publish test in a throwaway copy); fuzzer 0 failures at 9,354 renders.
- 2026-10-20 range tile: commas accepted, live refresh does not close the form (range_test.mjs passes on live).
- 2026-10-20 docs: INDEXING-RULES, RUNBOOK, UNIQUE-VALUE, CORRECTIONS, PAGE-CONTRACT, UI-REDESIGN.
