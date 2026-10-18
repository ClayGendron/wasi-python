"""Fixtures shared by the goal checks: the artifact set, and a guest runner over the judge's
driver."""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from harness import needs, paths

BINARIES = {"plain": "python.wasm", "snapshot": "python-snapshot.wasm"}
CACHE_ENV = "WASI_PYTHON_CACHE"


@pytest.fixture(scope="session", autouse=True)
def runner_cache_in_build():
    """The runner's compiled-module cache lives under build/, never in the user's cache
    (spec 001, Design)."""
    import os

    before = os.environ.get(CACHE_ENV)
    os.environ[CACHE_ENV] = str(paths.BUILD / "cwasm-cache")
    yield
    if before is None:
        os.environ.pop(CACHE_ENV, None)
    else:
        os.environ[CACHE_ENV] = before


NEED_OF = {"plain": "plain binary", "snapshot": "snapshot binary"}


@dataclass(frozen=True)
class ArtifactSet:
    dir: Path

    def path(self, name: str) -> Path:
        return self.dir / name

    def binary(self, which: str) -> Path:
        return self.dir / BINARIES[which]

    def manifest(self) -> paths.Manifest:
        return paths.parse_manifest((self.dir / "MANIFEST").read_text())


@pytest.fixture
def artifacts() -> ArtifactSet:
    needs.need("artifact dir")
    d = paths.artifact_dir()
    assert d is not None
    return ArtifactSet(d)


@pytest.fixture(scope="session")
def guest_workdir():
    paths.HARNESS_TMP.mkdir(parents=True, exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix="guest-", dir=paths.HARNESS_TMP))
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def guest(guest_workdir: Path, metric) -> Callable:
    """`guest(which, argv, files=…, env=…, host=…, fuel=…, stdlib=…)` runs the artifact once.

    It names its needs before it runs anything, so a check that uses it is `blocked`, never
    `fail`, when the artifact is absent. It records the run's fuel as the check's metric (the
    last run wins, so a check runs its measured program last). `stdlib` names another zip to
    grant in the artifact zip's place (spec 035, Decision 11)."""

    def run(which: str, argv: list[str], *, record: bool = True, stdlib: Path | None = None, **kw):
        needs.need("artifact dir", NEED_OF[which], "stdlib zip", "manifest", "wasmtime-py")
        from harness import guest as driver

        d = paths.artifact_dir()
        m = paths.parse_manifest((d / "MANIFEST").read_text())
        assert m.python, "MANIFEST has no python line"
        result = driver.run(
            d / BINARIES[which],
            argv,
            workdir=guest_workdir,
            python_version=m.python,
            stdlib=stdlib or d / "python-stdlib.zip",
            **kw,
        )
        if record:
            metric("fuel", result.fuel)
        return result

    return run
