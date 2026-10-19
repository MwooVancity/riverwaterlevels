"""Which release gates a refresh must run (used by refresh.py). Prints `full` or `light`.
full  = the template differs from the one the live site was built with (or the live site cannot be read): run every gate, including the slow browser gates.
light = the template is the same as the live one, so this is a data refresh: the browser layout gates already passed for this exact template when it was released and are skipped, so that a font or browser hiccup can never freeze fresh flood data;
        the data gates (check.py, truth_tests.py, the pre-publish comparison with USGS and NWS) and the template review check always run.
The live site publishes the hash it was built with at /_template.txt (written by tools/stamp_template.py before every publish)."""
import os, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from template_hash import template_hash  # noqa: E402


def main():
    try:
        live = urllib.request.urlopen(urllib.request.Request("https://riverwaterlevels.com/_template.txt", headers={"User-Agent": "riverwaterlevels-gate-plan"}), timeout=20).read().decode().strip()
    except Exception:
        print("full")
        return
    print("light" if live == template_hash() else "full")


main()
