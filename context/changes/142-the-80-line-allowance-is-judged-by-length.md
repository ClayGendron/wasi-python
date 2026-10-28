# 142: the 80-line allowance is judged by length

## Changelog

### Changed

- **The 80-line allowance is judged by length** (spec 142). Each function the long-function allowance lists is held at its listed length, one that grows past it or shrinks below it is reported, and the list is reset to the lengths the tree has (`run` 156, `run_async` 181, `Session.__init__` 178 and `_Process.__init__` 83 lines, which had grown past their listings unseen).

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "142"
units = 2
[claim.judge]
"tests/checks/test_rules.py" = "the long-function allowance's lengths become the bound; run, run_async and Session.__init__ are listed at 156, 181 and 178, the lengths they reached while nothing judged a length (the three entry points repeat one argument list, which gained a sentence for env and one for cache_dir in each docstring and one line in each body); _Process.__init__ is listed at 83, the length it reached when the abandoned tool threads' count and the queue of finished pools each added a field while nothing judged a length; Session.run_async, _open_session and _instance are lowered to 81, 138 and 155"
```
