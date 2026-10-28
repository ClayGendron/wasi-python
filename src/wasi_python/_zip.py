"""The private copy of the stdlib zip and matplotlib's data: the zip folders, the member
extraction, the intact check and the removal at exit."""

from __future__ import annotations

import io
import os
import shutil
import stat
import tempfile
import unicodedata
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path

from . import _artifacts, _platform
from ._artifacts import Artifacts
from ._private_dirs import _Private
from ._process import process

# The zip: one private folder per zip per
# process, beside a lock file. It holds `lib/python3XY.zip`, granted read-only at /usr/local/lib
# on every call (so the guest sees the zip there and nothing else), and `mpl-data/`, matplotlib's
# data extracted from the zip's inner archive, granted read-only at the path matplotlib computes.
# The table, `process().zips`: the zip's SHA-256 -> [its _Private folder, the copy's stamp, the
# data's record or None], under `process().zip_lock`, its own lock since the epoch ticker takes
# the cache lock every round.
MPL_DATA_MEMBER = "matplotlib/mpl-data.zip"  # the inner archive in the stdlib zip
MPL_DATA_GUEST = "matplotlib/mpl-data"  # under the zip's guest path: Path(__file__) there


@dataclass(frozen=True)
class _ZipFolder:
    lib: Path  # granted at /usr/local/lib: the zip alone
    data: Path | None  # matplotlib's data, when the zip carries it
    name: str  # the zip's name, python3XY.zip


def _zip_folder(found: Artifacts, want: str | None = None) -> _ZipFolder:
    # A found set's zip comes with the digest its SHA256SUMS check took: the private copy, the
    # only zip the guest reads, is held to it, so a zip changed after the check never reaches the
    # guest.
    want = want if want is not None else _artifacts._digest(found.stdlib_zip)
    name = f"python{_artifacts._version_tag(found.manifest)}.zip"
    p = process()
    with p.zip_lock:
        entry = p.zips.get(want)
        if entry is None:
            return _zip_folder_locked(found, want, name)
        private, stamp, record = entry
        if not os.path.isdir(private.path) or os.path.islink(private.path):
            # Removed on the host (a temporary-folder cleaner, say): made again, not trusted.
            private.remove()
            del p.zips[want]
            return _zip_folder_locked(found, want, name)
        lib = private.path / "lib"
        dest = lib / name
        try:
            st = os.lstat(dest) if os.path.isdir(lib) and not os.path.islink(lib) else None
        except FileNotFoundError:
            st = None
        if st is None or not stat.S_ISREG(st.st_mode) or _artifacts._stamp(st) != stamp:
            _real_folder(lib)
            entry[1] = _copy_zip(found, dest, want)  # changed on the host: copied again
        data = private.path / "mpl-data"
        if record is not None and not _data_intact(data, record):
            entry[2] = _extract_data(data, dest)  # changed on the host: extracted again
        return _ZipFolder(lib, None if entry[2] is None else data, name)


def _zip_folder_locked(found: Artifacts, want: str, name: str) -> _ZipFolder:
    private = _Private("wasi-python-zip-")
    try:
        lib = private.path / "lib"
        lib.mkdir(mode=0o700)
        stamp = _copy_zip(found, lib / name, want)
        record = _extract_data(private.path / "mpl-data", lib / name)
    except BaseException:
        private.remove()
        raise
    process().zips[want] = [private, stamp, record]
    return _ZipFolder(lib, None if record is None else private.path / "mpl-data", name)


def _zip_known(found: Artifacts) -> Path | None:
    """This process's folder for this zip, if it has made one."""
    with process().zip_lock:
        entry = process().zips.get(_artifacts._digest(found.stdlib_zip))
    return None if entry is None else entry[0].path


def _remove_entry(path: Path) -> None:
    """A real folder removed whole; a file or a link (to a folder too) unlinked, never followed."""
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    else:
        os.unlink(path)


def _real_folder(path: Path) -> None:
    """A real folder at the path: a file or a link there is removed first, never followed."""
    if os.path.islink(path) or (os.path.lexists(path) and not os.path.isdir(path)):
        os.unlink(path)
    if not os.path.isdir(path):
        os.mkdir(path, 0o700)


def _member_parts(name: str) -> tuple[str, ...]:
    """A member's path, refused when it could leave the data folder, or when a component is a
    name Windows rewrites or rejects (a reserved device, a trailing dot or space, a character it
    refuses) or holds a format character (Unicode's category Cf: the zero-width joiners, the
    byte-order mark), which HFS+ drops from a name, on every system: a system would read it as
    another name."""
    parts = tuple(name.rstrip("/").split("/"))
    if (
        not name
        or name.startswith("/")
        or "\\" in name
        or ":" in name
        or any(p in ("", ".", "..") or _platform._rewritten(p) for p in parts)
        or any(unicodedata.category(c) == "Cf" for c in name)
    ):
        raise RuntimeError(f"the stdlib zip's matplotlib data holds the member {name!r}")
    return parts


def _refuse_case_equal(paths: set[tuple[str, ...]]) -> None:
    """Refuse two distinct paths equal under case folding after NFC: a file system that folds
    case or normalises Unicode would write them as one. `paths` holds every member and every
    folder on the way to one, so two folders on the way are compared too."""
    seen: dict[str, str] = {}
    for parts in sorted(paths):
        name = "/".join(parts)
        other = seen.setdefault(unicodedata.normalize("NFC", name).casefold(), name)
        if other != name:
            raise RuntimeError(
                f"the stdlib zip's matplotlib data holds the member {name!r}, which is "
                f"{other!r} under case folding"
            )


def _extract_data(data: Path, zip_copy: Path) -> dict[str, tuple[int, ...] | None] | None:
    """matplotlib's data, made equal to the inner archive in the private copy of the zip (checked
    by its SHA-256 just before): the outer member is read into memory whole, each file written,
    read back once and compared with its CRC-32 and size, and every path recorded with its type
    and stamp. A member that is absolute, holds `..`, holds a name Windows rewrites, equals another
    under case folding, or is a link or anything but a regular file or folder is refused. What the
    folder holds and the archive does not is removed. None, and no folder, when the zip carries no
    data. Windows cannot replace a file a running guest has open: one already right is kept, as
    `_copy_zip` keeps the zip."""
    with zipfile.ZipFile(zip_copy) as outer:
        try:
            inner_bytes = outer.read(MPL_DATA_MEMBER)
        except KeyError:
            if os.path.lexists(data):
                shutil.rmtree(data) if os.path.isdir(data) and not os.path.islink(
                    data
                ) else os.unlink(data)
            return None
    files: dict[tuple[str, ...], zipfile.ZipInfo] = {}
    folders: set[tuple[str, ...]] = set()
    with zipfile.ZipFile(io.BytesIO(inner_bytes)) as inner:
        for info in inner.infolist():
            parts = _member_parts(info.filename)
            kind = stat.S_IFMT(info.external_attr >> 16)  # 0 when the zip records no type
            if info.is_dir():
                folders.add(parts)
            elif kind and kind != stat.S_IFREG:
                raise RuntimeError(
                    f"the stdlib zip's matplotlib data holds {info.filename!r}, not a regular file"
                )
            else:
                files[parts] = info
            folders.update(parts[:k] for k in range(1, len(parts)))
        clash = sorted("/".join(p) for p in folders & set(files))
        if clash:
            raise RuntimeError(f"the stdlib zip's matplotlib data holds {clash[0]!r} twice")
        _refuse_case_equal(folders | set(files))
        _real_folder(data)
        for parts in sorted(folders, key=len):
            _real_folder(data.joinpath(*parts))
        for parts, info in sorted(files.items()):
            _write_member(inner, info, data.joinpath(*parts))
    _remove_extra(data, files, folders)
    return _record(data)


def _write_member(inner: zipfile.ZipFile, info: zipfile.ZipInfo, dest: Path) -> None:
    body = inner.read(info)  # zipfile checks the member's CRC-32 as it reads
    fd, tmp = tempfile.mkstemp(prefix=".mpl-data-", dir=dest.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(body)
        os.chmod(tmp, 0o644)
        with open(tmp, "rb") as back:  # read back once: an accident on the way is caught here
            again = back.read()
        if len(again) != info.file_size or zlib.crc32(again) != info.CRC:
            raise RuntimeError(f"matplotlib's data file {dest} did not read back as written")
        if os.path.islink(dest) or os.path.isdir(dest):
            shutil.rmtree(dest) if os.path.isdir(dest) and not os.path.islink(dest) else os.unlink(
                dest
            )
        try:
            os.replace(tmp, dest)
        except PermissionError:
            if not _platform.PLATFORM.holds_open_files or not _holds(dest, info):
                raise
            Path(tmp).unlink(missing_ok=True)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _holds(path: Path, info: zipfile.ZipInfo) -> bool:
    try:
        with open(path, "rb") as f:
            body = f.read()
    except OSError:
        return False
    return len(body) == info.file_size and zlib.crc32(body) == info.CRC


def _remove_extra(
    data: Path, files: dict[tuple[str, ...], zipfile.ZipInfo], folders: set[tuple[str, ...]]
) -> None:
    """Every entry of the folder that the archive does not hold, removed without following a
    link."""
    for dirpath, dirnames, filenames in os.walk(data, topdown=True, followlinks=False):
        here = Path(dirpath).relative_to(data).parts
        for d in list(dirnames):
            p = Path(dirpath, d)
            if (*here, d) not in folders or os.path.islink(p):
                dirnames.remove(d)
                _remove_entry(p)
        for f in filenames:
            if (*here, f) not in files:
                os.unlink(Path(dirpath, f))


def _record(data: Path) -> dict[str, tuple[int, ...] | None]:
    """Every path under the data folder: None for a folder, the stamp for a file."""
    record: dict[str, tuple[int, ...] | None] = {}
    for dirpath, dirnames, filenames in os.walk(data, followlinks=False):
        here = Path(dirpath).relative_to(data)
        for d in dirnames:
            record[(here / d).as_posix()] = None
        for f in filenames:
            record[(here / f).as_posix()] = _artifacts._stamp(os.lstat(Path(dirpath, f)))
    return record


def _data_intact(data: Path, record: dict[str, tuple[int, ...] | None]) -> bool:
    """Per call, before granting: the whole tree against the record, the same names, each a real
    folder or a regular file as recorded, no link, each file's stamp equal."""
    if os.path.islink(data) or not os.path.isdir(data):
        return False
    # This runs on every call, so each entry costs one lstat of a plain path string and no path
    # object is built. The stamp is taken with os.lstat, as the record's is: a listing entry's
    # own stat does not carry the same device, inode and change time on every system.
    seen: dict[str, tuple[int, ...] | None] = {}
    todo = [(os.fspath(data), "")]
    try:
        while todo:
            folder, here = todo.pop()
            with os.scandir(folder) as listing:
                for entry in listing:
                    st = os.lstat(entry.path)
                    key = f"{here}/{entry.name}" if here else entry.name
                    if stat.S_ISDIR(st.st_mode):
                        seen[key] = None
                        todo.append((entry.path, key))
                    elif stat.S_ISREG(st.st_mode):
                        seen[key] = _artifacts._stamp(st)
                    else:
                        return False  # a link, or anything else
    except OSError:
        return False
    return seen == record


def _copy_zip(found: Artifacts, dest: Path, want: str) -> tuple[int, ...]:
    fd, tmp = tempfile.mkstemp(prefix=".python-zip-", dir=dest.parent)
    try:
        with os.fdopen(fd, "wb") as out, found.stdlib_zip.open("rb") as src:
            for block in iter(lambda: src.read(1 << 20), b""):
                out.write(block)
        # 0644, not read-only: Windows could neither replace nor remove a read-only file, and
        # the guest's grant is read-only anyway, in a 0700 folder.
        os.chmod(tmp, 0o644)
        try:
            os.replace(tmp, dest)
        except PermissionError:
            # Windows cannot replace a file a running guest has open; when the file in place is
            # already the right zip, the copy is not needed.
            if not _platform.PLATFORM.holds_open_files or not (
                dest.is_file() and _artifacts._hash_file(dest) == want
            ):
                raise
            Path(tmp).unlink(missing_ok=True)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    if _artifacts._hash_file(dest) != want:
        raise RuntimeError(f"the stdlib zip's copy at {dest} is not the artifact set's")
    return _artifacts._stamp(os.lstat(dest))


def _remove_zips() -> None:
    p = process()
    with p.zip_lock:
        entries = list(p.zips.values())
        p.zips.clear()
    for private, *_ in entries:
        private.remove()


process().remove_zips = _remove_zips  # the exit release removes this process's zip folders first
