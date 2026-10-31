"""Golden jobs: native Python at the guest's pins is the oracle.

A job takes a data directory and an output directory. Its expected output is its stdout, then
each file it wrote in path order, each after a `=== <name>` line. The oracle is its own uv
project (`tests/jobs/oracle/`), run with every uv download under `build/oracle/`.

Its interpreter is its own copy of the line's pinned host Python (`scripts/line.conf`'s
`HOST_PYTHON_ARCHIVE`), checked against `downloads/SHA256SUMS` and unpacked under
`build/oracle/python/`, because the pinned uv cannot install the line's version.
It shares no directory with the build.
"""

from __future__ import annotations

import functools
import importlib.util
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

from harness import paths

JOB_DIR = paths.REPO / "tests" / "jobs"
ORACLE_PROJECT = JOB_DIR / "oracle"
ORACLE_HOME = paths.BUILD / "oracle"
LINE_CONF = paths.REPO / "scripts" / "line.conf"
LINE_PY = paths.REPO / "scripts" / "line.py"
JOBS = (
    "numpy_csv",
    "pandas_csv",
    "numpy_random",
    "compress",
    "sqlite",
    "callbacks",
    "pandas_tz",
    "plot_line",
    "plot_callbacks",
    "plot_contour",
    "lxml_xml",
    "regex_features",
    # Tier A, one job per family
    "excel",
    "pdf",
    "markup",
    "text_formats",
    "modelling",
    "symbolic",
    "utilities",
    # The files two packages read by path, from the zip
    "files_from_the_zip",
    # scipy's first milestone
    "scipy_numeric",
    "scipy_solvers",
    "scipy_lapack",
    # scipy's second milestone: the sandbox's edges
    "scipy_edges",
    # scikit-learn
    "machine_learning",
    # seaborn's statistical plots and reportlab's PDF reports
    "statistical_plots",
    "pdf_reports",
    # statsmodels (Decision 12)
    "statistical_models",
    # python-docx and python-pptx from their default templates
    "documents",
    # pdfplumber's tables and xarray's labelled arrays
    "pdf_tables",
    "labelled_arrays",
    # drawsvg's vector drawings and animations, as SVG and HTML
    "vector_drawings",
)
# Jobs whose native output may differ off the platform that recorded them:
# native matplotlib's pixels may move by platform (its own tests allow it in 61 places), while the
# guest's never do. Each records its platform in tests/jobs/<job>.platform; the oracle reproduces
# it only there, and the guest must match it everywhere. plot_contour prints
# a figure's RGBA buffer and its SVG and PDF bytes, so it is bound in the same way.
# The scipy jobs too: the oracle's scipy is pinned to scipy-openblas on
# macOS arm64, where its goldens are recorded; elsewhere its LAPACK and kernels differ (the
# edges job too). And scikit-learn's: PCA and the linear models reach
# LAPACK through scipy. statistical_plots prints seaborn's figures' RGBA
# buffers and SVGs, and values from scipy's kernel densities and clustering; pdf_reports prints no
# pixel and reproduces everywhere. And statsmodels' (Decision 12): OLS and ARIMA reach
# LAPACK through scipy too.
PLATFORM_BOUND = (
    "plot_line",
    "plot_contour",
    "scipy_numeric",
    "scipy_solvers",
    "scipy_lapack",
    "scipy_edges",
    "machine_learning",
    "statistical_plots",
    "statistical_models",
)
# A small PNG an SVG drawing embeds as a data URI, read from the data folder.
DATA = {
    "sales.csv": paths.REPO / "fixtures" / "sales.csv",
    "swatch.png": paths.REPO / "fixtures" / "swatch.png",
}
# pyyaml publishes no cp315 wheel, so the oracle takes its pure tree from the pinned sdist, as the
# guest does: nothing is built on the host.
PURE_SDIST = "pyyaml-6.0.3.tar.gz"
VERSIONS = re.compile(r"versions( [\w-]+=\S+)+")


def script(job: str) -> Path:
    return JOB_DIR / f"{job}.py"


def expected_path(job: str) -> Path:
    return JOB_DIR / f"{job}.expected"


def platform_path(job: str) -> Path:
    return JOB_DIR / f"{job}.platform"


def this_platform() -> str:
    """The native platform a golden was made on, as `darwin-arm64`."""
    machine = platform.machine().lower()
    return f"{sys.platform}-{'arm64' if machine in ('arm64', 'aarch64') else machine}"


def reproducible_here(job: str) -> bool:
    """Whether the oracle can reproduce this job's golden on this machine."""
    if job not in PLATFORM_BOUND:
        return True
    f = platform_path(job)
    return f.is_file() and f.read_text().strip() == this_platform()


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


def host_python_archive() -> str:
    """The line's pinned host-Python archive, named in `scripts/line.conf` and read by the build's
    own parser (`scripts/line.py`), which enforces the file's grammar."""
    spec = importlib.util.spec_from_file_location("wasi_python_line", LINE_PY)
    assert spec is not None and spec.loader is not None
    line = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(line)
    name = line.read(LINE_CONF).get("HOST_PYTHON_ARCHIVE")
    if name is None:  # not a build host: the line pins a host Python for build hosts only
        raise RuntimeError("no host Python for this host: scripts/line.conf pins build hosts only")
    if "/" in name or name.startswith("."):
        raise RuntimeError(f"HOST_PYTHON_ARCHIVE is not a plain file name: {name!r}")
    return name


def oracle_python() -> Path:
    """The oracle's interpreter: the pinned archive, hash-checked, unpacked once under
    build/oracle/python/<archive>/. A stamp holding the archive's hash marks a finished unpack."""
    name = host_python_archive()
    home = ORACLE_HOME / "python" / name
    exe = home / "python" / "bin" / "python3"
    stamp = home / ".sha256"
    sha = paths.read_pin_list().get(name)
    if sha is None:
        raise RuntimeError(f"{name} is not pinned in downloads/SHA256SUMS")
    if exe.is_file() and stamp.is_file() and stamp.read_text() == sha:
        return exe
    archive = paths.DOWNLOADS / name
    if not archive.is_file():
        raise RuntimeError(f"downloads/{name} is missing: run scripts/00_download.sh")
    if paths.sha256_file(archive) != sha:
        raise RuntimeError(f"downloads/{name} does not match its pin")
    shutil.rmtree(home, ignore_errors=True)
    home.mkdir(parents=True)
    with tarfile.open(archive) as t:
        t.extractall(home, filter="data")
    stamp.write_text(sha)
    return exe


def oracle_pure() -> Path:
    """pyyaml as the guest has it: the pinned sdist, hash-checked, of which
    only `lib/yaml/` and `PKG-INFO` are unpacked under build/oracle/pure/, `PKG-INFO` as
    `pyyaml-<version>.dist-info/METADATA` beside `yaml/`. A stamp holding the archive's hash marks a
    finished unpack. A missing or mismatched sdist raises RuntimeError, which oracle_available()
    turns into the oracle need unmet."""
    home = ORACLE_HOME / "pure"
    stamp = home / ".sha256"
    sha = paths.read_pin_list().get(PURE_SDIST)
    if sha is None:
        raise RuntimeError(f"{PURE_SDIST} is not pinned in downloads/SHA256SUMS")
    if stamp.is_file() and stamp.read_text() == sha:
        return home
    archive = paths.DOWNLOADS / PURE_SDIST
    if not archive.is_file():
        raise RuntimeError(f"downloads/{PURE_SDIST} is missing: run scripts/00_download.sh")
    if paths.sha256_file(archive) != sha:
        raise RuntimeError(f"downloads/{PURE_SDIST} does not match its pin")
    top = PURE_SDIST.removesuffix(".tar.gz")
    shutil.rmtree(home, ignore_errors=True)
    unpack = home / "unpack"
    with tarfile.open(archive) as t:
        wanted = [
            m
            for m in t.getmembers()
            if m.name.startswith(f"{top}/lib/yaml/") or m.name == f"{top}/PKG-INFO"
        ]
        t.extractall(unpack, members=wanted, filter="data")
    (unpack / top / "lib" / "yaml").rename(home / "yaml")
    (home / f"{top}.dist-info").mkdir()
    (unpack / top / "PKG-INFO").rename(home / f"{top}.dist-info" / "METADATA")
    shutil.rmtree(unpack)
    stamp.write_text(sha)
    return home


def oracle_env(seed: int | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        UV_CACHE_DIR=str(ORACLE_HOME / "cache"),
        UV_PROJECT_ENVIRONMENT=str(ORACLE_HOME / "venv"),
        UV_PYTHON=str(oracle_python()),
        UV_PYTHON_PREFERENCE="only-system",
    )
    env.pop("VIRTUAL_ENV", None)
    env["PYTHONPATH"] = str(oracle_pure())  # pyyaml's pure tree, as the guest has it
    # matplotlib uses its own fonts only, as the guest does: natively it
    # would otherwise list every font of the machine.
    env["MPL_IGNORE_SYSTEM_FONTS"] = "1"
    # One BLAS thread, so the oracle's sums are taken in one order.
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["VECLIB_MAXIMUM_THREADS"] = "1"
    # One OpenMP thread: the native scikit-learn wheel has OpenMP, the guest has none, and one
    # thread takes its sums in one order (a guard: the draft's output was the
    # same without it).
    env["OMP_NUM_THREADS"] = "1"
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
    except (OSError, RuntimeError):
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
    env = oracle_env(seed)
    env["MPLCONFIGDIR"] = str(base / "mplconfig")  # fresh for every run: no font cache carried over
    r = subprocess.run(
        oracle_command(str(script(job)), str(data), str(out), offline=offline),
        env=env,
        capture_output=True,
        check=False,
    )
    if r.returncode != 0:
        tail = r.stderr.decode(errors="replace").strip().splitlines()[-1:] or [""]
        raise RuntimeError(f"{job}: the oracle exited {r.returncode}: {tail[0]}")
    return render(r.stdout, out)


def run_in_guest(guest, job: str, **kw) -> bytes:
    """One run of a job on the plain binary through the judge's guest; the rendered output. `kw`
    goes to the guest (a job that imports matplotlib passes its cache folder and its data grant)."""
    files = {f"/jobs/{job}.py": script(job).read_bytes()}
    files.update({f"/data/{n}": src.read_bytes() for n, src in DATA.items()})
    files["/out/.keep"] = b""
    r = guest("plain", [f"/jobs/{job}.py", "/data", "/out"], files=files, **kw)
    assert r.exit_code == 0, f"{job}: {r.describe()}"
    (r.root / "out" / ".keep").unlink()
    return render(r.stdout, r.root / "out")
