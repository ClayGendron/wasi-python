# Carrying a patch

This guide shows you how to carry a change to a pinned project's source, and how the change leaves again. Read it when a recipe file cannot do the job.

## Try a recipe file first

Most adaptations to WASI need no change to upstream source. A *recipe file* under [`recipes/`](https://github.com/ClayGendron/wasi-python/tree/main/recipes) does the job from the outside: a meson cross file, a compiler wrapper, a rename header, a stand-in module, or a link-time refusal. Use one whenever you can. See [Building from source](building.md#pins-and-recipe-files).

A *patch* is the last resort. Carry one only when the fix must change the source itself, for example a C callback defined with fewer parameters than CPython passes, which traps on WebAssembly.

## Write the patch

A patch lives under [`recipes/patches/`](https://github.com/ClayGendron/wasi-python/tree/main/recipes/patches), in a folder named after the pinned tarball's top folder:

```
recipes/patches/numpy-2.5.2/0001-npy-files-without-dup.patch
recipes/patches/numpy-2.5.2/0002-callback-signatures.patch
```

- The folder name is the name the tree has under `build/`, such as `numpy-2.5.2`.
- `NNNN` is four digits, unique in the folder. It sets the order the patches apply in.
- The file is a unified diff in `git diff` form, with paths relative to the tree's top.
- The patch is made against exactly its pinned tarball. No hunk may apply at an offset.

A patch may not contain a link, a binary hunk, a mode change, a rename or copy, a path outside the tree, or any file but a plain one. It may not change an autotools input (`configure.ac`, `configure.in`, `Makefile.am`, `*.m4`); patch the generated file the build runs instead. The tests read each patch as git reads it and name any of these.

A patch to a project's file carries that project's licence, as the same change upstream would.

## How the build applies it

[`scripts/steps/apply_patches.sh`](https://github.com/ClayGendron/wasi-python/blob/main/scripts/steps/apply_patches.sh) applies a tree's patches right after its step unpacks the tarball. The tests run the same script on a fresh extraction, so the two never apply differently. A release fails on any difference from a pinned tarball other than exactly the recorded patches.

## Record it

A carried patch is recorded in four places:

1. **`MANIFEST`** records its hash. The build writes this; you do not edit it by hand.
2. **`CHANGELOG.md`** names it, under the unreleased section.
3. **A pull request draft** for the upstream project. It lives in the project's memory folder under the same name as the patch, and starts with six header lines:

    ```
    - **Project:** <name> (<repository URL>)
    - **Against:** <version> (the pinned tarball)
    - **Status:** drafted | sent <url> | merged <url> | released <version, as the pinned file name writes it>
    - **Title:** <the pull request's title>
    - **Files:** <every path the patch touches, comma-separated>
    - **Why we carry it:** <what fails without it, in this project>
    ```

    The body is the text for the upstream maintainers. Where a project forbids AI-written pull request descriptions, the body holds the facts for a person to write from instead.
4. **A review** of the change that needs it, like every other change. See [Review and landing](review-and-landing.md).

The project's maintainer sends the pull request upstream. Recording its status changes no `MANIFEST` line, because a draft is not a build input.

## Remove it

A patch is temporary. Its life runs: drafted with its pull request, reviewed, carried, sent, merged, released upstream. When an upstream release carries the fix, move the pin to that release and delete the patch. Name the removal in `CHANGELOG.md`.

## See also

- [Pinned releases and patches](../explanation/pinned-releases-and-patches.md) explains why patches are few and temporary.
- [Principles](principles.md)
