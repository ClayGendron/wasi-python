# Changelog

One section per release of the `wasi-python` artifact set and wheel, newest first. A section's
body is the release's notes on GitHub. `release/version.py bump` adds a section; `release/version.py
release` dates it and tags the release (context/specifications/004-alpha-releases.md).

## 0.1.0a3 — unreleased

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

