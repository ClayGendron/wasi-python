"""Fixtures for the harness self-tests."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from harness import paths


@pytest.fixture
def work() -> Path:
    """A fresh directory under build/harness/ (never the system temp dir: §4.8)."""
    paths.HARNESS_TMP.mkdir(parents=True, exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix="unit-", dir=paths.HARNESS_TMP))
    yield d
    shutil.rmtree(d, ignore_errors=True)
