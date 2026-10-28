"""Design (b): a run-time memory image through wasmtime-py's public API.

Suites (results/<suite>.json):
  sizes        each prelude: fuel, image pages and MiB, pages changed from a fresh instance, compressed
               sizes, and the per-call restore cost over several restored calls
  correctness  a prelude that leaves live objects; restored calls use them; nothing a call does
               reaches the next; outputs compared with a fresh instance running the same sequence
  randomness   which states differ between two restored calls, with and without the per-call refresh
  preopens     the guest's preopen table is part of the image
  sp           the stack pointer (the module's one mutable global) read through an instrumented copy
  disk         the image saved and loaded: sizes, read, decompress and mmap costs
  fds          a prelude that leaves a file open

Run from this folder: uv run --no-sync python harness/image.py <suite> [...]
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import mmap
import os
import statistics
import sys
import time
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bare  # noqa: E402
from preludes import PRELUDES  # noqa: E402

RESULTS = Path(__file__).parents[1] / "results"
PAGE = bare.PAGE
HOME = "/tmp/.home"

# Publishes the prelude's own names into every later call's fresh __main__, collects, and freezes
# what the prelude left out of the collector's way, as the build-time snapshot freezes its bootstrap.
SEAL = (
    "(__import__('_reactor')._MAIN_NAMES.update({k: v for k, v in vars(__import__('__main__')).items() "
    "if not k.startswith('__')}), __import__('gc').collect(), __import__('gc').freeze()) and None"
)


def call_env(extra=None):
    return {**bare.BASE_ENV, "HOME": HOME, **(extra or {})}


def driver(program: str, env: dict) -> str:
    """One run() inside a turn: the reactor's own argument handling, environment and refresh."""
    argv = [bare.ARGV0, "-c", program]
    return f"raise SystemExit(__import__('_reactor').run({argv!r}, {env!r}))"


def make_image(engine, module, prelude, seal=True, extra_dirs=(), env=None):
    g = bare.Guest(engine, module, env=env, extra_dirs=extra_dirs, tag="make")
    try:
        base = g.capture()
        bare.set_phase("prelude")
        r = g.turn(prelude)
        s = g.turn(SEAL) if seal else None
        image = g.capture()
        return image, base, {"prelude": {k: r[k] for k in ("status", "trapped", "fuel", "s")}, "prelude_stderr": r["stderr"][-600:],
                             "seal": None if s is None else {k: s[k] for k in ("status", "fuel", "s")}}
    finally:
        g.close()


def changed_runs(image: bytes, base: bytes):
    """Runs of 64 KiB pages where the image differs from a fresh instance's memory (or lies past it)."""
    runs, start = [], None
    n = len(image) // PAGE
    for i in range(n):
        a = image[i * PAGE : (i + 1) * PAGE]
        differs = i * PAGE >= len(base) or a != base[i * PAGE : (i + 1) * PAGE]
        if differs and start is None:
            start = i
        elif not differs and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, n))
    return runs


def nonzero_pages(image: bytes) -> int:
    z = bytes(PAGE)
    return sum(1 for i in range(len(image) // PAGE) if image[i * PAGE : (i + 1) * PAGE] != z)


def restored_call(engine, module, image, program, env=None, how="memmove", runs=None, shutdown=True, extra_dirs=(), raw_turn=False):
    t0 = time.perf_counter()
    g = bare.Guest(engine, module, extra_dirs=extra_dirs, tag="call")
    t1 = time.perf_counter()
    try:
        if runs is None:
            rest = g.restore(image, how)
        else:  # only the pages that differ from a fresh instance
            want = len(image) // PAGE
            if want > g.pages():
                g.memory.grow(g.store, want - g.pages())
            c0 = time.perf_counter()
            dst = g.memory.data_ptr(g.store)
            dst_addr = ctypes.addressof(dst.contents)
            src = (ctypes.c_char * len(image)).from_buffer_copy(image) if isinstance(image, bytes) else image
            src_addr = ctypes.addressof(src)
            for a, b in runs:
                ctypes.memmove(dst_addr + a * PAGE, src_addr + a * PAGE, (b - a) * PAGE)
            rest = {"copy_s": time.perf_counter() - c0, "pages": want, "copied_pages": sum(b - a for a, b in runs)}
        t2 = time.perf_counter()
        bare.set_phase("call")
        code = program if raw_turn else driver(program, call_env(env))
        r = g.turn(code)
        t3 = time.perf_counter()
        sd = g.shutdown() if shutdown else None
        t4 = time.perf_counter()
        return {
            "instantiate_s": g.instantiate_s, "guest_setup_s": t1 - t0, "restore": rest, "restore_s": t2 - t1,
            "turn": {k: r[k] for k in ("status", "trapped", "fuel", "s")}, "stdout": r["stdout"], "stderr": r["stderr"][-1500:],
            "shutdown": None if sd is None else {k: sd[k] for k in ("status", "fuel", "s")}, "shutdown_stdout": None if sd is None else sd["stdout"],
            "total_s": t4 - t0, "turn_s": t3 - t2,
        }
    finally:
        g.close()


def fresh_sequence(engine, module, prelude, program, env=None, extra_dirs=()):
    """The same sequence with no image: prelude, seal and the program in one fresh instance."""
    g = bare.Guest(engine, module, extra_dirs=extra_dirs, tag="fresh")
    try:
        p = g.turn(prelude)
        g.turn(SEAL)
        r = g.turn(driver(program, call_env(env)))
        sd = g.shutdown()
        return {"prelude_fuel": p["fuel"], "prelude_s": p["s"], "turn": {k: r[k] for k in ("status", "fuel", "s")}, "stdout": r["stdout"], "stderr": r["stderr"][-1500:], "shutdown": {k: sd[k] for k in ("status", "fuel", "s")}}
    finally:
        g.close()


def plain_call(engine, module, program, env=None):
    """No image: a fresh snapshot instance running the program the same way (the baseline restore adds to)."""
    g = bare.Guest(engine, module, tag="plain")
    try:
        t0 = time.perf_counter()
        r = g.turn(driver(program, call_env(env)))
        sd = g.shutdown()
        return {"instantiate_s": g.instantiate_s, "turn": {k: r[k] for k in ("status", "fuel", "s")}, "shutdown_fuel": sd["fuel"], "s": time.perf_counter() - t0, "stdout": r["stdout"]}
    finally:
        g.close()


def med(xs):
    return round(statistics.median(xs) * 1000, 2)


# --- suites ---------------------------------------------------------------------------------

def suite_sizes(engine, module, names, repeats=5):
    out = {}
    program = "import sys; print(len(sys.modules))"
    for name in names:
        image, base, made = make_image(engine, module, PRELUDES[name])
        runs = changed_runs(image, base)
        t = time.perf_counter()
        z1 = zlib.compress(image, 1)
        z1_s = time.perf_counter() - t
        try:
            from compression import zstd

            t = time.perf_counter()
            zs = zstd.compress(image, 3)
            zs_s = time.perf_counter() - t
            t = time.perf_counter()
            zstd.decompress(zs)
            zsd_s = time.perf_counter() - t
            zstd_info = {"bytes": len(zs), "compress_ms": round(zs_s * 1000, 1), "decompress_ms": round(zsd_s * 1000, 1)}
        except ImportError:
            zstd_info = None
        delta = b"".join(image[a * PAGE : b * PAGE] for a, b in runs)
        calls = [restored_call(engine, module, image, program) for _ in range(repeats)]
        dcalls = [restored_call(engine, module, image, program, runs=runs, shutdown=False) for _ in range(repeats)]
        wcalls = [restored_call(engine, module, image, program, how="write", shutdown=False) for _ in range(2)]
        plain = [plain_call(engine, module, program) for _ in range(repeats)]
        out[name] = {
            **made,
            "pages": len(image) // PAGE,
            "MiB": round(len(image) / 2**20, 1),
            "nonzero_pages": nonzero_pages(image),
            "changed_pages": sum(b - a for a, b in runs),
            "changed_runs": len(runs),
            "changed_MiB": round(len(delta) / 2**20, 1),
            "zlib1_MiB": round(len(z1) / 2**20, 1),
            "zlib1_compress_ms": round(z1_s * 1000, 1),
            "zstd3": None if zstd_info is None else {**zstd_info, "MiB": round(zstd_info["bytes"] / 2**20, 1)},
            "zstd3_delta_MiB": None if zstd_info is None else round(len(zstd.compress(delta, 3)) / 2**20, 1),
            "restore_full_memmove_ms": med([c["restore_s"] for c in calls]),
            "copy_full_memmove_ms": med([c["restore"]["copy_s"] for c in calls]),
            "grow_ms": med([c["restore"]["grow_s"] for c in calls]),
            "restore_delta_ms": med([c["restore_s"] for c in dcalls]),
            "restore_memory_write_ms": med([c["restore_s"] for c in wcalls]),
            "instantiate_ms": med([c["instantiate_s"] for c in calls]),
            "program_turn_ms": med([c["turn_s"] for c in calls]),
            "program_fuel": calls[0]["turn"]["fuel"],
            "shutdown_ms": med([c["shutdown"]["s"] for c in calls]),
            "shutdown_fuel": calls[0]["shutdown"]["fuel"],
            "call_total_ms": med([c["total_s"] for c in calls]),
            "call_total_delta_no_shutdown_ms": med([c["total_s"] for c in dcalls]),
            "program_stdout": calls[0]["stdout"].strip(),
            "plain_call_ms": med([p["s"] + p["instantiate_s"] for p in plain]),
            "plain_program_fuel": plain[0]["turn"]["fuel"],
            "plain_shutdown_fuel": plain[0]["shutdown_fuel"],
            "all_status": sorted({str(c["turn"]["status"]) for c in calls + dcalls + wcalls}),
        }
        print(name, json.dumps({k: v for k, v in out[name].items() if k not in ("prelude_stderr",)}), flush=True)
    return out


OBJECTS_PRELUDE = '''
import numpy as np, pandas as pd, time
from sklearn.tree import DecisionTreeClassifier
from sklearn.datasets import load_iris
sales = pd.read_csv("/data/sales.csv")
iris = load_iris(as_frame=True)
df = iris.frame
model = DecisionTreeClassifier(random_state=0).fit(iris.data, iris.target)
def summarize(frame):
    return frame.groupby("target").mean().round(3)
counter = [0]
'''

USE = '''
import sys, builtins, numpy
print(summarize(df).to_csv(), end="")
print(model.predict(df.iloc[[0, 50, 100], :4]).tolist())
print(sales.groupby("region")["amount"].sum().to_dict())
print("counter", len(counter), "extra" in df.columns, numpy.sum is None, "pandas" in sys.modules, hasattr(builtins, "LEAK"))
counter.append(1)
df["extra"] = 1
numpy.sum = None
sys.modules.pop("pandas")
builtins.LEAK = 1
open("/left-by-call.txt", "w").write("x")
'''


def data_dir():
    d = bare.WORK / "data"
    d.mkdir(parents=True, exist_ok=True)
    (d / "sales.csv").write_text("region,amount\nnorth,10\nsouth,5\nnorth,7\n")
    (d / "hello.txt").write_text("from the prelude's data folder\n")
    return d


def suite_correctness(engine, module):
    d = data_dir()
    dirs = [(d, "/data")]
    image, base, made = make_image(engine, module, OBJECTS_PRELUDE, extra_dirs=dirs)
    a = restored_call(engine, module, image, USE, extra_dirs=dirs)
    b = restored_call(engine, module, image, USE, extra_dirs=dirs)
    no_data = restored_call(engine, module, image, USE)  # the data folder not granted to the call
    f = fresh_sequence(engine, module, OBJECTS_PRELUDE, USE, extra_dirs=dirs)
    res = {"made": made, "pages": len(image) // PAGE, "restored_a": a, "restored_b": b, "restored_without_data_grant": no_data, "fresh": f,
           "a_equals_fresh": a["stdout"] == f["stdout"], "a_equals_b": a["stdout"] == b["stdout"]}
    print(json.dumps({k: res[k] for k in ("a_equals_fresh", "a_equals_b", "pages")}), a["stdout"], a["stderr"], f["stdout"], no_data["stdout"], no_data["stderr"][-300:], sep="\n---\n")
    return res


RANDOM_PRELUDE = '''
import random, numpy as np, numpy.random, tempfile, time, sympy, json
next(tempfile._get_candidate_names())
t0_mono = time.monotonic()
t0_wall = time.time()
'''

RANDOM_PROGRAM = '''
import random, numpy as np, tempfile, uuid, time, os, sys, json
out = {
    "random": random.random(),
    "np_legacy": float(np.random.random()),
    "np_default_rng": float(np.random.default_rng().random()),
    "sympy_rng": sys.modules["sympy.core.random"].rng.random(),
    "tempfile_name": next(tempfile._get_candidate_names()),
    "uuid4": str(uuid.uuid4())[:8],
    "urandom": os.urandom(4).hex(),
    "hash_abc": hash("abc"),
    "monotonic_minus_prelude_s": round(time.monotonic() - t0_mono, 3),
    "monotonic_now_s": round(time.monotonic(), 3),
    "wall_minus_prelude_s": round(time.time() - t0_wall, 3),
    "env_SPIKE_X": os.environ.get("SPIKE_X"),
}
print(json.dumps(out))
'''


def suite_randomness(engine, module):
    image, base, made = make_image(engine, module, RANDOM_PRELUDE)
    calls = [restored_call(engine, module, image, RANDOM_PROGRAM, env={"SPIKE_X": str(i)}) for i in range(2)]
    raw = [restored_call(engine, module, image, RANDOM_PROGRAM, raw_turn=True, shutdown=False) for _ in range(2)]
    rows = [json.loads(c["stdout"].strip().splitlines()[-1]) if c["stdout"].strip() else c["stderr"] for c in calls + raw]
    same_refreshed = {k: rows[0][k] == rows[1][k] for k in rows[0]} if isinstance(rows[0], dict) and isinstance(rows[1], dict) else None
    same_raw = {k: rows[2][k] == rows[3][k] for k in rows[2]} if isinstance(rows[2], dict) and isinstance(rows[3], dict) else None
    res = {"made": made, "refreshed_calls": rows[:2], "raw_turn_calls": rows[2:], "equal_between_refreshed_calls": same_refreshed, "equal_between_raw_turns": same_raw}
    print(json.dumps(res, indent=1))
    return res


def suite_preopens(engine, module):
    d = data_dir()
    other = bare.WORK / "other"
    other.mkdir(exist_ok=True)
    (other / "hello.txt").write_text("from a different folder the call granted at /other\n")
    image, base, made = make_image(engine, module, "open('/data/hello.txt').read()", extra_dirs=[(d, "/data")])
    prog = (
        "import os\n"
        "for p in ('/data/hello.txt', '/other/hello.txt'):\n"
        "    try:\n        print(p, '->', open(p).read().strip())\n"
        "    except OSError as e:\n        print(p, '->', type(e).__name__, e.errno)\n"
    )
    same = restored_call(engine, module, image, prog, extra_dirs=[(d, "/data")])
    swapped = restored_call(engine, module, image, prog, extra_dirs=[(other, "/other")])
    fresh = plain_call(engine, module, prog)
    added = restored_call(engine, module, image, prog, extra_dirs=[(d, "/data"), (other, "/other")])
    res = {"same_layout": same["stdout"], "other_folder_same_slot": swapped["stdout"], "image_layout_plus_one_more_grant": added["stdout"], "stderr": swapped["stderr"], "plain_call_no_grants": fresh["stdout"]}
    print(json.dumps(res, indent=1))
    return res


def suite_fds(engine, module):
    d = data_dir()
    image, base, made = make_image(engine, module, "kept = open('/data/sales.csv')\nkept.readline()", extra_dirs=[(d, "/data")])
    prog = (
        "import os\n"
        "fds=[]\n"
        "for fd in range(64):\n"
        "    try:\n        os.fstat(fd); fds.append(fd)\n"
        "    except OSError: pass\n"
        "print('open fds', fds)\n"
        "try:\n    print('kept reads', repr(kept.readline()))\n"
        "except OSError as e:\n    print('kept', type(e).__name__, e.errno)\n"
        "print('kept fd', kept.fileno())\n"
        "f = open('/new.txt', 'w+'); print('new file fd', f.fileno()); f.write('written by this call'); f.flush()\n"
        "try:\n    kept.seek(0); print('kept now reads', repr(kept.read()))\n"
        "except OSError as e:\n    print('kept after', type(e).__name__, e.errno)\n"
    )
    r = restored_call(engine, module, image, prog, extra_dirs=[(d, "/data")])
    print(r["stdout"], r["stderr"][-500:])
    return {"stdout": r["stdout"], "stderr": r["stderr"], "shutdown": r["shutdown"]}


def suite_sp(engine, _module):
    from wasm_sections import with_global_exported

    src = Path(os.environ["WASI_PYTHON_ARTIFACTS"]) / "python-snapshot.wasm"
    dst = bare.WORK / "python-snapshot-sp.wasm"
    if not dst.exists():
        dst.write_bytes(with_global_exported(src.read_bytes(), 0, "spike.sp"))
    _, mod, compile_s = bare.engine_and_module(dst)
    g = bare.Guest(engine, mod, tag="sp")
    sp = lambda: g.exports["spike.sp"].value(g.store)  # noqa: E731
    seen = {"compile_or_load_s": round(compile_s, 1), "after_instantiate": sp()}
    g.turn(PRELUDES["pandas"])
    seen["after_prelude_turn"] = sp()
    g.turn(SEAL)
    seen["after_seal_turn"] = sp()
    image = g.capture()
    g.turn("def f(n):\n    return 0 if n == 0 else 1 + f(n - 1)\nf(500)")
    seen["after_recursive_turn"] = sp()
    g.close()
    h = bare.Guest(engine, mod, tag="sp2")
    h.restore(image)
    seen["restored_before_turn"] = h.exports["spike.sp"].value(h.store)
    r = h.turn(driver("import pandas; print(pandas.__version__)", call_env()))
    seen["restored_after_turn"] = h.exports["spike.sp"].value(h.store)
    seen["restored_output"] = r["stdout"].strip()
    h.close()
    print(seen)
    return seen


def suite_disk(engine, module, name="everything", repeats=5):
    image, base, made = make_image(engine, module, PRELUDES[name])
    runs = changed_runs(image, base)
    path = bare.WORK / f"image-{name}.raw"
    path.write_bytes(image)
    res = {"prelude": name, "MiB": round(len(image) / 2**20, 1), "sha256_ms": None}
    t = time.perf_counter()
    hashlib.sha256(image).hexdigest()
    res["sha256_ms"] = round((time.perf_counter() - t) * 1000, 1)
    reads, maps, zreads = [], [], []
    from compression import zstd

    zpath = bare.WORK / f"image-{name}.zst"
    zpath.write_bytes(zstd.compress(image, 3))
    res["zstd3_file_MiB"] = round(zpath.stat().st_size / 2**20, 1)
    for _ in range(repeats):
        t = time.perf_counter()
        data = path.read_bytes()
        reads.append(time.perf_counter() - t)
        t = time.perf_counter()
        zstd.decompress(zpath.read_bytes())
        zreads.append(time.perf_counter() - t)
    for _ in range(repeats):
        with open(path, "rb") as fh:
            mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
            t = time.perf_counter()
            c = restored_call(engine, module, _MmapBuf(mm), "import sys; print(len(sys.modules))")
            maps.append(c["restore"]["copy_s"])
            mm.close()
    mem = [restored_call(engine, module, image, "import sys; print(len(sys.modules))")["restore"]["copy_s"] for _ in range(repeats)]
    res.update({"read_raw_ms": med(reads), "read_and_zstd_decompress_ms": med(zreads), "copy_from_mmap_ms": med(maps), "copy_from_bytes_ms": med(mem),
                "changed_pages": sum(b - a for a, b in runs)})
    print(res)
    return res


class _MmapBuf:
    """A read-only mmap handed to memmove by address (ctypes cannot from_buffer a read-only map)."""

    def __init__(self, mm):
        self.mm = mm
        self.view = memoryview(mm)

    def __len__(self):
        return len(self.mm)


def _restore_any(self, image, how="memmove"):
    t0 = time.perf_counter()
    want = len(image) // PAGE
    if want > self.pages():
        self.memory.grow(self.store, want - self.pages())
    t1 = time.perf_counter()
    dst = self.memory.data_ptr(self.store)
    if isinstance(image, _MmapBuf):
        import _ctypes  # noqa: F401

        buf = ctypes.c_char.from_buffer_copy  # placeholder to keep the type checker quiet
        addr = _address_of_readonly(image.view)
        ctypes.memmove(dst, addr, len(image))
    elif how == "write":
        self.memory.write(self.store, image, 0)
    else:
        ctypes.memmove(dst, image, len(image))
    return {"grow_s": t1 - t0, "copy_s": time.perf_counter() - t1, "pages": want}


def _address_of_readonly(view: memoryview) -> int:
    # The buffer protocol's pointer through a ctypes call on the object: PyObject_GetBuffer.
    class Py_buffer(ctypes.Structure):
        _fields_ = [("buf", ctypes.c_void_p), ("obj", ctypes.py_object), ("len", ctypes.c_ssize_t), ("itemsize", ctypes.c_ssize_t),
                    ("readonly", ctypes.c_int), ("ndim", ctypes.c_int), ("format", ctypes.c_char_p), ("shape", ctypes.c_void_p),
                    ("strides", ctypes.c_void_p), ("suboffsets", ctypes.c_void_p), ("internal", ctypes.c_void_p)]

    b = Py_buffer()
    ctypes.pythonapi.PyObject_GetBuffer(ctypes.py_object(view), ctypes.byref(b), 0)
    addr = b.buf
    ctypes.pythonapi.PyBuffer_Release(ctypes.byref(b))
    return addr


bare.Guest.restore = _restore_any


def main(argv):
    engine, module, _ = bare.engine_and_module()
    suite = argv[0]
    if suite == "sizes":
        res = suite_sizes(engine, module, argv[1:] or list(PRELUDES))
        name = "sizes" if not argv[1:] else "sizes-" + "-".join(argv[1:])
    else:
        res = globals()[f"suite_{suite}"](engine, module)
        name = suite
    (RESULTS / f"{name}.json").write_text(json.dumps(res, indent=1))



def suite_restorecost(engine, module, name="everything", rounds=12):
    """Repeated restores of one image, alternating the source, with the page faults each took."""
    import resource

    image, base, made = make_image(engine, module, PRELUDES[name])
    runs = changed_runs(image, base)
    path = bare.WORK / f"image-{name}.raw"
    path.write_bytes(image)
    fh = open(path, "rb")
    mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
    rows = {"bytes": [], "mmap": [], "delta": [], "host_memcpy": []}
    for _ in range(rounds):
        for kind in ("bytes", "mmap", "delta"):
            g = bare.Guest(engine, module, tag="rc")
            try:
                f0 = resource.getrusage(resource.RUSAGE_SELF).ru_minflt
                if kind == "delta":
                    want = len(image) // PAGE
                    g.memory.grow(g.store, want - g.pages())
                    c0 = time.perf_counter()
                    dst = ctypes.addressof(g.memory.data_ptr(g.store).contents)
                    src = _address_of_readonly(memoryview(image))
                    for a, b in runs:
                        ctypes.memmove(dst + a * PAGE, src + a * PAGE, (b - a) * PAGE)
                    copy = time.perf_counter() - c0
                else:
                    r = g.restore(_MmapBuf(mm) if kind == "mmap" else image)
                    copy = r["copy_s"]
                faults = resource.getrusage(resource.RUSAGE_SELF).ru_minflt - f0
                ok = g.turn(driver("import sklearn, sys; print(len(sys.modules))", call_env()))
                rows[kind].append({"copy_ms": round(copy * 1000, 2), "minor_faults": faults, "ok": ok["stdout"].strip()})
            finally:
                g.close()
        dst = (ctypes.c_char * len(image))()
        c0 = time.perf_counter()
        ctypes.memmove(dst, image, len(image))
        rows["host_memcpy"].append({"copy_ms": round((time.perf_counter() - c0) * 1000, 2)})
        del dst
    mm.close()
    fh.close()
    summary = {k: {"median_ms": statistics.median(r["copy_ms"] for r in v), "min_ms": min(r["copy_ms"] for r in v),
                   "max_ms": max(r["copy_ms"] for r in v),
                   "median_faults": statistics.median(r.get("minor_faults", 0) for r in v)} for k, v in rows.items()}
    res = {"prelude": name, "MiB": round(len(image) / 2**20, 1), "changed_MiB": round(sum(b - a for a, b in runs) * PAGE / 2**20, 1),
           "load_average": os.getloadavg(), "summary": summary, "rows": rows}
    print(json.dumps({k: res[k] for k in ("MiB", "changed_MiB", "load_average", "summary")}, indent=1))
    return res


def suite_finalize(engine, module, name="everything"):
    """Where a restored call's end goes: the program, an atexit-only end, the collector over the
    unfrozen heap, and the reactor's shutdown (unfreeze and Py_FinalizeEx)."""
    image, base, made = make_image(engine, module, PRELUDES[name])
    out = {}
    prog = "import sklearn, sys; print(len(sys.modules))"
    g = bare.Guest(engine, module, tag="fin")
    g.restore(image)
    end = (
        "try:\n"
        f"    __rc = __import__('_reactor').run({[bare.ARGV0, '-c', prog]!r}, {call_env()!r})\n"
        "finally:\n"
        "    __import__('atexit')._run_exitfuncs()\n"
        "raise SystemExit(__rc)\n"
    )
    r = g.turn(end)
    out["program_with_atexit_end"] = {k: r[k] for k in ("status", "fuel", "s")}
    r = g.turn("__import__('gc').unfreeze() or __import__('gc').collect() and None")
    out["unfreeze_and_collect"] = {k: r[k] for k in ("status", "fuel", "s")}
    r = g.shutdown()
    out["shutdown_after_collect"] = {k: r[k] for k in ("status", "fuel", "s")}
    g.close()
    h = bare.Guest(engine, module, tag="fin2")
    h.restore(image)
    r = h.turn(driver(prog, call_env()))
    out["program"] = {k: r[k] for k in ("status", "fuel", "s")}
    r = h.shutdown()
    out["shutdown_alone"] = {k: r[k] for k in ("status", "fuel", "s")}
    h.close()
    print(json.dumps(out, indent=1))
    return out


def suite_cow(engine, module, name="everything", rounds=8):
    """Can Python map the image copy-on-write over wasmtime's linear memory? libc mmap with
    MAP_FIXED | MAP_PRIVATE from the image file over the memory's own pages, through ctypes. A probe
    of the operating system, outside wasmtime's API: wasmtime owns that mapping."""
    import resource

    libc = ctypes.CDLL(None, use_errno=True)
    libc.mmap.restype = ctypes.c_void_p
    libc.mmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_long]
    PROT_RW = mmap.PROT_READ | mmap.PROT_WRITE
    MAP_FIXED = 0x10
    image, base, made = make_image(engine, module, PRELUDES[name])
    path = bare.WORK / f"image-{name}.raw"
    path.write_bytes(image)
    fd = os.open(path, os.O_RDONLY)
    rows = []
    for _ in range(rounds):
        g = bare.Guest(engine, module, tag="cow")
        try:
            want = len(image) // PAGE
            g.memory.grow(g.store, want - g.pages())
            f0 = resource.getrusage(resource.RUSAGE_SELF).ru_minflt
            c0 = time.perf_counter()
            dst = ctypes.addressof(g.memory.data_ptr(g.store).contents)
            got = libc.mmap(dst, len(image), PROT_RW, mmap.MAP_PRIVATE | MAP_FIXED, fd, 0)
            map_s = time.perf_counter() - c0
            if got != dst:
                rows.append({"error": ctypes.get_errno()})
                continue
            r = g.turn(driver("import sklearn, sys; print(len(sys.modules))", call_env()))
            faults = resource.getrusage(resource.RUSAGE_SELF).ru_minflt - f0
            rows.append({"map_ms": round(map_s * 1000, 3), "turn_ms": round(r["s"] * 1000, 1), "faults_map_and_turn": faults, "stdout": r["stdout"].strip(), "status": r["status"]})
        finally:
            g.close()
    os.close(fd)
    res = {"rows": rows, "load_average": os.getloadavg()}
    print(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    os.environ.setdefault("WASI_PYTHON_ARTIFACTS", "/Users/claygendron/Git/Repos/wasi_python/build/release-0.1.1/set/wasi-python-0.1.1")
    bare.on_big_stack(main, sys.argv[1:])
