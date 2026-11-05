# Schema / Structured Data findings (2026-11-04, live fetch, read-only)

**Schema score: 52/100.** Valid and honest where present, but 4 of 5 gauge types and the home page have almost nothing.

## Detected
| Page | JSON-LD |
|---|---|
| / | none (no WebSite, no Organization) |
| /river/ohio-river-ky/louisville/ | BreadcrumbList + WebPage (isPartOf WebSite, publisher Organization, about Place+geo, mainEntity Dataset with license, creator, temporalCoverage, DataDownload to data.json). Valid, https context, absolute URLs, ISO dates. |
| /canada/ottawa-river-at-britannia/, /rhine/kaub/, /england/river-trent-at-colwick/ | BreadcrumbList only |
| /about/, /methodology/, /rivers/ky/ | BreadcrumbList only (last crumb has no `item`, which Google allows) |

The brief said "only BreadcrumbList"; the US page already carries the Dataset graph. No Microdata/RDFa.

## Findings

**1. HIGH - Non-US pages lack the Dataset/Place graph the US page has.** Evidence: Kaub, Ottawa, Trent have 1 ld+json block; Louisville has 2. This breaks the "one standard page" rule. Fix: use the same builder for all countries, with each agency's own creator and license (see example A). How we know: all four gauge types show WebPage + Dataset in the Rich Results Test and Search Console "Datasets" report.

**2. HIGH - No data.json on non-US pages.** Evidence: /rhine/kaub/data.json, the Canada one and the England one return 404; Louisville returns 200. Dataset `distribution` must point to a real file. Fix: only emit `distribution` when the file returns 200 (the Worker already serves `/live/<site>.json`; reuse that if it is public). Never emit a dead contentUrl. Check: a build gate that fetches each contentUrl.

**3. MEDIUM - Home page has no WebSite/Organization.** Fix: example B. Benefit: Google site name and entity clarity. Also feeds AI citation. Add `SearchAction` only if the search is a real URL (`/?q=`); it is a JS box today, so leave it out. Check: Rich Results Test shows WebSite; the site name shows in the SERP.

**4. MEDIUM - Louisville `license` and `creator` are right, but non-US licences need the agency's actual terms** (Open Government Licence for the EA, Datenlizenz Deutschland for PEGELONLINE, ECCC Open Government Licence - Canada). Take them from `data/sources.json`, never from memory.

**5. LOW - Organization has no logo, contact or sameAs.** Owner-only items (publisher name and email). Add only when the owner supplies them. Placeholders are forbidden.

**6. INFO - Hubs and about/methodology.** BreadcrumbList is enough. A CollectionPage/ItemList gives no Google feature. Skip.

## Types with no benefit
- **Observation / QuantitativeValue as a standalone type:** no Google feature, no consumer. Do not add.
- **Place alone:** no rich result. It only carries geo for entity matching, so keep it nested in `about` (as Louisville does).
- **Dataset:** the only type with a real feature (Dataset Search). It is thin value, but truthful. The AI-citation benefit is unproven.

## Live readings and stale cache (the key constraint)
Do NOT put the current level in markup. The Dataset describes a series, not a value. Safe fields: `temporalCoverage` (the build time window), `dateModified`, `variableMeasured` as a name and unit only, with no `value`. Louisville already follows this. Readings live in data.json, which is not used as a rich-result input. A stale-cache gate: JSON-LD must contain no digit that is also the page's current reading (add a `check.py` selftest). If you ever add a value, add `dateModified` plus `observationDate`. That is still risky, so don't.

## Ready JSON-LD

**A. Kaub (add to the existing graph; creator and licence verify first)**
```json
{"@context":"https://schema.org","@type":"WebPage","name":"Rhine at Kaub water level today","url":"https://riverwaterlevels.com/rhine/kaub/","isPartOf":{"@type":"WebSite","name":"River Water Levels","url":"https://riverwaterlevels.com/"},"about":{"@type":"Place","name":"Rhine at Kaub","geo":{"@type":"GeoCoordinates","latitude":50.0854,"longitude":7.765}},"mainEntity":{"@type":"Dataset","name":"PEGELONLINE gauge KAUB, Rhine: water level","description":"Recent water level readings at gauge KAUB on the Rhine, with 24 h change and forecast, from PEGELONLINE.","url":"https://riverwaterlevels.com/rhine/kaub/","creator":{"@type":"Organization","name":"Wasserstraßen- und Schifffahrtsverwaltung des Bundes (WSV) / PEGELONLINE","url":"https://www.pegelonline.wsv.de/"},"license":"<URL from data/sources.json>","variableMeasured":[{"@type":"PropertyValue","name":"Water level","unitText":"cm"}],"dateModified":"<build time, ISO 8601>"}}
```
Ottawa (02KF005, 45.3513, -75.8267, creator Water Survey of Canada, unit m) and Trent at Colwick (Gauge 4009, 52.9527, -1.0777, Environment Agency) follow the same shape. Where a `<...>` placeholder remains, it is filled at build from sources.json; if it is missing, omit the whole Dataset.

**B. Home**
```json
{"@context":"https://schema.org","@type":"WebSite","name":"River Water Levels","url":"https://riverwaterlevels.com/","publisher":{"@type":"Organization","name":"River Water Levels","url":"https://riverwaterlevels.com/"}}
```

## Do not add
FAQ, HowTo, Review/AggregateRating, and any LocalBusiness or Product schema. None applies truthfully.
