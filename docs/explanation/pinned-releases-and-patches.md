# Pinned releases and patches

This page explains why wasi-python ships a few pinned releases instead of every version of every package, and how it treats the rare changes it must make to upstream source.

## Every input is pinned

Every input to the build is *pinned*: named by its URL and its SHA-256 hash in `downloads/SHA256SUMS`. That covers each source tarball, the toolchain, every build tool and every pure-Python dependency. The build checks each hash before it uses the file, and a build that fetches anything unpinned is not a build.

Downloads are treated as untrusted. They unpack only under the build's own folders, never into the system, and they run only as build tools or as guests under wasmtime.

Pinning makes a release reproducible. Anyone can rebuild the artifact set from its pins and get the same bytes, and the release workflow checks that it does.

## A few releases, not every version

A release is one pinned set of versions: one CPython, one numpy, one pandas, and so on. The project does not build every release of every package. It builds a new set when there is a reason to, such as a security fix in a pinned component, and older sets stay published.

This keeps the product small enough to test whole. Every package in a set runs its own test suite inside the guest before the set is released. A matrix of every version against every other could not be tested that way.

It also keeps a release cheap. A new set means: re-pin, rebuild, re-test, publish. That should cost days, not weeks.

## Recipes first, patches last

Building packages for WASI needs adaptations. The first choice is always a *recipe file*: a file the build adds around an untouched source tree. Examples are a cross-compilation file, a compiler wrapper, a header that renames clashing symbols, or a small stand-in module. Recipe files live under `recipes/`.

When a change to upstream source cannot be avoided, the project carries it as a *patch file* under `recipes/patches/`. A carried patch is:

- **reviewed**, like any other change;
- **recorded**: its hash is in `MANIFEST`, and the changelog names it;
- **applied after the pinned tarball's hash is checked**, by one build step;
- **matched by an upstream pull request**, drafted in the repository for the project's maintainer to send, or already merged upstream (where an upstream project asks that a person write its reports, the draft is a sheet of facts to write from);
- **temporary**: it is deleted once an upstream release carries the fix and the pin moves past it.

The release fails on any difference between a source tree and its pinned tarball other than exactly the recorded patches. So a source tree is always its tarball plus a known list of changes, and nothing else.

Today the project carries 27 patches. Many are small fixes to C callback signatures, which native platforms forgive and WebAssembly does not; others let a package read its own data files from a zip. A few are fixes already merged upstream, carried until a release includes them. Every other adaptation is a recipe file. The patches are listed in [`recipes/patches/`](https://github.com/ClayGendron/wasi_python/tree/main/recipes/patches).

## Why patches stay few

A patch is a fork in miniature. Each one must be re-checked when its package moves, and each one is a place where the guest's package differs from the one its users know. Keeping patches few, public and temporary keeps the build close to upstream, makes a new pinned set cheap, and sends the fixes back to the projects that own the code.

To carry one yourself, see [Carrying a patch](../contributing/carrying-a-patch.md).

## In one line

Every input is pinned by URL and hash, a release is one tested set of versions, and a change to upstream source is a recorded, reviewed, temporary patch with its fix sent upstream.
