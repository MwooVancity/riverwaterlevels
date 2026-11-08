# Handoff 2026-11-08c: links, speed, gate audit, practice of every kind

First thing: read the 2026-11-09 11:00 UTC release log (refresh.yml run on main). The first release with lakes and coasts.

## Shipped today (all on main, dry runs "refresh OK")
- Internal links: one grid (`lib/page.py` `link_index`, `nb_pick`, `nb_urls`); nearest page of each other kind both ways; neediest-first reverse lists (US and world, `lib/world.py` `near_rev`); a page whose link set changed is rebuilt the same run (`_built.json` "nb"); census printed in every refresh and gates log. Census: gauge inbound min 3, world min 3.
- Speed: Lighthouse mobile in the dry run (`-f speed="<paths>"`, `tools/lh_line.py`). Analytics loads after the page (gauge page 63-72 to 87). Home map is a static 60 KB `templates/conus.webp` (was a 7-9 s live USGS export).
- Gate audit (fresh reviewer, 12 items): 8 fixed, 6 open (PLAN step 0a).
- Practice of every kind: `tools/release.py --every-kind` in the practice release (nightly and `-f release=true`); collects world feeds. Round 4: all 10 kinds passed. Rounds 1-3 found 10 defects, all fixed (PLAN Numbers).
- Tide prediction pages: fresh re-review PASS; badge names the live neighbour.
- CLAUDE.md trimmed (11.5 to 9.0 KB), new HARD rule: practice every kind.

## Open
- PLAN step 0 and 0a lists.
- Owner: publisher email, Search Console access, sending outreach notes.
