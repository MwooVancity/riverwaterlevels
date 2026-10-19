"""Build-integrity checks (not index gates). Usage: python -I check.py [dir]   |   python -I check.py --selftest
Per page: canonical, banned strings, doubled words, source line per block, units, gauge-local time, one h1, weight.
Site: unique titles, every internal link resolves, sitemap equals page set, tab/hub/state reciprocity, link budgets, no orphans, depth from home.
Exit 1 if anything fails.
"""
import os, re, sys, json, collections, gzip, hashlib
MAX_GZ = 90000  # pilot pages are about 48 KB compressed; tail pages carry fewer blocks
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.common import ROOT, SITE_URL

BANNED = [r"\bForecast page\b", r"\bsecond .{0,20}page\b", r"prototype", r"licen[cs]e", r"\bConf\b", r"\bSr\d{3,}", r"__[A-Z_]+__", r"\bundefined\b", r"\bNaN\b", r"\bNone\b", r"Unnamed [a-z ]*(boat ramp|fishing spot)", r"-?\b9{5,}\b", r"-?999\d{2,}\b", r"\b20\d\d-\d\d-\d\d[T ]\d\d:\d\d"]  # the last three (the ISO one: a raw machine timestamp shown to a reader; the other two: USGS sentinel values (-999999) must never be shown as readings)
MAX_BYTES = 230_000
BUDGET = {"gauge": 110, "hub": 80, "state": 480, "home": 200, "trust": 40}


def kind_of(rel):
    parts = rel.replace("\\", "/").split("/")
    if rel in ("index.html",):
        return "home"
    if parts[0] == "rivers":
        return "state"
    if parts[0] == "river":
        return "hub" if len(parts) == 3 else "gauge"
    return "trust"


JARGON = r"percentile|\bAEP\b|NWPS|NLDI|kcfs|StreamCat|\bSWE\b|\bTMDL\b"  # words a first-time reader cannot decode; allowed in Source lines, tables and the glossary, not in headings or stat tiles


def ui_checks(body, plain=True):
    """Reader-first gates on the page body: plain words in headings and tiles, no empty widgets, every image sized and described, heading order, no sentence stated twice."""
    bad = []
    heads = re.findall(r"<(h[1-6])[^>]*>(.*?)</\1>", body, re.S)
    for tag, inner in heads:
        t = re.sub(r"<[^>]+>", " ", inner)
        if plain and tag in ("h1", "h2") and re.search(JARGON, t, re.I):
            bad.append("jargon in %s: %r" % (tag, t.strip()[:50]))
    prev = 1
    for tag, _ in heads:
        lv = int(tag[1])
        if lv > prev + 1:
            bad.append("heading level skips from h%d to h%d" % (prev, lv))
        prev = lv
    for mm in re.finditer(r'<div class="tile [^"]*"><i class="ic">.*?</i><span>(.*?)</span><b>(.*?)</b>', body, re.S):
        t = re.sub(r"<[^>]+>", " ", mm.group(1) + " " + mm.group(2))
        if re.search(JARGON, t, re.I):
            bad.append("jargon in stat tile: %r" % t.strip()[:50])
    vis = re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", " ", body, flags=re.S))
    mm = re.search(r"[A-Za-z0-9)]\.\.(?!\.)|\.\s\.\s", vis)
    if mm:
        bad.append("double full stop near %r" % vis[max(0, mm.start() - 30):mm.end() + 20].strip())
    for w in ("bars", "strip", "chips"):
        if re.search(r'<div class="%s">\s*</div>' % w, body):
            bad.append("empty %s widget" % w)
    for mm in re.finditer(r"<img\b[^>]*>", body):
        im = mm.group(0)
        if not re.search(r'\swidth="\d+"', im) or not re.search(r'\sheight="\d+"', im):
            bad.append("image without width and height (layout shift): %s" % im[:60])
        if not re.search(r'\salt="[^"]+"', im):
            bad.append("image without alt text: %s" % im[:60])
    seen = collections.Counter(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", p)).strip() for p in re.findall(r"<p>(.*?)</p>", body, re.S))
    for s, n in seen.items():
        if n > 1 and len(s) >= 60:
            bad.append("sentence stated %d times: %r" % (n, s[:60]))
    return bad


def check_html(h, rel):
    bad = []
    url = "/" + os.path.dirname(rel).replace("\\", "/") + "/" if os.path.dirname(rel) else "/"
    m = re.search(r'<link rel="canonical" href="([^"]+)"', h)
    if not m:
        bad.append("no canonical")
    elif m.group(1) != SITE_URL + url:
        bad.append("canonical %s != %s" % (m.group(1), SITE_URL + url))
    if len(h.encode()) > MAX_BYTES:
        bad.append("page weight %d bytes over budget" % len(h.encode()))
    if "<main" not in h:
        return bad + ["no <main>"]
    body = h.split("<main", 1)[1].split("</main>")[0]
    text = re.sub(r"<[^>]+>", " ", body)
    for pat in BANNED:
        for mm in re.finditer(pat, text):
            bad.append("banned %r near %r" % (pat, text[max(0, mm.start() - 25):mm.end() + 25].strip()))
    for mm in re.finditer(r"\b([A-Za-z]+) \1\b", text, re.I):  # words only: "19 19" is a day and an hour in "2026-10-19 19:38", not a typo
        if mm.group(1).lower() not in ("had", "that"):
            bad.append("doubled word %r" % mm.group(0))
    for sec in re.findall(r'<section class="card blk".*?</section>', body, re.S):
        sid = re.search(r'id="([^"]+)"', sec).group(1)
        if not re.search(r'<p class="src">Source', sec):
            bad.append("block %s has no source line" % sid)
        if re.search(r"<tbody>\s*</tbody>", sec):
            bad.append("block %s has an empty table" % sid)
    if len(re.findall(r"<h1>", body)) != 1:
        bad.append("not exactly one h1")
    bad += ui_checks(body, plain=kind_of(rel) != "trust")
    for ld in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
        try:
            j = json.loads(ld)
            if not (isinstance(j, dict) and j.get("@context") and j.get("@type")):
                bad.append("structured data without @context and @type")
        except ValueError:
            bad.append("structured data is not valid JSON")
    md = re.search(r'<meta name="description" content="([^"]*)"', h)
    if not md or not (40 <= len(md.group(1)) <= 200):
        bad.append("meta description missing or outside 40-200 characters: %r" % (md.group(1)[:40] if md else None))
    for tag in ("og:title", "og:description", "og:url", "og:image"):
        if 'property="%s"' % tag not in h and rel != "404.html":
            bad.append("missing %s" % tag)  # trust pages are where the terms are explained
    if kind_of(rel) == "gauge" and not rel.replace("\\", "/").endswith("/forecast/index.html"):
        # Line 0, first-screen contract: the stat tiles come before the first data block
        first_blk = body.find('<section class="card blk"')
        head = body[:first_blk] if first_blk > 0 else body
        for need in ('class="tile flow', 'class="tile stage', 'class="tile norm', 'class="tile trend'):
            if need not in head:
                bad.append("first screen missing %s" % need.split('"')[1])
    if kind_of(rel) == "gauge":
        gz = len(gzip.compress(h.encode("utf-8"), 6))  # what the phone downloads (Cloudflare compresses HTML); the plan's old 150 KB bar was for the raw file
        if gz > MAX_GZ:
            bad.append("page weight %d KB compressed (limit %d KB)" % (gz // 1000, MAX_GZ // 1000))
        for lab, unit in (("Latest flow", "cfs"), ("Gage height", "ft")):
            for mm in re.finditer(r"<span>%s</span><b>(.*?)<small>(?:<abbr[^>]*>)?([^<]*)" % lab, body, re.S):
                if unit not in mm.group(2) and not (lab == "Gage height" and re.sub(r"<[^>]+>", "", mm.group(1)).strip() in ("–", "")):
                    bad.append("no unit on %s: %r" % (lab, mm.group(2)))
        sub = re.search(r'<p class="sub">(.*?)</p>', body, re.S)
        if not sub or not re.search(r"observed [A-Z][a-z]{2} \d{1,2}, \d{1,2}:\d{2} [AP]M [A-Z]{2,5}", re.sub(r"<[^>]+>", "", sub.group(1))):
            bad.append("observed time without gauge-local zone label")
    return bad


def check_dir(d):
    """One pass, one page in memory at a time: only small per-page facts (title, links, link count) are kept, so 30,000 pages need megabytes, not gigabytes."""
    urlof = lambda rel: "/" + os.path.dirname(rel).replace("\\", "/") + "/" if os.path.dirname(rel) else "/"
    results, titles, links_of, n_links, rel_of, noindex_of = {}, collections.defaultdict(list), {}, {}, {}, {}
    for root, _, fs in os.walk(d):
        for f in fs:
            if f.endswith(".html") and f != "404.html":
                p = os.path.join(root, f)
                rel = os.path.relpath(p, d)
                h = open(p, encoding="utf-8").read().replace("\u00a0", " ")  # times use no-break spaces for wrapping
                results[rel] = check_html(h, rel)
                t = re.search(r"<title>(.*?)</title>", h)
                titles[t.group(1) if t else ""].append(rel)
                u = urlof(rel)
                rel_of[u] = rel
                links_of[u] = set(re.findall(r'href="(/[^"#?]*)"', h))
                noindex_of[u] = bool(re.search(r'<meta name="robots" content="noindex', h))
                n_links[u] = len(re.findall(r"<a ", h))
    site_bad = []
    urls = rel_of
    for t, rels in titles.items():
        if len(rels) > 1:
            site_bad.append("duplicate title %r on %d pages" % (t[:50], len(rels)))
    redirects = {}
    rp = os.path.join(d, "_redirects")
    if os.path.exists(rp):
        for l in open(rp, encoding="utf-8"):
            q = l.split()
            if len(q) >= 2:
                redirects[q[0]] = q[1]
    static = {"/sitemap.xml", "/robots.txt", "/favicon.svg", "/og.png", "/favicon.ico", "/status.json"} | {"/sitemap-%d.xml" % i for i in range(1, 20)}
    graph = {}
    for u, links in links_of.items():
        rel = rel_of[u]
        for href in links:
            if href not in urls and href not in redirects and href not in static:
                results[rel].append("broken internal link %s" % href)
        graph[u] = links
        k = kind_of(rel)
        if n_links[u] > BUDGET[k]:
            results[rel].append("link budget: %d links on a %s page (max %d)" % (n_links[u], k, BUDGET[k]))
    # reciprocity: a gauge page and its Forecast page (when it exists) link to each other; hub and gauge link to each other when a hub page exists
    for u in urls:
        parts = u.strip("/").split("/")
        if len(parts) >= 3 and parts[0] == "river":
            base = "/" + "/".join(parts[:3]) + "/"
            if len(parts) == 3 or (len(parts) == 4 and parts[3] == "forecast"):
                if len(parts) == 3 and base + "forecast/" in urls and base + "forecast/" not in graph.get(u, ()):
                    results[urls[u]].append("missing link to its forecast page")
                if len(parts) == 4 and base not in graph.get(u, ()):
                    results[urls[u]].append("forecast page does not link back to its gauge page")
                hub = "/river/%s/" % parts[1]
                if hub in urls and hub not in graph.get(u, ()):
                    results[urls[u]].append("no link back to hub %s" % hub)
                if hub in urls and len(parts) == 3 and base not in graph.get(hub, ()):
                    results[urls[hub]].append("hub does not link to gauge %s" % base)
    # sitemap equals page set
    sp = os.path.join(d, "sitemap.xml")
    if os.path.exists(sp):
        sm = set(re.findall(r"<loc>https://[^/]+(/[^<]*)</loc>", open(sp, encoding="utf-8").read()))
        for sub in [x for x in sm if x.endswith(".xml")]:  # sitemap index: follow the child sitemaps
            sm.discard(sub)
            cp = os.path.join(d, sub.lstrip("/"))
            if os.path.exists(cp):
                sm |= set(re.findall(r"<loc>https://[^/]+(/[^<]*)</loc>", open(cp, encoding="utf-8").read()))
        hp = os.path.join(d, "_headers")
        hdr = open(hp, encoding="utf-8").read() if os.path.exists(hp) else ""
        open_mode = not re.search(r"https://riverwaterlevels\.com/\*\s*\n\s*X-Robots-Tag: noindex", hdr)
        want = {u for u in urls if not noindex_of.get(u)} if open_mode else set(urls)
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from lib import indexing
        cfg = indexing.load(ROOT)
        if bool(cfg["open"]) != open_mode:
            site_bad.append("data/index-allow.json (open=%s) and the built _headers (noindex rule present=%s) disagree" % (cfg["open"], not open_mode))
        if open_mode:
            rvp = os.path.join(ROOT, "data", "reviews.json")
            pages = (json.load(open(rvp, encoding="utf-8")) if os.path.exists(rvp) else {}).get("pages", {})
            from lib.reviewgate import is_ship
            bad_ix = [u for u in sorted(want) if indexing.GAUGE.match(u) and not is_ship(pages.get(u), u)]
            if bad_ix:
                site_bad.append("%d indexable gauge page(s) without a SHIP review, e.g. %s" % (len(bad_ix), bad_ix[:2]))
            if want != {u for u in urls if indexing.indexable(u, cfg)}:
                site_bad.append("pages without a noindex tag differ from data/index-allow.json")
        if sm != want:
            site_bad.append("sitemap differs from the indexable page set: %d only in sitemap, %d only in site" % (len(sm - want), len(want - sm)))
    else:
        site_bad.append("no sitemap.xml")
    # reachability and depth from home
    depth = {"/": 0}
    queue = ["/"]
    while queue:
        u = queue.pop(0)
        for v in graph.get(u, ()):
            v = redirects.get(v, v)
            if v in urls and v not in depth:
                depth[v] = depth[u] + 1
                queue.append(v)
    orphans = [u for u in urls if u not in depth]
    if orphans:
        site_bad.append("%d pages not reachable from home, e.g. %s" % (len(orphans), orphans[:3]))
    deep = [u for u, k in depth.items() if k > 4]
    if deep:
        site_bad.append("pages deeper than 4 clicks: %s" % deep[:3])
    return results, site_bad, (max(depth.values()) if depth else 0)


def selftest():
    good = ('<!doctype html><title>T</title><meta name="description" content="A description that is long enough to pass the length rule."><meta property="og:title" content="t"><meta property="og:description" content="d"><meta property="og:url" content="u"><meta property="og:image" content="i"><link rel="canonical" href="%s/river/a/b/water/"><main><h1>X</h1><p class="sub">USGS gauge 1 &middot; observed Oct 15, 7:00 PM CDT &middot; 5 min old</p>'
            '<div class="hero"><div class="tile flow"><span>Latest flow</span><b>5 <small>cfs</small></b></div><div class="tile stage"></div><div class="tile norm"></div><div class="tile trend"></div></div>'
            '<section class="card blk" id="q"><h2>H</h2><p>x</p><p class="src">Source: USGS</p></section></main>' % SITE_URL)
    rel = os.path.join("river", "a", "b", "water", "index.html")
    assert check_html(good, rel) == [], check_html(good, rel)
    broken = {"no source line": good.replace('<p class="src">Source: USGS</p>', ""), "wrong canonical": good.replace("/river/a/b/", "/river/x/y/"),
              "banned undefined": good.replace("<p>x</p>", "<p>undefined</p>"), "no unit": good.replace("<small>cfs</small>", "<small></small>"), "no zone": good.replace("CDT", ""),
              "two h1": good.replace("<h1>X</h1>", "<h1>X</h1><h1>Y</h1>"),
              "jargon heading": good.replace("<h2>H</h2>", "<h2>Percentile for the date</h2>"),
              "jargon tile": good.replace('<div class="tile norm"></div>', '<div class="tile norm"><i class="ic"></i><span>Compared</span><b>23rd percentile</b></div>'),
              "empty widget": good.replace("<p>x</p>", '<div class="bars"></div>'),
              "image without size": good.replace("<p>x</p>", '<img src="/a.png" alt="a">'),
              "image without alt": good.replace("<p>x</p>", '<img src="/a.png" width="5" height="5">'),
              "sentinel value": good.replace("<p>x</p>", "<p>Water temperature -999999 degrees</p>"),
              "bad structured data": good.replace("<p>x</p>", '<script type="application/ld+json">{oops</script>'),
              "double full stop": good.replace("<p>x</p>", "<p>That is the 82nd percentile..</p>"),
              "heading skip": good.replace("<p>x</p>", "<h4>Deep</h4>"),
              "claims a page that does not exist": good.replace("<p>x</p>", "<p>The Forecast page has the river forecast.</p>"),
              "page weight": good.replace("<p>x</p>", "<p>" + hashlib.sha256(b"a").hexdigest() * 0 + "".join(hashlib.sha256(str(i).encode()).hexdigest() for i in range(2600)) + "</p>"),
              "sentence twice": good.replace("<p>x</p>", "<p>" + "The same long sentence about the river repeated on the page. " * 1 + "</p><p>" + "The same long sentence about the river repeated on the page. " + "</p>")}
    for name, h in broken.items():
        assert check_html(h, rel), "selftest: broken fixture passed: " + name
    print("selftest OK: good fixture passes, %d broken fixtures all fail" % len(broken))


SECRET = re.compile(r"(?i)(api[_-]?key|x-api-key|secret|authorization|bearer|cloudflare_api_token)[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{20,}")


def secret_scan(d):
    """No key, token or secret in any built text file, and none of this machine's own key values."""
    bad, own = [], [v for k_, v in os.environ.items() if k_ in ("USGS_API_KEY", "CLOUDFLARE_API_TOKEN") and len(v) >= 12]
    for root, _, fs in os.walk(d):
        for f in fs:
            if f.endswith((".png", ".gz", ".ico")):
                continue
            t = open(os.path.join(root, f), encoding="utf-8", errors="ignore").read()
            if SECRET.search(t) or any(v in t for v in own):
                bad.append(os.path.relpath(os.path.join(root, f), d))
    return bad


def main():
    if "--selftest" in sys.argv:
        return selftest()
    d = next((a for a in sys.argv[1:] if not a.startswith("--")), os.path.join(ROOT, "dist_next"))
    res, site_bad, maxd = check_dir(d)
    fails = {k: v for k, v in res.items() if v}
    for k, v in fails.items():
        print("FAIL", k)
        for x in v[:8]:
            print("   ", x)
    for x in site_bad:
        print("SITE FAIL", x)
    leaks = secret_scan(d)
    for x in leaks[:5]:
        print("SITE FAIL secret-like text in built file", x)
    site_bad += ["secret-like text in %d built file(s)" % len(leaks)] if leaks else []
    print("pages %d, failing %d, site-level failures %d, max click depth from home %d" % (len(res), len(fails), len(site_bad), maxd))
    sys.exit(1 if (fails or site_bad) else 0)


main()
