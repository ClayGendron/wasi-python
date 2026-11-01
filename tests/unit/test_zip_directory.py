"""The zip directory's reader on the host: the recipe modules `_zip_directory` and `_zip_resources`,
and the judge's own zips. They run on the judge's Python, which need not be the guest's version, so
each compares with the host's `zipfile`, never with the host's zipimport (whose reader differs
across versions)."""

from __future__ import annotations

import importlib.util
import io
import struct
import sys
import types
import zipfile
import zlib
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


def _local_offset_past_the_directory() -> bytes:
    """The second entry's local-header offset points past the directory's start: zipimport
    raises `ZipImportError('bad local header offset')`."""
    data = bytearray(zips.build({"a.py": "x = 1\n", "b.py": ""}))
    second = data.find(b"PK\x01\x02", data.find(b"PK\x01\x02") + 4)
    struct.pack_into("<I", data, second + 42, 0x7000)
    return bytes(data)


def _negative_archive_offset() -> bytes:
    """The end record's directory offset raised by 10, past where the directory stands, so
    zipimport's archive offset (the bytes before the zip) comes out negative."""
    data = bytearray(zips.build({"a.py": "x = 1\n"}))
    end = data.rfind(b"PK\x05\x06")
    struct.pack_into("<I", data, end + 16, struct.unpack_from("<I", data, end + 16)[0] + 10)
    return bytes(data)


def _zip64_extra_without_a_zip64_end() -> bytes:
    """An entry whose compressed size is 0xFFFFFFFF, with the real size in a Zip64 extra, and a
    plain end record (no `PK\x06\x06`), as streaming writers make it."""
    data = bytearray(zips.build({"a.py": "x = 1\n"}))
    cd, end = data.find(b"PK\x01\x02"), data.rfind(b"PK\x05\x06")
    size = struct.unpack_from("<I", data, cd + 20)[0]
    name_size, extra_size = struct.unpack_from("<HH", data, cd + 28)
    struct.pack_into("<I", data, cd + 20, 0xFFFFFFFF)
    extra = struct.pack("<HHQ", 1, 8, size)
    at = cd + 46 + name_size + extra_size
    data[at:at] = extra
    struct.pack_into("<H", data, cd + 30, extra_size + len(extra))
    end += len(extra)
    struct.pack_into("<I", data, end + 12, struct.unpack_from("<I", data, end + 12)[0] + len(extra))
    return bytes(data)


ODD = {
    "zip64": zips.zip64_zip(),
    "cp437": zips.cp437_zip(),
    "truncated": zips.truncated_zip(),
    "one entry more than declared": _understated(),
    "a local-header offset past the directory": _local_offset_past_the_directory(),
    "a negative archive offset": _negative_archive_offset(),
    "a Zip64 extra without a Zip64 end record": _zip64_extra_without_a_zip64_end(),
}


def test_the_odd_zips_have_what_they_claim() -> None:
    """Each hostile zip has its feature, so `test_odd_zips_go_to_the_stock_reader` never passes
    on a zip that lacks it."""

    def end_record(data: bytes) -> tuple[int, int, int]:
        end = data.rfind(b"PK\x05\x06")
        cd_size, cd_offset = struct.unpack_from("<II", data, end + 12)
        return end, cd_size, cd_offset

    data = ODD["a local-header offset past the directory"]
    _, _, cd_offset = end_record(data)
    offsets = [struct.unpack_from("<I", data, i + 42)[0] for i in _entries(data)]
    assert offsets[0] <= cd_offset < offsets[1]
    data = ODD["a negative archive offset"]
    end, cd_size, cd_offset = end_record(data)
    assert end - cd_size - cd_offset < 0
    data = ODD["a Zip64 extra without a Zip64 end record"]
    (cd,) = _entries(data)
    assert struct.unpack_from("<I", data, cd + 20)[0] == 0xFFFFFFFF
    assert b"PK\x06\x06" not in data
    with zipfile.ZipFile(io.BytesIO(data)) as z:  # zipfile reads the size from the extra
        assert z.read("a.py") == b"x = 1\n"


def _entries(data: bytes) -> list[int]:
    found, at = [], data.find(b"PK\x01\x02")
    while at >= 0:
        found.append(at)
        at = data.find(b"PK\x01\x02", at + 4)
    return found


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
    # `pwd`, zipfile.Path.open's keyword: None reads as usual; a password goes to zipfile, which
    # uses it only for an encrypted member (and ignores it, of any type, for a plain one).
    theirs = zipfile.Path(loader.archive, "d/t.txt")
    for pwd in (None, b"k", "k"):
        with t.open("rb", pwd=pwd) as f, theirs.open("rb", pwd=pwd) as g:
            assert f.read() == g.read() == text.encode(), pwd
        with t.open("r", pwd=pwd, encoding="utf-8") as f:
            assert f.read() == text, pwd
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
    opened: list = []

    def __init__(self, root, at=""):
        self.at = at
        _ZipfileStub.calls.append((root, at))

    def open(self, mode="r", *args, pwd=None, **kwargs):
        _ZipfileStub.opened.append((mode, args, pwd, kwargs))
        return io.BytesIO(b"from zipfile")


def test_a_password_goes_to_zipfile(zr, zd, work, monkeypatch) -> None:
    """A plain member opened with a password is zipfile's to open, with that password."""
    loader = _member_zip(work, zd, {"d/m.bin": (b"plain", zipfile.ZIP_DEFLATED)})
    _ZipfileStub.calls, _ZipfileStub.opened = [], []
    monkeypatch.setattr(zipfile, "Path", _ZipfileStub)
    member = zr.ZipDirectoryPath(loader) / "d/m.bin"
    assert member.read_bytes() == b"plain" and _ZipfileStub.calls == []
    assert member.open("rb", pwd=b"k").read() == b"from zipfile"
    assert _ZipfileStub.calls == [(loader.archive, "d/m.bin")]
    assert _ZipfileStub.opened == [("rb", (), b"k", {})]


def _patch(data: bytes, offset: int, value: bytes) -> bytes:
    return data[:offset] + value + data[offset + len(value) :]


@pytest.mark.parametrize(
    "case",
    [
        "plain",
        "lzma",
        "over 1 MiB",
        "bad crc",
        "encrypted",
        "local name",
        "inflates past",
        "stream not ended",
    ],
)
def test_the_member_reader_hands_odd_members_to_zipfile(zr, zd, work, monkeypatch, case) -> None:
    body = b"a member that inflates\n" * 50
    method = zipfile.ZIP_LZMA if case == "lzma" else zipfile.ZIP_DEFLATED
    if case == "over 1 MiB":
        body, method = b"x" * (zr.LIMIT + 1), zipfile.ZIP_STORED
    if case == "stream not ended":
        # A deflate stream with no final block: it inflates to every byte of the body, with the
        # right size and CRC, but it never ends. Written stored, then marked deflated.
        squeeze = zlib.compressobj(9, zlib.DEFLATED, -15)
        raw = squeeze.compress(body) + squeeze.flush(zlib.Z_SYNC_FLUSH)
        loader = _member_zip(work, zd, {"d/m.bin": (raw, zipfile.ZIP_STORED)})
    else:
        loader = _member_zip(work, zd, {"d/m.bin": (body, method)})
    data = Path(loader.archive).read_bytes()
    cd = data.rfind(b"PK\x01\x02")
    if case == "stream not ended":
        crc = struct.pack("<I", zlib.crc32(body))
        size = struct.pack("<I", len(body))
        deflate = struct.pack("<H", zipfile.ZIP_DEFLATED)
        for at, value in ((8, deflate), (14, crc), (22, size)):  # the local header
            data = _patch(data, at, value)
        for at, value in ((10, deflate), (16, crc), (24, size)):  # the directory entry
            data = _patch(data, cd + at, value)
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


def test_metadata_leaves_a_prefixed_zip_to_upstream(zr, zd, work, monkeypatch) -> None:
    """A zip on the import path under a prefix (`/x.zip/sub`) is not answered from the archive's
    root names: upstream's own `zip_children` gets it, as it gets a zip off the import path."""
    import zipimport

    archive = _write(work, "m.zip", zips.build({**zips.DISTRIBUTIONS, "sub/__init__.py": ""}))
    prefixed = f"{archive}/sub"
    monkeypatch.setattr(zipimport, "_read_directory", zd.read_directory)
    monkeypatch.setitem(sys.path_importer_cache, archive, zipimport.zipimporter(archive))
    monkeypatch.setitem(sys.path_importer_cache, prefixed, zipimport.zipimporter(prefixed))
    assert sys.path_importer_cache[prefixed].prefix == "sub/"
    calls = []
    zr.stock_zip_children = lambda self: calls.append(self.root) or {"stock": None}

    class Root:
        def __init__(self, root):
            self.root = root

    assert zr.zip_children(Root(prefixed)) == {"stock": None} and calls == [prefixed]
    assert "judge_meta_a-1.0.dist-info" in zr.zip_children(Root(archive))
    assert calls == [prefixed], "the archive's own root went to upstream"


@pytest.fixture(autouse=True)
def _no_private_modules_left():
    yield
    for name in [n for n in sys.modules if n.startswith("judge_zip_")]:
        del sys.modules[name]


# Part 4: the stdlib zip read by its folder table.

TABLED = [
    "a.pyc",
    "nsp/x/m.pyc",
    "pkg-1.0.dist-info/METADATA",
    "pkg/Upper.pyc",
    "pkg/__init__.py",
    "pkg/__init__.pyc",
    "pkg/data.txt",
    "pkg/sub/m.pyc",
    "top.pyc",
]


def _make_stdlib_zip():
    sys.path.insert(0, str(paths.REPO / "scripts"))
    try:
        import make_stdlib_zip
    finally:
        sys.path.remove(str(paths.REPO / "scripts"))
    return make_stdlib_zip


def _tabled(work: Path, names=TABLED, edit=None) -> str:
    """A zip of `names` with the folder table step 70 writes; `edit` rewrites the table's lines
    (after the version line) before it goes back in."""
    path = work / "t.zip"
    path.write_bytes(zips.build({n: n for n in names}))
    _make_stdlib_zip().write_folder_table(path)
    if edit is not None:
        data = path.read_bytes()
        with zipfile.ZipFile(path) as z:
            lines = z.comment.decode().splitlines()
        table = edit(lines[0], [line.split(" ") for line in lines[1:]])
        end = len(data) - 22 - len(z.comment)
        path.write_bytes(data[: end + 20] + struct.pack("<H", len(table)) + table)
    return str(path)


def _lines(head: str, rows: list[list]) -> bytes:
    return "".join(f"{line}\n" for line in [head, *(" ".join(map(str, r)) for r in rows)]).encode()


def _row(rows: list[list], folder: str) -> list:
    return next(r for r in rows if r[0] == folder)


def _with(rows, folder, **change):
    """The rows with one field of one folder's row changed by a function of the row."""
    out = [list(r) for r in rows]
    row = _row(out, folder)
    for i, name in enumerate(("off", "size", "count", "init", "inits"), 1):
        if name in change:
            row[i] = change[name](row)
    return out


def _entry_length(path: str, name: str) -> int:
    with zipfile.ZipFile(path) as z:
        info = z.getinfo(name)
    return 46 + len(name) + len(info.extra) + len(info.comment)


AT_START = {  # each malformation the start finds: the table's text, as an edit of its lines
    "absent": lambda head, rows: b"",
    "another version": lambda head, rows: _lines("wasi-python folders 2", rows),
    "a field not a number": lambda head, rows: _lines(
        head, _with(rows, "pkg", count=lambda r: "x")
    ),
    "a leading zero": lambda head, rows: _lines(head, _with(rows, "pkg", off=lambda r: "0" + r[1])),
    "no last LF": lambda head, rows: _lines(head, rows)[:-1],
    "out of order": lambda head, rows: _lines(head, rows[::-1]),
    "overlapping": lambda head, rows: _lines(
        head, _with(rows, "pkg", off=lambda r: int(rows[0][1]) + 1)
    ),
    "past the end": lambda head, rows: _lines(
        head, _with(rows, "pkg", size=lambda r: int(r[2]) * 100)
    ),
    "the walk misses a run": lambda head, rows: _lines(
        head, _with(rows, "pkg", off=lambda r: int(r[1]) - 1, size=lambda r: int(r[2]) + 1)
    ),
    "a run's first entry in another folder": lambda head, rows: _lines(
        head, [["zzz", *rows[0][1:]], *rows[1:]]
    ),
    "the counts do not add up": lambda head, rows: _lines(
        head, _with(rows, "pkg", count=lambda r: int(r[3]) + 1)
    ),
}


@pytest.mark.parametrize("case", AT_START)
def test_a_table_that_does_not_fit_gives_the_full_read(zd, work, case) -> None:
    archive = _tabled(work, edit=AT_START[case])
    zd.tabled = archive
    files = zd.read_directory(archive)
    assert zd.served == {archive: "fast"} and files == zd._fast(archive)
    assert archive not in zd._folders


def test_an_entry_read_at_start_in_a_tabled_folder_gives_the_full_read(zd, work) -> None:
    """The pkg run cut before its last entry, which the start would then read as its own."""
    path = _tabled(work)
    cut = _entry_length(path, "pkg/sub/m.pyc")
    archive = _tabled(
        work,
        edit=lambda head, rows: _lines(
            head,
            _with(rows, "pkg", size=lambda r: int(r[2]) - cut, count=lambda r: int(r[3]) - 1),
        ),
    )
    zd.tabled = archive
    assert zd.read_directory(archive) == zd._fast(archive) and zd.served[archive] == "fast"


def _cache(monkeypatch, archive: str, files: dict) -> None:
    import zipimport

    monkeypatch.setitem(zipimport._zip_directory_cache, archive, files)


def test_a_load_that_does_not_fit_gives_the_full_read_in_place(zd, work, monkeypatch) -> None:
    """The pkg run stretched over top.pyc: the start fits, the load finds another folder's name
    and replaces the dict's contents with the full read; so does an OSError at a load."""
    top = None

    def stretch(head, rows):
        nonlocal top
        return _lines(
            head, _with(rows, "pkg", size=lambda r: int(r[2]) + top, count=lambda r: int(r[3]) + 1)
        )

    top = _entry_length(_tabled(work), "top.pyc")
    archive = _tabled(work, edit=stretch)
    zd.tabled = archive
    files = zd.read_directory(archive)
    assert zd.served[archive] == "folders" and "pkg/data.txt" not in files
    _cache(monkeypatch, archive, files)
    zd.load_all(archive)
    assert files == zd._fast(archive) and zd.served[archive] == "fast"
    assert zd.tabled is None and archive not in zd._folders

    archive = _tabled(work)
    zd.tabled = archive
    files = zd.read_directory(archive)
    _cache(monkeypatch, archive, files)

    def refuse(*args, **kwargs):
        raise OSError("gone")

    stock_open = zd._io.open_code
    monkeypatch.setattr(zd, "_io", types.SimpleNamespace(open_code=refuse))
    zd.load_all(archive)  # the load's read fails, and so does the full read's: stock's turn
    monkeypatch.setattr(zd, "_io", types.SimpleNamespace(open_code=stock_open))
    assert zd.served[archive] == "stock"


def test_a_load_whose_read_fails_falls_back_to_the_full_read(zd, work, monkeypatch) -> None:
    archive = _tabled(work)
    zd.tabled = archive
    files = zd.read_directory(archive)
    _cache(monkeypatch, archive, files)
    real = zd._io.open_code
    calls = []

    def once(path):
        calls.append(path)
        if len(calls) == 1:
            raise OSError("the first open fails")
        return real(path)

    monkeypatch.setattr(zd, "_io", types.SimpleNamespace(open_code=once))
    zd.load_all(archive)
    assert files == zd._fast(archive) and zd.served[archive] == "fast"


def test_another_archives_table_is_read_whole(zd, work) -> None:
    archive = _tabled(work)
    zd.tabled = str(work / "the-stdlib.zip")
    assert zd.read_directory(archive) == zd._fast(archive)
    assert zd.served == {archive: "fast"}


def _children(files: dict) -> dict:
    out: dict = {}
    for name in files:
        if name:
            out.setdefault(name.rstrip("/").rpartition("/")[0], []).append(name)
    return out


def test_every_folder_loaded_gives_the_full_reads_dict(zd, work, monkeypatch) -> None:
    """At start a folder is its own name and its `__init__` entries, so zipimport tells a package
    from a namespace package; once every folder is loaded the dict equals the full read's, each
    folder's children in its order, and the top level's names in theirs."""
    archive = _tabled(work)
    zd.tabled = archive
    files = zd.read_directory(archive)
    assert zd.served == {archive: "folders"}
    assert set(files) == {
        "a.pyc",
        "nsp/",
        "pkg-1.0.dist-info/METADATA",
        "pkg-1.0.dist-info/",
        "pkg/",
        "pkg/__init__.py",
        "pkg/__init__.pyc",
        "top.pyc",
    }
    full = zd._fast(archive)
    assert [files[n] for n in ("pkg/__init__.pyc", "top.pyc")] == [
        full[n] for n in ("pkg/__init__.pyc", "top.pyc")
    ]
    tops = lambda f: list(dict.fromkeys(n.split("/", 1)[0] for n in f))  # noqa: E731
    assert tops(files) == tops(full)
    _cache(monkeypatch, archive, files)
    zd.load_all(archive)
    assert files == full and zd.loaded(archive) == ["nsp", "pkg"]
    mine, theirs = _children(files), _children(full)
    assert {k: v for k, v in mine.items() if k} == {k: v for k, v in theirs.items() if k}
    assert sorted(mine[""]) == sorted(theirs[""])


def test_a_trigger_after_invalidation_reads_again_first(zd, work, monkeypatch) -> None:
    """After `invalidate_caches()`, a trigger takes the dict through the importer's own
    `_get_files()`: the archive is read again, every folder loaded before is loaded again, and
    then the trigger's folder."""
    import zipimport

    archive = _tabled(work)
    for name in ("__init__", "get_data", "exec_module", "get_resource_reader"):
        monkeypatch.setattr(zipimport.zipimporter, name, getattr(zipimport.zipimporter, name))
    finder = zipimport._bootstrap_external.PathFinder
    monkeypatch.setattr(finder, "find_distributions", finder.__dict__["find_distributions"])
    monkeypatch.setattr(zipimport, "_read_directory", zipimport._read_directory)
    monkeypatch.delitem(zipimport._zip_directory_cache, archive, raising=False)
    zd.install(True, archive)
    try:
        importer = zipimport.zipimporter(archive)
        assert zd.served == {archive: "folders"} and zd.loaded(archive) == []
        sub = zipimport.zipimporter(f"{archive}/nsp/x")
        assert zd.loaded(archive) == ["nsp"] and sub.prefix == "nsp/x/"
        importer.invalidate_caches()
        assert importer.get_data(f"{archive}/pkg/data.txt") == b"pkg/data.txt"
        files = zipimport._zip_directory_cache[archive]
        assert zd.loaded(archive) == ["nsp", "pkg"] and "nsp/x/m.pyc" in files
        assert files == zd._fast(archive)
    finally:
        zipimport._zip_directory_cache.pop(archive, None)


def test_the_children_map_follows_a_load(zr, zd, work, monkeypatch) -> None:
    """The resource reader's map of each folder's children is rebuilt when a load grows the
    dict it was built from, and a lookup through the path loads its folder."""
    import zipimport

    archive = _tabled(work)
    zd.tabled = archive
    files = zd.read_directory(archive)
    _cache(monkeypatch, archive, files)
    zr.touch = zd.touch
    loader = FakeLoader(archive, files)
    root = zr.ZipDirectoryPath(loader)
    assert sorted(p.name for p in root.iterdir()) == ["a.pyc", "nsp", "pkg", "pkg-1.0.dist-info",
                                                      "top.pyc"]  # fmt: skip
    pkg = root / "pkg"
    assert [p.name for p in pkg.iterdir()] == ["Upper.pyc", "__init__.py", "__init__.pyc",
                                               "data.txt", "sub"]  # fmt: skip
    assert zd.loaded(archive) == ["pkg"]
    zd.load_all(archive)
    assert [p.name for p in (root / "nsp").iterdir()] == ["x"]
    assert zipimport._zip_directory_cache[archive] is files


# Part 3: the judge's zips folder, made by several processes at once.

CONCURRENT_ZIPS = r"""
import sys, zipfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from harness import paths, zips
paths.HARNESS_TMP = Path(sys.argv[2])
go = Path(sys.argv[4])
while not go.exists():  # a start line, not a timing: every process builds from cold together
    pass
made = zips.judge_zips(Path(sys.argv[3]))
with zipfile.ZipFile(made.small) as s, zipfile.ZipFile(made.padded) as p:
    whole = s.testzip() is None and p.testzip() is None
    print(len(s.namelist()), len(p.namelist()), whole, made.small.parent.name)
"""
PROCESSES, TRIALS, SOURCE_MEMBERS = 6, 3, 400


def test_the_judges_zips_folder_is_safe_across_processes(work) -> None:
    """Six processes build the folder from cold at once, three times: each gets both zips whole,
    one folder is published, and no work folder is left."""
    import subprocess

    source = work / "source.zip"
    source.write_bytes(zips.build({f"m{i}.py": f"x = {i}\n" * 40 for i in range(SOURCE_MEMBERS)}))
    small = SOURCE_MEMBERS + len(zips.DISTRIBUTIONS)
    expected = f"{small} {small + 3 * SOURCE_MEMBERS} True"
    tests = str(paths.REPO / "tests")
    for trial in range(TRIALS):
        harness_tmp, go = work / f"trial{trial}", work / f"go{trial}"
        children = [
            subprocess.Popen(
                [sys.executable, "-c", CONCURRENT_ZIPS, tests, str(harness_tmp), str(source),
                 str(go)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(PROCESSES)
        ]  # fmt: skip
        go.touch()
        answers = [child.communicate(timeout=120) for child in children]
        lines = [out.strip() for out, _ in answers]
        errors = [err.strip().splitlines()[-1:] for out, err in answers if not out.strip()]
        assert errors == [], (trial, errors)
        assert [line.rsplit(" ", 1)[0] for line in lines] == [expected] * PROCESSES, trial
        left = sorted(p.name for p in harness_tmp.iterdir())
        assert len(left) == 1 and left[0].startswith("zips-") and left[0].endswith("-v3"), left
        assert {line.rsplit(" ", 1)[1] for line in lines} == {left[0]}
