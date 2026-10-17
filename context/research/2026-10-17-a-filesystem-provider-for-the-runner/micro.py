# The guest program for the per-call cost: N os.stat and N os.pread on one path.
# micro.sh writes N and WHERE into a copy before each run.
import os
N, WHERE = 0, "/data/in.csv"
for _ in range(N):
    os.stat(WHERE)
fd = os.open(WHERE, os.O_RDONLY)
for _ in range(N):
    os.pread(fd, 4, 0)
os.close(fd)
print("done", N, WHERE)
