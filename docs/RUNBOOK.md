# Runbook: what you do when something breaks, and how pages are opened to Google (plain steps, no coding)

You get an email from GitHub ("Run failed" / "watchdog") when something is wrong. Find the message below. If a step says "tell Claude", open Claude Code in this project and paste the one line.

## The site is up but a number looks wrong on a page
1. Do not wait. Tell Claude: "Wrong number on <page URL>: I see <what> and the official source says <what>."
2. Claude pulls the page from Google the same hour (`python -I tools/open_wave.py --pull <url>`), rolls back if needed (`python -I publish.py --rollback`) and finds the cause.
3. A correction is logged in `docs/CORRECTIONS.md`.

## Email: "watchdog failed" (hourly check of the live site)
The email body lists the reason. Match it:
- **"last build is N min old"**: the deployer stopped. Open https://github.com/MwooVancity/riverwaterlevels/actions, click "refresh", press "Run workflow". If it fails again, tell Claude "refresh keeps failing".
- **"median newest-reading age"** or **"the oldest gauge reading is N min old"**: USGS has stopped sending for some gauges. Nothing to fix; the pages say how old their data is. Tell Claude only if it lasts over 12 h.
- **"only N pages"**: the site shrank. Tell Claude immediately; it may be a bad deploy.
- **"cannot read _truth.json"** or **"last verified ... ago"**: the check against USGS and NWS has not run. Run "refresh" manually (above).
- **"gauge page(s) kept their previous page because the build failed"**: one gauge's page could not be built; its old page stays up with its real age. Tell Claude the gauge id from the email.
- **"blocks were hidden by the guard"**: a section of a page failed to build. Tell Claude the page and block name from the email.

## Email: "Run failed" for the workflow "refresh"
Open the run, read the last red step, and tell Claude the step name. Common ones: "check.py" (a page is missing a Source line or a unit), "truth_tests" (a number contradicts another on a page), "truth_live" (a built number differs from USGS or NWS). The live site stays on its last good release.

## You see nothing wrong but Google traffic dropped
Do not change pages. Tell Claude "traffic dropped" with the Search Console screenshot. Claude pulls pages with `open_wave.py --pull` only on a wrong or stale number, never to chase a traffic number.

## Indexing: which pages Google may see
The switch is `data/index-allow.json`: `open` (master), `site_pages` (home, state, about), `allow` (gauge page URLs). `lib/indexing.py` turns it into the robots tag and the sitemap; `check.py` refuses a build when the sitemap and the allow list disagree. `python -I tools/open_wave.py N` is a dry run of the next N pages; `--apply` writes them; `--pull <url>` removes one. `python -I tools/index_live.py` reads the live site after every deploy and reports any page whose tag disagrees with the list. You decide the pace (2026-10-21: all 25 pages and the site pages are open). Each opening is recorded in `docs/OPEN-ITEMS.md` with the date and URLs.

## Deployer
GitHub Actions `refresh.yml` is the only deployer (push to main, every 30 min fast, every 6 h full). The two Windows scheduled tasks are disabled (2026-10-20). If the site flips between two versions, tell Claude "deployers racing".

## Things only you can do
Publisher name and contact email; the corrections policy page; source-permission visits (USACE, TVA, Recreation.gov) and keys (USGS HIVIS cameras, Recreation.gov RIDB, AirNow); a free outside uptime monitor (for example UptimeRobot) watching https://riverwaterlevels.com/status.json and https://riverwaterlevels.com/_truth.json; Search Console verification; the consent banner before ads; running the gates when you have paused them.
