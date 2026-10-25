# 138: pull requests into `dev`, and the judge runs where it is needed

## Changelog

### Changed

- **Every merge into `dev` is accepted by CI** (spec 138, step 3): the run after a merge judges the normal tier on three systems, and two jobs follow a green gather. `accept-record` runs `uv run pytest --accept-from <record.json> --claims context/changes/` with no secret, and `accept-push`, in the `accept` environment, commits the two progress files alone and pushes them onto `dev` with a deploy key, only while `dev` is still the commit judged. A change's CHANGELOG line, package rows and claims are its news file under `context/changes/`, which `release/version.py bump` assembles at a release; `ci-status` refuses a pull request into `dev` that is not documentation only and has no news file, or no review file whose verdict begins "Lands", committed after its last code, by a reviewer other than its author. A documentation-only push onto a green head re-uses that head's run, and the weekly run opens an issue when it is red.

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "138"
new = [
  "tests/checks/test_rules.py::test_the_news_files_have_their_shape",
  "tests/checks/test_rules.py::test_the_accept_jobs_accept_a_green_merge_and_only_the_push_holds_the_key",
  "tests/checks/test_rules.py::test_the_accept_push_step_pushes_only_the_acceptance_onto_the_judged_tip",
  "tests/checks/test_rules.py::test_the_weekly_run_opens_an_issue_when_red_and_never_accepts",
]
changed = [
  "tests/checks/test_rules.py::test_the_release_signs_and_publishes_what_build_made",
  "tests/checks/test_rules.py::test_one_required_check_holds_every_job",
  "tests/checks/test_rules.py::test_every_job_checks_out_the_head_commit",
]
units = 171

[claim.judge]
"tests/checks/test_rules.py" = "four new rules: the news files' shape, the accept jobs, the accept push's own script, the weekly run"
"tests/harness/accept_from.py" = "new: the acceptance from CI's record"
"tests/harness/news.py" = "new: the reader of the news files"
"tests/harness/plugin.py" = "--accept-from and --claims, answered before any session; the news files' retirements read into the ratchet; the worktree refusal no longer names the lane"
"tests/harness/scoreboard.py" = "an acceptance's line may carry fields of its own; an absent check a news file retires is listed, not red"
"tests/harness/history.py" = "the three-systems need reads the systems an acceptance from CI's record names"
"tests/harness/gather.py" = "after a merge into dev the rows an acceptance needs a reason for are listed, each with its news file's reason, and the merged record carries the verdict, the event and each shard's guards"
"tests/harness/scan.py" = "the accept jobs' and the weekly run's scans; the plan reads runs (actions: read); the new jobs' permissions"
"tests/unit/test_accept_from.py" = "new: the fourteen refusals and the command"
"tests/unit/test_news.py" = "new: the news files' shape"
"tests/unit/test_ci_plan.py" = "the news and review refusals, the accept and weekly outputs, the re-use of a green run"
"tests/unit/test_gather.py" = "the post-merge listing, the claimed reason, the merged record's new fields"
"tests/unit/test_release_version.py" = "bump assembles the news files"
"tests/unit/test_sameness.py" = "a run's entry in the merged record has more fields"
"tests/unit/test_scan.py" = "the accept and weekly scans' rows; the fixture's plan reads runs"
"tests/unit/test_landing_lane.py" = "the worktree refusal's new words"
"tests/unit/test_plugin.py" = "a run with an absent check a news file retires is green and lists it"
"tests/unit/test_scoreboard.py" = "the ratchet's colour leaves out an absent check a news file retires"
```
