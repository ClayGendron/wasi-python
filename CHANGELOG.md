# Changelog

One section per release of the `wasi-python` artifact set and wheel, newest first. A section's
body is the release's notes on GitHub. `release/version.py bump` adds a section; `release/version.py
release` dates it and tags the release (context/specifications/004-alpha-releases.md).

## 0.1.0a2 — unreleased

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
- **Planted code never runs:** only the stdlib zip is on `sys.path` and `site` does not run
  (`sys.flags.no_site == 1`), so a module, `.pth` or `pyvenv.cfg` one call leaves in a root is
  never run by the next. The plain reactor ran them before.
- **The door is bounded:** a frame past guest memory, a response over 2 GiB or a failing host is
  a host fault (−2); `run` no longer raises for them.
- **Fuel counts the guest only:** `fuel_used` and the `fuel` cap start after instantiation, so
  they no longer include wasmtime's copy of the memory image (42.35M instructions for the
  snapshot, 5.05M for the plain reactor, charged on macOS when compiled in the process and on
  Windows always). Figures from 0.1.0a1 are that much higher.
- **The snapshot honours extra preopens** by name and in any order, as the plain reactor does;
  before, it ignored them or swapped them.

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

