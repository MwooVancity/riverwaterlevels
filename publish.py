"""Atomic publish with rollback. Usage: python -I publish.py   (checks dist_next, then swaps)   |   python -I publish.py --rollback
dist/ is the live release, dist_prev/ the previous one. Nothing is published if any check fails.
"""
import os, sys, shutil, subprocess
ROOT = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))
D, N, P = (os.path.join(ROOT, x) for x in ("dist", "dist_next", "dist_prev"))

if "--rollback" in sys.argv:
    if not os.path.isdir(P):
        sys.exit("no previous release")
    tmp = D + "_swap"
    os.rename(D, tmp); os.rename(P, D); os.rename(tmp, P)
    print("rolled back: dist is the previous release")
    sys.exit(0)
if not os.path.isdir(N):
    sys.exit("nothing to publish: run build.py first")
rc = subprocess.call([sys.executable, "-I", os.path.join(ROOT, "check.py"), N])
if rc:
    sys.exit("checks failed: release NOT published, dist/ unchanged")
# new gauge pages need a recorded SHIP verdict from a fresh-brain reader review (docs/REVIEW-PROMPT.md); pages already live are never blocked
sys.path.insert(0, ROOT)
from lib.reviewgate import unreviewed_new_pages
import json
def urls(d):
    f = os.path.join(d, "_urls.json")
    return json.load(open(f))["urls"] if os.path.exists(f) else []
rv = os.path.join(ROOT, "state", "reviews.json")
new = unreviewed_new_pages(urls(N), urls(D), json.load(open(rv, encoding="utf-8")) if os.path.exists(rv) else {}) if os.path.isdir(D) else []
if new:
    sys.exit("NEW PAGES NOT REVIEWED: %d new gauge page(s) have no SHIP verdict in state/reviews.json (e.g. %s). Run the review in docs/REVIEW-PROMPT.md first. Release NOT published, dist/ unchanged." % (len(new), ", ".join(new[:3])))
shutil.rmtree(P, ignore_errors=True)
if os.path.isdir(D):
    os.rename(D, P)
os.rename(N, D)
print("published: dist/ updated, previous release kept in dist_prev/")
