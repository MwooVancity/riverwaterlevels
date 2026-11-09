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

## Pictures on tiles (owner 2026-11-09: "shouldn't everything be a visual")
A picture is drawn by ONE shared helper from the same cached value the tile's number uses, never from a second fetch or a second calculation. It exists only when it shows a comparison the number can't (trend, range, danger line, time of day). The number stays as text above it. Before building any picture, check each line below; each needs a guard and a fixture.

All pictures
- Static picture vs live number: the Worker refreshes numbers every 3 min, the SVG is build time. A bar at 13.4 ft under a live "15.2 ft" is a false page. Guard: the picture carries its own time in its caption, or the live JS moves the marker with the number (data attributes), never neither.
- A new rule covers OLD pictures too: when a line is added here, check every picture already on the page against it the same batch (the flow and gage 24 h lines predated the static-vs-live rule and broke it until 2026-11-09; the Worker now moves their end dots).
- Missing data drawn as zero: a gap must be a gap (no bar, a break in the line), never a 0 bar or a flat line.
- Axis that lies: no cropped axis that turns 0.1 ft into a cliff; minimum span rule (the stage chart already keeps 1 ft); zero-based bars only where zero means something.
- Too few points: no picture under its minimum (line: 8 points; bars: 3 days; dots: 5 measurements). The tile shows the number alone, never an empty frame.
- Units: the picture uses the tile's unit (cm/m world pages, ft/cfs US); a world page never shows a ft axis on a cm number.
- Time zone: every time on a picture is the gauge's local time, DST included; never the viewer's or UTC.
- Stale source: same hide/amber limits as the number (STALE_H, HIDE_H). A hidden number hides its picture.
- Colour: the site's one blue; danger lines dashed with a text label, never a new red/amber that means something only to some readers; works in dark mode.
- Reading it without sight: every SVG has role="img" and a title with the numbers in words.
- Bytes and files: under 1 KB inline SVG each, no script, no image file; 14,000 pages x 5 pictures must stay inside the 90 KB phone budget (check.py).
- Phone width: readable at 320 px; labels never overlap (drop the middle label first).
- A check that reads it: check.py compares each picture's data attributes with the tile's number (a picture that disagrees with its own number holds the page).

Gage height: distance to flood
- No NWS stages, or only some (action but no flood): draw only the lines that exist; none = no bar.
- NWS and USGS read the river on different zero points (datum gap): margins already use the NWS reading; no NWS reading at that time = no bar.
- Lake or high-elevation gauge (580 ft, flood 590): a bar from 0 makes it look full. Axis floor = the lowest reading of the past year, labelled.
- Above major flood stage: bar full, arrow, "above major" in words.
- Negative gage height: axis starts below zero.
- Thresholds in flow, not stage (Boise): no stage bar.
- World pages: the agency's own marks (MHW, HSW), named as the agency names them; never NWS words.
- Coasts: tide datum (MLLW) and NWS coastal flood thresholds only where NWS publishes them for that station.

Forecast curve
- Forecast point is another place (McAlpine Lower for Louisville): label says so, as the tile does.
- Forecast older than its limit: amber after 24 h, hidden after 72 h, the curve with it.
- One forecast point, or forecast in flow while the tile is stage: no curve.
- Forecast starts before the latest reading (overlap) or hours after it (gap): draw from the latest reading; a gap is shown as a gap.
- Dam-controlled reach where the forecast is hours out of step (`_fc_offset`): show the offset note, never a smooth join that hides it.

Rain bars (7 days)
- Station day vs calendar day: ACIS observation days often end at 7 AM; label "observation day"; never past the page's local today (ACIS tomorrow bug).
- Missing (M) is a gap, trace (T) a hairline, never 0.
- Two sources (NWS RFC grid, ACIS stations) never mixed in one set of bars.
- Snow: liquid equivalent, labelled.

Daylight bar
- Polar day or night (Alaska, northern Norway): no sunrise or sunset; say "sun up all day" or "sun down all day", no bar.
- The "now" dot is build time on a static page: the live JS moves it, or it is left out.
- DST change day: lengths from the computed times, not 24 h arithmetic.

Depth dots (USGS channel measurements)
- Under 5 measurements within a mile: no picture.
- Flow spans 100x: log flow axis, labelled.
- Today's flow outside every measurement: say "above (or below) every measured flow", never extrapolate a depth.
- Old channel shape: use the last 15 years only; scour and fill change depth at the same flow.

## Never
- A per-gauge exception list. If one gauge needs it, the rule is wrong: redefine what the rule matches.
- A fix in the template that hides a bad value. The cache must hold the truth.
- Loosening a check to get a page through. A failing page is carried (old copy) or sent back; it is never forced live.
- A claim of "fixed" without step 6 in the same response.
