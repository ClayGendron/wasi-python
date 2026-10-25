"""Where do eight concurrent `wasi_python.run` calls wait on each other?

Arms: product (`wasi_python.run`) and bare (a minimal wasmtime-py embedding, as the speed spike's).
Modes (argv[1]):
  curve     speedup curves at 1, 2, 4, 8 threads for both arms (interleaved, 3 repeats, medians)
  timeline  8 hellos on 8 threads with per-thread phase stamps (wall + thread CPU) and lock accounting
  fix       8/8 with prototype fixes from FIXES=a,b,... (monkeypatched here; src/ untouched)
Every number is wall-clock on one machine: a benchmark fact for a memo, never a check.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path("/Users/claygendron/Git/Repos/wasi_python")
SET = REPO / "build/artifacts"
WORK = REPO / "build/concurrency-probe/work"
RESULTS = REPO / "build/concurrency-probe/results"
os.environ["WASI_PYTHON_ARTIFACTS"] = str(SET)
sys.path.insert(0, str(REPO / "tests"))

import wasmtime as wt  # noqa: E402

import wasi_python  # noqa: E402
from harness import guest  # noqa: E402
from wasi_python import _call, _engines, _home, _places, _private_dirs, _zip, _artifacts  # noqa: E402
from wasi_python._process import process  # noqa: E402

STDLIB = SET / "python-stdlib.zip"
BIN = SET / "python-snapshot.wasm"
ZNAME = guest.stdlib_name("3.15.0", STDLIB)
BASE_ENV = {"TMPDIR": "/tmp", "PYTHONTZPATH": ""}
MEMORY, DEADLINE, FUEL = 1 << 30, 60.0, 10**12
UNMETERED = 2**63 - 1
HELLO = "print('hello')"
CACHE_PY = REPO / "build/rust-spike-perf/work/cwasm-py"  # the spike's warm cache (same wasmtime)
CACHE_BARE = REPO / "build/rust-spike-perf/work/cwasm-bare"
LIB = WORK / "lib"


def stats(xs):
    xs = sorted(xs)
    return dict(n=len(xs), min=round(xs[0], 1), median=round(statistics.median(xs), 1), max=round(xs[-1], 1))


# --- arm: product -------------------------------------------------------------------------------

def product(code=HELLO):
    t = time.perf_counter()
    c = wasi_python.run(["-c", code], fuel=FUEL, deadline_s=DEADLINE, memory_bytes=MEMORY, cache_dir=CACHE_PY)
    ms = (time.perf_counter() - t) * 1e3
    if c.trapped or c.exit_code != 0:
        raise SystemExit(f"product: {c.trapped} {c.exit_code} {c.stderr[-300:]!r}")
    return ms


# --- arm: bare ----------------------------------------------------------------------------------

_bare_engine = None
_bare_module = None


def bare_engine():
    global _bare_engine
    if _bare_engine is None:
        cfg = wt.Config()
        cfg.consume_fuel = True
        cfg.epoch_interruption = True
        _bare_engine = wt.Engine(cfg)
    return _bare_engine


def bare_module():
    global _bare_module
    if _bare_module is None:
        CACHE_BARE.mkdir(parents=True, exist_ok=True)
        cw = CACHE_BARE / (BIN.stem + ".cwasm")
        if cw.is_file():
            _bare_module = wt.Module.deserialize_file(bare_engine(), str(cw))
        else:
            _bare_module = wt.Module.from_file(bare_engine(), str(BIN))
            cw.write_bytes(_bare_module.serialize())
    return _bare_module


def ensure_lib():
    LIB.mkdir(parents=True, exist_ok=True)
    z = LIB / ZNAME
    if not z.exists():
        os.link(STDLIB, z)
    return LIB


def bare(code=HELLO):
    io = WORK / f"bare-io-{threading.get_ident()}"
    io.mkdir(parents=True, exist_ok=True)
    engine, mod = bare_engine(), bare_module()
    t = time.perf_counter()
    store = wt.Store(engine)
    store.set_fuel(UNMETERED)
    store.set_epoch_deadline(2**40)
    store.set_limits(memory_size=MEMORY)
    wasi = wt.WasiConfig()
    wasi.argv = [guest.ARGV0, "-c", code]
    wasi.env = sorted(BASE_ENV.items())
    wasi.preopen_dir(str(ensure_lib()), "/usr/local/lib", False)
    wasi.stdout_file = str(io / "stdout")
    wasi.stderr_file = str(io / "stderr")
    store.set_wasi(wasi)
    linker = wt.Linker(engine)
    linker.define_wasi()
    i32 = wt.ValType.i32()
    linker.define_func("host", "call", wt.FuncType([i32] * 4, [i32]), lambda *a: -1, True)
    instance = linker.instantiate(store, mod)
    store.set_fuel(FUEL)
    exports = instance.exports(store)
    try:
        code_out = exports["run"](store)
    except wt.ExitTrap as e:
        code_out = e.code
    ms = (time.perf_counter() - t) * 1e3
    if code_out != 0:
        raise SystemExit(f"bare: exit {code_out} {(io / 'stderr').read_bytes()[-300:]!r}")
    return ms


# --- timing of a batch --------------------------------------------------------------------------

def batch(fn, n, workers):
    """n runs on `workers` threads: (wall ms, per-call ms list)."""
    per = []
    lock = threading.Lock()

    def one(_):
        ms = fn()
        with lock:
            per.append(ms)

    t = time.perf_counter()
    if workers == 1:
        for i in range(n):
            one(i)
    else:
        with ThreadPoolExecutor(workers) as ex:
            list(ex.map(one, range(n)))
    return (time.perf_counter() - t) * 1e3, per


def curve(repeats=3):
    rows = []
    for n in (1, 2, 4, 8):
        row = dict(n=n)
        seq = {"product": [], "bare": []}
        par = {"product": [], "bare": []}
        percall = {"product": [], "bare": []}
        for _ in range(repeats):
            for arm, fn in (("product", product), ("bare", bare)):  # interleaved: one window
                w, _ = batch(fn, n, 1)
                seq[arm].append(w)
                w, per = batch(fn, n, n)
                par[arm].append(w)
                percall[arm].extend(per)
        for arm in ("product", "bare"):
            row[arm] = dict(
                sequential=stats(seq[arm]), parallel=stats(par[arm]),
                speedup=round(statistics.median(seq[arm]) / statistics.median(par[arm]), 2),
                per_call_in_parallel=stats(percall[arm]),
            )
        print(json.dumps(row), file=sys.stderr, flush=True)
        rows.append(row)
    return rows


# --- the timeline and lock accounting ----------------------------------------------------------

EVENTS: list[dict] = []
EV_LOCK = threading.Lock()
T0 = [0.0]
RUN_OF_THREAD: dict[int, int] = {}
RUN_COUNTER = [0]


def _run_id():
    tid = threading.get_ident()
    return RUN_OF_THREAD.get(tid, -1)


def stamp(phase, t0, c0, extra=None):
    t1, c1 = time.perf_counter(), time.thread_time()
    ev = dict(run=_run_id(), tid=threading.get_ident() % 100000, phase=phase,
              t0=round((t0 - T0[0]) * 1e3, 3), t1=round((t1 - T0[0]) * 1e3, 3),
              wall=round((t1 - t0) * 1e3, 3), cpu=round((c1 - c0) * 1e3, 3))
    if extra:
        ev.update(extra)
    with EV_LOCK:
        EVENTS.append(ev)


def timed(module, name, phase):
    orig = getattr(module, name)

    def wrapper(*a, **k):
        t0, c0 = time.perf_counter(), time.thread_time()
        try:
            return orig(*a, **k)
        finally:
            stamp(phase, t0, c0)

    setattr(module, name, wrapper)
    return orig


class LockProbe:
    """A lock stand-in on the process object: counts acquisitions, the wait for each and the hold."""

    def __init__(self, name, inner):
        self.name, self.inner = name, inner
        self.count = 0
        self.wait = 0.0
        self.hold = 0.0
        self.max_hold = 0.0
        self.local = threading.local()

    def __enter__(self):
        t0 = time.perf_counter()
        self.inner.acquire()
        t1 = time.perf_counter()
        self.local.t = t1
        with EV_LOCK:
            self.count += 1
            self.wait += t1 - t0
        return self

    def __exit__(self, *exc):
        held = time.perf_counter() - self.local.t
        self.inner.release()
        with EV_LOCK:
            self.hold += held
            self.max_hold = max(self.max_hold, held)

    # `acquire`/`release` for code that calls them directly
    def acquire(self, *a, **k):
        return self.inner.acquire(*a, **k)

    def release(self):
        return self.inner.release()

    def report(self):
        return dict(name=self.name, count=self.count, wait_ms=round(self.wait * 1e3, 2),
                    hold_ms=round(self.hold * 1e3, 2), max_hold_ms=round(self.max_hold * 1e3, 3))


LOCKS = ("cache_lock", "held_lock", "zip_lock", "warnings_lock", "stack_size_lock",
         "outputs_lock", "epoch_callback_lock", "live_lock", "pool_lock", "tool_threads_lock")
PROBES: dict[str, LockProbe] = {}


def install_lock_probes():
    p = process()
    for name in LOCKS:
        PROBES[name] = LockProbe(name, getattr(p, name))
        setattr(p, name, PROBES[name])


def reset_probes():
    for pr in PROBES.values():
        pr.count, pr.wait, pr.hold, pr.max_hold = 0, 0.0, 0.0, 0.0


def install_timeline():
    timed(_artifacts, "_found_and_checked", "artifacts")
    timed(_places, "_walk_grants", "walk")
    timed(_engines, "_engine", "engine")
    timed(_engines, "_module", "module")
    timed(_engines, "_check_module", "check_module")
    timed(_call, "_preopens", "preopens")
    timed(_call, "_guest_home", "guest_home")
    timed(_zip, "_zip_folder", "zip")
    timed(_private_dirs, "_sweep_once", "sweep")
    timed(_places, "_check_preopens", "identity_check")
    timed(_home, "_start_guest", "thread_start")
    timed(_home, "_join_guest", "join")
    # The private folders: construction and removal.
    orig_private = _call._Private

    class TimedPrivate(orig_private):
        def __init__(self, prefix):
            t0, c0 = time.perf_counter(), time.thread_time()
            try:
                super().__init__(prefix)
            finally:
                stamp("private_make", t0, c0, dict(prefix=prefix))

        def remove(self):
            t0, c0 = time.perf_counter(), time.thread_time()
            try:
                super().remove()
            finally:
                stamp("private_remove", t0, c0, dict(prefix=self.name[:17]))

    _call._Private = TimedPrivate
    _zip._Private = TimedPrivate
    # wasmtime's own: instantiate and the wasm calls (the guest thread).
    orig_inst = wt.Linker.instantiate

    def inst(self, store, module):
        t0, c0 = time.perf_counter(), time.thread_time()
        try:
            return orig_inst(self, store, module)
        finally:
            stamp("instantiate", t0, c0)

    wt.Linker.instantiate = inst
    orig_fcall = wt.Func.__call__

    def fcall(self, *a, **k):
        t0, c0 = time.perf_counter(), time.thread_time()
        try:
            return orig_fcall(self, *a, **k)
        finally:
            stamp("wasm_call", t0, c0)

    wt.Func.__call__ = fcall
    orig_close = wt.Store.close

    def sclose(self):
        t0, c0 = time.perf_counter(), time.thread_time()
        try:
            return orig_close(self)
        finally:
            stamp("store_close", t0, c0)

    wt.Store.close = sclose
    # The home's finish steps (the releases), the body (guest thread total) and serve.
    orig_finish = _home._Home.finish

    def finish(self, step):
        def timed_step():
            t0, c0 = time.perf_counter(), time.thread_time()
            try:
                return step()
            finally:
                stamp("release_step", t0, c0)
        return orig_finish(self, timed_step)

    _home._Home.finish = finish
    orig_body = _home._Home.body

    def body(self, kind, fn, args):
        RUN_OF_THREAD[threading.get_ident()] = RUN_OF_THREAD.get(self.ident, -1)
        t0, c0 = time.perf_counter(), time.thread_time()
        try:
            return orig_body(self, kind, fn, args)
        finally:
            stamp("guest_body", t0, c0)

    _home._Home.body = body
    timed(_home._Home, "serve", "serve")
    # Thread.start itself (inside the stack-size window).
    orig_start = threading.Thread.start

    def tstart(self):
        t0, c0 = time.perf_counter(), time.thread_time()
        try:
            return orig_start(self)
        finally:
            if self.name == "wasi-python-guest":
                stamp("Thread.start", t0, c0)

    threading.Thread.start = tstart
    # the whole call
    orig_run = wasi_python.run

    def run(*a, **k):
        with EV_LOCK:
            RUN_COUNTER[0] += 1
            RUN_OF_THREAD[threading.get_ident()] = RUN_COUNTER[0]
        t0, c0 = time.perf_counter(), time.thread_time()
        try:
            return orig_run(*a, **k)
        finally:
            stamp("run", t0, c0)

    wasi_python.run = run


def timeline(n=8, workers=8, repeats=3):
    install_lock_probes()
    install_timeline()
    product()  # warm
    out = dict(sequential=[], parallel=[], locks_sequential=None, locks_parallel=None, events_parallel=None, events_sequential=None)
    for r in range(repeats):
        EVENTS.clear(); reset_probes(); T0[0] = time.perf_counter()
        w, _ = batch(product, n, 1)
        out["sequential"].append(w)
        if r == repeats - 1:
            out["locks_sequential"] = [p.report() for p in PROBES.values()]
            out["events_sequential"] = list(EVENTS)
        EVENTS.clear(); reset_probes(); T0[0] = time.perf_counter()
        w, _ = batch(product, n, workers)
        out["parallel"].append(w)
        if r == repeats - 1:
            out["locks_parallel"] = [p.report() for p in PROBES.values()]
            out["events_parallel"] = list(EVENTS)
    out["speedup"] = round(statistics.median(out["sequential"]) / statistics.median(out["parallel"]), 2)
    return out


def summarize(events):
    """Per phase: count, total wall, total cpu, mean wall (ms)."""
    by = {}
    for e in events:
        d = by.setdefault(e["phase"], dict(count=0, wall=0.0, cpu=0.0))
        d["count"] += 1; d["wall"] += e["wall"]; d["cpu"] += e["cpu"]
    return {k: dict(count=v["count"], wall_ms=round(v["wall"], 1), cpu_ms=round(v["cpu"], 1),
                    mean_wall_ms=round(v["wall"] / v["count"], 2)) for k, v in sorted(by.items())}



# --- prototype fixes (monkeypatched toggles; src/ untouched) --------------------------------------

import contextvars
import stat as _stat

ORIG = dict(
    start_guest=_home._start_guest, Private=_call._Private, sweep=_private_dirs._sweep_once,
    check_preopens=_places._check_preopens, zip_folder=_zip._zip_folder, data_intact=_zip._data_intact,
    ticker_call=_call._epoch_ticker, ticker_home=_home._epoch_ticker, walk_grants=_places._walk_grants,
)


def _start_guest_no_lock(home, kind, fn, args):
    """The guest thread started without the process-wide stack-size window (the size is set once
    for the batch). Sizes the window's cost; a pool of pre-sized threads would be the real shape."""
    context = contextvars.copy_context()
    thread = threading.Thread(target=context.run, args=(home.body, kind, fn, args), name="wasi-python-guest")
    with home.lock:
        home._move(_home._HomeEvent.START)
        home.thread = thread
        home.ended.clear()
    thread.start()


def _zip_folder_outside(found, want=None):
    """The zip folder's per-call checks (the zip's stamp, the whole mpl-data tree) read the
    filesystem only; here they run outside `zip_lock`. The original locked path, which checks
    again, is taken only to make or repair. Every call still checks the whole tree before granting."""
    want = want if want is not None else _artifacts._digest(found.stdlib_zip)
    name = f"python{_artifacts._version_tag(found.manifest)}.zip"
    p = process()
    with p.zip_lock:
        entry = p.zips.get(want)
        if entry is None:
            return _zip._zip_folder_locked(found, want, name)
        private, stamp, record = entry
    ok = os.path.isdir(private.path) and not os.path.islink(private.path)
    lib = private.path / "lib"
    dest = lib / name
    try:
        st = os.lstat(dest) if ok and os.path.isdir(lib) and not os.path.islink(lib) else None
    except FileNotFoundError:
        st = None
    ok = ok and st is not None and _stat.S_ISREG(st.st_mode) and _artifacts._stamp(st) == stamp
    data = private.path / "mpl-data"
    if ok and (record is None or _zip._data_intact(data, record)):
        return _zip._ZipFolder(lib, None if record is None else data, name)
    return ORIG["zip_folder"](found, want)


def _data_intact_scandir(data, record):
    """The same check (every name, each a real folder or regular file as recorded, no link, each
    file's stamp equal) by os.scandir and plain strings instead of os.walk and pathlib."""
    if os.path.islink(data) or not os.path.isdir(data):
        return False
    seen = {}
    base = os.fspath(data)
    try:
        todo = [""]
        while todo:
            rel = todo.pop()
            with os.scandir(os.path.join(base, rel) if rel else base) as it:
                for e in it:
                    st = e.stat(follow_symlinks=False)
                    key = f"{rel}/{e.name}" if rel else e.name
                    if _stat.S_ISDIR(st.st_mode):
                        seen[key] = None
                        todo.append(key)
                    elif _stat.S_ISREG(st.st_mode):
                        seen[key] = _artifacts._stamp(st)
                    else:
                        return False
    except OSError:
        return False
    return seen == record


class _NoTicker:
    def __init__(self, engine, wanted): pass
    @classmethod
    def count(cls): return 0
    def __enter__(self): return None
    def __exit__(self, *a): return None


class _PlainPrivate:
    """Sizing only, never a proposal: a private folder without its lock file (it weakens the sweep)."""
    def __init__(self, prefix):
        import tempfile
        self.path = Path(tempfile.mkdtemp(prefix=prefix))
        self.name = self.path.name
    def remove(self):
        import shutil
        shutil.rmtree(self.path, ignore_errors=True)


def set_fixes(names, on):
    """Apply (on) or undo (off) each named fix."""
    if "no_stack_lock" in names:
        threading.stack_size(_home._THREAD_STACK if on else 0)
        _home._start_guest = _start_guest_no_lock if on else ORIG["start_guest"]
    if "zip_outside" in names:
        _zip._zip_folder = _zip_folder_outside if on else ORIG["zip_folder"]
    if "data_scandir" in names:
        _zip._data_intact = _data_intact_scandir if on else ORIG["data_intact"]
    if "no_ticker" in names:
        _call._epoch_ticker = _NoTicker if on else ORIG["ticker_call"]
        _home._epoch_ticker = _NoTicker if on else ORIG["ticker_home"]
    if "no_private" in names:  # sizing only
        _call._Private = _PlainPrivate if on else ORIG["Private"]
    if "no_identity_check" in names:  # sizing only
        _places._check_preopens = (lambda *a, **k: None) if on else ORIG["check_preopens"]
    if "no_data_check" in names:  # sizing only
        _zip._data_intact = (lambda d, r: True) if on else ORIG["data_intact"]
    if "switch_fast" in names:  # informative only: the embedder owns the interpreter's switch interval
        sys.setswitchinterval(0.0001 if on else 0.005)
    if "switch_slow" in names:
        sys.setswitchinterval(0.05 if on else 0.005)
    if "no_walk_judge" in names:  # sizing only
        _places._walk_grants = (lambda *a, **k: (None, [])) if on else ORIG["walk_grants"]


def paired(names, repeats=3, n=8, workers=8):
    """Baseline and fixed, alternated in one window; bare beside them for the window's scale."""
    base_seq, base_par, fix_seq, fix_par, bseq, bpar = [], [], [], [], [], []
    for _ in range(repeats):
        set_fixes(names, False)
        base_seq.append(batch(product, n, 1)[0]); base_par.append(batch(product, n, workers)[0])
        set_fixes(names, True)
        fix_seq.append(batch(product, n, 1)[0]); fix_par.append(batch(product, n, workers)[0])
        set_fixes(names, False)
        bseq.append(batch(bare, n, 1)[0]); bpar.append(batch(bare, n, workers)[0])
    med = statistics.median
    return dict(
        fixes=names, n=n, workers=workers,
        baseline=dict(sequential=stats(base_seq), parallel=stats(base_par), speedup=round(med(base_seq) / med(base_par), 2)),
        fixed=dict(sequential=stats(fix_seq), parallel=stats(fix_par), speedup=round(med(fix_seq) / med(fix_par), 2)),
        bare=dict(sequential=stats(bseq), parallel=stats(bpar), speedup=round(med(bseq) / med(bpar), 2)),
    )


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "curve"
    WORK.mkdir(parents=True, exist_ok=True)
    label = os.environ.get("LABEL", mode)
    product(); bare()  # warm both arms (modules into memory)
    if mode == "curve":
        out = dict(mode=mode, rows=curve())
    elif mode == "timeline":
        out = dict(mode=mode, **timeline())
        out["summary_parallel"] = summarize(out["events_parallel"])
        out["summary_sequential"] = summarize(out["events_sequential"])
        print(json.dumps(dict(sequential=out["sequential"], parallel=out["parallel"], speedup=out["speedup"])), file=sys.stderr)
    elif mode == "fix":
        names = [f for f in os.environ.get("FIXES", "").split(",") if f]
        out = dict(mode=mode, **paired(names))
        b, f, r = out["baseline"], out["fixed"], out["bare"]
        print(f"{names}: baseline {b['sequential']['median']}/{b['parallel']['median']} = {b['speedup']}x | "
              f"fixed {f['sequential']['median']}/{f['parallel']['median']} = {f['speedup']}x | "
              f"bare {r['sequential']['median']}/{r['parallel']['median']} = {r['speedup']}x", file=sys.stderr)
    else:
        raise SystemExit(f"unknown mode {mode}")
    out["load_1m"] = os.getloadavg()[0]
    dest = RESULTS / f"{label}.json"
    dest.write_text(json.dumps(out, indent=1))
    print(f"wrote {dest}", file=sys.stderr)
    sys.stdout.flush()
    process().remove_zips()  # this process's zip folder; the 4.4 s module drop at exit is not this memo's subject
    os._exit(0)




# --- operations per call: the os-level calls the runner's Python makes, by name ------------------

def count_ops(fn, n=8):
    """Wrap every os function the runner reaches through the module and count calls per `fn`."""
    names = [k for k, v in vars(os).items() if callable(v) and not k.startswith("_") and k not in ("fspath", "fsencode", "fsdecode", "getpid", "getuid", "getloadavg", "urandom", "cpu_count", "get_terminal_size")]
    counts = {}
    saved = {}
    for name in names:
        orig = getattr(os, name)
        saved[name] = orig
        def make(name, orig):
            def w(*a, **k):
                counts[name] = counts.get(name, 0) + 1
                return orig(*a, **k)
            return w
        try:
            setattr(os, name, make(name, orig))
        except (AttributeError, TypeError):
            saved.pop(name)
    try:
        for _ in range(n):
            fn()
    finally:
        for name, orig in saved.items():
            setattr(os, name, orig)
    per = {k: round(v / n, 1) for k, v in sorted(counts.items(), key=lambda kv: -kv[1]) if v / n >= 0.5}
    return dict(total_per_call=round(sum(counts.values()) / n, 1), by_name=per)


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "ops":
    WORK.mkdir(parents=True, exist_ok=True)
    product(); bare()
    out = dict(mode="ops", product=count_ops(product), bare=count_ops(bare))
    set_fixes(["data_scandir"], True)
    out["product_with_scandir_check"] = count_ops(product)
    set_fixes(["data_scandir"], False)
    print(json.dumps(out, indent=1), file=sys.stderr)
    (RESULTS / "ops.json").write_text(json.dumps(out, indent=1))
    sys.stdout.flush(); process().remove_zips(); os._exit(0)


if __name__ == "__main__":
    main()
