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


def test_install_replaces_the_three_seams(zd, monkeypatch) -> None:
    """Each seam is put back afterwards: the host's own importlib.metadata must keep working."""
    import zipimport

    finder = zipimport._bootstrap_external.PathFinder
    monkeypatch.setattr(zipimport, "_read_directory", zipimport._read_directory)
    monkeypatch.setattr(
        zipimport.zipimporter, "get_resource_reader", zipimport.zipimporter.get_resource_reader
    )
    monkeypatch.setattr(finder, "find_distributions", finder.__dict__["find_distributions"])
    stock = finder.find_distributions
    zd.install()
    assert zipimport._read_directory is zd.read_directory
    assert zipimport.zipimporter.get_resource_reader is zd.get_resource_reader
    assert finder.find_distributions is zd.find_distributions
    assert zd.stock_find_distributions is stock


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


# Part 2: the resource reader's path and member reader.


class FakeLoader:
    """What `ZipDirectoryPath` asks of a zipimporter: its archive, its prefix and its dict."""

    def __init__(self, archive: str, files: dict, prefix: str = "") -> None:
        self.archive, self.files, self.prefix = archive, files, prefix

    def _get_files(self) -> dict:
        return self.files

    def is_package(self, fullname: str) -> bool:
        return True


@pytest.fixture
def zr():
    return _load("zip_resources")


NAMES = {
    "pkg/": None,
    "pkg/zone/": None,
    "pkg/zone/UTC": ("x",),
    "pkg/zone/Paris": ("x",),
    "pkg/a": ("x",),  # a file beside a same-named folder
    "pkg/a/": None,
    "pkg/a/b": ("x",),
    "//lead.py": ("x",),
    "//": None,  # the folder zipimport implies for "//lead.py"
}


def test_the_zip_path_answers_as_a_traversable(zr) -> None:
    files = dict(NAMES)
    root = zr.ZipDirectoryPath(FakeLoader("/z/x.zip", files))
    at = lambda p: p._at  # noqa: E731
    assert at(root.joinpath("pkg", "zone", "UTC")) == "pkg/zone/UTC"
    assert at(root / "pkg" / "zone") == "pkg/zone/"
    assert at(root.joinpath("pkg/zone/UTC/")) == "pkg/zone/UTC/"
    assert at(root.joinpath("pkg", "missing/")) == "pkg/missing/"
    assert at(root.joinpath("//lead.py")) == "//lead.py"
    assert at(root.joinpath("pkg", "a")) == "pkg/a"
    assert at(root.joinpath()) == ""
    pkg = root / "pkg"
    utc, utc_dir, missing_dir = pkg / "zone/UTC", pkg / "zone/UTC/", pkg / "missing/"
    assert [utc.is_file(), utc.is_dir(), utc.exists()] == [True, False, True]
    assert [utc_dir.is_file(), utc_dir.is_dir(), utc_dir.exists()] == [False, True, False]
    assert [missing_dir.is_file(), missing_dir.is_dir(), missing_dir.exists()] == [
        False,
        True,
        False,
    ]
    assert [root.is_file(), root.is_dir(), root.exists()] == [False, True, False]
    assert [(pkg / "zone").name, utc.name, root.name, utc_dir.name] == [
        "zone",
        "UTC",
        "x.zip",
        "UTC",
    ]
    assert (pkg / "zone/x.tar.gz").suffixes == [".tar", ".gz"] and root.suffix == ".zip"
    assert at(utc.parent) == "pkg/zone/" and at(pkg.parent) == "" and str(root.parent) == "/z"
    assert [str(root), str(utc), str(pkg)] == [
        "/z/x.zip/",
        "/z/x.zip/pkg/zone/UTC",
        "/z/x.zip/pkg/",
    ]
    assert utc == root.joinpath("pkg/zone/UTC") and hash(utc) == hash(pkg / "zone" / "UTC")
    assert utc != pkg and (utc == "/z/x.zip/pkg/zone/UTC") is False
    assert utc.__eq__("pkg/zone/UTC") is NotImplemented
    with pytest.raises(ValueError, match="Can't listdir a file"):
        utc.iterdir()
    assert zr._maps == {}, "a map before any listing"
    assert sorted(p.name for p in (pkg / "zone").iterdir()) == ["Paris", "UTC"]
    assert sorted(at(p) for p in pkg.iterdir()) == ["pkg/a", "pkg/a/", "pkg/zone/"]
    # zipfile.Path's own rule (`_is_child`) on zipimport's names: "//" is the root's child.
    assert [at(p) for p in root.iterdir()] == ["pkg/", "//"]
    built = zr._maps["/z/x.zip"]
    assert built[0] is files
    list(pkg.iterdir())
    assert zr._maps["/z/x.zip"] is built, "the map was built again for the same dict"
    root._loader.files = dict(files, **{"pkg/new": ("x",)})
    assert "new" in [p.name for p in pkg.iterdir()]
    assert zr._maps["/z/x.zip"][0] is root._loader.files


def _member_zip(folder: Path, zd, members: dict) -> FakeLoader:
    archive = folder / "m.zip"
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name, (data, method) in members.items():
            info = zipfile.ZipInfo(name, zips.DATE)
            info.compress_type = method
            z.writestr(info, data)
    archive.write_bytes(out.getvalue())
    return FakeLoader(str(archive), zd.read_directory(str(archive)))


def test_the_zip_path_opens_as_zipfile_path_does(zr, zd, work) -> None:
    text = "zoneinfo: ü\n"
    loader = _member_zip(work, zd, {"d/t.txt": (text.encode(), zipfile.ZIP_DEFLATED)})
    root = zr.ZipDirectoryPath(loader)
    t = root / "d" / "t.txt"
    with t.open("rb") as f:
        assert f.read() == text.encode()
    for mode in ("r", "rt", "r+"):
        with t.open(mode, encoding="utf-8") as f:
            assert f.read() == text, mode
    assert t.read_text(encoding="utf-8") == text and t.read_bytes() == text.encode()
    for mode in ("w", "br", "x", "a"):
        with pytest.raises(ValueError):
            t.open(mode)
    with pytest.raises(ValueError, match="encoding args invalid"):
        t.open("rb", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        (root / "d/missing").open("rb")
    with pytest.raises(IsADirectoryError):
        (root / "d").open("rb")
    with pytest.raises(IsADirectoryError):
        (root / "d").open("w")
    from importlib.resources.abc import Traversable, TraversableResources

    assert isinstance(t, Traversable) and "ZipDirectoryReader" not in vars(zr)
    assert issubclass(zr.ZipDirectoryReader, TraversableResources)
    assert zr.ZipDirectoryReader is vars(zr)["ZipDirectoryReader"], "not kept"
    reader = zr.ZipDirectoryReader(FakeLoader(loader.archive, loader.files, "d/"), "pkg.sub")
    assert reader.files()._at == "d/sub/"
    plain = zr.ZipDirectoryReader(FakeLoader(loader.archive, loader.files), "d")
    assert plain.files()._at == "d/" and plain.is_resource("t.txt") is True
    assert plain.is_resource("missing") is False and plain.is_resource("") is False


class _ZipfileStub:
    calls: list = []

    def __init__(self, root, at=""):
        self.at = at
        _ZipfileStub.calls.append((root, at))

    def open(self, mode="r", *args, **kwargs):
        return io.BytesIO(b"from zipfile")


def _patch(data: bytes, offset: int, value: bytes) -> bytes:
    return data[:offset] + value + data[offset + len(value) :]


@pytest.mark.parametrize(
    "case",
    ["plain", "lzma", "over 1 MiB", "bad crc", "encrypted", "local name", "inflates past"],
)
def test_the_member_reader_hands_odd_members_to_zipfile(zr, zd, work, monkeypatch, case) -> None:
    body = b"a member that inflates\n" * 50
    method = zipfile.ZIP_LZMA if case == "lzma" else zipfile.ZIP_DEFLATED
    if case == "over 1 MiB":
        body, method = b"x" * (zr.LIMIT + 1), zipfile.ZIP_STORED
    loader = _member_zip(work, zd, {"d/m.bin": (body, method)})
    data = Path(loader.archive).read_bytes()
    cd = data.rfind(b"PK\x01\x02")
    if case == "bad crc":
        crc = struct.unpack_from("<I", data, cd + 16)[0]
        data = _patch(data, cd + 16, struct.pack("<I", crc ^ 1))
    if case == "encrypted":
        data = _patch(data, 6, struct.pack("<H", 1))
    if case == "local name":
        data = _patch(data, 30, b"e")
    if case == "inflates past":
        data = _patch(data, cd + 24, struct.pack("<I", len(body) - 10))
    Path(loader.archive).write_bytes(data)
    loader.files = zd.read_directory(loader.archive)
    _ZipfileStub.calls = []
    monkeypatch.setattr(zipfile, "Path", _ZipfileStub)
    got = (zr.ZipDirectoryPath(loader) / "d/m.bin").read_bytes()
    if case == "plain":
        assert (got, _ZipfileStub.calls) == (body, [])
    else:
        assert (got, _ZipfileStub.calls) == (b"from zipfile", [(loader.archive, "d/m.bin")])


# Part 3: importlib.metadata's zip search on zipimport's dict.


def test_metadata_finds_a_zip_on_the_path_from_zipimports_dict(zr, zd, work, monkeypatch) -> None:
    import importlib.metadata as md
    import zipimport

    archive = _write(
        work, "m.zip", zips.build({"m.py": "", **zips.DISTRIBUTIONS, "pkg/__init__.py": ""})
    )
    monkeypatch.setattr(zipimport, "_read_directory", zd.read_directory)
    monkeypatch.setitem(sys.path_importer_cache, archive, zipimport.zipimporter(archive))
    monkeypatch.setitem(sys.modules, "_zip_resources", zr)
    monkeypatch.setattr(md.FastPath, "zip_children", md.FastPath.zip_children)
    stock = md.FastPath.zip_children
    calls = []
    zd.stock_find_distributions = lambda *a, **k: calls.append((a, k)) or iter(["found"])
    assert list(zd.find_distributions("ctx")) == ["found"] and calls == [(("ctx",), {})]
    assert md.FastPath.zip_children is zr.zip_children and zr.stock_zip_children is stock
    zd.find_distributions()
    assert zr.stock_zip_children is stock, "patched twice"

    class Root:  # a FastPath, as importlib.metadata makes one per sys.path entry
        def __init__(self, root):
            self.root = root

    ours, theirs = Root(archive), Root(archive)
    assert zr.zip_children(ours) == stock(theirs)
    assert list(zr.zip_children(ours)) == list(stock(theirs))
    assert type(ours.joinpath("pkg")).__name__ == "ZipDirectoryPath"
    assert str(ours.joinpath("pkg")) == str(theirs.joinpath("pkg"))
    other = _write(work, "other.zip", zips.build({"o.py": ""}))  # not on the import path
    elsewhere = Root(other)
    assert zr.zip_children(elsewhere) == {"o.py": None}
    assert type(elsewhere.joinpath("o.py")).__name__ == "Path"  # upstream's zipfile.Path
    dist = md.PathDistribution(ours.joinpath("judge_meta_b-2.0.dist-info"))
    assert dist.version == "2.0" and dist.requires == ["judge_meta_a>=1.0"]
    # RECORD's files that the zip lacks are dropped, as upstream drops them (`skip_missing_files`).
    assert [str(f) for f in dist.files] == ["judge_meta_b-2.0.dist-info/METADATA"]


@pytest.fixture(autouse=True)
def _no_private_modules_left():
    yield
    for name in [n for n in sys.modules if n.startswith("judge_zip_")]:
        del sys.modules[name]
