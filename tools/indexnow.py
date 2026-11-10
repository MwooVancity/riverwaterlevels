"""Tell Bing (and the other IndexNow engines) which pages just opened (PLAN 0h; ChatGPT search reads Bing's index).

python -I tools/indexnow.py <url> ...      -> one POST to api.indexnow.org with up to 10,000 urls
python -I tools/indexnow.py --new           -> the pages added to data/index-allow.json by the last commit (the daily release)
The key is public by design: build.py publishes it at /<KEY>.txt so the engines can check the site owns it.
"""
import json, os, subprocess, sys, urllib.request

KEY = "8a1906b9e99095f201fe1a3d6210c090"
HOST = "riverwaterlevels.com"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def payload(urls):
    urls = sorted({u if u.startswith("http") else "https://%s%s" % (HOST, u) for u in urls if u})[:10000]  # the protocol's limit per POST
    return {"host": HOST, "key": KEY, "keyLocation": "https://%s/%s.txt" % (HOST, KEY), "urlList": urls}


def allow_at(rev):
    out = subprocess.run(["git", "show", "%s:data/index-allow.json" % rev], cwd=ROOT, capture_output=True, text=True).stdout
    try:
        return set(json.loads(out).get("allow") or [])
    except ValueError:  # file missing at that commit: nothing was allowed
        return set()


def new_pages():
    """Paths in the allow list now but not one commit ago (code review 2026-11-09: diff lines resent a re-commaed entry and missed unindented ones)."""
    return sorted(allow_at("HEAD") - allow_at("HEAD~1"))


def send(urls):
    if not urls:
        print("indexnow: nothing to send")
        return
    body = json.dumps(payload(urls)).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "riverwaterlevels-indexnow"})  # the default Python client name is refused (403)
    try:
        print("indexnow: %d urls, HTTP %s" % (len(json.loads(body)["urlList"]), urllib.request.urlopen(req, timeout=30).status))
    except Exception as e:  # never fails a release: Bing learns from the sitemap anyway
        print("indexnow: not sent:", str(e)[:120])


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        p = payload(["/river/a/b/", "https://riverwaterlevels.com/river/a/b/", ""])
        assert p["urlList"] == ["https://riverwaterlevels.com/river/a/b/"] and p["keyLocation"].endswith(KEY + ".txt"), "indexnow: duplicate, blank or relative url sent, or wrong key location"
        print("selftest OK")
    elif sys.argv[1:] == ["--new"]:
        send(new_pages())
    else:
        send(sys.argv[1:])
