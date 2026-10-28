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
from wasi_python._process import process
falls = []
process().observers.on_slow_loop = falls.append
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
print("falls", falls)
"""


@pytest.mark.skipif(not POSIX, reason="Windows keeps the callback: no descriptor is read")
def test_output_arrives_above_descriptor_1024() -> None:
    """In a child that raises its own soft descriptor limit and holds 1,030 descriptors, so every
    descriptor the capture makes is above 1,023: the mebibyte arrives whole, no thread stays,
    and the reader never fell to its slow loop, so its wait read every byte. A reader that waited
    with `select.select` would fail at its first wait."""
    needs.need("runner", "artifact dir", "descriptor limit")
    lines = _child(ABOVE_1024)
    lowest = int(lines[0].split()[1])
    assert lowest > 1023, lines
    assert lines[1:] == ["call 0 1048576 True", "new threads 0", "falls []"], lines


FORKED_CHILD = f"""
import os, threading, warnings
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
before = set(threading.enumerate())
done = wasi_python.run(["-c", code], host=host)
after = set(threading.enumerate())
(pid,) = children
alive = os.waitpid(pid, os.WNOHANG) == (0, 0)
os.write(gate_w, b"x")
os.waitpid(pid, 0)
print("call", done.exit_code, len(done.stdout), done.stdout == b"z" * (1 << 20))
print("child alive at the return", alive)
print("new threads", len(after - before))
"""


@pytest.mark.skipif(not hasattr(os, "fork"), reason="no fork on this system")
def test_a_call_returns_while_a_forked_child_holds_its_descriptors() -> None:
    """The door forks a child that waits on a pipe of the check's own; the call then writes a
    mebibyte and returns with every byte while the child still lives, so the call never waited
    for an end of file the child's copies withhold, and leaves no thread behind, so nothing of
    the call waits for it either. The check then releases and reaps the child."""
    needs.need("runner", "artifact dir")
    lines = _child(FORKED_CHILD)
    want = ["call 0 1048576 True", "child alive at the return True", "new threads 0"]
    assert lines == want, lines


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


def test_a_stream_whose_write_raises_reports_dropped(monkeypatch) -> None:
    """A write the capture could not keep still reports every byte written, so the guest goes
    on, and the stream it reached says bytes were dropped, so the result names it as
    truncated."""
    import ctypes

    from wasi_python import _outputs

    class Failing(_outputs._Stream):
        def write(self, data: bytes) -> int:
            raise MemoryError

    stream = Failing("stdout", None)
    monkeypatch.setattr(process(), "outputs", {7: stream})
    data = ctypes.create_string_buffer(b"lost", 4)
    assert _outputs._write_output(7, data, 4) == 4
    assert (bytes(stream.data), stream.dropped) == (b"", True)
    assert _outputs._write_output(8, data, 4) == 4  # no stream: nothing to tell


def test_a_path_that_does_not_open_falls_back_to_the_callback(monkeypatch) -> None:
    """A host whose `/dev/fd` does not reach a pipe (Linux without `/proc`: a chroot, a minimal
    container) still runs every call: the platform's channel is given a path that does not
    open, the capture closes what it made and takes the callback, and the guest's line arrives.
    It runs on every system, since the channel is the check's own."""
    from wasi_python import _platform

    run = _run()
    run(["-c", "pass"])
    made: list[int] = []

    def channel() -> tuple[str, int, int]:
        r, w = os.pipe()
        made.extend((r, w))
        return f"/no-such-folder-of-descriptors/{w}", r, w

    monkeypatch.setattr(_platform.PLATFORM, "output_channel", channel)
    kinds: list[str] = []
    monkeypatch.setattr(process().observers, "on_capture", kinds.append)
    open_before = len(os.listdir("/dev/fd")) if POSIX else 0
    before = set(threading.enumerate())
    done = run(["-c", "print('x')"])
    after = set(threading.enumerate())
    open_after = len(os.listdir("/dev/fd")) if POSIX else 0
    assert (done.exit_code, done.stdout, done.truncated) == (0, b"x\n", ()), done
    assert (kinds, len(made) > 0, [t.name for t in after - before]) == (["callback"], True, [])
    assert open_after == open_before  # every descriptor the failed capture made is closed


READER_FAILS = f"""
import select, signal, sys
signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # as a command line that wants `| head` quiet
import wasi_python
from wasi_python._process import process
falls = []
process().observers.on_slow_loop = falls.append
assert wasi_python.run(["-c", "pass"]).exit_code == 0
real = select.poll


class Failing:
    def __init__(self):
        self.p = real()

    def register(self, *a):
        self.p.register(*a)

    def unregister(self, *a):
        self.p.unregister(*a)

    def poll(self, *a):
        raise OSError(5, "a wait that fails")


select.poll = Failing
done = wasi_python.run(["-c", {WRITE_MIB!r}])
print("call", done.exit_code, len(done.stdout), done.stdout == b"z" * (1 << 20), done.truncated)
with wasi_python.Session() as s:
    turns = [s.run(f"import sys\\nsys.stdout.write({{c!r}} * 100000)\\nprint(1)") for c in "ab"]
own = [(t.exit_code, t.stdout == c.encode() * 100000 + b"1\\n") for t, c in zip(turns, "ab")]
print("turns", own)
print("falls", falls)
"""


@pytest.mark.skipif(not POSIX, reason="Windows keeps the callback: no reader waits there")
def test_a_reader_whose_wait_fails_still_reads_every_byte() -> None:
    """In a child that restores SIGPIPE's default action, with every wait of the reader made to
    fail: a call still gets its mebibyte whole and a session's two turns their own bytes, and
    the child lives. A reader that closed its ends on such a failure would refuse the guest's
    next write, and the signal that refusal raises would end the host process. Each reader, the
    call's and the session's, reports its fall to the slow loop once."""
    needs.need("runner", "artifact dir")
    lines = _child(READER_FAILS)
    assert lines == [
        "call 0 1048576 True ()",
        "turns [(0, True), (0, True)]",
        "falls ['OSError', 'OSError']",
    ], lines


# A read of the pipe that fails takes nothing from it, and the reader reads the end again: no
# byte is lost, and the stream is not named. An end whose reads fail until the call ends may
# still hold bytes, and its stream is named.
FAILING_READS = """
import os, sys, threading
import wasi_python
from wasi_python import _outputs
assert wasi_python.run(["-c", "pass"]).exit_code == 0
real, failed = os.read, []
always = sys.argv[1] == "always"


def read(fd, n):
    reader = threading.current_thread().name == "wasi-python-output"
    if reader and n == _outputs.READ_BYTES and (always or not failed):
        failed.append(fd)
        raise OSError(5, "a read that fails")
    return real(fd, n)


os.read = read
done = wasi_python.run(["-c", sys.argv[2]])
print("call", done.exit_code, len(done.stdout), set(done.stdout), done.truncated, bool(failed))
"""


def _failing_reads(how: str, code: str) -> list[str]:
    needs.need("runner", "artifact dir")
    out = subprocess.run(
        [sys.executable, "-I", "-c", FAILING_READS, how, code],
        capture_output=True,
        text=True,
        timeout=300,  # a fail-safe for a call that would hang, not a timing
    )
    assert out.returncode == 0, out.stderr[-2000:]
    return out.stdout.splitlines()


@pytest.mark.skipif(not POSIX, reason="Windows keeps the callback: no pipe is read")
def test_a_failed_read_loses_no_byte_and_names_no_stream() -> None:
    """The reader's first read of the guest's output fails once: the mebibyte arrives whole,
    and `truncated` names nothing, since no byte was lost."""
    lines = _failing_reads("once", WRITE_MIB)
    assert lines == ["call 0 1048576 {122} () True"], lines


@pytest.mark.skipif(not POSIX, reason="Windows keeps the callback: no pipe is read")
def test_an_end_never_read_again_names_its_stream() -> None:
    """Every read of either end fails until the call ends: what each end held may still be in
    the pipe, so both streams are named, though only stdout had bytes."""
    lines = _failing_reads("always", "import os\nos.write(1, b'z' * 100)")
    assert lines == ["call 0 0 set() ('stdout', 'stderr') True"], lines


def test_each_reader_is_joined_once(monkeypatch) -> None:
    """Joins are counted, not timed: `threading.Thread.join` wrapped, three calls join three
    readers and a session of four turns joins one, each dead once joined; Windows has no
    reader and joins none."""
    import wasi_python

    run = _run()
    run(["-c", "pass"])
    joined: list[threading.Thread] = []
    join = threading.Thread.join

    def counted(self, *args, **kwargs):
        if self.name == "wasi-python-output":
            joined.append(self)
        return join(self, *args, **kwargs)

    monkeypatch.setattr(threading.Thread, "join", counted)
    for _ in range(3):
        assert run(["-c", "print(1)"]).stdout == b"1\n"
    calls = len(joined)
    with wasi_python.Session() as s:
        assert [s.run("print(2)").stdout for _ in range(4)] == [b"2\n"] * 4
    session = len(joined) - calls
    assert (calls, session) == ((3, 1) if POSIX else (0, 0))
    assert [t for t in joined if t.is_alive()] == []
