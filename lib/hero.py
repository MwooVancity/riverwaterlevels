"""Gauge context, hero, tiles, answer lines, sun and moon."""
import statistics, os, re, json, math, collections, hashlib, datetime, zoneinfo
from lib.common import *
from lib.core import *
from lib.core import _normalise


def ctx(site, row, rec, now):
    """Everything derived once per gauge; blocks only read this."""
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
            if basis and abs(lv / basis - 1) > 0.3 and not oscillating(fl):  # the day's mean says little about a river that has just moved by a third or more: judge the latest reading (tidal and oscillating gauges keep the mean)
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
            "srow": srow, "p": p, "method": method, "chg": chg, "obs": tzl(lt, zone), "flow_then24": (wc24[1] if (not osc) and wc24 else None), "river": row["river"], "place": row["place"], "st": row["state"],
            "lat": rec["lat"], "lon": rec["lon"], "has_forecast": bool(((rec.get("nwps") or {}).get("forecast") or {}).get("points")), "fc_page": bool(((rec.get("nwps") or {}).get("forecast") or {}).get("points")), "offline": age_min > 24 * 60, "osc": osc, "basis": basis, "basis_mean": method.startswith("trailing")}
    if flow_jitter(out):
        out["chg"] = None  # flow that does not follow the gage height gives no honest 24 h percent
    return out


TAILWATER = re.compile(r"\b(below|bl|blw|downstream of)\b.*\b(dam|lake|lk|reservoir|res|powerplant|power plant)\b|\btailwater\b", re.I)


def _swing_note(G):
    """Flow that varies by a factor of 1.5 or more inside 24 h (hydropower or release cycles): a change over a few hours depends on the hour of the day."""
    t0 = G["lt"] - datetime.timedelta(hours=24)
    v = [x[1] for x in G["fl"] if x[0] >= t0 and x[1] > 0]
    if len(v) >= 20 and max(v) / min(v) >= 1.5:
        return '<small>Flow varied between %s and %s cfs in the last 24 h, so a change over a few hours depends on the time of day.</small>' % (fmtc(min(v)), fmtc(max(v)))
    return ""


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


def dam_count(G):
    """Dams the EPA counts upstream, or None when StreamCat has no value for this gauge (silence must not read as no dams)."""
    sc = ((G["rec"].get("streamcat") or {}).get("vals") or {}).get("damdensws")
    area = G["row"].get("drainage_sqmi") or ((G["rec"].get("meta") or {}).get("loc") or {}).get("drainage_area")
    return None if sc is None or not area else upstream_dams(G)


def dams_txt(n):
    """A modelled count (dam density x drainage area): thousands separator, and no false precision above 100."""
    return "{:,}".format(int(round(n, -1)) if n >= 100 else n)


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
        cap += " Upstream dams may have changed flows during this record."
    if p is not None and G["osc"]:
        cap += " This gauge is tidal: the comparison uses the daily mean."
    if p is not None and TAILWATER.search(G["row"].get("raw_name") or ""):
        cap += " This gauge is below a dam, so flow follows releases, and the record may include years before the dam."
    d24 = G["lt"] - datetime.timedelta(hours=24)
    cmp_ = None  # tiles are assembled flow, stage, direction, comparison, then the rest
    strip = ""
    bcls = "" if p is None else "b-la" if p != 101 and p < 25 else "b-lp" if p == 101 or p > 75 else "b-lb"
    tiles = ui.tile("flow", "flow", "Latest flow", '<span data-live="flow">%s</span> <small><abbr title="cubic feet per second">cfs</abbr></small>' % fmtc(G["lv"]), ui.spark([x[1] for x in G["fl"] if x[0] >= d24]) + "@@DIR@@", bcls)
    tiles += ui.tile("stage", "stage", "Gage height", '<span data-live="stage">%s</span> <small>%s</small>' % (stage_txt, esc(stage_unit)),
                     (ui.spark([x[1] for x in sg if x[0] >= d24]) if sg else "") + '<small class="dv">%s</small>%s' % ((('<b class="qual">%s</b>' % qual_text(sg[-1][2])) if sg and qual_text(sg[-1][2]) else "") or next_impact(G) or "Level relative to the gauge\'s zero", "" if sg else ""))
    if p is None:
        word, plain = "–", ""
    else:
        word = band_word(p)  # single source of truth for the class label (was a duplicate of common.band_word that could drift)
        yrs = srow[0] if srow else 0
        on = G["ldate"].strftime("%b %d")
        plain = ("Lower than at least 95%% of the %d years on record for %s." % (yrs, on) if p == -1 else
                 "Higher than at least 95%% of the %d years on record for %s." % (yrs, on) if p == 101 else
                 "Lower than %d%% of the %d years on record for %s." % (100 - round(p), yrs, on) if p < 50 else
                 "Higher than %d%% of the %d years on record for %s." % (round(p), yrs, on))
        cap += ""
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
            word, ico = ("Rising", "up") if use > 1 else ("Falling", "down") if use < -1 else ("Steady", "steady")
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
            other = [("24 h", chg)] + [("%d h" % h, v) for h, v in sorted(c["chg"].items()) if h == 1 and span == "6 h"]
            parts = " &middot; ".join("%s: %s%.1f%%" % (n, "+" if v >= 0 else "", v) for n, v in other)
            uz = round(use)
            dir_chip = ("Steady: no change in %s" % span) if word == "Steady" and abs(use) < 0.05 else "%s: %s%.1f%% flow in %s" % (("%s, leveling off" % ("Falling" if use < 0 else "Rising")) if word == "Leveling off" else word, "+" if use > 0 else "-" if use < 0 else "", abs(use), span)
            word_note = word_note or {"Leveling off": "<small>It moved over %s but has changed by less than 0.5%% in the last hour.</small>" % span, "Unsteady": "<small>The last hour points the other way from the last %s.</small>" % span}.get(word, "")
            tiles += ui.tile("trend dv " + word.lower().split()[0], ico, "Change, last %s" % span, '%s%.1f%% <small class="word">%s</small>' % ("+" if use > 0 else "-" if use < 0 else "", abs(use), word),
                             '<small>%s%s</small>' % (parts, (" &middot; gage %+.2f ft/h" % gr) if (gr := gage_rate(G)) is not None else "") + (word_note if word == "Unclear" else "")
                             + (('<small>Last 20%% rise: %s.</small>' % (("%.0f days ago" % lbr if lbr >= 1.5 else "%.0f hours ago" % (lbr * 24)) if lbr is not None and lbr >= 0 else "none in the last 7 days")) if (lbr := last_big_rise(G)) != -1 else "")
                             + '<small id="ccap" hidden>Flow 24 h earlier: %s cfs.</small>' % fmtc(G["flow_then24"] if G.get("flow_then24") else G["lv"] / (1 + chg / 100)))
    norm_html = ui.tile("norm", "map", "Is this normal for %s?" % G["ldate"].strftime("%b %d").replace(" 0", " "), norm_word,
                     ('<small class="nt">%s</small>' % esc(norm_plain) if norm_plain else "") + ui.rangebar(p) + (('<small>%s last year: %s cfs (USGS daily mean).</small>' % (ly[1], fmtc(ly[0]))) if (ly := last_year_flow(G)) is not None else "") + '<small id="pcap">%s</small>' % esc(cap), ("wide dv " + bcls).strip())
    nwl = (G["rec"].get("nwps") or {}).get("lid")
    trend_html = tiles[len(pre):]
    if G["osc"]:  # a tidal reach has no 6 h direction: the day's range is the honest trend line, on the tile and in the answer alike
        v24_ = [x[1] for x in G["fl"] if x[0] > G["lt"] - datetime.timedelta(hours=24)]
        if v24_:
            dir_chip = "Tidal reach: %s to %s cfs over 24 h" % (fmtc(min(v24_)), fmtc(max(v24_)))
    tiles = pre.replace("@@DIR@@", '<small class="dv">%s</small>' % (('<b class="qual">%s</b>' % qual_text(G["fl"][-1][2])) if G["fl"] and qual_text(G["fl"][-1][2]) else esc(dir_chip or "Last 24 hours"))) + norm_html  # the trend lives in the answer pills and the change tile; the flow tile spells out its unit (a hover title does not work on a phone)  # flow, stage, comparison: the answer on the first phone screen
    strip = trend_html + strip  # change, then forecast, alerts, air, rain, sunset ride in one swipe row
    if c["fc"]:
        fcw = c["fc"]
        unit = fcw["unit"]
        above = fcw["cur"] is not None and fcw["cur"] > fcw["v"] + (0.05 if unit == "ft" else 0.02 * abs(fcw["v"]))
        val = ('%.1f <small>ft</small>' % fcw["v"]) if unit == "ft" else ('%s <small>cfs</small>' % fmtc(fcw["v"]))
        _pn = nws_point_note(G)
        sub = '<small>%s%s &middot; NWS point %s%s</small>' % ("first reached " if fcw["repeat"] else "", esc(fcw["t"]), esc(fcw["lid"]), (' (named \u201c%s\u201d, not this gauge\u2019s place)' % esc((G["rec"].get("nwps") or {}).get("name") or "")) if _pn else "")
        _end = ("%.1f ft" % fcw["end_v"]) if unit == "ft" else ("%s cfs" % fmtc(fcw["end_v"]))
        _parts = []
        if G["osc"]:
            _parts.append("Tidal reach: the NWS forecast is a net level; compare it with the day's range on the flow tile")
        elif unit == "ft" and fcw["cur"] is not None and not fcw["datum"] and abs(fcw["v"] - fcw["cur"]) >= 0.05 and not above:
            _parts.append("%.1f ft above now" % abs(fcw["v"] - fcw["cur"]))
        if above and not G["osc"]:
            _parts.append("%s below the latest reading" % (("%.1f ft" % (fcw["cur"] - fcw["v"])) if unit == "ft" else ("%s cfs" % fmtc(fcw["cur"] - fcw["v"]))))
        if fcw["falls"]:
            _parts.append(("then down to %s by %s" if not above and not G["osc"] else "down to %s by %s") % (_end, esc(fcw["end_t"])))
        if fcw["datum"]:
            _parts.append("NWS and USGS read this gauge on different zero points; the forecast is in NWS stage")
        if fcw.get("offset"):
            _parts.append("forecast out of step with the gauge reading (details under River forecast)")
        if _parts:
            sub += '<small class="dv">%s</small>' % " &middot; ".join(_parts)
        strip += ui.tile("fcst", "crest", ("NWS forecast" if above and not G["osc"] else ("Forecast high (NWS stage)" if fcw["datum"] else "Forecast high")) if unit == "ft" else ("NWS forecast flow" if above and not G["osc"] else "Forecast high flow"), val, sub)
    elif nwl and G["has_forecast"]:
        strip += ui.tile("fcst none", "crest", "River forecast", "Out of date", '<small>The latest NWS forecast for point %s is old or not in feet, so it is not shown. The weather forecast below is not a river forecast.</small>' % esc(nwl))
    elif nwl:
        strip += ui.tile("fcst none", "crest", "River forecast", "Not issued", '<small>NWS forecast point %s has no current river forecast. The weather forecast below is not a river forecast.</small>' % esc(nwl))
    else:
        strip += ui.tile("fcst none", "crest", "River forecast", "Not linked", '<small>No NWS river forecast point is linked to this gauge in our data. The weather forecast below is not a river forecast.</small>')
    if c["alerts"] is not None and not c["alerts"]["n"] and c["alerts"].get("age_h") is not None and c["alerts"]["age_h"] > 3:  # a fresh answer is said by the answer line and the alerts block; only an old or missing answer gets a tile
        al = c["alerts"]
        strip += ui.tile("alrt off stale", "bell", "NWS alerts", "No alerts", '<small>%s</small>' % ("Last NWS answer %s. The alert service has not answered since; check weather.gov." % esc(al["asof"])))
    elif c["alerts"] is None:
        strip += ui.tile("alrt unknown", "bell", "NWS alerts", "Unknown", '<small>We have no answer from the National Weather Service alert service for this location. Check weather.gov.</small>')
    if c["wt"]:
        wf = c["wt"]["f"]
        cold = ('<small class="cold">Below 50&deg;F: cold-water shock and loss of swimming ability within minutes of immersion (<a href="https://www.weather.gov/safety/coldwater" rel="noopener">NWS cold water safety</a>)</small>' if wf < 50 else
                '<small class="cold">Below 60&deg;F: cold-water shock risk on immersion (<a href="https://www.weather.gov/safety/coldwater" rel="noopener">NWS cold water safety</a>)</small>' if wf < 60 else "")
        strip += ui.tile("wtemp", "thermo", "Water temperature", '%.0f<small>&deg;F</small>' % wf, cold + '<small>USGS sensor, %s</small>' % esc(c["wt"]["t"]))
    nw = G["rec"].get("near_wtemp")
    if not c["wt"] and nw and nw.get("t") and (G["now"] - parse_t(nw["t"])).total_seconds() < 48 * 3600:
        _nm = re.sub(r", (\w\w)$", lambda m: ", " + m.group(1).upper(), nw["name"].title())
        _nm = re.sub(r" (At|Below|Above|Near|Of|On|In)\b", lambda m: " " + m.group(1).lower(), _nm)
        _same = nw["name"].split()[0].lower() == G["river"].split()[0].lower()
        strip += ui.tile("wtemp near", "thermo", "Water temperature nearby", '%.0f<small>&deg;F</small>' % nw["f"], '<small>No sensor at this gauge. %s: %s, %.0f mi away%s &middot; %s</small>' % ("Nearest on this river" if _same else "Nearest sensor", esc(_nm), nw["mi"], "" if _same else " (a different river)", esc(tzl(parse_t(nw["t"]), G["zone"]))))
    if c["up"]:
        up = c["up"]
        strip += ui.tile("upst", "up", "Upstream gauge now", '%s <small>cfs</small>' % fmtc(up["flow"]), '<small><a href="%s">%s</a>%s</small>' % (up["url"], esc(up["name"]), ((" &middot; measured lag about %d h" % up["lag"]) if up.get("lag") else "") + ((" &middot; " + esc(up["time"])) if up.get("time") else "")) + ('<small>A much smaller stream than this river: a tributary, not a stand-in for the water on its way.</small>' if G["lv"] and up["flow"] < 0.2 * G["lv"] else ""))
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
        strip += ui.tile("air", "wind", "Air temperature", '%.0f<small>&deg;F</small>' % a["f"], ('<small>%s</small>' % wtxt if wtxt else "") + '<small>Weather station %s%s%s, %s</small>' % (esc(a["st"]), (" (" + esc(re.sub(r"^\S*\d\S*\s+(at|near)\s+", "", a["name"])) + ")") if a.get("name") else "", (", %d mi away" % a["mi"]) if a.get("mi") is not None else "", esc(a["t"])))
    st_ = sun_times(G["lat"], G["lon"], G["ldate"])
    if st_:
        sh, _, sz = tzl(st_[1], G["zone"], date=False).replace("\u00a0", " ").rpartition(" ")
        strip += ui.tile("sun", "sun", "Sunset today", '%s <small>%s</small>' % (esc(sh), esc(sz)), '<small>Sunrise %s%s &middot; %s, %.0f%% lit &middot; computed from location and date</small>' % (esc(tzl(st_[0], G["zone"], date=False)), (" &middot; last light " + esc(tzl(ct_[1], G["zone"], date=False))) if (ct_ := sun_times(G["lat"], G["lon"], G["ldate"], -6.0)) else "", moon_phase(G["ldate"])[0].lower(), moon_phase(G["ldate"])[1]))
    ch = calm_hours(G)
    if ch:
        runs_, n_ = ch
        strip += ui.tile("calm", "sun", "Calm daylight hours today", (esc(runs_[0]) if runs_ else "No calm hour") + (' <small>+%d more</small>' % (len(runs_) - 1) if len(runs_) > 1 else ""),
                         '<small>%s</small>' % esc((lambda s: s[:1].upper() + s[1:])(("; ".join(runs_) + ": " if len(runs_) > 1 else "" if runs_ else "No daylight hour today: ") + "no thunder, wind under 15 mph, no rain in the NWS hourly grid (%d daylight hours checked)" % n_)))
    gone = []
    if not c["wt"] and not (nw and nw.get("t") and (G["now"] - parse_t(nw["t"])).total_seconds() < 48 * 3600):
        gone.append("water temperature (no USGS temperature sensor at this gauge or within 40 mi on this river)")
    if b_quality(G) is None:
        gone.append("clarity (no USGS turbidity or water-quality sensor at this gauge)")
    if not c["rain"]:
        gone.append("rain estimate (no NWS precipitation estimate in the last 6 h)")
    if not c["air"]:
        gone.append("air observation (no NWS station report in the last 12 h)")
    if not ((G["rec"].get("airnow") or {}).get("rows")):
        gone.append("air quality (no EPA AirNow monitor reports for this location)")
    if not ((G["rec"].get("nws") or {}).get("hourly")):
        gone.append("hourly weather (no NWS hourly forecast for this location)")
    if G["osc"] and not (G["rec"].get("tides") or {}).get("rows"):
        gone.append("tide predictions (no NOAA station within 50 mi)")
    strip_html = (('<div class="cstrip" role="group" aria-label="Conditions at the gauge" tabindex="0">%s</div>' % strip) if strip else "") + (('<p class="gaps">Not measured at this gauge: %s.</p>' % "; ".join(gone)) if gone else "")
    # Lakebrief comparison 2026-10-21: one line a forum post or local paper can paste, built only from fields already on the page
    cite = '<p class="cite"><small>Cite: %s, %s: water level %s, flow %s (USGS %s, observed %s). %s. Data: USGS, NWS.</small> <button type="button" class="cp" data-cite>Copy</button></p>' % (
        esc(river_at(G["river"], G["place"])), esc(G["st"]), ("%.2f ft" % G["sg"][-1][1]) if G["sg"] else "not measured", (fmtc(G["lv"]) + " cfs") if G["lv"] is not None else "not reporting", G["site"], esc(G["obs"]), SITE_URL + G["row"]["dashboard_url"])
    return ban + answer + '<div class="hero hero2" data-t="%s">%s</div>' % (iso(G["lt"]), tiles) + strip_html + cite


def calm_hours(G):
    """Daylight hours today with no thunder, wind under 15 mph and no rain in the NWS hourly grid, as runs like '7a to 11a'; None when the grid or the sun times are missing."""
    hrs = ((G["rec"].get("nws") or {}).get("grid") or {}).get("hours") or []
    st_ = sun_times(G["lat"], G["lon"], G["ldate"])
    if not hrs or not st_:
        return None
    zone = G["zone"]
    ok = []
    for h in hrs:
        try:
            t = parse_t(h["t"]).astimezone(zone)
        except (TypeError, ValueError):
            continue
        if t.date() != G["ldate"] or t < st_[0].astimezone(zone) or t > st_[1].astimezone(zone):
            continue
        calm = (h.get("thunder") or 0) < 30 and (h.get("wind_kmh") or 0) < 24.1 and (h.get("qpf_mm") or 0) < 0.3
        ok.append((t, calm))
    if not ok:
        return None
    runs, cur = [], None
    for t, calm in ok:
        if calm and cur is None:
            cur = [t, t]
        elif calm:
            cur[1] = t
        elif cur:
            runs.append(cur); cur = None
    if cur:
        runs.append(cur)
    def hh(t):
        return "%d%s" % (t.hour % 12 or 12, "a" if t.hour < 12 else "p")
    sunset = st_[1].astimezone(zone)
    return [("%s to %s" % (hh(a), hh(min(b + datetime.timedelta(hours=1), sunset)))) if a != b else hh(a) for a, b in runs], len(ok)


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
    return row[idx], when.strftime("%b %d").replace(" 0", " ")


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


def last_big_rise(G):
    """Days since the flow last rose 20% or more within 6 h (7-day series); None when no rise, -1 when the series is too short."""
    fl = G["fl"]
    if len(fl) < 12:
        return -1
    best = None
    for i in range(len(fl) - 1, 0, -1):
        t, v, _ = fl[i]
        lo = min((x[1] for x in fl if t - datetime.timedelta(hours=6) <= x[0] < t), default=None)
        if lo and lo > 0 and v >= 1.2 * lo:
            best = t
            break
    if best is None:
        return None
    return (G["lt"] - best).total_seconds() / 86400


def storm_line(G):
    """Lightning is the on-water danger that river levels do not show: the hours in the next 24 that the NWS hourly forecast calls thunderstorms, or an explicit 'none' (silence would read as fine). Text comes from the NWS short forecast, not from us."""
    n = G["rec"].get("nws") or {}
    hr = n.get("hourly") or []
    age = hours_old(n.get("hourly_updated"), G["now"]) if n.get("hourly_updated") else None
    if not hr or age is None:
        return ""
    if age > 12:
        return '<p class="storm warn">Thunderstorm outlook: the NWS hourly forecast for this location is %d h old, so hours with thunderstorms are not listed. Check weather.gov before going on the water.</p>' % age
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
    if not runs:
        return '<p class="storm ok">Thunderstorms: none in the National Weather Service forecast for the next %d hours.</p>' % len(nxt)
    when = "; ".join("%s to %s" % (tzl(a, G["zone"], date=(b - a) >= datetime.timedelta(hours=11)), tzl(b + datetime.timedelta(hours=1), G["zone"], date=(b - a) >= datetime.timedelta(hours=11))) if a != b else tzl(a, G["zone"], date=False) for a, b in runs)
    return '<p class="storm warn"><b>Thunderstorms in the forecast:</b> %s (gauge-local time).</p>' % esc(when)


def next_impact(G):
    """The next NWS impact statement above the latest reading, short, for the gage tile: the first thing a wader or boater wants to know about the level."""
    n = G["rec"].get("nwps") or {}
    im = n.get("impacts") or []
    if not im or not G["sg"]:
        return ""
    gap = datum_gap(G)
    cur = gap[0] if gap else G["sg"][-1][1]
    unit = (n.get("stage_units") or "ft").lower()
    ahead = sorted((i for i in im if isinstance(i.get("stage"), (int, float)) and i["stage"] > cur and len((i.get("statement") or "").strip()) >= 30), key=lambda i: i["stage"])
    if not ahead:
        return ""
    i = ahead[0]
    txt = i["statement"].strip()
    end = txt.find(". ")
    if 20 <= end < 160:
        txt = txt[:end + 1]
    elif len(txt) > 160:
        cut = txt.rfind(" ", 0, 157)
        txt = txt[:cut if cut > 40 else 157] + "\u2026"
    base = "Next NWS impact at %.1f %s (%.1f %s higher)" % (i["stage"], esc(unit), i["stage"] - cur, esc(unit))
    gr = gage_rate(G)  # time-to-flood: pure arithmetic from the rate of rise already on the page, labelled "at the current rate", no verdict
    if gr and gr > 0:
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


def b_sun(G):
    st = sun_times(G["lat"], G["lon"], G["ldate"])
    if not st:
        return None
    z = G["zone"]
    rows = tr(["Sunrise", esc(tzl(st[0], z, date=False))], right=(1,)) + tr(["Sunset", esc(tzl(st[1], z, date=False))], right=(1,))
    return block("sun", "Sun", "calc", table(["Event", "Time (gauge-local)"], rows, right=(1,)), "Source: computed from the gauge location and date %s. No external data." % G["ldate"].isoformat(), "usgs")


def nws_point_note(G):
    """When the NWS forecast point is named for another place than this gauge (Hudson River at Troy for the gauge at Green Island), say so: its flood stages and impact statements belong to that point."""
    n = G["rec"].get("nwps") or {}
    def norm(t):
        t = re.sub(r"\b(st|saint)\b\.?", "saint", (t or "").lower())
        t = re.sub(r"\bmt\b\.?", "mount", t)
        t = re.sub(r"\bft\b\.?", "fort", t)
        return re.sub(r"[^a-z0-9 ]", " ", t).split()
    nm, pl = norm(n.get("name")), norm(G["place"])
    if not nm or not pl:
        return ""
    if all(w in nm for w in pl):  # every word of the gauge's place is in the NWS name
        return ""
    return "The NWS links its forecast point %s to this USGS gauge but names it \u201c%s\u201d, for a nearby place. Its flood stages and impact statements are on the NWS stage scale; where the NWS and USGS read this gauge on different zero points, the margins below use the NWS reading." % (n.get("lid") or "", n.get("name"))
