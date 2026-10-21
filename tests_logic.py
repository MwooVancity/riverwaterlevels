"""Pure-logic release tests: the parts of tests.py that do not rebuild or overwrite dist/ or cache/, so they can sit in the release chain.
Usage: python -I tests_logic.py     (run by refresh.py before every publish; determinism, forced failure and rollback stay in tests.py, run by hand)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I leaves the script folder off the path
import tests

CHECKS = [("unit checks (percentile, axis labels, place phrasing, hidden blocks)", lambda: tests.unit_checks()[0]),
          ("new blocks hidden without data, when stale, when the source is not cleared", tests.blocks_safety),
          ("review gate: new gauge pages need a SHIP verdict, live pages never blocked", tests.review_gate),
          ("record_review imports template_hash without exiting", tests.record_tools_import),
          ("upstream/downstream pairs are listed on both pages", tests.related_closure),
          ("a SHIP needs a signature tied to its report", tests.signed_review),
          ("noindex kill switch: hold, open, allow list, header rule", tests.index_gate)]
def workflows_parse():
    """A workflow file that is not valid YAML never starts: GitHub shows a 0-second failure and every scheduled refresh stops silently (happened 2026-10-20)."""
    import glob
    try:
        import yaml
    except ImportError:
        return True  # PyYAML missing on this machine: nothing to check with
    root = os.path.dirname(os.path.abspath(__file__))
    for f in glob.glob(os.path.join(root, ".github", "workflows", "*.yml")):
        try:
            d = yaml.safe_load(open(f, encoding="utf-8"))
        except Exception as e:
            print("  workflow does not parse:", os.path.basename(f), str(e).splitlines()[-1][:100])
            return False
        if not isinstance(d, dict) or not (d.get("on") or d.get(True)) or not d.get("jobs"):
            print("  workflow lacks on/jobs:", os.path.basename(f))
            return False
    return True


CHECKS.append(("GitHub workflow files are valid YAML with triggers and jobs", workflows_parse))
bad = [name for name, fn in CHECKS if not fn()]
print("tests logic: %d checks, %d failures" % (len(CHECKS), len(bad)))
for b in bad:
    print("  FAIL", b)
sys.exit(1 if bad else 0)
