"""End-to-end safety tests for the slice. Usage: python -I tests.py
1. check.py selftest (good fixture passes, 5 broken fixtures fail)
2. determinism: two cache-only builds with the same clock give identical content hashes
3. forced source failure: a stale cache makes that page CRITICAL, the page is not rebuilt and dist/ keeps the last release
4. rollback: publish.py --rollback restores the previous release
"""
import os, sys, json, shutil, subprocess, hashlib, glob
ROOT = os.path.dirname(os.path.abspath(__file__))
PY = [sys.executable, "-I"]


def run(*a, env=None):
    e = dict(os.environ, **(env or {}))
    return subprocess.run(PY + list(a), cwd=ROOT, capture_output=True, text=True, env=e)


def hashes(d):
    return {os.path.relpath(p, d): hashlib.sha256(open(p, "rb").read()).hexdigest() for p in glob.glob(os.path.join(d, "**", "index.html"), recursive=True)}


def unit_checks():
    """Numbers and labels that a page must never get wrong: percentile interpolation, axis labels, place phrasing, blocks that must hide."""
    sys.path.insert(0, ROOT)
    import datetime
    from lib.common import interp_pct, river_at
    from lib import render
    from lib.render import tf, area_short
    from lib import blocks3
    row = [60, 100, 200, 300, 400, 500, 700, 800, 1000, 1200]  # years, then p5 p10 p20 p25 p50 p75 p80 p90 p95
    good = [
        interp_pct(row, 500) == 50,                      # exactly the median
        interp_pct(row, 50) == -1,                       # below the 5th percentile
        interp_pct(row, 5000) == 101,                    # above the 95th percentile
        20 < interp_pct(row, 350) < 25,                  # between p20 and p25
        tf(12.5, [2.5, 5.0, 7.5, 10.0, 12.5]) == "12.5",  # 12.5 is never printed as 12
        tf(0, [0, 1, 2]) == "0",
        river_at("Gauley River", "above Belva") == "Gauley River above Belva" or river_at("Gauley River", "Above Belva") == "Gauley River above Belva",
        river_at("Penns Creek", "Penns Creek") == "Penns Creek",
        river_at("Missouri River", "Kansas City") == "Missouri River at Kansas City",
        area_short("A; B; C; D; E; F; G; H", 6).endswith("and 2 more areas"),
        area_short("Linn; Union; Snyder", 6, "Union County").startswith("Union"),
    ]
    G = {"rec": {"floodfreq": {"rows": [{"aep": 1.0, "q": 1, "lo": None, "hi": None}], "regulated": True, "conflict": False}}}
    good.append(blocks3.b_floodfreq(G) is None)          # regulated gauge: no flood-frequency table
    G["rec"]["floodfreq"].update(regulated=False, conflict=True)
    good.append(blocks3.b_floodfreq(G) is None)          # conflicting preferred sets: no table
    return all(good), [i for i, g in enumerate(good) if not g]


def blocks_safety():
    """In-process: the final-form blocks return None on missing or stale data, and build_tab drops a block whose source status is not quoted/owner-permission."""
    import copy, datetime
    sys.path.insert(0, ROOT)
    from lib import render
    from lib.pages import load_effective
    rows, _ = load_effective()
    site = "06893000"
    rec = json.load(open(os.path.join(ROOT, "cache", site + ".json")))
    now = datetime.datetime.now(datetime.timezone.utc)
    G = render.ctx(site, rows[site], rec, now)
    good = True
    for k, f in (("multiyear", render.b_multiyear), ("peaks", render.b_peaks), ("wtemp", render.b_wtemp), ("snotel", render.b_snotel), ("cpc", render.b_cpc)):
        G2 = copy.deepcopy(G); G2["rec"][k] = None
        if k == "cpc":
            G2["rec"]["cpc610"] = None
        good &= f(G2) is None
    G2 = copy.deepcopy(G); G2["rec"]["nwps"] = {}
    good &= render.b_crests(G2) is None and render.b_impacts(G2) is None
    G2 = copy.deepcopy(G); G2["rec"]["nws"]["grid"] = {"updated": "2020-01-01T00:00:00+00:00", "hours": G2["rec"]["nws"]["grid"]["hours"]}
    good &= render.b_heatmap(G2) is None
    if G["rec"].get("cpc"):
        G2 = copy.deepcopy(G); G2["rec"]["cpc"]["issued"] = "01/01/2020"
        if G2["rec"].get("cpc610"):
            G2["rec"]["cpc610"]["issued"] = "01/01/2020"
        good &= render.b_cpc(G2) is None
    old = render.SOURCES["natmap"]["status"]
    try:
        render.SOURCES["natmap"]["status"] = "off"
        page, meta = render.build_tab("dashboard", G, rows)
        good &= "gauge_map" not in meta["blocks"]
    finally:
        render.SOURCES["natmap"]["status"] = old
    page, meta = render.build_tab("dashboard", G, rows)
    good &= "gauge_map" in meta["blocks"] and "data-site" in page
    G3 = copy.deepcopy(G); G3["offline"] = True; G3["age_min"] = 3 * 1440
    good &= render.b2.b_offline(G3) is not None and render.b2.b_offline(G) is None
    return bool(good)


def review_gate():
    """New gauge pages need a SHIP verdict; live pages and non-gauge pages are never blocked; GRANDFATHERED or FIX verdicts do not unlock a new page."""
    sys.path.insert(0, ROOT)
    import lib.reviewgate as rg
    rg.STRICT = False  # these checks are about which pages are held; signatures are tested in signed_review()
    from lib.reviewgate import unreviewed_new_pages as f
    live = ["/", "/river/a/b/", "/status/"]
    nxt = live + ["/river/c/d/", "/river/c/d/forecast/", "/status/x/", "/rivers/pa/"]
    rv = {"pages": {"/river/c/d/": {"verdict": "SHIP"}, "/river/c/d/forecast/": {"verdict": "HOLD"}}}
    from lib.reviewgate import hold_back
    rows = {"s1": {"dashboard_url": "/river/a/b/", "forecast_url": "/river/a/b/forecast/"}, "s2": {"dashboard_url": "/river/c/d/", "forecast_url": "/river/c/d/forecast/"}, "s3": {"dashboard_url": "/river/e/f/", "forecast_url": "/river/e/f/forecast/"}}
    held = hold_back(rows, ["/river/a/b/"], {"pages": {"/river/a/b/": {"verdict": "GRANDFATHERED"}, "/river/c/d/": {"verdict": "SHIP"}}}, {"s1", "s2"})
    return (f(nxt, live, {}) == ["/river/c/d/", "/river/c/d/forecast/"] and f(nxt, live, rv) == ["/river/c/d/forecast/"]
            and f(live, live, {}) == [] and f(nxt, nxt, {}) == []
            and f(["/river/g/h/"], live, {"pages": {"/river/g/h/": {"verdict": "GRANDFATHERED"}}}) == []
            and held == ({"s3"}, {"s1", "s2"}) and hold_back(rows, [], {}, None) == (set(), set()))


def signed_review():
    """A SHIP counts only when its signature matches the report file: an unsigned (hand-written) SHIP, a SHIP whose report was edited afterwards, and a SHIP for another URL are all refused."""
    sys.path.insert(0, ROOT)
    import lib.reviewgate as rg
    rg.STRICT = True
    rp = os.path.join("runs", "_test-review.md")
    open(os.path.join(ROOT, rp), "w", encoding="utf-8").write("verdict SHIP, no P0")
    good = {"verdict": "SHIP", "report": rp, "sig": rg.sign("SHIP", rp, "/river/x/y/")}
    res = (rg.is_ship(good, "/river/x/y/") and not rg.is_ship({"verdict": "SHIP", "report": rp}, "/river/x/y/") and not rg.is_ship(good, "/river/x/z/")
           and rg.is_ok({"verdict": "GRANDFATHERED"}, "/q/") and not rg.is_ship({"verdict": "HOLD", "report": rp, "sig": good["sig"]}, "/river/x/y/"))
    open(os.path.join(ROOT, rp), "w", encoding="utf-8").write("verdict SHIP, no P0 (edited)")
    res = res and not rg.is_ship(good, "/river/x/y/")
    os.remove(os.path.join(ROOT, rp))
    return res


def record_tools_import():
    """tools/record_review.py imports tools/template_hash.py: importing it must not end the process (it once did, so no verdict was ever written)."""
    r = subprocess.run([sys.executable, "-I", "-c", "import sys; sys.path.insert(0, 'tools'); import template_hash; print('imported')"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip() == "imported" and r.returncode == 0


def related_closure():
    """Upstream/downstream pairs found from one side only are listed on both pages; a pair with a gauge that is not on the site is left alone."""
    sys.path.insert(0, ROOT)
    from lib import related
    import datetime
    t = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    Gs = {"a": {"rec": {"related": {"items": [{"site": "b", "relation": "upstream", "flow": 5, "time": "x", "lag_h": 6, "lag_r": 0.9}, {"site": "zz", "relation": "downstream", "flow": 1, "time": "x"}]}}, "lv": 100, "lt": t},
          "b": {"rec": {}, "lv": 50, "lt": t}}
    before = related.check(Gs)
    added = related.close(Gs, lambda d: d.isoformat())
    row = Gs["b"]["rec"]["related"]["items"][0]
    return before == [("a", "b")] and added == 1 and row["site"] == "a" and row["relation"] == "downstream" and row["flow"] == 100 and row["lag_h"] == 6 and related.check(Gs) == [] and related.close(Gs, lambda d: d.isoformat()) == 0


def index_gate():
    """The per-batch kill switch: hold means nothing is indexable; open means only allowed gauge pages (and, with site_pages, the non-gauge pages); the production noindex header rule is dropped only when open."""
    sys.path.insert(0, ROOT)
    from lib import indexing as ix
    hold = {"open": False, "site_pages": False, "allow": set()}
    opn = {"open": True, "site_pages": False, "allow": {"/river/a/b/"}}
    sp = {"open": True, "site_pages": True, "allow": set()}
    tpl = open(os.path.join(ROOT, "templates", "_headers"), encoding="utf-8").read()
    return (not ix.indexable("/river/a/b/", hold) and not ix.indexable("/", hold)
            and ix.indexable("/river/a/b/", opn) and ix.indexable("/river/a/b/forecast/", opn) and not ix.indexable("/river/c/d/", opn) and not ix.indexable("/", opn)
            and ix.indexable("/", sp) and ix.indexable("/rivers/pa/", sp) and not ix.indexable("/river/c/d/", sp)
            and "X-Robots-Tag" in ix.headers(tpl, hold) and "riverwaterlevels.com/*" in ix.headers(tpl, hold)
            and "https://riverwaterlevels.com/*" not in ix.headers(tpl, opn) and "workers.dev" in ix.headers(tpl, opn) and "Strict-Transport-Security" in ix.headers(tpl, opn)
            and ix.sitemap_ok("/river/c/d/", hold) and not ix.sitemap_ok("/river/c/d/", opn))


def main():
    ok = True
    r = run("check.py", "--selftest"); print("1.", r.stdout.strip() or r.stderr.strip()[:200]); ok &= r.returncode == 0
    fixed = {"BUILD_NOW": "2026-10-16T23:00:00+00:00"}
    run("build.py", env=fixed); a = hashes(os.path.join(ROOT, "dist_next"))
    run("build.py", env=fixed); b = hashes(os.path.join(ROOT, "dist_next"))
    same = a == b and len(a) > 0
    print("2. determinism: %d pages, identical hashes on rebuild: %s" % (len(a), same)); ok &= same
    # 3. forced failure: age the Kinzua cache by 3 days
    site = "03011800"
    cp = os.path.join(ROOT, "cache", site + ".json")
    saved = open(cp, "rb").read()
    live_before = hashes(os.path.join(ROOT, "dist")).get(os.path.join("river", "kinzua-creek", "guffey", "index.html"))
    try:
        rec = json.loads(saved)
        for x in rec["usgs"]["rows"]:
            x["time"] = x["time"].replace("2026-10", "2026-08")
        json.dump(rec, open(cp, "w"))
        r = run("build.py", site, env={"BUILD_NOW": "2026-10-16T23:00:00+00:00"})
        crit = "CRITICAL" in r.stdout
        built = os.path.exists(os.path.join(ROOT, "dist_next", "river", "kinzua-creek", "guffey", "index.html"))
        live_after = hashes(os.path.join(ROOT, "dist")).get(os.path.join("river", "kinzua-creek", "guffey", "index.html"))
        good = crit and not built and live_before == live_after and live_before is not None
        print("3. forced stale source: critical flagged %s, page not rebuilt %s, live release unchanged %s" % (crit, not built, live_before == live_after)); ok &= good
    finally:
        open(cp, "wb").write(saved)
    # 4. rollback
    before = hashes(os.path.join(ROOT, "dist"))
    r = run("publish.py", "--rollback")
    after = hashes(os.path.join(ROOT, "dist"))
    run("publish.py", "--rollback")  # swap back
    back = hashes(os.path.join(ROOT, "dist"))
    rb = r.returncode == 0 and back == before
    print("4. rollback and swap back works: %s" % rb); ok &= rb
    t6, bad6 = unit_checks(); print("6. unit checks (percentile, axis labels, place phrasing, hidden blocks): %s %s" % (t6, bad6 or "")); ok &= t6
    t5 = blocks_safety(); print("5. new blocks: hidden without data, hidden when stale, hidden when the source is not cleared: %s" % t5); ok &= t5
    t8 = review_gate(); print("8. review gate: new gauge pages need a SHIP verdict, live pages never blocked: %s" % t8); ok &= t8
    t8d = record_tools_import(); print("8d. record_review can import template_hash without exiting: %s" % t8d); ok &= t8d
    t8c = related_closure(); print("8c. upstream/downstream pairs are listed on both pages: %s" % t8c); ok &= t8c
    t8b = signed_review(); print("8b. a SHIP needs a signature tied to its report; hand-written, edited-report and wrong-URL verdicts refused: %s" % t8b); ok &= t8b
    t9 = index_gate(); print("9. noindex kill switch: hold, open, allow list, header rule: %s" % t9); ok &= t9
    run("build.py")  # leave dist_next consistent with the real clock
    r = run("truth_tests.py"); print("7.", (r.stdout.strip().splitlines() or [r.stderr.strip()[:200]])[0]); ok &= r.returncode == 0
    if r.returncode:
        print(r.stdout.strip())
    print("ALL PASS" if ok else "FAILURES")
    sys.exit(0 if ok else 1)


main()
