"""The judge's `--tier` option, loaded by pytest from this package's pytest11 entry point.

pytest parses the command line before it reads `tests/conftest.py` when no path is given, so an
option the harness plugin registered there would be unknown to `uv run pytest --tier release`.
An entry point is loaded first. It imports nothing from the harness, since the harness is
importable only once pytest has put `tests/` on the path; the harness reads the option by name.
"""

from __future__ import annotations

import pytest

TIERS = ("normal", "release")  # the harness's scoreboard judges these two; a unit row holds it


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.getgroup("progress", "the progress harness").addoption(
        "--tier",
        choices=TIERS,
        help="normal (the default) leaves the release-tier checks unrun; release runs both tiers",
    )
