# ChatGPT prompt: is this river page missing any helpful data?

Attach the three files (`COMPLETENESS-AUDIT-2026-10-23.md`, `BLOCKS-INVENTORY.md`, this prompt). Visit a live page to see it: https://riverwaterlevels.com/river/potomac-river-md/little-falls/

---

You are a hard-to-impress product reviewer. I run riverwaterlevels.com — one page per USGS river gauge, government public data only, every number with its source and timestamp, no prose, no "safe to swim/float" verdicts. I want it to be the single most helpful river-conditions page for every water user, A–Z.

`BLOCKS-INVENTORY.md` lists every data source and block already on a page (~30 datasets per gauge). `COMPLETENESS-AUDIT-2026-10-23.md` is my own fresh-brain audit scoring it ~88/100 with a top-5 missing list. A live example is linked above.

Do this, tightly, with evidence:
1. **Find anything still missing** that (a) a real river user would want, (b) has a genuine PUBLIC data source (federal or state — give the URL), (c) returns a per-gauge or per-place value. Go user by user: angler, boater, camper, diver, emergency manager, hunter, irrigator, kayaker, parent, photographer, rafter, researcher, rower, rescue, sailor, SUP, swimmer, tuber, wader, whitewater. Ignore anything already in the inventory.
2. **Challenge my audit** — is anything in its top-5 wrong, overrated, or actually a verdict in disguise? Is the 88/100 fair?
3. **Confirm the dead ends** — datasets that *feel* like they should exist as a per-river feed but don't (national bacteria/E.coli for rivers, national boat-ramp registry, planned dam-release schedules, HAB for rivers). Add any I missed so I stop chasing them.
4. **Rank the real additions** you'd make, by reader value per unit of build effort, and say which are federal-universal (one fetch, every gauge) vs state-fragmented (per-state adapter).

Rules: never suggest safety verdicts (data-only site); give a real source URL for every suggestion or mark it "no public feed"; don't pad — if the honest answer is "it's near-complete, the rest doesn't exist as data", say that. Return one ranked table.

---
(end)
