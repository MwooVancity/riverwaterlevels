# FRESH-REVIEW-10-U: template hash 0cce61d1697e07ba (confirmed with tools/template_hash.py)

## Method
dist_next served on a local node static server (port 8791, stopped after). Playwright (chromium) at 390x844 touch, 340x700 touch dark, 1280x900 light; all 25 gauge pages scripted (275 page/tab states: 5 tabs on the phone widths, one state at desktop). Per state: horizontal scroll, controls under 36 px, clipped overflow, empty/NaN tiles, page errors. External hosts aborted; api.weather.gov mocked (warn, none), api.waterdata.usgs.gov mocked for one live-update test; Playwright clock moved to test the "live update unavailable" note. Screenshots read: Salt River (light and dark), Hudson Green Island (tidal), Atlanta (390 and 1280), Potomac, Lees Ferry captured; Salt 340 bottom. Full text of Atlanta read. JS-off and keyboard Tab order checked on Atlanta/Salt.

Script result: 275 states, 0 horizontal page scroll, 0 page errors, 0 empty or NaN tiles, 0 clipped text found.

## Previous P1s, verified by me
1. Answer pill after live NWS fetch: FIXED. Mock warn on Gauley: pill, banner and tile all "1 active". Mock none on Lees Ferry and Salt: pill "No active NWS alerts", banner removed. (Pages with a build-time alert still have no alert tile; harmless since pill and banner now update.)
2. Impact cards cut mid-sentence: FIXED. Atlanta cards now end at a sentence and add "rest of the statement in the full list below"; no card ends in "...". Residual P2 below.
3. Forecast crest buried: FIXED. Salt, Verde, Lees Ferry, Potomac, Hudson all start the River forecast rail with "Highest forecast" (Salt 15.8 ft / 10,300 cfs, Oct 23 5 PM, matches the strip card and the table).
4. Alert banner dead on second tap: FIXED. Lees Ferry with mock alert: from History, Data, Weather, Area and Now, tapping the banner switches to Now and the Alerts block is on screen each time (same scroll y 1849).
5. Dark alert pill contrast: FIXED. Salt dark "1 active NWS alert" 8.72:1 (light 5.92). Dark pills a1/a3 on all four alert/no-alert pages above 8:1.

New changes: flow tile "cfs = cubic feet per second" present on all pages (seen). Thin scrollbar present (scrollbar-width thin; 1280 strip still overflows 1534 vs 1204 px, so it is scrollable, fine). Red "live update unavailable" note: absent at +10 min, present at +2 h and +3 d (red rgb(179,38,30)); BUT see P1 below, it keys on build age, not reading age. "No earlier day" is in lib/render.py:685 but is not rendered on any of the 25 pages (all have a value), so I could not see it.

## Re-review after rebuild (hash 0cce61d1697e07ba; first review was on 4ecf32799a4751f9)
- P1 (live USGS reading left "Falling" and "Above normal" pills): FIXED. Mock 5,000 cfs / 9.50 ft on Salt River (light and dark): tile 5,000 cfs, `.a1` and `.a2` hidden, the alert pill stays, note "Flow and gage height at the top updated ..." shown. Second gauge, Atlanta with mock 9,000 cfs: same, pills hidden, "No active NWS alerts" stays. Failed fetch, reading 10 min old (Atlanta): all three pills kept, no red note. Failed fetch, 2 h old (Salt): all three pills kept, red "live update unavailable" shown.
- Record card wording: now "(N days before this peak)" (seen "1 day", "11 days", "14 days" before this peak). Fixed; still counted from the peak, not today, but now says so.
- Regression pass: the full 25-page scripted run again (275 states at 390 light, 340 dark, 1280 light): 0 horizontal scroll, 0 page errors, 0 empty tiles, 0 clipped text. Same small-tap list as before. Screenshot of Salt dark after live update read: layout intact.
- New P2: after a live update the large "Compared with past years: Above normal / Higher than 85%" card stays at its build value directly under a 5,000 cfs tile; only a small caption appended below it says it is as of build time. Fix: grey the card or retitle it "As of build time" when the live reading is newer.
- Remaining P0: none. Remaining P1: none.

## P0
None.

## P1
1. (FIXED in 0cce61d1697e07ba, see re-review) Live USGS update leaves the answer pill wrong and contradicting the tile (same bug class as old P1 #1, for flow). Mock USGS returns 5,000 cfs / 9.50 ft on Salt River (page built at 400 cfs / 6.77 ft). Result: tile "5,000 cfs", but pill still "Falling: -2.9% flow in 6 h" and "Above normal for Oct 20", change card and comparison unchanged. Only a small note below the hero says the top was updated. A reader on a rising flood sees "Falling" in the first pill. Fix: in the live script (hero script, USGS block), when F.t > snap, replace `.answer .a1` with "Live reading newer than trend" (or recompute from the live value versus the 6 h series) and `.a2` with "Comparison as of build time", or hide both, and mark the Change/Compare cards the same way. Gate: extend the live test to mock a flow 10x the build value and assert `.answer .a1` text does not say Falling.

## P2
- Impact cards now clip at the first sentence. At Atlanta 19 ft the card omits "Some homes in these areas will be flooded with around one foot of water"; at 20 ft (Major) the card omits "Several homes, businesses ... will begin to flood". The card is labelled, but the consequence sentence is the one a reader needs. Fix: show the last sentence containing home/building/road/evacuat when over the limit, or let the card grow.
- "Live update unavailable" note keys on build age (data-t older than 1 h), not on the reading's age. Salt/Hudson/Atlanta show it whenever the page is simply more than an hour old and the live fetch fails, which is the intended case, but a visitor on a working network whose USGS fetch returns the same reading as the build (reading itself stale, gauge offline) sees no note and only the age chip. Acceptable; mention in the gate.
- "Last this high" card: "2,720 cfs Oct 11, 2026 (2 days earlier)" on Atlanta is relative to the 7-day peak, not to now (Oct 20); reads as 2 days ago. Say "9 days ago (2 days before the 7-day peak)" or use days from today. Same on "Last day above the 90th percentile ... 3 days earlier".
- Forecast high card on stale forecasts: Atlanta "Forecast high 3.0 ft, Oct 20 8:00 PM", a time already now, with flat 3.0 ft for 19 points; NWS rating says 1,260 cfs vs USGS 1,040 cfs at 2.93 ft (a 21 percent flow gap for 0.1 ft, explained only as "NWS rating"). Hudson: "Forecast high 15.9 ft" is below the latest reading (16.06 ft) and NWS flow 994 cfs vs USGS 3,310 cfs; text is truthful but needs a reader to parse four sentences in a card.
- Pill wording: Lees Ferry "Rising: +41.3% flow in 6 h" has no dam-release caveat in the pill (the card has one: 24 h -0.4%). Hudson and Sacramento "Direction unclear" (tidal) is honest but does not say why in the pill.
- Tap targets: footer data-source "Terms" links 41x21 px on every page; state breadcrumb links 28x42; the inline gauge-name links under Nearby gauges 16 px high (Shenandoah, Salmon, Deschutes pages). Min 36 px otherwise; no horizontal scroll.
- Desktop 1280 strip still shows a cut card at the right edge (Rain) with a thin scrollbar only; Forecast and Change cards are taller than neighbours.
- JS-off: all content visible, tab bar hidden, no horizontal scroll (Salt 13,523 px tall). Long but complete.

## Checked and fine
Pill vs tile vs chart vs table numbers agree on the pages read (Atlanta 1,040 cfs / 2.93 ft / 13th percentile = "lower than 87%"; rate table matches strip -2.8% 6 h; stage table margins 9.1 ft = 12.0 minus 2.93). Flood stage lists and "no impact statement at or below the latest reading" correct on Salt and Hudson. Keyboard: visible 2 px focus outline on all 14 first stops, skip link first. Dark mode legible at 340 and 390 on Salt and Lees Ferry. Tab bar does not cover the footer at 340.

VERDICT: SHIP

## Did NOT check
In the re-review I did not re-read all five original screenshot pages in full or re-test the NWS alert mocks (only the USGS, hidden-pill and failed-fetch paths plus the scripted 25-page pass). Real touch swipe or iOS/Android keyboard with the fixed tab bar; screen reader; live USGS/NWS behaviour beyond mocks; the "No earlier day" card on a rendered page; the 12 months and Earlier years charts by eye on 24 pages (only counted that they render with no errors); Lees Ferry, Potomac and Atlanta screenshots below the first two screens; radar; print.
