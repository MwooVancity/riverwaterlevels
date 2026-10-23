# riverwaterlevels.com data inventory (2026-10-23)

Every public source shown on a gauge page (status quoted/permission). 21 active sources.

- **usgs** — USGS Water Data API, NLDI, daily statistics (credit: Data: U.S. Geological Survey)
- **nws** — National Weather Service api.weather.gov (credit: Forecasts, alerts and observations: National Weather Service. NWS material is not subject to copyright)
- **nwps** — NOAA National Water Prediction Service (flood stages, river forecast, National Water Model) (credit: River forecasts, flood stages, crests and impact statements: National Weather Service)
- **rfc** — NOAA River Forecast Center precipitation estimates and NWS radar imagery (credit: Rain estimates and radar: NOAA and National Weather Service)
- **padus** — USGS PAD-US public land (credit: Public land: USGS Gap Analysis Project, Protected Areas Database of the United States (PAD-US))
- **epa** — EPA ATTAINS (credit: Water quality assessments and watershed data: U.S. Environmental Protection Agency)
- **ridb** — Recreation.gov RIDB (federal recreation facilities) (credit: Recreation sites: Recreation.gov (RIDB))
- **hivis** — USGS HIVIS gaging-station cameras (NIMS API) (credit: Camera images: U.S. Geological Survey, HIVIS)
- **natmap** — USGS The National Map (USGS Topo map service) (credit: Map services and data available from U.S. Geological Survey, National Geospatial Program)
- **nrcs** — USDA NRCS SNOTEL (AWDB web service) (credit: Snow data: U.S. Department of Agriculture, Natural Resources Conservation Service)
- **cpc** — NOAA Climate Prediction Center 8 to 14 day outlook (NWS map service) (credit: Outlook: NOAA Climate Prediction Center)
- **usdm** — U.S. Drought Monitor (credit: The U.S. Drought Monitor is jointly produced by the National Drought Mitigation Center at the University of Nebraska-Lincoln, the United States Department of Agriculture, the National Oceanic and Atmospheric Administration and the National Aeronautics and Space Administration. Map courtesy of NDMC.)
- **stocking** — State fish and wildlife hatchery stocking records (credit: Stocking: state fish and wildlife agency)
- **uv** — U.S. EPA Envirofacts hourly UV index (credit: UV index: U.S. Environmental Protection Agency)
- **openfema** — FEMA OpenFEMA API (Disaster Declarations Summaries) (credit: Declarations: FEMA OpenFEMA (not endorsed by FEMA))
- **ncei** — NOAA NCEI Storm Events Database (credit: Storm events: NOAA National Centers for Environmental Information, Storm Events Database)
- **acis** — NOAA Regional Climate Centers ACIS (credit: Station climate data: NOAA Regional Climate Centers, ACIS (preliminary))
- **nwm** — NOAA National Water Model guidance (via NWPS) (credit: National Water Model guidance: NOAA)
- **coops** — NOAA CO-OPS tide predictions (api.tidesandcurrents.noaa.gov) (credit: Tide predictions: NOAA National Ocean Service, CO-OPS)
- **airnow** — EPA AirNow current air quality (airnowapi.org) (credit: Air quality: EPA AirNow and the reporting agency named on the row (preliminary data))
- **ncwsa** — National Center for Cold Water Safety, water temperature safety guide (credit: Guidance: National Center for Cold Water Safety)

## Blocks per gauge page (in order)
Alert banner, hero tiles (flow, gage height, is-it-normal percentile, 6h change, NWS forecast high, water temp, rain 24h, air, sun+moon, calm-daylight-window), cite line.
What the water is like now: cameras, water-quality sensors (temp/turbidity/DO/pH/conductance/nitrate + USGS ice/equip qualifiers), tides, hourly weather (thunder/humidity), weather forecast, air, air quality, UV index, rain here + nearby, radar.
Level/flow/flood: 7-day chart (30d/12mo/years), gage-height ladder with flood stages, NWS impacts, rate of change.
Forecast: NWS river forecast, National Water Model, rain outlooks (WPC/ACIS/CPC/Atlas14).
How today compares: month, year, prior years, record, water-temp-by-month + cold-water guidance, fish stocking (MT/MD/ND), snowpack.
Flood record: annual peaks, stage-years, flood frequency, crests, outlook.
Data: daily values, field measurements, rating, rate of rise.
Watershed/land: drought, ATTAINS impairment, StreamCat, dams (NID, 15mi), FEMA zone, land cover.
Area: recreation sites (RIDB), nearby gauges, NWS point, map, official links, data.json, embed, about.
