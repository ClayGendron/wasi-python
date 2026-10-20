"""Bytes of code and data each numpy linalg object contributes to main's python.wasm, from step 60's
link map (build/link/python.map, read only)."""

import re
import sys

tot, n = {}, {}
for line in open(sys.argv[1], errors="replace"):
    m = re.match(r"\s+\S+\s+([0-9a-f]+)\s+([0-9a-f]+)\s+(\S+\.a)\((\S+?\.o)\):\((\S+)\)", line)
    if not m:
        continue
    size = int(m.group(2), 16)
    arch = m.group(3).rsplit("/", 1)[-1]
    obj = m.group(4)
    if arch.startswith(("numpy__umath_linalg", "numpy_lapack_lite", "libopenblas", "libscipy_lapack_shims")):
        key = (arch, obj if not arch.startswith("libopenblas") else "*")
        tot[key] = tot.get(key, 0) + size
        n[key] = n.get(key, 0) + 1
for k in sorted(tot, key=lambda k: -tot[k]):
    print(k, tot[k], n[k])
print("numpy lapack_lite f2c objects, total bytes:", sum(v for k, v in tot.items() if "f2c" in k[1]))
