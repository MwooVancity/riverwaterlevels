"""Site doctor (gate 3 health, owner 2026-10-25: "no alarms"): reads the LIVE site, prints one health report, heals what it can, never fails.
Run hourly by .github/workflows/watchdog.yml and by hand at session start: python -I tools/watchdog.py
Heals: site not rebuilt for 60 min -> asks for a refresh (heal=refresh in $GITHUB_OUTPUT; the workflow dispatches it unless one is already
queued).
Reports (cannot heal, read at session start): live gauges missing from the site, sources that stopped working (hours since last_ok_at),
numbers not verified against USGS, a stale edge answer, and Googlebot getting a different page than a phone (no cloaking, ever).
At most one USGS call (the edge's own per-gauge fetch, when its 3-min cache is cold)."""
import csv, json, os, socket, sys, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lib.common import http_open
from lib.source_list import UNIVERSAL
from tools.worker_load import LIMIT, REQUESTS, load

SITE = "https://riverwaterlevels.com"
UA = {"User-Agent": "Mozilla/5.0 (rwl-doctor)"}
REBUILD_MIN = 120     # the Worker rebuilds on the hour only when the last build is over 40 min old, so up to about 112 min apart is healthy (2026-11-03: 60 alarmed a healthy site)
EDGE_MAX_S = 1800     # the cron writes only when a reading changed; 30 min with no write means the poll stopped
# a source that has not worked for this long is reported dead: 3 h for the hourly sources, 30 h for once-a-day sources
HOURLY = {"usgs", "nws", "rain", "wpc", "nwps"}


def get(path, raw=False):
    r = http_open(SITE + path, UA, 30)
    return r if raw else json.load(r)


def hours_since(iso):
    return (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))).total_seconds() / 3600


def release_stall():
    """A line when the daily release has added nothing for 3 days while gauges wait; its skips only ever reached the log."""
    with open(os.path.join(ROOT, "data", "last-release.txt")) as f:
        last = datetime.date.fromisoformat(f.read().strip())
    days = (datetime.datetime.now(datetime.timezone.utc).date() - last).days
    with open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8") as f:
        waiting = sum(1 for r in csv.DictReader(f) if r["status"] == "queue" and not r["gate"])
    return "no new gauges released for %d days, %d waiting" % (days, waiting) if days >= 3 and waiting else None


def world_short(s):
    """A line when a world page lacks a block its data allows, or a quarter of listed gauges are held back (5 of 38 today: 4 Austrian gauges with no coordinates, 1 near-duplicate)."""
    w = s.get("world") or {}
    gaps, held = w.get("gaps") or {}, (w.get("listed") or 0) - (w.get("shown") or 0)
    if gaps or held * 4 > (w.get("listed") or 0):
        return "pages missing blocks: %d gauges short, %d held of %s: %s" % (len(gaps), held, w.get("listed"), "; ".join("%s lacks %s" % (k, ", ".join(v)) for k, v in list(gaps.items())[:5]))


def main():
    ok, bad, heal = [], [], []
    out_ = os.environ.get("GITHUB_OUTPUT")
    try:
        s = get("/status.json")
    except Exception as e:
        print("DOCTOR: cannot read the live site's status.json (%s); asking for a refresh" % str(e)[:80])
        bad.append("site unreachable: status.json did not answer")
        heal.append("refresh")
        s = None
    if s:
        age = hours_since(s["built_at"]) * 60 if s.get("built_at") else 10 ** 6
        (bad if age > REBUILD_MIN else ok).append("site rebuilt %d min ago" % age)
        if age > REBUILD_MIN:
            heal.append("refresh")
        for k_, cap_, what_ in (("files", 100000 if os.environ.get("WORKERS_PAID") else 20000, "Cloudflare plan files"),):  # scale cliffs (PLAN.md factory audit): warn at 70%
            if s.get(k_) is not None:
                (bad if s[k_] > 0.7 * cap_ else ok).append("%s: %s of %s (%d%%)" % (what_, format(s[k_], ","), format(cap_, ","), 100 * s[k_] / cap_))
        (bad if world_short(s) else ok).append(world_short(s) or "world pages show every block their data allows")
        if s.get("cache_lost"):
            bad.append("data cache lost: this build started empty; the good copy was not overwritten")
        try:
            sh_ = json.loads(s.get("shards") or "{}")
            if 0 in sh_.get("failed", []) or len(sh_.get("failed", [])) * 4 >= sh_.get("of", 1):
                bad.append("collect shards failed: %s of %s (shard 0 holds every world gauge)" % (sh_["failed"], sh_["of"]))
        except ValueError:
            pass
        for c_ in (s.get("coverage") or {}).get("drops") or []:
            bad.append("blocks vanished: %s" % c_)
        live = {r["site"] for r in csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8")) if r["status"] == "live"}
        on = set(s.get("by_gauge") or {})
        missing = sorted(live - on)
        (bad if missing else ok).append("%d of %d live gauges on the site%s" % (len(live & on), len(live), (" (missing: %s)" % " ".join(missing[:12])) if missing else ""))
        try:  # gauges outside the US: the Worker's copy must keep moving
            wl = get("/live/world.json")
            if wl.get("t"):
                wh = hours_since(wl["t"])
                (bad if wh > 3 else ok).append("world gauge readings last changed %.1f h ago" % wh)
        except Exception:
            pass
        try:  # rolling rebuild (build.py ROLL_H 2): a page that stopped being rebuilt shows here, never silently
            bm = get("/_built.json")
            old_ = sorted((hours_since(v["at"]), k) for k, v in bm.items() if v.get("at"))[-3:]
            if old_ and old_[-1][0] > 6:
                bad.append("gauge pages not rebuilt for over 6 h: %s" % ", ".join("%s %.0f h" % (k, a) for a, k in old_ if a > 6))
                heal.append("refresh")
            elif old_:
                ok.append("oldest gauge page built %.1f h ago" % old_[-1][0])
        except Exception:
            ok.append("no /_built.json yet (first rolling build not deployed)")
    try:
        h = get("/_health.json")
        try:  # a source switched off in data/sources.json is a documented gap, not a broken feed
            off = {r.get("id") for r in json.load(open(os.path.join(ROOT, "data", "sources.json"), encoding="utf-8"))["sources"] if r.get("status") == "off"}
        except Exception:
            off = set()
        for src, v in sorted((h.get("sources") or {}).items()):
            if src in off or not v.get("last_run"):
                continue  # judge only sources a run actually attempted (2026-10-26: daily sources not yet attempted were reported "never worked")
            last = v.get("last_ok_at")
            limit = 3 if src in HOURLY else 30
            lr = v.get("last_run") or {}
            n = lr.get("ok", 0) + lr.get("absent", 0) + lr.get("failed", 0)
            # 2026-10-29: 12 false "not working" lines. "nws.forecast"-style keys count only failures (success is counted under "nws"),
            # so they are judged on the latest run only; "full"-mode sources (flood zone, dam, rainfall frequency) are fetched once per gauge, never on a clock
            if ("." in src or src == "gauge") and lr.get("at", "")[:13] < (h.get("at") or "")[:13]:
                continue
            if lr.get("mode") == "full" and not lr.get("failed"):
                continue
            if "." in src and lr.get("failed"):
                bad.append("%s failed on %d gauge(s) in the latest run (%s)" % (src, lr["failed"], v.get("last_error") or ""))
                continue
            if lr.get("ok", 0) == 0 and lr.get("absent", 0) == n and n:
                bad.append("source %s returned nothing for all %d gauges in its last run (the agency sent an empty answer)" % (src, n))
                continue
            if not last or ((src in UNIVERSAL or src in HOURLY) and hours_since(last) > limit) or hours_since(last) > 50:  # never worked, or a daily source silent for two days
                bad.append("%s %s has not worked for %s (last error: %s)" % ("feed dead:" if (src in HOURLY or src in ("eccc", "pegelonline", "world-wx")) and (not last or hours_since(last) > 24) else "source", src, "ever" if not last else "%.0f h" % hours_since(last), v.get("last_error") or "none recorded"))
            elif n >= 10 and lr.get("failed", 0) / n > 0.15:
                bad.append("source %s failed on %d of %d gauges in its last run (%s)" % (src, lr["failed"], n, v.get("last_error") or ""))
        ok.append("source health read (%s run, %s)" % (h.get("mode"), h.get("at", "")[:16]))
    except Exception as e:
        bad.append("cannot read /_health.json (%s)" % str(e)[:60])
    try:  # the edge asks USGS when a page is opened: one gauge's answer must be fresh, and Google must get the same page a phone gets
        pages = get("/live-sites.json")
        site, path = pages[0][0], pages[0][1]
        rr = http_open(SITE + "/live/%s.json" % site, UA, 30)
        lj = json.load(rr)
        la = hours_since(lj["t"]) * 3600 if lj.get("t") else None
        (bad if la is None or la > EDGE_MAX_S else ok).append("edge stored copy last updated %s ago" % ("never" if la is None else "%d s" % la))
        bt = rr.headers.get("x-rwl-build-trigger")  # "<iso> <status>": the Worker cron asked GitHub for a build
        if bt:
            at_, code, *end = bt.split(" ", 2)
            (ok if code == "204" else bad).append("%s: %s (204 = GitHub accepted)" % ("build key rejected, last build trigger from Cloudflare" if code in ("401", "403") else "last build trigger from Cloudflare", bt))
            if end and end[0].strip() and hours_since(end[0].replace(" UTC", "+00:00").replace(" ", "T")) > -30 * 24:
                bad.append("GitHub build key expires %s: make a new one and replace the Cloudflare secret GH_DISPATCH_TOKEN (RUNBOOK)" % end[0][:10])
        else:
            ok.append("Cloudflare has not needed to trigger a build yet (GitHub's own schedule ran in time)")
        if rr.headers.get("x-rwl-usgs-remaining"):
            rem_ = int(float(rr.headers.get("x-rwl-usgs-remaining")))
            (bad if rem_ < 200 else ok).append("USGS key budget left this hour: %d of 1,000" % rem_)
        import re
        flows = {}
        for who, ua in (("phone", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile/15E148 Safari/604.1"), ("googlebot", "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)")):
            r = http_open(SITE + path, {"User-Agent": ua}, 30)
            h = r.read().decode("utf-8", "replace")
            flows[who] = (re.search(r'data-live="flow">([^<]*)<', h) or [None, None])[1], len(h), r.headers.get("x-rwl-edge")
        if flows["phone"][0] != flows["googlebot"][0] or abs(flows["phone"][1] - flows["googlebot"][1]) > 2000:
            bad.append("Googlebot and a phone got different pages for %s: %s" % (path, flows))
        elif not flows["googlebot"][0]:
            bad.append("Googlebot got no flow number on %s" % path)
        else:
            ok.append("Googlebot and a phone get the same page (flow %s, edge %s)" % (flows["googlebot"][0], flows["googlebot"][2]))
        if not out_ or datetime.datetime.now(datetime.timezone.utc).hour == 12:  # outside links, once a day in CI and at every session start: government pages move (NWS AHPS 2024, USGS legacy 2027-02-22)
            ext = set(re.findall(r'href="(https?://(?!riverwaterlevels\.com)[^"]+)"', h))
            ext |= {e["url"] for st in json.load(open(os.path.join(ROOT, "data", "state-rules.json"), encoding="utf-8"))["states"].values() for e in (st.get("fish"), st.get("boat")) if e}  # one page shows only its own state's links
            ext = sorted(ext)
            dead = []
            for u in ext:
                try:
                    http_open(u.replace("&amp;", "&"), UA, 20).close()
                except Exception as e:  # ponytail: only "gone" counts; 403/429/5xx mean the server answered, and a timeout from one network proves nothing
                    if getattr(e, "code", None) in (404, 410) or isinstance(getattr(e, "reason", None), socket.gaierror):
                        dead.append("%s (%s)" % (u, getattr(e, "code", None) or str(e)[:40]))
            (bad if dead else ok).append("outside links on %s: %d checked%s" % (path, len(ext), (", dead: " + "; ".join(dead[:6])) if dead else ", none gone"))
    except Exception as e:
        bad.append("edge check failed (%s)" % str(e)[:80])
    try:
        tr = get("/_truth.json")
        if tr.get("status") == "mismatch":
            bad.append("built pages disagreed with USGS/NWS: %s" % str(tr.get("mismatches"))[:200])
        if not tr.get("last_ok_at") or hours_since(tr["last_ok_at"]) > 6:
            bad.append("numbers last verified against USGS %s" % ("never" if not tr.get("last_ok_at") else "%.0f h ago" % hours_since(tr["last_ok_at"])))
        else:
            ok.append("numbers verified against USGS %.1f h ago" % hours_since(tr["last_ok_at"]))
    except Exception as e:
        bad.append("cannot read /_truth.json (%s)" % str(e)[:60])
    tok = os.environ.get("CLOUDFLARE_API_TOKEN")
    if tok:  # a deploy key that expires stops every deploy with nobody around to renew it
        try:
            import urllib.request
            acct = os.environ.get("CLOUDFLARE_ACCOUNT_ID")  # an account key answers only at the account address (user address: 401)
            url = ("https://api.cloudflare.com/client/v4/accounts/%s/tokens/verify" % acct) if acct else "https://api.cloudflare.com/client/v4/user/tokens/verify"
            v = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": "Bearer " + tok}), timeout=20))
            exp = (v.get("result") or {}).get("expires_on")
            if exp and hours_since(exp) > -30 * 24:
                bad.append("Cloudflare deploy key expires %s: create a new one and replace the GitHub secret CLOUDFLARE_API_TOKEN" % exp[:10])
            else:
                ok.append("Cloudflare deploy key: %s" % ("expires " + exp[:10] if exp else "no expiry date"))
        except Exception as e:
            bad.append("Cloudflare deploy key expiry not readable (%s)" % str(e)[:50])
    try:
        stall = release_stall()
        if stall:
            bad.append(stall + (" (%s)" % s["release_skip"] if s and s.get("release_skip") else ""))
        use = load()
        if use is None and tok:
            bad.append("Worker load unreadable: the Cloudflare key needs Account Analytics Read, or the CPU and request stops are off")
        elif use:
            cut = use["stopped"]
            if use["requests"] >= REQUESTS and not os.environ.get("WORKERS_PAID"):
                bad.append("Workers Paid is due: %s Worker requests in 24 h of the free 100,000, past it pages answer error 1027" % format(use["requests"], ","))
            (bad if cut >= LIMIT and not os.environ.get("WORKERS_PAID") else ok).append("Cloudflare stopped the Worker %d times in 24 h%s" % (cut, " (Workers Paid is due: readers got error pages; then set the GitHub variable WORKERS_PAID, RUNBOOK)" if cut >= LIMIT else ""))
    except (OSError, ValueError, KeyError, AttributeError) as e:
        bad.append("no new gauges released: release record unreadable (%s)" % str(e)[:60])
    print("SITE HEALTH %s: %d problem(s)" % (datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), len(bad)))
    for x in bad:
        print("  PROBLEM:", x)
    for x in ok:
        print("  ok:", x)
    # Owner alarm after the Claude subscription ends (2026-10-30): the hourly run fails TWICE A DAY (01 and 13 UTC) when a reader-visible problem stands,
    # so GitHub's built-in failure email reaches the owner. Source noise (one feed down, its block hides) never alarms.
    SEVERE = ("site unreachable", "edge check failed", "edge stored copy", "cannot read", "world gauge readings", "feed dead", "Worker load unreadable", "data cache lost", "collect shards failed", "pages missing blocks", "blocks vanished", "build key", "no new gauges released", "numbers last verified", "USGS key budget", "Workers Paid", "site rebuilt", "live gauges on the site (missing", "built pages disagreed", "Cloudflare plan files", "GitHub cache", "gauge pages not rebuilt", "Googlebot and a phone", "deploy key expires")
    alarm = [x for x in bad if any(k in x for k in SEVERE)]
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        open(out, "a").write("heal=%s\n" % ("refresh" if "refresh" in heal else "none"))
        if alarm:  # watchdog.yml decides whether this run may email: GitHub skipped 59% of the 01 and 13 UTC hours (2026-11-02)
            open(out, "a").write("alarm=%s\n" % " | ".join(alarm)[:900].replace("\n", " "))
    return 0  # never fails: no owner email; problems are read at session start and healed here where possible


if "--selftest" in sys.argv:
    real = open
    try:
        open = lambda p, *a, **k: __import__("io").StringIO("2026-01-01\n" if p.endswith(".txt") else "status,gate\nqueue,\n")
        assert "days, 1 waiting" in release_stall(), "a stalled release went unreported"
        open = lambda p, *a, **k: __import__("io").StringIO(datetime.datetime.now(datetime.timezone.utc).date().isoformat() if p.endswith(".txt") else "status,gate\nqueue,\n")
        assert release_stall() is None, "a fresh release was reported"
        assert REBUILD_MIN > 112, "a normal gap between rebuilds would alarm"
        assert "1 gauges short" in world_short({"world": {"listed": 40, "shown": 40, "gaps": {"KAUB": ["alerts"]}}}), "a page gap went unreported"
        assert "6 held" in world_short({"world": {"listed": 20, "shown": 14, "gaps": {}}}), "held gauges went unreported"
        assert world_short({"world": {"listed": 38, "shown": 33, "gaps": {}}}) is None, "today's expected holds alarmed"
    finally:
        open = real
    print("selftest OK")
else:
    sys.exit(main())
