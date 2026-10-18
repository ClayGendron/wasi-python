"""The zips spec 035's checks run on (Decision 11), made on the host.

- `small.zip`: the artifact zip, appended to with two made-up distributions. Append mode keeps
  every existing member's bytes, so an import from it costs what it costs from the artifact zip.
- `padded.zip`: `small.zip` plus a copy of each artifact member under `pad1/`, `pad2/` and
  `pad3/`, at zlib level 1. Nothing imports from them; they only lengthen the directory, so the
  fuel difference between the two zips, over their member counts, is a cost per member.
- The odd zips (Zip64, a cp437 name, explicit directories, prepended bytes and a comment, a
  truncated directory) and a guest's resource zip (an LZMA member, a bad CRC, a 2 MiB member).
  Each is made in memory and checked for the feature it must have (`check_*`), so a check never
  passes on a zip that lacks it.

`judge_zips(artifact_zip)` makes `small.zip` and `padded.zip` once per artifact zip, under
build/harness/zips-<the zip's hash>-v2/, and reuses them while that zip is unchanged.
"""

from __future__ import annotations

import hashlib
import io
import os
import shutil
import struct
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from harness import paths

DATE = (2026, 1, 1, 0, 0, 0)
PADS = ("pad1/", "pad2/", "pad3/")
GROUP = "judge.zip_directory"
# The judge's two distributions: names spec 033's cannot clash with.
DISTRIBUTIONS = {
    "judge_meta_a-1.0.dist-info/METADATA": (
        "Metadata-Version: 2.1\nName: judge_meta_a\nVersion: 1.0\nSummary: the judge's first\n"
    ),
    "judge_meta_b-2.0.dist-info/METADATA": (
        "Metadata-Version: 2.1\nName: judge-meta-b\nVersion: 2.0\n"
        "Requires-Dist: judge_meta_a>=1.0\n\nA body.\n"
    ),
    "judge_meta_b-2.0.dist-info/entry_points.txt": (
        f"[{GROUP}]\nfirst = judge_meta_b.one:main\nsecond = judge_meta_b.two:run [extra]\n"
    ),
    "judge_meta_b-2.0.dist-info/RECORD": (
        "judge_meta_b/__init__.py,sha256=47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU,0\n"
        "judge_meta_b-2.0.dist-info/METADATA,,\n"
    ),
}


def _info(name: str, method: int = zipfile.ZIP_DEFLATED) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, DATE)
    info.compress_type = method
    info.external_attr = 0o644 << 16
    return info


def build(members: dict[str, bytes | str], *, comment: bytes = b"") -> bytes:
    """A zip of `members`, deflated and dated alike, in order; a name ending in `/` is a folder."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name, data in members.items():
            if name.endswith("/"):
                z.writestr(_info(name, zipfile.ZIP_STORED), b"")
            else:
                z.writestr(_info(name), data)
        z.comment = comment
    return out.getvalue()


def zip64_zip() -> bytes:
    """A module `zip64_mod` in a zip with a Zip64 end record and Zip64 extras: zipfile writes
    them for a small zip only with its limits lowered (the review's `odd.py`)."""
    old = zipfile.ZIP64_LIMIT, zipfile.ZIP_FILECOUNT_LIMIT
    zipfile.ZIP64_LIMIT, zipfile.ZIP_FILECOUNT_LIMIT = 8, 2
    try:
        return build({"zip64_mod.py": "WHO = 'zip64'\n", "pkg64/__init__.py": "", "pkg64/m.py": ""})
    finally:
        zipfile.ZIP64_LIMIT, zipfile.ZIP_FILECOUNT_LIMIT = old


CP437_MODULE = "café_437"  # é is byte 0x82 in cp437


def cp437_zip() -> bytes:
    """A module named in cp437, without the UTF-8 flag: written under an ASCII name of the same
    length, whose bytes are then replaced in the local header and the directory."""
    raw = f"{CP437_MODULE}.py".encode("cp437")
    stand_in = b"cafX_437.py"
    assert len(raw) == len(stand_in)
    data = build({stand_in.decode(): "WHO = 'cp437'\n"})
    assert data.count(stand_in) == 2
    return data.replace(stand_in, raw)


def explicit_dirs_zip() -> bytes:
    return build(
        {
            "xdir/": b"",
            "xdir/__init__.py": "",
            "xdir/sub/": b"",
            "xdir/sub/m.py": "WHO = 'explicit'\n",
            "top.py": "",
        }
    )


PREPENDED = b"#!/bin/sh\necho not a zip\nexit 0\n" * 20


def prepended_zip() -> bytes:
    return PREPENDED + build(
        {"pre_mod.py": "WHO = 'prepended'\n", "prepkg/__init__.py": "", "prepkg/a/b.py": ""},
        comment=b"an archive comment",
    )


def truncated_zip() -> bytes:
    """Three entries declared, the directory cut inside the third: the end record says so."""
    data = build({"t1.py": "", "t2.py": "", "t3.py": ""})
    end = data.rfind(b"PK\x05\x06")
    cd_size, cd_offset = struct.unpack_from("<II", data, end + 12)
    cut = data.rfind(b"PK\x01\x02") + 20
    tail = bytearray(data[end:])
    struct.pack_into("<I", tail, 12, cut - cd_offset)
    return data[:cut] + bytes(tail)


RESOURCE_PACKAGE = "guest_res"
BIG = 2 * 1024 * 1024


def _big_bytes() -> bytes:
    return b"".join(hashlib.sha256(i.to_bytes(4, "little")).digest() for i in range(BIG // 32))


def resource_zip() -> bytes:
    """A guest's package with an LZMA member, a member whose stored CRC is wrong, a stored member
    of 2 MiB and a plain one."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr(_info(f"{RESOURCE_PACKAGE}/__init__.py"), "")
        z.writestr(_info(f"{RESOURCE_PACKAGE}/lzma.txt", zipfile.ZIP_LZMA), "lzma " * 400)
        z.writestr(_info(f"{RESOURCE_PACKAGE}/badcrc.txt"), "a member whose CRC lies\n" * 20)
        z.writestr(_info(f"{RESOURCE_PACKAGE}/big.bin", zipfile.ZIP_STORED), _big_bytes())
        z.writestr(_info(f"{RESOURCE_PACKAGE}/plain.txt"), "plain\n")
    data = bytearray(out.getvalue())
    with zipfile.ZipFile(io.BytesIO(bytes(data))) as z:
        info = z.getinfo(f"{RESOURCE_PACKAGE}/badcrc.txt")
    bad = struct.pack("<I", info.CRC ^ 0xFFFFFFFF)
    good = struct.pack("<I", info.CRC)
    assert data.count(good) == 2  # the local header's and the directory's
    return bytes(data).replace(good, bad)


ODD_ZIPS = {
    "zip64": zip64_zip,
    "cp437": cp437_zip,
    "explicit_dirs": explicit_dirs_zip,
    "prepended": prepended_zip,
    "truncated": truncated_zip,
}


def check_zip64(data: bytes) -> None:
    assert b"PK\x06\x06" in data, "no Zip64 end record"
    cd = data.find(b"PK\x01\x02")
    assert struct.unpack_from("<I", data, cd + 20)[0] == 0xFFFFFFFF, "no 0xFFFFFFFF field"


def check_cp437(data: bytes) -> None:
    cd = data.find(b"PK\x01\x02")
    (flags,) = struct.unpack_from("<H", data, cd + 8)
    (size,) = struct.unpack_from("<H", data, cd + 28)
    assert not flags & 0x800, "the UTF-8 flag is set"
    assert any(b >= 0x80 for b in data[cd + 46 : cd + 46 + size]), "the name is ASCII"


def check_resource_zip(data: bytes) -> None:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos = {i.filename.rpartition("/")[2]: i for i in z.infolist()}
        assert infos["lzma.txt"].compress_type == zipfile.ZIP_LZMA
        assert infos["big.bin"].file_size == BIG
        assert infos["big.bin"].compress_type == zipfile.ZIP_STORED
        try:
            z.read(infos["badcrc.txt"])
        except zipfile.BadZipFile:
            pass
        else:
            raise AssertionError("badcrc.txt reads")


def _members(path: Path) -> int:
    with zipfile.ZipFile(path) as z:
        return len(z.infolist())


def make_small(artifact_zip: Path, out: Path) -> None:
    shutil.copyfile(artifact_zip, out)
    with zipfile.ZipFile(out, "a") as z:
        for name, text in DISTRIBUTIONS.items():
            z.writestr(_info(name), text)


def make_padded(small: Path, artifact_zip: Path, out: Path) -> None:
    shutil.copyfile(small, out)
    with zipfile.ZipFile(artifact_zip) as src, zipfile.ZipFile(out, "a") as z:
        members = [(i, src.read(i)) for i in src.infolist()]
        for pad in PADS:
            for info, data in members:
                copy = zipfile.ZipInfo(pad + info.filename, info.date_time)
                copy.compress_type = info.compress_type
                copy.external_attr = info.external_attr
                z.writestr(copy, data, compresslevel=1)


@dataclass(frozen=True)
class JudgeZips:
    small: Path
    padded: Path
    small_members: int
    padded_members: int

    def slope(self, small_fuel: int, padded_fuel: int) -> float:
        """Fuel per member between the two zips."""
        return (padded_fuel - small_fuel) / (self.padded_members - self.small_members)


def judge_zips(artifact_zip: Path) -> JudgeZips:
    """The two zips, made once per artifact zip and safe across processes (spec 052, Decision 13).

    Each process builds in its own work folder and publishes it with one rename. A home that
    exists is complete, since a rename of a finished build is the only way one comes to exist,
    and no home is ever removed: a process that loses the rename drops its own work folder and
    uses the one that won. The `-v2` name leaves any folder an earlier version made unread."""
    sha = paths.sha256_file(artifact_zip)[:16]
    home = paths.HARNESS_TMP / f"zips-{sha}-v2"
    if not home.is_dir():
        paths.HARNESS_TMP.mkdir(parents=True, exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix="zips-work-", dir=paths.HARNESS_TMP))
        try:
            make_small(artifact_zip, work / "small.zip")
            make_padded(work / "small.zip", artifact_zip, work / "padded.zip")
            os.rename(work, home)
        except OSError:
            shutil.rmtree(work, ignore_errors=True)
            if not home.is_dir():  # not another process's finished folder: a real error
                raise
    small, padded = home / "small.zip", home / "padded.zip"
    return JudgeZips(small, padded, _members(small), _members(padded))
