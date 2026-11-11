"""Which blocks the built gauge pages really show, by country, so a build that quietly ships less is seen. Read by tools/watchdog.py through status.json.
ponytail: reads every gauge page, about 2 s per 1,000 pages, 30 s at 14,000; sample one in ten if a build needs the time."""
import glob, os, re

MIN_PAGES = 20  # a share over fewer pages moves with one gauge
DROP = 0.7  # under 70% of a block's best share ever
CORE = 0.9  # only a block once on nearly every page (German alerts went 57% to 14% as warnings ended, 2026-11-03): blocks that show only when the river or weather calls for them swing every day (NWM guidance 18% to 8%, 2026-11-03)


def country(rel):
    """First path part decides: US lakes and coasts were counted as Germany until 2026-11-10 (12 false 'blocks vanished' alarms)."""
    top = rel.replace("\\", "/").split("/")[0]
    return "US" if top in ("river", "lake", "coast") else top.title() if top in ("canada", "england", "ireland") else "Germany"


def scan(root, old=None):
    """{"shares": {country: {block: share}}, "best": {...}, "drops": [...]}. A block is counted once per page."""
    seen = {}
    for p in glob.glob(os.path.join(root, "**", "index.html"), recursive=True):
        h = open(p, encoding="utf-8", errors="ignore").read()
        if 'class="hero hero2' not in h or '"BreadcrumbList"' not in h:  # a reader's gauge page; embed panels share the hero but no breadcrumb (264 US panels were counted as Germany, 2026-11-11)
            continue
        c = country(os.path.relpath(p, root))
        d = seen.setdefault(c, {"pages": 0, "blocks": {}})
        d["pages"] += 1
        for b in set(re.findall(r'<section [^>]*class="card blk"[^>]*id="(\w+)"', h)):
            d["blocks"][b] = d["blocks"].get(b, 0) + 1
    best, drops, shares = dict((old or {}).get("best") or {}), [], {}
    for c, d in seen.items():
        shares[c] = {"pages": d["pages"], "blocks": {b: round(n / d["pages"], 3) for b, n in sorted(d["blocks"].items())}}
        if d["pages"] < MIN_PAGES:
            continue
        for b, was in (best.get(c) or {}).items():
            if was >= CORE and shares[c]["blocks"].get(b, 0) < DROP * was:
                drops.append("%s %s on %.0f%% of pages, was %.0f%%" % (c, b, 100 * shares[c]["blocks"].get(b, 0), 100 * was))
        best[c] = {b: max(shares[c]["blocks"].get(b, 0), (best.get(c) or {}).get(b, 0)) for b in set(shares[c]["blocks"]) | set(best.get(c) or {})}
    return {"shares": shares, "best": best, "drops": drops[:12]}
