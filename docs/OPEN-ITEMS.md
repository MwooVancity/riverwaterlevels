# Open items (HARD, owner 2026-10-20: "so I never forget we still got stuff")

Run `python -I tools/open_items.py` at session start. A line leaves this file only with proof in the DONE log. Rewritten 2026-10-21 to match the code (fresh-brain docs review); history is in git.

## A. Ship (local commits d4ca4bc..HEAD, not deployed; owner runs the gates when ready)

## B. Wrong-number risks (first after the ship)
- [ ] CSP is report-only until a live run shows no console errors; then enforce. Privacy page: confirm no analytics claim.

## C. Data still missing for water users (sources: `data/sources.json`)
- [ ] Regulated gauges: dam name, upstream outflow gauge, schedule link (RISE, CWMS, NID terms unclear; USACE and TVA pages 403).
- [ ] Access points (OSM terms) and bacteria advisories (no national feed) stay held. Lees Ferry has no AirNow monitor within reach (declared on the page).

## D. Code
- [ ] Fixtures: irregular sampling for the 24 h mean; unit allowlist per field; NWS/USGS datum gate; gauge types never exercised on real data (ice-affected, canal, estuary).

## E. Owner only
- [ ] Publisher name and contact email on About (waived in data/publisher.json).
- [ ] Search Console property verified; watch the 25 URLs and site pages after 7, 14, 30 days.
- [ ] Consent banner before any ads; AdSense decision.
- [ ] Outside uptime monitor on /status.json and /_truth.json.
- [ ] Source-permission visits: usace.army.mil (CWMS), tva.com, Recreation.gov terms, NID.
- [ ] Alerts backend (email or push when flow crosses a reader's range).

## F. Prompts and tools (printed by `tools/open_items.py --brief`)
- Deploy: push to main or `gh workflow run refresh.yml -f mode=fast`; then `python -I tools/index_live.py` and read one live page body.
- Indexing and incidents: docs/RUNBOOK.md. Corrections: docs/CORRECTIONS.md.

## DONE log (date, item, proof)
- 2026-10-20 block guard + failure isolation + page carried forward; fuzzer 0 failures at 9,354 renders.
- 2026-10-21 Drought Monitor and ACIS cleared with quoted credit; USGS codes 00045 00055 72255 00480 on pages; NWM "reach None" bug caught by fuzz and fixed; seven planning docs deleted; commit 300303a.
- 2026-10-21 indexing opened on all 25 gauge pages + site pages (commit 0397846; live index_live: 25 allowed, 0 mismatches; sitemap 49 URLs).
- 2026-10-21 design review vs Lakebrief (docs/research/DESIGN-REVIEW-2026-10-21.md): one design system built (commit d4ca4bc, screenshots read); tides (Hudson: Troy 2.5 mi; Sacramento: Clarksburg 2.9 mi) and nearest water temperature (Gauley: Craigsville 14 mi) seen in cache; thunder and humidity rows in dist_next.
- 2026-10-21 fresh-brain docs review (docs/research/FRESH-BRAIN-DOCS-2026-10-21.md): CLAUDE.md rewritten as the master prompt; INDEXING-RULES merged into RUNBOOK; PAGE-CONTRACT merged into CLAUDE.md; docs/packet and pack_review.py deleted.
- 2026-10-21 USGS qualifiers printed (values read from the live API: ICE, EQUIP, ESTIMATED, BACKWATER, RATINGDEV, SEASONAL, DISCONTINUED, UNAVAIL; synthetic ICE reading rendered 'USGS flag: ice at the gauge' in the hero; truth contract 23); radar block back (25 pages); heat index and visibility rows; gaps line names rain, air, hourly and tides when missing; Line 0 gate 0 failures.
- 2026-10-21 credit lines from sources.json under every block (seen on Hudson: USGS, NWS, NOAA CO-OPS...); phone-tab registry reduced to six overrides; tidal reach = flow cycle or NOAA station within 10 mi (Hudson now shows tides and the 24 h range); headers: X-Frame-Options DENY, Permissions-Policy, CSP report-only. Commits 598dae4, 3f424a2, ad3ea9a, 6b8fc95.
- 2026-10-21 owner keys: USGS, RIDB, AirNow in .env and GitHub secrets; cameras at 4 gauges, air quality at 24, recreation sites at 15 (dist_next grep); Line 0 gate 0 failures; commits e9c221d, 2599b70.
- 2026-10-21 render.py split into core/hero/charts/weather/forecast/page with a facade; build byte-identical (60 files compared); fuzzer deleted (owner); commits 7a8af88, 41c9bc9. Collector split struck: every source already logs its failure and keeps the previous value.
- 2026-10-21 gates cut to three (owner: overengineered; one template, pages inherit it)
- 2026-10-21 evening: gates cut to three; redesign, tides, cameras, air quality, recreation sites, radar, USGS flags, credit lines, four derived blocks (calm hours, same date last year, gage ft/h, last 20% rise), tinted tiles all LIVE (curl: Potomac shows air_quality, radar, recreation_sites, tides; Delaware shows camera; index_live 25 allowed, 0 mismatches). Alert contract fixed (checks the tile, not the answer sentence); camera API 404 = no camera.
