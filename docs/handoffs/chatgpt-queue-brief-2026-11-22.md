# Brief for ChatGPT: how to order and finish a 14,000-page water-level site queue for maximum money (2026-11-22)

## Objective, first and above everything
The only goal is to earn as much AdSense and other ad money as possible, as soon as possible, inside truth and Google's rules (a penalised site earns $0). Judge every answer by that first.

## The site
riverwaterlevels.com. One static page per water gauge (rivers, lakes, reservoirs, coast tide stations), official agency data (USGS, NOAA CO-OPS, state and national agencies), English, built in Python, hosted on Cloudflare, public GitHub repo. Reader: a swimmer, kayaker, angler or boater going out today, on a phone, 30 seconds. About 570 pages inspected by Google, 417 indexed. Traffic is tiny: about 35 Google clicks and 4,130 impressions in 28 days. AdSense is NOT approved yet (re-apply planned about 2026-11-26), so revenue is $0 today.

## The release rule
25 new pages per day in total (a Google-trust cap). A daily job (`tools/release.py N`) picks the next N queued gauges, builds pages, and they enter Google through a separate step. Owner instruction today: "the top 25 keywords done a day", pure Keyword Planner order, "Keyword Planner is the only thing that matters", "no river, lake or ocean missing".

## How the queue is ordered now (pushed 2026-11-22)
Money = Keyword Planner search band of the water's keyword x ad rate (the keyword's own top-of-page bid divided by the median bid, else a country guess). Bands in the data are 0 / 50 / 500 / 5,000 / 50,000 searches a month (Google rounds). The first gauge on a keyword gets its whole band, later gauges on the same keyword get 5%. A held gauge never takes the full band. No forced lake slots, no jump-ahead for thin state pages.
Data: `data/keyword-tiers-water.csv` (52,637 keywords, 28,416 are lakes; columns keyword, tier, bid_high_cad), `data/world-queue.csv` (20,000 rows: rank, group, tier, keyword, river, place, region, country, gauge, shared, feed, ready), `data/waves.csv` (7,660 queued rows).

## Numbers measured today
- Queued US lakes: 402. By Keyword Planner band of their name: 2 at 5,000, 86 at 500, 149 at 50, 151 at 0, 14 with no Keyword Planner row at all. Lake head terms are about 50,000 searches a month in total against about 500 for a typical river.
- Queued non-lake rows: 7,258. In `world-queue.csv`: 1,670 have a keyword and tier (8 at 5,000, 288 at 500, 1,374 at 50); 5,542 have NO keyword (sort at 0); 46 are not in the file.
- Tomorrow's top 25 (dry run): Cedar Creek Reservoir TX and Lake Fork Reservoir TX (5,000), then river flow keywords at 500 (Yampa, Muskegon, Bitterroot, Weber, Wenatchee, Payette, Neches, Willamette, Methow and others), then 500-band lakes (Salton Sea, Flathead, Clear Lake CA, Lake Ray Hubbard, Toledo Bend and others). Only 25 of 402 lakes can go per day.
- Revenue guess: about 200,000 pageviews a month needed for $1,000 a month at an assumed $5 per 1,000 pageviews; my own timeline guess is late 2027 to mid 2028.

## Known gaps in the queue (please attack these)
1. 5,542 river rows have no keyword match. Matching by river name alone is unsafe: "Fall River" (KS) took the 5,000 band of Fall River MA, "Cedar Creek" took a lake's band, "Lake Fork" (a CO creek) took Lake Fork Reservoir TX's. Keyword Planner rows carry no state. How do we match state-aware, cheaply, with no paid API?
2. 14 queued lakes have no Keyword Planner row. Is there a better way than running Google Ads Keyword Planner by hand in Chrome?
3. Same-name lakes in different states share one band (Bridgeport Reservoir CA and TX, Wilson Lake KS vs AL, Lake Worth TX vs FL, Detroit Lake OR). 22 same-name groups with far-apart gauges are held.
4. A lake ranked by name never uses its own keyword's ad bid (always median rate). Today no matched lake keyword has a bid, so nothing changes yet.
5. 149 queued lakes are band 0 (Google shows no volume). When the 25 a day reach them, the order inside the band is arbitrary (Wikipedia page views break ties). Better tiebreaker?
6. USGS API 429 errors: the key quota is shared between the lake matching runs and the live data collect. Is a second key or an off-peak schedule the right fix?

## Questions I want answered, ranked by money
A. Is a strict Keyword Planner order the best way to spend 25 pages a day for revenue, or should some days mix in pages most likely to get indexed fast, or pages near already-ranking pages (topical authority), given Google indexed only 417 of 572 inspected pages and the site is tiny and new?
B. Should the cap stay 25 a day or rise? Evidence needed: what do new-site crawl and index rates look like for programmatic data pages, and what signals tell us the site can take 50?
C. What is the cheapest reliable way to get Search Console query data on long-tail lake questions (8+ word queries, question-start queries) to decide what each page must answer? (I plan a Search Console regex pull about 2026-12-10.)
D. How do I tell, within two weeks of the first 25 lake pages, whether the lake bet is working (which metric, which threshold) before pouring all 402 lakes in?
E. AdSense approval: what on a data-only utility site most often causes "low value content" rejection, and what should be fixed first before about 2026-11-26?
F. Anything in the queue logic above that is wrong, double counted or a hidden trap at 14,000 pages.

## Rules I must keep (do not suggest breaking them)
Truth first: every number comes from an official agency feed with unit, time and source; unknown beats false. No verdict words like "safe" or "fishable". No cloaking. Google helpful-content rules: no doorway pages, no padding, no links just for a count. One page per gauge needs something of its own (name and distance, nearby waters, weather point, access). Never a source whose terms bar ads or caching. Free Cloudflare limits: 5 crons, 1,000 KV writes a day, 20,000 files.

## How to answer
Open with the answer in one line. Then the top three actions by money with the exact test that would prove each worked. Mark every guess as a guess and every fact you are unsure of as unverified. If an answer relies on Google behaviour, say how sure you are and what a source would be. No flattery: tell me what is wrong with the plan above first.
