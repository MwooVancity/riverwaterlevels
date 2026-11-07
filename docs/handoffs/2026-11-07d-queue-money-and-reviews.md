# Handoff 2026-11-07 (d): queue in money order, reviews, bigger site

Start: "read docs/handoffs/2026-11-07d-queue-money-and-reviews.md and continue". Owner: keep executing without stopping; "every page perfected to the absolute possible limits"; "we should be bigger".

## State at handoff (17:05 UTC)
- main 7af87a3 + check has 5e06dfb (PLAN) and the Buffalo MS / Lake Fork OH hold (data/waves.csv): push check, read dryrun "refresh OK", then `git push origin check:main`.
- Live 16:02 build: 340 pages, failed_urls []. Today's release: failed 15:06 (fixed in 7af87a3), skipped 16:02 (last refresh 55 min > 45); a run after 16:10 was being watched for the release. Read its log first: `gh run list --workflow refresh.yml -L 3`, then `gh run view <id> --log | grep -E "release|not released|refresh OK|FAILED"`. Poll slowly (`gh run watch -i 120`): the account hit GitHub's API limit twice today.
- Built today (all live): code review fixes (10), lake NWS-scale fixes (Lanier, Allatoona, Barren, Corpus Christi cleared), coast Moon block (USNO), readiness fixes (truth_tests per-gauge carry, all page kinds carryable, failed release gates picks until tomorrow via tools/release_failed.py, cache saved after a missed restore, world pages vs ECCC/EA/PEGELONLINE before deploy at the page's own minute), new lakes/coasts publish only after a passed phone review (release.py UNREVIEWED_MAX = 0), one check.py page_checks for gate and release, quarantine ignores carried pages, bot pulls --autostash, doubled-word check skips quoted NWS text.
- Global ~/.claude/CLAUDE.md: edge-case list rewritten (owner asked).

## Queue audit (fresh agent, 2026-11-07, numbers measured)
- Keyword Planner: ~92,700 phrasings asked; 54,076 saved (data/keyword-tiers-water.csv 52,602; data/keyword-tiers.csv 1,476); 6,209 with 10+ searches (41 at 10K-100K, 1 at 100K+). Ranges only.
- data/world-queue.csv 20,000 rows (a cap in tools/world_queue.py): 19 at 10K-100K, 261 at 1K-10K, 1,390 at 100-1K, 3,926 at 10-100, 14,404 zero/unmeasured.
- Not in money order: (1) top 70 rows are US lakes/coasts blocked by UNREVIEWED_MAX 0 until a phone review; tomorrow's 25 = 5 reviewed lakes + 20 rivers at 100-1K; (2) no country rate in world_queue.py; country blank on 2,758 lake/ocean/hub rows; ambiguous names (Dunedin, Westport, Portland, New Plymouth, Bangor, Newport, Richmond, Freeport); (3) unbuildable rows at ranks 17-19 (Plymouth, Portsmouth: UK predictions barred; bore tides: place unclear); (4) ~135 US lake/coast rows at 1K+ not linked (Charleston, Biloxi, Lake Tahoe, Okeechobee, Texoma, Lake Norman); (5) multi-country rivers score 0 (Trent, Thames); world rivers enter only via data/world-ready.csv (32 rows at 10-100).

## Next, in order (money)
1. Link the ~135 US lake/coast rows at 1K+ (data/coasts.csv: CO-OPS stations with water level, exact name, read live; data/lakes.csv: USGS lake codes or agency feeds). Script the match, hand-check ambiguous.
2. tools/world_queue.py: country column, score = searches x RATE (tools/release.py), barred sources (UK tides, CHS) = 0, ambiguous multi-state names held until hand-picked; Trent/Thames to the UK.
3. Phone reviews of queued US lakes and coasts (python -I tools/hater_sample.py, node tools/hater_shots.mjs, reviewer reads tools/review_brief.md; PASS -> tools/review_sign.py -> data/reviewed.json). About 15k tokens a page (2026-11-07: 405k for 26). Owner: no screenshot cap.
4. NOAA tide-prediction-only stations (~2,800 beyond the ~200 with water level; public domain; 'tides' 1.15M/mo + 'tide times' 620k): predictions-only coast path, station distance and type (subordinate) named.
5. Hub generator (state x type, 3+ children); 47 hub rows, 1 built.
6. Ireland coasts (Marine Institute ERDDAP IMI_TidePrediction_HighLow, CC BY 4.0 read live; heights above OD Malin; Kinsale first) + Met Eireann terms read live.
7. Keyword Planner: 'river height'/'gauge' phrasings for UK, AU, NZ, IE; owner: monthly values need a running campaign.

## Lessons today
- Heredoc python with backslashes broke files 3 times (release.py "\n", collect.py regex): use Edit or a script file, never heredoc for backslashes.
- A guard that is right for truth can cost the money order (UNREVIEWED_MAX 0): pair it with the work that clears it (reviews).
- GitHub run "success" means nothing (continue-on-error): read "refresh OK" in the log.
- `gh run watch` default 3 s polling burns the API: use -i 120.
