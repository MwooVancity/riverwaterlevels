"""Gauge context, hero, tiles, answer lines, sun and moon."""
import statistics, os, re, json, math, collections, hashlib, datetime, zoneinfo
from lib.common import *
from lib.core import *
from lib.core import _normalise


def ctx(site, row, rec, now):
    """Everything derived once per gauge; blocks only read this."""
    if not (rec.get("usgs") or {}).get("rows"):  # a cache without USGS readings skips this gauge, never the whole build
        raise CriticalFail("no USGS readings in cache")
    rec = _normalise(rec)
    tzname = usgs_tz(rec) or rec.get("tz") or "UTC"
    zone = zoneinfo.ZoneInfo(tzname)
    fl, sg = series(rec, "00060"), series(rec, "00065")
    if not fl:
        raise CriticalFail("no flow series")
    lt, lv, lrow = fl[-1]
    age_min = (now - lt).total_seconds() / 60
    if age_min > 30 * 24 * 60:
        raise CriticalFail("latest flow older than 30 days (%.0f d)" % (age_min / 1440))
    stats = rec.get("stats")
    ldate = lt.astimezone(zone).date()
    mmdd = ldate.isoformat()[5:10]
    srow = stats.get(mmdd) if stats else None
    win = [x for x in fl if x[0] > lt - datetime.timedelta(hours=24)]
    mdate = ldate.strftime("%b %d").replace(" 0", " ")
    basis, method = lv, "latest reading compared with USGS daily percentiles for %s" % mdate
    if len(win) >= 4:
        steps = sorted((win[i][0] - win[i - 1][0]).total_seconds() for i in range(1, len(win)))
        step = steps[len(steps) // 2] or 900
        if len(win) >= 0.8 * 86400 / step and (win[-1][0] - win[0][0]).total_seconds() >= 20 * 3600:
            basis = sum(x[1] for x in win) / len(win)
            method = "trailing 24-hour mean compared with USGS daily percentiles for %s" % mdate
            if basis and abs(lv / basis - 1) > 0.3 and not oscillating(fl) and max(x[1] for x in win) < 1.5 * max(1e-9, min(x[1] for x in win)):  # the day's mean says little about a river that has just moved by a third or more: judge the latest reading (tidal and oscillating gauges keep the mean)
                basis, method = lv, "latest reading compared with USGS daily percentiles for %s" % mdate
    p = interp_pct(srow, basis) if srow else None
    ago = min(fl, key=lambda x: abs((x[0] - (lt - datetime.timedelta(hours=24))).total_seconds()))
    steps = sorted((fl[i][0] - fl[i - 1][0]).total_seconds() for i in range(max(1, len(fl) - 200), len(fl)))
    tol = max(1200, 0.6 * (steps[len(steps) // 2] if steps else 900))
    osc = oscillating(fl)  # tidal only when the flow itself cycles within the day; a nearby NOAA station shows a tide table but does not make this gauge tidal (Potomac at Little Falls and Delaware at Trenton sit just above the head of tide)
    wc24 = b3.window_change(fl, lt, 24)
    chg = wc24[2] if (not osc) and wc24 and abs((ago[0] - (lt - datetime.timedelta(hours=24))).total_seconds()) <= tol else None  # the same smoothed value as the rate table
    _pn = rec.get("nwps")
    if isinstance(_pn, dict) and isinstance(_pn.get("name"), str):
        _pn["name"] = re.sub(r"\s*\(IN MLLW\)", "", _pn["name"], flags=re.I)  # a datum note in the NWS point name is not part of the place
    out = {"site": site, "row": row, "rec": rec, "now": now, "zone": zone, "tzname": tzname, "fl": fl, "sg": sg, "lt": lt, "lv": lv, "lrow": lrow, "age_min": age_min, "stats": stats, "ldate": ldate,
            "srow": srow, "p": p, "method": method, "chg": chg, "obs": tzl(lt, zone), "flow_then24": (wc24[1] if (not osc) and wc24 else None), "river": row["river"], "place": usgs_place(row, rec)[0], "st": row["state"], "st_shown": usgs_place(row, rec)[1],
            "lat": rec["lat"], "lon": rec["lon"], "has_forecast": bool(((rec.get("nwps") or {}).get("forecast") or {}).get("points")), "fc_page": bool(((rec.get("nwps") or {}).get("forecast") or {}).get("points")), "offline": age_min > 24 * 60, "osc": osc, "tidal": osc and bool((rec.get("tides") or {}).get("rows")), "basis": basis, "basis_mean": method.startswith("trailing")}
    if flow_jitter(out):
        out["chg"] = None  # flow that does not follow the gage height gives no honest 24 h percent
    return out


TAILWATER = re.compile(r"\b(below|bl|blw|downstream of)\b.*\b(dam|lake|lk|reservoir|res|powerplant|power plant)\b|\btailwater\b", re.I)


def flow_jitter(G):
    """Flow that swings more than 1.8x inside 24 h while it does not move with the gage height (correlation under 0.5 over the aligned readings): lock-and-dam, tide or backwater effects, so the flow is not a reliable direction.
    Gauges where flow and stage rise and fall together (dam releases, floods) are never flagged. Returns (low, high, correlation) or None."""
    if G["osc"] or not G["sg"] or (G["sg"][-1][2].get("unit_of_measure") or "").lower() not in ("ft", "feet"):
        return None
    t0 = G["lt"] - datetime.timedelta(hours=24)
    fl = {x[0]: x[1] for x in G["fl"] if x[0] >= t0 and x[1] > 0}
    sg = {x[0]: x[1] for x in G["sg"] if x[0] >= t0}
    ks = [k for k in fl if k in sg]
    if len(ks) < 20:
        return None
    a_, b_ = [fl[k] for k in ks], [sg[k] for k in ks]
    if max(a_) / min(a_) < 1.8 or len(set(b_)) < 3 or len(set(a_)) < 3:
        return None
    r_ = statistics.correlation(a_, b_)
    return (min(a_), max(a_), r_) if r_ < 0.5 else None


def daily_swing(G):
    """'' or a line when flow swung by more than half within a day on 3 or more of the last 7 gauge-local days (releases, locks or tides)."""
    if G.get("tidal"):
        return ""  # a tidal reach already shows its range
    days = {}
    for t, v, _ in G["fl"]:
        if t >= G["lt"] - datetime.timedelta(days=7) and v is not None and v > 0:
            days.setdefault(t.astimezone(G["zone"]).date(), []).append(v)
    big = [(min(v), max(v)) for v in days.values() if len(v) >= 12 and max(v) >= 1.5 * min(v) and abs(v[-1] / v[0] - 1) <= 0.25]  # a day that rose and fell back, not a storm rise (full review: Albuquerque 214 to 999 cfs over a rising week)
    if len(big) < 3:
        return ""
    return '<p class="src swing">Flow here rises and falls within the day: on %d of the last 7 days it swung by more than half (widest day: %s to %s cfs). The 6 h change and the daily comparison can miss this; read the 7-day chart.</p>' % (
        len(big), *map(fmtc, max(big, key=lambda x: x[1] / x[0])))


def model_gap(G, first):
    """A note when the model's first hour is more than 20% away from the measured flow: read its shape, not its numbers."""
    lv = G.get("lv")
    if not lv or first is None or lv <= 0 or abs(first - lv) / lv <= 0.05:  # hater r4: an 8% gap at Billings had no note
        return ""
    return '<p class="src">The model starts at %s cfs while the gauge measured %s cfs (%+.0f%%): read the model for the direction it shows, not its numbers.</p>' % (fmtc(first), fmtc(lv), 100 * (first - lv) / lv)



def point_temp_note(G, f):
    """A line when the station's air temperature is more than 5F from the NWS hourly forecast for the gauge point this hour (hater r5: Wilkerson Pass 34F, gauge forecast 42F)."""
    hs = [(abs((parse_t(h["startTime"]) - G["now"]).total_seconds()), h) for h in (G["rec"].get("nws") or {}).get("hourly") or [] if h.get("startTime") and h.get("temperature") is not None and h.get("temperatureUnit") == "F"]
    d, h = min(hs, key=lambda x: x[0]) if hs else (None, None)
    if d is None or d > 3 * 3600 or abs(h["temperature"] - f) <= 5:
        return ""
    return '<small>NWS forecast for the gauge, %s: %d&deg;F (the station sits elsewhere)</small>' % (esc(tzl(parse_t(h["startTime"]), G["zone"], date=False)), h["temperature"])



def next_impact_cats(n, v):
    """'<small>29.5 ft below action stage (28.0 ft)</small>' from the NWS flood categories, or ''."""
    cats = {k: x for k, x in (n.get("categories") or {}).items() if x is not None}
    low = min(cats, key=cats.get) if cats else None
    return '<small>%.1f ft below %s stage (%.1f ft)</small>' % (cats[low] - v, low, cats[low]) if low and v < cats[low] else ""



def usgs_place(row, rec):
    """(place, state) as the USGS site name words them: 'near Clayton', 'GA' for CHATTOOGA RIVER NEAR CLAYTON, GA on an SC site."""
    nm = ((rec.get("meta") or {}).get("loc") or {}).get("monitoring_location_name") or row.get("raw_name") or ""
    nm = nm.strip().rstrip(".")  # "ARKANSAS RIVER NEAR AVONDALE, CO."
    m = re.search(r"\b(NEAR|NR|AT|ABOVE|ABV|BELOW|BLW)\s+([A-Z .'-]+?),\s*([A-Z]{2})$", nm.upper())
    place, st = row["place"], row["state"]
    if m and m.group(2).strip().lower() == (place or "").lower():
        place = {"NR": "near", "ABV": "above", "BLW": "below"}.get(m.group(1), m.group(1).lower()) + " " + place
        st = m.group(3)
    return place, st


SENT_END = re.compile(r"(?<!\b[A-Z])(?<!\bSt)(?<!\bMt)(?<!\bFt)(?<!\bRd)(?<!\bCo)(?<!\bNo)(?<!\bHwy)(?<!\bAve)\.\s(?=[A-Z0-9])")


def sent_ends(txt):
    """Positions of the full stops that end a sentence; "S. Main St. Bridge" ends none."""
    return [m.start() for m in SENT_END.finditer(txt)]


assert sent_ends("Water spreads across S. Main St. Bridge. Then more.") == [39]


def nws_stage(G, max_h=24):
    """(time, value) of the NWS-observed stage at this gauge's forecast point when under max_h hours old, else None."""
    o = (G["rec"].get("nwps") or {}).get("obs_stage")
    try:
        t, v = parse_t(o["t"]), float(o["v"])
    except (KeyError, TypeError, ValueError):
        return None
    return (t, v) if (G["now"] - t).total_seconds() <= max_h * 3600 and v > -999 else None


def datum_gap(G):
    """(NWS stage, USGS stage) when the two agencies read the same gauge on different zero points (latest readings within 30 minutes of each other differ by more than 0.3 ft); None when they agree or one is missing."""
    o = (G["rec"].get("nwps") or {}).get("obs_stage")
    sg = G["sg"]
    if not o or not sg or (sg[-1][2].get("unit_of_measure") or "").lower() not in ("ft", "feet"):
        return None
    try:
        t, v = parse_t(o["t"]), float(o["v"])
    except (KeyError, TypeError, ValueError):
        return None
    u = min(sg, key=lambda x: abs((x[0] - t).total_seconds()))
    if abs((u[0] - t).total_seconds()) > 1800:
        return None
    return (v, u[1], t) if abs(v - u[1]) > 0.3 else None


def upstream_dams(G):
    """About how many dams the EPA counts in the watershed upstream of the gauge (density per sq km x drainage area); 0 when unknown."""
    sc = ((G["rec"].get("streamcat") or {}).get("vals") or {}).get("damdensws")
    area = G["row"].get("drainage_sqmi") or ((G["rec"].get("meta") or {}).get("loc") or {}).get("drainage_area")  # the inventory lacks the area for some gauges; USGS station metadata has it
    try:
        return round(float(sc) * float(area or 0) * 2.58999)
    except (TypeError, ValueError):
        return 0


def hero(G, pages=None):
    from lib import ui
    c = b3.conditions(G, pages)
    p, srow = G["p"], G["srow"]
    pv = ("below 5th" if p == -1 else "above 95th" if p == 101 else ordinal(p)) if p is not None else "–"
    if p is not None and srow:
        pct_med = "%.0f%% of the median" % (G["basis"] / srow[5] * 100) if srow[5] else ""
        what = ("the trailing 24 h mean (%s cfs)" % fmtc(G["basis"])) if G["basis_mean"] else ("the %s reading" % tzl(G["lt"], G["zone"], date=False))
        cap = "Estimated from %s against %d years of USGS daily statistics for %s." % (what, srow[0], G["ldate"].strftime("%b %d"))
    else:
        pct_med, cap = "", "No percentile: no published statistics for this date."
    sg = G["sg"]
    stage_txt = ("%.2f" % sg[-1][1]) if sg else "–"
    stage_unit = UNITS.get(sg[-1][2].get("unit_of_measure"), sg[-1][2].get("unit_of_measure") or "ft") if sg else "ft"
    chg = G["chg"]
    ndam = upstream_dams(G)
    if p is not None and ndam >= 1:
        cap += (" A dam upstream may have changed flows during this record." if ndam == 1 else " %s dams upstream may have changed flows during this record." % format(ndam, ","))
    if p is not None and G["osc"]:
        cap += (" This gauge is tidal" if G["tidal"] else " Flow at this gauge rises and falls within the day") + ": the comparison uses the daily mean."
    if p is not None and TAILWATER.search(G["row"].get("raw_name") or ""):
        cap += " This gauge is below a dam, so flow follows releases, and the record may include years before the dam."
    d24 = G["lt"] - datetime.timedelta(hours=24)
    cmp_ = None  # tiles are assembled flow, stage, direction, comparison, then the rest
    strip = ""
    bcls = "" if p is None else "b-la" if p != 101 and p < 25 else "b-lp" if p == 101 or p > 75 else "b-lb"
    tiles = ui.tile("flow", "flow", "Latest flow", '<span data-live="flow">%s</span> <small><abbr title="cubic feet per second">cfs</abbr></small>' % fmtc(G["lv"]), ui.spark([x[1] for x in G["fl"] if x[0] >= d24]) + "@@DIR@@", bcls)
    if sg:
        tiles += ui.tile("stage", "stage", "Gage height", '<span data-live="stage">%s</span> <small>%s</small>' % (stage_txt, esc(stage_unit)),
                         ui.spark([x[1] for x in sg if x[0] >= d24]) + '<small class="dv">%s</small>' % ((('<b class="qual">%s</b>' % qual_text(sg[-1][2])) if qual_text(sg[-1][2]) else "") or ((next_impact(G) + "</small><small>Height above the gauge's zero point, not water depth") if next_impact(G) else "") or ("Below the gauge\'s zero point, a fixed reference level, not the riverbed" if sg[-1][1] < 0 else "Height above the gauge's zero point, not water depth"))
                         + (('<small>Reading of <span data-live="stageobs" data-t="%s">%s</span></small>' % (iso(sg[-1][0]), esc(tzl(sg[-1][0], G["zone"])))) if sg[-1][0] != G["lt"] else ""))
    else:  # Memphis 2026-10-26: USGS publishes flow only; the NWS forecast point at the same place observes the stage
        o, n_ = nws_stage(G), G["rec"].get("nwps") or {}
        if o:
            tiles += ui.tile("stage", "stage", "Gage height", '%.2f <small>%s</small>' % (o[1], esc(n_.get("stage_units") or "ft")),
                             '<small>NWS observed at %s, %s; USGS reports no gage height here%s</small>' % (esc(n_.get("lid") or ""), esc(tzl(o[0], G["zone"])), "; below zero means under the gauge's fixed reference level, not a dry river" if o[1] < 0 else "") + next_impact_cats(n_, o[1]))
        else:
            tiles += ui.tile("stage", "stage", "Gage height", "Not measured", "<small>%s</small>" % (
                ("USGS reports none here; NWS %s has no reading in the last 24 h" % esc(n_["lid"])) if n_.get("lid") else "USGS reports no gage height here and no NWS forecast point is linked"))
    if p is None:
        word, plain = "–", ""
    else:
        word = band_word(p)  # single source of truth for the class label (was a duplicate of common.band_word that could drift)
        yrs = srow[0] if srow else 0
        on = G["ldate"].strftime("%b %d")
        plain = ("Lower than at least 95%% of the %d years in the USGS daily statistics for %s." % (yrs, on) if p == -1 else
                 "Higher than at least 95%% of the %d years in the USGS daily statistics for %s." % (yrs, on) if p == 101 else
                 "Lower than %d%% of the %d years in the USGS daily statistics for %s." % (100 - round(p), yrs, on) if p < 50 else
                 "Higher than %d%% of the %d years in the USGS daily statistics for %s." % (round(p), yrs, on))
        _de = (((G["rec"].get("meta") or {}).get("ts") or {}).get("flow_daily") or [None, None])[1]
        if _de and _de[:4].isdigit() and int(_de[:4]) < G["ldate"].year - 1:
            plain = plain.rstrip(".") + " (USGS daily record ended %s)." % fdate(_de)  # hater r4/r5: Freeport's record ends 2015
        if G["basis_mean"]:
            plain = "The 24 h average, %s cfs, is %s" % (fmtc(G["basis"]), plain[0].lower() + plain[1:])  # hater r4: the latest reading sat in the band while the verdict said below
    norm_word, norm_plain = word, plain  # the trend tile below reuses the name `word`
    pre, dir_chip, word_note = tiles, "", ""
    if G["osc"]:
        pass  # the 24 h range already sits on the flow tile and in the answer sentence of a tidal reach (no third copy)
    elif flow_jitter(G) and c.get("sg6") is not None:
        lo_, hi_, rg_ = flow_jitter(G)
        d6 = c["sg6"]
        word, ico = ("Rising", "up") if d6 > 0.1 else ("Falling", "down") if d6 < -0.1 else ("Steady", "steady")
        dir_chip = "%s: gage height %+.2f ft in 6 h" % (word, d6)
        tiles += ui.tile("trend dv " + word.lower(), ico, "Gage height, last 6 h", '%s%.2f <small>ft</small> <small class="word">%s</small>' % ("+" if d6 > 0 else "", d6, word),
                         '<small id="ccap">Flow readings here swing between %s and %s cfs within 24 h and do not move with the gage height (correlation %.2f), so the flow is not a reliable direction and the gage height is used.</small>' % (fmtc(lo_), fmtc(hi_), rg_))
    else:
        if chg is None:
            tiles += ui.tile("trend", "steady", "24 h change", "–", '<small id="ccap">No reading 24 h earlier</small>')
        else:
            c6 = c["chg"].get(6)
            use, span = (c6, "6 h") if c6 is not None else (chg, "24 h")
            c1 = c["chg"].get(1)
            word, ico = ("Rising", "up") if use >= 2 else ("Falling", "down") if use <= -2 else ("Steady", "steady")
            c3 = c["chg"].get(3)
            if word != "Steady" and abs(use) * G["lv"] / 100 < 5:
                word, ico = "Steady", "steady"  # full review: "+2.1% Rising" was +4 cfs
            elif word != "Steady" and abs(use) < 5 and c3 is not None and (abs(c3) < 0.5 or (c3 > 0) != (use > 0)):
                word, ico = "Steady", "steady"  # a small 6 h change the last 3 h do not carry is a wobble (full review: "+2.2% Rising" on a flat river)
            elif word == "Steady" and c3 is not None and abs(c3) >= 3 and abs(c3) * G["lv"] / 100 >= 5:  # 6 h endpoints equal, the last 3 h moved (hater 2026-10-27: "Steady" beside "3 h +4.3%")
                use, span = c3, "3 h"
                word, ico = ("Rising", "up") if c3 > 0 else ("Falling", "down")
            elif word == "Steady" and chg is not None and abs(chg) >= 4:  # a slow, steady move (hater round 3: Memphis "Steady" at -4.8% in 24 h, -27% in 7 days)
                use, span = chg, "24 h"
                word, ico = ("Rising", "up") if chg > 0 else ("Falling", "down")
            if c1 is not None and word != "Steady":
                if abs(c1) >= 2 and (c1 > 0) != (use > 0):
                    word, ico = "Unsteady", "steady"  # the last hour points the other way from the last 6 h
                elif abs(c1) < 0.5 and abs(use) >= 3:
                    word, ico = "Leveling off", "steady"  # it moved, and has stopped
            sgd = c.get("sg6")
            if word in ("Rising", "Falling") and sgd is not None and abs(sgd) >= 0.05 and (sgd > 0) != (use > 0) and abs(use) < 5:
                word, ico = "Unclear", "steady"  # a small flow change that the gage height contradicts is noise, not a direction
                word_note = "<small>Flow changed %+.1f%% in %s but the gage height moved %+.2f ft the other way, so the direction is unclear.</small>" % (use, span, sgd)
            turned = c6 is not None and abs(chg) >= 5 and abs(c6) >= 2 and (chg > 0) != (c6 > 0)
            other = [(n_, v) for n_, v in (("1 h", c1), ("6 h", c6), ("24 h", chg)) if v is not None and n_ != span]
            parts = " &middot; ".join("%s: %s%.1f%%" % (n, "+" if v >= 0 else "", v) for n, v in other)
            uz = round(use)
            dir_chip = ("Steady: no change in %s" % span) if word == "Steady" and abs(use) < 0.05 else "%s: %s%.1f%% flow in %s" % (("%s, leveling off" % ("Falling" if use < 0 else "Rising")) if word == "Leveling off" else word, "+" if use > 0 else "-" if use < 0 else "", abs(use), span)
            if word == "Unsteady" and c1 is not None:
                dir_chip += ", %+.1f%% in the last hour" % c1
            word_note = word_note or {"Leveling off": "<small>It moved over %s but has changed by less than 0.5%% in the last hour.</small>" % span, "Unsteady": "<small>The last hour points the other way from the last %s.</small>" % span}.get(word, "")
            tiles += ui.tile("trend dv " + word.lower().split()[0], ico, "Change, last %s" % span, '%s%.1f%% <small class="word">%s</small>' % ("+" if use > 0 else "-" if use < 0 else "", abs(use), word),
                             '<small>%s%s</small>' % (parts, (" &middot; gage %+.2f ft/h" % gr) if (gr := gage_rate(G)) is not None else "") + (word_note if word == "Unclear" else "")
                             + '<small id="ccap" hidden>Flow 24 h earlier: %s cfs.</small>' % fmtc(G["flow_then24"] if G.get("flow_then24") else G["lv"] / (1 + chg / 100)))
    norm_html = ui.tile("norm", "map", "Is this normal for %s?" % G["ldate"].strftime("%b %d").replace(" 0", " "), norm_word,
                     ('<small class="nt">%s</small>' % esc(norm_plain) if norm_plain else "") + ui.rangebar(p) + (('<small>A year earlier, on %s: %s cfs (USGS daily mean%s).</small>' % (ly[1], fmtc(ly[0]), "" if ly[1].startswith("%s %d," % (G["ldate"].strftime("%b"), G["ldate"].day)) else "; USGS daily means run a day or two behind today")) if (ly := last_year_flow(G)) is not None else "") + '<small id="pcap">%s</small>' % esc(cap), ("wide dv " + bcls).strip())
    nwl = (G["rec"].get("nwps") or {}).get("lid")
    trend_html = tiles[len(pre):]
    if G["osc"]:  # a tidal reach has no 6 h direction: the day's range is the honest trend line, on the tile and in the answer alike
        v24_ = [x[1] for x in G["fl"] if x[0] > G["lt"] - datetime.timedelta(hours=24)]
        if v24_:
            dir_chip = "%s: %s to %s cfs over 24 h%s" % ("Tidal reach" if G["tidal"] else "Rose and fell", fmtc(min(v24_)), fmtc(max(v24_)), " (below zero: the tide pushes water upstream)" if min(v24_) < 0 else "")
    tiles = pre.replace("@@DIR@@", '<small class="dv">%s</small>' % (('<b class="qual">%s</b>' % qual_text(G["fl"][-1][2])) if G["fl"] and qual_text(G["fl"][-1][2]) else esc(dir_chip or "Last 24 hours"))) + norm_html  # the trend lives in the answer pills and the change tile; the flow tile spells out its unit (a hover title does not work on a phone)  # flow, stage, comparison: the answer on the first phone screen
    strip = trend_html + strip  # change, then forecast, alerts, air, rain, sunset ride in one swipe row
    if c["fc"]:
        fcw = c["fc"]
        unit = fcw["unit"]
        above = fcw["cur"] is not None and fcw["cur"] > fcw["v"] + (0.05 if unit == "ft" else 0.02 * abs(fcw["v"]))
        val = ('%.1f <small>ft</small>' % fcw["v"]) if unit == "ft" else ('%s <small>cfs</small>' % fmtc(fcw["v"]))
        _pn = nws_point_note(G)
        sub = '<small>%s%s &middot; NWS point %s%s</small>' % ("first reached " if fcw["repeat"] else "", esc(fcw["t"]), esc(fcw["lid"]), (' (named \u201c%s\u201d, not this gauge\u2019s place)' % esc((G["rec"].get("nwps") or {}).get("name") or "")) if _pn else ((", " + esc((G["rec"].get("nwps") or {}).get("name"))) if (G["rec"].get("nwps") or {}).get("name") else ""))  # reviewers: the first screen named the point by code only
        _end = ("%.1f ft" % fcw["end_v"]) if unit == "ft" else ("%s cfs" % fmtc(fcw["end_v"]))
        _parts = []
        if G["osc"]:
            _parts.append("%s: the level here rises and falls within the day around this forecast" % ("Tidal reach" if G["tidal"] else "Flow rises and falls within the day"))
        elif unit == "ft" and fcw["cur"] is not None and not fcw["datum"] and not above:
            _d = float("%.1f" % fcw["v"]) - float("%.2f" % fcw["cur"])
            _parts.append(("%.1f ft above now" % _d) if _d >= 0.05 else "about level with the latest reading")
        if above and not G["osc"]:
            _parts.append("%s below the latest reading" % (("%.1f ft" % (fcw["cur"] - fcw["v"])) if unit == "ft" else ("%s cfs" % fmtc(fcw["cur"] - fcw["v"]))))
        if fcw.get("swing"):
            _parts.append("swings daily between %s and %s until %s" % (("%.1f ft" % fcw["swing"][0]) if unit == "ft" else ("%s cfs" % fmtc(fcw["swing"][0])), ("%.1f ft" % fcw["v"]) if unit == "ft" else ("%s cfs" % fmtc(fcw["v"])), esc(fcw["swing"][1])))
        if fcw["falls"]:
            _parts.append(("then down to %s by %s" if not above and not G["osc"] else "down to %s by %s") % (_end, esc(fcw["end_t"])))
        if fcw["datum"]:
            _parts.append("NWS and USGS read this gauge on different zero points: on the USGS scale this forecast is about %.1f ft, %s the latest USGS reading" % (fcw["v"] + fcw["datum"][1] - fcw["datum"][0], ("%.1f ft above" % (fcw["v"] + fcw["datum"][1] - fcw["datum"][0] - G["sg"][-1][1])) if fcw["v"] + fcw["datum"][1] - fcw["datum"][0] > G["sg"][-1][1] else ("%.1f ft below" % (G["sg"][-1][1] - fcw["v"] - fcw["datum"][1] + fcw["datum"][0]))))
        if fcw.get("offset"):
            _parts.append("forecast out of step with the gauge reading (details under River forecast)")
        if _parts:
            sub += '<small class="dv">%s</small>' % " &middot; ".join(_parts)
        strip += ui.tile("fcst", "crest", ("NWS forecast" if above and not G["osc"] else ("NWS forecast (falling)" if fcw["cur"] is not None and fcw["v"] < fcw["cur"] - (0.05 if unit == "ft" else 0.02 * abs(fcw["cur"])) else ("Forecast high (NWS stage)" if fcw["datum"] else "Forecast high"))) if unit == "ft" else ("NWS forecast flow" if above and not G["osc"] else "Forecast high flow"), val, sub)
    elif nwl and G["has_forecast"]:
        strip += ui.tile("fcst none", "crest", "River forecast", "Out of date", '<small>The latest NWS forecast for point %s is old or not in feet, so it is not shown. The weather forecast below is not a river forecast.</small>' % esc(nwl))
    elif nwl:
        strip += ui.tile("fcst none", "crest", "River forecast", "Not issued", '<small>NWS forecast point %s has no current river forecast. The weather forecast below is not a river forecast.</small>' % esc(nwl))
    else:
        strip += ui.tile("fcst none", "crest", "River forecast", "Not linked", '<small>The National Weather Service has no river forecast point for this gauge. The weather forecast below is not a river forecast.</small>')
    if c["alerts"] is not None and not c["alerts"]["n"] and c["alerts"].get("age_h") is not None and c["alerts"]["age_h"] > 3:  # a fresh answer is said by the answer line and the alerts block; only an old or missing answer gets a tile
        al = c["alerts"]
        strip += ui.tile("alrt off stale", "bell", "NWS alerts", "No alerts", '<small>%s</small>' % ("Last NWS answer %s. The alert service has not answered since; check weather.gov." % esc(al["asof"])))
    elif c["alerts"] is None:
        strip += ui.tile("alrt unknown", "bell", "NWS alerts", "Unknown", '<small>We have no answer from the National Weather Service alert service for this location. Check weather.gov.</small>')
    if c["wt"]:
        wf = round(c["wt"]["f"])  # the tile prints %.0f: the warning judges that same number
        cold = ('<small class="cold">Below 50&deg;F: cold-water shock and loss of swimming ability within minutes of immersion (<a href="https://www.weather.gov/safety/coldwater" rel="noopener">NWS cold water safety</a>)</small>' if wf < 50 else
                '<small class="cold">Below 60&deg;F: cold-water shock risk on immersion (<a href="https://www.weather.gov/safety/coldwater" rel="noopener">NWS cold water safety</a>)</small>' if wf < 60 else "")
        strip += ui.tile("wtemp", "thermo", "Water temperature", '%.0f<small>&deg;F</small>' % wf, cold + '<small>USGS sensor, %s</small>' % esc(c["wt"]["t"]))
    nw = G["rec"].get("near_wtemp")
    if not c["wt"] and nw and nw.get("t") and isinstance(nw.get("f"), (int, float)) and isinstance(nw.get("mi"), (int, float)) and (G["now"] - parse_t(nw["t"])).total_seconds() < 48 * 3600:  # a null value skips the tile, never the page
        _nm = re.sub(r", (\w\w)$", lambda m: ", " + m.group(1).upper(), nw["name"].title())
        _nm = re.sub(r" (At|Below|Above|Near|Of|On|In)\b", lambda m: " " + m.group(1).lower(), _nm)
        _same = nw["name"].split()[0].lower() == G["river"].split()[0].lower()
        strip += ui.tile("wtemp near", "thermo", "Water temperature nearby", '%.0f<small>&deg;F</small>' % nw["f"], '<small>Measured at %s, %.0f mi away%s, %s. This gauge has no temperature sensor.</small>' % (esc(_nm), nw["mi"], "" if _same else " (a different river)", esc(tzl(parse_t(nw["t"]), G["zone"]))))
    if c["up"]:
        up = c["up"]
        strip += ui.tile("upst", "up", "Upstream gauge" if up["name"].split()[0].lower() == G["river"].split()[0].lower() else "Tributary upstream", '%s <small>cfs</small>' % fmtc(up["flow"]), '<small><a href="%s">%s</a>%s</small>' % (up["url"], esc(up["name"]), "" + ((" &middot; " + esc(up["time"])) if up.get("time") else "")) + ('<small>A much smaller stream than this river: a tributary, not a stand-in for the water on its way.</small>' if G["lv"] and up["flow"] < 0.2 * G["lv"] else ""))
    ban = ui.banner(c["alerts"]["n"], esc("; ".join(c["alerts"]["names"]))) if c["alerts"] and c["alerts"]["n"] else ""
    al_ = c["alerts"]
    if al_ is None:
        a_txt, a_cls = "NWS alerts unknown", "ax"
    elif al_["n"]:
        a_txt, a_cls = "%d active NWS alert%s" % (al_["n"], "" if al_["n"] == 1 else "s"), "ay"
    elif al_.get("age_h") is not None and al_["age_h"] > 3:
        a_txt, a_cls = "NWS alert check is old", "ax"
    else:
        a_txt, a_cls = "No active NWS alerts", "an"
    band_cls = "" if p is None else "la" if p != 101 and p < 25 else "lp" if p == 101 or p > 75 else "lb"
    fc_ = c.get("fc") or {}
    if fc_.get("cur") is not None and fc_.get("v") is not None and fc_.get("t"):
        fu_ = "ft" if fc_["v"] < 100 and fc_["cur"] < 100 else "cfs"
        big_rise = (fc_["v"] - fc_["cur"] >= 1.0) if fu_ == "ft" else (fc_["cur"] > 0 and fc_["v"] >= 1.25 * fc_["cur"])
        if big_rise:
            dir_chip = (dir_chip or "Direction unclear") + "; NWS forecast rises to %s by %s" % (("%.1f ft" % fc_["v"]) if fu_ == "ft" else ("%s cfs" % fmtc(fc_["v"])), fc_["t"])
    lv = G.get("lv")
    lead = ("%s cfs" % fmtc(lv)) if lv is not None else None
    norm_txt = ("%s for %s" % (norm_word, G["ldate"].strftime("%b %d").replace(" 0", " "))) if p is not None else "No past-years comparison for this date"
    # lead the summary with the actual reading so the line answers "how much / is it normal / which way / any alert" at a glance; each part stays a sourced fact, no verdict
    # dv = derived from the reading: when a newer reading is swapped in (worker/index.js, LIVE_JS) each dv element is stamped with the reading time it was computed from
    answer = ('<p class="answer" aria-label="Summary">%s<span class="a2 dv %s">%s</span><span class="a1 dv">%s</span>%s</p>' % (
        ('<span class="a1" data-live="lead">%s</span>' % esc(lead)) if lead else "", band_cls, esc(norm_txt), esc(dir_chip or "Direction unclear"), ('<span class="a3 %s">%s</span>' % (a_cls, esc(a_txt))) if a_txt else ""))
    if c["rain"]:
        strip += ui.tile("rain", "drop", "Rain, last 24 h", '%.2f <small>in</small>' % c["rain"]["in"], '<small>NWS RFC estimate%s</small>' % ((" to " + esc(c["rain"]["to"])) if c["rain"]["to"] else ""))
    if c["air"]:
        a = c["air"]
        wtxt = ", ".join(x for x in (("wind calm" if a["wind"] < 1 else ("wind %s %.0f mph" % (esc(a["dir"]), a["wind"])) if a["dir"] else ("wind %.0f mph" % a["wind"])) if a["wind"] is not None else "", ("gusts %.0f mph" % a["gust"]) if a["gust"] is not None else "") if x)
        # a station name that opens with a sensor code ("070W10895RWS1RP1 at Canyon Creek Rd") keeps only the place
        strip += ui.tile("air", "wind", "Air temperature", '<span data-wx="temp0">%.0f</span><small>&deg;F</small>' % a["f"], ('<small data-wx="wind0">%s</small>' % wtxt if wtxt else "") + '<small>Weather station %s%s%s, <span data-wx="t">%s</span></small>' % (esc(a["st"]), (" (" + esc(re.sub(r"^\S*\d\S*\s+(at|near)\s+", "", a["name"])) + ")") if a.get("name") else "", (", %d mi away" % a["mi"]) if a.get("mi") is not None else "", esc(a["t"])) + point_temp_note(G, a["f"]).replace("<small>", '<small data-wx="note">', 1) + ('<span hidden data-wxst="%s" data-t="%s"></span>' % (esc(a["st"]), esc(a["iso"])) if a.get("iso") else ""))  # inside the tile (hater r6: the note floated loose)
    st_ = sun_times(G["lat"], G["lon"], G["ldate"])
    nx_ = sun_times(G["lat"], G["lon"], G["ldate"] + datetime.timedelta(days=1)) if st_ and G["now"] > st_[1] else None
    if nx_:  # after sunset the next thing a reader plans around is sunrise (hater 2026-10-27: "Sunset today" shown at night)
        rh, _, rz = tzl(nx_[0], G["zone"], date=False).replace("\u00a0", " ").rpartition(" ")
        strip += ui.tile("sun", "sun", "Sunrise tomorrow", '%s <small>%s</small>' % (esc(rh), esc(rz)), '<small>Sunset today was %s &middot; computed from location and date</small>' % esc(tzl(st_[1], G["zone"], date=False)))
    elif st_:
        sh, _, sz = tzl(st_[1], G["zone"], date=False).replace("\u00a0", " ").rpartition(" ")
        strip += ui.tile("sun", "sun", "Sunset today", '%s <small>%s</small>' % (esc(sh), esc(sz)), '<small>Sunrise %s%s &middot; %s, %.0f%% lit &middot; computed from location and date</small>' % (esc(tzl(st_[0], G["zone"], date=False)), (" &middot; last light " + esc(tzl(ct_[1], G["zone"], date=False))) if (ct_ := sun_times(G["lat"], G["lon"], G["ldate"], -6.0)) else "", moon_phase(G["ldate"])[0].lower(), moon_phase(G["ldate"])[1]))
    # "Calm daylight hours" tile deleted 2026-10-27: "calm" was our own threshold, not a source's; it failed 3 of 6 hater pages (gusts ignored, an hour past sunset). The hourly table shows wind, gusts and thunder per hour.
    gone = []
    if not c["wt"] and not series(G["rec"], "00010") and not (nw and nw.get("t") and (G["now"] - parse_t(nw["t"])).total_seconds() < 48 * 3600):
        gone.append("live water temperature (no USGS temperature sensor at this gauge or within 40 mi on this river%s)" % ("; monthly history is shown below" if (G["rec"].get("wtemp") or {}).get("months") else ""))
    if b_quality(G) is None:
        gone.append("clarity (no USGS turbidity or water-quality sensor at this gauge)")
    if not c["rain"]:
        gone.append("NWS radar rain estimate for the last 6 h (rain measured at nearby stations is shown below where reported)")
    if not c["air"]:
        gone.append("air observation (no NWS station report in the last 12 h)")
    if not ((G["rec"].get("airnow") or {}).get("rows")):
        gone.append("air quality (no EPA AirNow monitor reports for this location)")
    if not ((G["rec"].get("nws") or {}).get("hourly")) and not (((G["rec"].get("nws") or {}).get("grid") or {}).get("hours")):  # the hourly table also draws from the grid (hater 2026-10-27, Freeport: "not available" above a full table)
        gone.append("hourly weather (no NWS hourly forecast for this location)")
    if G["osc"] and not (G["rec"].get("tides") or {}).get("rows"):
        gone.append("tide predictions (no NOAA station within 50 mi)")
    strip_html = daily_swing(G) + (('<div class="cstrip" role="group" aria-label="Conditions at the gauge" tabindex="0">%s</div>' % strip) if strip else "") + (('<p class="gaps">Not available for this gauge: %s.</p>' % "; ".join(gone)) if gone else "")
    # Lakebrief comparison 2026-10-21: one line a forum post or local paper can paste, built only from fields already on the page.
    # Water level comes from the same source as the gage tile (Memphis 2026-10-27: tile showed the NWS stage, cite said "not measured").
    cite ='<p class="cite"><small>Cite: %s, %s: water level %s, flow %s (USGS %s, observed %s). %s. Data: USGS, NWS.</small> <button type="button" class="cp" data-cite>Copy</button></p>' % (
        esc(river_at(G["river"], G["place"])), esc(G.get("st_shown") or G["st"]), (('<span data-cs>%.2f</span> ft' % G["sg"][-1][1]) + ((" (gage height at %s)" % esc(tzl(G["sg"][-1][0], G["zone"]))) if G["sg"][-1][0] != G["lt"] else "")) if G["sg"] else (("%.2f ft (NWS %s)" % (nws_stage(G)[1], esc((G["rec"].get("nwps") or {}).get("lid") or ""))) if nws_stage(G) else "not measured"), ('<span data-cf>%s</span> cfs' % fmtc(G["lv"])) if G["lv"] is not None else "not reporting", G["site"], '<span data-co>%s</span>' % esc(G["obs"]), SITE_URL + G["row"]["dashboard_url"])
    return ban + answer + '<div class="hero hero2" data-t="%s">%s</div>' % (iso(G["lt"]), tiles) + strip_html + cite


def last_year_flow(G):
    """Daily mean flow on this date a year ago from the multi-year window (USGS daily means); None when the window does not cover it."""
    m = G["rec"].get("multiyear") or {}
    ser, span, as_of = m.get("series") or {}, m.get("span"), m.get("as_of")
    if not ser or not span or not as_of:
        return None
    try:
        off = (datetime.date.fromisoformat(as_of) - G["ldate"]).days
    except ValueError:
        return None
    idx = span - 1 - off
    row = ser.get(str(G["ldate"].year - 1))
    if row is None:
        return None
    if off < 0 and len(row):  # the daily window ends at as_of (USGS daily means lag a day or two): use its last day and name the date
        idx, when = len(row) - 1, datetime.date.fromisoformat(as_of)
    else:
        when = G["ldate"]
    if not (0 <= idx < len(row)) or row[idx] is None:
        return None
    return row[idx], "%s %d, %d" % (when.strftime("%b"), when.day, when.year - 1)  # `when` is this year's date; the value is last year's


def gage_rate(G):
    """Gage height change over the last hour in ft/h (two readings an hour apart); None when under 0.05 ft/h or no stage."""
    sg = G["sg"]
    if not sg:
        return None
    t1, v1, _ = sg[-1]
    past = [x for x in sg if x[0] <= t1 - datetime.timedelta(minutes=55)]
    if not past:
        return None
    t0, v0, _ = past[-1]
    hrs = (t1 - t0).total_seconds() / 3600
    if hrs <= 0:
        return None
    r = (v1 - v0) / hrs
    return r if abs(r) >= 0.05 else None


def storm_line(G):
    """Lightning is the on-water danger that river levels do not show: the hours in the next 24 that the NWS hourly forecast calls thunderstorms, or an explicit 'none' (silence would read as fine). Text comes from the NWS short forecast, not from us."""
    n = G["rec"].get("nws") or {}
    hr = n.get("hourly") or []
    age = hours_old(n.get("hourly_updated"), G["now"]) if n.get("hourly_updated") else None
    if not hr or age is None:
        return ""
    if age > 12:
        return '<p class="storm warn">Thunderstorm outlook: the NWS hourly forecast for this location is %d h old; check weather.gov for the current thunderstorm risk before going on the water.</p>' % age
    nxt = [p for p in hr if parse_t(p["startTime"]) > G["now"] - datetime.timedelta(hours=1)][:24]
    if len(nxt) < 12:
        return ""
    runs, cur = [], None
    for p in nxt:
        hit = "thunder" in (p.get("shortForecast") or "").lower()
        t = parse_t(p["startTime"])
        if hit and cur is None:
            cur = [t, t]
        elif hit:
            cur[1] = t
        elif cur is not None:
            runs.append(cur)
            cur = None
    if cur is not None:
        runs.append(cur)
    per = [p for p in n.get("periods") or [] if parse_t(p["startTime"]) < G["now"] + datetime.timedelta(hours=24) and parse_t(p.get("endTime") or p["startTime"]) > G["now"] and re.search(r"(?i)t-?storm|thunder", (p.get("shortForecast") or "") + " " + (p.get("detailedForecast") or ""))]
    if not runs and per:  # full review: "not in the forecast wording" above "Tonight: Slight Chance T-storms"
        return '<p class="storm warn"><b>Thunderstorms in the forecast:</b> the NWS forecast for %s says %s.</p>' % (esc(per[0]["name"]), esc((per[0].get("shortForecast") or "thunderstorms possible").replace("T-storms", "thunderstorms")))
    if not runs:  # the forecast words name no thunderstorm; the hourly grid may still carry a small chance (hater 2026-10-27: "none" above "Thunder % 9 11")
        pk = 0
        for h in [h for h in ((n.get("grid") or {}).get("hours") or []) if parse_t(h["t"]) > G["now"] - datetime.timedelta(hours=1)][:24]:  # the same hours the table shows (full review: "up to 15%" over a row of zeros)
            pk = max(pk, h.get("thunder") or 0)
        if pk:
            return '<p class="storm ok">Thunderstorms: not in the National Weather Service forecast wording for the next %d hours; the hourly grid gives a thunder chance of up to %d%%.</p>' % (len(nxt), round(pk))
        return '<p class="storm ok">Thunderstorms: none in the National Weather Service forecast for the next %d hours.</p>' % len(nxt)
    when = "; ".join("%s to %s" % (tzl(a, G["zone"], date=(b - a) >= datetime.timedelta(hours=11)), tzl(b + datetime.timedelta(hours=1), G["zone"], date=(b - a) >= datetime.timedelta(hours=11))) if a != b else tzl(a, G["zone"], date=False) for a, b in runs)
    return '<p class="storm warn"><b>Thunderstorms in the forecast:</b> %s (gauge-local time).</p>' % esc(when)



def impact_flow(G):
    """True when the NWS impact thresholds are flows, not stages: a point can publish ft categories beside cfs impacts (Boise 13206000: minor 10.1 ft, impacts from 4,200)."""
    n = G["rec"].get("nwps") or {}
    cats = [v for v in (n.get("categories") or {}).values() if isinstance(v, (int, float)) and v > 0]
    imp = [i["stage"] for i in n.get("impacts") or [] if isinstance(i.get("stage"), (int, float))]
    return bool(cats and imp and min(imp) > 10 * max(cats))


def impact_list(G):
    """{stage: [statement, ...]} of NWS impact statements, cleaned once for every place that shows them: a rain scenario ("2 TO 3 INCH IN 24 HOUR ... WILL CAUSE THE RIVER TO RISE TO 4.7 FEET") is not a stage impact and is left out; all-capitals text is set in sentence case; the point code reads as its name."""
    n = G["rec"].get("nwps") or {}
    by = {}
    for i in n.get("impacts") or []:
        if not isinstance(i.get("stage"), (int, float)):
            continue
        t = re.sub(r"<[^>]+>", "", html.unescape(i.get("statement") or "")).strip()
        t = re.sub(r"\s*\+\s*$", "", re.sub(r"(?i)\s*for more information,?\s*(please\s*)?click here\.?", "", t)).strip()  # full review: dead link text and a stray "+"
        if len(t) < 30 or re.search(r"(?i)\binch(es)?\b[^.]{0,40}\b\d+\s*hours?\b", t):
            continue
        if sum(ch.isupper() for ch in t) > 0.6 * max(1, sum(ch.isalpha() for ch in t)):
            t = re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), t.lower())
        if n.get("lid"):
            t = re.sub(r"(?i)\b%s\b" % re.escape(n["lid"]), n.get("name") or "the NWS forecast point", t)
        by.setdefault(i["stage"], [])
        if t not in by[i["stage"]]:
            by[i["stage"]].append(t)
    return by


def next_impact(G):
    """The next NWS impact statement above the latest reading, short, for the gage tile: the first thing a wader or boater wants to know about the level."""
    n = G["rec"].get("nwps") or {}
    if not G["sg"]:
        return ""
    gap = datum_gap(G)
    cur = gap[0] if gap else G["sg"][-1][1]
    unit = (n.get("stage_units") or "ft").lower()
    _ref = ("the NWS reading of %.2f %s, on a different zero point from USGS" % (cur, unit)) if gap else "the latest reading"  # full review: Suwannee distances from 53.51 beside a 54.34 headline
    by = impact_list(G)  # the same list the impacts block shows (full review: tile 10.0 ft, block 7.0 ft)
    if impact_flow(G):  # thresholds published as flow: compared with the flow reading, never with the gage height
        up_ = [s_ for s_ in sorted(by) if G["lv"] is not None and s_ > G["lv"]]
        return ("Next NWS impact at %s cfs (%s cfs above the latest flow)" % (fmtc(up_[0]), fmtc(up_[0] - G["lv"]))) if up_ else ""
    ahead = [s_ for s_ in sorted(by) if s_ > cur]
    if not ahead:
        cats = {k: v for k, v in (n.get("categories") or {}).items() if isinstance(v, (int, float)) and v > cur}
        return ("NWS %s stage %.1f %s (%.1f %s above %s)" % (min(cats, key=cats.get), min(cats.values()), esc(unit), min(cats.values()) - cur, esc(unit), _ref)) if cats else ""  # full review: Moody showed no distance to its action stage
    i = {"stage": ahead[0]}
    txt = " / ".join(by[ahead[0]])
    end = next(iter(sent_ends(txt)), -1)
    if 20 <= end < 160:
        txt = txt[:end + 1]
    elif len(txt) > 160:
        cut = txt.rfind(" ", 0, 157)
        txt = txt[:cut if cut > 40 else 157] + "\u2026"
    cats = {k: v for k, v in (n.get("categories") or {}).items() if isinstance(v, (int, float)) and cur < v < i["stage"]}
    pre = ("NWS %s stage %.1f %s (%.1f %s above %s); " % (min(cats, key=cats.get), min(cats.values()), esc(unit), min(cats.values()) - cur, esc(unit), "the NWS reading" if gap else "the latest reading")) if cats else ""  # full review: Salt River showed the 42 ft impact, not Action 24 / Minor 30
    base = pre + "Next NWS impact at %.1f %s (%.1f %s above %s)" % (i["stage"], esc(unit), i["stage"] - cur, esc(unit), _ref)
    gr = gage_rate(G)  # time-to-flood: pure arithmetic from the rate of rise already on the page, labelled "at the current rate", no verdict
    fpk = max((s_ for _, s_, _ in fc_points(n.get("forecast") or {}) if s_ is not None), default=None) if (n.get("forecast") or {}).get("points") else None
    if gr and gr > 0 and not daily_swing(G) and not G.get("osc") and (fpk is None or fpk >= i["stage"]):  # full review: "12 h away" beside an NWS forecast that falls (Hudson)
        hrs = (i["stage"] - cur) / gr
        if hrs <= 72:  # only a near-term, actionable estimate; past ~3 days a straight-line rate says nothing
            base += "; %s away at the current +%.2f %s/h rise" % ("under 1 h" if hrs < 1 else ("about %d h" % round(hrs)), gr, esc(unit))
    return base


def sun_times(lat, lon, d, alt=-0.833):
    jd0 = (datetime.datetime(d.year, d.month, d.day, tzinfo=datetime.timezone.utc).timestamp() / 86400) + 2440587.5
    n = math.ceil(jd0 - 2451545.0 + 0.0008)
    js = n + 0.0009 - lon / 360
    rad = math.radians
    M = (357.5291 + 0.98560028 * js) % 360
    C = 1.9148 * math.sin(rad(M)) + 0.02 * math.sin(rad(2 * M)) + 0.0003 * math.sin(rad(3 * M))
    lam = (M + C + 180 + 102.9372) % 360
    jt = 2451545.0 + js + 0.0053 * math.sin(rad(M)) - 0.0069 * math.sin(rad(2 * lam))
    dec = math.asin(math.sin(rad(lam)) * math.sin(rad(23.4397)))
    cw = (math.sin(rad(alt)) - math.sin(rad(lat)) * math.sin(dec)) / (math.cos(rad(lat)) * math.cos(dec))
    if cw < -1 or cw > 1:
        return None
    w = math.degrees(math.acos(cw))
    to = lambda J: datetime.datetime.fromtimestamp((J - 2440587.5) * 86400, datetime.timezone.utc)
    return to(jt - w / 360), to(jt + w / 360)


def moon_phase(d):
    """Moon phase from the date (computed, mean synodic month from the 2000-01-06 new moon): name and percent lit."""
    age = ((datetime.datetime(d.year, d.month, d.day, 12, tzinfo=datetime.timezone.utc).timestamp() / 86400 + 2440587.5) - 2451550.1) % 29.530588853
    names = ["New moon", "Waxing crescent", "First quarter", "Waxing gibbous", "Full moon", "Waning gibbous", "Last quarter", "Waning crescent"]
    return names[int((age / 29.530588853) * 8 + 0.5) % 8], 50 * (1 - math.cos(2 * math.pi * age / 29.530588853))


def nws_point_note(G):
    """When the NWS forecast point is named for another place than this gauge (Hudson River at Troy for the gauge at Green Island), say so: its flood stages and impact statements belong to that point."""
    n = G["rec"].get("nwps") or {}
    def norm(t):
        t = re.sub(r"\b(st|saint)\b\.?", "saint", (t or "").lower())
        t = re.sub(r"\bmt\b\.?", "mount", t)
        t = re.sub(r"\bft\b\.?", "fort", t)
        return re.sub(r"[^a-z0-9 ]", " ", t).split()
    nm, pl = norm(n.get("name")), [w for w in norm(G["place"]) if w not in ("near", "nr", "at", "above", "abv", "below", "blw")]
    if not nm or not pl:
        return ""
    if all(w in nm for w in pl) or "".join(pl) in "".join(nm):  # every word of the gauge's place is in the NWS name ("Desoto" in "De Soto")
        return ""
    return "The NWS links its forecast point %s to this USGS gauge but names it \u201c%s\u201d, for a nearby place. %s" % (n.get("lid") or "", n.get("name"), "Its flood stages are on the NWS stage scale; its impact statements are NWS flow thresholds, compared with the latest USGS flow." if impact_flow(G) else "Its flood stages and impact statements are on the NWS stage scale; where the NWS and USGS read this gauge on different zero points, the margins below use the NWS reading.")
