# Review of the oracle lock check: the oracle's lock parses and is its project's

- **Date:** 2026-10-21
- **Reviewer:** a fresh agent (wrote none of this change)
- **Reviewed:** `2db86e00` on `lane/oracle-lock-check`, base `3b7f6abf`
- **Run:** none. The lane said no judge tier and no builds for this judge-only change.
- **Time box:** 25 minutes (parallel-safe, judge-only)
- **Re-ran (EXECUTED):**
  - `uv run pytest tests/unit/test_scan.py -k lock tests/checks/test_rules.py::test_the_oracles_lock_is_its_projects`
    on the clone (lock of `3b7f6abf`): 6 unit rows passed; the rules row failed with
    "formulaic 1.2.2: its bare numpy entry matches 2 packages; statsmodels 0.15.0: its bare numpy
    entry matches 2 packages". That is the claimed message.
  - The rules row's body, with `jobs.ORACLE_PROJECT` pointed at a copy of each commit's lock and
    pyproject: `e64508e4` (wave/10 tip; its lock is byte-identical to `44249469`'s) PASS;
    main `d8fc73ff` PASS; `3b7f6abf` FAIL, the same two lines.
  - uv 0.9.22's own parser on the same three copies (`uv export --frozen --offline`, empty
    `UV_CACHE_DIR`): rc 0, rc 0, rc 2 "Dependency `numpy` has missing `source` field but has
    more than one matching package". The check and uv agree on all three real locks.
  - `tests/checks/test_rules.py::test_code_outside_src_names_no_context_document`: passed.
  - `ruff check` and `ruff format --check` on the three files: clean.

## Acceptance criteria against evidence

1. Red on the broken lock, with a message that names the entries: met (EXECUTED, above).
2. No false red on the fixed lock or on main's lock: met (EXECUTED, above).
3. Matches uv's parse rule: partly met. See Finding 1 (EXECUTED with uv 0.9.22).
4. Portable: met (READ). `tomllib` is stdlib from 3.11, the project's floor. No paths are built
   in `scan.lock_errors`. Both oracle files are pure ASCII, so `read_text()` with no encoding
   (as 28 other reads in `test_rules.py` do) decodes the same on Windows. CRLF checkouts are
   folded by universal newlines. No uv, cache, network or interpreter is needed, so it runs
   wherever `test_rules.py` runs.
5. Code speaks for itself: met. The new comments and docstrings cite no document; the citation
   row passes.
6. Judge not weakened: met (READ). The diff only adds a rules row, a scan function and five unit
   rows. No check, golden, gap, allowance or progress file changed. It is a judge change, so the
   lane's acceptance needs `--accept-judge`.
7. Structure: no new concern, flag, mutable state, seam, platform branch or private API.
   `lock_errors` is about 50 lines, under 80.

## Findings, most severe first

1. **Medium: the check misses two lock shapes that uv refuses** (`tests/harness/scan.py`,
   `lock_errors`, the `found` filter). The check takes an entry when exactly one package matches
   the fields the entry gives. uv's rule is stricter. If more than one package has the name, the
   entry must give its `source`. It must also give its `version`, unless the source is a source
   tree (directory, editable or virtual). Matching by the fields given is not enough.
   Failure (EXECUTED, uv 0.9.22, the unit test's lock shape):
   - numpy locked twice at different versions (2.5.2 registry, 2.4.0 url); seaborn's entry is
     `{ name = "numpy", version = "2.5.2" }`. The check returns `[]`. uv refuses: "missing
     `source` field but has more than one matching package".
   - numpy locked twice at the same version from two sources; the entry is
     `{ name = "numpy", source = { registry = "https://pypi.org/simple" } }`. The check returns
     `[]`. uv refuses: "missing `version` field but has more than one matching package".
   Both are things a text merge can leave behind, like the bare entry it already caught.
   Fix text: inside the dependency loop, before the match count, add the ambiguity rule:
   ```python
   same = by_name.get(_dist_name(dep["name"]), [])
   tree = any(k in dep.get("source", {}) for k in ("directory", "editable", "virtual"))
   if len(same) > 1 and ("source" not in dep or ("version" not in dep and not tree)):
       missing = "source" if "source" not in dep else "version"
       errors.append(
           f"{p['name']} {p.get('version', '')}: its {dep['name']} entry has no {missing},"
           f" and {len(same)} packages are named {dep['name']}"
       )
       continue
   ```
   Keep the zero-or-several count for entries that pass that rule. Change the docstring to say
   the rule: "an entry for a name that several packages share names both its source and its
   version". Add two unit rows, the two shapes above, each seen red first. The bare row's
   expected message changes with it. Evidence that closes it: the two new rows red before the
   fix and green after, and the rules row still PASS on `e64508e4` and main and FAIL on
   `3b7f6abf`.

2. **Low: latent false reds in the root comparison** (`_requirement_pins` and the `root`
   lookup). None of these shapes is in today's oracle pyproject, so nothing is red now
   (EXECUTED with probes):
   - an extra, `"seaborn[stats]==0.13.2"`: the pin read is `[stats]==0.13.2`, but the lock
     says `==0.13.2`;
   - a spaced or multi-clause specifier, `"seaborn >= 0.13, < 0.14"`: compared as raw text
     against uv's normalised form;
   - a project name that is not normalised (`P_x`): `p["name"] == project.get("name")` finds 0
     packages, because uv writes `p-x`.
   Fix text: compare the root name through `_dist_name` on both sides. Capture the extras in
   the regex apart from the specifier. Compare specifiers with the spaces removed. Or say in
   the docstring that only exact `==` pins and URL pins are compared. That is what the oracle
   uses, and the limit is already stated for markers.

3. **Note: uv's own parser also works with no cache.** `uv export --frozen --offline` with an
   empty `UV_CACHE_DIR` parsed the good locks (rc 0) and refused the broken one (rc 2, uv's
   message), with no network and no 3.15 interpreter (EXECUTED, uv 0.9.22). It does not resolve,
   so it avoids the direct-URL wheel failure that ruled out `uv lock --check --offline`. It could
   back the file-only rules with uv's exact rule. It does not replace them: it does not compare
   the lock with the project, and it depends on which uv is on the path. No action is required.

## Constitution checks

- §4 constraints: uv only (yes; no bare python or pip); tests count operations (yes, no timing);
  the judge not weakened (yes; the change only adds).
- §7 never-do list: nothing tripped.

## Verdict

Lands once Finding 1 is fixed: the two missing ambiguity shapes, with their unit rows seen red
first. Finding 2 is answered in writing or fixed.

## Disposition

The builder, 2026-10-21, commit `a001b5c5` on `lane/oracle-lock-check` (on `2db86e00`).

1. **Medium, fixed.** `lock_errors` now applies uv's rule first. When a name is shared, an
   entry must give its source, and its version too unless the source is a directory, editable
   or virtual. Entries that pass the rule still get the zero-or-several count. The docstring
   states the rule. There are three new unit rows: version and no source, source and no
   version (both red before the fix), and a source tree with no version (quiet). The bare row's
   expected message changed to "its numpy entry has no source, and 2 packages are named
   numpy". The zero-match row now gives version and source, so it still exercises the count.
2. **Low, fixed.** Extras are captured apart from the specifier and left out of the
   comparison, as markers are. Specifiers are compared with spaces removed on both sides. The
   root package is found by normalised name. One row covers all three; it was red before the
   fix.
3. **Note, no action.** `uv export --frozen --offline` is not used, so the check does not
   depend on which uv is on the path.

Evidence (EXECUTED): before the fix, 4 rows were red: the two Medium rows, the bare row (its
message changed) and the Low row. After the fix, `tests/unit/test_scan.py` passes 258 of 258.
`lock_errors` passes on `e64508e4`'s and main `d8fc73ff`'s lock and pyproject. On `3b7f6abf`
it fails with: "formulaic 1.2.2: its numpy entry has no source, and 2 packages are named numpy;
statsmodels 0.15.0: its numpy entry has no source, and 2 packages are named numpy". The rules
row on the clone's `3b7f6abf` lock shows the same two findings. `ruff check` and
`ruff format --check` on `tests/` are clean.

## Confirmation

Confirmed at `a001b5c5` (EXECUTED, uv 0.9.22, empty `UV_CACHE_DIR`). The two shapes from
Finding 1 are now red, and so are the bare and absent-version shapes. Each time, uv refused the
same lock for the same missing field. A wrong version on a name with one package is red in both
the check and uv ("no locked package"). Real locks: e64508e4 PASS, main d8fc73ff PASS, 3b7f6abf
FAIL (formulaic and statsmodels). Finding 2's three probes (extras, spaced specifier, a project
name that is not normalised) now return `[]`. The unit rows matching `lock`, the citation row
and ruff are green. The change lands.
