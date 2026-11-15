# 195: A review that waits fails no run

## Changelog

### For contributors

- **A pull request waiting for its review no longer fails its run.** Until the review is written or signed again, the `review` and `ci-status` checks stay red and block the merge, but the run is not failed, so nobody is mailed. A review signed wrong still fails. `release/precheck.py` runs the first check before a push. [Review and landing](https://claygendron.github.io/wasi-python/contributing/review-and-landing/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "195"
units = 19
[claim.judge]
"tests/harness/scan.py" = "rule 17 allows continue-on-error on the review job and ci-status alone, each with its exact expression on the plan's review_waiting or waiting output and no job needing it, so a review that only waits leaves both checks red and its run unfailed; the review job's rules hold that the plan hands on both outputs"
"tests/unit/test_ci_plan.py" = "a review not yet written, left behind by code, or not landing yet waits; a review signed by its author or no one does not; a missing news file fails ci-status beside a waiting review"
"tests/unit/test_scan.py" = "rule 17's one exception and its mutants, and the plan's two new outputs"
"tests/unit/test_precheck.py" = "the precheck runs quick's own scripts in order and installs its hook without overwriting another's"
```
