"""The home's hand-off nobody waits for, `post`: it runs on the home, a `BaseException` from it
stops the call, and once the home has stopped it runs nothing. Stand-ins only: no wasm runs here,
and nothing is timed; the guest's `call` after its `post` orders the two through the one inbox."""

from __future__ import annotations

import threading

import pytest

from wasi_python import _home


class Stop(BaseException):
    """The embedder's own BaseException."""


def test_post_runs_on_the_home() -> None:
    """What the guest thread posts runs on the thread that serves it, before the hand-off the
    guest posts after it."""
    home = _home._Home()
    ran: list[tuple[str, int]] = []

    def guest() -> None:
        home.post(lambda: ran.append(("post", threading.get_ident())))
        home.call(lambda: ran.append(("call", threading.get_ident())))

    _home._on_guest_thread("run", home, None, guest)
    me = threading.get_ident()
    assert ran == [("post", me), ("call", me)]


def test_a_base_exception_from_a_post_stops_the_home() -> None:
    """The posted function's `BaseException` is the home's stop: the guest's next hand-off is
    refused, and the call raises it."""
    home = _home._Home()
    after: list[str] = []

    def stop() -> None:
        raise Stop()

    def guest() -> None:
        home.post(stop)
        home.call(lambda: after.append("ran"))

    with pytest.raises(Stop):
        _home._on_guest_thread("run", home, None, guest)
    assert after == []


def test_a_post_after_a_stop_does_nothing() -> None:
    """A stopped home takes no post: nothing is queued, so nothing of the embedder's runs."""
    home = _home._Home()
    home.stop(RuntimeError("stopped"))
    home.post(lambda: pytest.fail("a post ran on a stopped home"))
    assert home.inbox.empty()
