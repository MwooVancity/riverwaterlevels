# Report scan: every row of waves.csv against USGS latest and NWS list, every live page against text and structure checks.
import sys, os as _o; sys.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
import csv, collections as C, datetime as D, gzip, json, os, re, sys, html
from txt import text
sys.stdout.reconfigure(encoding="utf-8")
S = "C:/Users/mwoo7/Desktop/riverwaterlevels/runs/quarter/"
R = "C:/Users/mwoo7/Desktop/riverwaterlevels/"
now = D.datetime.now(D.timezone.utc)
rows = list(csv.DictReader(open(R + "data/waves.csv", encoding="utf-8")))
pa = {r["site"]: r for r in csv.DictReader(open(R + "data/pages-all.csv", encoding="utf-8"))}
inv = {r["site"]: r for r in csv.DictReader(open(R + "data/inventory-ranked.csv", encoding="utf-8"))}
latest = json.load(open(S + "latest.json"))
nw = json.load(open(S + "nwps.json"))
nw = {g["lid"]: g for g in (nw["gauges"] if isinstance(nw, dict) else nw)}


def age_h(t):
    try:
        return (now - D.datetime.fromisoformat(t.replace("Z", "+00:00"))).total_seconds() / 3600
    except Exception:
        return None


def tags(r):
    s = r["site"]
    a = pa.get(s, {})
    i = inv.get(s, {})
    raw = (a.get("raw_name") or i.get("name") or "").upper()
    st = r["state"]
    l = latest.get(s, {})
    f, h = l.get("00060"), l.get("00065")
    t = set()
    fa = age_h(f[1]) if f else None
    ha = age_h(h[1]) if h else None
    best = min([x for x in (fa, ha) if x is not None], default=None)
    if not l:
        t.add("no latest reading at all")
    if not f:
        t.add("no flow value in latest")
    if not h:
        t.add("no gage height value in latest")
    if f and h is None:
        t.add("flow only, USGS")
    if h and not f:
        t.add("stage only, USGS")
    if fa is not None and fa > 24:
        t.add("flow older than 24 h")
    if fa is not None and fa > 24 * 8:
        t.add("flow older than 8 days")
    if fa is not None and fa > 24 * 365:
        t.add("flow older than 1 year")
    if best is not None and best > 24 * 8:
        t.add("all readings older than 8 days")
    for x in (f, h):
        if x and x[2]:
            for q in (x[2] if isinstance(x[2], list) else [x[2]]):
                t.add("qualifier " + str(q))
    if f:
        try:
            v = float(f[0])
            if v < 0:
                t.add("negative flow now")
            if v == 0:
                t.add("zero flow now")
        except Exception:
            t.add("flow not a number")
    if re.search(r"\bTIDAL|TIDE\b", raw):
        t.add("name says tidal")
    if re.search(r"\b(CANAL|DITCH|DRAIN|DIVERSION|FLUME|AQUEDUCT|TUNNEL|PIPELINE|LATERAL|SPILLWAY|POWERPLANT|POWER PLANT)\b", raw):
        t.add("name says canal or ditch etc")
    if re.search(r"\b(DAM|RESERVOIR|LOCK|POWERHOUSE)\b", raw):
        t.add("name says dam, reservoir or lock")
    if st in ("AK", "HI", "PR", "VI", "GU", "AS", "MP"):
        t.add("state " + st)
    if st in ("AK", "ME", "VT", "NH", "NY", "MI", "WI", "MN", "ND", "SD", "MT", "WY", "ID", "IA", "NE"):
        t.add("cold state, ice likely in winter")
    lid = (i.get("nws_lid") or a.get("nws_lid") or "").strip()
    if not lid:
        t.add("no NWS forecast point in our data")
    else:
        g = nw.get(lid)
        if not g:
            t.add("NWS point id not in NWS list")
        else:
            o, c = g["status"]["observed"], g["status"]["forecast"]
            if o.get("floodCategory") in ("not_defined", "no_data", "obs_not_current", "out_of_service"):
                t.add("NWS observed " + o.get("floodCategory"))
            if c.get("floodCategory") in ("fcst_not_current", "not_defined", "no_data"):
                t.add("NWS forecast none")
            if o.get("floodCategory") in ("action", "minor", "moderate", "major"):
                t.add("NWS now at " + o.get("floodCategory"))
    if a.get("years_record", "").isdigit() and int(a["years_record"]) < 5:
        t.add("record under 5 years")
    if r.get("name_confidence") not in ("high",):
        t.add("name confidence " + str(r.get("name_confidence")))
    if re.search(r"\b(NR|AB|BL|ABV|BLW|CR|HWY|R|TRIB)\b|\d{4,}", r["place"] + " " + r["river"], re.I):
        t.add("abbreviation or number in shown name")
    return t


by = C.defaultdict(C.Counter)
ex = C.defaultdict(list)
for r in rows:
    for t in tags(r):
        by[t][r["status"]] += 1
        if len(ex[t]) < 3 and r["status"] in ("live", "queue"):
            ex[t].append(r["site"] + " " + r["river"] + " / " + r["place"])
print("status", C.Counter(r["status"] for r in rows))
print("%-46s %5s %6s %5s %6s  example" % ("tag", "live", "queue", "held", "excl"))
for t in sorted(by, key=lambda x: -by[x]["queue"]):
    b = by[t]
    print("%-46s %5d %6d %5d %6d  %s" % (t, b["live"], b["queue"], b["held-names"], b["excluded"], "; ".join(ex[t][:2])[:90]))
rc = C.Counter(r["river"] + "|" + r["state"] for r in rows if r["status"] in ("live", "queue"))
print("rivers", len(rc), "with 2+ gauges", sum(1 for v in rc.values() if v > 1), "gauges on those", sum(v for v in rc.values() if v > 1))
print("state top queue", C.Counter(r["state"] for r in rows if r["status"] == "queue").most_common(8))
print("excluded reasons", C.Counter((r.get("gate") or "?")[:30] for r in rows if r["status"] == "excluded").most_common(8))

# live pages
print("\n=== LIVE PAGES")
D_ = S + "live/"
pages = {}
for f in os.listdir(D_):
    if not f.startswith("river_"):
        continue
    h = open(D_ + f, encoding="utf-8").read()
    m = re.search(r"USGS gauge (\d{8,15})", h) or re.search(r"\(USGS (\d{8,15})\)", h)
    if m and "<h1" in h and "/water" not in f:
        pages[f] = (m.group(1), h, text(f))
print("gauge pages", len(pages), "others", len([f for f in os.listdir(D_) if f.startswith('river_')]) - len(pages))
CH = {
    "verdict word safe": r"\bsafe(?:ly|r)?\b",
    "verdict words good/ideal/recommended": r"\b(ideal|recommended|good conditions|runnable|fishable|floatable|dangerous)\b",
    "says provisional": r"provisional",
    "says Not issued": r"Not issued",
    "says Unknown": r"\bUnknown\b",
    "says not reporting": r"not reporting",
    "has flood stages": r"Action stage",
    "no flood stages line": r"no flood stage|not (?:set|defined|published).{0,30}flood|No NWS flood",
    "active alert banner": r"(Flood|River|Flash).{0,30}(Warning|Watch|Advisory|Statement)",
    "no active alerts": r"No active NWS alerts",
    "tidal words": r"\btid(?:e|al)\b",
    "dams upstream line": r"dams? upstream",
    "regulated line": r"regulat|controlled by|dam release|releases",
    "ice words": r"\bice\b",
    "gauge is not your stretch": r"at this gauge only|only at|not your|miles (?:up|down)stream|one point|this point",
    "turn around / 911": r"[Tt]urn around|\b911\b",
    "water temp tile": r"Water temperature \d",
    "camera": r"[Cc]amera",
    "cold water warn": r"cold water|hypothermia",
    "E. coli / bacteria": r"E\. coli|bacteria",
    "gage spelled gage height": r"Gage height",
    "dash in hero": r"Gage height\s*[–—-]\s*(ft)?\s",
    "normal range label": r"Normal range",
    "below normal label": r"Below normal|Much below",
    "above normal label": r"Above normal|Much above",
    "no statistics": r"no published statistics|No statistics",
}
cnt = C.Counter()
exm = C.defaultdict(list)
for f, (s, h, t) in pages.items():
    for k, p in CH.items():
        if re.search(p, t):
            cnt[k] += 1
            if len(exm[k]) < 2:
                m = re.search(p, t)
                exm[k].append(s + ": " + t[max(0, m.start() - 50):m.end() + 50].replace("\n", " "))
for k in CH:
    print("%-40s %3d/%d  %s" % (k, cnt[k], len(pages), " | ".join(exm[k][:1])[:150]))
B = C.Counter()
sz = []
th = C.Counter()
for f, (s, h, t) in pages.items():
    sz.append(len(gzip.compress(h.encode())))
    for k, p in {"lang=en": r'<html[^>]+lang="en"', "viewport": "name=\"viewport\"", "skip link": "Skip to content", "print css": "@media print", "og:image": "og:image", "manifest": "rel=\"manifest\"", "service worker": "serviceWorker", "share api": "navigator.share", "noscript": "<noscript", "svg role img": "role=\"img\"", "img no alt": r"<img(?![^>]*\balt=)", "mailto": "mailto:", "json-ld": "application/ld\\+json", "time tag": "<time", "tel": "tel:", "hreflang": "hreflang"}.items():
        if re.search(p, h):
            B[k] += 1
    for u in re.findall(r"""<script[^>]+src=["']([^"']+)""", h):
        th[re.sub(r"\?.*", "", u)[:60]] += 1
    for u in re.findall(r"""createElement\(["']script["']\).{0,160}?src\s*=\s*["']([^"']+)""", h, re.S):
        th["dyn " + u[:60]] += 1
print(B)
print("gz KB min/med/max", round(min(sz) / 1000), round(sorted(sz)[len(sz) // 2] / 1000), round(max(sz) / 1000))
print("scripts", th.most_common(8))
print("pub", open(R + "data/publisher.json", encoding="utf-8").read()[:300])
