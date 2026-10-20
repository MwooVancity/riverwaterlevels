# Page contract: every block has four honest states

The template is code (`lib/render.py`, `blocks2.py`, `blocks3.py`, `templates/site.css`); this file is the rule it must satisfy for every gauge type, enforced by tests.

## The four states of any block
| State | Meaning | What the page shows |
|---|---|---|
| valid | source answered and passed checks | the value with unit, observation time, Source line |
| valid-empty | source answered "nothing" (no alerts, no impact at this stage) | an explicit sentence, never silence ("not a statement that conditions are safe") |
| unavailable | source did not answer or sent a wrong shape | "Unknown" or "unavailable", never "none"; blocks that cannot be built are hidden by the guard and logged |
| stale | older than its limit (alerts 3 h, air obs 3 h, rain 6 h, river forecast 24 h; flow and stage show their age badge) | the value with its real age, marked old, no "current" claim |

## Safety blocks (a failure fails the gauge and keeps its previous page)
`b_alerts, b_river_forecast, b_impacts, b_stage_chart, b_flow_chart, b_offline, b_flood_stages, b_noforecast, b_nws_point` (`render.SAFETY_BLOCKS`). Every other block hides alone when it fails.

## Rules that never bend
- A number always has a unit, an observation time and a source. No sentinel, no negative flow outside tidal reaches, no Python `None` in text.
- The headline comparison judges the latest reading when it differs from the 24 h mean by more than 30% (non-tidal).
- A source record is a dict; fields have the types real data has (`data/cache_shape.json`); anything else counts as empty.
- No verdict words (safe, good, runnable) and no forecast of our own.

## Who proves it
`check.py` (text and structure), `truth_tests.py` (20 contracts across the 25 gauges incl. plausibility and guard), `truth_types.py` (10 gauge-type variants), `truth_fuzz.py` (every source field set to 5 junk values; 0 failures at 9,354 renders), `tools/review/*` browser gates (layout at 340 to 1280 px, search, live alerts, range tile), the signed template review, `truth_live.py` against USGS and NWS, the watchdog. See `CLAUDE.md` and `docs/research/GATE-WIRING-AUDIT.md`.

## Adding a new data block
Source row in `data/sources.json` with terms and status; fetch in `collect.py`; `python tools/gen_cache_shape.py`; block function `b_*` with its four states; add it to a fixture or the fuzz sample; new template hash needs a fresh signed review.
