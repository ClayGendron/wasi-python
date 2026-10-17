# 018 — Finder litter never breaks a build

- **Status:** drafted 2026-10-17, awaiting its pre-build review.
- **Owner:** Clay Gendron
- **Kind:** the build recipe (`scripts/steps/*.sh`, `scripts/make_stdlib_zip.py`,
  `scripts/assemble_artifacts.py`) and a judge addition in `tests/`.
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

1. **Remove with retries.** `scripts/steps/common.sh` gains `remove PATH...`. For each path it runs
   `rm -rf` up to three times, stopping at the first that succeeds; if the path still exists after
   the third, the step dies with one line naming it. A writer that adds a file during one pass is
   removed by the next. Three is a count, not a time: there is no sleep between passes. Every step
   uses `remove` for its outputs instead of `rm -rf`; `common.sh`'s own `find … -exec rm -rf` of
   bytecode caches stays, since `find` goes on past an entry it cannot remove and the caches are
   not outputs. Why retries and not "delete the litter first": a writer can add litter after any
   deletion, so only a retry closes the window, and it covers any litter name, not just a list.
2. **The zip never packs litter.** `make_stdlib_zip.py`'s `SKIP_NAMES` gains `.DS_Store`,
   `Thumbs.db` and `desktop.ini`, the judge's `OS_LITTER` (`tests/harness/paths.py`). The walk
   skips them in every input tree, so two trees with litter no longer collide and one tree's
   litter is never packed. The scripts cannot import the judge's harness, so the set is written
   twice; a unit check holds the two equal.
3. **The artifact set never lists litter.** `assemble_artifacts.py` writes into a folder it has
   just made (`build/artifacts.new`). Before it lists that folder's files for `SHA256SUMS`, it
   deletes any file there whose name is in the same set. A litter file written after the listing
   is not in `SHA256SUMS`, so the wheel's rule 3 and `write_assets` would see an unlisted file:
   that stays a failure, which is right (it is rare, and failing closed is the point).
4. **Source trees keep any litter.** A `.DS_Store` inside an unpacked source tree is not read by
   any compiler or configure script (INFERRED; the memo's rebuild after deleting it gave the same
   artifact set, byte for byte, EXECUTED), and Decision 2 keeps it out of the zip. Detecting files
   a build adds inside a source tree stays on the scoreboard's "not machine-checked" list.
5. **The artifact set does not change.** With no litter present (every CI host), the build makes
   the same bytes as before: Decisions 1 and 3 remove only what is not there, and Decision 2 skips
   names no tree has.

## Intent

A person can build on a Mac with a Finder window open on `build/`, and the build either succeeds
with the same artifact set or fails for a reason that is not litter.

## Design

- `common.sh`:

  ```sh
  # Remove each path, retrying: Finder can write a .DS_Store into a folder while rm empties it
  # (spec 018).
  remove() {
    for p in "$@"; do
      for _ in 1 2 3; do
        rm -rf "$p" 2>/dev/null && break
      done
      [ ! -e "$p" ] && [ ! -L "$p" ] || die "cannot remove $p"
    done
  }
  ```

  Under `set -eu`, a failing `rm` inside an `&&` list does not stop the step.
- Each `rm -rf` of outputs in `scripts/steps/*.sh` (steps 10, 20, 30, 35, 40, 50, 60, 80) becomes
  `remove`. `scripts/build.sh`'s `rm -rf` of `build/artifacts` and `build/artifacts.new` does too,
  through a copy of the function, since `build.sh` does not source `common.sh`.
- `make_stdlib_zip.py`: `SKIP_NAMES = {"conftest.py", "meson.build", *OS_LITTER}` with
  `OS_LITTER = {".DS_Store", "Thumbs.db", "desktop.ini"}` and a comment naming the judge's copy.
- `assemble_artifacts.py`: before `files = sorted(...)`, unlink every file under `new` whose name
  is in `OS_LITTER`.
- Checks (unit, in `tests/unit/test_scan.py` or a new `tests/unit/test_build_scripts.py`):
  - the scan finds no `rm -rf` in `scripts/steps/*.sh` or `scripts/build.sh` outside the
    `remove` function and `common.sh`'s cache clean-up (a new scan rule, `bare_rm_hits`);
  - `remove` run through `sh` on a folder that a background writer refills: a fake `rm` on
    `PATH` that fails its first call (as `rm -rf` does when a file appears) and runs the real
    `rm` after: the folder is gone and the function returned 0; a fake that always fails: the
    function exits 1 with "cannot remove";
  - `make_stdlib_zip.walk` over two temporary trees, each with a `.DS_Store`, a `Thumbs.db` and a
    real module: only the modules are yielded;
  - `make_stdlib_zip.OS_LITTER == paths.OS_LITTER`;
  - `assemble_artifacts`' litter removal, as a function `drop_litter(folder)` that the check
    calls on a temporary folder.
- Each check is seen failing first against the current scripts (the scan rule and the walk) or
  against a stand-in (`remove` without the retry).

## Scope

In: the above. Out:
- Other litter (`._*` AppleDouble files on non-APFS volumes, editor swap files): not seen; the
  retry already covers their effect on `rm`, and the zip's two-inputs rule still fails closed on
  them.
- Detecting files a build adds inside a source tree (Decision 4).

## Acceptance criteria

1. The checks exist and were seen failing before the change.
2. `uv run pytest` is green with `--accept-judge`.
3. Steps 70 to 90, re-run in a clone with this change, give the reviewed artifact set byte for
   byte (`cmp` of `python.wasm`, the snapshot, the zip, `MANIFEST` and `SHA256SUMS`), and the same
   steps with a `.DS_Store` placed in two of the zip's input trees succeed with the same bytes.
4. A release dry run passes every job.

## Landing notes

Not built.
