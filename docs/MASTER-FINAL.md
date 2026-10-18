# River Water Levels: master prompt for the final page set (2026-10-17)

Read first: `docs/PLAN.md`, `CLAUDE.md`. This file is the single contract for what a finished gauge page set contains and what is deliberately left out. A block not listed here is not part of the product. A block listed under "Not built" has a stated reason; reopen it only when the reason is gone.

## Rules every block obeys
Government API data only. No composed prose or verdicts (caveat and legal labels only). Every block carries a Source line that names the dataset, the period or issue time and the fetch time in the gauge's local zone. A block renders only when its source row in `data/sources.json` is `quoted` or `owner-permission`. A block with no data for a gauge returns None. Freshness limits: flow over 24 h old shows the not-reporting notice; forecast amber after 24 h and hidden after 72 h; observations 3 h / 12 h; rain 6 h / 24 h; alerts 3 h; SNOTEL 5 d; CPC 3 d. The gauge-local zone is the zone USGS publishes for the monitoring location.

## Page set per gauge
Dashboard `/river/<river>/<place>/`: offline notice, NWS alerts (county names with state codes, capped at 6 areas), 7-day flow chart with percentile band, gage height chart with NWS flood stages and forecast, gauge location (USGS Topo) beside radar, weather forecast, public land (PAD-US), about this gauge.
Water `/water/`: 7-day chart, rate of rise and fall (hidden at tidal gauges), last 30 days, last 12 months, daily mean flow, same 50 days in earlier years, record comparison, largest annual peaks with decade medians, flood-frequency peak flows (hidden when regulated or when USGS publishes conflicting preferred sets), historic crests (NWS), field measurements, flood events by county or city (NCEI, 10 years), federal flood declarations (OpenFEMA), rating curve, snowpack (SNOTEL, west), water temperature by month, water quality, upstream and downstream gauges with observed lag (only where empirical lag is strong), NWS flood stages, NWS forecast point (upstream and downstream points link to our page when the gauge is on the site), long-range flood outlook, flood impacts, EPA assessments and watershed characteristics, dams and flood zones (hidden until terms are read).
Forecast `/forecast/`: river forecast table, National Water Model guidance (where NWS issues no forecast), rain totals (RFC QPE with valid-through times), forecast rain (gridpoint QPF), 6 to 10 and 8 to 14 day outlooks, hourly heatmap, weather, observations, sun times; ACIS, Atlas 14 and Drought Monitor hidden until terms are read.
Site level: home (national map, near-me, search and filters that drive the all-gauges table and the state list, sortable all-gauges table), state pages, 301 redirects for single-gauge river hubs, trust pages (about, methodology, data sources, privacy, disclaimer, FAQ, glossary), Save gauge, CSV download, print CSS, dark mode, phone layout at 390 px.

## Not built, with the reason (do not add without clearing the reason)
- Unit toggle (metric): tables and chart labels mix units inside text; a partial toggle would show mixed units on one page.
- NOHRSC snow depth and water equivalent: the map service's pixel units are not documented in the service; a value without a verified unit is worse than none.
- Local Storm Reports: the only machine-readable feed found is not a government host.
- WPC significant river flood outlook, CatFIM extent maps, monthly precipitation normals: no verified endpoint and terms quote yet.
- Years in the record with a peak above flood stage: NWS and USGS peak stages can be on different datums.
- Embed widget, email alerts, hero photos: no product reason, extra legal surface.
- Lakes and reservoirs: owner scope decision (site is rivers and creeks).
- Water Quality Portal, CWMS, StreamStats basin delineation: no reader question not already answered.

## Acceptance (all must hold in the same turn, on the live site)
`python -I build.py`, `check.py`, `tests.py`, `node render_test.mjs`, `node js_test.mjs` pass; deploy with `python -I refresh.py --fast`; live fetch shows the changed content; both scheduled tasks Enabled; screenshots at 1280 and 390 (light and dark) were looked at, not only scanned; one fresh reviewer who has not seen earlier reports finds no P0 or P1.

## Owner-only before launch
Contact email; Cloudflare Always Use HTTPS and www redirect; remove the pre-launch `noindex` rules in `templates/_headers`; re-read the OpenFEMA, NCEI and EPA terms; decide on the hidden sources; AdSense account; keep the PC logged in for the refresh tasks.
