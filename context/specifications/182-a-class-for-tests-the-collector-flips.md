# 182: A class for tests the collector flips

- **Status:** built 2026-11-16 on `spec/182-a-class-for-tests-the-collector-flips`, from `dev` at `d4761c4e`, not landed. The owner chose this follow-up on 2026-11-01 (`../decisions.md`, "The 0.1.3 release pull request's three flips": "Restore + follow-up spec"; `../roadmap.md`, "Reserved: 182").
- **Date:** 2026-11-16
- **Owner:** Clay Gendron
- **Kind:** a judge change (`tests/harness/upstream.py`, `tests/harness/scan.py`, `tests/harness/plugin.py`, `tests/checks/test_v1_3_upstream_suites.py`, `tests/upstream/jinja2.toml`, `tests/upstream/fonttools.toml`, two of jinja2-r's list files, `tests/known_gaps.toml`, a release ledger file). Not structural: it changes no file under `src/`. No pre-build review: it touches neither the guest's imports or exports, the artifact set nor the build recipe (constitution §5.6).
- **Depends on:** landed: 067 (the classes, their list files and the class checks), 172 (the node-limited class, whose Decision 5 left this open), 181 (the restored lists this one starts from), 183 (a rise in a pass count is listed, not red).
- **Research it stands on:** the release-shape run 43865484595 on pull request #110's head `fb4a1bc6` (READ, its failure lines as the orchestrating session quoted them; its records could not be downloaded here); run 41346031022 and 181's landing notes (READ); every version of the three list files in git (READ); the digest searches below (EXECUTED).

Labels: EXECUTED means run and seen; READ means read from a file or a log, cited; INFERRED means reasoned.

## The problem

Three release-tier classes change their members with no change to the code that runs them.

- **jinja2-r's `no-asyncio-loop` and `no-asyncio-loop-error`.** An async test leaves an event loop behind. The garbage collector frees it during whichever test is running when it fires, and pytest reports the loop's unraisable warning on that test: as a failure in its call, or as an error at its teardown. Which test that is depends only on the set's allocations. A test can move between the two classes, or between failing and passing (READ: 181, Decision 2; the list files' history below).
- **fonttools-r-rest's `counted-clock`.** `TimerTest::test_split` asserts that its second lap is longer than its first. Under the judge's counted clock a lap counts clock reads, and a collector pass reads the clock at its start and end. When a pass falls in the second lap the test passes; otherwise it fails (READ: 181, Decision 3).

A class check holds its members exactly. A gap matches the check's message by count and digest, `N finding(s), digest D`. So any move turns the gap "failing differently", red. It happened at the 0.1.3 release pull request (run 41346031022, 181), and again in run 43865484595, a release-shape dispatch on #110, a Rust pipeline change that touches neither jinja2 nor fontTools (READ):

| class | expected | got |
|---|---|---|
| `jinja2-r-no-asyncio-loop-error` | 13, `ba56b641f579` | 19, `54478dcb2e88` |
| `jinja2-r-no-asyncio-loop` | 104, `959d6ba605ec` | 112, `7623e94ffbea` |
| `fonttools-r-rest-counted-clock` | 2, `0c61ab6175e3` | 4, `02b4b38a0999` |

Two things are wrong.

1. **The log does not say what moved.** The failure line shows the first five findings, and the class findings list the members first, sorted, then `+id` for each test that joined and `-id` for each that left. So the five shown are the first members, not the moves. The "fails differently" reason keeps only the first 240 characters of that line. The full findings live in the run's record, an artifact; from this environment the proxy refuses it (READ: the orchestrating session's brief). In 181 the members had to be reconstructed by hand from digests.
2. **No class can hold a test the collector moves between failing and passing.** 172's node-limited class holds tests that fail in every state, and a pass of one is a finding. Its Decision 5 left jinja2-r out for that reason.

What the counts say (INFERRED from `class_findings`). A class whose members equal its list has one finding per member. A run that adds `p` tests and removes `m` has `(n + p - m) + p + m = n + 2p` findings. So the error class gained 3 tests, the failed class 4, and `counted-clock` 1; the removals are not in the count.

## Decisions

### 1. A class failure names every member it gained and lost

The class check's message keeps its first line, `class G-K: N finding(s), digest D: <first five>; +k more`, unchanged: the gaps match it, and a gap records it as its reason. It gains a second line, `moved: +a; +b; -c`, with every `+id` and `-id` finding, none cut. When the class gained and lost nothing, there is no second line.

A gap that fails differently records the message's first line, cut to 240 characters, as today. Its reason now ends with ` · moved: …`, the second line whole. So the job log's failure section, and the record's reason, name each test that joined or left. The digest form the gaps match does not change.

### 2. A class may name the tests the collector moves

An ordinary class (one with a list file) may carry `collector_moves = [...]`: node ids that the collector's timing moves in and out of it. Each such test may be the class's member, a member of a sibling class, or pass, and the class check gives the same findings in each case:

- **The class check leaves them out.** `class_findings` drops a named test from the class's members before comparing them with the list, so it is never a finding, a `+id` or a `-id`. Every other member stays exact: a stable member that leaves is `-id`, and a new one is `+id`.
- **The judge's sorting does not change.** `judge_group` still gives each failure to the first class whose outcome and pattern fit. A named test that fails for another cause lands in another class, where it is exact, or is `unexpected …`, as today. A sibling is simply another class of the group that names the same test; jinja2-r's two classes share a pattern and differ by outcome.
- **The record says which ones were in.** The check records the fact `collector_moves_in`, the named tests that were members in this run. It is reported, never ratcheted.

The rules refuse: `collector_moves` on a node-limited class (whose list is its nodes); an empty, unsorted or repeated list; a named test also in the class's list file; a named test that a node-limited class of the group names; `collector_moves` in CPython's family, whose class lists are module and test ids from a different judge. A unit row holds that exactly the three classes below carry the key, so a fourth is a judge change a reviewer sees.

### 3. The pass ratchets do not change

A lost pass, a check that passed and now fails, stays red with no reason that clears it. This change touches no check's status: the class checks are gaps before and after.

The group's `passes` count still counts every passed test, a named one included. When a named test moves from passing into a class, the suite row's `passes` falls by one. That fall is a `FEWER` row, exactly as now: red on a pull request unless the pull request's news file names the suite row under `passes` with a `fewer` reason, and at the release unless a news file or the release ledger gives one (`../changes/README.md`; `../progress/README.md`, "The release tier"). The class gives no claim of its own, and nothing here lowers or skips the count. A rise is listed, not red (183).

For jinja2-r the count has not moved: both states 181 saw pass 552 (READ: 181, Decision 2), since each leaked loop warns on exactly one test and the victims trade places (INFERRED). For `test_split` it is not neutral: the count's accepted high-water mark is 2,635 since 181, so each run where `test_split` fails is `fonttools-r-rest` 2,635 to 2,634, a fall to claim. Whether a named test should leave the count is the owner's to decide (Landing notes, "For the owner"); this specification does not choose it.

### 4. The three classes and what is named

Each list is seeded from the evidence that can be read: every version of the three list files in git (`git log -p --follow`; three versions, `a88e9ec5`, `bedf8f30` and `d099f5d0`), 181's notes, and run 43865484595's failure lines.

**`jinja2-r-no-asyncio-loop-error`** names nine tests, all in `tests/test_async_filters.py`:

- from the history (READ): `test_custom_async_filter[asyncio]`, `test_custom_async_iteratable_filter[asyncio-<lambda>0]`, `test_sum[<lambda>0]`, `test_sum[<lambda>1]`;
- from run 43865484595 (EXECUTED, below): `test_join_attribute[<lambda>1]`, `test_simple_reject[<lambda>0]`, `test_simple_select_attr[<lambda>0]`, `test_simple_select_attr[<lambda>1]`, `test_sum_attributes[<lambda>0]`.

Its list keeps the other nine members; four leave it. The gap becomes `9 finding(s), digest 1891e18dfe2d`.

**`jinja2-r-no-asyncio-loop`** names six, from the history (READ): `tests/test_async_filters.py::test_custom_async_iteratable_filter[asyncio-<lambda>0]`, `::test_sum[<lambda>1]`, `tests/test_ext.py::TestExtensions::test_extend_late`, `::test_streamfilter_extension`, `tests/test_lexnparse.py::TestLexer::test_balancing`, `::TestParser::test_line_syntax`. Its list keeps 102; `test_streamfilter_extension` and `test_balancing` leave it. The gap becomes `102 finding(s), digest ea1eb2ac4985`.

**`fonttools-r-rest-counted-clock`** names `Tests/misc/loggingTools_test.py::TimerTest::test_split`. Its list does not change, nor does its gap, `2 finding(s), digest 0c61ab6175e3`.

**What run 43865484595's members were** (EXECUTED, 2026-11-16, a search over the judge's own `class_findings` and `digest`):

- `counted-clock`: `test_split` and the two `ttx` cases, with `+test_split`, give 4, `02b4b38a0999`, the run's digest. Nothing left.
- `no-asyncio-loop-error`: among 1,093 sets of up to four removals from the 13 members and every three additions from the 95 tests the history names outside the list, exactly one gives 19, `54478dcb2e88`: `test_join_attribute[<lambda>1]`, `test_simple_select_attr[<lambda>0]` and `test_sum[<lambda>1]` left, `test_simple_reject[<lambda>0]`, `test_simple_select_attr[<lambda>1]` and `test_sum_attributes[<lambda>0]` joined. A 48-bit digest matching one of about 1.5 × 10⁸ guesses by chance is about one in two million.
- `no-asyncio-loop`: the history names only four tests outside the list, so they are the four additions if any are; with up to four removals from the 104 (4,785,691 sets) none gives `7623e94ffbea`. So at least one of the four tests that joined is not named anywhere in the history, or more than four left (INFERRED). Those names are not known.

**What is inferred, and what the next run gives.** The named tests are the ones seen moving, not every test the collector can move. The error class's new five show a pattern: a parametrized pair's `<lambda>0` and `<lambda>1` cases trade places. That pattern is not used to name tests no run has shown moving (INFERRED: it may be the order the collector reaches the leaked loops in). The failed class's four new members in run 43865484595 are unknown. The next release-shape run or the release pull request will name them, and every other move, in its log (Decision 1). A test it names that the collector moved is added to the list then, as its own judge change with its reason. Until then `jinja2-r-no-asyncio-loop` may still fail differently on a set like #110's.

## Intent

A change to the set that only moves the collector's timing no longer turns these three class checks red, for the moves seen so far. Every other member of the three classes is still held exactly. Every other class is unchanged. Any class that does fail says in the log which tests joined and which left, so the next re-pin needs no record and no reconstruction.

## Design

- `tests/harness/scan.py`: `moved(findings)`, the second line of Decision 1; `MOVED`, its prefix; `moved_line(message)`, which finds it in a failure message (pytest indents an assertion message's later lines).
- `tests/harness/plugin.py`: a gap that fails differently appends the message's moved line, whole, to its reason.
- `tests/harness/upstream.py`: `Klass.collector_moves`; `klass_of` reads it; `class_findings` takes `moves` and leaves them out; `class_shape_errors` and `rule_errors` hold Decision 2's rules.
- `tests/checks/test_v1_3_upstream_suites.py`: `test_upstream_class` passes the class's moves to `class_findings`, adds the moved line to its message, and records `collector_moves_in` for a class that names any.
- `tests/upstream/jinja2.toml`, `tests/upstream/fonttools.toml`, `tests/upstream/expected/jinja2-r/{no-asyncio-loop,no-asyncio-loop-error}.txt`, `tests/known_gaps.toml`: Decision 4.
- `tests/unit/test_upstream.py`, `tests/unit/test_plugin.py`: the rows of the acceptance criteria.
- `context/changes/182-a-class-for-tests-the-collector-flips.md` and `context/release-claims/182-a-class-for-tests-the-collector-flips.toml`: the claims.

## Scope

**In:** the moved line (every class check and every gap that fails differently); the `collector_moves` key, its rules, and the three classes. **Out:** the `passes` count of a named test (Decision 3, the owner's); a driver that collects at each test's teardown so a leaked loop warns on the test that leaked it (the roadmap's other route, not measured); 172's node-limited class and tqdm-smoke's `collector-timing`, unchanged; CPython's judge, which refuses the key.

## Acceptance criteria

1. A class check's message names every member it gained and lost, beyond the five its first line shows, and its first line and digest do not change. Unit row `test_a_class_failure_names_every_member_it_gained_and_lost`, seen failing first.
2. A gap that fails differently keeps the moved line whole in its reason, past the 240 characters of the first line. Unit row `test_a_gap_that_fails_differently_names_what_moved`, seen failing first.
3. A named test is left out of its class's findings whether it is in, out or passing; a stable member that leaves or joins is still a finding. Unit row `test_a_class_leaves_the_collectors_tests_out_of_its_findings`, seen failing first.
4. Two sibling classes that name a test give the same findings whether it fails, errors or passes, and the group has no finding. Unit row `test_a_test_the_collector_moves_may_fail_error_or_pass`, seen failing first.
5. The rules of Decision 2. Six cases of `test_a_classs_collector_moves_are_held_by_the_rules` and `test_only_three_classes_name_collector_moves`, each seen failing first.
6. The three classes, over the members of every state seen (the three list versions, and run 43865484595's reproduced error and counted-clock members), give one digest each: 9, `1891e18dfe2d`; 102, `ea1eb2ac4985`; 2, `0c61ab6175e3`. EXECUTED (Landing notes).
7. The news file claims each verdict-bearing file under `[claim.judge]` and the three class checks under `changed`; the release ledger file carries the same block. `tests/lint`, `tests/checks/test_rules.py`, the fast tier and `release/precheck.py` are green.

## Landing notes

Built 2026-11-16, before its pull request and review.

- **Seen failing first** (EXECUTED, 2026-11-16). The eleven unit rows were written before the code. With `Klass` given its `collector_moves` field and no behaviour, all eleven failed: `scan.moved` missing; `class_findings` refusing a third argument; the rules naming none of the six refusals; no class carrying the key; and the plugin's reason ending at its 240-character first line. With the code, all eleven pass.
- **Every state seen, judged** (EXECUTED, criterion 6). The judge's own configs, lists, `class_findings` and the gaps' matches, run over the members of each state: the three list versions in git, and run 43865484595's members for the two classes whose digests were reproduced.

  | class | state (its members) | before, against `dev`'s lists | after, and matches its gap |
  |---|---|---|---|
  | `no-asyncio-loop-error` | `a88e9ec5`, `d099f5d0` | 13, `ba56b641f579` | 9, `1891e18dfe2d` |
  | | `bedf8f30` | 17, `927e255e0e70` | 9, `1891e18dfe2d` |
  | | run 43865484595 | 19, `54478dcb2e88` | 9, `1891e18dfe2d` |
  | `no-asyncio-loop` | `a88e9ec5`, `d099f5d0` | 104, `959d6ba605ec` | 102, `ea1eb2ac4985` |
  | | `bedf8f30` | 112, `a5bf2d0d98df` | 102, `ea1eb2ac4985` |
  | `counted-clock` | `a88e9ec5`, `bedf8f30`, run 43865484595 | 4, `02b4b38a0999` | 2, `0c61ab6175e3` |
  | | `d099f5d0` | 2, `0c61ab6175e3` | 2, `0c61ab6175e3` |

  The "before" column of each `d099f5d0` row, and of run 43865484595, is the gap's match or the run's digest, so the script reproduces the judge.
- **Not run here.** No artifact set or upstream source is in this container, so no class check ran in the guest. The next release-shape run or the release pull request is the first to run them, and `no-asyncio-loop` may still fail differently there (Decision 4); its moved line then names each test.
- **No pass count moves with this change.** It changes no outcome and no group's `passes`. A release run in which `test_split` fails shows `fonttools-r-rest` 2,635 to 2,634, red until claimed (Decision 3); whether run 43865484595 showed that fall is not known, since its gather could not be read here.
- **Where the claims are read.** The news file and `../release-claims/182-a-class-for-tests-the-collector-flips.toml` carry the three class checks under `changed`, and the judge files with their reasons. The rows are release-tier, so the run after the merge does not judge them; the release pull request reads the ledger.

**For the owner.** One question this specification does not decide (Decision 3): should a test a class names in `collector_moves` still count in its group's `passes`? Kept (built): every flip of `test_split` from pass to fail is a fall to claim, and so is any jinja2-r flip that does not trade a pass for a pass; nothing about the ratchet changes. Left out: a named test's pass is recorded as a fact and the count leaves it out, so the flip moves nothing; the accepted counts fall once, by the named tests that pass, and that fall is claimed once. The second changes what the `passes` ratchet counts, so it is the owner's.

The pull request, its run and its review are to be written at the landing.
