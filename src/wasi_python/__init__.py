"""wasi_python: a static CPython for WebAssembly hosts, with numpy and pandas compiled in.

The wheel carries the runtime's artifacts and this module tells an embedder where they are::

    from wasi_python import artifacts

    paths = artifacts()
    paths.snapshot      # python.wasm with the stack pre-imported; starts in a few milliseconds
    paths.plain         # the same reactor without the snapshot, for debugging
    paths.stdlib_zip    # the stdlib plus numpy, pandas and their pure-Python dependencies
    paths.manifest      # every pinned source and recipe hash the build used

`artifacts()` looks, in order, at `$WASI_PYTHON_ARTIFACTS` (when set and not empty), in a source
checkout at `build/artifacts/` (what `scripts/build.sh` writes), and at the wheel's own
`artifacts/`: the harness's order. `run()` runs one
program in one call (the `run` extra; see `wasi_python.run`), and README.md documents the contract
any other embedder implements.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

__version__ = "0.1.0a3"

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
ARTIFACTS_ENV = "WASI_PYTHON_ARTIFACTS"
# A source checkout: <repo>/src/wasi_python/ beside <repo>/build/artifacts/ (and pyproject.toml).
_REPO = Path(__file__).resolve().parents[2]
CHECKOUT_ARTIFACT_DIR = (
    _REPO / "build" / "artifacts" if (_REPO / "pyproject.toml").is_file() else None
)


class ArtifactsMissing(RuntimeError):
    """Raised when the runtime's artifacts are not beside this module."""


@dataclass(frozen=True)
class Artifacts:
    """Absolute paths to the runtime's files inside an installed wheel."""

    snapshot: Path
    plain: Path
    stdlib_zip: Path
    manifest: Path


def artifact_dir() -> Path:
    """The directory holding the artifact set (spec 001, Decision 3)."""
    env = os.environ.get(ARTIFACTS_ENV)
    if env:  # set and not empty
        return Path(env).resolve()
    for d in (CHECKOUT_ARTIFACT_DIR, ARTIFACT_DIR):  # the harness's order (spec 003, Decision 10)
        if d is not None and (d / "MANIFEST").is_file():
            return d
    raise ArtifactsMissing(
        f"no runtime artifacts: ${ARTIFACTS_ENV} is unset, and neither {CHECKOUT_ARTIFACT_DIR} nor "
        f"{ARTIFACT_DIR} has a MANIFEST. Install the released wheel, or build with "
        "scripts/build.sh (see README.md)."
    )


def artifacts() -> Artifacts:
    """Locate the artifact set, or explain how to produce it."""
    d = artifact_dir()
    manifest = d / "MANIFEST"
    if not manifest.is_file():
        raise ArtifactsMissing(f"{d} has no MANIFEST (from ${ARTIFACTS_ENV})")
    return Artifacts(
        snapshot=d / "python-snapshot.wasm",
        plain=d / "python.wasm",
        stdlib_zip=d / "python-stdlib.zip",
        manifest=manifest,
    )


from .runner import Completed, Grant, run, run_async  # noqa: E402  (runner.py imports Artifacts from here)

__all__ = [
    "Artifacts",
    "ArtifactsMissing",
    "Completed",
    "Grant",
    "artifact_dir",
    "artifacts",
    "run",
    "run_async",
]
