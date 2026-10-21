"""The survey's price: each family's whole-suite fuel (every session but the smoke candidates),
its outcomes, and its chosen smoke group's fuel; the tiers' totals and a shard packing.

    uv run --no-project python -I price.py <survey dir> > price.txt
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

S = Path(sys.argv[1])
jobs = {}
for line in (S / "jobs.jsonl").read_text().splitlines():
    j = json.loads(line)
    jobs[j["label"]] = j

# The chosen smoke group per family: a session label, or "whole" (the suite is its own smoke
# group: under 25 G, or one module that no path can split).
SMOKE = {
    "six": "whole", "cycler": "whole", "tzdata": "whole", "webencodings": "whole",
    "defusedxml": "whole", "xmltodict": "whole", "markupsafe": "whole", "interface-meta": "whole",
    "et-xmlfile": "whole", "tomli-w": "whole", "threadpoolctl": "whole", "cloudpickle": "whole",
    "xlrd": "whole", "tabulate": "whole", "toolz": "whole", "typing-extensions": "whole",
    "tqdm": "whole", "wrapt": "whole", "pyyaml": "whole",
    "charset-normalizer": "charset-normalizer-smoke", "beautifulsoup4": "beautifulsoup4-smoke",
    "soupsieve": "soupsieve-smoke", "formulaic": "formulaic-smoke",
    "attrs": "attrs-smoke3", "packaging": "packaging-smoke2",
    "more-itertools": "more-itertools-smoke", "pyparsing": "pyparsing-smoke",
    "patsy": "patsy-smoke", "mpmath": "mpmath-smoke3", "joblib": "joblib-smoke2",
    "python-dateutil": "python-dateutil-smoke", "html5lib": "whole",
    "jinja2": "jinja2-smoke", "networkx": "networkx-smoke2", "narwhals": "narwhals-smoke",
    "fonttools": "fonttools-smoke", "openpyxl": "openpyxl-smoke2",
    "xlsxwriter": "xlsxwriter-smoke", "seaborn": "seaborn-smoke2",
    "reportlab": "reportlab-smoke", "pypdf": "pypdf-smoke2", "sympy": "sympy-smoke2",
}
# sympy's one test past every bound, measured by 067's pre-build review (EXECUTED there)
SYMPY_17141 = 2_609e9
# sessions a later session replaced (survey only)
SUPERSEDED = {"sy-slow", "sy-solvers", "sy-simplify", "sy-rest"}

fam_full = defaultdict(int)
fam_counts = defaultdict(Counter)
fam_sessions = defaultdict(list)
capped = []
for lab, j in jobs.items():
    if "smoke" in lab or lab in SUPERSEDED:
        continue
    fam_full[j["family"]] += j["fuel"]
    fam_counts[j["family"]].update(j["counts"])
    fam_sessions[j["family"]].append(lab)
    cap = None
    if j["exit"] is None or j.get("trapped") or j.get("trap"):
        capped.append(lab)
fam_full["sympy"] += SYMPY_17141

print(f"{'family':20} {'whole suite':>12} {'smoke':>9}  passed failed error skipped xfail  smoke group")
tot_full = tot_smoke = 0
rows = []
for fam in sorted(SMOKE):
    s = SMOKE[fam]
    smoke = fam_full[fam] if s == "whole" else jobs[s]["fuel"] if s in jobs else float("nan")
    c = fam_counts[fam]
    rows.append((fam, fam_full[fam], smoke, c, s))
for fam, full, smoke, c, s in sorted(rows, key=lambda r: -r[1]):
    tot_full += full
    tot_smoke += smoke
    print(f"{fam:20} {full / 1e9:10.1f} G {smoke / 1e9:7.1f} G  {c['passed']:6} {c['failed']:6} "
          f"{c['error']:5} {c['skipped']:7} {c['xfailed']:5}  {s}")
whole = sum(full for fam, full, smoke, c, s in rows if SMOKE[fam] == "whole")
print(f"\nwhole suites (all 42): {tot_full / 1e12:.2f} T")
print(f"normal tier (smoke groups): {tot_smoke / 1e12:.3f} T")
print(f"release tier (the rest): {(tot_full - whole) / 1e12:.2f} T "
      f"(the whole-as-smoke families, {whole / 1e9:.1f} G, run in the normal tier only)")
print("trapped or stopped sessions:", capped or "none")
