"""Cross-tabulate 300-matrix letter strings (E raises or info>0, F finite, N all-nan).

Usage: crosstab.py name=file:row ...  where file is a probe's .out (text) or a guest .json (its
stdout), and row is the line's first word (inv, gesv, getrf).
"""

import json
import sys
from collections import Counter


def load(spec):
    name, rest = spec.split("=", 1)
    path, row = rest.rsplit(":", 1)
    text = open(path).read()
    if path.endswith(".json"):
        text = json.loads(text)["stdout"]
    for line in text.splitlines():
        w = line.split()
        if w and w[0] == row:
            return name, w[1]
    raise SystemExit(f"no row {row} in {path}")


rows = dict(load(a) for a in sys.argv[1:])
names = list(rows)
for k in names:
    c = Counter(rows[k])
    print(f"{k:24s} " + " ".join(f"{x}:{c[x]}" for x in sorted(c)))
for i, p in enumerate(names):
    for q in names[i + 1 :]:
        a, b = rows[p], rows[q]
        pair = Counter((x, y) for x, y in zip(a, b))
        same = sum(1 for x, y in zip(a, b) if (x == "E") == (y == "E"))
        print(f"{p} vs {q}: raise agrees on {same}/300; " + ", ".join(f"{x}{y}:{n}" for (x, y), n in sorted(pair.items())))
        diff = [str(j) for j, (x, y) in enumerate(zip(a, b)) if (x == "E") != (y == "E")]
        if len(diff) <= 40:
            print("   differ at", " ".join(diff))
