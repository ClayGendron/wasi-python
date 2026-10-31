# 166: The pins move for 0.1.3

- **Status:** drafted 2026-10-30, to be reviewed before it is built (the build recipe: constitution §5.6). The owner chose it on 2026-10-30 (decisions.md, "The scope of 0.1.3").
- **Date:** 2026-10-30
- **Owner:** Clay Gendron
- **Kind:** **build-class**, **a judge change**, not structural: nothing under `src/` changes. Recipe: `scripts/line.conf`, `00_download.sh`, `downloads/SHA256SUMS`, steps 10, 40, 50 and 70, `scripts/assemble_artifacts.py` (`PACKAGES`, line 804), the numpy and pandas patches. Judge: one rules row, `tests/harness/paths.py`'s `wasmtime_cli()`, the oracle, the goldens, `tests/upstream/` files of numpy and pandas. Documents: `SECURITY.md`, two pages of `docs/reference/`.
- **Depends on:** landed: 020, 127 (the runner on wasmtime-py 50.0.1; its Decision 6 left the CLI to a build-class specification), 136, 158, 159 (the build on arm64 Linux; two rebuilds vote). Siblings: 165 and 167 touch `SHA256SUMS`, `00_download.sh` and the oracle as text neighbours; 166's first pull request lands before they are built, so their packages are measured once on the new line. 162, 163, 164 and 168 touch `src/` only.
- **Research it stands on:** `../research/2026-10-30-what-0-1-3-could-carry.md`, item H (line 55); `../decisions.md` line 530; `../roadmap.md` line 91; 127's Decisions 6 and 7; 086 (a build-class move). Read once each on 2026-10-30: sqlite.org's chronology (3.54.1, 2026-10-16, is the newest); PyPI (numpy 2.5.4 and pandas 3.1.0 are the latest); wasmtime's v50.0.1 release (2026-10-29; five advisories, in wasi-sockets, GC types, typed `i31` calls, component resources and wasi-http); python-build-standalone's releases (20261026 carries 3.15.2).

Labels: EXECUTED means run and seen; READ means read from a file, cited; INFERRED means reasoned.

## The problem

The owner chose five moves: CPython 3.15.0 to 3.15.2, SQLite 3.54.1, the build's wasmtime command line 49.0.3 to 50.0.1, numpy 2.5.2 to 2.5.4, pandas 3.0.6 to 3.1.0, and the bug-fix releases that exist at build time.

One is done. `downloads/SHA256SUMS` has pinned `sqlite-autoconf-3540100.tar.gz`, SQLite 3.54.1, since spec 007 (2026-10-17), still the newest (READ).

The build's wasmtime 49.0.3 runs `wasmtime wizer` (`scripts/steps/80_snapshot.sh`). The runner has been on wasmtime 50 since 127. Two engine lines touch one set.

pandas 3.1.0 needs C++20 and is eight days old; it can fail alone.

## Decisions

### 1. One specification, two pull requests

The first moves CPython, the CLI, numpy and the sweep. The second moves pandas, stacked on the first or after it. A C++20 failure then holds back pandas alone. Each moves the set's key, so each run compiles and runs the upstream groups.

### 2. The order on the first branch, one commit each

1. The rows of Decision 9.
2. CPython 3.15.2: `PYTHON_VERSION`, the tarball, the three host Python archives from python-build-standalone 20261026, and the oracle's `requires-python` and lock. `10_tools.sh` line 214 ties the host Python to the line's version.
3. The CLI: the three `*_WASMTIME_DIR` names and archives.
4. numpy 2.5.4: the tarball, the three `NUMPY_HOST_WHEEL`s, the f2py check (`10_tools.sh` lines 227 and 230), the oracle, the patches.
5. The sweep, one commit per pin.

CPython goes first: every package is built by its cross Python. numpy precedes pandas, which compiles against its headers.

### 3. SQLite holds at 3.54.1

No line changes; the release notes say nothing. `35_stdlib_libs.sh` line 63 follows python-build-standalone's `PRAGMA compile_options`; the builder reads them again in the new host Python and records a difference.

### 4. The CLI is the runner's line, and a row holds it

The CLI moves to the newest 50.x at build time, 50.0.1 today. The judge compares fuel within one wasmtime major (spec 002, Decision 6), so "one version" means one major. A new row, `tests/checks/test_rules.py::test_the_builds_wasmtime_is_the_runners_line`, reads each host's `WASMTIME_DIR` in `line.conf` and `_wasmtime_ffi.PIN`, and fails when the majors differ.

The runner's engine does not move, so fuel stays comparable and spec 154 does not apply. The snapshot's bytes may move: the builder snapshots the branch's `python.wasm` with both CLIs and compares the two with `scripts/compare_snapshots.py`. A wizer flag renamed in 50 is an edit to `80_snapshot.sh`. A failure of `test_recursion_raises_under_the_wasmtime_cli`, the one row that runs a guest under the CLI, is a finding, not a judge edit.

`wasmtime_cli()` takes the first match of `wasmtime-v*`, so a tools folder holding both versions gives 49.0.3. It now reads the host's `WASMTIME_DIR` by exact name, as `tests/harness/scan.py` reads the host names.

### 5. Each new pin is hashed once and checked against its publisher

Each new file is fetched once by `00_download.sh`. Its SHA-256 is checked against the publisher's record (PyPI's digests, python.org's release page, python-build-standalone's `SHA256SUMS`, the GitHub asset digest for wasmtime), in a table in the landing notes.

### 6. The carried patches are re-made, not changed

A patch applies at no offset, so each is made against exactly its tarball. numpy's two move to `recipes/patches/numpy-2.5.4/`, pandas' one to `recipes/patches/pandas-3.1.0/`, and their drafts under `../upstream/patches/` with `Against` updated. All three are `drafted`. Each re-made patch's added and removed lines equal the old one's, apart from context; the landing notes show it. A change that must differ is a new change, reviewed as a patch. A patch upstream made unneeded is deleted, with its draft and a CHANGELOG line. The examples in `recipes/patches/README.md` and `docs/contributing/carrying-a-patch.md` name the new folder.

### 7. The sweep takes bug-fix releases of what ships

In: every pin compiled into `python.wasm` or shipped in the zip that has a release with the same major and minor and a higher patch on the day the branch is made; tzdata takes its newest. A swept pin's test source moves with it, and its `.ini` transcription is read again.

Out: the build's own tools (wasi-sdk, meson, Cython, ninja, pkgconf, versioneer, the Debian packages, pybind11, cppy), unless a moved package requires one. Out too: openpyxl and et-xmlfile, whose test archives need the owner's upload to the mirror (spec 158).

The landing notes list the candidates first. A pin whose licence file changes waits for the owner (§4.12). One that fails its suite in a new way twice goes back, named.

### 8. pandas 3.1.0 builds with its own C++20 (A decided; B the owner's alternative)

The second pull request moves `50_pandas.sh`, the tarball, `assemble_artifacts.py`, `70_zip.sh` (line 147), the oracle and the patch. C++20 comes from pandas' `meson.build`; `scripts/wasi-cxx` forces no standard. wasi-sdk 34's clang and libc++ compile C++20 (INFERRED). A missing header gets a recipe file first (§4.1). If pandas 3.1.0 fails to build, or loses passes it should keep, after two attempts on one cause: **A**, 0.1.3 ships pandas' newest 3.0.x and 3.1 moves in 0.1.4. **B**, the owner's alternative, holds 0.1.3 for pandas 3.1. The builder asks with AskUserQuestion, A first.

### 9. The rows first

Each is seen failing on `dev`'s tip first:

- `test_the_builds_wasmtime_is_the_runners_line`: red at 49 against 50.
- A unit row in `tests/unit/test_build_scripts.py`: `wasmtime_cli()` over a folder holding `wasmtime-v49.0.3-*` and `wasmtime-v50.0.1-*` returns the line's; today 49.0.3.
- `test_the_guests_configure_results_are_recorded` builds its path from `PYTHON_VERSION`, not the literal `Python-3.15.0` (`test_v1_5_rebuild_from_pins.py` line 568); under 3.15.2 it fails today.

### 10. What the judge's files may change

Each is a judge change with its reason in the claim, never a way to turn a run green.

- **Goldens** are remade by `tests/jobs/regen.py` under the new oracle, each diff and cause in the landing notes. A guest that stops matching the oracle is a failure.
- **`expected/` lists**, three kinds of edit only. A node upstream renamed, removed or fixed leaves its list. A new failing node joins a class only when the pattern matches and the traceback shows the class's cause. A new kind of failure is a new class with its closer.
- **Pass counts** fall only because upstream deleted or moved tests; `fewer` gives the counts. A test that passed, still exists and now fails is a finding to fix.
- **`numpy.ini`, `pandas.ini`** are transcribed again, the diff in the landing notes. **Fuel caps** rise only past the measured value. **`tests/cpython_configure.txt`** changes only by a result 3.15.2 flips, named.

The release tier runs only at the release pull request, so the builder runs its numpy, pandas and CPython groups locally before the review and appends their claims to the release ledger.

### 11. Bytes and fuel are bounded, then claimed

The landing notes hold 086's table: bytes per artifact; fuel rows up and down, median, minimum, maximum, sum. Above these bounds the cause is traced before the claim. First pull request: each artifact at most +1%, the normal tier's fuel sum at most +1%, no own check over +5%. Second: `python.wasm` and the zip at most +3%, each pandas group's fuel at most +15%. The bounds are INFERRED: 086's toolchain move grew the binary 0.164% (EXECUTED there), and a pandas minor release adds code.

### 12. Same bytes before the release

`release/ci_plan.py`'s `decide()` runs no rebuild on a pull request, so the builder builds the first head on macOS arm64 and compares `SHA256SUMS` with the run's arm64 Linux set. The x86-64 vote comes at the first weekly run after the merge, its run id recorded.

### 13. The documents and the release notes

`SECURITY.md` line 24's last sentence says the build's command line is wasmtime 50.0.1, the runner's line, and only makes the snapshot; `MANIFEST`'s pin lines name it. `packages.md` and `support-and-versioning.md` name the new versions. The news file, `../changes/166-the-pins-move-for-0-1-3.md`:

- `### Security`, only if 3.15.1's or 3.15.2's changelog fixes a module the zip carries: the issue and its link.
- `### Upgrading`: **CPython 3.15.2 and numpy 2.5.4 inside.** The guest's Python moves from 3.15.0 and numpy from 2.5.2, both bug-fix releases. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)
- `### Upgrading`: **pandas 3.1.0 inside.** pandas moves from 3.0.6 to a new minor release. Read pandas' own 3.1.0 notes for code that relies on what it changed. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)
- `### Upgrading`: **Saved snapshots are made again.** The binary and the zip change, so a `Snapshot` saved with 0.1.2 raises `SnapshotMismatch`. Make it again after you upgrade. [Snapshots](https://claygendron.github.io/wasi-python/how-to/snapshots/)
- `### For contributors`: **The build's wasmtime is the runner's line.** The snapshot is made by wasmtime 50.0.1, not 49.0.3, and the patches are re-made under `recipes/patches/numpy-2.5.4/` and `recipes/patches/pandas-3.1.0/`. [Building](https://claygendron.github.io/wasi-python/contributing/building/)

Package rows: numpy `2.5.4`, pandas `3.1.0`, "what works" unchanged.

## Intent

One pinned set for 0.1.3, one wasmtime line for build and runner, every change measured and given its reason.

## Design

The files are in Kind and the Decisions. No guest import or export changes.

## Scope

In: Decisions 1 to 13. Out: wasmtime 51 for runner and CLI together (127's shape, its own specification); the build tools; SQLite; the two mirrored pins; new packages (165, 167).

## Acceptance criteria

1. Decision 9's rows fail on `dev`'s tip, then pass (EXECUTED).
2. Every moved pin matches its publisher's hash (READ); the rebuild-from-pins checks pass.
3. Each patch applies at no offset; its changed lines equal the old ones or its draft says why (READ).
4. `python.wasm -V` names 3.15.2; `test_numpy_and_pandas_are_builtin_at_manifest_versions` passes at 2.5.4 and 3.1.0 (EXECUTED).
5. The two-CLI snapshot comparison is recorded (EXECUTED).
6. Every golden diff and `tests/upstream/**` edit is one of Decision 10's kinds, with its reason (READ by the reviewer).
7. The local release-tier groups are green and the ledger has their claims (EXECUTED).
8. Decision 11's table is in the landing notes, within bounds or each cause traced (EXECUTED).
9. The macOS and arm64 Linux sets agree (EXECUTED); the weekly x86-64 vote is recorded.
10. The news file passes `test_the_news_files_have_their_shape`; each pull request's `ci-status` is green and its review says "Lands".

## Landing notes

To be written at the landing.
