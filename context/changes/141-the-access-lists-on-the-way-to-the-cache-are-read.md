# 141: the access lists on the way to the cache are read

## Changelog

### Security

- **On macOS, a folder on the way to the module cache whose access list lets another user or group add, remove or rename what it holds, or change its list, means the cache is not used**, with a warning that names the folder, the principal and the rights; a deny entry, such as the `deny delete` every home carries, and an entry for you or root pass; a list that cannot be read means the cache is not used; on Linux the mode's group bits already show what a list grants, so nothing new is read there (spec 141).

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "141"
new = [
  "tests/unit/test_runner_module_cache_read.py::test_an_entry_that_lets_another_change_a_folder_on_the_way_is_not_used",
  "tests/unit/test_runner_module_cache_read.py::test_an_entry_that_changes_nothing_or_names_no_one_new_passes",
  "tests/unit/test_runner_module_cache_read.py::test_a_list_that_cannot_be_read_means_the_cache_is_not_used",
  "tests/unit/test_runner_module_cache_read.py::test_when_roots_list_fails_the_warning_says_no_folder_can_hold_the_cache",
  "tests/unit/test_runner_module_cache_read.py::test_on_macos_an_allow_entry_on_the_way_is_not_used",
  "tests/unit/test_runner_module_cache_read.py::test_on_macos_the_homes_deny_entry_passes",
  "tests/unit/test_runner_module_cache_read.py::test_on_macos_a_folder_made_below_an_inheriting_entry_is_not_used",
  "tests/unit/test_runner_module_cache_read.py::test_on_macos_each_entry_is_read_as_it_is_written",
  "tests/unit/test_runner_module_cache_read.py::test_on_linux_a_named_entry_shows_in_the_group_bits",
]
# Judge change, not verdict-bearing: the resolve-once row's stand-in for the C library names the
# ten calls the one access-list table now resolves, the last still acl_free, so the row holds the
# whole table to being published at once (seen red when the table is published before it is full).
changed = [
  "tests/unit/test_runner_threads.py::test_a_resolve_once_table_is_never_seen_half_filled",
]
units = 24
```
