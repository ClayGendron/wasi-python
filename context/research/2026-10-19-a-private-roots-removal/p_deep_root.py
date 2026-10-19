"""Spec 084's F1 probe: a guest given root=True builds a tree D levels deep through dir_fd,
holding one descriptor at a time; what does the runner's removal leave?

usage: p_deep_root.py SOFT DEPTH TEMP {run|session}
Prints one JSON line. Counts things; times nothing."""

import json
import os
import resource
import shutil
import sys
import tempfile

soft, depth, temp, mode = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4]
hard = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
resource.setrlimit(resource.RLIMIT_NOFILE, (soft, hard))
tempfile.tempdir = temp

import wasi_python  # noqa: E402
from wasi_python import runner  # noqa: E402

GUEST = f"""
import os
fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
for i in range({depth}):
    os.mkdir("a", dir_fd=fd)
    n = os.open("a", os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd); os.close(fd); fd = n
os.close(fd)
print("built", {depth})
"""

real_rmtree = shutil.rmtree
seen = {"calls": 0, "errors": {}, "open_fds_at_remove": []}


def rmtree(path, ignore_errors=False, onerror=None, *, onexc=None, dir_fd=None):
    seen["calls"] += 1
    seen["open_fds_at_remove"].append(len(os.listdir("/dev/fd")) - 1)

    def note(func, p, exc):
        key = f"{getattr(func, '__name__', func)}:{type(exc).__name__}:{getattr(exc, 'errno', None)}"
        seen["errors"][key] = seen["errors"].get(key, 0) + 1

    try:
        real_rmtree(path, onexc=note, dir_fd=dir_fd)
    except BaseException as e:  # noqa: BLE001
        k = f"raised:{type(e).__name__}"
        seen["errors"][k] = seen["errors"].get(k, 0) + 1
        if not ignore_errors:
            raise


rmtree.avoids_symlink_attacks = real_rmtree.avoids_symlink_attacks
shutil.rmtree = rmtree
open_before = len(os.listdir("/dev/fd")) - 1
raised = None
try:
    if mode == "run":
        done = wasi_python.run(["-c", GUEST], root=True)
        exit_code, out = done.exit_code, done.stdout
    else:
        with wasi_python.Session(root=True) as s:
            done = s.run(GUEST)
            exit_code, out = done.exit_code, done.stdout
except BaseException as e:  # noqa: BLE001
    raised, exit_code, out = f"{type(e).__name__}: {e}"[:200], None, b""


def deepest(p):
    n = 0
    fd = os.open(p, os.O_RDONLY | os.O_DIRECTORY)
    try:
        while True:
            try:
                nfd = os.open("a", os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd)
            except FileNotFoundError:
                return n
            os.close(fd)
            fd, n = nfd, n + 1
    finally:
        os.close(fd)


left = sorted(n for n in os.listdir(temp) if n.startswith("wasi-python-"))
roots = [n for n in left if n.startswith("wasi-python-root-") and not n.endswith(".lock")]
print(
    json.dumps(
        {
            "python": sys.version.split()[0],
            "soft": soft,
            "depth": depth,
            "mode": mode,
            "open_fds_before_call": open_before,
            "exit_code": exit_code,
            "stdout": out if isinstance(out, str) else out.decode(errors="replace"),
            "raised": raised,
            "rmtree_calls": seen["calls"],
            "open_fds_at_remove": seen["open_fds_at_remove"],
            "rmtree_errors": seen["errors"],
            "left": left,
            "levels_left": {r: deepest(os.path.join(temp, r, "a")) + 1 for r in roots
                            if os.path.isdir(os.path.join(temp, r, "a"))},
        }
    )
)
