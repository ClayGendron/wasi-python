# 155: the tag's run publishes what the release pull request judged

## Changelog

### For contributors

- **A tag's run publishes what the release pull request judged.** The tag's run rebuilds the set from the pins on three hosts, checks that its bytes and its commit are the ones the release pull request judged and recorded, installs the wheel on three systems, signs and publishes; it runs no test again. [What the release workflow does](https://claygendron.github.io/wasi-python/contributing/release-process/#what-the-release-workflow-does)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "155"
new = [
  "tests/checks/test_rules.py::test_a_tag_publishes_what_the_release_pull_request_judged",
  "tests/checks/test_rules.py::test_ci_status_fails_on_a_job_that_did_not_pass_or_a_refusal[a tag*",
]
retired = ["tests/checks/test_rules.py::test_the_judge_matrices_are_the_shard_plan_on_every_release[a pushed tag]"]
units = 37
[claim.judge]
"tests/harness/gather.py" = "--prove-set [--tree-only]: a tag's run, which no longer judges, holds the tagged commit to the release pull request's acceptance (the newest line from CI, the release tier and a pull request, whole and clean, on the tagged commit's parent, on the tag's own set and python.wasm) and requires the tagged commit to change accepted.json and one history volume alone; the gather itself is unchanged"
"tests/harness/scan.py" = "the workflow's rules follow the tag's new run: tag_run_errors (the plan's publish output, inputs and build on judge or rebuild, the tree proved before the compile, the build shard and its record only where the plan's build output says, the judged job and its proof), attest and publish need judged in place of the gather, ci-status reads the plan's publish and is red on a skipped publish, judged's permissions and its place outside a merge's acceptance"
```
