"""Small release rules with their own self-test (python -I tools/check_rules.py --selftest; run by gates.py)."""
import sys


def address_clash(rows, picks):
    """{site: reason} for each pick whose address already belongs to another live row or an earlier pick. Scale debate 2026-11-07: NOAA lists
    163 names shared by 380 tide stations (Long Beach x4); /coast/<place>/ with no suffix would let the second page overwrite the first."""
    taken = {r["url"]: r["site"] for r in rows if r.get("status") == "live" and r.get("url")}
    out = {}
    for r in picks:
        u = r.get("url")
        if u and u in taken and taken[u] != r["site"]:
            out[r["site"]] = "address %s already belongs to %s: give this one a -state or -place suffix in its csv row" % (u, taken[u])
        elif u:
            taken[u] = r["site"]
    return out


def selftest():
    rows = [{"site": "A", "status": "live", "url": "/coast/long-beach/"}, {"site": "B", "status": "queue", "url": "/coast/long-beach/"}]
    assert set(address_clash(rows, [{"site": "B", "url": "/coast/long-beach/"}])) == {"B"}, "a second Long Beach took the first one's address"
    assert set(address_clash([], [{"site": "C", "url": "/x/"}, {"site": "D", "url": "/x/"}])) == {"D"}, "two picks on one address"
    assert address_clash(rows[:1], [{"site": "A", "url": "/coast/long-beach/"}]) == {}, "a page's own address counted as a clash"
    print("check_rules selftest OK")


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else None
