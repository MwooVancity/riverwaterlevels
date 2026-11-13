# Benchmark 2026-11-13: tide-forecast.com

Why this site: weatherspark.com's robots.txt disallows ClaudeBot and Anthropic's other crawlers, so we stopped there. lakelevels.info has an empty sitemap.xml and no page index. tide-forecast.com allows all crawlers and its sitemap is complete.
It is a tide and sea-condition site, not a climate site, so it is a weaker benchmark than weatherspark would have been.

Read: robots.txt, sitemap_index.xml.gz (7 children, all 7 walked, 54,278 URLs, exact counts), 9 sample pages.

Every location is one slug with 5 sub-URLs: 10,739 locations x 5 = 53,695, plus 583 hubs.

| Type | Count | Example | What it shows | Our version | Status |
|---|---|---|---|---|---|
| Location guide `/locations/<place>` | 10,739 | /locations/Jordan-Point-James-River-Virginia | Title "<Place> Tide Station Location Guide". Nearby airport live weather (distance, wind, temp, visibility, cloud), nearby tide stations and surf breaks. | Our gauge/coast page already links nearby waters with distance. | we have it (waters, not airports) |
| Tide times `/tides/latest` | 10,739 | .../tides/latest | Title "Tide Times and Tide Chart for <Place>". Today's high/low times and heights in a sentence plus table, sunrise/sunset, 30-day chart, live "next high tide in". Computed predictions, not observed. | NOAA CO-OPS predictions on coast pages (7 days, labelled predictions). 30-day window and a next-tide countdown are the gap. | we could build with CO-OPS predictions API (30 days) |
| Live weather `/metars/latest` | 10,739 | .../metars/latest | Title "<Place> Live Weather Report". Table of the nearest 5+ airport METARs: distance, time, wind, gust, temp, visibility, cloud. | Our tiles show air temp and rain 24 h from one source. | we could build with NWS api.weather.gov station observations (US); foreign METAR via NOAA aviationweather |
| Sea conditions `/forecasts/latest` | 10,739 | .../forecasts/latest | Title "<Place> Sea Conditions and Tide Table". 17-day text summary in 5 blocks, then 3-hourly wave height, swell direction, period, wind, tide, moon phase. Model data. | NWS marine-zone warnings only; no waves. | we could build with NWS gridpoint waveHeight/period (US) and NDBC buoy observations; model waves elsewhere = no honest equivalent |
| Sea conditions six_day `/forecasts/latest/six_day` | 10,739 | .../forecasts/latest/six_day | Same title, description and byte size as the page above: a duplicate. | We would not build it (doorway/duplicate under our rule 4). | no honest equivalent (do not copy) |
| Country hubs `/countries/<c>/locations[/A-D]` | 254 | /countries/Canada/locations/A-D | Title "<Country> Tide Times". Lists all ports; big countries split A-D, E-J, K-N, O-S, T-Z. | Our tree home > country > region > hub lists every child. | we have it |
| Region maps `/weather_maps/<region>` | 324 | /weather_maps/Alabama | Title "Map of Tide Stations in <Region>". Interactive station map. | None. Hubs list waters; a map is a UI, not new data. | no honest equivalent (low value) |
| Site pages (home, /countries, /maps, /weather_maps, /pages/contact) | 5 | /countries | Directory of countries and static weather maps (images). | Home and hubs. | we have it |
| **Total** | **54,278** | | | | |

## What the site proves
- Its page set is one data source (tide harmonics, a weather model, METARs) repeated per place. Most of the 54k are near-duplicates (the six_day page is byte-identical to its sibling). Original data is thin: predictions and model output, nothing observed except METARs.
- Our edge: observed gauge data with official labels, 9 research pages, and a doorway rule that blocks name-swap copies.

## Top 3 page types we lack
1. 30-day tide table per NOAA station (/tides/latest): our pages stop at 7 days. CO-OPS predictions are free, official, and answer "tide times next weekend / next month". Label as predictions.
2. Nearby live weather reports (/metars/latest): the 5 nearest official stations with distance and time. Ours uses one source. NWS observations are official and free. Show on a page only as a block, not as a separate URL (a separate URL is a near-duplicate of the gauge page).
3. Wave and sea state for coastal pages (/forecasts/latest): wave height and period from NWS gridpoints or NDBC buoys. Needs a source-terms row in data/sources.json first. Build as a block on coast pages, not 5 URLs per place.
Not worth copying: the duplicate six_day pages and the station maps. Next step on any of the three: one block on a live page, then check Search Console for it.
