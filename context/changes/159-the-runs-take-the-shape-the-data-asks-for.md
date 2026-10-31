# 159: the runs take the shape the data asks for

## Changelog

### For contributors

- **The published set is built on arm64 Linux.** The release's artifact set and wheel are compiled on arm64 Linux instead of arm64 macOS; x86_64 Linux and arm64 macOS rebuild them from the pins and must give the same bytes before anything is cached, signed or published. [The same bytes from any build host](https://claygendron.github.io/wasi-python/reference/artifacts/#the-same-bytes-from-any-build-host)
- **A pull request's run ends sooner.** The tests start beside lint instead of after it, macOS runs on a pull request only when the platform module or the engine's pin changed, the longest test shards are split, and the review file has its own check, `review`. [What a pull request runs](https://claygendron.github.io/wasi-python/contributing/review-and-landing/#what-a-pull-request-runs)
- **The release run packs its slow tests into fewer legs.** The release tier's shards are packed by measured minutes, about twelve a leg, and the build shard runs in the x86_64 rebuild, so a merge's run no longer waits for a compile. [What the release workflow does](https://claygendron.github.io/wasi-python/contributing/release-process/#what-the-release-workflow-does)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "159"
new = ["tests/checks/test_rules.py::test_the_review_job_fails_on_a_review_refusal_or_no_plan*"]
units = 63
[claim.judge]
"tests/release_shards.toml" = "the shard plan is reshaped and no check moves between tiers or leaves the judge: own-guest is three files shards (own-guest-a, -b, -c), own-hostile and own-embedding each give their later functions to a nodes shard (own-hostile-b, own-embedding-c), own-embedding-a gives its later half to own-embedding-b, and the 229 release shards are 65, whole earlier shards packed by their measured judge-step minutes to at most twelve each, each with a `minutes` key"
"tests/harness/shards.py" = "rule (j): every release shard carries its measured minutes, no other shard does, and there are at most 80 release shards; the build shard runs on the x86_64 rebuild"
"tests/harness/gather.py" = "BUILD, the plan's build output, tells the gather whether the build shard ran: where it did not (a merge into dev, which no longer rebuilds), expected_keys omits build/build and G3 and G5 leave the build shard's checks unselected, as a normal run leaves the release tier's; its record comes from rebuild-linux-x86-64"
"tests/harness/scoreboard.py" = "an acceptance from CI's record keeps the passes of checks the record did not select in the history's passed set, as a normal run keeps the release tier's"
"tests/harness/accept_from.py" = "a check no shard of the record ran (the build shard on a merge's run) keeps its accepted row and its pass"
"tests/harness/scan.py" = "the workflow's rules follow its new shape: the build on arm64 Linux beside quick, the rebuilds on x86_64 Linux (with the build shard, after the zero-patch step and before the wheel) and arm64 macOS, the gather needing the x86_64 rebuild and never same-bytes, no max-parallel, the review job and ci-status not needing it"
"tests/harness/budget.py" = "a release shard past twelve measured minutes is a lint warning, never a failure"
```
