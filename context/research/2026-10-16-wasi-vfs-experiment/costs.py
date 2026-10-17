"""Fuel (exact) and wall time (benchmark, median of 5) for the cost table (memo finding 6).
Usage: costs.py <scratch dir> <repo> <mpl-data dir>"""

import shutil
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import drive  # noqa: E402

X, REPO, MPL = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT = X / "out"
ZIP = REPO / "build/out/python-stdlib.zip"
ZG = "/usr/local/lib/python314.zip/matplotlib/mpl-data"
PG = "/usr/local/share/wasi-python/mpl-data"
n = 0

READ_ALL = """
import os, sys
P = sys.argv[1]
total = 0
for d, dirs, files in os.walk(P):
    for f in files:
        with open(os.path.join(d, f), 'rb') as fh:
            total += len(fh.read())
print(total)
"""
ROOT_IO = """
import os
for i in range(2000):
    with open('/f%d' % (i % 20), 'w') as f:
        f.write('x' * 100)
    os.stat('/f%d' % (i % 20))
    with open('/f%d' % (i % 20)) as f:
        f.read()
print(len(os.listdir('/')))
"""


def root(zip_in_root=True, mpl_at=None):
    global n
    n += 1
    r = X / "croots" / f"c{n}"
    shutil.rmtree(r, ignore_errors=True)
    (r / "usr/local/lib").mkdir(parents=True)
    if zip_in_root:
        shutil.copyfile(ZIP, r / "usr/local/lib/python314.zip")
    if mpl_at:
        shutil.copytree(MPL, r / mpl_at.lstrip("/"))
    return r


def measure(label, wasm, argv, *, zip_in_root=True, mpl_at=None, with_root=True, repeat=5):
    fuels, walls, res = [], [], None
    for _ in range(repeat):
        pre = [(root(zip_in_root, mpl_at), "/", True)] if with_root else []
        t0 = time.perf_counter()
        res = drive.run(wasm, argv, preopens=pre, io=X / "cio" / f"c{n}")
        walls.append(time.perf_counter() - t0)
        fuels.append(res["fuel"])
    ok = res["exit"] == 0 and not res["trapped"]
    print(f"{label:58s} fuel {statistics.median(fuels):>13,.0f} (spread {max(fuels) - min(fuels)})"
          f"  wall {statistics.median(walls) * 1000:7.1f} ms  {'ok' if ok else 'FAIL ' + res['stderr'][-200:]}"
          f"  out={res['stdout'].strip()[:20]}")
    return statistics.median(fuels)


for wasm in ("control", "late", "packA", "packZ", "packZr"):
    drive.module(OUT / wasm / "python-snapshot.wasm")  # compile outside the timed runs
for wasm in ("control", "late", "packA"):
    drive.module(OUT / wasm / "python.wasm")

print("-- start: -c pass")
measure("control snapshot (today), root", OUT / "control/python-snapshot.wasm", ["-c", "pass"])
measure("late snapshot (vfs linked, nothing packed), root", OUT / "late/python-snapshot.wasm", ["-c", "pass"])
measure("packA snapshot (mpl-data packed), root", OUT / "packA/python-snapshot.wasm", ["-c", "pass"])
measure("packZ snapshot (zip + mpl packed), NO preopen", OUT / "packZ/python-snapshot.wasm", ["-c", "pass"], with_root=False)
measure("packZr snapshot (zip + mpl packed), root, no zip in it", OUT / "packZr/python-snapshot.wasm", ["-c", "pass"], zip_in_root=False)
measure("control plain reactor, root", OUT / "control/python.wasm", ["-c", "pass"], repeat=3)
measure("late plain reactor, root", OUT / "late/python.wasm", ["-c", "pass"], repeat=3)
measure("packA plain reactor, root", OUT / "packA/python.wasm", ["-c", "pass"], repeat=3)
print("-- start: import decimal, numpy (lazy stdlib import)")
measure("control snapshot, root", OUT / "control/python-snapshot.wasm", ["-c", "import decimal, fractions, numpy"])
measure("packZ snapshot, NO preopen", OUT / "packZ/python-snapshot.wasm", ["-c", "import decimal, fractions, numpy"], with_root=False)
print("-- read all of mpl-data (204 files)")
measure("control snapshot, data copied into the root (C1)", OUT / "control/python-snapshot.wasm", ["-c", READ_ALL, PG], mpl_at=PG)
measure("late snapshot, data copied into the root (vfs passthrough)", OUT / "late/python-snapshot.wasm", ["-c", READ_ALL, PG], mpl_at=PG)
measure("packA snapshot, data packed (C3)", OUT / "packA/python-snapshot.wasm", ["-c", READ_ALL, ZG])
print("-- ordinary file I/O in the root (2000 x open/write/close, stat, open/read/close)")
measure("control snapshot", OUT / "control/python-snapshot.wasm", ["-c", ROOT_IO])
measure("late snapshot (vfs linked)", OUT / "late/python-snapshot.wasm", ["-c", ROOT_IO])
measure("packA snapshot (vfs linked, data packed)", OUT / "packA/python-snapshot.wasm", ["-c", ROOT_IO])
