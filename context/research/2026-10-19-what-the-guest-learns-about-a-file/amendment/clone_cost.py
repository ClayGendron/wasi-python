"""Spec 083 amendment, the review's optional point: an APFS clone (clonefile(2), as `cp -c` makes)
of the stdlib zip, by ctypes: its cost against a copy, and its link count (a benchmark fact, not a
test). Each clone is removed after. Usage: uv run python -I clone_cost.py <zip> <scratch dir>"""
import ctypes, os, shutil, sys, time
from pathlib import Path
src, work = Path(sys.argv[1]), Path(sys.argv[2])
libc = ctypes.CDLL(None, use_errno=True)
for how in ("clonefile", "copyfile"):
    t = time.perf_counter()
    for i in range(20):
        d = work / f"{how}-{i}"
        if how == "clonefile":
            if libc.clonefile(os.fsencode(src), os.fsencode(d), 0) != 0:
                raise OSError(ctypes.get_errno(), "clonefile")
        else:
            shutil.copyfile(src, d)
    dt = (time.perf_counter() - t) / 20
    print(f"{how:9} {dt * 1000:6.2f} ms a run; nlink of a result {os.stat(work / f'{how}-0').st_nlink}; "
          f"same inode as the source {os.stat(work / f'{how}-0').st_ino == os.stat(src).st_ino}")
    for i in range(20):
        os.remove(work / f"{how}-{i}")
