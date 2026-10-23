# Completeness Audit — riverwaterlevels.com (2026-10-23)

Skeptical, read-only audit. Question: is this the most helpful river-conditions page for **every** water user, A–Z, or is helpful public data still missing?

## Method / evidence

- Pulled three live pages in full (curl, HTTP 200, 220–233 KB each) and stripped to text:
  - `potomac-river-md/little-falls/` (urban, fish stocking)
  - `colorado-river-az/lees-ferry/` (dam tailwater, trout/rafting, camera)
  - `salmon-river-id/white-bird/` (remote whitewater)
- WebSearch for each candidate source (marked **search-found**). Live page data is **tested**.

**Correction to the "already built" list — these are present and must NOT be chased as gaps** (verified in the live "What the water is like now" block):
sun times + last light, **moon phase/illumination** ("waxing gibbous, 93% lit"), wind + gust, a **daylight weather window** ("7a–5p: no thunder, wind under 15 mph, no rain in the NWS hourly grid"), water temp, humidity. Lightning is effectively covered by the NWS hourly thunder check. "Ice" appearing 20–24×/page is substring noise ("Service", "Ferry") — there is **no** real ice/freeze data.

## 1. A–Z river user types — ONE question, answered?

| User | Their one question | Answered? | If not: public source |
|---|---|---|---|
| Angler | Will fish bite / fishable? | Mostly — flow, temp, clarity(turbidity), stocking, moon | **Fish-consumption advisory missing** |
| Birder | Level for mudflats/habitat? | Yes (gage height, percentile) | — |
| Boater (motor) | Navigable / debris? | Level/flow yes; debris no | No debris feed (bucket) |
| Camper | Flood risk overnight? | Yes (forecast, flood stages, impacts) | — |
| Canoeist | Runnable now? | Yes (flow + forecast) | Planned release (bucket) |
| Diver | Visibility? | Proxy (turbidity sensor where present) | — |
| Dog owner | Toxic algae safe? | **No** | HAB — no river feed (bucket) |
| Drone pilot | Wind? | Yes (wind/gust) | Airspace = FAA, out of scope |
| Emergency mgr | Flood trajectory? | Yes (forecast, rate of rise, impacts) | — |
| Farmer/irrigator | Enough water / drought? | Yes (flow, drought monitor) | **28-day sustained percentile** |
| Fly fisher | Temp/light today? | Yes (temp, sun) | **UV index** |
| Floater/Tuber | Safe + mellow flow? | Flow yes | **UV**, bacteria (bucket) |
| Forager | — | N/A river-specific | — |
| Hunter | Waterfowl/season? | No | State regs, not conditions (out) |
| Hydro operator | Inflow/release? | Partial | **Upstream dam release/reservoir** |
| Kayaker/Rafter | Runnable now + tomorrow? | Flow + NWS forecast yes | **Dam release** (dam rivers) |
| Parent | Safe to get in? | Temp yes | **UV, bacteria, HAB** |
| Photographer | Golden hour / sky? | Yes (sun, last light, cloud) | UV (minor) |
| Property owner | Will it flood my land? | Yes (stage, FEMA zone, forecast) | **Upstream reservoir release** |
| Researcher | Raw data? | Yes (data.json, field meas., rating) | — |
| Rower/Sailor | Wind/chop? | Yes (wind/gust) | — |
| Rescue/swiftwater | Flow + rate of rise? | Yes | — |
| SUP | Wind + flow? | Yes | **UV** |
| Swimmer/Wader | Safe — temp/bacteria/algae? | Temp yes | **bacteria, HAB, UV** |
| Whitewater | Flow vs runnable range? | Current flow yes | Runnable range = Amer. Whitewater (non-gov) |

## 2. Genuinely missing data (real public source, per-gauge/per-place value)

| # | Reader | Data | Source (exact) | Freq | Coverage | Difficulty | Evidence |
|---|---|---|---|---|---|---|---|
| A | Swimmer, parent, paddler, angler, photographer | **UV index, hourly** | `https://data.epa.gov/efservice/getEnvirofactsUVHOURLY/ZIP/{zip}/JSON` (fields ZIP, DATE_TIME, UV_VALUE) | Daily forecast, hourly resolution | **Federal-universal** (ZIP-based) | Low — 1 fetch, 1 "now"-block line | search-found |
| B | Any user on northern gauges, winter | **Ice-affected flag / "flow may read high"** caveat | USGS NWIS IV/DV qualifier already in the response (USGS disables/flags ice-affected discharge) | Real-time | **Federal-universal** | Trivial — parse a flag already fetched | search-found |
| C | Rafter, angler (tailwater), hydro, property owner | **Upstream controlling-dam live release + reservoir elevation** | West: USBR RISE (`data.usbr.gov`, e.g. Glen Canyon release item 4315 cfs / 4354 af, elevation series). East/central: USACE `water.usace.army.mil` (CWMS). SE: TVA | Daily (provisional) | **Fragmented** (USBR/USACE/TVA) | Moderate–high (multi-agency) | search-found |
| D | Angler, swimmer, parent, forager | **Fish-consumption / contact advisory** (mercury, PCB, bacteria) | EPA National Listing of Fish Advisories + state 303(d)/ATTAINS causes (partly already shown as "state water quality assessments") | Annual–irregular | **Fragmented**, state-reported, patchy | Moderate; partial overlap w/ ATTAINS already on page | search-found |
| E | Farmer/irrigator, angler | **Sustained streamflow percentile (7-/28-day)** — "low/high for weeks, not just today" | USGS stats service (same pipeline as the existing "is it normal" block) + WaterWatch class | Daily | **Federal-universal** | Low — reuse existing USGS stats fetch | search-found |

## 3. "Feels like it should exist but doesn't as a usable per-gauge feed" — stop chasing

- **National bacteria / E. coli for river swimming.** EPA BEACON is **coastal + Great Lakes only**; no national river recreational-bacteria feed. State/riverkeeper samples are local and non-standard. *(search-found)*
- **National HAB / cyanobacteria for rivers.** EPA CyAN (satellite) covers **~2,000 lakes/reservoirs ≥1 km²**, not rivers. No river cyanobacteria feed. *(search-found)*
- **Dam *release schedules* (planned future recreational releases).** Observed daily release exists (item C); scheduled/planned whitewater releases live on American Whitewater (non-gov, scraped), not a clean federal feed.
- **National boat-ramp / river-access registry.** RIDB covers federal recreation sites only (already built). No national ramp/put-in/take-out dataset.
- **Debris / strainer / hazard reports.** No public feed.
- **River water clarity (secchi) and dissolved-oxygen as universal.** Only where a USGS water-quality sensor exists (already surfaced); not universal and not fillable elsewhere.

## 4. Verdict

**Info-gain vs any single competitor: ~88 / 100.** No competitor (raw USGS/NWIS, NWS AHPS, American Whitewater, Dreamflows, state DWR pages) combines ~30 datasets per gauge with cross-examination plus sun/moon/wind/temp/AQI/radar/tides/snowpack/water-quality/flood/drought/recreation. Breadth and sourcing are well beyond the field. It is held off ~100 by (a) two broadly-useful, easy gaps (UV, sustained percentile), (b) one high-value fragmented gap (upstream dam release for the many dam-controlled rec rivers), and (c) swim-safety items (bacteria/HAB) that genuinely have no river feed — a ceiling, not a failing.

### Top 5 additions, ranked by reader value per unit build effort

1. **EPA UV index (hourly)** — broad reach (every sunny-day user), federal-universal ZIP feed, one fetch + one "now"-block line. Best ratio.
2. **USGS ice-affected flag + caveat** — near-zero effort (flag already in the USGS response); stops northern-gauge readers misreading inflated winter flow. Narrow season/region but trivial.
3. **Upstream controlling-dam live release + reservoir elevation** — highest reader value for dam-controlled/tailwater gauges (flow ≈ release; it answers "what will it be tomorrow"). Moderate–high effort (USBR + USACE + TVA).
4. **Sustained streamflow percentile (7-/28-day)** — reuses the existing USGS stats pipeline; adds "low/high for weeks" for irrigators and anglers. Low effort, modest incremental value over today's percentile.
5. **Fish-consumption / contact advisory** — anglers, parents, swimmers; state-fragmented and patchy, partial overlap with the ATTAINS block already shown. Moderate effort, moderate value.
