# 138: pull requests into `dev`, and the judge runs where it is needed

## Changelog

### Changed

- **Every merge into `dev` is accepted by CI** (spec 138, step 3): the run after a merge judges the normal tier on three systems, and two jobs follow a green gather. `accept-record` runs `uv run pytest --accept-from <record.json> --claims context/changes/` with no secret, and `accept-push`, in the `accept` environment, commits the two progress files alone and pushes them onto `dev` with a deploy key, only while `dev` is still the commit judged. A change's CHANGELOG line, package rows and claims are its news file under `context/changes/`, which `release/version.py bump` assembles at a release; `ci-status` refuses a pull request into `dev` that is not documentation only and has no news file, or no review file whose verdict begins "Lands", committed after its last code, by a reviewer other than its author. A documentation-only push onto a green head re-uses that head's run, and the weekly run opens an issue when it is red.
- **A release is a pull request from `dev` to `main`** (spec 138, step 4): its run is the whole workflow on the commit `main` will receive (a set built on macOS and never reused, both rebuilds and same-bytes, every shard of both tiers on three systems, `verify` on three and `quick`), and its gather has every goal: no `PLAN`, G7 holding the newest acceptance to the run's own set, clean and whole, and each release-tier row that moved since the last release listed with the reason of a news file or of the release-tier ledger. Its own `accept-record` accepts the record of both tiers, and `.github/workflows/accept-release.yml`, started by that run's completion on `dev`'s own context, pushes the acceptance onto `dev` while `dev`'s tip is the head judged, red when it is not. When the acceptance lands, the release pull request's next run re-uses the green one. The release pull request is refused any commit that changes the accepted state and is not an acceptance, and its build job checks that the version's section is dated, its tag free and `main`'s tip an ancestor. `release/version.py date` dates the section on `dev` before the release pull request, joins any news file merged after `bump` and moves the ledger's blocks under the version; `release/version.py release` commits nothing, tags `main`'s tip and pushes the tag alone, so the commit tagged is the one judged plus its acceptance. `bump`, `date` and the release's two reviews land in one pull request into `dev`, the release's preparation, which the decision job judges as documentation, since its one change outside documentation is the version line and its change to the release-tier ledger is exactly `date`'s move.

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "138"
new = [
  "tests/checks/test_rules.py::test_the_release_acceptance_is_pushed_from_devs_own_context",
  "tests/checks/test_rules.py::test_the_release_pull_request_checks_what_its_tag_will",
  "tests/checks/test_rules.py::test_the_accept_push_step_pushes_only_the_acceptance_onto_the_judged_tip[the release: dev is the head judged]",
  "tests/checks/test_rules.py::test_the_accept_push_step_pushes_only_the_acceptance_onto_the_judged_tip[the release: dev moved on]",
  "tests/checks/test_rules.py::test_the_accept_push_step_pushes_only_the_acceptance_onto_the_judged_tip[the release: a third file changed]",
]
changed = [
  "tests/checks/test_rules.py::test_release_judges_in_shards",
  "tests/checks/test_rules.py::test_the_accept_jobs_accept_a_green_merge_and_only_the_push_holds_the_key",
  "tests/checks/test_rules.py::test_the_accept_push_step_pushes_only_the_acceptance_onto_the_judged_tip",
]
units = 53

[claim.judge]
"tests/checks/test_rules.py" = "two new rules (the release's acceptance pushed from dev's own context, the release pull request's version step) and the accept push's script run for the release's workflow too"
"tests/harness/gather.py" = "the release pull request is gathered whole with no PLAN, its moved release-tier rows listed with the news files' and the ledger's reasons, and G7's release form requires its own built set"
"tests/harness/scan.py" = "the gather's PLAN on a pull request into dev alone, accept-push on a push alone, accept-release.yml's shape and the one other holder of the key it is, the release pull request's version step, and an evaluator of each job's if: under the plan's outputs"
"tests/harness/accept_from.py" = "the release's acceptance names the release and takes the ledger's claims beside the news files'"
"tests/harness/news.py" = "the release-tier ledger read in the news files' claim shape, and moved under its version by the date"
"tests/unit/test_ci_plan.py" = "accept on the release pull request, its re-use across its own acceptance, its refusal of accepted state no acceptance wrote, and the release's preparation judged as documentation, its ledger held to date's move"
"tests/unit/test_gather.py" = "the release pull request judged whole, its release form of G7, and its release-tier rows listed when a news file or the ledger claims them and red when nothing does"
"tests/unit/test_scan.py" = "the new scans' rows and the evaluator's"
"tests/unit/test_accept_from.py" = "the release's subject and claims"
"tests/unit/test_news.py" = "the ledger's rows"
"tests/unit/test_release_version.py" = "date and release, every row with git and subprocess refused and its own release files"
```
