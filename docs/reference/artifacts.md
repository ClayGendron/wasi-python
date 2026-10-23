# Artifacts

This page describes the *artifact set*: the files that make up the runtime, what each holds, and where a release puts them. Read it if you embed the runtime in a host of your own, or want to know what the wheel carries.

## The set

| file | what it is |
|---|---|
| `python.wasm` | The plain *reactor*: CPython 3.15 plus every compiled package, linked into one `wasm32-wasip1` module as builtin modules. A reactor is a WebAssembly module that exports functions to call, rather than one `main` that runs once. You call `_initialize`, then `run` once per instance. |
| `python-snapshot.wasm` | The same binary after a *Wizer snapshot*: Wizer runs a module's start-up once at build time and saves the result as a new module. Here the interpreter is started and the stdlib's bootstrap modules are imported; no package is. You call `run` once per instance, with no `_initialize`. |
| `python-stdlib.zip` | The standard library and every package's Python half, as bytecode only, in a deflated zip. It also holds `host` (the tool protocol's guest package) and matplotlib's data as one inner archive, `matplotlib/mpl-data.zip`. |
| `MANIFEST` | Every pinned source, every supported build host's toolchain, and every recipe hash the build used. |
| `SHA256SUMS` | The SHA-256 of the three artifacts, `MANIFEST` and the licence notices. |

The licence notices of everything inside are in a `LICENSES/` folder beside them (for example, `LICENSES/cpython.txt`).

The compiled packages are part of the binaries. There is no `.so` file, no `dlopen`, and no install step inside the guest. `import numpy` finds a module whose origin is `built-in`.

## The snapshot and its zip

The snapshot pre-imports these stdlib modules, with an empty environment: `encodings`, `io`, `os`, `sys`, `json`, `csv`, `re` and `_colorize`. It pre-imports no package, so numpy, pandas and every other package import in your call, with your environment.

The snapshot runs only beside the exact stdlib zip it was built against, because zipimport's file offsets are part of the snapshot. `MANIFEST` names the zip's hash.

The snapshot is the same bytes on every build, from any supported build host. While it initializes, the clocks, entropy and file metadata answer constants, and no program ever sees them.

## `MANIFEST`

`MANIFEST` is a text file of lines. Among them:

- a `python` line naming the guest's CPython version, such as `python 3.15.0`;
- a `pin` line for each pinned input. It names every supported build host's inputs, not only the ones one build used, and the line `x-pins every-supported-build-host` says so. So `MANIFEST` is the same file from every host;
- a hash for each recipe file the build used;
- an `x-preimport` line that records what the snapshot pre-imports;
- the pinned test sources of the pure-Python packages.

## The same bytes from any build host

The set builds on arm64 macOS, arm64 Linux and x86_64 Linux. All three give the same artifact set, byte for byte: the same `SHA256SUMS` over the three artifacts, `MANIFEST` and the licences. Each release rebuilds the set on two Linux machines and requires their `SHA256SUMS` and wheel to equal the build's before anything is published.

## The wheel

The `wasi-python` wheel carries the same files, in an `artifacts` folder inside the `wasi_python` package. `wasi_python.artifacts()` returns their paths as an `Artifacts`:

| field | file |
|---|---|
| `snapshot` | `python-snapshot.wasm` |
| `plain` | `python.wasm` |
| `stdlib_zip` | `python-stdlib.zip` |
| `manifest` | `MANIFEST` |

`wasi_python.artifact_dir()` returns the folder. Both raise `ArtifactsMissing` when there is no set. Importing `wasi_python` never loads wasmtime; only `run` does. So an embedder that brings its own engine can install the wheel with `pip install --no-deps wasi-python` and use only `artifacts()`.

## Where the runner finds the set

`artifacts()` looks in this order:

1. the folder that `$WASI_PYTHON_ARTIFACTS` names;
2. when the package runs from a source checkout of wasi-python, that checkout's `build/artifacts/`;
3. the wheel's own copy.

A copy installed with `pip install --target`, or vendored, never takes a neighbouring `build/`.

`run` and `Session` check the set they find against its `SHA256SUMS` before they use it, and compile and grant only the bytes they checked. A set you pass as `artifacts=` is used as you give it. The check catches a file changed or half-written since the build, not a set rewritten whole with its `SHA256SUMS`. So keep the set where only you can write, and out of any writable grant.

## The compiled-module cache

The runner compiles `python.wasm` or the snapshot to native code once and keeps it as a `.cwasm` file, in the user cache folder or in `$WASI_PYTHON_CACHE` (an absolute path). It loads a `.cwasm` only from a folder at mode `0700` holding files at `0600`, as the runner makes them; anything made otherwise is compiled around and never loaded. `cache_dir=False` keeps the compiled module in memory only. The cache is not part of the public promise.

On Windows the runner can check only that the folder and its files are not links. So `cache_dir` and `$WASI_PYTHON_CACHE` must name a folder only you can write.

## Where a release puts them

Each release publishes, on GitHub:

- the wheel;
- the artifact set as a `.tar.xz` archive;
- a `SHA256SUMS` of those assets.

Every asset carries signed build provenance. The same wheel is uploaded to PyPI as `wasi-python`. See [Verify a download](../how-to/verify-a-download.md).

## Using the files without the runner

A host of your own preopens the stdlib zip read-only at `/usr/local/lib`, in a folder holding nothing else, so the guest finds `/usr/local/lib/python315.zip`. For matplotlib, it extracts the zip's member `matplotlib/mpl-data.zip` into a folder of its own and preopens that read-only at `/usr/local/lib/python315.zip/matplotlib/mpl-data`. See [Embed from other languages](../how-to/embed-from-other-languages.md) for the rest.

## In one line

Two binaries (plain and snapshot), one stdlib zip that must match the snapshot, and a `MANIFEST` and `SHA256SUMS` that pin and check them; the wheel carries the same files and `artifacts()` finds them.
