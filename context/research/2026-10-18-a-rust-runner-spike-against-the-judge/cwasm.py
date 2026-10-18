"""Compile the guest modules in wasmtime-py 49.0.0 and in the Rust spike (49.0.0 and 49.0.3) under
the same Config, and compare the serialized modules (.cwasm) byte for byte; then load
wasmtime-py's .cwasm in each Rust build and run one job on it.

    uv run --frozen --project <repo> python cwasm.py <rust-49.0.0> <rust-49.0.3>
"""

from __future__ import annotations

import hashlib
import os
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import wasmtime as wt

REPO = Path("/Users/claygendron/Git/Repos/wasi_python")
SET = REPO / "build/sets/s-8eb9e35734deeb21"
WORK = REPO / "build/rust-spike/work/cwasm"
BINS = {"plain": SET / "python.wasm", "snapshot": SET / "python-snapshot.wasm"}
COLLECTOR = os.environ.get("COLLECTOR") or None  # "drc": wasmtime-py's collector
CONFIGS = {"judge": (True, False), "runner-fuel": (True, True)}  # (consume_fuel, epoch)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def py_compile(cfg: str, which: str, tag: str) -> dict:
    fuel, epoch = CONFIGS[cfg]
    c = wt.Config()
    c.consume_fuel = fuel
    c.epoch_interruption = epoch
    engine = wt.Engine(c)
    t = time.perf_counter()
    mod = wt.Module.from_file(engine, str(BINS[which]))
    ms = (time.perf_counter() - t) * 1e3
    dest = WORK / f"py49.0.0-{cfg}-{which}{tag}.cwasm"
    dest.write_bytes(mod.serialize())
    return dict(side="py-49.0.0", cfg=cfg, which=which, ms=round(ms), bytes=dest.stat().st_size,
                sha=sha(dest)[:16], path=str(dest))


def rs_compile(binary: Path, label: str, cfg: str, which: str) -> dict:
    fuel, epoch = CONFIGS[cfg]
    dest = WORK / f"rs{label}-{COLLECTOR or 'default'}-{cfg}-{which}.cwasm"
    dest.unlink(missing_ok=True)
    job = dict(id="c", wasm=str(BINS[which]), cwasm=str(dest), argv=[], mode="judge",
               stdout_path="/dev/null", stderr_path="/dev/null", compile_only=True)
    batch = dict(consume_fuel=fuel, epoch_interruption=epoch, collector=COLLECTOR, jobs=[job])
    p = subprocess.run([str(binary)], input=json.dumps(batch).encode(), capture_output=True,
                       check=True)
    o = json.loads(p.stdout)
    return dict(side=f"rs-{label}", cfg=cfg, which=which, ms=round(o["module_ms"]),
                bytes=dest.stat().st_size, sha=sha(dest)[:16], path=str(dest))


def rs_load_and_run(binary: Path, label: str, cwasm: Path, which: str) -> dict:
    """Load a .cwasm wasmtime-py wrote, in the Rust build, and run print('hello') on it in judge
    mode (needs the judge Config: consume_fuel, no epoch)."""
    base = WORK / f"load-{label}-{which}"
    shutil.rmtree(base, ignore_errors=True)
    (base / "root/usr/local/lib").mkdir(parents=True)
    (base / "lib").mkdir()
    (base / "lib/python315.zip").hardlink_to(SET / "python-stdlib.zip")
    copy = base / "py.cwasm"
    shutil.copyfile(cwasm, copy)
    job = dict(id="load", wasm=str(BINS[which]), cwasm=str(copy),
               argv=["/usr/local/bin/python.wasm", "-c", "print('hello')"],
               preopens=[[str(base / "lib"), "/usr/local/lib", False], [str(base / "root"), "/", True]],
               fuel=2 * 10**11, mode="judge", stdout_path=str(base / "stdout"),
               stderr_path=str(base / "stderr"))
    batch = dict(consume_fuel=True, epoch_interruption=False, collector=COLLECTOR, jobs=[job])
    p = subprocess.run([str(binary)], input=json.dumps(batch).encode(), capture_output=True,
                       check=False)
    o = json.loads(p.stdout) if p.stdout else {"error": p.stderr.decode()[-500:]}
    if "error" in o:
        o["error"] = " / ".join(x.strip() for x in o["error"].splitlines() if x.strip())[:400]
    else:
        o["stdout"] = (base / "stdout").read_text()
    return dict(side=f"rs-{label}", loads=cwasm.name, **o)


def main() -> None:
    rs0, rs3 = Path(sys.argv[1]), Path(sys.argv[2])
    WORK.mkdir(parents=True, exist_ok=True)
    rows = []
    for cfg in CONFIGS:
        for which in BINS:
            rows.append(py_compile(cfg, which, ""))
            rows.append(rs_compile(rs0, "49.0.0", cfg, which))
            rows.append(rs_compile(rs3, "49.0.3", cfg, which))
            print(json.dumps(rows[-3:]), file=sys.stderr, flush=True)
    # Is one side's own output repeatable? Compile once more in wasmtime-py.
    rows.append(py_compile("judge", "plain", "-again"))
    loads = [
        rs_load_and_run(rs0, "49.0.0", WORK / "py49.0.0-judge-plain.cwasm", "plain"),
        rs_load_and_run(rs3, "49.0.3", WORK / "py49.0.0-judge-plain.cwasm", "plain"),
        rs_load_and_run(rs0, "49.0.0", WORK / "py49.0.0-judge-snapshot.cwasm", "snapshot"),
    ]
    out = dict(compiles=rows, loads=loads)
    dest = Path(__file__).parent / "results" / f"cwasm-{COLLECTOR or 'default'}-collector.json"
    dest.write_text(json.dumps(out, indent=1))
    for r in rows:
        print(r["side"], r["cfg"], r["which"], r["ms"], "ms", r["bytes"], r["sha"])
    for r in loads:
        print(json.dumps(r))


if __name__ == "__main__":
    main()
