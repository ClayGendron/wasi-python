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
grows = ["tests/checks/*"]
growth = "orjson, compiled from Rust with its standard library and PyO3, is linked into python.wasm and its Python pieces join the zip. Measured on darwin arm64 in run 43664780183 against the set at 338ed06dff: python.wasm 103,587,348 to 104,009,953 bytes (+422,605, +0.41%); python-snapshot.wasm 109,648,301 to 110,070,067 (+421,766); importing the dotted builtins 6,476,257,363 to 6,487,540,162 fuel (+0.17%); the cpython-fs suite 67,567,425,211 to 67,856,495,045 fuel (+0.43%). The larger module costs every check that loads it a little fuel; nothing else changes"
units = 59
[claim.judge]
"tests/harness/scan.py" = "the host table learns the three Rust names of each host, and the Rust build's rules"
"tests/harness/pins.py" = "orjson's sdist is a source tree the tree check reads"
"tests/harness/needs.py" = "orjson joins the built source components"
"tests/harness/paths.py" = "orjson, Rust's standard library and PyO3 join the packages and the licence components"
"tests/harness/import_list.py" = "a new gate: each binary's imports are exactly recipes/guest-imports.txt"
"tests/upstream/packages.toml" = "orjson's suite is later, closing with 192, which measures its groups' fuel; Rust's standard library and PyO3 are reached through it"
"tests/release_shards.toml" = "the Rust check file joins an existing shard"
"tests/checks/test_rules.py" = "the patch rule's docstring counts eight inputs, and the Rust build's rules: crate pins, the toolchain, the panic switch, offline cargo, the gates and the package rows"
"tests/harness/jobs.py" = "the golden job orjson_json joins the jobs"
"tests/harness/callbacks.py" = "a getset table is read only where a type reaches it, through tp_getset, a Py_tp_getset slot or a code store into that field: run 43793800978 reported libxml2's HTML element row `center` as a setter of the wrong type once a stray word or constant in the larger binary equalled its address"
```
