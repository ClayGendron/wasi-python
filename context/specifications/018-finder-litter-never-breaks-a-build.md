# 018 — Finder litter never breaks a build

- **Status:** landed 2026-10-17. Reviewed before build (`../reviews/018-finder-litter-never-breaks-a-build-spec-2026-10-17.md`) and after (`../reviews/018-finder-litter-never-breaks-a-build-2026-10-17.md`, with its confirmation).
- **Owner:** Clay Gendron
- **Kind:** the build recipe (`scripts/steps/*.sh`, a new `scripts/steps/remove.sh`, `scripts/build.sh`, a new `scripts/litter.py`, `scripts/make_stdlib_zip.py`, `scripts/assemble_artifacts.py`), judge additions in `tests/`, `README.md`.
- **Depends on:** 003 (the pinned build), 011 (`OS_LITTER` in the judge).
- **Research it stands on:** `../research/2026-10-17-finder-litter-breaks-a-desktop-build.md` (three failed desktop builds in one hour, each from a `.DS_Store` that Finder wrote into `build/` while a step ran; EXECUTED).

## The problem

macOS Finder writes `.DS_Store` files into folders a person has browsed, at any instant. Windows Explorer writes `Thumbs.db` and `desktop.ini` the same way. Such a file is litter: no build input reads it, and no artifact should carry it. Today a build fails on it in two ways:

- A step's `rm -rf` of its old outputs fails with "Directory not empty" when Finder writes a new `.DS_Store` into a folder between `rm`'s unlinks (steps 10 and 40, EXECUTED).
- Step 70 stops with "`.DS_Store` comes from two inputs" when litter sits in two input trees, because the zip refuses a name that two inputs give (EXECUTED). It failed closed; with litter in one tree only, the litter would be packed into the zip.

No wrong artifact was made: every failure stopped the build, and a litter file in the zip would change its bytes, which the same-bytes gate catches. The cost is a failed build and a person deleting files by hand.

## Decisions

1. **Remove with retries, in one place.** A new `scripts/steps/remove.sh` defines `remove PATH...`, and both `common.sh` and `scripts/build.sh` source it, so there is one copy. For each path it runs `rm -rf` up to three times, the first two quietly and the third with its error shown, so the last line names the cause; then, if the path still exists (or is a dangling link), it prints `ERROR: cannot remove <path>` and exits 1. Three is a count, not a time: there is no sleep between attempts.

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

   Every `rm -rf` under `scripts/` becomes `remove`, `common.sh`'s bytecode-cache clean-up included: `find … -exec rm -rf {} +` fails the step under `set -e` when one `rm` fails (the review, EXECUTED), so it becomes `find … -type d -prune | while read -r d; do remove "$d"; done`. A writer that adds a file during one attempt is removed by the next. **The residual:** a writer that writes into a folder continuously, with no pause, can still win all three attempts (the review, EXECUTED); Finder does not write that way, so the step then fails with the line above, as it fails today, and never makes a wrong artifact.
2. **One litter set for the scripts.** A new `scripts/litter.py` holds `OS_LITTER = frozenset({".DS_Store", "Thumbs.db", "desktop.ini"})`, the judge's set (`tests/harness/paths.py`); `make_stdlib_zip.py` and `assemble_artifacts.py` import it (each runs with `scripts/` on `sys.path`). The scripts cannot import the judge's harness, so the set is written twice, and a unit check holds the two equal.
3. **The zip never packs litter.** `make_stdlib_zip.py`'s `SKIP_NAMES` gains `OS_LITTER`. The walk skips them in `--lib` and every `--tree`, so two trees with litter no longer collide and one tree's litter is never packed. The wheels it reads are pinned zips, not folders a person browses, so they need no filter. No pinned tarball or wheel holds a file with one of these names (the review, EXECUTED), so no real file is skipped.
4. **The licences never pack litter.** `assemble_artifacts.py` lists `build/pandas-3.0.6/LICENSES/` with `iterdir()` and packs every entry into `LICENSES/pandas.txt`; a `.DS_Store` there changes that file and nothing fails (the review, EXECUTED). The listing skips `OS_LITTER` names.
5. **The artifact set never lists litter, and step 90 removes as the shell steps do.** `assemble_artifacts.py` writes into a folder it has just made (`build/artifacts.new`). Before it lists that folder's files for `SHA256SUMS`, it deletes any file there named in `OS_LITTER`, and the listing (`listed_files`) skips those names too, so litter written after the clean-up is never hashed into `SHA256SUMS`. Its two `shutil.rmtree(…, ignore_errors=True)` calls (of `artifacts.new` before, and of `artifacts` before the rename) become `_remove(path)`: up to three attempts, each unlinking a link or a file, or running `rmtree(ignore_errors=True)`, which goes on past an entry as `rm -rf` does, and deciding by whether the path still exists, so a path already gone (`artifacts.new` usually is) is success; then `SystemExit("ERROR: cannot remove <path>")` if it still exists, so a failure is one line, not a later traceback. Litter in the set that is not in `SHA256SUMS` fails the judge's `sums_errors` ("… is not listed in SHA256SUMS") and spec 016's wheel rule 3. That is right: a shipped set must hold only what it lists.
6. **The judge stays strict about `build/artifacts/`.** Finder can write a `.DS_Store` into the finished set after a build, and the judge's `SHA256SUMS` check then fails, naming the file. The judge is not loosened: a wheel built from that folder would carry the file. The memo and the README's build section name the remedy: `find build/artifacts -name .DS_Store -delete`.
7. **Source trees keep any litter.** A `.DS_Store` inside an unpacked source tree is read by no compiler or configure script (INFERRED; the memo's rebuild after deleting it gave the same artifact set, byte for byte, EXECUTED), and Decisions 3 and 4 keep it out of the set. Detecting files a build adds inside a source tree stays on the scoreboard's "not machine-checked" list.
8. **What the change does to the artifact set.** `python.wasm`, the snapshot, the zip and the licences are byte for byte as before when no litter is present (every CI host). `MANIFEST` records a hash of every tracked script, so the changed scripts' `recipe` lines change, and with them `MANIFEST`'s line in `SHA256SUMS` (the review, READ and EXECUTED). So the main tree's set is rebuilt when this lands, and the next release carries the new `MANIFEST`.

## Intent

A person can build on a Mac with a Finder window open on `build/`, and the build either succeeds with the same artifact set or fails for a reason that is not litter.

## Design

- `scripts/steps/remove.sh` (Decision 1), sourced by `common.sh` and `scripts/build.sh`.
- Each `rm -rf` in `scripts/steps/*.sh` (steps 10, 20, 30, 35, 40, 50, 60, 80) and `scripts/build.sh` becomes `remove`; `common.sh`'s cache clean-up becomes the `while read` loop.
- `scripts/litter.py` (Decision 2); `make_stdlib_zip.py`'s `SKIP_NAMES` and `assemble_artifacts.py`'s licence listing and pre-listing clean-up use it; `assemble_artifacts.py` gains `_remove` and `drop_litter(folder)`.
- The README's build section and the memo: Decision 6's remedy.
- Checks:
  - In `tests/unit/test_scan.py`, a scan rule `bare_rm_hits`: in every shell file under `scripts/` (by `is_shell`), except `scripts/steps/remove.sh`, no `rm` whose flags include both a recursive flag (`r` or `R`) and `f`, in any spelling (`-rf`, `-fr`, `-Rf`, `-r -f`, `--recursive --force`), wherever `rm` stands (after `if`, `!`, `xargs`, an assignment; as `\rm`, `/bin/rm`, `/usr/bin/rm`; with its flags on a continued line); its own unit cases include each, and the real `scripts/` tree has no hit. A string or a trailing comment can match too, which fails closed.
  - A new `tests/unit/test_build_scripts.py`:
    - `remove`, sourced from `remove.sh` under `sh`, with `rm` replaced by a shell function that counts its calls and fails a set number of times: fails once → exit 0, the path gone, exactly 2 calls; always fails → exit 1, `cannot remove` on standard error, exactly 3 calls; a dangling link is removed, and one an `rm` reports removed but leaves gives exit 1; two paths given are both removed. No background writer, no timing. On a host without a POSIX `sh` the case is blocked, naming that need, never passed or failed;
    - `make_stdlib_zip.walk` over two temporary trees, each with a `.DS_Store`, a `Thumbs.db` and a real module: only the modules are yielded;
    - `assemble_artifacts.drop_litter` on a temporary folder: litter gone, other files kept; the licence listing helper and `listed_files` skip litter; `_remove` takes a path already gone as success, removes a folder, and raises `ERROR: cannot remove` for one that stays;
    - `scripts/litter.py`'s `OS_LITTER == paths.OS_LITTER`.
- Each check is seen failing first against the current scripts (the scan rule, the walk, the licence listing) or a stand-in (`remove` without the retry).

## Scope

In: the above. Out:
- Other litter (`._*` AppleDouble files on non-APFS volumes, editor swap files): not seen; the retry already covers their effect on `rm`, and the zip's two-inputs rule still fails closed on them.
- Detecting files a build adds inside a source tree (Decision 7).
- Moving a folder aside before removing it, which would beat even a continuous writer: Finder is not one, and the residual fails closed.

## Acceptance criteria

1. The checks exist and were seen failing before the change.
2. `uv run pytest` is green with `--accept-judge`, after the main tree's set is rebuilt with the changed scripts (Decision 8).
3. One full build from pins in a clean clone with this change gives `python.wasm`, the snapshot, the zip and every licence file byte for byte as the reviewed set; `MANIFEST` differs only in the `recipe` lines of the changed and added scripts, and `SHA256SUMS` only in `MANIFEST`'s line. Then steps 70 to 90, re-run with a `.DS_Store` placed in two of the zip's input trees and in pandas' `LICENSES/`, give the same bytes again.
4. A release dry run passes every job.

## Landing notes

Built 2026-10-17 by the implementer (Claude Opus 5.5) in a scratch clone of `8a2be32`. **Not yet reviewed and not accepted.** Every claim below was run (EXECUTED) on macOS arm64.

### What was built

- `scripts/steps/remove.sh` (Decision 1), sourced by `common.sh` and `scripts/build.sh`; every `rm -rf` in steps 10, 20, 30, 35, 40, 50, 60 and 80 and in `build.sh` is now `remove`; `common.sh`'s cache clean-up is `find … -prune | while read -r d; do remove "$d"; done`.
- `scripts/litter.py` (Decision 2); `make_stdlib_zip.py`'s `SKIP_NAMES` gains it (Decision 3); `assemble_artifacts.py` gains `licence_files` (Decision 4), `drop_litter` before the listing and `_remove` for its two removals (Decision 5, with the confirmation's condition A).
- The scan rule `bare_rm_hits` (`tests/harness/scan.py`) with its unit cases and the real-tree case in `tests/unit/test_scan.py`; `tests/unit/test_build_scripts.py` (condition B: a host without a POSIX `sh` skips with a need, never passes or fails).
- README (*How it is built*) and the memo: Decision 6's remedy.

### Seen failing first

- Against the old scripts: the scan finds 12 bare `rm -rf` lines; the old zip walk yields `.DS_Store`; `licence_files` and `drop_litter` do not exist (scratch `build018`).
- Against a stand-in `remove` with one attempt: `test_remove_retries_until_the_path_is_gone` (fails once, twice) and `test_remove_stops_after_three_attempts_with_one_line` fail.

### Criterion 3: the artifact set

- One full build from pins (`scripts/00_download.sh`, then `scripts/build.sh`, all eleven steps ok) in the clean clone, against the main tree's reviewed set: `python.wasm`, `python-snapshot.wasm`, `python-stdlib.zip` and all twelve licence files are byte for byte the same. `MANIFEST`'s non-recipe lines are equal; its `recipe` lines differ for exactly the twelve changed scripts and the two added ones (`litter.py`, `remove.sh`), and `SHA256SUMS` only in `MANIFEST`'s line.
- Steps 70 to 90 re-run with a `.DS_Store` in `build/pandas-install/pandas/`, in numpy's installed package and in `build/pandas-3.0.6/LICENSES/`, and a `Thumbs.db` in `build/pandas-install/`: all 17 files of the set are byte for byte as the clean build's.

### The judge

`uv run pytest` in the clone, on its own fresh set: 162/166 pass, 0 fail, 4 blocked; v1.5 18/18; unit suite 360/365; 522 passed, 9 skipped; ratchet lost 0, gained 0, grew 0; judge changed: `tests/harness/scan.py`, `tests/unit/test_scan.py`, `tests/unit/test_build_scripts.py`.

### On landing

The main tree's set is rebuilt from the landed scripts (steps 90, or 70 to 90), since its `MANIFEST` names the old scripts' hashes (Decision 8); then the `--accept-judge` run.

### Revised against the build review

The build review (`../reviews/018-finder-litter-never-breaks-a-build-2026-10-17.md`) found five things; each is fixed, and its confirmation checked them (EXECUTED there): `_remove` now goes on past an entry, as `rm -rf` does (step 90 alone against a Finder-like writer: 10 of 10, was 6 of 10); the scan rule matches `rm` wherever it stands; three mutations it found surviving each fail a new case; the listing skips litter (now `listed_files`, with a case); and the README, a skip reason and the `sh` cases' `PATH` are corrected. `test_a_zip_entry_is_never_litter` is removed: the walk case covers the zip's inputs, and a unit check should not read the artifact set outside the ratchet. Before the confirmation's re-run the judge read 162/166, 0 fail, unit suite 366/371, 528 passed, 9 skipped, ratchet lost 0, grew 0. One optional gap is left: no case pins that `_remove` goes on past an error inside a tree (the old body passes the cases); the Finder-like writer run above is the evidence for it.
