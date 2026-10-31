# PLAN: riverwaterlevels.com

## Goal
Be the most useful page for a person deciding about this river today, one page per USGS gauge.
Scope (owner 2026-10-29: "purely the best river page there is. i want every river that exists"): rivers only, never lakes (Lakebrief has them). Target (owner 2026-10-29: "ok 9100 pages it is then"): every USGS flow gauge, data/waves.csv 9,099 rows, 25/day, no ungauged-river phase. Order: 7,498 queued (to about Aug 2027); then 283 held-names after a name fix; then 490 short-record (no percentile yet: "is this normal" says Unknown) and 546 tiny-basin; 206 excluded-name (canals, drains) stay out: not rivers. About 8,900 pages at the end. USER, NOT GOOGLE: every change is judged by that person; ranking is the result of being most useful, never the goal of a change. Reader: a person at the river today, on a phone, deciding in 30 seconds (see CLAUDE.md).

## Cheap and lazy first (HARD, owner 2026-10-29: "This the cheap lazy way? Don't we have ponytail")
Before any build or agent: does this need to exist at all? What already in the repo does it? Smallest change that works. A safety net for a failure an existing gate already blocks is not built.
- Lesson 2026-10-29: a "live verifier with auto-rollback" agent wrote 282 lines (rollback, status page, new gate) for a risk Gate 2 already blocks (built pages are checked against USGS/NWS before deploy). Stopped and reverted. Smallest real gap is the 3-minute live swap: if ever needed, `truth_live.py --live` as a report-only line in the hourly watchdog, nothing more.

## Where we are (2026-10-29 07:40 UTC, handoff)
- Live: 74 gauges, all 74 gauge pages open to Google (read live: sitemap 79 river URLs, no noindex on gauge pages). Live build 07:30 has batches A-E; F (old forecast tile age, hidden tiles named) and G (top minors) passed cloud dry runs and are pushed, deploying in order. Next session: read /status.json built_at > 07:30 and one Lees Ferry page body ("Older than 24 h" on the forecast tile) to confirm F/G live.
- Helpfulness audit loop: run 5 = 0 BLOCKER, 0 MAJOR (from 1/18 in run 1). Reports in the old session scratchpad (audit-run1..5.md); checklist tools/helpful_audit.md.
- Process that works: build batches with a cheaper-model agent from a short brief; builder looks at one phone slice and signs `_template --level=machine`; push to branch `check` (dryrun.yml, cloud data, every gate); read "refresh OK"; ONLY THEN push main in a separate step; read the live page.
- Search Console week 1: 64 impressions, 0 clicks, 58 for Rio Grande at Albuquerque.
- Owner-only now: a contact address so "Report a wrong number" reaches someone.

## What works
- Truth checks against live USGS/NWS, signed review gate (sized to the change), watchdog self-heal, dry run before deploy.
- One live-readings path (*/3 Worker cron, KV copy); visitors spend 0 USGS calls.

## What does not (yet)
- Local laptop data differs from the cloud cache: local gates passed three changes the cloud failed. Fix: every change goes through dryrun.yml (branch `check`) before main.
- 0 clicks; probably page 2 behind USGS/NOAA (position not yet seen).

## First-principles plan (owner 2026-10-29: "still isn't Elon Musk level")
Goal metric: people helped = weekly clicks from search + returning visitors (alerts, favorites). Pages are a means. Today: 74 gauges, 0 clicks/week.
The one constraint: the hourly collect fetches ~30 sources per gauge one after another; it caps the site near 150 gauges. At the owner cap of 20 gauges/day the ~9,000 named USGS gauges take ~450 days; the collect must stay fast as the count grows.

1. Kill the bottleneck (this week). Collect runs as a GitHub matrix: one job per state group in parallel (free plan allows 20 at once), each source on its own timer (readings hourly; forecasts 3-hourly; history, records, watershed, dams weekly), bulk API calls wherever the agency offers them (USGS latest-continuous for many sites per request, NWS by office). Target: a 2,000-gauge refresh in under 30 minutes. Done when a 500-gauge test run finishes inside 30 minutes with every gate green.
2. Release at the owner's cap of 20 gauges/day (a once-a-day step in refresh.yml, owner 2026-10-29), never more; ~9,000 named gauges = ~450 days at the cap. The sharded collect keeps the hourly run fast as the count grows. Brake stays: skip a day when refresh > 45 min.
3. Measure readers from week 1 of scale: Google Analytics, property "River Water Levels" in the calcscrape account, G-96RG42R07G (owner 2026-10-31, same tag as calcscrape; privacy page updated; it sets cookies, so an EU page such as the Rhine needs a consent banner or no tag). Weekly: which pages get visits, which blocks get opened, where readers leave. Blocks nobody opens move down or into folds (river data is never deleted, owner rule).
4. Make them come back: alerts (approved: web push), favorites, add to home screen (done). Target: 10% of visitors return within 7 days.
5. Earn trust and links: outreach drafts for the owner (embed panel), "Report a wrong number" with a real contact (owner), corrections log public.
6. Information no one else has, one dataset per week: low-head dams, dam releases, stocking, advisories. Each must answer a reader question and pass the helpfulness audit.
Dated targets: 2026-11-05 sharded collect live; at 25/day: 2026-11-30 ~850 gauges; 2026-12-31 ~1,600 gauges, first 100 clicks/week; alerts live by 2026-12-31.
What gets deleted to make room: per-gauge screenshot reviews (done), duplicated logic (done), any gate with no real catch in 10 runs, any doc beyond CLAUDE.md + PLAN.md, any local laptop step the cloud can do.

## Review and gate cost (owner 2026-10-29: "we've blown a million tokens")
- Spent 2026-10-28/29: about 1 million tokens, most of it on 8 full screenshot reviews (~170k each) that mostly returned notes; the deploy breaks were caught by machines.
- Rule now (CLAUDE.md "Reviews and gates: first principles"): machine checks + cloud dry run by default; max one full review a day; non-visual changes signed at level machine.
- Done: `data/index-allow.json` is out of `template_hash` (opening pages to Google needs no review signature).

## Ranking: what is missing for #1 (2026-10-29)
1. Trust and links (biggest gap): new domain, almost no links. Use the free embed panel: list fishing clubs, outfitters, paddling clubs, county and town pages per live river; Claude drafts each email, the owner sends. No spam, no paid links.
2. Position data: tick "Average position" in Search Console; work first on pages near page 1.
3. Time and clicks: first screen must end the search (level, flow, normal or not, when measured, what is coming).
4. Phone speed: run PageSpeed on the top 5 pages; fix anything failing Core Web Vitals.
5. Coverage: every new gauge adds its own river-and-town searches; release steadily.

## Helpfulness and information gain (what no other result shows)
- Already: USGS + NWS forecast + record history + low-water paddling ranges + "normal for the date" in plain words.
- Add next, each a government dataset found by WebSearch with its source row in `data/sources.json`:
  - Why the level is what it is: dam releases and irrigation diversions (Bureau of Reclamation, USACE, irrigation districts; e.g. Albuquerque autumn low flow).
  - Activity facts: state fish stocking reports, swim/E. coli advisories, boating closures, access points.
  - One line each: what changed since yesterday, what is coming in the next 24 h.
- Answer each Search Console query on the first screen (e.g. "flow rate": what 2,270 cfs means on this river).
- Delete repeated text: new information also means less repetition.

## Helpful-site gaps beyond data (owner 2026-10-29: "what else did you miss")
In order of value to a person at the river:
1. Works offline / weak signal: service worker keeps the last page and reading with its age; radar and big images load on tap.
2. Favorite rivers: star a gauge; home page shows your rivers first with current flow (browser storage, no account).
3. Safety data, never a verdict: low-head dams near the gauge (National Inventory of Dams), state life-jacket and boating rules.
4. Units switch: cfs/m3/s, ft/m, F/C.
5. Hourly conditions word + icon (NWS shortForecast), wind arrows, 7-day strip, empty states as one line, one source link per card.
6. Share card: Open Graph image of the current-flow card; add to home screen (web app manifest).
7. Plain-language "what this number means" taps; accessibility pass (contrast, text size, tap targets, labels).
8. About page a person reads (who, why, how numbers are checked, corrections, contact); "checked against USGS at <time>" on each page.
9. Search past ~150 gauges (known bug), confirm "near me" on a phone.
10. Alerts APPROVED by owner 2026-10-29: web push first (no emails stored, no outside account): reader picks a level on a gauge page, the existing */3 Worker cron compares the latest reading and sends a push (VAPID keys as Worker secrets, subscriptions in KV; watch the shared 1,000 KV writes/day). Needs item 6 (installable page) for iPhone. Email later only with an owner-opened email service. Built right after the offline batch.

## Helpfulness audit loop (owner 2026-10-29: "literally everything, down to the UI"; "think of the user not Google")
- Checklist: `tools/helpful_audit.md` (A purpose/first screen ... Q edge cases, 74 items). Judged as the person at the river, never as Google.
- Loop until clean: run ALL categories on Memphis 07032000, Boise 13206000, Scottville 04122500 + home, one state page, one river hub (text pass on the cheaper model; screenshots only for [eyes] items) -> every BLOCKER and MAJOR fixed in batches (one batch per category group, each: build, my look at one screenshot, cloud dry run, push, read live) -> re-run the audit on the fixed categories -> MINOR items listed here with a decision.
- Done when a full re-run returns 0 BLOCKER and 0 MAJOR. Status: DONE for blockers and majors. Runs: 1 = 1/18, 2 = 1/7, 3 = 0/7, 4 = 0/2, 5 = 0 BLOCKER, 0 MAJOR, 24 MINOR (2026-10-29). Batch G running on the 10 most useful MINOR items (glossary band cut-offs from code, silent-gauge rate note, rain-forecast age, 'live' title at 6 h, a 'Partial day' data bug, rain gap line, 44 px tap targets, anchor link names, report-a-wrong-number, ATTAINS). Remaining MINOR (decided: polish, after the feature work): Memphis empty columns and far-gauge padding, chart aria values, maskable icon, '168 h' wording, ramps sort. Re-run the audit after every feature batch.

## Before the Claude subscription ends (owner 2026-10-30: about 3 weeks; after that nobody changes code)
Goal: a breakage never reaches a reader, and the owner hears about failures without Claude. In order:
1. Failure email ON (owner 2026-10-30, after removing it once: "bring back the GitHub emails"): the watchdog fails its run once a day (13 UTC) only on reader-visible problems; GitHub emails the owner. Test: watchdog.yml test_alarm button (run 40991985079 failed as designed).
   Release fixed 2026-10-30: it ran only inside the 11 UTC hour and GitHub skips most hours (2026-10-29 had none), so most days released nothing; now the first run from 11 UTC that has not released today.
   Fixed 2026-10-30: a crashed gauge's live-site copy (Worker-swapped numbers beside build-time text) is now listed in _carried.json, so checks skip it (Austin 12.74 vs 12.76).
   Owner: Cloudflare free = 100,000 Worker requests/day shared with asmrregistry, reset 00:00 UTC; past it a fail-closed route shows error 1027 until midnight (developers.cloudflare.com/workers/platform/limits). Workers Paid ($5/mo) before real traffic.
2. Pinned: runners ubuntu-24.04, Python 3.12, Node 22, wrangler pinned (2026-10-30). Also fixed from the ChatGPT audit: a release that did not complete is undone before the refresh; carry limit is max(10, 5% of gauge pages) (forced bad page carried, others shipped).
3. Release stops itself when any limit is over 70% (files, cache, USGS calls); then the USGS brake.
4. DONE: no code calls the old USGS services (2026-10-30 scan: only api.waterdata / api.water / streamstats / apps hosts).
5. Compact the data cache format (687 KB per gauge).
6. Key-expiry check (USGS, AirNow, Recreation.gov, Cloudflare).
7. Remove the review-signature gate (needs a human after any code change).
8. Indexing brake: release pauses if Google stops indexing new pages (needs Search Console access, owner).
9. Owner runs /code-review ultra once, then no more code changes.

## Rhine page (owner 2026-10-31; lifts the US-only rule for this page)
Reader: English-speaking river-cruise passenger. Demand (Ahrefs, US, competitor River Cruise app, estimates): rhine river water levels today 1K, ...for cruise ships 600, rhine water levels 450, river levels in europe 60, rhine river levels 50.
One standalone page /rhine/, outside the gauge pipeline: 8-10 cruise-route gauges upstream to downstream (Basel, Mainz, Kaub, Koblenz, Koeln...), level in cm and feet, 24 h change, official low/normal/high label, reading time, source; a gauge reading is not depth; no verdict on sailing. Data: PEGELONLINE (WSV) REST API, no key, tested 2026-10-31 (Kaub 36 cm, 36 Rhine gauges, 786 in Germany). A failed fetch leaves only this page stale.
Before building: first real release proven; PEGELONLINE terms read from the WSV itself (a catalog says CC BY 4.0, unconfirmed); look at the top result. If Search Console shows visits, add Moselle, Main, German Danube from the same source.

## Factory at 9,100 gauges (5-step audit 2026-10-30, measured)
Order, each before its cliff (dates at 25/day):
1. USGS 1,000 calls/h: live readings already bulk (300 ids/call); slow history about 6 calls/gauge/day = about 2,300/h at 9,100. Brake (stop near 800/h, rest wait a run) + history weekly. Cliff about 500 gauges, 2026-11-16; do by 2026-11-10.
2. Cloud data cache: 687 KB per gauge, 610 KB of it USGS rows as verbose records (5 params x 767 rows); about 6 GB at 9,100 vs GitHub 10 GB per repo (eviction = full recollect = quota blow-up). Store [time, value] pairs. Before about 2,000 gauges.
3. NWS weather about 5 calls/gauge/hour: fetch on the page's 2 h rebuild rhythm (only what a rebuild uses). Before about 2,000 gauges.
4. GitHub 20 free parallel jobs, all taken by 20 shards: use 16 shards so watchdog and dry runs do not queue.
5. check.py and truth_live on rebuilt pages only. Before about 3,000 gauges (not measured yet).
6. Cloudflare free 20,000 files (3 per gauge): Workers Paid (owner) or one shared embed page. Before about 6,000 gauges (July 2027).
Fine at scale: build (0.1 s/gauge, rolling), release, tokens (3-page sample, 3 reads per deploy), laptop.

## Next steps (in order)
Done 2026-10-29: refactor (one helper per decision), all 74 pages open to Google, per-gauge review dropped, deploy confirmed live, helpfulness audit to 0 majors, offline/installable, daily release inside refresh.yml (20/day cap; practice release 40892070041: 18 added, 2 skipped for no USGS readings, refresh OK; first real release next 11:00 UTC).
1. Winter: ice gauges by 2026-12-01. When USGS withholds flow for ice (northern rivers, Dec-Mar), lib/hero.py ctx raises CriticalFail "no flow series" and the page freezes at the last pre-ice flow. Build a stage-only mode: gage height tiles plus "USGS withholds flow: ice". Proof: tools/break_blocks.py "ice" variant renders a page (today it is skipped).
2. State fishing and boating rules: DONE 2026-10-29 (data/state-rules.json, 100 links, WebSearch evidence, curl-checked; Ohio none: its site refuses scripted checks; watchdog checks all daily). PDFs (ID fish, MN boat) will move yearly; the link check reports it.
3. NOAA 10-day river model: the NWPS API returns an empty mediumRange for every series name (checked 2026-10-29, reach 2048241, Chattahoochee), so the 10-day line is missing on every page; the watchdog reports it. If still empty on 2026-11-29, look at the NWM medium-range bulk files instead.
4. Edge-case fixtures still missing: unit allowlist per field. Done 2026-10-29: ice, zero flow, tidal reversal and irregular sampling variants in the break gate (0 reader faults, except ice above); NWS/USGS datum in tools/truth_fixtures.py.
5. Sharded parallel collect (plan item 1): BUILT, ON since 2026-10-29 20:45 UTC (owner OK; undo: "sharded": false). sharded.yml (plan job, 20 collect shards, one finish job in the refresh group; a failed shard keeps its old files), switch data/pipeline.json {"sharded": false}; flip to true and push main to switch (if the plan job fails, the old single job runs). Shadow: 2,000 gauges steady state ~22 min (13 min slowest shard), WPC failures 8% -> 0%, rain 1-8% (empty answers, not fixed below 1%), truth contracts 0 failures at 2,000 (run 40941372688). Before ~500 gauges (about 2026-11-16 at 25/day; do by 2026-11-10): USGS-keyed history weekly, bulk neighbour temperature, USGS quota brake.
6. Daily release: steady 25/day, no ramp (owner 2026-10-29: "steady 25 a day forever"). It hits the USGS 1,000 calls/h limit near 500 gauges (about 2026-11-16): quota brake by 2026-11-10. Cloudflare free = 20,000 files (about 3 per gauge, about 6,600 gauges, about July 2027): Workers Paid before. After a deploy read status.json, _health.json and ONE page, never every page.
    Rolling rebuild BUILT 2026-10-30 (owner: "full rebuilds are not acceptable"): build.py rebuilds a gauge page only when new, code changed, NWS forecast reissued or alert set changed, flow moved over 20% in 24 h, its hourly slot (every 2 h), or over 2.5 h old; otherwise dist/ copy carried (local test: 34 carried, 8 hot, 32 slot of 74). dist/ kept in its own CI cache (rwl-pages-); dist/_built.json records each page build; watchdog flags any page over 6 h. Later at scale: check.py on rebuilt pages only, truth_live on a sample.
7. Cloudflare Web Analytics + privacy page line.
8. Alerts (web push), then favorites and units switch.
9. Outreach drafts for the owner; owner adds a contact address.
10. Government river data not yet on pages (owner 2026-10-29: "tell me all of them"). 21 sources wired, 7 off in data/sources.json, 4 never added. In order, edge case per line:
    a. Dam releases: USACE CWMS + Reclamation RISE (off: terms never read) + NID to find the dam above each gauge (off: terms unread, some fields restricted). Edge: same-river dam only, travel lag dam to gauge, public NID fields only. Fixes the "dam releases: not added yet" line now on 70 of 74 pages (also wrong on rivers with no dam). Source check running 2026-10-29.
    b. E. coli / water samples: Water Quality Portal (off: tributary samples matched by box). Fix: match by river channel via NLDI linked WQP sites. Edge: every sample shows its date, old samples never read as today.
    c. FEMA flood zone: dropped (owner 2026-10-29: "forget the flood zone thing").
    d. EPA UV index (off: point service 404; daily service by ZIP works). Edge: ZIP from lat/lon near state lines.
    e. TVA release schedules (TVA pages refuse scripted requests): maybe owner permission.
    f. NPS alerts and closures for gauges in national parks: needs a free NPS key (owner).
    g. USGS flood inundation map link where one exists for the gauge.
    Left out (reason): NOAA Atlas 14 rainfall frequency (not today's decision), WaterWatch (retired Feb 2026), Wild and Scenic designation (a label, not conditions), lock status (few navigable gauges), American Whitewater (not government; its ranges are verdicts). NOAA 10-day model: item 3.
11. Helpfulness audit after every feature batch; Search Console + analytics read weekly into this file.
12. Owner dashboard at /ops/ (merged prompt 2026-10-29: three lights: healthy, growing, Google noticing; "you need to do" line; built by the hourly job; noindex header; unknown = "unknown").
13. First-screen answers to real searches: each top Search Console query answered on its page's first screen (e.g. what the current cfs means on this river, from agency ranges where they exist).
14. Share card: link preview image of the current-flow card; "checked against USGS at <time>" line on each page.

## Owner only
- Send the link-outreach emails (drafts provided).
- Search Console: tick Average position; request indexing for top pages if wanted.
- Domain auto-renew (expires 2027-10-16).
- GitHub dispatch token (fine-grained, Actions write, this repo) as Worker secret `GH_DISPATCH_TOKEN`.
- Cloudflare KV writes and cron count (account shared, 5 crons); Workers Paid ($5/mo) before ~1,500 gauges.
- Publisher name and contact email; consent banner and AdSense decision; outside uptime monitor. The security header (CSP) stays report-only while the AdSense script is on pages: enforcing it would block the ads.
- Source-permission visits: USACE CWMS, TVA, Recreation.gov, NID.

## Open decisions
- Regulated gauges: dam name, upstream outflow, schedule link (RISE/CWMS/NID terms unclear).
- Access points and bacteria advisories (terms / no national feed).

## Done recently
- 2026-10-31 00:08 UTC deploy freeze ended (built 10:03 to 00:08, about 14 h, runs green): E. coli unit "None" failed pages, a new gauge with no earlier page blocked carry. Fixed: unit text, tools/quarantine.py with one retry per failed release, break test in dry runs only. First real release still unproven: next chance after 11:00 UTC 2026-10-31. Dry run still reports the break test nwps stale26h label on 01426500 (Forecast high + steady): open.
- 2026-10-30 01:09 UTC rolling rebuild LIVE (runs 40982333659, 40983566765, both refresh OK; pages cache restored and saved each run): live /_built.json shows 39 of 74 gauge pages rebuilt in the second run, 35 carried from the run before; Atlanta page flow 948 cfs.
- 2026-10-29 23:42 UTC live (run 40973591559, refresh OK): dam releases on 8 gauges (cloud: RISE 4/4, CWMS 4/4; Lees Ferry and Boise pages read), E. coli samples (WQP 73/74), UV row (EPA 502 on 20 of 38, retried hourly), "not added yet" line gone (0 on pages read). Inundation link skipped: USGS publishes no site list.
- 2026-10-29 evening: sharded collect ON (first run 40951494012: 20 of 20 shards, refresh OK, live built 21:06, 74 gauges, 0 failed); daily outside-link check in the watchdog found alerts.weather.gov dead (link removed, live read: 0 hits); watchdog health rules fixed (12 false "not working" lines down to real ones); docs/OPEN-ITEMS.md folded into this file.
- 2026-10-29 dry run before deploy (dryrun.yml, 3035d71); water-temperature crash fix (098de3f); docs trimmed to CLAUDE.md + PLAN.md (c52b171).
- 2026-10-28 batches 1-4: staleness table, NWS low-water levels, notes, flood status, forecast wording from one rule (4e8c788, 20a0130, 56c00a6, a021144, f0ecd72).
- 2026-10-28 meta description "today's flow and water level" (ee232f5).
