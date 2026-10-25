"""Does a Rust runner beat wasmtime-py on the costs the binding adds? Three arms on one wasmtime
(49.0.0, the one wasmtime-py 49.0.0 embeds), one artifact set, one Config (fuel on, epochs on):

- product: `wasi_python.run`, the shipped runner on wasmtime-py (its checks, threads, caches).
- bare:    a minimal wasmtime-py embedding in this file (what a thin Python wrapper costs).
- rust:    the spike binary on the `wasmtime` crate (what a Rust core costs).

Every number is wall-clock on one machine: a benchmark fact for a research memo, never a test.

    uv run --project <repo> python bench.py <rust-binary> <label>
"""

from __future__ import annotations

import json
import os
import statistics
import struct
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path("/Users/claygendron/Git/Repos/wasi_python")
SET = REPO / "build/artifacts"
WORK = REPO / "build/rust-spike-perf/work"
os.environ["WASI_PYTHON_ARTIFACTS"] = str(SET)
sys.path.insert(0, str(REPO / "tests"))

import wasmtime as wt  # noqa: E402

import wasi_python  # noqa: E402
from harness import guest  # noqa: E402

STDLIB = SET / "python-stdlib.zip"
BIN = {True: SET / "python-snapshot.wasm", False: SET / "python.wasm"}
ZNAME = guest.stdlib_name("3.15.0", STDLIB)
BASE_ENV = {"TMPDIR": "/tmp", "PYTHONTZPATH": ""}
MEMORY, DEADLINE, FUEL = 1 << 30, 60.0, 10**12
UNMETERED = 2**63 - 1
LIB = WORK / "lib"

# --- guest programs ---------------------------------------------------------------------------

HELLO = "print('hello')"
NUMPY = "import numpy as np; print(np.arange(10**6).sum())"
DOOR_SMALL = """
import _host
d = b'x' * 64
for _ in range(20000):
    _host.call(d)
print('ok')
"""
DOOR_LARGE = """
import _host
d = b'x' * (1 << 20)
for _ in range(500):
    _host.call(d)
print('ok')
"""
STDOUT_32M = """
import sys
chunk = b'y' * 65536
w = sys.stdout.buffer
for _ in range(512):
    w.write(chunk)
w.flush()
"""
FILES = """
import os
for i in range(20000):
    os.stat('/ro/f%d.txt' % (i % 100))
n = 0
for i in range(2000):
    with open('/ro/f%d.txt' % (i % 100), 'rb') as f:
        n += len(f.read())
print(n)
"""


class Files:
    """An in-memory provider: 100 files of 4 KiB (the mounts arm, Python's shadowed WASI)."""

    def __init__(self) -> None:
        self.tree = {f"/f{i}.txt": b"z" * 4096 for i in range(100)}

    def stat(self, path):
        if path == "/":
            return wasi_python.Stat("dir")
        d = self.tree.get(path)
        return wasi_python.Stat("file", len(d)) if d is not None else wasi_python.Errno.ENOENT

    def list(self, path):
        return [(p[1:], "file") for p in self.tree] if path == "/" else wasi_python.Errno.ENOTDIR

    def read(self, path):
        return self.tree.get(path, wasi_python.Errno.ENOENT)


def ro_dir() -> Path:
    d = WORK / "ro"
    if not d.exists():
        d.mkdir(parents=True)
        for i in range(100):
            (d / f"f{i}.txt").write_bytes(b"z" * 4096)
    return d


# --- arm: product -----------------------------------------------------------------------------

CACHE_PY = WORK / "cwasm-py"


def product(code: str, *, snapshot=True, echo=False, grants=(), mounts=(), output_bytes=None):
    extra = {} if output_bytes is None else {"output_bytes": output_bytes}
    if mounts:
        extra["max_file_calls"] = 10**6  # the program makes 22,000 calls; the default cap is 10,000
    t = time.perf_counter()
    c = wasi_python.run(
        ["-c", code],
        snapshot=snapshot,
        fuel=FUEL,
        deadline_s=DEADLINE,
        memory_bytes=MEMORY,
        host=(lambda b: b) if echo else None,
        **extra,
        grants=[wasi_python.Grant(str(h), g) for g, h in grants],
        mounts=[wasi_python.Mount(p, g) for g, p in mounts],
        cache_dir=CACHE_PY,
    )
    ms = (time.perf_counter() - t) * 1e3
    if c.trapped or c.exit_code != 0:
        raise SystemExit(f"product: {c.trapped} {c.exit_code} {c.stderr[-300:]!r}")
    return ms, len(c.stdout)


# --- arm: bare wasmtime-py ---------------------------------------------------------------------

_bare_engine = None
_bare_modules: dict[Path, wt.Module] = {}
CACHE_BARE = WORK / "cwasm-bare"


def bare_engine() -> wt.Engine:
    global _bare_engine
    if _bare_engine is None:
        cfg = wt.Config()
        cfg.consume_fuel = True
        cfg.epoch_interruption = True
        _bare_engine = wt.Engine(cfg)
    return _bare_engine


def bare_module(path: Path) -> wt.Module:
    if path not in _bare_modules:
        CACHE_BARE.mkdir(parents=True, exist_ok=True)
        cw = CACHE_BARE / (path.stem + ".cwasm")
        t = time.perf_counter()
        if cw.is_file():
            m = wt.Module.deserialize_file(bare_engine(), str(cw))
        else:
            m = wt.Module.from_file(bare_engine(), str(path))
            cw.write_bytes(m.serialize())
        print(f"  bare: module {path.name} in {(time.perf_counter() - t) * 1e3:.0f} ms", file=sys.stderr)
        _bare_modules[path] = m
    return _bare_modules[path]


def ensure_lib() -> Path:
    LIB.mkdir(parents=True, exist_ok=True)
    z = LIB / ZNAME
    if not z.exists():
        os.link(STDLIB, z)
    return LIB


def bare(code: str, *, snapshot=True, echo=False, grants=(), io: Path | None = None):
    io = io or (WORK / f"bare-io-{threading.get_ident()}")
    io.mkdir(parents=True, exist_ok=True)
    engine, mod = bare_engine(), bare_module(BIN[snapshot])
    t = time.perf_counter()
    store = wt.Store(engine)
    store.set_fuel(UNMETERED)
    store.set_epoch_deadline(2**40)
    store.set_limits(memory_size=MEMORY)
    wasi = wt.WasiConfig()
    wasi.argv = [guest.ARGV0, "-c", code]
    wasi.env = sorted(BASE_ENV.items())
    wasi.preopen_dir(str(ensure_lib()), "/usr/local/lib", False)
    for g, h in grants:
        wasi.preopen_dir(str(h), g, False)
    wasi.stdout_file = str(io / "stdout")
    wasi.stderr_file = str(io / "stderr")
    store.set_wasi(wasi)
    linker = wt.Linker(engine)
    linker.define_wasi()
    i32 = wt.ValType.i32()

    def door(caller, ptr, length, out_pp, out_lp):
        if not echo:
            return -1
        memory = caller.get("memory")
        ptr, length = ptr & 0xFFFFFFFF, length & 0xFFFFFFFF
        request = bytes(memory.read(caller, ptr, ptr + length))
        response = request
        p = caller.get("host_alloc")(caller, len(response)) & 0xFFFFFFFF
        if not p:
            return -2
        memory.write(caller, response, p)
        memory.write(caller, struct.pack("<I", p), out_pp & 0xFFFFFFFF)
        memory.write(caller, struct.pack("<I", len(response)), out_lp & 0xFFFFFFFF)
        return 0

    linker.define_func("host", "call", wt.FuncType([i32] * 4, [i32]), door, True)
    instance = linker.instantiate(store, mod)
    store.set_fuel(FUEL)
    exports = instance.exports(store)
    code_out = None
    try:
        if not snapshot:
            exports["_initialize"](store)
        code_out = exports["run"](store)
    except wt.ExitTrap as e:
        code_out = e.code
    ms = (time.perf_counter() - t) * 1e3
    out = (io / "stdout").read_bytes()
    if code_out != 0:
        raise SystemExit(f"bare: exit {code_out} {(io / 'stderr').read_bytes()[-300:]!r}")
    return ms, len(out)


# --- arm: rust ---------------------------------------------------------------------------------

RUST = Path(sys.argv[1])
CACHE_RS = WORK / "cwasm-rs"


def rust_jobs(code: str, n: int, *, snapshot=True, echo=False, grants=(), tag="j"):
    CACHE_RS.mkdir(parents=True, exist_ok=True)
    jobs = []
    for k in range(n):
        io = WORK / f"rs-io-{tag}-{k}"
        io.mkdir(parents=True, exist_ok=True)
        jobs.append(
            dict(
                id=f"{tag}-{k}",
                wasm=str(BIN[snapshot]),
                cwasm=str(CACHE_RS / (BIN[snapshot].stem + ".cwasm")),
                argv=[guest.ARGV0, "-c", code],
                env=sorted(BASE_ENV.items()),
                preopens=[[str(ensure_lib()), "/usr/local/lib", False]]
                + [[str(h), g, False] for g, h in grants],
                fuel=FUEL,
                memory_bytes=MEMORY,
                deadline_s=DEADLINE,
                mode="runner",
                door="echo" if echo else None,
                stdout_path=str(io / "stdout"),
                stderr_path=str(io / "stderr"),
            )
        )
    return jobs


def rust(jobs: list[dict], threads: int = 1):
    """Run one batch: (per-job run_ms list, batch_ms, process wall ms, module_ms)."""
    batch = dict(consume_fuel=True, epoch_interruption=True, collector="drc", threads=threads, jobs=jobs)
    t = time.perf_counter()
    p = subprocess.run([str(RUST)], input=json.dumps(batch).encode(), capture_output=True, check=False)
    wall = (time.perf_counter() - t) * 1e3
    if p.returncode != 0:
        raise SystemExit(f"rust exited {p.returncode}: {p.stderr.decode()[-2000:]}")
    runs, batch_ms, module_ms = [], None, None
    for line in p.stdout.decode().splitlines():
        o = json.loads(line)
        if "batch_ms" in o:
            batch_ms = o["batch_ms"]
            continue
        if "error" in o or o.get("exit_code") != 0:
            raise SystemExit(f"rust job {o.get('id')}: {o}")
        runs.append(o["run_ms"])
        module_ms = o["module_ms"]
    return runs, batch_ms, wall, module_ms


# --- the benchmarks ----------------------------------------------------------------------------

def stats(xs):
    xs = sorted(xs)
    return dict(n=len(xs), min=round(xs[0], 1), median=round(statistics.median(xs), 1), max=round(xs[-1], 1))


def bench_sequential(name, code, n, **kw):
    """Each arm runs the program n times in sequence; per-run wall in ms."""
    row = dict(bench=name, n=n)
    ms = [product(code, **{k: v for k, v in kw.items() if k != "tag"})[0] for _ in range(n)]
    row["product"] = stats(ms)
    ms = [bare(code, **{k: v for k, v in kw.items() if k in ("snapshot", "echo", "grants")})[0] for _ in range(n)]
    row["bare"] = stats(ms)
    jobs = rust_jobs(code, n, tag=name, **{k: v for k, v in kw.items() if k in ("snapshot", "echo", "grants")})
    runs, batch_ms, wall, module_ms = rust(jobs)
    row["rust"] = stats(runs)
    row["rust_batch_per_job"] = round(batch_ms / n, 1)
    row["rust_module_ms"] = round(module_ms, 1)
    print(json.dumps(row), file=sys.stderr, flush=True)
    return row


def bench_parallel(name, code, n, workers, repeats=3):
    """n runs of the program at once on `workers` threads, against n in sequence: wall of the whole."""
    row = dict(bench=name, n=n, workers=workers)
    for arm, fn in (("product", lambda: product(code)), ("bare", lambda: bare(code))):
        seq, par = [], []
        for _ in range(repeats):
            t = time.perf_counter()
            for _ in range(n):
                fn()
            seq.append((time.perf_counter() - t) * 1e3)
            t = time.perf_counter()
            with ThreadPoolExecutor(workers) as ex:
                list(ex.map(lambda _: fn(), range(n)))
            par.append((time.perf_counter() - t) * 1e3)
        row[arm] = dict(sequential=stats(seq), parallel=stats(par), speedup=round(statistics.median(seq) / statistics.median(par), 2))
    seq, par = [], []
    for _ in range(repeats):
        seq.append(rust(rust_jobs(code, n, tag=name), threads=1)[1])
        par.append(rust(rust_jobs(code, n, tag=name), threads=workers)[1])
    row["rust"] = dict(sequential=stats(seq), parallel=stats(par), speedup=round(statistics.median(seq) / statistics.median(par), 2))
    print(json.dumps(row), file=sys.stderr, flush=True)
    return row


def bench_mount(name, n):
    """The mounts arm alone: the same file program served by a Python provider."""
    ms = [product(FILES, grants=(), mounts=(("/ro", Files()),))[0] for _ in range(n)]
    row = dict(bench=name, n=n, product_mount=stats(ms))
    print(json.dumps(row), file=sys.stderr, flush=True)
    return row


def bench_cold(name, n=5):
    """A fresh process that runs one hello: wall and peak RSS, both sides, and the bare
    interpreter's own start for scale."""
    py_code = (
        "import os,sys; os.environ['WASI_PYTHON_ARTIFACTS']=%r; import wasi_python; "
        "c=wasi_python.run(['-c','print(1)'], fuel=10**12, cache_dir=%r); assert c.exit_code==0"
    ) % (str(SET), str(CACHE_PY))
    job = rust_jobs(HELLO, 1, tag="cold")
    batch = json.dumps(dict(consume_fuel=True, epoch_interruption=True, collector="drc", jobs=job)).encode()

    def timed(cmd, stdin=None):
        walls, rss = [], []
        for _ in range(n):
            t = time.perf_counter()
            p = subprocess.run(["/usr/bin/time", "-l", *cmd], input=stdin, capture_output=True, check=False, cwd=str(REPO))
            walls.append((time.perf_counter() - t) * 1e3)
            err = p.stderr.decode()
            if p.returncode != 0:
                raise SystemExit(f"{cmd[:2]}: {err[-500:]}")
            line = next(l for l in err.splitlines() if "maximum resident set size" in l)
            rss.append(int(line.split()[0]))  # darwin: bytes, this process tree's peak
        return stats(walls), max(rss) // (1 << 20)

    row = dict(bench=name, n=n)
    row["uv_python_pass"], _ = timed(["uv", "run", "--no-sync", "python", "-c", "pass"])
    row["product_process"], row["product_peak_rss_mib"] = timed(["uv", "run", "--no-sync", "python", "-c", py_code])
    row["rust_process"], row["rust_peak_rss_mib"] = timed([str(RUST)], batch)
    print(json.dumps(row), file=sys.stderr, flush=True)
    return row


def main() -> None:
    label = sys.argv[2]
    WORK.mkdir(parents=True, exist_ok=True)
    ro = ro_dir()
    print("warm-up (compiles the modules into each arm's cache)", file=sys.stderr)
    for snap in (True, False):
        product(HELLO, snapshot=snap)
        bare(HELLO, snapshot=snap)
        rust(rust_jobs(HELLO, 1, snapshot=snap, tag=f"warm{snap}"))
    only = set(os.environ.get("BENCH_ONLY", "").split(",")) - {""}
    plan = [
        ("hello-snapshot", lambda: bench_sequential("hello-snapshot", HELLO, 20)),
        ("hello-plain", lambda: bench_sequential("hello-plain", HELLO, 10, snapshot=False)),
        ("numpy-sum-snapshot", lambda: bench_sequential("numpy-sum-snapshot", NUMPY, 5)),
        ("door-echo-20000x64B", lambda: bench_sequential("door-echo-20000x64B", DOOR_SMALL, 3, echo=True)),
        ("door-echo-500x1MiB", lambda: bench_sequential("door-echo-500x1MiB", DOOR_LARGE, 3, echo=True)),
        ("stdout-32MiB", lambda: bench_sequential("stdout-32MiB", STDOUT_32M, 3, output_bytes=64 << 20)),
        ("files-grant", lambda: bench_sequential("files-grant-20000stat-2000read", FILES, 3, grants=(("/ro", ro),))),
        ("files-mount", lambda: bench_mount("files-mount-20000stat-2000read", 3)),
        ("parallel-8-hello", lambda: bench_parallel("parallel-8-hello", HELLO, 8, 8)),
        ("cold-process-hello", lambda: bench_cold("cold-process-hello")),
    ]
    rows = [fn() for name, fn in plan if not only or name in only]
    dest = Path(__file__).parent / f"results-{label}.json"
    dest.write_text(json.dumps(dict(label=label, rust=str(RUST), wasmtime_py=wt.__version__ if hasattr(wt, "__version__") else "49.0.0", rows=rows), indent=1))
    print(f"wrote {dest}", file=sys.stderr)


if __name__ == "__main__":
    main()
