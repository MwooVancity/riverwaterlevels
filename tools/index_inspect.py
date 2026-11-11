"""Which sitemap pages Google has indexed (PLAN 0h). Search Console URL Inspection, service account, read-only.

python -I tools/index_inspect.py [max]   -> inspects today's slice, merges it into data/index-inspect.json, prints counts by coverage state,
                                           then the URLs of every state except "Submitted and indexed".
Slice (audit 2026-11-10 #28): never-inspected pages first, then the oldest inspection; at most `max` a day (default 1,900, under Google's
2,000 inspections a day per property), so 14,000 pages take 8 days and the 9th day starts over. 8 workers, 30 s per call (was serial, 6.4 s a URL,
no timeout: 14,000 pages = 25 h). One writer: this tool writes data/index-inspect.json; tools/reindex.py reads it to put noindex-era pages first.
A failed inspection (quota, timeout) keeps the page's last answer and its old date, so it is first in line tomorrow. Never prints the key.
"""
import collections, concurrent.futures, datetime, json, os, re, sys, threading, urllib.request
sys.path.insert(0, os.path.dirname(__file__))

SITEMAP = "https://riverwaterlevels.com/sitemap.xml"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "index-inspect.json")
WORKERS, TIMEOUT, DAILY = 8, 30, 1900


def summarize(results):
    """{state: [url]} from [(url, inspection-result dict)]; an API error is its own state, never 'indexed'."""
    by = collections.defaultdict(list)
    for url, r in results:
        st = ((r or {}).get("indexStatusResult") or {}).get("coverageState") or "no answer"
        by[st].append(url)
    return by


def todays_slice(urls, done, n):
    """The n URLs to inspect today: never inspected first (sitemap order), then the oldest answer first."""
    return sorted(urls, key=lambda u: (u in done, (done.get(u) or {}).get("date") or ""))[:n]


def merge(done, results, today):
    """Fresh answers replace old ones; an error leaves the old answer and date (retried first next run). Pages gone from the sitemap are dropped."""
    for u, r in results:
        st = ((r or {}).get("indexStatusResult") or {}).get("coverageState")
        if st and not st.startswith("no answer"):
            done[u] = {"state": st, "date": today}
    return done


def main(n):
    from googleapiclient.discovery import build
    import google_auth_httplib2, httplib2
    from gsc_read import SITE, creds
    get = lambda u: re.findall(r"<loc>([^<]+)</loc>", urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "riverwaterlevels-index-check"}), timeout=30).read().decode())
    urls = [p for u in get(SITEMAP) for p in (get(u) if u.endswith(".xml") else [u])]  # past 10,000 pages /sitemap.xml is an index of sitemap files (lib/directory.py sitemap_files)
    try:
        done = json.load(open(OUT, encoding="utf-8"))
    except (OSError, ValueError):  # first run or a torn file: inspect from scratch
        done = {}
    on = set(urls)
    done = {u: v for u, v in done.items() if u in on}
    todo = todays_slice(urls, done, n)
    cr, local = creds("https://www.googleapis.com/auth/webmasters.readonly"), threading.local()

    def one(u):
        if not hasattr(local, "s"):  # httplib2 is not thread-safe: one client per worker, each call capped at TIMEOUT seconds
            local.s = build("searchconsole", "v1", http=google_auth_httplib2.AuthorizedHttp(cr, http=httplib2.Http(timeout=TIMEOUT)), cache_discovery=False)
        try:
            return u, local.s.urlInspection().index().inspect(body={"inspectionUrl": u, "siteUrl": SITE}).execute(num_retries=1).get("inspectionResult")
        except Exception as e:  # quota, timeout or a bad URL: counted as "no answer", the run goes on (the error class only; its text can carry request details)
            return u, {"indexStatusResult": {"coverageState": "no answer: " + type(e).__name__}}

    with concurrent.futures.ThreadPoolExecutor(WORKERS) as ex:
        out = list(ex.map(one, todo))
    merge(done, out, datetime.date.today().isoformat())
    tmp = OUT + ".tmp"
    json.dump(done, open(tmp, "w", encoding="utf-8"), indent=0, sort_keys=True)
    os.replace(tmp, OUT)
    by = summarize(out)
    print("index inspect: %d of %d sitemap pages today; %d known in %s" % (len(todo), len(urls), len(done), os.path.relpath(OUT)))
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
        d = {"a": {"state": "x", "date": "2026-11-01"}, "b": {"state": "x", "date": "2026-10-01"}}
        assert todays_slice(["a", "b", "c"], d, 2) == ["c", "b"], "index_inspect: the slice must take new pages, then the oldest answer"
        m = merge(dict(d), [("a", {"indexStatusResult": {"coverageState": "no answer: HttpError"}}), ("b", {"indexStatusResult": {"coverageState": "Submitted and indexed"}})], "2026-11-10")
        assert m["a"]["date"] == "2026-11-01" and m["b"] == {"state": "Submitted and indexed", "date": "2026-11-10"}, "index_inspect: an error overwrote the last answer, or a fresh one was lost"
        print("selftest OK")
    else:
        main(min(int(sys.argv[1]), DAILY) if sys.argv[1:] else DAILY)
