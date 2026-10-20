"""What the operating system decides: the flags and the kernel's identity, the two lock
implementations, fork, directory descriptors, the stack sizes and the three stack probes, and
the trap-handler guard."""

from __future__ import annotations

import ctypes
import errno
import os
import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ._process import process


def _flags(*names: str) -> int:
    flags = 0
    for name in names:
        flags |= getattr(os, name, 0)
    return flags


def _kernel_identity() -> str | None:
    """Which kernel this process runs on, or None: a lock taken on one kernel is invisible to
    another that shares the folder (a VM and its host), so a sweep touches only its own."""
    identity = process().kernel_identity
    if "value" not in identity:
        value = None
        try:
            if sys.platform.startswith("linux"):
                value = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
            elif sys.platform == "darwin":
                import ctypes.util

                libc = ctypes.CDLL(ctypes.util.find_library("c"))
                size_p, void_p = ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p
                libc.sysctlbyname.argtypes = [
                    ctypes.c_char_p,
                    void_p,
                    size_p,
                    void_p,
                    ctypes.c_size_t,
                ]
                libc.sysctlbyname.restype = ctypes.c_int
                buf, size = ctypes.create_string_buffer(64), ctypes.c_size_t(64)
                name = b"kern.bootsessionuuid"
                if libc.sysctlbyname(name, buf, ctypes.byref(size), None, 0) == 0:
                    value = buf.value.decode("ascii")
            elif sys.platform == "win32":
                import winreg

                access = winreg.KEY_READ | winreg.KEY_WOW64_64KEY
                where = r"SOFTWARE\Microsoft\Cryptography"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, where, 0, access) as key:
                    value = str(winreg.QueryValueEx(key, "MachineGuid")[0])
        except Exception:
            value = None
        identity["value"] = value if value and "\n" not in value else None
    return identity["value"]


_BUSY = {errno.EACCES, errno.EDEADLK, getattr(errno, "EDEADLOCK", errno.EDEADLK)}


def _try_lock(fd: int) -> bool | None:
    """Lock the open file without waiting: True when locked, False when another holder has it,
    None when this filesystem gives no lock (`ENOLCK` on NFS without a lock daemon, say)."""
    try:
        if sys.platform == "win32":
            import msvcrt

            os.lseek(fd, 0, 0)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        return False
    except OSError as e:
        return False if sys.platform == "win32" and e.errno in _BUSY else None


def _unlock_close(fd: int) -> None:
    """Unlock (Windows frees a closed handle's lock only after a delay), then close; quiet."""
    if sys.platform == "win32":
        try:
            import msvcrt

            os.lseek(fd, 0, 0)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
    try:
        os.close(fd)
    except OSError:
        pass


def _same_file(fd: int, path: str) -> bool:
    """Whether the open file is still the file at `path`; False when the path is gone."""
    try:
        opened, named = os.fstat(fd), os.lstat(path)
    except OSError:
        return False
    return (opened.st_dev, opened.st_ino) == (named.st_dev, named.st_ino)


# Fork (spec 015, Decision 5). A child of a process that made an engine inherits state from
# threads that no longer exist, and wasmtime does not support use across a fork (on macOS it
# aborts), so such a child is refused. A child of a parent that only imported this runs normally.


def _refuse_forked() -> None:
    if process().forked:
        raise RuntimeError(
            "wasi_python was used before this process was forked; use it in the child only, or "
            "start processes with 'spawn' or 'forkserver'"
        )


def _dir_fd_ok() -> bool:
    return os.mkdir in os.supports_dir_fd and shutil.rmtree.avoids_symlink_attacks is not False


def _open_dir(path: Path) -> int | None:
    """A handle on a directory, opened without following a link; None where the platform has no
    dir_fd support (Windows)."""
    if not _dir_fd_ok():
        return None
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    return os.open(path, flags)


def _close(fd: int | None) -> None:
    if fd is not None:
        os.close(fd)


# The guest's stack (spec 078). Every entry into wasm runs on a guest thread the runner makes for
# it, with _THREAD_STACK bytes of stack, _WASM_STACK of them for wasm (Decision 1). The C-stack
# window (128 KiB, recipes/reactor_main.c, spec 071) is unchanged. _HOST_ROOM holds what runs below
# the guest's frames: the runner's own callbacks (measured at most 48 KiB), and the collector's
# finalizers, audit hooks and trace functions that can run inside them (Decision 2; review F9).
_WASM_STACK = 8 << 20
_HOST_ROOM = 2 << 20
_THREAD_STACK = _WASM_STACK + _HOST_ROOM


# The guest thread's own stack (Decision 3). Each C function is a private prototype, resolved once;
# no argtypes are set on a shared ctypes attribute. What is measured is the thread's whole stack as
# the C library reports it (glibc's static TLS and thread descriptor lie inside it, and the frames
# above the entry count too), not the room left at the entry: the 1 MiB between the refusal line
# and the thread's size, and the host room, absorb both (the review's F14).


def _guest_stack(platform: str | None = None) -> tuple[int, int] | None:
    """(the usable bottom, the usable size) of this thread's stack, or None if unreadable."""
    try:
        plat = platform if platform is not None else sys.platform
        if plat.startswith(("linux", "android")):
            return _posix_stack()
        if plat == "darwin":
            return _darwin_stack()
        if plat == "win32":
            return _windows_stack()
    except Exception:
        return None
    return None


def _posix_stack() -> tuple[int, int] | None:
    api = process().stack_api
    if "getattr" not in api:
        libc = ctypes.CDLL(None)
        vp, sz = ctypes.c_void_p, ctypes.c_size_t
        api["self"] = ctypes.CFUNCTYPE(ctypes.c_ulong)(("pthread_self", libc))
        api["getattr"] = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_ulong, vp)(
            ("pthread_getattr_np", libc)
        )
        api["getstack"] = ctypes.CFUNCTYPE(
            ctypes.c_int, vp, ctypes.POINTER(vp), ctypes.POINTER(sz)
        )(("pthread_attr_getstack", libc))
        api["guard"] = ctypes.CFUNCTYPE(ctypes.c_int, vp, ctypes.POINTER(sz))(
            ("pthread_attr_getguardsize", libc)
        )
        api["destroy"] = ctypes.CFUNCTYPE(ctypes.c_int, vp)(("pthread_attr_destroy", libc))
    attr = (ctypes.c_char * 1024)()  # larger than any pthread_attr_t
    if api["getattr"](api["self"](), attr) != 0:
        return None
    try:
        addr, size, guard = ctypes.c_void_p(), ctypes.c_size_t(), ctypes.c_size_t()
        if api["getstack"](attr, ctypes.byref(addr), ctypes.byref(size)) != 0:
            return None
        if api["guard"](attr, ctypes.byref(guard)) != 0:
            return None
    finally:
        api["destroy"](attr)
    if not addr.value or size.value <= guard.value:
        return None
    return addr.value + guard.value, size.value - guard.value


def _darwin_stack() -> tuple[int, int] | None:
    api = process().stack_api
    if "top" not in api:
        libc = ctypes.CDLL(None)
        vp = ctypes.c_void_p
        api["self"] = ctypes.CFUNCTYPE(vp)(("pthread_self", libc))
        api["top"] = ctypes.CFUNCTYPE(vp, vp)(("pthread_get_stackaddr_np", libc))
        api["size"] = ctypes.CFUNCTYPE(ctypes.c_size_t, vp)(("pthread_get_stacksize_np", libc))
    me = api["self"]()
    top, size = api["top"](me), api["size"](me)
    if not top or not size or size >= top:
        return None
    return top - size, size


def _windows_stack() -> tuple[int, int] | None:
    """Counted conservatively: high - low - the thread's stack guarantee - one page (F7)."""
    api = process().stack_api
    if "limits" not in api:
        kernel32 = ctypes.WinDLL("kernel32")  # type: ignore[attr-defined]
        up = ctypes.POINTER(ctypes.c_size_t)
        api["limits"] = ctypes.WINFUNCTYPE(None, up, up)(  # type: ignore[attr-defined]
            ("GetCurrentThreadStackLimits", kernel32)
        )
        api["guarantee"] = ctypes.WINFUNCTYPE(  # type: ignore[attr-defined]
            ctypes.c_int, ctypes.POINTER(ctypes.c_ulong)
        )(("SetThreadStackGuarantee", kernel32))
    low, high = ctypes.c_size_t(), ctypes.c_size_t()
    api["limits"](ctypes.byref(low), ctypes.byref(high))
    guarantee = ctypes.c_ulong(0)
    if not api["guarantee"](ctypes.byref(guarantee)):  # 0 asks; it changes nothing
        return None
    return _windows_usable(low.value, high.value, guarantee.value)


def _windows_usable(
    low: int, high: int, guarantee: int, page: int = 4096
) -> tuple[int, int] | None:
    size = high - low - guarantee - page
    return (low + guarantee + page, size) if size > 0 else None


def _pyapi(name: str, restype: Any, *argtypes: Any) -> Any:
    """A private prototype of a C API function: no restype or argtypes is set on
    `ctypes.pythonapi`'s shared attributes (spec 078, the review's F5). AttributeError if absent."""
    return ctypes.PYFUNCTYPE(restype, *argtypes)((name, ctypes.pythonapi))


def _tell_interpreter(
    bottom: int,
    size: int,
    *,
    implementation: str | None = None,
    version: tuple[int, ...] | None = None,
    platform: str | None = None,
    libc: str | None = None,
    resolve: Callable[..., Any] | None = None,
) -> bool:
    """Where CPython 3.14 and later guess their thread's stack (Linux without glibc), tell the
    interpreter this thread's real one, or a callback from deep in the guest ends the process
    (Decision 3). True when told. CPython 3.14.0 there has no such call: RuntimeError."""
    import platform as platform_module

    name = implementation if implementation is not None else sys.implementation.name
    ver = version if version is not None else tuple(sys.version_info[:3])
    plat = platform if platform is not None else sys.platform
    if name != "cpython" or ver[:2] < (3, 14) or not plat.startswith("linux"):
        return False
    lib = libc if libc is not None else platform_module.libc_ver()[0]
    if lib == "glibc":
        return False
    find = resolve if resolve is not None else _pyapi
    try:
        get = find("PyThreadState_Get", ctypes.c_void_p)
        protect = find(
            "PyUnstable_ThreadState_SetStackProtection",
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_size_t,
        )
    except AttributeError:
        raise RuntimeError(
            f"CPython {'.'.join(map(str, ver))} on this C library guesses its thread's stack and "
            "cannot be told the guest thread's; use CPython 3.14.1 or later"
        ) from None
    try:
        protect(get(), bottom, size)
    except Exception as e:
        raise RuntimeError(f"the interpreter refused the guest thread's stack: {e}") from None
    return True


# Linux: the fatal signals wasmtime 49 handles to turn a fault in wasm into a trap
# (crates/wasmtime/src/runtime/vm/sys/unix/signals.rs, foreach_handler): SIGSEGV and SIGILL, and
# SIGFPE on x86_64. Its handlers are installed when the first engine is made (spec 071, Decision 9).
_TRAP_SIGNALS = ("SIGSEGV", "SIGILL")
_TRAP_SIGNALS_X86_64 = ("SIGFPE",)
_TRAP_HANDLERS_REPLACED = (
    "wasmtime's handler for {signal} was replaced after the first run, by a handler installed or "
    "removed since (faulthandler, signal.signal, or a native crash reporter); a trap in the guest "
    "would end or hang this process, so the call was refused. If faulthandler.enable() was "
    "called after the first run, faulthandler.disable() undoes it; otherwise restart the "
    "process, and install faulthandler or any crash reporter before the first run"
)


class _DlInfo(ctypes.Structure):
    _fields_ = [
        ("dli_fname", ctypes.c_char_p),
        ("dli_fbase", ctypes.c_void_p),
        ("dli_sname", ctypes.c_char_p),
        ("dli_saddr", ctypes.c_void_p),
    ]


def _load_base(address: int | None) -> int | None:
    """The load base of the shared object that holds `address`, by dladdr; None if none does."""
    if not address or address in (1,):  # SIG_DFL (0) and SIG_IGN (1) are in no object
        return None
    info = _DlInfo()
    if not process().handlers["dladdr"](ctypes.c_void_p(address), ctypes.byref(info)):
        return None
    return info.dli_fbase or None


def _handler_base(signum: int) -> int | None:
    """The load base of the object holding `signum`'s installed handler (the first word of
    `struct sigaction` in glibc and musl alike), or None."""
    buf = (ctypes.c_char * 1024)()  # larger than any struct sigaction
    if process().handlers["sigaction"](signum, None, buf) != 0:
        return None
    return _load_base(ctypes.c_void_p.from_buffer(buf).value)


def _wasmtime_base() -> int | None:
    """The load base of wasmtime-py's own library, read once, from one of its symbols."""
    handlers = process().handlers
    if "wasmtime" not in handlers:
        from . import _wasmtime_ffi as ffi

        handlers["wasmtime"] = _load_base(ffi.engine_symbol_address())
    base: int | None = handlers["wasmtime"]
    return base


def _trap_handlers_ready(
    platform: str | None = None,
    machine: str | None = None,
    handler_base: Callable[[int], int | None] | None = None,
    wasmtime_base: Callable[[], int | None] | None = None,
) -> str | None:
    """None when a trap in the guest would reach wasmtime; else the first signal whose handler is
    not wasmtime's (spec 071, Decision 9). Only on Linux, where wasmtime catches traps with signal
    handlers that a later faulthandler.enable() or disable(), a signal.signal or a native crash
    reporter can replace; macOS uses Mach ports and Windows a vectored handler. Exact for
    faulthandler, conservative for other handlers. Any failure counts as not ready."""
    import signal as signals

    if not (platform if platform is not None else sys.platform).startswith("linux"):
        return None
    names: tuple[str, ...] = _TRAP_SIGNALS
    if (machine if machine is not None else os.uname().machine) == "x86_64":
        names += _TRAP_SIGNALS_X86_64
    name = names[0]
    try:
        if handler_base is None or wasmtime_base is None:
            handlers = process().handlers
            if "sigaction" not in handlers:
                libc = ctypes.CDLL(None, use_errno=True)
                libc.sigaction.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
                libc.sigaction.restype = ctypes.c_int
                libc.dladdr.argtypes = [ctypes.c_void_p, ctypes.POINTER(_DlInfo)]
                libc.dladdr.restype = ctypes.c_int
                handlers["dladdr"], handlers["sigaction"] = libc.dladdr, libc.sigaction
            handler_base = handler_base or _handler_base
            wasmtime_base = wasmtime_base or _wasmtime_base
        ours = wasmtime_base()
        for name in names:
            if ours is None or handler_base(int(getattr(signals, name))) != ours:
                return name
    except Exception:
        return name
    return None
