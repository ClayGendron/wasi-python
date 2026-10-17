# Carried patches

A change to a pinned project's source that cannot be a recipe file is carried here as a patch,
as the constitution's §4.1 allows: reviewed, recorded in `MANIFEST` by its hash, named in
`CHANGELOG.md`, matched by an upstream pull request drafted for the owner to send, and deleted
once an upstream release carries the fix (specification 020).

## Layout

- `<top>/NNNN-<slug>.patch`: `<top>` is the pinned tarball's top folder, the name the tree has
  under `build/` (`numpy-2.5.2`). `NNNN` is four digits, unique in the folder, and sets the
  order. A unified diff in `git diff` form, paths relative to the tree's top.
- Its pull request: `context/upstream/patches/<top>/NNNN-<slug>.md`, the same name, with six
  header lines (`Project`, `Against`, `Status`, `Title`, `Files`, `Why we carry it`) and the
  text for the upstream maintainers.

`scripts/steps/apply_patches.sh` applies a tree's patches right after its step unpacks it, and
the judge applies them the same way to check that each tree is its tarball plus exactly these.

Where a project forbids AI-written pull request descriptions (numpy does), the draft's body is
the facts for the owner to write from, not the text.

## What a patch may not contain

No link, no binary hunk, no mode change, no file but a plain one (mode 100644), no rename or
copy, no path outside the tree, and no change to an autotools input (`configure.ac`,
`configure.in`, `Makefile.am`, `*.m4`); patch the generated file the build runs instead. The
judge's `patch_errors` names any of these, reading each patch as git reads it (`git apply
--numstat` and `--summary`), so a section git would apply cannot hide from it.

A `released <version>` status writes the version as the pinned file name does: `2.5.2` for
`numpy-2.5.2`, `3540100` for `sqlite-autoconf-3540100`.

## Licence

A patch to a project's file carries that project's licence, as the same change upstream would.
The notices in `LICENSES/` are the projects' own and do not change.

## The life of a patch

Drafted with its pull request; reviewed with the specification that needs it; carried; sent by
the owner (the agent prepares the change rebased onto upstream in a scratch clone when asked);
merged; released upstream; then deleted here, with the pin moved to the release that carries it.
