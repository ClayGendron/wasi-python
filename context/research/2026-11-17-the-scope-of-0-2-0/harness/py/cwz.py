import sys, zstandard, time, glob, os
for f in sorted(glob.glob(os.path.expanduser("~/.cache/wasi_python/*.cwasm"))):
    b = open(f, "rb").read()
    for lvl in (3, 19):
        t = time.perf_counter(); c = zstandard.ZstdCompressor(level=lvl, threads=-1).compress(b); ct = time.perf_counter() - t
        t = time.perf_counter(); zstandard.ZstdDecompressor().decompress(c); dt = time.perf_counter() - t
        print(os.path.basename(f)[:12], len(b), f"zstd{lvl}", len(c), "compress_s", round(ct, 1), "decompress_s", round(dt, 2), flush=True)
