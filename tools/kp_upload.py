"""Build Keyword Planner upload batches (owner 2026-11-22: every river, lake and coast must have a Keyword Planner row).
Phrases: AI seed lists (ChatGPT + Gemini debate, MODEL_GUESS: only seeds, never ranks) + every queued river name x2 phrasings.
Skips phrases the keyword file already has (a zero is an answer, never re-asked). Batches of 1,500 (Planner fails silently near 9,900).
Writes data/kp-upload/batch-NN.txt (one phrase per line, paste or upload) and data/kp-upload/manifest.csv (phrase, batch, source).
Usage: python -I tools/kp_upload.py --selftest | python -I tools/kp_upload.py
"""
import csv, os, re, sys

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
BATCH = 1500


def have():
    return {r["keyword"].lower() for r in csv.DictReader(open(os.path.join(D, "keyword-tiers-water.csv"), encoding="utf-8"))}


def controls(tiers, per_band=4):
    """Phrases already answered, spread over every band: each batch repeats them, so a changed band flags a drifting run."""
    by = {}
    for k in sorted(tiers):
        by.setdefault(tiers[k], []).append(k)
    return [k for t in sorted(by) for k in by[t][:per_band]]


LOW = ("creek", "brook", "fork", "run")  # 0 of ~60 such names got a Planner band in the 2026-11-22 probe: kept apart, not deleted
JUNK = (" on ", "highway", "cutoff", "  ")


def low_confidence(name):
    n = name.lower().strip()
    return n.endswith(LOW) or any(j in n for j in JUNK) or bool(re.search(r"\d", n))


def river_phrases(name):
    n = re.sub(r"\s+", " ", name.lower().replace("&", "and")).strip()
    n = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 '\-]", "", n)).strip()
    if not n:
        return []
    base = n if n.endswith(("river", "creek", "fork", "brook", "run", "bayou", "canal", "lake", "reservoir")) else n + " river"
    return [base + " level", base + " flow"]


def build(seeds, river_names, known):
    out, seen = [], set()
    def add(p, src):
        p = p.lower().strip()
        if p and p not in known and p not in seen:
            seen.add(p)
            out.append((p, src))
    for s in seeds:
        add(s, "ai-seed")  # one phrasing per intent: 'X lake level' and 'X lake water level' got the same band in 3,221 of 3,531 file pairs
    for r in river_names:
        for p in river_phrases(r):
            add(p, "queued-river")
    return out


def _selftest():
    assert river_phrases("Boise River") == ["boise river level", "boise river flow"]
    assert river_phrases("Fall Creek") == ["fall creek level", "fall creek flow"]
    assert river_phrases("Yampa") == ["yampa river level", "yampa river flow"]
    assert river_phrases("   ") == []
    assert river_phrases("Richland-Chambers  Reservoir")[0] == "richland-chambers reservoir level"
    r = build(["lake mead water level"], ["Boise River"], {"lake mead level"})
    assert [x[0] for x in r] == ["lake mead water level", "boise river level", "boise river flow"], r
    assert len(controls({"a%d" % i: i % 5 * 5 for i in range(60)}, 2)) == 10, "2 control phrases per band"
    assert build(["a"], ["a"], {"a"}) == [("a river level", "queued-river"), ("a river flow", "queued-river")]
    assert low_confidence("Fall Creek") and low_confidence("Arkansas River on Highway 160") and low_confidence("Route 9 River")
    assert not low_confidence("Boise River") and not low_confidence("Yampa")
    print("kp_upload selftest OK")


def main():
    seeds = [l.strip() for l in open(os.path.join(D, "kp-seeds-ai-2026-11-22.txt"), encoding="utf-8") if l.strip()]
    names = {r["river"] for r in csv.DictReader(open(os.path.join(D, "world-queue.csv"), encoding="utf-8")) if r["gauge"] and r["river"]}
    names |= {r["river"] for r in csv.DictReader(open(os.path.join(D, "waves.csv"), encoding="utf-8")) if r["status"] == "queue" and "lake" not in r["signals"].split(",")}
    tiers = {r["keyword"].lower(): int(float(r["tier"] or 0)) for r in csv.DictReader(open(os.path.join(D, "keyword-tiers-water.csv"), encoding="utf-8"))}
    low = sorted(n for n in names if low_confidence(n))
    unk = os.path.join(D, "kp-unknown.txt")  # blank Planner rows: asked once, never again
    asked = set(tiers) | (set(open(unk, encoding="utf-8").read().split("\n")) if os.path.exists(unk) else set())
    rows = build(seeds, sorted(n for n in names if not low_confidence(n)), asked)
    ctl = controls(tiers)
    out = os.path.join(D, "kp-upload")
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, "low-confidence-names.txt"), "w", encoding="utf-8").write("\n".join(low) + "\n")
    with open(os.path.join(out, "manifest.csv"), "w", newline="", encoding="utf-8") as m:
        w = csv.writer(m)
        w.writerow(["phrase", "batch", "source", "known_band"])
        for i in range(0, len(rows), BATCH):
            chunk = rows[i:i + BATCH]
            n = i // BATCH + 1
            open(os.path.join(out, "batch-%02d.txt" % n), "w", encoding="utf-8").write("\n".join(ctl + [p for p, _ in chunk]) + "\n")
            w.writerows([[p, n, "control", tiers[p]] for p in ctl] + [[p, n, s, ""] for p, s in chunk])
    print(len(rows), "phrases,", (len(rows) + BATCH - 1) // BATCH, "batches ->", out)


if __name__ == "__main__":
    _selftest() if "--selftest" in sys.argv else main()
