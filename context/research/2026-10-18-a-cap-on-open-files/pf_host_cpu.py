"""PF (spec 068): the shadows' host CPU per open and close. Needs prototype068.diff applied. One
process; the three counted shadows switched off (main's guard linker) and on, alternately, ten
rounds each. The guest times 20,000 open-and-close pairs on a granted file with its monotonic
clock (the host's), and 20,000 os.stat calls as a control the shadows do not touch. A benchmark
fact of this machine, never a check."""

import statistics
import tempfile
from pathlib import Path

from common068 import A

from wasi_python import Grant, mounts, run, runner

tmp = Path(tempfile.mkdtemp())
(tmp / "f.txt").write_bytes(b"x" * 100)
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
print(f"{pair:.0f} {(time.perf_counter_ns() - t) / N:.0f}")
'''
counted = mounts.COUNTED
seen = {"off": ([], []), "on": ([], [])}
for _ in range(10):
    for state in ("off", "on"):
        mounts.COUNTED = () if state == "off" else counted
        runner._guard_linkers.clear()
        r = run(["-c", timed], artifacts=A, grants=[Grant(tmp, "/data")], cache_dir=False)
        assert r.exit_code == 0, r.stderr.decode()[-500:]
        pair, stat = map(float, r.stdout.split())
        seen[state][0].append(pair / 1000)
        seen[state][1].append(stat / 1000)
for state, (pairs, stats) in seen.items():
    print(f"shadows {state}: open+close median {statistics.median(pairs):.2f} us "
          f"(min {min(pairs):.2f}, max {max(pairs):.2f}); os.stat median {statistics.median(stats):.2f} us")
off, on = statistics.median(seen["off"][0]), statistics.median(seen["on"][0])
print(f"added per open+close pair: {on - off:.2f} us (medians); "
      f"per 1,024 pairs: {(on - off) * 1024 / 1000:.2f} ms")

# A whole run that opens many files: the plain reactor importing pandas from the zip (919
# path_open and 919 fd_close, ph_opens_per_run.txt). Host wall time per run, alternately.
import time  # noqa: E402

whole = {"off": [], "on": []}
for _ in range(6):
    for state in ("off", "on"):
        mounts.COUNTED = () if state == "off" else counted
        runner._guard_linkers.clear()
        t = time.perf_counter()
        r = run(["-c", "import pandas"], artifacts=A, cache_dir=False, snapshot=False)
        whole[state].append(time.perf_counter() - t)
        assert r.exit_code == 0, r.stderr.decode()[-500:]
for state, times in whole.items():
    print(f"plain reactor, import pandas, shadows {state}: median {statistics.median(times) * 1000:.0f} ms "
          f"(min {min(times) * 1000:.0f}, max {max(times) * 1000:.0f})")
