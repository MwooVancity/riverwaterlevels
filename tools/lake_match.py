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
import csv, datetime, os, re, sys, urllib.request, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lib.pages import slug  # noqa: E402
from lib.common import TAILWATER  # the one shared rule (below a dam, tailrace, tailwater)

BASE = "https://api.waterdata.usgs.gov/ogcapi/v1/collections/"
LEVEL = ("62614", "62615", "72020", "00062")
MIN_YEARS = 1.0
PRACTICE = 5
NOT_LAKE = re.compile(r"\b(canal|lock|afterbay|forebay|tailrace|pond)\b", re.I)
DROP = {"lake", "lk", "reservoir", "res", "dam"}


def identity(name, state):
    """'Canyon Lk nr New Braunfels, TX' -> ('canyon', 'TX'). Text after nr/near/at is the place, not the lake."""
    n = re.split(r",|\b(?:nr|near|at|ab|above)\b", name.lower())[0]
    words = [w for w in re.findall(r"[a-z0-9]+", n) if w not in DROP]
    return " ".join(words), state.upper()


def lake_name(name):
    """Display name: the part before nr/near/comma, as USGS wrote it, with Lk -> Lake."""
    n = re.split(r",|\s+(?:nr|near)\s+", name)[0].strip()
    return re.sub(r"\bLk\b", "Lake", re.sub(r"\bRes\b", "Reservoir", n))


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
    for key, g in sorted(groups.items()):
        g.sort(key=lambda c: (-len(set(c["params"]) & set(LEVEL)), -(c.get("years") or 0), c["site"]))  # ponytail: deterministic, no scoring
        p = g[0]
        rows.append(dict(p, key=key))
        rep.append({"lake": "%s %s" % key, "gauges": [c["site"] for c in g], "primary": p["site"],
                    "param": "/".join(sorted(set(p["params"]) & set(LEVEL))), "years": round(p.get("years") or 0, 1),
                    "excluded": {c["site"]: "same lake and state; primary has %d level parameters, %.1f years, lower id on a tie" % (len(set(p["params"]) & set(LEVEL)), p.get("years") or 0) for c in g[1:]}})
    return rows, {"groups": rep, "held": held}


def plan(rows, have_sites, have_keys, tiers):
    """Rows to append, ordered by keyword tier (then site); skips every site or lake identity already present. The first PRACTICE get gate 'practice'."""
    new = [r for r in rows if r["site"] not in have_sites and r["key"] not in have_keys]
    new.sort(key=lambda r: (-tiers.get(lake_name(r["name"]).lower() + " water level", 0), r["site"]))
    for i, r in enumerate(new):
        r["gate"] = "practice" if i < PRACTICE else ""
    return new


def fetch(state=None, days=30):
    """The only network code. USGS lake locations (type LK, agency USGS), then their series metadata: params still reporting and the span of the level series."""
    def get(url):
        return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "riverwaterlevels.com lake_match"}), timeout=120).read())
    q = "monitoring-locations/items?site_type_code=LK&limit=1000&f=json" + ("&state_code=%s" % state if state else "")
    locs = [f for f in get(BASE + q)["features"] if f["properties"].get("agency_code") == "USGS"]
    cut = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    out = {}
    for f in locs:
        p = f["properties"]
        m = re.search(r",\s*([A-Z]{2})\s*$", p["monitoring_location_name"])
        out[p["monitoring_location_number"]] = {"site": p["monitoring_location_number"], "name": p["monitoring_location_name"], "state": m.group(1) if m else "",
                                                "lat": f["geometry"]["coordinates"][1], "lon": f["geometry"]["coordinates"][0], "type": "LK", "params": set(), "years": 0.0}
    ids = sorted(out)
    for i in range(0, len(ids), 40):
        url = BASE + "time-series-metadata/items?monitoring_location_id=%s&parameter_code=%s&limit=1000&f=json&skipGeometry=true" % (",".join("USGS-" + s for s in ids[i:i + 40]), ",".join(LEVEL))
        for f in get(url)["features"]:
            p = f["properties"]
            c = out.get(p["monitoring_location_id"][5:])
            if not c or not p.get("begin") or not p.get("end"):
                continue
            if p["end"][:10] >= cut:
                c["params"].add(p["parameter_code"])
            b, e = (datetime.datetime.fromisoformat(p[k][:10]) for k in ("begin", "end"))
            c["years"] = max(c["years"], (e - b).days / 365.25)
    return [c for c in out.values() if c["state"]]


def tiers():
    p = os.path.join(ROOT, "data", "keyword-tiers.csv")
    return {r["keyword"]: int(r["tier"] or 0) for r in csv.DictReader(open(p, encoding="utf-8"))} if os.path.exists(p) else {}


def existing():
    lk = list(csv.DictReader(open(os.path.join(ROOT, "data", "lakes.csv"), encoding="utf-8")))
    sites = {r["site"] for r in lk} | {r["site"] for r in csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8"))}
    return lk, sites, {identity(r["lake"], r["state"]) for r in lk}


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
    print("accepted %d lakes, %d held, %d new to queue (first %d practice)" % (len(rows), len(rep["held"]), len(new), PRACTICE))


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
    assert qualify(cands) == (rows, rep)  # deterministic
    for _ in range(2):  # lowest id wins a full tie
        r2, _r = qualify([c("20", "Tie Lk, OH"), c("10", "Tie Lk, OH")])
        assert r2[0]["site"] == "10"
    t = {"old reservoir water level": 500}
    new = plan(rows, set(), set(), t)
    assert new[0]["site"] == "8" and [r["gate"] for r in new] == ["practice"] * 3  # tier orders, first 5 practice
    assert plan(rows, {r["site"] for r in rows}, set(), t) == []  # re-run adds nothing
    assert plan(rows, set(), {r["key"] for r in rows}, t) == []  # a lake that already has a page is never replaced by another gauge
    assert urls(new, [{"lake": "Pleasant Lake"}])["1"].startswith("/lake/pleasant-lake-wi-1")  # shared name never shares an address
    print("lake_match selftest OK")


def main():
    if "--selftest" in sys.argv:
        return selftest()
    st = sys.argv[sys.argv.index("--state") + 1] if "--state" in sys.argv else None
    lk, sites, keys = existing()
    rows, rep = qualify(fetch(st))
    new = plan(rows, sites, keys, tiers())
    show(rows, rep, new)
    if "--apply" in sys.argv:
        apply(new, lk)
        print("appended %d rows" % len(new))


if __name__ == "__main__":
    main()
