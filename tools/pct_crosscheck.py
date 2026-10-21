"""Independent percentile cross-check (prior art: DOI-USGS/hyswap does this kind of statistic; we compute it ourselves so nothing third-party is installed).
For a few gauges it downloads the USGS DAILY MEAN FLOW history, ranks the latest full day against the same calendar day (plus or minus 3 days) of every earlier year, and compares that EMPIRICAL percentile with the percentile our page shows (published USGS daily statistics, interpolated). A gap above TOL points means the statistics row, the date selection or the interpolation is wrong for that gauge.
Usage: python -I tools/pct_crosscheck.py [site ...]   (network; run by hand or nightly, not in the release chain)
Exit 1 when any sampled gauge differs by more than TOL percentile points."""
import os, sys, json, datetime, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lib.common import interp_pct, usgs_headers  # noqa: E402

TOL = 15.0  # empirical percentiles from 20 to 90 samples are noisy: a gap above this is a real mismatch
SAMPLE = ["03192000", "01358000", "09085000", "06041000", "02336000"]


def daily(site):
    url = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/daily/items?monitoring_location_id=USGS-%s&parameter_code=00060&statistic_id=00003&limit=50000&f=json" % site
    req = urllib.request.Request(url, headers=usgs_headers())
    d = json.load(urllib.request.urlopen(req, timeout=120))
    out = {}
    for f in d.get("features", []):
        p = f["properties"]
        try:
            out[datetime.date.fromisoformat(p["time"][:10])] = float(p["value"])
        except (KeyError, TypeError, ValueError):
            pass
    return out


def main():
    sites = [a for a in sys.argv[1:] if a.isdigit()] or SAMPLE
    bad = []
    for site in sites:
        cache = json.load(open(os.path.join(ROOT, "cache", site + ".json"), encoding="utf-8"))
        stats = cache.get("stats") or {}
        try:
            d = daily(site)
        except Exception as e:
            print("%s: USGS daily values unavailable (%s); skipped" % (site, str(e)[:60]))
            continue
        if not d:
            print("%s: no daily values; skipped" % site)
            continue
        last = max(d)
        v = d[last]
        peers = []
        for k, val in d.items():
            if k.year == last.year:
                continue
            try:
                same = k.replace(year=last.year)
            except ValueError:  # Feb 29 in a leap year compared with a non-leap year: skip that sample
                continue
            if abs((same - last).days) <= 3:
                peers.append(val)
        if len(peers) < 20:
            print("%s: only %d same-date samples; skipped" % (site, len(peers)))
            continue
        emp = 100.0 * sum(1 for x in peers if x < v) / len(peers) + 0.5 * 100.0 * sum(1 for x in peers if x == v) / len(peers)
        row = stats.get(last.strftime("%m-%d"))
        ours = interp_pct(row, v) if row else None
        if ours is None:
            print("%s: no statistics row for %s; skipped" % (site, last))
            continue
        ours_c = 0.0 if ours == -1 else 100.0 if ours == 101 else ours
        gap = abs(ours_c - emp)
        print("%s: daily mean %s cfs on %s; empirical percentile %.0f (n=%d), our interpolated percentile %.0f, gap %.0f" % (site, v, last, emp, len(peers), ours_c, gap))
        if gap > TOL:
            bad.append("%s gap %.0f > %.0f" % (site, gap, TOL))
    print("percentile cross-check: %d mismatches" % len(bad))
    for b in bad:
        print("  MISMATCH", b)
    return 1 if bad else 0


sys.exit(main())
