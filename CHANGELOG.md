# Changelog

One section per release of the `wasi-python` artifact set and wheel, newest first. A section's
body is the release's notes on GitHub. `release/version.py bump` adds a section; `release/version.py
release` dates it and tags the release (context/specifications/004-alpha-releases.md).

## 0.1.0a1 — unreleased

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

