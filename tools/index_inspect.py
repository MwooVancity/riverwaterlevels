"""Which sitemap pages Google has indexed (PLAN 0h). Search Console URL Inspection, service account, read-only.

python -I tools/index_inspect.py [max]   -> counts by coverage state, then the URLs of every state except "Submitted and indexed".
Quota: 2,000 inspections a day per property; max defaults to 400 (336 sitemap pages on 2026-11-09). 14,000 pages = slices over 7 days.
"""
import collections, re, sys, urllib.request
sys.path.insert(0, __import__("os").path.dirname(__file__))
from gsc_read import SITE, creds

SITEMAP = "https://riverwaterlevels.com/sitemap.xml"


def summarize(results):
    """{state: [url]} from [(url, inspection-result dict)]; an API error is its own state, never 'indexed'."""
    by = collections.defaultdict(list)
    for url, r in results:
        st = ((r or {}).get("indexStatusResult") or {}).get("coverageState") or "no answer"
        by[st].append(url)
    return by


def main(n):
    from googleapiclient.discovery import build
    urls = re.findall(r"<loc>([^<]+)</loc>", urllib.request.urlopen(urllib.request.Request(SITEMAP, headers={"User-Agent": "riverwaterlevels-index-check"}), timeout=30).read().decode())[:n]
    s = build("searchconsole", "v1", credentials=creds("https://www.googleapis.com/auth/webmasters.readonly"), cache_discovery=False)
    out = []
    for u in urls:
        try:
            out.append((u, s.urlInspection().index().inspect(body={"inspectionUrl": u, "siteUrl": SITE}).execute().get("inspectionResult")))
        except Exception as e:  # quota or a bad URL: counted as "no answer", the run goes on
            out.append((u, {"indexStatusResult": {"coverageState": "no answer: " + str(e)[:60]}}))
    by = summarize(out)
    print("index inspect: %d sitemap pages" % len(urls))
    for st, us in sorted(by.items(), key=lambda x: -len(x[1])):
        print("  %4d  %s" % (len(us), st))
    for st, us in sorted(by.items()):
        if st != "Submitted and indexed":
            print("\n%s:" % st)
            for u in us:
                print("  " + u)


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        b = summarize([("a", {"indexStatusResult": {"coverageState": "Submitted and indexed"}}), ("b", {"indexStatusResult": {"coverageState": "Discovered - currently not indexed"}}), ("c", None)])
        assert b["Submitted and indexed"] == ["a"] and b["no answer"] == ["c"] and len(b) == 3, "index_inspect: a failed inspection counted as indexed"
        print("selftest OK")
    else:
        main(int(sys.argv[1]) if sys.argv[1:] else 400)
