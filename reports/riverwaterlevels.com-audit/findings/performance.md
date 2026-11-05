# Performance findings, riverwaterlevels.com (2026-11-04)

**Performance score: 74/100 (estimated).** Lab method only. PageSpeed Insights answered 429 (public quota exhausted), and there is no CrUX data. LCP, INP and CLS below are estimates from bytes and markup, not measured. Timings are from one Windows curl client (TTFB includes DNS and TLS).

## Core Web Vitals (estimated, mobile 4G)
- LCP: about 1.8-2.6 s, probably pass. The LCP element is text (the H1 or a tile). First-party HTML is 7-54 KB gzipped, and it is cache-HIT at the edge.
- INP: about 100-200 ms, probably pass. Page JS is small inline scripts. Risk comes from adsbygoogle and gtag work on the main thread.
- CLS: probably under 0.1. The map and radar images carry width and height. Ad slot space was not verified.

## Bytes a phone downloads (gzip, first view, ranked)
| Item | Home | Louisville | Ottawa | Trent |
|---|---|---|---|---|
| adsbygoogle.js (third party) | 205.6 KB | 205.6 | 205.6 | 205.6 |
| gtag.js (third party) | 181.1 | 181.1 | 181.1 | 181.1 |
| USGS topo map (third party, image, not gzipped) | 222 KB (lazy) | 180 KB (lazy flag not checked) | none | none |
| HTML | 7.3 | 54.4 | 14.4 | 12.5 |
| site.css | 9.7 | 9.7 | 9.7 | 9.7 |
| dir.css | 0.8 | none | none | none |
| **Total without map** | **~405 KB** | **~451 KB** | **~411 KB** | **~409 KB** |

Ad iframes and ad creatives load after adsbygoogle and were not measured. They add more.

## Findings

1. **HIGH: Third-party scripts are about 387 KB, or 94% of every page's bytes.**
   - Evidence: adsbygoogle 205.6 KB plus gtag 181.1 KB, against 22-64 KB first-party. The 90 KB gate in `check.py` counts only first-party, so it misses this.
   - Fix: load both scripts after first paint (on `load` or idle). Drop GA4 if nobody reads it. Add a third-party budget of about 400 KB to the gate.
   - Proof: Lighthouse "third-party summary" and transfer size drop; WebPageTest shows main-thread time under 300 ms.

2. **MEDIUM: Consent defaults deny only EEA/UK.** In the rest of the world, gtag and ads start with full consent and full cost. That is a policy choice, not a speed bug. Say so before any change.

3. **MEDIUM: Slow TTFB.** Measured 0.96 s (home), 1.18 s (Louisville), 1.10 s (Ottawa) and 1.49 s (Trent) with CF-Cache-Status HIT. Part of that is my client's connect time.
   - Fix: re-measure with `curl -w time_connect,time_appconnect` from a second location. If TTFB minus connect is above 200 ms, check the Worker's cost on cached HTML.
   - Proof: CrUX TTFB p75 at or under 800 ms.

4. **MEDIUM: Map images come from a slow third-party host.** The USGS basemap returned 222 KB in 8.0 s and 180 KB in 7.2 s. The home page marks its map `loading=lazy`, which is right.
   - Fix: confirm the Louisville map is lazy too. Serve a self-hosted static map, or give the box a fixed size so CLS stays 0.
   - Proof: no basemap request before scroll in DevTools.

5. **LOW: Louisville HTML is 54.4 KB gzipped (210 KB raw).** It is within the 90 KB limit, but it is the biggest first-party item.

6. **LOW: Caching.**
   - Good: hashed CSS has `max-age=31536000, immutable`.
   - HTML, `gauges.json`, manifest, favicon and `sw.js` use `max-age=0, must-revalidate` or `no-cache`. Revalidation is a cheap 304, which is correct for HTML.
   - Fix: give favicon and manifest a one-day max-age.

7. **LOW: Render blocking.**
   - The only blocking resources are `site.css` (9.7 KB gzipped) and, on the home page, `dir.css` (0.8 KB gzipped).
   - Several inline scripts run in `<head>` (consent, theme). All are tiny.
   - Ad and gtag scripts are `async`, so they do not block.
   - Fix: inline `dir.css` on the home page to save a round trip.

## Fonts
No webfont and no `@font-face`. The stack is `system-ui` and Georgia. Zero font bytes, no FOIT, and no font-driven CLS. Good; no change needed.

## /gauges.json
- Cost: 24.8 KB raw, 8.5 KB gzipped, `no-cache` with an ETag, so repeat visits are a 304.
- When it loads: the home page fetches it only on search-box focus or when a typed search finds no match. It is not fetched on first view.
- Fetch it on idle only if search is common. It is fine as is.
- Proof: no `/gauges.json` request in the first-load HAR.

## Unverified
- Live reading fetch URL: `/live/ohio-river-ky.json` returned 404, but the real slug is built in JS from `ID`. Not traced.
- Real-user numbers. Add CrUX or web-vitals RUM once there is traffic.
