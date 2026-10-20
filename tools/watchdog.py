"""Live-site watchdog: fails (so GitHub emails the owner) when the live data is stale or the site shrank.
Reads https://riverwaterlevels.com/status.json (written by build.py). Run by .github/workflows/watchdog.yml every hour; also works by hand: python tools/watchdog.py
Fail rules: build older than 3 h, median newest-reading age over 3 h, fewer pages than MIN_PAGES, status.json missing or unreadable."""
import json, sys, datetime, urllib.request

URL = "https://riverwaterlevels.com/status.json"
MAX_BUILD_AGE_MIN = 180
MAX_MEDIAN_AGE_MIN = 180
MAX_UNVERIFIED_H = 6  # numbers not compared with USGS and NWS for this long fail the watchdog
MIN_PAGES = 40  # 49 after the Forecast pages were merged into the gauge pages (2026-10-18); raise as cohorts are released; a deploy that drops below this is a failure


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
    try:  # when were the numbers last checked against USGS and NWS (tools/truth_live.py writes _truth.json at every build)
        tr = json.load(urllib.request.urlopen(urllib.request.Request("https://riverwaterlevels.com/_truth.json", headers={"User-Agent": "Mozilla/5.0 (watchdog)"}), timeout=30))
        if tr.get("status") == "mismatch":
            bad.append("the build-time check against USGS and NWS found mismatches: %s" % tr.get("mismatches"))
        ok = tr.get("last_ok_at")
        ok_age = (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(ok)).total_seconds() / 3600 if ok else None
        if ok_age is None or ok_age > MAX_UNVERIFIED_H:
            bad.append("the numbers were last verified against USGS and NWS %s (limit %d h); the latest check was %s" % ("never" if ok_age is None else "%.1f h ago" % ok_age, MAX_UNVERIFIED_H, tr.get("status")))
    except Exception as e:
        print("watchdog note: no _truth.json yet (%s); expected only until the first build after this check was added" % str(e)[:60])
    print("built %s (%d min ago), %d gauges, %d pages, median reading age %d min, oldest %d min" % (s["built_at"], age, s["gauges"], s["pages"], s["median_age_min"], s["oldest_age_min"]))
    for b in bad:
        print("WATCHDOG FAIL:", b)
    return 1 if bad else 0


sys.exit(main())
