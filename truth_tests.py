"""Truth gates: the contradictions and silences a reader should never meet. Each one comes from a defect a fresh-eyes reviewer found (docs/research/FRESH-REVIEW-6.md).
Usage: python -I truth_tests.py     (run by tests.py after a build; needs dist_next)
 1. Direction: the trend tile's word agrees with the sign of its headline and with the last 6 h of flow, on every gauge.
 2. Bands: for every comparison band (very low .. very high) the word, the sentence ("Lower than" below the middle, "Higher than" above) and the numbers agree.
 3. Silence: a gauge with no NWS river forecast says so; with an active alert there is a banner and no empty-alert tile; without one the tile says so.
 4. Time: a marker called "Now" never appears; the stage marker carries the time of the reading.
 5. Plain words on home and state pages (no ordinals like 91st or "above 95th" in tables).
Every check prints the page and the quote when it fails. Exit 1 on any failure."""
import os, sys, re, json, copy, datetime
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from lib import render  # noqa: E402
from lib.pages import load_effective  # noqa: E402

bad = []


def fail(where, msg):
    bad.append("%s: %s" % (where, msg))


def main():
    rows, _ = load_effective()
    now = datetime.datetime.now(datetime.timezone.utc)
    n = 0
    base = None
    for f in sorted(os.listdir(os.path.join(ROOT, "cache"))):
        if not f.endswith(".json") or f.startswith("_") or f[:-5] not in rows:
            continue
        site = f[:-5]
        try:
            G = render.ctx(site, rows[site], json.load(open(os.path.join(ROOT, "cache", f))), now)
        except render.CriticalFail:
            continue
        n += 1
        if base is None and G["p"] is not None and G["srow"]:
            base = G
        c = render.b3.conditions(G, None)
        h = render.hero(G, None)
        # 1. direction
        m = re.search(r'<div class="tile trend (rising|falling|steady)">.*?<b>([+-]?\d+)% <small class="word">([\w ]+)</small>', h, re.S)
        if m:
            word, val = m.group(3).lower(), int(m.group(2))
            c6 = c["chg"].get(6)
            if word in ("levelling off", "unsteady"):
                pass  # direction words that say the last hour differs from the last 6 h; nothing to contradict
            elif word == "rising" and val < 0 or word == "falling" and val > 0:
                fail(site, "trend word %s contradicts headline %+d%%" % (word, val))
            if c6 is not None and word in ("rising", "falling", "steady") and (word == "rising" and c6 <= 1 or word == "falling" and c6 >= -1 or word == "steady" and abs(c6) > 1):
                fail(site, "trend word %s disagrees with the last 6 h (%+.1f%%)" % (word, c6))
        # 3. silence
        if not G["has_forecast"] and 'class="tile fcst none"' not in h:
            fail(site, "no NWS river forecast but the page does not say so")
        nwl = (G["rec"].get("nwps") or {}).get("lid")
        if nwl and "Not linked" in h:
            fail(site, "page says no NWS point is linked but the data has point %s" % nwl)
        if not nwl and "Not issued" in h and "River forecast" in h:
            fail(site, "page says a point exists but the data has none")
        gaps = (re.search(r'<p class="gaps">Not available[^<]*', h) or [""])[0] if re.search(r'<p class="gaps">Not available', h) else ""
        if not c["wt"] and "water temperature" not in gaps:
            fail(site, "no water temperature and the page does not say so")
        if not (G["rec"].get("nwps") or {}).get("categories") and "flood stages" not in gaps:
            fail(site, "no NWS flood stages and the page does not say so")
        if not c["rain"] and "rain estimate" not in gaps:
            fail(site, "no rain estimate and the page does not say so")
        if c["wt"] and c["wt"]["f"] < -40:
            fail(site, "impossible water temperature %.0f F shown" % c["wt"]["f"])
        if c["fc"] and c["fc"]["cur"] is not None and c["fc"]["cur"] > c["fc"]["v"] + 0.1 and "already above this forecast" not in h:
            fail(site, "forecast high %.1f below the latest stage %.2f without saying so" % (c["fc"]["v"], c["fc"]["cur"]))
        al = c["alerts"]
        if al is not None:
            if al["n"] and ('class="abanner"' not in h or "NWS alerts</span>" in h):
                fail(site, "active alert: banner missing or empty-alert tile still shown")
            if not al["n"] and "No alerts active here" not in h:
                fail(site, "no alert: the tile does not say so")
    if n < 5:
        fail("setup", "only %d gauges rendered" % n)

    # 2. bands
    if base is None:
        fail("setup", "no gauge with statistics to test the bands")
    else:
        want = {-1: "Very low", 3: "Below normal", 10: "Below normal", 24: "Below normal", 25: "Normal range", 40: "Normal range", 49.9: "Normal range", 50: "Normal range", 60: "Normal range",
                75: "Normal range", 76: "Above normal", 94: "Above normal", 99: "Above normal", 101: "Very high"}
        for p, w in want.items():
            G2 = copy.deepcopy(base)
            G2["p"] = p
            h = render.hero(G2, None)
            m = re.search(r'<span>Compared with past years</span><b>([^<]+)</b><small class="nt">([^<]+)</small>', h)
            if not m:
                fail("band %s" % p, "comparison tile not found")
                continue
            word, sent = m.group(1), m.group(2)
            if word != w:
                fail("band %s" % p, "word %r, expected %r" % (word, w))
            lower = p == -1 or p < 50
            if lower and not sent.startswith("Lower than") or (not lower) and not sent.startswith("Higher than"):
                fail("band %s" % p, "sentence points the wrong way: %r" % sent)
            k = re.search(r"than (\d+)%", sent)
            if k and not (50 <= int(k.group(1)) <= 100) and "95% or more" not in sent:
                fail("band %s" % p, "share %s%% is not in 50..100: %r" % (k.group(1), sent))

    # 4 and 5. rendered pages (dist_next)
    d = os.path.join(ROOT, "dist_next")
    for root, _, fs in os.walk(d):
        for f in fs:
            if f != "index.html":
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, d).replace("\\", "/")
            h = open(p, encoding="utf-8").read()
            for m in re.finditer(r'<li class="now"><i class="lad-sw"></i>([^<]*)<b>', h):
                t = m.group(1)
                if t.startswith("Now"):
                    fail(rel, "stage marker says Now: %r" % t)
                elif not re.search(r"\d{1,2}:\d{2}\s?[AP]M", t):
                    fail(rel, "stage marker has no time: %r" % t)
            if re.search(r'<h2 class="secth">[^<]*</h2>\s*(<h2|<details|</div>)', h):
                fail(rel, "a section heading has nothing under it")
            if rel == "index.html" or rel.startswith("rivers/"):  # home and state pages: plain words in tables, cards and tags; Source lines and the glossary may use the technical terms
                vis = re.sub(r"<script.*?</script>|<meta[^>]*>|<p class=\"src\">.*?</p>", " ", h, flags=re.S)
                for pat in (r"\d+(?:st|nd|rd|th)", r"above 95th", r"below 5th", r"percentile"):
                    mm = re.search(pat, re.sub(r"<[^>]+>", " ", vis) if pat != r"percentile" else vis)
                    if mm:
                        fail(rel, "jargon %r near %r" % (pat, re.sub(r"\s+", " ", (re.sub(r"<[^>]+>", " ", vis) if pat != r"percentile" else vis)[max(0, mm.start() - 40):mm.end() + 20])))
    print("truth tests: %d gauges, %d failures" % (n, len(bad)))
    for b in bad[:30]:
        print("  FAIL", b)
    return 1 if bad else 0


sys.exit(main())
