# Review of 065 — CPython's own tests in the release (the specification, before build)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I wrote none of the spec, the
  memo, its addendum or its evidence. I read `AGENTS.md`; the constitution (§5.2, §5.6, §5.7);
  `context/decisions.md` (Decision 34 on main; question 99's answer, which sits on the 063
  branch's `decisions.md`, not yet on main); the memo
  `research/2026-10-18-cpythons-own-tests-under-the-runtime.md` with its evidence and the
  drafting addendum; spec 063 as it stands on its branch (`070ee4c`, after its second branch dry
  run); spec 069's paragraph on 065 (`68062f3`); the pre-build review of 060, for the shape; and
  the pinned sources the spec rests on: `Lib/test/libregrtest/` (`filter.py`, `findtests.py`,
  `result.py`, `results.py`, `single.py`, `utils.py`), `test_monitoring.py`,
  `test_functools.py`, `test_syntax.py`, `test_traceback.py`, `test_inspect/test_inspect.py`,
  `test_io/utils.py`, `test_ast/test_ast.py` in `build/Python-3.15.0`. Each claim is labelled
  EXECUTED, READ or INFERRED.
- **Reviewed:** `spec/065-cpythons-own-tests-in-the-release` at `21c327c` (commits `6b4c764`, the
  draft, and `21c327c`, the renumbering), drafted from `e21623e`. The diff touches only `context/`
  (READ). Against main `ef1441b` the diff also shows `context/reviews/0.1.0a6-security-review-2026-10-18.md`
  deleted: that is the branch's older base, not a change of the spec's (F10).
- **Ran (EXECUTED, darwin-arm64, wasmtime-py 49.0.0, the frozen set
  `build/sets/s-4eb5418a2b1bb553-c353b1d9`, read only; its snapshot and zip are byte-identical to
  the memo's `s-4eb5418a2b1bb553`).** One guest at a time; nothing written in any git tree. The
  drafting stage (`build/reviews-evidence/065-spec/stage`) and the memo's serialized module were
  read in place. Scripts and outputs are in `probes/` and `runs/` beside this file:
  - `probes/rv_run.py`: one regrtest session through `tests/harness/guest.py`, the drafting
    driver at `/cpy/judge/drive.py`, no `--junit-xml`.
  - `probes/rv_group.py` + `probes/rvgrant/drive2.py` + `probes/run_groups.sh`: the plan's four
    groups, one session each, in the plan's order, with `-W error`, `--fail-env-changed`, `-v`,
    the trap ids deselected by full id, the spec's caps, and an `M`-line dump at the end
    (`RVM`/`RVE` lines). A stand-in for the spec's driver, not it.
  - `probes/analyze_groups.py`, `probes/per_module.py`: failing ids against Appendix A
    (`allowances.tsv`), env warnings, module states.
  - `probes/match_check.py` → `probes/match_check.out`: Decision 12's proposed matches replayed
    over `allowances.tsv`'s recorded reasons.
  - Single-module runs: `mon-base`, `mon-ignore` (test_monitoring), `ft-onlyC`, `ft-C-CS`,
    `ft-3`, `ft-4` (test_functools), `tb3-nojunit`, `tb4`, `tb5`, `tb6` (test_traceback),
    `tarfile`, `pathlib`, `pathlib2`.
  - `gh run view 39182550825` (063's second branch dry run): job timings, read only.

  - `probes/fast_tier.txt`: `uv run pytest -m "not slow" -n 3` in the 065 worktree, without
    `--accept` (see the end).

## The plan, run as four sessions (EXECUTED)

The central probe. The plan's four groups, each one guest session, in the plan's order, under
`-W error` and `--fail-env-changed`, with the trap tests deselected by full id:

| group | fuel | Decision 10 expects | cap (Decision 10) | cap / fuel | wall here | failing ids | Appendix A | env warnings (stderr) | `M`-line candidates |
|---|---|---|---|---|---|---|---|---|---|
| `cpython-fs` | 219.7 G | about 235 G | 3.6×10¹¹ | 1.64 | 194.2 s | 67 | 67, identical | none | none |
| `cpython-a` | 246.3 G | about 230 G | 3.5×10¹¹ | **1.42** | 42.8 s | 9 | 9, identical | none | none |
| `cpython-b` | 325.3 G | about 295 G | 4.5×10¹¹ | **1.38** | 58.2 s | 56 | 55, plus `test_c_cleandoc` (F7) | `sys.path was modified by test_doctest` (F4) | none |
| `cpython-c` | 344.0 G | about 355 G | 5.4×10¹¹ | 1.57 | 62.5 s | 32 | 32, identical | `sys.path was modified by test_bdb` (F4) | `generate_build_details` (F3) |

- `cpython-c` first trapped at 267.1 G, in `test_syntax.LazyImportRestrictionTestCase.test_error_on_parser_stack_overflow`
  (`runs/cpython-c-first-trap.*`); it ran to its end once that id was deselected too (F2).
- Passes, counted from `-v`'s "ok" lines, agree with Decision 10's expected numbers within the
  parser's noise (a test that prints puts its "ok" on a line of its own; `test_zipimport_support`'s
  doctests print 342 such lines). The spec's stream will count exactly; I make no claim on the exact
  pass counts beyond "no module lost a block of passes" (`probes/per_module.py`).
- My runs carry `-v` and a second small grant (`/rv`), so their fuel is not the spec's; the shape
  (two caps under 1.5× their run) holds. The wall times are on a machine at load 20 to 140.

So the spec's central claim stands: the plan runs as four sessions, and its failures are Appendix
A's 163 ids, test for test, with one addition (F7), once the trap list is complete (F2).

## What holds

- **regrtest's `-i` matches full ids exactly (READ).** `filter.py:20–27, 52–77`: when every
  pattern contains a dot and no `?*[]`, the match is `set(patterns).__contains__`. A
  `test.<module>.*` pattern switches the group to `fnmatch`, which still matches a dotted full id
  only against the whole id (the dotted parts tried second have no dots). Decision 1's rule is
  right, and my hunts show why it matters (F2).
- **The universe adds up (EXECUTED).** The four plan lists, `not-selected.txt` and `test_traceback`
  are 557 distinct modules, equal to the memo's `per-module-results.tsv` (`comm`: no difference).
  Decision 10's sums (542 modules, 28,096 passes, 1.70×10¹² of caps), Decision 12's (26 classes,
  163 ids, 66 failed and 97 errors) and the trap budget (1.95×10¹²) are arithmetically right for
  what they count. `test_monitoring` is last in `cpython-b`; `test_profiling` is in `cpython-a`.
- **The order is fixed and the groups are leak-free for outcomes (EXECUTED).** `findtests` sorts
  (`findtests.py:64`); no `--randomize`; the four sessions above gave Appendix A's failing ids
  exactly (one addition, F7), so composition moved no test outcome. Fuel repeats closely:
  `test_pathlib` twice gave 6,946,225,840 and 6,946,222,351 (5×10⁻⁷, within the ratchet's 1e-4);
  the memo's `test_json` repeated to the instruction.
- **The `sys.executable`, `-W error`, `-bb` and A1 analyses are sound as far as they go (READ).**
  `platform.py`'s empty-executable branch, the bootstrap's refusal of `-W` and `-b`, and
  `clear_caches()` calling `ctypes._reset_cache()` (`utils.py:254–259`) are as stated.
- **Classification: judge-only is right by AGENTS.md's letter (READ).** The diff will touch no
  file under `scripts/` or `recipes/`, no line of `downloads/SHA256SUMS`, and not `release.yml`
  (063's matrices list shards, not groups; `release.yml:398, 519, 648` on the 063 branch). It
  changes no artifact. The `/cpython` grant is a judge-side preopen, not a guest import or export,
  so §5.6's second review is not required; the lane asked for it anyway, which is right because
  the change reaches the release.
- **The test sources are pinned (READ).** `Python-3.15.0.tar.xz` is `downloads/SHA256SUMS:16`,
  fetched from python.org by `scripts/00_download.sh:90`'s `get` line, which 063's `fetch.py
  --shard` reads; the stage takes tarball members only and the checks tie to MANIFEST's `pin` line.
  `apply_patches.sh:23` exits 0 for an absent patch folder, so the applier is harmless for CPython.
  Two refinements in F11.
- **The release-only risk is named.** Because a judge-only landing can turn the release red on
  Windows without the lane seeing it, criterion 12's branch dry run before landing is required, and
  it is.
- **The job count claim holds in kind (READ).** 065 adds no shard, no matrix leg and no macOS job.
  The numbers it quotes from 063 are stale (F8).

## Findings, most severe first

### F1 (high; judge honesty). `monitoring-tool-left` admits 45 failures that one deselection removes

- **The cause (READ).** `MonitoringTestBase.setUp` registers three tool ids and only `tearDown`
  frees them (`test_monitoring.py:122–139`). `TestCApiEventGeneration.setUp` calls
  `super().setUp()` and then `import_helper.import_module("_testcapi")`, which raises `SkipTest`
  (`:2598–2601`). A skip in `setUp` runs no `tearDown`, so the tools stay registered, and every
  later `MonitoringTestBase` test fails its own `setUp` assertion
  (`'test TestCApiEventGeneration' is not None`).
- **Measured (EXECUTED, `runs/mon-base.*`, `runs/mon-ignore.*`).** `test_monitoring` alone: 98
  run, 45 failures, 4 skipped. With `-i 'test.test_monitoring.TestCApiEventGeneration.*'`: 93 run,
  **0 failures**, 5 skipped. So 39 tests pass and 2 more skip that the class would admit as
  failures.
- **Why it matters (rule 4).** Those 41 tests fail in `setUp`, before their bodies run. Any
  regression in `sys.monitoring` (line, instruction, branch, local events, the optimizer's
  interaction) fails the same way with the same message and sorts into the class: the class
  hides the whole subsystem. It is not 45 named limitations; it is one skipped class and a
  cascade. Decision 5 already refuses to admit the same leak when it crosses modules; inside the
  module it is no different.
- **Fix.** Deselect the five `TestCApiEventGeneration` tests in `cpython-b` by `-i`, as a named,
  visible entry: a `[[deselected]]` (or reuse the trap entry's mechanism without the trap check)
  with its ids, its reason ("needs `_testcapi`; its `setUp` leaves three monitoring tools
  registered when it skips") and closer question 101, shown on the scoreboard as a gap so it cannot
  be forgotten. Drop the class; `cpython-b`'s expected passes rise by about 39; Appendix A loses 45
  ids. The facts sheet (Decision 20) states the upstream bug as fact, not INFERRED. The ordering
  rule can stay as cheap defence. 050's mechanism has no deselection entry today, so this is a
  decision 065 must make, not a builder's choice.

### F2 (high; the trap list). Two trap entries are each several tests, and the numbers built on five are wrong

- **`test_functools` (EXECUTED, `runs/ft-*`).** With only `TestPartialC.test_recursive_pickle`
  deselected the module traps at `TestPartialCSubclass.test_recursive_pickle`; with both, at
  `TestPartialPy…`; with three, at `TestPartialPySubclass…`; with all four, 334 run, 10 skipped,
  0 failures (324 passes, the memo's number). The method is inherited by four classes
  (`test_functools.py:443, 617, 676, 689, 696`).
- **`test_syntax` (EXECUTED, `runs/cpython-c-first-trap.*`).** `cpython-c` with Decision 1's one
  id trapped at `LazyImportRestrictionTestCase.test_error_on_parser_stack_overflow`, which inherits
  from `SyntaxErrorTestCase` (`test_syntax.py:3620`). With both ids it ran to its end.
- **`test_doctest` and `test_exceptions`** are one test each (READ; EXECUTED: `cpython-b` ran to
  its end with one id each).
- **So:** 7 test-level trap entries plus `test_traceback`, 8 in all; 34 gaps, not 31; criterion 4's
  "5 trap checks"; the trap budget 1.70×10¹² + 8 × 5×10¹⁰ = 2.10×10¹² (still under 2.5×10¹²).
  Decision 1's table, the Kind line, criterion 4, Decision 16's sum, Decision 18's README text
  ("the five tests") and the CHANGELOG line change with it. The memo's hunt deselected by bare
  name, which is exactly the masking Decision 1 warns about; no count from it should be carried
  over without a full-id rerun.
- **`test_traceback`, whole module: justified, but not by "two strikes" (EXECUTED, `runs/tb*`).**
  With full ids the hunt finds more trap sites (`PyExcReportingTests.test_exception_group_depth_limit`
  as well as the C one), and then a trap that is not any test's: it fires right after
  `TestTracebackException_ExceptionGroups.test_comparison` at the same fuel (6,527,384,023 and
  6,527,390,454) whichever test follows (`tb4`, `tb6`), so the test the stream names is innocent.
  INFERRED: deferred deallocation of a deep structure (the collector or a `setUp`), recursing in C.
  Write that as the reason for the whole-module entry.
- **And Decision 13's trap naming.** "The last `S` line" can name an innocent test. The finding
  should read `trap: … at or after <id>`, and the spec should say a trap's named test is where it
  surfaced, not necessarily its cause.

### F3 (medium; a false red). Decision 13's `M` rule fails `cpython-c` as planned

- **Measured (EXECUTED, `runs/cpython-c.out`: `RVM generate_build_details /cpy/Tools/build/generate-build-details.py`).**
  `test_build_details` puts `sys.modules["generate_build_details"]` in place before it executes a
  file that is not in the stage (`test_build_details.py:19–30`). The import fails, the test skips,
  and the half-made module stays, with a `__file__` under `/cpy/` and a name outside `test.`.
- Decision 13 makes that a group finding, so `cpython-c` is red on its first complete run.
  Criterion 4 words the intent differently ("no `M` line for a **product** module").
- **Fix.** Check the intent: a module the product provides (a builtin, or a name importable from
  the stdlib zip or the compiled-in packages) must not have a `__file__` under `/cpython/`. A test's
  own helper modules, by any name, are then not findings. Add a unit check with this exact case.

### F4 (medium; determinism of the verdict). `--fail-env-changed` is blind in every module that fails

- **READ.** `TestResult.set_env_changed` changes the state only when it is `None` or `PASSED`
  (`result.py:178–180`); and a run with any failure exits 2, never 3 (`results.py:84–98`). So in
  the 28 modules that hold class members (`test_io`, `test_mmap`, `test_bdb`, `test_doctest`,
  `test_inspect`, `test_pdb`, …) an environment change is invisible to the `D` line and the exit code.
- **EXECUTED.** It happens today: `sys.path was modified by test_doctest` in `cpython-b` and
  `by test_bdb` in `cpython-c` (my runs' stderr); and in the memo's own shard sessions
  (`build/cpython-suite-research/runs-shards/*.err`, `test_bdb`, 18 tempcwd entries). Decision 5's
  "the memo's three shard sessions had none" rests on a grep for the summary line that a `FAILED`
  module never reaches. Both are side effects of `read-only-eperm`: `forget()` raises before the
  test restores `sys.path`. regrtest restores the saved items afterwards, so nothing leaks; but the
  next such change, in a failing module, would not be seen.
- **Fix.** The driver writes `support.environment_altered` per module (for example
  `D <module> <state> env`), and an altered environment is a finding unless an entry names that
  module with its reason and closer (`test_bdb` and `test_doctest` today, closed with
  `read-only-eperm`'s facts sheet). Correct Decision 5's sentence.

### F5 (medium; determinism across hosts). Where the guest traps depends on the host

- **READ.** wasmtime's `max_wasm_stack` is "the maximum stack size, in bytes, that JIT code can
  use" (wasmtime-py's `_config.py:393–405`): native stack, consumed per wasm frame by code
  Cranelift generates for that host. aarch64 and x86-64 frames differ, and Windows x64 has its own
  ABI and stack probes.
- **INFERRED.** The memo and every probe here ran on darwin-arm64. Linux CI (x86-64) runs all four
  groups. A test near the limit may trap on one architecture only, or a trap entry may not trap
  there (its check then passes on one host and is a gap on another). Criterion 3's "the guest is
  the same bytes on every host, so a host is not an explanation" is false for stack exhaustion.
  CPython's suite probes recursion limits on purpose (`test_json`, `test_pickle`, `test_copy`,
  `test_isinstance`, `test_richcmp`, `test_compile`, …), and no check in the judge today exercises
  deep C recursion across hosts (`grep` of `tests/` and `src/`: none).
- **Fix.** State the rule before build: a trap seen on any host becomes a trap entry deselected on
  every host (one verdict), by a reviewed judge change, closed by 071; while the defect lasts, a
  trap check's verdict is "the named trap, or no trap" on every host, so a host where it does not
  trap is not red, and its record says which. Correct criterion 3's sentence. The branch dry run
  (criterion 12) is then the first evidence, and its landing notes list each host's traps. Spec
  071 should know this too: its fix must hold on x86-64 and Windows, not only on the lane's Mac.

### F6 (medium; judge honesty across hosts). Host entries are weaker than they need to be, and cover only tests

- **An outcome set loses information.** A host entry with `outcomes = ["passed", "failed"]`
  accepts a pass-to-fail regression on every host. Record each system's own outcome instead
  (`linux = "passed"`, `windows = "error"`, `macos = "passed"`), checked exactly on that host and
  still left out of `passes` and `passed_digest` everywhere, so G5's one verdict holds and nothing
  is accepted that was not seen.
- **They are invisible.** A host entry is not a gap; a growing list of tests left out of the count
  shows nowhere. Show their count on the scoreboard (or make each a gap closed by its closer).
- **Only test-level differences are covered.** A module that is `ENV_CHANGED`, has an `X` line,
  is `RESOURCE_DENIED`, or traps on one host has no entry; the only remedy the spec names is moving
  a module off macOS for fuel. Say what happens for each kind (I recommend: the module moves to a
  Linux-only group by a reviewed judge change with its reason, the same rule as for macOS fuel),
  and reconcile it with 063 Decision 18's "a system is never dropped from a shard to get a pass".
  Windows is unmeasured for all 50 file-system modules, so this will be needed (INFERRED).

### F7 (medium-low; the plan's numbers). `-W error` changes an outcome the seven-module probe did not reach

- **EXECUTED (`runs/cpython-b.out:7824`).** `test.test_inspect.test_inspect.TestRetrievingSourceCode.test_c_cleandoc`
  errors: `DeprecationWarning: It is deprecated to return a value that is not None from a test
  case`. The test does `return unittest.skip("requires _testinternalcapi")` instead of raising
  (`test_inspect.py:785–789`). Without `-W error` it counted as a **pass** in the memo, having
  tested nothing; with it, it is an error. `-W error` is the better judge here.
- **So** Appendix A has 164 ids (a `no-test-modules` member in `cpython-b`, matched on that
  warning, closer question 101), `cpython-b`'s expected passes lose one, and the upstream facts
  sheet gains the `return unittest.skip` bug. Decision 8's "Both gave … the same" holds for its seven
  modules only; say so.

### F8 (medium-low; cost). The quoted 063 numbers are stale, and the file-system group is bound by I/O, not fuel

- **063 changed after 065 was drafted (READ, 063 at `070ee4c`).** It added an `own-runner` shard
  on all three systems and took `own-rest` off Windows: 18 judge jobs plus 3 `verify` run at once,
  and its second dry run (39182550825) measured the shard stage: Linux upstream shards 73 to 198 s,
  `own-embedding` 281 s on Linux, the judge stage 4.7 minutes; `own-rest` on macOS already waited
  about 50 s for a macOS slot. 065 still adds no job; Decision 7's table and text should be
  re-derived on 063 as landed.
- **The time model misses host I/O (EXECUTED).** My `cpython-fs` session took 194.2 s for 219.7 G
  (0.88 s/G) while the other three took 0.17 to 0.18 s/G; `test_tarfile` alone took 217.8 s for
  62.9 G; the memo saw 194 s for it once and its 50 modules summed 306 s of wall. Decision 7 prices
  `cpython-fs` at fuel × 0.23–0.43 s/G plus sleeps. On Linux the change to the critical path is
  probably still small (INFERRED from the dry run: the heaviest Linux shard would be near
  `own-embedding`'s 281 s). On Windows (`upstream-windows`, 123 s today) and macOS
  (`upstream-macos`, 86 s), `cpython-fs` plus the full CPython unpack may become the longest leg.
  State a bound for those two legs and the remedy if exceeded (for example, `test_tarfile` and
  `test_zipfile` in the Linux copy only, by a reviewed judge change with its reason), and make
  criterion 12 record each leg's time against it.
- **The lane's serial judge** grows by more than "about 4 minutes" (criterion 11): 1.1 T of fuel
  at the quiet rate is about 3 minutes, plus about 50 s of real sleeps, plus the file-system
  group's I/O (minutes under load). Say "INFERRED, 4 to 8 minutes" and record it.
- **Caps.** Two groups ran above 1/1.5 of their cap (`cpython-a` 1.42×, `cpython-b` 1.38×).
  Decision 10's own rule raises them at the first run; fine, but the caps in the table should be
  read as provisional, and the budget check (2.5×10¹²) still fits.

### F9 (low). A1 as drafted stops working on spec 069's snapshot

- **READ.** The drafting driver patches `ctypes` only if it is in `sys.modules` when the driver
  starts (`probe_drive.py`). With 069 it is not; the first module that imports `ctypes` puts the
  stand-in there, and `clear_caches()` then raises after it (the memo: every module "failed
  (uncaught exception)"). Decision 4 says A1 is still needed, which is right, but not how.
- **Fix.** Name the mechanism that works on both snapshots: wrap `test.libregrtest.utils.clear_caches`
  (or install a one-name import hook) rather than importing `ctypes` in the driver, which would
  pre-import it for every test.

### F10 (low). Decision 12's matches are proven for 137 of 163 ids, not all

- **EXECUTED (`probes/match_check.out`).** Replaying Decision 12's table, in order, over
  `allowances.tsv`'s recorded reasons, 26 ids fall into no class: 17 have an empty recorded reason
  (11 `test_monitoring`, 3 `test_pdb`, …) and the rest's recorded reason is not the line the stream
  will write. `verbose_ids.py` keeps the **last** unindented line of unittest's report (a diff line,
  `'lineno'`, `</body></html>`), while Decision 13's reason is the **first** line of
  `format_exception_only`. So "written against each reason's first line" overstates the evidence.
  Say the builder's first run confirms every match against the stream's own reasons (criterion 3
  half says it).

### F11 (low). Stage from the verified tarball, and name the new CI input

- Decision 15 copies member bytes from `build/Python-<v>`, the build's working tree; the tie checks
  the tarball's hash, not the staged bytes. In CI the tree is fresh; on the lane it is whatever the
  build left. Staging each member from the verified tarball (or hashing the staged files against
  it) makes the lane's stage provably CI's, which 063 Decision 5 says the fuel needs.
- The CPython tarball becomes a new input on all three systems' judge runners. 063 Decision 19
  names its own new inputs for the release's threat-model review (§5.6); 065 should add this one.

### F12 (low; housekeeping)

- The branch is drafted from `e21623e`; against main `ef1441b` its diff deletes the a6 security
  review, and main has moved on (`a0de463`, 0.1.0a6 tagged). Rebase before build.
- Question 99's answer is in the 063 branch's `decisions.md`, not on main; 065 builds after 063,
  so this resolves itself, but the Problem should cite where.
- Decision 2 calls `platform.libc_ver()` raising "in every embedder's program" a defect and gives
  it to 074, but no document says whether 074 comes before 0.1.0. Say which.

## Notes (no change needed, or the builder's to carry)

- **N1.** `test_ast` (220 test methods) is `not_selected` for one module-level line,
  `STDLIB_FILES = [fn for fn in os.listdir(STDLIB) …]` (`test_ast/test_ast.py:41`; the memo's
  `runs/test_ast.err`). That is an upstream assumption like the unguarded `_testcapi` imports; put
  it in Decision 20's facts sheet, so the closer can become upstream and not only the README.
- **N2.** `no-ctypes` in `test_io` hides the read half of `test_raw_file_io` and
  `test_buffered_file_io`: `byteslike()` calls `ctypes.resize` (`test_io/utils.py:10–25`) because
  the stand-in imports. It is a real, named limitation with its closer, but it removes the core of
  the "widest probe of the file system". Spec 074, which revisits the stand-ins, should weigh it.
- **N3.** A trap check whose `-m` id no longer exists exits 4 (`EXITCODE_NO_TESTS_RAN`); Decision
  13 already makes any exit other than 0 or 2 a finding, so a rename cannot pass silently.
- **N4.** The memo's 512 KiB default stack is INFERRED against wasmtime-py's docstring, which says
  2 MB; the memo also found 2 MiB changes outcomes, so the effective default is smaller. That is
  071's to settle; it does not change 065.
- **N5.** 063's plan rules hold for the new placement: `cpython-fs` is in exactly one shard whose
  systems include Linux, and in the macOS and Windows shards without overlap on any system.

## Fast tier

EXECUTED, in the 065 worktree, `uv run pytest -m "not slow" -n 3 -p no:cacheprovider`, no
`--accept`, no artifact set in the worktree (`probes/fast_tier.txt`): 1,286 passed, 311 skipped,
4 failed, 278 checks blocked on `artifact dir`. The 4 failures are
`test_matplotlib_data_is_granted_read_only` and `test_usr_local_lib_holds_only_the_zip` (plain and
snapshot); their `_version()` helper asserts on a missing artifact dir instead of being blocked by
the need. With `WASI_PYTHON_ARTIFACTS` set to the frozen set the four pass
(`probes/fast_tier_four_with_set.txt`: 4 passed, lost 0). The branch touches only `context/`, so
none of this is 065's; the fail-not-block helper is a small pre-existing judge defect, worth a line
for spec 070 (the judge's small follow-ups). No rules check objects to the branch's `context/`
changes.

## Verdict

**Ready once F1 to F6 are written in** (F1 and F2 as decisions with their corrected numbers; F3
and F4 as rules in Decisions 13 and 5 with unit checks; F5 and F6 as stated rules for host
differences). F7 to F12 are corrections the builder can carry, but are cheaper written in now. The
plan itself is sound: run as four sessions on the frozen set it reproduced Appendix A test for test,
with one addition.

**One line:** the plan reproduces its 163 failures exactly, but one class hides `sys.monitoring`
behind a cascade, the trap list is two entries short of reality, the `M` rule and env checks would
misjudge today's runs, and host differences (stack depth, Windows files) need stated rules before
the release runs it.
