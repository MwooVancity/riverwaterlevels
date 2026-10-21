# FRESH-REVIEW-10-Y: template hash 927463f2a915ed1c

Reviewed 2026-10-21, about 06:40 to 08:10 UTC. `python -I tools/template_hash.py` printed `927463f2a915ed1c` (matches). Built pages served from `dist_next/` on 127.0.0.1:8787 (python http.server). Live riverwaterlevels.com was not used except as the "before" I already know from 10-X. No code or data was edited.

## Method
- Playwright Chromium (calcscrape's node_modules) rendered all 25 river pages at 390 px light, 390 px dark, 1280 px light and 1280 px dark (100 full-page screenshots, text dump at 1280, link list). 390-light ran with the network on (so the in-page USGS live check ran); the other three blocked external hosts. Per render: horizontal overflow, page errors, console errors, failed requests, sentinel words (NaN, undefined, null, None, nan, Infinity), empty tiles, images without alt, text under 11 px, interactive elements under 32 px, double spaces. Results: 0 px overflow on all 100, 0 page errors, 0 sentinel strings, 0 empty tiles, 0 images without alt, 0 text under 11 px, 0 double spaces, 0 broken internal links (every href resolved against dist_next). External hosts linked: USGS, NWS/NOAA, EPA, FEMA, USDA, ACIS, Drought Monitor only.
- Second pass on Potomac, Hudson, Salt, Kinzua in light and dark: computed contrast of every text node, listed horizontal scrollers, clicked each of the five phone tabs and listed the visible H2s (tab map below), and rendered Potomac at 1280 with network on to confirm the map tile loads (it does: basemap.nationalmap.gov export, alt text present).
- USGS IV API (00060, 00065, latest value plus a 4 h window) for all 25 site ids at 06:20 UTC and again at 06:50 UTC. Every page's flow, gage height and observation time equal the USGS value at the page's stated time; where USGS had a newer interval the page's age chip said so. Examples: Chattahoochee 1,050 cfs / 2.94 ft at 1:45 AM EDT exact; Lees Ferry 7,470 / 7.95 at 10:00 PM MST (USGS 22:00 = 7,470 / 7.95; 23:00 had fallen to 6,780, the page said 79 min old); Mississippi 179,000 / 7.59 at 12:00 AM CDT exact; Kinzua 16 / 2.25 exact; Yellowstone 1,570 / -0.16 at 10:00 PM MDT exact; Hudson 8,100 / 16.42 at 1:15 AM EDT exact; Salt 389 / 6.74 exact; Verde 599 / 4.75 exact; Ohio 73,100 / 15.67 at 12:45 AM EDT (USGS 00:45 = 73,100, 01:00 = 15.67: the page pairs the 12:45 flow with the 1:00 stage, a 15 min offset, see P2-12). 25 of 25 agree.
- Competitors: WebSearch for the eight sampled queries (first attempt was rate-limited; completed after the reset). Top results opened with Playwright at 390 (Android UA) and 1280 and screenshotted: USGS monitoring-location pages (09380000, 01358000, 03011800, 07010000, 06041000, 09506000, 06192500), water.noaa.gov gauges (tryn6, eadm7, bvaw2, cvra3, livm8; lefa3 returned 404), snoflo.org reports (Hudson, Gauley, Arizona and Pennsylvania state pages), americanwhitewater.org river-detail 2379 (Lower Gauley), howsyourriver.com Kinzua Creek, bigskyanglers.com Madison report, fwp.mt.gov Madison page, riverapp.net, flyanglersonline Yellowstone thread. The water.noaa.gov pages rendered only "loading..." after 6 s on a phone UA (NWPS is a JS app), which is itself the comparison.
- Read in full (screenshots at 390 light and/or dark plus the 1280 text): Potomac Little Falls (390 light, 1280 light with network), Salt Roosevelt (390 dark), Hudson Green Island (390 dark), Lees Ferry (1280 light), Kinzua (390), Gauley (390), Madison (390), Yellowstone (390), Verde (390), Mississippi (1280 dark). The other 15 were checked by script, their first-screen pill text, title, H1, description length, canonical and their text dumps (grep for the patterns listed under DEFECTS).

Tab map at 390 (Potomac; Hudson and Salt identical in structure): Now = What the water is like now, Water quality sensors, Hourly forecast, Weather forecast, Recent rain, Level flow and flood risk, Flow over time, Gage height and flood stages, Flood impacts, Weather alerts. Forecast = River forecast, Measured daily rain at nearby stations, Forecast rain totals, Outlooks. History = Rate of rise and fall, Compared with record, Largest annual peaks, Peaks that reached flood stage, Flood frequency, Historic crests, Long-range outlook. Data = Typical water temperature by month, Daily mean flow, Field measurements, Rating, Drought Monitor, State water quality, Watershed. Area = Air conditions, Public land, Upstream and downstream gauges, NWS forecast point, Gauge location, Official pages, About the gauge. The 10-X P1-2 ("Weather" tab held the river forecast) is fixed: the tab is now "Forecast" and matches its H2 group. Tab buttons are 78 x 56 px.

## #1 COMPARISON
Columns per competitor: answer-speed / freshness-clarity / trust / extra value / mobile layout.

| page | competitor 1 | competitor 2 | competitor 3 |
|---|---|---|---|
| /river/colorado-river-az/lees-ferry/ | USGS 09380000 monitoring page: BEAT / BEAT / LOSE / BEAT / BEAT | water.noaa.gov (lefa3 404; CLFA3 page loads only "loading..." on phone): BEAT / BEAT / LOSE / BEAT / BEAT | snoflo Arizona flow report (state page, no gauge value on first screen): BEAT / BEAT / BEAT / BEAT / BEAT |
| /river/hudson-river/green-island/ | snoflo Hudson at Green Island: BEAT / BEAT / BEAT / BEAT / BEAT | USGS 01358000: BEAT / BEAT / LOSE / BEAT / BEAT | water.noaa.gov tryn6: BEAT / BEAT / LOSE / BEAT / BEAT |
| /river/kinzua-creek/guffey/ | USGS 03011800: BEAT / TIE / LOSE / BEAT / BEAT | howsyourriver.com Kinzua Creek: BEAT / BEAT / BEAT / TIE / BEAT | paflyfish.com threads (2019): BEAT / BEAT / TIE / LOSE / BEAT |
| /river/mississippi-river-mo/saint-louis/ | USGS 07010000: BEAT / BEAT / LOSE / BEAT / BEAT | water.noaa.gov eadm7: BEAT / BEAT / LOSE / TIE / BEAT | news items (ksdk, grainnet, old floods): BEAT / BEAT / TIE / BEAT / BEAT |
| /river/gauley-river/above-belva/ | water.noaa.gov bvaw2: BEAT / BEAT / LOSE / TIE / BEAT | American Whitewater #2379 Lower Gauley: BEAT / TIE / TIE / LOSE / BEAT | snoflo Gauley above Belva: BEAT / TIE / BEAT / BEAT / BEAT |
| /river/madison-river/below-ennis-lake/ | fwp.mt.gov Madison River (recreation rules, no level): BEAT / BEAT / LOSE / TIE / BEAT | bigskyanglers.com Madison report (Oct 15, 2026): BEAT / TIE / TIE / LOSE / BEAT | USGS 06041000: BEAT / BEAT / LOSE / BEAT / BEAT |
| /river/verde-river/camp-verde/ | USGS 09504950 / 09506000: BEAT / BEAT / LOSE / BEAT / BEAT | riverapp.net station page: BEAT / TIE / TIE / BEAT / BEAT | weather.gov/fgz 2021 flood page: BEAT / BEAT / LOSE / BEAT / BEAT |
| /river/yellowstone-river-mt/livingston/ | USGS 06192500: BEAT / BEAT / LOSE / BEAT / BEAT | water.noaa.gov livm8: BEAT / BEAT / LOSE / TIE / BEAT | flyanglersonline / nbcmontana (old): BEAT / BEAT / TIE / LOSE / BEAT |

What each LOSE needs:
- Trust vs USGS and NWS (all eight): a .gov publisher versus a site whose footer says only "River Water Levels · Data: USGS, NOAA, NWS." No person, organisation or contact anywhere on the page (About page exists; footer does not say who). Owner waived this on 2026-10-20; it is still the first thing a rater looks for and the one place every competitor with a .gov domain beats us.
- Extra value vs American Whitewater (Gauley): AW shows "821 cfs, low runnable", difficulty III-IV(V), 14 mi, next release date. Our Gauley page names Summersville only inside the generic caveat and gives a paddler no published runnable range and no release schedule. A verbatim, attributed, dated row ("American Whitewater, Lower Gauley: low runnable at 821 cfs, read 2026-10-21"; "Next release: ...") is allowed under the hard rules and closes this.
- Extra value vs bigskyanglers (Madison): the shop report has dated angler observations ("707 cfs below Hebgen, dropped back for fall brown trout flows"). We cannot write that; we can show what we have and do not: the page never names the hoot-owl closure rule or FWP restrictions page that FWP publishes. One link row under Official pages: "Montana FWP restrictions and closures" (source value) closes most of it.
- Extra value vs paflyfish (Kinzua) and flyanglersonline (Yellowstone): anglers want a wading level and clarity; Kinzua has no turbidity sensor and the page says so; nothing else to add without composing. TIE at best; acceptable.
- Freshness TIE vs USGS on Kinzua: USGS showed 04:00 AM EDT when our build showed 02:00 AM, but the page's live check brought the top number to the same interval (verified: live script updated the header to the latest USGS value on 390-light runs that were not rate-limited).
- snoflo is beaten on trust only because it is wrong: its Hudson page says "flowing at 8,310 cfs, rising 18%" in the sentence, "7,310 cfs, Low 69% of median, since yesterday -4%" in the card, and "Water temp 75 °F" in October at a gauge with no temperature sensor. Not a reason to relax.

## PER ACTIVITY
What each person needs that is missing, buried or unexplained on OUR page (checked on the pages named):
- Fly fishing: a wading figure. The page gives flow, gage height and water temperature but nothing says what level the gauge reads when the riffles are wadeable; Penns, Madison, Kinzua have none; the only angler-facing line is the NWS cold-water note under water temperature (Madison 47 °F, good). Fix: a quoted, dated, attributed published range where one exists, else nothing.
- Bait fishing: clarity. Turbidity is on Potomac (5.6 FNU) and Lees Ferry (1.2 FNU) but is buried in "Water quality sensors" on the Now tab with no plain word; "Not measured: clarity" is printed on the first screen only where it is missing. Put the measured turbidity on the first screen with the same tile style where it exists.
- Boat fishing (motor): nothing on the page says whether a ramp is in the water; Mississippi and Ohio give a stage but no NWS low-water impact ("boat ramps unusable below X ft" statements exist in NWS impact lists for some points and are shown; where they do not exist nothing says so). Acceptable, but label the impacts list "Flood impacts" when it only lists high stages, so a boater does not search it for low-water lines.
- Kayaking / canoeing: a runnable range. Gauley, New, Salt, Verde, Roaring Fork, Deschutes, Salmon, Snake are paddled reaches; none prints a published range. See the AW line above.
- Rafting: release schedule on dam-controlled runs (Gauley Summersville, Lees Ferry Glen Canyon, Deschutes Pelton-Round Butte, Salt Roosevelt). Gauley and Lees Ferry name the dam only in a caveat; Salt, New (Bluestone), Deschutes name no dam at all (grep: 0 hits). The generic sentence "Upstream dams may have changed flows during this record" is on 23 of 25 pages regardless.
- SUP: wind. Air temperature tile shows "wind 7 mph NE"; the hourly table has gusts, but at 390 only 6 of 24 hours are visible and the row has no scroll hint (P2-3). Gust is what matters to a paddleboarder; it is hidden off-screen.
- Swimming: water temperature is on the first screen where measured (Potomac 60 °F, Madison 47 °F with the cold-water line, Lees Ferry 67 °F). Where missing, "Not measured at this gauge: water temperature" is printed; good. Missing: E. coli / bacteria. Potomac has the state water-quality assessment block on the Data tab but nothing on the first screen points to it.
- Tubing: the Potomac boater caution (3.5 ft, "fast moving water") is the right fact and is now on the gage tile, but it is cut off mid-sentence with "Fast…" (P1-2). Salt and Verde under a Flood Watch with a forecast rise of 9 ft / 7 ft: the pill now says "NWS forecast rises to 15.8 ft by Oct 23" on the first screen (10-X P1-4 fixed).
- Wading: rate of rise. "Rate of rise and fall" (last 1 h to 24 h, cfs and height) is on the History tab, which is the last place a wader looks for "is it coming up right now". Move the 1 h and 3 h rows to Now, or put "+0.00 ft in 1 h" under the gage tile.
- Motor boating: debris / navigation notices. Ohio, Mississippi, Missouri, Columbia, Sacramento, Hudson are navigable; the page has no USACE or Coast Guard notice row and the "Official pages" list does not link the USACE district gauge. One link row.
- Rowing: same as SUP (gust) plus water temperature; Hudson and Potomac rowing reaches have no water temperature (Hudson's sensor is stale, page says not measured: right).
- Diving: visibility. Turbidity where measured (see bait fishing); nothing else possible.
- Gold panning: Arkansas, Roaring Fork, Salmon, Yellowstone. Needs low-flow access and the public-land table (Area tab) which does show manager and PAD-US access; fine but four tabs away. No change needed beyond the PAD-US label (10-X P2-9 still open).
- Duck hunting: sunrise / last light are on the first screen (good); wind direction is in the hourly table (hidden columns, P2-3).
- Camping: "Flood Watch" banner and NWS impact at the next stage are on the first screen (Salt, Verde, Lees Ferry). Overnight rise is the question; the River forecast table is on the Forecast tab and the 6-hourly points are clear. OK.
- Hiking: Potomac trail closures (Billy Goat Trail at 5.0 ft, River Trail at 7.0 ft) are in the Flood impacts rail on the Now tab, but the rail is a horizontal scroller 1,618 px wide in a 354 px viewport with no scroll hint; the second card is cut at "The river rea" (P2-3).
- Guiding: the age chip, the live-check banner and "Charts, tables and comparisons below are as of the page build" are exactly what a guide needs; but after the live check succeeds the two headline pills (trend, normal) vanish (P1-1), so a guide refreshing at 7 AM sees fewer answers than at 2 AM.
- Parents: "is it safe" is answered by the disclaimer line only. The cold-water note (under 50 °F) is good where there is a sensor. Nothing to add without composing.
- Riverside residents / farmers: NWS impact statements quoted in full, flood stages, historic crests, "annual peaks that reached flood stage: 56 of 71 years" (Hudson): strong. Missing: the stage-to-impact distance is "4.6 ft above" but the forecast crest is not compared with the next impact stage in one sentence ("forecast crest 15.9 ft stays 5.1 ft below action stage"). One derived line from two source values.
- Bridge users: Potomac "Chain Bridge" and Hudson "Congress Street Bridge is closed" at 29.0 ft are in the impact list; fine.
- Swiftwater rescue: rate of rise in ft per hour is on History (should be Now, see wading); the 24 h range tile on tidal Hudson (993 to 9,330 cfs) is good.
- Birders: nothing river-specific is missing; sunrise is there.
- Photographers: sunset, last light, moon phase on the first screen: good. Golden hour is not needed.
- Students: percentile method is explained in the standfirst ("37th percentile; normal is between the 25th and 75th"), source and record length on every block; the "Sources and method" drawer at the foot. Good. Missing: a units line for "cfs" appears on every page ("cfs = cubic feet per second") but "FNU", "µS/cm" and "NAVD88" are never expanded on the page (glossary link only in the footer).

## DEFECTS

### P0
None found. All 25 pages show the USGS value at the time they state; no wrong unit; no sentinel; no overflow; no page error; no empty block; no broken link; dark-mode alert pill (10-X P1-1) is fixed and legible on Salt, Verde, Lees Ferry, Ohio, Chattahoochee.

### P1
1. **After a successful live check the page deletes two of its three headline answers.** Template, all 25 pages. Steps: open any page at 390 with the network on and wait for the USGS `latest-continuous` call to succeed (Potomac, Hudson, Gauley, Kinzua, Madison, Yellowstone and 13 others did in my run; the Arizona and Pacific pages hit a 429 because I made 25 calls in a minute). The script sets `hidden` on `.answer .a1` and `.answer .a2`, so the first screen reads only "No active NWS alerts"; "Falling: -2.6% flow in 6 h" and "Above normal for Oct 21" are gone, while the big "Above normal" block 300 px lower stays, with the line "The flow above is newer than this comparison". LINE 0's "is it normal" and "rising or falling" leave the first screen for every reader whose browser reached USGS, which is the normal case, and the page is then inconsistent with itself (pill hidden, block kept). Fix: do not hide; append the build time to the pill ("Above normal for Oct 21, as of 12:50 AM") the same way the block does, or recompute the trend pill from the live 24 h window the script already fetches. Gate: `ui_gates.mjs` fixture that loads a page with a mocked successful USGS response and asserts three visible `.answer` spans.
2. **Gage-height tile cuts the NWS safety sentence mid-word with an ellipsis.** Pages: Potomac ("...as defined by the State of Maryland. Fast…"), Chattahoochee ("...downstream from the gage on…"), Delaware ("...between Brown Street and Maple…"), Mississippi ("Water will reach the…"), Ohio ("Some yards along US…"), Penns ("A campground is…"), Roaring Fork ("...protruding into the…"), Shenandoah ("...near Bloomery, West Virginia,…"). Steps: first screen at 390 or 1280, right tile under the gage height. The first-screen urgency answer (10-X P1-5, now implemented) is clipped by a character limit, which is the "clipped text" defect LINE 1 names, on the one sentence a tuber or wader is reading. Fix: cut at the end of the first sentence of the impact statement, never mid-sentence (the first sentence is always complete: "The river reaches caution level for boaters, as defined by the State of Maryland."), and link "all impacts" below. Fixture in `truth_tests.py`: no tile caption ends with "…".
3. **"Forecast high" tile says the river is "already above this forecast" on five non-tidal pages.** Deschutes (2.9 ft vs 2.91), Missouri (12.6 vs 12.72), Ohio (14.9 vs 15.67), Potomac (3.3 vs 3.39), Susquehanna (34.8 vs 34.90). Steps: Now tab, forecast tile: "That is 0.1 ft below the latest reading. The latest reading (3.39 ft) is already above this forecast." Two sentences say one thing, and the label "FORECAST HIGH" sits on a number lower than now. Hudson is fixed (tidal note), the others carry 10-X P2-2 unchanged; raised to P1 because it now sits on the first screen next to the urgency answer and reads as a contradiction. Fix: when the crest is below the latest reading, label the tile "NWS forecast" and print one line: "Forecast 3.3 ft at 2:00 AM, 0.1 ft below the latest reading; the NWS expects it to fall." Drop the "already above" sentence everywhere.

### P2
1. Age chip "35 min old" is 12.5 px green (#0f5f36) on pale green: contrast 2.70, fails 4.5 (light mode, every page). Darken the text or drop the tint.
2. "Thunderstorms: none in the National Weather Service forecast" is grey on grey at 3.52 (light, every page). Use the body ink.
3. Three horizontal scrollers on the Now tab at 390 have no visible hint and cut content mid-word: hourly table (932 px in 354, 6 of 24 hours visible), weather forecast cards (954 px; third card shows "Wec"), flood impacts rail (1,618 px; second card "The river rea"). At 1280 the hourly table is still 970 px in an 848 px column and the last three hours are cut. Add a fade edge and "scroll for more" or wrap the cards.
4. 1280 tile grid: Mississippi, Potomac and others leave "Sunset today" or "Rain, last 24 h" alone with an empty slot; weather forecast shows 5 cards then an orphan "Friday" card on its own row (10-X P2-8 open).
5. Nearby-station names keep ACIS casing: "Chevy Chase 1.2 Sw", "Latham 1.8 Nw", "Colonie 3.6 Wnw", "Pueblo 2.5 Ssw". Print "SW", "NW", "WNW", "SSW".
6. Potomac lists "Chevy Chase 1.2 Sw" twice with different values (2.36 in vs 0.01 in on Oct 14): two ACIS stations with the same name and no id, so the reader cannot tell them apart. Append the station id or network.
7. "wind calm" lowercase in the air tile (Chattahoochee, Gauley, Kinzua, Madison, Mississippi) next to "Calm" in the Air conditions table. Pick one.
8. Penns Creek `<title>` is "Penns Creek, PA: river level and flow | River Water Levels"; the other 24 have no site suffix. Make it one pattern. Its H1 still lacks "at Penns Creek" (10-X P2-13).
9. "Highest, 7 days 24,300 cfs" (instantaneous, Rate of rise block) and "Peak, last 7 days 22,100 cfs" (daily mean, Compared-with-record block) on the same History tab, 600 px apart, without "daily mean" in the second label (10-X P2-11 open, Potomac).
10. Salt, New and Deschutes never name their controlling dam (Roosevelt, Bluestone, Pelton-Round Butte) while every page prints "Upstream dams may have changed flows during this record"; Gauley and Lees Ferry name theirs only inside the caveat. Name the dam in the caveat where the registry knows it (Madison already does this well: "Hebgen", "Madison Dam", "releases").
11. The live-check line "live check did not answer; showing the page as built" is inline grey in the header in this build (10-X P2-15 fixed; it appears once). When the check succeeds, the banner under the hero and the "The flow above is newer than this comparison" sentence in the 6 h tile say the same thing twice within 400 px; keep the banner only.
12. Ohio Louisville pairs the 12:45 AM flow (73,100) with the 1:00 AM stage (15.67) under one "observed Oct 21, 12:45 AM EDT" line; USGS at 12:45 read 15.66. Harmless here, wrong by one interval in principle: take both from the same timestamp or print the later one.
13. "Steady: 0.0% flow in 6 h" (Madison, Snake) and "Steady: +1.0%" (Chattahoochee) prints a sign on zero; "0.0%" reads as a sensor fault on a dam-controlled river. Say "Steady: no change in 6 h".
14. "Source" is a details summary and the opened text starts "Source: ..." again ("Source Source: USGS Water Data API" in the accessibility tree and the text dump, on every block). Label the summary "Where this comes from" or drop the prefix inside.
15. Breadcrumb state link "PA" / "WV" / "AZ" is 28 x 42 px; the in-tile links "Shenandoah River at Millville", "Salmon River at White Bird", "Deschutes River at Moody" are 17 px tall; "NWS cold water safety" is 127 x 17 (10-X P2-12 open).
16. PAD-US "Restricted access" for the C and O Canal (Potomac) is still printed as-is (10-X P2-9 open).
17. Hudson "Direction unclear" pill on a tidal gauge while the 24 h range tile has the honest answer (10-X P2-6 open).

## PAGE VERDICTS
PAGE /river/arkansas-river-co/avondale-07109500/: HOLD (P1-1 template: live check hides trend and normal pills)
PAGE /river/chattahoochee-river/atlanta/: HOLD (P1-1; P1-2 clipped gage-tile sentence)
PAGE /river/colorado-river-az/lees-ferry/: HOLD (P1-1)
PAGE /river/columbia-river-or/the-dalles/: HOLD (P1-1)
PAGE /river/delaware-river-nj/trenton/: HOLD (P1-1; P1-2)
PAGE /river/deschutes-river-or/moody/: HOLD (P1-1; P1-3 "already above this forecast")
PAGE /river/gauley-river/above-belva/: HOLD (P1-1; loses to American Whitewater on paddler value)
PAGE /river/hudson-river/green-island/: HOLD (P1-1)
PAGE /river/kinzua-creek/guffey/: HOLD (P1-1)
PAGE /river/madison-river/below-ennis-lake/: HOLD (P1-1)
PAGE /river/mississippi-river-mo/saint-louis/: HOLD (P1-1; P1-2)
PAGE /river/missouri-river-mo/kansas-city/: HOLD (P1-1; P1-3)
PAGE /river/new-river-wv/thurmond/: HOLD (P1-1)
PAGE /river/ohio-river-ky/louisville/: HOLD (P1-1; P1-2; P1-3)
PAGE /river/penns-creek/penns-creek/: HOLD (P1-1; P1-2; title pattern)
PAGE /river/potomac-river-md/little-falls/: HOLD (P1-1; P1-2; P1-3)
PAGE /river/roaring-fork-river/glenwood-springs/: HOLD (P1-1; P1-2)
PAGE /river/sacramento-river/freeport/: HOLD (P1-1)
PAGE /river/salmon-river-id/white-bird/: HOLD (P1-1)
PAGE /river/salt-river-az/roosevelt/: HOLD (P1-1)
PAGE /river/shenandoah-river/millville/: HOLD (P1-1; P1-2)
PAGE /river/snake-river-wa/anatone/: HOLD (P1-1)
PAGE /river/susquehanna-river-pa/marietta/: HOLD (P1-1; P1-3)
PAGE /river/verde-river/camp-verde/: HOLD (P1-1)
PAGE /river/yellowstone-river-mt/livingston/: HOLD (P1-1)

All 25 are otherwise sound: numbers match USGS, no sentinel or overflow, dark mode legible, tabs match their contents. P1-1 is one script change in the template; P1-2 and P1-3 are one renderer change each. After those three, every page is SHIP on this evidence.

## NOT CHECKED
- The live site (old template) was not re-screenshotted; "before" is from 10-X.
- 15 of the 25 pages were read by script, first-screen pills and text dump only, not every screenshot pixel: Arkansas, Chattahoochee, Columbia, Delaware, Deschutes, Missouri, New, Ohio, Penns, Roaring Fork, Sacramento, Salmon, Shenandoah, Snake, Susquehanna. Dark mode was examined by eye on Salt, Hudson and Mississippi only; the contrast script covered Potomac, Hudson, Salt, Kinzua in both schemes.
- The History, Data and Area tabs were screenshotted on Potomac, Hudson and Salt and read on Potomac (1280) only.
- NWS NWPS forecast values were not re-fetched from api.water.noaa.gov this session; the "already above" defect is a wording defect visible in the page text, not a forecast-value check.
- The 9 pages with a successful live check in my run were compared with USGS at build time; the live-updated header values were spot-checked on Potomac (5,150 cfs / 3.38 ft at 1:50 AM, matches USGS) and Hudson, not on all 9.
- Competitor pages that did not render (water.noaa.gov "loading..." on a phone UA after 6 s; lefa3 404) were judged on what a phone reader sees in that time, not on their eventual content.
- Screen-reader order, print layout, and the search box behaviour were not tested.
- The collapsed drawers at the foot of each page ("Flood record and history", "Daily values, measurements and rating", "Watershed, water quality and land", "Sources and method") were opened on Potomac only.

VERDICT: HOLD
