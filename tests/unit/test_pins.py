"""Zero patches: a source tree against its pinned tarball, on synthetic and real bytes."""

from __future__ import annotations

import hashlib
import io
import shutil
import tarfile
from pathlib import Path

import pytest

from harness import paths, pins


def make_tarball(path: Path, files: dict[str, bytes], links: dict[str, str] = None) -> Path:
    mode = "w:xz" if path.name.endswith(".xz") else "w:gz"
    with tarfile.open(path, mode) as t:
        dirs = {"/".join(n.split("/")[:i]) for n in files for i in range(1, n.count("/") + 1)}
        for d in sorted(dirs):
            info = tarfile.TarInfo(d)
            info.type = tarfile.DIRTYPE
            t.addfile(info)
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
        for name, target in (links or {}).items():
            info = tarfile.TarInfo(name)
            info.type = tarfile.SYMTYPE
            info.linkname = target
            t.addfile(info)
    return path


FILES = {"zlib-9.9/README": b"read me\n", "zlib-9.9/src/z.c": b"int z;\n"}


@pytest.fixture
def pair(work):
    tarball = make_tarball(work / "zlib-9.9.tar.gz", FILES, {"zlib-9.9/link": "README"})
    tree = work / "build" / "zlib-9.9"
    with tarfile.open(tarball) as t:
        t.extractall(work / "build", filter="data")
    return tarball, tree


def test_an_untouched_tree_has_no_drift(pair) -> None:
    assert pins.tree_drift(*pair) == []


def test_a_modified_file_is_drift(pair) -> None:
    tarball, tree = pair
    (tree / "src" / "z.c").write_bytes(b"int z = 1;\n")
    assert pins.tree_drift(tarball, tree) == ["src/z.c: modified"]


def test_a_deleted_file_is_drift(pair) -> None:
    tarball, tree = pair
    (tree / "README").unlink()
    assert pins.tree_drift(tarball, tree) == ["README: missing"]


def test_a_changed_symlink_is_drift(pair) -> None:
    tarball, tree = pair
    (tree / "link").unlink()
    (tree / "link").symlink_to("src/z.c")
    assert pins.tree_drift(tarball, tree) == ["link: symlink changed or missing"]


def test_files_the_build_adds_are_not_judged(pair) -> None:
    tarball, tree = pair
    (tree / "build-wasi").mkdir()
    (tree / "build-wasi" / "out.o").write_bytes(b"\0")
    assert pins.tree_drift(tarball, tree) == []


def test_a_pinned_member_with_a_litter_name_is_named(work) -> None:
    """The build's walks skip a litter name, so a pin that ships one is named by the
    tree check instead of being dropped from the zip without a word."""
    files = {**FILES, "zlib-9.9/src/._z.c": b"\0\5\26\7", "zlib-9.9/.DS_Store": b"Bud1"}
    tarball = make_tarball(work / "zlib-9.9.tar.gz", files)
    with tarfile.open(tarball) as t:
        t.extractall(work / "build", filter="data")
    assert sorted(pins.tree_drift(tarball, work / "build" / "zlib-9.9")) == [
        ".DS_Store: a pinned member with a name only an operating system leaves; the build skips"
        " it",
        "src/._z.c: a pinned member with a name only an operating system leaves; the build skips"
        " it",
    ]


def test_xz_tarballs_are_read_too(work) -> None:
    tarball = make_tarball(work / "Python-9.9.9.tar.xz", {"Python-9.9.9/LICENSE": b"psf\n"})
    with tarfile.open(tarball) as t:
        t.extractall(work, filter="data")
    assert pins.tree_drift(tarball, work / "Python-9.9.9") == []


def test_source_pair_finds_a_pinned_tarball_and_its_tree(pair, work) -> None:
    tarball, _ = pair
    downloads = work / "downloads"
    downloads.mkdir()
    shutil.copy(tarball, downloads / tarball.name)
    sha = hashlib.sha256(tarball.read_bytes()).hexdigest()
    (downloads / "SHA256SUMS").write_text(f"{sha}  {tarball.name}\n")
    assert pins.source_pair("zlib", downloads, work / "build") == (
        downloads / tarball.name,
        work / "build" / "zlib-9.9",
    )
    assert pins.source_pair("numpy", downloads, work / "build") is None


def test_the_cpython_source_is_matched_case_sensitively() -> None:
    assert pins.SOURCE_PATTERNS["cpython"].fullmatch("Python-3.14.8.tar.xz")
    assert not pins.SOURCE_PATTERNS["cpython"].fullmatch("python-3.14.7-wasi_sdk-24.zip")


def test_the_real_zlib_tarball_round_trips_and_a_patch_is_caught(work) -> None:
    tarball = paths.DOWNLOADS / "zlib-1.3.1.tar.gz"
    if not tarball.is_file():
        pytest.skip("zlib-1.3.1.tar.gz is not downloaded")
    assert paths.sha256_file(tarball) == paths.read_pin_list()[tarball.name]
    with tarfile.open(tarball) as t:
        t.extractall(work, filter="data")
    tree = work / "zlib-1.3.1"
    assert pins.tree_drift(tarball, tree) == []
    with (tree / "zconf.h").open("a") as f:
        f.write("/* a patch */\n")
    assert pins.tree_drift(tarball, tree) == ["zconf.h: modified"]


def test_a_subproject_folder_the_tarball_did_not_ship_is_drift(work) -> None:
    """A meson fallback that fetches a subproject leaves its folder under `subprojects/`, and
    builds it in; the folder is the one added file the tree check judges. A subproject the
    tarball ships is no drift, and an added folder anywhere else still is not judged."""
    files = {**FILES, "zlib-9.9/subprojects/shipped/meson.build": b"project('s')\n"}
    tarball = make_tarball(work / "zlib-9.9.tar.gz", files)
    with tarfile.open(tarball) as t:
        t.extractall(work / "build", filter="data")
    tree = work / "build" / "zlib-9.9"
    (tree / "elsewhere" / "x").mkdir(parents=True)
    assert pins.tree_drift(tarball, tree) == []
    (tree / "subprojects" / "x").mkdir()
    (tree / "subprojects" / "x" / "meson.build").write_bytes(b"project('x')\n")
    (tree / "src" / "subprojects" / "y").mkdir(parents=True)
    assert pins.tree_drift(tarball, tree) == [
        f"src/subprojects/y/: {pins.ADDED_SUBPROJECT}",
        f"subprojects/x/: {pins.ADDED_SUBPROJECT}",
    ]
