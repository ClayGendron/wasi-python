# Review of 003 — The pinned build, end to end, with the neutral door

- **Date:** 2026-10-16
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I was
  given the constitution, `AGENTS.md`, `context/README.md`, the review
  template, specifications 001 (as amended), 002 and 003, the four
  research memos 003 stands on with the spike's evidence directory,
  the harness code (`tests/harness/`, `tests/checks/`), the known gaps,
  and the current `scripts/`, `recipes/`, `downloads/SHA256SUMS`,
  `fixtures/` and `README.md`. I did not rely on the author's summary.
- **Reviewed:** the specification as drafted
  (`context/specifications/003-the-pinned-build-end-to-end.md`, 232
  lines), with the amended
  `context/specifications/001-the-neutral-host-door-and-the-runner.md`
  (90 lines), at HEAD `e007a58`.
- **Re-ran (EXECUTED, this machine, darwin-arm64):**
  - `uv run pytest -q -p no:cacheprovider` → `wasi_python v1: 14/67 pass ·
    8 gap · 45 blocked · 0 fail (unit suite 133/133)`; `147 passed, 45
    skipped, 8 xfailed`; ratchet `lost 0 · absent 0 · unrun 0 · gained 0 ·
    grew 0`; exit 0.
  - `build/oracle/venv/bin/python -I -c "import encodings, io, os, json,
    csv, re, numpy, pandas; …"` (native numpy 2.5.2 and pandas 3.0.6, the
    oracle's pins) → `random True`, `numpy.random.mtrand True`,
    `logging True`, `uuid True`, `secrets True`, `inspect True`,
    `zoneinfo True`, `tempfile False`; 597 modules. These are the modules
    the snapshot's pre-import will also load.
  - `uv run python -c "re.findall(r'default integer is (\d+)-bit',
    README)"` → `[]`; with `\s+` between the words → `['32']`. The
    README's phrase is split across a line break.
  - `date -u -r 1792034199` → `Thu Oct 15 03:16:39 UTC 2026`: the
    `SOURCE_DATE_EPOCH` the spike's driver logged is a commit time of the
    repository the spike ran in. `git log -1 --format=%ct` here →
    `1792178016`.
  - `grep -n getbuildinfo …/outputs/20_make_pandas.log` → line 616: the
    spike's relink after rewriting `Setup.local` recompiled
    `Modules/getbuildinfo.o`.
  - `grep -a -o '/home/[…]*' build/brett-3.14.7/python.wasm` →
    `/home/runner/work/cpython-wasi-build/cpython-wasi-build/cross-build/wasm32-wasip1`;
    the binary has a `.debug_info` section. A build by the same driver
    embeds its build directory.
  - `find build/oracle/venv/…/site-packages/*.dist-info -iname '*licen*'`
    → numpy's wheel carries eleven bundled licence files
    (`linalg/lapack_lite/LICENSE.txt`, `fft/pocketfft/LICENSE.md`,
    `random/src/mt19937/LICENSE.md`, `random/LICENSE.md`,
    `_core/src/multiarray/dragon4_LICENSE.txt`,
    `_core/include/numpy/libdivide/LICENSE.txt`, …); tzdata's wheel has
    `licenses/LICENSE` and `licenses/licenses/LICENSE_APACHE`.
  - `tar xzOf downloads/zlib-1.3.1.tar.gz zlib-1.3.1/configure` → lines
    22–30 support an out-of-tree build (`SRCDIR`); lines 268–275 still
    pick Apple `libtool` as the archiver on a Darwin host.
  - READ: `tests/checks/test_v1_5_rebuild_from_pins.py:17-18,35-43`,
    `tests/checks/test_rules.py:76-79` (the script scans list only the
    top level of `scripts/`); `tests/harness/scan.py:112,164-165`;
    `tests/harness/paths.py:73-80`; `tests/harness/guest.py`;
    `recipes/*.cross` (`cython = '@S12@/.venv-build/bin/cython'`);
    `scripts/*` (the spike's); `context/prior_art/pandas/pandas/meson.build`
    at `3ce0a8c` (`install_subdir(...)` with no `install_tag`);
    `context/prior_art/cpython/Tools/wasm/wasi/__main__.py:63-79`
    (`SOURCE_DATE_EPOCH` from `git log -1 --pretty=%ct`) and `:155-166`
    (`python` or `python.exe`); `build/brett-3.14.7/lib/python3.14/zipimport.py:95,269-272`
    (the directory cache, never invalidated by a stat),
    `random.py:941` (`_inst = Random()`), `logging/__init__.py:59`
    (`_startTime = time.time_ns()`);
    `build/oracle/…/pandas/_typing.py:200-202` (`np.random.RandomState`
    evaluated at import); `context/prior_art/wizer/tests/tests.rs:577-650`
    (Wizer calls `_initialize` before the init function and un-exports
    it; a call to an undefined import during init fails the wizening).

## Acceptance criteria against evidence

1. *From an empty `build/`, `scripts/build.sh` exits 0, prints ten
   lines, leaves the files of Decision 9* — checkable. As drafted it is
   **not reachable**: the pandas install tree lacks pandas' pure-Python
   package (finding 2). It also conflicts with criterion 3: an empty
   `build/` deletes `build/oracle/`, so the accepted oracle check turns
   `blocked`, and criterion 3 demands every v1.3 check `pass` (finding 9).
2. *A second run from `60_link` yields byte-identical `python.wasm`,
   snapshot and zip* — checkable, and **expected to fail on all three**
   (finding 4). It is also weak where it holds: a relink over the same
   objects says nothing about whether compiling from source repeats.
   It should be stated as "the same SHA-256 from two full builds", or
   kept as is and renamed for what it proves.
3. *`uv run pytest` green, every v1.1–v1.4 check `pass` but the named
   ones* — checkable and the right bar. **Not reachable as scoped**:
   `test_default_integer_width_is_documented` fails on the current
   README (EXECUTED above) and no specification owns the README edit
   (finding 9). Worse, three of the checks it counts would pass
   **vacuously** because the scans cannot see `scripts/steps/`
   (finding 1). Insufficient on one point: it never runs the suite a
   second time, so the 0.01% fuel tolerance on the 55–94 MB binaries,
   which the clock memo explicitly leaves open, is never tested before
   the fuel is protected. Add: a second `uv run pytest` after
   acceptance is green.
   Achievability of the parts asked about. The golden jobs plausibly
   match native: every float is rounded to nine digits, integer draws
   name `int64`, the legacy `binomial`, `poisson` and `multinomial`
   values are small enough for a 32-bit `long`, and the spike's pandas
   job matched native "to the millidigit" (INFERRED). The default-integer
   check will see `32` (numpy 2's `int_` is `intp`). The snapshot fuel
   ratio holds easily: `import pandas` in the snapshot is a dictionary
   hit. What the spec does not decide is the path when a job does
   **not** match. It should say: a mismatch is a red run; the build is
   fixed, or a gap is written with its exact digest and a closer memo;
   an `.expected` file is never edited.
4. *Six gaps removed because their checks pass* — checkable. But the
   Intent says "five of the eight known gaps close" (`003:167`) while
   this criterion lists six. And three of the six would "pass" only
   because the checks stop looking (finding 1).
5. *Accepted with `--accept "003" --accept-judge …`* — checkable.
   Sufficient once criterion 3 is sound.
6. *ruff clean* — checkable, sufficient.

## Findings, most severe first

1. **The judge goes blind to the build it is meant to judge**
   (`003:25-60`, `003:155-159`, `003:188-189`;
   `tests/checks/test_v1_5_rebuild_from_pins.py:17-18`,
   `tests/checks/test_rules.py:76-79`, `tests/harness/scan.py:164-165`)
   — the three script scans read only the top level of `scripts/`, and
   the path scan only knows `$HERE`, `${HERE}` and `@S12@`, so moving
   every step to `scripts/steps/` and renaming the token to `@ROOT@`
   makes them pass on nothing. Decision 11 lists neither change.
   Failure: `steps/10_tools.sh` runs `uv pip install` (or a later edit
   adds `curl https://…`, or a bare `python3`, or names a recipe file
   that does not exist). `test_no_build_script_fetches_outside_the_download_script`,
   `test_build_scripts_call_python_only_through_uv_or_a_path` and
   `test_every_repository_path_a_recipe_names_exists` all pass, because
   `_scripts()` is `SCRIPTS.iterdir()` and `scripts/steps` is a
   directory, and because `@ROOT@/recipes/…` matches no token. The two
   gaps are "removed because their checks pass" (criterion 4) and the
   passes are protected. This is the false green the 002 reviews were
   written to prevent. Fix, as judge edits Decision 11 names: scan
   `scripts/` recursively (the same file set `recipe_files()` already
   uses); add `@ROOT@` and whatever root variable the new scripts use to
   `PATH_TOKEN`; drop `.venv-build` from `GENERATED_ROOTS`; and add a
   self-test that a fetch, a bare `python3` and a missing path inside
   `scripts/steps/` are each found.

2. **pandas installed with `--tags python-runtime` has no pure-Python
   package** (`003:45-51`, `003:114-123`) — pandas installs its
   sub-packages with `install_subdir(...)` and no `install_tag`
   (READ: `context/prior_art/pandas/pandas/meson.build` at `3ce0a8c`),
   and meson does not install untagged files when `--tags` is given.
   Failure: step 50 runs "the same" `meson install --tags
   python-runtime`; `build/pandas-install/` holds the four top-level
   `.py` files, `_libs`' stubs and `_version_meson.py` but no
   `pandas/core`, `pandas/io`, `pandas/_config`…; the zip carries them
   into the guest; `import pandas` raises `ModuleNotFoundError: No
   module named 'pandas._config'` and every pandas check fails. This is
   what the spike saw: its `pandas-install/` was 536 KB, so it zipped
   pandas' whole tree from the sdist (`pandas-py/`, 8.8 MB) instead
   (EXECUTED inventory, `…/build-tree-inventory.txt`; the evidence memo,
   unscripted step 3). Decide one of: install pandas without `--tags`
   and let the zip step drop `tests/`; or take the pure tree from the
   sdist as the spike did (its `_version.py` gives `3.0.6`). Say which
   files the zip step drops from the numpy and pandas trees too (`.so`
   archives, `.a`, `.pc`, `conftest.py`, `tests/`): Decision 7 lists
   exclusions only for `Lib/`.

3. **Every snapshot run draws the same "random" numbers**
   (`003:95-99`) — the pre-import runs inside Wizer, whose WASI answers
   `random_get` and `clock_time_get` for real, and the state those
   answers seed is frozen into the snapshot.
   Failure: `import pandas` imports `random` (EXECUTED above), whose
   module-level `_inst = Random()` (READ: `random.py:941`) seeds from
   `os.urandom` at Wizer time; `pandas/_typing.py:200-202` touches
   `np.random.RandomState`, which imports `numpy.random.mtrand` and
   seeds its global `RandomState` the same way. Every guest started from
   one published snapshot then prints the same `random.random()`,
   `random.choice(...)` and `np.random.rand()` sequence, on every
   embedder, forever. A hash secret shared by all downloads (Decision 6's
   reasoning) is a known trade; a shared random stream is a silent
   correctness and security defect: any program that seeds nothing gets
   identical "random" output, and anything built on `random` (shuffles,
   sampling, `tempfile`-style names made from it) is predictable. Fix:
   decide it in Decision 6. For example: `wizer.initialize` ends with
   `random.seed(0)`, `numpy.random.seed(0)` and a fixed
   `logging._startTime`, so the snapshot's bytes are fixed; and `run`,
   on its first call in a snapshot, reseeds both from `random_get` and
   resets `logging._startTime`. Under the judge's driver that reseed is
   deterministic, so fuel still repeats. Add a check (or a line in an
   existing one): two snapshot runs under the real runner give different
   `random.random()`.

4. **Criterion 2 cannot hold: three sources of change are not
   controlled** (`003:200-206`, `003:39-41`, `003:52-57`, `003:114-118`).
   - *Build time in `python.wasm`.* `Modules/getbuildinfo.c` bakes
     `__DATE__ __TIME__` into `sys.version`, and make rebuilds it on
     every relink (EXECUTED: `20_make_pandas.log:616`). Step 60 runs
     `make` itself, outside the driver, so `SOURCE_DATE_EPOCH` is unset
     and clang uses the clock. Failure: two runs of `60_link` a minute
     apart give two `python.wasm` hashes, and two snapshots.
   - *The driver's epoch is this repository's last commit.* The driver
     sets `SOURCE_DATE_EPOCH` from `git log -1 --pretty=%ct` in its
     working directory (READ: `Tools/wasm/wasi/__main__.py:69-76`), and
     `build/Python-3.14.8` sits inside this git worktree. EXECUTED: the
     spike's logged epoch is a commit time of the repository it ran in.
     Failure: committing the landing notes changes `sys.version` and
     every artifact hash; git becomes an unpinned build input; and the
     Linux CI build of the same pins gets a different epoch.
   - *Wizer-time state in the snapshot.* Finding 3's seeds, and
     `logging._startTime = time.time_ns()` (READ: `logging/__init__.py:59`),
     are written at Wizer time from real entropy and the real clock.
     Failure: two Wizer runs over the same `python.wasm` differ in those
     bytes.
   - *The zip* (INFERRED): marshal writes a `frozenset` constant in
     iteration order, which depends on the compiling process's string
     hash seed; Decision 7 compiles in process under a random seed.
     Failure: a module with `x in {"a", "b"}` compiles to different bytes
     on two runs.
   Fix: one fixed `SOURCE_DATE_EPOCH` exported by `build.sh` for every
   step (from a pin, for instance the CPython release date), recorded in
   `MANIFEST`; finding 3's fixed seeds in `wizer.initialize`;
   `PYTHONHASHSEED=0` for the zip step; and a procedure for when the
   hashes still differ (build twice, `cmp -l` or `wasm-objdump -s`, find
   the field).

5. **The snapshot is bound to the exact zip bytes, and nothing says
   so** (`003:58-60`, `003:135-148`; 001 Decision 3) — the snapshot
   holds zipimport's directory cache for `/usr/local/lib/python314.zip`
   (file offsets read at Wizer time), and zipimport never re-reads it
   (READ: `zipimport.py:95,269-272`).
   Failure: an embedder upgrades `python-snapshot.wasm` but its root
   still holds the previous release's `python314.zip`. 001's runner lays
   the zip out only "when it is not there", so it keeps the old one.
   Every module not pre-imported is read at the old offsets: `bad local
   file header`, or wrong bytes unmarshalled. The same holds for a zip
   rebuilt after the snapshot. Two related contract facts are also
   left unstated: the snapshot bakes wasi-libc's preopen table, so it
   works only with exactly one preopen at `/` (spike finding 7); and a
   Wizer command line is not decided at all (Decision 1 says only
   "Wizer → snapshot"; the spike's `--allow-wasi --wasm-bulk-memory true
   --init-func wizer.initialize --mapdir /::<root>` is the evidence).
   Fix: decide the Wizer command in 003; make step 80 wizen over the
   very file step 90 publishes; write `x-snapshot-zip <sha256>` in
   `MANIFEST`; have 001's runner place the zip whenever its hash differs;
   say both facts in the guest contract and the README.

6. **The host-tool wiring is under-specified, and two pieces of it are
   wrong** (`003:35-38`, `003:69-76`, `003:110-113`, `003:188-189`).
   - `uv pip install --target` without `--python` lets uv pick an
     interpreter. It decides the wheel tags (the only Cython wheel pinned
     is `cp314-…-macosx_11_0_arm64`) and the shebang of the
     `bin/cython` and `bin/ninja` scripts it writes. Failure: uv
     selects the repository's `.venv` Python or a system 3.13; the
     install fails, or Cython runs under an unpinned interpreter.
   - No `UV_CACHE_DIR`: uv unpacks the wheels into `~/.cache/uv`,
     outside `downloads/` and `build/` (constitution §4.8; 002 sets it
     for the oracle for exactly this reason).
   - `--find-links downloads` resolves from whatever is in `downloads/`,
     which is git-ignored and may hold stray, unverified wheels. Name the
     pinned wheel files by path.
   - `PYTHONPATH` makes `meson` importable, but meson finds `ninja`, and
     numpy's and pandas' builds find `cython`, through `PATH` or the
     cross file. The cross files still say
     `cython = '@S12@/.venv-build/bin/cython'`, and "`@S12@` becomes
     `@ROOT@`" does not change that; `.venv-build` is gone.
   - Decision 3 removes `build/host-pylib/` without saying what replaces
     it on the native build-Python's path. pandas' `generate_pxi.py` runs
     under `python-wasi-cross` and needs `Cython.Tempita`. Cython needs
     `build/numpy-host` on its path to find `numpy/__init__.pxd`; the
     spike exported `PYTHONPATH=build/numpy-host-shim` for the whole
     pandas step (`scripts/07_pandas_build.sh`).
   - "globbing `cross-build/*/python.exe`" is macOS-only. On a
     case-sensitive filesystem the build-Python is `python` (READ: the
     driver's `build_python_path()`), so the stated host neutrality is
     false.
   - The spike took the reactor's compile flags and link line from a log
     line of a `make` that compiled `Modules/_json.o` and linked
     `python.wasm` (`scripts/08_build_vfsmain.sh`). A rerun's `make`
     prints neither, which is exactly criterion 2's case. Say where the
     flags come from (Makefile variables, or the first run's saved log).
   Fix: unpack the four tool wheels with the pinned interpreter
   (`build/tools/python/bin/python3 -m zipfile -e <wheel> build/tools/pylib`)
   instead of `uv pip`. Name `cython` in the cross files as
   `['@ROOT@/build/tools/python/bin/python3', '-m', 'cython']` and
   `ninja` by its path. State the `PATH` and `PYTHONPATH` of each step
   in one table. This also removes the need for Decision 11's
   fetch-scan relaxation (finding 7).

7. **Decision 11's `uv pip install --no-index` allowance weakens the
   fetch scan** (`003:157-158`; `tests/harness/scan.py:112`).
   `--no-index` stops index lookups only. Failure: `uv pip install
   --no-index --find-links https://example.org/wheels/ cython` or a
   requirement written as `pkg @ https://…` still fetches, and the
   edited scan accepts the line. If the allowance stays, it must also
   require `--offline` and reject any `://` on the line. Better, drop it
   (finding 6). The other Decision 11 edits do not weaken the judge.
   Moving needs to 003 is bookkeeping. Accepting `get <url> <name>`
   lines is safe, because the hash check still guards the bytes. And a
   gap is removed only when its check really passes, once finding 1 is
   fixed. Decision 10's change to the `artifact dir` predicate is also a
   judge change, and Decision 11 should list it.

8. **Licence notices omit what the binary actually links** (`003:135-143`;
   constitution §4.12). 003 copies only each tarball's top-level licence
   file. Failure: `python.wasm` statically contains numpy's lapack-lite,
   pocketfft, the mt19937 and PCG generators, dragon4 and libdivide,
   each with its own notice (EXECUTED: the eleven files in numpy's
   wheel above). It also contains pandas' vendored code (its `LICENSES/`
   directory), CPython's bundled libraries (expat, libmpdec, HACL\*,
   …) and wasi-libc's cloudlibc. None of those notices reaches
   `LICENSES/`. The artifact set this spec produces is what the wheel
   will carry, and BSD and MIT terms require the notice in a binary
   redistribution. 002 Decision 17 deferred "bundled sub-licences" to a
   release specification that does not exist. The harness's rule is
   "contains", so appending the bundled files to each component's
   notice costs nothing. Fix: decide it here (append the bundled licence
   files each sdist ships, plus wasi-libc's cloudlibc notice, pinned like
   the others), or name the document that will and what it must add.
   For tzdata, include `LICENSE_APACHE` beside `LICENSE`.

9. **Criterion 3 depends on a README edit nobody owns, and criterion 1
   deletes the oracle** (`003:193-196`, `003:200-213`; `README.md:43-46`;
   `tests/checks/test_v1_3_data_stack.py:83-88`).
   Failure: `test_default_integer_width_is_documented` searches for
   `default integer is (\d+)-bit` on one line; the README says
   "numpy's default\ninteger is 32-bit" across a line break, so it finds
   nothing (EXECUTED) and the check fails. 003's scope leaves the README
   to 001, and 001 owns only "Running it". The README's "How it is
   built" section also names `02_build_cpython_floor.sh`,
   `08_build_vfsmain.sh` and the other scripts 003 deletes, and nobody
   is assigned to update it. Separately, "from an empty `build/`" removes
   `build/oracle/` (and `build/brett-3.14.7/`), so the accepted
   `test_goldens_reproduce_under_the_pinned_oracle` becomes `blocked`
   and criterion 3's "every v1.3 check `pass`" fails unless the oracle
   is rebuilt online first. Fix: put the README's build section and the
   one-line default-integer sentence in 003's scope; and say "with no
   build output under `build/` (the oracle and the reference build kept)"
   or add the oracle rebuild to the procedure.

10. **The guest's `--version` does not carry the platform semantics
    the constitution requires** (`003:100-109`; constitution §4.11) —
    `run` handles `-c`, `-m`, a script path, `-I`, `-u` and `-X`, and
    nothing else is decided.
    Failure: an embedder runs `["--version"]` (or `-V`). It is not a
    flag `run` accepts, so it is treated as a script path or fails. §4.11
    says the 32-bit default integer, the missing threads, the missing
    modules and the speed ratio are "stated in the README and in
    `python3 --version`". This specification defines the guest's
    argument handling, so this is its decision. Fix: decide what
    `--version` prints (for instance `Python 3.14.8 (wasm32-wasip1;
    default integer 32-bit; no threads; …)`) and add a check for it.

11. **`run`'s semantics leave several choices open** (`003:100-109`,
    `003:84-91`; constitution §5.2).
    - No finalization. CPython's exit path runs `atexit` handlers and
      flushes open files; `run` returns with the interpreter alive.
      Failure: `f = open('/out/x.csv', 'w'); f.write('a,b\n')` at module
      level, with no close: native Python writes the file; the guest
      leaves it empty, because the instance is dropped with the data in
      `f`'s buffer. Decide: run `atexit` handlers, collect `__main__`,
      or document it.
    - The plain reactor's lazy-init config is not stated. Old 001
      Decision 4 kept a random hash secret on the plain path; 003
      dropped the sentence without a decision.
    - Not decided: no program argument (stdin, as the spike did, or an
      error); unknown flags (`-B`, `-E`, `-O`, `-W …`: CPython exits 2 on
      an unknown flag); `sys.exit("message")` (CPython prints the message
      to stderr); door return codes other than 0, −1 and −2; a host that
      called `host_alloc` and then returned −2 (who frees it); whether
      `run` may be called twice on one instance.
    - Two platform facts follow from the isolated config and should be
      documented. A script's directory is not on `sys.path`
      (`safe_path`), so `import sibling` fails where native Python works.
      And `os.environ` must be replaced through `putenv`/`unsetenv`, so
      C-level `getenv` (for example `TZ` with `time.tzset`) sees the same
      environment.

12. **The deterministic zip and the binaries leak the builder's paths**
    (`003:114-123`). Decision 7 puts the WASI `_sysconfigdata` into the
    zip; it holds absolute build paths (`CC`, `abs_builddir`, …). numpy's
    generated `__config__.py` records the compiler and Python paths. And
    the driver compiles with `-g`, so `python.wasm` carries DWARF with
    the build directory (EXECUTED: Brett's build embeds
    `/home/runner/work/…`).
    Failure: the published artifacts contain
    `/Users/<owner>/Git/Repos/wasi_python/build/…`, and two checkouts at
    different paths, or the Linux CI host, can never produce the same
    hash. Fix: decide now whether to strip debug sections (a link flag is
    a recipe change) and normalise the generated files, or leave both to
    the reproducible-builds memo and say so. Also fix each zip entry's
    `external_attr` and compression level. And decide whether
    `.dist-info` directories ship: without them,
    `importlib.metadata.version("pandas")` and `pandas.show_versions()`
    fail in the guest.

13. **A failed rebuild leaves a stale set that the new default judges as
    current** (`003:149-154`). With Decision 10, `build/artifacts/` is
    read whenever it holds a `MANIFEST`.
    Failure: a rebuild after an environmental failure (disk full, a
    killed Wizer) stops at step 80 and leaves the previous complete set
    in place. The recipe hashes still match, because no recipe changed.
    `uv run pytest` is green against binaries the current build did not
    produce. Fix: `build.sh` removes `build/artifacts/` before its first
    step, and step 90 writes into a temporary directory and renames it
    into place. Otherwise Decision 10 is sound (see Q4 under
    Constitution checks).

14. **Pins and recipe lines need two procedural decisions**
    (`003:31-34`, `003:61-68`, `003:144-147`).
    - The literal-URL check covers every pinned name. So once its gap is
      removed, `00_download.sh` must also fetch wasi-sdk 33 (pinned for
      the spike's exception probe) and Brett's zip (the harness's
      reference build) on every fresh build. The other choice is to
      unpin them, which breaks the 3.15 memo's and the self-tests'
      inputs. Decide which.
    - The python-build-standalone asset name contains `+`, which its
      release URL encodes as `%2B`. The basename then does not equal the
      pinned name, so use the `get <url> <name>` form for it.
    - `recipe` lines cover *tracked* files (`git ls-files`), but the new
      `scripts/steps/*` files are untracked until committed. A build
      before `git add` writes a `MANIFEST` without them, and the first
      commit makes the artifact stale. Say: stage the new files (not a
      commit) before the landing build.

15. **Moving fixtures into the spike's research directory edits a
    research record** (`003:124-134`). `context/README.md` says research
    is never edited after the fact, and
    `2026-10-16-the-spike-evidence-in-this-repository.md` records
    `fixtures/*` → `fixtures/` (byte-identical). Moving five fixtures and
    `scripts/bench_startup.py` into
    `2026-10-16-the-spike-that-proved-the-build/` makes that table
    false. Fix: record the move in a short new memo (or in 003's landing
    notes, cited from the evidence memo's successor).

## Constitution checks

- §4.1 zero patches: **holds by design.** zlib, numpy and pandas build
  outside their trees (zlib's `configure` supports it: READ lines
  22–30). CPython's driver adds only `Modules/Setup.local`, `cross-build/`,
  `__pycache__/` and the three copied C files, none of which is in the
  tarball. numpy's vendored meson writes `__pycache__/` into its own
  source directory; that is an added file, not judged. Finding 1 must be
  fixed so the build scripts themselves stay judged.
- §4.2 every input pinned: **partly.** The new pins are right (the
  build-needs memo's list). Unpinned inputs beyond the C compiler and
  `make` that Decision 2 names: `git` (the driver's
  `SOURCE_DATE_EPOCH`, finding 4); uv's version (if `uv pip` stays);
  host `pkg-config` (the WASI `configure` found `/opt/homebrew/bin/pkg-config`,
  EXECUTED in the spike's log); `curl`, `tar`, `xz`, `shasum`.
  "Verified before use" is weakened by `--find-links downloads`
  (finding 6) and by `build.sh <step>` runs that skip the hash check.
- §4.3 one target: holds. The two host Pythons are build tools only.
- §4.4 two-import wall: **holds.** `host::call` is the only custom
  import, and `host_alloc` is an export. Wizer keeps imports and fails a
  wizening that calls an undefined import (READ: Wizer tests), so no
  pre-import can reach the door.
- §4.5 embedder-neutral: holds after Decision 8's renames. Every current
  hit (11 files) is renamed, deleted or moved out of the scanned
  directories. 001's README "Running it" still says "for vfs, the
  filesystem verbs"; the README is not scanned, but §4.5 covers
  defaults and docs in spirit.
- §4.6 the artifact set: names and layout match 002 Decision 12. The
  snapshot and zip are an inseparable pair; say so (finding 5).
- §4.8 downloads untrusted: **violated as drafted** by uv's default
  cache in the home directory (finding 6).
- §4.11 platform semantics: **not met** for `python3 --version`
  (finding 10), and the README sentence the check reads is not owned
  (finding 9).
- §4.12 licence compliance: **not met** for bundled third-party code
  linked into the binary (finding 8).
- §4.13 uv only: the build calls the pinned interpreter by path, which
  the rule and its check allow.
- §5.2 no open questions: **not met.** Undecided: the Wizer command
  line, the plain path's hash seed, `run`'s handling of stdin, unknown
  flags, `--version` and finalization, the pandas install tags,
  `SOURCE_DATE_EPOCH`, the fate of the wasi-sdk 33 and Brett pins,
  `.dist-info` in the zip, and the path when a golden job mismatches
  (findings 2, 4, 5, 10, 11, 12, 14; criterion 3).
- §5.6 review before build: this record.
- §6: the RNG choice (finding 3) is a case of §6.3 (the same on every
  host) and §6.5: a sealed Python that hands every user the same random
  numbers would not be recognised as this project.
- §7 never-do list: nothing is tripped by the text. A build following
  Decision 1 would install downloads into the user's uv cache (§7,
  "install a download into the system", in spirit), and the Decision 11
  relaxation would let a later edit fetch unpinned bytes unseen
  (findings 6, 7, 1).
- Q4, Decision 10 (amending 002 Decision 5): **sound in principle.** A
  landed specification is a record; changing the judge through a new
  specification with `--accept-judge` is the process 002 itself
  defines. It does not reopen the false green the 002 review closed
  (finding 1 there). `$WASI_PYTHON_ARTIFACTS` still means "that path and
  nothing else". A set missing a file still fails
  `test_artifact_set_is_complete`. A deleted set turns accepted passes
  `unrun`, which is red. A stale set from another build fails
  `test_manifest_recipes_match_the_tree` whenever a recipe changed. The
  residual is finding 13. One consequence to state in the landing
  notes: after 003 is accepted, every clone or machine without
  `build/artifacts/` is red without `--partial`. That is intended
  (AGENTS.md, rule 6), but it is new for this repository.
- Q6, the split between 003 and 001: consistent on the import, the
  exports, the door codes and the dispatch. Lost or contradictory:
  (a) old 001 Decision 4's "the plain reactor keeps a secret from
  `random_get`" is in neither specification (finding 11); (b) 001's
  runner places the zip "when it is not there", which is unsafe against
  a snapshot (finding 5); (c) 001 says "the plain wasmtime CLI cannot
  instantiate the binary", but the CLI can with
  `-W unknown-imports-trap=y` or `-W unknown-imports-default=y`, and
  with the latter `host::call` returns 0, so `_host.call` reports an
  answer that never came. 001's README text should say that, and the
  guest should zero `out_ptr`/`out_len` before the call so a bogus 0
  yields `b''`, not a read of stale memory. (d) No specification owns
  README "How it is built" (finding 9).

## Disposition (filled in by the author, then confirmed by the reviewer)

By the author, 2026-10-16, in the revised specification (and 001
where named). Decision numbers are the revision's.

1. Judge blind to `scripts/steps/` — **fixed** (Decision 13): the
   script scans recurse and the path scan knows `@ROOT@`; listed as
   judge edits.
2. pandas' tagged install — **fixed** (Decision 1, steps 40 and 50):
   `meson install` with no tag filter; the zip step drops `*.so`,
   `*.so.deps` and `tests` (Decision 7).
3. Frozen random state — **fixed** (Decision 6): `wizer.initialize`
   seeds `random` and numpy's global `RandomState` with 0 and zeroes
   `logging._startTime` after the pre-imports (same frozen bytes every
   build); every `run` reseeds both from `os.urandom` and resets
   `_startTime`, so no two calls share draws.
4. Criterion 2 — **fixed** at each named source: `SOURCE_DATE_EPOCH` is
   a constant exported by `build.sh` to every step (Decision 1); the
   zip compiles under `PYTHONHASHSEED=0` (Decision 7); the frozen seeds
   and `_startTime` are fixed (Decision 6); DWARF is stripped (step 60).
   The criterion stays as written; if a byte still differs, the build
   does not land until the source is found (the two-strikes rule of
   AGENTS.md applies).
5. Snapshot bound to its zip — **fixed**: the pair is stated (Decision
   9), `MANIFEST` carries `x-snapshot-zip`, the Wizer command and the
   single `/` preopen are decided (step 80), the README states it
   (Decision 12), and 001's runner always writes the set's own zip.
6. Host-tool wiring — **fixed** (Decisions 1 and 3): `uv pip
   --python … --target … --no-index --find-links build/wheelhouse
   --require-hashes -r build/tools-requirements.txt` with only the
   pinned wheels in the wheelhouse and `UV_CACHE_DIR` under `build/`;
   `PATH` and `PYTHONPATH` stated; the cross files name
   `build/tools/pylib/bin/cython`; the build-Python found by a
   host-neutral glob; the reactor's flags from the target `sysconfig`
   and its link line from `make -n python.wasm`, not from a log.
7. The `uv pip` allowance — **narrowed** (Decision 13): only with
   `--no-index`, `--require-hashes` and no `http`; Decision 10's
   predicate change is listed as a judge edit.
8. Licence notices — **fixed** (Decision 9): CPython adds
   `Doc/license.rst`; pandas adds its `LICENSES/` (13 files, READ);
   wasi-libc adds cloudlibc's licence, now pinned (`c8b789cf…`, 1,292
   bytes, EXECUTED). numpy's sdist carries one `LICENSE.txt` (READ: the
   spike's numpy tree), which is used whole.
9. README regex, README ownership, the oracle, five vs six — **fixed**:
   the check's pattern tolerates a line break (judge edit, Decision
   13); README updates belong to this specification (Decision 12);
   criterion 1 keeps `build/oracle/`; the Intent says six.
10. `--version` — **fixed** (Decision 8) with a new `rules` check
    (Decision 13).
11. `run` semantics — **decided** (Decision 6): once per instance (a
    second call returns 70), `Py_FinalizeEx()` after the program (atexit,
    flushed files), stdin as the program when there is no `-c`, `-m` or
    script, the accepted-and-ignored flags listed, other flags exit 2,
    `sys.exit("msg")` prints and returns 1, the plain path's random hash
    secret, the script directory not on `sys.path` (documented), and
    `os.environ` through `clear`/`update` (which calls `putenv`). Other
    door codes raise `OSError` (Decision 5).
12. Builder's paths — **fixed for the artifacts** (Decisions 1 and 7):
    DWARF stripped; the repository path replaced in `_sysconfigdata`
    and numpy's `__config__.py`; zip modes, level and `.dist-info`
    decided. Paths elsewhere in build trees are not artifacts.
13. Stale set after a failed rebuild — **fixed** (Decision 1):
    `build/artifacts/` deleted before steps from 20 run, and assembled
    in `build/artifacts.new/` then renamed.
14. Research pins and staging — **fixed** (Decision 1): `--all` fetches
    the research pins, the default verifies with `--ignore-missing`, and
    step 10 checks the build pins are present; `get <url> <name>` covers
    `%2B`; step 90 refuses untracked recipe files.
15. Moving fixtures into a research directory — **changed**
    (Decision 11): the spike-only fixtures and `bench_startup.py` are
    deleted from the working tree and cited at commit `e007a58`; no
    research record is edited.

The review's question 6 points: the plain reactor's random hash secret
is decided (Decision 6); 001's zip placement and its wasmtime-CLI
statement are corrected (001 Decisions 2 and 3; the door zeroes its
outputs so `-W unknown-imports-default` yields `b""`, 003 Decision 5);
the README "How it is built" is owned here (Decision 12).

### Confirmation by the reviewer, 2026-10-16

I checked each disposition against the revised
`003-the-pinned-build-end-to-end.md` (339 lines) and the amended 001
(the working-tree diff on `e007a58`), not against the text above.
Decision numbers are the revision's. Re-ran: `uv run pytest -q -p
no:cacheprovider -m "not slow"` → `146 passed, 42 skipped, 4 deselected,
8 xfailed`, exit 0. New READs:
- `context/prior_art/numpy/pyproject.toml:52-69` at `ac61120`
  (`license-files`: 16 paths);
- `context/prior_art/numpy/numpy/random/_mt19937.pyx:145-195`
  (`_legacy_seeding` ends with `self._seed_seq = None`);
- `context/prior_art/cpython/Makefile.pre.in:991-992` (the
  `$(BUILDPYTHON)` recipe is one `$(LINKCC)` line);
- `Python/gc.c:1360-1365,1474-1479` (the GC reads the clock only under
  `DEBUG_STATS`);
- `Modules/main.c:841-844` (`Py_FinalizeEx() < 0` → exit 120);
- `Tools/wasm/wasi/__main__.py:79` (an exported `SOURCE_DATE_EPOCH`
  overrides the `git log` default).

1. **Confirmed.** Decision 13 makes the script scans recursive and
   teaches the path scan `@ROOT@`. Two remaining points. The path scan
   should also know the root *variable* the new shell scripts use, if
   it is not `$HERE`. And each of the three scan edits needs a self-test
   that fires on a file under `scripts/steps/`, so the fix cannot
   silently regress.
2. **Confirmed.** Steps 40 and 50 install with no tag filter, and
   Decision 7 drops `*.so`, `*.so.deps` and `tests`. One gap here is
   new finding N3: numpy's `meson install` must run through the vendored
   meson.
3. **Confirmed; the design is sound.** Fixed seeds at Wizer time give
   fixed bytes. A reseed from `os.urandom` before user code gives fresh
   draws per run, from real entropy under a runner and from the
   deterministic stream under the judge, so fuel still repeats. The
   module list I ran natively shows no other import-time random state
   in this pre-import set beyond `random._inst` and
   `numpy.random.mtrand._rand`. `RandomState.seed(0)` also clears
   `_seed_seq` (READ above), so no Wizer-time `SeedSequence` entropy is
   left in the heap. One residual is new finding N5: the plain path's
   reseed imports modules it should not.
4. **Confirmed as decided.** `SOURCE_DATE_EPOCH` is a constant exported
   to every step, and the driver lets the environment override its
   `git log` default (READ above). The zip compiles under
   `PYTHONHASHSEED=0`. The frozen seeds and `_startTime` are fixed, and
   DWARF is stripped. The GC does not store clock readings (READ above).
   Criterion 2 is now **achievable in principle, not yet evidenced**.
   Two things are unproven: that wasi-sdk 24's clang 18 honours
   `SOURCE_DATE_EPOCH` for `__DATE__`/`__TIME__` (INFERRED yes), and
   that CPython's own Wizer-time clock reads (six or seven per start,
   per the clock memo) leave nothing in the heap. Both have a decided
   path: the build does not land until the differing byte is
   explained. The criterion still proves only a relink; it is weaker
   than "two full builds", as noted before. Accepted as written.
5. **Confirmed.** Decision 9 states the pair and carries
   `x-snapshot-zip`. Step 80 decides the Wizer command and the single
   `/` preopen. 001's runner now always writes the set's own zip. A
   cheap addition, not required: the manifest check could compare
   `x-snapshot-zip` with the zip's SHA-256. Today `x-` lines are
   ignored, so a mismatched pair built by hand would still pass.
6. **Confirmed, with two small residuals** (new finding N4).
   - The `--require-hashes` wiring is right. Only the pinned wheels are
     in `build/wheelhouse/`. The requirement hashes come from
     `SHA256SUMS`, so uv re-verifies at install. The four tools have
     no dependencies, which `--require-hashes` needs. `--python` fixes
     the tags and shebangs.
   - The `make -n python.wasm` link line is sound. The recipe is one
     `$(LINKCC) … -o $@ Programs/python.o …` line (READ above). After
     a successful `make`, with only `python.wasm` deleted, `make -n`
     prints just that line. The reactor compile must run in
     `cross-build/wasm32-wasip1`, because `PY_CORE_CFLAGS`' `-I` paths
     are relative to it.
7. **Confirmed.** With `--require-hashes`, a fetched file must still
   match a pin, so the allowance no longer admits unpinned bytes. It can
   still reach the network through a user `uv.toml` `find-links` (see
   N4).
8. **Partly fixed.** CPython (`Doc/license.rst`), pandas (`LICENSES/`)
   and wasi-libc (cloudlibc) are answered. The concatenation is
   compatible with 002's content rule: each component's file still
   *contains* the tarball's or wheel's top-level licence byte for byte,
   provided the files are concatenated unaltered (no line-ending or
   encoding change). **numpy is not fixed** (new finding N1). The
   disposition's READ, "numpy's sdist carries one `LICENSE.txt`", is
   contradicted by numpy's `pyproject.toml`. tzdata's
   `LICENSE_APACHE` is also still unnamed ("each wheel's licence file",
   singular).
9. **Confirmed.** The regex edit only tolerates Markdown's line wrap,
   and the README sentence must still state the guest's number, so it
   does not weaken the judge. The README is owned (Decision 12), the
   oracle is kept, and the Intent says six.
10. **Partly fixed.** `-V`/`--version` and the README sentence are
    decided and checked. But §4.11 lists four facts, "the 32-bit
    default integer, the missing threads, the missing modules, the
    speed ratio", and the sentence omits the speed ratio (new finding
    N6).
11. **Confirmed as decided**, with three new findings on how: N2
    (the cost of `Py_FinalizeEx`), N5 and N7.
12. **Confirmed.** The path is replaced in memory before compiling, so
    no upstream or generated file on disk changes. DWARF is stripped.
    Modes, level and `.dist-info` are decided.
13. **Confirmed.**
14. **Confirmed.** macOS `shasum` accepts `--ignore-missing`. The
    harness's regex still matches `shasum -a 256 --ignore-missing -c
    SHA256SUMS`. Step 10 re-checks presence, and uv re-checks the tool
    wheels' hashes.
15. **Confirmed.** The evidence memo's `fixtures/` row now points at
    files that exist only at `e007a58`. That is acceptable, because the
    landing notes cite the commit.

The question 6 points are confirmed: 001's runner zip placement and its
CLI wording are corrected, and the door's zeroed outputs make
`-W unknown-imports-default` yield `b""`.

### New findings from the revision, most severe first

- **N1. numpy's bundled notices are still missing** (`003:205`;
  constitution §4.12). numpy declares 16 licence files
  (READ: `pyproject.toml:52-69`). Its sdist ships them under
  `numpy/linalg/lapack_lite/`, `numpy/fft/pocketfft/`,
  `numpy/random/src/{mt19937,pcg64,philox,sfc64,distributions,splitmix64}/`,
  `numpy/random/`, `numpy/ma/`, `numpy/_core/src/multiarray/dragon4_LICENSE.txt`
  and `pythoncapi-compat`. The top-level `LICENSE.txt` is numpy's own
  BSD text only.
  Failure: `python.wasm` statically contains lapack-lite, pocketfft,
  the four bit generators and the distributions code, and the zip
  contains `numpy.ma`. `LICENSES/numpy.txt` reproduces none of their
  notices. Fix: concatenate the `license-files` that apply to code the
  build compiles or zips. highway, svml and x86-simd-sort are disabled
  by the cross options and may be left out with that reason.
  Also name tzdata's `LICENSE_APACHE`.
- **N2. `Py_FinalizeEx()` on every `run` puts a full teardown of numpy
  and pandas into every snapshot call** (`003:166-170`). Finalizing is
  *safe*. It is the path every native `python` exit takes with these
  modules loaded. With static linking nothing is `dlclose`d. And
  "once per instance" avoids numpy's unsupported re-initialization.
  But it is not *cheap*.
  Failure (INFERRED; measure it): the snapshot's `print(1)` runs a few
  thousand Python instructions, then `Py_FinalizeEx` clears roughly 600
  modules' dictionaries, runs a full collection and deallocates
  pandas' and numpy's object graphs. Per-call fuel and wall time rise by
  orders of magnitude, and the README's "starts in 3 to 5 ms" becomes
  untrue. `test_snapshot_preimports_the_stack` compares the snapshot's
  `import pandas` (now about one teardown) with the plain one (start,
  import and the same teardown). It still very likely holds, but no
  longer by a wide margin. The instance is discarded anyway, so the
  intent (`atexit` runs, user files flushed) can be met for less:
  run `atexit._run_exitfuncs()`, clear `__main__`'s namespace, run one
  `gc.collect()`, and flush the standard streams. Decide by measuring
  both on the pandas snapshot (a benchmark fact in the memo). Also
  decide the exit code when finalization fails: CPython returns 120
  (READ: `Modules/main.c:841-844`).
- **N3. numpy's `meson install` must use the vendored meson**
  (`003:61-64`, `003:110-112`). Decision 3 puts
  `build/tools/pylib/bin` first on `PATH`, so a bare `meson` is meson
  1.12.1.
  Failure: step 40 configures `build/numpy-build/` with numpy's
  vendored meson (1.11.x) and then runs `meson install`. meson 1.12.1
  refuses a build directory made by another version, or regenerates it.
  Fix: every meson command of step 40 runs as
  `"$PY" build/numpy-2.5.2/vendored-meson/meson/meson.py …`.
- **N4. Small wiring residuals** (`003:35-36`, `003:52-54`).
  `UV_CACHE_DIR=build/uv-cache` is relative, so it lands wherever step
  10 happens to `cd`; export it as an absolute path. Add `--offline`
  (or `--no-config`) to the `uv pip` line, and let the fetch scan
  require it. Otherwise a `find-links` in the user's `uv.toml` can make
  uv contact the network. Hashes keep the bytes honest, but the build
  should not fetch at all outside `00_download.sh`.
- **N5. The plain path's reseed imports what the program never asked
  for** (`003:156-158`). `run` "reseeds `random` and, when it is
  imported, numpy's … sets `logging._startTime` to now".
  Failure: on the plain reactor, `print(1)` now imports `random` (and
  its dependencies) and, read literally, `logging`. That changes
  `sys.modules` and adds fuel to every plain run. Fix: "when it is
  imported" for `random` and `logging` too. In a snapshot both are
  imported, so nothing is lost.
- **N6. The version sentence omits the speed ratio §4.11 names**
  (`003:191-194`). Add it as a stated range, for example "numpy and
  pandas kernels 1.3 to 2.3 times native", from the spike memo's
  benchmark facts. A later release's memo can update the figure; the
  check compares the guest with the README, not with a measurement.
- **N7. `-m` must alter `sys` as CPython's does** (`003:159`).
  `runpy.run_module(name, run_name="__main__")` without
  `alter_sys=True` leaves `sys.argv[0]` and `sys.modules["__main__"]`
  unchanged.
  Failure: `-m pkg.tool` sees `sys.argv[0] == '-m'`, and
  `pickle`/`dataclasses` lookups through `sys.modules['__main__']` find
  the wrong module. Fix: `alter_sys=True` (or `runpy._run_module_as_main`,
  as CPython's `-m` does).
- **N8. Evidence placement** (`003:22-25`, `003:101-105`). The
  specification now stands partly on "the review's READ findings", and
  it records the cloudlibc pin as EXECUTED inline without the URL.
  Reviews are not research. Under §5.1 and §4.10, a two-paragraph memo
  (or an addendum memo to the build-needs one) should hold the
  cloudlibc URL, its hash and size, and the four READ facts the
  revision relies on. Low severity, and quick to fix.

## Verdict

**Build after the findings are answered.** The shape is right: one
command, numbered steps, a pinned host Python, out-of-tree builds, and
an artifact directory the harness reads. But as drafted, the judge
would pass the build scripts without reading them (1), pandas would not
import (2), every snapshot would share one random stream (3), and the
byte-identity criterion cannot hold (4). Each needs a decision in the
text before any code is written.

**After the revision (2026-10-16): build after the findings are
answered.** Findings 1–7 and 9–15 are confirmed fixed or decided, and
criterion 2 is now achievable in principle with a decided path if it is
not. Before building, the text still needs: N1 (numpy's bundled
licence notices: a §4.12 hard constraint), N2 (decide `Py_FinalizeEx`
against a cheaper exit, by measurement), N3 (the vendored meson for
numpy's install) and N6 (the speed ratio in the version sentence,
§4.11). N4, N5, N7 and N8 are one-line text changes that can go in with
them. None of them changes the design.

## Disposition of the confirmation's findings (by the author, 2026-10-16)

- N1 numpy's licences — **fixed**: `LICENSES/numpy.txt` concatenates
  every file numpy's `pyproject.toml` declares in `license-files` (17,
  READ in the research memo below); each wheel contributes every licence
  file in its `.dist-info` (tzdata's `LICENSE_APACHE` included).
- N2 `Py_FinalizeEx` — **kept, by decision** (Decision 6): correctness
  first (constitution §3); only full finalization guarantees `atexit`
  and flushed files. Its cost is measured as fuel and as a benchmark
  fact in the landing notes, and the README's start-up figure follows
  the measurement. A failed finalization returns 120.
- N3 numpy's install — **fixed**: the vendored meson installs what it
  configured.
- N4 — **fixed**: `UV_CACHE_DIR` absolute; `--offline` added.
- N5 — **fixed**: reseeding and `_startTime` only for modules already
  imported.
- N6 — **fixed**: the version sentence states the measured speed ratio
  and names its source.
- N7 — **fixed**: `alter_sys=True`.
- N8 — **fixed**: `../research/2026-10-16-facts-the-build-review-found.md`
  re-reads each fact in the pinned sources and records the cloudlibc
  pin; the specification cites it instead of the review.

The verdict's condition (N1, N2, N3, N6 answered) is met; the build
proceeds. The build's own review re-checks these against the code.
