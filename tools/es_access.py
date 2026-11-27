"""Writes data/es-access.json: places mapped in OpenStreetMap beside each of the 50 Spain reservoirs (slipways, beaches and bathing places,
marinas, boat hire and water clubs, campsites). By hand, about once a quarter: python -I tools/es_access.py   (lib/es.py hides the block after a year).
A reservoir is matched by its whole name; a name found on two waters far apart is left out unless PICK says which one it is."""
import csv
import datetime
import json
import math
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "es-access.json")
STOP = {"embalse", "de", "del", "la", "el", "los", "las", "pantano", "presa", "embassament", "encoro", "urtegia", "d", "l", "panta"}
PICK = {"San Juan": lambda e: e["bounds"]["minlat"] < 41,  # Tajo (Madrid); the other Embalse/Pantano de San Juan is on the Ebro side
        "Pena": lambda e: e["tags"].get("name") == "Embalse de Pena"}  # Teruel; 'Embalse de La Pena' (Huesca) is another reservoir
FILTERS = ('["leisure"="slipway"]', '["leisure"~"^(bathing_place|swimming_area|marina)$"]', '["natural"="beach"]', '["amenity"="boat_rental"]',
           '["sport"~"canoe|kayak|sailing|water_ski|rowing"]', '["tourism"="camp_site"]')
NEAR_M, CAMP_M = 250, 500  # from the mapped water outline
SPREAD = 0.35  # degrees: name matches further apart than this are different waters


def words(s):
    a = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return frozenset(w for w in re.findall(r"[a-z0-9]+", a) if w not in STOP)


def match(name, elements):
    """The OpenStreetMap water(s) that are this reservoir, or [] when none or when it cannot be told which."""
    m = re.match(r"^(.*), (El|La|Los|Las)$", name)
    full = m.group(2) + " " + m.group(1) if m else name
    alts = [words(a) for a in [full] + re.split(r"[-()]+", full) if words(a)]
    hits = [e for e in elements if e.get("bounds") and any(words(v) in alts for k, v in e.get("tags", {}).items() if k.split(":")[0] in ("name", "alt_name", "official_name"))]
    if name in PICK:
        hits = [e for e in hits if PICK[name](e)]
    for key in ("minlat", "minlon"):
        if hits and max(h["bounds"][key] for h in hits) - min(h["bounds"][key] for h in hits) > SPREAD:
            return []
    return hits


def kind(t):
    if t.get("leisure") == "slipway":
        return "ramp"
    if t.get("leisure") in ("bathing_place", "swimming_area"):
        return "bathing"
    if t.get("natural") == "beach":
        return "beach"
    if t.get("tourism") == "camp_site":
        return "camp"
    return "boats"


def usable(t):
    return t.get("access") not in ("private", "no", "military") and not re.search(r"(?i)\bmilitar\b", t.get("name", ""))


WRONG_NAME = {"camp": r"(?i)^(presa|club n[aá]utic)", "beach": r"(?i)^embarcadero$", "boats": r"(?i)de arousa"}  # review 2026-11-27: the name says it is not that kind of place, or not this place (Arousa is in Galicia)
SAME_M = 300  # two map objects with one name this close are one place


def tidy(places):
    """Drop a place whose name contradicts it, and the second copy of a place mapped twice."""
    out = []
    for g in places:
        if g["name"] and (re.search(WRONG_NAME.get(g["kind"], r"(?!)"), g["name"]) or any(
                o["kind"] == g["kind"] and o["name"] and words(o["name"]) == words(g["name"]) and metres((o["lat"], o["lon"]), (g["lat"], g["lon"])) <= SAME_M for o in out)):
            continue
        out.append(g)
    return out


def metres(a, b):
    return 111200 * math.hypot(a[0] - b[0], (a[1] - b[1]) * math.cos(math.radians(a[0])))


def over(q):
    for _ in range(6):
        try:
            req = urllib.request.Request("https://overpass-api.de/api/interpreter", urllib.parse.urlencode({"data": q}).encode(), {"User-Agent": "riverwaterlevels.com data"})
            r = json.load(urllib.request.urlopen(req, timeout=240))
            if r.get("remark"):  # Overpass answers 200 with a partial list when it runs out of time
                raise OSError("partial answer: %s" % r["remark"][:80])
            return r["elements"]
        except Exception as e:
            print("retry", str(e)[:80])
            time.sleep(45)
    raise SystemExit("Overpass unavailable: data/es-access.json left as it was")


def main():
    with open(os.path.join(ROOT, "data", "es-reservoirs.csv"), encoding="utf-8") as f:
        names = [r["name"] for r in csv.DictReader(f) if int(r["rank"]) <= 50]
    waters = over('[out:json][timeout:180];area["ISO3166-1"="ES"][admin_level=2]->.es;(way(area.es)["natural"="water"]["water"="reservoir"]["name"];relation(area.es)["natural"="water"]["water"="reservoir"]["name"];);out tags bb;')
    found = {n: h for n, h in ((n, match(n, waters)) for n in names) if h}
    if len(found) < 40:
        raise SystemExit("only %d of 50 matched: file left as it was" % len(found))
    ids = {t: [str(h["id"]) for hs in found.values() for h in hs if h["type"] == t] for t in ("way", "relation")}
    geo = over("[out:json][timeout:200];(%s);out geom;" % "".join("%s(id:%s);" % (t, ",".join(v)) for t, v in ids.items() if v))
    shape = {(e["type"], e["id"]): [(p["lat"], p["lon"]) for p in e.get("geometry", [])] + [(p["lat"], p["lon"]) for m in e.get("members", []) for p in m.get("geometry", [])] for e in geo}

    def box(h):
        b = h["bounds"]
        return b["minlat"] - .006, b["minlon"] - .008, b["maxlat"] + .006, b["maxlon"] + .008

    pois = over("[out:json][timeout:230];(%s);out center tags;" % "".join("nwr%s(%.4f,%.4f,%.4f,%.4f);" % ((f,) + box(h)) for hs in found.values() for h in hs for f in FILTERS))
    out = {}
    for n, hs in found.items():
        outline = [p for h in hs for p in shape.get((h["type"], h["id"]), [])]
        if not outline:
            continue
        got = []
        for e in pois:
            t, c = e.get("tags", {}), e.get("center") or e
            p = (c["lat"], c["lon"])
            if not usable(t) or not any(a <= p[0] <= x and b <= p[1] <= y for a, b, x, y in map(box, hs)):
                continue
            k = kind(t)
            if min(metres(p, q) for q in outline) <= (CAMP_M if k == "camp" else NEAR_M):  # ponytail: distance to outline corners, not edges; a straight shore with far corners can drop a point, never add one
                got.append({"kind": k, "name": t.get("name"), "lat": round(p[0], 5), "lon": round(p[1], 5), "access": t.get("access"), "osm": "%s/%d" % (e["type"], e["id"])})
        got = tidy(sorted(got, key=lambda g: (g["kind"], not g["name"], g["name"] or "", g["osm"])))
        if got:
            out[n] = got
        b = hs[0]["bounds"]
        print("%-22s %6.2f %6.2f  %d places" % (n, b["minlat"], b["minlon"], len(got)))
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"read_on": datetime.date.today().isoformat(), "licence": "Data (c) OpenStreetMap contributors, ODbL 1.0, https://www.openstreetmap.org/copyright", "reservoirs": out}, f, ensure_ascii=False, indent=1)
    print("matched %d of 50, %d with places, %d places" % (len(found), len(out), sum(map(len, out.values()))))


def selftest():
    def w(i, name, lat, lon):
        return {"type": "way", "id": i, "tags": {"name": name}, "bounds": {"minlat": lat, "maxlat": lat + .1, "minlon": lon, "maxlon": lon + .1}}
    two = [w(1, "Embalse de San Juan", 40.37, -4.45), w(2, "Pantano de San Juan", 41.76, -0.23)]
    assert [h["id"] for h in match("San Juan", two)] == [1], "the wrong San Juan was picked"
    assert match("Alloz", [w(1, "Embalse de Alloz", 42.7, -1.9), w(2, "Embalse de Alloz", 38.0, -3.0)]) == [], "two far waters with one name were merged"
    assert match("Viñuela, La", [w(3, "Embalse de La Viñuela", 36.8, -4.2)]) and not match("Pena", [w(4, "Embalse de La Peña", 42.37, -.76)])
    assert not usable({"access": "private"}) and not usable({"name": "Campamento Militar X"}) and usable({"access": "customers"})
    assert kind({"leisure": "slipway"}) == "ramp" and kind({"natural": "beach"}) == "beach" and kind({"tourism": "camp_site"}) == "camp"
    sys.path.insert(0, ROOT)
    import check
    from lib import es
    data = {"read_on": "2026-11-27", "reservoirs": {"A": [{"kind": "ramp", "name": None, "osm": "way/1", "access": None}, {"kind": "beach", "name": "Playa <B>", "osm": "node/2", "access": "customers"}]}}
    day = datetime.date(2026, 11, 28)
    h = es.access_section("A", day, data)
    assert "1 rampa para embarcaciones, 1 playa" in h and "Rampa sin nombre (1)" in h and "&lt;B&gt;" in h and "solo clientes" in h and not check.es_access_claims(h, "A", day, data)
    assert es.access_section("Z", day, data) == "" and es.access_section("A", day, {}) == "" and es.access_section("A", datetime.date(2028, 1, 1), data) == "", "no data or an old map reading made a block"
    assert check.es_access_claims(h.replace("way/1", "way/9"), "A", day, data) and check.es_access_claims(h.replace("no indica que", "indica que"), "A", day, data), "a foreign place or a missing warning passed"
    def p(kind, name, lat):
        return {"kind": kind, "name": name, "lat": lat, "lon": -2.0, "access": None, "osm": "node/%d" % int(lat * 1e4)}
    kept = tidy([p("beach", "Playa Uno", 39.0), p("beach", "Playa Uno", 39.001), p("beach", "Playa Uno", 39.05), p("camp", "Presa La Vinuela", 39.0), p("beach", "Embarcadero", 39.0), p("ramp", None, 39.0), p("ramp", None, 39.0001)])
    assert [(g["kind"], g["lat"]) for g in kept] == [("beach", 39.0), ("beach", 39.05), ("ramp", 39.0), ("ramp", 39.0001)], kept
    two = es.access_section("A", day, {"read_on": "2026-11-27", "reservoirs": {"A": [{"kind": "beach", "name": "X", "osm": "node/1", "access": None}, {"kind": "beach", "name": None, "osm": "node/2", "access": None}]}})
    assert "Playa sin nombre (1)" in two, "unnamed places are not numbered from 1"
    print("es_access selftest OK")


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main()
