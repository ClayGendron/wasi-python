# 007 — sqlite3, bz2 and lzma, built in

- **Status:** draft, 2026-10-17; revised the same day to answer its review
  (`../reviews/007-sqlite3-bz2-and-lzma-spec-2026-10-17.md`). It changes the build recipe and the
  artifact set, so it is reviewed again before it is built. It is **not built until the owner approves the three licences**
  (constitution §4.12; `../questions-for-the-owner.md`, question 9).
- **Owner:** Clay Gendron
- **Kind:** build recipe (`downloads/SHA256SUMS`, `scripts/00_download.sh`, a new
  `scripts/steps/35_stdlib_libs.sh`, `scripts/build.sh`, `scripts/steps/60_link.sh`,
  `scripts/assemble_artifacts.py`), the `-V` sentence (`recipes/reactor_bootstrap.py`), judge
  additions in `tests/` (checks, golden jobs, `tests/harness/paths.py`, `needs.py`, `pins.py`,
  `jobs.py`, `scoreboard.py`, `tests/unit/test_artifact_rules.py`),
  `.github/workflows/release.yml` (the zero-patch count), `README.md`,
  `CHANGELOG.md`.
- **Depends on:** 005 (the line), 006 (safe by default; this builds on its reactor).
- **Research it stands on:** `../research/2026-10-17-sqlite-bz2-and-lzma.md` and its evidence
  folder (the experiment: built, run against native, reproduced).
- **The owner's order** (2026-10-16): matplotlib, then sqlite, bz2 and lzma, then scipy.
  matplotlib waits on the owner's filesystem decision (questions 1 and 2); this one needs no
  C++ and no data folder, so it goes first (question 4).

## Decisions

1. **The pins** (EXECUTED by the experiment: downloaded, hashed, each cross-checked against a
   published value):
   - `sqlite-autoconf-3540100.tar.gz`, `https://sqlite.org/2026/sqlite-autoconf-3540100.tar.gz`,
     `926ef8d3eab93fbf6e06011901273eec076b25594a4e1cdadd50c987f4f6d64e` (its SHA3-256 matches
     sqlite.org's download page);
   - `bzip2-1.0.8.tar.gz`, `https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz`,
     `ab5a03176ee106d3f0fa90e381da478ddae405918153cca248e682cd0c4a2269` (good GPG signature);
   - `xz-5.8.4.tar.gz`,
     `https://github.com/tukaani-project/xz/releases/download/v5.8.4/xz-5.8.4.tar.gz`,
     `0014c7886930454fe8bd4228665b51af55eeae560ea135c9c4cd33f55b2591d9` (GitHub's asset digest;
     good GPG signature).
2. **One new step, `35_stdlib_libs.sh`**, as the experiment's, which builds three static
   archives under `build/stdlib-libs/` outside their source trees: bzip2's seven library files
   with its Makefile's flags; liblzma with xz's own `configure` in a separate directory (library
   only, no threads, no tools, no NLS); SQLite's amalgamation with one compile. Its options are
   fixed in the script: it reads no environment variable that could change the artifact (the
   experiment's `SQLITE_EXTRA` hook is gone). Step 60 stops with one line naming the missing
   archive when `build/stdlib-libs/` is incomplete. The three source
   trees stay byte-identical to their tarballs; v1.5's zero-patch check covers them
   (`test_source_tree_matches_its_tarball` gains `bzip2`, `xz` and `sqlite`).
3. **The route is `Setup.local`**, the one step 60 already writes: three lines, `_bz2`, `_lzma`
   and `_sqlite3` from CPython's own `Modules/` sources. `_sqlite3`'s line passes
   `-DPY_SQLITE_HAVE_SERIALIZE`, what CPython's `configure` defines when it finds
   `sqlite3_serialize`; it carries no `=`, because `makesetup` reads any line with `=` as a Make
   variable and drops the module silently (the experiment, EXECUTED). The `configure` route was
   not built, and it would move step 35 before step 20.
4. **SQLite's options** are the native host Python's feature set (FTS3/4/5, R-tree, Geopoly, math
   functions, dbstat, percentile; the review compared `PRAGMA compile_options`, EXECUTED), so
   results compare with the oracle; plus what WASI needs:
   `SQLITE_THREADSAFE=0`, `SQLITE_OMIT_LOAD_EXTENSION`, `SQLITE_MAX_MMAP_SIZE=0`. SQLite's own
   source already chooses its WASI locking (`unix-dotfile`) when it sees `__wasi__`; the recipe
   does not name it. `SQLITE_TEMP_STORE` keeps SQLite's default (temporary data in files, which
   go to `TMPDIR`, `/tmp` under spec 006's defaults).
5. **The word rule holds.** SQLite calls its OS layer a "VFS", and the constitution's
   embedder-name rule (§4.5) refuses that word in code. No recipe, check or script names it:
   the recipe relies on SQLite's own WASI default, and the checks test the behaviour (a lock
   directory appears), not the setting.
6. **`MANIFEST` and the licences.** Package lines `bzip2 1.0.8`, `xz 5.8.4` and
   `sqlite-autoconf 3540100` (SQLite 3.54.1, named as its pin names it, so the judge's pin rule
   needs no new encoding). `LICENSES/` gains `bzip2.txt` (its `LICENSE`), `xz.txt` (`COPYING` and
   `COPYING.0BSD`) and `sqlite.txt` (the public-domain blessing at the head of `sqlite3.h`).
   `tests/harness/paths.py`'s `LICENCE_COMPONENTS` gains `bzip2`, `xz` and `sqlite` (the notice's
   file name) and `PACKAGES` gains `bzip2`, `xz` and `sqlite-autoconf` (the `MANIFEST` name).
7. **The `-V` sentence** drops sqlite3, bz2 and lzma from its missing list and names zstd, which
   the WASI build also lacks (§4.11): "no ctypes, mmap, sockets, ssl or zstd". The README's platform facts and the CHANGELOG say what changed and what
   SQLite cannot do here.
8. **SQLite's limits are stated, not patched.** The README says:
   - one connection holds the database while it reads or writes, through a `<db>.lock`
     directory beside it, so a second connection (even in the same program) gets "database is
     locked" during another's write or unfinished read, after its busy timeout (5 s by default)
     (the review, EXECUTED);
   - `journal_mode=wal` silently stays `delete` unless `locking_mode=exclusive`;
   - a guest killed, out of fuel or past its deadline inside a transaction leaves `<db>.lock`
     and a hot journal, which the embedder removes (SQLite then rolls the journal back); a call
     without `root` (spec 006) never sees a stale lock, since its root is fresh;
   - SQLite's own randomness (`randomblob()`, `random()`, temporary names) is seeded from the
     time in seconds and the process id, which is always 1 on WASI, because the guest has no
     `/dev/urandom`: two calls in the same second can repeat it, and a `/dev/urandom` planted in
     a reused root fixes it (the review, EXECUTED). Python's `random`, `secrets`, `os.urandom`
     and `tempfile`'s names are unaffected (real entropy through WASI; the review ran them on
     both binaries, EXECUTED). The upstream fix (SQLite using `getentropy` on WASI) is recorded
     in the review (`../reviews/007-sqlite3-bz2-and-lzma-spec-2026-10-17.md`, finding 4) and goes
     into the research memo's "Where it stopped" at landing; the README's Safety list gains this
     row;
   - `sqlite3.threadsafety` is 0 (native: 3); `sysconfig` reports `_sqlite3`, `_bz2` and `_lzma`
     as missing or disabled and `PY_SQLITE_HAVE_SERIALIZE` as 0, because they were added through
     `Setup.local`, not `configure` (it says "disabled" for `_sqlite3`); `shelve` and `dbm` now create `dbm.sqlite3` files, as
     native does.
9. **Not pre-imported.** `import sqlite3` costs 6.7M instructions on first use (EXECUTED);
   the snapshot does not pre-import it, so a program that does not use it pays nothing. `bz2` and
   `lzma` are already in the snapshot (pandas' imports of `shutil` load them), so importing them
   costs nothing more.
10. **The judge** (accepted with `--accept-judge`):
    - a v1.1 check, `test_stdlib_c_modules_are_builtin`: `zlib`, `_bz2`, `_lzma` and `_sqlite3`
      are in `sys.builtin_module_names` on both binaries (it catches the silent `makesetup` drop);
    - a golden job `compress` (v1.3): bz2 at two levels, `.xz` and `.lzma`, a raw filter chain,
      `tarfile` `w:bz2`/`w:xz` with fixed metadata, round-tripped, with the outputs' lengths and
      SHA-256 printed; native 3.15 under the oracle writes the golden;
    - a golden job `sqlite` (v1.3): a file database in the job's data directory, never in its
      output directory (`jobs.render` compares every file there, and a database's header records
      the SQLite version that last wrote it, bytes 96 to 99: EXECUTED by the review): create,
      `executemany`, a transaction and a rollback, JSON and window functions, FTS5 matches, a
      temporary table forced to a temporary file with `PRAGMA temp_store=file` and
      `PRAGMA cache_size=2` (so the Windows verify job exercises SQLite's unlink of an open file;
      a table merely "large" may stay in the page cache), then `DataFrame.to_sql` and
      `pandas.read_sql`. The oracle's SQLite is 3.53.1, and its math library is the host's, so the
      job prints only what both agree on: no version or error text, every query with a total
      `ORDER BY`, floats rounded to 9 places by the jobs' own helper after they leave SQLite, no
      FTS5 `bm25()` scores, no JSON float text, no trigonometric or `log10` results (the review
      found these differ, EXECUTED; the math functions follow the C library, not the SQLite
      release);
    - `compress` and `sqlite` join `tests/harness/jobs.py`'s `JOBS`;
    - a v1.3 check, `test_sqlite_holds_a_lock_while_it_writes`: inside a write transaction a
      second connection opened with `timeout=0` gets `sqlite3.OperationalError` ("database is
      locked") at once (the default timeout waits about 5 s of real time) and `<db>.lock`
      exists; the same while a first connection holds an unfinished `SELECT`; after commit and
      close, both work and the lock is gone;
    - the other judge files that change: `.github/workflows/release.yml`'s zero-patch step
      expects `^7 passed` (four trees become seven); `tests/harness/needs.py`'s
      `SOURCE_COMPONENTS` and `tests/harness/pins.py`'s `SOURCE_PATTERNS` gain `bzip2`, `xz` and
      `sqlite`; the synthetic set in `tests/unit/test_artifact_rules.py` gains the three packages
      and pins. SQLite's licence notice is checked for presence only (it has no licence file to
      compare against); the scoreboard's "not machine-checked" line, which names presence-only
      notices for unpinned components, gains "SQLite's" (`tests/harness/scoreboard.py`).

## Intent

The three stdlib modules AI-written programs reach for after numpy and pandas (a local
database, `.bz2` and `.xz` files) work, from pinned sources with zero patches, and match native
where native behaviour is possible on WASI.

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

In: the above. Out: `_zstd` (libzstd, for `compression.zstd`; its own research and licence);
SQLite's `load_extension`; a SQLite locking other than SQLite's WASI default.

## Acceptance criteria

1. The owner has approved the three licences (question 9) before anything is built.
2. From an empty `build/`, `scripts/build.sh` passes; steps 35 to 90 run twice give the same
   reactor, snapshot and zip.
3. `uv run pytest` is green; the new jobs match native byte for byte; the run that records the
   state uses `--accept-judge` and `--accept-growth`, and every grown metric has its cause in the
   landing notes (the experiment measured the reactor +6.6%, the snapshot +3.2%,
   snapshot `-c pass` +0.33%).
4. The zero-patch check covers the three new trees and passes.
5. A dry run of the release workflow passes every job.

## Landing notes

(Filled in on landing.)
