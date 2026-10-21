# FRESH-BRAIN-DOCS-2026-10-21: the docs, the code, the gaps

Read: CLAUDE.md, README.md, docs/*.md (7), docs/packet/**/*.md (11), graphify-out/GRAPH_REPORT.md, docs/research/DESIGN-REVIEW-2026-10-21.md, docs/research/FRESH-REVIEW-10-Z.md; code: lib/render.py, lib/blocks2.py, lib/blocks3.py, collect.py, gates.py, gate.py, tools/line0_gate.py, tools/agent_gate.py, tools/review/editor_gate.mjs, templates/site.css, plus check.py, refresh.py, tools/open_items.py, data/sources.json, data/reviews.json, data/publisher.json, data/index-allow.json, data/ui-budget.json. Not read: docs/research/* (other), docs/archive/*, lib/ui.py, lib/directory.py beyond grep, the live site, screenshots.

## FILE VERDICTS

| File | Verdict | Reason |
|---|---|---|
| CLAUDE.md (64 lines) | REWRITE to the master prompt below (about 50 lines) | Three "Line 0" sections say the same thing three ways; the "Page template (frozen final form)" section describes a page that no longer exists (Save gauge, CSV, "Your range" tile: cut on 2026-10-20 and gone from render.py); "Not built yet" lists tides and nearest water-temperature sensor, both of which collect.py and blocks3.py already do; line 7 says the site is under a noindex hold, `data/index-allow.json` has `open: true` with 25 pages; line 42 invokes a global "Next:" rule that the global CLAUDE.md does not contain and the owner revoked 10-20. |
| README.md | KEEP | 17 lines, every line checks out against gates.py, refresh.py and lib/common.py. |
| docs/OPEN-ITEMS.md | REWRITE (trim to true gaps) | Section B lists three items already in code (tides: collect.py:774 `fetch_tides`, blocks3.py:294 `b_tides`; thunder and humidity rows: collect.py:575, render.py:1260-1261; nearest water-temperature sensor: collect.py:790 `fetch_near_wtemp`). A gap list that lists done work is the "wasting days" the owner named. `tools/open_items.py --brief` looks for a section `## I.` that does not exist. |
| docs/REVIEW-1ST.md | KEEP | The only prompt a gate reads (agent_gate.py, record_review.py require `## #1 COMPARISON`). It is the one review doc that is code-bound. |
| docs/RUNBOOK.md | KEEP, one edit | Owner-facing plain steps, matches watchdog.py messages. "Two deployers" section is stale once the Windows tasks are off; "Things only you can do" duplicates OPEN-ITEMS D. |
| docs/INDEXING-RULES.md | MERGE into RUNBOOK | 9 lines; three commands and one rule. The rule "A page may be opened only when ... signed SHIP ... `_truth.json` ok" is enforced by open_wave.py and check.py, so the doc is a pointer. |
| docs/CORRECTIONS.md | KEEP | A public policy and an empty ledger; the only doc with a reader-facing promise. The placeholder text belongs on the About page the day the owner sets a contact. |
| docs/PAGE-CONTRACT.md | MERGE into CLAUDE.md "Hard rules" | Good content (four states, safety blocks) but it restates render.py:1529 `SAFETY_BLOCKS` and the truth tests; it says "20 contracts", gates.py says 22; "10 gauge-type variants" vs CLAUDE.md "nine". Two copies drift. |
| docs/packet/README-FIRST.md | DELETE | A guide to a ChatGPT review zip whose contents (`late/`, `appendix/`, `code/docs/PLAN.md`, `WORK-LIST.md`, `RISKS-AND-STAGES.md`, `REVIEW-PROMPT.md`) no longer exist in the repo. |
| docs/packet/00-CONTEXT.md | DELETE (move 2 lines to CLAUDE.md) | Written for an outside reviewer; its "Success means: NOT STATED" and "History that matters" are planning prose. Keep only the glossary line and "no real paddler or angler has tested it". |
| docs/packet/MANIFEST.md | DELETE | Indexes files that were deleted on 2026-10-21 (PLAN.md, WORK-LIST.md, RISKS-AND-STAGES.md, REVIEW-PROMPT.md, late/, appendix/). |
| docs/packet/calcscrape-history.md | DELETE | About the other site. The one lesson ("judge by Search Console trend after each batch") is one sentence in the master prompt. |
| docs/packet/prompts/PROMPT-1-unanchored.md | DELETE | Strategy pass; owner has decided the product. |
| docs/packet/prompts/PROMPT-2-verify-claims.md | DELETE | Verifies WORK-LIST.md, which is gone. |
| docs/packet/prompts/PROMPT-3-gates-and-process.md | DELETE | Superseded by gates.py and docs/research/GATE-WIRING-AUDIT.md. |
| docs/packet/prompts/PROMPT-4-missions.md | DELETE | Judges `appendix/missions-A-to-L.md`, which is gone. |
| docs/packet/prompts/PROMPT-ALL.md | DELETE | 9-part prompt ending "Next: PART 2"; asks a model to read files that no longer exist. |
| docs/packet/prompts/PROMPT-BUGHUNT.md | MERGE the useful half into REVIEW-1ST.md as an optional "bug hunt" section | Its interaction, data-shape and consistency hunts are the best concrete test list in the repo; it still tells the hunter to test "Set your range", "Save gauge", "Download CSV", all cut. |
| docs/packet/prompts/PROMPT-TEMPLATE.md | DELETE | "Fort Knox" template design prompt; the design review of 10-21 and site.css already did this. |
| graphify-out/GRAPH_REPORT.md | KEEP (generated) | Regenerate after the deletions above; dated 2026-10-20, indexes 165 files including the deleted plan. |
| docs/research/DESIGN-REVIEW-2026-10-21.md | KEEP as the design spec until a shorter one replaces it | Its TILE SPEC and FIRST SCREEN SPEC are what site.css lines 243-262 now implement; the DEFECTS list is half fixed (tile shape, Georgia numerals, dark values done in site.css; "age stated seven ways" and "27 words under a number" are still in render.py LIVE_JS line 1341 and the gage tile). |
| docs/research/FRESH-REVIEW-10-Z.md | KEEP (signed evidence) | The signature in data/reviews.json is tied to it. |

## CONTRADICTIONS

1. CLAUDE.md line 7: "Pre-launch noindex hold: lifted ONLY when the owner says so." vs data/index-allow.json `open: true`, 25 allowed pages, and OPEN-ITEMS DONE "2026-10-21 indexing opened on all 25 gauge pages". The hold is over; the sentence is stale.
2. CLAUDE.md line 42: "The user's global rule to end a substantive turn with 'Next: ...' applies here (an old note in the plan said not to; the global instruction is newer and stronger)." vs the global CLAUDE.md (no such rule) and memory `feedback_no-next-line.md` ("owner 10-20: stop ending replies with Next"). The river file claims a rule that was revoked.
3. CLAUDE.md "Page template (frozen 'final form')": "Tools row: Save gauge, CSV download", "'Your range' last, `MYLV_JS`", "stat tiles ... alerts only when there are none" vs CLAUDE.md line 62 "Cut (owner 2026-10-20): Set your range, Save gauge, CSV download" and render.py (no `MYLV`, no CSV, grep returns nothing). The frozen template is not the built template.
4. CLAUDE.md "Not built yet": "NOAA tide predictions on tidal gauges (cleared, collector not written)" and OPEN-ITEMS B "NOAA CO-OPS tide predictions ... (sources cleared, code not written)" vs collect.py:774 `fetch_tides` and blocks3.py:294 `b_tides`, in `tab_blocks` and in `line0_gate.py` ITEMS ("tide table on a tidal reach").
5. OPEN-ITEMS B "NWS hourly: probabilityOfThunder, relativeHumidity, heatIndex, visibility rows" vs collect.py:575 (`probabilityOfThunder`, `relativeHumidity` fetched) and render.py:1260-1261 ("Thunder %", "Humidity %" rows). Only heatIndex and hourly visibility are missing.
6. OPEN-ITEMS B "Nearest same-river USGS water-temperature sensor when the gauge has none" vs collect.py:790 `fetch_near_wtemp`.
7. CLAUDE.md line 61: "Length is never a reason to cut or fold a Line 0 block; the height budgets only warn." vs gates.py GATE_4 running `tools/review/reader_budget.mjs` and `editor_gate.mjs`, both `process.exit(1)` on `maxNowHeight 5800`, `firstWords 200`, `tileChars 380` (data/ui-budget.json). The budgets block, they do not warn.
8. CLAUDE.md line 35: "the gaps line says what is missing for the gauge so silence never reads as 'fine'" and `line0_gate.py` requiring "Not measured at this gauge: ... water temperature" vs CLAUDE.md line 62 "Cut (owner 2026-10-20): ... the grey missing-data and dam notes." render.py:508 still prints `<p class="gaps">Not measured at this gauge`. One of the two owner lines must lose.
9. CLAUDE.md line 7: "Flood history, ratings and watershed data are detail, after the answer" and the product line "fishing, kayaking, swimming, every water activity" vs PAGE-CONTRACT.md "Safety blocks (a failure fails the gauge)": `b_flood_stages, b_impacts, b_stage_chart, b_crests...` are the only blocks whose failure stops a page; `b_quality` (temperature, turbidity, DO), `b_tides`, `b_air`, `b_hourly` can vanish silently (guard hides them, `BLOCK_ERRORS` logs). The code's definition of "safety" is flood-first; the owner's purpose is water-activity-first.
10. docs/packet/00-CONTEXT.md "Audience. Paddlers, anglers, rafters, tubers, swimmers, boaters, flood watchers" and PROMPT-3 "a data website where a wrong number could mislead someone near a flooding river" vs CLAUDE.md Line 0 (20 reader types, "is it dangerous right now, what is the water like"). The packet frames a flood site; the owner frames a water-activity site.
11. PAGE-CONTRACT.md "truth_tests.py (20 contracts ...)", "truth_types.py (10 gauge-type variants)" vs gates.py "truth contracts (22)" and CLAUDE.md "nine gauge-type variants".
12. CLAUDE.md line 31: "Releasing is slow to undo ... small batches, measure each" and 00-CONTEXT "small cohorts of at most 25 gauges a day" vs OPEN-ITEMS DONE "indexing opened on all 25 gauge pages + site pages" in one apply with no Search Console property verified (OPEN-ITEMS D).
13. editor_gate.mjs line 8 and reader_budget.mjs line 3: "never raise one without writing why in docs/UI-REDESIGN.md" vs no such file (deleted). lib/reviewgate.py line 2 cites docs/REVIEW-PROMPT.md (deleted); tools/open_wave.py:43 and tools/rescore.py:4 cite docs/research/FRESH-REVIEW-PLAN.md (research, reference only).
14. CLAUDE.md line 13 "Do not create planning docs" vs docs/packet/ (11 files of review-packet planning prose) still in the tree and the OPEN-ITEMS rule "add every new gap the same turn it is found", which is how a plan document grows back.
15. CLAUDE.md line 34 "No composed prose or verdicts on data pages. Visible text is a source value with unit and time, a label, or a verbatim source string" vs render.py SAFETY (line 1344): "It shows the readings a person uses to judge whether to fish, paddle, swim, tube or wade today; the judgement is yours." and LIVE_JS: "Flow and gage height at the top updated ... Charts, tables and comparisons below are as of the page build" (composed sentences; the design review counted the age stated seven ways). The rule is right; the code breaks it in the two places that are not blocks.

## UNENFORCED RULES (written, no gate, test or hook refers to them)

- "Study the best competing pages as screenshots, then design; look at every change at 390 px and 1280 px, light and dark, before it ships." (CLAUDE.md Line 0 reader first) and "Look at 3 reference sites before designing", "Any visual change ships with before and after screenshots read by a reviewer" (line 61). Nothing checks that screenshots exist for a template hash.
- "Every mechanical defect a review finds becomes an automated gate the same day." (line 30). No ledger maps review findings to gates; FRESH-REVIEW-10-Z P2 1-13 have no gate.
- "Every feature is tested against a person: a paddler, an angler, a flood watcher, a first-time visitor." (line 22). No fixture, no user test; 00-CONTEXT admits "no real paddler or angler has tested it".
- "a new source adds a gate line the same day" (line 5). `line0_gate.py` ITEMS has 14 lines; sources.json has 23 sources; water velocity, salinity, DO, pH, conductance, pressure trend, moon, tides-on-non-tidal have no item.
- "Each item is ... researched (WebSearch, terms quoted) where the source is not yet cleared" (line 5). Nothing fails when a `pending`/`off` source has no research record (sources.json rows for ridb, hivis, nid say "Terms not read" since 10-16).
- "small batches, measure each, never deploy pages that will stay noindex for weeks" (line 31). open_wave.py takes any N; nothing reads Search Console.
- "Dates move only when the page's own text or data changes" is calcscrape; the river equivalent "`dateModified: iso(G['lt'])`" is code, fine. But "Pull a page the same hour a wrong or stale number is found on it without a label" (INDEXING-RULES) has no timer or test.
- "Never end a session or call the project ready while it lists open items in A to E without naming them" (line 11). The session-start hook prints a count; nothing checks the session end.
- "Percentile ... never presented as a USGS value" (line 39). The word "estimated" is in DISCLAIMER (render.py:16); no test asserts the percentile tile carries it.
- "Owner is a non-coder: ... never ask them to run commands" (line 42) vs RUNBOOK telling the owner to press "Run workflow" and OPEN-ITEMS E listing commands. Not a gate matter, but the docs disagree with the rule.
- "Research originals live in calcscrape docs/research (reference only)" and "No API keys in pages, zips or docs" (line 41): check.py has a secrets scan for pages; nothing scans docs/ or zips.
- PAGE-CONTRACT "The headline comparison judges the latest reading when it differs from the 24 h mean by more than 30%": in code (render.py `basis`), but no fixture named for it in truth_tests (the file's numbered comments are 2, 4, 5, 9).

## UNWRITTEN RULES (in code, in no doc)

- `IGNORED_ALERTS` (Test Message, Administrative Message) are dropped from alert counts (render.py, ALERTS_JS `IG`). Not in CLAUDE.md or PAGE-CONTRACT.
- `b_tides` renders only when `G["osc"]` (flow oscillates within the day) is true (blocks3.py:296): tidal is detected, not declared. The docs call it "tidal reaches" as if a flag exists.
- `merge_charts` folds 7-day, 30-day, 12-month and multi-year into one block with a range switch (render.py:1405); CLAUDE.md's template lists them as four blocks.
- `GROUP_OF` decides the phone tab of a block by id (render.py:1346-1349); the fallback puts a block under the last `SEC:` heading. The "Now / Forecast / History / Data / Area" tabs are not described anywhere.
- `SIDE` set (render.py:1465): related, nearby, NWS point, flood stages, public land, about, map, sun, air observation, official links go to the right column, which on a phone is the "Area" tab, so the air observation (wind, pressure trend) and sunset, both Line 0 items, are off the Now tab on a phone.
- `ADS = False` (render.py:23) and the `"AD"` slot after flood impacts: the page has a reserved ad position; no doc says where ads go.
- Water-temperature tile only if the reading is under 24 h old and the unit is degC (blocks3.py:271-273); air observation only under 12 h; `conditions()` silently drops anything else.
- `fast_fill` and `fast_usgs` (collect.py:951-985): the 30-minute run only refreshes 00060 and 00065; sensors (temperature, turbidity, DO) refresh every 6 h. The page's "Observed" time on the sensor table is honest, but no doc says sensors are up to 6 h behind the flow.
- `collect.py:826` drops `echo`, `openfema`, `storms` from restored caches; FEMA declarations and storm counts are "cut" only here.
- Review signature rules (reviewgate.py) and the "fresh-context Claude subagent (same vendor as the author)" reviewer label in data/reviews.json: the docs say "fresh-brain reader review"; the data says the author's own vendor signs.
- `MAX_GZ = 90000` (check.py:7), `maxNowHeight 5800`, `firstWords 200`, `tileChars 380`, `repeat 2`, `trendRepeat 1` (data/ui-budget.json): hard numeric limits on page length and words that CLAUDE.md says do not exist ("Length is never a reason...").
- `open_wave.py` refuses without a publisher contact unless `data/publisher.json` carries a waiver; the waiver is live ("owner 2026-10-20") and says "add the contact before wave 1". Wave 1 is the next 25 pages and nothing re-checks.

## MISSING FOR WATER USERS

Checked against collect.py CODES (00060 flow, 00065 stage, 00010 water temp, 00300 DO, 63680 turbidity, 00400 pH, 00095 conductance, 99133 nitrate, 00045 rain at gauge, 00055/72255 velocity, 00480 salinity), NWS obs (temp, wind, gust, pressure and trend, visibility), NWS hourly (temp, wind, gust, sky, QPF, thunder, humidity), sun, civil twilight, moon phase, tides, SNOTEL, CPC, WPC, QPF, ACIS, drought, ATTAINS, StreamCat, NID (off), RISE (off), FEMA zone (off), PAD-US, Atlas 14 (off), peaks, crests, impacts, rating, field measurements, NWM. What no block shows:

1. **Ice and sensor qualifiers** (winter waders, anglers, rescue): USGS rows carry `qualifier` (Ice, Eqp, Bkw); collect.py keeps it (line 60), render.py never prints it (only blocks3.py:359 uses peak qualifiers). An "Ice" flow reads as a real number.
2. **Depth and current at the gauge in plain words** (waders, swimmers, rescue, parents): velocity (00055/72255) sits in the sensor table with no "ft/s" context; nothing converts stage to "about X ft deep at the gauge" from the field-measurement table (`b_field_meas` has measured depth and velocity rows; `fetch_fieldmeas` keeps them) and nothing says "2 ft/s is a wading hazard above knee depth". A verbatim USGS field measurement (date, width, mean depth, velocity) on the Now tab answers "how deep, how fast" from data, no verdict.
3. **Cold-water context next to the number**: `tile small.cold` exists (site.css) so a line is shown; no block states the NWS cold-water thresholds (verbatim, attributed) beside air temperature for the combined "water plus air under 120 °F" rule paddlers use. Attributed source text, not advice.
4. **Heat index and hourly visibility** (OPEN-ITEMS B, truly open): NWS gridpoint has `heatIndex`, `visibility`; `grid_hours` keys exclude them.
5. **Dam release schedule and tailwater warning** (anglers, waders, paddlers below Salt, New, Deschutes, Lees Ferry): `fetch_rise` and `fetch_nid` exist; both sources `off` for terms. The page does not even name the controlling dam (FRESH-REVIEW-10-Z P2-5). Naming the dam from NID's public name field needs no release data.
6. **Bacteria and algae advisories** (swimmers, tubers, dogs): no source. State health department beach/river advisories and EPA's BEACON are the public sources; none in sources.json.
7. **Smoke and air quality** (everyone outdoors): AirNow needs a free key (OPEN-ITEMS B); no block.
8. **Access points, ramps, campgrounds** (boaters, campers, guides): OSM and RIDB both `off`. PAD-US public land is shown but is not an access point.
9. **Published runnable or wading range, verbatim** (paddlers, waders): American Whitewater terms not found; link only. The page still prints nothing attributed for the question "what level do people paddle this at".
10. **Hunting and fishing season or regulation link** (hunters, anglers): no state FWP link row (FRESH-REVIEW-10-Z LOSE on Madison).
11. **Lightning in the last hour** (everyone on the water): only the hourly thunder probability; no observed lightning source (NWS has none public at point level; say so on the page).
12. **Streamflow forecast for gauges with no NWS forecast point**: `b_nwm` and `b_nwm_medium` exist; `b_noforecast` says "Not issued"; the NWM short-range guidance for ungauged reaches is the honest fallback and is on the page where the reach id resolves. Fine where present; 11 of 25 pages have neither (not verified this run).
13. **Water temperature by hour (diurnal)**: `b_wtemp` is monthly means; the 00010 series over 7 days is fetched (CODES, P8D) and only the latest value is shown. Anglers want the daily swing.
14. **Flow in a boater's unit**: "cfs" only; no "ft³/s", no m³/s toggle (unit toggle "not built"). Rowers and divers use metres; the metric units rule from calcscrape does not apply here, but a second unit in `<small>` costs nothing.
15. **Gauge photo or camera** (everyone, "what does 4,810 cfs look like"): HIVIS `off`; no hero image. This is the single largest visual gap against American Whitewater and local fly-shop pages.
16. **Rescue and resident items**: NWS impact statements are there (`b_impacts`); flood-crest-versus-next-impact sentence for residents (Z P2 "forecast-crest-versus-next-impact") is not. Bridge users: no road-closure feed (state DOT 511 is public; not in sources.json).
17. **Birders, photographers, students**: nothing is missing for them that is public and per-gauge beyond daylight and moon (both shown). Students: the CSV download that was cut was their one tool; a link to the USGS data endpoint per parameter in `b_official_links` covers it (not verified).

## DELETE

- `docs/packet/` entire folder (11 files): review-packet prose for a zip whose inputs are deleted; `tools/pack_review.py` builds it and should go with it (tools/pack_review.py, whole file).
- CLAUDE.md lines 52-53 "Page template (frozen 'final form')": describes cut tiles and tools; replace with the one-line order in the master prompt.
- CLAUDE.md lines 55-56 "Not built yet": two of nine items are built; the rest are sources.json rows with `status: off` and belong only there.
- CLAUDE.md line 42 sentence "The user's global rule to end a substantive turn with 'Next: ...' applies here ..." : false.
- CLAUDE.md line 8 "This folder is its own project: the car-repair site (calcscrape) rules do not apply here. Inherited on purpose ..." : the global CLAUDE.md applies regardless; the sentence creates the "Next:" confusion.
- docs/PAGE-CONTRACT.md "Who proves it" paragraph and "Adding a new data block" (both restate CLAUDE.md and gates.py).
- docs/OPEN-ITEMS.md B items 1, 2 (thunder, humidity half), 3: already in code (collect.py:774, 575, 790).
- render.py LIVE_JS line 1341: the composed banner "Flow and gage height at the top updated ... Charts, tables and comparisons below are as of the page build" and the appended "The flow above is newer than this comparison" sentence (`nt`): the age chip and per-block Source lines already say it (design review defect 4, still open).
- render.py:1344 SAFETY second sentence "It shows the readings a person uses to judge whether to fish, paddle, swim, tube or wade today; the judgement is yours.": composed prose under the hard rule at CLAUDE.md line 34; the disclaimer link and DISCLAIMER string cover it.
- render.py:508 `<p class="gaps">Not measured at this gauge: ...`: cut by the owner 10-20 (CLAUDE.md line 62) yet still rendered and required by line0_gate.py. Either delete it and change the gate to accept a `data-missing` attribute on the tile row, or keep it and delete the owner line. Decide once.
- lib/render.py `b_sun` block (line 1155): duplicate of the sunset tile (line 502) which already shows sunrise, last light and moon; the block is in `SIDE` and prints the same two times again.
- `tools/demand.py`, `tools/rescore.py`, `tools/gate_plan.py`, `data/waves-report.txt`, `data/backtest.txt`: the release-order formula and its tuned back-test (00-CONTEXT item 4 "not a valid test"); open_wave.py needs only `waves.csv` status and score columns. Keep waves.csv, delete the scoring theatre or mark it reference.
- `tools/review/reader_budget.mjs` and `editor_gate.mjs` numeric "ratchet" comments pointing to docs/UI-REDESIGN.md (deleted): either the budgets are rules (then write them in CLAUDE.md) or the gates are deleted. Given the owner's "length is never a reason", delete `maxNowHeight`, `maxTabHeight`, `firstWords`, `tileChars` from data/ui-budget.json and keep `repeat`, `trendRepeat`, `unitShown` and the detail checks (editor_gate.mjs lines 439-447), which measure defects, not length.
- `dist_prev/`, `dist_preview/`, `legacy/`, `shots/` in the tree: build output and screenshots; confirm .gitignore covers them (not checked).
- graphify-out/: regenerate, do not hand-edit.

## MASTER PROMPT

**riverwaterlevels.com. One static page per USGS river gauge. Government data only (USGS, NOAA/NWS, USDA, EPA). Ad-supported later. Owner is a non-coder and never runs commands.**

**Reader.** A person at or near this river today, on a phone, about to fish, paddle, swim, tube, wade, boat, row, dive, pan, hunt, camp, guide, or who lives, drives or rescues beside it. Flood watchers are one reader among twenty, not the first.

**Every gauge page, in this order, nothing collapsed on the Now tab:**
1. Alert banner (NWS, live) when one is active.
2. H1, gauge id, one age chip ("56 min old"), one observed time. Age is stated once.
3. Tiles: latest flow, gage height (sparklines), is-this-normal (percentile bar, words), 6 h change, NWS forecast high or "Not issued", water temperature, rain 24 h, air (temperature, wind, gusts, pressure trend), sunset (sunrise, last light, moon). Every tile: label, number, unit, one line of at most 7 words, time.
4. What the water is like now: sensors (temperature, turbidity, DO, pH, conductance, salinity, velocity, nitrate, with USGS qualifiers like Ice printed), tides on tidal reaches, hourly weather with thunder and humidity, rain here and upstream.
5. Level, flow and flood risk: 7-day chart with range switch, gage height with flood-stage ladder, NWS impact statements, rate of change.
6. Forecast: NWS river forecast, NWM guidance, rain outlooks.
7. How today compares: 30 days, 12 months, same dates in earlier years, record.
8. Closed folds: flood record, daily values and rating, watershed and land. Right column: upstream/downstream, nearby, NWS point, map, official links, about.

**Never shown:** "safe", "runnable", "fishable" or any verdict; composed sentences other than labels and verbatim attributed source text; a number without unit, time and Source line; a block whose source in `data/sources.json` is not `quoted` or `owner-permission`; a missing source as silence (say "not measured here"); data older than its limit as current.

**How a change ships.** `collect.py` is the only network code; `build.py` reads `cache/` only. Edit, then run `python -I gate.py` once per batch. A template change (`lib/`, `templates/`, `build.py`) needs a fresh-context reviewer answering `docs/REVIEW-1ST.md` and a signed SHIP (`tools/record_review.py`); `gate.py` refuses otherwise. Deploys run only through `.github/workflows/refresh.yml`. "Live" means the page body was read this turn. A rule lives in `gates.py` or it is not a rule; no planning docs; gaps go in `docs/OPEN-ITEMS.md` only with the file or command that proves they are open.

**New data source:** row in `data/sources.json` with quoted terms; fetch in `collect.py`; `python -I tools/gen_cache_shape.py`; one `b_*` block with its four states (valid, valid-empty, unavailable, stale); one line in `tools/line0_gate.py`; new template hash, new review.

**Owner alone decides:** publisher name and contact email; opening or pulling pages from the index; ads and consent; source-permission emails; source terms marked `owner-permission`; cutting any block.
