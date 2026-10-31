# Review of 161 — Growth is listed on dev and reconciled at the release: the plugin's rows run as a local run (fix forward)

- **Date:** 2026-10-30
- **Reviewer:** an agent (Claude Opus 5.5), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** `origin/dev` `0070b04e`..`bcf62521` (one commit, pull request #61, branch `fix/161-the-plugin-rows-run-as-a-local-run`)
- **Run:** not read by this reviewer, by the orchestrator's brief (no `gh` calls); the pull request's `ci-status` is the orchestrator's to read before the merge. The red run it fixes forward is dev's post-merge run 41159838593.
- **Re-ran:** see criteria 1 to 5, all EXECUTED on macOS. Box: 25 minutes, a parallel-safe judge fix.

## Acceptance criteria against evidence

1. The failure reproduces on `dev` — met, EXECUTED: a scratch `git worktree add --detach` of `origin/dev` (`0070b04e`), `GITHUB_EVENT_NAME=push GITHUB_REF=refs/heads/dev uv run pytest -q -n 3 tests/unit/test_plugin.py tests/unit/test_landing_lane.py` → 7 failed, 89 passed: the six plugin rows (`test_fuel_over_the_tolerance_is_red_and_under_it_is_not`, `test_bytes_growth_is_red`, `test_a_metric_that_stops_being_recorded_is_red`, `test_passes_ratchet_end_to_end_with_its_own_flag`, `test_an_ignores_count_ratchets_end_to_end`, `test_a_check_that_moves_tiers_needs_its_own_flag`) and `test_landing_lane.py::test_the_plugin_self_tests_pass_in_a_worktree`, which runs them. The scratch worktree is removed.
2. The fix turns them green — met, EXECUTED: the same command on `bcf62521` → 96 passed, exit 0.
3. No other unit file reads the runner's push-to-dev variables to a wrong verdict — met, EXECUTED: `GITHUB_EVENT_NAME=push GITHUB_REF=refs/heads/dev uv run pytest -m "not slow" -n 3 -q tests/unit` on `bcf62521` → 3281 passed, 77 skipped, exit 0. READ: the env reads in `tests/harness/` are `plugin.after_a_merge` (through `gather.g7_form`) and `gather`'s own `main`, which `test_gather.py` drives with explicit environs; nothing else in the plugin reads `GITHUB_*`.
4. The rows that test a merge's form still set the variables after the fixture clears them — met, READ and EXECUTED: `inner`'s `monkeypatch.delenv` runs at fixture setup, before the row body; `test_an_unclaimed_growth_is_listed_after_a_merge_and_red_elsewhere` (`tests/unit/test_plugin.py:791`) and `test_a_lost_pass_after_a_merge_is_still_red` (`:821`) `setenv` in the body, so the inner session sees them. The "after a merge into dev" case asserts green and the `· unclaimed` line, which only the post-merge form prints; `-k after_a_merge` with no variables set → 5 passed, and the same rows pass under the push-to-dev variables in run 2.
5. The news-file comment is parsed and changes no claim — met, EXECUTED: `news.parse` on the file at `origin/dev` and at the head gives equal `News` objects and equal claims (`spec = "161"`, one `new`, `units = 35`, one `judge` entry); `tomllib` takes the `#` lines as comments. `tests/unit/test_plugin.py` is in the judge's hash but not verdict-bearing (`paths.VERDICT_BEARING`), so the judge-hash line records it and no `[claim.judge]` entry is asked.
6. Lint — met, EXECUTED: `ruff check` and `ruff format --check` on `tests/unit/test_plugin.py` clean. The comment names no specification, memo or `context/` path (the writing rule).

## Findings, most severe first

1. **The failure mode can still only be seen after a merge** (`tests/unit/test_landing_lane.py:663`) — Low. A pull request's `quick` runs under `GITHUB_EVENT_NAME=pull_request`, which the plugin reads as a local form, so a future inner-session fixture that forgets to clear the variables passes the pull request and turns `dev` red again, as this one did. Fix text: let `test_the_plugin_self_tests_pass_in_a_worktree` hand `GITHUB_EVENT_NAME=push` and `GITHUB_REF=refs/heads/dev` to its subprocess, so every run, local or pull request, judges the plugin's rows under the post-merge form. Answerable in writing; it does not hold this fix.
2. **The landing notes do not yet name the fix forward** (`context/specifications/161-growth-is-listed-on-dev-and-reconciled-at-the-release.md`, Landing notes) — Low, `context/` only. Fix text: one bullet, "**Fixed forward by pull request #61:** dev's post-merge run 41159838593 was red on six rows of `tests/unit/test_plugin.py` and the landing lane's self-test, which read the runner's `GITHUB_EVENT_NAME=push` and `GITHUB_REF=refs/heads/dev` and judged as a merge; the `inner` fixture now clears `GITHUB_EVENT_NAME`, `GITHUB_REF`, `GITHUB_REF_TYPE` and `GITHUB_BASE_REF`, and a row that tests a merge's form sets them.", with the pull request's run id, added by the orchestrator with the acceptance.
3. **A redundant clear** (`tests/unit/test_plugin.py:809`) — Low, no action needed: the parametrized row's own `delenv` loop now repeats the fixture's. Harmless; it may go in a later change.

## Constitution checks

- §4 constraints: no upstream patch, no pinned input, no artifact, no `src/` change; uv only (every command above was `uv run`). The change is to a test fixture, not to a check's verdict: the six rows assert what they asserted before, now under the environment they were written for. No allowance, golden output, `known_gaps.toml` or `context/progress/` is touched, so the judge is not weakened.
- §7 never-do list: nothing tripped. Code names no specification or `context/` path; the review file is uncommitted, for the orchestrator to commit last.
- Structure (4a): no module-level mutable, seam, platform branch, private-API use or long function added; not structural.
- 4b: no line under `.github/` or `release/` changed.
- Self-check: not read (no `gh` calls by brief); the orchestrator confirms the template's four boxes and the `Author:` line.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Finding 1 — answered in writing: a pull request's own run cannot see the push-to-dev form, and teaching the landing lane's self-test to pass it is a judge change of its own; it is reserved in 161's landing notes as a follow-up, not built here, so this fix stays one line of cause.
2. Finding 2 — fixed in this commit: 161's landing notes name the red run 41159838593, this pull request and the cause.
3. Finding 3 — answered in writing: the row's own `delenv` is now redundant but harmless, and it states the row's intent where the row reads; it stays.

## Verdict

Lands on `bcf62521`: the six rows and the landing lane's self-test fail on `dev` and pass on the head under the runner's push-to-dev variables, the whole fast unit tier is green under them, the merge-form rows still see their variables, and the news file's claims are unchanged; the three Lows hold nothing.

Rebased by the orchestrator onto `dev` `a1acec5c` (159's merge), so the plan that writes the `review` check's output runs: no conflict, and `git range-diff` shows every commit identical; the code this review read at `bcf62521` is `f7c9e358` after the rebase.
