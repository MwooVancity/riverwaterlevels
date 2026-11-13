"""Fixtures for paths only a rare real event reaches: an ice flag, a frozen feed, an outage over a live page, a lost cache in a new year. Run by check.py --selftest."""
import datetime, email.utils, json, os, re, sys, tempfile, types, zoneinfo
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import collect
from lib import world
from lib import wx as wx_mod


def run():
    import gates as g_  # gate catch census: a page gate counts each caught page, a self-test only its own failure (fixtures print FAULT on purpose)
    out_ = "FAIL river/a/index.html\n    no Source line\nCARRIED previous live page for b\n  MISMATCH c: 5 vs 6\nKAUB FAULT page says no alerts\nworld truth: 1 fault(s)\npages 9, failing 1"
    assert g_.catches("page checks", out_, 1) == 4 and g_.catches("truth fixtures", out_, 0) == 0 and g_.catches("truth fixtures", "", 1) == 1 and g_.catches("built pages vs USGS/NWS", "truth_live: 0 mismatches", 0) == 0, "edge: gate catches miscounted"
    from tools import world_queue as wq_  # PLAN step 6: two same-name lakes in two states; a bare keyword credits neither, a keyword naming the state credits that one
    two_ = {wq_.core("clear lake"): {"CA", "IA"}, wq_.core("lake mead"): {"NV"}}
    assert wq_.namesake(wq_.core("clear lake"), "IA", "clear lake level", two_).startswith("held: 2 states"), "edge: a bare same-name keyword was credited to one state's lake"
    assert wq_.namesake(wq_.core("clear lake"), "IA", "clear lake iowa water level", two_) == "" and wq_.namesake(wq_.core("clear lake"), "CA", "clear lake ca", two_) == "", "edge: a keyword naming the state was held"
    assert wq_.namesake(wq_.core("clear lake"), "CA", "clear lake iowa water level", two_).startswith("held"), "edge: Iowa's search credited to California's Clear Lake"
    assert wq_.namesake(wq_.core("lake mead"), "NV", "lake mead water level", two_) == "", "edge: a one-state name was held"
    assert wq_.namesake(wq_.core("clear lake"), "KS", "clear lake arkansas", {wq_.core("clear lake"): {"KS", "AR"}}).startswith("held"), "edge: 'arkansas' read as naming Kansas"
    # full audit 2026-11-10: a coast station on a pier sits outside every marine zone; the nearest zone within the ring is used, an NWS outage raises
    real = collect.thr_json
    try:
        collect.thr_json = lambda u, *a, **k: {"features": [{"properties": {"id": "PZZ210"}}]} if "point=46.2073,-123.8683" in u else {"features": []}
        assert collect.marine_zone(46.2073, -123.7683, ring=True) == "PZZ210", "edge: coast station outside its marine zone found no zone"
        assert collect.marine_zone(46.2073, -123.7683) == "", "edge: a river gauge searched the ring"
        assert collect.marine_zone(10.0, 10.0, ring=True) == "", "edge: no zone nearby is not ''"
        collect.thr_json = lambda u, *a, **k: (_ for _ in ()).throw(OSError("down"))
        try:
            collect.marine_zone(46.2, -123.7, ring=True)
            raise AssertionError("edge: NWS down was stored as 'no marine zone'")
        except OSError:
            pass
    finally:
        collect.thr_json = real
    from lib import render  # noqa: F401  (build import order)
    from lib.directory import hub_summary  # river hub summary (Search Console 2026-11-11: thin 2-row hubs not indexed)
    nw = datetime.datetime.now(datetime.timezone.utc)
    hg = lambda **k: dict({"offline": False, "osc": False, "chg": -5.0, "p": 50, "now": nw, "rec": {"nws": {"alerts": []}}}, **k)
    hr = [{"site": "1", "place": "Marianna"}, {"site": "2", "place": "Altha"}, {"site": "3", "place": "Blountstown"}]
    hs = hub_summary(hr, {"1": hg(), "2": hg(chg=12.0, p=95, rec={"nws": {"alerts": [{"event": "Flood Warning", "ends": (nw + datetime.timedelta(hours=5)).isoformat()}]}}), "3": hg(offline=True)})
    assert "Marianna is typical" in hs and "falling" in hs and "Altha is much above normal and rising" in hs.lower().replace("altha", "Altha") and "Blountstown is not reporting" in hs and "Flood Warning (Altha)" in hs, "edge: river hub summary wrong: %s" % hs
    assert not re.search(r"\d+ ?(cfs|ft|%)", hs), "edge: hub summary carries a number the live table can contradict"
    assert hub_summary(hr[:1], {"1": hg(chg=None, p=None)}) == "", "edge: hub with nothing known says something"
    from lib.directory import hub_page  # the whole hub page builds (2026-11-11: the summary broke the page's own string formatting and stopped the build)
    hp_ = hub_page("chipola-river", "FL", [dict(r, river="Chipola River", drainage_sqmi="464", water_url="/river/chipola-river/x/") for r in hr[:2]],
                   2, {"1": hg(obs="Nov 10, 8:00 PM CST", lv=274.0, flow=274.0), "2": hg(obs="Nov 10, 8:00 PM CST", lv=706.0, flow=706.0)})
    assert "Right now: Marianna is" in hp_ and "2 of 2 gauges in Florida" in hp_, "edge: river hub page did not build with its summary"
    assert 'id="river_flow"' not in hp_ and 'id="river_forecast_all"' not in hp_ and 'id="river_access"' not in hp_, "edge: hub sections drawn with no data"
    # owner 2026-11-11 option 2: the hub's own data (all gauges' 7 days on one chart, each forecast crest, access along the river with its nearest gauge)
    zn = zoneinfo.ZoneInfo("America/Chicago")
    fl_ = lambda base: [(nw - datetime.timedelta(hours=h), base + h, None) for h in range(48, -1, -6)]
    fc_ = {"issued": (nw - datetime.timedelta(hours=3)).isoformat(), "primary_units": "ft", "points": [{"t": (nw + datetime.timedelta(hours=h)).isoformat(), "primary": 5.0 + h / 10, "secondary": None} for h in (6, 12, 18)]}
    ac_ = lambda mi: {"rows": [{"name": "Hwy 20 Landing", "type": "Boat ramp", "mi": mi}, {"name": "", "type": "Boat ramp", "mi": 1.0}]}
    hp2 = hub_page("chipola-river", "FL", [dict(r, river="Chipola River", drainage_sqmi="464", water_url="/river/chipola-river/x/") for r in hr[:2]], 2,
                   {"1": hg(obs="x", lv=274.0, flow=274.0, fl=fl_(270.0), zone=zn, rec={"nws": {"alerts": []}, "nwps": {"forecast": fc_}, "access": ac_(3.2)}),
                    "2": hg(obs="x", lv=706.0, flow=706.0, fl=fl_(700.0), zone=zn, rec={"nws": {"alerts": []}, "access": ac_(1.4), "related": {"items": [{"site": "1", "relation": "upstream", "lag_h": 9, "lag_r": 0.93}]}})})
    assert 'id="river_lag"' in hp2 and "about 9 h" in hp2 and "not a measured travel time" in hp2, "edge: hub lag between neighbouring gauges missing or claims a travel time"
    assert 'id="river_flow"' in hp2 and hp2.count("<polyline") == 4, "edge: hub flow chart missing (2 gauges, 2 sizes)"
    assert 'id="river_forecast_all"' in hp2 and "6.8 ft" in hp2 and "No NWS river forecast is issued for the other 1 gauge." in hp2, "edge: hub forecast table wrong"
    # state hub: the state today (rankings need 4 gauges with data; a gauge not reporting is never ranked)
    from lib.directory import state_blocks
    sr = [{"site": str(i), "place": "P%d" % i, "river": "R%d River" % i, "water_url": "/river/r%d/p/" % i} for i in range(6)]
    sg = {str(i): hg(p=p, chg=c) for i, (p, c) in enumerate(((95, 40.0), (50, 0.0), (5, -30.0), (80, 10.0), (20, -5.0), (99, 90.0)))}
    sg["5"]["offline"] = True
    sb = state_blocks(sr, sg)
    assert 'id="state_extremes"' in sb and sb.index("R0 River") < sb.index("R3 River") and "P5" not in sb.split('id="state_movers"')[0], "edge: state ranking wrong or ranks a silent gauge"
    assert 'id="state_movers"' in sb and "+40%" in sb and "-30%" in sb and "0%" not in re.sub(r"[+-]\d+%", "", sb), "edge: state movers wrong (a steady gauge listed as a mover)"
    assert state_blocks(sr[:3], {k: sg[k] for k in ("0", "1", "2")}) == "", "edge: a state ranking drawn from 3 gauges"
    zc = zoneinfo.ZoneInfo("America/Chicago")
    fresh, stale = (nw - datetime.timedelta(minutes=20)).isoformat(), (nw - datetime.timedelta(hours=5)).isoformat()
    fw = {"event": "Flood Warning", "severity": "Severe", "ends": (nw + datetime.timedelta(hours=10)).isoformat()}
    sa = {"0": hg(zone=zc, rec={"nws": {"fetched_at": fresh, "alerts": [fw, {"event": "Test Message"}, dict(fw, event="Flood Watch", ends=(nw - datetime.timedelta(hours=1)).isoformat())]}}),
          "1": hg(zone=zc, rec={"nws": {"fetched_at": stale, "alerts": [dict(fw, event="Old Warning")]}}), "2": hg(zone=zc, rec={"nws": {"fetched_at": fresh, "alerts": None}}), "3": hg(zone=zc, rec={"nws": {"fetched_at": fresh, "alerts": []}})}
    sb2 = state_blocks(sr[:4], sa)
    assert 'id="state_alerts"' in sb2 and sb2.count("Flood Warning") == 1 and "R0 River" in sb2.split('id="state_alerts"')[1], "edge: state hub misses an NWS alert in force at a gauge"
    assert "Test Message" not in sb2 and "Flood Watch" not in sb2 and "Old Warning" not in sb2 and "unknown for 2 gauges" in sb2, "edge: state hub shows a test, ended or stale alert, or counts a failed check as no alert"
    assert 'id="state_alerts"' not in state_blocks(sr[:4], {k: hg(zone=zc, rec={"nws": {"fetched_at": fresh, "alerts": []}}) for k in "0123"}), "edge: state hub draws an empty alert section"
    assert 'id="river_access"' in hp2 and hp2.count("Hwy 20 Landing") == 1 and "Altha, 1.4 mi" in hp2, "edge: hub access list not deduplicated to the nearest gauge"
    from lib.blocks3 import acis_name  # PLAN 0b: station codes in plain words
    for raw, want in (("SAN DIEGO 6.6 S", "6.6 mi south of San Diego"), ("NORTH ISLAND NAS", "North Island Naval Air Station"), ("SAN DIEGO INTL AP", "San Diego International Airport"),
                      ("CHEVY CHASE 1.2 SW", "1.2 mi southwest of Chevy Chase"), ("BOULDER 2 NNE", "2 mi north-northeast of Boulder"), ("ZZ 3 XQ", "Zz 3 Xq"), ("", "")):
        assert acis_name(raw) == want, "edge: station name %r gave %r" % (raw, acis_name(raw))
    from lib.world import fc_top  # full audit #9: a BfG row PEGELONLINE marks as an estimate is said as one in the tile
    nw_ = datetime.datetime.now(datetime.timezone.utc)
    f_ = lambda typ: {"fc": {"at": nw_.isoformat(), "pts": [[(nw_ + datetime.timedelta(hours=6)).isoformat(), 57.0, typ], [(nw_ + datetime.timedelta(hours=3)).isoformat(), 40.0, "forecast"]]}, "zone": "Europe/Berlin"}
    assert fc_top(f_("estimate"), nw_)[1:] == (57.0, True) and fc_top(f_("forecast"), nw_)[2] is False and fc_top(f_(None), nw_)[2] is False, "edge: a BfG estimate shown as a forecast"
    # PLAN 0i: lakes read their past years in their own elevation code; never as flow, never in another datum than the page shows
    assert collect.lake_code({"usgs": {"rows": [{"parameter_code": "00062"}, {"parameter_code": "00065"}]}}) == "00062", "edge: lake history not in the lake's code"
    assert collect.lake_code({"usgs": {"rows": [{"parameter_code": "00060"}, {"parameter_code": "00062"}]}}) == "00060", "edge: a gauge with flow lost its flow history"
    assert collect.lake_code({}) == "00060", "edge: empty record"
    from lib.charts import b_multiyear
    from lib.hero import last_year_flow
    td = datetime.date.today()
    my = {"as_of": td.isoformat(), "span": 3, "series": {str(td.year): [1000.0, 1001.0, 1002.0], str(td.year - 1): [990.0, 991.0, 992.0]}, "pc": "00062"}
    bl = b_multiyear({"rec": {"multiyear": my}, "ldate": td, "lake": "00062"})
    assert bl and "1001.00 ft" in bl["body"] and "cfs" not in bl["body"] + bl["source"], "edge: lake past years not shown in ft"
    assert b_multiyear({"rec": {"multiyear": my}, "ldate": td, "lake": "62614"}) is None, "edge: lake history in another datum than the page"
    assert last_year_flow({"rec": {"multiyear": my}, "ldate": td}) is None, "edge: a lake level read as last year's flow"
    # owner 2026-11-12: research pages (lib/research.py; edge cases in PLAN 14, 15, 17)
    from lib import research
    rb, rG = [], {}
    for i in range(12):  # 12 gauges, peaks 1960-2025: even gauges peak in March and doubled after WY2005, odd in May and unchanged
        s = "g%d" % i
        rb.append({"site": s, "state": "GA" if i < 6 else "TX", "river": "River %d" % i, "place": "Town", "dashboard_url": "/river/r%d/town/" % i, "_built": True})
        rG[s] = {"rec": {"peaks": {"rows": [["%d-%s-15" % (y, "03" if i % 2 == 0 else "05"), (200.0 + y % 7 if y > 2005 else 100.0 + y % 7) if i % 2 == 0 else 100.0 + y % 7, None, None, ""] for y in range(1960, 2026)]
                                    + [["1950-00-00", 5.0, None, None, ""], ["1955-03-15", None, 4.0, None, ""], ["1956-03-15", 0.0, None, None, ""], ["2010-04-15", 50.0, None, None, ""],  # unknown date, stage-only, zero, secondary peak
                                       ["1940-04-15", 900.0, None, None, "HISTORIC"], ["1941-04-15", 900.0, None, None, "MAXDAILYMEAN"], ["1942-04-15", 900.0, None, None, "DAMFAILURE"], ["1943-04-15", 900.0, None, None, "GREATERTHAN"],
                                       ["1944-04-15", 900.0, None, None, "MONTHUNKNOWN"], ["1945-04-15", 900.0, None, None, "ESTIMATED NEWCODE"]]}}}  # dropped codes; ESTIMATED kept; an unknown code counted
    rb.append({"site": "g0", "state": "GA", "river": "Other Creek", "place": "Town", "dashboard_url": "/river/other/town/", "_built": True})  # the same gauge on a second page
    rb.append({"site": "lk", "state": "GA", "river": "Lake", "place": "Dam", "dashboard_url": "/lake/x/", "_built": True})
    rG["lk"] = {"lake": "00062", "rec": {"peaks": {"rows": [["%d-01-01" % y, 9.0, None, None, ""] for y in range(1960, 2000)]}}}
    rb.append({"site": "tie", "state": "TX", "river": "Tie River", "place": "Town", "dashboard_url": "/river/tie/town/", "_built": True})
    rG["tie"] = {"rec": {"peaks": {"rows": [["%d-%s-15" % (y, "03" if y % 2 else "04"), 10.0, None, None, ""] for y in range(1960, 2000)]}}}  # 20 March, 20 April
    rb.append({"site": "old", "state": "TX", "river": "Old Cache", "place": "Town", "dashboard_url": "/river/old/town/", "_built": True})
    rG["old"] = {"rec": {"peaks": {"rows": [["%d-03-15" % y, 10.0, None, None] for y in range(1960, 2026)]}}}  # written before qualifiers were stored
    rb.append({"site": "dam", "state": "TX", "river": "Dam River", "place": "Town", "dashboard_url": "/river/dam/town/", "_built": True})
    rG["dam"] = {"rec": {"peaks": {"rows": [["%d-06-15" % y, 50.0 + y % 5, None, None, "REGULATED"] for y in range(1960, 2026)]}}}
    rp, rc = research.pages(rb, rG, datetime.date(2026, 11, 12))
    assert set(rp) == {"/research/", "/research/peak-month/", "/research/peak-change/"} and set(rp) <= set(research.URLS) and set(rc) == {"/research/peak-month/", "/research/peak-change/"}, "edge: research pages or CSVs missing, a page with no data built, or build.py's carry list misses one: %s %s" % (sorted(rp), sorted(rc))
    pm, pc_ = rp["/research/peak-month/"], rp["/research/peak-change/"]
    assert "most often comes in March: at 6 of 13 gauges, then May (6)" in pm, "edge: peak month counts wrong (duplicate gauge, lake, old cache row or regulated gauge counted)"
    assert "1 regulated gauge is listed but not counted" in pm and "Dam River at Town (regulated)" in pm and "Old Cache" not in pm + pc_, "edge: regulated gauge not apart, or an old cache row (no qualifiers) used"
    assert "/lake/x/" not in pm + pc_ and "/river/other/town/" not in pm, "edge: lake or second page of one gauge listed"
    assert "March (66 of 67 years, 99%)" in pm, "edge: a secondary peak, unknown date, no-flow row or a dropped code was counted (1945 ESTIMATED is kept: 67 water years)"
    assert "NEWCODE (12 peaks)" in pm, "edge: an unknown USGS code was not named on the page"
    assert "1 gauge split evenly between two or more months and is not counted" in pm and "March and April (20 of 40 years, 50% each)" in pm, "edge: tie not named"
    assert research._wy(2020, 10) == 2021 and research._wy(2020, 9) == 2020, "edge: water-year boundary"
    assert "At 6 of 12 gauges, yearly peaks in water years 2006 to 2025 differ from 1986 to 2005 by more than chance alone explains: 6 higher, 0 lower." in pc_ and "about 0.3 each way by chance" in pc_ and "Hodges-Lehmann" in pc_, "edge: peak change test counts or windows wrong: %s" % pc_[pc_.find("<b>"):pc_.find("<b>") + 400]
    assert "not a trend analysis" in pc_ and "says nothing about flood damage or why" in pc_ and "Mann-Whitney" in pc_ and "not a random or representative sample" in pc_, "edge: peak change lost its limits, its test or its sample statement"
    assert research.mwu_p([5.0] * 20, [5.0] * 20) == 1.0 and research.mwu_p(list(range(20)), list(range(100, 120))) < 0.001 and 0.1 < research.mwu_p([1.0, 3.0, 5.0, 7.0] * 5, [2.0, 4.0, 6.0, 8.0] * 5) <= 1.0 and abs(research.mwu_p([1, 2, 3, 4, 5], [6, 7, 8, 9, 10]) - 0.0122) < 0.0005, "edge: Mann-Whitney wrong on ties, separation or overlap"
    assert abs(research.poisson_tail(3, 1.0) - 0.0803) < 0.001 and abs(research.poisson_tail(0, 2.0) - 0.1353) < 0.001 and 0 <= research.poisson_tail(400, 300.0) < 0.001, "edge: Poisson tail wrong or underflows at 300"
    assert "usgs_site,river,place,state,page" in rc["/research/peak-change/"] and "mann_whitney_p" in rc["/research/peak-change/"] and 'href="data.csv"' in pc_, "edge: CSV header or download link missing"
    assert research._csv(["a", "b"], [["=SUM(A1)", ""], [-3, "x"], ["-x", ""]]) == "a,b\n'=SUM(A1),\n-3,x\n'-x,\n", "edge: CSV formula cell not neutralised, a negative number changed, or an empty cell got an apostrophe (live 100-year CSV, 2026-11-12)"
    assert 'data-method="%s"' % research.method_of("/research/peak-month/") in pm, "edge: research page lacks its method mark, so build.py could never carry it (and could carry an old-method copy)"
    assert research.pages(rb, rG, datetime.date(2026, 11, 20)) == (rp, rc), "edge: same data on another day gave a different page (fresh date without change)"
    assert research.pages(rb[:5], rG, datetime.date(2026, 11, 12)) == ({}, {}) and research.pages([], {}) == ({}, {}), "edge: research published from under 10 gauges, or empty cache crashed"
    same = [(r, research._peaks(rG[r["site"]]), rG[r["site"]]) for r in rb[:12] if int(r["site"][1:]) % 2 == 0] * 2
    one = research.peak_month(same, "", {})[1]
    assert "most often comes in March: at 12 of 12 gauges.</b>" in one, "edge: every gauge in one month broke the lead"
    cap_, research.ROW_CAP = research.ROW_CAP, 5
    try:
        assert "9 more gauges are not listed here" in research.pages(rb, rG, datetime.date(2026, 11, 12))[0]["/research/peak-month/"], "edge: a cut table did not say so"
    finally:
        research.ROW_CAP = cap_
    assert "BreadcrumbList" in pm and 'href="/research/peak-change/"' in rp["/research/"], "edge: research index or breadcrumb missing"
    # gauge page: a water year counts once at its highest stage (PLAN 17)
    from lib import blocks3 as _b3r
    sy_g = {"rec": {"nwps": {"categories": {"minor": 10.0}}, "peaks": {"rows": [["%d-03-01" % y, 1.0, 9.0, None, ""] for y in range(2000, 2012)] + [["2005-04-01", 1.0, 11.0, None, ""]]}}}
    sp_, dg_ = _b3r.stage_pair, _b3r.datum_gap
    _b3r.stage_pair, _b3r.datum_gap = (lambda G: (1, 1, None)), (lambda G: None)
    try:
        sy = _b3r.stage_years(sy_g)
    finally:
        _b3r.stage_pair, _b3r.datum_gap = sp_, dg_
    assert sy and len(sy[0]) == 12 and sum(1 for x in sy[0] if x[2] >= 10.0) == 1, "edge: a secondary stage peak counted as its own year on the gauge page"
    # PLAN 15: 100-year floods, flood stage years, water temperature; 70 gauges so the link budget is tested at size
    bb, bG = [], {}
    for i in range(70):
        s_ = "h%d" % i
        bb.append({"site": s_, "state": "GA", "river": "Big %d" % i, "place": "Town", "dashboard_url": "/river/b%d/town/" % i, "_built": True})
        ff = {"rows": [{"aep": 1, "q": 1000.0, "lo": 800.0, "hi": 1300.0}, {"aep": 10, "q": 500.0}], "range": "1950 to 2000", "range1": [1950, 2000], "regulated": i % 7 == 0}
        if i == 1: ff["conflict"] = True
        if i == 2: ff["range1"] = None  # the 1% row states no date range
        if i == 3: ff["rows"] = [{"aep": 10, "q": 500.0}]
        if i == 4: ff["range1"] = [1950, 2024]  # under 5 years after
        mo = {str(m): [10.0 + i * 0.2, 400] for m in range(1, 13)}
        mo["7"] = [12.0 + i * 0.25, 400]
        if i == 5: mo["7"] = [30.0, 100]  # July with too few days: gauge has no July
        if i == 6: mo["1"] = "bad"
        bG[s_] = {"rec": {"peaks": {"rows": [["%d-03-15" % y, 1200.0 if (y in (2010, 2020) and i % 2 == 0) else 400.0, 10.0 + (y % 3), None, ""] for y in range(1950, 2026)]}, "floodfreq": ff,
                          "wtemp": {"months": mo, "first_year": "1990", "last_year": "2026"}}, "_minor": 11.5}
    st_ = _b3r.stage_years
    _b3r.stage_years = lambda G: ([r for r in G["rec"]["peaks"]["rows"]], {"minor": G["_minor"]}, {}) if G.get("_minor") else None
    try:
        bp, bc = research.pages(bb, bG, datetime.date(2026, 11, 12))
    finally:
        _b3r.stage_years = st_
    riv_ = set(research.URLS) - {"/research/lake-levels/", "/research/tides/"}  # this fixture has no lakes or coasts
    assert set(bp) == riv_ and set(bc) == riv_ - {"/research/"}, "edge: a research page or CSV missing: %s" % sorted(riv_ - set(bp))
    hy, fs, wt = bp["/research/100-year-floods/"], bp["/research/flood-stage-years/"], bp["/research/water-temperature/"]
    assert "At 56 US river gauges on this site, USGS's '100-year' flow was reached in 56 of 1400 gauge-years after the last year of the record it was computed from" in hy and "about 14.0 would be expected" in hy and "The 56 fell in only 2 water years, so some came in the same water year" in hy and "is &lt;0.001" in hy and "At 10 regulated gauges, counted apart" in hy, "edge: 100-year counts or Poisson chance wrong (conflict, no range, no 1%% row or too few years counted; regulated not split): %s" % hy[hy.find("<b>"):hy.find("<b>") + 400]
    assert "at 56 of these gauges (the interval's level is not stated in the data we read): 56 gauge-years reached its lower end and 0 its upper end" in hy and "expected" not in hy[hy.find("interval USGS publishes"):hy.find("upper end")], "edge: confidence-bound counts wrong"
    assert "not one flood per century" in hy and "1%%" not in hy and "/river/b1/town/" not in hy and "that chance is too small" in hy and "rises after floods" in hy, "edge: 100-year page lost its plain meaning or its independence caveat, shows a double percent, or lists a conflicting statistic"
    assert "reached minor flood stage in 33% of years" in fs and "never at 0" in fs, "edge: flood stage share wrong: %s" % fs[fs.find("<b>"):fs.find("<b>") + 300]
    assert "In July, the median gauge on these rivers averages" in wt and "Across 69 US river gauges" in wt and "–" in wt and "1990 to 2026" in wt and max(len(re.findall(r"<th ", t_)) for t_ in wt.split("</table>")) <= 5, "edge: water temperature kept a thin July, crashed on a bad month, lost the record years, or a table is over 5 columns"
    for u_, h_ in bp.items():
        assert h_.count("<a ") <= 60, "edge: %s has %d links (check.py BUDGET trust 60)" % (u_, h_.count("<a "))
        assert u_ == "/research/" or "not a random or representative sample" in h_, "edge: %s does not state its sample" % u_
    # PLAN 18: lakes and tides (lake_full is the page's own helpers; its counting and staleness are tested here)
    now_ = datetime.datetime(2026, 11, 12, 18, 0, tzinfo=datetime.timezone.utc)
    zn_ = zoneinfo.ZoneInfo("America/New_York")
    lb, lG = [], {}
    for i in range(7):
        s_ = "lk%d" % i
        lb.append({"site": s_, "state": "GA", "river": "Lake %d" % i, "place": "Dam", "dashboard_url": "/lake/l%d/" % i, "_built": True})
        lG[s_] = {"lake": "00062", "now": now_, "zone": zn_, "rec": {"usace_pool": {"x": 1}}, "_f": [("USACE full pool", i < 4, "%.2f ft below full pool" % i, now_ - datetime.timedelta(hours=100 if i == 6 else 2), i == 5)]}
    lf_ = research.lake_full
    research.lake_full = lambda G: [x for x in G["_f"] if research._age_h(G, x[3]) <= research.CURRENT_H]
    try:
        ll = research.lake_levels(lb, lG)
        assert ll and "4 of 6 US lakes on this site sit below their agency's full mark right now." in ll[1] and "1 more lake has an agency figure older than 3 days and is left out" in ll[1] and "(daily figure)" in ll[1], "edge: lake counts or the stale lake wrong"
        assert research.lake_levels(lb[:4], lG) is None, "edge: a lake page built from under 5 lakes"
    finally:
        research.lake_full = lf_
    t0 = now_ - datetime.timedelta(days=2)
    ts_ = [t0 + datetime.timedelta(minutes=6 * k) for k in range(480)]
    cb, cG = [], {}
    for i in range(6):
        s_ = "c%d" % i
        cb.append({"site": s_, "state": "MA", "river": "Port %d" % i, "place": "", "dashboard_url": "/coast/p%d/" % i, "_built": True})
        cG[s_] = {"coast": True, "now": now_, "zone": zn_, "sg": [(t, 2.0 + (0.5 if (i == 2 and k == 100) else 0.1)) for k, t in enumerate(ts_)],
                  "rec": {"coops": {"pred": [(t.isoformat(), 2.0) for t in ts_], "hilo": [(ts_[10].isoformat(), 4.0, "H"), (ts_[70].isoformat(), -0.5, "L")]}}}
    cG["c5"]["rec"]["coops"]["level"] = {"id": "x", "name": "Next door", "km": 3.0}  # prediction-only: left out
    cG["c4"]["sg"] = cG["c4"]["sg"][:100]  # under 24 h matched: left out
    cb.append(cb[0])  # the same station twice
    tp_ = research.tides(cb, cG)
    assert tp_ is None, "edge: tide page built from 4 usable stations (floor is 5)"
    for i in (6, 7):
        cb.append({"site": "c%d" % i, "state": "ME", "river": "Port %d" % i, "place": "", "dashboard_url": "/coast/p%d/" % i, "_built": True})
        cG["c%d" % i] = dict(cG["c0"])
    tp_ = research.tides(cb, cG)
    assert tp_ and "Across 6 NOAA stations" in tp_[1] and "Port 2" in tp_[1][tp_[1].find("<b>"):tp_[1].find("</b>")] and "+0.50 ft" in tp_[1] and "2 stations were left out" in tp_[1] and "4.5 ft" in tp_[1], "edge: tide gaps, range, left-out count or the prediction-only station wrong: %s" % (tp_ and tp_[1][tp_[1].find("<b>"):tp_[1].find("<b>") + 300])
    assert "/coast/p5/" not in tp_[1] and "noaa_station" in tp_[2], "edge: a prediction-only station listed, or the tide CSV header missing"
    # peer review 2026-11-12 fixes
    sp_, dg_ = _b3r.stage_pair, _b3r.datum_gap
    _b3r.stage_pair, _b3r.datum_gap = (lambda G: (1, 1, None)), (lambda G: None)
    try:
        hg = {"rec": {"nwps": {"categories": {"minor": 10.0}}, "peaks": {"rows": [["1832-03-01", 9e5, 30.0, None, "HISTORIC"]] + [["%d-03-01" % y, 1.0, 9.0, None, ""] for y in range(2000, 2012)]}}}
        assert len(_b3r.stage_years(hg)[0]) == 12 and not any(r[0].startswith("1832") for r in _b3r.stage_years(hg)[0]), "review #1: a historic stage (flow row coded HISTORIC) counted on the gauge page"
        dd = {"rec": {"nwps": {"categories": {"minor": 10.0}}, "peaks": {"rows": [["%d-03-01" % y, 1.0, 30.0, None, ""] for y in range(1980, 1990)] + [["1990-03-01", 1.0, 9.0, "['DIFFDATUM']", ""]] + [["%d-03-01" % y, 1.0, 9.0, None, ""] for y in range(1991, 2003)]}}}
        assert all(r[0] > "1990" for r in _b3r.stage_years(dd)[0]), "review #1: stages before the last datum change counted"
    finally:
        _b3r.stage_pair, _b3r.datum_gap = sp_, dg_
    lb_ = {"rec": {"peaks": {"rows": [["2010-03-01", 1500.0, None, None, "MAXDAILYMEAN"], ["2011-03-01", 500.0, None, None, "GREATERTHAN"], ["1900-00-00", 9.0, None, None, "YEARUNKNOWN"]]}}}
    pk_ = research._peaks(lb_)
    assert pk_[2010][3] and pk_[2011][3] and 1900 not in pk_ and research._plain(pk_) == {}, "review #4/#5: lower bounds not marked, a year-unknown peak kept, or a lower bound used as a plain peak"
    hb = [dict(r, site="x%d" % k) for k, r in enumerate(bb[:12])]
    hG = {}
    for k, r in enumerate(hb):
        rows_ = [["%d-03-15" % y, 400.0, None, None, ""] for y in range(2001, 2026)]
        if k == 0:
            rows_[5] = ["2006-03-15", 1500.0, None, None, "MAXDAILYMEAN"]  # a lower bound over the 1% flow: a certain exceedance
            rows_[6] = ["2007-03-15", 900.0, None, None, "GREATERTHAN"]  # a lower bound under it: year unknown, not counted
        hG[r["site"]] = {"rec": {"peaks": {"rows": rows_}, "floodfreq": {"rows": [{"aep": 1, "q": 1000.0}], "range1": [1950, 2000]}}}
    h1 = research.hundred_year(research.gauges(hb, hG), {})[1]
    assert "reached in 1 of 299 gauge-years" in h1 and "same water year" not in h1, "review #4: lower-bound peaks mishandled in the 100-year count: %s" % h1[h1.find("<b>"):h1.find("<b>") + 200]
    assert research.poisson_two(14, 14.0) == 1.0 and research.poisson_two(0, 14.0) < 0.001 and abs(research.poisson_two(3, 1.0) - 2 * research.poisson_tail(3, 1.0)) < 1e-9, "review #3: two-sided Poisson wrong"
    assert research.hodges_lehmann([1.0, 2.0, 3.0], [11.0, 12.0, 13.0]) == 10.0 and research.bh_count([0.001, 0.01, 0.04, 0.5]) == 3, "review #6: Hodges-Lehmann or Benjamini-Hochberg wrong"
    md1, r1_ = research.circ([60] * 10)
    md2, r2_ = research.circ([1, 92, 183, 274] * 5)
    assert abs(md1 - 60) < 0.6 and r1_ > 0.999 and r2_ < 0.01 and (research.circ([360, 5])[0] > 360 or research.circ([360, 5])[0] < 6), "circular mean or concentration wrong (incl. the year-end wrap)"
    nw_ = datetime.datetime.now(datetime.timezone.utc)
    wp_ = [({"slug": "rhine", "feed": "pegelonline", "river": "Rhine"}, {"rows": [{"name": "A%d" % k, "cm": 300, "time": (nw_ - datetime.timedelta(hours=1)).isoformat(), "state": ("low", "normal", "high", "low")[k % 4]} for k in range(8)]
                                                                                       + [{"name": "OLD", "cm": 300, "time": (nw_ - datetime.timedelta(hours=30)).isoformat(), "state": "high"}]}),
           ({"slug": "dublin", "feed": "imi", "river": "Dublin"}, {"rows": [{"name": "D", "cm": 1, "time": nw_.isoformat(), "state": "normal"}]})]
    wr = research.world_rivers(wp_, {"rhine": {"A%d" % k for k in range(8)} | {"OLD"}, "dublin": {"D"}}, nw_)
    assert wr and "Right now, counted country by country: Germany, 4 of 8 gauges low and 2 high." in wr[1] and "never added across countries" in wr[1] and "Each label has its own basis: the WSV's own marks in Germany." in wr[1] and "in Canada" not in wr[1][:wr[1].find("<table")] and "<td>Germany</td><td class=\"r\">4 of 8</td>" in wr[1] and "Tidal" in wr[1], "PLAN 18c: world labels counted wrong, a stale reading labelled, or a tidal station labelled: %s" % (wr and wr[1][wr[1].find("<b>"):wr[1].find("<b>") + 200])
    assert not re.search(r"\b20\d\d-\d\d-\d\d[T ]\d\d:\d\d", wr[1]), "PLAN 18c: a raw machine timestamp on the world page (check.py BANNED held it, run 43357129006)"
    assert research.world_rivers(wp_[:1], {"rhine": {"A0", "A1"}}, nw_) is None, "PLAN 18c: a world page built from 2 labelled gauges"
    assert 'href="/research/world-rivers/"' not in research.pages(rb, rG, datetime.date(2026, 11, 12))[0]["/research/"] and 'href="/research/world-rivers/"' in research.pages(rb, rG, datetime.date(2026, 11, 12), world="World title")[0]["/research/"], "the research index links a world page that was not built"
    # PLAN 23: hostile review fixes
    assert collect.stat_range("Statistic Date Range: 10/01/1915 - 09/30/2017") == [1916, 2017] and collect.stat_range("Statistic Date Range: 1931 - 2021") == [1931, 2021] and collect.stat_range("Statistic Date Range: 10/01/2000 - 10/15/2017") == [2001, 2018] and collect.stat_range("") is None and collect.stat_range("Statistic Date Range: 2020 - 1990") is None, "23: StreamStats date range parse wrong (the live form is MM/DD/YYYY; the old pattern matched nothing)"
    assert "Over the last 2 days" in tp_[1] and "Lowest (observed minus predicted)" in tp_[1] and "Most below" not in tp_[1] and "Smallest" not in tp_[1] and "this week" not in tp_[1].lower() and "tide datums are referenced to" in tp_[1] and "parts of Alaska" in tp_[1], "23: tide page names a span the data does not cover, calls a positive gap 'below', or omits the steady sea-level offset"
    assert research._pl(1, "regulated gauge is", "regulated gauges are") == "1 regulated gauge is" and research._pl(2, "x", "ys") == "2 ys", "23: count-1 grammar"
    assert 'href="/research/world-rivers/">River levels in Germany' in research.pages(rb, rG, datetime.date(2026, 11, 12), world=research.title_of(wr[1]))[0]["/research/"], "23: the index link does not use the world page's own title"
    assert collect.fetch_floodfreq.__doc__ and "rangev" in open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "collect.py"), encoding="utf-8").read().split('"dur": durs')[1][:40], "23: a duration-only StreamStats record lacks rangev, so the early refresh refetches it every run"
    assert "Germany" in wr[1][:wr[1].find("</title>")] and "Ireland" not in wr[1][:wr[1].find("</title>")], "23: the world title names a country with no labelled gauge"
    assert "not a forecast" in fs and "National Weather Service warnings" in fs, "23: flood-stage page lacks its not-a-forecast line"
    # PLAN 22 lock 2: every headline reproduced from its own CSV; a doctored CSV drops the page
    for u_, h_ in list(bp.items()):
        if u_ != "/research/":
            assert research.verify(u_, h_, bc[u_]) == [], "22: %s does not reproduce from its own CSV: %s" % (u_, research.verify(u_, h_, bc[u_]))
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import check as _ck
    for u_, h_ in bp.items():
        assert not _ck.research_gate(h_, u_.strip("/") + "/index.html") and not _ck.research_sanity(h_), "22: the gate fails a real research page (false alarm): %s %s" % (u_, _ck.research_gate(h_, u_.strip("/") + "/index.html") + _ck.research_sanity(h_))
    for u_, h_ in bp.items():  # PLAN 24: every real title carries a measured seed's words
        assert _ck.research_title_ok(h_, u_), "24: %s title carries no measured seed: %s" % (u_, research.title_of(h_))
    assert not _ck.research_title_ok("<title>How warm are US rivers? | River Water Levels</title>", "/research/water-temperature/"), "24: a title with no measured seed passed"
    assert not _ck.research_title_ok("<title>Canada now | River Water Levels</title>", "/research/world-rivers/") and not _ck.research_title_ok("<title>Lake Erie | River Water Levels</title>", "/research/lake-levels/"), "24: the brand suffix supplied seed words to a title"
    lines_ = bc["/research/100-year-floods/"].splitlines()
    assert research.verify("/research/100-year-floods/", bp["/research/100-year-floods/"], "\n".join(lines_[:-3])), "22: a CSV missing rows still reproduced the 100-year headline"
    assert research.verify("/research/new-thing/", "<p><b>x</b></p>", "a\n1\n"), "22: a research page with no reproducibility check passed"
    # PLAN 21 harm audit: chance-level counts never called more than chance; licence credit in every CSV; cite-with-date line on snapshot pages; CSVs noindex
    nul = [({"site": "n%d" % i, "state": "GA", "river": "N%d" % i, "place": "T", "dashboard_url": "/river/n%d/t/" % i, "_built": True}) for i in range(40)]
    import random as _rnd
    _r = _rnd.Random(7)
    nG = {"n%d" % i: {"rec": {"peaks": {"rows": [["%d-03-15" % y, 100.0 + _r.random() * 50, None, None, ""] for y in range(1960, 2026)]}}} for i in range(40)}
    np_ = research.pages(nul, nG, datetime.date(2026, 11, 12))[0]["/research/peak-change/"]
    assert "On these 40 gauges, not in a way this test can tell from chance" in np_ and "not evidence that nothing changed" in np_ and "more than chance alone explains" not in np_, "21: noise across 40 gauges was called more than chance"
    assert rc["/research/peak-change/"].splitlines()[0].endswith(",credit") and "Data: U.S. Geological Survey" in rc["/research/peak-change/"], "21: a research CSV lacks the source credit"
    assert "PEGELONLINE" in wr[2] and "CC BY 4.0" in wr[2] and wr[2].splitlines()[0].endswith(",credit"), "21: the world CSV lacks the OGL or CC BY credit its terms require"
    assert "cite them with that date and time" in wr[1] and "cite them with that date and time" in tp_[1], "21: a snapshot page lacks its cite-with-date line"
    assert "/*.csv\n  X-Robots-Tag: noindex" in open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "_headers"), encoding="utf-8").read(), "21: research CSVs can be indexed as bare files"
    # owner 2026-11-12: what happened next in years like this one (collect.next_days + charts.b_like_today)
    from lib.charts import b_like_today
    d = datetime.date(2026, 11, 12)
    val = {}
    for y in range(1990, 2026):  # 36 years; even years flow 100 then 150 a week on, odd years 400
        for i in range(21):
            val[(datetime.date(y, 11, 9) + datetime.timedelta(days=i)).isoformat()] = (100.0 if i <= 3 else 150.0) if y % 2 == 0 else 400.0
    val["2026-11-10"] = 1.0  # this year never enters the past years
    nx = collect.next_days(val, d)
    assert nx["start"] == "2026-11-09" and "2026" not in nx["years"] and len(nx["years"]) == 36, "edge: next_days window or years wrong"
    assert collect.next_days(val, datetime.date(2028, 3, 3))["start"] == "2028-02-29" and collect.next_days({"2027-02-28": 5.0}, datetime.date(2028, 3, 3))["years"] == {}, "edge: Feb 29 start crashed or a thin year was kept"
    G = {"rec": {"multiyear": {"next": nx}}, "basis": 110.0, "ldate": d}
    lt = b_like_today(G)
    assert lt and "In 18 of 36 years" in lt["body"] and "higher in 18" in lt["body"] and "+50%" in lt["body"] and "not a forecast" in lt["body"], "edge: like-today counts wrong: %s" % (lt and lt["body"][:300])
    assert b_like_today(dict(G, basis=250.0)) is None, "edge: no year within 25% still built a block"
    assert b_like_today(dict(G, ldate=d + datetime.timedelta(days=14))) is None, "edge: window no longer holds today + 7, block still built"
    assert b_like_today(dict(G, lake="00062")) is None and b_like_today(dict(G, osc=True)) is None and b_like_today(dict(G, basis=None)) is None, "edge: lake, tidal or no-flow page got a like-today block"
    assert b_like_today({"rec": {"multiyear": {"next": {"start": "2026-11-09", "years": {k: v for k, v in list(nx["years"].items())[:8]}}}}, "basis": 110.0, "ldate": d}) is None, "edge: under 10 years of record built a block"
    ago = lambda **k: datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(**k)
    new = {"parameter_code": "00060", "time": "t1", "value": "11000", "qualifier": None}
    from lib import directory
    from lib import core as core_
    iso = lambda d: d.isoformat()
    fut = core_.series({"usgs": {"rows": [dict(new, time=iso(ago(minutes=30)), unit_of_measure="ft^3/s", value="900"), dict(new, time=iso(ago(minutes=-120)), unit_of_measure="ft^3/s", value="5000")]}}, "00060")
    fr_ = {"usgs": {"rows": [dict(new, time=iso(ago(minutes=30)), unit_of_measure="ft^3/s", value="900"), dict(new, time=iso(ago(minutes=-120)), unit_of_measure="ft^3/s", value="5000")]}}
    fut = core_.series(fr_, "00060")
    assert [v for _, v, _ in fut] == [900.0], "a US reading stamped 2 h in the future was kept as the latest (gate audit 0a)"
    from lib import hero as hero_
    assert "held as a likely clock error" in hero_.future_note({"rec": fr_, "lake": None}) and not hero_.future_note({"rec": {"held_future": ["00010"]}, "lake": None}) and not hero_.future_note({"rec": {}, "lake": None}), "a held future reading was not said on the page, or a water-temperature slip was (gate audit 0a)"
    __import__("json").dumps(fr_)  # the held mark keeps a rec JSON
    from lib import render  # noqa: F401 (lib.page imports through render)
    from lib import blocks2 as b2_
    t0_ = datetime.datetime(2026, 11, 9, 15, tzinfo=datetime.timezone.utc)
    fl_ = [(t0_ - datetime.timedelta(minutes=15 * k), 1160.0 if k == 0 else (1210.0 if k >= 96 else 1200.0), {}) for k in range(100, -1, -1)]
    rb_ = str(b2_.b_rate({"fl": fl_, "sg": [], "zone": zoneinfo.ZoneInfo("America/Denver"), "offline": False, "osc": False, "site": "x"}))
    assert "Last 1 h (same for 1 to 12 h)" in rb_ and rb_.count("Last 3 h") == 0 and "Last 24 h" in rb_ and "Full table" not in rb_, "rate of change: identical 1-12 h windows were printed four times, or the duplicate full table is back (fresh review 2026-11-09, Madison)"
    ok_ = "stationID,time,tide_time_category,Water_Level_ODMalin\n,UTC,,metres\nKinsale,2026-11-09T04:40:00Z,HIGH,1.534\nCobh,2026-11-09T05:00:00Z,HIGH,2.1\nKinsale,2026-11-09T11:00:00Z,LOW,-1.556\n"
    assert collect.imi_hilo(ok_, "Kinsale") == [["2026-11-09T04:40:00+00:00", 1.534, "H"], ["2026-11-09T11:00:00+00:00", -1.556, "L"]], "Ireland tides: another station's row kept, or time/height misread"
    try:
        collect.imi_hilo(ok_.replace("metres", "feet"), "Kinsale")
        raise AssertionError("Ireland tides: a changed unit row was read as metres")
    except RuntimeError:
        pass
    lv_ = collect.imi_live("station_id,longitude,latitude,time,Water_Level_OD_Malin\n,degrees_east,degrees_north,UTC,metres\nGalway Port,-9.048,53.269,2026-11-10T02:20:00Z,0.409\nGalway Port 2,-9.047911,53.26926,2026-11-10T02:20:00Z,0.534\nGalway Port,-9.048,53.269,2026-11-10T02:10:00Z,0.38\nHowth Water Level 2,-6.06,53.39,2026-11-10T02:20:00Z,NaN\n")
    assert lv_["Galway Port"]["series"] == [["2026-11-10T02:10:00+00:00", 0.38], ["2026-11-10T02:20:00+00:00", 0.409]] and lv_["Galway Port 2"]["series"][-1][1] == 0.534 and "Howth Water Level 2" not in lv_, "Irish live tides: sensors mixed, order wrong, or a NaN kept"
    from lib import blocks3 as b3_
    up_ = {"office": "SAM", "loc": "Buford", "fetched_at": "2026-11-10T03:17:03+00:00", "NGVD29": {"ft": 1070.346, "estimated": False}, "NAVD88": {"ft": 1070.571, "estimated": True}}
    ug_ = lambda lake, vd, alt, lv: {"lake": lake, "sg": [(t0_, lv, {})], "rec": {"usace_pool": up_, "meta": {"loc": {"vertical_datum": vd, "altitude": alt}}}}
    assert b3_.usace_full(ug_("00062", "NAVD88", 0.0, 1062.5)) == (1070.571, "NAVD88", True, 1062.5 - 1070.571) and b3_.usace_full(ug_("62614", "", None, 1062.5))[1] == "NGVD29", "Lanier full pool: the gauge's datum was not matched to USACE's value in that datum"
    assert b3_.usace_full(ug_("00062", "NAVD88", 812.4, 30.1)) is None and b3_.usace_full(ug_("00062", "NAVD88", 0.0, 1020.0)) is None, "full pool shown for a gauge datum with an offset, or a 50 ft gap (another project)"
    lcg_ = lambda days: {"lake": True, "sg": [(t0_, 1039.66, {})], "rec": {"usbr_lc": {"days": days, "cap_af": 26120000, "cap_elev_ft": 1219.6}}}
    assert b3_.lc_day(lcg_({"2026-11-07": [1039.55, 6947000], "2026-11-08": [1039.66, 6954000]})) == ("2026-11-08", 1039.66, 6954000) and b3_.lc_day(lcg_({"2026-11-07": [1039.55, 6947000]})) == ("2026-11-07", 1039.55, 6947000), "Lake Mead storage: the matching day was not used, or a table one day behind RISE left storage Unknown (live 2026-11-09)"
    nw = datetime.datetime(2026, 11, 7, 18, tzinfo=datetime.timezone.utc)
    lk = lambda i, **k: dict({"full_name": "Lake %03d" % i, "short_name": "L%d" % i, "timestamp": "2026-11-07", "elevation": 677.15, "conservation_pool_elevation": 681.0, "percent_full": 93.5, "conservation_storage": 9.0, "conservation_capacity": 10.0}, **k)
    assert directory.lake_state_page({"rows": {str(i): lk(i) for i in range(49)}}, {}, nw) is None, "a TWDB file cut short (under 50 reservoirs) still made the Texas page"
    tx = directory.lake_state_page({"fetched_at": "2026-11-07T17:00:00Z", "rows": dict({str(i): lk(i) for i in range(60)}, dry=lk(98, full_name="Addicks Reservoir", percent_full=None, elevation=76.38, conservation_pool_elevation=67.5), late=lk(99, full_name="Lake Old", timestamp="2026-11-01"))}, {}, nw)
    assert "677.15 ft" in tx and "3.85 ft below full pool" in tx and "Addicks Reservoir</td><td class=\"r\">Unknown" in tx and "8.88 ft above" not in tx and "6 days old" in tx, "Texas lake page: a published elevation was rounded, a dry flood dam got a pool figure, or an old row hid its age"
    cm = lambda vid, fl, w, a, dist, **k: {"properties": dict({"field_visit_id": vid, "time": "2026-08-0%sT18:00:00+00:00" % vid, "channel_flow": str(fl), "channel_width": str(w), "channel_area": str(a), "channel_velocity": "2.1", "channel_location_distance": dist, "channel_location_direction": "Downstream", "channel_width_unit": "ft", "channel_area_unit": "ft^2", "channel_flow_unit": "ft^3/s"}, **k)}
    ch = collect.chan_rows([cm("1", 71000, 1690, 33600, "5000.00"), cm("1", 900, 300, 600, "5000.00"), cm("1", 72000, 1700, 34000, "5000.00", channel_name="Check"), cm("2", 255000, 1780, 59000, "64000.00"), cm("3", 50, 20, 30, ""), cm("4", 10, 5, 0, "0"), cm("5", 10, 5, 9, "0", channel_width_unit="m")])
    assert [(r[1], r[2], r[3]) for r in ch] == [(71000, 1690, 33600)], "depth: a measurement 12 mi away, a side channel, a blank distance, a zero area or metres got into the depth table (Louisville, Omaha 2026-11-09)"
    assert collect.nwps_cats({"flood": {"categories": {"action": {"stage": 0}, "minor": {"stage": 55.0}, "major": {"stage": -9999}, "moderate": {"stage": None}}}}) == {"minor": 55.0}, "NWS flood stage 0, -9999 or blank kept as a flood level"
    pe = collect.pegel_end([{"timestamp": "2026-11-09T05:00:00+01:00", "value": 141.0}, {"timestamp": "2026-11-09T05:15:00+01:00", "value": 144.0}], {"timestamp": "2026-11-09T04:15:00Z", "value": 146.0})
    assert [p["value"] for p in pe] == [141.0, 146.0], "pegelonline: the series' last point disagreed with the current measurement at the same time (Wuerzburg carried twice 2026-11-09)"
    real, asked = collect.retry_json, []  # PLAN limit 9: one PEGELONLINE call for every station's current reading and marks of a page
    try:
        collect.retry_json = lambda u, *a, **k: asked.append(u) or [{"shortname": "KÖLN"}, {"shortname": "Trier UP"}]
        b_ = collect.pegel_bulk("https://x/stations/", ["KÖLN", "Trier UP", "NOPE"])
        assert set(b_) == {"KÖLN", "Trier UP"} and len(asked) == 1 and "ids=K%C3%96LN,Trier%20UP,NOPE&" in asked[0] and asked[0].startswith("https://x/stations.json?"), "pegelonline bulk: not one call for the page, a name not quoted, or a station keyed wrongly: %s" % asked
        collect.retry_json = lambda u, *a, **k: (_ for _ in ()).throw(OSError("down"))
        assert collect.pegel_bulk("https://x/stations/", ["KÖLN"]) == {}, "pegelonline bulk: a failed call did not fall back to one call per station"
    finally:
        collect.retry_json = real
    from lib import blocks3
    G = {"rec": {"fieldmeas": {"fetched_at": "2026-11-09T00:00:00Z", "chan": [["2026-08-04T18:49:06+00:00", 71000.0, 1690.0, 33600.0, 2.11, 5000.0, "Downstream"], ["2025-08-14T15:00:00+00:00", 48000.0, 1680.0, 17300.0, 1.9, 3000.0, "Downstream"]]}}, "lv": 48100.0, "zone": zoneinfo.ZoneInfo("America/New_York")}
    h = blocks3.b_depth(G)["body"]
    assert "average depth of 19.9 ft" in h and "About 10 ft deep on average</b> at a flow like today's (48,100 cfs)" in h and "average depth of 10.3 ft" in h and "pools and the main channel are deeper" in h and "5,000 ft downstream" in h, "depth block: wrong area/width, nearest-flow pick or distance label"
    assert blocks3.b_depth(dict(G, rec={"fieldmeas": {"chan": []}})) is None and blocks3.b_depth(dict(G, rec={})) is None, "depth block shown with no measurement"
    from lib.core import tzl as tzl_
    ny_, U_ = zoneinfo.ZoneInfo("America/New_York"), datetime.timezone.utc
    tzl_ = (lambda f: lambda *a: f(*a).replace("\u00a0", " "))(tzl_)  # times use no-break spaces on the page
    assert (tzl_(datetime.datetime(2026, 11, 1, 5, 30, tzinfo=U_), ny_), tzl_(datetime.datetime(2026, 11, 1, 6, 30, tzinfo=U_), ny_), tzl_(datetime.datetime(2026, 3, 8, 7, 30, tzinfo=U_), ny_)) == ("Nov 1, 1:30 AM EDT", "Nov 1, 1:30 AM EST", "Mar 8, 3:30 AM EDT"), "time zone label wrong on a clock-change night (each reading must carry its own EDT/EST)"
    ac = {"rec": {"acis": {"fetched_at": "2026-11-09T02:00:00Z", "days": ["2026-11-%02d" % d for d in range(3, 10)], "stations": [{"name": "TEST STN", "km": 3.0, "vals": ["0.10", "0.00", "T", "0.00", "0.00", "0.20", "M"]}]}}, "now": datetime.datetime(2026, 11, 9, 3, tzinfo=datetime.timezone.utc), "zone": zoneinfo.ZoneInfo("America/Chicago")}
    assert "not reported" not in blocks3.b_acis(ac)["body"], "rain table: a US page after midnight UTC showed tomorrow as 'not reported' (review 2026-11-09)"
    rows, add, fixed = collect.merge_rows([dict(new, value="10500"), dict(new, time="t0", value="9")], [new, dict(new, time="t2")])
    assert {r["time"]: r["value"] for r in rows}["t1"] == "11000" and (add, fixed) == (1, 1), "a USGS correction to a reading we already had was dropped"
    assert collect.merge_rows([new], [dict(new)])[1:] == (0, 0), "an unchanged reading counted as a correction"
    late = dict(new, time="t3", value="12400")  # Animas 2026-11-03: latest-continuous kept 12,400 at a time the continuous series no longer had
    assert [r["value"] for r in collect.add_latest([new], [late, dict(new, value="99")])] == ["11000", "12400"], "the page lacks the latest reading the edge shows, or a latest value overrode a continuous correction"
    z = lambda prov, std, lon=-70, lat=55: collect.eccc_zone({"PROV_TERR_STATE_LOC": prov, "DATETIME_LST": "2026-01-01T00:00:00" + std}, lon, lat)
    assert (z("NU", "-05:00"), z("NU", "-06:00"), z("NU", "-07:00"), z("QC", "-04:00", -60, 51), z("QC", "-04:00", -61.8, 47.4), z("QC", "-05:00"), z("SK", "-07:00")) == ("America/Iqaluit", "America/Rankin_Inlet", "America/Cambridge_Bay", "America/Blanc-Sablon", "America/Halifax", "America/Toronto", "America/Edmonton"), "a Canadian station in a split province read the wrong time zone (Nunavut read Toronto, 2026-11-04)"
    calls, rec_, log_ = [], {"access": "old"}, []
    def dead():
        calls.append(1)
        raise TimeoutError("The read operation timed out")
    for _ in range(6):
        collect.run_source(rec_, "access", dead, log_)
    collect.run_source(rec_, "land", lambda: (_ for _ in ()).throw(OSError("HTTP Error 404: Not Found")), log_)
    assert len(calls) == collect.DOWN_AFTER and rec_["access"] == "old" and collect.DOWN.get("land", 0) == 0, "a dead source was asked at every gauge (32 of 33 release minutes, 2026-11-04), lost its previous value, or a 404 counted as down"
    collect.DOWN.clear()
    src = open(os.path.join(ROOT, "collect.py"), encoding="utf-8").read()
    assert "&last_modified=" in src[src.index("def fast_usgs"):src.index("SLOW_KEYS")], "the hourly fetch cannot see a correction to an older reading"
    assert "g.f[0] !== m[3]" in open(os.path.join(ROOT, "worker", "index.js"), encoding="utf-8").read(), "the edge cannot correct a reading of the same time"
    from lib import blocks2
    t0 = datetime.datetime(2026, 11, 2, 16, tzinfo=datetime.timezone.utc)
    G = {"lt": t0, "zone": datetime.timezone.utc, "now": t0 + datetime.timedelta(hours=7), "sg": [(t0, 11.51, None), (t0 + datetime.timedelta(hours=6), 12.58, None)]}
    b = blocks2.b_flow_behind(G)
    assert b and "1.07 ft higher" in b["body"] and "7 h" in b["body"], "flow ending in a flood was not said"
    assert not blocks2.flow_behind(dict(G, sg=G["sg"][:1])), "a current flow was called behind"
    import io, zipfile
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as zf:
        zf.writestr("x.geojson", json.dumps({"crs": {"properties": {"name": "EPSG:3857"}}, "features": [{"properties": {"DM": 2}, "geometry": {"type": "Polygon", "coordinates": [[[123.456, 234.567], [0, 0], [99, 0], [123.456, 234.567]]]}}]}))
    assert wx_mod.drought_map(b.getvalue())[0][2][0][0][1] != round(wx_mod.drought_map(b.getvalue())[0][2][0][0][1], 3), "drought coordinates were rounded: false gaps open in solid areas"
    row = lambda m, c: {"geometry": {"coordinates": [-123.0, 49.0]}, "properties": {"CLIMATE_IDENTIFIER": "A", "STATION_NAME": "A", "MONTH": m, "VALUE": 1.0, "PERIOD_BEGIN": 1981, "PERIOD_END": 2010, "YEAR_COUNT_NORMAL_PERIOD": c}}
    near = {"lat": 49.0, "lon": -123.0}
    real_json = collect.http_json
    try:
        collect.http_json = lambda *a, **k: {"features": [row(10, 1)]}
        assert collect.normals_canada(near) is None, "one October passed as a 30-year normal"
        collect.http_json = lambda *a, **k: {"features": [row(m, 30) for m in range(1, 13)]}
        assert collect.normals_canada(near)["temp"]["10"] == 1.0, "a real normal was refused"
    finally:
        collect.http_json = real_json
    beob = "\n".join(["surface observations;Parameter description;dry_bulb_temperature_at_2_meter_above_ground", "10628;Unit;C", "Datum;Uhrzeit;Temperatur", "03.11.26;02:00;---", "03.11.26;01:00;7,2"])
    assert wx_mod.dwd_obs(beob, "10628", [50, 8, "X"])["obs"]["temp_c"] == 7.2, "an empty newest DWD row hid the station's weather"
    from lib.hero import beyond
    row = [13, None, 398.2, None, 624.0, 1470.0, 2525.0, None, 4516.0, None]
    assert beyond(row, 9000)[0] == "above 90th" and "4,520 cfs" in beyond(row, 9000)[1] and beyond(row, 100)[0] == "below 10th" and beyond(row, 1000) is None, "a flood past the published percentiles read as no statistics"
    assert beyond([7, None, None, None, 3543.6, 3572.2, 3590.7, None, None, None], 3537.3, "ft")[0] == "below 25th", "a lake under the lowest published percentile (Powell: 25th) read as no statistics"
    import check as check_
    pg = lambda t: '<html><head><link rel="canonical" href="x"></head><body><h1>x</h1><main>%s</main></body></html>' % t
    assert not [b for b in check_.check_html(pg("Walla Walla River | Ro Ro Anlage"), "x") if "doubled" in b], "a real place name with a doubled word failed the page"
    assert [b for b in check_.check_html(pg("Wis Wis campground"), "x") if "doubled" in b], "a doubled word typo passed"
    assert check_.kind_of("danube/pfelling/index.html") in check_.CARRYABLE and check_.kind_of("river/x/y/index.html") in check_.CARRYABLE, "a failing world or gauge page stops the whole deploy instead of keeping its live copy"
    with tempfile.TemporaryDirectory() as t:
        nd, od = os.path.join(t, "next"), os.path.join(t, "dist")
        for p_, b_ in ((nd, {"/rhine/kaub/": {"at": "new"}, "/rhine/maxau/": {"at": "new"}}), (od, {"/rhine/kaub/": {"at": "old"}, "/rhine/maxau/": {"at": "old"}})):
            os.makedirs(p_)
            json.dump([], open(os.path.join(p_, "live-sites.json"), "w"))
            json.dump(b_, open(os.path.join(p_, "_built.json"), "w"))
        keep_root, check_.ROOT = check_.ROOT, t
        try:
            check_.keep_old_times(nd, ["rhine/kaub/index.html"])
        finally:
            check_.ROOT = keep_root
        assert json.load(open(os.path.join(nd, "_built.json"))) == {"/rhine/kaub/": {"at": "old"}, "/rhine/maxau/": {"at": "new"}}, "a carried world page read as just built, so the 6 h alarm never sees it"
    assert collect.nwm_due({}),"a gauge with no model forecast must be due"
    collect.NWM_EMPTY[0] = 3
    assert not collect.nwm_due({}), "an empty model service kept being called every gauge, stretching the run"
    collect.NWM_EMPTY[0] = 0
    z = collect.eccc_zone
    on = {"PROV_TERR_STATE_LOC": "ON", "DATETIME_LST": "2026-11-02T10:00:00-05:00"}
    assert z(dict(on, DATETIME_LST="2026-11-02T10:00:00-06:00"), -94.5) == "America/Winnipeg", "Kenora kept Toronto time"
    assert z(on, -79.4) == "America/Toronto", "Toronto lost its zone"
    assert z({"PROV_TERR_STATE_LOC": "NL", "DATETIME_LST": "2026-11-02T10:00:00-04:00"}, -60) == "America/Halifax", "Labrador kept Newfoundland time"
    assert z({"PROV_TERR_STATE_LOC": "BC"}, -116.9) == "America/Edmonton" and z({"PROV_TERR_STATE_LOC": "BC"}, -123) == "America/Vancouver", "BC split wrong"

    class Reply:
        def __init__(self, age, headers=None):
            self.headers = headers or {"Last-Modified": email.utils.format_datetime(age)}
        read = lambda self: b"file"
    real_open = collect.urllib.request.urlopen
    try:
        collect.urllib.request.urlopen = lambda *a, **k: Reply(ago(hours=5))
        try:
            collect.fresh_raw("http://x", 3)
            raise AssertionError("a frozen alert file passed as current")
        except RuntimeError:
            pass
        collect.urllib.request.urlopen = lambda *a, **k: Reply(ago(minutes=5))
        assert collect.fresh_raw("http://x", 3) == b"file", "a fresh alert file was refused"
        collect.urllib.request.urlopen = lambda *a, **k: Reply(None, {"x-rwl-usgs-remaining": "120"})
        assert collect.usgs_low() is True, "a nearly spent USGS key did not pause history"
        collect.urllib.request.urlopen = lambda *a, **k: Reply(None, {"x-rwl-usgs-remaining": "900"})
        assert collect.usgs_low() is False, "a healthy key paused history"
        collect.urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(OSError("down"))
        assert collect.usgs_low() is False, "a dead site paused history"
    finally:
        collect.urllib.request.urlopen = real_open

    st = [{"shortname": "W", "currentMeasurement": {"value": 1, "timestamp": ago(hours=1).isoformat()}},
          {"shortname": "WT", "unit": "C", "longname": "WASSERTEMPERATUR", "currentMeasurement": {"value": 9, "timestamp": ago(hours=2).isoformat()}},
          {"shortname": "LT", "unit": "C", "longname": "LUFTTEMPERATUR", "currentMeasurement": {"value": 5, "timestamp": ago(hours=30).isoformat()}}]
    got = collect.side_readings(st)
    assert list(got) == ["WT"] and got["WT"][3] == st[1]["currentMeasurement"]["timestamp"], "a side reading lost its time or outlived 24 h"

    base = {"name": "01AB", "cm": 1.0, "time": "2026-11-02T12:00:00Z", "series": [["2026-11-02T12:00:00Z", 1.0]], "lat": 50.0, "lon": -100.0, "unit": "m", "zone": "America/Winnipeg", "months": {"11": [100.0] * 40 + [0.5, 0.8, 0.9, 1.0, 1.0, 1.0, 1.1, 1.2, 1.5, 2.0] * 2}}
    assert world.canada_label(base, datetime.datetime(2026, 11, 2))[0] == "Normal", "an old datum made today read Low"
    assert "Agency flag on this reading: Ice" in world.to_rec({"feed": "eccc", "river": "X", "slug": "x"}, dict(base, flag="Ice"))["feed"]["label_note"], "an ice flag did not reach the page"

    from lib import coverage, wx
    from lib import core as _core
    _n = "7 days: Source: A. Shaded band: x to y. Flow in cfs. 30 days: Source: B. Shaded band: x to y. Flow in cfs."
    assert _core.say_once(_n) == "7 days: Source: A. Shaded band: x to y. Flow in cfs. 30 days: Source: B.", _core.say_once(_n)
    import csv as _csv
    from lib import page as _pg
    _cs = {r["state"] for r in _csv.DictReader(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "coasts.csv"), encoding="utf-8"))}
    assert _cs <= set(_pg.BEACH_WATER), "coast state(s) with no beach-water program link: %s" % sorted(_cs - set(_pg.BEACH_WATER))
    from lib import blocks3 as _b3
    _now = datetime.datetime(2026, 11, 11, 18, tzinfo=datetime.timezone.utc)
    _aq = lambda cat: _b3.b_air_quality({"rec": {"airnow": {"fetched_at": "2026-11-11T18:00:00+00:00", "rows": [{"date": "2026-11-11", "hour": "17:00", "aqi": 60, "category": cat, "pollutant": "OZONE", "site": "X", "agency": "A"}]}}, "zone": datetime.timezone.utc, "now": _now})["body"]
    assert 'background:#ffff00' in _aq("Moderate") and "<i " not in _aq("Not a category").split('class="aq">')[1][:4], "AQI dot missing, or a dot guessed for an unknown category"
    square = [[1, [0, 2, 0, 2], [[[0, 0], [0, 2], [2, 2], [2, 0], [0, 0]]]], [3, [0.5, 1, 0.5, 1], [[[0.5, 0.5], [0.5, 1], [1, 1], [1, 0.5], [0.5, 0.5]]]]]
    assert wx.drought_at(0.7, 0.7, square) == 3 and wx.drought_at(1.5, 1.5, square) == 1 and wx.drought_at(3, 3, square) is None, "drought class wrong"
    assert world.metric("<td>2.3 mi</td>") == "<td>3.7 km</td>", "a decimal distance broke"
    with tempfile.TemporaryDirectory() as d:
        for i in range(20):
            os.makedirs(os.path.join(d, "river", str(i)))
            open(os.path.join(d, "river", str(i), "index.html"), "w").write('"BreadcrumbList"<div class="hero hero2"><section data-g="now" class="card blk" data-f="x" id="%s"></section>' % ("a" if i < 5 else "b"))
            os.makedirs(os.path.join(d, "embed", "river", str(i)))
            open(os.path.join(d, "embed", "river", str(i), "index.html"), "w").write('<div class="hero hero2">')
        got = coverage.scan(d, {"best": {"US": {"a": 0.9}}})
        assert "Germany" not in got["shares"], "embed panels were counted as German gauge pages"
        assert got["shares"]["US"]["blocks"]["a"] == 0.25 and "US a" in got["drops"][0], "a block vanishing across pages went unseen"
        assert not coverage.scan(d, {"best": {"US": {"a": 0.25}}})["drops"], "a steady block alarmed"
        assert not coverage.scan(d, {"best": {"US": {"a": 0.4}}})["drops"], "a block that comes and goes with the weather alarmed"
        assert not coverage.scan(d, {"best": {"US": {"a": 0.57}}})["drops"], "alerts that end with the weather alarmed"

    far = dict(base, name="F", lat=60.0, then=1.0)
    near = dict(base, name="N", lat=50.3, then=1.0)
    got = world.along({"flat": True, "feed": "eccc", "slug": "x"}, base, [base, far, near])
    assert [g[1] for g in got] == ["N"] and got[0][0] == "Nearby", "a far gauge read as nearby"


    real = world.page, world.missing, world.os.path.exists, world.GATE
    p = {"slug": "x", "gauge_pages": ["01AB"], "river": "X"}
    try:
        world.page, world.missing, world.GATE = lambda *a, **k: ("/u/", "<html>"), lambda h, r: ["alerts"], True
        world.os.path.exists = lambda q: False
        world.missing, world.GAPS = lambda h, r: [], {}
        world.choose([(p, {"rows": [base]})], None)
        assert world.GAPS.get("01AB") == ["flood warning note"], "a world page without the flood line passed"
        world.missing = lambda h, r: ["alerts"]
        assert world.choose([(p, {"rows": [base]})], None)["x"] == set(), "a new gauge with a gap was not held"
        world.os.path.exists = lambda q: True
        assert world.choose([(p, {"rows": [base]})], None)["x"] == {"01AB"}, "an outage pulled a live page"
        world.missing, world.page = lambda h, r: [], lambda *a, **k: ("/u/", "<html data-flood>")
        two = dict(p, gauge_pages=["01AB", "02CD"])
        assert world.choose([(two, {"rows": [base, dict(base, name="02CD")]})], None)["x"] == {"01AB"} and "same address" in world.THIN["02CD"][0], "two gauges whose titles slug alike both published to one address"
    finally:
        world.page, world.missing, world.os.path.exists, world.GATE = real

    england(ago)
    england_page()

    class Later(datetime.date):
        @classmethod
        def today(cls):
            return cls(2028, 1, 5)
    keep = collect.CACHE, collect.http_raw, collect.datetime
    with tempfile.TemporaryDirectory() as d:
        try:
            collect.CACHE, collect.datetime = d, types.SimpleNamespace(date=Later)
            def raw(url, timeout=0):
                if "2026" in url:
                    return b'{"g": {"2026-11-02": [2, 9]}}'
                raise collect.urllib.error.HTTPError(url, 404, "gone", {}, None)
            collect.http_raw = raw
            collect.archive({"slug": "rhine"}, [])
            assert json.load(open(os.path.join(d, "_archive-rhine-2026.json")))["g"], "a lost cache dropped a past year"
            assert json.load(open(os.path.join(d, "_archive-rhine-2027.json"))) == {}, "a year never archived did not stay empty"
        finally:
            collect.CACHE, collect.http_raw, collect.datetime = keep
    # full audit 2026-11-10 (tools/full_audit_last.md items 2-5, 7, 8, 10, 11, 15): synthetic US gauges through the real ctx and hero
    import math as m_, re as r_
    n0 = datetime.datetime.now(datetime.timezone.utc).replace(second=0, microsecond=0)
    n0 -= datetime.timedelta(minutes=n0.minute % 15)
    rw = lambda code, f, unit: [{"parameter_code": code, "time": (n0 - datetime.timedelta(minutes=15 * k)).isoformat(), "value": "%.3f" % f(k), "unit_of_measure": unit} for k in range(8 * 96)]
    def mk(flow, stage, extra=None, row=None, codes=()):
        rec = dict({"site": "1", "lat": 46.0, "lon": -122.0, "tz": "America/Los_Angeles", "usgs": {"rows": (rw("00060", flow, "ft^3/s") if flow else []) + rw("62614" if (row or {}).get("lake") else "00065", stage, "ft") + [x for c in codes for x in rw(*c)], "truncated": []}}, **(extra or {}))
        return render.ctx("1", dict({"river": "Test River", "place": "Kosmos", "state": "WA", "raw_name": "TEST RIVER NEAR KOSMOS, WA", "dashboard_url": "/river/t/k/", "hub_url": "/river/t/"}, **(row or {})), rec, n0)
    tides = {"tides": {"station": "9440000", "name": "Somewhere", "mi": 30, "fetched_at": n0.isoformat(), "rows": [{"t": (n0 + datetime.timedelta(hours=hh)).strftime("%Y-%m-%d %H:%M"), "v": 5.0, "type": "H"} for hh in (2, 14)]}}
    pulse = lambda k: 3000 if ((k // 4) % 24) in (6, 7, 8, 16, 17, 18, 19) else 800  # a dam's two releases a day (Cowlitz at Kosmos: osc True, lib/wx.py tidal False on live USGS data 2026-11-10)
    dam = mk(pulse, lambda k: pulse(k) / 600, tides)
    tide = mk(lambda k: 5000 + 3000 * m_.sin(2 * m_.pi * k * 15 / 745.2), lambda k: 5 + 2 * m_.sin(2 * m_.pi * k * 15 / 745.2), tides)
    assert dam["osc"] and not dam["tidal"] and render.b3.b_tides(dam) is None and "Tidal reach" not in render.hero(dam, None) and tide["tidal"], "audit #2: a dam's daily release cycle near a tide station read as tidal with a tide table (Cowlitz at Kosmos), or a 12.4 h tide did not read as tidal"
    rows_ = [[(datetime.date.today() - datetime.timedelta(days=3 + i)).isoformat(), 100.0 + i] for i in range(3700, -1, -1)]
    my_ = collect.multiyear(rows_)
    tdy = datetime.date.today()
    lyd = tdy.replace(year=tdy.year - 1, day=28) if (tdy.month, tdy.day) == (2, 29) else tdy.replace(year=tdy.year - 1)
    assert my_ and lyd.isoformat() in my_["ly"], "audit #3: the daily window stops last year at this year's newest daily mean, not at today's date"
    d3 = dam["ldate"]
    ly3 = d3.replace(year=d3.year - 1, day=28) if (d3.month, d3.day) == (2, 29) else d3.replace(year=d3.year - 1)
    G3 = dict(dam, rec=dict(dam["rec"], multiyear={"as_of": (d3 - datetime.timedelta(days=6)).isoformat(), "span": 50, "series": {str(ly3.year): [111.0] * 50}, "ly": {ly3.isoformat(): 2280.0, (ly3 - datetime.timedelta(days=6)).isoformat(): 111.0}}))
    assert render.last_year_flow(G3) == (2280.0, "%s, %d" % (render.md(ly3), ly3.year)) and "newest daily mean USGS has published" not in render.hero(G3, None), "audit #3: last year's value taken from another day (Nehalem: Nov 4 for Nov 10), or the false 'newest USGS has published' line is back"
    assert render.last_year_flow(dict(G3, rec=dict(G3["rec"], multiyear=dict(G3["rec"]["multiyear"], ly={})))) is None, "audit #3: a missing last-year day was filled from another date"
    lake_row = {"lake": "1", "river": "Lake Lanier", "place": "Buford Dam"}
    h4 = render.hero(mk(None, lambda k: 1062.4, row=lake_row, codes=[("72036", lambda k: 1643, "Kacre-ft")]), None)
    assert "1,643,000" in h4 and "publishes no storage" not in h4 and r_.findall(r'<div class="tile (\w+)', h4)[0] == "flow", "audit #4: USGS storage published as 72036 (thousand acre-ft) not read; the page said USGS publishes none (Lanier, Allatoona)"
    h8 = render.hero(mk(None, lambda k: 1062.4, row=lake_row), None)
    assert r_.findall(r'<div class="tile (\w+)', h8)[0] == "stage" and "publishes no storage" in h8 and r_.search(r'class="tile wtemp[^"]*">(?:(?!</div>).)*<b>Unknown</b>', h8, r_.S), "audit #8: an empty storage tile leads the lake page, or a missing water temperature has no word"
    G5 = dict(dam, sg=[(n0, 1.69, {"unit_of_measure": "ft"})], rec=dict(dam["rec"], nwps={"lid": "BAXG1", "name": "Baxley", "stage_units": "ft", "categories": {"action": 72.5, "minor": 74.5}, "obs_stage": {"t": n0.isoformat(), "v": 63.2}}))
    assert "11.0 ft on the USGS gauge scale" in render.next_impact(G5), "audit #5: an NWS stage shown beside a USGS gage height on another zero point without the conversion (Baxley 1.66 vs 72.5 ft)"
    ni0 = render.next_impact(dict(G5, rec=dict(G5["rec"], nwps=dict(G5["rec"]["nwps"], obs_stage=None))))
    assert "above" not in ni0 and "Unknown" in ni0, "audit #5: with no NWS reading to compare zero points, a distance from the USGS reading to an NWS stage was printed"
    md7 = n0.astimezone(zoneinfo.ZoneInfo("America/Los_Angeles")).date().isoformat()[5:10]
    G7 = mk(lambda k: 500, lambda k: 2.0, {"stats": {md7: [40, 100, 200, 300, 400, 800, 1500, 1800, 2500, 3000]}, "streamcat": {"vals": {"damdensws": 0.1}}}, row={"drainage_sqmi": "1000"})
    h7 = render.hero(G7, None)
    assert r_.match(r'<p class="status dv w3">The river here is typical for \w+ \d+ and steady\.</p><p class="answer"', h7), "audit #7: no plain status sentence above the answer strip"
    assert "About 259 dams upstream (our estimate: EPA StreamCat" in h7, "audit #11: the dams-upstream count does not name EPA StreamCat or say it is our arithmetic"
    hl_ = lambda hh, v, k: [(n0 + datetime.timedelta(hours=hh)).isoformat(), v, k]
    cst = mk(None, lambda k: 3.2, {"coops": {"fetched_at": n0.isoformat(), "pred": [[(n0 + datetime.timedelta(minutes=6 * i)).isoformat(), 4.0] for i in range(-10, 240)], "hilo": [hl_(-1, 8.0, "H"), hl_(5, 1.0, "L"), hl_(11, 9.1, "H")]}},
             row={"coast": "1", "river": "Astoria", "place": "Astoria", "state": "OR"}, codes=[("MLLW", lambda k: 3.2, "ft")])
    sc = render.b2.b_stage_chart(cst)["source"]
    assert "NOAA CO-OPS predicted tide" in sc and "National Weather Service forecast point" not in sc, "audit #10: the coast chart source names a blank NWS forecast point for NOAA's predicted tide"
    nt = r_.search(r'data-tide="([^"|]+)\|[^"]*" data-tides="([^"]*)">(\w+)', render.hero(cst, None))
    assert nt and render.parse_t(nt.group(1)) > n0 and nt.group(3) == "Low" and nt.group(2).count(";") == 1 and "data-tides" in render.TIDE_JS, "audit #15: the next tide is not after the build time, or the tile carries no tide list for the browser to step forward"
    assert "No NOAA tide prediction after this page was built" in render.hero(dict(cst, rec=dict(cst["rec"], coops=dict(cst["rec"]["coops"], hilo=[hl_(-1, 8.0, "H")]))), None), "audit #15: no future tide prediction did not say so"
    world_hub()
    nid_facts()


def world_hub():
    """PLAN 'Every page its own' item 4: a world hub carries data of its own (km order, one chart, warnings, BfG forecast highs) from rows already in cache."""
    from lib.directory import world_page
    nw = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    iso = lambda h: (nw - datetime.timedelta(hours=h)).isoformat()
    ser = lambda base: [[iso(h), base + h % 5] for h in range(168, -1, -1)]
    wxok = {"alerts": [], "fetched_at": iso(1)}
    g = lambda name, km, **k: dict({"name": name, "km": km, "cm": 200.0, "then": 190.0, "time": iso(1), "state": "normal", "series": ser(200), "wx": wxok}, **k)
    # Danube: km counts from the mouth, so it falls downstream; the list starts upstream, its middle out of order
    rows = [g("ULM", 2586.0, wx={"abroad": True}), g("KELHEIM", 2414.0, fc={"at": iso(2), "pts": [[iso(-6), 250.0, "forecast"], [iso(-30), 270.0, "estimate"]]}), g("INGOLSTADT", 2458.0),
            g("REGENSBURG", 2379.0, time=iso(30)), g("HOFKIRCHEN", 2256.0), g("STRAUBING", 2321.0),
            g("PASSAU", 2225.0, wx={"alerts": [{"event": "Frost", "ends": (nw + datetime.timedelta(hours=6)).isoformat()}], "fetched_at": iso(1)})]
    page = {"slug": "danube", "river": "Danube", "lead": "Official gauges, upstream to downstream."}
    h = world_page(page, {"fetched_at": iso(1), "rows": rows}, nw, ())
    order = [n.title() for n in ("ULM", "INGOLSTADT", "KELHEIM", "REGENSBURG", "STRAUBING", "HOFKIRCHEN", "PASSAU")]
    assert [h.index(">%s<" % n) for n in order] == sorted(h.index(">%s<" % n) for n in order) and "by the agency's river kilometre" in h, "world hub: Danube not upstream to downstream by km (km falls downstream)"
    chart = h[h.index('id="world_level_chart"'):h.index("</section>", h.index('id="world_level_chart"'))]
    assert chart.count('<polyline') == 8 and "4 of 6 reporting gauges" in chart and "Regensburg" not in chart and "Ulm" in chart and "Passau" in chart, "world hub: chart not capped at 4 evenly spaced reporting lines, or a gauge not reporting drawn"
    assert "Not reporting" in h and ">Regensburg<" in h, "world hub: a gauge not reporting is not named in the table"
    al = h[h.index('id="world_alerts"'):]
    assert "Frost" in al and "Ulm (outside Germany" in al and "DWD" in al, "world hub: a DWD warning in force, or a gauge DWD does not cover, not said"
    fc = h[h.index('id="world_forecast"'):]
    assert "270 cm" in fc and "(estimate)" in fc and "8.9 ft" in fc and "other 6 gauges" in fc, "world hub: BfG forecast high, its estimate flag or the count without a forecast wrong"
    # feed down: every check stale, so the warnings section hides; the gauge list stays
    down = world_page(page, {"fetched_at": iso(1), "rows": [dict(r, wx={}) for r in rows]}, nw, ())
    assert 'id="world_alerts"' not in down and 'id="world_gauges"' in down, "world hub: a dead warnings feed showed a section (or 'none'), or the gauge list was lost"
    # one gauge: no chart, the gauge page has its own
    one = world_page(page, {"fetched_at": iso(1), "rows": rows[:1]}, nw, ())
    assert 'id="world_level_chart"' not in one and "Listed upstream" not in one, "world hub: one gauge drew a chart or claimed an order"
    # a country hub with mixed units: each in its own unit plus feet, no chart across different rivers and zero points, none in force said once
    ca = {"slug": "canada", "river": "Canada", "lead": "Official gauges.", "feed": "eccc", "flat": True}
    c = world_page(ca, {"fetched_at": iso(1), "rows": [g("01AB", 0, cm=1.25, then=1.2, unit="m", zone="America/Toronto"), g("02CD", 0, cm=125.0, zone="America/Toronto")]}, nw, ())
    assert "1.25 m" in c and "4.1 ft" in c and "125 cm" in c and 'id="world_level_chart"' not in c and "No Environment Canada weather alert in force" in c and "provincial flood forecasting centres" in c, "world hub: mixed units, a cross-river chart, or Canada's no-alert line wrong"


def england(ago):
    """England (feed ea): a tide never reads as a river, a cut-short warning list is Unknown, the label is the agency's normal range, a warning reaches only gauges inside its area,
    and a country without every proof adds no gauge and fails no gate."""
    import math
    stamp = lambda m: (ago(minutes=m)).strftime("%Y-%m-%dT%H:%M:00Z")
    tide = [[stamp(15 * i), 2 + 1.5 * math.sin(2 * math.pi * i * 15 / 745)] for i in range(700, -1, -1)]
    river = [[stamp(15 * i), 1 + 0.001 * (700 - i) + 0.02 * math.sin(i)] for i in range(700, -1, -1)]
    assert wx_mod.tidal(tide) is True and wx_mod.tidal(river) is False and wx_mod.tidal(river[:50]) is None, "a tide read as a river, or a river as a tide"
    stage = {"parameter": "level", "qualifier": "Stage", "unitName": "mASD", "notation": "S-level-stage-i-15_min-mASD", "latestReading": {"dateTime": stamp(0)}}
    station = lambda ms, lo=1.0, hi=3.0: {"items": {"label": "Colwick", "riverName": "River Trent", "lat": 52.95, "long": -1.08, "RLOIid": "2102", "measures": ms,
                                                    "stageScale": {"typicalRangeLow": lo, "typicalRangeHigh": hi, "maxOnRecord": {"value": 5.5, "dateTime": "2000-11-08T12:30:00"}, "minOnRecord": {"value": 0.7}}}}
    asked = []

    def fake(series, ms):
        def get(url, *a, **k):
            asked.append(url)
            if "/readings" in url:
                return {"items": [{"measure": "x/" + stage["notation"], "dateTime": t, "value": v} for t, v in series[::-1]]}
            return station(ms)
        return get
    real = collect.http_json
    try:
        collect.http_json = fake(river, [stage, {"qualifier": "Tidal Level", "unitName": "mAOD", "parameter": "level"}])
        got = collect.fetch_ea("S", None)
        assert got.get("tidal") and not any("/readings" in u for u in asked), "a station with a tidal measure was read as a river"
        collect.http_json = fake(tide, [stage])
        assert collect.fetch_ea("S", None).get("tidal") and not world.ready(collect.fetch_ea("S", {"tidal": True})), "a level that moves with the tide reached a page"
        for v, word in ((0.5, "low"), (2.0, "normal"), (3.5, "high")):
            collect.http_json = fake(river[:-1] + [[river[-1][0], v]], [stage])
            got = collect.fetch_ea("S", None)
            assert got["state"] == word and got["marks"] == {"TRL": 1.0, "TRH": 3.0, "HHW": 5.5} and got["mark_dates"] == {"HHW": "2000-11-08"}, "label or marks not the agency's normal range and dated records: %s" % got["state"]
        assert "Environment Agency label, against its normal range for this gauge, 1.00 m to 3.00 m" in world.to_rec({"feed": "ea", "river": "England", "slug": "england"}, got)["feed"]["label_note"], "the label note does not say whose range"
    finally:
        collect.http_json = real
    square = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[-2, 52], [0, 52], [0, 54], [-2, 54], [-2, 52]]]}}]}
    warn = {"floodAreaID": "A", "severityLevel": 2, "severity": "Flood warning", "description": "River Trent at Colwick", "message": "Flooding is expected."}
    floods = wx_mod.ea_floods({"meta": {}, "items": [warn, dict(warn, floodAreaID="B", severityLevel=4)]})
    assert [f["floodAreaID"] for f in floods] == ["A"], "a warning no longer in force was kept"
    al = wx_mod.ea_alerts(floods, {"A": wx_mod.ea_rings(square)})
    assert [a["event"] for a in wx_mod.alerts_at(52.95, -1.08, al)] == ["Flood warning"] and wx_mod.alerts_at(51.5, -0.1, al) == [], "a warning missed the gauge inside its area, or reached one outside"
    tri = wx_mod.ea_alerts(floods, {"A": [[(52, -2), (54, -2), (54, 0)]]})
    assert wx_mod.alerts_at(53.9, -1.9, tri, collect.EA_NEAR_M) and not wx_mod.alerts_at(52.2, -0.2, tri, collect.EA_NEAR_M), "a gauge inside the area's box but 20 km outside its shape got the warning"
    bank = wx_mod.ea_alerts(floods, {"A": [[(52.9530, -1.0790), (52.9530, -1.0780), (52.9540, -1.0780), (52.9540, -1.0790)]]})  # a bank area 33 m north of the gauge, the channel left out
    assert wx_mod.alerts_at(52.9527, -1.0785, bank, collect.EA_NEAR_M) and not wx_mod.alerts_at(52.9527, -1.0785, bank) and not wx_mod.alerts_at(52.9400, -1.0785, bank, collect.EA_NEAR_M), "a warning for the bank missed the gauge in the channel, or reached one 1.4 km off"
    assert all(("within %d m" % collect.EA_NEAR_M) in t for t in (world.FEEDS["ea"]["flood_line"], dict(world.FEEDS["ea"]["swap"])["Source: Environment Agency alerts for the gauge location"])), "the page states another distance than the code tests"
    assert wx_mod.ea_floods({"meta": {"limit": 2}, "items": [warn, warn]}) is None and wx_mod.ea_floods({"meta": {}}) is None, "a cut-short warning list read as complete"
    assert wx_mod.ea_alerts(floods, {}) is None, "a warning area with no shape read as no warning"
    w = {"alerts": [{"event": "old"}], "fetched_at": "2026-11-01T00:00:00+00:00"}
    try:
        collect.http_json = lambda *a, **k: {"meta": {"limit": 500}, "items": [warn] * 500}
        collect.wx_england({"lat": 52.95, "lon": -1.08}, w, {})
    finally:
        collect.http_json = real
    assert w["fetched_at"] == "2026-11-01T00:00:00+00:00" and w["no_weather"], "a cut-short list refreshed the alert time, so the page could say none"
    hp = [{"slug": "x", "stations": ["A", "B"], "gauge_pages": ["A", "B"]}]
    assert world.drop_held(hp, {"A": ["thin"]}, "2026-11-01") == [] and hp[0]["held"] == {"A": "2026-11-01"}, "a first hold was not dated"
    assert world.drop_held(hp, {"A": ["thin"]}, "2026-11-07") == [] and world.drop_held(hp, None, "2026-12-01") == [], "a gauge dropped before 7 days, or on an unread status"
    assert world.drop_held(hp, {"A": ["thin"]}, "2026-11-08") == ["A"] and hp[0]["gauge_pages"] == ["B"] == hp[0]["stations"] and "thin" in hp[0]["dropped"]["A"] and "held" not in hp[0], "a gauge held 7 days kept its slot, or lost its reason"
    hp = [{"slug": "x", "gauge_pages": ["A"], "held": {"A": "2026-10-01"}}]
    assert world.drop_held(hp, {}, "2026-11-08") == [] and "held" not in hp[0], "a gauge that healed kept its old hold date"
    pages = [{"slug": "england", "feed": "ea", "gauge_pages": []}, {"slug": "rhine", "gauge_pages": ["KAUB"]}]
    unproven =dict(world.PROVED, ea={"reading": "seen on live data 2026-11-03"})
    assert world.listing(pages) == ["pegelonline"] and not world.proof_faults(world.listing(pages), unproven), "a country with no gauge page failed the proof gate"
    assert world.proof_faults(world.listing([dict(pages[0], gauge_pages=["4009"])]), unproven), "a country with a gauge page passed without every proof"
    keep, cache = world.PROVED, (collect.CACHE, world.common.CACHE, collect.http_raw)
    with tempfile.TemporaryDirectory() as d:
        try:
            collect.CACHE = world.common.CACHE = d  # never this machine's or the cloud's own proof
            collect.http_raw = lambda *a, **k: (_ for _ in ()).throw(collect.urllib.error.HTTPError("x", 404, "none yet", {}, None))
            world.PROVED = unproven
            assert world.room("ea", pages, {}) == 0, "a country without every proof had room to add gauges"
            no_alert = {k: "seen on live data, fixture" for k in world.PROOFS if k != "alerts"}
            assert not world.proof_faults(["ea"], {"ea": no_alert}) and world.proof_faults(["eccc"], {"eccc": no_alert}), "England needed an alert proof to ship, or another country shipped without one"
            world.PROVED = dict(keep, ea={k: "seen on live data, fixture" for k in world.PROOFS})
            assert world.room("ea", [dict(pages[0], gauge_pages=[])], {}) == 2, "a country with no page yet opened more than 2 a day"
            assert world.room("ea", pages, {}) > 0 and world.room("ea", [dict(pages[0], gauge_pages=list(range(25)))], {}) > 0, "a country cap is back"
            assert world.room("ea", [dict(pages[0], gauge_pages=["4009"])], {"4009": ["thin"]}) == 0 and world.room("ea", pages, None) == 0, "a country whose every page is thin, or an unread live status, still added gauges"
            world.PROVED = dict(keep, ea=dict(keep["ea"], alerts=""))
            probe(warn, square, pages)
            assert world.recorded([dict(pages[0], proof={"alerts": "carried by the release that listed the first gauge"})])["ea"] and not world.proof_faults(["ea"], world.proved([dict(pages[0], proof={"alerts": "carried by the release that listed the first gauge"})])), "a proof committed in world-pages.json was not read once the cache was lost"
        finally:
            world.PROVED = keep
            collect.CACHE, world.common.CACHE, collect.http_raw = cache


def england_page():
    """An England page before and after a live warning proves the point test, the rain tile in its four states, and the thin floor (owner 2026-11-03)."""
    import re as re_
    now = datetime.datetime.now(datetime.timezone.utc)
    iso = lambda m: (now - datetime.timedelta(minutes=m)).strftime("%Y-%m-%dT%H:%M:00Z")
    r = {"name": "4009", "title": "River Trent at Colwick", "lat": 52.95, "lon": -1.08, "unit": "m", "zone": "Europe/London", "cm": 1.2, "time": iso(5), "then": 1.1, "state": "normal", "range": [0.5, 2.0], "marks": {"TRL": 0.5, "TRH": 2.0},
         "series": [[iso(5 + 15 * i), 1.2 - 0.001 * i] for i in range(200, -1, -1)], "ea": {"flow": None}, "wx": {"fetched_at": now.isoformat(), "alerts": [], "no_weather": "Met Office data needs a key we do not hold"}}
    p = {"slug": "fixture-england", "river": "England", "flat": True, "feed": "ea"}
    sec = lambda h, i: re_.sub(r"<[^>]+>", " ", re_.search(r'<section[^>]*id="%s".*?</section>' % i, h, re_.S).group(0))
    tile = lambda h: re_.sub(r"<[^>]+>", " ", re_.search(r'<div class="tile rain[^"]*">.*?</div>', h, re_.S).group(0))
    keep = (collect.CACHE, world.common.CACHE)
    with tempfile.TemporaryDirectory() as d:
        try:
            collect.CACHE = world.common.CACHE = d  # no proof on file: never this machine's or the cloud's
            h = world.page(p, r, now)[1]
            al = sec(h, "alerts")
            assert "Unknown" in al and "check-for-flooding.service.gov.uk/alerts-and-warnings" in h.split('id="alerts"', 1)[1].split("</section>", 1)[0], "an unproven England alert block is not Unknown with the GOV.UK link"
            assert not re_.search(r"No (active |Environment Agency )?flood warning|No flood warnings in force|No active|could not be loaded|were returned", re_.sub(r"<[^>]+>", " ", h)), "an unproven England page said there are no warnings, or that alerts failed to load"
            assert not re_.search(r"\bnone\b", re_.sub(r"<[^>]+>", " ", world.EA_UNPROVEN_LINE + "".join(b for _, b in world.EA_UNPROVEN)), re_.I), "unproven England warning text says none, read as no warnings"
            assert "Flood warnings: Unknown on this page" in h and "within 150 m" not in h,"the flood line claims a check that is not proven"
            h2 = world.page(dict(p, proof={"alerts": "Environment Agency Flood warning (level 2), fixture"}), r, now)[1]
            assert "No Environment Agency flood warning or flood alert is in force for an area that holds this gauge" in h2 and "Flood warnings: Unknown" not in h2, "a proven England page lost its normal alert answer"
        finally:
            collect.CACHE, world.common.CACHE = keep
    assert "Unknown" in tile(h) and "No Environment Agency rain gauge read" in tile(h), "rain never collected did not say Unknown"
    for g, want in (({"station": "E7050", "km": 3.24, "mm": 4.6, "to": iso(30)}, ("4.6 mm", "E7050, 3.2 km away", "24 h to")),
                    ({"station": "E7050", "km": 3.2, "mm": 0.0, "to": iso(30)}, ("0.0 mm",)),
                    ({"station": "E7050", "km": 3.2, "mm": 4.6, "to": iso(8 * 60)}, ("Unknown", "Old value: 4.6 mm")),
                    ({"station": "E7050", "km": 3.2, "mm": None, "why": "90 of the 96 readings of the 24 h to its last one"}, ("Unknown", "90 of the 96")),
                    ({"why": "No Environment Agency rain gauge within 15 km"}, ("Unknown", "within 15 km"))):
        t = tile(world.page(p, dict(r, wx=dict(r["wx"], ea_rain=g)), now)[1])
        assert all(w in re_.sub(r"\s+", " ", t) for w in want) and ("Unknown" in want or "Unknown" not in t), "rain tile wrong for %s: %s" % (g, t[:200])
    day = {(now - datetime.timedelta(minutes=15 * i)).strftime("%Y-%m-%dT%H:%M:00Z"): 0.2 for i in range(100)}
    assert wx_mod.rain_total(day, 900)[0] == round(96 * 0.2, 1), "a 24 h total did not add exactly the 96 readings of its day"
    assert wx_mod.rain_total(dict(list(day.items())[:95]), 900)[0] is None and wx_mod.rain_total(dict(day, **{max(day): None}), 900)[0] is None and wx_mod.rain_total({}, 900)[0] is None, "a missing reading or no readings read as a total"
    row = lambda d, v, c="Complete", q="Good": {"date": d, "value": str(v), "completeness": c, "quality": q}
    lows = [row("%d-11-03" % y, 0.5 + y % 3) for y in range(2005, 2026)] + [row("2010-11-03", 0.1), row("2011-11-03", -9, q="Suspect"), row("2012-11-03", -9, c="Incomplete")] + [row((datetime.date(2020, 1, 1) + datetime.timedelta(i)).isoformat(), 0.7) for i in range(366)]
    highs = [dict(x, value=str(float(x["value"]) + 1)) for x in lows if x["value"] != "-9"]
    got = wx_mod.ea_days(lows, highs, 2026)
    assert got["days"]["11-03"][:3] == [0.1, None, 3.5] and got["day_years"] == 21, "a suspect or incomplete day reached the record, a repeated date was not its lowest, or the count is wrong: %s" % got["days"]["11-03"]
    assert [y[0] for y in got["years"]] == [2020] and got["years"][0][3] == 0.7, "a year with under 300 days, or this year, was listed"
    assert wx_mod.ea_days(lows[:9], highs[:9], 2026) == {}, "under 10 years said something"
    # the block keys by the LAST READING's local date, which is yesterday just after midnight (dry run 2026-11-07 00:03 UTC failed): fixture covers both
    rh = dict(r, **dict(got, days={(now + datetime.timedelta(days=k)).astimezone(zoneinfo.ZoneInfo("Europe/London")).strftime("%m-%d"): got["days"]["11-03"] for k in (-1, 0)}))
    hh =world.page(p, rh, now)[1]
    hist = sec(hh, "world_history")
    idx = {(52, -2): [(52.96, -1.10, "River Leen at Bulwell", "/england/river-leen-at-bulwell/", "1.00 m", "Normal")], (53, -2): [(53.9, -1.5, "Far River", "/england/far/", "2.00 m", "High")]}
    assert [x[1] for x in world.near({"lat": 52.95, "lon": -1.08}, idx, set())] == ["River Leen at Bulwell"] and [x[1] for x in world.near({"lat": 52.95, "lon": -1.08}, idx, {"/england/river-leen-at-bulwell/"})] == [], "nearby gauges: a gauge over 100 km away was listed (owner 2026-11-09: no forced links), or a skipped page shows"
    assert [x[1] for x in world.near({"lat": 10.0, "lon": 10.0}, idx, set(), 1)] == [], "nearby gauges: a page with no gauge within 100 km was given one thousands of km away (owner 2026-11-09)"
    hn = world.page(p, rh, now, (), (), idx)[1]
    hy = world.page(p, dict(rh, days=None, deciles=None), now)[1]
    rt = sec(hn, "rate_of_change") if 'id="rate_of_change"' in hn else ""
    assert "Last 1 h" in rt and "Last 24 h" in rt and "Highest in 7 days" in rt and "our arithmetic" in rt and " ft" not in rt, "a world page has no rate of change, or it shows feet as the level (0 of 37 live, 2026-11-04)"
    assert 'id="world_history"' in hy and "2020" in sec(hy, "world_history"), "yearly highs and lows hid because the gauge has no daily history (6 of 8 Canadian pages, 2026-11-04)"
    rp = dict(rh, peaks=[[2023, 1.234, "2023-04-18"], [2024, 2.5, "2024-04-02"]])
    hp = world.page(p, rp, now)[1]
    assert 'id="annual_peaks"' in hp and "2024-04-02" in sec(hp, "annual_peaks") and "annual_peaks" not in world.missing(hp, rp) and "annual_peaks" in world.missing(hp.replace('id="annual_peaks"', 'id="x"'), rp), "Canada's yearly peaks are cached but not on the page, or a page without them ships (COVER b_peaks have)"
    assert "openstreetmap.org/?mlat=" in hn and 'id="about_gauge"' in hn and "Station number" in sec(hn, "about_gauge"), "a world page has no About this gauge block (0 of 37 live, 2026-11-04)"
    assert 'id="nearby_gauges"' in hn and 'href="/england/river-leen-at-bulwell/"' in hn and "nearby_gauges" not in world.missing(hn, rh), "a world page with a gauge 2 km away shows no nearby gauges (0 of 37 live, 2026-11-04)"
    assert '<nav class="jump"' in hh and 'href="#world_history"' in hh, "an England page has no jump links while US and German pages do (UI review 2026-11-04)"
    assert " ft)" in hh and " ft)" not in hh, "a level and its feet can break across lines on a phone, '260 cm (2.5 / ft)' (UI review 2026-11-04)"
    assert "fetch(" not in world.LIVE and "data-live=stage" not in world.LIVE, "the world page swaps its level in the browser while its feet, change and label stay from the build (review 2026-11-04)"
    assert 'class="rb"' not in hh and "bottom 95%" not in hh, "an empty Lower-Typical-Higher scale with no marker, or the self-contradicting England range sentence, is back (UI review 2026-11-04)"
    assert hh.find("Not on this page yet") > hh.find('id="world_history"') > 0 and hh.count("Unknown on this page") <= 1, "the to-do list sits above the readings, or England repeats its Unknown flood line"
    assert "this date in 21 years" in hist and "Median" not in hist and "daily means" not in hist and "Hydrology API" in hist, "England history claims a median or daily means the agency does not publish, or lost its source: %s" % hist[:300]
    z = lambda m: (now + datetime.timedelta(hours=m)).strftime("%Y-%m-%dT%H:00Z")
    geo = lambda run, ts: {"features": [{"properties": {"modelRunDate": run, "timeSeries": ts}}]}
    hourly = geo(z(-1), [{"time": z(i), "screenTemperature": 9.4, "probOfPrecipitation": 40, "windSpeed10m": 5.0, "windDirectionFrom10m": 270} for i in range(30)] + [{"time": z(31)}])
    daily = geo(z(-1), [{"time": (now + datetime.timedelta(days=i)).strftime("%Y-%m-%dT00:00Z"), "dayMaxScreenTemperature": 12.6, "nightMinScreenTemperature": 3.2, "dayProbabilityOfPrecipitation": 20} for i in range(7)])
    met = wx_mod.met_forecast(hourly, daily, zoneinfo.ZoneInfo("Europe/London"))
    assert len(met["hourly"]) == 30 and met["hourly"][0]["windSpeed"] == "18 km/h" and met["hourly"][0]["windDirection"] == "W" and met["hourly"][0]["shortForecast"] == "", "Met Office hourly parse wrong, or it guessed sky words: %s" % met["hourly"][0]
    assert len(met["periods"]) == 14 and met["periods"][0]["temperature"] == 13 and met["periods"][1]["name"].endswith(" night"), "Met Office daily parse wrong"
    assert wx_mod.met_forecast(geo(z(-1), [{"time": z(1)}]), {}, zoneinfo.ZoneInfo("Europe/London")) == {}, "a forecast with no rows gave a time that would date old rows as new"
    hm = world.page(p, dict(rh, wx=dict(r["wx"], no_weather=None, **met)), now)[1]
    for b in ("hourly_forecast", "weather_forecast"):
        s = sec(hm, b)
        assert "Met Office" in s and "Environment Agency" not in s, "England weather is not credited to the Met Office: %s" % [x[max(0, x.find("Environment Agency") - 150):][:300] for x in [s]]
    assert "Powered by Met Office data" in re_.sub(r"<[^>]+>", " ", hm), "the Met Office attribution is missing"
    assert re_.search(r"<tbody>(.*?)</tbody>", re_.search(r'<section[^>]*id="hourly_forecast".*?</section>', hm, re_.S).group(0), re_.S).group(1).count("</tr>") == 8, "the hourly table is not 8 rows at 3-hour steps; 24 rows were 4 phone screens (UI review 2026-11-04)"
    assert ">Sky</th>" not in re_.search(r'<section[^>]*id="hourly_forecast".*?</section>', hm, re_.S).group(0), "a Sky column with no sky words showed blank on every row (live Colwick 2026-11-04)"
    assert not world.thin(h), "an England page with a reading and the alerts block was held for lacking weather: %s" % world.thin(h)
    assert world.thin(h.replace('id="alerts"', 'id="x"')) == [], "a page with a reading was held for a missing alerts block (owner 2026-11-08: only no reading holds)"
    world.THIN.clear()



def probe(warn, square, pages):
    """England's alert proof comes from a run, never a person: only a real warning in force (level 1 to 3), over an active non-tidal level station, with its area's shape."""
    import os as os_
    st = lambda **k: dict({"notation": "4009", "label": "Colwick", "lat": 52.95, "long": -1.08, "status": "x/statusActive", "measures": [{"qualifier": "Stage", "unitName": "mASD"}]}, **k)
    real = collect.http_json
    seen = os_.path.join(collect.CACHE, "_ea-proof.json")

    def run(floods, stations, shape=square):
        def get(url, *a, **k):
            if "/polygon" in url:
                if shape is None:
                    raise OSError("no shape")
                return shape
            return {"items": stations} if "id/stations" in url else floods
        collect.http_json = get
        try:
            collect.ea_probe({})
        finally:
            collect.http_json = real
        return os_.path.exists(seen) and world.alerts_proven(pages[0])
    level = lambda n: {"meta": {}, "items": [dict(warn, severityLevel=n)]}
    a2 = wx_mod.ea_alerts([warn], {"A": wx_mod.ea_rings(square)})[0]
    assert wx_mod.ea_proof([a2], [st()], 150) and wx_mod.ea_proof([dict(a2, level=4)], [st()], 150) is None and wx_mod.ea_proof([], [st()], 150) is None and wx_mod.ea_proof(None, [st()], 150) is None, "a warning no longer in force, or no warning at all, proved England"
    for why, floods, stations, shape in (("level 4", level(4), [st()], square), ("an empty list", {"meta": {}, "items": []}, [st()], square), ("a cut-short list", {"meta": {"limit": 1}, "items": [warn]}, [st()], square),
                                         ("a missing shape", level(2), [st()], None), ("a tidal station", level(2), [st(measures=[{"qualifier": "Stage", "unitName": "mASD"}, {"qualifier": "Tidal Level", "unitName": "mAOD"}])], square),
                                         ("a closed station", level(2), [st(status="x/statusClosed")], square), ("a station outside the area", level(2), [st(lat=51.5, long=-0.1)], square)):
        assert not run(floods, stations, shape), "%s unlocked England" % why
    assert run(level(2), [st()]), "a real level 2 warning over an active river station did not unlock England"
    assert "level 2" in json.load(open(seen, encoding="utf-8"))["ea"]["alerts"] and "4009" in json.load(open(seen, encoding="utf-8"))["ea"]["alerts"], "the proof does not name its warning and station"

    # RIDB facility details (2026-11-10): fee, reservations, address, directions, agency, email, first sentence, in RIDB's own words
    fac = lambda **k: dict({"FacilityID": "1", "FacilityName": "BOLDING MILL", "FacilityTypeDescription": "Campground", "FacilityLatitude": 34.30, "FacilityLongitude": -83.95, "ACTIVITY": [{"ActivityName": "BOATING"}],
                            "FacilityUseFeeDescription": "<p>Monday through Friday - $45.00</p>\n<p>Saturday and Sunday - $75.00</p>", "Reservable": True, "FacilityReservationURL": "", "FacilityPhone": "770-534-6960",
                            "FacilityEmail": "ranger@usace.army.mil", "ORGANIZATION": [{"OrgName": "US Army Corps of Engineers"}], "FacilityDirections": "<p>Take SR 400 north &amp; turn right.</p>",
                            "FACILITYADDRESS": [{"FacilityStreetAddress1": "4055 CHESTATEE ROAD", "City": "GAINESVILLE", "AddressStateCode": "GA", "PostalCode": "50506-0567"}],
                            "FacilityDescription": "<h2>Overview</h2>\nBolding Mill is on the lake.  <br/><br/>It has a beach. More text."}, **k)
    recs = [fac(), fac(), fac(FacilityID="2", FacilityName="Far Ramp", FacilityLatitude=36.0), fac(FacilityID="3", FacilityName="Shoal Creek Ramp", FacilityUseFeeDescription="", Reservable=False, FacilityEmail="not an email", FacilityDescription="Fishing license required."),
            fac(FacilityID="4", FacilityName="Long Fee Ramp", FacilityUseFeeDescription="x" * 400, FacilityReservationURL="https://www.recreation.gov/x")]
    real_gt, real_sec = collect.get_text, collect.secret
    collect.get_text, collect.secret = (lambda *a, **k: json.dumps({"RECDATA": recs})), (lambda n: "k")
    try:
        rd = collect.fetch_ridb(34.25, -84.0)
    finally:
        collect.get_text, collect.secret = real_gt, real_sec
    names = [s["name"] for s in rd["sites"]]
    assert names.count("BOLDING MILL") == 1 and "Far Ramp" not in names, "RIDB: a repeated facility listed twice, or one past 15 mi listed: %s" % names
    bm = rd["sites"][names.index("BOLDING MILL")]
    assert bm["fee"] == "Monday through Friday - $45.00 Saturday and Sunday - $75.00" and bm["directions"] == "Take SR 400 north & turn right." and bm["about"] == "Bolding Mill is on the lake.", "RIDB HTML not stripped to plain words: %r" % bm
    assert bm["address"] == "4055 Chestatee Road, Gainesville, GA" and "50506" not in json.dumps(bm) and bm["org"] == "US Army Corps of Engineers" and bm["reservable"] is True, "RIDB address, ZIP or agency wrong: %r" % bm
    from lib import blocks3 as b3r
    h = b3r.b_recreation({"rec": {"ridb": rd}, "zone": zoneinfo.ZoneInfo("America/New_York")})["body"]
    rows = [t for t in re.findall(r"<tr>.*?</tr>", h, re.S) if "<td" in t]
    assert len(rows) == 3 and h.count(">Bolding Mill<") == 1, "RIDB: wrong row count %d" % len(rows)
    assert "Recreation.gov lists it as reservable" in rows[0] and "href=\"https://www.recreation.gov/x\"" not in rows[0] and "$45.00" in rows[0], "RIDB: reservable with no URL must say so with no link"
    assert "Fee not stated by Recreation.gov" in h and "Not listed as reservable" in h and "not an email" not in h and "license" not in h, "RIDB: missing fee, not reservable, a bad email or a BANNED word mishandled"
    assert "Fees: see the site on Recreation.gov" in h and "x" * 400 not in h and '<a href="https://www.recreation.gov/x" rel="noopener">Reservable on Recreation.gov</a>' in h, "RIDB: a fee too long to show whole was cut, or a reservation URL not linked"
    assert not re.search(r"&lt;/?[a-zA-Z]|<p>Monday|\b(safe|open now)\b", h) and len(re.findall(r"<th ", h)) <= 5, "RIDB: HTML shown as text, a verdict, or more than 5 columns"
    old = {"fetched_at": "2026-11-09T00:00:00Z", "radius_mi": 15, "sites": [{"name": "OLD", "type": "Campground", "mi": 2.0, "activities": [], "water": [], "phone": "", "url": ""}]}
    assert "Unknown" in b3r.b_recreation({"rec": {"ridb": old}, "zone": zoneinfo.ZoneInfo("America/New_York")})["body"], "RIDB: a cache from before the fee field claimed 'Fee not stated'"
    # 2026-11-12: 28 live pages held by the sentence-repeat gate: sites run by one office share an address and a sentence of their descriptions
    fcfs = "This location is available on a first-come, first-served basis."
    sh = {"fetched_at": "2026-11-12T00:00:00Z", "radius_mi": 15, "sites": [dict(name=n, type="Campground", mi=float(i + 1), activities=[], water=[], phone="", url="", fee="",
          about="%s %s" % (fcfs, "Own words for %s here." % n), address="P.O. Box 309, Carbondale, CO") for i, n in enumerate(("ALPHA", "BETA", "GAMMA"))]}
    h2 = b3r.b_recreation({"rec": {"ridb": sh}, "zone": zoneinfo.ZoneInfo("America/New_York")})["body"]
    assert h2.count("first-come, first-served") == 1 and h2.count("P.O. Box 309, Carbondale, CO") == 1 and h2.count("Own words for") == 3 and h2.count("is listed once, under the first site") == 1 and "same as listed" not in h2, "RIDB: a shared address or sentence was repeated, an address was split, a note repeated, or a site's own words were dropped"
    assert not b3r._ridb_ok("Follow Highway 131 to the fork and and stay left.") and not b3r._ridb_ok("the picnic pavilion Pavilion is 15 miles") and not b3r._ridb_ok("Open (May to Sept.") and not b3r._ridb_ok("None.") and b3r._ridb_ok("Open (May to Sept.)"), "RIDB: a doubled word, a lone bracket or 'None.' passed into a page"
    # PLAN 20: gate gaps (research outside open_wave; new block types without a review)
    from lib import indexing as _ix, page as _pgx
    cfg_ = {"open": True, "site_pages": True, "allow": {"/research/peak-month/", "/research/tides/"}, "pulled": set(), "held": (), "research_ok": {"/research/peak-month/"}, "research_demand": {"/research/peak-month/", "/research/tides/"}}  # tides allowed but not reviewed at this version
    assert not _ix.indexable("/research/", cfg_) and not _ix.indexable("/research/tides/", cfg_) and _ix.indexable("/research/peak-month/", cfg_) and _ix.indexable("/about/", cfg_), "20: research pages indexable without open_wave, or a site page lost"
    assert not _ix.sitemap_ok("/research/tides/", cfg_), "20: a research page not opened is in the sitemap"
    # PLAN 22 lock 1: review of the exact method version
    td2 = tempfile.mkdtemp()
    os.makedirs(os.path.join(td2, "lib")); os.makedirs(os.path.join(td2, "data"))
    json.dump({"/research/a/": "v2", "/research/b/": "v2"}, open(os.path.join(td2, "data", "research-methods.json"), "w"))  # each page's own version
    json.dump({"research": {"/research/a/": "v2", "/research/b/": "v1"}}, open(os.path.join(td2, "data", "reviewed.json"), "w"))
    assert _ix.research_reviewed(td2) == {"/research/a/"}, "22: a page reviewed at an older method version counted as reviewed"
    open(os.path.join(td2, "data", "reviewed.json"), "w").write("{torn")
    assert _ix.research_reviewed(td2) == set(), "22: a torn reviewed.json opened research pages (must fail closed)"
    # PLAN 24 lock 6: measured search demand
    open(os.path.join(td2, "data", "keyword-tiers-water.csv"), "w").write("keyword,tier,bid_high_cad,kind\nLake  Levels,5000,1.0,lake\nflood stage,0,0,river\n")
    open(os.path.join(td2, "data", "research-keywords.csv"), "w").write("url,seed\n/research/a/,lake levels\n/research/b/,flood stage\n/research/c/,never asked phrase\n")
    assert _ix.research_demand(td2) == {"/research/a/"}, "24: demand wrong (case and spaces, 0 searches, or a never-asked seed)"
    cfg2 = dict(cfg_, allow={"/research/", "/research/peak-month/"}, research_ok={"/research/", "/research/peak-month/"}, research_demand=set())
    assert not _ix.indexable("/research/peak-month/", cfg2) and not _ix.indexable("/research/", cfg2), "24: a research page or the index opened with no measured demand"
    cfg2["research_demand"] = {"/research/peak-month/"}
    assert _ix.indexable("/research/peak-month/", cfg2) and _ix.indexable("/research/", cfg2), "24: a reviewed, allowed page with measured demand stayed closed, or the index did not follow it"
    rb_, rv_ = _pgx.reviewed_blocks, os.environ.pop("RWL_REVIEW", None)
    try:
        _pgx.reviewed_blocks = lambda: frozenset({"water_speed"})
        assert _pgx.block_ready("water_speed") and not _pgx.block_ready("like_today") and _pgx.block_ready("depth"), "20: a reviewed new block hidden, an unreviewed one shown, or an old block hidden"
        os.environ["RWL_REVIEW"] = "1"
        assert _pgx.block_ready("like_today"), "20: a review build hid the block it is meant to review"
    finally:
        _pgx.reviewed_blocks = rb_
        os.environ.pop("RWL_REVIEW", None)
        if rv_ is not None:
            os.environ["RWL_REVIEW"] = rv_
    _pgx.research_open.cache_clear()
    ro_ = _pgx.research_open
    _pgx.research_open = lambda: False
    try:
        assert 'href="/research/"' not in _pgx.footer(), "20: the footer links research pages Google may not index"
    finally:
        _pgx.research_open = ro_
    # PLAN 20: open_wave --open lets a named research page into Google; a page the last build did not serve is refused
    import importlib.util as _iu
    _sp = _iu.spec_from_file_location("ow_", os.path.join(os.path.dirname(os.path.abspath(__file__)), "open_wave.py"))
    ow_ = _iu.module_from_spec(_sp)
    _sp.loader.exec_module(ow_)
    td_ = tempfile.mkdtemp()
    os.makedirs(os.path.join(td_, "dist"))
    json.dump({"urls": ["/research/", "/research/tides/"]}, open(os.path.join(td_, "dist", "_urls.json"), "w"))
    ix_ = os.path.join(td_, "ix.json")
    json.dump({"open": True, "site_pages": True, "allow": ["/river/a/b/"]}, open(ix_, "w"))
    ow_.IX, ow_.ROOT, argv_ = ix_, td_, sys.argv
    try:
        sys.argv = ["open_wave.py", "--open", "/research/tides/"]
        ow_.main()
        assert json.load(open(ix_))["allow"] == ["/research/tides/", "/river/a/b/"], "20: --open did not add the page"
        sys.argv = ["open_wave.py", "--open", "/research/ghost/"]
        try:
            ow_.main()
            raise AssertionError("20: --open let in a page the build does not serve")
        except SystemExit:
            pass
    finally:
        sys.argv = argv_
    # PLAN 19d: the biggest floods, day by day
    dly = [[(datetime.date(1990, 1, 1) + datetime.timedelta(days=k)).isoformat(), 100.0] for k in range(12000)]
    dv = dict(dly)
    for dd_, pk in (("2000-05-10", 9000.0), ("2010-03-01", 7000.0), ("2015-06-01", 5000.0)):
        d_ = datetime.date.fromisoformat(dd_)
        for k, f_ in enumerate((0.2, 0.6, 1.0, 0.9, 0.7, 0.4, 0.2)):
            dv[(d_ + datetime.timedelta(days=k - 2)).isoformat()] = pk * f_
    dly = sorted(dv.items())
    pks = {"rows": [["2000-05-10", 9500.0, None, None, ""], ["2000-05-15", 9400.0, None, None, ""], ["1950-01-01", 99999.0, None, None, ""], ["1985-01-01", 50000.0, None, None, "HISTORIC"],
                    ["2010-03-01", 7500.0, None, None, ""], ["2012-01-01", 8000.0, None, None, "MAXDAILYMEAN"], ["2015-06-01", 5500.0, None, None, "ESTIMATED"]]}
    bf = collect.big_floods(dly, pks)
    assert bf and [f["date"] for f in bf["floods"]] == ["2000-05-10", "2010-03-01", "2015-06-01"], "19d: wrong floods picked (before the daily record, historic, daily mean, or a second peak of one flood used): %s" % (bf and [f["date"] for f in bf["floods"]])
    assert collect.big_floods(dly, {"rows": [["2000-05-10", 9500.0, None, None]]}) is None and collect.big_floods([], pks) is None, "19d: old cache rows or no daily record still built floods"
    from lib.charts import b_floods
    bfb = b_floods({"rec": {"floods": bf}})
    assert bfb and "peaked at 9,500 cfs on May 10, 2000" in bfb["body"] and "9,000 cfs on May 10" in bfb["body"] and "<td class=\"r\">4</td>" in bfb["body"] and "May 13" in bfb["body"], "19d: flood row wrong (peak, highest daily mean, days above half, back under half): %s" % (bfb and bfb["body"][:500])
    assert b_floods({"rec": {"floods": bf}, "lake": "00062"}) is None, "19d: a lake got a floods block"
    # PLAN 19c: the hourly check, said once on /methodology/
    from lib import directory as _dir
    tj = os.path.join(tempfile.mkdtemp(), "_truth.json")
    nn = datetime.datetime(2026, 11, 13, 4, 0, tzinfo=datetime.timezone.utc)
    for st_, mm, want in (("ok", [], "229 pages compared, no number differed"), ("mismatch", ["a", "b"], "2 pages showed a number that differed"), ("skipped", [], "did not complete; the last complete check was Nov 12, 20:00 UTC")):
        json.dump({"checked_at": "2026-11-13T03:20:26+00:00", "status": st_, "compared": 229, "mismatches": mm, "last_ok_at": "2026-11-12T20:00:00+00:00"}, open(tj, "w"))
        cs = _dir.checks_section(nn, tj)
        assert want in cs and "Nov 13, 03:20 UTC" in cs and not re.search(r"\b20\d\d-\d\d-\d\d[T ]\d\d:\d\d", cs), "19c: check result wrong for %s: %s" % (st_, cs)
    assert "Last available check" in _dir.checks_section(nn + datetime.timedelta(days=3), tj.replace("_truth", "_x")) or "not available" in _dir.checks_section(nn, tj.replace("_truth", "_x")), "19c: a missing result file crashed or claimed numbers"
    json.dump({"checked_at": "2026-11-10T03:20:26+00:00", "status": "ok", "compared": 5, "mismatches": []}, open(tj, "w"))
    assert "Last available check" in _dir.checks_section(nn, tj), "19c: a 3-day-old result read as the latest"
    # PLAN 19a: float time from USGS channel velocity
    sg_ = {"rec": {"fieldmeas": {"chan": [["2024-06-01T10:00", 100.0, 50, 40, 2.0, 0, ""], ["2023-06-01T10:00", 110.0, 50, 40, 3.0, 0, ""], ["2022-06-01T10:00", 95.0, 50, 40, 2.5, 0, ""],
                                          ["2021-06-01T10:00", 900.0, 50, 40, 9.0, 0, ""], ["1990-06-01T10:00", 100.0, 50, 40, 1.0, 0, ""], ["2020-06-01T10:00", 100.0, 50, 40, 25.0, 0, ""]]}},
           "lv": 100.0, "ldate": datetime.date(2026, 11, 12)}
    bs = b3r.b_speed(sg_)
    assert bs and "about 1.4 to 2.0 mph" in bs["body"] and "on 3 visits at 95 to 110 cfs" in bs["body"] and "29 min to 44 min" in bs["body"] and "not a trip time" in bs["source"], "19a: float time wrong (a far flow, a 1990 visit or a 25 ft/s typo used?): %s" % (bs and bs["body"][:300])
    assert b3r.b_speed(dict(sg_, lv=500.0)) is None and b3r.b_speed(dict(sg_, lake="00062")) is None and b3r.b_speed(dict(sg_, osc=True)) is None and b3r.b_speed(dict(sg_, lv=None)) is None, "19a: float time shown with no visits near today's flow, on a lake, a tidal reach or with no flow"


def nid_facts():
    """NID dam facts (2026-11-10): match by name and distance, never a guess; a missing NID value is a missing row, never zero."""
    from lib import blocks3 as b3n
    nw = datetime.datetime.now(datetime.timezone.utc)
    bu = {"NIDID": "GA00824", "NAME": "Buford Dam", "OTHER_NAMES": "Lake Sidney Lanier", "IS_ASSOCIATED_STRUCTURE": "No", "LATITUDE": 34.1603, "LONGITUDE": -84.0739, "YEAR_COMPLETED": 1958,
          "FED_AGENCY_OWNERS": "US Army Corps of Engineers", "PURPOSES": "Flood Risk Reduction, Hydroelectric, Recreation", "NID_HEIGHT": 231, "SURFACE_AREA": 47182.0, "MAX_STORAGE": 2554000.0, "NORMAL_STORAGE": 1917000.0, "DATA_UPDATED": 1789473600000}
    dike = dict(bu, NAME="Buford Dam - Saddle Dike 1", OTHER_NAMES="Lake Sidney Lanier", IS_ASSOCIATED_STRUCTURE="Yes", LATITUDE=34.1627, LONGITUDE=-84.0755)
    pond = {"NIDID": "GA00597", "NAME": "Dover Dam", "IS_ASSOCIATED_STRUCTURE": "No", "LATITUDE": 34.1024, "LONGITUDE": -83.9165}
    m, why = collect.nid_match([pond, dike, bu], 34.1627, -84.0755, "lake", collect.nid_words("Lake Lanier"))
    assert m and m["id"] == "GA00824" and m["normal_af"] == 1917000.0 and m["year"] == 1958 and m["mi"] < 1, "NID: Lake Lanier did not match Buford Dam (saddle dike or pond taken instead): %s" % why
    assert collect.nid_match([pond, dike], 34.1627, -84.0755, "lake", collect.nid_words("Lake Lanier"))[0] is None, "NID: no named dam matched a saddle dike or another dam"
    twin = dict(bu, NIDID="GA99999", LATITUDE=34.1650, LONGITUDE=-84.0770)
    assert collect.nid_match([bu, twin], 34.1627, -84.0755, "lake", {"lanier"})[0] is None, "NID: two equally near dams named for the lake: one was guessed"
    assert collect.nid_match([dict(bu, LATITUDE=35.0)], 34.1627, -84.0755, "lake", {"lanier"})[0] is None, "NID: a dam outside the radius matched"
    assert collect.nid_key("x", {"river_name": "CHATTAHOOCHEE RIVER AT BUFORD DAM, NEAR BUFORD, GA"}) == ("dam", {"buford"}) and collect.nid_key("x", {"river_name": "CHATTAHOOCHEE RIVER NEAR NORCROSS, GA"}) is None, "NID: a river gauge's dam was not read from its name, or a gauge with no dam got a lookup"
    gap = collect.nid_match([dict(bu, NORMAL_STORAGE=None, SURFACE_AREA=None, YEAR_COMPLETED=0)], 34.1627, -84.0755, "lake", {"lanier"})[0]
    Gd = lambda mm: {"now": nw, "rec": {"nid": {"fetched_at": collect.now_iso(), "match": mm}}}
    if b3n.cleared("nid"):
        h = b3n.b_dam_facts(Gd(m))
        assert h and "1,917,000 acre-ft" in h["body"] and "47,182 acres" in h["body"] and "231 ft" in h["body"] and "GA00824" in h["source"] and "hazard" not in h["body"].lower(), "NID: Buford Dam facts not shown as NID states them"
        h = b3n.b_dam_facts(Gd(gap))
        assert "Normal storage" not in h["body"] and "Surface area" not in h["body"] and "Year completed" not in h["body"] and "acre-ft" in h["body"], "NID: a missing NID value showed a row (or zero) instead of being left out"
        assert b3n.b_dam_facts(Gd(None)) is None and b3n.b_dam_facts({"now": nw, "rec": {}}) is None, "NID: no match or no fetch showed a dam block"
        bare = {k: None for k in m} | {"id": "X1", "name": "Bare Dam", "mi": 2.0}
        assert b3n.b_dam_facts(Gd(bare))["empty"], "NID: a record with no facts was drawn as a full card"
        old = {"now": nw, "rec": {"nid": {"fetched_at": (nw - datetime.timedelta(days=80)).isoformat(), "match": m}}}
        assert b3n.b_dam_facts(old)["amber"] and not b3n.b_dam_facts(Gd(m))["amber"], "NID: an 80-day-old record was not marked old"


if __name__ == "__main__":
    run()
    from tools.outreach_guard import selftest as outreach_selftest  # owner 2026-11-13: nobody is emailed twice
    outreach_selftest()
    # PLAN 29 king tides: NOAA's flood level is on the station datum, predictions on MLLW; a short reply, no level, past tides, a river page
    hj_, cg_ = collect.http_json, collect.coops_get
    yr_ = [{"t": "2027-%02d-01 12:00" % (1 + i % 12), "v": "3.0", "type": "H"} for i in range(700)] + [{"t": "2027-01-23 16:03", "v": "4.6", "type": "H"}, {"t": "2027-01-23 22:00", "v": "9.9", "type": "L"}]
    try:
        collect.coops_get = lambda st, q: yr_
        collect.http_json = lambda u, *a, **k: {"nos_minor": 6.24, "nws_minor": 7.19} if "floodlevels" in u else {"datums": [{"name": "STND", "value": 0.0}, {"name": "MLLW", "value": 1.73}]}
        ft_ = collect.fetch_floodtide("8726724")
        assert ft_["level"] == 4.51 and ft_["who"] == "nos" and ft_["over"] == [("2027-01-23T16:03:00+00:00", 4.6)],"king tide: flood level not moved from station datum to MLLW, or a low tide counted"
        collect.http_json = lambda u, *a, **k: {"nos_minor": None, "nws_minor": None}
        assert collect.fetch_floodtide("x")["level"] is None and collect.fetch_floodtide("x")["top"], "king tide: a station with no flood level lost its highest tides"
        collect.coops_get = lambda st, q: yr_[:40]
        try:
            collect.fetch_floodtide("x")
            raise AssertionError("king tide: a reply cut short could say 'none in 12 months'")
        except RuntimeError:
            pass
    finally:
        collect.http_json, collect.coops_get = hj_, cg_
    from lib import blocks3
    now_ = datetime.datetime(2026, 11, 13, tzinfo=datetime.timezone.utc)
    kt_ = lambda f, **k: blocks3.b_kingtide(dict({"coast": True, "site": "8726724", "zone": zoneinfo.ZoneInfo("America/New_York"), "now": now_, "rec": {"floodtide": f}}, **k))
    base_ = {"fetched_at": "2026-11-12T00:00:00+00:00", "who": "nos", "level": 4.51, "top": [["2027-08-02T15:50:00+00:00", 3.7], ["2026-11-01T15:00:00+00:00", 9.0]], "over": []}
    b_ = kt_(base_)["body"]
    assert "3.7 ft" in b_ and "0.8 ft below NOAA" in b_ and "9.0" not in b_, "king tide: gap to the flood level wrong, or a past tide shown as coming"
    assert "reach" in kt_(dict(base_, over=[["2027-01-23T16:03:00+00:00", 4.6]]))["body"] and "1 predicted high tide" in kt_(dict(base_, over=[["2027-01-23T16:03:00+00:00", 4.6]]))["body"], "king tide: a tide at the flood level not named"
    assert "publishes no flood level" in kt_(dict(base_, level=None))["body"], "king tide: no published level read as no flooding"
    assert "Unknown" in kt_({})["body"] and "Unknown" in kt_(dict(base_, top=[["2026-11-01T15:00:00+00:00", 9.0]]))["body"], "king tide: missing or all-past data shown as a coming tide"
    assert kt_(base_, coast=False) is None, "king tide block on a river page"
    assert not re.search(r"\bwill flood\b|\bsafe\b", b_), "king tide: a verdict in the text"
    # PLAN 31 surf zone forecast: NWS's words attributed; none issued is said (never 'Low'); old is amber, older is Unknown; NWS times parsed
    assert blocks3.nws_issued("11/13/2026", "500 PM EST") == datetime.datetime(2026, 11, 13, 22, tzinfo=datetime.timezone.utc) and blocks3.nws_issued("11/13/2026", "1205 AM PDT").hour == 0 and blocks3.nws_issued("N/A", "N/A") is None and blocks3.nws_issued("11/13/2026", "500 PM XYZ") is None, "surf: NWS issue time misread"
    hj_ = collect.http_json
    try:
        collect.http_json = lambda u, *a, **k: {"features": [{"attributes": {"beachname": "N/A", "rip": None}}]}
        assert collect.fetch_surf(37.8, -122.4)["rows"] == [], "surf: NWS's N/A placeholder kept as a forecast"
        collect.http_json = lambda u, *a, **k: {"error": {"code": 500}}
        try:
            collect.fetch_surf(37.8, -122.4)
            raise AssertionError("surf: an NWS error reply was stored as 'no forecast issued'")
        except RuntimeError:
            pass
    finally:
        collect.http_json = hj_
    sr_ = {"fetched_at": "2026-11-13T23:00:00+00:00", "rows": [{"beachname": "Duval Beaches", "sitename": "WFO Jacksonville", "productdat": "11/13/2026", "producttim": "500 PM EST", "period": "Saturday", "rip": "High", "surf": "3 to 4 feet.", "srfprod": "https://forecast.weather.gov/product.php?site=jax&product=srf&issuedby=jax"}]}
    sf_ = lambda s, h=2, **k: blocks3.b_surf(dict({"coast": True, "zone": zoneinfo.ZoneInfo("America/New_York"), "now": datetime.datetime(2026, 11, 13, 22, tzinfo=datetime.timezone.utc) + datetime.timedelta(hours=h), "rec": {"surf": s}}, **k))
    b_ = sf_(sr_)
    assert "High" in b_["body"] and "3 to 4 feet" in b_["body"] and "Duval Beaches" in b_["body"] and "National Weather Service" in b_["source"] and not b_["amber"], "surf: NWS risk, surf or attribution missing"
    assert sf_(sr_, 40)["amber"] and "Unknown" in sf_(sr_, 80)["body"] and "Unknown" in sf_(None)["body"], "surf: an old forecast shown as current"
    em_ = sf_(dict(sr_, rows=[]))
    assert em_["empty"] and "issues no surf zone forecast" in em_["body"] and "Low" not in em_["body"], "surf: no forecast read as a low risk"
    assert sf_(sr_, coast=False) is None, "surf block on a river page"
    # PLAN 32 moon phases on river and lake pages: USNO UT shown in local time, past phases dropped, none ahead = Unknown, coasts keep b_moon
    mp_ = {"fetched_at": "2026-11-13T00:00:00+00:00", "phases": [["New Moon", "2026-11-09T07:02:00+00:00"], ["First Quarter", "2026-11-17T11:48:00+00:00"], ["Full Moon", "2026-11-24T14:53:00+00:00"], ["Last Quarter", "2026-12-01T06:08:00+00:00"], ["New Moon", "2026-12-09T00:52:00+00:00"]]}
    mf_ = lambda m, **k: blocks3.b_moonphase(dict({"zone": zoneinfo.ZoneInfo("America/Denver"), "now": now_, "rec": {"moonphase": m}}, **k))
    b_ = mf_(mp_)["body"]
    assert "Next full moon: Nov 24, 7:53 AM" in b_ or "Next full moon: Nov 24, 7:53 AM" in b_.replace(" ", " "), "moon: UT full moon not shown in local time: " + b_[:200]
    assert "Nov 9" not in b_ and "Nov 9," not in b_.replace(" ", " "), "moon: a past phase shown as coming"
    assert "Unknown" in mf_({})["body"] and "Unknown" in mf_(dict(mp_, phases=mp_["phases"][:1]))["body"], "moon: missing or all-past phases shown"
    assert mf_(mp_, coast=True) is None and not re.search(r"\b(bite|best time|good fishing)\b", b_, re.I), "moon: on a coast page twice, or a fishing verdict"
    pr_, hr_ = list(collect._PHASES), collect.http_raw
    try:
        collect._PHASES.clear()
        collect.http_raw = lambda u, *a, **k: json.dumps({"phasedata": [{"phase": "Full Moon", "year": 2026, "month": 11, "day": 24, "time": "14:53"}]}).encode()
        try:
            collect.fetch_moonphase()
            raise AssertionError("moon: a short USNO reply was stored")
        except RuntimeError:
            assert collect._PHASES == [], "moon: a short reply stayed in the shared list"
    finally:
        collect._PHASES[:], collect.http_raw = pr_, hr_
    # PLAN 30 red tide (HABSOS): highest count named with its site and date; all zero said as no cells found; no sample = 'no sample', never 'no red tide'
    hj_ = collect.http_json
    try:
        collect.http_json = lambda u, *a, **k: {"features": [{"attributes": {"DESCRIPTION": "Siesta Beach", "SAMPLE_DATE": 1794240000000, "CATEGORY": "very low", "CELLCOUNT": 333.0, "CELLCOUNT_UNIT": "cells/L", "LATITUDE": 27.265, "LONGITUDE": -82.553}},
                                                                {"attributes": {"DESCRIPTION": "X", "SAMPLE_DATE": None, "CATEGORY": "", "CELLCOUNT": 5.0, "CELLCOUNT_UNIT": "cells/L", "LATITUDE": 27.3, "LONGITUDE": -82.5}},
                                                                {"attributes": {"DESCRIPTION": "Y", "SAMPLE_DATE": 1794240000000, "CATEGORY": "", "CELLCOUNT": None, "CELLCOUNT_UNIT": "cells/L", "LATITUDE": 27.3, "LONGITUDE": -82.5}}]}
        rr_ = collect.fetch_redtide(27.3317, -82.545)
        assert [x["site"] for x in rr_["rows"]] == ["Siesta Beach"] and rr_["rows"][0]["date"] == "2026-11-09" and 7 < rr_["rows"][0]["km"] < 8, "red tide: a sample with no date or count kept, or date/distance wrong"
        collect.http_json = lambda u, *a, **k: {"error": {"code": 400}}
        try:
            collect.fetch_redtide(27.3, -82.5)
            raise AssertionError("red tide: an error reply stored as no samples")
        except RuntimeError:
            pass
    finally:
        collect.http_json = hj_
    rt_ = lambda r, st="FL": blocks3.b_redtide({"coast": True, "row": {"state": st}, "zone": zoneinfo.ZoneInfo("America/New_York"), "rec": {"redtide": r}})
    rd_ = {"fetched_at": "2026-11-13T12:00:00+00:00", "rows": [{"site": "Siesta Beach", "date": "2026-11-09", "count": 0.0, "cat": "not observed", "km": 2.0}, {"site": "North Lido Beach", "date": "2026-11-09", "count": 333.0, "cat": "very low", "km": 1.6}]}
    b_ = rt_(rd_)["body"]
    assert "333 cells per liter (very low) at North Lido Beach" in b_ and "Siesta Beach" in b_, "red tide: highest count, its category or a site missing"
    assert "found Karenia brevis" in rt_(dict(rd_, rows=[dict(rd_["rows"][0])]))["body"] and "None of the 1" in rt_(dict(rd_, rows=[dict(rd_["rows"][0])]))["body"], "red tide: all-zero samples not said"
    e_ = rt_(dict(rd_, rows=[]))
    assert e_["empty"] and "No sample is not the same as no red tide" in e_["body"], "red tide: no sample read as no red tide"
    assert "Unknown" in rt_(None)["body"] and rt_(rd_, "CA") is None, "red tide: missing data shown, or the block on a non-Gulf coast"
    # PLAN 33a fish species (GBIF + ITIS): CC BY-NC never asked; ITIS down = scientific name only and asked again; 'recorded within', never 'in this river'
    hj_, nm_, ds_ = collect.http_json, dict(collect._GBIF_NAMES), dict(collect._GBIF_SETS)
    asked_ = []
    def fake_(u, *a, **k):
        asked_.append(u)
        if "occurrence/search" in u:
            return {"count": 30, "facets": [{"field": "SPECIES_KEY", "counts": [{"name": "1", "count": 20}, {"name": "2", "count": 10}]}, {"field": "DATASET_KEY", "counts": [{"name": "d1", "count": 25}]}]}
        if "/species/1" in u:
            return {"canonicalName": "Oncorhynchus nerka"}
        if "/species/2" in u:
            return {"canonicalName": "Salmo trutta"}
        if "/dataset/" in u:
            return {"title": "USGS Nonindigenous Aquatic Species database"}
        if "searchByScientificName" in u and "nerka" in u:
            return {"scientificNames": [{"tsn": "161979", "combinedName": "Oncorhynchus nerka"}]}
        if "getCommonNamesFromTSN" in u:
            return {"commonNames": [{"commonName": n, "language": "English"} for n in ("blueback salmon", "kokanee", "red salmon", "sockeye salmon")]}
        raise OSError("ITIS down")
    try:
        collect.http_json = fake_
        collect._GBIF_NAMES.clear(); collect._GBIF_SETS.clear()
        fi_ = collect.fetch_fish(39.36, -106.82)
        assert "CC_BY_NC" not in asked_[0] and "CC0_1_0" in asked_[0] and "CC_BY_4_0" in asked_[0], "fish: a non-commercial licence asked for, or an open one left out"
        assert fi_["rows"] == [["Oncorhynchus nerka", "blueback salmon, kokanee, red salmon", 20], ["Salmo trutta", None, 10]] and fi_["datasets"] == [["USGS Nonindigenous Aquatic Species database", 25]], "fish: names, counts or citation wrong"
        assert 2 not in collect._GBIF_NAMES and "2" not in collect._GBIF_NAMES, "fish: an ITIS failure was remembered for the whole run"
    finally:
        collect.http_json = hj_
        collect._GBIF_NAMES.clear(); collect._GBIF_NAMES.update(nm_); collect._GBIF_SETS.clear(); collect._GBIF_SETS.update(ds_)
    fb_ = lambda f: blocks3.b_fish({"zone": zoneinfo.ZoneInfo("America/Denver"), "rec": {"fish": f}})
    b_ = fb_(dict(fi_, fetched_at="2026-11-13T00:00:00+00:00"))["body"]
    assert "2 fish species have records within 10 km since 2000" in b_ and "blueback salmon" in b_ and "Salmo trutta" in b_ and "No common name listed" in b_ and "USGS Nonindigenous" in b_, "fish: lead, names or sources missing"
    assert not re.search(r"in this (river|lake)|\bbite\b|good fishing", b_, re.I), "fish: records claimed for this water, or a verdict"
    e_ = fb_(dict(fi_, fetched_at="2026-11-13T00:00:00+00:00", rows=[], species=0))
    assert e_["empty"] and "No record is not the same as no fish" in e_["body"] and "Unknown" in fb_(None)["body"], "fish: no record read as no fish, or missing data shown"
    # PLAN 35 solunar inputs on coasts: USNO's moon-overhead time shown in station time with the disputed-theory note; an older cache without it shows neither
    un_ = {"fetched_at": "2026-11-13T10:00:00+00:00", "days": [{"date": "2026-11-13", "moon": [["Rise", "2026-11-13T16:28:00+00:00"], ["Upper Transit", "2026-11-13T21:42:00+00:00"]], "closest": ["New Moon", "2026-11-09T07:02:00+00:00"]},
                                                                {"date": "2026-11-14", "moon": [], "closest": ["New Moon", "2026-11-09T07:02:00+00:00"]}]}
    mo_ = lambda u: blocks3.b_moon({"coast": True, "zone": zoneinfo.ZoneInfo("America/New_York"), "now": datetime.datetime(2026, 11, 13, 18, tzinfo=datetime.timezone.utc), "rec": {"usno": u}})["body"].replace(" ", " ")
    assert "Moon overhead today" in mo_(un_) and "4:42 PM" in mo_(un_) and "disputed" in mo_(un_), "solunar: moon overhead time missing, wrong zone, or the theory not called disputed"
    old_ = {**un_, "days": [dict(un_["days"][0], moon=[["Rise", "2026-11-13T16:28:00+00:00"]]), un_["days"][1]]}
    assert "overhead" not in mo_(old_) and "Solunar" not in mo_(old_), "solunar: a cache without the overhead time said 'none' or kept the note"
    # PLAN 36 Massachusetts stocking: points in the box, events by code (POST), species decoded from the layer's own list, a water beyond the radius dropped
    import io as io_
    gt_, uo_, sp_ = collect.get_text, collect.urllib.request.urlopen, dict(collect._MA_SP)
    try:
        collect._MA_SP.clear()
        collect.get_text = lambda u, *a, **k: json.dumps({"features": [{"attributes": {"STK_WB_ID": "1-1"}, "geometry": {"x": -72.6, "y": 42.26}}, {"attributes": {"STK_WB_ID": "2-2"}, "geometry": {"x": -70.0, "y": 42.26}}]}) if "Joined_View" in u else json.dumps({"fields": [{"name": "Species", "domain": {"codedValues": [{"code": "RT", "name": "Rainbow Trout"}]}}]})
        collect.urllib.request.urlopen = lambda req, *a, **k: io_.BytesIO(json.dumps({"features": [{"attributes": {"Species": "RT", "Stocked_Date": 1791928800000, "Waterbody": "Loon Pond - Springfield", "Water_Town_Code": "1-1"}},
                                                                                                {"attributes": {"Species": "ZZ", "Stocked_Date": 1791928800000, "Waterbody": "Far Pond", "Water_Town_Code": "2-2"}}]}).encode())
        ma_ = collect.fetch_stocking_ma(42.25, -72.6, 35)
        assert [(r["species"], r["water"], r["num"]) for r in ma_] == [("Rainbow Trout", "Loon Pond - Springfield", None)], "MA stocking: code not decoded, a far water kept, or a count invented"
    finally:
        collect.get_text, collect.urllib.request.urlopen = gt_, uo_
        collect._MA_SP.clear(); collect._MA_SP.update(sp_)
    # PLAN 36 stocking edge cases: a busy pond season never pushes the gauge's own river out; lake pages match their own lake; whole words only
    pond_ = [{"species": "Rainbow Trout", "date": "2026-10-%02d" % (1 + i % 28), "num": None, "water": "Pond %d" % i, "size": None, "mi": 20.0 + i} for i in range(40)]
    own_ = {"species": "Brown Trout", "date": "2026-09-01", "num": 500, "water": "Swift River - Belchertown", "size": None, "mi": 2.0}
    kept_ = collect.stock_keep(pond_ + [own_, dict(own_, date="2026-05-01")])
    assert own_ in kept_ and sum(1 for r in kept_ if r["water"] == own_["water"]) == 1 and kept_ == sorted(kept_, key=lambda r: r["date"], reverse=True), "stocking: the own river was pushed out, kept twice, or not newest first"
    assert len(collect.stock_keep(pond_ * 3, 25)) == 25, "stocking: the cap did not hold"
    assert blocks3._on_lake("Lake Saltonstall - Haverhill", "Lake Saltonstall") and not blocks3._on_lake("Meadow Pond", "Lake Mead") and not blocks3._on_lake("Saltonstall Brook", "Lake Saltonstall"), "stocking: lake match wrong"
    assert blocks3._on_river("Swift River - Belchertown", "Swift River") and not blocks3._on_river("Swiftwater Brook", "Swift River") and not blocks3._on_river("Swift River Pond", "Swift River"), "stocking: river match wrong"
    sk_ = lambda lake, river: blocks3.b_stocking({"lake": lake, "river": river, "zone": datetime.timezone.utc, "now": datetime.datetime(2026, 11, 13, tzinfo=datetime.timezone.utc),
                                                  "rec": {"stocking": {"fetched_at": "2026-11-13T00:00:00+00:00", "source": "S", "credit": "C", "miles": 35, "rows": [own_, {"species": "Rainbow Trout", "date": "2026-10-13", "num": None, "water": "Lake Saltonstall - Haverhill", "size": None, "mi": 3.0}]}}})
    assert "Lake Saltonstall" in sk_("00062", "Lake Saltonstall")["body"] and "Swift River" not in sk_("00062", "Lake Saltonstall")["body"] and "Swift River" in sk_(None, "Swift River")["body"], "stocking: a lake page missed its lake or showed a river's release"
    # PLAN 36 Georgia: a stream line's distance is its nearest vertex; the fixed species comes from the source entry; no count invented
    gt_ = collect.get_text
    try:
        collect.get_text = lambda u, *a, **k: json.dumps({"features": [{"attributes": {"Name": "Toccoa River (F) DH", "LastStock": 1793725200000}, "geometry": {"paths": [[[-84.0, 34.9], [-84.2, 34.61]]]}}]})
        ga_ = collect.fetch_stocking(34.6, -84.2)
        assert ga_["rows"][0]["species"] == "Trout" and ga_["rows"][0]["num"] is None and ga_["rows"][0]["mi"] < 1 and ga_["rows"][0]["date"] == "2026-11-03", "Georgia stocking: line distance, fixed species, count or date wrong"
    finally:
        collect.get_text = gt_
    # PLAN 37a NH and the MA/NH border: both states' releases kept, credits joined; NH codes decoded by the report key, water name readable
    ma0_, nh0_ = collect.fetch_stocking_ma, collect.fetch_stocking_nh
    try:
        collect.fetch_stocking_ma = lambda la, lo, mi: [{"species": "Rainbow Trout", "date": "2026-10-13", "num": None, "water": "Long Sought-for Pond - Westford", "size": None, "mi": 9.0}]
        collect.fetch_stocking_nh = lambda la, lo, mi: [{"species": "Brook Trout", "date": "2026-11-06", "num": 1000, "water": "Tewksbury Pond - Grafton", "size": None, "mi": 5.0}]
        bd_ = collect.fetch_stocking(42.8, -71.4)
        assert len(bd_["rows"]) == 2 and "MassWildlife" in bd_["source"] and "NH Fish and Game" in bd_["source"] and "; " in bd_["credit"], "border stocking: one state's releases or credit lost"
        collect.fetch_stocking_ma = lambda la, lo, mi: []
        assert collect.fetch_stocking(42.8, -71.4)["source"] == "NH Fish and Game fish stocking records", "border stocking: an empty state named as a source"
    finally:
        collect.fetch_stocking_ma, collect.fetch_stocking_nh = ma0_, nh0_
    assert collect.NH_SPECIES["EBT"] == "Brook Trout" and collect.NH_SPECIES["LLS"] == "Landlocked Salmon", "NH species key changed"
    # PLAN 37c Virginia parse: tags in the water name and county dropped, two species split, 'No Stockings Today' and unparsable dates skipped
    va_html_ = ("<tr><th>Date</th><th>County</th><th>Waterbody</th><th>Category</th><th>Species Stocked</th></tr>"
                "<tr><td>November 13, 2026</td><td>Bedford County</td><td>Liberty Lake <em>[Heritage Day Water]</em></td><td>A</td><td><p>Rainbow Trout</p><p>Brown Trout</p></td></tr>"
                "<tr><td>November 12, 2026</td><td>Statewide</td><td>No Stockings Today</td><td></td><td></td></tr><tr><td>TBD</td><td>Giles County</td><td>Wolf Creek</td><td>A</td><td>Rainbow Trout</td></tr>")
    assert collect.va_schedule(va_html_) == [("2026-11-13", "Bedford", "Liberty Lake", ["Rainbow Trout", "Brown Trout"])], "Virginia schedule parse wrong: %r" % collect.va_schedule(va_html_)
    # PLAN 37 merge: a refresh keeps earlier releases of the same source inside 550 days; another source replaces; nothing new keeps the old record
    old_ = {"source": "S", "rows": [{"species": "Trout", "date": "2026-10-01", "num": None, "water": "A Creek", "size": None, "mi": 1.0}, {"species": "Trout", "date": "2020-01-01", "num": None, "water": "Old Creek", "size": None, "mi": 1.0}]}
    nw_ = {"source": "S", "rows": [{"species": "Trout", "date": "2026-11-10", "num": None, "water": "B Creek", "size": None, "mi": 2.0}]}
    mg_ = collect.stock_merge(nw_, old_)
    assert [r["water"] for r in mg_["rows"]] == ["B Creek", "A Creek"], "stocking merge lost a recent release or kept a 2020 one"
    assert len(collect.stock_merge(dict(nw_, source="S and T"), old_)["rows"]) == 2, "stocking merge: a border page lost its releases when a second state joined"
    assert collect.stock_merge(dict(nw_, source="T"), old_)["rows"] == nw_["rows"] and collect.stock_merge(None, old_) is old_ and collect.stock_merge(None, None) is None, "stocking merge mixed sources or lost the old record"
    # 2026-11-13: the fish source line said 'licensed' (check.py BANNED) and the cloud refresh stopped; every new block's text now meets the banned list here first
    import check as ck_
    outs_ = [fb_(dict(fi_, fetched_at="2026-11-13T00:00:00+00:00")), sf_(sr_), rt_(rd_), kt_(base_), mf_(mp_), sk_(None, "Swift River")]
    for o_ in outs_:
        for pat_ in ck_.BANNED:
            assert not re.search(pat_, o_["body"] + " " + o_["source"]), "banned text in block %s: %s" % (o_["id"], pat_)
    print("selftest OK")
