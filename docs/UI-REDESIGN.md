# UI redesign: the hater-reader sweep (measured 2026-10-20, Gauley and Hudson gauge pages, phone width 390 px)

Persona: a person at the river with one bar of signal who does not care how many datasets we have. Everything below was measured on the built pages, not guessed.

## What the hater sees
| Measure | Gauley | Hudson | Verdict |
|---|---|---|---|
| Page height on a phone | 13,365 px (about 16 screens) | 17,396 px (about 21 screens) | Lakebrief's whole dashboard is about 2,000 px |
| Blocks (sections) | 28 | 31 | no ranking between them |
| Tiles above the first chart | 10 tiles = 1,204 px | 1,404 px | the answer sits under a wall of cards |
| Fine print: the "Source:" line under every block | 2,992 px (22% of the page) | similar | content for lawyers, shown to everyone |
| Tags (LIVE GAUGE, OFFICIAL NWS...) and "#" permalinks | 28 + 28 | | decoration nobody asked for |
| Tables | 21, 7 of them turned into stacked cards | | long, dense, low value per pixel |
| Biggest blocks | Federal flood declarations 3,330 px; Flood events 2,542; Largest annual peaks 2,440; Field measurements 1,629 | 2,542; 2,154; 1,629 | 1970s history in front of the reader |

## Repetition (same fact shown again)
- Flow and its change: answer strip, flow tile, trend tile, rate-of-change table (4 times). Forecast high: forecast tile, stage table, river-forecast block, stage chart (4). Gage height: 3. Rain "0.00 in": 4 (tile, rain totals, forecast rain totals, hero).
- The SAME flow series drawn four times: last 7 days, last 30 days, last 12 months, "same 50 days in earlier years".
- Weather split over 6 blocks: hourly heatmap, weather forecast, rain totals, forecast rain totals, outlooks, radar.
- Flood split over 10 blocks: stage chart, flood impacts, flood stages, stage years, historic crests, flood outlook, storm events, declarations, annual peaks, forecast point.
- Daily mean flow: a fold, a table and two charts.

## Hater verdicts, block by block
1. Header and title: fine. The Save / CSV buttons were ahead of the answer (moved below the tiles).
2. Tiles: two are dead weight on most gauges ("Not issued" in 36 px serif, "Your range" empty); air temperature, sunset and rain are trivia that take a full row.
3. Dial: 350 px to say "normal". A slim bar says it in 40 px (built).
4. Flow, stage and flood charts: stage chart plus its 7-row table is 1,179 px.
5. Weather: vertical list. Weather belongs in a horizontal strip, like every weather app.
6. Tables of time series on a phone become stacked cards, 5 lines per row: unreadable. Time series want a horizontal scroll with a pinned first column.
7. History: declarations from 1975 and storm events lead the lower half. The reader cares about the last 5 and the biggest.
8. Colour: everything is white cards on pale blue with grey type. Colour carries no meaning except in the dial.
9. Jargon left: "NWS RFC estimate", "Gage height to flow rating", "StreamCat", "NHDPlus reach", "Upstream watershed characteristics".
10. No way to move: the chip row scrolls away; nothing sticks.

## The redesign (staged; each stage is one template release with a fresh signed review)
**Stage A, structure and noise (cuts the page by about 60%)**
- One-line answer strip (built) + slim range bar (built). Tiles reduced to 6 (flow, stage, compared, change, alerts, forecast); air, rain and sunset become one horizontal "Weather now" strip; "Your range" becomes a link under the title.
- Five tabs on a phone, sticky bottom bar, all content stays in the HTML: **Now** (alerts, flow chart, flood ladder) / **Weather** / **History** / **Data** (the long tables) / **Area** (nearby gauges, map, about, links). Desktop keeps the two-column page.
- Source lines become a one-line "Source" footnote with the full text and exact record link inside (the rule that every figure links to its exact record stays). Remove the tags and the "#" glyphs.
**Stage B, merge the repeats**
- ONE flow chart with a range switch: 7 days / 30 days / 12 months / earlier years.
- ONE weather block: horizontal hourly strip (time, temperature, rain chance, wind), rain totals as a row, radar as a thumbnail link.
- ONE flood block: ladder with the current level, impact at each stage, a bar of annual peaks against the stages; declarations and storm events show the 3 most recent with "all N" inside a details.
**Stage C, tables and colour**
- Time-series tables scroll horizontally with a pinned first column and a visible scroll hint; text tables stay stacked and are capped at 5 rows with "show all".
- Colour system: band colour (amber / blue / purple, as the dial) on the flow tile edge, sparkline and answer pill; alerts amber when active; section headings with an accent; dark mode checked. No verdict colours.
- Plain words: drop or translate the jargon above.

## Rules while redesigning
Nothing is removed that a data rule requires (source, exact record link, observation time). No verdict words. Every merged block keeps its four states (docs/PAGE-CONTRACT.md). A phone first screen shows: title, one-line answer, flow, stage, comparison, alerts, with no scrolling past 900 px.

## The rail rule (owner 2026-10-20: "horizontal sliding blocks like a weather widget; the user must not scroll for 10 minutes")
Anything made of repeating same-shaped items is a sideways RAIL (scroll-snap cards, next card peeking, no JS, keyboard reachable, labelled region). Only text stays vertical (alerts, impact statements, safety). Block, current phone height (Gauley), new form, saving:
- Flood declarations (3,330) and flood events (2,542): rail of the 3 latest, "all N" in a details. About 5,000.
- Largest annual peaks (2,440): bar of peaks against flood stages + top-5 rail. About 2,000.
- Hourly forecast (550) + weather forecast (438 to 1,095): one weather widget, hourly rail + day rail. About 700 to 1,300.
- Rate of rise and fall (545): rail of 1 h / 3 h / 6 h / 12 h / 24 h chips. About 400.
- Compared with the record (1,069): rail of 5 stat cards. About 850.
- 7 d, 30 d, 12 mo, earlier years (1,966): ONE chart with a range switch. About 1,500.
- River forecast (947): rail of forecast points, crest highlighted. About 700.
- Rain now (587) + rain forecast (394): one row of rain chips. About 780.
- Stage chart + flood impacts (1,799): chart + rail of stage cards (Action / Minor / Moderate / Major with margin), impact text on tap. About 1,000.
- Nearby gauges, official links, watershed facts (about 1,350): gauge-card rail, link chips, fact chips. About 1,000.
- Hero tiles (1,204): 2 big tiles + comparison, everything else in ONE swipe rail. About 640.
- Field measurements (1,629), daily readings (639), about gauge (731): 5-row tables with "show all", compact definition grid. About 1,500.
Target: each phone tab 1,500 to 2,500 px (today 13,365 in one scroll). Build order: rails for declarations, storms, rate of change, record comparison, hero rail; then weather widget and the single range-switch chart; then forecast, rain, stage ladder, tables.
