"""LINE 0 gate (owner 2026-10-20: "every data block for every water activity, in priority"): the one gate that asks the reader's question.
For every built gauge page, offline, on dist_next:
 1. each Line 0 item is on the page, or the page says plainly that it is not measured or not issued here:
    danger (alerts block), water temperature (tile or "not measured"), clarity (sensor block or "not measured"), rain (tile or block), wind (air tile),
    thunderstorms (storm line, incl. the "forecast is old" form), hourly weather, daylight (sunset tile), trend (direction pill), river forecast (tile incl. "Not issued"),
    forecast rain or model guidance (rain forecast / NWM / outlook block; see below), comparison with past years (norm tile)
 2. order: the "What the water is like now" section comes before the flood history fold
 3. the page never prints a safety verdict ("is safe", "safe to swim", "runnable", "fishable" as a statement about this river)
Usage: python -I tools/line0_gate.py [dist_dir]   exit 1 on any failure, listing page and item."""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "dist_next")

ITEMS = [  # name, regex that proves the item is shown OR honestly declared absent
    ("danger: NWS alerts block", r'id="alerts"'),
    ("water temperature tile or 'not measured'", r'class="tile wtemp|Not measured at this gauge: [^<]*water temperature'),
    ("clarity sensors or 'not measured'", r'id="quality_sensors"|Not measured at this gauge: [^<]*clarity'),
    ("rain tile or rain block", r'class="tile rain|id="rain_totals"'),
    ("wind (air observation tile)", r'class="tile air'),
    ("thunderstorm line", r'class="storm (ok|warn)"'),
    ("hourly weather", r'id="hourly_(heatmap|forecast)"'),
    ("daylight (sunset tile)", r'class="tile sun'),
    ("trend pill", r'<span class="a1">'),
    ("river forecast tile (incl. Not issued)", r'class="tile fcst'),
    ("forecast rain / model guidance / outlook block", r'id="(forecast_rain_totals|nwm_forecast|nwm_medium|cpc_outlook|wpc_outlooks)"'),
    ("comparison with past years", r'class="tile norm'),
]
VERDICT = re.compile(r"\b(is|are|looks|seems) (safe|unsafe|runnable|fishable)\b|\bsafe to (swim|wade|paddle|tube|boat)\b", re.I)
bad = []
pages = 0
for st in sorted(os.listdir(os.path.join(DIST, "river"))):
    for g in sorted(os.listdir(os.path.join(DIST, "river", st))):
        f = os.path.join(DIST, "river", st, g, "index.html")
        if not os.path.exists(f):
            continue
        pages += 1
        h = open(f, encoding="utf-8").read()
        u = "/river/%s/%s/" % (st, g)
        for name, rx in ITEMS:
            if not re.search(rx, h):
                bad.append("%s: missing %s" % (u, name))
        a, b = h.find("What the water is like now"), h.find("Flood record and history")
        if a < 0 or (b > 0 and b < a):
            bad.append("%s: the water section is missing or below the flood history" % u)
        body = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
        body = re.sub(r"does not decide for you[^<]*|no alert does not mean conditions are safe|not a statement that conditions are safe", "", body)  # the disclaimers' own words
        m = VERDICT.search(re.sub(r"<[^>]+>", " ", body))
        if m:
            bad.append("%s: prints a safety verdict: %r" % (u, m.group(0)))
print("line 0 gate: %d gauge pages, %d failures" % (pages, len(bad)))
for x in bad[:40]:
    print("  FAIL", x)
if len(bad) > 40:
    print("  ... and %d more" % (len(bad) - 40))
sys.exit(1 if bad or not pages else 0)
