import sys, zipfile, zstandard, time
src = sys.argv[1]
with zipfile.ZipFile(src) as z:
    infos = z.infolist()
    methods = {}
    for i in infos: methods[i.compress_type] = methods.get(i.compress_type, 0) + 1
    raw = sum(i.file_size for i in infos)
    with zipfile.ZipFile("stored.zip", "w", zipfile.ZIP_STORED) as o:
        for i in infos: o.writestr(i, z.read(i), compress_type=zipfile.ZIP_STORED)
b = open("stored.zip", "rb").read()
c = zstandard.ZstdCompressor(level=19, threads=-1).compress(b)
t = time.perf_counter(); zstandard.ZstdDecompressor().decompress(c); dt = time.perf_counter() - t
print({"entries": len(infos), "methods": methods, "uncompressed_total": raw, "stored_zip_bytes": len(b), "stored_zstd19_bytes": len(c), "decomp_s": round(dt, 2)})
