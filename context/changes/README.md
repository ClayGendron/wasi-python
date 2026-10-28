# /context/changes

One news file per change that is not documentation only: `NNN-<slug>.md`, named after its specification (or after the pull request, when the pull request carries no specification). A pull request into `dev` that is not documentation only and carries none is red at `ci-status`. Its review file is `../reviews/NNN-<slug>-pr-YYYY-MM-DD.md`, with the same `NNN-<slug>`.

A news file says what the change moved, in three sections:

- **`## Changelog`**: the release's notes for this change, written for an embedder who did not follow the work. `bump` copies them into `CHANGELOG.md`, which is the GitHub release, the site's changelog page and PyPI's link, so they are the only text a reader gets; the detail an agent needs stays in the specification's landing notes, which the file's title names. Each entry is one `- ` line under one of six headings, in this order:
  - `### New`: something an embedder can do that they could not before (a function, an argument, a package, a host).
  - `### Faster`: the same result in less time or memory, said in the reader's terms (a start, a call, an import).
  - `### Security`: a hole closed or a guest's reach narrowed, with the advisory's identifier and link when one exists.
  - `### Fixed`: something that did not work as the documentation says, and now does.
  - `### Upgrading`: a change an embedder may need to act on (a value now refused, a default or a pin that moved, something removed), and the entry says what to do.
  - `### For contributors`: the build, the tests, the release process and the documentation's own tooling, nothing an embedder sees.

  Choose the heading by what the reader gets, not by what the code did. A change that both gives and asks something writes two entries. When two headings fit, use the first in the list; a change an embedder sees that fits none of the first five goes under New. An entry is a bold lead of two to twelve words that says the value, then the one fact that changed, then a link to a page of `https://claygendron.github.io/wasi-python/`, last; at most sixty words, not counting the links' addresses. For example: `- **Unbounded tool calls now end after an hour.** With `deadline_s=None` and no session lifetime, a tool call used to wait as long as its tool ran; it now raises `ToolTimeout` in the guest after 3,600 seconds. Give the tool a `timeout_s` to choose another bound. [Bound a tool's time](https://claygendron.github.io/wasi-python/how-to/tools/#bound-a-tools-time)`. An entry names no specification, review, finding or `context/` path, no private module or harness file, and no fuel figure unless the number is the point; an entry that adds or drops a carried patch names its `recipes/patches/` path. When no page explains the change, link the nearest page a reader acts from (the security model for a fixed pinned component, the packages page for a pin, the defaults page for a bound), or add the paragraph to a page. An entry that needs more than sixty words is two changes, or carries detail that belongs on the page. The model of 0.1.2's notes in `../specifications/152-release-notes-say-what-a-release-gives-the-reader.md`, "Design", is the standard. Nobody edits `CHANGELOG.md`'s unreleased section by hand, but for the release's summary and the rewrites its notes' reader asks for, made in the preparation pull request alone.
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
