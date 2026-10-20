"""Prints the open items from docs/OPEN-ITEMS.md by section, so a session starts by knowing what is still missing.
Usage: python -I tools/open_items.py            counts and the first line of every open item
       python -I tools/open_items.py --count    just the number (exit 1 when any item in sections A to E is open)"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sec, rows = "", []
for line in open(os.path.join(ROOT, "docs", "OPEN-ITEMS.md"), encoding="utf-8"):
    m = re.match(r"## ([A-H])\. (.*)", line)
    if m:
        sec = m.group(1) + ". " + m.group(2)
    elif line.startswith("## DONE"):
        sec = ""
    elif sec and line.startswith("- [ ]"):
        rows.append((sec, line[6:].strip()))
blocking = [r for r in rows if r[0][0] in "ABCDE"]
if "--brief" in sys.argv:  # session-start hook: one short block, no per-turn cost
    txt = open(os.path.join(ROOT, "docs", "OPEN-ITEMS.md"), encoding="utf-8").read()
    m = re.search(r"## I\. [^\n]*\n(.*?)\n## DONE", txt, re.S)
    print("RIVER SITE REMINDER: %d open items (%d block calling it ready). Full list: docs/OPEN-ITEMS.md. Say the count to the owner." % (len(rows), len(blocking)))
    print("Next items: " + " | ".join(t_[:70] for _, t_ in rows[:4]))
    print(m.group(1).strip() if m else "")
    sys.exit(0)
if "--count" in sys.argv:
    print(len(rows))
    sys.exit(1 if blocking else 0)
print("OPEN ITEMS: %d (%d in sections A to E, the ones that block calling the project ready)" % (len(rows), len(blocking)))
last = ""
for s, t in rows:
    if s != last:
        print("\n" + s)
        last = s
    print("  - " + t[:150])
