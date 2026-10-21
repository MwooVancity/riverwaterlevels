# FRESH-REVIEW-10-W: indexing batch 2 review, template hash 0cce61d1697e07ba

Reviewed 2026-10-20 evening (about 02:00 UTC Oct 21). Live `/_template.txt` returned `0cce61d1697e07ba` (matches). All 15 pages carry `robots: noindex,follow` today (expected before the wave).

## Method
- Playwright chromium loaded each page at 390 and 1280 px, light and dark (60 renders, full-page screenshots). Full visible text dumped at 1280 light. Scripted overflow test (scrollWidth minus innerWidth) and pageerror capture on every render: zero horizontal scroll, zero page errors. Scripted grep for NaN, undefined, null, Infinity: none on any page.
- USGS API (latest-continuous, 00060 and 00065) for all 15 gauge ids. Flow, gage height and timestamp (UTC converted) match the page header exactly on all 15 (data age 14 to 60 min at fetch).
- Mississippi St. Louis "Oct 1 to 19 mean 265,737 cfs" and "peak last 7 days 241,000 (Oct 14)" checked against the USGS daily-values API: consistent (daily means Oct 1 to 19 averaged about 265k; Oct 14 = 241,000).
- Read the full visible text of 8 pages (Mississippi, Columbia, Sacramento, Susquehanna, Verde, Glenwood Springs, Missouri, and the header/forecast/dam sections of the other 8); looked at the Verde (390 dark) and Sacramento (1280 light) full-page screenshots. Header, forecast, change, percentile and dam-caveat blocks of all 15 were compared by script/grep and by eye.
- Method and defect classes taken from FRESH-REVIEW-10-V.md.

## Per page
PAGE /river/roaring-fork-river/glenwood-springs/: SHIP
PAGE /river/missouri-river-mo/kansas-city/: SHIP
PAGE /river/mississippi-river-mo/saint-louis/: SHIP
PAGE /river/madison-river/below-ennis-lake/: SHIP
PAGE /river/delaware-river-nj/trenton/: SHIP
PAGE /river/gauley-river/above-belva/: SHIP
PAGE /river/susquehanna-river-pa/marietta/: SHIP
PAGE /river/arkansas-river-co/avondale-07109500/: SHIP
PAGE /river/snake-river-wa/anatone/: SHIP
PAGE /river/deschutes-river-or/moody/: SHIP
PAGE /river/yellowstone-river-mt/livingston/: SHIP
PAGE /river/new-river-wv/thurmond/: SHIP
PAGE /river/verde-river/camp-verde/: SHIP
PAGE /river/columbia-river-or/the-dalles/: SHIP
PAGE /river/sacramento-river/freeport/: SHIP

Notes behind the SHIPs:
- Columbia The Dalles: no river forecast is shown ("Not issued", says the weather forecast is not a river forecast), so no forecast-flow conversion to contradict the gauge. Pills "UNSTEADY" (6 h -4.9%, 1 h +2.8%) are honest for a regulated reach. 16th percentile text matches 80,810 cfs mean. Gage height +0.17 ft while flow +2.8% is dam-operation noise, not an error.
- Sacramento Freeport (tidal): handled well. Percentile uses the daily mean, a "24 H RANGE 4,350 to 13,000 cfs" tile replaces a trend, forecast is labelled "NWS stage" with an explicit note that NWS reads 102.00 ft vs USGS 104.21 ft (different zero), and the forecast cfs (8,900) is consistent with the observed 8,730. This is the tidal fix the Hudson review asked for and it works here.
- Missouri Kansas City: forecast 12.6 ft = 56,800 cfs vs 57,300 cfs at 12.75 ft: consistent, falling, pills agree.
- Verde Camp Verde: Flood Watch banner prominent and red; forecast tile (12.1 ft, about 8,660 cfs, 7.3 ft above now, Oct 23), forecast chart and table all agree with each other and with the heavy-rain outlook (1.66 in in 48 h). See P2-2.
- Glenwood Springs: forecast 3.0 ft = 1,340 cfs, consistent with the stated rating pairs (2.5 ft = 957, 2.0 = 625, 1.75 = 490).
- Every page shows data age in the header, "Observed ..." stamps, a build-time vs live note when they differ, the "not a flood warning ... no alert does not mean conditions are safe" box, source credits and the USGS/NWS/NOAA terms list.

## Findings

### P0
None. No stale value shown as current, no flood risk shown as fine, no wrong units, no empty or all-dash widgets, no overflow or errors.

### P1
None new. Carried over: no publisher name or contact on site-level pages (waived by the owner on 2026-10-20 per FRESH-REVIEW-10-V.md; I did not re-check the site-level pages this round).

### P2
1. Mississippi St. Louis: forecast tile says 7.9 ft is "about 174,000 cfs" and "0.1 ft above the latest reading", but the gauge reads 181,000 cfs at 7.75 ft. A higher stage with 4 percent less flow comes from the NWS rating differing from the USGS rating; small, but a reader sees a forecast "rise" with lower flow. Fix: when the rating-derived cfs at the forecast stage is below the observed cfs while the forecast stage is above the observed stage, drop the cfs line or add "NWS rating differs from USGS".
2. Verde Camp Verde and Glenwood Springs (and the same pattern as Salt River in V): the change tile and status read "FALLING -2.4%" (Verde) or "Rising +1.0%" while the NWS forecast is a 14x flow rise (609 to about 8,660 cfs) in 3 days. The forecast tile is directly beside it and the Flood Watch is on top, so this is not unsafe, but a headline pill or chip like "Forecast to rise 7.3 ft by Oct 23" would remove the mixed message. Verde has no headline pills at all.
3. Susquehanna Marietta: "+28.8% RISING" over 6 h is a rebound from the afternoon low (13,800 cfs at 1:15 PM, hydro-peaking pattern) while 24 h is -1.1%, 1 h is -0.6% and the NWS forecast is flat to falling. It is not tagged "UNSTEADY" (Arkansas Avondale gets that tag for a smaller 1 h/6 h disagreement). Fix: widen the UNSTEADY rule when 6 h magnitude is far larger than 24 h and the 1 h sign differs.
4. Gauley above Belva: release-driven river (fall Gauley season), but only the generic dam sentence ("about 10 dams", "Release schedules are not shown") appears; Madison below Ennis Lake gets the stronger "below a dam, flow follows releases" caveat. 24 h -21.7% is probably a release change. Add the below-dam caveat for Gauley and New River at Thurmond (about 120 upstream dams, Summersville/Bluestone releases).
5. "HIGHEST, 7 DAYS" (instantaneous) beside "PEAK, LAST 7 DAYS" (daily mean) differ on Columbia (118,000 vs 84,800 cfs), Mississippi (250,000 on Oct 14 vs 241,000) and others; label the second as daily mean. Odd phrasing "(2 days before this peak)" under LAST THIS HIGH.
6. Percentiles at regulated or pre-dam records (Columbia, Roaring Fork, Madison, Arkansas, Mississippi) compare against records that include pre-regulation years; the generic caveat is present everywhere, Madison has the stronger one.
7. Templated feel: about 25 identical blocks per page with many "0.00 in", "0%" lines; sameness risk, not a defect.
8. Footer "Data status" link (404 at /data-status/ per V); not re-checked.

## What I did NOT check
- Charts' underlying data points (visual and text consistency only), 30 day / 12 month / earlier years tabs, CSV download, range and Save-gauge interactions.
- Percentiles against USGS daily statistics (only arithmetic consistency of the stated figures).
- NWS forecasts, alerts, stages and impact statements against official NWS pages (I did not call NWS; forecast stage-to-flow was only checked for internal consistency and against the USGS pair).
- Whether noindex removal and sitemap inclusion are correct for the wave; robots.txt.
- Core Web Vitals, structured data validity, accessibility, radar and map tiles, EPA/FEMA/NCEI sections.
- Site-level pages (about, privacy, contact/publisher) this round.
- Only a single evening snapshot; behavior at other times or in a real flood not tested.
- I read in full 8 pages' text in the sense listed above; Arkansas, Delaware, Snake, Deschutes, Yellowstone, Madison, Gauley, New River lower sections were scanned by grep (dam caveats, peak/high blocks, impact stages, NaN checks), not read line by line.

VERDICT: SHIP
