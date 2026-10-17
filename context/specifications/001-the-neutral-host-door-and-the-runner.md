# 001 — The neutral host door and the runner

- **Status:** draft, 2026-10-16; amended three times the same day: to
  answer finding 9 of `../reviews/002-the-progress-harness-spec-2026-10-16.md`,
  to hand the guest half to spec 003, and, after 003 landed, to settle
  how the runner finds the artifacts, its engines and cache, its I/O and
  its limits.
- **Owner:** Clay Gendron
- **Kind:** feature (`src/wasi_python/runner.py`,
  `src/wasi_python/__init__.py`, `README.md`, judge edits in `tests/checks/`)
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
   memory_bytes=None, cache_dir=None, artifacts=None) -> Completed`,
   over wasmtime-py (the `run` extra). One call runs one program in a
   fresh store and instance and returns when it ends.
   - **Artifacts.** `artifacts` is an `Artifacts` (the package's
     dataclass of four paths) or `None`, which means
     `wasi_python.artifacts()`. That function resolves, in order:
     `$WASI_PYTHON_ARTIFACTS` when set and not empty; in a source
     checkout (the module at `<repo>/src/wasi_python/`, beside
     `<repo>/pyproject.toml`), `<repo>/build/artifacts/` when it holds a
     `MANIFEST`; and the wheel's own `artifacts/` beside the module when
     it holds one. This is the harness's order (003 Decision 10; the
     harness also reads an empty variable as unset), so the judge and
     the runner find the same set. Otherwise it raises
     `ArtifactsMissing`, naming the places.
   - **The root.** `root` is a host directory, created if absent and
     preopened at `/`; it is the guest's whole filesystem, and the
     guest can write anything in it, so the runner trusts nothing there.
     Before each call it places the artifact set's own zip at
     `/usr/local/lib/python3XY.zip` (`3.XY` from `MANIFEST`'s `python`
     line):
     - always as a copy, never a link to the artifact itself, so no
       guest write reaches the artifact set or another root;
     - through real directories only: a symbolic link or file the guest
       left in place of `usr`, `local` or `lib`, or of the zip, is
       removed and never followed;
     - replacing any file that is not byte for byte the artifact's zip,
       by renaming a fresh copy (made with a unique name in the same
       directory) over it (where Windows refuses the rename because a
       concurrent call's guest has the file open, the file in place is
       kept when it is byte for byte the right zip, and the rename's
       error stands otherwise); a directory the guest left there is removed
       first, without following links inside it. On POSIX a copy this
       process placed is recognised by its device, inode, size,
       modification and change times, and the change time is one a guest
       cannot set back, when the filesystem keeps sub-second times (a
       write within the same second would not show on one that keeps
       whole seconds); otherwise the file is hashed.

     The snapshot runs only beside the zip it was built against (003
     Decision 9). Concurrent calls may share a root, and placing the zip
     is safe among them: calls in one process place one root's zip one
     at a time (on Windows a file being renamed over cannot be opened, so
     an unserialized second call failed: spec 004's fourth dry run). The
     rename fallback above lets a process that renames find the zip
     already right; a call in another process reading the zip during
     someone else's rename can still fail on Windows. It is not safe
     against a guest running at the same
     time: one call's guest could change what another's sees, or swap
     in a link between the runner's check and its write and so make the
     runner write outside the root. An embedder gives each untrusted
     program its own root, or runs calls on a shared root one at a
     time.
   - **argv and environment.** The guest's `argv[0]` is
     `/usr/local/bin/python.wasm` and `argv` follows it; `run` handles
     it as 003 Decision 6 says. `env` (a mapping of str to str) is the
     guest's whole environment; nothing is inherited from the host.
   - **I/O.** `stdin` is `bytes` or `None` (empty). stdout and stderr
     are captured in memory through wasmtime's custom output callbacks
     and returned as `bytes`.
   - **The door.** `host` is a callable from request bytes to response
     bytes, or `None`. With `None` every call answers −1. Otherwise the
     runner reads the request from guest memory, calls `host`, asks
     `host_alloc` for space, writes the response and its pointer and
     length, and answers 0; an exception from `host`, a response that
     is not bytes-like, or a NULL from `host_alloc` answers −2 and
     writes nothing (003 Decision 5's contract).
   - **Order of calls.** `_initialize` then `run` when the module
     exports `_initialize` (the plain reactor); `run` alone otherwise
     (the snapshot). `snapshot` picks the binary.
   - **Limits.** `fuel` caps executed instructions (a deterministic
     bound); `deadline_s` is a wall-clock bound through epoch
     interruption: one daemon thread per process, while any call with a
     deadline runs, advances every engine's epoch once per 10 ms of wall
     time elapsed (catching up when a sleep runs long), and the store
     traps after `ceil(deadline_s / 0.01)` ticks. No test asserts on a
     wall-clock deadline. A `memory_bytes` below the binary's initial
     memory fails instantiation: `exit_code` is `None` and `trapped`
     carries wasmtime's first line. `memory_bytes` caps linear memory through
     the store's limits, so a guest allocation past it fails as a
     `MemoryError` in the guest, not a trap.
   - **Engines and the cache.** Fuel metering changes the compiled code,
     so the runner keeps two engines per process, one with fuel
     metering and one without, both with epoch interruption; a call
     uses the fuel engine only when `fuel` is given. A compiled module
     is cached in the process and, unless `cache_dir=False`, on disk as
     `<cache_dir>/<artifact sha256 prefix>-<wasmtime version>-<engine>.cwasm`,
     written to a temporary name and renamed into place. `cache_dir`
     defaults to `$WASI_PYTHON_CACHE` when set, else the user cache
     directory (`~/Library/Caches/wasi_python` on macOS,
     `%LOCALAPPDATA%\wasi_python\cache` on Windows,
     `$XDG_CACHE_HOME/wasi_python` or `~/.cache/wasi_python` elsewhere).
     A `.cwasm` that wasmtime refuses to load is compiled again and
     replaced. A `.cwasm` is native code that wasmtime runs as it finds
     it, so on POSIX the cache is used only when the directory (made
     `0700`) and each file (written `0600`) are owned by the user and
     writable by no one else; otherwise the runner warns
     (`RuntimeWarning`), neither reads nor writes there, and compiles in
     the process. On Windows the default cache is under the user's own
     profile. Anyone who can write to a private cache already runs
     code as its user, so the runner does not check which binary a
     `.cwasm` came from beyond its name. A `.cwasm` is never published
     (constitution §4.6).
     `wasi_python.runner.stats()` counts modules compiled, `.cwasm`
     files loaded and written in this process (a diagnostic the judge's
     cache check reads).
   - **The result.** `Completed(exit_code, stdout, stderr, trapped,
     fuel_used)`, a frozen dataclass. `exit_code` is `run`'s return
     value or the code of a WASI `proc_exit`, and `None` when the guest
     trapped. `trapped` is `None`, `"out of fuel"`, `"deadline"`, or
     the trap's first line. `fuel_used` is the instructions spent when
     `fuel` was given, and `None` otherwise or after a deadline trap
     (wasmtime does not bring its fuel count up to date on an epoch
     interrupt: EXECUTED, the landing notes).
   - **The door's addresses are unsigned.** wasmtime-py passes i32
     values as signed integers, so the runner masks every guest address
     and length to 32 bits before using it (the judge's driver too).
   - Without wasmtime-py, `run` raises `ImportError` naming
     `pip install "wasi-python[run]"`.
   - The runner answers `random_get` and `clock_time_get` from WASI as
     wasmtime does: only the judge's driver makes them deterministic.
     It shares no code with the judge's driver (`tests/harness/guest.py`).
4. **The README's "Running it"** shows the runner call and the
   contract any other embedder implements in three steps: preopen a
   directory at `/` holding the artifact set's zip at
   `/usr/local/lib/python3XY.zip`; bind `host::call` (answering −1 when
   there is no host); call `_initialize` (plain reactor only) and then
   `run` once per instance, with argv and the environment given through
   WASI.

## Intent

After this specification a Python embedder runs the artifact in one
call, and the README's "Running it" shows how any other embedder does
it: preopen a directory, bind one function, call one export.

## Design

- `src/wasi_python/runner.py` (not `run.py`, so the module never hides
  behind the function `wasi_python.run`): the runner; `Completed` a frozen
  dataclass; process state is the two engines, the module caches and
  the epoch thread.
- `src/wasi_python/__init__.py` re-exports `run` and `Completed`, and
  imports wasmtime only when `run` is called, so the package still
  imports without the `run` extra; `artifacts()` gains the resolution
  order of Decision 3.
- Tests: spec 002's three runner checks in
  `tests/checks/test_v1_4_embedding.py`, which are blocked until
  `wasi_python.run` exists, and five new v1.4 checks (a judge edit):
  `test_package_imports_without_wasmtime`,
  `test_runner_reports_a_host_fault`, `test_runner_caps_memory`,
  `test_runner_caches_the_compiled_module` (in two fresh processes:
  the first compiles and writes one `.cwasm`, the second loads it and
  compiles nothing), and `test_runner_runs_the_plain_reactor` (it tells
  the binaries apart by whether numpy is already imported); after the
  review, four more (five checks, the link check having two cases):
  `test_runner_refuses_a_cache_others_can_write`,
  `test_runner_keeps_the_artifact_zip_out_of_the_guests_reach`,
  `test_runner_never_follows_a_link_a_guest_left` (a link at the zip
  and at its directory), and
  `test_runner_serves_concurrent_calls_on_one_root`; after the
  confirmation, `test_runner_replaces_a_directory_left_in_the_zips_place`. The checks' conftest sets
  `$WASI_PYTHON_CACHE` to `build/cwasm-cache/`, so the judge never
  writes to the user's cache.

## Scope

In: the above. Out: the frame format (the embedder's); a pure-Python
`host` package; the component model; threads.

## Acceptance criteria

1. The three runner checks pass against `build/artifacts/`
   (`test_runner_runs_a_program_in_one_call`, `test_runner_binds_a_host`,
   `test_runner_stops_a_runaway_guest_by_fuel`), and the run is
   accepted into `context/progress/`.
2. `import wasi_python` works without wasmtime installed, and the five
   new checks pass.
3. The README's "Running it" shows the runner call and the three-step
   contract, and no longer mentions the spike's import.
4. `uv run ruff check src tests`, `uv run ruff format --check src
   tests` and `uv run pytest` are green.

## Landing notes

Built 2026-10-16 by the author agent, reviewed by a fresh agent
(`../reviews/001-the-neutral-host-door-and-the-runner-2026-10-16.md`),
and changed to answer the review. The figures below are from after the
changes.

**What was built.** `src/wasi_python/runner.py` (`run`, `Completed`,
`stats`) and the resolution order in `src/wasi_python/__init__.py`
(`artifact_dir()`, `artifacts()`), against the artifact set spec 003
landed (reactor `d77dc946962d2154…`, snapshot `b450c7a6892bf9e3…`, zip
`adf440a38f322674…`).

**The harness** (EXECUTED: `uv run pytest -q -p no:cacheprovider`, no
environment variable set): `wasi_python v1: 88/92 pass · 2 gap · 2
blocked · 0 fail (unit suite 137/137)`; `225 passed, 2 skipped, 2
xfailed`. v1.4 is 32/32. Still blocked: the wheel and the three-systems
check (the release work). Ratchet: lost 0, grew 0, gained 14.

**The review's escapes, shown on the old code and closed** (EXECUTED,
on a scratch copy of the artifact set): with the first build's
placement (a hard link to the artifact zip), a guest's write changed the
artifact zip's hash (`adf440a3…` to `51eaf78d…`), and a symbolic link the
guest left at its zip path made the next call write a file outside the
root. Both scenarios are now checks, and both pass. The real artifact
zip was intact (`adf440a3…`); the 29 hard links earlier scratch runs had
left to it were removed.

**Judge edits, each with its reason.**
- The ten new v1.4 checks of the Design section (eleven with the link
  check's two cases).
- `tests/checks/conftest.py` points `$WASI_PYTHON_CACHE` at
  `build/cwasm-cache/` for the session, so the judge never writes to the
  user's cache.
- `tests/test_api.py`: a source checkout now finds `build/artifacts/`,
  so "a checkout has no artifacts" is no longer true. The test now
  checks the resolution order (the harness's) and the error message,
  with the places patched to temporary directories.
- `tests/unit/test_plugin.py`: its inner sessions used the "runner" need
  as their example of an unmet protected need. With the runner built,
  that need is met, and the plugin rightly failed a check that skipped
  on a met need. The inner sessions now make "runner" unmet with
  `monkeypatch`, so the cases hold whatever the repository provides.
- `tests/harness/paths.py` reads an empty `$WASI_PYTHON_ARTIFACTS` as
  unset, as the runner does.
- `tests/harness/guest.py` (the judge's driver) masks the door's
  addresses to 32 bits, the defect the review found in both doors.
- `tests/harness/scoreboard.py` says how many changed judge files the
  ratchet line leaves out ("and N more"), with a unit test.

**Measured** (EXECUTED: Apple arm64, wall time as a benchmark fact).
- `run(["-c", "pass"])` on the snapshot: the first call in a process
  with an empty cache took 3.1 s (compiling); the first call in a new
  process with the `.cwasm` on disk took 96 ms; later calls in one
  process took 21 to 24 ms (median of five). Each `.cwasm` is about
  105 MB (snapshot), 118 MB (snapshot, fuel metering) and 70 MB (plain).
- Deadlines: `while True: pass` with `deadline_s` 0.3, 1 and 2 trapped
  as `"deadline"` after 0.307, 1.007 and 2.009 s (the first build's
  ticker overshot by about 40%).
- After a deadline trap with fuel given, `store.get_fuel()` reported
  about 2.7 million instructions spent whatever the deadline (0.3 s and
  0.6 s alike): wasmtime does not bring its fuel count up to date on an
  epoch interrupt, so `fuel_used` is `None` then.

**Probed by hand** (EXECUTED): stdin reaches the guest; `-` with argv;
`os._exit(7)` returns 7; `env` is the whole environment; the root holds
only `usr/`; three threads on three roots each get their own output; the
README's example prints `b'6\n'`.

**Departures from the decisions above.**
- The module is `runner.py`, not `run.py`: `wasi_python.run` is the
  function, and a submodule of the same name would be hidden behind it
  (`import wasi_python.run` returned the function).
- The runner frees its cached modules and engines at interpreter exit
  (`atexit`); otherwise wasmtime-py's finalizers ran after its bindings
  were gone and printed an ignored `TypeError` at exit.

**Review.** `../reviews/001-the-neutral-host-door-and-the-runner-2026-10-16.md`:
"does not land yet", then, after the dispositions, "confirmed, lands".
The confirmation's three low findings were closed before acceptance
(the review's author's note).
