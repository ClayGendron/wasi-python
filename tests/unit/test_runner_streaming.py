"""Output while the guest runs: `on_output` is handed each stream's bytes in order, on the thread
that made the call (the event loop's under `run_async`), while the guest still runs; at most
`output_bytes` of a stream are delivered and the first byte past them marks it; an `Exception`
from the callback is warned once and stops delivery only, any other `BaseException` stops the
call; `OutputFeed` iterates a `run_async` call's chunks beside its task; and `output_keep="tail"`
keeps a stream's end with the count of what was cut. Rows that run a guest need the artifact
set. Nothing here measures time: a row that waits, waits on the door, and the deadline is its
failure, never its verdict."""

from __future__ import annotations

import asyncio
import random
import sys
import threading
import warnings

import pytest

from harness import needs
from wasi_python import OutputChunk, OutputFeed, _limits, _outputs

FAIL_SAFE_S = 30  # a deadline that only a broken delivery reaches

# The guest prints "ready" flushed, then asks the host through the door until it answers
# "seen": the host answers so once `on_output` has had "ready", so the call ends only if the
# chunk arrived while the guest ran.
WAIT_FOR_SEEN = (
    "import _host\n"
    "print('ready', flush=True)\n"
    "while _host.call(b'?') != b'seen':\n"
    "    pass\n"
    "print('done', flush=True)\n"
)
# The guest prints "ready" flushed, then asks the door for ever: only a stop ends it.
FOREVER = "import _host\nprint('ready', flush=True)\nwhile True:\n    _host.call(b'?')\n"


def _wasi():
    needs.need("runner", "artifact dir")
    import wasi_python

    return wasi_python


def _joined(chunks: list[OutputChunk], stream: str) -> bytes:
    return b"".join(c.data for c in chunks if c.stream == stream)


class Stop(BaseException):
    """The embedder's own BaseException."""


# What runs without the artifact set: the stream's keep and the bound on delivery, driven
# write by write.


class Sink:
    def __init__(self) -> None:
        self.pieces: list[tuple[str, bytes, bool]] = []

    def __call__(self, stream: str, data: bytes, cut: bool) -> None:
        self.pieces.append((stream, bytes(data), cut))


def test_the_tail_keeps_the_last_bytes_whatever_the_pieces() -> None:
    """Under "tail" a stream holds its last `cap` bytes, in order, whatever the sizes of the
    writes that brought them, and counts every byte written."""
    rng = random.Random(164)
    for cap in (1, 7, 64, 100):
        stream = _outputs._Stream("stdout", cap, "tail")
        everything = bytearray()
        for _ in range(200):
            piece = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 3 * cap)))
            assert stream.write(piece) == len(piece)
            everything += piece
            held = bytes(stream.data[stream.at :] + stream.data[: stream.at])
            assert held == bytes(everything[-cap:]), cap
            assert len(stream.data) <= cap
        assert stream.written == len(everything)


def test_the_head_and_the_tail_read_as_the_result_says() -> None:
    """A stream within its cap reads whole in either keep; past it, "head" reads its first bytes
    and "tail" the marker and its last bytes, never more than the cap; a cap shorter than the
    marker keeps the tail alone."""
    for keep in ("head", "tail"):
        whole = _outputs._Stream("stdout", 10, keep)
        whole.write(b"abc")
        assert (whole.kept(), whole.dropped) == (b"abc", False)
    head = _outputs._Stream("stdout", 4, "head")
    head.write(b"abcdefgh")
    assert (head.kept(), head.dropped, head.written) == (b"abcd", True, 8)
    tail = _outputs._Stream("stdout", 20, "tail")
    tail.write(b"x" * 30 + b"0123456789")
    assert tail.kept() == b"[20 bytes cut]\n" + b"56789" and len(tail.kept()) == 20
    short = _outputs._Stream("stdout", 5, "tail")
    short.write(b"abcdefgh")
    assert short.kept() == b"defgh"
    nothing = _outputs._Stream("stdout", 0, "tail")
    nothing.write(b"abc")
    assert (nothing.kept(), nothing.dropped) == (b"", True)


def test_the_sink_is_handed_the_cap_and_one_mark() -> None:
    """The sink gets each write's bytes within the cap, in either keep; the write that crosses
    it carries the mark; a write after a cap met exactly brings an empty piece with the mark;
    nothing after."""
    for keep in ("head", "tail"):
        sink = Sink()
        stream = _outputs._Stream("stderr", 10, keep, sink)
        for piece in (b"abcd", b"efghijkl", b"mn"):
            stream.write(piece)
        assert sink.pieces == [("stderr", b"abcd", False), ("stderr", b"efghij", True)]
        exact = Sink()
        stream = _outputs._Stream("stdout", 4, keep, exact)
        for piece in (b"abcd", b"e", b"f"):
            stream.write(piece)
        assert exact.pieces == [("stdout", b"abcd", False), ("stdout", b"", True)]
    unbounded = Sink()
    stream = _outputs._Stream("stdout", None, "head", unbounded)
    stream.write(b"a" * 50)
    assert unbounded.pieces == [("stdout", b"a" * 50, False)]


def test_the_two_new_keywords_are_checked() -> None:
    """`output_keep` is "head" or "tail" and nothing else; `on_output` is a synchronous
    callable, and a feed is refused where no event loop delivers to it."""
    assert _limits._check_output_keep("head") == "head"
    assert _limits._check_output_keep("tail") == "tail"
    for bad in ("HEAD", "", None, 1):
        with pytest.raises(ValueError, match="output_keep"):
            _limits._check_output_keep(bad)
    assert _outputs._check_on_output(None, asynchronous=False) is None
    assert _outputs._check_on_output(print, asynchronous=False) is print
    with pytest.raises(TypeError, match="on_output"):
        _outputs._check_on_output(5, asynchronous=False)
    with pytest.raises(TypeError, match="OutputFeed"):
        _outputs._check_on_output(OutputFeed(), asynchronous=False)


# The public rows.


def test_every_kept_byte_arrives_in_order() -> None:
    """Each stream's chunks, joined, are its `Completed` field exactly; no chunk is empty or
    marked when nothing was cut."""
    wasi = _wasi()
    chunks: list[OutputChunk] = []
    code = (
        "import sys\n"
        "for i in range(3000):\n"
        "    print(i, flush=i % 7 == 0)\n"
        "    print(-i, file=sys.stderr)\n"
    )
    done = wasi.run(["-c", code], on_output=chunks.append)
    assert (done.exit_code, done.trapped, done.truncated) == (0, None, ()), done
    assert _joined(chunks, "stdout") == done.stdout and done.stdout.startswith(b"0\n1\n")
    assert _joined(chunks, "stderr") == done.stderr and done.stderr.startswith(b"0\n-1\n")
    assert all(c.data and not c.cut for c in chunks)
    assert {c.stream for c in chunks} == {"stdout", "stderr"}


def test_output_arrives_while_the_guest_runs() -> None:
    """The guest waits on the door for the host to have seen its "ready": a delivery made only
    at the end would leave it waiting until the deadline."""
    wasi = _wasi()
    chunks: list[OutputChunk] = []

    def host(request: bytes) -> bytes:
        return b"seen" if b"ready" in _joined(chunks, "stdout") else b"not yet"

    done = wasi.run(
        ["-c", WAIT_FOR_SEEN], host=host, on_output=chunks.append, deadline_s=FAIL_SAFE_S
    )
    assert (done.exit_code, done.trapped) == (0, None), done
    assert _joined(chunks, "stdout") == done.stdout == b"ready\ndone\n"


def test_on_output_runs_on_the_calling_thread() -> None:
    """Under `run`, on the thread that called it; under `run_async`, on the event loop's."""
    wasi = _wasi()
    seen: list[int] = []
    code = "import sys\nfor i in range(100): print(i, flush=True); print(i, file=sys.stderr)"
    done = wasi.run(["-c", code], on_output=lambda c: seen.append(threading.get_ident()))
    assert done.exit_code == 0 and seen and set(seen) == {threading.get_ident()}

    async def main() -> int:
        seen.clear()
        done = await wasi.run_async(
            ["-c", code], on_output=lambda c: seen.append(threading.get_ident())
        )
        assert done.exit_code == 0
        return threading.get_ident()

    loop_thread = asyncio.run(main())
    assert seen and set(seen) == {loop_thread}


def test_the_cap_bounds_what_is_delivered() -> None:
    """At most `output_bytes` of a stream are delivered, the last chunk of the stream marked;
    a cap met exactly and then passed brings an empty chunk with the mark."""
    wasi = _wasi()
    chunks: list[OutputChunk] = []
    code = "import sys\nfor i in range(9): sys.stdout.write('a' * 1000); sys.stdout.flush()"
    done = wasi.run(["-c", code], on_output=chunks.append, output_bytes=5000)
    assert done.truncated == ("stdout",) and done.stdout == b"a" * 5000
    out = [c for c in chunks if c.stream == "stdout"]
    assert _joined(out, "stdout") == b"a" * 5000
    assert [c.cut for c in out].count(True) == 1 and out[-1].cut

    exact: list[OutputChunk] = []

    def host(request: bytes) -> bytes:
        return b"seen" if len(_joined(exact, "stdout")) == 5000 else b"not yet"

    code = (
        "import _host, sys\n"
        "sys.stdout.write('b' * 5000); sys.stdout.flush()\n"
        "while _host.call(b'?') != b'seen':\n"
        "    pass\n"
        "sys.stdout.write('c'); sys.stdout.flush()\n"
    )
    done = wasi.run(
        ["-c", code],
        host=host,
        on_output=exact.append,
        output_bytes=5000,
        deadline_s=FAIL_SAFE_S,
    )
    assert (done.exit_code, done.truncated) == (0, ("stdout",)), done
    assert _joined(exact, "stdout") == b"b" * 5000
    assert exact[-1] == OutputChunk("stdout", b"", True)
    assert [c.cut for c in exact].count(True) == 1


def test_an_exception_in_on_output_stops_delivery_only(monkeypatch) -> None:
    """One warning, one callback call, and the call whole: the guest goes on printing after the
    callback raised, and nothing more reaches it. Python's default unraisable hook is in place,
    not pytest's, so a report through it would fail here."""
    wasi = _wasi()
    monkeypatch.setattr(sys, "unraisablehook", sys.__unraisablehook__)
    calls: list[OutputChunk] = []

    def on_output(chunk: OutputChunk) -> None:
        calls.append(chunk)
        raise ValueError("this callback chokes")

    def host(request: bytes) -> bytes:
        return b"seen" if calls else b"not yet"

    with pytest.warns(RuntimeWarning, match="ValueError: this callback chokes") as caught:
        done = wasi.run(
            ["-c", WAIT_FOR_SEEN], host=host, on_output=on_output, deadline_s=FAIL_SAFE_S
        )
    assert len([w for w in caught if w.category is RuntimeWarning]) == 1
    assert len(calls) == 1
    assert (done.exit_code, done.stdout) == (0, b"ready\ndone\n"), done


def test_a_base_exception_in_on_output_stops_the_call() -> None:
    """A guest that never ends by itself is stopped, and `run` and `run_async` raise the
    callback's own exception."""
    wasi = _wasi()

    def on_output(chunk: OutputChunk) -> None:
        raise Stop()

    with pytest.raises(Stop):
        wasi.run(["-c", FOREVER], host=lambda r: b"", on_output=on_output, deadline_s=FAIL_SAFE_S)

    async def main() -> None:
        await wasi.run_async(
            ["-c", FOREVER], host=lambda r: b"", on_output=on_output, deadline_s=FAIL_SAFE_S
        )

    with pytest.raises(Stop):
        asyncio.run(main())


def test_a_feed_follows_its_task() -> None:
    """`follow` gives every chunk in order and ends with its task."""
    wasi = _wasi()

    async def main():
        feed = OutputFeed()
        code = "import sys\nfor i in range(500): print(i, flush=True); print(i, file=sys.stderr)"
        task = asyncio.create_task(wasi.run_async(["-c", code], on_output=feed))
        chunks = [chunk async for chunk in feed.follow(task)]
        return chunks, await task

    chunks, done = asyncio.run(main())
    assert done.exit_code == 0
    assert _joined(chunks, "stdout") == done.stdout and _joined(chunks, "stderr") == done.stderr


def test_a_feed_ends_when_its_task_is_cancelled_before_it_starts() -> None:
    """A task cancelled before its first line runs no `finally` of `run_async`'s: `follow`
    still ends, since it watches the task."""
    from wasi_python import run_async

    async def main():
        feed = OutputFeed()
        task = asyncio.create_task(run_async(["-c", "print(1)"], on_output=feed))
        task.cancel()
        chunks = await asyncio.wait_for(_collect(feed.follow(task)), FAIL_SAFE_S)
        with pytest.raises(asyncio.CancelledError):
            await task
        return chunks

    assert asyncio.run(main()) == []


async def _collect(chunks) -> list[OutputChunk]:
    return [chunk async for chunk in chunks]


def test_an_async_on_output_is_refused() -> None:
    """A coroutine function is refused before any work, by `run` and by `run_async`."""
    from wasi_python import run, run_async

    async def on_output(chunk: OutputChunk) -> None:
        pass

    with pytest.raises(TypeError, match="on_output"):
        run(["-c", "pass"], on_output=on_output)
    with pytest.raises(TypeError, match="on_output"):
        asyncio.run(run_async(["-c", "pass"], on_output=on_output))


def test_a_feed_under_run_is_refused() -> None:
    """A feed delivers on an event loop: `run` has none, and refuses it before any work."""
    from wasi_python import run

    with pytest.raises(TypeError, match="OutputFeed"):
        run(["-c", "pass"], on_output=OutputFeed())


def test_a_feed_used_twice_is_refused() -> None:
    """A feed serves one call: the second `run_async` that is handed it refuses it, even when
    the first refused its own arguments."""
    from wasi_python import run_async

    async def main() -> None:
        feed = OutputFeed()
        with pytest.raises(ValueError, match="fuel"):
            await run_async(["-c", "pass"], on_output=feed, fuel=-1)
        with pytest.raises(TypeError, match="OutputFeed"):
            await run_async(["-c", "pass"], on_output=feed)
        assert [chunk async for chunk in feed.follow(asyncio.ensure_future(asyncio.sleep(0)))] == []

    asyncio.run(main())


def test_tail_keeps_the_end_and_marks_the_cut() -> None:
    """Under `output_keep="tail"` the result starts with the count cut and ends with the
    output's own end, within the cap."""
    wasi = _wasi()
    code = "import sys\nsys.stdout.write('x' * 996 + 'END\\n')"
    done = wasi.run(["-c", code], output_bytes=100, output_keep="tail")
    assert done.stdout.startswith(b"[900 bytes cut]\n"), done.stdout
    assert done.stdout.endswith(b"END\n") and len(done.stdout) == 100
    assert done.truncated == ("stdout",)
    with pytest.raises(ValueError, match="output_keep"):
        wasi.run(["-c", "pass"], output_keep="middle")


def test_a_streamed_call_leaves_no_thread_behind() -> None:
    """Delivery runs on the threads a call already has: none is left when it returns."""
    wasi = _wasi()
    wasi.run(["-c", "pass"])  # the engine, the module and the ticker, before counting
    before = set(threading.enumerate())
    chunks: list[OutputChunk] = []
    done = wasi.run(["-c", "print('x')"], on_output=chunks.append)
    assert done.exit_code == 0 and chunks
    left = [t for t in threading.enumerate() if t not in before and t.is_alive()]
    assert not left, left


def test_no_warning_without_a_fault() -> None:
    """A callback that never raises brings no warning."""
    wasi = _wasi()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        done = wasi.run(["-c", "print('quiet')"], on_output=lambda c: None)
    assert done.stdout == b"quiet\n"
