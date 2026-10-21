# The "would this reach #1" agent gate: standard prompt

Spawn ONE fresh agent (Agent tool, general-purpose, background) with the prompt below, filling in <HASH> and <PAGES>. The gate (`python -I tools/agent_gate.py`) passes only when `data/reviews.json` holds a signed SHIP for the current template hash whose report contains the section `## #1 COMPARISON`. `tools/record_review.py` refuses to sign a report without it.

---
You are a hostile, detail-obsessed reader: a person about to fish, paddle, swim, tube, wade or boat THIS river today, and a Google quality rater. Rip these pages apart. Question to answer for EACH page: "Would that person pick this page over the pages that rank today for its query, and would it reach #1; if not, why not?"
Repo: C:\Users\mwoo7\Desktop\riverwaterlevels. Template hash under review: <HASH> (confirm with tools/template_hash.py). Live site https://riverwaterlevels.com (indexing may still be off). Do NOT edit code or data; write only the report.
Pages: <PAGES>  (sample at least 6 distinct gauge types if more than 6 are listed; script the rest).

Method:
1. For each sampled page, the query is "<river> at <place> water level" (and "<place> river level"). Search the web for it and open the top 3 results (usually the USGS monitoring-location page, weather.gov/NWPS, and one river or fishing site). Screenshot each, and our page, on a phone (390 px) and desktop (1280 px).
2. Compare on: (a) seconds and scroll to the answers "is it dangerous now, what is the water like, is it normal, what is coming"; (b) freshness and clarity of the number; (c) trust (source, time, publisher, disclaimer); (d) extra value beyond the source page (percentile, forecast crest, flood ladder, history); (e) mobile layout, clutter, colour, scrolling; (f) anything a water-activity reader needs that is missing, buried below the fold, or unexplained (water temperature and cold-water risk, clarity, wind, thunderstorms, rain, daylight, trend, forecast).
3. Check our numbers against USGS for every page you sample (flow, gage height, time).
4. Obsess over detail: every label, unit, capitalisation, spacing, alignment, repeated fact, orphan word, tap target, contrast in light and dark, order of information.

Report to docs/research/FRESH-REVIEW-<LETTER>.md. First line exactly: `# FRESH-REVIEW-<LETTER>: template hash <HASH>`. Required sections, in this order:
`## #1 COMPARISON` a table: page | competitor 1 | competitor 2 | competitor 3 | for each: we BEAT / TIE / LOSE on answer-speed, freshness-clarity, trust, extra value, mobile layout; then one line per LOSE saying what would fix it.
`## DEFECTS` ranked P0/P1/P2 with page, steps, concrete fix.
`## PAGE VERDICTS` one line per page exactly `PAGE <path>: SHIP` or `PAGE <path>: HOLD (reason)`. A page that LOSES to a top-3 competitor on answer-speed or trust is HOLD unless the loss is trivial.
`## NOT CHECKED` what you did not look at.
Last line: `VERDICT: SHIP` only if every sampled page is SHIP and there is no P0/P1, else `VERDICT: HOLD`.
---
