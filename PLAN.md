# PLAN: riverwaterlevels.com

## Goal
Be the most useful page for a person deciding about this river today, one page per USGS gauge. USER, NOT GOOGLE: every change is judged by that person; ranking is the result of being most useful, never the goal of a change. Reader: a person at the river today, on a phone, deciding in 30 seconds (see CLAUDE.md).

## Where we are (2026-10-29)
- Gauges live: 74 (`data/waves.csv` status=live); queue 7,499, held for names 283, excluded 1,243.
- Open to Google: `data/index-allow.json` open=true, site pages open, 30 of 74 gauge URLs allowed (owner 2026-10-29: open all).
- Reviews: `_template` signed on every pushed code change; 11447650 Sacramento at Freeport FAIL, back in queue.
- Deploy: live site last confirmed built 2026-10-29T01:01Z. Later pushes failed in CI (Node 20 vs wrangler, year-1 date in break gate, water-temperature years as ints); each fixed (3f3d03b, f0ecd72, 098de3f). Dry run on cloud data passed 2026-10-29 (dryrun.yml, "refresh OK"). Live state after 098de3f: not read yet.
- Search Console week 1: 64 impressions, 0 clicks; 58 from Rio Grande at Albuquerque queries; top query "rio grande water level albuquerque today". No average position recorded yet.
- In progress: refactor, one helper per reader-facing decision (18 decisions were computed in 2-4 places, 12 disagreed). Part A must leave pages byte-identical; Part B changes listed page by page.

## What works
- Truth checks against live USGS/NWS, signed review gate (sized to the change), watchdog self-heal, dry run before deploy.
- One live-readings path (*/3 Worker cron, KV copy); visitors spend 0 USGS calls.

## What does not (yet)
- Local laptop data differs from the cloud cache: local gates passed three changes the cloud failed. Fix: every change goes through dryrun.yml (branch `check`) before main.
- 0 clicks; probably page 2 behind USGS/NOAA (position not yet seen).

## First-principles pass on the whole project (owner 2026-10-29: "elon musk it to #1")
The one requirement: the page a person at this river wants, for every river people search. Ranking comes from coverage (pages x searches), trust (links) and clicks that end the search. Everything else is questioned.
1. Question: per-gauge screenshot review (~80k tokens each, 25 gauges = ~2M) caps coverage. Machine gates already check every page against live USGS/NWS; the shared template is reviewed once. DECISION: new gauges ship on machine gates (check.py, truth_live, break gate, cloud dry run); a light review only for a gauge with a data shape no reviewed page has. Replaces the 2026-10-27 "every gauge needs a signed PASS" rule.
2. Delete: gates/checks with no real catch in 10 runs; duplicate logic (refactor done 2026-10-29); docs beyond CLAUDE.md + PLAN.md (done); per-gauge review signatures as a deploy requirement.
3. Simplify: one decision = one function; one deploy path (refresh.yml) with one practice path (dryrun.yml).
4. Accelerate: release waves of 25-50 gauges every day the cloud run stays under the hour (owner rule stands: never ~1,000 at once); open each wave to Google the same day; IndexNow on every wave.
5. Automate last: the hourly run releases and opens the next wave by itself when every gate passed for 24 h; Search Console and PageSpeed numbers read by script weekly into this file.
Ranking work in parallel: link outreach drafts (owner sends), first-screen answers for each top query, phone speed.

## Review and gate cost (owner 2026-10-29: "we've blown a million tokens")
- Spent 2026-10-28/29: about 1 million tokens, most of it on 8 full screenshot reviews (~170k each) that mostly returned notes; the deploy breaks were caught by machines.
- Rule now (CLAUDE.md "Reviews and gates: first principles"): machine checks + cloud dry run by default; max one full review a day; non-visual changes signed at level machine.
- To do: take `data/index-allow.json` out of `template_hash` (robots tags only; `tools/index_live.py` checks them), so opening pages to Google never needs a review signature. List gates with no real catch in their last 10 runs and delete them.

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
1. Finish the refactor: Part A byte-identical, Part B diff read, one review of the changed pages, dry run, push. Done when read live.
2. Open all 74 gauge pages: `python -I tools/open_wave.py 74 --apply` in the same push; sitemap + IndexNow; `python -I tools/index_live.py` 0 mismatches. Done when index_live shows 74 allowed.
3. Confirm deploy live: `/status.json` built_at after the push, one page body read.
4. Drop per-gauge review as a deploy requirement (`check.py` `review_gaps`: live gauges need no signature; `_template` still does; a FAIL still pulls a gauge) and take `data/index-allow.json` out of `template_hash`. Done when selftest proves both.
4b. Release 50 gauges: `python -I tools/release.py 50`, machine gates + dry run, open them same day. Done when 124 live and index_live shows them allowed.
5. Link outreach list (5 rivers with most impressions first) with drafted emails for the owner. Done when the owner has the drafts.
6. PageSpeed on top 5 pages. Done when all pass or fixes are pushed.
7. Datasets for information gain, one per batch: dam releases / diversions first (Albuquerque), then stocking reports, then advisories.
8. Week-2 Search Console read (with position): re-cut release order and first-screen answers from queries.
9. Clutter checks: source credit once, chart key once, a sentence repeated 3+ times. Status unknown; done when check.py rules with fixtures exist.
10. Scale before ~150 gauges: shard collect by state with per-source TTLs. Done when a 150-gauge run finishes inside the hour.

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
- Access points and bacteria advisories (terms / no national feed). Alerts backend (email/push on a reader's range).

## Done recently
- 2026-10-29 dry run before deploy (dryrun.yml, 3035d71); water-temperature crash fix (098de3f); docs trimmed to CLAUDE.md + PLAN.md (c52b171).
- 2026-10-28 batches 1-4: staleness table, NWS low-water levels, notes, flood status, forecast wording from one rule (4e8c788, 20a0130, 56c00a6, a021144, f0ecd72).
- 2026-10-28 meta description "today's flow and water level" (ee232f5).
