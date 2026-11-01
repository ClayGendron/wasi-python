# 177: Each pull request claims in a file of its own

## Changelog

### For contributors

- **Open pull requests no longer conflict over the release's claims.** The release ledger is now one file per pull request, named after its news file, instead of one file every pull request appended to; the check refuses a reason written into another change's file. [The release process](https://claygendron.github.io/wasi-python/contributing/release-process/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "177"
new = ["tests/checks/test_rules.py::test_the_release_ledger_is_a_file_per_pull_request"]
units = 18
[claim.judge]
"context/release-claims/*" = "the release ledger becomes a folder of one file per pull request: the six blocks of context/release-claims.toml move, byte for byte, each into the file named after its change's news file (159, 165, 166's two, 167, 171), the single file is removed, and the folder's README says its rule; the release reads the same claims"
```
