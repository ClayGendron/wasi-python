# Review of 020 — Carried patches (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change. I did not write the
  specification's pre-build review or its confirmation. I read `AGENTS.md`, the constitution
  (§2.5, §4.1, §4.8, §4.9, §6.2, §7, §8), `context/reviews/README.md`, the 018 build review (for
  the format), specification 020 with its landing notes, its pre-build review with the
  confirmation, and the diff. I did not rely on the landing notes. Each claim is labelled
  EXECUTED, READ or INFERRED.
- **Reviewed:** the scratch clone's `git diff 067c765 c6e27a7` (one commit). It touches
  `scripts/steps/apply_patches.sh` (new), `scripts/steps/common.sh`, steps 20, 30, 35, 40 and 50,
  `.gitattributes`, `.github/workflows/release.yml`, `tests/harness/pins.py`,
  `tests/harness/scan.py`, `tests/checks/test_rules.py`,
  `tests/checks/test_v1_5_rebuild_from_pins.py`, `tests/unit/test_patches.py` (new),
  `recipes/patches/README.md` (new), `context/upstream/README.md`, `README.md`, `CHANGELOG.md`
  and the specification.
- **Re-ran (EXECUTED, darwin-arm64, macOS 26.5, Homebrew git 2.51.0; the clone's own `build/`;
  the main tree's `build/artifacts` read only).** Probes and outputs are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev020b/`:
  - `scripts/battery.sh`: the applier against the pinned zlib tarball. One `git diff` patch
    edits `README`, deletes `ChangeLog`, adds `new dir/n v.c` and adds `café.c`. Then relative
    arguments, folders with spaces, an empty and a missing folder, an offset, a changed context
    line (fuzz), an empty patch, every hostile git setting at once on a tree inside an outer
    repository's ignored `build/`, and the clean-up with `TMPDIR` set to a folder with a space.
    Run under `/bin/sh` and `/bin/dash` on macOS (`battery-macos.txt`), and under Debian trixie's
    dash with GNU coreutils 9.7, findutils 4.10 and git 2.47.3, as root and as a plain user
    (`battery-linux.txt`). git was installed with `apt-get` inside that throwaway container
    only.
  - `scripts/scanprobe.py`, `scanprobe2.py`, `hiddenprobe.py`, `draftprobe.py`: odd patches and
    drafts against `patch_shape_errors`, `patch_errors` and `embedder_hits`, each beside what
    `git apply --numstat --summary` does with the same patch (`scan/*.txt`).
  - `scripts/pinsprobe.py`: both tar filters on the seven pinned tarballs, and `tree_drift` on the
    clone's CPython tree with one patch (`pins/pins.txt`). `scripts/delprobe.py`: a deletion
    patch through the applier and `tree_drift` (`del.txt`).
  - `uv run pytest -p no:cacheprovider` in the clone (`pytest-full.txt`): `175/179 pass · 0 gap ·
    4 blocked · 0 fail (unit suite 412/419, 7 skipped)`; v1.5 `18/18`; rules `17/18`; `587
    passed, 11 skipped`; ratchet vs `f2a7a07f47`: `lost 0 · absent 0 · unrun 0 · unrun locally
    2 · gained 1 · grew 0 · judge changed: .gitattributes, tests/checks/test_rules.py,
    tests/checks/test_v1_5_rebuild_from_pins.py and 3 more`; `next:
    context/specifications/004-alpha-releases.md`; **exit 0**. I did not pass `--accept`.
  - `uv run ruff check src tests` → all checks passed; `uv run ruff format --check src tests` →
    50 files already formatted (`ruff.txt`).
  - I did not commit or push. I did not run a build step or re-run the trial. The clone's `git
    status` was empty before and after, at `c6e27a7`. I wrote nothing in the main tree; this
    file is in the scratchpad.

## Decisions against the code

- **Decision 3, the applier (READ, EXECUTED).**
  - The `git` line is the Decision's: `env -i`, `PATH`, an empty `HOME` and `XDG_CONFIG_HOME`,
    `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null`, the ceiling at the tree's parent,
    `--whitespace=nowarn --verbose`, one patch at a time.
  - Both arguments are made absolute with `pwd -P` (READ). A relative tree and a relative patch
    folder, both with spaces, gave the same tree hash as absolute ones (EXECUTED, battery 2).
  - All hostile settings at once (XDG `attributes` with `* text eol=crlf`, a global
    `core.autocrlf=true` and `apply.whitespace=fix`, `GIT_CONFIG_COUNT`, `GIT_DIR` and
    `GIT_WORK_TREE`, a German locale), on a relative tree inside an outer repository's ignored
    `build/`: exit 0 and the same tree hash, `3184855958`, on macOS and on Linux (EXECUTED,
    battery 7). Nothing was skipped.
  - An empty folder and a missing folder: exit 0, nothing done (EXECUTED, battery 3).
  - An offset: exit 1, one line, `ERROR: 0001-main.patch was skipped or applied at an offset`
    (EXECUTED, battery 4). A changed context line: exit 1, `does not apply` (battery 5). git
    never fuzzes without `-C`. An empty patch: exit 1, `not a patch git can read` (battery 6).
  - The whole-line patterns are the ones the confirmation asked for (READ). A file named with
    "offset" no longer trips them (READ: the pattern is anchored at `^Hunk #`).
  - The mtime rule: a changed file keeps its tarball mtime (`README`: 1705948357 before and
    after); an added file with a plain name gets the newest file's mtime (EXECUTED, battery 1).
    But a deleted file comes back (finding 1), and an added or changed file whose name git
    quotes gets the current time (finding 6).
  - The clean-up: `$WORK` goes through `remove` on the EXIT trap. After a success and after a
    failure, `TMPDIR` was empty (EXECUTED, battery 8).
  - **dash and GNU tools (EXECUTED).** macOS `/bin/sh`, macOS `/bin/dash` and Debian dash with
    GNU tools gave the same results case for case, and the same tree hash. `touch -r`, `find
    -type f`, `[ -nt ]`, `cut -f3`, `mktemp -d` and `$((…))` behave alike. As root, git's
    "dubious ownership" check does not apply: the applier runs outside any repository.
  - The script sources spec 018's `remove.sh`. Decision 3 and the script's own header say "it
    sources nothing" (finding 9). `remove.sh` is standalone, so the judge can still run the
    applier alone (EXECUTED: `tree_drift` does).
- **The steps (READ).** Each of the seven unpacks is followed at once by `patch_tree`, before
  any `cd`, `sed`, `configure` or compile reads the tree: step 20 (`$CP` =
  `$B/Python-$PYTHON_VERSION`, so `Python-3.15.0` with `line.conf`'s `3.15.0`), step 30
  (`zlib-1.3.1`), step 35 (`bzip2-1.0.8`, `xz-5.8.4`, `sqlite-autoconf-3540100`), step 40
  (`numpy-2.5.2`) and step 50 (`pandas-3.0.6`). Each step removes its tree before the unpack, so
  a file a patch added never survives into the next run. `patch_tree` takes the folder from
  `basename`, which equals each tarball's top (the v1.5 check confirms it, EXECUTED in the
  judge). No other step unpacks a source tarball: step 10's are toolchains, and step 60 only
  reads two toolchain tarballs (READ, `grep`).
- **Decision 4 (READ, EXECUTED).** `recipes/patches/** -text`; the unit case commits a CRLF
  patch with this `.gitattributes` and applies it after checkout (passes in the judge run).
- **Decision 5 (READ).** No new `MANIFEST` line. The patch files would be `recipe` lines.
- **Decision 9, `tree_drift` (READ, EXECUTED).**
  - The v1.5 check still compares the tarball with its pin first (lines 67-69), then the top
    folder, then `tree_drift`. `tree_drift` alone does not check the hash, as before.
  - Without patches it is the old `_tarball_drift`, unchanged (READ).
  - With patches it extracts under `tempfile.gettempdir()` (EXECUTED:
    `/var/folders/…/T`, outside the repository), runs the same applier, and compares every file
    of the result. A file a patch adds is seen when absent (unit case). The deletion branch can
    never fire while finding 1 stands (EXECUTED, `del.txt`).
  - `filter="tar"` against `filter="data"`: both extract all seven tarballs to the same file
    list (EXECUTED: 5,434, 8,365, 1,597, 253, 56, 655 and 49 files). `"data"` is stricter: it
    refuses absolute links and links that leave the folder, and device files. Nothing is
    compared by mode, so it costs nothing (finding 10).
  - Speed, a benchmark fact and not a check: on the clone's CPython tree with one patch,
    `tree_drift` took 6.0 s, against 1.9 s without patches (EXECUTED, once).
  - The extraction sits in the system temporary folder (finding 3).
- **Decisions 6 and 7, `patch_errors` (READ, EXECUTED).**
  - Each rule fires on its own bad folder (the unit cases pass). A CRLF draft parses
    (EXECUTED). `\ No newline at end of file` is accepted, as it should be.
  - Status forms (EXECUTED): `released 3540100` against `sqlite-autoconf-3540100` fails with
    "delete the patch"; `released 3550000` passes; `released 3.15.1` against `Python-3.15.0`
    passes; `released v3.15.1` fails with "cannot compare"; `merged` without a link fails;
    `sent <url> extra` fails. `released 3.55.0` for SQLite, a later release in the dotted form,
    fails with "delete the patch" (finding 8).
  - A `---`/`+++` pair alone, with no `diff --git`: refused (EXECUTED). A quoted path, or git's
    own unquoted form with spaces: refused, a false failure, not a false pass (finding 8).
  - But two shapes pass that git applies to a file the check never sees (finding 2).
  - A new file with mode `100755` passes (finding 7). A link made through the `index` line's
    mode alone does not: git created a plain file (EXECUTED).
- **Decision 11, the embedder rule (READ, EXECUTED).** For a `.patch`, only `+` lines, `---`,
  `+++` and `diff --git` lines are scanned. Context lines and removed lines are skipped (unit
  case). The drafts are not scanned at all (finding 5).

## Criterion 3: the artifact set

EXECUTED, `cmp` of the clone's `build/artifacts` against the main tree's, read only:

- the same 17 files. `python.wasm`, `python-snapshot.wasm`, `python-stdlib.zip` and the twelve
  `LICENSES/*.txt` are byte for byte the same;
- `MANIFEST` differs in eight `recipe` lines only: the six changed scripts (steps 20, 30, 35, 40,
  50 and `common.sh`) and the two added files (`scripts/steps/apply_patches.sh`,
  `recipes/patches/README.md`). Each hash equals the file at `c6e27a7` (`shasum`);
- `SHA256SUMS` differs in `MANIFEST`'s line only.

The clone's set was rebuilt from step 40 after the trial. Steps 10 to 35 ran with the applier as
it was before the trial's `remove` fix. Without patches the applier exits before that code, so
this cannot change the bytes (READ, INFERRED).

## Criterion 4: the trial, as the landing notes tell it

- I did not re-run the trial. The account is consistent with what is in the clone (READ,
  EXECUTED): no trial patch, draft or CHANGELOG line is left in the tracked tree; the README count
  is 0; `MANIFEST` matches the current files. An empty, untracked
  `context/upstream/patches/` folder (13:02) is left from it. git ignores it; it is harmless.
- The two faults it found are fixed in the commit: the unit file uses `acmehost`, not an
  embedder name, and `test_no_embedder_name_in_code` passes; the applier's clean-up uses `remove`
  (READ).
- The trial patch only appended a comment. It did not exercise a deletion, an added file, or the
  rules on a tricky patch, so findings 1, 2 and 6 could not show there (INFERRED).

## The judge

See *Re-ran*. The scoreboard matches the landing notes' 175/179 with 0 fail. `gained 1` is the
new rules check. `test_patches.py` has 29 cases, all pass. The deletion case passes despite
finding 1, because it checks only the names of the drifted paths, not why (READ, EXECUTED).

## The docs

- **README (READ).** The row reads `| upstream patches carried | upstream patches carried: 0, each
  with an upstream pull request … |`. It says its label twice, so the rule's regex can match; it
  works, but reads oddly. *How it is built* and *Releasing* say "the source trees are their
  tarballs plus the recorded patches", as Decision 11 asks. The *Releasing* line runs past the
  file's width.
- **`recipes/patches/README.md` (READ).** Accurate in substance. "The judge's `patch_errors`
  names any of these" is too strong while finding 2 stands. It does not name the `Files:` rule.
- **`context/upstream/README.md` (READ).** Gives the header. It does not say that `released
  <version>` is written in the pinned file name's form (`3540100` for SQLite), which is the only
  form the rule reads right (finding 8).
- **CHANGELOG (READ).** One accurate entry under 0.1.0a3.
- **`AGENTS.md` (READ).** Still says "Until the specification that builds this lands, no patch is
  applied and the release workflow still fails on any diff against the pinned tarball". That is
  stale once this lands (finding 11). The constitution's own parenthesis in §4.1 expires by its
  own words.

## Acceptance criteria against evidence

1. *The checks exist and were seen failing before the change.* **Met in form.** The notes show
   the unit file failing to import against the old scripts, and the hostile-setting case failing
   against a stand-in applier. An import error is a weak "seen failing" for 29 cases. The
   deletion case shows it: it passes against an applier that does not delete (finding 1).
2. *`uv run pytest` green with `--accept-judge`.* **Pending the landing.** In the clone: exit 0,
   lost 0, grew 0, the judge changed in the files the specification names (EXECUTED).
3. *One full build from pins: binaries and licences byte for byte; `MANIFEST` only in `recipe`
   lines; `SHA256SUMS` only in `MANIFEST`'s line.* **Met** (EXECUTED, above).
4. *The trial patch.* **Met as reported** (READ, above); not re-run by me.
5. *A release dry run passes every job.* **Not shown.** The landing notes do not mention it.
   INFERRED: no job changes behaviour with no patch, except the step title.

## Findings, most severe first

1. **High. A patch that deletes a file leaves it in the tree, empty, and the judge agrees.**
   (`scripts/steps/apply_patches.sh:56-58, 69-72`)
   - The defect. Before a patch, the applier saves the mtime of every path `--numstat` lists,
     deleted ones included. After it, `touch -r "$WORK/mtime.$n" "$TREE/$rel"` runs for every
     saved path. `touch` creates a missing file. So the deleted path comes back as a 0-byte
     file with its old mtime.
   - Failure. EXECUTED (`battery-*.txt`, case 1): a `git diff` patch deleting zlib's `ChangeLog`
     applied with exit 0, and `ChangeLog` was then present, 0 bytes. The same on macOS sh,
     macOS dash and Linux dash. EXECUTED (`del.txt`): with the unit file's own `_delete` patch,
     the build-side tree ends with an empty `del.txt` and `tree_drift` gives `[]`. A tree where
     `del.txt` is really gone gives `['del.txt: missing']`: the judge fails the correct tree.
     The unpatched tree gives `del.txt: modified`, not `a recorded patch deletes it`, so that
     branch of `_patched_drift` can never fire.
   - Why it matters. INFERRED: a deletion is how one removes a module or a source a glob picks
     up. An empty `.py` imports instead of failing; an empty `.c` in a meson or make glob
     compiles to nothing. The build and the judge agree, so nothing would flag it.
   - Fix. Restore only files that exist after the patch: `touch -c -r …` or
     `[ -f "$TREE/$rel" ] && touch -r …`. In the unit case, assert that `del.txt` does not
     exist after the applier, and that the unpatched tree's drift line is `del.txt: a recorded
     patch deletes it`.

2. **Medium. `patch_shape_errors` trusts the `diff --git` line; git trusts the `---`/`+++`
   lines and reads sections the check never sees.** (`tests/harness/scan.py`,
   `patch_shape_errors`)
   - The defect. The touched set and the autotools rule come only from `diff --git` lines. The
     `---`/`+++` names are checked for a prefix, but not against the `diff --git` names. Once a
     hunk starts, `header` stays false, so a later `---`/`+++` pair with no `diff --git` is never
     read.
   - Failure. EXECUTED (`scan/shapes.txt`, `shapes2.txt`, `hidden.txt`), each with git's own
     `--numstat`:
     - `diff --git a/src/a.c b/src/a.c` with `--- a/configure.ac` / `+++ b/configure.ac`: git
       edits `configure.ac`. `patch_errors` with `Files: src/a.c` → `[]`.
     - A git section for `src/a.c`, then a plain `--- a/Makefile.am` / `+++ b/Makefile.am`
       section: git edits both. `patch_errors` with `Files: src/a.c` → `[]`.
     - `diff --git a/a.c b/a.c` with `+++ b/b.c`: git edits `b.c`; the check says `a.c`.
   - So Decision 6's autotools rule and its `Files:` rule can both be passed by a patch that does
     the thing they forbid. A reviewer reading the patch would likely see it; the rule exists so
     that the judge sees it too.
   - Fix. Either take the touched set from git itself (`git apply --numstat -z --summary`, run
     with the applier's scrubbed environment, and compare it with the `diff --git` names), or:
     require each `--- a/X` / `+++ b/X` to equal its `diff --git a/X b/X`; count hunk lines from
     each `@@ -a,b +c,d @@`, and refuse any `---`/`+++` line outside a git header. Add the three
     cases above as unit cases.

3. **Medium. `tree_drift` unpacks a download into the system temporary folder.**
   (`tests/harness/pins.py:_patched_drift`; Decision 9)
   - The defect. §4.8 and `AGENTS.md` say downloads "unpack under `downloads/` and `build/`,
     never into the system". The harness reads that strictly: `tests/unit/conftest.py` makes its
     folders under `build/harness/`, "never the system temp dir: §4.8" (READ). The patched check
     extracts the whole pinned tarball under `tempfile.gettempdir()` (EXECUTED:
     `/var/folders/…/T`, 144 MB for CPython).
   - Why the Decision chose it. The pre-build review's finding 2 showed that extracting under
     `build/harness/` without the ceiling skips every patch. The applier now sets the ceiling.
     EXECUTED (battery 7): a relative tree inside an outer repository's ignored `build/`, with
     `GIT_DIR` and `GIT_WORK_TREE` set, applies cleanly with the same bytes.
   - Fix. Extract under `paths.HARNESS_TMP` (`tempfile.TemporaryDirectory(dir=…)`), and add a
     unit case that runs `tree_drift` there. Or answer in writing why the system temporary folder
     is "not the system" for §4.8, and amend the harness's comment to match. The spec decided
     this, so the answer belongs in the specification too.

4. **Medium. Finder litter in `recipes/patches/` turns the rules check red, today.**
   (`tests/harness/scan.py:patch_errors`)
   - The defect. `patch_errors` lists folders with `iterdir()` and does not skip
     `paths.OS_LITTER`, which every other listing in the judge skips (spec 011's F3, spec 018).
   - Failure. EXECUTED (`scan/drafts.txt`): a `.DS_Store` in `recipes/patches/` gives
     `only folders and README.md belong here`; one in `recipes/patches/numpy-2.5.2/` gives
     `not named NNNN-<slug>.patch`. `recipes/patches/README.md` exists today, so opening that
     folder in Finder on the owner's Mac makes `test_carried_patches_follow_the_rules` fail with
     no patch carried. (A `.DS_Store` in a draft folder is ignored, since that loop globs
     `*.md`.)
   - Fix. Skip names in `paths.OS_LITTER` in both loops; a unit case for each folder.

5. **Low. The drafts are not scanned for embedder names.** (`tests/checks/test_rules.py`,
   `CODE_DIRS`; Decision 11)
   - The defect. Decision 11 says the embedder rule scans "the drafts in full". The rule scans
     `CODE_DIRS` (`recipes`, `scripts`, `src`, `tests`, `fixtures`); the drafts are under
     `context/upstream/patches/`.
   - Failure. EXECUTED (`scan/drafts.txt`): a draft containing an embedder's name gives no hit.
     That text goes upstream under the project's name.
   - Fix. Add `context/upstream/patches` to the scan in `test_no_embedder_name_in_code` (or a
     separate check), with a unit case.

6. **Low. A path git quotes escapes the mtime rule.** (`scripts/steps/apply_patches.sh:50-58`)
   - The defect. `--numstat` without `-z` quotes a non-ASCII name (`"caf\303\251.c"`). The
     applier then looks for a file of that literal name, finds none, and restores nothing.
   - Failure. EXECUTED (battery 1): the added `café.c` got the current time (1792257220), not
     the newest file's (1705948357). The same for a changed file with such a name (INFERRED).
     No pinned tarball has a non-ASCII name today (EXECUTED: 0 in all seven), so nothing is
     affected now.
   - Fix. `--numstat -z` (NUL-separated, unquoted), or `-c core.quotePath=false` in
     `git_clean`, plus a unit case with a non-ASCII added file.

7. **Low. A new executable file passes the shape rules.** (`PATCH_SHAPES`)
   - EXECUTED (`scan/shapes.txt`): `new file mode 100755` → no error; git creates the file
     `0755`. Decision 6 forbids mode changes and links, so a new script a build might run is the
     one mode left. Modes are not compared by `tree_drift` either.
   - Fix. Refuse `new file mode` other than `100644`, or have Decision 8's review list it with
     its mode. One sentence in `recipes/patches/README.md`.

8. **Low. Version and path forms the rules read wrongly, and the docs do not warn.**
   - `released 3.55.0` for `sqlite-autoconf-3540100` (a later release, written as SQLite writes
     it) fails with "released in 3.55.0, which sqlite-autoconf-3540100 has: delete the patch"
     (EXECUTED). It fails safe, but the message points the wrong way. Fix: say the form in
     `context/upstream/README.md`, and add "write it as the pinned file name does" to the error.
   - A patch to a path with a space is refused (EXECUTED), as is any path git quotes. numpy has
     4,587 such paths, all under `vendored-meson/meson/test cases/` (EXECUTED); none is a likely
     target. Accept it, and say so in `recipes/patches/README.md`.

9. **Low. The applier's header says it sources nothing; it sources `remove.sh`.**
   (`scripts/steps/apply_patches.sh:5, 27`, Decision 3)
   - The landing notes say so, and the judge runs it alone. Fix the comment and Decision 3's
     words, or inline the three-attempt removal.

10. **Low. `extractall(filter="tar")` could be `filter="data"`.** (`tests/harness/pins.py`)
    - EXECUTED: `"data"` extracts all seven tarballs to the same file list. It refuses absolute
      or escaping links and special files, which a pinned tarball should never have. Modes are
      not compared, so nothing else changes. The release workflow already uses `"data"`
      (`release.yml:232`).

11. **Low. Docs left stale on landing.**
    - `AGENTS.md` lines 22-24 ("Until the specification that builds this lands …").
    - The README row repeats its label; the *Releasing* line is over width.
    - `recipes/patches/README.md` says the judge names any forbidden shape (see finding 2).

## Constitution checks

- §4.1: the mechanism matches. Patches apply after the hash check (READ, `pinned()` in each
  step), are hashed as `recipe` lines (READ), named in the CHANGELOG and paired with a draft (the
  rules check). The release check compares with "exactly the recorded patches". Findings 1 and 2
  weaken "exactly": a deletion is not carried as written, and the rules can miss a touched file.
- §4.2 pins: holds. Nothing new is fetched.
- §4.5 embedder-neutral: holds in code; the drafts are unchecked (finding 5).
- §4.6 the artifact set: unchanged, byte for byte (criterion 3).
- §4.8 downloads are untrusted: the judge's extraction into the system temporary folder is at odds
  with the project's own reading (finding 3). `git apply` keeps writes inside the tree.
- §4.9 tests count: holds. No check reads a clock; the 6.0 s above is a benchmark fact.
- §4.10 evidence: the landing notes label their claims; criterion 5 is not reported.
- §4.13 tooling: ruff and pytest green; no dependency added.
- §7: nothing tripped. No source tree is changed by hand; no commit, push or tag.

## Disposition (filled in by the author, then confirmed by the reviewer)

Every finding is fixed, staged in the clone on `c6e27a7` (`git diff --cached`); the spec gains
"Revised against the build review". EXECUTED there: step 90 re-run; the judge 175/179, 0 fail,
593 passed, lost 0, grew 0; `tests/unit/test_patches.py` 35 passed; ruff clean.

1. **Fixed:** `touch -c -r`; the case asserts the deleted file is gone and that an empty file in
   its place is drift ("a recorded patch deletes it"); the `touch -r` stand-in fails it.
2. **Fixed:** `patch_shape_errors` takes paths from `git apply --numstat -z` and modes from
   `--summary` (outside any repository, configuration cleared); your two shapes are cases.
3. **Fixed:** `tree_drift` extracts under `paths.HARNESS_TMP` (`build/harness`).
4. **Fixed:** `patch_errors` skips `paths.OS_LITTER` names in both loops and among drafts (a case).
5. **Fixed:** the rules check also scans `context/upstream/patches/` for embedder names.
6. **Fixed:** the applier passes `-c core.quotePath=false`; an added `café.c` gets the newest
   time (a case).
7. **Fixed:** a new file must be mode 100644 (a case; `--summary` and the text rule).
8. **Fixed:** a released version in another form gets "write the released version as the pinned
   file name does (…)" (a case), and both READMEs say so. Paths with spaces are now read by
   git, not split by the rule.
9. **Fixed:** the header and Decision 3 say the applier sources `remove.sh`.
10. **Fixed:** `filter="data"`.
11. **Fixed:** `AGENTS.md`, §4.1's status sentence ("built by spec 020"), the README's row label,
    and `recipes/patches/README.md` (it now says the rules read patches as git does).


## Verdict

Does not land yet: the applier turns a deleted file into an empty one and the judge agrees
(finding 1), and the shape rules can be passed by a patch that edits a file they never see
(finding 2). Both are small fixes with unit cases. Findings 3 and 4 should be fixed or answered
with them.

## Confirmation

- **Date:** 2026-10-17
- **Reviewer:** the same fresh agent (Claude Opus 5.5); not the author.
- **Reviewed:** the fixes staged in the clone on `c6e27a7` (`git diff --cached`: 10 files), plus
  one unstaged change to `recipes/patches/README.md` (C2), and the author's Disposition above.
- **Re-ran (EXECUTED).** Outputs are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev020b/confirm/`:
  - `battery.sh` under macOS `/bin/sh` and `/bin/dash`, and under Debian dash with GNU tools and
    git 2.47.3 (`battery-macos.txt`, `battery-linux.txt`);
  - `delprobe.py` (`del.txt`); the four scan probes (`scan.txt`); `pinsprobe.py` (`pins.txt`);
  - `confirmprobe.py` (`confirmprobe.txt`): no git on `PATH`, the temporary folder inside a git
    repository, odd prefixes, a deleted executable, and the drafts' embedder scan;
  - `whereprobe.py`: `tree_drift` with a stand-in applier that prints the tree it is given;
  - `uv run pytest -p no:cacheprovider` in the clone (`pytest-full.txt`): `175/179 pass · 0 gap ·
    4 blocked · 0 fail (unit suite 418/425, 7 skipped)`; `593 passed, 11 skipped`; ratchet
    `lost 0 · gained 1 · grew 0`; **exit 0**. No `--accept`. ruff check and format clean.
  - I committed nothing. The clone's `git status` is as I found it (10 staged, 1 unstaged).

### Each finding against its fix

1. **Deletion — closed.** EXECUTED: zlib's `ChangeLog` is now absent after the applier, on all
   three shells. With the unit file's deletion patch, the unpatched tree gives `del.txt: a
   recorded patch deletes it`, the applied tree has no `del.txt`, and `tree_drift` gives `[]`.
   The unit case now asserts both.
2. **Hidden sections — closed.** EXECUTED: the `configure.ac`-under-`src/a.c` patch and the
   plain `Makefile.am` section after a hunk each now give "changes the autotools input" and a
   `Files:` mismatch from `patch_errors`. `+++ b/b.c` under `diff --git a/a.c b/a.c` gives
   `b.c` as touched, which is what git edits. Paths with spaces, quoted or not, are now read
   correctly, not refused.
   - **No git:** `patch_shape_errors` returns `git cannot read it: git is not on PATH …` and an
     empty touched set (EXECUTED). It fails closed. With no patch carried, `_git_reads` is never
     called, so a host without git stays green (READ).
   - One gap: C1 below.
3. **System temporary folder — closed.** EXECUTED: the stand-in applier was handed
   `…/repo/build/harness/patched-_ir100l7/zlib-1.3.1`, and nothing `patched-*` is left after.
   On CPython with one patch, the drift is still `['Modules/main.c: modified']`: the patch
   applied under `build/`, inside the outer repository, so the ceiling holds there.
4. **Finder litter — closed.** EXECUTED: a `.DS_Store` in `recipes/patches/`, in a patch folder
   and in a draft folder each give `[]`. There is a unit case.
5. **Drafts' embedder names — closed.** EXECUTED: `embedder_hits(root,
   ["context/upstream/patches"], …)` finds a name in a draft, and returns `[]` when the folder is
   absent. The rules check calls it (READ).
6. **Quoted names — closed.** EXECUTED: the added `café.c` now gets the newest file's mtime
   (1705948357) on all three shells. There is a unit case.
7. **New executable file — closed.** EXECUTED: `new file mode 100755` gives two errors (the text
   rule and `--summary`). Deleting an existing `100755` file is now refused too ("only plain
   files"). That is stricter than asked, and fails safe.
8. **Version form — closed.** EXECUTED: `released 3.55.0` and `3.54.1` for SQLite, and
   `v3.15.1` for CPython, now give "write the released version as the pinned file name does
   (…)". `released 3540100` still says "delete the patch"; `3550000` and `3.15.1` pass. Both
   READMEs say the form.
9. **Header — closed** (READ).
10. **`filter="data"` — closed.** EXECUTED: all seven tarballs extract to the same file lists
    under `"data"` as under `"tar"` (5,434, 8,365, 1,597, 253, 56, 655 and 49 files).
11. **Docs — closed** (READ), with C2 and C3 below.

Criterion 3 still holds (EXECUTED). Step 90 was re-run at 13:25. The three binaries are byte for
byte the main tree's. `MANIFEST` still differs only in the eight `recipe` lines. As a benchmark
fact, the patched CPython `tree_drift` took 7.6 s against 2.5 s unpatched, in one run.

### Still open

- **C1. Low. `_git_reads` sets its ceiling to its own working folder, so git still finds an
  enclosing repository.** (`tests/harness/scan.py:_git_reads`)
  - The defect. `cwd=home` and `GIT_CEILING_DIRECTORIES=home`. The pre-build review showed that
    a ceiling equal to the starting folder does not stop discovery: it must be the parent. The
    applier gets this right.
  - Failure. EXECUTED: with `tempfile.tempdir` inside a git repository's subfolder, a correct
    one-file patch gives `['p: changes no file']`. git skipped it as outside the prefix. The same
    happens with `GIT_DIR` and `GIT_WORK_TREE` set in the caller. It fails closed (a false
    failure, never a false pass), and only when `TMPDIR` is inside a repository. The Disposition's
    "outside any repository" does not hold then.
  - Fix. One line: run git in a subfolder of `home` (`cwd=home/w`) with the ceiling at `home`,
    or set the ceiling to `os.path.dirname(home)`.
- **C2. Must do before the commit: `recipes/patches/README.md` is changed but not staged.**
  - EXECUTED: the index holds the old file (sha256 `aae45aa6…`). The working tree and the
    rebuilt `MANIFEST` hold `5642227f…`.
  - Committing the staged set alone would land a `MANIFEST` whose `recipe` line names bytes not
    in the commit. Stage it, then check `git diff --cached --stat` (AGENTS.md rule 9).
- **C3. The constitution's §4.1 was edited.**
  - The staged change rewrites §4.1's parenthesis, from "until the specification that builds
    this lands, no patch is applied …" to "built by spec 020". My review did not ask for it: the
    parenthesis expires by its own words.
  - The constitution says to change it "only with the owner's explicit decision, recorded in the
    change". The edit is only factual, but the rule has no exception.
  - Either the owner approves it, recorded in the commit, or it is unstaged and left as it was.
    The `AGENTS.md` edit is fine either way.
- **C4. Low. Decision 6 still says "every path with `a/` or `b/` prefixes"**, but nothing checks
  that now.
  - EXECUTED: `--- a.c`/`+++ a.c`, and `x/`/`y/` prefixes, give no error. A traditional
    `/etc/a.c` is read as `etc/a.c` inside the tree.
  - Build and judge read the same way (both run `git apply -p1`), so nothing escapes.
  - Drop the words from Decision 6, or put the prefix check back. The spec's new status line also
    runs past the file's width.

## Disposition of the confirmation (filled in by the author)

- **C1:** fixed: `_git_reads` runs git in a subfolder of its temporary folder, below the
  ceiling, so git never finds an enclosing repository.
- **C2:** fixed: `recipes/patches/README.md` is staged; the `MANIFEST` step 90 made records the
  bytes the commit holds.
- **C3:** reverted. The §4.1 edit is undone; the constitution is exactly as the owner approved
  it. Its sentence "until the specification that builds this lands, no patch is applied and the
  old zero-diff check stands" expires by its own words with this landing; whether to reword it is
  recorded for the owner (question 33).
- **C4:** fixed: Decision 6 says "no path with a `..` part or outside the tree, as git reads the
  patch"; the status line is wrapped.
- The leftover placeholder list is removed.

Your verdict made the change land with these.

- C1:
- C2:
- C3:
- C4:

### Verdict of the confirmation

Lands once C2 is staged and C3 is settled: the owner approves the §4.1 edit, or it is unstaged.
Fix C1 and C4 in the same pass, one line each; they need no further review.
