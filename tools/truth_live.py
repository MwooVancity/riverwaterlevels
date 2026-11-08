"""Truth against the sources, on the LIVE site: every gauge page's latest flow, stage and time, and its flood stages, versus the USGS and NWS APIs fetched now.
Usage: python tools/truth_live.py            (exit 1 and print each mismatch). Run by tools/watchdog.py every hour and by hand.
       python tools/truth_live.py --dir dist_next   the same comparison on the BUILT pages before they are published (refresh.py runs it as a blocking gate; if the USGS or NWS API does not answer it only warns, never blocks)
Rules per gauge page:
 - the page's flow reading time equals USGS's latest: flow must match (within 1% or 1 cfs); stage must match within 0.02 ft
 - USGS has a newer reading: up to 12 hours behind is a warning, beyond STALE_FAIL_H fails (the Worker swaps the live numbers; carried pages are up to 2.5 h old)
 - flood stages shown on the page (Action, Minor, Moderate, Major) equal the NWS forecast point's categories within 0.05 ft
 - the NWS forecast point named on the page exists and answers"""
import json, os, re, sys, urllib.request, urllib.error, datetime, zoneinfo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.common import usgs_headers, new_fail  # new_fail: one writer of _failed.json, shared with truth_world

SITE = "https://riverwaterlevels.com"
USGS = "https://api.waterdata.usgs.gov/ogcapi/v1/collections/latest-continuous/items?monitoring_location_id=%s&parameter_code=00060,00065,62614,62615,72020,00062&limit=1000&f=json"
NWPS = "https://api.water.noaa.gov/nwps/v1/gauges/%s"
H = {"User-Agent": "Mozilla/5.0 (truth-live)"}
HU = dict(usgs_headers(), **H)  # with the key: anonymous calls from shared CI addresses get rate-limited and the check silently skips
MAX_LAG_H = 3
SAMPLE = 300  # live mode checks this many pages a run, rotating hourly: every page within ceil(pages / 300) hours. 185 pages serial took 92-313 s against a 5-min limit (2026-11-04)
WORKERS = 8  # parallel page and NWS fetches; ~0.3 s each, so 300 pages plus their NWS points take ~25 s at any site size
STALE_FAIL_H = 12  # a lag up to here is a warning (USGS lag or a single slow gauge, not a wrong number); beyond it the refresh is genuinely broken and the run should go red


LOCAL = sys.argv[sys.argv.index("--dir") + 1] if "--dir" in sys.argv else None


def page(path):
    """A site path (/river/x/y/ or /gauges.json) from the live site, or from the local build with --dir."""
    if LOCAL:
        root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), LOCAL)
        p = os.path.join(root, path.strip("/")) if path.endswith(".json") else os.path.join(root, path.strip("/"), "index.html")
        return open(p, encoding="utf-8").read()
    return get(SITE + path)


def get(u, t=60):
    import time
    for i, wait in enumerate((0, 5, 20, 45)):  # a rate limit (429) or a hiccup is retried before anything is recorded as skipped
        time.sleep(wait)
        try:
            return urllib.request.urlopen(urllib.request.Request(u, headers=HU if "waterdata.usgs.gov" in u else H), timeout=t).read().decode("utf-8", "replace")
        except Exception as e:
            if i == 3 or getattr(e, "code", 0) not in (0, 429, 500, 502, 503, 504):
                raise


AGENCY_URL = {  # the operator's own feed for the days around the page's reading (d0 = the reading's Pacific date)
    "CDEC": lambda sta, d0: "https://cdec.water.ca.gov/dynamicapp/req/JSONDataServlet?Stations=%s&SensorNums=6&dur_code=H&Start=%s&End=%s" % (sta, d0 - datetime.timedelta(days=1), d0 + datetime.timedelta(days=2)),
    "TWDB": lambda sta, d0: "https://www.waterdatafortexas.org/reservoirs/individual/%s-30day.csv" % sta,
    "Reclamation": lambda sta, d0: "https://data.usbr.gov/rise/api/result/download?type=json&itemId=%s&after=%s&before=%s" % (sta, d0 - datetime.timedelta(days=2), d0 + datetime.timedelta(days=6)),
}


def agency_got(ag, text):
    """{aware datetime: elevation ft} from the operator's answer, each in the operator's own clock."""
    if ag == "CDEC":  # CDEC times are Pacific Standard Time all year (its data page)
        pst = datetime.timezone(datetime.timedelta(hours=-8))
        return {datetime.datetime.strptime(r["date"], "%Y-%m-%d %H:%M").replace(tzinfo=pst): float(r["value"]) for r in json.loads(text) if isinstance(r.get("value"), (int, float)) and r["value"] != -9999}
    if ag == "TWDB":  # daily averages, dated; the page stores each at Texas midnight
        lines = [l.split(",") for l in text.splitlines() if l and not l.startswith("#")]
        tx = zoneinfo.ZoneInfo("America/Chicago")
        return {datetime.datetime.combine(datetime.date.fromisoformat(r["date"]), datetime.time(0), tzinfo=tx): float(r["water_level"]) for r in (dict(zip(lines[0], x)) for x in lines[1:]) if r.get("water_level") not in (None, "", "NA")}
    # Reclamation RISE: 'Datetime values are presented as UTC'
    return {datetime.datetime.fromisoformat(v["dateTime"].replace(" ", "T") + "+00:00"): float(v["result"]) for k, v in json.loads(text).items() if k.isdigit() and isinstance(v.get("result"), (int, float))}


def agency_verdict(ag, pt, pv, got):
    """None when the page's elevation pv at time pt is the operator's value for that time, else the mismatch."""
    if pt in got and abs(got[pt] - pv) > 0.005:
        return "lake elevation %s on the page, %s at %s for the same time" % (pv, got[pt], ag)
    if pt not in got and pt < max(got):
        return "the page's reading time %s is not a %s reading" % (pt.isoformat(), ag)
    if (max(got) - pt).total_seconds() / 3600 > STALE_FAIL_H:
        return "page is more than %d h behind %s" % (STALE_FAIL_H, ag)
    return None


def coops_verdict(pt, pv, got):
    """None when the coast page's water level pv at pt is NOAA's value for that minute (0.02 ft, the feed's 3 decimals rounded to 2), else the fault."""
    if not got:
        return None  # no answer proves nothing; the staleness of a dead feed is the page's own banner
    if pt in got and abs(got[pt] - pv) > 0.02:
        return "water level %s on the page, %s at NOAA for the same time" % (pv, got[pt])
    if pt not in got and pt < max(got):
        return "the page's reading time %s is not a NOAA 6-minute reading" % pt.isoformat()
    if (max(got) - pt).total_seconds() / 3600 > STALE_FAIL_H:
        return "page is more than %d h behind NOAA" % STALE_FAIL_H
    return None


GAUGE_ID = re.compile(r'var ID="USGS-(\d{7,15})"|USGS (?:lake )?gauge (\d+)')  # release 2026-11-08 stopped: 11 lake pages say "USGS lake gauge", the old pattern read no id


def selftest():
    T_ = datetime.datetime(2026, 11, 8, 15, 50, tzinfo=datetime.timezone.utc)
    assert tide_verdict(T_, 6.35, {T_: 6.35}) is None and "NOAA predicts" in tide_verdict(T_, 6.0, {T_: 6.35}) and "not a NOAA" in tide_verdict(T_ + datetime.timedelta(minutes=5), 6.35, {T_: 6.35}), "a tide page's next high/low was not checked against NOAA's list"
    assert per_page(["/lake/l%d/" % i for i in range(11)] + ["/river/a/b/"]) and not per_page(["/river/a/b/", "/rivers/tx/"]), "11 failing gauge pages stopped the release (2026-11-08), or a failing hub did not"
    gid = lambda h: (lambda m: m and (m.group(1) or m.group(2)))(GAUGE_ID.search(h))
    assert gid("USGS lake gauge 02334400") == "02334400" and gid("USGS gauge 06893000") == "06893000" and gid('var ID="USGS-08154510",Z') == "08154510", "a lake or river page's gauge id was not read"
    """Review 2026-11-07 #10: each operator branch fails when its clock or value is read wrong."""
    P = lambda s: datetime.datetime.fromisoformat(s)
    c = agency_got("CDEC", '[{"date": "2026-11-06 23:00", "value": 1012.34}, {"date": "2026-11-07 00:00", "value": -9999}]')
    assert c == {P("2026-11-06T23:00:00-08:00"): 1012.34}, c  # PST all year, -9999 dropped
    t = agency_got("TWDB", "# header\ndate,water_level,surface_area\n2026-11-06,677.15,18163\n2026-11-07,NA,1")
    assert t == {P("2026-11-06T00:00:00-06:00"): 677.15}, t  # Texas midnight (CST in November)
    r = agency_got("Reclamation", '{"0": {"dateTime": "2026-11-04 07:00:00", "result": 1062.5}, "meta": {}}')
    assert r == {P("2026-11-04T07:00:00+00:00"): 1062.5}, r  # UTC
    k = P("2026-11-06T23:00:00-08:00")
    assert agency_verdict("CDEC", k, 1012.34, c) is None
    assert "on the page" in agency_verdict("CDEC", k, 1013.0, c)
    assert "not a CDEC reading" in agency_verdict("CDEC", P("2026-11-06T22:30:00-08:00"), 1012.34, c)
    assert "behind" in agency_verdict("CDEC", k - datetime.timedelta(hours=20), 1012.34, {**c, k - datetime.timedelta(hours=20): 1012.34})
    q = P("2026-11-07T13:30:00+00:00")
    nn = {q: 3.41, q + datetime.timedelta(minutes=6): 3.45}
    assert coops_verdict(q, 3.41, nn) is None and "on the page" in coops_verdict(q, 3.9, nn) and "not a NOAA" in coops_verdict(q + datetime.timedelta(minutes=2), 3.41, nn), "a coast page's level was not compared with NOAA's for its own minute"
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        new_fail(td, "/lake/x/", ["/lake/x/: level 1 on the page, 2 at USGS"])
        f = json.load(open(os.path.join(td, "_failed.json")))
        assert f["pages"] == {"lake/x/index.html": ["/lake/x/: level 1 on the page, 2 at USGS"]} and f["site"] == [], "a new page's mismatch was not recorded for quarantine (release 2026-11-07)"
    print("truth_live selftest OK")


def pmap(f, xs):
    """f over xs, WORKERS at a time; an exception in f is raised here, as the serial loop did."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(WORKERS) as ex:
        return list(ex.map(f, xs))


def record(status, compared, bad, skipped):
    """With --dir: write _truth.json into the build so the live site says when its numbers were last checked against USGS and NWS (read by tools/watchdog.py). A skipped check is recorded as skipped, never as ok."""
    if not LOCAL:
        return
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
    agency = []
    try:  # pages check.py --carry replaced with the live copy: they passed their own release, and their age is the live site's
        carried = {"/" + r.rsplit("index.html", 1)[0] for r in (json.load(open(os.path.join(LOCAL, "_carried.json"))) if LOCAL else [])}
    except (OSError, ValueError):
        carried = set()
    urls = [u for _, u, *_ in gauges if u.startswith(("/river/", "/lake/"))]  # coast pages: NOAA CO-OPS, checked below against CO-OPS  # gauges outside the US: tools/truth_world.py checks them against their own feed
    if not LOCAL and len(urls) > SAMPLE:
        k = int(datetime.datetime.now(datetime.timezone.utc).timestamp() // 3600) * SAMPLE % len(urls)
        urls = (urls + urls)[k:k + SAMPLE]
    great = []  # Great Lakes pages (NOAA CO-OPS, IGLD)
    site_of = {g_[1]: str(g_[4]).split()[-1] for g_ in gauges if len(g_) > 4}  # gauges.json: [name, url, lat, lon, "State ST site"]
    html = dict(pmap(lambda u: (u, None if u in carried else page(u)), urls))
    for url in urls:
        if url in carried:
            skipped.append("%s: carried from the live site (this build's page failed a check)" % url)
            continue
        h = html[url]
        if '>Latest flow</span><b>Not published<' in h:  # ice: USGS publishes stage only, so no flow to compare; a page must never fail for saying so
            skipped.append("%s: flow not published by USGS" % url)
            continue
        sid = GAUGE_ID.search(h)
        flow = re.search(r'data-live="flow">([\d,.\-]+)<', h)
        stage = re.search(r'data-live="stage">([\d.\-]+)<', h)
        stage_t = re.search(r'data-live="stageobs" data-t="([^"]+)"', h)
        # the reading time the page actually shows: the edge worker stamps the swapped reading's time on the age chip, so the swapped number is what gets checked
        t = re.search(r'data-live="age" data-t="([^"]+)"', h) or re.search(r'class="hero hero2" data-t="([^"]+)"', h)
        cd_ = re.search(r"(CDEC station|Reclamation RISE item|TWDB reservoir) ([A-Za-z0-9-]+)", h)
        if url.startswith("/lake/") and site_of.get(url, "").startswith("COOPS-"):  # practice 2026-11-08: a Great Lakes page reads NOAA CO-OPS above IGLD, not USGS; checked with the coast pages below
            great.append(url)
            continue
        if url.startswith("/lake/") and cd_:  # a lake read from its operator's feed: checked below against that feed, never USGS
            agency.append((url, cd_.group(1).split()[0], cd_.group(2), stage, t))
            continue
        if url.startswith("/lake/"):  # a lake page shows its elevation in the stage slot and no flow: checked against the USGS lake codes
            if not (sid and stage and t):
                bad.append("%s: cannot read gauge id, lake elevation or time from the page" % url)
            else:
                pages[url] = {"sid": sid.group(1) or sid.group(2), "url": url, "lake": True, "stage": float(stage.group(1)), "t": datetime.datetime.fromisoformat(t.group(1)), "lid": None, "cats": {}, "derived": set()}
            continue
        if not (sid and flow and t):
            bad.append("%s: cannot read gauge id, flow or time from the page" % url)
            continue
        pages[url] = {"sid": sid.group(1) or sid.group(2), "url": url, "flow": float(flow.group(1).replace(",", "")), "stage": float(stage.group(1)) if stage else None, "stage_t": stage_t.group(1) if stage_t else None,
                               "t": datetime.datetime.fromisoformat(t.group(1)), "lid": (re.search(r"forecast point ([A-Z0-9]{5})", h) or [None, None])[1] if "forecast point" in h else None,
                               "cats": {m[0].lower(): float(m[1]) for m in re.findall(r'<li><i style="background:#[0-9a-f]+"></i>(Action|Minor|Moderate|Major) <b>([\d.\-]+) ft</b></li>', h)},
                               # derived NWS sentences: "NWS action stage X ft (D ft above the latest reading)", "Next NWS impact at X ft (D ft above the NWS reading of R ft, ...)"
                               "derived": set(re.findall(r"(?:NWS (action|minor|moderate|major) stage|Next NWS impact at) ([\d.\-]+) ft \(([\d.]+) ft (above|below) (?:the latest reading|the NWS reading of ([\d.\-]+) ft)", h))}
    for u in [u for _, u, *_ in gauges if u.startswith("/coast/")] + great:  # coast pages: the water level on the page against NOAA CO-OPS's latest reading for the same station
        h = page(u)
        sid, st_, t_ = re.search(r"At NOAA station (\d+), ", h) or re.search(r"NOAA tide station (\d+)", h) or re.search(r"COOPS-(\d+)", site_of.get(u, "")),re.search(r'data-live="stage">([\d.\-]+)<', h), re.search(r'data-live="age" data-t="([^"]+)"', h)
        if not (sid and st_ and t_):
            bad.append("%s: cannot read station, water level or time from the page" % u)
            continue
        pt = datetime.datetime.fromisoformat(t_.group(1)).astimezone(datetime.timezone.utc)
        try:  # scale debate 2026-11-07: the old 'latest' call matched the page's minute almost never (6-minute data), so no coast value was ever compared; now from the page's minute to now
            rows_ = json.loads(get("https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=water_level&station=%s&datum=%s&begin_date=%s&end_date=%s&time_zone=gmt&units=english&format=json&application=riverwaterlevels.com" % (
                sid.group(1), "IGLD" if u in great else "MLLW", pt.strftime("%Y%m%d%%20%H:%M"), datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%%20%H:%M"))))["data"]
        except Exception as e:
            (skipped if LOCAL else bad).append("%s: NOAA CO-OPS did not answer (%s)" % (u, str(e)[:60]))
            continue
        v_ = coops_verdict(pt, float(st_.group(1)), {datetime.datetime.fromisoformat(d["t"].replace(" ", "T") + ":00+00:00"): float(d["v"]) for d in rows_ if d.get("v") not in (None, "")})
        if v_:
            bad.append("%s: %s" % (u, v_))
        own, td_ = re.search(r"NOAA tide station (\d+)", h), re.search(r'data-tide="([^"|]+)\|([\d.\-]+)"', h)
        if own and td_:  # the next high or low on the page against NOAA's own list for the page's own station (a prediction-only page has no reading of its own to check)
            tt = datetime.datetime.fromisoformat(td_.group(1)).astimezone(datetime.timezone.utc)
            try:
                hl = json.loads(get("https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=predictions&interval=hilo&station=%s&datum=MLLW&begin_date=%s&range=24&time_zone=gmt&units=english&format=json&application=riverwaterlevels.com" % (
                    own.group(1), (tt - datetime.timedelta(hours=1)).strftime("%Y%m%d%%20%H:%M"))))["predictions"]
            except Exception as e:
                (skipped if LOCAL else bad).append("%s: NOAA hilo did not answer (%s)" % (u, str(e)[:60]))
                continue
            v_ = tide_verdict(tt, float(td_.group(2)), {datetime.datetime.fromisoformat(d["t"].replace(" ", "T") + ":00+00:00"): float(d["v"]) for d in hl})
            if v_:
                bad.append("%s: %s" % (u, v_))
    for u, ag, sta, st_, t_ in agency:  # the page's elevation against the operator's own value for the same time
        if not (st_ and t_):
            bad.append("%s: cannot read lake elevation or time from the page" % u)
            continue
        pt = datetime.datetime.fromisoformat(t_.group(1))
        d0 = (pt - datetime.timedelta(hours=8)).date()
        try:
            got = agency_got(ag, get(AGENCY_URL[ag](sta, d0)))
        except Exception as e:
            (skipped if LOCAL else bad).append("%s: %s did not answer (%s)" % (u, ag, str(e)[:60]))
            continue
        if not got:
            (skipped if LOCAL else bad).append("%s: %s returned no elevation" % (u, ag))
        else:
            v_ = agency_verdict(ag, pt, float(st_.group(1)), got)
            if v_:
                bad.append("%s: %s" % (u, v_))
    ids = sorted({pg["sid"] for pg in pages.values()})  # gate audit 2026-11-08: keyed by url, so two pages on one gauge (owner decision 7) are both compared
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
    def nws(lid):
        try:
            return lid, json.loads(get(NWPS % lid))
        except Exception as e:
            return lid, e
    nwps = dict(pmap(nws, sorted({pg["lid"] for pg in pages.values() if pg["lid"] and (pg["cats"] or pg["derived"])})))
    for pg in pages.values():
        sid = pg["sid"]
        if pg.get("lake"):
            got = [latest[(sid, c)] for c in ("62614", "62615", "72020", "00062") if (sid, c) in latest]
            if not got:
                (skipped if sid in failed_ids else bad).append("%s: USGS %s" % (pg["url"], "batch did not answer (skipped)" if sid in failed_ids else "returned no latest lake elevation"))
            elif any(gt == pg["t"] for gt, _ in got):
                if not any(gt == pg["t"] and abs(gv - pg["stage"]) <= 0.02 for gt, gv in got):
                    bad.append("%s: lake elevation %s on the page, USGS %s for the same time" % (pg["url"], pg["stage"], [gv for gt, gv in got if gt == pg["t"]]))
            elif max(gt for gt, _ in got) > pg["t"] and (max(gt for gt, _ in got) - pg["t"]).total_seconds() / 3600 > STALE_FAIL_H:
                bad.append("%s: page is more than %d h behind USGS" % (pg["url"], STALE_FAIL_H))
            continue
        u = latest.get((sid, "00060"))
        if not u:
            (skipped if sid in failed_ids else bad).append("%s: USGS %s" % (pg["url"], "batch did not answer (skipped)" if sid in failed_ids else "returned no latest flow"))
            continue
        ut, uv = u
        if ut == pg["t"]:
            if abs(uv - pg["flow"]) > max(1.0, 0.01 * abs(uv)):
                bad.append("%s: flow %s on the page, %s at USGS for the same time %s" % (pg["url"], pg["flow"], uv, ut.isoformat()))
            s_ = latest.get((sid, "00065"))
            if pg.get("stage_t") and pg["stage"] is not None:  # the tile states its own older reading time: USGS latest is a later reading, not a contradiction
                skipped.append("%s: stage is labelled with its own reading time (older than the flow)" % pg["url"])
            elif s_ and s_[0] == pg["t"] and pg["stage"] is not None:
                if abs(s_[1] - pg["stage"]) > 0.02:
                    bad.append("%s: stage %s on the page, %s at USGS" % (pg["url"], pg["stage"], s_[1]))
            elif pg["stage"] is not None:  # stage shown on the page but USGS has no stage at the page's timestamp: record as skipped, not silently ignored
                skipped.append("%s: stage not verified (no USGS stage at the page's timestamp)" % pg["url"])
        elif ut < pg["t"]:  # gate audit 2026-11-08: a page time after USGS's latest is a future time or a time-zone slip. Practice: Selway's USGS 'latest' is from 2010 (the page reads another series), so only a real slip (1-26 h) or a time past now fails
            gap_h = (pg["t"] - ut).total_seconds() / 3600
            (bad if pg["t"] > datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15) or 1 < gap_h <= 26 else skipped).append("%s: page reading time %s is after USGS's latest %s (future time or wrong time zone)" % (pg["url"], pg["t"].isoformat(), ut.isoformat()))
        elif ut > pg["t"]:
            lag = (ut - pg["t"]).total_seconds() / 3600
            # a lagging page is stale, not WRONG (it shows its real age). A short lag is normal; only an extreme lag means our refresh is actually broken.
            if lag > STALE_FAIL_H:
                bad.append("%s: page is %.1f h behind USGS (page %s, USGS %s)" % (pg["url"], lag, pg["t"].isoformat(), ut.isoformat()))
            elif lag > MAX_LAG_H:
                stale.append("%s: page is %.1f h behind USGS (USGS reads %s; the page shows this age)" % (pg["url"], lag, ut.isoformat()))
        if pg["lid"] and (pg["cats"] or pg["derived"]):
            nj = nwps[pg["lid"]]
            if isinstance(nj, Exception):
                e = nj
                if LOCAL:  # an NWS outage must not freeze fresh USGS data: the flood stages stay unchecked and the skip is recorded
                    skipped.append(pg["lid"])
                    continue
                bad.append("%s: NWS forecast point %s did not answer (%s)" % (pg["url"], pg["lid"], str(e)[:60]))
                continue
            cats = (nj.get("flood") or {}).get("categories") or {}
            for k, v in pg["cats"].items():
                nv = (cats.get(k) or {}).get("stage")
                if not isinstance(nv, (int, float)) or abs(nv - v) > 0.05:
                    bad.append("%s: %s flood stage %.1f ft on the page, %s at NWS %s" % (pg["url"], k, v, nv, pg["lid"]))
            # derived sentences against the source, not against our own math (flood site 2026-10-27: gates checked numbers against each other, not the truth)
            imp = [i.get("stage") for i in ((nj.get("flood") or {}).get("impacts") or []) if isinstance(i.get("stage"), (int, float))]
            obs = (nj.get("status") or {}).get("observed") or {}
            s_ = latest.get((sid, "00065"))
            for cat, x, d, way, nref in pg["derived"]:
                x, d = float(x), float(d)
                src = [(cats.get(cat) or {}).get("stage")] if cat else imp
                if not any(isinstance(v, (int, float)) and abs(v - x) <= 0.05 for v in src):
                    bad.append("%s: '%s %.1f ft' on the page, NWS %s publishes %s" % (pg["url"], "NWS %s stage" % cat if cat else "next NWS impact at", x, pg["lid"], src[:6]))
                nt = obs.get("validTime") and datetime.datetime.fromisoformat(obs["validTime"].replace("Z", "+00:00"))
                same_t = s_ and nt and s_[0] == nt and isinstance(obs.get("primary"), (int, float)) and obs["primary"] > -900
                if not nref and same_t and abs(obs["primary"] - s_[1]) > 0.3:  # measured from the USGS reading, but NWS reads the river on another zero point
                    bad.append("%s: distance to NWS %.1f ft is measured from the USGS reading %.2f ft, but NWS reads %.2f ft at the same time (different zero point)" % (pg["url"], x, s_[1], obs["primary"]))
                if LOCAL:  # arithmetic on the numbers as built (live pages get a newer reading swapped in at the edge, the sentence keeps its build-time reading)
                    ref = float(nref) if nref else pg["stage"]
                    if ref is not None and (abs(abs(x - ref) - d) > 0.06 or (way == "above") != (x > ref)):
                        bad.append("%s: '%.1f ft %s' %.1f ft, but %.1f - %.2f = %.2f" % (pg["url"], d, way, x, x, ref, x - ref))
    record("mismatch" if bad else ("skipped" if len(skipped) > max(3, len(pages) // 20) else "ok"), len(pages), bad, skipped)
    n_noaa = sum(1 for _, u, *_ in gauges if u.startswith("/coast/")) + len(great)
    print("truth_live: %d gauge pages compared with USGS and NWS, %d with their operator (CDEC, Reclamation, TWDB), %d coast and Great Lakes pages with NOAA (Great Lakes: %s), %d mismatches, %d skipped%s" % (
        len(pages), len(agency), n_noaa, ", ".join(great) or "none", len(bad), len(skipped), (": %s" % "; ".join(str(x)[:90] for x in skipped[:6])) if skipped else ""))
    for b in bad[:25]:
        print("  MISMATCH", b)
    for s in stale[:25]:
        print("  STALE (warning, not a failure)", s)
    if stale:
        print("truth_live: %d gauge(s) lagging USGS by 3 to %d h (warning only; the pages show their real age)" % (len(stale), STALE_FAIL_H))
    urls_ = sorted({b.split(": ", 1)[0] for b in bad})
    if LOCAL and bad and len(urls_) > max(3, len(pages) // 20):  # many at once is a checker or feed fault: still page by page (a carried page is its verified live copy), but said loudly; the watchdog names release days that ship nothing
        print("truth_live WARNING: %d of %d pages failed at once (checker wording or a feed outage?); each keeps its live copy or goes back to the queue" % (len(urls_), len(pages)))
    if LOCAL and bad and per_page(urls_):  # owner 2026-11-08 "fully automatic": one page never stops the release (2026-11-08: 11 unreadable lake pages over the old cap of 10 undid all 20 US picks); every failing page keeps its live copy or is sent back
        cp = os.path.join(LOCAL, "_carried.json")
        try:
            carried = json.load(open(cp))
        except (OSError, ValueError):
            carried = []
        newf = []
        for u in urls_:
            try:
                html = urllib.request.urlopen(urllib.request.Request("https://riverwaterlevels.com" + u, headers={"User-Agent": "riverwaterlevels.com truth_live"}), timeout=30).read()
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    print("truth_live: could not carry", u, str(e)[:60])
                    return 1
                new_fail(LOCAL, u, [b for b in bad if b.startswith(u + ":")])  # release 2026-11-07: deleting the page left its links and sitemap entry and stopped the publish; now quarantine.py sends it back to the queue and the retry builds without it
                newf.append(u)
                continue
            except Exception as e:
                print("truth_live: could not carry", u, str(e)[:60])
                return 1
            open(os.path.join(LOCAL, u.strip("/"), "index.html"), "wb").write(html)
            carried.append(u.strip("/") + "/index.html")
            print("CARRIED previous live page for", u, "(this build's numbers did not match the source)")
        json.dump(sorted(set(carried)), open(cp, "w"))
        return 1 if newf else 0  # a new page that failed: the workflow's second try sends it back (quarantine.py reads _failed.json) and ships the rest
    return 1 if bad else 0


def tide_verdict(t, v, hilo):
    """None when NOAA lists a high or low at the page's minute with the page's height (0.01 ft); else what differs. hilo: {utc time: ft}."""
    if t not in hilo:
        return "next tide %s is not a NOAA high or low time for this station" % t.isoformat()
    return None if abs(hilo[t] - v) <= 0.01 else "next tide %.3f ft on the page, NOAA predicts %.3f ft" % (v, hilo[t])


def per_page(urls):
    """True when every failing url is a gauge page, so each is carried or sent back and the rest ship; any other url (a hub, home) stops the publish. No count cap."""
    return all(u.startswith(("/river/", "/lake/", "/coast/")) for u in urls)


sys.exit(selftest() if "--selftest" in sys.argv else main())
