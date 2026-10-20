"""Compare matmul_bits.py's products: bit-identical entries and the largest difference in units in the
last place. Usage: matmul_compare.py name=file:row ... (a .json is a guest run, its stdout read)."""

import json
import sys

import numpy as np


def load(spec):
    name, rest = spec.split("=", 1)
    path, row = rest.rsplit(":", 1)
    text = open(path).read()
    if path.endswith(".json"):
        text = json.loads(text)["stdout"]
    for line in text.splitlines():
        w = line.split()
        if w and w[0] == row:
            return name, np.frombuffer(bytes.fromhex(w[1]), dtype=np.float64)
    raise SystemExit(f"no row {row} in {path}")


rows = dict(load(a) for a in sys.argv[1:])
names = list(rows)
for i, p in enumerate(names):
    for q in names[i + 1 :]:
        x, y = rows[p], rows[q]
        same = int((x == y).sum())
        ulps = np.abs(x.view(np.int64) - y.view(np.int64)).max()
        print(f"{p} vs {q}: {same}/{x.size} bit-identical, largest difference {ulps} ulp")
