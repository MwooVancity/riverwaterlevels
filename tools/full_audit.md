# Full audit: master prompt (owner 2026-11-10: "a master prompt to audit it fully")

Run: tell Claude "run the full audit" in this folder. It reads this file and follows it. Cost: about 8 fresh reviewers, ~1M tokens, about an hour. Run monthly, or after a big change. Report only. Fixes go into PLAN.md as items with "Edge cases:" lines, then get built like any other item.

## Rules for every reviewer
- Fresh eyes. Each reviewer gets the files and live URLs, never Claude's conclusions.
- Read-only. No edits, commits, pushes, workflow runs or Search Console changes.
- Proof only. Every finding needs a file:line, a live URL read in the same run, or a log line. Anything not proven is marked "unverified". A finding with no proof is dropped.
- Use the measured numbers: live `https://riverwaterlevels.com/status.json` (ledger, coverage, census) and the newest watchdog run Summary. Never download feeds again (CLAUDE.md "laptop" rule).
- Each finding gets:
  - one line in plain words;
  - its proof;
  - which reader or which number it hurts (readers, Google impressions or clicks, ad money, owner time);
  - the size at 14,000 pages;
  - a verdict: FIX / DELETE / SIMPLIFY / KEEP.
- The three tests (CLAUDE.md) judge every page finding: "Helpful / Gain / HCU". A suggestion that fails one is not made.
- Truth first: gates that catch wrong numbers stay. Never suggest loosening a check; suggest fixing the cause.

## The eight angles (one fresh reviewer each, run in parallel, max 8)

1. **Truth (is every number right?)**
   - Pick 15 live pages: 5 US rivers, 3 lakes, 3 coasts and 4 world pages, chosen at random from the sitemap.
   - For each page, compare the reading, the time and the unit with the agency's own page, fetched now.
   - Check the flood stages, the forecast, and the weather and rain lines.
   - List every mismatch, wrong time zone, wrong unit or stale number that is shown as fresh.
   - Read `lib/wx.py` `suspect`, `lib/world.py` `PROVED` and `tools/truth_*`: what kind of wrong number would get through today?

2. **Reader (5-second test on a phone)**
   - Fetch 6 pages at phone width: river, lake, coast, world, hub and home.
   - Can a person say what the river is doing in 5 seconds?
   - Check against CLAUDE.md "readable at a glance" and "Page rules":
     - order;
     - at most 5 columns per table;
     - unit next to each number;
     - no verdicts ("safe", "runnable", "fishable");
     - every number has a source line.
   - Name each sentence no source can check. Use the `content-quality-auditor` skill for the E-E-A-T read.

3. **Google (find, index, rank)**
   - Read the sitemap, `robots.txt`, canonical tags, noindex tags and structured data.
   - Check them against `data/index-allow.json` and `data/waves.csv`: a live page Google can't see, or a noindex page listed in the sitemap.
   - Find near-duplicate and doorway pages (owner decision 4).
   - Use the `seo-technical` and `seo-google` skills. Read Search Console with `tools/gsc_read.py` and index coverage with `tools/index_inspect.py` if the key works.
   - Name which pages get impressions but no clicks, and why.

4. **Speed and weight**
   - Lighthouse on mobile for 3 page kinds (`dryrun.yml -f speed=` artifact, if one already exists; otherwise "unverified").
   - Compressed HTML size against `MAX_GZ`.
   - Ads and Analytics must load after the page is readable.
   - Use the `web-perf` skill.

5. **Pipeline (does it run alone for weeks?)**
   - Read the four workflows, `refresh.py`, `collect.py`, `build.py`, `gates.py` and `tools/watchdog.py`.
   - For each step: what happens when it fails silently, what the owner sees, and whether it heals.
   - Find steps that never run (like the release steps found 2026-11-10), rules copied in two places, and jobs that report green while failing.
   - Use the `ledger` in `status.json` for run time. Name the first limit to break, with its number, among:
     - 45-minute brake;
     - Cloudflare: 20,000 files, 1,000 KV writes a day, 100,000 requests a day, 10 ms CPU;
     - GitHub minutes;
     - USGS key quota.

6. **Code shape (where it is more complicated than it needs to be)**
   - Run the `improve-codebase-architecture` steps: hot spots from `git log`, the deletion test, shallow modules and drift between copies.
   - Then `ponytail-audit`: dead files, functions nothing calls, and code that re-does what the standard library already does.
   - Start from the newest report (`tools/full_audit_last.md`) and say which of its items are done.

7. **Safety and terms**
   - Use the `security-review` skill on the repo: keys in pages, commits or logs; the Worker reading anything it must not (no cloaking: CLAUDE.md "System rules"); and what the GitHub token can do.
   - For every source shown on a page:
     - its `data/sources.json` row says `quoted`, with the terms quoted;
     - no source whose terms bar ads, commercial use or caching (`check.py` `reuse_barred`);
     - credit lines are present.
   - Privacy: consent by location, and the same tags on every indexable page.

8. **Money and demand**
   - Is the queue order (`tools/release.py` `RATE`, searches times ad rate) built on numbers less than 30 days old?
   - Which live pages have earned impressions?
   - Which page kinds have none after 6 weeks (PLAN 0l)?
   - What is the next country or kind by money, and is it blocked?
   - Read PLAN.md "Drawing board" items 1-9: state, owner and next action for each, each with a measured number.

## Then (Claude, in this session)
1. Merge the findings. Drop duplicates and anything without proof. Check the top 5 FIX items yourself with one read each.
2. Write `tools/full_audit_last.md`: date, one line per finding, ranked by harm to readers first, then money, then owner time. Overwrite the previous one: one file, never a pile of them.
3. Make the report a visual page (as in improve-codebase-architecture: a card per finding) and send it to the owner.
4. Put each FIX, DELETE and SIMPLIFY item into PLAN.md with "Edge cases:" lines, then start the top one at once (CLAUDE.md: keep going).
