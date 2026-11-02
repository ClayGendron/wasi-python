# 183: A pass count that rises is listed

## Changelog

### For contributors

- **A suite that passes more tests no longer stops a release.** The release's gather listed a rise in a suite's pass count as unexplained; it now shows it with the reason a change gives, as the acceptance already did, while a fall still needs its reason and a lost pass still fails. [Two tiers of tests](https://claygendron.github.io/wasi-python/contributing/release-process/#two-tiers-of-tests)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "183"
units = 4
[claim.judge]
"tests/harness/gather.py" = "an upstream group's pass count that rose is listed under GROWTH and never red, as the ratchet and the acceptance hold, with the text of a claim that names it; a fall still needs its fewer; approved by the owner on 2026-11-01"
"tests/unit/test_gather.py" = "four rows: a rise listed on the release pull request, a fall that needs its fewer, a rise that never hides a lost pass, and the text a rise is shown with"
```
