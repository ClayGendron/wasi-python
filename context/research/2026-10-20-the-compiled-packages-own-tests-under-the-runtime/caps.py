"""The re-survey's table, each cap by the owner's rule: 1.5 times the measured fuel, rounded up to
two significant figures; each family's budget the sum of its caps. Reads summary-resurvey.json
beside this file; every matplotlib-*/mpl-* group is the matplotlib family, every contourpy-* group
the contourpy family. Run: uv run --no-project python -I caps.py <group>..."""
import json
import math
import sys
from pathlib import Path

s = json.loads((Path(__file__).parent / "summary-resurvey.json").read_text())


def cap(f):
    x = 1.5 * f
    e = 10 ** (int(math.floor(math.log10(x))) - 1)
    return math.ceil(x / e) * e


def family(g):
    if g.startswith(("matplotlib", "mpl-")):
        return "matplotlib"
    if g.startswith("contourpy"):
        return "contourpy"
    return g.replace("-ro", "")


fam = {}
print("| group | fuel | cap | passed | failed | skipped | other |\n|---|---|---|---|---|---|---|")
for g in sys.argv[1:]:
    v = s[g]
    c = v["counts"]
    f = v["fuel"]
    k = cap(f)
    fam[family(g)] = fam.get(family(g), 0) + k
    other = ", ".join(f"{n} {o}" for o, n in c.items() if o not in ("passed", "failed", "skipped"))
    if v["collect_errors"]:
        other += f"; {len(v['collect_errors'])} collection errors"
    if v["deselected"]:
        other += f"; {v['deselected']} deselected"
    if v["trap_cause"]:
        other += f"; TRAP {v['trap_cause']}"
    print(f"| `{g}` | {f / 1e9:,.1f} G | {k:.2e} | {c.get('passed', 0):,} | {c.get('failed', 0)} "
          f"| {c.get('skipped', 0):,} | {other} |")
print()
for k, v in fam.items():
    print(f"{k}: budget {v:.3e}")
print(f"total caps {sum(fam.values()):.3e}; total fuel "
      f"{sum(s[g]['fuel'] for g in sys.argv[1:]) / 1e12:.3f} T")
