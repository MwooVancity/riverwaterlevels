# FRESH-REVIEW-10-ZA: template hash edd92a4a816f2974

Re-verification of FRESH-REVIEW-10-Z, 2026-10-21 about 08:55 UTC. `python -I tools/template_hash.py` printed `edd92a4a816f2974` (matches). Served from 127.0.0.1:8787. No code or data edited. Only change since Z: the pill suffix after a successful live check is time-only.

## Method
- Playwright, 390 px, light and dark, Salt Roosevelt and Potomac Little Falls, with the USGS `latest-continuous` call mocked to a successful 20-minute-old response (5,150 cfs / 3.38 ft) and all other external hosts blocked. Pill text, rendered height and line-height measured; first-screen screenshots read by eye (Salt dark, Potomac light).

## #1 COMPARISON
Unchanged from FRESH-REVIEW-10-Z (table there, done on hash 927463f2a915ed1c, competitors not re-opened). No cell changes.

## PER ACTIVITY
Unchanged from FRESH-REVIEW-10-Z.

## DEFECTS

### P0
None.

### P1
None.

Verified this run: after a mocked live success the pills read "Falling: -2.6% flow in 6 h (as of 12:50 AM)" and "Above normal for Oct 21 (as of 12:50 AM)" on Potomac (each 25 px = one line at 19 px line-height), and "Falling: -2.8% flow in 6 h; NWS forecast rises to 15.8 ft by Oct 23, 5:00 PM MST (as of 10:30 PM)" (44 px = two lines) and "Above normal for Oct 20 (as of 10:30 PM)" (one line) on Salt; identical in dark. Header shows the live value and "20 min old"; Flood Watch flag, gage tile sentence ("Water reaches the USGS wellhouse."), "Next NWS impact at 3.5 ft (0.1 ft above): The river reaches caution level for boaters, as defined by the State of Maryland." and the normal block are unchanged. Z P2-12 (95-character pill, three lines) is closed.

### P2 (remaining, carried from Z)
1. Three horizontal scrollers on the Now tab at 390 with no hint; hourly table also cut at 1280.
2. 1280 tile grid orphans.
3. Potomac duplicate "Chevy Chase 1.2 SW" rows without a station id.
4. "Highest, 7 days" vs "Peak, last 7 days" labels on History.
5. Salt, New, Deschutes never name their controlling dam.
6. Hero banner and 6 h tile repeat "newer than this comparison" after a live update.
7. Ohio pairs a 12:45 flow with a 1:00 stage.
8. Breadcrumb state link and in-tile link tap targets under 32 px.
9. PAD-US "Restricted access" label for the C and O Canal.
10. Hudson "Direction unclear" pill on a tidal gauge.
11. Penns Creek H1 lacks "at Penns Creek".
12. "NWS alert check is old" pill does not say what the last answer was.
13. The as-of time has no zone while the header time next to it does ("observed Oct 21, 5:39 AM EDT ... (as of 12:50 AM)"); on a page read from another zone this is ambiguous for a minute. Minor; the full form was worse.

## PAGE VERDICTS
PAGE /river/arkansas-river-co/avondale-07109500/: SHIP
PAGE /river/chattahoochee-river/atlanta/: SHIP
PAGE /river/colorado-river-az/lees-ferry/: SHIP
PAGE /river/columbia-river-or/the-dalles/: SHIP
PAGE /river/delaware-river-nj/trenton/: SHIP
PAGE /river/deschutes-river-or/moody/: SHIP
PAGE /river/gauley-river/above-belva/: SHIP
PAGE /river/hudson-river/green-island/: SHIP
PAGE /river/kinzua-creek/guffey/: SHIP
PAGE /river/madison-river/below-ennis-lake/: SHIP
PAGE /river/mississippi-river-mo/saint-louis/: SHIP
PAGE /river/missouri-river-mo/kansas-city/: SHIP
PAGE /river/new-river-wv/thurmond/: SHIP
PAGE /river/ohio-river-ky/louisville/: SHIP
PAGE /river/penns-creek/penns-creek/: SHIP
PAGE /river/potomac-river-md/little-falls/: SHIP
PAGE /river/roaring-fork-river/glenwood-springs/: SHIP
PAGE /river/sacramento-river/freeport/: SHIP
PAGE /river/salmon-river-id/white-bird/: SHIP
PAGE /river/salt-river-az/roosevelt/: SHIP
PAGE /river/shenandoah-river/millville/: SHIP
PAGE /river/snake-river-wa/anatone/: SHIP
PAGE /river/susquehanna-river-pa/marietta/: SHIP
PAGE /river/verde-river/camp-verde/: SHIP
PAGE /river/yellowstone-river-mt/livingston/: SHIP

## NOT CHECKED
- Only Salt and Potomac at 390 were rendered on this hash; the other 23 pages and the 1280 layouts were not re-rendered (the change is one template string).
- The real USGS live call was not exercised (mocked response).
- USGS values not re-fetched; competitors not re-opened.

VERDICT: SHIP
