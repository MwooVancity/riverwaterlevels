# Handoff 2026-11-09b: next session starts here

Done this session (all on main, deployed, refresh OK, read live):
- Search Console + GA4 readable: `python -I tools/gsc_read.py 28` (service account added by Claude in the owner's Chrome; GA4 property 561723165; Analytics Data API enabled). ChatGPT sends 5x more visits than Google.
- Helpful-content review, 8 Google patents, master edge-case list: PLAN.md sections "Helpful-content review 2026-11-09" and "Master edge-case list".
- Depth answer from USGS channel measurements on 216 of 216 river pages ("About 14 ft deep on average at a flow like today's").
- Master prompt for fixing data at the source: `tools/source_fix.md` (steps, edge-case table, pictures rule, calm page rules). CLAUDE.md points to it.
- Pictures: only series the source publishes. Tile flood bar, forecast curve and depth dots were built, then removed (owner). Tile 24 h lines kept; the Worker moves their end dot to the live reading.
- Calm page (owner: ADHD and autistic readers): tiles show number, line and one line; the rest behind "More"; safety words and reading times never fold; reduced motion; colour labels 4.5:1 (check.py colour_contrast); no control bytes in code (check.py control_chars).
- truth_live now compares every tile number with its source each run: flow, stage, water temp, air (209 pages), river forecast (123), rain (153); 0 mismatches.
- Fixed at the source: pegelonline series vs current (Wuerzburg), NWS flood stage 0, ACIS tomorrow column, channel measurement distance/side channel.
- Outreach list: 50 rows for the next 20 lakes in data/outreach.csv.

- Readable tables (PLAN 0g): census 966 -> 0 wide tables, now a page rule; hourly like the Weather Channel.
- Namesake rule from GeoNames in coast_match; review shots open toggles and the hourly grid.

Next, in order:
1. First-screen rule (PLAN 0g open): first phone screen = place, one plain status sentence, the number; a check for it.
2. Read the 11:00 UTC release (first coast and tide-table pages): log, one live page of each, CARRIED lines.
3. Plain-words pass on tile first lines; truth_live parses the derived NWS stage sentences, so change both together.
4. Namesake rule for lake rows (needs a lake gazetteer, not towns); gate catch census.
(Done since the first draft: rain label, Thunder header, refresh run time measured, coast namesake rule.)

Owner only: Cloudflare > riverwaterlevels.com > Email Routing > Settings > "Add missing records" (contact@ forwarding; Claude's click was blocked). Then Claude sets data/publisher.json email. Send outreach notes.
