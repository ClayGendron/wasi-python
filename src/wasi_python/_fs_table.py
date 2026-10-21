"""The mount table of one call: its preopens and descriptors, the numbers it gives and reuses,
the cap on files open at once, the provider calls behind the gate, the trampoline's forwards,
and the dispatch of every shadowed call to its function.

How it works: on a call with mounts, the guest's 29 preview1 calls that act on a descriptor and
are not forward-safe are shadowed (`SHADOWED`). Each finds its call on the thread's stack. A
call that names a number in the call's mount table is served here; any other is forwarded
to wasmtime's own WASI through a small trampoline instantiated on the guest's memory, by
`wasmtime_func_call` on the caller's context, fuel-neutral. Each mount is preopened on an empty,
read-only placeholder folder the runner owns, so wasi-libc's preopen scan finds it; a file or
folder opened in a mount gets a number from 2**30 up, which wasmtime never reaches.

A call without mounts shadows only the two calls in `GUARDED` and the three in
`COUNTED`, through a table with no mounts, so all five are forwarded: every forward of
the first two carries wasmtime 49.0.2's and 49.0.3's fixes, which wasmtime 49.0.0, the newest
wasmtime-py, lacks, and the last three let the table count the files the guest holds open.

Every table, with mounts or without, keeps the call's cap on files open at once: the
wasmtime numbers the guest opened and still holds, plus its open mount files, and answers EMFILE
to an open at the cap before wasmtime or a provider is asked.

wasmtime-py is imported only inside functions, so the package imports without the `run` extra.
"""

from __future__ import annotations

import heapq
import struct
import sys
import types
from array import array
from collections.abc import Callable, Iterable
from typing import Any, TypeVar, cast

from . import _fs_descriptors, _fs_paths
from ._fs_memory import (
    DIRECTORY,
    DIRENT,
    EBADF,
    ECANCELED,
    EFBIG,
    EIO,
    ETIMEDOUT,
    FAULTS_KEPT,
    FUEL_ALLOWANCE,
    FUEL_MAX,
    MASK32,
    MASK64,
    MAX_NAME,
    METHODS,
    PRIVATE,
    PROVIDER_BASE,
    REFUSED_KEPT,
    REGULAR_FILE,
    SIGNATURES,
    _Forwards,
)
from .mounts import (
    Errno,
    FileFault,
    FileRecord,
    Mount,
    RefusedWrite,
    Stat,
    _CallContext,
    _Listing,
    _Mounted,
    _Open,
    _raised,
)

_T = TypeVar("_T")
# The 29 shadowed calls, each to its function; the shared host function calls with no other name.
HANDLERS = {**_fs_descriptors.HANDLERS, **_fs_paths.HANDLERS}


class _Files:
    """One call's mount table and provider calls. Called by the 29 shadows through
    the shared function with the shadowed call's name; it answers an errno, or raises a
    wasmtime error that ends the run (a forward's, or an ABI error as wasmtime gives it), or a
    provider's BaseException, which the shared function records as the call's stop."""

    def __init__(
        self,
        mounts: list[tuple[Mount, int]],
        others: list[str],
        file_calls: int | None,
        staging: int,
        metered: bool,
        engine: Any = None,
        *,
        open_files: int | None = None,
        context: _CallContext,
    ) -> None:
        self.context = context  # the host's answers; the call's five change with its turns
        self.mounts: list[_Mounted] = []
        self.table: dict[int, _Open] = {}
        for mount, number in mounts:
            nested = tuple(
                g if mount.guest == "/" else g[len(mount.guest) :]
                for g in others + [m.guest for m, _ in mounts]
                if g != mount.guest
                and (g.startswith(mount.guest + "/") or (mount.guest == "/" and g != "/"))
            )
            mounted = _Mounted(
                mount.provider,
                mount.guest,
                context.ino_of(mount.guest),
                nested,
                mount.writable is True,
            )
            self.mounts.append(mounted)
            self.table[number] = _Open(mounted, "/", "dir", preopen=True)
        self.limit, self.staging, self.metered = file_calls, staging, metered
        self.engine = engine
        self.calls = dict.fromkeys(METHODS, 0)
        self.total = 0
        self.faults: list[FileFault] = []
        self.refused: list[RefusedWrite] = []
        self.refused_total = 0
        self.staged = 0
        self.opened = 0  # provider numbers in use, owed ones included
        self.free: list[int] = []
        # Closed for the guest, written back at the ending: out of `table`
        # (so no call finds them) and out of `free` (so no open reuses the number).
        self.owed: dict[int, _Open] = {}
        self.next = PROVIDER_BASE
        self.forwards: _Forwards | None = None
        # a forward's own error, or an ABI error the runner raised, and the guest's fuel then
        self.stop_fuel: tuple[BaseException, int] | None = None
        # The cap on files open at once, and the wasmtime numbers the guest opened and
        # still holds. None: no cap (a table built by hand); a call's table gets the call's value.
        self.open_files = open_files
        self.held: set[int] = set()
        self.session = False  # a session's table lives across turns

    def open_now(self) -> int:
        """The files and folders the guest holds open: the wasmtime numbers it opened,
        and its open mount files; an owed buffer is a number the guest has closed."""
        return len(self.held) + self.opened - len(self.owed)

    def _at_cap(self) -> bool:
        return self.open_files is not None and self.open_now() >= self.open_files

    def new_turn(self) -> None:
        """A session's turn starts its counters at zero, so each turn's record and limit are its
        own; the open files, their buffers and the owed write-backs carry over."""
        self.calls = dict.fromkeys(METHODS, 0)
        self.total = 0
        self.faults = []
        self.refused = []
        self.refused_total = 0
        self.stop_fuel = None

    def record(self) -> FileRecord:
        return FileRecord(
            types.MappingProxyType(dict(self.calls)),
            tuple(self.faults),
            tuple(self.refused),
            self.refused_total,
        )

    def walk(self, *, ending: bool = False) -> None:
        """The ending's write-backs, made after the guest has stopped by
        any ending that returns a result, on the call's thread, outside every host function:
        one `write` for each dirty buffer of a writable mount that is not unlinked, owed buffers
        included, in ascending provider number. Its own counted call path, never the gate: no
        cancel or deadline check (the guest is gone), never `call.ended` or the epoch or the
        fuel. Bounded by construction: at most MAX_MOUNT_FILES buffers, the staging bound in
        bytes, and the file calls left; a write-back past the limit is recorded, not made. It
        makes no call once the interpreter is exiting or a Ctrl-C is pending: no result will
        carry a record then, and provider code must not run.

        In a session the walk runs at every turn's ending: a write-back the limit refuses is
        recorded and stays dirty, to be offered again at the next ending, and an owed buffer is
        dropped once its write-back is made. A session's ending (`ending=True`) runs on purpose
        at exit, so it ignores the exiting flag that run_async's exit hook sets; a pending Ctrl-C
        still stops it."""
        for number in sorted([*self.table, *self.owed]):
            entry = self.table[number] if number in self.table else self.owed[number]
            if entry.kind != "file" or not entry.dirty or entry.unlinked:
                continue
            if (self.context.exiting() and not ending) or self.context.ctrl_c_pending():
                return
            paths = (entry.path,)
            if self.limit is not None and self.total >= self.limit:
                self._refuse(entry.mount, "write", paths, Errno.EIO, "exit", "limit")
                if self.session:
                    continue  # owed stays owed
            else:
                self._made(entry.mount, "write", "exit", paths, (bytes(entry.data),))
            entry.dirty = False
            if self.session and number in self.owed:
                del self.owed[number]
                self.opened -= 1
                heapq.heappush(self.free, number)
                self.staged -= entry.held

    def release(self) -> None:
        """Drop what the call held once it has ended: the staged files
        and listings, the trampoline's handles and the link back to the call, so nothing waits
        for the cyclic collector."""
        self.table.clear()
        self.owed.clear()
        self.mounts.clear()
        self.forwards = None
        self.stop_fuel = None
        self.staged = 0

    # The trampoline.

    def bind(self, wt: Any, store: Any, plain: Any, instance: Any) -> None:
        """Instantiate the trampoline on the guest's memory with wasmtime's own calls from
        `plain` (today's linker), and the stat trampoline on its own page. After
        the guest, before the fuel cap and `_initialize`."""
        module, stat_module = self.context.trampolines(wt, self.engine)
        imports = [plain.get(store, "wasi_snapshot_preview1", name) for name in SIGNATURES]
        imports.append(instance.exports(store)["memory"])
        exports = wt.Instance(store, module, imports).exports(store)
        stat_imports = [plain.get(store, "wasi_snapshot_preview1", name) for name in PRIVATE]
        stat = wt.Instance(store, stat_module, stat_imports).exports(store)
        from . import _wasmtime_ffi as ffi

        self.forwards = _Forwards(
            {name: ffi.raw_func(exports[name]) for name in SIGNATURES},
            {name: ffi.raw_func(stat[name]) for name in PRIVATE},
            stat["memory"],
        )

    def forward(self, caller: Any, name: str, args: tuple[int, ...], stat: bool = False) -> int:
        """wasmtime's own answer, on the caller's context, never through `Func.__call__` (whose
        exception slot is process-wide). Fuel-neutral on a metered call: read, raised by the
        allowance, and set back in a `finally` before any trap or error is raised. `stat`
        forwards one of `PRIVATE` through the guard's own trampoline, on its page.
        The engine is reached through the seam: a prepared call per name, made once."""
        from wasmtime import Trap, WasmtimeError

        from . import _wasmtime_ffi as ffi

        if self.forwards is None:
            return EBADF  # no trampoline yet: nothing of wasmtime's can be reached
        key = "stat:" + name if stat else name  # the guard trampoline's own slots
        slot = self.forwards.slots.get(key)
        if slot is None:
            func = self.forwards.stat[name] if stat else self.forwards.funcs[name]
            slot = ffi.PreparedCall(func, SIGNATURES[name])
            self.forwards.slots[key] = slot
        context = ffi.context_of(caller)  # for the call only; fuel goes by the caller
        before = ffi.get_fuel(caller) if self.metered else None
        raised: BaseException | None = None
        try:
            if before is not None:
                ffi.set_fuel(caller, min(before + FUEL_ALLOWANCE, FUEL_MAX))
            try:
                return slot.call(context, args)
            except (Trap, WasmtimeError) as e:
                raised = e
        finally:
            if before is not None:
                ffi.set_fuel(caller, before)
        assert raised is not None
        if before is not None:
            self.stop_fuel = (raised, before)
        raise raised

    # Dispatch.

    def __call__(self, caller: Any, name: str, *args: int) -> int:
        try:
            return HANDLERS[name](self, caller, *args)
        except BaseException as e:
            if self.metered and getattr(e, "abi", False):
                # An ABI error ends the run where a grant's does, with the fuel then (served
                # code spends none), as a forward's error keeps it.
                from . import _wasmtime_ffi as ffi

                self.stop_fuel = (e, ffi.get_fuel(caller))
            raise

    def _entry(self, fd: int) -> _Open | None:
        return self.table.get(fd & MASK32)

    # The provider.

    def _home(self, fn: Callable[..., _T], *args: Any) -> _T:
        """fn(*args) on the call's home thread, where the embedder's code runs:
        every step that can run a provider's code (its method, an answer's buffer
        or iteration, an exception's text) goes through here. Directly without a home."""
        return cast(_T, self.context.on_home(fn, *args))

    def _gate(self, caller: Any) -> int:
        """0, or the errno that stops a provider call while the guest runs: the call's cancel,
        its deadline, then the file-call limit, which names the end."""
        if self.context.cancelled():
            self.context.stop_now(caller)  # named "cancelled" by the callback at the next entry
            return ECANCELED
        if self.context.deadline_passed():
            self.context.stop_now(caller)  # an interrupt at the next entry: "deadline"
            return ETIMEDOUT
        if self.limit is not None and self.total >= self.limit:
            self.context.name_end("out of file calls")
            self.context.stop_now(caller)  # in the same step: the guest stops at its next entry
            return EIO
        return 0

    def _invoke(self, mount: _Mounted, method: str, args: tuple[Any, ...]) -> tuple[int, Any]:
        """The provider call itself, counted, inside the fault boundary: (0, answer), or EIO with
        the fault recorded. An OSError that names a member is that answer, as if returned;
        nothing of it is kept. A BaseException that is not an Exception is let through: it
        is the call's stop."""
        self.total += 1
        self.calls[method] += 1
        try:
            return 0, getattr(mount.provider, method)(*args)
        except Exception as e:
            if (member := _raised(e)) is not None:
                return 0, member
            self._fault(method, args[0], _described(e))
            return EIO, None

    # The write half.

    def _change(
        self, caller: Any, mount: _Mounted, method: str, at: str, paths: tuple[str, ...], *data: Any
    ) -> tuple[int, bool]:
        """One write-half call: (errno, made). Not made (cancel, deadline, limit) means the
        provider never saw it: nothing is recorded here, since the guest gets the errno and a
        write-back owed by a close or sync is recorded once, by the ending."""
        if errno := self._gate(caller):
            return errno, False
        return self._home(self._made, mount, method, at, paths, data), True

    def _made(
        self, mount: _Mounted, method: str, at: str, paths: tuple[str, ...], data: tuple[Any, ...]
    ) -> int:
        """Call the provider and judge its answer by its real type: None is success, an exact
        Errno is a refusal, anything else (an awaitable included) a fault, answered EIO. Every
        refusal and fault is recorded."""
        errno, answer = self._invoke(mount, method, (*paths, *data))
        if errno:
            self._refuse(mount, method, paths, Errno.EIO, at, "fault")
            return EIO
        try:
            if answer is None:
                return 0
            if type(answer) is Errno:  # exact: an enum with members has no subclass
                self._refuse(mount, method, paths, answer, at, "refused")
                return int(answer)
            self._bad(method, paths[0], answer)
        except Exception as e:
            self._fault(method, paths[0], _described(e))
        self._refuse(mount, method, paths, Errno.EIO, at, "fault")
        return EIO

    def _refuse(
        self,
        mount: _Mounted,
        method: str,
        paths: tuple[str, ...],
        errno: Errno,
        at: str,
        cause: str,
    ) -> None:
        self.refused_total += 1
        if len(self.refused) < REFUSED_KEPT:
            self.refused.append(RefusedWrite(mount.guest, method, paths, errno, at, cause))

    def _fault(self, method: str, path: str, error: str) -> None:
        if len(self.faults) < FAULTS_KEPT:
            self.faults.append(FileFault(method, path, error[:200]))

    def _bad(self, method: str, path: str, answer: object) -> int:
        if type(answer) is types.CoroutineType:
            try:
                answer.close()  # never awaited, never warned about
            except Exception:
                pass
        self._fault(method, path, f"bad answer: {type(answer).__name__}")
        return EIO

    def _stat(self, caller: Any, mount: _Mounted, path: str) -> tuple[int, str, int, int]:
        """(0, kind, size, mtime_ns), or (errno, "", 0, 0). Every answer is judged by its real
        type, which runs no provider code; what is left to look at runs inside the boundary, on
        the home thread (a `Stat` subclass's properties are the provider's code)."""
        if errno := self._gate(caller):
            return errno, "", 0, 0
        return self._home(self._stat_answer, mount, path)

    def _stat_answer(self, mount: _Mounted, path: str) -> tuple[int, str, int, int]:
        errno, answer = self._invoke(mount, "stat", (path,))
        if errno:
            return errno, "", 0, 0
        try:
            if type(answer) is Errno:  # exact: an enum with members has no subclass
                return int(answer), "", 0, 0
            if issubclass(type(answer), Stat):
                kind, size, mtime = answer.kind, answer.size, answer.mtime_ns
                if (
                    _kind(kind)
                    and _number(size, 2**63 - 1)
                    and _number(mtime, MASK64)
                    and (path != "/" or kind == "dir")
                ):
                    return 0, kind, int.__index__(size), int.__index__(mtime)
            return self._bad("stat", path, answer), "", 0, 0
        except Exception as e:
            self._fault("stat", path, _described(e))
            return EIO, "", 0, 0

    def _read(
        self, caller: Any, mount: _Mounted, path: str, buffer: bool = False
    ) -> tuple[int, bytes | bytearray | None]:
        """(0, bytes) for a file (a bytearray when `buffer`, for a descriptor that may write),
        (0, None) for a folder (EISDIR), or (errno, None). The answer is taken as a buffer on the
        home thread, where its buffer export, the provider's code, runs."""
        if errno := self._gate(caller):
            return errno, None
        return self._home(self._read_answer, mount, path, buffer)

    def _read_answer(
        self, mount: _Mounted, path: str, buffer: bool
    ) -> tuple[int, bytes | bytearray | None]:
        errno, answer = self._invoke(mount, "read", (path,))
        if errno:
            return errno, None
        try:
            if type(answer) is Errno:
                return (0, None) if answer is Errno.EISDIR else (int(answer), None)
            if not issubclass(type(answer), (bytes, bytearray, memoryview)):
                return self._bad("read", path, answer), None
            with memoryview(answer) as view:  # judged in bytes before any copy
                if self.staged + view.nbytes > self.staging:
                    return EFBIG, None
                return 0, (bytearray(view) if buffer else view.tobytes())
        except Exception as e:
            self._fault("read", path, _described(e))
            return EIO, None

    def _list(
        self, caller: Any, mount: _Mounted, path: str, ino: int, released: int = 0
    ) -> tuple[int, _Listing | None, int]:
        """(0, listing, bytes held), the dots first, or (errno, None, 0). A listing is kept as
        what the guest is served: one buffer of encoded preview1 entries (each its 24-byte
        header, `d_next` included, then its name) and an array of where each starts. It is
        judged against the staging bound as it is gathered, counting the bytes allocated for
        the buffer, the array and the set of names that finds a repeat; once gathered, it holds
        the buffer and the array. Every name is checked before the guest sees it. The call and
        the whole gathering (iter, each next, close) run on the home thread, so a generator
        `list` runs its body there."""
        if errno := self._gate(caller):
            return errno, None, 0
        return self._home(self._list_answer, mount, path, ino, released)

    def _list_answer(
        self, mount: _Mounted, path: str, ino: int, released: int
    ) -> tuple[int, _Listing | None, int]:
        errno, answer = self._invoke(mount, "list", (path,))
        if errno:
            return errno, None, 0
        iterator = None
        try:
            if type(answer) is Errno:
                return int(answer), None, 0
            kind_of = type(answer)
            if not issubclass(kind_of, Iterable) or issubclass(
                kind_of, (str, bytes, bytearray, memoryview)
            ):
                return self._bad("list", path, answer), None, 0
            data, offsets = _dots(ino)
            seen: set[bytes] = set()
            names = 0  # the bytes of the name objects the set holds
            prefix = path.rstrip("/") + "/"
            # iter() and each next() run the listing's own code, a generator method's body
            # included: an OSError there is the answer of its errno too.
            try:
                iterator = iter(answer)
            except Exception as e:
                return self._listing_raised(path, e), None, 0
            while True:
                try:
                    item = next(iterator)
                except StopIteration:
                    break
                except Exception as e:
                    return self._listing_raised(path, e), None, 0
                listed = _listed(item)
                if listed is None or listed[1] in seen:
                    return self._bad("list", path, answer), None, 0
                text, encoded, kind = listed
                seen.add(encoded)
                names += sys.getsizeof(encoded)
                child = self.context.ino_of(prefix + text)
                d_type = DIRECTORY if kind == "dir" else REGULAR_FILE
                offsets.append(len(data))
                data += struct.pack(DIRENT, len(offsets), child, len(encoded), d_type) + encoded
                gathering = sys.getsizeof(data) + sys.getsizeof(offsets)
                gathering += sys.getsizeof(seen) + names
                if self.staged - released + gathering > self.staging:
                    return EFBIG, None, 0
            return 0, (data, offsets), sys.getsizeof(data) + sys.getsizeof(offsets)
        except Exception as e:
            self._fault("list", path, _described(e))
            return EIO, None, 0
        finally:
            _close(iterator)

    def _listing_raised(self, path: str, e: Exception) -> int:
        """The errno for an exception the listing raised: its member's, or EIO with
        the fault recorded."""
        if (member := _raised(e)) is not None:
            return int(member)
        self._fault("list", path, _described(e))
        return EIO

    # Numbers and staging.

    def _take(self, entry: _Open) -> int:
        number = heapq.heappop(self.free) if self.free else self.next
        if number == self.next:
            self.next += 1
        self.table[number] = entry
        self.opened += 1
        self.staged += entry.held
        return number

    def _drop(self, number: int) -> None:
        entry = self.table.pop(number)
        if not entry.preopen:
            self.opened -= 1
            heapq.heappush(self.free, number)
        self.staged -= entry.held

    # The state the calls change: each write a call makes to the table is one of these.

    def _write_back(self, caller: Any, entry: _Open, at: str) -> tuple[int, bool]:
        """A dirty buffer's whole content handed to the provider, at close or sync: (errno,
        made). On success the buffer is clean; on a refusal it stays dirty."""
        if errno := self._gate(caller):
            return errno, False  # not made: owed at a close, still dirty at a sync
        data = bytes(entry.data)  # a copy the provider may keep, made only for a call that is made
        if (errno := self._made(entry.mount, "write", at, (entry.path,), (data,))) == 0:
            entry.dirty = False
        return errno, True

    def _fits(self, entry: _Open, size: int) -> bool:
        """Whether a buffer may become `size` bytes: judged against the staging bound on the new
        size, before a byte is allocated."""
        return size <= len(entry.data) or self.staged - entry.held + size <= self.staging

    def _changed(self, entry: _Open) -> None:
        """A buffer was written or resized: counted at its size, and dirty, even when its bytes
        are the same, as a grant's file has its mtime touched."""
        self.staged += len(entry.data) - entry.held
        entry.held = len(entry.data)
        entry.dirty = True

    def _follow(self, mount: _Mounted, src: str, dst: str | None = None) -> None:
        """After `remove(src)` or `rmdir(src)` (no `dst`), or `rename(src, dst)`, succeeded,
        this call's descriptors follow it, as POSIX's follow the file: those at the
        removed path, or at or under the rename's `dst`, are unlinked; then those at or under its
        `src` take the same path under `dst`. Owed buffers follow too: their bytes are the
        file's."""
        entries = [e for e in (*self.table.values(), *self.owed.values()) if e.mount is mount]
        live = [e for e in entries if not e.preopen and not e.unlinked]
        for e in live:
            if dst is None and e.path == src:
                self._unlink(e)
            elif dst is not None and (e.path == dst or e.path.startswith(dst + "/")):
                self._unlink(e)
        if dst is not None:
            for e in live:
                if not e.unlinked and (e.path == src or e.path.startswith(src + "/")):
                    e.path = dst + e.path[len(src) :]

    def _unlink(self, entry: _Open) -> None:
        """A descriptor whose path the guest removed or replaced: a file keeps its buffer for
        reads and writes and is never written back; a folder holds nothing from now on, its
        kept listing replaced by the dots."""
        entry.unlinked = True
        if entry.kind == "dir":
            listing = _dots(self.context.ino_of(entry.path))
            held = sys.getsizeof(listing[0]) + sys.getsizeof(listing[1])
            self.staged += held - entry.held
            entry.listing, entry.held, entry.fresh = listing, held, True

    def _hold(self, number: int) -> None:
        """A number wasmtime gave the guest at an open: it holds a slot under the cap."""
        self.held.add(number)

    def _unhold(self, number: int) -> None:
        """A number of wasmtime's the guest closed: its slot is free."""
        self.held.discard(number)

    def _renumbered(self, a: int, b: int) -> None:
        """wasmtime renumbered `a` onto `b`: `b`'s file is closed and `a`'s moved there."""
        self.held.discard(b)
        if a in self.held:
            self.held.discard(a)
            self.held.add(b)

    def _owe(self, number: int, entry: _Open) -> None:
        """Closed for the guest with its write-back not made: out of the table, so no call
        finds it, and owed, so no open reuses the number and its bytes stay counted."""
        del self.table[number]
        self.owed[number] = entry

    def _relist(self, entry: _Open, listing: _Listing | None, held: int) -> None:
        """A folder listed again: it keeps the new listing, counted at what it holds."""
        self.staged += held - entry.held
        entry.listing, entry.held, entry.fresh = listing, held, True


def _described(e: BaseException) -> str:
    """An exception's type name and the first line of its text; total: it runs no provider
    code it cannot survive (a metaclass's `__name__`, a `__str__` returning a str subclass) and
    formats nothing but plain str."""
    try:
        name = type.__dict__["__name__"].__get__(type(e))  # the type's own name, not a property's
        if type(name) is not str:
            name = "an exception"
    except Exception:
        name = "an exception"
    try:
        text = str(e)
        if type(text) is not str:
            return name
        lines = str.splitlines(str.strip(text))
    except Exception:
        return name
    return f"{name}: {lines[0]}" if lines else name


def _dots(ino: int) -> _Listing:
    """A listing's first two entries, `.` and `..`, encoded as wasmtime writes them."""
    data, offsets = bytearray(), array("I")
    for index, name in enumerate((b".", b"..")):
        offsets.append(len(data))
        data += struct.pack(DIRENT, index + 1, ino, len(name), DIRECTORY) + name
    return data, offsets


def _kind(value: object) -> bool:
    return type(value) is str and value in ("file", "dir")


def _number(value: Any, top: int) -> bool:
    kind = type(value)
    if issubclass(kind, bool) or not issubclass(kind, int):
        return False
    return 0 <= int.__index__(value) <= top


def _listed(item: object) -> tuple[str, bytes, str] | None:
    """A listing entry as (name, its UTF-8, kind), or None when it is outside the protocol: a
    plain tuple of two plain str (so no provider code runs to take it apart)."""
    if type(item) is not tuple or len(item) != 2:
        return None
    name, kind = item
    if type(name) is not str or not _kind(kind):
        return None
    if name in ("", ".", "..") or "/" in name or "\0" in name:
        return None
    try:
        encoded = name.encode("utf-8")
    except UnicodeEncodeError:
        return None  # a lone surrogate
    if len(encoded) > MAX_NAME:
        return None
    return name, encoded, kind


def _close(iterator: object) -> None:
    """Close a provider's iterator, as a for loop left early would not; never raising."""
    if iterator is None:
        return
    try:
        close = getattr(iterator, "close", None)
        if close is not None:
            close()
    except Exception:
        pass
