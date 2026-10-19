"""The v1.1 rules (MANIFEST, licences, the set itself), each on a good and a bad synthetic artifact
directory (criterion 7). The good set is built here from WAT modules and fake pins."""

from __future__ import annotations

import hashlib
import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from harness import artifacts as rules
from harness import paths, wat


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


PIN_FILES = {
    "Python-3.14.8.tar.xz": b"cpython source",
    "numpy-2.5.2.tar.gz": b"numpy source",
    "pandas-3.0.6.tar.gz": b"pandas source",
    "zlib-1.3.1.tar.gz": b"zlib source",
    "bzip2-1.0.8.tar.gz": b"bzip2 source",
    "xz-5.8.4.tar.gz": b"xz source",
    "sqlite-autoconf-3540100.tar.gz": b"sqlite source",
    "python_dateutil-2.9.0.post0-py2.py3-none-any.whl": b"dateutil wheel",
    "tzdata-2026.5-py2.py3-none-any.whl": b"tzdata wheel",
    "six-1.17.0-py2.py3-none-any.whl": b"six wheel",
    "regex-2026.9.29.tar.gz": b"regex pin",
    "matplotlib-3.11.2.tar.gz": b"matplotlib pin",
    "pillow-13.0.0.tar.gz": b"pillow pin",
    "kiwisolver-1.5.1.tar.gz": b"kiwisolver pin",
    "freetype-2.14.3.tar.xz": b"freetype pin",
    "harfbuzz-14.1.0.tar.xz": b"harfbuzz pin",
    "SheenBidi-3.0.0.tar.gz": b"sheenbidi pin",
    "libraqm-0.10.5.tar.gz": b"libraqm pin",
    "pybind11-3.1.0-py3-none-any.whl": b"pybind11 pin",
    "cppy-1.3.1-py3-none-any.whl": b"cppy pin",
    "cycler-0.12.1-py3-none-any.whl": b"cycler pin",
    "pyparsing-3.3.3-py3-none-any.whl": b"pyparsing pin",
    "packaging-26.3-py3-none-any.whl": b"packaging pin",
    "fonttools-4.67.0-py3-none-any.whl": b"fonttools pin",
    "contourpy-1.4.0.tar.gz": b"contourpy pin",
    "qhull-8.0.2.tar.gz": b"qhull pin",
    "libxml2-2.15.4.tar.xz": b"libxml2 pin",
    "libxslt-1.1.45.tar.xz": b"libxslt pin",
    "lxml-6.1.3.tar.gz": b"lxml pin",
    "openpyxl-3.1.5-py2.py3-none-any.whl": b"openpyxl pin",
    "et_xmlfile-2.0.0-py3-none-any.whl": b"et-xmlfile pin",
    "xlsxwriter-3.2.9-py3-none-any.whl": b"xlsxwriter pin",
    "xlrd-2.0.2-py2.py3-none-any.whl": b"xlrd pin",
    "pypdf-6.21.1-py3-none-any.whl": b"pypdf pin",
    "beautifulsoup4-4.15.0-py3-none-any.whl": b"beautifulsoup4 pin",
    "soupsieve-3.0.3-py3-none-any.whl": b"soupsieve pin",
    "html5lib-1.1-py2.py3-none-any.whl": b"html5lib pin",
    "webencodings-0.6.1-py3-none-any.whl": b"webencodings pin",
    "defusedxml-0.7.1-py2.py3-none-any.whl": b"defusedxml pin",
    "xmltodict-1.0.4-py3-none-any.whl": b"xmltodict pin",
    "pyyaml-6.0.3.tar.gz": b"pyyaml pin",
    "tomli_w-1.2.0-py3-none-any.whl": b"tomli-w pin",
    "jinja2-3.1.6-py3-none-any.whl": b"jinja2 pin",
    "markupsafe-3.0.4.tar.gz": b"markupsafe pin",
    "tabulate-0.10.0-py3-none-any.whl": b"tabulate pin",
    "charset_normalizer-3.5.2-py3-none-any.whl": b"charset-normalizer pin",
    "networkx-3.7.tar.gz": b"networkx pin",
    "patsy-1.0.3-py2.py3-none-any.whl": b"patsy pin",
    "sympy-1.14.0-py3-none-any.whl": b"sympy pin",
    "mpmath-1.3.0-py3-none-any.whl": b"mpmath pin",
    "attrs-26.1.0-py3-none-any.whl": b"attrs pin",
    "more_itertools-11.2.1-py3-none-any.whl": b"more-itertools pin",
    "toolz-1.2.0-py3-none-any.whl": b"toolz pin",
    "tqdm-4.70.1-py3-none-any.whl": b"tqdm pin",
    "typing_extensions-4.16.0-py3-none-any.whl": b"typing-extensions pin",
    "joblib-1.6.0-py3-none-any.whl": b"joblib pin",
    "cloudpickle-3.1.2-py3-none-any.whl": b"cloudpickle pin",
    "threadpoolctl-3.7.0-py3-none-any.whl": b"threadpoolctl pin",
    "narwhals-2.27.1-py3-none-any.whl": b"narwhals pin",
    "wasi-sdk-24.0-arm64-macos.tar.gz": b"sdk",
    "wasmtime-v49.0.3-aarch64-macos.tar.xz": b"wasmtime",
}
PIN_LIST = {name: sha(data) for name, data in PIN_FILES.items()}
PACKAGES = {
    "numpy": "2.5.2",
    "pandas": "3.0.6",
    "zlib": "1.3.1",
    "bzip2": "1.0.8",
    "xz": "5.8.4",
    "sqlite-autoconf": "3540100",
    "python-dateutil": "2.9.0.post0",
    "tzdata": "2026.5",
    "six": "1.17.0",
    "regex": "2026.9.29",
    "matplotlib": "3.11.2",
    "pillow": "13.0.0",
    "kiwisolver": "1.5.1",
    "freetype": "2.14.3",
    "harfbuzz": "14.1.0",
    "sheenbidi": "3.0.0",
    "libraqm": "0.10.5",
    "pybind11": "3.1.0",
    "cppy": "1.3.1",
    "cycler": "0.12.1",
    "pyparsing": "3.3.3",
    "packaging": "26.3",
    "fonttools": "4.67.0",
    "contourpy": "1.4.0",
    "qhull": "8.0.2",
    "libxml2": "2.15.4",
    "libxslt": "1.1.45",
    "lxml": "6.1.3",
    "openpyxl": "3.1.5",
    "et-xmlfile": "2.0.0",
    "xlsxwriter": "3.2.9",
    "xlrd": "2.0.2",
    "pypdf": "6.21.1",
    "beautifulsoup4": "4.15.0",
    "soupsieve": "3.0.3",
    "html5lib": "1.1",
    "webencodings": "0.6.1",
    "defusedxml": "0.7.1",
    "xmltodict": "1.0.4",
    "pyyaml": "6.0.3",
    "tomli-w": "1.2.0",
    "jinja2": "3.1.6",
    "markupsafe": "3.0.4",
    "tabulate": "0.10.0",
    "charset-normalizer": "3.5.2",
    "networkx": "3.7",
    "patsy": "1.0.3",
    "sympy": "1.14.0",
    "mpmath": "1.3.0",
    "attrs": "26.1.0",
    "more-itertools": "11.2.1",
    "toolz": "1.2.0",
    "tqdm": "4.70.1",
    "typing-extensions": "4.16.0",
    "joblib": "1.6.0",
    "cloudpickle": "3.1.2",
    "threadpoolctl": "3.7.0",
    "narwhals": "2.27.1",
}
TREE = {"recipes/a.c": sha(b"a"), "scripts/b.sh": sha(b"b")}


def manifest_text(**drop: bool) -> str:
    lines = ["# built by a test", "x-built-on test", "python 3.14.8"]
    lines += [f"package {k} {v}" for k, v in PACKAGES.items()]
    lines += [f"pin {s} {n}" for n, s in PIN_LIST.items() if n not in drop]
    lines += [f"recipe {s} {p}" for p, s in TREE.items()]
    return "\n".join(lines) + "\n"


def good_set(d: Path) -> Path:
    wat.build(d, "python.wasm", wat.PLAIN_REACTOR)
    wat.build(d, "python-snapshot.wasm", wat.SNAPSHOT)
    with zipfile.ZipFile(d / "python-stdlib.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("os.pyc", b"\0" * 64)
        z.writestr("encodings/__init__.pyc", b"\0" * 64)
    (d / "MANIFEST").write_text(manifest_text())
    (d / "LICENSES").mkdir()
    for c in paths.LICENCE_COMPONENTS:
        (d / "LICENSES" / f"{c}.txt").write_text(f"{c} licence\n")
    write_sums(d)
    return d


def write_sums(d: Path) -> None:
    files = sorted(p for p in d.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    (d / "SHA256SUMS").write_text(
        "".join(f"{paths.sha256_file(p)}  {p.relative_to(d)}\n" for p in files)
    )


@pytest.fixture
def good(work) -> Path:
    return good_set(work / "set")


def test_the_session_exports_have_their_types(good, work) -> None:
    """Spec 055, criterion 26: `turn` is (i32, i32) -> i32 and `shutdown` () -> i32; a set from
    before sessions names both as missing."""
    for b in ("python.wasm", "python-snapshot.wasm"):
        assert rules.export_type_errors(good / b) == []
    old = wat.build(work / "old", "python-snapshot.wasm", wat.BEFORE_SESSIONS)
    assert rules.export_type_errors(old) == [
        "python-snapshot.wasm: no function export shutdown",
        "python-snapshot.wasm: no function export turn",
    ]
    assert rules.export_errors(old, rules.SNAPSHOT_EXPORTS) == [
        "python-snapshot.wasm: no export shutdown",
        "python-snapshot.wasm: no export turn",
    ]


def test_a_good_set_passes_every_rule(good) -> None:
    m = paths.parse_manifest((good / "MANIFEST").read_text())
    assert rules.complete_errors(good) == []
    assert rules.sums_errors(good) == []
    assert rules.cwasm_errors(good) == []
    for b in ("python.wasm", "python-snapshot.wasm"):
        assert rules.is_core_module_errors(good / b) == []
        assert rules.module_errors(good / b) == []
    assert rules.export_errors(good / "python.wasm", rules.PLAIN_EXPORTS) == []
    assert (
        rules.export_errors(
            good / "python-snapshot.wasm", rules.SNAPSHOT_EXPORTS, rules.SNAPSHOT_FORBIDDEN
        )
        == []
    )
    assert m.errors == []
    assert paths.manifest_pin_errors(m, PIN_LIST) == []
    assert paths.manifest_recipe_errors(m, TREE) == []
    assert rules.stdlib_zip_errors(good / "python-stdlib.zip") == []
    assert rules.shared_library_errors(good / "python-stdlib.zip") == []


def test_build_paths_are_named_in_a_binary(work) -> None:
    """Spec 046, Decision 10: a binary holding the checkout's path or the home folder is named,
    with how many times; a shallow home folder is not searched for."""
    b = work / "python.wasm"
    b.write_bytes(b"\0file:///w/repo/build/xml-libs/etc/xml/catalog\0/home/u/x\0/w/repo/a\0")
    folders = rules.build_folders(Path("/w/repo"), Path("/home/u"))
    assert folders == ["/w/repo", "/home/u"]
    assert rules.build_path_errors(b, folders) == [
        "python.wasm: holds '/w/repo' 2 times",
        "python.wasm: holds '/home/u' 1 times",
    ]
    assert rules.build_folders(Path("/w/repo"), Path("/root")) == ["/w/repo"]
    b.write_bytes(b"\0file:///etc/xml/catalog\0")
    assert rules.build_path_errors(b, folders) == []


def test_completeness_names_each_missing_file(good) -> None:
    (good / "python-snapshot.wasm").unlink()
    (good / "LICENSES" / "six.txt").unlink()
    assert rules.complete_errors(good) == [
        "python-snapshot.wasm is missing",
        "LICENSES/six.txt is missing",
    ]


def test_sums_catch_a_changed_an_unlisted_and_a_missing_file(good) -> None:
    (good / "MANIFEST").write_text(manifest_text() + "# edited\n")
    (good / "extra.txt").write_text("x")
    (good / "LICENSES" / "six.txt").unlink()
    assert rules.sums_errors(good) == [
        "extra.txt is not listed in SHA256SUMS",
        "SHA256SUMS lists LICENSES/six.txt, which is absent",
        "MANIFEST does not match its SHA256SUMS line",
    ]


def test_sums_forgive_litter_names_only(good) -> None:
    """Spec 090, Decision 4: a Finder file in the set's folder is no finding; a real stray file
    still is, by name."""
    for rel in (".DS_Store", "LICENSES/._six.txt", ".TemporaryItems/x", "desktop.ini"):
        (good / rel).parent.mkdir(parents=True, exist_ok=True)
        (good / rel).write_bytes(b"litter")
    assert rules.sums_errors(good) == []
    (good / "stray.bin").write_bytes(b"x")
    assert rules.sums_errors(good) == ["stray.bin is not listed in SHA256SUMS"]


def test_a_compiled_module_in_the_set_is_caught(good) -> None:
    (good / "python.cwasm").write_bytes(b"\0")
    assert rules.cwasm_errors(good) == ["python.cwasm is a compiled module"]


def test_a_third_import_breaks_the_wall(good) -> None:
    wat.build(good, "python.wasm", wat.THIRD_IMPORT)
    assert rules.module_errors(good / "python.wasm") == [
        "python.wasm: third import env::sneak (func)"
    ]


def test_a_component_is_not_a_core_module(good) -> None:
    (good / "python.wasm").write_bytes(b"\0asm\x0d\x00\x01\x00")
    assert rules.is_core_module_errors(good / "python.wasm") == [
        "python.wasm: not a core module (version 0d000100)"
    ]


def test_exports_catch_a_missing_and_a_forbidden_name(good) -> None:
    assert rules.export_errors(good / "python-snapshot.wasm", rules.PLAIN_EXPORTS, {"run"}) == [
        "python-snapshot.wasm: no export _initialize",
        "python-snapshot.wasm: no export wizer.initialize",
        "python-snapshot.wasm: exports run",
    ]


def test_manifest_line_rules() -> None:
    m = paths.parse_manifest("python 3.14.8\npython 3.14.9\npins abc x\npackage numpy 2.5.2\n")
    assert "MANIFEST:3: not a python, package, pin or recipe line: 'pins abc x'" in m.errors
    assert "MANIFEST: 2 python lines; exactly one is required" in m.errors
    assert "MANIFEST: no package line for pandas" in m.errors
    assert not any("numpy" in e for e in m.errors)


def test_manifest_pins_must_be_the_pin_list_and_cover_everything() -> None:
    m = paths.parse_manifest(manifest_text())
    wrong = dict(PIN_LIST, **{"numpy-2.5.2.tar.gz": "0" * 64})
    assert paths.manifest_pin_errors(m, wrong) == [
        "pin numpy-2.5.2.tar.gz is not the line in downloads/SHA256SUMS"
    ]
    short = paths.parse_manifest(
        manifest_text(**{"Python-3.14.8.tar.xz": True, "six-1.17.0-py2.py3-none-any.whl": True})
    )
    assert paths.manifest_pin_errors(short, PIN_LIST) == [
        "no pin named Python-3.14.8.tar.xz for python 3.14.8",
        "no pin for package six",
    ]


def test_manifest_versions_must_match_their_pins() -> None:
    m = paths.parse_manifest(manifest_text().replace("package numpy 2.5.2", "package numpy 2.5.3"))
    assert paths.manifest_pin_errors(m, PIN_LIST) == [
        "package numpy 2.5.3 does not match its pin numpy-2.5.2.tar.gz"
    ]


def test_manifest_requires_toolchain_pins() -> None:
    m = paths.parse_manifest(manifest_text(**{"wasmtime-v49.0.3-aarch64-macos.tar.xz": True}))
    assert paths.manifest_pin_errors(m, PIN_LIST) == ["no pin for wasmtime"]


def test_brett_zip_is_never_the_cpython_pin() -> None:
    m = paths.parse_manifest(manifest_text(**{"Python-3.14.8.tar.xz": True}))
    m.pins["python-3.14.8-wasi_sdk-24.zip"] = "1" * 64
    errors = paths.manifest_pin_errors(m, {**PIN_LIST, "python-3.14.8-wasi_sdk-24.zip": "1" * 64})
    assert "no pin named Python-3.14.8.tar.xz for python 3.14.8" in errors


def test_recipes_must_equal_the_tree() -> None:
    m = paths.parse_manifest(manifest_text())
    tree = {"recipes/a.c": sha(b"a2"), "scripts/c.sh": sha(b"c")}
    assert paths.manifest_recipe_errors(m, tree) == [
        "stale artifact: scripts/c.sh is not in MANIFEST",
        "stale artifact: MANIFEST names scripts/b.sh, which the tree does not have",
        "stale artifact: recipes/a.c changed since the build",
    ]


def test_recipe_files_leave_out_benchmarks() -> None:
    files = paths.recipe_files()
    assert "scripts/wasi-cc" in files
    assert not any(Path(f).name.startswith("bench_") for f in files)


def test_stdlib_zip_must_be_bytecode_and_deflated(work) -> None:
    z = work / "bad.zip"
    with zipfile.ZipFile(z, "w") as archive:
        archive.writestr("os.py", "pass")
        archive.writestr("_x.so", b"\0")
    assert rules.stdlib_zip_errors(z) == [
        "os.py: source, not bytecode",
        "os.py: stored, not deflated",
        "_x.so: stored, not deflated",
    ]
    assert rules.shared_library_errors(z) == ["_x.so"]


def _tar_with_licence(path: Path, top: str, text: bytes) -> None:
    with tarfile.open(path, "w:gz") as t:
        info = tarfile.TarInfo(f"{top}/LICENSE")
        info.size = len(text)
        t.addfile(info, io.BytesIO(text))


def test_licences_are_checked_for_content_when_the_source_is_downloaded(
    good, work, monkeypatch
) -> None:
    downloads = work / "downloads"
    downloads.mkdir()
    _tar_with_licence(downloads / "zlib-1.3.1.tar.gz", "zlib-1.3.1", b"the zlib licence\n")
    tar_sha = paths.sha256_file(downloads / "zlib-1.3.1.tar.gz")
    (downloads / "SHA256SUMS").write_text(f"{tar_sha}  zlib-1.3.1.tar.gz\n")
    monkeypatch.setattr(paths, "DOWNLOADS", downloads)
    m = paths.parse_manifest(manifest_text())
    errors, content, presence = paths.licence_errors(good, m)
    assert errors == ["LICENSES/zlib.txt does not contain the licence of zlib-1.3.1.tar.gz"]
    assert content == ["zlib"] and "wasi-libc" in presence
    (good / "LICENSES" / "zlib.txt").write_bytes(b"notice\nthe zlib licence\nmore\n")
    assert paths.licence_errors(good, m)[0] == []
    # A download that does not match its pin is an error, never a silent fallback.
    (downloads / "SHA256SUMS").write_text(f"{'0' * 64}  zlib-1.3.1.tar.gz\n")
    errors = paths.licence_errors(good, m)[0]
    assert errors == ["LICENSES/zlib.txt: downloads/zlib-1.3.1.tar.gz does not match its pin"]


def _tar(path: Path, top: str, files: dict[str, bytes]) -> None:
    with tarfile.open(path, "w:gz") as t:
        for name, data in files.items():
            info = tarfile.TarInfo(f"{top}/{name}")
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))


def test_xz_and_sqlite_notices_must_hold_their_whole_licence(good, work, monkeypatch) -> None:
    """xz's library is under 0BSD, which its top-level COPYING only points to, and SQLite has no
    licence file: their notices must also hold COPYING.0BSD and the blessing that heads
    sqlite3.h, read from the pinned tarballs (spec 007's build review, finding 7). SQLite's pin
    is named sqlite-autoconf, not sqlite."""
    downloads = work / "downloads"
    downloads.mkdir()
    zero_bsd = b"BSD Zero Clause License\n"
    blessing = b"/*\n** The author disclaims copyright to this source code.  In place of\n*/\n"
    _tar(
        downloads / "xz-5.8.4.tar.gz",
        "xz-5.8.4",
        {"COPYING": b"xz: see COPYING.0BSD\n", "COPYING.0BSD": zero_bsd},
    )
    _tar(
        downloads / "sqlite-autoconf-3540100.tar.gz",
        "sqlite-autoconf-3540100",
        {"sqlite3.h": blessing},
    )
    sums = "".join(
        f"{paths.sha256_file(f)}  {f.name}\n" for f in sorted(downloads.glob("*.tar.gz"))
    )
    (downloads / "SHA256SUMS").write_text(sums)
    monkeypatch.setattr(paths, "DOWNLOADS", downloads)
    m = paths.parse_manifest(manifest_text())
    errors, content, presence = paths.licence_errors(good, m)
    assert "xz" in content and "sqlite" in content and "sqlite" not in presence
    assert "LICENSES/xz.txt does not contain the licence of xz-5.8.4.tar.gz" in errors
    assert (
        "LICENSES/sqlite.txt does not contain the licence of sqlite-autoconf-3540100.tar.gz"
        in errors
    )
    (good / "LICENSES" / "xz.txt").write_bytes(b"xz: see COPYING.0BSD\n" + zero_bsd)
    (good / "LICENSES" / "sqlite.txt").write_bytes(blessing)
    errors = paths.licence_errors(good, m)[0]
    assert not [e for e in errors if "xz" in e or "sqlite" in e], errors
    (good / "LICENSES" / "xz.txt").write_bytes(b"xz: see COPYING.0BSD\n")  # 0BSD dropped
    assert (
        "LICENSES/xz.txt does not contain the licence of xz-5.8.4.tar.gz"
        in paths.licence_errors(good, m)[0]
    )


# A cut of GIST's notice as matplotlib ships it in LICENSE/LICENSE_YORICK (the build review's F6).
YORICK = (
    b"BSD-style license for gist/yorick packages.\n"
    b"Copyright (c) 1996.  The Regents of the University of California.\n"
    b"All rights reserved.\n"
    b"Permission is hereby granted, without written agreement and without license or royalty\n"
    b"fees, to use, copy, modify, and distribute this software and its documentation for any\n"
    b"purpose, provided that this entire notice is included in all copies of any software\n"
    b"which is or includes a copy or modification of this software\n"
)


def test_contourpys_notice_holds_gists_and_qhulls_its_copying(good, work, monkeypatch) -> None:
    """contourpy's notice must hold GIST's, which matplotlib's pinned tarball ships as
    LICENSE/LICENSE_YORICK (BORROWED_LICENCE), and qhull's must hold its COPYING.txt, which the
    top-level search does not match (MORE_LICENCE; spec 043, Decision 11)."""
    downloads = work / "downloads"
    downloads.mkdir()
    _tar(downloads / "contourpy-1.4.0.tar.gz", "contourpy-1.4.0", {"LICENSE": b"contourpy BSD\n"})
    mpl = {"LICENSE/LICENSE": b"matplotlib's licence\n", "LICENSE/LICENSE_YORICK": YORICK}
    _tar(downloads / "matplotlib-3.11.2.tar.gz", "matplotlib-3.11.2", mpl)
    _tar(downloads / "qhull-8.0.2.tar.gz", "qhull-8.0.2", {"COPYING.txt": b"Qhull licence\n"})

    def pin() -> None:
        sums = "".join(
            f"{paths.sha256_file(f)}  {f.name}\n" for f in sorted(downloads.glob("*.tar.gz"))
        )
        (downloads / "SHA256SUMS").write_text(sums)

    pin()
    monkeypatch.setattr(paths, "DOWNLOADS", downloads)
    m = paths.parse_manifest(manifest_text())
    errors, content, _ = paths.licence_errors(good, m)
    assert {"contourpy", "qhull"} <= set(content), content
    assert "LICENSES/contourpy.txt does not contain matplotlib's LICENSE/LICENSE_YORICK" in errors
    assert "LICENSES/qhull.txt does not contain the licence of qhull-8.0.2.tar.gz" in errors
    (good / "LICENSES" / "contourpy.txt").write_bytes(b"contourpy BSD\n")  # GIST's notice left out
    errors = paths.licence_errors(good, m)[0]
    assert "LICENSES/contourpy.txt does not contain matplotlib's LICENSE/LICENSE_YORICK" in errors
    (good / "LICENSES" / "contourpy.txt").write_bytes(b"contourpy BSD\n" + YORICK)
    (good / "LICENSES" / "qhull.txt").write_bytes(b"Qhull licence\n")
    errors = paths.licence_errors(good, m)[0]
    assert not [e for e in errors if "contourpy" in e or "qhull" in e], errors
    mpl.pop("LICENSE/LICENSE_YORICK")  # a matplotlib without the notice
    _tar(downloads / "matplotlib-3.11.2.tar.gz", "matplotlib-3.11.2", mpl)
    pin()
    errors = paths.licence_errors(good, m)[0]
    assert (
        "LICENSES/contourpy.txt: matplotlib-3.11.2.tar.gz holds no LICENSE/LICENSE_YORICK" in errors
    ), errors


def test_an_empty_licence_file_fails(good, work, monkeypatch) -> None:
    monkeypatch.setattr(paths, "DOWNLOADS", work / "no-downloads")
    (good / "LICENSES" / "numpy.txt").write_text("")
    assert paths.licence_errors(good, None)[0] == ["LICENSES/numpy.txt is missing or empty"]


def test_a_wheel_must_carry_the_same_bytes(good, work) -> None:
    wheel = work / "wasi_python-0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as w:
        w.writestr(rules.TYPED, b"")
        for p in good.rglob("*"):
            if p.is_file():
                w.writestr(
                    f"wasi_python/artifacts/{p.relative_to(good).as_posix()}", p.read_bytes()
                )
    assert rules.wheel_errors(wheel, good) == []
    (good / "MANIFEST").write_text("changed\n")
    assert rules.wheel_errors(wheel, good) == [
        f"{wheel.name}: wasi_python/artifacts/MANIFEST differs from the artifact set"
    ]


def test_a_wheel_carries_the_list_and_nothing_else(good, work) -> None:
    """Spec 090, Decision 4: litter in the folder is forgiven, but a wheel member the set's list
    does not name is not, litter or not (the wheel is built with `cp -R build/artifacts`)."""
    wheel = work / "wasi_python-0-py3-none-any.whl"

    def build(extra: dict[str, bytes]) -> None:
        with zipfile.ZipFile(wheel, "w") as w:
            w.writestr(rules.TYPED, b"")
            for p in good.rglob("*"):
                if p.is_file() and not paths.has_litter(p.relative_to(good).as_posix()):
                    w.writestr(
                        f"wasi_python/artifacts/{p.relative_to(good).as_posix()}", p.read_bytes()
                    )
            for rel, data in extra.items():
                w.writestr(f"wasi_python/artifacts/{rel}", data)

    build({})
    (good / ".DS_Store").write_bytes(b"litter")
    (good / "LICENSES" / "._six.txt").write_bytes(b"litter")
    assert rules.wheel_errors(wheel, good) == []
    build({"Thumbs.db": b"x", "stray.bin": b"y"})
    assert rules.wheel_errors(wheel, good) == [
        f"{wheel.name} carries wasi_python/artifacts/Thumbs.db, which SHA256SUMS does not list",
        f"{wheel.name} carries wasi_python/artifacts/stray.bin, which SHA256SUMS does not list",
    ]


def test_a_wheel_must_carry_py_typed(good, work) -> None:
    """Spec 049, criterion 8: without `py.typed` a type checker treats the package as untyped."""
    wheel = work / "wasi_python-0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as w:
        for p in good.rglob("*"):
            if p.is_file():
                w.writestr(
                    f"wasi_python/artifacts/{p.relative_to(good).as_posix()}", p.read_bytes()
                )
    assert rules.wheel_errors(wheel, good) == [f"{wheel.name} lacks wasi_python/py.typed"]


def test_exception_rule_passes_the_standard_form(work) -> None:
    assert rules.exception_errors(wat.build(work, "eh.wasm", wat.EXCEPTIONS)) == []


def test_exception_rule_names_a_module_without_exceptions(work) -> None:
    assert rules.exception_errors(wat.build(work, "python.wasm", wat.PLAIN_REACTOR)) == [
        "python.wasm: no tag section (no exception tag defined)",
        "python.wasm: validates with exceptions off (no exception handling)",
    ]


def test_start_section_rule_names_a_start_function(work) -> None:
    assert rules.start_section_errors(wat.build(work, "s.wasm", wat.WITH_START)) == [
        "s.wasm: has a start section (guest code would run unmetered)"
    ]
    assert rules.start_section_errors(wat.build(work, "p.wasm", wat.PLAIN_REACTOR)) == []


def _zip_of(path: Path, members: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            z.writestr(name, data)
    return path


def test_host_facts_in_the_three_members_are_named(work) -> None:
    sysconfig, config, contourpy = rules.HOST_FACT_MEMBERS
    neutral = {
        sysconfig: b"BUILD_GNU_TYPE build HAVE_LINUX_CAN_H /wasi-python-build/x",
        config: b"cpu build family build endian little system build",
        contourpy: b"build_cpu build build_cpu_system build /wasi-python-build",
    }
    assert rules.host_fact_errors(_zip_of(work / "a.zip", neutral), "/home/me/repo") == []
    leaky = {
        sysconfig: b"aarch64-apple-darwin /usr/bin/install -c /home/me/repo/build",
        config: b"system linux",
        contourpy: b"build_cpu_system linux build_cpu aarch64 /home/me/repo/build",
    }
    assert rules.host_fact_errors(_zip_of(work / "b.zip", leaky), "/home/me/repo") == [
        f"{sysconfig}: holds 'darwin'",
        f"{sysconfig}: holds 'apple'",
        f"{sysconfig}: holds 'aarch64'",
        f"{sysconfig}: holds '/usr/bin'",
        f"{sysconfig}: holds '/home/me/repo'",
        f"{config}: holds 'linux'",
        f"{contourpy}: holds 'aarch64'",
        f"{contourpy}: holds 'linux'",
        f"{contourpy}: holds '/home/me/repo'",
    ]
    assert rules.host_fact_errors(_zip_of(work / "c.zip", {config: b""}), "/r") == [
        f"{sysconfig}: not in the zip",
        f"{contourpy}: not in the zip",
    ]


def test_a_reactor_with_the_sdk_tarball_runtime_is_named(work) -> None:
    good = work / "good.wasm"
    good.write_bytes(b"\0asm/src/src/llvm-project/libcxxabi/src/fallback_malloc.cpp")
    bad = work / "bad.wasm"
    bad.write_bytes(b"\0asm/Users/runner/work/wasi-sdk/wasi-sdk/src/llvm-project/x.cpp")
    assert rules.sdk_builder_path_errors(good) == []
    assert rules.sdk_builder_path_errors(bad) == ["bad.wasm: holds /Users/runner/work/wasi-sdk"]


def _tier_a_set(work: Path) -> Path:
    """A set with tqdm's and sympy's notices as step 90 writes them, its MANIFEST naming the pins:
    no downloads/, as in the release's judge shards."""
    d = work / "tier-a-set"
    (d / "LICENSES").mkdir(parents=True)
    licence = b"MIT, and MPL-2.0 Exhibit A\n"
    mpl = b"Mozilla Public License Version 2.0\n==========\n"
    source = d / "LICENSES" / "tqdm-4.70.1-source.whl"
    with zipfile.ZipFile(source, "w") as z:
        z.writestr("tqdm/__init__.py", "")
        z.writestr("tqdm-4.70.1.dist-info/licenses/LICENCE", licence)
    with zipfile.ZipFile(d / "python-stdlib.zip", "w") as z:
        z.writestr(rules.SYMPY_NESTED, "Copyright 2016, latex2sympy\n")
    wheel_sha = paths.sha256_file(source)
    (d / "MANIFEST").write_text(
        "python 3.15.0\npackage tqdm 4.70.1\npackage sympy 1.14.0\n"
        f"pin {wheel_sha} tqdm-4.70.1-py3-none-any.whl\npin {sha(mpl)} {rules.MPL_TEXT}\n"
    )
    parts = [
        ("tqdm-4.70.1-py3-none-any.whl: tqdm-4.70.1.dist-info/licenses/LICENCE", licence),
        (f"Mozilla Public License 2.0, the full text ({rules.MPL_TEXT})", mpl),
        ("tqdm source", f"LICENSES/tqdm-4.70.1-source.whl, SHA-256 {wheel_sha}\n".encode()),
    ]
    (d / "LICENSES" / "tqdm.txt").write_bytes(
        b"".join(f"==== {label} ====\n".encode() + data + b"\n" for label, data in parts)
    )
    (d / "LICENSES" / "sympy.txt").write_text("BSD\n\nCopyright 2016, latex2sympy\n")
    return d


def test_tqdm_notice_carries_the_mpl_and_its_source(work) -> None:
    """Spec 039, criterion 1: the rule passes the set step 90 writes, with no downloads/, and names
    each mutant: the MPL text missing or one byte changed, the carried source missing or one byte
    changed, and sympy's notice without its nested MIT notice."""
    d = _tier_a_set(work)
    assert rules.tier_a_notice_errors(d) == []
    notice, carried = d / "LICENSES" / "tqdm.txt", d / "LICENSES" / "tqdm-4.70.1-source.whl"
    good_notice, good_source = notice.read_bytes(), carried.read_bytes()
    no_mpl = [f"LICENSES/tqdm.txt does not hold the MPL-2.0 text of {rules.MPL_TEXT}"]

    notice.write_bytes(good_notice.replace(b"Mozilla Public License Version 2.0\n", b""))
    assert rules.tier_a_notice_errors(d) == no_mpl
    notice.write_bytes(good_notice.replace(b"==========", b"=========-"))
    assert rules.tier_a_notice_errors(d) == no_mpl
    notice.write_bytes(good_notice)
    carried.unlink()
    assert rules.tier_a_notice_errors(d) == ["LICENSES/tqdm-4.70.1-source.whl is missing"]
    carried.write_bytes(good_source[:-1] + bytes([good_source[-1] ^ 1]))
    assert rules.tier_a_notice_errors(d) == [
        "LICENSES/tqdm-4.70.1-source.whl is not the pinned tqdm-4.70.1-py3-none-any.whl "
        "that MANIFEST names"
    ]
    carried.write_bytes(good_source)
    (d / "LICENSES" / "sympy.txt").write_text("BSD\n")
    assert rules.tier_a_notice_errors(d) == [
        f"LICENSES/sympy.txt does not hold {rules.SYMPY_NESTED} as the zip carries it"
    ]
