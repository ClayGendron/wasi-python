"""Host litter (spec 089): a sealed stage refuses a writer, a removal unseals it, and a watched run
names any litter, or any change in a read-only grant. Nothing here needs the artifact set; nothing
measures time."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from harness import litter

BINDS = sys.platform != "win32" and os.geteuid() != 0  # a folder's mode stops a write


def _stage(root: Path) -> Path:
    for rel in ("lib/test/a.py", "lib/test/data/b.txt", "judge/x.json"):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(rel)
    return root


@pytest.mark.parametrize(
    "name, yes",
    [
        (".DS_Store", True),
        ("._a.py", True),
        ("Icon\r", True),
        (".Spotlight-V100", True),
        ("a.py", False),
        (".gitignore", False),
        ("DS_Store", False),
        ("Icon", False),
    ],
)
def test_litter_names(name: str, yes: bool) -> None:
    assert litter.is_litter(name) is yes


@pytest.mark.skipif(not BINDS, reason="a folder's mode does not stop a write on Windows or as root")
def test_a_sealed_stage_refuses_a_writer(tmp_path: Path) -> None:
    root = _stage(tmp_path / "stage")
    litter.seal(root)
    for d in (root, root / "lib", root / "lib/test", root / "lib/test/data", root / "judge"):
        with pytest.raises(PermissionError):
            (d / ".DS_Store").write_bytes(b"Bud1")
    assert litter.litter_in(root) == []
    assert litter.remove(root) is True
    assert not root.exists()


def test_seal_removes_what_landed_while_staging(tmp_path: Path) -> None:
    root = _stage(tmp_path / "stage")
    (root / "lib/.DS_Store").write_bytes(b"Bud1")
    (root / "lib/test/._a.py").write_bytes(b"")
    assert litter.seal(root) == ["lib/.DS_Store", "lib/test/._a.py"]
    assert litter.inventory(root) == {
        "lib/",
        "lib/test/",
        "lib/test/data/",
        "judge/",
        "lib/test/a.py",
        "lib/test/data/b.txt",
        "judge/x.json",
    }
    litter.remove(root)


def test_a_watched_run_names_litter_before(tmp_path: Path) -> None:
    root = _stage(tmp_path / "stage")
    (root / "lib/.DS_Store").write_bytes(b"Bud1")
    with pytest.raises(litter.HostLitter, match=r"/cpython/lib/\.DS_Store \(before the run\)"):
        litter.Watch([(str(root), "/cpython", False)])


def test_a_watched_run_names_any_new_entry_in_a_read_only_grant(tmp_path: Path) -> None:
    root = _stage(tmp_path / "stage")
    w = litter.Watch([(str(root), "/cpython", False)])
    (root / "lib/test/stray.py").write_text("")  # not litter: still a change, still named
    with pytest.raises(litter.HostLitter, match=r"/cpython/lib/test/stray\.py appeared"):
        w.after()


def test_a_watched_run_names_litter_in_a_writable_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    w = litter.Watch([(str(root), "/", True)])
    (root / "made-by-the-guest.txt").write_text("")  # a writable root may change
    w.after()
    (root / ".DS_Store").write_bytes(b"Bud1")
    with pytest.raises(litter.HostLitter, match=r"//?\.DS_Store \(after the run\)"):
        w.after()


@pytest.mark.parametrize("member", ["Lib/test/._a.py", "Lib/test/Icon\r", "Lib/test/.DS_Store/x"])
def test_a_stage_writer_refuses_a_litter_named_member(member: str) -> None:
    with pytest.raises(AssertionError, match="only an operating system leaves"):
        litter.refuse(member, "t.tar")
    litter.refuse("Lib/test/a.py", "t.tar")  # an ordinary member passes
    litter.refuse("Lib/test/x._pth", "t.tar")  # `._` only as a prefix (test_site's `._pth` files)


def test_the_cpython_stage_refuses_a_litter_member(tmp_path: Path) -> None:
    import io
    import tarfile

    from harness import regrtest

    tarball = tmp_path / "Python-9.9.9.tar.xz"
    with tarfile.open(tarball, "w:xz") as t:
        for name in ("Python-9.9.9/Lib/test/a.py", "Python-9.9.9/Lib/test/._a.py"):
            info = tarfile.TarInfo(name)
            info.size = 1
            t.addfile(info, io.BytesIO(b"x"))
    with pytest.raises(AssertionError, match=r"'Lib/test/\._a\.py'"):
        regrtest.stage(tarball, None, tmp_path / "stage")


def test_a_kit_wheel_with_a_litter_member_is_refused(tmp_path: Path) -> None:
    import zipfile

    from harness import upstream

    wheel = tmp_path / "k-1-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as z:
        z.writestr("k/__init__.py", "")
        z.writestr("k/desktop.ini", "")
    with pytest.raises(AssertionError, match="desktop.ini"):
        upstream.safe_unzip(wheel, tmp_path / "kit")


def test_a_runs_stdlib_folder_is_unsealed_after_a_voided_run(work: Path) -> None:
    """Build review F1: a run's sealed stdlib folder never outlives the run sealed, here a run
    the watch voids (a host callback drops litter into the root mid-run). With 083 (the batch)
    `_release` removes it through `litter.remove`, in the `finally` after the watch."""
    from harness import guest, wat

    stdlib = work / "stdlib.zip"
    stdlib.write_bytes(b"PK\x05\x06" + bytes(18))  # an empty zip

    def host(frame: bytes) -> bytes:
        for root in work.glob("run-*/root"):
            (root / ".DS_Store").write_bytes(b"Bud1")
        return frame

    wasm = wat.build(work, "plain.wasm", wat.PLAIN_REACTOR)
    with pytest.raises(litter.HostLitter, match=r"/\.DS_Store \(after the run\)"):
        guest.run(wasm, [], workdir=work, stdlib=stdlib, python_version="3.15", host=host)
    assert list(work.glob("run-*/lib")) == [] and litter.sealed_leftovers(work) == [], (
        litter.sealed_leftovers(work)
    )


@pytest.mark.skipif(not BINDS, reason="a folder's mode does not stop a write on Windows or as root")
def test_sealed_leftovers_are_named(tmp_path: Path) -> None:
    root = _stage(tmp_path / "stage")
    assert litter.sealed_leftovers(tmp_path) == []
    litter.seal(root)
    assert str(root) in litter.sealed_leftovers(tmp_path)
    litter.remove(root)
    assert litter.sealed_leftovers(tmp_path) == []
