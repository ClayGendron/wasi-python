"""What a program leaves young at its end, by kind: the facts a 'skip when nothing to finalize'
exit would decide on. usage: census.py <out.tsv>"""
import sys, os
HERE = os.path.dirname(os.path.abspath(sys.argv[0])); sys.path.insert(0, HERE)
from concurrent.futures import ProcessPoolExecutor
from cands import wrapper
CENSUS = r'''
import collections, io, types
STD = {id(x) for s in (sys.__stdin__, sys.__stdout__, sys.__stderr__) for x in (s, getattr(s, "buffer", None), getattr(getattr(s, "buffer", None), "raw", None)) if x is not None}
def census(objs):
    c = collections.Counter()
    for o in objs:
        t = type(o)
        if id(o) in STD:
            c["std streams"] += 1
        elif isinstance(o, (types.GeneratorType, types.CoroutineType, types.AsyncGeneratorType)):
            c["generator, suspended" if getattr(o, "gi_suspended", getattr(o, "cr_suspended", getattr(o, "ag_suspended", True))) else "generator, not started or done"] += 1
        elif isinstance(o, io.IOBase):
            c["io " + ("closed" if o.closed else "OPEN")] += 1
        elif isinstance(o, weakref.ref) and o.__callback__ is not None:
            c["weakref with callback"] += 1
        elif hasattr(t, "__del__"):
            c["__del__: " + getattr(t, "__module__", "?") + "." + t.__qualname__] += 1
        elif t.__module__ == "builtins":
            c["builtin, inert"] += 1
        elif t.__flags__ & (1 << 9) and t.__dealloc__ if False else False:
            pass
        else:
            k = "python class" if "__dict__" in dir(t) and getattr(t, "__module__", "") not in ("builtins",) and not t.__module__.startswith("_") else "extension: " + str(t.__module__).split(".")[0]
            c[k] += 1
    return c
objs = gc.get_objects()
c = census(objs)
print("young", len(objs), dict(c.most_common(12)))
if RUN == 9:
    young = {id(o) for o in objs}
    del objs
    gc.unfreeze()
    allo = gc.get_objects()
    frozen = [o for o in allo if id(o) not in young]
    print("frozen", len(frozen), dict(census(frozen).most_common(12)))
'''
W = {
    "pass": "pass",
    "print": "print('hello')",
    "json and csv": "import json, csv, io\nrows = [{'a': i, 'b': str(i)} for i in range(100)]\ns = io.StringIO(); w = csv.DictWriter(s, ['a', 'b']); w.writeheader(); w.writerows(rows)\nprint(len(json.dumps(rows)), len(s.getvalue()))",
    "a class and a generator, finished": "class P:\n    def __init__(s, x): s.x = x\nps = [P(i) for i in range(1000)]\nprint(sum(p.x for p in ps))",
    "import numpy": "import numpy as np\nprint(np.arange(10).sum())",
    "pandas groupby": "import pandas as pd\ndf = pd.DataFrame({'k': [1, 2, 1, 2], 'v': [1.0, 2.0, 3.0, 4.0]})\nprint(df.groupby('k').v.sum().to_dict())",
}
def one(job):
    name, binary, run = job
    from drv import go
    src = wrapper(run, "c", W[name]).replace("raise SystemExit(rc)\n", CENSUS + "raise SystemExit(rc)\n")
    r = go(src, snap=binary == "snapshot")
    return name, binary, r.fuel_used, r.stdout.decode().strip().replace("\n", " | "), r.stderr.decode()[-300:]
if __name__ == "__main__":
    jobs = [(n, b, 9 if b == "snapshot" else 8) for n in W for b in ("snapshot", "plain")]
    with ProcessPoolExecutor(8) as ex, open(sys.argv[1], "w") as fh:
        for row in ex.map(one, jobs):
            line = "\t".join(map(str, row)); fh.write(line + "\n"); print(line[:1500], flush=True)
