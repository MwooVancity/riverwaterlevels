# Runbook: what you do when something breaks (plain steps, no coding)

You get an email from GitHub ("Run failed" / "watchdog") when something is wrong. Find the message below. If a step says "tell Claude", open Claude Code in this project and paste the one line.

## The site is up but a number looks wrong on a page
1. Do not wait. Tell Claude: "Wrong number on <page URL>: I see <what> and the official source says <what>." 
2. Claude pulls the page from the live release (`python tools/open_wave.py --pull <url>` hides it from Google; `python publish.py --rollback` restores the previous release) and finds the cause.
3. A correction is logged in `docs/CORRECTIONS.md`.

## Email: "watchdog failed"  (hourly check of the live site)
The email body lists the reason. Match it:
- **"last build is N min old"**: the deployer stopped. Open https://github.com/MwooVancity/riverwaterlevels/actions, click "refresh", press "Run workflow". If it fails again, tell Claude "refresh keeps failing".
- **"median newest-reading age"** or **"the oldest gauge reading is N min old"**: USGS has stopped sending for some gauges. Nothing to fix; the pages say how old their data is. Tell Claude only if it lasts over 12 h.
- **"only N pages"**: the site shrank. Tell Claude immediately; it may be a bad deploy (`python publish.py --rollback`).
- **"cannot read _truth.json"** or **"last verified ... ago"**: the check against USGS and NWS has not run. Run "refresh" manually (above). If USGS is rate-limiting it says so in the log.
- **"gauge page(s) kept their previous page because the build failed"**: one gauge's page could not be built; its old page stays up with its real age. Tell Claude the gauge id from the email.
- **"blocks were hidden by the guard"**: a section of a page failed to build. Tell Claude the page and block name from the email.

## Email: "Run failed" for the workflow "refresh"
Open the run, read the last red step, and tell Claude the step name. Common ones: "template_hash" (the template changed without a signed review, nothing to do but tell Claude), "truth_tests" (a number contradicts another on a page), "clip_all" or "ui_gates" (a layout problem on a template change).

## You see nothing wrong but Google traffic dropped
Do not change pages. Follow `docs/INDEXING-RULES.md` stop rules; tell Claude "traffic dropped" with the Search Console screenshot.

## Two deployers
Until the two Windows scheduled tasks are switched off, GitHub and your PC can both deploy. If the site flips between two versions, tell Claude "deployers racing". Do not switch the Windows tasks off before the outside monitor exists (GitHub schedules run only every 2 to 6 hours).

## Things only you can do
Publisher name and contact email; the corrections policy page; source-permission emails (Drought Monitor, NID, Reclamation, FEMA); a free outside uptime monitor (for example UptimeRobot) watching https://riverwaterlevels.com/status.json and https://riverwaterlevels.com/_truth.json; lifting noindex; real river users trying a page.
