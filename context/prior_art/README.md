# Prior art

Shallow clones of the projects this one learns from. They live here so
a study can grep them in place; git ignores everything in this
directory except this index. **Read-only. Study, cite, describe; never
copy code.** Building a dependency from its released tarball (the
`downloads/` pins) is a different thing from this directory.

Refresh a clone before studying it (`git fetch --depth 1 origin && git
reset --hard FETCH_HEAD` inside it), re-check its licence, and record
the commit in the memo that cites it.

| clone | what we study in it | licence | cloned 2026-10-16 at |
|---|---|---|---|
| `cpython` (branch 3.14) | `Tools/wasm/wasi`, `Modules/makesetup`, `Modules/getpath.py`, `Python/import.c` (`is_builtin`) | PSF-2.0 | 7c04882 |
| `cpython-wasi-build` | Brett Cannon's release recipe and the SDK pin per Python line | MIT | 7ce0aaf |
| `pyodide` | the Emscripten shape of the same problem; the numpy recipe and its cross-build files | MPL-2.0 | 6754c1f |
| `pyodide-recipes` | package recipes: matplotlib (C++ exceptions, five patches), scipy (f2c, OpenBLAS), pandas | MPL-2.0 | 01bd0af |
| `wasi-sdk` | the toolchain releases; `CppExceptions.md`; the SDK-33 exception sysroot | Apache-2.0 with LLVM exception | 2b65040 |
| `wasi-libc` | the preview1 libc: the preopen table, `-lc-printscan-long-double`, the emulated signal/clock/getpid | Apache-2.0 / MIT (see its LICENSE) | 165235b |
| `wizer` | snapshotting: init function, `--mapdir`, why a reactor is needed | Apache-2.0 with LLVM exception | 6130150 |
| `wasmtime` | the host: epoch interruption, fuel, store limits, `.cwasm` serialization | Apache-2.0 with LLVM exception | 2d9c19b |
| `wasmtime-py` | the Python embedding our runner uses: `Linker.define_func`, `Module.deserialize_file` | Apache-2.0 with LLVM exception | 280ce73 |
| `componentize-py` | the link-time precedent for putting extension modules into one binary | Apache-2.0 with LLVM exception | 9ff99da |
| `webassembly-language-runtimes` | the WLR Python builds that embed the stdlib with wasi-vfs | Apache-2.0 | 5a40c30 |
| `numpy` | `meson.build`, `meson_cpu` (wasm32 family), `random/meson.build` (the double build of `distributions.c`) | BSD-3-Clause | ac61120 |
| `pandas` | `meson.build` (`_cyutility`), the unconditional `ctypes` and `mmap` imports | BSD-3-Clause | 3ce0a8c |
| `wasi-virt` | virtualizing a component's filesystem; the post-preview1 direction | Apache-2.0 with LLVM exception | 448f6df |

Removed: `bashkit` (everruns/bashkit; no licence file in the clone).
Its Wizer snapshot of CPython 3.14 and its HTTP door are studied
through its public README only.
