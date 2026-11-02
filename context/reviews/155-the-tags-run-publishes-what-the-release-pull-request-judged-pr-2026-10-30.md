# Review of 155 — The tag's run publishes what the release pull request judged

- **Date:** 2026-10-30
- **Reviewer:** an agent (Claude Opus 5.5), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** `a1acec5c..e96cb44f` on `spec/155-the-tags-run-publishes-what-the-release-pull-request-judged` (two commits), with the specification and its pre-build review
- **Run:** 41164381357 on `e96cb44f`, as the orchestrator read it (the reviewer made no `gh` call): plan full (the workflow changed), 57 (system, shard) pairs; every judge leg green (13 Windows, 15 macOS, Linux); verify on three systems; the gather green; 52 shard ratchets lost 0 and grew 0, 50 of them listing under `GROWTH` the absent `test_the_judge_matrices_are_the_shard_plan_on_every_release[a pushed tag]` as `155: retired`, the news file's claim; `ci-status` red on the missing review alone
- **Re-ran:** `uv run pytest -m "not slow" -n 2 -q tests/unit tests/lint tests/checks/test_rules.py` → 3532 passed, 79 skipped, exit 0; `tests/unit/test_gather.py -k prove` → 12 passed, exit 0; `tests/checks/test_rules.py -k "tag_publishes or ci_status_fails or judge_matrices"` → 11 passed, exit 0; `ruff check` and `ruff format --check` on `src tests release` → clean; `scan.tag_run_errors` on `dev`'s `release.yml` (`a1acec5c`) → 8 errors, ending "no judged job", so the new rules row fails before the change; `gather.prove_set` on a scratch clone at `v0.1.2` (`8e21c2c8`) → `None` for the tree and for line 115's bytes, the set's mismatch for a zero `set_sums`, and at its parent `193c9996` → "not a release pull request's" (tier normal)
- **Box:** 45 minutes (build-class); done inside it.

## Acceptance criteria against evidence

1. Tag outputs. Met. On `TAG`: `judge` false, `build` false, `rebuild` and `publish` true, `tier` empty, every judge list `[]`, `verify` the three runners. Nine other events give `publish` false, a dispatch on a tag among them (`test_a_tag_publishes_what_the_release_pull_request_judged`, `test_only_a_pushed_tag_publishes`). EXECUTED.
2. The workflow's shape. Met. `judged` needs exactly `[plan, build, same-bytes]` and runs on `publish == 'true'`. `attest`, `publish` and `ci-status` need it. `inputs` and `build` gate on `judge || rebuild`. `ci-status` exits red when `PUBLISH` is `true` and `publish` did not succeed. `scan.tag_run_errors`, its 14 mutants, the two new `ci-status` cases and `jobs_that_run` on four events hold all of it. READ and EXECUTED.
3. `--prove-set` in the six cases. Met with eleven: holds, tree alone, other set, other `python.wasm`, a merge's line, a local line, a push's line, a commit not the parent, a second file, partial, dirty. Two more rows cover the command line. EXECUTED. The real `v0.1.2` tag holds. EXECUTED.
4. No judge leg or gather on the next tag. Deferred to the next release's tag run, as the criterion says. `jobs_that_run` models the tag's run as exactly the twelve jobs. EXECUTED as a model, not as a run.
5. The pages. Met. §5.5 and the Status line, `release-process.md` (the steps, the new step 5, the release tier, "Dry runs"), the progress README's four places and the workflow's header comment all say Decision 3. READ.
6. Fast tier, lint, `ci-status`, news file. The local run is above. The news file is present. `ci-status` waits on the run.

## Release safety (READ unless marked)

- **A tag on a commit the release pull request did not judge cannot publish.** The newest line must be `source` ci, `tier` release and `event` pull_request (or absent). Its `commit`, and `accepted.json`'s, must be `HEAD^`. `git diff --name-only --no-renames HEAD^ HEAD` must be exactly `accepted.json` plus one `history(-NNNNN)?.jsonl`. A failed diff yields an empty list, which is refused. A merge commit's first-parent diff holds the whole merge, so it is refused too. An acceptance line cannot name its own commit, so the newest line was written in `HEAD`. The tree check runs first in `build`, before the compile and at `fetch-depth: 0`. `judged` runs it again at `fetch-depth: 2`.
- **A rebuilt set that differs cannot publish.** `same-bytes` requires both rebuilds to equal the build's set. `judged` then requires the build's own set to be the accepted one. It hashes `<top>/SHA256SUMS` and `python.wasm` from the tarball inside `release-assets` itself, after `verify-artifact`. It never takes the job outputs or the release assets' `SHA256SUMS`, and the scan refuses `release-assets/` as the hashed path. `set_sums` and the tarball are both taken after `licences.py append`, so they compare like for like. The `v0.1.2` probe agrees. EXECUTED.
- **Nothing but a pushed tag reaches `publish`.** `attest`, `publish` and `pypi` keep `if:` `push` with `ref_type` `tag`. They carry no status function, so a skipped or failed `judged` skips them. `judged` runs on `publish`, which `decide()` sets on `event.tag` alone. The weekly run and a dispatch, on a tag or on `main`, have `publish` false and a non-push event. EXECUTED in the unit and rules rows.
- **No guard of the tag's three jobs is weakened.** `attest`, `publish` and `pypi` still read through `verify-artifact` with `assets-id` and `sums-sha256`. `attest` still verifies each asset strictly. `judged` has `contents: read` and no token. The old G7 tag clause compared the judge's hash with the accepted one. The diff rule is stronger: the whole tree, the judge with it, is the judged tree.
- **Files under `.github/` and `release/` (4b).** `release.yml`: a tag runs no judge leg, no build shard and no gather. It adds `judged` (read-only). `ci-status` is red on a skipped publish. The tokens are unchanged: `id-token` in `attest` and `pypi`, `contents: write` in `publish`. `release/ci_plan.py`: `Decision.publish` and its output, `judge` false when `publish` is true, and `verify` on three runners whenever the run rebuilds. The pull request's own run (a workflow change, so `full`) is unaffected by the tag branch.

## Findings, most severe first

1. **Low: the tag no longer checks `set-source` itself** (`release.yml`, `judged`). G7 asked a tag's set to be built in its own run, and the gather no longer runs on a tag. The guard still holds two ways. The `inputs` job never trusts a cache on a tag ref. `same-bytes` requires the set to equal two rebuilds from the pins. Failure: none today. If a later change let `inputs` reuse a set on a tag, only `same-bytes` would stand between a cached set and the signature. Fix text (optional, or answered in writing): in `judged`'s last step, add `test "$SET_SOURCE" = built || { echo "the set was not built in this run"; exit 1; }` with `SET_SOURCE: ${{ needs.build.outputs.set-source }}` in its `env:`, and one mutant in `BAD_TAG_RUN`.
2. **Low: the proof trusts `main`'s history** (Decision 2, as specified). A hand-written line with `source` ci and `tier` release, on an unjudged parent, would pass. Only the owner and `accept-release.yml` write `main`, and G7 trusted the same file before. Failure: none in the process as run. No fix is asked. This note is for the next security review's threat model.
3. **Low: the self-check was not read by the reviewer.** This review made no `gh` call, by instruction. The orchestrator read the description and ticks its Windows box at the commit, which the run's Windows legs bear out. Fix text: tick the box.

## Constitution checks

- §4 constraints: none touched. No `src/` change, no pin, no artifact in git. §4.1 and the pins hold: the tag still compiles from the pins, runs the zero-patch step and has the three hosts vote.
- §5.5: amended by the owner's decision of 2026-10-30 (`decisions.md`). The new text is what the workflow does. The release pull request stays the whole dry run.
- §5.6: build-class. Reviewed before it was built. Lows 9 and 10 of that review are taken: the tree check is in `build`, and 159's criterion 4 already says "until specification 155 changes that row".
- "Never weaken the judge": the retired id `test_the_judge_matrices_are_the_shard_plan_on_every_release[a pushed tag]` is in `accepted.json`. It is a goal-marked (`rules`) check under `tests/checks/`, and its case is removed, not loosened. Its claim is false by the amended §5.5 and is replaced by the opposite claim in `test_a_tag_publishes_what_the_release_pull_request_judged`. The other three cases are unchanged. The `retired` entry qualifies (`context/changes/README.md`). The `new` ids and the `[a tag*` prefix match the added rows. `units = 37` agrees with the rows added, to within the count of mutants that changed in place.
- Structure (4a): no `src/` change. `tag_run_errors` is a new rule function in `scan.py`. No row of the rubric moves.
- §7 never-do list: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Low 1 —
2. Low 2 —
3. Low 3 —

## Verdict

Lands on e96cb44f: the code holds, the run is green but for the review refusal this file answers, the one `GROWTH` row is the claimed retirement, and only Lows stand, each answered in its text.
