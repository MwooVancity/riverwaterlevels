"""Site doctor (gate 3 health, owner 2026-10-25: "no alarms"): reads the LIVE site, prints one health report, heals what it can, never fails.
Run hourly by .github/workflows/watchdog.yml and by hand at session start: python -I tools/watchdog.py
Heals: site not rebuilt for 60 min -> asks for a refresh (heal=refresh in $GITHUB_OUTPUT; the workflow dispatches it unless one is already
queued).
Reports (cannot heal, read at session start): live gauges missing from the site, sources that stopped working (hours since last_ok_at),
numbers not verified against USGS, a stale edge answer, and Googlebot getting a different page than a phone (no cloaking, ever).
At most one USGS call (the edge's own per-gauge fetch, when its 3-min cache is cold)."""
import csv, json, os, sys, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lib.common import http_open
from lib.source_list import UNIVERSAL

SITE = "https://riverwaterlevels.com"
UA = {"User-Agent": "Mozilla/5.0 (rwl-doctor)"}
REBUILD_MIN = 60      # the hourly refresh missed once: ask for one
EDGE_MAX_S = 1800     # the cron writes only when a reading changed; 30 min with no write means the poll stopped
# a source that has not worked for this long is reported dead: 3 h for the hourly sources, 30 h for once-a-day sources
HOURLY = {"usgs", "nws", "rain", "wpc", "nwps"}


def get(path, raw=False):
    r = http_open(SITE + path, UA, 30)
    return r if raw else json.load(r)


def hours_since(iso):
    return (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))).total_seconds() / 3600


def main():
    ok, bad, heal = [], [], []
    out_ = os.environ.get("GITHUB_OUTPUT")
    try:
        s = get("/status.json")
    except Exception as e:
        print("DOCTOR: cannot read the live site's status.json (%s); asking for a refresh" % str(e)[:80])
        heal.append("refresh")
        s = None
    if s:
        age = hours_since(s["built_at"]) * 60 if s.get("built_at") else 10 ** 6
        (bad if age > REBUILD_MIN else ok).append("site rebuilt %d min ago" % age)
        if age > REBUILD_MIN:
            heal.append("refresh")
        live = {r["site"] for r in csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8")) if r["status"] == "live"}
        on = set(s.get("by_gauge") or {})
        missing = sorted(live - on)
        (bad if missing else ok).append("%d of %d live gauges on the site%s" % (len(live & on), len(live), (" (missing: %s)" % " ".join(missing[:12])) if missing else ""))
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
            if "." in src and lr.get("at", "")[:13] < (h.get("at") or "")[:13]:
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
                bad.append("source %s has not worked for %s (last error: %s)" % (src, "ever" if not last else "%.0f h" % hours_since(last), v.get("last_error") or "none recorded"))
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
            (ok if bt.endswith(" 204") else bad).append("last build trigger from Cloudflare: %s (204 = GitHub accepted)" % bt)
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
            ext = sorted(set(re.findall(r'href="(https?://(?!riverwaterlevels\.com)[^"]+)"', h)))
            dead = []
            for u in ext:
                try:
                    http_open(u.replace("&amp;", "&"), UA, 20).close()
                except Exception as e:  # ponytail: only "gone" counts; 403/429/5xx mean the server answered (bot walls, rate limits), so no false alarm
                    if getattr(e, "code", None) in (404, 410) or not hasattr(e, "code"):
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
    print("SITE HEALTH %s: %d problem(s)" % (datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), len(bad)))
    for x in bad:
        print("  PROBLEM:", x)
    for x in ok:
        print("  ok:", x)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        open(out, "a").write("heal=%s\n" % ("refresh" if "refresh" in heal else "none"))
    return 0  # never fails: no owner email; problems are read at session start and healed here where possible


sys.exit(main())
