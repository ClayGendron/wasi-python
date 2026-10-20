"""scikit-learn's build scripts on the host (spec 044, Decision 13's unit checks): the module list
from meson's install plan with nothing copied, gen_inittab's four renames, the staging of scipy's
Cython declarations, and the weak-duplicate gate and link-map check. No artifact; the gate's
llvm-nm output is the form the SDK's llvm-nm prints for wasm objects, and one check compiles two
small objects with the SDK when step 10 has unpacked it."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

import pytest

from harness import paths

sys.path.insert(0, str(paths.REPO / "scripts"))

import gen_inittab  # noqa: E402
import install_from_plan  # noqa: E402
import line  # noqa: E402
import weak_duplicates  # noqa: E402

SH = shutil.which("sh")
SUFFIX = ".cpython-315-wasm32-wasi.so"
STAGE = paths.REPO / "scripts" / "stage_scipy_cimports.sh"


def test_modules_only_lists_the_modules_and_copies_nothing(tmp_path, capsys) -> None:
    """--modules-only writes each extension module not tagged tests, sorted by install path, and
    copies nothing: the untagged files of scikit-learn's install_subdir, which the full install
    stops on, are ignored."""
    info = tmp_path / "build" / "meson-info"
    info.mkdir(parents=True)
    plan = {
        "targets": {
            f"/b/sklearn/tree/_tree{SUFFIX}": {
                "destination": f"{{py_platlib}}/sklearn/tree/_tree{SUFFIX}",
                "tag": "runtime",
            },
            f"/b/sklearn/_cyutility{SUFFIX}": {
                "destination": f"{{py_platlib}}/sklearn/_cyutility{SUFFIX}",
                "tag": "runtime",
            },
            f"/b/sklearn/_t{SUFFIX}": {
                "destination": f"{{py_platlib}}/sklearn/_t{SUFFIX}",
                "tag": "tests",
            },
            "/b/sklearn/svm/liblibsvm-skl.a": {"destination": "{libdir}/x.a", "tag": "devel"},
        },
        "install_subdirs": {
            "/s/sklearn": {"destination": "{py_platlib}/sklearn", "tag": None},
        },
    }
    (info / "intro-install_plan.json").write_text(json.dumps(plan))
    listing = tmp_path / "modules.txt"
    argv = ["--modules-only", str(tmp_path / "build"), str(listing), SUFFIX]
    assert install_from_plan.main(argv) == 0
    assert capsys.readouterr().out == "2 extension modules listed; 1 tagged tests left out\n"
    assert listing.read_text().splitlines() == [
        f"/b/sklearn/_cyutility{SUFFIX}\tsklearn/_cyutility{SUFFIX}\truntime",
        f"/b/sklearn/tree/_tree{SUFFIX}\tsklearn/tree/_tree{SUFFIX}\truntime",
    ]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["build", "modules.txt"]
    # The full install stops on the untagged install_subdir, which is why step 58 lists only.
    with pytest.raises(SystemExit, match="tag None"):
        install_from_plan.main([str(tmp_path / "build"), str(tmp_path / "d"), str(listing), SUFFIX])


def test_the_inittab_renames_scikit_learns_four(tmp_path, monkeypatch) -> None:
    """scikit-learn's _cyutility registers beside pandas' and scipy's, and each of its three pairs
    beside its partner, under the renamed init functions; without the table's four entries the
    clash check stops on exactly those names."""
    built = {
        "sk": [
            "sklearn/_cyutility",
            "sklearn/ensemble/_gradient_boosting",
            "sklearn/ensemble/_hist_gradient_boosting/_gradient_boosting",
            "sklearn/tree/_tree",
            "sklearn/cluster/_hdbscan/_tree",
            "sklearn/tree/_utils",
            "sklearn/manifold/_utils",
        ],
        "sp": [
            "scipy/_cyutility",
            "scipy/optimize/_zeros",
            "scipy/optimize/cython_optimize/_zeros",
            "scipy/spatial/_qhull",
        ],
        "pd": ["pandas/_libs/_cyutility"],
    }
    for folder, modules in built.items():
        for module in modules:
            so = tmp_path / folder / (module + gen_inittab.SUFFIX)
            so.parent.mkdir(parents=True, exist_ok=True)
            so.write_bytes(b"!<arch>\n")
    out = tmp_path / "inittab.c"
    argv = [
        "gen_inittab.py",
        str(out),
        f"pandas={tmp_path / 'pd'}",
        f"scipy={tmp_path / 'sp'}",
        f"sklearn={tmp_path / 'sk'}",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    gen_inittab.main()
    inits = dict(
        re.findall(
            r'_PyImport_SwapPackageContext\("([\w.]+)"\);\s*PyObject \*m = PyInit_(\w+)\(\);',
            out.read_text(),
        )
    )
    assert inits == {
        "pandas._libs._cyutility": "_cyutility",
        "scipy._cyutility": "scipy__cyutility",
        "scipy.optimize._zeros": "_zeros",
        "scipy.optimize.cython_optimize._zeros": "scipy_optimize_cython_optimize__zeros",
        "scipy.spatial._qhull": "scipy_spatial__qhull",
        "sklearn._cyutility": "sklearn__cyutility",
        "sklearn.ensemble._gradient_boosting": "_gradient_boosting",
        "sklearn.ensemble._hist_gradient_boosting._gradient_boosting": (
            "sklearn_ensemble__hist_gradient_boosting__gradient_boosting"
        ),
        "sklearn.tree._tree": "_tree",
        "sklearn.cluster._hdbscan._tree": "sklearn_cluster__hdbscan__tree",
        "sklearn.tree._utils": "_utils",
        "sklearn.manifold._utils": "sklearn_manifold__utils",
    }
    renamed = {k: v for k, v in gen_inittab.RENAMED.items() if not k.startswith("sklearn.")}
    monkeypatch.setattr(gen_inittab, "RENAMED", renamed)
    clash = (
        r"share an init function name: \['_cyutility', '_gradient_boosting', '_tree', '_utils'\]"
    )
    with pytest.raises(SystemExit, match=clash):
        gen_inittab.main()


def _scipy_tree(tmp_path):
    src, build = tmp_path / "scipy-1.18.1", tmp_path / "scipy-build"
    files = {
        src / "scipy" / "linalg" / "__init__.pxd": "# linalg\n",
        src / "scipy" / "special" / "__init__.pxd": "# special\n",
        src / "scipy" / "special" / "cython_special.pxd": "cpdef double xlogy(double, double)\n",
        build / "scipy" / "linalg" / "cython_blas.pxd": "ctypedef int blas_int\n",
        build / "scipy" / "linalg" / "cython_lapack.pxd": "from .cython_blas cimport blas_int\n",
    }
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return src, build, files


@pytest.mark.skipif(SH is None, reason="no sh on this host")
def test_scipys_declarations_are_staged_as_six_files(tmp_path) -> None:
    """The five .pxd files land under scipy/linalg and scipy/special, with an empty
    scipy/__init__.py as the package marker, and an earlier staging is replaced; a missing one
    stops the script, named, and stages nothing."""
    src, build, files = _scipy_tree(tmp_path)
    out = tmp_path / "scipy-cimport"
    (out / "stale").mkdir(parents=True)
    r = subprocess.run([SH, str(STAGE), str(src), str(build), str(out)], capture_output=True)
    assert r.returncode == 0, r.stderr
    got = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert got == [
        "scipy/__init__.py",
        "scipy/linalg/__init__.pxd",
        "scipy/linalg/cython_blas.pxd",
        "scipy/linalg/cython_lapack.pxd",
        "scipy/special/__init__.pxd",
        "scipy/special/cython_special.pxd",
    ]
    assert (out / "scipy" / "__init__.py").read_bytes() == b""
    for path, text in files.items():
        rel = path.relative_to(src if src in path.parents else build)
        assert (out / rel).read_text() == text
    (build / "scipy" / "linalg" / "cython_lapack.pxd").unlink()
    shutil.rmtree(out)
    r = subprocess.run([SH, str(STAGE), str(src), str(build), str(out)], capture_output=True)
    assert r.returncode == 1
    assert b"scipy-build/scipy/linalg/cython_lapack.pxd" in r.stderr, r.stderr
    assert not out.exists()


# llvm-nm -A -P -g --defined-only, as the SDK prints it for wasm objects in archives.
NM = """\
liba.a[a.o]: _ZNSt3__26vectorIiNS_9allocatorIiEEE11__vallocateB9nqe230100Em W 295 9b
liba.a[a.o]: _ZNKSt3__26vectorIiNS_9allocatorIiEEE4sizeB9nqe230100Ev W 15c 3a
liba.a[a.o]: _ZSt28__throw_bad_array_new_lengthB9nqe230100v W c0e 2d
liba.a[a.o]: _ZTVNSt3__19basic_iosIcNS_11char_traitsIcEEEE V 0 40
liba.a[a.o]: __clang_call_terminate W b6a 13
liba.a[a.o]: counter D 0 4
liba.a[a.o]: draw W 11c 40
liba.a[a.o]: _ZN8pybind116detail4noteEv W 30 8
liba.a[a.o]: use_a T 1 64
libb.a[b.o]: _ZNSt3__26vectorIiNS_9allocatorIiEEE11__vallocateB9nqe230100Em W 295 9b
libb.a[b.o]: _ZNKSt3__26vectorIiNS_9allocatorIiEEE4sizeB9nqe230100Ev W 15c 3a
libb.a[b.o]: _ZSt28__throw_bad_array_new_lengthB9nqe230100v W c0e 2d
libb.a[b.o]: _ZTVNSt3__19basic_iosIcNS_11char_traitsIcEEEE V 0 40
libb.a[b.o]: __clang_call_terminate W b6a 13
libb.a[b.o]: counter D 0 4
libb.a[b.o]: draw T 11c 40
libb.a[b.o]: _ZN8pybind116detail4noteEv W 30 8
libb.a[b.o]: use_b T 1 64
libb.a[c.o]: only_weak_here W 0 4
libb.a[d.o]: only_weak_here W 0 4
"""
DEMANGLED = {"_ZN8pybind116detail4noteEv": "pybind11::detail::note()"}


def test_the_gate_names_a_shared_weak_definition_and_allows_the_standard_library() -> None:
    """A weak definition two archives share is named with each archive's kind (weak against
    strong included); the C++ standard library, its vtables and clang's terminate helper are
    allowed by rule; two strong definitions are wasm-ld's to refuse, not the gate's; two copies
    inside one archive are one archive's; a reviewed pattern matches the demangled form, and a
    pattern that allows nothing is stale."""
    defs = weak_duplicates.parse_nm(NM)
    assert defs[0] == (
        "liba.a",
        "_ZNSt3__26vectorIiNS_9allocatorIiEEE11__vallocateB9nqe230100Em",
        "W",
    )
    bad, stale = weak_duplicates.findings(defs, DEMANGLED, [])
    assert bad == [
        "weak definition shared by 2 archives: _ZN8pybind116detail4noteEv "
        "(pybind11::detail::note()): liba.a (weak), libb.a (weak)",
        "weak definition shared by 2 archives: draw: liba.a (weak), libb.a (strong)",
    ]
    assert stale == []
    bad, stale = weak_duplicates.findings(defs, DEMANGLED, ["*pybind11::detail::*", "gone_*"])
    assert bad == ["weak definition shared by 2 archives: draw: liba.a (weak), libb.a (strong)"]
    assert stale == ["gone_*"]


def test_the_gate_reads_its_list_and_refuses_a_line_it_cannot_read(tmp_path) -> None:
    allowed = tmp_path / "allowed.txt"
    allowed.write_text("# a comment\n\n*pybind11::*  # why it is safe\n")
    assert weak_duplicates.read_allowed(allowed) == ["*pybind11::*"]
    with pytest.raises(SystemExit, match="cannot read llvm-nm's line"):
        weak_duplicates.parse_nm("garbage without a type\n")


def test_the_link_map_check_wants_whole_names() -> None:
    """A required name must appear as a whole symbol name, and a forbidden one must not; the
    original name inside a renamed one does not count, but a data segment named after it does."""
    text = (
        "  10  10  40  4  .bss.sklearn_libsvm_mt_rand\n"
        "  20  20  9b  1  sklearn_liblinear_set_seed\n"
    )
    assert weak_duplicates.map_findings(text, ["sklearn_libsvm_mt_rand"], ["mt_rand"]) == []
    assert weak_duplicates.map_findings(text, ["sklearn_newrand_mt_rand"], ["set_seed"]) == [
        "the link map does not name sklearn_newrand_mt_rand"
    ]
    stray = text + "  30  30  40  4  .bss.mt_rand\n"
    assert weak_duplicates.map_findings(stray, [], ["mt_rand"]) == ["the link map names mt_rand"]


SDK = paths.BUILD / "tools" / line.read().get("WASI_SDK_DIR", "no-sdk-on-this-host")
NEWRAND = """\
#include <vector>
extern "C" {
unsigned NAME_counter = 1;
inline unsigned bounded(unsigned r) { return (NAME_counter++ * 7u) % r; }
unsigned NAME_use(unsigned r) { std::vector<int> v(3); return bounded(r) + v.size(); }
}
"""


@pytest.mark.skipif(not (SDK / "bin" / "clang++").is_file(), reason="step 10 has not run")
def test_the_gate_on_two_compiled_objects(tmp_path) -> None:
    """Two small wasm objects, each defining the same `inline` function inside extern "C" as
    newrand.h does, are named by the gate; with one copy renamed by a header, as
    recipes/sklearn-renames/ does, the pair is clean; std::vector's templates in both are allowed
    by rule throughout."""

    def archive(name: str, header: str | None) -> str:
        src = tmp_path / f"{name}.cpp"
        src.write_text(NEWRAND.replace("NAME", name))
        cmd = [str(SDK / "bin" / "clang++"), "--target=wasm32-wasip1", "-O0", "-c", str(src)]
        cmd += ["-include", header] if header else []
        obj, lib = tmp_path / f"{name}.o", tmp_path / f"lib{name}.a"
        subprocess.run([*cmd, "-o", str(obj)], check=True, capture_output=True)
        subprocess.run([str(SDK / "bin" / "llvm-ar"), "rcs", str(lib), str(obj)], check=True)
        return str(lib)

    rename = tmp_path / "rename.h"
    rename.write_text("#define bounded renamed_bounded\n")
    allowed = tmp_path / "allowed.txt"
    allowed.write_text("")
    tools = [str(SDK / "bin" / "llvm-nm"), str(SDK / "bin" / "llvm-cxxfilt"), str(allowed)]

    def gate(*libs: str) -> subprocess.CompletedProcess:
        cmd = [sys.executable, str(paths.REPO / "scripts" / "weak_duplicates.py"), "archives"]
        env = dict(os.environ, PYTHONPATH="")
        return subprocess.run([*cmd, *tools, *libs], capture_output=True, text=True, env=env)

    r = gate(archive("a", None), archive("b", None))
    assert r.returncode == 1
    assert "ERROR: weak definition shared by 2 archives: bounded: liba.a (weak), libb.a (weak)" in (
        r.stdout
    )
    assert r.stdout.count("ERROR") == 1, r.stdout  # the std:: templates are allowed by rule
    r = gate(archive("a", None), archive("b", str(rename)))
    assert r.returncode == 0, r.stdout
    assert "0 unreviewed" in r.stdout
