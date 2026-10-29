"""Name cleaner v2 (planning tool, run on demand): re-reads the raw USGS name of every gauge the first-pass cleaner marked low and expands the short forms it could not read
(Truckee River A Farad, N F Shenandoah River, Wb Susquehanna River, Truckee C, State abbreviations like Fla). A name is written to data/name-fixes.csv only when the result has no leftover one-to-three letter token,
is not longer than 48 characters and has a place. lib/pages.py reads name-fixes.csv after the human overrides (human wins). Usage: python -I tools/clean_names.py [--show 60]
Fixed gauges move from held-names into the queue the next time tools/rescore.py runs; live gauges are never touched (their URLs must not change)."""
import os, re, sys, csv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lib.pages import WAVE0, slug

STATES = "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY PR".split()
LONG_AB = "Ala|Nebr|Mont|Ont|Ark|Okla|Tenn|Miss|Wash|Wis|Minn|Calif|Colo|Ariz|Kans|Mich|Penn|Penna|Tex|Fla|Ga|Va|Ky|Ill|Ind|Ore|Wyo|Nev|Dak"
TOK = {"rv": "River", "rvr": "River", "st": "Saint", "r": "River", "riv": "River", "ck": "Creek", "cr": "Creek", "crk": "Creek", "c": "Creek", "br": "Branch", "bk": "Brook", "fk": "Fork", "f": "Fork", "mf": "Middle Fork", "nf": "North Fork",
       "sf": "South Fork", "ef": "East Fork", "wf": "West Fork", "wb": "West Branch", "eb": "East Branch", "nb": "North Branch", "sb": "South Branch", "mb": "Middle Branch", "n": "North", "s": "South", "e": "East", "w": "West", "m": "Middle",
       "l": "Little", "bl": "Below", "ab": "Above", "abv": "Above", "blw": "Below", "bel": "Below", "nr": "Near", "trib": "Tributary", "cnl": "Canal", "res": "Reservoir", "lk": "Lake", "rd": "Road", "ave": "Avenue", "hwy": "Highway",
       "bdg": "Bridge", "brg": "Bridge", "mt": "Mount", "ft": "Fort", "pt": "Point", "sp": "Springs", "spgs": "Springs", "jct": "Junction", "dstrm": "Downstream", "upstr": "Upstream", "pk": "Peak", "val": "Valley", "cyn": "Canyon",
       "chatt": "Chattahoochee", "fy": "Ferry", "hl": "Hill", "can": "Canyon", "mtn": "Mountain", "pa": "PA", "str": "Stream", "dr": "Drive", "ala": "AL"}
DENY = set("a ga ala fy pc rte rt ds us mi div cn sh dr str ave blv bld cty co ck tr tw rr rm".split())  # short forms that are never part of a place name; any other short token with a vowel is read as a word (Ann, Ivy, Rum)
PREP = r"(?:at|near|nr|below|bl|blw|bel|above|ab|abv|downstream|dstrm|upstream|upstr|a)"
SMALL_OK = set("of the and at on in to la el san old big red dry elk oak fox cow bear us mi run new rio des de dam elm hot bay las mud gap los two paw bow dee van tar no fe au le up lee ash bad bay bee box cat dog eel fig gum hog ice jay key lag log mad man mil mow nut oil pea pig pot rat raw rye sac saw sea sun tin toy wet wolf yes zoo ten six one fox lac mill fall".split())


def clean(raw):
    s = raw.strip()
    for _ in range(2):
        s = re.sub(r"[,\s]+(?:%s|%s)\.?$" % ("|".join(STATES), LONG_AB), "", s, flags=re.I).strip()
    m = re.split(r"\s+(%s)\s+" % PREP, s, maxsplit=1, flags=re.I)
    river_raw, prep, place_raw = (m[0], m[1].lower(), m[2]) if len(m) == 3 else (s, "", "")

    def toks(t):
        out, bad = [], 0
        for w in re.split(r"\s+", t.strip()):
            bare = w.strip(",.")
            k = bare.lower()
            if not bare:
                continue
            if k in TOK:
                out.append(TOK[k])
            elif re.fullmatch(r"[A-Za-z]{1,3}", bare) and k not in SMALL_OK and (k in DENY or not re.search(r"[aeiou]", k)):
                bad += 1
                out.append(bare.title())
            else:
                out.append(bare.capitalize() if bare.isupper() or bare.islower() else bare)
        return " ".join(out), bad
    river, b1 = toks(river_raw)
    place, b2 = toks(place_raw) if place_raw else ("", 0)
    pre = {"below": "Below ", "bl": "Below ", "blw": "Below ", "bel": "Below ", "above": "Above ", "ab": "Above ", "abv": "Above "}.get(prep, "")
    place = (pre + place).strip()
    if not place:
        place = river
    return river, place, b1 + b2, bool(place_raw)


def main():
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "pages-all.csv"), encoding="utf-8")))
    ov = {r["site"] for r in csv.DictReader(open(os.path.join(ROOT, "data", "name-overrides.csv"), encoding="utf-8"))}
    LIVE_NOW = {r["site"] for r in csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8")) if r["status"] == "live"}
    fixed, left = [], 0
    for r in rows:
        if r["name_confidence"] != "low" or r["site"] in WAVE0 or r["site"] in ov or r["site"] in LIVE_NOW:
            continue
        river, place, bad, had_place = clean(r["raw_name"])
        raw = r["raw_name"]
        if "&" in raw or re.search(r"\b[A-Za-z]\.\s", raw) or re.search(r"\b[A-Za-z]{4,}\.\s", raw) or re.match(r"(?i)ar\s", raw) or re.search(r"\b\d+(st|nd|rd|th)?\s+st\b", raw, re.I):
            left += 1
            continue
        if bad or not had_place or len(place) > 48 or re.search(r"\d", river):
            left += 1
            continue
        fixed.append((r["site"], river, place, r["raw_name"]))
    with open(os.path.join(ROOT, "data", "name-fixes.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["site", "river", "place", "raw_name"])
        w.writerows(fixed)
    print("low-confidence gauges re-read: fixed %d, still unreadable %d" % (len(fixed), left))
    n = int(sys.argv[sys.argv.index("--show") + 1]) if "--show" in sys.argv else 0
    import random
    random.seed(7)
    for s, rv, pl, raw in random.sample(fixed, min(n, len(fixed))):
        print("  %-48s -> %s | %s" % (raw, rv, pl))


main()
