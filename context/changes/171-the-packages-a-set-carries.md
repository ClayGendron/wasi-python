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
growth = "Each distribution's .dist-info gains its top_level.txt, 58 members after 167, so every guest's zip directory is larger. Measured on darwin arm64 against dev's set at a750e8fe, built from the same tree by dev's own step 70 (python.wasm the same, 2d00a2ee): the zip 57,058,947 to 57,068,536 bytes (+9,589), 6,663 to 6,721 members; python-snapshot.wasm 104,870,698 to 104,890,482 (+19,784), the zip's directory being in the image; a plain start (-c pass) 282,492,922 to 283,900,438 fuel (+1,407,516, +0.50%, 24.3 k a member); a snapshot start 54,644,143 to 54,695,369 (+51,226, +0.09%), the larger directory freed at exit; one packages_distributions() on the snapshot 243,942,159 to 826,296,121, since it now reads 58 top_level.txt where it read none and answers 63 names instead of {}; the wheel, built by hand from each set, 101,649,159 to 101,659,539 bytes (+10,380), 3,198,061 under 104,857,600"
units = 37
[claim.judge]
"tests/public_api.txt" = "the public API gains Package (frozen dataclass: name, version, imports) and packages(artifacts=None), and nothing else"
```
