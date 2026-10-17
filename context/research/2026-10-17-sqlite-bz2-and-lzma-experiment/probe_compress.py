"""Guest probe: bz2 and lzma round trips, files, tarfile and zipfile. Prints only deterministic lines,
so the guest's output can be compared with native CPython's. WORK names a writable directory."""

import bz2
import hashlib
import io
import lzma
import os
import shutil
import tarfile
import zipfile

W = os.environ.get("WORK", "/work")
os.makedirs(W, exist_ok=True)


def h(b):
    return hashlib.sha256(b).hexdigest()[:16]


data = (b"wasi_python sealed portable " * 4000) + bytes(range(256)) * 64
print("data", len(data), h(data))

for level in (1, 9):
    c = bz2.compress(data, level)
    print("bz2", level, len(c), h(c), bz2.decompress(c) == data)
d = bz2.BZ2Decompressor()
c = bz2.compress(data)
out = b"".join(d.decompress(c[i : i + 1000]) for i in range(0, len(c), 1000))
print("bz2 incremental", out == data, d.eof)

for fmt, name in ((lzma.FORMAT_XZ, "xz"), (lzma.FORMAT_ALONE, "alone")):
    for preset in (0, 6, 9 | lzma.PRESET_EXTREME):
        c = lzma.compress(data, format=fmt, preset=preset)
        print("lzma", name, preset, len(c), lzma.decompress(c) == data)
for check in ("CHECK_NONE", "CHECK_CRC32", "CHECK_CRC64", "CHECK_SHA256"):
    cid = getattr(lzma, check)
    c = lzma.compress(data, check=cid)
    print("lzma check", check, lzma.is_check_supported(cid), len(c), lzma.decompress(c) == data)
raw = [{"id": lzma.FILTER_DELTA, "dist": 4}, {"id": lzma.FILTER_LZMA2, "preset": 6}]
c = lzma.compress(data, format=lzma.FORMAT_RAW, filters=raw)
print("lzma raw delta+lzma2", len(c), lzma.decompress(c, format=lzma.FORMAT_RAW, filters=raw) == data)
for bcj in ("FILTER_X86", "FILTER_ARM", "FILTER_ARM64", "FILTER_RISCV"):
    if hasattr(lzma, bcj):
        f = [{"id": getattr(lzma, bcj)}, {"id": lzma.FILTER_LZMA2}]
        c = lzma.compress(data, filters=f)
        print("lzma bcj", bcj, lzma.decompress(c) == data)

with bz2.open(f"{W}/a.txt.bz2", "wt", encoding="utf-8") as f:
    f.write("line\n" * 1000)
with bz2.open(f"{W}/a.txt.bz2", "rt", encoding="utf-8") as f:
    print("bz2 file", len(f.read()), os.path.getsize(f"{W}/a.txt.bz2"))
with lzma.open(f"{W}/a.txt.xz", "wt", encoding="utf-8") as f:
    f.write("line\n" * 1000)
with lzma.open(f"{W}/a.txt.xz", "rt", encoding="utf-8") as f:
    print("xz file", len(f.read()), os.path.getsize(f"{W}/a.txt.xz"))

src = f"{W}/tree"
os.makedirs(f"{src}/sub", exist_ok=True)
for i in range(5):
    with open(f"{src}/sub/f{i}.txt", "wb") as f:
        f.write(data[i * 1000 : (i + 1) * 5000])
for mode in ("bz2", "xz"):
    path = f"{W}/t.tar.{mode}"
    with tarfile.open(path, f"w:{mode}") as t:
        for i in range(5):
            info = tarfile.TarInfo(f"sub/f{i}.txt")
            payload = data[i * 1000 : (i + 1) * 5000]
            info.size, info.mtime = len(payload), 1767225600
            t.addfile(info, io.BytesIO(payload))
    with tarfile.open(path, f"r:{mode}") as t:
        names = t.getnames()
        body = t.extractfile("sub/f3.txt").read()
    with tarfile.open(path, "r:*") as t:
        auto = len(t.getnames())
    print("tarfile", mode, names, h(body), auto)
    out = f"{W}/x-{mode}"
    with tarfile.open(path, f"r:{mode}") as t:
        t.extractall(out, filter="data")
    print("tarfile extract", mode, sorted(os.listdir(f"{out}/sub")))

print("archive formats", [n for n, _ in shutil.get_archive_formats()])
print("unpack formats", [n for n, _, _ in shutil.get_unpack_formats()])
base = shutil.make_archive(f"{W}/mk", "xztar", src)
print("make_archive", os.path.basename(base))
for comp, name in ((zipfile.ZIP_BZIP2, "bzip2"), (zipfile.ZIP_LZMA, "lzma")):
    p = f"{W}/z-{name}.zip"
    with zipfile.ZipFile(p, "w", comp) as z:
        z.writestr("d.bin", data)
    with zipfile.ZipFile(p) as z:
        print("zipfile", name, z.read("d.bin") == data, z.testzip())
print("done")
