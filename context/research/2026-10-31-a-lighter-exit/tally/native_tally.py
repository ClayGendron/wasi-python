"""Teardown's allocations through the three domains, natively (pinned host CPython 3.15.2):
bytes asked, calls, the largest request and frees, counted only once Python is finalizing; then
the same with frees skipped and drained past a 1 MiB budget. usage: native_tally.py <hostpy> <out.tsv>"""
import os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
END = f"\nimport sys\nsys.path.insert(0, {HERE!r})\nimport tally\ntally.install()\n"
W = {
    "pass": "pass",
    "json and csv": "import json, csv, io\nrows = [{'a': i, 'b': str(i)} for i in range(100)]\ns = io.StringIO(); w = csv.DictWriter(s, ['a', 'b']); w.writeheader(); w.writerows(rows)\nprint(len(json.dumps(rows)), len(s.getvalue()))",
    "import fractions, decimal, datetime, sqlite3, email, http.client": "import fractions, decimal, datetime, sqlite3, email, http.client",
    "200k __del__": "class D:\n    def __del__(self): pass\nkeep = [D() for i in range(200000)]",
    "200k cycles": "class N:\n    pass\nkeep = []\nfor i in range(200000):\n    a = N(); b = N(); a.o = b; b.o = a; keep.append(a)",
    "a 2M-key dict": "big = {i: str(i) for i in range(2 * 10**6)}",
    "1M strings on json": "import json\njson.cache = [str(i) * 3 for i in range(10**6)]",
    "sqlite uncommitted insert": "import sqlite3\nc = sqlite3.connect('t.db'); c.execute('create table t(x)'); c.commit(); c.execute('insert into t values (1)')",
    "finalizers churn 500 x 1 MiB": "class C:\n    def __del__(self):\n        for i in range(500):\n            b = bytes(1 << 20)\nkeep = C()",
    "weakref.finalize pickles 50 MB": "import weakref, pickle\nclass F: pass\nf = F()\ndata = list(range(5 * 10**6))\nweakref.finalize(f, lambda d: len(pickle.dumps(d)), data).atexit = False",
}
def go(hostpy, prog, env):
    d = tempfile.mkdtemp()
    p = subprocess.run([hostpy, "-I", "-c", prog + END], cwd=d, capture_output=True, env=env)
    line = [l for l in p.stderr.decode().splitlines() if l.startswith("tally:")]
    return p.returncode, (line[0][7:] if line else p.stderr.decode()[-200:].replace("\n", " "))
if __name__ == "__main__":
    hostpy, out = sys.argv[1], sys.argv[2]
    with open(out, "w") as fh:
        fh.write("call\tmode\texit\ttally\n")
        for name, prog in W.items():
            for mode, env in (("count", {}), ("skip, drain past 1 MiB", {"TALLY_SKIP": "1", "TALLY_B": str(1 << 20)})):
                rc, t = go(hostpy, prog, env)
                row = f"{name}\t{mode}\t{rc}\t{t}"
                print(row, flush=True); fh.write(row + "\n")
