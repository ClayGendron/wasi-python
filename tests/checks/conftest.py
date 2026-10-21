"""Fixtures shared by the goal checks: the artifact set, and a guest runner over the judge's
driver."""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from harness import litter, needs, paths

BINARIES = {"plain": "python.wasm", "snapshot": "python-snapshot.wasm"}
CACHE_ENV = "WASI_PYTHON_CACHE"


@pytest.fixture(scope="session", autouse=True)
def runner_cache_in_build():
    """The runner's compiled-module cache lives under build/, never in the user's cache."""
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
    # Outside the home folder on darwin, where macOS writes .DS_Store into a writable root the
    # seal cannot close; build/harness elsewhere.
    d = Path(tempfile.mkdtemp(prefix="guest-", dir=paths.guest_tmp()))
    yield d
    litter.remove(d)  # its matplotlib data is sealed


@pytest.fixture
def guest(guest_workdir: Path, metric, tmp_path_factory: pytest.TempPathFactory) -> Callable:
    """`guest(which, argv, files=…, env=…, host=…, fuel=…, stdlib=…)` runs the artifact once.

    It names its needs before it runs anything, so a check that uses it is `blocked`, never
    `fail`, when the artifact is absent. It records the run's fuel as the check's metric (the
    last run wins, so a check runs its measured program last). `stdlib` names another zip to
    grant in the artifact zip's place. A recorded run whose inputs name a
    host path (under the checkout, the system's temp folder or pytest's) is refused:
    its fuel would depend on where they are; a run given one passes `record=False`."""

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
            measured=record,
            host_roots=(tmp_path_factory.getbasetemp(),),
            **kw,
        )
        if record:
            metric("fuel", result.fuel)
        return result

    return run


@pytest.fixture
def guest_turns(guest_workdir: Path) -> Callable:
    """`guest_turns(which, host=…, preopens=…)` is one instance of the artifact kept across calls,
    driven raw by the judge's own driver. Closed at the end."""
    made = []

    def make(which: str, **kw):
        needs.need("artifact dir", NEED_OF[which], "stdlib zip", "manifest", "wasmtime-py")
        from harness import guest as driver

        d = paths.artifact_dir()
        m = paths.parse_manifest((d / "MANIFEST").read_text())
        assert m.python, "MANIFEST has no python line"
        t = driver.turns(
            d / BINARIES[which],
            workdir=guest_workdir,
            python_version=m.python,
            stdlib=d / "python-stdlib.zip",
            **kw,
        )
        made.append(t)
        return t

    yield make
    for t in made:
        t.close()
