# Review of 007 — sqlite3, bz2 and lzma, built in (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I was given `AGENTS.md`, the constitution, `context/README.md`, the reviews README, the 006 pre-build review (for its format), the specification under review, the memo it stands on and its evidence folder. I did not rely on the author's summary.
- **Reviewed:** `context/specifications/007-sqlite3-bz2-and-lzma.md` (draft, 124 lines, untracked), against the working tree at `dbef7f2`.
- **Ran (EXECUTED, darwin-arm64, wasmtime-py 49.0.0).**
  - **Where.** Probes and outputs are under `…/scratchpad/review-007/` (`probes/`, `out/`). Nothing under this repository's `build/` was read for writing or written.
  - **Artifacts.** The experiment's 3.15 set with the three modules, `…/scratchpad/research-stdlib-c/repo/build/artifacts/` (it predates spec 006's reactor).
  - **Runner.** This repository's `wasi_python.run` (spec 006's runner: `TMPDIR=/tmp`, a fresh private root when none is named, the default deadline), with `WASI_PYTHON_ARTIFACTS` set to that set. The probe driver is `probes/g.py`.
  - **Native.** The line's pinned host Python, python-build-standalone `cpython-3.15.0+20261009`, run with `-I` from the clone's `build/tools/python/`. This is the interpreter the oracle unpacks.
  - **The judge's own functions.** `paths.parse_manifest`, `manifest_pin_errors`, `licence_errors`, `pins.source_pair` and `pins.tree_drift` were run on the experiment's set, with the specification's additions patched in (`probes/judge_lic.py`).
  - **Not run.** `uv run pytest` and `scripts/build.sh`. Spec 006's build review owns this tree's `build/`, and the scoreboard writes under it. The experiment's judge run (`outputs/judge-after.txt`, 94/98) is the author's. I did not reproduce it.
- **Read (READ):**
  - CPython 3.15.0: `configure.ac:4507-4592` (SQLite), `:5729-5760` (bzip2, liblzma), `:8526-8545`; `Modules/makesetup:127-130`; `Modules/Setup.stdlib.in:67-68, 152`; `Modules/_sqlite/connection.c:1693, 2255`; `pyconfig.h.in`.
  - SQLite 3.54.1 `sqlite3.c`: `:11774-11782`, `:40845-40872`, `unixRandomness`, `unixSleep`, `:49160-49181`.
  - The judge: `tests/harness/paths.py`, `pins.py`, `needs.py`, `jobs.py`, `tests/checks/test_v1_5_rebuild_from_pins.py`, `test_v1_3_data_stack.py`, `test_rules.py`, `tests/harness/scan.py`, `tests/unit/test_artifact_rules.py`, `.github/workflows/release.yml`.
  - The experiment: `35_stdlib_libs.sh`, `edit.py`, `setup.sh`, `drive_lock.py`, and `outputs/`.

## Acceptance criteria against evidence

1. *The owner has approved the three licences first.* Checkable, and right. The notices are complete (finding 12). Question 9 is open in `questions-for-the-owner.md:82-92`.
2. *From an empty `build/`, the build passes, and steps 35 to 90 twice give the same bytes.* Checkable. The experiment did both (`outputs/rebuild-twice.txt`, `build-from-scratch.txt`). I did not re-run them. One input to the step can change the bytes without a pin (finding 6).
3. *`uv run pytest` green; the new jobs match native byte for byte; growth has its cause.* **Not reachable as written.** The `sqlite` job compares its database file whether the specification wants it or not, and that file differs from native's (finding 1). Several things the job is told to print differ between the guest's SQLite and native's (finding 2).
4. *The zero-patch check covers the three trees and passes.* Met in substance. `tree_drift` is empty for all three trees (EXECUTED). But the Design does not list every judge file the check needs (finding 3).
5. *A dry run of the release workflow passes every job.* **Not reachable as written.** The workflow's zero-patch step requires exactly `4 passed`, and the specification makes it 7 (finding 3).

## Findings, most severe first

1. **The `sqlite` golden job compares its database file, and that file is not native's** (`007:77-81`). High.
   - **What the specification says.** The database lives "in the job's output directory", and "the database file itself is not compared".
   - **What the judge does (READ, `tests/harness/jobs.py:44-49`).** `jobs.render` appends every file under the output directory to stdout. Then `compare` checks the result byte for byte. `test_v1_3_data_stack.py:20-23` and `run_native` both render `/out`. So a database in `/out` *is* compared.
   - **It differs (EXECUTED, `probes/dbfile.py`, `out/dbfile.txt`).** The same 50-row table, written natively and in the guest, gives 8,192 bytes each, with different SHA-256s (`fb13bb3c…` native, `35fb3605…` guest).
     - Bytes 96–99 hold the version of the SQLite that last wrote the file: `3053001` native, `3054001` in the guest.
     - With bytes 92–99 masked, the two files are equal (`d109cc4a…`).
     - So "its bytes carry SQLite's page layout, which matches" is almost true. But the file as a whole cannot match while the oracle's SQLite is another release (finding 2).
   - **Also.** A `-journal` file or a `.lock` directory left in `/out` would be rendered too. The `compress` job has the same trap: a `.tar.bz2` or `.tar.xz` left in `/out` goes into `.expected` as raw bytes.
   - **Fix.**
     - Both jobs write their working files under `/tmp`, or a directory the job makes outside `out_dir`, never into `out_dir`.
     - Or they delete the files before exiting.
     - Say which, and say that `out_dir` is empty at the end, so `render` adds nothing.

2. **The oracle's SQLite is 3.53.1, not 3.54.1, and some results differ from it** (`007:44-46`, `007:77-81`). High-medium.
   - **The versions (EXECUTED, `out/opts.native.txt`, `out/opts.guest.txt`).** `sqlite3.sqlite_version` is `3.53.1` natively and `3.54.1` in the guest.
   - **The options match, as Decision 4 says (EXECUTED).** `PRAGMA compile_options` gives the same `ENABLE_*` set on both, including `DEFAULT_AUTOVACUUM`, `DEFAULT_RECURSIVE_TRIGGERS` and `TEMP_STORE=1`. The only differences are the WASI ones the decision names, plus `COMPILER`, `MAX_WORKER_THREADS=0`, `MUTEX_OMIT` and `MAX_SCHEMA` (new in 3.54).
   - **Results that differ (EXECUTED, `probes/floats.py`, `out/floats.*.txt`).** These ran on the plain reactor against native.
     - `json_array(1.0/3)` renders as `0.333333333333333` natively and `0.33333333333333332` in the guest. Decision 10's job prints "JSON … functions".
     - The math functions agree for `exp`, `ln`, `sqrt` and `pow` over 399 inputs. They disagree for `sin`, `cos`, `tan`, `log10`, `atan` and `acos`, because the two libm implementations differ.
     - FTS5's `bm25()` scores differ: the SHA-256 of the result list differs, although the first rows print the same.
     - Equal: `printf('%.17g')`, `cast(x as text)`, `avg`, `sum` and `total`.
   - **Why this matters.** The job prints whatever native prints, and a `versions` line naming `sqlite3.sqlite_version` would differ too. The existing jobs handle libm with `round(…, 9)` (READ, `tests/jobs/pandas_csv.py:16-17`). The experiment's probe rounded its math results and printed no FTS5 scores (READ, `probe_sqlite.py:38-41`), so it never saw these differences.
   - **Fix.** Decision 10 states the job's output rules:
     - No SQLite version or error text in the output.
     - Every `SELECT` has an `ORDER BY` that gives a total order. Rank ties are broken by `rowid`.
     - FTS5 prints matches, not scores.
     - Floats leave SQLite through Python and are printed with the jobs' rounding. JSON holds integers and strings only, or its floats are rounded in Python after parsing.
     - Decision 4's reason changes to "the same feature set as native (`PRAGMA compile_options`, EXECUTED); native's SQLite is 3.53.1".

3. **The judge changes listed are not all the judge changes needed. Criterion 5 fails on the release workflow** (`007:58`, `007:71-84`, `007:100-102`). Medium-high.
   - **`.github/workflows/release.yml:62-67` (READ).** The zero-patch step runs the parametrized check, then `grep -Eq "^4 passed, …"`. The comment above it says "All four trees must pass". With bzip2, xz and sqlite added, the count is 7. As written, the release dry run (criterion 5) fails.
   - **`tests/harness/needs.py:42, 110` (READ).** The check calls `needs.need(f"source tree {component}")`. The vocabulary is built from `SOURCE_COMPONENTS = ("cpython", "numpy", "pandas", "zlib")`. An unknown name raises `KeyError` ("a harness bug, and fails loudly", `needs.py:134`). The tuple gains the three.
   - **`tests/harness/jobs.py:31` (READ).** `JOBS` gains `compress` and `sqlite`. Otherwise `regen.py` and `test_goldens_reproduce_under_the_pinned_oracle` never run them.
   - **`tests/unit/test_artifact_rules.py:20-48` (READ).** Its synthetic good set writes package lines from its own `PACKAGES` dict. Once `paths.PACKAGES` gains three names, `parse_manifest` reports `MANIFEST: no package line for bzip2` (and the others) on the "good" set (READ, `paths.py:193-195`). Its `PIN_FILES` need the three tarballs too.
   - **The SQLite notice is checked for presence only (EXECUTED, `out/judge_lic.txt`).**
     - With `LICENCE_COMPONENTS` gaining `bzip2`, `xz` and `sqlite`, `licence_errors` is empty. `bzip2` and `xz` are checked for content: their top-level `LICENSE` and `COPYING` are in the notices.
     - `sqlite` is presence-only. `licence_source("sqlite", m)` looks up package `sqlite`, but the package line is `sqlite-autoconf`. The SQLite tarball has no top-level licence file anyway (EXECUTED: `tar -tzf`).
     - That is acceptable. But Decision 6 says the two tuples "gain the three", and the names differ (`sqlite` against `sqlite-autoconf`). Spell out both tuples, and say SQLite's notice is presence-checked and why.
   - **`pins.SOURCE_PATTERNS` (EXECUTED).** With `bzip2-[\w.]+\.tar\.gz`, `xz-[\w.]+\.tar\.gz` and `sqlite-autoconf-\d+\.tar\.gz`, `source_pair` finds all three trees and `tree_drift` is `[]` for each. Name the patterns in the specification.
   - **Fix.** Add `release.yml` (`^7 passed` and the comment), `needs.py`, `jobs.py` and `tests/unit/test_artifact_rules.py` to the Kind and the Design. Say all of them go in under `--accept-judge`.

4. **SQLite's randomness in the guest comes from the clock's second, and a file planted in a reused root can set it** (not in the specification). Medium.
   - **Why (READ, `sqlite3.c`, `unixRandomness`).**
     - SQLite seeds its random generator by reading `/dev/urandom`.
     - If that open fails, it uses `time()` (whole seconds) and `getpid()`. On WASI, `osGetpid` is the constant 1 (`:40874-40876`).
     - A WASI root has no `/dev/urandom`, unless a file by that name was put there.
   - **Same second, same values (EXECUTED, `probes/rand_many.py`, `out/rand.txt`).** Five calls without `root`, back to back, printed `hex(randomblob(16))`. Calls 0 and 1 printed `14B608D9…`; calls 2, 3 and 4 printed `2D2BC08D…`. Each call had its own fresh root.
   - **A planted file sets the values (EXECUTED).** On a named root holding a planted `/dev/urandom` of zero bytes, two calls printed the same `29B72176…`. In the same runs, `os.urandom` differed each time.
   - **What it touches.**
     - `random()` and `randomblob()`. `lower(hex(randomblob(16)))` is a common way to make an ID in SQL.
     - The names of SQLite's temporary files. Two guests on one shared root in the same second draw the same names (INFERRED from the shared seed).
     - Native SQLite reads `/dev/urandom`, so this is a difference from native that Decision 8 does not list.
   - **It is a new planted-data channel for spec 006.** Spec 006's Decision 6 lists "the real clock and entropy" as unprotected, but not a file that sets one library's seed.
   - **Fix.**
     - Decision 8 and the README say it: SQLite's `random()` and `randomblob()` repeat for runs in the same second, so use Python's `secrets`, `uuid.uuid4()` or `os.urandom` for IDs.
     - Spec 006's "Safety" list gains "a planted `/dev/urandom` sets SQLite's randomness".
     - The fix belongs upstream: SQLite could use `getentropy()`, which wasi-libc provides, under `SQLITE_WASI`. Record that as the upstream route (§4.1).
     - A recipe fix would have to replace SQLite's randomness hook. That API carries the word §4.5 refuses (finding 9), so it is not the smallest thing. Say that it was weighed and declined.

5. **The lock is held during reads too, and a deadline stop leaves it as well** (`007:62-67`, `007:82-84`). Medium.
   - **An unfinished read locks out other connections (EXECUTED, `probes/readlock.py`, `out/readlock.*.txt`).**
     - Connection `a` runs `select x from t` and fetches one row. The cursor is still open.
     - In the guest, `<db>.lock` exists. Connection `b`'s read and `b`'s write both fail with `database is locked`.
     - Natively, `b` reads, and only `b`'s commit fails.
     - This matches `sqlite3.c:43078` ("a single reader blocks all other connections"), which the memo quotes. But Decision 8, the README sentence it dictates and question 9 all say "while it writes".
     - A pattern this breaks: iterating a cursor on one connection while reading or writing through another.
   - **Spec 006's deadline leaves the lock too (EXECUTED, `probes/deadline_lock.py`, `out/deadline_lock.txt`).** A write stopped by `deadline_s=1.0` on a named root leaves `k.db`, `k.db-journal` and `k.db.lock`. The next run gets `database is locked`. Decision 8 names "killed or out of fuel". Spec 006's defaults add the deadline and the memory limit as ways to stop a guest.
   - **The wait is real time.** Python's default `timeout=5.0` makes the second connection retry for about five seconds before it fails (READ: `unixSleep` uses `nanosleep`). The memo marks this INFERRED and did not run it.
     - A check written as Decision 10 words it, with default `connect()` arguments, sleeps five seconds per binary.
     - That costs no fuel. But it is wall-clock time in the judge, and it would push a lowered-deadline check toward its limit.
   - **Fix.**
     - Decision 8 says: "while a connection holds any open statement or transaction"; "killed, out of fuel, past its deadline or out of memory"; and "after the connection's busy timeout (5 s by default)".
     - Check `test_sqlite_leaves_a_lock_while_it_writes` connects with `timeout=0`, and it also asserts the open-read case.

6. **The step script reads an environment variable that changes the artifact** (`007:32-37`; the experiment's `35_stdlib_libs.sh:51`). Low-medium.
   - **What it does.** `SQLITE_OPTS` includes `${SQLITE_EXTRA:-}`. The experiment used it for its lean-SQLite variant (`outputs/lean-sqlite.txt`).
   - **The problem.** Decision 2 says the step is "as the experiment's". A builder whose shell has `SQLITE_EXTRA` set gets different bytes, and no pin or recipe line records it. That breaks §4.2's intent, which is that the build is decided by the pins and the recipe.
   - **Fix.** The step has no such hook. The options are written out in full.
   - **While there.**
     - Step 60 should stop with one line when `build/stdlib-libs/lib/libsqlite3.a` is missing. A step-60-only run on a tree built before 007 otherwise fails inside `make` with a long log (INFERRED).
     - Five lines of the experiment's script run past 100 columns (`:24, 34, 39, 46, 59`; the comment at `:46` is 142). Wrap them when the script moves into `scripts/steps/`.

7. **SQLite's temporary files on a Windows host are never exercised** (`007:47-49`; the memo's "Where it stopped"). Low-medium.
   - **The mechanism (READ, memo §6).** SQLite unlinks a temporary file right after opening it. The memo did not run that on Windows.
   - **On macOS it works (EXECUTED, `probes/spill.py`).** Under spec 006's `TMPDIR=/tmp`, a spill (`temp_store=file`, `cache_size=2`, an `ORDER BY` over 3,000 one-KB blobs, and a temporary table) runs. `/tmp` shows nothing extra during the spill, nor afterwards.
   - **What is missing.** The release workflow's verify job runs the judge on `windows-2025` (READ, `release.yml:86-92`). But no planned check makes SQLite spill, so the Windows path stays unrun.
   - **Fix.** The `sqlite` job forces one small spill, which is still deterministic output. Then the Windows verify job exercises it on every release.

8. **Small differences a reader will see, which the README and CHANGELOG should name** (`007:59-61`). Low.
   - **`sysconfig` says the modules are missing (EXECUTED, `probes/sysc.py`).** `MODULE__SQLITE3_STATE` is `'disabled'`, `MODULE__BZ2_STATE` and `MODULE__LZMA_STATE` are `'missing'`, and `PY_SQLITE_HAVE_SERIALIZE` is `0`. Natively they are `'yes'`, `'yes'`, `'yes'` and `1`. The cause is the `Setup.local` route, which configure never sees.
   - **`sqlite3.threadsafety` is `0` (native `3`).**
   - **`shelve` and `dbm` change backend (EXECUTED, `probes/mm.py`).** A new `shelve.open` file is now `dbm.sqlite3` (`dbm.whichdb` says so), where before it could only be `dbm.dumb`. So shelves get the lock directory too.
   - **`-V` and the missing zstd.** The new sentence ("no ctypes, mmap, sockets or ssl") still says nothing of `compression.zstd`, which is missing (EXECUTED: `_zstd` raises `ModuleNotFoundError`). Native 3.15 has it, and the specification puts it out of scope. Constitution §4.11 says missing modules are stated. `test_rules.py:95` checks only "32-bit", "no threads", "ctypes" and the speed phrase, so adding "zstd" costs the judge nothing.
   - **Fix.** Decision 7 lists these four. The `-V` sentence becomes "no ctypes, mmap, sockets, ssl or zstd".

9. **The word rule holds, with one cost the specification should own** (`007:50-53`). Confirmation, low.
   - **What holds.** The rule is a substring match on `vfs` in `recipes/`, `scripts/`, `src/`, `tests/` and `fixtures/` (READ, `scan.py:54-68`, `test_rules.py:16-23`).
     - `PRAGMA compile_options` in the guest contains no such word (EXECUTED), because `SQLITE_DEFAULT_UNIX_VFS` is not set.
     - Nothing in Decision 10's checks or jobs needs it, provided the jobs print no URI parameter and no compile options. Finding 2's rules already exclude both.
   - **The cost.**
     - SQLite's choice is upstream's default, and upstream doubts it: "should SQLITE_DEFAULT_UNIX_VFS be "unix-none"?" (READ, `sqlite3.c:40852`). The lock check in Decision 10 would catch a future pin that changed it. Good; say so in the check's docstring, without the word.
     - The rule also rules out the recipe-level fix for finding 4.
   - **Fix.** One sentence in Decision 5: the lock check is what holds the default, and a recipe that needed SQLite's OS-layer API would need a reasoned judge change first.

10. **Text** (`007:3-17`, `007:64`, `007:68-70`). Low.
    - **Decision 8 wording.** "`journal_mode=wal` is refused" should say "silently stays `delete`". That is what the experiment saw (`outputs/probe_sqlite.snapshot.out:39`).
    - **Decision 9.** "cost nothing" is true of the import. The snapshot still grew 3.2% and `-c pass` 0.33% (criterion 3). Say "they are already in the snapshot".
    - **Decision 4.** Add its label: EXECUTED by the experiment, and re-run here.
    - **Criterion 3.** Name the ratchet's flags. Snapshot `-c pass` fuel grows 0.33%, over `FUEL_TOLERANCE = 1e-4`, so the accept needs `--accept-growth "<why>"` beside `--accept-judge`.

11. **Confirmations; no change needed.**
    - **The pins (EXECUTED, `shasum -a 256`, `openssl dgst -sha3-256`).**
      - The three tarballs in the experiment's `downloads/` hash to the specification's values. Their sizes are 3,332,984, 810,029 and 2,799,797 bytes.
      - SQLite's SHA3-256 is `b6ced585…57d9c4`. It equals the line in `https://sqlite.org/download.html`, fetched today (`sqlite-autoconf-3540100.tar.gz,3332984,b6ced585…`).
      - GitHub's API gives the xz 5.8.4 `.tar.gz` asset digest `sha256:0014c788…b2591d9`, equal to the pin.
      - bzip2's value is the one widely published for 1.0.8. I did not re-verify its signature.
    - **The `=` trap is real, and the line avoids it (READ).** `makesetup:129` has `*=*) DEFS="$line$NL$DEFS"; continue;;`. The `_sqlite3` line the experiment used has no `=`. All four modules are in `sys.builtin_module_names` on both binaries (EXECUTED, `probes/bi.py`), so the check Decision 10 adds would catch a dropped line.
    - **`-DPY_SQLITE_HAVE_SERIALIZE` is the only define that changes compiled code (READ).**
      - For `_sqlite3`, configure adds `-I$(srcdir)/Modules/_sqlite`, which the line has, and `PY_SQLITE_HAVE_SERIALIZE` (`configure.ac:4517, 4561-4566`).
      - `PY_SQLITE_ENABLE_LOAD_EXTENSION` is set only with `--enable-loadable-sqlite-extensions`, which is off by default.
      - Configure also defines `HAVE_BZLIB_H`, `HAVE_LZMA_H` and `HAVE_LIBSQLITE3`, but no file under `Modules/`, `Include/` or `Python/` reads them (grep).
      - `_bz2` and `_lzma` get only their CFLAGS and LIBS.
      - The source list matches `Setup.stdlib.in:152`.
    - **SQLite cannot reach outside the root (EXECUTED, `probes/sec.py`, both binaries, `out/sec.*.txt`).** I put a host database with a `secret` table beside the root, plus a relative and an absolute symlink to it inside the root. None of the following read it:
      - `connect` and `ATTACH` of `/../outside.db`, `../../outside.db` and `/work/../../outside.db`;
      - the URIs `file:/../…`, `file:///../…`, `file://localhost/../…` and `…&vfs=unix-none`;
      - both symlinks;
      - `/etc/passwd`.

      Each one opened or created a file inside the root, or failed. SQLite resolves symlinks and `..` itself, inside the guest's own view.
      - `VACUUM INTO '/../escape.db'` wrote `escape.db` inside the root.
      - `pragma temp_store_directory='/..'` is refused.
      - `load_extension()` does not exist.
      - The two-argument `fts3_tokenizer` is disabled.
      - The host file was unchanged afterwards.
    - **Temporary files under spec 006 (EXECUTED).** `TMPDIR=/tmp` is used, and nothing is left behind (finding 7).
    - **The stale lock (EXECUTED).** A call without `root` never sees one, because its root is fresh. A planted `-journal` in a reused root is only more planted data: the guest could write the database itself.
    - **The licences (READ, EXECUTED).**
      - All 141 xz source and header files that went into `liblzma.a` (from the build's `.Plo` dependency files) carry `SPDX-License-Identifier: 0BSD`. The GPL and LGPL parts of the tarball are not compiled.
      - bzip2's seven files and two headers each point to `LICENSE`. That file covers "the associated library libbzip2".
      - `sqlite3.c` has no copyright or licence line besides the blessing.
      - The notice taken from `sqlite3.h` (its first comment) holds the blessing.
      - CPython's `_sqlite`, `_bz2module.c` and `_lzmamodule.c` are under `cpython.txt`.
    - **The judge's package rule (EXECUTED).** With `package sqlite-autoconf 3540100`, `manifest_pin_errors` is `[]`.

## Constitution checks

- **§4.1 (zero patches)** holds. `tree_drift` is empty for the three new trees (EXECUTED), and the experiment's `diff -r` agrees.
- **§4.2 (pins)** holds for the three tarballs, which I re-hashed and cross-checked. The `SQLITE_EXTRA` hook goes against its intent (finding 6).
- **§4.3, §4.4 and §4.6** hold. The memo found the same 43 imports (`outputs/imports.txt`). I did not re-run that.
- **§4.5** holds as designed, at the cost finding 9 names.
- **§4.8** held for me. The downloads ran only as build inputs and under wasmtime. The native interpreter I ran is the line's pinned build tool.
- **§4.9** holds if the lock check uses `timeout=0` (finding 5). As worded, it sleeps through real time without measuring it.
- **§4.10** holds for the specification's numbers, which cite the experiment. Decision 4 lacks its label (finding 10).
- **§4.11** wants the remaining missing module (zstd) and SQLite's differences stated (findings 4, 5 and 8).
- **§4.12** is correctly gated by criterion 1.
- **§5.2 (no open questions):** none is left open. The `configure` route is decided against, with a reason.
- **§7:** nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. **Fixed.** The database lives in the job's data directory; Decision 10 says why (bytes 96–99).
2. **Fixed.** Decision 10 states the rules: no version or error text, a total `ORDER BY`, floats rounded to 9 places, no `bm25()`, no JSON float text, no trigonometric results.
3. **Fixed.** Decision 10 lists `release.yml` (`^7 passed`), `needs.SOURCE_COMPONENTS`, `pins.SOURCE_PATTERNS`, `jobs.JOBS` and the synthetic set; it says SQLite's notice is presence-only.
4. **Fixed.** Decision 8 documents SQLite's weak randomness, its cause and the upstream fix, and adds the row to spec 006's Safety list.
5. **Fixed.** Decision 8 says the lock is held during unfinished reads and after a deadline stop; the check uses `timeout=0` and is renamed `test_sqlite_holds_a_lock_while_it_writes`.
6. **Fixed.** Decision 2 removes the environment hook and adds step 60's one-line stop.
7. **Fixed.** The `sqlite` job forces a temporary spill.
8. **Fixed.** Decision 8 names `sysconfig`, `threadsafety` and `dbm.sqlite3`; Decision 7 adds zstd.
9. Noted.
10. **Fixed.** WAL "silently stays `delete`"; Decision 9 says "already in the snapshot"; Decision 4 carries its label; criterion 3 names `--accept-growth`.
11. Noted.

## Verdict

**Not ready to build yet.** The design is sound, and the parts I could test hold:

- the three pins and their cross-checks;
- the `Setup.local` route with its one define;
- byte-identical source trees;
- complete licence notices;
- a SQLite that cannot leave the root.

What has to change before the build:

- **Findings 1 and 2.** As specified, the `sqlite` golden job cannot match native.
- **Finding 3.** Criterion 5 fails on the release workflow's `4 passed`, and the check needs `needs.py`.
- **Findings 4 and 5.** Three SQLite limits are missing from what the README will say: a predictable random seed that a planted file can set, the lock during reads, and the lock after a deadline.

All of these are changes to the text and the judge list, not to the design.

One line: the recipe is right and patch-free; keep the database out of `/out`, keep SQLite's version and unrounded floats out of the goldens, list every judge file that changes, and tell users that SQLite's randomness and its lock are weaker in the guest than natively.

## Confirmation by the reviewer, 2026-10-17

- **Reviewed:** the specification at `91d6c02` (revised), against the dispositions above.
- **Ran (EXECUTED).** One new probe, `probes/pyrand.py` (`out/pyrand.txt`), on the experiment's set through this tree's runner. It ran twice on each binary. I did not run pytest or touch `build/`.
- **Read (READ):** the revised specification; `tests/harness/jobs.py:138-161` (`stage_data`, `run_native`); `tests/harness/scoreboard.py:31-36`; the research memo at `91d6c02` (`grep` for `urandom`, `getentropy`, `randomness`).

### Each finding

1. **Confirmed fixed.** The database goes in the data directory. `stage_data` copies the fixtures into a fresh directory for each native run (`jobs.py:138-150`). So the database never lands in `fixtures/`, and `render` never sees it.
2. **Fixed in rule; the stated cause is wrong** (new finding C3).
3. **Confirmed fixed in Decision 10.** Two remnants are new finding C5.
4. **Fixed in substance.** One claim is not true at `91d6c02`, and one phrase misleads (new findings C1 and C4).
5. **Fixed in the text and the check's `timeout=0`.**
   - Decision 8 now claims that an unfinished read holds the lock. No check guards that.
   - AGENTS.md rule 3 says a failure mode, once seen, becomes a check. Add the open-read case to the lock check (C6).
   - The README bullet still does not say that the error comes only after the busy timeout, 5 s by default. The check's bullet says it; the user-facing text should too (C6).
6. **Confirmed fixed.**
7. **Fixed in intent, not yet certain to happen** (new finding C2).
8. **Confirmed fixed.** One word: `sysconfig` reports `_sqlite3` as `'disabled'`, while `_bz2` and `_lzma` are `'missing'`. "Missing or disabled" is exact.
9. **Noted. Nothing to confirm.**
10. **Confirmed fixed.**
11. **Noted. Nothing to confirm.**

### New findings from the revision, most severe first

C1. **Decision 8 cites a memo record that does not exist** (`007:79-81`). Medium-low.
    - Decision 8 says: "The upstream fix (SQLite using `getentropy` on WASI) is recorded in the research memo."
    - At `91d6c02`, `context/research/2026-10-17-sqlite-bz2-and-lzma.md` contains neither `urandom`, `getentropy` nor `randomness` (READ, `grep`). The commit changed only the specification and this review (`git show --stat`).
    - Under §4.10, a claim must point at its evidence.
    - **Fix.** Add the section to the memo: `unixRandomness`, the time and pid fallback, this review's EXECUTED rows, and the upstream route. Or cite this review instead of the memo.

C2. **The spill is not certain as worded** (`007:98-100`). Low-medium.
    - Decision 10 says "a temporary table large enough to spill to a temporary file".
    - A temporary database's pages reach its file only when the page cache overflows. The default cache is `DEFAULT_CACHE_SIZE=-2000`, about 2 MB, in both builds (EXECUTED, `PRAGMA compile_options`).
    - A table under that size never touches the file (INFERRED from SQLite's pager). From inside the guest, nothing can show whether it did, because the file is unlinked.
    - So a job that looks right could leave the Windows path unrun without anyone noticing.
    - **Fix.** Make the spill certain by construction, as `probes/spill.py` did: `PRAGMA temp_store=file` and `PRAGMA cache_size=2`, then a temporary table and an `ORDER BY` over a few thousand one-KB rows. Print only counts and ordered keys.

C3. **The golden rules give the wrong cause for the float differences** (`007:101-104`). Low.
    - Decision 10 says "the review found these differ between 3.53.1 and 3.54.1". That is not what the review found.
    - The review compared native macOS SQLite 3.53.1 with the guest's 3.54.1 on wasi-libc. The trigonometric, `log10` and `bm25()` differences track the two libm implementations (INFERRED: `exp`, `ln`, `sqrt` and `pow` agreed). They would remain with one SQLite release on both sides. They may also differ between the oracle's own hosts, because `test_goldens_reproduce_under_the_pinned_oracle` runs natively wherever the oracle is present.
    - The JSON float text may be the release difference or a platform one. The review did not isolate it.
    - Why it matters: a future reader could think that bumping the oracle's Python lifts the rules.
    - **Fix.** Say "differ between the oracle and the guest (libm, and possibly the SQLite release)". Round floats with the jobs' existing helper (`format(round(float(x), 9) + 0.0, ".9g")`, `tests/jobs/pandas_csv.py:16-17`) after they leave SQLite, not with SQL's `round()` alone.

C4. **"Seeded from … the process id" reads as if the pid varied** (`007:75-77`). Low.
    - On WASI, SQLite's `osGetpid` is the constant 1 (READ, `sqlite3.c:40874-40876`). The only varying input is the second.
    - **Fix.** "Seeded from the time in whole seconds (the process id is always 1 on WASI)."
    - **The sentence's other claim holds (EXECUTED, `out/pyrand.txt`).** Python's `random`, `secrets`, `os.urandom` and `tempfile` names differ from run to run on both binaries. On the snapshot, `random` is already imported, and it still varies.

C5. **Two remnants of finding 3** (`007:8-12`, `007:63`, `007:110-116`, `007:125-135`). Low.
    - **Kind and Design are stale.** They still list only `tests/harness/paths.py` and `pins.py`. Decision 10 now also changes `release.yml`, `needs.py`, `jobs.py` and `tests/unit/test_artifact_rules.py`. Make the Kind and the Design say so.
    - **The tuples are still not spelled out.** Decision 6 still says `LICENCE_COMPONENTS` and `PACKAGES` "gain the three". Write `LICENCE_COMPONENTS += ("bzip2", "xz", "sqlite")` and `PACKAGES += ("bzip2", "xz", "sqlite-autoconf")`.
    - **The scoreboard does not name SQLite's notice.** The line Decision 10 cites reads "licence content of wasi-libc, llvm-runtimes and unpinned components (presence only)" (`scoreboard.py:34`). SQLite is pinned, so the line does not cover it.
    - **Fix for the scoreboard line.** Either extend `NOT_MACHINE_CHECKED`, a judge change that goes under `--accept-judge` with the rest, or drop the claim that it "already names" SQLite's notice. `test_v1_1`'s own scope line does list `sqlite` under "presence only" (READ, `test_v1_1_artifact_set.py:92`), so the fact is still reported.

C6. **The lock check and the README bullet lag Decision 8** (`007:68-70`, `007:106-109`). Low.
    - **Fix.** The lock check gains the open-read case: `a` fetches one row of an open `SELECT`, then `b` with `timeout=0` gets "database is locked". The README bullet adds "after the connection's busy timeout (5 s by default)".

### Constitution, after the revision

- §4.1, §4.2, §4.5, §4.9 and §4.12 hold. The `SQLITE_EXTRA` hook is gone, and the lock check uses `timeout=0`.
- §4.10 is tripped by C1 alone: a claim that points to a record that is not there.
- §5.2: no open question.
- §7: nothing tripped.

### Verdict after the revision

**Ready to build once C1 and C2 are corrected in the text.** Every original finding is fixed or answered, and none is reopened in substance.
- **C1.** A claim that cites a missing record.
- **C2.** Without it, the job may never spill, and the Windows path stays unrun.
- **C3 to C6.** One-line wording and list changes. They can go in at the same time.

None of these changes the design. The build still waits on the owner's answer to question 9.

One line: the revision answers all eleven findings. Record the randomness section where the specification says it is, and force the spill with two pragmas, and 007 can be built once the licences are approved.

## The author's answers to the confirmation

- **C1:** fixed. Decision 8 cites the review's finding 4 for the upstream fix, and the memo's "Where it stopped" gains it at landing.
- **C2:** fixed. The job forces the spill with `PRAGMA temp_store=file` and `cache_size=2`.
- **C3:** fixed. The float differences are attributed to the math library; floats are rounded by the jobs' helper after they leave SQLite; `log10` joins the excluded results.
- **C4:** fixed. The process id is always 1 on WASI; `tempfile` names join the unaffected list.
- **C5:** fixed. Kind and Design list every judge file; Decision 6 spells out `sqlite` (notice) and `sqlite-autoconf` (MANIFEST); the scoreboard line gains SQLite's.
- **C6:** fixed. The lock check also covers an unfinished `SELECT`; the README bullet names the busy timeout. `_sqlite3` is "disabled" in `sysconfig`.
