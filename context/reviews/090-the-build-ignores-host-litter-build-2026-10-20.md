# Review of 090 — the build and its artifact checks agree on one litter list (build review)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude Opus 5.5), which wrote neither the specification, its
  pre-build review nor the build.
- **Reviewed:** `spec/090-the-build-ignores-host-litter`, `e00d394..a4ab975` (my write-in on top: `125b063`) (code at `e90105c`;
  `a4ab975` adds only the landing notes), worktree `wasi_python-090`.
- **Time box:** 40 minutes (build-class and a judge change).
- **Run:** the builder's release run 39366660896 on `e90105c`, read (no run of my own was
  dispatched: the brief asked me to read this one; `a4ab975` differs from `e90105c` only in the
  specification file).
- **Re-ran:** each run only after checking that the main tree's `build/lane.lock` was absent (it was held
  by wave 04's accept until 00:24 EDT; I waited). Logs in the worktree's `build/090/review/`.
  - `uv run pytest -n 3` on the nine changed or litter unit files (`test_artifact_rules`,
    `test_build_scripts`, `test_patches`, `test_pins`, `test_regrtest`, `test_release_version`,
    `test_scoreboard`, `test_upstream`, `test_host_litter`) → 351 passed, exit 0.
  - **Mutation 1:** `litter.unrecorded` without its `__pycache__` clause → both stages' rows fail
    (`test_regrtest.py::test_the_stage_is_the_tarballs_bytes_and_lists_what_the_tree_adds`,
    `test_upstream.py::test_a_stray_file_is_not_staged_and_is_listed`), exit 1; file restored.
  - **Mutation 2:** `wheel_errors` without its list comparison →
    `test_artifact_rules.py::test_a_wheel_carries_the_list_and_nothing_else` fails, exit 1;
    restored. `git status` clean after both.
  - **Probe:** `tests/checks/test_v1_1_artifact_set.py::test_sha256sums_match_the_files` against a
    private copy of the worktree's set (`WASI_PYTHON_ARTIFACTS`) with `.DS_Store`,
    `LICENSES/._zlib.txt`, `Icon\r` and `.TemporaryItems/x` planted → passed; with `stray.bin`
    added → FAIL, "stray.bin is not listed in SHA256SUMS".
  - `tests/checks/test_rules.py -m "not slow" -n 3` after my write-in commit → 43 passed, 1 skipped.
  - `ruff check src tests scripts/litter.py release/version.py`, `ruff format --check src tests` →
    green.

## Acceptance criteria against evidence

1. **The checks fail first** — met. READ `build/090/first-fail.log`: 16 failed, 334 passed,
   1 skipped on `eb51d73`; the 16 are exactly the rows criterion 1 names (the zip walk, step 90's
   drop, list and licences, the two copies equal, the repo's ignores, both assets rows, both
   artifact-rule rows, both stages' `left_out` rows, the pinned-member row, the three patch rows,
   the judge-hash row).
2. **The same bytes, but for the moved recipe lines** — met, READ (the landing notes and
   `build/090/build.log`): three binaries and 60 licence files `cmp`-identical to `2b0480af…`;
   `MANIFEST` differs in four `recipe` lines, `SHA256SUMS` in `MANIFEST`'s line; the tarball the
   same bytes from both `version.py`s. CI's `the same bytes from every host` and both `rebuild from
   the pins` jobs green on `e90105c` (READ). To be redone against 086's set at the wave's rebase.
3. **Litter planted** — met, READ (`build/090/planted.log` and the landing notes); the unit rows
   plant the same names in each walk (EXECUTED, below).
4. **A real stray file still fails** — met: `stray.bin` named by `sums_errors` and `stray.py`
   changing the zip are READ (`build/090/stray.log`); the wheel row and the `conftest.py` row are
   EXECUTED below.
5. **No bytecode from step 20** — met, READ (the landing notes: 0 `__pycache__` under `Lib` after
   step 20). The step's `find … -prune | while read -r d; do remove "$d"; done` uses `common.sh`'s
   `remove` (sourced through `remove.sh`), the same loop `host_from_source` already runs.
6. **The judge** — met, with finding 1. `ruff check`/`format --check` green (EXECUTED). The fast
   tier READ (`build/090/fast.log`: lost 0, gained 0, grew 0, `judge changed` fifteen files). The
   release run READ: every job green but `judge (windows-2025, own-embedding)`, whose only reds are
   `test_the_removal_never_deletes_what_the_guest_may_not[home]` and `[private]` ("skipped without
   a known need", spec 084 C2; 094 has fixed them on main); no GREW, no G7 (the gather was skipped).
   The records in `build/090/ci/` EXECUTED with a script: 20 `left_out` facts on 16 nodes, all
   five `cpython-*` groups among them, every one `[]`.

## The judge changes against AGENTS rule 4

Each change was read for a case where it would hide something real.

- **`litter.unrecorded` (`left_out`).** Both stages test membership first (`rel in allowed` /
  `rel not in names`), so a pinned member under `__pycache__` or with a litter name is still
  staged; only a tree's *extra* file is dropped from the list. `left_out` feeds one place,
  `fact("left_out", …)` in `tests/checks/test_v1_3_upstream_suites.py:82`: a fact, never a verdict,
  so no check turns green through it. What it now hides is an extra file under a `__pycache__`
  folder that is not bytecode, which no build writes; acceptable, and named in finding 4.
- **`tree_drift`.** Strictly stronger but for one path: in `_patched_drift` a path with a litter
  *part* that the tarball does not hold is skipped, where only a litter *name* was. Such a path
  can come only from an OS writing into the judge's own extraction, or from a recorded patch, and
  `scan.patch_shape_errors` now refuses a patch that touches any path with a litter part. A pinned
  member with a litter part is newly reported in both drifts, after which the usual comparison
  still runs (spec 026's row now expects both lines). Nothing that drifted before passes now.
- **`sums_errors` / `wheel_errors`.** A litter path in `build/artifacts` is forgiven by
  `sums_errors`; a wheel built from that folder (`cp -R` then hatchling's `artifacts =
  ["src/wasi_python/artifacts"]`, which includes files whatever `.gitignore` says) would carry it,
  and `wheel_errors` now fails on any `wasi_python/artifacts/` member the list does not name, litter
  or not. The release tarball packs the list. So no shipped asset can carry a forgiven file
  unflagged: the forgiveness is for the folder, not for anything built from it.
- **`judge_files`, the patch rules.** `has_litter` on the whole relative path: a judged file in a
  folder with a litter name, or named `._x`, would leave the hash. pytest does not collect either
  (`norecursedirs` skips dot folders; `._test_x.py` is not `test_*.py`) and neither is importable,
  so no judged behaviour can hide there.
- **Declared.** The `--accept-judge` flag in *For the lane* names `sums_errors`, `wheel_errors`,
  `left_out`, `OS_LITTER` with both rules, `judge_files`, `tree_drift` (naming a pinned member),
  the patch rules and `litter.py`: every behaviour change above. The fifteen judged files it lists
  match the diff and the fast tier's `judge changed` line.
- **The seven readers.** `git grep` on the branch: every litter test in `scripts/` goes through
  `scripts/litter.py`'s `is_litter`/`has_litter`, and every one in `tests/` through
  `paths.is_litter`/`has_litter` (`judge_files`, `pins` both drifts, `scan`'s two wrappers,
  `artifacts._set_folder_files`, `harness/litter.py`'s `is_litter = paths.is_litter` and
  `unrecorded`, `guest._place` through it). `LITTER_NAMES` has no reader left. No reader still
  tests `name in OS_LITTER`. The unit row holds the two sets and both rules equal.

## The rebase onto 086 (and wave 03)

`git merge-tree --write-tree` of `a4ab975` with `c4af3c4` (086's tip) and with `a75e5d4`: one
conflict, `CHANGELOG.md` (both add under `0.1.0a8`); `scripts/steps/20_cpython.sh` auto-merges
(086 changes the driver's command line, 090 adds lines after the `python.wasm` test; read in the
merged tree). No interaction: 086's `_missing_stdlib_info.py` (step 70's `MISSING_INFO`) is read
from `$W/build/lib.wasi-wasm32-3.15/`, outside `$CP/Lib`, so step 20's `__pycache__` removal
cannot touch it; `60_link.sh`'s guard loop and step 70 are files 090 does not edit, and
`make_stdlib_zip`'s `--file` inputs bypass `walk`. 086's `--with-hash-algorithm=siphash13` does
not change bytecode. Wave 03's harness changes (`gather.py`, `needs.py`, `sameness.py`) touch no
file 090 edits. At the wave, criterion 2 is redone against 086's set: `20_cpython.sh`'s `recipe`
line moves under both specs, so `MANIFEST` will still differ in exactly the four lines.

## Findings, most severe first

1. **Criterion 6's CI facts do not tell the fix apart** (Low; the spec's landing notes,
   "Criterion 6's facts") — the 20 `left_out` facts in 39366660896 are all `[]`, but so are the same
   20 in 087's release run (`wasi_python-087/build/087/ci/`, a judge without 090), because CI's
   trees hold none of the bytecode a local tree does. The evidence that the fact is fixed is the two
   stages' unit rows (failing first, and failing under mutation 1) and criterion 5; the lane's
   sameness claim rests on those. **Written in** on the branch, `125b063`.
2. **Decision 7 says "git still treats the file as text"** (Low; the spec, Decision 7) — true for
   `git diff`, not for line-ending conversion: `git ls-files --eol .gitignore` gives `i/-text
   w/-text attr/text=auto eol=lf`, a lone CR making `text=auto` take it for not text. That is what
   keeps the two CRs through a commit and a Windows checkout, so the behaviour is right and only the
   sentence was loose. **Written in**, `125b063`.
3. **The README drops the local-wheel case** (Low; `README.md`, the Mac note; a code-side file, so
   the builder's) — litter in `build/artifacts` no longer fails `sums_errors`, but a wheel built by
   hand with `cp -R build/artifacts src/wasi_python/artifacts` carries it (hatchling's `artifacts`
   takes the folder whatever `.gitignore` says) and `wheel_errors` then names it. Fix text, appended
   to the note: "Before building a wheel by hand from `build/artifacts`, delete any such file
   there (`find build/artifacts -name .DS_Store -delete`): the wheel check names a member the set's
   list does not." No round needed.
4. **Not rebased onto today's main** (Low, the self-check's first item) — the base is `e00d394`;
   main is `f7511b7` and 086 is landing. The rebase onto 086 conflicts only in `CHANGELOG.md`
   (above); criterion 2 is then redone against 086's set, as the spec already says. A wave step, no
   round.
5. **Note: `unrecorded` drops any extra under a `__pycache__` folder, bytecode or not**
   (`tests/harness/litter.py:46`) — `left_out` is a fact only (one writer, no verdict), and pinned
   members are staged before the test, so nothing is hidden from a check. No action.
6. **Note: my single-node runs rewrote the worktree's `build/progress/latest.json`** (00:25 EDT).
   The builder's fast-tier evidence stays in `build/090/fast.log`; the lane judges its own commit.
   If the builder's record is wanted for sameness, re-run the fast tier there.

## Constitution checks

- §4.1 (patches): no patch added; a patch touching any litter part is now refused.
- §4.2 (pins): no input changed; the tree check now also names a pinned litter member.
- uv only: the step uses `$HOSTPY`; tests under `uv run`.
- Tests count operations: no clock read added.
- Artifacts never in git: none tracked; `.gitignore` gains litter only, and no tracked file
  matches `._*`, `.DS_Store` or `Icon\r` (`git ls-files`).
- §7: nothing tripped. The judge is changed openly, with its own flag and reason.

## Verdict

**Lands.** The judge changes hide nothing a check counted: `left_out` is a fact, `tree_drift`
is stronger, and the forgiven litter in the artifact folder cannot reach a shipped asset unflagged
(the wheel check and the tarball's list). Every change is declared in the `--accept-judge` flag. The
readers of the litter list all go through the two held-equal copies. Findings 1 and 2 are written
in (`125b063`); finding 3 is fix text for the builder; finding 4 is the wave's rebase onto 086,
which conflicts only in `CHANGELOG.md`.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Finding 1: written in by the reviewer (`125b063`); the builder agrees. The CI facts confirm only
   that no fact holds bytecode on CI; the two stages' unit rows and criterion 5 are the evidence.
2. Finding 2: written in by the reviewer (`125b063`).
3. Finding 3: taken, in the review's words, at the end of the README's Mac note (the builder,
   2026-10-20).
4. Finding 4: done. Rebased onto main `ebd0449` (086 landed); the one conflict, `CHANGELOG.md`, is
   resolved with both bullets under `## 0.1.0a8 — unreleased`. Not rebuilt here: the lane rebuilds
   the wave tip in the main tree and redoes criterion 2 against 086's set (*For the lane*).
5. Notes 5 and 6: no action.
