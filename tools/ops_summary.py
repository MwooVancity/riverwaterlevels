"""The owner's dashboard (owner 2026-11-10: "a dashboard url ... gate failures / not deployed / noindex so I can ask about them later").
Written by the hourly watchdog run into its GitHub run page (Summary tab), so it is private to the repo, needs no new public page, and
keeps updating while deploys fail (a page on the site would freeze with the site). Bookmark:
https://github.com/MwooVancity/riverwaterlevels/actions/workflows/watchdog.yml  -> newest run -> Summary.

python -I tools/ops_summary.py [watchdog-output.txt]   -> markdown on stdout (the workflow appends it to $GITHUB_STEP_SUMMARY)

Edge cases: site down or status.json torn -> says so; GitHub log download refused (egress 503) -> says the reason is unreadable; a log is read
only while the site is stale (one download an hour, not one per run); every list is capped at 40 lines with the full count (14,000 pages)."""
import csv, datetime, json, os, re, subprocess, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://riverwaterlevels.com"
CAP = 40
STALE_MIN = 90  # the hourly refresh plus slack: older means deploys are not landing


def get_json(path):
    try:
        req = urllib.request.Request(SITE + path, headers={"User-Agent": "riverwaterlevels.com ops summary"})
        return json.load(urllib.request.urlopen(req, timeout=30))
    except Exception as e:
        return {"_error": str(e)[:100]}


def capped(lines):
    return lines[:CAP] + (["- ... and %d more" % (len(lines) - CAP)] if len(lines) > CAP else [])


def stop_reason(wf="refresh.yml"):
    """The newest run's (refresh, or dryrun for code waiting on check) stop lines (STOPPED, FAIL, SITE FAIL, Traceback tail) from its finish job; None when unreadable."""
    try:
        run = json.loads(subprocess.run(["gh", "run", "list", "--workflow", wf, "--limit", "1", "--json", "databaseId,createdAt"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60).stdout)[0]
        jobs = json.loads(subprocess.run(["gh", "run", "view", str(run["databaseId"]), "--json", "jobs"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60).stdout)["jobs"]
        job = next((j for j in jobs if "finish" in j["name"]), jobs[-1])
        log = subprocess.run(["gh", "run", "view", "--job", str(job["databaseId"]), "--log"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        text = log.stdout or log.stderr
        if not log.stdout:
            return run, ["log not readable: %s" % text.strip()[:120]]
        keep = []
        for ln in text.splitlines():
            ln = re.sub(r"^.*?Z ", "", ln)
            if re.match(r"\s*(STOPPED|SITE FAIL|FAIL |refresh FAILED|refresh OK|release DROPPED|release committed|[A-Za-z]*Error:|CARRIED|could not carry)", ln) and "36;1m" not in ln:
                keep.append(ln.strip()[:200])
        return run, keep[-25:]
    except Exception as e:
        return None, ["could not read the newest refresh run: %s" % str(e)[:100]]


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    out = ["# River Water Levels: site state", "_Updated %s. Ask Claude about any line here._" % now.strftime("%Y-%m-%d %H:%M UTC"), ""]

    st = get_json("/status.json")
    out.append("## Is the site updating?")
    if st.get("_error"):
        out.append("**Unknown: the live site did not answer status.json** (%s)." % st["_error"])
        age = None
    else:
        built = datetime.datetime.fromisoformat(st["built_at"])
        age = (now - built).total_seconds() / 60
        out.append(("Yes: rebuilt %d min ago" if age <= STALE_MIN else "**NO: last rebuilt %.1f h ago; deploys are not landing (the live site keeps that copy)**") % (age if age <= STALE_MIN else age / 60)
                   + ". %s gauges, %s pages." % (st.get("gauges"), st.get("pages")))
    if age is None or age > STALE_MIN:
        run, lines = stop_reason()
        if run:
            out.append("Newest refresh run %s (%s), why it did not deploy:" % (run["databaseId"], run["createdAt"]))
        out += ["    " + x for x in lines] or ["    (no stop line found)"]
    out.append("")
    try:  # 2026-11-11: every check run was green while its gates failed, so 27 commits sat unpromoted all day and nobody saw it
        ahead = int(subprocess.run(["gh", "api", "repos/{owner}/{repo}/compare/main...check", "-q", ".ahead_by"], capture_output=True, text=True, timeout=60).stdout.strip())
    except Exception:
        ahead = None
    if ahead:
        run, lines = stop_reason("dryrun.yml")
        if not any(x.startswith("refresh OK") for x in lines):
            out.append("## Code changes waiting to go live")
            out.append("**%d commit(s) on check are not on main: the newest check run did not pass, so nothing was promoted.**%s" % (ahead, " Run %s:" % run["databaseId"] if run else ""))
            out += ["    " + x for x in lines if not x.startswith("CARRIED")] or ["    (no stop line found)"]
            out.append("")

    sys.path.insert(0, ROOT)
    from lib.ledger import catch_line
    out += ["## Gates", catch_line(None if st.get("_error") else st.get("catches")), ""]

    out.append("## Daily release (new gauges)")
    try:
        last = open(os.path.join(ROOT, "data", "last-release.txt"), encoding="utf-8").read().strip()
        ow = json.load(open(os.path.join(ROOT, "data", "open-wave-last.json"), encoding="utf-8"))
        out.append("Last release %s; last batch opened to Google %s: %s page(s)%s." % (last, ow.get("at"), ow.get("opened"),
                   (", %d unreviewed" % len(ow["unreviewed"])) if ow.get("unreviewed") else ""))
        if last != now.strftime("%Y-%m-%d") and now.hour >= 13:
            out.append("**No release today yet** (it runs from 11:00 UTC; a dropped release says why in the stop lines above).")
    except Exception as e:
        out.append("Unknown: %s" % str(e)[:100])
    out.append("")

    out.append("## Pages held back in the live build (old copy kept, or not built)")
    held = []
    if not st.get("_error"):
        held += ["- %s: page build failed, previous copy kept" % u for u in st.get("failed_urls") or []]
        held += ["- block error: %s" % e for e in st.get("block_errors") or []]
        for name, why in sorted(((st.get("world") or {}).get("thin") or {}).items()):
            held.append("- world gauge %s not built: %s" % (name, "; ".join(why) if isinstance(why, list) else why))
    out += capped(held) or ["None."]
    out.append("")

    out.append("## Live pages Google is told not to index")
    noidx = []
    try:
        ix = json.load(open(os.path.join(ROOT, "data", "index-allow.json"), encoding="utf-8"))
        allow, pulled = set(ix.get("allow") or []), set(ix.get("pulled") or [])
        for r in csv.DictReader(open(os.path.join(ROOT, "data", "waves.csv"), encoding="utf-8")):
            u = r.get("url") or ""
            if r.get("status") == "live" and u.startswith(("/river/", "/lake/", "/coast/")) and u not in allow:
                noidx.append("- %s (%s): %s" % (u, r.get("state"), "pulled by hand" if u in pulled else (r.get("decision") if (r.get("decision") or "").strip(" 0") else "live, waiting for the daily release to open it")))
        for w in json.load(open(os.path.join(ROOT, "data", "world-pages.json"), encoding="utf-8")):
            if w.get("hold"):
                noidx.append("- /%s/ and its gauge pages: on hold until the phone review passes" % w["slug"])
    except Exception as e:
        noidx.append("- could not read the allow list: %s" % str(e)[:100])
    out += capped(noidx) or ["None: every live page is open to Google."]
    out.append("")

    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        lines = open(sys.argv[1], encoding="utf-8", errors="replace").read().splitlines()
        probs = [ln.strip() for ln in lines if "PROBLEM" in ln]
        out.append("## Health check problems (%d)" % len(probs))
        out += capped(["- " + p.replace("PROBLEM: ", "") for p in probs]) or ["None."]
        out.append("")
        # audit 2026-11-10 #12: the hourly live-number checks (watchdog.yml appends their output to the same file); a MISMATCH is a live page showing a number its agency does not
        wrong = [ln.strip() for ln in lines if "MISMATCH" in ln or " FAULT" in ln or "WARNING" in ln]
        out.append("## Live pages whose numbers disagree with the agency now (%d)" % len(wrong))
        ran = [ln.strip()[:160] for ln in lines if ln.startswith(("truth_live:", "world truth:"))]
        out += capped(["- " + w for w in wrong]) or ["None (%s)." % "; ".join(ran) if ran else "**Unknown: the live checks printed no result this hour.**"]
    print("\n".join(out))


if __name__ == "__main__":
    main()
