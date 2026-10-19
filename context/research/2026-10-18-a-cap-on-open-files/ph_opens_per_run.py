"""PH (spec 068): how many counted calls typical runs make, so the per-call cost (PF) can be put
per run. Needs prototype068.diff applied. Counts the table's dispatch by name."""

import collections
import tempfile
from pathlib import Path

from common068 import A

from wasi_python import Grant, run
from wasi_python.mounts import _Files

seen = collections.Counter()
real = _Files.__call__


def counting(self, caller, name, *args):
    seen[name] += 1
    return real(self, caller, name, *args)


_Files.__call__ = counting
tmp = Path(tempfile.mkdtemp())
(tmp / "sales.csv").write_text("region,total\n" + "".join(f"r{i % 5},{i}\n" for i in range(1000)))
cases = [
    ("snapshot", True, "pass"),
    ("snapshot", True, "import json, csv, decimal, pathlib"),
    ("snapshot", True, "import pandas as pd; print(pd.read_csv('/data/sales.csv').groupby('region').total.sum().sum())"),
    ("plain", False, "pass"),
    ("plain", False, "import json, csv, decimal, pathlib"),
    ("plain", False, "import pandas as pd; print(pd.read_csv('/data/sales.csv').groupby('region').total.sum().sum())"),
]
for label, snap, code in cases:
    seen.clear()
    r = run(["-c", code], artifacts=A, grants=[Grant(tmp, "/data")], cache_dir=False, snapshot=snap)
    print(f"{label:<8} exit {r.exit_code} path_open {seen['path_open']:>4} fd_close {seen['fd_close']:>4} "
          f"fd_renumber {seen['fd_renumber']}  | {code[:70]}")
