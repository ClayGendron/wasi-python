# 168: The POSIX hosts have a module of their own

## Changelog

### For contributors

- **The platform code is split by host family.** The POSIX, Linux and macOS hosts now have a file of their own beside the Windows one, and the interface and the choice stay where they were. Nothing an embedder sees changes. [Your first change](https://claygendron.github.io/wasi-python/contributing/first-change/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "168"
new = []
retired = []
changed = []
passes = []
grows = []
units = 0
[claim.judge]
"tests/checks/test_rules.py" = "the platform rules name the new POSIX host module: PLATFORM_HALVES lets only the platform module import it and lets it import the shared half, and the comments say which module holds what"
"tests/unit/test_runner_package.py" = "ORDER places the POSIX host module between the Windows module and the platform module"
"tests/harness/api.py" = "RUNNER_FILES lists the POSIX host module among the runner's modules"
"tests/unit/test_runner_threads.py" = "the POSIX classes and the interpreter-call helper are named by the module that now holds them; no expectation changes"
"tests/unit/test_runner_calls.py" = "the Linux and macOS classes are named by the module that now holds them; no expectation changes"
"tests/unit/test_runner_module_caches.py" = "the Linux and macOS classes are named by the module that now holds them; no expectation changes"
"tests/unit/test_runner_module_cache_read.py" = "the access-list entry is named by the module that now holds it; no expectation changes"
```
