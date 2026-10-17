# Finder litter breaks a desktop build

- **Date:** 2026-10-17
- **Labels:** EXECUTED unless marked.

## What happened

A full build from pins in the main tree, on the owner's Mac, failed three times in one hour. Each
time the cause was a `.DS_Store` file that macOS Finder wrote into `build/` while the build ran:

1. Step 10's `rm -rf build/tools/...` failed with "Directory not empty": Finder wrote a new
   `.DS_Store` into a folder between `rm`'s unlinks.
2. Step 40's `rm -rf` failed the same way.
3. Step 70 stopped with ".DS_Store comes from two inputs (the second: build/pandas-install)". The
   zip step refuses a name that two inputs provide, so it failed closed instead of packing the
   litter.

After the last failure, `find build -name .DS_Store` listed one in 20 folders, including the
CPython, numpy, pandas, xz and SQLite source trees. Deleting them and re-running steps 70 to 90
gave the reviewed artifact set, byte for byte (`cmp` of `python.wasm`, the snapshot, the zip,
`MANIFEST` and `SHA256SUMS`).

The judge already ignores this litter (`OS_LITTER` in `tests/harness/paths.py`, from spec 011's
concurrency-check review). Scratch clones under the session's temporary directory never saw it.
INFERRED: a Finder window was open on, or had recently browsed, `build/`.

## What it means

- No wrong artifact was made: every failure stopped the build, and the same-bytes gate would catch
  a set that differed.
- A source tree with a `.DS_Store` in it is no longer byte-identical to its tarball. The
  zero-patch check compares the files the tarball holds, so it does not see an extra file. That
  is the scoreboard's "files a build adds inside a source tree", which is not machine-checked.

## What to do

A small recipe change, with its own review:
- each step's `rm -rf` of its outputs retries once, or removes `.DS_Store` files first;
- the zip step and `assemble_artifacts.py` skip `OS_LITTER` names when collecting inputs, as the
  judge does.

Until then, close any Finder window on `build/` while building, or run
`find build -name .DS_Store -delete` and re-run the step that failed.
