# Adding a package

This guide shows you the steps to add a package to the artifact set: pin its source, write its recipe, build it in, run its own tests in the release, and document it. It uses scipy as the example, because scipy needed most of what a compiled package can need.

Adding a package changes the build, so it is a larger change than most. Read [Building from source](building.md) first.

## 1. Pin the source

Every input is pinned by URL and SHA-256, and verified before use. Add the package's release source to `downloads/SHA256SUMS` and give it one `get <url> <name>` line in [`scripts/00_download.sh`](https://github.com/ClayGendron/wasi_python/blob/main/scripts/00_download.sh). Then fetch and verify:

```sh
scripts/00_download.sh
```

Each pin prints `fetched <name>` or `present <name>`, then a `<name>: OK` line for each verified file. A mismatch fails the step.

Build from the released source, never from a patched wheel. A pure-Python package that needs a carried patch comes from its pinned source release too.

## 2. Write the recipe

A compiled package gets a build step under [`scripts/steps/`](https://github.com/ClayGendron/wasi_python/tree/main/scripts/steps) and the recipe files it needs under [`recipes/`](https://github.com/ClayGendron/wasi_python/tree/main/recipes). For scipy, that meant:

- a meson cross file that describes the WASI target (`recipes/wasi-scipy.cross`);
- rename headers for symbols that only collide in a static link;
- shims that bridge scipy's LAPACK declarations to the C LAPACK it links against.

No Fortran compiler is involved. scipy's LAPACK is OpenBLAS's own C translation, built in an earlier step.

The compiler wrapper `scripts/wasi-cc` turns every extension module's shared link into a static archive, so the package's own `meson.build` does not change. Prefer a recipe file to a source change every time. When a source change cannot be avoided, carry a patch; see [Carrying a patch](carrying-a-patch.md).

## 3. Build it in

The link step links every compiled module into one interpreter as a builtin module. scipy adds 95 compiled modules this way. Its Python package goes into the stdlib zip. Build the steps you changed and the ones after them:

```sh
scripts/build.sh --from 57
```

Each step prints `ok <step>: <what it made> [<time>]`, or `FAILED <step>` and an `ERROR` line with the reason.

Then check what differs from native. Write each difference down for users on the limitations page, with one sentence of reason. For scipy, `scipy.odr` is not in the build (it needs ODRPACK, which is Fortran), and `workers=` other than 1 does not start threads or processes.

## 4. Run its own tests in the release

Every package runs its own test suite in the release. Add the package to `tests/upstream/packages.toml` with its kind:

- `suite`: its test groups are in `tests/upstream/<name>.toml` and in a shard of `tests/release_shards.toml`.
- `via`: its own suite cannot run here, and the entry names what reaches it instead.
- `build-only`: it only compiles another package, with a reason.
- `later`: its suite does not run yet, with a reason and the planned work that runs it.

For example, a header-only build dependency looks like this:

```toml
[package.pybind11]
kind = "build-only"
reason = "headers that compile kiwisolver and matplotlib; nothing of its own runs in the guest"
```

The tests check that every package names its own suite or says why not.

## 5. Document it

Add the package and its version to [Packages](../reference/packages.md). Add each behaviour that differs from native to the [limitations page](../reference/limitations.md). Name the change in `CHANGELOG.md`.
