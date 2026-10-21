# River Water Levels (riverwaterlevels.com)

A US river conditions site for people who fish, paddle, swim, wade, boat or live beside a river, built from government data only (USGS, NOAA / NWS, USDA, EPA, NCEI). One page per USGS gauge, river hubs, state pages and trust pages, served by a Cloudflare Worker with static assets. Indexing is opened page by page through `data/index-allow.json`.

Start with `CLAUDE.md` (Line 0, rules, pipeline), then `docs/RUNBOOK.md` (how to ship) and `docs/OPEN-ITEMS.md` (what is still missing).

```
python -I collect.py [--fast] [site ...]   # the only network code; refreshes cache/
python -I build.py                          # builds dist_next/ from cache/ only
python -I gate.py [--quick] [--live]        # the three gates in one table: build and sources, numbers, (--live) live
python -I publish.py                        # atomic swap into dist/, previous release kept; --rollback to undo
python -I refresh.py [--fast]               # the whole chain with a lock and a log (runs/refresh.log); GitHub Actions runs it on a schedule and on push
```

Releases: `python -I gate.py` once (three gates). Deploys run only through `.github/workflows/refresh.yml`.

Keys: read from the owner's other project's `.env` at run time by `lib/common.py`, never copied here. `docs/research/` (reviews and research notes) is git-ignored.
