# Link building: earn citations with things people can use (not directory spam)

Status 2026-10-20: the site is noindex, so links earn referral traffic and credibility now and ranking value only after indexing starts (docs/INDEXING-RULES.md). Build the assets first; start outreach only when wave 0 is indexed. ChatGPT's Reddit-founder idea, kept and corrected: copy the discoverability and distribution, never the sitewide-footer link farm (tens of thousands of links from about a thousand domains is a footprint, not an endorsement).

## Our edge and our limits
Edge: public-domain USGS/NWS data turned into things nobody else assembles: one number per gauge with its comparison to history, 25 to 9,500 gauges, live. Limits: government sources only (no American Whitewater data), no verdicts, no fake freshness, no automated mass mailing, no paid links, no link exchanges.

## Linkable assets, in build order (each must pass: real data, a source, a reason to cite)
1. **Embeddable live gauge widget**: one iframe or script tag per gauge (flow, change, comparison word, observed time, USGS credit, a plain "River Water Levels" attribution link). Outfitters, clubs, marinas, campgrounds, local news and fishing blogs get live conditions for free; we get a followed link per embed. Needs: `/embed/<gauge>/` static page, a copy-paste snippet on each gauge page, a size under 30 KB, no cookies, a disclaimer line.
2. **Open data catalog**: `/data/` listing every gauge we publish with id, river, coordinates, parameters, update time, units; `/api/gauge/<id>.json` static snapshots rebuilt every refresh (values, observation times, percentile, comparison, source links); `/llms.txt` and `/data/README` that state coverage, provenance and limits. Public-domain source data stay public domain; say what is our computation.
3. **National and state "now" pages**: "Rivers above normal today", "Rivers below normal today", "Biggest 24 h changes", per state. Computed from the same data, regenerated each refresh. These are the pages a newsroom or a club links during a flood or a drought.
4. **Record watch**: gauges at their highest or lowest reading for the date or the decade. Newsworthy hooks, only from real stats (never modeled).
5. **Weekly state river report** (static, auto-generated, data only) for newsletters and clubs. Later.
6. **Historical explorer** (pick a gauge and a date, see the percentile across years). Later, only if the data supports it reliably.

## Who links, and why (categories; never invent a name or an address)
- Outfitters, guides, paddling clubs, Trout Unlimited chapters, fishing-report blogs: the widget replaces a manual "current flow" line.
- Local TV, newspapers and county emergency pages: the "now" pages and record watch during events.
- State fish-and-wildlife and water-resource pages that keep a "river conditions" resource list.
- Watershed associations, riverkeepers, university hydrology and geography groups: the data catalog.
- Marinas, campgrounds, parks departments: the widget.
- Wikipedia and Wikidata: do NOT add our links ourselves (conflict of interest, and it gets reverted). If the catalog is good, editors may cite it.

## Tactics that work and are allowed
1. Widget partner outreach: write to 10 relevant sites a week, each message about THEIR river and THEIR page, with their gauge already built into a working embed. One follow-up, then stop.
2. Event data tips: when a river passes a flood stage or a drought record, send the newsroom one short note with the page and the numbers (public sources named).
3. Resource-page outreach: find pages that list river-condition links; offer a link only where we are more current or cover gauges they lack.
4. Competitor backlink study (the allowed way to learn from everybody): list who links to American Whitewater, USGS WaterData and similar pages (free Bing Webmaster and Common Crawl data; the `seo-backlinks` and `backlink-analyzer` skills), then ask the same kind of page owner, with a reason specific to them. Take their ideas; never copy their content.
5. Unlinked mentions and broken links: ask for a link where our data is already named or a dead link points at a gauge we cover.
6. Reddit and forums: answer real questions with a gauge link only where the community rules allow; never post the same link repeatedly.

## Never
Directories whose business is dofollow links; sitewide footer links; paid links or exchanges; automated submissions or mass mailing; fake reviews or accounts; hidden links in widgets (the attribution must be visible); scraping other sites' data or copying their pages.

## Measure (do not chase raw counts)
Per month: referring domains (Search Console Links report, Bing Webmaster), links that are editorial vs widget, referral visits (Cloudflare analytics), embeds in use, Search Console clicks to the gauge pages, and replies per 10 emails. Log every contact in `docs/LINK-LOG.md` (date, who, why them, what we offered, result). Stop rule: if 3 months of outreach (30+ individual messages) bring no editorial link, change the asset, not the volume.

## Short email templates (plain; edit the first line for every recipient)
- Widget: "Your page on the <river> lists flows by hand. I built a free live widget for the <gauge name> gauge (USGS data, observed time shown, no cookies): <link>. Here is the snippet. It links back to the source page. If it is useful, use it; if the numbers look wrong, tell me and I will fix them."
- Newsroom: "The <gauge> reached <stage> at <time>, the highest since <date>, from USGS and NWS data: <page>. Public sources are linked on the page. Free to use with credit."
- Resource page: "Your resource page lists <X>. We publish live USGS flows with history for <N> gauges in <state>: <link>. If it fits, a link would help your readers; if not, no problem."

## Before any outreach (owner)
Publisher name and contact email live (docs/CORRECTIONS.md), About page complete, wave 0 indexed, widget and catalog built and checked for wrong numbers. A widget with a wrong number on someone else's site is a safety and reputation event.
