# 020 — Carried patches

- **Status:** drafted 2026-10-17 and revised against its pre-build review
  (`../reviews/020-carried-patches-spec-2026-10-17.md`), awaiting the reviewer's confirmation.
- **Owner:** Clay Gendron
- **Kind:** the build recipe (a new `scripts/steps/apply_patches.sh`, each step that unpacks a
  source tarball), `.gitattributes`, the judge (`tests/harness/pins.py`, `tests/harness/scan.py`,
  `tests/checks/test_rules.py`, `tests/checks/test_v1_5_rebuild_from_pins.py`, unit checks), the
  release workflow's zero-patch step, `recipes/patches/README.md`, `context/upstream/README.md`,
  `README.md`, `CHANGELOG.md`.
- **Depends on:** 003 (the pinned build), 012 (the same bytes from any host), 018 (landed:
  `remove.sh`, the litter rules, the steps this changes).
- **Research it stands on:** the owner's answer to question 32 (2026-10-17): "I do not want to
  wait for upstream. I want to build fixes ourselves but document the upstream fixes (PRs) we
  should submit to other projects", recorded in the constitution's amended §4.1;
  `../research/2026-10-17-what-scipy-needs.md` (OpenBLAS's C LAPACK traps under wasm until a
  type fix lands upstream, the first patch this mechanism will carry).

## The problem

§4.1 now allows a source change that cannot be a recipe file, as a patch that is reviewed,
recorded, matched by a drafted upstream pull request, and deleted once upstream releases the
fix (§2.5, §6.2, §7 and §8 were amended to match, `dbe9f02`). Nothing in the build or the judge
supports that yet: no step applies a patch, and the release workflow fails on any difference
from a pinned tarball. Until this specification lands, §4.1 says no patch is applied.

This specification builds the mechanism only. It lands with **no patch**. The first patch
(OpenBLAS, for scipy; or numpy's `.npy` fix, question 8) comes with the specification that needs
it, reviewed there.

## Decisions

1. **Where a patch and its pull request live.**
   - The patch: `recipes/patches/<top>/NNNN-<slug>.patch`, where `<top>` is the pinned tarball's
     top folder, the name the tree has under `build/` (`numpy-2.5.2`). `NNNN` is four digits,
     unique in its folder, and sets the order. A unified diff in `git diff` form (`a/` and `b/`
     prefixes), paths relative to the tree's top.
   - Its pull request: `context/upstream/patches/<top>/NNNN-<slug>.md`, the same name. It is
     project knowledge, not a build input, so it is outside `recipes/`: recording that the owner
     sent it changes no `MANIFEST` line.

   Keying by the top folder ties a patch to one version: a version bump moves the tree to a new
   name, so its patches must be carried forward on purpose (re-made against the new tarball,
   re-reviewed) or dropped.
2. **The pull request draft** starts with six header lines, then the body:

   ```
   - **Project:** OpenBLAS (https://github.com/OpenMathLib/OpenBLAS)
   - **Against:** 0.3.34 (the pinned tarball)
   - **Status:** drafted
   - **Title:** <the pull request's title>
   - **Files:** <every path the patch touches, comma-separated>
   - **Why we carry it:** <one or two sentences: what fails without it, in this project>
   ```

   `Status` is one of `drafted`, `sent <url>`, `merged <url>`, `released <version>`. The body is
   the pull request's text for the upstream maintainers: what is wrong, why, the change, how it
   was tested, and whether the project asks for a contributor licence agreement (the owner signs
   one). Sending is the owner's (§7). When the owner asks to send one, the agent prepares the
   change rebased onto upstream's default branch in a scratch clone of upstream and hands the
   owner the branch and text; the owner opens the pull request, and the status records the link.
3. **One applier, for the build and the judge.** A standalone `scripts/steps/apply_patches.sh
   TREE PATCH_DIR` (it sources nothing, so the judge can run it alone):
   - for each `PATCH_DIR/[0-9][0-9][0-9][0-9]-*.patch` in name order (an empty or missing folder
     applies nothing), it runs, one patch at a time,

     ```
     env -i PATH="$PATH" HOME="$EMPTY" XDG_CONFIG_HOME="$EMPTY" GIT_CONFIG_NOSYSTEM=1 \
       GIT_CONFIG_GLOBAL=/dev/null GIT_CEILING_DIRECTORIES="$(dirname "$TREE")" \
       git -C "$TREE" apply --whitespace=nowarn --verbose "$patch"
     ```

     where `$EMPTY` is a fresh empty folder. Clearing the environment removes `GIT_DIR`,
     `GIT_WORK_TREE` and `GIT_CONFIG_*`; the empty `HOME` and `XDG_CONFIG_HOME` remove the user's
     config and attributes files; the ceiling keeps git from treating the outer repository's
     `build/` as its work tree. The review showed each of these changing the bytes or skipping a
     patch with exit 0 otherwise, and this form applying cleanly under all of them (EXECUTED);
   - it fails the step when git exits non-zero, or when its output says `Skipped patch`, or that
     a hunk applied `with fuzz` or at an `offset`: each patch is made against exactly its
     tarball, so any of these means it no longer fits. git's output goes to the step's log; the
     step dies with one line naming the patch;
   - after the patches, every file a patch changed gets back its mtime from the tarball, and a
     file a patch adds gets the tarball's newest member's mtime, so no `make` rule sees a newer
     input (Decision 6 forbids patching autotools inputs, which this alone would not make safe).

   Every step that unpacks a source tarball (20 CPython, 30 zlib, 35 bzip2, xz and SQLite, 40
   numpy, 50 pandas) calls it right after the unpack, before anything reads the tree.
4. **Kept byte for byte.** `.gitattributes` gains `recipes/patches/** -text`, so git never
   converts a patch's line endings: a patch to a CRLF file (several pinned trees have them) is
   stored and hashed as made. A check reads `git check-attr text` for a path there.
5. **Recorded by hash, and nothing else in `MANIFEST`.** Patch files sit under `recipes/`, so
   `MANIFEST` already records each one as a `recipe <sha256> <path>` line; those lines name every
   patched tree. No new kind of `MANIFEST` line is added (the parser refuses unknown ones).
6. **What a patch may contain** (`scan.patch_errors`, run by a rules check):
   - no link (`new file mode 120000`, `new mode 120000`), no binary hunk (`GIT binary patch`,
     `Binary files`), no mode change (`old mode`, `new mode`);
   - every path with `a/` or `b/` prefixes and no `..` part;
   - no change to an autotools input (`configure.ac`, `configure.in`, `Makefile.am`, `*.m4`):
     their outputs (`configure`, `Makefile.in`) are what the build runs, and a change to an input
     would need the host's autotools;
   - the draft's `Files:` line names exactly the paths the patch touches. A review lists each
     added file and why (Decision 8).
7. **The other rules** (same function):
   - every `.patch` has its draft, and every draft its `.patch`;
   - every `<top>` is the top of a pinned source tarball of a component in `SOURCE_PATTERNS`,
     taken from the pinned file name (the name without `.tar.*` equals the top for all seven, a
     separate check confirms it where `downloads/` exists), so the rule needs no download;
   - each draft has the six header lines and a status of the four forms; `released <version>`
     is allowed, but fails when `<top>` is that version or later, since the fix is then in the
     tarball and the patch must go;
   - each patch's path appears in `CHANGELOG.md` (the section is a review item);
   - the README's row reads `upstream patches carried: N` and N is the number of patch files.
8. **Reviewing a patch.** A patch is code that runs in every guest, so it is reviewed as runner
   code is: a pre-build review of the specification that adds it, a build review of the diff,
   and the §5.6 security review before each release covers every carried patch. A review lists
   each file a patch adds and why, and reads the pull request draft, since the owner will send
   that text under the project's name.
9. **The zero-patch check becomes "exactly the recorded patches".** `pins.tree_drift(tarball,
   tree)` extracts the tarball into a temporary folder under `tempfile.gettempdir()`, runs the
   same `apply_patches.sh` on it, and compares the tree with the result: every file and link of
   the result in the tree and the same, every path a patch deletes absent from the tree (`git
   apply --summary` names them). Without patches it is the check it is today: files a build adds
   inside a tree stay unjudged, as now. `test_source_tree_matches_its_tarball` keeps its name and
   still requires all seven trees; a new patched project adds its `SOURCE_PATTERNS` entry and
   raises the workflow's count, in the specification that adds it.
10. **Licences.** A patch to a project's file carries that project's licence, as the same change
    upstream would; `recipes/patches/README.md` says so. The notices in `LICENSES/` are the
    projects' own and do not change.
11. **The headline and the judge's words change.** The README's results row becomes
    "upstream patches carried: 0, each with an upstream pull request (`recipes/patches/`)";
    its "with no source tree patched" (*How it is built*) and "zero-patch check" (*Releasing*)
    become "the source trees are their tarballs plus the recorded patches"; the docstrings of
    `pins.tree_drift` and the v1.5 check say the same. The embedder-name rule scans only the
    added lines and the file names of a `.patch` (its context lines are upstream's text, and
    "vfs" alone is on 1,272 lines of SQLite), and the drafts in full.

## Intent

A fix the project needs from another project's source can be carried today, as the exact change
it proposes upstream, applied the same way on every host and by the judge, and anyone can see
which trees differ from their tarballs, by what, and whether the pull request has been sent.

## Design

- `scripts/steps/apply_patches.sh` (Decision 3); the five unpacking steps call it.
- `.gitattributes`: `recipes/patches/** -text`.
- `recipes/patches/README.md` and `context/upstream/README.md` (a paragraph on
  `context/upstream/patches/`): the layout, the draft's header, the rules, the licence, the life
  of a patch (drafted, reviewed, carried, sent, merged, released, deleted).
- `tests/harness/pins.py`: `patch_dir(top)`, the patched `tree_drift`.
- `tests/harness/scan.py`: `patch_errors(root, pinned)`; the embedder rule's `.patch` handling.
- `tests/checks/test_rules.py`: a check that runs `patch_errors` on the real tree (no patches, no
  errors).
- README, CHANGELOG and docstrings as Decision 11.
- Checks (unit, `tests/unit/test_patches.py`, on a small tarball and tree made in a temporary
  folder; `apply_patches.sh` run under `sh`, blocked where there is no POSIX `sh` or no `git`):
  - a patch that fits is applied with LF bytes kept; two patches apply in order, the second
    depending on the first; a patch that no longer fits, one that applies only at an offset, and
    an empty patch file each stop with one line naming it;
  - the hostile settings, each in the caller's environment or config: `core.autocrlf=true`,
    `apply.whitespace=fix`, an XDG `attributes` file with `* text eol=crlf`,
    `GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_0`, and `GIT_DIR`/`GIT_WORK_TREE`: the bytes are the same
    as without them, and nothing is skipped;
  - a patch to a CRLF file, committed into a scratch repository with this `.gitattributes` and
    checked out again, still applies;
  - mtimes: a changed file keeps its tarball mtime; an added one gets the newest member's;
  - `tree_drift` with patches: the patched tree passes; the unpatched tree fails for an edit, for
    a deletion only, and for an added file; a tree with one more edit fails, naming the file;
  - `patch_errors`: each rule of Decisions 6 and 7 named on a bad folder, a correct folder gives
    none; `git check-attr text` is `unset` under `recipes/patches/`;
  - the embedder rule ignores a `.patch`'s context lines and catches its added lines.
- Each check is seen failing first (no `apply_patches.sh`, no patch support in `tree_drift`, no
  `patch_errors`), and each hostile-setting case against a stand-in applier without `env -i`.

## Scope

In: the mechanism, landed with no patch. Out:
- Any patch. The first one comes with the specification that needs it, reviewed there.
- Sending a pull request: the owner's (§7).
- Patching a pure-Python dependency installed from a wheel (python-dateutil, tzdata, six): none
  is needed, and a wheel is not unpacked by a step.

## Acceptance criteria

1. The checks exist and were seen failing before the change.
2. `uv run pytest` is green with `--accept-judge`.
3. One full build from pins in a clean clone with this change gives the reviewed artifact set:
   the three binaries and the licences byte for byte; `MANIFEST` differing only in `recipe`
   lines (the changed steps, `apply_patches.sh`, `recipes/patches/README.md`); `SHA256SUMS` only
   in `MANIFEST`'s line.
4. A trial, in a scratch clone with its `origin` removed, never committed, and deleted after: a
   patch adding a comment to one numpy source file, staged with `git add`, with its draft,
   CHANGELOG line and README count. Steps 40 to 90 run with it, and the whole judge passes; then
   with the draft removed the rules check fails, naming it. The clone is then deleted.
5. A release dry run passes every job.

## Landing notes

Not built.
