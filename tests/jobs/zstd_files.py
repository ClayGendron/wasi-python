"""Golden job: compression.zstd, and tarfile's, zipfile's and shutil's zstd formats.
Usage: zstd_files.py <data dir> <out dir>.

Each output is round-tripped, and its length and SHA-256 are printed, so the compressed bytes
themselves must equal native's. libzstd's version comes first: a different library would change
every hash, and the first line then says why. Working files go in the data directory; the output
directory stays empty, because every file there is compared byte for byte."""

import hashlib
import io
import os
import shutil
import sys
import tarfile
import zipfile

from compression import zstd

data_dir, out_dir = sys.argv[1], sys.argv[2]
print(f"versions python={sys.version_info[0]}.{sys.version_info[1]}")
print("libzstd", ".".join(map(str, zstd.zstd_version_info)))


def show(name, blob, original):
    print(name, len(blob), hashlib.sha256(blob).hexdigest()[:32], "round-trip", original)


with open(os.path.join(data_dir, "sales.csv"), "rb") as fh:
    csv = fh.read()
# Text that compresses well, then bytes that do not (a hash chain), so both paths of the coder run.
noise = b"".join(hashlib.sha256(i.to_bytes(4, "little")).digest() for i in range(2048))
payload = csv * 40 + bytes(range(256)) * 32 + noise
print("payload", len(payload), hashlib.sha256(payload).hexdigest()[:32])

# One frame at a fast, the default and a strong level.
for level in (1, 3, 19):
    blob = zstd.compress(payload, level=level)
    show(f"zstd level {level}", blob, zstd.decompress(blob) == payload)

# A dictionary trained on fixed samples (the CSV's rows, each numbered), and a frame written with
# it. Training runs on one thread, so its result is fixed by the samples.
rows = csv.splitlines()
samples = [b"%d," % i + rows[1 + i % (len(rows) - 1)] * (1 + i % 3) for i in range(400)]
d = zstd.train_dict(samples, 2048)
print("dict", d.dict_id, len(d.dict_content), hashlib.sha256(d.dict_content).hexdigest()[:32])
sample = b"\n".join(samples[:20])
blob = zstd.compress(sample, level=3, zstd_dict=d)
show("zstd with dict", blob, zstd.decompress(blob, zstd_dict=d) == sample)

# A stream written in 4 KiB pieces through ZstdFile, then read back in pieces.
buf = io.BytesIO()
with zstd.ZstdFile(buf, "w", level=5) as f:
    for i in range(0, len(payload), 4096):
        f.write(payload[i : i + 4096])
blob = buf.getvalue()
with zstd.ZstdFile(io.BytesIO(blob)) as f:
    back = b"".join(iter(lambda: f.read(1000), b""))
show("zstd file level 5", blob, back == payload)

# A tar archive with fixed metadata, written to a file, read back and extracted.
members = {"a/sales.csv": csv, "a/b/noise.bin": noise, "a/empty.txt": b""}
path = os.path.join(data_dir, "archive.tar.zst")
with tarfile.open(path, "w:zst") as tar:
    for name, content in members.items():
        info = tarfile.TarInfo(name)
        info.size, info.mtime, info.mode = len(content), 1767225600, 0o644
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        tar.addfile(info, io.BytesIO(content))
with open(path, "rb") as fh:
    blob = fh.read()
target = os.path.join(data_dir, "extract-zst")
with tarfile.open(path, "r:*") as tar:
    names = tar.getnames()
    tar.extractall(target, filter="data")
same = all(
    open(os.path.join(target, name), "rb").read() == content for name, content in members.items()
)
show("tar.zst", blob, same and names == list(members))
shutil.rmtree(target)
os.remove(path)

# A zip member compressed with Zstandard, with a fixed date.
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as z:
    info = zipfile.ZipInfo("zstd.bin", date_time=(2026, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_ZSTANDARD
    z.writestr(info, payload)
with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as z:
    same = z.read("zstd.bin") == payload
show("zip zstandard", buf.getvalue(), same)

# shutil registers its zstd tar format once compression.zstd imports.
print("shutil zstdtar", "zstdtar" in [name for name, _ in shutil.get_archive_formats()])
