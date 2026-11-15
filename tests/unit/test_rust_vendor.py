"""The directory source cargo reads offline: each pinned crate unpacked with every file's
SHA-256, and rust-src's vendored crates beside them. The archives are made here, as crates.io lays
them out."""

from __future__ import annotations

import hashlib
import io
import json
import sys
import tarfile

from harness import paths

sys.path.insert(0, str(paths.REPO / "scripts"))

import rust_vendor  # noqa: E402

LOCK = """version = 4

[[package]]
name = "itoap"
version = "1.0.1"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "{sha}"

[[package]]
name = "orjson"
version = "3.13.0"
dependencies = [
 "itoap",
]
"""


def _crate(members: dict[str, bytes], top: str = "itoap-1.0.1") -> bytes:
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:gz") as tar:
        for name, body in members.items():
            info = tarfile.TarInfo(f"{top}/{name}" if not name.startswith("/") else name)
            info.size = len(body)
            tar.addfile(info, io.BytesIO(body))
    return out.getvalue()


def _layout(tmp_path, data: bytes, pin: str | None = None, lock_sha: str | None = None):
    sha = hashlib.sha256(data).hexdigest()
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    (downloads / "itoap-1.0.1.crate").write_bytes(data)
    sums = downloads / "SHA256SUMS"
    sums.write_text(f"{pin or sha}  itoap-1.0.1.crate\n")
    lock = tmp_path / "Cargo.lock"
    lock.write_text(LOCK.format(sha=lock_sha or sha))
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    return [str(lock), str(sums), str(downloads), str(vendor)], vendor, sha


def test_the_lock_names_its_crates_io_packages_only() -> None:
    assert rust_vendor.lock_crates(LOCK.format(sha="ab")) == [("itoap", "1.0.1", "ab")]


def test_a_pinned_crate_unpacks_with_every_files_checksum(tmp_path) -> None:
    files = {"Cargo.toml": b"[package]\n", "src/lib.rs": b"//\n", ".gitignore": b"target\n"}
    argv, vendor, sha = _layout(tmp_path, _crate(files))
    assert rust_vendor.crates_main(argv) == 0
    body = json.loads((vendor / "itoap-1.0.1" / ".cargo-checksum.json").read_text())
    assert body["package"] == sha
    assert body["files"] == {
        "Cargo.toml": hashlib.sha256(b"[package]\n").hexdigest(),
        "src/lib.rs": hashlib.sha256(b"//\n").hexdigest(),
    }
    assert not (vendor / "itoap-1.0.1" / ".gitignore").exists()


def test_a_crate_whose_pin_or_lock_disagrees_stops_the_step(tmp_path, capsys) -> None:
    argv, _, _ = _layout(tmp_path, _crate({"Cargo.toml": b""}), lock_sha="0" * 64)
    assert rust_vendor.crates_main(argv) == 1
    assert "is not the lock's checksum" in capsys.readouterr().out


def test_a_member_outside_the_crates_folder_is_refused(tmp_path) -> None:
    import pytest

    archive = tmp_path / "x.crate"
    archive.write_bytes(_crate({"Cargo.toml": b""}, top="other-1.0.0"))
    with pytest.raises(ValueError, match="outside"):
        rust_vendor.unpack_crate(archive, "itoap-1.0.1", tmp_path / "out")


def test_rust_srcs_crates_join_and_a_differing_one_stops(tmp_path, capsys) -> None:
    source, vendor = tmp_path / "library-vendor", tmp_path / "vendor"
    for root in (source / "cfg-if-1.0.4", source / "gimli-0.34.0", vendor / "gimli-0.34.0"):
        root.mkdir(parents=True)
        (root / ".cargo-checksum.json").write_text("{}")
        (root / "Cargo.toml").write_text("[package]\n")
    assert rust_vendor.std_main([str(source), str(vendor)]) == 0
    assert (vendor / "cfg-if-1.0.4" / "Cargo.toml").is_file()
    (vendor / "gimli-0.34.0" / "Cargo.toml").write_text("[package] # changed\n")
    assert rust_vendor.std_main([str(source), str(vendor)]) == 1
    assert "gimli-0.34.0 differs" in capsys.readouterr().out
