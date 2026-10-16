"""The package imports, and `artifacts()` tells the truth about where the artifacts are."""

from __future__ import annotations

import pytest

import wasi_python


def test_version_is_a_string() -> None:
    assert isinstance(wasi_python.__version__, str)


def test_artifacts_are_found_or_explained() -> None:
    if (wasi_python.ARTIFACT_DIR / "MANIFEST").is_file():  # an installed wheel
        found = wasi_python.artifacts()
        assert all(p.is_file() for p in (found.snapshot, found.plain, found.stdlib_zip))
    else:  # a source checkout
        with pytest.raises(wasi_python.ArtifactsMissing, match="source checkout"):
            wasi_python.artifacts()
