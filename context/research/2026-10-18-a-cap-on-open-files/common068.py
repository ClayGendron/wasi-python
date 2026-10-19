"""Shared by spec 068's probes: the frozen artifact set, and a count of this process's descriptors."""

import os
import sys
from pathlib import Path

from wasi_python import Artifacts

SET = Path(
    os.environ.get(
        "WASI_PYTHON_ARTIFACTS",
        "/Users/claygendron/Git/Repos/wasi_python/build/sets/s-4eb5418a2b1bb553-c353b1d9",
    )
)
A = Artifacts(SET / "python-snapshot.wasm", SET / "python.wasm", SET / "python-stdlib.zip", SET / "MANIFEST")


def host_fds() -> int:
    """Descriptors this process holds now (macOS and Linux: one entry per open descriptor)."""
    where = "/dev/fd" if sys.platform == "darwin" else "/proc/self/fd"
    return len(os.listdir(where)) - 1  # less the one listdir itself holds
