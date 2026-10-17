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
    "python_dateutil-2.9.0.post0-py2.py3-none-any.whl": b"dateutil wheel",
    "tzdata-2026.5-py2.py3-none-any.whl": b"tzdata wheel",
    "six-1.17.0-py2.py3-none-any.whl": b"six wheel",
    "wasi-sdk-24.0-arm64-macos.tar.gz": b"sdk",
    "wasmtime-v49.0.3-aarch64-macos.tar.xz": b"wasmtime",
}
PIN_LIST = {name: sha(data) for name, data in PIN_FILES.items()}
PACKAGES = {
    "numpy": "2.5.2",
    "pandas": "3.0.6",
    "zlib": "1.3.1",
    "python-dateutil": "2.9.0.post0",
    "tzdata": "2026.5",
    "six": "1.17.0",
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


def test_an_empty_licence_file_fails(good, work, monkeypatch) -> None:
    monkeypatch.setattr(paths, "DOWNLOADS", work / "no-downloads")
    (good / "LICENSES" / "numpy.txt").write_text("")
    assert paths.licence_errors(good, None)[0] == ["LICENSES/numpy.txt is missing or empty"]


def test_a_wheel_must_carry_the_same_bytes(good, work) -> None:
    wheel = work / "wasi_python-0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as w:
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
