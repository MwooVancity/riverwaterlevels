"""Download USGS daily discharge percentile statistics for live gauges that have no legacy/stats/<site>.json yet.
New gauges had none, so "is this normal" showed "-" while the page held 100 years of data (hater 2026-10-27, wave 3: 6 of 6 pages).
Usage: python -I tools/fetch_stats.py [site ...]   (default: every live gauge without a stats file). release.py runs it for each wave.
Output format (read by collect.py): {"d": {"MM-DD": [years, p05, p10, p20, p25, p50, p75, p80, p90, p95]}}
Source: USGS Water Data API statistics, observationNormals (waterservices.usgs.gov degrades from November 2026 and retires 2027-02-22).
It publishes the 5/10/25/50/75/90/95th percentiles; p20 and p80 are stored as null and lib.common.interp_pct skips them (never interpolated as data)."""
import csv, json, os, sys, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "legacy", "stats")
SLOT = ["5", "10", "20", "25", "50", "75", "80", "90", "95"]
URL = "https://api.waterdata.usgs.gov/statistics/v0/observationNormals?monitoring_location_id=USGS-%s&parameter_code=00060&computation_type=percentile"


def get(u):
    h = {"User-Agent": "riverwaterlevels.com stats"}
    if os.environ.get("USGS_API_KEY"):
        h["X-Api-Key"] = os.environ["USGS_API_KEY"]
    for a in range(4):
        try:
            return urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=120).read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                return ""
        except Exception:
            pass
        time.sleep(3 * (a + 1))
    return None  # failed, as opposed to "" (USGS answered: no statistics)


def parse(t):
    """{"MM-DD": [years, p05 ... p95]} from the daily-mean discharge normals; {} when USGS has none."""
    out = {}
    for f in (json.loads(t).get("features") or []) if t else []:
        for s in f["properties"].get("data") or []:
            if s.get("parameter_code") != "00060" or s.get("parent_statistic_id") != "00003":  # daily mean flow only
                continue
            for v in s.get("values") or []:
                if v.get("time_of_year_type") != "day_of_year" or v.get("computation") != "percentile":
                    continue
                by = dict(zip(v.get("percentiles") or [], v.get("values") or []))
                row = [float(by[p]) if by.get(p) not in (None, "") else None for p in SLOT]
                if row[4] is not None:
                    out[v["time_of_year"]] = [int(v.get("sample_count") or 0)] + row
    return out


def main():
    want = [a for a in sys.argv[1:] if not a.startswith("--")] or [r["site"] for r in csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8")) if r["status"] == "live"]
    todo = [s for s in want if not os.path.exists(os.path.join(OUT, s + ".json"))] if "--all" not in sys.argv else want
    os.makedirs(OUT, exist_ok=True)
    got, failed, none = 0, [], []
    for s in todo:
        t = get(URL % s)
        if t is None:
            failed.append(s)
            continue
        d = parse(t)
        if not d:
            none.append(s)
            continue
        json.dump({"d": d, "src": "USGS Water Data API statistics/v0 observationNormals (full period of record; differs from the legacy NWIS statistics kept for older gauges)"}, open(os.path.join(OUT, s + ".json"), "w"), separators=(",", ":"))
        got += 1
    print("stats: %d needed, %d downloaded, none published for: %s; download failed for: %s" % (len(todo), got, " ".join(none) or "none", " ".join(failed) or "none"))


if __name__ == "__main__":
    _t = json.dumps({"features": [{"properties": {"data": [{"parameter_code": "00060", "parent_statistic_id": "00003", "values": [{"time_of_year": "10-28", "time_of_year_type": "day_of_year", "computation": "percentile", "sample_count": 113,
         "percentiles": ["5", "10", "25", "50", "75", "90", "95"], "values": ["69.0", "96.8", "203.0", "448.0", "1070.0", "1704.0", "2238.0"]}]}]}}]})
    assert parse(_t) == {"10-28": [113, 69.0, 96.8, None, 203.0, 448.0, 1070.0, None, 1704.0, 2238.0]}
    main()
