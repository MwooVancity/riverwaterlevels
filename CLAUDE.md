# River Water Levels (riverwaterlevels.com)

Lakebrief-style, ad-supported US river gauge site. One page set per USGS gauge (Dashboard, Water, Forecast), river hubs, state pages, trust pages. Data from government APIs only. Domain bought 2026-10-16, served by a Cloudflare Worker with static assets. Pre-launch `noindex` hold in `templates/_headers`: remove it ONLY when the owner says so.
This folder is its own project: the car-repair site (calcscrape) rules do not apply here.

## Read first, every session and after every compaction
1. `C:\Users\mwoo7\Desktop\riverwaterlevels\docs\PLAN.md`: living plan, status, next steps, owner to-dos, decisions. Update it at every milestone.
2. `C:\Users\mwoo7\Desktop\calcscrape\docs\research\MASTER-SPEC.md` (the law), `DESIGN-UI.md`, `END-TO-END-PLAN.md`, `SITE-TEMPLATE-AND-ROLLOUT.md`, `FRESH-REVIEW.md` (originals live there; do not copy them here).
3. `data/sources.json`: the API and terms register (each source: endpoint terms page, status quoted / owner-permission / off).
4. Memory file `project_river-site.md`. If any of these disagree with the live site, the live site and the checks win, then fix the doc.

## Hard rules
- **No composed prose or verdicts on data pages.** Visible text is a source value with unit and time, a label from `lib/render.py`, or a verbatim source string (escaped). No "good time to fish", no safety judgement, no ranking sentences.
- **Every block has a `Source:` line** (what, who, when fetched or observed). A block that has no data returns `None` (no heading, no source line).
- **Terms gating:** a block renders only if its source in `data/sources.json` has status `quoted` or `owner-permission`; `off` sources are built but never shown. New source = search for its terms (WebSearch, not WebFetch), quote them in `sources.json`, then build.
- **Freshness:** flow older than 24 h = page rebuilt with a "Gauge not reporting" notice at the top; older than 30 days = CriticalFail (page not rebuilt, last release stays live); forecast 12 h amber / 72 h hidden; weather obs 3 h / 12 h; rain 6 h / 24 h; alerts amber at 3 h; SNOTEL 5 days; CPC 3 days.
- **`collect.py` is the only code that touches the network.** `build.py` reads `cache/` only. A failed source keeps its previous cache value.
- **Percentile** = interpolation of USGS daily percentiles for the date, shown with "estimated"; never presented as a USGS value. Time zones: gauge-local with abbreviation.
- Every published gauge page is indexable once the hold is lifted; no noindex gate, no 410. Trust, hub, state pages in the sitemap; sitemap = page set (check.py enforces).
- No API keys in pages, zips or docs. Key lives in the calcscrape `.env`, read only by `lib/common.py`.
- Owner is a non-coder: do the work, plain short replies, never ask them to run commands. Verify live pages before saying "live". One zip for ChatGPT reviews, key-scanned.

## Pipeline
`python -I collect.py [site..]` (all 25 = wave 0) -> `python -I build.py` (to `dist_next/`) -> `python -I check.py` -> `python -I publish.py` (atomic swap to `dist/`, previous in `dist_prev/`, `--rollback`) -> `npx wrangler deploy` -> `python -I livecheck.py <urls>`.
`python -I refresh.py` runs all of it with a lock and a log (`runs/refresh.log`). `python -I tests.py` = safety tests (determinism, stale source, rollback, block safety). `node js_test.mjs` = page JavaScript against stubbed USGS responses (CSV complete and sorted, no partial file on a 429, live-refresh note); `node render_test.mjs [--shots]` = real-browser overflow, console, scripts-off at 390 and 1280 px.
Collector modes: `--fast` (bulk USGS latest incl. related gauges, NWS, NWPS, rain: every 30 min), `--nws-only`, `--extras-only [--keys=a,b]` (slow sources). Full `collect.py` only every 6 h. Two scheduled tasks (hidden, only while the owner is logged in): "RiverWaterLevels Fast Refresh" (`refresh.py --fast`, 30 min) and "RiverWaterLevels Refresh" (`refresh.py`, 6 h). For manual deploys run `python -I refresh.py --fast` so the lock stops collisions. `python -I build.py --preview` builds dist_preview/ with uncleared blocks visible (review only). USGS rate-limits bursts (429).

## Files
`lib/render.py` block registry, tab layouts (`tab_blocks`), hero, live JS, tools JS; `lib/directory.py` home, state, hub, trust pages, sitemap, 404; `lib/pages.py` page set and name overrides (`data/name-overrides.csv`); `lib/common.py` paths and helpers; `templates/site.css`, `templates/_headers`; `data/sources.json` (terms register); spec and design in `C:\Users\mwoo7\Desktop\calcscrape\docs\research\` (MASTER-SPEC.md, DESIGN-UI.md, INTERNAL-LINKS.md, END-TO-END-PLAN.md).

## Page template (frozen "final form")
Gauge page = hero (flow, stage, percentile bar, 24 h change) + blocks. Dashboard: alerts, 7-day chart, [location map | radar], 3-period weather, public land. Water: chart, daily means, same 50 days in earlier years, record comparison, annual peaks, SNOTEL, water temperature by month, quality sensors, upstream/downstream gauges, flood stages, historic crests, NWS flood impacts. Forecast: alerts, NWS river forecast or NWM guidance, rain, 8-14 day outlook, hourly heatmap, 14-period forecast, radar, air obs, sun. Tools row: Save gauge (localStorage), CSV download (client-side from USGS API). Phone: one column, charts switch to a 340 px version, tables scroll in their own box, bottom tab bar.

## Not built, on purpose (reasons in `data/sources.json`)
EPA ATTAINS, OSM access points, Recreation.gov camping, HIVIS cameras, PFBC fishing layers, Drought Monitor, NID dams (terms not read or not found), WaterWatch (retired Feb 2026), hero photos (licence per photo), unit toggle (partial metric would mislead), embed widget (needs a separate utility page), national gauge map (needs a state outline asset), email alerts (needs a mail service and owner decision).

## Post-launch list
Name cleaner v2 (1,801 low-confidence names) and the other 9,074 gauges in waves; hosting decision before wave 3 (28,901 files); contact email, analytics, ads; national hubs only for NLDI-verified rivers.
