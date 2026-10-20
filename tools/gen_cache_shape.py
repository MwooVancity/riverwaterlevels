"""Writes data/cache_shape.json: for every source record in cache/ and each field inside it, whether real data holds a list or a dict there.
lib/render.py ctx() uses it to treat a field of the wrong container type (an API that changed shape) as empty instead of crashing the page.
Usage: python -I tools/gen_cache_shape.py     (run after a collect when a new source or field was added; the file is committed because CI has no cache at checkout)"""
import json, os, collections, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
seen = collections.defaultdict(lambda: collections.defaultdict(set))
iso = {}
for f in os.listdir(os.path.join(ROOT, "cache")):
    if not f.endswith(".json") or f.startswith("_"):
        continue
    d = json.load(open(os.path.join(ROOT, "cache", f), encoding="utf-8"))
    for k, v in d.items():
        if isinstance(v, dict):
            for sk, sv in v.items():
                if sv is not None:
                    seen[k][sk].add("list" if isinstance(sv, list) else "dict" if isinstance(sv, dict) else "str" if isinstance(sv, str) else "num" if isinstance(sv, (int, float)) and not isinstance(sv, bool) else "scalar")
                    if isinstance(sv, str):
                        try:
                            datetime.datetime.fromisoformat(sv)
                            iso[(k, sk)] = iso.get((k, sk), True)
                        except ValueError:
                            iso[(k, sk)] = False
out = {k: {sk: ("iso" if next(iter(t)) == "str" and iso.get((k, sk)) else next(iter(t))) for sk, t in sub.items() if len(t) == 1 and next(iter(t)) in ("list", "dict", "str", "num")} for k, sub in seen.items()}
out = {k: v for k, v in out.items() if v}
json.dump(out, open(os.path.join(ROOT, "data", "cache_shape.json"), "w", encoding="utf-8"), indent=0, sort_keys=True)
print("cache_shape.json: %d sources, %d typed fields" % (len(out), sum(len(v) for v in out.values())))
