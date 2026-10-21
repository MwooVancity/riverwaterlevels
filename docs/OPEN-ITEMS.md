# OPEN ITEMS: everything still missing (read at the start of EVERY session; update before ending one)

Owner rule 2026-10-20: "this should be in the harness of CLAUDE.md so I never forget we still got stuff." Nothing here is done until the artifact was checked in the same turn (file read, command output, live page). Tick an item only with its proof; move it to the DONE log at the bottom with the date and the proof.

## A. In flight (working tree, not shipped)
- [ ] UI release A: one-line answer, slim range bar, conditions strip, quiet source lines, phone tabs, band colour. Needs: gate fixes, phone screenshots looked at, fresh signed review, ship, live check.
- [ ] RAIL BUILD (owner 2026-10-20, docs/UI-REDESIGN.md 'The rail rule'): declarations, storm events, rate of change, record comparison, hero rail, weather widget, forecast points, rain, stage ladder, nearby gauges, links, facts; ONE range-switch flow chart; capped tables. Tabs per phone page 1,500 to 2,500 px.
- [ ] UI release B: ONE flow chart with a 7d/30d/12m/earlier-years switch; ONE weather block with a horizontal hourly strip; ONE flood block (ladder + impacts + peaks bar; declarations and storm events show 3 most recent with "all N").
- [ ] UI release C: horizontal-scroll time-series tables with pinned first column; text tables capped at 5 rows with "show all"; colour system (band colours, alerts amber, accents, dark mode); remove jargon (NWS RFC, StreamCat, NHDPlus, "rating", "watershed characteristics").

## B. Reader and product gaps
- [ ] READER-QUALITY GATES (new, blocking): phone page height budget, repeated-fact limit, fine-print share, answer visible by 900 px, tiles count, tabs present. Ratchet: numbers may only go down. (docs/UI-REDESIGN.md baseline: Gauley 13,365 px, Hudson 17,396 px; 28 blocks; sources 22%.)
- [ ] Units toggle (cfs/m3s, ft/m, F/C).
- [ ] Share button and permalinks per block; saved-gauges page; gauges near me; glossary link on every abbreviation. (all unverified: check what exists)
- [ ] Dark mode and print checked on the new layout.
- [ ] Range box tested on a real phone.

### B2. User-first features still missing (owner 2026-10-20: "continue to list everything missing for user satisfaction")
- [ ] FIND: gauges near me (one tap); recently viewed; typo-tolerant search with current flow and band colour per result; ranked lists "high water now / rising fast / low water" on home and state pages; map dots coloured by band with a tap card.
- [ ] UNDERSTAND: "usual for this date: X to Y cfs" printed next to today's value; yesterday / last week / same day last year values; tap-to-explain cfs and gage height (glossary links); upstream "water on the way" with estimated arrival; reader-owned activity presets (never our verdict).
- [ ] ACT: alerts when flow crosses MY range (needs a backend: owner decision); "My rivers" page (saved gauges with live values and band colours, device-local); install to home screen (PWA) and last-known values offline; working share button with a good link preview; compare two gauges side by side; embeddable widget for clubs and blogs; exports beyond 7 days.
- [ ] TRUST: "Report a problem" on every page (prefilled URL and values); corrections and contact link in the footer (needs owner publisher name and email); methodology link inside every source footnote.
- [ ] SPEED AND COMFORT: no layout shift when live numbers arrive; LCP, CLS and INP targets with a gate; dark mode, high contrast, large text, chart text alternatives and keyboard focus checked on the new layout; skeleton states while live data loads.
- [ ] CONTENT: gauge-type explainers (below a dam, tidal, ice-affected, small creek); links out to American Whitewater, state fishing reports and boat ramps (links only); recent history in plain words ("highest since March").
- [ ] RETURN: weekly digest email (backend); "biggest changes today" regional pages.

## C. Gates still open
- [x] `tests.py` split 2026-10-20: the pure-logic checks run as `tests_logic.py` in refresh.py ALWAYS (8 checks incl. workflow-YAML parse; 0 failures this turn). Determinism, forced failure and rollback stay in `tests.py` by hand (they rewrite dist/ and cache/).
- [ ] Reviewer P2s from FRESH-REVIEW-10-U: comparison card keeps its build-time value under a newer live flow tile; clipped impact cards drop the consequence sentence (Atlanta 19/20 ft); odd forecast-high cards (Atlanta, Hudson); desktop swipe strip cuts its last card; footer Terms links 21 px high. "No earlier day" never seen rendered.
- [ ] Forbes-editor items not yet done: one-sentence verdict line, uneven tile lengths (longest 338 chars), unlabelled sparklines, "Set your range" row placement, dense grey notes. Lower the editor budget in data/ui-budget.json as each is fixed.
- [ ] Fixtures: irregular sampling for the 24 h mean. [DST, leap-day key, tied and missing percentile values, naive timestamps: `truth_time.py`, in the chain since 2026-10-20.]
- [ ] Unit allowlist for every field beyond forecast units, forecast time-alignment gate, NWS/USGS datum gate (not only wording). [Forecast unit handling is tested in `truth_time.py`.]
- [ ] Pre-deploy truth check can still skip on a USGS outage without blocking: decide a limit (for example block after 2 consecutive skipped builds).
- [ ] Reviewer independence: record the independent (ChatGPT) review per template hash in data/reviews.json with `--reviewer=`.
- [ ] One deployer and a shared lock (GitHub + two Windows tasks can race; runs/refresh.lock is local to the PC).
- [ ] truth_fuzz deep run (all 25 gauges) by hand or nightly; fuzz covers only 3 gauges in quick mode.
- [x] Block guard: flood outlook, NWM medium range and storm reports stay OUT of SAFETY_BLOCKS: decided 2026-10-20 (supplementary, nothing claims safety when they are missing; reviewer R agreed).

### C2. Prior art to adopt (found 2026-10-20: "aren't there repos that could have saved us time?"; verified by search unless marked)
- [ ] Lighthouse CI + axe-core in CI with a budget file (performance, accessibility, page weight) against `dist_next`: replaces hand-built perf and a11y gates.
- [x] Percentile cross-check built WITHOUT installing hyswap (`tools/pct_crosscheck.py`, empirical rank over the same date plus or minus 3 days from USGS daily history vs our interpolated percentile); 2026-10-20 result on 5 gauges: gaps 4, 1, 1, 0, 8 points (tolerance 15). Wired into refresh.yml for full runs (every 6 h, after the deploy) 2026-10-20; still open: add more gauge types.
- [x] GitHub Actions `concurrency:` group on refresh.yml: ALREADY PRESENT (seen 2026-10-20: group refresh, cancel-in-progress false). The PC tasks are still a second deployer (section C).
- [ ] Evaluate dataretrieval-python (official USGS client) against our own `collect.py` calls for the identity and shape checks; do not replace working code without a failing test.
- [ ] Study DOI-USGS/flow-tiles (CC0) for the national band map; Datasette or similar for the open data catalog (not verified).
- Rule for next time: before any new subsystem, search GitHub and the vendor's own docs first and write what was found here.

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
- [ ] docs/PLAN.md, WORK-LIST.md, RISKS-AND-STAGES.md: top banner added 2026-10-20 pointing to the current docs; the old numbers inside still need a full rewrite.
- [ ] Owner fills publisher name and contact in docs/CORRECTIONS.md and About.
- [ ] Rebuild the ChatGPT zip after every UI release (`python -I tools/pack_review.py`) and inspect it.

## G. Owner only
- [ ] Publisher name, contact email, corrections page text live on About.
- [ ] Source-permission emails: Drought Monitor, NID, Reclamation, FEMA.
- [ ] Consent banner before any ads; AdSense decision.
- [ ] Five real river users try a page on a phone (docs/UNIQUE-VALUE.md).
- [ ] Switch off the second deployer once the outside monitor exists.
- [ ] Lift noindex: wave 0 per docs/INDEXING-RULES.md.

## J. Links and growth assets (docs/LINK-BUILDING.md; outreach only after wave 0 is indexed and the owner publisher/contact exists)
- [ ] Embeddable live gauge widget (`/embed/<gauge>/` + copy-paste snippet on every gauge page).
- [ ] Open data catalog: `/data/`, `/api/gauge/<id>.json` static snapshots, `/llms.txt`.
- [ ] National and state "now" pages (above normal, below normal, biggest 24 h changes) and a record watch.
- [ ] `docs/LINK-LOG.md` created and used for every outreach contact.
- [ ] Competitor backlink study (Bing Webmaster / Common Crawl via the backlink skills).

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
- 2026-10-20 editor_gate.mjs + live_flow_test.mjs + tests_logic.py added to the release chain (all pass on dist_next; editor gate caught "cfs" spelled out on 0/25 pages, fixed to 25/25). Release A SHIP signed for 0cce61d1697e07ba (FRESH-REVIEW-10-U), commit f4cad14. NOT yet live: confirm with the refresh run and the live `_template.txt`.
- 2026-10-20 refresh.yml was invalid YAML since 549c95b (scheduled refreshes could not start); fixed and gated by the workflow-parse check in tests_logic.py.
- 2026-10-20 independent percentile cross-check agrees within 8 points on 5 gauges (tools/pct_crosscheck.py output seen).
- 2026-10-20 `truth_time.py` (DST, leap-day key, ties, unit handling, naive timestamps) and `check.py --selftest` wired into refresh.py ALWAYS; reader-quality budget `tools/review/reader_budget.mjs` + `data/ui-budget.json` in the browser gates.
