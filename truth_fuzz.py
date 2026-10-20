"""Shape fuzzer: every source's data can arrive empty, null, the wrong type or with a field missing. The page must still render honestly (or refuse with CriticalFail), never raise, never print None / NaN / undefined.
Usage: python -I truth_fuzz.py            quick: 4 diverse gauges, every top-level key set to 6 junk values, every nested key of every source removed once
       python -I truth_fuzz.py --deep     all gauges (slow, run by hand or nightly)
Offline: reads cache/ only. Prints each failing (gauge, key, junk) so a fix targets the block, not the symptom. Exit 1 on any failure."""
import os, sys, re, json, copy, datetime
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from lib import render  # noqa: E402
from lib.pages import load_effective  # noqa: E402

DEEP = "--deep" in sys.argv
KEEP = ("usgs", "site", "lat", "lon", "tz")  # without these a gauge is not a gauge: removing them is a refusal, tested in truth_types.py
JUNK = [("None", None), ("empty dict", {}), ("empty list", []), ("empty string", ""), ("zero", 0), ("string", "x")]
BAD = re.compile(r"\bNone\b|\bNaN\b|\bundefined\b|\binf\b|-999|Traceback|\{\{|\}\}|%s|%d")
SAMPLE = ["03192000", "11447650", "03294500"]  # ordinary with forecast, tidal, big river with alerts
fails = []
seen = [0, 0, 0]


def try_render(label, rows, site, rec, now):
    seen[0] += 1
    del render.BLOCK_ERRORS[:]
    try:
        G = render.ctx(site, rows[site], rec, now)
        html, _ = render.build_tab("dashboard", G, rows)
    except render.CriticalFail:
        seen[1] += 1
        return
    except Exception as e:
        fails.append("%s: raised %s: %s" % (label, type(e).__name__, str(e)[:110]))
        return
    seen[2] += len(render.BLOCK_ERRORS)
    text = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", html, flags=re.S)
    m = BAD.search(text)
    if m:
        fails.append("%s: page shows %r near %r" % (label, m.group(0), re.sub(r"\s+", " ", text[max(0, m.start() - 45):m.end() + 30])))


def main():
    rows, _ = load_effective()
    now = datetime.datetime.now(datetime.timezone.utc)
    files = sorted(f[:-5] for f in os.listdir(os.path.join(ROOT, "cache")) if f.endswith(".json") and not f.startswith("_") and f[:-5] in rows)
    sites = files if DEEP else [s for s in SAMPLE if s in files] or files[:4]
    for site in sites:
        base = json.load(open(os.path.join(ROOT, "cache", site + ".json"), encoding="utf-8"))
        for key in [k for k in base if k not in KEEP]:
            for jname, jval in JUNK:
                rec = copy.deepcopy(base)
                rec[key] = jval
                try_render("%s: %s = %s" % (site, key, jname), rows, site, rec, now)
            if isinstance(base[key], dict):  # one nested field missing at a time: an API that renamed a field
                for sub in list(base[key]):
                    rec = copy.deepcopy(base)
                    del rec[key][sub]
                    try_render("%s: %s.%s removed" % (site, key, sub), rows, site, rec, now)
                    for jn, jv in (("None", None), ("string", "x"), ("empty list", []), ("empty dict", {}), ("number", 7)):
                        rec = copy.deepcopy(base)
                        rec[key][sub] = jv
                        try_render("%s: %s.%s = %s" % (site, key, sub, jn), rows, site, rec, now)
    print("truth fuzz: %d gauges, %d renders (%d refused as critical, %d blocks hidden by the guard), %d failures" % (len(sites), seen[0], seen[1], seen[2], len(fails)))
    for f in fails[:40]:
        print("  FAIL", f)
    if len(fails) > 40:
        print("  ... and %d more" % (len(fails) - 40))
    return 1 if fails else 0


sys.exit(main())
