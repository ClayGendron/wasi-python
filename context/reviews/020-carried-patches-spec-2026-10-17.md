# Review of 020 — Carried patches (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the specification. I read
  `AGENTS.md`, the constitution (§2, §4.1, §4.2, §4.9, §5.2, §5.6, §6, §7, §8), question 32,
  `context/reviews/README.md` and the 018 pre-build review (for the format). Each claim is
  labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/020-carried-patches.md` as committed in `1722100`.
  The files it changes are unchanged at `1722100`.
- **Read:** `scripts/steps/common.sh`, steps 20, 30, 35, 40, 50, `scripts/assemble_artifacts.py`,
  `scripts/make_stdlib_zip.py` (`walk`), `tests/harness/pins.py`, `tests/harness/needs.py`,
  `tests/harness/scan.py`, `tests/harness/paths.py` (`parse_manifest`, `recipe_files`),
  `tests/checks/test_v1_5_rebuild_from_pins.py`, `tests/checks/test_rules.py`,
  `tests/checks/test_v1_1_artifact_set.py`, `.gitattributes`, `README.md`, `CHANGELOG.md`, and the
  build job of `.github/workflows/release.yml`.
- **Ran (EXECUTED, darwin-arm64, macOS 26.5).** Homebrew `git` 2.51.0 and Apple `git` 2.50.1
  (Apple Git-155). No Linux `git` was run: no local image has `git`, and I did not fetch one.
  - The repo was not edited. I did not run `scripts/build.sh` or `uv run pytest`. Under the main
    `build/` I only listed files, grepped them, and ran today's `pins.tree_drift` read-only.
  - Scripts and outputs are under
    `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev020/`:
    - `scripts/mk.sh`: a git repo with an ignored `build/` that holds an unpacked tarball
      `proj-1.0` (an LF file, a CRLF file, a file to delete, a script, a file with trailing
      spaces);
    - `scripts/mkpatches.sh`: six patches made with `git diff` (an edit; a dependent edit plus a
      new file, a deletion and a mode change; a CRLF edit; a trailing-space line; a binary file;
      a symlink);
    - `scripts/ga.sh`: `git apply` in a scrubbed environment (`env -i`, empty `HOME`,
      `GIT_CONFIG_NOSYSTEM=1`, the ceiling set to the tree's parent, `--whitespace=nowarn`);
    - `cfg/`, `xdg/`: hostile git configs (`core.autocrlf`, `apply.whitespace=fix`, an XDG
      `attributes` file);
    - `sec/`: hostile patches (`../`, an absolute path, a symlink then a write through it, a
      link to `/etc/passwd`, a deletion only, a mode change only, an empty patch);
    - `scripts/proto_drift.py`: Decision 5's check as worded (extract, apply, every file of the
      result in the tree and the same);
    - `scripts/drift_now.py`, `scripts/manifest_probe.py`, `scripts/tx.py`: today's
      `tree_drift` on the real trees, `parse_manifest` with a `patched` line, and the time to
      extract CPython's tarball.

## What holds

- **The ceiling works, and is needed.** EXECUTED, both gits:
  - Without it, `git apply` run inside `build/proj-1.0` takes paths from the outer repository's
    top. It prints `Skipped patch 'a.c'.` and **exits 0**, for both `--check` and the apply. The
    tree is untouched.
  - With `GIT_CEILING_DIRECTORIES` set to the tree's parent, paths are taken from the current
    folder (after `-p1` strips `a/` and `b/`). A trailing slash, the `/tmp` form and the
    `/private/tmp` form all work.
  - The ceiling must be the parent. Set to the tree itself, git still finds the outer
    repository and skips.
- **No fuzz, and a failed patch changes nothing.** EXECUTED: a hunk whose context does not match
  fails with exit 1. `--check` leaves the tree's hashes unchanged, and so does a failed apply:
  `git apply` is all-or-nothing per patch. (Offsets are another matter: finding 11.)
- **New files, deletions, modes, binary files and symlinks apply.** EXECUTED: the six-patch
  series applied in order. `sub/new.c` was created, `del.txt` removed, `run.sh` became 0755, a
  `GIT binary patch` wrote `\0\1\2bin`, and `link.c -> a.c` was made.
- **`git apply` refuses paths outside the tree.** EXECUTED: `../evil.txt` and
  `sub/../../evil2.txt` give `invalid path` (exit 128). A write through a symlink, in the same
  patch or a later one, gives `beyond a symbolic link` (exit 1). An absolute path
  (`a/private/tmp/…`) loses its first part to `-p1` and lands inside the tree. Nothing escaped.
- **In-tree `.gitattributes` are not read.** EXECUTED: outside a repository, a
  `*.c text eol=crlf` file in the tree did not change the bytes. READ: numpy's tarball ships a
  `.gitattributes` with `*.bat text eol=crlf`; it is inert here.
- **Keying by the top folder fits all seven sources.** EXECUTED (`tar -tf`): each tarball has
  exactly one top folder, and it equals the file name without `.tar.*`: `Python-3.15.0`,
  `numpy-2.5.2`, `pandas-3.0.6`, `zlib-1.3.1`, `bzip2-1.0.8`, `xz-5.8.4`,
  `sqlite-autoconf-3540100`. No tarball holds a symlink, a hard link or a `.git` entry.
- **Today's check passes, and ignores build products.** EXECUTED (`drift_now.py`): all seven
  trees have zero drift. CPython builds inside its tree (`cross-build/`, READ step 20); the
  check passes because files the build adds are not judged (READ `pins.py` docstring). Decision
  5, as worded, keeps that.
- **The tarball's hash is checked first.** READ: `test_source_tree_matches_its_tarball` compares
  the tarball with its pin (lines 67-69) before `tree_drift`. `tree_drift` itself does not.
  The build checks it in `pinned()` before the unpack (READ `common.sh`), as §4.1 requires.
- **It is fast enough.** EXECUTED (a benchmark fact, not a check): extracting
  `Python-3.15.0.tar.xz` takes 2.9 s with `tarfile` (144 MB, 5,434 files); today's hash pass
  takes 1.7 s.
- **Patch files are recorded by hash.** READ: `assemble_artifacts.py` lists
  `git ls-files recipes scripts` into `recipe` lines, and refuses untracked files under
  `recipes/` (lines 106-123).

## Acceptance criteria against evidence

1. Checks seen failing first — not built. They can fail first: today's `tree_drift` has no
   patch input.
2. `uv run pytest` green with `--accept-judge` — not built.
3. One build from pins, byte for byte except `MANIFEST`'s recipe lines — not quite as written.
   `SHA256SUMS` changes too (finding 13).
4. A trial patch in a scratch clone — achievable, but it does not run steps 90 or the whole judge,
   so it would miss findings 4, 6 and 7 (finding 13).
5. A release dry run — not built.

## Findings, most severe first

1. **High. The constitution still forbids patches in four places.**
   (`context/constitution.md` §2.5, §6.2, §7, §8)
   - The defect. The amendment changed §4.1 only. §2.5 (the v1.5 goal) still says "with zero
     patches to any upstream tree". §7's first never-do is "Patch an upstream source tree, even
     'temporarily'". §8 says "from pinned sources with no patches". §6.2 asks "patch-free?".
   - Failure. READ: this spec changes the v1.5 judge from "zero" to "the recorded patches", and
     the README's headline. That contradicts §2.5. The first patch spec then has an agent do a
     §7 never-do. The judge's docstrings (`pins.py`, `test_v1_5_…`) and README lines 151
     and 225 also still say "zero", "zero-patch" or "no source tree patched" (READ).
   - Fix. The constitution is the owner's. Before this is built, ask the owner to amend §2.5,
     §6.2, §7 and §8 to match §4.1 (one question). List the docstrings and README lines in the
     Design, beside Decision 9.

2. **High. `git apply`'s result depends on the host's git environment, and a skip exits 0.**
   (Decision 3, Decision 5)
   - The defect. Decision 3 says `git apply` "behaves alike on every build host". It does not.
   - Failure. EXECUTED, with the ceiling set as Decision 3 says:
     - `core.autocrlf=true` (INFERRED: Git for Windows sets it in its system config) turned an LF file
       into CRLF throughout. Exit 0.
     - `apply.whitespace=fix` stripped the trailing spaces of an added line. Exit 0.
     - An XDG `attributes` file (`~/.config/git/attributes`) with `* text eol=crlf` turned an LF
       file into CRLF, **even with** `GIT_CONFIG_GLOBAL=/dev/null` and `GIT_CONFIG_NOSYSTEM=1`.
     - `GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_0` in the environment did the same.
     - `GIT_DIR` and `GIT_WORK_TREE` set in the environment (as inside a git hook) made git skip
       the patch **despite the ceiling**: `Skipped patch 'a.c'.`, exit 0.
   - Why it matters. The judge applies "with the same `git apply`" on the same host, so it
     agrees with the build. A desktop build makes different bytes from CI's, and nothing local
     sees it. Also, the judge's own temporary folders live under `build/harness`
     (`paths.HARNESS_TMP`, READ). A `tree_drift` that extracts there without the ceiling skips
     every patch, so an unpatched tree passes and a patched tree fails.
   - Fix. One implementation, used by both the build and the judge: a standalone
     `scripts/steps/apply_patches.sh TREE PATCH_DIR` (not inside `common.sh`, which needs
     `line.sh` and `$0`; see 018's finding 6). It runs
     `env -i PATH="$PATH" HOME=<an empty folder> GIT_CONFIG_NOSYSTEM=1 GIT_CEILING_DIRECTORIES=<parent>
     git -C "$TREE" apply --whitespace=nowarn --verbose <patch>`, and fails if the output has
     `Skipped patch`. EXECUTED: that form applied cleanly, with LF bytes, under the hostile XDG
     files and with `GIT_DIR`/`GIT_WORK_TREE` set in the caller. `tree_drift` calls the same
     script on its temporary copy. A unit check runs it under each hostile setting above.

3. **High. The repository's `.gitattributes` corrupts a patch to a CRLF file.**
   (`.gitattributes`: `* text=auto eol=lf`)
   - The defect. Git normalises CRLF to LF on `git add` for any file it thinks is text. A patch
     to a CRLF file carries CR bytes in its context and changed lines.
   - Failure. EXECUTED: in a scratch repo with the same attribute line, a committed patch to a
     CRLF file came back from checkout without its CRs, and `git apply` refused it
     (`win.bat: patch does not apply`). The original applied. READ (grep): pinned trees hold
     CRLF text files, e.g. `bzip2-1.0.8/dlltest.c`, `Python-3.15.0/PC/readme.txt`, several
     `PCbuild/*.bat`, `xz-5.8.4/windows/build-with-cmake.bat`, numpy's `doc/make.bat`.
   - Fix. Add `recipes/patches/** -text` to `.gitattributes`, and a check that
     `git check-attr text` says `unset` for a path there. The hashes in `MANIFEST` then are of the
     exact bytes on every host.

4. **Medium. The judge rejects Decision 4's `patched` line.** (`tests/harness/paths.py:188-211`)
   - The defect. `parse_manifest` turns any line that is not `python`, `package`, `pin`,
     `recipe` or `x-…` into an error. The Design does not list `paths.py`.
   - Failure. EXECUTED (`manifest_probe.py`): the real `MANIFEST` plus `patched numpy-2.5.2 1`
     gives `MANIFEST:90: not a python, package, pin or recipe line`, which
     `test_v1_1_artifact_set.py:80` fails. It stays hidden while no patch exists, then turns the
     first patch spec red.
   - Fix. Simplest: drop the line. The `recipe` lines under `recipes/patches/<top>/` already
     name each patched tree, and §4.1 asks only for each patch's hash. If it stays: teach the
     parser, and add a rule that the `patched` lines equal the counts under `recipes/patches/`.

5. **Medium. The check, as worded, cannot see a deletion or a mode change.** (Decision 5)
   - The defect. "Every file and link of the patched result must be in the tree, the same."
     Extra files in the tree are not judged, and modes are not compared.
   - Failure. EXECUTED (`proto_drift.py`): with a patch that only deletes `del.txt`, the
     **unpatched** tree passes (`drift: []`). The same for a patch that only changes a mode. An
     edit patch is seen (`a.c: modified`).
   - Fix. Every path a patch deletes must be absent from the tree (`git apply --summary` names
     them). Either compare modes for touched files, or forbid mode lines in a patch (finding 8).
     Add both cases to the unit checks ("the unpatched tree fails" for each kind of patch).

6. **Medium. The embedder-name rule will fail on upstream text inside a patch.**
   (`tests/checks/test_rules.py:21`, `CODE_DIRS` includes `recipes`)
   - The defect. `embedder_hits` scans every line of every file under `recipes/`, as a
     case-insensitive substring. A patch's context and removed lines are upstream's text.
   - Failure. EXECUTED (grep): "vfs" appears on 1,272 lines of `sqlite3.c` and in CPython's
     `Modules/posixmodule.c` (`statvfs`) and `Lib/shutil.py`. A patch with a hunk near any of
     them fails `test_no_embedder_name_in_code`, for text that is not ours.
   - Fix. For `.patch` files, scan only the `+` lines (our text) and the file names; scan the
     drafts in full. Add a unit case.

7. **Medium. A status update in a draft makes the judge red.** (Decision 2, Decision 4)
   - The defect. The `.md` drafts sit under `recipes/`, so each gets a `recipe` hash line in
     `MANIFEST`.
   - Failure. READ: when the owner records `sent <url>`, the draft's hash changes, and
     `test_manifest_recipes_match_the_tree` reports `stale artifact` until a rebuild. Recording a
     link changes the next set's `MANIFEST` and `SHA256SUMS`. The draft is not a build input.
   - Fix. Put the drafts in `context/upstream/<top>/NNNN-<slug>.md` (project knowledge lives
     in `context/`), paired by name with `recipes/patches/<top>/NNNN-<slug>.patch`. The pairing
     rule stays. Or exclude them from `recipe` lines, with a rule; moving them is simpler.

8. **Medium. Decision 7 leaves out what a patch may not contain.** (Decision 6, Decision 7)
   - The defect. A review reads the patch, but nothing refuses the risky shapes.
   - Failure.
     - EXECUTED: a patch adds `etcpw -> /etc/passwd`, exit 0. INFERRED from READ: `walk` in
       `make_stdlib_zip.py` reads every file with `p.read_bytes()`, which follows a link. A
       link under `Lib/` or `pandas/` would put a host file's bytes in the stdlib zip.
     - EXECUTED: a `GIT binary patch` applies. Its bytes cannot be reviewed.
     - INFERRED: a patch can add a file a build picks up by its name, e.g. `Lib/sitecustomize.py`,
       which every guest would run at start-up. Its hunk can sit in a patch whose draft never
       mentions it.
   - Fix. Add to `patch_errors`: no `new file mode 120000` or `new mode 120000` (no links); no
     `GIT binary patch`; no `old mode`/`new mode`; every path has `a/` and `b/` prefixes and no
     `..` part. The draft's header gains `- **Files:**` listing every path the patch touches,
     and a rule checks that list against the patch. Decision 7 says a review lists each added
     file and why.

9. **Medium. Patched files get a new mtime, and autotools may then rebuild itself.**
   (§5.2: undecided)
   - The defect. `tar` keeps each file's tarball mtime. `git apply` writes a patched file with
     the current time.
   - Failure. READ: xz's `src/liblzma/Makefile.in` (lines 897-925) has automake's rules:
     `Makefile.in` depends on `Makefile.am`, and `configure` on `configure.ac` and `m4/*`. A
     patch to `Makefile.am` or `configure.ac` makes them newer, so `make` runs `automake` or
     `autoconf` on the host. That needs tools the build does not pin, and writes into the source
     tree. INFERRED: the step fails, or the build depends on the host's autotools.
   - Fix. Decide it. My suggestion: after the patches, `apply_patches` sets each touched file's
     mtime to the tarball's newest member mtime; and a patch to a generated file's input also
     carries the regenerated output. Or forbid patches to autotools inputs. Name the choice.

10. **Medium. Three of Decision 6's rules are not right as written.**
    - **`released <version>` fails.** The pin may lag, and moving a pin is a release (§5.5). This
      rule makes the honest status impossible to record, so it teaches leaving the status stale.
      The keying already forces the decision: after a re-pin, the old `<top>` folder names no
      pinned tarball, and that rule fails. Fix: allow `released <version>`; fail only when the
      `<top>`'s own version equals that version.
    - **CHANGELOG, "in the section of the release that first carries it".** The judge cannot
      know which release first carried a patch from the tree alone. Fix: check that the path
      appears in `CHANGELOG.md`; the section is a review item. READ: the CHANGELOG has `## `
      sections per release, so a plain substring search is robust.
    - **"Every `<top>` names a pinned source tarball's top folder."** `top_dir` opens the tarball,
      which needs `downloads/` (absent in a clean clone and in CI's `verify`). Fix: take the top
      from the pinned file name (it equals the top for all seven, above), limited to the
      `SOURCE_PATTERNS` components, not to every pinned tarball (wasi-sdk is pinned too). A
      separate check, where downloads exist, confirms the tarball's real top equals that name.
    - The README rule is robust if the Design fixes the exact text and pattern
      (`upstream patches carried: (\d+)`).

11. **Low. "Every hunk's context matches exactly" overstates `git apply`.** (Decision 3)
    - EXECUTED: with two lines added above a hunk, git printed
      `Hunk #1 succeeded at 14 (offset 2 lines)`, exit 0. With the context present twice, it
      patched the first one.
    - Against one pinned tarball this is still deterministic, so it does not break the check.
      It matters when a patch is carried to a new version.
    - Fix. Say "no fuzz; offsets are allowed". Better: fail when `--verbose` reports an offset,
      so each patch is made against exactly its tarball.

12. **Low. Small gaps in `apply_patches` and its checks.**
    - `--check` of the whole series at once fails when patch 2 depends on patch 1 (EXECUTED).
      So check and apply one at a time. A later failure leaves earlier patches applied. That is
      fine (the next run unpacks again), but the unit check's "leaves the tree as unpacked"
      holds per patch only. And `--check` is redundant with an atomic apply; harmless.
    - `git apply` prints two or more lines on failure (EXECUTED). Send them to `build/logs/` and
      `die` with one line.
    - An empty `<top>/` folder makes `*.patch` expand to itself in `sh`. Guard it. An empty patch
      file exits 128 (`No valid patches`, EXECUTED), which is good; say so.
    - Add a rule that each `NNNN` is four digits and unique in its folder, so order never rests
      on the slug or the locale.
    - Spec 018 (drafted, not built) changes the same steps. Name the order of the two.
    - A new patched project (OpenBLAS) needs a `SOURCE_PATTERNS` entry, and the workflow's
      `^7 passed` becomes 8. Say this belongs to the spec that adds the project.

13. **Low. The acceptance criteria miss what the findings need.**
    - Criterion 3. `SHA256SUMS` changes in `MANIFEST`'s line too, and new `recipe` lines appear
      (e.g. `recipes/patches/README.md`). Name the expected diff, as 018's revision did.
    - Criterion 4. Run steps 40 to 90 and the whole judge with the trial patch. That would catch
      findings 4, 6 and 7. The trial patch must be staged with `git add`, or step 90 refuses it
      (READ `assemble_artifacts.py:106-123`). Remove the clone's `origin` (it is the main
      repository), never commit, and delete the clone after. Then it is safe.
    - Add a case for each finding fixed above (the hostile git settings, a CRLF patch, a
      deletion-only patch).

14. **Low. Two points about the drafts are left open.** (§5.2)
    - "Rebased onto upstream's default branch when sent": who rebases, and where? The
      `context/prior_art/` clones are read-only. Say the owner does it when sending, or where
      the agent prepares it.
    - Some projects need a contributor licence agreement (INFERRED: CPython does). Say the draft notes it,
      since the owner signs.

## Simpler options

- Drop the `patched` line (finding 4). The `recipe` lines already show the patched trees.
- In `tree_drift`, extract only the files the patches name (`git apply --numstat`), apply there,
  and compare the rest with the tarball as today. It is less code than a full extraction plus a
  tree walk.
- One `apply_patches.sh` for both the build and the judge (finding 2), so the two can never
  apply differently.

## Constitution checks

- §4.1: the mechanism matches the amended text (applied after the hash check, recorded by hash,
  CHANGELOG, drafted pull request). But §2.5, §6.2, §7 and §8 still say zero (finding 1).
- §4.2 pins: holds. The tarball is checked before the unpack (READ) and before the drift check
  (READ).
- §4.6 the artifact set is the product: at risk from host git settings (finding 2) and from links
  (finding 8).
- §4.8 downloads are untrusted: holds. `git apply` keeps writes inside the tree (EXECUTED).
- §4.9 tests count: holds. The checks are on files and exit codes, not time.
- §4.10 claims carry evidence: "behaves alike on every build host" has none and is false
  (finding 2).
- §5.2 no open questions: findings 9, 10 and 14 leave choices open.
- §5.6 review: Decision 7 is right in spirit; finding 8 makes it checkable.
- §7: the spec itself trips nothing. A patch carried under it would trip §7's first bullet as
  written (finding 1).

## Disposition (filled in by the author, then confirmed by the reviewer)

Every finding is taken; the specification is revised in place.

1. **The constitution:** amended in `dbe9f02` (§2.5, §6.2, §7 and §8 now match §4.1, recorded as
   part of the owner's answer to question 32, which decided carried patches). README lines and
   the judge's docstrings are listed in Decision 11.
2. **Host-dependent `git apply`:** taken as you suggested. Decision 3 is one standalone
   `apply_patches.sh` used by the build and by `tree_drift`, with `env -i`, an empty `HOME` and
   `XDG_CONFIG_HOME`, `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null` and the ceiling; it
   fails on `Skipped patch`. The unit checks run it under each hostile setting you found.
3. **CRLF:** Decision 4, `recipes/patches/** -text`, with a `git check-attr` check and a
   committed-CRLF-patch case.
4. **The `patched` line:** dropped (Decision 5); the `recipe` lines name the patched trees.
5. **Deletions and modes:** Decision 9 requires every path a patch deletes to be absent; Decision
   6 forbids mode lines; unit cases for a deletion-only patch and an added file.
6. **The embedder rule:** Decision 11 scans only a `.patch`'s added lines and file names; a case.
7. **Drafts and `MANIFEST`:** the drafts move to `context/upstream/patches/<top>/` (Decision 1).
8. **Risky shapes:** Decision 6 forbids links, binary hunks, mode changes, unprefixed or `..`
   paths, and autotools inputs; the draft's `Files:` line must match the patch; Decision 8 has a
   review list each added file.
9. **mtimes:** decided (Decision 3): a changed file gets back its tarball mtime, an added one the
   newest member's; and Decision 6 forbids patching autotools inputs, which mtimes alone would
   not make safe.
10. **Three rules:** `released <version>` is allowed and fails only when `<top>` is that version
    or later; the CHANGELOG rule is a path search; `<top>` comes from the pinned file name,
    limited to `SOURCE_PATTERNS`, with a separate check where downloads exist; the README
    pattern is fixed (`upstream patches carried: N`).
11. **Offsets:** an offset or fuzz fails the step (Decision 3); a case.
12. **Small gaps:** one patch at a time; git's output to the log and one line out; an empty
    folder applies nothing; `NNNN` four digits and unique; 018 landed first (`61b9fe6`), so 020
    builds on its steps; a new project's `SOURCE_PATTERNS` entry and workflow count belong to
    the specification that adds it (Decision 9).
13. **Criteria:** criterion 3 names the expected diff; criterion 4 runs steps 40 to 90 and the
    whole judge on a staged trial patch in a clone with `origin` removed, never committed, then
    deleted; the cases above are in the Design.
14. **Drafts' open points:** the agent prepares the rebased change in a scratch clone of upstream
    when the owner asks to send, and the owner opens the pull request; the draft notes any
    contributor licence agreement, which the owner signs (Decision 2).

## Verdict

Revise first: the mechanism is sound in outline and the ceiling is the right idea, but the
constitution still forbids patches outside §4.1, and `git apply` as specified gives
host-dependent bytes, can skip a patch with exit 0, and cannot apply a committed patch to a CRLF
file.

## Confirmation

- **Date:** 2026-10-17
- **Reviewer:** the same fresh agent (Claude Opus 5.5); not the author.
- **Reviewed:** the specification as revised in `44aa70f`, the Disposition above, and the
  constitution as amended in `dbe9f02`. Spec 018 landed in `61b9fe6` (`scripts/steps/remove.sh`
  is there, READ).
- **Ran (EXECUTED, darwin-arm64, Homebrew `git` 2.51.0).** The repo was not edited, except to
  append this section. Nothing under the main `build/` was written. Scripts are in
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev020/confirm/`:
  - `apply_patches.sh`: Decision 3's `env -i … git -C "$TREE" apply --whitespace=nowarn
    --verbose` command, copied as written, with a plain `case` test for the words Decision 3
    names (`Skipped patch`, `with fuzz`, `offset`);
  - `series/`: four patches (an edit, a dependent edit with a new file, a deletion and a mode
    change, a CRLF edit, a trailing-space line);
  - `gattr/`: a scratch repo with this repo's `.gitattributes` plus `recipes/patches/** -text`;
  - `off/`: a patch to a file named `offsets.pyx`;
  - `newest.sh`: the newest file of a tree, in POSIX `sh`.

### The applier, the `-text` line and the constitution

- **The `env -i` command holds under every hostile setting.** EXECUTED: the four-patch series
  gave the same tree hash (`6196ef0a0b98`), exit 0, with no setting, with an XDG config and
  `attributes` file, a global `core.autocrlf=true`, a global `apply.whitespace=fix`,
  `GIT_CONFIG_COUNT`, `GIT_DIR` with `GIT_WORK_TREE`, and `LANG`/`LC_ALL=de_DE.UTF-8`. Because
  `env -i` clears the locale, git's messages are always English, so testing its output is
  sound.
- **`recipes/patches/** -text` keeps a CRLF patch.** EXECUTED: after this repo's
  `* text=auto eol=lf` line, a CRLF patch committed and checked out again was byte-identical.
  `git check-attr text` says `unset`; `eol` still says `lf`, but has no effect without `text`.
- **The constitution now agrees.** READ: §2.5, §6.2, §7 and §8 allow only the patches §4.1
  allows.
- **The mtime rule can be built in POSIX `sh`.** EXECUTED: `newest.sh` (a `find -newer` walk)
  found `numpy/version.py` in numpy's unpacked tarball. That is the tarball's newest member, and
  its mtime matches (1786240139). A changed file's own mtime can be saved before the patch and
  put back after with `touch -r` (POSIX).

### Each disposition against its finding

1. The constitution — closed (`dbe9f02`, and Decision 11 for the README and docstrings).
2. Host-dependent `git apply` — closed by Decision 3 (EXECUTED above). Conditions A and B.
3. CRLF — closed by Decision 4 (EXECUTED above).
4. The `patched` line — closed: dropped (Decision 5).
5. Deletions and modes — closed: Decision 9 checks deletions, Decision 6 forbids mode lines.
6. The embedder rule — closed: Decision 11.
7. Drafts in `MANIFEST` — closed: the drafts are in `context/upstream/patches/` (Decision 1).
8. Risky shapes — closed: Decision 6, the `Files:` line, Decision 8.
9. mtimes — closed by a decision (Decision 3 plus Decision 6's ban on autotools inputs). The
   ban costs little: a change to an input can be described in the draft, while the carried
   patch changes the output the build runs.
10. The three rules — closed, except how `released <version>` compares versions (condition D).
11. Offsets — closed in intent. Condition A is about how they are detected.
12. Small gaps — closed, except the file-name rule (condition C).
13. Criteria — closed. Condition E tightens criterion 4.
14. The drafts' open points — closed (Decision 2).

### Conditions left (each a sentence in the spec, or checked by the build review)

A. **Test git's output by exact line, not by word.** If "`offset`" is matched anywhere in the
   output, a correct patch is refused when its path holds that word. Every `--verbose` run prints
   `Checking patch <path>...`.
   - EXECUTED: an exact-fit patch to `offsets.pyx` applied cleanly, and the word test then
     refused it.
   - EXECUTED (`tar -tf`): pinned paths that hold the word include pandas'
     `pandas/_libs/tslibs/offsets.pyx`, `.pxd` and `.pyi`, and CPython's
     `Include/internal/pycore_debug_offsets.h`. xz has `tests/ossfuzz/`.
   - Fix: match `^Skipped patch '` and `^Hunk #[0-9]+ succeeded at [0-9]+ \(offset -?[0-9]+ lines?\)\.$`.
     EXECUTED: the second pattern matches git's real offset line. Without `-C`, `git apply`
     never fuzzes, so "with fuzz" needs no pattern. Add a unit case: a patch to a file named
     `offsets.c` applies.
B. **Make both arguments absolute first.** `GIT_CEILING_DIRECTORIES` ignores a relative entry,
   and `git -C` opens a relative patch path from inside the tree.
   - EXECUTED: a relative `TREE` gave `Skipped patch` (caught, so it fails closed). A relative
     `PATCH_DIR` gave `can't open patch`.
   - Both fail closed, but a step must not hit them. The script starts with
     `TREE=$(cd "$1" && pwd -P)`, and the same for `PATCH_DIR`.
C. **A rule for each patch file's name.** The applier's glob `[0-9][0-9][0-9][0-9]-*.patch`
   silently ignores any other name, e.g. `1-fix.patch` or `0001-fix.diff`. `tree_drift` runs the
   same applier, so it ignores the file too. READ: Decision 7's pairing rule would still pass if
   the draft has the same name.
   - The result would be a patch recorded in `MANIFEST` and the CHANGELOG but never applied.
   - Decision 1 states the name form, but Decisions 6 and 7 do not check it.
   - Fix: add to `patch_errors` that every file in a `<top>` folder is `NNNN-<slug>.patch`, with
     `NNNN` unique in the folder, and a unit case for each.
D. **Say how `released <version>` is compared.** The rule "fails when `<top>` is that version or
   later" needs one comparison for all seven forms. SQLite's top is `sqlite-autoconf-3540100`,
   not `3.54.1`.
   - Fix: the status writes the version in the pinned file name's form. The version is the top
     less its `SOURCE_PATTERNS` prefix. Compare as tuples of integers split on `.`.
   - Do not use `packaging`: it is only a dependency of pytest, not of this project (§4.13).
E. **Criterion 4: no line shift, criterion 3's clone, and identical binaries.**
   - A comment added mid-file moves `__LINE__` for the code after it (INFERRED). That can change
     the binaries and trip the ratchet's bytes rule, which is not this trial's point.
   - Fix: append the comment at the end of a numpy `.c` file, and run the trial in criterion 3's
     clone (steps 10 to 35 are already built there). Then also check that the three binaries and
     the zip equal criterion 3's, byte for byte. That shows the applier changed only what the
     patch says.

Optional, not a condition: Decision 9 can find the deleted paths without `git apply --summary`.
They are the tarball members missing from the patched copy.

No new gap at the level of the first review's findings.

### Verdict

Ready to build, with conditions A to E written into the specification (one sentence each) or
checked by the build review.

## Disposition of the confirmation (filled in by the author)

- **A:** made (Decision 3): whole-line patterns `^Skipped patch '` and
  `^Hunk #[0-9]+ succeeded at [0-9]+ \(offset `; no fuzz pattern, since `-C` is never passed.
- **B:** made (Decision 3): both arguments made absolute first.
- **C:** made (Decision 7): every file in a patch folder is named `NNNN-<slug>.patch`, unique.
- **D:** made (Decision 7): the version in the pinned file name's form, compared as integer tuples.
- **E:** made (criterion 4): the comment at the end of a `.c` file, in criterion 3's clone, the
  binaries and zip equal to criterion 3's.

Your verdict made the specification ready to build with these.

