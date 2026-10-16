# Review of 003 — The pinned build, end to end, with the neutral door

- **Date:** 2026-10-16
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I was
  given the constitution, `AGENTS.md`, `context/README.md`, the review
  template, specifications 001, 002 and 003 (with 003's landing notes),
  003's specification review, the five research memos the brief named,
  and the change itself. I did not rely on the author's summary. I
  checked each landing-note claim myself.
- **Reviewed:** everything uncommitted on top of `f2292db`: the staged
  and unstaged diff (54 files, +1950 −863), the two untracked research
  memos, and the built outputs under `build/` (`artifacts/`, `logs/`,
  `link/`).
- **Re-ran (EXECUTED, this machine, darwin-arm64):**
  - `uv run pytest -q -p no:cacheprovider` → `wasi_python v1: 61/68 pass ·
    2 gap · 5 blocked · 0 fail (unit suite 133/133)`; `194 passed, 5
    skipped, 2 xfailed`; ratchet `lost 0 · absent 0 · unrun 0 · gained 0
    · grew 0`; exit 0. I ran it again after my rebuild (below), with the
    same counts and exit 0.
  - `uv run pytest -q -p no:cacheprovider -m "not slow"` → `190 passed, 5
    skipped, 4 deselected, 2 xfailed`; exit 0.
  - `uv run ruff check src tests` → `All checks passed!` (0).
    `uv run ruff format --check src tests` → `35 files already
    formatted` (0). `uv run python tests/jobs/regen.py --check` → `ok`
    for `numpy_csv`, `pandas_csv` and `numpy_random` (0).
  - Determinism: I saved `build/artifacts/*`, then ran `scripts/build.sh
    60 70 80 90`. Output: `ok 60_link: reactor: 31731935 bytes,
    fc69ea30c75139cc`, `ok 70_zip: … 10321907 bytes`, `ok 80_snapshot:
    snapshot: 64193898 bytes, 07243afe3dfcba86`, `ok 90_artifacts: 14
    files`; exit 0. `python.wasm` (`fc69ea30…`), `python-stdlib.zip`
    (`bf6d4a88…`), `MANIFEST` and `build/link/python.map` came out
    identical. The snapshot did not: `f5b8693e…` became `07243afe…`.
  - `uv run python scripts/compare_snapshots.py <old> <new>
    build/link/python.map` → `469 differing bytes in 179 symbols; 176 not
    allowed`, exit 1. The author's run saw 392 bytes.
  - Residue source (EXECUTED): many differing words hold `0x6ad285d2` in
    the old snapshot and `0x6ad2884c` in the new one. That is 1792181714
    and 1792182348 in Unix seconds. `stat -f %m` on `build/wizer-root`,
    its `usr/local/lib` and `python314.zip` gives `1792182348` for all of
    them. These are the mtimes of the Wizer root, which step 80 creates
    with `cp`.
  - Experiment (EXECUTED, written only to the scratchpad): two roots with
    `find <root> -exec touch -h -t 202601010000.00 {} +`, then Wizer run
    on each with step 80's flags, 3 s apart.
    `compare_snapshots.py` → `44 differing bytes in 12 symbols; 9 not
    allowed`. That is 17 bytes in the three named C-runtime symbols and 27
    bytes in 9 heap runs, down from 469 bytes in 179 runs.
  - Liveness of the residue (EXECUTED, in the snapshot guest):
    `gc.unfreeze()`, then every tracked object and its referents mapped
    by `id()` and `sys.getsizeof` against the 179 runs. 63 runs fall
    inside `str` objects at offset 17 (1 or 3 bytes), which is the
    unused upper 24 bits of `PyASCIIObject.state` (READ: the bitfield's
    `:24` padding). The rest lie outside any object. They sit in a GC
    head, in block slack, or in objects my probe made at run time.
  - Guest behaviour, with my own wasmtime-py driver. It used real WASI
    entropy and clocks and did not shadow `random_get` or
    `clock_time_get`. Results (EXECUTED):
    - Two snapshot runs of `random.random()` and `np.random.rand()`
      differ. `logging._startTime` is the current time. `hash('abc')` is
      `-1600925533` both times (fixed by design). On the plain reactor
      it differs per run.
    - `-c` in the snapshot sees `['csv', 'encodings', 'gc', 'io',
      'json', 'numpy', 'os', 'pandas', 're', 'time']` in `globals()`.
      The plain reactor sees `[]`.
    - `-c 1/0` → exit 1. The traceback begins with `File "<reactor>",
      line 63, in run`. A custom `sys.excepthook` is not called.
    - A script path gives `__name__ == '__main__'` and
      `sys.argv == ['/w/s.py', 'a', 'b']`. `import sib` from the script's
      directory fails, as documented.
    - `-m json.tool /w/in.json` and `-m calendar 2026 1` → 0, with the
      right output.
    - Stdin with no argument runs the program (`sys.argv == ['']`). `-`
      → `FileNotFoundError: '/-'`, exit 1.
    - `-O` → `unknown option -O`, exit 2. `-Xutf8` → exit 2. `-X dev` →
      0.
    - `-V` and `--version` print the Decision 8 sentence.
    - `sys.exit('bad thing')` → `bad thing` on stderr, exit 1.
      `SystemExit(3)`, `(256)` and `(-1)` → 3, 256 and -1.
    - A second `run()` on the same instance → 70, with its message (both
      binaries).
    - `env={'FOO': 'bar', 'TZ': 'UTC'}` → `os.environ` and `os.getenv`
      see exactly that.
    - An `atexit` handler runs. An unclosed file written at module level
      is flushed to disk.
    - `-u -c "print('x'); os._exit(0)"` → stdout empty.
      `sys.stdout.line_buffering` and `write_through` are both `False`.
    - No pinned lambda survives in the snapshot (0 found after
      `gc.unfreeze()`). `threading._time`, `subprocess._time` and
      `queue.time` are `time.perf_counter`, not `time.monotonic`.
    - With `PYTHONTZPATH=/w/tz`, `zoneinfo.TZPATH` is
      `('/w/tz',)` on the plain reactor and the four defaults in the
      snapshot.
    - Importing every name in `sys.stdlib_module_names` gives 46
      failures. The expected ones are present (`_ssl`, `_sqlite3`,
      `_bz2`, `_lzma`, `_ctypes`, …). Also failing: `pdb`, `pydoc` and
      `doctest` (`No module named '_pyrepl'`).
    - `sys.builtin_module_names` includes `_testcapi`,
      `_testinternalcapi`, `_testlimitedcapi`, `_testclinic`,
      `_testclinic_limited`, `_testbuffer`, `_xxtestfuzz` and
      `xxsubtype`.
    - `hasattr(sys, 'gettotalrefcount')` → `False` (a release build).
  - Fuel through the harness driver (`tests/harness/guest.py`), two runs
    each, on my rebuilt snapshot: `-c pass` 117,509,180 ×2;
    `os._exit(0)` 43,747,874 ×2; plain `-c pass` 251,916,499 ×2. These
    equal the landing notes.
  - `grep -a -o '/Users/[…]*' build/artifacts/python.wasm | sort -u` →
    13 paths `/Users/claygendron/Git/Repos/wasi_python/build/Python-3.14.8/Include/…h`.
    The snapshot has the same paths. The zip has none.
    `build/pandas-build/meson-info/intro-buildoptions.json` →
    `b_ndebug: 'false'`; numpy's is `'if-release'`.
  - Added files in upstream trees (`tar -tf` against `find -type f`):
    - numpy: `__pycache__/` under `vendored-meson/`,
      `numpy/_core/code_generators/` and `numpy/_build_utils/`.
    - pandas: `__pycache__/_version_meson.cpython-314.pyc` at the tree's
      root.
    - CPython: `Lib/**/__pycache__` (written during step 20, by the
      driver), the driver's `Modules/Setup.local`, and the three copied C
      files.
    - zlib: none.
  - The installed numpy package against the sdist's `.py` files, tests
    excluded: only build-time scripts are missing (`make_lite.py`,
    `clapack_scrub.py`, highway and pythoncapi-compat docs).
  - The new `SHA256SUMS` lines: every one of the 17 hashes appears in a
    research memo. There are 24 build pins and 2 research pins.
  - Fetch scan: `scan.fetch_hits` on a file holding `uv pip install
    --no-index --require-hashes -r r.txt; curl -fsSL -o x "$MIRROR"` →
    `[]`.
  - Every file the spec says was removed exists at `e007a58`
    (`git cat-file -e`).
- **READ:** `recipes/reactor_main.c`, `recipes/hostmodule.c`,
  `recipes/npy_rename.h`, `recipes/numpy_host_shim.py`, both cross
  files, every file under `scripts/` that changed, `tests/` diff,
  `tests/harness/guest.py`, `build/link/make.log`,
  `build/Python-3.14.8/Include/internal/pycore_mimalloc.h:26-32`
  (`MI_DEBUG 0` outside `Py_DEBUG`; `MI_SECURE` left at its default 0),
  `context/progress/history.jsonl` (line 3: accepted at
  `2026-10-16T20:18:19Z`, before this review).

## Acceptance criteria against evidence

1. *From an empty `build/` (oracle kept), `scripts/build.sh` exits 0,
   prints ten lines, leaves the files of Decision 9.* — **Met, on the
   logs; I did not re-run it from empty.** `build/logs/` holds all ten
   step logs, written 16:11 to 16:15. Step 20's CPython log runs over
   three minutes, which fits a real build. `build/artifacts/` holds
   Decision 9's files: two binaries, the zip, `MANIFEST`, `SHA256SUMS`,
   and nine `LICENSES/*.txt` files. numpy's notice has 17 parts, pandas'
   14, CPython's 2 and tzdata's 2 (with `LICENSE_APACHE`). I re-ran
   steps 60 to 90, which also exit 0.
2. *Steps 60 to 90 again give byte-identical `python.wasm`, snapshot and
   zip.* — **Not met for the snapshot.** The reactor and the zip repeat
   (EXECUTED). The snapshot differs in 469 bytes. See finding 1 for
   whether the narrowing is acceptable.
3. *`uv run pytest` green; v1.1 to v1.4 pass except the named blocked
   checks; the version check passes; four source trees match.* —
   **Met** (EXECUTED above). The judge does not check added files in
   source trees. Its own scoreboard says so ("files a build adds inside
   a source tree").
4. *Six gaps removed because their checks pass.* — **Met.** The six
   entries are gone from `tests/known_gaps.toml`. The six checks pass.
   The two that stay keep their closers.
5. *Accepted with `--accept "003" --accept-judge …`.* — **Met, but too
   early.** History line 3 was written before this review (finding 12).
6. *ruff clean on `src` and `tests`.* — **Met** (EXECUTED).

## Findings, most severe first

1. **Criterion 2 is unmet, and the stop came too early: most of the
   residue is the Wizer root's file mtimes**
   (`scripts/steps/80_snapshot.sh:12`;
   `context/research/2026-10-16-what-makes-the-snapshot-differ.md`
   finding 6) — the memo attributes the 375 heap bytes to "C-level clock
   reads" (INFERRED). They are mostly the build time, taken from `stat`
   of a root that `cp` creates at build time.
   Failure: any two runs of step 80 at different times differ. My two
   runs differed in 469 bytes. Several differing words equal the root's
   `st_mtime` exactly (`0x6ad2884c` = 1792182348). Setting every mtime
   in the root to a constant cut the difference to 44 bytes in 12
   symbols (EXECUTED).
   - The spec review's disposition 4 says: "if a byte still differs, the
     build does not land until the source is found".
   - AGENTS.md rule 7 stops after two failed attempts on *one*
     hypothesis. This hypothesis was never tried.
   - `scripts/compare_snapshots.py` exits 1 on the build as it stands,
     so the narrowed criterion has no passing check either.
   - The residue is **not** a correctness or security defect today
     (EXECUTED above). The `str` hits are padding bits. No `random`,
     numpy or `logging` state, and no pinned fake, survives into a run.
     mimalloc's cookie and keys are unused at `MI_SECURE 0`, release
     build (READ).

   Fix:
   - Fix the root's mtimes in step 80. Use `touch -t` from
     `SOURCE_DATE_EPOCH`, or `os.utime` under the host Python, on the
     directories too.
   - Rerun the comparison.
   - Then either chase the remaining 9 heap runs, or amend criterion 2
     in writing, with the owner's decision, to "reactor and zip
     identical; snapshot differs only in the named regions". If you
     amend it, extend `ALLOWED` so `compare_snapshots.py` passes on that
     contract.
   - Correct the memo's inference before it lands. It is untracked, so
     it can still change.

2. **The snapshot's `__main__` carries the build-time imports**
   (`recipes/reactor_main.c:208`, `:227`, `:83`, `:87`, `:98`) —
   `PyRun_SimpleString` runs PIN, the pre-import and `settle` in
   `__main__.__dict__`, and `run` then executes `-c` and stdin programs
   in that same dictionary.
   Failure: `-c "print(json.dumps(1))"`, or `numpy.zeros(3)` with no
   import, works in the snapshot. It raises `NameError` natively and on
   the plain reactor. `globals()` and `dir()` list ten names native
   Python does not (EXECUTED). Code tested against the snapshot breaks
   when run elsewhere, and the two shipped binaries behave differently.
   Fix: run the build-time strings in a private dictionary
   (`PyRun_String` with a fresh globals dict). Or restore `__main__`'s
   dictionary to its initial keys before `gc.freeze()`. Add a check that
   `-c "print(sorted(globals()))"` matches between the two binaries.

3. **The published binaries embed the builder's home path**
   (`recipes/wasi-pandas.cross:27`, `scripts/steps/50_pandas.sh:19`) —
   13 absolute `/Users/claygendron/Git/Repos/wasi_python/build/Python-3.14.8/Include/*.h`
   strings sit in `python.wasm` and the snapshot (EXECUTED). They are
   `assert()` `__FILE__` strings in the data section, so
   `--strip-debug` does not remove them. pandas is configured with
   `b_ndebug=false`. meson-python's wheels build with `if-release`.
   Failure: the artifacts reveal the owner's username and checkout path.
   A clone at another path, or the Linux CI build, can never reproduce
   `python.wasm`'s hash. pandas also ships with C asserts on, unlike its
   wheels: a failing assert is an `abort` trap where native pandas runs
   on. The spec review's finding 12 was marked "fixed for the
   artifacts".
   Fix: `-Db_ndebug=if-release` in step 50. Add
   `-ffile-prefix-map=@ROOT@=/wasi-python-build` to both cross files'
   `c_args` and `cpp_args`. Add a check that no artifact contains the
   repository path.

4. **`_pyrepl` is left out of the zip, which breaks `pdb`, `pydoc` and
   `doctest`** (`scripts/make_stdlib_zip.py:36`) — Decision 7's list of
   exclusions does not name it, and the landing notes do not list it as
   a departure.
   Failure: `import pdb`, `import pydoc` and `import doctest` raise
   `ModuleNotFoundError: No module named '_pyrepl'` (EXECUTED). So do
   `help()` and any library that imports them at module level. All three
   are pure Python and would otherwise work.
   Fix: keep `_pyrepl`. Or record the exclusion as a decision, with the
   modules it costs, in the spec and the README.

5. **The pin restore puts `perf_counter` where code bound `monotonic`**
   (`recipes/reactor_main.c:156`, `:158`) — `time.monotonic` and
   `time.perf_counter` share one lambda (and the same for the `_ns`
   pair). `_pinned_fake` is keyed by `id()`, so the later real function
   wins.
   Failure: after the snapshot, `threading._time`, `subprocess._time`
   and `queue.time` are `time.perf_counter` (EXECUTED).
   `threading._time is time.monotonic` is `False`, unlike native.
   `time.get_clock_info` reports a different clock name. The values
   agree on this CPython (INFERRED), so today this is identity, not
   arithmetic. It shows the restore is not exact.
   Fix: one lambda per pinned function. Add an assertion in `UNPIN` that
   every rebound value is the real function for that name.

6. **`-u` is accepted and silently not honoured; stdio is buffered**
   (`recipes/reactor_main.c:30`; spec Decision 6) — the decision says
   the config is "already … unbuffered". It is not:
   `line_buffering=False` and `write_through=False` (EXECUTED).
   Failure: `-u -c "print('x'); import os; os._exit(0)"` prints nothing.
   Native Python prints `x`. A program cut off by fuel or an epoch loses
   everything it printed since the last flush, which is all of it for
   most short programs. The README's start-up row recommends
   `os._exit(0)`, which loses output the same way.
   Fix: `config.buffered_stdio = 0`, or honour `-u` with
   `sys.stdout.reconfigure(write_through=True)`. Correct the decision's
   premise, and document the fuel-trap case for embedders.

7. **Pre-imported modules froze Wizer's empty environment**
   (`recipes/reactor_main.c:208`) — modules that read `os.environ` at
   import time keep Wizer's values in the snapshot.
   Failure: with `PYTHONTZPATH=/w/tz`, `zoneinfo.TZPATH` is
   `('/w/tz',)` on the plain reactor and the defaults in the snapshot
   (EXECUTED). The two binaries disagree on the same input.
   Fix: document it (README: "modules the snapshot pre-imports saw an
   empty environment"). Or reset the known cases in `run`, as is done
   for the seeds.

8. **Uncaught exceptions do not look native**
   (`recipes/reactor_main.c:104`) — `traceback.print_exc()` prints the
   `<reactor>` frame, and `runpy`'s frames for a script path, and it
   bypasses `sys.excepthook`.
   Failure: `-c 1/0` prints `File "<reactor>", line 63, in run` above
   the user's frame (EXECUTED). A program that installs an excepthook
   (for logging or JSON errors) never sees its hook called. Anything
   comparing stderr with native differs.
   Fix: call `sys.excepthook(type(e), e, e.__traceback__.tb_next)`, or
   strip the reactor's frames, as CPython's `-c` and script paths show
   only user frames.

9. **Command-line edges differ from CPython without saying so**
   (`recipes/reactor_main.c:78`, `:319`) — four small mismatches:
   - `-` is taken as a script path (`FileNotFoundError: '/-'`) instead
     of "read stdin".
   - The joined form `-Xutf8` is rejected with exit 2.
   - `SystemExit(256)` and `SystemExit(-1)` return 256 and -1, where a
     POSIX exit status is 0 and 255.
   - `sys.orig_argv` is `[]`.

   All EXECUTED.
   Failure: a script runner that passes `-` or `-Xutf8` fails. An
   embedder mapping `run`'s result to a process status gets a different
   code from native.
   Fix: handle `-` and the joined `-X` form. Document that `run` returns
   the unmasked code (or mask it).

10. **"Verified before use" holds only for a full run**
    (`scripts/steps/common.sh:25-29`) — `pinned()` checks that a file
    exists and is listed, not its hash. `scripts/build.sh 10 …` or `40`
    on its own uses whatever bytes are in `downloads/`.
    Failure: a download that is replaced or corrupted after step 00 is
    unpacked and run as a build tool unverified (constitution §4.2).
    Fix: in `pinned()`, `grep "  $1\$" SHA256SUMS | (cd "$D" && shasum
    -a 256 -c -)`.

11. **The judge's new fetch exemption is per line, and no self-test
    guards the three scan edits** (`tests/harness/scan.py:115-122`,
    `:132`) — a line that contains `uv pip install --no-index
    --require-hashes` exempts the whole line.
    Failure: `uv pip install --no-index --require-hashes -r r.txt; curl
    -fsSL -o x "$MIRROR"` gives no hit (EXECUTED). `--offline`, which
    the spec review's N4 asked the scan to require, is not required.
    The spec review's confirmation (item 1) asked for a self-test of each
    scan edit on a file under `scripts/steps/`. `tests/unit/` gains
    none, so the recursion, `@ROOT@`, the `get` regex and the exemption
    can regress silently.
    Fix:
    - Exempt only when the uv command is the line's sole `FETCH` match.
    - Require `--offline`.
    - Add the unit tests.

12. **The run was accepted before review** (`context/progress/history.jsonl`
    line 3, `2026-10-16T20:18:19Z`; AGENTS.md rule 6: "Accept only green,
    reviewed work").
    Failure: the protected state records a reactor this review asks to
    change (findings 2, 5, 6, 8). The fixes change `reactor_main.c`'s
    recipe hash and the snapshot's fuel, so a new acceptance is needed
    anyway. Line 3 then stands as an acceptance of unreviewed work.
    Fix: after the fixes, accept again with a reason that cites this
    review. Say in the landing notes that line 3 came before review.
    Whether line 3 is kept is the owner's call, since history is
    append-only once committed.

13. **numpy's and pandas' builds write caches into their source trees**
    (`scripts/steps/40_numpy.sh:16-22`, `50_pandas.sh:19-20`; Decision
    4) — Decision 4 says only CPython's driver and the three C files
    write inside an upstream tree.
    Failure: `numpy-2.5.2/` gains about 150 `.pyc` files under
    `vendored-meson/`, `numpy/_core/code_generators/` and
    `numpy/_build_utils/`. `pandas-3.0.6/__pycache__/` appears too
    (EXECUTED). The tarball check ignores added files, so it is green.
    The future release workflow's "any diff against the pinned tarball"
    gate would not be. No upstream file is modified, so §4.1 holds.
    Fix: `export PYTHONDONTWRITEBYTECODE=1` in `common.sh`.

14. **CPython's test modules ship as builtins** (`build/link/make.log`:
    the static link) — the driver's defaults compile `_testcapi`,
    `_testinternalcapi`, `_testlimitedcapi`, `_testclinic*`,
    `_testbuffer`, `_xxtestfuzz` and `xxsubtype` into the product
    (EXECUTED: `sys.builtin_module_names`).
    Failure: guest code can `import _testinternalcapi` and corrupt
    interpreter state. This stays inside the sandbox but is surprising
    in a product. It also costs size and attack surface no user asked
    for.
    Fix: disable test modules through the driver's configure arguments,
    if it accepts them. Otherwise record it as a driver default in the
    README.

15. **The door trusts the host's answer without checks**
    (`recipes/hostmodule.c:45`, `:49`, `:23-25`) — a host that returns 0
    with `out_ptr == 0` and `out_len > 0` makes
    `PyBytes_FromStringAndSize(NULL, n)` return `n` uninitialised bytes
    of guest heap. A negative length raises `SystemError`. A non-zero
    return with a pointer that `host_alloc` did not make is passed to
    `free()`.
    Failure: one misbehaving embedder leaks guest heap contents into
    Python, or corrupts the allocator. INFERRED; the harness host is
    well-behaved.
    Fix:
    - Reject `rc == 0` with a NULL pointer and a length above 0, and
      reject a negative length (`OSError`).
    - Document in 001's contract that a pointer is written only with
      `rc == 0`.

16. **The reactor's own link is not checked for clashes**
    (`scripts/steps/60_link.sh:41-43`, `:56`) — the `signature mismatch`
    and `duplicate symbol` guard reads `make.log` only. The link that
    produces the shipped binary (`eval "$link"`) adds `reactor_main.o`,
    which defines a global `run`, and its warnings go unchecked.
    Fix: capture that link's output and apply the same grep.

17. **Small inaccuracies.** Each is a nit, but each is a claim:
    - The landing notes say "25 build pins". `SHA256SUMS` has 26 lines,
      2 of them research pins, and `MANIFEST` has 24 `pin` lines.
    - The README names one unpinned host input. The build also runs
      host `uv` (step 10), `git` (step 90), `curl`, `tar`, `xz`,
      `shasum` and `sed`.
    - `x-wizer` in `MANIFEST` is a hard-coded string, not the command
      step 80 ran (`scripts/assemble_artifacts.py:138-141`).
    - `MANIFEST` does not record `SOURCE_DATE_EPOCH`.
    - `compare_snapshots.py` compares initial memory only, not globals
      or the file. Its `ALLOWED` key `start` is a generic symbol name.
    - `scripts/bench_native.py:1` cites the deleted
      `fixtures/bench_guest.py`.
    - `scripts/make_stdlib_zip.py:143` is 101 columns (scripts are
      outside the ruff gate).

## Constitution checks

- **§4.1 zero patches: holds.** No file from the four tarballs is
  modified (the tarball check passes). The added files are the driver's
  (allowed), the three copied C files (allowed), and the bytecode caches
  of finding 13 (not allowed by Decision 4's wording).
- **§4.2 every input pinned and hashed: holds for a full run.** All 24
  build pins have literal `get` URLs and hashes recorded in research.
  The tool wheels are installed `--offline --no-index --require-hashes`
  from a wheelhouse holding only the pinned four. Partial runs skip
  verification (finding 10). The unpinned host tools are more than the
  README says (finding 17).
- **§4.3 one target: holds.**
- **§4.4 two-import wall: holds.** The judge's import check passes on
  both binaries, and `host::call` is the only custom import.
  `host_alloc` is an export.
- **§4.5 embedder-neutral: holds in code.** No `vfs` in `scripts/`,
  `recipes/`, `src/` or `tests/`. README line 96 ("for vfs, the
  filesystem verbs") is in "Running it", which 001 owns. It predates this
  change.
- **§4.6 the artifact set: holds.** The layout matches 002 Decision 12.
  No `.cwasm`. The snapshot–zip pair is stated in the README and in
  `x-snapshot-zip`.
- **§4.8 downloads untrusted: holds.** Archives unpack under `build/`.
  uv's cache is `build/uv-cache`. Tools run only from `build/tools/`.
- **§4.10 claims carry their evidence: partly.** The fuel and hash
  numbers reproduce (EXECUTED above). The snapshot memo's INFERRED cause
  is wrong for most of the residue (finding 1). The pin count is off
  (finding 17).
- **§4.11 platform semantics: holds for the four named facts** (`-V`
  and the README agree; the check passes). Three platform facts this
  build adds are not documented:
  - the fixed hash secret of the snapshot (`hash_randomization == 0`:
    every snapshot instance shares string hashes);
  - the frozen environment of finding 7;
  - the buffered stdio of finding 6.
- **§4.12 licence notices: holds per Decision 9.** numpy has 17 parts.
  pandas has `LICENSE` plus 13 `LICENSES/` files. CPython's
  `Doc/license.rst` (which covers mimalloc, expat, libmpdec and HACL*)
  is included. wasi-libc includes cloudlibc. tzdata includes
  `LICENSE_APACHE`.
- **§4.13 tooling: holds** for `src/` and `tests/`. uv is used for the
  harness. The build calls its pinned interpreter by path.
- **§5.4 small, finished, verified:** not yet, because criterion 2 is
  unmet (finding 1).
- **§5.6 / AGENTS rule 6:** acceptance preceded review (finding 12).
- **§7 never-do list:** nothing tripped. Nothing fetched outside
  `00_download.sh`, nothing copied, no commit.

**The landing notes' departures.** I judged each one:
- numpy `--tags python-runtime,devel`: **sound.** Every non-test runtime
  `.py` is installed (EXECUTED comparison).
- pandas from the sdist tree plus `_version_meson.py`: **sound.**
  `import pandas` and the goldens pass. It hides that pandas' C is built
  with asserts on (finding 3).
- `npy_rename.h`: **sound.** It renames numpy's `NPY_NO_EXPORT` copy,
  and step 60 now fails on the warning class that exposed it.
- The three reproducibility measures:
  - the clock and entropy pins: no fake survives, but the restore is
    inexact (finding 5);
  - the stack clear: safe, since it zeroes only below the current
    frame's address minus 256 and the area below the stack pointer is
    dead;
  - mimalloc's random context: works, but couples to CPython's internal
    header, so a CPython upgrade must recheck it.
- `python.map`: fine.
- Deleted spike files: all present at `e007a58` (EXECUTED).

**Departures missing from the notes:**
- `_pyrepl` left out of the zip (finding 4);
- `__main__` used for the build-time code (finding 2);
- `build.sh` exports `PYTHONHASHSEED=0` to every step and deletes
  `build/artifacts/` from step 10, not 20;
- `gc.collect()` runs before `gc.freeze()`;
- numpy's `*_tests` and `_simd` modules are left out of the link.

The last three are harmless but undocumented.

**Judge edits (Decision 13).** Each edit is listed in the decision. None
creates a false green on the current tree. Recursive scanning makes the
judge stronger. The integer regex now accepts repeated, consistent
mentions, which is no weaker in practice. The new version check compares
the guest's `-V` with the README. The needs now name 003. Two points
remain: the fetch exemption is too wide and has no tests (finding 11).

**`build/artifacts` default discovery is safe.** `build.sh` deletes the
set before any build step, and step 90 renames a complete
`artifacts.new`. A stale set fails `test_manifest_recipes_match_the_tree`
when a recipe changes, and `$WASI_PYTHON_ARTIFACTS` still overrides it.
One limit: the ratchet keys the artifact by `python.wasm`'s hash. After
my rebuild the snapshot changed and the run stayed green with no
`grew`. That is right for content, but the judge does not notice a
different snapshot.

## Disposition (filled in by the author, then confirmed by the reviewer)

The author answered every finding on 2026-10-16. Everything below was
rebuilt from an empty `build/` (except `build/oracle/`) and then steps
60 to 90 twice more. Evidence is in spec 003's landing notes (EXECUTED
unless marked).

1. **Fixed, and the cause went one level deeper.** The mtime fix alone
   left 44 bytes, as the reviewer found. The remaining 27 heap bytes
   followed the root's inode and change time, which `touch` cannot
   set: Wizer run twice on one root left only the 16 named C-runtime
   bytes. The reactor's link now wraps `__wasi_clock_time_get`,
   `__wasi_random_get`, `__wasi_path_filestat_get` and
   `__wasi_fd_filestat_get` (`wasm-ld --wrap`; no upstream file is
   touched). While a reactor flag is set, they answer constants. The
   flag starts set, so the C runtime's constructors are covered too. It
   is cleared in `run` before Python starts and at the end of
   `wizer.initialize`. With this wrap, every rebuild gives the same
   snapshot (0 differing bytes), and criterion 2 holds unamended.
   `compare_snapshots.py` keeps an empty `ALLOWED`.
   - The executed memo keeps finding 6 and marks its inference wrong;
     an addendum (findings 8 to 10) records the cause and the fix.
   - The placeholder memo is completed in place as executed.
   - The Python-level stand-ins and the mimalloc context reset are
     removed. This also answers finding 5.
   - A new check, `test_a_program_sees_real_entropy_and_file_metadata`
     (both binaries), proves no pinned value reaches a program.
   - The pass also found a second source of nondeterminism. The zip's
     bytes depended on whether the host Python had bytecode caches of
     its own: marshal marks a string as shared by its reference count.
     Steps 60 and 70 now remove those caches first. A zip built after
     deliberately leaving 20 caches in place matched.
2. **Fixed.** The pre-imports and the settle code run in a private
   namespace (`run_private`), so `__main__` starts with CPython's six
   names on both binaries. Check: `test_main_starts_as_native`.
3. **Fixed.** pandas is configured with `-Db_ndebug=if-release`, and
   both cross files carry `-ffile-prefix-map=@ROOT@=/wasi-python-build`.
   No artifact holds the checkout path (`grep -c` gives 0). Check:
   `test_artifacts_carry_no_build_path`.
4. **Fixed.** `_pyrepl` stays in the zip, and spec 003 Decision 7 says
   so. Check: `test_stdlib_debugging_tools_import`. The zip grew 1.48%;
   that growth is accepted with this reason.
5. **Fixed by removal.** The Python-level pins are gone (see 1). The
   pins now sit below Python, so nothing needs restoring.
   `test_a_program_sees_real_entropy_and_file_metadata` and the
   reviewer's probe both show the identity: `threading._time is
   time.monotonic` and `queue.time is time.monotonic` are now `True`.
6. **Fixed.** `-u` replaces stdout and stderr with text wrappers over
   the raw file, with `write_through`, as CPython's `-u` does. The
   first attempt, `reconfigure(write_through=True)`, still lost output
   in the `BufferedWriter`. On a terminal, stdout is line-buffered.
   Decision 6's premise is corrected. The README says a fuel-stopped or
   `os._exit` program loses unflushed output unless run with `-u`.
   Check: `test_unbuffered_output_survives_a_hard_exit`.
7. **Fixed for the named case, and documented in general.** `run`
   re-reads `zoneinfo`'s path when `PYTHONTZPATH` is set. The README
   states that pre-imported modules saw an empty environment.
8. **Fixed.** The traceback is trimmed of `<reactor>` frames, and of
   `runpy`'s for a script, and set on the exception, because the
   default hook prints the exception's own traceback. It then goes
   through `sys.excepthook`, with CPython's fallback if the hook
   raises. `-c` source is registered with `linecache`, as CPython's
   `-c` does, so the line and its carets print. A script that cannot be
   opened prints CPython's `can't open file` line and returns 2.
   Check: `test_uncaught_errors_print_as_native`, which compares the
   whole stderr with native 3.14's.
9. **Fixed.**
   - `-` reads stdin, with `sys.argv[0] == '-'`.
   - `-X<opt>` is accepted.
   - Exit codes are masked to 0..255.
   - `sys.orig_argv` is set.

   Check: `test_exit_status_is_a_process_status`. `-Xutf8` is covered
   inside the `-u` check.
10. **Fixed.** `pinned()` runs `shasum -a 256 -c` on the file's own line
    every time it is used.
11. **Fixed.** The exemption now holds only when `uv pip` is the line's
    one fetch word, and it needs `--offline`, `--no-index` and
    `--require-hashes` as separate words, with no `://`. Unit tests
    cover the exemption, with five lines including the reviewer's
    `; curl` case. They also cover recursion (`scan.every_file`, which
    the checks now share), named `get <url> <name>` lines, and
    `@ROOT@` paths.
12. **Answered.** History line 3 stays, because the history is
    append-only. Line 4 accepts the reviewed state, with a reason that
    cites this review. The landing notes say line 3 preceded the
    review.
13. **Fixed.** `PYTHONDONTWRITEBYTECODE=1` is set in `common.sh`. After
    a build from empty, `find` shows no `__pycache__` in numpy's,
    pandas' or zlib's trees.
14. **Fixed.** Step 20 passes `-- --disable-test-modules` to the
    driver, which forwards it to both configures. The plain reactor is
    6% smaller. Check: `test_no_cpython_test_module_is_built_in`.
    pandas' own `pandas._libs.testing` stays, because pandas imports
    it.
15. **Fixed.** An answer of 0 with a negative length, or with a NULL
    pointer and a length, raises `OSError` and never builds bytes from
    unwritten memory. The contract is stated in `hostmodule.c` and in
    spec 003 Decision 5, which 001 cites.
16. **Fixed.** The reactor's compile and link write their own logs.
    The same clash grep runs on the link's log.
17. **Nits.**
    - **Pin count: fixed.** The notes say 24 build pins and 2 research
      pins.
    - **Unpinned host tools: fixed.** The README lists them.
    - **`x-wizer`: fixed.** It is the command step 80 ran, written
      there.
    - **`x-source-date-epoch`: added.**
    - **`compare_snapshots.py`: answered.** It now backs up the SHA-256
      comparison and only explains a difference, so memory alone is
      enough. `ALLOWED` is empty, so the generic `start` key is gone.
    - **`bench_native.py`: fixed.** It cites the file at `e007a58`.
    - **Long line: wrapped.**

Also answered:
- **Departures missing from the notes:** the landing notes now list
  `gc.collect()`, `PYTHONHASHSEED`, the step-10 deletion, and the
  `*_tests`/`_simd` exclusion.
- **Platform facts:** the README now states the snapshot's fixed hash
  secret, its frozen environment, and buffered stdio.
- **The ratchet keys the artifact by `python.wasm` only:** noted as a
  limit. With byte-identical snapshots it is no longer hiding drift,
  and a judge change to key it by both is left for the release work.

**One change the review did not ask for.** Finding 1's wrap and
finding 8's fixes made the plain reactor's per-start fuel grow 4.9%,
because it compiled a bootstrap twice as long at every start. The
measured cost was 17.9 million instructions, against 9.6 million for
the old one. The bootstrap is now `recipes/reactor_bootstrap.py`. Step
60 marshals it at build time (`scripts/freeze_bootstrap.py`, under the
same 3.14 host, with `PYTHONHASHSEED=0`), and the reactor loads it
after checking the bytecode magic. Plain-reactor fuel is now 2.1% below
history line 3. The snapshot's `run` costs about 0.12% more, for the
CPython-faithful work in 6, 8 and 9; that growth is accepted with this
reason.

**Re-ran after the fixes:**
- `uv run pytest -q -p no:cacheprovider` → `74/81 pass · 2 gap · 5
  blocked · 0 fail (unit suite 135/135)`, `209 passed, 5 skipped, 2
  xfailed`. The ratchet shows only the growth named above.
- ruff check and ruff format are clean.

## Verdict

**Lands after the findings are answered.** The build is sound, green
and reproducible for the reactor and the zip. Before landing, these need
a fix or a written answer:
- criterion 2's snapshot gap (1): the mtime fix is one line, and
  anything still left over is a recorded owner decision;
- the snapshot's polluted `__main__` (2);
- the builder's path in the published binaries (3);
- the missing `_pyrepl` (4);
- the post-review re-acceptance (12).

Findings 5 to 11 are small reactor and judge fixes, best done in the
same pass, since they change the same files. Findings 13 to 17 can be
answered in writing.

## Reviewer's confirmation, 2026-10-16

I checked the dispositions against the code and the rebuilt set, not
against their text. I read the diff of `recipes/`, `scripts/` and
`tests/`. That includes `reactor_main.c` with its four `--wrap`
functions, `reactor_bootstrap.py`, `freeze_bootstrap.py`, steps 20, 50,
60, 70, 80 and `common.sh`, `hostmodule.c`, `scan.py`, and the new
checks and unit tests.

**Re-ran (EXECUTED):**
- **The set as delivered:** `python.wasm` `d77dc946…`, the snapshot
  `b450c7a6…`, the zip `adf440a3…`.
- **Rebuilds:** `scripts/build.sh 60 70 80 90` twice. Every step said
  `ok`. Both runs gave the same three hashes as the set I started from,
  and the same `MANIFEST` (`02682c24…`) and `SHA256SUMS` (`4a2a63f4…`).
- **`uv run pytest -q -p no:cacheprovider`:** `74/81 pass · 2 gap · 5
  blocked · 0 fail (unit suite 135/135)`, `209 passed, 5 skipped, 2
  xfailed`.
  - The ratchet against line 3 reads `gained 13 · grew 8 · judge
    changed`, and the run exits 1.
  - The eight growths are the zip (+1.48%) and seven snapshot fuel
    metrics (+0.11 to +0.12%). Every other metric shrank: plain fuel
    about −2.1%, plain bytes −6.0%, snapshot bytes −2.9%. This matches
    the disposition.
- **Lint and goldens:** ruff check and ruff format are clean.
  `regen.py --check` reproduces all three jobs.
- **My own probes, under real WASI** (no shadowed clock or entropy), on
  both binaries:
  - `__main__` holds CPython's six names.
  - `-c 1/0` prints native's traceback, carets included. A custom
    excepthook is called.
  - A script's traceback shows only the script's frames.
  - `-` reads stdin. `-Xutf8` is accepted. `SystemExit(256)` and
    `(-1)` give 0 and 255. `sys.orig_argv` is set.
  - `-u … os._exit(0)` keeps `kept`.
  - `PYTHONTZPATH` reaches `zoneinfo.TZPATH`.
  - `pdb`, `pydoc` and `doctest` import, and `pydoc.render_doc` works.
  - No `_test*` or `xx*` builtin is present.
  - A missing script gives `can't open file …` and exit 2.
  - `threading._time`, `subprocess._time` and `queue.time` are
    `time.monotonic`.
  - `os.stat` gives a real inode and mtime, `os.urandom` is not zeros,
    and `time.time()` is now.
  - Two snapshot runs draw different `random` and numpy numbers.
  - A second `run()` returns 70.
- **The door, with a misbehaving host:** a NULL pointer with length 64,
  and length −5, both raise `OSError … malformed response`. A silent 0
  gives `b''`. Code 7 gives `OSError host door returned 7`.
- **Paths and caches:** `grep -c /Users/` finds 0 in both binaries and
  in the unzipped members of the zip. `find … -name __pycache__` finds 0
  in the numpy, pandas and zlib trees.

**Each finding:**
1. **Confirmed.** Three identical sets: byte-identical snapshots and 0
   differing bytes, with `ALLOWED` empty.
   - The wrap is sound. The flag starts set, so the constructors are
     covered. `wizer.initialize` clears it after the pre-imports, and
     `run` clears it before Python starts, on both binaries. Only the
     times, `dev` and `ino` are overwritten; size and type pass through.
   - The import check still passes, so the wall holds.
   - The memo's inference is marked wrong, and findings 8 to 10 record
     the cause. The placeholder memo is completed.
   - The zip's marshal dependence on the host Python's caches, and its
     fix, are recorded.
2. **Confirmed.**
3. **Confirmed.** One residual, not blocking:
   `test_artifacts_carry_no_build_path` searches raw bytes. It cannot
   see inside the zip's deflated members. I checked those by
   decompressing them, and they are clean.
4. **Confirmed.**
5. **Confirmed.** The Python-level pins are gone.
6. **Confirmed.**
7. **Confirmed** for `zoneinfo`. The general case is documented in the
   README.
8. **Confirmed.** One nit remains: when the excepthook itself raises,
   the output adds "During handling of the above exception…" and a
   `<reactor>` frame, which native does not print.
9. **Confirmed.**
10. **Confirmed.** `pinned()` re-checks the hash.
11. **Confirmed.** The sole-fetch-word rule and `--offline` are in
    place, and the unit tests cover my `; curl` case, recursion, `get`
    names and `@ROOT@`.
12. **Confirmed as answered, on one condition.** History has 3 lines
    today, so line 4 does not exist yet. The suite stays red until it is
    written. It must be written after this confirmation, with
    `--accept-judge` and `--accept-growth` for the growth listed above.
    Criterion 5's "Met by history line 4" is true only once that is
    done.
13. **Confirmed.**
14. **Confirmed.**
15. **Confirmed.**
16. **Confirmed.** `reactor-link.log` gets the same clash check.
17. **Confirmed.** The pin count, unpinned tools, `x-wizer`,
    `x-source-date-epoch` and the other nits are fixed.

**The bootstrap change:** it is sound. The bootstrap is marshalled under
the same 3.14 host with `PYTHONHASHSEED=0`, and the reactor checks the
bytecode magic before loading it. The rebuilds above show it is
reproducible.

One more note. The from-empty build in the landing notes came before the
frozen bootstrap. Steps 10 to 50 do not depend on it, and steps 60 to 90
were rebuilt after it, so criterion 1 still stands.

**Verdict: lands.** Its condition is that history line 4 is written now,
after this confirmation, with the judge and growth reasons, and that the
suite is green after it. The other residuals (3, 8) are not blocking.

## Author's note after the confirmation

The confirmation's first residual is closed before acceptance:
`test_artifacts_carry_no_build_path` now also reads every member of the
deflated stdlib zip (a judge edit, covered by line 4's judge reason). It
passes on the confirmed set. The second residual, a raising
`sys.excepthook`, stays as recorded: it prints extra lines that native
Python does not, and only in that case.
