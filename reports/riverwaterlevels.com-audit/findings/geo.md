# AI Search Readiness: riverwaterlevels.com (audited 2026-11-04, live fetches only)

**Score: 52/100.** Technical access 95, structure 65, citability 50, authority/entity 20, mentions 5. Platform estimates: Google AIO 40, ChatGPT 45, Perplexity 55, Copilot/Bing 50. Not verified: how many pages Google has indexed (needs Search Console).

## Crawler access: fine (no finding)
GPTBot, PerplexityBot, ClaudeBot, Google-Extended, OAI-SearchBot, Googlebot and a browser UA all got HTTP 200 and identical bytes on `/` (30,094), `/robots.txt` and `/llms.txt`. robots.txt is `Allow: /` plus the sitemap. No challenge or block seen at Cloudflare. Sitemap has 285 URLs. No meta robots noindex on any page checked.

## Findings

1. **HIGH, no authority yet (not fixable by code).** New domain, no external links, no Reddit/YouTube/Wikipedia presence found, AdSense not approved. Domain rating is a weak signal, but brand mentions are the strong one. Evidence: nothing but the site's own pages point to it. Fix: earn real mentions (a helpful answer on r/kayaking or a state fishing forum, a short YouTube gauge-reading explainer, data-source directories). Worked if: Search Console shows referring domains growing and branded queries appear.

2. **HIGH, few pages in Google's index.** Only 25 pages a day are opened to Google, so most of the 285 URLs cannot be quoted. AIO cites indexed pages. Fix: owner decision to open more; Search Console reorders. Worked if: Indexed count in Search Console rises.

3. **HIGH, query type.** "River level now" queries are usually served by USGS/NWS and Google's own widgets. AIO fires rarely on them. Target stable-fact queries instead ("Frio River flood stage", "Ohio River record flood Louisville", "Frio River drainage area"). Worked if: Search Console shows impressions on those queries, then AIO appears.

4. **MEDIUM, Key facts is good but short.** It sits in the HTML at about 5% of text, before the live tiles (position 2,181 of 41,590 on Concan). Sentences are sourced and self-contained, but each is 15-30 words under a "Key facts" heading, not a 134-167 word passage under a question heading. Canada and Rhine have only 2 sentences (the Rhine has no flood marks). Fix: add one 130-160 word, fully sourced stable paragraph per gauge under a question H2 such as "What are the flood stages of the Frio River at Concan?". No readings, no verdicts. Worked if: Perplexity/ChatGPT cite it for that question.

5. **MEDIUM, entity is thin and inconsistent.** Schema names publisher "River Water Levels" (Organization, name and URL only). No sameAs, no contact, no person. Home, About and the Canada/Rhine pages carry only BreadcrumbList, with no Organization or WebSite. About says who pays (AdSense) but not who publishes. Fix: same Organization block (with sameAs once any profile exists) on all pages, and a named publisher plus contact on About (owner-only). Worked if: a search for "River Water Levels" shows a consistent entity.

6. **MEDIUM, scope contradicts itself.** Home title, H1, description and llms.txt say US rivers, USGS/NOAA only. The site also serves Canada and Germany pages. Fix: say "US, Canada and Germany" in the home text and llms.txt, and add the world pages to llms.txt. Worked if: llms.txt lists world gauges.

7. **LOW, page weight.** US gauge raw HTML is about 200 KB. Fetchers may truncate. Keep the Key facts block first, as it is.

8. **LOW, llms.txt present (19.9 KB, valid format).** Useful for agents, but no evidence that Google AIO uses it.

## Ranked reasons AIO is unlikely today
1. New domain with no links or mentions. 2. Most pages not yet indexed. 3. Live-level queries rarely get AIO. 4. Government sources outrank us on identical data. 5. Thin entity. Technical access is not a cause.

## In our control
Findings 4, 5 and 6 (code), plus opening more pages and earning mentions (owner).
