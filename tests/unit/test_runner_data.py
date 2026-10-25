"""matplotlib's data in the runner's zip folder: extracted from the zip's
inner archive, every file read back and recorded, refused when a member could leave the folder,
and made equal to the archive again when the tree changed on the host. Synthetic zips only, so
nothing here needs the artifact set; nothing here measures time."""

from __future__ import annotations

import io
import os
import stat
import threading
import zipfile
from collections import Counter
from pathlib import Path

import pytest

from wasi_python import _zip

POSIX = os.name == "posix"
FILES = {
    "matplotlibrc": b"backend: Agg\n",
    "fonts/ttf/a.ttf": b"\0font",
    "stylelib/s.mplstyle": b"x",
}


def _inner(files: dict[str, bytes], link: str | None = None) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:
        for name, body in files.items():
            z.writestr(name, body)
        if link is not None:
            info = zipfile.ZipInfo(link)
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(info, "/etc")
    return out.getvalue()


def _stdlib(tmp_path: Path, inner: bytes | None) -> Path:
    path = tmp_path / "python315.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("os.pyc", b"\0" * 16)
        if inner is not None:
            z.writestr(_zip.MPL_DATA_MEMBER, inner)
    return path


def test_the_data_is_extracted_and_recorded(tmp_path) -> None:
    data = tmp_path / "mpl-data"
    record = _zip._extract_data(data, _stdlib(tmp_path, _inner(FILES)))
    assert record is not None
    assert {k for k, v in record.items() if v is not None} == set(FILES)
    assert {k for k, v in record.items() if v is None} == {"fonts", "fonts/ttf", "stylelib"}
    for name, body in FILES.items():
        assert (data / name).read_bytes() == body
    assert _zip._data_intact(data, record)


def test_a_zip_without_data_gives_no_folder(tmp_path) -> None:
    data = tmp_path / "mpl-data"
    assert _zip._extract_data(data, _stdlib(tmp_path, None)) is None
    assert not os.path.lexists(data)


@pytest.mark.parametrize("name", ["/abs.txt", "../up.txt", "a/../../up.txt", "a//b", "c:\\x"])
def test_a_member_that_could_leave_the_folder_is_refused(tmp_path, name) -> None:
    with pytest.raises(RuntimeError, match="holds the member"):
        _zip._extract_data(tmp_path / "mpl-data", _stdlib(tmp_path, _inner({name: b"x"})))


# Names a system would rewrite or read as another are refused on every system, whatever the
# host: a device Windows reserves (with or without an extension, and its superscript digits),
# a trailing dot or space Windows trims, a character Windows rejects, a format character (a
# zero-width joiner, the byte-order mark) that HFS+ drops from a name; and two paths, or folders
# on their way, that a case-folding file system or one that normalises Unicode reads as one.
@pytest.mark.parametrize(
    "name", ["CON.txt", "aux", "COM¹", "name.", "name ", "a?b", "a*b", "a\u200cb", "a\ufeffb"]
)
def test_a_name_windows_reserves_or_rewrites_is_refused(tmp_path, name) -> None:
    for member in (f"fonts/{name}", f"{name}/x.ttf"):
        with pytest.raises(RuntimeError, match="holds the member"):
            _zip._extract_data(tmp_path / "mpl-data", _stdlib(tmp_path, _inner({member: b"x"})))
        assert not os.path.lexists(tmp_path / "mpl-data")


@pytest.mark.parametrize(
    "names",
    [("Foo/x", "foo/x"), ("Foo/x", "foo/y"), ("é", "é")],
    ids=["case", "folder-case", "nfc"],
)
def test_names_equal_under_case_folding_are_refused(tmp_path, names) -> None:
    with pytest.raises(RuntimeError, match="holds the member"):
        _zip._extract_data(
            tmp_path / "mpl-data", _stdlib(tmp_path, _inner(dict.fromkeys(names, b"x")))
        )
    assert not os.path.lexists(tmp_path / "mpl-data")


def test_names_near_the_reserved_ones_pass(tmp_path) -> None:
    near = {"CONSOLE.txt": b"1", "COM10": b"2", "nul_x": b"3", "auxiliary/x": b"4", "a.b.c": b"5"}
    record = _zip._extract_data(tmp_path / "mpl-data", _stdlib(tmp_path, _inner(near)))
    assert record is not None and {k for k, v in record.items() if v is not None} == set(near)


def test_a_link_member_is_refused(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="not a regular file"):
        _zip._extract_data(tmp_path / "mpl-data", _stdlib(tmp_path, _inner(FILES, "evil")))


@pytest.mark.skipif(not POSIX, reason="links need privileges on Windows")
def test_every_change_on_the_host_is_seen_and_undone(tmp_path) -> None:
    """An added file, a changed one, a removed folder and a folder swapped for a link each fail the
    per-call comparison, and extracting again restores the archive's tree exactly."""
    zip_copy = _stdlib(tmp_path, _inner(FILES))
    data = tmp_path / "mpl-data"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("host file")
    changes = [
        lambda: (data / "stylelib" / "extra.mplstyle").write_text("added"),
        lambda: (data / "matplotlibrc").write_bytes(b"backend: changed\n"),
        lambda: _zip._remove_entry(data / "fonts"),
        lambda: (
            _zip._remove_entry(data / "fonts" / "ttf"),
            (data / "fonts" / "ttf").symlink_to(outside),
        ),
        lambda: (_zip._remove_entry(data), data.symlink_to(outside)),
    ]
    for change in changes:
        record = _zip._extract_data(data, zip_copy)
        assert record is not None and _zip._data_intact(data, record)
        change()
        assert not _zip._data_intact(data, record)
        again = _zip._extract_data(data, zip_copy)
        assert again is not None and _zip._data_intact(data, again)
        assert {k for k, v in again.items() if v is not None} == set(FILES)
        assert not data.is_symlink() and not (data / "fonts" / "ttf").is_symlink()
        for name, body in FILES.items():
            assert (data / name).read_bytes() == body
    assert sorted(os.listdir(outside)) == ["keep.txt"]  # nothing outside was touched


def test_the_data_comparison_lists_each_folder_once_and_stats_each_entry_once(
    tmp_path, monkeypatch
) -> None:
    """The comparison runs on every call, so its work is held as a count of the standard
    library's calls on this thread: one listing of the root and of each folder, one lstat of
    each entry's path and nothing else beside the root's own link and folder tests, whatever
    those cost on this system."""
    data = tmp_path / "mpl-data"
    record = _zip._extract_data(data, _stdlib(tmp_path, _inner(FILES)))
    assert record is not None
    me = threading.get_ident()
    calls: dict[str, list[str]] = {"scandir": [], "lstat": [], "stat": []}

    def counted(name: str):
        real = getattr(os, name)

        def wrapper(path, *args, **kwargs):
            if threading.get_ident() == me:
                calls[name].append(os.fspath(path))
            return real(path, *args, **kwargs)

        return wrapper

    for name in calls:
        monkeypatch.setattr(os, name, counted(name))
    root = os.fspath(data)
    os.path.islink(root)  # the root's two tests, as this system makes them
    os.path.isdir(root)
    root_tests = {name: Counter(paths) for name, paths in calls.items()}
    for paths in calls.values():
        paths.clear()

    assert _zip._data_intact(data, record)

    def native(key: str) -> str:
        return os.path.join(root, *key.split("/"))

    entries = Counter(native(key) for key in record)
    folders = Counter(native(key) for key, stamp in record.items() if stamp is None)
    assert Counter(calls["scandir"]) == Counter([root]) + folders
    assert Counter(calls["lstat"]) == root_tests["lstat"] + entries
    assert Counter(calls["stat"]) == root_tests["stat"]
    assert len(entries) == 6 and (not POSIX or len(calls["lstat"]) == 7)  # six entries, the root
