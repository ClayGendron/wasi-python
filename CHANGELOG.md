# Changelog

One section per release of the `wasi-python` artifact set and wheel, newest first. A section's
body is the release's notes on GitHub. `release/version.py bump` adds a section; `release/version.py
release` dates it and tags the release (context/specifications/004-alpha-releases.md).

## 0.1.0a4 — unreleased

- **What numpy's and pandas' own tests found** (spec 051). Three defects, fixed:
  - **numpy callbacks no longer trap the guest** (the second carried patch,
    `recipes/patches/numpy-2.5.2/0002-callback-signatures.patch`). Six C functions were defined
    with fewer parameters than CPython calls them with; WebAssembly checks the type of every
    indirect call, so `copy.copy` of any numpy scalar and `a.dtype = …` ended the call in a wasm
    trap. Each gains the parameter, unused. Its upstream facts sheet is
    `context/upstream/13-numpy-callback-signatures/`, for the owner to send. The judge now scans
    `python.wasm`'s referenced method and getset tables, and Cython's and CPython's single method
    definitions, for any callback whose type is not the one CPython calls it with
    (`test_callbacks_have_the_types_cpython_calls`); a mismatch is fixed by a patch or an
    upstream release, never excused.
  - **pandas' warnings point at the caller's line.** The zip's code objects now carry the name
    zipimport gives a module in it, `/usr/local/lib/python315.zip/pandas/core/frame.py`, instead
    of `pandas/core/frame.py`, so pandas' `find_stack_level` finds its own frames. Tracebacks show
    the full zip path, as native zip imports do. The zip grows by the longer names.
  - **The first carried patch, amended**
    (`recipes/patches/numpy-2.5.2/0001-npy-files-without-dup.patch`): `np.save` of a masked
    array to a path raises `NotImplementedError` again, as natively, where the patch had written
    its data and dropped its mask. A truncated `.npy` file read from a path raises numpy's
    in-memory `ValueError` message on WASI, a documented difference; the patch's tests and its
    upstream draft say so.
- **Security: the sandbox holds on wasmtime 49.0.0** (spec 048). wasmtime-py 49.0.0, the only
  49 release, bundles wasmtime 49.0.0, which carries two advisories that reach a guest; the
  runner now carries both fixes itself, on every call. **GHSA-m9f7-9w4p-gv38** (high, fixed in
  wasmtime 49.0.3): on macOS and FreeBSD a guest with a writable grant or `root=True` could
  rename a symbolic link pointing out of its sandbox with a trailing slash, `os.rename("up/",
  "stolen")`, and the kernel moved the host folder it pointed at into the sandbox. A rename with
  a trailing `/` on either path now needs a source that is a folder, judged without following
  the source's own link (`ENOTDIR` otherwise, or the source's own error, such as `ENOENT`), and
  a folder is renamed by its plain name. **GHSA-96f6-r43r-8c24** (low, fixed in wasmtime
  49.0.2): `fd_readdir` on a grant, a root or the stdlib folder gave the guest up to three bytes
  of host memory per entry; the runner now zeroes them. A call without mounts now runs on a
  guard linker that serves `fd_readdir` and `path_rename` through the runner (forwarded to
  wasmtime, fuel-neutral; `Completed.files` stays `None`); every other call stays wasmtime's.
  Once a call has stopped, these two answer `EIO`, as every runner-served call does. Each guard
  is removed when the published `wasmtime` requirement admits only fixed versions.
- **Tools in the runner** (spec 036). `run` and `run_async` take `tools=` (decorated or plain
  functions), `gate=` and `max_tool_calls=` (`DEFAULTS.tool_calls`, 1,000), checked before any
  work; `host=` and `tools=` exclude each other. The door asks the frame host to admit each frame
  by its length before it copies it, so a frame over 1 MiB costs the host the same whatever its
  size. Each tool call runs on its own daemon thread, in a copy of the caller's context, and is
  answered at the tool's `timeout_s`, two ticks before the deadline, at `cancel` or at Ctrl-C;
  a tool left running is `abandoned`, and one run may hold 4 of them. `Completed.tools` records
  every frame, on every ending; `runner.stats()` gains `tool_threads_running`. An artifact set
  without the guest package is refused (`ArtifactsMissing`). The README's "Tools" gives the
  API, its limits and their reasons, and LangChain and MCP recipes. The artifact set does not
  change.
- **x86_64 Linux rebuilds the same bytes** (spec 040). The release workflow's `same-bytes` gate
  now rebuilds the set on an x86_64 Linux runner too, beside the arm64 one, and requires the same
  `SHA256SUMS` and wheel from each; nothing is signed or published otherwise. wasi-sdk's x86_64
  clang orders two stack slots of numpy's `npy_cpowl` differently in instruction selection, so the
  x86_64 host now compiles with the pinned arm64 Linux wasi-sdk's clang under a pinned
  `qemu-aarch64` (Debian's, from `snapshot.debian.org`, with four aarch64 runtime packages), through
  the new launcher `scripts/clang-emulated`; every other tool stays native. Step 10 lays it out
  under `build/tools/` and stops unless five probes hold. Nothing changes on the arm64 hosts: the
  three artifacts and the licences keep their bytes, and `MANIFEST` gains the five pins and the
  launcher. The LLVM issue is drafted for the owner (`context/upstream/4-llvm-wasm-isel-slot-order/`);
  the emulation goes when an SDK's two compilers agree.
- **A tool protocol over the door** (spec 031). Guest code can call the host's tools with
  `from host import tools`; the stdlib zip carries the guest's half, the pure-Python package
  `host` (`host/__init__.py`, `host/tools.py`), and the wheel the host's, `wasi_python.tools`
  (`tool()`, the frame host, `stubs()`), which `import wasi_python` does not load. The binary,
  its imports and its exports are unchanged: frames are JSON, protocol 1, through the one door.
  The README's "The tool protocol" gives the frames, the kinds, the request rules, the schema
  subset and the validation budget, for an embedder in any language. `run(tools=…)` comes with
  spec 036. Costs: the zip grows by 2 members (12,963 bytes) and the snapshot by 4,197 bytes;
  a plain start by about 0.16 M fuel (+0.064%); a snapshot's start and program by nothing, its
  teardown (`Py_FinalizeEx`) by about 0.11 M (+0.14% of a `-c pass` call).
- **Writable mounts** (spec 034). `Mount(provider, guest, writable=True)` lets a guest create,
  write, append, truncate, make and remove folders and rename within a namespace your code
  serves. A writable mount's provider adds `write` (the whole file), `mkdir`, `remove`, `rmdir`
  and `rename`, each answering `None` or an `Errno`. A create or truncation reaches it at open as
  `write(path, b"")`; a file's bytes are handed over whole at close, at `fsync` and at every
  ending that returns a result (not when the call raises or the interpreter is exiting).
  `done.files.refused` and `refused_total` record every refused or unmade write, even on exit
  0 (`RefusedWrite`; `WritableFileProvider` for type checkers). Links are `ENOTSUP`; times are
  accepted and ignored; a rename to another writable preopen is `EXDEV`. Nothing is writable
  unless you say so. **`FileRecord.calls` now has eight keys** (the write half's zeros
  included) for every call with mounts, read-only ones too.
- **The stdlib zip carries package metadata** (spec 033). `importlib.metadata.version("numpy")`
  now answers `2.5.2` instead of raising `PackageNotFoundError`, and `distributions()` lists
  numpy, pandas, python-dateutil, six and tzdata at their pinned versions. A wheel keeps exactly
  `METADATA` and `entry_points.txt` of its `.dist-info`; numpy and pandas get their pinned sdists'
  `PKG-INFO` as `METADATA` (`make_stdlib_zip.py --metadata`). `files()` gives `None`: `RECORD` is
  not kept. A source tree that brings a `.dist-info` or `.egg-info` of its own now stops the
  build. Costs: the zip grows by 7 members (about 21 KB), every plain start by about 0.54 M fuel,
  and on the snapshot the first metadata lookup costs about 0.36 G fuel and `import numpy.testing`
  about 0.14 G more than before.
- **A wider `ctypes` stand-in** (spec 033). The one-function `recipes/ctypes_stub.py` becomes the
  package `recipes/ctypes_stand_in/` (`ctypes/__init__`, `ctypes/_types`, `ctypes/util` in the
  zip). It names wasm32's C types with CPython's aliases (`c_int is c_long`), sizes them, lets a
  module declare `Structure`, `POINTER`, `CFUNCTYPE` and array types, gives numpy each simple
  type's true dtype (never `dtype('O')`), and makes `ctypes.util.find_library` answer `None`. It
  loads no library, makes no instance and touches no memory: each raises
  `OSError("ctypes is unavailable on wasm32-wasi")`. So `import pandas.io.clipboard` and
  `import numpy.ctypeslib` now import, and sympy's and threadpoolctl's import-time names resolve.
  The types are built on first use, so `import numpy` does not pay for them. `help(ctypes)` and
  `np.info` of a C type work; asking numpy or pandas for the dtype of a `Structure`, `Union`,
  pointer, array or function type raises the `OSError` (no layout is computed). `-V` still says
  "no ctypes": no foreign function can be called.
- **`pip install wasi-python` runs programs** (spec 028). wasmtime-py (`wasmtime>=49,<50`) is
  now a required dependency, so the plain install runs `wasi_python.run` and `wasi-python run`;
  the `run` extra is no longer needed. It is kept, empty, so `pip install "wasi-python[run]"`
  still works. An embedder that brings its own wasmtime installs with
  `pip install --no-deps wasi-python` and uses `artifacts()`; importing the package still never
  loads wasmtime. Where wasmtime is missing or cannot load (its pure wheel on an unsupported
  platform), `run` raises one `ImportError` naming `wasmtime>=49,<50`, with wasmtime's own error
  as its cause. The release now proves the plain install on all three systems.
- **Added: read-only mounts** (spec 032). `run(..., mounts=[Mount(provider, "/work")])` serves
  a guest's ordinary file calls from the embedder's own code: a provider answers `stat`, `list`
  and `read` on normalized paths with a value or an `Errno`, never raising, and is counted and
  limited (`max_file_calls=`, default `DEFAULTS.file_calls`, 10,000; then `trapped` is `"out of
  file calls"`). A mount may sit at `/` (not with `root=`). No import is added: the runner
  shadows the guest's 29 descriptor calls on a second linker used only with mounts, and forwards
  every call it does not own to wasmtime's own WASI, fuel-neutral. `Completed.files` records the
  provider calls and faults. Exports `Mount`, `FileProvider`, `Stat`, `Errno`, `FileRecord` and
  `FileFault`. A call without mounts is unchanged.
- **The build says where it is** (spec 027; the artifact set is unchanged). `scripts/build.sh`
  runs a preflight first (the host, its tools, and 2.5 GiB free on a first build) and prints
  one line for it. Each step's line now ends with its time, `ok <step>: … [3m02s]`, and a
  passing build ends with a summary: the total time, the three artifacts with their sizes and
  hash prefixes, and the next command. On a terminal one status line below them shows the
  running step, its time against the last run, ninja's `[n/N]` and the time left; a pipe, `CI`,
  `TERM=dumb` or `--plain` gets the plain lines only, and the terminal ends showing exactly them.
- **A failure says why.** A failing step prints `FAILED <step>`, the last 20 lines of its log,
  and last one `ERROR <step>: <reason>` line, whose reason is the log's last line starting
  `ERROR` (or `exit <n>`). Before, the reason was the last line matching `error` anywhere, which
  could name a harmless `Checking for strerror... Yes.`. On GitHub Actions it is also an
  `::error` annotation.
- **New options:** `--list`, `--from STEP`, `--resume` (from the step the last run did not
  finish), `--check` (the preflight alone), `--plain` and `--help`. Nothing is skipped on its
  own. Ctrl-C stops the running step at once and exits 130; a TERM or HUP to `build.sh` alone
  waits for the running step, then exits 143 or 129. Each run's times go to
  `build/logs/timings.tsv`.
- **The download step** prints `fetched <name>` or `present <name>` per pin and ends with
  `downloads: <n> pins, <f> fetched, <v> verified`; it needs `curl` only for a pin it must fetch.
- **Fixed: a cancel during a door call is named `"cancelled"`** (spec 030). A call made with
  `cancel=` whose event was set while the `host` blocked in a door call for more than a few
  ticks ended with `trapped="error while executing at wasm backtrace:"`; so did a deadline that
  passed there under `cancel=`. They now end `"cancelled"` and `"deadline"`, with `exit_code`
  and `fuel_used` `None`, as they do while the guest computes. The door's answer is still not
  delivered then, and a host's own cancellation (an exception such as
  `asyncio.CancelledError`) or a Ctrl-C still comes first.

### Judge

- **numpy's and pandas' own tests run in the guest** (spec 050): upstream's fast selection, 11
  groups, 63,717 passing in the snapshot binary; each known failure is a gap listed by node id
  (12 classes with members: platform facts the README states, and numpy's C test modules); no
  test traps the guest. A new metric, `passes`, may fall only with `--accept-fewer-passes`. The
  artifact set does not change.

## 0.1.0a3 — 2026-10-17

- **Breaking: nothing is writable by default** (the owner's rule, constitution §4.15; spec 025).
  A call given no root and no grants has no `/`, no `/tmp` and no `HOME`: it can import,
  compute, print, read the stdlib and call the door, and nothing else. Before, it got a fresh
  private writable `/`. To keep that, pass `root=True` (`--private-root` on the command line);
  or grant the folders the program needs. `root=None` now means no root, like `False`.
- **Security: a `root` is prepared only through the folder that was checked** (the 0.1.0a3
  security review, S1). The runner made `root/usr/local/lib` and `root/tmp` by path after
  checking the root, so a guest of another call with a writable folder above it could swap that
  folder for a link in between, and the runner removed a file named `usr`, `local`, `lib` or
  `tmp`, or made folders, outside every grant. It now works through the walked folder's
  descriptor; the guest never saw the wrong folder before, and still does not. A writable grant
  at, inside or above the host Python's own `stdlib` or `site-packages` is now refused (S2). The
  patch applier refuses a source tree that holds `.git` (S3).
- **`np.save` and `np.load` of files work** (the first carried patch,
  `recipes/patches/numpy-2.5.2/0001-npy-files-without-dup.patch`): they raised `OSError` 58,
  because numpy's `tofile`/`fromfile` need `os.dup`, which WASI lacks. The patch is the fix numpy
  is asked to take (its pull request is drafted for the owner) and goes when numpy releases it.
  `ndarray.tofile`, `np.fromfile` on real files and memory maps still fail. The next §5.6 security
  review reads this patch.
- **Carried patches** (the owner's decision; constitution §4.1): a fix the project cannot wait
  for may now be carried as a patch to a pinned project's source, under `recipes/patches/`, with
  its upstream pull request drafted under `context/upstream/patches/`. Each is reviewed, hashed in
  `MANIFEST`, named here, and deleted once upstream releases the fix. None is carried yet; the
  release check is now "the source trees are their tarballs plus the recorded patches".
- **Typed grants:** `run(grants=[Grant(host, guest, writable=False), ...])` gives the guest
  more host folders, each read-only unless it says `writable=True`, nested in any order;
  `root=False` gives it no `/`, only its grants. Every grant and `root` is walked folder by folder
  and checked before any work: no link a guest could have made, no read-only grant inside a
  writable one, no writable grant at, inside or above the runtime's own folders. After wasmtime
  opens each folder, the runner checks it opened the one it checked. `HOME` is made in the folder
  the guest sees at `/tmp`, and there is none without one.
- **The stdlib zip is read-only and no longer copied into a root:** every call sees it read-only
  at `/usr/local/lib`, from one folder per process that its exit removes (a killed process's is
  swept like its other folders). A `python315.zip` that 0.1.0a2 left in a reused root is never
  read again and may be deleted.
- **Some `root=` values are now refused** (a change): a root at, inside or above the runtime's
  own folders, such as the home folder, a project folder holding `.venv` or `build/artifacts`,
  or the temporary folder itself, since its guest could change files later calls trust; a root
  holding `wasi_python`'s or wasmtime-py's own code; a root still to be made where the module
  cache will be made; and a root reached through a link in a folder you can write. A missing
  root is still made. No grant, read-only either, may hold the temporary folder, which holds
  every call's private folders and `stdin`.
- **Grants on the command line:** `wasi-python run --grant GUEST=HOST`, `--grant-writable
  GUEST=HOST`, `--root HOST` and `--no-root`, each one of `run`'s arguments.
- **`wasi-python run`:** a command that runs one program and prints its result as one line of
  JSON, so any language can run agent code by spawning it (`python -m wasi_python run` is the
  same). Each option is one of `run`'s arguments; without options the call has `run`'s defaults.
- **A killed process's files are cleaned up:** a process killed mid-call left its private root
  (the guest's files) and its stdin folder (the caller's `stdin`) in the temporary folder for
  good. Each now has a locked lock file beside it naming the kernel that made it; the next
  wasi_python process on that kernel removes them at its first call, and never touches a live
  call's folders or another kernel's. On a temporary folder without file locks, calls go on
  and such folders stay, as before.
- **`trapped` names a trap by its kind** (a change to what it says): a stack overflow now reads
  `"stack overflow"`, not wasmtime's heading `"error while executing at wasm backtrace:"`, and so
  do `"unreachable"`, `"memory out of bounds"` and every other trap with a code. An error with no
  trap code keeps its first line.
- **The released wheel is the bytes a second host rebuilt:** the release workflow rebuilds the
  wheel on arm64 Linux and publishes only a wheel equal to it, byte for byte, whose artifacts
  match the set's `SHA256SUMS`.
- **Run from async code:** `run_async` runs a call on a worker thread, so an async server's
  event loop never waits for a guest. Cancelling the awaiting task stops the guest (checked
  every 50 ms while it computes, at once when it waits or calls the door, later when other
  threads hold the GIL) and frees its worker before `CancelledError` is raised. Calls share one
  pool per process of `DEFAULTS.async_workers` threads (the CPU count, at most 8).
  `run(cancel=event)` stops a guest from any thread (`trapped == "cancelled"`). A process forked
  after it ran a guest now refuses to run guests, instead of aborting (macOS) or losing its
  deadlines; at exit, `run_async`'s guests are stopped and its queued calls dropped.
- **sqlite3, bz2 and lzma are built in**, from three new pins (SQLite 3.54.1, bzip2 1.0.8,
  liblzma from xz 5.8.4), with no upstream patch. `bz2`, `lzma` and `tarfile`'s `bz2` and `xz`
  modes write the same bytes as native; `sqlite3` gives native's results, except the last digits
  of its math functions (trigonometric, hyperbolic, `atan2`, `log10`, one-argument `log`), which
  follow the guest's C library, and what changed since native's SQLite 3.53.1, such as JSON's
  float text; it has the native feature set (FTS3/4/5, R-tree, Geopoly, math functions,
  dbstat, percentile). `shelve` and `dbm` now create `dbm.sqlite3` files, as native does. `-V`
  now says "no ctypes, mmap, sockets, ssl or zstd": `compression.zstd` is the compression module
  still missing.
- **SQLite's limits in the guest** (the README's *sqlite3 in the guest*): one connection holds
  the database, through a `<db>.lock` directory beside it, while it writes or has a statement
  open, so a second connection gets "database is locked" after its busy timeout (5 s by
  default); `journal_mode=wal` stays `delete` unless `locking_mode=exclusive`; a guest stopped
  inside a transaction (killed, out of fuel, past its deadline, or by `os._exit`) leaves the
  lock and a hot journal in a reused root for the embedder to remove; SQLite's own
  `random()`, `randomblob()` and temporary names are seeded from the clock's second, so use
  `secrets`, `uuid.uuid4()` or `os.urandom` for IDs; a database in a read-only directory opens
  only through a URI that takes no lock, such as `file:<path>?immutable=1`; no
  `load_extension`; `sqlite3.threadsafety` is 0.
- **Sizes:** the three libraries add about 2 MB to `python.wasm` (SQLite is most of it); the zip
  is unchanged. `import bz2` and `import lzma` cost nothing more on the snapshot, which already
  holds them; `import sqlite3` is not pre-imported.

## 0.1.0a2 — 2026-10-17

The second alpha moves the line to CPython 3.15.0 and wasi-sdk 33, so a C++ exception inside a
package becomes a Python exception instead of ending the guest.

- **The line:** CPython 3.15.0, built with wasi-sdk 33; numpy 2.5.2, pandas 3.0.6 and the
  pure-Python packages are unchanged. The line's versions are named once, in
  `scripts/line.conf`.
- **C++ exceptions work:** numpy and pandas' C++ is compiled for WebAssembly exception handling
  in its standard form (`exnref`). A C++ error such as pocketfft's failed allocation now raises
  `MemoryError` in the program, which goes on.
- **Hosts must support exception handling.** wasmtime 47 or later runs it by default (as
  wasmtime-py does); wasmer, wazero and Node need a switch; WAMR and wasmi cannot run it. The
  README's *Hosts* lists them. For a host without it, use `0.1.0a1`.
- **The stdlib zip's guest name is now `/usr/local/lib/python315.zip`.** An embedder that lays
  out the root by hand must follow it; `wasi_python.run` does.
- **The snapshot** is made by the pinned wasmtime's own `wasmtime wizer` (the standalone Wizer
  pin is gone), and pre-imports `_colorize`, which 3.15 loads lazily, so the first traceback in
  a run does not pay for it.
- **Measured:** a snapshot call costs about 6.6% more guest instructions than on 3.14 (81.9M
  against 76.8M: CPython 3.15's own start-up and finalization); the stdlib zip is 6% larger.
- **Safe by default** (`run` changes for existing callers):
  - with no `root`, a call runs in a fresh private directory, removed afterwards;
  - a call has a 60 s deadline, a 1 GiB memory cap and a 16 MiB output cap per stream unless it
    passes others (`None` means no limit); a longer job now ends with `trapped == "deadline"`;
  - the guest's environment starts from `TMPDIR=/tmp`, `PYTHONTZPATH=` and a `HOME` made
    fresh for each call (under `/tmp`, removed after it), with `env=` laid over it, so
    `os.environ` is no longer exactly what `env=` gave;
  - a call's store is closed when the call ends, trapped or not, so a trapped call no longer
    holds its guest memory until Python's garbage collector runs;
  - `Completed` gains `truncated`, last, defaulting to `()`.
  - `run` refuses a limit of the wrong type (`TypeError`) or out of range (`ValueError`) before
    any work, where 0.1.0a1 passed it on: a negative `fuel` or `memory_bytes`, or a
    `memory_bytes` of 2**63 or more, meant no limit; `True` meant 1; a deadline of 0 or less ran
    one tick. Integer limits take any integer type (numpy's included) from 0 to 2**63 - 1; a
    deadline is a positive real number of seconds (not `Decimal`), at most about 4.6e16.
  - `run` refuses an `argv`, `env` or `stdin` the guest would see differently, before any work: a
    NUL in an argument, key or value, or text that is not valid UTF-8 (`ValueError`); an `=` in a
    key, or an empty key (`ValueError`); a `str` as `argv`, a non-`str` item or entry, or an `env`
    that is not a `Mapping` (`TypeError`). `stdin` must be bytes-like: `""`, `0`, `False` and
    `[]`, which meant empty input, are now a `TypeError`, as any other `str` already was. Messages
    never quote a value.
- **Planted code never runs:** only the stdlib zip is on `sys.path` and `site` does not run
  (`sys.flags.no_site == 1`), so a module, `.pth` or `pyvenv.cfg` one call leaves in a root is
  never run by the next. The plain reactor ran them before.
- **The door is bounded:** a frame past guest memory, a response over 2 GiB or a failing host is
  a host fault (−2); `run` no longer raises for them.
- **Fuel counts the guest only:** `fuel_used` and the `fuel` cap start after instantiation, so
  they no longer include wasmtime's copy of the memory image (42.35M instructions for the
  snapshot, 5.05M for the plain reactor, charged on macOS when compiled in the process and on
  Windows always). Figures from 0.1.0a1 are that much higher.
- **A sleeping guest keeps its deadline:** `time.sleep` and `select` no longer hold a call past
  its deadline; the runner answers the guest's waits itself, stopping at the deadline. One
  `poll_oneoff` takes at most 4,096 subscriptions (more answer `ENOMEM`: `select.poll()` on more
  than 2,047 descriptors), and a bad pointer answers `EFAULT`.
- **Concurrent calls share nothing:** calls from many threads no longer corrupt wasmtime-py's
  callback tables (after a few hundred concurrent calls, every later call raised, and a guest
  could reach another call's host or output). The host functions are defined once per engine,
  and outputs use the runner's own table. An exception a host raises, and Ctrl-C, now come back
  to the call that caused them; Ctrl-C while a guest computed could abort the whole process. A
  trap or exit inside the guest's allocator during a door call is that call's result, and its
  `fuel_used` is `None`. Concurrent first calls compile the module once.
- **A guest cannot make `run` raise by exhausting host file descriptors:** the call's store,
  which holds every descriptor the guest opened, is now closed before anything else is cleaned
  up. Before, `run` raised `OSError` (Errno 24) and left the stdin scratch file behind.
- **Release provenance:** from this release on, every asset is attested by the release workflow
  and verified before it is published; the notes say how to verify a download.
- **The snapshot honours extra preopens** by name and in any order, as the plain reactor does;
  before, it ignored them or swapped them.
- **The same bytes from any build host:** arm64 macOS and arm64 Linux rebuild the same artifact
  set from the pins, byte for byte, and the release workflow rebuilds it on an arm64 Linux runner
  and compares `SHA256SUMS` before anything is signed. x86_64 Linux is pinned and builds, but its
  `python.wasm` is not yet byte-identical (one numpy function compiles differently there).
  Every host links wasi-sdk's
  host-neutral sysroot and builtins, and the build sorts in the C locale, so `python.wasm`'s hash
  changes. Inside the guest, `sysconfig` and `numpy.show_config()` name the build machine
  `build`. `MANIFEST`'s `pin` lines now list every supported build host's inputs.
## 0.1.0a1 — 2026-10-17

The first alpha: CPython 3.14.8 for `wasm32-wasip1` with numpy 2.5.2 and pandas 3.0.6 compiled
in, built from pinned sources with no upstream patches.

- **The artifact set:** `python.wasm` (a WASI reactor), `python-snapshot.wasm` (the same binary
  with numpy and pandas pre-imported by Wizer), the bytecode-only stdlib zip (with
  python-dateutil, tzdata and six), `MANIFEST`, `SHA256SUMS` and the licence notices. Each
  rebuilds to the same bytes on one host.
- **The guest:** two imports only, WASI preview1 and one host door (`host::call`); `run` follows
  CPython's command line (`-c`, `-m`, a script, stdin, `-u`, `-V`).
- **The runner:** `wasi_python.run(argv, root=...)` runs one program in one call, with a host
  function for the door, fuel, a deadline, a memory cap and a private compiled-module cache
  (the `run` extra).
- **Known limits:** numpy's default integer is 32-bit; no threads, sockets, ssl, sqlite3, bz2 or
  lzma; a C++ exception aborts the guest (wasi-sdk 24); compute is about 1.3 to 2.3 times slower
  than native. Built and judged on arm64 macOS; the release workflow also checks it on Linux
  and Windows.

