# wasi_python

**A statically linked CPython for WebAssembly hosts, with numpy and pandas
compiled in. No browser, no JavaScript. A few pinned releases, not every
version of everything.**

One `python.wasm` for `wasm32-wasip1` that runs on a WASI host with
WebAssembly exception handling (see *Hosts*), from your own Rust, Go or
Python program. The packages are linked in as builtin modules, so there is
no `dlopen`, no shared library and no package install step inside the
guest. The sandbox is WASI's capability model: the guest sees only the
directories and host functions you hand it.

- Site: <https://wasipython.dev>
- Status: **alpha.** `0.1.0a1` (CPython 3.14.8, wasi-sdk 24) is a GitHub
  pre-release; the next alpha moves to CPython 3.15.0 and wasi-sdk 33.
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

## Measured (arm64 macOS, wasmtime 49)

Times are from the first scripted build on the 3.14 line (spec 003's landing
notes, 2026-10-16); sizes and instruction counts are the 3.15 line's (spec 005's
landing notes, 2026-10-17). Times are benchmark facts on one machine, not
promises.

| fact | value |
|---|---|
| upstream patches to CPython, numpy, pandas, zlib | **zero**; every adaptation is a recipe file |
| build from pinned sources, downloads present | 4 min 19 s |
| `python.wasm` / `python-snapshot.wasm` / `python-stdlib.zip` | 29.8 MB / 63.5 MB / 11.1 MB (3.15 line) |
| `import numpy` | `origin == 'built-in'`, no `.so` opened |
| one call, snapshot, `-c pass` | 20 ms, of which about 14 ms is finalizing the interpreter; 81.9M guest instructions on 3.15 |
| one call, snapshot, skipping finalization (`os._exit(0)`; flush first) | 6 ms |
| one call, plain reactor, `-c pass` / `import pandas` | 33 ms / 720 ms |
| numpy kernels vs native (the spike's measurement) | 1.6 to 2.3 times slower (no SIMD, no BLAS, no threads) |
| pandas groupby, 1e6 rows, vs native (the spike's) | 1.3 to 1.4 times slower |
| numpy and pandas results vs native, same pins | byte-identical on three golden jobs |

The platform's facts, documented rather than patched, are what `python.wasm
-V` prints after its version:

> (wasm32-wasip1: numpy's default integer is 32-bit; no threads; no ctypes, mmap, sockets, ssl, sqlite3, bz2 or lzma; compute about 1.3 to 2.3 times slower than native)

So `np.arange(1_000_000).sum()` wraps (use `dtype=np.int64`). A C++
`throw` inside a package (numpy's FFT, for one) is caught as in native
code and reaches Python as an exception. A script's directory is not put on `sys.path`: the interpreter
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

## Hosts

The binaries use WebAssembly's exception-handling proposal in its standard
form (`exnref`, part of WebAssembly 3.0), so C++ exceptions work; a host
without it cannot load them. They also need multi-value and reference
types (WebAssembly 2.0). Only wasmtime 49 is run by this project; the rest
of the list is read from each runtime's release notes and source
(`context/research/2026-10-16-cpp-exceptions-and-wasi-hosts.md`):

- **runs by default:** wasmtime 47 or later (CLI, Rust, wasmtime-py; 37 to
  46 with `-W exceptions=y`); WasmEdge 0.16 or later (AOT 0.18 or later);
- **runs with a switch:** wasmer 6 or later on LLVM, V8 or Cranelift 7 or
  later (not Singlepass); wazero 1.12 or later with its experimental
  opt-in; Node 24.15 or later, or 25;
- **does not run:** WAMR, wasmi, wasmer-python, wasmer-go, wasmtime's
  Winch, and wasmtime built without its `gc` feature.

For a host without exception handling, use `0.1.0a1` (CPython 3.14.8,
wasi-sdk 24): the `v0.1.0a1` release's assets, or `wasi-python==0.1.0a1`
once that version is on PyPI. On it a C++ `throw` ends the guest, and
matplotlib will never be built for it. C++ cannot be done on WASI without
the proposal under this project's rules (the memo above), so a 3.15 set
without it is not built unless an embedder needs one.

## How it is built

One command, from pinned inputs, with no source tree patched:

```
scripts/00_download.sh   # fetch every pin and verify it against downloads/SHA256SUMS
scripts/build.sh         # ten steps, one line each; logs in build/logs/
```

The steps (`scripts/steps/`): unpack the toolchain and a pinned host Python
(CPython 3.15.0 from python-build-standalone) and install the build tools from
hashed wheels, offline; build CPython with its own `Platforms/WASI` driver;
build zlib, numpy and pandas outside their source trees, cross-compiling with
meson; link everything into one interpreter as builtin modules and relink it
as a WASI reactor; build the bytecode-only, deterministic stdlib zip; snapshot
the reactor with the pinned wasmtime's own `wasmtime wizer`, numpy and pandas
pre-imported; assemble
`build/artifacts/` with `MANIFEST`, `SHA256SUMS` and the licence notices of
everything inside. The compiler wrapper `scripts/wasi-cc` turns every
extension module's shared link into a static archive, so no `meson.build`
changes. The line's versions (CPython, wasi-sdk, the host Python) are named
once, in `scripts/line.conf`.

The recipe files under `recipes/`: two meson cross files, three rename headers
for symbols that only collide in a static link, the reactor entry, the door
module, a host-side numpy stand-in for pandas' build, and one-function stand-ins for `ctypes` and `mmap` that pandas
imports unconditionally.

One host input is not pinned: the native C compiler and `make` that CPython's
driver uses to build its own build-Python. Nothing it compiles is linked into
the guest; a rebuild on a second host will test that it does not matter. The
build also runs host tools that move or check bytes and are not pinned either:
`curl`, `shasum`, `tar`, `xz`, `sed`, `uv` (it installs the pinned wheels,
offline, by hash) and `git` (it lists the recipes for `MANIFEST`).

## Releasing

Releases are alpha builds for now, numbered `0.1.0aN`. The version lives in one place,
`src/wasi_python/__init__.py`, and `release/version.py` changes it:

```
uv run python release/version.py bump            # 0.1.0a1 -> 0.1.0a2, and a CHANGELOG.md section
uv run python release/version.py release --push  # date the section, tag v0.1.0a2, push: the release runs
```

Pushing the tag starts `.github/workflows/release.yml`. It builds from the pins on arm64 macOS,
runs the zero-patch check and the whole judge, and checks the same bytes on Linux, Windows and
macOS. Then it publishes a GitHub pre-release with the wheel, the artifact set as `.tar.xz`, and
their `SHA256SUMS`. PyPI upload is off until the trusted publisher is set up. A manual run of
the workflow is a dry run that never publishes (`context/specifications/004-alpha-releases.md`).

Before publishing, an `attest` job signs build provenance for every asset and verifies it
strictly (`context/specifications/009-release-security.md`). If it fails, nothing is published:
re-run the failed jobs of the same workflow run (its artifacts are kept 90 days); never push the
tag again. Dry runs never sign, since a signature is permanent in Sigstore's public log.

## Verifying a download

From the first release after `0.1.0a1` (which has no attestation), every release asset carries
build provenance signed by this repository's release workflow at the release's tag:

```
gh attestation verify <asset> --repo ClayGendron/wasi_python \
  --signer-workflow ClayGendron/wasi_python/.github/workflows/release.yml \
  --source-ref refs/tags/v<version> --deny-self-hosted-runners
```

`gh` must be logged in for this. Without `gh`, check the asset against the release's
`SHA256SUMS`. A bundle fetched from GitHub's attestations REST API, which answers without a
token, verifies offline with `--bundle`.

## Running it

From Python, one call (`pip install "wasi-python[run]"`, which brings
wasmtime-py):

```python
from wasi_python import run

done = run(["-c", "import pandas as pd; print(pd.Series([1, 2, 3]).sum())"])
done.exit_code, done.stdout        # (0, b'6\n')
```

With no `root`, the call gets a fresh private directory as its whole
filesystem, removed afterwards. `root=` grants a host directory instead,
at `/`: the runner copies the stdlib zip into it before each call and
replaces anything the guest changed there, without following any link
the guest left. `run` also takes `env`, `stdin`, `host` (a function from
request bytes to response bytes, bound to the door), `snapshot` (the
default; `False` runs the plain reactor), `fuel` (a cap on executed
instructions), `deadline_s`, `memory_bytes`, `output_bytes`, `cache_dir`
and `artifacts`. It returns `exit_code`, `stdout`, `stderr`, `trapped`
(`"out of fuel"`, `"deadline"`, or a trap's first line), `fuel_used` and
`truncated` (the streams whose output hit the cap). `fuel_used` counts the
guest's own instructions from the end of instantiation, so it is the same
whether the module was compiled or loaded from the `.cwasm` cache (measured
on macOS; Linux maps the memory image itself and never charged for it, and
Windows, which always copies it, is expected to match)
(`context/research/2026-10-17-fuel-depends-on-how-the-module-was-made.md`).

The compiled module is cached as a `.cwasm` in the user cache directory, or
in `$WASI_PYTHON_CACHE`, only where no other user can write (a `.cwasm` is
native code); `cache_dir=False` keeps it in memory only. Measured on Apple
arm64 (spec 001's landing notes): the first call compiles for about 3 s, a
first call with the `.cwasm` on disk takes about 0.1 s, and later calls in
one process about 20 to 25 ms. The runner finds the artifact set through
`wasi_python.artifacts()`: `$WASI_PYTHON_ARTIFACTS`, else a source
checkout's `build/artifacts/`, else the wheel's own copy.

Any other embedder does the same three things:

1. **Preopen a directory at `/`** holding the artifact set's stdlib zip at
   `/usr/local/lib/python315.zip`. The snapshot runs only beside the zip it
   was built against.
2. **Bind the one custom import, `host::call(ptr, len, out_ptr_ptr,
   out_len_ptr) -> i32`.** Answer −1 when there is no host. Otherwise read
   the request from guest memory, get space from the exported `host_alloc`,
   write the response, store its pointer and length at the two
   out-addresses, and answer 0; answer −2 if the host fails. Frames are
   opaque bytes: their meaning is the embedder's.
3. **Call `_initialize`** (the plain reactor only) **and then `run`**,
   once per instance, with argv (`argv[0]` is `/usr/local/bin/python.wasm`)
   and the environment given through WASI. `run` returns the exit status.

The plain `wasmtime run` CLI cannot bind a custom import and refuses the
binary. With `-W unknown-imports-default` it runs it, but the door then
answers 0 with no response, which guest code reads as an empty answer.

## Safety

Made for running code nobody reviewed, such as a model's. The policy:
code planted in a root never runs at start-up or on import in a later call,
on either binary; data planted in a root a caller reuses is read by later
calls, and only a fresh root closes that; a call that names no limit still
has one.

**Enforced, and judged** (`tests/checks/test_v1_2_*.py`):

- the guest sees only its root: no host path, no `..` out, no symbolic
  link out (refused at creation or on open);
- no network, no processes, no shared libraries; two imports only, WASI
  preview1 and the one door;
- only the stdlib zip is on the import path, and `site` does not run, so
  modules, `.pth` files or a `pyvenv.cfg` planted in a root never run
  (`sys.flags.no_site` is 1; `exit`, `quit`, `help` and `license` exist
  as in native Python);
- every door frame is bounded by guest memory, and nothing a frame or a
  host function does makes `run` raise;
- **defaults** (`wasi_python.runner.DEFAULTS`): 1 GiB of memory, a 60 s
  deadline, 16 MiB of output per stream (the rest dropped and named in
  `truncated`); pass `None` for no limit. The guest's environment starts
  from `TMPDIR=/tmp`, `PYTHONTZPATH=` (`zoneinfo` on the zip's tzdata) and
  a `HOME` made fresh and empty for each call under `/tmp` and removed
  after it; `env=` is laid over them;
- each call's store is closed when it ends, trapped or not, so its memory
  and open files are released at once; a call without `root` copies the
  11 MB stdlib zip into its fresh root and removes the root afterwards.

**Not protected:** disk use in a granted root; the host's file
descriptors (a guest can hold thousands of open files, which the embedder's
process shares; wasmtime-py offers no lower limit); data planted in a
reused root (dateutil's zone files, `mimetypes`' tables, any user file, the
plain reactor's `sys.prefix` after a planted `pyvenv.cfg`); pdb's `./.pdbrc`
in the current directory, `/`, which pdb runs as code when a program starts
pdb, as native pdb does (a fresh root closes it); a script or module the caller names to run
from a reused root; concurrent calls on one root (a guest can hard-link or
change the files another call uses, the stdlib zip included); a program
damaging its own stdlib zip during its own run; a guest that waits
(`time.sleep`, `select` with a timeout) holds its call past the deadline
until the wait ends (spec 010 fixes this); timing (the clock is real
and fine-grained); real entropy; the one-byte exit status.

## Scope

**In the first release:** CPython, numpy, pandas, zlib, python-dateutil,
tzdata, six, the host door, the snapshot.

**Out, with the one fact that decides each:** matplotlib (its data folder
needs a decision on the guest's filesystem; then FreeType, HarfBuzz, qhull,
kiwisolver, contourpy, Pillow); scipy (Fortran: f2c as Pyodide does; months);
threads; BLAS and SIMD; `_ctypes`, `mmap`, sockets, `_ssl`, `_sqlite3`, bz2,
lzma; pip inside the guest.

## Next

In order. Each item is a specification or a research memo under
`context/`; `uv run pytest` names what blocks the most checks (its `next:`
line). The runner, the door, the reactor, the build, the release workflow
and the 3.15 line have landed (specs 001, 003, 004 and 005). The direction
past these is in
`context/research/2026-10-16-a-principal-engineers-direction.md`.

1. **Reproducible builds on Linux** (`context/research/2026-10-16-…`,
   placeholder): pin the Linux toolchain, build there, and compare hashes
   with the macOS build. The reactor, the snapshot and the zip already
   rebuild to the same bytes on one host.
2. numpy's and pandas' own test subsets under the runtime.

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
