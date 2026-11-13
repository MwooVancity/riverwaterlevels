"""Build the ranked 20,000-row queue from Keyword Planner tiers. Inputs: data/keyword-tiers.csv (keyword, tier, worldwide),
data/world-rivers.csv (Wikidata names), data/waves.csv. Outputs: data/world-queue.csv (all rows) and the publishing order
docs/research/priority/picks.csv (US rows ready now; tools/release.py reads it first). Run: python -I tools/world_queue.py
"""
import collections as C, csv, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOTAL = 20000
CAP = 5000  # a higher number here is trivia, not gauge checking: "yellow river flow" 500K, "jordan river flow" 50K
STEP = {5000: 500, 500: 50, 50: 0, 0: 0}
PICKS = {(r["river"], r["state"]) for r in csv.DictReader(open(os.path.join(ROOT, "data", "keyword-picks.csv"), encoding="utf-8"))} if os.path.exists(os.path.join(ROOT, "data", "keyword-picks.csv")) else set()  # river name -> the state its searches mean, picked by hand
NOT_RIVER = re.compile(r"\b(dispute|flood|floods|pollution|battle|treaty|bridge)\b", re.I)
ENGLISH = ["GB", "IE", "CA", "AU", "NZ", "ZA", "IN", "PH", "LK", "SG", "KE", "NG"]


def norm(k):
    return " ".join(re.sub(r"[-']", " ", k.lower()).split())


def load(name):
    return list(csv.DictReader(open(os.path.join(ROOT, "data", name), encoding="utf-8")))


LEVEL = re.compile(r"\b(water|river|lake) levels?\b")  # PLAN 12 (keyword debate): "danube water levels" 50,000 is a gauge search, not trivia; only these phrasings pass CAP


# Owner 2026-11-13 "grow 10x": the Keyword Planner run of activity phrasings (data/kwp/) ranks the queue too, but only phrasings a gauge page answers
# with its own reading. Left out: 'forecast' ('battle creek forecast' is the town's weather), 'flooding' (news), fishing report, boat ramp, swimming.
# Also left out: 'water temperature' (many gauges have no sensor, the page would answer 'Unknown').
ASK = ("flood stage", "cfs", "gauge height", "conditions", "kayaking", "tubing")
assert not {"forecast", "flooding", "water temperature"} & set(ASK), "world_queue: a phrasing our page does not answer ranks the queue"


def tiers():
    t = {norm(r["keyword"]): int(r["tier"]) for r in load("keyword-tiers.csv")}
    kd = os.path.join(ROOT, "data", "kwp")
    for f in sorted(os.listdir(kd)) if os.path.isdir(kd) else []:
        if f.startswith("results-") and f.endswith(".csv"):
            for r in csv.DictReader(open(os.path.join(kd, f), encoding="utf-8")):
                if r["phrasing"] in ASK and int(r["tier"]) >= 50:
                    k = norm(r["keyword"])
                    t[k] = max(t.get(k, 0), int(r["tier"]))  # two measurements of one keyword: the larger, never load order
    return {k: (v if LEVEL.search(k) else min(v, CAP)) for k, v in t.items()}


def best(tier, keywords):
    k = max(keywords, key=lambda x: tier.get(norm(x), 0))
    t = tier.get(norm(k), 0)
    if k.endswith(" flow") and not any(tier.get(norm(x)) for x in keywords if not x.endswith((" flow",) + tuple(" " + a for a in ASK))):  # an activity search never lifts flow trivia
        t = min(t, 500)  # flow alone is often trivia (Jordan River, Holy Land), never the top tier
    return t, k


def write_demand(tier):
    """data/us-river-demand.csv: one row per US river name with a search number, after the shared-name rules. lib/directory.py orders state pages by it."""
    w = [r for r in load("waves.csv") if r["status"] in ("live", "queue")]
    states = C.defaultdict(set)
    for r in w:
        states[r["river"]].add(r["state"])
    abroad = {r["name"] + " river" for r in load("world-rivers.csv") if "US" not in r["cc"]}
    with open(os.path.join(ROOT, "data", "us-river-demand.csv"), "w", newline="", encoding="utf-8") as f:
        o = csv.writer(f)
        o.writerow(["river", "tier"])
        for name in sorted(states):
            n = name.lower()
            t, _ = best(tier, [n + " water level", n + " flow"])
            t = STEP[t] if len(states[name]) > 1 or n.startswith("lake ") or n in abroad else t
            if t:
                o.writerow([name, t])


def group(t, first):
    if t >= 5000:
        return 1 if first else 3
    if t >= 500:
        return 2 if first else 3
    if t:
        return 4 if first else 5
    return 6 if first else 7


def us_rows(tier):
    w = load("waves.csv")
    states, parts = C.defaultdict(set), C.defaultdict(set)
    for r in w:
        if r["status"] in ("live", "queue"):
            states[r["river"]].add(r["state"])
            if r["site"][:8].isdigit():
                parts[r["river"]].add(r["site"][:2])
    live = {(r["river"], r["state"]) for r in w if r["status"] == "live"}
    abroad = {r["name"] + " river" for r in load("world-rivers.csv") if "US" not in r["cc"]}  # Ottawa River, Ohio must not inherit Canada's searches
    seen, out = set(live), []
    wet = {r["site"] for f in ("lakes.csv", "coasts.csv") for r in load(f)}  # lakes and coasts: water_rows
    for r in sorted((r for r in w if r["status"] == "queue" and not r["gate"] and r["site"] not in wet), key=lambda r: -float(r["score"] or 0)):
        n = r["river"].lower()
        t, k = best(tier, [n + " water level", n + " flow"] + [n + " " + a for a in ASK])
        shared = len(states[r["river"]]) > 1 or n.startswith("lake ") or n in abroad
        held = ""
        if n.startswith("lake "):  # keyword debate 2026-11-07: "lake fork water level" means Lake Fork Reservoir TX, never a river gauge named Lake Fork (7 rows)
            t, held = 0, "held: a lake keyword on a river gauge"
        elif len(parts[r["river"]]) > 1 and t >= 500 and (r["river"], r["state"]) not in PICKS:  # keyword debate: different rivers sharing a name (White River IN, AR, VT) earn nothing until data/keyword-picks.csv names the one the searches mean.
            # One river crossing states (French Broad NC-TN, Youghiogheny MD-PA) keeps one USGS region (the site number's first two digits), so it is not held. ponytail: region prefix, a basin (HUC) lookup if two same-region namesakes appear
            t, held = 0, "held: %d different rivers share this name (USGS regions %s); pick one in data/keyword-picks.csv" % (len(parts[r["river"]]), ", ".join(sorted(parts[r["river"]])))
        elif shared:
            t = STEP[t]
        place = (r["river"], r["state"])
        first = place not in seen
        seen.add(place)
        out.append(dict(group=group(t, first), tier=t, keyword=k if t else "", river=r["river"], place=r["place"], region=r["state"], country="US",
                        gauge=r["site"], shared=held or ("yes" if shared else ""), feed="USGS", ready="yes", score=float(r["score"] or 0), category=r.get("activity") or ""))
    return out, {r["river"].lower() for r in w}


def world_rows(tier, us_names):
    names = C.defaultdict(set)
    count = C.Counter()
    uk = C.defaultdict(list)
    titles = C.defaultdict(list)
    for r in load("world-rivers.csv"):
        if NOT_RIVER.search(r["title"]):
            continue
        cc = set(filter(None, r["cc"].split("|")))
        names[r["name"]] |= cc
        count[r["name"]] += 1
        titles[r["name"]].append(r["title"])
        if cc & {"GB", "IE"}:
            uk[r["name"]].append(r["title"])
    out = []
    for n, cc in names.items():
        head = n if n.startswith("rio ") else n + " river"
        if head in us_names and "US" in cc:
            continue  # same river as our US gauges
        t, k = best(tier, ["river %s level" % n, head + " water level", head + " flow"])
        british = t and k.startswith("river ")  # "river thames level" is British wording, so only a British namesake competes
        shared = len(uk[n]) > 1 if british else count[n] > 1 or head in us_names
        if not british and head in us_names and t >= 500:  # keyword debate 2026-11-07: "white river water level" was credited to the White River in Jamaica; a US river shares the name, so the searches are not this river's until picked
            t, shared = 0, "held: a US river shares this name"
        elif shared:
            t = STEP[t]
        pool = uk[n] if british else titles[n]
        title = min(pool, key=lambda x: ("(" in x or "," in x, len(x), x))
        rank_cc = min((ENGLISH.index(c) for c in cc if c in ENGLISH), default=len(ENGLISH))
        out.append(dict(group=group(t, True) if t else 8, tier=t, keyword=k if t else "", river=title, place="", region="", country="|".join(sorted(cc - {"US"})),
                        gauge="", shared=shared if isinstance(shared, str) else ("yes" if shared else ""), feed="PEGELONLINE" if "DE" in cc else "not checked", ready="no",
                        score=-rank_cc * 100 + len(cc), category=""))
    return out


PHRASE = re.compile(r" (water level|level today|levels?|tides?|tide times|tide chart|high tide|water temperature|water temp|surf report|beach conditions|fishing report|dam release|gauge|depth|map)$")


def water_rows():
    """Lakes, coasts and state hubs in the SAME money list (owner 2026-11-07: the queue decides; 'texas lake levels' 10K-100K was missing because
    the queue was one row per river gauge, and rerunning this file dropped the hand-added lake and coast rows). Tiers from keyword-tiers-water.csv,
    uncapped: the CAP above is for river trivia ('yellow river flow'), a lake or tide search is the page itself. Built lakes and coasts (lakes.csv,
    coasts.csv) are ready with their gauge; every other name with 10+ searches is a 'not checked' row until a feed and terms are proven."""
    water = {}
    for r in load("keyword-tiers-water.csv"):
        k, t = norm(r["keyword"]), int(r["tier"])
        name = PHRASE.sub("", k)
        hub = re.match(r"(.+) (lake|river) levels$", k)
        kind = "hub" if hub and hub.group(1).title() in STATE_NAMES else r["kind"]
        if kind in ("river", "research") or t < 50 or name == k or (kind == "lake" and not WET.search(name)):  # 'tenis level' (tennis) is not a lake (keyword debate)
            continue
        cur = water.get((kind, name))
        if not cur or t > cur[0]:
            water[(kind, name)] = (t, r["keyword"])
    out, took = [], set()
    w = {r["site"]: r for r in load("waves.csv")}
    states_of = C.defaultdict(set)  # PLAN step 6: one name in several states (Clear Lake CA, IA, TX) is several places
    for kind, f, key in (("lake", "lakes.csv", "lake"), ("ocean", "coasts.csv", "place")):
        for r in load(f):
            states_of[core(norm(r[key]))].add(r["state"])
    for kind, f, key in (("lake", "lakes.csv", "lake"), ("ocean", "coasts.csv", "place")):
        for r in load(f):
            names = [n for (kd, n) in water if kd == kind and core(n) in (core(norm(r[key])), core(norm(r[key])) | ALIAS.get(core(norm(r[key])), set()))] or [norm(r[key])]  # 'lake choke canyon', 'hartwell lake'
            hit = [(water[(kind, n)], n) for n in names if (kind, n) in water]
            (t, k), n = max(hit) if hit else ((0, ""), "")
            took.update((kind, x) for x in names)
            held = namesake(core(norm(r[key])), r["state"], k, states_of) if t else ""
            t = 0 if held else t
            st = (w.get(r["site"]) or {}).get("status")
            out.append(dict(group=group(t, True), tier=t, keyword=k if t else "", river=r.get("lake") or r.get("name"), place=r.get("place", ""), region=r["state"], country="US",
                            gauge=r["site"], shared=held, feed=FEED.get((r.get("source") or ":").split(":")[0]) or ("USGS" if kind == "lake" else "NOAA CO-OPS"), ready="yes" if st in ("live", "queue") else "no", score=0, category=kind))
    for (kind, name), (t, k) in water.items():
        if (kind, name) in took:
            continue
        out.append(dict(group=group(t, True), tier=t, keyword=k, river=name.title(), place="", region="", country="", gauge=HUBS_BUILT.get(name, ""), shared="",
                        feed="statewide hub", ready="yes" if name in HUBS_BUILT else "no", score=0, category=kind) if kind == "hub" else
                   dict(group=group(t, True), tier=t, keyword=k, river=name.title(), place="", region="", country="", gauge="", shared="", feed="not checked", ready="no", score=0, category=kind))
    return out


WET = re.compile(r"\b(lake|lakes|reservoir|pond|lago|lac|loch|lough|see|dam|bay)\b")
HUBS_BUILT = {"texas lake": "/lakes/tx/"}  # built hub -> its URL in the gauge column (a built row has a gauge); ponytail: one hub, the hub generator (PLAN 'SITE STRUCTURE') replaces this
FEED = {"cdec": "CDEC", "rise": "Reclamation RISE", "twdb": "TWDB", "coops": "NOAA CO-OPS"}  # lakes.csv source prefix -> queue feed label
ALIAS = {frozenset({"lanier"}): {"sidney"}}  # Lake Sidney Lanier is Lake Lanier's official name


def core(n):
    return frozenset(n.split()) - {"lake", "reservoir", "the"}


def namesake(name, st, keyword, states_of):
    """PLAN step 6, the systemic namesake rule for lakes and coasts: a bare keyword ('clear lake level') whose name belongs to places in two or more
    states earns no page its searches until the keyword names the row's state (full name, or the abbreviation as the last word). '' = credit it.
    Rivers: us_rows (USGS regions) and world_rows (a US river shares the name); tide places abroad: tools/coast_match.py abroad (GeoNames).
    ponytail: knows only the places in lakes.csv and coasts.csv; a namesake we have not listed is caught by coast_match's GeoNames for coasts, not for lakes."""
    many = states_of.get(name) or set()
    if len(many) < 2:
        return ""
    sys.path.insert(0, ROOT)
    from lib.directory import STATE_NAMES as FULL
    k = norm(keyword)
    if k.split()[-1:] == [st.lower()] or " %s " % norm(FULL.get(st, st)) in " %s " % k:  # whole words: 'arkansas' never names Kansas
        return ""
    return "held: %d states have a place of this name (%s); the keyword names none" % (len(many), ", ".join(sorted(many)))


STATE_NAMES = {s.title() for s in ("alabama alaska arizona arkansas california colorado connecticut delaware florida georgia hawaii idaho illinois indiana iowa kansas kentucky "
               "louisiana maine maryland massachusetts michigan minnesota mississippi missouri montana nebraska nevada ohio oklahoma oregon pennsylvania tennessee texas "
               "utah vermont virginia washington wisconsin wyoming").split()} | {"New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota",
                                                                                   "Rhode Island", "South Carolina", "South Dakota", "West Virginia"}


def main():
    tier = tiers()
    write_demand(tier)
    us, us_names = us_rows(tier)
    world = world_rows(tier, us_names)
    water = water_rows()
    rows = sorted(us + world + water, key=lambda r: (r["group"], -r["tier"], r["ready"] != "yes", -r["score"], r["river"]))[:TOTAL]
    assert len(rows) == TOTAL, len(rows)
    assert all(r["tier"] <= CAP or LEVEL.search(norm(r.get("keyword") or "")) for r in rows if r["category"] not in ("lake", "ocean", "hub"))
    assert LEVEL.search("danube water levels") and not LEVEL.search("yellow river flow"), "world_queue: the level-phrase exception matches the wrong words"
    assert best({"yellow river flow": 5000, "yellow river kayaking": 50}, ["yellow river water level", "yellow river flow", "yellow river kayaking"]) == (500, "yellow river flow"), "world_queue: an activity search lifted flow trivia past 500"
    built = {x["site"] for x in load("waves.csv") if x["status"] in ("live", "queue")} & {r["site"] for f in ("lakes.csv", "coasts.csv") for r in load(f)}
    assert built <= {r["gauge"] for r in rows if r["ready"] == "yes"}, "a built lake or coast fell out of the queue: %s" % sorted(built - {r["gauge"] for r in rows})
    assert all(r["group"] == 8 or r["ready"] == "yes" or r["tier"] for r in rows)
    assert len({r["gauge"] for r in rows if r["gauge"]}) == sum(1 for r in rows if r["gauge"])
    fields = ["rank", "group", "tier", "keyword", "river", "place", "region", "country", "gauge", "shared", "feed", "ready"]
    with open(os.path.join(ROOT, "data", "world-queue.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(dict(r, rank=i) for i, r in enumerate(rows, 1))
    with open(os.path.join(ROOT, "docs", "research", "priority", "picks.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["site", "river", "place", "state", "category"])
        w.writerows([r["gauge"], r["river"], r["place"], r["region"], r["category"]] for r in rows if r["ready"] == "yes")
    print("rows", len(rows), "ready", sum(r["ready"] == "yes" for r in rows), "groups", sorted(C.Counter(r["group"] for r in rows).items()))
    print("tiers", sorted(C.Counter(r["tier"] for r in rows).items()), "foreign with demand", sum(1 for r in rows if r["ready"] == "no" and r["tier"]))
    for r in rows[:30]:
        print(r["group"], r["tier"], r["ready"], r["keyword"], "|", r["river"], r["place"], r["region"], r["country"], r["shared"])


if __name__ == "__main__":
    main()
