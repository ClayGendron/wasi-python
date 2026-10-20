"""The runner checks a set it finds against the set's own SHA256SUMS before using it (spec 087,
Decision 10, from the 0.1.0 security review's S3). A set the caller passes is the caller's own."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

import wasi_python
from harness import wat
from wasi_python import ArtifactsMissing, runner


def _sums(folder: Path) -> None:
    names = ["MANIFEST", "python-snapshot.wasm", "python-stdlib.zip", "python.wasm"]
    lines = [f"{hashlib.sha256((folder / n).read_bytes()).hexdigest()}  {n}\n" for n in names]
    (folder / "SHA256SUMS").write_text("".join(lines))


@pytest.fixture
def found(work, monkeypatch) -> Path:
    """A small set at $WASI_PYTHON_ARTIFACTS: a door-probing snapshot, an empty zip, its sums."""
    folder = work / "set"
    wat.build(folder, "python-snapshot.wasm", wat.SNAPSHOT)
    wat.build(folder, "python.wasm", wat.PLAIN_REACTOR)
    (folder / "MANIFEST").write_text("python 3.15.0\n")
    with zipfile.ZipFile(folder / "python-stdlib.zip", "w"):
        pass
    _sums(folder)
    monkeypatch.setenv(wasi_python._ARTIFACTS_ENV, str(folder))
    return folder


def test_a_found_set_that_matches_its_sums_runs(found) -> None:
    assert runner.run([], cache_dir=False).exit_code == 101  # the door: no host


@pytest.mark.parametrize("name", ["python-snapshot.wasm", "python-stdlib.zip", "MANIFEST"])
def test_a_found_file_that_differs_from_its_sums_is_refused(found, name) -> None:
    before = runner.stats()["compiled"]
    path = found / name
    if name == "python-snapshot.wasm":
        wat.build(found, name, wat.COMMAND_EXIT_7)  # another program in its place
    elif name == "MANIFEST":
        path.write_text("python 3.15.0\nrecipe 0000 planted\n")
    else:
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("sitecustomize.py", "print('planted')\n")
    with pytest.raises(ArtifactsMissing, match=f"{name}.*SHA256SUMS"):
        runner.run([], cache_dir=False)
    assert runner.stats()["compiled"] == before  # refused before it is compiled


def test_a_found_set_without_sums_is_refused(found) -> None:
    (found / "SHA256SUMS").unlink()
    with pytest.raises(ArtifactsMissing, match="SHA256SUMS"):
        runner.run([], cache_dir=False)


def test_a_session_checks_a_found_set_too(found) -> None:
    wat.build(found, "python-snapshot.wasm", wat.COMMAND_EXIT_7)
    with pytest.raises(ArtifactsMissing, match="python-snapshot.wasm.*SHA256SUMS"):
        wasi_python.Session(cache_dir=False)


def test_a_set_the_caller_passes_is_its_own(found) -> None:
    """`run(artifacts=…)` takes the caller's four paths as they are, as the judge's door probes
    and older sets do: the caller chose them."""
    wat.build(found, "python-snapshot.wasm", wat.SNAPSHOT)
    (found / "SHA256SUMS").unlink()
    given = wasi_python.artifacts()
    assert runner.run([], artifacts=given, cache_dir=False).exit_code == 101
