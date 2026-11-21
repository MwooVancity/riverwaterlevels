"""Lake qualifier (agreed with ChatGPT 2026-11-21): which USGS lake and reservoir gauges become ONE page per lake and state.
qualify(candidates) is pure. A candidate is a dict: site, name (USGS station name, "Canyon Lk nr New Braunfels, TX"), state (USPS), lat, lon,
type (site type code, "LK"), params (set of codes reported in the last 30 days), years (years of record on a level series).
Rules: type LK; one of 62614 62615 72020 00062 reported in the last 30 days; >= 1 year of record; a tailwater or canal, lock, afterbay,
forebay, tailrace, pond name is HELD with its reason, never dropped silently. Lake identity = normalised name + state (Pleasant WI and AZ stay apart).
ONE primary gauge per lake and state: more level parameters, then longer record, then lower site id; the others are listed with the reason, no extra URL.
Keyword tiers only ORDER accepted lakes (the first PRACTICE of them ship noindex); they never qualify one.
Dry run prints the grouping report and the held list. --apply appends data/lakes.csv and queues data/waves.csv (status queue, signals lake), never touches an
existing row, so a re-run adds nothing. Network: fetch() only, the USGS Water Data API collect.py uses (BASE). Usage:
  python -I tools/lake_match.py [--state 48] [--apply] | --selftest"""
import csv, datetime, os, re, sys, urllib.error, urllib.request, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lib.pages import slug  # noqa: E402
from lib.common import TAILWATER  # the one shared rule (below a dam, tailrace, tailwater)

BASE = "https://api.waterdata.usgs.gov/ogcapi/v1/collections/"
LEVEL = ("62614", "62615", "72020", "00062")
ELEV = {"62614", "62615", "72020"}  # lake surface elevation; 00062 is a gage height on a local datum
MIN_YEARS = 1.0
PRACTICE = 0  # 2026-11-21 Opus review: a gate on the top-tier rows stranded them (release.py never opens a practice gate); the nightly --every-kind practice run is the practice, so no row is gated here (raise only together with a gate that opens)
STATE_RE = re.compile(r",\s*([A-Z]{2})(?:-[A-Z]{2})*\s*$")
FAR_OK = {tuple(x.strip().split("|")) for x in open(os.path.join(ROOT, "data", "lake-far-ok.txt"), encoding="utf-8")} if os.path.exists(os.path.join(ROOT, "data", "lake-far-ok.txt")) else set()  # 'name|ST' lines (identity key): a lake with far-apart same-name gauges a person has approved as ONE lake (Opus follow-up: head-term lakes such as Okeechobee must not stay held for ever)
NOT_LAKE = re.compile(r"\b(canal|lock|afterbay|forebay|tailrace|pond)\b", re.I)
DROP = {"lake", "lk", "reservoir", "res", "dam"}


def identity(name, state):
    """'Canyon Lk nr New Braunfels, TX' -> ('canyon', 'TX'). Text after nr/near/at is the place, not the lake."""
    n = re.split(r",|\b(?:nr|near|at|ab|above)\b", name.lower())[0]
    words = [w for w in re.findall(r"[a-z0-9]+", n) if w not in DROP]
    return " ".join(words), state.upper()


def lake_name(name):
    """Display name: the part before nr/near/comma, as USGS wrote it, with Lk -> Lake."""
    n = re.split(r",|\s+(?:nr|near|at|ab|above)\s+", name, flags=re.I)[0].strip()  # the same cut words as identity(), so the page name and the identity agree (Opus follow-up)
    if n.isupper():  # USGS often writes 'HARTWELL LAKE NEAR ANDERSON, SC' (Opus review 2026-11-21)
        n = n.title()
    return re.sub(r"\bLk\b", "Lake", re.sub(r"\bRes\b", "Reservoir", n, flags=re.I), flags=re.I)


def place_name(name):
    m = re.search(r"\b(?:nr|near)\s+([^,]+)", name, re.I)
    return m.group(1).strip() if m else ""


def qualify(cands):
    """-> (accepted rows, report). report = {'groups': [...], 'held': [(site, name, reason)]}."""
    held, groups = [], {}
    for c in sorted(cands, key=lambda c: c["site"]):
        why = None
        if c.get("type") != "LK":
            why = "site type %s is not a lake or reservoir" % c.get("type")
        elif not c.get("state"):
            why = "no state in the station name"
        elif c.get("lat") is None or c.get("lon") is None:
            why = "no coordinates"
        elif not identity(c["name"], c["state"])[0]:
            why = "the lake name reduces to nothing"
        elif TAILWATER.search(c["name"]) or NOT_LAKE.search(c["name"]):
            why = "name is a tailwater, canal, lock, afterbay, forebay, tailrace or pond"
        elif not set(c["params"]) & set(LEVEL):
            why = "no lake level parameter (%s) reported in the last 30 days" % "/".join(LEVEL)
        elif (c.get("years") or 0) < MIN_YEARS:
            why = "under %g year of usable history (%.2f)" % (MIN_YEARS, c.get("years") or 0)
        if why:
            held.append((c["site"], c["name"], why))
            continue
        groups.setdefault(identity(c["name"], c["state"]), []).append(c)
    rows, rep = [], []
    for key in list(groups):  # one name in one state with gauges over 10 km apart is two lakes or one long reservoir: never guess (Opus review 2026-11-21), the whole group is held for a person; no second '#2' page
        far = max((km(a, b) for a in groups[key] for b in groups[key]), default=0)
        if far > 10 and key not in FAR_OK:
            held.extend((c["site"], c["name"], "same lake name and state but gauges %.0f km apart (two lakes or one long reservoir): needs a decision" % far) for c in groups.pop(key))
    for key, g in sorted(groups.items()):
        g.sort(key=lambda c: (-len(set(c["params"]) & ELEV), -len(set(c["params"]) & set(LEVEL)), -(c.get("years") or 0), c["site"]))  # measurement quality first (ChatGPT 2026-11-21): a gauge reporting lake ELEVATION (62614, 62615, 72020) outranks one reporting only 00062 gage height; then more level parameters, longer record, lower id (deterministic)
        p = g[0]
        rows.append(dict(p, key=key))
        rep.append({"lake": "%s %s" % key, "gauges": [c["site"] for c in g], "primary": p["site"],
                    "param": "/".join(sorted(set(p["params"]) & set(LEVEL))), "years": round(p.get("years") or 0, 1),
                    "excluded": {c["site"]: "same lake and state; primary has %d level parameters%s, %.1f years, lower id on a tie" % (len(set(p["params"]) & set(LEVEL)), " (an elevation gauge is preferred over 00062)" if set(p["params"]) & ELEV else "", p.get("years") or 0) for c in g[1:]}})
    return rows, {"groups": rep, "held": held}


def km(a, b):
    """Rough distance in km between two gauges (flat-earth, fine under 100 km)."""
    import math
    return math.hypot((a["lon"] - b["lon"]) * math.cos(math.radians(a["lat"])) * 111.0, (a["lat"] - b["lat"]) * 111.0)


def plan(rows, have_sites, have_keys, tiers, have_slugs=()):
    """Rows to append, ordered by keyword tier (then site); skips every site or lake identity already present. The first PRACTICE get gate 'practice'."""
    new = [r for r in rows if r["site"] not in have_sites and r["key"] not in have_keys and slug(lake_name(r["name"])) not in have_slugs]  # a new lake with a live lake's name would move that page's address (Opus review): held back
    new.sort(key=lambda r: (-tiers.get(lake_name(r["name"]).lower() + " water level", 0), r["site"]))
    for i, r in enumerate(new):
        r["gate"] = "practice" if i < PRACTICE else ""
    return new


def fetch(state=None, days=30):
    """The only network code. USGS lake locations (type LK, agency USGS), then their series metadata: params still reporting and the span of the level series."""
    def get(url):  # paced, with the USGS key when the environment has one, and a backoff on HTTP 429 (the laptop was rate-limited after repeated Texas runs, 2026-11-21)
        import time
        h = {"User-Agent": "riverwaterlevels.com lake_match"}
        if os.environ.get("USGS_API_KEY"):
            h["X-Api-Key"] = os.environ["USGS_API_KEY"].strip()
        for wait in (0.3, 30, 90, 180):
            time.sleep(wait)
            try:
                return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=120).read())
            except urllib.error.HTTPError as e:
                if e.code != 429 or wait == 180:
                    raise
    q = "monitoring-locations/items?site_type_code=LK&limit=1000&f=json" + ("&state_code=%s" % state if state else "")
    seen = set()

    def pages(url):  # follow the API's next links (a run without --state used to stop silently at 1000 sites, Opus review 2026-11-21)
        while url:
            d = get(url)
            yield from d["features"]
            seen.add(url)
            url = next((l["href"] for l in d.get("links", []) if l.get("rel") == "next"), None)
            if url in seen:  # a next link that points back would loop for ever; say so, a cut-short feed is never treated as complete
                print("WARNING: the API next link repeated, the lake list may be incomplete: %s" % url)
                break
    locs = [f for f in pages(BASE + q) if f["properties"].get("agency_code") == "USGS"]
    cut = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    out = {}
    for f in locs:
        p = f["properties"]
        m = STATE_RE.search(p["monitoring_location_name"])  # ', AZ-NV' (Lake Mead, Powell) takes the first state
        out[p["monitoring_location_number"]] = {"site": p["monitoring_location_number"], "name": p["monitoring_location_name"], "state": m.group(1) if m else "",
                                                "lat": (f.get("geometry") or {}).get("coordinates", [None, None])[1], "lon": (f.get("geometry") or {}).get("coordinates", [None, None])[0], "type": "LK", "params": set(), "years": 0.0}
    ids = sorted(out)
    for i in range(0, len(ids), 40):
        url = BASE + "time-series-metadata/items?monitoring_location_id=%s&parameter_code=%s&limit=1000&f=json&skipGeometry=true" % (",".join("USGS-" + s for s in ids[i:i + 40]), ",".join(LEVEL))
        for f in pages(url):
            p = f["properties"]
            c = out.get(p["monitoring_location_id"][5:])
            if not c or not p.get("begin") or not p.get("end"):
                continue
            if p["end"][:10] >= cut and p.get("computation_identifier") == "Instantaneous":  # a daily Min/Max/Mean series is not 'still reporting': the page reads instant readings (Opus review)
                c["params"].add(p["parameter_code"])
            b, e = (datetime.datetime.fromisoformat(p[k][:10]) for k in ("begin", "end"))
            c["years"] = max(c["years"], (e - b).days / 365.25)
    return list(out.values())  # a station with no state in its name is held with a reason in qualify(), never dropped silently


def tiers():
    p = os.path.join(ROOT, "data", "keyword-tiers.csv")
    return {r["keyword"]: int(r["tier"] or 0) for r in csv.DictReader(open(p, encoding="utf-8"))} if os.path.exists(p) else {}


def existing():
    lk = list(csv.DictReader(open(os.path.join(ROOT, "data", "lakes.csv"), encoding="utf-8")))
    sites = {r["site"] for r in lk} | {r["site"] for r in csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8"))}
    return lk, sites, {identity(r[f], r["state"]) for r in lk for f in ("lake", "raw_name")}, {slug(r["lake"]) for r in lk}


def urls(new, lk):
    """/lake/<slug>/ as lib/pages.py: a name shared by two lakes gets -<state>-<site> (Clear Lake CA and IA never share an address)."""
    count = {}
    for n in [r["lake"] for r in lk] + [lake_name(r["name"]) for r in new]:
        count[slug(n)] = count.get(slug(n), 0) + 1
    return {r["site"]: "/lake/%s/" % (slug(lake_name(r["name"])) + ("" if count[slug(lake_name(r["name"]))] == 1 else "-%s-%s" % (r["state"].lower(), r["site"]))) for r in new}


def apply(new, lk):
    u = urls(new, lk)
    with open(os.path.join(ROOT, "data", "lakes.csv"), "a", newline="", encoding="utf-8") as f, open(os.path.join(ROOT, "data", "waves.csv"), "a", newline="", encoding="utf-8") as w:
        a, b = csv.writer(f), csv.writer(w)
        for r in new:
            a.writerow([r["site"], r["state"], lake_name(r["name"]), place_name(r["name"]), r["lat"], r["lon"], r["name"], "", "", "usgs lake_match"])
            b.writerow(["queue", "", r["site"], lake_name(r["name"]), place_name(r["name"]), r["state"], "0", "", "", "0", "lake", r["gate"], "", "human", u[r["site"]]])


def show(rows, rep, new):
    for g in rep["groups"]:
        print("LAKE %-34s gauges %s primary %s %s %.1f y%s" % (g["lake"], ",".join(g["gauges"]), g["primary"], g["param"], g["years"], "".join("\n     excluded %s: %s" % kv for kv in g["excluded"].items())))
    for s, n, why in rep["held"]:
        print("HELD %s %-40s %s" % (s, n, why))
    print("accepted %d lakes, %d held (%d of them same-name gauges far apart: read these first), %d new to queue (first %d practice)" % (len(rows), len(rep["held"]), sum(1 for _, _, w in rep["held"] if "apart" in w), len(new), PRACTICE))


def selftest():
    def c(site, name, params=("62614",), years=5.0, type_="LK"):
        return {"site": site, "name": name, "state": name[-2:], "lat": 1.0, "lon": 2.0, "type": type_, "params": set(params), "years": years}
    cands = [c("2", "Pleasant Lk nr Foo, WI"), c("1", "Pleasant Lake near Bar, WI", ("62614", "00062")), c("3", "Pleasant Lk nr Baz, AZ"),
             c("4", "Hartwell Lk Tailrace nr Hartwell, GA"), c("5", "Savannah R below Hartwell Dam, GA", years=9), c("6", "Level Only Lk nr X, TX", ("00065",)),
             c("7", "Short Lk nr Y, TX", years=0.33), c("8", "Old Res nr Z, TX", ("62615",), 30), c("9", "Gauge on River nr Q, TX", type_="ST")]
    rows, rep = qualify(cands)
    got = {r["key"]: r["site"] for r in rows}
    assert got == {("pleasant", "WI"): "1", ("pleasant", "AZ"): "3", ("old", "TX"): "8"}, got  # two gauges on one lake = one row, primary has more parameters; WI and AZ apart
    assert next(g for g in rep["groups"] if g["lake"] == "pleasant WI")["excluded"].keys() == {"2"}  # the other gauge is reported with its reason
    held = {s: w for s, _, w in rep["held"]}
    assert set(held) == {"4", "5", "6", "7", "9"}, held  # tailrace and 'Savannah R below Hartwell Dam' held, 00065-only rejected, 4 months rejected, river type rejected
    assert "tailwater" in held["5"] and "last 30 days" in held["6"] and "history" in held["7"]
    two = qualify([c("20", "Gage Lk nr A, OK", ("00062",), 30), c("30", "Gage Lake near B, OK", ("62614",), 2)])[0]  # a lake ELEVATION gauge beats a longer 00062 gage-height record (ChatGPT 2026-11-21)
    assert [r["site"] for r in two] == ["30"], two
    assert qualify(cands) == (rows, rep)  # deterministic
    for _ in range(2):  # lowest id wins a full tie
        r2, _r = qualify([c("20", "Tie Lk, OH"), c("10", "Tie Lk, OH")])
        assert r2[0]["site"] == "10"
    t = {"old reservoir water level": 500}
    new = plan(rows, set(), set(), t)
    assert new[0]["site"] == "8" and [r["gate"] for r in new] == [""] * 3  # tier orders; no row is gated (PRACTICE = 0)
    assert lake_name("HARTWELL LAKE NEAR ANDERSON, SC") == "Hartwell Lake" and lake_name("CANYON LK NR NEW BRAUNFELS, TX") == "Canyon Lake"  # upper-case USGS names (Opus review)
    far, farrep = qualify([dict(c("40", "Silver Lk nr Alpha, MI"), lat=45.0, lon=-85.0), dict(c("41", "Silver Lk nr Beta, MI"), lat=46.0, lon=-86.0), dict(c("42", "Silver Lk nr Alpha2, MI"), lat=45.01, lon=-85.0)])
    assert far == [] and {s for s, _, _ in farrep["held"]} == {"40", "41", "42"} and "apart" in farrep["held"][0][2], (far, farrep)  # one name 150 km apart: the whole group is held, never a '#2' page
    oahe, _o = qualify([dict(c("60", "Lake Oahe nr Pierre, SD"), lat=44.4, lon=-100.4), dict(c("61", "Lake Oahe at Mobridge, SD"), lat=45.5, lon=-100.4)])
    assert oahe == [], oahe  # a long reservoir is held too, with the reason, not split into two pages
    assert STATE_RE.search("Lake Mead at Hoover Dam, AZ-NV").group(1) == "AZ" and STATE_RE.search("Canyon Lk nr New Braunfels, TX").group(1) == "TX" and not STATE_RE.search("SHASTA DAM (USBR)")  # state from the name
    assert "no coordinates" in {s: w for s, _, w in qualify([dict(c("70", "X Lk nr Y, MN"), lat=None)])[1]["held"]}["70"]  # a station with no coordinates is held with a reason
    FAR_OK.add(("okee", "FL"))  # an approved far group becomes ONE lake through the normal primary-gauge path
    okee = qualify([dict(c("80", "Okee Lk nr A, FL"), lat=26.9, lon=-80.8), dict(c("81", "Okee Lk nr B, FL"), lat=27.1, lon=-81.0)])[0]
    FAR_OK.discard(("okee", "FL"))
    assert [r["site"] for r in okee] == ["80"], okee
    near = qualify([dict(c("42", "Silver Lk nr Alpha, MI"), lat=45.0, lon=-85.0), dict(c("43", "Silver Lake near Alpha, MI"), lat=45.01, lon=-85.0)])[0]
    assert [r["site"] for r in near] == ["42"], near  # a second gauge 1 km away is the same lake: one page
    h = {s: w for s, _, w in qualify([c("50", "LK NR Y, MN"), dict(c("51", "Nameless Lk"), state="")])[1]["held"]}
    assert "reduces to nothing" in h["50"] and "no state" in h["51"], h  # nothing silently dropped
    assert plan(rows, set(), set(), t, {"old-reservoir"}) == [r for r in plan(rows, set(), set(), t) if r["site"] != "8"]  # a new lake whose name matches a live lake is held back
    assert plan(rows, {r["site"] for r in rows}, set(), t) == []  # re-run adds nothing
    assert plan(rows, set(), {r["key"] for r in rows}, t) == []  # a lake that already has a page is never replaced by another gauge
    assert urls(new, [{"lake": "Pleasant Lake"}])["1"].startswith("/lake/pleasant-lake-wi-1")  # shared name never shares an address
    print("lake_match selftest OK")


def main():
    if "--selftest" in sys.argv:
        return selftest()
    st = sys.argv[sys.argv.index("--state") + 1] if "--state" in sys.argv else None
    lk, sites, keys, slugs = existing()
    rows, rep = qualify(fetch(st))
    new = plan(rows, sites, keys, tiers(), slugs)
    for r in rows:  # a lake whose name matches a live lake in another state is not queued (it would move the live page's address); say so, never drop silently
        if r["site"] not in sites and r["key"] not in keys and slug(lake_name(r["name"])) in slugs:
            print("HELD %s %-40s same lake name as a live lake in another state: needs a fixed live address first" % (r["site"], r["name"]))
    show(rows, rep, new)
    if "--apply" in sys.argv:
        apply(new, lk)
        print("appended %d rows" % len(new))


if __name__ == "__main__":
    main()
