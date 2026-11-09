# Master prompt: fix every gauge at the source (owner 2026-11-09)

Use for any wrong, missing or odd number on any water page (river, lake, coast, any country). Paste this file to a fresh session, or follow it in place.

## The rule
A page shows what the agency published, converted once, in one place. A wrong page is fixed in the code that reads the feed (`collect.py`, one function per feed), never in the page template, never per gauge, never by loosening a check. One fix covers every gauge on that feed, today and at 14,000 pages.

## Steps (in order, no skipping)
1. **Name the defect in numbers.** Page URL, value shown, value at the agency for the same time, the agency URL you read in this session. No agency read = no defect yet.
2. **Find the one function.** Trace the number back: page block (`lib/*.py`), then cache key, then the `collect.py` function that wrote it. The fix lives where the value enters (`fetch_*`, `chan_rows`, `nwps_cats`, `pegel_end`), or in the shared helper every caller uses. If two places compute the same value, delete one.
3. **List every edge case for that function** (table below). For each one, write: how it breaks today, how many gauges it hits at full size, the test that fails without the guard.
4. **Write the failing fixture first** in `tools/edge_tests.py` (pure function, no network). Then the fix. Then run the fixture.
5. **Prove it on real data.** Run the fixed function on 5+ real gauges of that feed, including the one that failed and one of each odd kind (big river, tidal, lake, ice, side channel, far measurement). Print what the page would say.
6. **Prove it live.** Push `check`, read "refresh OK", push main, then `tools/truth_live.py` (US) or `tools/truth_world.py` (world): 0 mismatches. Read the live page.
7. **Record it.** One line in PLAN.md "Master edge-case list" (G = guarded, with the test name). A defect seen twice becomes a `check.py` or `truth_live` rule the same batch.

## Edge cases to check for every value a feed gives us
| Case | Seen here | Guard (where) |
|---|---|---|
| Two calls disagree at one time (current vs series) | Wuerzburg 144 vs 146 cm | Series ends on the current reading (`pegel_end`) |
| Missing written as a number (-9999, 0, -999999) | NWS flood category 0 | Keep only plausible values (`nwps_cats` > 0) |
| Blank, null, text where a number goes | USGS 00010 null value | Skip the row, never crash; block shows Unknown |
| Wrong unit or no unit (m/cm/ft, °C/°F, m3/s/cfs, ft^2) | channel area units | Accept only named units; else drop the row |
| Future time / very old "latest" | Selway 'latest' from 2010 | `wx.suspect` hold, truth_live future rule |
| Time zone: UTC day vs local day | ACIS 'tomorrow' column | Cut at the page's local date (`b_acis`) |
| Value from another place | Omaha measured 8.5 mi away; NWS point named for a nearby place | Distance limit (`CHAN_MAX_FT`), name the other place on the page |
| Several rows per event (side channel, repeat 'check' run, two sensors) | Austin Check vs Main | One row per visit, main channel; any-sensor match for temps |
| Revised or provisional values | USGS corrections | `merge_rows` keeps the correction, counts it |
| Feed changed shape | cache_shape.json | Wrong container = empty, never a crash |
| Feed down / partial / rate limited | 429, timeouts | Keep the last good value with its real age; retry on its timer, not hourly |
| Lagging daily values | daily mean 6 days behind | Say the real date, never "today" |
| First run, no old copy | new gauge | Ship test: recent reading, unit, time, or the page waits |
| Scale: calls x gauges per hour | 14,000 gauges, 1,000 USGS calls/h | Weekly sources in `WEEKLY`, spread by hash; one early refresh only when a new field appears |

## Never
- A per-gauge exception list. If one gauge needs it, the rule is wrong: redefine what the rule matches.
- A fix in the template that hides a bad value. The cache must hold the truth.
- Loosening a check to get a page through. A failing page is carried (old copy) or sent back; it is never forced live.
- A claim of "fixed" without step 6 in the same response.
