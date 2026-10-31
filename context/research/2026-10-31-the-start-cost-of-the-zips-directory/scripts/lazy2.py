# Guest prototype, the shape recommended: zipimport's own plain dict, each folder's run of the
# directory added on first use, by three triggers (a new importer with that prefix, get_data, an
# explicit ensure), and a re-read after invalidate_caches loads what was loaded before.
import _io, _struct, zipimport, sys
P = '/usr/local/lib/python315.zip'
_path_join = zipimport._bootstrap_external._path_join
_TAIL = 0xFFFF + 22 + 56 + 20
_END = _struct.Struct("<4s4xH2xIIH")
_ENTRY = _struct.Struct("<4s4xHHHHIIIHHH8xI")
_SIZES = _struct.Struct("<HHH")
_pending = {}   # archive -> {folder: (offset, size, count, init offset, init size)}
_where = {}     # archive -> (directory's start in the file, archive offset)
_loaded = {}    # archive -> folders loaded, kept across invalidate_caches

def _parse(archive, cd, arc_offset, a, b, files):
    head = _path_join(archive, "x")[:-1]
    unpack = _ENTRY.unpack_from
    p = a
    while p < b:
        (sig, flags, compress, time, date, crc, data_size, file_size, name_size, extra_size,
         comment_size, file_offset) = unpack(cd, p)
        name_at = p + 46
        p = name_at + name_size + extra_size + comment_size
        raw = cd[name_at : name_at + name_size]
        name = raw.decode() if flags & 0x800 else raw.decode("ascii")
        files[name] = (head + name, compress, data_size, file_size, file_offset + arc_offset,
                       time, date, crc)

def _implied(files, names):
    for name in names:
        while True:
            i = name.rstrip("/").rfind("/")
            if i < 0:
                break
            name = name[: i + 1]
            if name in files:
                break
            files[name] = None

def lazy_read(archive):
    with _io.open_code(archive) as fp:
        size = fp.seek(0, 2)
        fp.seek(max(size - _TAIL, 0))
        tail = fp.read(_TAIL)
        pos = tail.rfind(b"PK\x05\x06")
        _, count, cd_size, cd_offset, clen = _END.unpack_from(tail, pos)
        lines = tail[pos + 22 : pos + 22 + clen].split(b"\n")
        cd_at = size - len(tail) + pos - cd_size
        fp.seek(cd_at)
        cd = fp.read(cd_size)
    arc = cd_at - cd_offset
    segs = {}
    if lines[0] == b"wasi-python-segments 1":
        for line in lines[1:]:
            t, *v = line.split()
            segs[t.decode()] = tuple(map(int, v))
    files = {}
    p = 0
    for top, (off, sz, n, io, isz) in segs.items():   # the table is in the directory's order
        _parse(archive, cd, arc, p, off, files)
        files[top + "/"] = None                      # the folder, so `in` finds a namespace package
        if isz:
            _parse(archive, cd, arc, io, io + isz, files)
        p = off + sz
    _parse(archive, cd, arc, p, cd_size, files)
    _implied(files, list(files))
    _pending[archive] = segs
    _where[archive] = (cd_at, arc)
    for top in _loaded.get(archive, ()):
        load(archive, top, files)
    return files

def load(archive, top, files=None):
    segs = _pending.get(archive)
    seg = segs.pop(top, None) if segs else None
    if seg is None:
        return
    if files is None:
        files = zipimport._zip_directory_cache[archive]
    off, sz, n, io, isz = seg
    cd_at, arc = _where[archive]
    with _io.open_code(archive) as fp:
        fp.seek(cd_at + off)
        cd = fp.read(sz)
    new = {}
    _parse(archive, cd, arc, 0, sz, new)
    if isz:
        del files[top + "/__init__.pyc"]  # re-added below, in the directory's order
    files.update(new)
    _implied(files, list(new))
    _loaded.setdefault(archive, set()).add(top)

def load_all(archive=P):
    for top in list(_pending.get(archive, ())):
        load(archive, top)

_stock_init = zipimport.zipimporter.__init__
_stock_get_data = zipimport.zipimporter.get_data
def _init(self, path):
    _stock_init(self, path)
    if self.prefix and _pending.get(self.archive):
        load(self.archive, self.prefix.split("/", 1)[0])
def _get_data(self, pathname):
    if _pending.get(self.archive):
        key = pathname[len(self.archive) + 1:] if pathname.startswith(self.archive + "/") else pathname
        load(self.archive, key.split("/", 1)[0])
    return _stock_get_data(self, pathname)

def install_lazy():
    zipimport._zip_directory_cache.clear()
    sys.path_importer_cache.clear()
    zipimport._read_directory = lazy_read
    zipimport.zipimporter.__init__ = _init
    zipimport.zipimporter.get_data = _get_data

def install_full():
    import _zip_directory
    zipimport._zip_directory_cache.clear()
    sys.path_importer_cache.clear()
    zipimport._read_directory = _zip_directory.read_directory

def folder_orders(files):
    out = {}
    for name in files:
        if name:
            out.setdefault(name.rstrip("/").rpartition("/")[0], []).append(name)
    return out
