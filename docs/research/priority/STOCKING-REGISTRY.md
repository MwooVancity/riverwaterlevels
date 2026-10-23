# Fish-Stocking Endpoint Registry

Verified via WebSearch (discovery) + curl/urllib (testing) on 2026-10-22. READ-ONLY research.
Full machine-readable detail in `stocking-registry.json`.

**Goal per state:** a public endpoint returning individual hatchery stocking EVENTS with species, stocking date, number of fish, waterbody name, ideally point geometry.

## Tally (29 states researched)

- **Verified feed (species + date + count + waterbody, queryable): 5** - MT, MD, ND, WI, NY
  - **With POINT geometry: 3** - MT, MD, ND
  - Polygon geometry: 1 - WI (one feature per waterbody; events in embedded JSON string)
  - No geometry: 1 - NY (Socrata; text location only, would need geocoding)
- **Needs a table join: 2** - PA, NJ
- **None (no machine-readable events feed found): 22**

## Verified (use these)

| State | Type | Geometry | Date format | Records | Endpoint |
|-------|------|----------|-------------|---------|----------|
| MT | ArcGIS | point | epoch ms | 116,949 | fishViewer MapServer/38 (template; `outSR=4326` required) |
| MD | ArcGIS | point | epoch ms | 68 | TroutStockingActivities MapServer/0 (LOCATION/ActivityDate/NumOfFish/Species; trout only; 2026 season) |
| ND | ArcGIS | point | string `YYYY-MM-DD HH:MM:SS` | 6,022 | GNF_FishingWaters MapServer/3 (Lake_Name/Species/StockDate/Total_Stocked; all species; host slow) |
| WI | ArcGIS | polygon | year (in JSON) | 1,421 | FH_ANNUAL_STOCKING_SUMMARY MapServer/0 (events embedded in `STOCKING_RECORDS_JSON` per waterbody; 2025 present; 15-yr history) |
| NY | Socrata | none | year+month | 39,583 | data.ny.gov `e52k-ymww.json` (no lat/lon; covers 2011-2025) |

MD and ND are drop-in point feeds like the Montana template. WI needs a client-side JSON parse of one field and a polygon-centroid if a point is wanted. NY is the richest history but has no coordinates.

## Needs a join (data split across layers/tables)

- **PA** - PFBC `TroutStockedSections_<year>` polyline sections are "directly linked to tables of stocking events." **Could not verify via curl: `fbweb.pa.gov` returns an HTML wall (WAF) for every request** incl. `f=json`/`f=pjson`/`/query`, even with a browser UA. Needs a real browser/session to extract. One service per year; 2026 extent is in NAD83 State Plane PA North (ft). Point variant: `PFBC_Stocked_Trout_Waters/MapServer/1`.
- **NJ** - geometry in layers 33 (lakes centroids), 34/35 (streams) of `Environmental_admin/MapServer`; schedule/events in layer 38 (table: PERIOD/DATES/NUM_TROUT/STREAM_ID). Join STREAM_ID/LAKE_ID. Trout only, schedule is 22 rows (season plan, not history). Low value.

## None - and why (the useful near-misses)

Four states have a feed that is close but fails the events bar (no date AND/OR no count) - URLs kept in the JSON in case the site can still use them:

- **VT** - `MAP_ANR...MapServer/52`: 250 POINTS with species + waterbody + lat/lon, but **no date, no count** ("Fish Stocking Locations 2021" static snapshot). Usable as which-species-stocked-where.
- **VA** - `Projects/TroutApp/FeatureServer/0`: 47 points, designation + schedule-category + species yes/no flags, **no per-event date/count**.
- **CA** - `biosds778_fpu/FeatureServer/0`: 536 POLYGONS with only `last_yr_stkd` + county; **no species/date/count/waterbody name**. (The ds778 lead is waters, not events.)
- **MO** - `MO_Fishing_Interactive_Map` layers 6/7: trout lake/stream locations + regulation URLs, no events.
- **MI** - UMich-hosted `mi_dnr_stocking`: stocking SITES directory (vintage ~2000), species but no dates/counts.

Pure none (web/PDF/viewer reports or basemap layers only, no events service found): **CO, WV, AZ, ID, OR, WA, KY, GA, TN, NC, TX, UT, NM, CT, OH, MN, FL**.

- **FL** note: FWC `Freshwater_Fish_Stocking_Table` only exists on the TEST host `gistest.myfwc.com` (unreachable/firewalled from server); production `gis.myfwc.com` needs a token (HTTP 499). No open endpoint.
- **TN** note: a feature service may sit behind the TWRA ArcGIS Web AppBuilder viewer (app id in their stocking PDF) - worth manual inspection.

## Not individually researched

The remaining ~21 states (AL, AK, AR, DE, HI, IA, IL, IN, KS, LA, MA, ME, MS, NE, NH, NV, OK, RI, SC, SD, WY + DC) were not searched - this pass covered all 21 river-gauge priority states plus incidental discoveries (WI, VT, ND, VA, MO, MI, OH, MN). None are marked "none" without evidence; they are simply not yet checked.

## Manual-follow-up leads (behind viewers/WAFs/test hosts)

PA (WAF), FL (token/test host), TN (web app), CO/WA (atlas network requests), ID/UT/MN (browse Fisheries folder in their ArcGIS directory).
