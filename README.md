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
| `python.wasm` | a WASI reactor: CPython plus numpy, pandas, zlib, the `host` door; `_initialize`, then one `run` per instance |
| `python-snapshot.wasm` | the same binary after a Wizer snapshot with numpy and pandas pre-imported; one `run` per instance, about 20 ms |
| `python-stdlib.zip` | the stdlib plus numpy, pandas, python-dateutil, tzdata, six as a deflated zip |
| `MANIFEST`, `SHA256SUMS` | every pinned source, toolchain and recipe hash the build used |

Published as GitHub release assets (xz, 8 to 20 MB) and as the `wasi-python`
wheel on PyPI, which carries the same files and a `wasi_python.artifacts()`
function that returns their paths.

## Measured (2026-10-16, arm64 macOS, wasmtime 49)

From the first scripted build (spec 003; commands and outputs in its
landing notes). Times are benchmark facts on one machine, not promises.

| fact | value |
|---|---|
| upstream patches to CPython, numpy, pandas, zlib | **zero**; every adaptation is a recipe file |
| build from pinned sources, downloads present | 4 min 19 s |
| `python.wasm` / `python-snapshot.wasm` / `python-stdlib.zip` | 29.8 MB / 62.3 MB / 10.5 MB |
| `import numpy` | `origin == 'built-in'`, no `.so` opened |
| one call, snapshot, `-c pass` | 20 ms, of which about 14 ms is finalizing the interpreter |
| one call, snapshot, skipping finalization (`os._exit(0)`; flush first) | 6 ms |
| one call, plain reactor, `-c pass` / `import pandas` | 33 ms / 720 ms |
| numpy kernels vs native (the spike's measurement) | 1.6 to 2.3 times slower (no SIMD, no BLAS, no threads) |
| pandas groupby, 1e6 rows, vs native (the spike's) | 1.3 to 1.4 times slower |
| numpy and pandas results vs native, same pins | byte-identical on three golden jobs |

The platform's facts, documented rather than patched, are what `python.wasm
-V` prints after its version:

> (wasm32-wasip1: numpy's default integer is 32-bit; no threads; no ctypes, mmap, sockets, ssl, sqlite3, bz2 or lzma; compute about 1.3 to 2.3 times slower than native)

So `np.arange(1_000_000).sum()` wraps (use `dtype=np.int64`). On the
wasi-sdk 24 line a C++ `throw` aborts the guest (wasi-sdk 33 links real
exceptions). A script's directory is not put on `sys.path`: the interpreter
runs isolated. The snapshot runs only beside the exact stdlib zip it was built
against (its `MANIFEST` names the zip's hash), because zipimport's file
offsets are part of the snapshot.

`run` treats its arguments as CPython's command line does for one program:
`-c`, `-m`, a script, or `-` and no argument for stdin; `-u`; `-V`. Its return
value is the exit status, masked to 0 to 255 as a POSIX process's is. Output is
buffered as CPython's is without `-u`, so a program that ends in `os._exit` or
is stopped by fuel loses what it printed since its last flush; run it with
`-u`, or flush first. The snapshot adds three facts of its own:

- its string hash secret is fixed (`sys.flags.hash_randomization == 0`), so
  every snapshot instance hashes strings alike;
- the modules it pre-imports were imported with an empty environment: `run`
  re-reads what is known to matter (the `random` and numpy seeds, `logging`'s
  start time, `zoneinfo`'s `PYTHONTZPATH`), and anything else a module read
  from the environment at import keeps the build's value;
- it is the same bytes on every build: while it initializes, the clocks,
  entropy and file metadata answer constants, and no program ever sees them.

## How it is built

One command, from pinned inputs, with no source tree patched:

```
scripts/00_download.sh   # fetch every pin and verify it against downloads/SHA256SUMS
scripts/build.sh         # ten steps, one line each; logs in build/logs/
```

The steps (`scripts/steps/`): unpack the toolchain and a pinned host Python
(CPython 3.14.8 from python-build-standalone) and install the build tools from
hashed wheels, offline; build CPython with its own `Tools/wasm/wasi` driver;
build zlib, numpy and pandas outside their source trees, cross-compiling with
meson; link everything into one interpreter as builtin modules and relink it
as a WASI reactor; build the bytecode-only, deterministic stdlib zip; snapshot
the reactor with Wizer, numpy and pandas pre-imported; assemble
`build/artifacts/` with `MANIFEST`, `SHA256SUMS` and the licence notices of
everything inside. The compiler wrapper `scripts/wasi-cc` turns every
extension module's shared link into a static archive, so no `meson.build`
changes.

The recipe files under `recipes/`: two meson cross files, three rename headers
for symbols that only collide in a static link, the reactor entry, the door
module, a host-side numpy stand-in for pandas' build, a C++-exception stub for
the SDK-24 line, and one-function stand-ins for `ctypes` and `mmap` that pandas
imports unconditionally.

One host input is not pinned: the native C compiler and `make` that CPython's
driver uses to build its own build-Python. Nothing it compiles is linked into
the guest; a rebuild on a second host will test that it does not matter. The
build also runs host tools that move or check bytes and are not pinned either:
`curl`, `shasum`, `tar`, `xz`, `sed`, `uv` (it installs the pinned wheels,
offline, by hash) and `git` (it lists the recipes for `MANIFEST`).

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

1. **The runner** (`context/specifications/001-…`): `wasi_python.run`, which
   binds the door and runs either binary in one call. The door, the reactor
   and the build itself landed with spec 003; `uv run pytest` names what is
   left (its `next:` line).
2. **The CPython 3.15 + wasi-sdk 33 line** (`context/research/2026-10-16-…`,
   placeholder): re-run the recipe on the line that links C++ exceptions and
   pick the first release's pins on the result.
3. **Reproducible builds on Linux** (`context/research/2026-10-16-…`,
   placeholder): pin the Linux toolchain, build there, and compare hashes
   with the macOS build. The reactor, the snapshot and the zip already
   rebuild to the same bytes on one host.
4. The release workflow: `workflow_dispatch` on demand, the
   zero-patch gate, verification runs with counted operations, the assets
   and the wheel.
5. numpy's and pandas' own test subsets under the runtime.

Decided already, without further study: both binaries ship, the snapshot
first; the stdlib zip is bytecode-only and deflated; the int32 default
integer is documented, not patched.

## How this repo is organized

- `recipes/`, `scripts/`, `fixtures/`, `downloads/SHA256SUMS`: the build.
- `src/wasi_python/`: the wheel. `tests/`: its tests and the progress
  harness; `uv run pytest` prints the v1 scoreboard and guards it with a
  ratchet (`context/progress/README.md`).
- `context/`: the project's memory. `prior_art/` holds shallow clones we
  study and never copy (git-ignored, indexed in its README); `research/`
  holds dated memos, executed or marked placeholder; `specifications/`
  holds numbered work packages; `reviews/` holds the review of each built
  change before it lands. See `context/README.md`.
- `AGENTS.md`: the rules an agent follows here.

## Evidence

`context/research/2026-10-16-the-spike-that-proved-the-build.md` is the
executed spike this project grew from: every command, every number.
Its outputs, logs and generated link lines are in
`context/research/2026-10-16-the-spike-that-proved-the-build/`, and
`context/research/2026-10-16-the-spike-evidence-in-this-repository.md`
maps the spike's paths to this repository's. The spike ran inside
another repository, the first consumer of this runtime; nothing here
needs it.

## Why WASI and not "wasm"

WebAssembly is the machine: an instruction set and a file format. WASI is
the operating system interface the binary talks to: files, clock, args,
stdout. This binary needs a WASI host and nothing else. "Python in wasm"
usually means Pyodide, which needs a browser or Node through Emscripten's
JavaScript glue. This is the other thing.
