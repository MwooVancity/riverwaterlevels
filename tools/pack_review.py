"""Builds the review packet for ChatGPT (planning tool): Desktop\\river-review-packet.zip. Run only when everything is done and deployed: `site/` is the PUBLISHED build (dist/), so the packet shows what the world sees.
Contents: PROMPT.md (calcscrape/docs/research/chatgpt-final-master-prompt.md), site/, code/ (generator, tools, tests, workflows, docs, queue and name data), shots/ (comparison and gate contact sheets), reviews/ (every reader review, the plan review, research notes), data/ (inventory, hubs, geo summaries).
The zip is key-scanned: the script exits 1 and deletes the zip if any key-like string is found. Usage: python -I tools/pack_review.py"""
import os, re, shutil, sys, zipfile

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = r"C:\Users\mwoo7\Desktop\calcscrape\docs\research"
OUT = os.path.join(D, "river-review-packet.zip")
DESK = r"C:\Users\mwoo7\Desktop\river-review-packet.zip"
SKIP_DIRS = {"__pycache__", "node_modules"}


def add_tree(z, src, dst, only_ext=None):
    n = 0
    for root, dirs, fs in os.walk(src):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in fs:
            if only_ext and not f.endswith(only_ext):
                continue
            p = os.path.join(root, f)
            z.write(p, dst + "/" + os.path.relpath(p, src).replace("\\", "/"))
            n += 1
    return n


def main():
    if os.path.exists(OUT):
        os.remove(OUT)
    z = zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED)
    z.write(os.path.join(D, "chatgpt-final-master-prompt.md"), "PROMPT.md")
    for root, _, fs in os.walk(os.path.join(R, "dist")):
        for f in fs:
            if f != "_urls.json":
                p = os.path.join(root, f)
                z.write(p, "site/" + os.path.relpath(p, os.path.join(R, "dist")).replace("\\", "/"))
    for sub in ("lib", "templates", "tools"):
        add_tree(z, os.path.join(R, sub), "code/" + sub)
    for f in ["collect.py", "build.py", "check.py", "tests.py", "truth_tests.py", "refresh.py", "publish.py", "livecheck.py", "render_test.mjs", "js_test.mjs", "ui_gates.mjs", "package.json", ".github/workflows/refresh.yml", ".github/workflows/watchdog.yml",
              "README.md", "CLAUDE.md", "wrangler.jsonc", "data/sources.json", "data/name-overrides.csv", "data/name-fixes.csv", "data/waves.csv", "data/waves-report.txt", "data/backtest.txt", "data/recreation-rivers.txt", "data/demand.csv",
              "data/index-allow.json", "data/reviews.json", "data/pages-all.csv", "data/hubs.csv", "data/states.csv", "data/geo/gauge-geo.csv", "data/geo/places.csv"]:
        if os.path.exists(os.path.join(R, f)):
            z.write(os.path.join(R, f), "code/" + f)
    add_tree(z, os.path.join(R, "docs"), "code/docs", only_ext=".md")  # PLAN, WORK-LIST, RISKS-AND-STAGES, REVIEW-PROMPT, archive; docs/research is the reviews folder below
    for sub in ("cmp", "gate"):
        d = os.path.join(R, "shots", sub)
        if os.path.isdir(d):
            add_tree(z, d, "shots/" + sub)
    rd = os.path.join(R, "docs", "research")
    if os.path.isdir(rd):
        for f in sorted(os.listdir(rd)):
            if re.match(r"FRESH-REVIEW", f):
                z.write(os.path.join(rd, f), "reviews/" + f)
    for f in sorted(os.listdir(D)):
        if re.match(r"(FRESH-REVIEW|RESEARCH-|API-DISCOVERY|TERMS-QUOTES|terms-register|MASTER-SPEC|DESIGN-UI|INTERNAL-LINKS|END-TO-END-PLAN|STATUS-FINAL|LAKEBRIEF-WATER-PAGE)", f) and os.path.isfile(os.path.join(D, f)):
            z.write(os.path.join(D, f), "reviews/" + f)
    z.close()
    zz = zipfile.ZipFile(OUT)
    # key scan: every secret value in the calcscrape .env (read here, never written), plus generic key-shaped strings; no key fragment is stored in this file
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
    print("bytes", os.path.getsize(OUT), "files", len(zz.namelist()), "key-like", bad)
    if bad:
        zz.close()
        os.remove(OUT)
        sys.exit(1)
    zz.close()
    shutil.copy(OUT, DESK)
    print("copied to", DESK)


main()
