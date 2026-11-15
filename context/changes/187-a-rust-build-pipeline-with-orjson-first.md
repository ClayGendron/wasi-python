# 187: A Rust build pipeline, with orjson first

## Changelog

### New

- **orjson is built in: fast JSON from Rust.** `import orjson` gives orjson 3.13.0, compiled from Rust into both binaries, with native orjson's bytes for `dumps` and `loads`. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)

### For contributors

- **The build compiles Rust.** Rust 1.100.0 comes from Rust's own servers and every crate from crates.io, each pinned by SHA-256, and cargo builds offline; orjson's crate type is widened by `recipes/patches/orjson-3.13.0/0001-the-library-is-also-an-rlib.patch`. [Building from source](https://claygendron.github.io/wasi-python/contributing/building/)

## Package rows

| orjson | 3.13.0 | Built in, compiled from Rust: dumps and loads with every option, dataclasses, datetimes, UUIDs, enums and numpy arrays, with native orjson's bytes. A panic inside orjson ends the run, as natively. |

## Claims

```toml
[[claim]]
spec = "187"
new = [
  "tests/checks/test_v1_3_rust.py",
]
retired = []
changed = []
passes = []
grows = []
units = 0
[claim.judge]
"tests/harness/scan.py" = "the host table learns the three Rust names of each host"
"tests/harness/pins.py" = "orjson's sdist is a source tree the tree check reads, and its release tag's archive is a test source"
"tests/harness/needs.py" = "orjson joins the built source components"
"tests/harness/paths.py" = "orjson, Rust's standard library and PyO3 join the packages and the licence components"
"tests/harness/import_list.py" = "a new gate: each binary's imports are exactly recipes/guest-imports.txt"
"tests/upstream/packages.toml" = "orjson is a suite; Rust's standard library and PyO3 are reached through it"
"tests/upstream/orjson.toml" = "orjson's own suite: a smoke group in the normal tier and the rest in the release tier"
"tests/release_shards.toml" = "orjson's two groups and the Rust check file join existing shards"
"tests/checks/test_rules.py" = "the patch rule's docstring counts eight inputs"
```
