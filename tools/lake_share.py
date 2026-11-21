"""Daily lake share for tools/release.py (PLAN.md DECIDED 2026-11-21: lakes first, 5-10 a day of the 25, a guess).
lake_first(both, cap) puts at most `cap` lake rows at the front of the money order; the rest keep their order, so the day's cut at N stays N.
A row is (-money, kind, i, row); kind 1 = US row. A lake row has 'lake' in its signals. Practice-gated rows are never picked by the real release.
Usage: python -I tools/lake_share.py --selftest
"""
import sys

LAKE_FIRST = 8  # ChatGPT 2026-11-21: start at 5-10 a day; a guess, raise it only when the lake cohort numbers (PLAN.md) hold


def is_lake(x):
    return x[1] == 1 and "lake" in (x[3].get("signals") or "").split(",")


def lake_first(both, cap=LAKE_FIRST):
    both = [x for x in both if (x[3].get("gate") or "") != "practice"]
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
    assert sum(is_lake(x) for x in top) == 8 and len(top) == n and sum(not is_lake(x) for x in top) == 17, "30 lakes + 30 rivers: 8 lakes, 17 others"
    assert [x for x in top if not is_lake(x)] == [x for x in both if not is_lake(x)][:17], "non-lake order unchanged"
    few = sorted(rivers + lakes[:3], key=lambda x: x[:3])
    top = lake_first(few)[:n]
    assert sum(is_lake(x) for x in top) == 3 and len(top) == n and sum(not is_lake(x) for x in top) == 22, "3 lakes: 3 lakes + 22 others"
    only = lake_first(lakes)[:n]
    assert len(only) == n, "only lakes queued: surplus lakes fill the day"
    gated = row(99, "g", "lake", gate="practice", money=-1000)
    assert "g99" not in site_list(lake_first(sorted(both + [gated], key=lambda x: x[:3]))), "practice-gated lake never picked"
    by_tier = [row(1, "a", "lake", money=-5), row(2, "b", "lake", money=-500), row(3, "c", "lake", money=-50)]
    assert site_list(lake_first(sorted(by_tier, key=lambda x: x[:3]))) == ["b2", "c3", "a1"], "lake share ordered by tier"
    world = (-9999, 0, 0, {"site": "w", "signals": "lake"})
    assert not is_lake(world) and lake_first([world])[0] is world, "a world row is not a US lake row and keeps its place"
    print("lake_share selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
