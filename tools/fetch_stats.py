"""Download USGS daily discharge percentile statistics for live gauges that have no legacy/stats/<site>.json yet (keyless).
New gauges had none, so "is this normal" showed "-" while the page held 100 years of data (hater 2026-10-27, wave 3: 6 of 6 pages).
Usage: python -I tools/fetch_stats.py [site ...]   (default: every live gauge without a stats file). release.py runs it for each wave.
Output format (read by collect.py): {"d": {"MM-DD": [years, p05, p10, p20, p25, p50, p75, p80, p90, p95]}}
ponytail: legacy waterservices stat service; move to the Water Data API statistics endpoint when USGS retires it."""
import csv, json, os, sys, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "legacy", "stats")
PK = ["p05_va", "p10_va", "p20_va", "p25_va", "p50_va", "p75_va", "p80_va", "p90_va", "p95_va"]
URL = "https://waterservices.usgs.gov/nwis/stat/?format=rdb&sites=%s&statReportType=daily&statTypeCd=all&parameterCd=00060"


def get(u):
    for a in range(4):
        try:
            return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "riverwaterlevels.com stats"}), timeout=240).read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                return ""
        except Exception:
            pass
        time.sleep(3 * (a + 1))
    return None  # failed, as opposed to "" (USGS answered: no statistics)


def parse(t):
    hdr, out = None, {}
    for l in t.split("\n"):
        if not l or l.startswith("#"):
            continue
        c = l.split("\t")
        if c[0] == "agency_cd":
            hdr = c
            continue
        if hdr is None or c[0].startswith("5s"):
            continue
        r = dict(zip(hdr, c))
        if r.get("parameter_cd") != "00060":
            continue
        vals = [float(r[k]) if r.get(k) not in (None, "") else None for k in PK]
        if vals[4] is None:
            continue
        out.setdefault(r["site_no"], {})["%02d-%02d" % (int(r["month_nu"]), int(r["day_nu"]))] = [int(r.get("count_nu") or 0)] + vals
    return out


def main():
    want = [a for a in sys.argv[1:] if not a.startswith("--")] or [r["site"] for r in csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8")) if r["status"] == "live"]
    todo = [s for s in want if not os.path.exists(os.path.join(OUT, s + ".json"))]
    os.makedirs(OUT, exist_ok=True)
    got, failed = {}, []
    for i in range(0, len(todo), 20):
        t = get(URL % ",".join(todo[i:i + 20]))
        if t is None:
            failed += todo[i:i + 20]
        else:
            got.update(parse(t))
    for s, d in got.items():
        json.dump({"d": d}, open(os.path.join(OUT, s + ".json"), "w"), separators=(",", ":"))
    print("stats: %d needed, %d downloaded, none published for: %s; download failed for: %s" % (len(todo), len(got), " ".join(s for s in todo if s not in got and s not in failed) or "none", " ".join(failed) or "none"))


if __name__ == "__main__":
    assert parse("agency_cd\tsite_no\tparameter_cd\tmonth_nu\tday_nu\tcount_nu\t" + "\t".join(PK) + "\n5s\t15s\n" + "USGS\t01\t00060\t1\t2\t30\t" + "\t".join(str(x) for x in range(9)))["01"]["01-02"] == [30] + [float(x) for x in range(9)]
    main()
