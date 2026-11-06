# Handoff 2026-11-06: lakes, coasts, keyword queue

Live on main d686af0 (built 2026-11-06 23:14 UTC, 0 failed pages).

## Done this session (all live unless noted)
- USGS key: measured 951/1,000 left; daily 8-day re-pull and neighbour list spread over 24 hour slots (lib/common.py day_due). Breaks near 8,800 gauges.
- Lakes: 9 built (Choke Canyon, Canyon, Corpus Christi, Medina, Hartwell, Lanier, Kerr, Great Salt Lake, Powell). Go-live blockers fixed (title "water level", open_wave lake years, truth_live/index_live cover /lake/). QUEUED, not yet public.
- Coasts: 13 NOAA CO-OPS pages (/coast/<place>/) on the lake path: San Diego, Norfolk, Myrtle Beach, Fort Lauderdale, Chatham, Monterey, Pensacola, Panama City Beach, Port Angeles, New York, Atlantic City, Boston, Galveston. Next tide, today's tides, observed vs predicted (our calculation), predicted tide dashed on the chart, NOAA water temperature (held when suspect), NWS alerts/weather, San Diego waves (CDIP 46254). All phone-reviewed and fixed. QUEUED, not yet public.
- E. coli: Water Quality Portal WQX 3.0 (legacy had no USGS results after 2024-03-11), 40 stations a request, weekly.
- Census moved to the USGS Water Data API (waterservices retires Q1 2027).
- Keyword debate (closed): first gauge on a keyword gets the full band, others 5%; multi-country rows 0; check.py queue_over gate; coast titles lead with "<place> tides".
- open_wave writes data/open-wave-last.json; watchdog alarms on live pages stuck out of Google.

## First thing next session
1. Read PLAN.md: "MASTER PLAN 2026-11-06", "KEYWORD DEBATE", "COAST PILOT", "ChatGPT ... round" lines.
2. Confirm the daily release took the 22 queued lake/coast pages: data/waves.csv status live for 08206900 ... 8771450; read one live /lake/ and one live /coast/ page; status.json 0 failed; data/open-wave-last.json stuck is empty.

## Open, in order
- Keyword Planner run (owner's account, Chrome): "tide times", "water temperature", "river level today", "dam release", "gauge" for the top 100 names, keep 12 monthly values.
- Hand-check river names that mean several places at 5,000+ (Lake Fork TX, Buffalo AR, James, Wolf; Sabine/Shenandoah tagged NZ).
- world_queue CAP lift for "water level"/"level" with a water-type match (rerunning tools/world_queue.py would drop the hand-added lake/coast rows 20001+: make it read data/lakes.csv and data/coasts.csv first).
- Coast leftovers: Port Angeles air monitor in Canada labelled EPA; flash-flood reports beside "No active NWS alerts"; ramps inland of ocean piers; county drought section on coasts.
- Lakes: full pool / % full outside Texas (USACE CWMS: terms unread), Mead and Powell storage (USBR RISE: terms unread), Travis (TWDB-only page), Tahoe (gage height path), lake state hubs.
- Great Lakes: needs a lake-wide-average source with read terms.
- Waves for other coasts: partner buoy terms (CBIBS, CORMP, TABS) unread; NOAA-owned buoys only.
- Years-long sweep items 2-14 in PLAN.md.

## Owner only
- Read in a browser: usace.army.mil disclaimer, water.ca.gov Conditions of Use, data.usbr.gov/rise terms.
- Publisher name and contact email; Cloudflare Workers Paid before ~5,300 gauges or 100,000 page views a day.
- Regenerate the Met Office key pasted in chat.

## Lessons
- Never test the Water Quality Portal in a loop: its firewall blocks the IP (429).
- Heredocs mangle backslashes: use the Edit tool for regex or "\n".
- waves.csv / world-queue.csv line endings: add with `git -c core.autocrlf=false add` and append bytes, or the whole file shows as changed.
- A push to check while a dry run runs cancels it.
