"""Match world queue rows to a real agency station, strictly, so the release can publish them. Run: python -I tools/world_match.py
Writes data/world-ready.csv (tier, keyword, feed, station, title, page). Canada: one bulk ECCC station list call. England: ea_pick below, and only while lib/world.py room("ea") allows (a proof is on file and not every listed English gauge was held thin).
Rules (a wrong gauge is the worst defect, so anything unsure is skipped and printed with its reason):
- the station name must be "<RIVER> AT|NEAR|ABOVE|BELOW ..." (canals, drains and diversions never match);
- a bracketed qualifier must be a province, or a word found in the station name; with no qualifier the stations must sit in one province;
- a keyword a US gauge also targets is skipped, unless the row itself is Canadian: its bracket names a province or Canada, or Canada is its only country
  (owner 2026-11-03); the page then names the Canadian station and its province, which is true whoever searched;
- of what is left, the largest drainage area: the main stem, one gauge per river.
ponytail: largest drainage can pick a remote mouth gauge over a city one (Bow River near the mouth, not Calgary); add a per-river pick list if readers ask."""
import csv, datetime, json, os, re, sys, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROV = {"alberta": "AB", "british columbia": "BC", "manitoba": "MB", "new brunswick": "NB", "newfoundland": "NL", "labrador": "NL", "nova scotia": "NS", "ontario": "ON",
        "prince edward island": "PE", "quebec": "QC", "saskatchewan": "SK", "yukon": "YT", "northwest territories": "NT", "nunavut": "NU"}
URL = "https://api.weather.gc.ca/collections/hydrometric-stations/items?f=json&limit=10000&skipGeometry=true&STATUS_EN=Active&REAL_TIME=1&properties=STATION_NUMBER,STATION_NAME,PROV_TERR_STATE_LOC,DRAINAGE_AREA_GROSS"


def pick(river, stations):
    """(station, None) or (None, reason)."""
    m = re.match(r"^(.*?)\s*(?:\((.*)\))?$", river.strip())
    base, qual = m.group(1).upper().replace("ST. ", "ST. "), (m.group(2) or "").lower()
    hits = [s for s in stations if re.match(r"^%s (AT|NEAR|ABOVE|BELOW) " % re.escape(base), s["STATION_NAME"])]
    if qual and qual != "canada":
        if qual in PROV:
            hits = [s for s in hits if s["PROV_TERR_STATE_LOC"] == PROV[qual]]
        else:
            hits = [s for s in hits if qual.upper() in s["STATION_NAME"]]
    hits = [s for s in hits if s["PROV_TERR_STATE_LOC"] in PROV.values()]  # the station must sit in a province or territory (the list also carries border stations)
    if not qual or qual == "canada":
        if len({s["PROV_TERR_STATE_LOC"] for s in hits}) > 1:
            return None, "same name in %d provinces" % len({s["PROV_TERR_STATE_LOC"] for s in hits})
    if not hits:
        return None, "no real-time station named for it"
    return max(hits, key=lambda s: s.get("DRAINAGE_AREA_GROSS") or 0), None


def canadian(r):
    """The queue row is about a Canadian river by its own words: a bracket that names a province, territory or Canada, or Canada as its only country."""
    q = re.search(r"\(([^()]*)\)\s*$", r["river"])
    return (q.group(1).strip().lower() in PROV or q.group(1).strip().lower() == "canada") if q else r["country"] == "CA"


def title(name):
    return re.sub(r" (At|Near|Above|Below) ", lambda m: m.group(0).lower(), name.title())


def covered(slug="canada", country="Canada"):
    """River names already on a country page, from the hub cache, else the live gauge list: one gauge per river."""
    try:
        names = [r.get("title") or "" for r in json.load(open(os.path.join(ROOT, "cache", "_river-%s.json" % slug), encoding="utf-8"))["rows"]]
    except (OSError, ValueError, KeyError):
        names = [r[0] for r in json.load(urllib.request.urlopen(urllib.request.Request("https://riverwaterlevels.com/gauges.json", headers={"User-Agent": "riverwaterlevels.com"}), timeout=30)) if country in r[4]]
    return {re.split(r" (?:at|near|above|below) ", n, maxsplit=1)[0].upper() for n in names}


EA = "https://environment.data.gov.uk/flood-monitoring/"
PICK = {"River Trent": "4009", "River Thames": "3400TH", "River Severn": "2077"}  # Kingston (above Teddington Lock) and Shrewsbury Welsh Bridge; the rule picked Hannington Bridge and tidal Sharpness (2026-11-03)  # ponytail: Colwick, the Nottingham gauge, the largest city on the Trent, where the rule below would pick a smaller town. One hand line per famous river; each still passes every test.


def ea_get(path, timeout=60):
    return json.load(urllib.request.urlopen(urllib.request.Request(EA + path, headers={"User-Agent": "riverwaterlevels.com"}), timeout=timeout))


def ea_test(sid):
    """(True, None) when the station's live main stage is in metres above its datum, read in the last 24 h, with 2 days of readings that do not move with the tide; else (False, reason). Two calls."""
    import collect
    from lib import wx
    lv, _, tide = collect.ea_measures(ea_get("id/stations/" + urllib.parse.quote(sid))["items"])
    if tide or not lv:
        return False, "tidal" if tide else "no live river stage in metres"
    since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=8)).strftime("%Y-%m-%dT%H:%M:%SZ")
    pts = [[i["dateTime"], i["value"]] for i in ea_get("id/measures/%s/readings?_sorted&_limit=2000&since=%s" % (urllib.parse.quote(lv), since))["items"] if isinstance(i.get("value"), (int, float))][::-1]
    if len(pts) < 192 or (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(pts[-1][0].replace("Z", "+00:00"))).total_seconds() > 86400:
        return False, "too few recent readings to rule out a tide"
    t = wx.tidal(pts)
    return (False, "moves with the tide" if t else "too few readings to rule out a tide") if t is not False else (True, None)


def ea_pick(river, stations, flows, test):
    """(station, None) or (None, reason) for an English river name, strictly: the agency's riverName exactly, active, a main stage in metres above the stage datum, a normal range, no tidal measure,
    and a live test (ea_test) that rules out a tide. Order: PICK, then the most flow in m³/s now (the main stem, as Canada takes the largest drainage), then the widest normal range.
    ponytail: flow and range stand in for 'the gauge readers mean'; a river readers know by a town gauge gets a PICK line. At most 3 stations are tested, about 6 calls a river."""
    if "(" in river or "," in river:
        return None, "a qualified name, not an agency river name"
    def ok(s):
        ms = s.get("measures") or []
        ms = ms if isinstance(ms, list) else [ms]
        sc = s.get("stageScale") if isinstance(s.get("stageScale"), dict) else {}
        return (s.get("riverName") == river and str(s.get("status", "")).endswith("statusActive") and not any(m.get("qualifier") == "Tidal Level" for m in ms)
                and any(m.get("qualifier") == "Stage" and m.get("unitName") == "mASD" for m in ms) and isinstance(sc.get("typicalRangeLow"), (int, float)) and isinstance(sc.get("typicalRangeHigh"), (int, float)))
    hits = [s for s in stations if ok(s)]
    if not hits:
        return None, "no active non-tidal agency station named for it"
    flow = lambda s: max([flows.get(m.get("notation"), 0) for m in (s["measures"] if isinstance(s["measures"], list) else [s["measures"]]) if m.get("parameter") == "flow" and m.get("unitName") == "m3/s"] or [0])
    hits.sort(key=lambda s: (s["notation"] != PICK.get(river), -flow(s), -(s["stageScale"]["typicalRangeHigh"] - s["stageScale"]["typicalRangeLow"])))
    why = []
    for s in hits[:3]:
        good, reason = test(s["notation"])
        if good:
            return s, None
        why.append("%s %s" % (s["notation"], reason))
    return None, "no station passed: " + "; ".join(why)


def england(rows, pages, seen, stations_of=None, flows=None, test=ea_test, rivers=None, thin="live"):
    """Ready rows for England from queue rows whose country includes GB, or none at all while the feed lacks a proof, every listed English gauge was held thin, or the live status is unread. Prints every skip."""
    sys.path.insert(0, ROOT)
    from lib import world
    room = world.room("ea", pages, world.live_thin() if thin == "live" else thin)
    if not room:
        print("England: none added, %s" % ("; ".join(world.proof_faults(["ea"], world.proved(pages))) or "every listed English gauge is held as a thin page, or the live status is unread"))
        return [], []
    out, skip = [], []
    try:
        rivers = covered("england", "England") if rivers is None else rivers
    except Exception as e:  # no list of what England already shows: add nothing, never a second gauge on a river
        return [], [("England", "cannot read the gauges already shown: %s" % str(e)[:60])]
    try:
        flows = flows if flows is not None else {i["measure"].rsplit("/", 1)[-1]: i["value"] for i in ea_get("data/readings?latest&parameter=flow", 90)["items"] if isinstance(i.get("value"), (int, float))}
    except Exception as e:  # the latest flows only order the candidates
        print("England: latest flows unavailable, ordering by range:", str(e)[:80])
        flows = {}
    for r in rows:
        if len(out) >= room:
            break
        if r["river"].upper() in rivers:
            continue
        if r["shared"] or "US" in r["country"].split("|"):
            skip.append((r["keyword"], "a US gauge shares this keyword" if "US" in r["country"].split("|") else "two British rivers share this name"))
            continue
        try:
            st = stations_of(r["river"]) if stations_of else ea_get("id/stations?riverName=%s&_view=full" % urllib.parse.quote(r["river"]))["items"]
            s, why = ea_pick(r["river"], st, flows, test)
        except Exception as e:
            s, why = None, "agency did not answer: %s" % str(e)[:60]
        if not s:
            skip.append((r["keyword"], why))
            continue
        if s["notation"] in seen:
            continue
        seen.add(s["notation"])
        rivers.add(r["river"].upper())
        out.append({"tier": r["tier"], "keyword": r["keyword"], "feed": "ea", "station": s["notation"], "title": "%s at %s" % (r["river"], re.sub(r"\s+", " ", s.get("label") or "").strip()), "page": "england"})
    return out, skip


def main(stations=None, seen=None):
    seen = covered() if seen is None else seen
    stations = stations or [f["properties"] for f in json.load(urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "riverwaterlevels.com"}), timeout=90))["features"]]
    if len(stations) < 1000:
        sys.exit("station list cut short (%d): nothing written" % len(stations))
    pages = json.load(open(os.path.join(ROOT, "data", "world-pages.json"), encoding="utf-8"))
    have = {n for p in pages for n in p.get("gauge_pages") or []}
    out, skip, gb = [], [], []
    for r in csv.DictReader(open(os.path.join(ROOT, "data", "world-queue.csv"), encoding="utf-8")):
        if r["ready"] != "yes" and r["tier"] != "0" and "GB" in r["country"].split("|"):
            gb.append(r)
        if r["ready"] == "yes" or "CA" not in r["country"].split("|") or r["tier"] == "0":
            continue
        if (r["shared"] or "US" in r["country"].split("|")) and not canadian(r):
            skip.append((r["keyword"], "a US gauge shares this keyword"))
            continue
        s, why = pick(r["river"], stations)
        if not s:
            skip.append((r["keyword"], why))
            continue
        river = re.split(r" (?:AT|NEAR|ABOVE|BELOW) ", s["STATION_NAME"], maxsplit=1)[0]
        if s["STATION_NUMBER"] in have or river in seen:
            continue
        seen.add(river)
        out.append({"tier": r["tier"], "keyword": r["keyword"], "feed": "eccc", "station": s["STATION_NUMBER"], "title": title(s["STATION_NAME"]), "page": "canada"})
    taken = {w["keyword"] for w in out}
    for r in gb:
        if r["keyword"] in taken:
            skip.append((r["keyword"], "matched in Canada too: the searcher's country is unknown"))
    en, why = england([r for r in gb if r["keyword"] not in taken], pages, set(have))
    out, skip = out + en, skip + why
    with open(os.path.join(ROOT, "data", "world-ready.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["tier", "keyword", "feed", "station", "title", "page"])
        w.writeheader()
        w.writerows(out)
    print("ready %d, skipped %d" % (len(out), len(skip)))
    for k, why in skip:
        print("  skipped:", k, "-", why)
    return out


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        st = [{"STATION_NUMBER": a, "STATION_NAME": b, "PROV_TERR_STATE_LOC": c, "DRAINAGE_AREA_GROSS": d} for a, b, c, d in (
            ("1", "BOW RIVER AT BANFF", "AB", 2210), ("2", "BOW RIVER NEAR THE MOUTH", "AB", 25300), ("3", "BOW RIVER IRRIGATION DISTRICT MAIN CANAL AT DROP NO. 3", "AB", 99999),
            ("4", "PEACE RIVER NEAR TAYLOR", "BC", 1), ("5", "PEACE RIVER AT PEACE RIVER", "AB", 2), ("6", "JAMES RIVER NEAR SUNDRE", "AB", 817), ("7", "RED RIVER AT JAMES AVENUE PUMPING STATION", "MB", 9))]
        assert pick("Bow River", st)[0]["STATION_NUMBER"] == "2", "a canal or a smaller gauge won"
        assert pick("Peace River", st)[0] is None, "a name in two provinces was guessed"
        assert pick("James River (Alberta)", st)[0]["STATION_NUMBER"] == "6", "a qualified river missed"
        assert pick("James River (Manitoba)", st)[0] is None, "a station of another river matched by a word in its name"
        assert pick("Salmon River (Langley)", st)[0] is None, "a river with no station matched"
        assert pick("Red River (Canada)", st)[0]["STATION_NUMBER"] == "7" and pick("Red River", st + [{"STATION_NUMBER": "8", "STATION_NAME": "RED RIVER AT EMERSON", "PROV_TERR_STATE_LOC": "ND", "DRAINAGE_AREA_GROSS": 99}])[0]["STATION_NUMBER"] == "7", "a Canada bracket missed, or a station outside the provinces won"
        row_ = lambda river, country="CA": {"river": river, "country": country}
        assert canadian(row_("James River (Alberta)", "CA|US")) and canadian(row_("Ottawa River")) and canadian(row_("Salt River (Canada)", "AU|CA")), "a clearly Canadian row was not seen as Canadian"
        assert not canadian(row_("White River (Jamaica)", "CA|JM")) and not canadian(row_("Bow River", "AU|CA")) and not canadian(row_("Salmon River (Langley)")), "a row that is not clearly Canadian passed"
        sys.path.insert(0, ROOT)
        from lib import world
        stg = {"qualifier": "Stage", "unitName": "mASD", "parameter": "level"}
        en = lambda n, river="River X", ms=(), status="statusActive", flow=None: {"notation": n, "label": n, "riverName": river, "status": "x/" + status, "stageScale": {"typicalRangeLow": 0.1, "typicalRangeHigh": 1.0},
                                                                               "measures": [stg] + list(ms) + ([{"parameter": "flow", "unitName": "m3/s", "notation": n + "-q"}] if flow else [])}
        est = [en("T", ms=[{"qualifier": "Tidal Level", "unitName": "mAOD"}], flow=1), en("B", flow=1), en("C", flow=1), en("D", river="River X Tributary", flow=1), en("E", status="statusSuspended", flow=1)]
        flows = {"T-q": 99, "B-q": 5, "C-q": 9, "D-q": 50, "E-q": 70}
        tried = []
        test = lambda sid: (tried.append(sid), (False, "moves with the tide") if sid == "C" else (True, None))[1]
        assert ea_pick("River X", est, flows, test)[0]["notation"] == "B" and tried == ["C", "B"], "a tidal, tributary or suspended station was picked, or the series test was skipped: %s" % tried
        assert ea_pick("River X", est[:1], flows, test)[0] is None and ea_pick("River X (Kent)", est, flows, test)[0] is None, "a tidal-only river or a qualified name matched"
        PICK["River X"] = "B"
        assert ea_pick("River X", est, {"C-q": 9}, lambda sid: (True, None))[0]["notation"] == "B", "a PICK line lost to the flow rule"
        never = lambda r: (_ for _ in ()).throw(AssertionError("an unproven feed reached the agency"))
        row = {"keyword": "river x level", "river": "River X", "tier": "500", "shared": "", "country": "GB"}
        world.recorded = lambda pages: {}  # the fixture never reads a proof this laptop or the cloud recorded
        if world.proof_faults(["ea"], world.PROVED):  # England today: no proof of a live warning, so nothing may be added
            assert england([row], [], set(), stations_of=never, flows={}, rivers=set(), thin={}) == ([], []), "a feed missing a proof added gauges"
        real = world.PROVED
        try:
            world.PROVED = dict(real, ea={k: "seen on live data, fixture" for k in world.PROOFS})
            got = england([row], [], set(), stations_of=lambda r: est, flows=flows, test=lambda sid: (True, None), rivers=set(), thin={})[0]
            assert [g["station"] for g in got] == ["B"], "a proven feed added nothing"
            assert england([row], [{"feed": "ea", "gauge_pages": ["4009"]}], set(), stations_of=never, flows={}, rivers=set(), thin={"4009": ["5 reader blocks"]}) == ([], []), "a feed whose every page was held thin added gauges"
            assert england([row], [], set(), stations_of=never, flows={}, rivers=set(), thin=None) == ([], []), "gauges were added with the live status unread"
            assert len(england([row], [{"feed": "ea", "gauge_pages": list(range(25))}], set(), stations_of=lambda r: est, flows=flows, test=lambda sid: (True, None), rivers=set(), thin={})[0]) == 1, "a country cap is back: 25 listed gauges stopped the next"
        finally:
            world.PROVED = real
        print("selftest OK")
    else:
        main()
