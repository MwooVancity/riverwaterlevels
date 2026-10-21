"""Which pages may be indexed: the per-batch kill switch. One file decides: data/index-allow.json = {"open": false, "site_pages": false, "allow": []}.
- open false (the pre-launch hold): the production hosts send X-Robots-Tag: noindex for every page (templates/_headers) and every page also carries <meta name="robots" content="noindex,follow">.
- open true: the header rule for the production hosts is removed. A page is indexable only when it is allowed: gauge pages (and their Forecast page) only if the gauge URL is in "allow";
  every other page (home, state, river hubs, trust pages, status) only if "site_pages" is true. Every other page keeps <meta name="robots" content="noindex,follow"> and is left out of sitemap.xml.
- To pull a batch back: remove its URLs from "allow" (or set open false) and deploy; the next 30-minute refresh serves noindex for them. Search engines drop a page only after they recrawl it, so this is fast to apply and slow to take effect: release small batches."""
import json, os, re

GAUGE = re.compile(r"^/river/[^/]+/[^/]+/(forecast/)?$")
DEFAULT = {"open": False, "site_pages": False, "allow": []}


def load(root):
    p = os.path.join(root, "data", "index-allow.json")
    cfg = dict(DEFAULT)
    if os.path.exists(p):
        cfg.update(json.load(open(p, encoding="utf-8")))
    cfg["allow"] = set(cfg.get("allow") or [])
    return cfg


def indexable(url, cfg):
    if not cfg["open"]:
        return False
    if GAUGE.match(url):
        return url.replace("forecast/", "") in cfg["allow"]
    return bool(cfg["site_pages"])


def robots_meta(url, cfg):
    return "" if indexable(url, cfg) else '<meta name="robots" content="noindex,follow">'


def sitemap_ok(url, cfg):
    """In hold mode the sitemap lists every page (nothing is indexable anyway, and it keeps the structure testable); in open mode only indexable pages."""
    return True if not cfg["open"] else indexable(url, cfg)


def headers(template_text, cfg):
    """templates/_headers with the production noindex rules removed when the site is open (the workers.dev address always stays noindex)."""
    if not cfg["open"]:
        return template_text
    out, skip = [], False
    for line in template_text.splitlines():
        if re.match(r"https://(www\.)?riverwaterlevels\.com/\*", line):
            skip = True
            continue
        if skip and line.startswith((" ", "\t")) and "X-Robots-Tag" in line:
            skip = False
            continue
        skip = False
        out.append(line)
    return "\n".join(out) + "\n"
