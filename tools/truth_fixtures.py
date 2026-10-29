"""Fixtures for the truth contracts that real data once broke (shadow run 40936605236, 2026-10-29). Usage: python -I tools/truth_fixtures.py (gates.py runs it).
Each case bends one live gauge's cache into the shape that failed and asserts the page's answer; any live gauge with a USGS stage in ft and an NWS point will do."""
import os, sys, json, copy, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lib import render  # noqa: E402
from lib.pages import load_effective  # noqa: E402

rows, _ = load_effective()
now = datetime.datetime.now(datetime.timezone.utc)
base = None
for f in sorted(os.listdir(os.path.join(ROOT, "cache"))):
    if f.endswith(".json") and not f.startswith("_") and f[:-5] in rows:
        rec = json.load(open(os.path.join(ROOT, "cache", f)))
        try:
            G = render.ctx(f[:-5], rows[f[:-5]], rec, now)
        except render.CriticalFail:
            continue
        if G["sg"] and not G["osc"] and G["lv"] > 0 and (rec.get("nwps") or {}).get("lid"):
            base = (f[:-5], rec)
            break
assert base, "no live gauge to bend"


def ctx(mut):
    r = copy.deepcopy(base[1])
    mut(r)
    return render.ctx(base[0], rows[base[0]], r, now)


def stage(G):
    return G["sg"][-1][1]


def set_nwps(r, imp, obs=None, cats=None):
    n = r.setdefault("nwps", {})
    n.update({"impacts": imp, "stage_units": "ft", "categories": cats or {}, "forecast": None})
    n["obs_stage"] = obs


# 1. rain scenarios and "No known impacts" are not impact stages: the stage above them owes no quote (02138500, 02146110, 03510577, 05211000, 02160326)
def m1(r):
    set_nwps(r, [{"stage": -50, "statement": "1.5 INCH AVERAGE RAINFALL IN 2 HOURS WILL CAUSE A 1.5 FT RISE ON THE HEADWATERS."}, {"stage": -40, "statement": "No known impacts at this location."}, {"stage": 9999, "statement": "Bankfull stage as the river flows into the lake."}])
G = ctx(m1)
assert render.impact_list(G) == {9999: ["Bankfull stage as the river flows into the lake."]}, render.impact_list(G)

# 2. the NWS reads elevation but publishes gage-height impacts: no "reached", no "Next", one plain line (05301000)
t_ = ctx(lambda r: None)["sg"][-1][0].isoformat()


def m2(r):
    s = r["_s"]
    set_nwps(r, [{"stage": s + 18.8, "statement": "Emergency spillway level (also roadway level)"}], {"t": t_, "v": s + 900})


def with_s(mut):
    r0 = copy.deepcopy(base[1])
    r0["_s"] = stage(ctx(lambda r: None))
    return ctx(lambda r: (r.update({"_s": r0["_s"]}), mut(r)))


G2 = with_s(m2)
assert render.scale_clash(G2) is not None and render.impact_cur(G2, render.datum_gap(G2)) is None
b = render._forecast.b_impacts(G2)["body"]
assert "reached at" not in b and "Next impact" not in b and "different scale" in b, b[:300]
assert render.next_impact(G2) == ""

# 3. a reading above a real impact is quoted as reached (the highest one reached leads the cards)
def m3(r):
    s = r["_s"]
    set_nwps(r, [{"stage": s - 1, "statement": "Water is over the low lying river bank and onto the trail."}, {"stage": s + 3, "statement": "Water reaches the first houses along the road."}])


G3 = with_s(m3)
assert "reached at the latest reading" in render._forecast.b_impacts(G3)["body"]

# 4. a negative flow at a gauge that is not tidal shows as reported with the one plain line (02407000, 04157005)
def m4(r):
    for x in r["usgs"]["rows"]:
        if x["parameter_code"] == "00060":
            last = x
    last["value"] = "-300"


G4 = ctx(m4)
assert G4["lv"] < 0 and render.NEG_FLOW_NOTE in render.hero(G4, None)

# 5. a forecast inside the tolerance of the reading is level, in cfs as well as ft (03095500: 10.0 against 10.2 cfs)
assert render.fc_cmp(10.0, 10.2, "cfs") == "level" and render.fc_cmp(9.0, 10.2, "cfs") == "below"
print("truth fixtures: ok")
