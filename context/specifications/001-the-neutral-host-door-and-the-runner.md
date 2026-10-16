# 001 — The neutral host door and the runner

- **Status:** draft, 2026-10-16; amended the same day to answer
  finding 9 of `../reviews/002-the-progress-harness-spec-2026-10-16.md`
- **Owner:** Clay Gendron
- **Kind:** feature (`recipes/host*.c`, `scripts/08_build_reactor.sh`,
  `src/wasi_python/run.py`, `tests/`)
- **Depends on:** 002 (the progress harness): this specification lands
  by turning its v1.1, v1.2 and v1.4 checks from `blocked` to `pass`.
- **Research it stands on:**
  `../research/2026-10-16-the-spike-that-proved-the-build.md`
  (findings 5 and 7: the door and the reactor; question 7 of its
  pipeline plan), and the session's run of the spike's binaries under
  the plain wasmtime CLI, which failed to instantiate them because
  they import `vfs::ping`.

## Decisions

1. **The door is one import, `host::call`.** The binary declares
   exactly one custom import beside `wasi_snapshot_preview1`:
   `host::call(ptr: i32, len: i32, out_ptr_ptr: i32, out_len_ptr: i32)
   -> i32`. The guest passes a request frame; the host writes a
   response frame into guest memory it asks the guest to allocate
   (the two-step pattern: the host calls the exported
   `host_alloc(len) -> ptr`, writes, and stores the pointer and
   length). The return value is 0 when a host answered, −1 when no
   host is bound (the default binding), and −2 on a host fault. Frames are opaque bytes to this project; an
   embedder defines their content.
2. **The guest module is `_host`**, a C module compiled in, exposing
   `_host.call(frame: bytes) -> bytes` and `_host.available() ->
   bool`. On −1 `_host.call` raises `ConnectionRefusedError`; on −2 it
   raises `OSError`. `_host.available()` is `True` only when the last
   call was answered with 0. No pure-Python package wraps it here; an embedder ships its
   own (vfs ships `vfs`).
3. **Every build carries the door.** There is no door-less variant.
   A runner binds it; the default binding answers every call with
   the "no host" code, so the artifact runs under `wasi_python.run`
   with nothing attached. The plain wasmtime CLI cannot instantiate
   the binary, and the README says so.
4. **The reactor exports** are `_initialize`, `wizer.initialize` and
   `run`. `wizer.initialize` sets `use_hash_seed = 1` and
   `hash_seed = 0` in the config it initializes with, so the snapshot's
   hash secret is the same on every rebuild: the snapshot reproduces
   byte for byte and its fuel repeats (finding N1 of the 002 review).
   This costs nothing: a published snapshot's secret is already shared
   by everyone who downloads it and readable from its bytes. The plain
   reactor's `_initialize` path keeps a secret from `random_get`. `run` reads argv and the environment through the WASI calls
   on every invocation, sets `sys.argv` and refreshes `os.environ`,
   honours `-c code`, `-m module`, `-I`, `-u` and a script path,
   flushes `sys.stdout` and `sys.stderr`, and returns the exit code.
5. **The runner** is `wasi_python.run(argv, *, root, env=None,
   stdin=None, host=None, snapshot=True, fuel=None, deadline_s=None,
   memory_bytes=None, cache_dir=None) -> Completed`, over wasmtime-py
   (the `run` extra). It preopens `root` at `/`, lays out the stdlib
   zip at `/usr/local/lib/python3XY.zip` inside `root` if it is not
   there, binds `host::call` to `host` or to the default, calls
   `_initialize` then `run` for the plain binary and `run` alone for
   the snapshot, records the exit code before any trap propagates,
   and returns `Completed(exit_code, stdout, stderr, trapped)`. The
   compiled module is cached as `.cwasm` under `cache_dir`, keyed by
   wasmtime version and the artifact's hash. `fuel` caps the guest's
   executed instructions (a deterministic bound); `deadline_s` is an
   epoch deadline for embedders, and no test asserts on it.
6. **Names.** The recipe files `vfsmodule.c`, `vfs_main.c`,
   `vfs_inittab.c` become `hostmodule.c`, `reactor_main.c`,
   `inittab.c`; the `vfs` line in `Setup.local` becomes `_host`; the
   export `vfs_run` becomes `run`; the link script
   `08_build_vfsmain.sh` becomes `08_build_reactor.sh`.

7. **The build writes an artifact directory.** The link and snapshot
   steps write `build/artifacts/` in the layout spec 002 reads
   (Decision 12 there): the two binaries, the stdlib zip, `MANIFEST`,
   `SHA256SUMS`, and `LICENSES/<component>.txt`, each copied from the
   pinned source's top-level licence file (for `wasi-libc` and
   `llvm-runtimes`, from the wasi-sdk tarball). The checks run against it with
   `WASI_PYTHON_ARTIFACTS=build/artifacts uv run pytest`.

## Intent

After this specification any embedder, in any language with a
wasmtime binding, can run the artifact: preopen a directory, bind
one function, call `run`. The runner in the wheel does that for
Python embedders in one call and is what the verification tests use.

## Design

- `recipes/hostmodule.c`: the import declaration
  (`__attribute__((import_module("host"), import_name("call")))`),
  `host_alloc` exported (`malloc`), `_host.call` copying the request
  into guest memory, invoking the import, and returning the response
  as `bytes`, or raising as Decision 2 says for −1 and −2;
  `_host.available()` returns whether the last call was answered
  with 0.
- `recipes/reactor_main.c`: the spike's `vfs_main.c` with argv and
  env read per call and the two names changed.
- `src/wasi_python/run.py`: the runner; `Completed` as a frozen
  dataclass; no global state; one `Engine` per process, cached.
- Tests: none of its own. The checks are spec 002's, in
  `tests/checks/test_v1_1_artifact_set.py` (imports and exports),
  `test_v1_2_portable_and_sealed.py` and `test_v1_4_embedding.py` (the
  door, exit codes, argv and environment, and the three `runner`
  checks, the runaway one bounded by `fuel`). The spike's preview1
  call count is not asserted: the judge meters fuel, not WASI calls,
  and the snapshot's cost is ratcheted as fuel.

## Scope

In: the above. Out: the frame format (the embedder's); a pure-Python
`host` package; running under the component model; threads.

## Acceptance criteria

1. `wasm-objdump -x python.wasm` lists imports from exactly two
   modules, `wasi_snapshot_preview1` and `host`, and the export list
   contains `memory`, `_initialize`, `wizer.initialize`, `run`,
   `host_alloc`.
2. Against `build/artifacts/`, every spec 002 check in
   `test_v1_1_artifact_set.py` except the wheel check, every one in
   `test_v1_4_embedding.py`, and `test_guest_runs_here` are `pass` or a
   gap whose closer is another document, and the run is accepted into
   `context/progress/`.
3. The README's "Running it" section shows the runner call and no
   longer mentions `vfs::ping`.
4. `uv run ruff check src tests`, `uv run ruff format --check src
   tests` and `uv run pytest` are green.

## Landing notes

(Filled in on landing.)
