# sqlite3, bz2 and lzma as builtins on the 3.15 line

- **Status:** executed, 2026-10-17. Box: about 2.5 hours; used under one hour of wall time.
- **Owner:** Clay Gendron
- **Researcher:** the author agent (Claude Opus 5.5), on the owner's ordered post-v1 list
  (constitution §2: matplotlib, then "the stdlib modules WASI lacks (sqlite, bz2, lzma)").
- **Feeds:** the specification that adds the three modules; `../constitution.md` §4.12 (the
  owner approves every linked licence); the `-V` sentence (`recipes/reactor_bootstrap.py`).
- **Stands on:** `2026-10-16-the-cpython-3-15-and-wasi-sdk-33-line.md` (the line and the
  experiment pattern), `2026-10-16-what-data-folders-the-packages-need.md` §9 (SQLite's lock
  directory and temp files, READ there; run here).
- **Evidence:** `2026-10-17-sqlite-bz2-and-lzma-experiment/`. `setup.sh` clones this repository
  into a scratch directory, fetches and checks the three tarballs, adds the step file
  `35_stdlib_libs.sh` and runs `edit.py`. Nothing in this repository's build or tracked files
  changed. `outputs/` holds every number quoted below.
- **Machine (benchmark facts only):** Apple arm64, macOS 26.5, wasmtime 49 (CLI and
  wasmtime-py 49.0.0).

## The question

The 3.15 line (CPython 3.15.0, wasi-sdk 33, `scripts/line.conf`) builds without `_sqlite3`,
`_bz2` and `_lzma`. Can they be built in as builtins, from pinned sources, with zero upstream
patches? What does each cost? What works inside the guest, and what does not?

## Method

- **Pins (EXECUTED).** Each tarball was downloaded into its own empty directory, hashed, and
  cross-checked against a published value. GPG ran with a throwaway keyring in the scratch
  directory.
- **Build (EXECUTED).** A scratch clone of commit `360b51b`. First the unchanged recipe, steps
  10 to 90 (the *baseline*). Then a new step 35 and three `Setup.local` lines, steps 35 to 90.
- **Guest runs (EXECUTED).** `measure.py` runs fixed programs through the judge's own driver
  (`tests/harness/guest.py`), so fuel is exact. `drive_lock.py` runs the crash and lock stages
  through the product runner, `wasi_python.run`, with `WASI_PYTHON_ARTIFACTS` set to the clone's
  artifacts. Each probe ran on the snapshot and on the plain reactor.
- **Native comparison (EXECUTED).** `native.py` runs the same probes under the clone's oracle:
  the line's pinned host Python 3.15.0 (python-build-standalone) with the guest's package pins.
- **The judge (EXECUTED).** `uv run pytest` in the clone, on the baseline and on the new set.

## Findings

### 1. The pins

| file | URL | SHA-256 | cross-check | licence |
|---|---|---|---|---|
| `sqlite-autoconf-3540100.tar.gz` (3,332,984 B) | `https://sqlite.org/2026/sqlite-autoconf-3540100.tar.gz` | `926ef8d3eab93fbf6e06011901273eec076b25594a4e1cdadd50c987f4f6d64e` | SHA3-256 `b6ced585…57d9c4` equals sqlite.org's download page | public domain (the blessing in each file's header) |
| `bzip2-1.0.8.tar.gz` (810,029 B) | `https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz` | `ab5a03176ee106d3f0fa90e381da478ddae405918153cca248e682cd0c4a2269` | good signature, key `12768A96795990107A0D2FDFFC57E3CCACD99A78` (Mark Wielaard) | bzip2's own BSD-style licence (`LICENSE`) |
| `xz-5.8.4.tar.gz` (2,799,797 B) | `https://github.com/tukaani-project/xz/releases/download/v5.8.4/xz-5.8.4.tar.gz` | `0014c7886930454fe8bd4228665b51af55eeae560ea135c9c4cd33f55b2591d9` | equals GitHub's asset digest; good signature, key `3690C240CE51B4670D30AD1C38EE757D69184620` (Lasse Collin) | liblzma is 0BSD (`COPYING`, `COPYING.0BSD`) |

- All EXECUTED on 2026-10-17. SQLite 3.54.1 and xz 5.8.4 (2026-09-09) were the latest
  releases that day. bzip2 1.0.8 is the newest tarball in sourceware's `pub/bzip2/`.
- sqlite.org's URL carries the release year (`/2026/`). SQLite publishes SHA3-256 only.
  sourceware publishes a signature, not a hash. The GPG keys came from public keyservers, so
  they prove the signer's key, not the signer's identity (gpg says `[unknown]` trust).
- The SQLite tarball is the "autoconf" amalgamation: `sqlite3.c`, `sqlite3.h`,
  `sqlite3ext.h`, and a build system this recipe does not use.
- Only liblzma is linked from xz. The GPL and LGPL files in the tarball (scripts, `getopt`,
  build-system files) are not compiled (READ: xz's `COPYING`).

### 2. Building the three libraries: no recipe file beyond the step script (EXECUTED)

One new step, `scripts/steps/35_stdlib_libs.sh`, builds three static archives into
`build/stdlib-libs/`. It takes 35.1 s on this machine (benchmark fact). Each source tree is
unpacked from its tarball and compiled from outside it. After the build, `diff -r` of each tree
against a fresh unpack finds no difference (`outputs/source-trees.txt`).

- **bzip2.** Its Makefile builds in the source tree. So the step compiles the seven files of
  its `libbz2.a` target itself, with the Makefile's flags less `-g`
  (`-O2 -D_FILE_OFFSET_BITS=64`), and archives them with `llvm-ar rcD`. 80,798 bytes. No
  warning.
- **xz.** Its own autotools `configure`, run from a separate build directory, with
  `--host=wasm32-unknown-wasip1 --disable-shared --enable-static --disable-threads`, and the
  tools, scripts, docs and translations off. xz's `config.sub` knows `wasm32-wasip1`.
  Configure chose `sysconf` for the core count and memory size, no CLMUL, no threads. All
  encoders, decoders and checks (CRC32, CRC64, SHA-256) are in. `make -C src/liblzma`;
  `liblzma.a` is 213,672 bytes. No hand-written config header was needed.
- **SQLite.** One `clang -O2 -c sqlite3.c`. No configure. SQLite already supports WASI in its
  own source (READ: `sqlite3.c:11774-11782`, `:40844-40866`). On `__wasi__` it sets
  `SQLITE_WASI`, `SQLITE_THREADSAFE=0` and `SQLITE_OMIT_LOAD_EXTENSION`. It drops `mmap`,
  `fchmod`, `fchown` and the WAL shared-memory code, fakes `getpid`, and defaults to the
  `unix-dotfile` locking style. The step names `THREADSAFE=0`, `OMIT_LOAD_EXTENSION` and
  `MAX_MMAP_SIZE=0` again, so the command line says what the build is. It adds the feature set
  of the native host Python's SQLite (`PRAGMA compile_options` of python-build-standalone
  3.15.0): `ENABLE_FTS3`, `FTS3_PARENTHESIS`, `FTS4`, `FTS5`, `RTREE`, `GEOPOLY`,
  `MATH_FUNCTIONS`, `DBSTAT_VTAB`, `PERCENTILE`. 2,048,884 bytes. No warning.
- `SQLITE_OMIT_WAL`, `SQLITE_DEFAULT_LOCKING_MODE` and `SQLITE_DEFAULT_UNIX_VFS` were not
  needed. Finding 5 says what each locking choice does.

### 3. Linking them in: three `Setup.local` lines; one trap (EXECUTED)

Step 60 already writes the build directory's `Modules/Setup.local`. Three lines more, after
`zlib`, built from CPython's own module sources:

```
_bz2 _bz2module.c -I<stdlib-libs>/include <stdlib-libs>/lib/libbz2.a
_lzma _lzmamodule.c -I<stdlib-libs>/include <stdlib-libs>/lib/liblzma.a
_sqlite3 _sqlite/blob.c … _sqlite/util.c -I<cpython>/Modules/_sqlite -I<stdlib-libs>/include -DPY_SQLITE_HAVE_SERIALIZE <stdlib-libs>/lib/libsqlite3.a
```

- **The trap.** The first try wrote `-DPY_SQLITE_HAVE_SERIALIZE=1`. `makesetup` reads any line
  holding `=` as a Make variable definition (READ: `Modules/makesetup`, `case $line in *=*)`).
  So the `_sqlite3` line was silently dropped. The build passed. The reactor grew by only
  214,238 bytes, and `_sqlite3` was missing from `Modules/config.c`. Without the `=`, the
  module links. A check that imports each module catches this; the clash detector does not.
- `PY_SQLITE_HAVE_SERIALIZE` is what CPython's `configure` defines when the library has
  `sqlite3_serialize` (READ: `configure.ac`). Without it, `Connection.serialize` and
  `deserialize` are missing.
- No symbol clash: step 60's detector (`signature mismatch`, `duplicate symbol`) found none.
- **The alternative, CPython's own `configure`.** Given
  `LIBSQLITE3_CFLAGS=-I<dir> LIBSQLITE3_LIBS="-L<dir> -lsqlite3"` and the same for `BZIP2_*`
  and `LIBLZMA_*` after `--`, `Platforms/WASI configure-host` turns all three modules on
  (`MODULE__SQLITE3_STATE=yes`, `_BZ2`, `_LZMA` the same) and defines
  `PY_SQLITE_HAVE_SERIALIZE` itself (`outputs/configure-route.txt`). Only configure ran; the
  build through it was not run. This route makes step 20 depend on the libraries, so step 35
  moves before step 20, and a change to SQLite's options rebuilds CPython.

### 4. bz2 and lzma work, and match native byte for byte (EXECUTED)

`probe_compress.py`, on the snapshot, the plain reactor and native 3.15.0:

- `bz2.compress` at levels 1 and 9, the incremental decompressor, `bz2.open` text files;
- `lzma` in the `.xz` and `.lzma` (`FORMAT_ALONE`) formats at presets 0, 6 and 9|extreme;
  all four checks; a raw delta + LZMA2 chain; the x86 and ARM BCJ filters; `lzma.open`;
- `tarfile` written and read with `w:bz2`/`r:bz2`, `w:xz`/`r:xz` and `r:*`, and `extractall`;
  `shutil.make_archive(..., "xztar")`; `zipfile` with `ZIP_BZIP2` and `ZIP_LZMA`.

Every line is identical across the three runs: the compressed lengths and the SHA-256 of the
compressed bytes too. One line differs: native lists a `zstdtar` archive format and the guest
does not. `compression.zstd` needs `_zstd` (libzstd), a fourth compression module the WASI
build lacks (EXECUTED: `ModuleNotFoundError: No module named '_zstd'`).

### 5. sqlite3 works, with WASI's locking limits (EXECUTED)

`probe_sqlite.py`, on the snapshot, the plain reactor and native. Snapshot and plain agree on
every line.

**The same as native:** in memory and on a file in the root: create, `executemany`, queries,
JSON, math functions, window functions, FTS5, R-tree, `create_function`,
`create_aggregate`, `create_collation`, `serialize`/`deserialize`, `blobopen`, `iterdump`,
`backup` (to memory and to a file), a read-only URI that refuses writes, `VACUUM`, a temporary
table, a sort of 10,006 random 200-byte rows, rollback and commit; `journal_mode` `delete`
(the default), `truncate`, `persist`, `memory` and `off`. `DataFrame.to_sql` then
`pandas.read_sql` (a group-by) and `read_sql_query(parse_dates=...)` give the same frame as
native, `equals` true.

**Different from native:**

| case | native 3.15.0 | guest |
|---|---|---|
| `enable_load_extension` | present | absent (compiled out on WASI) |
| a write transaction is open | `t.db`, `t.db-journal` | also `t.db.lock`, a directory |
| a second connection reads while the first holds a write | reads | `database is locked` |
| `PRAGMA journal_mode=wal` | `wal` | stays `delete`, no error |
| WAL after `locking_mode=exclusive` | `wal` | `wal`, works (no shared memory needed) |
| `?vfs=unix` or `?vfs=unix-excl` (POSIX locks) | works | `disk I/O error` |
| `?vfs=unix-none` | works | works |

- **Why (READ, `sqlite3.c`).** The `unix-dotfile` style locks by creating `<db>.lock` with
  `mkdir` (`dotlockLock`, `:43146`). Any lock is exclusive: "a single reader blocks all other
  connections" (`:43078`). WAL in normal locking mode needs the shared-memory index, which is
  compiled out on WASI (`:42489`). wasi-libc's `fcntl` has no record locks, so the POSIX styles
  fail.
- **Python's own connections in one program lock each other out** while a write is open.
  Code that keeps two connections and writes through one while reading through the other gets
  `database is locked`.

### 6. A guest that dies in a transaction leaves the database locked (EXECUTED)

`drive_lock.py`, stage by stage on one root, plain and snapshot alike (`outputs/lock.txt`):

1. A guest opens a write transaction that spills to the file, then ends by `os._exit(3)`, or
   by running out of fuel (a trap). Both leave `k.db`, `k.db-journal` and `k.db.lock`.
2. The next run, with `timeout=0`: read and write both fail with `database is locked`.
3. After the lock directory is removed, the next read rolls the hot journal back: the rows are
   as they were before the transaction, and only `k.db` remains.

- With Python's default `timeout=5.0`, step 2 waits about five seconds of real time before
  failing (INFERRED: SQLite's busy handler sleeps through `nanosleep`; not run). The sleep
  costs no fuel.
- `unix-none` would leave no stale lock, but it has no locking at all, so two guests on one
  root could corrupt a database (READ: `sqlite3.c:43041-43042`). `unix-dotfile`, the default,
  is the safe one; recovery from a dead guest is the embedder's to do.
- **Temporary files.** Forcing a spill (`temp_store=file`, `cache_size=2`, a sort of 3,000
  1 KB blobs) works, with and without `SQLITE_TMPDIR=/tmpdir`. Nothing is left in the root
  afterwards. Where the file went cannot be seen from the guest: SQLite unlinks a temporary
  file right after opening it (READ: `sqlite3.c:47406`; the directory is the first writable of
  `SQLITE_TMPDIR`, `TMPDIR`, `/var/tmp`, `/usr/tmp`, `/tmp`, `.`, `:46918`). An unlink of an
  open file on a Windows host was not run. If it fails there, SQLite's own
  `SQLITE_UNLINK_AFTER_CLOSE` option defers it to the close (READ: `:47399`).

### 7. Costs (EXECUTED)

**Bytes** (`outputs/build-before.txt`, `outputs/rebuild-twice.txt`, `outputs/mapsizes.txt`):

| artifact | baseline | with the three | growth |
|---|---|---|---|
| reactor `python.wasm` | 29,801,866 | 31,760,440 | +1,958,574 (+6.57%) |
| snapshot | 63,484,356 | 65,504,775 | +2,020,419 (+3.18%) |
| stdlib zip | 11,140,659 | 11,140,659 | none (`sqlite3`, `bz2.py`, `lzma.py` were already in it) |

From the link map, the reactor's new code and data: SQLite 1,577,855; liblzma 115,480;
CPython's `_sqlite3` 68,897; bzip2 63,192; `_lzma` 16,035; `_bz2` 7,315; total 1,848,774.
SQLite is 85% of it. A lean SQLite (only `MATH_FUNCTIONS` of the nine options) makes it
1,083,674, the reactor 31,239,873 (+1,438,007) and the snapshot 64,981,214
(`outputs/lean-sqlite.txt`). The native feature set costs about 520 KB.

**Fuel**, exact, through the judge's driver (`outputs/fuel-before.txt`, `fuel-after.txt`):

| program | baseline | with the three |
|---|---|---|
| snapshot `-c pass` | 124,178,786 | 124,594,750 (+0.33%) |
| plain `-c pass` | 246,819,329 | 247,057,632 (+0.10%) |
| plain `-c "import pandas"` | 4,995,344,218 | 4,993,227,984 (−0.04%) |
| snapshot `-c "import bz2"` / `"import lzma"` | `ModuleNotFoundError` | 124,617,032 / 124,617,690 |
| snapshot `-c "import sqlite3"` | `ModuleNotFoundError` | 131,289,118 |

- bz2 and lzma cost nothing to import on the snapshot. They are already in it: `shutil` tries
  to import both when it loads (READ: `Lib/shutil.py:21-32`), pandas imports `shutil`, and now
  the attempt succeeds (EXECUTED: both are in `sys.modules` on a fresh snapshot run).
- sqlite3 is not pre-imported. Its first import costs 6.7M instructions on the snapshot.
- The judge's fuel metrics move the same way: +0.32% to +0.58% on snapshot checks, +0.03% to
  +0.11% on plain ones, and falls of 0.02% to 0.9% on six heavier plain checks (the three
  jobs, the gzip round trip, two imports of pandas) (`outputs/judge-metrics.txt`). One runner
  check, `test_a_cpp_exception_reaches_python`, fell 9.6%. It measures through
  `wasi_python.run`, whose fuel depends on how the module was compiled
  (`2026-10-17-fuel-depends-on-how-the-module-was-made.md`); it is not read as a cost here.
- Why `-c pass` grows by about 416k instructions on the snapshot is not traced. The snapshot
  holds more modules now (`bz2`, `lzma`, their helpers and their builtins' state), and
  start-up and shutdown walk more objects (INFERRED).

**Time** (benchmark facts): step 35 takes 35.1 s; the relink, zip, snapshot and artifacts
(steps 60 to 90) took 15.6 s. A full build from an empty `build/` with step 35 took 5 min 6 s
(finding 9).

### 8. It stays reproducible and sealed (EXECUTED)

- **Same bytes.** Steps 60 to 90 twice, then steps 35 to 90 once more: the reactor
  `e2d45152c4124177…`, the snapshot `038413bc39871fe9…` and the zip `e95b35dea78981e8…` all
  three times (`outputs/rebuild-twice.txt`). No build path is embedded (`strings` finds none).
- **The baseline built in the scratch clone equals this repository's own build** byte for
  byte: reactor `856e08eb…`, snapshot `7d983611…`, zip `e95b35de…`.
- **Imports unchanged.** Both binaries import 43 functions before and after: 42 WASI preview1
  calls and `host::call`, in two namespaces; no function added or removed; the judge's wall
  check reports nothing (`outputs/imports.txt`). SQLite's libc needs (`open`, `read`, `write`,
  `lseek`, `fsync`, `ftruncate`, `mkdir`, `rmdir`, `unlink`, `utimes`, `readlink`,
  `nanosleep`, …; `llvm-nm -u` of `sqlite3.o`) map onto calls CPython already imports: the
  import list did not change.
- **The judge.** On the new set, after two fixes below: 94/98, 248 passed, no failure. The four
  not passing are the ones already blocked or gapped (`outputs/judge-after.txt`). v1.3 (the data
  stack against native) stays 12/12. On the baseline set the one failure was
  `test_manifest_recipes_match_the_tree`: its `MANIFEST` was written before step 35 was
  committed in the clone (`outputs/judge-before.txt`). The ratchet compares with this
  repository's accepted state, which is still the 3.14 line, so its "grew" lines are not used
  here; `outputs/judge-metrics.txt` compares the two runs directly.

The judge found two things on the first run, both the recipe's to fix, not the judge's:

- **The word "vfs".** `context/embedders.txt` names `vfs`, and the rule
  (`test_no_embedder_name_in_code`) matches it as a case-insensitive substring in `recipes/`,
  `scripts/`, `src/`, `tests/` and `fixtures/` (READ: `tests/checks/test_rules.py`,
  `tests/harness/scan.py`). The step's comment said "unix-dotfile VFS". VFS is also
  SQLite's own term: `SQLITE_DEFAULT_UNIX_VFS` and the URI parameter `?vfs=` cannot be written
  in a recipe or a check without tripping it.
- **The package line.** `MANIFEST`'s `package sqlite 3.54.1` does not match the pin
  `sqlite-autoconf-3540100.tar.gz` (`test_manifest_pins_match_the_pin_list`): SQLite numbers
  its files `3540100`. `package sqlite-autoconf 3540100` matches.

### 9. The experiment reproduces from its own scripts (EXECUTED)

`setup.sh` was run into a second, empty scratch directory, then `scripts/build.sh` with every
step, from an empty `build/` (`outputs/build-from-scratch.txt`). Every step passed. The
reactor, the snapshot and the zip are the same bytes as in finding 8, built in a different
directory. The whole build took 5 min 6 s; the baseline's steps 10 to 90 took 4 min 46 s
(benchmark facts, `outputs/build-before.txt`).

## What it decides

All three can be built in on the 3.15 line from pinned sources with zero patches. The recipe
cost is one step script, three `Setup.local` lines, three pins (`SHA256SUMS` and
`00_download.sh`), the step's name in `build.sh`, and three package lines and licence notices in
`assemble_artifacts.py` (`edit.py` is the whole diff). No rename header, no stand-in module, no
compiler wrapper, no new import.

| module | verdict | cost (reactor) |
|---|---|---|
| `bz2` | works; output equals native | +70.5 KB |
| `lzma` | works; output equals native | +131.5 KB |
| `sqlite3` | works, partly: one writer and no readers beside it; no WAL in normal mode; a dead guest leaves a lock | +1.65 MB (+1.15 MB lean) |

A specification that adds them has to decide:

1. **The licences.** bzip2's BSD-style licence, xz's 0BSD and SQLite's public-domain
   dedication need the owner's approval (constitution §4.12). The notices go in `LICENSES/`;
   SQLite has no licence file, so its notice is the header blessing.
2. **The route.** `Setup.local` (no reorder; the `=` trap; one define by hand) or CPython's
   `configure` (CPython decides `PY_SQLITE_HAVE_SERIALIZE`; step 35 before step 20). Either
   needs a check that each of `_bz2`, `_lzma`, `_sqlite3` is in `sys.builtin_module_names`.
3. **SQLite's options.** The native feature set (+520 KB over lean) or a smaller one; whether
   to state `SQLITE_TEMP_STORE` (temporary data in memory instead of files).
4. **Locking.** Keep SQLite's WASI default, `unix-dotfile`, and document: the lock directory
   beside the database, no reader beside a writer, `journal_mode=wal` silently refused unless
   `locking_mode=exclusive`, and that a guest killed or out of fuel inside a write leaves
   `<db>.lock` for the embedder to remove.
5. **The word "vfs".** Either SQLite's VFS is never named in code, or the embedder-name rule
   gets a reasoned exception. That is a judge change, made on its own with `--accept-judge`.
6. **The pin's package name.** `sqlite-autoconf 3540100`, or the judge learns SQLite's version
   encoding.
7. **The `-V` sentence** names sqlite3, bz2 and lzma as missing; it changes, and so do the
   README's platform facts and the CHANGELOG.
8. **Whether the snapshot pre-imports `sqlite3`** (6.7M instructions on first import today), and
   whether `_zstd` (libzstd, for `compression.zstd`) joins the list. Both are out of this
   memo's scope.

## Where it stopped

- The `configure` route was run to the end of `configure` only, not built and run in the guest.
- The Windows host was not run: whether SQLite's unlink of an open temporary file and its
  `mkdir` lock behave there as on macOS is INFERRED from WASI's semantics, not seen.
- Two guests running at once on one root were not run; the lock is a directory, so it is
  shared through the root (INFERRED).
- **SQLite's randomness is weak in the guest** (added when spec 007 was built; found by the
  specification's review, `../reviews/007-sqlite3-bz2-and-lzma-spec-2026-10-17.md`, finding 4,
  EXECUTED there). `unixRandomness` in `sqlite3.c` reads `/dev/urandom`; a WASI root has none,
  so it falls back to `time()` in whole seconds and `getpid()`, which is the constant 1 on WASI.
  Five calls without `root`, back to back, printed two distinct `randomblob(16)` values; a
  planted zero-byte `/dev/urandom` in a reused root made two calls print the same value. Python's
  `random`, `secrets`, `os.urandom` and `tempfile` names are unaffected (real entropy through
  WASI's `random_get`). The fix belongs upstream (constitution §4.1): SQLite could use
  `getentropy()`, which wasi-libc provides, when `SQLITE_WASI` is set. A recipe-level fix would
  replace SQLite's randomness hook through its OS-layer API, whose name the embedder-name rule
  refuses in code; it was weighed and declined. The README states the limit.

## One line

bz2, lzma and sqlite3 build in on the 3.15 line from three pinned tarballs with one step script
and no patch, add 1.96 MB and 0.33% start-up fuel, keep the imports and the bytes reproducible,
and match native, except that SQLite on WASI locks with a directory: one writer, no reader
beside it, no WAL, and a dead guest leaves the lock behind.
