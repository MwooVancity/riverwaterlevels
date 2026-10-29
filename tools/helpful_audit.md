# Master helpfulness audit (owner 2026-10-29: "I want literally everything. Down to the UI")

Judge as the person, never as Google: a change that helps ranking but not the person is rejected; a change that helps the person needs no ranking reason.

Use: every build batch checks the categories it touches; a periodic audit runs ALL categories on 3 contrasting pages (a big dammed river, a mountain/snow river, a small river with no NWS forecast) plus the home page, one state page and one river hub. Text pass first (cheap), then screenshots only for categories that need eyes (marked [eyes]).

## The reader (judge everything as these people, on a phone, at or near the river, 30 seconds)
Paddler/kayaker/rafter, angler (wading or boat), swimmer/tuber, boater (ramp, fuel, depth), camper, guide/outfitter, rescuer, person living or driving nearby, first-time visitor who knows nothing about rivers, someone with low vision or on a screen reader, someone with one bar of signal, someone outside the US who thinks in metres and Celsius.
For each: what do they need first, what would make them leave, what would make them come back?

## Output format (always)
Table: category | page(s) | exact text or element (quote, image file for [eyes]) | what goes wrong for which reader | severity (BLOCKER = wrong or dangerous; MAJOR = confuses or slows most readers; MINOR = polish) | plain fix (label, explanation, move, merge, format; never an invented fact or a verdict). Worst first. Then: the 5 fixes that help the most readers. Machine-catchable findings get "→ check.py rule".

## A. Purpose and the first screen
1. Does the first screen answer, without scrolling: how high/how much water now, is that normal for today, rising or falling, how old the reading is, is anything dangerous (alerts, flood), what is coming (forecast)?
2. Is the page's one job obvious within 3 seconds (which river, which place, which gauge)?
3. Does anything on the first screen not serve the reader at the water (citations, codes, developer links, drainage area)?
4. After this screen, does the person still need another site or app (USGS, NWS, a weather app, a fishing report) to decide about today? Name what sent them away.

## B. Truth and consistency
5. Every number matches its source and every other place it appears (same value, same rounding, same unit, same time).
6. No two statements contradict (word vs number, tile vs table, label vs chart, heading vs content).
7. Every derived word (Steady/Rising, Normal/Above, Forecast high, Good) follows one stated rule that a reader could check from numbers on the page.
8. Daily average vs single reading vs forecast vs estimate always labelled as which.
9. Different windows (24 h, 7 days, 28 days, month, record) always named where used.
10. Datum/scale differences (NWS vs USGS zero point, old gauge scale) said where they matter.

## C. Freshness and time
11. Every reading, forecast, image and table says when it is from, in local time with the time zone.
12. Old data is visibly old (age in words) and never sits under "now", "live", "current" or "next 24 hours".
13. A gauge that stopped reporting says so at the top, not only in small print.
14. Times across a clock change (DST) read sensibly.
15. The page's own build/refresh time and the live update time are both clear and agree.

## D. Plain language (the first-time visitor)
16. Every unit and term explained once where first used: cfs, gage height, zero point/datum, percentile, flood categories, AQI, SWE, provisional, regulated.
17. No unexplained codes: NWS point IDs (BIGI1), HUC numbers, station IDs, product names (NWM, QPF, CPC, ACIS, WPC, ATTAINS, StreamCat, NowCast, MRMS).
18. Headings say what, where and when ("Hourly weather at Albuquerque, next 24 hours", not "Weather").
19. Numbers have meaning: is 2,270 cfs a lot here? (comparison to normal, to the reader's activity thresholds from agencies).
20. Sentences short; one idea each; no hedging chains; no repeated sentences across blocks.

## E. Safety and verdict risk
21. Nothing reads as "safe", "good to go", "fishable", "runnable", including indirect words (Good, Normal, Open, Supporting, Steady used as reassurance).
22. Danger information (alerts, flood stage, cold water, low-head dams, closures) is never below less important content and never collapsed.
23. "No alerts" is never presented as "no danger"; absence of data is never presented as absence of risk.
24. Sources of danger info are official and named; reader is pointed to the authority (NWS, park, state) where they must check.

## F. Completeness and information gain
25. Every public dataset that answers a reader question at this river is present (Line 0): readings, forecast, flood stages/impacts, low-water levels, weather, wind, rain, snow, water temperature, quality/advisories, dam releases, access points, stocking, closures, camera, tides, history, nearby gauges.
26. What does this page show that USGS, NWS (water.noaa.gov), snoflo and the top Google result do not? If nothing, say so.
27. Every "not available" is true (no public feed has it) and named in the gaps line.
28. Missing reader questions with no source → listed as gaps for PLAN.md.

## G. Order, structure and length
29. Blocks in order of what the water-activity reader needs: level/flow, the water now, weather, river forecast, getting on the water, longer outlook, history, deep data.
30. Each block earns its place for THIS reader; deep/technical data in closed groups at the bottom, never deleted.
31. No block repeats another block's numbers without adding something.
32. Page length: can a reader find any block in 2 taps (jump links, section headings)?
33. Empty and unavailable states are one line, not a full card.

## H. Visual design and layout [eyes]
34. One visual system: same card style, spacing, label style, number style, colour meanings across blocks.
35. Visual hierarchy: the most important number is the biggest thing; headings scan; secondary text is visibly secondary.
36. Colour carries meaning consistently (warning = amber, danger = red, normal = neutral) and never alone (also words/icons).
37. Nothing cut off, overlapping, wrapping mid-number or mid-unit, or clipped at the right edge on a 390 px phone and on desktop.
38. Tables fit the phone without sideways scroll unless the scroll is obvious and intended; columns have units in headers.
39. Charts: title says what/where/when, axes labelled with units, readable on a phone, current value marked, legend not repeated, no chart restating its title.
40. Icons have text alternatives; arrows say what they mean.
41. White space: no wall of text, no cramped tables, consistent margins.
42. Dark mode (if offered) keeps contrast and colour meanings.

## I. Interaction and controls [eyes]
43. Tap targets at least 44 px; links look like links; toggles say what they open and show state.
44. Collapsed content says what is inside and how much ("Every hour, 24 rows").
45. Search finds a river by name, town, state, nickname and typo; works with every live gauge.
46. "Near me" works on a phone and says what it needs.
47. Share, copy, favorite, alert and unit controls work and confirm the action.
48. Live refresh updates numbers without layout jumps; the page never shows a number changing to an older one.

## J. Speed, signal and offline
49. Page weight small; images and radar load only when visible or tapped; no layout shift.
50. First screen readable on a slow 3G connection within a few seconds.
51. Works offline or on weak signal with the last data and its age (service worker).
52. Installable to the home screen (manifest, icon, name).

## K. Accessibility
53. Text contrast meets WCAG AA; text resizes to 200% without breaking.
54. Headings in order (h1, h2, h3); landmarks; tables have header cells; charts have text summaries.
55. Every image/icon/chart has a text alternative; screen reader reads numbers with units.
56. Keyboard reachable; focus visible; no information by colour alone.

## L. Navigation and findability
57. Breadcrumbs, river hub, state page and nearby/upstream/downstream gauges link sensibly (3-5 related links).
58. Home page lets a new visitor find their river in one step.
59. 404 page helps (search, nearby rivers).
60. URLs readable and stable.

## M. Trust and transparency
61. Who runs the site, why, contact, corrections policy, methodology, last checked against the source — reachable from every page.
62. Every block names its source with a link to the exact record; no unsourced number.
63. Disclaimers short and placed where they matter, not repeated on every card.
64. Ads (if any) never look like data and never sit inside safety information.

## N. Return visits and personal use
65. Favorites / recent rivers; alerts on a reader's level; add to home screen; shareable card that shows the river and current flow.
66. Units switch (cfs/m3/s, ft/m, °F/°C) remembered.

## O. Recognising and sharing the page
67. The page name (tab title, heading, link preview) tells a person at a glance which river, which place and that it is today's water, in their words, with no stale numbers.
68. A link sent to a friend shows the river and a true preview, so the friend knows what they are opening.
69. Every page is about its own river: nothing reads as a copy of another page with the name swapped.

## P. Privacy, legal, ethics
70. No tracking beyond what is disclosed; consent where required; no personal data stored without need (alerts: minimal).
71. Government data terms respected; credits correct.

## Q. Errors and edge cases
72. A source down, a field missing, a value 0, negative, huge, or a string where a number was expected: the block hides or says "not reported", never crashes or shows "None", "NaN", "–" where a value exists.
73. Ice-affected, tidal, regulated, estuary, canal gauges and gauges without stage or without flow read sensibly.
74. Time zones across state lines; gauges near midnight; first/last day of month.
