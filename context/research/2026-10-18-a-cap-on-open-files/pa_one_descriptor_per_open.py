"""PA (spec 068): each file or folder a guest opens in a grant holds one host descriptor until it
closes it; a file opened in a mount holds none. Counted from inside a door call, while the guest
holds what it opened. Runs on main's code (no prototype needed)."""

import sys
import tempfile
from pathlib import Path

from common068 import A, host_fds

from wasi_python import Grant, Mount, run
from wasi_python.mounts import Errno, Stat

tmp = Path(tempfile.mkdtemp())
for i in range(300):
    (tmp / f"f{i}.txt").write_bytes(b"x")
(tmp / "sub").mkdir()


class Files:
    def stat(self, path):
        if path == "/":
            return Stat("dir")
        return Stat("file", 1) if path.startswith("/m") else Errno.ENOENT

    def list(self, path):
        return [(f"m{i}", "file") for i in range(300)] if path == "/" else Errno.ENOTDIR

    def read(self, path):
        if path == "/":
            return Errno.EISDIR
        return b"y" if path.startswith("/m") else Errno.ENOENT


seen = []


def host(frame: bytes) -> bytes:
    seen.append((frame.decode(), host_fds()))
    return b"ok"


code = r'''
import _host, os, sys
held = []
_host.call(b"start")
for n, where in ((100, "/data/f{}.txt"), (150, "/data/f{}.txt")):
    for i in range(len(held), len(held) + n):
        held.append(os.open(where.format(i), os.O_RDONLY))
    _host.call(b"files %d" % len(held))
d = [os.open("/data/sub", os.O_RDONLY | os.O_DIRECTORY) for _ in range(50)]
_host.call(b"plus 50 folders")
for fd in held + d:
    os.close(fd)
_host.call(b"closed all")
if len(sys.argv) > 1:
    m = [os.open("/mnt/m%d" % i, os.O_RDONLY) for i in range(200)]
    _host.call(b"200 mount files")
'''
r = run(["-c", code], artifacts=A, grants=[Grant(tmp, "/data")], host=host, cache_dir=False)
print("grants only:", r.exit_code, r.trapped, r.stderr.decode()[-300:])
base = seen[0][1]
for label, n in seen:
    print(f"  {label:<18} host descriptors {n}  (+{n - base})")
seen.clear()
r = run(
    ["-c", code, "mounts"],
    artifacts=A,
    grants=[Grant(tmp, "/data")],
    mounts=[Mount(Files(), "/mnt")],
    host=host,
    cache_dir=False,
)
print("with a mount:", r.exit_code, r.trapped, r.stderr.decode()[-300:])
base = seen[0][1]
for label, n in seen:
    print(f"  {label:<18} host descriptors {n}  (+{n - base})")
print("python", sys.version.split()[0])
