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
bad = [name for name, fn in CHECKS if not fn()]
print("tests logic: %d checks, %d failures" % (len(CHECKS), len(bad)))
for b in bad:
    print("  FAIL", b)
sys.exit(1 if bad else 0)
