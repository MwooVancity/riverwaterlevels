"""Build-integrity checks (not index gates). Usage: python -I check.py [dir]   |   python -I check.py --selftest
Per page: canonical, banned strings, doubled words, source line per block, units, gauge-local time, one h1, weight.
Site: unique titles, every internal link resolves, sitemap equals page set, tab/hub/state reciprocity, link budgets, no orphans, depth from home.
Exit 1 if anything fails.
"""
import os, re, sys, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.common import ROOT, SITE_URL

BANNED = [r"prototype", r"licen[cs]e", r"\bConf\b", r"\bSr\d{3,}", r"__[A-Z_]+__", r"\bundefined\b", r"\bNaN\b", r"\bNone\b", r"Unnamed [a-z ]*(boat ramp|fishing spot)"]
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
    for mm in re.finditer(r"\b(\w+) \1\b", text, re.I):
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
    bad += ui_checks(body, plain=kind_of(rel) != "trust")  # trust pages are where the terms are explained
    if kind_of(rel) == "gauge" and not rel.replace("\\", "/").endswith("/forecast/index.html"):
        # Line 0, first-screen contract: the stat tiles come before the first data block
        first_blk = body.find('<section class="card blk"')
        head = body[:first_blk] if first_blk > 0 else body
        for need in ('class="tile flow', 'class="tile stage', 'class="tile norm', 'class="tile trend'):
            if need not in head:
                bad.append("first screen missing %s" % need.split('"')[1])
    if kind_of(rel) == "gauge":
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
    results, titles, links_of, n_links, rel_of = {}, collections.defaultdict(list), {}, {}, {}
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
        if sm != set(urls):
            site_bad.append("sitemap differs from page set: %d only in sitemap, %d only in site" % (len(sm - set(urls)), len(set(urls) - sm)))
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
    good = ('<!doctype html><title>T</title><link rel="canonical" href="%s/river/a/b/water/"><main><h1>X</h1><p class="sub">USGS gauge 1 &middot; observed Oct 15, 7:00 PM CDT &middot; 5 min old</p>'
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
              "heading skip": good.replace("<p>x</p>", "<h4>Deep</h4>"),
              "sentence twice": good.replace("<p>x</p>", "<p>" + "The same long sentence about the river repeated on the page. " * 1 + "</p><p>" + "The same long sentence about the river repeated on the page. " + "</p>")}
    for name, h in broken.items():
        assert check_html(h, rel), "selftest: broken fixture passed: " + name
    print("selftest OK: good fixture passes, %d broken fixtures all fail" % len(broken))


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
    print("pages %d, failing %d, site-level failures %d, max click depth from home %d" % (len(res), len(fails), len(site_bad), maxd))
    sys.exit(1 if (fails or site_bad) else 0)


main()
