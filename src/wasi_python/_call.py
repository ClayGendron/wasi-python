"""One call: `Completed`, the checked run and the instance, the driver and `_Call`, the
host-function wrapper and the epoch callback, the linkers and trampolines, `poll_oneoff`, the
door and the tool host. The guest's output streams and their capture are `_outputs`'."""

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
from typing import TYPE_CHECKING, Any, NamedTuple, Protocol

from . import _artifacts, _engines, _home, _outputs, _places, _platform, _private_dirs, _zip
from . import _snapshot as _snapshot  # its own line: the line above is full
from ._artifacts import GUEST_PACKAGE, Artifacts, ArtifactsMissing
from ._engines import _epoch_ticker
from ._fs_memory import STAGING_CEILING, _aligned
from ._home import _Home, _Stopped
from ._limits import CANCEL_TICKS, NO_DEADLINE, TICK_S
from ._outputs import _Stream
from ._places import ZIP_GUEST, Grant, _Preopen
from ._platform import _TRAP_HANDLERS_REPLACED, _Walked
from ._private_dirs import _Private
from ._process import process
from ._zip import MPL_DATA_GUEST
from .mounts import FileRecord, Mount

if TYPE_CHECKING:
    import asyncio

    import wasmtime

    from ._fs_table import _Files
    from ._tool_host import _ToolHost
    from .tools import Tool, ToolCall, ToolRecord

ARGV0 = "/usr/local/bin/python.wasm"
NO_HOST = -1
HOST_FAULT = -2
MASK32 = 0xFFFFFFFF
UNMETERED = 2**63 - 1  # the budget instantiation runs on, before the cap is set
MAX_RESPONSE = 0x7FFFFFFF  # the largest door response: its length must fit a signed i32
# The guest's environment before the caller's `env`. HOME is added per call: a fresh, empty
# directory under /tmp that the runner removes afterwards, so nothing a call leaves in its HOME
# (pdb's .pdbrc, for one) is read by the next; where /tmp is not writable, an empty folder the
# guest cannot write, so `~` never falls back to the working folder, which may be a reused root.
BASE_ENV = {"TMPDIR": "/tmp", "PYTHONTZPATH": ""}

Host = Callable[[bytes], "bytes | bytearray | memoryview"]  # the door's host function


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
        image_sha256: The SHA-256 of the snapshot's image a call or turn started from, or `None`.
    """

    exit_code: int | None
    stdout: bytes
    stderr: bytes
    trapped: str | None
    fuel_used: int | None
    truncated: tuple[str, ...] = ()
    files: FileRecord | None = None  # the mounts' record, for a call with mounts
    tools: ToolRecord | None = None  # the tool protocol's record, for a call with tools
    image_sha256: str | None = None  # the snapshot's, for a call that started from one


@dataclass(frozen=True, slots=True)
class _CheckedCall:
    """Every argument a call's guest depends on, checked once before any work and never edited
    on the way down: a default is read when the call is made, and a field spelled wrong is a
    `TypeError` at the construction, not a `KeyError` under a guest. Every field is required.
    The call's home thread and the loop its async tools await on are not fields: they are
    bindings the runner makes while it runs the call, and travel as parameters."""

    fuel: int | None
    deadline_s: float | None
    memory_bytes: int | None
    output_bytes: int | None
    argv: tuple[str, ...]
    env: dict[str, str] | None  # never mutated after the check
    stdin: bytes | None
    cancel: threading.Event | None
    tools: tuple[Tool, ...] | None
    gate: Callable[[ToolCall], Any] | None  # may be async
    tool_calls: int | None
    tool_request_bytes: int | None
    root: str | bool | None  # `False` none, `None` a private one, else a host path
    grants: tuple[Grant, ...]
    mounts: tuple[Mount, ...]
    import_path: tuple[str, ...]
    import_serving: tuple[int, ...]  # for each entry, the index of the grant serving it
    file_calls: int | None
    open_files: int | None
    binary: str  # "snapshot" or "plain"
    start: _snapshot._Start | None  # None from the binary alone; else an image, or a making


class _Stop(Protocol):
    """What stops a call's waits: a `threading.Event`, or a session's pair of them."""

    def is_set(self) -> bool: ...


def _run_checked(
    wt: Any,
    c: _CheckedCall,
    host: Host | None,
    chosen: _engines._Cache,
    artifacts: Artifacts | None,
    loop: asyncio.AbstractEventLoop | None,
) -> Completed:
    """One call, checked: the artifact set found, the folders walked, the engine and module
    made, the instance run on a guest thread while this thread, its home, serves it. `loop` is
    the caller's event loop, which async tools await on, or None for a private loop."""
    snapshot = c.binary == "snapshot"
    found, checked = (
        (artifacts, None) if artifacts is not None else _artifacts._found_and_checked(snapshot)
    )
    checked = _snapshot._same_set(c.start, found, checked)  # an image binds to its set
    if c.tools is not None and not _artifacts._has_guest_package(found.manifest):
        raise ArtifactsMissing(
            f"{found.manifest} has no `recipe … {GUEST_PACKAGE}` line: this artifact set "
            "predates the tool protocol, so its guest cannot `from host import "
            "tools`; tools= needs a set built with the guest package"
        )
    cache = chosen.folder
    root = c.root
    walked_root, walked = _places._walk_grants(
        root,
        c.grants,
        found,
        cache,
        c.import_path,
        c.import_serving,
        others=_engines._caches(chosen),
    )
    preopens: list[_Preopen] = []
    private = None
    home = _Home()  # this thread, while the guest runs on its own
    try:
        after_walk = process().observers.after_walk
        if after_walk is not None:
            after_walk()
        binary = found.snapshot if snapshot else found.plain
        engine = _engines._engine(c.fuel is not None)
        want = None if checked is None else checked.binary
        module = _engines._module(engine, c.fuel is not None, binary, cache, want)
        zip_want = None if checked is None else checked.zip
        root_path, private = _preopens(found, root, walked_root, walked, preopens, zip_want)
        return _call(wt, engine, module, root_path, preopens, c, host, loop, home)
    finally:

        def release() -> None:
            # Windows holds every walked folder until here; a private root can be removed only
            # after.
            for w in [walked_root, *(w for _, _, w in walked), *(p.walked for p in preopens)]:
                if w is not None:
                    w.close()
            _places._let_go([walked_root, *(w for _, _, w in walked)])  # nothing writes them now
            if private is not None:
                private.remove()

        home.finish(release)  # never while a guest thread runs


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
    a call and a session's opening. `zip_want` is the zip's checked digest, for a set
    the runner found."""
    _private_dirs._sweep_once()
    folder = _zip._zip_folder(found, zip_want)
    preopens.append(
        _Preopen(
            "the stdlib folder",
            _platform.PLATFORM.walk("", str(folder.lib), judge=False),
            ZIP_GUEST,
            False,
        )
    )
    if folder.data is not None:  # after the zip's grant
        guest = f"{ZIP_GUEST}/{folder.name}/{MPL_DATA_GUEST}"
        walked_data = _platform.PLATFORM.walk("", str(folder.data), judge=False)
        preopens.append(_Preopen("matplotlib's data", walked_data, guest, False))
    root_path = None
    private = None
    if root is None:
        private = _Private("wasi-python-root-")  # 0700, this user's own, locked
        try:
            (private.path / "usr" / "local" / "lib").mkdir(parents=True)
            root_path = private.path
            walked_private = _platform.PLATFORM.walk("", str(root_path), judge=False)
        except BaseException:
            private.remove()
            raise
        preopens.append(_Preopen("the private root", walked_private, "/", True))
    elif walked_root is not None:
        root_path = Path(walked_root.path)
        # Real folders, never a guest's link: without them /usr would vanish from a fresh
        # root's listing, and the zip's path could resolve into a file a guest wrote. Made
        # through the walked folder, never its path, which another guest may have swapped
        # since the walk.
        _, made = _platform.PLATFORM.real_dir(root_path, walked_root.fd, ("usr", "local", "lib"))
        _platform._close(made)
        preopens.append(_Preopen("root", walked_root, "/", True))
    for where, grant, w in walked:
        preopens.append(_Preopen(where, w, grant.guest, grant.writable))
    return root_path, private


def _call(
    wt: Any,
    engine: wasmtime.Engine,
    module: wasmtime.Module,
    root: Path | None,
    preopens: list[_Preopen],
    c: _CheckedCall,
    host: Host | None,
    loop: asyncio.AbstractEventLoop | None,
    home: _Home,
) -> Completed:
    """One instance, one program. The store is closed before this returns, trapped or not, so the
    guest's memory and open files are released at once (a trapped store is otherwise kept alive by
    a reference cycle until Python's collector runs) and a private root can be removed afterwards
    (Windows refuses to remove an open directory). Ctrl-C is deferred while the guest runs."""
    with _home._deferred_ctrl_c():
        return _call_deferred(wt, engine, module, root, preopens, c, host, loop, home)


def _call_deferred(
    wt: Any,
    engine: wasmtime.Engine,
    module: wasmtime.Module,
    root: Path | None,
    preopens: list[_Preopen],
    c: _CheckedCall,
    host: Host | None,
    loop: asyncio.AbstractEventLoop | None,
    ht: _Home,
) -> Completed:
    """The call's fresh HOME folder and its store, released once the guest thread has ended.
    `ht` is the home thread; `home` below is the guest's HOME."""
    fixed = None if c.start is None else c.start.home  # a snapshot's, at its fixed path
    home = _guest_home(root, preopens, tuple(m.guest for m in c.mounts), fixed)
    store = wt.Store(engine)
    try:
        return _instance(wt, engine, module, store, preopens, home.guest, c, host, loop, ht)
    finally:

        def release() -> None:
            store.close()
            _release_home(home)

        ht.finish(release)  # never while a guest thread runs


class _GuestHome(NamedTuple):
    """The guest's HOME: `guest`, its path, always set; and either `fresh`, the folder made for
    the call (its name, the folder it is in, a handle on that folder), or `empty`, the private
    folder preopened read-only there instead, with its walk."""

    guest: str
    fresh: tuple[str, Path | None, int | None] | None
    empty: tuple[_Private, _Walked] | None


def _guest_home(
    root: Path | None, preopens: list[_Preopen], mounted: tuple[str, ...], fixed: str | None = None
) -> _GuestHome:
    """The guest's HOME, shared by a call and a session's opening, made after `preopens` is
    listed. A fresh folder where the guest sees a writable /tmp; else an empty private folder,
    appended to `preopens` read-only, so the mounts' numbers and the identity check count it.
    Without a HOME, `~` stays `~`, a path relative to the working folder, which a root or a mount
    at / serves: a file one call left there would be read, or run, by the next (reportlab runs
    `~/.reportlab_mods` on import). A snapshot's call has HOME at its `fixed` path, where a package
    found it at import, with a private folder of its own there, writable where /tmp is."""
    tmp, tmp_fd = _home_folder(root, preopens, mounted)
    name = f".home-{secrets.token_hex(16)}"
    if tmp is None or fixed is not None:
        _platform._close(tmp_fd)
        empty = _Private("wasi-python-")  # 0700, this user's own, locked; its lock file beside it
        try:
            walked = _platform.PLATFORM.walk("", str(empty.path), judge=False)
        except BaseException:
            empty.remove()
            raise
        guest = fixed or f"/tmp/{name}"
        preopens.append(_Preopen("the guest's HOME", walked, guest, tmp is not None))
        return _GuestHome(guest, None, (empty, walked))
    # The fresh HOME is made, and removed, through a handle on /tmp opened without following a
    # link, so a guest running concurrently on the same folder cannot turn /tmp into a link
    # between the check and the mkdir (Windows has no dir_fd; its guests can make links only
    # where the user holds the symbolic-link privilege).
    try:
        if tmp_fd is not None:
            os.mkdir(name, dir_fd=tmp_fd)
        else:
            (tmp / name).mkdir()
    except BaseException:
        _platform._close(tmp_fd)
        raise
    return _GuestHome(f"/tmp/{name}", (name, tmp, tmp_fd), None)


def _remove_home(fresh: tuple[str, Path | None, int | None]) -> None:
    """A fresh HOME's budgeted removal, and its folder's handle closed."""
    name, tmp, tmp_fd = fresh
    try:
        _private_dirs._remove_fresh_home(name, tmp, tmp_fd)
    finally:
        _platform._close(tmp_fd)


def _release_home(home: _GuestHome) -> None:
    """Remove the guest's HOME once no guest runs: the fresh one by its budgeted removal, the
    empty one after its walk is closed, since Windows refuses to remove a folder a handle holds
    (closing a walk twice does nothing, so a later close of every preopen is harmless)."""
    if home.fresh is not None:
        _remove_home(home.fresh)
    if home.empty is not None:
        empty, walked = home.empty
        walked.close()
        empty.remove()


def _home_folder(
    root: Path | None, preopens: list[_Preopen], mounted: tuple[str, ...] = ()
) -> tuple[Path | None, int | None]:
    """Where a fresh HOME is made: a writable grant at /tmp, else the root's tmp, else
    nowhere. A read-only grant at /tmp hides the root's tmp, so then there is no fresh HOME
    either, and a mount at /tmp counts as one: the runner makes nothing in a mount. Where there is
    none, `_guest_home` gives the guest an empty, read-only one."""
    if "/tmp" in mounted:
        return None, None
    at_tmp = [p for p in preopens if p.guest == "/tmp"]
    if at_tmp:
        p = at_tmp[0]
        if not p.writable:
            return None, None
        fd = p.walked.fd
        return Path(p.walked.path), (
            os.dup(fd) if fd is not None and _platform.PLATFORM.has_dir_fd else None
        )
    if root is None:
        return None, None
    # TMPDIR, a real folder (a guest's link there is removed), made through the root's walked
    # folder, never its path.
    fd = next(p.walked.fd for p in preopens if p.guest == "/")
    return _platform.PLATFORM.real_dir(root, fd, ("tmp",))


def _import_prelude(entries: tuple[str, ...]) -> list[str]:
    """The `-c` prelude that puts the import path on `sys.path`: one
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
    home: str,
    c: _CheckedCall,
    host: Host | None,
    loop: asyncio.AbstractEventLoop | None,
    ht: _Home,
) -> Completed:
    """The instance: its limits, waits and host functions armed, the guest run on a thread of
    its own with `ht`, this thread, as its home, and everything released once that thread has
    ended. `home` is the guest's HOME."""
    argv, env, stdin, cancel = c.argv, c.env, c.stdin, c.cancel
    fuel, deadline_s = c.fuel, c.deadline_s
    memory_bytes, output_bytes = c.memory_bytes, c.output_bytes
    if fuel is not None:
        # Fuel is metered from the end of instantiation: instantiation runs only
        # wasmtime's own memory fill, which it charges per byte when it cannot map the image
        # (macOS when compiled in the process, Windows always); the guest's work starts after.
        store.set_fuel(UNMETERED)
    if memory_bytes is not None:
        store.set_limits(memory_size=memory_bytes)
    ticks = NO_DEADLINE if deadline_s is None else max(1, math.ceil(deadline_s / TICK_S))
    # A call with `cancel` is first checked within CANCEL_TICKS ticks, whatever its deadline; its
    # callback then enforces the deadline too.
    # Every call is polled every CANCEL_TICKS ticks: so Ctrl-C, and an
    # exception raised into the home thread, reach a guest that never calls back.
    store.set_epoch_deadline(min(CANCEL_TICKS, ticks))
    # The ticker's count at which this store's deadline has passed, read after the deadline is
    # set: a wait in poll_oneoff stops there, so it never outlives the deadline.
    stop_at = None if deadline_s is None else _stop_at(_epoch_ticker.count(), ticks)
    checks: list[Callable[[], bool]] = []
    if stop_at is not None:
        checks.append(lambda: _epoch_ticker.count() >= stop_at)
    if cancel is not None:
        checks.append(cancel.is_set)  # a wait ends at a cancel, deadline or not
    if _home._ctrl_c_watched():
        checks.append(lambda: process().ctrl_c_pending)  # a wait on the main thread ends at Ctrl-C
    checks.append(ht.stopped)  # and at an exception raised into the home
    waits = _Waits(
        lambda: time.perf_counter(),
        time.sleep,
        (lambda: any(check() for check in checks)) if checks else None,
    )
    # Under tools=, the runner is the door's host: the frame host, bound by the same deadline,
    # cancel and Ctrl-C, and asked to admit each frame by its length before it is read (036).
    tool_host = _tool_host(c, stop_at, cancel, loop, ht)
    admit = None
    if tool_host is not None:
        host, admit = tool_host, tool_host.admit

    out, err = _Stream("stdout", output_bytes), _Stream("stderr", output_bytes)
    wasi = wt.WasiConfig()
    origin_ns = time.perf_counter_ns()  # wasmtime's monotonic clock counts from here
    wasi.argv = [ARGV0, *_import_prelude(c.import_path), *argv]
    wasi.env = sorted({**BASE_ENV, "HOME": home, **(env or {})}.items())
    check = _engines._check_module(wt, engine, fuel is not None)
    capture = _outputs._capture(wasi, out, err)  # before any guest code
    scratch = None
    mounts = c.mounts
    mounted: list[_Preopen] = []  # each mount's preopen, on the call's empty placeholder
    table = None
    files = None
    try:
        # 0700, this user's own, locked; made before the preopens, since it holds the
        # mounts' placeholder, which lies under the temporary folder no grant may reach.
        scratch = _Private("wasi-python-")
        if mounts:
            placeholder = scratch.path / "mount"
            placeholder.mkdir()
            for i, mount in enumerate(mounts):
                walked = _platform.PLATFORM.walk("", str(placeholder), judge=False)
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
        from ._fs_table import _Files

        staging = STAGING_CEILING if memory_bytes is None else memory_bytes
        others = [p.guest for p in preopens]
        if mounts:
            guest_linker = _mount_linker(wt, engine)
            first = 3 + len(preopens)  # the mounts' preopens come after every other
            numbers = [(mount, first + i) for i, mount in enumerate(mounts)]
        else:
            # A call without mounts: the counted linker, today's but for the three calls the cap
            # on open files counts, served by a table with no mounts, which forwards them.
            guest_linker = _counted_linker(wt, engine)
            numbers = []
        context = _Context()
        table = _Files(
            numbers,
            others,
            c.file_calls,
            staging,
            fuel is not None,
            engine,
            open_files=c.open_files,  # strict, as file_calls
            context=context,
        )
        call = _Call(store, host, waits, origin_ns, cancel, stop_at, admit, table=table, home=ht)
        _watch(store)  # every call
        with _epoch_ticker(engine, True):
            image = None if c.start is None else c.start.image
            drive = functools.partial(_drive, plain=linker, image=image)
            args = (wt, guest_linker, store, module, call, fuel, every, check)
            done = _home._on_guest_thread("run", ht, call, drive, *args)
        fuel_used = _fuel_used(fuel, done, call, store.get_fuel)
        # What the guest wrote is handed over at every ending that returns a result, after the
        # fuel is read; a call that raises never gets here. Every call has a table, with mounts
        # or without; a table without mounts walks nothing (no mount, nothing owed).
        table.walk()
    finally:
        if ht.done and table is not None:  # the record kept
            # A table without mounts is never reported: `files` is None without mounts.
            files = table.record() if mounts else None

        def release() -> None:
            if tool_host is not None:  # the call's tool loop, ended without waiting
                tool_host.close()
            # The store holds every descriptor the guest opened; a guest can open them until the
            # host refuses. Close it first, so the clean-up below has descriptors to work with,
            # and make that clean-up unable to raise.
            store.close()
            capture.close()  # after the store: nothing more can arrive
            if table is not None:  # the rest dropped now
                table.release()
                context.leave()
            for p in mounted:
                p.walked.close()
            if scratch is not None:
                scratch.remove()

        ht.finish(release)  # never while a guest thread runs
    truncated = tuple(s.name for s in (out, err) if s.dropped)
    record = None if tool_host is None else tool_host.record  # on every ending
    return Completed(
        done.exit_code,
        bytes(out.data),
        bytes(err.data),
        done.trapped,
        fuel_used,
        truncated,
        files,
        record,
        None if c.start is None else c.start.sha256,
    )


def _fuel_used(
    fuel: int | None, done: _Driven, call: _Call, remaining: Callable[[], int]
) -> int | None:
    """The instructions the guest ran, or None when the count is meaningless: after an epoch
    interrupt wasmtime's fuel counter is not brought up to date, and a
    stopped call ended on one."""
    if fuel is None or done.trapped == "deadline":
        return None
    held = call.table.stop_fuel
    if held is not None and call.ended is None and call.stopped is held[0]:
        # A forward's own trap or error, or an ABI error a served call raised: the
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
    image: bytes | None = None,
) -> _Driven:
    """Instantiate and run the guest with its call on this thread's stack. What a host function
    caught and recorded comes first: an exit or a trap is the call's result, and any other
    exception (Ctrl-C, a host's cancellation) is raised here, on the thread that made the call.
    `plain` is today's linker when `linker` is the mount linker: the identity check reads
    wasmtime's own answers through it, and the trampoline takes wasmtime's calls from it.
    `image` is a snapshot's, copied in before any guest code runs."""
    # before every entry into the guest
    not_ready = _platform.PLATFORM.trap_handlers_ready()
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
            _places._check_preopens(wt, own, store, check, list(preopens))  # the identity check
        instance = linker.instantiate(store, module)
        # After the guest, before the fuel cap and _initialize.
        call.table.bind(wt, store, own, instance)
        if image is not None:  # the host's copy: it spends no fuel
            _snapshot._restore(store, instance, image)
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
        cause.__traceback__ = None  # a reported stop's frames hold this call
    elif call.ended is not None:  # the epoch callback stopped it
        exit_code, trapped = None, call.ended
    return _Driven(exit_code, trapped, metered, instance)


class _Call:
    """One call's state, which the shared host functions find on the calling thread's stack: its
    door, its poll_oneoff, its store's context address, and the first exception they caught; for
    a call with `cancel`, the event, the ticker count its deadline passes at, and the outcome the
    epoch callback recorded."""

    def __init__(
        self,
        store: Any,
        host: Host | None,
        waits: _Waits,
        origin_ns: int,
        cancel: _Stop | None = None,
        stop_at: int | None = None,
        admit: Callable[[int], bytes | None] | None = None,
        *,
        table: _Files,
        home: _Home | None = None,
    ) -> None:
        from . import _wasmtime_ffi as ffi

        self.context = ffi.context_address(store)
        self.origin_ns = origin_ns  # its waits count from here
        # The thread that made the call, which runs the embedder's code;
        # None calls it directly (the judge's stand-ins).
        self.home = home
        # admit: the frame host's, under tools=, whose host is the runner's own code
        self.door = _door(host, admit, home if admit is None else None)
        self.poll = _poll_oneoff(origin_ns, waits, files=table)
        self.stopped: BaseException | None = None
        self.cancel = cancel
        self.stop_at = stop_at
        # "cancelled" or "deadline", from the epoch callback; "out of file calls"
        self.ended: str | None = None
        self.table = table  # the call's mount table, or its table without mounts
        context = _context_of(table)
        if context is not None:
            context.enter(self)

    def files(self, caller: Any, name: str, *args: int) -> int:
        """One of the 29 shadowed calls, for a call with mounts, or one of the three
        the counted linker shadows, for a call without."""
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
    whose exceptions travel by a process-wide slot. `bound` goes before the guest's
    arguments: a file shadow's name."""

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
            # the epoch callback has ended.
            if call.stopped is None and _home._ctrl_c_watched() and process().ctrl_c_pending:
                process().ctrl_c_pending = False
                raise KeyboardInterrupt
            if call.stopped is not None or call.ended is not None:
                return stopped  # no host function runs for a stopped or ended call
            answer: int = getattr(call, kind)(caller, *bound, *args)  # door, poll or files
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
                    # The invariant: while the guest runs, `call.ended` is
                    # set only where the runner also stops the guest by its own act in the same
                    # step: by the epoch callback, on a path that returns an error; or by the
                    # file-call limit's shadow, which sets the epoch deadline to 0
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


class _Context:
    """The runner's answers to the mount table's nine questions (`mounts._CallContext`): the
    four process-wide ones from this module and the process object, read at every call, and
    the five of the call the table serves, which `enter` and `leave` set and clear with the
    call's life, or a session's turns; with no call they answer "no call"."""

    def __init__(self) -> None:
        self.call: _Call | None = None

    def enter(self, call: _Call) -> None:
        self.call = call

    def leave(self) -> None:
        self.call = None

    def ino_of(self, path: str) -> int:
        return _places._siphash13(path.encode())

    def trampoline(self, wt: Any, engine: wasmtime.Engine) -> Any:
        return _trampoline_module(wt, engine)

    def exiting(self) -> bool:
        return process().exiting

    def ctrl_c_pending(self) -> bool:
        return _ctrl_c_now()

    def stop_now(self, caller: Any) -> None:
        _epoch_now(caller)

    def cancelled(self) -> bool:
        call = self.call
        return call is not None and call.cancel is not None and call.cancel.is_set()

    def deadline_passed(self) -> bool:
        call = self.call
        return (
            call is not None and call.stop_at is not None and process().ticker_count >= call.stop_at
        )

    def name_end(self, reason: str) -> None:
        call = self.call
        if call is not None and call.ended is None:
            call.ended = reason

    def on_home(self, fn: Callable[..., Any], *args: Any) -> Any:
        home = None if self.call is None else self.call.home
        return fn(*args) if home is None else home.call(fn, *args)


def _context_of(table: _Files) -> _Context | None:
    """The runner's own context behind a table, which learns the call; None for a table the
    judge built on a fake."""
    context = table.context
    return context if isinstance(context, _Context) else None


def _epoch_answer(context: Any, delta: Any) -> int:
    """The epoch callback's decision for the call on top of this thread's stack, in order: a
    recorded stop holds, a named end holds (the first named end, such as "out of file
    calls", is kept under `cancel=` too), a deferred Ctrl-C becomes a stop, then a cancel, then
    the deadline; otherwise continue for up to CANCEL_TICKS ticks. 0 continues; an error (an int
    address) stops the guest."""
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
        if home is not None and home.raised is not None:  # raised into the home
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
    one tick, never 0, so the next callback tries again."""
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
    and the callback finds its call through the thread's stack."""
    from . import _wasmtime_ffi as ffi

    p = process()
    with p.epoch_callback_lock:  # one object for the process: a store must never outlive its own
        if p.epoch_callback is None:
            p.epoch_callback = ffi.EPOCH_CALLBACK(_on_epoch)
        callback = p.epoch_callback
    ffi.watch_epochs(store, callback)


def _linker(wt: Any, engine: wasmtime.Engine) -> Any:
    """The engine's one linker: WASI, the shadowed poll_oneoff and the door, defined once, so a
    call adds nothing to wasmtime-py's process-wide table of host functions."""
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
    """The engine's second linker, used only by calls with mounts:
    today's, plus a shadow over each of the 29 calls in `_fs_memory.SHADOWED`, each in the shared
    form, answering EBADF to a caller that is not its call's store and EIO once its call has
    stopped. Defined once per engine, like the first."""
    from ._fs_memory import SIGNATURES

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


def _counted_linker(wt: Any, engine: wasmtime.Engine) -> Any:
    """The engine's third linker, used by every call without mounts:
    today's, plus a shadow over the three calls in `_fs_memory.COUNTED` (path_open, fd_close and
    fd_renumber, which the table forwards and counts against the call's cap on open files), in
    the shared form, as the mount linker's. Every other call stays wasmtime's own. Defined once
    per engine, like the others."""
    from ._fs_memory import COUNTED, SIGNATURES

    p = process()
    with p.cache_lock:
        linker = p.counted_linkers.get(engine)
        if linker is None:
            linker = _runner_linker(wt, engine)
            kinds = {"i32": wt.ValType.i32(), "i64": wt.ValType.i64()}
            for name in COUNTED:
                ty = wt.FuncType([kinds[p] for p in SIGNATURES[name]], [kinds["i32"]])
                shadow = _shared("files", EBADF, EIO, name)
                linker.define_func("wasi_snapshot_preview1", name, ty, shadow, True)
            p.counted_linkers[engine] = linker
        return linker


def _trampoline_module(wt: Any, engine: wasmtime.Engine) -> Any:
    """The forwarders, compiled once per engine and instantiated per call."""
    from ._fs_memory import trampoline_wat

    p = process()
    with p.cache_lock:
        module = p.trampolines.get(engine)
        if module is None:
            module = p.trampolines[engine] = wt.Module(engine, trampoline_wat())
        return module


EINVAL, ENOMEM, EBADF, EFAULT, EIO = 28, 48, 8, 21, 29  # WASI preview1 errno values
MAX_SUBSCRIPTIONS = 4096  # one poll_oneoff's host work is bounded
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
    first), hence the + 1: a wait never ends before the epoch reaches the deadline."""
    return count + ticks + 1


def _poll_plan(
    raw: bytes, n: int, realtime_ns: int, monotonic_ns: int, kind: Callable[[int], str | None]
) -> _Plan:
    """poll_oneoff as wasmtime answers it (crates/wasi/src/p1.rs): unknown clock flags are
    EINVAL; a descriptor is answered from what `kind` says the call knows of it: a number the
    guest holds and a mount's file are ready at once, a folder and any other number EBADF, and
    stdio as wasmtime answers it (stdin for writing, stdout and stderr for reading EBADF);
    otherwise the shortest clock wins, and every clock due by then is reported, with nbytes 0.
    Every descriptor is ready at once, and a clock is reported only when no descriptor is;
    wasmtime reports what is ready at its first look, which for a file is often nothing yet.
    Kept differences, since the runner does not ask wasmtime what a held number is: a folder
    the guest opened is ready (wasmtime: EBADF); a file on a read-only place, polled for
    writing, is ready (wasmtime: EPERM); a file at its end has no hangup flag (wasmtime sets
    it); a closed 0, 1 or 2 is ready, and stdio renumbered onto another number is EBADF there
    (wasmtime: EBADF, and that stdio's answer); past 4096 subscriptions, ENOMEM (no cap)."""
    if n == 0:
        return _Plan(EINVAL)
    if n > MAX_SUBSCRIPTIONS:
        return _Plan(ENOMEM)
    ready, clocks = [], []
    for userdata, tag, which, timeout, _precision, flags in struct.iter_unpack(SUBSCRIPTION, raw):
        if tag == CLOCK:
            if which not in (REALTIME, MONOTONIC) or flags & ~ABSTIME:
                return _Plan(EINVAL)
            if flags & ABSTIME:
                timeout -= realtime_ns if which == REALTIME else monotonic_ns
            clocks.append((max(0, timeout), userdata))
        elif tag in (FD_READ, FD_WRITE):
            known = kind(which)
            if known is None and which <= 2:
                if (tag == FD_READ and which in (1, 2)) or (tag == FD_WRITE and which == 0):
                    return _Plan(EBADF)
            elif known not in ("held", "file"):
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
    slices without measuring time."""

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


class _PollFiles(Protocol):
    """What the poll asks of the call's table: what it knows of a descriptor, and the record of
    the error that ends the run."""

    def kind(self, fd: int) -> str | None: ...
    def record_stop(self, error: BaseException, caller: Any) -> None: ...


def _poll_oneoff(
    origin_ns: int,
    waits: _Waits,
    realtime_ns: Callable[[], int] = time.time_ns,
    monotonic_ns: Callable[[], int] = time.perf_counter_ns,
    *,
    files: _PollFiles,
) -> Callable[..., int]:
    """The shadowed poll_oneoff, answering descriptors from the call's table `files`. It raises
    only a wasmtime error, to the shared function, which records it as the stop: a misaligned
    pointer ends the run, as wasmtime ends it: in_ptr once the count is checked, out_ptr and
    nevents_ptr once the subscriptions are answered, since wasmtime checks them only when it
    writes. A wait ended by the deadline answers normally, and the guest traps at its next epoch
    check; a BaseException goes to the shared function too. Kept differences: a pointer past
    memory is EFAULT (wasmtime ends the run, or answers the errno of a subscription it refuses
    before it reaches the end); the events' room is 32 bytes per subscription (wasmtime's, per
    event written); the padding is written as zeros (wasmtime leaves it). Clocks injectable."""
    from wasmtime import WasmtimeError

    def call(caller: Any, in_ptr: int, out_ptr: int, n: int, nevents_ptr: int) -> int:
        try:
            memory = caller.get("memory")
            in_ptr, out_ptr, n, nevents_ptr = (
                v & MASK32 for v in (in_ptr, out_ptr, n, nevents_ptr)
            )
            if n == 0 or n > MAX_SUBSCRIPTIONS:
                return EINVAL if n == 0 else ENOMEM
            _aligned(in_ptr, 8)
            size = memory.data_len(caller)
            if in_ptr + 48 * n > size:
                return EFAULT
            raw = bytes(memory.read(caller, in_ptr, in_ptr + 48 * n))
            plan = _poll_plan(raw, n, realtime_ns(), monotonic_ns() - origin_ns, files.kind)
            if plan.errno is not None:
                return plan.errno
            for ptr, align in ((out_ptr, 8), (nevents_ptr, 4)):
                _aligned(ptr, align)
            if out_ptr + 32 * n > size or nevents_ptr + 4 > size:
                return EFAULT
            if plan.wait_ns:
                waits.wait(plan.wait_ns / 1e9)
            events = b"".join(struct.pack(EVENT, *e) for e in plan.events)
            memory.write(caller, events, out_ptr)
            memory.write(caller, struct.pack("<I", len(plan.events)), nevents_ptr)
            return 0
        except WasmtimeError as error:
            files.record_stop(error, caller)  # the fuel then is the guest's
            raise
        except Exception:
            return EINVAL  # anything else is recorded by the shared function

    return call


def _first_line(text: str) -> str:
    lines = text.strip().splitlines()
    return lines[0] if lines else "trap"


def _trap_name(e: wasmtime.Trap) -> str:
    import wasmtime as wt

    if e.trap_code == wt.TrapCode.OUT_OF_FUEL:
        return "out of fuel"
    if e.trap_code == wt.TrapCode.INTERRUPT:
        return "deadline"
    if e.trap_code is not None:  # by its kind, not wasmtime's heading
        return _trap_code_name(e.trap_code)
    return _first_line(e.message)


def _trap_code_name(code: wasmtime.TrapCode) -> str:
    """`TrapCode.STACK_OVERFLOW` is "stack overflow"."""
    return code.name.lower().replace("_", " ")


def _door_answer(host: Host, request: bytes) -> bytes | None:
    """The host's answer as exact bytes, or None for a fault; on the home thread, so a response's
    own code (a bytes subclass's `__bytes__` or `__len__`) runs there too. The cap is checked on
    the answer's buffer before the copy, so an over-cap buffer is never doubled, and again on the
    exact bytes, since a subclass's `__bytes__` may return more, or an object whose `len` is not
    its buffer's. What leaves here is the object the guest thread measures and writes."""
    response = host(request)
    if not isinstance(response, (bytes, bytearray, memoryview)):
        return None
    if memoryview(response).nbytes > MAX_RESPONSE:
        return None  # checked in bytes, before the copy
    data = bytes(response)
    if type(data) is not bytes:  # a `__bytes__` that returned a subclass
        data = bytes(memoryview(data))
    if len(data) > MAX_RESPONSE:
        return None
    return data


class _GuestStop(Exception):
    """A trap or exit raised inside the guest's host_alloc, carried past the door's own
    `except Exception` so that it stops the call, where a wasmtime exception the host raised is
    a fault."""

    def __init__(self, cause: BaseException) -> None:
        super().__init__()
        self.cause = cause


def _door(
    host: Host | None,
    admit: Callable[[int], bytes | None] | None = None,
    home: _Home | None = None,
) -> Callable[..., int]:
    """host::call(ptr, len, out_ptr_ptr, out_len_ptr) -> 0, -1 or -2.

    With `admit` (the tool protocol's frame host), each frame's length is offered to
    it once the addresses are checked and before the frame is read: bytes it returns are the
    answer, and the frame is never copied out of guest memory, so a refused frame costs the
    host the same whatever its length. The raw `host=` path passes no `admit`, as before."""

    import wasmtime as wt

    depth = 0  # door calls in progress on this call: one, unless host_alloc calls the door

    def call(caller: Any, ptr: int, length: int, out_ptr_ptr: int, out_len_ptr: int) -> int:
        nonlocal depth
        if host is None:
            return NO_HOST
        if depth:  # a door call from inside host_alloc: refused, before its frame is read
            return HOST_FAULT
        depth += 1
        try:
            return frame(caller, ptr, length, out_ptr_ptr, out_len_ptr, host)
        except _GuestStop as passed:
            raise passed.cause from None  # the shared function records it as the call's stop
        except Exception:  # a host's wasmtime exception too: the host's, not the guest's
            return HOST_FAULT  # nothing a frame or a host does escapes run()
        finally:
            depth -= 1

    def frame(
        caller: Any, ptr: int, length: int, out_ptr_ptr: int, out_len_ptr: int, host: Host
    ) -> int:
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
            admitted: bytes = response  # the frame host's own answer, as a host's would be read
            response = _door_answer(lambda _: admitted, b"")
        if response is None:
            return HOST_FAULT
        try:
            p = alloc(caller, len(response)) & MASK32
        except (wt.Trap, wt.WasmtimeError) as cause:
            raise _GuestStop(cause) from None  # a trap or exit inside host_alloc is the guest's
        if not p or p + len(response) > memory.data_len(caller):
            return HOST_FAULT
        memory.write(caller, response, p)
        memory.write(caller, struct.pack("<I", p), out_ptr_ptr)
        memory.write(caller, struct.pack("<I", len(response)), out_len_ptr)
        return 0

    return call


# The tool threads alive in this process: one per tool call, counted in
# as it starts and out as it ends, after its call returned or not.


def _count_tool_threads(delta: int) -> None:
    p = process()
    with p.tool_threads_lock:
        p.tool_threads_running += delta


def _count_abandoned(delta: int) -> int:
    """The tool threads still running after their call was answered, across the process, after
    adding `delta`: the count a bound refuses a tool call by."""
    p = process()
    with p.tool_threads_lock:
        p.tool_threads_abandoned += delta
        return p.tool_threads_abandoned


def _home_context(home: _Home | None) -> Callable[[], contextvars.Context]:
    """How a tool call copies its context: on the home thread, so it sees what a provider or the
    door host set earlier in the call; with no home
    thread, where the call is made."""
    if home is None:
        return contextvars.copy_context
    return lambda: home.call(contextvars.copy_context)


def _ctrl_c_now() -> bool:
    """A Ctrl-C is pending for the call on this (the main) thread: read, never cleared."""
    return _home._ctrl_c_watched() and process().ctrl_c_pending


def _tool_host(
    c: _CheckedCall,
    stop_at: int | None,
    cancel: threading.Event | None,
    loop: asyncio.AbstractEventLoop | None,
    home: _Home | None,
) -> _ToolHost | None:
    """The call's frame host, for a call with tools=, bound by the call's deadline, its cancel
    and Ctrl-C, and by an exception raised into its home thread,
    where each tool call's context is copied; None otherwise. With
    no home thread (a host the judge drives itself), the embedder's code runs where the frame
    is answered, as a `_Call` without a home runs its door."""
    if c.tools is None:
        return None
    from ._tool_host import _Bounded, _ToolHost, _ToolLoop

    bound = _Bounded(
        tick_s=TICK_S,
        stop_at=stop_at,
        ticks=lambda: _epoch_ticker.count(),
        cancel=cancel,
        ctrl_c=_ctrl_c_now if home is None else (lambda: _ctrl_c_now() or home.stopped()),
        count=_count_tool_threads,
        abandoned=_count_abandoned,
        context=_home_context(home),
    )
    # Under run_async, the caller's loop; otherwise a private loop of the call's own.
    tool_loop = _ToolLoop(loop, count=_count_tool_threads)
    return _ToolHost(
        c.tools,
        gate=c.gate,
        max_calls=c.tool_calls,
        invoke=bound,
        tool_loop=tool_loop,
        max_bytes=c.tool_request_bytes,  # the call's byte budget for frames
    )
