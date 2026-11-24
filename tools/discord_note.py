"""One Discord message when a release ran or a refresh failed (owner 2026-11-23: "best way to keep up on pages not being deployed").
Env: DISCORD_WEBHOOK (a GitHub secret; unset = print only, never an error), PASSED ("1" when the refresh passed), RELEASED ("1" when the daily release ran), RUN_URL.
Counts come from data/waves.csv. Hourly passing refreshes send nothing.
Usage: python -I tools/discord_note.py --selftest | python -I tools/discord_note.py
"""
import csv, collections, json, os, sys, urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def message(rows, passed, released, url):
    """Text to send, or None when nothing needs saying."""
    if passed and not released:
        return None
    c = collections.Counter(r["status"] for r in rows)
    gates = collections.Counter(r["gate"] for r in rows if r["status"] == "queue" and r["gate"])
    head = ("FAILED: the refresh did not pass, the site kept yesterday's pages." if not passed else "Release done.")
    lines = [head, "live %d, queued %d, held %d" % (c["live"], c["queue"], c["held-names"] + sum(gates.values()))]
    if gates:
        lines.append("held by gate: " + ", ".join("%s %d" % (g[:40], n) for g, n in gates.most_common(5)))
    if url:
        lines.append(url)
    return "\n".join(lines)[:1900]


def _selftest():
    rows = [{"status": "live", "gate": ""}, {"status": "queue", "gate": "no-usgs-rows"}, {"status": "queue", "gate": ""}]
    assert message(rows, True, False, "") is None, "a passing hourly refresh must stay silent"
    assert message(rows, False, False, "u").startswith("FAILED") and "u" in message(rows, False, False, "u")
    m = message(rows, True, True, "")
    assert m.startswith("Release done") and "live 1, queued 2" in m and "no-usgs-rows 1" in m, m
    print("discord_note selftest OK")


def main():
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8")))
    text = message(rows, os.environ.get("PASSED") == "1", os.environ.get("RELEASED") == "1", os.environ.get("RUN_URL", ""))
    if not text:
        return
    hook = os.environ.get("DISCORD_WEBHOOK", "")
    if not hook.startswith("https://discord.com/api/webhooks/"):
        print("no webhook set; would send:\n" + text)
        return
    req = urllib.request.Request(hook, data=json.dumps({"content": text}).encode(), headers={"Content-Type": "application/json", "User-Agent": "rwl-note"})
    try:
        urllib.request.urlopen(req, timeout=20)
        print("discord note sent")
    except OSError as e:  # a notification must never fail the run
        print("discord note failed:", e)


if __name__ == "__main__":
    _selftest() if "--selftest" in sys.argv else main()
