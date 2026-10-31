# 171: The packages a set carries

## Changelog

### New

- **List the packages an agent can import.** `wasi_python.packages()` returns each Python package in the runtime with its version and import names, without starting a guest; `wasi-python packages` prints them, or one JSON line with `--json`. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)

### Fixed

- **`importlib.metadata.packages_distributions()` answers in the guest.** Each package now carries its `top_level.txt`, so the guest maps `sklearn` to scikit-learn. [Limitations](https://claygendron.github.io/wasi-python/reference/limitations/)

### For contributors

- **Each package staged as a folder names its import names.** The zip step's `--metadata` takes `<PKG-INFO>=<name>,<name>`, and the build stops on a top-level name no package owns or two packages own. [Adding a package](https://claygendron.github.io/wasi-python/contributing/adding-a-package/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "171"
new = [
  "tests/checks/test_v1_3_data_stack.py::test_the_host_lists_the_packages_the_guest_finds*",
  "tests/checks/test_v1_3_data_stack.py::test_every_name_in_the_zip_belongs_to_a_package",
]
grows = ["tests/checks/*"]
growth = "Each of the 55 distributions' .dist-info gains its top_level.txt, so every guest's zip directory holds 55 more entries. Measured on darwin arm64 against dev's set at 117bcd67 (python.wasm byte for byte the same, a1137950): the zip 54,960,042 to 54,969,118 bytes (+9,076), 6,476 to 6,531 members; python-snapshot.wasm 104,660,252 to 104,684,438 (+24,186), the zip's directory being in the image; a plain start (-c pass) 277,589,139 to 279,014,133 fuel (+1,424,994, +0.51%, 25.9 k a member); a snapshot start 54,177,689 to 54,209,973 (+32,284, +0.06%), the larger directory freed at exit; one packages_distributions() on the snapshot 241,418,304 to 799,553,249, since it now reads 55 top_level.txt where it read none and answers 60 names instead of {}; the wheel, built by hand from each set, 99,478,845 to 99,487,321 bytes (+8,476), 5,370,279 under 104,857,600"
units = 34
[claim.judge]
"tests/public_api.txt" = "the public API gains Package (frozen dataclass: name, version, imports) and packages(artifacts=None), and nothing else"
```
