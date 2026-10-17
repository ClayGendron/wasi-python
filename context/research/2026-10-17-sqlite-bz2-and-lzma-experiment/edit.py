"""Experiment edits: link _bz2, _lzma and _sqlite3 into a scratch clone of the 3.15 line as builtins.

Run with the clone's root as the one argument, after `35_stdlib_libs.sh` is copied into its
scripts/steps/ and the three tarballs are pinned in its downloads/SHA256SUMS.
"""

import sys
from pathlib import Path

R = Path(sys.argv[1])


def sub(rel: str, *pairs: tuple[str, str]) -> None:
    p = R / rel
    s = p.read_text()
    for old, new in pairs:
        if old not in s:
            raise SystemExit(f"{rel}: no match for {old!r}")
        s = s.replace(old, new, 1)
    p.write_text(s)


ZLIB_GET = (
    "get https://github.com/madler/zlib/releases/download/v1.3.1/zlib-1.3.1.tar.gz zlib-1.3.1.tar.gz\n"
)
sub(
    "scripts/00_download.sh",
    (
        ZLIB_GET,
        ZLIB_GET
        + "get https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz bzip2-1.0.8.tar.gz\n"
        + "get https://github.com/tukaani-project/xz/releases/download/v5.8.4/xz-5.8.4.tar.gz xz-5.8.4.tar.gz\n"
        + "get https://sqlite.org/2026/sqlite-autoconf-3540100.tar.gz sqlite-autoconf-3540100.tar.gz\n",
    ),
)
sub("scripts/build.sh", ("30_zlib 40_numpy", "30_zlib 35_stdlib_libs 40_numpy"))

SQLITE_SRC = " ".join(
    f"_sqlite/{n}.c"
    for n in (
        "blob",
        "connection",
        "cursor",
        "microprotocols",
        "module",
        "prepare_protocol",
        "row",
        "statement",
        "util",
    )
)
sub(
    "scripts/steps/60_link.sh",
    (
        '  echo "zlib zlibmodule.c -I$B/zlib-wasi/include $B/zlib-wasi/lib/libz.a"\n',
        '  echo "zlib zlibmodule.c -I$B/zlib-wasi/include $B/zlib-wasi/lib/libz.a"\n'
        '  echo "_bz2 _bz2module.c -I$B/stdlib-libs/include $B/stdlib-libs/lib/libbz2.a"\n'
        '  echo "_lzma _lzmamodule.c -I$B/stdlib-libs/include $B/stdlib-libs/lib/liblzma.a"\n'
        # What configure would have defined had it found the library (configure.ac: sqlite3_serialize).
        # No '=' in the line: makesetup reads any line holding '=' as a Make variable definition.
        f'  echo "_sqlite3 {SQLITE_SRC} -I$CP/Modules/_sqlite -I$B/stdlib-libs/include'
        ' -DPY_SQLITE_HAVE_SERIALIZE $B/stdlib-libs/lib/libsqlite3.a"\n',
    ),
)
sub(
    "scripts/assemble_artifacts.py",
    ('    "zlib": "1.3.1",\n', '    "zlib": "1.3.1",\n    "bzip2": "1.0.8",\n    "xz": "5.8.4",\n    "sqlite-autoconf": "3540100",  # SQLite 3.54.1, named as its pin names it\n'),
    (
        '        "zlib": [("zlib LICENSE", (b / "zlib-1.3.1" / "LICENSE").read_bytes())],\n',
        '        "zlib": [("zlib LICENSE", (b / "zlib-1.3.1" / "LICENSE").read_bytes())],\n'
        '        "bzip2": [("bzip2 LICENSE", (b / "bzip2-1.0.8" / "LICENSE").read_bytes())],\n'
        '        "xz": [(f"xz {n}", (b / "xz-5.8.4" / n).read_bytes()) for n in ("COPYING", "COPYING.0BSD")],\n'
        '        "sqlite": [("SQLite sqlite3.h (public domain: its header comment)",\n'
        '                    (b / "sqlite-autoconf-3540100" / "sqlite3.h").read_bytes().split(b"*/")[0] + b"*/\\n")],\n',
    ),
)
print("edits applied")
