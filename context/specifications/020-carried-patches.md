# 020 — Carried patches

- **Status:** landed 2026-10-17. Reviewed before build
  (`../reviews/020-carried-patches-spec-2026-10-17.md`) and after
  (`../reviews/020-carried-patches-2026-10-17.md`, with its confirmation).
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
   TREE PATCH_DIR` (it sources only spec 018's `remove.sh`, so the judge can run it alone). It
   first makes both
   arguments absolute (`cd … && pwd -P`): a relative tree makes git ignore the ceiling.
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
   - it fails the step when git exits non-zero, or when a line of its output matches
     `^Skipped patch '` or `^Hunk #[0-9]+ succeeded at [0-9]+ \(offset `: each patch is made
     against exactly its tarball, so either means it no longer fits. Lines are matched whole, not
     words: git prints every patched path, and pinned trees have files named `offsets.pyx`.
     `env -i` clears the locale, so git's messages are English. git never fuzzes without `-C`,
     which the applier does not pass. git's output goes to the step's log; the
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
     `Binary files`), no mode change (`old mode`, `new mode`), no new file but a plain one (mode
     100644), no rename or copy; the paths and modes are read as git reads the patch (`git apply
     --numstat -z` and `--summary`), so a plain `---`/`+++` section after a hunk, or names that
     differ from `diff --git`, are judged too;
   - no path with a `..` part or outside the tree, as git reads the patch;
   - no change to an autotools input (`configure.ac`, `configure.in`, `Makefile.am`, `*.m4`):
     their outputs (`configure`, `Makefile.in`) are what the build runs, and a change to an input
     would need the host's autotools;
   - the draft's `Files:` line names exactly the paths the patch touches. A review lists each
     added file and why (Decision 8).
7. **The other rules** (same function):
   - every file in `recipes/patches/<top>/` is named `NNNN-<slug>.patch` (four digits, unique in
     the folder), since the applier's glob takes only those: a patch named otherwise would be
     recorded but never applied;
   - every `.patch` has its draft, and every draft its `.patch`;
   - every `<top>` is the top of a pinned source tarball of a component in `SOURCE_PATTERNS`,
     taken from the pinned file name (the name without `.tar.*` equals the top for all seven, a
     separate check confirms it where `downloads/` exists), so the rule needs no download;
   - each draft has the six header lines and a status of the four forms; `released <version>`
     is allowed, but fails when `<top>` is that version or later, since the fix is then in the
     tarball and the patch must go. The version is written in the pinned file name's form
     (`2.5.2` for numpy, `3540100` for SQLite) and compared as a tuple of integers split on `.`;
     no version library is used;
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
4. A trial, in criterion 3's clone with its `origin` removed, never committed, and deleted
   after: a patch appending a comment at the end of one numpy `.c` file (so no `__LINE__`
   shifts), staged with `git add`, with its draft, CHANGELOG line and README count. Steps 40 to
   90 run with it; the binaries and the zip equal criterion 3's byte for byte; the whole judge
   passes; then with the draft removed the rules check fails, naming it.
5. A release dry run passes every job.

## Landing notes

Built 2026-10-17 by the implementer (Claude Opus 5.5) in a scratch clone of `067c765` (specs 017
and 018 landed). **Not yet reviewed and not accepted.** Every claim below was run (EXECUTED) on
macOS arm64 with git 2.50, unless it says otherwise.

### What was built

- `scripts/steps/apply_patches.sh` (Decision 3): absolute arguments first; each
  `NNNN-*.patch` in name order through `env -i … git -C TREE apply --whitespace=nowarn --verbose`
  with an empty `HOME`/`XDG_CONFIG_HOME`, `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null`
  and the ceiling; whole-line checks for `^Skipped patch '` and the offset line; a changed file
  gets back its mtime (`touch -r` from a saved copy), an added one the newest file's; one ERROR
  line on failure. It sources only spec 018's `remove.sh`, for its own clean-up.
- `common.sh`'s `patch_tree TREE`, called right after each of the seven unpacks (steps 20, 30,
  35 three times, 40, 50).
- `.gitattributes`: `recipes/patches/** -text`. `recipes/patches/README.md`;
  `context/upstream/README.md`'s section on drafts.
- `tests/harness/pins.py`: `patch_files`, and `tree_drift(tarball, tree, patches=None)`, which,
  when a tree has patches, extracts the tarball into a temporary folder, runs the same applier
  and compares, deletions included; without patches it is the old check.
- `tests/harness/scan.py`: `patch_shape_errors`, `patch_errors` (Decisions 6 and 7), and the
  embedder rule's `.patch` handling (only added lines and file names).
- Checks: `test_carried_patches_follow_the_rules` (rules); the v1.5 tree check also confirms each
  tarball's top folder equals its file name; `tests/unit/test_patches.py` (29 cases).
- README (the results row, *How it is built*, *Releasing*), the workflow step's title, the
  docstrings, CHANGELOG.

### Choices the specification left to the build

- **Renames and copies** (`rename from`, `copy from`) are refused too: they would make the
  applier's mtime bookkeeping and the draft's `Files:` line ambiguous, and no upstream fix needs
  one.
- The applier finds the newest file of the tree as unpacked with a `-nt` walk; it runs only when a
  tree has patches.

### Seen failing first

- Against the scripts before this change: no applier, no `patch_errors`, and `tree_drift` takes no
  patches (the unit file fails to import them).
- Against a stand-in applier without `env -i`:
  `test_the_callers_git_settings_change_nothing` fails (the hostile settings change the bytes).

### Criterion 3: a full build from pins

In a clean clone with this change (`scripts/00_download.sh`, then `scripts/build.sh`, all eleven
steps ok): the three binaries, the zip and the licences are byte for byte the main tree's;
`MANIFEST`'s non-recipe lines are equal and its `recipe` lines differ for exactly the six changed
steps' files and the two added ones (`apply_patches.sh`, `recipes/patches/README.md`);
`SHA256SUMS` only in `MANIFEST`'s line.

### Criterion 4: the trial patch

In that clone, with its `origin` removed and the build committed: a patch appending a comment to
the end of `numpy/_core/src/multiarray/ctors.c`, with its draft, CHANGELOG line and README count,
staged, never committed. Steps 40 to 90: step 40's log says `applied 0001-trial.patch`; the
three binaries and the zip equal criterion 3's byte for byte. The whole judge ran on it and found
two real faults in this build, which were then fixed: the unit file used an embedder's name as
test data (the embedder rule), and the applier's clean-up was a bare `rm -rf` (spec 018's rule;
it now uses `remove`). Re-run: 175/179 pass, 0 fail, the patched zero-diff check included. With the
draft removed, the rules check failed: "…/0001-trial.patch: no pull request draft at …". The trial
was then removed, and steps 40 to 90 re-run without it. (A copy of the clone could not run the
trial: the toolchain under `build/tools` holds the clone's absolute paths.)

### Left over

- Windows runs no build step; the applier is POSIX `sh` and runs only on the build hosts (macOS,
  Linux). The release's `rebuild` job on arm64 Linux runs it first in CI (no patches yet, so it
  exits early there).

### Revised against the build review

The build review (`../reviews/020-carried-patches-2026-10-17.md`) found one high and three
medium defects, and seven low points; its disposition answers each. In short (EXECUTED in the
clone):

- **High:** a patch that deleted a file left it as an empty file, and the judge agreed: the
  applier's `touch -r` re-created it. It is `touch -c -r` now; the unit case asserts the file is
  gone and that an empty file left in its place is drift. The stand-in with `touch -r` fails it.
- **Medium:** the shape rules read paths and modes as git does (`git apply --numstat -z`,
  `--summary`), so names that differ from `diff --git` and plain sections after a hunk are
  judged (two cases); `tree_drift` extracts under `build/harness` with `filter="data"`, never the
  system temporary folder (§4.8); Finder litter in `recipes/patches/` is skipped.
- **Low:** the drafts are scanned for embedder names; the applier passes
  `core.quotePath=false`, so a non-ASCII added file gets the newest time (a case); a new file must
  be mode 100644 (a case); a released version in another form than the pinned name's is named as
  such (a case); the header and Decision 3 say the applier sources `remove.sh`; `AGENTS.md`,
  the README's row and the two READMEs are brought up to date.
