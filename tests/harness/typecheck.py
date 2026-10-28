"""The type checker's passes over the runner's package, named in this one place.

The package is read under two platforms, each named, so every host gives one verdict. The Linux
pass is mypy as pyproject.toml configures it: every module but the Windows half, whose
signatures it reads silently where the platform module imports it. The Windows pass reads that
one module with win32's stubs, where `ctypes.WinDLL`, `msvcrt.locking` and `winreg` exist, and
reads the modules it imports for their types only, reporting none of their errors (under win32
those are the POSIX calls). Each module is read by exactly one pass, so no error is reported
twice and no line needs a suppression the other platform would call unused.

The rules check reads PASSES through `run`, and so does a local run of this file
(`uv run python tests/harness/typecheck.py`), so the check and the command cannot drift.
Standard library only, so the file runs as a script without the harness on the path."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

WINDOWS_HALF = "src/wasi_python/_platform_windows.py"

# (the pass's name, mypy's arguments after `-m mypy`), each run in the repository's root.
PASSES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("linux", ("--no-error-summary",)),
    (
        "win32",
        (
            "--platform",
            "win32",
            "--follow-imports",
            "silent",
            "--cache-dir",
            "build/.mypy_cache_win32",  # its own, so the two passes keep each other's entries
            "--no-error-summary",
            WINDOWS_HALF,
        ),
    ),
)


def run(root: Path) -> list[str]:
    """Every error line of every pass, each prefixed by its pass's name (`win32: src/...`), and
    one finding for a pass that exits 2 (a crash or a configuration error) or exits 1 with no
    error line. An empty list means both passes are clean."""
    findings: list[str] = []
    for name, args in PASSES:
        r = subprocess.run(
            [sys.executable, "-m", "mypy", *args],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        errors = [f"{name}: {line}" for line in r.stdout.splitlines() if ": error: " in line]
        findings += errors
        said = (r.stdout + r.stderr).strip().splitlines()[:3]
        if r.returncode == 2:
            findings.append(f"{name}: mypy exited 2 (a crash or a configuration error): {said}")
        elif r.returncode != 0 and not errors:
            findings.append(f"{name}: mypy exited {r.returncode} with no error line: {said}")
    return findings


if __name__ == "__main__":
    found = run(Path(__file__).resolve().parents[2])
    print("\n".join(found) or "both passes are clean")
    sys.exit(1 if found else 0)
