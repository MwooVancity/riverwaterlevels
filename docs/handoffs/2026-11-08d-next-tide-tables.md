# Handoff 2026-11-08d: next session starts here

1. Read the 2026-11-09 11:00 UTC release (refresh.yml on main): first unattended lakes and coasts, plus 9 new tide places (Savannah 5K). Log lines now show truth summaries, FAULT, CARRIED and census in every run.
2. Build PLAN step 0 "tide tables" (spec and edge cases are there): about 19 SERP-proven US tide keywords with no live NOAA level within 25 km. Code path: collect.py fetch_coops (raises on no water level), lib/hero.py ctx (requires USGS rows), lib/page.py coast swaps, check.py observed-time rule, tools/truth_live.py coast loop (hilo-only check), lib/pages.py variant 'coast-tables', coast_match.py pred_pick (level_km rule becomes optional for this kind). New variant: one cloud phone review before release (`gh workflow run dryrun.yml --ref check -f review="<ids>"`), and the practice adds it automatically (`--every-kind`).
3. Then PLAN open rows in order: outreach list for the next 20 pages (drawing board 5), score rivers against howsyourriver (3), stats_gap lake fixture, compare water temperature, rain, air and forecast numbers with their source (gate audit open list).

Fixed late 2026-11-08 from the deploy log: Idaho zone false hold, Animas 'None on record' held for days, Canada alert check too loose (James River's carried copy showed an ended warning). Lesson: every carried page is a possible stale or false page; read the CARRIED lines after each deploy and fix the cause the same day.

Owner one-clicks (PLAN drawing board 9 and 4): add velocity-engine@asmr-directory-497009.iam.gserviceaccount.com to Search Console (Restricted) and GA4 (Viewer); publisher email; send outreach notes.
