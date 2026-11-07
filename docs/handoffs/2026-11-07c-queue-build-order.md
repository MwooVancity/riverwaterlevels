# Handoff 2026-11-07 (c): three agency lakes done, next: build what the top queue rows need

Start: "read docs/handoffs/2026-11-07c-queue-build-order.md and continue". Owner: keep executing PLAN.md without stopping (memory feedback_keep-executing).

## State (all pushed; last dry run watched: 42328943495 on ff3c094; if not "refresh OK", read its log first)
- Shasta (CDEC-SHA), Mead (RISE-6123), Travis (TWDB-travis) built and queued; world-queue rows 14/16/19 linked. Today's 25 = 14 pages at 10K-100K + 11 at 1K-10K (25 lakes and coasts), simulated 2026-11-07.
- Watchdog never emails now (owner 2026-11-07: no failure emails): alarm steps removed from watchdog.yml. GitHub may still email on a real refresh failure: owner can switch Actions emails off in GitHub notification settings (owner-only).
- After 11:00 UTC release: read /lake/shasta-lake/, /lake/lake-mead/, /lake/lake-travis/ live vs agency, screenshots at phone width, waves.csv gate column for anything sent back.

## Next: build in queue order what rows need (259 rows at 1K+ have no page)
Top unbuilt (rank, tier, keyword, need):
- 12 50000 texas lake levels: hub exists (/lakes/tx/); link the row (gauge column) so it counts as built.
- 13 50000 bore tides: Alaska Turnagain Arm, NOAA CO-OPS Anchorage? read first; may be not a place page.
- 15 50000 lake michigan water temp: Great Lakes source (NOAA GLERL/CO-OPS), PLAN item.
- 17/18 50000 plymouth / portsmouth tide times: UK, waits UKHO predictions (owner key).
- 31+ 5000: river trent level (England EA), many US tide stations (anchorage, astoria, avalon, bandon, bar harbor, barnstable...) = coasts.csv rows on the existing CO-OPS path (cheapest: one row each), lakes (allatoona, amistad, barren river) = USGS lake path or agency feed.
Cheapest win: add coasts.csv rows for every 1K+ US tide keyword with a CO-OPS station (script the match: nearest station with water level), then lakes on USGS lake codes.

## Lessons
- Heredoc python with backslashes broke collect.py twice: use Edit only.
- `cmd | tail -1 && git commit` hides a failing selftest: capture the exit code.
