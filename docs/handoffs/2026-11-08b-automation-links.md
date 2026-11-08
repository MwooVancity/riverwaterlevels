# Handoff 2026-11-08 (b): fully automatic release, links, tide pages

Start: "read docs/handoffs/2026-11-08b-automation-links.md and continue". Owner: execute PLAN.md without stopping; drawing board first (CLAUDE.md).

## State (16:20 UTC 2026-11-08)
- main = check 8ae0657, deployed, refresh OK, index_live 216 pages 0 mismatches.
- Releases 11-07 and 11-08 shipped nothing (11-08: truth_live could not read "USGS lake gauge" on 11 reviewed lakes, over the old 10-page cap, so all 20 picks were undone). Fixed: id pattern (ea4f55a), no count cap (3d347ef).
- FIRST next session: read the 2026-11-09 11:00 UTC release (sharded.yml / refresh.yml log "release committed" or "release DROPPED"); expect 25 lakes and coasts (tier 50K first: Canyon, Choke Canyon, Kerr, Corpus Christi, Hartwell, Lanier, Mead...). Then census live links (PLAN Drawing board 6) and home title (names lakes and tides once they are live).

## Built today
- Fully automatic a-e (PLAN step): per-page carry or send-back; review per template variant (lib/pages.py variant, data/reviewed.json variants: lake-usgs, lake-agency, coast-live, coast-prediction); cloud review shots (`gh workflow run dryrun.yml --ref check -f review="<ids>"`, artifact `review`); coast_match --apply before each release; watchdog alarm after 2 days via data/last-success.txt.
- Owner rules: no duplicate or thin gate (near_dupes deleted by agent 69bd03c; open_wave block/years gates; check.py FLOOR off for water pages; world thin = no reading only).
- Links: world nearby at any distance; few_neighbours warning; CLAUDE.md link rules 1-7; home lists lakes and coasts.
- Backlinks: per-page embed code with a visible plain link (lib/page.py embed_snippet); data/outreach.csv 16 named orgs for 5 lakes; owner note in PLAN.
- Tide prediction pages (9): level_from, nearby station named, review blockers fixed, truth_live next high/low vs NOAA hilo.
- Trust: /contact/ + footer link appear once data/publisher.json has an email (owner).

## Open (in PLAN Drawing board, worst first)
- Links: outreach list for the next 20 pages; owner sends.
- Intent: SERP top 50 money keywords (not measured for rivers).
- Proof: owner exports Search Console weekly (last read 10-20..10-29: 359 impressions, 1 click).
- Experience: Core Web Vitals unmeasured (PageSpeed API quota); Lighthouse in the cloud dry run.
- Link rules 3 (up/downstream named), 4 (inbound 3+), 5 (neighbour rebuild on change) not built.
- CLAUDE.md ~11 KB, over its 8 KB cap.

## Lessons
- A heredoc turned "\n" inside a Python string into a real newline (lib/directory.py): use Edit for code strings.
- Every push to `check` cancels the running dry run: batch commits, push once, wait.
- Laptop partial builds give false failures (links 2 of 3, home 'thin', German flows): judge only the cloud dry run.
