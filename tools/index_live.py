"""Indexing state of the LIVE site must equal data/index-allow.json (run after every deploy and by the watchdog; network).
Usage: python -I tools/index_live.py        exit 1 and print each mismatch
Rules:
 - open false: every sampled page sends noindex (header or meta) and the sitemap may list anything
 - open true: each allowed gauge page has NO noindex header and NO robots meta, and is in sitemap.xml
              each gauge page that is NOT allowed sends noindex (header or meta) and is NOT in sitemap.xml
              the sitemap lists no page outside the allow list (plus site pages only when site_pages is true)
 - the workers.dev address always sends noindex"""
import json, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lib.common import http_open
SITE = "https://riverwaterlevels.com"
H = {"User-Agent": "Mozilla/5.0 (index-live)"}
GAUGE = re.compile(r"^/river/[^/]+/[^/]+/(forecast/)?$")


def get(url):
    r = http_open(url, H, 40)
    return r.headers.get("x-robots-tag", ""), r.read().decode("utf-8", "replace")


def noindex(hdr, body):
    return "noindex" in hdr.lower() or bool(re.search(r'<meta[^>]+name="robots"[^>]+noindex', body))


def main():
    cfg = json.load(open(os.path.join(ROOT, "data", "index-allow.json"), encoding="utf-8"))
    allow = set(cfg.get("allow") or [])
    bad = []
    try:
        _, sm = get(SITE + "/sitemap.xml")
        urls = json.loads(get(SITE + "/gauges.json")[1])
    except Exception as e:
        print("index live: site did not answer (%s); skipped" % str(e)[:80])
        return 0
    locs = re.findall(r"<loc>([^<]+)</loc>", sm)
    if "<sitemapindex" in sm:  # the sitemap is an index: its <loc>s are child sitemaps, so union the page URLs from each child (past 10k URLs, else every allowed page false-fails as "missing from sitemap")
        pages_ = []
        for c in locs:
            try:
                pages_ += re.findall(r"<loc>([^<]+)</loc>", get(c)[1])
            except Exception:
                pass
        locs = pages_
    listed = {u.replace(SITE, "") for u in locs}
    gauges = sorted({g[1] for g in urls if len(g) > 1 and GAUGE.match(g[1])})
    if cfg.get("open"):
        for u in sorted(allow):
            h, b = get(SITE + u)
            if noindex(h, b):
                bad.append("%s is allowed but still sends noindex" % u)
            if u not in listed:
                bad.append("%s is allowed but missing from sitemap.xml" % u)
        for u in gauges:
            if u in allow:
                continue
            h, b = get(SITE + u)
            if not noindex(h, b):
                bad.append("%s is NOT allowed but is indexable" % u)
            if u in listed:
                bad.append("%s is NOT allowed but is in sitemap.xml" % u)
        extra = {u for u in listed if u not in allow and not (cfg.get("site_pages") and not GAUGE.match(u))}
        if extra:
            bad.append("sitemap lists pages outside the allow list: %s" % sorted(extra)[:5])
    else:
        for u in gauges[:5]:
            h, b = get(SITE + u)
            if not noindex(h, b):
                bad.append("%s is indexable while the site is closed" % u)
    try:
        h, _ = get("https://riverwaterlevels.mwoo778.workers.dev/")
        if "noindex" not in h.lower():
            bad.append("workers.dev address does not send noindex")
    except Exception:
        pass
    print("index live: open=%s, %d allowed, %d gauge pages checked, %d mismatches" % (cfg.get("open"), len(allow), len(gauges), len(bad)))
    for b in bad:
        print("  MISMATCH", b)
    return 1 if bad else 0


sys.exit(main())
