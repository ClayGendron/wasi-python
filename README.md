# wasi_python

**A statically linked CPython for WebAssembly hosts, with numpy and pandas
compiled in. No browser, no JavaScript. A few pinned releases, not every
version of everything.**

One `python.wasm` for `wasm32-wasip1` that runs anywhere a WASI host runs:
wasmtime, wasmer, wazero, or your own Rust, Go or Python program. The
packages are linked in as builtin modules, so there is no `dlopen`, no
shared library and no package install step inside the guest. The sandbox
is WASI's capability model: the guest sees only the directories and host
functions you hand it.

- Site: <https://wasipython.dev>
- Status: **pre-release.** The build is proven (see *Evidence*); the repo is
  being assembled from it. Nothing is published yet.
- Licence: Apache-2.0.

## What you get

| artifact | what it is |
|---|---|
| `python.wasm` | a WASI reactor: CPython plus numpy, pandas, zlib, the `host` door; `_initialize` once, `run` per call |
| `python-snapshot.wasm` | the same binary after a Wizer snapshot with numpy and pandas pre-imported; starts in 3 to 5 ms |
| `python-stdlib.zip` | the stdlib plus numpy, pandas, python-dateutil, tzdata, six as a deflated zip |
| `MANIFEST`, `SHA256SUMS` | every pinned source, toolchain and recipe hash the build used |

Published as GitHub release assets (xz, 8 to 20 MB) and as the `wasi-python`
wheel on PyPI, which carries the same files and a `wasi_python.artifacts()`
function that returns their paths.

## Measured (2026-10-16, arm64 macOS, wasmtime 49)

| fact | value |
|---|---|
| upstream patches to CPython, numpy, pandas | **zero**; twelve small recipe files |
| full build from pinned sources | about ten minutes |
| `import numpy` | `origin == 'built-in'`, no `.so` opened |
| cold start per call, snapshot | 3.0 ms (numpy), 4.8 ms (numpy + pandas) |
| cold start per call, plain reactor | 80 to 120 ms |
| numpy kernels vs native | 1.6 to 2.3 times slower (no SIMD, no BLAS, no threads) |
| pandas groupby, 1e6 rows, vs native | 1.3 to 1.4 times slower |
| memory after the pandas job | 108 MiB |

Two facts of the platform, documented rather than patched: numpy's default
integer is 32-bit on wasm32, so `np.arange(1_000_000).sum()` wraps (use
`dtype=np.int64`); and on the wasi-sdk 24 line a C++ `throw` aborts the
guest (wasi-sdk 33 links real exceptions).

## How it is built

Everything is a pinned source plus a recipe file. No source tree is patched.

1. `scripts/00_download.sh` fetches CPython, numpy, pandas, zlib, wasi-sdk,
   Wizer and the wasmtime CLI and verifies every hash in
   `downloads/SHA256SUMS`.
2. `scripts/02_build_cpython_floor.sh` builds CPython with its own
   `Tools/wasm/wasi` driver.
3. `scripts/09_build_zlib.sh` builds zlib as a static archive.
4. `scripts/03_numpy_build.sh` and `scripts/07_pandas_build.sh` cross-compile
   with meson. The compiler wrapper `scripts/wasi-cc` turns every extension
   module's shared link into a static archive, so the upstream `meson.build`
   files never change.
5. `scripts/gen_inittab.py` registers every module under its dotted name;
   `scripts/04b_link_python_pandas.sh` writes `Modules/Setup.local` and links
   one `python.wasm`.
6. `scripts/08_build_vfsmain.sh` relinks it as a WASI reactor; Wizer snapshots
   it with the stack pre-imported.
7. `scripts/make_stdlib_zip.py` builds the zip.

The recipe files under `recipes/`: two meson cross files, two rename headers
for symbols that only collide in a static link, the reactor entry, the door
module, the generated inittab, a C++-exception stub for the SDK-24 line, and
one-function stand-ins for `ctypes` and `mmap` that pandas imports
unconditionally.

## Running it

The binary declares one custom import, the **host door**: a single function
the embedder binds, through which guest code reaches the host (for vfs, the
filesystem verbs). A plain `wasmtime run` cannot define a custom import, so
the plain CLI only runs a door-less build. The `wasi_python` wheel will ship
a runner (`wasi_python.run`, over wasmtime-py) that binds the door to a
default and calls the reactor entry; see *Next*.

Layout the guest expects, so CPython's own prefix search finds the stdlib:

```
<root>/usr/local/bin/python.wasm     # argv0, the path only; the file need not exist there
<root>/usr/local/lib/python314.zip   # the stdlib zip, found by the landmark search
```

With a door-less build and the wasmtime CLI (verified with Brett Cannon's
3.14.7 build and this project's zip):

```
wasmtime run --dir <root>::/ --argv0 /usr/local/bin/python.wasm python.wasm \
    -I -X utf8 -c "import sys; print(sys.version)"
```

## Scope

**In the first release:** CPython, numpy, pandas, zlib, python-dateutil,
tzdata, six, the host door, the snapshot.

**Out, with the one fact that decides each:** matplotlib (C++ exceptions:
needs the wasi-sdk 33 line, then freetype, libpng, qhull, kiwisolver,
contourpy, Pillow; weeks); scipy (Fortran: f2c as Pyodide does; months);
threads; BLAS and SIMD; `_ctypes`, `mmap`, sockets, `_ssl`, `_sqlite3`, bz2,
lzma; pip inside the guest.

## Next

Before a first release, in order. Each item is a specification or a
research memo under `context/`:

1. **The neutral host door and the runner**
   (`context/specifications/001-…`): rename `vfs::ping` to `host::call`,
   `vfs_run` to `run`, and ship `wasi_python.run`, which binds the door and
   runs either binary in one call.
2. **The CPython 3.15 + wasi-sdk 33 line** (`context/research/2026-10-16-…`,
   placeholder): re-run the recipe on the line that links C++ exceptions and
   pick the first release's pins on the result.
3. **Reproducible builds on Linux** (`context/research/2026-10-16-…`,
   placeholder): make the build-Python wrapper host-neutral, build in CI,
   compare hashes with the macOS build.
4. The release workflow: `workflow_dispatch` on demand, the
   zero-patch gate, verification runs with counted operations, the assets
   and the wheel.
5. numpy's and pandas' own test subsets under the runtime.

Decided already, without further study: both binaries ship, the snapshot
first; the stdlib zip is bytecode-only and deflated; the int32 default
integer is documented, not patched.

## How this repo is organized

- `recipes/`, `scripts/`, `fixtures/`, `downloads/SHA256SUMS`: the build.
- `src/wasi_python/`, `tests/`: the wheel.
- `context/`: the project's memory. `prior_art/` holds shallow clones we
  study and never copy (git-ignored, indexed in its README); `research/`
  holds dated memos, executed or marked placeholder; `specifications/`
  holds numbered work packages; `reviews/` holds the review of each built
  change before it lands. See `context/README.md`.
- `AGENTS.md`: the rules an agent follows here.

## Evidence

`context/research/2026-10-16-the-spike-that-proved-the-build.md` is the
executed spike this project grew from: every command, every number, every
output file. It was run inside the
[vfs](https://github.com/claygendron/vfs) repository, whose shell runs this
runtime over a database-backed filesystem; the raw build logs and outputs
live there under `context/research/studies/2026-10-15-agent-shell/experiments/s12/`.

## Why WASI and not "wasm"

WebAssembly is the machine: an instruction set and a file format. WASI is
the operating system interface the binary talks to: files, clock, args,
stdout. This binary needs a WASI host and nothing else. "Python in wasm"
usually means Pyodide, which needs a browser or Node through Emscripten's
JavaScript glue. This is the other thing.
