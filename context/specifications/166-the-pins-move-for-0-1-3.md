# 166: The pins move for 0.1.3

- **Status:** the first pull request (CPython 3.15.2, the build's wasmtime 50.0.1, numpy 2.5.4, the bug-fix sweep) built 2026-10-31 on `spec/166-the-pins-move-for-0-1-3` (pull request 67; its first run, 41170628147, red on four legs, fixed in one commit), not landed; the second (pandas 3.1.0) built 2026-10-31 on `spec/166-pandas-3-1-0`, stacked on the first, not landed; its new licence notices and four release groups that lose passes wait for the owner (its landing notes). zlib 1.3.2 waits for the owner (its licence file changed; the landing notes). Drafted 2026-10-30, to be reviewed before it is built (the build recipe: constitution §5.6). The owner chose it on 2026-10-30 (decisions.md, "The scope of 0.1.3"). Amended 2026-10-30 against its pre-build review, `../reviews/166-the-pins-move-for-0-1-3-spec-2026-10-30.md` ("Fit to build after amendments"): every finding taken; the review's Disposition says where.
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
- soupsieve's tiers: soupsieve-smoke ran out of fuel under 35 G at `test_escape_round_trip`. soupsieve 3.0.4's `test_api.py` adds two tests that match a selector for each of about 63,000 code points (`test_escape_round_trip`, `test_unescaped_non_ascii_identifiers`); with the cap lifted the smoke measured 164.8 G, past the 100 G a smoke group may measure (`test_upstream_files_are_well_formed`, red in run 41170628147). A keyword split cannot select inside a smoke family's groups (they are path groups, `tiers.kind_of`), so `test_api.py`, whole, leaves the smoke for the release tier's path group: soupsieve-smoke runs `tests/test_level1`, 15.1 G and 35 passes (88), cap 23 G by the 1.5 rule; soupsieve-r runs every other file, `test_api.py` with it, 185.8 G and 400 passes (342), cap 280 G; the budget is their sum, 303 G. No check moves between tiers; the smoke's pass count falls by the move, claimed under `fewer`.
- `tests/cpython_configure.txt`: the one line above. No pass count falls.

**Decision 11: bytes and fuel.** Bytes against dev's set; fuel on darwin arm64, numpy's, pandas' and CPython's groups at dev's set and the head's, the swept pins' against `accepted.json`'s darwin rows.

| | dev's set | the head | change |
|---|---|---|---|
| `python.wasm` | 99,421,513 | 99,487,062 | +65,549 (+0.066%) |
| `python-snapshot.wasm` | 104,517,748 | 104,576,267 | +58,519 (+0.056%) |
| `python-stdlib.zip` | 53,915,154 | 53,829,197 | −85,957 (−0.159%) |
| the wheel, built by hand from each set (run 41170628147's own: 98,327,640) | 98,371,695 | 98,327,639 | −44,056 (−0.045%); the run's is 1,672,360 under 100,000,000 and 6,529,960 under 104,857,600 |

| groups (darwin) | rows | up / down | median | range | sum |
|---|---|---|---|---|---|
| numpy, pandas, CPython, normal tier | 16 | 14 / 2 | +0.157% | −0.525% (cpython-archives) to +3.197% (cpython-a) | 2,906.2 G → 2,920.96 G, +0.507% |
| numpy, pandas, CPython, release tier | 18 | 16 / 2 | +0.134% | −0.130% to +1.108% (cpython-release-b-inline) | 4,372.4 G → 4,381.1 G, +0.199% |

Every pass count holds or grows: cpython-a 5,865 → 5,898 (and runs the four new modules), numpy-core 9,519 → 9,752, numpy-lib 4,825 → 4,835, numpy-others 7,277 → 7,295; every pandas group equal. The swept: pypdf-smoke +0.31% (217 → 218 passes), pypdf-r −2.42% (1,474 → 1,695), soupsieve-smoke 23.1 G → 15.1 G (88 → 35, `test_api.py` moved), soupsieve-r 31.4 G → 185.8 G (322 → 400), wrapt-smoke +0.79% (1,367 → 1,379), tzdata-smoke +0.20% (628 both).

Against the bounds: each artifact within ±1%; the wheel smaller. The upstream normal groups measured are +0.507% in sum (soupsieve-smoke now falls); soupsieve-r's growth is the release tier's, traced above. The own checks' fuel is the pull request's gather's darwin comparison (`ci:full`). cpython-a's +3.2% is its larger plan (four new modules, 33 more passing tests) and numpy-core's +1.57% its 233 more passing tests.

**The set at this head.** A clean rebuild from step 10 wrote the same `SHA256SUMS` as the incremental build, `784b119d2a67f85d4c1d4a16f4dc1c67a93799632440c46658ddafba4b082e26` (its digest): `python.wasm` `9ef1a190…`, the snapshot `ed740363…`, the zip `c23e82e1…`. Decision 12: run 41170628147 (the pull request's first, at `a7f5cee5`, `ci:full`) built the set on arm64 Linux; the run's arm64 Linux set's `SHA256SUMS` is byte-identical to this Mac's, digest `784b119d2a67…` (EXECUTED: its `release-assets` artifact unpacked and compared). A fix commit changes no recipe file, so the comparison holds at the next head.

**The local runs at this head.** `ruff check` and `ruff format --check` on `src tests release`: clean. `uv run pytest -m "not slow" -n 3 tests/unit tests/lint tests/checks/test_rules.py`: green after the unit rows above (3,562 passed, one rules row blocked by the prior-art clones, as on `dev`). `uv run pytest tests/lint`: 14 passed. `uv run pytest --shard=build`: 52 passed (41 checks, 11 unit), the configure row and the CLI recursion row among them. The data stack, artifact-set, matplotlib, scipy, regex and lxml check files: green after the linalg row. The upstream groups of numpy, pandas, CPython (both tiers), pypdf, soupsieve, wrapt and tzdata: green, the gaps as recorded.

**Run 41170628147's four red legs, and their fixes** (one fix commit; each check run locally by node id at the rebuilt set before the push):
- own-hostile-b, on all three systems: `test_deep_data_limits[hash-tuple]`. CPython 3.15.2 guards tuple hashing with its C-stack check (gh-154318, "A RecursionError is now raised instead of overflowing the C stack"), and the guest's guard window (`recipes/reactor_main.c`, the top 128 KiB of the linear stack, spec 071) raises "Stack overflow (used 112 kB) while hashing a tuple" before 30,000 levels. 3.15.0 recursed until the wasm stack trapped. The premise moved upstream, so the case moves from the trap table to `test_deep_data_raises` at 400,000 levels, as `repr` and `==` already are: `test_deep_data_limits[hash-tuple]` is retired, `test_deep_data_raises[hash-tuple]` is new, and `docs/reference/limitations.md` names `hash` among the C recursions that raise. No recipe changes: widening the guard window would spend the native stack it protects.
- upstream-windows: `test_upstream_suite[cpython-fs]` on Windows. `test_logging.FileHandlerTest.test_emit_reopen_error` is new in 3.15.2 and removes the folder of a file the handler holds open; CPython skips it on Windows, but the guest is not `nt`, and a Windows host refuses the removal. It is a host entry, `win-logging-emit-reopen-error` (darwin and Linux passed, Windows error), with its gap, as the other open-file entries are.
- upstream-pure-smoke-a, on Linux: tqdm-smoke's three classes. Under 3.15.2 the stray event loop of tqdm's asyncio tests is collected during `test_iter_overhead_simplebar_hard` rather than `test_iter_basic_overhead`, so the two tests trade classes (no-asyncio-loop-error against no-threads-error and no-threads), each with its class's cause and pattern; the same trade on darwin here.
- own-rest, on Linux and macOS: `test_upstream_files_are_well_formed`, soupsieve-smoke past 100 G; the tier change above.

### The second pull request: pandas 3.1.0 (built 2026-10-31)

Built on `spec/166-pandas-3-1-0`, stacked on the first pull request (built at its head `a7f5cee5`, rebased onto its fix commit `c2083f5c`, which changes no input of the set), by a builder sub-agent of the orchestrating session, in a worktree of its own beside 165's builder (the build at `nice 10`). Every figure is EXECUTED on an arm64 Mac (Darwin 25.5.0) unless it says otherwise. "The first pull request's set" is the set built at `a7f5cee5` (`python.wasm` `9ef1a190…`), and its pandas groups' fuel is that builder's darwin measurement at that set.

**Decision 8: pandas 3.1.0 is built; fallback A is not taken.** The newest 3.0.x is 3.0.6, the pin, so fallback A would have held pandas where it is. Two causes stopped the build, one attempt each, both closed by the cross file (§4.1, a recipe file first):
- pandas' moments (`pandas/_libs/simd/moments_scalar.cpp`, meson's choice for a `wasm32` host) include `pandas/simd/moments_simd.hpp`, which names xsimd's batch API (`xsimd::load_unaligned<Arch>`). xsimd 14.2.0 declares that API only when it finds a SIMD architecture, and the guest is built without SIMD128, so the compile failed (`no member named 'load_unaligned' in namespace 'xsimd'`). `-DXSIMD_WITH_EMULATED=1` declares it through xsimd's emulated architecture (plain scalar code, xsimd's "Emulated Mode"); the scalar path is what runs, and no SIMD instruction enters the binary.
- The link's weak-duplicate gate found eleven weak definitions of fast_float (`fast_float::pow5_tables<void>::large_power_of_5`, `bigint::pow5`, `parse_mantissa<char>` and eight more) in `libpandas_tokenizer.a` and scipy's `io._fast_matrix_market._fmm_core`. pandas compiles fast_float 8.2.10; scipy 1.18.1's fast_matrix_market vendors an older single-header fast_float with no version macros. Not one header, so not the same code, so no allow-list line: `-Dfast_float=pandas_fast_float` gives pandas' copy its own namespace (its `#include "fast_float/fast_float.h"` lines are header names, which the macro does not touch). The gate then passed with no new line in `recipes/weak-duplicates-allowed.txt`.
- C++20 itself needed nothing: pandas' `meson.build` asks `cpp_std=c++20`, `scripts/wasi-cxx` forces no standard, and wasi-sdk 34's clang compiles `<span>`, designated initializers and the rest. No new rename header: pandas' C rename header still covers its vendored numpy datetime helpers, and the C++ files carry none of them.
- pandas 3.1.0 renames its JSON module `pandas._libs.json` to `pandas._libs._ujson`, read from the built archives by `gen_inittab.py` as before: 45 extension archives, as 3.0.6 had.

**Decision 5: the pin against its publisher.** `pandas-3.1.0.tar.gz`, `ecb9b2d8…ace17e49`, 5,933,421 bytes, fetched once from PyPI's URL, equals PyPI's `digests.sha256` (read once, 2026-10-31). The oracle's lock (relocked with uv 0.9.22) carries PyPI's hashes for the sdist and the cp315 wheels, `c0bfec4d…` (macOS 11 arm64), `bbfb087d…` (manylinux aarch64) and `4b5ce186…` (manylinux x86-64).

**Decision 7: the licence files change, so the move waits for the owner (§4.12).** pandas' `LICENSE` and its thirteen `LICENSES/` files of 3.0.6 are byte for byte the same in 3.1.0. 3.1.0 adds three: `LICENSES/XSIMD_LICENSE` (BSD-3-Clause, xsimd, compiled into the moments), `LICENSES/STATSBASE_JL_LICENSE` (MIT, StatsBase.jl's `rankcorr.jl`, which `algos.pyx`'s Kendall's tau follows) and `LICENSES/NERI_SCHNEIDER_LICENSE` (MIT, Cassio Neri and Lorenz Schneider's branchless calendar algorithm, in the vendored `np_datetime.c`). Its `license-files` also names fast_float's three files in its vendored folder, `subprojects/fast_float-8.2.10/LICENSE-{APACHE,BOOST,MIT}` (fast_float is Apache-2.0 OR BSL-1.0 OR MIT, compiled into the CSV tokenizer). The assembler packs `LICENSES/` whole, so the first three ship already; `scripts/assemble_artifacts.py` now adds fast_float's three after them (`LICENSES/pandas.txt`, 52,715 → 70,240 bytes). All are permissive notices of code pandas 3.1.0 compiles in; no term of pandas' own licence moves. By Decision 7 the merge waits for the owner's answer on these new notices, as zlib's did.

**Decision 6: the carried patch, re-made.** `recipes/patches/pandas-3.1.0/0001-styler-templates-from-a-zip.patch` was re-made by applying the 3.0.6 patch to a scratch git tree of the 3.1.0 tarball and writing `git diff`; the same method against 3.0.6 reproduces the old patch byte for byte. Its `+` and `-` lines and its hunk header are 3.0.6's; only the `index` line differs (`a53c8e9..874d93e`). It applies at no offset. Its draft moved to `../upstream/patches/pandas-3.1.0/`, `Against` updated, and `../upstream/README.md` names the new path.

**Decision 10: the judge's files.**
- Goldens: `tests/jobs/regen.py` under the oracle at pandas 3.1.0 remade sixteen, each in its first line alone, `pandas=3.0.6` to `pandas=3.1.0`. No job's output moves, and the guest matches every one.
- `tests/upstream/pandas.ini`, transcribed again: 3.1.0's first filter is `error` (every warning an error; 3.0.6's was `error:::pandas`), its markers moved from `pyproject.toml` into `pandas/conftest.py`'s `pytest_configure`, which the driver stages, its `--junitxml` left its addopts, and the third-party filters changed (the encoding filters name `EncodingWarning`; sqlite, coverage, `BuiltinImporter` and bitwise-inversion lines in; botocore, setuptools, tables, `ssl.SSLSocket`, `BufferedRandom` and asyncio lines out). With `error` first, the driver's own warning stopped every session before collection: the driver imports hypothesis before pytest (to load its judge profile), so pytest cannot rewrite `_hypothesis_globals` and warns. 3.0.6's list ignored that warning; the transcription keeps one line for it, as `numpy.ini` and four other families' do, named in its header.
- `expected/pandas-io-parser/no-mmap.txt`: 3.1.0 adds a parallel `read_csv` for large local files that maps its file (`pandas/io/parsers/readers.py`, `_read_csv_parallel`) and `test_parallel_read.py`, 164 tests; sixteen of them reach the parallel reader and fail with the stand-in's `OSError: mmap is unavailable on wasm32-wasi`, the class's cause and pattern, as does the new `test_python_parser_only.py::test_memory_map_multichar_sep[python]`. The list holds 57 (40); none leaves. Its gap counts 57 findings.
- `pandas-slow-b` gains two classes, each with its gap (closer `docs/reference/limitations.md`). **no-mmap**, nine members: `TestReadCsvParallel`'s slow tests call `_read_csv_parallel` directly. **wasm32-int32**, three members: `test_categorical_dtype_high_cardinality_numeric[c_high, c_low, python]` passed at 3.0.6 and fails at 3.1.0, because 3.1.0 rewrote it to build its expected categories from `np.array([int(x) for x in data])`, numpy's default integer, which is 32 bits on wasm32, while `read_csv(dtype="category")` infers int64 categories. The product's answer is native's: the same program on native pandas 3.1.0 (the oracle) and in the guest gives int64 categories; only the test's expected `int32` differs (`build/166/probe_cat.py`, EXECUTED both). This is the one test that passed, still exists and now fails (Decision 10's finding to fix); the fix is pandas' test's (an explicit `dtype=np.int64`), not the product's, so it is recorded as a class beside narwhals' `wasm32-int32`, and a test-source patch is the alternative if the reviewer prefers one.
- The product's `read_csv` stays serial: pandas' worker count is `os.cpu_count()` unless `mode.max_threads` is set, and the guest's `os.cpu_count()` is 1 (EXECUTED: `wasi wasm32 1`, `_default_n_workers()` 1), so a large CSV takes the serial path that never maps. Setting `mode.max_threads` in the guest reaches the mapping and raises `OSError`, as `limitations.md`'s "no mmap" says.
- Fuel cap: `pandas-io-parser` ran out of fuel under 135 G at `test_parallel_read.py`. Measured with the cap lifted (this Mac, this head's set): 182.17 G, against 94.37 G at the first pull request's set. The cap keeps the group's headroom (135 / 94.37 = 1.431): 261 G.
- Pass counts: every normal group grows (5,254 more passes). The release groups fall: `pandas-slow-a` 2,259 → 2,256 and `pandas-slow-b` 28 → 26. Each fall is upstream's: 3.1.0 drops the `slow` mark from `test_where_inplace_casting` (now parametrized), `test_unstack_number_of_levels_larger_than_int32_warns`, `test_pivot_number_of_levels_larger_than_int32_warns` and `test_isocalendar`, so their six nodes leave the slow groups for the normal ones, and slow-b's three `wasm32-int32` cases fail as above, beside four new passing parallel-read tests. Per group, no other test that passed at 3.0.6 and still exists fails (EXECUTED, the streams of `pandas-io-parser`, `pandas-slow-a` and `pandas-slow-b` at both sets compared node by node: 31, 3 and 3 passing nodes absent, renamed or re-marked upstream).
- `tests/fixtures/upstream-stages.json`: pandas' staged files' digest is the 3.1.0 tarball's (`1527f12c…`); its group JSON is unchanged.

**Decision 11: bytes and fuel**, against the first pull request's set (and dev's, from the first pull request's table).

| | the first pull request's set | this head | change | against dev's set |
|---|---|---|---|---|
| `python.wasm` | 99,487,062 | 100,627,632 | +1,140,570 (+1.146%) | +1,206,119 (+1.213%) |
| `python-snapshot.wasm` | 104,576,267 | 105,717,756 | +1,141,489 (+1.092%) | +1,200,008 (+1.148%) |
| `python-stdlib.zip` | 53,829,197 | 54,162,674 | +333,477 (+0.620%) | +247,520 (+0.459%) |
| the wheel, built by hand from each set | 98,327,639 | 99,186,606 | +858,967 (+0.874%) | +814,911 (+0.828%) |

The wheel is 813,394 bytes under 100,000,000 and 5,670,994 under 104,857,600, so decision 64's line is not crossed.

| pandas group (darwin) | tier | fuel, the first pull request's set | this head | change | passes |
|---|---|---|---|---|---|
| pandas-frame | normal | 354.79 G | 372.81 G | +5.08% | 10,926 → 13,957 |
| pandas-groupby | normal | 487.63 G | 439.73 G | −9.82% | 22,228 → 22,632 |
| pandas-internals | normal | 21.75 G | 20.95 G | −3.70% | 258 → 269 |
| pandas-io-formats | normal | 89.67 G | 80.69 G | −10.01% | 1,972 → 2,058 |
| pandas-io-parser | normal | 94.37 G | 182.17 G | +93.04% | 3,474 → 4,785 |
| pandas-libs | normal | 27.28 G | 26.12 G | −4.25% | 1,063 → 1,134 |
| pandas-reshape | normal | 103.30 G | 99.00 G | −4.16% | 2,664 → 2,858 |
| pandas-tslibs | normal | 38.86 G | 31.76 G | −18.27% | 590 → 736 |
| pandas-slow-a | release | 303.78 G | 269.34 G | −11.34% | 2,259 → 2,256 |
| pandas-slow-b | release | 86.75 G | 84.35 G | −2.77% | 28 → 26 |

Normal tier: 8 groups, 2 up and 6 down, median −4.21%, sum 1,217.64 G → 1,253.23 G (+2.92%). Release tier: both down, sum 390.54 G → 353.69 G (−9.43%).

Against the bounds: `python.wasm` and the zip within +3%. Every pandas group within +15% but `pandas-io-parser`, +93.0%, traced: `test_parallel_read.py` alone, in a session of its own, takes 79.7 G (about 14 G of it the session's start, the fuel a session that stops before collection spends), with 111 passes, and the other parser files pass 1,200 more tests (`test_c_parser_only.py` +358, `test_common_basic.py` +157, `test_categorical.py` +135, `test_float.py` +94 and more). The own checks measured (the data stack, artifact-set, default-profile, zip-directory, lxml, matplotlib, scipy and regex files, 159 metered rows) against the first pull request's: +0.419% in sum, median −0.001%, at most +1.81% (`test_numpy_and_pandas_are_builtin_at_manifest_versions`, the import), none past +5%.

**Decision 10's release groups over pandas: four lose passes, and this waits for the owner.** The release groups of statsmodels, scikit-learn, matplotlib and contourpy, both tiers, ran locally at this head (122 checks pass, 47 known gaps hold as recorded, 4 fail; 25 minutes): matplotlib's and contourpy's pass, and four groups lose their accepted pass, each to pandas 3.1.0's own changes, not to the guest:
- `scikit-learn-datasets`, 27 findings, all in `sklearn/datasets/tests/test_openml.py` with `parser="pandas"`. pandas 3.1.0's `read_csv(dtype="category")` infers numeric categories (int64) where 3.0.6 kept strings, so scikit-learn 1.9.1's `_pandas_arff_parser` hands an int to `re.search` in `strip_single_quotes` (`TypeError: expected string or bytes-like object, got 'int'`), and its type-inference tests see other category types. Natively, scikit-learn 1.9.1's wheel on pandas 3.1.0 (the oracle) fails the same 27 tests by name (EXECUTED, `build/166/native_run.py`). In the product, `fetch_openml(parser="pandas")` of a dataset with numeric categories breaks as natively; the guest has no network, so it reaches it only through a filled `data_home`.
- `statsmodels-tsa-statespace-1` (12 findings: `test_exponential_smoothing.py`'s concentrated-initialization tests), `statsmodels-tsa-statespace-2` (`test_news.py::test_news_summary_methods`) and `statsmodels-graphics-to-multivariate-factor_rotation` (`test_tsaplots.py::test_plot_quarter`): pandas 3.1.0 deprecates the `inplace` keyword (`Pandas4Warning`, "The inplace keyword in Series.drop is deprecated", `DataFrame.set_index` likewise), which statsmodels 0.15.0 passes (`news.py:956` and `:1136` among them), and the tests see the warning as an error. In the product these are warnings, and the results are unchanged.
- No newer scikit-learn 1.9.x or statsmodels 0.15.x exists (the sweep's candidates), so the pins cannot follow.

Decision 10 makes a test that passed, still exists and now fails a finding to fix, and Decision 8 sends pandas to fallback A when it "loses passes it should keep". These passes are lost to an incompatibility between pinned releases, the same natively, so neither a class (an allowance for a lost pass) nor fallback A is the builder's to choose alone. The owner's choice, asked by the orchestrator: **A**, 0.1.3 keeps pandas 3.0.6 (the newest 3.0.x) and this pull request closes; **B**, pandas 3.1.0 with two carried patches, scikit-learn's ARFF parser keeping its categories as strings and statsmodels' `inplace` calls rewritten, each with its upstream draft; **C**, pandas 3.1.0 with the four losses recorded as classes, closer the packages' next releases. These groups are release tier, so this pull request's run does not see them; the release pull request would. scipy's groups, both tiers, ran after them at this head: 174 pass and 49 known gaps hold as recorded, no pass lost (43 minutes).

**The news file while stacked.** The news file holds two claim blocks: the first pull request's, as #67 carries it at `c2083f5c`, and this one's after it. While this branch carries #67's commits, its run judges their changes too (an absent `test_deep_data_limits[hash-tuple]` is red unless a claim retires it: run 41180751848 went red on every judge leg with the first block replaced). Once #67 merges and its acceptance is written, the rebase onto `dev` drops the first block, so the acceptance after this merge reads this block alone.

**Decision 12: same bytes, and the local runs at this head.** The set was built clean from step 00 in this worktree (step 50 three times over the two causes above, then 53 to 90). Its `SHA256SUMS` (digest `91105cf51691…`; `python.wasm` `e735e196…`, the snapshot `2fb3cf9f…`, the zip `722dccbb…`) is byte-identical to the set run 41180751848 built on arm64 Linux at `c3927750` (its `release-assets`; every file checks against it), and nothing the set reads changed after `c3927750`. The run's wheel is 99,186,606 bytes, the hand-built one's size: 813,394 under 100,000,000. 165's builder measured its wheel on #67 at 99,460,553 bytes (+1,132,913 over #67's 98,327,640), so with both changes the wheel would be about 100,319,500 bytes, past decision 64's line by about 320,000: the owner's question before the second of them merges, joined with 167's PyPI request. `ruff check` and `ruff format --check`: clean. The fast tier at the head: 3,562 passed, the one rules row blocked by the prior-art clones, as on `dev`. `uv run pytest tests/lint`: 14 passed. `uv run pytest --shard=build`: 52 passed (41 checks, 11 unit rows); `tests/cpython_configure.txt` unchanged. The data stack's, artifact-set's, default-profile's, zip-directory's, lxml's, matplotlib's, scipy's and regex's check files: 228 passed, the wheel row blocked without a wheel in `dist/`. Every pandas group, both tiers: 17 passed, 5 known gaps as recorded.
