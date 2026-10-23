# Review of 007 — sqlite3, bz2 and lzma, built in (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I was given `AGENTS.md`, the constitution (§4.12 and §4.15 noted), the reviews README, spec 012's build review for format, the specification with its landing notes (A1 to A8), its pre-build review, the research memo, the patch and the evidence folder. I checked the landing notes against the clone. I did not take them on trust.
- **Reviewed:** `spec007.patch` (25 files, +792 −28), uncommitted in the scratch clone at `3ee5bbe`. The patch is byte-identical to the clone's `git diff HEAD` (EXECUTED, `cmp`). The set reviewed is the clone's `build/artifacts`, with `SHA256SUMS` `b7473480…`.
- **Where.** My probes, outputs and backups are under `…/scratchpad/review007b/` (`probes/`, `mut/`, `backup/`, `judge-full.txt`, `growth.txt`, `envexp/`). I ran every guest probe through `wasi_python.run` from the clone's venv with `WASI_PYTHON_ARTIFACTS=<clone>/build/artifacts`. The read-only probe is the one exception: it used the judge's own `tests/harness/guest.run`, because `run` has no read-only grant.
- **Re-ran (EXECUTED, darwin-arm64):**
  - `uv run pytest` (no `--accept`): exit 1, `451 passed, 3 skipped`. The scoreboard is `150/153 pass · 0 gap · 3 blocked · 0 fail (unit suite 301/301)`. The ratchet reads `lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 8 · grew 32` and `RED: 32 metric(s) grew`. This is the landing notes' block, line for line.
  - `uv run python tests/jobs/regen.py --check`: all five goldens reproduce under the oracle.
  - The workflow's zero-patch step, verbatim: `7 passed, 11 deselected`, and its `grep` matches.
  - `uv run ruff check src tests`: clean. `ruff format --check`: 45 files already formatted.
  - `sh scripts/build.sh 35 60 70 80 90`, four times, for the mutations and the restore. The restore run gave a `SHA256SUMS` and an artifact tree identical to the ones I found (`cmp`, `diff -r`).
- **Left as found (EXECUTED).** `git status` and `git diff` match my snapshot taken before the review (`cmp`). Every mutated file was copied back and its SHA-256 checked. `build/logs` and `build/progress` were restored from backups. I did not touch the main repository: I only cloned it into the scratchpad, to check that the patch applies.

## Acceptance criteria against evidence

1. *The owner approved the three licences first.* **Met** (READ). Constitution §4.12 names SQLite (public domain), bzip2 (BSD-style) and liblzma (0BSD), approved 2026-10-17.
2. *From an empty `build/` the build passes; steps 35 to 90 run twice give the same bytes.* **Met.**
   - The full build from empty is the author's (READ, `build-macos.txt`). The Linux aarch64 build is also the author's: `linux-out/SHA256SUMS` and `MANIFEST` equal macOS's (EXECUTED here, `cmp`).
   - I re-ran steps 35, 60, 70, 80 and 90 after restoring the recipe, and got the same `SHA256SUMS`, byte for byte (EXECUTED). That makes three equal runs of step 35 onward, counting the author's two.
3. *`uv run pytest` green; the new jobs match native byte for byte; every growth has a cause.* **Met**, with the accept still to come.
   - The run is red only for growth (EXECUTED). Both jobs pass, and both goldens reproduce natively.
   - I recomputed the growth table from `build/progress/latest.json` and `context/progress/accepted.json` (EXECUTED, `growth.txt`). It has 32 rows. Every number equals the landing notes' table, and the six shrinking metrics match too.
   - The causes check out:
     - A fresh snapshot holds `bz2`, `lzma`, `_bz2` and `_lzma` but not `sqlite3`; the plain reactor holds none of them (EXECUTED).
     - `import sqlite3` costs 6,739,663 instructions on the snapshot (EXECUTED: fuel 88,755,397 against 82,015,734 for `pass`). `import bz2, lzma` costs 393.
4. *The zero-patch check covers the three trees and passes.* **Met** (EXECUTED).
   - It gives 7 passed. Each new tree has exactly its tarball's file count (xz 655, bzip2 56, sqlite 49), and no file was added.
   - Mutations 8 and 10 show the check bites.
5. *A dry run of the release workflow passes every job.* **Not shown.** It needs a push, as the notes say. I ran the zero-patch step locally. Whether `ubuntu-24.04-arm` rebuilds the same bytes is INFERRED, not shown (see "Host neutrality" below).

## Findings, most severe first

1. **The README and CHANGELOG say `sqlite3` "gives native's results", and some of its results differ from native's** (`README.md`, *sqlite3 in the guest*, first paragraph; `CHANGELOG.md`, the sqlite3 bullet). Medium.
   - **The evidence (EXECUTED, `probes/diff.py`).** I ran the same script natively (the line's pinned 3.15) and on the plain reactor, and compared the outputs (`diff.native.txt`, `diff.guest.txt`).
     - SQLite's `sin`, `cos`, `tan`, `log10`, `atan` and `acos` give different values over 199 inputs. They follow the C library.
     - `json_array(1.0/3)` prints `0.33333333333333332` in the guest and `0.333333333333333` natively. This is the release difference: 3.54.1 against native's 3.53.1.
     - `exp`, `ln` and `sqrt` agree.
   - **Why it matters.** The golden job was designed around these differences (Decision 10), and it is right to be. But the README states the claim with no exception, against §4.10 and §4.11. A user who compares trigonometric results, or JSON float text, with native will see the difference.
   - **Fix.** Qualify the claim in both files. For example: "gives native's results, except SQLite's trigonometric and `log10` functions, which follow the C library, and what changed between SQLite releases (native's is 3.53.1), such as JSON's float text."

2. **A database in a read-only grant cannot be opened, even with `mode=ro`** (not in the README). Medium-low.
   - **What happens (EXECUTED, `probes/ro.py`, through the judge's harness runner).** The database `/data/ro.db` sits in a read-only extra preopen.
     - `connect("/data/ro.db")` fails with "access permission denied", and so does `file:/data/ro.db?mode=ro`.
     - `file:/data/ro.db?immutable=1` reads it.
     - On a writable grant all three read it, and the `.lock` directory is gone afterwards.
   - **The cause (INFERRED from `sqlite3.c`).** SQLite's WASI locking takes a read lock by making `<db>.lock` beside the database, and a read-only directory refuses that.
   - **Who meets it.** `run` grants only a writable root, so a `run` caller never meets this. But extra preopens are a supported embedding pattern (`test_extra_preopens_work_on_the_snapshot`). An embedder that grants a read-only data folder, which is the natural way to hand over a database, gets an error where native reads.
   - **Fix.** Add one bullet to *sqlite3 in the guest*: "a database in a read-only directory opens only as `file:<path>?immutable=1` (`uri=True`), because the lock is a directory beside it". Mention it in the CHANGELOG too.

3. **The README's facts table still gives the old sizes** (`README.md:43`). Low-medium.
   - The row reads `29.8 MB / 63.5 MB / 11.1 MB`. The set is now 31.8 MB / 65.5 MB / 11.1 MB (EXECUTED, `ls -l`).
   - The CHANGELOG's "about 2 MB" is right, but the README's own number is stale (§4.10).
   - The landing notes flag the build-time row (4 min 19 s) under "Left over". They do not flag this one.
   - **Fix.** Update the row from the table in the landing notes. Either re-measure the build-time row or mark it as predating step 35.

4. **Step 35 says no environment variable changes the archives, and one does** (`scripts/steps/35_stdlib_libs.sh:6`, and Decision 2's "it reads no environment variable that could change the artifact"). Low.
   - **The experiment (EXECUTED, `envexp/`).** I ran xz's `configure` and `make` exactly as step 35 does, in a scratch directory with a different path.
     - A clean environment gives `ca6e4748…`, equal to the clone's `liblzma.a`. So the build path does not reach the archive.
     - `CPPFLAGS="-I/opt/homebrew/include -DLZMA_UNSTABLE"` gives the same bytes.
     - `CPPFLAGS=-fno-inline` gives `83cdb1a3…`, 208,492 bytes instead of 213,672.
   - **Why.** Autoconf reads `CPPFLAGS`, `LDFLAGS`, `LIBS` and `CONFIG_SITE` from the environment, and `make` reads `MAKEFLAGS`. The step sets only `CC`, `AR`, `RANLIB` and `CFLAGS`.
   - **How much it matters.** Steps 20 and 60 already have the same exposure, and CI runners do not set these variables. The same-bytes gate would catch a difference. So this is an overclaim in a comment, not a hole in the gate.
   - **Fix.** Either pass `CPPFLAGS= LDFLAGS= LIBS= CONFIG_SITE=/dev/null` on the `configure` line, or reword the comment and Decision 2.
   - Either edit changes the script's recipe hash in `MANIFEST` (`git ls-files scripts`). So steps 90 and the judge must re-run, and the hashes in the landing notes change.

5. **"Out of memory" does not leave the lock; a hard exit does** (`README.md`, third bullet of *sqlite3 in the guest*; the CHANGELOG; Decision 8). Low.
   - **The evidence (EXECUTED, a reused root with a 256 MiB limit).** Each case opened a write transaction first.
     - **A Python `MemoryError` leaves nothing.** I tried one huge allocation and a loop of 1 MiB allocations. Each ended with exit 1 and left only `k.db`: the interpreter unwinds and closes the connection.
     - **`os._exit(3)` leaves the lock and the journal.** It left `k.db`, `k.db-journal` and `k.db.lock`.
     - **Running out of fuel leaves them too**, the same three files.
   - **Fix.** List "killed, out of fuel, past its deadline, or a hard exit such as `os._exit`". Drop "out of memory", or keep it only for a memory failure that traps.

6. **The probe cited for "on a fresh snapshot `bz2` and `lzma` are in `sys.modules` and `sqlite3` is not" cannot show it** (`build007/probes/claims.py`; landing notes, "The README's SQLite facts"). Low.
   - The probe imports `sqlite3`, `bz2` and `lzma` before it prints membership, so its output is `modules True True True`. That output contradicts the sentence it is cited for.
   - The claim itself is true (EXECUTED here: the snapshot has `bz2`, `lzma`, `_bz2` and `_lzma` before any import, and no `sqlite3`).
   - **Fix.** Cite a probe that checks before it imports, or this review.

7. **Two licence notices can lose their substance without the judge noticing** (`tests/harness/paths.py`, `licence_source` and `_top_level_licence`). Low.
   - **The xz notice (mutation 3 survived).** The xz notice is checked against `COPYING` only. Removing `COPYING.0BSD`, the licence that covers the linked library, still passes.
   - **The SQLite notice (mutation 5 survived).** It is presence-only, as documented. A notice reading "not a licence" passes.
   - **The practical risk is small.** 0BSD asks for no notice, and the content shipped is right (READ):
     - `xz.txt` holds `COPYING` and `COPYING.0BSD`;
     - `bzip2.txt` is the `LICENSE` file;
     - `sqlite.txt` is the blessing from `sqlite3.h`.
   - **Fix (optional).** Have the scoreboard's "not machine-checked" line name xz's 0BSD text. Or make the SQLite check require "disclaims copyright", the phrase `sqlite_notice()` already asserts at build time.
   - **While there.** The line's wording "wasi-libc, llvm-runtimes, SQLite's and unpinned components" reads awkwardly.

8. **The clone is one commit behind `main`** (process). Low.
   - **Where `main` is.** `main` is now `6634dee` (the 0.1.0a2 security review). That commit changes `runner.py`, `test_v1_2_hostile_guest.py`, the README, the CHANGELOG, the constitution and `accepted.json`.
   - **The patch still fits.** `git apply --check` of the patch applies cleanly on a clone of `6634dee` (EXECUTED). The new accepted state moves no metric against the one used here and adds one check, `test_a_guest_that_uses_up_host_descriptors_cannot_make_run_raise` (EXECUTED). So the growth table should hold (INFERRED).
   - **What the landing needs.** It must re-run the judge on `main` plus the patch. The ratchet line will then read "vs 3ee5bbe…", and the judge-changed list may differ. The landing notes should give that run's numbers.
   - The README's new *Not protected* text from `6634dee` and this patch's additions land in the same paragraph without a textual conflict. Read them together once applied.

9. **A dropped `Setup.local` module still builds green** (mutation 12). Informational.
   - With `-DPY_SQLITE_HAVE_SERIALIZE=1`, `build.sh 60 70 80 90` exits 0 with a smaller reactor (30,016,656 bytes). Only the judge notices: `test_stdlib_c_modules_are_builtin` fails on both binaries.
   - That is the check working as designed. A one-line assertion in step 60 (the three names in the generated `config.c`) would stop it at build time. It is optional.

## Verified, no change needed

- **Zero patches (§4.1).** EXECUTED:
  - the three trees match their tarballs, file for file;
  - `Setup.local` is written to the build directory `$W/Modules/`;
  - xz is configured from `build/xz-build` (a VPATH build);
  - bzip2's and SQLite's objects go to `*-build/`;
  - `hostmodule.c` and `inittab.c` are copied into `$CP/Modules/` (a CPython tree). That copy is pre-existing behaviour, and it is not this spec's.
- **The pins (§4.2).** EXECUTED:
  - all three tarballs hash to the pins and to the `MANIFEST` `pin` lines;
  - SQLite's SHA3-256 is `b6ced585…7657d9c4`, the value the pre-build review matched to sqlite.org;
  - there are 39 `pin` lines (A1).
  - Step 35 calls `pinned` for all three before its `rm -rf`. With one digit of bzip2's pin changed, it stopped with `does not match its pin` and left `build/` untouched (same inodes).
- **Host neutrality (A2).** EXECUTED unless marked:
  - No archive and no artifact holds a build path: 0 hits for `/Users/`, `/private/tmp` or `scratchpad`.
  - `liblzma.a` built in another directory is byte-identical.
  - xz's `config.h` holds only facts about the wasm target (`HAVE_*`, `TUKLIB_*_SYSCONF`, `NDEBUG`). Its `configure` has no `CC_FOR_BUILD` (READ).
  - macOS (BSD `sed`/`awk`, bash as `sh`) and Debian trixie (dash, GNU `sed`/`grep`) gave identical sets (`cmp` of the author's `linux-out/`).
  - That `ubuntu-24.04-arm` (dash, GNU tools, GNU Make 4.3) gives the same bytes is INFERRED from this. The release gate is what proves it.
- **The `-V` sentence.** EXECUTED. Both binaries print "…no ctypes, mmap, sockets, ssl or zstd…", the same text as `README.md:55`. `compression.zstd` raises `ModuleNotFoundError`. `mmap` and `ctypes` are the existing stand-ins.
- **The lock check** holds what Decision 8 says. EXECUTED:
  - Mutations 1 and 13 kill it.
  - `timeout=0` keeps the judge off real time. A `timeout=0.3` probe showed the busy wait is real time (0.3 s), as the README says.
- **SQLite's weak randomness.** EXECUTED:
  - Five calls without `root` in one second all gave `FEC97A59…` from `randomblob(16)`, while `os.urandom` differed each time.
  - A planted zero-byte `/dev/urandom` gave `29B72176…` on two calls more than a second apart, the same value the pre-build review saw. So the planted seed is constant, not only per-second.
  - `unixRandomness` falls back to `time()` and `osGetpid` = 1 (READ, `sqlite3.c:47757`).
  - The README's bullet and its *Not protected* row say this correctly.
- **The README's other sqlite claims.** EXECUTED on both binaries:
  - `threadsafety` 0;
  - `sysconfig` gives `missing`, `missing`, `disabled` and 0;
  - `journal_mode=wal` gives `delete`, and `wal` after `locking_mode=exclusive`;
  - `serialize()` works and `enable_load_extension` is absent;
  - `shelve` creates `dbm.sqlite3`;
  - a deadline stop leaves the lock and the journal; removing the lock lets the next call read the database.
  - `PRAGMA compile_options` matches native apart from the WASI options, `COMPILER`, `MAX_SCHEMA` and the mutex and thread options (Decision 4).
- **The spill in the `sqlite` job reaches temporary files.** EXECUTED, `probes/sec2.py`:
  - With `temp_store=file` the guest's next free descriptor rises from 4 to 7 during the temp table and the sort. With `temp_store=memory` it stays at 5.
  - `/tmp` lists nothing during or after, so the files are unlinked while open.
  - So the Windows verify job does exercise the unlink-while-open path. Windows itself was not run, here or by the author.

## Security (§4.4, §4.15)

Adding sqlite3, bz2 and lzma opens no new channel to the host.

- **Nothing new reaches the host (EXECUTED, `probes/sec.py`, `sec2.py`, both binaries).**
  - **The setup.** A host database `outside.db` with a `secret` table sat beside each root. Inside the root I put a relative link to it, made by the guest, plus an absolute link to it and a link to its directory, both planted by the host.
  - **Opening it.** None of these read the secret:
    - `connect` of `/../`, `../../` and `/x/../../`;
    - the URIs `file:/../`, `file:///../` and `file://localhost/../`, with and without `vfs=` parameters;
    - the three links;
    - `/etc/passwd`.
  - **ATTACH.** `ATTACH` of the same paths read nothing either. Each one created or opened a file inside the root, or failed with "unable to open".
  - **Writing out.** `VACUUM INTO '/../escape.db'` and `'../../escape2.db'` wrote inside the root. `VACUUM INTO '/absdir/escape3.db'` (through the host-planted link) failed.
  - **Settings.** `pragma temp_store_directory='/..'` is refused, and `load_extension` does not exist. The host database was unchanged afterwards, and nothing was written beside the roots.
  - The one-argument `fts3_tokenizer` returns NULL. The two-argument form, which takes a pointer, is off by default.
- **Temporary files** go to `TMPDIR` inside the root. If it is missing, SQLite falls back to other directories in the guest's view: with `TMPDIR=/nonexistent` the spill still ran and left nothing (EXECUTED).
- **`dbm.sqlite3` and the lock directory** live beside their file, in the same grant (EXECUTED). A shared writable grant lets one guest hold another's database locked. That is the same planted-data class the README already lists.
- **Memory.** `zeroblob(900000000)` and a 600 MB `lzma` round trip both end in a clean `MemoryError` under the default limit, with no trap (EXECUTED).
- **The guest's imports.** The judge's import checks pass on both binaries (EXECUTED, in the full run): the guest still has two imports only.
- **No default moves (READ).** The runner is unchanged by the patch. No default is loosened, so §4.15 needs no owner decision.

## Mutations

Each mutation was applied, the named checks were run, and the file was restored byte for byte (SHA-256 compared with the copy taken first). The rebuild mutations ended with a restore build whose `SHA256SUMS` and tree equal the pre-review set.

| # | mutation | caught by | result |
|---|---|---|---|
| 1 | the lock check's program opens its database in SQLite's no-locking mode (a URI parameter) | `test_sqlite_holds_a_lock_while_it_writes` | killed: `write False 10`, then "disk I/O error" |
| 2 | `sqlite.py` puts `jobs.db` in the output directory | `test_sqlite_job_matches_native` | killed (on the `files` line) |
| 3 | `LICENSES/xz.txt` without its `COPYING.0BSD` part | `test_licence_notices_cover_every_component` | **survived** (finding 7) |
| 4 | `LICENSES/sqlite.txt` emptied | same | killed |
| 5 | `LICENSES/sqlite.txt` replaced by "not a licence" | same | **survived**: presence-only, as documented (finding 7) |
| 6 | `LICENSES/bzip2.txt`, one word changed | same | killed |
| 7 | one hex digit of bzip2's pin changed | step 35; `test_manifest_pins_match_the_pin_list`, the licence check, zero-patch `[bzip2]` | killed: step 35 stopped before touching `build/`; 3 checks failed |
| 8 | one byte appended to `build/xz-5.8.4/src/liblzma/common/common.c` | `test_source_tree_matches_its_tarball[xz]` | killed: "modified" |
| 9 | a file added inside the SQLite tree | same | survived: "files a build adds inside a source tree" is listed as not machine-checked |
| 10 | the SQLite tree moved away | the workflow's `^7 passed` grep | killed: `6 passed, 1 skipped`; the grep failed |
| 11 | `libsqlite3.a` moved away | step 60's stop | killed: one line, exit 1, `build/link` untouched |
| 12 | `-DPY_SQLITE_HAVE_SERIALIZE=1` in `Setup.local` (rebuild 60–90) | `test_stdlib_c_modules_are_builtin[plain/snapshot]`, the lock check, the `sqlite` job | killed by all four; the build itself exited 0 (finding 9) |
| 13 | SQLite built with the no-locking default and without FTS5 (rebuild 35, 60–90) | the lock check, the `sqlite` job, the word rule | killed by all three: no `.lock`, "no such module: fts5", and `test_no_embedder_name_in_code` fired on the script |
| 14 | liblzma configured without the SHA-256 check (rebuild 35, 60–90) | `test_compress_job_matches_native` | killed: "Unsupported integrity check" |

## Constitution checks

- **§4.1** holds: the trees are unmodified and every adaptation is in `recipes/` and `scripts/`.
- **§4.2** holds: the three pins are verified on download and again on use.
- **§4.3** holds: there is no host branch in step 35.
- **§4.4** holds: the import checks pass.
- **§4.5** holds: the word appears in no code, and mutation 13 shows the rule fires.
- **§4.6** holds: three notices were added and the other nine are unchanged.
- **§4.8** holds: xz's `configure` runs as a build tool under `build/`. I ran only the line's pinned 3.15 natively, as the oracle does.
- **§4.9** holds: the lock check uses `timeout=0`, and no check measures time.
- **§4.10:** findings 1, 3, 5 and 6.
- **§4.11:** findings 1, 2 and 5.
- **§4.12:** the licences were approved before the build.
- **§4.13** holds: ruff is green and the unit suite gives 301/301.
- **§4.14:** nothing was committed.
- **§4.15** holds: no default moves and no channel opens.
- **§7:** nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Fixed. README and CHANGELOG: native's results except SQLite's `sin`, `cos`, `tan`, `atan`, `acos` and `log10`, which follow the C library, and what changed since native's SQLite 3.53.1, such as JSON's float text.
2. Fixed. README bullet and CHANGELOG: a database in a read-only directory opens only as `file:<path>?immutable=1` with `uri=True`; `mode=ro` is not enough.
3. Fixed. Sizes now 31.8 / 65.5 / 11.1 MB; the build-time row re-measured on a full build from pins: 5 min 41 s (EXECUTED, `build-v2.txt`).
4. Fixed both ways: step 35 unsets `CPPFLAGS LDFLAGS LIBS CONFIG_SITE MAKEFLAGS MFLAGS GNUMAKEFLAGS CPATH C_INCLUDE_PATH LIBRARY_PATH`, and its own output variable is renamed `LIBDIR` (as `LIBS`, a `LIBS` in the environment would have been exported to xz's configure; `OUT` is taken by `common.sh`). Decision 2's text says so. The rebuild gave byte-identical archives and artifacts (`before-v2.sha` = `after-v2.sha`).
5. Fixed. 'out of memory' replaced by 'or by a hard exit such as `os._exit`' in the README, the CHANGELOG and the spec.
6. Fixed. The landing notes cite this review's EXECUTED check, not `probes/claims.py`.
7. Fixed (taken). xz's notice must also hold `COPYING.0BSD` from the pinned tarball; SQLite's must hold the blessing that heads the pinned `sqlite3.h` (`tests/harness/paths.py`, `_more_licence`; the package lookup maps `sqlite` to `sqlite-autoconf`). Both mutations now fail the check (EXECUTED). The scoreboard line no longer names SQLite.
8. Done. The clone is rebased onto `main`; the landing re-runs the judge on `main` plus the change and gives that run's numbers.
9. Taken. Step 60 stops when `Modules/config.c` lacks `PyInit__bz2`, `PyInit__lzma` or `PyInit__sqlite3`.

## Verdict

**Does not land yet.**

- **What holds.** The build is sound, reproducible and safe. All of these hold under re-run and mutation:
  - the pins;
  - zero patches;
  - the same bytes on two hosts;
  - the goldens;
  - the lock check;
  - the growth table;
  - the sandbox.
- **What must happen first.** Findings 1 to 5 must be fixed or answered in writing. Four are documentation. Finding 4 is a comment, or a one-line environment scrub. If the author edits step 35 for it, the recipe hash in `MANIFEST` changes, so step 90 and the judge must re-run.
- **How it lands.** The landing re-runs the judge on `main` (`6634dee`) with the patch applied (finding 8) before the `--accept`.

One line: the code is right and safe to land; five claims in the text need fixing first.

## Confirmation (2026-10-17)

- **Who.** A second fresh agent (Claude Opus 5.5). I wrote neither the change nor the review above. I read `AGENTS.md`, the constitution, this review with its dispositions, `git show HEAD` (the fixes, `466a3b2`) and `git diff 1745ac1 HEAD` in the clone.
- **Where.** My probes and outputs are under `…/scratchpad/confirm007/`. Guest probes ran through `wasi_python.run` from the clone's venv with `WASI_PYTHON_ARTIFACTS=<clone>/build/artifacts`. The read-only probe used the judge's `tests/harness/guest.run`, as the review did.
- **Left as found (EXECUTED).** `git status`, `git diff` and the SHA-256 of every file under `build/artifacts` equal my snapshot taken first (`cmp`). The judge run wrote only its usual files under `build/`. Nothing was accepted. This section is my only edit.

### The scoreboard (EXECUTED)

`uv run pytest -m "not slow" -p no:cacheprovider` in the clone, exit 1:

```
wasi_python v1: 145/154 pass · 0 gap · 3 blocked · 0 fail · 6 deselected   (unit suite 301/301)
  v1.1  artifact set        24/25  blocked 1
  v1.2  portable, sealed    30/31  blocked 1
  v1.3  data stack           9/15
  v1.4  embedding           48/48
  v1.5  rebuild from pins   18/18
  rules constitution rules  16/17  blocked 1
blocked by: prior-art clones 1 · three systems 1 · wheel 1
next: context/specifications/004-alpha-releases.md (unblocks 2, closes 0)
ratchet vs 3ee5bbe148: lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 6 · grew 32 ·
  not selected 4 · judge changed: … and 10 more
RED: 32 metric(s) grew
446 passed, 3 skipped, 6 deselected
```

- Nothing fails. The run is red only for the 32 growths the landing notes explain. The six deselected are the slow checks, so `gained 6` here against the full run's 8 is expected.
- `ruff check` and `ruff format --check` are clean on `main` (`821723e`) with the whole change applied. The unit suite gives `293 passed, 6 skipped` there (no artifacts in that clone).

### Each finding

1. **Not resolved: the list of functions is incomplete.** EXECUTED (`probes/math.py`, the same 199 inputs natively under the pinned 3.15, SQLite 3.53.1, and in the guest, 3.54.1).
   - The README names `sin`, `cos`, `tan`, `atan`, `acos` and `log10`. These also differ: `asin` (7 of 199), `atan2` (14), `sinh` (38), `cosh` (33), `tanh` (1), `asinh` (2), `acosh` (1), `atanh` (42), and one-argument `log` (1), which is SQLite's `log10`.
   - These agree: `exp`, `ln`, `log2`, `log(b, x)`, `pow`, `sqrt`, `mod`, `pi`, `degrees`, `radians`, `ceil`, `floor`, `trunc`, and `printf('%.17g')`.
   - JSON's float text differs as stated (`0.33333333333333332` against `0.333333333333333`).
   - The CHANGELOG's "its trigonometric functions and `log10`" covers more, but not the hyperbolic ones by any usual reading.
   - **Fix.** In both files: "SQLite's trigonometric and hyperbolic functions (`sin` to `atanh`, and `atan2`) and `log10` (one-argument `log`) follow the C library". Or say "SQLite's transcendental math functions other than `exp`, `ln`, `log2` and `pow`".
2. **Not resolved: "only" is false.** EXECUTED (`probes/ro2.py`, the read-only preopen through the judge's runner).
   - Confirmed: plain `connect` and `mode=ro` fail with "access permission denied", and `immutable=1` reads.
   - But `file:/data/ro.db?nolock=1`, `?mode=ro&nolock=1` and `?vfs=unix-none` also read it. Only `vfs=unix-dotfile` fails like the default.
   - **Fix.** One word in the README and the CHANGELOG: "opens as `file:<path>?immutable=1` (or `nolock=1`) with `uri=True`".
3. **Confirmed.** EXECUTED: the sizes are 31,760,992, 65,506,914 and 11,140,578 bytes, which are 31.8, 65.5 and 11.1 MB. `build-v2.txt` gives `real 340.81`, which is 5 min 41 s. Its "Left over" bullet is stale; see N3.
4. **Confirmed as far as the unset reaches, but the absolute claim is still false** (new finding N1). EXECUTED and READ:
   - READ: nothing else in step 35, `common.sh` or `line.sh` uses `LIBS`. `OUT` is set in `common.sh` and used by steps 60, 70 and 80, not by step 35. `LIBDIR` is used only in step 35, and every use was renamed. Under `set -u`, a missed `$LIBS` would have stopped the step; the clean run did not stop.
   - EXECUTED (`run35.sh`): I ran step 35 alone in a copy of the tree layout (`confirm007/s35`, with the clone's `build/tools` and the three pinned tarballs linked in). Each run gives the clone's archives exactly (`liblzma.a` `ca6e4748…`, 213,672 bytes) under each of these: a clean environment; `CPPFLAGS=-fno-inline`, twice; `LIBS=-lnonexistent_xyz`; `CONFIG_SITE=/nonexistent/site LDFLAGS=-Wl,--bogus MAKEFLAGS=-k`. So the review's experiment no longer changes anything.
   - The rebuild claim holds: the full hashes in `before-v2.sha` equal the archives and binaries in `build/` now. `after-v2.sha` holds 16-digit prefixes, and they agree.
5. **Confirmed.** EXECUTED (`probes/stop.py`, a reused root with a write transaction open):
   - `os._exit(3)`, out of fuel and past the deadline each leave `k.db-journal` and `k.db.lock`.
   - A `MemoryError` loop under a 256 MiB limit leaves only `k.db`.
   - "Out of memory" is gone from the README, the CHANGELOG and the specification (READ, `grep`).
6. **Confirmed.** READ: the landing notes now credit the claim to this review's check.
7. **Confirmed.** EXECUTED (`lic.py`, the judge's own `licence_errors` on copies of `LICENSES/`):
   - The notices as built pass, with `xz` and `sqlite` in the content list.
   - Mutation 3 (`xz.txt` without the `COPYING.0BSD` text) now fails. So does mutation 5 (`sqlite.txt` reading "not a licence"). A blessing split across two lines fails too.
   - `licence_source("sqlite")` resolves to the pinned `sqlite-autoconf-3540100.tar.gz` through the MANIFEST's `package sqlite-autoconf 3540100` line.
   - **On CI with `downloads/` present** the inputs are the same pinned tarballs, and `LICENSES/` is built from them. I see no path to a false failure (INFERRED).
   - **Without `downloads/`** both fall back to presence only, as every component does (EXECUTED: mutation 5 passes then). That is the documented behaviour, not a false pass.
   - **If a later `sqlite3.h` lost the sentence,** the judge would fall back to presence only without saying so. But `sqlite_notice()` already stops the build in that case (READ, `assemble_artifacts.py:99`).
   - **Scope.** The check needs one sentence, not the whole blessing. A notice holding only "The author disclaims copyright to this source code." passes (EXECUTED). The disposition's "the blessing that heads the pinned `sqlite3.h`" says more than is checked. This is acceptable, but the comment could say "its first sentence".
   - **No unit test** covers `_more_licence` or the `sqlite` to `sqlite-autoconf` mapping. The only coverage is the artifact check, and it runs only where `downloads/` holds the tarballs. See N2.
8. **Not resolved: `main` has moved again.** EXECUTED: the main repository is at `821723e`, three commits past `1745ac1` (`f1db97f`, `7006bb6`, `821723e`). Those commits change `tests/harness/paths.py` (in other hunks), `tests/checks/test_v1_4_embedding.py`, `tests/unit/test_scoreboard.py` and `context/progress/accepted.json`.
   - `git apply --check` of `git diff 1745ac1 HEAD` on a fresh clone of `821723e` passes.
   - The landing must rebase onto `821723e`, or whatever `main` is then, and re-run the full judge there before the accept, as the disposition already says. Its ratchet will read against `f1db97f`'s accepted state.
9. **Confirmed.** EXECUTED:
   - The real `Modules/config.c` has `PyInit__bz2`, `PyInit__lzma` and `PyInit__sqlite3` (declarations at lines 18 to 20, `_inittab` entries at lines 98 to 100).
   - I ran CPython's own `makesetup` in a scratch directory, with the Makefile's argument list, on copies of the build's `Setup.local`, `Setup.stdlib` and `Setup.bootstrap`. The output equals the build's `config.c` apart from its first comment line, which names the source path.
   - With the review's mutation 12 (`-DPY_SQLITE_HAVE_SERIALIZE=1`), the regenerated `config.c` lacks `PyInit__sqlite3`, so the new loop would stop step 60.
   - READ: the loop runs after `make all`, whose `Makefile Modules/config.c:` rule regenerates `config.c` when `Setup.local` changes, and before the reactor link. The loop variable `m` is not used elsewhere in the step.

### New findings

- **N1. Step 35's comment and Decision 2 still say no environment variable changes the archives, and one still does.** Low. This is the same class as finding 4.
  - EXECUTED: `tuklib_cv_physmem_method=none` in the environment gives a different `liblzma.a` (`cb885f58…`, 213,584 bytes). Autoconf takes any exported `ac_cv_*` or `*_cv_*` cache variable as a test's answer.
  - The same-bytes gate would still catch a difference, and CI sets no such variable.
  - **Fix.** Reword it to "the flag and search-path variables autoconf, make and clang read are unset". Or run `configure` under `env -i`, passing only `PATH`, `CC`, `AR`, `RANLIB` and `CFLAGS`.
  - Either edit changes the recipe hash in `MANIFEST`, so steps 90 and the judge re-run, with no change to the binaries.
- **N2. The judge change in `paths.py` has no unit test.** Low.
  - `test_licences_are_checked_for_content_when_the_source_is_downloaded` tests the zlib case with a synthetic tarball. Nothing tests xz's second file, SQLite's sentence or the package mapping.
  - AGENTS.md rule 3 asks for the check with the behaviour, and the mutations above were ad hoc.
  - **I think one is needed, and it is small.** Use synthetic `xz-5.8.4.tar.gz` (with `COPYING` and `COPYING.0BSD`) and `sqlite-autoconf-3540100.tar.gz` (with `sqlite3.h`) in the monkeypatched `downloads/`. Assert:
    - that both pass when the notices hold the text;
    - that each fails without its second part;
    - that a `sqlite3.h` without the sentence gives presence only.
  - Or answer in writing why the artifact check is enough.
- **N3. The landing notes are stale after the fixes.** Low, process. READ, in the clone's specification:
  - The status line still says "awaiting its build review".
  - The table's `MANIFEST` (`e6a165cb…`) and `SHA256SUMS` (`b7473480…`) are pre-fix. They are now `c22c808e…` and `0bfb53c6…` (EXECUTED), because step 35's recipe hash changed.
  - The Linux line's "byte-identical `SHA256SUMS` (`b7473480…`)" was shown before the fix. The archives did not change, so it still holds for the binaries (INFERRED).
  - The judge block is the pre-fix run against `1f21dd021a`.
  - "Left over" still says the build review has not been done, and that the README's build time is 4 min 19 s.
  - These belong to the landing re-run (finding 8). The notes must carry that run's numbers and cite this review.

### Verdict

**Does not land yet.**

- **What holds.** The code, the build and the judge change are right:
  - findings 3, 5, 6, 7 and 9 are confirmed;
  - finding 4's scrub works;
  - the scoreboard has no failure.
- **What is left is text and the landing run.**
  - Two README and CHANGELOG sentences are still inaccurate: the function list (finding 1) and "only" (finding 2).
  - N1's comment, and N2's unit test or a written answer.
  - Then the rebase onto the current `main`, the full judge re-run there, refreshed landing notes (finding 8, N3), and the accept.
- None of this changes a binary. N1's edit changes `MANIFEST`'s recipe hash, so steps 90 and the judge re-run.

One line: the build and the checks are right; two user-facing sentences are still wrong, and the landing must re-run on the current `main`.

## Disposition of the confirmation (filled in by the author)

- Finding 1 — Fixed: the README says SQLite's math functions follow the guest's C library and names what differed over 199 inputs (the trigonometric and hyperbolic functions, `atan2`, `log10`, one-argument `log`) and what did not (`exp`, `ln`, `sqrt`); the CHANGELOG matches.
- Finding 2 — Fixed: "opens only through a URI that takes no lock, such as `immutable=1` or `nolock=1`"; `mode=ro` alone is not enough.
- Finding 8 — To do at landing: rebase onto `main` after the 0.1.0a2 tag, re-run the full judge there, and give that run's numbers.
- N1 — Fixed: xz's `configure` and `make` run under `env -i` with only `PATH` and `LC_ALL`, through a shell function (this host's `PATH` holds a space). EXECUTED: steps 35–90 with `tuklib_cv_physmem_method=none` and `CPPFLAGS=-fno-inline` exported gave byte-identical archives. The same `CPPFLAGS` did change the reactor through step 60's CPython `make`, an exposure that predates this spec (your finding 4's note); it is recorded in the landing notes' "Left over". A clean rebuild of 60–90 restored the reference hashes.
- N2 — Fixed: `test_xz_and_sqlite_notices_must_hold_their_whole_licence` in `tests/unit/test_artifact_rules.py`, with synthetic tarballs; it fails with `_more_licence` disabled (EXECUTED) and passes with it.
- N3 — To do at landing, with finding 8: the landing notes are rewritten from the rebased run (hashes, judge block, status, "Left over").

## Second confirmation

- **Who.** The same agent who wrote the confirmation above. I did not write the change.
- **What I read.** The author's "Disposition of the confirmation", and the three commits `11085c7..HEAD` in the clone: `5b4e512`, `45b4c67` and `8da8864`. The clone is at `8da8864`, on `11085c7` (Release 0.1.0a2), which is the main repository's `HEAD` (EXECUTED).
- **Left as found (EXECUTED).** `git status`, `HEAD` and the SHA-256 of every file under `build/artifacts` and `build/stdlib-libs/lib` equal my snapshot taken first. My experiments ran in copies under `…/scratchpad/confirm007/` (`s35/`, `c2/`). This section is my only edit.

### The full judge (EXECUTED)

`uv run pytest -p no:cacheprovider` in the clone, no `--accept`, exit 1:

```
wasi_python v1: 151/154 pass · 0 gap · 3 blocked · 0 fail   (unit suite 303/303)
  v1.1 24/25 blocked 1 · v1.2 30/31 blocked 1 · v1.3 15/15 · v1.4 48/48 · v1.5 18/18 · rules 16/17 blocked 1
ratchet vs f1db97f37c: lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 8 · grew 32 ·
  judge changed: … and 10 more
RED: 32 metric(s) grew
454 passed, 3 skipped
```

This is the landing notes' new block, line for line. It includes `test_manifest_recipes_match_the_tree`, so the built `MANIFEST` matches the edited recipes. `release/version.py check` gives `ok 0.1.0a3`.

### Each item

- **Finding 1: confirmed.** READ and EXECUTED.
  - The README now says the math functions follow the guest's C library.
  - It says which ones differed over 199 inputs: the trigonometric and hyperbolic functions, `atan2`, `log10` and one-argument `log`. It says `exp`, `ln` and `sqrt` did not.
  - That matches my comparison (`probes/math.cmp.txt`). The 0.1.0a3 CHANGELOG bullet matches too.
- **Finding 2: confirmed.** READ, against my earlier run (`ro2.out`).
  - The README now says "only through a URI that takes no lock, such as `immutable=1` or `nolock=1`", and "`mode=ro` alone is not enough". That is true: `nolock=1`, `mode=ro&nolock=1`, `vfs=unix-none` and `immutable=1` read the database, and `mode=ro` does not.
  - The CHANGELOG gives `immutable=1` as the example.
- **Finding 8: confirmed.** EXECUTED: the change sits on `11085c7`, the current `main`, and the full judge above is the run on that base.
  - The 007 bullets moved out of the released 0.1.0a2 section into a new "0.1.0a3 — unreleased" section, and `__version__` is `0.1.0a3`. That is what `version.py bump` writes (READ, `_bump`).
  - `main` must not move again before the accept, or the run must be repeated.
- **N1: not resolved.** The step 35 comment's claim is still false, now through clang instead of autoconf.
  - EXECUTED: I ran the new step 35 alone in `confirm007/s35`.
    - A clean environment gives the clone's three archives.
    - `tuklib_cv_physmem_method=none` and `CPPFLAGS=-fno-inline` now change nothing. So the `env -i` around xz works.
    - But `CCC_OVERRIDE_OPTIONS=+-fno-inline` changes `libbz2.a` (`46a1c9e4…`) and `libsqlite3.a` (`5cb1cff9…`). It does not change `liblzma.a`, which `env -i` shields.
  - The cause: the bzip2 and SQLite compiles run `$CC` directly, in the step's own environment. Clang reads `CCC_OVERRIDE_OPTIONS` (and others the `unset` line does not list) from there.
  - So "no environment variable changes the archives" is still an overclaim. The risk is the same as before: CI sets no such variable, and the same-bytes gate would catch a difference.
  - **Fix.** Run the bzip2 and SQLite compiles through the same `clean` function, then drop the `unset` line, or keep it. Or reword the sentence to say what is sealed: "xz's configure and make run in an empty environment; the direct compiles unset the include and library search variables".
  - Either edit changes the recipe hash in `MANIFEST`, so step 90 and the full judge re-run. The binaries should not change (INFERRED from the clean run above).
- **N2: confirmed.** EXECUTED, in a scratch clone of the clone (`c2/`).
  - `test_xz_and_sqlite_notices_must_hold_their_whole_licence` passes.
  - It fails under each of three mutations of `paths.py`: the `sqlite` to `sqlite-autoconf` mapping removed, `_more_licence` disabled, and xz handled like SQLite.
  - It does not test a `sqlite3.h` without the sentence. That case falls back to presence only, and the build already guards it, so the test is enough.
- **N3: confirmed, with two small wording slips.** READ and EXECUTED.
  - These match the current set: the status line, the `MANIFEST` and `SHA256SUMS` hashes (`6038693f…`, `46d855b7…`), the binary hashes, the judge block, "Left over", and the Linux line, now marked as the pre-review build.
  - **Slip 1.** "After the build review" cites "findings 1 and C1" and "finding 2 and C2". The confirmation named its findings N1 to N3.
  - **Slip 2.** "Left over" says the reactor change under `CPPFLAGS` was "EXECUTED in the review's confirmation". The author ran that experiment; the confirmation did not.
  - Fix both when the notes are next touched. They do not block.

### Verdict

**Does not land yet.**

- **What holds.** Findings 1, 2 and 8 and N2 and N3 are confirmed. The full judge has no failure, and it matches the landing notes.
- **What is left.** N1 only: step 35's comment still says no environment variable changes the archives, and `CCC_OVERRIDE_OPTIONS` does, for `libbz2.a` and `libsqlite3.a`.
- **How it lands.** A one-line fix (`clean` around the two direct compiles, or a narrower sentence). Then step 90, the full judge on the current `main`, the landing numbers updated, and the accept. No other review round is needed if the fixed step 35 gives the same three archives, the same binaries, and a judge run with nothing lost and nothing failing.

One line: everything is confirmed except one sentence in step 35, which is still false for the bzip2 and SQLite compiles; seal them or narrow the sentence, re-run, and it lands.

## Disposition of the second confirmation (filled in by the author)

- N1 — Fixed: every tool in step 35 (clang, llvm-ar, xz's `configure` and `make`) runs through `clean`, an `env -i` with only `PATH` and `LC_ALL`; the `unset` line is gone. EXECUTED: step 35 with `CCC_OVERRIDE_OPTIONS=+-fno-inline`, `CPPFLAGS=-fno-inline` and `tuklib_cv_physmem_method=none` exported gave the reference archives (`9c1c0be0…`, `ca6e4748…`, `8a95c95f…`), and steps 60 to 90 the reference reactor, snapshot and zip; only `MANIFEST` (`f1a15067…`) and `SHA256SUMS` (`69eb0fb5…`) changed, by the recipe hash. The landing's judge run loses nothing and fails nothing (below), the condition the second confirmation set for landing without another round.
- The two wording slips in the landing notes (C1/C2, and who ran the reactor experiment) are fixed.
