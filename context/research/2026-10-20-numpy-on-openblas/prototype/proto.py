"""Spec 100's drafting prototype: compile numpy's BLAS and LAPACK callers as a numpy build that found
the set's OpenBLAS would (-DHAVE_CBLAS, no BLAS_SYMBOL_PREFIX), with main's own compile commands
(build/numpy-build/compile_commands.json, read only), into a scratch folder; then link them
against build/openblas-wasi/lib/libopenblas.a and count wasm-ld's signature mismatches.

  variant A  no recipe: the names numpy's sources give
  variant B  the recipe: recipes' numpy_lapack_abi.h force-included into the linalg callers and
             both python_xerbla.c, and the shims in numpy_lapack_shims.c linked

Nothing under the main tree is written: -MD/-MQ/-MF are dropped and -o points here.
"""

import json
import os
import shlex
import subprocess
import sys

MAIN = os.environ["REPO"]
SDK = f"{MAIN}/build/tools/wasi-sdk-34.0-arm64-macos"
OB = f"{MAIN}/build/openblas-wasi"
HERE = os.environ["WORK"]
OUT = f"{HERE}/proto"
HEADER = f"{HERE}/bin/numpy_lapack_abi.h"
SHIMS = f"{HERE}/bin/numpy_lapack_shims.c"

db = json.load(open(f"{MAIN}/build/numpy-build/compile_commands.json"))


def entry(suffix, module):
    hits = [e for e in db if e["file"].endswith(suffix) and module in e["command"]]
    assert len(hits) == 1, (suffix, module, len(hits))
    return hits[0]


# (label, compile_commands suffix, module the entry belongs to, source to compile instead, gets header)
UNITS = [
    ("umath_linalg", "linalg/umath_linalg.cpp", "_umath_linalg", None, True),
    ("lapack_litemodule", "linalg/lapack_litemodule.c", "lapack_lite.cpython", None, True),
    ("linalg_python_xerbla", "lapack_lite/python_xerbla.c", "lapack_lite.cpython", None, True),
    ("vdot", "multiarray/vdot.c", "_multiarray_umath", None, False),
    ("multiarraymodule", "multiarray/multiarraymodule.c", "_multiarray_umath", None, False),
    ("arraytypes", "arraytypes.c", "_multiarray_umath", None, False),
    ("matmul", "matmul.c", "_multiarray_umath", None, False),
    ("ufunc_type_resolution", "umath/ufunc_type_resolution.c", "_multiarray_umath", None, False),
    ("cblasfuncs", "multiarray/vdot.c", "_multiarray_umath", "../numpy-2.5.2/numpy/_core/src/common/cblasfuncs.c", False),
    ("core_python_xerbla", "multiarray/vdot.c", "_multiarray_umath", "../numpy-2.5.2/numpy/_core/src/common/python_xerbla.c", True),
]


def command(e, obj, source, header):
    words = shlex.split(e["command"])
    out, skip = [], 0
    for i, w in enumerate(words):
        if skip:
            skip -= 1
            continue
        if w in ("-MQ", "-MF", "-o"):
            skip = 1
            continue
        if w == "-MD" or w.startswith("-DBLAS_SYMBOL_PREFIX="):
            continue
        if w == "-c":
            skip = 1
            continue
        out.append(w)
    src = source or words[words.index("-c") + 1]
    out[1:1] = ["-DHAVE_CBLAS", f"-I{OB}/include"] + (["-include", HEADER] if header else [])
    return out + ["-c", src, "-o", obj]


env = dict(os.environ, WASI_SDK_PATH=SDK)
for variant in ("A", "B"):
    d = f"{OUT}/{variant}"
    os.makedirs(d, exist_ok=True)
    objs = []
    for label, suffix, module, source, header in UNITS:
        e = entry(suffix, module)
        obj = f"{d}/{label}.o"
        cmd = command(e, obj, source, header and variant == "B")
        r = subprocess.run(cmd, cwd=e["directory"], env=env, capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"{variant} {label}: compile failed\n{r.stderr[-2000:]}")
        objs.append(obj)
    if variant == "B":
        obj = f"{d}/numpy_lapack_shims.o"
        subprocess.run([f"{SDK}/bin/clang", "--target=wasm32-wasip1", "-O2", "-c", SHIMS, "-o", obj], check=True)
        objs.append(obj)
    # As step 60 links them: each python_xerbla.o is a member of its module's archive (three
    # archives), pulled only when a name it defines is still undefined; the other objects stand for
    # the members the inittab's references pull. The archives come before libopenblas.a, as there.
    direct = [o for o in objs if not o.endswith("python_xerbla.o")]
    archives = []
    for o in objs:
        if o.endswith("python_xerbla.o"):
            a = o[:-2] + ".a"
            if os.path.exists(a):
                os.remove(a)
            subprocess.run([f"{SDK}/bin/llvm-ar", "rcs", a, o], check=True)
            archives.append(a)
    objs = direct + archives
    log = f"{d}/link.log"
    with open(log, "w") as f:
        r = subprocess.run(
            [f"{SDK}/bin/wasm-ld", "--no-entry", "--allow-undefined", "--export-all", "--no-gc-sections",
             *objs, f"{OB}/lib/libopenblas.a", "-o", f"{d}/linked.wasm"],
            stdout=f, stderr=subprocess.STDOUT)
    text = open(log).read()
    names = sorted({line.split(":")[-1].strip() for line in text.splitlines() if "signature mismatch" in line})
    dups = [line for line in text.splitlines() if "duplicate symbol" in line]
    print(f"variant {variant}: link exit {r.returncode}, {len(names)} signature mismatches, {len(dups)} duplicate symbols")
    if names:
        print("  ", " ".join(names))
    nm = subprocess.run([f"{SDK}/bin/llvm-nm", f"{d}/linked.wasm"], capture_output=True, text=True).stdout
    for sym in ("xerbla_", "wasi_numpy_xerbla_", "dgesv_", "wasi_numpy_dgesv_", "cblas_dgemm"):
        hits = [l for l in nm.splitlines() if l.split()[-1:] == [sym]]
        print(f"   {sym}: {len(hits)} {' | '.join(hits)}")
