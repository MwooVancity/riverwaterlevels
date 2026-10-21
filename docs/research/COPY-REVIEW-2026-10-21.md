# Copy review, 2026-10-21 (dist_next, 49 pages)

Method: every page's visible text was extracted by script (html.parser; tags stripped; meta description, alt, aria-label and title attributes kept) into one text file per page, then 31 pattern checks ran over all 49 files (unit spelling, time and date formats, British spelling, credit lines against `data/sources.json`, Source lines without Credit, leaked qualifier letters, lowercase after a full stop, decimals on cfs). The Potomac, Hudson, Delaware, Lees Ferry, Kinzua and home pages, and About, Privacy, Methodology, Disclaimer, Data sources, FAQ, Glossary, Data status and the Maryland state page were read in full by eye. Trust-page claims were checked against `lib/directory.py`, `lib/hero.py`, `lib/core.py`, `lib/blocks2.py`, `lib/blocks3.py`, `lib/page.py`, `collect.py`, `.github/workflows/refresh.yml`, `templates/_headers`, `data/publisher.json` and the built HTML.

## VERDICT

**No.** I would not sign off tonight. Three trust pages state things the built site does not do (a Save gauge button, a CSV download, FEMA and NCEI records on gauge pages, a Cloudflare analytics script); the About page does not say that the site has no publisher contact although `data/publisher.json` records that waiver; one Source line prints a sentence starting lowercase on four pages; the Kinzua tile calls the Allegheny "this river"; five block labels name the wrong source ("Official NWS" on NOAA tide predictions, "Weather station" on EPA air quality); values leak raw source codes ("0.00A", "NEW", "N/A"). Every one of these is a template fix in `lib/`, so one review round would clear them. The rest is a style sheet: the site mixes British and American spelling, four date formats and three time formats, and the first phone screen says the same alert and the same comparison twice.

## DEFECTS (worst first)

1. **False claims on trust pages (Privacy, Methodology, About).** Page: /privacy/ "The Save gauge button keeps a short list of gauge links in your browser's local storage" — no page contains a Save gauge control (grep "Save gauge" over dist_next: 0 pages; `localStorage` is used only for the theme key `rwl_theme`). Replacement: "The dark or light switch stores your choice in your browser's local storage, on your device only; nothing is sent to us." Page: /methodology/ "The CSV download is built in your browser from the USGS API for the last 7 days of flow and gage height." — no page has a CSV control (0 pages). Replacement: delete the sentence. Page: /about/ "USGS, NWS, NOAA, FEMA, EPA, NCEI and USDA records for one location joined on one page" and /methodology/ "Flood history for the county ... NOAA NCEI Storm Events ... FEMA's OpenFEMA" — no gauge page shows a FEMA or NCEI block (0 pages contain "Storm Events" or "OpenFEMA"). Replacement for About: "USGS, NWS, NOAA, EPA and USDA records for one location joined on one page, each with its source and time." Replacement for Methodology: delete the "Flood history for the county" section until the block ships. Printed by `lib/directory.py` (`trust_pages` strings, lines ~197-245).

2. **Publisher waiver not stated on About.** `data/publisher.json`: email "", waived "wave 0 opens without a publisher contact". /about/ names no publisher, no contact and does not say one is missing. A quality rater reads that as anonymous. Replacement (add under "What this site is not"): "Who runs it: River Water Levels is an independent site. A contact address is not yet published; corrections are handled as described on the Methodology page." Print in `lib/directory.py` About section.

3. **Lowercase sentence start in a Source line.** Page: Lees Ferry (also every gauge with a forecast but no flood stages: 4 pages per the "lowercase after period" check). Current: "observed to Oct 21, 7:00 AM MST. the forecast (dashed curve) from National Weather Service forecast point CLFA3". Replacement: "observed to Oct 21, 7:00 AM MST. The forecast (dashed curve) is from National Weather Service forecast point CLFA3". File: `lib/blocks2.py` line 107, `what = " and ".join(...)`; capitalise the first letter of `what`.

4. **"Nearest on this river" names another river.** Page: Kinzua Creek. Current: "No sensor at this gauge. Nearest on this river: Allegheny River Below Kinzua Dam At Big Bend, PA, 16 mi away, USGS sensor 03012545". The Allegheny is not Kinzua Creek, and the gaps line on other pages promises "on this river". Replacement: "No sensor at this gauge. Nearest USGS water temperature sensor: Allegheny River below Kinzua Dam at Big Bend, PA, 16 mi away (a different river), sensor 03012545, Oct 21, 8:45 AM EDT." File: `lib/hero.py` line 245; also the `.title()` call there produces "Below ... At" (capitalised prepositions).

5. **Block tags name the wrong source.** Tides block (NOAA CO-OPS) carries the tag "Official NWS"; Air quality (EPA AirNow) carries "Weather station"; Hourly forecast on Kinzua carries "Official NWS" (correct) but the same tag family puts "Live gauge" on the camera and on the flow chart and "Agency data" on state water quality. Readers take a tag as the source. Replacement: tides tag "NOAA tide table"; air quality tag "EPA monitor"; or drop the tag and let the Source line carry the source. File: `lib/core.py` line 18 `TAGS` and the tag argument in `lib/blocks3.py` line 338 (`"official"`) and the AirNow block (`"obs"`).

6. **Raw source codes printed as values.** (a) Delaware, Salt, Verde rain-station tables: "0.00A", "0.13A" (ACIS accumulation flag). Replacement: "0.00 in" with the flag dropped, or "–". File: `lib/blocks3.py` line 88, the `cell` lambda handles "A" alone, not a trailing "A". (b) Delaware air quality row: "PM10 | 14 | Good | NEW" — monitor column shows "NEW". Replacement: print the site name or leave the cell blank. (c) Kinzua recreation table: phone "N/A". Replacement: blank cell. File: RIDB block in `lib/blocks3.py`.

7. **One screen, same fact twice.** Lees Ferry first screen: banner "1 active National Weather Service alert" and, two lines down, pill "1 active NWS alert"; pill "Unsteady: -8.4% flow in 6 h" and tile "Change, last 6 h -8.4% Unsteady"; pill "Below normal for Oct 21" and tile "Is this normal for Oct 21? Below normal". Lees Ferry alert card: "until October 22 at 11:00PM MST" (NWS text) and "Ends Oct 22, 11:00 PM MST" on the next line. Replacement: keep the banner and drop the alert pill when a banner is shown; keep the tiles and drop the direction and comparison pills (they repeat the tile headline word for word); drop the "Ends" line when the quoted headline already gives the end. File: `lib/hero.py` `answer` (lines ~283-290) and `ui.banner`; alerts block in `lib/render.py`/`blocks`.

8. **Forecast tile prose runs to four sentences.** Lees Ferry: "first reached Oct 21, 8:00 AM MST · NWS point CLFA3 / 0.9 ft above the latest reading (about 8,000 cfs by the NWS rating); falling now, the NWS expects a rise. / Then falls to 7.1 ft by Oct 27, 5:00 AM MST. / For 8:00 AM MST the forecast was 8.1 ft; the gauge reads 7.18 ft now. Forecasts at gauges below dams and in tidal reaches can run out of step with the readings." Hudson: "first reached Oct 21, 2:00 PM EDT · NWS point TRYN6 (named “Hudson River at Troy”, not this gauge’s place)". Replacement (one line under the number): "Oct 21, 8:00 AM MST · NWS point CLFA3 · 0.9 ft above now, then down to 7.1 ft by Oct 27" and move the dam/tidal note to the River forecast block. File: `lib/hero.py` lines 205-224.

9. **Advice sentence on the water-temperature tile.** Every gauge under 60°F: "Below 60°F: cold-water shock risk on immersion; a wetsuit or PFD matters (NWS cold water safety)." CLAUDE.md allows no composed sentences beyond labels and verbatim source text; "PFD" and "immersion" are jargon. Replacement: "Under 60°F: NWS cold water safety" as a link, nothing else. File: `lib/hero.py` lines 240-241.

10. **Water temperature and air temperature print the unit differently.** Tile: "59°" then "F" (degree sign attached to the number, F as the unit); Air temperature: "59" then "°F". Replacement: number "59", unit "°F" on both. File: `lib/hero.py` line 243 and 245 (`'%.0f&deg;<small>F</small>'`) to match line 274.

11. **Tile without a time.** Potomac "Upstream gauge now 1,330 cfs / Shenandoah River at Millville" has no observed time (the rule is label, number, unit, one line, time). Replacement line: "Shenandoah River at Millville · Oct 21, 10:30 AM EDT". File: `lib/hero.py` line 248.

12. **"Next NWS impact at 3.5 ft, 0.2 ft above"** (Potomac, Hudson, Delaware gage height tile): "above" what. Replacement: "Next NWS impact statement at 3.5 ft, 0.2 ft higher than now". File: `lib/hero.py` line 349 `next_impact`.

13. **"This reach is tidal: a net level, compare with the day's range."** (Potomac, Hudson, Delaware forecast tile). Replacement: "Tidal reach: the NWS forecast is a net level; compare it with the day's range on the flow tile." File: `lib/hero.py` line 213.

14. **Safety line reads twice.** Every gauge page: "no alert does not mean conditions are safe" and "It shows the readings a person uses to judge whether to fish, paddle, swim, tube or wade today; the judgement is yours." Replacement: "Government data, shown with the time it was observed or issued. It is not a flood warning. No alert does not mean the water is safe; the decision is yours. Disclaimer". File: `lib/page.py` line 168 `SAFETY`.

15. **Empty table shown as silence.** Kinzua "Historic crests" prints the header "Crest stage" and then the Source line with no rows and no sentence (valid-empty must be a sentence). Replacement: "The NWS lists no historic crests for forecast point GUFP1." File: historic crests block (`lib/blocks3.py`/`blocks2.py`, grep "Historic crests").

16. **"Gage height at page build (USGS)"** (stage table, every gauge): "page build" is our jargon. Replacement: "Latest USGS gage height". File: `lib/blocks2.py` line 86.

17. **Jargon printed without a gloss** (gauge pages): "Height above MLLW" (tides), "Has TMDL", "Cycle", "4A", "POTTF" (water quality table), "NowCast AQI", "FNU", "µS/cm", "NAVD88", "method record-v1", "parameter 00010", "NHDPlus reach 4512772", "NWIS rating depot, expanded shifted rating, 4,000 rows, thinned to 92 points", "(IN MLLW)". Replacement: "Height above the tide datum (MLLW)"; "Has a cleanup plan (TMDL)"; drop "method record-v1", "parameter 00010", "NHDPlus reach N" and the rating-depot sentence from Source lines (keep "USGS rating table for the gauge, thinned for display"); strip "(IN MLLW)" from forecast-point names. Files: `lib/blocks3.py` 338; `lib/blocks2.py` 302; `lib/charts.py` 220; `collect.py` 742 (`method`), rating block.

18. **Percentile method line is code-speak.** Every gauge, Sources fold: "Percentile method: trailing 24 h mean vs USGS daily percentiles for calendar date 10-21." Replacement: "Percentile: trailing 24-hour mean compared with USGS daily percentiles for Oct 21." File: `lib/page.py` line 150 prints `G["method"]` from `collect.py`.

19. **State page plural.** /rivers/md/: "Rivers in Maryland — 1 rivers, 1 gauges". Replacement: "Rivers in Maryland: 1 river, 1 gauge". File: `lib/directory.py` line 152.

20. **Home page.** "Live river levels and flows for US rivers & creeks" (ampersand; "Live" while readings are up to 73 min old). Replacement: "River levels and flows for US rivers and creeks". "Flow and water level for 25 gauges across the US, from USGS gauges and the National Weather Service." Replacement: "Flow and water level at 25 USGS gauges across the US, with National Weather Service forecasts and alerts." Table header "24 h" over values like "+4%". Replacement: "24 h change". Legend "Gauge colour". Replacement: "Gauge color". Unlabelled line "Northeast 5 · Midwest 2 · South 6 · West 12". Replacement: "Gauges by region: Northeast 5 · Midwest 2 · South 6 · West 12". File: `lib/directory.py` home (lines ~45-130).

21. **Time formats, three styles on one page.** Site style "Oct 21, 10:50 AM EDT"; tides table "04:44 2026-10-21" (24-hour, ISO date); AirNow "2026-10-21 10:00 EDT"; hourly header "11a 12p" (fine as a compact axis); NWS alert text "October 21 at 5:53AM MST" (quoted, leave). Replacement: tides "Oct 21, 4:44 AM" and AirNow "Oct 21, 10:00 AM EDT". Files: `lib/blocks3.py` tides rows (line ~330) and AirNow block.

22. **Date formats.** "October 1 to 19, mean flow" (record block) vs "Oct 26 to Oct 30" (outlooks) vs "Last reviewed October 17, 2026" (methodology) vs "calendar date 10-21". Replacement: "Oct 1 to 19"; "Last reviewed Oct 17, 2026". Files: record block in `lib/blocks3.py`; `lib/directory.py` 245.

23. **British spelling on a US site (79 hits, 27 pages):** "centred" (map alt and Source, `lib/page.py` 57-58), "colour" (`lib/directory.py` 65), "labelled" (`lib/directory.py` 202), "judgement" (`lib/page.py` 168), "Modelled flow" (`lib/forecast.py` 79, `lib/blocks2.py` 230), "Levelling off" (`lib/hero.py`, glossary). Replacement: centered, color, labeled, judgment, Modeled, Leveling off.

24. **Metric inside an imperial page.** "4 km grid", "within about 400 m of the gauge", "0.013 per sq km" (dam density) beside "sq mi", "mi", "in". Replacement: "about 2.5-mile grid", "within about a quarter mile", "per sq mi" (convert) or drop dam density. Files: rain block Source (`lib/blocks3.py`), ATTAINS Source (`lib/blocks2.py` 302), StreamCat block.

25. **Decimals on cfs where the page elsewhere uses whole numbers.** Kinzua and 12 other pages: "+0.00 cfs", "-0.60 cfs", "6.6 cfs", "+4.0 cfs". Replacement: whole cfs ("0 cfs", "-1 cfs"); use one decimal only under 10 cfs and apply it everywhere on the page. File: `fmt` in `lib/core.py` and the rate-of-change rows in `lib/blocks3.py` ~200.

26. **Wind written three ways.** Tile "wind 10 mph NNE" / "wind: calm"; Air conditions table "NNE 10 mph" / "Calm"; forecast "Wind 0 mph". Replacement: "wind NNE 10 mph", "wind calm" everywhere. Files: `lib/hero.py` 272, air block in `lib/weather.py`.

27. **Source names in all caps or source-cased.** "GREENBELT PARK PICNIC AREAS", "RED BRIDGE (PA)", "COLORADO RIVER AT LEES FERRY, AZ" (USGS site name), "Bradford 4Sw Res 5", "Page Municipal Ap", "Kane Exp. Forest", "Showers And Thunderstorms", "Slight (At Least 15%)". Quoted text may stay source-cased, but the recreation and station names are labels, not quotes. Replacement: title-case the RIDB and ACIS names ("Greenbelt Park Picnic Areas"); expand "Ap" to "Airport".

28. **Fold summary lists read as run-on.** "3 sections: Largest annual peaks, Flood frequency: peak flows, Historic crests". Replacement: separate with " · " and drop the inner colon ("Flood frequency of peak flows").

29. **Hudson quotes an NWS typo without a sic.** "Village of Wateford" is in the NWS impact statement. Leave the quote; nothing to change, but the editor should know it is the source's.

30. **About contradicts CLAUDE.md on forecasts.** /about/: "Where the National Weather Service issues a river forecast for the gauge, the same page has a Forecast section." Every page has a Forecast tab (Kinzua shows "River forecast: Not issued" and the tab). Replacement: "Every page has a Forecast section: the National Weather Service river forecast where one is issued, otherwise the words Not issued, with the weather forecast and rain outlooks." File: `lib/directory.py` 197.

## STYLE SHEET

1. Spelling: American (color, centered, labeled, judgment, modeled, leveling).
2. Units: cfs, ft, in, mph, °F (number then a space then the unit, except °F and % which close up: "59 °F" in tables is wrong; "59°F"); sq mi; mi; no metric except in a quoted source name.
3. Times: "Oct 21, 10:50 AM EDT" everywhere, gauge-local, zone abbreviation once per line; the hourly axis may use "11a 12p".
4. Dates: "Oct 21, 2026"; ranges "Oct 26 to 30" or "1981 to 2010"; never ISO, never full month names.
5. Durations: "24 h", "6 h" in labels and chips; "24 hours" only inside a sentence.
6. Numbers: thousands comma; whole cfs; stages two decimals (3.33 ft) for readings, one decimal for NWS stages (5.0 ft); percentages whole ("79%").
7. Separators: " · " between items on one line; ";" only inside quoted source text; no " — " and no " & ".
8. Labels: sentence case, noun phrase, no verb ("Latest flow", "Change, last 6 h", "24 h change"); a label must say what its column holds ("24 h change", not "24 h").
9. Tiles: label, number, unit, one line, time. One line means one line.
10. Source line: "Source: <agency product>, <period or fetch time>. <one caveat>. Credit: <credit from sources.json>." Credits exactly as in `data/sources.json`, once per source per block.
11. Tags: a tag names the publisher of the block (USGS, NWS, NOAA, EPA, USDA), never a kind of device.
12. Jargon: expand once per page, in parentheses, the first time; no internal ids (method names, parameter codes, reach ids, row counts).
13. Quoted source text (NWS statements, site names) stays verbatim; our labels around it are ours and follow this sheet.
14. Repetition: a fact appears once per screen; the pill row says only what the tiles do not.
15. No advice, no verdict words; a link to the agency's safety page is the most the page says.

## TRUST PAGES

| Claim | True? | Evidence |
|---|---|---|
| Privacy: "This site does not set cookies." | Unverified | No `Set-Cookie` or cookie JS in built pages; Cloudflare's edge may set none, not checked live. |
| Privacy: "Cloudflare Web Analytics: a script loaded from static.cloudflareinsights.com" | Not in the built pages | 0 of 49 pages reference cloudflareinsights; `templates/_headers` CSP (report-only) script-src is `'self' 'unsafe-inline'`, which would report that script. Either Cloudflare injects it at the edge (not verifiable here) or the sentence is false. |
| Privacy: browser contacts radar.weather.gov, basemap.nationalmap.gov, api.waterdata.usgs.gov, api.weather.gov | True but incomplete | `LIVE_JS` in `lib/page.py` fetches api.waterdata.usgs.gov; alerts fetch api.weather.gov; 4 camera pages also load images from usgs-nims-images.s3.amazonaws.com (CSP img-src lists it), which Privacy does not name. |
| Privacy: "Save gauge button ... local storage" | False | No such control; localStorage holds only `rwl_theme`. |
| Privacy: "Find gauges near me ... asks for your location only when you press it" | True | Home page only; `geolocation` string on 1 page (index). |
| About: "A scheduled job rebuilds the site about every 30 minutes" | True | `refresh.yml` cron "5,35 * * * *" (fast) and "20 3,9,15,21" (full). |
| About: "Your browser re-checks the newest USGS reading and NWS alerts when the page loads" | True | `LIVE_JS` fetch of latest-continuous; alerts JS present. |
| About: "readings older than 24 hours are not shown as current" | True | `LIMIT_TEXT` and the not-reporting tile in `lib/hero.py`. |
| About: "Rise and fall over 1, 3, 6, 12 and 24 hours" | True | Rate of rise and fall block, Lees Ferry and Kinzua pages show all five windows. |
| About: "USGS, NWS, NOAA, FEMA, EPA, NCEI and USDA records ... on one page" | False | No FEMA or NCEI block on any built page. |
| About: Forecast section only where NWS issues a forecast | Misleading | Every page has the Forecast tab; no-forecast pages print "Not issued". |
| About: no publisher name or contact | Waiver not stated | `data/publisher.json` email "" and a recorded waiver; About says nothing about it. |
| Methodology: percentiles 5,10,20,25,50,75,80,90,95; trailing 24-hour mean when 80% of readings and 20 hours span | True | `lib/hero.py` line 29: `len(win) >= 0.8 * 86400 / step` and `>= 20 * 3600`. |
| Methodology: daily mean needs 80% of readings | True | `collect.py` 763 and Source line "at least 80% of expected readings". |
| Methodology: rate windows "within 20 minutes or 60% of the reporting interval"; steady within 1% | True | `tol = max(1200, 0.6 * step)` in `lib/hero.py` 37, `lib/blocks3.py` 200; 1% in hero. |
| Methodology: lag r >= 0.85, 96 h overlap, 3% variation, 1 to 72 h | True | `collect.py` 970 docstring and Source line in `lib/page.py` 34. |
| Methodology: SNOTEL within 37 miles, three nearest | True | `lib/charts.py` 236 "within 37 miles"; `collect.py` 227 "3 nearest". |
| Methodology: water temperature months with fewer than 150 values marked | True | `lib/charts.py` 218 `n < 150`. |
| Methodology: freshness limits alerts 3 h, obs 3 h, rain 6 h, river forecast 24 h, hourly 12 h | True | `lib/core.py` 174 `LIMIT_TEXT` plus default "12 h". |
| Methodology: "Snow data older than 5 days and outlooks older than 3 days are hidden" | Unverified | No 5-day or 3-day constant found in `lib/`, `collect.py`, `build.py` or `gates.py`. |
| Methodology: "The CSV download is built in your browser" | False | No CSV control on any page. |
| Methodology: "Flood history for the county" (NCEI, FEMA) | False as shipped | Blocks not on any page; `data/sources.json` lists both as `quoted`, so the sources exist but nothing prints them. |
| Methodology: "Last reviewed October 17, 2026" | Stale | Four claims above are false today. |
| Disclaimer page | True | Same text as the gauge-page footer disclaimer (`DISCLAIMER` in `lib/page.py`); "labelled" British. |
| Data sources page | Mostly true | Lists FEMA and NCEI rows with credits although no block shows them; "Sources whose terms are not yet settled are not used" matches `off` rows (osm, nid, hdsc, waterwatch, usbr, fema_nfhl). |
| Corrections page | Absent | The brief lists a /corrections/ page; dist_next has none (`docs/CORRECTIONS.md` exists; Methodology carries a Corrections paragraph). |
| Credit lines | True | Every "Credit:" string on all 49 pages matches a `credit` in `data/sources.json`; none missing; the double "Credit: ... Credit: ..." on the stage chart and peaks-vs-flood-stage blocks is two sources, not a duplicate. Home-page map Source line has no Credit (it is a caption, not a block). |

## NOT CHECKED

- Live site (riverwaterlevels.com) and anything Cloudflare injects at the edge (analytics beacon, cookies); only dist_next was read.
- Rendered layout and contact sheets (`shots/`); this is a text review, so tile overflow, truncation and dark-mode contrast are unjudged.
- The 19 gauge pages not read by eye (Arkansas, Chattahoochee, Columbia, Deschutes, Gauley, Madison, Mississippi, Missouri, New, Ohio, Penns, Roaring Fork, Sacramento, Salmon, Salt, Shenandoah, Snake, Susquehanna, Verde, Yellowstone) were covered only by the pattern checks.
- 404 page, `_blocks.json`, `gauges.json`, `status.json`, sitemap and robots.
- Whether NWS-quoted text (impact statements, alert headlines, forecast wording) is verbatim against the NWS API; "Village of Wateford" was assumed to be the source's spelling.
- Numeric correctness of any value (percentiles, lags, conversions); only labels, units and wording were judged.
- The snow and outlook hide limits (5 days, 3 days) could not be located in code.
