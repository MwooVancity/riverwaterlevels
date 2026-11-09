"""Fixtures for paths only a rare real event reaches: an ice flag, a frozen feed, an outage over a live page, a lost cache in a new year. Run by check.py --selftest."""
import datetime, email.utils, json, os, sys, tempfile, types, zoneinfo
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import collect
from lib import world
from lib import wx as wx_mod


def run():
    ago = lambda **k: datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(**k)
    new = {"parameter_code": "00060", "time": "t1", "value": "11000", "qualifier": None}
    from lib import directory
    from lib import core as core_
    iso = lambda d: d.isoformat()
    fut = core_.series({"usgs": {"rows": [dict(new, time=iso(ago(minutes=30)), unit_of_measure="ft^3/s", value="900"), dict(new, time=iso(ago(minutes=-120)), unit_of_measure="ft^3/s", value="5000")]}}, "00060")
    assert [v for _, v, _ in fut] == [900.0], "a US reading stamped 2 h in the future was kept as the latest (gate audit 0a)"
    from lib import render  # noqa: F401 (lib.page imports through render)
    from lib import blocks2 as b2_
    t0_ = datetime.datetime(2026, 11, 9, 15, tzinfo=datetime.timezone.utc)
    fl_ = [(t0_ - datetime.timedelta(minutes=15 * k), 1160.0 if k == 0 else (1210.0 if k >= 96 else 1200.0), {}) for k in range(100, -1, -1)]
    rb_ = str(b2_.b_rate({"fl": fl_, "sg": [], "zone": zoneinfo.ZoneInfo("America/Denver"), "offline": False, "osc": False, "site": "x"}))
    assert "Last 1 to 12 h" in rb_ and rb_.count("Last 1 h") == 0 and "Last 24 h" in rb_ and "Full table" not in rb_, "rate of change: identical 1-12 h windows were printed four times, or the duplicate full table is back (fresh review 2026-11-09, Madison)"
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
    square = [[1, [0, 2, 0, 2], [[[0, 0], [0, 2], [2, 2], [2, 0], [0, 0]]]], [3, [0.5, 1, 0.5, 1], [[[0.5, 0.5], [0.5, 1], [1, 1], [1, 0.5], [0.5, 0.5]]]]]
    assert wx.drought_at(0.7, 0.7, square) == 3 and wx.drought_at(1.5, 1.5, square) == 1 and wx.drought_at(3, 3, square) is None, "drought class wrong"
    assert world.metric("<td>2.3 mi</td>") == "<td>3.7 km</td>", "a decimal distance broke"
    with tempfile.TemporaryDirectory() as d:
        for i in range(20):
            os.makedirs(os.path.join(d, "river", str(i)))
            open(os.path.join(d, "river", str(i), "index.html"), "w").write('<div class="hero hero2"><section data-g="now" class="card blk" data-f="x" id="%s"></section>' % ("a" if i < 5 else "b"))
        got = coverage.scan(d, {"best": {"US": {"a": 0.9}}})
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


if __name__ == "__main__":
    run()
    print("selftest OK")
