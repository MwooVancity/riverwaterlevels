# FRESH-REVIEW-10-O: phone layout of data tables (flood_declarations now 4 data columns + stacked rows)

Build: http://localhost:8123 (dist_next). Widths 390, 360, 340 (dsf 2, isMobile) and 1280. All details forced open. Screenshots: shots/review10o/ (689 files; every section containing a table or dl, per page and width, plus a top shot; report.json holds the script counts).

## Script results (all 10 pages x 4 widths)
- Page-level horizontal scroll: 0 everywhere.
- Sideways-scrolling containers: only hourly_heatmap (.scroll 933-973 > 270-320 px), as intended. 0 others at any width, including 1280.
- Overlap test (text leaf boxes intersecting inside any section): 0 on Potomac 340/390, Kinzua 360, Hudson 340. The Potomac flood_impacts block shows no rule line across the NWS text.
- Split tokens (a word whose box spans two lines): 0 at 1280; 2-9 per page at 390/360/340. Nearly all are legal breaks after a hyphen or slash: "(gauge-local)", "(peak-flow", "long-range", "monitoring-locations", FEMA endpoint URL (breaks inside "DisasterDec/larationsSummaries"), "Cluett-Peabody", "I-65", "STRAIGHT-LINE". No number or date is cut mid-digit.

## Screenshots opened (one line each)
1. potomac 340 flood_declarations: 4 stacked cards, label left / value right; Declaration, Declared, Incident period, Title readable; PROGRAMS row is absent; source line wraps, URL broken inside "DisasterDec/larationsSummaries".
2. potomac 1280 flood_declarations: table with 5 columns incl. Programs, no scroll; "Jun 23, / 1972" and "Aug 17, / 1971" wrap inside the Declared column, "Jul / 12, 2006" in Incident period.
3. sacramento 360 flood_declarations: 12 cards, long titles right-aligned in 4-5 lines ("STRAIGHT-/LINE WINDS" hyphen break); readable; no Programs.
4. yellowstone 360 flood_declarations: 8 cards, "Apr 10, 2023 to Apr / 26, 2023" date range wraps between date parts; "SEVERE STORMS,ICE" missing space is in FEMA's title; readable.
5. potomac 390 flood_impacts: 2-column table, stage ft + NWS statement, nothing overlapping or cut.
6. potomac 340 flood_impacts: same, text wraps more, no overlap, no scroll.
7. kinzua 340 water_quality_assessment: stacked cards; unit id breaks "Wintergreen / Run- / 112375467" (id number intact on its own line); readable.
8. potomac 340 about_gauge: 2-column table, no break mid-number, source "monitoring-/locations" hyphen break.
9. potomac 340 first screen: flow 6,300 cfs, gage 3.54 ft, "Falling: -1.3% flow in 6 h" visible; the comparison ("Above normal", 81% of 96 years) starts at the fold, text visible, bar/gauge below it.
10. hudson 340 first screen: flow 6,390 cfs, gage 16.18 ft, "Falling: gage height -0.26 ft in 6 h", comparison "Normal range" and dial begin in first 900 px. Red "live update unavailable" line is a localhost artifact (no live fetch), not judged.

Not opened by eye: the other ~680 section shots (checked by script only: scroll, split, overlap), the "/" and "/rivers/pa/" pages (no table sections; script clean, no screenshot opened).

## Defects
P0: none found.

P1
- Programs column (Public / Individual assistance) is hidden on phones: templates/site.css line 43 (`table.hc4 td:nth-child(5){display:none}`) and line 129 drop column 5, so a phone reader loses a FEMA field that desktop shows. The "four columns" are really five on desktop. Fix: drop the hc4 class for this table (or add a Programs row to the card). Gate: ui_gates check that every th at 1280 has a matching visible data-l row at 390 unless listed as intentionally hidden.

P2
- Dates wrap mid-date at 1280 and in stacked rows ("Jun 23, / 1972", "Apr 10, 2023 to Apr / 26, 2023"). Fix: white-space:nowrap per date or put "to" on its own line. Gate: split-token script (here) failing on `Mon D,` followed by a wrapped year.
- Incident period repeats "Oct 4, 1975 to Oct 4, 1975" for one-day events; show a single date.
- FEMA endpoint URL breaks mid-word in the source line; use overflow-wrap:anywhere only on the URL or shorten to "fema.gov OpenFEMA".
- Unit id "Run-112375467" breaks after the hyphen (use a non-breaking hyphen).

## Could not check
Real device fonts/Safari, screen reader, dark mode, remote images, comparison with live USGS/NWS values (not part of this scope), live (non-localhost) first-screen state.

VERDICT: SHIP AFTER FIXES (P1 Programs hidden on phone; P2 date wraps)
P0 list: none
