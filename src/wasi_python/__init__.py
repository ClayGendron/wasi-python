"""wasi_python: a static CPython for WebAssembly hosts, with numpy, pandas and matplotlib inside.

One call runs one program in a fresh, sealed guest::

    from wasi_python import run

    done = run(["-c", "import pandas; print(pandas.__version__)"])
    done.exit_code, done.stdout

The wheel carries the runtime's artifacts, and `artifacts()` says where they are, for an
embedder that runs them through its own wasmtime binding::

    paths = artifacts()
    paths.snapshot      # python.wasm started, the stdlib's bootstrap imported (no package)
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

import threading

from . import runner as _runner
from ._artifacts import Artifacts, ArtifactsMissing, artifact_dir, artifacts
from .mounts import (
    Errno,
    FileFault,
    FileProvider,
    FileRecord,
    Mount,
    RefusedWrite,
    Stat,
    WritableFileProvider,
)
from .runner import (
    Completed,
    Defaults,
    Grant,
    Session,
    SessionEnded,
    run,
    run_async,
    stats,
)

__version__ = "0.1.0a8"

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
    "Session",
    "SessionEnded",
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
