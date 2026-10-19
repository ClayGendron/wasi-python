# Confirmation of 065's revision against its pre-build review

- **Date:** 2026-10-18
- **Reviewer:** the same fresh agent that wrote the pre-build review
  (`065-cpythons-own-tests-in-the-release-spec-2026-10-18.md`, beside this file). I wrote none of
  the revision. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `spec/065-cpythons-own-tests-in-the-release`, rebased onto main `7d377dd`:
  `git diff b215132..6eebe09` (the revision `1e758d5` and `6eebe09`, Decision 22 and criterion 14).
  The diff touches only `context/` (READ). I also read spec 071 at `2265b90`, Decision 7 and
  question 102, and `tests/harness/needs.py`, `tests/harness/paths.py` and
  `tests/checks/test_v1_2_hostile_guest.py` for Decision 22.
- **Ran (EXECUTED, darwin-arm64, wasmtime-py 49.0.0, one guest at a time, nothing written in any git
  tree).** Under `confirm/`: `rv_confirm.py` runs regrtest on **main's frozen set
  `s-ff5246a2c2f1a52b`** (read only; compiled once to `confirm/snapshot-ff52.cwasm`).
  `rvgrant/drive3.py` is a stand-in for the revised driver. It wraps `clear_caches` without
  importing `ctypes` (Decision 4). After each module it writes `support.environment_altered`, and
  the first line of every `print_warning` regrtest made during that module, as `RVD` lines
  (Decision 13's `D … <env>`). It writes `M` lines with the revised `product`/`test` rule
  (Decision 13). Runs: `ff-cpython-b` and `ff-cpython-c` (the planned lists, trap ids and the
  deselection by full id, `-W error`, `--fail-env-changed`, the revised caps) and `ff-traceback`.
  Outputs are in `runs/ff-*`. The first `ff-cpython-*` pair is kept as `confirm/run_confirm.log`,
  for the reason C1 gives.

## Findings, each as written in

| finding | written in | evidence |
|---|---|---|
| F1 `monitoring-tool-left` | **Yes.** The class is gone. `[[deselected]]` `capi-event-generation` holds 5 ids, closer question 101, and is a gap. Criterion 2's `sys.monitoring` stand-in (drop `LINE` events) proves a regression is now red. | EXECUTED on main's set: `D test_monitoring PASSED kept`; `cpython-b` has 11 failing ids, exactly the revised Appendix A (55 − 45 + `test_c_cleandoc`) |
| F2 trap list | **Yes, and the author's count is right.** It is 4 + 2 + 1 + 1 = 8 test-level entries, plus `test_traceback`: 9. My review's "seven, 8 in all" was my arithmetic error. Budget 1.75×10¹² + 9 × 5×10¹⁰ = 2.20×10¹² (checked). The finding reads "at or after <id>". | EXECUTED: `cpython-b` and `cpython-c` ran to their end on main's set with those ids; `test_traceback` alone still traps there (2.09 G) |
| F3 `M` rule | **Yes.** A line is `product` when its top-level name is builtin or found by `PathFinder` on the product's path. | EXECUTED: `RVM generate_build_details … test` on main's set; no `product` line in either group |
| F4 env changes | **Yes, with a hole in the new entry (C1).** | EXECUTED: `D test_doctest FAILED altered ['sys.path was modified by test_doctest']`, `D test_bdb FAILED altered ['sys.path was modified by test_bdb']`; every other module of both groups `kept` |
| F5 traps by host | **Yes, with a gap for the whole-module entry (C2).** The rule "any host → every host" and "the named trap, or no trap" with a constant finding is sound for test-level entries. | READ |
| F6 host entries | **Yes, for tests.** Each system's result is checked exactly, and each entry is a gap. **Module entries leave a hole (C3).** | READ |
| F7 `test_c_cleandoc` | **Yes.** Its `match` (`deprecated to return a value…`) is in `cpython-b`'s `no-test-modules`; 21 failed and 98 errors (checked). | EXECUTED (above) |
| F8 cost | **Yes.** The archives split into 9 modules: 1,313 passes, 164 G, no failure. `cpython-fs` keeps 41 modules: 3,735 passes, 58 G. The caps are 1.50, 1.51 and 1.57 times the measured fuel. The macOS and Windows bounds come with a remedy. The table is re-derived on 063 and its dry run. | EXECUTED (the memo's table, recomputed); READ |
| F9 A1 | **Yes.** Note for the builder: `single.py` imports `clear_caches` by name (`single.py:23, 205`), so the name to wrap is `single.clear_caches`. The spec already says the builder wraps "whichever name regrtest calls". | READ; EXECUTED: drive3's wrap ran both groups with no uncaught exception |
| F10 matches | **Yes**, stated as proposals. | READ |
| F11 stage and input | **Yes.** The stage is read from the tarball's members (criterion 10 with its stand-in), and the tarball is named for the threat-model review. | READ |
| F12 housekeeping | **Yes.** Rebased onto `7d377dd`; question 99 cited where it lives; 074 comes before 0.1.0. | READ |
| Fast tier helper | **Yes**, as Decision 22, with one wrong expectation in criterion 14 (C6). | READ |

## What is open, most severe first

### C1 (medium): an `[[environment]]` entry admits any environment change in its module

- **The hole (READ).** The entry names a module, not what changed. Every cause regrtest knows sets
  the same flag:
  - a saved resource that differs (`save_env.py:347–356`: `sys.path`, `os.environ`, cwd, the
    warnings filters, …);
  - an unraisable exception (`utils.py:133–135`);
  - an uncaught thread exception (`utils.py:157–159`);
  - a file left behind (`utils.py:518–519`).

  Under `-W error`, an unclosed file's `ResourceWarning` in `__del__` becomes an unraisable
  exception. So a new leak in `test_bdb` or `test_doctest` would be admitted silently by
  `sys-path-bdb` or `sys-path-doctest`, whose reason is `sys.path`.
- **Fix.** Record what changed, and admit only that.
  - Every cause above goes through `print_warning`. The driver wraps it (in `save_env`, `utils`
    and `single`, which import it by name) and writes each warning's first line on the `D` line.
    EXECUTED: `drive3.py` captured exactly `sys.path was modified by test_doctest` and `… by
    test_bdb`.
  - Each entry gains a `changes` list, `["sys.path"]` today. Any other kind is a finding.
- **A builder hazard, seen.** `support.print_warning` reads `print_warning.orig_stderr` off its own
  global name (`support/__init__.py:1519–1530`). My first wrapper lacked that attribute. `save_env`'s
  warning then raised, and both modules became `UNCAUGHT_EXC` (EXECUTED, `confirm/run_confirm.log`:
  `test_doctest crashed … AttributeError: 'function' object has no attribute 'orig_stderr'`). The
  wrapper must copy `orig_stderr`. A unit check of the driver can hold that.

### C2 (medium): the whole-module trap entry has no "no trap" verdict

- **READ.** Decision 1 says that while an entry is open its trap check adds a red finding "if … the
  entry's test fails or errors without a trap". For `c-stack-traceback` the entry is a whole
  module. Where it does not trap, `test_traceback` runs to its end with about a hundred failures:
  96 errors and 9 failures at 2 MiB (the memo, section 3), almost all for want of `_testcapi`. So
  on any host with more stack headroom, which is exactly F5's case, the check turns red. The trap
  depends on the host, so a host that does not trap is not a defect.
- **Fix.** For a module entry, "no trap" means: the module ran to its `D` line. Its counts are
  recorded as a fact, and its failures are not judged until the entry closes and the module joins
  `cpython-a` with its classes. Add a fixed-stream case to criterion 2.

### C3 (low-medium): a module host entry drops that module's passes from every host's count

- **READ.** Decision 21: "a module entry's tests are left out of `passes` and `passed_digest` on
  every host". A new failure is still a finding, because it sorts into no class. But a pass that
  becomes a skip, or a test that vanishes, is not counted anywhere. The `fewer` ratchet cannot see
  it in that module.
- **Fix.** The entry's check records, per system, the module's pass count and digest, and checks
  them exactly on that system, as it checks the module's result. None exists today, so this is
  text only.

### C4 (low): an open trap entry never asks to be removed

- **READ.** The check's finding is constant. "no trap on this host" is only a fact, so a fixed trap
  keeps its test deselected until someone reads the facts.
- **Fix.** Show the fact as the gap's note on the scoreboard. Better, the gather lists any entry
  with "no trap" on all three systems.

### C5 (low): a deselected id is not checked to exist

- **READ.** A deselected test never starts, so the stream cannot show a stale id after a re-pin.
- **Fix.** When the tarball is present, the rules check reads the module's source and finds each id's
  class and method.

### C6 (low): criterion 14 expects the wrong need

- **READ.** `paths.artifact_dir()` returns the `WASI_PYTHON_ARTIFACTS` folder whenever that variable
  is set (`paths.py:125–128`), so "artifact dir" is met for an empty folder. The four checks are
  then blocked on `manifest`, not `artifact dir` (`needs.py:154–158`).
- **Fix.** Expect "blocked, naming `manifest`", or run the self-test with the variable unset and no
  set reachable. The stand-in (today's `_version()`) still fails either way: `FileNotFoundError` on
  `MANIFEST`.

### C7 (low; across specs): spec 071 still describes 065's old five entries

- **READ.** 071 at `2265b90`, Decision 7, says "one closes, four are renamed", and that if 071
  lands first "065's builder derives on this set: four trap entries". With 065's nine, the window
  closes four (the `test_recursive_pickle` variants) and five remain. 065's own text is consistent
  ("five trap entries, with 071's reasons"); 071 needs the matching edit.

### C8 (trivial)

- `questions-for-the-owner.md`, question 101, says the five tests are deselected "by name". The
  spec's rule is by full id.

## Verdict

**Not yet confirmed: confirmed for build once C1 and C2 are written in.** Both are short text
changes:
- C1: an environment entry names what changed, and the driver records it.
- C2: a module trap entry's "no trap" verdict.

C3 to C8 the builder can carry, or the author can fold in with them. Everything the review asked for
is in. On main's new set (`s-ff5246a2c2f1a52b`), the revised mechanisms behave as written on
`cpython-b` and `cpython-c`: the deselection, the environment entries, the `M` rule, A1 by wrap,
and the trap ids. Their failing ids are the revised Appendix A, exactly.

**One line:** every finding is written in and the plan holds on main's set, but an environment entry
must name what changed and the whole-module trap entry needs a "no trap" verdict before build.

---

# Second confirmation: C1 to C6, C8 and the F9 note (2026-10-18)

- **Reviewed:** `git diff 6eebe09..75823c9` in the 065 worktree. It touches the spec and one line of
  `context/questions-for-the-owner.md` (READ). C7 goes to spec 071 separately and is not judged
  here. I re-read the regrtest sources the new text relies on: `libregrtest/utils.py:126–175,
  510–520`, `single.py:168–182`, `save_env.py` (its `resources`), `support/__init__.py:1519–1567`
  and `support/threading_helper.py`. No new guest runs were needed; the first confirmation's runs
  on `s-ff5246a2c2f1a52b` stand. No git tree was touched.

## Each item

| item | written in | check |
|---|---|---|
| C1, environment entries | **Yes.** `changes = ["sys.path"]`; the driver records the first line of each `print_warning`; a recorded line no entry's `changes` match is a finding. The `orig_stderr` hazard and its unit check are in. Criterion 2 has the stand-in. | READ: every cause that sets `environment_altered` also calls `print_warning` (saved resources, unraisable, thread exception, file left behind, uncollectable garbage, reaped child, dangling threads), so recording the warnings sees every cause. Two small gaps follow (D1, D2). |
| C2, whole-module "no trap" | **Yes.** No trap means the module reached its `D` line. Its counts are a fact; it is red only for another trap cause, out of fuel, an `X` line, or a missing `D` or `E` line. Criterion 2 has the stream and the stand-in. | READ; sound |
| C3, module host entries | **Yes.** Each records a pass count and digest per system, checked exactly on that system. | READ; sound |
| C4, "no trap" asks to be seen | **Yes.** A scoreboard line and a gather line, neither red; `gather.py` is added to the changed files. | READ; sound |
| C5, ids exist | **Yes.** Deselected and test-level trap ids are checked against the verified tarball's source with `ast`, inherited methods in the same module included. | READ: every current id resolves that way (`TestPartialCSubclass(TestPartialC)` and the `TestPartial` mixin; `LazyImportRestrictionTestCase(SyntaxErrorTestCase)`; all in their own modules) |
| C6, criterion 14 | **Yes.** It expects `manifest`, and the stand-in's failure is named. | READ `paths.py:125–128`, `needs.py:154–158` |
| C8, question 101 | **Yes.** "by full id". | READ |
| F9 note | **Yes.** It names `single.clear_caches` (`single.py:23, 205`). | READ; one wording leftover (D3) |

## Small items for the builder (none blocks the build)

- **D1 (low): a prefix match is too loose for one resource.** `changes` matches "the start of a
  recorded warning line". `save_env`'s resources include both `sys.path` and `sys.path_hooks`
  (READ), so `"sys.path"` also admits `sys.path_hooks was modified by test_bdb`. Match the kind as
  `<change> was modified by` (the resource name exactly), or on a word boundary. Add the
  `sys.path_hooks` line to criterion 2's not-admitted streams.
- **D2 (low): an `altered` with no recorded line should be a finding.** Today every cause prints a
  warning (READ, above). If a future one sets the flag silently, an entry that matches the module
  would admit it, since no unmatched line exists. Make `D … altered` with no recorded line a
  finding.
- **D3 (trivial): Decision 4's wording.** Decision 4 still begins "the driver wraps
  `test.libregrtest.utils.clear_caches`", then names `single.clear_caches` as the name to wrap.
  Wrapping the `utils` attribute alone changes nothing, because `single` holds its own reference. One
  sentence should say what to wrap.
- **D4 (trivial): criterion 2's unraisable stream.** It writes `…|Warning -- Unraisable exception`.
  The recorded first line is the message `print_warning` receives, `Unraisable exception`; the
  `Warning -- ` prefix is added only when it prints (`support/__init__.py:1519–1525`). The verdict
  is the same either way (a finding); only the fixture text differs.

## Verdict

**Confirmed for build.** C1 to C6, C8 and the F9 note are written in correctly, and the new text
breaks nothing I can find. The builder carries D1 to D4 (D1 and D2 are one-line rules in the
environment entry's matching). C7 is spec 071's.

**One line:** every confirmation item is in; build it, matching environment kinds exactly and
treating a silent `altered` as a finding.
