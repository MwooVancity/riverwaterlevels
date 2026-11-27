"""Spain reservoir weekly history (MITECO Boletin Hidrologico, BD-Embalses). Pure parsing and the figures a page shows; no network.
Input is the CSV `mdb-export -D '%Y-%m-%d' BD-Embalses.mdb "T_Datos Embalses 1988-2026"` writes: AMBITO_NOMBRE, EMBALSE_NOMBRE, FECHA, AGUA_TOTAL,
AGUA_ACTUAL, ELECTRICO_FLAG; volumes are text in hm3 with a decimal comma. A blank or unreadable value is Unknown (None), never 0."""
import csv
import datetime
import statistics

NEED = ("AMBITO_NOMBRE", "EMBALSE_NOMBRE", "FECHA", "AGUA_TOTAL", "AGUA_ACTUAL")
STALE_DAYS = 15  # weekly bulletin: one missed week is shown as old, two make the current figure Unknown


def hm3(text):
    """'1505,00' or '1.505,00' -> 1505.0; blank, junk or negative -> None."""
    t = (text or "").strip()
    if not t:
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
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
        basin[n] = (r["AMBITO_NOMBRE"] or "").strip()
    return {n: [(d,) + v for d, v in sorted(rows.items())] for n, rows in out.items() if rows}, basin


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
    print("es_data selftest OK")


if __name__ == "__main__":
    selftest()
