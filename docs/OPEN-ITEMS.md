# Open items (HARD, owner 2026-10-20: "so I never forget we still got stuff")

Run `python -I tools/open_items.py` at session start. A line leaves this file only with proof in the DONE log. Rewritten 2026-10-21 after the planning docs were deleted; everything before that date is in git history.

## A. Ship (blocks indexing)
- [ ] Search Console: watch the 25 URLs and the site pages after 7, 14, 30 days (owner verifies the property first).

## B. Data every river user still lacks (sources cleared, code not written)
- [ ] NOAA CO-OPS tide predictions on tidal gauges (Hudson, Sacramento): nearest station from stations.json?type=tidepredictions, high/low table, credit "Tide predictions: NOAA National Ocean Service, CO-OPS".
- [ ] NWS hourly: probabilityOfThunder, relativeHumidity, heatIndex, visibility rows in the hourly table (fields confirmed in the gridpoint API).
- [ ] Nearest same-river USGS water-temperature sensor when the gauge has none.
- [ ] Flow chart: unit and legend inside the figure; "same hour tomorrow / weekend" row; daily low and high hour line.
- [ ] Regulated gauges (Belva, Thurmond, Millville, Roosevelt): dam name, upstream outflow gauge, schedule link. Source terms still unclear for RISE, CWMS, NID; USACE and TVA pages 403.
- [ ] Owner keys: USGS HIVIS cameras (free signup), Recreation.gov RIDB (ramps, campgrounds), AirNow.

## C. Code
- [ ] collect.py (1,045 lines) split into one file per source with its own self-check; no silent failures.
- [ ] render.py (1,555 lines) + blocks2/blocks3 into one file per section; one block registry (id, section, family, reader question, source) feeding Line 0 gate, Sources panel, credit lines and phone tabs.
- [ ] Credit line from data/sources.json rendered automatically under every block of that source.
- [ ] Security headers in templates/_headers (CSP, X-Frame-Options, Permissions-Policy). Privacy page must not claim an analytics script that is not served.
- [ ] Gate 5 (agent) screenshots all pages, not a sample; gate.py --live after every deploy in CI.
- [ ] Fixtures: irregular sampling for the 24 h mean; unit allowlist per field; NWS/USGS datum gate.
- [ ] Gauge types never exercised on real data: ice-affected, canal, estuary.
- [ ] Review signature is forgeable by anyone with the repo (hash of report + hash); acceptable while one person deploys.

## D. Owner only
- [ ] Publisher name and contact email on About (waived for wave 0 in data/publisher.json).
- [ ] Search Console property verified.
- [ ] Consent banner before any ads; AdSense decision.
- [ ] Outside uptime monitor on /status.json and /_truth.json.
- [ ] Source-permission visits: usace.army.mil (CWMS), tva.com, Recreation.gov terms, NID.
- [ ] Alerts backend (email or push when flow crosses a reader's range).

## E. Prompts and tools (printed by `tools/open_items.py --brief`)
- Review: docs/REVIEW-1ST.md. Sign: `MSYS_NO_PATHCONV=1 python -I tools/record_review.py SHIP docs/research/<report>` (+ `--pages-only --pages=<urls>` for live pages). Gates: `python -I gate.py [--quick] [--live]`.
- Deploy: push to main (workflow runs on push and schedule) or `gh workflow run refresh.yml -f mode=fast`; then `python -I tools/index_live.py` and read one live page body.
- Indexing: docs/INDEXING-RULES.md. Alerts: docs/RUNBOOK.md. Corrections: docs/CORRECTIONS.md.

## DONE log (date, item, proof)
- 2026-10-19 template review chain S/R/Q/P signed; CI green; live `_template.txt` = signed hash.
- 2026-10-20 block guard + failure isolation + page carried forward; fuzzer 0 failures at 9,354 renders.
- 2026-10-20 refresh.yml invalid YAML since 549c95b fixed; workflow-parse check in tests_logic.py.
- 2026-10-20 editor_gate, live_flow_test, truth_time, reader_budget, line0_gate, agent_gate, index_live in the gate list (gates.py); gate.py one table.
- 2026-10-20 wave 0: 9 pages indexable live (index_live 0 mismatches); 15 more signed under FRESH-REVIEW-10-W.
- 2026-10-21 Drought Monitor and ACIS cleared with quoted credit (data/sources.json); USGS codes 00045 00055 72255 00480 on pages (4 rain, 2 velocity, 1 salinity seen in dist_next); NWM "reach None" bug caught by fuzz and fixed (9,048 renders, 0 failures); gate.py --quick green except the unsigned template; seven planning docs deleted; commit 300303a.
- 2026-10-21 template edd92a4a816f2974 live (curl /_template.txt), signed SHIP on all 25 pages (FRESH-REVIEW-10-Y HOLD, Z SHIP, ZA SHIP); reviewer P1s fixed (pills kept and dated after a live check, full NWS impact sentence on the gage tile, crest-below-reading labelled as a forecast fall); push run 39581344330 success; index_live 0 mismatches.
- 2026-10-21 indexing opened on all 25 gauge pages + site pages (commit 0397846, open_wave 25 --apply).
