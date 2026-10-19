"""Resident memory of N live instances that each ran `-c pass` (kept alive, as a multi-tenant host
would hold them during a run). Usage: instances.py <label> <wasm> <N>. RSS from ps, a benchmark
fact for memory (bytes are the measure; the number is this machine's)."""
import os, pathlib, subprocess, sys
HERE = pathlib.Path("/Users/claygendron/Git/Repos/wasi_python")
sys.path.insert(0, str(HERE / "tests/harness"))
import wasmtime as wt, guest  # noqa
label, wasm, n = sys.argv[1], pathlib.Path(sys.argv[2]), int(sys.argv[3])
ZIP = HERE / "build/sets/s-4eb5418a2b1bb553/python-stdlib.zip"
S = pathlib.Path(__file__).resolve().parent.parent
work = S / "runs" / f"inst-{label}"
def rss():
    return int(subprocess.check_output(["ps", "-o", "rss=", "-p", str(os.getpid())]).strip()) * 1024
mod = guest.module(wasm)
base = rss()
kept = []
for k in range(n):
    store = wt.Store(guest.engine()); store.set_fuel(guest.UNMETERED)
    wasi = wt.WasiConfig(); wasi.argv = [guest.ARGV0, "-c", "pass"]
    root = work / f"r{k}"; (root / "usr/local/lib").mkdir(parents=True, exist_ok=True)
    lib = work / "lib"; lib.mkdir(exist_ok=True)
    if not (lib / "python315.zip").exists(): os.link(ZIP, lib / "python315.zip")
    wasi.preopen_dir(str(lib), "/usr/local/lib", False); wasi.preopen_dir(str(root), "/", True)
    wasi.stdout_file = str(root / "out"); wasi.stderr_file = str(root / "err")
    store.set_wasi(wasi)
    linker = wt.Linker(guest.engine()); linker.define_wasi(); linker.allow_shadowing = True
    i32 = wt.ValType.i32()
    linker.define_func("host", "call", wt.FuncType([i32] * 4, [i32]), lambda *a: -1, True)
    inst = linker.instantiate(store, mod)
    ex = inst.exports(store)
    if "_initialize" in ex: ex["_initialize"](store)
    ex["run"](store)
    kept.append((store, inst))
    if k == 0: first = rss()
total = rss()
print(f"{label}: module loaded {base/2**20:.1f} MiB; after 1 instance +{(first-base)/2**20:.1f} MiB; after {n} instances +{(total-base)/2**20:.1f} MiB; per instance (2..{n}) {(total-first)/(n-1)/2**20:.1f} MiB")
