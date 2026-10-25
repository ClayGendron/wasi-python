"""The speed spike's FILES program (20,000 stats and 2,000 reads on a read-only grant), timed in
four arms, each in a fresh process: the product as shipped; the product with the two guarded
calls left native; the product with the guarded and the counted calls left native; a bare
wasmtime-py embedding. Wall-clock on one machine: benchmark facts for a memo, never a check.

    <venv python> files_bench.py driver <label> [repeats]     # runs every arm, interleaved
    <venv python> files_bench.py <arm> <program>              # one arm, in-process
"""
import importlib.metadata as md, json, os, statistics, subprocess, sys, time
from pathlib import Path

REPO = Path("/Users/claygendron/Git/Repos/wasi_python")
SET = REPO / "build/artifacts"
WORK = REPO / "build/scratch-wt50/bench-work"
os.environ["WASI_PYTHON_ARTIFACTS"] = str(SET)
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tests"))
FUEL, MEMORY, DEADLINE = 10**12, 1 << 30, 120.0
PROGRAMS = {
    "files": "import os\nfor i in range(20000):\n    os.stat('/ro/f%d.txt' % (i % 100))\nn = 0\nfor i in range(2000):\n    with open('/ro/f%d.txt' % (i % 100), 'rb') as f:\n        n += len(f.read())\nprint(n)\n",
    "hello": "print('hello')",
}
VER = md.version("wasmtime")


def ro_dir() -> Path:
    d = WORK / "ro"
    if not d.exists():
        d.mkdir(parents=True)
        for i in range(100):
            (d / f"f{i}.txt").write_bytes(b"z" * 4096)
    return d


def product(code: str, ro: Path, runs: int) -> list[float]:
    import wasi_python
    out = []
    for _ in range(runs):
        t = time.perf_counter()
        c = wasi_python.run(["-c", code], fuel=FUEL, deadline_s=DEADLINE, memory_bytes=MEMORY,
                            grants=[wasi_python.Grant(str(ro), "/ro")], cache_dir=WORK / "cwasm-product")
        out.append((time.perf_counter() - t) * 1e3)
        assert c.exit_code == 0 and not c.trapped, (c.exit_code, c.trapped, c.stderr[-300:])
    return out


def bare(code: str, ro: Path, runs: int) -> list[float]:
    import wasmtime as wt
    from harness import guest
    cfg = wt.Config(); cfg.consume_fuel = True; cfg.epoch_interruption = True
    engine = wt.Engine(cfg)
    cache = WORK / f"cwasm-bare-{VER}"; cache.mkdir(parents=True, exist_ok=True)
    cw = cache / "python-snapshot.cwasm"
    if cw.is_file():
        mod = wt.Module.deserialize_file(engine, str(cw))
    else:
        mod = wt.Module.from_file(engine, str(SET / "python-snapshot.wasm")); cw.write_bytes(mod.serialize())
    lib = WORK / "lib"; lib.mkdir(exist_ok=True)
    z = lib / guest.stdlib_name("3.15.0", SET / "python-stdlib.zip")
    if not z.exists():
        os.link(SET / "python-stdlib.zip", z)
    io = WORK / "bare-io"; io.mkdir(exist_ok=True)
    out = []
    for _ in range(runs):
        t = time.perf_counter()
        store = wt.Store(engine); store.set_fuel(2**63 - 1); store.set_epoch_deadline(2**40)
        store.set_limits(memory_size=MEMORY)
        wasi = wt.WasiConfig(); wasi.argv = [guest.ARGV0, "-c", code]; wasi.env = [("TMPDIR", "/tmp"), ("PYTHONTZPATH", "")]
        wasi.preopen_dir(str(lib), "/usr/local/lib", False); wasi.preopen_dir(str(ro), "/ro", False)
        wasi.stdout_file = str(io / "stdout"); wasi.stderr_file = str(io / "stderr")
        store.set_wasi(wasi)
        linker = wt.Linker(engine); linker.define_wasi()
        i32 = wt.ValType.i32()
        linker.define_func("host", "call", wt.FuncType([i32] * 4, [i32]), lambda *_: -1, True)
        inst = linker.instantiate(store, mod); store.set_fuel(FUEL)
        try:
            code_out = inst.exports(store)["run"](store)
        except wt.ExitTrap as e:
            code_out = e.code
        out.append((time.perf_counter() - t) * 1e3)
        assert code_out == 0, (io / "stderr").read_bytes()[-300:]
    return out


def arm(name: str, program: str) -> None:
    ro = ro_dir()
    code = PROGRAMS[program]
    if name == "bare":
        fn = bare
    else:
        import wasi_python._fs_memory as m
        if name in ("product-noguard", "product-nocount"):
            m.GUARDED = ()  # the guard linker is built at the first call, from these tuples
        if name == "product-nocount":
            m.COUNTED = ()
        fn = product
    fn(code, ro, 1)  # warm: the module from its cache, the first instantiation
    ms = fn(code, ro, 3)
    print(json.dumps({"arm": name, "program": program, "wasmtime_py": VER, "ms": [round(x, 1) for x in ms]}))
    sys.stdout.flush()
    os._exit(0)  # the module drop at exit is not what is measured


def driver(label: str, repeats: int) -> None:
    rows = {}
    plan = [(a, p) for p in ("files", "hello") for a in ("product", "product-noguard", "product-nocount", "bare")]
    for r in range(repeats):
        for a, p in plan:
            out = subprocess.run([sys.executable, __file__, a, p], capture_output=True, text=True, check=False)
            if out.returncode != 0:
                raise SystemExit(f"{a} {p}: {out.stderr[-800:]}")
            row = json.loads(out.stdout.strip().splitlines()[-1])
            rows.setdefault((a, p), []).extend(row["ms"])
            print(f"  round {r + 1} {a:17s} {p:6s} {row['ms']}", file=sys.stderr, flush=True)
    result = {"label": label, "wasmtime_py": VER, "arms": {}}
    for (a, p), ms in rows.items():
        result["arms"][f"{a}/{p}"] = {"n": len(ms), "median_ms": round(statistics.median(ms), 1), "min_ms": round(min(ms), 1), "max_ms": round(max(ms), 1)}
    dest = REPO / "build/scratch-wt50/out" / f"files-bench-{label}.json"
    dest.write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "driver":
        driver(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 3)
    else:
        arm(sys.argv[1], sys.argv[2])
