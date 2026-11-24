import sys, json, zlib, wasi_python as wp
from wasi_python import _snapshot as s
for name, pk in [("pandas", ["pandas"]), ("all", None)]:
    snap = wp.make_package_snapshot(pk)
    p = f"{name}.wpsnap"; snap.save(p)
    o = snap.origin
    open(f"{name}.img", "wb").write(snap._image)
    print(name, json.dumps({k: getattr(o, k) for k in ("kind","home","guest_paths","env_names","image_bytes")}, default=list))
