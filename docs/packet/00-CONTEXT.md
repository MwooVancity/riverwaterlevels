# CONTEXT (one page; read first)

**Goal.** riverwaterlevels.com: a US river-conditions website (current flow, level, how it compares with normal, trend, forecast, alerts, history, flood record) from free government data only, funded by ads, built by one non-coder owner with an AI assistant (Claude). The owner's words: be the best place for "a person standing at the river on a phone", "user first, not Google", "tens of thousands of pages", release ordered by "water sports and activities". Domain bought 2026-10-16; 25 gauge pages live; the whole site is under a `noindex` hold the owner lifts.

**Success means.** NOT STATED by the owner. [Owner to fill: visits and revenue targets, time horizon, whether ads are mandatory.]

**Audience.** Paddlers, anglers, rafters, tubers, swimmers, boaters, flood watchers, on a phone at or near a river.

**Business model.** Ads (AdSense if approved). Revenue per 1,000 visits and traffic needed: UNKNOWN. Running cost: about zero (Cloudflare free Workers, GitHub free Actions). Owner time: UNKNOWN.

**Non-negotiables (owner).** Government data only; USA only; free sources and hosting; no composed advice or verdicts on pages (only source values, labels, verbatim source text); every block shows its source and time; a block shows only if its source's terms are cleared; the owner never runs commands; `noindex` stays until the owner decides; the reader judges, not search engines.

**Open to challenge.** One page per gauge; the verdict-free rule; ad-supported model; the 25 pilot gauges; the release-order formula; the AI review process; the goal "tens of thousands of pages" (gauges alone make about 9,500 files); lakes later.

**History that matters.**
1. The owner's other site (calcscrape, car-repair cost data pages) lost about 99% of Google impressions on 2026-09-14 (about 800 a day to about 2 a day, uniformly on every page, still indexed); AdSense rejected it as thin on 2026-10-02. Cause unproven: new-domain "sandbox", Indexing API misuse, a core/spam update on scaled content, brand overlap were the hypotheses. See `evidence/calcscrape-history.md`. This site copies that site's "data page, almost no prose, templated per entity" model.
2. This site started as 3 tabs per gauge (Dashboard, Water, Forecast), became one page per gauge with a Forecast page where NWS issues one, and on 2026-10-18 the owner merged the Forecast page in ("we don't need multiple pages for the same river").
3. First plan said "index everything"; now small cohorts of at most 25 gauges a day behind a kill switch (`data/index-allow.json`).
4. The first release order used Wikipedia page views of the river NAME and drainage area; a review found it ranked 89% of gauges by river size and gave one famous river's fame to every gauge sharing its name. It was rewritten on 2026-10-18 from Wild and Scenic Rivers, the Nationwide Rivers Inventory, Census places and tailwater; its back-test (19 of 25 hand-picked gauges) was tuned after the fact and is not a valid test.
5. About 18 rounds of "fresh-brain" AI reviews of the template were run on 2026-10-18/19 (`late/`). Values matched USGS/NWS in every round after the first few; findings were wording, silence, contradictions between two statements, claims on the trust pages, and twice real data gaps. Each class became a test (`code/truth_tests.py`).
6. GitHub Actions is the deployer; its scheduled runs fire every 2 to 6 hours in practice (see `evidence/ci-runs.txt`), not every 30 minutes; the owner's PC also runs two scheduled tasks. Freshness of the numbers on the page is delivered by a browser-side refresh of the latest reading.

**Tried and failed / reversed.** Population-based reach in the queue score (under-ranked rural recreation towns); smoothing flow changes into averages (reviewers could not reproduce the numbers, removed); a blanket CSS rule that wrapped table cells (broke numbers mid-word, removed); a review tool that silently never recorded a verdict (fixed); the Windows tasks racing manual work and once deploying an unreviewed tree.

**Unknown.** Search demand for any page type; how long Google takes to index a new domain; whether Google will treat thousands of templated gauge pages as scaled content; whether every source's terms permit every block (several are hidden until read); whether anyone beyond the owner's reviewers likes the pages (no real paddler or angler has tested it); ad revenue.

**What a reader gets that competitors do not.** Not established. Competitors a person would use: USGS WaterData, NWS/NOAA water.noaa.gov, American Whitewater (runnable ranges, releases, hazards, access points), Lakebrief (lake pages), Windy and weather apps, local fly shops. See `evidence/competitors/`.

**Glossary.** gauge = a USGS river measurement station; cfs = cubic feet per second (flow); gage height = water level in feet relative to the gauge's zero; percentile for date = where today's flow sits among every year's flow for that calendar date; NWS forecast point = a National Weather Service river forecast location (can be a different place than the USGS gauge); tailwater = river just below a dam; noindex hold = pages tell search engines not to index; cohort/wave = a batch of pages released together; SHIP verdict = a recorded "ready" from a reviewer; kill switch = the config that lists which pages are indexable.

**File map.** `MANIFEST.md`.
