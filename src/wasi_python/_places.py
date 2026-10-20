"""Places a guest may reach: `Grant`, the argument checks for root, grants, mounts and the
import path, the POSIX and Windows walks and their judge, SipHash-1-3 and the preopen check,
the runtime and shared folders, and the real directory at a path."""

from __future__ import annotations

import os
import struct
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

from . import _limits, _platform, _zip
from ._artifacts import Artifacts
from ._limits import _UNSET
from ._platform import Identity, _Walked
from .mounts import METHODS, Mount

if TYPE_CHECKING:
    from .runner import Defaults


@dataclass(frozen=True)
class Grant:
    """A host folder the guest sees at a guest path, read-only unless `writable=True`.

    A grant may be nested in another; `run` checks every grant before any work.

    Attributes:
        host: The host folder, a str or os.PathLike[str].
        guest: Where the guest sees it: an absolute guest path, not / and not the runtime's
            own /usr/local/lib.
        writable: Whether the guest may write there. Keyword-only.
    """

    # spec 017
    host: str | os.PathLike[str]
    guest: str
    writable: bool = field(default=False, kw_only=True)


# Grants (spec 017). A grant is a host folder the guest sees at a guest path, read-only unless it
# says `writable=True`. Every host path, `root` included, is walked one component at a time from
# `/`, judging each link on the way, and every rule compares identities (device and inode), never
# spellings: macOS folders are case-insensitive, and Windows spells one folder many ways. wasmtime
# then opens each path itself, so before the guest runs a check module of the runner's own reads
# back each preopen's identity and compares it with the walk's (Decision 5).
ZIP_GUEST = "/usr/local/lib"
_M64 = (1 << 64) - 1


def _host_path(where: str, value: Any) -> str:
    if isinstance(value, (bytes, bytearray)):
        raise TypeError(f"{where} must be a str or os.PathLike[str], not bytes")
    try:
        path = os.fspath(value)
    except TypeError:
        raise TypeError(
            f"{where} must be a str or os.PathLike[str], not {type(value).__name__}"
        ) from None
    if not isinstance(path, str):
        raise TypeError(f"{where} must be a str or os.PathLike[str], not a path of bytes")
    path = _limits._text(where, path)
    if not path:
        raise ValueError(f"{where} is empty")
    return path


def _guest_path(where: str, value: Any) -> str:
    """An absolute guest path with no empty, `.` or `..` component and no trailing `/`, which
    wasi-libc would otherwise match by text alone (memo §7d); not `/` and not the runtime's."""
    if not isinstance(value, str):
        raise TypeError(f"{where}: the guest path must be a str, not {type(value).__name__}")
    path = _limits._text(f"{where}: the guest path", value)
    if not path.startswith("/"):
        raise ValueError(f"{where}: the guest path must be absolute; got {path!r}")
    if path == "/":
        raise ValueError(f"{where}: the guest path / is the root; pass root= instead")
    if any(part in ("", ".", "..") for part in path.split("/")[1:]):
        raise ValueError(
            f"{where}: the guest path {path!r} has an empty, '.' or '..' part, or ends in '/'"
        )
    if path == ZIP_GUEST or path.startswith(ZIP_GUEST + "/"):
        raise ValueError(f"{where}: {path!r} is the runtime's own ({ZIP_GUEST})")
    return path


def _check_root(root: Any) -> str | bool | None:
    """The root as the runner keeps it: a host path; None for a private root (`root=True`); or
    False for none, the default (spec 025: nothing writable unless the embedder asks)."""
    if root is None or root is False:
        return False
    if root is True:
        return None
    return _host_path("root", root)


def _check_grants(grants: Any) -> tuple[Grant, ...]:
    """The grants as a tuple of plain `Grant`s, so `run_async` hands its worker no used iterator."""
    if isinstance(grants, (str, bytes, bytearray, Grant)) or not isinstance(grants, Iterable):
        raise TypeError(f"grants must be an iterable of Grant, not {type(grants).__name__}")
    checked: list[Grant] = []
    seen: set[str] = set()
    for i, grant in enumerate(grants):
        if not isinstance(grant, Grant):
            raise TypeError(f"grants[{i}] must be a Grant, not {type(grant).__name__}")
        guest = _guest_path(f"grants[{i}]", grant.guest)
        where = f"grants[{i}] at {guest}"
        if type(grant.writable) is not bool:
            raise TypeError(f"{where}: writable must be True or False, not {grant.writable!r}")
        if guest in seen:
            raise ValueError(f"{where}: another grant has the same guest path")
        seen.add(guest)
        checked.append(
            Grant(_host_path(f"{where}: host", grant.host), guest, writable=grant.writable)
        )
    return tuple(checked)


class _Places(NamedTuple):
    """A call's places, checked together: the root (`False` none, `None` a private one, else a
    host path), the grants, the mounts, the import path with the index of the read-only grant
    serving each entry, and the two caps every call has."""

    root: str | bool | None
    grants: tuple[Grant, ...]
    mounts: tuple[Mount, ...]
    import_path: tuple[str, ...]
    import_serving: tuple[int, ...]
    file_calls: int | None
    open_files: int | None


def _check_places(
    root: Any,
    grants: Any,
    mounts: Any,
    max_file_calls: Any,
    limits: Defaults,
    *,
    import_path: Any = (),
    max_open_files: Any = _UNSET,
) -> _Places:
    """root, grants, mounts, the import path, the file-call limit and the cap on open files,
    checked together before any work: a mount may share no guest path with a grant, and a mount
    at / comes with no root (spec 032); each import-path entry is served by a read-only grant
    (spec 054); the cap applies to every call, with or without places (spec 068)."""
    checked_root = _check_root(root)
    checked_grants = _check_grants(grants)
    checked_mounts = _check_mounts(mounts, checked_grants, checked_root)
    entries, serving = _check_import_path(import_path, checked_grants, checked_mounts, checked_root)
    if max_file_calls is _UNSET:
        max_file_calls = limits.file_calls
    if max_open_files is _UNSET:
        max_open_files = limits.open_files
    return _Places(
        checked_root,
        checked_grants,
        checked_mounts,
        entries,
        serving,
        _limits._integer_limit("max_file_calls", max_file_calls),
        _limits._integer_limit("max_open_files", max_open_files),
    )


def _under(path: str, place: str) -> bool:
    """`path` is at or below `place` by whole components, as wasi-libc matches a preopen; never
    by text alone (`/code2` is not under `/code`)."""
    return place == "/" or path == place or path.startswith(place + "/")


def _check_import_path(
    import_path: Any, grants: tuple[Grant, ...], mounts: tuple[Mount, ...], root: Any
) -> tuple[tuple[str, ...], tuple[int, ...]]:
    """The import path's entries, as the plain strings `_guest_path` returns (never the caller's
    objects, which the prelude is built from), and for each the index of the read-only grant that
    serves it; or TypeError for a type and ValueError for a value (spec 054, Decisions 2 to 4).
    The place serving an entry is the one with the longest guest prefix, as wasi-libc resolves
    it, and must be a read-only grant; no writable grant and no mount may lie under an entry."""
    if isinstance(import_path, (str, bytes, bytearray)) or not isinstance(import_path, Iterable):
        raise TypeError(f"import_path must be an iterable of str, not {type(import_path).__name__}")
    # Every place a path can resolve to: (guest path, what it is, its index, writable).
    places: list[tuple[str, str, int, bool]] = [
        (g.guest, "grants", i, g.writable) for i, g in enumerate(grants)
    ]
    places += [(m.guest, "mounts", i, m.writable) for i, m in enumerate(mounts)]
    if root is not False:  # a host path or a private root: always writable, at /
        places.append(("/", "root", -1, True))
    entries: list[str] = []
    serving: list[int] = []
    for i, entry in enumerate(import_path):
        where = f"import_path[{i}]"
        if isinstance(entry, str) and str.__str__(entry) == "/":
            raise ValueError(f"{where}: / cannot be on the import path; name a folder or a zip")
        path = _guest_path(where, entry)
        where = f"{where} {path!r}"
        if path in entries:
            raise ValueError(f"{where}: another entry is the same")
        found = [p for p in places if _under(path, p[0])]
        if not found:
            raise ValueError(f"{where}: no grant serves it; name a path inside a read-only grant")
        guest, kind, k, writable = max(found, key=lambda p: len(p[0]))
        named = "the root" if kind == "root" else f"{kind}[{k}] at {guest}"
        if kind == "mounts":
            raise ValueError(
                f"{where} is served by {named}, a mount; only a read-only grant may serve the "
                "import path (a provider may also be serving a writable store)"
            )
        if writable:
            raise ValueError(
                f"{where} is served by {named}, which is writable; only a read-only grant may "
                "serve the import path"
            )
        for other, okind, ok, owritable in places:
            if okind != "root" and (owritable or okind == "mounts") and _under(other, path):
                what = "a mount" if okind == "mounts" else "writable"
                raise ValueError(
                    f"{where}: {okind}[{ok}] at {other} is {what} and lies under it; nothing "
                    "writable, and no mount, may lie under an entry"
                )
        entries.append(path)
        serving.append(k)
    return tuple(entries), tuple(serving)


def _check_mounts(mounts: Any, grants: tuple[Grant, ...], root: Any) -> tuple[Mount, ...]:
    """The mounts as a tuple of plain `Mount`s, or TypeError for a type and ValueError for a
    value, each naming the mount's position and guest path (spec 032, Decision 2)."""
    import inspect

    if isinstance(mounts, (str, bytes, bytearray, Mount)) or not isinstance(mounts, Iterable):
        raise TypeError(f"mounts must be an iterable of Mount, not {type(mounts).__name__}")
    checked: list[Mount] = []
    seen = {grant.guest for grant in grants}
    for i, mount in enumerate(mounts):
        if not isinstance(mount, Mount):
            raise TypeError(f"mounts[{i}] must be a Mount, not {type(mount).__name__}")
        if not isinstance(mount.guest, str):
            raise TypeError(
                f"mounts[{i}]: the guest path must be a str, not {type(mount.guest).__name__}"
            )
        text = _limits._text(f"mounts[{i}]: the guest path", mount.guest)
        guest = "/" if text == "/" else _guest_path(f"mounts[{i}]", text)
        where = f"mounts[{i}] at {guest}"
        if type(mount.writable) is not bool:
            raise TypeError(f"{where}: writable must be True or False, not {mount.writable!r}")
        # A writable mount's provider has the write half too (spec 034, Decision 1).
        methods = METHODS if mount.writable else METHODS[:3]
        for method in methods:
            function = getattr(mount.provider, method, None)
            if not callable(function):
                raise TypeError(f"{where}: the provider has no callable {method}()")
            if inspect.iscoroutinefunction(function):
                raise TypeError(
                    f"{where}: the provider's {method}() is a coroutine function; a provider "
                    "answers synchronously (async providers are a later specification)"
                )
        if guest in seen:
            raise ValueError(f"{where}: a grant or another mount has the same guest path")
        if guest == "/" and root is not False:
            raise ValueError(
                f"{where}: a mount at / is the guest's whole filesystem; it cannot be given "
                "with root="
            )
        seen.add(guest)
        checked.append(Mount(mount.provider, guest, writable=mount.writable))
    return tuple(checked)


def _chain(path: Path) -> tuple[Identity | None, tuple[Identity, ...]]:
    """A runtime folder's identity (None while it does not exist) and the identities of its
    deepest existing ancestor and that one's ancestors, every link followed; never refuses."""
    here = Path(os.path.realpath(path))
    exists = True
    while True:
        try:
            first = _platform.PLATFORM.identity_of(here)
            break
        except OSError:
            exists = False
            if here.parent == here:
                return None, ()
            here = here.parent
    chain = [first]
    for parent in here.parents:
        try:
            chain.append(_platform.PLATFORM.identity_of(parent))
        except OSError:
            break
    return (first if exists else None), tuple(chain)


def _judge(
    root: _Walked | None,
    grants: list[tuple[str, Grant, _Walked]],
    runtime: list[tuple[str, Any, Any]],
    shared: list[tuple[str, tuple[Identity, ...]]] = [],  # noqa: B006 (read only)
) -> None:
    """Decision 4's rules, by identity. `runtime` is (name, identity or None, chain) for each of
    the runtime's own folders: a writable grant at, inside or above one is refused; a folder not
    made yet holds nothing, so only a grant above its deepest existing ancestor is. `shared` is
    (name, chain) for each folder no grant, read-only included, may be at or above."""
    judged = [("root", None, root)] if root is not None else []
    for where, _, w in [*judged, *grants]:  # root too: the temporary folder may have moved
        for name, chain in shared:
            if w.identity is not None and w.identity in chain:
                raise ValueError(f"{where} holds {name}; grant a folder apart from it")
    writable = [("root", root)] if root is not None else []
    writable += [(where, w) for where, g, w in grants if g.writable]
    for where, w in writable:
        for name, identity, chain in runtime:
            inside = identity is not None and identity in w.chain
            above = w.identity is not None and w.identity in chain
            if inside or above:
                how = "is inside" if inside else "holds"
                raise ValueError(
                    f"{where} is writable and {how} {name}, which later calls trust; grant a "
                    "folder apart from it"
                )
    for where, g, r in grants:
        if g.writable:
            continue
        for other, w in writable:
            if w.identity is not None and w.identity in r.chain:
                raise ValueError(
                    f"{where} is read-only but inside {other}, which is writable; a guest would "
                    "change it through that grant"
                )


def _rotl(x: int, b: int) -> int:
    return ((x << b) | (x >> (64 - b))) & _M64


def _siphash13(data: bytes) -> int:
    v0, v1 = 0x736F6D6570736575, 0x646F72616E646F6D
    v2, v3 = 0x6C7967656E657261, 0x7465646279746573

    def rounds(n: int) -> None:
        nonlocal v0, v1, v2, v3
        for _ in range(n):
            v0 = (v0 + v1) & _M64
            v1 = _rotl(v1, 13) ^ v0
            v0 = _rotl(v0, 32)
            v2 = (v2 + v3) & _M64
            v3 = _rotl(v3, 16) ^ v2
            v0 = (v0 + v3) & _M64
            v3 = _rotl(v3, 21) ^ v0
            v2 = (v2 + v1) & _M64
            v1 = _rotl(v1, 17) ^ v2
            v2 = _rotl(v2, 32)

    end = len(data) - len(data) % 8
    for i in range(0, end, 8):
        m = struct.unpack_from("<Q", data, i)[0]
        v3 ^= m
        rounds(1)
        v0 ^= m
    last = (len(data) & 0xFF) << 56
    for i, byte in enumerate(data[end:]):
        last |= byte << (8 * i)
    v3 ^= last
    rounds(1)
    v0 ^= last
    v2 ^= 0xFF
    rounds(3)
    return v0 ^ v1 ^ v2 ^ v3


def _wasi_ino(identity: Identity) -> int:
    """The `ino` wasmtime reports for a folder of this identity. Rust sign-extends a negative
    dev_t, hence the mask; the words are native-endian, as Rust's Hash writes them."""
    return _siphash13(struct.pack("=QQ", identity[0] & _M64, identity[1] & _M64))


class _Preopen(NamedTuple):
    label: str  # how an error names it: "grant 2 at /data", "root", "the stdlib folder"
    walked: _Walked
    guest: str
    writable: bool


def _check_preopens(wt: Any, linker: Any, store: Any, check: Any, preopens: list[_Preopen]) -> None:
    """Before the guest: each preopen 3 + i is the folder the walk checked, by guest name and by
    identity. A mismatch raises before the guest runs; the walk's holds are released either way."""
    try:
        exports = linker.instantiate(store, check).exports(store)
        memory = exports["memory"]
        for i, p in enumerate(preopens):
            fd = 3 + i
            name = p.guest.encode()
            ok = exports["prestat"](store, fd) == 0
            if ok:
                head = bytes(memory.read(store, 0, 8))
                ok = head[0] == 0 and struct.unpack_from("<I", head, 4)[0] == len(name)
            ok = ok and exports["name"](store, fd, len(name)) == 0
            ok = ok and bytes(memory.read(store, 1024, 1024 + len(name))) == name
            ok = ok and exports["stat"](store, fd) == 0
            identity = p.walked.identity
            if ok and identity is not None:
                reported = struct.unpack("<Q", bytes(memory.read(store, 72, 80)))[0]
                ok = reported == _wasi_ino(identity)
            if not ok:
                raise RuntimeError(f"{p.label} changed between its check and the call")
    finally:
        for p in preopens:
            p.walked.close()


def _walk_grants(
    root: str | bool | None,
    grants: tuple[Grant, ...],
    found: Artifacts,
    cache: Path | None,
    import_path: tuple[str, ...] = (),
    serving: tuple[int, ...] = (),
) -> tuple[_Walked | None, list[tuple[str, Grant, _Walked]]]:
    """Every grant and `root`, walked and judged before any work (Decision 4); a missing root is
    made only once every rule has passed on its existing chain, the import path's included."""
    walked_root: _Walked | None = None
    walked: list[tuple[str, Grant, _Walked]] = []
    runtime = _runtime_folders(found, cache)  # first: it makes the module cache if it can
    try:
        if isinstance(root, str):
            walked_root = _platform.PLATFORM.walk("root", root, judge=True, may_make=True)
        for i, grant in enumerate(grants):
            where = f"grants[{i}] at {grant.guest}"
            walked.append(
                (where, grant, _platform.PLATFORM.walk(where, os.fspath(grant.host), judge=True))
            )
        _judge(walked_root, walked, runtime, _shared_folders())
        _judge_import_path(walked_root, walked, import_path, serving)
        if walked_root is not None and walked_root.missing:
            try:
                walked_root = _platform.PLATFORM.make_missing("root", walked_root)
            except OSError as e:
                raise ValueError(f"root: {root!r} cannot be made: {e.strerror or e}") from None
        return walked_root, walked
    except BaseException:
        for w in [walked_root, *(w for _, _, w in walked)]:
            if w is not None:
                w.close()
        raise


def _judge_import_path(
    root: _Walked | None,
    grants: list[tuple[str, Grant, _Walked]],
    import_path: tuple[str, ...],
    serving: tuple[int, ...],
) -> None:
    """Spec 054, Decision 5, by identity: no writable grant, and no root, at or inside the whole
    folder of a read-only grant that serves an entry. The whole folder, not the entry's
    subfolder: a link inside a grant reaches any folder of it. A root still to be made carries
    its deepest existing ancestor's chain, so one to be made inside is refused before it is."""
    writable = [("root", root)] if root is not None else []
    writable += [(where, w) for where, g, w in grants if g.writable]
    for i, (entry, k) in enumerate(zip(import_path, serving, strict=True)):
        where, _, r = grants[k]
        for other, w in writable:
            if r.identity is not None and r.identity in w.chain:
                raise ValueError(
                    f"import_path[{i}] {entry!r} is served by {where}, whose folder holds "
                    f"{other}, which is writable; a guest would plant code there for the import "
                    "path"
                )


def _runtime_folders(found: Artifacts, cache: Path | None) -> list[tuple[str, Any, Any]]:
    """The folders later calls and processes trust: this zip's folder (or, before it is made, the
    temporary folder that will hold it), the artifact set's files, the module cache, and the
    runtime's own code (this package and wasmtime-py's, whose native library a guest must never
    replace). The module cache is made first, if it can be, so it is judged as it will be: a root
    still to be made above a cache still to be made would otherwise come to hold it (the build
    review, finding 1)."""
    import wasmtime

    if cache is not None:
        try:
            cache.mkdir(mode=0o700, parents=True, exist_ok=True)
        except OSError:
            pass  # unusable: `_module` then keeps compiled modules in memory
    zip_dir = _zip._zip_known(found)
    if zip_dir is not None:
        folders = [("the runtime's stdlib folder", *_chain(zip_dir))]
    else:
        temp = Path(tempfile.gettempdir())
        folders = [
            ("the temporary folder, where the runtime's stdlib folder goes", None, _chain(temp)[1])
        ]
    parts = {found.manifest.parent, found.snapshot.parent, found.plain.parent}
    parts.add(found.stdlib_zip.parent)
    folders += [("the artifact set", *_chain(d)) for d in sorted(parts)]
    if cache is not None:
        folders.append(("the module cache", *_chain(cache)))
    folders.append(("wasi_python's own code", *_chain(Path(__file__).resolve().parent)))
    folders.append(("wasmtime-py's own code", *_chain(Path(wasmtime.__file__).resolve().parent)))
    # The host's own interpreter, which the next host process runs (spec 024, S2): its stdlib,
    # its site-packages and scripts, and the user's site-packages it imports at start-up.
    import site
    import sysconfig

    paths = sysconfig.get_paths()
    keys = ("stdlib", "platstdlib", "purelib", "platlib", "scripts")
    own = {Path(paths[k]).resolve() for k in keys if k in paths}
    if site.ENABLE_USER_SITE:
        own.add(Path(site.getusersitepackages()).resolve())
    folders += [("the host Python's own code", *_chain(d)) for d in sorted(own) if d.is_dir()]
    return folders


def _shared_folders() -> list[tuple[str, tuple[Identity, ...]]]:
    """Folders no grant may be at or above, read-only included: the temporary folder holds every
    call's private root and stdin (the build review, finding 2)."""
    temp = Path(tempfile.gettempdir())
    return [
        (
            "the temporary folder, which holds every call's private folders and stdin",
            _chain(temp)[1],
        )
    ]
