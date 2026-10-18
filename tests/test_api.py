"""The package imports, and `artifacts()` tells the truth about where the artifacts are."""

from __future__ import annotations

from pathlib import Path

import pytest

import wasi_python


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
    monkeypatch.setattr(wasi_python, "_ARTIFACT_DIR", wheel)
    monkeypatch.setattr(wasi_python, "_CHECKOUT_ARTIFACT_DIR", checkout)
    monkeypatch.setenv(wasi_python._ARTIFACTS_ENV, str(env))
    assert wasi_python.artifacts().manifest == env / "MANIFEST"
    monkeypatch.setenv(wasi_python._ARTIFACTS_ENV, "")
    assert wasi_python.artifacts().plain == checkout / "python.wasm"
    monkeypatch.delenv(wasi_python._ARTIFACTS_ENV)
    assert wasi_python.artifacts().plain == checkout / "python.wasm"
    (checkout / "MANIFEST").unlink()
    assert wasi_python.artifacts().snapshot == wheel / "python-snapshot.wasm"


def test_missing_artifacts_are_explained(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv(wasi_python._ARTIFACTS_ENV, raising=False)
    monkeypatch.setattr(wasi_python, "_ARTIFACT_DIR", tmp_path / "wheel")
    monkeypatch.setattr(wasi_python, "_CHECKOUT_ARTIFACT_DIR", tmp_path / "checkout")
    with pytest.raises(wasi_python.ArtifactsMissing, match="scripts/build.sh"):
        wasi_python.artifacts()
