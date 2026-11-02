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

    far = dict(base, name="F", lat=60.0, then=1.0)
    near = dict(base, name="N", lat=50.3, then=1.0)
    got = world.along({"flat": True, "feed": "eccc", "slug": "x"}, base, [base, far, near])
    assert [g[1] for g in got] == ["N"] and got[0][0] == "Nearby", "a far gauge read as nearby"

    real = world.page, world.missing, world.shingles, world.alike, world.os.path.exists, world.GATE
    p = {"slug": "x", "gauge_pages": ["01AB"], "river": "X"}
    try:
        world.page, world.missing, world.shingles, world.alike, world.GATE = lambda *a, **k: ("/u/", "<html>"), lambda h, r: ["alerts"], lambda h: set(), lambda a, b: True, True
        world.os.path.exists = lambda q: False
        assert world.choose([(p, {"rows": [base]})], None)["x"] == set(), "a new gauge with a gap was not held"
        world.os.path.exists = lambda q: True
        assert world.choose([(p, {"rows": [base]})], None)["x"] == {"01AB"}, "an outage pulled a live page"
    finally:
        world.page, world.missing, world.shingles, world.alike, world.os.path.exists, world.GATE = real

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


if __name__ == "__main__":
    run()
    print("selftest OK")
