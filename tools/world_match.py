"""Match world queue rows to a real agency station, strictly, so the release can publish them. Run: python -I tools/world_match.py
Writes data/world-ready.csv (tier, keyword, feed, station, title, page). Canada only for now: one bulk ECCC station list call.
Rules (a wrong gauge is the worst defect, so anything unsure is skipped and printed with its reason):
- the station name must be "<RIVER> AT|NEAR|ABOVE|BELOW ..." (canals, drains and diversions never match);
- a bracketed qualifier must be a province, or a word found in the station name; with no qualifier the stations must sit in one province;
- a keyword a US gauge also targets is skipped (the searcher may mean the US river);
- of what is left, the largest drainage area: the main stem, one gauge per river.
ponytail: largest drainage can pick a remote mouth gauge over a city one (Bow River near the mouth, not Calgary); add a per-river pick list if readers ask."""
import csv, json, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROV = {"alberta": "AB", "british columbia": "BC", "manitoba": "MB", "new brunswick": "NB", "newfoundland": "NL", "labrador": "NL", "nova scotia": "NS", "ontario": "ON",
        "prince edward island": "PE", "quebec": "QC", "saskatchewan": "SK", "yukon": "YT", "northwest territories": "NT", "nunavut": "NU"}
URL = "https://api.weather.gc.ca/collections/hydrometric-stations/items?f=json&limit=10000&skipGeometry=true&STATUS_EN=Active&REAL_TIME=1&properties=STATION_NUMBER,STATION_NAME,PROV_TERR_STATE_LOC,DRAINAGE_AREA_GROSS"


def pick(river, stations):
    """(station, None) or (None, reason)."""
    m = re.match(r"^(.*?)\s*(?:\((.*)\))?$", river.strip())
    base, qual = m.group(1).upper().replace("ST. ", "ST. "), (m.group(2) or "").lower()
    hits = [s for s in stations if re.match(r"^%s (AT|NEAR|ABOVE|BELOW) " % re.escape(base), s["STATION_NAME"])]
    if qual:
        if qual in PROV:
            hits = [s for s in hits if s["PROV_TERR_STATE_LOC"] == PROV[qual]]
        else:
            hits = [s for s in hits if qual.upper() in s["STATION_NAME"]]
    elif len({s["PROV_TERR_STATE_LOC"] for s in hits}) > 1:
        return None, "same name in %d provinces" % len({s["PROV_TERR_STATE_LOC"] for s in hits})
    if not hits:
        return None, "no real-time station named for it"
    return max(hits, key=lambda s: s.get("DRAINAGE_AREA_GROSS") or 0), None


def title(name):
    return re.sub(r" (At|Near|Above|Below) ", lambda m: m.group(0).lower(), name.title())


def covered():
    """River names already on a Canadian page, from the hub cache, else the live gauge list: one gauge per river."""
    try:
        names = [r.get("title") or "" for r in json.load(open(os.path.join(ROOT, "cache", "_river-canada.json"), encoding="utf-8"))["rows"]]
    except (OSError, ValueError, KeyError):
        names = [r[0] for r in json.load(urllib.request.urlopen(urllib.request.Request("https://riverwaterlevels.com/gauges.json", headers={"User-Agent": "riverwaterlevels.com"}), timeout=30)) if "Canada" in r[4]]
    return {re.split(r" (?:at|near|above|below) ", n, maxsplit=1)[0].upper() for n in names}


def main(stations=None, seen=None):
    seen = covered() if seen is None else seen
    stations = stations or [f["properties"] for f in json.load(urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "riverwaterlevels.com"}), timeout=90))["features"]]
    if len(stations) < 1000:
        sys.exit("station list cut short (%d): nothing written" % len(stations))
    pages = json.load(open(os.path.join(ROOT, "data", "world-pages.json"), encoding="utf-8"))
    have = {n for p in pages for n in p.get("gauge_pages") or []}
    out, skip = [], []
    for r in csv.DictReader(open(os.path.join(ROOT, "data", "world-queue.csv"), encoding="utf-8")):
        if r["ready"] == "yes" or "CA" not in r["country"].split("|") or r["tier"] == "0":
            continue
        if r["shared"] or "US" in r["country"].split("|"):
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
        print("selftest OK")
    else:
        main()
