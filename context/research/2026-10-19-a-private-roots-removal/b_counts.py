"""Spec 084's built removal: counted calls and peak descriptors on the checks' trees (a 1,000-level
tree with a file at each level; a 5,300-entry wide folder), by wrapping os functions. Counts only.
usage: uv run python b_counts.py WORK"""
import os, sys
from wasi_python import runner
work = sys.argv[1]
os.makedirs(work, exist_ok=True)
ok = runner._dir_fd_ok()
runner._dir_fd_ok = lambda: ok
names = ("open", "close", "scandir", "unlink", "rmdir", "chmod", "fchmod", "mkdir", "rename")
counts, live = dict.fromkeys(names, 0), {"now": 0, "peak": 0}
real = {n: getattr(os, n) for n in names}

def wrap(n):
    def f(*a, **k):
        counts[n] += 1
        r = real[n](*a, **k)
        if n == "open":
            live["now"] += 1
        elif n == "close":
            live["now"] -= 1
        elif n == "scandir":
            live["peak"] = max(live["peak"], live["now"] + 1)
        live["peak"] = max(live["peak"], live["now"])
        return r
    return f

def deep(top, depth):
    os.mkdir(top); fd = os.open(top, os.O_RDONLY | os.O_DIRECTORY)
    for _ in range(depth):
        os.close(os.open("f", os.O_CREAT | os.O_WRONLY, 0o644, dir_fd=fd)); os.mkdir("a", dir_fd=fd)
        n = os.open("a", os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd); os.close(fd); fd = n
    os.close(fd)
    return 2 * depth

def wide(top):
    os.mkdir(top)
    for i in range(5000): open(os.path.join(top, f"f{i}"), "w").close()
    for i in range(300): os.mkdir(os.path.join(top, f"d{i}"))
    return 5300

for label, make in (("deep 1,000 levels + a file each", lambda p: deep(p, 1000)), ("wide 5,000 files + 300 folders", wide)):
    top = os.path.join(work, "t")
    entries = make(top)
    for k in counts: counts[k] = 0
    live.update(now=0, peak=0)
    for n in names: setattr(os, n, wrap(n))
    try:
        gone = runner._remove_tree(top)
    finally:
        for n in names: setattr(os, n, real[n])
    c = sum(counts[n] for n in ("open", "scandir", "unlink", "rmdir"))
    print(f"{label}: gone={gone} entries={entries} counted={c} ({c / entries:.2f} per entry) "
          f"peak descriptors={live['peak']} {dict((k, v) for k, v in counts.items() if v)}")
