"""Bounded local check (h02-fs-memory): drive the runner's mount and guard linkers with a raw
preview1 module and crafted 32-bit pointers, lengths, iovecs and dirent buffers, and record each
answer, whether the call was recorded as a stop, and whether any byte of guest memory outside the
call's declared result region changed. Uses the target's own test harness classes (read-only)."""
import hashlib, importlib.util, json, os, struct, sys, tempfile
from pathlib import Path

REPO = Path(".")
SCR = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("hfiles", REPO / "tests/harness/files.py")
H = importlib.util.module_from_spec(spec); sys.modules["hfiles"] = H; spec.loader.exec_module(H)
import wasmtime
from wasi_python import _fs_memory as M

END = H.MEMORY_END
out = []
def rec(name, **kw):
    out.append({"case": name, **kw}); print(name, kw)

def snapshot(raw):
    return bytes(raw.memory.read(raw.store, 0, END))

def diff(a, b):
    return [i for i in range(len(a)) if a[i] != b[i]]

def call(raw, name, *args, allowed=()):
    """Run one call with memory filled by 0xAA; report errno or stop, and changed byte ranges."""
    before = snapshot(raw)
    try:
        r = raw(name, *args); stop = None
    except H.Ends as e:
        r, stop = None, e.message
    after = snapshot(raw)
    ch = diff(before, after)
    outside = [i for i in ch if not any(lo <= i < hi for lo, hi in allowed)]
    return r, stop, (min(ch), max(ch) + 1, len(ch)) if ch else None, len(outside)

def fill(raw, keep=()):
    raw.put(0, b"\xaa" * END)

work = SCR / "work"; work.mkdir(exist_ok=True)
place = Path(tempfile.mkdtemp(dir=work, prefix="place-"))
grant = Path(tempfile.mkdtemp(dir=work, prefix="grant-"))
for i in range(6):
    (grant / f"f{i}.txt").write_bytes(b"x" * i)
(grant / "sub").mkdir()

# ---------------- the mount linker ----------------
prov = H.MemoryProvider()
m = H.Mounted(prov, place, writable=True)
r = m.raw
fill(r)
e, fd = r.open(3, "a.txt", rights=H.RIGHTS_ALL)
rec("mount.open a.txt", errno=e, fd=fd, provider_base=fd is not None and fd >= M.PROVIDER_BASE)
e, dfd = r.open(3, "d", oflags=H.O_DIRECTORY)
rec("mount.open d/", errno=e, fd=dfd)
NEG = lambda v: v - (1 << 32) if v >= 1 << 31 else v  # as wasmtime-py hands an i32 over

fill(r)
for ptr, label in ((END - 23, "end-23"), (END - 24, "end-24"), (NEG(0xFFFFFFF8), "0xFFFFFFF8"), (NEG(0x80000000), "0x80000000"), (END - 20, "end-20 misaligned")):
    res = call(r, "fd_fdstat_get", fd, ptr, allowed=[(ptr & M.MASK32, (ptr & M.MASK32) + 24)])
    rec(f"mount.fd_fdstat_get out={label}", errno=res[0], stop=res[1], changed=res[2], changed_outside=res[3])

for ptr, label in ((END - 63, "end-63"), (END - 64, "end-64")):
    res = call(r, "fd_filestat_get", fd, ptr, allowed=[(ptr, ptr + 64)])
    rec(f"mount.fd_filestat_get out={label}", errno=res[0], stop=res[1], changed=res[2], changed_outside=res[3])

def iov(at, pairs):
    r.put(at, b"".join(struct.pack("<II", b, n) for b, n in pairs))

cases = [
    ("buf=0xFFFFFFF0,len=0x20 (wraps 2**32)", H.IOVECS, [(0xFFFFFFF0, 0x20)], 1, H.RESULT),
    ("buf=end-4,len=5", H.IOVECS, [(END - 4, 5)], 1, H.RESULT),
    ("buf=end-4,len=4", H.IOVECS, [(END - 4, 4)], 1, H.RESULT),
    ("second iovec out of bounds", H.IOVECS, [(H.BUFFER, 4), (END, 1)], 2, H.RESULT),
    ("iovec array at end-4", END - 4, None, 1, H.RESULT),
    ("count=0x7FFFFFFF", H.IOVECS, [(H.BUFFER, 4)], 0x7FFFFFFF, H.RESULT),
    ("count=-1", H.IOVECS, [(H.BUFFER, 4)], -1, H.RESULT),
    ("nread at end-2", H.IOVECS, [(H.BUFFER, 4)], 1, END - 2),
    ("nread at 0xFFFFFFFC", H.IOVECS, [(H.BUFFER, 4)], 1, NEG(0xFFFFFFFC)),
    ("iovec array misaligned", H.IOVECS + 2, [(H.BUFFER, 4)], 1, H.RESULT),
]
for label, at, pairs, count, nread in cases:
    fill(r)
    if pairs is not None:
        iov(at, pairs)
    r("fd_seek", fd, 0, 0, H.RESULT)
    fill(r)
    if pairs is not None:
        iov(at, pairs)
    allowed = [(H.RESULT, H.RESULT + 4)]
    if pairs:
        allowed += [(b, b + n) for b, n in pairs if b + n <= END]
    res = call(r, "fd_read", fd, at, count, nread, allowed=allowed)
    rec(f"mount.fd_read {label}", errno=res[0], stop=res[1], changed=res[2], changed_outside=res[3])
    res = call(r, "fd_write", fd, at, count, nread, allowed=[(H.RESULT, H.RESULT + 4)])
    rec(f"mount.fd_write {label}", errno=res[0], stop=res[1], changed=res[2], changed_outside=res[3])

fill(r)
for off, wh in ((2**63 - 1, 0), (-1, 0), (-(2**63), 1), (2**63 - 1, 2)):
    res = call(r, "fd_seek", fd, off, wh, H.RESULT, allowed=[(H.RESULT, H.RESULT + 8)])
    rec(f"mount.fd_seek off={off} whence={wh}", errno=res[0], stop=res[1], pos=r.u64(H.RESULT) if res[0] == 0 else None, changed_outside=res[3])
r("fd_seek", fd, 2**63 - 1, 0, H.RESULT); r("fd_seek", fd, 2**63 - 1, 1, H.RESULT)
e, pos = r.tell(fd)
rec("mount.fd_tell after seeking to 2**64-2", errno=e, pos=pos)
iov(H.IOVECS, [(H.BUFFER, 4)])
res = call(r, "fd_read", fd, H.IOVECS, 1, H.RESULT, allowed=[(H.RESULT, H.RESULT + 4)])
rec("mount.fd_read at position 2**64-2", errno=res[0], stop=res[1], changed_outside=res[3])
res = call(r, "fd_write", fd, H.IOVECS, 1, H.RESULT, allowed=[(H.RESULT, H.RESULT + 4)])
rec("mount.fd_write at position 2**64-2", errno=res[0], stop=res[1], changed_outside=res[3])
res = call(r, "fd_pwrite", fd, H.IOVECS, 1, 2**63 - 8, H.RESULT, allowed=[(H.RESULT, H.RESULT + 4)])
rec("mount.fd_pwrite offset 2**63-8 (staging bound)", errno=res[0], stop=res[1], changed_outside=res[3])
res = call(r, "fd_pwrite", fd, H.IOVECS, 1, -1, H.RESULT, allowed=[(H.RESULT, H.RESULT + 4)])
rec("mount.fd_pwrite offset -1", errno=res[0], stop=res[1], changed_outside=res[3])
res = call(r, "fd_filestat_set_size", fd, -1)
rec("mount.fd_filestat_set_size -1", errno=res[0], stop=res[1], changed_outside=res[3])

fill(r)
for label, ptr, n in (("path at end-1 len 2", END - 1, 2), ("path len 0x7FFFFFFF", H.PATH, 0x7FFFFFFF), ("path len -1", H.PATH, -1), ("path ptr 0xFFFFFFFF len 1", NEG(0xFFFFFFFF), 1), ("path len 4097 in bounds", H.PATH, 4097)):
    res = call(r, "path_open", 3, 0, ptr, n, 0, H.READ_RIGHTS, H.READ_RIGHTS, 0, H.RESULT, allowed=[(H.RESULT, H.RESULT + 4)])
    rec(f"mount.path_open {label}", errno=res[0], stop=res[1], changed_outside=res[3])
    res = call(r, "path_filestat_get", 3, 0, ptr, n, H.RESULT, allowed=[(H.RESULT, H.RESULT + 64)])
    rec(f"mount.path_filestat_get {label}", errno=res[0], stop=res[1], changed_outside=res[3])
r.put(END - 5, b"a.txt")
res = call(r, "path_open", 3, 0, END - 5, 5, 0, H.READ_RIGHTS, H.READ_RIGHTS, 0, H.RESULT, allowed=[(H.RESULT, H.RESULT + 4)])
rec("mount.path_open path ending exactly at memory end", errno=res[0], stop=res[1], changed_outside=res[3])
r.put(H.PATH, b"a.txt")
res = call(r, "path_open", 3, 0, H.PATH, 5, 0, H.READ_RIGHTS, H.READ_RIGHTS, 0, END - 2, allowed=[])
rec("mount.path_open out at end-2", errno=res[0], stop=res[1], changed_outside=res[3])

# readdir on a mount folder
fill(r)
for label, buf, n, used in (
    ("buf end-10 len 20", END - 10, 20, H.RESULT),
    ("buf end-30 len 30", END - 30, 30, H.RESULT),
    ("buf len 0x7FFFFFFF", H.DIRBUF, 0x7FFFFFFF, H.RESULT),
    ("used inside buf", H.DIRBUF, 200, H.DIRBUF + 16),
    ("used at end-3", H.DIRBUF, 200, END - 3),
):
    res = call(r, "fd_readdir", dfd, buf, n, 0, used, allowed=[(buf, min(END, buf + n)), (used, used + 4)])
    pads = None
    if res[0] == 0:
        data = r.get(buf, min(n, END - buf))
        pads = [data[p + 21: p + 24].hex() for p in range(0, 24 * 3, 0) ] if False else None
    rec(f"mount.fd_readdir {label}", errno=res[0], stop=res[1], changed=res[2], changed_outside=res[3])
for cookie in (2**63, -1, 10**6):
    res = call(r, "fd_readdir", dfd, H.DIRBUF, 200, cookie, H.RESULT, allowed=[(H.DIRBUF, H.DIRBUF + 200), (H.RESULT, H.RESULT + 4)])
    rec(f"mount.fd_readdir cookie={cookie}", errno=res[0], stop=res[1], used=r.u32(H.RESULT) if res[0] == 0 else None, changed_outside=res[3])

# rename and readlink on the mount
fill(r)
r.put(END - 2, b"a/")
r.put(H.PATH2, b"zz")
res = call(r, "path_rename", 3, END - 2, 2, 3, H.PATH2, 2, allowed=[])
rec("mount.path_rename old ends at memory end with '/'", errno=res[0], stop=res[1], changed_outside=res[3])
res = call(r, "path_readlink", 3, H.PATH, 1, END - 4, 8, H.RESULT, allowed=[])
rec("mount.path_readlink buf end-4 len 8", errno=res[0], stop=res[1], changed_outside=res[3])

# ---------------- the guard linker ----------------
g = H.Guarded([(grant, "/g", True)])
q = g.raw

def pads(data):
    found, pos = [], 0
    while pos + 24 <= len(data):
        found.append(data[pos + 21: pos + 24].hex())
        pos += 24 + struct.unpack_from("<I", data, pos + 16)[0]
    return found

for label, buf, n, used in (
    ("plain listing", H.DIRBUF, 4096, H.RESULT),
    ("used over first d_namlen", H.DIRBUF, 4096, H.DIRBUF + 16),
    ("used over second entry header", H.DIRBUF, 4096, H.DIRBUF + 25 + 4),
    ("used just before buf (overlaps 2 bytes)", H.DIRBUF, 4096, H.DIRBUF - 2),
    ("buf at end-300, len 300", END - 300, 300, H.RESULT),
):
    fill(q)
    res = call(q, "fd_readdir", 3, buf, n, 0, used, allowed=[(buf, min(END, buf + n)), (used, used + 4)])
    info = {}
    if res[0] == 0:
        cnt = q.u32(used)
        data = bytearray(q.get(buf, cnt))
        info = {"used": cnt, "pads": pads(bytes(data))}
    rec(f"guard.fd_readdir {label}", errno=res[0], stop=res[1], changed_outside=res[3], **info)

# the trap path: a listing that crosses the end of memory, after some entries were written
fill(q)
buf = END - 60
res = call(q, "fd_readdir", 3, buf, 4096, 0, H.RESULT, allowed=[(buf, END)])
data = q.get(buf, 60)
rec("guard.fd_readdir buf end-60 len 4096 (crosses memory end)", errno=res[0], stop=res[1], changed=res[2], changed_outside=res[3], first_entries_pads=pads(data), raw_prefix=data[:56].hex())
fill(q)
res = call(q, "fd_readdir", 3, H.DIRBUF, 4096, 0, END - 2, allowed=[(H.DIRBUF, H.DIRBUF + 4096)])
data = q.get(H.DIRBUF, 400)
rec("guard.fd_readdir used at end-2 (trap after listing written)", errno=res[0], stop=res[1], changed=res[2], changed_outside=res[3], pads=pads(data)[:6])

# guarded rename with crafted spans
fill(q)
q.put(END - 2, b"x/")
q.put(H.PATH2, b"y")
res = call(q, "path_rename", 3, END - 2, 2, 3, H.PATH2, 1, allowed=[])
rec("guard.path_rename old 'x/' ends at memory end", errno=res[0], stop=res[1], changed_outside=res[3])
res = call(q, "path_rename", 3, NEG(0xFFFFFFFF), 2, 3, H.PATH2, 1, allowed=[])
rec("guard.path_rename old ptr 0xFFFFFFFF", errno=res[0], stop=res[1], changed_outside=res[3])
q.put(H.PATH, b"sub/" + b"/" * 5000)
res = call(q, "path_rename", 3, H.PATH, 5004, 3, H.PATH2, 1, allowed=[])
rec("guard.path_rename 5004-byte slash path", errno=res[0], stop=res[1], changed_outside=res[3])
q.put(H.PATH, b"f1.txt/")
res = call(q, "path_rename", 3, H.PATH, 7, 3, H.PATH2, 1, allowed=[])
rec("guard.path_rename file with slash", errno=res[0], stop=res[1], changed_outside=res[3])
q.put(H.PATH, b"f1.txt")
res = call(q, "path_open", 3, 0, H.PATH, 6, 0, H.READ_RIGHTS, H.READ_RIGHTS, 0, END - 2, allowed=[])
rec("guard.path_open out at end-2", errno=res[0], stop=res[1], changed_outside=res[3], held=sorted(g.table.held))

json.dump(out, open(SCR / "evidence" / "check_bounds.json", "w"), indent=1)
