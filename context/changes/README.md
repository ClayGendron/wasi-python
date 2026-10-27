# /context/changes

One news file per change that is not documentation only: `NNN-<slug>.md`, named after its specification (or after the pull request, when the pull request carries no specification). A pull request into `dev` that is not documentation only and carries none is red at `ci-status`. Its review file is `../reviews/NNN-<slug>-pr-YYYY-MM-DD.md`, with the same `NNN-<slug>`.

A news file says what the change moved, in three sections:

- **`## Changelog`**: the CHANGELOG lines, each a `- ` line under `### Added`, `### Changed`, `### Fixed` or `### Security`, as `CHANGELOG.md` uses them. Nobody edits `CHANGELOG.md`'s unreleased section by hand.
- **`## Package rows`** (optional): rows of the compiled packages' table in `docs/reference/packages.md` (`| package | version | what works |`) that the change adds or moves, or `None.`.
- **`## Claims`**: one `toml` block of `[[claim]]` tables, `spec` the file's number, in the shape of the claim lists (`../progress/README.md`) with three more keys.

```toml
[[claim]]
spec = "NNN"
new = []             # checks or files added
retired = []         # checks removed: the acceptance retires each absent check they name
changed = []         # checks whose status, need, reason, closer, area, facts or metric names move
passes = []          # upstream checks whose pass count moves
fewer = ""           # the reason, required when a count named in passes falls
grows = []           # checks whose fuel or bytes grow
growth = ""          # the reason, required with grows
units = 0            # unit tests added
[claim.judge]        # each verdict-bearing judge file changed, with its reason
"tests/known_gaps.toml" = "a new allowance"
[claim.moved]        # each check moved between tiers, with its reason
```

An entry with `::` is a check; one without is a file and stands for its checks; a trailing `*` is a prefix.

Who reads them:

- **The gather** lists each growth, fall in a pass count and tier move under `GROWTH` with the reason a claim gives, or `unclaimed`.
- **The accept job** (`uv run pytest --accept-from <record.json> --claims context/changes/`) takes every reason from the news files changed since the last acceptance. An absent check is retired only when `retired` names it; a growth, a fall, a verdict-bearing judge file changed (`tests/harness/paths.py`'s `VERDICT_BEARING`) and a tier move each need the claim that names it; any other judge change is recorded by the judge's hash and needs none. An unclaimed row refuses the acceptance with the row named, and the fix is a one-line pull request to the news file.
- **`release/version.py bump`** assembles every news file into the new version's CHANGELOG section and the packages page, then removes them. `tests/checks/test_rules.py::test_the_news_files_have_their_shape` holds every file here to the shape.

A later pull request of the same specification edits its news file: it adds its CHANGELOG lines and replaces the claim block with its own, since the accept job reads the block of each news file changed since the last acceptance.

A change that moves a release-tier row, or what one runs, also appends its `[[claim]]` block to the release-tier ledger, `../release-tier-claims.toml`: the run after its merge judges the normal tier alone and `bump` removes its news file, so the release pull request's gather and acceptance read the reason there (`../progress/README.md`, "The release tier").
