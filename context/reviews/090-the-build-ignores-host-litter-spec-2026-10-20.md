# Review of 090 — the build and its artifact checks agree on one litter list (the specification, before build)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I wrote none of 090, 089, the
  memo or the code. Time box: 30 minutes (the lane's). The README sets 45 for build-class work.
- **Reviewed:** the specification as drafted, at main `e00d394`
  (`context/specifications/090-the-build-ignores-host-litter.md`). I read it against main's code
  as it is now, after 039, 041, 073, 085, 087, 089 and 093. 086 is pending in wave 03.
- **Read:** `AGENTS.md`; constitution §5.6, §5.7 and §7; `context/reviews/README.md`; spec 089;
  memo `research/2026-10-19-ds-store-in-the-judges-stages.md` §1, §2 and §5; spec 078's landing
  notes (the `left_out` difference). Code: `scripts/litter.py`, `scripts/make_stdlib_zip.py`,
  `scripts/assemble_artifacts.py`, `scripts/gen_inittab.py`, `scripts/steps/20_cpython.sh`,
  `common.sh`, `60_link.sh` and `70_zip.sh`; `release/version.py`; `.github/workflows/release.yml`
  (lines 70–110 and 300–385); `tests/harness/paths.py`, `artifacts.py`, `litter.py`,
  `regrtest.py` (`stage`), `upstream.py` (`stage`), `pins.py` (`tree_drift`), `scan.py`
  (`patch_shape_errors`, the drafts walk) and `sameness.py`; `tests/checks/test_v1_1_artifact_set.py`;
  `tests/checks/test_v1_3_upstream_suites.py`; `tests/unit/test_build_scripts.py`; and
  `build/Python-3.15.0/Platforms/WASI/_build.py` (CPython's own build script).
- **Run:** none. This reviews a specification, and nothing is built yet. The build review
  dispatches the release workflow.
- **Re-ran (EXECUTED, darwin-arm64).** No pytest tier, and no unit file. `build/lane.lock` was
  absent. Everything I wrote is beside this file:
  - `scan.py` lists the members of every archive in `downloads/` (75 archives). It found 0 members
    with a 090 litter name, and took 53.3 s.
  - In a scratch git repository, a `.gitignore` holding the text `Icon[\r]` ignores a file named
    `Iconr`, not one named `Icon\r`. The form `Icon` followed by two literal CR bytes ignores
    `Icon\r`.
  - Read-only `ls -laT` and `find` in the main tree's `build/`.

## What holds

- **The four build gaps are real as READ.** `make_stdlib_zip.SKIP_NAMES` and
  `assemble_artifacts.drop_litter`, `listed_files` and `licence_files` test `name in OS_LITTER`,
  which holds three names (`scripts/litter.py:5`). `write_assets` packs
  `sorted(artifacts.rglob("*"))` with no filter (`release/version.py:162`). `sums_errors` and
  `wheel_errors` filter nothing (`tests/harness/artifacts.py:45-48`, `:179-186`). The repo's
  `.gitignore` has no `.DS_Store`. Only the owner's `~/.gitignore_global` ignores it, so step 90's
  `git ls-files --others --exclude-standard recipes scripts` (`assemble_artifacts.py:352-371`)
  would stop on one on another Mac.
- **The principle is right.** Walks that collect inputs skip litter. A consumer takes the list.
  A folder-against-list check forgives litter names only.
- **Recipe hashes are safe already.** MANIFEST hashes only `git ls-files recipes scripts`
  (`assemble_artifacts.py:463-473`), so litter there never reaches a hash. Untracked files stop
  step 90 instead.
- **No pinned archive holds a litter-named member today** (EXECUTED: 75 archives, 0 hits). So
  widening the walks' skip list changes no artifact byte when no litter is present.
- **It still applies after 039, 041, 073, 085 and 087.** 039 and 041 add `pure-install` and more
  `--tree` inputs. All of them go through `walk`, so the new rule covers them. 085's `set_sums` is
  the hash of the set's own `SHA256SUMS`, which this spec does not change. 073 and 087 touch
  nothing here.

## Acceptance criteria against evidence (as written)

1. **Checks fail first** — checkable, with one exception. The tarball-scan row (Decision 1) skips
   when `downloads/` is absent, so it cannot be a row that fails first (F6).
2. **Same bytes** — not met as written. MANIFEST and SHA256SUMS must differ (F2).
3. **Litter planted** — checkable as a build experiment (counts and `cmp`, no clock). Unit rows
   with planted files should cover the same paths too (F2's fix text).
4. **A real stray file still fails** — checkable. It holds for `sums_errors`. For the wheel it
   holds only on CI (F4).
5. **The judge** — it does not say this is a judge change, so it cannot be met as stated (F3).

## Findings, most severe first

1. **High — Decision 5 does not fix the `left_out` difference the lane hit, and it would keep the
   fact unstable** (`tests/harness/regrtest.py:228-237`, `tests/harness/upstream.py:427-444`,
   `tests/checks/test_v1_3_upstream_suites.py:82`, `tests/harness/sameness.py:57-59`).
   Two separate gaps:
   - **(a) The files were not desktop litter.** They were a host Python's bytecode, which the build
     writes itself. Step 20 runs `Platforms/WASI build`. Its `build` subcommand ends each half with
     `make pythoninfo` (`_build.py:424-432`; `Makefile.pre.in:2404`:
     `./$(BUILDPYTHON) -m test.pythoninfo`), and `test.pythoninfo` imports `test.test_socket`.
     READ, by time in the main tree tonight: `build/logs/20_cpython.log` was last written at
     22:53:21, and 11 `.pyc` files under `build/Python-3.15.0/Lib/test/**/__pycache__/` were
     written at 22:53:20–21 (`test_socket`, `pythoninfo`, `support/*`, `libregrtest/utils`). The
     files 078's lane saved are dated 10:02, and the step 20 log before them is dated 09:59:54. So
     every rebuild of step 20 writes them back. `common.sh:27`'s `PYTHONDONTWRITEBYTECODE=1` does
     not stop them; I did not settle why. They are in the main tree now. 090's litter list does
     not include `__pycache__` or `*.pyc`, so Decision 5 leaves these files in `left_out`.
   - **(b) Listing litter "separately" still records it.** `sameness` compares `facts` exactly,
     every key except `fuel_facts`. A second list inside the fact still differs between a tree
     that has litter and one that does not. Rule 6a then stops the landing.

   Failure: the next lane judges in the main tree, which has the 11 `.pyc` files. It compares with
   a reviewer whose worktree has no `build/Python-3.15.0` (then `tree is None`, so `left_out` is
   `[]`) or a cleaned one. Sameness differs on `cpython-*` `left_out`, and the landing stops, as
   it did for 078.

   Fix text (Decision 5, rewritten): "`left_out` lists a build tree's extra files under a staged
   folder, except litter names (`is_litter`, every path part) and anything under a `__pycache__`
   folder. A host Python's bytecode comes from step 20's `make pythoninfo`. Neither kind is
   recorded in any fact, so the fact depends only on the pinned tarball and the tree's real
   extras."

   Also do these:
   - Add a problem bullet that cites 078's landing note.
   - Add a unit row: a tree holding `Lib/test/__pycache__/x.cpython-315.pyc`, `Lib/test/.DS_Store`
     and `Lib/test/extra.py` gives `left_out == ["Lib/test/extra.py"]`, and the same for
     `upstream.stage`.
   - Optionally, step 20 removes `Lib/**/__pycache__` after its build, as `common.sh:34` already
     does for the tools' Python. That is build-class, and it fits here.
   - This changes a recorded fact, so it is a judge change (F3).

2. **Medium — Criterion 2 (and the Kind line's "byte-identical") cannot pass as written**
   (`scripts/assemble_artifacts.py:463-473`). MANIFEST has a `recipe <sha256> <path>` line for
   every tracked file under `scripts/`. This spec edits `scripts/litter.py`,
   `make_stdlib_zip.py` and `assemble_artifacts.py`. So MANIFEST differs from main's set in those
   three lines, and SHA256SUMS differs in MANIFEST's line. `test_v1_1_artifact_set.py:95`
   (`manifest_recipe_errors`) requires exactly that. "The five files" also leaves out
   `LICENSES/*.txt`.

   Fix text: "A rebuild from pins with no litter present matches main's set at the build's base,
   checked with `cmp`: `python.wasm`, `python-snapshot.wasm`, `python-stdlib.zip` and every
   `LICENSES/*` file are byte-identical. MANIFEST differs exactly in the `recipe` lines of the
   files this spec edits, and SHA256SUMS exactly in MANIFEST's line. The judge's `bytes` metrics
   do not move. With no litter, `version.py assets` gives the same tarball bytes as before (same
   members, same order)."

   Also name the base. 086 (wave 03, toolchain) rebuilds and may touch `assemble_artifacts.py`
   too. If 090 builds after it, the comparison is against 086's set.

3. **Medium — It changes the judge but does not say so, and widening `paths.OS_LITTER` moves
   checks the spec calls unchanged.** The spec edits `tests/harness/paths.py`, `artifacts.py`,
   `regrtest.py` and `upstream.py`. All of them are judging files, so the judge hash moves, and
   the lane needs `--accept-judge "spec 090: …"` (AGENTS.md rule 4). Criterion 5 and the Kind
   line say neither, and there is no "For the lane" section.

   `paths.OS_LITTER` also has five other readers that the spec does not list:
   - `paths.judge_files` (`paths.py:276`; the judge hash leaves out the new names).
   - `pins.tree_drift` (`pins.py:118`). This is spec 020's tree-against-tarball check, which the
     Scope calls "unchanged". It would now also skip `ehthumbs.db`, `Icon\r` and the volume
     names. The prefix rule does not reach it.
   - `scan.patch_shape_errors` (`scan.py:1958`).
   - The drafts walk (`scan.py:2042`).
   - `tests/unit/test_scoreboard.py:316`.

   Each of these tests names only, so after this spec "one definition" would hold the widened
   names everywhere but the `._` prefix only in some places.

   Fix text:
   - Add to the Kind line: "and a judge change: the lane accepts with `--accept-judge`."
   - List each reader of `paths.OS_LITTER` with its new test (`is_litter`, or names only, and
     why).
   - Rewrite the Scope's 020 line: "`tree_drift` skips the widened names and the `._` prefix too;
     a real extra file still fails it."

4. **Low — Decision 4's reason misses the wheel.** "No consumer of the set would carry it once
   the tarball packs its list" is not so. The wheel is built from `cp -R build/artifacts`
   (`release.yml:77`, `:194`, `:260`), and the memo's own §2 row says `._x`, `Icon\r` and
   `Thumbs.db` would go into it. `wheel_errors` checks only that the wheel holds every set file
   (`artifacts.py:179-186`). Once it forgives litter in the folder, a local wheel carrying
   `Thumbs.db` passes the judge. CI's exact comparison (`release.yml:376-380`) still catches it at
   release.

   Fix text: "`wheel_errors` also fails on a wheel member under `wasi_python/artifacts/` that
   `SHA256SUMS` does not list, litter or not."

5. **Low — Decision 6's `Icon[\r]` does not ignore `Icon\r`** (EXECUTED above: it ignores
   `Iconr`).

   Fix text: "`.gitignore` gains `.DS_Store`, `._*` and the line `Icon` followed by two literal
   CR bytes (git strips one trailing CR). A unit row runs `git check-ignore` on a file named
   `Icon\r`."

6. **Low — The tarball-scan row is slow, and it cannot fail first.** On this Mac it lists 75
   archives (698 MB) in 53.3 s (EXECUTED; a benchmark fact, not a check). That is about a quarter
   of the fast tier. Where `downloads/` is absent, it skips.

   Fix text: "The row is marked `slow`, or it scans only the trees `70_zip.sh` walks and the zip's
   wheels. Where `downloads/` is absent, it is a skip with a stated need. It is not one of
   criterion 1's rows."

7. **Low — Litter folders are not pruned.** `.Spotlight-V100`, `.fseventsd`, `.Trashes`,
   `.TemporaryItems` and `.DocumentRevisions-V100` are folders. `walk` prunes `dirnames` by
   `SKIP_DIRS` only (`make_stdlib_zip.py:103-110`), and `listed_files` and `sums_errors` test
   `p.name` only. So a file inside a `.TemporaryItems/` folder would still be packed or listed.

   Fix text: "Every walk prunes a folder with an `is_litter` name, and each list test checks every
   path part, as `litter.refuse` does."

8. **Low — Two gaps are INFERRED, not seen, and two more globs would meet them.** The memo decoded
   only `.DS_Store` files. On APFS, Finder writes `._x` files only onto volumes without extended
   attributes (exFAT, SMB), and `Icon\r` only for a custom folder icon. Keep the rule, since it
   costs one line, but label these two gaps INFERRED. `gen_inittab.py:51`
   (`rglob("*" + SUFFIX)`) and `60_link.sh:53` (`find -name "*.cpython-…so"`) would take a
   `._x.cpython-315-wasm32-wasi.so` as a module. They would fail loudly. Name both in Scope, as
   "out" or "in".

9. **Low — Decision 3's motivation and order.** `write_assets` runs only in `release.yml:106`, on
   CI, and by the spec's own Scope CI has no desktop writer. Keep the decision, on the principle
   that a consumer takes the list. But say it guards a local `version.py assets`.

   The Design says "in its order, plus `SHA256SUMS`". Today `SHA256SUMS` sorts in its place
   (`LICENSES/…`, `MANIFEST`, `SHA256SUMS`, `python-…`), and folders come first. Say the member
   order stays exactly as now, so the tarball with no litter is byte-identical. Extend
   `test_release_version.py::test_assets_are_deterministic` with planted litter and a missing
   listed file.

10. **Low — Status and Files are stale.** 089 has landed (`45b917c`). `tests/harness/litter.py`
    already holds the widened `LITTER_NAMES`. Its comment says "the names spec 090 adds".

    Fix text:
    - Drop "if 089 has landed".
    - Add `tests/harness/litter.py` to Files: `LITTER_NAMES` becomes `paths.OS_LITTER` and
      `is_litter` is the one shared rule, so there are two copies (scripts and harness) held equal
      by the unit check, not three.
    - Set the Status base to the current main.

## Constitution checks

- **§4.1 (patches):** no upstream source change. Step 20's bytecode is fixed in the judge or by a
  recipe, never by a patch. It holds.
- **§4 (pins):** no input changes. It holds.
- **§5.6:** this is the required pre-build review for the build recipe. The build review must read
  the release workflow run on the branch.
- **§5.7:** the spec is build-class. It is also a judge change (F3), and the landing must carry
  both kinds of reasons.
- **Tests count operations:** every criterion is a count, a list or a `cmp`. F6's timing is
  recorded only as a fact.
- **§7:** nothing tripped. Nothing under `build/` is to be edited by hand. Removing step 20's
  bytecode, if chosen, is a recipe step.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. F1 — taken (the builder, 2026-10-19): Decision 5 rewritten, so `left_out` records neither a
   litter path nor anything under `__pycache__` (`litter.unrecorded`); unit rows in both stages;
   step 20 removes `Lib/**/__pycache__` (Decision 6); the cause is written under *The problem*
   (the native build-Python runs as `python.exe -E`; the WASI guest gets no host variable from
   wasmtime). Declared a judge change.
2. F2 — taken: criterion 2 restated in the review's words, with four `recipe` lines (step 20 is
   now edited too) and the base named (`e00d394`, the set accepted at `b0c7a74`).
3. F3 — taken: the Kind line declares the judge change and `--accept-judge`; a table names all
   seven readers of `paths.OS_LITTER` with their test after the spec; the Scope's 020 line is
   rewritten.
4. F4 to F10 — (Low; answered in writing, no further round) F4, F5, F7, F8, F9, F10 taken as
   written; F6 answered: the slow scan is replaced by a guard in `tree_drift`, which already
   reads every pinned member. The specification's "Disposition of the pre-build review" has each.

## Verdict

Ready once F1 is fixed, by rewriting Decision 5 so that `left_out` records neither litter nor
`__pycache__`, and F2 and F3 are fixed, by restating criterion 2 against MANIFEST's recipe lines
and declaring the judge change with every reader of `paths.OS_LITTER` named. The Lows are fix text
the builder takes in writing.
