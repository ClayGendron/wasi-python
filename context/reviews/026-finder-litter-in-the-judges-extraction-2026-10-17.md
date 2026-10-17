# Review of 026: Finder litter in the judge's own extraction (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change or its
  specification. Every claim is labelled EXECUTED, READ or INFERRED.
- **Read:**
  - specification 026 with its landing notes;
  - `git show b5a34de` (three files);
  - all of `_patched_drift`, `_remove_tree` and `_tarball_drift` in `tests/harness/pins.py`;
  - `patch_errors` and `patch_shape_errors` in `tests/harness/scan.py`;
  - `paths.OS_LITTER`;
  - spec 018's rules.
- **Reviewed:** commit `b5a34de` on main (not pushed, not accepted).
- **Re-ran (EXECUTED, darwin-arm64):** scripts and logs are in the scratch folder `rev025/`
  (`m3`, `m4`, `extra/test_held_litter.py`). The full judge is in the 025 review: 188/190,
  0 fail, lost 0, grew 0. ruff is clean. `build/progress/latest.json` was restored byte for
  byte.

## What changed (READ)

- **The patched comparison skips a litter name the tarball does not hold.** It walks the
  extraction with the patches applied (`result`), and skips an entry when its name is in
  `OS_LITTER` (`.DS_Store`, `Thumbs.db`, `desktop.ini`, exact names) and its relative path is
  not one of the tarball's members.
- **Directories are not skipped by this.** `rglob` still descends into a skipped name, so a
  litter-named directory cannot hide the files inside it.
- **The comparison runs one way:** from the expected tree to the build tree. Files only in the
  build tree were never compared. The unpatched comparison (`_tarball_drift`) walks only the
  tarball's members, and is unchanged.
- **The extraction is removed with three tries.** One that will not go is left under
  `build/harness`, which git ignores (`.gitignore:5: build/`, EXECUTED).

## Can it hide a real upstream difference?

- **A litter file the tarball ships is still compared (EXECUTED).** My probe added
  `.DS_Store` to the test tarball, applied a patch, and changed the build tree's copy.
  `tree_drift` reported `.DS_Store: modified` on main. It reported nothing on mutant m4, which
  skips every litter name whatever the tarball holds. So the code is right, but no check of
  the judge's own guards this case (finding 1).
- **Another case is compared (READ).** `.ds_store` or `.DS_STORE` is not in `OS_LITTER`, which
  matches names exactly, so it is compared like any file. Members keep the tarball's spelling,
  so `rel not in held` compares like with like.
- **A litter-named file that a patch adds is not compared (EXECUTED).** A patch adding
  `sub/.DS_Store`, with a build tree that never got it, gives `drift: []`. `patch_shape_errors`
  does not refuse such a name (READ). No build input reads these names, and spec 018 keeps them
  out of every artifact (READ), so nothing ships differently (INFERRED). It is still a file a
  carried patch could change unseen (finding 2).
- **Only the three exact names are skipped**, and only off the tarball's member list (READ).

## Mutants (EXECUTED)

| mutant | change | result |
|---|---|---|
| m3 | no litter skip | `test_os_litter_in_the_judges_own_extraction_is_not_drift` fails |
| m4 | litter skipped even when the tarball holds it | **survives**: all 37 checks in `test_patches.py` pass (finding 1) |

## The leftover folder

- **Two old leftovers are in `build/harness` (EXECUTED):**
  - `patched-7odafqtz` (15:38, 16 KB);
  - `patched-cq8ozq4b` (15:47, 888 KB, a partial numpy tree).

  Each holds `.DS_Store` files. Both are older than the commit (15:51), so they are the old
  `TemporaryDirectory` failure the specification describes. My runs on the new code left
  none.
- **Nothing reports a leftover, and nothing removes old ones (READ).** Each is under an
  ignored folder, and its size is at most a source tree. Finding 3.

## Acceptance criteria against evidence

| # | criterion | evidence | holds |
|---|---|---|---|
| 1 | litter written into the extraction after the real applier gives no drift; seen failing first | EXECUTED: the check passes, m3 fails it | yes |
| 2 | judge green, lost 0, grew 0 (`--accept-judge` is the owner's step) | EXECUTED: 188/190, lost 0, grew 0 | yes, pending acceptance |

## Findings, most severe first

### 1. No check guards "a litter file the tarball holds is still compared": low (EXECUTED)

Decision 1 promises it, and the new check's docstring says it, but only the skip is tested.
Mutant m4 removes the `rel not in held` condition and passes every check. Suggested: add the
case from `rev025/extra/test_held_litter.py`. The tarball holds `.DS_Store`, the build tree's
copy differs, and the expected drift is `[".DS_Store: modified"]`. It passes on main and fails
on m4.

### 2. A carried patch may add a litter-named file that no comparison sees: low (EXECUTED, READ)

Suggested: `patch_shape_errors` refuses a path whose last part is in `OS_LITTER`, as it
refuses autotools inputs. No upstream fix would add such a file.

### 3. A leftover extraction is kept silently: informational (EXECUTED, READ)

Suggested: before making a new extraction, remove `patched-*` folders older than the run with
the same retries, or name a leftover in the scoreboard's output. The README's "keep output
short" rule allows one line.

## Constitution checks

- **§4.1:** the release check "the source trees are their tarballs plus the recorded patches"
  is unchanged for every file the tarball or a patch holds, except finding 2's narrow case
  (READ, EXECUTED).
- **§4.8:** the extraction stays under the project's `build/harness`, never the system's
  temporary folder (READ).
- **AGENTS.md rule 4:** the judge change has a stated reason, and spec 026 is its
  specification (READ).

## Disposition (filled in by the author, then confirmed by the reviewer)

1. **Fixed.** `test_a_litter_name_the_tarball_ships_is_still_compared`: a tarball shipping
   `.DS_Store`, the tree's copy changed, gives `.DS_Store: modified`. The mutant that drops the
   member condition now fails it (EXECUTED).
2. **Fixed.** `patch_shape_errors` refuses a patch that touches an OS-litter name ("a name
   Finder or Explorer writes"), with `test_a_patch_may_not_touch_a_litter_name`; so no litter
   name can enter a tree through a patch and escape comparison.
3. **Answered, no change.** A leftover extraction stays under the git-ignored `build/harness`
   by design (Decision 4); the next judge run's extraction is a fresh folder, so it is never read.


## Verdict

**May land.** It does what it says, and it cannot hide a difference in any file the tarball
ships (EXECUTED). Answer findings 1 and 2 before the tag, since both are small additions to
the judge. Finding 3 is optional.
