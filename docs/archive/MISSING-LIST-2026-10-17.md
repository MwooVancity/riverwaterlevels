# Everything not yet built or decided (2026-10-17). Ranked inside each group. Reasons are in docs/MASTER-FINAL.md for items left out on purpose.

## A. Information gain: what the USGS and NWS pages do not give (data only, no verdicts)
1. Flow duration curve with today's flow marked (StreamStats publishes the 1 to 99 percent duration flows): "how often is it this high or low".
2. Low-flow statistics (7-day 2, 10 and 20 year lows, StreamStats): drought context.
3. Monthly flow chart (median and range for each month with the current month marked).
4. This year against the wettest, driest and median year for the date.
5. Days since the last time above flood stage, above the 90th percentile, and below the 10th percentile.
6. Basin rainfall (average over the watershed, last 24 and 72 hours), not only rain at the gauge point.
7. Provisional or approved status and USGS data qualifiers (ice, estimated, equipment) shown per reading.
8. Water temperature live where the gauge measures it, plus dissolved oxygen, turbidity, pH, conductance, with their time (sensors exist at some gauges; none at the three tested).
9. Dam releases and schedules upstream (USACE, Reclamation, TVA): where a dam controls the river.
10. Upstream lake and reservoir elevations (USGS parameter 62614) that influence the river.
11. Nearby gauges on the same river as a compact table with live flow (not only upstream and downstream).
12. National Water Model 10-day flow where there is no NWS forecast (returned for St. Louis only in tests).
13. US Drought Monitor for the county (data returned for all tested gauges; terms: credit required, commercial use unclear, owner email needed).
14. Moon phase and twilight from the US Naval Observatory (government source) for anglers.
15. Wind and thunderstorm timing from the NWS gridpoint feed in the hourly heatmap (wind gust is collected; storm probability is not shown).
16. Public access sites from Recreation.gov RIDB (campgrounds, boat ramps) alongside PAD-US.
17. NOHRSC snow depth (blocked: units unconfirmed), CatFIM flood-extent maps (only about 42 percent of sites), monthly rain normals (stations missing at some gauges).

## B. User-first features
1. Flood-stage ladder graphic (stage axis with action, minor, moderate, major marks and the latest stage and forecast crest).
2. Jump links at the top of the Water tab, ordered by reader question.
3. "Cite this" and "Quote this" on each fact: copies a sentence with value, source, time and permalink (the Forbes and AI-engine use case).
4. Permalink anchors on every block and chart (ids exist; add visible link icons).
5. Per-gauge data file (`/data/<site>.json`) and long-range CSV (30 days, 1 year) with a stated licence line, for journalists and answer engines.
6. Compare two gauges side by side; saved-gauges page with live flows (Save gauge exists, no page).
7. Interactive map (pan, zoom, filter by percentile) instead of a static image; better near-me.
8. Email or push alerts when a gauge crosses a flow or stage the user picks (Workers, KV and Email Sending are available on this account); weekly river digest.
9. Search with autocomplete and recent gauges; helpful 404 with search.
10. Spanish pages later; metric units (deliberately off until every number can convert).
11. Dynamic share image per gauge with the current flow (cost grows with gauge count).
12. Last-used tab and gauge remembered (localStorage), per-user default.

## C. National and state summary pages (info gain, press value, internal links)
"Rivers above flood stage now", "Lowest flows for the date", "Biggest 24-hour rises", by state and nationally; each with Dataset structured data and a daily `dateModified`. These are the pages a journalist quotes.

## D. SEO, trust, legal
1. Search Console and Bing Webmaster verification, sitemap submission, IndexNow ping on change (needs the owner's accounts).
2. Publisher identity, contact (email routing), corrections and outage policy, changelog page (`/changelog/`) with versioned methodology.
3. Terms of use, copyright and takedown contact, accessibility statement, `security.txt`.
4. Consent messaging for EEA and UK visitors before any ad tag (Google requires a certified CMP when serving ads there), `ads.txt` after approval, ad slots that reserve space and are switched off on thin pages (ad quality gate by block count).
5. Entity and Organization schema only after a real identity exists.
6. Backlink and press plan built on section C (data stories), no link schemes.
7. Core Web Vitals field monitoring from Cloudflare Web Analytics; preconnect, lazy images, fixed image sizes.
8. Accessibility audit to WCAG 2.2 AA (chart text alternatives exist as tables; add captions, keyboard order, contrast in dark mode).

## E. Operations and resilience
1. One deployer (GitHub Actions) with the PC tasks disabled; watchdog workflow that fails on stale data, repeated shard failure or a shrinking page count.
2. Public status page (`/status/`) showing last refresh time per source (transparency, also feeds the watchdog).
3. Staging deploy to the workers.dev hostname before production; one-command rollback (`wrangler rollback`) documented for the owner; tests and render checks run in CI before deploy.
4. Tiered refresh, R2 data store, sharded matrix jobs, synthetic scale test (see plan Gate 9).
5. Politeness: identifying User-Agent with a contact URL for NWS, ETag and conditional requests, respect Retry-After; per-source rate budgets.
6. Anomaly detection on readings (flatlines, spikes, impossible values) with a hide-and-flag rule; gold-gauge regression snapshots; monthly reconciliation of our percentile against USGS statistics.
7. Security hygiene: pin Actions to commit SHAs, Dependabot, secret scanning on the public repo, token rotation reminder, DMARC and SPF for the contact address, domain auto-renew and expiry alert (registered 2026-10-16).
8. Owner runbook in plain language: what to check weekly, what each alert means, how to roll back.
9. Cost watch: Workers paid plan near 20,000 files, R2 and GitHub minutes, an alert at 80 percent of any limit.
10. Backups: data and releases recoverable (git history, R2 versions).

## F. Strategy and decisions still open
1. Recreation-weighted release order and a first cohort of 25 to 50 gauges; stop at the Search Console gates before expanding.
2. Lakes and reservoirs scope (Lakebrief's demand is lakes).
3. Hosting plan for more than 20,000 files.
4. Whether to charge for alerts or keep everything free and ad-supported.
5. Name cleaner v2 for the 1,798 held names before any wave beyond the first cohort.
