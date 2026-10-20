# Gate wiring audit (2026-10-19, adversarial, run not read)

Method: mutation tests on a throwaway copy (deleted), plus `git archive HEAD` as a stand-in for a fresh CI checkout. Nothing deployed.
Chain (refresh.py, verified): collect, build, check, stamp, template_hash --check, truth_tests, truth_types, truth_live --dir, [4 browser gates if template changed], publish (re-runs check.py + new-page review), wrangler, livecheck, truth_live (SOFT). Any non-zero return before the deploy hits `break`; only the last truth_live is in SOFT (the pre-publish one has different argv, so it blocks).

## 1. Wiring table

| Gate | Chain | GitHub | Windows | Blocks | Needs / CI notes |
|---|---|---|---|---|---|
| check.py | yes, twice (step 3 and in publish) | yes | yes | yes | dist_next only |
| template_hash --check | yes | yes | yes | yes | data/reviews.json and the signed report must be git-tracked. HEAD passes in a fresh archive (rc 0). Reports under gitignored docs/research need `git add -f` |
| truth_tests | yes | yes | yes | yes | cache/ from the same run; contracts 4, 5, 9 read dist_next |
| truth_types | yes | yes | yes | yes | hard-coded cache/03192000.json |
| truth_live --dir | yes | yes | yes | **skips on any USGS error** (429, 5xx, bad JSON) | network |
| browser gates | only if live template hash differs | yes | yes | yes | Playwright; skipped on data-only runs |
| publish new-page review | yes | **no-op** | yes | yes | `if os.path.isdir(D)`: CI has no dist/ |
| livecheck | after deploy | yes | yes | marks run failed, no rollback | |
| truth_live (live) | SOFT | yes | yes | no | alarm via watchdog only |
| **tests.py** | **no** | no | no | n/a | passes in 16 s, but it rewrites real dist/ and cache/ |
| **truth_fuzz.py** | **no** | no | no | n/a | 2.5 min quick, 0 failures |
| render_test.mjs, js_test.mjs | no | no | no | n/a | manual only |

Windows tasks (schtasks): both enabled, same chain, "Fast Refresh" fires at :05/:35, the same minutes as GitHub's cron. Last Result of Fast Refresh = 1: the dirty working tree has no SHIP, and the log shows "STOPPED at tools/template_hash.py" (17 STOPPED lines). That is the gate working.

## 2. Mutation proof

| Mutation | Command | rc | Stops refresh? |
|---|---|---|---|
| "None" / "NaN" / "the the" in a page | check.py | 1 | yes |
| One extra line in lib/render.py (HEAD copy) | template_hash --check | 1 | yes |
| Negative flow in a cache | truth_tests | 1 | yes |
| Flow 99,999,999 | truth_tests | 1 | yes |
| **-999999 sentinel in a cache** | truth_tests | **0** | contract 19's sentinel branch is dead: `series()` drops values <= -900 first. The protection is `series()`; the test is theatre |
| nws/rain/nwps set to a string | truth_tests | **1, TypeError** | blocks, but the test crashes (`setdefault` returns None after ctx coercion). One malformed source freezes all deploys. Build and check pass; the page says "Alerts could not be loaded" |
| nws.alerts set to a string (nested) | build, check | build 0, check 1 | `conditions()` and `hero()` are not guarded: "PAGE BUILD CRASH", the gauge is missing, check fails on broken links. Safe, but one bad gauge freezes the whole site |
| **b_alerts raises on all 25 gauges** | build / check / truth_tests / truth_types | **0 / 0 / 0 / 0** | **ships**. The guard prints a line; nothing fails. Contract 20 is theatre: truth_tests never calls `build_tab`, so `BLOCK_ERRORS` stays empty. truth_types calls `build_tab` but never reads it |
| **Gauge reading 40 days old** | build, check, publish | 0, 0, 0 | **the page is deleted from dist and the live site**. "previous pages stay live" (build.py, CLAUDE.md, tests.py step 3) is false. Watchdog floor is 40 pages against 49, so there is no alert |
| USGS unreachable (HTTPS_PROXY dead) | truth_live --dir | 0 | `_truth.json` = `skipped`, `last_ok_at` carried over from the live file (null if the live site is also unreachable) |
| New unreviewed page, dist/ present vs absent | publish.py | 1 vs **0** | confirms the CI no-op. `build.py` hold_back is the only CI guard |
| _truth.json absent on live | watchdog.py | **0** | the `except Exception` prints a note and passes |
| Nested type confusion | truth_fuzz | 0 | JUNK is applied to top-level keys only, so it missed the alerts crash |

Watchdog on `skipped`: no immediate alert; it fails only when `last_ok_at` is older than 6 h. Its `mismatch` branch is dead (a mismatching build never ships). It checks median age, not the oldest gauge; `by_gauge` is unused.

## 3. Order and races
- Gates run on dist_next, then publish re-runs check.py and renames the same directory. In one process nothing can swap it between the gates and the rename. Good.
- Three deployers: GitHub (HEAD, serialised by `concurrency`), Windows Fast and Windows Full. They share no lock. `runs/refresh.lock` is a local file on the Windows PC; GitHub never sees it. Two Windows tasks are serialised by it, but only for 45 minutes; a longer run lets a second start, and the first run's `os.remove` can throw.
- Last wrangler deploy wins. A slow run can overwrite a newer one with older data. Windows deploys the working tree (it can be unpushed) while GitHub deploys HEAD, so the live template can flip between them. `gate_plan` only reads the live hash.
- The template hash covers lib/, templates/ and build.py. It does not cover data/sources.json (terms gating decides what renders), name overrides, or collect.py.
- The review "signature" is a hash of a report file. It is tamper-evident for accidents, not a security control; whoever runs record_review.py can sign.

## 4. Loopholes
1. Hidden blocks. Alerts, river forecast and flood ladder can vanish with no "unavailable" text, as shown above. The hero tile still says "No alerts active here" or "Unknown", so the safety headline survives, but the detail does not.
2. Silent page deletion at 30 days (see above). Between 24 h and 30 days the page stays with "Gauge not reporting", which is visible.
3. truth_live skip on every error, including routine 429s. A baseline run in this audit was skipped by a 429.
4. A successful CI run logs nothing about which gates ran or skipped.
5. Contract-19 sentinel check and the sg check are dead code.

## 5. Five highest-value fixes
1. Make guard errors fatal for safety blocks. In `_safe`, for ids alerts, river_forecast and stage ladder return a visible "temporarily unavailable" block. In truth_types and build.py, exit 1 if `BLOCK_ERRORS` is non-empty. Test: re-run the b_alerts mutation, expect rc 1. About 15 min.
2. Page-set shrink gate. In publish.py, or as an ALWAYS gate, compare `_urls.json` with the live list (fetch it when dist/ is absent) and fail on any missing gauge URL. Test: the 40-day mutation must give rc 1. This also removes the dist-absent no-op. About 15 min.
3. Fix truth_tests contract 18 (`G3["rec"]["nws"] = dict(G3["rec"].get("nws") or {}, alerts=None)`), guard `conditions()` with `isinstance(list)`, and add nested string/list junk to truth_fuzz. Test: the "nws is a string" and "alerts is a string" mutations must build with rc 0. About 20 min.
4. Split tests.py into a side-effect-free half (selftest, review, sign, index, units) and add that to ALWAYS. Add truth_fuzz quick as a nightly workflow. Test: break the signed-review logic and watch refresh stop. About 20 min.
5. Make truth_live skip count. Fail the deploy if USGS has been skipped for 2 runs in a row, retry 429 with backoff, and make the watchdog fail when `_truth.json` is absent or 404. Test: dead-proxy run twice, expect rc 1. About 15 min.

Also: disable the Windows tasks once GitHub is proven (races), and stop `os.remove(LOCK)` from throwing.

WIRING VERDICT: PARTLY. Biggest hole: the block guard is a silent black hole. A block (alerts, forecast, flood stages) that raises on every gauge passes every gate and ships with no "unavailable" notice, and the pass-looking "contract 20" cannot fire. Close second: a dead gauge's page is silently removed from the live site.
