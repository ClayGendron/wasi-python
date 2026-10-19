"""Spec 083 amendment: what a per-run copy of the stdlib zip costs, against a hard link (a benchmark
fact, not a test). Each of the 20 links or copies is removed after.
Usage: uv run python -I copy_cost.py <zip> <scratch dir>"""
import os, shutil, sys, time
from pathlib import Path
src, work = Path(sys.argv[1]), Path(sys.argv[2])
for how in ("link", "copyfile"):
    t = time.perf_counter()
    for i in range(20):
        d = work / f"{how}-{i}"
        if how == "link":
            os.link(src, d)
        else:
            shutil.copyfile(src, d)
    dt = (time.perf_counter() - t) / 20
    print(f"{how:9} {dt * 1000:7.2f} ms a run; nlink of the source {os.stat(src).st_nlink}; of a copy {os.stat(work / f'{how}-0').st_nlink}")
    for i in range(20):
        os.remove(work / f"{how}-{i}")
