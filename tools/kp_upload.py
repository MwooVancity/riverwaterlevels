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


def river_phrases(name):
    n = re.sub(r"\s+", " ", name.lower().replace("&", "and")).strip()
    n = re.sub(r"[^a-z0-9 '\-]", "", n)
    if not n:
        return []
    base = n if n.endswith(("river", "creek", "fork", "brook", "run", "bayou", "canal")) else n + " river"
    return [base + " level", base + " flow"]


def build(seeds, river_names, known):
    out, seen = [], set()
    def add(p, src):
        p = p.lower().strip()
        if p and p not in known and p not in seen:
            seen.add(p)
            out.append((p, src))
    for s in seeds:
        add(s, "ai-seed")
        if s.endswith(" water level"):
            add(s[: -len(" water level")] + " level", "ai-seed-variant")
    for r in river_names:
        for p in river_phrases(r):
            add(p, "queued-river")
    return out


def _selftest():
    assert river_phrases("Boise River") == ["boise river level", "boise river flow"]
    assert river_phrases("Fall Creek") == ["fall creek level", "fall creek flow"]
    assert river_phrases("Yampa") == ["yampa river level", "yampa river flow"]
    assert river_phrases("   ") == []
    r = build(["lake mead water level"], ["Boise River"], {"lake mead level"})
    assert [x[0] for x in r] == ["lake mead water level", "boise river level", "boise river flow"], r
    assert build(["a"], ["a"], {"a"}) == [("a river level", "queued-river"), ("a river flow", "queued-river")]
    print("kp_upload selftest OK")


def main():
    seeds = [l.strip() for l in open(os.path.join(D, "kp-seeds-ai-2026-11-22.txt"), encoding="utf-8") if l.strip()]
    names = {r["river"] for r in csv.DictReader(open(os.path.join(D, "world-queue.csv"), encoding="utf-8")) if r["gauge"] and r["river"]}
    names |= {r["river"] for r in csv.DictReader(open(os.path.join(D, "waves.csv"), encoding="utf-8")) if r["status"] == "queue" and "lake" not in r["signals"].split(",")}
    rows = build(seeds, sorted(names), have())
    out = os.path.join(D, "kp-upload")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "manifest.csv"), "w", newline="", encoding="utf-8") as m:
        w = csv.writer(m)
        w.writerow(["phrase", "batch", "source"])
        for i in range(0, len(rows), BATCH):
            chunk = rows[i:i + BATCH]
            n = i // BATCH + 1
            open(os.path.join(out, "batch-%02d.txt" % n), "w", encoding="utf-8").write("\n".join(p for p, _ in chunk) + "\n")
            w.writerows([[p, n, s] for p, s in chunk])
    print(len(rows), "phrases,", (len(rows) + BATCH - 1) // BATCH, "batches ->", out)


if __name__ == "__main__":
    _selftest() if "--selftest" in sys.argv else main()
