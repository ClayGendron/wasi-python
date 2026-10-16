"""The package imports, and a source checkout says plainly that it holds no artifacts."""

from __future__ import annotations

import pytest

import wasi_python


def test_version_is_a_string() -> None:
    assert isinstance(wasi_python.__version__, str)


def test_source_checkout_has_no_artifacts() -> None:
    with pytest.raises(wasi_python.ArtifactsMissing, match="source checkout"):
        wasi_python.artifacts()
