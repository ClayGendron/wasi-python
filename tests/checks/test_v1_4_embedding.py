"""v1.4: an embedder preopens a directory, binds one function, and calls one export.

The guest-side checks use the judge's own driver, which does exactly that and nothing more;
the runner checks call `wasi_python.run`, the wheel's one-call embedding (spec 001)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from harness import needs

pytestmark = pytest.mark.goal("v1.4")
BINARY = pytest.mark.parametrize("which", ["plain", "snapshot"])


@BINARY
def test_door_without_a_host_says_so(guest, which) -> None:
    code = (
        "import _host\n"
        "try:\n"
        "    _host.call(b'x')\n"
        "    print('answered')\n"
        "except ConnectionRefusedError:\n"
        "    print('refused')\n"
        "print(_host.available())\n"
    )
    r = guest(which, ["-c", code])
    assert r.exit_code == 0, r.describe()
    assert r.text.split() == ["refused", "False"], r.text


@BINARY
def test_door_round_trips_bytes_through_a_host(guest, which) -> None:
    seen = []

    def host(frame: bytes) -> bytes:
        seen.append(frame)
        return frame[::-1]

    code = "import _host\nprint(_host.call(b'abc'), _host.available())\n"
    r = guest(which, ["-c", code], host=host)
    assert r.exit_code == 0, r.describe()
    assert r.text.strip() == "b'cba' True", r.text
    assert seen == [b"abc"], seen


@BINARY
def test_run_returns_the_exit_code(guest, which) -> None:
    r = guest(which, ["-c", "import sys; sys.exit(3)"])
    assert r.exit_code == 3, r.describe()


@BINARY
def test_run_reads_argv_and_environment_each_call(guest, which) -> None:
    code = "import os, sys; print(sys.argv[1:], os.environ.get('WASI_PYTHON_PROBE'))"
    for value in ("one", "two"):
        r = guest(which, ["-c", code, value], env={"WASI_PYTHON_PROBE": value})
        assert r.exit_code == 0, r.describe()
        assert r.text.strip() == f"['{value}'] {value}", r.text


NATIVE_MAIN = "['__builtins__', '__doc__', '__loader__', '__name__', '__package__', '__spec__']"
NATIVE_TRACEBACK = (
    "Traceback (most recent call last):\n"
    '  File "<string>", line 1, in <module>\n'
    "    1/0\n"
    "    ~^~\n"
    "ZeroDivisionError: division by zero\n"
)


@BINARY
def test_main_starts_as_native(guest, which) -> None:
    """A program's __main__ is CPython's, never holding the snapshot's build-time imports."""
    r = guest(which, ["-c", "print(sorted(globals()))"])
    assert r.exit_code == 0, r.describe()
    assert r.text.strip() == NATIVE_MAIN, r.text


@BINARY
def test_uncaught_errors_print_as_native(guest, which) -> None:
    """The user's frames only, through sys.excepthook, as CPython's -c prints them."""
    hook = "import sys\nsys.excepthook = lambda t, e, tb: print('hook', t.__name__)\n1/0\n"
    r = guest(which, ["-c", hook])
    assert (r.exit_code, r.text.strip()) == (1, "hook ZeroDivisionError"), r.describe()
    r = guest(which, ["-c", "1/0"])
    assert r.exit_code == 1, r.describe()
    assert r.stderr.decode(errors="replace") == NATIVE_TRACEBACK, r.stderr


@BINARY
def test_exit_status_is_a_process_status(guest, which) -> None:
    """SystemExit's code comes back as a POSIX process status would: 0 to 255."""
    codes = [guest(which, ["-c", f"raise SystemExit({c})"]).exit_code for c in (256, -1)]
    assert codes == [0, 255], codes


@BINARY
def test_unbuffered_output_survives_a_hard_exit(guest, which) -> None:
    """-u is honoured: what was printed is written before os._exit or a trap can lose it."""
    r = guest(which, ["-u", "-Xutf8", "-c", "print('kept'); import os; os._exit(0)"])
    assert (r.exit_code, r.text) == (0, "kept\n"), r.describe()


@BINARY
def test_a_program_sees_real_entropy_and_file_metadata(guest, which) -> None:
    """The constants the build pins while it snapshots never reach a program."""
    code = (
        "import os\n"
        "st = os.stat('/w/f')\n"
        "print(os.urandom(8) != bytes(8), st.st_ino != 0, st.st_mtime != 1767225600)\n"
    )
    r = guest(which, ["-c", code], files={"/w/f": b"x"})
    assert r.exit_code == 0, r.describe()
    assert r.text.split() == ["True", "True", "True"], r.text


def _runner():
    needs.need("runner", "artifact dir")
    import wasi_python

    return wasi_python.run


def _root(workdir: Path) -> Path:
    return Path(tempfile.mkdtemp(prefix="runner-", dir=workdir))


def test_runner_runs_a_program_in_one_call(guest_workdir) -> None:
    run = _runner()
    done = run(["-c", "print(1)"], root=_root(guest_workdir))
    assert (done.exit_code, done.stdout) in ((0, b"1\n"), (0, "1\n")), done


def test_runner_binds_a_host(guest_workdir) -> None:
    run = _runner()
    done = run(
        ["-c", "import _host; print(_host.call(b'abc'))"],
        root=_root(guest_workdir),
        host=lambda frame: frame[::-1],
    )
    assert done.exit_code == 0 and "cba" in str(done.stdout), done


def test_runner_stops_a_runaway_guest_by_fuel(guest_workdir) -> None:
    run = _runner()
    done = run(["-c", "while True: pass"], root=_root(guest_workdir), fuel=10**9)
    assert done.trapped and done.exit_code is None, done
