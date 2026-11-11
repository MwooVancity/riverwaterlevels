# PLAN: riverwaterlevels.com

History (dated batch logs, audits, debates, research, old step lists): `docs/plan-history.md`. Rules: `CLAUDE.md`.

## Goal
The most useful page for a person deciding about this river today, anywhere (reader: CLAUDE.md). Objective: AdSense earnings from people helped.
Scarce resource: Claude time. From 2026-11-20 the owner moves from Max to Pro (owner 2026-11-03): sessions continue but far fewer, so growth slows, never stops; everything must run alone between sessions, and the costly builds (world release, limits) belong before Nov 20.
Bottleneck: AdSense approval, then readers. Earns $0 until approved; calcscrape and asmrregistry were rejected as low value content, so approval outranks page count.

## Revenue goal (owner 2026-11-10): $1,500 a month by 2027-11-10
Math (assumptions marked): $1,500 / page RPM $5-10 (ASSUMED until AdSense reports ours) = 150,000-300,000 page views a month. Measured 2026-11-10: ~200 sessions a month (ChatGPT 112, direct 60, Google 18), 241 gauge pages, Google position 13.1, 21 clicks in 28 days, AdSense 'Getting ready' (earns $0).
Pages: 25 a day by the release = about 9,000 more by 2027-11. Each needs about 20-30 views a month (today under 1): ranking, not page count, decides it.
Checkpoints (read monthly with tools/gsc_read.py; miss one = the next session works only the lever behind it):
| Date | Pages | Views/month | Google clicks/month | Lever if missed |
| 2027-01-10 | ~1,800 | 8,000 | 2,000 | AdSense approved? indexing (index_inspect) |
| 2027-04-10 | ~4,000 | 40,000 | 12,000 | position: page-two pages vs top results, links |
| 2027-07-10 | ~6,300 | 100,000 | 35,000 | CTR on pages at position 1-5 |
| 2027-11-10 | ~9,000 | 200,000 | 70,000 | RPM: measure; more lakes and coasts (higher searches) |
Order of levers: (1) AdSense approval (needs the contact address: owner's Cloudflare click) (2) indexing (daily Request-indexing job, IndexNow) (3) rank from page two to top five (three tests: better than #1; earned links: outreach, embed) (4) volume (release 25/day, biggest searches first) (5) ChatGPT/Bing (largest source today).

## Reader
A person at or near this water today, on a phone, with 30 seconds (full text: CLAUDE.md "Reader"). One page per place people search for, even when it shows the same feed or gauge as another page (owner 2026-11-08).

## Done 2026-11-10 to 11-11 (full audit, Superpowers review, PLAN crush; all on `check`, every self-test passing; proof lines below say what was read live)
- Deploys: the site froze 4 h on 11-10 (truth_tests crash, carried noindex, -0.0, Dublin Port); fixed, LIVE 15:04 UTC. Release steps (reindex, IndexNow, Search Console resubmit) moved into the sharded job that runs. One bad new page now holds only itself, never the whole day's release (check.py attribute).
- Readers: coast pages show NWS marine-zone warnings (LIVE: Astoria gale + hazardous seas, PZZ210); dam-release rivers no longer called tidal (LIVE: Cowlitz); last year's same date; USGS lake storage 72036; flood stages also on the USGS scale; one plain status sentence on the first screen (LIVE: Baxley); lake full pool and water-temperature Unknown with reason; BfG estimates labelled; next tide moves forward; rain stations in words (LIVE: San Diego); open public land first; lake wording (no "storage readings" without storage, shore not river access).
- Every page its own: river hubs (summary, 7-day chart of every gauge, forecast crests, access along the river, lag between gauges), state hubs (furthest above/below normal, fastest movers, forecasts, alerts at gauges), world hubs (gauges by river km, level chart, warnings, BfG forecast highs); dam facts from the USACE National Inventory of Dams; Recreation.gov fee, reservations, address, phone; lake past years in the lake's own elevation code; repeated method notes moved once to /methodology/; .json data files sent noindex.
- Truth checks: clock text vs reading time, 30-min DST and 10-min future tolerances, US future readings held at build and in the Worker, unreadable world page = fault, near-flat stuck sensor, terms stated for every shown source (16 unread read: 9 allowed, AirNow cache only, 5 still unread), secret scan covers every key, no link to a noindexed page, own-data census and gate-catch census every run, Search Console access and contact-mail MX checked by the watchdog.
- Machinery: check.py and truth_live check only pages rebuilt this run; Worker reads one gauge's row and goes national past 1,500 gauges; Worker observability; NWS observations on the 2 h rebuild slot; 16 shards; PEGELONLINE bulk current reading; travel time weekly (USGS key limit ~1,000 -> ~1,580); one release path; data-cache-lost and load-guard alarms that can fire; owner dashboard in the watchdog Summary (repo is public: no secrets on it).
- Code: check.py importable (self-test runs once), one carry rule, one km()/merc(), cadence in lib/cadence.py, ~520 dead lines deleted, PLAN 74 KB -> this, CLAUDE.md 12.5 -> 9.9 KB.
- Google: Search Console validation restarted 2026-11-11 for the 308 noindex-era pages (owner asked); reindex queue in inspection order; index_inspect parallel in daily slices; Ireland rate fixed; Keyword Planner bids rank the queue.
- Speed 2026-11-11 (Lighthouse mobile, cloud): Lake Lanier 89, Rhine Kaub 90, San Diego coast 89, CLS 0 on all three.

## Black-hat review 2026-11-11 (tools/blackhat_review.md; verdict: not a spam site, no cloaking, lastmod honest)
- DONE (commit a8b91de, on check): embed credit line optional, "River Water Levels" + nofollow (Google names keyword links in widgets as link spam); Clearwater data.json and Dataset name the measuring station 8726724; coast series key `water_level_7d`; dam estimate names the National Inventory of Dams; "L&D", "The Dalles" casing; home world anchors plain; gauge air temperature labelled apart from the weather tile; hub titles say their gauge count. Also: Lake Michigan lake-great PASS; world hubs' source line and "None in force" (6 hubs were carried as old copies).
- Found by the way: the short coast title (audit #27) dropped H1 words, break_blocks failed, and no check run promoted to main all day (27 commits) while every run showed green. Title fixed; the owner dashboard now shows "Code changes waiting to go live" with the stop lines.
- Deploy gate (owner "improve it"): tools/deploy_gate.py, a project Stop hook, blocks a session from stopping while check has code main lacks and the newest finished check run failed or hit a merge conflict, quoting its stop lines (self-test passes).
- KEEP: sitemap lastmod moves with weather text (honest: the page did change).
- Outreach: hold until the nofollow embed is LIVE (it is what the emails offer).

## Next steps
1. LIVE 2026-11-11 (build 166f348, 16:54 UTC; read: Clearwater data.json water_level_station NOAA 8726724, titles "San Diego tides: tide times and water level, water temperature, CA", /embed/ credit optional + nofollow, Rhine "10 gauges" + "No DWD weather warning in force", "Claiborne L&D"; check had conflicted with main, merged by hand): Read the next check run: "refresh OK" and promotion to main; then the live Clearwater data.json (`water_level_station`), a coast title, /embed/.
   Edge cases: break_blocks fails on another coast title (test: rank_checks on San Diego and Clearwater titles, run in session, passes); a tide-table page title (swap turns "water level" into "tide table": rank_checks accepts it).
2. DONE 2026-11-11 (live re-measure, 10 random river pages: 88 shared sentences / 6,927 chars -> 82 / 6,061; the rest are required credits, source lines, safety lines and chart legends; on check: depth note once, credits once, key-facts filler cut; the hourly, rate and windows notes already moved): Boilerplate (black-hat #5): 95 sentences identical on every river page. Move each method or source note that repeats on every page to /methodology/ once, keep one link and the gauge's own sentences. Delete, never reword.
   Edge cases: a note carrying this gauge's number or time looks generic but is not (test: masked-number diff of 10 live pages lists only fully identical sentences); a safety line (not for navigation, provisional data) must stay on the page (stays: the disclaimer rule); check.py source-line rule still met per block.
3. LIVE 2026-11-11 (tides block before stage_chart on /coast/clearwater/): Clearwater (black-hat #3): its first screen leads with its own tide predictions (8726706), the borrowed level labelled as the Beach gauge with a link.
   Edge cases: every coast with a borrowed level, not only Clearwater (test: pages where `level_of(G)` is set); a doorway census pair stays flagged until it differs.
4. WAITING 2026-11-18: lake past years live, then the lake phone review.
5. OWNER: the clicks under Owner only (Email Routing, Cloudflare token, outreach, 5-second test). Black-hat #7: no named operator or contact is the site's largest rater gap; the contact page waits on Email Routing.
Reader tools from the 2026-11-03 gap research (never folded in until 2026-11-11; ranked by "changes a decision in 30 seconds"; Helpful: answers the reader's next question / Gain: competitors lack it or bury it / HCU: official data, no verdict):
6. DONE 2026-11-11 (on check; tested: node stub tap shows "5.00 ft, Nov 9, 6:00 PM CST", forecast marked, page still scrolls; check.py selftest guards the points): Tap a chart for the value and time (gauge charts: flow, gage height, lake level, tide). Pure page code, no new source.
   Edge cases: a tap between two readings shows the nearest real reading, never an interpolated one (test: fixture with a 6 h gap); a held or suspect reading is not read out as current; no layout shift (CLS 0 stays: speed run); works with the Worker's live number swap (the newest point included); screen readers keep the table under the chart.
7. DONE 2026-11-11 (code + 12 hand-checked rows on 6 gauges: Merced Pohono, Potomac Little Falls, Comal, Guadalupe New Braunfels, James Richmond, Chattahoochee Atlanta; Youghiogheny row dropped: rule gauge on another stretch; 25 gauges checked with none; news-only leads not used. Phone review of the new block: cloud run on 11266500 + 08169000): Agency-published activity limits and closures, quoted with source and date ("Boulder County: tubing closed above 700 cfs"), only where an agency publishes one for that reach.
   Edge cases: an expired or seasonal limit shown as current (store the agency's date and season; past it = hidden); a limit in another unit or gauge (state the agency's gauge; show only when it is this gauge); our words replacing the agency's (quote only, BANNED verdict words still fail); one county's rule shown on a neighbour county's page.
8. DONE 2026-11-11 (research: only Texas has a current machine feed, and its terms say "personal use" and bar reproduction without approval (owner decision 7: link out); FL status is HTML only, CA open file newest advisory 2026-03-06, NJ and HI internal app routes with unread terms, EPA BEACON is yearly. Built: each coast page in TX, FL, NJ, WA, HI links its state swim-advisory program; SC, VA, MA, ME, OR, AK, CA not yet found: recheck at the next full audit): Official bathing-water status (EU bathing water directive sites in Germany/England/Ireland; US state beach advisories where a feed exists), not only samples.
   Edge cases: an advisory from last season shown as today's (status date shown; out of season says so); a beach 10 km away shown as this river's (distance shown, same water only); a feed down = Unknown, never "open".
9. DONE 2026-11-11 (11 live pages at a dam; operators publish monthly plans, no schedule feed. Read live: Glen Canyon page has current monthly volumes (updated 2026-10-15), linked from Lake Powell; Yellowtail newest plan Jan 2023 (stale, not linked); Canyon Ferry PDF unreadable (not linked). Recheck yearly): Upcoming dam release schedules where the operator publishes them (TVA, USACE, Reclamation), labelled as the operator's plan.
   Edge cases: a schedule changed after we fetched it (fetched time shown; "plans change" stated by the operator's words); a release for a different dam on the same river; time zone of the operator vs the gauge.

## Waiting (nothing to do before the date)
- 2026-11-18: lake past-years block appears as the weekly fetch reaches each lake; read /lake/lake-lanier/, then one phone review of the lake variant.
- 2026-11-25: Search Console validation result for the noindex-era pages.
- 2026-12-06: refresh run time alarm projected near 1,011 pages (ledger); build "only what changed" for the next stage then.
- 2026-12-07: Rio Grande at Albuquerque title test (clicks and CTR vs the 28 days before).
- 2026-12-11: Search Console Links (referring domains) after outreach.
- 2026-12-21: tide-table pages, impressions after 6 weeks; a page with none is improved or pulled.
- Terms still unread (no official text found): stocking (Montana says "personal or informational use"), cwms (USACE copyright page blocks bots), acis, airnow (ads/commercial), ncwsa, wqp. Read in a browser; if any bars ads, hide its block.
- Code review leftovers (low): tide test runs on inland gauges (efficiency); hub status words duplicate the gauge page's helper; a page carried from before the live-line placeholder shows no 'updated' note until it rebuilds.

## Limits (dates at 25 a day)
1. USGS 1,000 calls/h: history weekly in 168 slots, 325 calls/h at 9,100; a 429 stops history for that run.
2. Data cache: 16 MB at 97 gauges, about 1.5 GB at 9,100. GitHub evicts oldest; no pause rule.
3. DONE 2026-11-11: NWS observations on the 2 h rebuild slot (alerts hourly); about 2.5 calls a gauge an hour.
4. DONE 2026-11-11: 16 shards.
5. DONE 2026-11-11: check.py page rules and truth_live --dir on rebuilt pages only.
6. Cloudflare 20,000 files, 3 per gauge: Workers Paid (100,000) or one shared embed page. Before 6,000, about July 2027. 14,000 gauges is 42,000 files.
7. Release pauses over 70% of plan files, a refresh over 45 min, or 10 Worker stops a day on the free plan; each holds growth, never a page.
8. World Worker refresh: station names in one URL break near 150 gauges; a whole-feed reply (786 stations, about 650 KB) risks the 10 ms CPU. Before 150: per-feed copies from the hourly build, or Workers Paid. Each country adds one feed call per poll.
9. PARTLY DONE 2026-11-11: world feeds spread across shards, PEGELONLINE bulk current reading; the 8-day history is still one call per station (about 6,000 an hour at 6,000 world gauges); split the station list near 500 stations on one page.
10. KV: USGS at most 480 writes a day plus world 96, of 1,000 shared.
11. `_redirects`: rules after the first dynamic one count against 100; single-gauge forwards live in `single-rivers.json` plus the Worker. Link budgets: home 300, state 700.
12. NOAA CO-OPS: 4 calls per coast per hour, no published limit (300 coasts = 28,800 a day): watch 429s. RISE and CDEC publish no limit.

## Owner only
- Request-indexing job stalled since 2026-11-09 (runs 11-10 and 11-11 "succeeded" but requested 0: Chrome asked for site permission and nobody answered): in Chrome, open the Claude extension, allow search.google.com once ("Always allow"). The 9:28 job then runs alone.
- Links (drawing board 5, 0 sent until now): 40 emails ready in docs/outreach-emails.md, one per organization for the 13 live lake pages, each offering the free embed panel. Send after Email Routing is on (so they can reply to a site address); tell Claude which went and it dates them in data/outreach.csv. Proof: referring domains in Search Console Links, read 2026-12-11.
- Owner alone decides: publisher name and contact email; pages opened to Google beyond the daily 25; ads and consent; Search Console; source keys; domain renewal; Cloudflare plan; outside uptime monitor; cutting any block.
- Workers Paid ($5/mo), then GitHub variable `WORKERS_PAID`=1: 100,000 files; free is 100,000 requests a day shared, past it error 1027 until midnight UTC. Needed before ~5,300 gauges.
- Publisher name and contact address; `data/publisher.json` email is empty.
- AdSense: turn on consent mode in Privacy & messaging (flags are off by default); add a contact email, then build `/contact/` and link it in the footer.
- AdSense decision. CSP stays report-only while ads are on pages.
- Free sign-ups: SEPA registration, OPW courtesy email (with our server IPs, before Irish river pages), NRW key (Wales 1-year storage limit: default accept, keep 12 months). Later keys: Norway NVE, NZ Canterbury.
- Read the USACE disclaimer in a browser (bot-blocked; CWMS pools wait on it).
- Outside uptime monitor; GitHub Actions failure-email setting; a running Keyword Planner campaign for exact monthly volumes.
- Decide: a daily scheduled Claude routine that reads GitHub failures and the watchdog report and fixes code (costs tokens daily).
- Replace the Google robot key `livedatacalc-automation` (printed in chat 2026-10-31); old key starts 73f0baf9.
- Confirm a phone visit in Analytics Realtime (owner's Chrome blocks the tag). Confirm the test alarm email arrived.
- Delete `river-pipeline-for-chatgpt.zip` from the Desktop.
- 5-second test (owner 2026-11-09 readable-at-a-glance rule): show one river page on a phone to someone who is not Claude for 5 seconds; they say what the river is doing. Tell Claude what they said.
- Contact address (Cloudflare Email Routing): Cloudflare dashboard > riverwaterlevels.com > Email > Email Routing > Get started > add the custom address `contact` (contact@riverwaterlevels.com) forwarding to your own inbox > Add records. If the address is already there, open Email Routing > Settings > "Add missing records". Your inbox address is never written in this repo. Then Claude sets data/publisher.json email to contact@riverwaterlevels.com.
- Cloudflare API token (the Cloudflare load guard, tools/worker_load.py, is blind without it: audit #32): Cloudflare dashboard > My Profile > API Tokens > Edit the token used as CLOUDFLARE_API_TOKEN > Add more > Account > Account Analytics > Read > Continue to summary > Update token (Save).
- Send the outreach notes in data/outreach.csv.
- Search Console > Settings > Users and permissions > velocity-engine@asmr-directory-497009.iam.gserviceaccount.com > three dots > Change permissions > Full > Save (Claude's click was blocked: it grants a permission).
- Outreach emails; domain renews 2027-10-16; source-permission visits (USACE, TVA, Recreation.gov, NID).
