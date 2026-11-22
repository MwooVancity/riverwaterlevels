"""Order the lake queue by demand: Wikipedia page views (12 months) of each queued lake -> data/waves.csv score + wikipedia_views_12m.
Why: every queued lake had score 0, so the daily release took lakes by gauge number (Maine ponds before Lake Mendota) and earned nothing (owner 2026-11-21: money first).
A lake with no matching article keeps a small score (UNKNOWN), not zero: unknown is not zero. Only status=queue rows of kind lake are touched; all others stay byte-for-byte.
Usage: python -I tools/lake_demand.py [--dry]
"""
import csv, json, math, os, re, sys, time, urllib.error, urllib.parse, urllib.request
import threading
FAILED = set()  # threads whose current lake had a failed call
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
    FAILED.add(threading.get_ident())
    return None


def title_views(title):
    t = urllib.parse.quote(title.replace(" ", "_"), safe="")
    j = get("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/%s/monthly/%s/%s" % (t, START, END))
    time.sleep(0.6)
    return sum(x["views"] for x in j["items"]) if j and j.get("items") else None


def has_word(w, text):
    return re.search(r"\b" + re.escape(w.lower()) + r"\b", text) is not None


def resolve(name, st):
    FAILED.discard(threading.get_ident())
    t, v = _resolve(name, st)
    return t, v, threading.get_ident() in FAILED


def _resolve(name, st):
    """-> (title, views) of the lake's article, else (None, None). The article must name the state and be a lake, reservoir or sea."""
    state = STATE_NAMES.get(st, st)
    cands = ["%s (%s)" % (name, state), name]
    for cand in cands:
        t = match(cand, state)
        if t:
            return t, title_views(t)
    # a search-API rescue was tried 2026-11-21 and dropped: it matched the wrong lake (Hubbard Creek Reservoir took Lake Ray Hubbard's views, Chambers Lake PA got 1.38M); a wrong high score is worse than UNKNOWN
    return None, None


def match(cand, state):
    """canonical title if the article for cand names the state and is a lake, reservoir or sea, else None."""
    if not cand:
        return None
    j = get("https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(cand.replace(" ", "_"), safe=""))
    time.sleep(0.6)
    if not j or j.get("type") == "disambiguation":
        return None
    text = ((j.get("description") or "") + " " + (j.get("extract") or "")).lower()
    if has_word(state, text) and any(has_word(w, text) for w in ("lake", "reservoir", "sea", "lagoon")):  # whole words: 'kansas' is not in 'arkansas', 'sea' not in 'season' (Opus review)
        return (j.get("titles") or {}).get("canonical") or cand
    return None


def score(v):
    return round(min(100.0, 100.0 * math.log10(v) / 6.2), 1) if v and v > 0 else UNKNOWN


def norm(n):
    return re.sub(r"[^a-z0-9 ]", "", n.lower()).strip()


def tier_of(name, T):
    """Keyword Planner band of the lake's level searches (data/keyword-tiers-water.csv, 'X water level' phrasings only), or None when the file has no row for the name."""
    n = norm(name)
    base = re.sub(r"^lake | lake$| reservoir$", "", n)
    groups = [  # the lake's own phrasing wins whenever the file has a row for it (Opus review: 'pleasant lake' = 0 must not take 'lake pleasant' = 5000, a lake in Arizona)
        [n],
        [re.sub(r"\b([a-z]) (?=[a-z]\b)", r"\1", n)],  # 'lake j b thomas' -> 'lake jb thomas'
        [base + " lake", "lake " + base, base + " reservoir", base],  # only then the other lake-word forms
    ]
    for g in groups:
        ks = [f + s for f in g for s in (" water level", " level", " water levels", " levels") if f + s in T]
        if ks:
            return max(T[k] for k in ks)
    return None


NO_ROW = 17.0  # no Keyword Planner row at all: unknown is not zero (below the 50 band at 34, above a measured 0)


def final(tier, views):
    """Keyword Planner first (owner 2026-11-22: 'the only thing that matters'): band = 20 * log10(tier + 1) (50 -> 34, 500 -> 54, 5000 -> 74), Wikipedia views only break ties inside a band (max +9); no row = NO_ROW."""
    base = NO_ROW if tier is None else 20 * math.log10(tier + 1)
    return round(base + (score(views) if views else 0.0) * 0.09, 1)


def selftest():
    assert final(5000, None) > final(500, 10 ** 7) > final(50, 10 ** 7) > final(50, None) > final(None, 10 ** 7) > final(0, None) and final(None, None) == NO_ROW, "keyword band beats Wikipedia views; no row is not zero"
    P = {"pleasant lake water level": 0, "lake pleasant water level": 5000, "lake fork water level": 5000, "cedar creek lake water level": 5000, "lake jb thomas water level": 500}
    assert tier_of("Pleasant Lake", P) == 0 and tier_of("Lake Fork Reservoir", P) == 5000 and tier_of("Cedar Creek Reservoir", P) == 5000 and tier_of("Lake J. B. Thomas", P) == 500, "exact name wins; bare, swapped and initials forms fall back"
    assert tier_of("Lake Toledo Bend", {"lake toledo bend water level": 5000}) == 5000 and tier_of("Toledo Bend Reservoir", {"lake toledo bend water level": 5000}) == 5000 and tier_of("Nope Lake", {}) is None, "tier_of forms"
    assert score(None) == UNKNOWN and score(0) == UNKNOWN and score(1_200_000) == 98.1 and score(10 ** 7) == 100.0 and score(100) < score(10_000), "lake_demand score"
    assert has_word("Kansas", "a lake in arkansas") is False and has_word("Virginia", "in west virginia") is True and has_word("sea", "season") is False and has_word("sea", "a salt sea in california") is True, "whole-word match"
    print("lake_demand selftest OK")


def main():
    rows = list(csv.reader(open(WAVES, encoding="utf-8", newline="")))
    h = rows[0]
    ix = {k: h.index(k) for k in ("status", "site", "river", "state", "score", "wikipedia_views_12m", "signals")}
    todo = [i for i, r in enumerate(rows[1:], 1) if r[ix["status"]] == "queue" and "lake" in r[ix["signals"]].split(",") and ("--all" in sys.argv or not r[ix["wikipedia_views_12m"]])]  # incremental: a lake that already has views keeps them (an outage never wipes them)
    if "--tier-only" in sys.argv:
        todo = []  # no Wikipedia calls: only re-score from Keyword Planner bands and the views already stored
    print("lakes to look up", len(todo), flush=True)
    with ThreadPoolExecutor(2) as ex:
        got = list(ex.map(lambda i: resolve(rows[i][ix["river"]], rows[i][ix["state"]]), todo))
    n_found = n_failed = 0
    done = []
    for i, (t, v, failed) in zip(todo, got):
        if failed:  # a lookup that hit a failed call keeps its row untouched; the next incremental run retries it (an outage never writes a false 'unknown')
            n_failed += 1
            continue
        rows[i][ix["score"]] = str(score(v))
        rows[i][ix["wikipedia_views_12m"]] = "" if v is None else str(v)
        n_found += v is not None
        done.append((i, v))
    print("found", n_found, "unknown", len(done) - n_found, "left for a rerun (failed calls)", n_failed)
    top = sorted(((score(v), rows[i][ix["river"]], rows[i][ix["state"]], v) for i, v in done), reverse=True)[:25]
    for x in top:
        print(" ", x)
    T = {r["keyword"].lower(): int(float(r["tier"] or 0)) for r in csv.DictReader(open(os.path.join(ROOT, "data", "keyword-tiers-water.csv"), encoding="utf-8"))}
    missing = []
    for r in rows[1:]:
        if r[ix["status"]] == "queue" and "lake" in r[ix["signals"]].split(","):
            t = tier_of(r[ix["river"]], T)
            if t is None:
                missing.append(r[ix["river"]] + " " + r[ix["state"]])
            v = r[ix["wikipedia_views_12m"]]
            r[ix["score"]] = str(final(t, int(v) if v else None))
    print("queued lakes with no Keyword Planner row at all (need a run):", len(missing), missing)
    if "--dry" not in sys.argv:
        with open(WAVES, "w", encoding="utf-8", newline="") as f:
            csv.writer(f, lineterminator="\n").writerows(rows)


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main()
