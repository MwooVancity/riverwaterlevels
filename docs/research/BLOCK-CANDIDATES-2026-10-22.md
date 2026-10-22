# River site: candidate data blocks still missing (2026-10-22)

Planning doc. Inspired by abfishreport.ca (same WSC/ECCC government-data shape as us). Each block below is a reader question we do NOT yet answer, the public source, and how hard it is. Evidence tags: VERIFIED = endpoint hit live this session; SEARCH = found via WebSearch, URL recorded, not yet hit; NEEDS-CHECK = exists but no clean feed confirmed. All must obey the site rule: data with unit/time/source, no prose, no verdicts. A block ships only after its source terms are read into data/sources.json.

## Tier 1 — highest reader value, clean data

### 1. Fish stocking (anglers) — "what did they stock here and when"
Per-water records: species, date, strain, count. abfishreport's anchor feature.
- New York DEC — Socrata, CSV/JSON/XML by URL. data.gov/dataset/fish-stocking-lists-actual-beginning-2011 (SEARCH)
- California DFW "Recent Stocked Waters" ds778 — ArcGIS CSV/shapefile. data.cnra.ca.gov/dataset/recent-stocked-waters-california-ds778 (SEARCH)
- New Jersey NJDEP — ArcGIS REST, stream layer 38 fields PERIOD/DATES/NUM_TROUT/STREAM_ID. https://mapsdep.nj.gov/arcgis/rest/services/Features/Environmental_admin/MapServer/38/query (VERIFIED live JSON)
- Ohio DNR — full CSV export. ohiodnr.gov fish-stocking-records (SEARCH)
- North Dakota G&F — CSV + Esri REST JSON. data.gov fish-stocking (SEARCH)
- Pattern: each state has its own ArcGIS/Socrata/data.gov feed. Build a per-state adapter; match stocking location to our gauge by name + coordinates. CO and PA not found yet (need per-state search).
- Shape: a b_stocking block, "Recent stocking at or near this water" table (date, species, count, source agency). Join by river name + nearest point.

### 2. Boat ramps / access points / put-ins (paddlers, anglers, tubers) — "where do I get on"
The top gap from the Lakebrief review. Already an `off` row in data/sources.json ("terms unclear").
- Recreation.gov RIDB (federal facilities) — have the key, partial coverage.
- State boat-ramp ArcGIS layers (same servers as stocking; most states publish a public-access-points layer). (SEARCH, per-state)
- USACE and NPS ramp layers on federal reaches. (NEEDS-CHECK)
- Shape: b_access table (name, type, managed by, distance, map link, source record). No descriptions.

## Tier 2 — strong, data needs a per-state or federal pull

### 3. Fish consumption / mercury advisories (anglers, families) — "is the fish safe to eat"
- EPA National Listing of Fish Advisories (NLFA) — exists since 1993, state-supplied, mercury dominant; NO clean download/API confirmed (NEEDS-CHECK, epa.gov/fish-tech/national-listing-fish-advisories).
- State health-dept advisory tables are the fallback (per-state, mostly PDF/HTML). (NEEDS-CHECK)
- Caveat on the card: an advisory is for a species in a water, issued by the state, with its date.

### 4. Low-head dam hazard (paddlers, swimmers) — "is there a drowning-machine dam near here"
- USACE National Inventory of Dams now includes a Low-Head Dam Inventory, ~10,000 structures; NID downloadable as shapefile via HIFLD/DataLumos. (SEARCH, nid.usace.army.mil)
- BYU nationwide low-head database, ~13,000 dams. (SEARCH, news.byu.edu; contact for data)
- WRDA 2022 definition: river-wide dam, drop 6 in to 25 ft.
- Shape: b_lowhead, "Low-head dams within N miles" (name, river mile/location, source). Hazard facts quoted, no "dangerous" verdict of ours.

### 5. Reservoir level & storage for dam-fed rivers (tailwater anglers, boaters) — "is the dam holding or releasing"
- USACE district reservoir data and USBR (Bureau of Reclamation) RISE API. (NEEDS-CHECK; some via NWPS already)
- TVA reservoir/release pages (owner-permission, like the Gauley problem). (NEEDS-CHECK)
- Ties to the dead-flow Gauley case: where USGS flow stops at a dam, the release schedule is the answer.

### 6. Fish species present / fish surveys (anglers) — "what's in this river"
- USGS BioData aquatic (fish/invertebrate survey data), aquatic.biodata.usgs.gov (NEEDS-CHECK; not curl-friendly).
- State fisheries survey data (per-state). (NEEDS-CHECK)

## Tier 3 — nice, derivable or thin

### 7. Solunar / best-fishing times — derive from the sun+moon we already pull. No new source. (BUILD-FROM-OWN-DATA)
### 8. River miles / float time between access points — derive once ramps (block 2) exist. (DERIVED)
### 9. Hatch timing (fly anglers) — no clean national API; would be regional tables, source-thin. (NEEDS-CHECK, low priority)
### 10. Active wildfire perimeters / smoke (summer floaters) — NIFC/IRWIN feed; we already show AirNow air quality. (SEARCH, low priority)
### 11. Water-temperature forecast — NOAA National Water Model experimental; we show observed temp. (NEEDS-CHECK)
### 12. Ice conditions, northern rivers — limited public data. (NEEDS-CHECK, seasonal)

## Already covered (do NOT re-add)
flow, stage, percentile-normal, NWS forecast + alerts, water temp, weather, rain, radar, tides, air quality, cameras, recreation sites (RIDB), snowpack (SNOTEL), water-quality sensors (DO/pH/turbidity/conductance/nitrate), flood stages, impacts, annual peaks, dams list, FEMA zone, land cover, nearby gauges, cite-this, data.json, embed.

## Build order when the owner reopens the river site
1. Fish stocking (NJ + NY + CA + OH + ND adapters first; they have live feeds) — biggest angler draw, cleanest data.
2. Access points / ramps — the known paddler gap; read the per-state layer terms.
3. Low-head dam hazard — one federal pull (NID), high safety value.
4. Mercury advisories, reservoir levels, species — after their sources are verified.
Each is one sources.json row + one fetch in collect.py + one b_* block with the four states, same as every existing block.
