"""An inline pytest session keeps the signal handlers it found.

pytest's faulthandler plugin, in a session run inside this process (pytester's `runpytest`), calls
`faulthandler.disable()` at its end and then `enable()` again. `disable()` puts back the handlers
faulthandler saw when the outer session enabled it, so any handler installed in between is gone:
on Linux, wasmtime's, which the runner's guard then misses.
The judge's `pytester` (tests/conftest.py) runs every inline session with `-p no:faulthandler`."""

from __future__ import annotations

import ctypes
import faulthandler
import signal
import sys

import pytest

posix = pytest.mark.skipif(sys.platform == "win32", reason="sigaction is POSIX's")

STAND_IN = signal.SIGABRT  # one of faulthandler's; abort() still ends the process if it is ignored
SIG_IGN = 1


def _sigaction():
    libc = ctypes.CDLL(None, use_errno=True)
    libc.sigaction.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
    libc.sigaction.restype = ctypes.c_int
    return libc.sigaction


def _read(sigaction, signum: int) -> ctypes.Array:
    """The installed `struct sigaction`, raw (1024 bytes is larger than any libc's)."""
    buf = (ctypes.c_char * 1024)()
    assert sigaction(signum, None, buf) == 0, ctypes.get_errno()
    return buf


def _handler(sigaction, signum: int) -> int:
    """The installed handler: the first word of `struct sigaction` on glibc, musl and macOS."""
    return ctypes.c_void_p.from_buffer(_read(sigaction, signum)).value or 0


def _handler_after(session) -> int:
    """SIGABRT's installed handler after `session()` runs with a stand-in, `SIG_IGN` set through
    sigaction after faulthandler (as wasmtime's is, at the first engine). The whole struct is put
    back after, and faulthandler is switched on (then off) only if the outer session has not."""
    sigaction = _sigaction()
    enabled_here = not faulthandler.is_enabled()  # the judge's own session has it on already
    if enabled_here:
        faulthandler.enable(file=sys.__stderr__)
    saved = _read(sigaction, STAND_IN)
    try:
        stand_in = (ctypes.c_char * len(saved)).from_buffer_copy(saved)
        ctypes.c_void_p.from_buffer(stand_in).value = SIG_IGN
        assert sigaction(STAND_IN, stand_in, None) == 0, ctypes.get_errno()
        assert _handler(sigaction, STAND_IN) == SIG_IGN
        session()
        return _handler(sigaction, STAND_IN)
    finally:
        assert sigaction(STAND_IN, saved, None) == 0, ctypes.get_errno()
        if enabled_here:
            faulthandler.disable()


@posix
def test_an_inline_session_keeps_a_handler_installed_after_faulthandler(pytester) -> None:
    """A handler installed after faulthandler is still the installed one after an inline session
    (`runpytest`, through pytester's `inline_run`). The stand-in plays wasmtime's part on every
    POSIX host."""

    def session():
        pytester.makepyfile(test_inner="def test_ok():\n    pass\n")
        result = pytester.runpytest()
        assert result.ret == 0, result.stdout.str()[-2000:]

    after = _handler_after(session)
    assert after == SIG_IGN, f"the inline session replaced the handler: {after:#x}"


@posix
def test_a_parseconfigure_keeps_a_handler_installed_after_faulthandler(pytester) -> None:
    """The same through pytester's `parseconfig`: a config `parseconfigure` configures runs the
    plugins' `pytest_configure`, and its unconfigure their `pytest_unconfigure`."""

    def session():
        config = pytester.parseconfigure()
        config._ensure_unconfigure()

    after = _handler_after(session)
    assert after == SIG_IGN, f"the configured session replaced the handler: {after:#x}"


def test_an_inline_session_after_an_engine_leaves_the_guard_ready(pytester) -> None:
    """End to end: an engine, then an inline session, and the
    runner's guard still finds wasmtime's handlers. Only Linux has the guard (macOS uses Mach
    ports, Windows a vectored handler), so elsewhere both reads are None by design."""
    import wasmtime

    from wasi_python import _platform

    wasmtime.Engine()  # wasmtime installs its handlers once, at the first engine in the process
    before = _platform.PLATFORM.trap_handlers_ready()
    assert before is None, f"the guard refused before the inline session, on {before}"
    pytester.makepyfile(test_inner="def test_ok():\n    pass\n")
    result = pytester.runpytest()
    assert result.ret == 0, result.stdout.str()[-2000:]
    after = _platform.PLATFORM.trap_handlers_ready()
    assert after is None, f"after an inline session the guard refuses, on {after}"
