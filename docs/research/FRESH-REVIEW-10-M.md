# FRESH-REVIEW-10-M (localhost:8123 build, 12 gauge pages + 6 site pages)

VERDICT: SHIP AFTER FIXES. P0 list: none found.

## Cross-checks (live USGS IV and NWPS, Oct 19 about 1:30 AM EDT)
- Potomac 01646500: 6,300 cfs, 3.54 ft, 00:50 EDT (page equal). BRKM2 flood stages 5/10/12/14 equal; impacts 3.5 and 4.5 ft equal.
- Roaring Fork 09085000: 501 cfs, 1.77 ft, 22:45 MDT equal. GWSC2 9/9.3/14/17 equal; forecast peak 2.29 ft, 0.816 cfs per NWPS = page 2.3 ft / 816 cfs.
- Missouri KC 06893000: 60,400 cfs, 13.28 ft, 23:30 CDT equal. KCDM7 29/32/35/49 equal; forecast 13.3 ft equal.
- Chattahoochee 02336000: 1,110 cfs, 3.01 ft, water 14.6 C (page 58 F) equal. VING1 12/14/18/20 equal; forecast max 3.6 ft = 1,920 cfs equal.
- Delaware 01463500: 5,530 cfs, 8.91 ft, 14.1 C (57 F) equal. TREN4 17/20/23/25 equal; forecast 9.3 ft / 7,250 cfs equal.
- Ohio 03294500, Hudson, Susquehanna, Shenandoah, Penns, Salmon: flow and stage equal to USGS (page is about an hour older, ignored as instructed). Flood stages of MLPK2, TRYN6, MRTP1, MILW2, PNCP1, WHBI1 equal NWPS.
- Percentile bands agree with the stated rule (under 25th below, over 75th above): 9th, 22nd, 22nd below; 35th, 51st, 61st, 67th, 73rd normal; 77th, 80th, 81st, 88th above.

## Stage versus NWS categories
Every page is below Action stage. Only Potomac (3.54 ft) has an NWS impact at or below the reading, and the page quotes it (3.5 ft "caution level for boaters", next 4.5 ft "danger level") above the tabs, with the next stage. The other 9 pages have all impacts above the reading and say so only through the table row "Action stage 8.0 ft, 5.6 ft above the latest gage height". Kinzua says "NWS flood stages (none published for this location)".

## Defects
P1-1 Safety sentence overlapped by a rule. /river/potomac-river-md/little-falls/ on a 390 px phone: a horizontal line from the next block runs through the text "Conditions for boating will be extremely hazardous." (shots/review10m/potomac-m-impact.png; the paragraph `p.gaps.impact` ends at y=2138, the `.src.safety` block starts at 2143 with its border drawn across the last two lines). Fix: margin-bottom on `.gaps.impact`. Gate: ui_gates overlap check on `.impact` vs next sibling on the Potomac fixture.

P1-2 Impact statement is plain small text about 1,900 px down on a phone, below eight tiles and the dam sentence, in the same style as the dam note. A reader at "caution level for boaters" sees "Above normal / Falling" first. Fix: render it as a card under the tiles with the NWS stage name. Gate: any gauge with an impact at or below the stage must have the card in the first 1,500 px.

P1-3 Pages with no impact at the current stage are silent in words. e.g. Shenandoah, 2.40 ft: nothing says "below the lowest NWS impact stage (8.0 ft)". The silence could read as "fine". Fix: one quoted-structure sentence ("NWS lists no impact below 8.0 ft"). Gate: regex on pages with flood stages and no "NWS impact statement at".

P1-4 Methodology states "We do not make forecasts, rate conditions or give advice." The site does label conditions ("Above normal", "Below normal", "Very high" on the home table) and writes instructions: About "For emergencies, follow official warnings."; FAQ "Use official National Weather Service warnings for emergencies."; Potomac forecast point table "Check this forecast point at water.noaa.gov". Either reword the rule ("rate" to "judge safety or runnability") or remove the instructions. Gate: grep site-written text for imperative verbs against the rule text.

P2-1 Ohio at Louisville: "Steady: -0.8% flow in 6 h" beside "1 h: -2.8%" and "24 h: -7.9%", no swing note (the Hudson page has one). Methodology explains the 1% steady rule only for the 6 h window.
P2-2 Kinzua Creek: "Levelling off: -3.9% flow in 6 h" at 20 cfs; one cfs of rounding is about 5%. Change shown on a rounded integer.
P2-3 Chattahoochee: headline "Falling" while the forecast high is 0.6 ft above now (3.6 ft vs 3.01); Hudson flags this ("The gage height is falling now; the NWS forecast expects it to rise."), Chattahoochee does not.
P2-4 Home table: "-0%" (Colorado, Salmon) and "Very high" (Verde) appear where the legend has three bands.
P2-5 Susquehanna/Penns Creek: card labelled "Forecast high" shows a value below the current reading, followed by "The latest reading ... is already above this forecast." Explained, but the label reads wrong.

## Rules checked against pages
Disclaimer "does not say whether a river is runnable, fishable or safe to swim or tube": true on all 12 pages (no such sentence found). "No active alerts ... not a statement that conditions are safe": present. Privacy page hosts (radar.weather.gov, basemap.nationalmap.gov, api.waterdata.usgs.gov, api.weather.gov) match the Potomac page's loaded hosts; no cookie or font host seen in HTML. Home count 25 gauges and regional counts (5+2+6+12) agree. About/FAQ claim of a gaps line under the tiles is true.

## Roles (phone, 390 px; no horizontal overflow on any of 18 pages)
Paddler: rising/falling and forecast are in the first two screens; hazards, dam releases and temperature absence are stated as absent ("Release schedules are not shown"). Tuber/swimmer: no runnable verdict by design; water temperature shown where available, absent stated (KC, Ohio, Susquehanna, Penns, Kinzua). Angler: temperature, percentile, sunset on screen 2. Skeptic: no unresolved contradiction found; the 1 h versus 6 h cases are explained.

## Screenshots opened (one line each)
- river_potomac-river-md_little-falls-m-top.png: 390 px; title, 33 min old, red alert card, flow and stage tiles, top of the percentile card, nothing clipped.
- potomac-m-s2.png: dam sentence, impact paragraph with a rule through its last lines, disclaimer, tab pills cut off at the right (scrollable), alert card, 7-day chart.
- potomac-m-dark.png: dark theme, tiles and gauge readable, amber FALLING readable, no clipping.
- potomac-d-top.png: 1280 px, tile grid, percentile gauge, alert strip, no overlap.
- potomac-m-impact.png: the overlap defect P1-1.
- hudson-m-s1.png: stage bar with markers, chart with forecast dashes, table "Flood stages from" row wraps into a narrow column, legible.
- home-m.png: headline, dot map, filters, gauge table with Very high and -0%.
- Other 11 pages: top-of-page screenshots saved in shots/review10m/ but not opened; their text was read from page dumps.

## Not checked
No screen reader, no throttled network, no lazy radar or topo images (not loaded), no desktop or dark shots of the other 11 gauges, no states or hub pages, old /forecast/ and /water/ redirects not tested, NWS rating flow for Ohio (NWPS returns -999). The skeptic text pass is a grep and a read, not every sentence of the 5,000-line text dumps.
