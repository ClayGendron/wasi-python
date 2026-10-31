"""`packages()` and `Package`: the Python packages a set carries, read from its zip on the host.

Each row writes its own zip, so no artifact set is needed, and counts opens rather than time."""

from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

import wasi_python
from wasi_python import Artifacts, ArtifactsMissing, Package, _packages, packages


def _metadata(name: str | None, version: str | None) -> bytes:
    rows = ["Metadata-Version: 2.1"]
    rows += [f"Name: {name}"] if name is not None else []
    rows += [f"Version: {version}"] if version is not None else []
    return ("\n".join(rows) + "\n\nA description.\n").encode()


def _set(folder: Path, members: dict[str, bytes]) -> Artifacts:
    """A set whose zip holds the members; the other three files are never read."""
    folder.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(folder / "python-stdlib.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            z.writestr(name, data)
    return Artifacts(
        snapshot=folder / "python-snapshot.wasm",
        plain=folder / "python.wasm",
        stdlib_zip=folder / "python-stdlib.zip",
        manifest=folder / "MANIFEST",
    )


THREE = {
    "os.pyc": b"",
    "zeta_pkg-2.0.dist-info/METADATA": _metadata("Zeta.Pkg", "2.0"),
    "zeta_pkg-2.0.dist-info/top_level.txt": b"zeta\n",
    "alpha_beta-1.0.dist-info/METADATA": _metadata("alpha_beta", "1.0"),
    "alpha_beta-1.0.dist-info/top_level.txt": b"beta\nalpha\n",
    "alpha_gamma-0.1.dist-info/METADATA": _metadata("Alpha-Gamma", "0.1"),
    "alpha/__init__.pyc": b"",
}


def test_each_distribution_in_normalized_order_with_its_name_as_written(tmp_path) -> None:
    """Sorted by the normalized name (alpha-beta, alpha-gamma, zeta-pkg), each Name as its
    METADATA writes it, the imports sorted from top_level.txt, and () without one."""
    assert packages(_set(tmp_path, THREE)) == (
        Package("alpha_beta", "1.0", ("alpha", "beta")),
        Package("Alpha-Gamma", "0.1", ()),
        Package("Zeta.Pkg", "2.0", ("zeta",)),
    )


def test_str_is_the_line_for_a_prompt() -> None:
    assert str(Package("scikit-learn", "1.9.1", ("sklearn",))) == (
        "scikit-learn 1.9.1 (import sklearn)"
    )
    assert str(Package("attrs", "26.1.0", ("attr", "attrs"))) == (
        "attrs 26.1.0 (import attr, attrs)"
    )
    assert str(Package("tzdata", "2026.6", ())) == "tzdata 2026.6"


@pytest.mark.parametrize(
    ("name", "version"), [(None, "1.0"), ("x", None), ("", "1.0")], ids=["name", "version", "empty"]
)
def test_a_missing_name_or_version_raises_naming_the_folder(tmp_path, name, version) -> None:
    found = _set(tmp_path, {"x-1.0.dist-info/METADATA": _metadata(name, version)})
    with pytest.raises(ArtifactsMissing, match=r"x-1\.0\.dist-info has no Name or no Version"):
        packages(found)


def test_a_folder_with_no_metadata_raises(tmp_path) -> None:
    found = _set(tmp_path, {"x-1.0.dist-info/top_level.txt": b"x\n"})
    with pytest.raises(ArtifactsMissing, match=r"x-1\.0\.dist-info has no Name"):
        packages(found)


def test_a_member_over_one_mib_raises(tmp_path) -> None:
    big = _metadata("x", "1.0") + b"x" * _packages.MEMBER_BYTES
    found = _set(tmp_path, {"x-1.0.dist-info/METADATA": big})
    with pytest.raises(ArtifactsMissing, match=r"x-1\.0\.dist-info/METADATA holds \d+ bytes"):
        packages(found)
    # A large member outside every .dist-info folder is not read, so it is no matter.
    fine = _set(tmp_path / "fine", {"x/data.bin": b"\0" * (_packages.MEMBER_BYTES + 1)})
    assert packages(fine) == ()


@pytest.mark.parametrize(
    "members",
    [
        {"x-1.dist-info/METADATA": b"Name: x\x1b[2J\nVersion: 1\n\n"},
        {"x-1.dist-info/METADATA": b"Name: x\nVersion: 1\x00\n\n"},
        {"x-1.dist-info/METADATA": "Name: x\u2028y\nVersion: 1\n\n".encode()},
        {"x-1.dist-info/METADATA": _metadata("x", "1"), "x-1.dist-info/top_level.txt": b"a\x07b"},
    ],
    ids=["name", "version", "line-separator", "import"],
)
def test_a_control_character_raises_naming_the_folder(tmp_path, members) -> None:
    """A line of a prompt is never split or rewritten by what a set's metadata holds."""
    with pytest.raises(ArtifactsMissing, match=r"x-1\.dist-info: .* holds a control character"):
        packages(_set(tmp_path, members))


def test_a_zip_that_cannot_be_read_raises(tmp_path) -> None:
    found = _set(tmp_path, {})
    found.stdlib_zip.write_bytes(b"not a zip")
    with pytest.raises(ArtifactsMissing, match="cannot be read"):
        packages(found)
    found.stdlib_zip.unlink()
    with pytest.raises(ArtifactsMissing, match="cannot be read"):
        packages(found)


def _broken(path: Path, how: str) -> None:
    """A one-member zip whose METADATA cannot be read: its deflated bytes are not a deflate
    stream, its central header names compression method 99, or it sets the encrypted flag."""
    member = "x-1.dist-info/METADATA"
    method = zipfile.ZIP_DEFLATED if how == "bad deflate" else zipfile.ZIP_STORED
    with zipfile.ZipFile(path, "w", method) as z:
        z.writestr(member, _metadata("x", "1") * 4)
    data = bytearray(path.read_bytes())
    central = data.index(b"PK\x01\x02")
    if how == "bad deflate":
        start = 30 + len(member)  # the one local header, which carries no extra field
        data[start : start + 8] = b"\xff" * 8  # block type 3, which deflate reserves
    elif how == "method 99":
        data[central + 10 : central + 12] = (99).to_bytes(2, "little")
    else:
        data[central + 8] |= 0x01
    path.write_bytes(bytes(data))


@pytest.mark.parametrize("how", ["bad deflate", "method 99", "encrypted"])
def test_a_member_that_cannot_be_read_raises_artifacts_missing(tmp_path, how) -> None:
    """Whatever the zip module raises for a member it cannot read, `packages()` raises the one
    error it promises, with the cause chained."""
    found = _set(tmp_path, {})
    _broken(found.stdlib_zip, how)
    with pytest.raises(ArtifactsMissing, match="cannot be read") as raised:
        packages(found)
    assert raised.value.__cause__ is not None


def test_a_second_call_on_the_same_zip_opens_nothing(tmp_path, monkeypatch) -> None:
    opened = []

    class Counting(zipfile.ZipFile):
        def __init__(self, *args, **kwargs) -> None:
            opened.append(args[0])
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(_packages, "ZipFile", Counting)
    found = _set(tmp_path, THREE)
    first = packages(found)
    assert len(opened) == 1
    assert packages(found) is first and len(opened) == 1
    # Rewritten in place, even at the same size and modification time, it is read again.
    stat = os.stat(found.stdlib_zip)
    _set(tmp_path, {**THREE, "zeta_pkg-2.0.dist-info/top_level.txt": b"zetb\n"})
    os.utime(found.stdlib_zip, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    again = packages(found)
    assert len(opened) == 2 and again[-1] == Package("Zeta.Pkg", "2.0", ("zetb",))


def test_none_finds_the_set_and_anything_else_is_a_type_error(tmp_path, monkeypatch) -> None:
    found = _set(tmp_path, THREE)
    found.manifest.write_text("python 3.15.2\n")
    monkeypatch.setenv("WASI_PYTHON_ARTIFACTS", str(tmp_path))
    assert packages() == packages(found)
    with pytest.raises(TypeError, match="Artifacts or None; got str"):
        packages(str(tmp_path))  # type: ignore[arg-type]
    monkeypatch.setenv("WASI_PYTHON_ARTIFACTS", str(tmp_path / "absent"))
    with pytest.raises(ArtifactsMissing):
        packages()


def test_packages_loads_no_wasmtime(tmp_path) -> None:
    found = _set(tmp_path, THREE)
    files = [str(found.snapshot), str(found.plain), str(found.stdlib_zip), str(found.manifest)]
    program = (
        "import pathlib, sys, wasi_python\n"
        f"found = wasi_python.Artifacts(*map(pathlib.Path, {files!r}))\n"
        "print(len(wasi_python.packages(found)), 'wasmtime' in sys.modules)\n"
    )
    package_root = Path(wasi_python.__file__).resolve().parent.parent
    env = {**os.environ, "PYTHONPATH": str(package_root)}
    out = subprocess.run(
        [sys.executable, "-c", program], capture_output=True, text=True, env=env, check=True
    )
    assert out.stdout.split() == ["3", "False"], out
