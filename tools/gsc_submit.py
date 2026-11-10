"""Resubmit the sitemap to Google Search Console (the one official, scriptable 'come and read my new pages' signal; Google has no API for
'Request indexing' outside job postings and livestreams, and retired the sitemap ping in 2023). Run by the daily scheduled task on the
owner's PC (the key lives only in calcscrape .env, never in GitHub). Needs the service account at Full permission in Search Console.

python -I tools/gsc_submit.py   -> prints "sitemap resubmitted" or why not (never raises)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gsc_read import SITE, creds

SITEMAP = "https://riverwaterlevels.com/sitemap.xml"


def main():
    try:
        from googleapiclient.discovery import build
        s = build("searchconsole", "v1", credentials=creds("https://www.googleapis.com/auth/webmasters"), cache_discovery=False)
        s.sitemaps().submit(siteUrl=SITE, feedpath=SITEMAP).execute()
        got = s.sitemaps().get(siteUrl=SITE, feedpath=SITEMAP).execute()
        print("sitemap resubmitted; Google last downloaded it %s" % got.get("lastDownloaded", "never"))
    except Exception as e:
        msg = str(e)
        print("sitemap not resubmitted: %s" % ("the service account is Restricted; owner: Search Console > Users and permissions > Full" if "403" in msg or "forbidden" in msg.lower() else msg[:160]))


if __name__ == "__main__":
    main()
