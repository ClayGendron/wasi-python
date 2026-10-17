# 020 — Carried patches

- **Status:** drafted 2026-10-17, awaiting its pre-build review.
- **Owner:** Clay Gendron
- **Kind:** the build recipe (`scripts/steps/common.sh` and each step that unpacks a source
  tarball, `scripts/assemble_artifacts.py`), the judge (`tests/harness/pins.py`,
  `tests/harness/scan.py`, `tests/checks/test_v1_5_rebuild_from_pins.py`, unit checks), the
  release workflow's zero-patch step, `recipes/patches/README.md`, `README.md`, `CHANGELOG.md`.
- **Depends on:** 003 (the pinned build), 012 (the same bytes from any host), 014's rule that a
  check names what it refuses.
- **Research it stands on:** the owner's answer to question 32 (2026-10-17): "I do not want to
  wait for upstream. I want to build fixes ourselves but document the upstream fixes (PRs) we
  should submit to other projects", recorded in the constitution's amended §4.1;
  `../research/2026-10-17-what-scipy-needs.md` (OpenBLAS's C LAPACK traps under wasm until a
  type fix lands upstream, the first patch this mechanism will carry).

## The problem

§4.1 now allows a source change that cannot be a recipe file, as a patch that is reviewed,
recorded, matched by a drafted upstream pull request, and deleted once upstream releases the
fix. Nothing in the build or the judge supports that yet: no step applies a patch, and the
release workflow fails on any difference from a pinned tarball. Until this specification lands,
§4.1 says no patch is applied.

This specification builds the mechanism only. It lands with **no patch**. The first patch
(OpenBLAS, for scipy; or numpy's `.npy` fix, question 8) comes with the specification that needs
it, reviewed there.

## Decisions

1. **Where a patch lives.** `recipes/patches/<top>/`, where `<top>` is the pinned tarball's top
   folder, the name the tree has under `build/` (`numpy-2.5.2`, `OpenBLAS-0.3.34`). Each patch
   is a pair:
   - `NNNN-<slug>.patch`: a unified diff, paths relative to the tree's top (`git diff` style, `a/`
     and `b/` prefixes), applied in `NNNN` order;
   - `NNNN-<slug>.md`: its upstream pull request, drafted for the owner to send.

   Keying by the top folder ties a patch to one version: a version bump moves the tree to a new
   name, so its patches must be carried forward on purpose (re-made, re-reviewed) or dropped.
2. **The pull request draft** starts with five header lines, then the body:

   ```
   - **Project:** OpenBLAS (https://github.com/OpenMathLib/OpenBLAS)
   - **Against:** 0.3.34 (the pinned tarball); rebased onto upstream's default branch when sent
   - **Status:** drafted
   - **Title:** <the pull request's title>
   - **Why we carry it:** <one or two sentences: what fails without it, in this project>
   ```

   `Status` is one of `drafted`, `sent <url>`, `merged <url>`, `released <version>`. The body is
   the pull request's text, written for the upstream maintainers: what is wrong, why, the change,
   how it was tested. The owner sends it; the agent never does (§7). When the owner sends it, the
   status records the link.
3. **Applying.** `common.sh` gains `apply_patches TREE`: for each `recipes/patches/<top>/*.patch`
   of that tree's top folder, in name order, it runs `git apply --check` and then `git apply`,
   from inside the tree, with `GIT_CEILING_DIRECTORIES` set to the tree's parent so that git never
   treats the outer repository's `build/` as its work tree. `git apply` takes a patch only when
   every hunk's context matches exactly (no fuzz), so a patch that no longer fits stops the step
   with one line naming it. Every step that unpacks a source tarball calls `apply_patches` right
   after the unpack, before anything reads the tree. `git` is already a host tool of the build
   (it lists the recipes for `MANIFEST`); `git apply` behaves alike on every build host.
4. **Recorded by hash.** Patch files sit under `recipes/`, so `MANIFEST` already records each one
   as a `recipe <sha256> <path>` line (`assemble_artifacts.py` lists `git ls-files recipes
   scripts`). `MANIFEST` gains one line per patched tree, `patched <top> <count>`, so a reader
   sees at a glance which trees differ from their tarballs. A tree with no patch has no line.
5. **The zero-patch check becomes "exactly the recorded patches".** `pins.tree_drift(tarball,
   tree)` extracts the tarball into a temporary folder, applies that tree's patches there with
   the same `git apply`, and compares the tree with the result: every file and link of the
   patched result must be in the tree, the same, and no file a patch adds may be missing.
   Without patches it is the check it is today. `test_source_tree_matches_its_tarball` keeps its
   name (the release workflow and its own scan find it by name) and still requires all seven
   trees; the workflow step's title becomes "the source trees are their tarballs plus the
   recorded patches".
6. **The judge's rules for patches** (`scan.patch_errors`, run by a rules check):
   - every `.patch` has its `.md`, and every `.md` its `.patch`;
   - every `<top>` folder names a pinned source tarball's top folder (no patch for a version not
     pinned);
   - each `.md` has the five header lines, a status of the four forms, and a body;
   - a status of `released <version>` fails: the fix is upstream, so the patch is deleted and
     the pin moved;
   - each patch is named in `CHANGELOG.md` (by its path) in the section of the release that first
     carries it;
   - the README's "upstream patches" row states the number of patch files.
7. **Reviewing a patch.** A patch is code that runs in every guest, so it is reviewed as runner
   code is: a pre-build review of the specification that adds it, a build review of the diff, and
   the §5.6 security review before each release covers every carried patch. A review of a patch
   also reads its pull request draft, since the owner will send that text under the project's
   name.
8. **Licences.** A patch to a project's file carries that project's licence, as the same change
   upstream would; `recipes/patches/README.md` says so. The notices shipped in `LICENSES/` are
   the projects' own and do not change.
9. **The headline changes.** The README's results row "upstream patches … **zero**" becomes
   "upstream patches carried: N, each with an upstream pull request (`recipes/patches/`)",
   with N = 0 when this lands. The CHANGELOG says the project now may carry patches, and how
   they are recorded.

## Intent

A fix the project needs from another project's source can be carried today, as the exact change
it proposes upstream, and anyone can see which trees differ from their tarballs, by what, and
whether the pull request has been sent.

## Design

- `recipes/patches/README.md`: the layout, the draft's header, the licence rule, the life of a
  patch (drafted, reviewed, carried, sent, merged, released, deleted).
- `scripts/steps/common.sh`: `apply_patches`, as Decision 3. The steps that unpack a source
  tarball (20 CPython, 30 zlib, 35 bzip2, xz and SQLite, 40 numpy, 50 pandas) call it after
  each unpack.
- `scripts/assemble_artifacts.py`: the `patched <top> <count>` lines.
- `tests/harness/pins.py`: `patches_for(top)` and the patched `tree_drift`.
- `tests/harness/scan.py`: `patch_errors(root, pinned)`; a rules check in
  `tests/checks/test_rules.py` runs it on the real tree.
- Checks (unit, `tests/unit/test_patches.py`, on a small tarball and tree made in a temporary
  folder):
  - `apply_patches` under `sh`: a patch that fits is applied; one whose context no longer
    matches stops with one line naming it and leaves the tree as unpacked (`--check` first);
    two patches apply in name order;
  - `tree_drift` with patches: the patched tree passes; the unpatched tree, a tree with one more
    edit, and a tree missing a file a patch adds each fail, naming the file;
  - `patch_errors`: a lone `.patch`, a lone `.md`, a folder for an unpinned version, a missing
    header, an unknown status, `released 1.2.3`, a patch the CHANGELOG does not name, and a
    README count that is wrong, each named; a correct folder has none.
- Each check is seen failing first (no `apply_patches`, no patch support in `tree_drift`, no
  `patch_errors`).

## Scope

In: the mechanism, landed with no patch. Out:
- Any patch. The first one comes with the specification that needs it (scipy's OpenBLAS, or
  numpy's `.npy` fix), and is reviewed there.
- Sending a pull request: the owner's (§7).
- Patching a pure-Python dependency installed from a wheel (python-dateutil, tzdata, six): none is
  needed, and a wheel is not unpacked by a step; a later specification can extend this if one is.

## Acceptance criteria

1. The checks exist and were seen failing before the change.
2. `uv run pytest` is green with `--accept-judge`.
3. One full build from pins in a clean clone with this change gives the reviewed artifact set,
   byte for byte except `MANIFEST`'s recipe lines (no `patched` line, since no patch exists).
4. In a scratch clone, a trial patch to one tree (a comment added to a numpy source file, never
   committed) is applied by its step, passes the patched zero-patch check, and is refused by the
   rules check until its draft, CHANGELOG line and README count exist; with the trial removed,
   the check passes again.
5. A release dry run passes every job.

## Landing notes

Not built.
