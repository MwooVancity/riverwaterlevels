"""Fetches live pages on the real domain and reports status, noindex header, flow value, title. Usage: python -I livecheck.py [url ...]
Exit 1 if a page is not 200 or shows no flow value, so refresh.py stops and logs it."""
import sys, re, urllib.request

DEFAULT = ["https://riverwaterlevels.com/river/missouri-river-mo/kansas-city/water/", "https://riverwaterlevels.com/river/kinzua-creek/guffey/water/"]
bad = 0
for u in (sys.argv[1:] or DEFAULT):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "livecheck"}), timeout=30)
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
