"""PD (spec 068): the prototype's cap, counted. Needs prototype068.diff applied to main 434a811:
the cap is then the private `runner._PROTO_OPEN_FILES` (default 1024), not yet a keyword."""

import sys
import tempfile
from pathlib import Path

from common068 import A

from wasi_python import Grant, Mount, run, runner
from wasi_python.mounts import Errno, Stat

tmp = Path(tempfile.mkdtemp())
for i in range(40):
    (tmp / f"f{i}.txt").write_bytes(b"x")
    (tmp / f"d{i}").mkdir()


class Files:
    def stat(self, path):
        return Stat("dir") if path == "/" else Stat("file", 1)

    def list(self, path):
        return [(f"m{i}", "file") for i in range(40)] if path == "/" else Errno.ENOTDIR

    def read(self, path):
        return Errno.EISDIR if path == "/" else b"y"


def go(cap, code, **kw):
    runner._PROTO_OPEN_FILES = cap
    r = run(["-c", code], artifacts=A, grants=[Grant(tmp, "/data")], cache_dir=False, **kw)
    out = r.stdout.decode().strip()
    print(f"cap={cap}: exit {r.exit_code} trapped {r.trapped} | {out} {r.stderr.decode()[-300:]}")
    return r


print("1. a grant, cap 16: open until refused; a close frees exactly one slot")
go(16, r'''
import errno, os
held = []
try:
    while True:
        held.append(os.open("/data/f%d.txt" % (len(held) % 40), os.O_RDONLY))
except OSError as e:
    print("opened", len(held), "then", errno.errorcode[e.errno], repr(e.strerror), end="; ")
os.close(held.pop())
held.append(os.open("/data/f0.txt", os.O_RDONLY))
try:
    os.open("/data/f1.txt", os.O_RDONLY); print("17th opened (wrong)", end="; ")
except OSError as e:
    print("after close+open, next is", errno.errorcode[e.errno], end="; ")
try:
    os.listdir("/data")
except OSError as e:
    print("listdir at the cap:", errno.errorcode[e.errno], end="; ")
try:
    open("/data/missing")
except OSError as e:
    print("a missing file at the cap:", errno.errorcode[e.errno], end="; ")
for fd in held: os.close(fd)
again = [os.open("/data/f%d.txt" % i, os.O_RDONLY) for i in range(16)]
print("after closing all, opened", len(again), "again")
''')

print("2. folders count: 8 folders + 8 files, cap 16")
go(16, r'''
import errno, os
d = [os.open("/data/d%d" % i, os.O_RDONLY | os.O_DIRECTORY) for i in range(8)]
f = [os.open("/data/f%d.txt" % i, os.O_RDONLY) for i in range(8)]
try:
    os.open("/data/d9", os.O_RDONLY | os.O_DIRECTORY); print("17th opened (wrong)")
except OSError as e:
    print("17th:", errno.errorcode[e.errno])
''')

print("3. mounts count too, cap 16: 10 mount files + 6 grant files")
r = go(16, r'''
import errno, os
m = [os.open("/mnt/m%d" % i, os.O_RDONLY) for i in range(10)]
g = [os.open("/data/f%d.txt" % i, os.O_RDONLY) for i in range(6)]
for where in ("/data/f7.txt", "/mnt/m11"):
    try:
        os.open(where, os.O_RDONLY); print(where, "opened (wrong)", end="; ")
    except OSError as e:
        print(where, errno.errorcode[e.errno], end="; ")
os.close(m.pop())
g.append(os.open("/data/f8.txt", os.O_RDONLY))
print("a mount close freed a slot for a grant file")
''', mounts=[Mount(Files(), "/mnt")])
print("   provider reads:", r.files.calls["read"], "(10 opens; the refused one made none)")

print("4. the default, 1024: exactly 1024 opens, then EMFILE, and the run goes on")
go(1024, r'''
import errno, os
held = []
try:
    while True:
        held.append(os.open("/data/f%d.txt" % (len(held) % 40), os.O_RDONLY))
except OSError as e:
    print("opened", len(held), "then", errno.errorcode[e.errno], end="; ")
print("still running")
''')

print("5. None: no cap; 3000 opens")
go(None, r'''
import os
held = [os.open("/data/f%d.txt" % (i % 40), os.O_RDONLY) for i in range(3000)]
print("opened", len(held))
''')

print("6. cap 0: what still works")
for snap in (True, False):
    for code in ("print(1)", "import json; print(json.dumps([1]))", "import csv; print(csv.__name__)"):
        print(f"   snapshot={snap} {code!r}:", end=" ")
        go(0, code, snapshot=snap)

print("7. files left open at exit do not carry into the next call")
go(4, "import os; [os.open('/data/f%d.txt' % i, os.O_RDONLY) for i in range(4)]; print('held 4')")
go(4, "import os; [os.open('/data/f%d.txt' % i, os.O_RDONLY) for i in range(4)]; print('held 4 again')")

print("8. cap 1 and 2 on the plain reactor: the zip needs one at a time")
for cap in (1, 2):
    print(f"   snapshot=False cap={cap}:", end=" ")
    go(cap, "import json, csv, decimal; print(json.dumps([1]), decimal.Decimal(1))", snapshot=False)
