"""Resources and metadata from the zip's directory: the frozen module `_zip_resources` (spec 035).

`_zip_directory.install()` makes `zipimporter.get_resource_reader` return a `ZipDirectoryReader`,
and importlib.metadata's zip search use `zip_children` below. Both answer names from the dict
zipimport already holds for the archive (`loader._get_files()`), so neither parses the zip again,
where upstream builds a `zipfile.Path`, which parses the whole directory, on every resource read
and on the first metadata query.

`ZipDirectoryPath` is `zipfile.Path`'s `Traversable` with zipimport's dict as its name set: the same
`is_dir`, `exists`, `is_file`, `joinpath`, `name`, `parent`, `str` and `open` (Decision 6). Its
bytes come from a strict, bounded member reader: a stored or deflated member of at most 1 MiB whose
local header, size and CRC-32 all agree with the directory. Any other member, any failed test and
any error is opened by upstream's `zipfile.Path`, with its checks, its streaming and its errors.

`ZipDirectoryPath` satisfies the `Traversable` protocol (a runtime-checkable one) as `zipfile.Path`
does, without subclassing it, and `ZipDirectoryReader` is made on first use: importing
`importlib.resources.abc` runs `importlib.resources` and `tempfile`, about 20 M fuel on the
snapshot, which a metadata query does not otherwise pay. A resource read has imported it already.

It is loaded on first use, through the frozen importer, and compiled at build time by step 60.
"""

import io
import os
import pathlib
import posixpath
import sys
import zipimport
import zlib

LIMIT = 1 << 20  # the largest member, either size, the fast path reads
_LOCAL = b"PK\x03\x04"

# importlib.metadata's own zip search, for every root that is not a zip on the import path; set
# by `use_zip_children` when it puts ours in its place.
stock_zip_children = None

# The children map of each archive, kept with the dict it was built from and that dict's length,
# since loading a folder grows the same dict: archive -> (dict, length, map).
_maps = {}


def touch(loader, at):
    """Load the folder of the loader's archive that `at` lies in, when the archive is read by
    folder: `_zip_directory.touch`, which `_zip_directory` puts here when it loads this module."""


def _files(loader, at):
    """zipimport's dict for the loader's archive, with the folder `at` names loaded."""
    touch(loader, at)
    return loader._get_files()


def _read_member(archive, at, toc):
    """The member's bytes, or None when the fast path must not serve it."""
    _, compress, data_size, file_size, offset, _, _, crc = toc
    if compress not in (0, 8) or data_size > LIMIT or file_size > LIMIT:
        return None
    with io.open_code(archive) as fp:
        fp.seek(offset)
        local = fp.read(30)
        if len(local) != 30 or local[:4] != _LOCAL:
            return None
        flags = int.from_bytes(local[6:8], "little")
        method = int.from_bytes(local[8:10], "little")
        name_size = int.from_bytes(local[26:28], "little")
        extra_size = int.from_bytes(local[28:30], "little")
        if flags & 0x1 or method != compress:
            return None
        if fp.read(name_size) != at.encode("utf-8"):
            return None
        fp.seek(extra_size, 1)
        raw = fp.read(data_size)
    if len(raw) != data_size:
        return None
    if compress == 8:
        inflate = zlib.decompressobj(-15)
        data = inflate.decompress(raw, file_size + 1)
        if not inflate.eof:
            return None
    else:
        data = raw
    if len(data) != file_size or zlib.crc32(data) != crc:
        return None
    return data


def _text_args(encoding=None, *args, **kwargs):
    return io.text_encoding(encoding, 3), args, kwargs


def _children(loader, files):
    """Each folder's children, in the dict's order, built in one pass and kept with the dict."""
    kept = _maps.get(loader.archive)
    if kept is not None and kept[0] is files and kept[1] == len(files):
        return kept[2]
    children = {}
    for name in files:
        if name:
            children.setdefault(posixpath.dirname(name.rstrip("/")), []).append(name)
    _maps[loader.archive] = (files, len(files), children)
    return children


class ZipDirectoryPath:
    """A name in a zip on the import path, answered from zipimport's dict for the archive."""

    def __init__(self, loader, at=""):
        self._loader = loader
        self._at = at

    def __repr__(self):
        return f"{type(self).__name__}({self._loader.archive!r}, {self._at!r})"

    def __str__(self):
        return posixpath.join(self._loader.archive, self._at)

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return (self._loader.archive, self._at) == (other._loader.archive, other._at)

    def __hash__(self):
        return hash((self._loader.archive, self._at))

    def _next(self, at):
        return type(self)(self._loader, at)

    def _base(self):
        return pathlib.PurePosixPath(self._at or self._loader.archive)

    @property
    def name(self):
        return self._base().name

    @property
    def suffix(self):
        return self._base().suffix

    @property
    def suffixes(self):
        return self._base().suffixes

    @property
    def stem(self):
        return self._base().stem

    @property
    def parent(self):
        if not self._at:
            return pathlib.Path(self._loader.archive).parent
        at = posixpath.dirname(self._at.rstrip("/"))
        return self._next(at + "/" if at else at)

    def is_dir(self):
        return not self._at or self._at.endswith("/")

    def exists(self):
        return self._at in _files(self._loader, self._at)

    def is_file(self):
        return self.exists() and not self.is_dir()

    def joinpath(self, *other):
        name = posixpath.join(self._at, *map(os.fspath, other))
        files = _files(self._loader, name)
        if name not in files and name + "/" in files:
            name += "/"
        return self._next(name)

    __truediv__ = joinpath

    def iterdir(self):
        if not self.is_dir():
            raise ValueError("Can't listdir a file")
        files = _files(self._loader, self._at)
        names = _children(self._loader, files).get(self._at.rstrip("/"), ())
        return iter([self._next(name) for name in names])

    def open(self, mode="r", *args, pwd=None, **kwargs):
        if self.is_dir():
            raise IsADirectoryError(self)
        if mode[0] != "r":
            if mode[0] == "w":
                raise ValueError("write() requires mode 'w', 'x', or 'a'")
            raise ValueError('open() requires mode "r" or "w"')
        toc = _files(self._loader, self._at).get(self._at)
        if toc is None:
            raise FileNotFoundError(self)
        data = None
        if pwd is None:  # a password, as zipfile.Path.open takes it, is zipfile's to use
            try:
                data = _read_member(self._loader.archive, self._at, toc)
            except Exception:
                data = None
        if data is None:
            import zipfile

            path = zipfile.Path(self._loader.archive, self._at)
            return path.open(mode, *args, pwd=pwd, **kwargs)
        if "b" in mode:
            if args or kwargs:
                raise ValueError("encoding args invalid for binary operation")
            return io.BytesIO(data)
        encoding, args, kwargs = _text_args(*args, **kwargs)
        return io.TextIOWrapper(io.BytesIO(data), encoding, *args, **kwargs)

    def read_bytes(self):
        with self.open("rb") as strm:
            return strm.read()

    def read_text(self, encoding=None, errors=None):
        with self.open(encoding=encoding, errors=errors) as strm:
            return strm.read()


def _make_reader():
    from importlib.resources.abc import TraversableResources

    class ZipDirectoryReader(TraversableResources):
        """`importlib.resources`' reader for a module in a zip: `ZipReader`'s root, our path."""

        def __init__(self, loader, module):
            self.prefix = loader.prefix.replace("\\", "/")
            if loader.is_package(module):
                self.prefix += module.rpartition(".")[2] + "/"
            self.archive = loader.archive
            self._loader = loader

        def is_resource(self, path):
            target = self.files().joinpath(path)
            return target.is_file() and target.exists()

        def files(self):
            return ZipDirectoryPath(self._loader, self.prefix)

    ZipDirectoryReader.__qualname__ = "ZipDirectoryReader"
    return ZipDirectoryReader


def __getattr__(name):
    """`ZipDirectoryReader`, made and kept on first use."""
    if name != "ZipDirectoryReader":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    reader = globals()["ZipDirectoryReader"] = _make_reader()
    return reader


def zip_children(self):
    """`FastPath.zip_children` for a zip on the import path, from zipimport's dict: upstream's own
    expression over its names, in upstream's order."""
    loader = sys.path_importer_cache.get(self.root)
    if isinstance(loader, zipimport.zipimporter) and not loader.prefix:
        self.joinpath = ZipDirectoryPath(loader).joinpath
        return dict.fromkeys(name.split("/", 1)[0] for name in loader._get_files())
    return stock_zip_children(self)


def use_zip_children(fast_path):
    """Put `zip_children` in `FastPath`'s place, keeping its own for every other root."""
    global stock_zip_children
    if fast_path.zip_children is not zip_children:
        stock_zip_children = fast_path.zip_children
        fast_path.zip_children = zip_children
