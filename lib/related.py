"""Upstream/downstream gauges are found by the USGS NLDI from each gauge's side, so A can list B while B does not list A. This closes the relation for gauges that are both on the site:
if A lists B as upstream, B gets A as downstream (and the other way round), with A's own latest flow and time. A measured lag is copied across. Nothing is invented: the pair comes from the same NLDI answer."""
from lib.common import dir_lv

INV = {"upstream": "downstream", "downstream": "upstream"}


def close(Gs, iso):
    added = 0
    for a, G in Gs.items():
        for x in (G["rec"].get("related") or {}).get("items") or []:
            b = x["site"]
            if b not in Gs or b == a:
                continue
            rel = Gs[b]["rec"].setdefault("related", {"items": []})
            items = rel.setdefault("items", [])
            if any(y["site"] == a for y in items):
                continue
            row = {"site": a, "relation": INV[x["relation"]], "flow": dir_lv(G), "time": iso(G["lt"])}
            for k in ("lag_h", "lag_r"):
                if x.get(k) is not None:
                    row[k] = x[k]
            items.append(row)
            added += 1
    return added


def check(Gs):
    """Returns the pairs that are still one-sided (must be empty after close())."""
    bad = []
    for a, G in Gs.items():
        for x in (G["rec"].get("related") or {}).get("items") or []:
            b = x["site"]
            if b in Gs and not any(y["site"] == a and y["relation"] == INV[x["relation"]] for y in (Gs[b]["rec"].get("related") or {}).get("items") or []):
                bad.append((a, b))
    return bad
