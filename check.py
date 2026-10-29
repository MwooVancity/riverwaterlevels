"""Gate 1 page and site checks. Usage: python -I check.py [dir]   |   python -I check.py --selftest
Per page: canonical, banned strings, doubled words, source line per block, units, gauge-local time, one h1, weight.
Site: unique titles, every internal link resolves, sitemap equals page set, tab/hub/state reciprocity, link budgets, no orphans, depth from home.
Exit 1 if anything fails.
"""
import os, re, sys, json, collections, gzip, hashlib, html
MAX_GZ = 90000  # pilot pages are about 48 KB compressed; tail pages carry fewer blocks
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.common import ROOT, SITE_URL, MOJI, demoji

BANNED = [r"\bin our data\b", r"\bpage as built\b", r"live check did not answer", r"\(water first\)",  # hater round 2 (2026-10-27): builder's jargon a reader cannot parse
          r"\bForecast page\b", r"\bsecond .{0,20}page\b", r"prototype", r"licen[cs]e", r"\bConf\b", r"\bSr\d{3,}", r"__[A-Z_]+__", r"\bundefined\b", r"\bNaN\b", r"\bNone\b", r"Unnamed [a-z ]*(boat ramp|fishing spot)", r"-?\b9{5,}\b", r"-?999\d{2,}\b", r"\b20\d\d-\d\d-\d\d[T ]\d\d:\d\d", r"&lt;/?[a-zA-Z]+[\s>&/]"]  # last: source HTML shown to the reader as text (NWS impact link, Clear Creek 2026-10-26)  # the last three (the ISO one: a raw machine timestamp shown to a reader; the other two: USGS sentinel values (-999999) must never be shown as readings)
MAX_BYTES = 260_000  # raw HTML; the reader limit is MAX_GZ (90 KB compressed). Raised 2026-10-21 for the camera, air-quality and recreation blocks (Roaring Fork 231 KB raw, 56 KB gzipped)
BUDGET = {"gauge": 125, "hub": 80, "state": 480, "home": 200, "trust": 60, "status": 600}  # status 2026-10-25: the freshness dashboard links every gauge (69 at 53 gauges); own budget so it doesn't share the prose-page trust cap. At scale (~500+ gauges) the status page needs pagination - a known scale item, like the state 480-link ceiling.  # trust 40->60 2026-10-21 (footer "Add to your site" + status page); gauge 110->125 2026-10-23: new data blocks (stocking, UV, sustained flow, access points) each add source/record links on data-heavy gauges like the Potomac
FLOOR = {"gauge": 5000, "hub": 700, "home": 1500, "trust": 300, "state": 650}  # min visible chars for an INDEXABLE page; a thinner indexable page reads as thin/near-duplicate to Google. State hubs carry statewide drought + NWS alerts + a conditions table (~1000+ chars); the 650 floor catches a genuinely broken/empty hub while tolerating a transient missing-drought blip. 2026-10-23: the long-tail thin-page guard the whole-project review flagged as missing.


def kind_of(rel):
    parts = rel.replace("\\", "/").split("/")
    if rel == "index.html":
        return "home"
    if parts[0] == "rivers":
        return "state"
    if parts[0] == "status":  # the all-gauges freshness dashboard: one link per gauge, grows with the site, not a prose page
        return "status"
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
    text = re.sub(r"<[^>]+>", " ", re.sub(r"<br\s*/?>|</t[dh]>", " | ", re.sub(r"(?s)<(pre|code)\b.*?</\1>", " ", body)))  # code samples (the embed snippet) are meant to show markup; a line or cell break is a break, not a space ("Truckee<br>Truckee River")
    for mm in re.finditer(r"fetch\(\s*['\"](https?:)?//[^'\"]*waterdata\.usgs\.gov", h):  # USGS is the one keyed, metered API: readings come from our stored copy (NWS alerts are keyless and stay direct)
        bad.append("page script calls USGS directly (%r): live readings must come from our stored copy" % h[mm.start():mm.start() + 60])
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
            if need == 'class="tile trend' and ("Tidal reach:" in head or "Rose and fell:" in head):
                continue  # a tidal reach has no 6 h direction; hero.py prints the day's range instead
            if need not in head:
                bad.append("first screen missing %s" % need.split('"')[1])
        # the edge swaps in a newer reading; everything the build derived from the old one (class word, trend, summary) must be marked dv so it gets its own "as of" time
        if 'class="tile norm' in head and not re.search(r'class="tile norm[^"]*\bdv\b', head):
            bad.append("first screen: the is-this-normal tile is not marked dv (would show an old class under a swapped reading with no time)")
        if '<p class="answer"' in head and not re.search(r'class="a2 dv\b', head):
            bad.append("first screen: the summary class is not marked dv")
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
        if not sub or not re.search(r"observed [A-Z][a-z]{2} \d{1,2}, \d{1,2}:\d{2} [AP]M [A-Z]{2,5}", re.sub(r"<[^>]+>", "", sub.group(1))):
            bad.append("observed time without gauge-local zone label")
    return bad


def claims_vs_cache(h, rec, now=None):
    """A page that says a value is missing while our own cache holds it fresh has hidden data (Memphis: 'no gage height' while NWS MEMT1 observed it)."""
    import datetime
    now = now or datetime.datetime.now(datetime.timezone.utc)
    bad = []
    o = (rec.get("nwps") or {}).get("obs_stage") or {}
    try:
        fresh = (now - datetime.datetime.fromisoformat(o["t"].replace("Z", "+00:00"))).total_seconds() < 24 * 3600 and float(o["v"]) > -999
    except (KeyError, TypeError, ValueError, AttributeError):
        fresh = False
    if fresh and re.search(r"<span>Gage height</span><b>Not measured", h):
        bad.append("gage height shown as not measured while NWS %s observed it at %s" % ((rec.get("nwps") or {}).get("lid"), o["t"]))
    if (rec.get("tides") or {}).get("rows") and "tide predictions (no NOAA station" in h:
        bad.append("gaps line says no tide station while the cache holds NOAA tide predictions")
    return bad


DUP_MAX = 0.80  # owner rule: no two pages over 80% the same text (Google scaled-content policy); 2026-10-27 worst pair 68%


def shingles(h):
    """5-word shingles of the visible <main> text with every number masked, so two pages differ only by what they SAY, not their readings."""
    b = h.split("<main", 1)[1].split("</main>")[0] if "<main" in h else h
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style|svg)\b.*?</\1>", " ", b))).lower()
    w = re.sub(r"\d[\d,.:]*", "#", t).split()
    return {hash(" ".join(w[i:i + 5])) for i in range(len(w) - 4)}


def near_dupes(sh):
    """Pairs of gauge pages sharing more than DUP_MAX of their text. ponytail: all pairs, fine to ~3,000 pages (4.5M set ops); past that compare within a state or use MinHash."""
    ks = sorted(sh)
    return [(a, b, j) for i, a in enumerate(ks) for b in ks[i + 1:] if sh[a] and sh[b] and (j := len(sh[a] & sh[b]) / len(sh[a] | sh[b])) > DUP_MAX]


def cloak_risks(js):
    """Google's cloaking rule: crawlers and people must get the same page. The edge Worker therefore never reads the visitor's identity."""
    pat = r"""(?i)\b(?:req|request)\.(?:cf\b|headers\.get\(\s*["'](?:user-agent|sec-ch-ua[\w-]*|cf-ipcountry|cf-connecting-ip|x-forwarded-for|cf-bot[\w-]*)["'])"""
    return ["edge worker reads the visitor's identity (%s): Google and phones could get different pages" % m.group(0) for m in re.finditer(pat, js)]


TIMER_ONLY = ("poll", "build")  # worker functions run by the cron, never by a visitor's request


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


def review_gaps(live_sites, reviews, code):
    """Owner 2026-10-27: no page is live unless a hater looked at it. reviews = {id: record from state/reviews}; code = template_hash()."""
    bad = []
    t = reviews.get("_template")
    if not t or t.get("verdict") != "PASS" or t.get("template") != code:
        bad.append("page code changed since the last signed hater review (code %s, last PASS %s): screenshot a sample, review it, sign _template" % (code, (t or {}).get("template") if (t or {}).get("verdict") == "PASS" else "none"))
    for s_ in sorted(live_sites):
        r = reviews.get(s_)
        if not r or r.get("verdict") != "PASS":
            bad.append("gauge %s is live without a signed hater PASS (%s)" % (s_, "FAIL: " + r["notes"][:80] if r else "never reviewed"))
    return bad


def load_reviews():
    d = os.path.join(ROOT, "state", "reviews")
    return {f[:-5]: json.load(open(os.path.join(d, f), encoding="utf-8")) for f in (os.listdir(d) if os.path.isdir(d) else []) if f.endswith(".json")}


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
    if miss or "water level" not in title.lower():
        bad.append("title %r does not match the search (missing %s)" % (title[:80], ", ".join(miss + ([] if "water level" in title.lower() else ["water level"]))))
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
    others = {u for u in re.findall(r'href="(/river/[^"#?]+/)"', h) if u != url}
    if len(others) < 3:
        bad.append("links only %d other gauge pages (at least 3: nearby, upstream, downstream)" % len(others))
    return bad


def css_truncation(css):
    """Reader text is never cut off with an ellipsis or a line clamp (hater 2026-10-27: 'No sensor at this ga...' hid where 48 F came from)."""
    return ["site.css cuts reader text off (%s)" % m.group(0) for m in re.finditer(r"text-overflow\s*:\s*ellipsis|line-clamp\s*:", css)]


def hater_rules(h):
    """Defects the first hater round found on every page that a machine can see in the built HTML."""
    bad = []
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))
    if re.search(r"Thunderstorms: none", t):
        row = re.search(r"Thunder %((?:\s+[\d\u2013-]+)+)", t)
        if row and any(x.isdigit() and int(x) > 0 for x in row.group(1).split()):
            bad.append("says 'Thunderstorms: none' while the hourly table shows a thunder chance above 0")
    m = re.search(r"(?<![\d.,])\b1 (hours|days|years|miles|minutes) (ago|earlier|before|away)", t)  # not the tail of "1.1 days ago"
    if m:
        bad.append("ungrammatical %r" % m.group(0))
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
    for lab in re.findall(r"<tr><th>([^<]*)</th>", hm.group(0) if hm else ""):
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
    return bad


def check_dir(d):
    """One pass, one page in memory at a time: only small per-page facts (title, links, link count) are kept, so 30,000 pages need megabytes, not gigabytes."""
    urlof = lambda rel: "/" + os.path.dirname(rel).replace("\\", "/") + "/" if os.path.dirname(rel) else "/"
    results, titles, links_of, n_links, rel_of, noindex_of, vis_of = {}, collections.defaultdict(list), {}, {}, {}, {}, {}
    gauge_sh = {}
    for root, _, fs in os.walk(d):
        for f in fs:
            if f.endswith(".html") and f != "404.html":
                p = os.path.join(root, f)
                rel = os.path.relpath(p, d)
                h = open(p, encoding="utf-8").read().replace("\u00a0", " ")  # times use no-break spaces for wrapping
                results[rel] = check_html(h, rel) + ((rank_checks(h, urlof(rel)) + hater_rules(h)) if kind_of(rel) == "gauge" else [])
                sid = re.search(r"USGS gauge (\d{8,15})\b", h)
                cp = os.path.join(ROOT, "cache", sid.group(1) + ".json") if sid else None
                if cp and os.path.exists(cp):
                    results[rel] += claims_vs_cache(h, json.load(open(cp, encoding="utf-8")))
                stp = os.path.join(ROOT, "legacy", "stats", sid.group(1) + ".json") if sid else None
                if stp and "no published statistics for this date" in h and os.path.exists(stp) and len(json.load(open(stp)).get("d") or {}) >= 300:  # wave 3 2026-10-27: "is this normal" blank on 6 of 6 pages while the USGS statistics file was in the repo
                    results[rel].append("says 'no published statistics' while legacy/stats holds this gauge's USGS daily statistics")
                t = re.search(r"<title>(.*?)</title>", h)
                titles[t.group(1) if t else ""].append(rel)
                u = urlof(rel)
                rel_of[u] = rel
                links_of[u] = set(re.findall(r'href="(/[^"#?]*)"', h))
                noindex_of[u] = bool(re.search(r'<meta name="robots" content="noindex', h))
                n_links[u] = len(re.findall(r"<a ", h))
                if kind_of(rel) == "gauge" and 'class="hero' in h and not re.search(r'<meta name="robots" content="noindex', h):
                    gauge_sh[u] = shingles(h)
                vis_of[u] = len(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S))))
    site_bad = []
    urls = rel_of
    wjs = open(os.path.join(ROOT, "worker", "index.js"), encoding="utf-8").read()
    site_bad += cloak_risks(wjs) + visitor_calls(wjs) + css_truncation(open(os.path.join(ROOT, "templates", "site.css"), encoding="utf-8").read())
    from lib.common import template_hash
    import csv as _csv
    live_now = {r["site"] for r in _csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8")) if r["status"] == "live"}
    lsp = os.path.join(d, "live-sites.json")  # judge the gauge pages actually built, not only the list (2026-10-27: 22 queued gauges were built and published)
    live_now |= {r[0] for r in json.load(open(lsp, encoding="utf-8"))} if os.path.exists(lsp) else set()
    site_bad += review_gaps(live_now, load_reviews(), template_hash())
    for a, b, j in near_dupes(gauge_sh):
        site_bad.append("near-duplicate pages: %s and %s share %.0f%% of their text (limit %.0f%%)" % (a, b, 100 * j, 100 * DUP_MAX))
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
    static = {"/sitemap.xml", "/robots.txt", "/favicon.svg", "/og.png", "/favicon.ico", "/status.json", "/llms.txt", "/ads.txt", "/live-sites.json", "/_health.json"} | {"/sitemap-%d.xml" % i for i in range(1, 20)}
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
        from lib import indexing
        cfg = indexing.load(ROOT)
        if bool(cfg["open"]) != open_mode:
            site_bad.append("data/index-allow.json (open=%s) and the built _headers (noindex rule present=%s) disagree" % (cfg["open"], not open_mode))
        if open_mode:
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
    try:  # pipeline review #2: a gauge whose build failed keeps its previous page (publish.py); it is reachable again once its data recovers
        kept = set(json.load(open(os.path.join(d, "status.json"), encoding="utf-8")).get("failed_urls") or [])
    except (OSError, ValueError):
        kept = set()
    orphans = [u for u in urls if u not in depth and u not in kept]
    if orphans:
        site_bad.append("%d pages not reachable from home, e.g. %s" % (len(orphans), orphans[:3]))
    deep = [u for u, k in depth.items() if k > 4]
    if deep:
        site_bad.append("pages deeper than 4 clicks: %s" % deep[:3])
    return results, site_bad, (max(depth.values()) if depth else 0)


def selftest():
    assert hater_rules("<p>Thunderstorms: none in the forecast</p><tr><th>Thunder %</th><td>9</td><td>11</td></tr>"), "selftest: 'none' over a thunder chance did not fire"
    assert not hater_rules("<p>Thunderstorms: none in the forecast</p><tr><th>Thunder %</th><td>0</td><td>0</td></tr>"), "selftest: 'none' over zero thunder wrongly flagged"
    assert hater_rules("<small>Peak: 1 hours ago.</small>"), "selftest: '1 hours ago' did not fire"
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
    assert hater_rules('<table class="hm"><tbody><tr><th>Rain or snow (water) in/h</th><td>0</td></tr></tbody></table>'), "selftest: long hourly label did not fire"
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
    assert any("other gauge pages" in x for x in rank_checks(pg("Lehigh River, Lehighton: water level", "Lehigh River at Lehighton, PA", "x", 1), "/u/")), "selftest: a page linking 1 other gauge did not fire"
    assert css_truncation(".tile small{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}"), "selftest: caption ellipsis did not fire"
    assert not rank_checks(pg("Madison River, Below Hebgen Lake Near Grayling: water level", "Madison River below Hebgen Lake Near Grayling, MT", "Home / MT / Madison River / Below Hebgen Lake Near Grayling USGS gauge 06038500 observed Oct 26. Cite: Madison River below Hebgen Lake Near Grayling, MT: water level 1.5 ft", 4), "/u/"), "selftest: the page's own name repeated in breadcrumb, H1 and cite wrongly flagged"
    assert not rank_checks(pg("Rio Grande, Albuquerque: water level", "Rio Grande at Albuquerque, NM", "x", 4), "/u/"), "selftest: a river named without the word river wrongly flagged"
    assert not css_truncation(".tile small{display:block}"), "selftest: plain caption CSS wrongly flagged"
    ok_rev = {"_template": {"verdict": "PASS", "template": "abc"}, "01": {"verdict": "PASS", "notes": ""}}
    assert not review_gaps({"01"}, ok_rev, "abc"), "selftest: reviewed page on reviewed code wrongly blocked"
    assert any("without a signed hater PASS" in x for x in review_gaps({"01", "02"}, ok_rev, "abc")), "selftest: unreviewed live gauge did not block"
    assert any("code changed" in x for x in review_gaps({"01"}, ok_rev, "xyz")), "selftest: changed page code without a new review did not block"
    assert any("FAIL" in x for x in review_gaps({"01"}, dict(ok_rev, **{"01": {"verdict": "FAIL", "notes": "tidal on a dam river"}}), "abc")), "selftest: a FAIL verdict did not block"
    w_ok = "async function poll(env) { await fetch(USGS); }\nasync function build(env) { await fetch(GH); }\nasync function serve(req, env) { return env.ASSETS.fetch(req); }"
    assert not visitor_calls(w_ok), "selftest: timer-only outside calls wrongly flagged: %s" % visitor_calls(w_ok)
    assert visitor_calls(w_ok + "\nasync function page(req) { return fetch('https://api.waterdata.usgs.gov/x'); }"), "selftest: worker calling USGS on a page view did not fire"
    assert cloak_risks('const ua = req.headers.get("User-Agent");'), "selftest: worker reading the user agent did not fire"
    assert cloak_risks("if (request.cf.botManagement.score < 30) {}"), "selftest: worker reading the bot score did not fire"
    assert not cloak_risks('fetch(u, { headers: { "User-Agent": UA } })'), "selftest: our own outgoing user agent wrongly flagged"
    wd = lambda i, p: p + "".join(chr(97 + int(c)) for c in str(i))  # digit-free words: numbers are masked before comparing
    a = "<main>" + " ".join(wd(i, "w") for i in range(300)) + " flow 120 cfs</main>"
    assert near_dupes({"/x/": shingles(a), "/y/": shingles(a.replace("flow 120", "flow 9,400"))}), "selftest: near-duplicate pages (same words, other readings) did not fire"
    assert not near_dupes({"/x/": shingles(a), "/y/": shingles("<main>" + " ".join(wd(i, "z") for i in range(300)) + "</main>")}), "selftest: distinct pages wrongly flagged"
    good = ('<!doctype html><title>T</title><meta name="description" content="A description that is long enough to pass the length rule."><meta property="og:title" content="t"><meta property="og:description" content="d"><meta property="og:url" content="u"><meta property="og:image" content="i"><link rel="canonical" href="%s/river/a/b/water/"><main><h1>X</h1><p class="sub">USGS gauge 1 &middot; observed Oct 15, 7:00 PM CDT &middot; 5 min old</p>'
            '<div class="hero"><div class="tile flow"><span>Latest flow</span><b>5 <small>cfs</small></b></div><div class="tile stage"></div><div class="tile norm dv"></div><div class="tile trend"></div></div>'
            '<section class="card blk" id="q"><h2>H</h2><p>x</p><p class="src">Source: USGS</p></section></main>' % SITE_URL)
    rel = os.path.join("river", "a", "b", "water", "index.html")
    assert check_html(good, rel) == [], check_html(good, rel)
    broken = {"no source line": good.replace('<p class="src">Source: USGS</p>', ""), "wrong canonical": good.replace("/river/a/b/", "/river/x/y/"),
              "banned undefined": good.replace("<p>x</p>", "<p>undefined</p>"), "no unit": good.replace("<small>cfs</small>", "<small></small>"), "no zone": good.replace("CDT", ""),
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
             "&lt;/?[a-zA-Z]+": good.replace('<div class="tile trend"></div>', '<div class="tile trend"></div><p>For more information click &lt;a href=&quot;x.php&quot;&gt;here&lt;/a&gt;.</p>'),
             "summary class is not marked dv": good.replace('<div class="tile trend"></div>', '<div class="tile trend"></div><p class="answer"><span class="a2 lb">Normal range</span></p>')}
    obs = {"nwps": {"lid": "MEMT1", "obs_stage": {"t": "2026-10-26T10:00:00Z", "v": 1.6}}}
    import datetime
    at = datetime.datetime(2026, 10, 26, 12, tzinfo=datetime.timezone.utc)
    assert claims_vs_cache('<span>Gage height</span><b>Not measured</b>', obs, at), "selftest: hidden NWS stage did not fire"
    assert not claims_vs_cache('<span>Gage height</span><b>1.60 <small>ft</small></b>', obs, at), "selftest: filled NWS stage wrongly failed"
    assert not claims_vs_cache('<span>Gage height</span><b>Not measured</b>', obs, at + datetime.timedelta(days=2)), "selftest: a 2-day-old NWS stage should not count"
    for want, h in aimed.items():
        got = check_html(h, rel)
        if want.startswith("ok:"):  # a near-miss that must NOT fire (2026-10-26 CI: a tidal range holding the reading)
            assert not got, "selftest: %r wrongly failed: %s" % (want, got)
            continue
        assert any(want in g for g in got), "selftest: %r did not fire (got %s)" % (want, got)
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


CARRY_MAX = 10  # more failing gauge pages than this is a template fault: the whole release stops


def carry(d, fails):
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
    if "--carry" in sys.argv and fails and not site_bad and len(fails) <= CARRY_MAX and all(kind_of(k) == "gauge" for k in fails):
        if carry(d, fails):  # owner 2026-10-28: one bad page must not hold every other fix off the site
            carried = set(fails)
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
    sys.exit(1 if (fails or site_bad) else 0)


main()
