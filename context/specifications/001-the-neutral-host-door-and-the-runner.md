# 001 — The neutral host door and the runner

- **Status:** draft, 2026-10-16; amended twice the same day: to answer
  finding 9 of `../reviews/002-the-progress-harness-spec-2026-10-16.md`,
  then to hand the guest half to spec 003.
- **Owner:** Clay Gendron
- **Kind:** feature (`src/wasi_python/run.py`, `pyproject.toml`,
  `README.md`)
- **Depends on:** 002 (the harness) and 003 (the artifact set it runs:
  the door, the reactor and the build, which this specification first
  decided and 003 now owns).
- **Research it stands on:**
  `../research/2026-10-16-the-spike-that-proved-the-build.md`
  (findings 5 and 7: the door and the reactor; the spike's in-process
  runs under wasmtime-py), `../research/2026-10-16-fuel-as-the-operation-count.md`
  (finding 4: a fuel cap is a deterministic bound).

## Decisions

1. **The guest's contract is spec 003's**, Decisions 5 and 6 there:
   one custom import, `host::call(ptr, len, out_ptr_ptr, out_len_ptr)
   -> i32`, answered 0 (a host answered), −1 (no host bound) or −2
   (host fault), with the response written through the guest's
   `host_alloc`; exports `memory`, `host_alloc`, `run`, and on the
   plain reactor `_initialize` and `wizer.initialize`. Frames are
   opaque bytes; an embedder defines their content.
2. **Every build carries the door.** There is no door-less variant. A
   runner binds it; the default binding answers every call with −1,
   so the artifact runs under `wasi_python.run` with nothing attached.
   The plain wasmtime CLI refuses the binary's unknown import; with
   `-W unknown-imports-default` it runs it, but the door then returns
   0 with no response, which `_host` reads as an empty answer. The
   README says to use a runner that binds the door.
3. **The runner** is `wasi_python.run(argv, *, root, env=None,
   stdin=None, host=None, snapshot=True, fuel=None, deadline_s=None,
   memory_bytes=None, cache_dir=None) -> Completed`, over wasmtime-py
   (the `run` extra). It preopens `root` at `/`, always writes the
   artifact set's own zip to `/usr/local/lib/python3XY.zip` inside
   `root`, replacing what is there (`3.XY` from `MANIFEST`'s `python`
   line; the snapshot runs only beside the zip it was built against:
   003 Decision 9), binds `host::call` to
   `host` (a callable from request bytes to response bytes; an
   exception it raises answers −2) or to the default, calls
   `_initialize` then `run` for the plain binary and `run` alone for
   the snapshot, and returns `Completed(exit_code, stdout, stderr,
   trapped)`: `exit_code` is `run`'s return value or the code of a WASI
   `proc_exit`, and `None` when the guest trapped; `trapped` is `None`
   or the trap's first line. `fuel` caps the guest's executed
   instructions (a deterministic bound); `deadline_s` is an epoch
   deadline for embedders, and no test asserts on it; `memory_bytes`
   caps linear memory through the store's limits. The compiled module
   is cached as `.cwasm` under `cache_dir` (default: the user cache
   directory), keyed by the wasmtime version and the artifact's
   SHA-256; a `.cwasm` is never published (constitution §4.6). The
   runner answers `random_get` and `clock_time_get` from WASI as
   wasmtime does: only the judge's driver makes them deterministic.

## Intent

After this specification a Python embedder runs the artifact in one
call, and the README's "Running it" shows how any other embedder does
it: preopen a directory, bind one function, call one export.

## Design

- `src/wasi_python/run.py`: the runner; `Completed` a frozen
  dataclass; no global state but one cached `Engine` per process.
- `src/wasi_python/__init__.py` re-exports `run` and `Completed`, and
  imports wasmtime only inside `run`, so the package still imports
  without the `run` extra.
- Tests: spec 002's three runner checks in
  `tests/checks/test_v1_4_embedding.py`, which are blocked until
  `wasi_python.run` exists.

## Scope

In: the above. Out: the frame format (the embedder's); a pure-Python
`host` package; the component model; threads.

## Acceptance criteria

1. The three runner checks pass against `build/artifacts/`
   (`test_runner_runs_a_program_in_one_call`, `test_runner_binds_a_host`,
   `test_runner_stops_a_runaway_guest_by_fuel`), and the run is
   accepted into `context/progress/`.
2. `import wasi_python` works without wasmtime installed.
3. The README's "Running it" shows the runner call and the three-step
   contract, and no longer mentions the spike's import.
4. `uv run ruff check src tests`, `uv run ruff format --check src
   tests` and `uv run pytest` are green.

## Landing notes

(Filled in on landing.)
