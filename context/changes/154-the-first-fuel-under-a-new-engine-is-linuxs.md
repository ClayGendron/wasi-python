# 154: the first fuel under a new engine is Linux's

## Changelog

### For contributors

- **Every upstream group keeps a fuel across an engine move.** When no macOS fuel of the current wasmtime is recorded for a group only Linux ran, the acceptance records Linux's, labelled with its system and never compared with another system's. [Two tiers of tests](https://claygendron.github.io/wasi-python/contributing/release-process/#two-tiers-of-tests)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "154"
new = [
  "tests/unit/test_scoreboard.py::test_fuel_another_system_measured_is_never_compared[a darwin run against a linux fuel]",
  "tests/unit/test_scoreboard.py::test_fuel_another_system_measured_is_never_compared[a linux fuel against a linux fuel]",
  "tests/unit/test_scoreboard.py::test_fuel_another_system_measured_is_never_compared[a fall]",
  "tests/unit/test_scoreboard.py::test_accept_lets_the_keys_own_system_replace_another_systems_fuel",
  "tests/unit/test_accept_from.py::test_a_check_only_linux_ran_takes_linuxs_fuel_when_none_is_of_this_engine[another engine]",
  "tests/unit/test_accept_from.py::test_a_check_only_linux_ran_takes_linuxs_fuel_when_none_is_of_this_engine[none recorded]",
  "tests/unit/test_accept_from.py::test_linux_first_fuel_keeps_the_lower_and_is_never_a_growth",
  "tests/unit/test_accept_from.py::test_darwin_fuel_replaces_another_systems_without_a_claim",
  "tests/unit/test_gather.py::test_a_darwin_record_against_another_systems_fuel_is_neither_red_nor_listed",
  "tests/unit/test_plugin.py::test_a_local_run_replaces_fuel_another_system_measured",
]
units = 10
[claim.judge]
"context/release-tier-claims.toml" = "127's block is removed: the acceptance now records Linux's fuel for a check only Linux ran when none of the current engine is recorded, so an engine move drops no fuel and no claim needs to clear the upstream suites' growth"
```
