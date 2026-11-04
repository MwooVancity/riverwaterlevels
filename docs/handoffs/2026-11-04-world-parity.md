# Handoff 2026-11-04: world pages to US quality (owner: "do all the items", force it on every non-US page)

Read PLAN.md first. These three sections, all 2026-11-04, hold every open item:
- "Live block audit"
- "Fresh review of the queue release"
- "US vs world parity audit"

Live on main tonight:
- 4f497a4: a failed EA history fetch retries in 7 days.
- 10d579c: Met Office weather for England. Not proven live: no England page yet.
- c18cbb6: a country with no live page opens 2 gauges a day.
- 3f653b8: country and river hubs get a 700-link budget; refresh success 01:31Z.

## Root cause found
`lib/world.py` COVER says "have" for blocks that 0 of 37 live world pages show. Live audit, 2026-11-04 02 UTC:
- b_about and b_nearby: "have" for all three countries, live 0/37.
- b_record: "have" for Canada, live 0.
- b_multiyear: "have" for Canada and England; world_history live 2/37.

`missing()` checks only `owed()`, which never lists those blocks. COVER is therefore a promise nothing enforces.

## 1. The forcing guard (build first, test first)
A `check.py` rule over every world page in dist (not only new ones): each block COVER marks "have" for that page's feed must render with data, by its section id. The exception is when the gauge's own data lacks it; then the page must say "Unknown" with a reason.
- Needs a map from each b_* function to its section id. Read it from the block functions; do not hand-type it.
- A miss fails the page as carryable: the live copy stays and the watchdog names it. Never noindex.
- Fixture: a world page missing about_gauge fails. Then fix the cause so all 37 pass.
- Adversarial pass on every "none:" answer in COVER, because several are dodges:
  - b_rate "the 24 h tile carries it": rate of change is computable from the series, so build it.
  - b_map "map service is USGS only": find an open map with read terms, or a static map from coordinates.
  - b_record for Germany and England: the official marks carry it; confirm the same reader answer.
  - Each surviving "none" needs a reason a reader would accept.

## 2. Fill the gaps (data we already hold)
1. rate_of_change (US 157/162, world 0/37).
2. gauge_map (162/0).
3. about_gauge (162/0).
4. nearby_gauges (162/0; along_river 17/37).
5. record_comparison for Canada.
6. world_history for Canada and England (2/37).
7. flow_chart (US 162, world 23/37: check which Canadian or English gauges have flow but no chart).

Check: US hourly_forecast 0/162 is probably a different block id on US pages; confirm before calling it a gap.

## 3. Tools, from `reports/River page tool gaps.md` and the ChatGPT debate
1. Charts readable by touch (value and time on tap), US and world.
2. A WaterAlert link for this exact gauge. Verify the URL pattern live first.
3. England impact levels ("property flooding possible above X m"). Find the feed and read its terms first.
4. Coverage study before building agency activity limits: 100 top gauges, how many have a published limit, is it permanent, does it match the gauge's reach.

## 4. Then the PLAN.md world gaps, worst first
1. URL collision between gauges whose titles slug alike.
2. Canada time zones (Nunavut, east Quebec).
3. Phone refresh mixing new cm with old feet, change and label.
4. truth_world inside the deploy gate.
5. Per-feed failure counter.
6. World supply from the station lists.
7. Held gauges sent back to the queue after 7 days.
8. World URLs through open_wave.

## Also pending
- After the 11 UTC release adds England's first gauges, read the refresh log line `met <gauge> ... hourly fields [...] daily fields [...]` and one England page.
- The mechanical parity script from the previous handoff becomes part of the forcing guard in item 1.

Rules: one background job at a time; dry run on `check` before main; `/code-review high` once for the batch. Never use a key pasted in chat.
