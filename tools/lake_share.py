"""Daily lake share for tools/release.py (PLAN.md DECIDED 2026-11-21: lakes first, 5-10 a day of the 25, a guess).
lake_first(both, cap) puts at most `cap` lake rows at the front of the money order; the rest keep their order, so the day's cut at N stays N.
A row is (-money, kind, i, row); kind 1 = US row. A lake row has 'lake' in its signals. Practice-gated rows are never picked by the real release.
LAKE_FIRST is 25 since owner 2026-11-21 (was 5-10): while lakes are queued all of a day's 25 are lakes.
Usage: python -I tools/lake_share.py --selftest
"""
import sys

LAKE_FIRST = 25  # owner 2026-11-21: "raise it 25 a day" (was 8, a ChatGPT guess); all 25 daily slots go to lakes while lakes are queued, other rows fill what lakes cannot


def is_lake(x):
    return x[1] == 1 and "lake" in (x[3].get("signals") or "").split(",")


def lake_first(both, cap=LAKE_FIRST):
    both = [x for x in both if (x[3].get("gate") or "") != "practice"]
    if not cap:  # cap 0 = pure money order (owner 2026-11-22: Keyword Planner decides, rivers and lakes together)
        return both
    lakes = [x for x in both if is_lake(x)]  # money order kept: keyword tier x ad rate
    others = [x for x in both if not is_lake(x)]
    return lakes[:cap] + others + lakes[cap:]  # surplus lakes only fill slots the other rows cannot


def _selftest():
    def row(i, kind, sig="", gate="", money=0):
        return (money, 1, i, {"site": "%s%d" % (kind, i), "signals": sig, "gate": gate})
    def site_list(rows):
        return [x[3]["site"] for x in rows]
    n = 25
    rivers = [row(i, "r", money=-100 + i) for i in range(30)]
    lakes = [row(i, "l", "lake", money=-50 + i) for i in range(30)]
    both = sorted(rivers + lakes, key=lambda x: x[:3])
    top = lake_first(both)[:n]
    assert sum(is_lake(x) for x in top) == 25 and len(top) == n and sum(not is_lake(x) for x in top) == 0, "30 lakes + 30 rivers: 25 lakes, 0 others"
    assert [x for x in top if not is_lake(x)] == [x for x in both if not is_lake(x)][:0], "non-lake order unchanged"
    wide = lake_first(both)[:30]
    assert [x for x in wide if not is_lake(x)] == [x for x in both if not is_lake(x)][:5] and sum(is_lake(x) for x in wide) == 25, "N=30: 25 lakes then the rivers in their own order"
    few = sorted(rivers + lakes[:3], key=lambda x: x[:3])
    top = lake_first(few)[:n]
    assert sum(is_lake(x) for x in top) == 3 and len(top) == n and sum(not is_lake(x) for x in top) == 22, "3 lakes: 3 lakes + 22 others"
    only = lake_first(lakes)[:n]
    assert len(only) == n, "only lakes queued: surplus lakes fill the day"
    gated = row(99, "g", "lake", gate="practice", money=-1000)
    assert "g99" not in site_list(lake_first(sorted(both + [gated], key=lambda x: x[:3]))), "practice-gated lake never picked"
    by_tier = [row(1, "a", "lake", money=-5), row(2, "b", "lake", money=-500), row(3, "c", "lake", money=-50)]
    assert site_list(lake_first(sorted(by_tier, key=lambda x: x[:3]))) == ["b2", "c3", "a1"], "lake share ordered by tier"
    assert site_list(lake_first(sorted(rivers + lakes, key=lambda x: x[:3]), 0)) == site_list(sorted(rivers + lakes, key=lambda x: x[:3])), "cap 0 keeps pure money order"
    world = (-9999, 0, 0, {"site": "w", "signals": "lake"})
    assert not is_lake(world) and lake_first([world])[0] is world, "a world row is not a US lake row and keeps its place"
    print("lake_share selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
