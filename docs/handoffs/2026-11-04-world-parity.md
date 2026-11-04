# Handoff 2026-11-04: world parity

Read PLAN.md first: sections "Fresh review of the queue release" and "US vs world parity audit" (both 2026-11-04) hold every open item, in order.

Live on main tonight:
- 4f497a4: a failed EA history fetch retries in 7 days.
- 10d579c: Met Office Global Spot for England weather. Not proven live, because no England gauge page exists yet.
- c18cbb6: a country with no live page opens 2 gauges a day.
- 6b561f8: country and river hubs get a 700-link budget and are carryable. Its dry run and deploy were running when this was written; read the refresh run for that sha.

Next, in order:
1. After the 11 UTC release adds England's first gauges, read the refresh log line `met <gauge> ... hourly fields [...] daily fields [...]` and one England page. A missing field name is a fix in `lib/wx.py` `met_forecast`.
2. The mechanical parity script (owner approved): `tools/parity.py`, run by `check.py --selftest` or gates. It must:
   - list every US/world branch and every check that skips world pages;
   - build one German, one Canadian and one English page and run every US check on them;
   - render with the clock shifted 2 days and across a clock change;
   - feed each world source empty, cut short and failing, and prove only its own country goes Unknown.
   Every gap it finds gets a failing test first.
3. Then the world gaps from PLAN.md, worst first: URL collision, Canada time zones, phone refresh mixing numbers, truth_world inside the deploy gate, per-feed failure counter, world supply from the station lists.

Rules: one background job at a time; `check` dry run before main; reviews are `/code-review high`. Never use a key pasted in chat.
