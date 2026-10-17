# 018 — Finder litter never breaks a build

- **Status:** drafted 2026-10-17 and revised against its pre-build review
  (`../reviews/018-finder-litter-never-breaks-a-build-spec-2026-10-17.md`); ready to build, with
  the confirmation's two conditions made.
- **Owner:** Clay Gendron
- **Kind:** the build recipe (`scripts/steps/*.sh`, a new `scripts/steps/remove.sh`,
  `scripts/build.sh`, a new `scripts/litter.py`, `scripts/make_stdlib_zip.py`,
  `scripts/assemble_artifacts.py`), judge additions in `tests/`, `README.md`.
- **Depends on:** 003 (the pinned build), 011 (`OS_LITTER` in the judge).
- **Research it stands on:** `../research/2026-10-17-finder-litter-breaks-a-desktop-build.md`
  (three failed desktop builds in one hour, each from a `.DS_Store` that Finder wrote into
  `build/` while a step ran; EXECUTED).

## The problem

macOS Finder writes `.DS_Store` files into folders a person has browsed, at any instant. Windows
Explorer writes `Thumbs.db` and `desktop.ini` the same way. Such a file is litter: no build input
reads it, and no artifact should carry it. Today a build fails on it in two ways:

- A step's `rm -rf` of its old outputs fails with "Directory not empty" when Finder writes a new
  `.DS_Store` into a folder between `rm`'s unlinks (steps 10 and 40, EXECUTED).
- Step 70 stops with "`.DS_Store` comes from two inputs" when litter sits in two input trees,
  because the zip refuses a name that two inputs give (EXECUTED). It failed closed; with litter in
  one tree only, the litter would be packed into the zip.

No wrong artifact was made: every failure stopped the build, and a litter file in the zip would
change its bytes, which the same-bytes gate catches. The cost is a failed build and a person
deleting files by hand.

## Decisions

1. **Remove with retries, in one place.** A new `scripts/steps/remove.sh` defines
   `remove PATH...`, and both `common.sh` and `scripts/build.sh` source it, so there is one copy.
   For each path it runs `rm -rf` up to three times, the first two quietly and the third with its
   error shown, so the last line names the cause; then, if the path still exists (or is a
   dangling link), it prints `ERROR: cannot remove <path>` and exits 1. Three is a count, not a
   time: there is no sleep between attempts.

   ```sh
   remove() {
     for p in "$@"; do
       rm -rf "$p" 2>/dev/null || rm -rf "$p" 2>/dev/null || rm -rf "$p" || true
       if [ -e "$p" ] || [ -L "$p" ]; then
         echo "ERROR: cannot remove $p" >&2
         exit 1
       fi
     done
   }
   ```

   Every `rm -rf` under `scripts/` becomes `remove`, `common.sh`'s bytecode-cache clean-up
   included: `find … -exec rm -rf {} +` fails the step under `set -e` when one `rm` fails (the
   review, EXECUTED), so it becomes `find … -type d -prune | while read -r d; do remove "$d";
   done`. A writer that adds a file during one attempt is removed by the next. **The residual:**
   a writer that writes into a folder continuously, with no pause, can still win all three
   attempts (the review, EXECUTED); Finder does not write that way, so the step then fails with
   the line above, as it fails today, and never makes a wrong artifact.
2. **One litter set for the scripts.** A new `scripts/litter.py` holds
   `OS_LITTER = frozenset({".DS_Store", "Thumbs.db", "desktop.ini"})`, the judge's set
   (`tests/harness/paths.py`); `make_stdlib_zip.py` and `assemble_artifacts.py` import it (each
   runs with `scripts/` on `sys.path`). The scripts cannot import the judge's harness, so the set
   is written twice, and a unit check holds the two equal.
3. **The zip never packs litter.** `make_stdlib_zip.py`'s `SKIP_NAMES` gains `OS_LITTER`. The
   walk skips them in `--lib` and every `--tree`, so two trees with litter no longer collide and
   one tree's litter is never packed. The wheels it reads are pinned zips, not folders a person
   browses, so they need no filter. No pinned tarball or wheel holds a file with one of these
   names (the review, EXECUTED), so no real file is skipped.
4. **The licences never pack litter.** `assemble_artifacts.py` lists
   `build/pandas-3.0.6/LICENSES/` with `iterdir()` and packs every entry into
   `LICENSES/pandas.txt`; a `.DS_Store` there changes that file and nothing fails (the review,
   EXECUTED). The listing skips `OS_LITTER` names.
5. **The artifact set never lists litter, and step 90 removes as the shell steps do.**
   `assemble_artifacts.py` writes into a folder it has just made (`build/artifacts.new`). Before
   it lists that folder's files for `SHA256SUMS`, it deletes any file there named in
   `OS_LITTER`. Its two `shutil.rmtree(…, ignore_errors=True)` calls (of `artifacts.new` before,
   and of `artifacts` before the rename) become `_remove(path)`: up to three `rmtree` attempts, each
   catching `OSError` and deciding by whether the path still exists, as `remove.sh` does, so a
   path already gone (`artifacts.new` usually is) is success; then
   `SystemExit("cannot remove <path>")` if it still exists, so a failure is one line, not a
   later traceback. Litter written into the set after the listing is not in `SHA256SUMS`; the
   judge's `sums_errors` ("… is not listed in SHA256SUMS") and spec 016's wheel rule 3 fail on
   it. That is right: a shipped set must hold only what it lists.
6. **The judge stays strict about `build/artifacts/`.** Finder can write a `.DS_Store` into the
   finished set after a build, and the judge's `SHA256SUMS` check then fails, naming the file.
   The judge is not loosened: a wheel built from that folder would carry the file. The memo and
   the README's build section name the remedy: `find build/artifacts -name .DS_Store -delete`.
7. **Source trees keep any litter.** A `.DS_Store` inside an unpacked source tree is read by no
   compiler or configure script (INFERRED; the memo's rebuild after deleting it gave the same
   artifact set, byte for byte, EXECUTED), and Decisions 3 and 4 keep it out of the set.
   Detecting files a build adds inside a source tree stays on the scoreboard's "not
   machine-checked" list.
8. **What the change does to the artifact set.** `python.wasm`, the snapshot, the zip and the
   licences are byte for byte as before when no litter is present (every CI host). `MANIFEST`
   records a hash of every tracked script, so the changed scripts' `recipe` lines change, and
   with them `MANIFEST`'s line in `SHA256SUMS` (the review, READ and EXECUTED). So the main tree's
   set is rebuilt when this lands, and the next release carries the new `MANIFEST`.

## Intent

A person can build on a Mac with a Finder window open on `build/`, and the build either succeeds
with the same artifact set or fails for a reason that is not litter.

## Design

- `scripts/steps/remove.sh` (Decision 1), sourced by `common.sh` and `scripts/build.sh`.
- Each `rm -rf` in `scripts/steps/*.sh` (steps 10, 20, 30, 35, 40, 50, 60, 80) and
  `scripts/build.sh` becomes `remove`; `common.sh`'s cache clean-up becomes the `while read` loop.
- `scripts/litter.py` (Decision 2); `make_stdlib_zip.py`'s `SKIP_NAMES` and
  `assemble_artifacts.py`'s licence listing and pre-listing clean-up use it; `assemble_artifacts.py`
  gains `_remove` and `drop_litter(folder)`.
- The README's build section and the memo: Decision 6's remedy.
- Checks:
  - In `tests/unit/test_scan.py`, a scan rule `bare_rm_hits`: in every shell file under
    `scripts/` (by `is_shell`), except `scripts/steps/remove.sh`, no `rm` whose flags include both
    a recursive flag (`r` or `R`) and `f`, in any spelling (`-rf`, `-fr`, `-Rf`, `-r -f`,
    `--recursive --force`); its own unit cases include each spelling, and the real `scripts/`
    tree has no hit.
  - A new `tests/unit/test_build_scripts.py`:
    - `remove`, sourced from `remove.sh` under `sh`, with `rm` replaced by a shell function that
      counts its calls and fails a set number of times: fails once → exit 0, the path gone,
      exactly 2 calls; always fails → exit 1, `cannot remove` on standard error, exactly 3 calls;
      a dangling link is removed. No background writer, no timing. On a host without a POSIX
      `sh` the case is blocked, naming that need, never passed or failed;
    - `make_stdlib_zip.walk` over two temporary trees, each with a `.DS_Store`, a `Thumbs.db`
      and a real module: only the modules are yielded;
    - `assemble_artifacts.drop_litter` on a temporary folder: litter gone, other files kept;
      the licence listing helper skips litter;
    - `scripts/litter.py`'s `OS_LITTER == paths.OS_LITTER`.
- Each check is seen failing first against the current scripts (the scan rule, the walk, the
  licence listing) or a stand-in (`remove` without the retry).

## Scope

In: the above. Out:
- Other litter (`._*` AppleDouble files on non-APFS volumes, editor swap files): not seen; the
  retry already covers their effect on `rm`, and the zip's two-inputs rule still fails closed on
  them.
- Detecting files a build adds inside a source tree (Decision 7).
- Moving a folder aside before removing it, which would beat even a continuous writer: Finder
  is not one, and the residual fails closed.

## Acceptance criteria

1. The checks exist and were seen failing before the change.
2. `uv run pytest` is green with `--accept-judge`, after the main tree's set is rebuilt with
   the changed scripts (Decision 8).
3. One full build from pins in a clean clone with this change gives `python.wasm`, the
   snapshot, the zip and every licence file byte for byte as the reviewed set; `MANIFEST`
   differs only in the `recipe` lines of the changed and added scripts, and `SHA256SUMS` only in
   `MANIFEST`'s line. Then steps 70 to 90, re-run with a `.DS_Store` placed in two of the zip's
   input trees and in pandas' `LICENSES/`, give the same bytes again.
4. A release dry run passes every job.

## Landing notes

Not built.
