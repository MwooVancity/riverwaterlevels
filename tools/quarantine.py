"""After a refresh failed on a release day: send the new gauges that failed back to the queue, so the retry ships the rest.
Reads dist_next/_failed.json (written by check.py). Exit 0: every failure was a new gauge, now queued with its reason. Exit 1: something else failed
(an existing page or a site-level rule), so the workflow undoes the whole release instead. 2026-10-30: one new gauge with no earlier page froze all deploys for 13 h."""
import csv, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lib.pages import load_effective

WAVES, ALLOW = os.path.join(ROOT, "data", "waves.csv"), os.path.join(ROOT, "data", "index-allow.json")


WPP = os.path.join(ROOT, "data", "world-pages.json")


def world_new():
    """{published path: (page slug, station)} for each world gauge this release added (data/world-pages.json against HEAD)."""
    from lib.directory import world_gauge_url
    try:
        head = json.loads(subprocess.check_output(["git", "show", "HEAD:data/world-pages.json"], cwd=ROOT, text=True, encoding="utf-8"))
        cur = json.load(open(WPP, encoding="utf-8"))
    except (OSError, ValueError, subprocess.CalledProcessError):
        return {}
    old = {(p["slug"], s) for p in head for s in p.get("gauge_pages") or []}
    out = {}
    for p in cur:
        try:
            title = {r["name"]: r.get("title") for r in json.load(open(os.path.join(ROOT, "cache", "_river-%s.json" % p["slug"]), encoding="utf-8"))["rows"]}
        except (OSError, ValueError, KeyError):
            title = {}
        for s in p.get("gauge_pages") or []:
            if (p["slug"], s) not in old:
                for nm in {title.get(s) or s, s}:
                    out[world_gauge_url(p, nm).strip("/") + "/index.html"] = (p["slug"], s)
    return out


def blame(pages, rows, rel, picks):
    """{site: why} for the failing pages, or None when one cannot be attributed. A gauge page (or its embed) is its own pick (2026-10-31). A state page rivers/<st>/index.html blames this release's new picks in that state, and a river hub river/<slug>/index.html the new picks under it (2026-11-21: '14th Street' on rivers/ga undid all 25). Coarse: if the real cause is an old gauge the retry fails and the release is undone, nothing bad ships."""
    bad = {}
    for k, v in pages.items():
        s = rel.get(k[6:] if k.startswith("embed/") else k)
        if s is not None:
            bad[s] = v
            continue
        parts = k.split("/")
        st = parts[1] if parts[0] == "rivers" and len(parts) == 3 else None
        hub = "/" + "/".join(parts[:-1]) + "/" if parts[0] == "river" and len(parts) == 3 else None
        text = " ".join(v).lower()  # evidence, not just a state: a pick is blamed only when its own name appears in the failure message (2026-11-21 audit: a state hub failing for another reason must not send good gauges back)
        hit = [p for p in picks if p in rows and ((st and (rows[p].get("state") or "").lower() == st) or (hub and (rows[p].get("dashboard_url") or "").startswith(hub)))
               and any(len(n) > 3 and n.lower() in text for n in (rows[p].get("place"), rows[p].get("raw_name")) if n)]
        if not hit:
            return None
        for p in hit:
            bad.setdefault(p, v)
    return bad


def selftest():
    rows = {"A": {"state": "GA", "place": "Columbus", "dashboard_url": "/river/chattahoochee-river/columbus/"}, "B": {"state": "CO", "place": "Yampa", "dashboard_url": "/river/x/y/"}, "O": {"state": "GA", "place": "Old", "dashboard_url": "/river/old/z/"}}
    rel = {r["dashboard_url"].strip("/") + "/index.html": s for s, r in rows.items()}
    picks = {"A", "B"}
    assert blame({"rivers/ga/index.html": ["jargon near 'River at 14th Street at Columbus'"]}, rows, rel, picks) == {"A": ["jargon near 'River at 14th Street at Columbus'"]}
    assert blame({"rivers/ga/index.html": ["template variable missing"]}, rows, rel, picks) is None  # the message does not name the pick: unattributable, the release is undone
    assert blame({"river/x/y/index.html": ["Yampa x"]}, rows, rel, picks) == {"B": ["Yampa x"]}
    assert blame({"index.html": ["x"]}, rows, rel, picks) is None  # home page: site-level
    assert blame({"rivers/tx/index.html": ["x"]}, rows, rel, picks) is None  # a state with no new pick
    import tempfile
    from lib.common import fail_pages
    with tempfile.TemporaryDirectory() as d:
        fail_pages(d, {"rivers/ga/index.html": ["m"]}, ["s"])
        fail_pages(d, {"a/index.html": ["n"]})
        f = json.load(open(os.path.join(d, "_failed.json"), encoding="utf-8"))
    assert set(f["pages"]) == {"rivers/ga/index.html", "a/index.html"} and f["site"] == ["s"]
    print("quarantine selftest OK")


def main():
    try:
        failed = json.load(open(os.path.join(ROOT, "dist_next", "_failed.json"), encoding="utf-8"))
    except (OSError, ValueError):
        sys.exit("no _failed.json: the failure was not a page check")
    try:  # release 2026-11-07: Green River was already carried (its live copy ships), yet it counted as "not a new gauge" and undid all 25 picks
        carried = {r.replace("\\", "/") for r in json.load(open(os.path.join(ROOT, "dist_next", "_carried.json"), encoding="utf-8"))}
    except (OSError, ValueError):
        carried = set()
    pages = {k.replace("\\", "/"): v for k, v in (failed.get("pages") or {}).items() if k.replace("\\", "/") not in carried}
    if failed.get("site") or not pages:
        sys.exit("site-level failure or no failing page: %s" % str(failed.get("site"))[:200])
    was = {r["site"] for r in csv.DictReader(subprocess.check_output(["git", "show", "HEAD:data/waves.csv"], cwd=ROOT, text=True, encoding="utf-8").splitlines()) if r["status"] == "live"}
    rows, _ = load_effective()
    rel = {rows[s]["dashboard_url"].strip("/") + "/index.html": s for s in rows}
    wnew = world_new()  # gate audit 2026-11-08: a failing new world page undid all 25 picks; now it leaves world-pages.json alone
    wbad = {k: v for k, v in pages.items() if k in wnew}
    pages = {k: v for k, v in pages.items() if k not in wnew}
    if wbad:
        wp_ = json.load(open(WPP, encoding="utf-8"))
        for k in wbad:
            slug_, st_ = wnew[k]
            for p_ in wp_:
                if p_["slug"] == slug_:
                    for f_ in ("stations", "gauge_pages"):
                        if st_ in (p_.get(f_) or []):
                            p_[f_].remove(st_)
        raw = open(WPP, encoding="utf-8", newline="").read()
        nl_ = "\r\n" if "\r\n" in raw else "\n"
        open(WPP, "w", encoding="utf-8", newline="").write("[" + nl_ + ("," + nl_).join(" " + json.dumps(x, ensure_ascii=False) for x in wp_) + nl_ + "]" + nl_)
        print("world gauges back out of this release: %s" % ", ".join("%s %s" % wnew[k] for k in sorted(wbad)))
        if not pages:
            return
    picks = {r["site"] for r in csv.DictReader(open(WAVES, encoding="utf-8")) if r["status"] == "live"} - was
    bad = blame(pages, rows, rel, picks)
    if bad is None or any(s in was for s in bad):
        sys.exit("a failing page is not a new gauge or a state/hub of one: %s" % sorted(pages)[:5])
    all_ = list(csv.DictReader(open(WAVES, encoding="utf-8")))
    for r in all_:
        if r["site"] in bad:
            r["status"], r["gate"] = "queue", ("site-check: " + bad[r["site"]][0]).replace("\n", " ")[:300]
    with open(WAVES, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(all_[0].keys()))
        w.writeheader()
        w.writerows(all_)
    cfg = json.load(open(ALLOW, encoding="utf-8"))
    gone = {rows[s]["dashboard_url"] for s in bad}
    cfg["allow"] = [u for u in cfg["allow"] if u not in gone]
    json.dump(cfg, open(ALLOW, "w", encoding="utf-8"), indent=1)
    for s in bad:  # practice 2026-11-08: a sent-back gauge kept its cache file, so the second try built it again and failed again
        try:
            os.remove(os.path.join(ROOT, "cache", s + ".json"))
        except OSError:
            pass
    print("back to the queue: %s" % ", ".join(sorted(bad)))


selftest() if "--selftest" in sys.argv else main()
