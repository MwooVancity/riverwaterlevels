"""Merge the collect shards' files into the restored cache (sharded.yml, finish job).
Usage: python -I tools/merge_shards.py SHARDS_DIR N     SHARDS_DIR holds shard-0 .. shard-(N-1), each with cache/*.json, health.json, timing.json
A shard whose folder is missing (its job failed) keeps its gauges' old cache files and is named in the log. A gauge file written by two shards is named too. state-XX.json (statewide hubs) may come from several shards: the one without an error, newest first, wins.
state/source-health.json: the run's counts are summed over shards, last_ok_at / last_fail_at take the latest. Prints the failure rate per source.
"""
import sys, os, json, shutil

d, n = sys.argv[1], int(sys.argv[2])
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cache = os.path.join(ROOT, "cache")
os.makedirs(cache, exist_ok=True)
failed, owner, copied, diffs = [], {}, 0, []
sum_, last = {}, {}
base = {}
hp = os.path.join(ROOT, "state", "source-health.json")
try:
    base = json.load(open(hp)).get("sources") or {}
except Exception:
    pass


def hub_ok(path):
    try:
        j = json.load(open(path))
        return not (j.get("alerts_err") or j.get("drought_err")), j.get("fetched_at") or ""
    except Exception:
        return False, ""


for i in range(n):
    sh = os.path.join(d, "shard-%d" % i)
    if not os.path.isdir(os.path.join(sh, "cache")):
        failed.append(i)
        continue
    for f in sorted(os.listdir(os.path.join(sh, "cache"))):
        src, dst = os.path.join(sh, "cache", f), os.path.join(cache, f)
        if f.startswith("state-"):
            if os.path.exists(dst) and f in owner and hub_ok(dst) >= hub_ok(src):
                continue
        elif f in owner:
            diffs.append("%s written by shards %d and %d" % (f, owner[f], i))
            continue
        shutil.copy(src, dst)
        owner[f] = i
        copied += 1
    try:
        h = json.load(open(os.path.join(sh, "health.json")))
    except Exception:
        diffs.append("shard %d: no health.json" % i)
        continue
    for k, s in (h.get("sources") or {}).items():
        lr = s.get("last_run") or {}
        if lr.get("at") != h.get("at"):
            continue  # not run by this shard (carried over from the cache it started with)
        a = sum_.setdefault(k, {"ok": 0, "absent": 0, "failed": 0, "at": h["at"], "mode": "run"})
        for c in ("ok", "absent", "failed"):
            a[c] += lr.get(c, 0)
        a["at"] = max(a["at"], h["at"])
        if s.get("last_ok_at"):
            last.setdefault(k, {})["last_ok_at"] = max(last.get(k, {}).get("last_ok_at", ""), s["last_ok_at"])
        if lr.get("failed") and s.get("last_fail_at", "") >= last.get(k, {}).get("last_fail_at", ""):
            last.setdefault(k, {}).update(last_fail_at=s["last_fail_at"], last_error=s.get("last_error", ""))
out = dict(base)
for k, a in sum_.items():
    e = {x: y for x, y in (base.get(k) or {}).items() if x in ("last_ok_at", "last_fail_at", "last_error")}
    e.update(last.get(k, {}))
    e["last_run"] = a
    out[k] = e
if sum_:
    at = max(a["at"] for a in sum_.values())
    os.makedirs(os.path.dirname(hp), exist_ok=True)
    json.dump({"at": at, "mode": "run", "attempted": max((a["ok"] + a["absent"] + a["failed"] for k, a in sum_.items() if k == "usgs"), default=0), "sources": out}, open(hp, "w"), indent=1)
print("merged %d files from %d of %d shards" % (copied, n - len(failed), n))
if failed:
    print("SHARDS THAT FAILED (their gauges keep the old cache files): %s" % ", ".join(map(str, failed)))
for x in diffs:
    print("NOTE " + x)
print("source outcomes this run (failed / total):")
for k, a in sorted(sum_.items(), key=lambda kv: -kv[1]["failed"]):
    t = a["ok"] + a["absent"] + a["failed"]
    print("  %-14s %5d / %5d  %5.2f%%  %s" % (k, a["failed"], t, 100.0 * a["failed"] / max(1, t), (last.get(k, {}).get("last_error", "") if a["failed"] else "")[:60]))
sys.exit(0)
