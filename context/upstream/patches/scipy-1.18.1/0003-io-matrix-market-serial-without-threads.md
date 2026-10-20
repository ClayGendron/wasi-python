- **Project:** scipy (https://github.com/scipy/scipy)
- **Against:** 1.18.1 (the pinned tarball)
- **Status:** drafted
- **Title:** io: read and write Matrix Market serially by default on Emscripten and WASI
- **Files:** scipy/io/_fast_matrix_market/__init__.py
- **Why we carry it:** on `wasm32-wasip1` a thread cannot be started, so `scipy.io.mmread` and `mmwrite` at their default parallelism raise `RuntimeError`.

**This is a facts sheet, not a pull request.** scipy's AI policy
(https://scipy.github.io/devdocs/dev/conduct/ai_policy.html, READ 2026-10-20) says: "The use of
an AI agent that writes code and then submits a pull request autonomously is not permitted"; "In
explaining your contribution, do not use AI to automatically generate descriptions"; and "You must
disclose whether AI has been used to assist in the development of your pull request", naming the
tools, how they were used and what is AI generated. If the owner sends it, he writes the issue or
pull request himself from these facts, with that disclosure. Nothing has been posted.

**What is wrong.** `scipy/io/_fast_matrix_market/__init__.py` sets `PARALLELISM = 0` (line 24),
"number of CPUs". Any value but 1 takes fast_matrix_market's threaded path
(`read_body.hpp:477`, `write_body.hpp:68`; both test only `num_threads != 1`), whose pool starts
at least one worker (`task_thread_pool.hpp:137-142`). On WASI (`wasm32-wasip1`, no threads)
`std::thread::hardware_concurrency()` is 1 and constructing a `std::thread` throws
`std::system_error`, so every `mmread` and `mmwrite` at the default raises `RuntimeError`, even
for a one-line matrix in an `io.BytesIO`. Emscripten without pthreads has the same limit; Pyodide
skips scipy's Matrix Market tests for it (`pyodide-recipes`, `packages/scipy/scipy-conftest.py`).

**The change.** Import `sys`; set `PARALLELISM = 1 if sys.platform in ("emscripten", "wasi")
else 0`; the docstring says why. Nothing else: a program may still set `PARALLELISM`, and the
threadpoolctl controller reports and sets the same variable. On every other platform the default
is unchanged.

**A deeper fix, for the maintainers to weigh.** fast_matrix_market itself (which scipy vendors)
could run serially when a requested count of 0 resolves to `hardware_concurrency() == 1`. That
would help any one-core host, not only these two platforms, but it is a change to the vendored
C++ and to its upstream; the one-line Python default is the smaller fix for scipy.

**How it is checked** (this project's spec 038; the result is written here when its build has
run). In this project's statically linked CPython for `wasm32-wasip1`, a sparse and a dense
matrix written with `mmwrite` to an `io.BytesIO` and read back with `mmread` must give the same
matrix, with nothing writable, on both of its binaries, and the bytes written must equal native
scipy's, which writes with threads (fast_matrix_market writes its chunks in order).
**Result** (2026-10-20, the build of spec 038): both hold on both binaries; the SHA-256 of
the bytes written equals native scipy 1.18.1's for a sparse and a dense matrix.

It is deleted, and the pin moved, when a scipy release carries the fix.
