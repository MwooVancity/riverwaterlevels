# riverwaterlevels.com SEO audit, 2026-11-05: score and action plan

Health score 73/100 (weighted). Technical 86, Content 71, On-page ~78 (estimate, from the technical and content findings), Schema 52, Performance 74 (estimate: PageSpeed quota was out), AI search 52, Images ~80 (estimate, not measured).
Not run: Search Console, backlinks, Core Web Vitals field data (no keys connected); screenshot review (done 2026-11-04).
Checked by hand: the Ottawa "Nov 4, 2025" date flag was false (the page shows Nov 4 with no year); index_live 0 mismatches of 185.

## Owner only
1. High: publisher name and a monitored contact email on /about/ and the footer, plus a /contact/ page. Today /contact/ and /corrections/ return 404 and no page has an email. This is the main AdSense trust risk; sibling sites were rejected for low value.
2. Decide on gtag (Google Analytics, 181 KB of about 450 KB per page). AdSense (206 KB) stays. Search Console clicks are the number that counts.

## Code, in order
1. Truth: Louisville shows "Typical for this date" beside +168% in 24 h. The chip compares the 24-hour mean, not the latest reading. The chip must name what it compares. Fixture first.
2. Truth: Ottawa shows 517 m3/s (6:25 PM) and 526 m3/s (6:10 PM) on one page. Every flow value gets its time beside it. check.py rule.
3. Schema: copy the Louisville WebPage + Place + Dataset graph to world pages (each agency as creator and licence; no distribution until data.json exists). WebSite + Organization on the home page. check.py rule: no live reading in JSON-LD.
4. Scope: home H1, description and /llms.txt say US only; the site also covers Canada, Germany and England. Use the real counts from the build.
5. Redirects: trailing slash and index.html return 307; make them 301 in the Worker.
6. World titles: add country and station id, as US titles do.
7. Hubs: state hubs with 1-2 gauges (/rivers/ky/ is 199 words): fold into regional hubs. Never noindex.
8. Template share 50-64% with digits masked (under the 80% gate): move repeated explainers behind one glossary link.
9. lastmod: 274 of 285 sitemap dates are the same day; use each page's last real data change.

## Rejected (against project rules)
- A 130-160 word composed paragraph per gauge (composed prose; Key facts covers quotable facts).
- noindex for thin hubs.

Findings per area: findings/technical.md, content.md, schema.md, performance.md, geo.md, sxo.md.
