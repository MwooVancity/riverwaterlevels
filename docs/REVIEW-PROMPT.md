# Master review prompt (fresh brain, reader first)

Use: give the text under "PROMPT" to a fresh agent (no history, no hints about what we think is wrong). Run it (1) before any change to `lib/`, `templates/` or `build.py` goes live, and (2) on a sample of every release batch (see "Which pages"). The review is the gate: no SHIP verdict on file for the current template hash, no template deploy. Data refreshes every 30 minutes do not need a review; they are covered by the automated gates (`check.py`, `tests.py`, `ui_gates.mjs`, `tools/watchdog.py`).

Why this and not "review every page": all pages come from one template, so a defect is in the template and shows on thousands of pages at once; a person cannot read 9,099 pages, but a fresh reader can break the template on its hardest cases. Mechanical defects found by a review must become an automated gate the same day (`check.py`, `tests.py`, `truth_tests.py`, `ui_gates.mjs`) so the same defect never needs a human again. A review finds what nobody thought of; a gate keeps it from coming back.

## Which pages (the hardest cases, not random ones)
One of each, per release batch: a big river; a creek; a dam-controlled river; a gauge with no NWS forecast; a gauge with an active alert; a tidal or ice-affected gauge; a gauge with no water temperature; a gauge whose NWS forecast point is a different gauge; a very low and a very high comparison; the home page, a state page, a hub page, the status page. At scale add the 5 pages with the largest change since the last review.

## PROMPT

You are a product reviewer seeing riverwaterlevels.com for the first time. Ignore Google, SEO and rankings completely. The only question: for a real person at or near a US river, is this the best place on the internet to understand the river right now, and what stops it being that? You will be judged on the defects you find that I did not know about and on never praising something you did not test.

Rules of the site you must respect when proposing fixes: government data only, no composed advice or verdicts, every block carries a Source line with a time. If a rule hurts readers, say so and propose a way to honour its intent.

PAGES: <list the live URLs from "Which pages">. Playwright is available through node (createRequire('C:/Users/mwoo7/Desktop/calcscrape/package.json')). Helper scripts: `C:/Users/mwoo7/AppData/Local/Temp/claude/C--Users-mwoo7-Desktop-calcscrape/05d97f67-e169-43ec-bf1c-8104f8e1417a/scratchpad/` (elem_shots.mjs, overflow.mjs, culprit.mjs, clipped.mjs, imgload.mjs) and `ui_gates.mjs` in the site folder.

STEP 1, LOOK. Screenshot every page at 1280 px and 390 px (deviceScaleFactor 2, isMobile), light and dark. Full pages are very tall: slice into 2000 px pieces. Remote images (radar, USGS topo) load lazily online: scroll to them first. For EVERY screenshot you open write one line of what you literally see (what is in the top 900 px, what is cut off, overlaps, empty, too small). A verdict without these lines is invalid.

STEP 2, TASKS as each person; report seconds and success or failure: (a) kayaker at a put-in on a phone: is it rising or falling, what is coming; (b) angler: temperature, whether flow is typical, sunset; (c) landowner worried about flooding: distance to flood stage, forecast, alerts, what floods at which stage; (d) first-time visitor who has never heard of cfs, gage height or percentile: can they read the top; (e) someone who wants two nearby rivers: can they move between pages; (f) slow phone or screen reader.

STEP 3, CONTRADICTIONS (the defects humans miss). For each page list every number that appears twice or that describes the same thing, and check they agree: headline direction versus the 1 h, 6 h and 24 h changes; "now" values versus their stated times; the gauge a flood stage belongs to versus the gauge being shown; units; percent and word bands (a "below normal" must read as lower, never higher); counts; dates and time zones. Then cross-check 5 gauges against waterdata.usgs.gov and water.noaa.gov (flow, stage, time, flood stages, forecast).

STEP 4, SILENCE (the other class humans miss). For every element ask what it is silent about and whether a reader would read the silence as "fine". Examples: no forecast, no alert, no temperature, no upstream gauge, a dam upstream, a stale value, a sensor offline, an estimated number that looks measured. Every absence must say that it is absent and why.

STEP 5, THE REST: jargon, density, hierarchy, repeated information, dead space, empty widgets, mobile (clipping, tap size, sticky bars), dark mode, folded content a reader needs, slow-connection behaviour, and anything a competitor (USGS, NWS, American Whitewater, Lakebrief) does better; say what.

OUTPUT (write the full report to `docs/research/FRESH-REVIEW-<n>.md` and return at most 400 words): 1) VERDICT: SHIP, SHIP AFTER FIXES (list), or HOLD, for the template as tested. 2) Ranked defects P0 (wrong, contradictory, unsafe, or blocks the main job), P1 (worse than a competitor), P2 (polish), each with page URL or screenshot file, the quote, why it hurts a reader, the cheapest fix, AND the automated gate that would have caught it (check, regex or test and its fixture). 3) What you could not check yourself (be exact: a source you could not open, an image that did not load, a screen reader you did not run). 4) The ten changes that most improve the reader's experience.

Read-only: do not edit the site, run refresh/build/publish, or deploy.

## Pre-deploy flow (new pages and template changes)
1. `python -I build.py`, then `python -I check.py`, `python -I tests.py`, `node ui_gates.mjs` must pass.
2. `node tools/serve.mjs dist_next 8123` serves the not-yet-live pages; give the reviewers `http://localhost:8123/...` URLs for the NEW gauge pages (cross-checks against USGS and NWS still use the live agency sites). At about 25 new pages a day use one reviewer per 5 pages in parallel; a template change gets the full prompt on the hardest cases.
3. Fix every P0 (and P1 where cheap), rebuild, rerun step 1. Turn each mechanical defect into a gate the same day.
4. `python tools/record_review.py SHIP docs/research/FRESH-REVIEW-<n>.md` writes the verdict for the template hash and for every new gauge page in `dist_next`.
5. `python publish.py` (or `refresh.py`) now publishes. `publish.py` REFUSES any new gauge page without a SHIP verdict in `data/reviews.json` ("NEW PAGES NOT REVIEWED"); pages already live, and the 30-minute data refresh, are never blocked. `refresh.py` also logs `SOFT GATE FAILED ... template_hash.py --check` when the live template has no SHIP verdict.
The 43 pages live before this gate existed are marked GRANDFATHERED (honestly: not individually reviewed); the all-pages review that follows FRESH-REVIEW-6 replaces that mark with SHIP or a defect list.

## Record
`data/reviews.json`: `{"templates": {"<hash>": {...}}, "pages": {"/river/x/y/": {"verdict": "SHIP|HOLD|GRANDFATHERED", "report": "...", "date": "..."}}}`. The hash is `python tools/template_hash.py`. Do not edit it by hand; use `tools/record_review.py`.
