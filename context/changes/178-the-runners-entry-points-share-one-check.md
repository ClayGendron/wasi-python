# 178: The runner's entry points share one argument check and one async wrapper

## Changelog

### For contributors

- **The runner's argument check and async plumbing have their own module.** The check every entry point runs, the default pool, the registry of live calls and the exit hook moved out of the runner, and both `run_async`s now await one shared wrapper. Nothing an embedder sees changes. [Your first change](https://claygendron.github.io/wasi-python/contributing/first-change/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "178"
new = []
retired = []
changed = []
passes = []
grows = []
units = 0
[claim.judge]
"tests/checks/test_rules.py" = "LONG_FUNCTIONS: run_async lowered from 217 to its measured 197 and Session.run_async dropped at 77 lines, since both now await the shared wrapper; run raised from 182 to 183 by its one new line, which reads the defaults and passes them to the moved argument check"
"tests/unit/test_runner_package.py" = "ORDER places the new entry-point module between the sessions module and the runner, and LATE names the tool import of the argument check in the file that now holds it"
"tests/harness/api.py" = "RUNNER_FILES lists the new entry-point module among the runner's modules"
"tests/checks/test_v1_4_public_api.py" = "the argument check is named by the module that now holds it and given the defaults its entry point read; the same test still counts one read per entry point; no expectation changes"
"tests/unit/test_runner_limits.py" = "the argument check is named by the module that now holds it and given the defaults; no expectation changes"
"tests/unit/test_runner_tools.py" = "the argument and tool checks are named by the module that now holds them and given the defaults; no expectation changes"
"tests/unit/test_runner_async.py" = "the pool's submit is named by the module that now holds it and given the defaults' reader; no expectation changes"
"tests/checks/test_v1_2_hostile_guest.py" = "the exit hook a guest program calls is named by the module that now holds it; no expectation changes"
```
