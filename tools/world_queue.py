"""Build the ranked 20,000-row queue from Keyword Planner tiers. Inputs: data/keyword-tiers.csv (keyword, tier, worldwide),
data/world-rivers.csv (Wikidata names), data/waves.csv. Outputs: data/world-queue.csv (all rows) and the publishing order
docs/research/priority/picks.csv (US rows ready now; tools/release.py reads it first). Run: python -I tools/world_queue.py
"""
import collections as C, csv, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOTAL = 20000
CAP = 5000  # a higher number here is trivia, not gauge checking: "yellow river flow" 500K, "jordan river flow" 50K
STEP = {5000: 500, 500: 50, 50: 0, 0: 0}
ENGLISH = ["GB", "IE", "CA", "AU", "NZ", "ZA", "IN", "PH", "LK", "SG", "KE", "NG"]


def norm(k):
    return " ".join(re.sub(r"[-']", " ", k.lower()).split())


def load(name):
    return list(csv.DictReader(open(os.path.join(ROOT, "data", name), encoding="utf-8")))


def tiers():
    return {norm(r["keyword"]): min(int(r["tier"]), CAP) for r in load("keyword-tiers.csv")}


def best(tier, keywords):
    k = max(keywords, key=lambda x: tier.get(norm(x), 0))
    t = tier.get(norm(k), 0)
    if k.endswith(" flow") and not any(tier.get(norm(x)) for x in keywords if not x.endswith(" flow")):
        t = min(t, 500)  # flow alone is often trivia (Jordan River, Holy Land), never the top tier
    return t, k


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
    states = C.defaultdict(set)
    for r in w:
        if r["status"] in ("live", "queue"):
            states[r["river"]].add(r["state"])
    live = {(r["river"], r["state"]) for r in w if r["status"] == "live"}
    abroad = {r["name"] + " river" for r in load("world-rivers.csv") if "US" not in r["cc"]}  # Ottawa River, Ohio must not inherit Canada's searches
    seen, out = set(live), []
    for r in sorted((r for r in w if r["status"] == "queue" and not r["gate"]), key=lambda r: -float(r["score"] or 0)):
        n = r["river"].lower()
        t, k = best(tier, [n + " water level", n + " flow"])
        shared = len(states[r["river"]]) > 1 or n.startswith("lake ") or n in abroad
        if shared:
            t = STEP[t]
        place = (r["river"], r["state"])
        first = place not in seen
        seen.add(place)
        out.append(dict(group=group(t, first), tier=t, keyword=k if t else "", river=r["river"], place=r["place"], region=r["state"], country="US",
                        gauge=r["site"], shared="yes" if shared else "", feed="USGS", ready="yes", score=float(r["score"] or 0), category=r.get("activity") or ""))
    return out, {r["river"].lower() for r in w}


def world_rows(tier, us_names):
    names = C.defaultdict(set)
    count = C.Counter()
    title = {}
    for r in load("world-rivers.csv"):
        names[r["name"]] |= set(filter(None, r["cc"].split("|")))
        count[r["name"]] += 1
        title.setdefault(r["name"], r["title"])
    out = []
    for n, cc in names.items():
        head = n if n.startswith("rio ") else n + " river"
        if head in us_names and "US" in cc:
            continue  # same river as our US gauges
        t, k = best(tier, ["river %s level" % n, head + " water level", head + " flow"])
        shared = count[n] > 1 or head in us_names
        if shared:
            t = STEP[t]
        rank_cc = min((ENGLISH.index(c) for c in cc if c in ENGLISH), default=len(ENGLISH))
        out.append(dict(group=group(t, True) if t else 8, tier=t, keyword=k if t else "", river=title[n], place="", region="", country="|".join(sorted(cc - {"US"})),
                        gauge="", shared="yes" if shared else "", feed="PEGELONLINE" if "DE" in cc else "not checked", ready="no",
                        score=-rank_cc * 100 + len(cc), category=""))
    return out


def main():
    tier = tiers()
    us, us_names = us_rows(tier)
    world = world_rows(tier, us_names)
    rows = sorted(us + world, key=lambda r: (r["group"], -r["tier"], r["ready"] != "yes", -r["score"], r["river"]))[:TOTAL]
    assert len(rows) == TOTAL, len(rows)
    assert all(r["tier"] <= CAP for r in rows)
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
