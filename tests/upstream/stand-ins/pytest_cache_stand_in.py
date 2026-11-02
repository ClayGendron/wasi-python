"""A test-side stand-in for pytest's cache, for a family whose fixtures read `config.cache`: the
driver runs pytest without its cache plugin, since the stage is read-only and a cache would carry
state from one session to the next. This plugin gives `config.cache` as a dictionary held in
memory for the one session, starting from the family's .ini option `session_cache`, one
`key=value` per line. imageio's `test_images` fixture asks the cache where its test images are,
and would otherwise try to make that folder in the read-only stage. It is staged into the family's
kit only, and loaded by the family's .ini with `-p`."""

import pytest


class _SessionCache:
    def __init__(self, values: dict[str, object]) -> None:
        self._values = values

    def get(self, key: str, default):
        return self._values.get(key, default)

    def set(self, key: str, value) -> None:
        self._values[key] = value


def pytest_addoption(parser) -> None:
    parser.addini("session_cache", "the session cache's first values, key=value", type="linelist")


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config) -> None:
    if not hasattr(config, "cache"):
        lines = config.getini("session_cache")
        config.cache = _SessionCache(dict(line.split("=", 1) for line in lines))
