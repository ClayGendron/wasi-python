"""A starting image an embedder makes, with no guest: the saved file and its checks, the file's
ownership rule, the object's own rules, the call's checks of a snapshot, the package names, the
grant judge's rule for the folders of saved files, the restore into a stand-in module, and the
process's counts and folders.

The rows that need an instance use a module of their own, one or two pages of memory and
nothing else, through the restore's own signature; the rows that need a set use a stand-in set
of small modules, passed as `artifacts=`."""

from __future__ import annotations

import asyncio
import concurrent.futures
import copy
import dataclasses
import hashlib
import json
import os
import pickle
import stat
import sys
import zipfile
import zlib
from pathlib import Path

import pytest

import wasi_python
from harness import wat
from wasi_python import _artifacts, _platform, _snapshot, _snapshot_make, runner
from wasi_python._process import _Process, process

PAGE = 65536
POSIX = pytest.mark.skipif(sys.platform == "win32", reason="POSIX modes and owners")
WINDOWS = pytest.mark.skipif(sys.platform != "win32", reason="Windows' own rule")
NO_PREPARE = wat.SNAPSHOT.replace(
    '(func (export "prepare") (param i32 i32) (result i32) (i32.const -1))', ""
)


def _origin(image: bytes, **changed: object) -> wasi_python.SnapshotOrigin:
    prelude = "import numpy\nx = 1\ny = 2\n"
    fields = {
        "prelude": prelude,
        "prelude_sha256": hashlib.sha256(prelude.encode()).hexdigest(),
        "prelude_fuel": None,
        "image_bytes": len(image),
        "image_sha256": hashlib.sha256(image).hexdigest(),
        "home": _snapshot.IMAGE_HOME,
        "guest_paths": ("/data",),
        "env_names": ("A",),
        "snapshot_sha256": "0" * 64,
        "stdlib_zip_sha256": "1" * 64,
        "wasi_python": "0.1.2",
        "made_at": "2026-10-28T09:14:03Z",
    }
    fields.update(changed)
    return wasi_python.SnapshotOrigin(**fields)  # type: ignore[arg-type]


def _image(pages: int = 2) -> bytes:
    return bytes(range(256)) * (pages * PAGE // 256)


def _snap(image: bytes | None = None, **changed: object) -> wasi_python.Snapshot:
    image = _image() if image is None else image
    return _snapshot._made(image, _origin(image, **changed))


def _folder(work: Path, name: str = "app") -> Path:
    folder = work / name
    folder.mkdir(mode=0o700)
    return folder


def _write(path: Path, *, first: bytes = b"wasi-python snapshot\n", header=None, body=b"") -> Path:
    """A file in the saved form, its parts as given, written as save() writes one (mode 600)."""
    if header is None:
        header = {}
    head = header if isinstance(header, bytes) else json.dumps(header, sort_keys=True).encode()
    path.write_bytes(first + head + b"\n" + body)
    path.chmod(0o600)
    return path


def _header(image: bytes, **changed: object) -> dict:
    origin = _origin(image)
    out = {"format": 1, "codec": "zlib", **dataclasses.asdict(origin)}
    out["guest_paths"], out["env_names"] = list(origin.guest_paths), list(origin.env_names)
    out.update(changed)
    return out


def _stand_in_set(work: Path, snapshot_wat: str = wat.SNAPSHOT, manifest: str = "") -> Path:
    folder = work / "set"
    wat.build(folder, "python-snapshot.wasm", snapshot_wat)
    wat.build(folder, "python.wasm", wat.PLAIN_REACTOR)
    (folder / "MANIFEST").write_text("python 3.15.0\n" + manifest)
    with zipfile.ZipFile(folder / "python-stdlib.zip", "w"):
        pass
    return folder


def _given(folder: Path) -> wasi_python.Artifacts:
    return wasi_python.Artifacts(
        snapshot=folder / "python-snapshot.wasm",
        plain=folder / "python.wasm",
        stdlib_zip=folder / "python-stdlib.zip",
        manifest=folder / "MANIFEST",
    )


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------
# The file


def test_the_file_round_trips(work) -> None:
    snap = _snap()
    path = _folder(work) / "app.wpsnap"
    assert snap.save(path) is None
    loaded = wasi_python.Snapshot.load(path)
    assert loaded.origin == snap.origin
    assert loaded._image == snap._image
    assert path.read_bytes().startswith(b"wasi-python snapshot\n")
    if sys.platform != "win32":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    snap.save(path)  # a second save replaces the file
    assert wasi_python.Snapshot.load(path).origin == snap.origin


@POSIX
def test_a_save_where_others_may_write_is_refused_and_writes_nothing(work) -> None:
    open_folder = _folder(work, "open")
    open_folder.chmod(0o777)
    try:
        with pytest.raises(PermissionError, match="written by others"):
            _snap().save(open_folder / "app.wpsnap")
        assert list(open_folder.iterdir()) == []
    finally:
        open_folder.chmod(0o700)


LOAD_REFUSALS = {
    "another first line": dict(first=b"not a snapshot\n"),
    "format 2": dict(header=_header(_image(), format=2)),
    "an unknown codec": dict(header=_header(_image(), codec="zstd")),
    "not a page multiple": dict(header=_header(_image(), image_bytes=PAGE + 1)),
    "past 4 GiB": dict(header=_header(_image(), image_bytes=(4 << 30) + PAGE)),
    "a stream that ends short": dict(
        header=_header(_image(), image_bytes=3 * PAGE), body=zlib.compress(_image(), 1)
    ),
    "bytes past image_bytes": dict(
        header=_header(_image(), image_bytes=PAGE), body=zlib.compress(_image(), 1)
    ),
    "an image whose hash differs": dict(
        header=_header(_image()), body=zlib.compress(_image()[::-1], 1)
    ),
}


@pytest.mark.parametrize("case", sorted(LOAD_REFUSALS))
def test_load_refuses_a_file_that_does_not_fit(work, case) -> None:
    path = _write(_folder(work) / "bad.wpsnap", **LOAD_REFUSALS[case])
    with pytest.raises(wasi_python.SnapshotMismatch, match="bad.wpsnap"):
        wasi_python.Snapshot.load(path)


def test_load_refuses_a_header_past_its_cap(work) -> None:
    path = _write(_folder(work) / "big.wpsnap", header=b" " * ((17 << 20) + 1))
    with pytest.raises(wasi_python.SnapshotMismatch, match="header"):
        wasi_python.Snapshot.load(path)


@POSIX
def test_load_refuses_a_file_others_may_write(work) -> None:
    path = _folder(work) / "app.wpsnap"
    _snap().save(path)
    path.chmod(0o620)
    with pytest.raises(PermissionError, match=r"written by others \(mode 620\)"):
        wasi_python.Snapshot.load(path)


@POSIX
def test_load_refuses_a_link(work) -> None:
    folder = _folder(work)
    _snap().save(folder / "real.wpsnap")
    (folder / "link.wpsnap").symlink_to(folder / "real.wpsnap")
    with pytest.raises(PermissionError, match="link"):
        wasi_python.Snapshot.load(folder / "link.wpsnap")


@POSIX
def test_load_refuses_a_file_with_two_names(work) -> None:
    folder = _folder(work)
    _snap().save(folder / "one.wpsnap")
    os.link(folder / "one.wpsnap", folder / "two.wpsnap")
    with pytest.raises(PermissionError, match="name"):
        wasi_python.Snapshot.load(folder / "one.wpsnap")


@POSIX
def test_load_refuses_a_way_through_another_users_folder(work) -> None:
    folder = _folder(work)
    path = folder / "app.wpsnap"
    _snap().save(path)

    def lstat(name: str) -> os.stat_result:
        st = os.lstat(name)
        if Path(name) == folder:  # as if another user owned the folder the file is in
            values = list(st)
            values[stat.ST_UID] = os.getuid() + 1
            return os.stat_result(values)
        return st

    with pytest.raises(PermissionError, match="another user's"):
        _platform.PLATFORM.open_owned(path, lstat=lstat)


@WINDOWS
def test_load_refuses_a_link_on_windows(work) -> None:
    folder = _folder(work)
    _snap().save(folder / "real.wpsnap")
    try:
        (folder / "link.wpsnap").symlink_to(folder / "real.wpsnap")
    except OSError:
        pytest.skip("this user may not make a symbolic link")
    with pytest.raises(PermissionError, match="link"):
        wasi_python.Snapshot.load(folder / "link.wpsnap")


# ---------------------------------------------------------------------------------------------
# The object


def test_a_snapshot_is_made_only_by_its_functions() -> None:
    with pytest.raises(TypeError, match="make_snapshot, make_package_snapshot or Snapshot.load"):
        wasi_python.Snapshot()
    snap = _snap()
    with pytest.raises(TypeError, match=r"save\(\) it and Snapshot.load\(\) it"):
        pickle.dumps(snap)
    assert copy.copy(snap) is snap and copy.deepcopy(snap) is snap
    with pytest.raises(AttributeError):
        snap.origin = None  # type: ignore[misc]
    other = _snap()
    assert snap == snap and snap != other and len({snap, other, snap}) == 2  # by identity


def test_the_repr_reads_as_one_line() -> None:
    snap = _snap()
    assert repr(snap) == (
        "<Snapshot 'import numpy' +2 lines, 0.1 MiB, made 2026-10-28T09:14:03Z "
        "by wasi-python 0.1.2>"
    )
    long = _snap(prelude="import numpy, pandas, scipy, sklearn, statsmodels, sympy")
    assert repr(long).startswith("<Snapshot 'import numpy, pandas, scipy, sklearn, st…', ")
    one = _snap(prelude="pass")
    assert repr(one).startswith("<Snapshot 'pass', 0.1 MiB, ")


def test_check_binds_a_snapshot_to_its_set(work) -> None:
    folder = _stand_in_set(work)
    given = _given(folder)
    own = _snap(
        snapshot_sha256=_digest(given.snapshot), stdlib_zip_sha256=_digest(given.stdlib_zip)
    )
    assert own.check(artifacts=given) is None
    other = _snap(stdlib_zip_sha256=_digest(given.stdlib_zip))
    with pytest.raises(wasi_python.SnapshotMismatch, match="make it again with this set"):
        other.check(artifacts=given)


def test_a_making_on_a_set_without_prepare_is_refused_before_any_walk(work) -> None:
    given = _given(_stand_in_set(work, NO_PREPARE))
    missing = wasi_python.Grant(work / "no-such-folder", "/data")  # a walk would refuse it
    with pytest.raises(wasi_python.ArtifactsMissing, match="does not export prepare"):
        wasi_python.make_snapshot("pass", grants=[missing], artifacts=given, cache_dir=False)


# ---------------------------------------------------------------------------------------------
# A call's checks of `snapshot=`


class _Refusing(concurrent.futures.Executor):
    """An executor that records any submit: a call refused before any work never reaches it."""

    def __init__(self) -> None:
        self.submitted: list[object] = []

    def submit(self, fn, /, *args, **kwargs):
        self.submitted.append(fn)
        raise AssertionError("submit must not be reached")


def test_snapshot_is_true_false_or_a_snapshot(monkeypatch) -> None:
    lookups: list[int] = []

    def found():
        lookups.append(1)
        raise AssertionError("the artifacts must not be looked up")

    monkeypatch.setattr(_artifacts, "find_artifacts", found)
    with pytest.raises(TypeError, match="snapshot must be True, False or a Snapshot; got str"):
        runner.run(["-c", "pass"], snapshot="yes")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="got str"):
        wasi_python.Session(snapshot="yes")  # type: ignore[arg-type]
    small = runner.Defaults(PAGE, 60.0, 1 << 20)
    snap = _snap()  # two pages
    ex = _Refusing()
    for call in (
        lambda: runner.run(["-c", "pass"], snapshot=snap, memory_bytes=PAGE),
        lambda: asyncio.run(
            runner.run_async(["-c", "pass"], snapshot=snap, memory_bytes=PAGE, executor=ex)
        ),
        lambda: wasi_python.Session(snapshot=snap, memory_bytes=PAGE),
    ):
        with pytest.raises(wasi_python.SnapshotMismatch, match="below the snapshot's image of"):
            call()
    before = wasi_python.set_defaults(small)
    try:
        with pytest.raises(wasi_python.SnapshotMismatch, match="memory_bytes is 65,536"):
            runner.run(["-c", "pass"], snapshot=snap)
    finally:
        wasi_python.set_defaults(before)
    assert (lookups, ex.submitted) == ([], [])


# ---------------------------------------------------------------------------------------------
# The package names


LINES = (
    "x-snapshot-package numpy numpy\n"
    "x-snapshot-package scikit-learn sklearn sklearn.tree sklearn.linear_model\n"
)


def test_package_names_are_checked_before_any_work(work) -> None:
    given = _given(_stand_in_set(work, NO_PREPARE, LINES))
    with pytest.raises(TypeError, match="not a str"):
        wasi_python.make_package_snapshot("numpy", artifacts=given)  # type: ignore[arg-type]
    for bad in ("numpy; import os", "", "1numpy", "numpy.", "import"):
        with pytest.raises(ValueError, match="packages"):
            wasi_python.make_package_snapshot([bad], artifacts=given)


def test_package_names_resolve_against_the_sets_lines(work) -> None:
    manifest = _stand_in_set(work, manifest=LINES) / "MANIFEST"

    def names(*given: str) -> list[str]:
        return _snapshot_make._package_names(given, manifest)

    tree = ["sklearn", "sklearn.tree", "sklearn.linear_model"]
    assert names("scikit-learn") == tree
    assert names("Scikit-Learn") == tree
    assert names("sklearn") == tree  # a line's first name imports its line
    assert names("sklearn.tree", "json") == ["sklearn.tree", "json"]
    assert names("numpy", "numpy", "sklearn.tree", "scikit-learn") == [
        "numpy",
        "sklearn.tree",
        "sklearn",
        "sklearn.linear_model",
    ]
    assert _snapshot_make._package_names(None, manifest) == ["numpy", *tree]
    assert _snapshot_make._package_code(["numpy", "sklearn.tree"]) == (
        "import numpy\nimport sklearn.tree\n"
    )


def test_a_set_without_package_lines(work) -> None:
    folder = _stand_in_set(work, NO_PREPARE)
    manifest = folder / "MANIFEST"
    with pytest.raises(wasi_python.ArtifactsMissing, match="no x-snapshot-package lines"):
        wasi_python.make_package_snapshot(artifacts=_given(folder))
    assert _snapshot_make._package_names(["numpy.linalg"], manifest) == ["numpy.linalg"]
    with pytest.raises(wasi_python.ArtifactsMissing, match="scikit-learn"):
        _snapshot_make._package_names(["scikit-learn"], manifest)


# ---------------------------------------------------------------------------------------------
# The grant judge


def test_a_writable_grant_holding_a_snapshots_folder_is_refused(work) -> None:
    given = _given(_stand_in_set(work))
    parent = _folder(work, "parent")  # apart from the stand-in set, which a grant may not hold
    project = _folder(parent, "project")
    inside = project / "work"
    inside.mkdir()
    _snap().save(project / "app.wpsnap")

    def grant(host: Path, writable: bool) -> int | None:
        g = wasi_python.Grant(host, "/w", writable=writable)
        return runner.run([], grants=[g], artifacts=given, cache_dir=False).exit_code

    for host in (project, parent):
        with pytest.raises(ValueError, match="holds the folder of a snapshot file"):
            grant(host, True)
    with pytest.raises(ValueError, match="holds the folder of a snapshot file"):
        runner.run([], root=str(project), artifacts=given, cache_dir=False)
    assert grant(inside, True) == 101  # the stand-in's door probe: it ran
    assert grant(project, False) == 101


def test_a_folder_a_running_session_may_write_is_refused_until_it_ends(work) -> None:
    given = _given(_stand_in_set(work))
    shared = _folder(work, "shared")
    _snap().save(_folder(work, "kept") / "app.wpsnap")
    session = wasi_python.Session(
        grants=[wasi_python.Grant(shared, "/w", writable=True)], artifacts=given, cache_dir=False
    )
    try:
        with pytest.raises(PermissionError, match="running now"):
            _snap().save(shared / "app.wpsnap")
        with pytest.raises(PermissionError, match="running now"):
            _snap().save(_folder(shared, "below") / "app.wpsnap")
        assert list(shared.rglob("*.wpsnap")) == []
    finally:
        session.close()
    _snap().save(shared / "app.wpsnap")  # allowed once no call may write it
    assert wasi_python.Snapshot.load(shared / "app.wpsnap").origin == _snap().origin


@POSIX
def test_a_link_inside_a_writable_grant_on_the_way_to_a_snapshot_is_refused(work) -> None:
    given = _given(_stand_in_set(work))
    parent = _folder(work, "parent")
    real = _folder(work, "real")
    (parent / "link").symlink_to(real)
    _snap().save(parent / "link" / "app.wpsnap")  # its folder kept as written, through the link
    g = wasi_python.Grant(parent, "/w", writable=True)
    with pytest.raises(ValueError, match="holds the folder of a snapshot file"):
        runner.run([], grants=[g], artifacts=given, cache_dir=False)


def test_load_refuses_a_home_other_than_the_images(work) -> None:
    body = zlib.compress(_image(), 1)
    path = _write(_folder(work) / "home.wpsnap", header=_header(_image(), home="/w"), body=body)
    with pytest.raises(wasi_python.SnapshotMismatch, match="home"):
        wasi_python.Snapshot.load(path)


# ---------------------------------------------------------------------------------------------
# The restore


ONE_PAGE = '(module (memory (export "memory") 1))'
TWO_PAGES = '(module (memory (export "memory") 2))'


def _instance(wat_text: str, limit: int | None = None):
    import wasmtime

    engine = wasmtime.Engine()
    store = wasmtime.Store(engine)
    if limit is not None:
        store.set_limits(memory_size=limit)
    module = wasmtime.Module(engine, wasmtime.wat2wasm(wat_text))
    return store, wasmtime.Instance(store, module, [])


def test_the_restore_grows_the_memory_and_copies_the_image() -> None:
    store, instance = _instance(ONE_PAGE)
    image = _image(3)
    before = runner.stats()["snapshots_restored"]
    _snapshot._restore(store, instance, image)
    memory = instance.exports(store)["memory"]
    assert memory.size(store) == 3
    assert bytes(memory.read(store, 0, 3 * PAGE)) == image
    assert runner.stats()["snapshots_restored"] == before + 1


def test_the_restore_refuses_an_image_past_the_stores_limit() -> None:
    store, instance = _instance(ONE_PAGE, limit=2 * PAGE)
    with pytest.raises(wasi_python.SnapshotMismatch, match="memory"):
        _snapshot._restore(store, instance, _image(3))
    memory = instance.exports(store)["memory"]
    assert bytes(memory.read(store, 0, memory.data_len(store))) == bytes(memory.data_len(store))


def test_the_restore_refuses_an_image_shorter_than_the_instance() -> None:
    store, instance = _instance(TWO_PAGES)
    with pytest.raises(wasi_python.SnapshotMismatch, match="shorter"):
        _snapshot._restore(store, instance, _image(1))


# ---------------------------------------------------------------------------------------------
# The process


def test_a_fork_keeps_the_snapshot_folders() -> None:
    p = _Process()
    p.snapshot_folders.add("/home/me/app")
    p.reset_after_fork()
    assert p.snapshot_folders == {"/home/me/app"}


def test_stats_lists_makings_and_restores() -> None:
    counts = runner.stats()
    assert {"snapshots_made", "snapshots_restored"} <= set(counts)
    assert set(process().counts) >= {"snapshots_made", "snapshots_restored"}
