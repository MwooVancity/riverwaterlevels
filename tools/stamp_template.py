"""Writes the template hash into the build (dist_next/_template.txt) so the next refresh can tell whether the template changed (tools/gate_plan.py). Run by refresh.py after build.py."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from template_hash import template_hash  # noqa: E402

open(os.path.join(ROOT, "dist_next", "_template.txt"), "w").write(template_hash() + "\n")
print("stamped", template_hash())
