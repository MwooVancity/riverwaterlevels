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
# a gauge whose build failed keeps its previous page: copied in BEFORE the checks so no link to it breaks
import json
try:
    failed_urls = json.load(open(os.path.join(N, "status.json"), encoding="utf-8")).get("failed_urls") or []
except Exception:
    failed_urls = []
kept = []
for u in failed_urls:
    old, new_ = os.path.join(D, u.strip("/"), "index.html"), os.path.join(N, u.strip("/"), "index.html")
    if os.path.isfile(old) and not os.path.exists(new_):
        os.makedirs(os.path.dirname(new_), exist_ok=True)
        shutil.copy2(old, new_)
        kept.append(u)
if kept:  # the carried pages keep their sitemap entry and their place in _urls.json, so the checks see the same page set the live site has
    import re
    try:
        sm_old = open(os.path.join(D, "sitemap.xml"), encoding="utf-8").read()
        sm_new = open(os.path.join(N, "sitemap.xml"), encoding="utf-8").read()
        for u in kept:
            m = re.search(r"<url><loc>[^<]*%s</loc>.*?</url>" % re.escape(u), sm_old)
            if m and m.group(0) not in sm_new:
                sm_new = sm_new.replace("</urlset>", m.group(0) + "</urlset>")
        open(os.path.join(N, "sitemap.xml"), "w", encoding="utf-8").write(sm_new)
    except OSError:
        pass
    uj = os.path.join(N, "_urls.json")
    if os.path.isfile(uj):
        d_ = json.load(open(uj, encoding="utf-8"))
        d_["urls"] = d_["urls"] + [u for u in kept if u not in d_["urls"]]
        json.dump(d_, open(uj, "w", encoding="utf-8"))
if kept:
    print("kept the previous page (before the checks, so links to it stay valid) for %d gauge(s) whose build failed: %s" % (len(kept), ", ".join(kept[:5])))
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
rv = os.path.join(ROOT, "data", "reviews.json")
new = unreviewed_new_pages(urls(N), urls(D), json.load(open(rv, encoding="utf-8")) if os.path.exists(rv) else {}) if os.path.isdir(D) else []
if new:
    sys.exit("NEW PAGES NOT REVIEWED: %d new gauge page(s) have no SHIP verdict in data/reviews.json (e.g. %s). Run the review in docs/REVIEW-PROMPT.md first. Release NOT published, dist/ unchanged." % (len(new), ", ".join(new[:3])))
shutil.rmtree(P, ignore_errors=True)
if os.path.isdir(D):
    os.rename(D, P)
os.rename(N, D)
print("published: dist/ updated, previous release kept in dist_prev/")
