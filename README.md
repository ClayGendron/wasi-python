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
| `python.wasm` | a WASI reactor: CPython plus numpy, pandas, zlib, bz2, lzma, sqlite3, the `host` door; `_initialize`, then one `run` per instance |
| `python-snapshot.wasm` | the same binary after a Wizer snapshot with numpy and pandas pre-imported; one `run` per instance, about 20 ms |
| `python-stdlib.zip` | the stdlib plus numpy, pandas, python-dateutil, tzdata, six as a deflated zip |
| `MANIFEST`, `SHA256SUMS` | every pinned source, every supported build host's toolchain, and every recipe hash |

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
| upstream patches to CPython, numpy, pandas, zlib, bzip2, xz, SQLite | **zero**; every adaptation is a recipe file |
| build from pinned sources, downloads present | 5 min 41 s (macOS arm64, 10 cores) |
| `python.wasm` / `python-snapshot.wasm` / `python-stdlib.zip` | 31.8 MB / 65.5 MB / 11.1 MB (3.15 line) |
| `import numpy` | `origin == 'built-in'`, no `.so` opened |
| one call, snapshot, `-c pass` | 20 ms, of which about 14 ms is finalizing the interpreter; 81.9M guest instructions on 3.15 |
| one call, snapshot, skipping finalization (`os._exit(0)`; flush first) | 6 ms |
| one call, plain reactor, `-c pass` / `import pandas` | 33 ms / 720 ms |
| numpy kernels vs native (the spike's measurement) | 1.6 to 2.3 times slower (no SIMD, no BLAS, no threads) |
| pandas groupby, 1e6 rows, vs native (the spike's) | 1.3 to 1.4 times slower |
| numpy, pandas, bz2, lzma and sqlite3 results vs native, same pins | byte-identical on five golden jobs |

The platform's facts, documented rather than patched, are what `python.wasm
-V` prints after its version:

> (wasm32-wasip1: numpy's default integer is 32-bit; no threads; no ctypes, mmap, sockets, ssl or zstd; compute about 1.3 to 2.3 times slower than native)

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
- it is the same bytes on every build, from any supported build host: while
  it initializes, the clocks, entropy and file metadata (a directory's size
  and link count included) answer constants, and no program ever sees them.

### sqlite3 in the guest

`sqlite3`, `bz2` and `lzma` are built in. `bz2`, `lzma` and `tarfile`'s
`bz2` and `xz` modes write the same bytes as native Python. `sqlite3` has
native's feature set (FTS3/4/5, R-tree, Geopoly, math functions, dbstat,
percentile) and gives native's results, except two kinds. SQLite's math
functions follow the guest's C library, so their last digits can differ:
over 199 inputs each, the trigonometric and hyperbolic functions, `atan2`,
`log10` and one-argument `log` did, and `exp`, `ln` and `sqrt` did not.
And what changed between SQLite releases (native's is 3.53.1) shows, such
as JSON's float text. WASI has no file locks, so SQLite uses its own WASI default,
and these facts follow from it:

- one connection holds the database, through a `<db>.lock` directory beside
  it, while it writes or has a statement open (an unfinished `SELECT`
  included); a second connection, even in the same program, then gets
  "database is locked" after its busy timeout (5 s by default);
- `journal_mode=wal` silently stays `delete`, unless the connection first
  sets `locking_mode=exclusive`;
- a guest stopped inside a transaction (killed, out of fuel, past its
  deadline, or by a hard exit such as `os._exit`) leaves `<db>.lock` and a hot journal; in a
  reused root the embedder removes the lock directory, and SQLite then rolls
  the journal back; a call without `root` never sees a stale lock, since its
  root is fresh;
- SQLite's own randomness (`random()`, `randomblob()`, its temporary file
  names) is seeded from the time in whole seconds, because the guest has no
  `/dev/urandom` (the process id is always 1 on WASI): two calls in the same
  second repeat it, and a `/dev/urandom` planted in a reused root sets it;
  use `secrets`, `uuid.uuid4()` or `os.urandom` for IDs, which use real
  entropy;
- a database in a read-only directory opens only through a URI that takes
  no lock (`uri=True`), such as `file:<path>?immutable=1` or
  `file:<path>?nolock=1`, because the lock is a directory made beside it;
  `mode=ro` alone is not enough;
- no `load_extension`; `sqlite3.threadsafety` is 0 (native: 3);
- `sysconfig` reports `_bz2` and `_lzma` as missing, `_sqlite3` as
  disabled and `PY_SQLITE_HAVE_SERIALIZE` as 0, because they are linked in
  through `Setup.local`, which CPython's `configure` never sees; all three
  import, and `Connection.serialize` works;
- `shelve` and `dbm` now create `dbm.sqlite3` files, as native does, so a
  shelf holds the lock directory too.

Temporary data goes to files under `TMPDIR` (`/tmp` by default in `run`).

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
scripts/build.sh         # eleven steps, one line each; logs in build/logs/
```

The steps (`scripts/steps/`): unpack the toolchain and a pinned host Python
(CPython 3.15.0 from python-build-standalone) and install the build tools from
hashed wheels, offline; build CPython with its own `Platforms/WASI` driver;
build zlib, numpy and pandas outside their source trees, cross-compiling with
meson, and the C libraries behind `bz2`, `lzma` and `sqlite3` (bzip2, liblzma
from xz with xz's own `configure`, and SQLite's one-file amalgamation); link everything into one interpreter as builtin modules and relink it
as a WASI reactor; build the bytecode-only, deterministic stdlib zip; snapshot
the reactor with the pinned wasmtime's own `wasmtime wizer`, numpy and pandas
pre-imported; assemble
`build/artifacts/` with `MANIFEST`, `SHA256SUMS` and the licence notices of
everything inside. The compiler wrapper `scripts/wasi-cc` turns every
extension module's shared link into a static archive, so no `meson.build`
changes. The line's versions (CPython, wasi-sdk, the host Python) are named
once, in `scripts/line.conf`.

**The same bytes from any build host.** The build runs on arm64 macOS and
arm64 Linux, and both give the same artifact set, byte for byte: the same
`SHA256SUMS` over the three artifacts, `MANIFEST` and the licences
(`context/specifications/012-the-same-bytes-from-any-host.md`). x86_64 Linux
is a pinned build host too, but its rebuilds are not yet byte-identical: its
wasi-sdk compiler lays out one numpy function's stack differently, so its
`python.wasm` differs by 21 bytes and its snapshot with it; its zip, `MANIFEST`
and licences are the same
(`context/research/2026-10-17-x86-64-rebuilds-differ-in-one-function.md`). Each host's
own inputs (wasi-sdk, wasmtime, the host Python, the Cython and ninja wheels)
are named once per host in `scripts/line.conf` and fetched by that host's
branch of `scripts/00_download.sh`; every host's pins are in
`downloads/SHA256SUMS`. So `MANIFEST`'s `pin` lines name every supported build
host's inputs, not only the ones one build used (its line
`x-pins every-supported-build-host` says so), and `MANIFEST` is the same file
from every host. Four things make the bytes host-neutral: the host's wasi-sdk
keeps only its compiler, and every host links wasi-sdk's host-neutral sysroot
and builtins; the build sorts in the C locale; the snapshot sees a directory's
size and link count as constants; and the stdlib zip's `_sysconfigdata` and
numpy's `__config__.py` say nothing about the build machine. Inside the guest,
`sysconfig.get_config_var('BUILD_GNU_TYPE')` and `numpy.show_config()`'s build
machine therefore say `build`, not the host that built it. No compiler runs in
a WASI guest, so nothing reads them.

The recipe files under `recipes/`: two meson cross files, three rename headers
for symbols that only collide in a static link, the reactor entry, the door
module, a host-side numpy stand-in for pandas' build, and one-function stand-ins for `ctypes` and `mmap` that pandas
imports unconditionally.

One host input is not pinned: the native C compiler and `make` that CPython's
driver uses to build its own build-Python. Nothing it compiles is linked into
the guest, and Apple clang and gcc 14.2 give the same artifact bytes
(`context/research/2026-10-16-reproducible-builds-on-linux.md`). The build
also runs host tools that move or check bytes and are not pinned either:
`curl`, `shasum` (perl's), `tar`, `xz`, `sed`, `uv` (it installs the pinned
wheels, offline, by hash) and `git` (it lists the recipes for `MANIFEST`). The
release workflow prints each runner's versions of them. xz's own `configure`,
which configures liblzma, also runs the host's shell tools (`sh`, `sed`,
`grep`, `awk`); the same-bytes gate is what shows they leave the artifacts
alone.

**Building on a Mac with Finder open.** Finder writes `.DS_Store` files into
folders you browse, at any moment. Every shell step removes its old outputs
through `remove` (`scripts/steps/remove.sh`), and step 90 through its own
`_remove`; both retry. The zip, the licences
and the artifact set never pack such a file (spec 018). One case is left: a
`.DS_Store` written into the finished `build/artifacts/` makes the judge's
`SHA256SUMS` check fail, naming the file, because a wheel built from that
folder would carry it. Delete it with `find build/artifacts -name .DS_Store -delete`.

## Releasing

Releases are alpha builds for now, numbered `0.1.0aN`. The version lives in one place,
`src/wasi_python/__init__.py`, and `release/version.py` changes it:

```
uv run python release/version.py bump            # 0.1.0a1 -> 0.1.0a2, and a CHANGELOG.md section
uv run python release/version.py release --push  # date the section, tag v0.1.0a2, push: the release runs
```

Pushing the tag starts `.github/workflows/release.yml`. It builds from the pins on arm64 macOS,
runs the zero-patch check and the whole judge, and checks the same bytes on Linux, Windows and
macOS. Beside the build, a `rebuild` job rebuilds the set from the pins on an arm64 Linux runner,
and `same-bytes` requires its `SHA256SUMS` to equal the set's, byte for byte; nothing is signed
or published until it passes. x86_64 Linux is not in this gate yet (above). Then it publishes
a GitHub pre-release with the wheel, the artifact set as `.tar.xz`, and
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
  --signer-workflow ClayGendron/wasi_python/.github/workflows/release.yml@refs/tags/v<version> \
  --source-ref refs/tags/v<version> --deny-self-hosted-runners
```

`--signer-workflow` matches a prefix of the signer's identity, so it carries the `@` and the
tag, which pins the workflow file exactly. `gh` must be logged in for this. Without `gh`, check
the asset against the release's `SHA256SUMS`.

## Running it

From Python, one call (`pip install "wasi-python[run]"`, which brings
wasmtime-py):

```python
from wasi_python import run

done = run(["-c", "import pandas as pd; print(pd.Series([1, 2, 3]).sum())"])
done.exit_code, done.stdout        # (0, b'6\n')
```

With no `root`, the call gets a fresh private directory as its whole
filesystem, removed afterwards. `root=` gives the guest a host directory
instead, writable, at `/`; `root=False` gives it no `/` at all. `grants=`
hands it more host folders, each read-only unless it says otherwise (see
*Grants*). The stdlib zip is never in a root: every call sees it read-only
at `/usr/local/lib`. `run` also takes `env`, `stdin`, `host` (a function from
request bytes to response bytes, bound to the door), `snapshot` (the
default; `False` runs the plain reactor), `fuel` (a cap on executed
instructions), `deadline_s`, `memory_bytes`, `output_bytes`, `cache_dir`,
`artifacts` and `cancel` (a `threading.Event`: once it is set, the guest
stops, `trapped` is `"cancelled"`; see *From async code* for how soon). It
returns `exit_code`, `stdout`, `stderr`, `trapped` (`"out of fuel"`,
`"deadline"`, `"cancelled"`, a trap's kind such as `"stack overflow"`,
`"unreachable"` or `"memory out of bounds"`, or, for an error with no trap
code, its first line), `fuel_used` and
`truncated` (the streams whose output hit the cap). `fuel_used` counts the
guest's own instructions from the end of instantiation, so it is the same
whether the module was compiled or loaded from the `.cwasm` cache (measured
on macOS; Linux maps the memory image itself and never charged for it, and
Windows, which always copies it, is expected to match)
(`context/research/2026-10-17-fuel-depends-on-how-the-module-was-made.md`).

The compiled module is cached as a `.cwasm` in the user cache directory, or
in `$WASI_PYTHON_CACHE`, only where no other user can write (a `.cwasm` is
native code); `cache_dir=False` keeps it in memory only. On Windows the
runner cannot check who may write a folder, so `cache_dir` and
`$WASI_PYTHON_CACHE` must name a folder only you can write; the default, in
your own profile, is one. Measured on Apple
arm64 (spec 001's landing notes): the first call compiles for about 3 s, a
first call with the `.cwasm` on disk takes about 0.1 s, and later calls in
one process about 20 to 25 ms. The runner finds the artifact set through
`wasi_python.artifacts()`: `$WASI_PYTHON_ARTIFACTS`, else a source
checkout's `build/artifacts/`, else the wheel's own copy.

### Grants

```python
from pathlib import Path

from wasi_python import Grant, run

data = Path.home() / "project" / "data"
done = run(
    ["-c", "import os; open('/out/n.txt', 'w').write(str(len(os.listdir('/data'))))"],
    root=False,
    grants=[Grant(data, "/data"), Grant("/tmp/job-17", "/out", writable=True)],
)
```

`Grant(host, guest, *, writable=False)` gives the guest the host folder `host`
at the guest path `guest`, read-only unless `writable=True`. A read-only grant
refuses every write-type call with `EPERM` (`PermissionError` in Python). Grants
may be nested (`/data` read-only with `/data/out` writable), in any order: the
guest's C library picks the longest matching guest path. `HOME` is made fresh
in the folder the guest sees at `/tmp`: a writable grant there, else the root's
own `tmp`; with neither, there is no `HOME`. With `root=False` there is no `/`,
and a relative path fails.

Every grant, and `root`, is checked before the guest is set up, and refused
with `TypeError` or `ValueError` (the runner may first make its own module
cache, so that it is judged as it will be):

- a guest path must be absolute, with no empty, `.` or `..` part and no
  trailing `/`; not `/` (that is `root`), not `/usr/local/lib` or under it
  (the runtime's), and no two grants may share one;
- a host path is walked one folder at a time and never through a link in a
  folder you can write, which a guest could have made (on Windows, never
  through any link, junction or other reparse point, which includes
  OneDrive's cloud folders and some container layers); a folder you may
  search but not list is walked through, as wasmtime opens it; a grant's
  folder must exist, and a missing `root` is made. Run as the superuser,
  every folder counts as writable, so every link on the way is refused
  (macOS's `/tmp` and `/var` included): name the real path;
- a read-only grant inside a writable one, or `root`, is refused: the guest
  could change it through the other;
- a writable grant or `root` at, inside or above the runtime's own folders
  is refused, since later calls and processes trust them: the stdlib folder
  (or the temporary folder that holds it), the artifact set, the module
  cache, and the code of `wasi_python` and wasmtime-py themselves. So
  `root=Path.home()`, a project folder holding the `.venv` this process runs
  from or `build/artifacts`, and the temporary folder itself are refused;
- any grant, read-only too, at or above the temporary folder is refused: it
  holds every call's private folders and `stdin`;
- folders are compared by identity (device and inode), never by spelling.

After wasmtime opens each folder itself, the runner checks, before the guest
runs, that it opened the folder it checked; a folder swapped in between
raises `RuntimeError`. A folder removed between the check and wasmtime's own
open raises wasmtime's `WasmtimeError`.

What grants do not do:

- `..` never crosses from one grant into another, and a grant does not appear
  in a listing of its parent;
- a read-only grant can still change if the same host files are writable
  elsewhere, by another call or another program;
- a SQLite database in a read-only grant opens only through a URI that takes
  no lock (`file:/data/db.sqlite?immutable=1`);
- a folder reachable by two routes (a bind mount, a share mounted twice) is
  judged by the route you give. Each route is checked against the runtime's
  files and the other grants by identity, which a bind mount shares and a
  second mount of a network share may not.

### From async code

`run_async` takes `run`'s arguments except `cancel` (cancel its task
instead), plus `executor`, and runs the call on
a worker thread, so the event loop never waits for a guest. wasmtime
releases the GIL while wasm runs, so guests on different workers run in
parallel. An ASGI endpoint (FastAPI shown):

```python
import asyncio
from wasi_python import run_async

@app.post("/run")
async def run_code(code: str):
    async with asyncio.timeout(30):  # also bounds the time spent waiting for a worker
        done = await run_async(["-c", code])
    return {"exit_code": done.exit_code, "stdout": done.stdout.decode()}
```

- **Cancelling the task stops its guest.** The runner checks the cancel
  every 50 ms while the guest computes, and at once when it waits or calls
  the door; the check and the clean-up need the GIL, so other busy Python
  threads delay them (measured: up to 200 ms to stop and 460 ms to return
  with one other thread spinning). The worker is freed and the private
  root removed before `CancelledError` (or the timeout's `TimeoutError`)
  reaches the caller. A call still waiting for a worker never starts. A guest inside
  a door host is stopped only when the host returns: the runner cannot
  interrupt host code.
- **What cancels the task** is your code: a timeout, a task group,
  shutdown. Starlette does not cancel a plain endpoint's task when the
  client disconnects, so without a timeout that guest runs to its
  `deadline_s`.
- **How many run at once.** With no `executor`, calls share one pool per
  process of `DEFAULTS.async_workers` threads: the CPU count (with CPU
  affinity, from Python 3.13), at most 8. Further calls wait for a worker.
  At the defaults each running guest may hold 1 GiB of memory, up to
  32 MiB of output and a copy of its `stdin`, so 8 workers bound one
  process at about 8.3 GiB, plus the disk a guest writes and the file
  descriptors it opens. Four server worker processes have four pools: four
  times that. A container's CPU quota is not seen; set the size with
  `wasi_python.runner.DEFAULTS = dataclasses.replace(DEFAULTS,
  async_workers=n)`. The bound covers only `run_async` on its own pool, not
  `run` called from your threads, an `executor` you pass, or a
  framework's thread pool for synchronous endpoints.
- **A synchronous endpoint** that calls `run` also keeps the loop free (the
  framework runs it on a thread), but it cannot be cancelled.
- **`executor`** must run callables on threads of this process; a process
  or interpreter pool is refused.
- **Forking.** A process forked after it ran a guest refuses to run guests
  (`RuntimeError`): wasmtime does not support use across a fork. Warm the
  runner up after the fork (in gunicorn's `post_fork`, say), never before.
- **Exit.** At interpreter exit, `run_async`'s running guests are stopped
  together and its queued calls dropped, so exit waits about as long as
  one cancel, longer for a worker inside a door host or still compiling.
  On a Python without `threading._register_atexit` (CPython has had it
  since 3.9) the stop runs later, and exit can wait for queued calls.
- **A door host that must await** runs the coroutine on its own loop with
  `asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=...)`;
  without a timeout a closing loop blocks it forever.
- `run_async` is asyncio only. Under trio, call `run(cancel=event)` from a
  worker thread.

Any other embedder does the same three things:

1. **Preopen the artifact set's stdlib zip, read-only, in a folder of its
   own at `/usr/local/lib`** (the guest finds `/usr/local/lib/python315.zip`),
   plus whatever folders the embedder grants, possibly none, a folder at `/`
   included. The snapshot runs only beside the zip it was built against.
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

- the guest sees only its root: no host path, no `..` out, and the guest
  cannot follow a symbolic link out (refused on open). It can still
  *create* a relative link that points out, which matters to host code that
  reads its root afterwards (see "Not protected");
- no network, no processes, no shared libraries; two imports only, WASI
  preview1 and the one door;
- only the stdlib zip is on the import path, and `site` does not run, so
  modules, `.pth` files or a `pyvenv.cfg` planted in a root never run
  (`sys.flags.no_site` is 1; `exit`, `quit`, `help` and `license` exist
  as in native Python);
- every door frame is bounded by guest memory, and nothing a frame or a
  host function does makes `run` raise;
- the deadline holds while the guest waits: the runner answers
  `poll_oneoff` itself (`time.sleep`, `select`), in slices that stop at the
  deadline, as wasmtime answers it except as spec 010 states (a directory or
  an unopened descriptor is reported ready; a bad pointer answers `EFAULT`);
  more than 4,096 subscriptions answer `ENOMEM` (`select.poll()` on more than
  2,047 descriptors with its default mask);
- **defaults** (`wasi_python.runner.DEFAULTS`): 1 GiB of memory, a 60 s
  deadline, 16 MiB of output per stream (the rest dropped and named in
  `truncated`); pass `None` for no limit. A limit of the wrong type or out
  of range (a negative cap, `True`, a deadline of 0) raises `TypeError` or
  `ValueError` before any work, so no value can quietly remove a limit;
  integer limits take any integer type (numpy's included) from 0 to
  2**63 - 1, and a deadline is a positive real number of seconds, counted in
  ticks of 10 ms (any positive deadline is at least one tick). The
  guest's environment starts from `TMPDIR=/tmp`, `PYTHONTZPATH=`
  (`zoneinfo` on the zip's tzdata) and
  a `HOME` made fresh and empty for each call in the folder the guest sees at
  `/tmp` and removed after it (no `HOME` where there is none); `env=` is laid
  over them;
- **grants** are read-only unless they say otherwise, checked before any
  work, and checked again after wasmtime opens them (see *Grants*); the stdlib
  zip is a read-only grant on every call;
- **inputs**: `argv` is any iterable of `str`, `env` a mapping of `str` to
  `str`, `stdin` a bytes-like object. One the guest would see differently
  (a NUL, text that is not UTF-8, an `=` or nothing as an env key) raises
  `ValueError` before any work, and a wrong type `TypeError`; no message
  quotes a value;
- each call's store is closed when it ends, trapped or not, so its memory
  and open files are released at once; a process copies the 11 MB stdlib
  zip once, into a folder of its own that its exit removes;
- calls made through `run` share nothing with each other but the stdlib
  zip's folder, which each sees read-only: the host
  functions are defined once per engine and serve only the call whose store
  called them, and each call's output goes to its own buffer, never through
  wasmtime-py's shared callback tables; whatever a host function catches (a
  trap in the guest's allocator, a host's `SystemExit` or `CancelledError`,
  Ctrl-C) stops that call and is reported or raised by that call's `run`, on
  its own thread. While `run` holds the main thread under Python's default
  SIGINT handler, Ctrl-C ends the call at the guest's next wait or door
  call, or during a wait, or else at its deadline; an embedder's own
  handler is left alone.

To report a way around any of this, see [SECURITY.md](SECURITY.md).

**Not protected:** a killed process (mid-call, its private root and stdin
folder; at any time after its first call, its 11 MB stdlib zip folder; each
with its lock file, stay in the temporary folder until another
process using wasi_python on the same kernel, with the same temporary
folder, starts its first call; folders from releases before 0.1.0a3 have no
lock file and are never removed: delete `wasi-python-*` entries there by hand
when no wasi_python process runs; two machines that share one temporary
folder and report the same identity, such as cloned Windows images, are not
told apart; a temporary folder on a filesystem without file locks, where such
folders are never removed); disk use in any
root, the private one included (a guest
can write as fast as the disk takes it until its deadline, tens of GiB in
the default 60 s; point `tempfile.tempdir`, or `root`, at a size-limited
volume if that matters); links a guest leaves in a granted root that point
outside it (host code that reads or writes the root after a call must not
follow links: open with `O_NOFOLLOW`, or check `os.lstat` first);
the host's file
descriptors (a guest can hold thousands of open files, which the embedder's
process shares; wasmtime-py offers no lower limit; while one guest holds them
all, the embedder's own code and other calls' `run` can fail with `OSError`,
though that guest's own call ends cleanly); data planted in a
reused root (dateutil's zone files, `mimetypes`' tables, any user file, the
plain reactor's `sys.prefix` after a planted `pyvenv.cfg`); pdb's `./.pdbrc`
in the current directory, `/`, which pdb runs as code when a program starts
pdb, as native pdb does (a fresh root closes it); a script or module the caller names to run
from a reused root; concurrent calls on one root (a guest can hard-link or
change the files another call uses); a guest that waits
(`time.sleep`, `select`) in a call with `deadline_s=None`, which waits as
long as it asks (no instruction runs, so fuel does not stop it); Ctrl-C
for a guest that never waits or calls the door in a call with
`deadline_s=None` and no `cancel` (it runs on; with `cancel=`, the runner's
check ends it); Ctrl-C under an embedder's SIGINT handler
that raises, asyncio's on a second Ctrl-C included, while a guest runs on
the main thread: wasmtime-py, or under `cancel=` the runner's epoch
callback, can then abort the process, so call `run` on a worker thread
(`run_async`, `asyncio.to_thread`, a thread pool) there; other code in the
same process using wasmtime-py directly, whose exceptions can reach a
trapping `run` through wasmtime-py's shared exception slot; an `env=` that
overrides `HOME` or `PYTHONTZPATH` on a reused root (pdb then reads a
`.pdbrc`, and `zoneinfo` a zone file, that a guest may have planted there);
`stdin`, which is written to a host temporary file of its size; SQLite's own
randomness (`random()`, `randomblob()`, its temporary names), which is seeded
from the clock's whole second because the guest has no `/dev/urandom`, so two
calls in the same second repeat it and a `/dev/urandom` planted in a reused
root sets it (Python's `random`, `secrets`, `os.urandom` and `tempfile` names
use real entropy); a stale SQLite lock and hot journal left in a reused root
by a guest stopped inside a transaction (see *sqlite3 in the guest*); an `argv`
or `env` larger than the guest's memory, which exits 1 with empty stderr;
timing
(the clock is real and fine-grained); real entropy; the one-byte exit status.

## Scope

**In the first release:** CPython, numpy, pandas, zlib, python-dateutil,
tzdata, six, the host door, the snapshot. **Since then:** `sqlite3`, `bz2` and
`lzma` (SQLite 3.54.1, bzip2 1.0.8, liblzma from xz 5.8.4).

**Out, with the one fact that decides each:** matplotlib (its data folder
needs a decision on the guest's filesystem; then FreeType, HarfBuzz, qhull,
kiwisolver, contourpy, Pillow); scipy (Fortran: f2c as Pyodide does; months);
threads; BLAS and SIMD; `_ctypes`, `mmap`, sockets, `_ssl`; `_zstd`
(`compression.zstd`: libzstd needs its own research and licence approval);
SQLite's `load_extension` (WASI has no `dlopen`); pip inside the guest.

## Next

In order. Each item is a specification or a research memo under
`context/`; `uv run pytest` names what blocks the most checks (its `next:`
line). The runner, the door, the reactor, the build, the release workflow
and the 3.15 line have landed (specs 001, 003, 004 and 005). The direction
past these is in
`context/research/2026-10-16-a-principal-engineers-direction.md`.

1. x86_64 Linux rebuilds byte-identical
   (`context/research/2026-10-17-x86-64-rebuilds-differ-in-one-function.md`):
   its wasi-sdk compiler lays out one numpy function's stack differently;
   the cause is found, the fix is not.
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
