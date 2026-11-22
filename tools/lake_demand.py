"""Order the lake queue by demand: Wikipedia page views (12 months) of each queued lake -> data/waves.csv score + wikipedia_views_12m.
Why: every queued lake had score 0, so the daily release took lakes by gauge number (Maine ponds before Lake Mendota) and earned nothing (owner 2026-11-21: money first).
A lake with no matching article keeps a small score (UNKNOWN), not zero: unknown is not zero. Only status=queue rows of kind lake are touched; all others stay byte-for-byte.
Usage: python -I tools/lake_demand.py [--dry]
"""
import csv, json, math, os, re, sys, time, urllib.error, urllib.parse, urllib.request
FAILS = []  # calls that failed after every retry (not a 404): a rerun during a Wikimedia outage must never overwrite real view counts
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lib.directory import STATE_NAMES

WAVES = os.path.join(ROOT, "data", "waves.csv")
UA = {"User-Agent": "riverwaterlevels.com lake demand (planning only)"}
START, END = "20251101", "20261031"
UNKNOWN = 15.0  # no article found: below any known lake with real views, above zero


def get(url):
    for i in range(6):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(3 * (i + 1))
        except Exception:
            time.sleep(3 * (i + 1))
    FAILS.append(url)
    return None


def title_views(title):
    t = urllib.parse.quote(title.replace(" ", "_"), safe="")
    j = get("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/%s/monthly/%s/%s" % (t, START, END))
    time.sleep(0.25)
    return sum(x["views"] for x in j["items"]) if j and j.get("items") else None


def has_word(w, text):
    return re.search(r"\b" + re.escape(w.lower()) + r"\b", text) is not None


def resolve(name, st):
    """-> (title, views) of the lake's article, else (None, None). The article must name the state and be a lake, reservoir or sea."""
    state = STATE_NAMES.get(st, st)
    for cand in ("%s (%s)" % (name, state), name):
        j = get("https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(cand.replace(" ", "_"), safe=""))
        time.sleep(0.25)
        if not j or j.get("type") == "disambiguation":
            continue
        text = ((j.get("description") or "") + " " + (j.get("extract") or "")).lower()
        if has_word(state, text) and any(has_word(w, text) for w in ("lake", "reservoir", "sea", "lagoon")):  # whole words: 'kansas' is not in 'arkansas', 'sea' not in 'season' (Opus review)
            t = (j.get("titles") or {}).get("canonical") or cand
            return t, title_views(t)
    return None, None


def score(v):
    return round(min(100.0, 100.0 * math.log10(v) / 6.2), 1) if v and v > 0 else UNKNOWN


def selftest():
    assert score(None) == UNKNOWN and score(0) == UNKNOWN and score(1_200_000) == 98.1 and score(10 ** 7) == 100.0 and score(100) < score(10_000), "lake_demand score"
    assert has_word("Kansas", "a lake in arkansas") is False and has_word("Virginia", "in west virginia") is True and has_word("sea", "season") is False and has_word("sea", "a salt sea in california") is True, "whole-word match"
    print("lake_demand selftest OK")


def main():
    rows = list(csv.reader(open(WAVES, encoding="utf-8", newline="")))
    h = rows[0]
    ix = {k: h.index(k) for k in ("status", "site", "river", "state", "score", "wikipedia_views_12m", "signals")}
    todo = [i for i, r in enumerate(rows[1:], 1) if r[ix["status"]] == "queue" and "lake" in r[ix["signals"]].split(",")]
    print("queued lakes", len(todo), flush=True)
    with ThreadPoolExecutor(3) as ex:
        got = list(ex.map(lambda i: resolve(rows[i][ix["river"]], rows[i][ix["state"]]), todo))
    n_found = 0
    for i, (t, v) in zip(todo, got):
        rows[i][ix["score"]] = str(score(v))
        rows[i][ix["wikipedia_views_12m"]] = "" if v is None else str(v)
        n_found += v is not None
    print("found", n_found, "unknown", len(todo) - n_found)
    if FAILS:
        print("REFUSED: %d calls failed after every retry (not a 404); nothing written, rerun later" % len(FAILS))
        return
    top = sorted(((score(v), rows[i][ix["river"]], rows[i][ix["state"]], v) for i, (t, v) in zip(todo, got)), reverse=True)[:25]
    for x in top:
        print(" ", x)
    if "--dry" not in sys.argv:
        with open(WAVES, "w", encoding="utf-8", newline="") as f:
            csv.writer(f, lineterminator="\n").writerows(rows)


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main()
