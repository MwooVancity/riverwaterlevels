# FRESH-REVIEW-10-Q: verification of the -P fixes (dist_next, built Oct 19 17:28 local)

Method: served dist_next on :8766 (stopped), Playwright with mocked api.weather.gov, wrapping measured with client rects at 1280 and 390, 9 mobile top-of-page captures I took myself (390 px), all 25 gauge pages text-scanned, NWS values cross-checked against api.water.noaa.gov. Page code not edited.

## Verification of the six fixes

1. Live alert tile: WORKS on pages with a tile. Mock Flood Warning on Roosevelt and Kinzua: tile reads "1 / Flood Warning", class `on`. Empty list: "0 / No alerts active here. Checked live Oct 19, 4:30 PM MST." Request aborted: tile keeps "0 / No alerts active here" (build text), lower block keeps build text. Gap, see P1-1.
2. Hero sentence: correct and measured. Gauley: "This compares the 24 h mean (2,843 cfs); the latest reading, 1,270 cfs, is 55% below it." 1,270/2,843 = 0.447, so 55% below is right. Sacramento: 4,910 vs 8,058 = 39% below, right. Clear in the bold line on a phone. Not fully fixed, see P1-2.
3. Dates: table dates never split (0 of 101 on Roosevelt, 71 Kinzua, 80 Potomac, 106 Ohio and Saint Louis, both widths; they use no-break spaces). One-day periods show one date (0 "X to X"). "Wintergreen Run-112375467" uses a non-breaking hyphen and no longer splits at the hyphen (it can wrap at the space before the id, fine). Still splitting: dates inside Source lines at 390 (e.g. "Sep 19, 2026 to Oct 18, 2026", "produced Oct 19, 2026") - plain prose wrap, P2.
4. Dams: commas and rounding present everywhere ("about 25,630", "16,800", "2,740", "1,540"). Fixed.
5. Columbia at The Dalles: tile now says "A much smaller stream than this river: a tributary, not a stand-in for the water on its way." Fixed. (Snake at Anatone shows Salmon River at White Bird, 29% of flow, no note; defensible, P2.)
6. Earlier fixes hold: flood outlook times read "Oct 19, 12:38 PM MST" with a valid window; no "undefined", NaN, "-0%" or ISO text in any of 49 pages (ISO strings exist only in data-t attributes); declarations have five columns; impact line reads correctly; home has no "-0%" (zero reads "0%", unknown a dash).

Ohio datum: checked against the NWS API: MLPK2 "Ohio River at McAlpine Lower" lists usgsId 03294500 (this gauge) and its observed stage was 17.38 ft at 23:00Z against the page's 17.34 ft at 22:00Z. The assumption is TRUE and the numbers are right. Gauley BVAW2 lists USGS 03192000 and 2.84 ft, matching. Yellowstone LIVM8 (-0.09 ft), Salt SLRA3 (6.89 ft) also match.

## P0
None.

## P1
1. Banner not live (Ohio, Chattahoochee: the 2 pages with a build-time alert have a `.abanner` and no tile). Measured: with the mocked response "Flood Warning, Severe", the top banner still reads "1 active National Weather Service alert / Special Weather Statement" while the lower block lists the Flood Warning. With an empty response the banner still claims an alert and the lower block says none. On a page with no build-time alert, a live warning updates the tile only, there is no banner and no link to #alerts. Fix: let the live script also rewrite or remove `.abanner` (insert it when al.length>0, remove when 0) with the same event names. Gate: add to the ui_gates mock test an Ohio case asserting banner text equals the mocked event.
2. Headline band still contradicts the reading on fast-moving rivers. Gauley (down 62.5% in 24 h): big heading "Above normal", dial in the purple arc, home and the West Virginia state page say "1,270 cfs, above normal". The explanation sits in the bold line but the word, dial and every list repeat the 24 h-mean band. Sacramento is the inverse case. Fix: when the latest reading falls in a different band than the mean, name both ("Above normal by 24 h mean; latest reading is Normal range") and use the latest reading's band on list rows. Gate: build check that fails if the latest-flow band differs from the headline band and no note is visible.

## P2
1. Verde: "Very high ... Higher than 95% or more of the 49 years" is ungrammatical. Fix: "At or above the 95th percentile of the 49 years".
2. Hero wording "This compares the 24 h mean" is clumsy. Better: "The 24 h mean (2,843 cfs) is used; the latest reading, 1,270 cfs, is 55% below it."
3. Tile fallback text on a failed live alert fetch carries no build time ("No alerts active here"); the time is only in the lower Source line. Add "as of build HH:MM".
4. Saint Louis forecast tile: "Nov 2, 06:00 AM CST" (zero-padded, while others read "6:00 PM"). Still unfixed from -P. Also temperature tile formats differ ("66° F" vs "66 °F").
5. Jargon: "NWS RFC estimate" (rain tile), "no median" on SNOTEL rows (16 pages, "0.0 in, no median") with no reason.
6. Ohio note says the NWS name is "a different place name from this USGS gauge" and stops. The NWS record lists the same USGS ID; saying "NWS lists USGS 03294500 for this point" would remove the doubt the page raises. Readers cannot verify the datum themselves, so the claim is correct but the page hides why.
7. Home/state lists say "Live flow" though values are up to ~90 min old (times are shown). Wording, minor.
8. Capture and hygiene: shots/gate has Oct 18 files for Missouri, Sacramento and Hudson forecast (stale; I used my own captures).

## Critical pass notes
Checked 25 pages by text: change word vs 6 h % consistent with the glossary rule (Penns +1.4% Rising, Ohio +0.9% Steady follows the 1% rule, though it reads odd beside Roaring Fork +3.3% "Levelling off"). Percentile vs band words agree on all 25. No "source failed shown as none": absent items say "Not available for this gauge: ... (reason)", "Not issued", "Unknown" paths exist in code. Lees Ferry +57.2% / 24 h +0.5% is explained by the printed 24 h range and the cycle note. Mobile: no horizontal scroll, no clipped text found by detector on 9 pages.

## Could not check
- Alerts "Unknown" and "stale" tile branches (no page triggers them; mock only covers success, empty, abort).
- Live USGS CSV fetch: in my run it showed "live update unavailable, showing the last build" in red on every page (my offline/blocked context); I could not see the connected state.
- Remote map tiles and radar (blocked, home map showed broken-image alt text overlapping, an artifact of my blocking), dark mode, Safari or real device, screen reader, slow connection.
- Values beyond the 5 NWS points above against USGS pages; most table sections not read by eye.

VERDICT: SHIP AFTER FIXES (P1-1 banner must follow the live alert fetch; P1-2 name the latest-reading band when it differs from the 24 h-mean headline)
P0 list: none
