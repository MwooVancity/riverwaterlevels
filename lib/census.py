"""Coverage census (plan 2026-11-05 step 1): every official site in a feed is built or held with a reason, so what our code cannot
build is a number in status.json, never a silent skip. collect.py fetch_census fetches; this file only counts (no network)."""

KIND = {"ST": "stage_only", "LK": "lake", "ES": "tidal", "OC": "tidal"}  # USGS site type of a level-only site
BUILDS = {"flow", "stage_only", "lake"}  # what our page builds (level-only through the ice path; lakes since 2026-11-05); tidal and ocean are the gap


def classify(flow, level, built):
    """flow: set of USGS site numbers with flow; level: {site: USGS site type} for sites with a level of any kind; built: set of live sites.
    Returns counts per kind plus built and code_cannot."""
    kinds = {s: "flow" for s in flow}
    for s, t in level.items():
        kinds.setdefault(s, KIND.get(t[:2], "stage_only"))
    out = {}
    for s, k in kinds.items():
        out[k] = out.get(k, 0) + 1
    out["built"] = sum(1 for s in kinds if s in built)
    out["code_cannot"] = sum(1 for k in kinds.values() if k not in BUILDS)
    return out


if __name__ == "__main__":
    c = classify({"1", "2"}, {"2": "ST", "3": "LK", "4": "ES", "5": "ST-CA"}, {"1"})
    assert c == {"flow": 2, "lake": 1, "tidal": 1, "stage_only": 1, "built": 1, "code_cannot": 1}, c
    print("census selftest OK")
