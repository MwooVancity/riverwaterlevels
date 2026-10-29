"""River forecast, model guidance, impacts, alerts and crests."""
import statistics, os, re, json, math, collections, hashlib, datetime, zoneinfo
from lib.common import *
from lib.core import *
from lib.hero import *


def b_flood_stages(G):
    n = G["rec"].get("nwps") or {}
    cats = n.get("categories") or {}
    if not cats:
        return None
    rows = "".join(tr([k.capitalize(), "%.1f ft" % cats[k]], right=(1,)) for k in ("action", "minor", "moderate", "major") if k in cats)
    o = nws_stage(G)
    if o:
        rows += tr(["Latest NWS reading, %s" % esc(tzl(o[0], G["zone"])), "%.2f ft (%.1f ft below %s)" % (o[1], cats[min(cats, key=cats.get)] - o[1], min(cats, key=cats.get))], right=(1,)) if o[1] < min(cats.values()) else tr(["Latest NWS reading, %s" % esc(tzl(o[0], G["zone"])), "%.2f ft" % o[1]], right=(1,))
    return block("flood_stages", "Flood stages", "official", FLOOD_LEVELS + table(["Category", "Gage height (ft)"], rows, right=(1,)),
                 "Source: National Weather Service forecast point %s (%s), fetched %s. Compare with the gage height above; thresholds belong to that forecast point." % (esc(n.get("lid") or ""), esc(n.get("name") or ""), esc(tzl(parse_t(n["fetched_at"]), G["zone"]))), "nwps")


def b_river_forecast(G):
    n = G["rec"].get("nwps") or {}
    fc = n.get("forecast")
    if not fc or not fc.get("points"):
        return None
    age = hours_old(fc.get("issued"), G["now"]) if fc.get("issued") else None
    if age is not None and age > HIDE_H["river_forecast"]:
        return None
    rows = ""
    fut = [x for x in fc_points(fc) if x[0] >= G["now"]]  # same window as the forecast tile (hater r4: tile 11 PM, block 10 PM)
    if not fut:
        return None
    gap = datum_gap(G)
    keep = list(range(len(fut)))
    thin = ""
    if len(fut) > 48:
        step = max(2, (len(fut) - 24) // 24)
        top = max(range(len(fut)), key=lambda i: (fut[i][1] if fut[i][1] is not None else (fut[i][2] or 0)))
        val = lambda i: fut[i][1] if fut[i][1] is not None else (fut[i][2] or 0)
        days_ = collections.defaultdict(list)
        for i in range(len(fut)):
            days_[fut[i][0].astimezone(G["zone"]).date()].append(i)
        ext = {f_(ix, key=val) for ix in days_.values() for f_ in (max, min)}  # each day's high and low (hater r6: the list kept only the lows of a daily swing)
        keep = sorted(set(range(24)) | set(range(24, len(fut), step)) | {top, len(fut) - 1} | ext)
        thin = " After the first day the table shows about every %d hours; each day's highest and lowest forecast values and the last point are always included." % step
    runs = []  # consecutive points with the same printed values become one row "from - to" (Atlanta: 18 rows of 3.0 ft, 1,110 cfs)
    for t_, s_, f_ in [fut[i] for i in keep]:
        v_ = (("%.1f ft" % s_) if s_ is not None else "–", ("%s cfs" % fmtc(f_)) if f_ is not None else "–")
        if runs and runs[-1][2] == v_:
            runs[-1][1] = t_
        else:
            runs.append([t_, t_, v_])
    for a_, b_, v_ in runs:
        rows += tr([esc(tzl(a_, G["zone"])) + ((" to " + esc(tzl(b_, G["zone"]))) if b_ != a_ else "")] + list(v_), right=(1, 2))
    if gap:
        rows += tr(["NWS and USGS read this gauge on different zero points", "NWS %.2f ft at %s" % (gap[0], esc(tzl(gap[2], G["zone"], date=False))), "USGS %.2f ft at that time" % gap[1]], right=(1, 2))
    issued = esc(tzl(parse_t(fc["issued"]), G["zone"])) if fc.get("issued") else "time not stated"
    lead = ""
    pts_ = fc_points(fc)
    if pts_:
        near = min(pts_, key=lambda x: abs((x[0] - G["lt"]).total_seconds()))
        # not across zero points (gap) and not in a tidal reach, where one reading against a daily forecast says nothing (hater 2026-10-27, Freeport)
        if not gap and not G["osc"] and abs((near[0] - G["lt"]).total_seconds()) <= FC_NEAR_S and near[2] and G["lv"] and abs(near[2] - G["lv"]) > FC_OFF_REL * max(near[2], G["lv"]):
            lead = '<p class="src">At %s the NWS forecast flow is %s cfs; the USGS measured %s cfs at %s. %s</p>' % (esc(tzl(near[0], G["zone"], date=False)), fmtc(near[2]), fmtc(G["lv"]), esc(tzl(G["lt"], G["zone"], date=False)), ("The NWS forecast level for that time is %.1f ft against %.2f ft at the gauge, so the forecast itself starts off the reading." % (near[1], G["sg"][-1][1])) if (near[1] is not None and G["sg"] and abs(near[1] - G["sg"][-1][1]) > 0.2) else "The levels agree; the NWS converts level to flow with its own rating, which differs from the USGS rating here.")
    from lib.blocks3 import _fc_offset
    _o = _fc_offset(G, fut, "ft" if any(x[1] is not None for x in fut) else "cfs", gap)
    if _o:
        lead += '<p class="src">For %s the forecast was %s; the gauge reads %s now. Forecasts at gauges below dams and in tidal reaches can run out of step with the readings.</p>' % (esc(_o["t"]), esc(_o["f"]), esc(_o["c"]))
    if gap:
        lead += '<p class="src">These forecast levels are on the NWS scale, which reads %.2f ft %s than the USGS gage height at this gauge: add %.2f ft to compare them with the USGS readings above.</p>' % (abs(gap[1] - gap[0]), "lower" if gap[0] < gap[1] else "higher", gap[1] - gap[0])
    sel = [fut[i] for i in keep]
    top_i = max(range(len(sel)), key=lambda i: (round(sel[i][1], 1) if sel[i][1] is not None else 0, sel[i][2] or 0))  # w13: a later 3.3 ft 237 cfs card beat the "highest" 3.3 ft 235 cfs
    pick = list(range(len(sel))) if len(sel) <= 10 else sorted({round(k * (len(sel) - 1) / 9) for k in range(10)} | {top_i})  # whole span, not only the first hours
    _d = collections.defaultdict(list)
    for i in range(len(sel)):
        if sel[i][1] is not None:
            _d[sel[i][0].astimezone(G["zone"]).date()].append(i)
    if len(sel) > 10 and any(max(sel[i][1] for i in ix) - min(sel[i][1] for i in ix) >= 0.5 for ix in _d.values()):  # a daily swing: each day's high and low card (hater r7: the cards kept only the lows)
        pick = sorted({f_(ix, key=lambda i: sel[i][1]) for ix in list(_d.values())[:5] for f_ in (max, min)} | {top_i})  # at most 11 cards; the table holds every value
    pick.sort(key=lambda i: i != top_i)  # the highest forecast point is the first card
    _pr = lambda i: (("%.1f" % sel[i][1]) if sel[i][1] is not None else "", fmtc(sel[i][2]) if sel[i][2] is not None else "")
    run_ = [0]
    for i in range(1, len(sel)):
        run_.append(run_[-1] + (_pr(i) != _pr(i - 1)))
    _ends = {}
    for i, r_ in enumerate(run_):
        _ends.setdefault(r_, [i, i])[1] = i
    pick = sorted({_ends[run_[i]][0] for i in pick} | {_ends[run_[top_i]][0]})  # one card per run of identical printed values (w12 review: two cards for 18 identical values)
    top_i = _ends[run_[top_i]][0]
    _k = []
    for i in pick:  # a sampled card printing the same as the card before it says nothing new (Salmon: 1,160 cfs twice with 1,170 unshown between)
        if _k and _pr(i) == _pr(_k[-1]):
            if i == top_i:
                _k[-1] = i
            continue
        _k.append(i)
    pick = _k
    span_ = {a_: b_ for a_, b_ in _ends.values() if b_ != a_ and a_ in pick}
    if len(pick) < len(_ends):
        lead += '<p class="src">The cards show %d of the %d rows of this forecast, to %s; the table below lists every row.</p>' % (len(pick), len(_ends), esc(tzl(sel[-1][0], G["zone"])))
    fcards = []
    _hv = sel[top_i][1] if sel[top_i][1] is not None else sel[top_i][2]
    _cv = fc_cur(G, gap) if sel[top_i][1] is not None else G["lv"]
    _below = _hv is not None and _cv is not None and fc_cmp(_hv, _cv, "ft" if sel[top_i][1] is not None else "cfs") == "below"  # 1.7 ft forecast vs 1.68 ft reading is rounding, not "below" (full review)  # full review: a rising river showed "Highest forecast 3.2 ft" under a 3.52 ft reading
    lead = '<p class="src">NWS forecast issued %s.%s</p>' % (issued, " The latest reading is already above every forecast point." if _below else "") + lead + hydronotes_html(G)
    _flat = fc_word([x[1] if x[1] is not None else x[2] for x in sel], _cv, "ft" if sel[top_i][1] is not None else "cfs") != "high"  # no "Highest forecast" header unless the forecast rises above the reading  # every card the same level: no card is "highest" (hater 2026-10-27, Freeport: ten 102.5 ft cards)
    for i in pick:
        t_, s_, f_ = sel[i]
        main = ("%.1f <small>ft</small>" % s_) if s_ is not None else (("%s <small>cfs</small>" % fmtc(f_)) if f_ is not None else "–")
        subf = ("%s cfs" % fmtc(f_)) if (s_ is not None and f_ is not None) else ""
        fcards.append(card(("Highest forecast%s &middot; " % (" (below the latest reading)" if _below else "") if i == top_i and not _flat else "") + (("From %s to %s" % (esc(tzl(t_, G["zone"])), esc(tzl(sel[span_[i]][0], G["zone"])))) if i in span_ else esc(tzl(t_, G["zone"]))), main, subf, "crest" if i == top_i and not _flat else ""))
    if len(sel) > 1 and run_[-1] == 0:  # every value prints the same: one card (full review: nine identical "1.9 ft, 154 cfs" cards; w12: two cards)
        t_, s_, f_ = sel[pick[0]]
        fcards = [card("Every forecast value, %s to %s" % (esc(tzl(sel[0][0], G["zone"])), esc(tzl(sel[-1][0], G["zone"]))), ("%.1f <small>ft</small>" % s_) if s_ is not None else ("%s <small>cfs</small>" % fmtc(f_)), ("%s cfs" % fmtc(f_)) if (s_ is not None and f_ is not None) else "")]
    ftable = table(["Time (gauge-local)", "Gage height (NWS)", "Flow (NWS value)"], rows, right=(1, 2))
    return block("river_forecast", "NWS river forecast for %s" % n["name"] if n.get("name") else "NWS river forecast", "official", lead + rail(fcards, "River forecast points") + more(("All %d forecast values" % len(sel)) if len(runs) == len(keep) else ("All %d forecast values, in %d row%s (neighbouring equal values grouped)" % (len(sel), len(runs), "" if len(runs) == 1 else "s")), ftable),
                 "Source: National Weather Service forecast point %s, issued %s. Official forecasts change as rain and releases change. NWS flow values come from the NWS rating for its point and can differ from USGS flow readings.%s" % (esc(n.get("lid") or ""), issued, thin), "nwps", amber=age)


def b_nwm(G):
    if (G["rec"].get("nwps") or {}).get("forecast"):
        return None
    n = G["rec"].get("nwm") or {}
    pts = n.get("points") or []
    if len(pts) < 4:
        return None
    age = hours_old(n.get("reference_time"), G["now"]) if n.get("reference_time") else None
    if age is not None and age > HIDE_H["nwm_guidance"]:
        return None
    fut = [p for p in pts if parse_t(p["t"]) >= G["now"] - datetime.timedelta(hours=1)]
    if len(fut) < 4:
        return None
    rows = "".join(tr([esc(tzl(parse_t(p["t"]), G["zone"])), "%s cfs" % fmtc(sig3(p["flow"]))], right=(1,)) for p in fut[::3][:8])
    ref = esc(tzl(parse_t(n["reference_time"]), G["zone"])) if n.get("reference_time") else "time not stated"
    return block("nwm_guidance", "NOAA National Water Model, next %d hours" % round((parse_t(fut[::3][:8][-1]["t"]) - G["now"]).total_seconds() / 3600), "model", model_gap(G, fut[0]["flow"]) + table(["Time (gauge-local)", "Modeled flow"], rows, right=(1,)),
                 "Source: NOAA National Water Model, reach %s, run %s. Model guidance, not an official forecast and not a measurement." % (esc(str(n["comid"])) if isinstance(n.get("comid"), (int, str)) and str(n.get("comid")).strip() else "id not stated", ref), "nwm", amber=age)


def b_alerts(G):
    n = G["rec"].get("nws") or {}
    al = live_alerts(G)  # test messages and ended alerts left out
    zone = G["zone"]
    when = esc(tzl(parse_t(n["fetched_at"]), zone)) if n.get("fetched_at") else "time not stated"
    age = hours_old(n.get("fetched_at"), G["now"]) if n.get("fetched_at") else None
    if al is None:
        body = '<p>Alerts could not be loaded at the last fetch.</p>'
    elif not al and age is not None and age > stale_after("alerts"):
        body = '<p>Unknown: last NWS alert check %s ago; check weather.gov. This is not a statement that conditions are safe.</p>' % age_words(parse_t(n["fetched_at"]), G["now"])
    elif not al:
        body = '<p>No active National Weather Service alerts were returned for this location. This is not a statement that conditions are safe.</p>'
    else:
        items = ""
        for a in al:
            ends = esc(tzl(parse_t(a["ends"] or a["expires"]), zone)) if (a.get("ends") or a.get("expires")) else "not stated"
            items += '<div class="alert sev-%s"><b>%s</b> &middot; %s &middot; %s<br>%s%s</div>' % ((a.get("severity") or "unknown").lower(), esc(a.get("event") or ""), esc(a.get("severity") or "severity not stated"), esc(area_short(a.get("areaDesc") or "", 6, (((G["rec"].get("meta") or {}).get("loc")) or {}).get("county_name")) + ((" (" + ", ".join(a["states"]) + ")") if a.get("states") else "")), esc(a.get("headline") or ""), "" if re.search(r"\buntil\b", a.get("headline") or "", re.I) else ("<br>Ends " if a.get("ends") else "<br>NWS message valid until ") + ends)  # the NWS headline usually gives the end time; print it once
        body = items
    return block("alerts", "Weather alerts", "official", body, "Source: National Weather Service alerts for the gauge location, fetched %s." % when, "nws", amber=age, empty=(al == [] and not (age is not None and age > stale_after("alerts"))))


def crest_date(t, zone):
    if str(t).endswith("T00:00:00Z"):  # date-only value stored as midnight UTC: not a moment, so no zone shift
        return fdate(str(t)[:10])
    return fdate(parse_t(t).astimezone(zone).date().isoformat())


def b_crests(G):
    n = G["rec"].get("nwps") or {}
    cr = n.get("crests") or []
    if not cr:
        return None
    unit = (n.get("stage_units") or "ft").lower()
    rows = "".join(tr([crest_date(c["t"], G["zone"]) if c.get("t") else "–", "%.2f %s" % (c["stage"], esc(unit)), ("%s cfs" % fmtc(c["flow"])) if isinstance(c.get("flow"), (int, float)) and c["flow"] > 0 else "–"], right=(1, 2)) for c in cr)
    return block("historic_crests", "Historic crests", "official", table(["Date", "Crest stage", "Flow"], rows, right=(1, 2)),
                 "Source: National Weather Service forecast point %s (%s), historic crests as published by the NWS; the NWS may have recorded them on an older gauge datum. The USGS annual peaks above are a separate record and can differ in date, flow and datum." % (esc(n.get("lid") or ""), esc(n.get("name") or "")), "nwps")


def hydronotes_html(G):
    md = G["now"].strftime("%m%d")
    on = [h_["text"] for h_ in (G["rec"].get("nwps") or {}).get("hydronotes") or [] if not (h_.get("from") and h_.get("to")) or (h_["from"] <= md <= h_["to"] if h_["from"] <= h_["to"] else (md >= h_["from"] or md <= h_["to"]))]
    return "".join('<p class="src">NWS note for this point: \u201c%s\u201d</p>' % esc(demoji(t)) for t in on)


def _low_range(v):
    m = re.match(r"^\s*([\d,.]+)\s*(?:-|to)\s*([\d,.]+)\s*(k?cfs|ft)\b", v or "", re.I)
    if not m:
        return None
    k = 1000 if m.group(3).lower() == "kcfs" else 1
    try:
        return float(m.group(1).replace(",", "")) * k, float(m.group(2).replace(",", "")) * k, "ft" if m.group(3).lower() == "ft" else "cfs"
    except ValueError:
        return None


def _commas(v):
    return re.sub(r"\b\d{4,}\b", lambda m: "{:,}".format(int(m.group(0))), v or "")  # "1000-1500 cfs" beside "1,030 cfs" (w11 note)


def low_now(G):
    """(impact, reading) for the NWS low-water impact whose range holds the latest reading (a stage range is on the NWS scale: fc_cur), or None."""
    st = fc_cur(G, datum_gap(G))
    for i in (G["rec"].get("nwps") or {}).get("low_impacts") or []:
        r = _low_range(i["value"])
        cur = (G["lv"] if r[2] == "cfs" else st) if r else None
        if r and cur is not None and r[0] <= cur <= r[1]:
            return i, cur
    return None


def b_low_water(G):
    n = G["rec"].get("nwps") or {}
    li, lh = n.get("low_impacts") or [], n.get("low_hist") or []
    if not li and not lh:
        return None
    hit, hcur = low_now(G) or (None, None)
    out = ""
    if li:
        rows = "".join(tr([esc(_commas(i["value"])) + (" <b>(latest reading is in this range)</b>" if i is hit else ""), esc(demoji(i["impact"]))]) for i in li)
        out += ('<p class="src">The latest reading, %s, is in the NWS range %s.</p>' % (("%s cfs" % fmtc(hcur)) if _low_range(hit["value"])[2] == "cfs" else ("%.2f ft" % hcur), esc(_commas(hit["value"])))) if hit else ""
        out += table(["Level", "National Weather Service low-water statement"], rows)
    if lh:
        out += table(["Record low date", "Stage", "Flow"], "".join(tr([crest_date(c["t"], G["zone"]) if c.get("t") else "–", "%.2f %s" % (c["stage"], esc((n.get("stage_units") or "ft").lower())), ("%s cfs" % fmtc(c["flow"])) if isinstance(c.get("flow"), (int, float)) and c["flow"] > 0 else "–"], right=(1, 2)) for c in lh), right=(1, 2))
    return block("low_water", "Low-water levels", "official", out,
                 "Source: National Weather Service forecast point %s (%s), low-water impacts and historic low stages. Statements are quoted from the NWS." % (esc(n.get("lid") or ""), esc(n.get("name") or "")), "nwps")


def b_impacts(G):
    n = G["rec"].get("nwps") or {}
    im = n.get("impacts") or []
    if not im:
        return None
    unit = (n.get("stage_units") or "ft").lower()
    by = impact_list(G)
    if not by:
        return None
    flow_ = impact_flow(G)
    if flow_:
        unit = "cfs"
    fv = lambda v: ("%s cfs" % fmtc(v)) if flow_ else "%.1f %s" % (v, esc(unit))
    by = {k_: [demoji(x) for x in v_] for k_, v_ in by.items()}
    rows = "".join(tr([fv(s_), "<br>".join(esc(x) for x in by[s_])], right=(0,)) for s_ in sorted(by))
    pn = nws_point_note(G)
    gap_ = datum_gap(G)
    cur_ = impact_cur(G, gap_)  # the reading on the NWS scale (Memphis: no USGS stage, the NWS observes it; hater r8)
    if flow_:
        gap_, cur_ = None, G["lv"]
    _ref = ("NWS reading of %.2f %s" % (gap_[0], esc(unit))) if gap_ else "latest reading"
    _clash = scale_clash(G)
    if _clash is not None:
        gap_ = None
    _lead = ('<p class="src">The NWS stage reading here, %.2f %s, is on a different scale from the impact levels it publishes for this point, so no distance to them is given.</p>' % (_clash, esc(unit))) if _clash is not None else ('<p class="src">The NWS reads this gauge on a different zero point from USGS: %.2f %s at %s, when USGS read %.2f %s. The levels and distances below are on the NWS scale.</p>' % (gap_[0], esc(unit), esc(tzl(gap_[2], G["zone"], date=False)), gap_[1], esc(unit))) if gap_ else ""  # full review: Suwannee 54.34 vs 53.51 unexplained
    ss = sorted(by)
    below_ = [x for x in ss if cur_ is not None and x <= cur_]
    start = ss.index(below_[-1]) if below_ else 0
    icards, said_next = [], False
    for s_ in ss[start:start + 6]:
        txt = " / ".join(by[s_])
        short, cut = txt, False
        if len(txt) > 260:  # cut only at the end of a sentence and say so; never mid-sentence
            k = max([e for e in sent_ends(txt) if e < 260], default=-1)
            if k > 60 and txt[k - 1] != ".":
                short, cut = txt[:k + 1], True
        margin = "" if cur_ is None else ("reached at the %s" % _ref if s_ <= cur_ else "%s above the %s" % ((("%s cfs" % fmtd(s_ - cur_)) if flow_ else fv(r1(s_ - cur_))), _ref))
        if cut:
            margin = (margin + "; " if margin else "") + "rest of the statement in the full list below"
        reached = s_ <= (cur_ if cur_ is not None else -1e9)
        nxt_ = cur_ is not None and not reached and not said_next  # "Next" only on the first level above the reading (hater 2026-10-27: "NEXT:" on every card)
        said_next = said_next or nxt_
        icards.append(card(("Next impact at " if nxt_ else "At ") + fv(s_), esc(short), margin))
    itable = table(["Flow" if flow_ else "Stage", "National Weather Service impact statement"], rows, right=(0,))
    return block("flood_impacts", "Flood impacts by stage", "official", (('<p class="src">%s</p>' % esc(pn)) if pn else "") + _lead + rail(icards, "Flood impacts by stage") + more("All %d impact statements in full" % len(ss), itable),
                 "Source: National Weather Service forecast point %s (%s). Statements are quoted from the NWS and describe that forecast point." % (esc(n.get("lid") or ""), esc(n.get("name") or "")), "nwps")
