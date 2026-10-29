# PLAN: riverwaterlevels.com

## Goal
Be the most useful page for a person deciding about this river today, one page per USGS gauge. USER, NOT GOOGLE: every change is judged by that person; ranking is the result of being most useful, never the goal of a change. Reader: a person at the river today, on a phone, deciding in 30 seconds (see CLAUDE.md).

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
3. Measure readers from week 1 of scale: Cloudflare Web Analytics (free, no cookies; privacy page updated). Weekly: which pages get visits, which blocks get opened, where readers leave. Blocks nobody opens move down or into folds (river data is never deleted, owner rule).
4. Make them come back: alerts (approved: web push), favorites, add to home screen (done). Target: 10% of visitors return within 7 days.
5. Earn trust and links: outreach drafts for the owner (embed panel), "Report a wrong number" with a real contact (owner), corrections log public.
6. Information no one else has, one dataset per week: low-head dams, dam releases, stocking, advisories. Each must answer a reader question and pass the helpfulness audit.
Dated targets: 2026-11-05 sharded collect live; at 20/day: 2026-11-30 ~700 gauges; 2026-12-31 ~1,300 gauges, first 100 clicks/week; alerts live by 2026-12-31.
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

## Next steps (in order)
Done 2026-10-29: refactor (one helper per decision), all 74 pages open to Google, per-gauge review dropped, deploy confirmed live, helpfulness audit to 0 majors, offline/installable, daily release inside refresh.yml (20/day cap; practice release 40892070041: 18 added, 2 skipped for no USGS readings, refresh OK; first real release next 11:00 UTC).
1. Confirm batches F and G live; read the practice release run (20 real gauges picked, "refresh OK").
2. Sharded parallel collect (plan item 1): BUILT, ON since 2026-10-29 20:45 UTC (owner OK; undo: "sharded": false). sharded.yml (plan job, 20 collect shards, one finish job in the refresh group; a failed shard keeps its old files), switch data/pipeline.json {"sharded": false}; flip to true and push main to switch (if the plan job fails, the old single job runs). Shadow: 2,000 gauges steady state ~22 min (13 min slowest shard), WPC failures 8% -> 0%, rain 1-8% (empty answers, not fixed below 1%), truth contracts 0 failures at 2,000 (run 40941372688). Before ~500 gauges (about 2026-11-19 at 20/day; do by 2026-11-12): USGS-keyed history weekly, bulk neighbour temperature, USGS quota brake.
3. Daily release runs at the 20/day cap; watch refresh time weekly.
4. Cloudflare Web Analytics + privacy page line.
5. Alerts (web push), then favorites and units switch.
6. Outreach drafts for the owner; owner adds a contact address.
7. One new dataset per week (low-head dams first).
8. Helpfulness audit after every feature batch; Search Console + analytics read weekly into this file.
9. Owner dashboard at /ops/ (merged prompt 2026-10-29: three lights: healthy, growing, Google noticing; "you need to do" line; built by the hourly job; noindex header; unknown = "unknown").
10. First-screen answers to real searches: each top Search Console query answered on its page's first screen (e.g. what the current cfs means on this river, from agency ranges where they exist).
11. Share card: link preview image of the current-flow card; "checked against USGS at <time>" line on each page.

## Owner only
- Send the link-outreach emails (drafts provided).
- Search Console: tick Average position; request indexing for top pages if wanted.
- Domain auto-renew (expires 2027-10-16).
- GitHub dispatch token (fine-grained, Actions write, this repo) as Worker secret `GH_DISPATCH_TOKEN`.
- Cloudflare KV writes and cron count (account shared, 5 crons); Workers Paid ($5/mo) before ~1,500 gauges.
- Publisher name and contact email; consent banner and AdSense decision; outside uptime monitor.
- Source-permission visits: USACE CWMS, TVA, Recreation.gov, NID.

## Open decisions
- Regulated gauges: dam name, upstream outflow, schedule link (RISE/CWMS/NID terms unclear).
- Access points and bacteria advisories (terms / no national feed).

## Done recently
- 2026-10-29 dry run before deploy (dryrun.yml, 3035d71); water-temperature crash fix (098de3f); docs trimmed to CLAUDE.md + PLAN.md (c52b171).
- 2026-10-28 batches 1-4: staleness table, NWS low-water levels, notes, flood status, forecast wording from one rule (4e8c788, 20a0130, 56c00a6, a021144, f0ecd72).
- 2026-10-28 meta description "today's flow and water level" (ee232f5).
