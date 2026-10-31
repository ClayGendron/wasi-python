# 169: zstd, built in

- **Status:** drafted 2026-10-31, to be reviewed before it is built (the build recipe). The owner approved the licence on 2026-10-31 (decisions.md, "The decisions of 2026-10-31 morning", on PR #72). Amended the same day against its pre-build review, `../reviews/169-zstd-built-in-spec-2026-10-31.md` ("Fit to build after amendments"): its Medium and nine Lows taken (its Disposition says where). Built 2026-10-31 on `spec/169-zstd-built-in`; its pull request is open (Landing notes).
- **Date:** 2026-10-31
- **Owner:** Clay Gendron
- **Kind:** **build-class**, **a judge change**, one carried patch (pandas); not structural: nothing under `src/` changes. It is specification 167's Decision 10 (B1 to B4) under its own number, as that decision asks.
- **Depends on:** landed: 007 (the route this follows), 020 (carried patches), 063 and 065 (own suites, CPython's plan). 166: CPython 3.15.2 (#67) and pandas 3.1.0 (#71) land first; this is written against them. 167's Part A brings the wheel's size gate (`PYPI_FILE_LIMIT`). 167 and 170 also move the tree count; the second to land rebases and recounts.
- **Research it stands on:** `167-pdfplumber-plotly-xarray-and-zstd.md`, Decision 10, and its pre-build review `../reviews/167-pdfplumber-plotly-xarray-and-zstd-spec-2026-10-30.md` (Findings 6 to 8, confirmed); `007-sqlite3-bz2-and-lzma.md`; `../decisions.md`, "The decisions of 2026-10-31 morning" (the licence; the wheel's interim line). **Drafting reads** (READ, 2026-10-31): CPython's and pandas 3.1.0's files and the build and judge files cited below.

Labels: EXECUTED means run and seen; READ means read from a file, cited; INFERRED means reasoned.

## The problem

1. CPython's WASI build has no libzstd, so `compression.zstd` (PEP 784) fails to import, as the `-V` line says (`recipes/reactor_bootstrap.py:28-32`).
2. Three surfaces depend on it: `compression.zstd` itself; `tarfile`'s `zst` modes and `zipfile`'s `ZIP_ZSTANDARD`; and `shutil`'s `zstdtar` format. `shutil` and `zipfile` try the import at module top (`shutil.py:36`, `zipfile/__init__.py:35`), so they register it once `_zstd` exists.
3. pandas' `compression="zstd"` imports the third-party `zstandard` (`io/common.py:915`), which the set does not carry.
4. CPython's `test_zstd` is in the plan (`tests/upstream/python/cpython-b.txt:140`) and skips whole today.

## Decisions

### 1. The pin: zstd 1.5.7's release tarball

`zstd-1.5.7.tar.gz` from `https://github.com/facebook/zstd/releases/download/v1.5.7/`, in `downloads/SHA256SUMS` and `scripts/00_download.sh`. The builder checks the SHA-256 against the release's own `.sha256` asset and its signature, and records both in the landing notes, with the signing key's fingerprint and where it was read. 1.5.7 is the oracle's libzstd on 3.15.0 (EXECUTED in 167); the builder checks it again on 3.15.2's oracle (`compression.zstd.zstd_version_info`). Equal versions let the golden compare compressed bytes.

### 2. Step 35 builds `libzstd.a`, outside the tree

Step 35 compiles a fourth library as it compiles bzip2 (`scripts/steps/35_stdlib_libs.sh:26-38`), each file by `clean $CC` into `build/zstd-build/`, archived as `build/stdlib-libs/lib/libzstd.a`. The files are every `.c` under `lib/common`, `lib/compress`, `lib/decompress` and `lib/dictBuilder`, sorted: about 30 in 1.5.7 (INFERRED). The builder records the count, and the step stops on any other. Objects are named by basename, and the step stops if two share one. The include folders are zstd's own build's: `lib/` and `lib/common/`. `dictBuilder` is needed: `compression.zstd.train_dict` and `finalize_dict` call it. The flags:

- `-O2 -DZSTD_DISABLE_ASM`: the one `.S` file is x86-64 only and is not listed.
- `-D_WASI_EMULATED_PROCESS_CLOCKS`, as qhull's (`37_plot_libs.sh:74`): `dictBuilder` calls `clock()` for its progress display. The emulated clock is linked already, so the guest's imports and constructors do not change, as their checks hold.
- `-DXXH_NAMESPACE=ZSTD_`: zstd's own Makefile sets it, so its xxHash cannot meet another in the link.
- `-DZSTD_LEGACY_SUPPORT=0`: no decoder for frames from zstd before 0.8 (2016). The limitations page says so.
- no `ZSTD_MULTITHREAD`: the guest has no threads. `nb_workers` above 0 raises `ValueError` (167's review, Finding 6), and `test_zstd` skips its threaded cases (`test_zstd.py:68`).

`zstd.h`, `zdict.h` and `zstd_errors.h` go to `build/stdlib-libs/include/`. The step's size line names it. The tree stays its tarball, so the tree check covers it.

### 3. Step 60 links `_zstd` through `Setup.local`

The route of 007 (Decision 3). Step 60 changes in four places:

- `libzstd.a` joins the archives it requires (`60_link.sh:21-23`).
- It joins the weak-duplicate gate's list (`:100`).
- `Setup.local` gains `_zstd _zstd/_zstdmodule.c _zstd/zstddict.c _zstd/compressor.c _zstd/decompressor.c -I$SL/include $SL/lib/libzstd.a`, CPython's own four files (`Setup.stdlib.in:69`). No `=`.
- `_zstd` joins the dropped-module check (`:139`).

The comments that count the libraries change: `60_link.sh:2-4` and `:96`, and `35_stdlib_libs.sh:2-5`.

### 4. pandas reaches `compression.zstd` when `zstandard` is missing

A carried patch, `recipes/patches/pandas-3.1.0/0002-zstd-from-the-standard-library.patch`. In `get_handle`'s zstd branch (`io/common.py:914-924`), `import_optional_dependency("zstandard", errors="ignore")`; when it returns `None`, the handle is `compression.zstd.ZstdFile(handle, mode=ioargs.mode, level=...)`. `level` is forwarded only when writing. Any other key raises `TypeError` naming it, and on read any key does, `level` included, as `zstandard.ZstdDecompressor` would; `ZstdFile` itself refuses `level` in read mode (3.15.2 `_zstdfile.py:63-65`). None is dropped silently. With `zstandard` present, pandas' path is unchanged.

Why a patch and not a stand-in `zstandard` (constitution §4.1). pandas asks for `zstandard>=0.23.0` (`compat/_optional.py:55`), so a stand-in would have to claim a version of a package it is not. `pd.show_versions()` would report it, and a user's `import zstandard` would meet a partial API. Its one gain: pandas' `compression` fixtures would run. The patch is about fifteen lines with an upstream path, so it is the smaller departure.

pandas' own zstd tests skip without `zstandard` (`conftest.py:320`, `:337`, READ), so this specification's guest check is that path's only test, and the survey says so. Before drafting, the builder reads pandas' main branch and issue tracker. If upstream already has a fallback, the patch backports that commit, its hash in the draft, so deleting the patch at upstream's release changes nothing a user sees. The draft, `context/upstream/patches/pandas-3.1.0/0002-zstd-from-the-standard-library.md`, follows pandas' contribution rules, read at build. It offers the fallback for Python 3.14 and later.

### 5. The checks

- **Golden job `zstd_files`** (v1.3, `tests/jobs/zstd_files.py`, joining `JOBS` at `tests/harness/jobs.py:33`). It follows `compress.py`'s shape: the payload built from `sales.csv`, each output's length and SHA-256 printed with its round trip. It prints `compression.zstd.zstd_version_info` first, so a version difference shows as one line, not as every hash. Its lines: `compression.zstd.compress` at levels 1, 3 and 19; a dictionary from `train_dict` over fixed samples, and a frame compressed with it; a streaming `ZstdFile` written in 4 KiB pieces; `tarfile`'s `w:zst` with `compress.py`'s fixed metadata; `zipfile`'s `ZIP_ZSTANDARD` with a fixed date; and `shutil.get_archive_formats()` naming `zstdtar`. Native 3.15.2 under the oracle writes the golden. zstd's output at these levels does not depend on the word size (INFERRED). If a line differs, the builder stops and records it before touching the job.
- **Guest check `test_pandas_zstd_reads_and_writes_through_the_standard_library`** (v1.3, `test_v1_3_data_stack.py`). `to_csv(path, compression="zstd")` and `to_csv("frame.csv.zst")`, then `compression.zstd.open(path, "rt").read()` equals `to_csv()`'s text, and `read_csv` gives the frame back; `read_csv("frame.csv.zst")` infers the method; a `BytesIO` handle works both ways; `to_pickle` and `read_pickle` with `compression="zstd"` round-trip; `{"method": "zstd", "level": 19}` writes; `{"method": "zstd", "threads": 2}` raises `TypeError` naming `threads`, and so does `level` on read. No oracle: it has no `zstandard`. Seen failing first without the patch.
- **`test_stdlib_c_modules_are_builtin`** (`tests/checks/test_v1_1_artifact_set.py:348-357`) gains `_zstd`, on both binaries.
- **The `-V` line** drops "zstd", and the check that reads it follows.
- **Own suite (063).** `tests/upstream/packages.toml`: `stdlib_modules` (line 13) gains `compression.zstd`, and `[package.zstd]` is `kind = "via"`, `via = "compression.zstd"`, valid under `tests/harness/shards.py:388-395`. CPython's `test_zstd` now runs in `cpython-b` (490 G, `tests/upstream/python.toml:48-50`). The zstd cases of `test_tarfile`, `test_zipfile` and `test_zipfile64` run in `cpython-archives` (250 G) and the release tier's `cpython-release-archives` (150 G, 99.7 G measured); `test_shutil`'s in `cpython-fs` (100 G); and `test_zipimport`'s (`test_zipimport.py:1101`) in `cpython-archives` too. A test that fails in the guest gets an expected class with its reason. A fuel cap that must rise is a judge change with this specification's reason.

### 6. The files of the set

- `scripts/assemble_artifacts.py`: `PACKAGES` gains `"zstd": "1.5.7"`. `LICENSES/zstd.txt` holds `LICENSE` (BSD-3-Clause, the side of zstd's BSD-or-GPLv2 choice the set takes) and `lib/dictBuilder/divsufsort.c`'s head comment through `head_notice` (`:607`), with Yuta Mori's MIT words. The approval names both.
- `tests/harness/paths.py`: `LICENCE_COMPONENTS` and `PACKAGES` gain `zstd`. `_top_level_licence` (`:656`) takes the first top-level `LICENSE*` or `COPYING` in the tarball's order, and `MORE_LICENCE` (`:681`) only adds texts. A `git archive` tarball lists `COPYING` (GPLv2) before `LICENSE` (INFERRED). So the builder first lists the tarball's top level (`tar -tzf zstd-1.5.7.tar.gz | awk -F/ 'NF==2'`) and records the order. If `COPYING` comes first, `paths.py` gains `TOP_LICENCE = {"zstd": "LICENSE"}`, which `_top_level_licence` reads in place of the first match. Its reason: zstd is BSD-3-Clause or GPLv2 at the user's choice, and the set takes BSD-3-Clause. Shipping GPLv2's text too is refused: it would suggest the set is under GPLv2. `_more_licence` reads top-level members only (`:701`), so divsufsort's notice stays the assembler's `head_notice`, which stops the build if its words are missing; the judge checks the notice file's presence for it.
- `tests/harness/pins.py` `SOURCE_PATTERNS` and `tests/harness/needs.py` `SOURCE_COMPONENTS` gain `zstd`.
- `.github/workflows/release.yml`: the tree count, now "^28 passed" at `:383`, `:489` and `:588`, rises by one.
- `recipes/snapshot-packages.txt`: `zstd: compression.zstd`.

### 7. What the user sees

The `-V` line on both reference pages (`limitations.md:11`, `packages.md:11`). The limitations page's "No `_ssl` and no `_zstd`" becomes "No `_ssl`", and a line says frames from before zstd 0.8 do not decode and `nb_workers` must be 0. The packages page's paragraph on the built-in stdlib modules (`packages.md:13`) gains `compression.zstd` over libzstd 1.5.7, and that `tarfile`'s and `zipfile`'s zstd modes and pandas' `compression="zstd"` work.

### 8. Size and fuel, measured

`libzstd.a`'s linked share grows both binaries and the snapshot; 167 put it at about 0.5 MB of the wheel (INFERRED: no spike built it). `shutil`, `tempfile` (through `shutil`) and `zipfile` now import `compression.zstd` (three enum classes, `_zstdfile`, `compression._common._streams`). A program that imports them pays that; the snapshot pre-imports no package, so a snapshot start pays the same 10.4 M fuel; only the percentage is larger. Before the pull request opens, the builder records the binaries' and the wheel's bytes and the fuel of `import shutil` with no snapshot, and names the fuel checks that move.

The wheel is held under 104,857,600 bytes (the owner's interim line); about 4.5 MB is left, of which 167's Part A takes about 2 MB and 170 about 0.2 MB. If the wheel grows by more than 1.0 MB, the builder stops and asks the owner before merging. If 167's `PYPI_FILE_LIMIT` row is not on `dev` when this merges, criterion 9's recorded bytes are the line's only evidence, and the landing notes say so. The news file claims each growth.

## Intent

`compression.zstd`, `tarfile`'s and `zipfile`'s zstd modes, `shutil`'s `zstdtar` and pandas' `compression="zstd"` work in the guest, and write native's bytes where native writes through libzstd.

## Design

- Recipe: `downloads/SHA256SUMS`, `scripts/00_download.sh`, `scripts/steps/35_stdlib_libs.sh`, `scripts/steps/60_link.sh`, `scripts/assemble_artifacts.py`, `recipes/reactor_bootstrap.py`, `recipes/snapshot-packages.txt`.
- Patch: `recipes/patches/pandas-3.1.0/0002-zstd-from-the-standard-library.patch` and its draft.
- Judge: the job and its `.expected`; `tests/harness/jobs.py`, `paths.py`, `pins.py`, `needs.py`; two check files; `tests/upstream/` as the run shows; `tests/unit/test_artifact_rules.py`'s synthetic set; the workflow's count.
- Documents: `docs/reference/limitations.md`, `docs/reference/packages.md`.

## Scope

In: Decisions 1 to 8. Out: zstd's threads; legacy frames; the `zstd` command-line tool; a `zstandard` module of any kind.

## Acceptance criteria

1. The pin's SHA-256 matches the release's `.sha256` asset and the signature checks, the key's fingerprint recorded (EXECUTED, in the landing notes).
2. Before the pull request opens, the builder sweeps the headers of every compiled file (`Copyright|licen[cs]e`). Any licence beyond BSD-3-Clause and divsufsort's MIT goes to the owner first (EXECUTED, the list in the landing notes).
3. `test_stdlib_c_modules_are_builtin` with `_zstd` is seen failing first on the old set, and passes on both binaries.
4. `test_zstd_files_job_matches_native` passes, its golden from the oracle (`tests/jobs/regen.py --check`).
5. The pandas guest check is seen failing first without the patch; it passes with it.
6. `test_source_tree_matches_its_tarball` passes for zstd and for the patched pandas tree; `test_carried_patches_follow_the_rules` passes with the draft.
7. `test_zstd` runs in `cpython-b`, and the zstd cases in the groups Decision 5 names, their passes counted; every new expected item names its reason; `test_every_package_names_its_own_suite` passes.
8. The tarball's top-level order is recorded, and the artifact-set checks pass with `LICENSES/zstd.txt` (with `TOP_LICENCE` if `COPYING` comes first), the `zstd 1.5.7` package line and its `x-snapshot-package` line.
9. The bytes and fuel of Decision 8 are recorded, the wheel under 104,857,600 bytes and its growth at most 1.0 MB or the owner asked, each growth claimed (EXECUTED).
10. The fast tier, `tests/lint` and the pull request's `ci-status` are green; the x86-64 `same-bytes` run that follows is green.

## Landing notes

Built 2026-10-31 by an agent (Claude Opus 5.5), a builder sub-agent of the orchestrating session, on `spec/169-zstd-built-in` from `dev` at `1c36543d`. The set was built whole from the pins in its own worktree (`scripts/build.sh`, 35 min), first without the pandas patch, then `--from 50` with it. Everything below is EXECUTED on an arm64 Mac (Darwin 25.5.0) unless marked.

**pandas 3.1.0 is not on `dev` yet** (#71 is open), so the patch is against pandas 3.0.6, `recipes/patches/pandas-3.0.6/0002-zstd-from-the-standard-library.patch`. Whichever of the two lands second rebases: the patch and its draft move to `pandas-3.1.0/`, re-made against 3.1.0's `io/common.py` (the branch is the same code at lines 914-924), and `tests/fixtures/upstream-stages.json`'s python digest is recomputed.

**The pin** (criterion 1): `zstd-1.5.7.tar.gz`, SHA-256 `eb33e51f49a15e023950cd7825ca74a4a2b43db8354825ac24fc1b7ee09e6fa3`, equal to the release's own `zstd-1.5.7.tar.gz.sha256` asset. Its `.sig` asset is a good signature (`gpg --verify`, a throwaway keyring) by "Zstandard Release Signing Key <signing@zstd.net>", RSA 4096, created 2021-03-09, fingerprint `4EF4 AC63 455F C9F4 545D 9B7D EF8F E995 28B5 2FFD`. The key was read from keyserver.ubuntu.com (keys.openpgp.org has none for it); zstd's own release workflow signs with `--sign-with signing@zstd.net` (`.github/workflows/publish-release-artifacts.yml`, READ). The oracle's libzstd is 1.5.7 on 3.15.2 too (the job's second line).

**The tarball's top level** (criterion 8, Decision 6), in its order: `.buckconfig`, `.buckversion`, `.cirrus.yml`, `.gitattributes`, `.gitignore`, `CHANGELOG`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `COPYING`, `LICENSE`, `Makefile`, `Package.swift`, `README.md`, `SECURITY.md`, `TESTING.md`, then the folders. `COPYING` (GPLv2) comes first, so `tests/harness/paths.py` gains `TOP_LICENCE = {"zstd": "LICENSE"}`, read by `_top_level_licence` in place of the first match. `LICENSES/zstd.txt` holds `LICENSE` and `lib/dictBuilder/divsufsort.c`'s head comment (Yuta Mori's MIT words, through `head_notice`); GPLv2's text does not ship. The unit row `test_zstds_notice_holds_the_bsd_licence_the_set_takes_not_gplv2` failed before `TOP_LICENCE` (it wanted `COPYING`'s text) and passes with it.

**The header sweep** (criterion 2): every `.c` and `.h` under `lib/common`, `lib/compress`, `lib/decompress` and `lib/dictBuilder`, and the three installed headers, grepped for `Copyright|licen[cs]e`. 68 files carry zstd's dual notice (BSD-style `LICENSE` or GPLv2 `COPYING`, at the user's option), with three copyright holders: Meta Platforms (64 files), Yann Collet - Meta Platforms (`xxhash.c`, `xxhash.h`) and Tino Reichardt (`threading.c`, `threading.h`, the same dual notice). The other two, `divsufsort.c` and `divsufsort.h`, are Yuta Mori's MIT. Nothing beyond the approval.

**Step 35**: 30 C files, as Decision 2 inferred, no two sharing a basename; the step stops on any other count. `libzstd.a` is 616,644 bytes; no compiler warning. The flags add `-ffile-prefix-map`, as qhull's compile has it: zstd's error macros can name `__FILE__` at debug levels.

**Seen failing first**: `test_stdlib_c_modules_are_builtin` fails on both binaries of 165's set (`['_zstd']`) and passes on this set's (criterion 3). `test_pandas_zstd_reads_and_writes_through_the_standard_library` fails on the set built without the patch (pandas' missing-dependency `ImportError`, "`Import zstandard` failed", from `get_handle`) and passes with it (criterion 5). `test_zstd_files_job_matches_native` passes: the guest writes the oracle's bytes at levels 1, 3 and 19, for the trained dictionary (its ID and content) and the frame written with it, the 4 KiB stream, `tar.zst` and the `ZIP_ZSTANDARD` member (criterion 4). The golden was written by the oracle under hash seeds 0 and 1, which agreed, and `tests/jobs/regen.py --check` passes: every job reproduces.

**pandas upstream** (Decision 4): pandas' `main` (`d834961c`, 2026-10-30) has no `compression.zstd` path, so nothing is backported. Issue pandas-dev/pandas#62365 asks for one and is open, unanswered by a maintainer; the draft says so and points the owner at the issue.

**Trees and rules** (criterion 6): `test_source_tree_matches_its_tarball[zstd]` and `[pandas]` pass; `test_carried_patches_follow_the_rules` passes with the draft and the README's count at 30. The release workflow's tree count is 31.

**CPython's suites** (criterion 7), against the accepted record at `30566232` (before 165): `cpython-b` 9,573 to 9,687 passes (`test_zstd` runs, no expected class), 296.7 G to 302.8 G of 490 G; `cpython-archives` 1,336 to 1,505 passes (the zstd cases of `test_tarfile`, `test_zipfile`, `test_zipfile64` and `test_zipimport`), 167.8 G to 172.1 G of 250 G; `cpython-fs` 3,738 to 3,739 (`test_shutil`'s), 64.1 G to 64.3 G of 100 G. No test failed. `test_zipimport`'s two Zstandard ZIP64 tests skip for want of `largefile`, as their kin do, so `cpython-archives` named them as in no release list; they join `cpython-release-archives.txt`, which then ran out of its 150 G. Measured with them: 6 passes, 248.9 G (99.7 G before), so its cap is 380 G, 1.5 times the measure, a judge change with this reason. Its shard, `upstream-release-001`, was 10.4 minutes; upstream-release-001 is estimated at 11.1 to 11.4 judge minutes (149 G at 145 to 207 G a minute), about 17 on the weekly x86-64 runs; the release pull request's run re-measures it, and a figure past twelve repacks it (INFERRED). `test_every_package_names_its_own_suite` passes with `[package.zstd]` reached through `compression.zstd`.

**Size and fuel** (criterion 9), against 165's set (dev at `28a1e7cf`): `python.wasm` 99,492,553 to 99,977,838 bytes (+485,285); `python-snapshot.wasm` 104,660,252 to 105,151,156 (+490,904); the zip 54,960,042 to 54,960,419 (+377, the patch; `compression.zstd` was already in it). **The wheel**, built by hand from each set as the release workflow builds it: 99,478,846 to 99,729,163 bytes (+250,317), under the 1.0 MB stop and 5,128,437 under 104,857,600. 167's `PYPI_FILE_LIMIT` row is not on `dev`, so these recorded bytes are the line's only evidence until it is. Fuel, plain then snapshot: `-c pass` unchanged (277.6 M, 54.2 M); `import shutil` 410.0 M to 420.4 M (+2.54%) and 85.2 M to 95.6 M (+12.2%); `import tempfile` +2.30% and +8.4%; `import zipfile` +1.49% and +4.5%; `import pandas` +0.08% and +0.16%. The snapshot pre-imports no package, so a snapshot start pays the import of `compression.zstd` (three enum classes, `_zstdfile`, `compression._common._streams`) like a plain one. The fuel checks that move are those whose program imports `shutil`, `tempfile` or `zipfile` (regrtest, the upstream drivers, pandas); the news file claims them as `tests/checks/*`, and the release ledger's block claims every upstream group, since each pytest-driven guest imports `shutil`.

**Local runs**: `ruff` clean; `tests/lint` green; the fast tier green but `test_carried_patches_follow_the_rules`, run before the news file existed, and `test_every_other_family_stages_what_it_staged_before`, whose python digest the new release list moves (recomputed in `tests/fixtures/upstream-stages.json`); both pass now. Blocked as on `dev`: prior-art clones, three systems, wheel.
