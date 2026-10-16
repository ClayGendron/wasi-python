"""wasi_python: a static CPython for WebAssembly hosts, with numpy and pandas compiled in.

The wheel carries the runtime's artifacts and this module tells an embedder where they are::

    from wasi_python import artifacts

    paths = artifacts()
    paths.snapshot      # python.wasm with the stack pre-imported; starts in a few milliseconds
    paths.plain         # the same reactor without the snapshot, for debugging
    paths.stdlib_zip    # the stdlib plus numpy, pandas and their pure-Python dependencies
    paths.manifest      # every pinned source and recipe hash the build used

A source checkout has no artifacts; `artifacts()` then raises `ArtifactsMissing` with the build
command in its message. The host-call import the binary declares, and the runner that binds it,
are documented in README.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__version__ = "0.0.0"

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"


class ArtifactsMissing(RuntimeError):
    """Raised when the runtime's artifacts are not beside this module."""


@dataclass(frozen=True)
class Artifacts:
    """Absolute paths to the runtime's files inside an installed wheel."""

    snapshot: Path
    plain: Path
    stdlib_zip: Path
    manifest: Path


def artifacts() -> Artifacts:
    """Locate the bundled artifacts, or explain how to produce them."""
    manifest = ARTIFACT_DIR / "MANIFEST"
    if not manifest.is_file():
        raise ArtifactsMissing(
            f"no runtime artifacts under {ARTIFACT_DIR}; this is a source checkout. "
            "Install the released wheel, or build with scripts/ (see README.md)."
        )
    return Artifacts(
        snapshot=ARTIFACT_DIR / "python-snapshot.wasm",
        plain=ARTIFACT_DIR / "python.wasm",
        stdlib_zip=ARTIFACT_DIR / "python-stdlib.zip",
        manifest=manifest,
    )
