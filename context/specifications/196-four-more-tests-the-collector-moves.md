# 196: Four more tests the collector moves

- **Status:** built 2026-11-17 on `claude/project-thread-5s6fa0`, from `dev` at `70275241`, not landed. It is the step 182 provides for (its "What is inferred, and what the next run gives"): a test a release run names as moved by the collector is added to its class's `collector_moves`, as its own judge change with its reason. Its authority is the owner's choice for such tests, "Stop counting them" (2026-11-16, `182-a-class-for-tests-the-collector-flips.md`).
- **Date:** 2026-11-17
- **Owner:** Clay Gendron
- **Kind:** a judge change (`tests/upstream/jinja2.toml`, `tests/upstream/expected/jinja2-r/no-asyncio-loop.txt`, `tests/known_gaps.toml`, a release ledger file). Not structural: nothing under `src/` or `tests/harness/` changes. No pre-build review: it touches neither the guest's imports or exports, the artifact set nor the build recipe (constitution §5.6).
- **Depends on:** landed: 182 (`collector_moves`), 181 (the class's last re-pin). Blocks: the 0.1.5 release pull request, #120; and the weekly run's issue, #116.
- **Research it stands on:** the 0.1.5 release pull request's run 43982122112 on `70275241`, job 133714403059 (`upstream-release-039`), its failure section and moved line (READ). The run's record artifact is refused by this environment's proxy, so the job log is the source; 182's moved line names every member that joined or left.

Labels: EXECUTED, run and seen; READ, read from a file or a log, cited; INFERRED, reasoned.

## The problem

Run 43982122112 judged 150 jobs: 138 passed, 10 were skipped as publishing and the steps after a green run, and one failed, shard `upstream-release-039`, with `ci-status` red behind it (READ). In that shard only `test_upstream_class[jinja2-r-no-asyncio-loop]` failed: 106 findings, `b6be1b9ee02b`, where its gap holds 102, `ea1eb2ac4985`. Its moved line: `+tests/test_ext.py::TestExtensions::test_debug; +tests/test_loader.py::TestModuleLoader::test_weak_references; -tests/test_async_filters.py::test_groupby_tuple_index[<lambda>1]; -tests/test_async_filters.py::test_simple_select_attr[<lambda>1]` (READ). The ratchet line: `lost 0 · absent 0 · unrun 0 · gained 0 · grew 0` (READ). `no-asyncio-loop-error`, fontTools' `counted-clock`, pydantic's and pydantic-core's classes all held.

This is the case 182's "What is inferred" left open: its named tests are the ones seen moving, not every test the collector can move, and the release pull request names the rest. `test_weak_references` sets its environment to `None` and calls `gc.collect()` (READ: jinja2 3.1.6's `tests/test_loader.py`), so a leaked loop no earlier pass freed is freed, and its warning lands, there. `test_debug` renders a template that dumps its whole context, an allocation-heavy test on which a collector pass can fire (INFERRED). The two that left are each the `<lambda>1` half of a parametrized pair, the pattern 182 saw in the error class (READ, 182's "What is inferred").

## Decisions

### 1. The four tests join `no-asyncio-loop`'s `collector_moves`

The class now names ten tests, sorted. A named test may not also be in the class's list (182's rules), so the two that left leave `no-asyncio-loop.txt`, 102 to 100 members. `test_groupby_tuple_index[<lambda>1]` stays a member of `no-asyncio-loop-error`, where it did not move; `test_simple_select_attr[<lambda>1]` is now named by both sibling classes, which 182's criterion 4 holds. Every other member of the class is still held exactly.

### 2. The gap is re-pinned to 100, `3576e7515999`

The judge's own `class_findings` and `report`, over the head's list and moves, give `100 finding(s), digest 3576e7515999` for both run 43982122112's members and the accepted list's (EXECUTED). The run's red digest, `106 finding(s), digest b6be1b9ee02b`, was reproduced first from the accepted list, the old moves and the moved line (EXECUTED), so the membership the new gap rests on is the run's.

### 3. jinja2-r's passes fall by the two that joined

A named test's pass is in neither its group's `passes` nor its `passed_digest` (182's criterion 7). `test_debug` and `test_weak_references` passed in every accepted run (INFERRED: neither is in any class list in git), so jinja2-r's count falls 548 to 546. The news file and the release ledger claim it under `passes`, with its `fewer` reason.

## Intent

The release pull request's run judges jinja2-r's asyncio-loop class on what the collector cannot move, and goes green on this set.

## Design

Data only: one list in `tests/upstream/jinja2.toml` grows by four names, one list file loses two lines, one gap's match moves. 182's code reads them unchanged.

## Scope

In: `no-asyncio-loop`'s moves, its list and its gap, and their claims. Out: every other class, the harness, and any test the collector has not been seen moving.

## Acceptance criteria

1. The head's judge files reproduce run 43982122112's red digest from the accepted list, and give the new gap over both that run's members and the accepted list. EXECUTED (above).
2. `tests/unit/test_upstream.py`, `tests/checks/test_rules.py`, `tests/lint` and `release/precheck.py` are green, or fail only as on `origin/dev`.
3. The news file claims the class check under `changed`, the suite row under `passes` with `fewer`, and each verdict-bearing file under `[claim.judge]`; the release ledger file carries the release-tier block.
4. The release pull request's next run passes `upstream-release-039`. Not judged here: the pull request's own run judges the normal tier.

## Landing notes

### What is inferred, and what the next run gives

The named tests are still the ones seen moving. A release-tier run may move another, as this one did; its moved line names it, and it is added the same way. The run on this pull request has no release tier, so #120's next run is the first to judge the new gap.
