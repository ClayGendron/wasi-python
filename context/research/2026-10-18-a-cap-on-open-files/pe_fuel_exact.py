"""PE (spec 068): the shadows' fuel, exactly. Needs prototype068.diff applied. The runner's linker
is given a fixed random_get and a counting clock_time_get (the clock-and-random memo's method),
so a program's fuel is the same on every run; then the three counted shadows are switched off
(`mounts.COUNTED = ()`, main's guard linker) and on, alternately, in one process."""

import struct
import tempfile
from pathlib import Path

from common068 import A

from wasi_python import Grant, Mount, mounts, run, runner
from wasi_python.mounts import Errno, Stat

original = runner._runner_linker
ticks = [0]


def fixed_linker(wt, engine):
    linker = original(wt, engine)
    i32, i64 = wt.ValType.i32(), wt.ValType.i64()

    def random_get(caller, ptr, n):
        caller.get("memory").write(caller, bytes((i * 7 + 1) & 0xFF for i in range(n)), ptr)
        return 0

    def clock_time_get(caller, clock, precision, out):
        ticks[0] += 1000
        caller.get("memory").write(caller, struct.pack("<Q", ticks[0]), out)
        return 0

    linker.define_func("wasi_snapshot_preview1", "random_get", wt.FuncType([i32, i32], [i32]), random_get, True)
    linker.define_func(
        "wasi_snapshot_preview1", "clock_time_get", wt.FuncType([i32, i64, i32], [i32]), clock_time_get, True
    )
    return linker


runner._runner_linker = fixed_linker
tmp = Path(tempfile.mkdtemp())
(tmp / "f.txt").write_bytes(b"x" * 100)
for i in range(50):
    (tmp / f"g{i}.csv").write_text("a,b\n1,2\n")


class Files:
    def stat(self, path):
        return Stat("dir") if path == "/" else Stat("file", 4)

    def list(self, path):
        return [(f"m{i}", "file") for i in range(20)] if path == "/" else Errno.ENOTDIR

    def read(self, path):
        return Errno.EISDIR if path == "/" else b"a,b\n"


fixed = r'''
import csv, glob, json, os
total = 0
for path in sorted(glob.glob("/data/*.csv")):
    with open(path) as f:
        total += sum(1 for _ in csv.reader(f))
for _ in range(2000):
    os.close(os.open("/data/f.txt", os.O_RDONLY))
if os.path.isdir("/mnt"):
    for name in sorted(os.listdir("/mnt")):
        with open("/mnt/" + name) as f:
            total += len(f.read())
print(total, len(os.listdir("/data")))
'''
counted = mounts.COUNTED
for snapshot in (True, False):
    for label, kw in (("grants", {}), ("grants+mount", {"mounts": [Mount(Files(), "/mnt")]})):
        seen = {"off": [], "on": []}
        for _ in range(3):
            for state in ("off", "on"):
                mounts.COUNTED = () if state == "off" else counted
                runner._guard_linkers.clear()
                ticks[0] = 0
                r = run(["-c", fixed], artifacts=A, grants=[Grant(tmp, "/data")], cache_dir=False,
                        fuel=10**13, snapshot=snapshot, env={"PYTHONHASHSEED": "0"}, **kw)
                assert r.exit_code == 0, r.stderr.decode()[-500:]
                seen[state].append(r.fuel_used)
        print(f"snapshot={snapshot} {label}: shadows off {seen['off']}  on {seen['on']}  "
              f"delta {seen['on'][0] - seen['off'][0]}  stdout {r.stdout.decode().strip()}")
