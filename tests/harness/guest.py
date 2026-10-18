"""The judge's own guest driver (spec 002, Decision 9).

It does only what any embedder must do: preopen the stdlib, read-only, in a folder of its own at
`/usr/local/lib` (spec 017: the runtime's files are never in a writable root), one directory at
`/` (and, when a check asks, more directories, read-only or writable, in a chosen order), bind
`host::call`, and call one export. It is kept apart from `wasi_python.run`, the runner it
judges. It also answers `random_get` and `clock_time_get` itself, so every run is seeded alike
and fuel (instructions executed) repeats to a few parts in ten million
(context/research/2026-10-16-a-host-supplied-clock-and-random-make-fuel-exact.md).
"""

from __future__ import annotations

import hashlib
import itertools
import os
import shutil
import struct
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

import wasmtime as wt

DEFAULT_FUEL = 2 * 10**11
UNMETERED = 2**63 - 1  # instantiation's own memory fill is not the guest's work (spec 008)
NO_HOST = -1
HOST_FAULT = -2
ARGV0 = "/usr/local/bin/python.wasm"
REALTIME_START_NS = 1_767_225_600_000_000_000  # 2026-01-01T00:00:00Z, a fixed start
CLOCK_STEP_NS = 1_000

_engine: wt.Engine | None = None
_modules: dict[tuple[str, int, int], wt.Module] = {}
_run_ids = itertools.count()


def engine() -> wt.Engine:
    global _engine
    if _engine is None:
        cfg = wt.Config()
        cfg.consume_fuel = True
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


def _random_stream() -> Callable[[int], bytes]:
    counter = itertools.count()

    def take(n: int) -> bytes:
        out = bytearray()
        while len(out) < n:
            out += hashlib.sha256(struct.pack("<Q", next(counter))).digest()
        return bytes(out[:n])

    return take


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
) -> Result:
    """Run the guest once, in a fresh instance and a fresh root under `workdir`."""
    mod = module(wasm)
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

    store = wt.Store(engine())
    store.set_fuel(UNMETERED)  # fuel is metered from the end of instantiation (spec 008)
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
    for host_dir, guest_path, writable in ordered:
        wasi.preopen_dir(host_dir, guest_path, writable)
    wasi.stdout_file = str(io / "stdout")
    wasi.stderr_file = str(io / "stderr")
    store.set_wasi(wasi)

    linker = wt.Linker(engine())
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
    linker.define_func("host", "call", wt.FuncType([i32] * 4, [i32]), door, True)

    exit_code: int | None = None
    trapped: str | None = None
    cause: str | None = None
    metered = False  # the budget is set only once instantiation has succeeded
    try:
        inst = linker.instantiate(store, mod)
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
