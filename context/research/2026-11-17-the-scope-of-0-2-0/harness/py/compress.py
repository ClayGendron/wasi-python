import sys, time, gzip, lzma, pathlib, zstandard
d = pathlib.Path(sys.argv[1])
for name in ["python.wasm", "python-snapshot.wasm", "python-stdlib.zip"]:
    b = (d / name).read_bytes()
    row = [name, len(b)]
    for label, comp, decomp in [
        ("gzip9", lambda x: gzip.compress(x, 9), gzip.decompress),
        ("zstd19", lambda x: zstandard.ZstdCompressor(level=19, threads=-1).compress(x), lambda x: zstandard.ZstdDecompressor().decompress(x)),
        ("xz9", lambda x: lzma.compress(x, preset=9), lzma.decompress),
    ]:
        c = comp(b)
        t = time.perf_counter(); decomp(c); dt = time.perf_counter() - t
        row += [label, len(c), round(dt, 2)]
    print(*row, flush=True)
