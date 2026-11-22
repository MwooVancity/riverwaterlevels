"""Merge a Keyword Planner 'Saved keywords' export (UTF-16 or UTF-8 tab file) into data/keyword-tiers-water.csv.
Rules (owner 2026-11-22, ChatGPT verdict): a band stays a band, a blank row is UNKNOWN (never a zero, never re-asked: data/kp-unknown.txt),
rows already in the file are never overwritten, the raw export is kept in data/kp-raw/. All-locations plan only (the 52,637-row file is worldwide).
Usage: python -I tools/kp_merge.py --selftest | python -I tools/kp_merge.py <export.csv>
"""
import csv, os, shutil, sys

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
FILE = os.path.join(D, "keyword-tiers-water.csv")


def kind(k):
    w = set(k.split())
    if w & {"tide", "tides", "surf", "wave", "waves"}:
        return "ocean"
    if w & {"lake", "reservoir", "loch", "dam"}:
        return "lake"
    return "river"


def parse(path):
    raw = open(path, "rb").read()
    txt = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig")
    rows = list(csv.reader(txt.splitlines(), delimiter="\t"))
    hi = next(i for i, r in enumerate(rows) if r and r[0] == "Keyword")
    out = []
    for r in rows[hi + 1:]:
        if len(r) < 4 or not r[0] or r[2] in ("All", "United States"):
            continue
        vol = int(float(r[3].replace(",", ""))) if r[3] else None
        bid = r[9] if len(r) > 9 and r[9] else ""
        out.append((r[0].lower().strip(), vol, bid))
    return out


def merge(rows, have):
    """Returns (new file rows, unknown keywords). A volume of 0 is an answer; a blank is unknown."""
    add, unknown = [], []
    for k, vol, bid in rows:
        if k in have:
            continue
        have.add(k)
        if vol is None:
            unknown.append(k)
        else:
            add.append({"keyword": k, "tier": vol, "bid_high_cad": bid, "kind": kind(k)})
    return add, unknown


def _selftest():
    add, unk = merge([("a river level", 500, "2.5"), ("b river level", None, ""), ("c lake level", 0, ""), ("old", 50, "")], {"old"})
    assert [a["keyword"] for a in add] == ["a river level", "c lake level"] and unk == ["b river level"], (add, unk)
    assert kind("x tide chart") == "ocean" and kind("x lake level") == "lake" and kind("x river flow") == "river"
    assert kind("lochsa river level") == "river" and kind("adams river level") == "river"
    print("kp_merge selftest OK")


def main(path):
    have = {r["keyword"].lower() for r in csv.DictReader(open(FILE, encoding="utf-8"))}
    unk = os.path.join(D, "kp-unknown.txt")
    if os.path.exists(unk):
        have |= set(open(unk, encoding="utf-8").read().split("\n"))
    add, unknown = merge(parse(path), have)
    os.makedirs(os.path.join(D, "kp-raw"), exist_ok=True)
    shutil.copy(path, os.path.join(D, "kp-raw", os.path.basename(path).replace(" ", "_")))
    with open(FILE, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, ["keyword", "tier", "bid_high_cad", "kind"], lineterminator="\n").writerows(add)
    with open(os.path.join(D, "kp-unknown.txt"), "a", encoding="utf-8") as f:
        f.write("".join(k + "\n" for k in unknown))
    print(len(add), "added,", len(unknown), "new unknown (blank)")


if __name__ == "__main__":
    _selftest() if "--selftest" in sys.argv else main(sys.argv[1])
