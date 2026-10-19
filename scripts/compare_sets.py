#!/usr/bin/env python3
"""Compare a rebuilt artifact set (and its wheel) with a release's (spec 037, Decision 17).

Usage: uv run python scripts/compare_sets.py SET REBUILT [--wheels RELEASE.whl REBUILT.whl]

SET is a folder holding SHA256SUMS and the files it lists (a release's set, or build/artifacts).
REBUILT is a folder holding the rebuild's SHA256SUMS, and either the rebuilt files or, given
--wheels, nothing else: the rebuilt binaries are then the rebuilt wheel's own copies.

They are the same bytes when:
- every file of SET hashes to its line of SET's SHA256SUMS;
- the rebuild's SHA256SUMS is the set's, byte for byte, but the digests on the lines of the
  artifacts that recipes/same_bytes_exceptions.toml names, which may differ;
- each rebuilt file whose line differs hashes to that line (a stale or mixed-up file proves
  nothing) and passes scripts/same_bytes.py against SET's file;
- given --wheels, the two wheels hold the same entries in the same order with the same metadata
  and bytes, but the differing binaries' entries (each the compared file itself), SHA256SUMS (each
  its own set's) and RECORD's lines for those (each right for its own wheel's bytes).

A rebuild with the same SHA256SUMS must give a byte-identical wheel. Standard library only; exit
status 0 when the same bytes, 1 (with the reason) when not.
"""

from __future__ import annotations

import base64
import hashlib
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import same_bytes  # noqa: E402

ARTIFACTS = "wasi_python/artifacts/"


class Differs(Exception):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_sums(text: str) -> list[tuple[str, str]]:
    out = []
    for line in text.splitlines():
        digest, sep, name = line.partition("  ")
        if not sep or len(digest) != 64 or set(digest) - set("0123456789abcdef") or not name:
            raise Differs(f"a SHA256SUMS line is not '<sha256>  <name>': {line!r}")
        out.append((digest, name))
    return out


def _record_line(path: str, data: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
    return f"{path},sha256={digest},{len(data)}"


def _meta(info: zipfile.ZipInfo) -> tuple:
    return (
        info.filename,
        info.date_time,
        info.compress_type,
        info.comment,
        info.extra,
        info.create_system,
        info.create_version,
        info.extract_version,
        info.flag_bits,
        info.internal_attr,
        info.external_attr,
    )


def compare_wheels(
    release: zipfile.ZipFile,
    rebuilt: zipfile.ZipFile,
    own: dict[str, tuple[bytes, bytes]],
) -> None:
    """`own` maps each entry allowed to differ (the binaries and SHA256SUMS, by their path in the
    wheel) to the bytes each wheel must hold there: the set's, then the rebuild's."""
    a, b = release.infolist(), rebuilt.infolist()
    if [i.filename for i in a] != [i.filename for i in b]:
        only = sorted({i.filename for i in a} ^ {i.filename for i in b})
        raise Differs(f"the wheels hold other entries or another order (only in one: {only})")
    if release.comment != rebuilt.comment:
        raise Differs("the wheels' archive comments differ")
    for x, y in zip(a, b, strict=True):
        if _meta(x) != _meta(y):
            raise Differs(f"{x.filename}: the entries' metadata differ")
        da, db = release.read(x), rebuilt.read(y)
        if x.filename in own:
            want_a, want_b = own[x.filename]
            if (da, db) != (want_a, want_b):
                raise Differs(f"{x.filename}: a wheel's entry is not its own set's file")
        elif x.filename.endswith(".dist-info/RECORD"):
            la, lb = da.decode().splitlines(), db.decode().splitlines()
            if len(la) != len(lb):
                raise Differs("the wheels' RECORDs have other lines")
            for ra, rb in zip(la, lb, strict=True):
                path = ra.split(",", 1)[0]
                if path in own:
                    want = (_record_line(path, own[path][0]), _record_line(path, own[path][1]))
                    if (ra, rb) != want:
                        raise Differs(f"RECORD's line for {path} is not its own wheel's file")
                elif ra != rb:
                    raise Differs(f"RECORD's line for {path} differs")
        elif (da, x.CRC, x.file_size, x.compress_size) != (db, y.CRC, y.file_size, y.compress_size):
            raise Differs(f"{x.filename}: the entries differ")


def compare_sets(
    set_dir: Path,
    rebuilt_dir: Path,
    wheels: tuple[Path, Path] | None = None,
    root: Path = same_bytes.ROOT,
) -> list[str]:
    """One line per file that differs and why that is allowed; raises Differs when it is not."""
    set_text = (set_dir / "SHA256SUMS").read_bytes()
    rebuilt_text = (rebuilt_dir / "SHA256SUMS").read_bytes()
    set_sums, rebuilt_sums = read_sums(set_text.decode()), read_sums(rebuilt_text.decode())
    for digest, name in set_sums:
        if sha256((set_dir / name).read_bytes()) != digest:
            raise Differs(f"the set's {name} is not its SHA256SUMS line")
    zips = tuple(zipfile.ZipFile(w) for w in wheels) if wheels else None

    def rebuilt_file(name: str) -> bytes:
        found = []
        if (rebuilt_dir / name).is_file():
            found.append((rebuilt_dir / name).read_bytes())
        if zips and ARTIFACTS + name in zips[1].namelist():
            found.append(zips[1].read(ARTIFACTS + name))
        if not found:
            raise Differs(f"the rebuild's {name} is neither in {rebuilt_dir} nor in its wheel")
        if any(f != found[0] for f in found):
            raise Differs(f"the rebuild's {name} differs from its wheel's copy")
        return found[0]

    if [n for _, n in set_sums] != [n for _, n in rebuilt_sums]:
        raise Differs("the rebuild's SHA256SUMS lists other files or another order")
    report, own = [], {}
    recipe = None
    for (want, name), (have, _) in zip(set_sums, rebuilt_sums, strict=True):
        if want == have:
            continue
        if recipe is None:
            recipe = same_bytes.load_recipe(root)
        functions = tuple(f for e in recipe if name in e.artifacts for f in e.functions)
        if not functions:
            raise Differs(f"the rebuild's {name} differs and no exception names it")
        data = rebuilt_file(name)
        if sha256(data) != have:
            raise Differs(f"the rebuild's {name} is not its own SHA256SUMS line")
        try:
            named = same_bytes.compare((set_dir / name).read_bytes(), data, functions)
        except same_bytes.Refused as e:
            raise Differs(f"{name}: {e}") from None
        report.append(
            f"{name}: the same bytes but where {len(named)} named functions open a try_table"
        )
        own[ARTIFACTS + name] = ((set_dir / name).read_bytes(), data)
    # The rebuild's SHA256SUMS as bytes: the set's, with only the exception lines' digests
    # replaced (the implementation review's I2: line ends and the last newline count).
    expected = set_text
    for (want, name), (have, _) in zip(set_sums, rebuilt_sums, strict=True):
        if want != have:
            line = f"{want}  {name}\n".encode()
            if expected.count(line) != 1:
                raise Differs(f"the set's SHA256SUMS has no single line for {name}")
            expected = expected.replace(line, f"{have}  {name}\n".encode())
    if rebuilt_text != expected:
        raise Differs(
            "the rebuild's SHA256SUMS is not the set's bytes with only the exception lines' "
            "digests replaced"
        )
    if own:
        own[ARTIFACTS + "SHA256SUMS"] = (set_text, rebuilt_text)
    if zips:
        if not own and wheels[0].read_bytes() != wheels[1].read_bytes():
            compare_wheels(*zips, own)
            raise Differs("the wheels are not byte for byte equal though SHA256SUMS is")
        compare_wheels(*zips, own)
    return report


def main(argv: list[str]) -> int:
    wheels = None
    if len(argv) == 5 and argv[2] == "--wheels":
        wheels, argv = (Path(argv[3]), Path(argv[4])), argv[:2]
    if len(argv) != 2:
        print("usage: uv run python scripts/compare_sets.py SET REBUILT [--wheels A.whl B.whl]")
        return 2
    try:
        report = compare_sets(Path(argv[0]), Path(argv[1]), wheels)
    except (Differs, same_bytes.Refused) as e:
        print(f"{argv[1]}: not the same bytes as {argv[0]}: {e}")
        return 1
    for line in report:
        print(f"{argv[1]}: {line}")
    print(f"{argv[1]}: the same bytes as {argv[0]}" + (" (and the same wheel)" if wheels else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
