# 090 — the build and its artifact checks agree on one litter list

- **Status:** **built 2026-10-20**, on `spec/090-the-build-ignores-host-litter` from main
  `e00d394` (drafted with 089 on `3866f56`; revised against its pre-build review and confirmed
  ready, 2026-10-19). Its release run is read below. Build-class and a judge change, so a fresh
  agent reviews the build before it lands (§5.6).
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** **build-class** (§5.7): it touches `scripts/` and `release/`. **And a judge change:**
  the lane accepts with `--accept-judge`. Files: `scripts/litter.py`, `scripts/make_stdlib_zip.py`,
  `scripts/assemble_artifacts.py`, `scripts/steps/20_cpython.sh`, `release/version.py`,
  `tests/harness/paths.py` (`OS_LITTER`, `is_litter`, `has_litter`), `tests/harness/litter.py`
  (its own `LITTER_NAMES` goes; `unrecorded`), `tests/harness/artifacts.py` (`sums_errors`,
  `wheel_errors`), `tests/harness/regrtest.py` and `tests/harness/upstream.py` (`stage`'s
  `left_out`), `tests/harness/pins.py` (`tree_drift`), `tests/harness/scan.py` (the patch rules),
  the repo's `.gitignore`, the README's Mac note, `CHANGELOG.md`, and their unit rows. With no
  litter present the artifact set is the same but for the `recipe` lines this spec moves
  (criterion 2).
- **Depends on:** spec 018 (the build's three-name litter set), which it widens, and spec 089
  (landed, `45b917c`), whose `litter.is_litter` it makes the one shared rule.
- **Research it stands on:** `../research/2026-10-19-ds-store-in-the-judges-stages.md`, §2 (a
  read-only survey of every place the build walks, copies, hashes or zips a folder).

## The problem

macOS writes `.DS_Store` files into `build/` while a build runs (the memo, §1;
`../research/2026-10-17-finder-litter-breaks-a-desktop-build.md`). Spec 018 made the build skip
three names: `.DS_Store`, `Thumbs.db`, `desktop.ini`. Five gaps remain (READ, the memo's §2, and
the pre-build review):

- **AppleDouble `._x` files and `Icon\r` pass every filter** (INFERRED: the memo decoded only
  `.DS_Store` files; on APFS Finder writes `._x` only onto volumes without extended attributes,
  such as exFAT or SMB, and `Icon\r` only for a folder given a custom icon). A `._x` would become
  a zip member or a `SHA256SUMS` line; `._x.py` would fail the zip's compile step. Volume folders
  such as `.TemporaryItems/` are not pruned at all: a file inside one would be packed.
- **`release/version.py`'s `write_assets` walks `build/artifacts` with no filter**, so a
  `.DS_Store` there enters the release tarball. It runs on CI (`release.yml`), where no desktop
  writes; the gap is a local `version.py assets`, and the principle that a consumer of a set takes
  the set's list.
- **The judge's `sums_errors` and `wheel_errors` fail on a `.DS_Store` in `build/artifacts`** (the
  README's documented case), though the set's list never names it.
- **Step 90's untracked-file check and `paths.dirty_path` ignore `.DS_Store` only through the
  owner's global git ignore**, so on another Mac they stop on it.
- **The CPython groups' `left_out` fact records a host Python's bytecode**, and so differs between
  two trees built from the same pins. Spec 078's lane met it: sameness between the lane's record
  and the reviewer's differed on three `Lib/test/__pycache__` files in the main tree's
  `build/Python-3.15.0`, and the landing stopped until they were moved aside (078's landing notes,
  "Sameness"). Every rebuild of step 20 writes them back (READ, below). They are not desktop
  litter: the build writes them itself.

**Why `PYTHONDONTWRITEBYTECODE=1` does not stop them** (READ: file times in the main tree's
`build/Python-3.15.0` after the wave-02 rebuild, and the two Makefiles' command lines; which
process wrote each file is INFERRED from the times). `common.sh` exports the variable, and two
writers never see it:

1. The native build-Python's own `make all` runs it as `$(PYTHON_FOR_BUILD)`, which is
   `./python.exe -E`, and `-E` makes Python ignore every `PYTHON*` variable. 121 caches outside
   `Lib/test` were written at 22:51:48–59, starting the second `python.exe` was linked (22:51:48):
   `site`, `encodings`, `sysconfig/__main__`, `_osx_support`, `json`, `zoneinfo`.
2. The WASI half's `make pythoninfo` (CPython's `Platforms/WASI/_build.py`,
   `pythoninfo_wasi_python`) runs `python.wasm` under wasmtime with `--dir <checkout>::/` and no
   `--env`. wasmtime passes a guest no host variable it is not told to, so the guest writes caches
   into the mapped checkout: 45 files at 22:53:20–21, the step's last second, all eleven under
   `Lib/test` among them (`test_socket`, `pythoninfo`, `support/*`, `libregrtest/utils`). The
   native half's own `pythoninfo` runs without `-E` and inherits the variable, so it writes none.

## Principle

Litter is never an input, so a walk that collects inputs skips it. A consumer of a set takes the
set's list, not its folder. A check that compares a folder with its list ignores litter names, and
only those: a real stray file still fails it. A fact records only what the pins and the tree's real
extras decide.

## Intent

Nothing a desktop process writes into `build/` changes an artifact's bytes, a release asset or a
recorded fact, and every check that catches a real stray file today still catches it.

## Decisions

1. **One litter definition, two copies.** `OS_LITTER` is `.DS_Store`, `Thumbs.db`, `desktop.ini`,
   `ehthumbs.db`, `Icon\r`, `.Spotlight-V100`, `.fseventsd`, `.Trashes`, `.TemporaryItems`,
   `.DocumentRevisions-V100`, `.apdisk`. `is_litter(name)` is `name in OS_LITTER or
   name.startswith("._")`; `has_litter(rel)` is true when any part of a `/`-separated path is
   litter, as `litter.refuse` already tests. `scripts/litter.py` holds the build's copy and
   `tests/harness/paths.py` the judge's; `tests/harness/litter.py` drops its own `LITTER_NAMES`
   and takes `paths`'. The existing unit check holds the two copies equal, the set and both rules.
2. **The collecting walks use it, and prune litter folders.** `make_stdlib_zip.walk` prunes a
   folder with an `is_litter` name and skips such a file. `assemble_artifacts.drop_litter` removes
   every path under the set with a litter part (a litter folder whole), `listed_files` leaves out
   any path with a litter part, and `licence_files` any `is_litter` name.
3. **The release tarball packs its list.** `write_assets` packs exactly the files the set's
   `SHA256SUMS` names, plus `SHA256SUMS`, and fails on a listed file that is missing. It never
   walks the folder for files. The member order stays exactly as today (folders first, then the
   files in the same `Path` sort), so with no litter the tarball is byte-identical. It guards a
   local `version.py assets`; CI has no desktop writer.
4. **The artifact-folder checks forgive litter names only.** `sums_errors` leaves out any path with
   a litter part; any other unlisted file still fails, naming it. `wheel_errors` does the same for
   the folder's files, and also fails on a wheel member under `wasi_python/artifacts/` that the
   set's `SHA256SUMS` does not list (nor is `SHA256SUMS`), litter or not: the wheel is built with
   `cp -R build/artifacts` (`release.yml`), so a forgiven folder must not mean a forgiven wheel.
5. **`left_out` records neither litter nor bytecode.** The CPython and upstream stages' `left_out`
   lists a build tree's extra files under a staged folder, except a path with a litter part and
   anything under a `__pycache__` folder (`litter.unrecorded`). Neither kind is recorded in any
   fact, so the fact depends only on the pinned tarball and the tree's real extras, and sameness
   between two trees built from the same pins holds. A real extra file (a `conftest.py` a build
   left) is still listed.
6. **Step 20 removes the bytecode it made.** After `Platforms/WASI build`, step 20 removes every
   `__pycache__` folder under `$CP/Lib`, as `common.sh`'s `host_from_source` does for the tools'
   Python. Nothing reads them later: steps 60 and 70 marshal with the tools' Python, after
   `host_from_source`, and the zip skips `__pycache__`. Step 60's `make all` runs the build-Python
   with `-E` again and writes a few caches back outside `Lib/test`; Decision 5 keeps every one of
   them out of the facts.
7. **The repo ignores litter itself.** `.gitignore` gains `.DS_Store`, `._*` and the line `Icon`
   followed by two literal CR bytes (git strips one trailing CR; `Icon[\r]` matches `Iconr`, the
   review's F5). EXECUTED in a scratch clone with this repo's `* text=auto eol=lf`: the line
   survives a commit and a clone, `git check-ignore` matches `Icon\r` and not `Iconr`, and git
   still treats the file as text.
8. **The README's Mac note** says what is left: nothing a desktop writes into `build/` changes an
   artifact or a fact; closing System Settings' Storage pane and Finder windows on the checkout
   stops the writers.

### Every reader of the judge's `OS_LITTER`, and its test after this spec

| reader | today | after | why |
|---|---|---|---|
| `paths.judge_files` (the judge hash) | `f.name not in OS_LITTER` | `not has_litter(rel)` | litter never moves the hash; a litter folder's files neither |
| `pins.tree_drift` (spec 020, `_patched_drift`) | skips a litter name the tarball lacks | skips a path with a litter part the tarball lacks; **and reports a pinned member with a litter part** in both drifts | a real extra or changed file still fails it; a pinned member the build's walks would skip is named instead of silently dropped (Decision 1's guard) |
| `scan.patch_shape_errors` | a touched path whose last part is litter | a touched path with a litter part | a patch may not create what the walks skip |
| `scan.patch_errors` (folders, files, the drafts walk) | skips the three names | skips `is_litter` names; the drafts walk any path with a litter part | Finder's files are not ours |
| `tests/harness/litter.py` (`LITTER_NAMES`, `is_litter`) | its own widened copy | `paths.OS_LITTER`, `paths.is_litter` | one judge copy, not two |
| `guest._place` | `litter.is_litter` | unchanged | already the widened rule |
| `tests/unit/test_scoreboard.py` (the judge-hash row) | plants the three | plants every name a host can create, and `._x.py` | the row follows the set |

The tarball guard replaces the draft's slow scan of every pinned archive (the review's F6): the
tree check already reads every member of all twenty-two trees, so a pin that ships a litter-named
member is caught where its tree is checked, at no extra cost. Today no pinned archive holds one
(the review, EXECUTED over 75 archives).

## Design

`scripts/litter.py` exports `OS_LITTER`, `is_litter` and `has_litter`; `tests/harness/paths.py`
keeps the same three, held equal by the unit check. Each collecting walk replaces its `name in
OS_LITTER` test with `is_litter(name)` and prunes litter folders. `write_assets` reads the set's
`SHA256SUMS` and packs `artifacts / rel` for each listed path and `SHA256SUMS`, sorted as `Path`s,
with their folders first, as now. `sums_errors` and `wheel_errors` drop `has_litter` paths from the
folder's files before comparing; `wheel_errors` compares the wheel's `wasi_python/artifacts/`
members with the list. `litter.unrecorded(rel)` is `has_litter(rel) or "__pycache__" in parts`,
and both stages skip it when they build `left_out`. Step 20 ends with a `find "$CP/Lib" -name
__pycache__ -type d -prune` loop through `remove`.

## Scope

In: Decisions 1 to 8 and the reader table. Out: the judge's stages, grants and seal (spec 089);
a check for files a build adds inside a source tree (still not machine-checked); `release.yml`'s
`find` checks (CI has no desktop writer, and they compare with a list); `gen_inittab.py`'s
`rglob("*" + SUFFIX)` and `60_link.sh`'s `find -name "*.cpython-…so"`, which would take a
`._x.cpython-315-wasm32-wasi.so` for a module and fail loudly (a wrong symbol, a failed link),
never silently, and which see only build outputs (out; INFERRED, no `._x` file was ever seen).
`tree_drift` skips the widened names and the `._` prefix too, and names a pinned litter member; a
real extra or changed file still fails it.

## Acceptance criteria

1. **The checks fail first.** On the base `e00d394`, before the code: the widened-litter rows
   (the zip walk, step 90's drop and list, both copies equal), the release tarball's list rows,
   the artifact checks' litter rows (`sums_errors`, `wheel_errors`), the `left_out` rows of both
   stages, the tree-drift guard row and the `.gitignore` row fail. So does the judge-hash row,
   which now plants `._test_a.py` and a litter folder; the litter-name rows 089 already widened
   pass on the base and keep passing.
2. **The same bytes, but for the moved recipe lines.** A rebuild from pins with no litter present
   matches main's set at the build's base (`e00d394`, whose recipes are those of the set the lane
   accepted at `b0c7a74`, `SHA256SUMS` `2b0480af…`), checked with `cmp`: `python.wasm`,
   `python-snapshot.wasm`, `python-stdlib.zip` and every `LICENSES/*` file are byte-identical.
   `MANIFEST` differs exactly in the `recipe` lines of the files this spec edits under `scripts/`
   (`scripts/litter.py`, `scripts/make_stdlib_zip.py`, `scripts/assemble_artifacts.py`,
   `scripts/steps/20_cpython.sh`), and `SHA256SUMS` exactly in `MANIFEST`'s line. The judge's
   `bytes` metrics do not move. With no litter, `version.py assets` gives the same tarball bytes
   as before (same members, same order). If 086 lands first, the base is 086's set, and the same
   comparison holds against it.
3. **Litter planted.** With `._x.py`, `Icon\r`, `.DS_Store` and a `.TemporaryItems/x.py` planted in
   `build/pandas-install` and `build/artifacts/LICENSES` before steps 70 to 90 and the release
   step: the same set, and a release tarball whose members equal `SHA256SUMS`' list plus itself.
   Unit rows plant the same names in each walk.
4. **A real stray file still fails.** A planted `stray.py` in `build/pandas-install` enters the zip
   and fails the same-bytes gate; a planted `stray.bin` in `build/artifacts` fails `sums_errors`,
   naming it; a wheel member the list does not name fails `wheel_errors`, naming it; a
   `conftest.py` a build left under a staged folder stays in `left_out`.
5. **No bytecode from step 20.** After a rebuild, `find build/Python-3.15.0/Lib/test -name
   __pycache__` finds nothing (step 60's `-E` runs may write caches outside `Lib/test`; Decision 5
   keeps them out of the facts either way).
6. **The judge.** `ruff` green; the fast tier `-n 3` against a private copy of the reviewed set: no
   failure, no lost pass, no fuel moved, `judge changed` naming exactly the judging files above.
   The full judge is the release workflow on the branch (the wave rules: no local full run):
   every red line is GREW, G7, or one main already carries; and in its records (`gh run download
   <id> -D build/090/ci/`) every `cpython-*` and upstream `left_out` fact holds no `__pycache__`
   or litter path. The `left_out` fact is written only by the slow `test_upstream_suite`, so the
   fast tier never records it (the confirmation's Low).

## For the lane

**What this claims**, each for the build review to check (each line starts "090:"):

- 090: the artifact set is unchanged but for MANIFEST's four `recipe` lines and SHA256SUMS's
  MANIFEST line (criterion 2, EXECUTED below); no `bytes` metric moves.
- 090: no goal check is new, retired or changed in verdict; the unit suite gains six rows
  (`test_build_scripts.py` 1, `test_release_version.py` 2, `test_artifact_rules.py` 2,
  `test_pins.py` 1) and changes eight existing ones.
- 090: no row grows and no pass moves: no `--accept-growth`, no `--accept-fewer-passes`, no
  `--retire`.
- 090: the judge hash changes in fifteen files: `tests/harness/artifacts.py`, `litter.py`,
  `paths.py`, `pins.py`, `regrtest.py`, `scan.py`, `upstream.py`, and
  `tests/unit/test_artifact_rules.py`, `test_build_scripts.py`, `test_patches.py`,
  `test_pins.py`, `test_regrtest.py`, `test_release_version.py`, `test_scoreboard.py`,
  `test_upstream.py`. Not judged but changed: `scripts/litter.py`, `scripts/make_stdlib_zip.py`,
  `scripts/assemble_artifacts.py`, `scripts/steps/20_cpython.sh`, `release/version.py` (so
  build-class), `.gitignore`, `README.md`, `CHANGELOG.md`.
- 090: the CPython and upstream `left_out` facts no longer hold `__pycache__` or litter paths, so
  the lane's sameness no longer differs on them (078's stop); a fact that held only those is now
  `[]`. The lane's main-tree `build/Python-3.15.0` keeps the old bytecode until step 20 runs
  again; the judge leaves it out either way.
- 090: the tree check (`test_source_tree_matches_its_tarball`) now names a pinned member with a
  litter name; none of the twenty-two trees has one (the release run's build job, 22 passed).

**The flags**, each pasted as is:

```
--accept "090: one litter list for the build and the judge (.DS_Store, AppleDouble ._x, Icon\r, Thumbs.db, desktop.ini, ehthumbs.db, a volume's folders); the release tarball packs the set's list; step 20 removes the bytecode CPython's build writes into Lib; the artifact set unchanged but for four MANIFEST recipe lines"
--accept-judge "090: sums_errors and wheel_errors forgive litter paths only and the wheel may carry nothing SHA256SUMS does not list; left_out records neither litter nor __pycache__; paths.OS_LITTER widened with is_litter and has_litter, held equal to scripts/litter.py, used by judge_files, tree_drift (which now names a pinned litter member) and the patch rules; harness litter.py takes paths' list"
```

## Disposition of the pre-build review (2026-10-20)

The review: `../reviews/090-the-build-ignores-host-litter-spec-2026-10-20.md`, on main `e00d394`.
Verdict: "ready once F1, F2 and F3"; the Lows are fix text the builder takes in writing. Every
finding is taken. The reviewer's confirmation (in the same file): "Ready to build", with one Low,
taken below.

- **F1 (High), `left_out` would keep recording bytecode, and litter listed apart is still
  recorded.** Taken. Decision 5 rewritten: `left_out` records neither a litter path nor anything
  under `__pycache__` (`litter.unrecorded`), so the fact depends only on the tarball and the
  tree's real extras. A problem bullet cites 078's landing note. Unit rows in both stages: a tree
  holding `Lib/test/__pycache__/x.cpython-315.pyc`, `Lib/test/.DS_Store` and `Lib/test/extra.py`
  gives `left_out == ["Lib/test/extra.py"]`, and the same shape for `upstream.stage`. The optional
  part is taken as Decision 6: step 20 removes `Lib/**/__pycache__` after its build. The cause is
  settled as far as READ allows (*The problem*, "Why `PYTHONDONTWRITEBYTECODE=1` does not stop
  them"): the native build-Python runs as `python.exe -E`, which ignores the variable, and the
  WASI guest under wasmtime is given no host variable at all. It is a judge change (F3).
- **F2 (Medium), criterion 2 could not pass as written.** Taken, in the review's words: the three
  binaries and every licence file byte-identical; `MANIFEST` differs exactly in the edited
  scripts' `recipe` lines (four now, with step 20), `SHA256SUMS` exactly in `MANIFEST`'s line;
  the `bytes` metrics do not move; the tarball is the same with no litter. The base is named
  (`e00d394`, the set accepted at `b0c7a74`), and 086's set if 086 lands first. The Kind line no
  longer says "byte-identical".
- **F3 (Medium), an undeclared judge change, and `paths.OS_LITTER`'s other readers.** Taken. The
  Kind line declares the judge change and `--accept-judge`; *For the lane* will carry the exact
  flag. The reader table names all seven readers with their test after this spec; the Scope's 020
  line is rewritten.
- **F4 (Low), the wheel.** Taken as Decision 4's second half: `wheel_errors` fails on a wheel
  member under `wasi_python/artifacts/` the list does not name, litter or not.
- **F5 (Low), `Icon[\r]`.** Taken (Decision 7), with the unit row (`git check-ignore` on `Icon\r`,
  with the user's own excludes file switched off, so the owner's global ignore cannot pass it).
  The row skips on Windows, whose file names cannot hold a CR.
- **F6 (Low), the slow tarball scan.** Answered: replaced by the tree check's guard (the reader
  table), which reads every member already, so nothing slow is added. Its unit row (a synthetic
  tarball with a `._x` member) fails first; a real pin with such a member would fail the tree
  check where its tree is checked.
- **F7 (Low), litter folders not pruned.** Taken (Decision 2; `has_litter` everywhere a path is
  tested).
- **F8 (Low), INFERRED gaps and two more globs.** Taken: the `._x` and `Icon\r` gaps are labelled
  INFERRED; `gen_inittab.py` and `60_link.sh` are named out of scope, with the reason.
- **F9 (Low), Decision 3's motivation and order.** Taken: it guards a local `version.py assets`;
  the member order is stated as unchanged; `test_release_version.py` gains planted litter and a
  missing listed file.
- **The confirmation's Low (criterion 6 lacked a full run).** Taken: criterion 6 reads the
  `left_out` facts in the branch's release run records, which are this build's full judge.
- **F10 (Low), a stale Status and Files.** Taken: 089 is a landed dependency;
  `tests/harness/litter.py` is in Files and its copy goes, so there are two copies, not three; the
  Status names `e00d394`.

## Landing notes

### What was built

- `scripts/litter.py`: `OS_LITTER` widened to eleven names, `is_litter`, `has_litter`.
  `make_stdlib_zip.walk` prunes litter folders and skips litter files; `assemble_artifacts`'s
  `drop_litter` removes litter files and folders, `listed_files` leaves out any path with a litter
  part, `licence_files` any litter name. `scripts/steps/20_cpython.sh` removes every
  `__pycache__` under `$CP/Lib` after the driver's build, with the cause in a comment.
- `release/version.py`: `set_files` reads the set's `SHA256SUMS` (refusing a missing file or a
  path outside the set) and `write_assets` packs those files and `SHA256SUMS`, in the old order.
- The judge: `paths.OS_LITTER`, `is_litter`, `has_litter` (the second copy);
  `tests/harness/litter.py` takes them and adds `unrecorded`; both stages' `left_out` skip it;
  `sums_errors` and `wheel_errors` forgive litter paths only, and `wheel_errors` names a wheel
  member the list does not; `judge_files`, `tree_drift` and the patch rules use the shared rules,
  and `tree_drift` names a pinned litter member. `.gitignore`, the README's Mac note and the
  CHANGELOG (under 0.1.0a8).

### Seen failing first (EXECUTED)

The checks commit `eb51d73`, before any code, extracted to a scratch tree and run with this
worktree's environment (`build/090/first-fail.log`): 16 failed, 334 passed, 1 skipped: the zip
walk, step 90's drop and list, the two copies equal, the repo's ignores, both assets rows, both
artifact-rule rows, both stages' `left_out` rows, the pinned-member row, the three patch rows and
the judge-hash row. Each failed on the behaviour (litter packed, listed or recorded; a missing
rule), except the wheel row, which failed first on the helper it calls (`paths.has_litter`, not
there yet).

### The rebuild (EXECUTED, darwin-arm64; `build/090/build.log`, 16 steps in 7 m 43 s)

- **Criterion 2.** Against main's set (the main tree's `build/artifacts`, `SHA256SUMS`
  `2b0480af…`, whose `recipe` lines equal `e00d394`'s files): `python.wasm` (`cef11d8d…`),
  `python-snapshot.wasm` (`ab114823…`), `python-stdlib.zip` (`f7d96aab…`) and all 60
  `LICENSES/*` files are `cmp`-identical. `MANIFEST` differs in exactly four `recipe` lines
  (`scripts/assemble_artifacts.py`, `scripts/litter.py`, `scripts/make_stdlib_zip.py`,
  `scripts/steps/20_cpython.sh`), `SHA256SUMS` in exactly `MANIFEST`'s line; the new set's
  `SHA256SUMS` is `9e291bba…`. The release tarball from `e00d394`'s `version.py` and from this
  one, on the same set, is the same bytes (`f1c235cf…`).
- **Criterion 5.** After step 20, `find build/Python-3.15.0/Lib -name __pycache__` finds 0.
- **Criterion 3.** With `._x.py`, `Icon\r`, `.DS_Store` and `.TemporaryItems/x.py` planted in
  `build/pandas-install`, `build/pandas-install/pandas` and `build/pandas-3.0.6/LICENSES` (a
  licence input), steps 70, 80 and 90 gave the same set (`diff -r` empty). The same names planted
  in `build/artifacts` and `build/artifacts/LICENSES`: the release tarball is the same bytes,
  its 65 members equal `SHA256SUMS`' list plus itself, and `sums_errors` is `[]`.
- **Criterion 4.** A planted `build/artifacts/stray.bin`: `sums_errors` is `["stray.bin is not
  listed in SHA256SUMS"]`. A planted `build/pandas-install/pandas/stray.py`: step 70's zip holds
  3682 `.pyc` (one more, `pandas/stray.pyc`) and differs from the set's. Steps 70 to 90 again
  without it restored the clean set; the planted litter was then removed.

### The judge (no `--accept`)

- `uv run ruff check src tests` and `ruff format --check src tests`: green. The unit suite
  (`-n 3`): 1723 passed, 14 skipped.
- **The fast tier**, `uv run pytest -m "not slow" -n 3` on `fa34179` plus the row fix `e90105c`,
  against this worktree's rebuilt set (`build/090/fast.log`): 577/701 pass, 0 gap, 3 blocked, 0
  fail (unit suite 1737/1744, 7 skipped); ratchet vs `2bb98c8`: lost 0, gained 0, grew 0;
  `judge changed` the fifteen files named in *For the lane*. The judge hash is `0d56263c…`.
- **The release run** 39366660896 on `e90105c` (the full judge, under the wave rules): every
  job green on all three systems but one, `judge (windows-2025, own-embedding)`, whose only red
  lines are main's two known Windows reds that spec 094 fixes:
  `test_the_removal_never_deletes_what_the_guest_may_not[home]` and `[private]` ("skipped
  without a known need", spec 084, C2); lost 2 there, gained 0, grew 0. No GREW line, no G7 line:
  the gather was skipped because that shard failed. `rebuild from the pins` on both Linux hosts,
  `the same bytes from every host` and the build job (its tree check: 22 passed, so no pinned
  member has a litter name) are green.
- **Criterion 6's facts.** The run's records (`gh run download 39366660896 -D build/090/ci/`, 19
  records): 20 `left_out` facts on 16 nodes, all five `cpython-*` groups among them; none holds a
  `__pycache__` or litter path, and every one is `[]`.

One line: the build skips one shared litter list, the release packs its list, the artifact checks
forgive litter names only, and `left_out` records neither litter nor bytecode, so a desktop's
files never change an artifact or a fact and a real stray file still fails.
