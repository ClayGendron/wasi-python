"""The judge's own guest driver (spec 002, Decision 9).

It does only what any embedder must do: preopen the stdlib, read-only, in a folder of its own at
`/usr/local/lib` (spec 017: the runtime's files are never in a writable root), one directory at
`/` (and, when a check asks, more directories, read-only or writable, in a chosen order), bind
`host::call`, and call one export. A check that plots asks for matplotlib's data too: the zip's
inner archive `matplotlib/mpl-data.zip`, extracted once per zip and granted read-only at the path
matplotlib computes, as the README's embedder contract says (spec 023, Decision 5). It is kept
apart from `wasi_python.run`, the runner it judges. It also answers `random_get` and
`clock_time_get` itself (context/research/2026-10-16-a-host-supplied-clock-and-random-make-fuel-
exact.md), and a file's times and inode number (spec 083: its times are the clock's values, its
inode a count), and gives each run its own copy of the stdlib, so no link count is shared. So
every run is seeded alike, and fuel (instructions executed) repeats exactly on one machine whose
file system stamps every change apart, at one checkout path.
"""

from __future__ import annotations

import hashlib
import io
import itertools
import os
import shutil
import struct
import sys
import tempfile
import threading
import zipfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import wasmtime as wt

from harness import litter, paths

DEFAULT_FUEL = 2 * 10**11
WASM_STACK = 8 << 20  # the runner's stated wasm stack (spec 078, Decision 1; spec 071, Decision 3)
THREAD_STACK = WASM_STACK + (2 << 20)  # the runner's guest thread (spec 078, Decision 2)
EPOCH_FAR_OFF = 2**40  # epochs are on, as in the runner, but no check is ever interrupted
UNMETERED = 2**63 - 1  # instantiation's own memory fill is not the guest's work (spec 008)
NO_HOST = -1
HOST_FAULT = -2
ARGV0 = "/usr/local/bin/python.wasm"
REALTIME_START_NS = 1_767_225_600_000_000_000  # 2026-01-01T00:00:00Z, a fixed start
CLOCK_STEP_NS = 1_000
# Each clock's resolution, stated by the judge, not read from the host (spec 065): realtime and
# monotonic at the step, the CPU-time clocks at a nanosecond. The values are the ones a darwin host
# answered before this was stated, so no darwin result moves; a Linux host answered 1 ns for the
# first two, which turned CPython's timing tests from skips into failures there.
CLOCK_RESOLUTION_NS = {0: CLOCK_STEP_NS, 1: CLOCK_STEP_NS, 2: 1, 3: 1}

_engine: wt.Engine | None = None
_modules: dict[tuple[str, int, int], wt.Module] = {}
_run_ids = itertools.count()
_mpl_data: dict[tuple[str, int, int], Path] = {}
MPL_DATA_MEMBER = "matplotlib/mpl-data.zip"


def engine() -> wt.Engine:
    """The runner's engine (spec 071, Decision 3): fuel, epoch interruption and the runner's
    8 MiB wasm stack (spec 078), so a check sees the native frames and the stack `run` gives.
    Epoch checks make Cranelift's frames larger; a driver without them measured more room than
    users get. Above 2 MiB wasmtime needs the async stack size raised first."""
    global _engine
    if _engine is None:
        from wasmtime import _ffi

        cfg = wt.Config()
        cfg.consume_fuel = True
        cfg.epoch_interruption = True
        _ffi.wasmtime_config_async_stack_size_set(cfg.ptr(), WASM_STACK)
        cfg.max_wasm_stack = WASM_STACK
        _engine = wt.Engine(cfg)
    return _engine


_stack_lock = threading.Lock()


def on_own_stack(fn: Callable[[], Any]) -> Any:
    """fn() on a thread with room for the 8 MiB wasm stack, as the runner gives (spec 078): its
    value, or its exception. The driver's host functions run there too; they are the judge's own."""
    import contextvars

    box: dict[str, Any] = {}

    def body() -> None:
        try:
            box["value"] = fn()
        except BaseException as e:
            box["error"] = e

    context = contextvars.copy_context()
    thread = threading.Thread(target=context.run, args=(body,), name="wasi-python-judge-guest")
    with _stack_lock:
        old = threading.stack_size(THREAD_STACK)
        try:
            thread.start()
        finally:
            threading.stack_size(old)
    thread.join()
    if "error" in box:
        raise box["error"]
    return box.get("value")


def module(path: Path) -> wt.Module:
    """Compile once per session (a large binary costs seconds and a gigabyte to compile)."""
    st = path.stat()
    key = (str(path.resolve()), st.st_size, st.st_mtime_ns)
    if key not in _modules:
        _modules[key] = wt.Module.from_file(engine(), str(path))
    return _modules[key]


@dataclass(frozen=True)
class Result:
    exit_code: int | None
    stdout: bytes
    stderr: bytes
    trapped: str | None  # None, "out of fuel", or the trap's first line
    fuel: int
    root: Path
    trap_cause: str | None = None  # the line after "Caused by:" (spec 050, Decision 14)

    @property
    def text(self) -> str:
        return self.stdout.decode(errors="replace")

    def describe(self) -> str:
        """One line for a failure message: how the guest ended, and the end of its stderr."""
        tail = self.stderr.decode(errors="replace").strip().splitlines()[-1:] or [""]
        how = f"trapped ({self.trapped})" if self.trapped else f"exit {self.exit_code}"
        return f"{how}; stderr: {tail[0][:200]}"


def trap_cause(message: str) -> str | None:
    """The line after a trap message's "Caused by:" line (`wasm trap: indirect call type
    mismatch`), or None. The first line ("error while executing at wasm backtrace:") is the same
    for every such trap and cannot tell one cause from another."""
    lines = [line.strip() for line in message.splitlines()]
    for i, line in enumerate(lines):
        if line == "Caused by:":
            return next((rest for rest in lines[i + 1 :] if rest), None)
    return None


def kind(mod: wt.Module) -> str:
    """Dispatch by exports: command, plain reactor, or snapshot."""
    names = {e.name for e in mod.exports}
    if "_start" in names:
        return "command"
    if "run" in names and "_initialize" in names:
        return "reactor"
    if "run" in names:
        return "snapshot"
    raise ValueError(f"no _start and no run export (exports: {sorted(names)})")


def stdlib_name(python_version: str, stdlib: Path) -> str:
    major, minor = python_version.split(".")[:2]
    return f"python{major}{minor}.zip" if stdlib.is_file() else f"python{major}.{minor}"


def _place(src: Path, dest: Path) -> None:
    """The stdlib in a run's own folder, with an inode of its own (spec 083, Decision 10): a hard
    link would share the set's file, whose link count every other run moves, and the guest sees it.
    On darwin an APFS clone (what `cp -c` makes), else, or if that fails, a copy."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        # A host folder a desktop may write into: its litter is no input, and the seal would
        # delete it anyway (spec 089, N1).
        shutil.copytree(
            src, dest, ignore=lambda _d, names: [n for n in names if litter.is_litter(n)]
        )
        return
    if sys.platform == "darwin" and _clone(src, dest):
        return
    shutil.copyfile(src, dest)


def _clone(src: Path, dest: Path) -> bool:
    import ctypes

    try:
        libc = ctypes.CDLL(None, use_errno=True)
        return libc.clonefile(os.fsencode(src), os.fsencode(dest), 0) == 0
    except (OSError, AttributeError):
        return False


def _release(store: wt.Store, lib: Path | None) -> None:
    """After a guest: its store closed first (on Windows, wasmtime's handles in `lib` go with it),
    then its own stdlib folder, which spec 089 sealed, unsealed and removed; `litter.remove`
    never raises, so it can never fail a run, and names on stderr anything it could not remove."""
    store.close()
    if lib is not None:
        litter.remove(lib)


def mpl_data_dir(stdlib: Path, workdir: Path) -> Path:
    """matplotlib's data, extracted once per zip from its inner archive into the work folder."""
    st = stdlib.stat()
    key = (str(stdlib.resolve()), st.st_size, st.st_mtime_ns)
    if key not in _mpl_data:
        dest = workdir / f"mpl-data-{len(_mpl_data)}"
        with zipfile.ZipFile(stdlib) as outer:
            inner = io.BytesIO(outer.read(MPL_DATA_MEMBER))
        with zipfile.ZipFile(inner) as z:
            for member in z.namelist():
                litter.refuse(member, MPL_DATA_MEMBER)  # the seal must never meet it (spec 089)
            z.extractall(dest)
        litter.seal(dest)  # read-only for every run that shares it (spec 089)
        _mpl_data[key] = dest
    return _mpl_data[key]


def _random_stream() -> Callable[[int], bytes]:
    counter = itertools.count()

    def take(n: int) -> bytes:
        out = bytearray()
        while len(out) < n:
            out += hashlib.sha256(struct.pack("<Q", next(counter))).digest()
        return bytes(out[:n])

    return take


# What the guest learns about a file (spec 083). wasmtime's filestat and readdir calls hand the
# guest the host's real times, and an inode number that is a hash of the host's own, new for a
# fresh file; each moves the instructions a program runs. The driver forwards the five calls that
# carry them to wasmtime and answers those fields itself, as it answers the clock and random.
P1 = "wasi_snapshot_preview1"
FILE_CALLS: dict[str, tuple[str, ...]] = {
    "fd_filestat_get": ("i32", "i32"),
    "path_filestat_get": ("i32", "i32", "i32", "i32", "i32"),
    "fd_filestat_set_times": ("i32", "i64", "i64", "i32"),
    "path_filestat_set_times": ("i32", "i32", "i32", "i32", "i64", "i64", "i32"),
    "fd_readdir": ("i32", "i32", "i32", "i64", "i32"),
}
OWN_PAGE = ("fd_filestat_get", "path_filestat_get")  # the stats the driver makes for itself
FILESTAT = struct.Struct("<QQB7xQQQQQ")  # dev, ino, filetype, nlink, size, atim, mtim, ctim
INO_AT, TIMES_AT = 8, 40  # the only fields the driver writes in a stat
DIRENT = struct.Struct("<QQIB3x")  # d_next, d_ino, d_namlen, d_type, three bytes of padding
OWN_PATH = FILESTAT.size  # where a stat's path goes on the driver's own page
ATIM, ATIM_NOW, MTIM, MTIM_NOW = 1, 2, 4, 8  # fstflags
FORWARD_FUEL = 1 << 20  # lent to each forward and taken back: the trampoline's, not the guest's
MASK32 = 0xFFFFFFFF
_forwarders: dict[bool, wt.Module] = {}


def forwarders_wat(names: tuple[str, ...], own_page: bool) -> str:
    """A module that imports each of wasmtime's calls in `names` and exports a function that
    calls it. wasmtime's WASI reads and writes the memory the calling instance exports: the
    guest's, imported and exported again; or, with `own_page`, a page of the module's own, so a
    stat the driver makes for itself never touches a byte of the guest's."""
    lines = ["(module"]
    for name in names:
        lines.append(f'  (import "{P1}" "{name}" (func ${name} {_signature(name)}))')
    if own_page:
        lines.append('  (memory (export "memory") 1)')
    else:
        lines += ['  (import "env" "memory" (memory 0))', '  (export "memory" (memory 0))']
    for name in names:
        gets = " ".join(f"(local.get {i})" for i in range(len(FILE_CALLS[name])))
        lines.append(f'  (func (export "{name}") {_signature(name)} (call ${name} {gets}))')
    return "\n".join([*lines, ")"])


def _signature(name: str) -> str:
    return f"(param {' '.join(FILE_CALLS[name])}) (result i32)"


def _forwarders_module(eng: wt.Engine, own_page: bool) -> wt.Module:
    """Compiled once for the driver's own engine; a run on its own engine (`own=`) compiles its
    own each time, since a module of one engine must never reach another (no key by `id`)."""
    names = OWN_PAGE if own_page else tuple(FILE_CALLS)
    if eng is not engine():
        return wt.Module(eng, forwarders_wat(names, own_page))
    if own_page not in _forwarders:
        _forwarders[own_page] = wt.Module(eng, forwarders_wat(names, own_page))
    return _forwarders[own_page]


class FileFacts:
    """One run's answers about files, by wasmtime's inode number (its hash of the host's):
    - the inode number: 1 for the first file the guest sees, 2 for the next, and so on;
    - the times: a file first seen, or whose mtim or ctim moved on the host, takes the clock's
      next value for each new time (one value for all of them); atim follows `noatime`: it moves
      only with mtim or ctim, or when the guest sets it, never because the host read the file;
      a time the guest set is answered as set, while the host keeps it.
    A 0 (wasmtime's answer for its stdio streams) is answered 0, with no clock step."""

    def __init__(self, now: Callable[[], int]) -> None:
        self.now = now
        self.inos: dict[int, int] = {}
        self.times: dict[int, list[tuple[int, int]]] = {}

    def ino(self, real: int) -> int:
        return 0 if real == 0 else self.inos.setdefault(real, len(self.inos) + 1)

    def stamp(self, real_ino: int, real: tuple[int, int, int]) -> tuple[int, int, int]:
        if real_ino == 0 and not any(real):
            return (0, 0, 0)
        old = self.times.get(real_ino)
        fresh = [old is None or old[i][0] != real[i] for i in range(3)]
        fresh[0] = old is None or fresh[1] or fresh[2]
        now = self.now() if any(fresh) else 0
        kept = [
            (real[i], 0 if real[i] == 0 else now)
            if fresh[i] or old is None
            else (real[i], old[i][1])
            for i in range(3)
        ]
        self.times[real_ino] = kept
        return (kept[0][1], kept[1][1], kept[2][1])

    def filestat(self, raw: bytes) -> bytes:
        """`raw` with its inode number and times answered; every other byte as wasmtime wrote it."""
        out = bytearray(raw)
        ino, times = self.fields(raw)
        struct.pack_into("<Q", out, INO_AT, ino)
        struct.pack_into("<QQQ", out, TIMES_AT, *times)
        return bytes(out)

    def fields(self, raw: bytes) -> tuple[int, tuple[int, int, int]]:
        _dev, ino, _kind, _nlink, _size, atim, mtim, ctim = FILESTAT.unpack(raw)
        return self.ino(ino), self.stamp(ino, (atim, mtim, ctim))

    def set_times(self, raw: bytes, chosen: dict[int, int]) -> None:
        """After a set-times call the host accepted, with the file's stat as the host now gives it:
        field i (0 atim, 1 mtim) is answered `chosen[i]` while the host keeps that time."""
        _dev, ino, _kind, _nlink, _size, atim, mtim, ctim = FILESTAT.unpack(raw)
        self.stamp(ino, (atim, mtim, ctim))
        for i, value in chosen.items():
            self.times[ino][i] = ((atim, mtim)[i], value)

    def listing(self, data: bytearray) -> None:
        """A readdir answer, in place: each whole entry's d_ino answered and its padding zeroed
        (wasmtime 49.0.0 leaves host bytes there; spec 048); of an entry cut at the end, only the
        d_ino and padding bytes present are zeroed (wasi-libc never reads a cut entry)."""
        at = 0
        while at < len(data):
            if len(data) - at < DIRENT.size:
                for lo, hi in ((8, 16), (21, 24)):
                    end = min(at + hi, len(data))
                    data[at + lo : end] = bytes(max(0, end - at - lo))
                return
            d_next, ino, namlen, kind = DIRENT.unpack_from(data, at)
            DIRENT.pack_into(data, at, d_next, self.ino(ino), namlen, kind)
            at += DIRENT.size + namlen


class _FileCalls:
    """The five shadowed calls: each forwarded to wasmtime's own on the guest's memory through a
    trampoline, fuel-neutral, and a successful answer's fields rewritten by `facts`."""

    def __init__(self, counted: bool, facts: FileFacts) -> None:
        self.counted = counted
        self.facts = facts
        self.funcs: dict[str, Any] = {}
        self.own: dict[str, Any] = {}
        self.page: Any = None

    def define(self, linker: wt.Linker) -> None:
        for name, params in FILE_CALLS.items():
            kinds = [wt.ValType.i32() if p == "i32" else wt.ValType.i64() for p in params]
            ty = wt.FuncType(kinds, [wt.ValType.i32()])
            linker.define_func(P1, name, ty, getattr(self, name), True)

    def bind(self, store: wt.Store, eng: wt.Engine, guest: wt.Instance) -> None:
        """Instantiate both trampolines with wasmtime's own calls: after the guest, before it
        runs. Its own linker holds only wasmtime's WASI, on the same store and so the same
        descriptor table."""
        plain = wt.Linker(eng)
        plain.define_wasi()
        imports: list[Any] = [plain.get(store, P1, name) for name in FILE_CALLS]
        imports.append(guest.exports(store)["memory"])
        ex = wt.Instance(store, _forwarders_module(eng, False), imports).exports(store)
        self.funcs = {name: ex[name] for name in FILE_CALLS}
        own = [plain.get(store, P1, name) for name in OWN_PAGE]
        mine = wt.Instance(store, _forwarders_module(eng, True), own).exports(store)
        self.own = {name: mine[name] for name in OWN_PAGE}
        self.page = mine["memory"]

    def call(self, caller: wt.Caller, func: Any, *args: int) -> int:
        """wasmtime's answer, with the guest's fuel as it was before: the trampoline runs on fuel
        lent to it, so its few instructions never count and never run a guest out early."""
        if func is None:
            raise RuntimeError("a file call before the driver's trampolines were bound")
        before = wt.Store.get_fuel(caller) if self.counted else None  # type: ignore[arg-type]
        try:
            if before is not None:
                lent = min(before + FORWARD_FUEL, UNMETERED)
                wt.Store.set_fuel(caller, lent)  # type: ignore[arg-type]
            return func(caller, *args)
        finally:
            if before is not None:
                wt.Store.set_fuel(caller, before)  # type: ignore[arg-type]

    def _answer(self, caller: wt.Caller, at: int) -> None:
        memory: Any = caller.get("memory")
        raw = bytes(memory.read(caller, at, at + FILESTAT.size))
        ino, times = self.facts.fields(raw)
        memory.write(caller, struct.pack("<Q", ino), at + INO_AT)
        memory.write(caller, struct.pack("<QQQ", *times), at + TIMES_AT)

    def fd_filestat_get(self, caller: wt.Caller, fd: int, out: int) -> int:
        errno = self.call(caller, self.funcs.get("fd_filestat_get"), fd, out)
        if errno == 0:
            self._answer(caller, out & MASK32)
        return errno

    def path_filestat_get(
        self, caller: wt.Caller, fd: int, flags: int, path: int, n: int, out: int
    ) -> int:
        args = (fd, flags, path, n, out)
        errno = self.call(caller, self.funcs.get("path_filestat_get"), *args)
        if errno == 0:
            self._answer(caller, out & MASK32)
        return errno

    def fd_readdir(
        self, caller: wt.Caller, fd: int, buf: int, length: int, cookie: int, used: int
    ) -> int:
        args = (fd, buf, length, cookie, used)
        errno = self.call(caller, self.funcs.get("fd_readdir"), *args)
        if errno:
            return errno
        memory: Any = caller.get("memory")
        buf, used = buf & MASK32, used & MASK32
        count = struct.unpack("<I", bytes(memory.read(caller, used, used + 4)))[0]
        if count and (used + 4 <= buf or used >= buf + count):  # else the count lies over it
            data = bytearray(memory.read(caller, buf, buf + count))
            self.facts.listing(data)
            memory.write(caller, bytes(data), buf)
        return 0

    def _chosen(self, atim: int, mtim: int, flags: int) -> dict[int, int]:
        """What a set-times call sets, by field: an exact time as given, "now" the clock's next."""
        chosen: dict[int, int] = {}
        now: int | None = None
        for i, (value, exact, at_now) in enumerate(
            ((atim, ATIM, ATIM_NOW), (mtim, MTIM, MTIM_NOW))
        ):
            if flags & exact:
                chosen[i] = value & 0xFFFFFFFFFFFFFFFF
            elif flags & at_now:
                now = self.facts.now() if now is None else now
                chosen[i] = now
        return chosen

    def _record(self, caller: wt.Caller, errno: int, chosen: dict[int, int]) -> None:
        if errno == 0:
            self.facts.set_times(bytes(self.page.read(caller, 0, FILESTAT.size)), chosen)

    def fd_filestat_set_times(
        self, caller: wt.Caller, fd: int, atim: int, mtim: int, flags: int
    ) -> int:
        args = (fd, atim, mtim, flags)
        errno = self.call(caller, self.funcs.get("fd_filestat_set_times"), *args)
        if errno == 0 and (chosen := self._chosen(atim, mtim, flags)):
            got = self.call(caller, self.own.get("fd_filestat_get"), fd, 0)
            self._record(caller, got, chosen)
        return errno

    def path_filestat_set_times(
        self, caller: wt.Caller, fd: int, flags: int, path: int, n: int, a: int, m: int, fst: int
    ) -> int:
        args = (fd, flags, path, n, a, m, fst)
        errno = self.call(caller, self.funcs.get("path_filestat_set_times"), *args)
        if errno == 0 and (chosen := self._chosen(a, m, fst)):
            memory: Any = caller.get("memory")
            path, n = path & MASK32, n & MASK32
            name = bytes(memory.read(caller, path, path + n))  # wasmtime has just read it
            short = OWN_PATH + n - self.page.data_len(caller)
            if short > 0:
                self.page.grow(caller, (short + 65535) // 65536)
            self.page.write(caller, name, OWN_PATH)
            stat = self.own.get("path_filestat_get")
            got = self.call(caller, stat, fd, flags, OWN_PATH, n, 0)
            self._record(caller, got, chosen)
        return errno


def _forms(root: Path) -> set[str]:
    """The ways a check can write `root` into a guest's input (spec 081, Decision 2): as written and
    resolved, each also in forward slashes and, for an absolute path, as a `file:` URI; and any of
    these holding a backslash with every backslash doubled, as `repr()` and JSON write it."""
    forms: set[str] = set()
    for p in (Path(root), Path(root).resolve()):
        forms |= {str(p), p.as_posix()}
        if p.is_absolute():
            forms.add(p.as_uri())
    return forms | {f.replace("\\", "\\\\") for f in forms if "\\" in f}


def host_paths_in(
    roots: Sequence[Path],
    argv: Sequence[str],
    env: Mapping[str, str] | None = None,
    files: Mapping[str, bytes | str] | None = None,
    preopens: list[tuple[str, Path, bool]] | None = None,
    *,
    fold_case: bool = sys.platform == "win32",
) -> list[str]:
    """Each input the guest can see that names a host path under one of `roots`: an argument, an
    environment variable, a file's guest path or contents, or a grant's guest path (spec 081).
    The guest's work moves with the length of any host path it is given, so a run whose fuel is
    recorded must give it guest paths only. On Windows (`fold_case`) case is ignored."""
    needles = sorted({form for root in roots for form in _forms(root)})
    if fold_case:
        needles = [n.casefold() for n in needles]
    found: list[str] = []

    def look(where: str, value: str | bytes) -> None:
        text = value.decode("utf-8", "replace") if isinstance(value, bytes) else value
        if fold_case:
            text = text.casefold()
        if any(n in text for n in needles):
            found.append(where)

    for i, arg in enumerate(argv, 1):
        look(f"argv[{i}]", arg)
    for name, value in (env or {}).items():
        look(f"env {name}", f"{name}={value}")
    for guest_path, content in (files or {}).items():
        look(f"file {guest_path}", guest_path)
        look(f"the contents of {guest_path}", content)
    for guest_path, _, _ in preopens or []:
        look(f"grant {guest_path}", guest_path)
    return found


def host_roots_always() -> tuple[Path, ...]:
    """The roots every measured run is checked against: the checkout, and the system's temp folder
    unless it is literally `/tmp`, a path guests are given as their own (spec 081, Decision 2)."""
    temp = tempfile.gettempdir()
    return (paths.REPO,) if temp == "/tmp" else (paths.REPO, Path(temp))


def run(
    wasm: Path,
    argv: list[str],
    *,
    workdir: Path,
    python_version: str | None = None,
    stdlib: Path | None = None,
    files: Mapping[str, bytes | str] | None = None,
    env: Mapping[str, str] | None = None,
    host: Callable[[bytes], bytes] | None = None,
    fuel: int = DEFAULT_FUEL,
    preopens: list[tuple[str, Path, bool]] | None = None,
    preopens_first: bool = False,
    mpl_data: bool = False,
    own: tuple[wt.Engine, wt.Module] | None = None,
    measured: bool = True,
    host_roots: Sequence[Path] = (),
    clock_step_ns: int = CLOCK_STEP_NS,
    root_writable: bool = True,
) -> Result:
    """Run the guest once, in a fresh instance and a fresh root under `workdir`. With `mpl_data`,
    matplotlib's data is granted read-only beside the stdlib zip. `own` is an engine the caller
    made at wasmtime's defaults (no fuel, no epochs) and the module compiled on it, as another
    embedder's would be (spec 071, criterion 3); the driver's cached engine is never swapped, and
    such a run counts no fuel. A `measured` run (the default: one whose fuel a check records) is
    refused before anything runs when its inputs name a host path under the checkout, the
    system's temp folder or `host_roots` (spec 081): its fuel would depend on where they are.
    Each clock read advances the guest's clocks by `clock_step_ns`, so a guest's elapsed time is a
    count of its reads (spec 087, Decision 3), and the file times the driver answers take the same
    step (spec 083's ticks). The default keeps every other check's fuel; at the
    default, `clock_res_get` answers from `CLOCK_RESOLUTION_NS`, read at call time (spec 065), and
    with another step the realtime and monotonic clocks state that step as their resolution.
    `root_writable=False` grants the root read-only."""
    if measured and own is None:
        named = host_paths_in((*host_roots_always(), *host_roots), argv, env, files, preopens)
        if named:
            raise ValueError(
                "a measured run gives the guest a host path in "
                + ", ".join(named)
                + ": its fuel would depend on where the checkout is; give it guest paths, or"
                " record no fuel for this run (spec 081)"
            )
    eng, mod = own if own is not None else (engine(), module(wasm))
    counted = own is None
    how = kind(mod)
    base = workdir / f"run-{next(_run_ids)}"
    root, io = base / "root", base / "io"
    root.mkdir(parents=True)
    io.mkdir()
    lib = None
    if stdlib is not None:
        if python_version is None:
            raise ValueError("a stdlib needs the python version that names it")
        # The root keeps real usr/local/lib folders, as the runner's does, so `/` lists `usr`;
        # the stdlib itself (a zip, or the reference build's directory) is its own grant.
        (root / "usr/local/lib").mkdir(parents=True)
        lib = base / "lib"
        _place(stdlib, lib / stdlib_name(python_version, stdlib))
        litter.seal(lib)  # read-only and fresh: sealed like a stage (spec 089, F4)
    for guest_path, content in (files or {}).items():
        dest = root / guest_path.lstrip("/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content.encode() if isinstance(content, str) else content)

    store = wt.Store(eng)
    if counted:
        store.set_fuel(UNMETERED)  # fuel is metered from the end of instantiation (spec 008)
        store.set_epoch_deadline(EPOCH_FAR_OFF)
    wasi = wt.WasiConfig()
    wasi.argv = [ARGV0, *argv]
    wasi.env = sorted((env or {}).items())
    # Extra preopens are (guest path, host directory, writable); they go after the root, or
    # before it with preopens_first, so a check can try both orders (spec 006, check 1.11).
    extra = [
        (str(host_dir), guest_path, writable) for guest_path, host_dir, writable in preopens or []
    ]
    # The root is writable unless a check runs as an embedder's default call does, with nothing
    # writable (spec 037's build review, F1: its checks moved here from `wasi_python.run`).
    top = (str(root), "/", root_writable)
    ordered = [*extra, top] if preopens_first else [top, *extra]
    if lib is not None:
        ordered.insert(0, (str(lib), "/usr/local/lib", False))
    if mpl_data:
        if stdlib is None or lib is None or not stdlib.is_file():
            raise ValueError("matplotlib's data comes from a stdlib zip")
        name = stdlib_name(python_version or "", stdlib)
        data = mpl_data_dir(stdlib, workdir)
        ordered.insert(1, (str(data), f"/usr/local/lib/{name}/matplotlib/mpl-data", False))
    watch = litter.Watch(ordered)  # host litter, before the run and after it (spec 089)
    for host_dir, guest_path, writable in ordered:
        wasi.preopen_dir(host_dir, guest_path, writable)
    wasi.stdout_file = str(io / "stdout")
    wasi.stderr_file = str(io / "stderr")
    store.set_wasi(wasi)

    linker = wt.Linker(eng)
    linker.define_wasi()
    linker.allow_shadowing = True
    i32, i64 = wt.ValType.i32(), wt.ValType.i64()
    take_random = _random_stream()
    ticks = itertools.count(1)
    files = _FileCalls(counted, FileFacts(lambda: REALTIME_START_NS + next(ticks) * clock_step_ns))

    def random_get(caller: wt.Caller, buf: int, n: int) -> int:
        caller.get("memory").write(caller, take_random(n), buf)
        return 0

    def clock_time_get(caller: wt.Caller, clock_id: int, _precision: int, out: int) -> int:
        start = REALTIME_START_NS if clock_id == 0 else 0
        value = start + next(ticks) * clock_step_ns
        caller.get("memory").write(caller, struct.pack("<Q", value), out)
        return 0

    def clock_res_get(caller: wt.Caller, clock_id: int, out: int) -> int:
        if clock_id not in CLOCK_RESOLUTION_NS:
            return 28  # EINVAL: an unknown clock, as WASI answers
        res = CLOCK_RESOLUTION_NS[clock_id]
        if clock_step_ns != CLOCK_STEP_NS and clock_id in (0, 1):
            res = clock_step_ns  # a changed step is the run's stated resolution (spec 087)
        caller.get("memory").write(caller, struct.pack("<Q", res), out & 0xFFFFFFFF)
        return 0

    def door(caller: wt.Caller, ptr: int, length: int, out_ptr_ptr: int, out_len_ptr: int) -> int:
        if host is None:
            return NO_HOST
        memory = caller.get("memory")
        alloc = caller.get("host_alloc")
        if memory is None or alloc is None:
            return HOST_FAULT
        ptr, length = ptr & 0xFFFFFFFF, length & 0xFFFFFFFF  # i32 values; addresses are unsigned
        out_ptr_ptr, out_len_ptr = out_ptr_ptr & 0xFFFFFFFF, out_len_ptr & 0xFFFFFFFF
        size = memory.data_len(caller)  # the runner's bounds (spec 006, Decision 3)
        if ptr + length > size or out_ptr_ptr + 4 > size or out_len_ptr + 4 > size:
            return HOST_FAULT
        request = bytes(memory.read(caller, ptr, ptr + length))
        try:
            response = bytes(host(request))
        except Exception:
            return HOST_FAULT
        if memoryview(response).nbytes > 0x7FFFFFFF:
            return HOST_FAULT
        p = alloc(caller, len(response)) & 0xFFFFFFFF
        if not p or p + len(response) > memory.data_len(caller):
            return HOST_FAULT
        memory.write(caller, response, p)
        memory.write(caller, struct.pack("<I", p), out_ptr_ptr)
        memory.write(caller, struct.pack("<I", len(response)), out_len_ptr)
        return 0

    p1 = "wasi_snapshot_preview1"
    linker.define_func(p1, "random_get", wt.FuncType([i32, i32], [i32]), random_get, True)
    linker.define_func(
        p1, "clock_time_get", wt.FuncType([i32, i64, i32], [i32]), clock_time_get, True
    )
    linker.define_func(p1, "clock_res_get", wt.FuncType([i32, i32], [i32]), clock_res_get, True)
    linker.define_func("host", "call", wt.FuncType([i32] * 4, [i32]), door, True)
    files.define(linker)

    exit_code: int | None = None
    trapped: str | None = None
    cause: str | None = None
    metered = False  # the budget is set only once instantiation has succeeded

    def go() -> int:  # on a thread with room for the wasm stack (spec 078)
        nonlocal metered
        inst = linker.instantiate(store, mod)
        files.bind(store, eng, inst)  # before the guest runs (spec 083)
        if counted:
            store.set_fuel(fuel)
            metered = True
        exports = inst.exports(store)
        if how == "command":
            exports["_start"](store)
            return 0
        if how == "reactor":
            exports["_initialize"](store)
        return exports["run"](store)

    try:
        exit_code = on_own_stack(go)
    except wt.ExitTrap as e:
        exit_code = e.code
    except wt.Trap as e:
        trapped = "out of fuel" if e.trap_code == wt.TrapCode.OUT_OF_FUEL else e.message
        cause = None if trapped == "out of fuel" else trap_cause(trapped or "")
        trapped = trapped.strip().splitlines()[0] if trapped else "trap"
    except wt.WasmtimeError as e:
        trapped = str(e).strip().splitlines()[0]
    except BaseException:
        _release(store, lib)
        raise
    spent = fuel - store.get_fuel() if metered else 0
    result = Result(
        exit_code=exit_code,
        stdout=(io / "stdout").read_bytes(),
        stderr=(io / "stderr").read_bytes(),
        trapped=trapped,
        fuel=spent,
        root=root,
        trap_cause=cause,
    )
    try:
        watch.after()  # a run whose grants changed raises HostLitter: its fuel is not recorded
    finally:
        _release(store, lib)  # after the watch: it must see the run's own stdlib copy (spec 089)
    return result


@dataclass(frozen=True)
class Turn:
    """One call into a `Turns` instance: the export's return value (None after a trap or an exit),
    what it wrote, and how it ended."""

    value: int | None
    stdout: bytes
    stderr: bytes
    trapped: str | None
    exit_code: int | None = None  # proc_exit's code, when the call exited

    @property
    def text(self) -> str:
        return self.stdout.decode(errors="replace")

    def describe(self) -> str:
        tail = self.stderr.decode(errors="replace").strip().splitlines()[-1:] or [""]
        how = f"trapped ({self.trapped})" if self.trapped else f"returned {self.value}"
        return f"{how}; stderr: {tail[0][:200]}"


class Turns:
    """One instance of the guest kept across calls, driven raw (spec 055, criteria 1 to 3 and
    34): `turn(code)` writes the code through `host_alloc` and calls the `turn` export;
    `turn_raw(ptr, length)`, `run()` and `shutdown()` call the exports as they are. Each call
    gets `fuel` and reports only what it wrote. The door's host function, if any, is called with
    this object and the request, so a check can call back into the instance from the door."""

    def __init__(
        self,
        wasm: Path,
        *,
        workdir: Path,
        python_version: str,
        stdlib: Path,
        host: Callable[[Turns, bytes], bytes] | None = None,
        preopens: list[tuple[str, Path, bool]] | None = None,
        argv: list[str] | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self.mod = module(wasm)
        self.how = kind(self.mod)
        base = workdir / f"turns-{next(_run_ids)}"
        root, self._io = base / "root", base / "io"
        (root / "usr/local/lib").mkdir(parents=True)
        self._io.mkdir()
        self.root = root
        self._lib = lib = base / "lib"
        _place(stdlib, lib / stdlib_name(python_version, stdlib))
        self.store = wt.Store(engine())
        self.store.set_fuel(UNMETERED)
        self.store.set_epoch_deadline(EPOCH_FAR_OFF)  # the runner's engine has epochs (spec 071)
        wasi = wt.WasiConfig()
        wasi.argv = [ARGV0, *(argv or [])]
        wasi.env = sorted((env or {}).items())
        wasi.preopen_dir(str(lib), "/usr/local/lib", False)
        wasi.preopen_dir(str(root), "/", True)
        for guest_path, host_dir, writable in preopens or []:
            wasi.preopen_dir(str(host_dir), guest_path, writable)
        wasi.stdout_file = str(self._io / "stdout")
        wasi.stderr_file = str(self._io / "stderr")
        self.store.set_wasi(wasi)
        linker = wt.Linker(engine())
        linker.define_wasi()
        linker.allow_shadowing = True
        i32 = wt.ValType.i32()

        def door(caller: wt.Caller, ptr: int, length: int, out_pp: int, out_lp: int) -> int:
            if host is None:
                return NO_HOST
            memory = caller.get("memory")
            ptr, length = ptr & 0xFFFFFFFF, length & 0xFFFFFFFF
            request = bytes(memory.read(caller, ptr, ptr + length))
            response = bytes(host(self, request))
            p = caller.get("host_alloc")(caller, len(response)) & 0xFFFFFFFF
            if not p:
                return HOST_FAULT
            memory.write(caller, response, p)
            memory.write(caller, struct.pack("<I", p), out_pp & 0xFFFFFFFF)
            memory.write(caller, struct.pack("<I", len(response)), out_lp & 0xFFFFFFFF)
            return 0

        linker.define_func("host", "call", wt.FuncType([i32] * 4, [i32]), door, True)
        self.instance = linker.instantiate(self.store, self.mod)
        self.exports = self.instance.exports(self.store)
        self._read = {"stdout": 0, "stderr": 0}
        self._initialized = False
        self.inner: list[int] = []  # values of calls made from inside the door

    def _new(self, name: str) -> bytes:
        data = (self._io / name).read_bytes()
        out, self._read[name] = data[self._read[name] :], len(data)
        return out

    def _call(self, fn: Callable[[], int], fuel: int) -> Turn:
        self.store.set_fuel(fuel)
        value: int | None = None
        trapped: str | None = None
        exit_code: int | None = None

        def go() -> int:  # on a thread with room for the wasm stack (spec 078)
            if self.how == "reactor" and not self._initialized:
                self._initialized = True
                self.exports["_initialize"](self.store)
            return fn()

        try:
            value = on_own_stack(go)
        except wt.ExitTrap as e:
            exit_code = e.code
        except wt.Trap as e:
            trapped = "out of fuel" if e.trap_code == wt.TrapCode.OUT_OF_FUEL else "trap"
        except wt.WasmtimeError as e:
            trapped = str(e).strip().splitlines()[0]
        return Turn(value, self._new("stdout"), self._new("stderr"), trapped, exit_code)

    def write(self, code: bytes) -> int:
        """`code` in a buffer from host_alloc: its address."""
        p = self.exports["host_alloc"](self.store, len(code)) & 0xFFFFFFFF
        self.exports["memory"].write(self.store, code, p)
        return p

    def turn(self, code: str | bytes, fuel: int = DEFAULT_FUEL) -> Turn:
        data = code.encode() if isinstance(code, str) else code

        def go() -> int:
            p = self.write(data) if data else 0
            return self.exports["turn"](self.store, p, len(data))

        return self._call(go, fuel)

    def turn_raw(self, ptr: int, length: int, fuel: int = DEFAULT_FUEL) -> Turn:
        return self._call(lambda: self.exports["turn"](self.store, ptr, length), fuel)

    def run(self, fuel: int = DEFAULT_FUEL) -> Turn:
        return self._call(lambda: self.exports["run"](self.store), fuel)

    def shutdown(self, fuel: int = DEFAULT_FUEL) -> Turn:
        return self._call(lambda: self.exports["shutdown"](self.store), fuel)

    def call_from_door(self, caller: str, *args: int) -> int:
        """Call an export from inside a door call (the store is the caller's); its value."""
        value = self.exports[caller](self.store, *args)
        self.inner.append(value)
        return value

    def close(self) -> None:
        _release(self.store, self._lib)


def turns(wasm: Path, **kw: Any) -> Turns:
    """A `Turns` instance of `wasm` (spec 055)."""
    return Turns(wasm, **kw)
