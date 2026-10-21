# FRESH-REVIEW-10-Z: template hash 8309e9eea73c1430

Re-verification of FRESH-REVIEW-10-Y on the rebuilt `dist_next/`, 2026-10-21 about 08:20 to 08:50 UTC. `python -I tools/template_hash.py` printed `8309e9eea73c1430` (matches). Served from 127.0.0.1:8787. No code or data edited.

## Method
- Playwright rendered Potomac Little Falls, Deschutes Moody, Chattahoochee Atlanta, Salt Roosevelt, Madison below Ennis Lake and Penns Creek at 390 light (network on, one page every 8 s), 390 dark, 1280 light and 1280 dark (24 renders). Per render: overflow, sentinel words, console errors, `.answer` pill visibility, hero tile text, age-chip and thunderstorm-line contrast, ellipsis, "already above", ACIS compass casing, "wind calm", "Steady: 0.0%", fold label.
- The real USGS `latest-continuous` call still returned 429 for my address (left over from the Y run), so P1-1 was verified with a mocked successful response (Playwright route returning a 20-minute-old 5,150 cfs / 3.38 ft feature set) on Potomac and Salt, light and dark, plus screenshots.
- All 25 rebuilt pages scanned from their HTML text for: ellipsis, "already above", compass casing, "wind calm", "Steady: 0.0%", sentinel words, title suffix, "Source Source", the gage-tile caption and the forecast-tile label and line.
- Screenshots read by eye: Potomac 390 light (mocked live success), Salt 390 dark, Deschutes 1280 light.
- Numbers: not re-fetched from USGS this run; the build data is the same snapshot as Y (same observation times and values on every page checked), where all 25 matched USGS.

## #1 COMPARISON
The comparison in FRESH-REVIEW-10-Y was done on hash 927463f2a915ed1c; the competitor pages were not re-opened. Nothing in this rebuild changes a BEAT/TIE/LOSE cell except that the three P1 defects that made our first screen weaker than the build (hidden pills, clipped safety sentence, "already above" contradiction) are gone, so the answer-speed BEATs now hold with the network on as well as off. Table reused:

| page | competitor 1 | competitor 2 | competitor 3 |
|---|---|---|---|
| /river/colorado-river-az/lees-ferry/ | USGS 09380000: BEAT / BEAT / LOSE / BEAT / BEAT | water.noaa.gov (lefa3 404; NWPS "loading..." on phone): BEAT / BEAT / LOSE / BEAT / BEAT | snoflo Arizona state report: BEAT / BEAT / BEAT / BEAT / BEAT |
| /river/hudson-river/green-island/ | snoflo Hudson at Green Island: BEAT / BEAT / BEAT / BEAT / BEAT | USGS 01358000: BEAT / BEAT / LOSE / BEAT / BEAT | water.noaa.gov tryn6: BEAT / BEAT / LOSE / BEAT / BEAT |
| /river/kinzua-creek/guffey/ | USGS 03011800: BEAT / TIE / LOSE / BEAT / BEAT | howsyourriver.com Kinzua Creek: BEAT / BEAT / BEAT / TIE / BEAT | paflyfish.com threads: BEAT / BEAT / TIE / LOSE / BEAT |
| /river/mississippi-river-mo/saint-louis/ | USGS 07010000: BEAT / BEAT / LOSE / BEAT / BEAT | water.noaa.gov eadm7: BEAT / BEAT / LOSE / TIE / BEAT | news items: BEAT / BEAT / TIE / BEAT / BEAT |
| /river/gauley-river/above-belva/ | water.noaa.gov bvaw2: BEAT / BEAT / LOSE / TIE / BEAT | American Whitewater #2379: BEAT / TIE / TIE / LOSE / BEAT | snoflo Gauley above Belva: BEAT / TIE / BEAT / BEAT / BEAT |
| /river/madison-river/below-ennis-lake/ | fwp.mt.gov Madison: BEAT / BEAT / LOSE / TIE / BEAT | bigskyanglers.com report: BEAT / TIE / TIE / LOSE / BEAT | USGS 06041000: BEAT / BEAT / LOSE / BEAT / BEAT |
| /river/verde-river/camp-verde/ | USGS 09504950 / 09506000: BEAT / BEAT / LOSE / BEAT / BEAT | riverapp.net: BEAT / TIE / TIE / BEAT / BEAT | weather.gov/fgz 2021 flood page: BEAT / BEAT / LOSE / BEAT / BEAT |
| /river/yellowstone-river-mt/livingston/ | USGS 06192500: BEAT / BEAT / LOSE / BEAT / BEAT | water.noaa.gov livm8: BEAT / BEAT / LOSE / TIE / BEAT | flyanglersonline / nbcmontana: BEAT / BEAT / TIE / LOSE / BEAT |

LOSE fixes unchanged from Y: a named publisher and contact (trust vs every .gov; owner-waived 2026-10-20); a verbatim, attributed, dated published range and release date on paddled reaches (Gauley vs American Whitewater); an FWP restrictions link row (Madison vs Big Sky Anglers).

## PER ACTIVITY
Reused from FRESH-REVIEW-10-Y, with the two items this rebuild changed:
- Tubing / wading / parents: the first-screen urgency sentence is now complete on every page that has NWS impacts ("The river reaches caution level for boaters, as defined by the State of Maryland." on Potomac; "Water reaches the USGS wellhouse." on Salt; full sentences on Chattahoochee, Delaware, Mississippi, Ohio, Penns, Roaring Fork, Shenandoah). Done.
- Guiding: after a live update the pills now read "Falling: -2.6% flow in 6 h (as of Oct 21, 12:50 AM EDT)" and "Above normal for Oct 21 (as of Oct 21, 12:50 AM EDT)" under a header showing the newer value and "20 min old"; the banner under the hero states what is live and what is as of the build. Done.
- Still open from Y: wading level and runnable range (none; must be quoted and attributed or absent); turbidity on the first screen where measured; rate of rise on the Now tab rather than History; gust column hidden off-screen at 390; dam name on Salt, New, Deschutes; USACE / Coast Guard link row on navigable rivers; forecast-crest-versus-next-impact sentence for residents; FNU, µS/cm, NAVD88 never expanded on the page.

## DEFECTS

### P0
None.

### P1
None remaining. Verified this run:
1. Live-success pill hiding (Y P1-1): with a mocked successful USGS response, Potomac and Salt (light and dark) keep all three `.answer` spans visible; the trend and normal pills carry " (as of <build time>)"; the header shows the live value (5,150 cfs / 3.38 ft, 20 min old) and the hero banner says charts are as of the build. Screenshot read: the two long pills wrap to two lines at 390, legible, underlines intact.
2. Clipped gage-tile sentence (Y P1-2): 0 of 25 pages has an ellipsis in the gage tile; the caption ends at the first full stop of the NWS impact statement on all 17 pages that have one. The two remaining "..." hits on Chattahoochee ("athletic field at Lovett School...backyards") and Mississippi ("is overtopped. Also...at this") are inside quoted NWS impact statements further down, i.e. the NWS's own text, not clipping.
3. "Already above this forecast" (Y P1-3): 0 of 25 pages. Deschutes, Missouri, Ohio, Potomac, Susquehanna now label the tile "NWS forecast" and print one line, e.g. Potomac "0.2 ft below the latest reading (3.39 ft): the NWS expects the level to fall"; Missouri "It then falls to 10.8 ft by ..."; pages whose crest is above now keep "Forecast high".

Also verified fixed from the Y P2 list: age chip contrast 9.17 light / 9.30 dark (was 2.70); thunderstorm line 18.6 / 17.7 (was 3.52); ACIS compass casing (0 hits on 25 pages); "wind: calm" (Chattahoochee, Madison, Penns); "Steady: no change in 6 h" (Madison; Snake not re-rendered but the build text has no "0.0%"); fold label "Where this comes from" (0 "Source Source" strings); one title pattern (Penns Creek no longer carries the site suffix).

### P2 (remaining, carried from Y)
1. Three horizontal scrollers on the Now tab at 390 with no hint (hourly table, weather forecast cards cut at "Wec", flood impacts rail cut at "The river rea"); hourly table also cut at 1280.
2. 1280 tile grid orphans ("Sunset today" alone; "Friday" weather card alone).
3. Potomac lists "Chevy Chase 1.2 SW" twice with different values; no station id to tell them apart (casing fixed, duplication not).
4. "Highest, 7 days" (instantaneous) vs "Peak, last 7 days" (daily mean) on the same History tab without "daily mean" in the label.
5. Salt, New, Deschutes never name their controlling dam; Gauley and Lees Ferry only inside the caveat.
6. Banner under the hero and the "flow above is newer than this comparison" sentence in the 6 h tile say the same thing twice after a live update.
7. Ohio pairs a 12:45 flow with a 1:00 stage under one observed time.
8. Breadcrumb state link 28 x 42 px; in-tile links 17 px tall; "NWS cold water safety" 127 x 17.
9. PAD-US "Restricted access" printed as-is for the C and O Canal.
10. Hudson "Direction unclear" pill on a tidal gauge.
11. Penns Creek H1 still lacks "at Penns Creek".
12. New: with "(as of ...)" appended, the Salt trend pill is 95 characters ("Falling: -2.8% flow in 6 h; NWS forecast rises to 15.8 ft by Oct 23, 5:00 PM MST (as of Oct 20, 10:30 PM MST)") and takes three lines at 390. Consider putting the as-of time once on the row rather than on each pill.
13. New: when the NWS alerts call fails and the build is over 2 h old the third pill becomes "NWS alert check is old" (seen on every network-blocked 1280 render). Honest, but the wording does not say what the last answer was; "No alerts as of 1:44 AM (check failed)" would.

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
- The real live USGS call could not be exercised (429 from my address); P1-1 is proven with a mocked response on Potomac and Salt only. The 429 path itself (grey "live check did not answer" line, pills unchanged) was seen on all six pages.
- Only 6 of 25 pages were re-rendered; the other 19 were checked from the rebuilt HTML text for the fixed patterns, not screenshotted on this hash.
- USGS values were not re-fetched this run; the build snapshot is unchanged from Y where all 25 matched.
- Competitor pages were not re-opened; the comparison table is from the previous hash.
- Tabs other than Now, the collapsed drawers, dark-mode screenshots other than Salt 390, and the 1280 dark renders were checked by script (contrast, overflow, sentinels) only.
- Snake River "Steady: no change" wording and the Potomac duplicate-station rows were checked in HTML text only.

VERDICT: SHIP
