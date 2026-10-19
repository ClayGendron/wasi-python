# 090 — the build and its artifact checks agree on one litter list

- **Status:** **drafted 2026-10-19** on `spec/089-host-litter-never-reaches-a-verdict` from main
  `3866f56` (committed with 089 for review; built on a branch of its own). Build-class, so a
  fresh agent reviews it before it is built (§5.6).
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** **build-class** (§5.7): it touches `scripts/` and `release/`. Files:
  `scripts/litter.py`, `scripts/make_stdlib_zip.py`, `scripts/assemble_artifacts.py`,
  `release/version.py`, `tests/harness/paths.py` (`OS_LITTER`), `tests/harness/artifacts.py`
  (`sums_errors`, `wheel_errors`), the regrtest and upstream `left_out` facts, the repo's
  `.gitignore`, the README's Mac note, and their unit rows. With no litter present the artifact set
  is byte-identical (criterion 2).
- **Depends on:** spec 018 (the build's three-name litter set), which it widens. It does not need
  089: if 089 has landed, its `litter.is_litter` is replaced by the shared definition here.
- **Research it stands on:** `../research/2026-10-19-ds-store-in-the-judges-stages.md`, §2 (a
  read-only survey of every place the build walks, copies, hashes or zips a folder).

## The problem

macOS writes `.DS_Store` files into `build/` while a build runs (the memo, §1;
`../research/2026-10-17-finder-litter-breaks-a-desktop-build.md`). Spec 018 made the build skip
three names: `.DS_Store`, `Thumbs.db`, `desktop.ini`. Four gaps remain (READ, the memo's §2):

- AppleDouble `._x` files and `Icon\r` pass every filter: a `._x` becomes a zip member or a
  `SHA256SUMS` line; `._x.py` fails the zip's compile step.
- `release/version.py`'s `write_assets` walks `build/artifacts` with no filter at all, so a
  `.DS_Store` there enters the release tarball.
- The judge's `sums_errors` and `wheel_errors` fail on a `.DS_Store` in `build/artifacts` (the
  README's documented case), although no consumer of the set would carry it once the tarball packs
  its list.
- Step 90's untracked-file check and `paths.dirty_path` ignore `.DS_Store` only through the owner's
  global git ignore, so on another Mac they stop on it.

## Principle

Litter is never an input, so a walk that collects inputs skips it. A consumer of a set takes the
set's list, not its folder. A check that compares a folder with its list ignores litter names, and
only those: a real stray file still fails it.

## Intent

Nothing a desktop process writes into `build/` changes an artifact's bytes or a release asset, and
every check that catches a real stray file today still catches it.

## Decisions

1. **One litter definition.** `is_litter(name)`: `name in OS_LITTER or name.startswith("._")`, with
   `OS_LITTER` widened to `.DS_Store`, `Thumbs.db`, `desktop.ini`, `ehthumbs.db`, `Icon\r`,
   `.Spotlight-V100`, `.fseventsd`, `.Trashes`, `.TemporaryItems`, `.DocumentRevisions-V100`,
   `.apdisk`. In `scripts/litter.py` and `tests/harness/paths.py`; the existing unit check holds
   the two equal and gains the prefix rule. A unit row checks that no pinned tarball present holds
   a member with such a name.
2. **The collecting walks use it:** `make_stdlib_zip.py`'s `SKIP_NAMES` test, and
   `assemble_artifacts.py`'s `drop_litter`, `listed_files` and `licence_files`.
3. **The release tarball packs its list.** `write_assets` packs exactly the files `SHA256SUMS`
   names, plus `SHA256SUMS`, and fails on a listed file that is missing. It never walks the folder.
4. **The artifact-folder checks ignore litter names only.** `sums_errors` and `wheel_errors` skip
   `is_litter` names; any other unlisted file still fails, naming it.
5. **`left_out` keeps litter apart.** The CPython and upstream stages' `left_out` facts list litter
   in the build tree separately from real extra files, so a real one is never buried.
6. **The repo ignores litter itself.** `.gitignore` gains `.DS_Store`, `._*` and `Icon[\r]`.
7. **The README's Mac note** says what is left: nothing a desktop writes into `build/` changes an
   artifact; closing System Settings' Storage pane and Finder windows on the checkout stops the
   writers.

## Design

`scripts/litter.py` exports `OS_LITTER` and `is_litter`; `tests/harness/paths.py` keeps its own
copy, held equal by the existing unit check. Each collecting walk replaces its `name in OS_LITTER`
test with `is_litter(name)`. `write_assets` reads `SHA256SUMS` and packs those paths in its order.
`sums_errors` and `wheel_errors` drop `is_litter` names from the unlisted set before reporting.

## Scope

In: Decisions 1 to 7. Out: the judge's stages and grants (spec 089); spec 020's tree-versus-tarball
check (it walks a fresh extraction and reports by tarball name, unchanged); a check for files a
build adds inside a source tree (still not machine-checked); `release.yml`'s `find` checks (CI has
no desktop writer, and they compare with a list).

## Acceptance criteria

1. **The checks fail first.** On main: the widened-litter rows, the release tarball's list row and
   the artifact checks' litter rows fail.
2. **The same bytes.** A rebuild from pins with no litter present gives the reviewed artifact set
   byte for byte (`cmp` of the five files).
3. **Litter planted.** With `._x.py`, `Icon\r` and `.DS_Store` planted in `build/pandas-install`
   and `build/artifacts` before steps 70 to 90 and the release step: the same set, and a release
   tarball whose members equal `SHA256SUMS`' list plus itself.
4. **A real stray file still fails.** A planted `stray.py` in `build/pandas-install` enters the zip
   and fails the same-bytes gate; a planted `stray.bin` in `build/artifacts` fails `sums_errors`,
   naming it.
5. **The judge.** `ruff` green; the fast tier and one full run `-n 3` against a private copy of the
   reviewed set: no failure, no lost pass, no fuel moved.

## Landing notes

Not built yet.

One line: the build skips one shared litter list, the release packs its list, and the artifact
checks forgive litter names only, so a desktop's files never change an artifact and a real stray
file still fails.
