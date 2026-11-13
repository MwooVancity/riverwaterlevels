"""Which pages may be indexed: the per-batch kill switch. One file decides: data/index-allow.json = {"open": false, "site_pages": false, "allow": []}.
- open false (the pre-launch hold): the production hosts send X-Robots-Tag: noindex for every page (templates/_headers) and every page also carries <meta name="robots" content="noindex,follow">.
- open true: the header rule for the production hosts is removed. A page is indexable only when it is allowed: gauge pages (and their Forecast page) only if the gauge URL is in "allow";
  every other page (home, state, river hubs, trust pages, status) only if "site_pages" is true. Every other page keeps <meta name="robots" content="noindex,follow"> and is left out of sitemap.xml.
- To pull a batch back: remove its URLs from "allow" (or set open false) and deploy; the next 30-minute refresh serves noindex for them. Search engines drop a page only after they recrawl it, so this is fast to apply and slow to take effect: release small batches."""
import json, os, re

GAUGE = re.compile(r"^/(?:river/[^/]+/[^/]+|lake/[^/]+|coast/[^/]+)/(forecast/)?$")  # lakes enter Google only through open_wave too (review 2026-11-06)
DEFAULT = {"open": False, "site_pages": False, "allow": []}


def load(root):
    p = os.path.join(root, "data", "index-allow.json")
    cfg = dict(DEFAULT)
    if os.path.exists(p):
        cfg.update(json.load(open(p, encoding="utf-8")))
    cfg["allow"] = set(cfg.get("allow") or [])
    cfg["pulled"] = set(cfg.get("pulled") or [])  # any page pulled by hand (open_wave --pull): world pages are site pages, so the allow list alone could not pull one
    try:  # owner 2026-11-09 "pages that slip through gates": a world feed listed in data/world-pages.json with "hold" stays noindex (and off the sitemap), hub and pages, until its phone review passes
        cfg["held"] = tuple("/%s/" % w["slug"] for w in json.load(open(os.path.join(root, "data", "world-pages.json"), encoding="utf-8")) if w.get("hold"))
    except (OSError, ValueError, KeyError, TypeError):
        cfg["held"] = ()
    cfg["research_ok"] = research_reviewed(root)
    cfg["research_demand"] = research_demand(root)
    if os.environ.get("RWL_NOINDEX"):  # preview builds (preview.yml): every page noindex
        cfg["open"] = False
    return cfg


def research_demand(root):
    """PLAN 24 lock 6 (systemic): research pages with at least one seed phrasing (data/research-keywords.csv) that Keyword Planner measured with searches
    (data/keyword-tiers-water.csv, the one demand file). A seed never asked is not demand; a missing or torn file = none (fail closed)."""
    import csv
    norm = lambda k: " ".join(str(k or "").lower().split())
    try:
        kw = {norm(r["keyword"]) for r in csv.DictReader(open(os.path.join(root, "data", "keyword-tiers-water.csv"), encoding="utf-8")) if str(r.get("tier") or "0").replace(".", "", 1).isdigit() and float(r["tier"]) > 0}
        return {r["url"] for r in csv.DictReader(open(os.path.join(root, "data", "research-keywords.csv"), encoding="utf-8")) if norm(r["seed"]) in kw}
    except (OSError, ValueError, KeyError):
        return set()


def research_reviewed(root):
    """PLAN 22 lock 1: research pages whose current method version passed a fresh peer review (data/reviewed.json "research": {url: method}).
    METHOD is read from lib/research.py's text (no import: indexing stays light). A torn file or no METHOD = none (fail closed)."""
    try:  # each page's own version (data/research-methods.json): a fix reopens only the page it touched
        ms = json.load(open(os.path.join(root, "data", "research-methods.json"), encoding="utf-8"))
        rv = json.load(open(os.path.join(root, "data", "reviewed.json"), encoding="utf-8")).get("research") or {}
        return {u for u, v in rv.items() if ms.get(u) and v == ms[u]}
    except (OSError, ValueError, AttributeError):
        return set()


def indexable(url, cfg):
    if not cfg["open"] or url.startswith(("/embed/river/", "/embed/lake/", "/embed/coast/")) or url == "/status/":  # embed panels are framed copies of the gauge page; /status/ is an operations page
        return False
    if url in cfg.get("pulled", ()):
        return False
    if url.startswith(tuple(cfg.get("held") or ())):
        return False
    if GAUGE.match(url):
        return url.replace("forecast/", "") in cfg["allow"]
    if url.startswith("/research/"):  # PLAN 20: only when open_wave allows them; PLAN 22: and only when a fresh peer review passed this exact method version
        dem, ok = cfg.get("research_demand") or set(), cfg.get("research_ok") or ()
        if url == "/research/":  # the index opens when any finding below it is open
            return url in cfg["allow"] and url in ok and any(u in cfg["allow"] and u in ok for u in dem)
        return url in cfg["allow"] and url in ok and url in dem  # PLAN 24: no measured search demand, no Google
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


def stuck_line(o):
    """The watchdog's alarm text for data/open-wave-last.json: live pages held out of Google for a fixable reason, else None."""
    return "%d live page(s) never opened to Google: %s" % (len(o["stuck"]), "; ".join(o["stuck"][:3])) if (o or {}).get("stuck") else None
