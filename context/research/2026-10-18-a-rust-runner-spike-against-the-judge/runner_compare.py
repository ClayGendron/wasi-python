"""Compare the Rust spike in runner mode with the product runner, `wasi_python.run`.

Runner mode: Config(consume_fuel when a budget is given, epoch_interruption always), wasmtime's
own random and clocks, the stdlib zip and matplotlib's data at /usr/local/lib, no root, the
grants after them, the runner's base env, the runner's default memory cap (1 GiB) and deadline
(60 s) unless a job names its own. Random and clocks are real here, so fuel is not expected to
repeat exactly; each job runs twice on each side to show the spread.

    uv run --frozen --project <repo> python runner_compare.py <rust-binary> <label>
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path("/Users/claygendron/Git/Repos/wasi_python")
SET = REPO / "build/sets/s-8eb9e35734deeb21"
SPIKE = REPO / "build/rust-spike"
os.environ["WASI_PYTHON_ARTIFACTS"] = str(SET)
sys.path.insert(0, str(REPO / "tests"))

import wasi_python  # noqa: E402
from harness import guest  # noqa: E402

STDLIB = SET / "python-stdlib.zip"
BIN = {True: SET / "python-snapshot.wasm", False: SET / "python.wasm"}
BASE_ENV = {"TMPDIR": "/tmp", "PYTHONTZPATH": ""}
DEFAULT_MEMORY, DEFAULT_DEADLINE = 1 << 30, 60.0

RO_RW = """
import os
print(sorted(os.listdir('/ro')))
try:
    open('/ro/new.txt', 'w').write('no')
    print('ro write: allowed')
except OSError as e:
    print('ro write:', type(e).__name__, e.errno)
open('/rw/out.txt', 'w').write('written by the guest\\n')
print('rw write: ok')
"""

JOBS = {
    "hello-snapshot": dict(argv=["-c", "print('hello')"], snapshot=True, fuel=10**10),
    "hello-snapshot-hashseed0": dict(
        argv=["-c", "print('hello')"], snapshot=True, fuel=10**10, env={"PYTHONHASHSEED": "0"}
    ),
    "numpy-sum-plain": dict(
        argv=["-c", "import numpy as np; print(np.arange(10**6).sum())"],
        snapshot=False,
        fuel=10**11,
    ),
    "exit3-stderr-snapshot": dict(
        argv=["-c", "import sys; sys.stderr.write('boom\\n'); sys.exit(3)"],
        snapshot=True,
        fuel=10**10,
    ),
    "memory-cap-snapshot": dict(
        argv=["-c", "b = bytearray(300 << 20)"], snapshot=True, fuel=10**10, memory_bytes=256 << 20
    ),
    "grants-ro-rw-snapshot": dict(argv=["-c", RO_RW], snapshot=True, fuel=10**10, grants=True),
    "deadline-unmetered-snapshot": dict(
        argv=["-c", "while True: pass"], snapshot=True, fuel=None, deadline_s=1.0
    ),
    "deadline-metered-snapshot": dict(
        argv=["-c", "while True: pass"], snapshot=True, fuel=10**13, deadline_s=1.0
    ),
}
REPEATS = 2


def grant_dirs(base: Path) -> list[tuple[str, Path, bool]]:
    ro, rw = base / "ro", base / "rw"
    ro.mkdir(parents=True)
    rw.mkdir(parents=True)
    (ro / "in.txt").write_text("read-only input\n")
    return [("/ro", ro, False), ("/rw", rw, True)]


def run_py(name: str, spec: dict, base: Path, cache: Path) -> dict:
    grants = grant_dirs(base) if spec.get("grants") else []
    t = time.perf_counter()
    c = wasi_python.run(
        spec["argv"],
        snapshot=spec["snapshot"],
        fuel=spec.get("fuel"),
        env=spec.get("env"),
        deadline_s=spec.get("deadline_s", DEFAULT_DEADLINE),
        memory_bytes=spec.get("memory_bytes", DEFAULT_MEMORY),
        grants=[wasi_python.Grant(str(h), g, writable=w) for g, h, w in grants],
        cache_dir=cache,
    )
    wall = time.perf_counter() - t
    rw = (base / "rw" / "out.txt").read_bytes() if grants else None
    return dict(
        exit_code=c.exit_code,
        trapped=c.trapped,
        fuel=c.fuel_used,
        stdout=c.stdout,
        stderr=c.stderr,
        rw=rw,
        wall_s=wall,
    )


def rust_job(name: str, spec: dict, base: Path, mpl: Path) -> dict:
    lib, io = base / "lib", base / "io"
    lib.mkdir(parents=True)
    io.mkdir()
    zname = guest.stdlib_name("3.15.0", STDLIB)
    os.link(STDLIB, lib / zname)
    preopens = [
        [str(lib), "/usr/local/lib", False],
        [str(mpl), f"/usr/local/lib/{zname}/matplotlib/mpl-data", False],
    ]
    for g, h, w in grant_dirs(base) if spec.get("grants") else []:
        preopens.append([str(h), g, w])
    return dict(
        id=name,
        wasm=str(BIN[spec["snapshot"]]),
        argv=[guest.ARGV0, *spec["argv"]],
        env=sorted({**BASE_ENV, **(spec.get("env") or {})}.items()),
        preopens=preopens,
        fuel=spec.get("fuel"),
        memory_bytes=spec.get("memory_bytes", DEFAULT_MEMORY),
        deadline_s=spec.get("deadline_s", DEFAULT_DEADLINE),
        mode="runner",
        stdout_path=str(io / "stdout"),
        stderr_path=str(io / "stderr"),
    )


def run_rust(binary: Path, batch_jobs: list[dict], metered: bool) -> dict[str, dict]:
    batch = dict(consume_fuel=metered, epoch_interruption=True, jobs=batch_jobs)
    p = subprocess.run(
        [str(binary)], input=json.dumps(batch).encode(), capture_output=True, check=False
    )
    if p.returncode != 0:
        raise SystemExit(f"rust runner exited {p.returncode}: {p.stderr.decode()[-2000:]}")
    out = {}
    for line in p.stdout.decode().splitlines():
        o = json.loads(line)
        j = next(j for j in batch_jobs if j["id"] == o["id"])
        rw = Path(j["stdout_path"]).parent.parent / "rw" / "out.txt"
        out[o["id"]] = dict(
            exit_code=o.get("exit_code"),
            trapped=o.get("trapped"),
            fuel=o.get("fuel_used"),
            stdout=Path(j["stdout_path"]).read_bytes() if "error" not in o else b"",
            stderr=Path(j["stderr_path"]).read_bytes() if "error" not in o else b"",
            rw=rw.read_bytes() if rw.is_file() else None,
            run_ms=o.get("run_ms"),
            error=o.get("error"),
        )
    return out


def main() -> None:
    binary, label = Path(sys.argv[1]), sys.argv[2]
    work = SPIKE / "work" / f"runner-{label}-{int(time.time())}"
    cache = SPIKE / "work" / "cwasm-py-runner"
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    mpl = guest.mpl_data_dir(STDLIB, work)
    py: dict[str, list[dict]] = {n: [] for n in JOBS}
    rs: dict[str, list[dict]] = {n: [] for n in JOBS}
    for k in range(REPEATS):
        for n, spec in JOBS.items():
            py[n].append(run_py(n, spec, work / f"py-{n}-{k}", cache))
            print(f"py {n}#{k}: {py[n][-1]['exit_code']} {py[n][-1]['trapped']} {py[n][-1]['fuel']}",
                  file=sys.stderr, flush=True)
        for metered in (True, False):
            names = [n for n, s in JOBS.items() if (s.get("fuel") is not None) == metered]
            batch = [rust_job(n, JOBS[n], work / f"rs-{n}-{k}", mpl) for n in names]
            for n, o in run_rust(binary, batch, metered).items():
                rs[n].append(o)
    rows = []
    for n in JOBS:
        a, b = py[n], rs[n]
        same = lambda key: all(x[key] == a[0][key] for x in a + b)  # noqa: E731
        fuels_py = [x["fuel"] for x in a]
        fuels_rs = [x["fuel"] for x in b]
        row = dict(
            job=n,
            exit=[a[0]["exit_code"], b[0]["exit_code"]],
            trapped=[a[0]["trapped"], b[0]["trapped"]],
            exit_equal=same("exit_code"),
            trapped_equal=same("trapped"),
            stdout_equal=same("stdout"),
            stderr_equal=same("stderr"),
            rw_equal=same("rw"),
            fuel_py=fuels_py,
            fuel_rs=fuels_rs,
            errors=[x["error"] for x in b if x.get("error")],
        )
        if not row["stderr_equal"]:
            row["stderr_py"] = a[0]["stderr"][-400:].decode(errors="replace")
            row["stderr_rs"] = b[0]["stderr"][-400:].decode(errors="replace")
        if not row["stdout_equal"]:
            row["stdout_py"] = a[0]["stdout"][-300:].decode(errors="replace")
            row["stdout_rs"] = b[0]["stdout"][-300:].decode(errors="replace")
        if all(f is not None for f in fuels_py + fuels_rs):
            lo, hi = min(fuels_py + fuels_rs), max(fuels_py + fuels_rs)
            row["fuel_spread_ppm"] = round((hi - lo) / lo * 1e6, 1)
            row["fuel_spread_py_ppm"] = round((max(fuels_py) - min(fuels_py)) / lo * 1e6, 1)
            row["fuel_spread_rs_ppm"] = round((max(fuels_rs) - min(fuels_rs)) / lo * 1e6, 1)
        row["outputs_match"] = all(
            row[k] for k in ("exit_equal", "trapped_equal", "stdout_equal", "stderr_equal", "rw_equal")
        )
        rows.append(row)
    dest = Path(__file__).parent / "results" / f"runner-{label}.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(dict(label=label, binary=str(binary), rows=rows), indent=1))
    for r in rows:
        print(json.dumps(r))
    print(f"outputs matched {sum(r['outputs_match'] for r in rows)}/{len(rows)}; wrote {dest}")


if __name__ == "__main__":
    main()
