# 166: The pins move for 0.1.3

- **Status:** the first pull request (CPython 3.15.2, the build's wasmtime 50.0.1, numpy 2.5.4, the bug-fix sweep) built 2026-10-31 on `spec/166-the-pins-move-for-0-1-3`, not landed; the second (pandas 3.1.0) not built. zlib 1.3.2 waits for the owner (its licence file changed; the landing notes). Drafted 2026-10-30, to be reviewed before it is built (the build recipe: constitution §5.6). The owner chose it on 2026-10-30 (decisions.md, "The scope of 0.1.3"). Amended 2026-10-30 against its pre-build review, `../reviews/166-the-pins-move-for-0-1-3-spec-2026-10-30.md` ("Fit to build after amendments"): every finding taken; the review's Disposition says where.
- **Date:** 2026-10-30
- **Owner:** Clay Gendron
- **Kind:** **build-class**, **a judge change**, not structural: nothing under `src/` changes. Recipe: `line.conf`, `00_download.sh`, `SHA256SUMS`, steps 10, 40, 50 and 70, `assemble_artifacts.py`, the moved pins' patches and rename headers. Judge: one rules row, `paths.wasmtime_cli()`, the oracle, the goldens, `tests/upstream/`. Documents: `SECURITY.md`, two reference pages.
- **Depends on:** landed: 020, 127 (the runner on wasmtime-py 50.0.1; its Decision 6 left the CLI to a build-class specification), 136, 158; 159 (the build on arm64 Linux, two rebuilds voting), landing before this is built. Siblings: 165 builds after 166's first pull request lands; 167's pandas patch lands after 166's second, on its pandas folder; both merge only after Decision 12's x86-64 vote. 162, 163, 164 and 168 touch `src/` only.
- **Research it stands on:** `../research/2026-10-30-what-0-1-3-could-carry.md`, item H (line 55); `../decisions.md` line 530 and decision 64 (the wheel's 100 MB line); `../roadmap.md` line 91; 127's Decisions 6 and 7; 086. Read once each on 2026-10-30: sqlite.org (3.54.1 is the newest), PyPI (numpy 2.5.4 and pandas 3.1.0 are the latest), wasmtime v50.0.1 (2026-10-29), python-build-standalone 20261026 (carries 3.15.2).

Labels: EXECUTED means run and seen; READ means read from a file, cited; INFERRED means reasoned.

## The problem

The owner chose CPython 3.15.2, SQLite 3.54.1, the build's wasmtime 50.0.1 (from 49.0.3), numpy 2.5.4, pandas 3.1.0, and the bug-fix releases that exist at build time. SQLite 3.54.1 has been pinned since spec 007 (READ). The build's wasmtime runs `wasmtime wizer` (`80_snapshot.sh`) on another line than the runner's 50. pandas 3.1.0 needs C++20 and is eight days old.

## Decisions

### 1. One specification, two pull requests

The first moves CPython, the CLI, numpy and the sweep; the second, stacked or after it, pandas, so a C++20 failure holds back pandas alone. Each moves the set's key and carries the label `ci:full`.

### 2. The order on the first branch, one commit each

1. The rows of Decision 9.
2. CPython 3.15.2: `PYTHON_VERSION`, the tarball, the three host Pythons (`10_tools.sh` line 214 ties them to the line), the oracle's `requires-python` and lock.
3. The CLI: the three `*_WASMTIME_DIR` names and archives.
4. numpy 2.5.4: the tarball and `40_numpy.sh` lines 2, 11 and 12; the three `NUMPY_HOST_WHEEL`s; the f2py check (`10_tools.sh` lines 227 and 230); `PACKAGES`, the source path and `70_zip.sh` line 146; `recipes/npy_rename.h` if a new duplicate symbol appears; the oracle; the patches.
5. The sweep, one commit per pin.

CPython goes first: every package is built by its cross Python.

### 3. SQLite holds at 3.54.1

No line changes. `35_stdlib_libs.sh` line 63 follows python-build-standalone's `PRAGMA compile_options`; the builder reads them again in the new host Python and records any difference.

### 4. The CLI is the runner's line, and a row holds it

The CLI moves to the newest 50.x, 50.0.1 today. The judge compares fuel within one major (spec 002, Decision 6), so one major is "one version". A new row, `tests/checks/test_rules.py::test_the_builds_wasmtime_is_the_runners_line`, reads each host's `WASMTIME_DIR` in `line.conf` and `_wasmtime_ffi.PIN`, and fails when the majors differ.

The runner's engine does not move, so 154's engine rule does not apply. The builder snapshots the branch's `python.wasm` with both CLIs and records both files' SHA-256 and `scripts/compare_snapshots.py`'s output, which reads initial memory only. A wizer flag renamed in 50 is an edit to `80_snapshot.sh`. A failure of `test_recursion_raises_under_the_wasmtime_cli` is a finding, not a judge edit.

`wasmtime_cli()`, which takes the first sorted `wasmtime-v*`, reads the host's `WASMTIME_DIR` by exact name instead.

### 5. Each new pin is hashed once and checked against its publisher

Each new file is fetched once; its SHA-256 is checked against PyPI's digests, python.org's page, python-build-standalone's `SHA256SUMS` or the GitHub asset digest, in a table in the landing notes.

### 6. Every carried patch of a moved pin is re-made, not changed

A patch applies at no offset, so every moved pin's patches are re-made against its tarball: numpy's two, pandas' one, any swept tree's. Folders take the new top's name; drafts move with `Against` updated; `MODIFIED`'s keys (`assemble_artifacts.py` line 379) move with regex's; OpenBLAS's three are regenerated by their script and compared. A re-made patch's changed lines equal the old one's (shown in the landing notes). A change that must differ is reviewed as a new patch; one upstream made unneeded is deleted with its draft. The two documented examples name numpy's new folder.

### 7. The sweep takes bug-fix releases of what ships

In: every pin compiled into `python.wasm` or shipped in the zip that has a release with the same major and minor and a higher patch on the day the branch is made; tzdata takes its newest. A swept pin's test source moves with it, and its `.ini` transcription is read again.

Out: the build's own tools (wasi-sdk, meson, Cython, ninja, pkgconf and the rest) unless a moved package requires one; openpyxl and et-xmlfile, whose test archives need the owner's mirror upload (spec 158).

The landing notes list the candidates first, marking those with patches. Any moved pin whose licence files change waits for the owner (§4.12), numpy and pandas included. A swept pin that fails its suite in a new way twice goes back, named.

### 8. pandas 3.1.0 builds with its own C++20 (A decided; B the owner's alternative)

The second pull request moves `50_pandas.sh`, the tarball, `PACKAGES`, the source path, `70_zip.sh` line 147, the oracle and the patch. C++20 comes from pandas' `meson.build`; `scripts/wasi-cxx` forces no standard (READ); wasi-sdk 34 compiles C++20 (INFERRED). A missing header or a new duplicate symbol gets a recipe file first (`wasi-pandas.cross`, `pandas_rename.h`; §4.1). If pandas 3.1.0 fails to build, or loses passes it should keep, after two attempts on one cause: **A**, 0.1.3 ships pandas' newest 3.0.x and 3.1 moves in 0.1.4. **B**, the owner's alternative, holds 0.1.3 for pandas 3.1. The builder asks with AskUserQuestion, A first.

### 9. The rows first

- `test_the_builds_wasmtime_is_the_runners_line`: red on `dev`'s tip, 49 against 50.
- A unit row in `tests/unit/test_build_scripts.py`: `wasmtime_cli()` given the line's name, `wasmtime-v50.0.1-…`, over a folder holding both versions returns 50.0.1; red on `dev`'s tip.
- `test_the_guests_configure_results_are_recorded` builds its path from `PYTHON_VERSION`, not the literal `Python-3.15.0` (`test_v1_5_rebuild_from_pins.py` line 568). It is seen failing after commit 2 with the literal kept, then fixed.

### 10. What the judge's files may change

Each is a judge change with its reason in the claim, never a way to a green run.

- **Goldens** are remade by `tests/jobs/regen.py`, each diff and cause in the landing notes; a guest that stops matching the oracle is a failure.
- **`expected/` lists and CPython's plan (`tests/upstream/python/`)**, three kinds of edit only. A node upstream renamed, removed or fixed leaves its list. A new failing node joins a class only when the pattern matches and the traceback shows the class's cause. A new kind of failure is a new class with its closer.
- **Pass counts** fall only because upstream deleted or moved tests; `fewer` gives the counts. A test that passed, still exists and now fails is a finding to fix.
- **`.ini` files** are transcribed again, the diff in the landing notes. A **fuel cap** rises only when a measured fuel exceeds it, keeping the group's former headroom, with the run named. **`tests/cpython_configure.txt`** changes only by a result 3.15.2 flips, named.

Before the review the builder runs locally the release groups of numpy, pandas, CPython and every swept pin. The release groups that depend on numpy (scipy, scikit-learn, statsmodels, matplotlib, contourpy) are read at Decision 12's weekly run. Their claims go to the release ledger (`context/release-claims.toml` once 161 lands).

### 11. Bytes and fuel are bounded, then claimed

Linux fuel is never compared (154) and the upstream groups run on Linux alone, so own checks' fuel comes from the gather's darwin comparison, and the upstream groups' fuel (numpy, pandas, CPython, both tiers) is measured locally on darwin at `dev`'s set and the head's, labelled with its platform.

The landing notes hold 086's table: bytes per artifact and the wheel; fuel rows up and down, median, minimum, maximum, sum. Above these bounds the cause is traced before the claim. First pull request: each artifact at most +1%, the normal tier's fuel sum at most +1%, no own check over +5%. Second: `python.wasm` and the zip at most +3%, each pandas group's fuel at most +15%. The bounds are INFERRED from 086's +0.164%. The wheel (0.1.2: 1.64% under 100,000,000 bytes) is read against 100,000,000 and PyPI's 104,857,600; crossing the first asks the owner before the merge (decision 64), joined with 167's PyPI request.

### 12. Same bytes before the siblings build

`ci_plan.py`'s `decide()` runs no rebuild on a pull request, so at each pull request's final head the builder builds on macOS arm64, compares `SHA256SUMS` with the run's arm64 Linux set, and runs the build shard (`uv run pytest --shard build`), recording its pass line and the configure diff. That vote is two aarch64 hosts. The x86-64 vote is the first weekly run after 166's last merge; 165 and 167 merge only once its `same-bytes` is green, or the owner, asked with AskUserQuestion, dispatches one.

### 13. The documents and the release notes

`SECURITY.md` line 24 says the build's wasmtime is 50.0.1, the runner's line, and only makes the snapshot; its `x-wizer` clause goes (the pin lines name the CLI). Two reference pages name the new versions. The news file, `../changes/166-the-pins-move-for-0-1-3.md`:

- `### Security`, only if 3.15.1's or 3.15.2's changelog fixes a module the zip carries: the issue and its link.
- `### Upgrading`: **CPython 3.15.2 and numpy 2.5.4 inside.** Bug-fix releases, from 3.15.0 and 2.5.2. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)
- `### Upgrading`: **pandas 3.1.0 inside.** A new minor release, from 3.0.6; read pandas' 3.1.0 notes for code that relies on what it changed. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)
- `### Upgrading`: **Saved snapshots are made again.** The binary and the zip change, so a `Snapshot` saved with 0.1.2 raises `SnapshotMismatch`. Make it again after you upgrade. [Snapshots](https://claygendron.github.io/wasi-python/how-to/snapshots/)
- `### For contributors`: **The build's wasmtime is the runner's line.** The snapshot is made by wasmtime 50.0.1, not 49.0.3. [Building](https://claygendron.github.io/wasi-python/contributing/building/)
- `### For contributors`, one entry per pull request: **The carried patches follow their pins.** Each re-made patch by its full path, such as `recipes/patches/numpy-2.5.4/0001-npy-files-without-dup.patch`, split if past sixty words. [Carrying a patch](https://claygendron.github.io/wasi-python/contributing/carrying-a-patch/)

Package rows: numpy `2.5.4`, pandas `3.1.0`, "what works" unchanged.

## Intent

One pinned set, one wasmtime line for build and runner, every change measured and given its reason.

## Design

The files are in Kind and the Decisions. No guest import or export changes.

## Scope

In: Decisions 1 to 13. Out: wasmtime 51 (127's shape, its own specification); the build tools; the two mirrored pins; new packages.

## Acceptance criteria

1. Decision 9's rows are seen failing as it says, then pass (EXECUTED).
2. Every moved pin matches its publisher's hash (READ); the build shard passes locally at each final head (EXECUTED).
3. Each patch applies at no offset; its changed lines equal the old ones or its draft says why (READ).
4. `python.wasm -V` names 3.15.2; `test_numpy_and_pandas_are_builtin_at_manifest_versions` passes at 2.5.4 and 3.1.0 (EXECUTED).
5. The two-CLI comparison is recorded (EXECUTED).
6. Every golden diff and `tests/upstream/**` edit is one of Decision 10's kinds, with its reason (READ).
7. The local release groups are green, their claims in the ledger (EXECUTED).
8. Decision 11's table is within bounds or each cause traced (EXECUTED).
9. The macOS and arm64 Linux sets agree at each final head (EXECUTED); the weekly x86-64 vote is recorded before 165 and 167 merge.
10. The news file passes `test_the_news_files_have_their_shape` and `test_carried_patches_follow_the_rules`; each pull request's `ci-status` is green and its review says "Lands".

## Landing notes

### The first pull request: CPython 3.15.2, the CLI, numpy 2.5.4 and the sweep (built 2026-10-31)

Built on `spec/166-the-pins-move-for-0-1-3` from `dev` at `a1acec5c`, by a builder sub-agent of the orchestrating session. Every figure is EXECUTED on an arm64 Mac (Darwin 25.5.0) unless it says otherwise. "dev's set" is the set `../progress/accepted.json` records (`python.wasm` `d4192605…`, 0.1.2's), measured from an export of `a1acec5c` with that set and its own source trees, so the guest and its tests are dev's on both sides.

**Decision 9's rows, each seen failing first.**
- `tests/checks/test_rules.py::test_the_builds_wasmtime_is_the_runners_line`: red on `dev`'s tip, three findings (each host's `WASMTIME_DIR` major 49, the runner's 50); green from the CLI commit.
- `tests/unit/test_build_scripts.py::test_the_wasmtime_cli_is_the_lines_by_its_exact_name`: red on `dev`'s tip (`wasmtime_cli()` took no name); green once `paths.wasmtime_cli()` takes the host's `WASMTIME_DIR` by its exact name (`paths.build_line()` reads `line.conf` through `line.py`).
- `test_the_guests_configure_results_are_recorded`, with the literal kept, on the 3.15.2 tree: `no build/Python-3.15.0/cross-build/wasm32-wasip1/pyconfig.h`. Built from `PYTHON_VERSION`, it found one new result, `+_Py_HAVE_STRERROR_R 1`: 3.15.2's configure adds the private check `PY_CHECK_FUNC_PRIVATE(strerror_r)` (with `_Py_HAVE_PTHREAD_ATTR_GET_NP` and `HAVE_PTHREAD_NP_H`, which wasi-libc does not define). `tests/cpython_configure.txt` takes the line and the digest `155442b1…`; nothing else flips.

**Decision 5: each new pin against its publisher.** Fetched once each into `downloads/` (the Linux hosts' inputs not fetched here; CI fetches and verifies them):

| file | SHA-256 | the publisher's record |
|---|---|---|
| `Python-3.15.2.tar.xz` | `8b5536d2…575797de` | python.org's 3.15.2 page |
| `cpython-3.15.2+20261026-{aarch64-apple-darwin,aarch64-unknown-linux-gnu,x86_64-unknown-linux-gnu}-install_only.tar.gz` | `285a6b92…758e64a6`, `6fc73e8a…ee318616`, `08d4ae90…dd4092aa` | python-build-standalone 20261026's `SHA256SUMS` |
| `wasmtime-v50.0.1-{aarch64-macos,aarch64-linux,x86_64-linux}.tar.xz` | `960e5216…b30c65c8`, `d737e077…50cf4094`, `68546645…a75498a5` | each GitHub release asset's `digest` (v50.0.1, 2026-10-29) |
| `numpy-2.5.4.tar.gz`; its cp315 wheels for macOS 14 arm64, manylinux aarch64 and x86_64 | `9a94cf75…c7999d2a`; `0b4724a1…d44de2a5`, `325518d4…08db1266`, `56733449…fdd0e86d` | PyPI |
| `pypdf-6.21.4-py3-none-any.whl`, `pypdf-6.21.4.tar.gz` | `33e4fb41…a666255c`, `c8817e3f…f0bc2163` | PyPI |
| `soupsieve-3.0.4-py3-none-any.whl`, `soupsieve-3.0.4.tar.gz` | `84128266…9fe7afbf`, `924fab84…5e5bc4c0` | PyPI |
| `wrapt-2.5.2-py3-none-any.whl`, `wrapt-2.5.2.tar.gz` | `61eb54e9…7aaf90f0`, `551cb49e…9d9fddbf` | PyPI |
| `tzdata-2026.6-py2.py3-none-any.whl`, `tzdata-2026.6.tar.gz` | `0a10eec6…a70b4aec`, `85d2cd9c…4feece6d` | PyPI |
| `pypdf-6.21.4-sample-files-tag.tar.gz` | `01563c62…331a627d`, 6.21.1's bytes | the 6.21.4 tag's `sample-files` submodule is `818dc013`, 6.21.1's (GitHub's contents API at both tags) |

**Decision 7: the sweep's candidates**, read 2026-10-30 from PyPI's JSON (once a package), the projects' git tags and the GNOME and Savannah listings. A pin with a carried patch is marked (patch).
- Moved: numpy 2.5.2 → 2.5.4 (patch); pypdf 6.21.1 → 6.21.4 (patch, a test-source patch); soupsieve 3.0.3 → 3.0.4; wrapt 2.5.1 → 2.5.2 (2026-10-29); tzdata 2026.5 → 2026.6 (its newest).
- **Held for the owner: zlib 1.3.1 → 1.3.2** (2026-02-17; "check for negative lengths in crc32_combine", "prevent the use of insecure functions"). Its `LICENSE` changes, the copyright line from `1995-2022` to `1995-2026`, and it adds `contrib/minizip/LICENSE.Info-Zip` (minizip is not built), so by Decision 7 it waits for the owner (§4.12).
- No release past the pin in the same minor: every other pure package in the zip (pandas' 3.1.0 is the second pull request; openpyxl and et-xmlfile are out by Decision 7 and have nothing newer), regex (2026.9.29 is the newest), scipy 1.18.1, scikit-learn 1.9.1, statsmodels 0.15.0, matplotlib 3.11.2, Pillow 13.0.0, kiwisolver 1.5.1, contourpy 1.4.0, lxml 6.1.3 (patch), pybind11, cppy; bzip2 1.0.8, xz 5.8.4, libxml2 2.15.4 (patch), libxslt 1.1.45, OpenBLAS 0.3.34 (patches), FreeType 2.14.3, HarfBuzz 14.1.0, SheenBidi 3.0.0, libraqm 0.10.5, qhull 8.0.2 (patch). SQLite holds at 3.54.1 (Decision 3). Newer minors that stay out: fonttools 4.68.0, xlsxwriter 3.3.1, mpmath 1.4.1, narwhals 2.28.0, reportlab 5.1.0, python-dateutil 3.0.0, libraqm 0.11.0, HarfBuzz 14.5 and 15.
- **Licence files** (§4.12): numpy 2.5.4's `license-files` and every licence-like file of its sdist are 2.5.2's byte for byte; pypdf's, soupsieve's, wrapt's and tzdata's wheels' licences are their old ones'. CPython's `LICENSE` and HACL*'s header are 3.15.0's; its `Doc/license.rst` changes one line, mimalloc's notice from `Copyright (c) 2018-2021 Microsoft Corporation, Daan Leijen` to `2018-2025`, because 3.15.2 vendors mimalloc 2.5 (from 2.1.2). The licence is MIT as before, and the owner chose 3.15.2 by name (decisions.md, "The scope of 0.1.3"), so CPython moves and the line is named here for the owner to read.

**Decision 6: the carried patches, re-made.** Each was re-made by applying the old patch to a scratch git tree of the new tarball and writing `git diff`; the method, run against the old tarballs, reproduces numpy's two patches byte for byte.
- `recipes/patches/numpy-2.5.4/0001-npy-files-without-dup.patch` and `0002-callback-signatures.patch`: the changed lines (every `+` and `-` line) equal 2.5.2's; the hunk headers are unchanged; only the `index` lines differ (the files' blobs moved). Both apply at no offset.
- `recipes/patches/pypdf-6.21.4/0001-tests-import-ssl-where-it-is-used.patch`: `tests/__init__.py` is the same file in both sdists, so the patch is 6.21.1's bytes (it was written without `index` lines or function context, and kept in its own form).
- The drafts moved with them, `Against` updated; `docs/contributing/carrying-a-patch.md` and `recipes/patches/README.md` name numpy's new folder. No `MODIFIED` key moves (regex did not move).

**Decision 3: SQLite.** python-build-standalone 3.15.2's `PRAGMA compile_options` (SQLite 3.53.1 in the host) equal 3.15.0's but for `COMPILER=clang-23.1.3` (was 22.1.3); step 35's options stand.

**Decision 4: the CLI.** `wasmtime wizer --help` is the same text in 49.0.3 and 50.0.1, so step 80's flags stand. The branch's `python.wasm` snapshotted with each CLI: 49.0.3 and 50.0.1 both write `ed740363c44cda6d497e7cfbb68864eaf267d106c5be8f728c962ce56dcd6036`, 104,576,267 bytes; `scripts/compare_snapshots.py`: `0 differing bytes in 0 symbols`. `test_recursion_raises_under_the_wasmtime_cli` passes under 50.0.1 (the build shard).

**What else the moved pins asked.**
- mimalloc 2.5's constructors: `mi_process_attach`, `constructor(101)`, takes the place of `_mi_process_init` and does what its `mi_process_load` did but the `atexit`; wasm-ld's `.Lregister_call_dtors.101` registers the `destructor(101)` `mi_process_detach` with `atexit`, which calls `mi_process_done` at exit as before. Both read and listed in `tests/harness/constructors.py` in link order; neither calls Python.
- numpy 2.5.4 checks the input of LAPACK's SVD and least-squares drivers for inf and nan (numpy issue 32591), so `np.linalg.cond` of a nan matrix returns nan and DLASCL's two xerbla lines are gone. Native numpy 2.5.4 on OpenBLAS (the oracle's `macosx_11_0_arm64` wheel) prints exactly the guest's answers; `test_numpy_linalg_errors_are_native_numpy_on_openblas` records them. Its LAPACK declarations are unchanged, so `recipes/numpy_lapack_shims.c` stands, and the rank-deficient string native 2.5.4 prints is 2.5.2's.
- Unit rows followed the pins: the download step's test tree takes the line's CPython tarball by name; CPython's staged test files' digest and group JSON digest in `tests/fixtures/upstream-stages.json` are 3.15.2's and its plan's (its `Lib/test` drops `test_cppext` and `memory_watchdog.py` and adds modules), every other family's unchanged; `test_regrtest.py` counts the plan's 546 normal modules (543, four in, one out).

**Decision 10: the judge's files.**
- Goldens, remade by `tests/jobs/regen.py` under the oracle at 3.15.2 (relocked with CI's uv, 0.9.22): fourteen change, each in its first line alone, the versions it names. No job's output moves.
- `.ini` files: numpy's, pypdf's, soupsieve's, wrapt's and tzdata's pytest configuration is unchanged upstream (wrapt's `tox.ini` drops a PyPy environment; pypdf's `pyproject.toml` changes ruff and mypy settings only); `numpy.ini`'s first comment names 2.5.4.
- CPython's plan: `test_cppext` (removed upstream) leaves `cpython-b.txt`; 3.15.2's four new `test_free_threading` modules join their siblings in `cpython-a.txt`, sorted, since regrtest lists every module and the plan places each. This is a placement the plan's own rule requires, beside Decision 10's three kinds of edit.
- `expected/cpython-a/no-test-modules.txt`: three new tests of 3.15.2's `test_traceback` (`CPythonSuggestionFormattingTests.test_name_error_with_bad_getattr`, `_getattribute`, `_property`) fail on the missing `_testcapi`, the class's cause and pattern; its gap counts 143 findings.
- Fuel caps: soupsieve-smoke ran out of fuel under 35 G at `test_escape_round_trip`. soupsieve 3.0.4's `test_api.py` adds tests that compile a selector for each of about 63,000 code points. Measured with the cap lifted (this Mac, the head's set): 164.8 G. The cap keeps the group's headroom (35 / 23.16 = 1.511): 250 G; the family's budget is the sum, 298 G.
- `tests/cpython_configure.txt`: the one line above. No pass count falls.

**Decision 11: bytes and fuel.** Bytes against dev's set; fuel on darwin arm64, numpy's, pandas' and CPython's groups at dev's set and the head's, the swept pins' against `accepted.json`'s darwin rows.

| | dev's set | the head | change |
|---|---|---|---|
| `python.wasm` | 99,421,513 | 99,487,062 | +65,549 (+0.066%) |
| `python-snapshot.wasm` | 104,517,748 | 104,576,267 | +58,519 (+0.056%) |
| `python-stdlib.zip` | 53,915,154 | 53,829,197 | −85,957 (−0.159%) |
| the wheel, built by hand from each set | 98,371,695 | 98,327,639 | −44,056 (−0.045%); 1,672,361 under 100,000,000 and 6,529,961 under 104,857,600 |

| groups (darwin) | rows | up / down | median | range | sum |
|---|---|---|---|---|---|
| numpy, pandas, CPython, normal tier | 16 | 14 / 2 | +0.157% | −0.525% (cpython-archives) to +3.197% (cpython-a) | 2,906.2 G → 2,920.96 G, +0.507% |
| numpy, pandas, CPython, release tier | 18 | 16 / 2 | +0.134% | −0.130% to +1.108% (cpython-release-b-inline) | 4,372.4 G → 4,381.1 G, +0.199% |

Every pass count holds or grows: cpython-a 5,865 → 5,898 (and runs the four new modules), numpy-core 9,519 → 9,752, numpy-lib 4,825 → 4,835, numpy-others 7,277 → 7,295; every pandas group equal. The swept: pypdf-smoke +0.31% (217 → 218 passes), pypdf-r −2.42% (1,474 → 1,695), soupsieve-smoke 23.1 G → 164.8 G (88 → 93), soupsieve-r +17.7%, 36.9 G under its 48 G cap (322 → 342), wrapt-smoke +0.79% (1,367 → 1,379), tzdata-smoke +0.20% (628 both).

Against the bounds: each artifact within ±1%; the wheel smaller. The fuel bound of the normal tier's sum (+1%) is crossed by soupsieve-smoke's +141.7 G alone, traced above to soupsieve 3.0.4's new tests; without it the upstream groups measured are +0.507%. The own checks' fuel is the pull request's gather's darwin comparison (`ci:full`). cpython-a's +3.2% is its larger plan (four new modules, 33 more passing tests) and numpy-core's +1.57% its 233 more passing tests.

**The set at this head.** A clean rebuild from step 10 wrote the same `SHA256SUMS` as the incremental build, `784b119d2a67f85d4c1d4a16f4dc1c67a93799632440c46658ddafba4b082e26` (its digest): `python.wasm` `9ef1a190…`, the snapshot `ed740363…`, the zip `c23e82e1…`. Decision 12's comparison with the pull request's arm64 Linux set follows below once its run has built.

**The local runs at this head.** `ruff check` and `ruff format --check` on `src tests release`: clean. `uv run pytest -m "not slow" -n 3 tests/unit tests/lint tests/checks/test_rules.py`: green after the unit rows above (3,562 passed, one rules row blocked by the prior-art clones, as on `dev`). `uv run pytest tests/lint`: 14 passed. `uv run pytest --shard=build`: 52 passed (41 checks, 11 unit), the configure row and the CLI recursion row among them. The data stack, artifact-set, matplotlib, scipy, regex and lxml check files: green after the linalg row. The upstream groups of numpy, pandas, CPython (both tiers), pypdf, soupsieve, wrapt and tzdata: green, the gaps as recorded.
