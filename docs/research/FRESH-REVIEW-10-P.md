# FRESH-REVIEW-10-P: pre-SHIP pass on dist_next (built Oct 19 17:22)

Method: read the built HTML of 12 pages as text (Salt/Roosevelt, Gauley, Saint Louis, Ohio/Louisville, Chattahoochee, Kinzua, Columbia/The Dalles, Sacramento/Freeport, home, methodology, plus scans of all 25 gauges), served dist_next on :8765 and measured wrapping and search with Playwright, read lib/render.py for branches no built page exercises, and opened 6 screenshots. Server stopped.

IMPORTANT about shots/gate/: the PNGs are from the Oct 18 build (Sacramento shows 9,150 cfs, the build says 4,910; Missouri is Oct 18). They do NOT show today's changes. Also 12 of the 32 files per mode (all named `...C_Program_Files_Git_...`: home, about, gauley, shenandoah, status, rivers/pa and others) are blank white or black images: the screenshot tool passed a Git-Bash-mangled path. I opened two, both blank. So the PA state page and the status page were never actually seen by the gate. Fix the capture script (MSYS_NO_PATHCONV=1) and re-shoot before trusting the shots.

## The 7 changes

1. Alerts tile Unknown / stale: code is right (render.py 411-416: "Unknown" when alerts is None, "as of ... has not answered since" when over 3 h). No built page exercises either branch (all 23 non-banner pages show "0 / No alerts active here"), so I could not see them rendered. NEW DEFECT, see P1-1.
2. Flood outlooks times: FIXED. All 4 pages that have the table (Roosevelt, Camp Verde, Lees Ferry, Glenwood Springs) read "Oct 19, 12:38 PM MST", "Oct 21, 5:00 AM MST to Oct 22, 5:00 AM MST". No ISO timestamp, "undefined" or NaN anywhere in the 60+ built pages.
3. Impact line when below every impact stage: present on 10 pages, reads correctly ("no impact statement at or below the latest reading of 6.89 ft. Its lowest impact stage is 24.0 ft"). Potomac 3.48 vs 3.5 reads fine.
4. Declarations: FIXED. Five columns (Declaration, Declared, Incident period, Title, Programs) in `table.stk`, stacked on phone, Programs row present.
5. Search ranking: FIXED. Typed "colo" gives Colorado River first, "pa" gives Penns Creek first, "new" gives New River first, "st lou" finds Saint Louis, "ohio" finds Ohio River.
6. Home change column: FIXED. No "-0%" in the page; zeros read "0%", unknown reads a dash.
7. "What we do not do" (methodology only; about has no such paragraph): reads "We do not make our own forecasts and we do not rate conditions as good or bad. Forecasts, outlooks and impact statements shown are National Weather Service products quoted as published; every other number is a source value or a calculation described on this page." Honest enough, but see P2-6: the hero says "Above normal / Below normal", which is a rating against history; the sentence should say "we do not rate whether conditions are good, safe or runnable".

## P0
None found. (I did not verify any value against live USGS/NWS; see Could not check.)

## P1
1. Hero alert tile and banner never update from the live alert fetch. Page: any gauge. ALERTS_JS (render.py 1277-1280) rewrites only the lower `#alerts` block. The hero tile ("0 / No alerts active here") and the banner are build-time. Because pages are rebuilt every 30 minutes, an alert issued after the build shows in the lower block but the top of the page still says no alerts; the "stale" mark only appears after 3 h. For the "Unknown" state the same: live fetch succeeds, lower block shows alerts, hero still says Unknown. This is the one place a reader at a river could read the top tile as "fine". Fix: have the live script also replace the `.tile.alrt` tile and insert the banner (or change the tile text to "No alerts when this page was built, HH:MM" until the live fetch answers). Gate: ui_gates fixture with a mocked api.weather.gov response containing one alert; assert the tile no longer says "No alerts".
2. Hero "Compared with past years" uses the trailing 24 h mean, which contradicts the flow shown on fast-changing gauges. Gauley above Belva: latest 1,270 cfs, down 62.5% in 24 h (3,390 earlier), headline "Above normal, higher than 85%"; the 85% belongs to the 2,843 cfs 24 h mean. The explanation is in small print under the dial. Home table repeats "Above normal" next to 1,270. A kayaker sees the word "Above normal" beside a river that just dropped by two thirds. Fix: when |24 h change| is over about 30%, or the latest value and the 24 h mean fall in different bands, show the band of the latest reading too ("Latest reading: Normal range; 24 h mean: Above normal") or label the headline "Above normal (24 h mean)". Gate: build check that fails when the instant-value band differs from the headline band without a visible note.
3. Date wrapping still present and widespread (carried from -O, not fixed). Measured at 1280: Roosevelt 22 dates split across lines, Kinzua 15, Potomac 6, e.g. "Jun 23, / 1972", "Mar 18, / 2010", "Jul 25, 2006 to Aug / 4, 2006". At 390: 18 on Potomac ("May 30, 2026", "Mar 19, 1936"). Not clipped, but dates in the declarations, peaks and impact tables read as two items. Fix: `white-space:nowrap` on date cells (td whose text matches a date) and put " to " ranges on two lines. Gate: the split-token script from -O as a ui_gates check (any `Mon D, YYYY` whose client rects span two tops fails).

## P2
1. One-day incident periods still print "Feb 19, 1980 to Feb 19, 1980" (Roosevelt, 4 rows), "Oct 4, 1975 to Oct 4, 1975" (Potomac). Show one date when start equals end. Gate: regex `(\w{3} \d+, \d{4}) to \1`.
2. Source lines use `overflow-wrap:anywhere` (`.src`), so the FEMA endpoint and the SIR 2014-5211 URL break mid-word ("DisasterDec/larationsSummaries"). Confirmed unchanged. Fix: make URLs real links with `overflow-wrap:break-word` only inside them, or print "OpenFEMA, Disaster Declarations Summaries v2".
3. "Wintergreen Run-112375467" still breaks after the hyphen (Kinzua water quality). Use a non-breaking hyphen or put the id in its own span with nowrap.
4. Dams count has no thousands separator and a precision it does not have: "about 25634" (Saint Louis), "about 16801" (Missouri), "about 2739" (Ohio), "about 1535" (Columbia). Roosevelt says "about 16". Format with commas; round counts over 100.
5. Columbia at The Dalles: tile "Upstream gauge now 4,380 cfs, Deschutes River at Moody". The Deschutes is a 6% tributary of a 74,500 cfs river, not a stand-in for upstream flow; a first-time reader will read 4,380 as "what is coming". Show only gauges on the same river, or label "Tributary gauge".
6. Wording: temperature tiles format inconsistently ("Water temperature 62° F" vs "Air temperature 63 °F"). Time formats inconsistent in the Saint Louis forecast tile ("Nov 2, 06:00 AM CST" vs "6:00 PM CDT" elsewhere). Hourly thunderstorm line on Roosevelt is out of order ("4:00 PM to 6:00 PM; 12:00 PM to 4:00 PM"): sort chronologically and add the day for the second window.
7. Home map in the screenshots has no basemap (tiles load remotely; offline artifact, not judged) but with dots only, 25 unlabeled circles give a phone reader nothing; dots are not tappable by name in the capture.
8. Ohio River at Louisville: the page compares the USGS stage (17.34 ft) with flood stages 53 to 73 ft of NWS point MLPK2 "Ohio River at McAlpine Lower" and prints "37.7 ft above the latest gage height". The place-name mismatch is disclosed, the datum agreement is supported by forecast 17.1 vs reading 17.34, but the page does not say the datum was checked. Worth confirming against water.noaa.gov before SHIP since it is a distance-to-flood number. Same note on Gauley (BVAW2 named "Gauley River near Belva").

## What I checked and found fine
Flood outlook times; impact line; declarations columns and stacking; search ranking; home "-0%"; no horizontal page scroll at 390 or 1280 on the three pages I measured; gauge with no flood stages (Kinzua, Columbia, Sacramento) says why; no forecast says "Not issued" with the point id; tidal Sacramento says tidal and uses the daily mean and gives the 24 h range; datum difference NWS vs USGS on Sacramento is explained; stale-source marks exist in code; the disclaimer text is on every gauge page; dark mode on Salmon hero legible.

## Could not check
- Alerts "Unknown" and "stale" branches rendered: no built page triggers them (read code only).
- Any value against live USGS/NWS/water.noaa.gov (no live cross-check done); Ohio and Gauley datum/flood-stage mapping unverified.
- Screenshots of today's build, the PA state page, the status page, Gauley and Shenandoah (blank or old captures).
- Safari/real devices, screen reader, remote map tiles and radar, behaviour of the live fetches (CSV, alerts) on a slow connection.
- Dark-mode details beyond one hero; not every one of ~700 table sections was viewed.

VERDICT: SHIP AFTER FIXES (P1-1 live alert fetch must update the hero tile/banner; P1-2 headline band vs latest flow; P1-3 date wrapping; capture script producing blank shots)
P0 list: none
