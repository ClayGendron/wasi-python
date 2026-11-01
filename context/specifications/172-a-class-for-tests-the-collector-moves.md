# 172: A class for tests the collector moves

- **Status:** built 2026-10-31 on `spec/172-a-class-for-tests-the-collector-moves`, not landed. The owner approved the judge change on 2026-10-31 (`../decisions.md`, "A class for tests the collector moves").
- **Date:** 2026-10-31
- **Owner:** Clay Gendron
- **Kind:** a judge change (`tests/harness/upstream.py`, `tests/upstream/tqdm.toml`, three of tqdm-smoke's list files, `tests/known_gaps.toml`). Not structural: it changes no file under `src/`. No pre-build review: it touches neither the guest's imports or exports, the artifact set nor the build recipe (constitution §5.6).
- **Depends on:** landed: 050 and 067 (the classes, their list files and the class checks). In flight: 166's second pull request (#71, pandas 3.1.0), which moves tqdm-smoke's lists to the other state; 172 is rebased onto it.
- **Research it stands on:** the runs of #67, #71 and #81 on 2026-10-31, and the three local runs below (EXECUTED).

Labels: EXECUTED means run and seen; READ means read from a file, cited; INFERRED means reasoned.

## The problem

Two of tqdm's tests, `tests/tests_perf.py::test_iter_basic_overhead` and `::test_iter_overhead_simplebar_hard`, run in tqdm-smoke, a normal-tier group. An earlier asyncio test leaves an event loop behind. The garbage collector frees it during whichever of the two runs when it fires (EXECUTED, the streams below):

- that test errors at setup with `Exception ignored while calling deallocator <function BaseEventLoop.__del__>` and never runs;
- the other runs, fails with `TqdmMonitorWarning: tqdm:disabling monitor support`, and errors at teardown with `` `tqdm` instances still in existence POST-test ``.

Which test is which depends only on the set's allocations. Neither passes in either state. Any change to the set can flip them. A flip moves members between three classes (`no-threads`, `no-threads-error`, `no-asyncio-loop-error`), and the class checks go red. It happened on #67, #71 and #81 on 2026-10-31.

The judge cannot hold this today. `judge_group` (`tests/harness/upstream.py:802`) gives each outcome to the first class whose outcome and pattern fit. A class cannot be limited to particular tests. The causes are tqdm's ordinary no-threads causes, which about 200 other outcomes match. No merge of classes holds it.

## Decisions

### 1. A class may name its tests

A class may carry `nodes = [...]`, the node ids it is for. Such a class is **node-limited**. It claims an outcome only for its own nodes, only when the reason matches its pattern, and before any other class. It names its outcomes with `outcomes = [...]` in place of `outcome`, so one class holds a test that fails in one run and errors in the next.

### 2. Its tests must fail, and only for its causes

An outcome of a named test that is not the class's is a finding of the group. A failure or error for another cause is `unexpected …`, never handed to an ordinary class. A pass or a skip is `passed <node>, which class <id> says fails`. The class's list is its `nodes`; it has no list file. So a named test that passes, is absent, or fails for another cause is also `-<node>` in the class check. Every other test keeps exact class membership.

### 3. The rules hold its shape

`class_shape_errors` (`tests/harness/upstream.py:973`), called by `rule_errors`, refuses: `outcome` and `outcomes` together; an outcome other than `failed` or `error`; `outcomes` without `nodes`; `nodes` that are empty, unsorted or repeated; `nodes` in CPython's family, whose judge does not read them. `rule_errors` refuses a node named by two node-limited classes of one group, and a node-limited class without its gap. A node-limited class's list file would be a stray file, which the rules already refuse.

### 4. tqdm-smoke gets `collector-timing`

One class, `collector-timing`, names exactly the two tests, with `outcomes = ["failed", "error"]`. Its pattern is the union of `no-threads`' and `no-asyncio-loop-error`'s: the three causes the owner named (no threads, no event-loop socket, an unraisable warning at teardown). The two tests leave the three lists. Its gap and the three changed gaps close with `docs/reference/limitations.md`, as their siblings do.

### 5. jinja2-r is follow-up

jinja2-r's flips include tests moving between passing and failing. The owner's rule covers tests that fail in every state, so it does not apply there. A specification of its own handles it if it recurs.

## Intent

A change to the set that only moves the collector's timing no longer turns tqdm-smoke red. The two tests are still held to fail, and only for the named causes.

## Design

- `tests/harness/upstream.py`: `Klass` gains `nodes` and `outcomes` and the method `claims`; `klass_of` reads a class from its table (also used by `tests/harness/packages.py`); `judge_group` claims the named tests first through `_limited_finding`; `class_list` gives a class's list; `class_shape_errors` and `rule_errors` hold Decision 3.
- `tests/checks/test_v1_3_upstream_suites.py`: `test_upstream_class` reads `class_list`.
- `tests/upstream/tqdm.toml`, `tests/upstream/expected/tqdm-smoke/{no-threads,no-threads-error,no-asyncio-loop-error}.txt`, `tests/known_gaps.toml`: Decision 4.
- `tests/unit/test_upstream.py`: eleven rows.

## Scope

**In:** the node-limited class, its rules, tqdm-smoke's class. **Out:** jinja2-r (Decision 5); CPython's judge (`tests/harness/regrtest.py`), which refuses `nodes`.

## Acceptance criteria

1. A node-limited class claims its tests in either order and outcome, before an ordinary class whose cause also fits. Unit row `test_a_node_limited_class_claims_its_nodes_first_and_in_either_outcome`, seen failing first.
2. A named test that passes or fails for another cause is a group finding. Unit row `test_a_node_limited_classs_test_that_passes_or_fails_for_another_cause_is_a_finding`, seen failing first.
3. A node-limited class's list is its nodes, and an absent one changes the digest. Unit row `test_a_node_limited_classs_list_is_its_nodes_and_an_absent_one_is_a_finding`, seen failing first.
4. The rules of Decision 3. Unit rows `test_a_node_limited_class_needs_no_list_file_but_its_gap`, six cases of `test_a_node_limited_classs_shape_is_held_by_the_rules` and `test_a_node_limited_class_in_cpythons_family_is_refused`, each seen failing first.
5. tqdm-smoke's checks give the same verdicts and the same digest for every class in both states. EXECUTED on three sets (Landing notes).

## Landing notes

**Seen failing first** (EXECUTED, 2026-10-31): the ten unit rows failed with `Klass` given its two fields and no behaviour (10 failed), then passed. The eleventh, for CPython's family, was added at the review: it failed with the refusal removed and passed with it restored.

**Both states** (EXECUTED, 2026-10-31). tqdm-smoke's six checks, run locally on three sets:

| set | `test_iter_basic_overhead` | `test_iter_overhead_simplebar_hard` |
|---|---|---|
| A: dev's pins (165's build, CPython 3.15.2, pandas 3.0.6) | fails, errors at teardown | errors at setup |
| B: 169's build (zstd) | errors at setup | fails, errors at teardown |
| B: 166's build (pandas 3.1.0) | errors at setup | fails, errors at teardown |

Before the change, A passed and both B sets failed three class checks. After it, all three sets pass the suite and match all six gaps with the same digests: `collector-timing` 2 findings, `972ddf3843c5`; `no-asyncio-loop-error` 10, `5e4afad71ed0`; `no-threads-error` 98, `77e1b0dfaea7`; `no-threads` 116, `53093d631048`; `no-processes` and `no-processes-error` unchanged. The streams differ in those four lines alone, save for addresses.

**After the rebase onto `9c0d879e`** (EXECUTED, 2026-11-01). #71 had moved the lists to state B. The conflicts were resolved to dev's side less the two tests, so the three lists are byte for byte the ones measured above. 165's and 166's sets left with their worktrees, so the checks ran again on 167's build (state A), 169's and 175-176's (state B): all pass with the digests above.

The pull request, its run and its review are to be written at the landing.
