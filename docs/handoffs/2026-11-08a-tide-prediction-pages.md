# Handoff 2026-11-08 (a): tide prediction pages

Start: "read docs/handoffs/2026-11-08a-tide-prediction-pages.md and continue". Owner: keep executing, everything, no stopping.

## State (02:30 UTC 2026-11-08)
- main = check a4299ba: live 340 pages, 0 failed. Today's changes live: neg_zero rule + tide tiles round first; Moon "No moonrise today"; release runs the near-duplicate rule per pick (f1ae97c, twin test sent back at 100%).
- FIRST: read 03:10 practice run (`gh run list --workflow dryrun.yml -L 3`, log "practice:" / "practice gates committed") and 11:00 release (refresh.yml / sharded.yml log "release committed"). Release now also runs near_dupes over all of dist_next: watch its run time and any "near-duplicate of" send-backs.

## Decided (PLAN.md item 7 lines on 'prediction-only')
- Owner: prediction-only tide pages ship (CLAUDE.md ship test amended). Debates (3 fresh agents): ship a strict subset; 80% numbers-included rule kept; tide own-page rule = NOAA offsets vs live tide pages within 10 km, >=15 min or >=max(0.3 ft, 10% of mean range), else a 'nearby stations' row.
- Measured: subordinate stations answer interval=hilo only (interval=6 -> "No Predictions data was found"). 59 tide keywords at 1K+ match ONE prediction-only station; 13 pass reference-first + live level within 25 km.
- Foreign namesakes (kinsale=IE, botany bay=AU, dungeness=GB) beat lists and gazetteers (GeoNames cities500 tried: flags Corpus Christi/PY, Clearwater/CA, misses Botany Bay, Dungeness). Rule: a prediction-only keyword ships only when hand-picked with SERP evidence. A fresh agent was checking all 59 by web search: scratchpad tide59_serp.csv (session scratchpad; if lost, re-run: list in scratchpad tide59.csv / pred_all.py, or redo with tools/coast_match.py logic).

## Design (not built)
- Page = the station's OWN NOAA hilo predictions + ONE real reading: the nearest NOAA live water-level station within 25 km, its name and distance on the hero ("Water level at <station>, N km away"). Reuses the coast pipeline: data/coasts.csv new column `level_from` (nearby water-level id); collect.py fetch_coops(level_from) for rows/pred/water temp; own station hilo only (weekly is enough; predictions do not change).
- Anomaly tile compares the nearby station's reading with the NEARBY station's predictions, labelled with its place, never the page's place.
- Subordinate pages name their reference station; reference stations first; subordinate only if no reference within 10 km.
- Gates to add with fixtures: check.py prediction-only page without a real reading within 25 km fails; tide own-page offset rule; truth_live compares next high/low vs NOAA hilo; break_blocks sample 'coast prediction-only'.
- Picks: data/keyword-picks.csv rows for the SERP-proven US keywords; tools/coast_match.py `--predictions` mode reads them.
- Pilot 15-25, phone review each, release 25/day; past ~100 only after AdSense approval.

## Lessons
- Heredoc wrote a literal no-break space instead of " " again (release.py); fixed with a script file. Edit tool also cannot match a literal no-break space.

## Edge cases (failures first; each with the test that fails without its guard)
1. Subordinate station, interval=6 refused: fetch_coops raises today, page never builds. Guard: own station fetched hilo only. Test: fixture with empty pred and non-empty hilo builds.
2. Own hilo empty or cut short (NOAA down): tide tiles blank. Guard: "Unknown" + previous cache kept; a page whose hilo window misses today says Unknown. Test: break_blocks variant hilo=[].
3. Wrong place for the reading: hero says the level is at this place when it is 12 km away. Guard: hero and Source name the level station and "N km away". Test: check.py fails a page with level_from that lacks the level station name.
4. Truth check queries the own station (no water level) and fails every page: truth_live must query level_from. Test: truth_live selftest row with level_from.
5. Live refresh (Worker /live/<site>.json) keyed on own id that has no readings. Guard: live file for the page carries level_from readings. Test: worker_slice_test with a prediction-only site.
6. Time zone: AK, HI, VI, PR, GU stations (lst_ldt is station local). Guard: page zone from station lat/lon as now; test: VI station times in AST.
7. Distance rule measured from the wrong point (page lat vs own station). Guard: distance from own station to level station. Test: coast_match selftest.
8. Level station dies or retires: real reading goes stale. Guard: existing stale rules (24 h not reporting); a NEW page without a live reading is held, a live one is never pulled. Test: existing stale fixture with level_from.
9. Duplicate keywords to one station (cape may tides / tide times): one page. Guard: matcher dedups by station. Test: selftest.
10. Two pages too close (subordinate offsets): own-page offset rule (>=15 min or >=max(0.3 ft, 10% range)) else nearby row. Test: fixture pair at 5 min fails.
11. Foreign or other-US namesake: only SERP-proven picks in data/keyword-picks.csv. Test: unpicked keyword refused.
12. Scale: +1 hilo call per page; fetched weekly (cache age >7 days), 25 pages/day x 3,264 max = 3,264 calls/week at full size; nearest search 3,264 x ~300 stations trivial. Files: 1 page + 1 live file each.
13. Datum: own and level station heights both MLLW, named. Test: datum_named already covers /coast/.
14. Negative zero on lows (-0.027 ft seen live): neg_zero rule live. Covered.

## Update 03:00 UTC: picks done
- data/tide-picks.csv: 59 keywords web-searched 2026-11-08 (47 US, 5 FOREIGN, 6 MIXED, 1 OTHER_US; search tool returns US results only, so foreign undercounted: phone review is the second check).
- `python -I tools/coast_match.py --predictions` (selftest in --selftest): 9 PASS: bellingham 9449211 (level Cherry Point 23.3 km), corpus christi tide times 8775870 (Packery Channel 6.2), edmonds 9447427 (Seattle 23.7), homer 9455558 (Seldovia 25.0), indian river inlet 8558690 (Lewes 19.7), jacksonville beach 8720291 (Mayport 13.4), marco 8724991 (Naples Bay N 19.3), mission bay 9410196 (La Jolla 8.7), waldport 9434939 (South Beach 21.3).
- Skipped: 23 no live level within 25 km (next: count NDBC buoy or water temperature as the real reading); 14 subordinate with a reference within 10 km (Tampa, Sarasota, Savannah, Cape May: next, point the keyword at that reference station's page, named with distance, instead of skipping).
- NEXT BUILD, in order (edge cases above): data/coasts.csv column level_from; collect.py own-station hilo only + fetch_coops(level_from); hero/Source name the level station and km; truth_live and Worker live file use level_from; check.py rule (level_from page must name its level station) + fixture; break_blocks 'coast prediction-only' sample; build the 9; phone review; release.
