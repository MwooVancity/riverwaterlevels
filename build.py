"""Builder: reads cache/ only (no network). Renders Dashboard, Water and Forecast tabs per gauge, hub, state and home pages, trust pages, sitemap, robots, redirects, headers.
Writes dist_next/, then check.py and publish.py decide. A gauge whose critical data fails is skipped: its previous pages stay in dist/ (publish copies nothing from a failed build).
Usage: python -I build.py [site ...]   (default: every cached gauge)
"""
import os, sys, json, shutil, hashlib, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.common import *
from lib.pages import load_effective
from lib import render, directory


FILE_BUDGET = 19000


def write(root, url, html):
    path = os.path.join(root, url.strip("/"), "index.html") if url != "/" else os.path.join(root, "index.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(html)


def main():
    rows, hubs = load_effective()
    now = datetime.datetime.fromisoformat(os.environ["BUILD_NOW"]) if os.environ.get("BUILD_NOW") else datetime.datetime.now(datetime.timezone.utc)
    cached = [f[:-5] for f in sorted(os.listdir(CACHE)) if f.endswith(".json") and not f.startswith("_") and f[:-5] in rows]
    preview = "--preview" in sys.argv
    render.PREVIEW = preview
    sites = [a for a in sys.argv[1:] if not a.startswith("--")] or cached
    report = {"built_at": iso(now), "gauges": [], "failed": [], "pages": 0}
    Gs = {}
    for s in sites:
        try:
            Gs[s] = render.ctx(s, rows[s], load_cache(s), now)
        except render.CriticalFail as e:
            report["failed"].append({"site": s, "reason": str(e)})
            print("CRITICAL", s, e, "(skipped; previous pages stay live)")
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

    for s, G in Gs.items():
        for tab in (("dashboard", "forecast") if G["has_forecast"] else ("dashboard",)):  # one page per gauge; a Forecast page only where NWS issues a river forecast
            page, meta = render.build_tab(tab, G, rows)
            emit(meta["url"], page)
        report["gauges"].append({"site": s, "url": rows[s]["dashboard_url"], "age_min": round(G["age_min"]), "percentile": G["p"]})
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
                   "pages": len(urls) + 1, "by_gauge": {r["site"]: round(Gs[r["site"]]["age_min"]) for r in built}}, open(os.path.join(nxt, "status.json"), "w"), separators=(",", ":"))
    # rivers with a single gauge: /river/<river>/ redirects to that gauge's dashboard
    # one dynamic rule (Cloudflare allows 100 dynamic and 2,000 static rules): the old /water/ address of every gauge leads to its page
    redirects = ["/river/:hub/:place/water/ /river/:hub/:place/ 301"]
    lm_path = os.path.join(ROOT, "state", "lastmod.json")
    os.makedirs(os.path.dirname(lm_path), exist_ok=True)
    lm = json.load(open(lm_path)) if os.path.exists(lm_path) else {}
    today = now.date().isoformat()
    for u, h in hashes.items():
        if lm.get(u, {}).get("hash") != h:
            lm[u] = {"hash": h, "date": today}
    if not os.environ.get("BUILD_NOW") and not preview:
        json.dump(lm, open(lm_path, "w"), indent=0)
    for name, xml in directory.sitemap_files(urls, {u: lm[u]["date"] for u in urls if u in lm}).items():
        open(os.path.join(nxt, name), "w", encoding="utf-8").write(xml)
    open(os.path.join(nxt, "robots.txt"), "w", encoding="utf-8").write(directory.robots())
    open(os.path.join(nxt, "404.html"), "w", encoding="utf-8").write(directory.not_found())
    open(os.path.join(nxt, "favicon.svg"), "w", encoding="utf-8").write(directory.FAVICON)
    json.dump([[river_at(r["river"], r["place"]) + ", " + r["state"], r["dashboard_url"], round(Gs[r["site"]]["lat"], 4), round(Gs[r["site"]]["lon"], 4)] for r in built], open(os.path.join(nxt, "gauges.json"), "w"), separators=(",", ":"))
    open(os.path.join(nxt, "_redirects"), "w", encoding="utf-8").write("\n".join(list(redirects) + ["/favicon.ico /favicon.svg 301"]) + "\n")
    shutil.copy(os.path.join(ROOT, "templates", "_headers"), os.path.join(nxt, "_headers"))
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
