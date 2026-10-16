"""Golden jobs: native Python at the guest's pins is the oracle (spec 002, Decision 11).

A job takes a data directory and an output directory. Its expected output is its stdout, then
each file it wrote in path order, each after a `=== <name>` line. The oracle is its own uv
project (`tests/jobs/oracle/`), run with every uv download under `build/oracle/`.
"""

from __future__ import annotations

import functools
import os
import re
import shutil
import subprocess
from pathlib import Path

from harness import paths

JOB_DIR = paths.REPO / "tests" / "jobs"
ORACLE_PROJECT = JOB_DIR / "oracle"
ORACLE_HOME = paths.BUILD / "oracle"
JOBS = ("numpy_csv", "pandas_csv", "numpy_random")
DATA = {"sales.csv": paths.REPO / "fixtures" / "sales.csv"}
VERSIONS = re.compile(r"versions( [\w-]+=\S+)+")


def script(job: str) -> Path:
    return JOB_DIR / f"{job}.py"


def expected_path(job: str) -> Path:
    return JOB_DIR / f"{job}.expected"


def render(stdout: bytes, out_dir: Path) -> bytes:
    parts = [stdout]
    for f in sorted(p for p in out_dir.rglob("*") if p.is_file()):
        parts.append(f"=== {f.relative_to(out_dir).as_posix()}\n".encode())
        parts.append(f.read_bytes())
    return b"".join(parts)


def compare(expected: bytes, actual: bytes) -> str | None:
    """None when equal; otherwise one line saying how they differ."""
    if expected == actual:
        return None
    exp = expected.decode(errors="replace").split("\n")
    act = actual.decode(errors="replace").split("\n")
    if VERSIONS.fullmatch(exp[0]) and VERSIONS.fullmatch(act[0]) and exp[0] != act[0]:
        return f"goldens are stale: expected {exp[0]!r}, the guest has {act[0]!r}"
    for n, (e, a) in enumerate(zip(exp, act, strict=False), 1):
        if e != a:
            return f"line {n}: expected {e!r}, got {a!r}"
    return f"expected {len(exp)} lines, got {len(act)}"


def oracle_env(seed: int | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        UV_CACHE_DIR=str(ORACLE_HOME / "cache"),
        UV_PYTHON_INSTALL_DIR=str(ORACLE_HOME / "python"),
        UV_PROJECT_ENVIRONMENT=str(ORACLE_HOME / "venv"),
        UV_PYTHON_PREFERENCE="only-managed",
    )
    env.pop("VIRTUAL_ENV", None)
    if seed is not None:
        env["PYTHONHASHSEED"] = str(seed)
    return env


def oracle_command(*args: str, offline: bool = True) -> list[str]:
    uv = shutil.which("uv") or "uv"
    flags = ["--frozen", "--project", str(ORACLE_PROJECT)] + (["--offline"] if offline else [])
    return [uv, "run", "-q", *flags, "python", *args]


@functools.cache
def oracle_available() -> bool:
    try:
        r = subprocess.run(
            oracle_command("-c", "import numpy, pandas"),
            env=oracle_env(),
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    return r.returncode == 0


def stage_data(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, src in DATA.items():
        shutil.copyfile(src, directory / name)


def run_native(job: str, seed: int, workdir: Path, *, offline: bool = True) -> bytes:
    """One native run of a job under the oracle; the rendered output."""
    base = workdir / f"{job}-seed{seed}"
    if base.exists():
        shutil.rmtree(base)
    data, out = base / "data", base / "out"
    stage_data(data)
    out.mkdir(parents=True)
    r = subprocess.run(
        oracle_command(str(script(job)), str(data), str(out), offline=offline),
        env=oracle_env(seed),
        capture_output=True,
        check=False,
    )
    if r.returncode != 0:
        tail = r.stderr.decode(errors="replace").strip().splitlines()[-1:] or [""]
        raise RuntimeError(f"{job}: the oracle exited {r.returncode}: {tail[0]}")
    return render(r.stdout, out)
