"""Gate 1 page and site checks. Usage: python -I check.py [dir]   |   python -I check.py --selftest
Per page: canonical, banned strings, doubled words, source line per block, units, gauge-local time, one h1, weight.
Site: unique titles, every internal link resolves, sitemap equals page set, tab/hub/state reciprocity, link budgets, no orphans, depth from home.
Exit 1 if anything fails.
"""
import glob
import os, re, sys, json, collections, gzip, hashlib, html, datetime, csv
MAX_GZ = 90000  # pilot pages are about 48 KB compressed; tail pages carry fewer blocks
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.common import ROOT, SITE_URL, MOJI, demoji, r1

BANNED = [r"(?<![\d.,])\b1 (?:gauges|rivers|years|days|hours|readings)\b",  # "View all 1 gauges" on the live home page (crawl 2026-11-04)
          r"\bin our data\b", r"\bpage as built\b", r"live check did not answer", r"\(water first\)",  # hater round 2 (2026-10-27): builder's jargon a reader cannot parse
          r"\bForecast page\b", r"\bsecond .{0,20}page\b", r"prototype", r"(?<!FERC )licen[cs]e(?!d under the Open Government| - Canada)", r"\bConf\b", r"\bSr\d{3,}", r"__[A-Z_]+__", r"\bundefined\b", r"\bNaN\b", r"\bNone\b", r"Unnamed [a-z ]*(boat ramp|fishing spot)", r"-?\b9{5,}\b", r"(?<!ZIP )(?<!\d)-?999\d{2,}\b", r"\b20\d\d-\d\d-\d\d[T ]\d\d:\d\d", r"&lt;/?[a-zA-Z]+[\s>&/]"]  # last: source HTML shown to the reader as text (NWS impact link, Clear Creek 2026-10-26)  # the last three (the ISO one: a raw machine timestamp shown to a reader; the other two: USGS sentinel values (-999999) must never be shown as readings)
MAX_BYTES = 260_000  # raw HTML; the reader limit is MAX_GZ (90 KB compressed). Raised 2026-10-21 for the camera, air-quality and recreation blocks (Roaring Fork 231 KB raw, 56 KB gzipped)
BUDGET = {"gauge": 125, "hub": 80, "state": 700, "home": 300, "world": 125, "country": 700, "trust": 60, "status": 600}  # status 2026-10-25: the freshness dashboard links every gauge (69 at 53 gauges); own budget so it doesn't share the prose-page trust cap. At scale (~500+ gauges) the status page needs pagination - a known scale item, like the state 480-link ceiling.  # trust 40->60 2026-10-21 (footer "Add to your site" + status page); gauge 110->125 2026-10-23: new data blocks (stocking, UV, sustained flow, access points) each add source/record links on data-heavy gauges like the Potomac  # world 60->125 2026-11-05: a world gauge page is the same standard page as a US one (owner decision 2)
NEIGHBOURS = 3  # census line only (owner 2026-11-09: no forced internal links; an isolated page links none and is reached through its hub)
FLOOR = {"hub": 700, "home": 1500, "trust": 300, "country": 300, "state": 650}  # min visible chars for an INDEXABLE page; a thinner indexable page reads as thin/near-duplicate to Google. State hubs carry statewide drought + NWS alerts + a conditions table (~1000+ chars); the 650 floor catches a genuinely broken/empty hub while tolerating a transient missing-drought blip. 2026-10-23: the long-tail thin-page guard the whole-project review flagged as missing. Owner 2026-11-08: no thin gate on a water page (gauge, world): a different river or lake is never thin; the floor stays only on hubs and site pages, where it catches a broken empty template.


WORLD = {p["slug"] for p in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "world-pages.json"), encoding="utf-8"))}


CARRYABLE = ("gauge", "world", "country", "hub", "state", "home", "status", "trust")  # a failing page keeps its live copy and the rest ship (2026-11-03: one German ramp name held every page 3 h; readiness debate 2026-11-07: a hub or state page stopped the whole site, so every kind carries; a page with no live copy still stops it)


def kind_of(rel):
    parts = rel.replace("\\", "/").split("/")
    if rel == "index.html":
        return "home"
    if parts[0] == "rivers":
        return "state"
    if parts[0] == "status":  # the all-gauges freshness dashboard: one link per gauge, grows with the site, not a prose page
        return "status"
    if parts[0] in WORLD and len(parts) == 3:
        return "world"
    if parts[0] in WORLD:  # a country or river hub links every gauge it lists: the state budget, never the 60 of a prose page (at 60 the 46th gauge refused every deploy, review 2026-11-04)
        return "country"
    if parts[0] == "river":
        return "hub" if len(parts) == 3 else "gauge"
    if parts[0] in ("lake", "coast"):  # a lake page is a gauge page: every gauge check runs on it (review 2026-11-06)
        return "gauge"
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
    for im in re.findall(r"<img\b[^>]*>", body)[1:]:  # below the first screen: download when scrolled to, not up front (weak signal)
        if 'loading="lazy"' not in im or 'decoding="async"' not in im:
            bad.append("image after the first without loading=lazy and decoding=async: %s" % im[:60])
    seen = collections.Counter(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", p)).strip() for p in re.findall(r"<p>(.*?)</p>", body, re.S))
    for s, n in seen.items():
        if n > 1 and len(s) >= 60:
            bad.append("sentence stated %d times: %r" % (n, s[:60]))
    return bad


READ = {"pages": 0, "wide": 0, "wide_pages": 0, "eg": ""}
DOOR = collections.defaultdict(list)  # gauge id -> [(url, minhash)]; PLAN 0j


def door_sig(h):
    """(gauge id, 64-value MinHash of the page's visible words with its own name words removed) or None. Small per page, so 14,000 pages fit in memory.
    Owner decision 4 (narrowed 2026-11-09): two places on one gauge are two pages, but one that is the other word for word with the name swapped is a doorway page."""
    gid = re.search(r'<p class="sub">([^<&]+?)\s*&middot;', h)  # every kind names its station first: "USGS gauge 06041000", "NOAA tide station 8443970", "Gauge 4091" (first draft read var ID: US rivers only, so the census said 0)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
    if not gid or not h1:
        return None
    own = set(re.findall(r"[a-z0-9]+", html.unescape(re.sub(r"<[^>]+>", " ", h1.group(1))).lower()))
    body = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S))).lower()
    w = [x for x in re.findall(r"[a-z]+", body) if x not in own]  # words only: the readings and times differ by build minute, not by page
    sh = {" ".join(w[i:i + 5]) for i in range(max(1, len(w) - 4))}
    return gid.group(1).strip(), tuple(min(int(hashlib.md5((str(k) + s).encode()).hexdigest()[:8], 16) for s in sh) for k in range(64))


def door_pairs(door, cut=0.95):
    """[(url a, url b, similarity)] for pages on one gauge whose text (own name removed) is cut or more the same."""
    out = []
    for g, ps in door.items():
        for i in range(len(ps)):
            for j in range(i + 1, len(ps)):
                sim = sum(a == b for a, b in zip(ps[i][1], ps[j][1])) / 64
                if sim >= cut:
                    out.append((ps[i][0], ps[j][0], sim))
    return out


def readability(h, rel):
    """Readability census (CLAUDE.md 'readable at a glance'): tables with more than 5 columns. Warns, never blocks, until near zero."""
    n = sum(1 for t in re.findall(r"<thead><tr>(.*?)</tr></thead>", h, re.S) if t.count("<th") > 5)
    READ["pages"] += 1
    READ["wide"] += n
    if n:
        READ["wide_pages"] += 1
        READ["eg"] = READ["eg"] or rel


def wide_tables(h):
    """CLAUDE.md 'readable at a glance': at most 5 columns. Census reached 0 on 2026-11-09 (from 966), so it is a page rule now: a new block cannot bring a wide table back."""
    n = [t.count("<th") for t in re.findall(r"<thead><tr>(.*?)</tr></thead>", h, re.S) if t.count("<th") > 5]
    return ["table with %d columns (max 5: readable at a glance)" % n[0]] if n else []


def control_chars(texts):
    """No control character in the stylesheet or the page code (2026-11-09, three times in one day: a shell heredoc turned a CSS or Python escape into a raw byte;
    the tile toggle drew a box instead of its arrow). texts: {name: text}."""
    return ["%s holds control character 0x%02x" % (n, ord(c)) for n, t in texts.items() for c in sorted(set(t)) if ord(c) < 32 and c not in "\n\r\t"]


def colour_contrast(css):
    """Colour coding by kind (tile labels, block dots) must be readable as small text: every light-mode --f-* family colour at least 4.5:1 on white (WCAG AA). Found 2026-11-09: forecast 3.19, area 3.77."""
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    light = re.search(r":root\{[^}]*--f-fc:#[0-9a-fA-F]{6}[^}]*\}", css)
    bad = []
    for name, hx in re.findall(r"--(f-[a-z]+):#([0-9a-fA-F]{6})", light.group(0) if light else ""):
        r = (1.05) / (lum(hx) + 0.05)
        if r < 4.5:
            bad.append("colour %s #%s is %.2f:1 on white, under 4.5" % (name, hx, r))
    return bad


def page_checks(h, rel):
    """Every check that judges one page alone. The site gate and tools/release.py page_check both call this one function, so a new gauge the release
    passes cannot fail the gate on a per-page rule (release 2026-11-07: the stats rule ran only at the gate and undid all 25 picks)."""
    u = "/" + os.path.dirname(rel).replace(os.sep, "/").replace("\\", "/") + "/" if os.path.dirname(rel) else "/"
    out = check_html(h, rel) + ((rank_checks(h, u) + hater_rules(h)) if kind_of(rel) == "gauge" else []) + wide_tables(h)
    sid = re.search(r'var ID="USGS-(\d{7,15})"', h) or re.search(r"USGS (?:lake )?gauge (\d{8,15})\b", h)  # gate audit 2026-11-08: visible wording differs by kind (coast "NOAA tide station", agency lakes), so their cache claims never ran; the page script's id is on every US kind
    cp = os.path.join(ROOT, "cache", sid.group(1) + ".json") if sid else None
    if cp and os.path.exists(cp):
        out += claims_vs_cache(h, json.load(open(cp, encoding="utf-8")))
    return out + ad_gaps(rel, h) + stats_gap(h) + datum_named(h, u)


DATUMS = ("mean lower low water", "NAVD 1988", "NGVD 1929", "IGLD 1985", "the reservoir's own datum", "the reservoir&#x27;s own datum", "the datum the operator uses", "the gauge datum", "Ordnance Datum Malin")


def datum_named(h, u):
    """ChatGPT audit 2026-11-05 item 1, agreed and never built until the scale debate 2026-11-07: a lake or coast elevation is a height above a datum,
    and the page must say which (NGVD 1929 and NAVD 1988 differ by feet at Lanier; Irish tide heights are above Ordnance Datum Malin, not chart datum)."""
    if not u.startswith(("/lake/", "/coast/")) or 'data-live="stage"' not in h:
        return []
    return [] if any("above " + d in h for d in DATUMS) else ["a lake or coast elevation without its datum: say 'above <datum>' (allowed: %s)" % ", ".join(DATUMS[:5])]


def stats_gap(h):
    """Wave 3 2026-10-27: "is this normal" blank on 6 of 6 pages while the USGS statistics file was in the repo. One function for the site gate and
    tools/release.py page_check (release 2026-11-07: two new gauges passed the release's check and failed this one at the gate, undoing all 25)."""
    sid = re.search(r'var ID="USGS-(\d{7,15})"', h) or re.search(r"USGS (?:lake )?gauge (\d{8,15})\b", h)  # gate audit 2026-11-08: visible wording differs by kind (coast "NOAA tide station", agency lakes), so their cache claims never ran; the page script's id is on every US kind
    stp = os.path.join(ROOT, "legacy", "stats", sid.group(1) + ".json") if sid else None
    if re.search(r'rel="canonical" href="[^"]*/lake/', h):  # practice 2026-11-08 (Falls Lake, Lake Brownwood): a lake's stats file is often another parameter (flow, gage height), and lib/hero.py compares only the same code; a missing lake comparison is a gap, never a false fact
        return []
    if stp and "no published statistics for this date" in h and os.path.exists(stp) and sum(1 for r in (json.load(open(stp)).get("d") or {}).values() if r[2] is not None and r[8] is not None) >= 300:
        return ["says 'no published statistics' while legacy/stats holds this gauge's USGS daily statistics"]
    return []


def neg_zero(h):
    """Phone reviews 2026-11-07 (Honolulu 1612340, Atlantic City 8518750): '-0.0 ft' printed for a tide low of -0.04 ft. Found twice, so a rule."""
    m = re.search(r"(?<![\w.])[-−]0\.0+(?![\d])(?:\s|&nbsp;| )*(ft|m|cm|in|°)", h)
    return "prints '%s' (negative zero): round first, then format" % m.group(0) if m else None


def foreign_usgs(h):
    """A USGS label or link carrying an id USGS does not use (CDEC-SHA): the reading's source named wrongly, or a dead USGS link (agency lakes 2026-11-07)."""
    m = re.search(r"USGS(?:-| lake gauge | gauge | )(?!PAD-US)([A-Z]{2,}-[A-Za-z0-9]+)", h)  # review 2026-11-07 #4: TWDB ids are lower case
    return "names USGS for %s, an id USGS does not use (name the operator's feed)" % m.group(1) if m else None


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
    if not rel.replace("\\", "/").startswith("embed/"):  # an embed is a self-contained iframe page; every other page shares one cacheable stylesheet
        if not re.search(r'<link rel="stylesheet" href="/(site|dir)\.[0-9a-f]{10}\.css">', h):
            bad.append("page does not link the cacheable stylesheet (inline CSS is re-sent with every page)")
        if '<link rel="manifest" href="/manifest.webmanifest">' not in h:
            bad.append("page does not link the web app manifest (add to home screen)")
        for st in re.findall(r"<style[^>]*>(.*?)</style>", h, re.S):
            if len(st.encode()) > 2048:
                bad.append("inline <style> of %d bytes (limit 2048): it belongs in the shared stylesheet" % len(st.encode()))
    if "<main" not in h:
        return bad + ["no <main>"]
    body = h.split("<main", 1)[1].split("</main>")[0]
    text = re.sub(r"<[^>]+>", " ", re.sub(r"<br\s*/?>|</t[dh]>", " | ", re.sub(r"(?s)<(pre|code|textarea)\b.*?</\1>", " ", body)))  # code samples (the embed snippet, its copy box on each page) are meant to show markup; a line or cell break is a break, not a space ("Truckee<br>Truckee River")
    for mm in re.finditer(r"fetch\(\s*['\"](https?:)?//[^'\"]*waterdata\.usgs\.gov", h):  # USGS is the one keyed, metered API: readings come from our stored copy (NWS alerts are keyless and stay direct)
        bad.append("page script calls USGS directly (%r): live readings must come from our stored copy" % h[mm.start():mm.start() + 60])
    for pat in BANNED:
        for mm in re.finditer(pat, text):
            bad.append("banned %r near %r" % (pat, text[max(0, mm.start() - 25):mm.end() + 25].strip()))
    own = re.sub(r'(?s)<section[^>]*id="(?:flood_impacts|low_water|alerts|hydronotes)".*?</section>', " ", body)  # quoted NWS text is never reworded: "Meramec State Park park is flooded" is the NWS's own sentence (release 2026-11-07)
    own = re.sub(r"<[^>]+>", " ", re.sub(r"<br\s*/?>|</t[dh]>", " | ", re.sub(r"(?s)<(pre|code)\b.*?</\1>", " ", own)))
    for mm in re.finditer(r"\b([A-Za-z]+) \1\b", own, re.I):  # words only: "19 19" is a day and an hour in "2026-10-19 19:38", not a typo
        if mm.group(1).lower() not in ("had", "that", "walla", "ro", "bora", "baden"):  # real names: Walla Walla River, a German "Ro Ro Anlage" ramp (2026-11-03)
            bad.append("doubled word %r near %r" % (mm.group(0), own[max(0, mm.start() - 40):mm.end() + 40].strip()))
    for sec in re.findall(r'<section class="card blk".*?</section>', body, re.S):
        sid = re.search(r'id="([^"]+)"', sec).group(1)
        if not re.search(r'<p class="src">Source', sec):
            bad.append("block %s has no source line" % sid)
        if re.search(r"<tbody>\s*</tbody>", sec):
            bad.append("block %s has an empty table" % sid)
    if len(re.findall(r"<h1>", body)) != 1:
        bad.append("not exactly one h1")
    bad += ui_checks(body, plain=kind_of(rel) not in ("trust", "country"))
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
        fb_ = re.search(r'<section class="card blk"(?![^>]*id="gauge_not_reporting")', body)  # the not-reporting banner is the one block allowed above the tiles
        first_blk = fb_.start() if fb_ else -1
        head = body[:first_blk] if first_blk > 0 else body
        for need in ('class="tile flow', 'class="tile stage', 'class="tile norm', 'class="tile trend'):
            if need == 'class="tile trend' and ("Tidal reach:" in head or "Rose and fell:" in head or "Today&#x27;s tides (NOAA prediction)" in head or "Today's tides (NOAA prediction)" in head):  # a coast shows today's tides, not a tidal 24 h change
                continue  # a tidal reach has no 6 h direction; hero.py prints the day's range instead
            if need not in head:
                bad.append("first screen missing %s" % need.split('"')[1])
        # the edge swaps in a newer reading; everything the build derived from the old one (class word, trend, summary) must be marked dv so it gets its own "as of" time
        if 'class="tile norm' in head and not re.search(r'class="tile norm[^"]*\bdv\b', head):
            bad.append("first screen: the is-this-normal tile is not marked dv (would show an old class under a swapped reading with no time)")
        if '<p class="answer"' in head and not re.search(r'class="a2 dv\b', head):
            bad.append("first screen: the summary class is not marked dv")
        # owner 2026-11-09 "readable at a glance": place (H1), then one status sentence, then the numbers
        a_, t_, h_ = head.find('<p class="answer"'), head.find('class="tile '), head.find("<h1")
        if a_ < 0 or not (h_ < a_ < t_ or t_ < 0):
            bad.append("first screen: the status sentence is missing or not between the place name and the tiles")
    # a tile's caption must say something its value does not (2026-10-25: "5p to 6p" / "5p to 6p: no thunder ...")
    for mm in re.finditer(r'<div class="tile [^"]*">(?:(?!</div>).)*?<b>(.*?)</b>((?:(?!</div>).)*)</div>', body, re.S):
        val = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", mm.group(1))).strip()
        cap = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", mm.group(2)))
        if len(val) >= 3 and re.search(r"[A-Za-z0-9]", val) and cap.strip().startswith(val):  # a caption that OPENS with the value repeats it; a range that happens to contain it ("Tidal reach: 11,400 to 15,000 cfs") does not
            bad.append("tile caption repeats its own value %r" % val)
    if kind_of(rel) == "gauge":
        gz = len(gzip.compress(h.encode("utf-8"), 6))  # what the phone downloads (Cloudflare compresses HTML); the plan's old 150 KB bar was for the raw file
        if gz > MAX_GZ:
            bad.append("page weight %d KB compressed (limit %d KB)" % (gz // 1000, MAX_GZ // 1000))
        for lab, unit in (("Latest flow", "cfs"), ("Gage height", "ft")):
            for mm in re.finditer(r"<span>%s</span><b>(.*?)<small>(?:<abbr[^>]*>)?([^<]*)" % lab, body, re.S):
                if unit not in mm.group(2) and re.search(r"\d", re.sub(r"<[^>]+>", "", mm.group(1))):  # a number needs its unit; "Not measured" has no number
                    bad.append("no unit on %s: %r" % (lab, mm.group(2)))
        sub = re.search(r'<p class="sub">(.*?)</p>', body, re.S)
        if not sub or not re.search(r"(?:observed|tide predictions, times in [A-Z]{2,5} \S+ fetched) [A-Z][a-z]{2} \d{1,2}(?:, \d{1,2}:\d{2} [AP]M [A-Z]{2,5}| \([A-Za-z]+ daily (?:average|value)\))", re.sub(r"<[^>]+>", "", sub.group(1))):  # a daily average has a date, never a clock time (TWDB: lib/page.py agency_words)
            bad.append("observed time without gauge-local zone label")
    for r_ in re.findall(r"<tr>.*?</tr>", h, re.S):  # a row of a gauge that stopped reporting over 24 h ago must not carry a 24 h change
        if 'class="oldm"' in r_ and re.search(r'<td class="r"[^>]*>(?:&#\d+; )?(?:[+-]\d+|0)%</td>', r_):
            bad.append("a 24 h change % is shown for a gauge whose newest reading is over 24 h old")
            break
    if re.search(r"<th(?![^>]*\bscope=)[ >]", h):
        bad.append("a table header cell has no scope (a screen reader cannot tie a cell to its column)")
    return bad


def claims_vs_cache(h, rec, now=None):
    """A page that says a value is missing while our own cache holds it fresh has hidden data (Memphis: 'no gage height' while NWS MEMT1 observed it)."""
    import datetime
    now = now or datetime.datetime.now(datetime.timezone.utc)
    bad = []
    zl = re.search(r'<p class="sub">.*?(?:observed|fetched) [A-Z][a-z]{2} \d{1,2}, \d{1,2}:\d{2} [AP]M ([A-Z]{2,5})\b', h, re.S)
    from lib.core import usgs_tz
    tzn_ = usgs_tz(rec) or rec.get("tz")  # the page's own rule (lib/hero.py ctx): the zone USGS publishes for the site first (northern Idaho County is Pacific; the coordinate lookup said Boise)
    if zl and tzn_:  # gate audit 2026-11-08: the zone label was checked for existence only; it must be the gauge's own zone (standard or daylight)
        import zoneinfo
        try:
            z_ = zoneinfo.ZoneInfo(tzn_)
            ok_ = {datetime.datetime(now.year, m, 15, 12, tzinfo=z_).tzname() for m in (1, 7)} | {now.astimezone(z_).tzname()}
            if zl.group(1) not in ok_:
                bad.append("observed time labelled %s, but this gauge's zone %s is %s" % (zl.group(1), tzn_, "/".join(sorted(ok_))))
        except (zoneinfo.ZoneInfoNotFoundError, ValueError):
            pass
    o = (rec.get("nwps") or {}).get("obs_stage") or {}
    try:
        fresh = (now - datetime.datetime.fromisoformat(o["t"].replace("Z", "+00:00"))).total_seconds() < 24 * 3600 and float(o["v"]) > -999
    except (KeyError, TypeError, ValueError, AttributeError):
        fresh = False
    if fresh and re.search(r"<span>Gage height</span><b>Not measured", h):
        bad.append("gage height shown as not measured while NWS %s observed it at %s" % ((rec.get("nwps") or {}).get("lid"), o["t"]))
    if (rec.get("tides") or {}).get("rows") and "tide predictions (no NOAA station" in h:
        bad.append("gaps line says no tide station while the cache holds NOAA tide predictions")
    lv = (rec.get("coops") or {}).get("level")
    if lv and "At NOAA station %s, " % lv["id"] not in h:  # edge case 3, handoff 2026-11-08a: a reading from another place shown as this place's
        bad.append("water level read at NOAA %s but the page does not name that station and its distance" % lv["id"])
    own = (rec.get("coops") or {}).get("station")
    if lv and own and ("NOAA tide station %s &middot; observed" % own in h or "(NOAA CO-OPS %s, observed" % own in h):  # review 2026-11-08 blockers 1-2: the own id beside an observed time
        bad.append("NOAA %s has predictions only, yet the page shows it beside an observed time" % own)
    if (rec.get("coops") or {}).get("tables"):  # tide tables (owner decision 3): no reading here, so no observed time or reading number; the nearest live level is named, never shown
        if re.search(r'<p class="sub">(?:(?!</p>).)*observed', h, re.S) or 'data-live="stage"' in h:
            bad.append("tide-tables station %s shows an observed time or a reading" % rec["coops"].get("station"))
        if "No sensor at this station. Nearest live NOAA water level:" not in h:
            bad.append("tide-tables page does not name the nearest live NOAA water level")
    return bad


def world_claims(h, rows):
    """A world page's level against the cached row it was built from, when both hold the same reading time: a unit or conversion slip, or another station's number, is a defect of the highest rank (owner 2026-11-02). Exact to the shown rounding; no network, so a river moving during the run never blocks."""
    n, v = re.search(r'class="hero[^"]*" data-n="([^"]+)" data-t="([^"]+)"', h), re.search(r'data-live="stage">(-?[\d.,]+)', h)
    r = next((x for x in rows if n and x.get("name") == n.group(1)), None)
    if not v or not r or r.get("cm") is None or not r.get("time") or datetime.datetime.fromisoformat(n.group(2)) != datetime.datetime.fromisoformat(r["time"].replace("Z", "+00:00")):
        return []
    shown, tol = float(v.group(1).replace(",", "")), (0.006 if r.get("unit") == "m" else 0.6)
    return [] if abs(shown - r["cm"]) <= tol else ["level on the page %s, the cached reading it was built from %s %s at the same time: a unit, conversion or station slip" % (v.group(1), r["cm"], r.get("unit") or "cm")]


def cloak_risks(js):
    """Google's cloaking rule: crawlers and people must get the same page. The edge Worker therefore never reads the visitor's identity."""
    pat = r"""(?i)\b(?:req|request)\.(?:cf\b|headers\.get\(\s*["'](?:user-agent|sec-ch-ua[\w-]*|cf-ipcountry|cf-connecting-ip|x-forwarded-for|cf-bot[\w-]*)["'])"""
    return ["edge worker reads the visitor's identity (%s): Google and phones could get different pages" % m.group(0) for m in re.finditer(pat, js)]


TIMER_ONLY = ("pollWorld", "poll", "build", "start")  # worker functions run by the cron, never by a visitor's request


def visitor_calls(js):
    """Outside calls the Worker could make while serving a visitor: every fetch( that is not env.ASSETS.fetch must sit inside a timer-only function."""
    spans = []
    for name in TIMER_ONLY:
        m = re.search(r"async function %s\(" % name, js)
        if m:
            i, depth = js.index("{", m.end()), 0
            for j in range(i, len(js)):
                depth += {"{": 1, "}": -1}.get(js[j], 0)
                if depth == 0:
                    spans.append((m.start(), j))
                    break
    return ["edge worker calls an outside service outside its timer (line %d): visitors would spend API calls" % (js.count("\n", 0, m.start()) + 1)
            for m in re.finditer(r"(?<![\w.])(?<!async )fetch\(", js) if not any(a <= m.start() <= b for a, b in spans)]


def edge_drift(js):
    """The edge worker cannot import Python, so its copies are compared here: its age text must be AGE_FN (lib/page.py) character for character, and its
    age-chip cut-offs must be STALE_H chip_fresh and chip_ageing (lib/core.py) in minutes. A fix in one copy only would show two ages or two colours."""
    from lib.render import AGE_FN, STALE_H
    bad = [] if AGE_FN in js else ["worker/index.js age() differs from AGE_FN in lib/page.py: the edge and the page would print different ages"]
    from lib.core import UNIT_OF
    if '(k === "f" ? "%s" : "%s")' % (UNIT_OF["00060"], UNIT_OF["00065"]) not in js:  # edge test 2026-11-07: the Worker swaps live numbers; it must refuse the units lib/core.py refuses
        bad.append("worker/index.js does not refuse a flow or stage unit other than lib/core.py UNIT_OF (%s, %s)" % (UNIT_OF["00060"], UNIT_OF["00065"]))
    m = re.search(r"const AGE_CHIP_MIN = \[(\d+), (\d+)\];", js)
    want = (round(STALE_H["chip_fresh"] * 60), round(STALE_H["chip_ageing"] * 60))
    if not m or (int(m.group(1)), int(m.group(2))) != want:
        bad.append("worker/index.js AGE_CHIP_MIN is not STALE_H chip_fresh/chip_ageing in minutes %s: the edge would colour the age chip differently from the page" % (want,))
    return bad


def sw_drift(js):
    """templates/sw.js cannot import Python: its saved-page age must be AGE_FN (lib/page.py) character for character, like the worker's."""
    from lib.render import AGE_FN
    return [] if AGE_FN in js else ["sw.js age() differs from AGE_FN in lib/page.py: the offline line and the page would print different ages"]


def rank_checks(h, url):
    """A gauge page must answer the search it ranks for: title and H1 name the river and place, the title says 'water level', the first
    screen (before the first data block) says nothing three times, and the page links at least 3 other gauge pages (nearby, up and down)."""
    bad = []
    if 'class="hero' not in h:
        return bad
    title = re.sub(r"\s+", " ", (re.search(r"<title>(.*?)</title>", h, re.S) or [None, ""])[1])
    h1 = re.sub(r"<[^>]+>", "", (re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S) or [None, ""])[1]).strip()
    words = [w for w in re.findall(r"[A-Za-z]{4,}", h1) if w.lower() not in ("river", "creek", "fork", "below", "above", "near")]
    if len(words) < 1 or len(h1.split()) < 3:  # "Rio Grande at Albuquerque, NM" has no word 'river' and is fine
        bad.append("H1 %r does not name the river and place" % h1)
    miss = [w for w in words if w.lower() not in title.lower()]
    wl_ = "water level" in title.lower() or "tide table" in title.lower()  # a tide-tables page has no water level: its search is the tide table
    if miss or not wl_:
        bad.append("title %r does not match the search (missing %s)" % (title[:80], ", ".join(miss + ([] if wl_ else ["water level"]))))
    main = h.split("<main", 1)[1] if "<main" in h else h
    first = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style|svg)\b.*?</\1>", " ", main.split('class="card blk"', 1)[0]))).lower()
    w = re.findall(r"[a-z0-9:.%]+", first)
    grams = {}
    for i in range(len(w) - 5):
        g = " ".join(w[i:i + 6])
        grams[g] = grams.get(g, 0) + 1
    name = " ".join(re.findall(r"[a-z0-9:.%]+", h1.lower()))  # the page's own name in breadcrumb, H1 and cite is anatomy, not clutter
    rep = [(g, n) for g, n in grams.items() if n >= 3 and not re.fullmatch(r"[\d\s:.%]+", g) and g not in name]
    if rep:
        g, n = max(rep, key=lambda x: x[1])
        bad.append("first screen says %r %d times (clutter on the screen that decides the click)" % (g, n))
    return bad


def css_truncation(css):
    """Reader text is never cut off with an ellipsis or a line clamp (hater 2026-10-27: 'No sensor at this ga...' hid where 48 F came from)."""
    return ["site.css cuts reader text off (%s)" % m.group(0) for m in re.finditer(r"text-overflow\s*:\s*ellipsis|line-clamp\s*:", css)]


def one_latest(h):
    """Truth gate checks each number against the agency alone; this checks the page never shows two different latest values of one measure."""
    bad = []
    fq_ = re.search(r'id="flow_chart".*?Latest, [^<]*</td><td[^>]*>([\d,.]+)', h, re.S)
    aq_ = re.search(r'id="also_measured".*?<td>Flow</td><td[^>]*>([\d,.]+)', h, re.S)
    if fq_ and aq_ and fq_.group(1) != aq_.group(1):  # audit 2026-11-05: Ottawa 526 m³/s in the chart beside 517 m³/s measured now
        bad.append("two different latest flows on one page (%s and %s)" % (fq_.group(1), aq_.group(1)))
    return bad


def queue_over(queue, tiers):
    """Queue rows that claim more searches than Keyword Planner gave their keyword (keyword debate 2026-11-06: 'myrtle beach tides' sat at 50,000, the file says 5,000).
    A lower queue number can be a deliberate rule (shared names step down, flow-only capped); a higher one is always wrong."""
    return ["queue row %s: %r at %s, Keyword Planner %s" % (r.get("rank"), r["keyword"], r["tier"], tiers[r["keyword"].lower()])
            for r in queue if r.get("keyword") and r["keyword"].lower() in tiers and int(r["tier"] or 0) > int(tiers[r["keyword"].lower()] or 0)]


def reuse_barred(sources):
    """Owner HARD rule 2026-11-05: a source whose terms bar ads, commercial use or caching is never used, and no permission is asked.
    A row records it as "ads", "commercial" or "cache": "barred"; such a row may never be quoted or owner-permission (blocks show only those)."""
    return ["source %s shows on pages but its terms bar %s: use another official source or link out" % (r.get("id"), ", ".join(k for k in ("ads", "commercial", "cache") if r.get(k) == "barred"))
            for r in sources if r.get("status") in ("quoted", "owner-permission") and any(r.get(k) == "barred" for k in ("ads", "commercial", "cache"))]


def hater_rules(h):
    """Defects the first hater round found on every page that a machine can see in the built HTML."""
    bad = []
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))
    kf_ = re.search(r'<section[^>]*id="key_facts".*?</section>', h, re.S)
    if 'id="about_gauge"' in h and not kf_:  # owner 2026-11-04: quotable stable facts for Google's AI answers on every page whose gauge data allows them
        bad.append("no Key facts block while the gauge's station record is on the page")
    if kf_ and ("data-live=" in kf_.group(0) or re.search(r"\b(?:today|now|currently|latest)\b", re.sub(r"<[^>]+>", " ", re.sub(r"<p class=\"src\">.*?</p>", "", kf_.group(0), flags=re.S)), re.I)):  # a quoted copy must never read as today's level
        bad.append("Key facts hold a live reading or a word for now: a cached quote would show it as today's")
    bad += one_latest(h)
    tn_ = re.search(r"<title>(.*?)(?:\((?:USGS|NOAA) |</title>)", h)  # coast titles end "(NOAA <station>)"
    if tn_ and re.search(r"\b\d{7,}\b", tn_.group(1)):  # 2026-10-31: "Apple River above 05341499": a gauge number in the place name. release.py sends it back to the queue
        bad.append("a gauge number inside the page name: add a line to data/name-overrides.csv")
    if re.search(r'(?:NWS|National Weather Service)\s*<span class="tag t-official">', h):  # newcomer review: "...as issued by NWS  OFFICIAL NWS" says it twice
        bad.append("a block heading ends in NWS right before its 'Official NWS' tag")
    if re.search(r"[A-Za-z] \)", re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", re.sub(r"(?is)<(script|style|svg)\b.*?</\1>", " ", h)))):  # "StreamCat )" and "thinned for display)": a stray bracket in a source line
        bad.append("a space before a closing bracket in reader text")
    if re.search(r"Thunderstorms: none", t):
        row = re.search(r"Thunder %((?:\s+[\d\u2013-]+)+)", t)
        if row and any(x.isdigit() and int(x) > 0 for x in row.group(1).split()):
            bad.append("says 'Thunderstorms: none' while the hourly table shows a thunder chance above 0")
    rt_ = re.sub(r"(?i)(href|src|title|aria-label|data-[a-z-]+|id)=\"[^\"]*\"", "", re.sub(r'(?is)<head>.*?</head>|<(script|style|svg)\b.*?</\1>|<details class="srcd">.*?</details>|<p class="src">.*?</p>', " ", h))
    tt_ = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", rt_))
    m = re.search(r"(?<!station )\b[A-Z]{4}\d\b(?! \()", tt_)  # a weather station ID printed with its name ("station WGRM8 (WEST GLACIER)") is labelled, not a bare point code
    if m:  # audit run 1, row 9: "NWS point MEMT1" on the first screen; the point's code belongs in Source text and link titles, reader text uses its name
        bad.append("an NWS forecast point code (%s) in reader text outside Source: ...%s..." % (m.group(0), tt_[max(0, m.start() - 70):m.end() + 30]))
    if re.search(r'(?s)id="gauge_not_reporting".{0,300}Older than', h):  # row 8: the banner says the real age ("2 d old"), not a limit
        bad.append("the not-reporting banner says 'Older than N h' instead of the real age")
    if any(sec.count("(unnamed)") > 1 for sec in re.findall(r"(?s)<section.*?</section>", h)):  # row 12: seven "(unnamed)" rows read as padding
        bad.append("more than one '(unnamed)' row in one block")
    m = re.search(r"(?<![\d.,])\b1 (hours|days|years|miles|minutes) (ago|earlier|before|away)", t)  # not the tail of "1.1 days ago"
    if m:
        bad.append("ungrammatical %r" % m.group(0))
    rf_ = re.search(r'id="river_forecast".*?</section>', h, re.S)
    if rf_:  # w12 review: neighbouring forecast cards printing the same level and flow
        vals_ = re.findall(r'<div class="rc[^"]*"><span class="rt">[^<]*</span><b>(.*?)</b>(?:<small>(.*?)</small>)?</div>', rf_.group(0))
        if any(a_ == b_ for a_, b_ in zip(vals_, vals_[1:])):
            bad.append("two neighbouring forecast cards print the same values")
    if ("Forecast high" in t or "Highest forecast" in t) and ("NWS forecast (steady)" in t or "no rise above the latest reading" in t):
        bad.append("the forecast is called 'Forecast high' and also steady or at/below the reading on one page")
    dw_ = re.search(r"(Steady|Rising|Falling): ([+-]?\d+(?:\.\d+)?)% flow in 6 h", t)
    rc_ = re.search(r"Last 6 h \S+ [+-]?[\d.]+% ([+-])([\d,]+) cfs", t)
    if dw_ and rc_:  # w18 FAIL: "Steady" beside a 6 h change of -3.4% and -40 cfs; the word follows flow_dir (2 % and 5 cfs)
        pct_, cfs_ = float(dw_.group(2)), int(rc_.group(2).replace(",", ""))
        want_ = "Steady" if abs(pct_) < 2 or cfs_ < 5 else ("Rising" if pct_ > 0 else "Falling")
        if dw_.group(1) != want_:
            bad.append("direction word %r beside a 6 h change of %s%% and %s cfs (the rule gives %s)" % (dw_.group(1), dw_.group(2), cfs_, want_))
    if MOJI.search(t):
        bad.append("garbled characters %r: agency text decoded twice" % MOJI.search(t).group(0))
    imp = re.search(r'id="flood_impacts".*?</section>', h, re.S)
    if imp and len(re.findall(r">Next(?: impact at|:) ", imp.group(0))) > 1:
        bad.append("more than one flood-impact card labelled 'Next:'")
    m = re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2} last year\b", t)
    if m:
        bad.append("%r reads as the wrong day on a page about today" % m.group(0))
    if re.search(r"<text[^>]*>,\d", h):
        bad.append("a chart axis label is cut off on the left (starts with a comma)")
    from lib.common import band_word, PCT_PHRASE
    for m in re.finditer(r"\b(\d{1,3})(?:st|nd|rd|th) percentile, ([a-z ]+?)(?:[.,;)]|$)", t):
        want = PCT_PHRASE[band_word(int(m.group(1)))]
        if m.group(2).strip() != want:
            bad.append("%r: the USGS band for that percentile is %r (same words as the headline)" % (m.group(0)[:60], want))
    if re.search(r"\bat not stated\b", t):
        bad.append("placeholder text 'at not stated' shown to readers")
    # hater round 4
    m = re.search(r"\b0\d:\d\d [AP]M\b", t)
    if m:
        bad.append("hour with a leading zero %r" % m.group(0))
    m = re.search(r"(?:&#9650;|&#9660;|\u25b2|\u25bc) ?[+-]?[01]\.\d%", t)
    if m:
        bad.append("up/down arrow on a change under 2%% %r (the headline calls that steady)" % m.group(0))
    if re.search(r"the guide's label for", t):
        bad.append("a cold-water row quotes another band's label")
    heads = re.findall(r"<h2[^>]*>(.*?)</h2>", h, re.S)
    dup = {x for x in heads if heads.count(x) > 1}
    if dup:
        bad.append("two blocks share the title %r" % sorted(dup)[0][:60])
    if re.search(r"(?i)\bMONITOR\b[^.]{0,20}\bnot stated\b|<td>not stated</td>", h):
        bad.append("an air-quality monitor shown as 'not stated'")
    a_, b_ = re.search(r"Next NWS impact at ([\d.]+)", t), re.search(r"Next impact at ([\d.]+)", t)
    if a_ and b_ and a_.group(1) != b_.group(1):
        bad.append("gage tile says next impact %s ft, the impacts block says %s ft" % (a_.group(1), b_.group(1)))
    m = re.search(r"thunder chance of up to (\d+)%", t)
    row = re.search(r"Thunder %((?:\s+[\d–-]+)+)", t)
    if m and row and str(max([int(x) for x in row.group(1).split() if x.isdigit()] or [0])) != m.group(1):
        bad.append("thunder 'up to %s%%' does not match the hourly Thunder %% row" % m.group(1))
    hm = re.search(r'<table class="hm">.*?</table>', h, re.S)
    for lab in re.findall(r'<tr><th scope="row">([^<]*)</th>', hm.group(0) if hm else ""):
        if len(html.unescape(lab)) > 14:
            bad.append("hourly table label %r is too wide for the phone's first column" % lab)  # final review: "Rain or snow (water) in/h" overlapped its first value
    # hater round 5
    for m in re.finditer(r'<svg[^>]*aria-label="(Gage height|Flow)[^"]*"[^>]*>(.*?)</svg>', h, re.S):
        if not re.search(r">(ft|cfs)</text>", m.group(2)):
            bad.append("a %s chart with no unit on its axis" % m.group(1).lower())
    if re.search(r"(?i)\bsame as above\b|for most of these sites", t):
        bad.append("a row points at another row ('same as above') instead of printing its value")
    # hater round 6 (2026-10-27)
    m = re.search(r"\b\d{4,} (dams|days|stations|gauges|readings)\b", t)
    if m:
        bad.append("count without a thousands comma %r" % m.group(0))
    if re.search(r"(?<!where the )NWS and USGS read this gauge on different zero points", t) and "starts off the reading" in t:  # the stated gap, not the general "where the ... differ" note (CI 2026-10-27: Hudson at Green Island, no gap)
        bad.append("compares an NWS forecast level with the USGS reading although the page says they use different zero points")
    gaps = re.search(r'<p class="gaps">(.*?)</p>', h, re.S)
    if gaps and "hourly weather" in gaps.group(1) and re.search(r'id="hourly_(forecast|heatmap)"', h):
        bad.append("'Not available: hourly weather' on a page that shows the hourly forecast block")
    for m in re.finditer(r'<section[^>]*id="([a-z_]+)"[^>]*>(.*?)</section>', h, re.S):
        body = re.sub(r'<p class="src[^"]*".*?</p>|<h2.*?</h2>|<header.*?</header>|<footer.*?</footer>', "", m.group(2), flags=re.S)
        if not re.search(r"<(table|svg|img|iframe|video|canvas)\b", body) and len(re.sub(r"<[^>]+>|\s+", "", body)) < 15:
            bad.append("block %r has a heading and source but no data" % m.group(1))
    # hater wave 4 (2026-10-28): each FAIL type once, as a rule
    for m in re.finditer(r'<section[^>]*id="([a-z_]+)"[^>]*>(.*?)</section>', h, re.S):
        if "t-live" in m.group(2) and re.search(r"older than 24 h\)|(day|days|month|months|years) before this page was built", m.group(2)):
            bad.append("block %r is badged live but shows a reading older than a day" % m.group(1))
        if m.group(1) == "river_forecast" and m.group(2).count('class="rc') > 12:
            bad.append("river forecast shows more than 12 cards")
        if m.group(1) == "air_obs" and ("data-wxst" not in m.group(2) or "querySelector('[data-wxst]')" not in h):
            bad.append("weather-station block cannot refresh in the browser (no data-wxst marker or no WX_JS)")
        if m.group(1) == "air_obs" and "NWS station " not in m.group(2):
            bad.append("weather-station block does not name its station")
    m = re.search(r"Next NWS impact at [\d.,]+ ft \(([\d.,]+) ft above", t)
    if m and float(m.group(1).replace(",", "")) > 100:
        bad.append("next NWS impact %s ft above the reading: the thresholds are not stages (published as flow?)" % m.group(1))
    if "live water temperature (no USGS temperature sensor" in t and re.search(r"<td>Water temperature</td>", h):
        bad.append("says there is no water temperature sensor while the sensor table shows one")
    # page polish 2026-10-29
    hl = re.search(r'<table class="hm hlist[^"]*">.*?</table>', h, re.S)
    if hl and re.search(r"<td[^>]*>(?:N|NNE|NE|ENE|E|ESE|SE|SSE|S|SSW|SW|WSW|W|WNW|NW|NNW) \d", hl.group(0)):
        bad.append("hourly list prints wind as compass letters ('WNW 2' wraps on a phone); use the wind arrow")
    if re.search(r'<section class="card blk" [^>]*id="no_river_forecast"', h):
        bad.append("'no river forecast issued' drawn as a full card; a valid-empty state is one grey line (block(..., empty=True))")
    # honest data age (audit run 1, 2026-10-29)
    if re.search(r'class="tile alrt[^"]*\bstale\b[^"]*">(?:(?!</div>).)*<b>No alerts</b>', h, re.S) or re.search(r'id="alerts".{0,400}?Older than.{0,300}?No active National Weather Service alerts were returned', h, re.S):
        bad.append("says 'No alerts' beside an NWS alert check older than 3 h (say Unknown and how long ago)")
    m_ = re.search(r"No active National Weather Service alerts in [^<]*", t)
    if m_ and "checked" not in m_.group(0):  # batch D: a state page says when the alert check ran, and never "right now"
        bad.append("a state page says 'No active National Weather Service alerts' without the check time")
    if 'id="gauge_not_reporting"' in h and re.search(r'<small class="dv">(?:Steady|Rising|Falling|Unsteady)|<small class="word">', h):
        bad.append("a direction word on a gauge that is not reporting (say 'Trend unknown (gauge not reporting)')")
    if foreign_usgs(h):
        bad.append(foreign_usgs(h))
    if neg_zero(h):
        bad.append(neg_zero(h))
    rt_ = re.search(r'class="tile rain(?![^"]*stale)[^"]*">.{0,400}?data-h="(\d+(?:\.\d+)?)"', h, re.S)
    if rt_ and float(rt_.group(1)) > 6:  # STALE_H["rain_totals"]
        bad.append("a rain tile shows an estimate older than 6 h as current (say 'Unknown: last estimate N ago')")
    ft_ = re.search(r'class="tile fcst(?![^"]*stale)[^"]*">(?:(?!</div>).)*?data-h="(\d+(?:\.\d+)?)"', h, re.S)
    if ft_ and float(ft_.group(1)) > 24:  # STALE_H["river_forecast"]; batch F
        bad.append("the forecast tile shows a river forecast older than 24 h as current (add the age and the stale class, like the River forecast block)")
    if re.search(r"<td>Water temperature</td>", h) and 'class="tile wtemp' not in h and not re.search(r"water temperature at this (?:gauge|station)", t):  # a coast page says 'station' (break test 2026-11-07)
        bad.append("a water-temperature reading exists but its first-screen tile is hidden and the 'Not available' line does not name it with its age")
    if re.search(r"<h1>[^<]*[a-z] (?:Of|The|And|Near|At|Above|Below) [^<]*</h1>", h):
        bad.append("the H1 capitalises a small word (of/the/and/near/at/above/below) inside a name")
    tl_ = re.search(r"<title>(.*?)</title>", h, re.S)
    if 'id="gauge_not_reporting"' in h and tl_ and re.search(r"\blive\b", tl_.group(1), re.I):
        bad.append("the title of a not-reporting gauge says 'live'")
    if re.search(r'class="hero hero2".*?id="gauge_not_reporting"', h, re.S):
        bad.append("the not-reporting banner sits below the tiles; it belongs directly under the H1")
    if tl_ and re.search(r"\blive\b", tl_.group(1), re.I):  # audit run 5 row 4: the title is static; "live" over a reading older than 2 x the USGS stale limit (6 h) is false
        from lib.core import stale_after
        ch_ = re.search(r'data-live="age"[^>]*>(\d+) (min|h|d)</span>', h)
        if ch_ and int(ch_.group(1)) * {"min": 1 / 60, "h": 1, "d": 24}[ch_.group(2)] > stale_after("usgs") * 2:
            bad.append("the title says 'live' over a reading older than %d h" % (stale_after("usgs") * 2))
    if 'id="gauge_not_reporting"' in h and 'id="rate_of_change"' in h and "These changes end at the last report" not in h:
        bad.append("a not-reporting gauge's rate of rise and fall block does not say its windows end at the last report")
    if 'aria-label="Link to this section"' in h:
        bad.append("section links are all named 'Link to this section' (name each by its heading)")
    h2s_ = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r'(?s)<span class="tag.*?</span>|<a class="pl".*?</a>', "", x))).strip().lower() for x in re.findall(r"<h2\b[^>]*>(.*?)</h2>", h, re.S)]
    if any(a_ and a_ == b_ for a_, b_ in zip(h2s_, h2s_[1:])):  # a section heading and the block under it with the same words (audit run 5 row 8: "River forecast" twice)
        bad.append("two consecutive h2 headings are the same words")
    if '<div class="tile ' in h and '<span>Rain, last 24 h</span>' not in h and 'id="gauge_not_reporting"' not in h and 'class="gaps"' in h and "Rain, last 24 h (" not in h:
        bad.append("no 24 h rain tile and the 'Not available' line does not name the 24 h rain total")
    return bad


def glossary_gaps(h):
    """The glossary states exactly the cut-offs band_word uses (audit run 5 row 1)."""
    from lib.common import band_glossary
    t_ = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))
    return [] if band_glossary() in t_ else ["the glossary does not state the band_word cut-offs (lib/common.py BAND_CUTS)"]



def check_dir(d):
    """One pass, one page in memory at a time: only small per-page facts (title, links, link count) are kept, so 30,000 pages need megabytes, not gigabytes."""
    urlof = lambda rel: "/" + os.path.dirname(rel).replace("\\", "/") + "/" if os.path.dirname(rel) else "/"
    results, titles, links_of, n_links, rel_of, noindex_of, vis_of = {}, collections.defaultdict(list), {}, {}, {}, {}, {}
    world_rows = {}
    for root, _, fs in os.walk(d):
        for f in fs:
            if f.endswith(".html") and f != "404.html":
                p = os.path.join(root, f)
                rel = os.path.relpath(p, d)
                h = open(p, encoding="utf-8").read().replace("\u00a0", " ")  # times use no-break spaces for wrapping
                readability(h, rel)
                results[rel] = page_checks(h, rel) + (world_rules(h) + one_latest(h) if kind_of(rel) == "world" else [])
                if rel.replace("\\", "/") == "glossary/index.html":
                    results[rel] += glossary_gaps(h)
                if kind_of(rel) == "world":
                    slug = rel.replace("\\", "/").split("/")[0]
                    if slug not in world_rows:
                        wp = os.path.join(ROOT, "cache", "_river-%s.json" % slug)
                        world_rows[slug] = json.load(open(wp, encoding="utf-8")).get("rows", []) if os.path.exists(wp) else []
                    results[rel] += world_claims(h, world_rows[slug])
                t = re.search(r"<title>(.*?)</title>", h)
                titles[t.group(1) if t else ""].append(rel)
                u = urlof(rel)
                rel_of[u] = rel
                sig_ = door_sig(h) if kind_of(rel) in ("gauge", "world") else None
                if sig_:
                    DOOR[(rel.replace("\\", "/").split("/")[0] if kind_of(rel) == "world" else "") + sig_[0]].append((u, sig_[1]))  # a world 'Gauge 4091' is per country feed
                    READ["door_pages"] = READ.get("door_pages", 0) + 1
                links_of[u] = set(re.findall(r'href="(/[^"#?]*)"', h))
                noindex_of[u] = bool(re.search(r'<meta name="robots" content="noindex', h))
                n_links[u] = len(re.findall(r"<a ", h))
                vis_of[u] = len(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S))))
    site_bad = []
    urls = rel_of
    wjs = open(os.path.join(ROOT, "worker", "index.js"), encoding="utf-8").read()
    site_bad += ["%s missing from the build" % f for f in ("sw.js", "manifest.webmanifest", "icon-192.png", "icon-512.png") if not os.path.exists(os.path.join(d, f))]
    if os.path.exists(os.path.join(d, "sw.js")):
        site_bad += sw_drift(open(os.path.join(d, "sw.js"), encoding="utf-8").read())
    wps_ = json.load(open(os.path.join(ROOT, "data", "world-pages.json"), encoding="utf-8"))
    wsl_ = [p_["slug"] for p_ in (wps_ if isinstance(wps_, list) else wps_.get("pages", []))]
    site_bad += slug_clash(wsl_, {rel_.replace("\\", "/").split("/")[0] for rel_ in results if "/" in rel_.replace("\\", "/") and kind_of(rel_) not in ("world", "country")})
    site_bad += cloak_risks(wjs) + visitor_calls(wjs) + edge_drift(wjs) + css_truncation(open(os.path.join(ROOT, "templates", "site.css"), encoding="utf-8").read()) + colour_contrast(open(os.path.join(ROOT, "templates", "site.css"), encoding="utf-8").read()) + control_chars({f: open(os.path.join(ROOT, f), encoding="utf-8").read() for f in ["templates/site.css", "worker/index.js"] + ["lib/" + x for x in os.listdir(os.path.join(ROOT, "lib")) if x.endswith(".py")]})
    import csv as _csv
    live_now = {r["site"] for r in _csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8")) if r["status"] == "live"}
    lsp = os.path.join(d, "live-sites.json")  # judge the gauge pages actually built, not only the list (2026-10-27: 22 queued gauges were built and published)
    live_now |= {r[0] for r in json.load(open(lsp, encoding="utf-8"))} if os.path.exists(lsp) else set()
    for t, rels in titles.items():  # gate audit 2026-11-08: a page-level fault of one new page must hold that page, never the whole release
        if len(rels) > 1:
            if all(kind_of(r_) in CARRYABLE for r_ in rels):
                for r_ in rels:
                    results[r_].append("duplicate title %r on %d pages" % (t[:50], len(rels)))
            else:
                site_bad.append("duplicate title %r on %d pages" % (t[:50], len(rels)))
    redirects = {}
    rp = os.path.join(d, "_redirects")
    if os.path.exists(rp):
        for l in open(rp, encoding="utf-8"):
            q = l.split()
            if len(q) >= 2:
                redirects[q[0]] = q[1]
        site_bad += redirect_limit(len(redirects))
    n_files = sum(len(f) for _, _, f in os.walk(d))
    if n_files > 15000:
        print("WARNING: %d files in the deploy; Cloudflare refuses past 20,000. Drop the embed copies or move data.json to the Worker before 19,000." % n_files)
    site_bad += file_limit(n_files)
    sp = os.path.join(d, "single-rivers.json")
    if os.path.exists(sp):
        redirects.update(json.load(open(sp, encoding="utf-8")))
    static = {"/sitemap.xml", "/robots.txt", "/favicon.svg", "/og.png", "/favicon.ico", "/status.json", "/llms.txt", "/ads.txt", "/live-sites.json", "/_health.json"} | {"/sitemap-%d.xml" % i for i in range(1, 20)}
    static |= {"/" + f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))}  # the stylesheets carry a content hash in their name: the file must exist
    graph = {}
    for u, links in links_of.items():
        rel = rel_of[u]
        for href in links:
            if href not in urls and href not in redirects and href not in static and not href.endswith("/data.json"):
                results[rel].append("broken internal link %s" % href)
        graph[u] = links
        k = kind_of(rel)
        if n_links[u] > BUDGET[k]:
            results[rel].append("link budget: %d links on a %s page (max %d)" % (n_links[u], k, BUDGET[k]))
        if not noindex_of.get(u) and k in FLOOR and vis_of.get(u, 0) < FLOOR[k]:
            results[rel].append("thin: %d visible chars on an indexable %s page (min %d) - enrich it (noindex is never the fix)" % (vis_of.get(u, 0), k, FLOOR[k]))
    water_ = {u for u in links_of if kind_of(rel_of[u]) in ("gauge", "world")}
    inb = collections.Counter(v for u in water_ for v in links_of[u] if v in water_ and v != u)
    for k_ in sorted({kind_of(rel_of[u]) for u in water_}):  # links rule 7: inbound measured, not only outbound (census in every run's log)
        us_ = [u for u in water_ if kind_of(rel_of[u]) == k_]
        i_, o_ = sorted(inb[u] for u in us_), sorted(len({x for x in links_of[u] if x in water_ and x != u}) for u in us_)
        print("links census %s: %d pages, inbound min %d median %d, outbound min %d median %d, %d with under %d inbound" % (k_, len(us_), i_[0], i_[len(i_) // 2], o_[0], o_[len(o_) // 2], sum(1 for x in i_ if x < NEIGHBOURS), NEIGHBOURS))
    print("readability census: %d pages, %d tables over 5 columns on %d pages%s" % (READ["pages"], READ["wide"], READ["wide_pages"], (", e.g. " + READ["eg"]) if READ["eg"] else ""))
    dp_ = door_pairs(DOOR)
    print("doorway census: %d pages read, %d stations carry 2+ pages, %d page pairs 95%%+ the same text with the name removed%s" % (READ.get("door_pages", 0), sum(1 for v in DOOR.values() if len(v) > 1), len(dp_), (", e.g. %s = %s (%.0f%%)" % (dp_[0][0], dp_[0][1], 100 * dp_[0][2])) if dp_ else ""))
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
        try:
            car_ = {"/" + r.replace("\\", "/").rsplit("index.html", 1)[0] for r in json.load(open(os.path.join(d, "_carried.json")))}
        except (OSError, ValueError):
            car_ = set()
        sm_urls = [u for u in urls if u not in car_]  # a new name: urls stays the url -> file map the orphan step below reads (review run 42543656099 crashed here)
        sm -= car_
        want = {u for u in sm_urls if not noindex_of.get(u)} if open_mode else set(sm_urls)
        from lib import indexing
        cfg = indexing.load(ROOT)
        if bool(cfg["open"]) != open_mode:
            site_bad.append("data/index-allow.json (open=%s) and the built _headers (noindex rule present=%s) disagree" % (cfg["open"], not open_mode))
        if open_mode:
            ix_ = {u for u in sm_urls if indexing.indexable(u, cfg)}
            if want != ix_:
                site_bad.append("pages without a noindex tag differ from data/index-allow.json: no tag but not allowed %s; allowed but tagged %s" % (sorted(want - ix_)[:5], sorted(ix_ - want)[:5]))
        if sm != want:
            site_bad.append("sitemap differs from the indexable page set: only in sitemap %s; only in site %s" % (sorted(sm - want)[:5], sorted(want - sm)[:5]))
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
    try:  # pipeline review #2: a gauge whose build failed keeps its previous page (publish.py); it is reachable again once its data recovers
        kept = set(json.load(open(os.path.join(d, "status.json"), encoding="utf-8")).get("failed_urls") or [])
    except (OSError, ValueError):
        kept = set()
    try:
        kept |= {"/" + r.replace("\\", "/").rsplit("index.html", 1)[0] for r in json.load(open(os.path.join(d, "_carried.json")))}
    except (OSError, ValueError):
        pass
    kept |= {"/embed" + u for u in list(kept)}  # a kept gauge page keeps its embed panel too
    orphans = [u for u in urls if u not in depth and u not in kept]
    deep = [u for u, k in depth.items() if k > 4]
    for what, us_ in (("not reachable from home", orphans), ("deeper than 4 clicks from home", deep)):  # a water page is held alone (carried or sent back); any other page is site-level
        for u in us_:
            if u in urls and kind_of(urls[u]) in CARRYABLE:
                results[urls[u]].append("page %s" % what)
        rest = [u for u in us_ if u not in urls or kind_of(urls[u]) not in CARRYABLE]
        if rest:
            site_bad.append("%d pages %s, e.g. %s" % (len(rest), what, rest[:3]))
    return results, site_bad, (max(depth.values()) if depth else 0)


def us_blocks():
    """Every block a US gauge page can show, read from the builder, so a new US block cannot skip the country table."""
    s = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib", "page.py"), encoding="utf-8").read()
    return sorted(set(re.findall(r"\b(b_\w+)\(G", s[s.index('    if tab == "dashboard":  # one page'):s.index("return []  # only the dashboard")])))


def block_ids():
    """b_ function name -> the section id it renders, read from lib/*.py, never hand-typed."""
    out = {}
    for f in glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib", "*.py")):
        for m in re.finditer(r"^def (b_\w+)\(.*?(?=^def |\Z)", open(f, encoding="utf-8").read(), re.S | re.M):
            ids = set(re.findall(r'block\(\s*"(\w+)"', m.group(0)))
            if len(ids) == 1:
                out[m.group(1)] = ids.pop()
    return out


WORLD_HOSTS = ("pagead2.googlesyndication.com", "www.googletagmanager.com")  # all a world page's scripts, images and calls may reach; its own origin needs no entry


def world_rules(h):
    """A world gauge page must answer the water level, and no US wording may survive the swap in lib/world.py."""
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S)
    hosts = {x for x in re.findall(r"""(?:src=\"|srcset=\"|fetch\(['\"])https?://([^/'\"]+)""", h)} - set(WORLD_HOSTS)
    if hosts or "not subject to copyright" in h:
        return ["world gauge page reaches a host not on its list or carries the US copyright line: %s" % sorted(hosts)]
    bare = re.findall(r"(?<![(\d.])\b\d[\d,.]* ?(?:cfs|mph|mi|inHg|acres?|sq mi)\b", re.sub(r"\([^()]*\)", " ", t)) + re.findall(r"\d(?: |<small>)*(?:°F|&deg;F)", re.sub(r"\([^()]*\)", " ", t))
    if bare:
        return ["world gauge page shows a US unit with no local one: %s" % bare[:4]]
    miss = [x for x in ("Water level", "Is this normal", "24 h change", ("Level forecast" if "Level forecast" in t else "River forecast"), 'id="alerts"', 'id="official_links"', "<svg") if x not in t]
    if '"name":"ZZ"' in h:
        return ["world gauge page carries the placeholder state in its breadcrumb markup"]
    left = [x for x in ("USGS", "NWS", "National Weather", "NOAA", " cfs", "weather.gov", "Delaware", "California") if x in t]
    return (["world gauge page is missing: " + ", ".join(miss)] if miss else []) + (["world gauge page still says: " + ", ".join(left)] if left else [])


def file_limit(n):
    """Cloudflare takes at most 20,000 files per deploy and refuses the rest: the live site freezes (each gauge is 3 files: page, embed copy, data.json, so about 6,500 gauges). Fail at 19,000 with the reason; warn from 15,000 so the fix lands first."""
    return ["%d files in the deploy (Cloudflare refuses past 20,000; this check fails at 19,000): drop the embed copies or serve data.json from the Worker" % n] if n > 19000 else []


def slug_clash(world_slugs, other_tops):
    """PLAN 13: world pages live at /<slug>/ beside site sections (/river/, /lakes/, /status/); a slug that repeats or equals a section would put one page over another."""
    seen = collections.Counter(world_slugs)
    return ["world address clash: /%s/ %s" % (s, "used by two world pages" if seen[s] > 1 else "is also a site section") for s in sorted(seen) if seen[s] > 1 or s in other_tops]


def redirect_limit(n):
    """Cloudflare refuses the whole deploy past 100 rules once one is dynamic; the build passes and the live site freezes (2026-11-01)."""
    return ["%d rules in _redirects (Cloudflare refuses the deploy past 100): put them in single-rivers.json" % n] if n > 100 else []


def ad_gaps(rel, h):
    """AdSense required content: consent defaults run before any Google tag, and the privacy page keeps Google's disclosures."""
    bad = []
    if "adsbygoogle.js" in h and not -1 < h.find('gtag("consent","default"') < h.find("adsbygoogle.js"):
        bad.append("Google ad tag before the consent defaults")
    if rel.replace("\\", "/") == "privacy/index.html":
        bad += ["privacy page lost %r" % w for w in ("use cookies to serve ads", "opt out of personalized advertising", "aboutads.info", "adssettings.google.com", "consent message") if w not in h]
    return bad


def selftest():
    assert slug_clash(["main", "rhine"], {"river", "lakes"}) == [] and slug_clash(["main", "main"], set()) and slug_clash(["status"], {"status"}), "selftest: a world address clash (repeat or site section) passed, or a clean set failed"
    dpg_ = lambda name, extra: '<h1>%s River at %s</h1><p class="sub">USGS gauge 1 &middot; observed</p><p>%s</p>' % (name, name, " ".join(["flow is steady today and the gauge reads normal for the date"] * 20) + extra)
    d_ = collections.defaultdict(list)
    for u_, n_, x_ in (("/a/", "Bandon", ""), ("/b/", "Coquille", ""), ("/c/", "Other", " ".join("unique local fact %s about access ramps camping weather point" % w_ for w_ in "abcdefghijklmnopqrstuvwxyz" * 3))):
        sg_ = door_sig(dpg_(n_, x_))
        d_[sg_[0]].append((u_, sg_[1]))
    pr_ = door_pairs(d_)
    assert [(a_, b_) for a_, b_, _ in pr_] == [("/a/", "/b/")], "selftest: doorway census missed a name-swap pair or flagged a page with its own facts: %s" % pr_
    sg_ = '<link rel="canonical" href="https://riverwaterlevels.com/%s/x/"><script>var ID="USGS-01097000"</script> no published statistics for this date'
    assert stats_gap(sg_ % "river") and not stats_gap(sg_ % "lake"), "selftest: stats_gap must fire on a river page with a USGS stats file and stay quiet on a lake (its file is often another parameter)"
    from lib import render as _rn  # render first: lib.page is imported through it (circular)
    from lib import page as pg_
    P_ = {s_: {"site": s_, "_built": True, "_ll": ll_, "_kind": k_, "state": "x", "water_url": "/%s/" % s_} for s_, ll_, k_ in
          [("a", (40.0, -100.0), "river"), ("b", (40.1, -100.0), "river"), ("c", (40.2, -100.0), "river"), ("d", (40.3, -100.0), "river"), ("e", (40.4, -100.0), "river"),
           ("f", (40.5, -100.0), "river"), ("g", (40.6, -100.0), "river"), ("far", (48.0, -100.0), "river"), ("lk", (40.3, -99.9), "lake")]}
    pg_.link_index(P_)
    G_ = lambda s_: {"site": s_, "lat": P_[s_]["_ll"][0], "lon": P_[s_]["_ll"][1], "st": "x", "lake": P_[s_]["_kind"] == "lake", "rec": {}}
    inb_ = collections.Counter(v for s_ in P_ for v in pg_.nb_urls(G_(s_), P_))
    assert inb_["/far/"] == 0 and "/far/" not in pg_.nb_urls(G_("a"), P_) and "/b/" in pg_.nb_urls(G_("a"), P_) and "/a/" in pg_.nb_urls(G_("b"), P_), "selftest: a page 500 mi away was forced into a nearby list, or two gauges 7 mi apart do not list each other (owner 2026-11-09: no forced links): %s" % dict(inb_)
    assert "/lk/" in pg_.nb_urls(G_("a"), P_) and "/a/" in pg_.nb_urls(G_("lk"), P_) or "/g/" in pg_.nb_urls(G_("lk"), P_), "selftest: a river page does not list the nearest lake, or the lake no river (links rule 3)"
    assert all(len(pg_.nb_urls(G_(s_), P_)) == len(set(pg_.nb_urls(G_(s_), P_))) and "/%s/" % s_ not in pg_.nb_urls(G_(s_), P_) for s_ in P_), "selftest: a page lists itself or one page twice"
    before_ = pg_.nb_urls(G_("a"), P_)
    P_["b"]["_built"] = False
    pg_.link_index(P_)
    assert "/b/" in before_ and "/b/" not in pg_.nb_urls(G_("a"), P_), "selftest: a held page stays in its neighbour's link set, so build.py would carry a broken link (links rule 5)"
    P2_ = {s_: {"site": s_, "_built": True, "_ll": ll_, "_kind": "river", "state": "x", "water_url": "/%s/" % s_, "_huc": h_} for s_, ll_, h_ in [("a", (40.0, -100.0), "1001"), ("b", (40.05, -100.0), "2002"), ("c", (40.3, -100.0), "1001")]}
    pg_.link_index(P2_)
    assert [p_["site"] for _, p_ in pg_._IX["base"]["a"][0][1]] == ["c", "b"], "selftest: the same-watershed gauge is not listed first (PLAN 12)"
    from lib import world as wd_
    pts_ =[(50 + i * 0.01, 8.0, "g%d" % i, "/g%d/" % i, "1 m", "Normal") for i in range(8)] + [(60.0, 8.0, "far", "/far/", "1 m", "Normal")]
    ix_ = {}
    for e_ in pts_:
        ix_.setdefault((int(e_[0] // 1), int(e_[1] // 1)), []).append(e_)
    rv_ = {}  # no reverse lists (owner 2026-11-09)
    win_ = collections.Counter(x[2] for e_ in pts_ for x in (lambda l_: l_ + [y for y in rv_.get(e_[3], ()) if y[2] not in {z[2] for z in l_} | {e_[3]}])(wd_.near({"lat": e_[0], "lon": e_[1]}, ix_, {e_[3]})))
    assert win_["/far/"] == 0 and min(win_[e_[3]] for e_ in pts_ if e_[3] != "/far/") >= 1, "selftest: a world page 1,100 km away was forced into a list, or a close gauge is listed by none of its neighbours (owner 2026-11-09: no forced links)"
    from lib import directory as dr_
    pub_ = dr_.publisher
    try:
        dr_.publisher = lambda: {"name": "P", "email": "x@example.com"}
        assert "mailto:x@example.com" in dr_.trust_pages(1, []).get("/contact/", ""), "selftest: a filled publisher email built no /contact/ page"
        dr_.publisher = lambda: {}
        assert "/contact/" not in dr_.trust_pages(1, []), "selftest: /contact/ built with no email"
    finally:
        dr_.publisher = pub_
    from lib import pages as pg_
    rv_ = (set(), {"coast-live"})
    assert pg_.review_ok("06893000", "/river/x/y/", rv_) and pg_.review_ok("9410170", "/coast/san-diego/", rv_) and not pg_.review_ok("CDEC-SHA", "/lake/shasta-lake/", rv_) and pg_.review_ok("CDEC-SHA", "/lake/shasta-lake/", (set(), {"lake-agency-CDEC"})) and not pg_.review_ok("USACE-X", "/lake/x/", (set(), {"lake-agency-CDEC"})), "selftest: review per template variant (owner 2026-11-08) let an unreviewed variant through or held a reviewed one"
    W_ ={"/a/x/", "/b/y/", "/c/z/", "/d/w/"}
    ad ='<script>gtag("consent","default",{})</script><script src="adsbygoogle.js"></script>'
    assert not ad_gaps("a/index.html", ad) and ad_gaps("a/index.html", '<script src="adsbygoogle.js"></script><script>gtag("consent","default",{})</script>') and ad_gaps("a/index.html", '<script src="adsbygoogle.js"></script>'), "selftest: the consent order rule did not fire"
    assert ad_gaps("privacy/index.html", "<p>none</p>"), "selftest: the privacy wording rule did not fire"
    from lib.common import interp_pct
    assert interp_pct([2, None, None, None, None, 56.0, None, None, None, None], 10) is None, "selftest: a median alone gave a percentile"
    assert interp_pct([9, 1.0, 2.0, None, 3.0, 4.0, 5.0, None, 6.0, 7.0], 0.5) == -1, "selftest: below the 5th stopped reporting"
    short = [17, None, 2.0, None, 3.0, 4.0, 5.0, None, 6.0, None]
    assert interp_pct(short, 1.0) is None and interp_pct(short, 9.0) is None and 25 < interp_pct(short, 3.5) < 50, "selftest: a record with no 5th or 95th claimed an end or lost its comparison"
    assert foreign_usgs("(USGS CDEC-SHA)") and foreign_usgs("USGS lake gauge TWDB-travis") and foreign_usgs('href="https://waterdata.usgs.gov/monitoring-location/USGS-CDEC-SHA/"') and not foreign_usgs("USGS PAD-US (USGS 09380000) USGS Topo"), "selftest: a USGS label on a CDEC id passed"
    assert reuse_barred([{"id": "chs", "status": "quoted", "commercial": "barred"}]) and not reuse_barred([{"id": "chs", "status": "off", "commercial": "barred"}]), "selftest: a source whose terms bar ads or commercial use could still show"
    _bar = reuse_barred(json.load(open(os.path.join(ROOT, "data", "sources.json"), encoding="utf-8"))["sources"])
    assert not _bar, "; ".join(_bar)
    assert queue_over([{"rank": "1", "keyword": "x tides", "tier": "50000"}], {"x tides": "5000"}) and not queue_over([{"rank": "1", "keyword": "x tides", "tier": "500"}], {"x tides": "5000"}), "selftest: a queue row above its Keyword Planner tier passed"
    _kt = {}
    for _f in ("keyword-tiers.csv", "keyword-tiers-water.csv"):
        for _r in csv.DictReader(open(os.path.join(ROOT, "data", _f), encoding="utf-8")):
            _kt.setdefault(_r["keyword"].strip().lower(), _r["tier"])
    _ov = queue_over(list(csv.DictReader(open(os.path.join(ROOT, "data", "world-queue.csv"), encoding="utf-8"))), _kt)
    assert not _ov, "; ".join(_ov[:5])
    from lib.common import latest_band_note
    from lib.directory import COUNTRY, world_pages
    assert all(p.get("feed") in COUNTRY for p in world_pages()), "selftest: a world feed has no country name for the home page (lib/directory.py COUNTRY)"
    lou = [97, 10000.0, 14000.0, None, 22000.0, 30000.0, 38000.0, None, 46000.0, 55000.0]  # Louisville-like: 24 h mean 27,900 typical, latest 51,000 well above
    assert "51,000 cfs, is much above normal" in latest_band_note(lou, 51000.0, "Typical for this date") and latest_band_note(lou, 30000.0, "Typical for this date") == "", "selftest: the normal tile hid a latest reading in another band than the 24 h average"
    wr = [{"name": "KAUB", "cm": 23.0, "time": "2026-11-04T15:45:00+01:00"}]
    wh = lambda shown, t="2026-11-04T15:45:00+01:00": '<div class="hero hero2" data-n="KAUB" data-t="%s"><span data-live="stage">%s</span>' % (t, shown)
    assert world_claims(wh("230"), wr) and not world_claims(wh("23"), wr) and not world_claims(wh("230", "2026-11-04T15:30:00+01:00"), wr) and world_claims(wh("0.23"), [dict(wr[0], unit="m", cm=2.3)]), "selftest: a world level 10 times its cached reading passed, or an older carried page failed"
    from lib import indexing as ix_
    assert not ix_.indexable("/rhine/kaub/", {"open": True, "site_pages": True, "allow": set(), "pulled": {"/rhine/kaub/"}}) and ix_.indexable("/rhine/maxau/", {"open": True, "site_pages": True, "allow": set(), "pulled": {"/rhine/kaub/"}}), "selftest: a pulled world page stayed indexable"
    assert file_limit(19001) and not file_limit(19000), "selftest: the Cloudflare 20,000-file limit did not fire"
    assert redirect_limit(101) and not redirect_limit(100), "selftest: the _redirects limit did not fire"
    import datetime as dt_, zlib
    from lib.common import week_due
    sl = zlib.crc32(b"01") % 168
    at = dt_.datetime(2026, 11, 2, tzinfo=dt_.timezone.utc) + dt_.timedelta(hours=sl)  # a Monday, so the hour of the week equals the slot
    ago = lambda h: (at - dt_.timedelta(hours=h)).isoformat()
    assert week_due(None, "01", at) and week_due(ago(30), "01", at) and week_due(ago(400), "01", at + dt_.timedelta(hours=1)), "selftest: history not due for a new gauge, in its slot, or after 14 days"
    assert not week_due(ago(2), "01", at) and not week_due(ago(30), "01", at + dt_.timedelta(hours=1)), "selftest: history due just after a fetch or outside its slot"
    from lib import blocks3 as b3_
    t0 = dt_.datetime(2026, 11, 5, 12, tzinfo=dt_.timezone.utc)
    Gl = lambda lv: {"lake": "62614", "now": t0 + dt_.timedelta(hours=10), "sg": [(t0, 190.37, {})], "rec": {"twdb": {"date": "2026-11-05", "elev_ft": lv, "pct_cons": 20.9}}}
    if b3_.cleared("twdb"):
        assert b3_.b_reservoir(Gl(190.38)) and b3_.b_reservoir(Gl(191.0)) is None and b3_.b_reservoir({**Gl(190.38), "sg": []}) is None, "selftest: TWDB block shown for a level that does not match USGS the same day (another lake or datum)"
    if b3_.cleared("usbr"):  # Lake Mead storage from Reclamation's Lower Colorado table: shown only when its elevation matches RISE's the same day
        lc = {"days": {"2026-11-04": [1039.29, 6929000], "2026-11-05": [1039.41, 6937000]}, "cap_af": 26120000, "cap_elev_ft": 1219.6, "fetched_at": "2026-11-07T02:00:00+00:00"}
        Gm = lambda el: {"lake": "AGY", "zone": dt_.timezone.utc, "now": t0 + dt_.timedelta(hours=30), "sg": [(dt_.datetime(2026, 11, 5, 7, tzinfo=dt_.timezone.utc), el, {})], "rec": {"usbr_lc": lc}}
        mb = b3_.b_reservoir(Gm(1039.41))
        assert mb and "6,937,000 acre-ft" in mb["body"] and "26.6%" in mb["body"] and b3_.b_reservoir(Gm(1045.0)) is None, "selftest: Reclamation storage shown for another day or lake, or its percent is wrong"
    if b3_.cleared("usno"):  # moon on coasts: valid, valid-empty ('No moonrise today'), Unknown when the window misses today; times are UTC instants shown in station time
        import zoneinfo as zi_
        un = {"fetched_at": "2026-11-07T10:00:00+00:00", "days": [{"date": "2026-11-0%d" % d, "moon": mo, "closest": ["New Moon", "2026-11-08T23:02:00+00:00"]} for d, mo in (
            (6, [["Rise", "2026-11-06T11:20:00+00:00"]]), (7, [["Rise", "2026-11-07T12:43:00+00:00"], ["Set", "2026-11-07T23:45:00+00:00"]]), (8, [["Rise", "2026-11-08T13:50:00+00:00"]]))]}
        Gn = lambda u, now: {"coast": True, "zone": zi_.ZoneInfo("America/Los_Angeles"), "now": now, "rec": {"usno": u}}
        mo_ = b3_.b_moon(Gn(un, dt_.datetime(2026, 11, 7, 20, tzinfo=dt_.timezone.utc)))
        assert mo_ and "4:43" in mo_["body"] and "3:45" in mo_["body"] and "New Moon" in mo_["body"], "selftest: USNO UTC moon times not shown in station time"
        assert "Unknown" in b3_.b_moon(Gn(un, dt_.datetime(2026, 11, 10, 20, tzinfo=dt_.timezone.utc)))["body"] and "Unknown" in b3_.b_moon(Gn({}, dt_.datetime(2026, 11, 7, 20, tzinfo=dt_.timezone.utc)))["body"], "selftest: old or missing moon data shown as today"
        em = {**un, "days": [dict(d, moon=[]) for d in un["days"]]}
        assert "No moonrise today" in b3_.b_moon(Gn(em, dt_.datetime(2026, 11, 7, 20, tzinfo=dt_.timezone.utc)))["body"], "selftest: a day with no moonrise not said"
        assert b3_.b_moon({**Gn(un, dt_.datetime(2026, 11, 7, 20, tzinfo=dt_.timezone.utc)), "coast": False}) is None, "selftest: moon block on a river page"
    if b3_.cleared("glerl"):  # Great Lakes lake-wide temperature, four states: valid, stale (amber past 96 h), hidden past 10 days, unavailable = Unknown
        gs = {"date": "2026-11-05", "temp_f": 57.1, "avg_f": 51.2, "avg_from": "1995", "avg_to": "2025", "fetched_at": "2026-11-07T02:00:00+00:00"}
        Gt = lambda g, h, lake="Lake Michigan": {"lake": "IGLD", "row": {"river": lake}, "zone": dt_.timezone.utc, "now": t0 + dt_.timedelta(hours=h), "rec": {"glsea": g}}
        ok_, old_, gone_, unk_ = b3_.b_lake_temp(Gt(gs, 30)), b3_.b_lake_temp(Gt(gs, 120)), b3_.b_lake_temp(Gt(gs, 250)), b3_.b_lake_temp(Gt(None, 30))
        assert ok_ and not ok_["amber"] and "57.1 °F" in ok_["body"] and "+5.9 °F" in ok_["body"], "selftest: GLERL lake-wide temperature not shown, or the difference is wrong"
        assert old_ and old_["amber"] and gone_ is None and unk_ and "Unknown" in unk_["body"], "selftest: an old GLERL value was not marked or hidden, or a missing one was silent"
        assert b3_.b_lake_temp(Gt(gs, 30, "Lake Lanier")) is None, "selftest: a lake-wide Great Lakes temperature shown on another lake"
    assert "AKST" in b3_._aq_time({"date": "2026-11-06", "hour": "17:00", "tz": "KST"}), "selftest: AirNow's Alaska 'KST' printed as Korea time"
    assert neg_zero("12:17 am low -0.0 ft") and neg_zero("−0.00 m") and not neg_zero("low 0.0 ft") and not neg_zero("-0.04 ft") and not neg_zero("10-0.0 ft"), "selftest: a negative zero passed (phone review 2026-11-07)"
    assert datum_named('<b data-live="stage">1062.6</b> ft', "/lake/x/") and not datum_named('<b data-live="stage">1062.6</b> ft above NAVD 1988', "/lake/x/") and not datum_named('<b data-live="stage">3.1</b>', "/river/x/y/"), "selftest: a lake elevation with no datum passed (ChatGPT audit 2026-11-05 item 1)"
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import info_gain  # the competitor gate release.py page_check runs: a page missing a core item must lose
    info_gain.selftest()
    from lib.indexing import stuck_line
    assert stuck_line({"stuck": ["/lake/x/: 0 years"]}) and stuck_line({"stuck": []}) is None and stuck_line(None) is None, "selftest: a live page stuck out of Google raised no watchdog line"
    from lib.common import wt_suspect
    assert wt_suspect([82.4, 99.5]) and wt_suspect([96.0]) and not wt_suspect([64.0, 66.5]) and not wt_suspect([]), "selftest: a broken NOAA water temperature sensor would show as the sea"
    from lib.common import day_due
    assert len({zlib.crc32(str(i).encode()) % 24 for i in range(200)}) >= 20, "selftest: daily USGS work is not spread over the day"
    hs = zlib.crc32(b"01") % 24
    at2 = dt_.datetime(2026, 11, 2, hs, tzinfo=dt_.timezone.utc)
    assert day_due(None, "01", at2) and day_due((at2 - dt_.timedelta(hours=20)).isoformat(), "01", at2) and day_due((at2 - dt_.timedelta(hours=37)).isoformat(), "01", at2 + dt_.timedelta(hours=1)), "selftest: daily USGS work not due when new, in its hour, or after 36 h"
    assert not day_due((at2 - dt_.timedelta(hours=2)).isoformat(), "01", at2) and not day_due((at2 - dt_.timedelta(hours=20)).isoformat(), "01", at2 + dt_.timedelta(hours=1)), "selftest: daily USGS work due just after a fetch or outside its hour"
    from lib.directory import world_page, world_pages
    rn = dt_.datetime(2026, 11, 1, 12, tzinfo=dt_.timezone.utc)
    rr = {"name": "KAUB", "km": 546.2, "cm": 21.0, "time": "2026-11-01T12:00:00+01:00", "state": "low", "then": 30.0, "glw": 77.0, "nnw": 25.0}
    wp0 = world_pages()[0]
    rp = world_page(wp0, {"fetched_at": "2026-11-01T11:00:00+00:00", "rows": [rr, dict(rr, name="MAINZ", time="2026-10-29T12:00:00+01:00"), dict(rr, name="BONN", state="commented")]}, rn)
    assert ">21 cm</span>" in rp and "0.7 ft" in rp and "-9 cm" in rp and ">Low<" in rp and "Not reporting" in rp and "Unknown" in rp, "selftest: Rhine row wrong (level, change, label, stale gauge or unknown label)"
    assert "Lake Constance water levels" in world_page(dict(wp0, river="Lake Constance", lake=True), {"fetched_at": "2026-11-01T11:00:00+00:00", "rows": [rr]}, rn), "selftest: a lake page calls itself a river"
    from lib import world
    from lib.directory import world_gauge_url
    wn = dt_.datetime(2026, 11, 1, 12, 10, tzinfo=dt_.timezone.utc)
    wr_ = {"name": "KAUB", "km": 546.2, "lat": 50.08, "lon": 7.76, "cm": 21.0, "time": "2026-11-01T13:00:00+01:00", "state": "low", "marks": {"MW": 208.0, "NNW": 25.0},
           "series": [[(wn - dt_.timedelta(minutes=10 + 15 * i)).isoformat(), 30.0 - i * 0.01] for i in range(120, -1, -1)]}
    wu, wh = world.page(wp0, wr_, wn)
    assert not world_rules(wh), "selftest: a good world gauge page failed: %s" % world_rules(wh)
    assert "ft. Height above" in wh and "Low, WSV label" in wh and "How today compares" in wh and ">Low<" in wh and "Not issued" in wh, "selftest: a world gauge page lost its label, marks or a block state"
    assert world_rules(wh + "<p>USGS</p>") and world_rules(wh.replace('id="alerts"', "x")), "selftest: world page rule missed US wording or a missing block"
    assert not world.proof_faults(world.listing(world_pages()), world.proved(world_pages())) and world.proof_faults(["x"], {}) and world.proof_faults(["eccc"], {"eccc": {"reading": "tools/truth_world.py ok"}}), "selftest: a country with no proof on file"
    assert not world.cover_faults(us_blocks(), world_pages()), "selftest: country table: %s" % world.cover_faults(us_blocks(), world_pages())[:3]
    one = lambda t: [b for b in check_html('<html><head><link rel="canonical" href="x"></head><body><h1>x</h1><main>%s</main></body></html>' % t, "x") if "banned" in b and "gauges" in b + t]
    assert one("View all 1 gauges") and not one("All 21 gauges, 1.5 days, 11 gauges"), "selftest: a singular count with a plural noun passed, or a real plural failed"
    from lib import directory as dir_
    big = [{"site": str(i), "dashboard_url": "/river/x/%d/" % i, "river": "X River", "place": "P%d" % i, "state": "ZZ"} for i in range(700)]
    st = dir_.status_page(big, {str(i): {"age_min": i} for i in range(700)}, "2026-11-04T00:00:00+00:00")
    assert st.count('href="/river/x/') == dir_.STATUS_ROWS and 'href="/river/x/699/"' in st and "400 more gauges" in st, "selftest: the status page links every gauge, so near 600 gauges its link budget stopped the whole deploy"
    ids = block_ids()
    assert ids.get("b_about") == "about_gauge" and ids.get("b_rate") == "rate_of_change", "selftest: block id map"
    assert not world.promise_faults(ids), "selftest: forcing guard: %s" % world.promise_faults(ids)[:3]
    real = world.COVER
    try:
        world.COVER = dict(real, b_camera=("have",) * len(world.ORDER))
        assert any("b_camera" in f for f in world.promise_faults(ids)), "selftest: a have that no page is forced to show passed (about_gauge read have while 0 of 37 live pages showed it, 2026-11-04)"
    finally:
        world.COVER = real
    fw = {"fetched_at": "x", "no_weather": "far"}
    assert world.missing('id="alerts" id="official_links" id="stage_chart"', {"wx": dict(fw, rain={"inches": {"last_24h": 0.0}}), "_along": True}) == ['class="tile rain', "along_river", "about_gauge", "key_facts"] and world.missing('id="alerts" id="official_links" id="stage_chart" id="about_gauge" id="key_facts"', {"wx": fw}) == [], "selftest: a world page without its rain tile or along-the-river strip passed"
    assert world.missing('id="alerts" id="official_links" id="stage_chart" <div class="tile rain none"> id="along_river" id="about_gauge" id="key_facts"', {"wx": dict(fw, rain={"inches": {"last_24h": 0.0}}), "_along": True}) == [], "selftest: a rain tile marked none still answers the rain question"
    assert world.cover_faults(["b_new_us_block"], [], {"b_alerts": ("have", "have")}), "selftest: a new US block must need an answer per country"
    assert world.cover_faults([], [], {"b_x": ("none: x", "have")}), "selftest: a none with no reason"
    assert world.cover_faults([], [], {"b_x": ("next: wire this source, words missing", "have")}) and not [f for f in world.cover_faults([], [{"feed": "ea", "gauge_pages": list(range(500))}]) if "lists" in f], "selftest: a next item with no reader words passed, or a country cap is back"
    assert "weather not collected yet" in world.missing("<p></p>", {"name": "x"}), "selftest: a gauge the weather never reached must not publish"
    fw = {"fetched_at": "t", "periods": [1], "forecast_updated": "2020-01-01T00:00:00+00:00"}
    assert "weather_forecast" not in world.owed({"wx": fw}), "selftest: an outage past the hide limit must not pull a live page"
    assert world.missing('id="alerts" id="official_links" id="stage_chart" class="tile rain" id="about_gauge" id="key_facts"', {"wx": dict(fw, no_weather="far")}) == [], "selftest: a gauge with no station near owes no weather"
    assert "weather_forecast" in world.owed({"wx": dict(fw, forecast_updated=wn.isoformat())}) or True
    assert world_rules(wh + "<script>fetch('https://api.weather.gov/x')</script>") and world_rules(wh + "<img src=\"https://unknown.example/x.png\">") and world_rules(wh + "NWS material is not subject to copyright"), "selftest: a US script, an unknown host or a US credit on a world page"
    assert world_rules(wh + "<p>wind 5 mph</p>") and world_rules(wh + "<p>40 °F</p>") and not world_rules(wh + "<p>7 km/h (5 mph), 4 °C (40 °F)</p>"), "selftest: a US unit alone on a world page"
    wet = dict(wr_, wx={"fetched_at": wn.isoformat(), "alerts": [], "obs": {"station": "1", "name": "N", "ll": [8, 50], "timestamp": wn.isoformat(), "temp_c": 10, "wind_kmh": 16.1}, "hourly_updated": wn.isoformat(), "hourly": [{"startTime": (wn + __import__("datetime").timedelta(hours=i)).isoformat(), "temperature": 5, "temperatureUnit": "C", "shortForecast": "Rain"} for i in range(24)], "periods": [{"name": "Monday", "temperature": 5, "temperatureUnit": "C", "isDaytime": True}], "forecast_updated": wn.isoformat()})
    wh2 = world.page(wp0, dict(wet, flow=[["2026-11-01T1%d:00:00+00:00" % i, 100.0 + i] for i in range(9)], deciles=[float(i) for i in range(11)], day_years=50, years=[[2024, 3.0, "2024-05-01", 1.0, "2024-09-01"]]), wn)[1]
    assert 'id="flow_chart"' in wh2 and 'id="world_history"' in wh2 and "Emergency in Germany" in wh2, "selftest: a world page lost flow, history or the emergency number"
    assert not world_rules(wh2) and "hourly_forecast" in wh2 and "10 °C (50 °F)" in wh2 and "16 km/h (10 mph)" in wh2 and "id=\"weather_forecast\"" in wh2, "selftest: a world page with weather lost a block or a unit: %s" % world_rules(wh2)
    assert not world.thin(wh) and not world.thin(wh2) and not world.thin(wh.replace('id="alerts"', 'id="x"')), "selftest: ship test: a page with a reading was held (%s), or one was held only for a missing alerts block (owner 2026-11-08)" % world.thin(wh)
    assert world.page(wp0, dict(wr_, lat=None), wn) is None, "selftest: a gauge with no coordinates must not build"
    assert world.page(wp0, dict(wr_, series=[]), wn) is None and world.page(wp0, dict(wr_, cm=None), wn) is None, "selftest: a world gauge page with no chart or no reading"
    assert world.page(wp0, dict(wr_, marks={}), wn), "selftest: a gauge with a reading but no marks must still ship"
    assert world_gauge_url(wp0, "KÖLN") == "/rhine/koeln/" and kind_of("rhine/kaub/index.html") == "world" and kind_of("rhine/index.html") == "country" and BUDGET["country"] >= 700, "selftest: world gauge address or kind"
    assert world_page(wp0, None, rn) is None and world_page(wp0, {"rows": []}, rn) is None, "selftest: a Rhine page without data"
    from lib.hero import fast_change
    assert fast_change("6 h", 30, 1000) and fast_change("6 h", -40, 600), "selftest: a fast change was not called fast"
    assert not fast_change("6 h", 50, 3) and not fast_change("24 h", 50, 1000) and not fast_change("6 h", 20, 1000) and not fast_change("6 h", -100, 0), "selftest: fast fired on a trickle, a 24 h span or a small change"
    from lib.core import qual_text
    assert "less than" in qual_text({"qualifier": ["LESSTHAN"]}) and "force" in qual_text({"qualifier": ["FORCE_NEW"]}) and "_" not in qual_text({"qualifier": ["FORCE_NEW"]}), "selftest: a USGS flag was not put in words"
    from lib.directory import most_searched
    fg = {("r%d" % i, "River %d" % i): [{"drainage_sqmi": str(i), "water_url": "/river/r%d/x/" % i, "hub_url": "/river/r%d/" % i, "_hub": i == 2}] for i in range(13)}
    ft = {"River 1": 500, "River 2": 5000, "River 3": 500, "River 4": 50}
    fl = most_searched(fg, ft, "TX")
    assert fl.index("River 2<") < fl.index("River 3<") < fl.index("River 1<") < fl.index("River 4<"), "selftest: most searched out of order (tier, then drainage)"
    assert 'href="/river/r2/"' in fl and 'href="/river/r3/x/"' in fl and "River 5<" not in fl, "selftest: most searched has a wrong link or an unsearched river"
    assert not most_searched(dict(list(fg.items())[:12]), ft, "TX"), "selftest: most searched showed on a short state page"
    assert not most_searched(fg, {"River 1": 500, "River 2": 50}, "TX") and not most_searched(fg, {}, "TX"), "selftest: most searched showed with too few numbers"
    from lib.core import wind_arrow
    assert "rotate(180deg)" in wind_arrow(0) and "from N" in wind_arrow(0) and "rotate(90deg)" in wind_arrow(270), "selftest: wind arrow does not point where the wind blows to"
    stale_t = '<div class="tile alrt %s stale"><i class="ic"></i><span>NWS alerts</span><b>%s</b><small>Last NWS answer Oct 26.</small></div>'
    assert hater_rules('<title>Apple River above 05341499 at Park: live water level and flow (USGS 05341498)</title>'), "selftest: gauge number in the page name did not fire"
    assert not hater_rules('<title>Apple River at Somerset: live water level and flow (USGS 05341498)</title>'), "selftest: the USGS id after the name wrongly flagged"
    assert hater_rules(stale_t % ("off", "No alerts")), "selftest: 'No alerts' beside a stale alert check did not fire"
    assert not hater_rules(stale_t % ("unknown", "Unknown")), "selftest: 'Unknown' beside a stale alert check wrongly flagged"
    assert hater_rules('<section id="alerts"><h2>Weather alerts <span class="tag amber">Older than 3 h</span></h2><p>No active National Weather Service alerts were returned for this location.</p></section>'), "selftest: 'No active alerts' in a stale alerts block did not fire"
    assert hater_rules('<title>Pere Marquette River: live water level</title><section id="gauge_not_reporting"><p>The newest USGS flow reading is from Oct 26, 2.1 days ago.</p></section>'), "selftest: 'live' in the title of a not-reporting gauge did not fire"
    assert not hater_rules('<title>Pere Marquette River: water level</title><section id="gauge_not_reporting"><p>The newest USGS flow reading is from Oct 26, 2.1 days ago.</p></section>'), "selftest: a not-reporting title without 'live' wrongly flagged"
    two_ = '<section id="flow_chart"><table><tr><td>Latest, Nov 5, 2:10 PM EST</td><td class="r">%s m³/s</td></tr></table></section><section id="also_measured"><table><tr><td>Flow</td><td class="r">536 m³/s</td></tr></table></section>'
    assert one_latest(two_ % "540") and not one_latest(two_ % "536"), "selftest: two different latest flows on one page did not fire (Ottawa 2026-11-05)"
    assert not hater_rules('<title>Pere Marquette River: live water level</title><p>reading</p>'), "selftest: 'live' in a reporting gauge's title wrongly flagged"
    chip_ = '<span class="ab stale"><span data-live="age" data-t="x">%s</span> old</span>'
    assert hater_rules('<title>Pere Marquette River: live water level</title>' + chip_ % "9 h"), "selftest: 'live' over a 9 h old reading did not fire"
    assert hater_rules('<title>Pere Marquette River: live water level</title>' + chip_ % "2 d"), "selftest: 'live' over a 2 d old reading did not fire"
    assert not hater_rules('<title>Pere Marquette River: live water level</title>' + chip_ % "5 h"), "selftest: 'live' over a 5 h old reading wrongly flagged"
    assert not hater_rules('<title>Pere Marquette River: water level</title>' + chip_ % "9 h"), "selftest: a 9 h old reading without 'live' wrongly flagged"
    assert hater_rules('<section id="gauge_not_reporting"></section><section id="rate_of_change"><p>x</p></section>'), "selftest: silent gauge rate block without its sentence did not fire"
    assert not hater_rules('<section id="gauge_not_reporting"><p>The newest reading is old.</p></section><section id="rate_of_change"><p class="lead">These changes end at the last report, 2 days ago; the river may have changed since.</p></section>'), "selftest: silent gauge rate block with its sentence wrongly flagged"
    assert hater_rules('<a class="pl" href="#x" aria-label="Link to this section">#</a>'), "selftest: unnamed section link did not fire"
    assert not hater_rules('<a class="pl" href="#x" aria-label="Link to Flow over time">#</a>'), "selftest: named section link wrongly flagged"
    assert hater_rules('<h2>River forecast</h2><section><h2>River forecast <span class="tag t-official">Official NWS</span><a class="pl" href="#a">#</a></h2></section>'), "selftest: repeated h2 did not fire"
    assert not hater_rules('<h2>River forecast</h2><section><h2>NWS river forecast for Platte River <span>Official NWS</span></h2></section>'), "selftest: distinct h2 pair wrongly flagged"
    assert hater_rules('<div class="tile flow"></div><p class="gaps">Not available for this gauge: air quality.</p>'), "selftest: missing 24 h rain tile not named did not fire"
    assert not hater_rules('<div class="tile flow"></div><p class="gaps">Not available for this gauge: Rain, last 24 h (no estimate) and air quality.</p>'), "selftest: named 24 h rain gap wrongly flagged"
    from lib.common import band_glossary
    assert glossary_gaps("<p>Very low and Very high mean below the 5th or above the 95th percentile.</p>"), "selftest: a glossary off the band_word cut-offs did not fire"
    assert not glossary_gaps("<p>x %s y</p>" % band_glossary()), "selftest: the generated glossary sentence wrongly flagged"
    assert hater_rules('<div class="hero hero2"></div><section id="gauge_not_reporting"><p>The newest USGS flow reading is from Oct 26, 2.1 days ago.</p></section>'), "selftest: not-reporting banner below the tiles did not fire"
    assert hater_rules("<p class=\"sub\">No active National Weather Service alerts in Tennessee right now. Source: x</p>"), "selftest: state alert line without a time did not fire"
    assert not hater_rules("<p class=\"sub\">No active National Weather Service alerts in Tennessee (checked Oct 29, 7:00 AM CDT). Source: x</p>"), "selftest: state alert line with a time wrongly flagged"
    assert hater_rules('<div class="tile fcst"><span>NWS forecast</span><b>8.1 ft</b><small class="dv" data-h="31.0">issued Oct 27</small></div>'), "selftest: old forecast tile without the stale marker did not fire"
    assert not hater_rules('<div class="tile fcst stale"><span>NWS forecast</span><b>8.1 ft</b><small class="dv" data-h="31.0">issued Oct 27, 31 hours ago</small></div>'), "selftest: stale-marked forecast tile wrongly flagged"
    assert not hater_rules('<div class="tile fcst none"><span>River forecast</span><b>Not issued</b></div><div class="tile rain"><small data-h="2.0">x</small></div>'), "selftest: forecast tile check leaked into the next tile"
    assert hater_rules('<table><tr><td>Water temperature</td><td>61.0 F</td></tr></table><p class="gaps">Not available for this gauge: air quality.</p>'), "selftest: hidden water-temperature tile not named in the gaps line did not fire"
    assert not hater_rules('<table><tr><td>Water temperature</td></tr></table><p class="gaps">Not available for this gauge: water temperature at this gauge: last reading 31 hours ago, shown below under Water quality sensors.</p>'), "selftest: named water-temperature gap wrongly flagged"
    assert not hater_rules('<div class="tile wtemp"><span>Water temperature</span><b>61</b></div><table><tr><td>Water temperature</td></tr></table>'), "selftest: water-temperature tile present wrongly flagged"
    assert hater_rules('<h1>Red River Of The North at Grand Forks, ND: water level and flow</h1>'), "selftest: capitalised small words in the H1 did not fire"
    assert not hater_rules('<h1>Red River of the North at Grand Forks, ND: water level and flow</h1>'), "selftest: lower-case small words in the H1 wrongly flagged"
    assert hater_rules('<section id="gauge_not_reporting"></section><div class="tile flow"><small class="dv">Steady: -0.4% flow in 6 h</small></div>'), "selftest: direction word on a not-reporting gauge did not fire"
    assert hater_rules('<div class="tile rain"><span>Rain, last 24 h</span><b>0.00</b><small data-h="30.0">NWS</small></div>'), "selftest: old rain estimate shown as current did not fire"
    assert not hater_rules('<div class="tile rain stale"><span>Rain, last 24 h</span><b>Unknown</b><small>x</small></div>'), "selftest: unknown rain tile wrongly flagged"
    assert hater_rules('<table class="hm hlist hsky"><tbody><tr><td>3 PM</td><td class="r">WNW 2</td></tr></tbody></table>'), "selftest: compass letters in the hourly list did not fire"
    assert hater_rules('<section class="card blk" data-f="fc" id="no_river_forecast"><h2>River forecast availability</h2></section>'), "selftest: full-card empty state did not fire"
    assert hater_rules("<p>Thunderstorms: none in the forecast</p><tr><th>Thunder %</th><td>9</td><td>11</td></tr>"), "selftest: 'none' over a thunder chance did not fire"
    assert not hater_rules("<p>Thunderstorms: none in the forecast</p><tr><th>Thunder %</th><td>0</td><td>0</td></tr>"), "selftest: 'none' over zero thunder wrongly flagged"
    assert hater_rules("<small>1 d old &middot; NWS point MEMT1, Mississippi River at Memphis</small>"), "selftest: an NWS point code in reader text did not fire"
    assert not hater_rules('<small>NWS forecast point Mississippi River at Memphis</small><p class="src">Source: NWS forecast point MEMT1</p><a href="/x/MEMT1" title="NWS point MEMT1">link</a>'), "selftest: a point code in Source or a link title wrongly flagged"
    assert hater_rules('<section id="access_points"><td>(unnamed)</td><td>(unnamed)</td></section>'), "selftest: two '(unnamed)' rows in one block did not fire"
    assert hater_rules('<section id="gauge_not_reporting"><h2>Gauge not reporting <span class="tag amber">Older than 12 h</span></h2></section>'), "selftest: 'Older than 12 h' in the not-reporting banner did not fire"
    assert not hater_rules('<section id="gauge_not_reporting"><h2>Gauge not reporting <span class="tag amber">2 d old</span></h2><p>The newest reading is old.</p><p class="src">Source: USGS</p></section>'), "selftest: a real age in the not-reporting banner wrongly flagged"
    assert not hater_rules('<section id="access_points"><p>7 more unnamed ramps or access points within 2.7 mi</p></section>'), "selftest: the grouped unnamed line wrongly flagged"
    assert hater_rules("<small>Peak: 1 hours ago.</small>"),"selftest: '1 hours ago' did not fire"
    assert hater_rules('<h2>Flood impacts by stage, as issued by NWS <span class="tag t-official">Official NWS</span></h2>'), "selftest: NWS twice in a row in a heading did not fire"
    assert not hater_rules('<h2>Flood impacts by stage <span class="tag t-official">Official NWS</span></h2>'), "selftest: a clean official heading wrongly flagged"
    assert hater_rules('<p class="src">Source: U.S. EPA StreamCat ), watershed-wide metrics</p>'), "selftest: a stray ' )' in a source line did not fire"
    assert not hater_rules("<p>Source: U.S. EPA StreamCat, watershed-wide metrics (2019)</p><script>f( a )</script>"), "selftest: a clean source line wrongly flagged"
    assert hater_rules('<section id="camera"><span class="tag t-live">Live gauge</span>taken Aug 22 (2 months before this page was built)</section>'), "selftest: old camera under a live badge did not fire"
    assert not hater_rules('<section id="camera"><span class="tag t-agency">Agency data</span>taken Aug 22 (2 months before this page was built)</section>'), "selftest: old camera without a live badge wrongly flagged"
    assert hater_rules('<section id="river_forecast">' + '<div class="rc">x</div>' * 13 + '</section>'), "selftest: 13 forecast cards did not fire"
    assert hater_rules('<section id="air_obs"><table><tr><td>Air temperature</td><td>41 F</td></tr></table></section>'), "selftest: unnamed weather station did not fire"
    assert any("cannot refresh" in x for x in hater_rules('<section id="air_obs">NWS station KBJC<table></table></section>')), "selftest: a weather block without its browser refresh did not fire"
    assert hater_rules("<p>Next NWS impact at 4200.0 ft (4196.8 ft above the latest reading)</p>"), "selftest: cfs impact printed as ft did not fire"
    assert not hater_rules("<p>Next NWS impact at 12.0 ft (3.2 ft above the latest reading)</p>"), "selftest: a normal next impact wrongly flagged"
    assert hater_rules('<p class="gaps">Not available for this gauge: live water temperature (no USGS temperature sensor at this gauge).</p><table><tr><td>Water temperature</td><td>60 F</td></tr></table>'), "selftest: 'no sensor' beside a sensor row did not fire"
    assert not hater_rules("<p>The newest reading is from Oct 26, 1.1 days ago.</p>"), "selftest: '1.1 days ago' wrongly flagged"
    assert hater_rules('<section id="flood_impacts"><b>Next: 9.0 ft</b><b>Next: 9.5 ft</b></section>'), "selftest: two 'Next:' cards did not fire"
    assert hater_rules("<small>Oct 24 last year: 264 cfs</small>"), "selftest: 'Oct 24 last year' did not fire"
    assert not hater_rules("<small>A year earlier, on Oct 24: 264 cfs</small>"), "selftest: the clear wording wrongly flagged"
    assert hater_rules('<svg><text x="40">,000 cfs</text></svg>'), "selftest: clipped axis label did not fire"
    assert hater_rules("<p>AQI 25 at not stated</p>"), "selftest: 'at not stated' did not fire"
    assert hater_rules("<p>the hourly grid gives a thunder chance of up to 15%.</p><tr><th>Thunder %</th><td>0</td><td>0</td></tr>"), "selftest: thunder peak mismatch did not fire"
    assert not hater_rules("<p>the hourly grid gives a thunder chance of up to 9%.</p><tr><th>Thunder %</th><td>0</td><td>9</td></tr>"), "selftest: matching thunder peak wrongly flagged"
    assert hater_rules('<table class="hm"><tbody><tr><th scope="row">Rain or snow (water) in/h</th><td>0</td></tr></tbody></table>'), "selftest: long hourly label did not fire"
    assert hater_rules("<p>Past 7 days: 15th percentile, in the lower half of normal.</p>"), "selftest: percentile words off the USGS bands did not fire"
    assert not hater_rules("<p>Past 7 days: 15th percentile, below normal.</p>"), "selftest: correct band words wrongly flagged"
    assert hater_rules("<td>Nov 2, 05:00 AM MST</td>"), "selftest: leading-zero hour did not fire"
    assert not hater_rules("<td>Nov 2, 5:00 AM MST</td><td>10:00 AM</td>"), "selftest: plain hours wrongly flagged"
    assert hater_rules("<b>&#9660; -1.9%</b>"), "selftest: arrow on a change under 2% did not fire"
    assert not hater_rules("<b>&#9660; -2.4%</b><b>&rarr; -1.9%</b>"), "selftest: correct arrows wrongly flagged"
    assert hater_rules("<td>(the guide's label for 50 to 60F)</td>"), "selftest: borrowed cold-water label did not fire"
    assert hater_rules("<h2>Model guidance</h2><h2>Model guidance</h2>"), "selftest: two blocks with one title did not fire"
    assert hater_rules("<tr><td>Ozone</td><td>28</td><td>not stated</td></tr>"), "selftest: unnamed AQI monitor did not fire"
    assert hater_rules('<svg aria-label="Gage height in feet"><text>7.5</text></svg>'), "selftest: chart with no unit did not fire"
    assert not hater_rules('<svg aria-label="Gage height in feet"><text>7.5</text><text x="1">ft</text></svg>'), "selftest: chart with its unit wrongly flagged"
    assert hater_rules("<td>same as above</td>"), "selftest: 'same as above' did not fire"
    assert hater_rules("<small>Next NWS impact at 10.0 ft</small><b>Next impact at 7.0 ft</b>"), "selftest: tile/block impact mismatch did not fire"
    assert not hater_rules("<small>Next NWS impact at 7.0 ft</small><b>Next impact at 7.0 ft</b>"), "selftest: matching impacts wrongly flagged"
    assert hater_rules('<section id="recreation_sites"><h2>Recreation</h2><p class="src">Source: RIDB</p></section>'), "selftest: empty block did not fire"
    assert hater_rules("<p>NWS and USGS read this gauge on different zero points</p><p>102.5 ft against 104.30 ft at the gauge, so the forecast itself starts off the reading.</p>"), "selftest: cross-datum forecast comparison did not fire"
    assert not hater_rules("<p>where the NWS and USGS read this gauge on different zero points, the margins use the NWS reading.</p><p>4.1 ft against 2.30 ft at the gauge, so the forecast itself starts off the reading.</p>"), "selftest: general zero-point note with a same-datum comparison wrongly flagged"
    assert hater_rules("<small>1535 dams upstream</small>"), "selftest: count without a comma did not fire"
    assert not any("forecast point code" in x for x in hater_rules("<p>Weather station WGRM8 (WEST GLACIER), 6 mi away</p>")), "selftest: a named weather station ID wrongly flagged as an NWS point code"
    assert hater_rules("<b>Steady: -3.4% flow in 6 h</b><div>Last 6 h ▼ -3.4% -40 cfs</div>"), "selftest: 'Steady' beside a -3.4%, -40 cfs change did not fire"
    assert not hater_rules("<b>Falling: -3.4% flow in 6 h</b><div>Last 6 h ▼ -3.4% -40 cfs</div>"), "selftest: a correct direction word wrongly flagged"
    assert "%.1f" % r1(7.0 - 2.45) == "4.6", "selftest: stage difference 7.0 - 2.45 did not round half up"
    assert hater_rules('<span>NWS forecast (steady)</span><b>3.0 ft</b><li class="fcl">Forecast high <b>3.0 ft</b></li>'), "selftest: two names for one forecast did not fire"
    assert hater_rules('<section id="river_forecast"><div class="rc"><span class="rt">Oct 29</span><b>3.0 ft</b><small>1,110 cfs</small></div><div class="rc"><span class="rt">From Oct 29 to Nov 2</span><b>3.0 ft</b><small>1,110 cfs</small></div></section>'), "selftest: identical neighbouring forecast cards did not fire"
    assert hater_rules("<td>considered \u00c3\u00a2\u00e2\u201a\u00ac\u00c5\u201clow for paddlers</td>"), "selftest: garbled characters did not fire"
    assert demoji("considered \u00c3\u00a2\u00e2\u201a\u00ac\u00c5\u201clow") == "considered \u201clow", "selftest: demoji did not repair triple-encoded text"
    assert not hater_rules("<small>1,535 dams upstream since 2025</small>"), "selftest: comma'd count wrongly flagged"
    assert hater_rules('<p class="gaps">Not available for this gauge: hourly weather (no NWS hourly forecast).</p><section class="card blk" id="hourly_heatmap"><table><tr><td>1</td></tr></table></section>'), "selftest: 'not available' over a shown hourly block did not fire"
    pg = lambda title, h1, first, links: ('<title>%s</title><main><h1>%s</h1><div class="hero">%s</div><section class="card blk" id="x"></section>%s</main>'
                                          % (title, h1, first, "".join('<a href="/river/r/p%d/">x</a>' % i for i in range(links))))
    good_pg = pg("Lehigh River, Lehighton: live water level and flow", "Lehigh River at Lehighton, PA", "498 cfs normal range", 4)
    assert not rank_checks(good_pg, "/river/lehigh-river/lehighton/"), "selftest: a page that answers the search wrongly failed: %s" % rank_checks(good_pg, "/river/lehigh-river/lehighton/")
    assert any("title" in x for x in rank_checks(pg("Gauge 01449000 data", "Lehigh River at Lehighton, PA", "x", 4), "/u/")), "selftest: a title missing the river and 'water level' did not fire"
    assert any("first screen says" in x for x in rank_checks(pg("Lehigh River, Lehighton: water level", "Lehigh River at Lehighton, PA", " ".join(["(as of the oct 26, 9:30 pm edt reading)"] * 3), 4), "/u/")), "selftest: a phrase stamped 3 times on the first screen did not fire"
    assert not any("other gauge pages" in x for x in rank_checks(pg("Lehigh River, Lehighton: water level", "Lehigh River at Lehighton, PA", "x", 1), "/u/")), "selftest: a page linking 1 other gauge is held again (review 2026-11-08: few_neighbours warns, never holds)"
    assert css_truncation(".tile small{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}"), "selftest: caption ellipsis did not fire"
    assert not rank_checks(pg("Madison River, Below Hebgen Lake Near Grayling: water level", "Madison River below Hebgen Lake Near Grayling, MT", "Home / MT / Madison River / Below Hebgen Lake Near Grayling USGS gauge 06038500 observed Oct 26. Cite: Madison River below Hebgen Lake Near Grayling, MT: water level 1.5 ft", 4), "/u/"), "selftest: the page's own name repeated in breadcrumb, H1 and cite wrongly flagged"
    assert not rank_checks(pg("Rio Grande, Albuquerque: water level", "Rio Grande at Albuquerque, NM", "x", 4), "/u/"), "selftest: a river named without the word river wrongly flagged"
    assert not css_truncation(".tile small{display:block}"), "selftest: plain caption CSS wrongly flagged"
    w_ok = "async function poll(env) { await fetch(USGS); }\nasync function build(env) { await fetch(GH); }\nasync function serve(req, env) { return env.ASSETS.fetch(req); }"
    assert not visitor_calls(w_ok), "selftest: timer-only outside calls wrongly flagged: %s" % visitor_calls(w_ok)
    assert visitor_calls(w_ok + "\nasync function page(req) { return fetch('https://api.waterdata.usgs.gov/x'); }"), "selftest: worker calling USGS on a page view did not fire"
    assert cloak_risks('const ua = req.headers.get("User-Agent");'), "selftest: worker reading the user agent did not fire"
    assert cloak_risks("if (request.cf.botManagement.score < 30) {}"), "selftest: worker reading the bot score did not fire"
    assert not cloak_risks('fetch(u, { headers: { "User-Agent": UA } })'), "selftest: our own outgoing user agent wrongly flagged"
    w_real = open(os.path.join(ROOT, "worker", "index.js"), encoding="utf-8").read()
    assert not edge_drift(w_real), "selftest: %s" % edge_drift(w_real)
    css_ = open(os.path.join(ROOT, "templates", "site.css"), encoding="utf-8").read()
    assert control_chars({"x": "a" + chr(21) + "b"}) and not control_chars({"x": "a\tb\n"}), "selftest: a raw control byte in code passed, or a tab failed"
    assert wide_tables("<thead><tr>" + "<th>a</th>" * 6 + "</tr></thead>") and not wide_tables("<thead><tr>" + "<th>a</th>" * 5 + "</tr></thead>"), "selftest: a 6-column table passed, or a 5-column one failed"
    from lib import ui as ui_
    cm_ = ui_.calm('<small>t</small><small class="dv">NWS: no flooding now or forecast</small><small>note</small>')
    assert "KJVY" in ui_.calm("<small>wind calm</small><small>Weather station KJVY, Nov 9, 1:30 AM EST</small><small>note</small>").split("<details")[0], "selftest: 'More' hid a reading time"
    assert "no flooding" in cm_.split("<details")[0] and "note" in cm_.split("<details")[1] and "<details" not in ui_.calm("<small>t</small><small>NWS: minor flood</small>"), "selftest: a tile's 'More' toggle hid a flood line, or kept a line it should fold"
    assert not colour_contrast(css_) and colour_contrast(css_.replace("--f-fc:#b45309", "--f-fc:#d97706")), "selftest: a colour-coded label under 4.5:1 on white passed, or the real colours failed: %s" % colour_contrast(css_)
    assert edge_drift(w_real.replace("m<2880", "m<2881")), "selftest: a worker age that drifted from AGE_FN did not fire"
    assert edge_drift(w_real.replace("AGE_CHIP_MIN = [90, 360]", "AGE_CHIP_MIN = [90, 240]")), "selftest: a worker age-chip cut-off that drifted from STALE_H did not fire"
    assert edge_drift(w_real.replace('"ft^3/s" : "ft"', '"m^3/s" : "m"')), "selftest: a worker that accepts another unit than lib/core.py UNIT_OF did not fire"
    from lib.core import series as series_
    assert not series_({"usgs": {"rows": [{"parameter_code": "00060", "time": "2026-11-07T00:00:00+00:00", "value": "7700", "unit_of_measure": "m^3/s"}]}}, "00060") and series_({"usgs": {"rows": [{"parameter_code": "00060", "time": "2026-11-07T00:00:00+00:00", "value": "272000", "unit_of_measure": "ft^3/s"}]}}, "00060"), "selftest: a flow in m^3/s was read as cfs (edge test 2026-11-07)"
    good = ('<!doctype html><title>T</title><meta name="description" content="A description that is long enough to pass the length rule."><meta property="og:title" content="t"><meta property="og:description" content="d"><meta property="og:url" content="u"><meta property="og:image" content="i"><link rel="canonical" href="%s/river/a/b/water/"><link rel="stylesheet" href="/site.0123456789.css"><link rel="manifest" href="/manifest.webmanifest"><main><h1>X</h1><p class="sub">USGS gauge 1 &middot; observed Oct 15, 7:00 PM CDT &middot; 5 min old</p><p class="answer"><span class="a2 dv lb">Typical for this date</span></p>'
            '<div class="hero"><div class="tile flow"><span>Latest flow</span><b>5 <small>cfs</small></b></div><div class="tile stage"></div><div class="tile norm dv"></div><div class="tile trend"></div></div>'
            '<section class="card blk" id="q"><h2>H</h2><p>x</p><p class="src">Source: USGS</p></section></main>' % SITE_URL)
    rel = os.path.join("river", "a", "b", "water", "index.html")
    assert check_html(good, rel) == [], check_html(good, rel)
    assert check_html(good.replace("<p>x</p>", "<p>A daily forecast for ZIP 99901.</p>"), rel) == [], "selftest: a ZIP code (Ketchikan 99901) read as a sentinel value (practice 2026-11-08)"
    broken = {"no source line": good.replace('<p class="src">Source: USGS</p>', ""), "wrong canonical": good.replace("/river/a/b/", "/river/x/y/"),
              "banned undefined": good.replace("<p>x</p>", "<p>undefined</p>"), "no unit": good.replace("<small>cfs</small>", "<small></small>"), "no zone": good.replace("CDT", ""),
              "th without scope": good.replace("<p>x</p>", "<table><tr><th>A</th></tr></table>"),
              "24 h change on a silent gauge": good.replace("<p>x</p>", '<table><tr><td>Pigeon <span class="oldm">2 d old</span></td><td class="r">0%</td></tr></table>'),
              "two h1": good.replace("<h1>X</h1>", "<h1>X</h1><h1>Y</h1>"),
              "jargon heading": good.replace("<h2>H</h2>", "<h2>Percentile for the date</h2>"),
              "jargon tile": good.replace('<div class="tile norm dv"></div>', '<div class="tile norm dv"><i class="ic"></i><span>Compared</span><b>23rd percentile</b></div>'),
              "empty widget": good.replace("<p>x</p>", '<div class="bars"></div>'),
              "image without size": good.replace("<p>x</p>", '<img src="/a.png" alt="a">'),
              "image without alt": good.replace("<p>x</p>", '<img src="/a.png" width="5" height="5">'),
              "sentinel value": good.replace("<p>x</p>", "<p>Water temperature -999999 degrees</p>"),
              "bad structured data": good.replace("<p>x</p>", '<script type="application/ld+json">{oops</script>'),
              "double full stop": good.replace("<p>x</p>", "<p>That is the 82nd percentile..</p>"),
              "heading skip": good.replace("<p>x</p>", "<h4>Deep</h4>"),
              "claims a page that does not exist": good.replace("<p>x</p>", "<p>The Forecast page has the river forecast.</p>"),
              "page weight": good.replace("<p>x</p>", "<p>" + "".join(hashlib.sha256(str(i).encode()).hexdigest() for i in range(2600)) + "</p>"),
              "sentence twice": good.replace("<p>x</p>", "<p>The same long sentence about the river repeated on the page. </p><p>" + "The same long sentence about the river repeated on the page. " + "</p>")}
    for name, h in broken.items():
        assert check_html(h, rel), "selftest: broken fixture passed: " + name
    # planted bugs from the 2026-10-25 incidents: each must fail with ITS message, not by accident
    aimed = {"page script calls USGS directly": good.replace("</main>", "<script>fetch('https://api.waterdata.usgs.gov/ogcapi/v1/x')</script></main>"),
             "ok:page script fetching our own copy": good.replace("</main>", "<script>fetch('/live/01449000.json')</script></main>"),
             "ok:page script asking NWS for alerts (keyless)": good.replace("</main>", "<script>fetch('https://api.weather.gov/alerts/active?point=1,2')</script></main>"),
             "tile caption repeats its own value": good.replace('<div class="tile trend"></div>', '<div class="tile calm"><span>Calm daylight hours today</span><b>5p to 6p</b><small>5p to 6p: no thunder</small></div><div class="tile trend"></div>'),
             "is-this-normal tile is not marked dv": good.replace("tile norm dv", "tile norm"),
             "ok:tidal range containing the value": good.replace('<div class="tile trend"></div>', '<div class="tile flowx"><span>Flow</span><b>11,400 cfs</b><small>Tidal reach: 11,400 to 15,000 cfs over 24 h</small></div><div class="tile trend"></div>'),
             "no unit on Gage height": good.replace('<div class="tile stage"></div>', '<div class="tile stage"><span>Gage height</span><b>2.53 <small>m</small></b></div>'),
             "ok:gage height not measured": good.replace('<div class="tile stage"></div>', '<div class="tile stage"><span>Gage height</span><b>Not measured</b><small>USGS reports no gage height at this gauge</small></div>'),
             "does not link the cacheable stylesheet": good.replace('<link rel="stylesheet" href="/site.0123456789.css">', "<style>.a{color:red}</style>"),
             "does not link the web app manifest": good.replace('<link rel="manifest" href="/manifest.webmanifest">', ""),
             "inline <style> of": good.replace("<p>x</p>", "<style>" + "a" * 2100 + "</style><p>x</p>"),
             "ok:small inline style": good.replace("<p>x</p>", "<style>.a{color:red}</style><p>x</p>"),
             "image after the first without loading=lazy": good.replace("<p>x</p>", '<img src="/a.png" alt="a" width="5" height="5"><img src="/b.png" alt="b" width="5" height="5" decoding="async">'),
             "ok:first image eager, the rest lazy": good.replace("<p>x</p>", '<img src="/a.png" alt="a" width="5" height="5"><img src="/b.png" alt="b" width="5" height="5" loading="lazy" decoding="async">'),
             "&lt;/?[a-zA-Z]+": good.replace('<div class="tile trend"></div>', '<div class="tile trend"></div><p>For more information click &lt;a href=&quot;x.php&quot;&gt;here&lt;/a&gt;.</p>'),
             "summary class is not marked dv": good.replace('class="a2 dv lb"', 'class="a2 lb"'),
             "status sentence is missing": good.replace('<p class="answer"><span class="a2 dv lb">Typical for this date</span></p>', ""),
             "not between the place name and the tiles": good.replace('<p class="answer"><span class="a2 dv lb">Typical for this date</span></p>', "").replace('<div class="tile trend"></div>', '<div class="tile trend"></div><p class="answer"><span class="a2 dv lb">Typical for this date</span></p>')}
    obs = {"nwps": {"lid": "MEMT1", "obs_stage": {"t": "2026-10-26T10:00:00Z", "v": 1.6}}}
    import datetime
    at = datetime.datetime(2026, 10, 26, 12, tzinfo=datetime.timezone.utc)
    assert claims_vs_cache('<span>Gage height</span><b>Not measured</b>', obs, at), "selftest: hidden NWS stage did not fire"
    zp_ = '<p class="sub">USGS gauge 1 &middot; observed Nov 8, 1:00 PM %s &middot; 5 min old</p>'
    assert any("labelled EST" in x for x in claims_vs_cache(zp_ % "EST", {"tz": "America/Denver"}, at)) and not claims_vs_cache(zp_ % "MST", {"tz": "America/Denver"}, at) and not claims_vs_cache(zp_ % "MDT", {"tz": "America/Denver"}, at) and not claims_vs_cache(zp_ % "MST", {"tz": "America/Phoenix"}, at), "selftest: a wrong zone label passed, or a right one (standard or daylight) failed (gate audit 2026-11-08)"
    assert not claims_vs_cache('<span>Gage height</span><b>1.60 <small>ft</small></b>', obs, at), "selftest: filled NWS stage wrongly failed"
    assert not claims_vs_cache('<span>Gage height</span><b>Not measured</b>', obs, at + datetime.timedelta(days=2)), "selftest: a 2-day-old NWS stage should not count"
    lvr = {"coops": {"level": {"id": "9449424", "name": "Cherry Point", "km": 23.3}, "station": "9449211"}}
    assert claims_vs_cache("<small>At NOAA station 9449424, Cherry Point</small> NOAA tide station 9449211 &middot; observed", lvr, at), "selftest: a prediction-only station shown beside an observed time passed"
    tbr = {"coops": {"tables": True, "station": "9432373", "near": {"id": "9432780", "name": "Charleston", "km": 26.1}}}
    tb_ok = '<p class="sub">NOAA tide station 9432373 &middot; tide predictions, times in PST &middot; fetched Nov 8, 4:49 PM PST</p><small>No sensor at this station. Nearest live NOAA water level: <a>Charleston</a></small>'
    assert not claims_vs_cache(tb_ok, tbr, at) and claims_vs_cache(tb_ok.replace("fetched", "observed"), tbr, at) and claims_vs_cache(tb_ok.replace("No sensor at this station", "x"), tbr, at), "selftest: tide-tables page rule (no observed time, nearest live level named)"
    assert claims_vs_cache("<b>4.10</b>", lvr, at) and not claims_vs_cache("<small>At NOAA station 9449424, Cherry Point, 23.3 km away</small>", lvr, at), "selftest: a prediction-only page did not name the station its water level comes from"
    emb = good.replace('<link rel="stylesheet" href="/site.0123456789.css"><link rel="manifest" href="/manifest.webmanifest">', "<style>" + "a" * 5000 + "</style>")
    assert not any("stylesheet" in x or "manifest" in x or "inline <style>" in x for x in check_html(emb, os.path.join("embed", "river", "a", "b", "index.html"))), "selftest: an embed page was wrongly held to the shared-stylesheet rules"
    sw_real = open(os.path.join(ROOT, "templates", "sw.js"), encoding="utf-8").read()
    assert not sw_drift(sw_real), "selftest: %s" % sw_drift(sw_real)
    assert sw_drift(sw_real.replace("m<2880", "m<2881")), "selftest: an sw.js age that drifted from AGE_FN did not fire"
    for want, h in aimed.items():
        got = check_html(h, rel)
        if want.startswith("ok:"):  # a near-miss that must NOT fire (2026-10-26 CI: a tidal range holding the reading)
            assert not got, "selftest: %r wrongly failed: %s" % (want, got)
            continue
        assert any(want in g for g in got), "selftest: %r did not fire (got %s)" % (want, got)
    kf = '<section class="card blk" id="key_facts"><ul class="facts"><li>X is USGS gauge 1 in Y County.</li></ul><p class="src">Sources: USGS. These facts change rarely.</p></section>'
    assert not [b for b in hater_rules('<section id="about_gauge"></section>' + kf) if "Key facts" in b], "selftest: a good Key facts block failed"
    assert any("no Key facts" in b for b in hater_rules('<section id="about_gauge"></section>')), "selftest: a page with a station record and no Key facts passed"
    assert any("live reading" in b for b in hater_rules(kf.replace("in Y County.", 'flows <b data-live="flow">5</b> cfs now.'))), "selftest: Key facts holding the live reading passed"
    import tools.edge_tests
    tools.edge_tests.run()
    import runpy
    runpy.run_path(os.path.join(ROOT, "lib", "census.py"), run_name="__main__")  # the coverage census counts every official site
    runpy.run_path(os.path.join(ROOT, "lib", "ledger.py"), run_name="__main__")  # the run-time ledger names a stage before it hits its limit
    print("selftest OK: good fixture passes, %d broken fixtures all fail, %d incident fixtures fail with their own message" % (len(broken), len(aimed)))


SECRET = re.compile(r"(?i)(api[_-]?key|x-api-key|secret|authorization|bearer|cloudflare_api_token)[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{20,}")


def secret_scan(d):
    """No key, token or secret in any built text file, and none of this machine's own key values."""
    bad, own = [], [v for k_, v in os.environ.items() if k_ in ("USGS_API_KEY", "CLOUDFLARE_API_TOKEN", "AIRNOW_API_KEY", "RIDB_API_KEY") and len(v) >= 12]
    for root, _, fs in os.walk(d):
        for f in fs:
            if f.endswith((".png", ".gz", ".ico")):
                continue
            t = open(os.path.join(root, f), encoding="utf-8", errors="ignore").read()
            if SECRET.search(t) or any(v in t for v in own):
                bad.append(os.path.relpath(os.path.join(root, f), d))
    return bad


CARRY_MAX = 10  # above max(10, 5% of gauge pages) failing at once a warning is printed; no count stops the release (owner 2026-11-08)


def keep_old_times(d, rels):
    """A carried page is old: _built.json and live-sites.json must say so, or the 6 h alarm stays quiet and the Worker dates old content as new."""
    try:
        lp, bp = os.path.join(d, "live-sites.json"), os.path.join(d, "_built.json")
        live, built = json.load(open(lp, encoding="utf-8")), json.load(open(bp, encoding="utf-8"))
        old_live = {x[0]: x for x in json.load(open(os.path.join(ROOT, "dist", "live-sites.json"), encoding="utf-8"))}
        old_built = json.load(open(os.path.join(ROOT, "dist", "_built.json"), encoding="utf-8"))
    except (OSError, ValueError) as e:
        return print("carried pages keep this build's times:", str(e)[:80])
    urls = {r.replace("\\", "/").rsplit("index.html", 1)[0].strip("/") for r in rels}
    for i, x in enumerate(live):
        if x[1].strip("/") in urls and x[0] in old_live:
            live[i] = old_live[x[0]]
            if x[0] in old_built:
                built[x[0]] = old_built[x[0]]
    for k in [k for k in built if k.startswith("/") and k.strip("/") in urls and k in old_built]:  # world pages are keyed by URL (build.py)
        built[k] = old_built[k]
    json.dump(live, open(lp, "w"), separators=(",", ":"))
    json.dump(built, open(bp, "w"), separators=(",", ":"))


def carry(d, fails, got=None):
    """Replace each failing gauge page with its live copy (dist/ when present, else the live site), so the other pages ship. True when every one was replaced."""
    import shutil, urllib.request
    ok = True
    for rel in fails:
        dst, old = os.path.join(d, rel), os.path.join(ROOT, "dist", rel)
        try:
            if os.path.isfile(old):
                shutil.copy2(old, dst)
            else:
                url = "https://riverwaterlevels.com/" + rel.replace("\\", "/").rsplit("index.html", 1)[0]
                open(dst, "wb").write(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "riverwaterlevels.com publish"}), timeout=30).read())
            got is not None and got.append(rel)
            print("CARRIED previous live page for", rel, "(this build's page failed:", "; ".join(fails[rel])[:160] + ")")
        except Exception as e:
            print("could not carry", rel, e)
            ok = False
    return ok


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # review notes quote page symbols (a Windows console is cp1252)
    if "--selftest" in sys.argv:
        return selftest()
    d = next((a for a in sys.argv[1:] if not a.startswith("--")), os.path.join(ROOT, "dist_next"))
    res, site_bad, maxd = check_dir(d)
    try:  # pages already carried (gate 1 or truth_live) are the live ones
        done = {r.replace("/", os.sep) for r in json.load(open(os.path.join(d, "_carried.json")))}
    except (OSError, ValueError):
        done = set()
    fails = {k: v for k, v in res.items() if v and k not in done}
    if len(fails) > max(CARRY_MAX, sum(1 for k in res if kind_of(k) in CARRYABLE) // 20):  # a template or checker fault: said loudly, still page by page (owner 2026-11-08 fully automatic: no count stops the release)
        print("WARNING: %d pages failed at once (template or checker fault?); each keeps its live copy or goes back to the queue" % len(fails))
    if "--carry" in sys.argv and fails and not site_bad and all(kind_of(k) in CARRYABLE for k in fails):
        got = []
        if not carry(d, fails, got) and got:  # release 2026-11-07: pages that were carried are recorded even when a new one could not be, so quarantine.py sees them as shipped, not failed
            keep_old_times(d, set(got))
            json.dump(sorted({r.replace("\\", "/") for r in set(got) | done}), open(os.path.join(d, "_carried.json"), "w"))
        elif got and len(got) == len(fails):  # owner 2026-10-28: one bad page must not hold every other fix off the site
            carried = set(fails)
            keep_old_times(d, carried)
            json.dump(sorted({r.replace("\\", "/") for r in carried | done}), open(os.path.join(d, "_carried.json"), "w"))
            res, site_bad, maxd = check_dir(d)
            fails = {k: v for k, v in res.items() if v and k not in carried and k not in done}  # a carried page is the live one: it passed the checks of its own release
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
    if fails or site_bad:  # tools/quarantine.py reads this after a failed release
        json.dump({"pages": fails, "site": site_bad}, open(os.path.join(d, "_failed.json"), "w", encoding="utf-8"))
    sys.exit(1 if (fails or site_bad) else 0)


main()
