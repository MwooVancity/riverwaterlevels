# riverwaterlevels.com data inventory (updated 2026-10-23)

22 active public sources shown on gauge pages.

- **usgs** — USGS Water Data API, NLDI, daily statistics
- **nws** — National Weather Service api.weather.gov
- **nwps** — NOAA National Water Prediction Service (flood stages, river forecast, National Water Model)
- **rfc** — NOAA River Forecast Center precipitation estimates and NWS radar imagery
- **padus** — USGS PAD-US public land
- **epa** — EPA ATTAINS
- **osm** — OpenStreetMap via Overpass
- **ridb** — Recreation.gov RIDB (federal recreation facilities)
- **hivis** — USGS HIVIS gaging-station cameras (NIMS API)
- **natmap** — USGS The National Map (USGS Topo map service)
- **nrcs** — USDA NRCS SNOTEL (AWDB web service)
- **cpc** — NOAA Climate Prediction Center 8 to 14 day outlook (NWS map service)
- **usdm** — U.S. Drought Monitor
- **stocking** — State fish and wildlife hatchery stocking records
- **uv** — U.S. EPA Envirofacts hourly UV index
- **openfema** — FEMA OpenFEMA API (Disaster Declarations Summaries)
- **ncei** — NOAA NCEI Storm Events Database
- **acis** — NOAA Regional Climate Centers ACIS
- **nwm** — NOAA National Water Model guidance (via NWPS)
- **coops** — NOAA CO-OPS tide predictions (api.tidesandcurrents.noaa.gov)
- **airnow** — EPA AirNow current air quality (airnowapi.org)
- **ncwsa** — National Center for Cold Water Safety, water temperature safety guide

## New blocks added 2026-10-23 (this session)
- Fish stocking (species, date, count, water, distance) — MT, MD, ND state feeds; extensible registry; live on Potomac (12 MD trout stockings).
- UV index (peak today + EPA category) — EPA Envirofacts, universal.
- Sustained flow (past 7 and 28 day percentile vs USGS daily stats) — low/high for weeks.
- Boat ramps and put-ins (OpenStreetMap, ODbL) — the access-points gap; best-effort via Overpass.
- Ice-affected reading: already covered by the USGS qualifier (not a new block).

## Full block set per gauge page (in order)
Alert banner; hero tiles (flow, gage height, is-it-normal percentile, 6h change, NWS forecast high, water temp, rain 24h, air, sun+moon, calm-daylight-window); cite line.
What the water is like now: cameras, water-quality sensors (temp/turbidity/DO/pH/conductance/nitrate + USGS ice/equip qualifiers), tides, hourly weather, weather forecast, air, air quality, UV index, rain here + nearby, radar.
Level/flow/flood: 7-day chart (30d/12mo/years), gage-height flood ladder, NWS impacts, rate of change.
Forecast: NWS river forecast, National Water Model, rain outlooks (WPC/ACIS/CPC/Atlas14).
How today compares: month, year, prior years, sustained 7/28-day percentile, record, water-temp-by-month + cold-water guidance, fish stocking, snowpack.
Flood record: annual peaks, stage-years, flood frequency, crests, outlook.
Data: daily values, field measurements, rating, rate of rise.
Watershed/land: drought, ATTAINS impairment, StreamCat, dams (NID), FEMA zone, land cover.
Area: boat ramps/put-ins (OSM), recreation sites (RIDB), nearby gauges, NWS point, map, official links, data.json, embed, about.
