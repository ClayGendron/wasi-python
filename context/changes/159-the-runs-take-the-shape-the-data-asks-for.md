# 159: the runs take the shape the data asks for

## Changelog

### For contributors

- **The published set is built on arm64 Linux.** The release's artifact set and wheel are compiled on arm64 Linux instead of arm64 macOS; x86_64 Linux and arm64 macOS rebuild them from the pins and must give the same bytes before anything is cached, signed or published. [The same bytes from any build host](https://claygendron.github.io/wasi-python/reference/artifacts/#the-same-bytes-from-any-build-host)
- **A pull request's run ends sooner.** The tests start beside lint instead of after it, macOS runs on a pull request only when the platform module or the engine's pin changed, the longest test shards are split, and the review file has its own check, `review`. [What a pull request runs](https://claygendron.github.io/wasi-python/contributing/review-and-landing/#what-a-pull-request-runs)
- **The release run packs its slow tests into fewer legs.** The release tier's shards are packed by measured minutes, about twelve a leg, and the build shard runs in the x86_64 rebuild, so a merge's run no longer waits for a compile. [What the release workflow does](https://claygendron.github.io/wasi-python/contributing/release-process/#what-the-release-workflow-does)
- **sympy's slowest test no longer holds a release leg.** `test_uniform_P`, which upstream expects to fail, ran past the release job's 30 minutes under CPython 3.15.2; it now runs to a small fuel cap and is recorded as a known gap, so every release leg is packed to about twelve minutes. [What the release workflow does](https://claygendron.github.io/wasi-python/contributing/release-process/#what-the-release-workflow-does)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "159"
new = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[sympy-slow-uniform-P]"]
retired = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[sympy-r-stats-4-continuous-rv-2]"]
[claim.judge]
"tests/upstream/sympy.toml" = "sympy's test_uniform_P, the whole of the group sympy-r-stats-4-continuous-rv-2, takes 3.54 T of fuel under CPython 3.15.2 (+23.6% over the accepted 2.87 T) and its leg ran past the release judge job's 30 minutes in run 41201012715; one test cannot be split, so by the owner's choice of 2026-10-31 it is a trap, sympy-slow-uniform-P, run alone to the 50 G cap with sympy-r-stats-4-continuous-rv-3, like the six sympy tests already past the bound for one test; the group and its split keyword go, the split keeps rv-1 and rv-3 with the same tests, and the family's budget, the sum of its caps, falls by 4.3 T less 50 G"
"tests/known_gaps.toml" = "the new trap sympy-slow-uniform-P is a gap, its finding out of fuel at the 50 G cap (digest 8a6adb372535), closed by docs/reference/limitations.md as its seven sympy siblings are; approved by the owner on 2026-10-31"
"tests/release_shards.toml" = "upstream-release-033, which held only the retired group, is removed and no other shard is renumbered; the trap rides with sympy-r-stats-4-continuous-rv-3 in upstream-release-041, at most 50 G more; no release shard is past twelve measured minutes any longer"
"context/release-claims.toml" = "a block for the release: the retired group, the new trap and sympy's release-tier growth under CPython 3.15.2, one group measured, the others read at the next weekly run"
```
