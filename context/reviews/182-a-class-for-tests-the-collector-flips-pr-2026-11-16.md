# Review of 182 — A class for tests the collector flips

- **Date:** 2026-11-16
- **Reviewer:** an agent (Claude), a fresh sub-agent of https://claude.ai/code/session_01BD1pVHiZoxnwRv6JCqJKeC; not the author.
- **Reviewed:** `origin/dev` `d4761c4e` `...1f6fc4a5`, the one code commit, with the specification as it stands in that commit
- **Run:** none yet: the branch is not pushed, so no `ci-status` and no gather were read, and the self-check (the pull request's description) does not exist yet to be read
- **Re-ran:** `uv run pytest tests/lint tests/unit -q -p no:cacheprovider --deselect tests/unit/test_runner_grants.py::test_the_walk_judges_links -n 4` → 3679 passed, 104 skipped, exit 0. `uv run python release/precheck.py` → exit 1: ruff, mypy, the rules checks, their budget and lint ok; the only failure is `tests/unit/test_runner_grants.py::test_the_walk_judges_links`, the known root-container failure that fails the same way on `dev`; the plan prints one wait, the missing review file. A digest script over the judge's own `upstream.load`, `class_list`, `class_findings` and `scan.digest`. Four mutants (Probes).

Box: 45 minutes (a judge change). No `-spec` review is needed. The change touches nothing under `src/`, the guest's imports and exports, the artifact set or the build recipe, and its Kind line does not carry **structural**. I agree with that: nothing in the diff is structural.

## Acceptance criteria against evidence
1. The moved line names every gain and loss, and the first line and digest stay the same. Met for `scan.moved` and `scan.report`. EXECUTED. Its use in the check itself is finding 2.
2. A gap that fails differently keeps the moved line whole. Met. EXECUTED: the row passes, and removing the `why +=` line in `plugin.py` fails it (M2).
3. A named test is left out whether it is in, out or passing, and stable members stay exact. Met. EXECUTED: dropping the filter in `class_findings` fails two rows (M1).
4. Two siblings give the same findings in three states. Met. EXECUTED.
5. The rules: six refusals and the three-classes row. Met. EXECUTED: removing the list-overlap refusal fails its case (M3). Failing first before the code is INFERRED from the landing notes, since there is no self-check to read.
6. The digests. Met. EXECUTED, by my own script over the judge's functions. Every list version (`a88e9ec5`, `bedf8f30`, `d099f5d0`, `origin/dev`) now gives the three gaps' matches, 9 `1891e18dfe2d`, 102 `ea1eb2ac4985` and 2 `0c61ab6175e3`, and the landing notes' "before" column reproduces exactly. So does the reconstruction of run 43865484595: 19 `54478dcb2e88` against `dev`'s error list, then 9 `1891e18dfe2d`, and counted-clock 4 `02b4b38a0999`, then 2. As disclosed, `jinja2-r-no-asyncio-loop` is not reproduced for that run and may still fail differently. The specification promises nothing there, so it is no finding.
7. The claims and the green gates. Met. READ: every verdict-bearing file changed is under `[claim.judge]`, the three class checks are under `changed` (the new fact `collector_moves_in` is a moved fact name), and `units = 11` is the count of new rows. EXECUTED: lint and precheck pass as above.

Nothing loosens outside the three classes (READ, EXECUTED). With no `moves`, `class_findings` returns what it did before. `judge_group` is unchanged, the plugin only adds text to a reason that is already red, and the three-classes row pins the key. A named test that fails for another cause is still `unexpected`. One thing I read that the specification does not say: seven of the error class's nine names are stable members of `no-asyncio-loop.txt` (they fail in their call and sometimes also error at teardown). They never leave the failed class, so the error class ignoring their teardown error hides no pass. See finding 3.

## Findings, most severe first
1. **The owner's decision on `passes` is not built** (`tests/harness/upstream.py:854`, `:885`). Medium. The owner chose to have named tests leave their group's `passes` count, with their passes recorded as a fact. The commit still counts them, so any run where `test_split` fails turns `fonttools-r-rest` red. Evidence that closes this: the round's fix commit, with each of these held by a unit row:
   - (a) The count leaves out exactly the ids in the `collector_moves` of that group's own classes, in both `judge_group` and `combine`, through one shared helper. `combine` recounts from the streams, so a fix in only one of them is half a fix.
   - (b) A group whose classes name none keeps a count identical to today's, and a test named in another group's class still counts.
   - (c) A fact on the suite check records the named tests that passed, and preferably each named test's outcome, so a named test that is skipped or no longer runs is visible.
   - (d) The fix commit states whether `passed_digest` keeps or drops the named tests.
   - (e) One fall, computed from the accepted record and not guessed, claimed under `passes` and `fewer` in the news file and in `context/release-claims/182-….toml`, since the rows are release-tier. For `fonttools-r-rest` that is 2,635 → 2,634 if the accepted mark counted `test_split`. For `jinja2-r` it is 552 minus the named tests that passed then. INFERRED from the lists: four of them, `test_custom_async_iteratable_filter[asyncio-<lambda>0]` and `test_sum[<lambda>1]` (which pass in their call and error at teardown), plus `test_extend_late` and `test_line_syntax`.
   - (f) These texts are rewritten: the reasons that say the count does not change (`context/changes/182-….md:27`, `context/release-claims/182-….toml:10`), the changelog entry, and Decision 3.
2. **The class check's wiring has no evidence** (`tests/checks/test_v1_3_upstream_suites.py:132-139`). Medium. Mutant M4 dropped `klass.collector_moves` from the `class_findings` call, and the whole of `tests/unit` and `tests/lint` still passed (3679 passed). The fact, the moves argument and the moved line in the message are first executed by a release-shape run. Evidence that closes this: move the body into a harness function (members, list, class → findings, message, fact) with a unit row that M4 fails. Finding 1's fact comes under the same row.
3. **The comment misdescribes the error class** (`tests/upstream/jinja2.toml:45-48`). Low. It says each named test moves "to its sibling, or to a pass". Seven of the error class's nine are failed-class members whose teardown the warning sometimes reaches. Fix text: "...collector_moves names each test seen joining or leaving the class. Most of the error class's are members of no-asyncio-loop whose teardown the warning sometimes reaches; the others move between the classes or to a pass. The class check leaves them out and holds the rest exactly."

## Constitution checks
- §4: nothing under `src/`, no artifact, no recipe and no patch changes. The code-writing rule holds: the new comments and docstrings name no specification number and no `context/` path (lint, EXECUTED).
- §7: "never weaken the judge" is not tripped. The judge is narrowed to fifteen named ids in three classes. The change is its own, with reasons, and it is claimed. The trailer is `Co-Authored-By: Claude Opus 5.5`.

## The passes trade-off (decided by the owner; my view)
Keeping the count made the pass ratchet the backstop: a named test that really regressed, with a reason matching its class's pattern, still showed as a fall to claim. Leaving it out keeps the rows green across flips but drops that backstop. The fact in 1(c) then carries the weight, so it should name each named test's outcome. The pinned three-classes row bounds the cost.

## Disposition (filled in by the author, then confirmed by the reviewer)
1. —
2. —
3. —

## Verdict
Does not land yet: finding 1 (the owner's `passes` decision, to be built in the fix commit under conditions (a) to (f)) and finding 2 (no unit row holds the class check's wiring) stand. Finding 3 is independent of the decision, and finding 2's new row should also cover finding 1's fact.
