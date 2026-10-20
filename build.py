"""Builder: reads cache/ only (no network). Renders Dashboard, Water and Forecast tabs per gauge, hub, state and home pages, trust pages, sitemap, robots, redirects, headers.
Writes dist_next/, then check.py and publish.py decide. A gauge whose critical data fails is skipped: its previous pages stay in dist/ (publish copies nothing from a failed build).
Usage: python -I build.py [site ...]   (default: every cached gauge)
"""
import os, sys, json, shutil, hashlib, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.common import *
from lib.pages import load_effective
from lib import render, directory, indexing, related


FILE_BUDGET = 19000


def write(root, url, html):
    path = os.path.join(root, url.strip("/"), "index.html") if url != "/" else os.path.join(root, "index.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(html)


def live_urls(path):
    """The page list of the release that is live now: the local copy when there is one, else the deployed list (a fresh CI checkout has no dist/)."""
    try:
        if os.path.exists(path):
            return json.load(open(path))["urls"]
        import urllib.request
        return json.load(urllib.request.urlopen(urllib.request.Request(SITE_URL + "/_urls.json", headers={"User-Agent": "Mozilla/5.0 (build)"}), timeout=30))["urls"]
    except Exception:
        return []


def main():
    rows, hubs = load_effective()
    now = datetime.datetime.fromisoformat(os.environ["BUILD_NOW"]) if os.environ.get("BUILD_NOW") else datetime.datetime.now(datetime.timezone.utc)
    cached = [f[:-5] for f in sorted(os.listdir(CACHE)) if f.endswith(".json") and not f.startswith("_") and f[:-5] in rows]
    preview = "--preview" in sys.argv
    render.PREVIEW = preview
    ix = indexing.load(ROOT)
    render.INDEX_CFG = ix
    sites = [a for a in sys.argv[1:] if not a.startswith("--")] or cached
    report = {"built_at": iso(now), "gauges": [], "failed": [], "pages": 0}
    Gs = {}
    for s in sites:
        try:
            Gs[s] = render.ctx(s, rows[s], load_cache(s), now)
        except render.CriticalFail as e:
            report["failed"].append({"site": s, "reason": str(e), "url": rows[s]["dashboard_url"]})
            print("CRITICAL", s, e, "(skipped; previous pages stay live)")
    from lib.reviewgate import hold_back
    live_f, rv_f = os.path.join(ROOT, "dist", "_urls.json"), os.path.join(ROOT, "data", "reviews.json")
    skip_g, skip_f = hold_back({s: rows[s] for s in Gs}, live_urls(live_f) if not preview and "--no-hold" not in sys.argv else [], json.load(open(rv_f, encoding="utf-8")) if os.path.exists(rv_f) else {}, set())
    if "--no-hold" in sys.argv:  # review builds: include the pages that are waiting for their review
        skip_g, skip_f = set(), set()
    for s in skip_g:
        del Gs[s]
    for s in skip_f:
        Gs[s]["fc_page"] = False
    report["held_for_review"] = sorted(rows[s]["dashboard_url"] for s in skip_g) + sorted(rows[s]["forecast_url"] for s in skip_f)
    if report["held_for_review"]:
        print("HELD FOR REVIEW (new pages without a SHIP verdict; everything else still ships): %s" % ", ".join(report["held_for_review"]))
    related.close(Gs, iso)  # upstream/downstream pairs are listed on both pages
    built = [rows[s] for s in Gs]
    inv_size = {k: len(v) for k, v in hubs.items()}
    by_hub = collections.defaultdict(list)
    for r in built:
        r["_built"] = True
        g = Gs[r["site"]]
        r["_ll"], r["_lv"], r["_band"] = (g["lat"], g["lon"]), g["lv"], band_word(g["p"])
        key = (r["hub_slug"], r["state"])
        by_hub[key].append(r)
    for key, g in by_hub.items():  # a hub page needs two or more built gauges; with one, the river address redirects to that gauge
        for r in g:
            r["_hub"] = len(g) > 1
            r["_single"] = len(g) == 1
    nxt = os.path.join(ROOT, "dist_preview" if preview else "dist_next")
    shutil.rmtree(nxt, ignore_errors=True)
    urls, hashes = [], {}

    def emit(url, html):
        write(nxt, url, html)
        urls.append(url)
        hashes[url] = hashlib.sha256(html.encode()).hexdigest()[:16]

    block_counts = {}
    for s, G in Gs.items():
        n_err = len(render.BLOCK_ERRORS)
        try:
            page, meta = render.build_tab("dashboard", G, rows)  # one page per gauge; the river forecast is a section of it where NWS issues one
            hurt = [e for e in render.BLOCK_ERRORS[n_err:] if e.split(": ")[1:2] and e.split(": ")[1] in render.SAFETY_BLOCKS]
            if hurt:  # a hidden alerts, forecast, stage or flow section is not an acceptable page: keep the previous one
                raise RuntimeError("safety block failed: " + "; ".join(hurt)[:160])
        except Exception as e:  # one gauge's page must never stop the other 9,000: it is reported as failed and its previous page stays live
            report["failed"].append({"site": s, "reason": "page build raised %s: %s" % (type(e).__name__, str(e)[:100]), "url": rows[s]["dashboard_url"]})
            print("PAGE BUILD CRASH", s, type(e).__name__, str(e)[:100], "(skipped; previous page stays live)")
            continue
        emit(meta["url"], page)
        block_counts[meta["url"]] = len(meta["blocks"])
        report["gauges"].append({"site": s, "url": rows[s]["dashboard_url"], "age_min": round(G["age_min"]), "percentile": G["p"]})
    if not block_counts:
        sys.exit("every gauge failed to build (%d failures, first: %s): nothing to publish, dist/ unchanged" % (len(report["failed"]), report["failed"][0]["reason"][:120] if report["failed"] else "no gauge pages"))
    report["block_errors"] = render.BLOCK_ERRORS[:50]
    if render.BLOCK_ERRORS:
        print("BLOCKS HIDDEN BY THE GUARD (%d): %s" % (len(render.BLOCK_ERRORS), "; ".join(render.BLOCK_ERRORS[:5])))
    json.dump(block_counts, open(os.path.join(nxt, "_blocks.json"), "w"), separators=(",", ":"))  # data blocks rendered per gauge page: tools/open_wave.py will not release a page with too few
    if built:
        emit("/", directory.home(built, Gs))
        for st in sorted({r["state"] for r in built}):
            emit("/rivers/%s/" % st.lower(), directory.state_page(st, [r for r in built if r["state"] == st], Gs))
        for (hs, st), g in by_hub.items():
            if len(g) > 1:
                emit("/river/%s/" % hs, directory.hub_page(hs, st, g, inv_size[(hs, st)], Gs))
        for url, html in directory.trust_pages(len(built), built).items():
            emit(url, html)
        emit("/status/", directory.status_page(built, Gs, report["built_at"]))
        ages = [Gs[r["site"]]["age_min"] for r in built]
        json.dump({"built_at": report["built_at"], "gauges": len(built), "newest_age_min": round(min(ages)), "oldest_age_min": round(max(ages)), "median_age_min": round(sorted(ages)[len(ages) // 2]),
                   "pages": len(urls), "failed_urls": [f["url"] for f in report["failed"] if f.get("url")], "block_errors": render.BLOCK_ERRORS[:30], "by_gauge": {r["site"]: round(Gs[r["site"]]["age_min"]) for r in built}}, open(os.path.join(nxt, "status.json"), "w"), separators=(",", ":"))
    # rivers with a single gauge: /river/<river>/ redirects to that gauge's dashboard
    # one dynamic rule (Cloudflare allows 100 dynamic and 2,000 static rules): the old /water/ address of every gauge leads to its page
    redirects = ["/river/:hub/:place/water/ /river/:hub/:place/ 301", "/river/:hub/:place/forecast/ /river/:hub/:place/ 301", "/rivers/ / 301"]
    lm_path = os.path.join(ROOT, "state", "lastmod.json")
    os.makedirs(os.path.dirname(lm_path), exist_ok=True)
    lm = json.load(open(lm_path)) if os.path.exists(lm_path) else {}
    today = now.date().isoformat()
    for u, h in hashes.items():
        if lm.get(u, {}).get("hash") != h:
            lm[u] = {"hash": h, "date": today}
    if not os.environ.get("BUILD_NOW") and not preview:
        json.dump(lm, open(lm_path, "w"), indent=0)
    for name, xml in directory.sitemap_files([u for u in urls if indexing.sitemap_ok(u, ix)], {u: lm[u]["date"] for u in urls if u in lm}).items():
        open(os.path.join(nxt, name), "w", encoding="utf-8").write(xml)
    open(os.path.join(nxt, "robots.txt"), "w", encoding="utf-8").write(directory.robots())
    open(os.path.join(nxt, "404.html"), "w", encoding="utf-8").write(directory.not_found())
    open(os.path.join(nxt, "favicon.svg"), "w", encoding="utf-8").write(directory.FAVICON)
    json.dump([[river_at(r["river"], r["place"]) + ", " + r["state"], r["dashboard_url"], round(Gs[r["site"]]["lat"], 4), round(Gs[r["site"]]["lon"], 4), (directory.STATE_NAMES.get(r["state"], r["state"]) + " " + r["state"] + " " + r["site"])] for r in built], open(os.path.join(nxt, "gauges.json"), "w"), separators=(",", ":"))
    open(os.path.join(nxt, "_redirects"), "w", encoding="utf-8").write("\n".join(list(redirects) + ["/favicon.ico /favicon.svg 301"]) + "\n")
    open(os.path.join(nxt, "_headers"), "w", encoding="utf-8").write(indexing.headers(open(os.path.join(ROOT, "templates", "_headers"), encoding="utf-8").read(), ix))
    shutil.copy(os.path.join(ROOT, "templates", "og.png"), os.path.join(nxt, "og.png"))
    json.dump({"urls": urls}, open(os.path.join(nxt, "_urls.json"), "w"))
    report["pages"] = len(urls)
    if len(urls) > FILE_BUDGET and not preview:
        raise SystemExit("file budget: %d pages is over %d (Cloudflare free plan allows 20,000 files per deploy)" % (len(urls), FILE_BUDGET))
    runs = os.path.join(ROOT, "runs", now.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(runs, exist_ok=True)
    json.dump(report, open(os.path.join(runs, "report.json"), "w"), indent=1)
    print("gauges %d, pages %d, failed %d, redirects %d -> dist_next (run check.py, then publish.py)" % (len(Gs), len(urls), len(report["failed"]), len(redirects)))


main()
