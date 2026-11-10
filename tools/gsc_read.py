"""Read Search Console + GA4 for riverwaterlevels.com (service account, read-only).

python -I tools/gsc_read.py [days]   -> prints totals, top queries, top pages, AI referrals.
Key: calcscrape .env GSC_CREDENTIALS_PATH (never copied here).
"""
import os, sys, datetime as dt
from pathlib import Path

ENV = Path(__file__).resolve().parents[2] / "calcscrape" / ".env"
SITE = "sc-domain:riverwaterlevels.com"
GA4_PROPERTY = "properties/561723165"  # River Water Levels (G-96RG42R07G)
AI = ("chatgpt", "perplexity", "copilot", "gemini", "claude", "bing.com/chat")


def creds(scope):
    from google.oauth2 import service_account
    if os.environ.get("GSC_KEY_JSON"):  # GitHub secret (owner 2026-11-10: the key may live in GitHub secrets for the post-release sitemap resubmit)
        import json
        return service_account.Credentials.from_service_account_info(json.loads(os.environ["GSC_KEY_JSON"]), scopes=[scope])
    env = dict(l.split("=", 1) for l in ENV.read_text().splitlines() if "=" in l and not l.startswith("#"))
    path = env["GSC_CREDENTIALS_PATH"].strip().strip('"')
    if not os.path.isabs(path):
        path = str(ENV.parent / path)
    return service_account.Credentials.from_service_account_file(path, scopes=[scope])


def gsc(days):
    from googleapiclient.discovery import build
    s = build("searchconsole", "v1", credentials=creds("https://www.googleapis.com/auth/webmasters.readonly"), cache_discovery=False)
    end = dt.date.today() - dt.timedelta(days=2)  # GSC lags ~2 days
    start = end - dt.timedelta(days=days - 1)
    q = lambda dims, n: s.searchanalytics().query(siteUrl=SITE, body={
        "startDate": str(start), "endDate": str(end), "dimensions": dims, "rowLimit": n}).execute().get("rows", [])
    tot = q([], 1)
    t = tot[0] if tot else {"impressions": 0, "clicks": 0, "position": 0}
    print(f"GSC {start}..{end}: {t['impressions']:.0f} impressions, {t['clicks']:.0f} clicks, position {t.get('position', 0):.1f}")
    for dim in ("query", "page"):
        print(f"top {dim}:")
        for r in sorted(q([dim], 1000), key=lambda r: -r["impressions"])[:15]:
            print(f"  {r['impressions']:>5.0f} imp {r['clicks']:>3.0f} clk pos {r['position']:>5.1f}  {r['keys'][0]}")


def ga4(days):
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric
    c = BetaAnalyticsDataClient(credentials=creds("https://www.googleapis.com/auth/analytics.readonly"))
    r = c.run_report(RunReportRequest(property=GA4_PROPERTY, date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
                                      dimensions=[Dimension(name="sessionSource")], metrics=[Metric(name="sessions"), Metric(name="userEngagementDuration")]))
    rows = [(x.dimension_values[0].value, int(x.metric_values[0].value), float(x.metric_values[1].value)) for x in r.rows]
    print(f"GA4 last {days} days sessions by source (engaged seconds per session): " + ", ".join(f"{k} {v} ({e / v:.0f} s)" for k, v, e in rows[:12]))
    ai = sum(v for k, v, _ in rows if any(a in k for a in AI))
    print(f"AI assistant sessions: {ai}")


if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 28
    gsc(days)
    try:
        ga4(days)
    except ImportError:
        print("GA4: pip install google-analytics-data (not installed)")
