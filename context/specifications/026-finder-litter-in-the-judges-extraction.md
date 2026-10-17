# 026 — Finder litter in the judge's own extraction

- **Status:** built 2026-10-17, awaiting its build review.
- **Owner:** Clay Gendron
- **Kind:** the judge's harness (`tests/harness/pins.py`), a unit check in
  `tests/unit/test_patches.py`.
- **Depends on:** 018 (OS litter: `paths.OS_LITTER`), 020 (the patched zero-diff check), both
  landed.
- **Research it stands on:** the judge runs of 2026-10-17 that failed
  `test_source_tree_matches_its_tarball[numpy]` with `.DS_Store: missing` and `modified`, on a
  machine where Finder showed `build/`.

## The problem

For a tree with carried patches (numpy today), spec 020's check extracts the pinned tarball under
`build/harness`, applies the patches, and compares every file of that fresh extraction with the
build tree. macOS Finder writes `.DS_Store` into folders it shows, and it wrote them into the
judge's fresh extraction while the check ran (EXECUTED: the findings named `.DS_Store` files that
the tarball does not hold, `tar -tzf … | grep -c DS_Store` is 0, and they came back after being
removed from the build tree). The release check on CI never sees Finder; a local judge run fails
for a file no build reads.

## Decisions

1. **A litter name the tarball does not hold is skipped** in the patched comparison:
   `.DS_Store`, `Thumbs.db` and `desktop.ini` (`paths.OS_LITTER`, spec 018's set), only when the
   path is not one of the tarball's members. A tarball that ships such a file is still compared
   byte for byte, so nothing the release takes from upstream escapes the check.
2. The unpatched comparison (`_tarball_drift`) already walks only the tarball's members, so
   litter in a build tree never counted there; it is unchanged.
3. Artifacts are untouched: spec 018's rules keep litter out of the zip and the wheel.
4. **The extraction is removed with retries** (spec 018's three), and one that still will not
   go stays under `build/harness`, which git ignores: Finder also wrote litter into it while
   `TemporaryDirectory` removed it, which failed the check with `OSError` 66 (EXECUTED).

## Intent

A Finder window cannot fail the judge; an upstream file still cannot change unseen.

## Design

```
tests/harness/pins.py         _patched_drift skips untracked litter; _remove_tree
tests/unit/test_patches.py    the litter check
```

## Scope

In: the patched comparison and its clean-up. Out: the build trees themselves (spec 018 keeps
litter out of the artifacts); any change to what counts as drift for a file the tarball holds.

## Acceptance criteria

1. `test_os_litter_in_the_judges_own_extraction_is_not_drift`, seen failing first: the real
   applier, then litter written into the extraction, gives no drift.
2. `uv run pytest` green with `--accept-judge`; lost 0; grew 0.

## Landing notes

Built 2026-10-17 by the implementer (Claude Opus 5.5). EXECUTED on macOS arm64: the unit check
failed first with `['.DS_Store: missing', 'sub/Thumbs.db: missing']` and passes with the change;
`tests/unit/test_patches.py` 37 passed. Not yet reviewed.
