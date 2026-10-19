"""PC (spec 068): what shadowing path_open, fd_close and fd_renumber costs. Run once on main's
code and once with the prototype applied; the label says which. Host CPU: the guest times
20,000 open-and-close pairs on a granted file with its own monotonic clock (the host's), five
runs, median. Fuel: one metered run of a fixed file-heavy program; fuel_used must not move."""

import statistics
import sys
import tempfile
from pathlib import Path

from common068 import A

from wasi_python import Grant, run

label = sys.argv[1]
tmp = Path(tempfile.mkdtemp())
(tmp / "f.txt").write_bytes(b"x" * 100)
for i in range(50):
    (tmp / f"g{i}.csv").write_text("a,b\n1,2\n")

timed = r'''
import os, time
N = 20000
t = time.perf_counter_ns()
for _ in range(N):
    os.close(os.open("/data/f.txt", os.O_RDONLY))
pair = (time.perf_counter_ns() - t) / N
t = time.perf_counter_ns()
for _ in range(N):
    os.stat("/data/f.txt")
stat = (time.perf_counter_ns() - t) / N
print(f"{pair:.0f} {stat:.0f}")
'''
pairs, stats = [], []
for _ in range(5):
    r = run(["-c", timed], artifacts=A, grants=[Grant(tmp, "/data")], cache_dir=False)
    assert r.exit_code == 0, r.stderr.decode()[-500:]
    p, s = map(float, r.stdout.split())
    pairs.append(p)
    stats.append(s)
print(f"{label}: open+close pair median {statistics.median(pairs) / 1000:.2f} us "
      f"(runs {[round(p / 1000, 2) for p in pairs]}); os.stat control median "
      f"{statistics.median(stats) / 1000:.2f} us")

fixed = r'''
import csv, json, os, zipfile, glob
total = 0
for path in sorted(glob.glob("/data/*.csv")):
    with open(path) as f:
        total += sum(1 for _ in csv.reader(f))
for _ in range(2000):
    os.close(os.open("/data/f.txt", os.O_RDONLY))
print(total, len(os.listdir("/data")), json.dumps(sorted(os.listdir("/usr/local/lib"))))
'''
for snapshot in (True, False):
    used = []
    for _ in range(3):
        r = run(["-c", fixed], artifacts=A, grants=[Grant(tmp, "/data")], cache_dir=False,
                fuel=10**13, snapshot=snapshot, env={"PYTHONHASHSEED": "0"})
        assert r.exit_code == 0, r.stderr.decode()[-500:]
        used.append(r.fuel_used)
    print(f"{label}: snapshot={snapshot} fuel_used {used} stdout {r.stdout.decode().strip()}")
