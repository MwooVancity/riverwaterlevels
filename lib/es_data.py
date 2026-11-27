"""Spain reservoir weekly history (MITECO Boletin Hidrologico, BD-Embalses). Pure parsing and the figures a page shows; no network.
Input is the CSV `mdb-export -D '%Y-%m-%d' BD-Embalses.mdb "T_Datos Embalses 1988-2026"` writes: AMBITO_NOMBRE, EMBALSE_NOMBRE, FECHA, AGUA_TOTAL,
AGUA_ACTUAL, ELECTRICO_FLAG; volumes are text in hm3 with a decimal comma. A blank or unreadable value is Unknown (None), never 0."""
import csv
import datetime
import re
import statistics

NEED = ("AMBITO_NOMBRE", "EMBALSE_NOMBRE", "FECHA", "AGUA_TOTAL", "AGUA_ACTUAL")
MIN_ROWS = 500  # first sight of a reservoir: the real ranked 50 have 1,052 to 2,030 weeks (file of 2026-11-24)
STALE_DAYS = 15  # weekly bulletin: a reading older than this is marked old and the later fill is called unknown
SPIKE = 25.0  # percentage points of capacity


def hm3(text):
    """'1505,00' or '1.505,00' -> 1505.0; blank, junk or negative -> None."""
    t = (text or "").strip()
    if not t:
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", t):  # '1.505' with no comma: thousands or a decimal point, so Unknown
        return None
    try:
        v = float(t)
    except ValueError:
        return None
    return v if 0 <= v < 100000 else None


def parse(lines, names):
    """{name: [(date, capacity, volume)] oldest first} for the wanted names. A changed header raises: the old pages then stay live."""
    rd = csv.DictReader(lines)
    missing = [c for c in NEED if c not in (rd.fieldnames or [])]
    if missing:
        raise ValueError("BD-Embalses columns changed, missing %s" % ", ".join(missing))
    out, basin = {n: {} for n in names}, {}
    for r in rd:
        n = (r["EMBALSE_NOMBRE"] or "").strip()
        if n not in out:
            continue
        try:
            d = datetime.date.fromisoformat((r["FECHA"] or "")[:10])
        except ValueError:
            continue
        out[n][d] = (hm3(r["AGUA_TOTAL"]), hm3(r["AGUA_ACTUAL"]))  # one row per date: a repeated date keeps the last
        b = (r["AMBITO_NOMBRE"] or "").strip()
        if basin.setdefault(n, b) != b:  # two reservoirs with one name would mix their weeks
            raise ValueError("%s is listed in two basins, %s and %s" % (n, basin[n], b))
    return {n: [(d,) + v for d, v in sorted(rows.items())] for n, rows in out.items() if rows}, basin


def pack(data, basin):
    """The cache file's data part: {"newest", "basin", "rows": {name: [[iso, capacity, volume]]}}. About 28 bytes a week a reservoir."""
    return {"newest": max((r[-1][0] for r in data.values()), default=datetime.date.min).isoformat(), "basin": basin,
            "rows": {n: [[d.isoformat(), c, v] for d, c, v in r] for n, r in data.items()}}


def unpack(cache):
    """The cache file back to what parse() returns: ({name: [(date, capacity, volume)]}, {name: basin})."""
    return {n: held([(datetime.date.fromisoformat(d), c, v) for d, c, v in r]) for n, r in cache["rows"].items()}, cache["basin"]


def held(rows):
    """A one-week jump over SPIKE that reverses the next week (La Serena 1324, 13, 1322 hm3, Oct 2018) is a source error: that volume becomes Unknown.
    ponytail: the newest week has no next week yet, so it cannot be held; the page notes a large last-week change instead."""
    out = list(rows)
    for i in range(1, len(rows) - 1):
        a, m, z = (pct(r[1], r[2]) for r in rows[i - 1:i + 2])
        if None not in (a, m, z) and (rows[i + 1][0] - rows[i - 1][0]).days <= 21 and min(abs(m - a), abs(m - z)) > SPIKE and (m - a) * (m - z) > 0:
            out[i] = (rows[i][0], rows[i][1], None)
    return out


def refusal(new, old, names, today):
    """Why a freshly packed file must NOT replace the cache, or None. `old` is the cache in use, None on the first run."""
    gone = sorted(set(names) - set(new["rows"]))
    if gone:
        return "%d of %d reservoirs missing: %s" % (len(gone), len(names), ", ".join(gone[:5]))
    if new["newest"] > (today + datetime.timedelta(days=1)).isoformat():
        return "a reading is dated in the future (%s)" % new["newest"]
    if old and new["newest"] < old["newest"]:
        return "newest date %s is older than the stored %s" % (new["newest"], old["newest"])
    for n in sorted(names):
        rows, was = new["rows"][n], (old or {}).get("rows", {}).get(n)
        if was and (rows[-1][0] < was[-1][0] or len(rows) < len(was) - 4):  # 4: room for the agency removing a few bad weeks
            return "%s lost weeks: now %d to %s, stored %d to %s (cut-short file?)" % (n, len(rows), rows[-1][0], len(was), was[-1][0])
        if not was and len(rows) < MIN_ROWS:
            return "%s has only %d weeks (cut-short file?)" % (n, len(rows))
    return None


def pct(cap, vol):
    """Percent full against that row's own capacity; None when either is unknown or the volume is over capacity by more than 5% (a wrong row)."""
    if vol is None or not cap or vol > cap * 1.05:
        return None
    return 100.0 * vol / cap


def near(rows, day, window=4):
    """The row closest to `day` within `window` days, with a usable percent."""
    c = [r for r in rows if abs((r[0] - day).days) <= window and pct(r[1], r[2]) is not None]
    return min(c, key=lambda r: abs((r[0] - day).days)) if c else None


def year_back(d, k):
    try:
        return d.replace(year=d.year - k)
    except ValueError:  # 29 February
        return d.replace(year=d.year - k, day=28)


def figures(rows, today):
    """What a page shows for one reservoir, or None when no usable reading exists. `stale` past STALE_DAYS: the page must not call the figure current."""
    good = [r for r in rows if r[0] <= today and pct(r[1], r[2]) is not None]
    if not good:
        return None
    d, cap, vol = good[-1]
    now = pct(cap, vol)
    past = [pct(r[1], r[2]) for r in (near(good, year_back(d, k)) for k in range(1, d.year - good[0][0].year + 1)) if r]

    def change(days):
        r = near(good, d - datetime.timedelta(days=days))
        return None if r is None else now - pct(r[1], r[2])

    prior = near(good, year_back(d, 1))
    return {"date": d, "capacity": cap, "volume": vol, "pct": now, "stale": (today - d).days > STALE_DAYS,
            "week_change": change(7), "month_change": change(28), "last_year": None if prior is None else pct(prior[1], prior[2]),
            "years": len(past), "median": statistics.median(past) if len(past) >= 10 else None,
            "low": min(past) if len(past) >= 10 else None, "high": max(past) if len(past) >= 10 else None,
            "below": sum(1 for p in past if p < now) if len(past) >= 10 else None}


def monthly(rows, last_year):
    """Month by month over the 10 whole years before `last_year`: [(month, median, low, high, years)] of each year's median fill in that month.
    None unless every month has at least 8 of those years: a short or gappy record gives no 'usual year'."""
    got = {}
    for d, c, v in rows:
        p = pct(c, v)
        if p is not None and last_year - 10 <= d.year < last_year:
            got.setdefault((d.month, d.year), []).append(p)
    out = []
    for m in range(1, 13):
        ys = [statistics.median(v) for (mm, _), v in got.items() if mm == m]
        if len(ys) < 8:
            return None
        out.append((m, statistics.median(ys), min(ys), max(ys), len(ys)))
    return out


def selftest():
    head = "AMBITO_NOMBRE,EMBALSE_NOMBRE,FECHA,AGUA_TOTAL,AGUA_ACTUAL,ELECTRICO_FLAG"
    rows = [head] + ['Tajo,A,%d-11-24,"1.000,00","%d,00",0' % (y, 100 + (y - 2000) * 10) for y in range(2000, 2027)]
    rows += ['Tajo,A,2026-11-17,"1.000,00","350,00",0', 'Tajo,A,2026-12-01,"1.000,00",,0', 'Tajo,B,2026-11-24,"10,00","50,00",0', 'Tajo,A,bad,"1,00","1,00",0']
    data, basin = parse(rows, {"A", "B", "C"})
    assert set(data) == {"A", "B"} and basin["A"] == "Tajo"
    f = figures(data["A"], datetime.date(2026, 12, 2))
    assert f["date"] == datetime.date(2026, 11, 24) and f["capacity"] == 1000 and f["volume"] == 360, "the blank newest row must not read as 0"
    assert round(f["pct"], 1) == 36.0 and round(f["week_change"], 1) == 1.0 and round(f["last_year"], 1) == 35.0 and f["years"] == 26 and f["below"] == 26 and not f["stale"]
    assert figures(data["A"], datetime.date(2026, 12, 20))["stale"], "an old reading was not marked stale"
    assert figures(data["B"], datetime.date(2026, 12, 2)) is None, "a volume five times the capacity was shown"
    assert hm3("") is None and hm3("x") is None and hm3("-1,00") is None and hm3("0,00") == 0.0 and hm3("1.505,50") == 1505.5
    assert year_back(datetime.date(2028, 2, 29), 1) == datetime.date(2027, 2, 28)
    short = figures(data["A"][-5:], datetime.date(2026, 12, 2))
    assert short["median"] is None and short["below"] is None, "fewer than 10 past years must give no 'normal'"
    try:
        parse(["a,b", "1,2"], {"A"})
    except ValueError:
        pass
    else:
        raise AssertionError("a changed file format passed")
    today = datetime.date(2026, 12, 2)
    weeks = [(datetime.date(2026, 11, 24) - datetime.timedelta(weeks=k), 10.0, None if k == 1 else 5.0) for k in range(600, -1, -1)]
    old = pack({"A": weeks, "B": weeks}, {"A": "Tajo", "B": "Ebro"})
    assert unpack(old)[0]["A"] == weeks and old["newest"] == "2026-11-24"
    assert refusal(old, None, {"A", "B"}, today) is None and refusal(old, old, {"A", "B"}, today) is None
    for bad, was in ((pack({"A": weeks}, {}), old), (pack({}, {}), old), (pack({"A": weeks[:-1], "B": weeks[:-1]}, {}), old), (pack({"A": weeks, "B": weeks[:-1]}, {}), old),
                     (pack({"A": weeks[10:], "B": weeks}, {}), old), (pack({"A": weeks[-100:], "B": weeks}, {}), None)):
        assert refusal(bad, was, {"A", "B"}, today), "a bad file would have replaced the cache"
    assert refusal(old, None, {"A", "B"}, datetime.date(2026, 11, 1)), "a future date passed"
    try:
        parse([head, 'Tajo,A,2026-11-24,"1,00","1,00",0', 'Ebro,A,2026-11-17,"1,00","1,00",0'], {"A"})
    except ValueError:
        pass
    else:
        raise AssertionError("one name in two basins was merged")
    w = [(datetime.date(2018, 10, d), 3219.0, v) for d, v in ((2, 1330.0), (9, 1324.0), (16, 13.0), (23, 1322.0))]
    assert [r[2] for r in held(w)] == [1330.0, 1324.0, None, 1322.0], "the La Serena spike was published"
    assert held(w[:3]) == w[:3] and hm3("1.505") is None
    wk = [(datetime.date(y, m, 15), 100.0, float(20 + m)) for y in range(2016, 2026) for m in range(1, 13)]
    mo = monthly(wk + [(datetime.date(2026, 1, 15), 100.0, 99.0), (datetime.date(2015, 1, 15), 100.0, 99.0)], 2026)
    assert mo[0] == (1, 21.0, 21.0, 21.0, 10) and mo[11][1] == 32.0, "the running year or an 11th year got into the usual year"
    assert monthly([r for r in wk if not (r[0].month == 7 and r[0].year < 2019)], 2026) is None, "a month with 7 years gave a usual year"
    print("es_data selftest OK")


if __name__ == "__main__":
    selftest()
