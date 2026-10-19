"""Spec 073's build: a benchmark fact (never a test assertion): wall-clock of one warm snapshot
call, `-c pass`, through wasi_python.run, on the built set; the median of 15 after 3 warm-ups.

    uv run python <this file>
"""

import statistics
import time

import wasi_python

for _ in range(3):
    wasi_python.run(["-c", "pass"])
times = []
for _ in range(15):
    t0 = time.perf_counter()
    done = wasi_python.run(["-c", "pass"])
    times.append(time.perf_counter() - t0)
    assert done.exit_code == 0, done
print(f"snapshot -c pass: median {statistics.median(times) * 1000:.1f} ms over 15 "
      f"(min {min(times) * 1000:.1f}, max {max(times) * 1000:.1f})")
