# Indexing rules: which pages Google may see, and when to stop

Status 2026-10-20: the whole site is `noindex` (`data/index-allow.json`: `open:false`, `site_pages:false`, `allow:[]`). Nothing below is active until the owner says "start". A valid gauge id is NOT a reason to index a page.

## How the switch works (all in code)
- `data/index-allow.json`: `allow` = the gauge page URLs that may be indexed; `site_pages` = home, state, about and other trust pages; `open` = master switch. `lib/indexing.py` turns it into the robots meta tag, the `X-Robots-Tag` header and the sitemap.
- `python tools/open_wave.py N` = dry run of the next N pages (highest queue score first, live, reviewed SHIP). `--apply` writes them. `--pull /river/x/y/` removes pages (the kill switch for a batch). Then build, check, deploy.
- `check.py` refuses a build when an allowed page has no SHIP review; `sitemap` and the allow list must agree (checked).

## Entry criteria for any page (all must hold; `open_wave.py` enforces the first four)
1. Page is live and has a SHIP verdict in `data/reviews.json`.
2. At least `MIN_BLOCKS` (15) data blocks render and the gauge has at least `MIN_YEARS` (10) years of daily statistics.
3. Not excluded or held in `data/waves.csv` (name confidence, gate column).
4. Not a duplicate: at most 1 gauge per river per day (`rescore.py`).
5. By hand, per cohort: `_truth.json` status ok and under 6 h old; `status.json` has no `failed_urls` and no `block_errors`; `truth_types`, `truth_fuzz` and the browser gates passed on the current template; every data block shown has a source row in `data/sources.json` with status other than `off`.
6. Owner-only preconditions (page 0 of the release): publisher name and contact email on About; a corrections route (`docs/CORRECTIONS.md`); Search Console property verified so the cohort can be measured. No ads and no consent banner needed while ads are off.

## Cohorts and the stop and go rules (numbers are decisions, change them in this file and in `PLAN.md` together)
| Wave | What opens | Wait before the next | Go only if |
|---|---|---|---|
| 0 | `site_pages:true` (home, state pages, trust pages) + the 10 hand-picked gauge pages below | 14 days | pages crawled and no data incident |
| 1 | 25 more (diverse types), then 25 per day at most | 14 days after the first 25, then rolling | see go rules |
| later | 25 per day | continuous, with a weekly review | every rule below stays green |

Hand-pick the 10 for wave 0 by type, not only by score: 1 ordinary mid-size river, 1 tailwater (Lees Ferry), 1 small creek without forecast (Kinzua), 1 tidal or oscillating (Hudson or Sacramento), 1 big river with flood stages (Ohio), 1 mountain river (Salmon or Yellowstone), 3 high-queue popular rivers, 1 with an active alert history.

**Go (next wave)** when ALL hold after the wait: no wrong-number incident (a `P0` in the bug ledger); watchdog green for 14 days; Search Console shows the wave-0 URLs crawled; no manual action; the home and trust pages did not lose impressions faster than the gauge pages gained them.
**Hold** when: fewer than half of the opened URLs are indexed after 30 days (diagnose crawl, canonical, quality before adding); watchdog red for more than 24 h cumulative.
**Stop and pull** (`open_wave.py --pull`, or `open:false`) when: a wrong or stale number reached a page without a visible label; Search Console shows a site-wide impressions fall of more than 50% within 7 days of a wave; a manual action or AdSense policy notice appears; the source terms of a displayed block turn out not to allow it.
Never open more than one wave inside 14 days, and never open pages to hit a count.

## What to record for each wave (`docs/COHORT-LOG.md`, one table, appended by hand or script)
date, URLs opened, template hash, indexed after 7, 14, 30 days, impressions, clicks, queries that matched, incidents. The decision to go, hold or stop is written next to the numbers.

## Not decided here (owner)
Whether and when ads start (separate consent-banner work), and the lakes cohort (after the first river cohorts are healthy).
