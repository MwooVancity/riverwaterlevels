"""Add the next gauges from the priority list to the site, in one command.
Usage: python -I tools/release.py N [--dry] [--list docs/research/priority/picks.csv]
Steps: pick the first N rows of the list that have no cache yet -> mark them live in data/waves.csv -> python -I collect.py <sites> (full) -> python -I build.py
-> print the new page URLs. A new page stays out of Google until `tools/open_wave.py N --apply` lists it. --dry prints the picks and stops.
"""
import os, sys, csv, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
args = [a for a in sys.argv[1:] if not a.startswith("--")]
n = int(args[0]) if args else 25
lst = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--list=")), os.path.join(ROOT, "docs", "research", "priority", "picks.csv"))
dry = "--dry" in sys.argv
PY = [sys.executable, "-I"]

cached = {f[:-5] for f in os.listdir(os.path.join(ROOT, "cache")) if f.endswith(".json")}
live_ = {r["site"]: r for r in csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8"))}
picks = [r for r in csv.DictReader(open(lst, encoding="utf-8")) if live_.get(r["site"], {}).get("status") == "queue" and not live_.get(r["site"], {}).get("gate")] if os.path.exists(lst) else []
seen_ = {r["site"] for r in picks}
picks += sorted((dict(r, category=r.get("activity") or "") for r in live_.values() if r["status"] == "queue" and not r.get("gate") and r["site"] not in seen_),
                key=lambda r: -float(r.get("score") or 0))  # after the owner's list: the scored queue, best first
# one ranking (owner 2026-11-03, HARD): highest search tier first, any country. US rows get their tier from the queue; world rows come
# matched to a real station by tools/world_match.py. A world gauge is a data row in data/world-pages.json; the refresh collects and builds
# it, and lib/world.py choose holds any page that fails, so nothing unproven ships.
WORLD_MAX = 400  # ponytail: world feeds are fetched one gauge at a time on shard 0; past about 500 that job nears its hour. Split the world fetch first.
import json as _json
q_ = list(csv.DictReader(open(os.path.join(ROOT, "data", "world-queue.csv"), encoding="utf-8")))
# keyword debate 2026-11-06: the first gauge on a keyword gets its whole search band, every other gauge 5% (one gauge per river first);
# an equal split put 15 Guadalupe gauges below 250-search creeks. A row naming several countries ("AU|CA|FR|GB") gets nothing until one is chosen.
live_kw = {r["keyword"] for r in q_ if r["gauge"] and live_.get(r["gauge"], {}).get("status") == "live"}
first_ = {}
for r in q_:
    if r["keyword"] and r["gauge"] and r["keyword"] not in live_kw:
        first_.setdefault(r["keyword"], r["gauge"])
def share(t, k, g=None):
    return 0 if not k else int(t or 0) * (1 if k not in live_kw and first_.get(k, g) == g else 0.05)  # a world row is the first gauge when no US gauge holds the keyword
tier_ = {r["gauge"]: (0 if "|" in (r.get("country") or "") else share(r["tier"], r["keyword"], r["gauge"])) for r in q_ if r["gauge"]}
wpp = os.path.join(ROOT, "data", "world-pages.json")
wpages = _json.load(open(wpp, encoding="utf-8"))
from lib import world as _world
thin_ = _world.live_thin()
held_before_ = _json.dumps([p.get("held") for p in wpages])
gone_ = _world.drop_held(wpages, thin_, __import__("datetime").date.today().isoformat())  # a hold older than 7 days frees its WORLD_MAX slot and is never re-added
for s_ in gone_:
    print("  world  dropped %s after %d days held" % (s_, _world.DROP_DAYS))
listed = {s for p in wpages for s in p.get("gauge_pages") or []}
wr = os.path.join(ROOT, "data", "world-ready.csv")
ready = [w for w in csv.DictReader(open(wr, encoding="utf-8")) if w["station"] not in listed and not any(w["station"] in (p.get("dropped") or {}) for p in wpages)] if os.path.exists(wr) else []
room_, fits = {}, []
for w in ready:  # a feed missing a proof adds nothing; a feed whose every listed gauge was held thin adds nothing (lib/world.py room), so thin pages never eat the 25 a day
    room_.setdefault(w["feed"], _world.room(w["feed"], wpages, thin_))
    if room_[w["feed"]] > 0:
        room_[w["feed"]] -= 1
        fits.append(w)
ready = fits
ready = ready[:max(0, WORLD_MAX - len(listed))]
# money first (owner 2026-11-03): searches x ad rate per country. Guesses from PLAN.md until AdSense reports ours; US 1.0.
RATE = {"eccc": 0.8, "ea": 0.8, "pegelonline": 0.8}
both = sorted([(-tier_.get(r["site"], 0), 1, i, r) for i, r in enumerate(picks)] + [(-share(w["tier"], w["keyword"], w["station"]) * RATE.get(w["feed"], 0.1), 0, j, w) for j, w in enumerate(ready)], key=lambda x: x[:3])[:n]  # a tie goes to the world row
world_add = [x[3] for x in both if x[1] == 0]
picks = [x[3] for x in both if x[1] == 1]
if world_add or gone_ or held_before_ != _json.dumps([p.get("held") for p in wpages]):
    for w in world_add:
        page = next(p for p in wpages if p["slug"] == w["page"])
        for k in ("stations", "gauge_pages"):
            page.setdefault(k, []).append(w["station"])
        rec_ = _world.recorded(wpages).get(page.get("feed", "pegelonline"))
        if rec_ and not page.get("proof") and not (_world.PROVED.get(page.get("feed", "pegelonline")) or {}).get("alerts"):
            page["proof"] = rec_  # the proof that opened this country is committed with its first gauge: a lost cache can never relock it
            print("  proof committed with it: %s" % str(rec_.get("alerts"))[:160])
        print("  world  %s  %s  (%s, tier %s)" % (w["station"], w["title"], w["keyword"], w["tier"]))
    if not dry:
        raw = open(wpp, encoding="utf-8", newline="").read()
        nl_ = "\r\n" if "\r\n" in raw else "\n"
        open(wpp, "w", encoding="utf-8", newline="").write("[" + nl_ + ("," + nl_).join(" " + _json.dumps(x, ensure_ascii=False) for x in wpages) + nl_ + "]" + nl_)
    print("world gauges added: %d (the refresh collects and builds them; a page that fails is held, never shown)" % len(world_add))
    if not picks:
        sys.exit(0)
for r in picks:
    r["url"] = r.get("url") or (live_.get(r["site"]) or {}).get("url")  # picks.csv holds the order, waves.csv the address: a pick with no address once sent the whole day back
if not picks and not world_add:
    sys.exit("nothing to add: every gauge in %s already has a cache" % lst)
print("adding %d gauges:" % len(picks))
for r in picks:
    print("  %s  %s at %s, %s  (%s)" % (r["site"], r["river"], r["place"], r["state"], r["category"]))
if dry:
    sys.exit(0)

# bookkeeping: data/waves.csv status queue -> live for these sites
wp = os.path.join(ROOT, "data", "waves.csv")
rows = list(csv.DictReader(open(wp, encoding="utf-8")))
sites = {r["site"] for r in picks}
for r in rows:
    if r["site"] in sites and r["status"] == "queue":
        r["status"] = "live"
with open(wp, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

subprocess.call(PY + [os.path.join(ROOT, "tools", "fetch_stats.py")] + sorted(sites), cwd=ROOT)  # wave 3: "is this normal" blank because new gauges had no stats file
rc = subprocess.call(PY + [os.path.join(ROOT, "collect.py")] + sorted(sites), cwd=ROOT)
if rc:
    sys.exit("collect failed (%d); nothing built" % rc)
import json
dead = set()
for s_ in sorted(sites):  # practice run 2026-10-29: Arkansas at Parkdale and Snake at Hells Canyon returned no USGS rows; they go back to the queue with a gate so tomorrow picks others
    try:
        c_ = json.load(open(os.path.join(ROOT, "cache", s_ + ".json"), encoding="utf-8"))
        ok_ = isinstance(c_, dict) and bool((c_.get("usgs") or {}).get("rows") if isinstance(c_.get("usgs"), dict) else c_.get("usgs"))
    except (OSError, ValueError):
        ok_ = False
    if not ok_:
        dead.add(s_)
if dead:
    rows = list(csv.DictReader(open(wp, encoding="utf-8")))
    for r in rows:
        if r["site"] in dead:
            r["status"], r["gate"] = "queue", "no-usgs-rows"
    with open(wp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("not released (no USGS readings): %s" % ", ".join(sorted(dead)))
    picks = [r for r in picks if r["site"] not in dead]
subprocess.call(PY + [os.path.join(ROOT, "tools", "sync_legacy.py")], cwd=ROOT)  # CI builds from the repo: the new gauges' daily stats must be committed with the wave (push legacy/ too)
rc = subprocess.call(PY + [os.path.join(ROOT, "build.py")], cwd=ROOT)
if rc:
    sys.exit("build failed (%d)" % rc)


def page_check(picks_):
    """{site: first message} for each new gauge whose built page fails check.py's page checks (the same functions the site gate runs per page)."""
    os.chdir(ROOT)
    ck = {"__file__": os.path.join(ROOT, "check.py"), "__name__": "check"}
    exec(compile(open("check.py", encoding="utf-8").read().rsplit("\nmain()", 1)[0], "check.py", "exec"), ck)
    out = {}
    for r in picks_:
        u = r.get("url")
        f = os.path.join(ROOT, "dist_next", u.strip("/").replace("/", os.sep), "index.html") if u else ""
        if not f or not os.path.exists(f):
            out[r["site"]] = "no built page at %s" % u
            continue
        h = open(f, encoding="utf-8").read().replace("\u00a0", " ")  # as check_dir reads it (times use no-break spaces)
        bad = ck["check_html"](h, os.path.relpath(f, os.path.join(ROOT, "dist_next"))) + ck["rank_checks"](h, u) + ck["hater_rules"](h)
        if bad:
            out[r["site"]] = bad[0]
    return out


def truth_check(picks_):
    """{site: message} for each new gauge that breaks a truth contract (truth_tests.py, per-gauge contracts only): the same rules the gate runs, so the gate never meets a failure the release could have sent back."""
    import truth_tests
    truth_tests.bad.clear()
    truth_tests.main(only={r["site"] for r in picks_})
    out = {}
    for b_ in truth_tests.bad:
        site_, _, msg_ = b_.partition(": ")
        out.setdefault(site_, "truth: " + msg_)
    return out


failed = page_check(picks)  # robustness (owner 2026-10-29): one bad page must never block the day's release; it goes back to the queue with its reason and the rest ship
for s_, m_ in truth_check([r for r in picks if r["site"] not in failed]).items():
    failed[s_] = m_
if failed:
    rows = list(csv.DictReader(open(wp, encoding="utf-8")))
    for r in rows:
        if r["site"] in failed:
            r["status"], r["gate"] = "queue", (failed[r["site"]] if failed[r["site"]].startswith("truth: ") else "page-check: " + failed[r["site"]]).replace("\n", " ")[:300]
    with open(wp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    for s_, m_ in sorted(failed.items()):
        print("not released (%s): %s  %s" % ("truth contract" if m_.startswith("truth: ") else "page check", s_, m_))
    picks = [r for r in picks if r["site"] not in failed]
    rc = subprocess.call(PY + [os.path.join(ROOT, "build.py")], cwd=ROOT)
    if rc:
        sys.exit("rebuild failed (%d)" % rc)
urls = [r["url"] for r in picks if r.get("url")]
if not urls:
    sys.exit("released nothing: every pick was sent back")  # a day with no new gauge must fail, never log every gate passed
print("\nbuilt: %d new page(s). Now: push (deploys), python -I tools/open_wave.py %d --apply, push again." % (len(urls), len(urls)))
