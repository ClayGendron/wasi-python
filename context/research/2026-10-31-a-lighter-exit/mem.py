"""Teardown's memory: linear memory's size when the call ends, with today's teardown and with the
same call ending in os._exit(0), on the stock binaries and the spike that frees nothing.
Linear memory only grows, so the size at the end is the call's peak, and the difference is what
teardown grew it by. usage: mem.py <out.tsv>"""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(sys.argv[0])); sys.path.insert(0, HERE)
import wasmtime
from concurrent.futures import ProcessPoolExecutor

W = {
    "pass": "pass",
    "import numpy": "import numpy as np\nprint(np.arange(10).sum())",
    "pandas groupby": "import pandas as pd\ndf = pd.DataFrame({'k': [1, 2, 1, 2], 'v': [1.0, 2.0, 3.0, 4.0]})\nprint(df.groupby('k').v.sum().to_dict())",
    "pandas 1e6 rows": "import numpy as np, pandas as pd\ndf = pd.DataFrame({'k': np.arange(10**6) % 1000, 'v': np.random.default_rng(1).random(10**6), 's': [str(i % 5000) for i in range(10**6)]})\ng = df.groupby('k').agg({'v': 'sum', 's': 'nunique'})\nprint(len(g))",
    "200k __del__": "class D:\n    def __del__(self): pass\nkeep = [D() for i in range(200000)]",
    "200k cycles": "class N:\n    pass\nkeep = []\nfor i in range(200000):\n    a = N(); b = N(); a.o = b; b.o = a; keep.append(a)",
    "a 2M-key dict": "big = {i: str(i) for i in range(2 * 10**6)}",
    "1M strings, 50k modules-ish attrs": "import json\njson.cache = [str(i) * 3 for i in range(10**6)]",
}
BINS = {
    "stock": None,
    "nofree": os.path.join(HERE, "bins", "snap-nofree2.wasm"),
}
SIZES = []

def one(job):
    name, binary, end = job
    from drv import A, variant, go_with
    sizes = []
    orig_inst = wasmtime.Linker.instantiate
    orig_close = wasmtime.Store.close
    seen = {}
    def inst(self, store, module):
        i = orig_inst(self, store, module)
        seen[id(store)] = i
        return i
    def close(self):
        i = seen.pop(id(self), None)
        if i is not None:
            try:
                m = i.exports(self)["memory"]
                sizes.append(m.data_len(self))
            except Exception as e:
                sizes.append(repr(e))
        return orig_close(self)
    wasmtime.Linker.instantiate = inst
    wasmtime.Store.close = close
    arts = A if BINS[binary] is None else variant(BINS[binary])
    code = W[name] + ("\nimport os, sys\nsys.stdout.flush()\nos._exit(0)" if end == "os._exit" else "")
    d = tempfile.mkdtemp(dir=os.path.join(HERE, "tmp"))
    r = go_with(arts, code, root=d, memory_bytes=None)
    return name, binary, end, r.exit_code, r.fuel_used, sizes[-1] if sizes else "?"

if __name__ == "__main__":
    jobs = [(n, b, e) for n in W for b in BINS for e in ("teardown", "os._exit")]
    with ProcessPoolExecutor(6) as ex, open(sys.argv[1], "w") as fh:
        fh.write("call\tbinary\tending\texit\tfuel\tmemory_bytes\n")
        for row in ex.map(one, jobs):
            line = "\t".join(str(x) for x in row)
            print(line, flush=True)
            fh.write(line + "\n")
