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
    live_before = hashes(os.path.join(ROOT, "dist")).get(os.path.join("river", "kinzua-creek", "guffey", "water", "index.html"))
    try:
        rec = json.loads(saved)
        for x in rec["usgs"]["rows"]:
            x["time"] = x["time"].replace("2026-10", "2026-08")
        json.dump(rec, open(cp, "w"))
        r = run("build.py", site, env={"BUILD_NOW": "2026-10-16T23:00:00+00:00"})
        crit = "CRITICAL" in r.stdout
        built = os.path.exists(os.path.join(ROOT, "dist_next", "river", "kinzua-creek", "guffey", "water", "index.html"))
        live_after = hashes(os.path.join(ROOT, "dist")).get(os.path.join("river", "kinzua-creek", "guffey", "water", "index.html"))
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
    t5 = blocks_safety(); print("5. new blocks: hidden without data, hidden when stale, hidden when the source is not cleared: %s" % t5); ok &= t5
    run("build.py")  # leave dist_next consistent with the real clock
    print("ALL PASS" if ok else "FAILURES")
    sys.exit(0 if ok else 1)


main()
