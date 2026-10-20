# FRESH-REVIEW-10-S (latest): template hash b69212c36ff966c8 (confirmed with tools/template_hash.py)

## Resolved earlier (re-checked at c5170c6/ae46bb0/4d4f615, not re-tested in this batch beyond the form)
- Range form no longer breaks on phones (letter-per-line column gone).
- Flood-stage note wording: honest; margins arithmetic matches (53.0-17.39 = 35.6 Ohio; 21.0-16.01 = 5.0 Hudson).
- Six UI polish changes verified on Hudson (equal heights, rules, boxed safety note contrast, "No alerts", stage-table alignment). Chip-row fade never seen on a gauge page (unverified).

## This batch
(1) Range tile, real browser (Playwright, mobile, 390 and 340 px, Hudson, served on :8769, stopped after). Inputs are type=text inputmode=decimal, aria-labels present, focus lands in "Low" on open, no overlapping controls, smallest tap target 40 px, no horizontal scroll, open height 199 px (216 px with the error line at 340). Typed 5,000 and 12,000, Save: tile reads "In your range / You set 5,000 to 12,000 cfs. Now 8,910 cfs."; survives reload; "5 000" and "12 000" also work; Change reopens with 5000/12000 filled; Clear returns to "Set your range". Letters, negatives, empty and low above high are refused with "Enter the lowest flow, then a higher flow, as numbers." tools/review/range_test.mjs passes (commas; live refresh keeps the form open). I could not run a real live refresh (hosts blocked).
(2) Normalising risk: compared dist_next with the live site for Hudson and Gauley (same observation times, so a clean test). Flow, stage, percentile, forecast, flood stages, alerts and dates: no value lost or changed. Only differences: Hudson +1 block (flood_stage_years: 56 of 71 annual peaks at or above the 21.5 ft minor stage, with the datum caveat), the new note text, and a neighbour gauge (New River 4,300 vs 4,160 cfs, fresher). No "None", "NaN" or "undefined" on any of the 25 pages; status.json block_errors is empty. Not compared: the other 23 pages.
(3) Guard. Read render.py end, build.py, publish.py. A raising block is logged, shown in build output and status.json; hero, safety text and sources are unguarded, so a crash there fails the gauge and publish carries the old page forward. I found no path to a half-built page, and a section heading is only written when a block follows. Gap, P1: SAFETY_BLOCKS covers alerts, river forecast, impacts, stage chart, flow chart, offline only. A raise in b_flood_stages (the flood-stage table), b_noforecast (the "no forecast issued" statement), b_nws_point, b_dams, b_wtemp ("water temperature not available" note), b_flood_outlook or b_stage_years is hidden silently and the page ships looking complete; a landowner then sees no flood stages with no explanation. Fix: add b_flood_stages, b_noforecast, b_nws_point (and b_dams, b_wtemp) to SAFETY_BLOCKS. The match is a string search for " b_name:" in the log text, which is fragile; matching on function name stored separately would be sturdier.
(4) Text: "No earlier day on record" appears on none of the 25 pages built now, so I could not read it in place; no printed "None" anywhere.

## P2
- Silent rounding: low 5.5 and high "1e3" are accepted and saved as "6 to 1,000 cfs".
- After an invalid entry the tile keeps its old label ("In your range") while the sentence below shows the error; after Clear the hidden form still holds the last typed values (5.5, 1000).
- Hudson and Gauley both exactly 50th percentile (still unchecked against USGS stats); orphan Sunset tile on odd tile counts.

## Could not check
Chip-row fade on a gauge page; other 23 pages against live; live NWS/USGS refresh; "No earlier day on record" in place; screen reader.

## Final read (hash 003218c6cc8aad14)
Confirmed in the source: SAFETY_BLOCKS now holds nine names incl. b_flood_stages, b_noforecast, b_nws_point; build.py matches the exact function name; the submit handler accepts only ^[0-9]+([.][0-9]+)?$ and refuses high below low; range_test.mjs passes. Not in the list and flood-related, but supplementary and silent only as absence: b_flood_outlook, b_nwm_medium, b_wpc, b_qpf, b_crests, b_rise (optional to add). I did not rerun the fuzzer.

VERDICT: SHIP
P0 list: none
