# Corrections: public policy and internal process

## Public text (goes on the About page once the owner sets the contact; PLACEHOLDERS are owner-only)
"River Water Levels shows readings published by USGS and NOAA with their observation times. If a number on this site disagrees with the official source, email <CONTACT EMAIL, owner to set>. We check the page against the source, correct or hide it, and record the correction here. This site is not a flood warning service; for warnings use weather.gov."
Publisher: <PUBLISHER NAME, owner to set>.

## Internal process
1. Report arrives (email or tell Claude). Record: page, what was shown, what the source said, source time, time of report.
2. Reproduce with `python tools/truth_live.py` and the page. If the page is wrong or misleading: hide the page (`python tools/open_wave.py --pull <url>` and deploy) or fix and deploy; if only a block, the guard hides it.
3. Root cause is a layer, not a symptom; add a failing fixture to `truth_tests.py`, `truth_types.py` or `truth_fuzz.py` before closing.
4. Append one line to the table below. A wrong number that reached a reader without a visible age or source label is a stop event under `docs/INDEXING-RULES.md`.

| Date | Page | Shown | Source said | Cause | Fix and test |
|---|---|---|---|---|---|
| (none yet) | | | | | |
