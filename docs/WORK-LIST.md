# Work list after the plan review (2026-10-18)

📄 Planning doc only: this file does not change the site. It is the complete list of what was done in response to `docs/research/FRESH-REVIEW-PLAN.md`, with a status for each line (DONE, PARTLY, DECIDED, RESEARCHED, LATER, OWNER). A line is DONE only when the artifact was checked in the session that wrote it; the checks are named. A hostile auditor is asked to verify every line (master prompt Mission L).

## A. Page model
1. Forecast pages merged into the gauge page (one page per gauge, a Forecast section where NWS issues a river forecast, `/forecast/` and `/water/` redirect). DONE: build, `check.py`, `tests.py`, `ui_gates.mjs` pass; 49 pages; redirect rules in `dist_next/_redirects`. LIVE (verified 2026-10-19: 49 pages, `/forecast/` and `/water/` return 301 to the gauge page).

## B. Release queue
2. Free federal data downloaded for every gauge: USGS coordinates (9,099 of 9,099), Wild and Scenic segments (948, with 560 recreation and 467 fish values), Nationwide Rivers Inventory (4,496 segments), Census places (19,484 with population). DONE: `tools/fetch_geo.py`, files in `data/geo/`.
3. `tools/rescore.py` rewritten as a gauge-level score (gate, Activity 0.45, Reach 0.15, Decision 0.25, Quality 0.15, duplicate penalty, one gauge per river per day). DONE: `data/waves-report.txt`. Weights differ from the reviewer's proposal because population-based reach under-ranked rural recreation towns; reason recorded in `docs/PLAN.md`.
4. Wikipedia matching: titles starting "List of", city articles ("Name,_State") and articles whose title lacks the river's first word are rejected inside `rescore.py`; Wikipedia is a 40% share of Reach only. DONE for scoring; `tools/demand.py` itself is unchanged (PARTLY).
5. Ditch, canal, drain, outfall, floodway, spillway, diversion, sewer, storm, channel names, basins under 5 sq mi and records under 3 years are excluded (1,242 gauges). One gauge per river per release day. DONE.
6. Held names: name cleaner v2 (`tools/clean_names.py`, `data/name-fixes.csv`) fixed 1,383 of 1,801; 283 remain held; no live address changed (checked). DONE; the 283 are PARTLY (review by hand in score order, LATER).
7. Back-test `data/backtest.txt`: 19 of 25 (misses listed in `docs/PLAN.md`). DONE as a measure; PARTLY as a result.
8. `rescore.py` and `demand.py` read `data/pages-all.csv` in this folder. `rescore.py` DONE; `demand.py` still reads the calcscrape copy (the two files are byte-identical): LATER.
9. Indexability: `tools/open_wave.py` requires status live or queue, at least 15 data blocks (`dist/_blocks.json`) and 10 years of record. DONE in code; thresholds are provisional until tail gauges are built.

## C. Water-sports content
10. Dam release data: terms searched for Reclamation RISE, USACE CWMS, NID (no restrictions stated in metadata, no terms page found) and American Whitewater (no terms found). RESEARCHED; block LATER (spec in `docs/PLAN.md`); AW is link only.
11. Runnable / fishable / float ranges: LATER, only verbatim attributed source values.
12. Thunderstorm line from the NWS hourly forecast (hours called thunderstorms, or an explicit "none") on every gauge page. DONE: `truth_tests.py` check 6. Water temperature beside air temperature, "not available" lines: already built. Bacteria advisories, low-head dam statement: LATER (need a source).
13. Lakes: DECIDED in, after the first river cohort. Not built.

## D. Scale
14. Page-count honesty: about 9,500 pages at full size; tens of thousands need another page type (lakes; flood forecast points without a USGS gauge). DECIDED, recorded in `docs/PLAN.md` and `docs/RISKS-AND-STAGES.md`.
15. Page weight: measured 28 to 55 KB compressed; the 150 KB raw bar withdrawn; `check.py` fails a gauge page above 90 KB compressed. DONE. Tail refresh tiers and R2 for per-gauge files: designed in `docs/PLAN.md`, LATER.
16. File budget: total checked at 19,000 (`build.py`); per-page-class budgets: LATER.

## E. Gates and rules
17. `ui_gates.mjs` and the template review block a deploy; CI installs Playwright. DONE in code (`refresh.py`, `refresh.yml`); first CI run with it: pending (pushed 2026-10-19; the next scheduled GitHub run is the proof).
18. Review verdicts signed against their report file; hand-written or edited verdicts refused. DONE: `tests.py` 8b. GRANDFATHERED pages stay (live before the gate); they cannot be indexed.
19. NWS User-Agent carries the About page URL. DONE (a real contact address is OWNER).
20. One CLAUDE.md and one PLAN.md; contradictions removed; older documents archived in `docs/archive/`; `MASTER-PLAN-20K.md` became `docs/RISKS-AND-STAGES.md` with corrected numbers; `REVIEW-PROMPT.md` helper path fixed and persona added. DONE; a hostile auditor is asked to find what is still stale.
21. Windows scheduled tasks disabled after a clean day of the watchdog: OWNER machine step.

## F. Master prompt and zip
22. Master prompt rewritten (Missions K and L added, queue and claims verification, tens-of-thousands question). DONE: `calcscrape/docs/research/chatgpt-final-master-prompt.md`.
23. Fresh-brain review of the changed template: thirteen rounds (FRESH-REVIEW-10-A to -M); round M found no P0; signed SHIP recorded in `data/reviews.json` and deployed. DONE. P1 backlog in `docs/PLAN.md`.
24. Zip rebuilt by `tools/pack_review.py` only after 1 to 23, key scan empty.

## Round-9 and round-10 page fixes (from the earlier reader reviews)
Unit-aware forecast reading (Freeport), NWPS observed stage read by units, datum-gap handling, windowed 1 h / 6 h / 24 h changes, forecast "falls to" and single-peak wording, `/about/` corrected, symmetric upstream / downstream (`lib/related.py`), live-update-failed note and static note retired by a newer reading, midnight chart ticks, nearby-gauge and record absence lines, air station name and distance, radar reach (140 miles), home-search no-match link, static nav on phones, glossary entries. DONE (checks: `truth_tests.py` 6 to 9, `tests.py` 8c, `ui_gates.mjs`, builds). Sidebar air and sun blocks removed from the merged Forecast section (the tiles already carry them).

## OWNER (cannot be done by me)
Publisher name and contact email; corrections and outage policy; consent banner before ads; real paddler and angler testing; the decision to lift noindex; disabling the two Windows tasks; the four source-terms emails or the decision to rely on public-domain status; whether to pay for Workers if a page type needs more than 20,000 files.
