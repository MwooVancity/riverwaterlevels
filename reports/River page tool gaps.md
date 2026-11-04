# Few true gaps remain; four matter

**What this is:** a planning doc only. It doesn't change the site.

The site's own code already has most of the tools that competitors are known for. The researchers listed 11 "missing" tools. A grep of `lib/` (2026-11-03) shows that 8 of them already have a block on US pages. Rate of rise is `b_rate`. The river camera is `b_camera`. Record and "last this high" are `b_record`, `b_peaks` and `b_crests`. Upstream and downstream order is `b_related` via NLDI. Turbidity is `b_quality`. NWS impact text is `b_impacts` and `b_low_water`. The National Water Model outlook is `b_nwm` and `b_nwm_medium`. Dam release is `b_dam`. There is also a WaterAlert link and a "gage height is not depth" line.

Four gaps would change what a reader on a phone decides within 30 seconds. **First and most valuable:** quote the activity limits and closures that agencies publish (for example a county's 700 cfs tubing closure). That is the most-asked question, and no competitor gives it without its own verdict. **Second:** make the charts readable by touch, because they are static pictures today. **Third:** link straight to the alert signup for this gauge instead of the general WaterAlert home page. **Fourth:** on pages outside the US, fill in the "next" items `lib/world.py` already lists, for England above all (impact levels, river forecast, water temperature).

The biggest unknown is the site itself. This report checked that each block exists in the code. It did not check that the block shows, reads correctly or helps on a live page. Every "already present" below means "code exists", not "works well".

Evidence tags used throughout: **[C]** confirmed competitor feature, **[Q]** confirmed user question or complaint (interest, not proven demand at scale), **[D]** official dataset with reuse terms confirmed, **[P]** plausible opportunity without demand evidence, **[U]** unverified. "Checked" dates are when the research notes were written (2026-11-03) or when the code was grepped (2026-11-03).

## Ranking rule: does it change a decision in 30 seconds?

Competitor feature counts are used only as hints. A tool ranks high only if it changes what a reader at the river does next (go, wait, move, leave) or saves them a step, using official data and no verdict.

The strongest demand signal in the notes is "is X cfs good for my trip?", which came up in 15+ independent forum, Reddit and outfitter pages **[Q]** ([r/Louisville snapshot](https://reddit.sentinel-team.org/posts/1stlsou/snapshots/2026-04-24T20%3A21%3A57.677621Z); [Ozark Anglers](https://forums.ozarkanglers.com/topic/55576-is-this-river-level-ok-for-wade-fishing); checked 2026-11-03). Paddlers and anglers say only local experience can turn a flow number into a judgment for one stretch **[Q]** ([paddling.com](https://forums.paddling.com/t/flow-cfs/17168)). That is a verdict the site must not give. The only allowed answer is a limit an agency itself published.

These counts are pages the researchers found. They are not search volumes. No People-also-ask or Search Console query data was gathered **[U]**.

## Missing everywhere (US and non-US): ranked

| Rank | Tool | Why it changes a decision | Evidence | Competitors with it | Data source | Effort |
|---|---|---|---|---|---|---|
| 1 | **Agency-published activity limits and closures**, quoted with source and date (for example "Boulder County: tubing closed above 700 cfs") | Answers the #1 question with the agency's own words, not ours | [Q] 15+ pages ([Denver Gazette](https://www.denvergazette.com/?p=392540); [Longmont Leader](https://longmontleader.com/outside/sheriff-implements-tubing-restrictions-on-st-vrain-creek-river-5474298); [Golden Transcript](https://www.thegoldentranscript.com/news/golden-expecting-an-earlier-and-shorter-tubing-season/article_fb1007ff-cd6e-43b9-bd86-ff3a33580be4.html)) | None found. AW and rivers.run show **paddler-made** ranges, not agency ones [C] ([AW](https://www.americanwhitewater.org/?p=13366); [rivers.run](https://apps.apple.com/us/app/rivers-run/id1552809249)) | Sheriff, city and park notices. **No feed**, and the examples found were mostly in Colorado [U for coverage] | High. One curated row per gauge (same pattern as `data/dams.json`). Each row goes stale when the agency changes its rule, so each needs a `read_on` date and an age limit |
| 2 | **Touch readout on charts** (tap or drag to see value and time) and a range choice | Lets the reader check "what was it at 7 am" or "is it still rising" without reading SVG gridlines | [C] GaugeMap drag readout ([GOBA guide](https://goba.org.uk/?p=1021)). [C] Riffle 24 h/48 h/7 d/30 d ([App Store](https://apps.apple.com/app/id1662402139)). [Q] Blue Liner reviewers complained of one point per day ([App Store](https://apps.apple.com/us/app/id6464350766)). Demand for a touch readout itself: [P] | GaugeMap, Riffle. GOV.UK has a **fixed** 5-day chart with no range choice [C] ([station 7267](https://check-for-flooding.service.gov.uk/station/7267)) | Data already on the page. Code check: the charts in `lib/charts.py` and `lib/blocks3.py` are static `<svg>` with no pointer handlers (grep 2026-11-03) | Low. A small inline script, counted against the 90 KB limit |
| 3 | **Alert signup for this exact gauge** | One tap instead of searching WaterAlert for the site number | [C] the USGS page has a "Create a WaterAlert" link per site ([WaterAlert guide](https://accounts.waterdata.usgs.gov/wateralert/user-guide)). 7 competitors offer threshold alerts [C] (see competitor notes). Code: `lib/page.py:114` links the **general** `accounts.waterdata.usgs.gov/wateralert/` page | WaterAlert, RiverTrax, Riffle, Blue Liner, rivers.run, RiverApp, DreamFlows | USGS WaterAlert (US only). Whether a deep link that pre-fills the site exists: [U]. Read the USGS page's own link first | Very low, if the deep link exists |
| 4 | **Official bathing-water status** (not just samples) | Swimmers and dog owners ask "after rain, can I swim?" | [Q] 8+ pages ([WDBJ7](https://www.wdbj7.com/2025/07/22/wait-river-drop-heavy-rain-impacts-water-levels-bacteria-james-river/); [ABC11](https://abc11.com/post/french-broad-river-officials-warn-swimming-north-carolina/15114934/)) | None of the competitors researched | England: EA Bathing Water Quality API, **OGL stated** [D] ([bwq](https://environment.data.gov.uk/bwq/)), but few river gauges sit near a bathing water [U]. US BEACON: **no API found** ([BEACON](https://beacon.epa.gov/ords/beacon2/r/beacon_apex/beacon2/about-page-content)). Canada and Germany: per city or Land, no national API | Medium for England only. High or blocked elsewhere. US pages already show E. coli **samples** (`b_samples`, Water Quality Portal) |
| 5 | **Upcoming dam release schedule** (planned, not only the latest outflow) | Tailwater anglers and tubers plan around tomorrow's release | [Q] 6+ pages ([USGS Wallenpaupack](https://www.usgs.gov/publications/time-travel-releases-lake-wallenpaupack-us-geological-surveys-streamgage-monitoring); [Brazos RA](https://brazos.org/about-us/news/current-news/articleid/2391)) | DreamFlows, AW Flow Info, Local River Flows [C] ([DreamFlows](https://www.dreamflows.com/)). DreamFlows schedules are not an official feed | USACE CWMS Data API, reads need no login ([GitHub](https://github.com/USACE/cwms-data-api)). Whether it publishes **future** schedules: [U]. USBR RISE is daily history only ([data.gov](https://catalog.data.gov/dataset/starvation-reservoir-and-dam-daily-lake-reservoir-release-total-cfs-time-series-data)). Terms pages not read [U] | Medium. Extends `b_dam`. Must not guess which dam feeds which gauge |
| 6 | **Downloadable readings as a spreadsheet** (CSV) | Rarely a phone decision. Useful for guides and residents keeping records | [C] GOV.UK CSV ([station 7267](https://check-for-flooding.service.gov.uk/station/7267)), DreamFlows CSV. Demand: [P] | GOV.UK, DreamFlows | Already built: `data.json` is linked in the page's schema (`lib/page.py:411`) | Very low. Low value; rank stays last |

## On US pages, missing on non-US pages

`lib/world.py` `COVER` already lists these blocks per country (Canada, Germany, England). Only a "next:" entry is fixable. A "none:" entry records that the agency publishes no such data. That claim came from the code author, and this report did not re-check it **[U]**.

| Block (US) | Canada | Germany | England | Fixable now? |
|---|---|---|---|---|
| `b_impacts` / `b_flood_stages`: what floods at each level | none | none (state level) | **next**: GOV.UK lists impact levels per station (Colwick 4.30 m read 2026-11-03), no open feed read | England: high reader value. GOV.UK pairs plain impact text with each threshold [C] ([station 7267](https://check-for-flooding.service.gov.uk/station/7267)) |
| `b_river_forecast`: official river forecast | none (provincial) | have | **next**: GOV.UK model forecast at some stations, no open feed read | England only, if a feed exists |
| `b_wtemp`: water temperature | none | have | **next**: 2 of 7,439 EA measures | England only, 2 gauges. Low reach |
| `b_related`: upstream/downstream in river order | none: feed has no order | have | none | Order exists for GOV.UK pages [C], but there is no open order field [U] |
| `b_camera` | none | none | none | No national feed in any of the three |
| `b_record`, `b_peaks`, history charts | have / partly | **none**: PEGELONLINE keeps 30 days | partly (record in official marks) | Germany history needs another source (the Länder?) [U] |
| `b_flood_outlook` | none | none | **next**: Flood Forecasting Centre 5-day risk | England, if a feed exists |
| `b_air_quality`, `b_acis`, `b_air`, `b_qpf`, `b_radar` | mixed | have | **next** (Defra, Met Office) | Context blocks. They do not change the water decision; build last |
| `b_samples`, `b_attains`, `b_drought` | none | none | **next** (EA archives) | Low within 30 seconds |

The most valuable fix in this group is **England's impact levels**. GOV.UK already shows "5.15 m: top of normal range, low-lying land flooding possible" on its station page **[C]**. Until the site carries the same lines, its England page answers "what floods at this level?" worse than the free official page.

## Already present (code exists; live quality not checked)

| Researcher "gap" | Where it is | Caveat found in code |
|---|---|---|
| Rate of rise | `b_rate` (`lib/blocks2.py:131`): 1/3/6/12/24 h change, flow and height | Shown as a block, not an alert. Hidden at tidal or oscillating gauges |
| Record level with date, "highest since" | `b_record` ("last day as high as this week"), `b_peaks`, `b_crests` (NWS historic crests), `b_low_water` | Uses daily means, which run a day or two behind |
| Upstream/downstream in river order | `b_related` via NLDI (`lib/related.py`), upstream tile in the hero, lag hours | The lag is **our own** calculation and must say so. NLDI can start slightly off the gauge ([NLDI docs](https://api.water.usgs.gov/docs/nldi/navigation)) |
| USGS river camera | `b_camera` (HIVIS/NIMS, `lib/blocks3.py:400`) | 1,000+ cameras across about 13,500 stations, so at most about 7% of gauges have one ([USGS](https://www.usgs.gov/mission-areas/water-resources/news/1000-cameras-and-counting)) |
| Turbidity | `b_quality` (63680) with a USGS-attributed explanation | Only at about 8% of gauges (2018 count) ([USGS](https://www.gov.nl.ca/ecc/files/waterres-rti-rtwq-conf-2018-17-patrickrasmussen.pdf)). The hero says "clarity" is missing otherwise |
| NWS impact text per stage | `b_impacts`, `b_low_water`, next-impact line in the height tile | US forecast points only |
| NWM outlook as model guidance | `b_nwm`, `b_nwm_medium` | US only |
| Dam release | `b_dam` (CWMS/RISE, hand-matched) | Latest outflow only, not a schedule |
| Inundation maps | `b_nws_point` links water.noaa.gov | A general link, not the map itself |
| Gage height is not depth | `GLOSS` in `lib/hero.py:216` plus `/glossary/` | Answers the Potomac beginner question [Q] ([paddling.com](https://forums.paddling.com/t/newbie-kayaking-and-camping-on-potomac/54064)) |
| Normal for the date | is-this-normal tile, percentile band on the 7-day chart, `b_sustained`, `b_flowdur` | |
| Weather, rain forecast, radar, snow, stocking, tides, access points | `b_hourly`, `b_qpf`, `b_radar`, `b_snotel`, `b_stocking`, `b_tides`, `b_access` | `b_access` lists OSM ramps. It does **not** say whether a ramp is closed |

## Do NOT build

**Plain-word clarity bins** ("Clear, Stained, Muddy, Blown out"). These are RiverTrax's own scale **[C]** ([App Store](https://apps.apple.com/us/app/rivertrax/id6745478475)). On this site they would be a verdict built on a sensor at about 8% of gauges.

**Personal "your range" bands and "sweet spot" alerts.** They need accounts or stored state. They also give a false sense of safety, since the range the reader typed in becomes what the page displays. WaterAlert already does thresholds officially.

**Lightning.** Blitzortung's own terms say "private and entertainment purposes" and "not intended for protection of life and property" ([blitzortung](https://www.blitzortung.org/sr/contact.php)). No official free source was found **[U]**.

**Road closures from 511.** Every state's feed is different. Some need a developer agreement or key, and **no flood event type** was found ([511wi](https://511wi.gov/developers/doc); [511.org](https://511.org/open-data/faqs)). Showing nothing would read as "road open".

**Ramp open or closed status.** No national dataset exists. Closure notices are one-off news items ([riverbender](https://m.riverbender.com/news/details/public-launch-ramp-closed-until-further-notice-93258.cfm)). A list that is partly up to date is worse than none.

**CyAN algal-bloom index.** It covers lakes only, and US lakes are out of scope (Lakebrief). It is a satellite index, not an advisory, and the web app had an outage in 2026 ([EPA](https://www.epa.gov/node/219529)).

**Hatch charts, solunar, shop reports, put-in/take-out guides, journals, widgets, watch apps.** These are not official data, need an app or account, or duplicate better products (Current: Fishing, AW, RiverApp) **[C]**.

**A travel-time calculator for releases.** Published times depend on base flow and release size ([USGS FS 083-96](https://pubs.usgs.gov/fs/1996/fs-083-96)). Quote a study only where one exists for that reach.

**A Navigation notices (USCG weekly notices, German skipper notices) block.** The US notices are weekly PDFs, and no German endpoint or terms were found ([navcen](https://navcen.uscg.gov/node/194)). It would take heavy maintenance for few readers.

## Task-by-task score against competitors

The "Site" column is based on code only and was not checked on live pages. Competitor columns come from the cited notes. "?" means the evidence is not enough to judge.

| Reader task (30 s, phone) | Site | USGS page | NWPS | GOV.UK | RiverTrax | rivers.run / AW | Riffle |
|---|---|---|---|---|---|---|---|
| Level now with time and source | Have | Have | Have | Have | Have | Have | Have |
| Is it normal for today's date | Have (percentile) | ? | ? | Have (normal range) | ? | Paddler range only | ? |
| Rising or falling, and how fast | Have (`b_rate`) | Chart only | Chart | Trend word | Have, plus alert | Colour | Trend |
| What is coming (official forecast) | Have (US), partial abroad | No | Have | Some stations | Have | Have | Premium |
| What floods at this level | Have (US), **missing England** | No | Have | **Have** | Stage lines | No | Flood stages |
| Is my activity allowed at this level | **Missing** | No | No | No | User range | Paddler range | User range |
| Read an exact past value on the chart | **Worse (static)** | Have [U] | ? | Fixed 5 day | Have [U] | ? | Have (ranges) |
| Get told when it crosses a level | General link only | WaterAlert | No | Floodline number | **Best** | Have | Have |
| See the river (camera) | Have where USGS has one | ? | Gauge photos | No | Have (700+) | No | No |
| Water clarity / temperature | Have where measured | Have | No | No | Have | Units toggle | Have |
| Upstream and downstream next gauge | Have (US, Germany) | No | Forecast points | **Have** | Have | No | No |
| Can I swim (bacteria) | Samples only | No | No | No | No | No | No |

The site leads on putting the "is it normal" percentile and official impact text on one page together. It is behind on chart interaction and alerts. RiverTrax leads on alerts and gets about even on camera and upstream gauges **[C]**. It trails GOV.UK on England impact text. There is not enough evidence to compare speed, uptime or readability for any competitor. Small App Store review samples (3 to 42 ratings) make the complaints anecdotes **[Q]**.

## Conclusion

The cheap work is mostly finished. The next gains come from two places. The first is the reader's actual question, "is it allowed or closed at this level?", and the only verdict-free answer is curating agency notices by hand. That only pays off where an agency has published a number, so it should start with the gauges that have the most searches. The second is fixing how the site shows what it already has: touch-readable charts and an alert link for this exact gauge.

Before any build, run one check that matters more than this report. Open 5 live pages and confirm that the "already present" blocks above actually render with real data. A block that exists in the code but is hidden by its four-state rules on most gauges is a gap in practice.
