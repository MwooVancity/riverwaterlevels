# Handoff 2026-11-07 (b): agency lakes Shasta + Mead, deploy safety

## Done (all on main, dry runs "refresh OK")
- c832a18 watchdog: world-wx counts successes; monthly world-normals/world-access judged on 750 h (live _health: 85 ok / 1 failed).
- 61ac8ba agency-lake path: lakes.csv `source` column; collect.py AGENCY/NOUSGS/fetch_agency; fetch_cdec (CDEC SHA hourly, PST all year); lib/common.py AGENCIES (label, src, every); lake code "AGY"; page.py agency_words (no USGS on the reading lines; PAD-US and Topo keep USGS); check.py foreign_usgs (+fixture); truth_live operator branch; live-sites.json numeric ids only (Worker USGS poll).
- e789848 Lake Mead: fetch_rise (RISE 6123 daily, UTC); daily feeds "not reporting" only past 96 h (hero.py); storage 6124 held (unit 'af' but 6,904); truth_live carries failing /lake/ and /coast/ pages too (was /river/ only: one lake mismatch stopped every deploy).
- sources.json: cdec row (owner read live DWR terms 2026-11-07: disclaimer only); usbr row ads/commercial/cache allowed.
- waves.csv: CDEC-SHA and RISE-6123 queued.

## First thing next session
1. After the 11:00 UTC release: read https://riverwaterlevels.com/lake/shasta-lake/ and /lake/lake-mead/ (title, value vs CDEC/RISE, "CDEC station SHA" / "Reclamation RISE item 6123", 3+ nearby links, no "USGS CDEC-" text). If gated back to queue, read waves.csv gate column.
2. Phone screenshots of both (tools/hater_sample.py, node tools/hater_shots.mjs) before open_wave.

## Next builds (queue order)
1. Lake Travis: TWDB individual file is date only (no time). Needs a date-only reading line ("TWDB daily estimate for Nov 6"), never a made-up time. Add twdb to AGENCIES/fetch_agency; truth_live branch.
2. Info gain on Shasta/Mead vs Lakebrief: CDEC capacity (4,552,000 AF) and % of historical average; Mead full pool from Reclamation, read first.
3. Hub generator, world URL silos, surf report (PLAN.md).

## Owner decision pending
Daily scheduled Claude routine to read GitHub failures + watchdog and fix code (costs tokens daily). Asked 2026-11-07, no answer yet.

## Lessons
- Heredoc python with regex backslashes warns/breaks: use Edit (happened again this session; caught, line was correct).
- Local gates fail on a stale laptop cache; the dry run is the proof.
