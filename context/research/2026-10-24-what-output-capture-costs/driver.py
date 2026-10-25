"""What output capture costs: arms, attribution and prototypes, monkeypatched from here.

Run from the repository root with its uv environment (the artifact set at build/artifacts):
    uv run --no-sync python context/research/2026-10-24-what-output-capture-costs/driver.py <suite> [repeats]

Suites: repro, attribute, sizes, stderr, protos, cap, all. Results go to results/<suite>.json.
Nothing under src/ is edited: every prototype replaces a module global of wasi_python._call for
the duration of one run and restores it after.
"""

from __future__ import annotations

import ctypes
import json
import os
import statistics
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]  # context/research/<this folder>/ -> the repository
SET = REPO / "build/artifacts"
WORK = REPO / "build/output-capture-costs"  # the driver's own folders, never beside this file
os.environ["WASI_PYTHON_ARTIFACTS"] = str(SET)
sys.path.insert(0, str(REPO / "tests"))

import wasmtime as wt  # noqa: E402
from wasmtime import _bindings, _ffi  # noqa: E402

import wasi_python  # noqa: E402
from wasi_python import _call  # noqa: E402
from wasi_python._process import process  # noqa: E402
from harness import guest  # noqa: E402

CACHE = WORK / "cwasm"  # the product compiles the snapshot here once, about 30 s, if absent
LIB = WORK / "lib"  # the stdlib zip under the name the guest expects, for the bare arms
IO = WORK / "io"
BARE_CWASM = REPO / "build/rust-spike-perf/work/cwasm-bare/python-snapshot.cwasm"
SNAPSHOT = SET / "python-snapshot.wasm"
MEMORY, DEADLINE, FUEL = 1 << 30, 60.0, 10**12
UNMETERED = 2**63 - 1
BASE_ENV = {"TMPDIR": "/tmp", "PYTHONTZPATH": ""}

# --- guest programs ---------------------------------------------------------------------------

# The speed spike's program, as written there: 512 writes of 64 KiB through sys.stdout.buffer.
STDOUT_32M = """
import sys
chunk = b'y' * 65536
w = sys.stdout.buffer
for _ in range(512):
    w.write(chunk)
w.flush()
"""


def os_write_program(size: int, count: int, fd: int = 1) -> str:
    """One fd_write per os.write: no BufferedWriter between the program and WASI."""
    return f"import os\nchunk = b'y' * {size}\nfor _ in range({count}):\n    os.write({fd}, chunk)\n"


# --- arm: product -----------------------------------------------------------------------------


def product(code: str, *, output_bytes: int | None = 64 << 20) -> tuple[float, int, wasi_python.Completed]:
    t = time.perf_counter()
    c = wasi_python.run(
        ["-c", code],
        snapshot=True,
        fuel=FUEL,
        deadline_s=DEADLINE,
        memory_bytes=MEMORY,
        output_bytes=output_bytes,
        cache_dir=CACHE,
    )
    ms = (time.perf_counter() - t) * 1e3
    if c.trapped or c.exit_code != 0:
        raise SystemExit(f"product: {c.trapped} {c.exit_code} {c.stderr[-300:]!r}")
    return ms, len(c.stdout), c


# --- arm: bare wasmtime-py ---------------------------------------------------------------------

_engine = None
_module = None


def bare_engine() -> wt.Engine:
    global _engine
    if _engine is None:
        cfg = wt.Config()
        cfg.consume_fuel = True
        cfg.epoch_interruption = True
        _engine = wt.Engine(cfg)
    return _engine


def bare_module() -> wt.Module:
    global _module
    if _module is None:
        t = time.perf_counter()
        if BARE_CWASM.is_file():
            _module = wt.Module.deserialize_file(bare_engine(), str(BARE_CWASM))
        else:
            _module = wt.Module.from_file(bare_engine(), str(SNAPSHOT))
        print(f"  bare: module in {(time.perf_counter() - t) * 1e3:.0f} ms", file=sys.stderr)
    return _module


# Raw CFUNCTYPE callbacks for the bare arm, each kept alive for the process.
OUT_WRITE_T = _bindings._wasi_config_set_stdout_custom.argtypes[1]
OUT_FREE_T = _bindings._wasi_config_set_stdout_custom.argtypes[3]
RAW_SINK: list[bytearray] = [bytearray()]
RAW_CALLS = [0]


def _raw_nothing(key, data, size):
    RAW_CALLS[0] += 1
    return size


def _raw_string_at(key, data, size):
    RAW_CALLS[0] += 1
    ctypes.string_at(data, size)
    return size


def _raw_product_like(key, data, size):
    """The product's callback, re-made here: lock, lookup, string_at, _Stream.write."""
    RAW_CALLS[0] += 1
    with process().outputs_lock:
        stream = process().outputs.get(key or 0)
    return size if stream is None else stream.write(ctypes.string_at(data, size))


def _raw_free(key):
    return None


LIBC = ctypes.CDLL(None)
DEVNULL = os.open(os.devnull, os.O_WRONLY)
RAW = {
    "custom-libc": ctypes.cast(LIBC.write, OUT_WRITE_T),  # write(fd, buf, n): the key is the fd
    "custom-raw": OUT_WRITE_T(_raw_nothing),
    "custom-copy": OUT_WRITE_T(_raw_string_at),
    "custom-product-like": OUT_WRITE_T(_raw_product_like),
}
RAW_FREE = OUT_FREE_T(_raw_free)


def _drain(fds, streams, chunk=1 << 20):
    """Read every pipe to EOF into its stream; the stream's cap drops what is past it."""
    import select

    open_ = dict(zip(fds, streams))
    while open_:
        ready, _, _ = select.select(list(open_), [], [])
        for fd in ready:
            data = os.read(fd, chunk)
            if data:
                open_[fd].write(data)
            else:
                os.close(fd)
                del open_[fd]


def bare_on_thread(code: str, *, mode: str = "file") -> tuple[float, int]:
    """The bare arm on a spawned thread with an 8 MiB stack, as the product runs its guest."""
    box = []
    old = threading.stack_size(8 << 20)
    try:
        th = threading.Thread(target=lambda: box.append(bare(code, mode=mode)))
        th.start()
        th.join()
    finally:
        threading.stack_size(old)
    return box[0]


def ensure_lib() -> Path:
    """The bare arms' stdlib folder: the set's zip linked under the name the guest looks for."""
    LIB.mkdir(parents=True, exist_ok=True)
    z = LIB / guest.stdlib_name("3.15.0", SET / "python-stdlib.zip")
    if not z.exists():
        try:
            os.link(SET / "python-stdlib.zip", z)
        except OSError:
            z.write_bytes((SET / "python-stdlib.zip").read_bytes())
    return LIB


def bare(code: str, *, mode: str = "file") -> tuple[float, int]:
    """mode: file | custom-pub | custom-raw | custom-copy | custom-product-like | pipe."""
    io = IO / f"bare-{threading.get_ident()}"
    io.mkdir(parents=True, exist_ok=True)
    engine, mod = bare_engine(), bare_module()
    RAW_CALLS[0] = 0
    sink = bytearray()
    stream = _call._Stream("stdout", 64 << 20)
    t = time.perf_counter()
    store = wt.Store(engine)
    store.set_fuel(UNMETERED)
    store.set_epoch_deadline(2**40)
    store.set_limits(memory_size=MEMORY)
    wasi = wt.WasiConfig()
    wasi.argv = [guest.ARGV0, "-c", code]
    wasi.env = sorted(BASE_ENV.items())
    wasi.preopen_dir(str(ensure_lib()), "/usr/local/lib", False)
    if mode == "file":
        wasi.stdout_file = str(io / "stdout")
    elif mode == "custom-pub":
        wasi.stdout_custom = lambda b: sink.extend(b)  # wasmtime-py's own table and copy
    elif mode == "custom-product-like":
        with process().outputs_lock:
            key = next(process().output_keys)
            process().outputs[key] = stream
        _ffi.wasi_config_set_stdout_custom(wasi.ptr(), RAW[mode], key, RAW_FREE)
    elif mode == "custom-libc":
        _ffi.wasi_config_set_stdout_custom(wasi.ptr(), RAW[mode], DEVNULL, RAW_FREE)
    elif mode == "pipe":
        r, w = os.pipe()
        wasi.stdout_file = f"/dev/fd/{w}"  # wasmtime opens the pipe's write end anew
        os.close(w)
        reader = threading.Thread(target=_drain, args=((r,), (stream,)), daemon=True)
        reader.start()
    else:
        _ffi.wasi_config_set_stdout_custom(wasi.ptr(), RAW[mode], 1, RAW_FREE)
    wasi.stderr_file = str(io / "stderr")
    store.set_wasi(wasi)
    linker = wt.Linker(engine)
    linker.define_wasi()
    i32 = wt.ValType.i32()
    linker.define_func("host", "call", wt.FuncType([i32] * 4, [i32]), lambda *a: -1, True)
    instance = linker.instantiate(store, mod)
    store.set_fuel(FUEL)
    exports = instance.exports(store)
    code_out = None
    try:
        code_out = exports["run"](store)
    except wt.ExitTrap as e:
        code_out = e.code
    if mode == "pipe":
        store.close()  # drops wasmtime's write end: EOF for the reader
        reader.join()
        n = len(stream.data)
    ms = (time.perf_counter() - t) * 1e3
    if mode == "file":
        n = (io / "stdout").stat().st_size
    elif mode == "pipe":
        pass
    elif mode == "custom-pub":
        n = len(sink)
    elif mode == "custom-product-like":
        n = len(stream.data)
        with process().outputs_lock:
            process().outputs.pop(key, None)
    elif mode == "custom-libc":
        n = -1
    else:
        n = RAW_CALLS[0]
    if code_out != 0:
        raise SystemExit(f"bare: exit {code_out} {(io / 'stderr').read_bytes()[-300:]!r}")
    return ms, n


# --- the product, instrumented or with a prototype in place of its callback ---------------------


class Patched:
    """Replace module globals of wasi_python._call for one run, then restore them."""

    def __init__(self, **names):
        self.names, self.saved = names, {}

    def __enter__(self):
        for k, v in self.names.items():
            self.saved[k] = getattr(_call, k)
            setattr(_call, k, v)
        return self

    def __exit__(self, *exc):
        for k, v in self.saved.items():
            setattr(_call, k, v)


WRITE_T = ctypes.CFUNCTYPE(ctypes.c_ssize_t, ctypes.c_void_p, ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t)

STAMPS: list[tuple[int, int, int, int]] = []  # (t_in_ns, t_out_ns, size, thread ident)


def _stamped(key, data, size):
    t0 = time.perf_counter_ns()
    r = _call._write_output(key, data, size)
    # The OS thread's ident is cheap; the Python thread's name is read for the first four
    # callbacks only, since naming a thread Python has never seen makes a `_DummyThread`, and a
    # fresh name on each callback means a fresh thread state on each callback.
    name = threading.current_thread().name if len(STAMPS) < 4 else threading.get_ident()
    STAMPS.append((t0, time.perf_counter_ns(), size, name))
    return r


STAMPED = WRITE_T(_stamped)

# Prototype A1: one copy per write, a growing bytearray; the lock and the lookup kept.


class StreamA1:
    def __init__(self, name, cap):
        self.name, self.cap, self.data, self.dropped = name, cap, bytearray(), False

    def write_from(self, data, size):
        room = size if self.cap is None else max(0, self.cap - len(self.data))
        if room < size:
            self.dropped = True
        n = min(room, size)  # the write's own size, never the room: the room may be larger
        if n:
            self.data += (ctypes.c_ubyte * n).from_address(ctypes.addressof(data.contents))
        return size


def _write_a1(key, data, size):
    try:
        with process().outputs_lock:
            stream = process().outputs.get(key or 0)
        return size if stream is None else stream.write_from(data, size)
    except BaseException:
        return size


# Prototype A2: one copy into a bytearray preallocated to the cap, a memoryview target.


class StreamA2:
    def __init__(self, name, cap):
        self.name, self.cap, self.dropped, self.pos = name, cap, False, 0
        self.buf = bytearray(cap if cap is not None else 0)
        self.view = memoryview(self.buf)

    @property
    def data(self):
        return self.view[: self.pos]

    def write_from(self, data, size):
        room = max(0, self.cap - self.pos)
        if room < size:
            self.dropped = True
        n = min(room, size)
        if n:
            ctypes.memmove(ctypes.addressof(ctypes.c_char.from_buffer(self.buf, self.pos)), data, n)
            self.pos += n
        return size


# Prototype A3: A1's copy without the lock and lookup (a plain dict read): the lock's share.


def _write_a3(key, data, size):
    try:
        stream = process().outputs.get(key or 0)
        return size if stream is None else stream.write_from(data, size)
    except BaseException:
        return size


# Prototype A4: memmove into a bytearray grown by a zero-filled extension (no per-size types).


class StreamA4:
    def __init__(self, name, cap):
        self.name, self.cap, self.data, self.dropped = name, cap, bytearray(), False

    def write_from(self, data, size):
        room = size if self.cap is None else max(0, self.cap - len(self.data))
        if room < size:
            self.dropped = True
        n = min(room, size)
        if n:
            start = len(self.data)
            self.data += bytes(n)
            ctypes.memmove(ctypes.addressof(ctypes.c_char.from_buffer(self.data, start)), data, n)
        return size


# Prototype A5: the current two copies, but the lock and lookup dropped: is the lock the cost?


def _write_a5(key, data, size):
    try:
        stream = process().outputs.get(key or 0)
        return size if stream is None else stream.write(ctypes.string_at(data, size))
    except BaseException:
        return size


PROTOS = {
    "a1-one-copy-grow": (WRITE_T(_write_a1), StreamA1),
    "a2-one-copy-prealloc": (WRITE_T(_write_a1), StreamA2),
    "a3-one-copy-no-lock": (WRITE_T(_write_a3), StreamA1),
    "a4-one-copy-memmove-grow": (WRITE_T(_write_a1), StreamA4),
    "a5-two-copies-no-lock": (WRITE_T(_write_a5), _call._Stream),
}


def product_proto(code: str, name: str, *, output_bytes: int | None = 64 << 20):
    write, stream_cls = PROTOS[name]
    with Patched(_output_write=write, _Stream=stream_cls):
        return product(code, output_bytes=output_bytes)


def product_stamped(code: str, *, output_bytes: int | None = 64 << 20):
    STAMPS.clear()
    with Patched(_output_write=STAMPED):
        ms, n, c = product(code, output_bytes=output_bytes)
    stamps = list(STAMPS)
    inside_ns = sum(b - a for a, b, _, _ in stamps)
    sizes = sorted({s for _, _, s, _ in stamps})
    from collections import Counter

    names = Counter(i for _, _, _, i in stamps if isinstance(i, int))
    first = [i for _, _, _, i in stamps[:4]]
    return ms, n, {
        "first_four_thread_names": first,
        "callbacks": len(stamps),
        "inside_ms": inside_ns / 1e6,
        "per_callback_us": inside_ns / 1e3 / max(1, len(stamps)),
        "sizes": sizes[:8],
        "os_threads": dict(names),
        "on_home_thread": threading.get_ident() in names,
    }


# Design (b): the product with wasmtime writing stdout to a file in the call's scratch; no
# callback. The cap cannot be enforced live; the file holds whatever the guest wrote.
FILE_PATHS: list[Path] = []


def _send_outputs_file(wasi, out, err):
    p = process()
    with p.outputs_lock:
        keys = next(p.output_keys), next(p.output_keys)
        p.outputs[keys[0]], p.outputs[keys[1]] = out, err
    io = IO / f"product-file-{threading.get_ident()}"
    io.mkdir(parents=True, exist_ok=True)
    FILE_PATHS[:] = [io / "stdout", io / "stderr"]
    wasi.stdout_file = str(FILE_PATHS[0])
    wasi.stderr_file = str(FILE_PATHS[1])
    return keys


def product_file(code: str, *, output_bytes: int | None = 64 << 20):
    with Patched(_send_outputs=_send_outputs_file):
        ms, _, c = product(code, output_bytes=output_bytes)
    return ms, FILE_PATHS[0].stat().st_size, c


# Design (b2): wasmtime writes each stream into a pipe the runner opened; one reader thread per
# call drains both pipes into the two streams, whose cap is enforced as the bytes arrive. The
# host never holds more than the cap plus the pipes' kernel buffers. The streams' `data` and
# `dropped` wait for the reader, which ends at EOF, which the store's close delivers.


class StreamP:
    def __init__(self, name, cap):
        self.name, self.cap, self._data, self._dropped = name, cap, bytearray(), False
        self.reader = None

    def write(self, data):
        room = len(data) if self.cap is None else max(0, self.cap - len(self._data))
        if room < len(data):
            self._dropped = True
        self._data.extend(data[:room])
        return len(data)

    def _join(self):
        if self.reader is not None:
            self.reader.join()

    @property
    def data(self):
        self._join()
        return self._data

    @property
    def dropped(self):
        self._join()
        return self._dropped


def _send_outputs_pipe(wasi, out, err):
    p = process()
    with p.outputs_lock:
        keys = next(p.output_keys), next(p.output_keys)
    (r1, w1), (r2, w2) = os.pipe(), os.pipe()
    wasi.stdout_file = f"/dev/fd/{w1}"
    wasi.stderr_file = f"/dev/fd/{w2}"
    os.close(w1)
    os.close(w2)
    reader = threading.Thread(target=_drain, args=((r1, r2), (out, err)), daemon=True)
    out.reader = err.reader = reader
    reader.start()
    return keys


def product_pipe(code: str, *, output_bytes: int | None = 64 << 20):
    with Patched(_send_outputs=_send_outputs_pipe, _Stream=StreamP):
        return product(code, output_bytes=output_bytes)


def crossing_floor(n: int = 20000) -> dict:
    """What one ctypes callback costs when C calls it on a thread that holds a Python thread
    state (here: Python calls the C thunk, which calls back): the floor of the crossing."""
    buf = (ctypes.c_ubyte * 4096)()
    cb = RAW["custom-raw"]
    cb(None, buf, 4096)
    t = time.perf_counter()
    for _ in range(n):
        cb(None, buf, 4096)
    us = (time.perf_counter() - t) * 1e6 / n
    # The same callback on a thread with no Python thread state: a C thread. ctypes offers none
    # here; the libc arm against the raw arm inside wasmtime stands for it.
    return {"direct_call_us": us}


# --- the suites --------------------------------------------------------------------------------


def repeat(fn, n: int):
    rows = [fn() for _ in range(n)]
    ms = [r[0] for r in rows]
    return {
        "median_ms": statistics.median(ms),
        "min_ms": min(ms),
        "runs": ms,
        "n": [r[1] for r in rows],
        "extra": [r[2] for r in rows if len(r) > 2 and isinstance(r[2], dict)],
    }


def suite_repro(n: int) -> dict:
    return {
        "program": "the spike's STDOUT_32M (sys.stdout.buffer, 512 x 64 KiB)",
        "product": repeat(lambda: product(STDOUT_32M), n),
        "bare-file": repeat(lambda: bare(STDOUT_32M, mode="file"), n),
        "bare-custom-pub": repeat(lambda: bare(STDOUT_32M, mode="custom-pub"), n),
    }


def suite_attribute(n: int) -> dict:
    code = os_write_program(65536, 512)
    out = {"program": "os.write(1, 64 KiB) x 512"}
    out["product"] = repeat(lambda: product(code), n)
    out["product-stamped"] = repeat(lambda: product_stamped(code), n)
    out["product-file"] = repeat(lambda: product_file(code), n)
    out["bare-file"] = repeat(lambda: bare(code, mode="file"), n)
    out["bare-file-on-thread"] = repeat(lambda: bare_on_thread(code, mode="file"), n)
    out["bare-pipe"] = repeat(lambda: bare(code, mode="pipe"), n)
    out["product-pipe"] = repeat(lambda: product_pipe(code), n)
    out["bare-custom-libc"] = repeat(lambda: bare(code, mode="custom-libc"), n)
    out["bare-custom-raw"] = repeat(lambda: bare(code, mode="custom-raw"), n)
    out["bare-custom-copy"] = repeat(lambda: bare(code, mode="custom-copy"), n)
    out["bare-custom-product-like"] = repeat(lambda: bare(code, mode="custom-product-like"), n)
    out["bare-custom-pub"] = repeat(lambda: bare(code, mode="custom-pub"), n)
    out["empty"] = {
        "product": repeat(lambda: product("pass"), n),
        "product-pipe": repeat(lambda: product_pipe("pass"), n),
        "bare-file": repeat(lambda: bare("pass", mode="file"), n),
    }
    out["crossing-floor"] = crossing_floor()
    return out


def suite_sizes(n: int) -> dict:
    out = {}
    for size, count in ((4096, 8192), (65536, 512), (1 << 20, 32)):
        code = os_write_program(size, count)
        key = f"{size}x{count}"
        out[key] = {
            "product": repeat(lambda: product(code), n),
            "product-stamped": repeat(lambda: product_stamped(code), n),
            "product-file": repeat(lambda: product_file(code), n),
            "bare-file": repeat(lambda: bare(code, mode="file"), n),
            "bare-custom-libc": repeat(lambda: bare(code, mode="custom-libc"), n),
            "bare-custom-raw": repeat(lambda: bare(code, mode="custom-raw"), n),
            "product-pipe": repeat(lambda: product_pipe(code), n),
            "a1-one-copy-grow": repeat(lambda: product_proto(code, "a1-one-copy-grow"), n),
        }
    return out


def suite_stderr(n: int) -> dict:
    code = os_write_program(65536, 512, fd=2)
    return {
        "program": "os.write(2, 64 KiB) x 512",
        "product": repeat(lambda: product(code), n),
        "product-stamped": repeat(lambda: product_stamped(code), n),
        "product-file": repeat(lambda: product_file(code), n),
        "product-pipe": repeat(lambda: product_pipe(code), n),
        "a1-one-copy-grow": repeat(lambda: product_proto(code, "a1-one-copy-grow"), n),
    }


def suite_protos(n: int) -> dict:
    code = os_write_program(65536, 512)
    out = {"program": "os.write(1, 64 KiB) x 512", "product": repeat(lambda: product(code), n)}
    for name in PROTOS:
        out[name] = repeat(lambda: product_proto(code, name), n)
    out["product-pipe"] = repeat(lambda: product_pipe(code), n)
    return out


def suite_cap(n: int) -> dict:
    """The promises, on each design: the cap exact at the byte, truncation named, stderr apart."""
    code = "import os,sys\nos.write(1, b'x' * (1 << 20))\nos.write(2, b'done\\n')\n"
    out = {}
    for name in ("product", *PROTOS):
        if name == "product":
            ms, _, c = product(code, output_bytes=4096)
        else:
            ms, _, c = product_proto(code, name, output_bytes=4096)
        out[name] = {
            "stdout_len": len(c.stdout),
            "stdout_ok": c.stdout == b"x" * 4096,
            "stderr": repr(c.stderr[:80]),
            "truncated": list(c.truncated),
        }
    ms, _, c = product_pipe(code, output_bytes=4096)
    out["product-pipe (design b2)"] = {
        "stdout_len": len(c.stdout),
        "stdout_ok": c.stdout == b"x" * 4096,
        "stderr": repr(c.stderr[:80]),
        "truncated": list(c.truncated),
    }
    mixed = "import os\nfor i in range(1000):\n    os.write(1, b'o'*7)\n    os.write(2, b'e'*5)\n"
    ms, _, c = product_pipe(mixed, output_bytes=None)
    out["product-pipe interleaved"] = {
        "stdout_ok": c.stdout == b"o" * 7000,
        "stderr_ok": c.stderr == b"e" * 5000,
        "truncated": list(c.truncated),
    }
    ms, size, c = product_file(code, output_bytes=4096)
    out["product-file (design b)"] = {
        "file_size_on_disk": size,
        "note": "the cap is not enforced: the file holds every byte the guest wrote",
        "truncated": list(c.truncated),
    }
    # The ctypes array-type cache: how many types does a sweep of sizes leave behind?
    import gc

    before = len(gc.get_objects())
    for s in range(1, 2001):
        (ctypes.c_ubyte * s)
    out["ctypes_array_types_after_2000_sizes"] = len(gc.get_objects()) - before
    return out


def suite_small(n: int) -> dict:
    """The common case: many small writes, as print() makes them."""
    code = os_write_program(100, 10000)
    return {
        "program": "os.write(1, 100 B) x 10,000",
        "product": repeat(lambda: product(code), n),
        "product-stamped": repeat(lambda: product_stamped(code), n),
        "product-file": repeat(lambda: product_file(code), n),
        "product-pipe": repeat(lambda: product_pipe(code), n),
        "bare-file": repeat(lambda: bare(code, mode="file"), n),
        "bare-pipe": repeat(lambda: bare(code, mode="pipe"), n),
        "bare-custom-libc": repeat(lambda: bare(code, mode="custom-libc"), n),
        "bare-custom-raw": repeat(lambda: bare(code, mode="custom-raw"), n),
    }


SUITES = {
    "repro": suite_repro,
    "small": suite_small,
    "attribute": suite_attribute,
    "sizes": suite_sizes,
    "stderr": suite_stderr,
    "protos": suite_protos,
    "cap": suite_cap,
}


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    names = list(SUITES) if which == "all" else [which]
    (HERE / "results").mkdir(exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    CACHE.chmod(0o700)  # the runner reads a module cache only from a private folder
    # Warm: one product run and one bare run, so the module load is outside every timer.
    product("pass")
    bare("pass")
    for name in names:
        t = time.perf_counter()
        result = SUITES[name](n)
        result["_meta"] = {
            "suite": name,
            "repeats": n,
            "seconds": round(time.perf_counter() - t, 1),
            "platform": sys.platform,
            "python": sys.version.split()[0],
        }
        (HERE / "results" / f"{name}.json").write_text(json.dumps(result, indent=1, default=str))
        print(f"{name}: {result['_meta']['seconds']} s", file=sys.stderr)
        for k, v in result.items():
            if isinstance(v, dict) and "median_ms" in v:
                print(f"  {k:32s} median {v['median_ms']:8.1f} ms  min {v['min_ms']:8.1f}  n={v['n'][0]}", file=sys.stderr)
                for e in v["extra"][:1]:
                    print(f"      {e}", file=sys.stderr)
            elif isinstance(v, dict) and k != "_meta":
                for k2, v2 in v.items():
                    if isinstance(v2, dict) and "median_ms" in v2:
                        print(f"  {k}/{k2:28s} median {v2['median_ms']:8.1f} ms  min {v2['min_ms']:8.1f}  n={v2['n'][0]}", file=sys.stderr)
                        for e in v2["extra"][:1]:
                            print(f"      {e}", file=sys.stderr)
                    else:
                        print(f"  {k}/{k2}: {v2}", file=sys.stderr)


if __name__ == "__main__":
    main()
