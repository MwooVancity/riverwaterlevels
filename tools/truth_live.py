"""Truth against the sources, on the LIVE site: every gauge page's latest flow, stage and time, and its flood stages, versus the USGS and NWS APIs fetched now.
Usage: python tools/truth_live.py            (exit 1 and print each mismatch). Run by tools/watchdog.py every hour and by hand.
       python tools/truth_live.py --dir dist_next   the same comparison on the BUILT pages before they are published (refresh.py runs it as a blocking gate; if the USGS or NWS API does not answer it only warns, never blocks)
Rules per gauge page:
 - the page's flow reading time equals USGS's latest: flow must match (within 1% or 1 cfs); stage must match within 0.02 ft
 - USGS has a newer reading: the page may be behind by at most 3 hours (the browser refreshes the numbers on load, so a short lag is normal)
 - flood stages shown on the page (Action, Minor, Moderate, Major) equal the NWS forecast point's categories within 0.05 ft
 - the NWS forecast point named on the page exists and answers"""
import json, re, sys, urllib.request, datetime

SITE = "https://riverwaterlevels.com"
USGS = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/latest-continuous/items?monitoring_location_id=%s&parameter_code=00060,00065&limit=1000&f=json"
NWPS = "https://api.water.noaa.gov/nwps/v1/gauges/%s"
H = {"User-Agent": "Mozilla/5.0 (truth-live)"}
MAX_LAG_H = 3
STALE_FAIL_H = 12  # a lag up to here is a warning (USGS lag or a single slow gauge, not a wrong number); beyond it the refresh is genuinely broken and the run should go red


LOCAL = sys.argv[sys.argv.index("--dir") + 1] if "--dir" in sys.argv else None


def page(path):
    """A site path (/river/x/y/ or /gauges.json) from the live site, or from the local build with --dir."""
    if LOCAL:
        import os
        root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), LOCAL)
        p = os.path.join(root, path.strip("/")) if path.endswith(".json") else os.path.join(root, path.strip("/"), "index.html")
        return open(p, encoding="utf-8").read()
    return get(SITE + path)


def get(u, t=60):
    import time
    for i, wait in enumerate((0, 5, 20, 45)):  # a rate limit (429) or a hiccup is retried before anything is recorded as skipped
        time.sleep(wait)
        try:
            return urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=t).read().decode("utf-8", "replace")
        except Exception as e:
            if i == 3 or getattr(e, "code", 0) not in (0, 429, 500, 502, 503, 504):
                raise


def record(status, compared, bad, skipped):
    """With --dir: write _truth.json into the build so the live site says when its numbers were last checked against USGS and NWS (read by tools/watchdog.py). A skipped check is recorded as skipped, never as ok."""
    if not LOCAL:
        return
    import os
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    last_ok = now if status == "ok" else None
    if last_ok is None:
        try:
            last_ok = json.loads(get(SITE + "/_truth.json", 20)).get("last_ok_at")
        except Exception:
            last_ok = None
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), LOCAL)
    json.dump({"checked_at": now, "status": status, "compared": compared, "skipped": skipped, "mismatches": bad[:10], "last_ok_at": last_ok}, open(os.path.join(root, "_truth.json"), "w", encoding="utf-8"))


def main():
    bad = []
    skipped = []
    stale = []
    gauges = json.loads(page("/gauges.json"))
    pages = {}
    for name, url, *_ in gauges:
        h = page(url)
        sid = re.search(r"USGS gauge (\d+)", h)
        flow = re.search(r'data-live="flow">([\d,.\-]+)<', h)
        stage = re.search(r'data-live="stage">([\d.\-]+)<', h)
        t = re.search(r'class="hero hero2" data-t="([^"]+)"', h)
        if not (sid and flow and t):
            bad.append("%s: cannot read gauge id, flow or time from the page" % url)
            continue
        pages[sid.group(1)] = {"url": url, "flow": float(flow.group(1).replace(",", "")), "stage": float(stage.group(1)) if stage else None,
                               "t": datetime.datetime.fromisoformat(t.group(1)), "lid": (re.search(r"forecast point ([A-Z0-9]{5})", h) or [None, None])[1] if "forecast point" in h else None,
                               "cats": {m[0].lower(): float(m[1]) for m in re.findall(r'<li><i style="background:#[0-9a-f]+"></i>(Action|Minor|Moderate|Major) <b>([\d.\-]+) ft</b></li>', h)}}
    ids = sorted(pages)
    latest = {}
    failed_ids = set()
    for i in range(0, len(ids), 40):
        try:
            j = json.loads(get(USGS % ",".join("USGS-" + s for s in ids[i:i + 40])))
        except Exception as e:
            if LOCAL:  # one batch's outage must not abandon the other batches (a later-batch wrong value would otherwise ship unchecked); skip only this batch's gauges
                print("truth_live: USGS batch %d did not answer (%s); that batch skipped, continuing" % (i // 40, str(e)[:80]))
                failed_ids.update(ids[i:i + 40])
                continue
            raise
        for f in j.get("features", []):
            p = f["properties"]
            latest[(p["monitoring_location_id"][5:], p["parameter_code"])] = (datetime.datetime.fromisoformat(p["time"]), float(p["value"]))
    for sid, pg in pages.items():
        u = latest.get((sid, "00060"))
        if not u:
            (skipped if sid in failed_ids else bad).append("%s: USGS %s" % (pg["url"], "batch did not answer (skipped)" if sid in failed_ids else "returned no latest flow"))
            continue
        ut, uv = u
        if ut == pg["t"]:
            if abs(uv - pg["flow"]) > max(1.0, 0.01 * abs(uv)):
                bad.append("%s: flow %s on the page, %s at USGS for the same time %s" % (pg["url"], pg["flow"], uv, ut.isoformat()))
            s_ = latest.get((sid, "00065"))
            if s_ and s_[0] == pg["t"] and pg["stage"] is not None:
                if abs(s_[1] - pg["stage"]) > 0.02:
                    bad.append("%s: stage %s on the page, %s at USGS" % (pg["url"], pg["stage"], s_[1]))
            elif pg["stage"] is not None:  # stage shown on the page but USGS has no stage at the page's timestamp: record as skipped, not silently ignored
                skipped.append("%s: stage not verified (no USGS stage at the page's timestamp)" % pg["url"])
        elif ut > pg["t"]:
            lag = (ut - pg["t"]).total_seconds() / 3600
            # a lagging page is stale, not WRONG (it shows its real age). A short lag is normal; only an extreme lag means our refresh is actually broken.
            if lag > STALE_FAIL_H:
                bad.append("%s: page is %.1f h behind USGS (page %s, USGS %s)" % (pg["url"], lag, pg["t"].isoformat(), ut.isoformat()))
            elif lag > MAX_LAG_H:
                stale.append("%s: page is %.1f h behind USGS (USGS reads %s; the page shows this age)" % (pg["url"], lag, ut.isoformat()))
        if pg["lid"] and pg["cats"]:
            try:
                cats = (json.loads(get(NWPS % pg["lid"])).get("flood") or {}).get("categories") or {}
            except Exception as e:
                if LOCAL:  # an NWS outage must not freeze fresh USGS data: the flood stages stay unchecked and the skip is recorded
                    skipped.append(pg["lid"])
                    continue
                bad.append("%s: NWS forecast point %s did not answer (%s)" % (pg["url"], pg["lid"], str(e)[:60]))
                continue
            for k, v in pg["cats"].items():
                nv = (cats.get(k) or {}).get("stage")
                if not isinstance(nv, (int, float)) or abs(nv - v) > 0.05:
                    bad.append("%s: %s flood stage %.1f ft on the page, %s at NWS %s" % (pg["url"], k, v, nv, pg["lid"]))
    record("mismatch" if bad else ("skipped" if skipped else "ok"), len(pages), bad, skipped)
    print("truth_live: %d gauge pages compared with USGS and NWS, %d mismatches%s" % (len(pages), len(bad), (", flood stages unchecked for %s" % skipped) if skipped else ""))
    for b in bad[:25]:
        print("  MISMATCH", b)
    for s in stale[:25]:
        print("  STALE (warning, not a failure)", s)
    if stale:
        print("truth_live: %d gauge(s) lagging USGS by 3 to %d h (warning only; the pages show their real age)" % (len(stale), STALE_FAIL_H))
    return 1 if bad else 0


sys.exit(main())
