"""Hater review, step 2: record the reviewer's verdict for a gauge page (or `_template` for a code change), tied to the code it was made on.
Usage: python -I tools/review_sign.py <site|_template> PASS|FAIL "worst defects first, or 'none'" [--by NAME]
Writes state/reviews/<id>.json. The gate (check.py) refuses a build when a live gauge has no PASS, or when the page code changed since
the last PASS of `_template` (a sample of pages reviewed on the new code). A FAIL blocks until the defects are fixed and the page re-reviewed."""
import datetime, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lib.common import template_hash

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(args) < 3 or args[1] not in ("PASS", "FAIL"):
    sys.exit(__doc__)
rid, verdict, notes = args[0], args[1], args[2]
if rid != "_template" and not os.path.isdir(os.path.join(ROOT, ".cache", "review", rid)):
    sys.exit("no screenshots for %s: run node tools/hater_shots.mjs %s and LOOK at them first" % (rid, rid))
by = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--by=")), None) or (sys.argv[sys.argv.index("--by") + 1] if "--by" in sys.argv and sys.argv.index("--by") + 1 < len(sys.argv) else "reviewer")
_shot = os.path.join(ROOT, ".cache", "review", rid, "_code.txt")
if rid != "_template" and os.path.exists(_shot) and not open(_shot).read().startswith("remote") and open(_shot).read().strip() != template_hash():
    sys.exit("refused: the page code changed after %s was shot (shots on code %s, now %s): shoot it again and look again" % (rid, open(_shot).read().strip(), template_hash()))
os.makedirs(os.path.join(ROOT, "state", "reviews"), exist_ok=True)
rec = {"id": rid, "verdict": verdict, "notes": notes, "by": by, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "template": template_hash(), "level": next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--level=")), "full")}  # first = first screen + full text (owner 2026-10-28), full = every screenshot
json.dump(rec, open(os.path.join(ROOT, "state", "reviews", rid + ".json"), "w", encoding="utf-8"), indent=1)
open(os.path.join(ROOT, "state", "reviews", "_log.jsonl"), "a", encoding="utf-8").write(json.dumps(rec) + "\n")  # history: what haters found, for new gate rules
import shutil
shutil.rmtree(os.path.join(ROOT, ".cache", "review", rid), ignore_errors=True)  # signed: the screenshots are spent (about 5 MB a gauge); the verdict and findings live in _log.jsonl
print("signed", rid, verdict, "on code", rec["template"])
if verdict == "FAIL" and rid != "_template":
    # a failed page leaves the site now, not at the next deploy (flood site 2026-10-27: pages stayed live after a hater FAIL); release.py brings it back
    p = os.path.join(ROOT, "data", "waves.csv")
    s = open(p, encoding="utf-8", newline="").read()
    lines = s.splitlines(keepends=True)
    out = [("queue" + l[4:]) if l.startswith("live,") and l.split(",")[2] == rid else l for l in lines]
    if out != lines:
        open(p, "w", encoding="utf-8", newline="").write("".join(out))
        print("pulled", rid, "off the site (waves.csv live -> queue); bring it back with tools/release.py after a PASS")
