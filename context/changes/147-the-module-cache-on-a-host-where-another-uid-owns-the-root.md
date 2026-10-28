# 147: the module cache on a host where another uid owns the root

## Changelog

### Fixed

- **The module cache works on a host where another uid owns `/`**, as on Cloudflare Containers, where every start compiled for about five minutes: the owner of `/` is trusted on the way to the cache as root is, on `/`'s own file system, since it can already replace any folder there, and the mode rule is unchanged; when `/` itself is open to other writers the warning says no folder can help, and to close `/` or pass `cache_dir=False`, instead of pointing at `$WASI_PYTHON_CACHE`; the cache's owner test is the effective uid, as the runner's other folders' is; a folder made on the way between the check and the runner's `mkdir` is judged; `$WASI_PYTHON_CACHE` is read once, when the call is made, and a `..` after a link in it or in `cache_dir` means what the system means (spec 147).

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "147"
new = [
  "tests/unit/test_runner_module_cache_read.py::test_the_owner_of_root_is_trusted_on_the_way_as_root_is",
  "tests/unit/test_runner_module_cache_read.py::test_a_root_others_may_write_still_refuses",
  "tests/unit/test_runner_module_cache_read.py::test_when_root_fails_the_warning_says_no_folder_can_hold_the_cache",
  "tests/unit/test_runner_module_cache_read.py::test_an_overflow_owner_of_root_is_trusted_on_root_alone",
  "tests/unit/test_runner_module_cache_read.py::test_the_cache_asks_the_one_owner_test",
  "tests/unit/test_runner_module_cache_read.py::test_a_folder_made_on_the_way_after_the_walk_is_judged",
  "tests/unit/test_runner_module_cache_read.py::test_module_miss_requires_held",
  "tests/unit/test_runner_module_caches.py::test_a_relative_cache_variable_is_the_folder_it_named_at_the_call",
  "tests/unit/test_runner_module_caches.py::test_a_cache_variable_set_after_the_call_is_not_read_by_it",
  "tests/unit/test_runner_module_caches.py::test_a_dotdot_after_a_link_in_cache_dir_means_what_the_system_means",
  "tests/unit/test_runner_module_caches.py::test_on_windows_a_cache_folder_is_made_absolute_keeping_every_dotdot",
]
# Judge changes, neither file verdict-bearing: the swap row is rewritten so that wasmtime is
# given the path and the name's stamp checked after the load is what discards the swapped file
# (its premise restored; skipped on Windows, where the held-handle row covers it); and the three
# direct calls of _module_miss in the two files pass held=None by name, since held is required.
changed = [
  "tests/unit/test_runner_module_caches.py::test_a_cwasm_swapped_between_its_check_and_its_load_is_discarded",
]
units = 25
```
