# Handoff 2026-11-09a: next session starts here

Done this session (all on main, deployed, refresh OK):
- Tide tables (PLAN step 0): 29 tide places with no live NOAA level within 25 km joined the queue as kind 'coast-tables'. Phone review FAIL then PASS (runs 42543656099, 42544780280); variant marked reviewed, so they release by tier in the daily release.
- Site-wide: embed box no longer drawn over block headings; coast meta description and JSON-LD fixed (no 'flow', creator NOAA); the whole local day of tides is in the cache; moon badge; duplicate ramps.
- check.py crashed on any orphan page (fixed); stats_gap lake fixture; truth_live compares water temperature with USGS.

Next, in order:
1. After the 2026-11-09 11:00 UTC release: read its log (refresh.yml on main). Expect the first coast pages (no coast page is live yet: gauges.json had none on 2026-11-09 01:40 UTC). Read one live tide-tables page (/coast/<place>/) and one coast-live page: description, JSON-LD creator, 'Today's tides' whole day, 'No sensor at this station'. Read the CARRIED lines.
2. PLAN open rows: outreach list for the next 20 pages (drawing board 5); score rivers against howsyourriver (3); compare rain, air and NWS forecast numbers with their source (gate audit).
3. Review notes open (minor, site-wide): PAD-US manager 'City' on Bullards Beach State Park; ACIS rain rows show tomorrow as 'not reported'; hourly 'Thunder' header clipped by the scroll fade.

Owner one-clicks unchanged (PLAN drawing board 9 and 4).
