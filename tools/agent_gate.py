"""The "would this reach #1" agent gate (owner 2026-10-20: "the gate needs to spawn an agent with that question").
A script cannot start a Claude agent (GitHub has no login; calcscrape forbids a spawned CLI), so the gate FAILS until a fresh agent has answered the question for THIS template hash and the signed report contains the '## #1 COMPARISON' section.
When it fails, the harness rule in CLAUDE.md applies: spawn the agent with the prompt in docs/REVIEW-1ST.md, then `python -I tools/record_review.py SHIP <report>`.
Usage: python -I tools/agent_gate.py"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from lib.reviewgate import is_ship  # noqa: E402
from template_hash import template_hash  # noqa: E402


def main():
    h = template_hash()
    e = (json.load(open(os.path.join(ROOT, "data", "reviews.json"), encoding="utf-8")).get("templates") or {}).get(h)
    if not is_ship(e, h):
        print("AGENT GATE FAILED: no signed SHIP for template %s. Spawn the #1 reviewer: prompt in docs/REVIEW-1ST.md." % h)
        return 1
    rp = os.path.join(ROOT, e["report"])
    if "## #1 COMPARISON" not in open(rp, encoding="utf-8").read():
        print("AGENT GATE FAILED: the signed report %s has no '## #1 COMPARISON' section (it answers 'is it defect-free', not 'would it reach #1'). Spawn the #1 reviewer: docs/REVIEW-1ST.md." % e["report"])
        return 1
    print("agent gate passes: a fresh agent answered the #1 question for template %s (%s)" % (h, e["report"]))
    return 0


sys.exit(main())
