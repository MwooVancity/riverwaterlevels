# Second pass: live hero against USGS latest, big moves under a Normal label, banners, canadian and odd names, static pages' claims.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import csv, json, re, collections as C
from txt import text
sys.stdout.reconfigure(encoding="utf-8")
S = "C:/Users/mwoo7/Desktop/riverwaterlevels/runs/quarter/"
R = "C:/Users/mwoo7/Desktop/riverwaterlevels/"
latest = json.load(open(S + "latest.json"))
waves = {r["site"]: r for r in csv.DictReader(open(R + "data/waves.csv", encoding="utf-8"))}
seen = set()
off = []
big = []
ban = []
oth = []
chips = C.Counter()
for f in os.listdir(S + "live"):
    if not f.startswith("river_"):
        continue
    h = open(S + "live/" + f, encoding="utf-8").read()
    t = text(f)
    m = re.search(r"USGS gauge (\d{8,15})", t)
    if not m:
        oth.append(f)
        continue
    s = m.group(1)
    seen.add(s)
    if 'class="abanner' in h or "<a class=\"abanner" in h:
        ban.append(s)
    hm = re.search(r"min old\s+([\d,.-]+) cfs (.{4,30}?) for \w+ \d+ ([-+][\d.]+)% flow in 6 h", t) or re.search(r"(?:old|ago)\s+([\d,.-]+) cfs (.{4,30}?) for \w+ \d+\s+(.{0,30})", t)
    if not hm:
        oth.append("hero? " + s + " " + re.sub(r"\s+", " ", t[t.find("USGS gauge"):][:170]))
        continue
    v = float(hm.group(1).replace(",", ""))
    l = latest.get(s, {}).get("00060")
    if l and l[0] not in (None, ""):
        lv = float(l[0])
        if lv and abs(v / lv - 1) > 0.15:
            off.append((s, v, lv, l[1][:16]))
    chips[hm.group(2)] += 1
    pm = re.match(r"[-+][\d.]+", hm.group(3))
    if pm and abs(float(pm.group())) >= 25:
        big.append((s, waves[s]["river"], waves[s]["place"], hm.group(2), pm.group(), v))
print("gauges", len(seen), "live rows missing", [s for s, r in waves.items() if r["status"] == "live" and s not in seen])
print("banner", ban, "chips", chips)
print("hero off >15% from USGS now", off)
print("6h change >=25%", big)
print("other", oth[:12])
for s, r in waves.items():
    if re.search(r"British Columbia|Canada|Ontario|Quebec|Alberta|Manitoba|Saskatchewan|Yukon|Mexico\b", r["place"] + r["river"]) and "New Mexico" not in r["place"] + r["river"]:
        print("foreign?", s, r["status"], r["state"], r["river"], r["place"])
for f in ("methodology.html", "faq.html", "privacy.html"):
    t = text(f)
    print("=====", f, len(t))
    for m in re.finditer(r"(?i)[^.\n]*(every \d+ minutes|about every|corrections?\b|report a wrong|email|contact|your browser contacts|rebuild)[^.\n]*\.", t):
        print(" -", m.group(0).strip()[:260])
