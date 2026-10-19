"""wasi_python: a static CPython for WebAssembly hosts, with numpy, pandas and matplotlib inside.

One call runs one program in a fresh, sealed guest::

    from wasi_python import run

    done = run(["-c", "import pandas; print(pandas.__version__)"])
    done.exit_code, done.stdout

The wheel carries the runtime's artifacts, and `artifacts()` says where they are, for an
embedder that runs them through its own wasmtime binding::

    paths = artifacts()
    paths.snapshot      # python.wasm with the stack pre-imported; starts in a few milliseconds
    paths.plain         # the same reactor without the snapshot, for debugging
    paths.stdlib_zip    # the stdlib plus the packages' pure-Python parts
    paths.manifest      # every pinned source and recipe hash the build used

The public API is this module's `__all__`, the module `wasi_python.tools` (host functions a
guest may call), the `wasi-python` command, and the environment variables
`WASI_PYTHON_ARTIFACTS` and `WASI_PYTHON_CACHE`. Everything else is internal, the modules
`runner`, `mounts` and `cli` included, and may change in any release. Importing this module
never loads wasmtime-py; `run` does. README.md's "API reference" lists every public name and
the promise each release keeps.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path

__version__ = "0.1.0a7"

_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
_ARTIFACTS_ENV = "WASI_PYTHON_ARTIFACTS"
# A source checkout: <repo>/src/wasi_python/ beside <repo>/build/artifacts/ (and pyproject.toml).
_REPO = Path(__file__).resolve().parents[2]
_CHECKOUT_ARTIFACT_DIR = (
    _REPO / "build" / "artifacts" if (_REPO / "pyproject.toml").is_file() else None
)


class ArtifactsMissing(RuntimeError):
    """Raised when there is no usable artifact set; the message says how to get one."""


@dataclass(frozen=True)
class Artifacts:
    """The artifact set's four files, made by `artifacts()`, or by you for `run(artifacts=…)`.

    Attributes:
        snapshot: The snapshot binary, python-snapshot.wasm: the reactor with the stack
            pre-imported.
        plain: The plain reactor, python.wasm, without the snapshot.
        stdlib_zip: The stdlib zip, python-stdlib.zip, which every guest sees read-only at
            /usr/local/lib.
        manifest: The MANIFEST: every pinned source and recipe hash the build used.
    """

    snapshot: Path
    plain: Path
    stdlib_zip: Path
    manifest: Path


def artifact_dir() -> Path:
    """The folder holding the artifact set.

    It is `$WASI_PYTHON_ARTIFACTS` when that is set and not empty; else a source checkout's
    build/artifacts/ when it holds a MANIFEST; else the wheel's own artifacts/ when it holds one.

    Raises:
        ArtifactsMissing: None of the three is there.
    """
    # The harness's order (spec 001, Decision 3; spec 003, Decision 10).
    env = os.environ.get(_ARTIFACTS_ENV)
    if env:  # set and not empty
        return Path(env).resolve()
    for d in (_CHECKOUT_ARTIFACT_DIR, _ARTIFACT_DIR):
        if d is not None and (d / "MANIFEST").is_file():
            return d
    raise ArtifactsMissing(
        f"no runtime artifacts: ${_ARTIFACTS_ENV} is unset, and neither "
        f"{_CHECKOUT_ARTIFACT_DIR} nor {_ARTIFACT_DIR} has a MANIFEST. Install the released "
        "wheel, or build with scripts/build.sh (see README.md)."
    )


def artifacts() -> Artifacts:
    """The artifact set's paths, in the folder `artifact_dir()` names.

    Raises:
        ArtifactsMissing: There is no artifact set, or its folder has no MANIFEST; the message
            says how to get one.
    """
    d = artifact_dir()
    manifest = d / "MANIFEST"
    if not manifest.is_file():
        raise ArtifactsMissing(f"{d} has no MANIFEST (from ${_ARTIFACTS_ENV})")
    return Artifacts(
        snapshot=d / "python-snapshot.wasm",
        plain=d / "python.wasm",
        stdlib_zip=d / "python-stdlib.zip",
        manifest=manifest,
    )


# Last: runner.py imports Artifacts from here.
from . import runner as _runner  # noqa: E402
from .mounts import (  # noqa: E402
    Errno,
    FileFault,
    FileProvider,
    FileRecord,
    Mount,
    RefusedWrite,
    Stat,
    WritableFileProvider,
)
from .runner import Completed, Defaults, Grant, run, run_async, stats  # noqa: E402

# set_defaults swaps the binding `run` reads, and reads the old one, under this lock (spec 049).
_defaults_lock = threading.Lock()


def defaults() -> Defaults:
    """The `Defaults` a call reads now: the limits it has for each one it does not name.

    On import they are 1 GiB of memory, a 60 s deadline, 16 MiB of output per stream, 10,000
    file calls, 1,000 tool calls, and as many `run_async` workers as the machine has CPUs, at
    most 8.
    """
    return _runner._current_defaults()


def set_defaults(new: Defaults) -> Defaults:
    """Replace the `Defaults` that calls read, and return the previous ones.

    A call reads the defaults once, when it is made, so a call already made keeps what it read.
    The swap and the read of the old value happen under one lock, so two threads that race each
    get a distinct previous value and neither loses a restore. The usual change is one field::

        set_defaults(dataclasses.replace(defaults(), async_workers=4))

    A new `async_workers` applies to `run_async` calls submitted afterwards: the next one
    without an `executor` makes a pool of the new size, whatever limits it read. Calls already
    running or queued on the old pool still run there, so for a while both pools' workers may
    run guests (after 8 to 4, up to 12 at once).

    Args:
        new: The limits calls read from now on, already checked by `Defaults`.

    Raises:
        TypeError: `new` is not a `Defaults`.
    """
    if not isinstance(new, Defaults):
        raise TypeError(f"set_defaults takes a Defaults; got {type(new).__name__}")
    with _defaults_lock:
        old = _runner.DEFAULTS
        _runner.DEFAULTS = new
    return old


__all__ = [
    "Artifacts",
    "ArtifactsMissing",
    "Completed",
    "Defaults",
    "Errno",
    "FileFault",
    "FileProvider",
    "FileRecord",
    "Grant",
    "Mount",
    "RefusedWrite",
    "Stat",
    "WritableFileProvider",
    "artifact_dir",
    "artifacts",
    "defaults",
    "run",
    "run_async",
    "set_defaults",
    "stats",
]
