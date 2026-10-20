"""The re-survey's table with each cap by the owner's rule: 1.5 times the fuel, rounded up to two
significant figures; each family's budget the sum of its caps."""
import json, math, sys
from pathlib import Path
s = json.loads((Path(__file__).parent / "summary.json").read_text())
def cap(f):
    x = 1.5 * f
    e = 10 ** (int(math.floor(math.log10(x))) - 1)
    return math.ceil(x / e) * e
fam = {}
print("| group | fuel | cap | passed | failed | skipped | other |\n|---|---|---|---|---|---|---|")
for g in sys.argv[1:]:
    v = s[g]; c = v["counts"]; f = v["fuel"]; k = cap(f)
    family = "matplotlib" if g.startswith(("matplotlib", "mpl-")) else g.replace("-ro", "")
    fam[family] = fam.get(family, 0) + k
    other = ", ".join(f"{n} {o}" for o, n in c.items() if o not in ("passed", "failed", "skipped"))
    if v["collect_errors"]: other += f"; {len(v['collect_errors'])} collection errors"
    if v["deselected"]: other += f"; {v['deselected']} deselected"
    if v["trap_cause"]: other += f"; TRAP {v['trap_cause']}"
    print(f"| `{g}` | {f/1e9:,.1f} G | {k:.2e} | {c.get('passed',0):,} | {c.get('failed',0)} | {c.get('skipped',0):,} | {other} |")
print()
for k, v in fam.items(): print(f"{k}: budget {v:.3e}")
print(f"total caps {sum(fam.values()):.3e}; total fuel {sum(s[g]['fuel'] for g in sys.argv[1:])/1e12:.3f} T")
