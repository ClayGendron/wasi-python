# Guest-side variants of the recipe's reader, each a prefix of its work. Exec'd as a prelude.
import _io, _struct, zipimport, gc, marshal
P = '/usr/local/lib/python315.zip'
_path_join = zipimport._bootstrap_external._path_join
_TAIL = 0xFFFF + 22 + 56 + 20
_END = _struct.Struct("<4s4xH2xII")
_ENTRY = _struct.Struct("<4s4xHHHHIIIHHH8xI")

def cd_bytes(archive):
    with _io.open_code(archive) as fp:
        size = fp.seek(0, 2)
        fp.seek(max(size - _TAIL, 0))
        tail = fp.read(_TAIL)
        pos = tail.rfind(b"PK\x05\x06")
        _, count, cd_size, cd_offset = _END.unpack_from(tail, pos)
        header = size - len(tail) + pos - cd_size
        fp.seek(header)
        return count, fp.read(cd_size), header - cd_offset

def stage(archive, level):
    count, cd, arc_offset = cd_bytes(archive)
    if level == 0:
        return None
    head = _path_join(archive, "x")[:-1]
    unpack = _ENTRY.unpack_from
    files = {}
    p = 0
    for _ in range(count):
        (sig, flags, compress, time, date, crc, data_size, file_size, name_size, extra_size,
         comment_size, file_offset) = unpack(cd, p)
        name_at = p + 46
        p = name_at + name_size + extra_size + comment_size
        if level == 1:
            continue
        raw = cd[name_at : name_at + name_size]
        name = raw.decode() if flags & 0x800 else raw.decode("ascii")
        if level == 2:
            continue
        path = head + name if name and name[-1] != "/" else _path_join(archive, name)
        if level == 3:
            continue
        t = (path, compress, data_size, file_size, file_offset + arc_offset, time, date, crc)
        if level == 4:
            continue
        files[name] = t
    if level == 5:
        return files
    for name in list(files):
        while True:
            i = name.rstrip("/").rfind("/")
            if i < 0:
                break
            name = name[: i + 1]
            if name in files:
                break
            files[name] = None
    return files

def implied_sorted(files):
    # the implied directories in one pass, for names grouped by folder: only a new folder walks up
    last = None
    for name in list(files):
        i = name.rfind("/", 0, len(name) - 1)
        d = name[: i + 1]
        if d == last or i < 0:
            continue
        last = d
        while d and d not in files:
            files[d] = None
            d = d[: d.rfind("/", 0, len(d) - 1) + 1]
    return files
