# River Water Levels (riverwaterlevels.com): build

Pipeline: `collect.py` (the only code that uses the network) -> `cache/` -> `build.py` (cache only) -> `dist_next/` -> `check.py` -> `publish.py` (atomic swap, previous release kept) -> `npx wrangler deploy`.

```
python -I collect.py [site ...]     # refresh cache (default: the 25 wave 0 gauges in lib/pages.py)
python -I build.py                  # 3 tabs per gauge + hubs, states, home, trust pages, sitemap, robots, redirects, headers
python -I check.py                  # integrity checks on dist_next (per page and site-wide)
python -I publish.py                # check + swap into dist; --rollback to undo
python -I tests.py                  # selftest, determinism, forced stale source, rollback
python -I livecheck.py [url ...]    # fetch live URLs on the real domain
npx wrangler deploy                 # uploads dist/ as a Worker with static assets, attached to riverwaterlevels.com
```

Law: `C:\Users\mwoo7\Desktop\calcscrape\docs\research\MASTER-SPEC.md` (plus MASTER-PROMPT, DESIGN-UI, INTERNAL-LINKS, END-TO-END-PLAN). API keys are read from the older repo's `.env` at run time and never copied here.

Files: `lib/common.py` paths and helpers; `lib/pages.py` effective page table (first-pass cleaner plus `data/name-overrides.csv`), slugs, hubs, wave 0 list; `lib/render.py` block registry and tab shell; `lib/directory.py` home, state, hub, trust pages, sitemap; `data/sources.json` terms register that gates which blocks render; `templates/` css and `_headers`.

## Pre-launch hold
`templates/_headers` sends `X-Robots-Tag: noindex` on riverwaterlevels.com and www. Remove those two rules at launch (owner rule: every published page is indexable).

## Facts learned building (2026-10-16)
- NWPS `/gauges/<USGS id>` returns the forecast point directly (lid, usgsId, reachId = NWM reach). The per-area gauge search endpoint is rate limited (429); do not use it.
- Some inventory gauges stopped reporting flow years ago (Arkansas at Canon City: last flow 2006) or are seasonal with null values (Arkansas at Parkdale, qualifier SEASONAL). `build.py` treats a flow reading older than 30 days as a critical failure and publishes nothing for that gauge; between 24 h and 30 days the page shows a Gauge not reporting notice.
- NWS can return system "Test Message" alerts; they are filtered out (`IGNORED_ALERTS`).
- NLDI navigation returns non-gauge sites; related gauges are filtered to inventory gauges on the site that report flow.

## Not built yet
Name cleaner v2 (NHDPlus), the other 9,074 gauges, pH/field-measurement/peaks/record-comparison blocks, EPA/OSM/camping/camera/PFBC fishing blocks (terms off or unported), locator map, contact email and Report-an-issue, analytics, ads, sitemap shards by state, search index JSON for the full inventory, hosting decision before wave 3 (20,000-file limit), git repo.


## Final form (2026-10-17)
See CLAUDE.md for rules, pipeline, template and the not-built list. Collector modes: `--nws-only`, `--extras-only [--keys=snotel,cpc,peaks,wtemp,multiyear]`. `python -I refresh.py` runs the whole chain. Test 5 in tests.py covers the new blocks.

`--fast` collector mode, `build.py --preview`, `tools/demand.py` and `tools/rescore.py` (rollout order), `lib/blocks2.py` and `lib/blocks3.py` (blocks) were added 2026-10-17; see docs/PLAN.md.
