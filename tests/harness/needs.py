"""The fixed vocabulary of needs (spec 002, Decision 5).

A check that cannot run calls `need(name)`. The call skips only when the need's predicate is
false, with the reason `needs: <name>`; the plugin re-evaluates the predicate and turns a skip
that names a met need, or no known need, into a failure. Each need names the document that
provides it, so the scoreboard can say what to do next.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass

import pytest

from harness import paths

PREFIX = "needs: "


@dataclass(frozen=True)
class Need:
    name: str
    met: Callable[[], bool]
    provided_by: str


def _artifact_file(name: str) -> Callable[[], bool]:
    def met() -> bool:
        d = paths.artifact_dir()
        return d is not None and (d / name).is_file()

    return met


def _wasmtime() -> bool:
    try:
        import wasmtime  # noqa: F401
    except ImportError:
        return False
    return True


def _runner() -> bool:
    import wasi_python

    return callable(getattr(wasi_python, "run", None))


def _wheel() -> bool:
    return any(paths.DIST.glob("wasi_python-*.whl"))


def _three_systems() -> bool:
    from harness import scoreboard

    d = paths.artifact_dir()
    wasm = d / "python.wasm" if d else None
    if wasm is None or not wasm.is_file():
        return False
    return scoreboard.systems_that_passed(paths.HISTORY, paths.sha256_file(wasm)) >= {
        "linux",
        "darwin",
        "win32",
    }


def _oracle() -> bool:
    from harness import jobs

    return jobs.oracle_available()


def _reference_build() -> bool:
    return (paths.REFERENCE_BUILD / "python.wasm").is_file()


def _prior_art() -> bool:
    return any(p.is_dir() for p in paths.PRIOR_ART.iterdir()) if paths.PRIOR_ART.is_dir() else False


def _git() -> bool:
    try:
        r = subprocess.run(
            ["git", "-C", str(paths.REPO), "rev-parse", "HEAD"], capture_output=True, check=False
        )
    except OSError:
        return False
    return r.returncode == 0


def _source_tree(component: str) -> Callable[[], bool]:
    def met() -> bool:
        from harness import pins

        return pins.source_pair(component) is not None

    return met


SPEC_001 = "context/specifications/001-the-neutral-host-door-and-the-runner.md"
SPEC_003 = "context/specifications/003-the-pinned-build-end-to-end.md"
REPRO_MEMO = "context/research/2026-10-16-reproducible-builds-on-linux.md"
SPEC_002 = "context/specifications/002-the-progress-harness.md"
README_NEXT = "README.md (Next, item 4)"

SOURCE_COMPONENTS = ("cpython", "numpy", "pandas", "zlib")

VOCABULARY: dict[str, Need] = {
    n.name: n
    for n in [
        Need("artifact dir", lambda: paths.artifact_dir() is not None, SPEC_003),
        Need("plain binary", _artifact_file("python.wasm"), SPEC_003),
        Need("snapshot binary", _artifact_file("python-snapshot.wasm"), SPEC_003),
        Need("stdlib zip", _artifact_file("python-stdlib.zip"), SPEC_003),
        Need("manifest", _artifact_file("MANIFEST"), SPEC_003),
        Need("wasmtime-py", _wasmtime, SPEC_002),
        Need("runner", _runner, SPEC_001),
        Need("wheel", _wheel, README_NEXT),
        Need("three systems", _three_systems, README_NEXT),
        Need("oracle", _oracle, SPEC_002),
        Need("reference build", _reference_build, SPEC_002),
        Need("prior-art clones", _prior_art, "context/prior_art/README.md"),
        Need("git", _git, "-"),
        *[Need(f"source tree {c}", _source_tree(c), REPRO_MEMO) for c in SOURCE_COMPONENTS],
    ]
}


def need(*names: str) -> None:
    """Skip the calling check unless every named need is met; report the first unmet one."""
    for name in names:
        n = VOCABULARY[name]  # a KeyError here is a harness bug, and fails loudly
        if not n.met():
            pytest.skip(PREFIX + name)


def parse_reason(reason: str) -> str | None:
    """The need named by a skip reason, or None when the reason names no need."""
    text = reason.strip()
    if text.startswith("Skipped: "):
        text = text[len("Skipped: ") :]
    if not text.startswith(PREFIX):
        return None
    return text[len(PREFIX) :].strip()
