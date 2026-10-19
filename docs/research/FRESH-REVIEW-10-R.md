# FRESH-REVIEW-10-R (re-verified): template hash ddb9f0f609ee14fc, dist_next rebuilt

Method: template_hash.py confirms ddb9f0f609ee14fc. Served dist_next on :8767 (stopped), parsed all 25 gauge pages and the home and state pages, reran the 390 px Playwright sweep and tools/review/alerts_live_test.mjs. No code edited. External hosts were blocked in my runs, so the "live update unavailable" line is my blocking.

## Resolved since my first R report (verified this run)
- Alerts: live Flood Warning updates banner, hero tile and lower block; an empty answer removes a stale banner; an abort or 500 leaves the page as built (my 6-case mock on Ohio, Chattahoochee, Roosevelt; shipped test passes). Not changed since: still P2 below.
- P1-1 tidal "Very low": the "on its own would read" sentence and "This compares the 24 h mean" appear on 0 of 25 pages. Sacramento now reads "Below normal. Lower than 77% of the 67 years... This gauge is tidal: the comparison uses the daily mean" with its 24 h range shown.
- P1-2 datum: Sacramento tile reads "Forecast high (NWS stage) 102.8 ft", with the NWS 102.00 ft vs USGS 104.21 ft note; this label appears only on Sacramento.
- P1-3 Gauley: heading "Normal range", "Higher than 58% of the 62 years", caption "Estimated from the 6:00 PM EDT reading against 62 years", home row "1,270 cfs, Normal range", West Virginia state page "1,270 cfs, normal range". Heading, caption and rows agree with the falling trend (-44.5% in 6 h).
- Verde percentile sentence reads "Higher than at least 95% of the 49 years" (correct).

## Re-sweep results
- All 25 pages: heading band, percentile sentence and home-row band agree with each other on 25 of 25. Band words follow the percentile (below 25 below normal, 25 to 75 normal, above 75 above normal, 95 or more very high). The latest-reading rule moved only Gauley; on the other 24 the caption still says 24 h mean and the latest flow is within about 22% of it (largest: Lees Ferry 8,000 vs 6,551 cfs, Normal range either way; the page prints its 4,970 to 8,070 cfs range and dam-cycle note).
- Tidal pages (Sacramento, Hudson at Green Island) keep the mean and say so.
- Regression: 25 pages at 390 px, no undefined, NaN, None, "-0%", ISO text, null, horizontal scroll, empty tile or overflow outside a scroll container (the doubled-word detector fires only on case and newline false positives). I filtered my output by the false-positive string, so the earlier "empty clipped table cell" notes on Atlanta, Trenton, Kinzua and Penns were not re-listed this run; treat as unchanged P2.

## P0
None.

## P1
None that I would not defend.

## P2
1. Shenandoah at Millville: "Above normal, Higher than 75%". At the 75 boundary the rounded figure sits in the normal band by my rule; the build probably uses the unrounded value (75.x). Show the band cut-off in the glossary or print one decimal near boundaries.
2. Gauley's headline now judges the latest reading while 24 other pages judge the 24 h mean; the captions say which, but the rule (a more than 30% gap) is not stated on the page. A small "Compared using the latest reading because it differs from the 24 h mean by more than 30%" would help the next reader of a Gauley-type page.
3. Banner pages (Ohio, Chattahoochee) have no hero alert tile; after a live empty answer the hero shows nothing, only the lower block says "none returned". The Roosevelt-type fallback tile says "No alerts active here" on a failed fetch with no build time.
4. Four pages (Atlanta, Trenton, Kinzua, Penns) have a few empty-looking narrow table cells; half-empty last tile row on several pages.

## Could not check
Connected live state (USGS CSV and NWS from a real network), dark mode, real device, screen reader, remote map and radar tiles, an extreme-low gauge (none built; "Lower than at least 95%" not seen rendered), alert tile "Unknown" and "stale" branches, USGS/NWS cross-checks beyond arithmetic within pages. I did not recapture the four phone screenshots after the rebuild; I checked Gauley and Sacramento by text only.

## Round 2: record_comparison table stacked (template hash 0d86ec8bdb9ee7ed, confirmed by template_hash.py)

Measured with Playwright (isMobile, external hosts blocked) on Gauley, Roosevelt, Potomac and Ohio at 390, 360 and 340 px (12 runs); server on :8767 stopped.
- The "Compared with this gauge's record" table is `class="stk"` on all 12 runs, 5 rows, columns Measure / Value / When or rank. Every cell carries its label (`data-l`): e.g. Ohio "Peak daily flow, last 7 days | 131,000 cfs | Oct 14, 2026"; "Last time ... this high or higher | 146,000 cfs | Sep 28, 2026 (16 days earlier)"; Gauley 4,190 cfs Oct 12; Potomac 22,100 cfs Oct 14. Labels match values; the values agree with the peak-then-earlier logic on each page.
- No clipping: 0 clipped cells, table right edge 355, 325 and 305 px at 390, 360 and 340 (15 px margin), page horizontal scroll 0 on all 12 runs.
- Other tables unchanged in kind: per page one `hm` (heat table) still scrolls inside its own scroll wrapper (as before, by design, not page scroll); `hc1 hc3`, `hc3` and the other `stk` tables are the same classes as before; only this table changed (it was a plain table).
- Screenshot (Gauley, 390 px at 2x, which I opened): five separate cards, each with MEASURE, VALUE, WHEN OR RANK rows, readable, right-aligned values, nothing cut off.

P2 (new, cosmetic): the MEASURE text is squeezed into about half the card width, so a long measure wraps to 6 lines ("Last time, before the last 7 days, that daily flow was this high or higher") while VALUE and WHEN rows are one line. Showing the measure full width as the card title and dropping the "MEASURE" label would read better. Also the third measure ("Last day above the 90th percentile...") puts a date under the label VALUE; the label is accurate for the first rows only. Neither blocks shipping.

Could not check in round 2: Linux fonts (the CI environment that caused the failure); I used Windows Chromium, so the real test is the CI rerun. Pages other than the four; dark mode.

VERDICT: SHIP
P0 list: none
