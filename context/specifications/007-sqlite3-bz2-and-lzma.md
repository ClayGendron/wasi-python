# 007 — sqlite3, bz2 and lzma, built in

- **Status:** built and reviewed, 2026-10-17 (`../reviews/007-sqlite3-bz2-and-lzma-2026-10-17.md`), for 0.1.0a3. Drafted and revised the same day to answer its review (`../reviews/007-sqlite3-bz2-and-lzma-spec-2026-10-17.md`). The owner approved the three licences on 2026-10-17 (constitution §4.12). It was written before specs 008 to 014 landed; the landing notes record how the build adapts it to spec 012's host-neutral recipe.
- **Owner:** Clay Gendron
- **Kind:** build recipe (`downloads/SHA256SUMS`, `scripts/00_download.sh`, a new `scripts/steps/35_stdlib_libs.sh`, `scripts/build.sh`, `scripts/steps/60_link.sh`, `scripts/assemble_artifacts.py`), the `-V` sentence (`recipes/reactor_bootstrap.py`), judge additions in `tests/` (checks, golden jobs, `tests/harness/paths.py`, `needs.py`, `pins.py`, `jobs.py`, `scoreboard.py`, `tests/unit/test_artifact_rules.py`), `.github/workflows/release.yml` (the zero-patch count), `README.md`, `CHANGELOG.md`.
- **Depends on:** 005 (the line), 006 (safe by default; this builds on its reactor).
- **Research it stands on:** `../research/2026-10-17-sqlite-bz2-and-lzma.md` and its evidence folder (the experiment: built, run against native, reproduced).
- **The owner's order** (2026-10-16): matplotlib, then sqlite, bz2 and lzma, then scipy. matplotlib waits on the owner's filesystem decision (questions 1 and 2); this one needs no C++ and no data folder, so it goes first (question 4).

## Decisions

1. **The pins** (EXECUTED by the experiment: downloaded, hashed, each cross-checked against a published value):
   - `sqlite-autoconf-3540100.tar.gz`, `https://sqlite.org/2026/sqlite-autoconf-3540100.tar.gz`, `926ef8d3eab93fbf6e06011901273eec076b25594a4e1cdadd50c987f4f6d64e` (its SHA3-256 matches sqlite.org's download page);
   - `bzip2-1.0.8.tar.gz`, `https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz`, `ab5a03176ee106d3f0fa90e381da478ddae405918153cca248e682cd0c4a2269` (good GPG signature);
   - `xz-5.8.4.tar.gz`, `https://github.com/tukaani-project/xz/releases/download/v5.8.4/xz-5.8.4.tar.gz`, `0014c7886930454fe8bd4228665b51af55eeae560ea135c9c4cd33f55b2591d9` (GitHub's asset digest; good GPG signature).
2. **One new step, `35_stdlib_libs.sh`**, as the experiment's, which builds three static archives under `build/stdlib-libs/` outside their source trees: bzip2's seven library files with its Makefile's flags; liblzma with xz's own `configure` in a separate directory (library only, no threads, no tools, no NLS); SQLite's amalgamation with one compile. Its options are fixed in the script, and every tool it runs (clang, llvm-ar, xz's `configure` and `make`) runs under `env -i` with only `PATH` and `LC_ALL` (autoconf reads `*_cv_*` cache variables and clang reads `CCC_OVERRIDE_OPTIONS` and `CPATH`), so no environment variable can change the artifact (the experiment's `SQLITE_EXTRA` hook is gone; the build review's finding 4 and its confirmation, N1). Step 60 stops with one line naming the missing archive when `build/stdlib-libs/` is incomplete. The three source trees stay byte-identical to their tarballs; v1.5's zero-patch check covers them (`test_source_tree_matches_its_tarball` gains `bzip2`, `xz` and `sqlite`).
3. **The route is `Setup.local`**, the one step 60 already writes: three lines, `_bz2`, `_lzma` and `_sqlite3` from CPython's own `Modules/` sources. `_sqlite3`'s line passes `-DPY_SQLITE_HAVE_SERIALIZE`, what CPython's `configure` defines when it finds `sqlite3_serialize`; it carries no `=`, because `makesetup` reads any line with `=` as a Make variable and drops the module silently (the experiment, EXECUTED). The `configure` route was not built, and it would move step 35 before step 20.
4. **SQLite's options** are the native host Python's feature set (FTS3/4/5, R-tree, Geopoly, math functions, dbstat, percentile; the review compared `PRAGMA compile_options`, EXECUTED), so results compare with the oracle; plus what WASI needs: `SQLITE_THREADSAFE=0`, `SQLITE_OMIT_LOAD_EXTENSION`, `SQLITE_MAX_MMAP_SIZE=0`. SQLite's own source already chooses its WASI locking (`unix-dotfile`) when it sees `__wasi__`; the recipe does not name it. `SQLITE_TEMP_STORE` keeps SQLite's default (temporary data in files, which go to `TMPDIR`, `/tmp` under spec 006's defaults).
5. **The word rule holds.** SQLite calls its OS layer a "VFS", and the constitution's embedder-name rule (§4.5) refuses that word in code. No recipe, check or script names it: the recipe relies on SQLite's own WASI default, and the checks test the behaviour (a lock directory appears), not the setting.
6. **`MANIFEST` and the licences.** Package lines `bzip2 1.0.8`, `xz 5.8.4` and `sqlite-autoconf 3540100` (SQLite 3.54.1, named as its pin names it, so the judge's pin rule needs no new encoding). `LICENSES/` gains `bzip2.txt` (its `LICENSE`), `xz.txt` (`COPYING` and `COPYING.0BSD`) and `sqlite.txt` (the public-domain blessing at the head of `sqlite3.h`). `tests/harness/paths.py`'s `LICENCE_COMPONENTS` gains `bzip2`, `xz` and `sqlite` (the notice's file name) and `PACKAGES` gains `bzip2`, `xz` and `sqlite-autoconf` (the `MANIFEST` name).
7. **The `-V` sentence** drops sqlite3, bz2 and lzma from its missing list and names zstd, which the WASI build also lacks (§4.11): "no ctypes, mmap, sockets, ssl or zstd". The README's platform facts and the CHANGELOG say what changed and what SQLite cannot do here.
8. **SQLite's limits are stated, not patched.** The README says:
   - one connection holds the database while it reads or writes, through a `<db>.lock` directory beside it, so a second connection (even in the same program) gets "database is locked" during another's write or unfinished read, after its busy timeout (5 s by default) (the review, EXECUTED);
   - `journal_mode=wal` silently stays `delete` unless `locking_mode=exclusive`;
   - a guest killed, out of fuel or past its deadline inside a transaction leaves `<db>.lock` and a hot journal, which the embedder removes (SQLite then rolls the journal back); a call without `root` (spec 006) never sees a stale lock, since its root is fresh;
   - SQLite's own randomness (`randomblob()`, `random()`, temporary names) is seeded from the time in seconds and the process id, which is always 1 on WASI, because the guest has no `/dev/urandom`: two calls in the same second can repeat it, and a `/dev/urandom` planted in a reused root fixes it (the review, EXECUTED). Python's `random`, `secrets`, `os.urandom` and `tempfile`'s names are unaffected (real entropy through WASI; the review ran them on both binaries, EXECUTED). The upstream fix (SQLite using `getentropy` on WASI) is recorded in the review (`../reviews/007-sqlite3-bz2-and-lzma-spec-2026-10-17.md`, finding 4) and goes into the research memo's "Where it stopped" at landing; the README's Safety list gains this row;
   - `sqlite3.threadsafety` is 0 (native: 3); `sysconfig` reports `_sqlite3`, `_bz2` and `_lzma` as missing or disabled and `PY_SQLITE_HAVE_SERIALIZE` as 0, because they were added through `Setup.local`, not `configure` (it says "disabled" for `_sqlite3`); `shelve` and `dbm` now create `dbm.sqlite3` files, as native does.
9. **Not pre-imported.** `import sqlite3` costs 6.7M instructions on first use (EXECUTED); the snapshot does not pre-import it, so a program that does not use it pays nothing. `bz2` and `lzma` are already in the snapshot (pandas' imports of `shutil` load them), so importing them costs nothing more.
10. **The judge** (accepted with `--accept-judge`):
    - a v1.1 check, `test_stdlib_c_modules_are_builtin`: `zlib`, `_bz2`, `_lzma` and `_sqlite3` are in `sys.builtin_module_names` on both binaries (it catches the silent `makesetup` drop);
    - a golden job `compress` (v1.3): bz2 at two levels, `.xz` and `.lzma`, a raw filter chain, `tarfile` `w:bz2`/`w:xz` with fixed metadata, round-tripped, with the outputs' lengths and SHA-256 printed; native 3.15 under the oracle writes the golden;
    - a golden job `sqlite` (v1.3): a file database in the job's data directory, never in its output directory (`jobs.render` compares every file there, and a database's header records the SQLite version that last wrote it, bytes 96 to 99: EXECUTED by the review): create, `executemany`, a transaction and a rollback, JSON and window functions, FTS5 matches, a temporary table forced to a temporary file with `PRAGMA temp_store=file` and `PRAGMA cache_size=2` (so the Windows verify job exercises SQLite's unlink of an open file; a table merely "large" may stay in the page cache), then `DataFrame.to_sql` and `pandas.read_sql`. The oracle's SQLite is 3.53.1, and its math library is the host's, so the job prints only what both agree on: no version or error text, every query with a total `ORDER BY`, floats rounded to 9 places by the jobs' own helper after they leave SQLite, no FTS5 `bm25()` scores, no JSON float text, no trigonometric or `log10` results (the review found these differ, EXECUTED; the math functions follow the C library, not the SQLite release);
    - `compress` and `sqlite` join `tests/harness/jobs.py`'s `JOBS`;
    - a v1.3 check, `test_sqlite_holds_a_lock_while_it_writes`: inside a write transaction a second connection opened with `timeout=0` gets `sqlite3.OperationalError` ("database is locked") at once (the default timeout waits about 5 s of real time) and `<db>.lock` exists; the same while a first connection holds an unfinished `SELECT`; after commit and close, both work and the lock is gone;
    - the other judge files that change: `.github/workflows/release.yml`'s zero-patch step expects `^7 passed` (four trees become seven); `tests/harness/needs.py`'s `SOURCE_COMPONENTS` and `tests/harness/pins.py`'s `SOURCE_PATTERNS` gain `bzip2`, `xz` and `sqlite`; the synthetic set in `tests/unit/test_artifact_rules.py` gains the three packages and pins. SQLite has no licence file, so its notice must hold the blessing that heads the pinned `sqlite3.h`, and xz's must also hold its `COPYING.0BSD` (the build review's finding 7; `tests/harness/paths.py`).

## Intent

The three stdlib modules AI-written programs reach for after numpy and pandas (a local database, `.bz2` and `.xz` files) work, from pinned sources with zero patches, and match native where native behaviour is possible on WASI.

## Design

```
scripts/steps/35_stdlib_libs.sh   bzip2, liblzma, SQLite as static archives (new)
scripts/build.sh                  35_stdlib_libs between 30 and 40
scripts/steps/60_link.sh          three Setup.local lines
scripts/assemble_artifacts.py     three packages, three licence notices
recipes/reactor_bootstrap.py      the -V sentence
tests/checks/…                    the builtin-modules check, the lock check
tests/jobs/compress.py, sqlite.py and their .expected
tests/harness/paths.py, pins.py, needs.py, jobs.py, scoreboard.py   the three components
tests/unit/test_artifact_rules.py   the synthetic set
.github/workflows/release.yml     ^7 passed
README.md, CHANGELOG.md
```

## Scope

In: the above. Out: `_zstd` (libzstd, for `compression.zstd`; its own research and licence); SQLite's `load_extension`; a SQLite locking other than SQLite's WASI default.

## Acceptance criteria

1. The owner has approved the three licences (question 9) before anything is built.
2. From an empty `build/`, `scripts/build.sh` passes; steps 35 to 90 run twice give the same reactor, snapshot and zip.
3. `uv run pytest` is green; the new jobs match native byte for byte; the run that records the state uses `--accept-judge` and `--accept-growth`, and every grown metric has its cause in the landing notes (the experiment measured the reactor +6.6%, the snapshot +3.2%, snapshot `-c pass` +0.33%).
4. The zero-patch check covers the three new trees and passes.
5. A dry run of the release workflow passes every job.

## Landing notes

Built 2026-10-17 by the implementer (Claude Opus 5.5) in a scratch clone of `3ee5bbe`, not in the main tree, after the owner approved the three licences (criterion 1; constitution §4.12, `../questions-for-the-owner.md`, question 9), then rebased onto `11085c7` (Release 0.1.0a2), so it ships in 0.1.0a3. Reviewed by a fresh agent (`../reviews/007-sqlite3-bz2-and-lzma-2026-10-17.md`: 9 findings, then a confirmation with 3 more); every finding is fixed or answered there. Every claim below was run (EXECUTED) unless it says otherwise.

### After the build review

- The README and CHANGELOG qualify "native's results": SQLite's math functions follow the guest's C library (finding 1 and its confirmation), and a database in a read-only grant opens only through a URI that takes no lock (finding 2 and its confirmation). The sizes row and the build-time row are re-measured: a full build from pins took 5 min 41 s (finding 3).
- Step 35 runs every tool (clang, llvm-ar, xz's `configure` and `make`) under `env -i` with only `PATH` and `LC_ALL`. With `CPPFLAGS=-fno-inline`, `tuklib_cv_physmem_method=none` and `CCC_OVERRIDE_OPTIONS=+-fno-inline` exported, step 35 gave byte-identical archives (finding 4, N1). The same `CPPFLAGS` changes the reactor through step 60's CPython `make`, an exposure that predates this spec (see "Left over").
- Step 60 stops if `Modules/config.c` lacks any of the three modules (finding 9).
- xz's notice must hold `COPYING.0BSD`, and SQLite's the blessing in `sqlite3.h`, both read from the pinned tarballs; a unit test with synthetic tarballs covers it (finding 7, N2).
- Each rebuild after these fixes gave the same reactor, snapshot and zip as the first build (`4befe9de…`, `a7a0a4a8…`, `2a8085a2…`). `MANIFEST` and `SHA256SUMS` changed, because the recipe hashes changed; their final hashes are in the table below.

### Adapting the specification to the recipe after spec 012

This specification was written against the recipe of spec 006. Specs 008 to 014 landed before it was built; spec 012 changed the recipe most (per-host names in `scripts/line.conf`, a host `case` in `00_download.sh`, one host-neutral wasm runtime, `LC_ALL=C`, host facts rewritten in the zip). Each adaptation, for the build review. **None changes a decision**; A6 changes the expected numbers of criterion 3.

- **A1. The pins are host-neutral.** The three `get` lines sit in `00_download.sh`'s "Sources" block beside zlib's, outside the host `case`, because every build host fetches the same source tarballs. Their `SHA256SUMS` lines follow zlib's. `MANIFEST` has 39 `pin` lines (36 before).
- **A2. Step 35 is host-neutral by construction.** It has no host branch. It compiles with `$SDK/bin/clang`, whose sysroot and builtins step 10 has already replaced with the host-neutral ones (spec 012, Decision 2), and it runs under `build.sh`'s `LC_ALL=C`. It reads all three tarballs through `pinned` before it removes anything. xz's `configure` runs the build host's shell tools (`sh`, `sed`, `grep`, `awk`), a new unpinned host input; the README says so beside the other unpinned tools. The Linux build below shows they leave the bytes alone.
- **A3. The zip needs no new rewrite.** The `Setup.local` lines name `build/stdlib-libs/` absolute paths. The zip came out byte-identical to the baseline's (`2a8085a2…`), so step 70's host-fact rewrite (spec 012, Decision 5) needed no change, and `test_stdlib_zip_names_no_build_host` and `test_artifacts_carry_no_build_path` pass.
- **A4. The zero-patch check reads `needs.SOURCE_COMPONENTS`.** Its parametrization was a literal list of four; it now uses the needs vocabulary's tuple, so the list of trees is written once. The test IDs are unchanged (`[cpython]` … `[sqlite]`). The workflow's grep wants `^7 passed`, and the step's command gives `7 passed, 11 deselected` (EXECUTED).
- **A5. Where the checks run.** `test_stdlib_c_modules_are_builtin` runs on both binaries (v1.1). The two golden jobs are `slow`, like the other three, and run on the plain reactor through `_run_job`. `test_sqlite_holds_a_lock_while_it_writes` runs on the snapshot only (v1.3), with `timeout=0` throughout.
- **A6. Fuel moved less than the experiment measured.** Spec 008 made fuel count the guest only (from the end of instantiation). The experiment's +0.33% for snapshot `-c pass` included instantiation; under today's judge a snapshot call grows by about +0.04% (the table below).
- **A7. Spec 006's Safety list** is the README's *Safety* section: its "Not protected" paragraph gains SQLite's randomness and the stale lock. The SQLite facts of Decision 8 are a new README subsection, *sqlite3 in the guest*.
- **A8. x86_64 Linux** stays as spec 012 left it: pinned, built in no CI job, and not built here.

### Seen failing first

The new checks ran against the baseline set (the main tree's `build/artifacts/`, reactor `2df569f2…`, snapshot `4130d3ba…`, zip `2a8085a2…`, copied out read-only), with the goldens already written by the oracle and before any recipe change: `7 failed, 23 passed, 7 skipped`.

- `test_stdlib_c_modules_are_builtin[plain]` and `[snapshot]`: `['_bz2', '_lzma', '_sqlite3']`.
- `test_manifest_is_well_formed`: no package line for `bzip2`, `xz`, `sqlite-autoconf`.
- `test_licence_notices_cover_every_component`: `bzip2.txt`, `xz.txt`, `sqlite.txt` missing.
- `test_compress_job_matches_native`, `test_sqlite_job_matches_native` and `test_sqlite_holds_a_lock_while_it_writes`: `ModuleNotFoundError` for `_bz2` or `_sqlite3`.
- The three new zero-patch cases were blocked (no source trees), as they should be.

### The goldens

`tests/jobs/regen.py` wrote `compress.expected` (834 bytes) and `sqlite.expected` (1,103 bytes) under the pinned oracle (python-build-standalone 3.15.0, whose SQLite is 3.53.1); the three existing goldens came out unchanged. `regen.py --check` then reproduced all five, each with two hash seeds. Neither job leaves a file in its output directory; the database is `<data>/jobs.db`.

### The new set (criterion 2)

macOS arm64, in the clone, from an empty `build/` (the main tree's pinned downloads copied in; the three new tarballs fetched by `00_download.sh`; every file hash-checked): `sh scripts/build.sh`, all eleven steps, 321 s (a benchmark fact). Step 35 made `libbz2.a` 80,798 bytes, `liblzma.a` 213,672 and `libsqlite3.a` 2,048,884, the experiment's sizes.

| file | bytes | SHA-256 | before |
|---|---|---|---|
| `python.wasm` | 31,760,992 | `4befe9de64edc783996ab006e6179b704a73a520b67431135df103db9db9625d` | 29,802,418 `2df569f2…` |
| `python-snapshot.wasm` | 65,506,914 | `a7a0a4a8da0f3c50fc630ac39ba74dc9da440eef594343d279af91a8880c9c36` | 63,489,079 `4130d3ba…` |
| `python-stdlib.zip` | 11,140,578 | `2a8085a23f661f81eb6f522708e1957b849588681a69e3992f7707731754e7c5` | unchanged |
| `MANIFEST` | 8,320 | `f1a150672096532a4e4af7b09aa49d6c4441f687a6ccac2ce0afa968baacd414` | 7,874 `980beb0a…` |
| `LICENSES/bzip2.txt` | 1,921 | `28753c7121ccf73cc69a44ee55ba52d891d3bf1718940d2e3cffa661d225a455` | new |
| `LICENSES/xz.txt` | 3,775 | `93947eef5170a4e17a3dfed772f23f4fa366beff24358f41764cf60698a053e3` | new |
| `LICENSES/sqlite.txt` | 1,533 | `681f05f7e60baee5e748a22c0e3dfa1fce3fcf16c69078998928bfb3978c70f9` | new |
| `SHA256SUMS` | 1,365 | `69eb0fb50d70a0a8433e82ece65254f9a1b643617e360391d5d5cc55c9c0b8d1` | `5353ad94…` |

- The reactor grew by 1,958,574 bytes (+6.57%), exactly the experiment's growth; the snapshot by 2,017,835 (+3.18%). The nine older licence files are unchanged.
- **Steps 35 to 90 again** (`sh scripts/build.sh 35 40 50 60 70 80 90`, 136 s): the same `SHA256SUMS`, byte for byte (`cmp`).
- **Step 60's stop:** with `liblzma.a` moved away, `sh scripts/steps/60_link.sh` printed `ERROR: build/stdlib-libs/lib/liblzma.a is missing: run step 35` and exited 1 before touching anything.
- **Linux aarch64:** the image of `../research/2026-10-17-the-linux-build-experiment/Dockerfile` (`debian:trixie-slim@sha256:a29215f6…`, uv 0.9.22 checked against its digest; gcc 14.2.0, GNU Make 4.4.1, no locale set), on a copy of the clone's working tree. `00_download.sh` fetched only Linux aarch64's own five inputs. All eleven steps passed in 288 s. Its `build/artifacts/SHA256SUMS` is **byte-identical to macOS's** (`cmp`; both `b7473480…`, the first build's, before the review's recipe edits), and so is its `MANIFEST`. The container, its volume and its image were removed afterwards.
- **The README's SQLite facts, on this set** (through `wasi_python.run`, both binaries): `threadsafety` 0; `sysconfig` gives `_bz2` and `_lzma` `missing`, `_sqlite3` `disabled` and `PY_SQLITE_HAVE_SERIALIZE` 0; `journal_mode=wal` answers `delete`, and `wal` after `locking_mode=exclusive`; `serialize()` works and `enable_load_extension` is absent; a new `shelve` is `dbm.sqlite3`. On a fresh snapshot `bz2` and `lzma` are in `sys.modules` and `sqlite3` is not (the build review ran this check before any import; the author's `probes/claims.py` imported first and could not show it).

### The judge (criterion 3)

`uv run pytest` in the clone, rebased onto `11085c7`, with the oracle and the reference build present and no `--accept`:

```
wasi_python v1: 151/154 pass · 0 gap · 3 blocked · 0 fail   (unit suite 303/303)
  v1.1  artifact set        24/25  blocked 1
  v1.2  portable, sealed    30/31  blocked 1
  v1.3  data stack          15/15
  v1.4  embedding           48/48
  v1.5  rebuild from pins   18/18
  rules constitution rules  16/17  blocked 1
blocked by: prior-art clones 1 · three systems 1 · wheel 1
ratchet vs f1db97f37c: lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 8 · grew 32 ·
  judge changed: tests/checks/test_v1_1_artifact_set.py, tests/checks/test_v1_3_data_stack.py,
  tests/checks/test_v1_5_rebuild_from_pins.py and 10 more
RED: 32 metric(s) grew
454 passed, 3 skipped
```

- The new jobs match native byte for byte. Nothing fails. The run is red only for growth, which the accept states. Gained 8: the two builtin-module checks, the two jobs, the lock check and three zero-patch trees. `unrun locally 1` is the prior-art clones, which a clone lacks.
- The judge changed in 13 files: the three check files, `tests/harness/jobs.py`, `needs.py`, `paths.py`, `pins.py`, `scoreboard.py`, `tests/unit/test_artifact_rules.py`, and the two jobs with their goldens. The accept needs `--accept-judge`.
- The 32 growths, against `context/progress/accepted.json`:

| check | metric | accepted | now |
|---|---|---|---|
| `test_binary_is_a_core_wasm_module[plain]` | bytes | 29,802,418 | 31,760,992 (+6.572%) |
| `test_binary_is_a_core_wasm_module[snapshot]` | bytes | 63,489,079 | 65,506,914 (+3.178%) |
| `test_extra_preopens_work_on_the_snapshot[root first]` | fuel | 836,162,951 | 846,852,242 (+1.278%) |
| `test_extra_preopens_work_on_the_snapshot[data first]` | fuel | 836,163,085 | 846,852,376 (+1.278%) |
| `test_stdlib_debugging_tools_import` | fuel | 534,905,050 | 535,471,457 (+0.106%) |
| `test_unbuffered_output_survives_a_hard_exit[snapshot]` | fuel | 2,886,877 | 2,889,264 (+0.083%) |
| `test_default_integer_width_is_documented` | fuel | 1,126,976,186 | 1,127,900,958 (+0.082%) |
| `test_longdouble_parses` | fuel | 1,127,575,580 | 1,128,244,374 (+0.059%) |
| `test_run_reads_argv_and_environment_each_call[snapshot]` | fuel | 82,283,408 | 82,329,594 (+0.056%) |
| `test_guest_has_no_network` | fuel | 329,648,779 | 329,829,453 (+0.055%) |
| `test_no_cpython_test_module_is_built_in` | fuel | 82,620,024 | 82,660,854 (+0.049%) |
| `test_a_program_sees_real_entropy_and_file_metadata[snapshot]` | fuel | 82,775,098 | 82,813,833 (+0.047%) |
| `test_door_without_a_host_says_so[snapshot]` | fuel | 82,782,357 | 82,820,142 (+0.046%) |
| `test_numpy_and_pandas_are_builtin_at_manifest_versions[snapshot]` | fuel | 82,285,108 | 82,321,939 (+0.045%) |
| `test_snapshot_preimports_the_stack` | fuel | 81,926,472 | 81,961,874 (+0.043%) |
| `test_a_program_sees_real_entropy_and_file_metadata[plain]` | fuel | 242,227,843 | 242,331,642 (+0.043%) |
| `test_unbuffered_output_survives_a_hard_exit[plain]` | fuel | 216,726,618 | 216,818,725 (+0.042%) |
| `test_exit_status_is_a_process_status[snapshot]` | fuel | 81,996,007 | 82,030,352 (+0.042%) |
| `test_door_round_trips_bytes_through_a_host[plain]` | fuel | 241,829,925 | 241,930,985 (+0.042%) |
| `test_run_returns_the_exit_code[snapshot]` | fuel | 82,047,342 | 82,081,264 (+0.041%) |
| `test_guest_runs_here[snapshot]` | fuel | 81,994,395 | 82,028,117 (+0.041%) |
| `test_main_starts_as_native[plain]` | fuel | 241,548,312 | 241,647,628 (+0.041%) |
| `test_main_starts_as_native[snapshot]` | fuel | 82,101,223 | 82,134,890 (+0.041%) |
| `test_guest_sees_only_its_root` | fuel | 242,351,278 | 242,450,645 (+0.041%) |
| `test_guest_runs_here[plain]` | fuel | 241,439,129 | 241,536,204 (+0.040%) |
| `test_run_returns_the_exit_code[plain]` | fuel | 241,493,447 | 241,589,426 (+0.040%) |
| `test_exit_status_is_a_process_status[plain]` | fuel | 241,446,647 | 241,541,291 (+0.039%) |
| `test_door_without_a_host_says_so[plain]` | fuel | 242,283,890 | 242,376,993 (+0.038%) |
| `test_door_round_trips_bytes_through_a_host[snapshot]` | fuel | 82,374,344 | 82,400,746 (+0.032%) |
| `test_run_reads_argv_and_environment_each_call[plain]` | fuel | 241,778,963 | 241,856,069 (+0.032%) |
| `test_uncaught_errors_print_as_native[snapshot]` | fuel | 83,340,903 | 83,364,874 (+0.029%) |
| `test_uncaught_errors_print_as_native[plain]` | fuel | 670,579,668 | 670,715,834 (+0.020%) |

- Why it grew:
  - The bytes: the three libraries and their CPython modules are linked in. The experiment's link map put 85% of it in SQLite (memo, finding 7).
  - The snapshot's calls: the snapshot now holds `bz2`, `lzma` and their state, because `shutil`'s import of them (pandas imports `shutil`) now succeeds (EXECUTED: both are in `sys.modules` on a fresh snapshot). Start-up and finalization walk more objects (INFERRED), about +0.03% to +0.06% a call.
  - The two `test_extra_preopens_work_on_the_snapshot` cases walk `gc.get_objects()` (READ), so they pay for every extra object, +1.28%.
  - The plain reactor's small calls grow about +0.04%: the interpreter registers three more builtin modules and initializes a larger data segment (INFERRED).
- Six metrics shrank: the plain checks that import pandas fell 0.06% to 0.31%, and `test_gzip_round_trips` 0.95%. There, `shutil`'s attempts to import `bz2` and `lzma` no longer raise `ModuleNotFoundError` (INFERRED; the memo saw the same falls).
- The accept, after the build review, is `uv run pytest --accept "<reason>" --accept-judge "<the 13 judge files: spec 007's checks, jobs and goldens>" --accept-growth "<the causes above>"`.

### Left over

- **Criterion 5, the release workflow's dry run:** run 39035741327 on `5abc972` passed every job: build and judge, the arm64 Linux rebuild, the same-bytes gate, and verify on Ubuntu, macOS and Windows (where the `sqlite` job first ran SQLite's unlink of an open temporary file). The zero-patch step's `^7 passed` was also run locally (A4).
- **Step 60 reads the environment** through CPython's own `configure` and `make` (`CPPFLAGS` changed the reactor, EXECUTED by the author while answering the review's confirmation). Steps 20 and 60 predate this spec; the same-bytes gate catches a difference. Sealing them like step 35 is a separate change.
- **Benchmarks** (time) were not re-measured beyond the build walls above and the README's build-time row (5 min 41 s, a full build from pins on this machine).
- The research memo's "Where it stopped" gains SQLite's randomness and its upstream route (Decision 8).
