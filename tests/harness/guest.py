"""The judge's own guest driver (spec 002, Decision 9).

It does only what any embedder must do: preopen the stdlib, read-only, in a folder of its own at
`/usr/local/lib` (spec 017: the runtime's files are never in a writable root), one directory at
`/` (and, when a check asks, more directories, read-only or writable, in a chosen order), bind
`host::call`, and call one export. A check that plots asks for matplotlib's data too: the zip's
inner archive `matplotlib/mpl-data.zip`, extracted once per zip and granted read-only at the path
matplotlib computes, as the README's embedder contract says (spec 023, Decision 5). It is kept
apart from `wasi_python.run`, the runner it judges. It also answers `random_get` and
`clock_time_get` itself, so every run is seeded alike and fuel (instructions executed) repeats to
a few parts in ten million
(context/research/2026-10-16-a-host-supplied-clock-and-random-make-fuel-exact.md).
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
import zipfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import wasmtime as wt

from harness import paths

DEFAULT_FUEL = 2 * 10**11
WASM_STACK = 512 * 1024  # the runner's stated wasm stack (spec 071, Decision 3)
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
    512 KiB wasm stack, so a check sees the native frames and the stack `run` gives. Epoch checks
    make Cranelift's frames larger; a driver without them measured more room than users get."""
    global _engine
    if _engine is None:
        cfg = wt.Config()
        cfg.consume_fuel = True
        cfg.epoch_interruption = True
        cfg.max_wasm_stack = WASM_STACK
        _engine = wt.Engine(cfg)
    return _engine


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
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dest)
        return
    try:
        os.link(src, dest)
    except OSError:
        shutil.copyfile(src, dest)


def mpl_data_dir(stdlib: Path, workdir: Path) -> Path:
    """matplotlib's data, extracted once per zip from its inner archive into the work folder."""
    st = stdlib.stat()
    key = (str(stdlib.resolve()), st.st_size, st.st_mtime_ns)
    if key not in _mpl_data:
        dest = workdir / f"mpl-data-{len(_mpl_data)}"
        with zipfile.ZipFile(stdlib) as outer:
            inner = io.BytesIO(outer.read(MPL_DATA_MEMBER))
        with zipfile.ZipFile(inner) as z:
            z.extractall(dest)
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
) -> Result:
    """Run the guest once, in a fresh instance and a fresh root under `workdir`. With `mpl_data`,
    matplotlib's data is granted read-only beside the stdlib zip. `own` is an engine the caller
    made at wasmtime's defaults (no fuel, no epochs) and the module compiled on it, as another
    embedder's would be (spec 071, criterion 3); the driver's cached engine is never swapped, and
    such a run counts no fuel. A `measured` run (the default: one whose fuel a check records) is
    refused before anything runs when its inputs name a host path under the checkout, the
    system's temp folder or `host_roots` (spec 081): its fuel would depend on where they are."""
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
    ordered = (
        [*extra, (str(root), "/", True)] if preopens_first else [(str(root), "/", True), *extra]
    )
    if lib is not None:
        ordered.insert(0, (str(lib), "/usr/local/lib", False))
    if mpl_data:
        if stdlib is None or lib is None or not stdlib.is_file():
            raise ValueError("matplotlib's data comes from a stdlib zip")
        name = stdlib_name(python_version or "", stdlib)
        data = mpl_data_dir(stdlib, workdir)
        ordered.insert(1, (str(data), f"/usr/local/lib/{name}/matplotlib/mpl-data", False))
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

    def random_get(caller: wt.Caller, buf: int, n: int) -> int:
        caller.get("memory").write(caller, take_random(n), buf)
        return 0

    def clock_time_get(caller: wt.Caller, clock_id: int, _precision: int, out: int) -> int:
        start = REALTIME_START_NS if clock_id == 0 else 0
        value = start + next(ticks) * CLOCK_STEP_NS
        caller.get("memory").write(caller, struct.pack("<Q", value), out)
        return 0

    def clock_res_get(caller: wt.Caller, clock_id: int, out: int) -> int:
        if clock_id not in CLOCK_RESOLUTION_NS:
            return 28  # EINVAL: an unknown clock, as WASI answers
        caller.get("memory").write(
            caller, struct.pack("<Q", CLOCK_RESOLUTION_NS[clock_id]), out & 0xFFFFFFFF
        )
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

    exit_code: int | None = None
    trapped: str | None = None
    cause: str | None = None
    metered = False  # the budget is set only once instantiation has succeeded
    try:
        inst = linker.instantiate(store, mod)
        if counted:
            store.set_fuel(fuel)
            metered = True
        exports = inst.exports(store)
        if how == "command":
            exports["_start"](store)
            exit_code = 0
        else:
            if how == "reactor":
                exports["_initialize"](store)
            exit_code = exports["run"](store)
    except wt.ExitTrap as e:
        exit_code = e.code
    except wt.Trap as e:
        trapped = "out of fuel" if e.trap_code == wt.TrapCode.OUT_OF_FUEL else e.message
        cause = None if trapped == "out of fuel" else trap_cause(trapped or "")
        trapped = trapped.strip().splitlines()[0] if trapped else "trap"
    except wt.WasmtimeError as e:
        trapped = str(e).strip().splitlines()[0]
    spent = fuel - store.get_fuel() if metered else 0
    return Result(
        exit_code=exit_code,
        stdout=(io / "stdout").read_bytes(),
        stderr=(io / "stderr").read_bytes(),
        trapped=trapped,
        fuel=spent,
        root=root,
        trap_cause=cause,
    )


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
        lib = base / "lib"
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
        try:
            if self.how == "reactor" and not self._initialized:
                self._initialized = True
                self.exports["_initialize"](self.store)
            value = fn()
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
        self.store.close()


def turns(wasm: Path, **kw: Any) -> Turns:
    """A `Turns` instance of `wasm` (spec 055)."""
    return Turns(wasm, **kw)
