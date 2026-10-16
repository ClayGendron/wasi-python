# 003 — The pinned build, end to end, with the neutral door

- **Status:** draft, 2026-10-16
- **Owner:** Clay Gendron
- **Kind:** build recipe and guest (`scripts/`, `recipes/`,
  `downloads/SHA256SUMS`, `fixtures/`, judge edits in `tests/`). It
  changes the guest's imports and exports, the artifact set and the
  build recipe, so it is reviewed once before it is built
  (constitution §5.6).
- **Depends on:** 002 (the harness it lands against).
- **Takes over from 001:** its Decisions 1, 2, 4, 6 and 7 (the door,
  the guest module, the reactor's exports, the names, the artifact
  directory). 001 keeps the runner.
- **Research it stands on:**
  `../research/2026-10-16-the-spike-that-proved-the-build.md` (the
  recipe, findings 1 to 9),
  `../research/2026-10-16-the-spike-evidence-in-this-repository.md`
  (the unscripted steps), `../research/2026-10-16-what-the-scripted-build-needs.md`
  (findings 1 to 7, the hash list),
  `../research/2026-10-16-a-host-supplied-clock-and-random-make-fuel-exact.md`
  (why the snapshot's hash seed is fixed).

## Decisions

1. **One command builds everything: `scripts/build.sh`.** It runs the
   steps below in order, each a script under `scripts/steps/`, each
   logging to `build/logs/<step>.log` and printing one line (`ok
   <step>` or `ERROR <step>: <last log line>`). `scripts/build.sh
   <step>…` runs only the named steps. A step's inputs are the outputs
   of earlier steps and the pinned downloads; nothing else.
   - `00_download.sh` (kept at `scripts/00_download.sh`, where the
     harness looks): fetches every pin from a literal URL into
     `downloads/` when absent, then `shasum -a 256 -c SHA256SUMS` over
     all of them; it never writes `SHA256SUMS` and calls no Python.
   - `steps/10_tools.sh`: unpacks wasi-sdk 24, Wizer, the wasmtime CLI
     and the host Python under `build/tools/`, and installs the build
     tools from the downloaded wheels with `uv pip install
     --no-index --find-links downloads --target build/tools/pylib`.
   - `steps/20_cpython.sh`: unpacks CPython 3.14.8 to
     `build/Python-3.14.8/` and runs its own `Tools/wasm/wasi build`
     under the host Python.
   - `steps/30_zlib.sh`: unpacks zlib and configures and builds it in
     `build/zlib-build/`, outside its source tree, installing to
     `build/zlib-wasi/`.
   - `steps/40_numpy.sh`: meson setup in `build/numpy-build/` (outside
     the tree) with numpy's vendored meson and `recipes/wasi-numpy.cross`;
     ninja; `meson install --tags python-runtime` to
     `build/numpy-install/`; then the host-side numpy stand-in for
     pandas' build at `build/numpy-host/` (Decision 6).
   - `steps/50_pandas.sh`: the same for pandas into
     `build/pandas-build/` and `build/pandas-install/`.
   - `steps/60_link.sh`: generates the inittab from both build trees
     into `build/link/inittab.c`, writes the build-directory copy of
     `Modules/Setup.local`, copies the C files makesetup needs into
     `build/Python-3.14.8/Modules/`, runs `make`, then links the
     reactor (`-mexec-model=reactor`, `recipes/reactor_main.c` in place
     of `Programs/python.o`) to `build/out/python.wasm`.
   - `steps/70_zip.sh`: `build/out/python-stdlib.zip` (Decision 7).
   - `steps/80_snapshot.sh`: Wizer → `build/out/python-snapshot.wasm`.
   - `steps/90_artifacts.sh`: assembles `build/artifacts/` (Decision 9).
2. **Every input is pinned.** `downloads/SHA256SUMS` gains the lines in
   the build-needs memo (the host Python, the four build-tool wheels,
   the three pure-Python wheels, the eight licence files). The
   download script names every pin on a line with its literal URL, as
   `get <url> [<local name>]`; the local name is needed where URL
   basenames collide. The one unpinned host input is the native C
   compiler and `make` that CPython's driver uses for its build-Python;
   the README says so, and the reproducible-builds memo tests it.
3. **One host Python runs every host-side step:** python-build-standalone
   CPython 3.14.8 (`build/tools/python/`), with
   `build/tools/pylib/` on `PYTHONPATH` for Cython, meson, ninja and
   versioneer. `scripts/python-wasi-cross` (the target-Python meson
   introspects) keeps using the driver's native build-Python, found by
   globbing `cross-build/*/python.exe` minus the wasm32 one, not by a
   literal host triple. `.venv-build/` and `build/host-pylib/` are
   gone.
4. **No build writes inside an upstream tree except CPython's own
   driver**, which builds in `cross-build/` and reads
   `Modules/Setup.local` from there, and the three C files makesetup
   needs in `Modules/` (added files; makesetup mangles absolute source
   paths, READ: spike memo finding 2). zlib, numpy and pandas build
   outside their trees. The four trees then match their tarballs
   (`test_source_tree_matches_its_tarball`).
5. **The door, as 001 decided it.** `recipes/hostmodule.c` defines the
   builtin module `_host`: it imports `host::call(ptr, len,
   out_ptr_ptr, out_len_ptr) -> i32` and exports `host_alloc(len) ->
   ptr` (`malloc`). `_host.call(frame: bytes) -> bytes` returns the
   response on 0, raises `ConnectionRefusedError` on −1 (no host bound)
   and `OSError` on −2 (host fault); `_host.available()` is `True` only
   when the last call returned 0. `host_alloc`'s memory belongs to the
   guest, which frees it after copying the response.
6. **The reactor** (`recipes/reactor_main.c`) exports `_initialize`
   (from the reactor model), `wizer.initialize` and `run`, and nothing
   else of its own (plus `memory` and `host_alloc`).
   - `wizer.initialize` initializes with an isolated config,
     `use_hash_seed = 1`, `hash_seed = 0` (so the snapshot is the same
     bytes on every rebuild and its fuel repeats), pre-imports
     `encodings, io, os, sys, json, csv, re, numpy, pandas`, and runs
     `gc.freeze()`.
   - `run` initializes lazily when `wizer.initialize` never ran (the
     plain reactor), then reads argv and the environment through the
     WASI calls on every call, sets `sys.argv`, replaces `os.environ`'s
     contents, and runs `-c code`, `-m module` (through `runpy`) or a
     script path; `-I`, `-u` and `-X <opt>` are accepted and ignored
     (the config is isolated and unbuffered output is flushed anyway).
     A `SystemExit` becomes `run`'s return value (its code, 0 for
     `None`, 1 for a non-integer); any other uncaught exception prints
     its traceback and returns 1. `run` flushes `sys.stdout` and
     `sys.stderr` before it returns.
   - The host-side numpy stand-in (`recipes/numpy_host_shim.py`, the
     spike's file brought in) is installed by step 40 next to numpy's
     `__init__.pxd`, `__init__.cython-30.pxd` and `_core/include/`
     (sdist headers plus the three the WASI build generates).
7. **The stdlib zip is bytecode-only, deflated and deterministic.**
   `scripts/make_stdlib_zip.py` compiles every `.py` to `.pyc` in
   process (the host Python's 3.14 magic is the guest's;
   `UNCHECKED_HASH`), deflates every member, sorts entries, and gives
   every entry the timestamp 1980-01-01 00:00. It holds the stdlib
   (`Lib/`, without `ctypes` and the test, IDLE, tkinter, turtledemo,
   ensurepip, venv and `site-packages` trees), numpy and pandas from
   their `meson install` trees, python-dateutil, tzdata and six from
   their pinned wheels, the WASI `_sysconfigdata`, and the two
   stand-ins as `ctypes.py` and `mmap.py`.
8. **Names.** `recipes/vfsmodule.c` → `hostmodule.c`;
   `recipes/vfs_main.c` → `reactor_main.c`; `recipes/vfs_inittab.c` is
   deleted (the inittab is generated into `build/link/`); the spike's
   numbered scripts are replaced by `scripts/steps/`; the inittab
   constructor and every identifier drop the embedder's name.
   `scripts/bench_startup.py`, which imports the embedder's shim, and
   the spike-only fixtures (`hello.txt`, `job_numpy.py`,
   `job_pandas.py`, `study04_script.py`, `bench_guest.py`) move to
   `context/research/2026-10-16-the-spike-that-proved-the-build/`
   as evidence; `fixtures/` keeps `sales.csv`, `hello.c` and
   `throw_probe.cpp`.
9. **The artifact directory** (`build/artifacts/`) is the layout spec
   002 reads (its Decision 12): `python.wasm` (the plain reactor),
   `python-snapshot.wasm`, `python-stdlib.zip`, `MANIFEST`,
   `SHA256SUMS`, and `LICENSES/<component>.txt` — `cpython`, `numpy`,
   `pandas`, `zlib` from their tarballs' top-level licence files;
   `python-dateutil`, `tzdata`, `six` from their wheels' licence files;
   `wasi-libc` and `llvm-runtimes` as the pinned licence files of the
   build-needs memo, concatenated in the memo's order with a one-line
   header naming each. `MANIFEST` has, in this order: `python 3.14.8`;
   `package` lines for `numpy`, `pandas`, `zlib`, `python-dateutil`,
   `tzdata`, `six`; a `pin` line for every download the build read;
   a `recipe` line for every tracked file under `recipes/` and
   `scripts/` except `scripts/bench_*`; `x-wizer` with Wizer's command
   line and `x-preimport` with the pre-import list.
10. **The harness finds `build/artifacts/` by itself** (this amends 002
    Decision 5): the artifact directory is `$WASI_PYTHON_ARTIFACTS`
    when set, else `build/artifacts/` when it holds a `MANIFEST`, else
    the wheel's directory when it does. Deleting `build/artifacts/`
    after its checks are accepted turns the run red (the artifact needs
    are protected), so the default cannot hide a regression.
11. **Judge edits this specification makes, each its own reason:** the
    needs that this specification provides name it as their provider;
    the literal-URL scan reads `get <url> <name>` lines; the
    fetch scan allows `uv pip install` only with `--no-index`; the
    known gaps it closes are removed and the embedder gap with them.

## Intent

After this specification the first real artifact set exists, built by
one command from pinned inputs on this machine, and the harness judges
it: the v1.1 to v1.4 checks move from `blocked` to `pass` (all but the
runner's, the wheel's and the three-systems check), and five of the
eight known gaps close.

## Design

```
scripts/
  00_download.sh      fetch + verify, literal URLs
  build.sh            runs scripts/steps/*.sh in order; one line each
  steps/10_tools.sh … 90_artifacts.sh
  python-wasi-cross   host-neutral
  wasi-cc, wasi-cxx   unchanged
  gen_inittab.py      writes to a path it is given; no embedder name
  make_stdlib_zip.py  pyc, deflate, deterministic, wheels as inputs
  bench_native.py, bench_native_pandas.py   unchanged
recipes/
  hostmodule.c        the door (_host) and host_alloc
  reactor_main.c      wizer.initialize and run
  numpy_host_shim.py  the host-side numpy stand-in (from the spike)
  cxa_stubs.c, ctypes_stub.py, mmap_stub.py, *_rename.h, *.cross   unchanged except paths
```

The cross files' `@S12@` token becomes `@ROOT@`, and their `-include`
paths name `recipes/`.

## Scope

In: the above. Out: the runner and README's "Running it" (001); Linux
pins and a Linux run (the reproducible-builds memo); the release
workflow; the CPython 3.15 line; any change to what the snapshot
pre-imports beyond Decision 6.

## Acceptance criteria

1. From an empty `build/`, `scripts/build.sh` exits 0, prints ten
   lines, and leaves `build/artifacts/` with the files of Decision 9.
   (EXECUTED evidence in the landing notes: the command, its output,
   the wall time as a benchmark fact.)
2. A second `scripts/build.sh` over the first one's `build/` (steps
   rerun from `60_link`) yields byte-identical `python.wasm`,
   `python-snapshot.wasm` and `python-stdlib.zip` (same SHA-256).
3. `uv run pytest`, with no environment variable set, is green and
   shows every v1.1 check `pass` except `test_wheel_carries_the_artifact_set`
   (blocked: wheel); every v1.2 check `pass` except
   `test_same_bytes_passed_on_three_systems` (blocked); every v1.3
   check `pass`; every v1.4 check `pass` except the three runner checks
   (blocked: runner); `test_source_tree_matches_its_tarball` `pass` for
   all four trees.
4. These gaps are removed because their checks pass:
   `test_no_embedder_name_in_code`,
   `test_build_scripts_call_python_only_through_uv_or_a_path`,
   `test_download_script_verifies_and_never_writes_the_pins`,
   `test_every_pin_is_fetched_from_a_literal_url`,
   `test_every_repository_path_a_recipe_names_exists`,
   `test_pure_python_packages_are_pinned`. The two that stay
   (`test_toolchain_is_pinned_for_linux_and_macos`,
   `test_release_workflow_runs_the_zero_patch_check`) keep their
   closers.
5. The run is accepted with `--accept "003" --accept-judge "<the judge
   edits of Decision 11>"`, protecting the new passes and their fuel
   and bytes.
6. `uv run ruff check src tests` and `ruff format --check src tests`
   are clean.

## Landing notes

(Filled in on landing.)
