# 084: Merged work is cleared

## Changelog

### For contributors

- **A merged change's worktree and branch are cleared.** Once a pull request is squash-merged into `dev` and a green run after the merge covers it, its worktree and local branch are removed; GitHub deletes the remote branch at the merge, and the pull request's head stays fetchable by its number. [Review and landing](https://claygendron.github.io/wasi-python/contributing/review-and-landing/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "084"
```
