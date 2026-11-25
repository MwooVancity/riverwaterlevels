I am a solo site owner who does not code; an AI assistant writes all the code. I need you to debate and improve a build plan, and to tell me where it is wrong. Please argue, do not just agree.

WHAT I AM REALLY ASKING: Last time you gave me a recovery order after Google took away about 95% of my site's search impressions. I told the assistant "run a workflow that builds what ChatGPT wants, in order". The assistant has now written a plan for that automated multi-agent build. Is the plan right, what is the correct order and shape, and what should not be built?

MY EXACT WORDS (verbatim): "Traffic going up coz Google officially killed our site?" / "Nov19 tanked" / "Strange because that means api sites are cooked" / "Plan how to build it all as we grow" / "K workflow what chatgpt wants in order" / "Debate a planmd for that workflow".

GOAL (top rule): earn as much ad money as possible, inside truth and Google's rules (a penalised site earns $0). Every page must pass three tests: helpful to a swimmer/kayaker/angler/boater checking a lake or river on a phone in 30 seconds; information gain over what already ranks; Google helpful-content review.

FACTS (measured, with source):
- Site: static pages, one per US stream gauge or lake, official US agency data (USGS, NWS, NOAA), about 516 pages live, plus some world pages. 25 new pages a day.
- Google Search Console (API): impressions about 200 a day 11-02 to 11-19, then 9, 8, 15, 11 on 11-20 to 11-23. About 95% fall in one day, all page types, all countries, all devices. Pages at position 6-7 vanished. Average position had slid from 7 to 47 between 11-01 and 11-13 before the cliff.
- Not deindexed: URL Inspection says "Submitted and indexed", robots allows all, sitemap read with 0 errors (682 URLs), the live pages return 200 to a Googlebot user agent.
- Bing did not fall: about 60 clicks a day, 865 to 1,200 impressions a day.
- Same Google account, another data site (flood insurance data) kept growing: 506 / 492 / 491 / 408 / 395 impressions a day on 11-18..11-22. A live camera-map site of the owner's also survived. The owner says our closest competitor (a live lake-level aggregator) fell the same day.
- Google's status page (read by the assistant): "November 2026 core update" ran 10 Nov for 13 days 20 hours (ended about 24 Nov); a "December 2026 core update" entry dated 24 Nov, content unread.
- Live page check for "medina lake water level": page 1 is the Texas state water site, USGS, two other lake-level sites, a local news site, NOAA, a Facebook page and the competitor. We are not on page 1 (we averaged position 6.9 before).
- CORRECTION to what you were told last time: our pages are NOT thin. A live lake page has 38 sections: level and flood stages, hourly and 7-day weather, radar, recent rain, nearby boat ramps and marinas, fish species, camera, "how today compares with past years", "the same 50 days in earlier years", historic crests, the dam's facts, drought monitor, E. coli samples, upstream and downstream gauges, nearby water, official links. 121 KB of HTML. Even so it vanished with the rest.
- Traffic reality (GA4 last 14 days): direct 184 sessions (9 s engaged each, likely bots), ChatGPT 102, Bing 27, Google 14. About 13 Google clicks in 14 days.
- Money: AdSense is not approved yet (reapply possible 11-26). An Adsterra banner was added 11-24; it does not render yet.
- Built but not open to Google: a /map/ page (every built US gauge as a dot on a US map, search not yet built), set to noindex until a phone review is signed. Embeds (paste a link, oEmbed) are live.

HARD RULES (verbatim from the project file): "A false page is worse than none." "No verdicts ('safe', 'runnable')." "One static page per gauge, official data." "A link exists only because this reader would tap it next, never for a count." "Nothing for a count or ranking trick: no forced links, no padding." "No code reaches production unreviewed: an independent review is required before any push." "Cloudflare free plan: 5 cron jobs, 1,000 KV writes a day, 100k requests a day, 20,000 files, 10 ms CPU." "Never enter passwords or payment details." Two writers on one file overwrite each other.

WHAT I DID AND WHY (failures included):
- Measured the cliff, ruled out a block or deindex, found Bing and a sibling site unaffected. I guessed a core-update demotion; unproven.
- I first guessed "pages restate one agency number, so they are thin" and planned to add history charts. I then read the live page and found those blocks already exist. So that guess was wrong and I corrected my plan file.
- I raised releases to 50 a day for hours, then returned to 25 a day after the cliff. Releasing faster does not fix a site-wide drop.

THE ASSISTANT'S PLAN FOR THE WORKFLOW (your order from last time, adjusted):
Rules for the workflow: strictly one step at a time (one writer per file), each step = build agent, then an independent review agent, then the existing automated check suite; nothing is pushed inside the workflow; one batched push at the end; each step must name its three-test line, its edge cases, its cost at 14,000 pages, and stop with a written result if a gate fails.
Order:
0. Measure: daily Search Console series (re-read 11-26 and 12-03). A fixed list of 50 to 100 queries tracked daily by position. PROBLEM: Google's own results cannot be scraped (terms), and Search Console only shows queries where we already appear (now almost none). Options: Bing Webmaster data, a paid rank API, or a manual weekly check in a browser for 20 queries.
1. Finish /map/: independent phone-screenshot sign-off, open it to Google, then a search box and filters, then split by region before 2,000 dots. It must show latest reading, age and unit, greyed when stale, never green for Unknown.
2. Embeds as distribution: already live. The work is outreach for links (lake associations, marinas, local news), done by the owner's approval per batch, not code. Measure installs.
3. Saved places in the browser (localStorage, no sign-in, no server cost), a "my waters" row on the home page.
4. History coverage gaps: find waters whose history blocks are empty and fix their data, no new chart type.
5. Alerts: only after a reliability test (a feed that is down is "Unknown", never "all clear"); needs an email sender and consent, so an owner step.
6. Newsletter: not built until there is real content.
Not building: more doorway pages, a login system, deleting the 520 pages.

MY QUESTION, with options and the assistant's recommendation:
Q1. Is "one step at a time, build then review then gates, one push" the right shape for an automated multi-agent build, or should some steps run in parallel on separate branches? (Recommend sequential: the files overlap and one writer per file is a rule.)
Q2. Is this the right order given the new fact that the pages are already rich and still vanished? Should step 0 (measurement) and the map come first, or should something address the likely real cause (no links, no brand, young domain)? Recommend: measurement and map first, outreach for links in parallel as a human step.
Q3. Which steps would you CUT or defer, and why (money first: what moves ad revenue)? Recommend cutting alerts and newsletter for now.
Q4. What is the cheapest honest way to track ~50 queries' positions without scraping Google? Recommend: Bing Webmaster API plus a manual weekly 20-query check.
Q5. Should I wait for the 12-03 Search Console reread before building anything that depends on rankings? Recommend: build map and saved places now (they do not depend on rankings), wait on anything else.
Q6. What would make you say this whole plan is wrong?
ANSWER FORMAT: first restate in two lines what you think I am asking. Then a table with columns: step / keep, change or cut / why / what it moves (revenue number). Then your recommended order in one numbered list. Then a short list of claims you are unsure about, labelled as guesses. Say "could not verify" instead of guessing.

GAP CHECK before you answer: list what is MISSING from my situation or this prompt that would change your answer (facts, numbers, files, constraints, risks, alternatives, and the questions an expert reviewer would ask me first), ranked by how much each would change your verdict. For each item say how I can check it. Name the assumption in my prompt most likely to be wrong. If nothing is missing, say 'nothing missing' and list what you checked. Do not fill gaps with guesses.
