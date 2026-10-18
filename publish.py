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
shutil.rmtree(P, ignore_errors=True)
if os.path.isdir(D):
    os.rename(D, P)
os.rename(N, D)
print("published: dist/ updated, previous release kept in dist_prev/")
