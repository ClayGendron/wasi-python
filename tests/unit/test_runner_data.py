"""matplotlib's data in the runner's zip folder (spec 023, Decision 5): extracted from the zip's
inner archive, every file read back and recorded, refused when a member could leave the folder,
and made equal to the archive again when the tree changed on the host. Synthetic zips only, so
nothing here needs the artifact set; nothing here measures time."""

from __future__ import annotations

import io
import os
import stat
import zipfile
from pathlib import Path

import pytest

from wasi_python import runner

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
            z.writestr(runner.MPL_DATA_MEMBER, inner)
    return path


def test_the_data_is_extracted_and_recorded(tmp_path) -> None:
    data = tmp_path / "mpl-data"
    record = runner._extract_data(data, _stdlib(tmp_path, _inner(FILES)))
    assert record is not None
    assert {k for k, v in record.items() if v is not None} == set(FILES)
    assert {k for k, v in record.items() if v is None} == {"fonts", "fonts/ttf", "stylelib"}
    for name, body in FILES.items():
        assert (data / name).read_bytes() == body
    assert runner._data_intact(data, record)


def test_a_zip_without_data_gives_no_folder(tmp_path) -> None:
    data = tmp_path / "mpl-data"
    assert runner._extract_data(data, _stdlib(tmp_path, None)) is None
    assert not os.path.lexists(data)


@pytest.mark.parametrize("name", ["/abs.txt", "../up.txt", "a/../../up.txt", "a//b", "c:\\x"])
def test_a_member_that_could_leave_the_folder_is_refused(tmp_path, name) -> None:
    with pytest.raises(RuntimeError, match="holds the member"):
        runner._extract_data(tmp_path / "mpl-data", _stdlib(tmp_path, _inner({name: b"x"})))


def test_a_link_member_is_refused(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="not a regular file"):
        runner._extract_data(tmp_path / "mpl-data", _stdlib(tmp_path, _inner(FILES, "evil")))


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
        lambda: runner._remove_entry(data / "fonts"),
        lambda: (
            runner._remove_entry(data / "fonts" / "ttf"),
            (data / "fonts" / "ttf").symlink_to(outside),
        ),
        lambda: (runner._remove_entry(data), data.symlink_to(outside)),
    ]
    for change in changes:
        record = runner._extract_data(data, zip_copy)
        assert record is not None and runner._data_intact(data, record)
        change()
        assert not runner._data_intact(data, record)
        again = runner._extract_data(data, zip_copy)
        assert again is not None and runner._data_intact(data, again)
        assert {k for k, v in again.items() if v is not None} == set(FILES)
        assert not data.is_symlink() and not (data / "fonts" / "ttf").is_symlink()
        for name, body in FILES.items():
            assert (data / name).read_bytes() == body
    assert sorted(os.listdir(outside)) == ["keep.txt"]  # nothing outside was touched
