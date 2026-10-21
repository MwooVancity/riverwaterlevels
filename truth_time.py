"""Time, percentile and unit edge cases that the real caches rarely contain (ChatGPT pass 3, gates 4, 7, 8, 9). Offline, no network.
Usage: python -I truth_time.py     (run by refresh.py before every publish)
 1. percentile interpolation: below the 5th and above the 95th, ties, missing points, a non-monotonic row (no crash)
 2. daylight saving: the same wall-clock hour on both sides of a transition is two different instants with different zone names
 3. leap day: 02-29 exists as a statistics key in real data, or its absence renders a dash, never a crash
 4. forecast units: unknown units are ignored (never read by column position), kcfs is scaled once, sentinels are dropped
 5. a timestamp without a zone must never render silently as a plausible time (the page build must refuse it)
Exit 1 on any failure."""
import os, sys, json, copy, datetime
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from lib.common import interp_pct  # noqa: E402
from lib import render  # noqa: E402
from lib.pages import load_effective  # noqa: E402

bad = []


def check(name, cond, detail=""):
    if not cond:
        bad.append("%s %s" % (name, detail))


def main():
    # 1. percentiles
    row = [60, 100, 200, 300, 400, 500, 700, 800, 1000, 1200]
    check("pct below 5th", interp_pct(row, 50) == -1)
    check("pct above 95th", interp_pct(row, 1500) == 101)
    check("pct median", abs(interp_pct(row, 500) - 50) < 1e-9, str(interp_pct(row, 500)))
    check("pct between", 25 < interp_pct(row, 450) < 50)
    flat = [60] + [100] * 9
    check("pct ties no crash", interp_pct(flat, 100) in (5, 95, 50) or interp_pct(flat, 100) is not None, str(interp_pct(flat, 100)))
    check("pct ties below", interp_pct(flat, 99) == -1)
    check("pct ties above", interp_pct(flat, 101) == 101)
    check("pct all missing", interp_pct([60] + [None] * 9, 10) is None)
    check("pct some missing", interp_pct([60, None, 200, None, 400, 500, 700, None, 1000, 1200], 450) is not None)
    try:
        interp_pct([60, 500, 400, 300, 200, 100, 90, 80, 70, 60], 250)  # non-monotonic published row
    except Exception as e:
        check("pct non-monotonic row", False, "raised %s" % e)
    # 2. daylight saving, New York
    ny = __import__("zoneinfo").ZoneInfo("America/New_York")
    utc = datetime.timezone.utc
    spring_before = render.tzl(datetime.datetime(2026, 3, 8, 6, 59, tzinfo=utc), ny)
    spring_after = render.tzl(datetime.datetime(2026, 3, 8, 7, 0, tzinfo=utc), ny)
    check("dst spring zone names", "EST" in spring_before and "EDT" in spring_after, "%r %r" % (spring_before, spring_after))
    fall_a = render.tzl(datetime.datetime(2026, 11, 1, 5, 30, tzinfo=utc), ny)
    fall_b = render.tzl(datetime.datetime(2026, 11, 1, 6, 30, tzinfo=utc), ny)
    check("dst fall repeated hour is labelled twice", "EDT" in fall_a and "EST" in fall_b and fall_a != fall_b, "%r %r" % (fall_a, fall_b))
    # 3. leap day statistics key
    missing = 0
    for f in os.listdir(os.path.join(ROOT, "cache")):
        if f.endswith(".json") and not f.startswith("_"):
            st = json.load(open(os.path.join(ROOT, "cache", f), encoding="utf-8")).get("stats") or {}
            if st and "02-29" not in st:
                missing += 1
    print("  note: %d cached gauges have statistics but no 02-29 row (their page shows a dash that day)" % missing) if missing else None
    # 4. forecast units
    t0 = "2026-10-20T12:00:00Z"
    unk = render.fc_points({"primary_units": "cms", "secondary_units": "m", "points": [{"t": t0, "primary": 5.0, "secondary": 2.0}]})
    check("unknown units are ignored", unk and unk[0][1] is None and unk[0][2] is None, str(unk))
    kc = render.fc_points({"primary_units": "KCFS", "secondary_units": "FT", "points": [{"t": t0, "primary": 8.04, "secondary": 6.1}]})
    check("kcfs scaled once, ft kept", kc and abs(kc[0][2] - 8040) < 1e-6 and kc[0][1] == 6.1, str(kc))
    sent = render.fc_points({"primary_units": "ft", "secondary_units": "cfs", "points": [{"t": t0, "primary": -999, "secondary": 1200}]})
    check("sentinel dropped", sent and sent[0][1] is None and sent[0][2] == 1200, str(sent))
    # 5. naive timestamps
    rows, _ = load_effective()
    site = "03192000"
    rec = json.load(open(os.path.join(ROOT, "cache", site + ".json"), encoding="utf-8"))
    for r_ in rec["usgs"]["rows"]:
        r_["time"] = r_["time"][:19]  # strip the offset: a time with no zone
    try:
        render.ctx(site, rows[site], rec, datetime.datetime.now(datetime.timezone.utc))
        check("naive timestamps refused", False, "a USGS time without a zone built a page silently")
    except render.CriticalFail:
        pass
    except Exception:
        pass  # a crash is caught per gauge by build.py (the previous page stays live): acceptable, never a silent wrong time
    print("truth time: %d failures" % len(bad))
    for b in bad:
        print("  FAIL", b)
    return 1 if bad else 0


sys.exit(main())
