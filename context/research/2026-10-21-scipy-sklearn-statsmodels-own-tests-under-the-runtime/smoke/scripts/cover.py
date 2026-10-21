"""Per probe: fuel, outcomes, and which of the product's compiled modules it imported.

    uv run python build/095b/survey/cover.py [prefix]
"""

import json
import sys
from pathlib import Path

S = Path.cwd() / "build/095b/survey"
built = [n for n in (S / "builtins.txt").read_text().split()
         if n.split(".")[0] in ("scipy", "sklearn", "statsmodels")]
prefix = sys.argv[1] if len(sys.argv) > 1 else ""
for d in sorted((S / "out").iterdir()):
    r = d / "result.json"
    if not d.name.startswith(prefix) or not r.exists() or d.name.startswith(("derived", "code")):
        continue
    res = json.loads(r.read_text())
    mods = set()
    if (d / "mods.txt").exists():
        mods = {line.split()[0] for line in (d / "mods.txt").read_text().splitlines()}
    name = d.name
    pkg = ("sklearn" if name.startswith(("sk-", "scikit-learn")) else
           "statsmodels" if name.startswith(("sm-", "statsmodels")) else "scipy")
    hit = sorted(m for m in built if m in mods and m.startswith(pkg + "."))
    c = res["counts"]
    print(f"{d.name}\t{res['fuel'] / 1e9:.1f}\t{res['exit']}\t{res['trapped']}\t"
          f"{json.dumps(c, sort_keys=True)}\t{len(hit)}")
    (d / "compiled.txt").write_text("\n".join(hit) + "\n")
