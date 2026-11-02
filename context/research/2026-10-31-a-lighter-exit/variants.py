"""Fuel of plain -c programs, with today's ending and with os._exit, on the spike binaries.
usage: variants.py <out.tsv>"""
import sys, os
HERE = os.path.dirname(os.path.abspath(sys.argv[0])); sys.path.insert(0, HERE)
from concurrent.futures import ProcessPoolExecutor
B = {
    "today": (None, None),
    "E no-op free": ("bins/snap-nofree2.wasm", "bins/plain-nofree.wasm"),
    "D stop after modules": ("bins/snap-nointerp.wasm", "bins/plain-nointerp.wasm"),
    "D+E": ("bins/snap-nointerp-nofree.wasm", "bins/plain-both.wasm"),
}
W = {"pass": "pass", "import numpy": "import numpy as np\nprint(np.arange(10).sum())",
     "pandas groupby": "import pandas as pd\ndf = pd.DataFrame({'k': [1, 2, 1, 2], 'v': [1.0, 2.0, 3.0, 4.0]})\nprint(df.groupby('k').v.sum().to_dict())"}
def one(job):
    b, binary, w, exit_ = job
    from drv import go_with, variant, A
    path = B[b][0 if binary == "snapshot" else 1]
    arts = A if path is None else variant(os.path.join(HERE, path), snap=binary == "snapshot")
    code = W[w] + ("\nimport os; os._exit(0)" if exit_ else "\nimport os")
    r = go_with(arts, code, snap=binary == "snapshot")
    return b, binary, w, "os._exit" if exit_ else "finalize", r.fuel_used, r.exit_code, r.trapped
if __name__ == "__main__":
    jobs = [(b, bi, w, e) for b in B for bi in ("snapshot", "plain") for w in W for e in (0, 1) for _ in range(1 if bi == "snapshot" else 3)]
    with ProcessPoolExecutor(8) as ex, open(sys.argv[1], "w") as fh:
        for row in ex.map(one, jobs):
            fh.write("\t".join(map(str, row)) + "\n")
