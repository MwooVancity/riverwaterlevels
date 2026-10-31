# Report fixtures: real gauge caches pushed into each USGS edge state and rendered by the real page code, nothing written to the project.
import copy, datetime, json, os, re, sys, traceback, html as H
ROOT = "C:/Users/mwoo7/Desktop/riverwaterlevels"
sys.path.insert(0, ROOT)
os.chdir(ROOT)
sys.stdout.reconfigure(encoding="utf-8")
src = open("tools/break_blocks.py", encoding="utf-8").read()
src = src[:src.index("def main():")]
g_ = {"__file__": ROOT + "/tools/break_blocks.py", "__name__": "bb"}
exec(compile(src, "bb", "exec"), g_)
render, load_effective, related, page_faults, load_cache = g_["render"], g_["load_effective"], g_["related"], g_["page_faults"], g_["load_cache"]
rows, _ = load_effective()
SITES = sys.argv[1:] or ["02336000"]


def dt(s):
    return datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))


def rows_of(rec, c):
    return [r for r in rec["usgs"]["rows"] if r["parameter_code"] == c]


def last_n(rec, c, hours):
    rs = rows_of(rec, c)
    end = max(dt(r["time"]) for r in rs)
    return [r for r in rs if dt(r["time"]) > end - datetime.timedelta(hours=hours)]


def setv(rec, hours, v, q=None, c="00060"):
    for r in last_n(rec, c, hours):
        r["value"] = v
        r["qualifier"] = q


def drop(rec, c):
    rec["usgs"]["rows"] = [r for r in rec["usgs"]["rows"] if r["parameter_code"] != c]


def ice_gone(rec, hours):
    keep = set(id(r) for r in last_n(rec, "00060", hours))
    rec["usgs"]["rows"] = [r for r in rec["usgs"]["rows"] if id(r) not in keep]


def alln(rec, q):
    for r in rows_of(rec, "00060"):
        r["value"] = None
        r["qualifier"] = q


S = {
    "unbroken": (lambda r: None, 0),
    "zero flow 3 days": (lambda r: setv(r, 72, "0"), 0),
    "zero flow, flagged ZEROFLOW": (lambda r: setv(r, 72, "0", ["ZEROFLOW"]), 0),
    "dry, flagged DRY": (lambda r: setv(r, 24, "0", ["DRY"]), 0),
    "negative flow": (lambda r: setv(r, 6, "-45"), 0),
    "drop to zero in 6 h": (lambda r: setv(r, 6, "0"), 0),
    "ICE flag, value kept": (lambda r: setv(r, 24, "150", ["ICE"]), 0),
    "ICE, value null 2 days": (lambda r: setv(r, 48, None, ["ICE"]), 0),
    "ICE, no flow rows 2 days": (lambda r: ice_gone(r, 48), 2),
    "ICE, no flow rows 8 days": (lambda r: ice_gone(r, 200), 0),
    "ICE, every flow null": (lambda r: alln(r, ["ICE"]), 0),
    "stage only": (lambda r: drop(r, "00060"), 0),
    "flow only": (lambda r: drop(r, "00065"), 0),
    "reading 25 h old": (lambda r: None, 25),
    "reading 4 days old": (lambda r: None, 96),
    "reading 29 days old": (lambda r: None, 24 * 29),
    "reading 31 days old": (lambda r: None, 24 * 31),
    "DISCONTINUED flag": (lambda r: setv(r, 3, "500", ["DISCONTINUED"]), 0),
    "BACKWATER flag": (lambda r: setv(r, 3, "500", ["BACKWATER"]), 0),
    "DAMFAILURE flag": (lambda r: setv(r, 3, "500", ["DAMFAILURE"]), 0),
    "BLWMIN flag": (lambda r: setv(r, 3, "1", ["BLWMIN"]), 0),
    "LESSTHAN flag": (lambda r: setv(r, 3, "1", ["LESSTHAN"]), 0),
    "FLOOD flag": (lambda r: setv(r, 3, "9000", ["FLOOD"]), 0),
    "TIDE flag": (lambda r: setv(r, 3, "500", ["TIDE"]), 0),
    "huge spike x100": (lambda r: setv(r, 1, "999999"), 0),
    "sentinel -999999": (lambda r: setv(r, 1, "-999999"), 0),
}
for s in SITES:
    base = load_cache(s)
    end = max(dt(r["time"]) for r in rows_of(base, "00060"))
    print("=====", s, rows[s]["river"], rows[s]["place"], "cache end", end)
    for name, (mut, shift) in S.items():
        rec = copy.deepcopy(base)
        mut(rec)
        now = end + datetime.timedelta(minutes=20) + datetime.timedelta(hours=shift)
        try:
            G = render.ctx(s, rows[s], rec, now)
            faults, secs = page_faults(G, rows)
            hero = render.build_tab("dashboard", G, rows)[0]
            hero = hero[hero.find("<h1"):]
            t = re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style|svg)\b.*?</\1>", " ", hero, flags=re.S))))
            print("%-30s ok  faults=%d %s\n    %s" % (name, len(faults), sorted(faults)[:3], t[60:420]))
        except render.CriticalFail as e:
            print("%-30s PAGE NOT BUILT: %s" % (name, e))
        except Exception as e:
            print("%-30s CRASH %s %s" % (name, type(e).__name__, str(e)[:120]))
