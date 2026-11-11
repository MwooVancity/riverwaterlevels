"""Builder: reads cache/ only (no network). Renders Dashboard, Water and Forecast tabs per gauge, hub, state and home pages, trust pages, sitemap, robots, redirects, headers.
Writes dist_next/, then check.py and publish.py decide. A gauge whose critical data fails is skipped: its previous pages stay in dist/ (publish copies nothing from a failed build).
Usage: python -I build.py [site ...]   (default: every cached gauge)
"""
import glob, os, sys, json, shutil, hashlib, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.common import *
from lib.pages import load_effective
from lib import coverage, render, directory, indexing, related, world
from lib import page as pagelib
from lib.blocks2 import flow_behind


FILE_BUDGET = 95000 if os.environ.get("WORKERS_PAID") else 19000


def write(root, url, html):
    path = os.path.join(root, url.strip("/"), "index.html") if url != "/" else os.path.join(root, "index.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # 2026-11-10 (Healdsburg; tide lows 11-07): -0.04 ft printed as '-0.0 ft' by whichever of ~40 formatters; fixed once here for every page, not per formatter
    open(path, "w", encoding="utf-8").write(NEG_ZERO.sub(r"\1", html))


def prev_page(url):
    """The live copy of a gauge page (dist/ when present, else the live site); None when there is none."""
    p = os.path.join(ROOT, "dist", url.strip("/"), "index.html")
    if os.path.isfile(p):
        return open(p, encoding="utf-8").read()
    try:
        import urllib.request
        return urllib.request.urlopen(urllib.request.Request(SITE_URL + url, headers={"User-Agent": "riverwaterlevels.com build"}), timeout=30).read().decode("utf-8")
    except Exception:
        return None


def linkable(url, ix):
    """A built page other pages may link: indexable, or every page while the site is on its pre-launch hold (nothing is indexable then, and the lists must still work)."""
    return not ix["open"] or indexing.indexable(url, ix)


def conus_name():
    """templates/conus.webp published under a name hashed from its bytes, so it can be cached for a year (_headers) and a new map is a new name (audit #42)."""
    return "conus.%s.webp" % hashlib.sha256(open(os.path.join(ROOT, "templates", "conus.webp"), "rb").read()).hexdigest()[:10]


def main():
    rows, hubs = load_effective()
    now = datetime.datetime.fromisoformat(os.environ["BUILD_NOW"]) if os.environ.get("BUILD_NOW") else datetime.datetime.now(datetime.timezone.utc)
    cached = [f[:-5] for f in sorted(os.listdir(CACHE)) if f.endswith(".json") and not f.startswith("_") and f[:-5] in rows]
    preview = "--preview" in sys.argv
    render.PREVIEW = preview
    ix = indexing.load(ROOT)
    render.INDEX_CFG = ix
    import csv
    live = sorted(r["site"] for r in csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8")) if r["status"] == "live")
    # only live gauges are built: a cached gauge sent back to the queue must leave the site (2026-10-27: 22 pulled-back pages stayed live on old data)
    sites = [a for a in sys.argv[1:] if not a.startswith("--")] or [s for s in cached if s in set(live)]
    missing = [s for s in live if s not in cached] if not [a for a in sys.argv[1:] if not a.startswith("--")] else []
    report = {"built_at": iso(now), "gauges": [], "failed": [], "pages": 0}
    for s in missing:  # a live gauge with no cache yet (USGS 429, lost CI cache) fails ALONE: publish carries its previous page over, the other gauges still ship (owner 2026-10-25: never refuse rivers; was a whole-site ABORT that froze the site)
        report["failed"].append({"site": s, "reason": "no cache yet (collect.py has not stored it)", "url": (rows.get(s) or {}).get("dashboard_url")})
        print("NO CACHE", s, "(skipped; previous page, if any, stays live)")
    Gs = {}
    for s in sites:
        try:
            Gs[s] = render.ctx(s, rows[s], load_cache(s), now)
        except Exception as e:  # pipeline review #5: any error in one gauge's data skips that gauge, never the build
            report["failed"].append({"site": s, "reason": "%s: %s" % (type(e).__name__, str(e)[:100]), "url": rows[s]["dashboard_url"]})
            print("CRITICAL", s, type(e).__name__, str(e)[:100], "(skipped; previous pages stay live)")
    related.close(Gs, iso)  # upstream/downstream pairs are listed on both pages
    built = [rows[s] for s in Gs]
    inv_size = {k: len(v) for k, v in hubs.items()}
    by_hub = collections.defaultdict(list)
    for r in built:
        r["_built"] = linkable(r["dashboard_url"], ix)  # links rule 5 (audit 2026-11-10 #24): every list (home, hubs, nearby, upstream) links only built pages Google may index; noindexed /lake/barren-river-lake/ was on the home page
        g = Gs[r["site"]]
        r["_ll"], r["_lv"], r["_band"] = (g["lat"], g["lon"]), dir_lv(g), band_word(g["p"])
        r["_kind"] = pagelib.kind_of_g(g)  # links rule 3: the nearest lake, coast and river page of the other kinds
        r["_huc"] = str(((g["rec"].get("meta") or {}).get("loc") or {}).get("hydrologic_unit_code") or "")[:8]  # PLAN 12: same watershed listed first
        lvl_ = (g["rec"].get("coops") or {}).get("level")  # review 2026-11-08 blocker 3: a prediction-only page's level is its neighbour's, named in every list
        r["_val"] = ("%.2f ft%s" % (g["sg"][-1][1], " at %s" % lvl_["name"] if lvl_ else "")) if g.get("lake") and g["sg"] else "tide predictions" if g.get("tables") else None  # lake review: lists showed "– cfs" for a lake; a tide-tables page has no reading
        key = (r["hub_slug"], r["state"])
        by_hub[key].append(r)
    pagelib.link_index(rows, Gs)  # one grid for every nearby list and the rebuild test below
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

    # Rolling rebuild (owner 2026-10-29: "full rebuilds are not acceptable"). The Worker swaps live flow/stage every 3 min, so a page's static parts
    # need rebuilding only every ROLL_H hours (2: weather observations turn amber at 3 h; truth_live fails a page only past 12 h). Rebuilt now: new page, code changed,
    # hot (NWS alert, NWS river forecast, flow moved over 20% in 24 h), its slot this hour, or older than ROLL_H + 0.5 h (GitHub skipped runs).
    # Otherwise the published copy in dist/ is carried. dist/_built.json says when each page was built and from which code; it travels with dist/,
    # so a failed publish can never make it lie. No dist/ (first run, lost cache) or --full: everything is built.
    ROLL_H = 2
    tpl = template_hash()
    D = os.path.join(ROOT, "dist")
    try:
        was = json.load(open(os.path.join(D, "_built.json"), encoding="utf-8"))
        old_blocks = json.load(open(os.path.join(D, "_blocks.json"), encoding="utf-8"))
    except (OSError, ValueError):
        was, old_blocks = {}, {}
    full = preview or "--full" in sys.argv or bool([a for a in sys.argv[1:] if not a.startswith("--")]) or not was
    built_map, why = {}, collections.Counter()

    def sig(G):  # what the page was built from that changes between rolling rebuilds and must show at once
        al = sorted("%s|%s" % (a.get("event"), a.get("expires")) for a in (G["rec"].get("nws") or {}).get("alerts") or [])
        return [((G["rec"].get("nwps") or {}).get("forecast") or {}).get("issued"), al, G["rec"].get("_revised"), bool(flow_behind(G))]

    def due(s, G):
        u = rows[s]["dashboard_url"].strip("/")
        b = was.get(s) or {}
        if full or not all(os.path.isfile(os.path.join(D, p)) for p in (os.path.join(u, "index.html"), os.path.join(u, "data.json"), os.path.join("embed", u, "index.html"))):
            return "new"
        if b.get("tpl") != tpl or rows[s]["dashboard_url"] not in old_blocks:
            return "code"
        if (indexing.robots_meta(rows[s]["dashboard_url"], ix) == "") != ('name="robots"' not in open(os.path.join(D, u, "index.html"), encoding="utf-8").read(30000).split("</head>")[0]):  # 2026-11-10: a page opened (or pulled) by open_wave was carried with its old robots tag while the sitemap listed it, and check.py stopped the release; the carried file is the truth, so old build records need no new field  # ponytail: reads the <head> of each carried page (robots tag sits ~4 KB in; 14,000 pages = a few seconds)
            return "index"
        if pagelib.nb_urls(G, rows) != b.get("nb"):  # links rule 5: a page added, held or pulled changes its neighbours' lists in the same run
            return "links"
        if sig(G) != b.get("sig") or abs(G.get("chg") or 0) > 20:  # a new NWS forecast issue or a changed alert set, not merely one existing (48 of 74 were "hot")
            return "hot"
        age_h = (now - datetime.datetime.fromisoformat(b["at"])).total_seconds() / 3600
        if int(hashlib.md5(s.encode()).hexdigest(), 16) % ROLL_H == now.hour % ROLL_H or age_h >= ROLL_H + 0.5:
            return "slot"
        return None

    block_counts = {}
    live_copies = []
    for s, G in Gs.items():
        reason = due(s, G)
        if not reason:  # carried: the published page, its embed and data.json, unchanged
            u = rows[s]["dashboard_url"]
            for p in (u.strip("/") + "/index.html", u.strip("/") + "/data.json", "embed/" + u.strip("/") + "/index.html"):
                os.makedirs(os.path.dirname(os.path.join(nxt, p)), exist_ok=True)
                shutil.copy2(os.path.join(D, p), os.path.join(nxt, p))
            urls.append(u)
            hashes[u] = hashlib.sha256(open(os.path.join(D, u.strip("/"), "index.html"), "rb").read()).hexdigest()[:16]
            block_counts[u] = old_blocks[u]
            built_map[s] = was[s]
            why["carried"] += 1
            report["gauges"].append({"site": s, "url": u, "age_min": round(G["age_min"]), "percentile": G["p"]})
            continue
        why[reason] += 1
        built_map[s] = {"at": iso(now), "tpl": tpl, "sig": sig(G), "nb": pagelib.nb_urls(G, rows)}
        n_err = len(render.BLOCK_ERRORS)
        try:
            page, meta = render.build_tab("dashboard", G, rows)  # one page per gauge; the river forecast is a section of it where NWS issues one
            hurt = [e for e in render.BLOCK_ERRORS[n_err:] if e.split(": ")[1:2] and e.split(": ")[1] in render.SAFETY_BLOCKS]
            if hurt:  # a hidden alerts, forecast, stage or flow section is not an acceptable page: keep the previous one
                raise RuntimeError("safety block failed: " + "; ".join(hurt)[:160])
        except Exception as e:  # one gauge's page must never stop the other 9,000: it is reported as failed and its previous page stays live
            report["failed"].append({"site": s, "reason": "page build raised %s: %s" % (type(e).__name__, str(e)[:100]), "url": rows[s]["dashboard_url"]})
            print("PAGE BUILD CRASH", s, type(e).__name__, str(e)[:100], "(skipped; previous page stays live)")
            if was.get(s):  # the carried old page keeps its old build record, so the next run rebuilds it
                built_map[s] = was[s]
            else:
                built_map.pop(s, None)
            old = prev_page(rows[s]["dashboard_url"])  # pipeline review #1: the hubs link this gauge, so its previous page is carried into this build (no broken link, no frozen site)
            if old:
                write(nxt, rows[s]["dashboard_url"], old)
                live_copies.append(rows[s]["dashboard_url"].strip("/") + "/index.html")  # its numbers may be the Worker's newer swap beside build-time text: truth_live and check skip it like any carried page
                urls.append(rows[s]["dashboard_url"])
                hashes[rows[s]["dashboard_url"]] = hashlib.sha256(old.encode()).hexdigest()[:16]
            continue
        emit(meta["url"], page)
        write(nxt, "/embed" + meta["url"], render.embed_page(G, rows))
        ur = G["rec"]["usgs"]["rows"]
        ser = lambda code: [[r["time"], float(r["value"])] for r in ur if r["parameter_code"] == code and r.get("value") not in (None, "")]
        my = G["rec"].get("multiyear") or {}
        json.dump({"site": s, "name": river_at(rows[s]["river"], rows[s]["place"]) + ", " + rows[s]["state"], "page": SITE_URL + meta["url"], "observed": None if G.get("tables") else iso(G["lt"]), **({"tide_predictions_hilo_mllw_ft": G["rec"]["coops"]["hilo"]} if G.get("tables") else {}), "units": {"flow": "cfs", "stage": "ft"}, "flow_7d": ser("00060"), "stage_7d": ser("00065"), **({"lake_elevation_7d": ser(G["lake"]), "storage_7d": ser("00054"), "lake_units": {"lake_elevation": "ft above " + lake_datum(G), "storage": "acre-ft"}} if G.get("lake") else {}),
                   "daily_mean_flow": {"as_of": my.get("as_of"), "days": my.get("span"), "by_year": my.get("series")}, "source": "NOAA CO-OPS tide predictions above MLLW (no water level is measured at this station)" if G.get("tables") else "NOAA CO-OPS water level above MLLW, preliminary data not yet quality-checked by NOAA" if G.get("coast") else ("%s station %s, provisional" % (G["agy"]["name"], G["agy_st"])) if G.get("agy") else "USGS Water Data API, provisional data subject to revision", "credit": "NOAA National Ocean Service, CO-OPS" if G.get("coast") else G["agy"]["name"] if G.get("agy") else "U.S. Geological Survey", "built_at": iso(now)},
                  open(os.path.join(nxt, meta["url"].strip("/"), "data.json"), "w"), separators=(",", ":"))
        block_counts[meta["url"]] = len(meta["blocks"])
        report["gauges"].append({"site": s, "url": rows[s]["dashboard_url"], "age_min": round(G["age_min"]), "percentile": G["p"]})
    if not block_counts:
        sys.exit("every gauge failed to build (%d failures, first: %s): nothing to publish, dist/ unchanged" % (len(report["failed"]), report["failed"][0]["reason"][:120] if report["failed"] else "no gauge pages"))
    report["block_errors"] = render.BLOCK_ERRORS[:50]
    if render.BLOCK_ERRORS:
        print("BLOCKS HIDDEN BY THE GUARD (%d): %s" % (len(render.BLOCK_ERRORS), "; ".join(render.BLOCK_ERRORS[:5])))
    if live_copies:
        json.dump(live_copies, open(os.path.join(nxt, "_carried.json"), "w"))
    print("gauge pages: %s" % ", ".join("%s %d" % kv for kv in sorted(why.items())))
    json.dump(block_counts, open(os.path.join(nxt, "_blocks.json"), "w"), separators=(",", ":"))  # data blocks rendered per gauge page: tools/open_wave.py will not release a page with too few
    if built:
        shown = [r for r in built if r["_built"]]  # links rule 5: lists name only pages Google may index
        rivers_ = [r for r in shown if not r.get("lake")]  # flow lists (home, state hubs) list rivers; a lake has no cfs to show there
        waters_ = [r for r in shown if r.get("lake")]
        emit("/", directory.home(rivers_, Gs, waters_).replace('src="/conus.webp"', 'src="/%s"' % conus_name()))  # lakes and coasts get their home link (basics audit 2026-11-08); the map under its hashed, year-cached name
        state_data = {}
        for st in sorted({r["state"] for r in rivers_}):
            sp = os.path.join(ROOT, "cache", "state-%s.json" % st.lower())
            if os.path.exists(sp):
                try:
                    state_data[st] = json.load(open(sp, encoding="utf-8"))
                except Exception:
                    pass
        tx = None
        try:  # Texas lake levels hub: one cached TWDB file; missing or broken -> no page this build (the cache keeps the last good file, so only a lost cache drops it)
            tp = os.path.join(ROOT, "cache", "twdb-texas.json")
            if os.path.exists(tp):
                linked = {re.sub(r"[^a-z0-9]", "", (lr.get("twdb") or "").lower()): next((b["dashboard_url"] for b in built if b["site"] == lr["site"]), None) for lr in csv.DictReader(open(os.path.join(ROOT, "data", "lakes.csv"), encoding="utf-8")) if lr.get("twdb")}
                tx = directory.lake_state_page(json.load(open(tp, encoding="utf-8")), {k: v for k, v in linked.items() if v}, datetime.datetime.now(datetime.timezone.utc))
                if tx:
                    emit("/lakes/tx/", tx)
        except Exception as e:
            print("FAIL lakes/tx", str(e)[:120])
        for st in sorted({r["state"] for r in rivers_}):
            emit("/rivers/%s/" % st.lower(), directory.state_page(st, [r for r in rivers_ if r["state"] == st], Gs, state_data.get(st), lakes_hub=bool(tx) and st == "TX", waters=[r for r in waters_ if r["state"] == st]))  # audit #26: a lake's breadcrumb names its state hub, so the hub lists it
        for (hs, st), g in by_hub.items():
            if len(g) > 1:  # ponytail: a hub whose gauges are all still unopened lists them anyway (its address must not 404); open_wave opens them the same day
                emit("/river/%s/" % hs, directory.hub_page(hs, st, [r for r in g if r["_built"]] or g, inv_size[(hs, st)], Gs))
        for url, html in directory.trust_pages(len(built), built).items():
            emit(url, html)
        world_rows = []
        wnow, wpages = datetime.datetime.now(datetime.timezone.utc), []
        for page in directory.world_pages():
            try:
                d = json.load(open(os.path.join(CACHE, "_river-%s.json" % page["slug"]), encoding="utf-8"))
            except (OSError, ValueError):  # lost or torn: counted as held below, never a quiet 404
                continue
            if page.get("feed") == "eccc":
                for r in d["rows"]:
                    r["state"] = world.canada_label(r, wnow)[0].lower()
            wpages.append((page, d))
        wkeep = world.choose(wpages, wnow)
        wlisted = sum(len(p.get("gauge_pages") or []) for p in directory.world_pages())
        near = world.near_index(wpages, wkeep)
        for page, d in wpages:
            keep = wkeep[page["slug"]]
            for r in d["rows"]:
                if r["name"] not in keep:
                    continue
                gp = world.page(page, r, wnow, d["rows"], keep, near)
                emit(gp[0], gp[1])
                built_map[gp[0]] = {"at": iso(now)}  # keyed by URL: check.py keep_old_times keeps a carried world page's old time, so the watchdog's 6 h alarm sees it
                world_rows.append([(r.get("title") or "%s at %s" % (page["river"], r["name"].replace(" UP", "").title())), gp[0], round(r["lat"], 4), round(r["lon"], 4), {"eccc": "Canada", "ea": "England UK", "imi": "Ireland"}.get(page.get("feed"), "Germany Europe")])
            wp = directory.world_page(page, d, wnow, keep)
            if wp:
                emit("/%s/" % page["slug"], wp.replace("Data: USGS, NOAA, NWS.", "Data: official agencies, listed on each page.").replace("-0.00 m", "0.00 m"))
        os.makedirs(os.path.join(nxt, "archive"), exist_ok=True)
        for f in glob.glob(os.path.join(CACHE, "_archive-*.json")):
            shutil.copy(f, os.path.join(nxt, "archive", os.path.basename(f)[1:]))
        emit("/status/", directory.status_page(built, Gs, report["built_at"]))
        ages = [Gs[r["site"]]["age_min"] for r in built]
        json.dump({"built_at": report["built_at"], "sha": os.environ.get("GITHUB_SHA") or "", "gauges": len(built), "newest_age_min": round(min(ages)), "oldest_age_min": round(max(ages)), "median_age_min": round(sorted(ages)[len(ages) // 2]),
                   "pages": len(urls), "failed_urls": [f["url"] for f in report["failed"] if f.get("url")], "block_errors": render.BLOCK_ERRORS[:30], "world": {"listed": wlisted, "shown": sum(len(v) for v in wkeep.values()), "gaps": {k: v[:6] for k, v in list(world.GAPS.items())[:40]}, "thin": {k: v[:3] for k, v in list(world.THIN.items())[:400]}}, "by_gauge": {r["site"]: round(Gs[r["site"]]["age_min"]) for r in built}}, open(os.path.join(nxt, "status.json"), "w"), separators=(",", ":"))
    json.dump(built_map, open(os.path.join(nxt, "_built.json"), "w"), separators=(",", ":"))
    hp = os.path.join(ROOT, "state", "source-health.json")  # every source's last outcome and when it last worked (collect.py write_health), read by tools/watchdog.py
    if os.path.exists(hp):
        shutil.copy2(hp, os.path.join(nxt, "_health.json"))
    pp = os.path.join(CACHE, "_ea-proof.json")  # England's alert proof (collect.py ea_probe), published so a lost cache reads it back
    if os.path.exists(pp):
        shutil.copy2(pp, os.path.join(nxt, "_proofs.json"))
    # Cloudflare counts every rule after the first dynamic one as dynamic, limit 100 (deploy refused 2026-11-01, site frozen 7 h), and one
    # rule per river would pass 2,000 static anyway, so rivers with a single gauge go to single-rivers.json and worker/index.js sends the 301
    redirects = ["/river/apple-river-wi/above-05341499-at-park-in-somerset/ /river/apple-river-wi/above-park-in-somerset/ 301", "/river/:hub/:place/water/ /river/:hub/:place/ 301", "/river/:hub/:place/forecast/ /river/:hub/:place/ 301", "/rivers/ / 301"]
    json.dump({r["hub_url"]: r["dashboard_url"] for r in built if r.get("_single") and r.get("hub_url") and r["hub_url"] != r["dashboard_url"]}, open(os.path.join(nxt, "single-rivers.json"), "w"), separators=(",", ":"), sort_keys=True)
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
    open(os.path.join(nxt, "8a1906b9e99095f201fe1a3d6210c090.txt"), "w", encoding="utf-8").write("8a1906b9e99095f201fe1a3d6210c090")  # IndexNow key file (tools/indexnow.py KEY; public by design)
    open(os.path.join(nxt, "llms.txt"), "w", encoding="utf-8").write(directory.llms(built))
    open(os.path.join(nxt, "ads.txt"), "w", encoding="utf-8").write("google.com, pub-8997828618122077, DIRECT, f08c47fec0942fa0\n")  # AdSense authorized-sellers file (owner 2026-10-23)
    open(os.path.join(nxt, "404.html"), "w", encoding="utf-8").write(directory.not_found(built))
    open(os.path.join(nxt, "favicon.svg"), "w", encoding="utf-8").write(directory.FAVICON)
    json.dump([[river_at(r["river"], r["place"]) + ", " + r["state"], r["dashboard_url"], round(Gs[r["site"]]["lat"], 4), round(Gs[r["site"]]["lon"], 4), (directory.STATE_NAMES.get(r["state"], r["state"]) + " " + r["state"] + " " + r["site"])] for r in built] + world_rows, open(os.path.join(nxt, "gauges.json"), "w"), separators=(",", ":"))
    # the edge live layer (worker/index.js): which page is which gauge, the reading the page was built with, and its time zone
    # every built gauge (check.py, info_gain, hater_sample read it); the Worker cron sends only the numeric USGS ids to USGS
    json.dump([[r["site"], r["dashboard_url"], iso(Gs[r["site"]]["lt"]), Gs[r["site"]]["tzname"], Gs[r["site"]]["lv"]] for r in built], open(os.path.join(nxt, "live-sites.json"), "w"), separators=(",", ":"))
    open(os.path.join(nxt, "_redirects"), "w", encoding="utf-8").write("\n".join(list(redirects) + ["/favicon.ico /favicon.svg 301"]) + "\n")
    open(os.path.join(nxt, "_headers"), "w", encoding="utf-8").write(indexing.headers(open(os.path.join(ROOT, "templates", "_headers"), encoding="utf-8").read(), ix))
    shutil.copy(os.path.join(ROOT, "templates", "og.png"), os.path.join(nxt, "og.png"))
    shutil.copy(os.path.join(ROOT, "templates", "conus.webp"), os.path.join(nxt, conus_name()))  # home map, static, cached a year under its hashed name
    shutil.copy(os.path.join(ROOT, "templates", "conus.webp"), os.path.join(nxt, "conus.webp"))  # ponytail: the old name for a home page cached before the hashed one; delete after 2026-12
    for name in ("sw.js", "icon-192.png", "icon-512.png"):
        shutil.copy(os.path.join(ROOT, "templates", name), os.path.join(nxt, name))
    for name, text in render.ASSETS.items():  # the stylesheets, each named by a hash of its content
        open(os.path.join(nxt, name), "w", encoding="utf-8").write(text)
    json.dump({"name": "River Water Levels", "short_name": "Rivers", "start_url": "/", "scope": "/", "display": "standalone", "theme_color": "#1d5fa8", "background_color": "#ffffff",
               "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"}, {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"}]},
              open(os.path.join(nxt, "manifest.webmanifest"), "w"), indent=1)
    json.dump({"urls": urls}, open(os.path.join(nxt, "_urls.json"), "w"))
    report["pages"] = len(urls)
    nfiles = sum(len(fs) for _, _, fs in os.walk(nxt))  # the real deploy count: pages + per-gauge embed/data.json + sitemaps + infra, not just len(urls)
    report["files"] = nfiles
    sp_ = os.path.join(nxt, "status.json")  # limits measured every run, read by tools/watchdog.py (warns at 70%): Cloudflare 20,000 files, GitHub 10 GB cache
    if os.path.exists(sp_):
        st_ = json.load(open(sp_))
        st_["files"] = nfiles
        for key, name in (("shards", "shards.json"), ("release_skip", "release-skip.txt")):
            try:
                st_[key] = open(os.path.join(ROOT, "state", name)).read().strip()
            except OSError:
                pass
        st_["cache_lost"] = os.environ.get("CACHE_MATCHED") == ""
        from lib import ledger
        cp_ = os.path.join(ROOT, "cache", "_census.json")
        st_["census"] = json.load(open(cp_, encoding="utf-8")) if os.path.exists(cp_) else None  # every official site built or not; tools/watchdog.py reports it
        st_["ledger"] = ledger.report()  # every stage's slowest run today and the page count where it breaks; tools/watchdog.py alarms on "soon"
        st_["catches"] = ledger.catch_report()  # per gate, what it caught in its last 10 runs (refresh.py writes it after the gates, so this is the runs before this one)
        st_["coverage"] = coverage.scan(nxt, json.load(open(os.path.join(ROOT, "dist", "status.json"))).get("coverage") if os.path.exists(os.path.join(ROOT, "dist", "status.json")) else None)
        json.dump(st_, open(sp_, "w"), separators=(",", ":"))
    if nfiles > FILE_BUDGET and not preview:
        raise SystemExit("file budget: %d files is over %d (the Cloudflare plan's limit per deploy)" % (nfiles, FILE_BUDGET))
    runs = os.path.join(ROOT, "runs", now.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(runs, exist_ok=True)
    json.dump(report, open(os.path.join(runs, "report.json"), "w"), indent=1)
    for old_run in sorted(os.listdir(os.path.dirname(runs)))[:-50]:  # laptop stays clean (owner 2026-10-28): keep the last 50 build reports
        shutil.rmtree(os.path.join(os.path.dirname(runs), old_run), ignore_errors=True)
    print("gauges %d, pages %d, failed %d, redirects %d -> dist_next (run check.py, then publish.py)" % (len(Gs), len(urls), len(report["failed"]), len(redirects)))


_ix = {"open": True, "site_pages": True, "allow": {"/lake/a/"}, "pulled": set(), "held": ()}
assert linkable("/lake/b/", {"open": False}) and linkable("/lake/a/", _ix) and not linkable("/lake/b/", _ix) and linkable("/rivers/ga/", _ix), "build: links rule 5 (only indexable pages linked; every page while on hold)"
_ld = json.loads(world.world_ld({"feed": "imi"}, {"time": "2026-11-10T03:10:00Z", "lat": 53.3456, "lon": -6.2219}, "/irish-sea/dublin-port/", {"head": "Dublin Port", "agency": "Marine Institute", "station": "Dublin Port", "api": "Marine Institute ERDDAP", "name": "Marine Institute (Ireland)"},
                                  "<title>Dublin Port tide &amp; sea level today | River Water Levels</title>")[35:-9])
assert _ld["@type"] == "WebPage" and _ld["name"].startswith("Dublin Port tide & sea") and _ld["about"]["name"] == "Dublin Port, Ireland" and _ld["mainEntity"]["creator"]["name"] == "Marine Institute (Ireland)", "build: world gauge structured data (audit #25)"
assert 'href="/lake/lake-lanier/">Lake Lanier' in directory.state_waters("GA", [{"river": "Lake Lanier", "place": "Buford Dam", "water_url": "/lake/lake-lanier/"}]) and directory.state_waters("GA", []) == "", "build: state hub lists its lakes (audit #26)"
main()
