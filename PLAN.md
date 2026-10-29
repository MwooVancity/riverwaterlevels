# PLAN: riverwaterlevels.com

## Goal
Be the #1 and genuinely most useful page for "<river> <place> water level / flow / today", one page per USGS gauge. Reader: a person at the river today, on a phone, deciding in 30 seconds (see CLAUDE.md).

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

## Next steps (in order)
1. Finish the refactor: Part A byte-identical, Part B diff read, one review of the changed pages, dry run, push. Done when read live.
2. Open all 74 gauge pages: `python -I tools/open_wave.py 74 --apply` in the same push; sitemap + IndexNow; `python -I tools/index_live.py` 0 mismatches. Done when index_live shows 74 allowed.
3. Confirm deploy live: `/status.json` built_at after the push, one page body read.
4. Release the next 25 gauges: `python -I tools/release.py 25`, FIRST-mode review each, open them. Done when 99 live with PASS.
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
