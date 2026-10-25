# Building from source

This guide shows you how to build the artifact set (`python.wasm`, `python-snapshot.wasm`, `python-stdlib.zip`, `MANIFEST` and `SHA256SUMS`) from pinned sources on your own machine.

The build runs on arm64 macOS, arm64 Linux and x86_64 Linux. All three give the same artifacts, byte for byte.

## Before you begin

- A checkout of the repository.
- The host tools the build checks for on `PATH`: `cc`, `make`, `shasum`, `tar`, `gzip`, `xz`, `sed`, `uv`, `git`, `stty` and `df`.
- At least 2.5 GiB free under `build/` for a first build.

You do not need a Python of your own. The build fetches a pinned host Python and uses only that one.

## Build the artifacts

Run two commands from the repository root:

```sh
scripts/00_download.sh   # fetch every pin and verify it against downloads/SHA256SUMS
scripts/build.sh         # a preflight, twenty steps with one line each, a summary; logs in build/logs/
```

The first command fetches every pinned input into `downloads/` over HTTPS and checks each one against its SHA-256 in `downloads/SHA256SUMS`. A mismatch fails the build and names the file; a file that is already present is never fetched again, so delete it and run the command again. Nothing it downloads is run as a program on your system; downloads are build tools or source trees only.

The second command builds everything. The artifacts land in `build/artifacts/`.

## Read the output

`scripts/build.sh` starts with a preflight. The preflight checks the build host, the host tools and the free space. It prints one line:

```
preflight: <host>; 11 tools; <n> GiB free
```

If something is missing, it prints one `ERROR preflight:` line and stops.

Each step then prints one line, `ok <step>: <what it made> [<time>]`. A failing step prints `FAILED <step>`, the last 20 lines of its log, and one closing line:

```
ERROR <step>: <reason> (log: …)
```

The reason is the last line of the step's log that starts with `ERROR`. So `grep '^ERROR'` gives you exactly the reason. A passing build ends with `done:`, the three artifacts with their sizes and the start of their hashes, and the next command to run. Each step writes its full log under `build/logs/`.

On a terminal, a status line sits below those lines and redraws in place. It shows the step, its place in the run, its time against the last run, and the time left. A pipe, `CI`, `TERM=dumb` or `--plain` gives the plain lines only. `NO_COLOR` turns colour off.

## Run part of the build

Every step removes and remakes its own outputs. Nothing is skipped on its own. To run part of the build, name the steps:

```sh
scripts/build.sh --list        # each step, what it does, and its last time
scripts/build.sh --from 60     # that step and every later one
scripts/build.sh --resume      # the step the last run did not finish, and every later one
scripts/build.sh 60 70         # only the named steps
scripts/build.sh --check       # the preflight alone
```

Ctrl-C stops the running step at once and exits with code 130. A `kill -TERM` or `HUP` sent to `build.sh` alone waits for the running step to end, because a shell handles a signal only once its foreground command returns. To stop at once, signal the process group (`kill -TERM -<pgid>`), as Ctrl-C does.

## What the steps do

The steps live in [`scripts/steps/`](https://github.com/ClayGendron/wasi-python/tree/main/scripts/steps). In order, they:

1. Unpack the toolchain and the pinned host Python, and install the build tools from hashed wheels, offline.
2. Build CPython with its own `Platforms/WASI` driver.
3. Build zlib and the C libraries behind `bz2`, `lzma` and `sqlite3`.
4. Build libxml2 and libxslt, the plotting libraries, and OpenBLAS's C LAPACK.
5. Cross-compile numpy, pandas, regex, lxml, matplotlib, scipy, scikit-learn and statsmodels.
6. Link everything into one interpreter as builtin modules, and relink it as a WASI reactor.
7. Build the bytecode-only, deterministic stdlib zip.
8. Snapshot the reactor with the pinned wasmtime's own `wasmtime wizer`. The snapshot pre-imports the stdlib's bootstrap modules and no package.
9. Assemble `build/artifacts/` with `MANIFEST`, `SHA256SUMS` and the licence notices of everything inside.

The versions that define a release line (CPython, wasi-sdk and the host Python) are named once, in [`scripts/line.conf`](https://github.com/ClayGendron/wasi-python/blob/main/scripts/line.conf).

## Only the pinned Python runs

Every Python a build step runs is the pinned host Python, or one built from pins. The build puts the pinned interpreter first on `PATH` under the names `python`, `python3` and `python3.15`. Behind it, every other Python on your `PATH` is linked to a shim that refuses to run. A step that calls an unpinned Python fails, even if it swallowed the refusal, and `build/logs/unpinned-python.log` names the call.

## The same bytes from any build host

Each supported build host compiles with its own pinned wasi-sdk clang, yet all of them produce the same artifact set. Four things make the bytes host-neutral:

- Each host's wasi-sdk keeps only its compiler. Every host links wasi-sdk's host-neutral sysroot and builtins.
- The build sorts in the C locale.
- The snapshot sees a directory's size and link count as constants.
- The stdlib zip's `_sysconfigdata` and numpy's `__config__.py` say nothing about the build machine. Inside the guest, the build machine is named `build`.

Every compile also carries `-ffp-contract=off`, written into the toolchain's own configuration files rather than on a command line. Without it, two builds of the same clang ordered one floating-point expression's stack slots differently, and the x86_64 binary differed by 21 bytes. WebAssembly has no fused multiply-add, so the flag does not change run-time arithmetic. Do not add the flag, or any option that overrides it, to a command line.

One host input is not pinned: the native C compiler and `make` that CPython's driver uses to build its own build-Python. Nothing it compiles is linked into the guest.

## Pins and recipe files

Every input is pinned by URL and SHA-256 in `downloads/SHA256SUMS`, and verified before use. `MANIFEST` names every supported build host's pins, not only the ones your build used, so it is the same file from every host.

A *recipe file* is an adaptation the project writes instead of changing upstream source. The files under [`recipes/`](https://github.com/ClayGendron/wasi-python/tree/main/recipes) include:

- meson cross files that describe the WASI target to each package's build;
- rename headers for symbols that only collide in a static link;
- the reactor's entry point and the host door module;
- stand-in modules, such as a `ctypes` package that names and sizes wasm32's C types and refuses every foreign call;
- link-time refusals, which answer a call the platform cannot make with a clear error.

The compiler wrapper [`scripts/wasi-cc`](https://github.com/ClayGendron/wasi-python/blob/main/scripts/wasi-cc) turns every extension module's shared link into a static archive, so no package's `meson.build` changes. When a recipe file is not enough, the project carries a small, recorded source patch; see [Pinned releases and patches](../explanation/pinned-releases-and-patches.md).

## Building on a Mac with Finder open

Finder and the storage scan in System Settings write `.DS_Store` files into folders they size. Nothing they write into `build/` changes an artifact: the zip, the licences and the set's file list skip such names. To stop the writers, close the Storage pane in System Settings and any Finder window on the checkout. Before you build a wheel by hand from `build/artifacts`, delete any such file there:

```sh
find build/artifacts -name .DS_Store -delete
```

## Building the wheel by hand

The release workflow builds the wheel. To build one from your own set, copy the set in, write the wheel's licence, build, then put `LICENSE` back:

```sh
cp -R build/artifacts src/wasi_python/artifacts
uv run --no-project python -I release/licences.py append build/artifacts
uv build --wheel
uv run --no-project python -I release/licences.py restore
```

The wheel's `LICENSE` is the project's licence followed by every licence in the set, as a release's is. The tests compare it with the set whenever a wheel is in `dist/`.

## Next steps

- Make your first change and run the tests: [Your first change](first-change.md).
- Add a package to the set: [Adding a package](adding-a-package.md).
- See how a release is cut: [The release process](release-process.md).
