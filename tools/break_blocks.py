"""Break every input on purpose (owner 2026-10-28: "scrutinize the template for every failure case possible").
For each gauge, each top-level data source in its cache is pushed into a failure state (missing, stale by 26 h, empty lists,
duplicated list items, numbers set to None) and the gauge page is rendered again in memory. Every page check, hater rule and
block crash that the variant adds over the unbroken page is a finding, grouped by source, failure state and message.
Also prints the link map: block function -> cache sources it reads.
Usage: python -I tools/break_blocks.py [site ...]   (default: a feature-covering sample). Reads cache/ only, writes nothing."""
import ast, copy, collections, datetime, json, os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from lib.common import *
from lib.pages import load_effective
from lib import render, related

ck = {"__file__": os.path.join(ROOT, "check.py"), "__name__": "check"}
exec(compile(open("check.py", encoding="utf-8").read().rsplit("\nmain()", 1)[0], "check.py", "exec"), ck)


def link_map():
    out = collections.defaultdict(set)
    for f in glob.glob("lib/*.py"):
        for fn in ast.walk(ast.parse(open(f, encoding="utf-8").read())):
            if isinstance(fn, ast.FunctionDef) and (fn.name.startswith("b_") or fn.name in ("hero", "conditions", "next_impact")):
                for n in ast.walk(fn):  # G["rec"].get("x") or G["rec"]["x"] or rec.get("x")
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get" and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
                        src = ast.unparse(n.func.value)
                        if src in ('G["rec"]', "rec"):
                            out[fn.name].add(n.args[0].value)
                    if isinstance(n, ast.Subscript) and ast.unparse(n.value) in ('G["rec"]', "rec") and isinstance(n.slice, ast.Constant):
                        out[fn.name].add(n.slice.value)
    return out


ISO = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d")


def walk(o, f):
    if isinstance(o, dict):
        return {k: walk(v, f) for k, v in o.items()}
    if isinstance(o, list):
        return f(o, "list") if f(None, "probe-list") else [walk(v, f) for v in o]
    return f(o, "leaf")


def stale(o):
    def f(v, kind):
        if kind == "probe-list":
            return False
        if kind == "leaf" and isinstance(v, str) and ISO.match(v):
            try:
                return (datetime.datetime.fromisoformat(v.replace("Z", "+00:00")) - datetime.timedelta(hours=26)).isoformat()
            except ValueError:
                return v
        return v
    return walk(o, f)


def empty(o):
    return walk(o, lambda v, kind: (kind == "probe-list") or ([] if kind == "list" else v))


def dup(o):
    return walk(o, lambda v, kind: (kind == "probe-list") or ((v + v) if kind == "list" else v))


def nulls(o):
    return walk(o, lambda v, kind: False if kind == "probe-list" else (None if kind == "leaf" and isinstance(v, (int, float)) and not isinstance(v, bool) else v))


MUT = {"missing": None, "stale26h": stale, "empty": empty, "dup": dup, "nulls": nulls}


def page_faults(G, rows):
    n0 = len(render.BLOCK_ERRORS)
    try:
        h, meta = render.build_tab("dashboard", G, rows)
    except Exception as e:
        return {"PAGE CRASH %s: %s" % (type(e).__name__, str(e)[:80])}, {}
    rel = meta["url"].strip("/") + "/index.html"
    bad = set(ck["check_html"](h, rel) + ck["rank_checks"](h, meta["url"]) + ck["hater_rules"](h))
    bad |= {"BLOCK CRASH " + e.split(": ", 1)[1][:90] for e in render.BLOCK_ERRORS[n0:]}
    secs = {m.group(1): ("t-live" in m.group(2), "tag amber" in m.group(2) or "older than 24 h" in m.group(2), re.sub(r"<[^>]+>|\s+", " ", m.group(2))) for m in re.finditer(r'<section[^>]*id="([a-z_]+)"[^>]*>(.*?)</section>', h, re.S)}
    return {re.sub(r"\d[\d.,]*", "N", b)[:140] for b in bad}, secs


GATE = "--gate" in sys.argv  # gates.py: realistic failures only (missing, stale, empty, duplicated); exit 1 on a page crash, a printed None or own stale readings badged live


def main():
    if GATE:
        for k in ("nulls",):
            MUT.pop(k)
    else:
        lm = link_map()
        print("LINK MAP (block -> cache sources):")
        for b in sorted(lm):
            print("  %-22s %s" % (b, ", ".join(sorted(lm[b]))))
    rows, _ = load_effective()
    now = datetime.datetime.now(datetime.timezone.utc)
    want = [a for a in sys.argv[1:] if not a.startswith("--")]
    if GATE and not want:
        want = [s for s in ("07032000", "13206000", "01426500", "06461500") if os.path.exists(os.path.join(CACHE, s + ".json"))]
    sites = want or ["06461500", "03466500", "07032000", "06893000", "13206000", "01570500", "14105700", "01426500", "08169000", "02336000", "05082500", "12194000"]
    Gs, recs = {}, {}
    for s in sites:
        recs[s] = load_cache(s)
        Gs[s] = render.ctx(s, rows[s], copy.deepcopy(recs[s]), now)
    related.close(Gs, iso)
    for s, g in Gs.items():
        rows[s].update({"_built": True, "_ll": (g["lat"], g["lon"]), "_lv": g["lv"], "_band": band_word(g["p"]), "_hub": False, "_single": True})
    found = collections.defaultdict(set)
    n = 0
    for s in sites:
        base, bsecs = page_faults(Gs[s], rows)
        for key in sorted(k for k in recs[s] if not k.startswith("_") and k not in ("lat", "lon", "river_name")):
            for mname, mf in MUT.items():
                rec = copy.deepcopy(recs[s])
                if mf is None:
                    rec.pop(key)
                else:
                    rec[key] = mf(rec[key])
                try:
                    G = render.ctx(s, rows[s], rec, now)
                    faults, secs = page_faults(G, rows)
                    faults -= base
                    if mname == "stale26h" and key == "usgs":  # oracle: a block whose content moved with the 26-h-old data must not still claim live without an age warning
                        faults |= {"STALE SHOWN LIVE in block %s" % b for b, (lv, am, tx) in secs.items() if lv and not am and b in bsecs and tx != bsecs[b][2]}
                except render.CriticalFail:
                    faults = set()  # the gauge is skipped and its previous page stays: correct
                except Exception as e:
                    faults = {"CTX CRASH %s: %s" % (type(e).__name__, str(e)[:80])}
                n += 1
                for f_ in faults:
                    found[(key, mname, f_)].add(s)
    print("\n%d broken variants rendered over %d gauges; %d distinct faults" % (n, len(sites), len(found)))
    for (key, mname, f_), ss in sorted(found.items(), key=lambda x: (-len(x[1]), x[0])):
        print("%2d gauges | %-12s %-9s | %s | e.g. %s" % (len(ss), key, mname, f_, sorted(ss)[0]))
    if GATE:
        hard = [k for k in found if not k[2].startswith("BLOCK CRASH")]  # a crashed block is hidden by the guard and listed in status.json; a crashed page, a printed None or own stale readings badged live reach the reader
        print("break gate: %d reader-visible fault(s)" % len(hard))
        sys.exit(1 if hard else 0)


if __name__ == "__main__":
    main()
