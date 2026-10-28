"""The guest's stdout and stderr: each kept up to its cap in a `_Stream`, and two captures that
bring the guest's bytes there, with one shape.

Why two. wasmtime hands a custom output stream its bytes 4 KiB at a time on a worker thread of
its own, and a Python callback called there makes and destroys a Python thread state for every
piece: most of what output cost was that hand-off and that thread state, not the copy. A pipe
that wasmtime opens by its path and writes as a file costs one kernel write per piece on the
guest's own thread and nothing in Python, and one reader thread of the runner's, per store,
moves what arrives into the two capped streams. `_PipeCapture` is that, where the platform
offers such a channel (`output_channel`) and wasmtime can open its path; `_CallbackCapture` is
the custom-output callback, where it offers none or wasmtime cannot open it.

The shape. `_capture` opens one on a `WasiConfig` with its first two streams. `retarget` gives
it two fresh streams, `settle` returns once every byte the guest wrote so far is in them, and
`close`, called after the store is closed, gathers the rest and frees what the capture holds. A
call opens one and closes it after its store; a session opens one with its store, retargets it
before each turn, settles it after each turn and closes it after its store.

The reader's rules. It waits with `select.poll`, which takes any descriptor, where
`select.select` refuses one of 1,024 or more. It ends when `close()` asks, after the store has
closed and nothing more can arrive, or earlier once both streams have reached end of file; it
never waits for end of file, since a forked child of the embedder holds copies of wasmtime's
write ends for as long as the child lives. A stream is named as truncated where a piece is lost
or may be: a piece it fails to keep, or an end whose last read failed when a turn's bytes are
handed back or the reader ends; a failed read that a later read of its end follows takes nothing
from the pipe and loses nothing. The callback names a stream by the same rule, where a write
that reached it could not be kept. If its wait or a read fails, it reads on without blocking in
a slower loop until `close()` asks: it never stops reading, since a guest blocked in a host
write on a full pipe is beyond the deadline, a cancel and Ctrl-C, which stop wasm code only; and
it never closes an end the guest may still write to, since that write would refuse the guest and
would end a host that restored SIGPIPE's default action. Whatever ends it, it tells every
waiter. A turn's settle rests on wasmtime writing a file output on the guest's own thread: a
write has reached the pipe when `fd_write` returns.
"""

from __future__ import annotations

import ctypes
import os
import select
import threading
import time
from typing import Any, Protocol

from . import _platform
from ._process import process

READ_BYTES = 65536  # one read takes a pipe's whole buffer on macOS and Linux
SETTLE, STOP = b"s", b"x"  # what the wake pipe carries to the reader
SLOW_WAIT_S = 0.001  # the slow loop's sleep when no end had bytes


class _Stream:
    """A guest's stdout or stderr, kept up to a cap. Bytes past it are dropped, never buffered,
    and still reported as written, so the guest's write succeeds and is not retried (wasmtime-py
    takes the callback's return value as the count written)."""

    def __init__(self, name: str, cap: int | None) -> None:
        self.name, self.cap, self.data, self.dropped = name, cap, bytearray(), False

    def write(self, data: bytes) -> int:
        room = len(data) if self.cap is None else max(0, self.cap - len(self.data))
        if room < len(data):
            self.dropped = True
        self.data.extend(data[:room])
        return len(data)


class _Capture(Protocol):
    """What a call and a session ask of a capture, whichever kind it is."""

    kind: str  # "pipe" or "callback", told to the observer

    def retarget(self, out: _Stream, err: _Stream) -> None: ...
    def settle(self) -> None: ...
    def close(self) -> None: ...


def _close_quietly(fd: int) -> None:
    try:
        os.close(fd)
    except OSError:
        pass  # already closed, or never a descriptor: nothing is left to free


class _PipeCapture:
    """The two streams through two pipes wasmtime writes as files, read on one thread of the
    runner's own for as long as the store lives."""

    kind = "pipe"

    def __init__(self, first: tuple[str, int, int], out: _Stream, err: _Stream) -> None:
        self.lock = threading.Lock()  # the targets and `ended`
        self.first = first
        self.targets = [out, err]
        self.ends: dict[int, int] = {}  # each read end still open: its stream, 0 or 1
        self.wake = (-1, -1)  # the pipe `settle` and `close` wake the reader by
        self.settled = threading.Event()
        self.ended = False  # the reader has ended: both streams at end of file, or closed
        self.stop_asked = False  # the reader's own: `close()`'s stop byte has been read
        self.settle_owed = False  # the reader's own: a settle byte read, its answer not yet set
        self.failing: set[int] = set()  # the reader's own: each end whose last read failed
        self.thread: threading.Thread | None = None  # the reader, until `close()` joins it

    def open(self, wasi: Any) -> bool:
        """Both paths given to wasmtime, which opens each before its setter returns; the runner's
        write ends closed, so wasmtime's are the only ones; the reader started. False, with
        every descriptor this made closed, when wasmtime cannot open a path (a host whose
        `/dev/fd` does not reach a pipe, as Linux without `/proc`): the caller takes the
        callback. Any other failure is raised, the same descriptors closed, before guest code."""
        made = list(self.first[1:])
        try:
            second = _platform.PLATFORM.output_channel()
            if second is None:
                raise OSError("the platform gave one output channel and then none")
            made += second[1:]
            try:
                wasi.stdout_file, wasi.stderr_file = self.first[0], second[0]
            except Exception:
                for fd in made:
                    _close_quietly(fd)
                return False
            for w in (self.first[2], second[2]):
                made.remove(w)
                os.close(w)
            self.wake = os.pipe()
            made += self.wake
            self.ends = {self.first[1]: 0, second[1]: 1}
            self.thread = threading.Thread(
                target=self._drain, name="wasi-python-output", daemon=True
            )
            self.thread.start()
        except BaseException:
            for fd in made:
                _close_quietly(fd)
            self.ends, self.thread = {}, None
            raise
        return True

    def retarget(self, out: _Stream, err: _Stream) -> None:
        with self.lock:
            self.targets = [out, err]

    def settle(self) -> None:
        """Returns once the reader has read every byte the pipes hold into the current targets;
        at once if it has ended, when nothing more can arrive."""
        with self.lock:
            if self.ended:
                return
            self.settled.clear()
        os.write(self.wake[1], SETTLE)
        self.settled.wait()

    def close(self) -> None:
        """After the store is closed, so nothing more can arrive: the reader reads what the pipes
        hold, closes its ends and ends; it is joined and the wake pipe closed. It never waits for
        end of file, and never raises."""
        thread, self.thread = self.thread, None
        if thread is None:
            return
        try:
            os.write(self.wake[1], STOP)
        except OSError:
            pass  # the reader has ended already: the join below returns at once
        thread.join()
        for fd in self.wake:
            _close_quietly(fd)

    def _drain(self) -> None:
        """The reader: each ready end read into its stream, until `close()` asks it to stop or
        both streams have reached end of file. If the wait or a read fails, the slow loop reads
        on in its place."""
        try:
            poller = select.poll()
            for fd in (*self.ends, self.wake[0]):
                poller.register(fd, select.POLLIN)
            while self.ends:
                for fd, _ in poller.poll():
                    if fd == self.wake[0]:
                        if self._woken(poller):
                            return
                    elif fd in self.ends:  # not closed by a read earlier in this round
                        self._take(fd, poller)
        except BaseException as e:
            try:
                on_slow_loop = process().observers.on_slow_loop
                if on_slow_loop is not None:
                    on_slow_loop(type(e).__name__)
            finally:
                self._slow()  # whatever the observer does, the reader reads on
        finally:
            self._end()

    def _woken(self, poller: select.poll) -> bool:
        """A settle or a stop: every end read until none is ready; True for a stop."""
        asked = os.read(self.wake[0], 64)
        if STOP in asked or not asked:
            self.stop_asked = True
        if SETTLE in asked:
            self.settle_owed = True  # answered below, or by the slow loop if this read fails
        self._read_ready(poller)
        if self.stop_asked:
            return True
        self.settle_owed = False
        self.settled.set()
        return False

    def _read_ready(self, poller: select.poll) -> None:
        """Every end that is ready now read, until none is: every byte written before this."""
        while self.ends:
            ready = [fd for fd, _ in poller.poll(0) if fd in self.ends]
            if not ready:
                return
            for fd in ready:
                self._take(fd, poller)

    def _take(self, fd: int, poller: select.poll | None) -> bool:
        """One read of one end into its stream's current target; whether it read bytes. An
        empty read is end of file: every write end is closed, so the end is closed too. A read
        that fails takes nothing from the pipe: its end is marked as failing until a read of it
        does not fail, and the failure is raised, so the reader moves to its slow loop. A piece
        the stream fails to keep is dropped and named."""
        which = self.ends[fd]
        with self.lock:
            target = self.targets[which]
        try:
            data = os.read(fd, READ_BYTES)
        except BlockingIOError:
            self.failing.discard(fd)
            return False  # the slow loop's: nothing there yet
        except BaseException:
            self.failing.add(fd)
            raise
        self.failing.discard(fd)
        if not data:
            del self.ends[fd]
            if poller is not None:
                poller.unregister(fd)
            _close_quietly(fd)
            return False
        try:
            target.write(data)
        except BaseException:
            target.dropped = True  # the piece is lost; the stream says so
        return True

    def _slow(self) -> None:
        """The reader's fall-back after its wait or a read failed: every end read without
        blocking, a millisecond's sleep when none had bytes, until `close()` asks. It never
        closes an end the guest may still write to, since a write into a closed pipe refuses
        the guest, and ends a host that restored SIGPIPE's default action; and it never stops
        reading, since a guest blocked on a full pipe is beyond the deadline, a cancel and
        Ctrl-C, which stop wasm code only. A failed read marks its end and the loop goes on; a
        settle answered while an end is marked names that end's stream."""
        for fd in (*self.ends, self.wake[0]):
            try:
                os.set_blocking(fd, False)
            except OSError:
                pass  # a descriptor already closed: its reads fail and are named
        while True:
            try:
                asked = self._wake_bytes()
                if STOP in asked:
                    self.stop_asked = True
                got = False
                for fd in list(self.ends):
                    got = self._drain_end(fd) or got
                if self.stop_asked or not self.ends:
                    return
                if SETTLE in asked or self.settle_owed:  # read after the byte: all before it
                    self.settle_owed = False
                    self._name_failing()
                    self.settled.set()
                if not got:
                    time.sleep(SLOW_WAIT_S)
            except BaseException:
                time.sleep(SLOW_WAIT_S)  # a failure of the loop's own: try again

    def _wake_bytes(self) -> bytes:
        try:
            return os.read(self.wake[0], 64)
        except BlockingIOError:
            return b""

    def _drain_end(self, fd: int) -> bool:
        """One end read without blocking until it is empty or at end of file; whether it had
        bytes. A read that fails marks the end and leaves it for the next round."""
        got = False
        try:
            while fd in self.ends and self._take(fd, None):
                got = True
        except BaseException:
            pass  # the end is marked; the loop reads it again next round
        return got

    def _name_failing(self) -> None:
        """Each end whose last read failed may still hold bytes its stream never got, now that
        the stream is handed back: the stream is named."""
        with self.lock:
            for fd in self.failing:
                which = self.ends.get(fd)
                if which is not None:
                    self.targets[which].dropped = True

    def _end(self) -> None:
        """The reader's last act, after `close()` asked or both streams reached end of file:
        the read ends it still holds closed, since no write end is left in this process, and
        every waiter told."""
        self._name_failing()
        for fd in self.ends:
            _close_quietly(fd)
        self.ends = {}
        with self.lock:
            self.ended = True
            self.settled.set()


# The callback capture: the guest's two streams by keys that are never reused, in the process's
# output table. wasmtime calls the two functions below on its own threads, and frees a key when
# it drops the stream; wasmtime-py's own table for custom outputs is not used, since it has no
# lock.


def _write_output(key: int | None, data: Any, size: int) -> int:
    stream = None
    try:
        with process().outputs_lock:
            stream = process().outputs.get(key or 0)
        return size if stream is None else stream.write(ctypes.string_at(data, size))
    except BaseException:
        if stream is not None:  # the result names the stream as truncated
            stream.dropped = True
        return size  # never raises, never prints: the bytes are dropped and the write succeeds


def _free_output(key: int | None) -> None:
    with process().outputs_lock:
        process().outputs.pop(key or 0, None)


# The two as C function pointers, made once and kept here for as long as wasmtime may call them.
_output_write = ctypes.CFUNCTYPE(
    ctypes.c_ssize_t, ctypes.c_void_p, ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t
)(_write_output)
_output_free = ctypes.CFUNCTYPE(None, ctypes.c_void_p)(_free_output)


class _CallbackCapture:
    """The two streams through wasmtime's custom outputs: one C callback for both, by two keys
    of the process's output table."""

    kind = "callback"

    def __init__(self, out: _Stream, err: _Stream) -> None:
        self.first = (out, err)
        self.keys = (0, 0)

    def open(self, wasi: Any) -> None:
        from . import _wasmtime_ffi as ffi

        p = process()
        with p.outputs_lock:
            self.keys = next(p.output_keys), next(p.output_keys)
            p.outputs[self.keys[0]], p.outputs[self.keys[1]] = self.first
        ffi.set_custom_outputs(wasi, _output_write, _output_free, self.keys[0], self.keys[1])

    def retarget(self, out: _Stream, err: _Stream) -> None:
        p = process()
        with p.outputs_lock:
            p.outputs[self.keys[0]], p.outputs[self.keys[1]] = out, err

    def settle(self) -> None:
        """Nothing to wait for: a guest's write returns once the callback has kept its bytes."""

    def close(self) -> None:
        p = process()
        with p.outputs_lock:  # the guest has ended; wasmtime frees the keys later
            for key in self.keys:
                p.outputs.pop(key, None)


def _capture(wasi: Any, out: _Stream, err: _Stream) -> _Capture:
    """The capture this platform offers, opened on `wasi` with its first two streams, its kind
    told to the observer. It raises before any guest code, with what it made freed."""
    first = _platform.PLATFORM.output_channel()
    capture: _PipeCapture | _CallbackCapture | None = None
    if first is not None:
        pipe = _PipeCapture(first, out, err)
        if pipe.open(wasi):
            capture = pipe
    if capture is None:  # no channel, or one wasmtime could not open
        capture = _CallbackCapture(out, err)
        capture.open(wasi)
    on_capture = process().observers.on_capture
    if on_capture is not None:
        on_capture(capture.kind)
    return capture
