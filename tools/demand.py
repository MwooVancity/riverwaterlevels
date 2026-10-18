"""Planning tool (not part of the site build): demand proxy for the rollout order.
For every river name in pages-all.csv, find its English Wikipedia article and sum 12 months of page views. Unknown (no article found) is NOT zero: it is left blank and scored by the fallback.
Output: data/demand.csv (river, state, title, views_12m, status). Resumable: rows already in the file are kept. Usage: python -I tools/demand.py
"""
import os, sys, csv, json, time, urllib.parse, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lib.directory import STATE_NAMES

PAGES = r"C:\Users\mwoo7\Desktop\calcscrape\docs\research\prototypes\data\pages-all.csv"
OUT = os.path.join(ROOT, "data", "demand.csv")
UA = {"User-Agent": "riverwaterlevels.com demand-test (planning only)"}
END, START = "20260930", "20251001"


def get(url):
    for i in range(4):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 * (i + 1))
        except Exception:
            time.sleep(2 * (i + 1))
    return None


def summary(title):
    j = get("https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_"), safe=""))
    time.sleep(0.12)
    return j


def views(title):
    j = get("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/%s/monthly/%s/%s" % (urllib.parse.quote(title.replace(" ", "_"), safe=""), START, END))
    time.sleep(0.12)
    return sum(x["views"] for x in j["items"]) if j and j.get("items") else None


def resolve(river, st):
    state = STATE_NAMES.get(st, st)
    for cand in ("%s (%s)" % (river, state), river):
        s = summary(cand)
        if not s or s.get("type") == "disambiguation":
            continue
        text = ((s.get("description") or "") + " " + (s.get("extract") or "")).lower()
        if state.lower() in text or ("%s" % st.lower()) in text.split():
            t = (s.get("titles") or {}).get("canonical") or cand
            return t, views(t)
    return None, None


def main():
    from concurrent.futures import ThreadPoolExecutor
    seen = {}
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")):
            seen[(r["river"], r["state"])] = r
    names = sorted({(r["river"], r["state"]) for r in csv.DictReader(open(PAGES, encoding="utf-8")) if r["name_confidence"] != "low"})
    todo = [n for n in names if n not in seen]
    print("rivers", len(names), "to look up", len(todo), flush=True)
    new = not os.path.exists(OUT)
    with open(OUT, "a", newline="", encoding="utf-8") as f, ThreadPoolExecutor(8) as ex:
        w = csv.writer(f)
        if new:
            w.writerow(["river", "state", "title", "views_12m", "status"])
        for i, ((river, st), (t, v)) in enumerate(zip(todo, ex.map(lambda n: resolve(*n), todo))):
            w.writerow([river, st, t or "", "" if v is None else v, "found" if v is not None else "unknown"])
            if i % 100 == 0:
                f.flush()
                print(i, river, st, t, v, flush=True)


main()
