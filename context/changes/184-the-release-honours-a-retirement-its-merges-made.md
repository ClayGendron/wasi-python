# 184: The release honours a retirement its merges made

## Changelog

### For contributors

- **A check retired at its merge no longer stops the release.** The release's acceptance reads every change's reasons again, and refused a retirement because the check was already gone; it now accepts one a merge since the last release made, and refuses any other as before. [Two tiers of tests](https://claygendron.github.io/wasi-python/contributing/release-process/#two-tiers-of-tests)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "184"
units = 3
[claim.judge]
"tests/harness/accept_from.py" = "on the release pull request, a retired entry also names a check a history line since the last release's acceptance retired, since the release reads again the claims its merges were accepted on; asked for by the owner on 2026-11-02"
"tests/unit/test_accept_from.py" = "three rows: a retirement a merge made since the last release is honoured, one before the last release is not, and a merge still refuses an entry that names no absent check"
```
