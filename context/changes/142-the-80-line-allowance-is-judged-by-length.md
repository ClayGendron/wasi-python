# 142: the 80-line allowance is judged by length

## Changelog

### Changed

- **The 80-line allowance is judged by length** (spec 142). Each function the long-function allowance lists is held at its listed length, one that grows past it or shrinks below it is reported, and the list is reset to the lengths the tree has (`run` 156, `run_async` 181 and `Session.__init__` 178 lines, which had grown past their listings unseen).

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "142"
units = 2
[claim.judge]
"tests/checks/test_rules.py" = "the long-function allowance's lengths become the bound; run, run_async and Session.__init__ are listed at 156, 181 and 178, the lengths they reached while nothing judged a length (the three entry points repeat one argument list, which gained a sentence for env and one for cache_dir in each docstring and one line in each body); _open_session, _instance and _Process.__init__ are lowered to 136, 155 and 81"
```
