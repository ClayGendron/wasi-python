# 161: Growth is listed on dev and reconciled at the release

## Changelog

### For contributors

- **A merge is recorded once its tests pass.** After a merge, a growth, a fall in passes, a test moved between tiers or a changed test file with no reason no longer stops the record; the record names it, and the release waits until each has its reason, in the news file or the release ledger. [After a merge](https://claygendron.github.io/wasi-python/contributing/review-and-landing/#after-a-merge)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "161"
new = ["tests/checks/test_rules.py::test_the_release_ledger_holds_claim_blocks_in_their_shape"]
units = 35
# After the merge, the plugin's rows met the runner's own push-to-dev variables and judged as a
# merge; their fixture now clears them, so they judge as a local run unless a row sets them.
[claim.judge]
"context/release-claims.toml" = "the release-tier ledger is renamed the release ledger and widened to carry any claim block; it holds its header comments alone, rewritten, and no block"
```
