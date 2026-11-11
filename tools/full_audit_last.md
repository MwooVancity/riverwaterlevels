# Full audit, 2026-11-10 (tools/full_audit.md; 8 fresh reviewers plus architecture walk)
Ranked: reader harm first, then money, then owner time. V = checked live by Claude in the merge step. Each finding is one line.

## Readers misled or at risk
1. V FIX Coast pages miss marine warnings: Astoria says "No active NWS alerts" while PZZ210 (Columbia River Bar) has a Gale Warning and a Hazardous Seas Warning. Cause: alerts are fetched only for the land point (collect.py:798).
2. V FIX Dam-release river called "Tidal reach" and shown a tide table: /river/cowlitz-river/kosmos/. lib/hero.py:79 uses "daily swing plus a tide station within 50 mi"; the 12.4 h tide test lives at lib/wx.py:184, world pages only.
3. V FIX "Same day last year" on the wrong day on nearly every US flow page: Nehalem shows Nov 4, 2025 while USGS has Nov 10, 2025 (2,280 cfs). lib/hero.py:449, 613-631 cut the window at this year's newest daily value.
4. V FIX "USGS publishes no storage for this lake" is false for Lanier and Allatoona: 72036 is never requested (collect.py:13; sentence at lib/hero.py:360).
5. FIX Gage height tile mixes two zero points (USGS 1.66 ft next to NWS action stage 72.5 ft, Baxley). Show the flood stages on the USGS scale; the page already knows the offset.
6. FIX The top of the page jumps when the live reading is newer than the page, or an alert is inserted; the HTML and live-sites.json come from different builds.
7. FIX No plain one-line status at the top (chips only); drainage area takes space on the first screen.
8. FIX Lake: an empty Storage tile first; water temperature missing with no word; no full pool, which is what lake searchers check.
9. FIX Rhine tile shows the BfG "Estimate" as "Highest in the forecast"; the record-low claim is unverified against WSV.
10. FIX The coast chart source line names a blank NWS forecast point for a NOAA tide prediction.
11. SIMPLIFY "1,193 dams upstream" is our own math with no source named; the "before these 7 days" sentence reads backwards.

## Checks that would let wrong numbers through
12. V FIX Hourly live MISMATCH lines (5 today, e.g. Strasburg water temperature 55 vs 53.8 °F) never reach the dashboard: truth_live runs outside watchdog-out.txt (watchdog.yml:55), and the step goes red while the run shows green.
13. FIX No check reads "not published" claims, our own derived numbers (percentile, changes, last year, tidal label, nearby water temperature) or the clock text shown to readers; a 1 h daylight-saving slip passes (lib/wx.py:374, truth_live.py:337).
14. FIX truth_world passes a page it cannot read (`ok = not shown or`, truth_world.py:41/90/111).
15. FIX "Next tide" can already be in the past on a carried page; nothing checks that it is still ahead.
16. FIX Stuck-sensor test only fires on 6+ days of identical values (lib/wx.py:379).
17. FIX The terms check almost never fires: 35 of the 42 sources shown on pages never stated whether ads, commercial use and caching are allowed (check.py:452). The openfema, RIDB and AirNow terms were never read in a browser.
18. FIX The page secret scan skips METOFFICE_SITE_KEY, GSC_KEY_JSON and private-key blocks (check.py:1299-1304).

## Money and Google
19. FIX About 28% of sitemap pages are still out of Google's index, from the pre-launch noindex crawl of 10-17 (27 of 96 sampled). Put the reindex queue in Inspection-state order, noindex first.
20. FIX Lake Michigan (50K searches, the top row) is held on a phone review nobody owns; the lake-great variant is not in reviewed.json.
21. FIX Releases shipped nothing on 3 of the last 4 days (about 75 pages lost).
22. OWNER No contact address (publisher.json email empty, /contact/ 404, no MX records): blocks AdSense approval. One Cloudflare click (Email Routing).
23. FIX RATE has no imi (Ireland ranks at 0.1, not 0.8); real bid_high_cad in keyword-tiers-water.csv is unused (tools/release.py:88).
24. FIX Live noindexed /lake/barren-river-lake/ is linked from the home page and from Bowling Green (link rule 5); add a check.py rule.
25. FIX World gauge pages carry only a breadcrumb in their structured data; no WebSite markup on home.
26. FIX Georgia hub lists no lakes; hubs must list every child.
27. SIMPLIFY Coast titles up to 121 characters; "Saint" where searchers type "St." (data/name-overrides.csv).
28. FIX index_inspect.py: serial, 6.4 s a URL, no timeout; 14,000 pages = 25 h. Run it in parallel, in daily slices.

## Machinery (runs alone for weeks)
29. FIX The USGS key (1,000 an hour, about 180-280 used at 241 gauges) is the first limit: the release brake (fewer than 300 left) stalls growth near 700-1,000 US gauges (projection).
30. FIX The Worker parses all of live-sites.json on every request: 10 ms CPU breaks at about 1,500-3,000 gauges. Look up one gauge per request.
31. FIX "data cache lost" alarm can never fire (CACHE_MATCHED is set only in the refresh.yml job, which is skipped).
32. FIX The Cloudflare load guard is blind (the key lacks Account Analytics Read, OWNER click) and passes when empty; it must skip instead.
33. FIX The owner alarm in watchdog.py:254 is dead code; CLAUDE.md says "alarms at most twice a day". Settle it one way.
34. DELETE The single-job release path in refresh.yml (the copy that never runs; today's bug). Then the unused sharded.yml inputs.
35. SIMPLIFY check.py --carry runs twice a refresh (gates and publish.py); about 40 min a run at 14,000 pages.
36. SIMPLIFY Every shard uploads shard 0's world files: 20 x 10 MB artifacts and about 600 NOTE lines that bury real warnings.
37. FIX Shard 0 holds every world feed (553 s against 90-180 s); the ledger projects it by US pages.
38. FIX 22 standing watchdog problems, mostly noise (coops "never worked").
39. SIMPLIFY Duplicate scheduled runs; the watchdog runs twice an hour; 20 shards fill GitHub's 20-job cap.
40. FIX The release brake adds the worst runs of 24 h (possibly two different runs) and treats an unreadable status.json as 0 min.
41. FIX The Worker has no observability; poll errors are swallowed.
42. FIX The topo map is a 217 KB image from nationalmap.gov on every view; render it once in the cloud. conus.webp has max-age=0.
43. FIX Lake, world and home pages have no speed test after 11-08.
44. DECIDE The repo is public, so the "private" dashboard is public (no secrets on it). Private costs Actions minutes (about 20 shards an hour); reword the rule or move the dashboard.

## Code shape
45. FIX The self-test runs twice per gate: edge_tests imports check.py, which has no `__main__` guard (check.py:1399).
46. SIMPLIFY The carry rule is written 4 times with different limits (check, truth_live, truth_world, truth_tests); two copies skip keep_old_times.
47. SIMPLIFY check.py is loaded by exec in 5 places; make it a module.
48. SIMPLIFY A source's fetch cadence lives in collect.py and in watchdog SLOW (today's false cdec_res alarm).
49. DELETE tools/quarter/ (417 lines, one-off), render_test.mjs, default_sites(), tint(); the 4 haversines become 1; esc_ui becomes html.escape.
50. SIMPLIFY PLAN.md is 73 KB (35 items DONE or CLOSED; move them to plan-history); CLAUDE.md is 12.5 KB against about 8; index_live.py is described as automatic but nothing runs it.

## KEEP (passed)
Readings, times and units right on all 15 sampled pages; sitemap, canonical and robots agree; no doorway pairs; no keys leaked; no cloaking; tables at 5 columns or fewer; no verdict words; page weight 13-54 KB of 90.
