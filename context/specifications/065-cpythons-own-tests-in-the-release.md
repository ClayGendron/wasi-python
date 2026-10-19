# 065 — CPython's own tests in the release

- **Status:** **built 2026-10-19; build review passed once F1 to F3 were fixed; rebased onto main
  `08de0c8` (063 landed) and re-judged on its set** (Landing notes, last section). Confirmed for
  build at `75823c9`; built first on spec 063's branch head `1488377`. Before that: drafted 2026-10-18; revised the same day against its pre-build review
  (`065-cpythons-own-tests-in-the-release-spec-2026-10-18.md`, held in the session's scratchpad
  with its probes and runs; the lane copies it to `../reviews/`). The review said "ready once F1 to
  F6 are written in". F1 to F12 are written in as the lane ruled; the Disposition section at the end
  says where. The confirmation round
  (`065-cpythons-own-tests-in-the-release-spec-confirmation-2026-10-18.md`, beside the review) left
  C1 to C8 open: C1 to C6 and C8 are written in below, C7 is spec 071's edit (the Disposition's last
  part). Drafted on
  `spec/065-cpythons-own-tests-in-the-release` from main `e21623e`, rebased onto main `7d377dd`
  (0.1.0a6 tagged, spec 046 landed). It builds after spec 063 lands, on 063's shards, plan file,
  package list, fetch mode and gather.
- **Owner:** Clay Gendron
- **Kind:** the judge only. **Not build-class.**
  - **New:**
    - `tests/upstream/python.toml`: CPython's configuration: the runner, the grant, the
      resources, the groups, what is not selected, the trap entries, the classes, the deselection,
      environment and host entries (Decision 21);
    - `tests/upstream/python/<group>.txt`: the plan, one module per line in run order, for the
      five groups;
    - `tests/upstream/regrtest_drive.py`: the guest-side driver;
    - `tests/upstream/expected/cpython-*/<class>.txt`: 25 class lists, 119 test ids;
    - 37 entries in `tests/known_gaps.toml` (25 classes, 9 trap entries, 1 deselection entry, 2
      environment entries);
    - two upstream facts sheets under `context/upstream/` (Decision 20).
  - **Changed:**
    - `tests/harness/upstream.py`: a second runner kind (regrtest), one stage and one grant per
      family, the regrtest stream, the module universe, the named entries, a budget per family;
    - `tests/checks/test_v1_3_upstream_suites.py`: the needs per runner, and the checks of the
      named entries (Decision 21);
    - `tests/harness/shards.py`: a trap's group named in its entry; the entries' checks go with
      their group;
    - `tests/upstream/fetch.py`: `--shard` fetches the trees of the families the shard runs;
    - `tests/upstream/packages.toml`: `python` becomes `suite`;
    - `tests/release_shards.toml`: six existing shards gain CPython groups; no shard is added;
    - `tests/harness/guest.py`: the judge answers `clock_res_get` (the build's departure; spec 002's
      dated line), guarded by a check in `tests/checks/test_v1_2_portable_and_sealed.py`;
    - `tests/harness/scoreboard.py`: the "not machine-checked" line, and one line naming the open
      trap entries that did not trap on this host (Decision 1);
    - `tests/harness/gather.py`: one printed line naming the open trap entries that trapped on no
      system of the release (Decision 1); it is not a reason to be red;
    - `tests/checks/test_v1_2_hostile_guest.py`: its `_version()` helper reports a missing artifact
      set as blocked, not failed (Decision 22);
    - `tests/unit/test_upstream.py`, `tests/unit/test_shards.py`, `tests/unit/test_fetch_trees.py`;
    - `README.md`, `CHANGELOG.md`, `AGENTS.md` (rule 4), `context/progress/README.md`, one dated
      line in spec 063, `context/roadmap.md`.

  **Why not build-class.** It touches no file under `scripts/` or `recipes/`, no line of
  `downloads/SHA256SUMS` (the CPython tarball is already pinned, line 16), and not the release
  workflow: the CPython groups join shards that already exist, and 063's matrices list shards, not
  groups, so every matrix of `release.yml` is unchanged and 063's scan passes as it stands
  (Decision 7; the review, READ). It rebuilds nothing and changes no artifact. The `/cpython` grant
  is a preopen the judge makes, not a guest import or export. It still changes what the release
  judges, through the plan file, so the lane asked for a pre-build review, and the release-only
  risk is why criterion 12's branch dry run is required.
- **Depends on:**
  - **063** (the release judges in parallel shards; confirmed for build, building now, its branch
    at `0815007` after two branch dry runs). 065 builds on its `--shard`, `tests/release_shards.toml`,
    `tests/upstream/packages.toml` (where `python` is `later` with 065 as its closer), `fetch.py
    --shard`, and the gather's G4 and G5. 063 lands first.
  - **050** and **051** (the upstream mechanism: groups, `passes` and its `fewer` ratchet, trap
    entries, classes by id, gaps, the stream, the session cache, the acceptance refusal), and
    **002** (checks, gaps, needs, the stepped clock of its Decision 9), **020** (a source tree is
    its tarball plus the recorded patches; CPython carries none), **017** (read-only grants),
    **052** (the serial verdict of record).
  - **In flight, with an order rule each:**
    - **071** (deep recursion raises `RecursionError`; drafted at `2265b90`). Its C-stack window
      closes the four `test_recursive_pickle` trap entries. The other five trap entries close
      with its owner question, 102 (Decision 1). If 071 lands first, 065's builder derives on
      071's set: five trap entries, with 071's reasons.
    - **069** (the snapshot pre-imports no package; build-class) moves every snapshot fuel
      number. Whichever of 065 and 069 lands second re-derives: 065's builder takes its numbers on
      069's set, or 069 accepts the CPython groups' fuel with its other growth (Decision 6).
    - **064** (pull requests with required checks) carries the branch's dry run if it has landed
      (Decision 7).
    - **074** (what CPython's suite asks of the product; reserved) closes four classes and six
      modules not selected; it comes before 0.1.0 (Decision 19).
- **Research it stands on:** `../research/2026-10-18-cpythons-own-tests-under-the-runtime.md`
  (called "the memo"), EXECUTED on the frozen set `s-4eb5418a2b1bb553`: regrtest's own `main()`
  in the guest, 557 modules one per session, three shards as one session each, variants, the
  trap hunt, the eleven classes. Its addendum and `evidence/spec-065-drafting/` hold the runs made
  while drafting this specification (EXECUTED, 2026-10-18, the same set): `sys.executable` empty,
  `-W error`, the guest's `chmod`, trailing slash and read-only `unlink`, the plan, and every
  failing test by the id the stream will write. **The pre-build review's runs** (EXECUTED, the
  same snapshot and zip): the plan's four groups as four sessions under `-W error` and
  `--fail-env-changed`, the trap hunts by full id, `test_monitoring` with and without its C API
  class, the environment warnings, and the `M`-line candidates. Also spec 063's memo and its second
  branch dry run, 39182550825 (job times; READ, `gh run view`).

## The problem

The owner decided question 99 on 2026-10-18: "Gate 0.1.0 regardless". Main records it in the
roadmap's paragraph of that evening (`434a811`: "CPython's own test suite gates 0.1.0 (question
99 …)"); the full answer is `### 99, answered` in spec 063's branch's `decisions.md`, which lands
with 063. CPython's own test suite must gate the release, as numpy's and pandas' do since spec 063.

The memo ran it. regrtest runs in the guest, in one process, through the judge's own driver.
27,503 tests pass. Every failure has a named cause, in eleven classes. One cause is a real defect:
C-level recursion (a recursive `repr`, a deeply nested list) ends the whole guest in a wasm trap
instead of raising `RecursionError`. The judge's golden jobs never call that. CPython's suite did.

Today the judge does not run the suite, and the release does not either. `python` is `later` in
`tests/upstream/packages.toml`, closed by this specification.

This specification makes the suite a judge job and a release gate, the way spec 050 made numpy's
and pandas' suites one:
- a ratcheted pass count per group;
- fuel per group;
- every known failure a gap, listed by test id, with its closer;
- every test it does not run, and every host difference, named and on the scoreboard;
- the groups in the release's shards, on Linux in full, and the file-system group on macOS and
  Windows too.

So the next deep-recursion trap is found by the judge, and the release names it.

## Decisions

The first nine are the nine choices the memo's section 8 leaves open (the lane's list), each
decided with its reason. The rest are the mechanism.

1. **The stack: gate now, with nine trap entries.** The suite gates with what traps today. Each
   trapping test is a `[[trap]]` entry, deselected from its group on every host and run alone by
   its own check, a gap until it is fixed. Spec 050's Decision 9 is the mechanism, with the two
   changes below (the name of the place, and the verdict across hosts).

   | id | entry (a full test id, or a module) | group | closes with |
   |---|---|---|---|
   | `c-stack-partial-c` | `test.test_functools.TestPartialC.test_recursive_pickle` | `cpython-a` | spec 071 |
   | `c-stack-partial-c-subclass` | `test.test_functools.TestPartialCSubclass.test_recursive_pickle` | `cpython-a` | spec 071 |
   | `c-stack-partial-py` | `test.test_functools.TestPartialPy.test_recursive_pickle` | `cpython-a` | spec 071 |
   | `c-stack-partial-py-subclass` | `test.test_functools.TestPartialPySubclass.test_recursive_pickle` | `cpython-a` | spec 071 |
   | `c-stack-doctest` | `test.test_doctest.test_doctest.…test_issue35753` (the builder pins the full id) | `cpython-b` | question 102 |
   | `c-stack-exceptions` | `test.test_exceptions.…test_recursion_in_except_handler` | `cpython-b` | question 102 |
   | `c-stack-syntax` | `test.test_syntax.SyntaxErrorTestCase.test_error_on_parser_stack_overflow` | `cpython-c` | question 102 |
   | `c-stack-syntax-lazy-import` | `test.test_syntax.LazyImportRestrictionTestCase.test_error_on_parser_stack_overflow` | `cpython-c` | question 102 |
   | `c-stack-traceback` | the module `test_traceback` | `cpython-a` | question 102 |

   - **Why nine, not five** (the review, F2; EXECUTED). The memo's hunt deselected by bare name,
     which removed every class that inherits a method. By full id: `test_recursive_pickle` traps
     in all four `functools.partial` test classes (with one deselected the module traps at the
     next; with all four, 334 run, 10 skip, none fails: the memo's 324 passes), and
     `test_error_on_parser_stack_overflow` in two (`LazyImportRestrictionTestCase` inherits from
     `SyntaxErrorTestCase`). `test_doctest` and `test_exceptions` are one test each. The review
     counted seven test-level entries; its own runs show eight (4 + 2 + 1 + 1), so nine with
     `test_traceback`.
   - **Full ids, not names.** regrtest's `-i` matches a pattern against a test's id or any of its
     dotted parts, across the whole session; when every pattern is a full id it matches the ids
     exactly (READ, `libregrtest/filter.py`, `_compile_match_function`). A bare name would drop
     same-named tests in other classes and modules, silently. So each entry is a full id, and its
     group passes it as `-i <id>`.
   - **The whole-module entry, and why.** `test_traceback` is in no group's list. By full id the
     hunt finds trap sites in `CExcReportingTests` and `PyExcReportingTests`
     (`test_exception_group_depth_limit`), then a trap that is no test's: it fires right after
     `TestTracebackException_ExceptionGroups.test_comparison`, at the same fuel (6,527,384,023 and
     6,527,390,454), whichever test follows (the review's `tb4` and `tb6`, EXECUTED). INFERRED:
     the deferred freeing of a deep structure, recursing in C. A test-level entry cannot name
     that, so the module is one entry. Its trap check runs the module alone; its group is
     `cpython-a`, where it goes once it is closed.
   - **Where a trap is named.** A trap's finding reads `trap: <cause> at or after <id>`: the
     test the stream last started (Decision 13). It is where the trap surfaced, not necessarily
     its cause.
   - **One verdict for every host (the review, F5).** A wasm frame's size on wasmtime's native
     stack is the code Cranelift makes for that host: aarch64, x86-64 and Windows x64 differ
     (READ, wasmtime-py's `Config.max_wasm_stack`). So a test near the limit may trap on one
     host only, and an entry may not trap on another. The rule:
     - **a trap seen on any host becomes a trap entry deselected on every host**, by a reviewed
       judge change, with its closer;
     - **while the entry exists, its trap check accepts "the named trap, or no trap"** on every
       host. It always fails with one constant finding, `open trap entry: <entry id>`, which its
       gap admits, so the gap is the same on every host. It records what happened as a fact,
       `trap at or after <id>` or `no trap on this host`. It adds a finding, and is red, if the
       guest traps by another cause, runs out of fuel, the entry's test fails or errors without a
       trap, or regrtest ends abnormally (exit 4 if the id names no test any more);
     - **for a whole-module entry** (`c-stack-traceback`; the confirmation's C2), "no trap" means
       the module ran to its `D` line. Its counts (passed, failed, error, skipped) are recorded as
       a fact, and its failures are not judged while the entry is open: where `test_traceback`
       does not trap it has about a hundred failures for want of `_testcapi` (96 errors and 9
       failures at 2 MiB, the memo), and a host with more stack headroom is not a defect. They are
       judged when the entry closes and the module joins `cpython-a` with its classes. The check is
       red only for a trap by another cause, "out of fuel", an `X` line, or a run that ends without
       the module's `D` line or the `E` line;
     - **"no trap" asks to be seen** (the confirmation's C4). The scoreboard prints one line naming
       the open trap entries that did not trap in this run (`trap entries with no trap here: …`),
       and 063's gather prints the entries that trapped on no system of the release. Neither is
       red: a fixed trap is removed by the change that closes it, and these lines tell that change
       it may;
     - **an entry is removed** only by the change that closes it, whose evidence is its own dry
       run's facts: no trap on any host. Its trap check is then absent, and that landing retires
       it with `--retire`.

     Spec 071 needs to know this too: its fix must hold on x86-64 and Windows, not only on the
     lane's Mac. The branch dry run (criterion 12) is the first evidence, and its landing notes
     list each host's traps.
   - **When 071 lands** (spec 050's condition C1, as above): its C-stack window closes the four
     `test_recursive_pickle` entries (071's Decision 7: the window closes `test_recursive_pickle`;
     EXECUTED there for the method, and its builder confirms all four variants). The same landing
     removes them, so the tests run in `cpython-a` again. The other five still trap at 512 KiB,
     each for a reason 071 names: freeing a 1,000-long chain of `_Call` objects (`test_doctest`);
     freeing what the handlers chained (`test_exceptions`); the parser's `MAXSTACK` (both
     `test_syntax` entries); printing and freeing deep exception groups (`test_traceback`). Their
     closer is **question 102**, which 071 asks (a stack the runner owns, or carried patches), in
     `context/questions-for-the-owner.md`.
   - **Closers in the TOML.** The four close with spec 071's file under `context/specifications/`;
     the five with `context/questions-for-the-owner.md`, their reason naming question 102. If 071
     is not on main when 065 is built, the memo stands in for both, and 071 moves them when it
     lands (071, Decision 7), as 050 did for 051.
   - **When `test_traceback` is closed,** it joins `cpython-a`'s list. Its tests that need
     `_testcapi` (96 errors and 9 failures at a 2 MiB stack, almost all for want of `_testcapi`;
     the memo, section 3) join `cpython-a`'s `no-test-modules` class in that landing, each by id.
   - *Why not wait for 071.* The gate is the owner's ("regardless"), and a trap entry is already a
     red-until-fixed gap on the scoreboard, so waiting would only hide the suite's other 28,000
     tests from the release for the length of 071.

2. **`sys.executable`: empty, built by spec 074; until then its four modules are not
   selected.**
   - **What it is today** (EXECUTED, both binaries): `sys.executable` is
     `/usr/local/bin/python.wasm`, a file the guest does not have. So `platform.libc_ver()` raises
     `FileNotFoundError` in any program. `test_time`, `test_calendar`, `test_strptime` and
     `test_os.test_posix` fail to load (they call it at import), and `test_platform.test_libc_ver`
     errors.
   - **Measured with it empty** (EXECUTED, `evidence/spec-065-drafting/sessions.jsonl`,
     `exe-empty`; the driver set `sys.executable` and `sys._base_executable` to `""` before
     regrtest imported anything; one session, 4.90 G fuel):

     | module | passed | skipped | failed | error |
     |---|---|---|---|---|
     | `test_calendar` | 68 | 18 | | |
     | `test_strptime` | 56 | 4 | | |
     | `test_time` | 44 | 20 | 1 (`test_monotonic`: the stepped clock) | |
     | `test_os.test_posix` | 37 | 148 | | 1 (`test_posix_fadvise`, `[Errno 22]`) |
     | `test_platform` | 33 | 6 | | |
     | `test_sys` | 43 | 60 | | 1 (`test_stdlib_dir`, as with today's value) |

     These equal the memo's A3 (an empty file at that path) test for test. `test_sys`, which
     checks `sys.executable` most, is unchanged.
   - **Why empty is clearly better for the guest.** CPython documents it: "If Python is unable to
     retrieve the real path to its executable, `sys.executable` will be an empty string or
     `None`." `platform.libc_ver()` has a branch for exactly that ("sys.executable is not set",
     `Lib/platform.py:191`, READ) and returns `('', '')`. The guest really cannot reach its
     executable: the file is not in any grant. Today's value makes a stdlib function raise in
     every embedder's program. numpy, pandas and matplotlib read `sys.executable` only in an
     error message and a Tk backend (READ, `grep` of the three trees outside their tests). It
     moves 206 passes into the gate (205 in the four modules, and `test_libc_ver`).
   - **Not built here.** The value comes from `program_name` in `recipes/reactor_main.c`; making it
     empty is a recipe change: it changes the snapshot, so every check's fuel and the artifact
     hashes move, and it needs a rebuild and its own pre-build review. Spec 069 changes the same
     recipe now. So the change is **spec 074** (follow-up A, a product specification reserved in
     the roadmap, before 0.1.0; Decision 19), which also selects the four modules and moves their
     two new failures into classes.
   - **Meanwhile.** The four modules are `not_selected`, and `test_platform.test_libc_ver` is
     class `no-executable-file`; both close with spec 074. The memo's A3 (a file planted at that
     path by the judge) is never used: the judge does not run a product that does not exist.
   - `test_posix_fadvise`'s `[Errno 22]` is INFERRED to depend on the host (macOS has no
     `posix_fadvise`). Spec 074 selects the module on Linux and macOS evidence, with a host entry
     if the dry run shows a difference (Decision 21).

3. **CPython's C test modules: left out, named, with the owner's question 101.**
   - **What they reach** (the memo, section 2; the review): `_testcapi`, `_testinternalcapi`,
     `_testlimitedcapi`, `_testbuffer`, `_testmultiphase` and the `xx*` modules are absent
     (`--disable-test-modules`, `scripts/steps/20_cpython.sh:16`). That skips about 500 tests and
     11 modules whole; keeps 3 modules from loading (`test_class`, `test_with`, `test_getpath`: an
     unguarded import); errors 3 tests (`test_call`'s `test_margin_is_sufficient`, and in
     `test_inspect` one CLI test and `test_c_cleandoc`, which returns `unittest.skip(…)` instead of
     raising it, an error under `-W error`, Decision 8); and makes `TestCApiEventGeneration` skip in
     `setUp`, which would fail 45 other `test_monitoring` tests (Decision 5).
   - **Here.** The three modules are `not_selected`. The three errors are class `no-test-modules`
     (Appendix A). `TestCApiEventGeneration`'s five tests are a deselection entry (Decision 21).
     Each closes with `context/questions-for-the-owner.md`, question 101. Skips are upstream's own
     outcomes, not class members.
   - **Question 101** (added by this specification): should question 89's judge-only binary also
     link CPython's C test modules? Question 89 was answered for numpy's: "(a), a judge-only binary
     linked with numpy's test modules, never shipped: a later build-class specification." CPython's
     need a different build of CPython itself (`--enable-test-modules`), which is a new build
     output, so the choice is the owner's, as 89's was. The agent recommends yes, in the same
     later specification. 065 builds without the answer.

4. **A1, `_reset_cache`: in the driver now, by wrapping `clear_caches`; spec 074 moves it into
   the stand-in.**
   - **Why it is needed at all.** regrtest's `clear_caches()` calls `ctypes._reset_cache()` on
     whatever `ctypes` is in `sys.modules` after each module (`libregrtest/utils.py:254–259`,
     READ). The product's stand-in has no such function, so without A1 every module "failed
     (uncaught exception)" (the memo). It is needed after spec 069 too: 35 files of `Lib/test`
     outside `test_ctypes` import `ctypes` themselves (`test_builtin`, `test_bytes`,
     `test_memoryview`, `test_gc`, …; READ, `grep`), so the stand-in is in `sys.modules` once any of
     them has run, pre-import or not.
   - **How, on both snapshots** (the review, F9). The drafting driver patched `ctypes` only if it
     was in `sys.modules` when the driver started; on 069's snapshot it is not, and the first
     module that imports it would break every later one. So the driver wraps
     `test.libregrtest.utils.clear_caches`: before calling the original, it gives the `ctypes` then
     in `sys.modules`, if any, a no-op `_reset_cache` when it lacks one. The driver never imports
     `ctypes` itself, so no test sees it pre-imported. The name to wrap is
     `test.libregrtest.single.clear_caches`: `single.py` imports it by name and calls it after each
     module (`single.py:23, 205`, READ by the confirmation; EXECUTED there, a wrap of it ran
     `cpython-b` and `cpython-c` with no uncaught exception). A unit check of the driver's source
     names it.
   - **Harmless in the product, but not free.** A no-op `_reset_cache` claims nothing false: the
     stand-in keeps no cache. But it changes the stdlib zip's bytes and the snapshot, so the
     artifact hashes and every snapshot check's fuel move, and it would make 065 a recipe change
     with a rebuild, beside 069's. It is a private hook of CPython's own test runner: in the whole
     stdlib only `ctypes` defines it and regrtest calls it (READ, `grep`).
   - **So:** the driver keeps A1, with its reason in the driver and in `python.toml`'s header, as
     050's pytest options are adaptations of the runner. Spec 074 puts `_reset_cache` in
     `recipes/ctypes_stand_in/` with its other stand-in changes, and deletes A1 from the driver in
     the same landing (a judge change it carries).
   - **The memo's other adaptations.** A2 (the driver makes `/tmp` in the fresh writable root)
     stays: it is the judge's environment, as 050's. A3 is never used (Decision 2). A4 is gone:
     the driver's own stream replaces regrtest's XML (Decision 9).

5. **Isolation: one session per group, in a fixed order; nothing named is admitted as a cascade;
   environment changes are seen in every module.**
   - **Measured** (the memo, section 5): two of three one-session shards gave exactly the outcomes
     of their modules run one per session, test by test. The third differed in six tests: a later
     `test_profiling` failed with `ValueError: tool 2 is already in use`. The review's four group
     sessions gave Appendix A's ids exactly, so the plan's composition moved no outcome (EXECUTED).
   - **The cause, now read** (the review, F1; READ, `test_monitoring.py:122–139, 2598–2601`).
     `MonitoringTestBase.setUp` registers three monitoring tools, and only `tearDown` frees them.
     `TestCApiEventGeneration.setUp` calls `super().setUp()` and then imports `_testcapi`, which
     raises `SkipTest`. A skip in `setUp` runs no `tearDown`, so the tools stay registered, and
     every later `MonitoringTestBase` test fails its own `setUp` assertion (`'test
     TestCApiEventGeneration' is not None`), in the module and after it.
   - **So the class goes, and the five tests are deselected** (the lane's ruling on F1). The draft
     admitted those 45 failures as a class, `monitoring-tool-left`. But they fail in `setUp`, before
     their bodies run, so any regression in `sys.monitoring` (line, instruction, branch and local
     events, the optimizer) would fail the same way, with the same message, and sort into the
     class: the class would hide the subsystem. With the five `TestCApiEventGeneration` tests
     deselected, `test_monitoring` alone gives 93 run, 0 failures, 5 skipped (the review's
     `mon-ignore`, EXECUTED, against 98 run, 45 failures, 4 skipped): 39 more tests pass and
     test their bodies. The deselection is a named entry with its ids, reason and closer, a gap on
     the scoreboard (Decision 21). Criterion 2's stand-in shows a `sys.monitoring` regression is
     now red.
   - **The order rule stays as cheap defence.** `test_monitoring` is the last line of its group's
     list, and `test_profiling` is in another group, so a tool left registered by any future skip
     can reach no later module. The rules check enforces both (Decision 16).
   - *Not one session per module:* it costs about 46% more fuel (1,687 G against 1,154 G, the
     memo) for the same outcomes.
   - **Environment changes, in every module** (the review, F4). The driver passes
     `--fail-env-changed`, as CPython's own CI does (`--fast-ci`, READ). But regrtest marks a module
     `ENV_CHANGED` only when its state is unset or `PASSED` (`result.py:178–180`), and a run with any
     failure exits 2, never 3 (`results.py:84–98`), so in a module with a failing test an
     environment change shows in neither the state nor the exit code. The draft said the memo's
     shard sessions had none; that rested on a grep for a summary line a `FAILED` module never
     reaches. They had one: `sys.path was modified by test_bdb` (the memo's
     `runs-shards/*.err`), and the review's sessions show it for `test_doctest` in `cpython-b` and
     `test_bdb` in `cpython-c` (EXECUTED, stderr). Both are side effects of `read-only-eperm`:
     `test.support`'s `forget()` raises before the test restores `sys.path`. regrtest restores the
     saved items afterwards, so nothing leaks today; the next change in a failing module would not
     be seen. So:
     - the driver reads `test.support.environment_altered` after each module and writes it on the
       module's `D` line (Decision 13), whatever the state, **with what changed**: the first line
       of each warning regrtest printed during the module;
     - an altered environment is a group finding, unless an `[[environment]]` entry names that
       module **and that kind of change**, with its reason and closer (Decision 21): `sys.path` in
       `test_doctest` (`cpython-b`) and in `test_bdb` (`cpython-c`) today, closed with
       `read-only-eperm`'s wasmtime facts sheet;
     - **why the kind matters** (the confirmation's C1, READ). Every cause regrtest knows sets the
       same flag: a saved resource that differs (`save_env.py:347–356`: `sys.path`, `os.environ`,
       the working folder, the warnings filters, …), an unraisable exception (`utils.py:133–135`),
       an uncaught thread exception (`utils.py:157–159`), a file left behind (`utils.py:518–519`).
       Under `-W error` an unclosed file's `ResourceWarning` becomes an unraisable exception. An
       entry that named only the module would admit any of them in `test_bdb` or `test_doctest`.
       Every cause goes through `test.support.print_warning`, so the driver records its first line
       (EXECUTED by the confirmation on main's set `s-ff5246a2c2f1a52b`: exactly `sys.path was
       modified by test_doctest` and `… by test_bdb`, every other module of both groups `kept`).

6. **The plan is a judge change, with its numbers.** A group's fuel depends on its exact list and
   order: one long session keeps more objects alive (the memo: one shard 66 G above the sum of its
   modules). So:
   - adding, moving or reordering a module is a judge change, re-measured by its first run, with
     `--accept-judge`, and `--accept-growth` or `--accept-fewer-passes` as the numbers move;
   - a re-pin of CPython that adds or removes a module turns every CPython group red until the plan
     names it (Decision 14, the universe check), so it cannot be left out by accident;
   - the plan lists are judged files; AGENTS.md rule 4 names them beside the allowance files.
   - **069's order rule.** 069 moves every snapshot run's fuel (no numpy pre-imported), and may
     move outcomes (a test that imports numpy then pays its import). Whichever lands second
     re-derives: 065 on 069's set (its first run sets the baseline), or 069 accepting the CPython
     groups' fuel with its other growth and explaining any outcome that moves.

7. **Systems: Linux in full; the file-system group on macOS and Windows too; no job added.**
   - **The groups** (Decision 10): `cpython-fs` holds the modules that probe file-system semantics;
     `cpython-archives` the archive and compression modules, whose cost is the host's file I/O;
     `cpython-a`, `-b` and `-c` hold the rest.
   - **063 as it stands** (READ, its branch at `0815007`, `tests/release_shards.toml`; its second
     branch dry run, 39182550825, job times by `gh run view`). Since this was drafted, 063 added an
     `own-runner` shard on all three systems and took `own-rest` off Windows: 18 judge jobs and 3
     `verify` jobs run at once. In that run the Linux upstream shards took 73 to 198 s each, the
     macOS `upstream-macos` 86 s, the Windows `upstream-windows` 123 s, and the longest legs were
     `own-embedding` on Linux (281 s) and `own-guest` on macOS (266 s); `own-rest` on macOS waited
     about 50 s for a macOS slot. Each time is the job's, setup and fetching included.
   - **The shards after 065.** Each CPython group joins an existing shard, chosen by those job
     times; `upstream-groupby`, already the longest upstream shard, takes none.

     | shard (063) | job time in 39182550825 | groups after 065 | systems | added (INFERRED) | job time after (INFERRED) |
     |---|---|---|---|---|---|
     | `upstream-groupby` | 198 s | pandas-groupby | linux | none | 198 s |
     | `upstream-frame` | 114 s | pandas-frame, **cpython-b** | linux | about 325 G | 210 to 245 s |
     | `upstream-numpy-a` | 121 s | numpy-core, numpy-lib, **cpython-a**, **cpython-fs** | linux | about 305 G, 27 s of sleeps, file I/O | 260 to 315 s |
     | `upstream-numpy-b` | 73 s | numpy-others, pandas-reshape, **cpython-archives** | linux | about 165 G, archive I/O | 185 to 265 s |
     | `upstream-pandas-small` | 107 s | the five small pandas groups, **cpython-c** | linux | about 345 G, 22 s of sleeps | 225 to 265 s |
     | `upstream-macos` | 86 s | numpy-lib, **cpython-fs** | macos | about 60 G, 27 s of sleeps, file I/O | 175 to 240 s; **bound 300 s** |
     | `upstream-windows` | 123 s | pandas-io-parser, **cpython-fs** | windows | about 60 G, 27 s of sleeps, file I/O | 225 to 400 s; **bound 360 s** |

     - *Fuel:* the review's four sessions (`cpython-a` 246.3 G, `-b` 325.3 G, `-c` 344.0 G, the
       unsplit file-system group 219.7 G, with `-v` and a second small grant), split by the memo's
       per-module fuel (`cpython-archives` 165 G, `cpython-fs` 59 G). *Rate:* the dry run's Linux
       upstream shards spent about 0.2 to 0.3 s per G of fuel, setup aside. *Fetching:* about 30 s
       more for the CPython tarball (36 MB, verified, unpacked), 40 s on Windows. *Sleeps:* the
       stepped clock does not shorten `poll_oneoff` (the memo): `test_os.test_os` and `test_shelve`
       in `cpython-fs`, `test_sched` in `cpython-c`.
     - *File I/O is not fuel* (the review, F8; EXECUTED on a loaded Mac): the unsplit file-system
       group took 194 s for 220 G (0.88 s per G, against 0.17 to 0.18 for the other groups), and
       `test_tarfile` alone 218 s for 63 G. That is why the archives are their own group, run on
       Linux only in the release.
     - **The critical path.** The judge stage was 4.7 minutes in the dry run. The slowest shard
       after 065 is INFERRED at 4.4 to 5.3 minutes on Linux, so the stage grows by 0 to about 0.6
       minutes; a dry run about 20 to 23 minutes.
   - **Why merge, and not new shards.** At the fan-out 063 runs 21 jobs (18 judge, 3 `verify`)
     against Free's 20, and 6 macOS jobs against Free's 5 (one already waits). New Linux shards
     would make more jobs wait, and would add matrix legs to `release.yml`, making this
     build-class. A separate macOS shard would be a seventh macOS job. Merging adds no job, no
     macOS job and no workflow change.
   - **Why the file-system group on macOS and Windows, and the archives on Linux only.** The memo
     calls CPython's suite "the widest probe of the guest's file system there is". `cpython-fs`
     holds that probe: `os`, `shutil`, `pathlib`, `tempfile`, `glob`, `io`, `stat`, the path
     modules, `sqlite3`, `dbm`, `shelve`, `importlib`, `logging`'s file handlers, `mmap`. macOS is
     where the lane accepts, so its fuel there is compared with the lane's to 1e-4. Windows is where
     the host's file system differs most (spec 058). The archive modules (`test_tarfile`,
     `test_zipfile`, `test_zipfile64`, `test_zipimport`, `test_zipimport_support`, `test_zipapp`,
     `test_gzip`, `test_bz2`, `test_lzma`) are mostly the host's I/O (Windows is unmeasured, and
     the dry run's `upstream-windows` already spends 123 s on 89 G); they run on Linux in the
     release and on darwin at every landing.
   - **The bounds, and what happens past them** (the review, F8). `upstream-macos` within 300 s
     and `upstream-windows` within 360 s of job time, recorded by criterion 12. If either is
     exceeded, the builder moves the slowest `cpython-fs` modules on that leg (by the job log's
     per-module lines, regrtest's own) to a Linux-and-macOS group by a reviewed judge change with
     its reason; if Windows is still past its bound, `cpython-fs` leaves `upstream-windows`, and
     is Linux and macOS only, by a reviewed judge change with its reason. Neither drops a system to
     get a pass: the outcomes stay the same, only the time moves (063, Decision 18 allows a system
     to leave a shard as a judge change with its reason).
   - **macOS fuel.** If `cpython-fs` on a CI macOS runner differs from the lane's fuel by more than
     the ratchet's 1e-4, the builder finds the module that moves (each alone, on both), and moves
     it from `cpython-fs` to a Linux-only group by a reviewed judge change with its reason. Fuel is
     ratcheted on darwin-arm64 only (063, Decision 8).
   - **One verdict for every host.** A grant carries its host folder's semantics, and a wasm frame
     its host's stack cost. A test or a module whose result depends on the host would make 063's G5
     red (each group's `passes` and `passed_digest` equal in every record and to the lane's). The
     darwin and Linux hosts differ at least in case sensitivity (APFS, as the lane uses it, folds
     case; ext4 does not), and CPython's tests probe it (INFERRED; for example
     `os_helper.fs_is_case_insensitive`). Traps follow Decision 1's rule; every other difference
     is a host entry (Decision 21), recorded per system, on the scoreboard as a gap. None exists
     today: the memo and the review ran on darwin only. Each is added from the dry run's records,
     by a judge change the review sees before landing. A host difference is never admitted by a
     class on one system, and a system is never dropped from a shard to get a pass.
   - **The branch's dry run, before landing.** The owner's answer to question 98 covers pushing a
     specification's branch to GitHub to dispatch a dry run on it, as 063's builder does (spec 063,
     Decision 18). So 065's builder pushes `spec/065-cpythons-own-tests-in-the-release` and
     dispatches `release.yml` on it, and deletes the branch from GitHub after landing. If spec 064
     (pull requests with required checks) has landed by then, the builder opens a pull request
     instead, and its checks are the dry run.
   - **A new CI input** (the review, F11). The CPython tarball becomes an input of the judge
     runners on all three systems (fetched by `fetch.py --shard`, verified against
     `downloads/SHA256SUMS`, unpacked, never run: its test files run only in the guest). The next
     release's threat-model review (constitution §5.6) sees it, beside 063's own new inputs (063,
     Decision 19).

8. **`-W error`: adopted, in the driver; `-bb`: not reachable, said so.**
   - **CPython's CI** runs the suite under `-u -W error -bb -E` (`--fast-ci`,
     `libregrtest/main.py:646–668`, READ).
   - **`-W error`, tried on one module set** (EXECUTED, `sessions.jsonl`, `set-base` and
     `set-werror`): `test_json`, `test_datetime`, `test_tempfile`, `test_pathlib`, `test_zipimport`,
     `test_codecs`, `test_unittest` in one session, with and without the driver setting
     `sys.warnoptions` and the warnings filter to `error` before regrtest imports anything. For
     those seven modules both gave 3,236 passed, 935 skipped and the same 2 failures; fuel 47.11 G
     and 47.15 G (+0.08%). So it is cheap, and the driver adopts it.
   - **Over the whole plan it changes one outcome** (the review, F7; EXECUTED, its `cpython-b`
     session). `test.test_inspect.test_inspect.TestRetrievingSourceCode.test_c_cleandoc` returns
     `unittest.skip("requires _testinternalcapi")` instead of raising it (`test_inspect.py:785–789`,
     READ). Without `-W error` it counted as a pass in the memo, having tested nothing; with it,
     `DeprecationWarning: It is deprecated to return a value that is not None from a test case`
     makes it an error. `-W error` is the better judge here. It joins `cpython-b`'s
     `no-test-modules` class, and the upstream facts sheet gains the bug (Decision 20).
   - **What it is not.** The guest's bootstrap refuses `-W` ("unknown option",
     `recipes/reactor_bootstrap.py`, READ), so the filter starts after the snapshot's own imports,
     not before them as the interpreter flag would. A warning numpy raises at its import is not
     made an error. The driver's filter covers everything the suite imports and runs.
   - **`-bb`** sets `sys.flags.bytes_warning`, which is fixed at start-up (EXECUTED: `0` in the
     guest), and the bootstrap refuses `-b`. It needs a product change for a test-only flag, so it
     is not cheap and not adopted. The scoreboard's "not machine-checked" line names it
     (Decision 17).

9. **The driver's own outcome stream, naming subtests; not regrtest's XML.**
   - regrtest's `--junit-xml` loses the whole record in one process (A4: `test_xml_etree` and
     `test_xml_etree_c` swap ElementTree's classes, and the writer fails), and a failed subtest has
     no name in it (the memo, section 5). The memo's 152 failures by XML are 163 by name (EXECUTED:
     `verbose_ids.py` over the memo's verbose reruns): eight `test_io` subtests (`[readinto]`,
     `[readinto1]`) where the XML had four nameless entries, two `test_mmap` and three `test_bdb`
     parameter subtests where it had one each, three `test_pdb` doctest examples it did not record
     at all, and `test_doctest`'s one error, seen once its trapping test was deselected. With
     `-W error`'s one (Decision 8) they are 164; less the 45 the deselection removes (Decision 5),
     119.
   - So the driver writes spec 050's kind of stream from unittest's result hooks and regrtest's
     per-module result (Decision 13), and passes no `--junit-xml`.

10. **The groups: the file-system probe, the archives, and the rest balanced by fuel into
    three.** The plan is `tests/upstream/python/<group>.txt`. The lists come from
    `evidence/spec-065-drafting/plan/` (made by `plan065.py` from the memo's
    `per-module-results.tsv`; EXECUTED), with the drafted file-system list split in two:

    | group | modules | passes (expected) | fuel (measured or estimated) | its Linux shard | cap |
    |---|---|---|---|---|---|
    | `cpython-fs` | 41 | 3,735 | about 60 G | `upstream-numpy-a` | 1.0×10¹¹ |
    | `cpython-archives` | 9 | 1,313 | about 165 G | `upstream-numpy-b` | 2.5×10¹¹ |
    | `cpython-a` | 209 | 5,681 | 246.3 G (the review) | `upstream-numpy-a` | 3.7×10¹¹ |
    | `cpython-b` | 141 | 9,535 | 325.3 G (the review) | `upstream-frame` | 4.9×10¹¹ |
    | `cpython-c` | 142 | 7,870 | 344.0 G (the review) | `upstream-pandas-small` | 5.4×10¹¹ |
    | **all** | **542** | **28,134** | **about 1.14 T** | | **1.75×10¹²** |

    - **`cpython-archives`** is exactly `test_tarfile`, `test_zipfile`, `test_zipfile64`,
      `test_zipimport`, `test_zipimport_support`, `test_zipapp`, `test_gzip`, `test_bz2`,
      `test_lzma`. It has no class: none of its tests fails.
    - **`cpython-fs`** is the drafting list `plan/cpython-fs.txt` less those nine: `test_os.*`,
      `test_shutil`, `test_pathlib`, `test_tempfile`, `test_glob`, `test_posixpath`,
      `test_genericpath`, `test_stat`, `test_filecmp`, `test_fileinput`, `test_shelve`, the
      `test_dbm*` modules, `test_sqlite3`, `test_mailbox`, `test_py_compile`, `test_compileall`,
      `test_importlib`, `test_linecache`, `test_logging`, `test_mmap`, `test_unicode_file`,
      `test_unicode_file_functions`, `test_file_eintr`, `test_fileutils`, `test_netrc`,
      `test_site`, `test_pkgutil`, and every `test_io.*`.
    - **The others** went, largest first, to whichever of `cpython-a`, `-b`, `-c` left its shard
      lightest (by 063's memo's fuel), never putting `test_profiling` with `test_monitoring`. Their
      shards were then chosen by the dry run's job times (Decision 7).
    - **Order:** sorted, then `test_monitoring` moved last (Decision 5). There is no
      `--randomize`: the order is the list's, and regrtest's per-test random seed comes from the
      guest's seeded random, so a group repeats (the memo: `test_json` to the instruction; the
      review: `test_pathlib` twice within 5×10⁻⁷).
    - **Expected passes** are the memo's per-module passes, plus the four trap modules' passes once
      their trapping tests are deselected by full id (73, 93, 324 and 103), plus `test_monitoring`'s
      39 (Decision 5), less `test_c_cleandoc` (Decision 8). The builder's first run counts them
      exactly and explains any difference (criterion 3).
    - Modules skipped whole (231) stay in their groups: they cost little in one session, and one
      that starts running shows as new passes or a new failure.
    - **Caps:** at least 1.5 times the review's measured fuel for `cpython-a`, `-b` and `-c` (it ran
      `cpython-a` at 1.42 and `cpython-b` at 1.38 times the drafted caps, so both are raised), and
      about 1.5 times the estimate for the two split groups. The builder raises any cap below 1.5
      times its first run.

11. **What is not selected, each with its reason and closer.** A module that fails to load is never
    admitted by a class (spec 050's rule for collection errors); it is not selected instead. These
    are the memo's 14:

    | modules | reason | closes with |
    |---|---|---|
    | `test_ctypes` | the `ctypes` stand-in imports, then every use raises (README: "no ctypes") | `README.md` |
    | `test_code`, `test_genericalias` | they name `ctypes.pythonapi`, `py_object`, `Array` at import, which the stand-in lacks | spec 074 (follow-up A; Decision 19) |
    | `test_class`, `test_with`, `test_getpath` | an unguarded import of `_testinternalcapi` | `context/questions-for-the-owner.md` (question 101) |
    | `test_ensurepip`, `test_venv`, `test_sysconfig` | `ensurepip` and `venv` are not in the zip ("no pip, no venv", constitution §3); `test_sysconfig` imports `test.support.venv` | `README.md` |
    | `test_ast` | one module-level line lists the stdlib's folder (`test_ast/test_ast.py:41`), which is a zip; the facts sheet names it as an upstream assumption (Decision 20) | `README.md` |
    | `test_time`, `test_calendar`, `test_strptime`, `test_os.test_posix` | `platform.libc_ver()` at import, and `sys.executable` names no file (Decision 2) | spec 074 |

    regrtest runs only the modules a group lists, so "not selected" means listed nowhere; the
    entries name them, and the universe check (Decision 14) requires every module regrtest knows to
    be in exactly one place.

12. **Known failures are classes, by test id, each one gap: 25 classes, 119 ids.** Spec 050's
    Decision 10, unchanged: an `[[expected]]` entry (`id`, `group`, `outcome`, `match`, `reason`,
    `closes_with`), its members in `tests/upstream/expected/<group>/<class>.txt`, one sorted test id
    per line, the group's failures sorted into the first class whose outcome and `match` fit, a
    class check `test_upstream_class[<group>-<class>]` that is exact (`+id`, `-id`), and an emptied
    class kept as a passing check (condition C1). A subtest's id is unittest's own
    (`<test id> [<msg>]` or `<test id> (<params>)`). An unexpected success is a failure, as
    unittest counts it (`wasSuccessful()`), sorted like one.

    | group | class | outcome | ids | match (proposed; the builder writes it against the stream's own reasons) | closes with |
    |---|---|---|---|---|---|
    | `cpython-fs` | `no-ctypes` | error | 14 | `ctypes is unavailable` | `README.md` |
    | `cpython-fs` | `no-mmap` | error | 31 | `mmap is unavailable\|cannot access local variable 'm'` | `README.md` |
    | `cpython-fs` | `mmap-stand-in-surface` | error | 4 | `module 'mmap' has no attribute\|object\.__new__\(\) takes exactly one` | spec 074 |
    | `cpython-fs` | `sqlite-lock` | error | 7 | `database is locked` | `README.md` |
    | `cpython-fs` | `no-file-modes` | failed | 1 | `error not raised` | `README.md` |
    | `cpython-fs` | `stdlib-zip` | failed | 4 | `Lists differ: \['/usr/local/lib/python315\.zip/\|0 not greater than 0\|TypeError not raised by getline\|\[\] is not true` | `README.md` |
    | `cpython-fs` | `stdlib-zip-error` | error | 2 | `No module named 'c_resources'` | `README.md` |
    | `cpython-fs` | `stepped-clock` | failed | 3 | `No rotated files found\|within 0\.05 delta` | `context/specifications/002-the-progress-harness.md` |
    | `cpython-fs` | `trailing-slash-einval` | error | 1 | `\[Errno 28\] Invalid argument: .*/'$` | the wasmtime facts sheet (Decision 20) |
    | `cpython-a` | `no-ctypes` | error | 1 | `ctypes is unavailable` | `README.md` |
    | `cpython-a` | `no-test-modules` | error | 1 | `get_stack_pointer` | `context/questions-for-the-owner.md` (question 101) |
    | `cpython-a` | `read-only-eperm` | error | 1 | `^PermissionError: ` | the wasmtime facts sheet |
    | `cpython-a` | `stdlib-zip` | failed | 4 | `Lists differ: \[\('te\|pyc'>" != \|raise self\.failureException\(msg\)' not found` | `README.md` |
    | `cpython-a` | `stdlib-zip-error` | error | 1 | `_path_normpath: path should be string` | `README.md` |
    | `cpython-a` | `no-executable-file` | error | 1 | `No such file or directory: '/usr/local/bin/python\.wasm'` | spec 074 |
    | `cpython-b` | `no-ctypes` | error | 1 | `ctypes is unavailable` | `README.md` |
    | `cpython-b` | `no-test-modules` | error | 2 | `No module named '_testcapi'\|deprecated to return a value that is not None from a test case` | `context/questions-for-the-owner.md` (question 101) |
    | `cpython-b` | `read-only-eperm` | error | 2 | `^PermissionError: ` | the wasmtime facts sheet |
    | `cpython-b` | `stdlib-zip` | failed | 4 | `Lists differ: \[\('te\|Items in the first set but not the second` | `README.md` |
    | `cpython-b` | `stdlib-zip-error` | error | 2 | `could not get source code` | `README.md` |
    | `cpython-c` | `no-ctypes` | error | 5 | `ctypes is unavailable` | `README.md` |
    | `cpython-c` | `ctypes-stand-in-surface` | error | 1 | `module 'ctypes' has no attribute 'pythonapi'` | spec 074 |
    | `cpython-c` | `read-only-eperm` | error | 18 | `^PermissionError: ` | the wasmtime facts sheet |
    | `cpython-c` | `stdlib-zip` | failed | 5 | `Failed example:\|Pydoc: Error\|^AssertionError: 1 != 0$` | `README.md` |
    | `cpython-c` | `stdlib-zip-error` | error | 3 | `NotADirectoryError: \[Errno 54\]\|argument of type 'NoneType' is not a container` | `README.md` |

    21 failed and 98 errors. Every id is in Appendix A.
    - **The matches are proposals** (the review, F10; EXECUTED, its `match_check.py`): replayed over
      the drafting evidence's recorded reasons, they place 137 of 163 ids. The rest have an empty
      recorded reason, or a recorded reason that is the last line of unittest's report (a diff line,
      `'lineno'`, `</body></html>`) while the stream writes the first line of
      `format_exception_only` (Decision 13). So the builder writes each `match` against the
      stream's own reasons on its first run (criterion 3); `evidence/spec-065-drafting/allowances.tsv`
      is the ids' evidence, not the reasons'.
    - A `match` may be broad (`^PermissionError: `, since one of `test_bdb`'s reasons is a re-raised
      traceback): the list is exact, so a stranger the match takes shows as `+<id>` and is red, as
      spec 050 notes for its bare `AssertionError: `.

    **The memo's eleven classes, mapped, and each product issue's closer:**
    - `c-stack-exhausted`: the nine trap entries; spec 071 and question 102 (Decision 1).
    - `no-test-modules`: class `no-test-modules` (three ids), the deselection of
      `TestCApiEventGeneration` (five ids), and three modules not selected; question 101
      (Decisions 3 and 5).
    - `ctypes-stand-in`: `no-ctypes` where a call raises: **documented** (README: "no ctypes"; the
      stand-in imports so that numpy and pandas can, and so CPython's tests take it as working
      instead of skipping). In `test_io` this hides the read half of `test_raw_file_io` and
      `test_buffered_file_io` (`byteslike()` calls `ctypes.resize`, `test_io/utils.py:10–25`; the
      review's N2), which spec 074 weighs. `ctypes-stand-in-surface` and two modules not selected,
      where a name is missing at import: spec 074, which decides whether the stand-in names
      `pythonapi`, `py_object` and `Array` so `test_code`, `test_genericalias` and `test_frame`
      load.
    - `mmap-stand-in`: `no-mmap` is **documented** (README: "no mmap"; pandas imports `mmap`
      unconditionally, so the stand-in must import, and CPython's tests then run instead of
      skipping). `mmap-stand-in-surface` (the stand-in lacks `mmap.error` and `ACCESS_DEFAULT`, and
      its class takes no arguments): spec 074. The module stays selected: it has a pass and 20
      skips, and its class keeps guarding the stand-in.
    - `bytecode-only-zip`: `stdlib-zip` and `stdlib-zip-error`, and `test_ast` not selected:
      **documented**, the product's choice since spec 003 (the README gains the consequences,
      Decision 18). `sys._stdlib_dir` is set to the zip (EXECUTED, both binaries); `test_stdlib_dir`
      fails because `os.path.exists` of a module's `__file__` inside the zip is false (READ, the
      test).
    - `read-only-eperm`: **documented** in the README and reported (EXECUTED: `os.unlink` of a
      missing path under a read-only grant gives `PermissionError` `[Errno 63]`; natively
      `FileNotFoundError`). It is wasmtime's answer before any lookup (INFERRED: its preview1 checks
      the grant's rights first), so its closer is the wasmtime facts sheet, which the README cites.
      The two environment entries close with it too (Decision 5).
    - `sqlite-lock`: **documented** (the README's own fact).
    - `no-executable-file`: one class and four modules not selected; spec 074 (Decision 2).
    - `not-in-zip`: three modules not selected; **documented**.
    - `stepped-clock`: the judge's own clock (spec 002, Decision 9): file times come from the host's
      real clock and `time.time()` from 2026-01-01, stepping 1 µs a read. A real clock would pass
      these and lose exact fuel. Its closer is spec 002, which states the choice; it is permanent
      while fuel is exact.
    - `wasi-path-errno`: `trailing-slash-einval`, **documented** in the README and reported
      (EXECUTED: `open("<dir>/missing/", "wb")` gives `OSError` `[Errno 28]`; natively
      `FileNotFoundError`); closer, the wasmtime facts sheet.
    - **New since the memo**, from the stream's names: `no-file-modes`. The memo put
      `test_dbm_sqlite3.ReadOnlyFilesystem.test_readonly_file_write` under the SQLite lock. Its
      cause is that WASI has no permission bits (EXECUTED: `os.chmod(f, S_IREAD)` succeeds,
      `st_mode` is `0o100000`, and a write after it succeeds). **Documented**.

13. **The stream.** The driver writes `/judge/outcomes.txt` in the guest's writable root, outside
    `TMPDIR` so no test's temporary clean-up reaches it, flushing every line. The host reads it
    after the guest returns, as spec 050's Decision 11 does.

    | line | written when |
    |---|---|
    | `L <module>` | before the run: every module regrtest's own discovery names, as `--list-tests` would print them (the same functions, in process) |
    | `C <module>` | a module starts |
    | `S <test id>` | a test starts (unittest's `startTest`) |
    | `R <outcome> <id> -- <reason>` | every test outcome: `passed`, `failed`, `error`, `skipped`, `xfailed`, `xpassed`; for a failing subtest, its own id. Passing subtests are not written. The reason is the first line of the error's own text (`traceback.format_exception_only`: its type and message), at most 200 characters; a skip's reason for a skip |
    | `X <module> -- <reason>` | a module fails to load, or raises outside any test |
    | `D <module> <state> <env>` | a module ends, with regrtest's state (`PASSED`, `FAILED`, `SKIPPED`, `RESOURCE_DENIED`, `DID_NOT_RUN`, `ENV_CHANGED`, …) and `env` = `altered` or `kept`, from `test.support.environment_altered` read after the module, whatever the state; after `altered`, the first line of each `print_warning` regrtest made during the module, `|`-separated (Decision 5) |
    | `M <module> <file> <kind>` | at session end, each `sys.modules` entry whose `__file__` is under `/cpython/`, with `kind` = `product` when the product provides that name (below), else `test` |
    | `E <regrtest exit code>` | last |

    - **`passes`** is the number of `R passed` lines: test-level, as regrtest counts them, without
      host entries (Decision 21). `passed_digest` is over the same ids.
    - **The guard's intent** (the review, F3). A module the product provides must come from the
      product. The driver marks an `M` line `product` when the module's top-level name is in
      `sys.builtin_module_names` or is found by `importlib.machinery.PathFinder` on the product's
      own import path (the stdlib zip and the compiled-in packages); a test's own helper, by any
      name, is `test`. The review's `cpython-c` session shows why: `test_build_details` puts
      `sys.modules["generate_build_details"]` in place before executing a file that is not staged,
      the test skips, and the half-made module stays, with a `__file__` under the grant and a name
      outside `test.` (EXECUTED). That is `test`, not a finding.
    - **The group check's findings** (never admitted by a class): a failure no class takes; an `X`
      line; a `D` state other than `PASSED`, `FAILED`, `SKIPPED`, `RESOURCE_DENIED` or
      `DID_NOT_RUN`; a `D … altered` line whose module and kinds of change no environment entry names; an exit code other than 0 or
      2; a missing `E` line; a trap (`trap: <cause> at or after <id>`, the last `S` or `C` line)
      or "out of fuel"; an `M … product` line; a host entry whose recorded outcome on this system
      differs from what ran; the universe check (Decision 14).
    - The reasons hold guest paths only (`/cpython/…`, `/usr/local/lib/…`, `/tmp/…`).
    - **A builder hazard, seen** (the confirmation's C1, EXECUTED). `support.print_warning` reads
      `print_warning.orig_stderr` off its own global name (`support/__init__.py:1519–1530`), and
      `save_env`, `utils` and `single` import it by name. The driver wraps it in all four places,
      and the wrapper **copies `orig_stderr`**: the confirmation's first wrapper lacked it, so
      `save_env`'s warning raised `AttributeError: 'function' object has no attribute
      'orig_stderr'` and both modules became `UNCAUGHT_EXC`. A unit check of the driver holds it
      (criterion 2).

14. **The universe: every module regrtest knows is in exactly one place.** Each group's `L` lines
    are regrtest's own list (557 modules for 3.15.0, the memo; the review checked the plan's lists
    against it: 557 distinct, no difference, EXECUTED). The group check fails, naming each module,
    unless that list equals the union of the five groups' lists, the `not_selected` modules and the
    whole-module trap entries, with no module in two places. So an upstream module the plan does
    not name, at a re-pin, is red everywhere, and a module the plan names that regrtest no longer
    knows is red too. This needs no extra session: the list is read in each group's own.

15. **Where the tests come from, and how the guest finds them: their own stage and grant.**
    - **The stage, from the verified tarball** (the review, F11). Once per judge run,
      `upstream.Session` stages CPython's tests into their own folder. It reads every member under
      `Python-<v>/Lib/test/` **from the tarball itself** (`pins.source_pair("cpython")`'s tarball,
      whose SHA-256 the tie has just checked), not from the build's working tree, and writes it to
      `<stage>/lib/test/`. So the lane's stage is byte for byte CI's, which the fuel needs (063,
      Decision 5), whatever the build left in `build/Python-<v>` (11 `__pycache__` files today, the
      memo). The record's `left_out` fact lists the tree's files under `Lib/test` that are not
      members, as a warning. Plus `<stage>/judge/regrtest_drive.py` and one `<stage>/judge/<id>.json`
      per group and trap (its modules in order, its `-i` ids, the resources and options), so the
      guest parses no argument list of its own.
    - **Tied to the artifact,** as spec 050's Decision 3: the checks fail (not blocked) when
      MANIFEST's `pin` line for the CPython tarball names another file or hash, or when its
      `recipe` lines for `recipes/patches/Python-<v>/` differ from the repository's (none today;
      `apply_patches.sh:23` exits 0 for an absent patch folder, READ).
    - **The grant.** The stage is granted read-only at **`/cpython`**, and a CPython group gets that
      grant alone. The driver appends `/cpython/lib` to `sys.path`, so every module the product has
      still comes from the product; the `M` lines check it.
    - **Why not inside `/upstream`.** The guest's fuel depends on the whole grant (`Session.prepare`'s
      own comment; 063's memo, section 2: numpy-lib's fuel moved 3.9e-5 with one tree absent, 500
      times the residual). CPython's 1,810 files in `/upstream` would move all eleven numpy and
      pandas groups' fuel. So `upstream.Session` keeps one stage per family, each with every
      package of its family: `/upstream` holds numpy and pandas exactly as today (the same files,
      byte for byte), and `/cpython` holds CPython. Criterion 9 proves the numpy and pandas fuel
      does not move.
    - **The config.** `tests/upstream/python.toml` has `package = "python"`, `component = "cpython"`
      (the source component and its need), `runner = "regrtest"`, `grant = "/cpython"`,
      `resources = "all,-cpu,-gui,-largefile"`, `options = ["--fail-env-changed"]`,
      `warnings = "error"`, `[groups.<name>]` with `list` and `fuel`, `[[not_selected]]` with
      `modules`, `[[trap]]` with `group`, `[[expected]]`, and the entries of Decision 21. numpy's
      and pandas' files gain nothing; `runner` defaults to `pytest` and `grant` to `/upstream`.
    - **The resources.** `-u all,-cpu,-gui,-largefile`: CPython's own `make test` (`--fast-ci`,
      which means `-u all,-cpu`, and `-u-gui`), less `largefile`, which writes multi-gigabyte files
      (the memo).

16. **The rules check, widened.** `test_upstream_files_are_well_formed` also checks, with no guest:
    - every plan list exists for its group, has no duplicate, is sorted except that
      `test_monitoring` is last in its group, and `test_profiling` is not in that group;
    - no module is in two of: the five lists, `not_selected`, a whole-module trap;
    - every trap names a group of its package, and a test-level trap's module is in that group's
      list;
    - every deselection, environment and host entry names a group and modules in its list; a
      deselected id's module is in that group; a host entry records an outcome or state for each
      system its group runs on, from the allowed ones (Decision 21); and each entry has its gap;
    - every closer exists (the memo stands in for spec 074's and 071's files until they exist,
      Decisions 1 and 19);
    - **the budgets, per family:** the `/upstream` family's caps at most 3×10¹² (unchanged); the
      `/cpython` family's group and trap caps at most 2.5×10¹² (1.75×10¹² + 9 × 5×10¹⁰ = 2.20×10¹²
      today);
    - when the tarball is here, every listed module names a `test_*.py` file or a test package
      under its `Lib/test/`;
    - **when the tarball is here, every deselected id exists** (the confirmation's C5): the rules
      check reads the id's module source from the verified tarball's member (parsed with `ast`, not
      run) and finds its class and method, a method inherited from a base class in the same module
      included. A deselected test never starts, so the stream could not show a stale id after a
      re-pin; this does. The same holds for every test-level trap entry's id.

    **The fuel spent** (a review rule, as spec 050's 1.8×10¹²): the CPython group and trap checks'
    recorded `fuel` stays under 1.45×10¹²; each landing's notes sum it and say why if it is over.

17. **The needs, the area and the scoreboard's last line.**
    - The CPython checks need `artifact dir`, `snapshot binary`, `stdlib zip`, `manifest`,
      `wasmtime-py` and `source tree cpython`, not `upstream kit` (regrtest is in `Lib/test`). No
      need is new.
    - They live in `tests/checks/test_v1_3_upstream_suites.py`, area v1.3 (constitution §2.3:
      "every compiled-in package imports and works"; CPython is the base of all of them), marked
      `slow`, so the fast tier skips them and the full judge runs them. Spec 050's acceptance
      refusal (Decision 13) covers them, since it counts the file.
    - **The not-machine-checked line** gains "CPython's tests that need its C test modules
      (number 101) · CPython under `-bb`".

18. **What the README and the CHANGELOG say.**
    - **README, "Measured,"** gains a row: CPython's own tests in the guest (spec 065; regrtest, 542
      of 557 modules in five groups): the accepted passes, the gaps by closer, and the nine tests
      that trap the guest (spec 071 and question 102).
    - **README, the platform's facts,** gain, after the `np.save` sentences: "WASI has no
      permission bits: `os.chmod` succeeds and changes nothing, and `st_mode` carries none. Under a
      read-only grant, removing a path raises `PermissionError` even when the path does not exist,
      and opening a missing path with a trailing slash raises `OSError` (`EINVAL`), not
      `FileNotFoundError` (wasmtime's answers; `context/upstream/<n>-…`). The standard library is
      bytecode in a zip: tracebacks into it show no source line; `inspect.getsource`, `linecache`,
      `pdb` and `pydoc` have no source for it; `os.path.exists` of a stdlib module's `__file__` is
      false, and the zip's path cannot be listed. `sys.executable` names
      `/usr/local/bin/python.wasm`, which the guest does not have, so `platform.libc_ver()` raises
      `FileNotFoundError`." Spec 074 rewrites that last sentence when it lands.
    - **README, *Releasing*** (063's text): "with numpy's, pandas' and CPython's own test suites on
      Linux, and one group of numpy's and pandas', and CPython's file-system group, on macOS and on
      Windows".
    - **CHANGELOG,** under the first unreleased section's *Judge* heading: "**CPython's own tests in
      the judge and the release** (spec 065). The judge runs CPython's own regrtest suite in the
      guest: 542 of its 557 modules in five groups, about 28,000 passing tests, each known failure a
      class by test id with its closer, each test it does not run named, and the nine tests where
      C-level recursion traps the guest (spec 071, question 102) each a gap. The release runs the
      five groups on Linux in its existing upstream shards, and the file-system group on macOS and
      Windows too. `python` now names its suite in `tests/upstream/packages.toml`."

19. **Spec 074 (follow-up A): what CPython's suite asks of the product, before 0.1.0.** A product
    specification, build-class (recipes), reserved as 074 in the roadmap by this specification.
    **It comes before 0.1.0** (the review, F12): it closes four classes and six modules not
    selected in a gate the owner set for 0.1.0, and one of them is a stdlib function that raises
    in every embedder's program today. It carries:
    - `sys.executable` (and `sys._base_executable`) empty (Decision 2), selecting `test_time`,
      `test_calendar`, `test_strptime` and `test_os.test_posix`, with `test_monotonic` in
      `stepped-clock` and `test_posix_fadvise` decided on Linux and macOS evidence;
    - `_reset_cache` in the `ctypes` stand-in, and A1 deleted from the driver (Decision 4);
    - whether the stand-ins name what CPython's tests name at import (`ctypes.pythonapi`,
      `py_object`, `Array`; `mmap.error`, `ACCESS_DEFAULT`), which decides `test_code`,
      `test_genericalias`, `ctypes-stand-in-surface` and `mmap-stand-in-surface`; and whether
      `byteslike()`'s `ctypes.resize` should fail in a way `test_io` skips (the review's N2).

    Until its specification is written, the closers of its classes and modules name the memo (the
    rules check needs a file), and it moves them when it lands, as spec 050 did before 051 existed.

20. **Upstream facts sheets, drafted for the owner.** Under `context/upstream/`, the next free
    numbers (21 and 22, after spec 076's 20), each a `notes.md` facts sheet with its evidence, listed in
    `context/upstream/README.md`; nothing is posted:
    - **CPython's tests in one WASI process:**
      - the `cpython_only` tests that import `_testcapi` or `_testinternalcapi` unguarded
        (`test_class`, `test_with`, `test_getpath`, `test_call.TestRecursion`, `test_inspect`'s CLI
        test, `test_traceback`'s `CExcReportingTests`);
      - `TestCApiEventGeneration.setUp` registering monitoring tools, through
        `MonitoringTestBase.setUp`, before it skips for want of `_testcapi`, so `tearDown` never
        frees them and 45 later tests fail (READ, `test_monitoring.py:122–139, 2598–2601`; EXECUTED,
        the review's `mon-base` and `mon-ignore`);
      - `test_inspect`'s `test_c_cleandoc` returning `unittest.skip(…)` instead of raising it
        (`test_inspect.py:785–789`), a pass that tests nothing, and an error under `-W error`;
      - `test_ast` listing the stdlib's folder at import (`test_ast/test_ast.py:41`), which fails
        where the stdlib is a zip (the review's N1);
      - `--junit-xml`'s writer in one process (A4);
      - the deep-recursion tests skipped on Emscripten and not on WASI (`test_traceback.py:2256`).
    - **wasmtime's read-only and trailing-slash errnos:** `EPERM` before `ENOENT` under a read-only
      grant, and `EINVAL` for a trailing slash on a missing path, each with a two-line reproducer
      and the native answer. Its `notes.md` is the `closes_with` of `read-only-eperm`,
      `trailing-slash-einval` and the two environment entries (the rules check needs a file), and
      the README cites it.

21. **Named entries that are not classes: a deselection, environment entries, host entries.** Spec
    050 has a class for a failure and a trap entry for a trap. CPython's suite needs three more
    kinds of allowance, each in `python.toml` with an `id`, a `group`, a `reason` and a
    `closes_with`, each checked, and each a gap on the scoreboard, so none can be forgotten.
    - **`[[deselected]]`: tests that must not run, by full id** (the lane's ruling on F1). Its
      `tests` are full ids; the group passes each as `-i <id>`. Its check,
      `test_upstream_deselected[<group>-<id>]`, reads the group's cached run and fails with one
      finding per id (`deselected: <id>`), which its gap admits by count and digest; it adds a red
      finding if a listed id ran (an `S` line for it). The builder's first run records each id's
      outcome without the entry in the landing notes. One today:

      | group | id | tests | reason | closes with |
      |---|---|---|---|---|
      | `cpython-b` | `capi-event-generation` | the five `test.test_monitoring.TestCApiEventGeneration.*` tests, by full id (`test_enter_scope_two_events`, `test_fire_event`, `test_fire_event_failing_callback`, `test_missing_exception`, and the one that skips today; the builder lists them from the stream) | needs `_testcapi`; its `setUp` leaves three monitoring tools registered when it skips, which fails every later `MonitoringTestBase` test (Decision 5) | `context/questions-for-the-owner.md` (question 101) |

      It closes when the judge runs these tests with `_testcapi` (question 101's binary) or upstream
      frees the tools on skip; either change removes the entry.
    - **`[[environment]]`: modules allowed to leave the environment altered** (the lane's ruling on
      F4; the confirmation's C1). Its `modules` are module names, and its `changes` the kinds of
      change it admits, each matched against the start of a recorded warning line (`"sys.path"`
      matches `sys.path was modified by …`). The group sorts each `D … altered` line into the entry
      that names its module; a recorded line that none of the entry's `changes` match stays a group
      finding. Its check, `test_upstream_environment[<group>-<id>]`, is exact like a
      class check: one finding per module that altered it (admitted by its gap), `+<module>` for an
      altered module the entry does not name, `-<module>` for a named module that kept it (the entry
      then shrinks, as an emptied class does). Two today:

      | group | id | modules | changes | reason | closes with |
      |---|---|---|---|---|---|
      | `cpython-b` | `sys-path-doctest` | `test_doctest` | `["sys.path"]` | `sys.path was modified`: `test.support`'s `forget()` meets `PermissionError` under the read-only grant before the test restores `sys.path` (`read-only-eperm`) | the wasmtime facts sheet |
      | `cpython-c` | `sys-path-bdb` | `test_bdb` | `["sys.path"]` | the same, in `test_bdb` | the wasmtime facts sheet |

    - **`[[host_dependent]]`: a result that differs by host, recorded per system** (the lane's
      rulings on F6). Either a `test` (a full id) with a test outcome per system (`passed`,
      `skipped`, `failed`, `error`), or a `module` with a module result per system (`PASSED`,
      `FAILED`, `SKIPPED`, `RESOURCE_DENIED`, `DID_NOT_RUN`, `ENV_CHANGED`, `load-error`), under the
      keys `darwin`, `linux` and `win32` for each system its group runs on (063's platform
      prefixes). The verdict:
      - on each system the result must equal that system's recorded one exactly; any other is a
        group finding. So a pass that becomes a failure on any host is red: nothing is accepted
        that was not seen on that host;
      - a test entry's outcome is left out of `passes`, `passed_digest` and class sorting on every
        host; a module entry's tests are left out of the group's `passes` and `passed_digest` on
        every host, and the entry records instead, per system, the module's own pass count and
        digest (`passes`, `passed_digest` under each system's key), checked exactly on that system
        (the confirmation's C3), so a pass that becomes a skip or a test that vanishes is still red;
        on a system whose recorded result is `PASSED` or `FAILED` its failures still sort into
        classes; an `X` line or `D … ENV_CHANGED` for that module is accepted only on the systems
        that record `load-error` or `ENV_CHANGED`. So G5's one verdict holds, and each host is
        still judged on what it really does;
      - its check, `test_upstream_host[<group>-<id>]`, fails with one constant finding naming the
        entry and its per-system results (`host entry <id>: darwin=… linux=… win32=…`), admitted by
        its gap, and adds a red finding if this system's result, or a module entry's pass count or
        digest, differs. So each host entry is on
        the scoreboard under its closer, and their number shows in the gap count;
      - its closer is `README.md` when the difference is the host's genuine semantics (the README
        then states it), or the wasmtime facts sheet when it is wasmtime's choice;
      - **a trap on one host is not a host entry:** it is a trap entry on every host (Decision 1).

      None today. Each is added from the branch dry run's records by a reviewed judge change.
    - **Shards.** Each entry's check goes with its group in 063's selection, as a class check does
      (the map `plugin.upstream_scopes`).

22. **The hostile-guest helper reports blocked, not failed, without an artifact set** (the
    review's "Fast tier" section; the lane's ruling, since spec 070 is closed). In
    `tests/checks/test_v1_2_hostile_guest.py`, `_version()` reads MANIFEST after
    `assert directory is not None`. With no artifact set, `test_matplotlib_data_is_granted_read_only`
    and `test_usr_local_lib_holds_only_the_zip` (plain and snapshot: four results) therefore **fail**
    on that assertion instead of being blocked by the need, as every other check is (EXECUTED by the
    review: `uv run pytest -m "not slow"` in a worktree without a set, 4 failed; with
    `WASI_PYTHON_ARTIFACTS` set, 4 passed, lost 0). A failure without a cause in the product is a
    false red (spec 002, Decision 5: a missing input is a need). So `_version()` calls
    `needs.need("artifact dir", "manifest")` before it reads anything, and drops the assertion.
    (The two checks call `_version()` before `_run()`, whose need would block them; the third
    caller, `test_planted_code_never_runs`, calls `_run()` first and is already blocked.) Nothing
    changes when the set is present: the four checks run as today, and the ratchet shows no
    movement.

## Intent

The judge runs CPython's own test suite inside the guest, counts every pass, and shows every known
failure, every test it does not run, every environment change it allows and every host difference
as a gap, by name, with what will close it. The release runs it too: all of it on Linux, and its
file-system part on macOS and Windows, inside the shards it already has. It turns red when a pass
is lost, a test traps the guest, a failure appears, a module appears that the plan does not name,
or a host answers differently from what was recorded for it.

## Design

```
tests/upstream/python.toml           package python, component cpython, runner regrtest, grant
                                       /cpython, resources, options, warnings; [groups.<name>] list
                                       and fuel; [[not_selected]] modules; [[trap]] with group;
                                       [[expected]]; [[deselected]]; [[environment]];
                                       [[host_dependent]] (none today)
tests/upstream/python/cpython-{fs,archives,a,b,c}.txt
                                     the plan: one module per line, in run order (Decision 10)
tests/upstream/regrtest_drive.py     guest side: A2 (/tmp), A1 (a wrapped clear_caches, until spec
                                       074), -W error, /cpython/lib appended to sys.path, the stream
                                       hooks (unittest's result, regrtest's per-module result,
                                       test.support.environment_altered, the M lines' kind),
                                       regrtest's main() with the group's JSON
tests/upstream/expected/cpython-*/<class>.txt
                                     25 lists, 119 ids (Appendix A)
tests/harness/upstream.py            Config.runner, .component, .grant, .resources, .options,
                                       .warnings; Group.list; Trap.group; Deselected; Environment;
                                       HostEntry; a stage per grant family, CPython's from its
                                       tarball; the regrtest argv; parse_regrtest_stream;
                                       judge_regrtest_group (findings, classes, entries, passes, the
                                       universe); the trap check's open-entry verdict; rule_errors
                                       widened (Decision 16)
tests/checks/test_v1_3_upstream_suites.py
                                     _need per runner; python's groups, classes and traps as numpy's;
                                       test_upstream_deselected, test_upstream_environment,
                                       test_upstream_host (defined only while an entry exists)
tests/harness/shards.py              a trap's group: its `group` key when it has one, else 063's
                                       path rule; the entries' checks with their group
tests/upstream/fetch.py              --shard: the kit when the shard has a pytest group; the trees
                                       of every family whose group the shard holds (numpy and pandas
                                       together, as 063; CPython's tarball for a CPython group)
tests/upstream/packages.toml         [package.python] kind = "suite"
tests/release_shards.toml            cpython-b in upstream-frame; cpython-a and cpython-fs in
                                       upstream-numpy-a; cpython-archives in upstream-numpy-b;
                                       cpython-c in upstream-pandas-small; cpython-fs also in
                                       upstream-macos and upstream-windows
tests/known_gaps.toml                37 entries
tests/harness/scoreboard.py          NOT_MACHINE_CHECKED's new text
tests/unit/test_upstream.py, test_shards.py, test_fetch_trees.py
context/upstream/<n>-cpython-tests-in-one-wasi-process/, <n+1>-wasmtime-read-only-errnos/
README.md, CHANGELOG.md, AGENTS.md (rule 4), context/progress/README.md, spec 063 (one dated line),
context/roadmap.md
```

**A CPython group's run, in order:**
1. Stage `/cpython` once per judge run, after the MANIFEST tie, from the tarball.
2. Run `guest.run(snapshot, ["-u", "/cpython/judge/regrtest_drive.py", "<group>"], workdir, stdlib,
   env={"TMPDIR": "/tmp", "HOME": "/tmp"}, fuel=<cap>, preopens=[("/cpython", <stage>, False)],
   mpl_data=<as 050>)`.
3. In the guest: A2, A1, the warnings filter, `sys.path`, the hooks; `L` lines; then regrtest's
   `main()` with `-u <resources> --fail-env-changed <-i id>… <modules in order>`.
4. Read the stream; sort failures into classes and `D … altered` lines into environment entries;
   apply host entries for this system; check the universe, the states and the guard.
5. Record `fuel` and `passes`, and the facts `counts`, `passed_digest`, `left_out`, `states`,
   `env_altered`.
6. Cache the result for the group's class and entry checks; assert no finding.

**`AGENTS.md` rule 4** names `tests/upstream/python/` beside `tests/upstream/*.toml` and
`tests/upstream/expected/`: a plan list is not edited to turn a run green.

**`context/progress/README.md`**: one line, that the CPython groups are upstream checks like
numpy's, with the same `passes` metric, flag and refusal, and three more kinds of entry.

**Spec 063, one dated line** in its Status: "2026-10-…: `python` is a `suite` since spec 065; its
five groups sit in four Linux upstream shards, and `cpython-fs` also in `upstream-macos` and
`upstream-windows`."

## Scope

**In:** the above.

**Out, each with its reason:**
- **Fixing what the suite found.** Spec 071 fixes the C-stack trap it can; question 102 decides the
  rest; spec 074 the product's `sys.executable` and stand-ins; question 101 decides the C test
  modules. 065 names each, by id, with that closer.
- **CPython's C test modules** and the about 500 tests that skip without them: the owner's
  (question 101).
- **`-bb`**: it needs a product flag (Decision 8).
- **The plain binary.** Spec 050's Decision 1: the snapshot is the binary embedders call; the plain
  binary's import path is proved by the golden jobs.
- **The `cpu` and `largefile` resources, `--huntrleaks`, `--randomize`, `--rerun`, `-j`.**
  CPython's own fast CI leaves out `cpu`; `largefile` writes gigabytes; a leak hunt multiplies the
  fuel; a random order makes fuel unrepeatable; a rerun is a retry (063, Decision 14); the guest
  cannot start processes.
- **Per-system classes.** One verdict for every host (Decisions 1, 7 and 21).
- **Posting the upstream facts sheets.** The owner posts (Decision 20).
- **New shards or matrix legs.** Decision 7.
- **Nothing of the fail-not-block helper is left out.** The review's "Fast tier" section found it in
  four fast-tier runs without an artifact set; spec 070 is closed, so 065 fixes it (Decision 22).
- **Wall-clock.** No check reads a clock (§4.9); every time above is a benchmark estimate.

## Acceptance criteria

Each is counted; none times anything. Each check is written first and run against today's code (or
the stand-in named) to see it fail; the builder records each failing assertion in the landing notes.
A stand-in is applied in a scratch copy, never committed.

1. **The rules.** `test_upstream_files_are_well_formed` passes with Decision 16's rules on the new
   files. `tests/unit/test_upstream.py` variants each fail with their own line: a module in two
   lists; a module in a list and in `not_selected`; `test_monitoring` not last; `test_profiling` in
   `test_monitoring`'s group; a list not sorted; a trap with no group, or a test-level trap whose
   module is in another group; a deselected id whose module is in another group; a deselected id
   or trap id whose class or method the tarball's source does not have (C5); an entry with no
   gap; a host entry missing a system its group runs on, or with a result outside the allowed ones;
   the `/cpython` family's caps over 2.5×10¹²; a closer that does not exist. Seen failing first: the
   check fails on 063's tree (no `python.toml`, and `packages.toml` says `later`).
   *Stand-ins:* a rule that checks the budget across both families together (numpy's and pandas'
   2.519×10¹² plus CPython's then fail a good tree); one that checks sortedness before moving
   `test_monitoring` (a good list fails).

2. **The stream and the verdict, on fixed streams** (`tests/unit/test_upstream.py`, no guest):
   - a failing subtest's id is `<test id> [<msg>]` or `<test id> (<params>)`, and it sorts into a
     class by that id;
   - each of these is a group finding: an `X` line; `D … ENV_CHANGED …`; `D … INTERRUPTED …`; a
     `D … FAILED altered` line no environment entry names; exit code 3; a missing `E` line; a stream
     ending after `S` (a trap, `at or after` that test) or after `C` (naming that module); an
     `M json /cpython/lib/json/__init__.py product` line; an `L` line for a module in no list; a list
     module with no `L` line; a host entry whose recorded result on this system differs;
   - not findings: `skipped`, `xfailed`, `D … SKIPPED`, `D … RESOURCE_DENIED`, `D … DID_NOT_RUN`;
     `M generate_build_details /cpython/Tools/build/generate-build-details.py test` (the review's
     case, F3); `D test_bdb FAILED altered` with `sys-path-bdb` in place;
   - `xpassed` sorts as a failure;
   - `passes` counts `R passed` only, and leaves a host entry's test out of `passes` and
     `passed_digest`; a module host entry's tests too;
   - a class with one id more than its list fails with `+<id>`, one fewer with `-<id>`; an
     environment entry likewise with `+<module>` and `-<module>`;
   - a deselection entry's check fails with exactly its ids, and is red when a listed id has an `S`
     line;
   - a trap check with its entry open gives the same one finding whether the stream ends in the
     named trap or ends with `E 0`, and records which as a fact; a trap by another cause adds a
     finding (F5);
   - for the whole-module entry, a stream where `test_traceback` runs to `D test_traceback FAILED
     kept` and `E 2`, with 96 errors and 9 failures, gives only the open-entry finding and records
     the counts as a fact; the same stream without its `D` line is red (C2);
   - `D test_bdb FAILED altered sys.path was modified by test_bdb` with `sys-path-bdb` in place is
     not a finding; `D test_bdb FAILED altered sys.path was modified by test_bdb|Warning --
     Unraisable exception` is, for the second kind (C1);
   - a module host entry whose module's pass count or digest on this system differs from its
     recorded one is red (C3);
   - the driver's `print_warning` wrapper carries `orig_stderr` (a unit check of the driver's
     source and of the wrapper object, C1's hazard).
   *Stand-ins:* a parser that counts passing subtests as passes (`passes` then differs from the
   fixed stream's expected count); an environment entry that matches the module only, without its
   `changes` (the unraisable-exception stream then passes); a whole-module trap check that judges
   the module's failures (the `test_traceback` stream is then red); one that reads
   `environment_altered` only for `PASSED` modules
   (the `test_bdb` stream then shows no `altered`, and its entry's check reports `-test_bdb`); an
   `M` rule that flags every module outside `test.` (the `generate_build_details` stream is then a
   finding).
   **The `sys.monitoring` stand-in** (EXECUTED by the builder, F1): `test_monitoring` alone, with
   the deselection entry, under a scratch driver that wraps `sys.monitoring.set_local_events` to
   drop `LINE` events. Its `TestLineAndInstructionEvents` and `TestLocalEvents` tests then fail in
   their bodies, and the group check names each as `unexpected failed <id>`: the regression is red.
   The same scratch driver over the draft's design (no deselection, the 45-id class) changes
   nothing the class would show, since those tests fail in `setUp` either way. The landing notes
   give both runs' failing ids.

3. **Seen failing first, then the baseline** (EXECUTED by the builder on the frozen set of its base,
   with the CPython tarball and tree linked into the worktree as spec 050's Decision 20 does):
   - the five group checks before any class, entry or gap: `cpython-a` traps in `test_functools`,
     `cpython-b` in `test_doctest` (the first of its two trapping modules in order), `cpython-c` in
     `test_syntax`, `cpython-fs` fails with its 67 ids, and `cpython-archives` passes;
   - with the nine trap entries, each group runs to its end, and its failures equal Appendix A's ids
     for that group exactly. Any difference (an id the evidence did not name; an outcome `-W error`
     changed; a module whose outcomes differ from its run alone, which is a leak) is explained in
     the landing notes before a class is written, and each class's `match` is written against the
     stream's own reasons (F10);
   - each group's `passes` is compared with Decision 10's expected numbers, and any difference
     explained. The guest is the same bytes on every host, so a host explains no difference but a
     stack exhaustion, which Decision 1's rule handles (F5).

4. **With the TOML, the lists and the gaps complete,** the run on that set gives: 5 group checks
   `pass`; 25 class checks `gap`; 9 trap checks `gap`, each with exactly its one open-entry finding
   and the fact `trap at or after <id>`; the deselection check and the 2 environment checks `gap`;
   no `M … product` line; no `ENV_CHANGED` and no `altered` outside the two entries; the universe
   check clean (557 modules, each in one place).

5. **Fuel repeats.** The builder runs each CPython group twice in one judge session (a one-off, not
   a check); the two fuels are within 0.01%, and the landing notes give both, and the sum of the
   CPython group and trap checks' fuel against the 1.45×10¹² review rule.

6. **The shards.** 063's `test_release_shards_cover_the_judge` and
   `test_every_package_names_its_own_suite` pass on the new plan and package list.
   `tests/unit/test_shards.py`: a CPython trap with `group = "cpython-a"` is selected with
   `cpython-a`'s shard and with no other; `cpython-fs`'s suite, class and entry checks are selected
   by `upstream-numpy-a`, `upstream-macos` and `upstream-windows`, each on its own system;
   `cpython-archives`' by `upstream-numpy-b` only.
   *Stand-in:* a `select` that places a CPython trap by 063's path rule (it then lands in `rest`,
   and the plan's rule (c) or the unit check fails).

7. **The fetch.** `tests/unit/test_fetch_trees.py`, a fake `urlopen` and synthetic tarballs: a shard
   with a CPython group fetches the CPython tarball, verifies it against `downloads/SHA256SUMS`,
   unpacks it with the `data` filter and runs the applier on its (absent) patch folder; a shard with
   only numpy or pandas groups fetches no CPython tarball; a shard with a CPython group and no
   pytest group fetches no kit; a hash mismatch deletes the `.part` file and exits 1.
   *Stand-in:* 063's fetch unchanged (it fetches no CPython tarball, and the unit check fails).

8. **The shards together, locally** (EXECUTED by the builder, as 063's criterion 8, for the six
   shards this changes): `--shard=upstream-frame`, `upstream-numpy-a`, `upstream-numpy-b`,
   `upstream-pandas-small`, `upstream-macos` and `upstream-windows`, each in its own process. Each
   CPython group's `passes` and `passed_digest` equal the serial full run's. Then `gather.py` over
   063's criterion-8 records, with these six shards' records in place of theirs, passes; its G5
   holds for every CPython group.

9. **numpy and pandas do not move.** The full judge's ratchet against the base shows lost 0, grew 0,
   fewer 0: every numpy and pandas group's fuel is within the ratchet's tolerance of the accepted
   value. A unit check shows the `/upstream` stage's file list and bytes are the same with and
   without `python.toml` in the configs, and that a CPython group's preopens are exactly
   `[("/cpython", <stage>, False)]`. *Stand-in:* a Session that stages CPython into `/upstream` (the
   unit check fails, and numpy-lib's fuel moves).

10. **The tie and the stage.** Unit checks: a MANIFEST whose CPython `pin` line differs from the
    tarball makes the CPython checks fail (not blocked), naming both; the stage's files are the
    tarball's member bytes, so a file changed in a scratch tree's `Lib/test` is not what is staged,
    and a stray file there is listed in `left_out`. *Stand-in:* a stage copied from the tree (the
    changed byte then reaches the stage, and the unit check fails).

11. **The full judge.** `uv run ruff check`, `uv run ruff format --check` and `uv run pytest` green,
    with the judge changed (`--accept-judge` is the lane's):
    - gained: 5 (the group checks); the 37 gaps on the scoreboard under their closers;
    - lost 0, grew 0, fewer 0, unrun locally 0 in the main tree;
    - the scoreboard's last lines carry Decision 17's text;
    - the landing notes give the full serial judge's time before and after (a benchmark fact;
      INFERRED 4 to 8 minutes more: 1.14 T of fuel at the quiet rate is about 3 minutes, plus about
      50 s of real sleeps, plus the file-system groups' I/O, minutes under load).

12. **The branch's dry run, before landing** (Decision 7; not a check). Every job passes on all
    three systems. The landing notes link each run, and record: each changed shard's job time
    against Decision 7's table, and `upstream-macos` and `upstream-windows` against their bounds
    (300 s and 360 s), with the remedy taken if one is past it; `cpython-fs`'s fuel on the CI macOS
    runner against the lane's; each host's trap facts for the nine entries (F5); the gather's G5
    line for `cpython-fs` on three systems; every host entry the run made necessary, with each
    host's result and its review.

13. **The lane's dry run after landing** (on main's exact commit; not a check), as 063's criterion
    11. A failure there is fixed before any tag.

14. **The hostile-guest helper is blocked, not failed** (Decision 22). A plugin self-test in
    `tests/unit/` runs `test_matplotlib_data_is_granted_read_only` and
    `test_usr_local_lib_holds_only_the_zip` with `WASI_PYTHON_ARTIFACTS` naming an empty folder: all
    four results are `blocked`, each naming `manifest`, and none is `fail`. (`paths.artifact_dir()`
    returns that folder whenever the variable is set, so `artifact dir` is met and `manifest` is
    not: `paths.py:125–128`, `needs.py:154–158`; the confirmation's C6.) With the frozen set
    they pass as before. *Stand-in:* today's `_version()`, with its `assert directory is not None`
    and no need (the self-test then sees four `fail` results, `FileNotFoundError` on `MANIFEST`).

## The owner's choices

Two are the owner's, both asked in `../questions-for-the-owner.md`; 065 builds without either
answer, and each gap names its question (§5.2):
- **Number 101** (asked here), because it adds a build output: whether question 89's judge-only
  binary also links CPython's C test modules. It closes `no-test-modules`, the deselection entry,
  and three modules not selected (Decisions 3 and 21).
- **Number 102** (asked by spec 071): what closes the deep-recursion traps 071's window cannot. It
  closes five of the nine trap entries (Decision 1).

Everything else is decided above.

## Appendix A: the allowances by id

The ids the stream will write, from the memo's verbose reruns, its trap hunt, and the review's
`cpython-b` session for `test_c_cleandoc` (EXECUTED; `evidence/spec-065-drafting/allowances.tsv`
for the 163 the drafting saw, with the reasons the drafting recorded). The builder writes the list
files from its first run (criterion 3) and the review compares them with this. The class lists hold
119 ids; the deselection entry 5 (Decision 21); the environment entries 2 modules; the trap entries 9
(Decision 1).

**`cpython-fs`** (67)
- `no-ctypes` (14): `test.test_io.test_general.{CIOTest,PyIOTest}.` `test_buffered_file_io`,
  `test_raw_bytes_io`, `test_raw_file_io`, `test_buffered_readinto_mixin [readinto]`,
  `test_buffered_readinto_mixin [readinto1]`; `test.test_io.test_bufferedio.{CBufferedRWPairTest,PyBufferedRWPairTest}.`
  `test_readinto [readinto]`, `test_readinto [readinto1]`.
- `no-mmap` (31): `test.test_mmap.LargeMmapTests.` `test_large_filesize`, `test_large_offset`;
  `test.test_mmap.MmapTests.` `test_access_parameter`, `test_anonymous`, `test_basic`,
  `test_concat_repeat_exception`, `test_context_manager`, `test_context_manager_exception`,
  `test_double_close`, `test_empty_file`, `test_entire_file`, `test_extended_getslice`,
  `test_extended_set_del_slice`, `test_find_end`, `test_flush_parameters`,
  `test_flush_return_value`, `test_io_methods`, `test_length_0_large_offset`,
  `test_length_0_offset`, `test_move`, `test_non_ascii_byte`, `test_offset`, `test_read_all`,
  `test_read_invalid_arg`, `test_rfind`, `test_tougher_find`, `test_trackfd_neg1`,
  `test_trackfd_parameter (close_original_fd=False)`, `test_trackfd_parameter (close_original_fd=True)`,
  `test_weakref`, `test_write_returning_the_number_of_bytes_written`.
- `mmap-stand-in-surface` (4): `test.test_mmap.MmapTests.` `test_error`,
  `test_mmap_closed_by_int_scenarios`, `test_repr`, `test_subclass`.
- `sqlite-lock` (7): `test.test_sqlite3.test_transactions.TransactionTests.`
  `test_delete_starts_transaction`, `test_dml_does_not_auto_commit_before`,
  `test_insert_starts_transaction`, `test_multiple_cursors_and_iternext`,
  `test_replace_starts_transaction`, `test_toggle_auto_commit`, `test_update_starts_transaction`.
- `no-file-modes` (1): `test.test_dbm_sqlite3.ReadOnlyFilesystem.test_readonly_file_write`.
- `stdlib-zip` (4): `test.test_linecache.LineCacheTests.` `test_clearcache`, `test_frozen`,
  `test_getline`, `test_memoryerror`.
- `stdlib-zip-error` (2): `test.test_importlib.resources.test_files.{ImplicitContextFilesDiskTests,ImplicitContextFilesZipTests}.test_implicit_files_with_compiled_importlib`.
- `stepped-clock` (3): `test.test_logging.TimedRotatingFileHandlerTest.test_rollover`;
  `test.test_os.test_os.UtimeTests.` `test_utime_current`, `test_utime_current_old`.
- `trailing-slash-einval` (1): `test.test_shutil.TestCopy.test_copyfile_nonexistent_dir`.

**`cpython-archives`** (0): no class.

**`cpython-a`** (9)
- `no-ctypes` (1): `test.test_pickletools.OptimizedPickleTests.test_buffers_numpy`.
- `no-test-modules` (1): `test.test_call.TestRecursion.test_margin_is_sufficient`.
- `read-only-eperm` (1): `test.test_trace.TestCoverageCommandLineOutput.test_cover_files_written_no_highlight`.
- `stdlib-zip` (4): `test.test_contextlib_async.TestAsyncExitStack.test_exit_exception_traceback`;
  `test.test_module.ModuleTests.test_module_repr_source`;
  `test.test_unittest.test_result.Test_TestResult.` `test_addFailure_filter_traceback_frames`,
  `test_addFailure_filter_traceback_frames_context`.
- `stdlib-zip-error` (1): `test.test_sys.SysModuleTest.test_stdlib_dir`.
- `no-executable-file` (1): `test.test_platform.PlatformTest.test_libc_ver`.

**`cpython-b`** (11)
- `no-ctypes` (1): `test.test_memoryview.OtherTest.test_ctypes_cast`.
- `no-test-modules` (2): `test.test_inspect.test_inspect.TestModuleCLI.test_get_cli_details_for_extension_module`;
  `test.test_inspect.test_inspect.TestRetrievingSourceCode.test_c_cleandoc`.
- `read-only-eperm` (2): `test.test_doctest.test_doctest.TestDocTestFinder.test_empty_namespace_package`;
  `test.test_support.TestSupport.test_forget`.
- `stdlib-zip` (4): `test.test_contextlib.TestExitStack.test_exit_exception_traceback`;
  `test.test_inspect.test_inspect.TestModuleCLI.` `test_get_cli_details_for_frozen_module`,
  `test_get_cli_details_for_source_module`, `test_get_cli_details_for_source_package`.
- `stdlib-zip-error` (2): `test.test_inspect.test_inspect.TestGetsourceStdlib.`
  `test_getsource_stdlib_collections_abc`, `test_getsource_stdlib_decimal`.
- **Not a class:** the deselection entry `capi-event-generation` (five
  `test.test_monitoring.TestCApiEventGeneration.*` ids) and the environment entry
  `sys-path-doctest` (`test_doctest`).

**`cpython-c`** (32)
- `no-ctypes` (5): `test.test_pickle.{CDumpPickle_LoadPickle,CPicklerTests,DumpPickle_CLoadPickle,InMemoryPickleTests,PyPicklerTests}.test_buffers_numpy`.
- `ctypes-stand-in-surface` (1): `test.test_frame.TestFrameCApi.test_basic`.
- `read-only-eperm` (18): `test.test_bdb.BreakpointTestCase.` `test_bp_after_last_statement`,
  `test_bp_condition`, `test_bp_exception_on_condition_evaluation`, `test_bp_ignore_count`,
  `test_clear_two_bp_on_same_line`, `test_disabled_temporary_bp`,
  `test_ignore_count_on_disabled_bp`, `test_temporary_bp`;
  `test.test_bdb.IssuesTestCase.` `test_next_command_in_generator_for_loop`,
  `test_next_command_in_generator_with_subiterator`,
  `test_next_until_return_in_generator (set_type='next')`,
  `test_next_until_return_in_generator (set_type='return')`,
  `test_next_until_return_in_generator (set_type='until')`,
  `test_return_command_in_generator_with_subiterator`,
  `test_step_at_return_with_no_trace_in_caller`;
  `test.test_bdb.RunTestCase.test_runeval_step`;
  `test.test_bdb.StateTestCase.` `test_next_over_import`, `test_skip`.
- `stdlib-zip` (5): `test.test_pdb.test_pdb_breakpoints_preserved_across_interactive_sessions [1]`,
  `… [2]`; `test.test_pdb.test_pdb_return_to_different_file [3]`;
  `test.test_pydoc.test_pydoc.PydocUrlHandlerTest.test_url_requests`;
  `test.test_pydoc.test_pydoc.TestInternalUtilities.test__get_version`.
- `stdlib-zip-error` (3): `test.test_pydoc.test_pydoc.PydocDocTest.`
  `test_mixed_case_module_names_are_lower_cased`, `test_synopsis_sourceless`;
  `test.test_pydoc.test_pydoc.PydocImportTest.test_importfile`.
- **Not a class:** the environment entry `sys-path-bdb` (`test_bdb`).

## Disposition of the pre-build review (2026-10-18)

The review is `065-cpythons-own-tests-in-the-release-spec-2026-10-18.md` (the session's scratchpad,
`065-review/`, with `probes/` and `runs/`; the lane copies it to `../reviews/`). It confirmed the
plan: run as four sessions on the frozen set, its failures were the drafted 163 ids test for test,
with one addition. The lane ruled on each finding; each is written in as ruled.

- **F1 (high), `monitoring-tool-left` hid `sys.monitoring`.** The class is gone. The five
  `TestCApiEventGeneration` tests are a deselection entry by full id, closer question 101, with its
  reason; `cpython-b` gains 39 passes. The mechanism, which spec 050 lacks, is decided: Decision 21's
  `[[deselected]]`, a gap on the scoreboard. Criterion 2's `sys.monitoring` stand-in shows a
  regression is now red. The facts sheet states the upstream bug as read (Decision 20).
- **F2 (high), the trap list.** Nine entries by full id: four `test_recursive_pickle` variants, two
  `test_error_on_parser_stack_overflow` variants, `test_doctest`, `test_exceptions`, and
  `test_traceback` whole (Decision 1). The review counted seven test-level entries; its runs show
  eight, so the lane's "8 trap entries" and 2.10×10¹² become 9 and, with F8's raised caps,
  1.75×10¹² + 9 × 5×10¹⁰ = 2.20×10¹² (Decision 16, under 2.5×10¹²); 37 gaps. The finding reads
  `at or after <id>`. Spec 071's draft (`2265b90`) closes the four `test_recursive_pickle`
  entries; the other five close with question 102. `test_traceback`'s reason is the trap that is no
  test's.
- **F3 (medium), the `M` rule.** Only a product module with a `__file__` under `/cpython/` is a
  finding (Decision 13), with the review's `generate_build_details` case as a unit check
  (criterion 2).
- **F4 (medium), environment changes in failing modules.** The driver reads
  `support.environment_altered` per module; an altered environment is a finding unless an
  `[[environment]]` entry names the module: `test_doctest` and `test_bdb` today (Decisions 5, 13 and
  21). Decision 5's "none" is corrected.
- **F5 (medium), traps by host.** A trap seen on any host is a trap entry on every host; while it is
  open its check accepts "the named trap, or no trap", with one constant finding and a fact
  (Decision 1). Criterion 3's sentence is corrected.
- **F6 (medium), host entries.** Each records each system's own result, checked exactly there; each
  is a gap on the scoreboard; they cover module results too (`ENV_CHANGED`, `load-error` and the
  others); a trap on one host is Decision 1's (Decision 21). Reconciled with 063 Decision 18
  (Decision 7).
- **F7, `-W error` and `test_c_cleandoc`.** 164 ids before F1 (119 after); `no-test-modules` in
  `cpython-b`; the facts sheet gains the bug; Decision 8 says its probe held for seven modules only.
- **F8, cost.** Decision 7 re-derived on 063 at `0815007` and its dry run 39182550825; the
  archive modules split into `cpython-archives`, Linux only in the release, so `cpython-fs` on
  macOS and Windows is about 60 G; bounds of 300 s (macOS) and 360 s (Windows) with the remedy
  decided; `cpython-a` and `-b` caps raised to at least 1.5 times the review's fuel; the lane's
  judge INFERRED 4 to 8 minutes more (criterion 11).
- **F9, A1 on 069's snapshot.** The driver wraps `clear_caches` and never imports `ctypes`
  (Decision 4).
- **F10, the matches.** Stated as proposals placed for 137 of 163 ids; the builder writes them
  against the stream's own reasons (Decision 12, criterion 3).
- **F11, the stage and the input.** Staged from the verified tarball (Decision 15, criterion 10);
  the tarball named as a new CI input for the threat-model review (Decision 7).
- **F12, housekeeping.** Rebased onto main `7d377dd`; question 99's answer cited where it is (the
  Problem); spec 074 comes before 0.1.0 (Decision 19, and the roadmap).
- **The "Fast tier" section** (the fail-not-block helper): fixed here, since spec 070 is closed
  (Decision 22, criterion 14).
- **Notes.** N1 (`test_ast`'s module-level listing) is in the facts sheet and the not-selected
  table; N2 (`byteslike()`'s `ctypes.resize`) is for spec 074 (Decisions 12 and 19); N3 is already
  covered (an exit other than 0 or 2 is a finding); N4 (wasmtime's real default stack) is 071's; N5
  holds for the new placement (each CPython group in exactly one Linux shard).

## Disposition of the confirmation round (2026-10-18)

The confirmation (`065-cpythons-own-tests-in-the-release-spec-confirmation-2026-10-18.md`, beside
the review) found every finding written in, and ran the revised mechanisms on main's new set
(`s-ff5246a2c2f1a52b`): on `cpython-b` and `cpython-c` the deselection, the environment entries, the
`M` rule, A1 by wrap and the trap ids behave as written, and their failing ids are the revised
Appendix A exactly. It confirmed the nine trap entries (its own "seven" was an arithmetic slip). Its
verdict: confirmed for build once C1 and C2 are written in. Each item, as the lane ruled:

- **C1 (medium), an environment entry admitted any change in its module.** An entry names its
  kinds, `changes = ["sys.path"]`; the driver records the first line of each `print_warning`; any
  other kind is a finding (Decisions 5, 13 and 21; criterion 2 with a stand-in). The builder hazard
  (copy `print_warning.orig_stderr`) is in Decision 13 with a unit check.
- **C2 (medium), the whole-module trap entry had no "no trap" verdict.** "No trap" means the module
  ran to its `D` line; its counts are a fact; its failures are unjudged until the entry closes
  (Decision 1; criterion 2 with a stand-in).
- **C3, a module host entry hid its passes.** It records and checks its pass count and digest per
  system (Decision 21; criterion 2).
- **C4, "no trap" never asked to be removed.** The scoreboard names open entries that did not trap
  here; the gather names those that trapped on no system (Decision 1; the Kind's changed files).
- **C5, a deselected id was not checked to exist.** A static check against the verified tarball's
  source, for deselected and trap ids (Decision 16; criterion 1).
- **C6, criterion 14's need.** It expects `manifest`, not `artifact dir`.
- **C7, spec 071 describes 065's old five entries.** Spec 071's edit; the lane routes it there.
  065's text already reads "five trap entries, with 071's reasons" if 071 lands first.
- **C8, question 101 said "by name".** It says "by full id" (`../questions-for-the-owner.md`).
- **F9's builder note.** The name to wrap is `single.clear_caches` (Decision 4).

## Landing notes

Built 2026-10-19 by the builder (Claude Opus 5.5) in the worktree `wasi_python-065`, branch
`spec/065-cpythons-own-tests-in-the-release`, on spec 063's branch head `1488377` (itself on main
`6fd89e0`), against main's frozen set `s-ff5246a2c2f1a52b` (lxml in; the first runs were on
`s-4eb5418a2b1bb553-c353b1d9`, 063's earlier base). Not yet reviewed. Every number below is
EXECUTED unless marked. At landing the lane rebases onto main after 063 lands.

**Setup (as spec 050's Decision 20).** Read-only symbolic links in the worktree to the main
tree's `downloads/{numpy-2.5.2.tar.gz,pandas-3.0.6.tar.gz,Python-3.15.0.tar.xz}`,
`build/{numpy-2.5.2,pandas-3.0.6,Python-3.15.0}` and `build/upstream/wheels`;
`WASI_PYTHON_ARTIFACTS` set to the frozen set. Nothing in the main tree was written.

**What changed.** As the Design lists, with these builder details:
- `tests/harness/regrtest.py` holds the regrtest runner (stage, argv, stream, verdict, trap
  verdict, rules, session); `tests/harness/upstream.py` loads `python.toml` into the same
  `Config` (new fields default for numpy and pandas), keeps its `/upstream` session to the pytest
  packages, splits the cap budget per grant family, and its tie names `.tar.xz` trees.
- The driver wraps `test.support.print_warning` once: `libregrtest.utils.print_warning` calls it
  by attribute, so `save_env`, `single` and `utils` all reach the wrapper; the wrapper carries
  `orig_stderr`, and a unit check runs it against a stand-in `support` (C1's hazard). A1 wraps
  `single.clear_caches` (F9). Load failures are read by wrapping `single._load_run_test`.
- Environment kinds match `<change> was modified by` exactly (D1); an `altered` module with no
  warning line is a finding (D2); the unraisable line is the bare `Unraisable exception` (D4).
- The rules' id check parses the tarball's source with `ast` and finds a class nested under an
  `if` (`test_tempfile`'s `TestTemporaryFile` sits under one).
- The group check records every finding as a fact (`findings`), so a release record carries them
  all, not only the message's first five (added after the first dry run).

**Seen failing first, then the baseline (criterion 3).** Before the class lists and gaps existed,
the rules check failed with every missing gap, and each class and trap check failed on its own
findings. The groups, run through the harness on `s-4eb5418a2b1bb553-c353b1d9` with the nine
trap entries: no finding in any group; the 25 classes held 119 ids, equal to Appendix A id for id
(`diff`: none); `cpython-fs` 3,735 passes, `cpython-archives` 1,313, `cpython-a` 5,681,
`cpython-b` 9,534, `cpython-c` 7,870. `cpython-b` is one under Decision 10's 9,535:
`test_doctest`'s `test_CLI` is now a skipped doctest ("all examples were skipped"), which the
memo's XML had counted as a pass. Each of the nine trap entries trapped at its named test
(`trap at or after <id>`), `test_traceback` at `CExcReportingTests.test_exception_group_depth_limit`.

**The branch's dry runs (criterion 12; question 98).** Three, each on a pushed head:
- `39191495242` (on 063's old head `2efcece`): cancelled when 063 was rebased.
- `39192207869` (head `1776879`): `upstream-numpy-a` failed: `trailing-slash-einval` passes on
  Linux. `upstream-pandas-small` failed: `test_int`'s four denial-of-service tests failed on Linux,
  and the guest trapped at or after
  `test.test_ordered_dict.CPythonOrderedDictSubclassTests.test_highly_nested`. `upstream-windows`
  failed with 26 findings in `cpython-fs`. `own-guest` on Windows failed, 063's four known checks
  (spec 076). Judged:
  - `test_int`: the tests skip on darwin because `time.get_clock_info(...).resolution` there is
    1 µs, the stepped clock's step, and fail on Linux, whose host answers 1 ns. The guest's clock is
    the judge's, so `tests/harness/guest.py` now answers `clock_res_get` itself, with the values a
    darwin host answered (1 µs for realtime and monotonic, 1 ns for the CPU-time clocks), so no
    darwin result moves (the full judge: grew 0) and every host agrees.
  - the `OrderedDict` trap: Decision 1's rule, a tenth trap entry,
    `c-stack-ordered-dict-subclass`, deselected on every host, closed by question 102. On darwin
    its trap check records "no trap on this host" and the scoreboard names it (C4).
  - the trailing slash: a host entry, `trailing-slash` (darwin `error`, linux `passed`, win32
    `error`); its class `trailing-slash-einval` is emptied and kept, without a gap (condition C1).
- `39194284100` (head `9b1dcb0`): every Linux shard green. `upstream-windows`: 25 Windows
  differences in `cpython-fs`, read from the record's `findings` fact: 22 `test_tempfile` tests (a
  Windows host refuses to remove a file the guest holds open), `test_shutil`'s colon name and its
  folder opened for reading. Each is a host entry recorded per system (darwin and linux `passed`,
  win32 its outcome), closed by the README's *On Windows* list (the build review's F3; facts sheet
  22 keeps the Windows facts as evidence).
- `39196429702` (head `f760fd2`): **every job passed but `own-guest` on Windows** (063's four
  known checks, spec 076's), so the gather was skipped. Job times against Decision 7's bounds:
  `upstream-macos` 122 s (bound 300 s), `upstream-windows` 296 s (bound 360 s); Linux
  `upstream-numpy-a` 218 s, `upstream-numpy-b` 163 s, `upstream-frame` 222 s,
  `upstream-pandas-small` 219 s, `upstream-groupby` 189 s (no CPython group). Against the records:
  `cpython-fs` has 3,710 passes and `passed_digest` `63a876f3798c` on the lane's Mac, the CI macOS
  runner, Linux and Windows alike, so G5 holds for it; its fuel on the CI macOS runner is 2.3e-6
  from the lane's (the ratchet's tolerance is 1e-4). The gather itself waits on spec 076.

**The full judge (criterion 11).** `uv run ruff check` and `uv run ruff format --check` clean.
`WASI_PYTHON_ARTIFACTS=…/s-ff5246a2c2f1a52b uv run pytest -n 3`, no `--accept`, exit 0:

```
wasi_python v1: 417/515 pass · 77 gap · 21 blocked · 0 fail   (unit suite 1447/1455, 8 skipped)
gaps close with: notes 31 · README 25 · 2026-10-18-cpythons-own-tests-under-the-runtime 13 · questions-for-the-owner 5 · 2026-10-17-matplotlib-on-the-current-line 2 · 002-the-progress-harness 1
trap entries with no trap here: c-stack-ordered-dict-subclass
ratchet vs 75f03ab77e: lost 0 · absent 0 · unrun 0 · unrun locally 18 · gained 9 · grew 0 · judge changed: …
1864 passed, 29 skipped, 77 xfailed in 481.07s (0:08:01)
```

- Gained 9: the five CPython group checks, the emptied class check, and 063's three rules (063 is
  not accepted on main yet). No existing check's fuel moved, the numpy and pandas groups' included
  (criterion 9), with the guest's stated clock resolution.
- The CPython checks: 5 groups pass (28,107 passes; fuel 56.9 G, 163.4 G, 246.4 G, 325.4 G and
  345.0 G, 1.137 T in all, under the 1.45×10¹² review rule; every cap at least 1.5 times its group);
  63 gaps: 24 classes (119 ids), 10 trap entries, 1 deselection, 2 environment entries, 26 host
  entries. `unrun locally 18` is this worktree's tooling (the other components' trees, the oracle);
  none is an upstream check.
- The fast tier on the same set: 1,824 passed, 28 skipped, lost 0.

**Criterion 2's `sys.monitoring` stand-in** (EXECUTED, `test_monitoring` alone). With the
deselection: 88 passed, 0 failed. The same with a scratch driver that drops `LINE` from
`set_events` and `set_local_events`: 15 passed and 76 failures, each an `unexpected failed`. So
the regression is red. Without the deselection (the draft's class), the same stand-in also
changes the failures' messages (it breaks `setUp`'s own event check), so this stand-in does not
show the class hiding a body-only regression; the base runs do: under the draft every one of the
45 tests failed in `setUp` before its body ran.

**Criterion 14** (EXECUTED): with `WASI_PYTHON_ARTIFACTS` naming an empty folder the four results
are `blocked` on `manifest`; today's helper fails all four (the stand-in, run on a scratch edit).

**Departures from the specification, each with its reason:**
- Ten trap entries, not nine: the Linux-only `OrderedDict` trap, by Decision 1's own rule.
- Twenty-six host entries, not none: what the dry runs found, by Decision 21's rule; the
  `trailing-slash-einval` class is emptied as a result.
- `tests/harness/guest.py` answers `clock_res_get` (not in the Design): the judge's clock was
  passing the host's resolution through, a host difference of the judge's own making.
- The `findings` fact on a failing CPython group (not in the Design), for the release records.
- The upstream facts sheets were numbered 20 and 21; spec 076 takes 20, so they are 21 and 22 (the
  build review's F5).
- The branch was rebased twice (onto `2efcece`, then onto `1488377`); five files of the second
  rebase's intermediate commits carry conflict markers, repaired in `1776879`. Each commit after
  that is clean; the lane squashes at landing (the build review's F4).
- Expected passes are 28,107 on main's set against the spec's 28,134 estimate: `test_doctest` −1
  (above), `test_ordered_dict` −1 (deselected), and the 25 Windows host entries' tests, which pass
  on darwin and are left out of `passes` on every host.

**The build review** (`065-cpythons-own-tests-in-the-release-build-2026-10-19.md`, the session's
scratchpad; the lane copies it to `../reviews/`): "lands once F1 to F3 are fixed"; the seven
departures accepted. Fixed:
- **F1:** `test_the_guest_clocks_resolution_is_the_judges` (v1.2) shows the guest distinct
  resolutions the judge states, so the judge answered, not the host; its stand-in, the binding
  removed, fails with `['1000', '1000', '1000']` (EXECUTED). `process_time`'s resolution never
  reaches `clock_res_get` in this guest (1 ns either way, EXECUTED), so the check reads the three
  clocks that ask. A unit check pins the stated table. Spec 002 gains its dated line, which says
  the CPU-time clocks are stated at 1 ns though they step 1 µs, and that the four `test_int`
  denial-of-service tests now skip on every host.
- **F2:** the README's trailing-slash sentence per host: `EINVAL` on macOS, `FileNotFoundError` on
  Linux, `ENOTDIR` on Windows.
- **F3:** the 25 Windows host entries close with `README.md`, whose *On Windows* list gains the
  colon-name and folder-open facts beside its open-file rule; facts sheet 22 keeps
  `read-only-eperm`, the two environment entries and `trailing-slash`.
- **F5:** the facts sheets are renumbered 21 (CPython's tests) and 22 (wasmtime's errnos), after
  spec 076's 20.
- **F4:** the lane squashes at landing.

**The `--accept-judge` reason, proposed for the lane:** "spec 065: CPython's own regrtest suite in
the guest, five groups (28,107 passes on s-ff5246a2c2f1a52b), 24 classes by test id, ten trap
entries, a deselection, two environment entries and 26 host entries; the judge states each guest
clock's resolution, guarded by a v1.2 check; the hostile-guest helper blocks on manifest; the 25
Windows host entries close with the README; facts sheets renumbered 21 and 22 after spec 076's 20".

### Rebased onto main `08de0c8` and re-judged on its set

063 landed as `19427b5`; the branch was rebased onto main `08de0c8` (its own commits replayed,
main's side kept where both changed a file, then this branch's hunks merged back three ways: three
files both sides appended to, kept both; one gap main had removed, 063's Linux faulthandler gap,
dropped again). Judged on `s-c50ca51fae5eb55b-c9dcb5b8`, which is `s-c50ca51fae5eb55b` with spec
079's MANIFEST recipe lines (its `python.wasm`, snapshot and zip byte-identical, EXECUTED `cmp`;
against the bare `s-c50ca51fae5eb55b` the fast tier loses `test_manifest_recipes_match_the_tree`
on 079's recipe lines, which is the set's, not this change's). Every number below is EXECUTED.

**What moved, with its measured cause:**
- **Trap entries: eight, from ten.** On this set (spec 071's C-stack window and the runner's
  512 KiB engine in the judge's driver), each entry run alone: the four `test_recursive_pickle`
  variants pass ("no trap on this host"), so their entries and gaps are removed and the tests run in
  `cpython-a` again (+4 passes); `test.test_ordered_dict.PurePythonOrderedDictTests.test_highly_nested`
  and `…PurePythonOrderedDictSubclassTests.test_highly_nested` trap, so they are entries
  (`c-stack-ordered-dict-py`, `c-stack-ordered-dict-py-subclass`, 071's Decision 8; −2 passes in
  `cpython-c`); `CPythonOrderedDictSubclassTests.test_highly_nested`, the dry run's Linux trap, now
  traps on darwin too; `test_doctest`, `test_exceptions`, both `test_syntax` entries and
  `test_traceback` still trap. All eight close with question 102
  (`context/questions-for-the-owner.md`, now on main), no longer the memo.
- **A1 stays.** 069 does not remove it (EXECUTED: `test_memoryview`, `test_bool`, `test_builtin` in
  one session; without A1, once `test_memoryview` imports the `ctypes` stand-in, `test_bool` and
  `test_builtin` end `UNCAUGHT_EXC`, 153 passes against 326 with it). The stand-in still has no
  `_reset_cache`; spec 074 moves it.
- **Classes: none moved.** Every one of the 24 class lists, the deselection and both environment
  entries are exactly as before (EXECUTED, the five groups through the harness, ids compared).
- **Passes:** `cpython-fs` 3,710, `cpython-archives` 1,313, `cpython-a` 5,685 (+4, the
  `test_recursive_pickle` tests), `cpython-b` 9,534, `cpython-c` 7,867 (−2, the deselected
  `OrderedDict` tests): 28,109.
- **Fuel** (the full judge): 59.8 G (+5.1% on `s-ff5246a2c2f1a52b`), 164.6 G (+0.7%), 268.6 G
  (+9.0%), 294.4 G (−9.5%), 372.5 G (+8.0%); 1.160 T. The causes measured: the trap changes cost
  0.09 G in `cpython-a` (the group with the four ids deselected again: 268.54 G against 268.63 G),
  so the moves are the set's. 069's snapshot holds no package now: `cpython-b` with numpy and pandas
  imported first in the session costs 363.8 G, of which 4.6 G is the imports (a session that only
  imports them), so a long session's fuel depends on what is alive in it by tens of G either way;
  which of the set's changes (069, 071's window and its extra linked function, 077, 079) moves
  each group by how much is not decomposed further (INFERRED that 069 is most of it).
- **Caps:** `cpython-a` 3.7 to 4.1×10¹¹ and `cpython-c` 5.4 to 5.6×10¹¹, at least 1.5 times their
  fuel; the `/cpython` family's caps with the eight trap entries sum to 2.21×10¹² (budget 2.5).
- **Gaps:** 61 (24 classes, 8 trap entries, 1 deselection, 2 environment entries, 26 host entries).

**Rebased again onto main `2737b29`, and the delta look's findings** (the build review's delta
look at `19c4acb`: "lands once G1 is reverted and the closers are moved"):
- **The rebase.** Main gained spec 081 (it edits `guest.run`, where this branch binds
  `clock_res_get`: the three-way merge was clean), the README corrections, the owner's answers to
  questions 100 to 104 (moved into `decisions.md`; this branch's copy of question 101 goes with
  them) and the 0.1.0a7 release, so the CHANGELOG entry moves to a new `0.1.0a8 — unreleased`
  section, and 074's reservation joins main's roadmap.
- **G1.** The three spec-074 classes (`mmap-stand-in-surface`, `no-executable-file`,
  `ctypes-stand-in-surface`) close with the memo again in `python.toml`, as their gaps do; a
  replace-all had moved them.
- **Closers.** Question 102 is answered (a), so the eight trap entries close with
  `context/roadmap.md`, their reasons naming spec 078 (the runner runs each guest on a stack of its
  own, 8 MiB); question 101 is answered, so its entries (the two `no-test-modules` classes, the
  deselection and the three modules left out) close with `context/roadmap.md`, naming spec 088 (the
  judge-only binary). `python.toml` and `known_gaps.toml` agree, entry for entry (checked by a
  script: every gap's first token equals its entry's `closes_with`).

**The judge on main `2737b29`, at `85e611c`** (`-n 3`, on a private copy of
`s-c50ca51fae5eb55b-c9dcb5b8` in the worktree, so the zip's link count is 1 and not the shared
set's 554; `build/progress/latest.json` kept, its commit `85e611c`):
- Fast tier: 2060 passed, 30 skipped, 1 xfailed; lost 0, gained 1, grew 0.
- Full judge, exit 0:
  `wasi_python v1: 523/622 pass · 76 gap · 23 blocked · 0 fail   (unit suite 1579/1587, 8 skipped)`;
  `ratchet vs dfbf8e044f: lost 0 · absent 0 · unrun 0 · unrun locally 21 · gained 7 · grew 0`;
  2096 passed, 31 skipped, 76 xfailed.
- **081 moved no CPython number** beyond the run-to-run variation: passes unchanged (28,109); fuel
  against the run on `08de0c8` `cpython-a` −2.1×10⁻⁸, `cpython-archives` −2.4×10⁻⁶, `cpython-b`
  −5.5×10⁻⁸, `cpython-c` +9.0×10⁻⁵, `cpython-fs` +4.1×10⁻⁵, each within the ratchet's 1e-4.
- An earlier run on `08de0c8`, on the shared set, showed 26 of main's own rows "grown" (and the
  CPython groups varied up to 3.3×10⁻⁴); main's own tests in a scratch copy gave the same variation,
  which the delta look traces to the zip's hard links in every run root (spec 083 fixes it). That
  run is superseded by this one.

**The `--accept-judge` reason, restated:** "spec 065: CPython's own regrtest suite in the guest,
five groups (28,109 passes on s-c50ca51fae5eb55b-c9dcb5b8), 24 classes by test id, eight trap
entries closing with spec 078 (spec 071 closed four, added two), a deselection, two environment
entries and 26 host entries; question-101 entries close with spec 088; the judge states each guest
clock's resolution, guarded by a v1.2 check; the hostile-guest helper blocks on manifest; the 25
Windows host entries close with the README; facts sheets renumbered 21 and 22 after spec 076's 20".
