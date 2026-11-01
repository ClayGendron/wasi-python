# 181: The release runs three flips

- **Status:** built 2026-11-01 on `spec/181-the-release-runs-three-flips`, from `dev` at `84c39c62`, not landed. The owner approved the three judge changes on 2026-11-01 (`../decisions.md`, "The 0.1.3 release pull request's three flips").
- **Date:** 2026-11-01
- **Owner:** Clay Gendron
- **Kind:** a judge change (`tests/checks/test_v1_4_results.py`, `tests/known_gaps.toml`, `tests/upstream/expected/jinja2-r/{no-asyncio-loop,no-asyncio-loop-error}.txt`, `tests/upstream/expected/fonttools-r-rest/counted-clock.txt`, a release ledger file). Not structural: nothing under `src/` changes. No pre-build review: it touches neither the guest's imports or exports, the artifact set nor the build recipe (constitution §5.6).
- **Depends on:** landed: 163 (the results rows), 067 (the classes and their lists), 172 (whose Decision 5 left jinja2-r's flip open). Blocks: the 0.1.3 release pull request, #96.
- **Research it stands on:** the release pull request's run 41346031022 on `84c39c62`, its job logs and the failed records of shards `upstream-release-039` and `upstream-release-041`; the diagnosis of that run made on 2026-11-01 by the orchestrating session; `../research/2026-10-31-the-start-cost-of-the-zips-directory.md` (the plain binary's hash seed).

Labels: EXECUTED, run and seen; READ, read from a file or a log, cited; INFERRED, reasoned.

## The problem

Run 41346031022, the 0.1.3 release pull request's, was red on three checks that moved with no change to the code or the set (READ: the set is `503293500a64…`, the one `dev`'s last acceptance judged).

1. `tests/checks/test_v1_4_results.py::test_both_binaries_return_the_same_records[False]` grew on macOS, fuel 266,861,498 to 267,018,014. The row runs the plain reactor through the public API, which answers `random_get` from the host, so CPython's hash secret is random on each start and the count moves by up to about 0.3 M from run to run. The row has drifted at every acceptance since 173; its snapshot twin, whose seed is fixed, has not. A ratchet on noise goes red about one run in two, and a claim cannot clear it on the release pull request, since a shard reads claims only from `context/changes/`.
2. jinja2-r's `no-asyncio-loop-error` (17 findings, `a9e51a8343b8`, where 13, `af97922d3b81`, were expected) and `no-asyncio-loop` (110, `500e70e2e2ed`, where 106, `c7177c5b2367`) moved. An event loop an earlier async test leaves behind is collected during whichever test is running when the collector fires, and that depends on the set's allocations. This set gives the state the lists held from 067 to 166's second pull request, which 0.1.0 to 0.1.2 released with. The suite still passes 552.
3. fonttools-r-rest's `counted-clock` (3 findings, `a5888c38d28b`, where `5f05fa61a255` was expected) moved: `Tests/misc/loggingTools_test.py::TimerTest::test_split` now passes, and the group's passes rose from 2,634 to 2,635. The test asserts its second lap is longer than its first. Under the judge's counted clock a lap counts clock reads, not time, and a collector pass reads the clock at its start and its end; on this set one falls in the second lap.

## Decisions

The owner chose each with the AskUserQuestion tool on 2026-11-01.

### 1. The plain reactor's fuel in the records row is a fact

"Record it as a fact." The `[False]` row reports its fuel with `fact`, never ratcheted, as the rows that import numpy already do. Its assertion that both binaries return the same records stays. The `[True]` row keeps its exact fuel as a metric.

### 2. jinja2-r's two lists go back to the state this set gives

"Restore + follow-up spec." The two list files and their gaps return byte for byte to their content before 166's second pull request (`bedf8f30`): the error class gains `test_custom_async_iteratable_filter[asyncio-<lambda>0]` and `test_sum[<lambda>1]` and loses `test_custom_async_filter[asyncio]` and `test_sum[<lambda>0]`; the failed class gains those two, `TestExtensions::test_streamfilter_extension` and `TestLexer::test_balancing`, and loses `TestExtensions::test_extend_late` and `TestParser::test_line_syntax`. A later set may flip it back. 182 is reserved to give jinja2-r's flip a stable class, as 172 did for tqdm-smoke, but one that lets a test move between passing and failing.

### 3. fonttools-r-rest takes the new pass

"Take the new pass." `TimerTest::test_split` leaves `counted-clock`, and its gap is re-pinned to the two `ttx` cases. The group's passes go from 2,634 to 2,635. If a later set moves the collector's pass out of the second lap, the pass count falls and that run is red until a claim gives its reason; 182 may take this test too.

## Intent

The 0.1.3 release pull request's next run is green on these three checks, and none of them can go red again on noise alone: the plain reactor's fuel is reported, and the two flipped families hold this set's membership until 182 gives jinja2-r a stable class.

## Design

- `tests/checks/test_v1_4_results.py`: the records row reports the plain reactor's fuel with `fact` and the snapshot's with `metric`; the module docstring says why.
- `tests/upstream/expected/jinja2-r/no-asyncio-loop{,-error}.txt`: their content at `bedf8f30^`; `tests/upstream/expected/fonttools-r-rest/counted-clock.txt`: less `test_split`.
- `tests/known_gaps.toml`: the three gaps' matches; their reasons do not change.
- `context/changes/181-the-release-runs-three-flips.md` and `context/release-claims/181-the-release-runs-three-flips.toml`: the claims.

## Scope

**In:** the three checks above. **Out:** a sweep of the other plain-reactor rows that ratchet fuel (candidates in `test_v1_4_checkpoint.py`, `test_v1_4_sessions.py`, `test_v1_4_embedding.py`, `test_v1_3_default_profile.py` and `test_v1_2_hostile_guest.py`; none moved in this run); jinja2-r's stable class (182); the fourth red job, an upload that timed out.

## Acceptance criteria

1. `test_both_binaries_return_the_same_records[False]` records `fuel` under its facts and no fuel metric; `[True]` records its fuel as a metric. READ in the pull request's run's record.
2. The class lists, with no test run, give exactly the findings run 41346031022 saw: the judge's own `class_findings` and `digest` over the run's membership and the lists at `84c39c62` give `17, a9e51a8343b8`, `110, 500e70e2e2ed` and `3, a5888c38d28b`; over the restored lists, `13, ba56b641f579`, `104, 959d6ba605ec` and `2, 0c61ab6175e3`, the three gaps' new matches. EXECUTED.
3. Where the pull request's run runs jinja2-r and fonttools-r-rest on the cached set, their class checks match their gaps, jinja2-r passes 552 and fonttools-r-rest 2,635.
4. The news file claims each verdict-bearing file under `[claim.judge]`, the moved checks under `changed`, the fonttools-r-rest pass count under `passes` and the `[False]` row's dropped metric under `grows`; the release ledger file `../release-claims/181-the-release-runs-three-flips.toml` carries the two release-tier rows' block.
5. `tests/lint`, `tests/checks/test_rules.py` and the fast tier are green, and so is the pull request's `ci-status`.

## Landing notes

Built 2026-11-01, before its pull request and review.

- **The run.** 41346031022, on `84c39c62` (the 0.1.3 release pull request, #96). Jobs 124972146466 (judge, macos-15, own-guest-d), 124972147192 (upstream-release-039) and 124972147292 (upstream-release-041). The fourth red job, 124972147316 (upstream-release-052), failed to upload its record (`ETIMEDOUT`) after a green shard, and needs no change.
- **The digests** (EXECUTED, criterion 2). The run's records carry each class's count and digest, not its members. The judge's `class_findings` and `digest`, run over the candidate membership (the lists before `bedf8f30` for jinja2-r; the list less `test_split` for fonttools-r-rest) against the lists at `84c39c62`, reproduce all three of the run's digests exactly; a digest is a hash of the exact set of findings, so that membership is the run's. The restored lists then give the three new matches.
- **No new check.** Each change re-records an existing check, so none is seen failing first; the `[False]` row's fuel moves from a metric to a fact.
- **Where the claims are read.** A shard's ratchet reads claims from the news files at its commit (`tests/harness/plugin.py`, `claimed_by_news`). After this merges, `context/changes/181-the-release-runs-three-flips.md` stays in the folder until the next `bump`, since 0.1.3's `bump` and `date` have run, so the release pull request's shards and its acceptance read it there; the acceptance also reads the ledger file. `dev`'s acceptance after the merge drops the `[False]` row's macOS fuel from `accepted.json` with this claim's growth reason, so the release pull request's macOS shard has nothing of it to compare.
- **The follow-up.** 182 (reserved in `../roadmap.md`): a stable class for jinja2-r's collector flip.

The pull request, its run and its review are to be written at the landing.
