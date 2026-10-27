# 138: pull requests into `dev`, and the judge runs where it is needed

## Changelog

### Changed

- **Every merge into `dev` is accepted by CI** (spec 138, step 3): the run after a merge judges the normal tier on three systems, and two jobs follow a green gather. `accept-record` runs `uv run pytest --accept-from <record.json> --claims context/changes/` with no secret, and `accept-push`, in the `accept` environment, commits the two progress files alone and pushes them onto `dev` with a deploy key, only while `dev` is still the commit judged. A change's CHANGELOG line, package rows and claims are its news file under `context/changes/`, which `release/version.py bump` assembles at a release; `ci-status` refuses a pull request into `dev` that is not documentation only and has no news file, or no review file whose verdict begins "Lands", committed after its last code, by a reviewer other than its author. A documentation-only push onto a green head re-uses that head's run, and the weekly run opens an issue when it is red.
- **A release is a pull request from `dev` to `main`** (spec 138, step 4): its run is the whole workflow on the commit `main` will receive (a set built on macOS and never reused, both rebuilds and same-bytes, every shard of both tiers on three systems, `verify` on three and `quick`), and its gather has every goal: no `PLAN`, G7 holding the newest acceptance to the run's own set, clean and whole, and each release-tier row that moved since the last release listed with the reason of a news file or of the release-tier ledger. Its own `accept-record` accepts the record of both tiers, and `.github/workflows/accept-release.yml`, started by that run's completion on `dev`'s own context, pushes the acceptance onto `dev` while `dev`'s tip is the head judged, red when it is not. When the acceptance lands, the release pull request's next run re-uses the green one. The release pull request is refused any commit that changes the accepted state and is not an acceptance, and its build job checks that the version's section is dated, its tag free and `main`'s tip an ancestor. `release/version.py date` dates the section on `dev` before the release pull request, joins any news file merged after `bump` and moves the ledger's blocks under the version; `release/version.py release` commits nothing, tags `main`'s tip and pushes the tag alone, so the commit tagged is the one judged plus its acceptance. `bump`, `date` and the release's two reviews land in one pull request into `dev`, the release's preparation, which the decision job judges as documentation, since its one change outside documentation is the version line and its change to the release-tier ledger is exactly `date`'s move.
- **The judge's diet** (spec 138, step 5): the eight writing conventions (the specifications' shape and that they leave no choice undecided, one-line Markdown paragraphs, the labels of an executed write-up, the README's coverage badge, and the three rules that code and strings name no document of the knowledge tree) leave the goal count for `tests/lint/`, which the fast tier does not collect and the `quick` job runs as its `lint` step (`uv run pytest tests/lint`), gating `ci-status` without a ratchet; the four rules that hold more than writing stay goal checks. The fast tier has a budget: a normal-tier goal check whose fuel is past its family's cap in `tests/lint/budget.toml` (twice today's largest) is red on the pull request that grew it (the gather) and refused at the acceptance, until the file names the specification that will move it, and `lint` holds the accepted fuel too; a goal check past 60 seconds in `quick` is reported as a warning, never a failure. `--accept-judge` is needed only when a verdict-bearing judge file changed since the last acceptance (`tests/harness/paths.py`, `VERDICT_BEARING`: the known gaps, the upstream suites' TOML files and `expected/` lists, CPython's plan, the shard plan, the public API's list, the release tier's claims, which join the judge's files) and is refused as unnecessary otherwise, the judge's hash recording the rest. `uv run pytest --tier release` parses: `--tier` comes from the `pytest11` entry point of `wasi-python-judge-options`, a dev-only member of the uv workspace under `tests/judge_options/`, and the wheel declares none. The `coverage` job is gone: on a run with the merge-grade set each Linux leg of the product's own shards runs under coverage.py and sends its report to Codecov, which merges them into the badge.

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "138"
new = [
  "tests/checks/test_rules.py::test_the_writing_conventions_are_lint_not_goal_checks",
  "tests/checks/test_rules.py::test_the_verdict_bearing_files_are_judge_files",
  "tests/checks/test_rules.py::test_the_runners_coverage_rides_a_judge_leg",
]
retired = [
  "tests/checks/test_rules.py::test_specifications_have_their_header_and_sections",
  "tests/checks/test_rules.py::test_specifications_have_no_open_question",
  "tests/checks/test_rules.py::test_markdown_paragraphs_are_one_line_each",
  "tests/checks/test_rules.py::test_executed_memos_label_their_claims",
  "tests/checks/test_rules.py::test_readme_carries_the_codecov_badge",
  "tests/checks/test_rules.py::test_code_outside_src_names_no_context_document",
  "tests/checks/test_rules.py::test_no_string_names_a_context_document",
  "tests/checks/test_rules.py::test_src_names_no_context_document",
]
changed = [
  "tests/checks/test_rules.py::test_the_set_key_names_every_build_input",
  "tests/checks/test_rules.py::test_release_judges_in_shards",
  "tests/checks/test_rules.py::test_the_release_signs_and_publishes_what_build_made",
]
units = 51

[claim.judge]
"context/release-tier-claims.toml" = "the release tier's claims join the judge's files, as a verdict-bearing file"
```
