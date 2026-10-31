# Guest prototype: zipimport's dict with each package folder's members read on first use.
import _io, _struct, zipimport, sys
P = '/usr/local/lib/python315.zip'
_path_join = zipimport._bootstrap_external._path_join
_TAIL = 0xFFFF + 22 + 56 + 20
_END = _struct.Struct("<4s4xH2xIIH")
_ENTRY = _struct.Struct("<4s4xHHHHIIIHHH8xI")

def _parse(archive, cd, arc_offset, count, files, p=0):
    head = _path_join(archive, "x")[:-1]
    unpack = _ENTRY.unpack_from
    for _ in range(count):
        (sig, flags, compress, time, date, crc, data_size, file_size, name_size, extra_size,
         comment_size, file_offset) = unpack(cd, p)
        name_at = p + 46
        p = name_at + name_size + extra_size + comment_size
        raw = cd[name_at : name_at + name_size]
        name = raw.decode() if flags & 0x800 else raw.decode("ascii")
        path = head + name if name and name[-1] != "/" else _path_join(archive, name)
        files[name] = (path, compress, data_size, file_size, file_offset + arc_offset, time, date, crc)

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

class LazyFiles(dict):
    """zipimport's dict, less the members of folders not yet asked for."""
    def __missing__(self, key):
        i = key.find("/")
        if i > 0 and self.load(key[:i]):
            return dict.__getitem__(self, key)
        raise KeyError(key)

    def load(self, top):
        seg = self._segs.pop(top, None)
        if seg is None:
            return False
        off, size, count = seg[0], seg[1], seg[2]
        with _io.open_code(self._archive) as fp:
            fp.seek(self._cd_at + off)
            cd = fp.read(size)
        new = {}
        _parse(self._archive, cd, self._arc_offset, count, new)
        self.update(new)
        _implied(self, list(new))
        return True

    def load_all(self):
        for top in list(self._segs):
            self.load(top)

def lazy_read(archive):
    with _io.open_code(archive) as fp:
        size = fp.seek(0, 2)
        fp.seek(max(size - _TAIL, 0))
        tail = fp.read(_TAIL)
        pos = tail.rfind(b"PK\x05\x06")
        _, count, cd_size, cd_offset, clen = _END.unpack_from(tail, pos)
        comment = tail[pos + 22 : pos + 22 + clen]
        cd_at = size - len(tail) + pos - cd_size
        arc_offset = cd_at - cd_offset
        segs = {}
        lines = comment.split(b"\n")
        if lines[0] == b"wasi-python-segments 1":
            for line in lines[1:]:
                t, *v = line.split()
                segs[t.decode()] = [int(x) for x in v]
        # the directory less the folders' runs: read whole, skip each run by its offset
        fp.seek(cd_at)
        cd = fp.read(cd_size)
    files = LazyFiles()
    files._segs = segs; files._archive = archive; files._cd_at = cd_at; files._arc_offset = arc_offset
    runs = sorted((v[0], v[1], v[2], v[3], v[4], t) for t, v in segs.items())
    p = 0
    for off, size, n, init_off, init_size, top in runs:
        _parse(archive, cd[p:off], arc_offset, _count(cd, p, off), files)
        if init_size:
            _parse(archive, cd, arc_offset, 1, files, init_off)
        p = off + size
    _parse(archive, cd[p:], arc_offset, _count(cd, p, cd_size), files)
    _implied(files, list(files))
    return files

def _count(cd, a, b):
    # entries in cd[a:b]: walked by their sizes (the prototype's; a table would carry it)
    n = 0
    while a < b:
        ns, es, cs = _struct.unpack_from("<HHH", cd, a + 28)
        a += 46 + ns + es + cs; n += 1
    return n

_stock_init = zipimport.zipimporter.__init__
def _init(self, path):
    _stock_init(self, path)
    if self.prefix:
        files = zipimport._zip_directory_cache.get(self.archive)
        if type(files) is LazyFiles:
            files.load(self.prefix.split("/", 1)[0])

def install_lazy():
    zipimport._zip_directory_cache.clear()
    sys.path_importer_cache.clear()
    zipimport._read_directory = lazy_read
    zipimport.zipimporter.__init__ = _init

def install_full():
    import _zip_directory
    zipimport._zip_directory_cache.clear()
    sys.path_importer_cache.clear()
    zipimport._read_directory = _zip_directory.read_directory

class Counting(dict):
    n_in = 0; n_get = 0
    def __contains__(self, k):
        Counting.n_in += 1
        return dict.__contains__(self, k)
    def __getitem__(self, k):
        Counting.n_get += 1
        return dict.__getitem__(self, k)

def install_counting():
    import _zip_directory
    zipimport._zip_directory_cache.clear()
    sys.path_importer_cache.clear()
    zipimport._read_directory = lambda a: Counting(_zip_directory._fast(a))
