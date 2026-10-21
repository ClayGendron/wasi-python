"""The runner checks a set it finds against the set's own SHA256SUMS before using it.
A set the caller passes is the caller's own."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

import wasi_python
from harness import wat
from wasi_python import ArtifactsMissing, _artifacts, _engines, runner
from wasi_python._process import process


def _sums(folder: Path) -> None:
    names = ["MANIFEST", "python-snapshot.wasm", "python-stdlib.zip", "python.wasm"]
    lines = [f"{hashlib.sha256((folder / n).read_bytes()).hexdigest()}  {n}\n" for n in names]
    (folder / "SHA256SUMS").write_text("".join(lines))


@pytest.fixture
def found(work, monkeypatch) -> Path:
    """A small set at $WASI_PYTHON_ARTIFACTS: a door-probing snapshot, an empty zip, its sums."""
    folder = work / "set"
    wat.build(folder, "python-snapshot.wasm", wat.SNAPSHOT)
    wat.build(folder, "python.wasm", wat.PLAIN_REACTOR)
    (folder / "MANIFEST").write_text("python 3.15.0\n")
    with zipfile.ZipFile(folder / "python-stdlib.zip", "w"):
        pass
    _sums(folder)
    monkeypatch.setenv(_artifacts._ARTIFACTS_ENV, str(folder))
    return folder


def test_a_found_set_that_matches_its_sums_runs(found) -> None:
    assert runner.run([], cache_dir=False).exit_code == 101  # the door: no host


@pytest.mark.parametrize("name", ["python-snapshot.wasm", "python-stdlib.zip", "MANIFEST"])
def test_a_found_file_that_differs_from_its_sums_is_refused(found, name) -> None:
    before = runner.stats()["compiled"]
    path = found / name
    if name == "python-snapshot.wasm":
        wat.build(found, name, wat.COMMAND_EXIT_7)  # another program in its place
    elif name == "MANIFEST":
        path.write_text("python 3.15.0\nrecipe 0000 planted\n")
    else:
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("sitecustomize.py", "print('planted')\n")
    with pytest.raises(ArtifactsMissing, match=f"{name}.*SHA256SUMS"):
        runner.run([], cache_dir=False)
    assert runner.stats()["compiled"] == before  # refused before it is compiled


def test_a_found_set_without_sums_is_refused(found) -> None:
    (found / "SHA256SUMS").unlink()
    with pytest.raises(ArtifactsMissing, match="SHA256SUMS"):
        runner.run([], cache_dir=False)


def test_a_session_checks_a_found_set_too(found) -> None:
    wat.build(found, "python-snapshot.wasm", wat.COMMAND_EXIT_7)
    with pytest.raises(ArtifactsMissing, match="python-snapshot.wasm.*SHA256SUMS"):
        wasi_python.Session(cache_dir=False)


def test_a_set_the_caller_passes_is_its_own(found) -> None:
    """`run(artifacts=…)` takes the caller's four paths as they are, as the judge's door probes
    and older sets do: the caller chose them."""
    wat.build(found, "python-snapshot.wasm", wat.SNAPSHOT)
    (found / "SHA256SUMS").unlink()
    given = wasi_python.artifacts()
    assert runner.run([], artifacts=given, cache_dir=False).exit_code == 101


# A file swapped after the check, by a writer of the set's folder
# during a call, is refused too; the checked digest binds the bytes the call compiles and the
# zip the guest reads, and a .cwasm is written only from checked bytes.
PLANTED = wat.SNAPSHOT.replace(wat.DOOR_RUN, '(func (export "run") (result i32) (i32.const 42))')


@pytest.fixture
def fresh(monkeypatch) -> None:
    """No module or zip this process already holds, so each case compiles and copies anew."""
    monkeypatch.setattr(process(), "modules", {})
    monkeypatch.setattr(process(), "zips", {})


def _swap_after_check(monkeypatch, swap) -> None:
    real = _artifacts._found_and_checked

    def checked_then_swapped(snapshot):
        out = real(snapshot)
        swap()
        return out

    monkeypatch.setattr(_artifacts, "_found_and_checked", checked_then_swapped)


def test_a_binary_swapped_after_the_check_is_not_compiled(found, fresh, monkeypatch) -> None:
    _swap_after_check(monkeypatch, lambda: wat.build(found, "python-snapshot.wasm", PLANTED))
    before = runner.stats()["compiled"]
    with pytest.raises(ArtifactsMissing, match="changed after it was checked"):
        runner.run([], cache_dir=False)
    assert runner.stats()["compiled"] == before


def test_a_binary_swapped_before_its_compile_leaves_no_cwasm(found, fresh, work, monkeypatch):
    cache = work / "cache"
    cache.mkdir(mode=0o700)
    good = (found / "python-snapshot.wasm").read_bytes()
    real = _engines._module_miss

    def swapped_first(*args):
        wat.build(found, "python-snapshot.wasm", PLANTED)
        return real(*args)

    monkeypatch.setattr(_engines, "_module_miss", swapped_first)
    with pytest.raises(ArtifactsMissing, match="changed after it was checked"):
        runner.run([], cache_dir=cache)
    assert list(cache.glob("*.cwasm")) == []
    monkeypatch.setattr(_engines, "_module_miss", real)
    (found / "python-snapshot.wasm").write_bytes(good)  # the set put right
    assert runner.run([], cache_dir=cache).exit_code == 101  # the checked module, cached anew
    assert len(list(cache.glob("*.cwasm"))) == 1


def test_a_zip_swapped_after_the_check_never_reaches_the_guest(found, fresh, monkeypatch) -> None:
    def swap() -> None:
        with zipfile.ZipFile(found / "python-stdlib.zip", "w") as z:
            z.writestr("sitecustomize.py", "print('planted')\n")

    _swap_after_check(monkeypatch, swap)
    with pytest.raises(RuntimeError, match="is not the artifact set's"):
        runner.run([], cache_dir=False)


# The caches in front of the check key on the file's whole stamp (device, inode, size, both
# times), the one `_stamp` gives: a replacement of the same size and modification time is
# hashed again, and a MANIFEST rewritten in place is read again. Opens are counted, never time.


def _opens(monkeypatch) -> list[str]:
    import os

    opened: list[str] = []
    real = os.open

    def counting(path, *args, **kwargs):
        opened.append(os.fspath(path))
        return real(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", counting)
    return opened


def test_a_same_size_same_mtime_replacement_is_hashed_again(tmp_path, monkeypatch) -> None:
    import os

    first, second = b"a" * 100, b"b" * 100
    target, other = tmp_path / "python.wasm", tmp_path / "replacement"
    target.write_bytes(first)
    opened = _opens(monkeypatch)
    assert _artifacts._digest(target) == hashlib.sha256(first).hexdigest()
    other.write_bytes(second)
    st = target.stat()
    os.utime(other, ns=(st.st_atime_ns, st.st_mtime_ns))  # the same size, the same mtime
    os.replace(other, target)
    assert target.stat().st_mtime_ns == st.st_mtime_ns and target.stat().st_size == len(first)
    assert _artifacts._digest(target) == hashlib.sha256(second).hexdigest()
    assert opened.count(str(target)) == 2  # one read each: the first file, its replacement
    assert _artifacts._digest(target) == hashlib.sha256(second).hexdigest()
    assert opened.count(str(target)) == 2  # the cached digest of the file in place: no read


def _descriptor_reports(monkeypatch, **changed: int) -> None:
    """`os.fstat` reports the open file with `changed` fields, as Windows does for st_ctime_ns:
    the change time by descriptor, the creation time by name."""
    import os

    real = os.fstat

    def fstat(fd):
        st = real(fd)
        ns = {f: getattr(st, f) for f in ("st_atime_ns", "st_mtime_ns", "st_ctime_ns")}
        fields = list(st)
        fields[1] = changed.get("st_ino", st.st_ino)
        ns.update((f, v) for f, v in changed.items() if f in ns)
        return os.stat_result(fields, ns)

    monkeypatch.setattr(os, "fstat", fstat)


def test_a_change_time_the_name_reports_otherwise_still_hits_the_cache(
    tmp_path, monkeypatch
) -> None:
    target = tmp_path / "python.wasm"
    target.write_bytes(b"a" * 100)
    _descriptor_reports(monkeypatch, st_ctime_ns=target.stat().st_ctime_ns + 1)
    opened = _opens(monkeypatch)
    assert _artifacts._digest(target) == hashlib.sha256(b"a" * 100).hexdigest()
    assert _artifacts._digest(target) == hashlib.sha256(b"a" * 100).hexdigest()
    assert opened.count(str(target)) == 1  # the second call takes the cached digest


def test_a_descriptor_that_is_another_file_than_the_name_is_not_cached(
    tmp_path, monkeypatch
) -> None:
    target = tmp_path / "python.wasm"
    target.write_bytes(b"a" * 100)
    _descriptor_reports(monkeypatch, st_ino=target.stat().st_ino + 1)
    opened = _opens(monkeypatch)
    assert _artifacts._digest(target) == hashlib.sha256(b"a" * 100).hexdigest()
    assert _artifacts._digest(target) == hashlib.sha256(b"a" * 100).hexdigest()
    assert opened.count(str(target)) == 2  # what was hashed is not the named file: read again


def test_a_rewritten_manifest_gives_its_new_version_tag(tmp_path) -> None:
    manifest = tmp_path / "MANIFEST"
    manifest.write_text("python 3.15.0\n")
    assert _artifacts._version_tag(manifest) == "315"
    manifest.write_text("python 3.16.0\nrecipe one two\n")  # a reinstall rewrites it in place
    assert _artifacts._version_tag(manifest) == "316"
