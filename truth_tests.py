"""Truth gates: the contradictions and silences a reader should never meet. Each one comes from a defect a fresh-eyes reviewer found (docs/research/FRESH-REVIEW-6.md).
Usage: python -I truth_tests.py     (run by tests.py after a build; needs dist_next)
 1. Direction: the trend tile's word agrees with the sign of its headline and with the last 6 h of flow, on every gauge.
 2. Bands: for every comparison band (very low .. very high) the word, the sentence ("Lower than" below the middle, "Higher than" above) and the numbers agree.
 3. Silence: a gauge with no NWS river forecast says so; with an active alert there is a banner and no empty-alert tile; without one the tile says so.
 4. Time: a marker called "Now" never appears; the stage marker carries the time of the reading.
 5. Plain words on home and state pages (no ordinals like 91st or "above 95th" in tables).
19. Plausible numbers: no sentinel, negative non-tidal flow or impossible temperature in the series a page uses; a flat 72 h flow is printed as a note.
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
        # 21. the one-line answer says what the tiles say: same trend chip, same comparison word, same alert state
        ans = re.search(r'<p class="answer"[^>]*>(.*?)</p>', h, re.S)
        if not ans:
            fail(site, "no one-line answer above the tiles")
        else:
            spans = re.findall(r"<span[^>]*>(.*?)</span>", ans.group(1))
            chip = re.search(r'<small class="dirchip">(.*?)</small>', h, re.S)
            if len(spans) != 3:
                fail(site, "answer strip does not hold three statements: %r" % spans)
            else:
                if chip and spans[0] != chip.group(1):
                    fail(site, "answer strip trend %r differs from the trend chip %r" % (spans[0], chip.group(1)))
                nw = re.search(r'<div class="tile norm[^"]*">.*?<b>(.*?)</b>', h, re.S)
                if nw and G["p"] is not None and not spans[1].startswith(re.sub(r"<[^>]+>", "", nw.group(1)) + " for "):
                    fail(site, "answer strip comparison %r differs from the comparison tile %r" % (spans[1], nw.group(1)))
                if G["p"] is None and "No past-years" not in spans[1]:
                    fail(site, "no percentile but the answer strip still states a comparison: %r" % spans[1])
                if c["alerts"] is not None and c["alerts"]["n"] and "active NWS alert" not in spans[2]:
                    fail(site, "active alert not stated in the answer strip: %r" % spans[2])
                if c["alerts"] is not None and not c["alerts"]["n"] and "active NWS alert" in spans[2] and "No active" not in spans[2]:
                    fail(site, "no alert but the strip claims one: %r" % spans[2])
                if c["alerts"] is None and "unknown" not in spans[2]:
                    fail(site, "alert source unknown but the strip does not say so: %r" % spans[2])
        # 22. a forecast flow "by the NWS rating" belongs to the NWS point's own rating: never shown at a tidal reach or when the point is another place (Hudson at Green Island showed 2,170 cfs against a measured 6,060)
        if "by the NWS rating" in h and (G["osc"] or render.nws_point_note(G)):
            fail(site, "forecast cfs by the NWS rating shown at a tidal gauge or at a forecast point in another place")
        # 19. plausible numbers: no sentinel or physically impossible reading in the series the page uses (a source's -999999, a negative flow outside a tidal reach, a 400 degree water temperature)
        vals = [x[1] for x in G["fl"]]
        if any(v <= -900 or v >= 1e7 for v in vals):
            fail(site, "flow series holds a sentinel or impossible value (%s)" % [v for v in vals if v <= -900 or v >= 1e7][:2])
        if G["lv"] < 0 and not G["osc"]:
            fail(site, "latest flow is negative (%s cfs) at a gauge that is not tidal or oscillating" % G["lv"])
        if G["sg"] and any(x[1] <= -900 for x in G["sg"]):
            fail(site, "gage height series holds a sentinel value")
        if c.get("wt") and not -2 <= (c["wt"]["f"] - 32) / 1.8 <= 42:
            fail(site, "water temperature %s F is outside -2 to 42 C" % c["wt"]["f"])
        if c.get("air") and not -60 <= c["air"]["f"] <= 130:
            fail(site, "air temperature %s F is outside -60 to 130 F" % c["air"]["f"])
        d1 = G["lt"] - datetime.timedelta(hours=72)
        w72 = [x[1] for x in G["fl"] if x[0] >= d1]
        if len(w72) >= 200 and len(set(w72)) == 1 and w72[0] > 0:
            print("  note: %s flow is identical in all %d readings of the last 72 h (stuck sensor or a fixed release?)" % (site, len(w72)))
        # 1. direction
        m = re.search(r'<div class="tile trend (rising|falling|steady)">.*?<b>([+-]?\d+(?:\.\d+)?)% <small class="word">([\w ]+)</small>', h, re.S)
        if m:
            word, val = m.group(3).lower(), float(m.group(2))
            c6 = c["chg"].get(6)
            if word in ("levelling off", "unsteady", "unclear"):
                pass  # direction words that say the last hour differs from the last 6 h; nothing to contradict
            elif word == "rising" and val < 0 or word == "falling" and val > 0:
                fail(site, "trend word %s contradicts headline %+d%%" % (word, val))
            if c6 is not None and word in ("rising", "falling", "steady") and (word == "rising" and c6 <= 1 or word == "falling" and c6 >= -1 or word == "steady" and abs(c6) > 1):
                fail(site, "trend word %s disagrees with the last 6 h (%+.1f%%)" % (word, c6))
        # 6. storms: the lightning line says thunderstorms exactly when the NWS hourly forecast for the next 24 h does
        sl = render.storm_line(G)
        if sl:
            hr24 = [q for q in ((G["rec"].get("nws") or {}).get("hourly") or []) if render.parse_t(q["startTime"]) > G["now"] - datetime.timedelta(hours=1)][:24]
            if any("thunder" in (q.get("shortForecast") or "").lower() for q in hr24) != ("Thunderstorms in the forecast" in sl):
                fail(site, "storm line disagrees with the hourly forecast: %s" % sl[:90])
        # 7. units: forecast stage and flow are told apart by their units, never by column position
        fcd = (G["rec"].get("nwps") or {}).get("forecast") or {}
        if (fcd.get("primary_units") or "").lower() == "kcfs":
            for q, (tt, st_, fl_) in zip(fcd.get("points") or [], render.fc_points(fcd)):
                if isinstance(q.get("secondary"), (int, float)) and q["secondary"] > -900 and (st_ != q["secondary"] or (fl_ is not None and abs(fl_ - q["primary"] * 1000) > 0.5)):
                    fail(site, "forecast units swapped: stage %s flow %s from %s" % (st_, fl_, q))
                    break
        # 8. datum: when NWS and USGS read the gauge on different zero points and a forecast is shown, the page says so
        if render.datum_gap(G) and c["fc"] and "different zero points" not in h:
            fail(site, "NWS and USGS stages differ by more than 0.3 ft but the forecast tile does not say so")
        # 10. noisy flow: when flow swings but does not follow the gage height, the headline must not give a percent direction
        if render.flow_jitter(G) and re.search(r'\d+% <small class="word">(Rising|Falling)', h):
            fail(site, "flow does not follow gage height (lock, tide or backwater) but the headline still gives a flow direction")
        # 11. forecast out of step with the latest reading: the forecast tile says so
        if c["fc"] and c["fc"].get("offset") and "out of step" not in h:
            fail(site, "forecast differs from the latest reading (%s) but the tile does not say so" % (c["fc"]["offset"],))
        # 12. one number, one source: the headline's 6 h percent equals the 6 h row of the rate table (both come from window_change)
        if m and "Change, last 6 h" in h:
            rb = render.b2.b_rate(G)
            mm = re.search(r"<td[^>]*>6 h</td>.*?\(([+-]?\d+\.\d)%\)", rb["body"], re.S) if rb else None
            if mm and abs(float(mm.group(1)) - val) > 0.051:
                fail(site, "headline %+.1f%% in 6 h but the rate table says %s%%" % (val, mm.group(1)))
            m24 = re.search(r"24 h: ([+-]?\d+\.\d)%", h)
            t24 = re.search(r"<td[^>]*>24 h</td>.*?\(([+-]?\d+\.\d)%\)", rb["body"], re.S) if rb else None
            if m24 and t24 and abs(float(m24.group(1)) - float(t24.group(1))) > 0.051:
                fail(site, "tile says %s%% in 24 h but the rate table says %s%%" % (m24.group(1), t24.group(1)))
        # 13. (dropped 2026-10-20, owner: the upstream-dams note is not useful to the reader)
        # 14. the forecast high on the tile appears in the river forecast table (the table must reach the peak it headlines)
        if c["fc"]:
            fb = render.b_river_forecast(G)
            want_ = ("%.1f ft" % c["fc"]["v"]) if c["fc"]["unit"] == "ft" else ("%s cfs" % render.fmt(c["fc"]["v"]))
            if fb and want_ not in fb["body"]:
                fail(site, "forecast high %s is on the tile but not in the forecast table" % want_)
        # 15. "Flow about 24 h earlier" in the tile equals the "Flow then" of the 24 h row in the rate table (it is a measured average, not a back-computed number)
        m_then = re.search(r"Flow 24 h earlier: ([\d,]+) cfs", h)
        rb2 = render.b2.b_rate(G)
        t_then = re.search(r"<td[^>]*>24 h</td><td[^>]*>([\d,]+) cfs", rb2["body"]) if rb2 else None
        if m_then and t_then and m_then.group(1) != t_then.group(1):
            fail(site, "tile says %s cfs 24 h earlier but the rate table says %s cfs" % (m_then.group(1), t_then.group(1)))
        # 16. when the gauge reads at or above the lowest NWS impact stage (same datum), the page quotes the NWS impact for that level
        imp = [i for i in ((G["rec"].get("nwps") or {}).get("impacts") or []) if isinstance(i.get("stage"), (int, float))]
        if imp and G["sg"] and (G["sg"][-1][2].get("unit_of_measure") or "").lower() in ("ft", "feet"):
            curst = (render.datum_gap(G) or (G["sg"][-1][1],))[0]
            if curst >= min(i["stage"] for i in imp) and "NWS impact statement at" not in h:
                fail(site, "the stage (%.2f ft) is at or above an NWS impact stage but the page does not quote it" % curst)
        # 17. the site gives no advice (Methodology: we do not give advice)
        if re.search(r"(?i)get off the water|you should|we recommend|do not (?:enter|swim|boat)", h):
            fail(site, "advice wording on a data page")
        # 18. alerts: a failed or old alert source never reads as "no alerts" (never fetched: Unknown; answer older than 3 h: says as-of and that it is old)
        G3 = copy.deepcopy(G)
        G3["rec"].setdefault("nws", {})["alerts"] = None
        h3 = render.hero(G3, None)
        if "Unknown" not in h3 or "No alerts active here" in h3:
            fail(site, "alert source never answered but the page does not say Unknown")
        G4 = copy.deepcopy(G)
        G4["rec"].setdefault("nws", {}).update({"alerts": [], "fetched_at": (G["now"] - datetime.timedelta(hours=20)).isoformat()})
        h4 = render.hero(G4, None)
        if "has not answered since" not in h4 or "No alerts active here" in h4:
            fail(site, "alert answer is 20 h old but the page says no alerts as if current")
        # 3. silence
        if not G["has_forecast"] and 'class="tile fcst none"' not in h:
            fail(site, "no NWS river forecast but the page does not say so")
        nwl = (G["rec"].get("nwps") or {}).get("lid")
        if nwl and "Not linked" in h:
            fail(site, "page says no NWS point is linked but the data has point %s" % nwl)
        if not nwl and "Not issued" in h and "River forecast" in h:
            fail(site, "page says a point exists but the data has none")
        # (the "not available for this gauge" list was removed 2026-10-20 by the owner; a missing tile needs no note) but missing flood stages must still be said, inside the stage block: silence there reads as "no flood risk"
        sb_ = render.b2.b_stage_chart(G)
        if sb_ and not (G["rec"].get("nwps") or {}).get("categories") and "publishes no flood stages" not in sb_["body"]:
            fail(site, "no NWS flood stages and the stage block does not say so")
        if c["wt"] and c["wt"]["f"] < -40:
            fail(site, "impossible water temperature %.0f F shown" % c["wt"]["f"])
        if c["fc"] and c["fc"]["cur"] is not None and c["fc"]["cur"] > c["fc"]["v"] + 0.1 and "already above this forecast" not in h and not G["osc"]:  # a tidal reach prints the tidal note instead
            fail(site, "forecast high %.1f below the latest stage %.2f without saying so" % (c["fc"]["v"], c["fc"]["cur"]))
        al = c["alerts"]
        if al is not None:
            if al["n"] and ('class="abanner"' not in h or "NWS alerts</span>" in h):
                fail(site, "active alert: banner missing or empty-alert tile still shown")
            if not al["n"] and (al.get("age_h") is None or al["age_h"] <= 3) and "No active NWS alerts" not in h:  # an old answer says so instead (contract 18); a fresh none is the answer pill
                fail(site, "no alert: the answer pill does not say so")
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
            m = re.search(r'<span>Is this normal for [^<]*\?</span><b>([^<]+)</b><small class="nt">([^<]+)</small>', h)
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
                for pat in (r"\b\d+(?:st|nd|rd|th)\b", r"\babove 95th\b", r"\bbelow 5th\b", r"percentile"):
                    mm = re.search(pat, re.sub(r"<[^>]+>", " ", vis) if pat != r"percentile" else vis)
                    if mm:
                        fail(rel, "jargon %r near %r" % (pat, re.sub(r"\s+", " ", (re.sub(r"<[^>]+>", " ", vis) if pat != r"percentile" else vis)[max(0, mm.start() - 40):mm.end() + 20])))
    # 9. related gauges are symmetric: when page A links B as upstream or downstream, B's page links back to A
    d_ = os.path.join(ROOT, "dist_next")
    links = {}
    for root, _, files in os.walk(os.path.join(d_, "river")):
        if "index.html" in files and root.replace("\\", "/").count("/") and len(os.path.relpath(root, os.path.join(d_, "river")).replace("\\", "/").split("/")) == 2:
            u = "/" + os.path.relpath(root, d_).replace("\\", "/") + "/"
            m = re.search(r'<section class="card blk" id="related_gauges">(.*?)</section>', open(os.path.join(root, "index.html"), encoding="utf-8").read(), re.S)
            links[u] = set(re.findall(r'href="(/river/[^"]+)"', m.group(1))) if m else set()
    for u, ls in links.items():
        for v in ls:
            if v in links and u not in links[v]:
                fail(u, "lists %s as an upstream or downstream gauge but that page does not list it back" % v)
    try:  # 20. the block guard must never fire on the real caches: a hidden block is a bug, not a feature (build.py lists them in status.json)
        be = json.load(open(os.path.join(ROOT, "dist_next", "status.json"), encoding="utf-8")).get("block_errors") or []
    except Exception:
        be = []
    if be:  # one or two gauges: their old pages stay live and the watchdog alerts; three or more (or 10%), the shape of a source changed for everyone: stop the release
        hit = {e.split(":")[0] for e in be}
        if len(hit) >= max(3, n // 10):
            fail("blocks", "the block guard hid blocks on %d gauges, a systemic break: %s" % (len(hit), "; ".join(be[:5])))
        else:
            print("  note: the block guard hid blocks on %d gauge(s), their previous pages stay live: %s" % (len(hit), "; ".join(be[:3])))
    print("truth tests: %d gauges, %d failures" % (n, len(bad)))
    for b in bad[:30]:
        print("  FAIL", b)
    return 1 if bad else 0


sys.exit(main())
