"""A filesystem provider under the real artifact set, through shadowed preview1 calls.

uv run --no-sync python shadow.py ART_DIR SCRATCH MODE [PROGRAM_FILE]

MODE is one of
  plain     the runner's shape today: define_wasi, nothing shadowed (the baseline)
  passthru  the 26 file calls shadowed by Python, every call forwarded to wasmtime's own WASI
            through a trampoline instance (no provider mount): the cost of the shadow alone
  provider  as passthru, plus an in-memory provider mounted at /work; a real read-only grant
            at /data keeps working beside it

Prints: exit code, stdout, stderr, guest fuel, the count of each shadowed call, and wall time
(a benchmark fact, never a test). Nothing here is the runner's code; it is a model of it.
"""

from __future__ import annotations

import collections
import os
import struct
import sys
import time
from pathlib import Path

import wasmtime as wt

ART, SCRATCH, MODE = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
PROGRAM = Path(sys.argv[4]).read_text() if len(sys.argv) > 4 else "print('hi')"
P1 = "wasi_snapshot_preview1"
M32 = 0xFFFFFFFF

# preview1 numbers
OK, ACCES, BADF, EXIST, INVAL, ISDIR, NOENT, NOTDIR, NOTEMPTY, NOTSUP = 0, 2, 8, 20, 28, 31, 44, 54, 55, 58
NOTCAPABLE, SPIPE, PERM = 76, 70, 63
DIR_T, FILE_T = 3, 4
O_CREAT, O_DIRECTORY, O_EXCL, O_TRUNC = 1, 2, 4, 8
APPEND = 1
FILE_CALLS = """fd_advise fd_close fd_datasync fd_fdstat_get fd_fdstat_set_flags fd_filestat_get
fd_filestat_set_size fd_filestat_set_times fd_pread fd_pwrite fd_read fd_readdir fd_seek fd_sync
fd_tell fd_write path_create_directory path_filestat_get path_filestat_set_times path_link
path_open path_readlink path_remove_directory path_rename path_symlink path_unlink_file""".split()
# the calls whose first argument is not the fd they act on
NOT_FD_FIRST = {"path_symlink"}  # (old_path, old_len, fd, new_path, new_len)


# ---------------------------------------------------------------- an embedder's provider (model)


class FsError(Exception):
    def __init__(self, errno: int) -> None:
        self.errno = errno


class MemoryProvider:
    """The interface under test: whole-file verbs on normalized paths relative to the mount."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {"seed.txt": b"from the provider\n"}
        self.dirs: set[str] = {""}
        self.calls: collections.Counter[str] = collections.Counter()

    def stat(self, path: str) -> tuple[str, int]:
        self.calls["stat"] += 1
        if path in self.dirs:
            return "dir", 0
        if path in self.files:
            return "file", len(self.files[path])
        raise FsError(NOENT)

    def read(self, path: str) -> bytes:
        self.calls["read"] += 1
        if path in self.dirs:
            raise FsError(ISDIR)
        if path not in self.files:
            raise FsError(NOENT)
        return self.files[path]

    def write(self, path: str, data: bytes) -> None:
        self.calls["write"] += 1
        parent = path.rpartition("/")[0]
        if parent not in self.dirs:
            raise FsError(NOENT)
        if path.endswith("denied.txt"):
            raise FsError(ACCES)  # a refused write-back, to see it reach the guest at close
        self.files[path] = bytes(data)

    def list(self, path: str) -> list[tuple[str, str]]:
        self.calls["list"] += 1
        if path not in self.dirs:
            raise FsError(NOTDIR if path in self.files else NOENT)
        pre = "" if path == "" else path + "/"
        out = []
        for p in sorted(self.dirs | set(self.files)):
            if p and p.startswith(pre) and "/" not in p[len(pre):]:
                out.append((p[len(pre):], "dir" if p in self.dirs else "file"))
        return out

    def mkdir(self, path: str) -> None:
        self.calls["mkdir"] += 1
        if path in self.dirs or path in self.files:
            raise FsError(EXIST)
        self.dirs.add(path)

    def remove(self, path: str) -> None:
        self.calls["remove"] += 1
        if path in self.dirs:
            raise FsError(ISDIR)
        if self.files.pop(path, None) is None:
            raise FsError(NOENT)

    def rmdir(self, path: str) -> None:
        self.calls["rmdir"] += 1
        if path not in self.dirs:
            raise FsError(NOENT)
        if self.list(path):
            raise FsError(NOTEMPTY)
        self.dirs.discard(path)

    def rename(self, src: str, dst: str) -> None:
        self.calls["rename"] += 1
        if src in self.files:
            self.files[dst] = self.files.pop(src)
        elif src in self.dirs:
            raise FsError(NOTSUP)
        else:
            raise FsError(NOENT)


# ---------------------------------------------------------------- the runner side (model)


def join(base: str, rel: str) -> str:
    """A guest path relative to a provider directory, normalized; EPERM if it climbs out, which is
    what wasmtime answers for a real grant (dot_path.txt)."""
    parts = [] if base == "" else base.split("/")
    for seg in rel.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if not parts:
                raise FsError(PERM)
            parts.pop()
        else:
            parts.append(seg)
    return "/".join(parts)


class Open:
    def __init__(self, path: str, kind: str, data: bytes = b"", writable: bool = False) -> None:
        self.path, self.kind, self.buf, self.pos = path, kind, bytearray(data), 0
        self.writable, self.dirty, self.append, self.listing = writable, False, False, None


class Shim:
    """The runner's provider layer: an fd table over wasmtime's, staged buffers, errno."""

    def __init__(self, provider: MemoryProvider, mount_fd: int) -> None:
        self.p = provider
        self.fds: dict[int, Open] = {mount_fd: Open("", "dir")}
        self.counts: collections.Counter[str] = collections.Counter()
        self.refused: list[tuple[str, int]] = []  # the call record of failed write-backs
        self.reserve = self.release = self.fwd = None  # set once the trampolines exist

    # memory helpers
    @staticmethod
    def mem(c):
        return c.get("memory")

    def s(self, c, ptr, n) -> str:
        return bytes(self.mem(c).read(c, ptr & M32, (ptr & M32) + (n & M32))).decode()

    def iovs(self, c, iovs, n):
        raw = bytes(self.mem(c).read(c, iovs & M32, (iovs & M32) + 8 * (n & M32)))
        return [struct.unpack_from("<II", raw, 8 * i) for i in range(n & M32)]

    def put(self, c, ptr, fmt, *v):
        self.mem(c).write(c, struct.pack(fmt, *v), ptr & M32)

    def filestat(self, c, out, kind, size):
        self.mem(c).write(c, struct.pack("<QQB7xQQQQQ", 0, 0, DIR_T if kind == "dir" else FILE_T, 1, size, 0, 0, 0), out & M32)

    # dispatch
    def handler(self, name):
        fwd_name = name

        def fn(c, *a):
            self.counts[name] += 1
            fd = a[2] if name in NOT_FD_FIRST else a[0]
            if fd in self.fds or (name in ("path_rename", "path_link") and (a[3 if name == "path_rename" else 4] in self.fds)):
                try:
                    return getattr(self, name)(c, *a)
                except FsError as e:
                    return e.errno
            return self.fwd[fwd_name](c, *a)

        return fn

    # the calls
    def path_open(self, c, dirfd, dirflags, p, n, oflags, rb, ri, fdflags, out):
        d = self.fds[dirfd]
        path = join(d.path, self.s(c, p, n))
        kind = None
        try:
            kind, _ = self.p.stat(path)
        except FsError as e:
            if e.errno != NOENT or not oflags & O_CREAT:
                raise
        if kind and oflags & O_CREAT and oflags & O_EXCL:
            raise FsError(EXIST)
        if oflags & O_DIRECTORY and kind != "dir":
            raise FsError(NOTDIR)
        writes = bool(rb & (1 << 6))  # fd_write right
        if kind == "dir":
            if writes and not oflags & O_DIRECTORY:
                raise FsError(ISDIR)
            o = Open(path, "dir")
        else:
            data = b"" if kind is None or oflags & O_TRUNC else self.p.read(path)
            o = Open(path, "file", data, writes)
            o.dirty = kind is None or bool(oflags & O_TRUNC)
            o.append = bool(fdflags & APPEND)
        fd = self.reserve(c, dirfd)  # a number from wasmtime's own table, on the placeholder
        if fd < 0:
            raise FsError(-fd)
        self.fds[fd] = o
        self.put(c, out, "<I", fd)
        return OK

    def fd_close(self, c, fd):
        o = self.fds.pop(fd)
        err = self.flush(o)
        self.release(c, fd)
        return err

    def flush(self, o) -> int:
        if o.kind == "file" and o.dirty:
            try:
                self.p.write(o.path, bytes(o.buf))
                o.dirty = False
            except FsError as e:
                self.refused.append((o.path, e.errno))
                return e.errno
        return OK

    def fd_read(self, c, fd, iovs, n, out):
        o = self.fds[fd]
        if o.kind == "dir":
            raise FsError(ISDIR)
        total, m = 0, self.mem(c)
        for buf, ln in self.iovs(c, iovs, n):
            chunk = bytes(o.buf[o.pos:o.pos + ln])
            m.write(c, chunk, buf)
            o.pos += len(chunk)
            total += len(chunk)
            if len(chunk) < ln:
                break
        self.put(c, out, "<I", total)
        return OK

    def fd_pread(self, c, fd, iovs, n, off, out):
        o = self.fds[fd]
        save, o.pos = o.pos, off
        try:
            return self.fd_read(c, fd, iovs, n, out)
        finally:
            o.pos = save

    def fd_write(self, c, fd, iovs, n, out):
        o = self.fds[fd]
        if o.kind == "dir" or not o.writable:
            raise FsError(BADF)
        if o.append:
            o.pos = len(o.buf)
        total, m = 0, self.mem(c)
        for buf, ln in self.iovs(c, iovs, n):
            data = bytes(m.read(c, buf, buf + ln))
            end = o.pos + len(data)
            if o.pos > len(o.buf):
                o.buf.extend(b"\0" * (o.pos - len(o.buf)))
            o.buf[o.pos:end] = data
            o.pos = end
            total += len(data)
        o.dirty = True
        self.put(c, out, "<I", total)
        return OK

    def fd_pwrite(self, c, fd, iovs, n, off, out):
        o = self.fds[fd]
        save, o.pos, ap, o.append = o.pos, off, o.append, False
        try:
            return self.fd_write(c, fd, iovs, n, out)
        finally:
            o.pos, o.append = save, ap

    def fd_seek(self, c, fd, off, whence, out):
        o = self.fds[fd]
        if o.kind == "dir":
            raise FsError(ISDIR)
        base = {0: 0, 1: o.pos, 2: len(o.buf)}.get(whence)
        if base is None or base + off < 0:
            raise FsError(INVAL)
        o.pos = base + off
        self.put(c, out, "<Q", o.pos)
        return OK

    def fd_tell(self, c, fd, out):
        self.put(c, out, "<Q", self.fds[fd].pos)
        return OK

    def fd_filestat_get(self, c, fd, out):
        o = self.fds[fd]
        self.filestat(c, out, o.kind, len(o.buf))
        return OK

    def fd_fdstat_get(self, c, fd, out):
        o = self.fds[fd]
        rights = (1 << 30) - 1
        self.put(c, out, "<BxHxxxxQQ", DIR_T if o.kind == "dir" else FILE_T, APPEND if o.append else 0, rights, rights)
        return OK

    def fd_fdstat_set_flags(self, c, fd, flags):
        self.fds[fd].append = bool(flags & APPEND)
        return OK

    def fd_filestat_set_size(self, c, fd, size):
        o = self.fds[fd]
        del o.buf[size:]
        o.buf.extend(b"\0" * (size - len(o.buf)))
        o.dirty = True
        return OK

    def fd_readdir(self, c, fd, buf, ln, cookie, out):
        o = self.fds[fd]
        if o.kind != "dir":
            raise FsError(NOTDIR)
        if o.listing is None:
            o.listing = [(".", "dir"), ("..", "dir"), *self.p.list(o.path)]
        blob = bytearray()
        for i, (name, kind) in enumerate(o.listing[cookie:], start=cookie + 1):
            nb = name.encode()
            blob += struct.pack("<QQIB3x", i, i, len(nb), DIR_T if kind == "dir" else FILE_T) + nb
            if len(blob) >= ln:
                break
        blob = blob[:ln]
        self.mem(c).write(c, bytes(blob), buf & M32)
        self.put(c, out, "<I", len(blob))
        return OK

    def path_filestat_get(self, c, fd, flags, p, n, out):
        kind, size = self.p.stat(join(self.fds[fd].path, self.s(c, p, n)))
        self.filestat(c, out, kind, size)
        return OK

    def path_create_directory(self, c, fd, p, n):
        self.p.mkdir(join(self.fds[fd].path, self.s(c, p, n)))
        return OK

    def path_unlink_file(self, c, fd, p, n):
        self.p.remove(join(self.fds[fd].path, self.s(c, p, n)))
        return OK

    def path_remove_directory(self, c, fd, p, n):
        self.p.rmdir(join(self.fds[fd].path, self.s(c, p, n)))
        return OK

    def path_rename(self, c, fd, p, n, fd2, p2, n2):
        if fd not in self.fds or fd2 not in self.fds:
            return 75  # XDEV: across a provider and a real folder
        self.p.rename(join(self.fds[fd].path, self.s(c, p, n)), join(self.fds[fd2].path, self.s(c, p2, n2)))
        return OK

    def fd_sync(self, c, fd):
        return self.flush(self.fds[fd])

    fd_datasync = fd_sync

    def fd_advise(self, c, *a):
        return OK

    def fd_filestat_set_times(self, c, *a):
        return OK

    def path_filestat_set_times(self, c, *a):
        return OK

    def path_readlink(self, c, *a):
        return INVAL  # no links in a provider: "not a link"

    def path_symlink(self, c, *a):
        return NOTSUP

    def path_link(self, c, *a):
        return NOTSUP


# ---------------------------------------------------------------- trampolines


def wat_type(t) -> str:
    return str(t)


def trampoline_wat(sigs: dict) -> str:
    """Forwarders to wasmtime's own WASI, run on the guest's memory (re-exported as `memory`, which
    is where wasmtime's WASI looks: wiggle's caller.get_export("memory"))."""
    imports, funcs = [], []
    for name, ft in sigs.items():
        ps = " ".join(wat_type(p) for p in ft.params)
        rs = " ".join(wat_type(r) for r in ft.results)
        imports.append(f'(import "{P1}" "{name}" (func ${name} (param {ps}) (result {rs})))')
        gets = " ".join(f"local.get {i}" for i in range(len(ft.params)))
        funcs.append(f'(func (export "{name}") (param {ps}) (result {rs}) {gets} call ${name})')
    return "(module\n" + "\n".join(imports) + '\n(import "env" "memory" (memory 0))\n(export "memory" (memory 0))\n' + "\n".join(funcs) + ")"


RESERVE_WAT = f"""(module
 (import "{P1}" "path_open" (func $open (param i32 i32 i32 i32 i32 i64 i64 i32 i32) (result i32)))
 (import "{P1}" "fd_close" (func $close (param i32) (result i32)))
 (memory (export "memory") 1)
 (data (i32.const 0) ".")
 ;; a fresh number from wasmtime's table: "." of the (empty, read-only) placeholder, as a directory
 (func (export "reserve") (param $dir i32) (result i32) (local $e i32)
  (local.set $e (call $open (local.get $dir) (i32.const 0) (i32.const 0) (i32.const 1) (i32.const 2)
                 (i64.const 0x4000) (i64.const 0) (i32.const 0) (i32.const 16)))
  (if (result i32) (local.get $e) (then (i32.sub (i32.const 0) (local.get $e))) (else (i32.load (i32.const 16)))))
 (func (export "release") (param $fd i32) (result i32) (call $close (local.get $fd))))"""


# ---------------------------------------------------------------- the run


def main() -> None:
    cfg = wt.Config()
    cfg.consume_fuel = True
    engine = wt.Engine(cfg)
    binary = os.environ.get("BINARY", "python-snapshot.wasm")  # or python.wasm, the plain reactor
    cw = SCRATCH / (binary + ".cwasm")
    if cw.exists():
        module = wt.Module.deserialize_file(engine, str(cw))
    else:
        module = wt.Module.from_file(engine, str(ART / binary))
        cw.write_bytes(module.serialize())
    sigs = {i.name: i.type for i in module.imports if i.module == P1 and i.name in FILE_CALLS}
    assert len(sigs) == len(FILE_CALLS), sorted(set(FILE_CALLS) - set(sigs))

    zipdir, data, place, out = SCRATCH / "zip", SCRATCH / "data", SCRATCH / "placeholder", SCRATCH / "out"
    for d in (zipdir, data, place, out):
        d.mkdir(exist_ok=True)
    if not (zipdir / "python315.zip").exists():
        (zipdir / "python315.zip").write_bytes((ART / "python-stdlib.zip").read_bytes())
    (data / "in.csv").write_text("a,b\n1,2\n3,4\n")

    store = wt.Store(engine)
    store.set_fuel(10**13)
    w = wt.WasiConfig()
    w.argv = ["/usr/local/bin/python.wasm", "-c", PROGRAM]
    w.env = [("PYTHONTZPATH", ""), ("TMPDIR", "/tmp")]
    w.preopen_dir(str(zipdir), "/usr/local/lib", False)  # fd 3
    w.preopen_dir(str(data), "/data", False)  # fd 4: a real read-only grant
    if MODE == "provider":
        w.preopen_dir(str(place), "/work", False)  # fd 5: the provider's mount, an empty placeholder
    w.stdout_file, w.stderr_file = str(out / "stdout"), str(out / "stderr")
    store.set_wasi(w)

    plain = wt.Linker(engine)
    plain.define_wasi()
    i32 = wt.ValType.i32()
    plain.define_func("host", "call", wt.FuncType([i32] * 4, [i32]), lambda c, *a: -1)
    linker = plain
    shim = None
    if MODE in ("passthru", "provider"):
        linker = wt.Linker(engine)
        linker.define_wasi()
        linker.allow_shadowing = True
        linker.define_func("host", "call", wt.FuncType([i32] * 4, [i32]), lambda c, *a: -1)
        provider = MemoryProvider()
        shim = Shim(provider, 5 if MODE == "provider" else -1)
        for name, ft in sigs.items():
            linker.define_func(P1, name, ft, shim.handler(name), True)

    t0 = time.perf_counter()
    inst = linker.instantiate(store, module)
    ex = inst.exports(store)
    if shim is not None:
        tramp = wt.Module(engine, trampoline_wat(sigs))
        imports = [plain.get(store, P1, n) for n in sigs] + [ex["memory"]]
        fwd = wt.Instance(store, tramp, imports).exports(store)
        shim.fwd = {n: fwd[n] for n in sigs}
        res = wt.Instance(store, wt.Module(engine, RESERVE_WAT), [plain.get(store, P1, "path_open"), plain.get(store, P1, "fd_close")]).exports(store)
        shim.reserve = lambda c, d: res["reserve"](c, d)
        shim.release = lambda c, fd: res["release"](c, fd)
    fuel0 = store.get_fuel()
    try:
        if "_initialize" in ex:
            ex["_initialize"](store)
        code = ex["run"](store)
    except wt.ExitTrap as e:
        code = e.code
    except wt.Trap as e:
        code = f"trap: {str(e).splitlines()[0]}"
    secs = time.perf_counter() - t0
    fuel = fuel0 - store.get_fuel()
    store.close()
    print(f"binary={binary} mode={MODE} exit={code} fuel={fuel:,} seconds={secs:.3f}")
    print("stdout:", (out / "stdout").read_text().rstrip())
    err = (out / "stderr").read_text().rstrip()
    if err:
        print("stderr:", err[-1500:])
    if shim is not None:
        print("shadowed calls:", sum(shim.counts.values()), dict(sorted(shim.counts.items())))
        print("provider calls:", dict(shim.p.calls))
        print("refused write-backs:", shim.refused)
        if MODE == "provider":
            print("provider files after:", {k: v[:40] for k, v in sorted(shim.p.files.items())})
    print("placeholder still empty:", os.listdir(place) == [])


main()
