"""Fixtures for paths only a rare real event reaches: an ice flag, a frozen feed, an outage over a live page, a lost cache in a new year. Run by check.py --selftest."""
import datetime, email.utils, json, os, sys, tempfile, types
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import collect
from lib import world
from lib import wx as wx_mod


def run():
    ago = lambda **k: datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(**k)
    new = {"parameter_code": "00060", "time": "t1", "value": "11000", "qualifier": None}
    rows, add, fixed = collect.merge_rows([dict(new, value="10500"), dict(new, time="t0", value="9")], [new, dict(new, time="t2")])
    assert {r["time"]: r["value"] for r in rows}["t1"] == "11000" and (add, fixed) == (1, 1), "a USGS correction to a reading we already had was dropped"
    assert collect.merge_rows([new], [dict(new)])[1:] == (0, 0), "an unchanged reading counted as a correction"
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

    far = dict(base, name="F", lat=60.0, then=1.0)
    near = dict(base, name="N", lat=50.3, then=1.0)
    got = world.along({"flat": True, "feed": "eccc", "slug": "x"}, base, [base, far, near])
    assert [g[1] for g in got] == ["N"] and got[0][0] == "Nearby", "a far gauge read as nearby"


    real = world.page, world.missing, world.shingles, world.alike, world.os.path.exists, world.GATE
    p = {"slug": "x", "gauge_pages": ["01AB"], "river": "X"}
    try:
        world.page, world.missing, world.shingles, world.alike, world.GATE = lambda *a, **k: ("/u/", "<html>"), lambda h, r: ["alerts"], lambda h: set(), lambda a, b: True, True
        world.os.path.exists = lambda q: False
        world.missing, world.GAPS = lambda h, r: [], {}
        world.choose([(p, {"rows": [base]})], None)
        assert world.GAPS.get("01AB") == ["flood warning note"], "a world page without the flood line passed"
        world.missing = lambda h, r: ["alerts"]
        assert world.choose([(p, {"rows": [base]})], None)["x"] == set(), "a new gauge with a gap was not held"
        world.os.path.exists = lambda q: True
        assert world.choose([(p, {"rows": [base]})], None)["x"] == {"01AB"}, "an outage pulled a live page"
    finally:
        world.page, world.missing, world.shingles, world.alike, world.os.path.exists, world.GATE = real

    england(ago)

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
    pages = [{"slug": "england", "feed": "ea", "gauge_pages": []}, {"slug": "rhine", "gauge_pages": ["KAUB"]}]
    unproven = dict(world.PROVED, ea={"reading": "seen on live data 2026-11-03"})
    assert world.listing(pages) == ["pegelonline"] and not world.proof_faults(world.listing(pages), unproven), "a country with no gauge page failed the proof gate"
    assert world.proof_faults(world.listing([dict(pages[0], gauge_pages=["4009"])]), unproven), "a country with a gauge page passed without every proof"
    keep = world.PROVED
    try:
        world.PROVED = unproven
        assert world.room("ea", pages) == 0, "a country without every proof had room to add gauges"
        world.PROVED = dict(keep, ea={k: "seen on live data, fixture" for k in world.PROOFS})
        assert world.room("ea", pages) == world.FROZEN["ea"] and world.room("ea", [dict(pages[0], gauge_pages=list(range(25)))]) == 0, "FROZEN did not cap a country with blocks not wired"
    finally:
        world.PROVED = keep


if __name__ == "__main__":
    run()
    print("selftest OK")
