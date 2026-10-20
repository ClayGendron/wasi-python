"""The harness plugin (scoreboard, ratchet, acceptance) and pytester for its self-tests."""

from __future__ import annotations

import pytest

pytest_plugins = ["harness.plugin", "pytester"]

# Spec 082: an inline session's faulthandler plugin disables faulthandler at its end and enables it
# again, which puts back the handlers faulthandler first saw and drops any installed since (on
# Linux, wasmtime's, so the runner's guard refuses every later call that makes an engine).
NO_FAULTHANDLER = ("-p", "no:faulthandler")


@pytest.fixture
def pytester(pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch) -> pytest.Pytester:
    """pytest's own, but every session it runs in this process goes without faulthandler: its
    `inline_run`, which `runpytest` (in process) and the collecting helpers call, and its
    `parseconfig`, which `parseconfigure` calls. A subprocess session needs nothing."""
    inline_run, parseconfig = pytester.inline_run, pytester.parseconfig

    def inline_run_keeping_the_handlers(*args, **kwargs):
        return inline_run(*NO_FAULTHANDLER, *args, **kwargs)

    def parseconfig_keeping_the_handlers(*args):
        return parseconfig(*NO_FAULTHANDLER, *args)

    monkeypatch.setattr(pytester, "inline_run", inline_run_keeping_the_handlers)
    monkeypatch.setattr(pytester, "parseconfig", parseconfig_keeping_the_handlers)
    return pytester
