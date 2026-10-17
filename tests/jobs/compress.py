"""Golden job: bz2, lzma and tarfile (spec 007). Usage: compress.py <data dir> <out dir>.

Each output is round-tripped, and its length and SHA-256 are printed, so the compressed bytes
themselves must equal native's. Working files go in the data directory; the output directory
stays empty, because every file there is compared byte for byte (jobs.render)."""

import bz2
import hashlib
import io
import lzma
import os
import shutil
import sys
import tarfile
import zipfile

data_dir, out_dir = sys.argv[1], sys.argv[2]
print(f"versions python={sys.version_info[0]}.{sys.version_info[1]}")


def show(name, blob, original):
    print(name, len(blob), hashlib.sha256(blob).hexdigest()[:32], "round-trip", original)


with open(os.path.join(data_dir, "sales.csv"), "rb") as fh:
    csv = fh.read()
# Text that compresses well, then bytes that do not (a hash chain), so both coders' paths run.
noise = b"".join(hashlib.sha256(i.to_bytes(4, "little")).digest() for i in range(2048))
payload = csv * 40 + bytes(range(256)) * 32 + noise
print("payload", len(payload), hashlib.sha256(payload).hexdigest()[:32])

for level in (1, 9):
    blob = bz2.compress(payload, level)
    show(f"bz2 level {level}", blob, bz2.decompress(blob) == payload)
comp = bz2.BZ2Compressor(5)
blob = b"".join(comp.compress(payload[i : i + 4096]) for i in range(0, len(payload), 4096))
blob += comp.flush()
dec = bz2.BZ2Decompressor()
back = b"".join(dec.decompress(blob[i : i + 1000]) for i in range(0, len(blob), 1000))
show("bz2 incremental level 5", blob, back == payload and dec.eof)

blob = lzma.compress(payload)
show("xz preset 6 crc64", blob, lzma.decompress(blob) == payload)
blob = lzma.compress(payload, check=lzma.CHECK_SHA256, preset=9 | lzma.PRESET_EXTREME)
show("xz preset 9e sha256", blob, lzma.decompress(blob) == payload)
blob = lzma.compress(payload, check=lzma.CHECK_NONE, preset=0)
show("xz preset 0 none", blob, lzma.decompress(blob) == payload)
blob = lzma.compress(payload, format=lzma.FORMAT_ALONE)
show("lzma alone", blob, lzma.decompress(blob, format=lzma.FORMAT_ALONE) == payload)
chain = [
    {"id": lzma.FILTER_DELTA, "dist": 4},
    {"id": lzma.FILTER_LZMA2, "preset": 6},
]
blob = lzma.compress(payload, format=lzma.FORMAT_RAW, filters=chain)
show(
    "raw delta+lzma2",
    blob,
    lzma.decompress(blob, format=lzma.FORMAT_RAW, filters=chain) == payload,
)

# tar archives with fixed metadata, written to a file, read back and extracted.
members = {"a/sales.csv": csv, "a/b/noise.bin": noise, "a/empty.txt": b""}
for mode in ("bz2", "xz"):
    path = os.path.join(data_dir, f"archive.tar.{mode}")
    with tarfile.open(path, f"w:{mode}") as tar:
        for name, content in members.items():
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode = len(content), 1767225600, 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            tar.addfile(info, io.BytesIO(content))
    with open(path, "rb") as fh:
        blob = fh.read()
    target = os.path.join(data_dir, f"extract-{mode}")
    with tarfile.open(path, "r:*") as tar:
        names = tar.getnames()
        tar.extractall(target, filter="data")
    same = all(
        open(os.path.join(target, name), "rb").read() == content
        for name, content in members.items()
    )
    show(f"tar.{mode}", blob, same and names == list(members))
    shutil.rmtree(target)
    os.remove(path)

# zip members compressed with bzip2 and LZMA, with a fixed date.
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as z:
    for kind, method in (("bzip2", zipfile.ZIP_BZIP2), ("lzma", zipfile.ZIP_LZMA)):
        info = zipfile.ZipInfo(f"{kind}.bin", date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = method
        z.writestr(info, payload)
with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as z:
    same = all(z.read(n) == payload for n in ("bzip2.bin", "lzma.bin"))
show("zip bzip2+lzma", buf.getvalue(), same)
