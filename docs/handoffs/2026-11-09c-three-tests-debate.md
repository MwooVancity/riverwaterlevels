# Handoff 2026-11-09c (updated late 11-09): next session starts here

How sessions work now (fresh review "why do you keep stopping", applied 11-09):
- Batch finished items into ONE push to `check`, then keep working. A passing dryrun ("refresh OK") promotes itself to main and starts refresh.yml (dryrun.yml promote step; first run of it = the push of commit "Stop stopping"; confirm in its log: "promoted <sha> to main; refresh started"). A conflict with main is left for the session to merge.
- Gate runs are per commit now (no cancelling an earlier push).
- PLAN.md markers: DONE, LIVE, CLOSED, DECIDED, WAITING <date>, OWNER. The Stop hook (~/.claude/hooks/plan-gate.mjs) pushes a stop back to work once while any other item is open; a reply containing HANDOFF passes.

Owner orders (CLAUDE.md): three tests above all (Helpful / Gain / HCU line per change); no forced internal links (60 mi / 100 km, no reverse lists); edge cases written into each plan item.

Done today and live (gate refresh OK, index_live 0 mismatches, pages read): first-screen rule; plain normal-tile line; US future-time drop; coast alerts heading; rate windows merged; last-year label; depth caveat; reverse links deleted; IndexNow (361 sent, release pings new pages); doorway census (285 pages, 0 pairs); Lake Mead storage 6,947,000 acre-ft (Reclamation table, own date); world address clash guard; session-start line with release age.
Pushed, verify live: Albuquerque title test ("water level and flow today", read clicks 2026-12-07); the promote step.
Owner's Chrome 11-09: Request indexing for /rivers/ca co az mt mo ky ga id, /about/, /methodology/ (Google confirmed); Bing sitemap resubmitted (Bing: 0 impressions so far). Service account -> Full was blocked (permission grant): owner.

Open (PLAN Next steps, 2 items):
- 9a USACE full pool BUILT (Lanier, Hartwell, Allatoona, Barren; block 'How full the lake is'); phone review dispatched as dryrun run 42748521697 (review="02334400 02187010"): download artifact 'review', read the shots, mark the block reviewed or fix. The push run promotes to main by itself, so the block may already be live: read /lake/lake-lanier/ for 'below full pool today'.
- 7 Ireland: readers done (Kinsale predictions fetch_imi_hilo; live network fetch_imi_live, 22 gauges). Next 7c-2: Irish live tide page kind (reading vs IMI prediction, Europe/Dublin, m + ft, warnings Unknown + met.ie like England, Official links Marine Institute), build via a small dedicated builder or the world generator, check.py rules, truth check vs ERDDAP, then 7d phone review. Met Eireann warnings feed https://www.met.ie/Open_Data/json/warning_IRELAND.json returned [] on 11-09 (prove on the first real warning).
Daily scheduled task 'river-request-indexing' (9:28 local) works data/reindex-queue.txt (88 URLs); first run 11-10: check data/reindex-log.txt.
WAITING: 0h next 10 Request-indexing clicks 2026-11-10 (81 left); 0l tide-table check 2026-12-21; 0 first tide-table page; 14 scale items.

Owner only: Search Console service account Restricted -> Full; Cloudflare Email Routing "Add missing records" (no MX yet); outreach notes; 5-second test.
