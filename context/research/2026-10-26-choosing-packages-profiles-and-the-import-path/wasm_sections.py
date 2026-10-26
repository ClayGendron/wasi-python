"""Read python.wasm's sections and, if its name section survived, attribute code size to packages
by function-name prefix. Pure reading; nothing is executed."""
import re, sys
from collections import Counter
from pathlib import Path

data = Path(sys.argv[1]).read_bytes()
assert data[:8] == b"\0asm\1\0\0\0"
pos = 8
def leb(p):
    r = s = 0
    while True:
        b = data[p]; p += 1; r |= (b & 0x7f) << s; s += 7
        if not b & 0x80: return r, p
sections = []
while pos < len(data):
    sid = data[pos]; pos += 1
    size, pos = leb(pos)
    name = ""
    body = pos
    if sid == 0:
        n, q = leb(pos); name = data[q:q+n].decode(); body = q + n
    sections.append((sid, name, size, body, pos + size))
    pos += size
print("total bytes", len(data))
names = {0:"custom",1:"type",2:"import",3:"function",4:"table",5:"memory",6:"global",7:"export",8:"start",9:"elem",10:"code",11:"data",12:"datacount"}
for sid, name, size, body, end in sections:
    print(f"  section {str(names.get(sid, sid)):10s} {name:28s} {size:>12,}")
# The name section: function names.
fn = {}
for sid, name, size, body, end in sections:
    if sid == 0 and name == "name":
        p = body
        while p < end:
            sub = data[p]; p += 1
            n, p = leb(p)
            if sub == 1:
                cnt, q = leb(p)
                for _ in range(cnt):
                    idx, q = leb(q); ln, q = leb(q); fn[idx] = data[q:q+ln].decode(errors="replace"); q += ln
            p += n
print("named functions:", len(fn))
if not fn:
    sys.exit(0)
# Function body sizes from the code section, indexed after the imports.
imports = 0
for sid, name, size, body, end in sections:
    if sid == 2:
        cnt, p = leb(body)
        for _ in range(cnt):
            ln, p = leb(p); p += ln; ln, p = leb(p); p += ln
            kind = data[p]; p += 1
            if kind == 0: _, p = leb(p); imports += 1
            elif kind == 1: p += 1; flags = data[p]; p += 1; _, p = leb(p); p = (leb(p)[1] if flags & 1 else p)
            elif kind == 2: flags = data[p]; p += 1; _, p = leb(p); p = (leb(p)[1] if flags & 1 else p)
            elif kind == 3: p += 2
sizes = {}
for sid, name, size, body, end in sections:
    if sid == 10:
        cnt, p = leb(body)
        for i in range(cnt):
            ln, p = leb(p); sizes[imports + i] = ln + 2; p += ln
print("code bodies:", len(sizes), "sum", f"{sum(sizes.values()):,}")
def bucket(n):
    n = n.lstrip("_")
    for pre, b in [("sklearn", "scikit-learn"), ("scipy", "scipy"), ("statsmodels", "statsmodels"),
                   ("numpy", "numpy"), ("npy", "numpy"), ("PyArray", "numpy"), ("pandas", "pandas"),
                   ("matplotlib", "matplotlib"), ("PIL", "Pillow"), ("Imaging", "Pillow"),
                   ("kiwi", "kiwisolver"), ("contourpy", "contourpy"), ("qh_", "qhull"),
                   ("xml", "libxml2/libxslt"), ("xslt", "libxml2/libxslt"), ("lxml", "lxml"),
                   ("regex", "regex"), ("FT_", "freetype"), ("ft_", "freetype"), ("hb_", "harfbuzz"),
                   ("Sheen", "sheenbidi"), ("SB", "sheenbidi"), ("raqm", "libraqm"), ("sqlite3", "sqlite"),
                   ("lzma", "xz"), ("BZ2", "bzip2"), ("Py", "cpython"), ("_Py", "cpython"),
                   ("std::", "libc++"), ("__cxx", "libc++"), ("cblas", "openblas"), ("LAPACK", "openblas"),
                   ("gotoblas", "openblas"), ("blas", "openblas")]:
        if n.startswith(pre): return b
    if re.match(r"^[sdcz](gemm|gemv|trsm|syrk|potrf|getrf|geqrf|gesdd|gesvd|syev|heev|lapack|axpy|dot|scal|copy|swap|nrm2|asum|trmm|symm|hemm|gbmv|sbmv|tbmv|tpmv|trmv|tbsv|tpsv|trsv|ger|her|syr|spr|hpr|rot|lacpy|laset|lange|lansy|larfg|larft|larfb|orm|org|un|ge|po|sy|he|tr|gb|gt|pb|pt|st|hs|la|bd|tg|gg|ls)", n): return "openblas"
    if "cython" in n.lower() or n.startswith("__pyx"): return "cython-generated (unattributed)"
    return "other"
tot = Counter()
for idx, sz in sizes.items():
    tot[bucket(fn.get(idx, "?"))] += sz
for b, sz in tot.most_common():
    print(f"  {b:34s} {sz:>12,}  {100*sz/sum(sizes.values()):5.1f}%")
