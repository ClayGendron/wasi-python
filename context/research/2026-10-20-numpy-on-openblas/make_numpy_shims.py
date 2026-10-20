"""Write recipes/numpy_lapack_shims.c (spec 100, Decision 4) from numpy's own declarations, so each
shim's parameters are numpy's, copied in numpy's order, never retyped. Usage:
    make_numpy_shims.py <numpy source tree> > recipes/numpy_lapack_shims.c
It reads numpy/linalg/umath_linalg.cpp and lapack_litemodule.c, takes the 35 routines numpy calls,
and stops if a routine is missing or the two files declare one differently."""

import re
import sys


CALLED = sorted(
    (
        "ccopy cgelsd cgesdd cgesv cgetrf cheevd cpotrf dcopy dgeev dgelsd dgeqrf dgesdd dgesv dgetrf "
        "dorgqr dpotrf dsyevd scopy sgeev sgelsd sgesdd sgesv sgetrf spotrf ssyevd zcopy zgeev zgelsd "
        "zgeqrf zgesdd zgesv zgetrf zheevd zpotrf zungqr"
    ).split()
)
PAT = re.compile(r"extern\s+(?:\"C\"\s+)?fortran_int\s+FNAME\((\w+)\)\s*\(([^;]*?)\)\s*;", re.S)

HEADER = """\
/* numpy's side of the LAPACK ABI (spec 100, Decision 4): one shim for each of the 35 LAPACK and
 * BLAS routines numpy's linear algebra calls, and no other.
 *
 *   numpy declares each of them as returning an int (numpy/linalg/umath_linalg.cpp,
 *   lapack_litemodule.c); the set's OpenBLAS defines them void, as LAPACK's subroutines are and as
 *   scipy declares them (spec 037). WebAssembly traps on a call whose type differs from its
 *   target's. recipes/numpy_lapack_abi.h sends numpy's calls to wasi_numpy_<name>_; each shim here
 *   passes numpy's parameters, in numpy's order, unchanged, to OpenBLAS's routine and returns 0,
 *   what an f2c subroutine returns. numpy reads only `info`; lapack_lite returns the 0 as its
 *   '<name>_' entry, which is what native numpy reads on OpenBLAS.
 *
 * The parameter lists are numpy 2.5.2's own, copied by
 * context/research/2026-10-20-numpy-on-openblas/make_numpy_shims.py; every argument is a pointer.
 * Step 40 compiles this file alone, with no numpy flag and no rename header, into
 * build/numpy-shims/libnumpy_lapack_shims.a; step 60 links it. Check 4
 * (test_one_lapack_is_linked) holds the set: the names defined here equal the wasi_numpy_* names
 * numpy's two objects leave undefined, less wasi_numpy_xerbla_. A numpy that calls a routine with
 * no shim fails the link. Remove this file with recipes/numpy_lapack_abi.h. */

typedef int fortran_int; /* numpy's CBLAS_INT with no ILP64: OpenBLAS's LP64 blasint */
typedef struct {
    float r, i;
} f2c_complex;
typedef struct {
    double r, i;
} f2c_doublecomplex;
"""


def arg_name(param):
    return re.findall(r"(\w+)\s*(?:\[\])?$", param.strip())[0]


def wrap(head, items, tail, indent):
    """head(item, item, ...)tail, broken only after a comma, lines at most 99 columns."""
    lines, line = [], head + "("
    for k, item in enumerate(items):
        piece = item + (", " if k < len(items) - 1 else ")" + tail)
        if len(line) + len(piece.rstrip()) > 99:
            lines.append(line.rstrip())
            line = indent
        line += piece
    lines.append(line.rstrip())
    return "\n".join(lines)


def main():
    src = sys.argv[1]
    found = {}
    for f in ("umath_linalg.cpp", "lapack_litemodule.c"):
        for m in PAT.finditer(open(f"{src}/numpy/linalg/{f}").read()):
            found.setdefault(m[1], set()).add(" ".join(m[2].split()))
    out = [HEADER]
    for name in CALLED:
        decls = found.get(name)
        if not decls or len(decls) != 1:
            sys.exit(f"{name}: numpy declares it {len(decls or ())} ways")
        params = [p.strip() for p in decls.pop().split(",")]
        args = [arg_name(p) for p in params]
        out.append(wrap(f"void {name}_", params, ";", "    "))
        out.append(wrap(f"fortran_int wasi_numpy_{name}_", params, "", "    "))
        out.append("{")
        out.append(wrap(f"    {name}_", args, ";", "        "))
        out.append("    return 0;")
        out.append("}")
        out.append("")
    print("\n".join(out).rstrip())


main()
