# Technical SEO: riverwaterlevels.com (audited 2026-11-04, live fetch only)

**Score: 86/100.** No Critical or High issues. The site is clean on the main checks; the open items are Medium and Low.

## Passing (checked live)
- robots.txt: `Allow: /` plus the sitemap line.
- Sitemap: 285 URLs, all return 200. Each has a self-canonical. None carries a noindex meta tag or an X-Robots-Tag header.
- Sitemap and indexability agree both ways:
  - Every URL linked from the 285 pages that is not in the sitemap is noindex (`/status/`, the kern-river and apple-river gauge pages, and 183 `/embed/river/...` pages).
  - I found no indexable page missing from the sitemap.
- Redirects: http and www go to https non-www in one 301. A missing path such as `/river/zz/` returns a real 404 with `noindex`.
- Orphans: 0 across the 285 URLs. The home page links to the hubs, and gauge pages are one more click away.
- Hreflang: none, and `<html lang="en">` is set. Correct for English only.
- Page weight: gzip is 55 KB for Louisville and Glenwood Springs, 14 KB for Kaub. All are under the 90 KB limit.
- Numbers are in the static HTML. Frio River at Concan has about 41k characters of visible text with no JS needed, and it states which parts are as of the page build.

## Findings

### 1. Medium: slash redirects are 307 (temporary)
- Evidence:
  - `/about` returns 307 to `/about/`.
  - `/river/frio-river/concan` returns 307 to `/river/frio-river/concan/`.
  - `/index.html` returns 307 to `/`.
  - The http and www redirects are 301.
- Fix: make the Worker issue 301 for slash and index.html normalisation.
- Check: `curl -sI https://riverwaterlevels.com/about` shows 301.

### 2. Medium: `llms.txt` is out of date
- Evidence: `/llms.txt` says "USGS, NOAA/NWS" only and lists 186 `/river/` links. It has no Canada, Rhine, England, Moselle, Main or Danube pages (0 matches).
- Fix: have the build generate it from the sitemap list and name all five agencies.
- Check: the world hubs and gauges appear in `/llms.txt`, and its text matches `/data-sources/`.

### 3. Medium: the home page presents the site as US-only
- Evidence:
  - The `/` H1 is "River levels and flows for US rivers and creeks".
  - The home meta description says "US river gauges, from USGS and the National Weather Service".
  - The home page links /canada/, /rhine/, /england/, /danube/, /main/, /moselle/ and /lake-constance/ (all in the sitemap).
- Fix: reword the title, H1 and description to name the countries and agencies.
- Check: the home source states the five agencies, matching `/data-sources/`.

### 4. Low: lastmod is a blanket date
- Evidence: 274 of 285 entries have `2026-11-05`, and 11 have `2026-11-04`. The `/about/` page is stamped 11-04 and gauge pages 11-05, so they track the daily rebuild, not a content change. At the time of the fetch the 11-05 date was ahead of the US date of 11-04.
- Fix: set lastmod to the last real change per page; static pages keep their edit date.
- Check: the lastmod values differ by page type and `/about/` does not move on rebuild.

### 5. Low: some world gauges are weakly linked
- Evidence: 34 sitemap URLs have 2 or fewer inbound internal links. The Canada pages credit-river-near-cataract and james-river-near-sundre have 1 each. There is no `/rivers/` index (`/rivers/` 301s to `/`).
- Fix: add 3 to 5 related links on world gauges (neighbours on the same river or in the same hub), as the programmatic rule already says.
- Check: a re-crawl shows no sitemap URL with fewer than 3 inbound links.

### 6. Low: world titles are generic
- Evidence: `/rhine/kaub/` has the title "Rhine at Kaub water level today | River Water Levels". `/england/river-trent-at-colwick/` has "River Trent at Colwick water level today". US pages have "live water level and flow (USGS 03294500)". Only the US titles carry the gauge ID and unit.
- Fix: add the country and gauge ID to world titles.
- Check: titles carry the country or the gauge ID, and they are still unique across the sitemap.

### 7. Low: security headers
- Evidence: `content-security-policy-report-only` is set, not an enforced CSP. HSTS is `max-age=31536000` with no includeSubDomains. Other headers are good: nosniff, DENY, referrer-policy, permissions-policy.
- Fix: enforce the CSP once reports are clean.
- Check: `curl -sI` shows `content-security-policy`, not the report-only form.

## Doorway risk
No exact duplicates: gauge pages share a template but carry their own readings and statistics. Held gauge pages and 183 embed pages are noindex with self-canonicals.
