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

import check  # a module since full audit #47 (its main() runs only as a script)
ck = vars(check)


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
            except (ValueError, OverflowError):  # CI 2026-10-29: a year-1 date in NWS data crashed the gate itself
                return v
        return v
    return walk(o, f)


def empty(o):
    return walk(o, lambda v, kind: (kind == "probe-list") or ([] if kind == "list" else v))


def dup(o):
    return walk(o, lambda v, kind: (kind == "probe-list") or ((v + v) if kind == "list" else v))


def nulls(o):
    return walk(o, lambda v, kind: False if kind == "probe-list" else (None if kind == "leaf" and isinstance(v, (int, float)) and not isinstance(v, bool) else v))


def flow_rows(f):
    """Gauge types the sample never had (open item D): change only the USGS flow rows (00060); every other source passes through."""
    def m(o):
        if not (isinstance(o, dict) and isinstance(o.get("rows"), list) and o["rows"] and isinstance(o["rows"][0], dict) and "parameter_code" in o["rows"][0]):
            return o
        o = copy.deepcopy(o)
        q = [r for r in o["rows"] if r.get("parameter_code") == "00060"]
        for i, r in enumerate(q):
            f(i, r)
        if f is irregular:
            o["rows"] = [r for r in o["rows"] if r.get("parameter_code") != "00060" or r.get("_keep")]
        return o
    return m


def ice(i, r):  # ice-affected: USGS keeps the stage, withholds flow
    r["value"], r["qualifier"] = None, "ICE"


def zero(i, r):  # dry wash or canal at zero: no division by zero in "% change"
    r["value"] = "0"


def tidal(i, r):  # estuary: flow reverses with the tide
    r["value"] = str(-abs(float(r["value"] or 0))) if i % 2 else r["value"]


def irregular(i, r):  # sampling gaps: an hour-long hole every few readings
    r["_keep"] = i % 7 in (0, 3)


MUT = {"missing": None, "stale26h": stale, "empty": empty, "dup": dup, "nulls": nulls,
       "ice": flow_rows(ice), "zeroflow": flow_rows(zero), "tidal": flow_rows(tidal), "irregular": flow_rows(irregular)}


def page_faults(G, rows):
    n0 = len(render.BLOCK_ERRORS)
    try:
        h, meta = render.build_tab("dashboard", G, rows)
        h = h.replace(" ", " ")  # as check.py reads built pages
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
    if GATE and not want:  # owner 2026-11-07: an edge-case practice run for every page type, not only US rivers (lakes and coasts crashed when dead 40 days)
        TYPES = {"US river": ("07032000", "13206000", "01426500", "06461500"), "US lake on USGS": ("02334400", "09379900"), "lake on CDEC": ("CDEC-SHA",),
                 "lake on Reclamation RISE": ("RISE-6123",), "lake on TWDB": ("TWDB-travis",), "Great Lake on NOAA CO-OPS": ("COOPS-9087031",), "coast on NOAA CO-OPS": ("9410170",)}
        for k_, ss in TYPES.items():
            have = [s for s in ss if os.path.exists(os.path.join(CACHE, s + ".json"))]
            print("type %-26s %s" % (k_, ", ".join(have) if have else "NOT TESTED: no cache file for %s" % ", ".join(ss)))
            want += have
        # ponytail: world pages (Canada, England, Germany) are built by lib/world.py from feed files, not render.ctx; they are tested by world fixtures and truth_world, not here
    sites = want or ["06461500", "03466500", "07032000", "06893000", "13206000", "01570500", "14105700", "01426500", "08169000", "02336000", "05082500", "12194000"]
    Gs, recs = {}, {}
    for s in sites:
        recs[s] = load_cache(s)
        Gs[s] = render.ctx(s, rows[s], copy.deepcopy(recs[s]), now)
    related.close(Gs, iso)
    for s, g in Gs.items():
        rows[s].update({"_built": True, "_ll": (g["lat"], g["lon"]), "_lv": dir_lv(g), "_band": band_word(g["p"]), "_hub": False, "_single": True})
    found = collections.defaultdict(set)
    base_of = {}
    n = 0
    for s in sites:
        base, bsecs = page_faults(Gs[s], rows)
        base_of[s] = base
        for f_ in base:
            if not f_.startswith("BLOCK CRASH"):
                found[("(unbroken page)", "none", f_)].add(s)
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
    for s in sites:  # ice: flow gone or a month old, stage still reporting; the gauge must keep a page that says so
        for label, keep in (("no flow", lambda t: False), ("old flow", lambda t: t < "2000")):
            rec = copy.deepcopy(recs[s])
            rec["usgs"]["rows"] = [r for r in rec["usgs"]["rows"] if r["parameter_code"] != "00060" or keep(r["time"])]
            if not any(r["parameter_code"] == "00065" for r in rec["usgs"]["rows"]):
                continue
            if label == "old flow":
                rec["usgs"]["rows"].append({"parameter_code": "00060", "time": "1999-01-01T00:00:00+00:00", "value": "500", "unit_of_measure": "ft^3/s", "qualifier": None})
                rec["usgs"]["rows"].sort(key=lambda r: r["time"])
            ice_now = datetime.datetime.fromisoformat(max(r["time"] for r in rec["usgs"]["rows"])) + datetime.timedelta(minutes=30)
            n0 = len(render.BLOCK_ERRORS)
            try:
                h = render.build_tab("dashboard", render.ctx(s, rows[s], rec, ice_now), rows)[0]
                bad = [] if re.search("Latest flow.{0,300}Not published", h, re.S) else ["ICE PAGE shows no Not published on the flow tile"]
                bad += ["ICE " + e for e in render.BLOCK_ERRORS[n0:] if e.split(": ")[1:2] and e.split(": ")[1] in render.SAFETY_BLOCKS]
            except Exception as e:
                bad = ["ICE CRASH %s: %s" % (type(e).__name__, str(e)[:80])]
            for f_ in bad:
                found[("usgs", label, f_)].add(s)
        try:  # dead: nothing for 40 days; the page says so with its real age instead of freezing as if current
            dead = render.ctx(s, rows[s], copy.deepcopy(recs[s]), datetime.datetime.fromisoformat(max(r["time"] for r in recs[s]["usgs"]["rows"])) + datetime.timedelta(days=40))
            if "gauge_not_reporting" not in render.build_tab("dashboard", dead, rows)[0]:
                found[("usgs", "dead 40 d", "DEAD PAGE has no not-reporting banner")].add(s)
        except Exception as e:
            found[("usgs", "dead 40 d", "DEAD CRASH %s: %s" % (type(e).__name__, str(e)[:80]))].add(s)
    for s in sites:  # owner 2026-11-07: clock-change nights. Every reading and the clock move together onto the US fall-back hour and the spring-forward hour; the page must render and pass every page rule
        newest = max((r["time"] for r in recs[s]["usgs"]["rows"]), default=None)
        if not newest:
            continue
        for label, target in (("DST fall-back", "2026-11-01T06:45:00+00:00"), ("DST spring-forward", "2027-03-14T07:45:00+00:00")):
            delta = datetime.datetime.fromisoformat(target) - datetime.datetime.fromisoformat(newest)
            def mv(v, kind, d_=delta):
                if kind == "probe-list":
                    return False
                if kind == "leaf" and isinstance(v, str) and ISO.match(v):
                    try:
                        return (datetime.datetime.fromisoformat(v.replace("Z", "+00:00")) + d_).isoformat()
                    except (ValueError, OverflowError):
                        return v
                return v
            n += 1
            try:
                G = render.ctx(s, rows[s], walk(copy.deepcopy(recs[s]), mv), now + delta)
                faults, _ = page_faults(G, rows)
                faults -= base_of.get(s, set())
            except render.CriticalFail:
                faults = set()
            except Exception as e:
                faults = {"DST CRASH %s: %s" % (type(e).__name__, str(e)[:80])}
            for f_ in faults:
                if not f_.startswith("BLOCK CRASH"):
                    found[("clock", label, f_)].add(s)
    if GATE and not [a for a in sys.argv[1:] if not a.startswith("--")]:  # owner 2026-11-07: world pages too (Canada, England, Germany river, Lake Constance), one gauge per page file
        from lib import world as world_
        wp_ = {p["slug"]: p for p in json.load(open(os.path.join(ROOT, "data", "world-pages.json"), encoding="utf-8"))}
        for slug in ("canada", "england", "rhine", "lake-constance"):
            f_ = os.path.join(CACHE, "_river-%s.json" % slug)
            rows_w = (json.load(open(f_, encoding="utf-8")).get("rows") or []) if os.path.exists(f_) else []
            if not rows_w or slug not in wp_:
                print("type world %-20s NOT TESTED: no cache file or page row" % slug)
                continue
            print("type world %-20s %s" % (slug, rows_w[0].get("name")))
            p_, r0 = wp_[slug], rows_w[0]

            def wfaults(r_):
                try:
                    got = world_.page(p_, r_, now, [r_], [r_.get("name")])
                except Exception as e:
                    return {"WORLD CRASH %s: %s" % (type(e).__name__, str(e)[:80])}
                if not got:
                    return set()  # held by the ship test: the live page stays, correct
                u_, h_ = got
                rel_ = u_.strip("/") + "/index.html"
                return set(ck["check_html"](h_.replace(" ", " "), rel_) + ck["world_rules"](h_) + ck["one_latest"](h_))
            base_w = wfaults(copy.deepcopy(r0))
            for key in sorted(k for k in r0 if k not in ("name", "title", "lat", "lon", "uuid", "number")):
                for mname, mf in MUT.items():
                    r_ = copy.deepcopy(r0)
                    if mf is None:
                        r_.pop(key)
                    else:
                        r_[key] = mf(r_[key])
                    n += 1
                    for f2 in wfaults(r_) - base_w:
                        found[("world:" + key, mname, f2)].add(slug)
    print("\n%d broken variants rendered over %d gauges; %d distinct faults" % (n, len(sites), len(found)))
    for (key, mname, f_), ss in sorted(found.items(), key=lambda x: (-len(x[1]), x[0])):
        print("%2d gauges | %-12s %-9s | %s | e.g. %s" % (len(ss), key, mname, f_, sorted(ss)[0]))
    if GATE:
        hard = [k for k in found if not k[2].startswith("BLOCK CRASH")]  # a crashed block is hidden by the guard and listed in status.json; a crashed page, a printed None or own stale readings badged live reach the reader
        print("break gate: %d reader-visible fault(s)" % len(hard))
        sys.exit(1 if hard else 0)


if __name__ == "__main__":
    main()
