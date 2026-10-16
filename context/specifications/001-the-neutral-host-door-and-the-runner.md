# 001 — The neutral host door and the runner

- **Status:** draft, 2026-10-16
- **Owner:** Clay Gendron
- **Kind:** feature (`recipes/host*.c`, `scripts/08_build_reactor.sh`,
  `src/wasi_python/run.py`, `tests/`)
- **Depends on:** nothing; first specification.
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
   length). The return value is 0 on success and a small negative
   code on a host fault. Frames are opaque bytes to this project; an
   embedder defines their content.
2. **The guest module is `_host`**, a C module compiled in, exposing
   `_host.call(frame: bytes) -> bytes` and `_host.available() ->
   bool`. No pure-Python package wraps it here; an embedder ships its
   own (vfs ships `vfs`).
3. **Every build carries the door.** There is no door-less variant.
   A runner binds it; the default binding answers every call with
   the "no host" code, so the artifact runs under `wasi_python.run`
   with nothing attached. The plain wasmtime CLI cannot instantiate
   the binary, and the README says so.
4. **The reactor exports** are `_initialize`, `wizer.initialize` and
   `run`. `run` reads argv and the environment through the WASI calls
   on every invocation, sets `sys.argv` and refreshes `os.environ`,
   honours `-c code`, `-m module`, `-I`, `-u` and a script path,
   flushes `sys.stdout` and `sys.stderr`, and returns the exit code.
5. **The runner** is `wasi_python.run(argv, *, root, env=None,
   stdin=None, host=None, snapshot=True, deadline_s=None,
   memory_bytes=None, cache_dir=None) -> Completed`, over wasmtime-py
   (the `run` extra). It preopens `root` at `/`, lays out the stdlib
   zip at `/usr/local/lib/python3XY.zip` inside `root` if it is not
   there, binds `host::call` to `host` or to the default, calls
   `_initialize` then `run` for the plain binary and `run` alone for
   the snapshot, records the exit code before any trap propagates,
   and returns `Completed(exit_code, stdout, stderr, trapped)`. The
   compiled module is cached as `.cwasm` under `cache_dir`, keyed by
   wasmtime version and the artifact's hash.
6. **Names.** The recipe files `vfsmodule.c`, `vfs_main.c`,
   `vfs_inittab.c` become `hostmodule.c`, `reactor_main.c`,
   `inittab.c`; the `vfs` line in `Setup.local` becomes `_host`; the
   export `vfs_run` becomes `run`; the link script
   `08_build_vfsmain.sh` becomes `08_build_reactor.sh`.

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
  as `bytes`; `_host.available()` returns whether the last call was
  answered by a real host (the default binding sets a flag through a
  second response code).
- `recipes/reactor_main.c`: the spike's `vfs_main.c` with argv and
  env read per call and the two names changed.
- `src/wasi_python/run.py`: the runner; `Completed` as a frozen
  dataclass; no global state; one `Engine` per process, cached.
- Tests (`tests/test_run.py`, marked `artifact`, skipped when
  `wasi_python.artifacts()` raises): `run(["-c", "print(1)"])`
  prints `1` with exit 0; `run(["-c", "import sys; sys.exit(3)"])`
  returns 3; a script reading and writing under `root` sees the
  files; `_host.call(b"x")` with no host returns the "no host"
  response and `_host.available()` is false; with a host bound to
  `lambda frame: frame[::-1]` the guest gets the reversed bytes;
  `sys.argv` and `os.environ` reflect the call; a spinning script
  with `deadline_s=0.5` reports `trapped` and no exit code; the
  preview1 call counts for `-c pass` on the snapshot are at most the
  spike's 96 for the whole pandas job, asserted as a count.

## Scope

In: the above. Out: the frame format (the embedder's); a pure-Python
`host` package; running under the component model; threads.

## Acceptance criteria

1. `wasm-objdump -x python.wasm` lists imports from exactly two
   modules, `wasi_snapshot_preview1` and `host`, and the export list
   contains `memory`, `_initialize`, `wizer.initialize`, `run`,
   `host_alloc`.
2. All tests in `tests/test_run.py` pass against a freshly built
   artifact in the release workflow, and are skipped cleanly in a
   source checkout.
3. The README's "Running it" section shows the runner call and no
   longer mentions `vfs::ping`.
4. `uv run ruff check`, `uv run ruff format --check` and
   `uv run pytest` are green.

## Landing notes

(Filled in on landing.)
