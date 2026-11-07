# Handoff 2026-11-07: keyword runs, titles, block order, Texas hub, one money queue

## Done this session (proof in PLAN.md "KEYWORD PLANNER US 2026-11-06")
- Keyword Planner US, 2 batches (788 phrasings, ranges only: no monthly values without a running campaign). 403 new rows in data/keyword-tiers-water.csv.
- Titles name water temperature only while the tile shows a fresh reading (live: Au Sable River at Mio, 52.3 F). Coast titles add "tide chart".
- Block order follows searches: coasts lead with tide chart, tide table, waves; lakes with storage then level chart (live with the 2026-11-07 release).
- /lakes/tx/ Texas lake levels hub (TWDB, 122 reservoirs), phone-checked. First deploy was 404: the sharded merge did not copy cache/twdb-texas.json (fixed 858a77a). CONFIRM LIVE FIRST (see below).
- Dead-link fix: /rivers/tx/ links the hub only when it was built.
- England edge test fixed (failed after midnight UTC; fixture only).
- tools/world_queue.py: one money list over rivers, lakes, coasts and state hubs (commit 2642c86, laptop only until pushed).
- Memory: build only the next queue row (feedback_queue-decides).

## First thing next session
1. If 2642c86 and the PLAN commits are not on origin/check: `git push origin check`, read dry run "refresh OK", push main.
2. Read https://riverwaterlevels.com/lakes/tx/ : title "Texas lake levels today", Lake Travis row equals TWDB recent-conditions.json. Read /rivers/tx/ has the link.
3. Read one live /lake/ and one /coast/ page after the 2026-11-07 11:00 UTC release (22 queued); status.json 0 failed; data/open-wave-last.json stuck empty.

## Open, in order (the queue decides)
1. Daily-agency lake pages: Lake Mead (RISE 6123), Lake Travis (TWDB), Shasta (CDEC SHA). Full design and failure list: PLAN.md "NEXT BUILD: daily-agency lake pages".
2. Hub generator (PLAN "SITE STRUCTURE AT FULL SCALE"): replace hand-wired /lakes/tx/ before a second state; HUBS_BUILT in world_queue.py goes with it.
3. World URLs to country silos (/rhine/x/ -> /de/rhine/x/, 44 pages, 301s).
4. Surf report (1K-10K at 6 coasts): NDBC NOAA-owned buoys only.
5. Earlier list: hand-check multi-state river names, coast leftovers (Port Angeles AQ label), Great Lakes source.

## Lessons
- Heredoc python wrote invisible backspace characters into a regex (\b became \x08): use Edit for any backslash.
- The cloud build is sharded: any new cache file must be added to the merge copy list in .github/workflows/sharded.yml.
- A dry run has no fresh collect: a page built from a new feed will not appear there; prove it on the live deploy.
- docs/research/priority/picks.csv is gitignored; release reads tiers from data/world-queue.csv (committed).
