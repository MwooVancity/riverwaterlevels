# Open items (HARD, owner 2026-10-20: "so I never forget we still got stuff")

Run `python -I tools/open_items.py` at session start. A line leaves this file only with proof in the DONE log. Rewritten 2026-10-21 to match the code (fresh-brain docs review); history is in git.

## A. Ship (local commit d4ca4bc, not deployed; owner runs the gates when ready)
- [ ] Template 75e770e9eb52a23c (one design system, tides, nearest water temperature, thunder and humidity, chart unit): `python -I gate.py` once, fix what fails, fresh reviewer (docs/REVIEW-1ST.md, re-verify by resuming the same agent), sign, push, live checks (`_template.txt`, `index_live.py`, one page body).

## B. Wrong-number risks (first after the ship)
- [ ] USGS qualifiers (Ice, Eqp, estimated) are never printed: an iced gauge shows a real-looking number. Print the qualifier on the flow and gage tiles and in the sensor table; a truth contract for it.
- [ ] Water-activity blocks (sensors, tides, air, hourly) are not in `SAFETY_BLOCKS`; when their source fails they vanish without a gaps line. Extend the gaps line to every Line 0 item.
- [ ] Forecast tile still carries two lines of context on some gauges (rating, name mismatch, datum); design says one.

## C. Data still missing for water users (sources: `data/sources.json`)
- [ ] Radar: NWS radar images are public domain; clear the row and restore the block.
- [ ] Regulated gauges: dam name, upstream outflow gauge, schedule link (RISE, CWMS, NID terms unclear; USACE and TVA pages 403).
- [ ] Heat index and visibility rows in the hourly table (fields confirmed in the NWS grid; not yet read in `grid_hours`).
- [ ] Owner keys: USGS HIVIS cameras, Recreation.gov RIDB (ramps, campgrounds), AirNow. Access points (OSM) and bacteria advisories (no national feed) stay held.

## D. Code
- [ ] collect.py (1,100 lines) split into one file per source with its own self-check; no silent failures.
- [ ] render.py (1,560 lines) + blocks2/blocks3 into one file per section; one block registry (id, section, family, reader question, source) feeding the Line 0 gate, Sources panel, credit lines and phone tabs.
- [ ] Credit line from `data/sources.json` rendered automatically under every block of that source.
- [ ] Security headers in templates/_headers (CSP, X-Frame-Options, Permissions-Policy). Privacy page must not claim an analytics script that is not served.
- [ ] Gate 5 (agent) screenshots all pages, not a sample; `gate.py --live` after every deploy in CI.
- [ ] Fixtures: irregular sampling for the 24 h mean; unit allowlist per field; NWS/USGS datum gate; gauge types never exercised on real data (ice-affected, canal, estuary).
- [ ] `tools/pack_review.py` and `docs/packet/` deleted 2026-10-21 (they indexed deleted docs); `graphify-out/` regenerate after the refactor.

## E. Owner only
- [ ] Publisher name and contact email on About (waived in data/publisher.json).
- [ ] Search Console property verified; watch the 25 URLs and site pages after 7, 14, 30 days.
- [ ] Consent banner before any ads; AdSense decision.
- [ ] Outside uptime monitor on /status.json and /_truth.json.
- [ ] Source-permission visits: usace.army.mil (CWMS), tva.com, Recreation.gov terms, NID.
- [ ] Alerts backend (email or push when flow crosses a reader's range).

## F. Prompts and tools (printed by `tools/open_items.py --brief`)
- Review: docs/REVIEW-1ST.md. Sign: `MSYS_NO_PATHCONV=1 python -I tools/record_review.py SHIP docs/research/<report>` (+ `--pages-only --pages=<urls>` for live pages). Gates: `python -I gate.py [--quick] [--live]`.
- Deploy: push to main or `gh workflow run refresh.yml -f mode=fast`; then `python -I tools/index_live.py` and read one live page body.
- Indexing and incidents: docs/RUNBOOK.md. Corrections: docs/CORRECTIONS.md.

## DONE log (date, item, proof)
- 2026-10-19 template review chain S/R/Q/P signed; CI green; live `_template.txt` = signed hash.
- 2026-10-20 block guard + failure isolation + page carried forward; fuzzer 0 failures at 9,354 renders.
- 2026-10-20 refresh.yml invalid YAML since 549c95b fixed; workflow-parse check in tests_logic.py.
- 2026-10-20 editor_gate, live_flow_test, truth_time, reader_budget, line0_gate, agent_gate, index_live in the gate list (gates.py); gate.py one table.
- 2026-10-21 Drought Monitor and ACIS cleared with quoted credit; USGS codes 00045 00055 72255 00480 on pages; NWM "reach None" bug caught by fuzz and fixed; seven planning docs deleted; commit 300303a.
- 2026-10-21 template edd92a4a816f2974 live (curl /_template.txt), signed SHIP on all 25 pages (FRESH-REVIEW-10-Y HOLD, Z SHIP, ZA SHIP); push run 39581344330 success; index_live 0 mismatches.
- 2026-10-21 indexing opened on all 25 gauge pages + site pages (commit 0397846; live index_live: 25 allowed, 0 mismatches; sitemap 49 URLs).
- 2026-10-21 design review vs Lakebrief (docs/research/DESIGN-REVIEW-2026-10-21.md): one design system built (commit d4ca4bc, screenshots read); tides (Hudson: Troy 2.5 mi; Sacramento: Clarksburg 2.9 mi) and nearest water temperature (Gauley: Craigsville 14 mi) seen in cache; thunder and humidity rows in dist_next.
- 2026-10-21 fresh-brain docs review (docs/research/FRESH-BRAIN-DOCS-2026-10-21.md): CLAUDE.md rewritten as the master prompt; INDEXING-RULES merged into RUNBOOK; PAGE-CONTRACT merged into CLAUDE.md; docs/packet and pack_review.py deleted.
