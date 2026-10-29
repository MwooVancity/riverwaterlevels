"""Session-start hook: the first four "Next steps" from PLAN.md (the only plan file; docs/OPEN-ITEMS.md folded in 2026-10-29)."""
import os, re
txt = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "PLAN.md"), encoding="utf-8").read()
steps = re.findall(r"^\d+\. (.{0,90})", txt.split("## Next steps", 1)[-1].split("\n## ", 1)[0], re.M)
print("RIVER PLAN: %d next steps in PLAN.md. First: %s" % (len(steps), " | ".join(steps[:4])))
