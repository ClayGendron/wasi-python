"""PG (spec 068): criteria 1 and 2's raw rows, tried on the prototype (prototype068.diff applied)
through the judge's own raw harnesses, `tests/harness/files.py`'s Guarded and Mounted."""

import struct
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tests"))
from harness import files  # noqa: E402

R = files.RESULT


def opener(raw, fd, name, oflags=0):
    raw.put(files.PATH, name.encode())
    errno = raw("path_open", fd, 0, files.PATH, len(name), oflags, files.READ_RIGHTS, 0, 0, R)
    return errno, struct.unpack("<I", raw.get(R, 4))[0] if errno == 0 else None


tmp = Path(tempfile.mkdtemp())
for i in range(5):
    (tmp / f"f{i}").write_bytes(b"x")
(tmp / "sub").mkdir()

g = files.Guarded([(tmp, "/w", False)])
g.table.open_files = 3
forwarded = []
real = g.table.forward


def counting(caller, name, args, stat=False):
    forwarded.append(name)
    return real(caller, name, args, stat)


g.table.forward = counting
raw = g.raw
got = [opener(raw, 3, "f0"), opener(raw, 3, "f1"), opener(raw, 3, "sub", files.O_DIRECTORY)]
print("three opens:", got)
print("fourth:", opener(raw, 3, "f2"), "forwarded path_open", forwarded.count("path_open"))
print("missing at cap:", opener(raw, 3, "nope"), "forwarded", forwarded.count("path_open"))
a, b = got[0][1], got[1][1]
print("close a:", raw("fd_close", a), "open:", opener(raw, 3, "f2"), "next:", opener(raw, 3, "f3"))
held = [n for _, n in got[1:]] + []
c = opener(raw, 3, "f2")  # at cap -> EMFILE
print("close b:", raw("fd_close", b), "missing:", opener(raw, 3, "nope"), "then:", opener(raw, 3, "f4"))
print("close 2**20:", raw("fd_close", 2**20), "open:", opener(raw, 3, "f0"))
print("close stdin:", raw("fd_close", 0), "open:", opener(raw, 3, "f0"))
print("table held:", sorted(g.table.held))
x, y = sorted(g.table.held)[:2]
print("renumber held->held:", raw("fd_renumber", x, y), "open:", opener(raw, 3, "f0"), "next:", opener(raw, 3, "f1"))
z = sorted(g.table.held)[0]
print("renumber held->1:", raw("fd_renumber", z, 1), "open:", opener(raw, 3, "f1"), "close 1:", raw("fd_close", 1), "open:", opener(raw, 3, "f1"))
print("renumber (2**31-1)x2 guarded:", raw("fd_renumber", 2**31 - 1, 2**31 - 1))
p = files.grant_raw([(tmp, "/w", False)])
print("renumber (2**31-1)x2 plain:", p("fd_renumber", 2**31 - 1, 2**31 - 1))
g2 = files.Guarded([(tmp, "/w", False)])
g2.table.open_files = None
print("None, 50 opens:", {opener(g2.raw, 3, "f%d" % (i % 5))[0] for i in range(50)})

print("--- mounts")
ph = Path(tempfile.mkdtemp())
prov = files.MemoryProvider()
m = files.Mounted(prov, ph, folders=[(tmp, "/w", False)])
m.table.open_files = 4
mr = m.raw
print("two mount, two folder:", opener(mr, 3, "a.txt"), opener(mr, 3, "b.txt"), opener(mr, 4, "f0"), opener(mr, 4, "f1"))
print("fifth folder:", opener(mr, 4, "f2"), "fifth mount:", opener(mr, 3, "a.txt"), "reads", m.table.record().calls["read"])
