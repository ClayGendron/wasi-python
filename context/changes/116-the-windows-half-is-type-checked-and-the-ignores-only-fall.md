# 116: the Windows half is type-checked, and the ignores only fall

## Changelog

### For contributors

- **The runner's Windows code is type-checked on every run.** A second pass checks it as Windows sees it, each platform's class is checked against its interface, and the type checker's suppressions fell from 25 to 3; a rise needs a reason. [How structure is judged](https://claygendron.github.io/wasi-python/contributing/review-and-landing/#how-structure-is-judged)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "116"
# New: the shape rule and the count of the type checker's escapes, whose metric `ignores` is
# recorded for the first time at the acceptance after the merge (a new check, so nothing to
# compare and no growth to claim), and the unit file that runs the two passes over a copy.
new = [
  "tests/checks/test_rules.py::test_every_type_ignore_names_its_code_and_reason",
  "tests/checks/test_rules.py::test_the_type_checkers_escapes_are_counted",
  "tests/unit/test_typecheck.py",
]
# Judge changes, none verdict-bearing: the type-checking row runs two passes, pyproject.toml's
# [tool.mypy] excludes the Windows half from the Linux pass, and `ignores` joins `bytes` in the
# plugin, sameness and the acceptance from CI's record. The type-checking row's status, need
# and metric names do not move.
units = 7
```
