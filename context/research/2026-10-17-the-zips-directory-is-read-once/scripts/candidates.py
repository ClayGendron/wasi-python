"""Research prototypes, run inside the guest by guest_candidates.py (exec'd from a -c string).

Our own code, written for this memo to count fuel; not product code. Paths use '/' (WASI's
separator). Nothing here handles Zip64 or cp437 names: today's zip has neither, and the
prototypes fall back or raise where a product version would handle them.

1. read_directory_struct(archive): zipimport's directory as one read of the central directory and
   one struct call per member, with the implied directories added; must equal zipimport's dict.
2. read_directory_from_bytes(archive): the same with int.from_bytes on slices (no struct).
3. IndexReader: an importlib.resources reader for a zipimporter that answers from zipimport's own
   cached directory and reads members through zipimporter.get_data, so a resource read costs
   nothing per member of the zip.
   use_index_metadata(): importlib.metadata's search of a zip on sys.path, on the same directory.
4. cache_zipreader_roots(): ZipReader.files() made to reuse one zipfile.Path root per archive.
"""

import _io
import _struct

_CDH = _struct.Struct("<4s4xHHHHIIIHHH8xI")  # one central-directory header, 46 bytes
_EOCD = _struct.Struct("<4s6xHII")  # signature, entries, directory size, directory offset


def _central_directory(archive):
    with _io.open_code(archive) as fp:
        size = fp.seek(0, 2)
        tail_len = min(size, 0xFFFF + 22)
        fp.seek(size - tail_len)
        tail = fp.read(tail_len)
        pos = tail.rfind(b"PK\x05\x06")
        if pos < 0:
            raise ValueError("not a zip")
        sig, n, cd_size, cd_off = _EOCD.unpack_from(tail, pos)
        header_position = size - tail_len + pos - cd_size
        fp.seek(header_position)
        cd = fp.read(cd_size)
    return n, cd, header_position - cd_off


def _add_implied_dirs(files):
    for name in list(files):
        while True:
            i = name.rfind("/", 0, len(name) - 1)
            if i < 0:
                break
            name = name[: i + 1]
            if name in files:
                break
            files[name] = None
    return files


def read_directory_struct(archive, implied=True):
    n, cd, arc = _central_directory(archive)
    unpack = _CDH.unpack_from
    files = {}
    prefix = archive + "/"
    pos = 0
    for _ in range(n):
        sig, flags, compress, time, date, crc, dsize, fsize, nlen, elen, clen, off = unpack(cd, pos)
        if sig != b"PK\x01\x02":
            raise ValueError("bad central directory")
        start = pos + 46
        raw = cd[start : start + nlen]
        name = raw.decode() if flags & 0x800 else raw.decode("ascii")
        files[name] = (prefix + name, compress, dsize, fsize, off + arc, time, date, crc)
        pos = start + nlen + elen + clen
    return _add_implied_dirs(files) if implied else files


def read_directory_from_bytes(archive):
    n, cd, arc = _central_directory(archive)
    fb = int.from_bytes
    files = {}
    prefix = archive + "/"
    pos = 0
    for _ in range(n):
        if cd[pos : pos + 4] != b"PK\x01\x02":
            raise ValueError("bad central directory")
        flags = fb(cd[pos + 8 : pos + 10], "little")
        nlen = fb(cd[pos + 28 : pos + 30], "little")
        extra = fb(cd[pos + 30 : pos + 32], "little") + fb(cd[pos + 32 : pos + 34], "little")
        raw = cd[pos + 46 : pos + 46 + nlen]
        name = raw.decode() if flags & 0x800 else raw.decode("ascii")
        files[name] = (
            prefix + name,
            fb(cd[pos + 10 : pos + 12], "little"),
            fb(cd[pos + 20 : pos + 24], "little"),
            fb(cd[pos + 24 : pos + 28], "little"),
            fb(cd[pos + 42 : pos + 46], "little") + arc,
            fb(cd[pos + 12 : pos + 14], "little"),
            fb(cd[pos + 14 : pos + 16], "little"),
            fb(cd[pos + 16 : pos + 20], "little"),
        )
        pos += 46 + nlen + extra
    return _add_implied_dirs(files)


# --- 3. a resource reader on zipimport's own directory --------------------------------------

import io as _pyio
import zipimport as _zipimport
from importlib.resources.abc import Traversable as _Traversable
from importlib.resources.abc import TraversableResources as _TraversableResources


class IndexPath(_Traversable):
    def __init__(self, loader, at=""):
        self._loader = loader
        self._at = at  # '' for the archive's root, 'a/b/' for a directory, 'a/b/c' for a file

    def _files(self):
        return self._loader._get_files()  # zipimport's cached dict: name -> toc entry or None

    @property
    def name(self):
        return self._at.rstrip("/").rpartition("/")[2]

    def is_dir(self):
        at = self._at
        return at == "" or (at if at.endswith("/") else at + "/") in self._files()

    def is_file(self):
        return not self._at.endswith("/") and self._files().get(self._at) is not None

    def exists(self):
        return self.is_file() or self.is_dir()

    def joinpath(self, *descendants):
        at = self._at
        if at and not at.endswith("/"):
            at += "/"
        for d in descendants:
            for part in str(d).split("/"):
                if part:
                    at = (at if at.endswith("/") or not at else at + "/") + part
        if at + "/" in self._files():
            at += "/"
        return IndexPath(self._loader, at)

    __truediv__ = joinpath

    def iterdir(self):
        if not self.is_dir():
            raise NotADirectoryError(self._at)
        base = self._at if self._at.endswith("/") or not self._at else self._at + "/"
        for name in self._files():
            if name.startswith(base) and name != base:
                rest = name[len(base) :]
                if "/" not in rest.rstrip("/"):
                    yield IndexPath(self._loader, name)

    def open(self, mode="r", *args, **kwargs):
        if self.is_dir():
            raise IsADirectoryError(self._at)
        if not self.is_file():
            raise FileNotFoundError(self._at)
        data = _pyio.BytesIO(self._loader.get_data(self._loader.archive + "/" + self._at))
        if mode == "rb":
            return data
        if mode == "r":
            return _pyio.TextIOWrapper(data, *args, **kwargs)
        raise ValueError(f"Invalid mode value '{mode}', only 'r' and 'rb' are supported")

    @property
    def parent(self):
        at = self._at.rstrip("/").rpartition("/")[0]
        return IndexPath(self._loader, at + "/" if at else "")

    def __str__(self):
        return self._loader.archive + "/" + self._at

    def __repr__(self):
        return f"IndexPath({str(self)!r})"


class IndexReader(_TraversableResources):
    def __init__(self, loader, module):
        prefix = loader.prefix
        if loader.is_package(module):
            prefix += module.rpartition(".")[2] + "/"
        self._root = IndexPath(loader, prefix)

    def files(self):
        return self._root


def use_index_reader():
    _zipimport.zipimporter.get_resource_reader = lambda self, fullname: IndexReader(self, fullname)


def use_index_metadata():
    """importlib.metadata's zip search answered from zipimport's directory, not zipfile.Path."""
    import importlib.metadata as md
    import sys

    def zip_children(self):
        importer = sys.path_importer_cache.get(self.root)
        if not isinstance(importer, _zipimport.zipimporter) or importer.prefix:
            raise ValueError(self.root)
        root = IndexPath(importer, "")
        self.joinpath = root.joinpath
        return dict.fromkeys(n.split("/", 1)[0] for n in importer._get_files())

    md.FastPath.zip_children = zip_children


# --- 4. ZipReader with one zipfile.Path root per archive ---------------------------------------


def cache_zipreader_roots():
    import zipfile
    from importlib.resources import readers

    roots = {}

    def files(self):
        root = roots.get(self.archive)
        if root is None:
            root = roots[self.archive] = zipfile.Path(self.archive)
        return zipfile.Path(root.root, self.prefix)

    readers.ZipReader.files = files
