"""Gauge-type matrix: the page must render, and must stay honest, when a gauge lacks data the 25 pilot gauges happen to have.
Usage: python -I truth_types.py     (offline; reads cache/, no network; run by refresh.py before every publish)
Each variant takes a real cached gauge and removes or distorts one thing a real gauge type lacks (no statistics, no stage, no NWS point, no optional source, a tidal swing with negative flow, a flat sensor, a dead sensor).
A variant must not raise, must not print None / NaN / undefined, and a dead sensor must fail loudly (CriticalFail) instead of rendering old numbers as current.
Exit 1 on any failure."""
import os, sys, re, json, copy, math, datetime
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from lib import render  # noqa: E402
from lib.pages import load_effective  # noqa: E402

SITE = "03192000"  # Gauley above Belva: stats, stage, NWS point, forecast: the fullest cache we have
OPTIONAL = ("nws", "nwps", "rain", "nwm", "land", "wtemp", "snotel", "cpc", "multiyear", "usdm", "attains", "rating", "atlas14", "openfema", "storms", "echo", "acis", "nid", "fema_zone", "rise", "streamcat", "fieldmeas", "cpc610", "floodfreq", "wpc", "record", "peaks", "related")
BAD = re.compile(r"\bNone\b|\bNaN\b|\bundefined\b|\binf\b|-999")
bad = []


def flow_rows(rec):
    return sorted([r for r in rec["usgs"]["rows"] if r["parameter_code"] == "00060"], key=lambda r: r["time"])


def v_no_stats(r): r["stats"] = None
def v_no_stage(r): r["usgs"]["rows"] = [x for x in r["usgs"]["rows"] if x["parameter_code"] != "00065"]
def v_no_optional(r):
    for k in OPTIONAL:
        r.pop(k, None)


def v_no_alerts_source(r):
    r["nws"] = {k: v for k, v in (r.get("nws") or {}).items() if k != "alerts"}


def v_tidal(r):  # a tidal swing: flow goes negative twice a day
    rows = flow_rows(r)
    for i, x in enumerate(rows):
        x["value"] = "%.0f" % (4000 * math.sin(i / 8.0) + 500)


def v_flat(r):
    for x in flow_rows(r):
        x["value"] = "850"


def v_zero(r):
    for x in flow_rows(r):
        x["value"] = "0"


def v_few_readings(r):
    keep = flow_rows(r)[-3:]
    r["usgs"]["rows"] = [x for x in r["usgs"]["rows"] if x["parameter_code"] != "00060"] + keep


def v_ice(r):  # winter ice: the sensor reports gaps, only a few old readings remain in the last day
    rows = flow_rows(r)
    drop = set(id(x) for x in rows[-40:-5])
    r["usgs"]["rows"] = [x for x in r["usgs"]["rows"] if id(x) not in drop]


VARIANTS = [("no daily statistics", v_no_stats), ("no stage series", v_no_stage), ("no optional source at all", v_no_optional), ("no alert data", v_no_alerts_source),
            ("tidal swing with negative flow", v_tidal), ("flat sensor", v_flat), ("zero flow", v_zero), ("three readings", v_few_readings), ("gap in the last day", v_ice)]


def main():
    rows, _ = load_effective()
    base = json.load(open(os.path.join(ROOT, "cache", SITE + ".json"), encoding="utf-8"))
    now = datetime.datetime.now(datetime.timezone.utc)
    shown = []
    for name, fn in VARIANTS:
        rec = copy.deepcopy(base)
        fn(rec)
        try:
            G = render.ctx(SITE, rows[SITE], rec, now)
            html, _ = render.build_tab("dashboard", G, rows)
        except render.CriticalFail:
            shown.append(name + ": refused")
            continue  # a refusal to render is a legitimate answer to bad data
        except Exception as e:
            bad.append("%s: raised %s: %s" % (name, type(e).__name__, str(e)[:100]))
            continue
        shown.append(name + ": rendered")
        text = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", html, flags=re.S)
        m = BAD.search(text)
        if m:
            bad.append("%s: page shows %r near %r" % (name, m.group(0), re.sub(r"\s+", " ", text[max(0, m.start() - 50):m.end() + 30])))
    # a dead sensor: every reading 40 days old must be refused, never shown as current
    rec = copy.deepcopy(base)
    for x in rec["usgs"]["rows"]:
        t = datetime.datetime.fromisoformat(x["time"]) - datetime.timedelta(days=40) - (now - max(datetime.datetime.fromisoformat(y["time"]) for y in base["usgs"]["rows"]))
        x["time"] = t.isoformat()
    try:
        render.ctx(SITE, rows[SITE], rec, now)
        bad.append("dead sensor (40 days old): rendered instead of failing")
    except render.CriticalFail:
        pass
    print("truth types: %d gauge-type variants, %d failures (%s)" % (len(VARIANTS) + 1, len(bad), "; ".join(shown)))
    for b in bad[:20]:
        print("  FAIL", b)
    return 1 if bad else 0


sys.exit(main())
