"""Starting images an embedder makes: `Snapshot`, `SnapshotOrigin`, `SnapshotFailed` and
`SnapshotMismatch`; the saved file; a call's check of its start and of the set; and the capture
and the restore of the guest's linear memory.

A snapshot is the guest's linear memory after the embedder's code ran once in a fresh instance
of the set's snapshot binary. Every call given one is a fresh instance of that binary whose
memory is grown to the image's size and the image copied in before its program runs, so nothing
a call does reaches the image or another call. Memory is the guest's whole state: the binary's
one mutable global, the stack pointer, is back at its first value whenever an export returns.

The copy is the host's, through wasmtime-py's public pointer to the memory, so it spends no
fuel. This module imports neither the call, the sessions nor the runner; they import it."""

from __future__ import annotations

import ctypes
import dataclasses
import datetime
import hashlib
import json
import os
import sys
import tempfile
import zlib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple, NoReturn

from . import _artifacts, _places, _platform
from ._artifacts import Artifacts, ArtifactsMissing
from ._process import process

if TYPE_CHECKING:
    from ._call import Completed

MAGIC = b"wasi-python snapshot\n"  # the file's first line names its kind
FORMAT = 1
CODEC = "zlib"  # in every supported Python's standard library
LEVEL = 1  # a save is once per image: the fastest level, a third of the image's size
PAGE = 65536
SLICE = 1 << 20  # the file is compressed and read in slices, never a second whole copy
IMAGE_HOME = "/tmp/.home-snapshot"  # every image's HOME: a path a package kept at import holds
MAX_CODE_BYTES = 16 << 20  # the code is kept in the file's header; more is data for a grant
MAX_HEADER_BYTES = 17 << 20  # the code and room for the rest
MAX_IMAGE_BYTES = 4 << 30  # the guest's 32-bit address space
REASONS = ("exit", "trapped", "open file")
_NOT_PUBLIC = "make a Snapshot with make_snapshot, make_package_snapshot or Snapshot.load"


class SnapshotMismatch(ValueError):
    """A snapshot does not fit where it is used: a saved file that is not one, is damaged or is
    of a newer format; a call whose artifact set is not the one the image was made with; or a
    call whose `memory_bytes` is below the image. The message says what to do."""


class SnapshotFailed(RuntimeError):
    """The code given to `make_snapshot` or `make_package_snapshot` did not leave an image a
    call could start from. The message is one line that says what to do.

    Attributes:
        reason: One of three fixed strings: "exit" (the code exited with a status other than 0,
            or raised), "trapped" (it trapped, ran out of fuel or passed its deadline, as
            `completed.trapped` says) or "open file" (it left a file or folder open).
        completed: The making's own `Completed`: its exit status, output and trap.
    """

    def __init__(self, message: str, *, reason: str, completed: Completed) -> None:
        super().__init__(message)
        self.reason = reason
        self.completed = completed


@dataclass(frozen=True)
class SnapshotOrigin:
    """Where a snapshot came from, kept with its image and in its saved file.

    Attributes:
        prelude: The code that made the image, as given: the image already holds its code
            objects, so the origin reveals nothing the image does not.
        prelude_sha256: The SHA-256 of the code as UTF-8.
        prelude_fuel: The instructions the code ran, when the making was given `fuel`; else
            `None`.
        image_bytes: The image's size: a whole number of 64 KiB pages.
        image_sha256: The SHA-256 of the image, which `Completed.image_sha256` repeats.
        home: The guest's HOME while the code ran, which every call from the image sees.
        guest_paths: The guest paths of the making's root, grants and mounts.
        env_names: The sorted names of the making's `env`, never their values.
        snapshot_sha256: The SHA-256 of the set's `python-snapshot.wasm` it was made with.
        stdlib_zip_sha256: The SHA-256 of the set's `python-stdlib.zip` it was made with.
        wasi_python: The version of wasi-python that made it.
        made_at: When it was made, in UTC, ISO 8601, to the second.
    """

    prelude: str
    prelude_sha256: str
    prelude_fuel: int | None
    image_bytes: int
    image_sha256: str
    home: str
    guest_paths: tuple[str, ...]
    env_names: tuple[str, ...]
    snapshot_sha256: str
    stdlib_zip_sha256: str
    wasi_python: str
    made_at: str


class _Start(NamedTuple):
    """What a checked call starts from: the image (None for a making), the guest's HOME, the
    image's SHA-256, and the set digests it binds to (snapshot binary, zip); None for a
    making."""

    image: bytes | None
    home: str
    sha256: str | None
    digests: tuple[str, str] | None


# The making's start, passed to `Session` by `make_snapshot` alone: the fixed HOME, no image.
MAKING = _Start(None, IMAGE_HOME, None, None)


class Snapshot:
    """A starting image: the guest's memory after your code ran once, and its origin.

    Make one with `make_snapshot` or `make_package_snapshot`, or read a saved one with
    `Snapshot.load`, and pass it as `snapshot=` to `run`, `run_async` or `Session`. Every call
    from it is a fresh instance that starts with a private copy of the image, so nothing one
    call does reaches the image or another call. A snapshot is immutable and may be used by any
    number of calls on any threads at once. It binds to the artifact set it was made with. It is
    not pickled: `save()` it and `Snapshot.load()` it, which checks the file.
    """

    __slots__ = ("_image", "_origin")
    _image: bytes
    _origin: SnapshotOrigin

    def __new__(cls, *args: object, **kwargs: object) -> Snapshot:
        raise TypeError(_NOT_PUBLIC)

    def __setattr__(self, name: str, value: object) -> NoReturn:
        raise AttributeError("a Snapshot cannot be changed")

    def __delattr__(self, name: str) -> NoReturn:
        raise AttributeError("a Snapshot cannot be changed")

    def __copy__(self) -> Snapshot:
        return self

    def __deepcopy__(self, memo: object) -> Snapshot:
        return self

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError(
            "a Snapshot is not pickled: save() it and Snapshot.load() it, which checks it"
        )

    def __repr__(self) -> str:
        origin = self._origin
        lines = origin.prelude.splitlines() or [""]
        first = lines[0] if len(lines[0]) <= 40 else lines[0][:40] + "…"
        more = len(lines) - 1
        others = "" if not more else f" +{more} line{'s' if more > 1 else ''}"
        size = origin.image_bytes / 2**20
        return (
            f"<Snapshot {first!r}{others}, {size:.1f} MiB, made {origin.made_at} "
            f"by wasi-python {origin.wasi_python}>"
        )

    @property
    def origin(self) -> SnapshotOrigin:
        """Where the image came from: its code, its size and hash, and the set it binds to."""
        return self._origin

    def save(self, path: str | os.PathLike[str]) -> None:
        """Write the snapshot to a file only you can write, which `Snapshot.load` reads back.

        The folder is checked first by the rule `load` holds the file to, so a file is never
        saved where it could not be loaded. The file is written beside its name and then moved
        onto it, replacing a file there. Keep it where no guest is granted writing.

        Args:
            path: The file to write; by convention its name ends in `.wpsnap`.

        Raises:
            TypeError: `path` is not a str or a path.
            PermissionError: Others may change the folder, or a folder on the way to it, or a
                call or session running now may write it.
            OSError: The file could not be written.
        """
        target = Path(_path("path", path)).absolute()
        _publish_and_check(target.parent)  # no running guest may rewrite it
        fd, temp = tempfile.mkstemp(prefix=".wasi-python-", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as f:
                os.close(_platform.PLATFORM.open_owned(Path(temp)))  # load's rule, first
                _write(f, self)
            os.replace(temp, target)
        except BaseException:
            try:
                os.unlink(temp)
            except OSError:
                pass
            raise

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> Snapshot:
        """Read a snapshot that `save` wrote, and check it before it is returned.

        The file must be one only you can write, as `save` makes it, and is read through the
        descriptor that was checked. Its header, its size, its stream and the image's hash are
        each checked, and the stream is never read past the size its header names. The set is
        not checked here: `Snapshot.check` does, and so does every call.

        Args:
            path: The file `save` wrote.

        Returns:
            The snapshot the file holds.

        Raises:
            TypeError: `path` is not a str or a path.
            SnapshotMismatch: The file is not a snapshot, is damaged, or is of a newer format.
            PermissionError: Others may write the file or its folder, or it is a link, or a
                call or session running now may write it.
            OSError: The file could not be read.
        """
        where = Path(_path("path", path))
        _publish_and_check(where.absolute().parent)
        fd = _platform.PLATFORM.open_owned(where)
        with os.fdopen(fd, "rb") as f:
            image, origin = _read(f, where)
        return _made(image, origin)

    def check(self, artifacts: Artifacts | None = None) -> None:
        """Raise the `SnapshotMismatch` a call would, without running a call.

        The set is found as a call finds it, and checked against its SHA256SUMS, unless one is
        given; the snapshot binary's and the stdlib zip's digests must be the origin's.

        Args:
            artifacts: The artifact set to check against; `None` finds it with `artifacts()`.

        Raises:
            TypeError: `artifacts` is not an `Artifacts`.
            SnapshotMismatch: The set is not the one the image was made with.
            ArtifactsMissing: There is no usable artifact set.
        """
        if artifacts is not None and not isinstance(artifacts, Artifacts):
            raise TypeError(f"artifacts must be an Artifacts, or None; got {type(artifacts)}")
        found, checked = (
            (artifacts, None) if artifacts is not None else _artifacts._found_and_checked(True)
        )
        _same_set(_start_of(self), found, checked)


def _made(image: bytes, origin: SnapshotOrigin) -> Snapshot:
    """A snapshot, made by the runner's own functions only."""
    snap = object.__new__(Snapshot)
    object.__setattr__(snap, "_image", image)
    object.__setattr__(snap, "_origin", origin)
    return snap


def _path(name: str, value: Any) -> str:
    if not isinstance(value, (str, os.PathLike)):
        raise TypeError(f"{name} must be a str or a path; got {type(value).__name__}")
    text = os.fspath(value)
    if not isinstance(text, str) or not text:
        raise TypeError(f"{name} must be a non-empty str path")
    return text


def _version() -> str:
    """The version of the package that runs: its own `__version__`, already imported."""
    return str(getattr(sys.modules.get(__package__ or "wasi_python"), "__version__", "unknown"))


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _origin_of(
    code: str, image: bytes, fuel: int | None, paths: Iterable[str], env_names: Iterable[str],
    digests: tuple[str, str],
) -> SnapshotOrigin:  # fmt: skip
    """The origin a making records."""
    return SnapshotOrigin(
        prelude=code,
        prelude_sha256=hashlib.sha256(code.encode("utf-8")).hexdigest(),
        prelude_fuel=fuel,
        image_bytes=len(image),
        image_sha256=hashlib.sha256(image).hexdigest(),
        home=IMAGE_HOME,
        guest_paths=tuple(paths),
        env_names=tuple(sorted(env_names)),
        snapshot_sha256=digests[0],
        stdlib_zip_sha256=digests[1],
        wasi_python=_version(),
        made_at=_now(),
    )


def _publish_and_check(folder: Path) -> None:
    """Keep a saved or loaded file's folder from every later call's writable grants, then refuse
    it if a call or session running now may write it, forgetting it again if it was new. Each
    side publishes before it checks, as a starting call registers its writable grants before it
    judges these folders, so of a call and a save at once, one always sees the other."""
    p, key = process(), str(folder)
    with p.cache_lock:
        new = key not in p.snapshot_folders
        p.snapshot_folders.add(key)
    try:
        _places._refuse_live_writable(folder)
    except PermissionError:
        if new:
            with p.cache_lock:
                p.snapshot_folders.discard(key)
        raise


# ---------------------------------------------------------------------------------------------
# The file: the first line, one line of JSON (the format, the codec and the origin, keys
# sorted), then the image as one zlib stream.


def _write(f: Any, snap: Snapshot) -> None:
    header = {"format": FORMAT, "codec": CODEC, **dataclasses.asdict(snap._origin)}
    f.write(MAGIC)
    f.write(json.dumps(header, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n")
    squeeze = zlib.compressobj(LEVEL)
    view = memoryview(snap._image)
    for at in range(0, len(view), SLICE):
        f.write(squeeze.compress(view[at : at + SLICE]))
    f.write(squeeze.flush())


def _read(f: Any, where: Path) -> tuple[bytes, SnapshotOrigin]:
    if f.readline(len(MAGIC)) != MAGIC:
        raise SnapshotMismatch(f"{where} is not a wasi-python snapshot file")
    line = f.readline(MAX_HEADER_BYTES + 1)
    if len(line) > MAX_HEADER_BYTES or not line.endswith(b"\n"):
        raise SnapshotMismatch(f"{where} has a header past {MAX_HEADER_BYTES:,} bytes, or none")
    try:
        header = json.loads(line)
    except ValueError:
        raise SnapshotMismatch(f"{where} has a damaged header") from None
    origin = _header_origin(header, where)
    image = _image_of(f, origin.image_bytes, where)
    if hashlib.sha256(image).hexdigest() != origin.image_sha256:
        raise SnapshotMismatch(f"{where} is damaged: its image does not match its hash")
    return image, origin


def _header_origin(header: Any, where: Path) -> SnapshotOrigin:
    """The origin a header holds, each field of its kind; the format and codec this reads."""
    if not isinstance(header, dict):
        raise SnapshotMismatch(f"{where} has a damaged header")
    form = header.get("format")
    if type(form) is not int or form < 1:
        raise SnapshotMismatch(f"{where} has a damaged header: format {form!r}")
    if form > FORMAT:
        raise SnapshotMismatch(
            f"{where} was saved by a newer wasi-python, format {form}; this one reads format "
            f"{FORMAT}"
        )
    if header.get("codec") != CODEC:
        raise SnapshotMismatch(f"{where} is compressed with {header.get('codec')!r}, not zlib")
    values: dict[str, Any] = {}
    for field in dataclasses.fields(SnapshotOrigin):
        value = header.get(field.name)
        if field.name in ("guest_paths", "env_names") and isinstance(value, list):
            value = tuple(value)
        kinds = {"prelude_fuel": (int, type(None)), "image_bytes": (int,)}.get(field.name)
        if field.name in ("guest_paths", "env_names"):
            ok = isinstance(value, tuple) and all(isinstance(v, str) for v in value)
        else:
            ok = type(value) in (kinds or (str,))
        if not ok:
            raise SnapshotMismatch(f"{where} has a damaged header: {field.name} {value!r}")
        values[field.name] = value
    if values["home"] != IMAGE_HOME:  # format 1 has one HOME, which every call preopens
        raise SnapshotMismatch(f"{where} has a damaged header: home {values['home']!r}")
    size = values["image_bytes"]
    if size <= 0 or size % PAGE or size > MAX_IMAGE_BYTES:
        raise SnapshotMismatch(
            f"{where} names an image of {size:,} bytes: not a whole number of 64 KiB pages up "
            "to 4 GiB"
        )
    return SnapshotOrigin(**values)


def _image_of(f: Any, size: int, where: Path) -> bytes:
    """The stream decompressed to exactly `size` bytes, never one byte further."""
    stream = zlib.decompressobj()
    out = bytearray()
    try:
        while not stream.eof:
            chunk = stream.unconsumed_tail or f.read(SLICE)
            if not chunk:
                break
            out += stream.decompress(chunk, size - len(out) + 1)
            if len(out) > size:
                raise SnapshotMismatch(f"{where} holds more than its image of {size:,} bytes")
    except zlib.error:
        raise SnapshotMismatch(f"{where} is damaged: its stream does not decompress") from None
    if not stream.eof or len(out) != size:
        raise SnapshotMismatch(f"{where} is damaged: its stream ends before {size:,} bytes")
    if stream.unused_data or f.read(1):
        raise SnapshotMismatch(f"{where} is damaged: it has bytes past its stream")
    return bytes(out)


# ---------------------------------------------------------------------------------------------
# A call's start, and the set it binds to.


def _start(snapshot: Any, memory_bytes: int | None) -> tuple[str, _Start | None]:
    """`snapshot=` checked: the binary a call runs ("snapshot" or "plain"), and what it starts
    from. A snapshot needs `memory_bytes` at least its image."""
    if snapshot is MAKING:
        return "snapshot", MAKING
    if isinstance(snapshot, bool):
        return ("snapshot" if snapshot else "plain"), None
    if not isinstance(snapshot, Snapshot):
        name = type(snapshot).__name__
        raise TypeError(f"snapshot must be True, False or a Snapshot; got {name}")
    size = snapshot.origin.image_bytes
    if memory_bytes is not None and memory_bytes < size:
        raise SnapshotMismatch(
            f"memory_bytes is {memory_bytes:,}, below the snapshot's image of {size:,} bytes; "
            "pass at least that, or None"
        )
    return "snapshot", _start_of(snapshot)


def _start_of(snap: Snapshot) -> _Start:
    o = snap._origin
    return _Start(snap._image, o.home, o.image_sha256, (o.snapshot_sha256, o.stdlib_zip_sha256))


def _same_set(
    start: _Start | None, found: Artifacts, checked: _artifacts._Checked | None
) -> _artifacts._Checked | None:
    """The digests a call holds its set's bytes to. A call from the set alone keeps what it has.
    A call from an image, or a making, takes the snapshot binary's and the zip's digests, those
    the found set's check took or, for a set passed, its own now, which the call then holds the
    bytes it compiles and copies to; an image's must be the origin's."""
    if start is None:
        return checked
    if checked is None:
        snap, zipped = _artifacts._digest(found.snapshot), _artifacts._digest(found.stdlib_zip)
        checked = _artifacts._Checked(snap, zipped)
    if start.digests is not None and start.digests != (checked.binary, checked.zip):
        which, want, got = (
            ("snapshot binary", start.digests[0], checked.binary)
            if start.digests[0] != checked.binary
            else ("stdlib zip", start.digests[1], checked.zip)
        )
        raise SnapshotMismatch(
            f"this snapshot was made for the artifact set whose {which} is {want[:12]}…, and "
            f"this call runs {got[:12]}… (wasi-python {_version()}); make it again with this set"
        )
    return checked


def _refuse_unprepared(start: _Start | None, binary: Path, exports: set[str]) -> None:
    """A making needs the `prepare` export, which sets before snapshots lack."""
    if start is MAKING and "prepare" not in exports:
        raise ArtifactsMissing(
            f"{binary} does not export prepare: this artifact set predates snapshots you make; "
            "use a set built with them"
        )


# ---------------------------------------------------------------------------------------------
# The capture and the restore, through wasmtime-py's public pointer to linear memory.


def _memory_image(store: Any, memory: Any) -> bytes:
    """Linear memory, whole, in one copy into `bytes`."""
    return ctypes.string_at(memory.data_ptr(store), memory.data_len(store))


def _restore(store: Any, instance: Any, image: bytes) -> None:
    """The image copied into a fresh instance before any of its code runs: its memory grown to
    the image's pages, then the image written over it whole, one copy from the `bytes`. An image
    shorter than the instance's memory would leave the binary's own bytes above it, and one past
    the store's limit is refused before any byte is copied."""
    import wasmtime

    memory = instance.exports(store)["memory"]
    pages, have = len(image) // PAGE, memory.size(store)
    if len(image) % PAGE or pages < have:
        raise SnapshotMismatch(
            f"the image of {len(image):,} bytes is shorter than this instance's memory of "
            f"{have * PAGE:,}: it was not made from this snapshot binary"
        )
    if pages > have:
        try:
            memory.grow(store, pages - have)
        except wasmtime.WasmtimeError:
            raise SnapshotMismatch(
                f"this call's memory limit is below the image of {len(image):,} bytes"
            ) from None
    target = memory.data_ptr(store)  # after the grow, which may move the memory
    if memory.data_len(store) != len(image):
        raise SnapshotMismatch("the instance's memory did not grow to the image's size")
    ctypes.memmove(target, image, len(image))
    p = process()
    with p.cache_lock:
        p.counts["snapshots_restored"] += 1
