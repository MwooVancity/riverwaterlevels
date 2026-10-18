"""Live-site watchdog: fails (so GitHub emails the owner) when the live data is stale or the site shrank.
Reads https://riverwaterlevels.com/status.json (written by build.py). Run by .github/workflows/watchdog.yml every hour; also works by hand: python tools/watchdog.py
Fail rules: build older than 3 h, median newest-reading age over 3 h, fewer pages than MIN_PAGES, status.json missing or unreadable."""
import json, sys, datetime, urllib.request

URL = "https://riverwaterlevels.com/status.json"
MAX_BUILD_AGE_MIN = 180
MAX_MEDIAN_AGE_MIN = 180
MIN_PAGES = 60  # raise as cohorts are released; a deploy that drops below this is a failure


def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (watchdog)"})
    try:
        s = json.load(urllib.request.urlopen(req, timeout=30))
    except Exception as e:
        print("WATCHDOG FAIL: cannot read %s: %s" % (URL, e))
        return 1
    built = datetime.datetime.fromisoformat(s["built_at"])
    age = (datetime.datetime.now(datetime.timezone.utc) - built).total_seconds() / 60
    bad = []
    if age > MAX_BUILD_AGE_MIN:
        bad.append("last build is %d min old (limit %d)" % (age, MAX_BUILD_AGE_MIN))
    if s["median_age_min"] > MAX_MEDIAN_AGE_MIN:
        bad.append("median newest-reading age is %d min (limit %d)" % (s["median_age_min"], MAX_MEDIAN_AGE_MIN))
    if s["pages"] < MIN_PAGES:
        bad.append("only %d pages (minimum %d)" % (s["pages"], MIN_PAGES))
    print("built %s (%d min ago), %d gauges, %d pages, median reading age %d min, oldest %d min" % (s["built_at"], age, s["gauges"], s["pages"], s["median_age_min"], s["oldest_age_min"]))
    for b in bad:
        print("WATCHDOG FAIL:", b)
    return 1 if bad else 0


sys.exit(main())
