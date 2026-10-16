# 003 — The pinned build, end to end, with the neutral door

- **Status:** draft, 2026-10-16; revised the same day to answer the
  specification review
  (`../reviews/003-the-pinned-build-end-to-end-spec-2026-10-16.md`).
- **Owner:** Clay Gendron
- **Kind:** build recipe and guest (`scripts/`, `recipes/`,
  `downloads/SHA256SUMS`, `fixtures/`, `README.md`, judge edits in
  `tests/`). It changes the guest's imports and exports, the artifact
  set and the build recipe, so it was reviewed before build
  (constitution §5.6).
- **Depends on:** 002 (the harness it lands against).
- **Takes over from 001:** the door, the guest module, the reactor,
  the names and the artifact directory. 001 keeps the runner.
- **Research it stands on:**
  `../research/2026-10-16-the-spike-that-proved-the-build.md` (the
  recipe, findings 1 to 9),
  `../research/2026-10-16-the-spike-evidence-in-this-repository.md`
  (the unscripted steps), `../research/2026-10-16-what-the-scripted-build-needs.md`
  (findings 1 to 7, the hash list),
  `../research/2026-10-16-facts-the-build-review-found.md` (the review's
  READ facts and the cloudlibc pin),
  `../research/2026-10-16-a-host-supplied-clock-and-random-make-fuel-exact.md`
  (why seeds are fixed at snapshot time).

## Decisions

### The command and its steps

1. **One command builds everything: `scripts/build.sh`.** It runs the
   steps in order, each a script under `scripts/steps/`, each logging
   to `build/logs/<step>.log` and printing one line, `ok <step>` or
   `ERROR <step>: <last log line>`. `scripts/build.sh <step>…` runs the
   named steps only. It exports `SOURCE_DATE_EPOCH=1767225600`
   (2026-01-01T00:00:00Z, a constant) and `UV_CACHE_DIR=<repository>/build/uv-cache`
   (absolute)
   for every step. Before any step from `20` on runs, it deletes
   `build/artifacts/`, so a failed rebuild never leaves an old set that
   looks current; step `90` writes `build/artifacts.new/` and renames it.
   - `scripts/00_download.sh [--all]` fetches the build pins (and with
     `--all` also the research pins: wasi-sdk 33, Brett's 3.14.7 build)
     from literal URLs into `downloads/` when absent, then runs
     `shasum -a 256 --ignore-missing -c SHA256SUMS`. It never writes
     `SHA256SUMS` and calls no Python. Each pin is a line `get <url>
     <name>`; the name is the file's name in `downloads/` (needed where
     URL basenames collide or are encoded, as `%2B` for `+`).
   - `steps/10_tools.sh` checks that every build pin is present, unpacks
     wasi-sdk 24, Wizer, the wasmtime CLI and the host Python under
     `build/tools/`, copies exactly the pinned build-tool wheels into
     `build/wheelhouse/`, writes `build/tools-requirements.txt` with
     their names, versions and SHA-256s from `SHA256SUMS`, and runs
     `uv pip install --python build/tools/python/bin/python3 --target
     build/tools/pylib --offline --no-index --find-links build/wheelhouse
     --require-hashes -r build/tools-requirements.txt` (`--offline` so a
     user's uv configuration cannot reach the network).
   - `steps/20_cpython.sh`: unpacks CPython 3.14.8 to
     `build/Python-3.14.8/` and runs `Tools/wasm/wasi build` under the
     host Python, with `WASI_SDK_PATH` and the wasmtime CLI on `PATH`.
   - `steps/30_zlib.sh`: configures and builds zlib in
     `build/zlib-build/`, outside its source tree (zlib's configure
     supports it: the review READ it), installing to `build/zlib-wasi/`.
   - `steps/40_numpy.sh`: `meson setup build/numpy-build/` with numpy's
     vendored meson and `recipes/wasi-numpy.cross`; `ninja`; the same
     vendored meson's `install --destdir build/numpy-install` with no tag
     filter (meson 1.12.1 refuses a build directory its vendored 1.11
     made); then
     the host-side numpy stand-in at `build/numpy-host/numpy/`
     (`recipes/numpy_host_shim.py` as `__init__.py`, numpy's
     `__init__.pxd`, `__init__.cython-30.pxd` and `_core/include/` from
     its sdist, plus the three headers the WASI build generates).
   - `steps/50_pandas.sh`: the same for pandas into
     `build/pandas-build/` and `build/pandas-install/`, with no tag
     filter (pandas' `install_subdir` carries no tag, so a tagged
     install leaves out its pure-Python package: the review's finding 2).
   - `steps/60_link.sh`: generates the inittab from both build trees
     into `build/link/inittab.c` (`scripts/gen_inittab.py <out>
     <build dir>…`); writes the build-directory copy of
     `Modules/Setup.local`; copies `hostmodule.c`, `cxa_stubs.c` and
     the generated `inittab.c` into `build/Python-3.14.8/Modules/`
     (makesetup mangles absolute source paths); runs `make`. It then
     compiles `recipes/reactor_main.c` with the target's
     `PY_CORE_CFLAGS` and include paths (read through
     `scripts/python-wasi-cross` and `sysconfig`), takes the link
     command from `make -n python.wasm` after deleting `python.wasm`,
     swaps `Programs/python.o` for the reactor object, adds
     `-mexec-model=reactor`, links `build/out/python.wasm`, and strips
     its DWARF sections (`llvm-strip --strip-debug`; the name section,
     which tracebacks use, stays).
   - `steps/70_zip.sh`: `build/out/python-stdlib.zip` (Decision 7).
   - `steps/80_snapshot.sh`: lays out `build/wizer-root/usr/local/lib/python314.zip`
     (the same bytes as `build/out/python-stdlib.zip`) and runs
     `wizer --allow-wasi --wasm-bulk-memory true --init-func
     wizer.initialize --mapdir /::build/wizer-root -o
     build/out/python-snapshot.wasm build/out/python.wasm`. One preopen,
     at `/`: wasi-libc's preopen table is snapshotted (READ: spike memo
     finding 7).
   - `steps/90_artifacts.sh`: assembles the artifact directory
     (Decision 9). It refuses to run while any file under `recipes/`
     or `scripts/` is untracked by git, so every recipe the build used
     has a `recipe` line.

### Inputs

2. **Every input is pinned.** `downloads/SHA256SUMS` gains the lines of
   the build-needs memo and wasi-libc's
   `libc-bottom-half/cloudlibc/LICENSE` at the same commit
   (`c8b789cf5a746611e6300a0cc7750dbf92b61912a709d04e639245f7290656d0`,
   1,292 bytes; EXECUTED: `curl | shasum -a 256`). The one unpinned host
   input is the native C compiler and `make` that CPython's driver uses
   for its build-Python; `README.md` says so, and the
   reproducible-builds memo tests it.
3. **One host Python runs every host-side step:** python-build-standalone
   CPython 3.14.8 at `build/tools/python/`. `build/tools/pylib/` is on
   `PYTHONPATH` and `build/tools/pylib/bin` first on `PATH`, so meson,
   ninja and cython resolve there; the cross files name
   `@ROOT@/build/tools/pylib/bin/cython`. `scripts/python-wasi-cross`
   (what meson introspects as the target Python) runs the driver's
   native build-Python, found as `cross-build/*/python.exe` or
   `cross-build/*/python` other than the wasm32 one, with
   `build/tools/pylib` on its `PYTHONPATH` (Cython and versioneer for
   pandas' generators: both Pythons are 3.14, one ABI), and, for the
   pandas step only, `build/numpy-host` before it. `.venv-build/` and
   `build/host-pylib/` are gone.
4. **No build writes inside an upstream tree except CPython's own
   driver** (in `cross-build/`, reading `Modules/Setup.local` from
   there) and the three C files of step 60 in `Modules/` (added files).
   zlib, numpy and pandas build outside their trees. The four trees
   then match their tarballs (`test_source_tree_matches_its_tarball`).

### The guest

5. **The door.** `recipes/hostmodule.c` defines the builtin module
   `_host`. It imports `host::call(ptr, len, out_ptr_ptr, out_len_ptr)
   -> i32` and exports `host_alloc(len) -> ptr` (`malloc`; the guest
   frees the response after copying it into a `bytes`).
   `_host.call(frame: bytes) -> bytes` returns the response on 0,
   raises `ConnectionRefusedError` on −1 (no host bound), `OSError` on
   −2 (host fault), and `OSError("host door returned <n>")` on any other
   value. It zeroes the response pointer and length before the call, so
   a host that returns 0 without writing yields `b""`. `_host.available()` is `True` only when the last call returned
   0.
6. **The reactor** (`recipes/reactor_main.c`) exports `_initialize`
   (from the reactor model), `wizer.initialize` and `run`, plus
   `memory` and `host_alloc`.
   - **`wizer.initialize`** initializes with an isolated config,
     `use_hash_seed = 1`, `hash_seed = 0`; pre-imports `encodings, io,
     os, sys, json, csv, re, numpy, pandas`; then, so that the frozen
     state is the same bytes on every build, seeds `random` and
     numpy's global `RandomState` with 0 and sets `logging._startTime`
     to 0; then `gc.freeze()`. A snapshot's hash secret is public in its
     bytes anyway, so a fixed one costs nothing.
   - **The plain reactor** (no `wizer.initialize`) initializes on the
     first `run` with an isolated config and a random hash secret
     (`random_get`, as CPython does).
   - **`run`, once per instance.** A second call prints an error and
     returns 70. On its one call it reads argv and the environment
     through the WASI calls, sets `sys.argv`, replaces `os.environ`'s
     contents (`clear`, then `update`, which also calls `putenv`),
     reseeds `random` and numpy's global `RandomState` from
     `os.urandom` and sets `logging._startTime` to now, each only when
     that module is already imported (so no two calls of one snapshot
     share draws, and the plain reactor imports nothing extra), and
     runs:
     `-c code`; `-m module` (`runpy.run_module(name, run_name="__main__",
     alter_sys=True)`, as CPython's `-m` does);
     a script path; or, with neither, the program on stdin. `-I`, `-u`,
     `-E`, `-s`, `-B` and `-X <opt>` are accepted and ignored (the
     config is already isolated, unbuffered and bytecode-free); `-V` and
     `--version` print the version line of Decision 8; any other flag
     prints `unknown option` and returns 2. The script's directory is
     not put on `sys.path` (isolated mode); the README says so.
     `SystemExit` becomes the return value: its code, 0 for `None`, 1
     after printing a non-integer to stderr (CPython's rule); any other
     uncaught exception prints its traceback and returns 1. Then `run`
     calls `Py_FinalizeEx()`, so `atexit` handlers run and every open
     file is flushed, as a native Python's exit does; if finalization
     fails, `run` returns 120 (CPython's code). Correctness comes first
     (constitution §3): the cost of finalizing some 600 modules is
     measured as fuel and as a benchmark fact in the landing notes, and
     the README's start-up figure is updated to what is measured.
   - **Runaway and memory** are the embedder's: fuel or epochs, store
     limits.
7. **The stdlib zip is bytecode-only, deflated and deterministic.**
   `scripts/make_stdlib_zip.py`, run under the host Python with
   `PYTHONHASHSEED=0`, compiles every `.py` to `.pyc` in process
   (`UNCHECKED_HASH`; the host's 3.14 magic is the guest's), deflates
   every member at level 9, sorts entries, gives each the timestamp
   1980-01-01 00:00 and mode 0644, and leaves out `*.dist-info`. It
   holds the stdlib (`Lib/`, without `ctypes` and the test, IDLE,
   tkinter, turtledemo, ensurepip, venv and `site-packages` trees),
   numpy and pandas from their install trees (without `*.so`,
   `*.so.deps` and `tests` directories), python-dateutil, tzdata and
   six from their pinned wheels, the WASI `_sysconfigdata`, and the two
   stand-ins as `ctypes.py` and `mmap.py`. In `_sysconfigdata` and
   numpy's `__config__.py` the absolute repository path is replaced by
   `/wasi-python-build` before compiling, so the zip carries no
   builder's path. Resource files (tzdata's zone files, dateutil's
   zoneinfo tarball) stay as data members; `importlib.resources` reads
   them through zipimport. A module that needs its own source is a
   finding of the golden jobs.
8. **Platform semantics in `--version`** (constitution §4.11 names
   four: the 32-bit default integer, no threads, the missing modules,
   the speed ratio): the guest's `-V` prints `Python 3.14.8
   (wasm32-wasip1: numpy's default integer is 32-bit; no threads; no
   ctypes, mmap, sockets, ssl, sqlite3, bz2 or lzma; compute about 1.3
   to 2.3 times slower than native)`, and the README carries the same
   sentence. The ratio is the spike's measurement (its finding 8) and
   changes with the next measured one.

### The artifact set

9. **`build/artifacts/`** is the layout 002 reads (its Decision 12):
   `python.wasm` (the plain reactor), `python-snapshot.wasm`,
   `python-stdlib.zip`, `MANIFEST`, `SHA256SUMS`, and
   `LICENSES/<component>.txt`, each its sources concatenated with a
   one-line header naming each:
   - `cpython`: the tarball's `LICENSE`, then `Doc/license.rst`
     (incorporated software: expat, libmpdec, HACL* and the rest);
   - `numpy`: every file its `pyproject.toml` declares in
     `license-files` (`LICENSE.txt` and the bundled notices of
     lapack-lite, pocketfft, the random generators and the rest), in
     that order;
   - `pandas`: the sdist's `LICENSE`, then every file in its
     `LICENSES/`;
   - `zlib`: the tarball's `LICENSE`;
   - `python-dateutil`, `tzdata`, `six`: every licence file in each
     wheel's `.dist-info` (tzdata's `LICENSE_APACHE` included);
   - `wasi-libc`: its five pinned files and cloudlibc's;
   - `llvm-runtimes`: the three pinned LLVM files.

   `MANIFEST`, in this order: `python 3.14.8`; `package` lines for
   `numpy`, `pandas`, `zlib`, `python-dateutil`, `tzdata`, `six`; a
   `pin` line for every download the build read; a `recipe` line for
   every tracked file under `recipes/` and `scripts/` except
   `scripts/bench_*`; `x-wizer` with Wizer's command line;
   `x-preimport` with the pre-import list; `x-snapshot-zip <sha256>`,
   the zip the snapshot was built against. **The snapshot and the zip
   are a pair:** zipimport's directory offsets are frozen in the
   snapshot, so the snapshot runs only beside that exact zip. The
   README says so, and 001's runner always lays out the artifact
   set's own zip.
10. **The harness finds `build/artifacts/` by itself** (this amends 002
    Decision 5, and is a judge edit): the artifact directory is
    `$WASI_PYTHON_ARTIFACTS` when set, else `build/artifacts/` when it
    holds a `MANIFEST`, else the wheel's directory when it does. A
    deleted set after acceptance is red (protected needs); a stale one
    fails the recipe-hash check. A machine without `build/artifacts/`
    runs with `--partial "<why>"`.

### Names, files and the judge

11. **Names.** `recipes/vfsmodule.c` → `hostmodule.c`;
    `recipes/vfs_main.c` → `reactor_main.c`; `recipes/vfs_inittab.c` is
    deleted (generated now); the cross files' `@S12@` token becomes
    `@ROOT@` and their `-include` paths name `recipes/`; the spike's
    numbered scripts are replaced by `scripts/steps/`; no identifier
    carries the embedder's name. `scripts/bench_startup.py` (which
    imports the embedder's shim and cannot run here) and the
    spike-only fixtures (`hello.txt`, `job_numpy.py`, `job_pandas.py`,
    `study04_script.py`, `bench_guest.py`) are deleted from the working
    tree; they stay in this repository's history at commit `e007a58`,
    which the landing notes cite, and no research record is edited.
12. **The README** is this specification's to update: "How it is
    built" (the one command and its steps), the unpinned host compiler,
    the version sentence of Decision 8, the snapshot–zip pair, and the
    script-directory fact of Decision 6.
13. **Judge edits, each with its reason** (accepted with
    `--accept-judge`):
    - the script scans read every file under `scripts/` recursively,
      and the path scan knows `@ROOT@` (otherwise `scripts/steps/`
      would be unread: the review's finding 1);
    - the fetch scan allows a `uv pip install` line only when it has
      `--no-index`, `--require-hashes` and no `http`, and `curl`/`wget`
      only in `00_download.sh`;
    - the literal-URL scan reads `get <url> <name>` lines;
    - the default-integer check's pattern tolerates a line break inside
      "default integer is N-bit" (Markdown wraps; the review's finding 9);
    - a new `rules` check, `test_version_states_the_platform_semantics`,
      runs `-V` on the plain binary and compares with the README;
    - the needs this specification provides name it as provider;
      Decision 10's predicate;
    - the gaps it closes are removed.

## Intent

After this specification the first real artifact set exists, built by
one command from pinned inputs, and the harness judges it: the v1.1 to
v1.4 checks move from `blocked` to `pass` (all but the runner's, the
wheel's and the three-systems check), and six of the eight known gaps
close.

## Design

```
scripts/
  00_download.sh      get <url> <name> lines; shasum --ignore-missing -c
  build.sh            the steps in order; one line each; SOURCE_DATE_EPOCH, UV_CACHE_DIR
  steps/10_tools.sh … 90_artifacts.sh
  python-wasi-cross   host-neutral; pylib and (pandas) numpy-host on its path
  wasi-cc, wasi-cxx   unchanged
  gen_inittab.py      gen_inittab.py <out.c> <build dir>…
  make_stdlib_zip.py  pyc, deflate, deterministic, wheels and stand-ins as inputs
  bench_native.py, bench_native_pandas.py   unchanged
recipes/
  hostmodule.c        _host and host_alloc
  reactor_main.c      wizer.initialize and run
  numpy_host_shim.py  the host-side numpy stand-in (the spike's file)
  cxa_stubs.c, ctypes_stub.py, mmap_stub.py, *_rename.h, *.cross
```

**If a golden job does not match native**, the difference is
investigated before landing. A platform fact of the class §4.11
names is written into the README and the version sentence, and the job
is changed only through a judge edit with that reason. Anything else is
a defect fixed before landing. A defect still open after two attempts
becomes a gap whose closer is a new placeholder memo naming the
difference, and the landing notes say so.

## Scope

In: the above. Out: the runner (001); Linux pins and a Linux run (the
reproducible-builds memo); the release workflow; the CPython 3.15
line; anything the snapshot pre-imports beyond Decision 6.

## Acceptance criteria

1. With `build/` emptied except `build/oracle/`, `scripts/build.sh`
   exits 0, prints ten lines, and leaves `build/artifacts/` with the
   files of Decision 9 (the command, its output and the wall time as a
   benchmark fact in the landing notes).
2. Running steps `60` to `90` again yields byte-identical
   `python.wasm`, `python-snapshot.wasm` and `python-stdlib.zip` (same
   SHA-256).
3. `uv run pytest`, with no environment variable set, is green; every
   v1.1 check is `pass` except `test_wheel_carries_the_artifact_set`
   (blocked: wheel); every v1.2 check `pass` except
   `test_same_bytes_passed_on_three_systems` (blocked); every v1.3
   check `pass`, or a gap under the golden-job rule above; every v1.4
   check `pass` except the three runner checks (blocked: runner); the
   new version check `pass`; `test_source_tree_matches_its_tarball`
   `pass` for all four trees.
4. These six gaps are removed because their checks pass:
   `test_no_embedder_name_in_code`,
   `test_build_scripts_call_python_only_through_uv_or_a_path`,
   `test_download_script_verifies_and_never_writes_the_pins`,
   `test_every_pin_is_fetched_from_a_literal_url`,
   `test_every_repository_path_a_recipe_names_exists`,
   `test_pure_python_packages_are_pinned`. The two that stay keep their
   closers.
5. The run is accepted with `--accept "003" --accept-judge "<the edits
   of Decision 13>"`.
6. `uv run ruff check src tests` and `ruff format --check src tests`
   are clean.

## Landing notes

(Filled in on landing.)
