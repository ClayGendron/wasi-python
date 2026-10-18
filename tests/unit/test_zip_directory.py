"""Spec 035 on the host: the recipe modules `_zip_directory` and `_zip_resources`, and the
judge's own zips. They run on the judge's Python, which need not be the guest's version, so
each compares with the host's `zipfile`, never with the host's zipimport (whose reader differs
across versions)."""

from __future__ import annotations

import importlib.util
import io
import struct
import sys
import zipfile
from pathlib import Path

import pytest

from harness import paths, zips

RECIPES = paths.REPO / "recipes"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"judge_{name}", RECIPES / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def zd():
    return _load("zip_directory")


def _write(folder: Path, name: str, data: bytes) -> str:
    path = folder / name
    path.write_bytes(data)
    return str(path)


ORDINARY = {
    "plain": zips.build({"a.py": "x = 1\n", "pkg/__init__.py": "", "pkg/sub/m.py": "y = 2\n"}),
    "explicit dirs": zips.explicit_dirs_zip(),
    "prepended and a comment": zips.prepended_zip(),
}


@pytest.mark.parametrize("case", ORDINARY)
def test_the_fast_reader_matches_zipfile_on_the_host(zd, work, case) -> None:
    archive = _write(work, "x.zip", ORDINARY[case])
    files = zd.read_directory(archive)
    assert zd.served == {archive: "fast"}
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
    implied = set(zipfile.Path(archive).root.namelist()) - {i.filename for i in infos}
    members = [n for n, toc in files.items() if toc is not None]
    assert members == [i.filename for i in infos]
    for info in infos:
        toc = files[info.filename]
        dos_date = (info.date_time[0] - 1980) << 9 | info.date_time[1] << 5 | info.date_time[2]
        dos_time = info.date_time[3] << 11 | info.date_time[4] << 5 | info.date_time[5] // 2
        assert toc == (
            f"{archive}/{info.filename}".rstrip("/"),
            info.compress_type,
            info.compress_size,
            info.file_size,
            info.header_offset,
            dos_time,
            dos_date,
            info.CRC,
        ), info.filename
    assert {n for n, toc in files.items() if toc is None} == implied


def _stock_stub(zd, answer):
    calls = []

    def stub(archive):
        calls.append(archive)
        if isinstance(answer, BaseException):
            raise answer
        return answer

    zd.stock_read_directory = stub
    return calls


def _understated() -> bytes:
    data = bytearray(zips.build({"a.py": "", "b.py": "", "c.py": ""}))
    end = data.rfind(b"PK\x05\x06")
    struct.pack_into("<HH", data, end + 8, 2, 2)
    return bytes(data)


ODD = {
    "zip64": zips.zip64_zip(),
    "cp437": zips.cp437_zip(),
    "truncated": zips.truncated_zip(),
    "one entry more than declared": _understated(),
}


@pytest.mark.parametrize("case", ODD)
@pytest.mark.parametrize("answer", [{"from": "stock"}, ValueError("stock's own error")])
def test_odd_zips_go_to_the_stock_reader(zd, work, case, answer) -> None:
    archive = _write(work, "odd.zip", ODD[case])
    calls = _stock_stub(zd, answer)
    if isinstance(answer, BaseException):
        with pytest.raises(ValueError) as caught:
            zd.read_directory(archive)
        assert caught.value is answer
    else:
        assert zd.read_directory(archive) is answer
    assert calls == [archive]
    assert zd.served == {archive: "stock"}


def test_an_unreadable_archive_goes_to_the_stock_reader(zd, work) -> None:
    calls = _stock_stub(zd, {})
    missing = str(work / "missing.zip")
    assert zd.read_directory(missing) == {}
    assert calls == [missing] and zd.served == {missing: "stock"}


def test_install_replaces_zipimports_reader(zd, monkeypatch) -> None:
    import zipimport

    monkeypatch.setattr(zipimport, "_read_directory", zipimport._read_directory)
    zd.install()
    assert zipimport._read_directory is zd.read_directory


def test_the_judges_zips_have_what_they_claim(work) -> None:
    zips.check_zip64(zips.zip64_zip())
    zips.check_cp437(zips.cp437_zip())
    zips.check_resource_zip(zips.resource_zip())
    assert zips.prepended_zip().startswith(zips.PREPENDED)
    with zipfile.ZipFile(io.BytesIO(zips.prepended_zip())) as z:
        assert z.comment == b"an archive comment"
    with zipfile.ZipFile(io.BytesIO(zips.explicit_dirs_zip())) as z:
        assert {"xdir/", "xdir/sub/"} <= set(z.namelist())
    with pytest.raises(zipfile.BadZipFile):
        zipfile.ZipFile(io.BytesIO(zips.truncated_zip()))
    # small.zip keeps each member of its source, local header and data, byte for byte.
    source = work / "source.zip"
    source.write_bytes(zips.build({"m.py": "x = 1\n", "pkg/__init__.py": "", "pkg/d.txt": "d"}))
    zips.make_small(source, work / "small.zip")
    before, after = source.read_bytes(), (work / "small.zip").read_bytes()
    cd_offset = struct.unpack_from("<I", before, before.rfind(b"PK\x05\x06") + 16)[0]
    assert after[:cd_offset] == before[:cd_offset]
    with zipfile.ZipFile(work / "small.zip") as z:
        assert set(zips.DISTRIBUTIONS) <= set(z.namelist())
    zips.make_padded(work / "small.zip", source, work / "padded.zip")
    with zipfile.ZipFile(work / "padded.zip") as z:
        names = z.namelist()
    assert len(names) == len(zips.DISTRIBUTIONS) + 4 * 3
    assert {n for n in names if n.startswith("pad3/")} == {"pad3/m.py", "pad3/pkg/__init__.py",
                                                           "pad3/pkg/d.txt"}  # fmt: skip


@pytest.fixture(autouse=True)
def _no_private_modules_left():
    yield
    for name in [n for n in sys.modules if n.startswith("judge_zip_")]:
        del sys.modules[name]
