"""Fetches live pages on the real domain and reports status, noindex header, flow value, title. Usage: python -I livecheck.py [url ...]
Exit 1 if a page is not 200 or shows no flow value, so refresh.py stops and logs it."""
import sys, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.common import http_open

DEFAULT = ["https://riverwaterlevels.com/river/missouri-river-mo/kansas-city/", "https://riverwaterlevels.com/river/kinzua-creek/guffey/"]
bad = 0
for u in (sys.argv[1:] or DEFAULT):
    try:
        r = http_open(u, {"User-Agent": "livecheck"}, 30)
        h = r.read().decode("utf-8", "ignore")
        t = re.search(r"<title>(.*?)</title>", h)
        fl = re.search(r"Latest flow</span><b>(.*?)<small>", h, re.S)
        flow = re.sub(r"<[^>]+>", "", fl.group(1)).strip() if fl else None
        print(r.status, u.split("/")[2], "| x-robots:", r.headers.get("x-robots-tag"), "| flow:", flow, "|", (t.group(1) if t else "NO TITLE")[:70])
        bad += r.status != 200 or not flow
    except Exception as e:
        print("ERR", u.split("/")[2], str(e)[:120])
        bad += 1
sys.exit(1 if bad else 0)
