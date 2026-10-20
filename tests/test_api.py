"""The package imports, and `artifacts()` tells the truth about where the artifacts are."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

import wasi_python
from wasi_python import _artifacts


def test_version_is_a_string() -> None:
    assert isinstance(wasi_python.__version__, str)


def _set(d: Path) -> Path:
    d.mkdir(parents=True)
    (d / "MANIFEST").write_text("python 3.14.8\n")
    return d


def test_artifacts_resolve_in_the_harness_order(tmp_path, monkeypatch) -> None:
    """$WASI_PYTHON_ARTIFACTS when set and not empty, then a checkout's build/artifacts/, then
    the wheel's own copy: the order the harness uses (spec 001, Decision 3)."""
    env, wheel, checkout = (_set(tmp_path / n) for n in ("env", "wheel", "checkout"))
    monkeypatch.setattr(_artifacts, "_ARTIFACT_DIR", wheel)
    monkeypatch.setattr(_artifacts, "_CHECKOUT_ARTIFACT_DIR", checkout)
    monkeypatch.setenv(_artifacts._ARTIFACTS_ENV, str(env))
    assert wasi_python.artifacts().manifest == env / "MANIFEST"
    monkeypatch.setenv(_artifacts._ARTIFACTS_ENV, "")
    assert wasi_python.artifacts().plain == checkout / "python.wasm"
    monkeypatch.delenv(_artifacts._ARTIFACTS_ENV)
    assert wasi_python.artifacts().plain == checkout / "python.wasm"
    (checkout / "MANIFEST").unlink()
    assert wasi_python.artifacts().snapshot == wheel / "python-snapshot.wasm"


def test_missing_artifacts_are_explained(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv(_artifacts._ARTIFACTS_ENV, raising=False)
    monkeypatch.setattr(_artifacts, "_ARTIFACT_DIR", tmp_path / "wheel")
    monkeypatch.setattr(_artifacts, "_CHECKOUT_ARTIFACT_DIR", tmp_path / "checkout")
    with pytest.raises(wasi_python.ArtifactsMissing, match="scripts/build.sh"):
        wasi_python.artifacts()


def _installed(tmp_path: Path, where: str, project: str) -> tuple[Path, Path, Path]:
    """A copy of the package at `proj/<where>/wasi_python`, as `pip install --target` or vendoring
    leaves it, with its own set; the project's pyproject.toml names `project`, and a planted set
    with a MANIFEST waits at `proj/build/artifacts`, where a guest with a writable grant at
    `proj/build` could write one (the 0.1.0 security review's S3)."""
    proj = tmp_path / "proj"
    package = proj / where / "wasi_python"
    package.mkdir(parents=True)
    for source in Path(wasi_python.__file__).parent.glob("*.py"):
        (package / source.name).write_bytes(source.read_bytes())
    own = _set(package / "artifacts")
    planted = _set(proj / "build" / "artifacts")
    (proj / "pyproject.toml").write_text(f'[project]\nname = "{project}"\nversion = "1"\n')
    return package.parent, own, planted


def _found(path_entry: Path) -> str:
    env = {k: v for k, v in os.environ.items() if k != _artifacts._ARTIFACTS_ENV}
    code = "import sys; sys.path.insert(0, sys.argv[1]); import wasi_python; "
    code += "print(wasi_python.artifact_dir())"
    out = subprocess.run(
        [sys.executable, "-I", "-c", code, str(path_entry)],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return out.stdout.strip()


@pytest.mark.parametrize(
    "where, project",
    [("deps", "someproj"), ("deps", "wasi-python"), ("src", "someproj")],
    ids=["target install", "target install in a wasi-python project", "vendored under src"],
)
def test_an_installed_copy_ignores_a_neighbouring_set(tmp_path, where, project) -> None:
    """Spec 087, Decision 10 (S3): only a source checkout, the package at `<repo>/src/wasi_python`
    beside a pyproject.toml that names wasi-python, prefers `<repo>/build/artifacts`. A copy
    installed or vendored anywhere else uses its own set and never a neighbouring one."""
    entry, own, planted = _installed(tmp_path, where, project)
    assert _found(entry) == str(own.resolve()), planted


def test_a_source_checkout_prefers_its_build(tmp_path) -> None:
    """Spec 087, Decision 10: the layout of this repository still finds its build's set."""
    entry, own, planted = _installed(tmp_path, "src", "wasi-python")
    assert _found(entry) == str(planted.resolve()), own
