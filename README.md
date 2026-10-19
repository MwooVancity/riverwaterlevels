# River Water Levels (riverwaterlevels.com)

A US river gauge site built from government data only (USGS, NOAA / NWS, USDA, EPA, FEMA, NCEI, USGS National Map). One page per USGS gauge, river hubs, state pages and trust pages, served by a Cloudflare Worker with static assets. The site is under a pre-launch `noindex` hold that only the owner lifts.

Start with `CLAUDE.md` (rules, gates, pipeline, template), then `docs/PLAN.md` (decisions, numbers, release queue, backlog) and `docs/WORK-LIST.md` (what the last plan review asked for and its status). Older documents are in `docs/archive/` and are superseded.

```
python -I collect.py [--fast] [site ...]   # the only network code; refreshes cache/
python -I build.py                          # builds dist_next/ from cache/ only
python -I check.py                          # integrity checks (per page and site-wide); --selftest runs the broken fixtures
python -I truth_tests.py                    # contracts over every gauge page (direction, units, silence, one number one source ...)
python -I tests.py                          # selftest, determinism, stale source, rollback, review gate, kill switch
node ui_gates.mjs                           # first screen, tap targets, contrast, accessibility, layout shift (390 px)
python -I publish.py                        # atomic swap into dist/, previous release kept; --rollback to undo
python -I refresh.py [--fast]               # the whole chain with a lock and a log (runs/refresh.log)
```

Releases: the template (`lib/`, `templates/`, `build.py`) needs a signed fresh-reader review (`tools/record_review.py`), pages are indexed only in small cohorts through `data/index-allow.json` and `tools/open_wave.py`. The release order is `tools/rescore.py` (`data/waves.csv`, gitignored). Planning data comes from `tools/fetch_geo.py`; names are cleaned by `tools/clean_names.py`.

Keys: read from the owner's other project's `.env` at run time by `lib/common.py`, never copied here. The folder `docs/research/` (reviews and research notes) is git-ignored.
