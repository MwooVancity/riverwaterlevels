"""Info gain (owner rule 5: no info gain, no page). Scores each built /lake/ and /coast/ page against the competitor items in data/competitors.json:
have (a mark of the item is on our page), none (the item's none_if reason holds: no open-terms source has it here) or missing.
A page missing a core item (the answer to the search) loses and is listed; the rest is the to-fill list, cheapest first.
Usage: python -I tools/info_gain.py [dist dir] [url ...]    Exit 1 when a page loses. score(html, kind) is what release.py page_check calls."""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMP = json.load(open(os.path.join(ROOT, "data", "competitors.json"), encoding="utf-8"))


def score(h, kind):
    """{'have': [...], 'none': [...], 'missing': [...], 'lost': [core items missing]} for one page's HTML."""
    out = {"have": [], "none": [], "missing": [], "lost": []}
    for it in COMP[kind]["items"]:
        if any(m in h for m in it["mark"]):
            out["have"].append(it["item"])
        elif it.get("none_if"):
            out["none"].append("%s (%s)" % (it["item"], it["none_if"]))
        else:
            out["missing"].append(it["item"])
            if it.get("core"):
                out["lost"].append(it["item"])
    return out


def kind_of(u):
    return "lake" if u.startswith("/lake/") else "coast" if u.startswith("/coast/") else None


def main():
    args = [a for a in sys.argv[1:]]
    d = next((a for a in args if not a.startswith("/")), os.path.join(ROOT, "dist_next"))
    urls = [a for a in args if a.startswith("/")] or [u for _, u, *_ in json.load(open(os.path.join(d, "live-sites.json"), encoding="utf-8")) if kind_of(u)]
    lost = 0
    for u in urls:
        p = os.path.join(d, u.strip("/").replace("/", os.sep), "index.html")
        if not os.path.exists(p) or not kind_of(u):
            print("%s: no built page" % u)
            continue
        s = score(open(p, encoding="utf-8").read(), kind_of(u))
        n = len(COMP[kind_of(u)]["items"])
        lost += bool(s["lost"])
        print("%s %s have %d/%d%s%s%s" % ("LOSES" if s["lost"] else "ok   ", u, len(s["have"]), n, "; missing: " + ", ".join(s["missing"]) if s["missing"] else "",
                                         "; none: " + ", ".join(s["none"]) if s["none"] else "", "; core missing: " + ", ".join(s["lost"]) if s["lost"] else ""))
    sys.exit(1 if lost else 0)


def selftest():
    good = {"lake": 'data-live="stage">677 id="stage_chart" <td>Full pool <td>Surface area</td> Wind mph</th> id="radar" id="access_points" Operated by',
            "coast": 'Next tide id="tides" NOAA predicted tide id="tide_table" Sunrise Moonrise Wind mph</th>'}
    for k, h in good.items():
        s = score(h, k)
        assert not s["lost"] and not s["missing"], (k, s)
        core = [it for it in COMP[k]["items"] if it.get("core")]
        assert core, "%s has no core item: nothing could ever lose" % k
        assert score("", k)["lost"] == [it["item"] for it in core], k
    loose = score("window.dataLayer Lake elevation is the water surface above the datum the operator uses; radar loop credit", "lake")
    assert "wind now and forecast" not in loose["have"] and "managing agency and its rules" not in loose["have"] and "current water-surface elevation" in loose["lost"], loose  # review #6: a bare word is no proof
    print("info_gain selftest OK")


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main()
