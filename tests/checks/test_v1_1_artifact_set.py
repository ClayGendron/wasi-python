"""v1.1: the artifact set is complete, sealed behind the wall, and says what built it."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from harness import artifacts as rules
from harness import needs, paths, scan

pytestmark = pytest.mark.goal("v1.1")

BINARY = pytest.mark.parametrize("which", ["plain", "snapshot"])
NEED_OF = {"plain": "plain binary", "snapshot": "snapshot binary"}


def _binary(artifacts, which):
    needs.need(NEED_OF[which])
    return artifacts.binary(which)


def test_artifact_set_is_complete(artifacts) -> None:
    errors = rules.complete_errors(artifacts.dir)
    assert not errors, scan.report(errors)


def test_sha256sums_match_the_files(artifacts) -> None:
    errors = rules.sums_errors(artifacts.dir)
    assert not errors, scan.report(errors)


def test_no_compiled_module_in_the_set(artifacts) -> None:
    errors = rules.cwasm_errors(artifacts.dir)
    assert not errors, scan.report(errors)


@BINARY
def test_binary_is_a_core_wasm_module(artifacts, which, metric) -> None:
    binary = _binary(artifacts, which)
    metric("bytes", binary.stat().st_size)
    errors = rules.is_core_module_errors(binary)
    assert not errors, scan.report(errors)


@BINARY
def test_imports_are_wasi_and_the_door_only(artifacts, which) -> None:
    errors = rules.module_errors(_binary(artifacts, which))
    assert not errors, scan.report(errors)


@BINARY
def test_exceptions_are_the_standard_form(artifacts, which) -> None:
    """C++ exceptions reach their handlers: the standard exnref form, which hosts must support."""
    errors = rules.exception_errors(_binary(artifacts, which))
    assert not errors, scan.report(errors)


@BINARY
def test_no_start_section(artifacts, which) -> None:
    errors = rules.start_section_errors(_binary(artifacts, which))
    assert not errors, scan.report(errors)


def test_plain_reactor_exports(artifacts) -> None:
    errors = rules.export_errors(_binary(artifacts, "plain"), rules.PLAIN_EXPORTS)
    errors += rules.export_type_errors(_binary(artifacts, "plain"))  # spec 055
    assert not errors, scan.report(errors)


def test_snapshot_exports(artifacts) -> None:
    errors = rules.export_errors(
        _binary(artifacts, "snapshot"), rules.SNAPSHOT_EXPORTS, rules.SNAPSHOT_FORBIDDEN
    )
    errors += rules.export_type_errors(_binary(artifacts, "snapshot"))  # spec 055
    assert not errors, scan.report(errors)


def test_manifest_is_well_formed(artifacts) -> None:
    needs.need("manifest")
    m = artifacts.manifest()
    assert not m.errors, scan.report(m.errors)


def test_manifest_pins_match_the_pin_list(artifacts) -> None:
    needs.need("manifest")
    errors = paths.manifest_pin_errors(artifacts.manifest(), paths.read_pin_list())
    assert not errors, scan.report(errors)


def test_manifest_recipes_match_the_tree(artifacts) -> None:
    needs.need("manifest")
    errors = paths.manifest_recipe_errors(artifacts.manifest(), paths.recipe_files())
    assert not errors, scan.report(errors)


def test_manifest_names_the_pre_imports(artifacts) -> None:
    """MANIFEST's `x-preimport` line says what the snapshot pre-imports: the stdlib's bootstrap
    and no package (decision 34; spec 069, check e)."""
    needs.need("manifest")
    lines = artifacts.path("MANIFEST").read_text().splitlines()
    found = [ln.removeprefix("x-preimport ") for ln in lines if ln.startswith("x-preimport ")]
    want = ", ".join(paths.PREIMPORT)
    assert found == [want], f"MANIFEST's x-preimport lines are {found}, not [{want!r}]"


def test_licence_notices_cover_every_component(artifacts) -> None:
    m = artifacts.manifest() if artifacts.path("MANIFEST").is_file() else None
    errors, content, presence = paths.licence_errors(artifacts.dir, m)
    scope = f"content checked: {', '.join(content) or 'none'}; presence only: {', '.join(presence)}"
    assert not errors, scan.report(errors, f"licence notices ({scope})")


def test_tqdm_notice_carries_the_mpl_and_its_source(artifacts) -> None:
    """tqdm ships as bytecode, MPL-2.0's Executable Form, so the set carries its source (the
    pinned wheel, unchanged, as LICENSES/tqdm-<version>-source.whl) and its notice holds the
    full MPL-2.0 text beside the wheel's LICENCE; sympy's notice holds the MIT notice nested in
    its package (spec 039, Decision 8)."""
    errors = rules.tier_a_notice_errors(artifacts.dir)
    assert not errors, scan.report(errors)


def test_cpython_notice_covers_hacl(artifacts) -> None:
    """HACL* is compiled into the binary and CPython's license.rst does not name it (review of
    spec 004, finding 1), so its MIT notice must be in LICENSES/cpython.txt."""
    text = artifacts.path("LICENSES/cpython.txt").read_text(errors="replace")
    assert "HACL* Contributors" in text and "Permission is hereby granted" in text


def test_stdlib_zip_is_bytecode_only_and_deflated(artifacts, metric) -> None:
    needs.need("stdlib zip")
    z = artifacts.path("python-stdlib.zip")
    metric("bytes", z.stat().st_size)
    errors = rules.stdlib_zip_errors(z)
    assert not errors, scan.report(errors)


def test_artifacts_carry_no_build_path(artifacts) -> None:
    """No file in the set holds the checkout's path: it would publish the builder's home
    directory and tie every hash to where the repository was cloned."""
    needle = str(paths.REPO).encode()
    hits = [
        p.name for p in sorted(artifacts.dir.rglob("*")) if p.is_file() and needle in p.read_bytes()
    ]
    with zipfile.ZipFile(artifacts.path("python-stdlib.zip")) as z:  # members are deflated
        hits += [f"python-stdlib.zip:{n}" for n in z.namelist() if needle in z.read(n)]
    assert not hits, scan.report(hits, f"files holding {paths.REPO}")


@BINARY
def test_binaries_hold_no_build_path(artifacts, which) -> None:
    """Neither binary holds the checkout's path or the build user's home folder (spec 046,
    Decision 10): a path compiled in through a `-D` string (libxml2's default catalog, from its
    configure's `--prefix`) or an `assert`'s `__FILE__` names the builder's disk, and no two
    checkouts would give the same bytes. The binary-side twin of the zip's host-fact check."""
    folders = rules.build_folders(paths.REPO, Path.home())
    errors = rules.build_path_errors(_binary(artifacts, which), folders)
    assert not errors, scan.report(errors)


def test_reactor_holds_no_sdk_builder_path(artifacts) -> None:
    """The reactor links the host-neutral wasm runtime, not the one inside the builder's SDK
    tarball, whose assert messages name where that tarball was built (spec 012, Decision 2)."""
    errors = rules.sdk_builder_path_errors(_binary(artifacts, "plain"))
    assert not errors, scan.report(errors)


def test_no_cpython_test_module_is_built_in(guest) -> None:
    """CPython's _test* and xx* modules are test scaffolding, not part of the product."""
    code = (
        "import sys\n"
        "print([m for m in sys.builtin_module_names if m.startswith(('_test', 'xx', '_xx'))])\n"
    )
    r = guest("snapshot", ["-c", code])
    assert (r.exit_code, r.text.strip()) == (0, "[]"), r.text or r.describe()


def test_a_missing_stdlib_module_says_why(guest) -> None:
    """The zip carries _missing_stdlib_info, which CPython's build generates beside
    _sysconfigdata, so a traceback for a stdlib module this platform lacks says why, as native
    CPython's does (spec 086; spec 078's build review, F2). Without it traceback falls back to
    "was not found"."""
    code = (
        "import traceback\n"
        "try:\n"
        "    import _tkinter\n"
        "except ModuleNotFoundError as e:\n"
        "    print(traceback.format_exception_only(e)[-1].strip())\n"
    )
    r = guest("snapshot", ["-c", code])
    want = "ModuleNotFoundError: Unsupported platform for standard library module '_tkinter'"
    assert (r.exit_code, r.text.strip()) == (0, want), r.text or r.describe()


@BINARY
def test_stdlib_c_modules_are_builtin(guest, which) -> None:
    """zlib, _bz2, _lzma and _sqlite3 are linked in as builtins (spec 007). A Setup.local line
    holding `=` is read by makesetup as a Make variable and its module is dropped without an
    error, so only the guest can say the module is there."""
    code = (
        "import sys\n"
        "want = ('zlib', '_bz2', '_lzma', '_sqlite3')\n"
        "print([m for m in want if m not in sys.builtin_module_names])\n"
    )
    r = guest(which, ["-c", code])
    assert (r.exit_code, r.text.strip()) == (0, "[]"), r.text or r.describe()


DOTTED_NAMES = """
import importlib, json, sys
scipy_only = sys.argv[1] == "scipy"
dotted = sorted(
    n for n in sys.builtin_module_names
    if "." in n and (n.split(".")[0] == "scipy") == scipy_only
)
wrong = []
for n in dotted:
    try:
        got = importlib.import_module(n).__name__
    except Exception as e:
        got = f"import {type(e).__name__}"
    if got != n:
        wrong.append([n, got])
print(json.dumps({"dotted": len(dotted), "wrong": wrong}))
"""
# Importing every dotted builtin pulls in most of each package (spec 047, Decision 7): 5.0 G
# fuel on the plain reactor and 0.1 G on the snapshot before regex (its pre-build review's
# finding 10). One program per binary, each with a budget; a figure above half its budget is a
# finding for the build review, and a plain run past its budget is split per top-level package,
# never narrowed to fewer modules. scipy's 95 modules are their own run (spec 037).
DOTTED_FUEL = {"plain": 20_000_000_000, "snapshot": 10_000_000_000}
SCIPY_DOTTED_FUEL = 40_000_000_000
# What native scipy 1.18.1 itself gives, not this build's (EXECUTED under the pinned oracle, spec
# 037's landing notes): `_uarray`'s module definition names it `uarray._uarray`. It equals the
# native answer; nothing of this build is excused. (`_matfuncs_sqrtm_triu` imported first was a
# circular import natively too, until carried patch scipy-1.18.1/0002 moved its import: pydoc's
# apropos imports every builtin.)
SCIPY_NATIVE = {
    "scipy._lib._uarray._uarray": "uarray._uarray",
}
# matplotlib's package needs its data folder and a writable cache folder to import, as in its
# own checks (spec 023): granted here, so its builtins are named like every other.
MPL_ENV = {"MPLCONFIGDIR": "/mplconfig"}


@BINARY
def test_dotted_builtins_keep_their_import_names(guest, which) -> None:
    """Every builtin with a dot in its name imports as a module whose `__name__` is that name, as
    a native import from a shared library gives it (spec 047, Decision 4). CPython gives a builtin
    no package context, so a single-phase module (regex's `_regex`, scipy's f2py modules) keeps
    its short `m_name` unless the inittab's wrapper sets the context around its init function;
    pickle then looks for a top-level module that does not exist. General: a later single-phase
    package is caught the same way, and fixed by a recipe, never by an exemption here."""
    r = guest(
        which, ["-c", DOTTED_NAMES, "rest"], env=MPL_ENV, mpl_data=True, fuel=DOTTED_FUEL[which]
    )
    assert (r.exit_code, r.trapped) == (0, None), r.describe()
    got = json.loads(r.text)
    assert got["dotted"] > 0, r.text
    assert got["wrong"] == [], f"{got['wrong']} (of {got['dotted']} dotted builtins)"


@BINARY
def test_scipys_dotted_builtins_keep_their_import_names(guest, which) -> None:
    """The same for scipy's 95 builtins, in their own run (spec 037): each imports as a module
    named by its dotted name, or as native scipy imports it where native differs (SCIPY_NATIVE)."""
    r = guest(which, ["-c", DOTTED_NAMES, "scipy"], fuel=SCIPY_DOTTED_FUEL)
    assert (r.exit_code, r.trapped) == (0, None), r.describe()
    got = json.loads(r.text)
    assert got["dotted"] > 0, r.text
    wrong = [w for w in got["wrong"] if SCIPY_NATIVE.get(w[0]) != w[1]]
    assert wrong == [], f"{wrong} (of {got['dotted']} dotted builtins)"
    left = sorted(set(SCIPY_NATIVE) - {w[0] for w in got["wrong"]})
    assert not left, f"SCIPY_NATIVE names {left}, which now import under their own names"


REGEX = """
import json, sys
import regex
print(json.dumps({"builtin": "regex._regex" in sys.builtin_module_names,
                  "regex": regex.__version__}))
"""


@BINARY
def test_regex_is_builtin_at_manifest_version(guest, which) -> None:
    """`regex._regex` is a builtin, and regex is the version MANIFEST names (spec 047, Decision
    10)."""
    r = guest(which, ["-c", REGEX])
    assert r.exit_code == 0, r.describe()
    m = paths.parse_manifest((paths.artifact_dir() / "MANIFEST").read_text())
    want = {"builtin": True, "regex": m.packages.get("regex")}
    assert json.loads(r.text) == want, f"guest says {r.text.strip()}, want {want}"


def test_wheel_carries_the_artifact_set(artifacts) -> None:
    needs.need("wheel")
    wheels = sorted(paths.DIST.glob("wasi_python-*.whl"))
    assert len(wheels) == 1, scan.report([w.name for w in wheels], "dist/ must hold one wheel")
    errors = rules.wheel_errors(wheels[0], artifacts.dir)
    assert not errors, scan.report(errors)


def test_static_constructors_are_reviewed(artifacts) -> None:
    """Every function `__wasm_call_ctors` calls is on the reviewed list (spec 023, Decision 8): a
    static constructor runs in `_initialize`, before Python starts, and one that touches Python
    hangs there (matplotlib 3.11.2's ft2font enums did, until carried patch 0001). Read from the
    plain binary's name section, so a new one fails here instead of hanging a run."""
    from harness import constructors, wasm

    mod = wasm.parse_file(_binary(artifacts, "plain"))
    errors = constructors.constructor_errors(mod)
    assert not errors, scan.report(errors, f"constructors {wasm.call_ctors(mod)}")


@BINARY
def test_target_features_are_the_lines(artifacts, which) -> None:
    """`target_features` is exactly the line's ten (spec 023, Decision 8): `+atomics` (which
    `-pthread` adds), `+simd128` or `+tail-call` would each be a new host requirement."""
    from harness import constructors, wasm

    errors = constructors.feature_errors(wasm.parse_file(_binary(artifacts, which)))
    assert not errors, scan.report(errors)


LXML = """
import json, sys
import lxml
from lxml import etree, objectify
dotted = lambda t: ".".join(map(str, t))
print(json.dumps({
    "builtin": [m for m in ("lxml.etree", "lxml.objectify") if m in sys.builtin_module_names],
    "lxml": lxml.__version__,
    "libxml2": dotted(etree.LIBXML_VERSION),
    "libxslt": dotted(etree.LIBXSLT_VERSION),
    "features": sorted(etree.LIBXML_FEATURES & {"iconv", "schematron", "zlib", "thread"}),
}))
"""


@BINARY
def test_lxml_is_builtin_at_manifest_versions(guest, which) -> None:
    """`lxml.etree` and `lxml.objectify` are builtins, and lxml, libxml2 and libxslt are the
    versions MANIFEST names (spec 046, Decision 10). libxml2 converts encodings through
    wasi-libc's iconv and keeps Schematron; it has no zlib and no threads (Decision 3)."""
    r = guest(which, ["-c", LXML])
    assert r.exit_code == 0, r.describe()
    got = json.loads(r.text)
    m = paths.parse_manifest((paths.artifact_dir() / "MANIFEST").read_text())
    want = {
        "builtin": ["lxml.etree", "lxml.objectify"],
        "lxml": m.packages.get("lxml"),
        "libxml2": m.packages.get("libxml2"),
        "libxslt": m.packages.get("libxslt"),
        "features": ["iconv", "schematron"],
    }
    assert got == want, f"guest says {got}, want {want}"
