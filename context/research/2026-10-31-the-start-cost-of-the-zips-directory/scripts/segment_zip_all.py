"""Copy a zip and write a segment table into its archive comment (members and offsets unchanged).

    python -I segment_zip.py <in.zip> <out.zip>

A segment is one top-level folder that is not the stdlib's: its run of central-directory entries
(the zip is sorted, so each folder's run is contiguous). A line: `<folder> <offset> <size> <count>
<init offset> <init size>`, offsets relative to the directory's start; init is the folder's
`__init__.pyc` entry, or 0 0."""
import shutil, struct, sys, zipfile
src, dst = sys.argv[1], sys.argv[2]
shutil.copyfile(src, dst)
data = open(dst, "rb").read()
eocd = data.rfind(b"PK\x05\x06")
_, _, _, _, count, cd_size, cd_off, _ = struct.unpack_from("<4sHHHHIIH", data, eocd)
std = set() if len(sys.argv) > 3 else (set(sys.stdlib_module_names) | {"_pyrepl", "profiling", "_colorize", "compression", "annotationlib", "encodings"})
p = cd_off; entries = []
for _ in range(count):
    n, e, c = struct.unpack_from("<HHH", data, p + 28)
    name = data[p + 46 : p + 46 + n].decode()
    entries.append((name, p - cd_off, 46 + n + e + c)); p += 46 + n + e + c
segs = {}
for name, off, size in entries:
    if "/" not in name: continue
    top = name.split("/", 1)[0]
    if top.split(".")[0] in std or ".dist-info" in top: continue
    s = segs.setdefault(top, [off, 0, 0, 0, 0])
    assert s[0] + s[1] == off, top  # contiguous
    s[1] += size; s[2] += 1
    if name == top + "/__init__.pyc": s[3], s[4] = off, size
lines = ["wasi-python-segments 1"] + [f"{t} {' '.join(map(str, v))}" for t, v in segs.items()]
comment = "\n".join(lines).encode()
assert len(comment) < 0xFFFF
out = data[: eocd + 20] + struct.pack("<H", len(comment)) + comment
open(dst, "wb").write(out)
print(len(segs), "segments,", sum(v[2] for v in segs.values()), "lazy members of", count, ";", len(comment), "bytes of comment")
