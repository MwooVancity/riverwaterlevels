# FRESH-REVIEW-10-N: phone layout of data tables (build at localhost:8123, not live)

Method: Playwright (chromium), 12 pages x widths 390, 360, 340 (dpr 2, isMobile) and 1280, all details opened, DOM audit (document scroll width, table overflow, per-token line-break test on every table cell) plus element screenshots of every table section (881 files in shots/review10n/, audit.json = raw numbers). I opened and read only the screenshots listed below; the rest were checked by the DOM test only.

## Screenshots opened (one line each)
- river_potomac-river-md_little-falls__340__flood_impacts.png: Stage column is 1 character wide; header reads S/T/A/G/E vertically, "3.5 ft" splits to "3." / "5" / "ft", "10.0" to "10" / ".0"; the NWS statement beside it is fine. No rule line crossing the text.
- ...__390__flood_impacts.png: same defect at 390: "STAGE" stacked one letter per line, every value "3." "5" "ft" over three lines.
- ...__340__flood_declarations.png: "DECLARATION" breaks to DECLA/RATIO/N, "DECLARED" to DECL/ARED, "DR-1652-MD" to three lines "DR-/1652-/MD", dates "Jun/23,/1972" over three lines.
- ...__340__rate_of_change.png: header "WINDOW" breaks to WINDO/W; "-1,190 cfs (-15.9%)" wraps to two lines but intact; "24,300 cfs" wraps "cfs" under the number, readable; times wrap at a comma, readable.
- river_ohio-river-ky_louisville__340__stage_chart.png: Measure column crushed: "Flood stage s from", "Gage heigh t at page build (USG S)", "Actio n stage", "Mode rate stage", "Forec ast high"; the Note column wraps "1:00 A M EDT" and "35.5 ft above the latest gage height" over five lines; the first row has a rule line that stops short.
- home__340__table (HOME_table_340.png): "94,80 0", "207,0 00", "60,40 0", "77,50 0", "19,20 0" broken mid-number, "-0 %", "+6 %" percent sign on its own line, header "FLOW , CFS" and "24 H" broken, gauge names "Chattahooche e".
- potomac_heatmap_340.png: heatmap scrolls sideways inside its own box (cells clipped at 6A, shadow edge); direction codes broken "NN / W" in every cell.
- FIRST_potomac_340.png: first screen shows alert, flow 6,300 cfs, gage height 3.54 ft, "Above normal", "Higher than 81%..."; direction text "Falling: -1.3% flow in 6 h" present. Red "live update unavailable" line is long but readable.
- FIRST_yellowstone_390.png: flow 1,610 cfs, gage -0.09 ft, "Steady -0.6% flow in 6 / h" (lone "h" on its own line), "Below normal", gauge; all present on first screen.

## DOM audit (all 12 pages)
- Page-level sideways scroll: none at any width (document width equals viewport everywhere).
- Only internally scrolling table: the hourly heatmap (931 px wide inside its own container) on every gauge page; by design but clipped at the edge on phones.
- Tokens broken mid-word or mid-number inside table cells: 13 to 75 per gauge page at 390/360/340 (Ohio at Louisville worst: 50/67/75); home page 24/24/31; /rivers/pa/ has no table, 0. At 1280: 0, except one on Missouri at Kansas City (not inspected).
- Tables affected on gauge pages: flood_impacts, flood_declarations, rate_of_change, stage_chart (flood stages), hourly_heatmap, nws_forecast_point, daily_readings, water_quality_assessment, flood_stage_years, public_land, river_forecast.

## Defects
P0
1. Stage column of "Flood impacts by stage" is crushed to one character at 340, 360 and 390 on every page with NWS impacts (Potomac, Ohio, Missouri, Hudson, Salmon, Yellowstone, Penns). The flood stage number is the key fact and is unreadable ("3." "5" "ft"). Cause: overflow-wrap:anywhere lets the column shrink to nothing. Fix: `white-space:nowrap` on number, id, date and unit cells (first column), let only prose cells wrap, add `min-width:max-content` to the stage cell. Gate: ui_gates test that no number/date/id token in a table cell has more than one line box at 340 (the audit script's token test is the fixture; Potomac flood_impacts).
2. Stage/flood-stage table (Ohio, Hudson, Gauley "Measure | Gage height | Note"): labels broken ("Actio n", "Mode rate", "heigh t"), notes broken ("1:00 A M EDT"). Same cause, same fix and gate.
3. Disaster declarations: ids "DR-1652-MD", dates and headers broken (DECLA/RATIO/N). Same fix; ids need nowrap.
4. Home page table: flow numbers cut mid-number ("94,80 / 0", "207,0 / 00"), "-0 %" split, header "24 H" broken. A reader sees 94,80 and 0 as two numbers. Same fix; also shorten headers.
5. Rate of change header "WINDOW" and hourly heatmap direction "NN / W" broken. Same rule (headers and short codes nowrap).

P1
6. Heatmap still scrolls sideways inside the card with the right cells cut at the edge and no visible hint beyond a faint shadow (competitor NWS hourly graph is also wide, but shows a scroll cue).
7. Louisville stage table is five-lines tall per row; stacked "label: value" rows would be shorter than a crushed table.

P2
8. "Steady: -0.6% flow in 6 / h" leaves "h" alone on a line; add a no-break space before units.
9. Red "live update unavailable, showing the last build" line is long and starts with a dot at line start on phones.

## Not reproduced / not checked
- Rule line crossing the NWS impact statement on Potomac: not seen at 340 or 390 in flood_impacts and alerts sections (opened flood_impacts only; alerts screenshot taken but not opened). The only odd rule is the first-row line stopping short in the Ohio stage table (item 2).
- I did not open every one of the 881 screenshots; the other pages are covered by the token test only. Kinzua, Salmon, Colorado, Gauley, Penns, Missouri visuals not opened. Folded groups opened by script (all details forced open), their closed state not viewed. Dark mode, steps 2 to 5 of the master prompt, and cross-checks against USGS/NWS were out of scope and not done. 1280 shots not opened (DOM test only).

## Verdict
HOLD. The new wrap rule removes sideways scroll but breaks numbers, ids and dates mid-token on every page.
P0 list: (1) flood-stage column 1 character wide, (2) stage/measure table labels and notes broken, (3) declaration ids, dates, headers broken, (4) home table numbers broken mid-number, (5) "WINDOW" header and heatmap direction codes broken.
