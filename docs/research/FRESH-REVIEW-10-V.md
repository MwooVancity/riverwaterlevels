# FRESH-REVIEW-10-V: wave-0 indexing review, template hash 0cce61d1697e07ba

Reviewed 2026-10-20 evening (about 01:30 UTC Oct 21). Live site confirmed: `/_template.txt` returned `0cce61d1697e07ba`. All 10 pages carry `robots: noindex,follow` today (as expected before the wave).

## Method
- Playwright (chromium) loaded each live page at 390 and 1280 px, light and dark (40 renders, full-page screenshots). Full visible text dumped at 1280 light. Horizontal overflow test on every render: none found (no HSCROLL output). I looked at montages (390 light, 390 dark, 1280 dark, top of page) for all 10 pages; I read the Hudson and Salt River montages in detail and skimmed the rest from the text dump.
- Cross-check of flow and gage height against the USGS instantaneous-values API for each gauge id (latest 3 h). All 10 latest flow and stage values and timestamps match the page headers exactly (Kinzua 16.6 vs shown 17 is rounding). Also checked NWS observed stage for MLPK2 and TRYN6 via api.water.noaa.gov: same scale as the USGS gauge (15.9 vs 15.86 ft; 16.28 vs 16.48 ft), so the Ohio flood-stage margins are not a datum error.
- Penns Creek daily means recomputed from USGS instantaneous data to test the "peak last 7 days" block.
- Read /about/, /data-sources/ in full; grepped /disclaimer/, /privacy/, /faq/, /methodology/, /glossary/ for email, contact, publisher, owner.

## Page sections

### /river/shenandoah-river/millville/
Gauge 01636500. 952 cfs / 1.96 ft, 63 min old at the time of reading, matches USGS. 73rd percentile (24 h mean 1,285 cfs vs 952 now) is explained on the page. Forecast 2.3 ft = about 1,280 cfs is consistent. Data age, sources, "not a flood warning" present in header, disclaimer box and footer. Minor: "HIGHEST, 7 DAYS 4,400 cfs" (instantaneous) next to "PEAK, LAST 7 DAYS 3,780 cfs" (daily mean, not labelled as such) looks contradictory.
PAGE /river/shenandoah-river/millville/: SHIP

### /river/colorado-river-az/lees-ferry/
Gauge 09380000. 8,070 cfs / 8.13 ft at 6:00 PM MST matches USGS. Flood Watch banner is prominent and red. Dam-controlled river; page says upstream dams changed the record and shows 1,160 dams. 23rd percentile uses a record that starts before Glen Canyon Dam (1921), so "below normal" is not like-for-like (the generic dam caveat is there). The 6 h change (+24.7%) beside 24 h (+2.5%) is explained as time-of-day. Forecast text "first reached Oct 20, 6:00 PM" is awkward.
PAGE /river/colorado-river-az/lees-ferry/: SHIP

### /river/kinzua-creek/guffey/
Gauge 03011800. 16.6 cfs / 2.26 ft matches USGS exactly. "River forecast: Not issued" is stated plainly and says the weather forecast is not a river forecast. Small stream, flat readings are plausible. Many "not available" notes, but honest.
PAGE /river/kinzua-creek/guffey/: SHIP

### /river/hudson-river/green-island/
Gauge 01358000, tidal. 6,060 cfs / 16.48 ft matches USGS (flow jumped 3,290 to 6,060 in 2.5 h, tidal). The page handles tide partly: percentile uses the daily mean, and a "24 H RANGE 993 to 10,500 cfs" tile replaces the trend. Problems: (a) forecast tile says "about 2,170 cfs by the NWS rating" at 15.9 ft while the gauge shows 6,060 cfs at 16.48 ft and a 6,985 cfs daily mean; the NWS stage-to-flow rating does not apply to a tidal reach, so this figure contradicts the page's own numbers and is misleading. (b) The forecast point is Troy (above the dam), compared against the Green Island reading as "0.4 ft below the latest reading"; the page does say the names differ. (c) Impact text says latest reading 16.28 ft while the header says 16.48 ft (build time vs live; explained elsewhere on the page, but looks inconsistent).
PAGE /river/hudson-river/green-island/: HOLD (tidal gauge shows an NWS-rating forecast flow of 2,170 cfs that contradicts the observed 6,060 cfs and daily mean 6,985; suppress forecast cfs on tidal gauges)

### /river/ohio-river-ky/louisville/
Gauge 03294500. 75,100 cfs / 15.86 ft matches USGS. Special Weather Statement shown. 6 h change flagged "UNCLEAR" because flow and stage disagree: honest. Flood stages 53/55/65/73 ft versus 15.98 ft reading are on the same scale per NWS data, and the page explains the forecast point name. Forecast 14.9 ft vs 15.86 ft is 1.1 ft below: fine.
PAGE /river/ohio-river-ky/louisville/: SHIP

### /river/salmon-river-id/white-bird/
Gauge 13317000. 3,740 cfs / 12.37 ft matches USGS (flat for 2+ h; "Steady 0.0%" is plausible at this precision). 19th percentile consistent with a low autumn flow. Forecast 12.4 ft equals about 3,740 cfs: consistent. Rain estimate shown as not available with a reason.
PAGE /river/salmon-river-id/white-bird/: SHIP

### /river/chattahoochee-river/atlanta/
Gauge 02336000. 1,040 cfs / 2.93 ft matches USGS. Forecast 3.0 ft stated as about 1,260 cfs vs 1,040 cfs at 2.93 ft: a 0.07 ft step cannot add 220 cfs on the USGS rating (rounding of the forecast stage to 0.1 ft plus a different NWS rating), looks odd but small. Dam-release river (Buford Dam, about 190 dams noted); release schedule explicitly not shown. 13th percentile consistent.
PAGE /river/chattahoochee-river/atlanta/: SHIP

### /river/potomac-river-md/little-falls/
Gauge 01646500. 5,360 cfs / 3.41 ft matches USGS. Safety-relevant: NWS caution stage 3.5 ft is 0.09 ft above the reading; the page shows the impact statement and says no alert is not safe. Page admits the latest reading is already above the forecast (3.3 ft). "Upstream gauge now: Shenandoah 952 cfs, lag 16 h" carries a caution that it is a much smaller tributary, which is honest but confusing next to 5,360 cfs.
PAGE /river/potomac-river-md/little-falls/: SHIP

### /river/penns-creek/penns-creek/
Gauge 01555000. 268 cfs / 2.23 ft matches USGS. Internal inconsistency: "HIGHEST, 7 DAYS 383 cfs" (Oct 13, 9:15 PM, 168 h earlier, the window edge) while "PEAK, LAST 7 DAYS 426 cfs Oct 13" (daily mean; I recomputed about 433). The instantaneous window starts after the earlier Oct 13 hours, so the daily mean exceeds the "highest". Cosmetic but a rater comparing the two blocks would see a contradiction. Title "Penns Creek, PA" is thin but matches USGS naming.
PAGE /river/penns-creek/penns-creek/: SHIP

### /river/salt-river-az/roosevelt/
Gauge 09498500. 397 cfs / 6.76 ft (5:30 PM MST, 64 min old) matches USGS. Flood Watch banner prominent. NWS forecast climbs to 15.8 ft (about 10,300 cfs) on Oct 23, 9.1 ft above now; shown in the forecast tile, chart and table. But the status pills read "Falling: -3.6%" and "Above normal"; nothing in the header summary says a large rise is forecast. A river-goer scanning only the pills would be under-warned (the alert and tile are right below).
PAGE /river/salt-river-az/roosevelt/: SHIP

## Site-level pages
- /about/ and /data-sources/: clear, specific, honest about sources, refresh cadence (30 min rebuild, browser re-check), "not a government site", "not a flood warning service". Terms-read dates per source. NO publisher name, NO contact email, NO author or operator identity on either page, nor (by grep) on /disclaimer/, /privacy/, /faq/, /methodology/, /glossary/. I did not invent one.
- /data-status/ returns 404 although it is linked in the footer text list on pages I fetched ("Data status"): not verified whether the link points elsewhere.

## Findings

### P0
None found. No stale value presented as current, no flood risk shown as fine, no wrong units found in the 10 pages.

### P1
1. No publisher name and no contact email anywhere on the reviewed site-level pages. For an indexing wave on a safety-adjacent data site this is the single biggest low-quality signal (anonymous, uncontactable, YMYL-ish). The owner must supply real details; I could not and did not make them up.
2. Hudson River at Green Island: forecast flow "about 2,170 cfs" contradicts observed 6,060 cfs (tidal reach); also compares Troy forecast point stage with Green Island stage. Fix: hide NWS-rating cfs and the margin comparison for tidal gauges, or state they are not comparable.

### P2
1. Penns Creek and Millville: "HIGHEST, 7 DAYS" (instantaneous) and "PEAK, LAST 7 DAYS" (daily mean) disagree; label the second as daily mean and align windows.
2. Salt River: top status pills say "Falling" while NWS forecasts a rise of 9.1 ft; add a forecast-rise chip when forecast high is far above current.
3. Hudson: impact text uses 16.28 ft (page build) while header says 16.48 ft (live).
4. Forecast "about N cfs by the NWS rating" is derived from a 0.1 ft rounded stage; Chattahoochee (3.0 ft = 1,260 vs 2.93 ft = 1,040) and Potomac (3.3 ft = 4,610 vs 3.41 ft = 5,360) differ from the USGS pair noticeably.
5. Lees Ferry percentile compares with a pre-dam record; consider a stronger caveat for regulated rivers.
6. Templated feel: every page has the same ~25 blocks (weather, outlooks, radar, hourly) with many "0.00 in", "0%" and "not available" lines; a rater may see sameness between gauges. The hydrology blocks are real and specific, so this is risk rather than a defect.
7. Footer lists "Data status", which returned 404 at /data-status/.

## Not checked
- Whether noindex is removed or the sitemap is correct for the wave; robots.txt was only glimpsed (Allow all, sitemap listed). Root "/" returned 307, not followed.
- Charts' underlying data points (only visual and text consistency), the 30 day / 12 month / earlier years tabs, the CSV download, the "Set your range" and "Save gauge" interactions.
- Percentiles against USGS daily statistics (only the arithmetic consistency of the stated percentile and "lower than" figures).
- NWS forecasts, alerts and impact statements versus the official NWS pages (only MLPK2 and TRYN6 observed stage were compared). Radar, map tiles and EPA/FEMA/NCEI sections not examined.
- Lighthouse/Core Web Vitals, structured data validity beyond reading the JSON-LD (BreadcrumbList and WebPage only), mobile tap targets beyond the screenshots, accessibility.
- Pages' content at other times of day or under changed conditions (a single evening snapshot).
- I skimmed rather than read every line of the lower page sections for Kinzua, Salmon, Chattahoochee, Potomac and Penns Creek.

ROLL-UP: the 9 pages marked SHIP above are cleared for indexing on template 0cce61d1697e07ba; Hudson stays HOLD (P1 forecast tile); the missing publisher/contact P1 is NOT fixed, it is waived by the owner (2026-10-20) and remains your top quality-rater risk
(Reviewer note: the owner waiver and the exclusion of Hudson were relayed by the coordinator; I did not verify them. The 9-page verdict below holds only with both in force; for the full 10-page set the verdict is HOLD.)
VERDICT: SHIP
