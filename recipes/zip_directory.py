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

The plain reactor reads the stdlib zip by folder (`install(by_folder=True)`). Step 70 writes a
table of the zip's top-level folders into its archive comment: each folder's run of the directory
and the run of its `__init__.*` entries. A start reads the directory once, as above, parsing every
entry outside the runs and, for each folder, only its own name and its `__init__` entries, so
zipimport tells a package from a namespace package as before; the rest is pending, kept with the
dict it belongs to, which stays zipimport's plain dict. A folder loads, with one seek and one read,
on the first of: a zipimporter made inside it (every submodule import makes one), the import of its
package, `get_data` on a path in it, and a lookup in it by the resource reader. Every trigger takes
the dict through the importer's own `_get_files()`, so after `invalidate_caches()` the zip is read
again first, and the re-read loads again every folder loaded before. A load takes the folder's
`__init__` entries out and puts them back with the rest, so each folder's children keep the full
read's order. A table that is absent, of another version or does not fit the directory gives the
full read; a load that finds a wrong count, end or name, or an OSError, replaces the dict's
contents in place with the full read and drops the table. A wrong table never yields a wrong dict.
The snapshot reads the whole directory when it is built, and any other archive is read whole.

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

# What served each archive's last read: "folders", "fast" or "stock".
served = {}

_TAIL = 0xFFFF + 22 + 56 + 20  # zipimport's window: the longest comment and the end records
_END = _struct.Struct("<4s4xH2xIIH")  # signature, entries, directory size and offset, comment
_ENTRY = _struct.Struct("<4s4xHHHHIIIHHH8xI")  # zipimport's 46-byte central header fields
_MAX16 = 0xFFFF
_MAX32 = 0xFFFFFFFF
_TABLE = b"wasi-python folders 1"  # the folder table's first line, version 1

# The one archive read by its folder table (`install`), or None.
tabled = None
# Each archive read by its table: [its dict, the folders still pending (folder -> run), the
# directory's place in the file, the archive offset, the directory's offset, the path head].
_folders = {}
# The folders loaded so far, by archive, in load order; kept across a re-read, which loads them
# again, so importers made before an `invalidate_caches()` still find their members.
_loaded = {}


def _end(fp):
    """(entries, directory size, its offset, its start in the file, the archive offset, the
    comment) from the end record, or None for anything zipimport's reader must answer."""
    size = fp.seek(0, 2)
    fp.seek(max(size - _TAIL, 0))
    tail = fp.read(_TAIL)
    if b"PK\x06\x06" in tail:
        return None  # a Zip64 end record, or bytes that look like one
    pos = tail.rfind(b"PK\x05\x06")
    if pos < 0 or len(tail) - pos < 22:
        return None
    _, count, cd_size, cd_offset, comment_size = _END.unpack_from(tail, pos)
    if count == _MAX16 or cd_size == _MAX32 or cd_offset == _MAX32:
        return None
    header = size - len(tail) + pos
    if header < cd_size or header < cd_offset:
        return None
    header -= cd_size
    arc_offset = header - cd_offset
    if arc_offset < 0:
        return None
    return count, cd_size, cd_offset, header, arc_offset, tail[pos + 22 : pos + 22 + comment_size]


def _entries(files, cd, head, arc_offset, cd_offset, p, stop, count, folder, outside):
    """Parse entries of `cd` from byte `p` into `files`: `count` of them when it is not None,
    else up to byte `stop`. With `folder`, each name must be in it; with `outside`, none may be
    in one of its folders. The byte after the last entry, or None for anything odd."""
    unpack = _ENTRY.unpack_from
    n = 0
    while n != count and p < stop:
        if p + 46 > stop:
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
        if p > stop:
            return None
        raw = cd[name_at : name_at + name_size]
        if flags & 0x800:
            name = raw.decode()
        elif raw.isascii():
            name = raw.decode("ascii")
        else:
            return None  # cp437
        if folder is not None:
            if not name.startswith(folder):
                return None
        elif outside and name.partition("/")[0] in outside and "/" in name:
            return None
        if name and name[-1] != "/":
            path = head + name
        else:
            path = _path_join(head[:-1], name)
        files[name] = (path, compress, data_size, file_size, file_offset + arc_offset, time, date,
                       crc)  # fmt: skip
        n += 1
    if count is not None and n != count:
        return None
    return p


def _implied(files, names):
    """The folders zipimport implies for `names`, by its own loop."""
    for name in names:
        while True:
            i = name.rstrip("/").rfind("/")
            if i < 0:
                break
            name = name[: i + 1]
            if name in files:
                break
            files[name] = None


def _fast(archive):
    """zipimport's dict for a plain zip, or None for anything zipimport's reader must answer."""
    with _io.open_code(archive) as fp:
        start = fp.tell()
        try:
            end = _end(fp)
            if end is None:
                return None
            count, cd_size, cd_offset, header, arc_offset, _ = end
            fp.seek(header)
            cd = fp.read(cd_size)
        finally:
            fp.seek(start)
    if len(cd) != cd_size:
        return None
    head = _path_join(archive, "x")[:-1]
    files = {}
    p = _entries(files, cd, head, arc_offset, cd_offset, 0, cd_size, count, None, None)
    if p != cd_size:
        return None  # fewer entries than declared, more, or bytes zipimport would read on
    _implied(files, list(files))
    return files


def _table(comment, cd_size):
    """The folder table in an archive comment: [(folder, offset, size, count, init offset, init
    count)] in directory order, or None when there is none, of another version, or it is
    malformed or out of order."""
    lines = comment.split(b"\n")
    if len(lines) < 2 or lines[0] != _TABLE or lines[-1] != b"":
        return None
    table = []
    at = 0
    for line in lines[1:-1]:
        fields = line.split(b" ")
        if len(fields) != 6 or not fields[0]:
            return None
        numbers = []
        for field in fields[1:]:
            if not field.isdigit() or (field[:1] == b"0" and len(field) > 1):
                return None
            numbers.append(int(field))
        off, size, count, init_off, init_count = numbers
        if off < at or size == 0 or count == 0 or off + size > cd_size:
            return None  # out of order, overlapping, empty or past the end
        if init_count and not off <= init_off < off + size:
            return None
        if not fields[0].isascii() or b"/" in fields[0]:
            return None
        table.append((fields[0].decode("ascii") + "/", off, size, count, init_off, init_count))
        at = off + size
    return table


def _by_table(archive):
    """zipimport's dict with every tabled folder pending but its own name and its `__init__`
    entries, or None when the archive has no table that fits its directory."""
    with _io.open_code(archive) as fp:
        end = _end(fp)
        if end is None:
            return None
        count, cd_size, cd_offset, header, arc_offset, comment = end
        table = _table(comment, cd_size)
        if table is None:
            return None
        fp.seek(header)
        cd = fp.read(cd_size)
    if len(cd) != cd_size:
        return None
    head = _path_join(archive, "x")[:-1]
    outside = {folder[:-1] for folder, *_ in table}
    if len(outside) != len(table):
        return None  # a folder listed twice
    files = {}
    pending = {}
    p = 0
    total = 0
    for folder, off, size, n, init_off, init_count in table:
        before = len(files)
        p = _entries(files, cd, head, arc_offset, cd_offset, p, off, None, None, outside)
        if p != off:
            return None  # the walk between runs missed this run's start
        total += len(files) - before
        end = off + size
        if _entries({}, cd, head, arc_offset, cd_offset, off, end, 1, folder, None) is None:
            return None  # the run's first entry names another folder
        if folder not in files:
            files[folder] = None
        if init_count:
            init = {}
            at = _entries(init, cd, head, arc_offset, cd_offset, init_off, off + size, init_count,
                          folder + "__init__.", None)  # fmt: skip
            if at is None or len(init) != init_count or any("/" in k[len(folder) :] for k in init):
                return None
            files.update(init)
        pending[folder[:-1]] = (off, size, n)
        total += n
        p = off + size
    before = len(files)
    p = _entries(files, cd, head, arc_offset, cd_offset, p, cd_size, None, None, outside)
    total += len(files) - before
    if p != cd_size or total != count:
        return None  # the counts do not add up
    _implied(files, list(files))
    _folders[archive] = [files, pending, header, arc_offset, cd_offset, head]
    for name in list(_loaded.get(archive, ())):
        off, size, n = pending.pop(name)
        new = {}
        at = _entries(new, cd, head, arc_offset, cd_offset, off, off + size, n, name + "/", None)
        if at != off + size:
            return None
        _merge(files, new)
    return files


def _merge(files, new):
    """A folder's entries into the dict: its `__init__` entries taken out and put back with the
    rest, so the folder's children keep the full read's order."""
    for name in new.keys() & files.keys():
        del files[name]
    files.update(new)
    _implied(files, list(new))


def _fall_back(archive, files):
    """The full read in place of the table's, the dict's contents replaced and the table dropped;
    zipimport's own error, when even that read fails."""
    global tabled
    _folders.pop(archive, None)
    _loaded.pop(archive, None)
    if tabled == archive:
        tabled = None
    full = None
    try:
        full = _fast(archive)
    except Exception:
        full = None
    if full is None:
        served[archive] = "stock"
        full = stock_read_directory(archive)
    else:
        served[archive] = "fast"
    files.clear()
    files.update(full)


def _load(archive, folder, files):
    """Load one pending folder into `files`, the dict the table's read made: one seek, one read."""
    state = _folders.get(archive)
    if state is None or state[0] is not files:
        return
    run = state[1].pop(folder, None)
    if run is None:
        return
    off, size, n = run
    new = {}
    try:
        with _io.open_code(archive) as fp:
            fp.seek(state[2] + off)
            cd = fp.read(size)
        at = None
        if len(cd) == size:
            at = _entries(new, cd, state[5], state[3], state[4], 0, size, n, folder + "/", None)
    except OSError:
        at = None
    if at != size or len(new) != n:
        _fall_back(archive, files)
        return
    _merge(files, new)
    _loaded.setdefault(archive, {})[folder] = None


def touch(importer, at):
    """Load the folder that `at`, a name in the importer's archive, lies in, if it is pending.
    The dict is the importer's own `_get_files()`, so after `invalidate_caches()` the archive
    is read again first."""
    state = _folders.get(importer.archive)
    if state is not None:
        folder = at.partition("/")[0]
        if folder in state[1]:
            _load(importer.archive, folder, importer._get_files())


def load_all(archive):
    """Load every pending folder of the archive."""
    state = _folders.get(archive)
    if state is None:
        return
    for folder in list(state[1]):
        files = zipimport._zip_directory_cache.get(archive)
        if files is None:
            return
        _load(archive, folder, files)


def loaded(archive):
    """The folders of the archive loaded so far, in load order."""
    return list(_loaded.get(archive, ()))


def read_directory(archive):
    """zipimport's `_read_directory(archive)`, read once and unpacked in C; the archive read by
    folder (`install`) by its table, when it has one that fits."""
    if archive == tabled:
        try:
            files = _by_table(archive)
        except Exception:
            files = None
        if files is not None:
            served[archive] = "folders"
            return files
        _folders.pop(archive, None)
    try:
        files = _fast(archive)
    except Exception:
        files = None
    if files is None:
        served[archive] = "stock"
        return stock_read_directory(archive)
    served[archive] = "fast"
    return files


def _resources():
    """The module `_zip_resources`, its lookups loading a pending folder through `touch`."""
    import _zip_resources

    _zip_resources.touch = touch
    return _zip_resources


def get_resource_reader(self, fullname):
    """Return the ResourceReader for a module in a zip file: one on zipimport's own dict."""
    return _resources().ZipDirectoryReader(self, fullname)


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
        _zip_resources = _resources()
        _zip_resources.use_zip_children(metadata.FastPath)
        _zip_children = _zip_resources.zip_children
    return stock_find_distributions(*args, **kwargs)


# zipimporter's own methods, which the triggers below call once the folder is loaded.
stock_init = zipimport.zipimporter.__init__
stock_get_data = zipimport.zipimporter.get_data
stock_exec_module = zipimport.zipimporter.exec_module


def _init(self, path):
    """zipimporter's `__init__`: an importer made inside a folder, as every submodule import
    makes one, loads that folder."""
    stock_init(self, path)
    if self.prefix and self.archive in _folders:
        touch(self, self.prefix)


def _get_data(self, pathname):
    """zipimporter's `get_data`, with the folder the path lies in loaded first."""
    if self.archive in _folders:
        key = pathname
        if pathname.startswith(self.archive + "/"):
            key = pathname[len(self.archive) + 1 :]
        touch(self, key)
    return stock_get_data(self, pathname)


def _exec_module(self, module):
    """zipimporter's `exec_module`: a package imported from the archive's top loads its folder
    before its own code runs, so its `__init__` finds every member beside it."""
    if not self.prefix and self.archive in _folders:
        spec = module.__spec__
        if spec is not None and spec.submodule_search_locations is not None:
            touch(self, module.__name__ + "/")
    return stock_exec_module(self, module)


def install(by_folder=False, archive=None):
    """Put the reader in zipimport's place, the resource reader on zipimporter and the
    metadata search on PathFinder (where zipimport's separator is `/`, as in the guest). With
    `by_folder`, the archive (the stdlib zip, `sys._stdlib_dir`, when None) is read by its folder
    table, and zipimporter loads a folder on its first use."""
    global stock_find_distributions, tabled
    if zipimport.path_sep != "/":
        return
    zipimport._read_directory = read_directory
    zipimport.zipimporter.get_resource_reader = get_resource_reader
    finder = zipimport._bootstrap_external.PathFinder
    if stock_find_distributions is None:
        stock_find_distributions = finder.find_distributions
    finder.find_distributions = staticmethod(find_distributions)
    if by_folder:
        if archive is None:
            import sys

            archive = sys._stdlib_dir
        tabled = archive
        zipimport.zipimporter.__init__ = _init
        zipimport.zipimporter.get_data = _get_data
        zipimport.zipimporter.exec_module = _exec_module
