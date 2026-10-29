"""Shadow collect check (collect-shadow.yml): compare the shadow run's cache with the cache it started from, gauge by gauge.
Usage: python -I tools/shadow_compare.py BASE_DIR NEW_DIR SITES_FILE BASE_HEALTH NEW_HEALTH OUT.json
Per gauge: (1) every source the base record has, the new record has; (2) newest USGS reading not older than the base's by more than 1 h;
(3) USGS row count within 5%; per source: no failure count the base run did not have. Writes the counts and the failing gauges to OUT.json.
"""
import sys, os, json, datetime

base, new, sites_file, hb, hn, out = sys.argv[1:7]
SKIP = {"fetched_at", "_fetched", "site", "tz", "stats_source", "alerts"}  # alerts come and go with the weather: absent in one run is not a lost source


def keys(rec):
    ks = set()
    for k, v in rec.items():
        if k in SKIP or not v:
            continue
        ks.add(k)
        if isinstance(v, dict):
            ks.update("%s.%s" % (k, kk) for kk, vv in v.items() if vv and kk not in SKIP and kk != "fetched_at")
    return ks


def newest(rec):
    ts = [r["time"] for r in (rec.get("usgs") or {}).get("rows") or [] if r.get("time")]
    return datetime.datetime.fromisoformat(max(ts).replace("Z", "+00:00")) if ts else None


res = {"gauges": 0, "missing_source": {}, "stale": [], "rows_off": [], "new_gauge": [], "unreadable": []}
for s in [l.strip() for l in open(sites_file) if l.strip()]:
    pb, pn = os.path.join(base, s + ".json"), os.path.join(new, s + ".json")
    if not os.path.exists(pn):
        res["unreadable"].append(s)
        continue
    if not os.path.exists(pb):
        res["new_gauge"].append(s)  # no base record (fake queue gauges): nothing to compare
        continue
    try:
        b, n = json.load(open(pb)), json.load(open(pn))
    except Exception as e:
        res["unreadable"].append("%s %s" % (s, e))
        continue
    res["gauges"] += 1
    for k in sorted(keys(b) - keys(n)):
        res["missing_source"].setdefault(k, []).append(s)
    tb, tn = newest(b), newest(n)
    if tb and (not tn or (tb - tn).total_seconds() > 3600):
        res["stale"].append(s)
    rb, rn = len((b.get("usgs") or {}).get("rows") or []), len((n.get("usgs") or {}).get("rows") or [])
    if rb and abs(rn - rb) / rb > 0.05:
        res["rows_off"].append("%s %d->%d" % (s, rb, rn))
bh = (json.load(open(hb)).get("sources") or {}) if os.path.exists(hb) else {}
nh = (json.load(open(hn)).get("sources") or {})
res["new_failures"] = {}
for src, v in nh.items():
    lr = v.get("last_run") or {}
    if lr.get("mode") != "run" or not lr.get("failed"):
        continue
    ob = ((bh.get(src) or {}).get("last_run") or {})
    tot, otot = lr["ok"] + lr["absent"] + lr["failed"], max(1, ob.get("ok", 0) + ob.get("absent", 0) + ob.get("failed", 0))
    if lr["failed"] / tot > ob.get("failed", 0) / otot + 0.05:
        res["new_failures"][src] = "%d of %d failed (base run %d of %d) %s" % (lr["failed"], tot, ob.get("failed", 0), otot, v.get("last_error", ""))
res["ok"] = not (res["missing_source"] or res["stale"] or res["rows_off"] or res["new_failures"] or res["unreadable"])
json.dump(res, open(out, "w"), indent=1)
print("compared %d gauges: missing-source keys %d, stale %d, rows off %d, new failures %d, unreadable %d, no-base %d -> %s" % (
    res["gauges"], len(res["missing_source"]), len(res["stale"]), len(res["rows_off"]), len(res["new_failures"]), len(res["unreadable"]), len(res["new_gauge"]), "OK" if res["ok"] else "DIFF"))
