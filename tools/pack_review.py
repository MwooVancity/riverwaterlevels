"""Builds the review packet for ChatGPT (planning tool): one zip, Desktop\\river-review-packet.zip. Run only when everything is done and deployed.
Layout (see docs/packet/MANIFEST.md): README-FIRST.md, 00-CONTEXT.md, MANIFEST.md, prompts/ (four passes), site/ (the PUBLISHED build, dist/), code/ (a snapshot of git HEAD, so uncommitted experiments are never in it, plus the generated data/waves.csv),
evidence/ (competitor screenshots, our screenshots, CI run history, a real CI gate log, fresh gate output run on the HEAD snapshot, the other site's history), appendix/ (the old missions), late/ (earlier AI reviews: open only in pass 2).
Text files have the owner's Windows home path and Cloudflare account subdomain replaced by placeholders. The zip is key-scanned (secret values read from the calcscrape .env at run time; nothing secret is stored in this file); on a hit the zip is deleted and the script exits 1.
Usage: python -I tools/pack_review.py"""
import os, re, shutil, subprocess, sys, tempfile, zipfile

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = r"C:\Users\mwoo7\Desktop\calcscrape\docs\research"
OUT = os.path.join(tempfile.gettempdir(), "river-review-packet.zip")
DESK = r"C:\Users\mwoo7\Desktop\river-review-packet.zip"
PY = [sys.executable, "-I"]
TEXT = (".md", ".py", ".mjs", ".js", ".json", ".csv", ".txt", ".html", ".css", ".yml", ".yaml", ".jsonc", ".xml", "_headers")
OUR_SCREENS = {  # packet name: file in shots/gate
    "home-desktop-light.png": "d-light_.png", "home-phone-light.png": "m-light_.png", "state-desktop-light.png": "d-light_rivers_mt_.png",
    "gauge-hudson-desktop-light.png": "d-light_river_hudson_river_green_island_.png", "gauge-hudson-phone-light.png": "m-light_river_hudson_river_green_island_.png",
    "gauge-hudson-desktop-dark.png": "d-dark_river_hudson_river_green_island_.png", "gauge-hudson-phone-dark.png": "m-dark_river_hudson_river_green_island_.png",
    "gauge-kinzua-creek-phone-light.png": "m-light_river_kinzua_creek_guffey_.png", "gauge-livingston-desktop-light.png": "d-light_river_yellowstone_river_mt_livingston_.png",
    "gauge-white-bird-phone-light.png": "m-light_river_salmon_river_id_white_bird_.png", "about-phone-light.png": "m-light_about_.png", "status-desktop-light.png": "d-light_status_.png",
}


def run(cmd, cwd, timeout=900):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return (p.stdout + p.stderr).strip()


def scrub(name, data):
    if not name.lower().endswith(TEXT):
        return data
    try:
        t = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    t = t.replace("C:\\Users\\mwoo7\\Desktop\\", "<home>\\").replace("C:/Users/mwoo7/Desktop/", "<home>/").replace("mwoo778", "<account>")
    return t.encode("utf-8")


def main():
    work = tempfile.mkdtemp(prefix="rwl_pack_")
    head = os.path.join(work, "head")
    os.makedirs(head)
    tar = os.path.join(work, "head.tar")
    subprocess.run(["git", "archive", "--format=tar", "-o", tar, "HEAD"], cwd=R, check=True)
    subprocess.run(["tar", "-xf", tar, "-C", head], check=True)
    for extra in ("data/waves.csv",):  # generated and gitignored
        if os.path.exists(os.path.join(R, extra)):
            shutil.copy(os.path.join(R, extra), os.path.join(head, extra))
    # fresh gate output on the HEAD snapshot (cache copied in; build writes only inside the snapshot)
    shutil.copytree(os.path.join(R, "cache"), os.path.join(head, "cache"))
    gate = ["# Gate output, run just now on a clean snapshot of git HEAD (the committed code), not on the working tree.\n"]
    for title, cmd in (("check.py --selftest", PY + ["check.py", "--selftest"]), ("build.py", PY + ["build.py"]), ("check.py (49 built pages, per page and site-wide)", PY + ["check.py"]), ("truth_tests.py (contracts over every gauge page)", PY + ["truth_tests.py"])):
        gate.append("\n$ python -I %s\n%s\n" % (" ".join(cmd[2:]), run(cmd, head)[-1800:]))
    ci_list = run(["gh", "run", "list", "--workflow", "refresh.yml", "--limit", "40", "--json", "status,conclusion,event,createdAt,updatedAt,databaseId"], R)
    ci_ok = run(["gh", "run", "list", "--workflow", "refresh.yml", "--status", "success", "--limit", "1", "--json", "databaseId"], R)
    import json
    runs = json.loads(ci_list) if ci_list.startswith("[") else []
    import datetime
    lines = ["# Last %d GitHub Actions runs of refresh.yml (the deployer). event = schedule (cron every 30 minutes, best effort) or workflow_dispatch (manual)\n# created (UTC) | event | conclusion | minutes" % len(runs)]
    for x in runs:
        a = datetime.datetime.fromisoformat(x["createdAt"].replace("Z", "+00:00")); b = datetime.datetime.fromisoformat(x["updatedAt"].replace("Z", "+00:00"))
        lines.append("%s | %s | %s | %.1f" % (a.strftime("%Y-%m-%d %H:%M"), x["event"], x["conclusion"], (b - a).total_seconds() / 60))
    sched = sorted([datetime.datetime.fromisoformat(x["createdAt"].replace("Z", "+00:00")) for x in runs if x["event"] == "schedule"])
    gaps = [round((b - a).total_seconds() / 3600, 1) for a, b in zip(sched, sched[1:])]
    lines.append("\n# hours between consecutive scheduled runs: %s" % gaps)
    ci_log = ""
    if ci_ok.startswith("["):
        rid = json.loads(ci_ok)[0]["databaseId"]
        full = run(["gh", "run", "view", str(rid), "--log"], R, timeout=300)
        keep = [l.split("\t", 2)[-1][:260] for l in full.splitlines() if re.search(r"\$ .*(collect|build|check|template_hash|truth_tests|truth_live|ui_gates|search_test|clip_all|publish|wrangler|livecheck|stamp)|refresh OK|FAILED|STOPPED|UI gates pass|search test passes|no table scrolls|truth tests|pages \d+|Deployed|gates:", l)]
        ci_log = "# The gate lines of the last passing GitHub Actions run (id %s) of refresh.yml\n" % rid + "\n".join(keep[-60:]) + "\n"

    z = zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED)

    def add(arc, path_or_bytes):
        data = open(path_or_bytes, "rb").read() if isinstance(path_or_bytes, str) else path_or_bytes
        z.writestr(arc, scrub(arc, data))

    pk = os.path.join(R, "docs", "packet")
    for f in ("README-FIRST.md", "00-CONTEXT.md", "MANIFEST.md"):
        add(f, os.path.join(pk, f))
    for f in sorted(os.listdir(os.path.join(pk, "prompts"))):
        add("prompts/" + f, os.path.join(pk, "prompts", f))
    add("appendix/missions-A-to-L.md", os.path.join(D, "chatgpt-final-master-prompt.md"))
    for root, _, fs in os.walk(os.path.join(R, "dist")):
        for f in fs:
            if f not in ("_urls.json",):
                p = os.path.join(root, f)
                add("site/" + os.path.relpath(p, os.path.join(R, "dist")).replace("\\", "/"), p)
    skip = ("docs/archive/", "docs/packet/", "cache/", "dist", "runs/", "node_modules/")
    for root, dirs, fs in os.walk(head):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "node_modules", "cache", "dist_next", "dist_prev", "dist", "runs", ".git")]
        for f in fs:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, head).replace("\\", "/")
            if any(rel.startswith(s) for s in skip) or rel in ("data/geo/places.csv",) or rel.endswith((".png", ".zip")):
                continue
            add("code/" + rel, p)
    add("evidence/gate-output.txt", "".join(gate).encode("utf-8"))
    add("evidence/ci-runs.txt", "\n".join(lines).encode("utf-8"))
    add("evidence/ci-run-gates.log", ci_log.encode("utf-8"))
    add("evidence/calcscrape-history.md", os.path.join(pk, "calcscrape-history.md"))
    comp = os.path.join(R, "shots", "competitors")
    if os.path.isdir(comp):
        for f in sorted(os.listdir(comp)):
            if f.endswith(".png") and not f.startswith("nws-"):  # the NWS page did not render headless
                add("evidence/competitors/" + f, os.path.join(comp, f))
    for arc, src in OUR_SCREENS.items():
        p = os.path.join(R, "shots", "gate", src)
        if os.path.exists(p):
            add("evidence/our-screens/" + arc, p)
    rd = os.path.join(R, "docs", "research")
    for f in sorted(os.listdir(rd)):
        if re.match(r"FRESH-REVIEW-(10-[A-Z]|PLAN)\.md$", f):
            add("late/" + f, os.path.join(rd, f))
    z.close()
    zz = zipfile.ZipFile(OUT)
    secrets = []
    envp = r"C:\Users\mwoo7\Desktop\calcscrape\.env"
    if os.path.exists(envp):
        for line in open(envp, encoding="utf-8", errors="ignore"):
            if "=" in line and not line.lstrip().startswith("#"):
                v = line.split("=", 1)[1].strip().strip("\"'")
                if len(v) >= 12:
                    secrets.append(v)
    generic = re.compile(r"(?i)(api[_-]?key|x-api-key|secret|authorization|bearer|cloudflare_api_token|token)[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{24,}")
    bad = []
    for n in zz.namelist():
        t = zz.read(n).decode("utf-8", "ignore")
        if generic.search(t) or any(v in t for v in secrets):
            bad.append(n)
    import collections
    print("bytes", os.path.getsize(OUT), "files", len(zz.namelist()), dict(collections.Counter(n.split("/")[0] for n in zz.namelist())), "key-like", bad)
    zz.close()
    shutil.rmtree(work, ignore_errors=True)
    if bad:
        os.remove(OUT)
        sys.exit(1)
    shutil.copy(OUT, DESK)
    print("copied to", DESK)


main()
