"""The zip's directory, read once: the frozen module `_zip_directory` (spec 035).

recipes/reactor_main.c imports this module between the interpreter's two start phases, before
anything is read from the stdlib zip, and calls `install()`. From then on zipimport reads every
archive's central directory through `read_directory`, which builds the same dict as zipimport's
own `_read_directory` (the same keys, the same tuples, in the same order) with one read of the
directory and one `_struct` unpack per member, where zipimport makes about a dozen Python calls
per member. Anything outside the plain case goes to zipimport's own reader, kept here as
`stock_read_directory`: Zip64, a cp437 name, any inconsistency, any error. So those zips, and
every error message, are upstream's. It also gives zipimporter a resource reader on that same dict,
and importlib.metadata a search of the zip on it (both in `_zip_resources`, loaded on first use),
so neither a resource read nor a metadata query parses the zip again.

It imports only `_io`, `_struct` and `zipimport` (and, through it, `_frozen_importlib_external`),
which the interpreter's core phase can import. Step 60 compiles it with the guest's own Python
(scripts/freeze_bootstrap.py) and links it into the reactor as a frozen module.
"""

import _io
import _struct
import zipimport

_path_join = zipimport._bootstrap_external._path_join

# zipimport's own reader. `read_directory` looks it up by this name at each call, so a check can
# put a stub in its place.
stock_read_directory = zipimport._read_directory

# What served each archive's last read: "fast" or "stock".
served = {}

_TAIL = 0xFFFF + 22 + 56 + 20  # zipimport's window: the longest comment and the end records
_END = _struct.Struct("<4s4xH2xII")  # signature, entries, directory size, directory offset
_ENTRY = _struct.Struct("<4s4xHHHHIIIHHH8xI")  # zipimport's 46-byte central header fields
_MAX16 = 0xFFFF
_MAX32 = 0xFFFFFFFF


def _fast(archive):
    """zipimport's dict for a plain zip, or None for anything zipimport's reader must answer."""
    with _io.open_code(archive) as fp:
        start = fp.tell()
        try:
            size = fp.seek(0, 2)
            fp.seek(max(size - _TAIL, 0))
            tail = fp.read(_TAIL)
            if b"PK\x06\x06" in tail:
                return None  # a Zip64 end record, or bytes that look like one
            pos = tail.rfind(b"PK\x05\x06")
            if pos < 0 or len(tail) - pos < 22:
                return None
            _, count, cd_size, cd_offset = _END.unpack_from(tail, pos)
            if count == _MAX16 or cd_size == _MAX32 or cd_offset == _MAX32:
                return None
            header = size - len(tail) + pos
            if header < cd_size or header < cd_offset:
                return None
            header -= cd_size
            arc_offset = header - cd_offset
            if arc_offset < 0:
                return None
            fp.seek(header)
            cd = fp.read(cd_size)
        finally:
            fp.seek(start)
    if len(cd) != cd_size:
        return None
    head = _path_join(archive, "x")[:-1]
    unpack = _ENTRY.unpack_from
    files = {}
    p = 0
    for _ in range(count):
        if p + 46 > cd_size:
            return None
        (sig, flags, compress, time, date, crc, data_size, file_size, name_size, extra_size,
         comment_size, file_offset) = unpack(cd, p)  # fmt: skip
        if sig != b"PK\x01\x02":
            return None
        if data_size == _MAX32 or file_size == _MAX32 or file_offset == _MAX32:
            return None  # a Zip64 extra holds the real value
        if file_offset > cd_offset:
            return None
        name_at = p + 46
        p = name_at + name_size + extra_size + comment_size
        if p > cd_size:
            return None
        raw = cd[name_at : name_at + name_size]
        if flags & 0x800:
            name = raw.decode()
        elif raw.isascii():
            name = raw.decode("ascii")
        else:
            return None  # cp437
        if name and name[-1] != "/":
            path = head + name
        else:
            path = _path_join(archive, name)
        files[name] = (path, compress, data_size, file_size, file_offset + arc_offset, time, date,
                       crc)  # fmt: skip
    if p != cd_size:
        return None  # more entries than declared, or bytes zipimport would read on
    for name in list(files):  # the implied directories, by zipimport's own loop
        while True:
            i = name.rstrip("/").rfind("/")
            if i < 0:
                break
            name = name[: i + 1]
            if name in files:
                break
            files[name] = None
    return files


def read_directory(archive):
    """zipimport's `_read_directory(archive)`, read once and unpacked in C."""
    try:
        files = _fast(archive)
    except Exception:
        files = None
    if files is None:
        served[archive] = "stock"
        return stock_read_directory(archive)
    served[archive] = "fast"
    return files


def get_resource_reader(self, fullname):
    """Return the ResourceReader for a module in a zip file: one on zipimport's own dict."""
    from _zip_resources import ZipDirectoryReader

    return ZipDirectoryReader(self, fullname)


# PathFinder's own `find_distributions`, which `find_distributions` below calls.
stock_find_distributions = None
_zip_children = None  # `_zip_resources.zip_children`, once FastPath has it


def find_distributions(*args, **kwargs):
    """PathFinder's `find_distributions`, with importlib.metadata's search of a zip on the
    import path answered from zipimport's dict. It runs only when a program asks for metadata."""
    global _zip_children
    import sys

    metadata = sys.modules.get("importlib.metadata")
    if metadata is None:
        __import__("importlib.metadata")
        metadata = sys.modules["importlib.metadata"]
    if metadata.FastPath.zip_children is not _zip_children:
        import _zip_resources

        _zip_resources.use_zip_children(metadata.FastPath)
        _zip_children = _zip_resources.zip_children
    return stock_find_distributions(*args, **kwargs)


def install():
    """Put the reader in zipimport's place, the resource reader on zipimporter and the
    metadata search on PathFinder (where zipimport's separator is `/`, as in the guest)."""
    global stock_find_distributions
    if zipimport.path_sep != "/":
        return
    zipimport._read_directory = read_directory
    zipimport.zipimporter.get_resource_reader = get_resource_reader
    finder = zipimport._bootstrap_external.PathFinder
    if stock_find_distributions is None:
        stock_find_distributions = finder.find_distributions
    finder.find_distributions = staticmethod(find_distributions)
