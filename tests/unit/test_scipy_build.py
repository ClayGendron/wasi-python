"""scipy's build scripts on the host (spec 037, Decision 15's unit checks): the direct-call file
f2py's routines get, the install from meson's plan, gen_inittab's rename table, the wrapper's
per-file include (and its argv unchanged when unset), and the audit of OpenBLAS's void
convention. No artifact, no toolchain: the wrapper runs a stand-in compiler that prints its argv."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest

from harness import paths

sys.path.insert(0, str(paths.REPO / "scripts"))

import audit_openblas_void  # noqa: E402
import f2py_direct_calls  # noqa: E402
import gen_inittab  # noqa: E402
import install_from_plan  # noqa: E402

SH = shutil.which("sh")
WRAPPER = paths.REPO / "scripts" / "wasi-cc"

MODULE = """/* File: _tinymodule.c */
#include <Python.h>
#include "fortranobject.h"
typedef union { struct {float r,i;}; npy_cfloat _npy; } complex_float;
#define F_FUNC(f,F) f##_
#define F_INT int
static PyObject *_tiny_error;
extern void F_FUNC(sgesv,SGESV)(F_INT*,F_INT*,float*,F_INT*,F_INT*,float*,F_INT*,F_INT* );
extern void F_FUNC(cgees,CGEES)(char*,char*,F_INT(*)(complex_float*),F_INT*,F_INT,F_INT );
extern float F_FUNC(sdot,SDOT)(F_INT*,float*,F_INT*,float*,F_INT* );
extern void F_FUNC(sgesv,SGESV)(F_INT*,F_INT*,float*,F_INT*,F_INT*,float*,F_INT*,F_INT* );
static int body(void) { return 0; }
"""


def test_the_direct_call_file_calls_each_routine_once() -> None:
    """Each routine a module declares is called once, directly, with as many zeros as its
    prototype has parameters (a function-pointer parameter counts as one), after the module's own
    preamble; a routine two modules declare differently stops it."""
    text, n = f2py_direct_calls.render([("_tinymodule.c", MODULE)])
    assert n == 3
    assert "typedef union { struct {float r,i;}; npy_cfloat _npy; } complex_float;" in text
    assert "static int body" not in text  # nothing after the first prototype is copied
    calls = [line.strip() for line in text.splitlines() if line.strip().startswith("(void)")]
    assert calls == [
        "(void)F_FUNC(sgesv,SGESV)(0, 0, 0, 0, 0, 0, 0, 0);",
        "(void)F_FUNC(cgees,CGEES)(0, 0, 0, 0, 0, 0);",
        "(void)F_FUNC(sdot,SDOT)(0, 0, 0, 0, 0);",
    ]
    other = MODULE.replace("F_INT*,float*,F_INT*,float*,F_INT* );", "F_INT*,float*,F_INT* );")
    with pytest.raises(SystemExit, match="sdot: _tinymodule.c and _other.c declare it differently"):
        f2py_direct_calls.render([("_tinymodule.c", MODULE), ("_other.c", other)])


def _plan(tmp_path, entries: dict) -> None:
    info = tmp_path / "build" / "meson-info"
    info.mkdir(parents=True)
    (info / "intro-install_plan.json").write_text(json.dumps(entries))


SUFFIX = ".cpython-315-wasm32-wasi.so"


def test_the_install_takes_python_runtime_files_and_lists_extension_modules(tmp_path) -> None:
    """Files tagged python-runtime land at their destinations; tests and devel are skipped; each
    extension module is listed with its build path, install path and tag, never copied, and a
    test module is not listed."""
    src = tmp_path / "src"
    src.mkdir()
    for name in ("a.py", "data.npz", "t.py", "cfg.py"):
        (src / name).write_text(name)
    _plan(
        tmp_path,
        {
            "targets": {
                f"/b/scipy/linalg/_flapack{SUFFIX}": {
                    "destination": f"{{py_platlib}}/scipy/linalg/_flapack{SUFFIX}",
                    "tag": "runtime",
                },
                f"/b/scipy/_cyutility{SUFFIX}": {
                    "destination": f"{{py_platlib}}/scipy/_cyutility{SUFFIX}",
                    "tag": "python-runtime",
                },
                f"/b/scipy/_lib/_test_ccallback{SUFFIX}": {
                    "destination": f"{{py_platlib}}/scipy/_lib/_test_ccallback{SUFFIX}",
                    "tag": "tests",
                },
                "/b/libx.a": {"destination": "{py_platlib}/scipy/lib/libx.a", "tag": "devel"},
            },
            "python": {
                str(src / "a.py"): {
                    "destination": "{py_platlib}/scipy/a.py",
                    "tag": "python-runtime",
                },
                str(src / "data.npz"): {
                    "destination": "{py_purelib}/scipy/stats/data.npz",
                    "tag": "python-runtime",
                },
                str(src / "t.py"): {"destination": "{py_platlib}/scipy/tests/t.py", "tag": "tests"},
            },
            "configure": {
                str(src / "cfg.py"): {
                    "destination": "{py_platlib}/scipy/__config__.py",
                    "tag": "python-runtime",
                }
            },
        },
    )
    dest, listing = tmp_path / "dest", tmp_path / "modules.txt"
    rc = install_from_plan.main([str(tmp_path / "build"), str(dest), str(listing), SUFFIX])
    assert rc == 0
    got = sorted(str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file())
    assert got == ["scipy/__config__.py", "scipy/a.py", "scipy/stats/data.npz"]
    assert listing.read_text().splitlines() == [
        f"/b/scipy/_cyutility{SUFFIX}\tscipy/_cyutility{SUFFIX}\tpython-runtime",
        f"/b/scipy/linalg/_flapack{SUFFIX}\tscipy/linalg/_flapack{SUFFIX}\truntime",
    ]


def test_the_install_stops_on_a_destination_outside_the_package(tmp_path) -> None:
    _plan(
        tmp_path,
        {"python": {"/s/x.h": {"destination": "{includedir}/x.h", "tag": "python-runtime"}}},
    )
    with pytest.raises(SystemExit, match="is not under"):
        install_from_plan.main(
            [str(tmp_path / "build"), str(tmp_path / "d"), str(tmp_path / "l"), SUFFIX]
        )


def test_the_inittab_renames_what_the_table_names_and_checks_the_final_names(
    tmp_path, monkeypatch
) -> None:
    """scipy's _cyutility, cython_optimize._zeros and spatial._qhull register under their renamed
    init functions beside pandas' _cyutility and optimize._zeros; matplotlib's _qhull is left out
    by its dotted name while scipy's is kept; and a clash left after the renames still stops it."""
    import re

    built = {
        "sp": [
            "scipy/_cyutility",
            "scipy/optimize/_zeros",
            "scipy/optimize/cython_optimize/_zeros",
            "scipy/spatial/_qhull",
        ],
        "pd": ["pandas/_libs/_cyutility"],
        "mpl": ["matplotlib/_qhull", "matplotlib/_path"],
    }
    for folder, modules in built.items():
        for module in modules:
            so = tmp_path / folder / (module + gen_inittab.SUFFIX)
            so.parent.mkdir(parents=True, exist_ok=True)
            so.write_bytes(b"!<arch>\n")
    out = tmp_path / "inittab.c"
    argv = ["gen_inittab.py", str(out), f"scipy={tmp_path / 'sp'}", f"pandas={tmp_path / 'pd'}"]
    argv.append(f"matplotlib={tmp_path / 'mpl'}")
    monkeypatch.setattr(sys, "argv", argv)
    gen_inittab.main()
    text = out.read_text()
    inits = dict(
        re.findall(
            r'_PyImport_SwapPackageContext\("([\w.]+)"\);\s*PyObject \*m = PyInit_(\w+)\(\);', text
        )
    )
    assert inits == {
        "scipy._cyutility": "scipy__cyutility",
        "scipy.optimize._zeros": "_zeros",
        "scipy.optimize.cython_optimize._zeros": "scipy_optimize_cython_optimize__zeros",
        "scipy.spatial._qhull": "scipy_spatial__qhull",
        "pandas._libs._cyutility": "_cyutility",
        "matplotlib._path": "_path",
    }
    clash = tmp_path / "sp2" / "scipy" / "x" / ("_path" + gen_inittab.SUFFIX)
    clash.parent.mkdir(parents=True)
    clash.write_bytes(b"!<arch>\n")
    argv = [
        "gen_inittab.py",
        str(out),
        f"scipy={tmp_path / 'sp2'}",
        f"matplotlib={tmp_path / 'mpl'}",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit, match=r"share an init function name: \['_path'\]"):
        gen_inittab.main()


def _wrapper(tmp_path, argv: list[str], env_extra: dict | None = None) -> list[str]:
    """The argv scripts/wasi-cc hands its compiler, read from a stand-in clang that prints it."""
    sdk = tmp_path / "sdk"
    (sdk / "bin").mkdir(parents=True, exist_ok=True)
    clang = sdk / "bin" / "clang"
    clang.write_text('#!/bin/sh\nfor a in "$@"; do printf "%s\\n" "$a"; done\n')
    clang.chmod(0o755)
    env = {"PATH": os.environ.get("PATH", os.defpath), "WASI_SDK_PATH": str(sdk)}
    env.update(env_extra or {})
    r = subprocess.run(
        [SH, str(WRAPPER), *argv], env=env, capture_output=True, text=True, timeout=60
    )
    assert r.returncode == 0, r.stderr
    return r.stdout.splitlines()


# Command lines shaped like numpy's, pandas' and OpenBLAS's compiles (spec 037's pre-build review,
# finding 4): with the map unset, the wrapper hands the compiler exactly what it did before.
SHAPES = [
    [
        "-Inumpy/_core",
        "-fPIC",
        "-O3",
        "-include",
        "/r/recipes/npy_rename.h",
        "-MD",
        "-MQ",
        "x.o",
        "-MF",
        "x.o.d",
        "-o",
        "numpy/_core/x.c.o",
        "-c",
        "../numpy/_core/src/x.c",
    ],
    [
        "-Ipandas/_libs",
        "-fPIC",
        "-pthread",
        "-DNPY_NO_SIGNAL",
        "-o",
        "p.o",
        "-c",
        "pandas/_libs/hashtable.pyx.c",
    ],
    ["-O2", "-DARCH_WASM", "-include", "sched.h", "-c", "-o", "dgemm.o", "../kernel/dgemm.c"],
]


@pytest.mark.parametrize("argv", SHAPES, ids=["numpy", "pandas", "openblas"])
def test_the_wrapper_is_unchanged_without_the_map(tmp_path, argv) -> None:
    dropped = {"-fPIC", "-fpic", "-fPIE", "-fpie", "-pthread"}
    want = ["--target=wasm32-wasip1", *[a for a in argv if a not in dropped]]
    assert _wrapper(tmp_path, argv) == want


def test_the_wrapper_adds_a_mapped_files_include_and_logs_it(tmp_path) -> None:
    """A compile whose source path ends with a map entry's suffix gets that entry's -include and
    one log line; another compile gets neither; a comment line is no entry."""
    mapping = tmp_path / "map.txt"
    mapping.write_text("# a comment\n_flapackmodule.c /r/flapack.h\n/_zeros.c /r/zeros.h\n")
    log = tmp_path / "log.txt"
    env = {"WASI_CC_FILE_INCLUDES": str(mapping), "WASI_CC_FILE_INCLUDES_LOG": str(log)}
    hit = ["-O2", "-o", "f.o", "-c", "scipy/linalg/_flapackmodule.c"]
    assert _wrapper(tmp_path, hit, env) == [
        "--target=wasm32-wasip1",
        *hit,
        "-include",
        "/r/flapack.h",
    ]
    miss = ["-O2", "-o", "z.o", "-c", "scipy/optimize/_zerosmodule.c"]
    assert _wrapper(tmp_path, miss, env) == ["--target=wasm32-wasip1", *miss]
    zeros = ["-O2", "-o", "_zeros.c.o", "-c", "scipy/optimize/cython_optimize/_zeros.so.p/_zeros.c"]
    assert _wrapper(tmp_path, zeros, env)[-2:] == ["-include", "/r/zeros.h"]
    assert log.read_text().splitlines() == [
        "_flapackmodule.c\tscipy/linalg/_flapackmodule.c",
        "/_zeros.c\tscipy/optimize/cython_optimize/_zeros.so.p/_zeros.c",
    ]


AUDITED = """diff --git a/lapack-netlib/SRC/dgesv.c b/lapack-netlib/SRC/dgesv.c
--- a/lapack-netlib/SRC/dgesv.c
+++ b/lapack-netlib/SRC/dgesv.c
@@ -1,9 +1,9 @@
-/* Subroutine */ int dgesv_(integer *n, integer *nrhs)
+/* Subroutine */ void dgesv_(integer *n, integer *nrhs)
 {
-    extern /* Subroutine */ int xerbla_(char *, integer *);
+    extern /* Subroutine */ void xerbla_(char *, integer *, ftnlen);
-	xerbla_("DGESV", &i__1);
-	return 0;
+	xerbla_("DGESV", &i__1, (ftnlen)5);
+	return;
 }
"""


def test_the_audit_pairs_each_rule_and_names_a_stranger() -> None:
    """Each of the convention's rewrites is paired with its rule; a line no rule explains is
    named, and so is a removal with no addition."""
    kinds, bad = audit_openblas_void.audit(AUDITED)
    assert dict(kinds) == {"int->void": 1, "xerbla proto": 1, "xerbla call": 1, "return": 1}
    assert bad == []
    stranger = AUDITED.replace("+	return;", "+	return 1;")
    kinds, bad = audit_openblas_void.audit(stranger)
    assert bad == ["-\treturn 0; / +\treturn 1;"]
    lone = AUDITED + "@@ -20,1 +20,0 @@\n-    i__1 = 0;\n"
    assert audit_openblas_void.audit(lone)[1] == ["unpaired: -    i__1 = 0;"]
