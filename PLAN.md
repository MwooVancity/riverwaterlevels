# PLAN: riverwaterlevels.com

## Goal
Be the single most useful page for "<river> <place> water level", one page per USGS gauge. Reader: a person at the river today, on a phone, deciding in 30 seconds (see CLAUDE.md).

## Where we are (2026-10-28)
- Gauges live: 74 (`data/waves.csv` status=live); queue 7,499, held for names 283, excluded 1,243.
- Open to Google: `data/index-allow.json` open=true, 30 gauge URLs on the allow list plus site pages.
- Reviews: 77 signatures in `state/reviews/`: 75 PASS, 1 FAIL (11447650 Sacramento at Freeport, back in queue); `_template` PASS 2026-10-29T02:20Z, level first, template 851f24993c3b.
- Deploy: live site last confirmed built 2026-10-29T01:01Z, before batches 1-4. Deploys had failed (Node 20 vs wrangler 4.155 needing Node 22, fixed 3f3d03b; a year-1 date crashed the break gate, fixed f0ecd72). Deploy of 3f3d03b..ee232f5: status unknown (not read live).
- Search Console week 1 (owner report this session): 64 impressions, 0 clicks; 58 from Rio Grande at Albuquerque queries; top query "rio grande water level albuquerque today".
- Publisher contact: empty in `data/publisher.json` (owner waiver for wave 0).

## What works
- Truth checks against live USGS/NWS (`truth_live.py`), signed hater review gate, watchdog self-heal.
- One live-readings path (*/3 Worker cron, KV copy); visitors spend 0 USGS calls.
- USGS calls moved off retiring services (3d97e6c); collect errors recorded in source health (e1128f3).

## What does not (yet)
- Deploys broke silently twice this week; live state after the fixes is unproven.
- 0 clicks: the meta description now says "today's flow and water level, live from USGS gauge" (ee232f5); effect unknown.
- Only 30 of 74 live gauges are on the index allow list.

## Next steps (in order)
1. Confirm the deploy is live: refresh.yml green, `/status.json` built_at after ee232f5, `tools/index_live.py` 0 mismatches. Done when read live.
2. Release the next 25 gauges: `python -I tools/release.py 25`, FIRST-mode review each. Done when 99 live with PASS signatures.
3. Open released gauges to Google: `tools/open_wave.py N --apply`. Done when index_live shows them allowed, 0 mismatches.
4. Week-2 Search Console read: re-cut the release order from queries. Done when picks.csv reflects GSC queries.
5. Clutter: print each source credit once, chart key once; checks for a sentence repeated 3+ times and a dash in a hero tile (2026-10-26 plan item 3). Status unknown; done when check.py rules with fixtures exist.
6. Missing fixtures: irregular sampling for the 24 h mean, unit allowlist per field, NWS/USGS datum, ice/canal/estuary gauges. Done when `check.py --selftest` lists them.
7. CSP report-only to enforce after a live run shows no console errors. Done when the header is enforcing.
8. Scale before ~150 gauges: shard the collect run by state with per-source TTLs; before 5,000 per-gauge build; before 16,000 Workers Paid file cap. Done when a 150-gauge run finishes inside the hour.

## Owner only
- Search Console verification (and watch week 2, 30 days).
- Domain auto-renew (expires 2027-10-16).
- GitHub dispatch token (fine-grained, Actions write, this repo) as Worker secret `GH_DISPATCH_TOKEN` for the self-heal build trigger.
- Check Cloudflare KV writes and cron count (account shared, 5 crons); Workers Paid ($5/mo) before ~1,500 gauges.
- Publisher name and contact email; consent banner and AdSense decision; outside uptime monitor on /status.json and /_truth.json.
- Source-permission visits: USACE CWMS, TVA, Recreation.gov, NID.

## Open decisions
- Regulated gauges: dam name, upstream outflow, schedule link (RISE/CWMS/NID terms unclear).
- Access points and bacteria advisories held (terms / no national feed). Alerts backend (email/push on a reader's range).

## Done recently
- 2026-10-28 batch 1-2: one staleness table, NWS low-water levels, NWS notes, flood status on forecast tile, exact cfs gaps (4e8c788, 20a0130).
- 2026-10-28 forecast wording from one rule; forecast compared with one stage everywhere (56c00a6, a021144).
- 2026-10-28 batch 4: half-up stage gaps, sensor years, break gate survives year-1 dates (f0ecd72); CI on Node 22 (3f3d03b).
- 2026-10-28 meta description "today's flow and water level" (ee232f5).
- 2026-10-27 Wave 3: 21 gauges live after hater review (23e8f36); Boise live (0e324a4).
