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
    return urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=t).read().decode("utf-8", "replace")


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
    for i in range(0, len(ids), 40):
        try:
            j = json.loads(get(USGS % ",".join("USGS-" + s for s in ids[i:i + 40])))
        except Exception as e:
            if LOCAL:
                print("truth_live: the USGS API did not answer (%s); comparison skipped, not blocking, recorded as skipped in _truth.json" % str(e)[:80])
                record("mismatch" if bad else "skipped", 0, bad, ["USGS API"])
                return 1 if bad else 0
            raise
        for f in j.get("features", []):
            p = f["properties"]
            latest[(p["monitoring_location_id"][5:], p["parameter_code"])] = (datetime.datetime.fromisoformat(p["time"]), float(p["value"]))
    for sid, pg in pages.items():
        u = latest.get((sid, "00060"))
        if not u:
            bad.append("%s: USGS returned no latest flow" % pg["url"])
            continue
        ut, uv = u
        if ut == pg["t"]:
            if abs(uv - pg["flow"]) > max(1.0, 0.01 * abs(uv)):
                bad.append("%s: flow %s on the page, %s at USGS for the same time %s" % (pg["url"], pg["flow"], uv, ut.isoformat()))
            s_ = latest.get((sid, "00065"))
            if s_ and s_[0] == pg["t"] and pg["stage"] is not None and abs(s_[1] - pg["stage"]) > 0.02:
                bad.append("%s: stage %s on the page, %s at USGS" % (pg["url"], pg["stage"], s_[1]))
        elif ut > pg["t"]:
            lag = (ut - pg["t"]).total_seconds() / 3600
            if lag > MAX_LAG_H:
                bad.append("%s: page is %.1f h behind USGS (page %s, USGS %s)" % (pg["url"], lag, pg["t"].isoformat(), ut.isoformat()))
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
    return 1 if bad else 0


sys.exit(main())
