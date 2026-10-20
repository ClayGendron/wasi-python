"""Generate the inittab constructor: one C file that registers every cross-built extension module
on CPython's inittab under its dotted import name, derived from the archive's path under its meson
build directory (spec 003, step 60).

    gen_inittab.py [--against <CPython's Modules/config.c>] <out.c> <package>=<meson build dir> ...

Builtin lookup compares the full dotted name (Python/import.c, is_builtin), so
`numpy._core._multiarray_umath` resolves to a builtin from inside the numpy package. Test-only
numpy modules (*_tests, _simd) are left out, and so is matplotlib's `_tkagg` (no Tk); its `_qhull`
is registered since spec 043. A module built at the root of a build directory is placed by
ROOT_MODULES, or the run fails. The plot packages' directories (build/plot-modules/*) and scipy's
(build/scipy-modules, spec 037) hold each archive at its install path (spec 023, step 55;
contourpy's `_contourpy`, spec 043), so their names are those paths.

A module whose init function would share its name with another's is compiled with a renamed one
(recipes/scipy_rename.h and recipes/scipy_cython_optimize_zeros.h; scikit-learn's four in
recipes/sklearn-renames/, spec 044), and RENAMED names it here; the clash check runs on the final
names (spec 037, Decision 8). scikit-learn's archives lie at their install paths
(build/sklearn-modules), as scipy's do.

`--against` names CPython's own Modules/config.c: an entry whose init function has the name of
one of CPython's builtins (`PyInit__random`) stops the run. The static link would resolve the
inittab's reference to CPython's function, never pull in the package's archive member, and say
nothing, so the package's module would be CPython's (spec 044's build: sklearn.utils._random).

Each entry is registered through a wrapper that calls its init function inside CPython's package
context, set to the entry's dotted name, as `_PyImport_RunModInitFunction` does for a module loaded
from a shared library (Python/importdl.c); a builtin gets no context otherwise, so a single-phase
module (regex's `_regex`) would keep its short name and pickle would look for a top-level module
(spec 047, Decision 4). Multi-phase modules return a definition and never read the context. The
one internal function is declared here, as Include/internal/pycore_import.h declares it; step 60
stops if the pinned header no longer does.
"""

import re
import sys
from pathlib import Path

import line

SUFFIX = f".cpython-{line.read()['PYTHON_TAG']}-wasm32-wasi.so"
# Cython 3.1+ builds its shared utility module at the build root; pandas imports it from here.
ROOT_MODULES = {("pandas", "_cyutility"): "pandas._libs._cyutility"}
# Left out by dotted name: numpy's SIMD test module, and matplotlib's _tkagg (no Tk). Both
# _qhull modules are linked (matplotlib's since spec 043; scipy.spatial's, spec 037).
LEFT_OUT = {"numpy._core._simd", "matplotlib.backends._tkagg"}
# Init functions compiled under another name (spec 037, Decision 8): dotted name -> the name after
# PyInit_. scipy's _cyutility shares pandas' name; scipy.optimize.cython_optimize._zeros shares
# scipy.optimize._zeros'; scipy.spatial._qhull shares matplotlib's _qhull (linked by spec 043).
RENAMED = {
    "scipy._cyutility": "scipy__cyutility",
    "scipy.optimize.cython_optimize._zeros": "scipy_optimize_cython_optimize__zeros",
    "scipy.spatial._qhull": "scipy_spatial__qhull",
    # scikit-learn (spec 044, Decision 6; recipes/sklearn-renames/): its _cyutility shares pandas'
    # and scipy's name; three modules share a name with another of its own, whose partner keeps it.
    "sklearn._cyutility": "sklearn__cyutility",
    "sklearn.ensemble._hist_gradient_boosting._gradient_boosting": (
        "sklearn_ensemble__hist_gradient_boosting__gradient_boosting"
    ),
    "sklearn.cluster._hdbscan._tree": "sklearn_cluster__hdbscan__tree",
    "sklearn.manifold._utils": "sklearn_manifold__utils",
    # sklearn.utils._random's PyInit__random is CPython's own `_random` (found at spec 044's build:
    # the link kept CPython's and dropped scikit-learn's member without a word); --against stops it.
    "sklearn.utils._random": "sklearn_utils__random",
}
# CPython's own declaration (Include/internal/pycore_import.h), less the parameter's name.
SWAP = "const char *_PyImport_SwapPackageContext"


def wrapper(n: int, dotted: str, name: str) -> str:
    """Entry n's init function, called with the package context set to its dotted name."""
    return (
        f"static PyObject *ctx_{n}(void)\n"
        "{\n"
        f'    const char *old = _PyImport_SwapPackageContext("{dotted}");\n'
        f"    PyObject *m = PyInit_{name}();\n"
        "    _PyImport_SwapPackageContext(old);\n"
        "    return m;\n"
        "}\n"
    )


def modules(package: str, build_dir: Path) -> list[tuple[str, str]]:
    found = []
    for so in sorted(build_dir.rglob("*" + SUFFIX)):
        name = so.name[: -len(SUFFIX)]
        if name.endswith("_tests"):
            continue
        parts = list(so.relative_to(build_dir).parent.parts)
        if parts:
            dotted = ".".join([*parts, name])
        elif (package, name) in ROOT_MODULES:
            dotted = ROOT_MODULES[(package, name)]
        else:
            raise SystemExit(f"{so}: built at the root of {build_dir}; add it to ROOT_MODULES")
        if dotted in LEFT_OUT:
            continue
        if not dotted.startswith(package + "."):
            raise SystemExit(f"{so}: {dotted} is outside the {package} package")
        found.append((dotted, RENAMED.get(dotted, name)))
    return found


def builtin_inits(config_c: Path) -> set[str]:
    """The names after PyInit_ of the builtins CPython's own config.c registers."""
    return set(re.findall(r"\bPyInit_(\w+)\(", config_c.read_text()))


def main() -> None:
    args = sys.argv[1:]
    against: set[str] = set()
    if args[:1] == ["--against"]:
        against = builtin_inits(Path(args[1]))
        args = args[2:]
    out = Path(args[0])
    entries = []
    for arg in args[1:]:
        package, _, build_dir = arg.partition("=")
        entries += modules(package, Path(build_dir))
    names = [name for _, name in entries]
    clashes = sorted({n for n in names if names.count(n) > 1})
    if clashes:
        raise SystemExit(f"two modules share an init function name: {clashes}")
    taken = sorted(f"{dotted} (PyInit_{name})" for dotted, name in entries if name in against)
    if taken:
        raise SystemExit(f"init function names CPython's own builtins have: {taken}")
    unused = sorted(set(RENAMED) - {dotted for dotted, _ in entries})
    if unused and any(d.split(".")[0] in {e.split(".")[0] for e, _ in entries} for d in unused):
        raise SystemExit(f"RENAMED names modules this link has not: {unused}")
    lines = [
        "/* Generated by scripts/gen_inittab.py. Do not edit. */",
        "#include <Python.h>",
        f"extern {SWAP}(const char *);",
        *(f"extern PyObject *PyInit_{name}(void);" for _, name in entries),
        "",
        "/* Each init function runs inside the package context of its dotted name (spec 047). */",
        *(wrapper(n, dotted, name) for n, (dotted, name) in enumerate(entries)),
        "static int registered = 0;",
        "",
        "/* Runs from the constructor pass, before Py_Initialize; once only. */",
        "__attribute__((constructor)) static void",
        "register_builtin_extensions(void)",
        "{",
        "    if (registered) {",
        "        return;",
        "    }",
        "    registered = 1;",
        *(f'    PyImport_AppendInittab("{d}", ctx_{n});' for n, (d, _) in enumerate(entries)),
        "}",
        "",
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    print(f"{out}: {len(entries)} modules")


if __name__ == "__main__":
    main()
