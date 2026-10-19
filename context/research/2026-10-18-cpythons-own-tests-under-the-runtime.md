# CPython's own tests run in the guest, and what they found

- **Status:** executed, 2026-10-18 (a time-boxed prototype in a scratch folder and in the
  git-ignored `build/cpython-suite-research/`; nothing in the repository was changed by it).
- **Owner:** Clay Gendron
- **Researcher:** a research agent (Claude Opus 5.5), at the lane's request.
- **Feeds:** spec 065, CPython's own tests in the release (reserved by spec 063, Decision 15: the
  `python` entry of `tests/upstream/packages.toml` is `later` with 065 as its closer). The owner,
  answering question 99 on 2026-10-18: "Gate 0.1.0 regardless".
- **Stands on:** spec 050 (numpy's and pandas' own tests under the runtime) and its memo
  `2026-10-18-numpy-and-pandas-own-tests-in-the-guest.md`, whose method this follows; spec 063 and
  its memo `2026-10-18-the-release-judges-in-parallel-shards.md` (the shard model, the CI fuel
  rate).
- **Evidence:** beside this memo. `per-module-results.tsv` is the table, one row per module.
  The scripts are `stage.py`, `drive.py`, `run_one.py`, `run_many.py`, `analyze.py`,
  `classify.py`, `shards.py` and `probe.py`. `evidence/` holds the failures, the classes, the
  skip reasons, the shard lists and records, and the guest-time log. The raw records (stdout,
  stderr, regrtest's XML per session) stay in `build/cpython-suite-research/runs*/`.

Terms used below:

- **regrtest** is CPython's test runner, `python -m test` (`Lib/test/libregrtest/`).
- A **module** is one entry of regrtest's `--list-tests`. Split packages count once per
  sub-module, so `test_os.test_posix` is one module.
- A **session** is one guest run: one fresh instance, one regrtest process.
- **Fuel** counts the guest's executed instructions; 1 G is 10⁹.

## How it was run (EXECUTED)

- **The set.** The frozen artifact set `build/sets/s-4eb5418a2b1bb553` (CPython 3.15.0, numpy
  2.5.2, pandas 3.0.6, matplotlib 3.11.2), read in place. The **snapshot** binary, as spec 050
  uses.
- **The driver.** The judge's own guest driver, `tests/harness/guest.py`, imported unchanged.
  It brings the seeded random, the stepped clock (it starts at 2026-01-01 and moves 1 µs per
  read), the fuel meter, a fresh writable root at `/`, the stdlib zip read-only at
  `/usr/local/lib` and matplotlib's data. `env` is `TMPDIR=/tmp HOME=/tmp`, as spec 050's.
  wasmtime-py's default `max_wasm_stack`, as the judge and the runner use. The compiled module
  is serialized once to `build/cpython-suite-research/` and deserialized per process.
- **The tests.** `stage.py` checks `downloads/Python-3.15.0.tar.xz` against
  `downloads/SHA256SUMS` and reads its member names; it extracts nothing. It copies each
  `Lib/test/` member from the source tree `build/Python-3.15.0` (1,810 files, about 40 MB). It
  leaves out the 11 files that are not members (`__pycache__`). The stage is granted read-only
  at `/cpy`. CPython carries no recorded patch (`recipes/patches/` has none for it; READ).
- **How the guest imports them.** The zip has no `test` package: `scripts/make_stdlib_zip.py`
  skips every `test` and `tests` folder (`SKIP_DIRS`, line 65; READ; 0 members, EXECUTED).
  `test` is a top-level package of its own, so the driver appends `/cpy/lib` to `sys.path`.
  Spec 050 joined test folders to the packages' `__path__`; this is the same idea one level
  up. Appending keeps every module the product has coming from the product.
- **The runner in the guest.** `drive.py` calls regrtest's own `main()` in the one process.
  The options are `-u all,-cpu,-gui,-largefile`, plus `--junit-xml /tmp/junit.xml` for the
  per-test record. There is no `-j`: the guest cannot start processes.
- **Four adaptations,** each in `drive.py` with its reason:

  | id | what | without it |
  |---|---|---|
  | A1 | gives the product's `ctypes` stand-in a no-op `_reset_cache` | every module "failed (uncaught exception)". The snapshot pre-imports numpy, which imports the stand-in. regrtest's `clear_caches()` then calls `ctypes._reset_cache()` on whatever `ctypes` is in `sys.modules` (`libregrtest/utils.py:255`) |
  | A2 | `os.makedirs("/tmp")` | the root is empty, so regrtest's work folder and `tempfile` fall back to `/`, and the XML could not be written |
  | A3 | an empty file at `/usr/local/bin/python.wasm` (only in the variant runs of section 3) | 5 modules fail to import, and 1 test errors (finding 4.3) |
  | A4 | keeps each module's XML as text and writes the text | in one session, `test_xml_etree` and `test_xml_etree_c` swap ElementTree's classes. The XML writer then fails with `append() argument 1 must be xml.etree.ElementTree.Element, not xml.etree.ElementTree.Element`, and the session's whole record is lost. A4 was added after the per-module pass and the first shard runs |

- **The passes.**
  1. Every module in its own session: 557 sessions, A1 and A2. Fuel cap 4×10¹¹, and a
     300-second wall limit per module. Nothing reached either.
  2. The 47 modules that did not end OK, again with `-v`, to name each failing test.
  3. Variants on a few modules: with A3, with a 2 MiB wasm stack, and a hunt for traps.
  4. Three shards, each one session of about 160 to 230 modules (section 5).
  5. Two modules run twice, to check that fuel repeats.
- **The machine.** It was shared with builds and the landing lane: load average 37 to 111 on
  10 cores. Only one guest ran at a time. So the wall times below are inflated; fuel and counts
  are not. Total guest time was about 39 minutes (`evidence/elapsed.txt`, plus about 4 minutes
  of probes that it does not log).

## 1. How CPython's own WASI CI runs the suite (READ)

- **The workflow.** `context/prior_art/cpython/.github/workflows/reusable-wasi.yml` is a
  60-minute job. It runs wasmtime 38.0.3 and wasi-sdk 24, and makes a debug build
  (`--with-pydebug`). Then it runs `make --directory cross-build/wasm32-wasip1 test`.
- **What `make test` runs.** It is `$(TESTRUNNER) --fast-ci -u-gui` (`Makefile.pre.in:2343`).
  The test runner is the build machine's own Python (`TESTPYTHON = $(PYTHON_FOR_BUILD)`). regrtest sees a cross build with a
  `HOSTRUNNER` (`libregrtest/main.py:629–640`). It then adds `-j 2` and runs each worker as its
  own process, `wasmtime run … python.wasm -m test.libregrtest.worker`. So the parallelism is
  host processes, one wasmtime each. That is the same shape as spec 063's shards.
- **What `--fast-ci` means** (`libregrtest/cmdline.py:473–510`): `-j0`, `--randomize`,
  `--fail-env-changed`, `--rerun`, `--slowest`, `-u all,-cpu`, `--timeout 600`. It also adds
  the Python options `-u -W error -bb -E` (`main.py:646–668`).
- **The host runner** (`Platforms/WASI/__main__.py:16–29`): `--argv0`, `--dir {CHECKOUT}::/`
  (the source checkout is the guest's `/`, so `sys.executable` and the sources exist), and
  `--config Platforms/WASI/wasmtime.toml`.
- **The stack.** That config sets `max-wasm-stack = 33_554_432`, "32 MiB; big enough for the
  test suite to pass under a debug build". The judge and the runner use wasmtime's default.
- **test.support's WASI skips.** `is_wasi = sys.platform == "wasi"`. It turns off processes
  (`has_subprocess_support`), `fork` and sockets. `skip_wasi_stack_overflow()` reads "Exhausts
  stack on WASI". `Lib/test` uses `is_wasi` 88 times in 38 files, and
  `skip_wasi_stack_overflow` 46 times (grep).
- **What this build leaves out.** The build passes `--disable-test-modules`
  (`scripts/steps/20_cpython.sh:16`). So `_testcapi`, `_testinternalcapi`,
  `_testlimitedcapi`, `_testbuffer`, `_testmultiphase` and the `xx*` modules are absent.
  `_decimal`, `_zstd`, `_ssl`, `_hashlib`, `_uuid` and `_ctypes` are missing too (the
  cross-build Makefile's `MODULE_*_STATE`).

## 2. The whole suite, one module per session (EXECUTED)

All 557 modules ran. Each ran in its own session, with wasmtime's default stack and without A3.

| modules | count | passed | skipped | failed | error | fuel |
|---|---|---|---|---|---|---|
| ended OK | 277 | 22,507 | | 0 | 0 | 1,179.7 G |
| ended with failing tests | 28 | 4,996 | | 69 | 83 | 175.5 G |
| failed to import or load ("uncaught exception") | 14 | 0 | | | | 22.9 G |
| **trapped the guest** | **5** | 0 | | | | 10.3 G |
| skipped whole (no sockets, threads, processes; GIL; missing modules) | 231 | 0 | | | | 306.5 G |
| ran no test | 2 | 0 | | | | 2.5 G |
| **all** | **557** | **27,503** | **3,918** | **69** | **83** | **1,697.7 G** |

- **Other outcomes.** 5 tests are expected failures and none passes unexpectedly.
- **The fixed start.** A session costs about 1.14 G before its first test: the snapshot's
  start, regrtest's import and the module's import (`--list-tests` alone took 1.12 G). So 557
  sessions carry about 635 G of starts. One session per shard pays it once (section 5).
- **The heaviest modules:**

  | module | fuel |
  |---|---|
  | `test_zipfile` | 80.5 G |
  | `test_pickle` | 64.1 G |
  | `test_tarfile` | 63.2 G |
  | `test_set` | 38.2 G |
  | `test_decimal` | 33.7 G (pure Python: `_decimal` is missing) |
  | `test_userstring` | 30.6 G |
  | `test_str` | 28.9 G |

  The rest are under 27 G each.
- **Fuel repeats.** `test_json` ran twice to the same instruction (8,157,686,641), and
  `test_datetime` to within 34 in 11.2 G. regrtest's "random seed" comes from the guest's seeded
  random, so the order is fixed too.
- **Wall time** is a benchmark fact, and it is noisy here. The 557 sessions summed 738 s.
  Some modules wait on the host, which fuel cannot see:
  - real sleeps. The stepped clock does not shorten `poll_oneoff`, so `test_sched` took 22 s,
    `test_os.test_os` 19 s, and `test_shelve` 8 s (SQLite's 5-second busy timeout);
  - file-system work under load. `test_tarfile` took 194 s in one run and was most of a
    136-second shard in another.

### The skips (EXECUTED; `evidence/skip-reasons.txt`)

Of the 231 modules skipped whole, the larger groups are:
- 53 "GIL enabled" (the free-threading tests);
- 50 "requires socket support";
- 16 subprocess, 15 threading, 9 `_multiprocessing`, 7 fork;
- 6 `_testinternalcapi`, 5 `_testmultiphase`.

Of the 3,918 skipped tests, the largest groups are:

| tests | reason |
|---|---|
| 750 | "requires subprocess support" |
| 227 + 129 | Windows only |
| 197 | "test requires C version" (no `_decimal`) |
| 177 | "requires zstd" |
| 148 + 99 + 95 + 68 + 43 + … | `_testcapi`, `_testinternalcapi` |
| 136 + 105 + 20 | symlinks |
| 92 | threading |
| 78 | `_testbuffer` ("ndarray object required") |
| 36 | "Exhausts stack on WASI" |

CPython's own skips do their job. Almost everything WASI cannot do is a skip, not a failure.

## 3. Variants (EXECUTED; `evidence/variant-sessions.jsonl`)

- **With A3** (an empty file where `sys.executable` points), the five modules that failed on it
  run:

  | module | passed | skipped | failed | error |
  |---|---|---|---|---|
  | `test_calendar` | 68 | 18 | | |
  | `test_strptime` | 56 | 4 | | |
  | `test_time` | 44 | 20 | 1 | |
  | `test_os.test_posix` | 37 | 148 | | 1 |
  | `test_platform` | 33 (one more than without A3) | 6 | | |

  - `test_time`'s failure is `test_monotonic`. It sleeps 0.5 s, and the stepped clock moves
    only microseconds.
  - `test_os.test_posix`'s error is `test_posix_fadvise`: `OSError: [Errno 22] File too large`.
- **With a 2 MiB wasm stack,** four of the five trapping modules run to their end:
  - `test_doctest`: 74 passed, 1 error;
  - `test_exceptions`: 94 passed;
  - `test_syntax`: 105 passed;
  - `test_traceback`: 178 passed, 96 errors and 9 failures, almost all "No module named
    '_testcapi'".

  `test_functools` still traps, at `TestPartialC.test_recursive_pickle`. 2 MiB is the most
  wasmtime-py 49 accepts: a larger `max_wasm_stack` panics with "max_wasm_stack size cannot
  exceed the async_stack_size", and the Config does not expose `async_stack_size`.
- **The hunt** deselected each trapping test with `-i`, as spec 050's crash hunter did. With
  that, `test_doctest` (73 passed, 1 error), `test_exceptions` (93), `test_functools` (324) and
  `test_syntax` (103) finish at the default stack. `test_traceback` trapped at three places one
  after another:
  - after `CExcReportingTests.test_exception_group_depth_limit`;
  - at `TestFallbackTracebackFormat.test_exception_group_deep_recursion_traceback`;
  - after `TracebackCases.test_signatures`.

  The hunt stopped there (two strikes); the module stays a whole-module trap entry.

## 4. The failures, in classes (EXECUTED; `evidence/classes.tsv`)

Every failed or errored test, every module that failed to load, and every trap falls into one
of eleven classes. None is left unclassified. Counts are from the per-module pass (section 2).

| class | kind | failed | error | modules that failed to load | traps | modules |
|---|---|---|---|---|---|---|
| `c-stack-exhausted` | **defect of this build** | | | | 5 | `test_doctest`, `test_exceptions`, `test_functools`, `test_syntax`, `test_traceback` |
| `no-test-modules` | build choice (`--disable-test-modules`) | 45 | 2 | 3 | | `test_monitoring` (45), `test_call`, `test_inspect`, `test_class`, `test_with`, `test_getpath` |
| `ctypes-stand-in` | product stand-in | 4 | 14 | 3 | | `test_io` (both), `test_pickle` (5), `test_memoryview`, `test_pickletools`, `test_frame`, `test_ctypes`, `test_code`, `test_genericalias` |
| `mmap-stand-in` | product stand-in | 1 | 33 | | | `test_mmap` |
| `bytecode-only-zip` | product choice (spec 003) | 14 | 8 | 1 | | `test_linecache` (4), `test_pdb`, `test_inspect`, `test_contextlib` (both), `test_unittest`, `test_module`, `test_pydoc`, `test_importlib`, `test_sys`, `test_ast` |
| `read-only-eperm` | sandbox (wasmtime) | 1 | 17 | | | `test_bdb` (16), `test_support`, `test_trace` |
| `sqlite-lock` | documented (README) | 1 | 7 | | | `test_sqlite3` (7), `test_dbm_sqlite3` |
| `no-executable-file` | product contract | | 1 | 4 | | `test_time`, `test_calendar`, `test_strptime`, `test_os.test_posix`, `test_platform` |
| `not-in-zip` | product choice | | | 3 | | `test_ensurepip`, `test_venv`, `test_sysconfig` (`ensurepip` and `venv` are not in the zip) |
| `stepped-clock` | judge environment | 3 | | | | `test_os.test_os` (2: `utime` "current" against host file times), `test_logging` (rotation) |
| `wasi-path-errno` | sandbox (wasmtime) | | 1 | | | `test_shutil` |
| **all** | | **69** | **83** | **14** | **5** | |

### 4.1 A real defect: C-level recursion traps the guest (EXECUTED)

- **What happens.** Five modules end in `wasm trap: call stack exhausted`, which kills the whole
  guest. These are not Python exceptions. Plain user code does it too, in the snapshot through
  the judge's driver, at the default stack:

  ```
  class A:
      def __repr__(self): return repr(self)
  repr(A())                                   trap (call stack exhausted), 4.0 M fuel
  l = []
  for i in range(100000): l = [l]
  repr(l)                                     trap, 344 M fuel
  def f(n): return f(n + 1)
  f(0)                                        RecursionError (pure Python recursion is fine)
  eval("(" * 1000 + ")" * 1000)               MemoryError (the parser's own limit)
  ```

  With a 2 MiB stack, the first raises `RecursionError` and the second still traps.
- **The cause** (READ; INFERRED that it is the whole cause). CPython 3.15 guards C recursion
  by measuring its own C stack in linear memory. For WASI it uses `Py_C_STACK_SIZE` 4,000,000
  bytes (`Python/ceval.c:66–80`: no `_Py_LINKER_THREAD_STACK_SIZE` is defined in the
  cross-build's `pyconfig.h`). The linker gives it 16 MiB (`-z stack-size=16777216`). But every
  C call is also a wasm call on wasmtime's own native stack, which `max_wasm_stack` bounds. Its
  default is far smaller (512 KiB, INFERRED from wasmtime's documentation). That stack runs out
  first, and CPython never sees it coming. CPython's CI hides this with 32 MiB, and upstream
  marks some of these tests `skip_emscripten_stack_overflow` only (for example
  `test_exception_group_deep_recursion_traceback`, `Lib/test/test_traceback.py:2256`).
- **Why it matters.** An embedder's guest can be killed by `repr` of a self-referencing object
  or of a deep structure, where native Python raises `RecursionError`. This is the kind of thing
  spec 050 was built to find (spec 050: "the next `os.dup`"). The fix is its own specification:
  - a recipe that lowers CPython's C-stack budget to fit wasmtime's default stack
    (build-class);
  - or a stated stack size in the runner and in the embedder contract;
  - or both.

  wasmtime-py caps the runner at 2 MiB today, and 2 MiB is not enough for the nested-list case.

### 4.2 Upstream test-suite assumptions (EXECUTED; READ)

These are not defects of this build. They are places where CPython's tests assume what
`--disable-test-modules` or one-process runs take away. Each is a candidate upstream report:

- **Unguarded C test modules.** Some `cpython_only` tests import `_testcapi` and
  `_testinternalcapi` without guarding the import, so they error instead of skipping:
  - `test_traceback.CExcReportingTests.get_report`, 90 errors (at 2 MiB);
  - `test_class`, `test_with` and `test_getpath`, which fail to load;
  - `test_call.TestRecursion.test_margin_is_sufficient`.

  `test_monitoring.TestCApiEventGeneration` skips one test, then fails 45 tests across the
  module. The tool it leaves registered is the INFERRED cause.
- **One process leaks state.** In one session, a monitoring tool left in use breaks a later
  module. `test_profiling`'s `CProfileTest` fails 6 tests with `ValueError: tool 2 is already in
  use` in shard 2, and passes alone (section 5). regrtest's workers use fresh processes, so
  upstream never meets this.
- **One process breaks the XML writer** (adaptation A4).

### 4.3 Product facts the suite exercises (EXECUTED)

- **`sys.executable` names a file the guest does not have** (`/usr/local/bin/python.wasm`).
  `platform.libc_ver()` opens it, so `platform`, `time`, `calendar`, `strptime` and
  `os.test_posix` fail to import. The product must decide one of these:
  - `sys.executable` empty (CPython's documented value when it is unknown);
  - a file at that path;
  - or keep it, documented.
- **The stand-ins import.** `ctypes` and `mmap` import, then raise `OSError` on use. CPython's
  tests treat an importable `ctypes` as a working one: `test_ctypes` fails to load and
  `test_mmap` errors 33 times, where a missing module would skip. The README already states "no
  ctypes, mmap".
- **The stdlib is bytecode in a zip.**
  - Tracebacks, `inspect.getsource`, `linecache`, `pdb` breakpoints in stdlib files and
    `pydoc` have no source.
  - `os.listdir` of the zip's path fails (`test_ast`, `test_pydoc`).
  - `sys._stdlib_dir` is `None` (`test_sys.test_stdlib_dir`).
- **SQLite's lock directory** gives `database is locked` to a second connection. This is the
  README's own documented fact.

### 4.4 Sandbox and environment facts (EXECUTED)

- **A read-only grant answers `EPERM` before it checks that a path exists.** In the guest,
  `os.unlink` of a missing file under a read-only grant gives `PermissionError` (63, `EPERM`):
  for `/cpy/judge/nonexistent.pyc`, for `/usr/local/lib/python315.zip/x.pyc` and for a path
  under a file. Under the writable root it gives `FileNotFoundError` (44). Native Python gives
  `FileNotFoundError` for all of them. test.support's `forget()` unlinks `.pyc` names in every
  `sys.path` entry, the zip's included, and expects only `FileNotFoundError` or
  `NotADirectoryError`. That breaks 18 tests. Whether this is wasmtime's or the WASI
  specification's intent is not checked (a wasmtime report candidate, or a README fact).
- **A trailing slash.** `open("<dir>/does_not_exist/", "wb")` gives `EINVAL` (28) in the guest
  and `ENOENT` natively (`test_shutil.test_copyfile_nonexistent_dir`).
- **`posix_fadvise`** gives `OSError: [Errno 22] File too large` on this macOS host. That this
  depends on the host is INFERRED: macOS has no `posix_fadvise`. It may pass on Linux, which
  would make it a per-system allowance.
- **The stepped clock.** File times come from the host's real clock, and `time.time()` from the
  judge's clock, which starts at 2026-01-01. So `utime(None)` against `time.time()` differs by
  months (`test_os` 2). Rotation by time fails (`test_logging` 1). Sleeps measure as
  microseconds (`test_time.test_monotonic` with A3). Many time-based tests skip on purpose
  instead ("'slow' conversion took only 1e-06 seconds", `test_int`). A real clock would pass
  these and lose exact fuel (spec 002's clock memo). The judge's clock is the right choice; its
  cost is a class.

## 5. Shards: one session per shard (EXECUTED; `evidence/shard-vs-modules.txt`)

`shards.py plan` split the 552 modules that did not trap into three shards. It balanced them by
fuel less the 1.14 G start. Each shard ran as **one** session, at the default stack, without A3:

| shard | modules | passed | skipped | failed | error | xfailed | fuel | wall (loaded) |
|---|---|---|---|---|---|---|---|---|
| shard 0 | 160 | 10,183 | 1,216 | 9 | 13 | 0 | 352.1 G | 135.7 s (307.5 s in a run before A4, at 365.9 G) |
| shard 1 | 231 | 8,160 | 1,206 | 9 | 67 | 2 | 420.0 G | 100.2 s (179.0 s before A4, at 430.8 G) |
| shard 2 | 161 | 9,154 | 1,496 | 51 | 9 | 3 | 382.1 G (before A4) | 317.3 s |
| **all** | **552** | **27,497** | **3,918** | **69** | **89** | **5** | **1,154 G** | **553 s** |

- **The same outcomes as alone, but for one leak.** Shards 0 and 1 gave exactly the outcomes of
  their modules run one per session, test by test. Shard 2 differs in six tests: the
  `test_profiling` leak of 4.2.
- **One session per shard saves a third of the fuel.** The three shards' modules cost 1,687 G
  run one per session, and 1,154 G run as three sessions. A4 itself saved 13.8 G and 10.8 G
  (the XML parsed per module).
- **Fuel depends on the shard's composition.** It is not the sum of its modules less their
  starts: shard 1 is 66 G above that sum. That is INFERRED to be the collector, with more objects
  alive in one long session. A shard's fuel is a property of its exact list and order, as spec
  050's group fuel is of its grant.
- **Subtests.** A failed subtest has no name in regrtest's XML (the test case element has no
  attributes). The verbose rerun named them. A judge stream must name them itself.

## 6. What the gate costs (INFERRED from the numbers above)

- **CPU.** spec 063's memo measured 0.154 to 0.170 s per G on a quiet Mac, and about 1.5 to 2.5
  times that on a CI runner. So 1,154 G is about 3 minutes on a quiet Mac and **4.5 to 8
  minutes of guest CPU on CI**. That is 1.5 to 2.7 minutes per shard of about 385 G.
- **Host-side waits,** which fuel does not count: the real sleeps of 2 (about 50 s) and file
  I/O. Under this load, `test_tarfile` alone took 194 s in one run, while in another the whole
  160-module shard that holds it took 136 s.
- **Per shard on a 4-CPU Linux runner:** about 2 to 4 minutes of tests, plus spec 063's 45 s of
  job setup. The fetch of the CPython tarball (36 MB, verified) and the unpacking of `Lib/test`
  add an INFERRED half minute. So each shard is about 3 to 5 minutes. That is under spec 063's
  embedding floor of 4.5 to 5.5 minutes, so three shards add no time to the release's critical
  path.
- **Two shards** would be 4 to 7 minutes each, above the floor. Four would spend a Free-plan
  slot for nothing.
- **Fuel caps** at 1.5 times: about 5.3, 6.3 and 5.7 ×10¹¹, 1.73×10¹² in all. That is beside
  spec 050's 2.52×10¹² for numpy and pandas.

## 7. A proposed shape for spec 065

These are proposals for the specification to decide, in spec 050's style.

1. **What runs.** CPython's whole regrtest suite: every module `--list-tests` names, from the
   pinned tarball's `Lib/test` (members only), in the snapshot, through the judge's driver. It
   runs in **three named shards** (`cpython-a`, `cpython-b`, `cpython-c`), one guest session
   each. Each shard is one check, `test_upstream_suite[<shard>]`, with the `fuel` and `passes`
   metrics and spec 050's `fewer` ratchet. The resource set is
   `-u all,-cpu,-gui,-largefile`. That is CPython's own `make test`, less `largefile`, which
   writes multi-gigabyte files.
2. **The test package.** It is staged from `Python-3.15.0.tar.xz`'s members. The check is tied to
   `MANIFEST`'s `pin` line for that tarball and to there being no CPython patch, as spec 050
   ties numpy's and pandas'. It is granted read-only and appended to `sys.path`. The fetch of
   spec 063, `fetch.py --shard`, verifies the tarball and unpacks only `Lib/test`. The tarball
   is already in `downloads/SHA256SUMS`, so the kit needs no new pin.
3. **Not selected (`-x`), each with its reason and closer,** like numpy's `not_selected`: the
   14 modules that fail to load.
   - `test_ctypes`, `test_code`, `test_genericalias`: the stand-in;
   - `test_class`, `test_with`, `test_getpath`: the test modules;
   - `test_ensurepip`, `test_venv`, `test_sysconfig`: not in the zip;
   - `test_ast`: bytecode only;
   - the 4 `sys.executable` ones, unless finding 4.3's decision lands first.

   A collection error is never admitted (spec 050); selecting these out keeps that rule.
4. **Trap entries** for `c-stack-exhausted`. These are `[[trap]]` entries deselected from their
   shard with `-i`, each run alone as a trap check, each a gap that closes with the
   stack-budget specification (4.1):
   - `test_doctest`'s `test_issue35753`;
   - `test_exceptions`' `test_recursion_in_except_handler`;
   - `test_functools`' `test_recursive_pickle`;
   - `test_syntax`'s `test_error_on_parser_stack_overflow`;
   - `test_traceback` as a whole module.
5. **Classes** for the rest: `[[expected]]` entries by test id, with list files, as spec 050's
   Decision 10.
   - **Closed by the README:** `ctypes-stand-in`, `mmap-stand-in`, `bytecode-only-zip`,
     `sqlite-lock`, and two new README facts, `read-only-eperm` and `wasi-path-errno`.
   - **Closed by the owner's question on the test modules:** `no-test-modules`.
   - **Closed by its decision:** `stepped-clock`.
   - **Closed by the fix:** the `test_profiling` leak, unless the plan orders the modules
     around it.
   - 0 classes are left unknown.
6. **The driver's stream.** Write spec 050's kind of stream from a unittest result hook, with a
   node id per test and per subtest. Do not rely on `--junit-xml`. It loses the record in one
   process (A4) and drops subtest names. Then A4 is not needed.
7. **The cost.** About 1.15 T fuel, and 3 to 5 minutes per shard on CI. It runs on Linux in
   the release (spec 063's model), and on darwin-arm64 at every landing like spec 050's groups.

## 8. What spec 065 must decide

1. **The stack.** Does 065 wait for the stack-budget fix, or gate with five trap entries? Which
   fix: a recipe that lowers `Py_C_STACK_SIZE` (build-class, changes the artifacts), a stated
   `max_wasm_stack` in the runner and the embedder contract (wasmtime-py allows at most 2 MiB
   today), or both. This is the one real defect the suite found.
2. **`sys.executable`.** Empty, a placeholder file, or documented as is. The answer moves 5
   modules between not-selected and selected, and A3 must not be a judge-only fiction.
3. **CPython's C test modules** (`_testcapi` and the others). Leave them out, with about 50
   failures and 500 skips admitted; or build them into a test-only binary the judge alone uses.
   This parallels question 89 for numpy and is the owner's.
4. **The stand-ins.** Should A1's `_reset_cache` move into `recipes/ctypes_stand_in/` (a
   product change of one line), or stay a driver adaptation?
5. **Isolation.** Accept one session per shard with the order fixed and the leak admitted. Or
   split the leaking pair across shards. Or pay about 46% more fuel for one session per
   module (1,687 G against 1,154 G).
6. **The plan and its stability.** A shard's fuel depends on its exact list. Adding a module, or
   upstream adding a test file at a re-pin, is a judge change with its numbers, as spec 050's
   groups are.
7. **Systems.** Linux only, as the package shards are, or one shard on Windows and macOS too.
   CPython's own suite is the widest probe of the guest's file system there is. The errno facts
   of 4.4 may differ by host, which would need allowances per system.
8. **The interpreter options.** CPython's CI runs with `-W error -bb`; this research did not try
   them.
9. **Upstream reports to draft:** the unguarded `_testcapi` imports; the `--junit-xml` writer in
   one process; the deep-recursion tests that skip on Emscripten but not on WASI. And for
   wasmtime: `EPERM` before `ENOENT`, and `EINVAL` on a trailing slash.

## Addendum, 2026-10-18: runs made while drafting spec 065 (EXECUTED)

Made by spec 065's drafting agent on the same frozen set, one guest at a time, through the same
runner (`run_one.py`, adapted as `probe_run.py`) and a driver with two switches
(`probe_drive.py`); they ran from the main tree's `build/reviews-evidence/065-spec/`, beside a
copy of the memo's stage. Records: `evidence/spec-065-drafting/` (`sessions.jsonl`; the raw runs in the
main tree's `build/reviews-evidence/065-spec/runs/`). Spec 065's Decisions 2, 8, 10 and 12 rest on
them.

- **`sys.executable` empty.** With `sys.executable` and `sys._base_executable` set to `""` before
  regrtest imports anything, `test_time`, `test_calendar`, `test_strptime`, `test_os.test_posix`,
  `test_platform` and `test_sys` in one session (4.90 G fuel) give 44/68/56/37/33/43 passed, the
  same as A3, with `test_monotonic`, `test_posix_fadvise` and `test_stdlib_dir` the only failures.
- **`-W error`.** Seven modules (`test_json`, `test_datetime`, `test_tempfile`, `test_pathlib`,
  `test_zipimport`, `test_codecs`, `test_unittest`) in one session, with and without the driver
  setting the warnings filter to `error`: 3,236 passed, 935 skipped and the same 2 failures both
  ways; 47.11 G and 47.15 G fuel. `-bb` cannot be set: `sys.flags.bytes_warning` is 0 and fixed,
  and the bootstrap refuses `-b`.
- **The guest's answers** (`probe_c.py`, both binaries): `sys._stdlib_dir` is
  `/usr/local/lib/python315.zip`; `platform.libc_ver()` raises `FileNotFoundError`;
  `os.chmod(f, S_IREAD)` succeeds, `st_mode` is `0o100000`, and a write after it succeeds;
  `open("/tmp/nope/", "wb")` raises `OSError` `[Errno 28]`; `os.unlink` of a missing path under
  the read-only `/usr/local/lib` raises `PermissionError` `[Errno 63]`.
- **The failing tests by the ids a stream names** (`verbose_ids.py` over `runs-verbose/`): 162 ids,
  plus `test_doctest`'s one error from the hunt, 163 in all. The XML's nameless subtest entries are
  eight `test_io`, two `test_mmap` and three `test_bdb` subtests, and three `test_pdb` doctest
  examples that the XML did not record at all. `test_dbm_sqlite3`'s one failure is the missing
  permission bits above, not the SQLite lock. `allowances.py` sorts them into spec 065's groups
  and classes (`allowances.tsv`).
- **A plan in four groups** (`plan065.py`, `plan/`): the file-system modules in `cpython-fs` (50
  modules, 223 G before the composition effect), the rest balanced by fuel against spec 063's Linux
  upstream shards into `cpython-a` (209, 219 G), `cpython-b` (141, 279 G) and `cpython-c` (142,
  338 G); `test_monitoring` last in its group and apart from `test_profiling`. Not run as groups:
  the builder's first run sets their numbers.

## What it decides

- CPython's own suite runs in the guest through regrtest's own `main()`, with four small
  adaptations and no change to the artifact set. It passes 27,503 tests in 1.7 T fuel run one
  module per session, or 27,497 in 1.15 T as three sessions.
- CPython's WASI skips cover what WASI lacks. What fails has eleven causes, each named. One is a
  real defect: C-level recursion traps the guest instead of raising `RecursionError`.
- Three shards of about 385 G each fit spec 063's release at 3 to 5 minutes each.

## One line

CPython's own tests run in the guest: 27,503 of them pass, every failure falls in one of eleven
named classes, and they found that a recursive `repr` kills the guest instead of raising
`RecursionError`.
