"""Run one guest session of CPython's regrtest through the judge's own guest driver.

uv run python run_one.py <label> <fuel> -- <regrtest args...>

The snapshot binary of the frozen set, the judge's guest driver (tests/harness/guest.py: the
stdlib zip read-only at /usr/local/lib, a fresh writable root at /, the stepped clock, the seeded
random, fuel metered from the end of instantiation), plus one read-only grant: the stage at /cpy.
Writes <label>.json (exit, trap, fuel, wall seconds, per-test outcomes from regrtest's
--junit-xml) and <label>.out/.err under build/cpython-suite-research/runs/.
"""

import json
import os
import shutil
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path("/Users/claygendron/Git/Repos/wasi_python")
SET = REPO / "build/sets/s-4eb5418a2b1bb553"
WORK = REPO / "build/cpython-suite-research"
STAGE = WORK / "stage"
RUNS = WORK / os.environ.get("CPY_RUNS", "runs")
CWASM = WORK / "snapshot-fuel.cwasm"
ENV = {"TMPDIR": "/tmp", "HOME": "/tmp"}

sys.path.insert(0, str(REPO / "tests"))
import wasmtime as wt  # noqa: E402
from harness import guest  # noqa: E402


def preload(wasm: Path) -> None:
    """Compile once and keep it, so each session deserializes instead of compiling.

    With CPY_STACK=<bytes>, the engine's max_wasm_stack is set (wasmtime's default otherwise, as
    in the judge and the runner); CPython's own WASI CI uses 32 MiB (Platforms/WASI/wasmtime.toml).
    """
    if os.environ.get("CPY_STACK") and guest._engine is None:
        cfg = wt.Config()
        cfg.consume_fuel = True
        cfg.max_wasm_stack = int(os.environ["CPY_STACK"])
        guest._engine = wt.Engine(cfg)
    eng = guest.engine()
    if not CWASM.exists():
        tmp = CWASM.with_suffix(".tmp")
        tmp.write_bytes(wt.Module.from_file(eng, str(wasm)).serialize())
        tmp.rename(CWASM)
    st = wasm.stat()
    key = (str(wasm.resolve()), st.st_size, st.st_mtime_ns)
    if key not in guest._modules:  # once per process
        guest._modules[key] = wt.Module.deserialize_file(eng, str(CWASM))


def outcomes(xml_text: str) -> list[tuple[str, str, str]]:
    """(outcome, test id, reason) per testcase element."""
    out = []
    root = ET.fromstring(xml_text)
    for case in root.iter("testcase"):
        name = case.get("name") or "?"
        if case.find("error") is not None:
            e = case.find("error")
            out.append(("error", name, (e.get("type") or "") + ": " + (e.get("message") or "")))
        elif case.find("failure") is not None:
            e = case.find("failure")
            out.append(("failed", name, (e.get("type") or "") + ": " + (e.get("message") or "")))
        elif case.find("skipped") is not None:
            out.append(("skipped", name, case.find("skipped").text or ""))
        elif case.find("output") is not None:
            out.append(("xfailed", name, ""))
        elif case.get("name") is None:
            out.append(("failed", name, "subtest failure (no testcase result)"))
        elif case.get("outcome") == "UNEXPECTED_SUCCESS":
            out.append(("xpassed", name, ""))
        else:
            out.append(("passed", name, ""))
    return out


def main() -> None:
    label, fuel = sys.argv[1], int(float(sys.argv[2]))
    args = sys.argv[sys.argv.index("--") + 1 :]
    RUNS.mkdir(parents=True, exist_ok=True)
    wasm = SET / "python-snapshot.wasm"
    preload(wasm)
    workdir = WORK / "tmp"  # shared: the driver keeps matplotlib's data here once per process
    workdir.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    r = guest.run(
        wasm,
        ["-u", "/cpy/judge/drive.py", *args, "--junit-xml", "/tmp/junit.xml"],
        workdir=workdir,
        python_version="3.15.0",
        stdlib=SET / "python-stdlib.zip",
        env=ENV,
        fuel=fuel,
        preopens=[("/cpy", STAGE, False)],
        # Adaptation A3 (CPY_EXE=1): an empty file where sys.executable points, so
        # platform.libc_ver() (which reads sys.executable) finds a file to read.
        files={"/usr/local/bin/python.wasm": b""} if os.environ.get("CPY_EXE") else None,
        mpl_data=True,
    )
    wall = time.monotonic() - t0
    junit = r.root / "tmp/junit.xml"
    cases = []
    if junit.is_file():
        try:
            cases = outcomes(junit.read_text(errors="replace"))
        except ET.ParseError as e:
            cases = [("error", "<junit>", f"unparseable junit: {e}")]
    (RUNS / f"{label}.out").write_bytes(r.stdout)
    (RUNS / f"{label}.err").write_bytes(r.stderr)
    counts: dict[str, int] = {}
    for o, _, _ in cases:
        counts[o] = counts.get(o, 0) + 1
    rec = {
        "label": label,
        "args": args,
        "exit": r.exit_code,
        "trapped": r.trapped,
        "trap_cause": r.trap_cause,
        "fuel": r.fuel,
        "wall_s": round(wall, 1),
        "junit": junit.is_file(),
        "counts": counts,
        "cases": cases,
        "stderr_tail": r.stderr.decode(errors="replace").strip().splitlines()[-3:],
    }
    (RUNS / f"{label}.json").write_text(json.dumps(rec, indent=1))
    shutil.rmtree(r.root.parent, ignore_errors=True)  # the session's root and io
    print(
        f"{label}: exit={r.exit_code} trap={r.trapped} fuel={r.fuel / 1e9:.2f}G wall={wall:.1f}s "
        f"{counts}"
    )


if __name__ == "__main__":
    main()
