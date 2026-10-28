"""A bare embedding of the 0.1.1 snapshot through wasmtime-py's public API, for the starting-image spike.

The product's engine and module cache are reused (wasi_python._engines), so the compiled code is the
product's; everything else (the store, WASI, the preopens, the turns) is made here, in the shape
the runner gives a call: the stdlib folder at /usr/local/lib, matplotlib's data inside it, a fresh
writable root at /, a HOME under /tmp, the runner's base environment. Two WASI calls are shadowed
by Python functions that count them (random_get, clock_time_get by clock id) and answer as the
host would. Nothing under src/ is edited; nothing here is product code.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import tempfile
import threading
import time
from collections import Counter
from pathlib import Path

import wasmtime as wt

from wasi_python import _artifacts, _engines, _zip

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
WORK = REPO / "build" / "starting-image"
ARGV0 = "/usr/local/bin/python.wasm"
BASE_ENV = {"TMPDIR": "/tmp", "PYTHONTZPATH": ""}
UNMETERED = 2**63 - 1
FUEL = 10**13
PAGE = 65536

COUNTS: Counter = Counter()  # the shadowed calls, by phase label
PHASE = ["init"]
MONO_ORIGIN: dict[int, int] = {}  # store id -> perf_counter_ns at its WASI config, as wasmtime's own clock


def set_phase(name: str) -> None:
    PHASE[0] = name


def _found():
    return _artifacts.artifacts()


def engine_and_module(binary: Path | None = None):
    os.environ.setdefault("WASI_PYTHON_CACHE", str(WORK / "cache"))
    engine = _engines._engine(True)
    found = _found()
    binary = binary or found.snapshot
    cache = _engines._cache_dir(None)
    t0 = time.perf_counter()
    module = _engines._module(engine, True, binary, cache, None)
    return engine, module, time.perf_counter() - t0


def _linker(engine):
    linker = wt.Linker(engine)
    linker.define_wasi()
    linker.allow_shadowing = True
    i32, i64 = wt.ValType.i32(), wt.ValType.i64()

    def random_get(caller, buf, length):
        COUNTS[(PHASE[0], "random_get")] += 1
        COUNTS[(PHASE[0], "random_get bytes")] += length
        caller["memory"].write(caller, os.urandom(length), buf)
        return 0

    def clock_time_get(caller, clock, precision, out):
        COUNTS[(PHASE[0], f"clock_time_get {clock}")] += 1
        if clock == 0:
            now = time.time_ns()
        else:
            now = time.perf_counter_ns() - MONO_ORIGIN.get(0, 0)
        caller["memory"].write(caller, now.to_bytes(8, "little"), out)
        return 0

    def door(caller, a, b, c, d):
        return 1  # no host: the guest is told there is none

    linker.define_func("wasi_snapshot_preview1", "random_get", wt.FuncType([i32, i32], [i32]), random_get, True)
    linker.define_func(
        "wasi_snapshot_preview1", "clock_time_get", wt.FuncType([i32, i64, i32], [i32]), clock_time_get, True
    )
    linker.define_func("host", "call", wt.FuncType([i32] * 4, [i32]), door, True)
    return linker


class Guest:
    """One instance: a store, its WASI config, its root and its outputs."""

    _linkers: dict = {}

    def __init__(self, engine, module, env=None, extra_dirs=(), tag="g", monotonic_origin=None, argv=()):
        self.engine, self.module = engine, module
        found = _found()
        folder = _zip._zip_folder(found)
        WORK.mkdir(parents=True, exist_ok=True)
        self.dir = Path(tempfile.mkdtemp(prefix=f"{tag}-", dir=WORK))
        root = self.dir / "root"
        (root / "usr" / "local" / "lib").mkdir(parents=True)
        home = "/tmp/.home"
        (root / "tmp" / ".home").mkdir(parents=True)
        self.root = root
        wasi = wt.WasiConfig()
        wasi.argv = [ARGV0, *argv]
        wasi.env = sorted({**BASE_ENV, "HOME": home, **(env or {})}.items())
        wasi.preopen_dir(str(folder.lib), "/usr/local/lib", False)
        if folder.data is not None:
            wasi.preopen_dir(str(folder.data), f"/usr/local/lib/{folder.name}/{_zip.MPL_DATA_GUEST}", False)
        wasi.preopen_dir(str(root), "/", True)
        for host, guest in extra_dirs:
            wasi.preopen_dir(str(host), guest, False)
        (self.dir / "stdin").write_bytes(b"")
        wasi.stdin_file = str(self.dir / "stdin")
        self.out_path, self.err_path = self.dir / "stdout", self.dir / "stderr"
        wasi.stdout_file = str(self.out_path)
        wasi.stderr_file = str(self.err_path)
        if monotonic_origin is None:
            MONO_ORIGIN[0] = time.perf_counter_ns()
        self.store = wt.Store(engine)
        self.store.set_fuel(UNMETERED)
        self.store.set_epoch_deadline(1 << 40)
        self.store.set_wasi(wasi)
        linker = Guest._linkers.get(id(engine))
        if linker is None:
            linker = Guest._linkers[id(engine)] = _linker(engine)
        t0 = time.perf_counter()
        self.instance = linker.instantiate(self.store, module)
        self.instantiate_s = time.perf_counter() - t0
        self.exports = self.instance.exports(self.store)
        self.memory = self.exports["memory"]
        if "_initialize" in self.exports:
            self.exports["_initialize"](self.store)
        self.store.set_fuel(FUEL)
        self._out_seen = 0
        self._err_seen = 0

    # --- the reactor's exports ------------------------------------------------------------
    def turn(self, code: str) -> dict:
        data = code.encode()
        before = self.store.get_fuel()
        t0 = time.perf_counter()
        p = self.exports["host_alloc"](self.store, len(data)) & 0xFFFFFFFF
        self.memory.write(self.store, data, p)
        status = trapped = None
        try:
            status = self.exports["turn"](self.store, p, len(data))
        except wt.ExitTrap as e:
            status = f"exit {e.code}"
        except wt.Trap as e:
            trapped = str(e).splitlines()[0]
        seconds = time.perf_counter() - t0
        return {"status": status, "trapped": trapped, "fuel": before - self.store.get_fuel(), "s": seconds, **self.new_output()}

    def shutdown(self) -> dict:
        before = self.store.get_fuel()
        t0 = time.perf_counter()
        status = self.exports["shutdown"](self.store)
        return {"status": status, "fuel": before - self.store.get_fuel(), "s": time.perf_counter() - t0, **self.new_output()}

    def new_output(self) -> dict:
        out = self.out_path.read_bytes() if self.out_path.exists() else b""
        err = self.err_path.read_bytes() if self.err_path.exists() else b""
        o, e = out[self._out_seen :], err[self._err_seen :]
        self._out_seen, self._err_seen = len(out), len(err)
        return {"stdout": o.decode(errors="replace"), "stderr": e.decode(errors="replace")}

    # --- the image ------------------------------------------------------------------------
    def pages(self) -> int:
        return self.memory.size(self.store)

    def capture(self) -> bytes:
        n = self.memory.data_len(self.store)
        return ctypes.string_at(self.memory.data_ptr(self.store), n)

    def restore(self, image, how: str = "memmove") -> dict:
        """Grow to the image's size and copy it in. `image` is bytes or a buffer."""
        t0 = time.perf_counter()
        want = len(image) // PAGE
        have = self.pages()
        if want > have:
            self.memory.grow(self.store, want - have)
        t1 = time.perf_counter()
        if how == "memmove":
            buf = (ctypes.c_char * len(image)).from_buffer_copy(image) if isinstance(image, bytes) and False else image
            ctypes.memmove(self.memory.data_ptr(self.store), buf, len(image))
        elif how == "write":
            self.memory.write(self.store, image, 0)
        else:
            raise ValueError(how)
        t2 = time.perf_counter()
        return {"grow_s": t1 - t0, "copy_s": t2 - t1, "pages": want, "grown_by": max(0, want - have)}

    def close(self) -> None:
        self.store.close() if hasattr(self.store, "close") else None
        shutil.rmtree(self.dir, ignore_errors=True)


def on_big_stack(fn, *args, **kwargs):
    """Run fn on a thread with room for the 8 MiB wasm stack, as the runner does; return its result."""
    box: dict = {}

    def body():
        try:
            box["value"] = fn(*args, **kwargs)
        except BaseException as e:  # noqa: BLE001
            box["error"] = e

    old = threading.stack_size(64 << 20)
    try:
        t = threading.Thread(target=body)
        t.start()
    finally:
        threading.stack_size(old)
    t.join()
    if "error" in box:
        raise box["error"]
    return box["value"]
