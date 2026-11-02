"""How often Cloudflare stopped our Worker for CPU in 24 h. A stopped run is a reader's error page, so this real count, not a gauge guess,
decides when growth waits for Workers Paid. Prints the count, or nothing when the key cannot read analytics. Measured 2026-11-02 at 142 gauges:
2,661 requests, p50 2.0 ms, p99 8.9 ms, max 15 ms, none stopped."""
import datetime, json, os, sys, urllib.request

QUERY = """query($a:String!,$f:Time!,$t:Time!){viewer{accounts(filter:{accountTag:$a}){workersInvocationsAdaptive(limit:100,filter:{datetime_geq:$f,datetime_leq:$t}){sum{requests}dimensions{scriptName status}}}}}"""
LIMIT = 10  # one stop can be a passing spike; ten a day is a pattern
REQUESTS = 80000  # 80% of the free 100,000 a day, shared by every Worker on the account; past 100,000 pages answer error 1027


def ask(body, token):
    return json.load(urllib.request.urlopen(urllib.request.Request("https://api.cloudflare.com/client/v4/graphql", json.dumps(body).encode(), {"Authorization": "Bearer " + token, "Content-Type": "application/json"}), timeout=30))


def stopped(ask=ask):
    n = load(ask)
    return n and n["stopped"]


def load(ask=ask):
    """{"stopped": runs of our Worker killed, "requests": every Worker on the account} over 23 h, or None."""
    token, account = os.environ.get("CLOUDFLARE_API_TOKEN"), os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    if not token or not account:
        return None
    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        rows = ask({"query": QUERY, "variables": {"a": account, "f": (now - datetime.timedelta(hours=23)).isoformat(), "t": now.isoformat()}}, token)["data"]["viewer"]["accounts"][0]["workersInvocationsAdaptive"]
        return {"stopped": sum(r["sum"]["requests"] for r in rows if r["dimensions"] == {"scriptName": "riverwaterlevels", "status": "exceededResources"}), "requests": sum(r["sum"]["requests"] for r in rows)}
    except Exception as e:  # no analytics permission or Cloudflare down: says nothing about the Worker
        print("worker load not readable:", str(e)[:80], file=sys.stderr)
        return None


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        os.environ.update(CLOUDFLARE_API_TOKEN="x", CLOUDFLARE_ACCOUNT_ID="y")
        got = {"data": {"viewer": {"accounts": [{"workersInvocationsAdaptive": [{"sum": {"requests": 12}, "dimensions": {"scriptName": "riverwaterlevels", "status": "exceededResources"}}, {"sum": {"requests": 9}, "dimensions": {"scriptName": "other", "status": "success"}}]}]}}}
        assert stopped(lambda b, t: got) == 12 and load(lambda b, t: got)["requests"] == 21, "stopped runs or requests not counted"
        assert stopped(lambda b, t: {"data": None}) is None, "an unreadable answer counted as a number"
        print("selftest OK")
    else:
        n = stopped()
        print("" if n is None else n)
