"""The guest's stdout and stderr: how a call captures them (a pipe the runner reads on POSIX, the
callback on Windows), the cap cut to the byte inside a piece, the two streams kept apart, every
byte written before a hard exit, and no thread of the call left behind, even when every
descriptor is above 1,023 or a forked child holds a copy of the call's. The capture's kind is
counted through the process's observer; bytes, names, keys and threads are counted, nothing is
timed. Each row that runs a guest needs the artifact set."""

from __future__ import annotations

import os
import subprocess
import sys
import threading

import pytest

from harness import needs
from wasi_python._process import process

POSIX = os.name == "posix"
MIB = 1 << 20
# One mebibyte to stdout through the unbuffered descriptor, every byte of it: a hard exit does
# not flush Python's buffered stdout, and a write may take less than it was given.
WRITE_MIB = (
    "import os\n"
    "data = memoryview(b'z' * (1 << 20))\n"
    "while data:\n"
    "    data = data[os.write(1, data):]\n"
)


def _run():
    needs.need("runner", "artifact dir")
    import wasi_python

    return wasi_python.run


def _child(script: str) -> list[str]:
    """`script` in a fresh interpreter, its stdout's lines; the timeout is a fail-safe for a call
    that would hang, not a timing."""
    out = subprocess.run(
        [sys.executable, "-I", "-c", script], capture_output=True, text=True, timeout=300
    )
    assert out.returncode == 0, out.stderr[-2000:]
    return out.stdout.splitlines()


def test_output_is_captured_through_a_pipe_on_posix(monkeypatch) -> None:
    """One capture per call, of the platform's kind: a pipe on macOS and Linux, the callback on
    Windows, where the old path stays."""
    run = _run()
    kinds: list[str] = []
    monkeypatch.setattr(process().observers, "on_capture", kinds.append)
    done = run(["-c", "print('x')"])
    assert (done.exit_code, done.stdout) == (0, b"x\n"), done
    assert kinds == (["pipe"] if POSIX else ["callback"])


@pytest.mark.skipif(not POSIX, reason="Windows keeps the callback: it sets the custom outputs")
def test_a_pipe_capture_sets_no_custom_output(monkeypatch) -> None:
    """A pipe capture never sets a custom output: wasmtime-py's two public setters raise if
    reached, its own table allocates nothing, the runner's output table draws no key (one key is
    drawn here before the call and one after, so a call that drew none leaves them one apart),
    and the observer records one pipe."""
    import wasmtime

    from wasi_python import _wasmtime_ffi

    run = _run()
    run(["-c", "pass"])  # the engine and the module, before anything is counted

    def refused(self, value) -> None:
        raise AssertionError("a custom output was set")

    for name in ("stdout_custom", "stderr_custom"):
        monkeypatch.setattr(wasmtime.WasiConfig, name, property(fset=refused))
    table = _wasmtime_ffi.custom_output_table()
    allocate, allocated = table.allocate, []

    def counted(value):
        allocated.append(1)
        return allocate(value)

    monkeypatch.setattr(table, "allocate", counted)
    kinds: list[str] = []
    monkeypatch.setattr(process().observers, "on_capture", kinds.append)
    first = next(process().output_keys)
    done = run(["-c", "print('x')"])
    last = next(process().output_keys)
    assert (done.exit_code, done.stdout) == (0, b"x\n"), done
    assert (len(allocated), last - first, kinds) == (0, 1, ["pipe"])


def test_the_cap_cuts_inside_a_write() -> None:
    """Three writes of 3,000 bytes under a cap of 5,000: the first 5,000 bytes exactly, the
    stream named, the other stream whole. A reader takes bytes in pieces the kernel chooses, so
    the cut falls inside a piece."""
    run = _run()
    code = "import os\nfor _ in range(3):\n    os.write(1, b'y' * 3000)\nos.write(2, b'done\\n')\n"
    done = run(["-c", code], output_bytes=5000)
    assert done.exit_code == 0, done
    assert (done.stdout, done.stderr, done.truncated) == (b"y" * 5000, b"done\n", ("stdout",))


def test_stdout_and_stderr_stay_apart_when_interleaved() -> None:
    """A thousand rounds of 7 bytes to stdout and 5 to stderr: 7,000 and 5,000 bytes, each of its
    own stream, nothing truncated."""
    run = _run()
    code = (
        "import os\nfor _ in range(1000):\n    os.write(1, b'o' * 7)\n    os.write(2, b'e' * 5)\n"
    )
    done = run(["-c", code])
    assert done.exit_code == 0, done
    assert (done.stdout, done.stderr, done.truncated) == (b"o" * 7000, b"e" * 5000, ())


def test_every_byte_written_before_a_hard_exit_arrives() -> None:
    """A mebibyte written, then `os._exit(0)`: the call's stdout is that mebibyte exactly."""
    run = _run()
    done = run(["-c", WRITE_MIB + "os._exit(0)\n"])
    assert (done.exit_code, done.trapped) == (0, None), done
    assert done.stdout == b"z" * MIB


def test_a_call_leaves_no_thread_of_its_own_behind() -> None:
    """After one warm-up call (a process's first call starts the epoch ticker, which stays), a
    call with a mebibyte of output leaves no thread that was not there before it. Threads are
    compared as objects, so a thread that reused an ended one's ident is still new."""
    run = _run()
    run(["-c", "pass"])
    before = set(threading.enumerate())
    done = run(["-c", WRITE_MIB])
    after = set(threading.enumerate())
    assert (done.exit_code, done.stdout) == (0, b"z" * MIB), done.exit_code
    assert [t.name for t in after - before] == []


ABOVE_1024 = f"""
import os, resource, threading
soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
want = 2048 if hard == resource.RLIM_INFINITY else min(hard, 2048)
resource.setrlimit(resource.RLIMIT_NOFILE, (want, hard))  # this process's own limit, for itself
import wasi_python
assert wasi_python.run(["-c", "pass"]).exit_code == 0  # the engine, the module and the ticker
held = [os.open(os.devnull, os.O_RDONLY) for _ in range(1030)]
r, w = os.pipe()
print("lowest", min(r, w))
os.close(r)
os.close(w)
before = set(threading.enumerate())
done = wasi_python.run(["-c", {WRITE_MIB!r}])
after = set(threading.enumerate())
print("call", done.exit_code, len(done.stdout), done.stdout == b"z" * (1 << 20))
print("new threads", len(after - before))
"""


@pytest.mark.skipif(not POSIX, reason="Windows keeps the callback: no descriptor is read")
def test_output_arrives_above_descriptor_1024() -> None:
    """In a child that raises its own soft descriptor limit and holds 1,030 descriptors, so every
    descriptor the capture makes is above 1,023: the mebibyte arrives whole and no thread stays.
    A reader that waited with `select.select` would die at its first wait, and the guest would
    block for ever on a full pipe."""
    needs.need("runner", "artifact dir", "descriptor limit")
    lines = _child(ABOVE_1024)
    lowest = int(lines[0].split()[1])
    assert lowest > 1023, lines
    assert lines[1:] == ["call 0 1048576 True", "new threads 0"], lines


FORKED_CHILD = f"""
import os, warnings
import wasi_python
assert wasi_python.run(["-c", "pass"]).exit_code == 0
gate_r, gate_w = os.pipe()
children = []


def host(frame):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)  # a fork of a threaded process
        pid = os.fork()
    if pid == 0:  # the child: it holds a copy of every descriptor the call has open
        os.read(gate_r, 1)
        os._exit(0)
    children.append(pid)
    return b""


code = "import _host\\n_host.call(b'fork')\\n" + {WRITE_MIB!r}
done = wasi_python.run(["-c", code], host=host)
(pid,) = children
alive = os.waitpid(pid, os.WNOHANG) == (0, 0)
os.write(gate_w, b"x")
os.waitpid(pid, 0)
print("call", done.exit_code, len(done.stdout), done.stdout == b"z" * (1 << 20))
print("child alive at the return", alive)
"""


@pytest.mark.skipif(not hasattr(os, "fork"), reason="no fork on this system")
def test_a_call_returns_while_a_forked_child_holds_its_descriptors() -> None:
    """The door forks a child that waits on a pipe of the check's own; the call then writes a
    mebibyte and returns with every byte while the child still lives, so the call never waited
    for an end of file the child's copies withhold. The check then releases and reaps it."""
    needs.need("runner", "artifact dir")
    lines = _child(FORKED_CHILD)
    assert lines == ["call 0 1048576 True", "child alive at the return True"], lines


def test_the_stream_keeps_the_cap_to_the_byte() -> None:
    """A stream keeps up to its cap and reports every write as whole: 100 bytes into a cap of 10
    keep 10 and set `dropped`; a second write keeps nothing and still returns its length; no
    cap keeps all."""
    from wasi_python._outputs import _Stream

    capped = _Stream("stdout", 10)
    assert capped.write(b"x" * 100) == 100
    assert (bytes(capped.data), capped.dropped) == (b"x" * 10, True)
    assert capped.write(b"y" * 5) == 5
    assert bytes(capped.data) == b"x" * 10
    free = _Stream("stderr", None)
    assert free.write(b"z" * 100) == 100
    assert (bytes(free.data), free.dropped) == (b"z" * 100, False)
