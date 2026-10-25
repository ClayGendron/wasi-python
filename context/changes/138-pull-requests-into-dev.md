# 138: pull requests into `dev`, and the judge runs where it is needed

## Changelog

### Changed

- **Every merge into `dev` is accepted by CI** (spec 138, step 3): the run after a merge judges the normal tier on three systems, and two jobs follow a green gather. `accept-record` runs `uv run pytest --accept-from <record.json> --claims context/changes/` with no secret, and `accept-push`, in the `accept` environment, commits the two progress files alone and pushes them onto `dev` with a deploy key, only while `dev` is still the commit judged. A change's CHANGELOG line, package rows and claims are its news file under `context/changes/`, which `release/version.py bump` assembles at a release; `ci-status` refuses a pull request into `dev` that is not documentation only and has no news file, or no review file whose verdict begins "Lands", committed after its last code, by a reviewer other than its author. A documentation-only push onto a green head re-uses that head's run, and the weekly run opens an issue when it is red.

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "138"
```
