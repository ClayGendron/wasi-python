"""Spec 083: does the host's file system give every write its own modification time? 5,000 writes
to one file, each followed by an fstat. Usage: uv run python -I granularity.py <scratch dir>"""
import collections
import os
import sys

path = os.path.join(sys.argv[1], "granularity.tmp")
fd = os.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY)
times = []
for _ in range(5000):
    os.write(fd, b"x")
    times.append(os.fstat(fd).st_mtime_ns)
os.close(fd)
os.remove(path)
steps = [b - a for a, b in zip(times, times[1:])]
print(f"writes 5000; distinct mtimes {len(set(times))}; repeats {sum(1 for s in steps if s == 0)}; "
      f"smallest step {min(steps)} ns; commonest {collections.Counter(steps).most_common(3)}")
