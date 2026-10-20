"""One call: `Completed`, the checked run and the instance, the driver and `_Call`, the
host-function wrapper and the epoch callback, the linkers and trampolines, the output streams,
`poll_oneoff`, the door and the tool host."""

from __future__ import annotations

import contextvars
import ctypes
import functools
import math
import os
import secrets
import struct
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

from . import _artifacts, _engines, _home, _places, _platform, _private_dirs, _zip
from ._artifacts import GUEST_PACKAGE, Artifacts, ArtifactsMissing
from ._engines import _epoch_ticker
from ._home import _Home, _Stopped
from ._limits import CANCEL_TICKS, NO_DEADLINE, TICK_S
from ._places import ZIP_GUEST, Grant, _Preopen, _Walked
from ._platform import _TRAP_HANDLERS_REPLACED
from ._private_dirs import _Private
from ._process import process
from ._zip import MPL_DATA_GUEST
from .mounts import STAGING_CEILING, FileRecord, Mount

if TYPE_CHECKING:
    import wasmtime

    from .tools import ToolRecord, _ToolHost

ARGV0 = "/usr/local/bin/python.wasm"
NO_HOST = -1
HOST_FAULT = -2
MASK32 = 0xFFFFFFFF
UNMETERED = 2**63 - 1  # the budget instantiation runs on, before the cap is set (spec 008)
MAX_RESPONSE = 0x7FFFFFFF  # the largest door response: its length must fit a signed i32
# The guest's environment before the caller's `env`. HOME is added per call: a fresh, empty
# directory under /tmp that the runner removes afterwards, so nothing a call leaves in its HOME
# (pdb's .pdbrc, for one) is read by the next (spec 006, Decision 2).
BASE_ENV = {"TMPDIR": "/tmp", "PYTHONTZPATH": ""}

Host = Callable[[bytes], bytes]


@dataclass(frozen=True)
class Completed:
    """How one program ended: what `run` returns.

    Attributes:
        exit_code: The program's exit status: its return value, or the code it passed to exit.
            `None` when it trapped.
        stdout: What the guest wrote to standard output, up to the output limit.
        stderr: What the guest wrote to standard error, up to the output limit.
        trapped: `None` when the program ended by itself. Otherwise one of four fixed strings,
            "out of fuel", "deadline", "cancelled" or "out of file calls", or wasmtime's words:
            a trap's plain name ("stack overflow"), or an error's first line. The four strings
            are promised; wasmtime's words are not.
        fuel_used: The guest's instructions spent, when a `fuel` cap was given and no deadline
            hit; else `None`.
        truncated: The streams ("stdout", "stderr") whose output passed the limit.
        files: For a call with mounts, its provider calls, faults and refused writes; else
            `None`.
        tools: For a call with tools, every frame counted and the first 1,000 listed; else
            `None`.
    """

    exit_code: int | None
    stdout: bytes
    stderr: bytes
    trapped: str | None
    fuel_used: int | None
    truncated: tuple[str, ...] = ()
    files: FileRecord | None = None  # spec 032
    tools: ToolRecord | None = None  # spec 036


def _run_checked(
    wt: Any,
    c: dict[str, Any],
    host: Host | None,
    snapshot: bool,
    cache_dir: str | os.PathLike[str] | None | bool,
    artifacts: Artifacts | None,
) -> Completed:
    found, checked = (
        (artifacts, None) if artifacts is not None else _artifacts._found_and_checked(snapshot)
    )
    if c.get("tools") is not None and not _artifacts._has_guest_package(found.manifest):
        raise ArtifactsMissing(
            f"{found.manifest} has no `recipe … {GUEST_PACKAGE}` line: this artifact set "
            "predates the tool protocol (spec 031), so its guest cannot `from host import "
            "tools`; tools= needs a set built with the guest package"
        )
    cache = _engines._cache_dir(cache_dir)
    root = c["root"]
    entries, serving = c.get("import_path", ()), c.get("import_serving", ())
    walked_root, walked = _places._walk_grants(root, c["grants"], found, cache, entries, serving)
    preopens: list[_Preopen] = []
    private = None
    home = c.get("home") or _Home()  # this thread, while the guest runs on its own (spec 078)
    c = {**c, "home": home}
    try:
        after_walk = process().observers.after_walk
        if after_walk is not None:
            after_walk()
        binary = found.snapshot if snapshot else found.plain
        engine = _engines._engine(c["fuel"] is not None)
        want = None if checked is None else checked.binary
        module = _engines._module(engine, c["fuel"] is not None, binary, cache, want)
        zip_want = None if checked is None else checked.zip
        root_path, private = _preopens(found, root, walked_root, walked, preopens, zip_want)
        return _call(wt, engine, module, root_path, preopens, c, host)
    finally:

        def release() -> None:
            # Windows holds every walked folder until here; a private root can be removed only
            # after.
            for w in [walked_root, *(w for _, _, w in walked), *(p.walked for p in preopens)]:
                if w is not None:
                    w.close()
            if private is not None:
                private.remove()

        home.finish(release)  # never while a guest thread runs (spec 078, Decision 14)


def _preopens(
    found: Artifacts,
    root: str | bool | None,
    walked_root: _Walked | None,
    walked: list[tuple[str, Grant, _Walked]],
    preopens: list[_Preopen],
    zip_want: str | None = None,
) -> tuple[Path | None, _Private | None]:
    """The zip's folder, matplotlib's data, the root and the grants, appended to `preopens` in
    the order wasmtime opens them; (the root's path, a private root to remove or None). Shared by
    a call and a session's opening (spec 055). `zip_want` is the zip's checked digest, for a set
    the runner found (spec 087, Decision 10)."""
    _private_dirs._sweep_once()
    folder = _zip._zip_folder(found, zip_want)
    preopens.append(
        _Preopen(
            "the stdlib folder", _places._walk("", str(folder.lib), judge=False), ZIP_GUEST, False
        )
    )
    if folder.data is not None:  # after the zip's grant (spec 023, Decision 5)
        guest = f"{ZIP_GUEST}/{folder.name}/{MPL_DATA_GUEST}"
        walked_data = _places._walk("", str(folder.data), judge=False)
        preopens.append(_Preopen("matplotlib's data", walked_data, guest, False))
    root_path = None
    private = None
    if root is None:
        private = _Private("wasi-python-root-")  # 0700, this user's own, locked (spec 016)
        try:
            (private.path / "usr" / "local" / "lib").mkdir(parents=True)
            root_path = private.path
            walked_private = _places._walk("", str(root_path), judge=False)
        except BaseException:
            private.remove()
            raise
        preopens.append(_Preopen("the private root", walked_private, "/", True))
    elif walked_root is not None:
        root_path = Path(walked_root.path)
        # Real folders, never a guest's link: without them /usr would vanish from a fresh
        # root's listing, and the zip's path could resolve into a file a guest wrote. Made
        # through the walked folder, never its path, which another guest may have swapped
        # since the walk (spec 024).
        if walked_root.fd is not None and _platform._dir_fd_ok():
            os.close(_places._real_dir_at(walked_root.fd, ("usr", "local", "lib")))
        else:
            _places._real_dir(root_path, ("usr", "local", "lib"))
        preopens.append(_Preopen("root", walked_root, "/", True))
    for where, grant, w in walked:
        preopens.append(_Preopen(where, w, grant.guest, grant.writable))
    return root_path, private


def _home_of(c: dict[str, Any]) -> _Home:
    """The call's home thread (spec 078): the one `_run_checked` made, or one made here for a call
    built by hand (the judge's stand-ins)."""
    home = c.get("home")
    if home is None:
        home = c["home"] = _Home()
    return home


def _call(
    wt: Any,
    engine: wasmtime.Engine,
    module: wasmtime.Module,
    root: Path | None,
    preopens: list[_Preopen],
    c: dict[str, Any],
    host: Host | None,
) -> Completed:
    """One instance, one program. The store is closed before this returns, trapped or not, so the
    guest's memory and open files are released at once (a trapped store is otherwise kept alive by
    a reference cycle until Python's collector runs) and a private root can be removed afterwards
    (Windows refuses to remove an open directory). Ctrl-C is deferred while the guest runs."""
    with _home._deferred_ctrl_c():
        return _call_deferred(wt, engine, module, root, preopens, c, host)


def _call_deferred(
    wt: Any,
    engine: wasmtime.Engine,
    module: wasmtime.Module,
    root: Path | None,
    preopens: list[_Preopen],
    c: dict[str, Any],
    host: Host | None,
) -> Completed:
    tmp, tmp_fd = _home_folder(root, preopens, tuple(m.guest for m in c.get("mounts", ())))
    home = None
    if tmp is not None:
        # The fresh HOME is made, and removed, through a handle on /tmp opened without following a
        # link, so a guest running concurrently on the same folder cannot turn /tmp into a link
        # between the check and the mkdir (Windows has no dir_fd; its guests can make links only
        # where the user holds the symbolic-link privilege, spec 084).
        name = f".home-{secrets.token_hex(16)}"
        try:
            if tmp_fd is not None:
                os.mkdir(name, dir_fd=tmp_fd)
            else:
                (tmp / name).mkdir()
        except BaseException:
            _platform._close(tmp_fd)
            raise
        home = (name, f"/tmp/{name}")
    store = wt.Store(engine)
    try:
        guest_home = None if home is None else home[1]
        return _instance(wt, engine, module, store, preopens, guest_home, c, host)
    finally:

        def release() -> None:
            store.close()
            if home is not None:
                _private_dirs._remove_fresh_home(home[0], tmp, tmp_fd)
            _platform._close(tmp_fd)

        _home_of(c).finish(release)  # never while a guest thread runs (spec 078, Decision 14)


def _home_folder(
    root: Path | None, preopens: list[_Preopen], mounted: tuple[str, ...] = ()
) -> tuple[Path | None, int | None]:
    """Where HOME is made (Decision 3): a writable grant at /tmp, else the root's tmp, else
    nowhere. A read-only grant at /tmp hides the root's tmp, so then there is no HOME either, and
    a mount at /tmp counts as one (spec 032): the runner makes nothing in a mount."""
    if "/tmp" in mounted:
        return None, None
    at_tmp = [p for p in preopens if p.guest == "/tmp"]
    if at_tmp:
        p = at_tmp[0]
        if not p.writable:
            return None, None
        fd = p.walked.fd
        return Path(p.walked.path), (
            os.dup(fd) if fd is not None and _platform._dir_fd_ok() else None
        )
    if root is None:
        return None, None
    # TMPDIR, a real folder (a guest's link there is removed), made through the root's walked
    # folder, never its path (spec 024).
    fd = next(p.walked.fd for p in preopens if p.guest == "/")
    if fd is not None and _platform._dir_fd_ok():
        return root / "tmp", _places._real_dir_at(fd, ("tmp",))
    return _places._real_dir(root, ("tmp",)), None


def _import_prelude(entries: tuple[str, ...]) -> list[str]:
    """The `-c` prelude that puts the import path on `sys.path` (spec 054, Decision 7): one
    expression statement that binds no name in `__main__`. It drops the `linecache` entry the
    reactor registered for it, so no later `exec` or `eval` of a string shows its source; extends
    `sys.path` after the stdlib zip; and runs the caller's argv through the reactor's own
    argument handling, whose exit code it returns. `entries` are the plain strings
    `_check_import_path` kept, so `repr` is `str`'s own. No entries, no prelude: the argv is
    today's."""
    if not entries:
        return []
    plain = [str.__str__(e) for e in entries]
    line = (
        "__import__('linecache')._interactive_cache.clear() or "
        f"__import__('sys').path.extend({plain!r}) or "
        "__import__('sys').exit(__import__('_reactor').run("
        f"[{ARGV0!r}, *__import__('sys').argv[1:]], dict(__import__('os').environ)))"
    )
    return ["-c", line]


def _instance(
    wt: Any,
    engine: wasmtime.Engine,
    module: wasmtime.Module,
    store: wasmtime.Store,
    preopens: list[_Preopen],
    home: str | None,
    c: dict[str, Any],
    host: Host | None,
) -> Completed:
    argv, env, stdin, cancel = c["argv"], c["env"], c["stdin"], c["cancel"]
    fuel, deadline_s = c["fuel"], c["deadline_s"]
    memory_bytes, output_bytes = c["memory_bytes"], c["output_bytes"]
    if fuel is not None:
        # Fuel is metered from the end of instantiation (spec 008): instantiation runs only
        # wasmtime's own memory fill, which it charges per byte when it cannot map the image
        # (macOS when compiled in the process, Windows always); the guest's work starts after.
        store.set_fuel(UNMETERED)
    if memory_bytes is not None:
        store.set_limits(memory_size=memory_bytes)
    ticks = NO_DEADLINE if deadline_s is None else max(1, math.ceil(deadline_s / TICK_S))
    # A call with `cancel` is first checked within CANCEL_TICKS ticks, whatever its deadline; its
    # callback then enforces the deadline too (spec 015).
    # Every call is polled every CANCEL_TICKS ticks (spec 078, Decision 5): so Ctrl-C, and an
    # exception raised into the home thread, reach a guest that never calls back.
    store.set_epoch_deadline(min(CANCEL_TICKS, ticks))
    ht = _home_of(c)  # the home thread (spec 078); `home` is the guest's HOME
    # The ticker's count at which this store's deadline has passed, read after the deadline is set
    # (spec 010): a wait in poll_oneoff stops there, so it never outlives the deadline.
    stop_at = None if deadline_s is None else _stop_at(_epoch_ticker.count(), ticks)
    checks = [] if stop_at is None else [lambda: _epoch_ticker.count() >= stop_at]
    if cancel is not None:
        checks.append(cancel.is_set)  # a wait ends at a cancel, deadline or not
    if _home._ctrl_c_watched():
        checks.append(lambda: process().ctrl_c_pending)  # a wait on the main thread ends at Ctrl-C
    checks.append(ht.stopped)  # and at an exception raised into the home (spec 078, C1)
    waits = _Waits(
        lambda: time.perf_counter(),
        time.sleep,
        (lambda: any(check() for check in checks)) if checks else None,
    )
    # Under tools=, the runner is the door's host: the frame host, bound by the same deadline,
    # cancel and Ctrl-C, and asked to admit each frame by its length before it is read (036).
    tool_host = _tool_host(c, stop_at, cancel, ht)
    admit = None
    if tool_host is not None:
        host, admit = tool_host, tool_host.admit

    out, err = _Stream("stdout", output_bytes), _Stream("stderr", output_bytes)
    wasi = wt.WasiConfig()
    origin_ns = time.perf_counter_ns()  # wasmtime's monotonic clock counts from here (spec 010)
    wasi.argv = [ARGV0, *_import_prelude(c.get("import_path", ())), *argv]
    fresh = {} if home is None else {"HOME": home}  # no HOME where there is no /tmp to make it
    wasi.env = sorted({**BASE_ENV, **fresh, **(env or {})}.items())
    check = _engines._check_module(wt, engine, fuel is not None)
    keys = _send_outputs(wasi, out, err)
    scratch = None
    mounts: tuple[Mount, ...] = c.get("mounts", ())
    mounted: list[_Preopen] = []  # each mount's preopen, on the call's empty placeholder
    table = None
    files = None
    try:
        # 0700, this user's own, locked (spec 016); made before the preopens, since it holds the
        # mounts' placeholder, which lies under the temporary folder no grant may reach (spec 032).
        scratch = _Private("wasi-python-")
        if mounts:
            placeholder = scratch.path / "mount"
            placeholder.mkdir()
            for i, mount in enumerate(mounts):
                walked = _places._walk("", str(placeholder), judge=False)
                mounted.append(
                    _Preopen(f"mounts[{i}] at {mount.guest}", walked, mount.guest, False)
                )
        every = [*preopens, *mounted]
        for p in every:  # the stdlib folder first; wasi-libc picks by the longest guest prefix
            wasi.preopen_dir(p.walked.path, p.guest, p.writable)
        stdin_path = scratch.path / "stdin"
        stdin_path.write_bytes(stdin or b"")
        wasi.stdin_file = str(stdin_path)
        store.set_wasi(wasi)
        linker = _linker(wt, engine)  # held for the whole call: clearing the cache cannot free it
        from .mounts import _Files

        staging = STAGING_CEILING if memory_bytes is None else memory_bytes
        others = [p.guest for p in preopens]
        if mounts:
            guest_linker = _mount_linker(wt, engine)
            first = 3 + len(preopens)  # the mounts' preopens come after every other
            numbers = [(mount, first + i) for i, mount in enumerate(mounts)]
        else:
            # A call without mounts: the guard linker, today's but for fd_readdir and
            # path_rename, served by a table with no mounts, which forwards both with wasmtime
            # 49.0.2's and 49.0.3's fixes (spec 048, Decision 7).
            guest_linker = _guard_linker(wt, engine)
            numbers = []
        table = _Files(
            numbers,
            others,
            c["file_calls"],
            staging,
            fuel is not None,
            engine,
            open_files=c["open_files"],  # spec 068: strict, as file_calls
        )
        call = _Call(store, host, waits, origin_ns, cancel, stop_at, table, admit, home=ht)
        _watch(store)  # every call (spec 078, Decision 5)
        with _epoch_ticker(engine, True):
            drive = functools.partial(_drive, plain=linker)
            args = (wt, guest_linker, store, module, call, fuel, every, check)
            done = _home._on_guest_thread("run", ht, call, drive, *args)
        fuel_used = _fuel_used(fuel, done, call, store.get_fuel)
        # Spec 034, Decision 8: what the guest wrote is handed over at every ending that returns
        # a result, after the fuel is read; a call that raises never gets here. Every call has a
        # table since spec 048; a guard table's walk does nothing (no mount, nothing owed).
        table.walk()
    finally:
        if ht.done and table is not None:  # the record kept (the build review, F3)
            # A guard table is never reported: `files` is None without mounts (spec 048).
            files = table.record() if mounts else None

        def release() -> None:
            if tool_host is not None:  # the call's tool loop, ended without waiting (spec 053)
                tool_host.close()
            # The store holds every descriptor the guest opened; a guest can open them until the
            # host refuses. Close it first, so the clean-up below has descriptors to work with,
            # and make that clean-up unable to raise (the 0.1.0a2 security review, F1).
            store.close()
            with process().outputs_lock:  # the guest has ended; wasmtime frees the keys later
                for key in keys:
                    process().outputs.pop(key, None)
            if table is not None:  # the rest dropped now (the build review, F3)
                table.release()
            for p in mounted:
                p.walked.close()
            if scratch is not None:
                scratch.remove()

        ht.finish(release)  # never while a guest thread runs (spec 078, Decision 14)
    truncated = tuple(s.name for s in (out, err) if s.dropped)
    record = None if tool_host is None else tool_host.record  # on every ending (C6)
    return Completed(
        done.exit_code,
        bytes(out.data),
        bytes(err.data),
        done.trapped,
        fuel_used,
        truncated,
        files,
        record,
    )


def _fuel_used(
    fuel: int | None, done: _Driven, call: _Call, remaining: Callable[[], int]
) -> int | None:
    """The instructions the guest ran, or None when the count is meaningless: after an epoch
    interrupt wasmtime's fuel counter is not brought up to date (spec 001 landing notes), and a
    stopped call ended on one (spec 011)."""
    if fuel is None or done.trapped == "deadline":
        return None
    table = getattr(call, "table", None)
    held = None if table is None else table.stop_fuel
    if held is not None and call.ended is None and call.stopped is held[0]:
        # A forward's own trap or error, or an ABI error a served call raised (spec 032): the
        # count read then is the guest's, as when wasmtime's WASI meets it directly.
        return fuel - held[1]
    if call.stopped is not None or call.ended is not None:
        return None
    return fuel - remaining() if done.metered else 0


class _Driven(NamedTuple):
    exit_code: int | None
    trapped: str | None
    metered: bool  # the cap is set only once instantiation has succeeded
    instance: Any


def _drive(
    wt: Any,
    linker: Any,
    store: Any,
    module: Any,
    call: _Call,
    fuel: int | None,
    preopens: list[_Preopen] = (),  # type: ignore[assignment]
    check: Any = None,
    plain: Any = None,
) -> _Driven:
    """Instantiate and run the guest with its call on this thread's stack. What a host function
    caught and recorded comes first: an exit or a trap is the call's result, and any other
    exception (Ctrl-C, a host's cancellation) is raised here, on the thread that made the call
    (spec 011). `plain` is today's linker when `linker` is the mount linker: the identity check
    reads wasmtime's own answers through it, and the trampoline takes wasmtime's calls from it
    (spec 032)."""
    not_ready = (
        _platform._trap_handlers_ready()
    )  # spec 071, Decision 9: before every entry into the guest
    if not_ready is not None:
        raise RuntimeError(_TRAP_HANDLERS_REPLACED.format(signal=not_ready))
    exit_code: int | None = None
    trapped: str | None = None
    metered = False
    instance = None
    stack = _home._stack()
    stack.append(call)
    process().calls.lost = False
    try:
        if call.cancel is not None and call.cancel.is_set():  # cancelled before the guest ran
            call.ended = "cancelled"
            return _Driven(None, "cancelled", False, None)
        own = linker if plain is None else plain
        if preopens:
            _places._check_preopens(wt, own, store, check, list(preopens))  # spec 017, Decision 5
        instance = linker.instantiate(store, module)
        if call.table is not None:  # after the guest, before the fuel cap and _initialize
            call.table.bind(wt, store, own, instance)
        if fuel is not None:
            store.set_fuel(fuel)
            metered = True
        exports = instance.exports(store)
        if "_initialize" in exports:
            exports["_initialize"](store)
        exit_code = exports["run"](store)
    except wt.ExitTrap as e:
        exit_code = e.code
    except wt.Trap as e:
        trapped = _trap_name(e)
        e.__traceback__ = None  # its frames hold this call: freed now, not by the collector
    except wt.WasmtimeError as e:
        trapped = _first_line(str(e))
        e.__traceback__ = None
    finally:
        stack.pop()
        calls = process().calls
        lost, calls.lost = getattr(calls, "lost", False), False
    if lost:
        raise RuntimeError("wasi_python lost track of a call")
    cause = call.stopped
    if cause is not None:
        exit_code, trapped = None, None
        if isinstance(cause, wt.ExitTrap):
            exit_code = cause.code
        elif isinstance(cause, wt.Trap):
            trapped = _trap_name(cause)
        elif isinstance(cause, wt.WasmtimeError):
            trapped = _first_line(str(cause))
        else:
            raise cause
        cause.__traceback__ = None  # a reported stop's frames hold this call (spec 032, F3)
    elif call.ended is not None:  # the epoch callback stopped it (spec 015)
        exit_code, trapped = None, call.ended
    return _Driven(exit_code, trapped, metered, instance)


class _Call:
    """One call's state, which the shared host functions find on the calling thread's stack: its
    door, its poll_oneoff, its store's context address, and the first exception they caught; for
    a call with `cancel`, the event, the ticker count its deadline passes at, and the outcome the
    epoch callback recorded (spec 015)."""

    def __init__(
        self,
        store: Any,
        host: Host | None,
        waits: Any,
        origin_ns: int,
        cancel: threading.Event | None = None,
        stop_at: int | None = None,
        table: Any = None,
        admit: Callable[[int], bytes | None] | None = None,
        *,
        home: Any = None,
    ) -> None:
        from . import _wasmtime_ffi as ffi

        self.context = ffi.context_address(store)
        self.origin_ns = origin_ns  # its waits count from here (spec 055, the review's F6)
        # The thread that made the call, which runs the embedder's code (spec 078, Decision 4);
        # None calls it directly (the judge's stand-ins).
        self.home = home
        # admit: the frame host's, under tools= (spec 036), whose host is the runner's own code
        self.door = _door(host, admit, home if admit is None else None)
        self.poll = _poll_oneoff(origin_ns, waits)
        self.stopped: BaseException | None = None
        self.cancel = cancel
        self.stop_at = stop_at
        # "cancelled" or "deadline", from the epoch callback; "out of file calls" (spec 032)
        self.ended: str | None = None
        self.table = table  # the call's mount table (spec 032), or its guard table (spec 048)
        if table is not None:
            table.call = self

    def files(self, caller: Any, name: str, *args: int) -> int:
        """One of the 29 shadowed calls, for a call with mounts (spec 032), or one of the two
        the guard shadows, for a call without (spec 048)."""
        if self.table is None:
            return EBADF
        return self.table(caller, name, *args)

    def stop(self, caller: Any, cause: BaseException) -> None:
        """Record the cause and stop the guest: an epoch deadline of 0, set through the caller's
        context, traps it at its next function entry, with nothing raised through wasmtime-py."""
        if self.stopped is None:
            self.stopped = cause
        from . import _wasmtime_ffi as ffi

        ffi.set_epoch_deadline(caller, 0)


def _shared(kind: str, refused: int, stopped: int, *bound: Any) -> Callable[..., int]:
    """A host function defined once per engine. It serves the call on top of this thread's
    stack, and only when the caller is that call's store; it never raises into wasmtime-py,
    whose exceptions travel by a process-wide slot (spec 011). `bound` goes before the guest's
    arguments: a file shadow's name (spec 032)."""

    import wasmtime as wt

    from . import _wasmtime_ffi as ffi

    wasmtime_errors = (wt.Trap, wt.WasmtimeError)

    def function(caller: Any, *args: int) -> int:
        call = None
        try:
            stack = _home._stack()
            call = stack[-1] if stack else None
            if call is None or ffi.context_address(caller) != call.context:
                return refused
            # Ctrl-C comes before the guard below: a pending Ctrl-C is recorded even for a call
            # the epoch callback has ended (spec 015's order).
            if call.stopped is None and _home._ctrl_c_watched() and process().ctrl_c_pending:
                process().ctrl_c_pending = False
                raise KeyboardInterrupt
            if call.stopped is not None or call.ended is not None:
                return stopped  # no host function runs for a stopped or ended call (spec 030)
            answer = getattr(call, kind)(caller, *bound, *args)
            if _home._ctrl_c_watched() and process().ctrl_c_pending:  # Ctrl-C during a wait
                process().ctrl_c_pending = False
                raise KeyboardInterrupt
            if call.cancel is not None and call.cancel.is_set():
                _epoch_now(caller)  # the epoch callback names it at the guest's next entry
            return answer
        except BaseException as cause:
            try:
                if (
                    call is not None
                    and call.ended is not None
                    and isinstance(cause, wasmtime_errors)
                ):
                    # The invariant (specs 030 and 032): while the guest runs, `call.ended` is
                    # set only where the runner also stops the guest by its own act in the same
                    # step: by the epoch callback, on a path that returns an error; or by the
                    # file-call limit's shadow (spec 032), which sets the epoch deadline to 0
                    # before it returns (`_drive` sets it only before any guest code runs). So a
                    # Trap or WasmtimeError caught here after `ended` is set is the runner's own
                    # stop surfacing: the callback's error, met in host_alloc after a door call
                    # outlived the callback's window, or at a forward's trampoline entry. The
                    # limit's shadow raises nothing, and once `ended` is set the guard above
                    # keeps every later host function, forwards included, from running. It is
                    # not a stop: `_drive` names the run from `ended`. ExitTrap is a
                    # WasmtimeError, and it cannot occur here, because the callback's error
                    # aborts host_alloc first. Keep this test this narrow: any other exception,
                    # or one caught before `ended`, is a stop.
                    _epoch_now(caller)  # the guest stops at its next function entry
                elif call is not None:
                    call.stop(caller, cause)
            except BaseException:
                pass
            return stopped

    return function


def _epoch_now(caller: Any) -> None:
    """An epoch deadline of 0 for the caller's store: its guest stops, or meets its epoch
    callback, at its next function entry."""
    from . import _wasmtime_ffi as ffi

    ffi.set_epoch_deadline(caller, 0)


def _epoch_answer(context: Any, delta: Any) -> int:
    """The epoch callback's decision for the call on top of this thread's stack, in order: a
    recorded stop holds, a named end holds (spec 032: the first named end, such as "out of file
    calls", is kept under `cancel=` too), a deferred Ctrl-C becomes a stop, then a cancel, then
    the deadline; otherwise continue for up to CANCEL_TICKS ticks. 0 continues; an error (an int
    address) stops the guest (spec 015)."""
    call = None
    try:
        try:
            stack = _home._stack()
            call = stack[-1] if stack else None
            if call is not None and ctypes.addressof(context.contents) != call.context:
                call = None
        except BaseException:
            call = None
        if call is None:
            process().calls.lost = True
            return _stop_error(delta)
        if call.stopped is not None:
            return _stop_error(delta)
        if call.ended is not None:
            return _stop_error(delta)
        if _home._ctrl_c_watched() and process().ctrl_c_pending:
            process().ctrl_c_pending = False
            call.stopped = KeyboardInterrupt()
            return _stop_error(delta)
        home = getattr(call, "home", None)
        if home is not None and home.raised is not None:  # raised into the home (spec 078)
            call.stopped = _Stopped()
            return _stop_error(delta)
        if call.cancel is not None and call.cancel.is_set():
            call.ended = "cancelled"
            return _stop_error(delta)
        count = _epoch_ticker.count()
        if call.stop_at is not None and count >= call.stop_at:
            call.ended = "deadline"
            return _stop_error(delta)
        left = CANCEL_TICKS if call.stop_at is None else call.stop_at - count
        delta[0] = max(1, min(CANCEL_TICKS, left))
        return 0
    except BaseException as cause:
        try:
            if call is None:
                process().calls.lost = True
            elif call.stopped is None:
                call.stopped = cause
        except BaseException:
            pass
        return _stop_error(delta)


def _stop_error(delta: Any) -> int:
    """A new wasmtime error, which wasmtime owns once returned. If none can be made, continue for
    one tick, never 0, so the next callback tries again (spec 015's build review, F2)."""
    try:
        from . import _wasmtime_ffi as ffi

        address = ffi.new_error(b"stopped by wasi_python")
        if address:
            return address
    except BaseException:
        pass
    try:
        delta[0] = 1
    except BaseException:
        pass
    return 0


def _on_epoch(context: Any, data: Any, delta: Any, kind: Any) -> int:
    return _epoch_answer(context, delta)  # never writes `kind`: wasmtime panics on a bad value


def _watch(store: Any) -> None:
    """Give a store the epoch callback, with a NULL finalizer: no per-call ctypes object exists,
    and the callback finds its call through the thread's stack (spec 015)."""
    from . import _wasmtime_ffi as ffi

    p = process()
    with p.epoch_callback_lock:  # one object for the process: a store must never outlive its own
        if p.epoch_callback is None:
            p.epoch_callback = ffi.EPOCH_CALLBACK(_on_epoch)
        callback = p.epoch_callback
    ffi.watch_epochs(store, callback)


def _linker(wt: Any, engine: wasmtime.Engine) -> Any:
    """The engine's one linker: WASI, the shadowed poll_oneoff and the door, defined once, so a
    call adds nothing to wasmtime-py's process-wide table of host functions (spec 011)."""
    p = process()
    with p.cache_lock:
        linker = p.linkers.get(engine)
        if linker is None:
            linker = p.linkers[engine] = _runner_linker(wt, engine)
        return linker


def _runner_linker(wt: Any, engine: wasmtime.Engine) -> Any:
    linker = wt.Linker(engine)
    linker.define_wasi()
    linker.allow_shadowing = True
    i32 = wt.ValType.i32()
    ty = wt.FuncType([i32] * 4, [i32])
    poll = _shared("poll", EINVAL, EINVAL)
    linker.define_func("wasi_snapshot_preview1", "poll_oneoff", ty, poll, True)
    linker.define_func("host", "call", ty, _shared("door", NO_HOST, HOST_FAULT), True)
    return linker


def _mount_linker(wt: Any, engine: wasmtime.Engine) -> Any:
    """The engine's second linker, used only by calls with mounts (spec 032, Decision 1):
    today's, plus a shadow over each of the 29 calls in `mounts.SHADOWED`, each in the shared
    form, answering EBADF to a caller that is not its call's store and EIO once its call has
    stopped. Defined once per engine, like the first."""
    from .mounts import SIGNATURES

    p = process()
    with p.cache_lock:
        linker = p.mount_linkers.get(engine)
        if linker is None:
            linker = _runner_linker(wt, engine)
            kinds = {"i32": wt.ValType.i32(), "i64": wt.ValType.i64()}
            for name, params in SIGNATURES.items():
                ty = wt.FuncType([kinds[p] for p in params], [kinds["i32"]])
                shadow = _shared("files", EBADF, EIO, name)
                linker.define_func("wasi_snapshot_preview1", name, ty, shadow, True)
            p.mount_linkers[engine] = linker
        return linker


def _guard_linker(wt: Any, engine: wasmtime.Engine) -> Any:
    """The engine's third linker, used by every call without mounts (spec 048, Decision 7):
    today's, plus a shadow over the two calls in `mounts.GUARDED` (fd_readdir and path_rename)
    and the three in `mounts.COUNTED` (path_open, fd_close and fd_renumber, which the table
    forwards and counts against the call's cap on open files; spec 068), in the shared form, as
    the mount linker's. Every other call stays wasmtime's own. Defined once per engine, like the
    others."""
    from .mounts import COUNTED, GUARDED, SIGNATURES

    p = process()
    with p.cache_lock:
        linker = p.guard_linkers.get(engine)
        if linker is None:
            linker = _runner_linker(wt, engine)
            kinds = {"i32": wt.ValType.i32(), "i64": wt.ValType.i64()}
            for name in GUARDED + COUNTED:
                ty = wt.FuncType([kinds[p] for p in SIGNATURES[name]], [kinds["i32"]])
                shadow = _shared("files", EBADF, EIO, name)
                linker.define_func("wasi_snapshot_preview1", name, ty, shadow, True)
            p.guard_linkers[engine] = linker
        return linker


def _stat_trampoline_module(wt: Any, engine: wasmtime.Engine) -> Any:
    """The rename rule's stat trampoline, with its own one-page memory, compiled once per engine
    and instantiated per call (spec 048, Decision 2)."""
    from .mounts import stat_trampoline_wat

    p = process()
    with p.cache_lock:
        module = p.stat_trampolines.get(engine)
        if module is None:
            module = p.stat_trampolines[engine] = wt.Module(engine, stat_trampoline_wat())
        return module


def _trampoline_module(wt: Any, engine: wasmtime.Engine) -> Any:
    """The forwarders, compiled once per engine and instantiated per call (spec 032)."""
    from .mounts import trampoline_wat

    p = process()
    with p.cache_lock:
        module = p.trampolines.get(engine)
        if module is None:
            module = p.trampolines[engine] = wt.Module(engine, trampoline_wat())
        return module


# The guest's stdout and stderr, by a key that is never reused. wasmtime calls the two functions
# below on its own threads, and frees a key when it drops the stream; wasmtime-py's own table for
# custom outputs is not used, since it has no lock (spec 011).


@ctypes.CFUNCTYPE(
    ctypes.c_ssize_t, ctypes.c_void_p, ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t
)
def _output_write(key: int | None, data: Any, size: int) -> int:
    try:
        with process().outputs_lock:
            stream = process().outputs.get(key or 0)
        return size if stream is None else stream.write(ctypes.string_at(data, size))
    except BaseException:
        return size  # never raises, never prints: the bytes are dropped and the write succeeds


@ctypes.CFUNCTYPE(None, ctypes.c_void_p)
def _output_free(key: int | None) -> None:
    with process().outputs_lock:
        process().outputs.pop(key or 0, None)


def _send_outputs(wasi: Any, out: _Stream, err: _Stream) -> tuple[int, int]:
    from . import _wasmtime_ffi as ffi

    p = process()
    with p.outputs_lock:
        keys = next(p.output_keys), next(p.output_keys)
        p.outputs[keys[0]], p.outputs[keys[1]] = out, err
    ffi.set_custom_outputs(wasi, _output_write, _output_free, keys[0], keys[1])
    return keys


EINVAL, ENOMEM, EBADF, EFAULT, EIO = 28, 48, 8, 21, 29  # WASI preview1 errno values
MAX_SUBSCRIPTIONS = 4096  # one poll_oneoff's host work is bounded (spec 010)
SUBSCRIPTION = (
    "<QB7xIxxxxQQH6x"  # userdata, tag, clock id or fd, timeout, precision, flags: 48 bytes
)
EVENT = "<QHB5xQH6x"  # userdata, error, type, nbytes, flags: 32 bytes
CLOCK, FD_READ, FD_WRITE = 0, 1, 2
REALTIME, MONOTONIC = 0, 1
ABSTIME = 1


@dataclass(frozen=True)
class _Plan:
    """What one poll_oneoff answers: an errno, or the events to write after waiting wait_ns."""

    errno: int | None
    events: tuple[tuple[int, int, int, int, int], ...] = ()
    wait_ns: int = 0


def _stop_at(count: int, ticks: int) -> int:
    """The ticker's count at which a deadline of `ticks`, set when the count was `count`, has
    passed. The engine's epoch can be one round ahead of the count (the ticker advances the engines
    first), hence the + 1: a wait never ends before the epoch reaches the deadline (spec 010)."""
    return count + ticks + 1


def _poll_plan(raw: bytes, n: int, realtime_ns: int, monotonic_ns: int) -> _Plan:
    """poll_oneoff as wasmtime 49 answers it (crates/wasi/src/p1.rs), for the guest's files and
    stdio: a descriptor subscription is ready at once (stdin for writing, stdout and stderr for
    reading and the preopened root answer EBADF); otherwise the shortest clock wins, and every
    clock due by then is reported, with nbytes 0 as wasmtime writes it (spec 010)."""
    if n == 0:
        return _Plan(EINVAL)
    if n > MAX_SUBSCRIPTIONS:
        return _Plan(ENOMEM)
    ready, clocks = [], []
    for userdata, tag, which, timeout, _precision, flags in struct.iter_unpack(SUBSCRIPTION, raw):
        if tag == CLOCK:
            if which not in (REALTIME, MONOTONIC):
                return _Plan(EINVAL)
            if flags & ABSTIME:
                timeout -= realtime_ns if which == REALTIME else monotonic_ns
            clocks.append((max(0, timeout), userdata))
        elif tag in (FD_READ, FD_WRITE):
            if (
                which == 3
                or (tag == FD_READ and which in (1, 2))
                or (tag == FD_WRITE and which == 0)
            ):
                return _Plan(EBADF)
            ready.append((userdata, 0, tag, 1, 0))
        else:
            return _Plan(EINVAL)
    if ready:
        return _Plan(None, tuple(ready))
    wait_ns = min(timeout for timeout, _ in clocks)
    due = tuple((userdata, 0, CLOCK, 0, 0) for timeout, userdata in clocks if timeout <= wait_ns)
    return _Plan(None, due, wait_ns)


class _Waits:
    """A wait that the call's deadline ends: in slices of at most TICK_S while a deadline is set,
    one sleep otherwise. `now`, `sleep` and `deadline_passed` are injected so the judge counts the
    slices without measuring time (spec 010)."""

    def __init__(
        self,
        now: Callable[[], float],
        sleep: Callable[[float], None],
        deadline_passed: Callable[[], bool] | None,
    ) -> None:
        self.now, self.sleep, self.deadline_passed = now, sleep, deadline_passed

    def wait(self, seconds: float) -> None:
        if self.deadline_passed is None:
            if seconds > 0:
                self.sleep(seconds)
            return
        until = self.now() + seconds
        while (left := until - self.now()) > 0 and not self.deadline_passed():
            self.sleep(min(left, TICK_S))


def _poll_oneoff(
    origin_ns: int,
    waits: _Waits,
    realtime_ns: Callable[[], int] = time.time_ns,
    monotonic_ns: Callable[[], int] = time.perf_counter_ns,
) -> Callable[..., int]:
    """The shadowed poll_oneoff. It never raises into wasmtime-py (an exception there travels by a
    process-wide slot another call can take): a wait ended by the deadline answers normally, and
    the guest traps at its next epoch check. A BaseException goes to the shared function, which
    records it and stops the guest (spec 011). The clocks are injectable for the judge."""

    def call(caller, in_ptr: int, out_ptr: int, n: int, nevents_ptr: int) -> int:
        try:
            memory = caller.get("memory")
            in_ptr, out_ptr, n, nevents_ptr = (
                v & MASK32 for v in (in_ptr, out_ptr, n, nevents_ptr)
            )
            if n == 0 or n > MAX_SUBSCRIPTIONS:
                return EINVAL if n == 0 else ENOMEM
            size = memory.data_len(caller)
            if in_ptr + 48 * n > size or out_ptr + 32 * n > size or nevents_ptr + 4 > size:
                return EFAULT
            raw = bytes(memory.read(caller, in_ptr, in_ptr + 48 * n))
            plan = _poll_plan(raw, n, realtime_ns(), monotonic_ns() - origin_ns)
            if plan.errno is not None:
                return plan.errno
            if plan.wait_ns:
                waits.wait(plan.wait_ns / 1e9)
            events = b"".join(struct.pack(EVENT, *e) for e in plan.events)
            memory.write(caller, events, out_ptr)
            memory.write(caller, struct.pack("<I", len(plan.events)), nevents_ptr)
            return 0
        except Exception:
            return EINVAL  # anything else is recorded by the shared function (spec 011)

    return call


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


def _first_line(text: str) -> str:
    lines = text.strip().splitlines()
    return lines[0] if lines else "trap"


def _trap_name(e: wasmtime.Trap) -> str:
    import wasmtime as wt

    if e.trap_code == wt.TrapCode.OUT_OF_FUEL:
        return "out of fuel"
    if e.trap_code == wt.TrapCode.INTERRUPT:
        return "deadline"
    if e.trap_code is not None:  # by its kind, not wasmtime's heading (spec 016, Decision 3)
        return _trap_code_name(e.trap_code)
    return _first_line(e.message)


def _trap_code_name(code: Any) -> str:
    """`TrapCode.STACK_OVERFLOW` is "stack overflow"."""
    return code.name.lower().replace("_", " ")


def _door_answer(host: Host, request: bytes) -> bytes | None:
    """The host's answer as plain bytes, or None for a fault; on the home thread, so a response's
    own code (a bytes subclass's `__bytes__`) runs there too (spec 078, Decision 4)."""
    response = host(request)
    if not isinstance(response, (bytes, bytearray, memoryview)):
        return None
    if memoryview(response).nbytes > MAX_RESPONSE:
        return None  # checked in bytes, before the copy
    return bytes(response)


def _door(
    host: Host | None,
    admit: Callable[[int], bytes | None] | None = None,
    home: Any = None,
) -> Callable[..., int]:
    """host::call(ptr, len, out_ptr_ptr, out_len_ptr) -> 0, -1 or -2 (spec 003, Decision 5).

    With `admit` (the tool protocol's frame host, spec 036), each frame's length is offered to
    it once the addresses are checked and before the frame is read: bytes it returns are the
    answer, and the frame is never copied out of guest memory, so a refused frame costs the
    host the same whatever its length. The raw `host=` path passes no `admit`, as before."""

    import wasmtime as wt

    def call(caller, ptr: int, length: int, out_ptr_ptr: int, out_len_ptr: int) -> int:
        if host is None:
            return NO_HOST
        try:
            return frame(caller, ptr, length, out_ptr_ptr, out_len_ptr)
        except (wt.Trap, wt.WasmtimeError):
            raise  # a trap or exit inside host_alloc: the shared function records it (spec 011)
        except Exception:
            return HOST_FAULT  # nothing a frame or a host does escapes run() (spec 006)

    def frame(caller, ptr: int, length: int, out_ptr_ptr: int, out_len_ptr: int) -> int:
        memory, alloc = caller.get("memory"), caller.get("host_alloc")
        if memory is None or alloc is None:
            return HOST_FAULT
        ptr, length = ptr & MASK32, length & MASK32  # i32 values: addresses are unsigned
        out_ptr_ptr, out_len_ptr = out_ptr_ptr & MASK32, out_len_ptr & MASK32
        size = memory.data_len(caller)
        if ptr + length > size or out_ptr_ptr + 4 > size or out_len_ptr + 4 > size:
            return HOST_FAULT  # memory.read would clamp a frame that runs past memory
        response = None if admit is None else admit(length)
        if response is None:
            request = bytes(memory.read(caller, ptr, ptr + length))
            response = (
                _door_answer(host, request)
                if home is None
                else home.call(_door_answer, host, request)
            )
        else:
            response = _door_answer(lambda _: response, b"")
        if response is None:
            return HOST_FAULT
        p = alloc(caller, len(response)) & MASK32
        if not p or p + len(response) > memory.data_len(caller):
            return HOST_FAULT
        memory.write(caller, response, p)
        memory.write(caller, struct.pack("<I", p), out_ptr_ptr)
        memory.write(caller, struct.pack("<I", len(response)), out_len_ptr)
        return 0

    return call


# The tool threads alive in this process (spec 036, Decision 5): one per tool call, counted in
# as it starts and out as it ends, after its call returned or not.


def _count_tool_threads(delta: int) -> None:
    p = process()
    with p.tool_threads_lock:
        p.tool_threads_running += delta


def _home_context(home: Any) -> Callable[[], contextvars.Context]:
    """How a tool call copies its context: on the home thread, so it sees what a provider or the
    door host set earlier in the call (spec 078, Decision 4, the review's F12)."""
    if home is None:
        return contextvars.copy_context
    return lambda: home.call(contextvars.copy_context)


def _ctrl_c_now() -> bool:
    """A Ctrl-C is pending for the call on this (the main) thread: read, never cleared."""
    return _home._ctrl_c_watched() and process().ctrl_c_pending


def _tool_host(
    c: dict[str, Any], stop_at: int | None, cancel: Any, home: Any = None
) -> _ToolHost | None:
    """The call's frame host, for a call with tools=, bound by the call's deadline, its cancel
    and Ctrl-C (spec 036, Decisions 2 to 5), and by an exception raised into its home thread,
    where each tool call's context is copied (spec 078, Decision 4, C1); None otherwise."""
    if c.get("tools") is None:
        return None
    from .tools import _Bounded, _ToolHost, _ToolLoop

    bound = _Bounded(
        tick_s=TICK_S,
        stop_at=stop_at,
        ticks=lambda: _epoch_ticker.count(),
        cancel=cancel,
        ctrl_c=_ctrl_c_now if home is None else (lambda: _ctrl_c_now() or home.stopped()),
        count=_count_tool_threads,
        context=_home_context(home),
    )
    # Under run_async, the caller's loop; otherwise a private loop of the call's own (spec 053).
    tool_loop = _ToolLoop(c.get("tool_loop"), count=_count_tool_threads)
    return _ToolHost(
        c["tools"],
        gate=c["gate"],
        max_calls=c["tool_calls"],
        invoke=bound,
        tool_loop=tool_loop,
        max_bytes=c.get("tool_request_bytes"),  # spec 060; a hand-built c without it: no limit
    )
