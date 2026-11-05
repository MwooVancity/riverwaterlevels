# SXO audit, 2026-11-04

**Search experience score: 68/100.** Pages are deep and sourced. Weak points: what a phone sees first, thin non-US pages, and unverified freshness on one page. Limits: WebSearch gave no ranks; page reads were summaries, not a phone render.

## What wins per query
| Query | Winners seen | Type |
|---|---|---|
| ohio river level louisville | Louisville MSD river page, local news (WAVE3, WHAS, WDRB, Spectrum) on the 2025 flood | Agency page plus news |
| frio river level | snoflo, howsyourriver, legionreport, riverapp, NWS text products | Aggregator gauge pages |
| river trent level | gov.uk check-for-flooding, riverlevels.uk, floodradar | Agency plus aggregator, station level |
| ottawa river level | 613today map (Britannia, Hull), CBC flood stories, ORRPB | Local aggregator map plus news |

Our pages are the same type as the winners for Frio, Trent and Ottawa (gauge page). Ohio is a partial mismatch (see F1).

## Findings

**F1. Ohio/Louisville: local readers ask in "downtown stage" terms. Severity: High.**
Evidence: SERP is MSD plus flood news citing McAlpine Upper/Lower stage in feet. Our page leads with USGS flow (51,000 cfs) and the NWS point is "McAlpine Lower", a different place from the gauge.
Fix: put the NWS stage for McAlpine Lower beside the gauge tile, with flood-category thresholds from NWS, and label which gauge each number belongs to.
Proof: Search Console clicks for "ohio river level louisville" and "mcalpine" queries; mismatch note gone from the page.

**F2. Non-US pages are thinner than US pages. Severity: High.**
Evidence: Trent shows alerts "Unknown" and forecast "Not shown". Ottawa has no forecast and no flood thresholds. Winners (gov.uk, riverlevels.uk) show warning status and a typical range.
Fix: Trent: EA flood-warning feed by area (CAP/JSON) and EA station forecast where issued. Ottawa: ORRPB and Environment Canada water office thresholds if the terms allow. Otherwise say "Not issued" with the reason.
Proof: `world.gaps` and `thin` counts fall; Unknown tiles on live Trent page go to zero.

**F3. Ottawa date reads "Nov 4, 2025". Severity: High (truth).**
Evidence: the fetch summary shows 2025, today is 2026-11-04. May be a summary slip; I could not confirm.
Fix: read the live HTML timestamp and the `/live` JSON; if it is wrong, treat as a top-rank defect. Add a check: shown year must match the feed year.
Proof: a render with the clock shifted two days shows the stale mark.

**F4. Top of page is long for a 30-second reader. Severity: Medium.**
Evidence: US pages carry about 18 sections (Frio, Ohio). Tiles come first, which is right, but there is no one-line "latest reading vs flood stage" next to the H1 on Ohio.
Fix: tile order stays; add action/minor flood stage values beside the gage height tile (official numbers only).
Proof: scroll depth and bounce in Cloudflare/Search Console; page stays under 90 KB.

## Personas (0-100)
| Page | Angler | Paddler | Flood-worried homeowner |
|---|---|---|---|
| Ohio/Louisville | 62 (no temp) | 66 (boat access list partial) | 78 (stages, impacts, rate of rise; wrong-place forecast point costs points) |
| Frio/Concan | 80 (temp, flow) | 82 (flow, percentiles) | 70 (no river forecast issued, stages present) |
| Trent/Colwick | 55 | 58 (ramps listed) | 52 (alerts Unknown) |
| Ottawa/Britannia | 50 | 55 | 40 (no thresholds, no forecast) |

## Top 3 missing, by page (public official data only)
- **Ohio:** (1) NWS stage at McAlpine Lower in the first tiles; (2) USACE lock/dam pool or release data for the Falls (USACE Louisville District publishes it); (3) water temperature from USGS or ORSANCO where a sensor exists, else "no sensor".
- **Frio:** (1) NWS river forecast: none issued, so show "Not issued" with the point id (done); (2) Texas Water Development Board / Texas park-gauge notices (Garner State Park) if published as data; (3) none further; page is near the winners.
- **Trent:** (1) EA flood warnings and alerts by area; (2) EA river level forecast where issued; (3) full year-by-year history.
- **Ottawa:** (1) ORRPB flood thresholds and forecast; (2) Environment Canada flood watch/warning status; (3) upstream gauge levels (Hull, Carillon, Lac Deschenes) from the Water Survey of Canada.

No verdict text, no noindex, no FAQ schema is suggested.
