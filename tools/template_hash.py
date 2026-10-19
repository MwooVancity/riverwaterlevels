"""Hash of everything that decides how a page looks and what it says (lib/, templates/, build.py). A review verdict in data/reviews.json belongs to one hash.
Usage: python tools/template_hash.py            prints the hash
       python tools/template_hash.py --check    exit 1 and print TEMPLATE NOT REVIEWED when the current hash has no SHIP entry"""
import hashlib, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def template_hash():
    h = hashlib.sha256()
    files = [os.path.join(ROOT, "build.py")]
    for sub in ("lib", "templates"):
        d = os.path.join(ROOT, sub)
        files += [os.path.join(d, f) for f in sorted(os.listdir(d)) if os.path.isfile(os.path.join(d, f))]
    for f in files:
        h.update(os.path.relpath(f, ROOT).encode())
        h.update(open(f, "rb").read().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:16]


def main():
    cur = template_hash()
    print(cur)
    if "--check" in sys.argv:
        p = os.path.join(ROOT, "data", "reviews.json")
        rv = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
        if rv.get("templates", {}).get(cur, {}).get("verdict") != "SHIP":
            print("TEMPLATE NOT REVIEWED: no SHIP verdict for template %s (see docs/REVIEW-PROMPT.md)" % cur)
            return 1
    return 0


sys.exit(main())
