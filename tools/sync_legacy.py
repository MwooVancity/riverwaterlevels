"""Copy each live gauge's USGS daily-statistics files from the owner's PC data folder into the repo's legacy/.
CI builds from the repo, so a gauge whose file exists only on the PC loses "is this normal?" on the live site
(found 2026-10-25: 28 of 53 live gauges). release.py runs this after every wave. Usage: python -I tools/sync_legacy.py
"""
import csv, os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from lib.common import LEGACY

repo = os.path.join(ROOT, "legacy")
if os.path.normpath(LEGACY) == os.path.normpath(repo):
    sys.exit("LEGACY is the repo folder (no PC data folder here): nothing to sync")
live = [r["site"] for r in csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8")) if r["status"] == "live"]
copied, absent = 0, []
for kind in ("stats",):
    os.makedirs(os.path.join(repo, kind), exist_ok=True)
    for s in live:
        src, dst = os.path.join(LEGACY, kind, s + ".json"), os.path.join(repo, kind, s + ".json")
        if os.path.exists(dst):
            continue
        if os.path.exists(src):
            shutil.copy2(src, dst)
            copied += 1
        else:
            absent.append("%s/%s" % (kind, s))
print("copied %d files into legacy/; not on the PC either: %s" % (copied, ", ".join(absent) or "none"))
