# 157: The reactor prepares a starting image

## Changelog

### Added

- **Other engines can start every call from a starting image.** The snapshot binary exports `prepare`, which runs your setup code once and leaves memory ready to copy into each new instance. [Embed from other languages](https://claygendron.github.io/wasi-python/how-to/embed-from-other-languages/#start-each-call-from-a-starting-image)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "157"
new = [
  "tests/checks/test_v1_4_prepare.py",
  "tests/checks/test_v1_1_artifact_set.py::test_manifest_names_the_snapshot_packages",
]
grows = ["tests/checks/test_v1_*"]
growth = "the reactor gains the export `prepare`, a prepared instance's ending and five reseeds in `_refresh`, so both binaries are larger and every run unmarshals and refreshes a little more"
units = 7
[claim.judge]
"tests/release_shards.toml" = "the new check file test_v1_4_prepare.py joins the own-guest shard on all three systems, as every product check file is in a files shard"
"context/release-tier-claims.toml" = "the block that claims the upstream suites' fuel growth for the release pull request's acceptance, which reads the ledger beside the news files"
```
