"""Fuel of each ending over small workloads. usage: work.py <out.tsv> <cands comma list> [reps_plain]"""
import sys, os
HERE = os.path.dirname(os.path.abspath(sys.argv[0])); sys.path.insert(0, HERE)
from concurrent.futures import ProcessPoolExecutor
from cands import wrapper, NAMES
W = {
    "pass": "pass",
    "print": "print('hello')",
    "json and csv": "import json, csv, io\nrows = [{'a': i, 'b': str(i)} for i in range(100)]\ns = io.StringIO(); w = csv.DictWriter(s, ['a', 'b']); w.writeheader(); w.writerows(rows)\nprint(len(json.dumps(rows)), len(s.getvalue()))",
    "1,000 instances": "class P:\n    def __init__(s, x): s.x = x\nps = [P(i) for i in range(1000)]\nprint(sum(p.x for p in ps))",
    "a file closed by with": "with open('a.txt', 'w') as f: f.write('x' * 100)\nprint(open('a.txt').read()[:3])",
    "a file left open": "f = open('a.txt', 'w'); f.write('x' * 100)",
    "import fractions, decimal, datetime": "import fractions, decimal, datetime\nprint(fractions.Fraction(1, 3) + 1, decimal.Decimal('1.1') * 3, datetime.date(2026, 1, 1))",
    "import numpy": "import numpy as np\nprint(np.arange(10).sum())",
    "pandas groupby": "import pandas as pd\ndf = pd.DataFrame({'k': [1, 2, 1, 2], 'v': [1.0, 2.0, 3.0, 4.0]})\nprint(df.groupby('k').v.sum().to_dict())",
}
def one(job):
    name, binary, run = job
    import tempfile
    from drv import go
    d = tempfile.mkdtemp(dir=os.path.join(HERE, "tmp"))
    r = go(wrapper(run, "c", W[name]), snap=binary == "snapshot", root=d, env={"LX_WHY": "1"} if run == 6 else None)
    why = [l[5:] for l in r.stderr.decode(errors="replace").splitlines() if l.startswith("why:")]
    return name, binary, NAMES[run], r.fuel_used, r.exit_code, (why[0] if why else ""), r.stdout.decode()[:60].strip()
if __name__ == "__main__":
    cands = [int(c) for c in sys.argv[2].split(",")]
    reps = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    jobs = [(n, b, c) for n in W for c in cands for b in ("snapshot", "plain") for _ in range(1 if b == "snapshot" else reps)]
    with ProcessPoolExecutor(8) as ex, open(sys.argv[1], "w") as fh:
        for row in ex.map(one, jobs):
            line = "\t".join(map(str, row)); fh.write(line + "\n"); print(line, flush=True)
