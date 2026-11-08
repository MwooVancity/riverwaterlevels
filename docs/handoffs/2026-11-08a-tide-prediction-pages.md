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
