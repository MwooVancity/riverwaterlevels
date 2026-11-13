# Federal and state data: used, unused, and the join nobody publishes (2026-11-13)

📄 Planning doc only. It doesn't change the site.

Used means the source has a `data/sources.json` row with status `quoted` or `owner-permission` and a block that reads it. That is 41 of 48 rows. The `off` rows are Atlas 14, WaterWatch, NFHL, and UK NRFA.

## Used (feeds pages today)
USGS Water Data API, NLDI, daily stats, peaks, StreamStats · NWS api.weather.gov · NOAA NWPS (stages, forecasts, NWM) · RFC precipitation · PAD-US · EPA ATTAINS · OSM · RIDB · USGS HIVIS cameras · The National Map · SNOTEL · CPC 8-14 day · Drought Monitor · USACE NID · state hatchery stocking · EPA UV · OpenFEMA declarations · NCEI Storm Events · Reclamation RISE · USACE CWMS · ACIS · CO-OPS tides and temperature · AirNow · NCCWS cold-water table · Water Quality Portal · TWDB · CDIP · NDBC · CDEC · GLERL GLSEA · USNO · agency river-use rules · foreign: PEGELONLINE, ECCC, EA flood and hydrology, DWD, UBA, AAFC, Met Office, Marine Institute, Met Eireann.

## Unused, with the join only we can make

The web check used one search per join. "No published join found" means the search turned up no study or site joining these two sources. It is not proof that none exists.

| Source (owner, terms) | Join with what we have | Reader question it answers | Web check |
|---|---|---|---|
| EPA CyAN cyanobacteria index, about 2,000 large lakes (EPA, REST API live, EPA data license, "provisional, research-level") | Lake page × CyAN weekly index × our water temperature and level | "Is there algae on this lake now, and is it usually worse in hot, low-water weeks?" | No lake-page join with level and temperature found. CyAN's own app shows the index only. |
| USCG BARD boating accidents (USCG, releasable table; CA, OR, PR withheld 2009-22) | Accident date and waterbody × USGS flow that day against the median | "Do accidents on this river cluster at high flow?" | No published BARD × streamflow analysis found. |
| CDC WONDER drowning deaths, ICD-10 W65-W74, by state and month (CDC, cells under 10 suppressed) | State-month drownings × median USGS water temperature for that state-month | "Do drownings peak when the water is still cold?" (cold-shock window) | Not found for the US; UK and AU studies only. |
| EPA BEACON beach advisories (EPA, annual, prior year only, no API) | Beach × nearest gauge or tide × advisory days | "How often is this beach closed, and after what rain?" | Not found, but there is no live data and no API. Hold. |
| NOAA Atlas 14 (off: terms) | — | — | Stays off. |
| FEMA NFIP claims (OpenFEMA) | Claims by county-year × flood-stage days | Being built by the flood-insurance session | Not ours: one writer per topic. |

## Order (searches × originality ÷ harm)
1. **CyAN × lake pages.** It is per page, so it repeats across about 2,000 lakes, and "algae bloom <lake>" is a seasonal search. Harm is a false "clear" from a provisional satellite index. The guard is to show the index with its date and the words "satellite estimate", and never write "safe".
2. **Drowning × water temperature research page.** It is one national page. Harm is a small-number or causal claim. The guards are suppressed cells, n beside each month, and association only.
3. **BARD × flow research page.** Harm is that withheld states and under-reporting bias the counts. The guard is to name the gaps in the abstract and limitations.
4. **BEACON.** Held: prior-year only, no API.

Each item enters PLAN.md with its edge cases before any code.
