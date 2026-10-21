# 112 — Strings speak for themselves: no document cited in a string literal

- **Status:** **built 2026-10-21 on `5005ccbd`** (the release workflow's run 39589394200 on
  that commit: green on three systems but the gather's G7; the landing notes). Before:
  **drafted 2026-10-21** on `spec/112-strings-speak-for-themselves` from main's
  `d8fc73f`; **reviewed before build 2026-10-21**
  (`../reviews/112-strings-speak-for-themselves-spec-2026-10-21.md`, commit `6d98601c`: lands once
  M1 and M2 are written in; both, the five Lows and the three Notes are written in, its
  Disposition). A different agent reviews the build.
- **Date:** 2026-10-21
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe by effect, build-class by the letter** (§5.7), as spec 109 was. Two
  files under `scripts/` change (one string each: `gen_inittab.py`'s generated C comment and
  `refuse-python`'s refusal) and eight step names of `.github/workflows/release.yml` (and the
  `goal` marker's help in `pyproject.toml`, which no artifact carries), so the
  specification is build-class by AGENTS.md's definition. **One artifact's bytes move:**
  `MANIFEST` records the SHA-256 of every tracked file under `scripts/`, so its two `recipe`
  lines for those files change, and with them `SHA256SUMS`'s `MANIFEST` line and the wheel that
  carries the set. `MANIFEST`'s size does not change (a SHA-256 is 64 hex digits either way).
  **`python.wasm`, the snapshot and the stdlib zip keep their bytes** (INFERRED, confirmed by
  criterion 9): the inittab comment stays one line, so no line of the generated `inittab.c`
  moves, and a C comment compiles to nothing; `refuse-python` runs only when a build step calls
  an unpinned Python. **A judge change** (a rules check, its scanner, its unit rows, an
  allowance, and string literals across `tests/`): the lane accepts it with `--accept-judge`.
  No fuel row moves: no check that records fuel has a string that changes (the one citing
  string in such a check is kept for the closer, Decision 5's `GUEST_FUEL`).
- **Depends on:** **109** (landed: the comment rule outside `src/`, its scanner
  `CITATION_RULES`, its file list `context_citation_files` and its allowance
  `CONTEXT_CITATION_ALLOWED`). It builds on main. Wave 10 (045, 110, 111) edits
  `tests/checks/test_rules.py`, `tests/harness/scan.py` and `tests/unit/test_scan.py`; if that
  wave lands first, this specification rebases onto it and measures again (criterion 2).
- **Research it stands on:** the owner's answer to question 111 (`../decisions.md`, "Questions
  108 to 111": the citing strings are reworded before 0.1.0; the judge's allowance files and the
  guest's own sources stay in the reserved closer); spec 109's build review, finding 2
  (`../reviews/109-code-speaks-for-itself-2026-10-21.md`: 78 citing string lines, four of them
  read by a user); spec 107's build review, finding 3 (a `spec NNN` rule over string tokens).
  Its own measurements below, each labelled, on `d8fc73f`.

## The problem

Spec 109 made every comment and docstring outside `src/` give its reason in words. It left the
string literals alone (its rule (c)), and some of them are what a person reads first. The
progress group's title says "the progress harness (spec 002)". `--shard`'s help says "run one
shard of the release's plan (spec 063)". The scoreboard's not-machine-checked line ends "(spec
091)". The C file `gen_inittab.py` writes into every build says "(spec 047)". The release
workflow's step names, on the Actions page, end "(spec 063, Decision 5)". A number tells the
reader where a reason was once written, not what it is.

The owner answered question 111 on 2026-10-21: before 0.1.0, these strings give their reasons in
words. The judge's allowance files' comments and the guest's own sources stay in the reserved
closer, after 0.1.0.

**The population** (EXECUTED, `uv run python build/112/measure2.py` in the builder's worktree,
the reading of Decisions 2 and 3, on `d8fc73f`): **92 citations in string literals** in the
files this rule reads (and **108** more in the judge's allowance files, out of scope, Decision
4), and **93** with the review form the pre-build review added (Decision 2), the one more being
`CTYPES`'s, kind E. With 109's eight forms unchanged over every string, the count is 263 (`measure.py`); the 171
it drops are paths the judge opens and labels such as `S1` (Decision 2). Every one of the 93 is
in one of five kinds:

| kind | hits | literals | files |
|---|---|---|---|
| **A. Output a person reads**: the judge's messages, help and titles; a check's failure message; the build's refusal; the workflow's step names; the generated C comment | 45 | 42 | `plugin.py` 10, `scan.py` 4, `sameness.py` 4, `litter.py` 3, `scoreboard.py` 3, `paths.py` 2, `pins.py` 1, `history.py` 1, `guest.py` 1 (all `tests/harness/`); `test_v1_3_data_stack.py` 2, `test_v1_4_embedding.py` 2, `test_v1_5_rebuild_from_pins.py` 2; `release.yml` 8; `scripts/refuse-python` 1; `scripts/gen_inittab.py` 1 |
| **B. A test's copy of a message in A**, which it matches | 10 | 10 | `test_pins.py` 2, `test_sameness.py` 2, `test_landing_lane.py` 2, `test_patches.py` 1, `test_build_progress.py` 1, `test_several_cores.py` 1, `test_scan.py` 1 (the workflow step it splices) |
| **C. A comment inside a program held as a string**: nine host programs a check runs in a child Python, one guest program | 20 | 10 | `test_v1_4_embedding.py` 10 (four programs), `test_v1_2_hostile_guest.py` 6 (four; `PLANT` is the guest's), `test_landing_lane.py` 2, `test_scipy_build.py` 2 |
| **D. Data**: a rule's own name, a scanner's fixture, a gap's closer | 17 | 14 rows | `test_scan.py` 9, `test_shards.py` 5, `test_landing_lane.py` 1, `test_rules.py` 1, `scan.py` 1 |
| **E. Kept for the closer**: a guest program in a check that records fuel | 1 | 1 row | `test_v1_3_data_stack.py` 1 (`CTYPES`, "review 033") |

A, B and C are reworded: **75 hits**. D and E stay, one allowance row per phrase (Decision 5).
The read found four more citations the forms do not match, all in kind A, reworded with the
rest: the scoreboard's "(number 89)" and "(number 101)" (the owner's questions), `data_stack`'s
"(decision 34, …)", and `tests/harness/packages.py:560`'s "(Decision 14)". The pre-build review
found three more: the `goal` marker's help in `pyproject.toml:101` ("(spec 002)", a file 109 does
not read; Decision 3 now reads it), `CTYPES`'s "(review 033, finding 1)" (kind E, a form now),
and `tests/unit/test_gather.py:420`'s test id "(from before 085)" (reworded; no form matches a
bare number). `src/` has none (EXECUTED, the same reading over every `.py` under `src/`: 0).

## Decisions

### 1. The rule reads strings, beside 109's rule for comments

109's check reads comments and docstrings. This one reads every other string a file holds, so
that between them every word of prose and every literal is read. It is a sibling check, not a
wider 109: its forms differ (Decision 2), and so do its skips and its allowance. 109's check,
scanner and allowance do not change.

### 2. The forms it refuses: 109's, less the two that are data in a string

`STRING_CITATION_RULES` in `tests/harness/scan.py`, built from 109's `CITATION_RULES` patterns:

| rule | refuses |
|---|---|
| `specification` | 109's two forms: `spec NNN` in any case and spelling, and a bare `0NN's` |
| `constitution` | 109's: `constitution §` and a section numbered like `§4.15` |
| `memo` | 109's: the word |
| `review` | a review followed by a date `YYYY-MM-DD`; a review followed by a specification's number, `review 033` (`\breviews?\s+0\d{2}\b`, any case; the pre-build review's M2); a review named by its kind (109's list: build, pre-build, delta, follow-up, security, integration, re-review, confirmation's) |
| `question` | 109's: `question NN` |
| `named finding` | a finding a review names, **any letter**: `the review's C2`, `the build review, F1` |

Two of 109's forms are left out, each measured (EXECUTED, the 171 hits the narrowing drops):

- **A path** (`context/…`, and 109's review form followed by a path, `reviews/…`). In a string,
  a path is what the code opens or names as the file to fix: the progress history, the
  specifications the needs table points at, the evidence folders, the prior-art README. AGENTS.md
  already says the judge reads `context/` as data.
- **A bare finding identifier** (`S1`, `D0`, `F4.2`). In a string it is a label: the hostile
  guest's cases `S1` to `S9`, a parametrized test id `[S2-True]`, a schema's `$defs/D0`, the
  recipes' placeholder `@S12@`. The four string citations of that shape on the base each sit
  beside a review's name or a specification, so the `named finding` form, widened to every
  letter, holds them.

A bare `Decision N` or `criterion N` with no specification beside it is not refused, as in 109;
where one stands beside a removed specification it is removed with it.

### 3. What it reads

- **Files:** 109's files (`context_citation_files`: `tests/`, `.github/workflows/`, `scripts/`,
  `release/`), **every `.py` under `src/`**, **and `pyproject.toml`**, less the judge's allowance
  files (Decision 4). `src/` has no citing string today; reading it costs nothing and holds the
  product's own messages, the ones a user of the wheel reads. `pyproject.toml` registers the
  `goal` marker a second time, and `pytest --markers` prints both (the review's M1); its
  non-comment lines are read as any TOML's.
- **Python:** through `ast`: every `str` and `bytes` constant, and each f-string's literal parts
  joined (a replacement field read as `{…}`), so `"a " "spec 052"` is read whole. Not read, each
  edge exact (the review's Note 8):
  - **the docstrings 109 reads, and no more:** the first string token of a module's, a class's or
    a function's first statement when that statement is a plain string constant. A bare string
    statement elsewhere, an f-string in that place, and the later tokens of an implicitly
    concatenated docstring are read here, since 109 does not read them;
  - **a pattern:** the pattern argument (the first, or `pattern=`) of `re.compile`, `search`,
    `match`, `fullmatch`, `findall`, `finditer`, `sub`, `subn` and `split`
    (`re.compile(r"\bmemo\b")` is the rule's own vocabulary). `re.escape`'s argument is text and
    is read, and so is `sub`'s replacement;
  - **an admitted phrase:** the second item of each `(path, phrase, reason)` row of an assignment
    to a name ending in `_ALLOWED`. The paths and the reasons are read; a reason is a named
    constant, read like any string, so a reason cannot hide a citation.

  A phrase assembled with `+` (`"m" + "emo"`) is two strings, and is how a unit row writes a
  citation it needs (109's practice).
- **Other files:** every line that is not a `#` comment, and the part of a line before a
  trailing ` # `: the complement of 109's reading, so a shell `echo`, a YAML step name and a
  TOML value are read.
- A hit is reported as `path:line: rule: phrase`, the line being where the phrase starts: each
  string token of an implicitly concatenated literal keeps its own line (from `tokenize`), and a
  triple-quoted token adds the newlines before the phrase (the review's Note 9).

### 4. The judge's allowance files are not read

`tests/known_gaps.toml` and `tests/upstream/*.toml` are left out of the files, by a named
constant in the check with its reason: the owner kept them in the reserved closer (question
111), AGENTS.md rule 4 makes their edits a judge change of their own, and a gap's `closes_with`
names its closer by number in the judge's own format. Measured (EXECUTED): 108 hits, 41
distinct phrases, 40 of them `closes_with = "spec 067"` and its like. The guest's own sources
(`tests/jobs/*.py`, the three drivers) **are read**: under these forms they hold no citing
string (EXECUTED: 0; 109's bare-finding form saw `/F1`, a PDF font's name, twice in
`tests/jobs/pdf.py`), so their bytes need not move.

### 5. One allowance for data, each row with its reason, a stale row failing

`STRING_CITATION_ALLOWED` in `tests/checks/test_rules.py` holds `(path, phrase, reason)`, 109's
grain: a row admits that phrase anywhere in that file's strings; a row that admits nothing
fails. Fifteen rows, four reasons as named constants:

- **`RULE_NAME`** (2): `"memo"` in `tests/checks/test_rules.py` and `tests/harness/scan.py`, the
  name a rule table gives the form it refuses.
- **`FIXTURE`** (9): a scanner's input in a unit file: `tests/unit/test_scan.py`'s eight phrases
  in 109's citation rows (`constitution §`, `memo`, `review 2026-10-19`, `question 95`, `review's
  F4.2`, `build review`, `Confirmation's M5`, `Confirmation's`; `memo` also in a specification
  fixture's header) and `tests/unit/test_landing_lane.py`'s `memo` (a draft research file's
  name, `memo.md`, that the dirty-tree check is given). Their text is what the scanner reads,
  so rewording it would change the row; the rows stay as 109 wrote them.
- **`GAP_DATA`** (3): `tests/unit/test_shards.py`'s `spec 065`, `spec 001` and `spec 099`,
  `closes_with` values in a known-gaps fixture, the format the judge parses.
- **`GUEST_FUEL`** (1): `tests/checks/test_v1_3_data_stack.py`'s `review 033`, a comment in
  `CTYPES`, the guest program of `test_ctypes_stand_in_names_what_packages_import`, whose `guest`
  fixture records the run's fuel for both rows (`[plain]`, `[snapshot]`). Reason: "a guest program
  in a check that records fuel: its bytes are the guest's input, so it changes with the closer
  that re-measures the guest's fuel" (the review's M2). It is not reworded here.

No other row is added; a reviewer reads any addition.

### 6. How a string is reworded

109's rules, applied to strings:

- **(a)** Delete the citation and its connector: `(spec 062)`, `; spec 089`, `(spec 029,
  Decision 2)`. The sentence stands.
- **(b)** Where the citation was the reason, write the reason in words, drawn from the document
  it cited, which the builder reads; the landing notes list each with its document.
- **(c)** A test that matches a reworded message (kind B) changes to the new text in the same
  way it matched the old: an exact string stays exact, a substring a substring, a `match=` a
  `match=`, and a test that singled a message out by its citation singles it out by its whole new
  shape (the review's L6: `test_several_cores.py` matches `plugin.REFUSAL` as a pattern). No verdict, golden, expected file or progress file changes. The workflow step that
  `test_scan.py` splices out and back (`SET_SUMS_STEP`) is the workflow's text, so it follows
  the workflow's new name.
- **(d)** The inittab comment stays on one line, so the generated C keeps its line numbers.
- **(e)** A comment inside a held program (kind C) is reworded by (a) and (b) as 109 did
  comments. The one guest program, `PLANT` in `test_v1_2_hostile_guest.py`, is in a check that
  records no fuel, so its bytes may move.

### 7. What each string of kinds A and B says

The table is the draft's proposal; the builder may improve the words, and the landing notes
show the final text of every one.

| where | now ends or reads | becomes |
|---|---|---|
| `plugin.py:94`, the progress group's title | `the progress harness (spec 002)` | `the progress harness` |
| `plugin.py:108`, `--shard`'s help | `… plan (spec 063)` | `run one shard of the release's plan` |
| `plugin.py:151`; `test_landing_lane.py:395` | `… in the main tree (constitution §5.7); this is a linked worktree` | `… in the main tree; this is a linked worktree` |
| `plugin.py:181`, `:193` | `(spec 029, Decision 2)`, `(spec 029)` | removed (a) |
| `plugin.py:204`, the `goal` marker's help | `a v1 progress check (spec 002)` | `a v1 progress check` |
| `pyproject.toml:101`, the `goal` marker (found by the review) | `a v1 progress check (spec 002); area is …` | `a v1 progress check; area is v1.1 to v1.5 or rules` |
| `plugin.py:295` | `a shard runs serially (spec 063, Decision 4)` | `a shard runs serially: the shards are the parallelism` (b) |
| `plugin.py:517`, `REFUSAL`; `test_several_cores.py:434` | `refused: {} ({}; spec 052, Decision 7)`; the test looks for `spec 052` | `refused: {} ({})`; the test matches the line naming the option against `REFUSAL` made a pattern, each `{}` as `.+` (the review's L6) |
| `plugin.py:543` | `… it fails (the build review, F1)` | `… it fails` |
| `scoreboard.py:33`, the not-machine-checked line | `(number 89)`, `(number 101)`, `(spec 091)` | each removed (a) |
| `scoreboard.py:232`, `:300`; `history.py:258` | `(spec 062)` | removed (a) |
| `sameness.py:114` | `worst_platform on every check (from 092's build review)` | `worst_platform on every check` |
| `sameness.py:117`; `test_sameness.py:221`, `:227` | `a release record from before spec 092 (…): download the record of a run on a commit that has gather.py from spec 092`; the tests match `before spec 092` | `a release record older than the merged release record (…): download the record of a run on a commit whose gather.py writes the merged record` (b); the tests match `older than the merged release record` |
| `sameness.py:423`, `--claims`' help | `a claim list (spec 092, Decision 5)` | `a claim list ([[claim]] tables)` (b) |
| `litter.py:55`, `:164`, `:219` | `(spec 089, F6)`, `(spec 089)`, `; spec 089.` | removed (a) |
| `paths.py:72` | `(spec 097)` | removed (a) |
| `paths.py:405`, the worktree note; `test_landing_lane.py:676` | `(constitution §4.14 puts them outside)` | `(a worktree belongs outside the repository)` (b) |
| `pins.py:100`; `test_pins.py:86`, `:88`; `test_patches.py:267` | `the build skips it (spec 090)` | `the build skips it` |
| `guest.py:585` | `(spec 081)` | removed (a) |
| `scan.py:1545`, the signing ties' rule 14 | `… not its row in spec 057's table` | `… not its row in JOB_PERMISSIONS` (b) |
| `scan.py:1793`, rule 6 | `(set-sums-sha256; spec 085)` | `(set-sums-sha256)` |
| `scan.py:2338` | `(spec 026)` | removed (a) |
| `packages.py:560` (found by the read) | `(Decision 14)` | removed (a) |
| `test_v1_3_data_stack.py:229` | `(spec 069, Decision 5b)` | removed (a) |
| `test_v1_3_data_stack.py:237`, `_named` | `{what}: {names} (decision 34, spec 069)` | `{what}: {names}; the snapshot starts with the stdlib's bootstrap and no package` (b, the check's docstring) |
| `test_v1_4_embedding.py:5429`, `:5436` | `(spec 097; set TMPDIR …)`, `(spec 097): set TMPDIR …` | `(set TMPDIR …)`, `: set TMPDIR …` |
| `test_v1_5_rebuild_from_pins.py:417` | `{name} is {digest}, not the memo's` | `{name} is {digest}, not the reproducer's recorded TRY_TABLE_SHA256` (b) |
| `test_v1_5_rebuild_from_pins.py:486` | `(spec 086, Decision 7)` | removed (a) |
| `release.yml:79`, `:103` (and `test_scan.py:2102`), `:192`, `:258`, `:367`, `:483`, `:640`, `:759`, step names | `(spec 020)`, `(spec 085)`, `(spec 016, Decision 1)`, `(spec 016)`, `(…, verified; spec 063, Decision 5)` | each removed (a); the last three read `What the shard needs (the upstream kit and source trees, verified)` |
| `scripts/refuse-python:14`; `test_build_progress.py:1086` | `… host-python's Python (spec 079)` | `… host-python's Python` |
| `tests/unit/test_gather.py:420`, a test id (found by the review) | `the newest line with no set (from before 085)` | `the newest line with no set (from before a history line named its set)` |
| `scripts/gen_inittab.py:137`, the generated C comment | `/* Each init function runs inside the package context of its dotted name (spec 047). */` | `/* Each init function runs inside the package context of its dotted name. */` |

No check reads a workflow step's name but `test_scan.py`'s splice (EXECUTED, `grep` of the
eight names under `tests/`; the review's own read: `workflow_step_script`'s three callers name
none of the eight, and `needs:` and `if:` use ids).

## Intent

Every string a person reads outside the judge's allowance files and the guest's sources under
`recipes/`, and every string a check holds but one guest program's, gives its reason in words. A rules check over string tokens holds it, beside 109's for
comments and 107's for `src/`, and the only citations left in a string are data, named row by
row: a rule's own name, a scanner's fixture, a gap's closer.

## Design

- **The scanner** (`tests/harness/scan.py`, after 109's block): `STRING_CITATION_RULES`
  (Decision 2), `_python_strings(text)` and `_uncommented_lines(text)` (Decision 3),
  `string_citation_hits(path)` returning `(line, rule, phrase)`, and
  `string_citation_files(root)`: 109's files plus `src/**/*.py` and `pyproject.toml`, less the judge's allowance
  files.
- **The check** (`tests/checks/test_rules.py`, after 109's):
  `test_no_string_names_a_context_document`, with `RULE_NAME`, `FIXTURE`, `GAP_DATA`, `GUEST_FUEL`,
  `STRING_CITATION_ALLOWED` and `STRING_RULE_LATER` (the judge's allowance files' patterns and
  the reason of Decision 4). It reports each hit as `path:line: rule: phrase`, and each stale row.
- **The unit rows** (`tests/unit/test_scan.py`, fourteen): one parametrized row per form (ten
  cases: two specification forms, two constitution forms, the memo, a dated review, a numbered review, a review by
  its kind, a question, a named finding of a letter outside 109's six); one row for the carriers
  (a plain string, an implicit concatenation split mid-citation, an f-string's literal part, a
  bytes literal, a shell `echo`, a YAML step name, and the three edges of Decision 3 that are
  read: a bare string statement after the first, an f-string in a docstring's place, an
  `re.escape` argument, an allowance row's reason); one negative row (a docstring, a comment, a
  pattern given to `re.compile` and to `re.sub`, an allowance row's phrase, a `context/` path, a
  `reviews/` path, a label `S1`, a phrase assembled with `+`, a file that does not parse: no
  hit); one row for the files read (`src/` and `pyproject.toml` in, the judge's allowance files
  out); one row for the line reported inside a triple-quoted string and on the second line of an
  implicitly concatenated literal. Their fixtures are assembled from parts, so the unit file's own strings are
  never a hit.
- **The rewording:** by hand, kind by kind, from Decision 7's table and Decision 6's rules; 75
  hits in 62 literals across 24 files, plus `packages.py:560`.

## Scope

In: the string literals of `tests/`, `scripts/`, `release/` and `.github/workflows/` (and
`src/`, read and found clean); the check, its scanner, its unit rows, its allowance. Out: the
judge's allowance files (Decision 4: the reserved closer after 0.1.0); comments and docstrings
(109's and 107's checks, unchanged); the guest's own sources' comments (109's `GUEST_INPUT`
rows, unchanged; their strings hold no citation); `recipes/` (the guest's own sources, compiled
or frozen into the guest, such as `npy_fenv_flags.h`'s `#error … (spec 099)` and the stand-in
modules' docstrings: the reserved closer; the review's L4); `CTYPES`'s comment (Decision 5's
`GUEST_FUEL`, the closer that re-measures guest fuel); a bare `Decision N` or `criterion N` with no
specification beside it, and a bare number in an id (Decision 2; `test_history.py`'s three
`criterion N OPS` prints, `WRITE_PARITY`'s "Decision 12's deliberate differences" in a guest
program, and `test_landing_lane.py`'s ids `steer052` and `spoof052` keep theirs; the closer may
take them, the review's Note 10); `context/`, `CHANGELOG.md` and the roadmap (the lane's).

## Acceptance criteria

1. **Seen failing first:** on the base content, with the check, its scanner, its unit rows and
   its allowance in place and nothing else changed, the check fails with one line per kind A, B
   and C hit (75 by the draft's prototype; the built scanner's count recorded in
   `build/112/seen-failing.txt`), and every allowance row is used.
2. **Measured on the base it builds on:** the population table is re-run by the built scanner
   on the build's base (main, or wave 10's tip if it landed) and the landing notes give the
   counts by kind and file; any hit not in the table is reworded or answered in writing.
3. **Passes on the built commit**, with `STRING_CITATION_ALLOWED` holding only the fifteen rows
   of Decision 5, every one used, and 109's and 107's checks still green.
4. **The unit rows** (fourteen) pass; `tests/unit/test_scan.py` passes whole.
5. **Strings only:** for every Python file changed but `tests/harness/scan.py`,
   `tests/checks/test_rules.py` and `tests/unit/test_scan.py`, the `ast` dump with every string
   constant blanked is the same before and after; in those three, every top-level statement
   present on the base has the same blanked `ast`, apart from `SET_SUMS_STEP`'s string; for the
   other files, the lines that change are the eight step names, the one `echo` and the one marker
   line, and nothing else (`build/112/same-code.py`, prints nothing; the review's L5).
6. **No protected file changes:** `git diff --stat <base> -- tests/known_gaps.toml
   'tests/upstream/*.toml' tests/upstream/expected tests/upstream/python context/progress src
   tests/jobs tests/upstream/drive.py tests/upstream/regrtest_drive.py
   tests/upstream/package_drive.py` is empty.
7. **Every kind B test still matches its message:** each test of Decision 7's table passes by
   node id, and the landing notes show each message's old and new text.
8. **Rule (b) traced:** the landing notes list every string written under rule (b) with the
   document it stood on.
9. **The artifact set:** the builder's release workflow run on the built commit builds a set
   whose `python.wasm`, snapshot and stdlib zip have the SHA-256 of a release workflow run on the
   base, or on the latest commit whose `recipes/`, `scripts/` (but the two files) and
   `downloads/SHA256SUMS` are the base's (its run id in the landing notes; the review's L7), and
   whose `MANIFEST` differs from it only in the `recipe` lines of
   `scripts/gen_inittab.py` and `scripts/refuse-python`; every red line of the run is G7 or one
   the landing notes explain; the run id is in the landing notes.
10. **The fast tier** on the built commit fails exactly the baseline's nodes, and `sameness.py`
    against the base's record prints nothing outside this specification's claims. Against a
    frozen set built on the base, `test_manifest_recipes_match_the_tree` is the one expected
    difference, its message naming exactly the two files (the review's L7).
11. **Ruff:** `ruff check` and `ruff format --check` are green on `src/` and `tests/`.

## For the lane

- **Kind:** parallel-safe by effect, build-class by the letter (two `scripts/` files and the
  workflow's step names; `MANIFEST`'s two recipe lines move); a judge change. It takes one of a
  wave's two build-class slots, or lands beside judge-only work; it conflicts textually with any
  entry that edits the messages of Decision 7 or the three judge files of the Design.
- **The dispatch:** the builder's release workflow run on its branch (criterion 9).
- **The claim list** (its shape; the build writes it as run):

  ```toml
  [[claim]]
  spec = "112"
  new = [
    "tests/checks/test_rules.py::test_no_string_names_a_context_document",
  ]
  units = 14
  ```

  112: **retired checks:** none. **Lost passes:** none. **Rows that grow:** none (no fuel row:
  no check that records fuel changes a string; no bytes row: `MANIFEST` keeps its size). **The
  judge hash changes** in `tests/harness/scan.py`, `tests/checks/test_rules.py`,
  `tests/unit/test_scan.py` and every file under `tests/` whose strings changed.
- **The flags, the CHANGELOG line and the roadmap line:** as built, in the landing notes'
  "For the lane, as built".

## One line

Every string a person reads now says why in words, and a check over string literals keeps
document numbers out of them, with a rule's name, a fixture and a gap's closer as the named
exceptions.

## Landing notes

Built 2026-10-21 in the worktree `.claude/worktrees/agent-aa11adde6f6ab4801` of the main tree,
branch `spec/112-strings-speak-for-themselves`, from main's `d8fc73f` (no rebase needed: the
branch was main's tip). Every number here is EXECUTED on the base or the built commit, with its
command; the outputs are kept under `build/112/` in that worktree (git-ignored): `measure.py`,
`measure2.py`, `hits-before.tsv`, `hits-proposed.tsv`, `lines.py` (the draft's measurements);
`check_list.py` (the check's findings one per line), `seen-failing.txt`, `hits-built-before.txt`,
`hits-after.txt`; `reword.py` (the recorded rewording, `--list-b` for rule (b)), `reflow.py`,
`reword-applied.txt`; `same_code.py`, `same-code.txt`; `units.log`, `units2.log`; `fast.log`,
`fast-base.log`, `built.json`, `base.json`, `failed-built.txt`, `failed-base.txt`; `edit_spec.py`
and `disposition.py` (the review's fix text written in).

- **Commits, in the order built** (`git log --oneline d8fc73f..`): `3496fadb` (the draft),
  `6d98601c` (the pre-build review), `68512820` (its findings written in, its Disposition),
  `b976dcdf` (the check, its scanner, its fourteen unit rows and its allowance; seen failing),
  `5005ccbd` (the rewording), and the commit that carries these notes. **The built commit is
  `5005ccbd`**; the last commit touches only this file. `git diff --stat d8fc73f 5005ccbd`:
  30 files changed, 1,041 insertions, 84 deletions.
- **Seen failing first** (criterion 1; `seen-failing.txt`, on `b976dcdf`, the base's content
  with the check in place): **77 findings**, digest `890ff5b807ff`, every one of the fifteen
  allowance rows used. 77 is the draft's 75 plus the `goal` marker in `pyproject.toml` (the
  review's M1) and `sameness.py:118`, a second `spec 092` in the literal that starts at `:117`,
  which the draft's prototype counted once (it kept one hit per phrase and line of a literal's
  start; the built scanner reports each phrase on the line it starts).
- **Measured on the base it builds on** (criterion 2): main did not move; the built scanner over
  `d8fc73f`'s content finds exactly the table's population plus the review's three finds (its M1
  read, its M2 kind E, and the gather id, which no form matches and the read reworded): 77
  reworded findings, 23 admitted hits on fifteen rows (`hits-built-before.txt`, 100 lines).
- **Passes on the built commit** (criterion 3): `check_list.py` on `5005ccbd` prints nothing;
  every row is used (`hits-after.txt`: 24 admitted hits: `test_scan.py` 14, `test_shards.py` 5,
  `scan.py` 2, `test_rules.py`, `test_landing_lane.py` and `test_v1_3_data_stack.py` 1 each).
  109's and 107's checks pass beside it.
- **Unit rows** (criterion 4): fourteen in `tests/unit/test_scan.py` (ten forms, the carriers,
  the negative row, the files, the lines), all green on their first run; the scanner file passes
  whole. Run with every changed unit file and `tests/checks/test_rules.py` (`units.log`): 763
  passed, 7 skipped; by node id, `test_a_step_that_runs_an_unpinned_python_fails` and the twelve
  rows of `test_each_refused_option_exits_before_anything_runs` (`units2.log`): 13 passed.
- **Strings only** (criterion 5; `same_code.py d8fc73f`, `same-code.txt`): prints nothing. Its
  wider set is four files, not three: `tests/unit/test_several_cores.py`'s refusal test is the
  one code change the review's L6 asked for (Difference 2).
- **No protected file changes** (criterion 6): `git diff --stat d8fc73f -- tests/known_gaps.toml
  'tests/upstream/*.toml' tests/upstream/expected tests/upstream/python context/progress src
  tests/jobs tests/upstream/drive.py tests/upstream/regrtest_drive.py
  tests/upstream/package_drive.py` is empty.
- **Kind B** (criterion 7): each copy follows its message exactly (old → new):
  `test_landing_lane.py`'s `WORKTREE_LINE` (`… in the main tree (constitution §5.7); this is …` →
  `… in the main tree; this is …`) and the worktree note (`(constitution §4.14 puts them
  outside)` → `(a worktree belongs outside the repository)`); `test_pins.py` twice and
  `test_patches.py` (`the build skips it (spec 090)` → `the build skips it`);
  `test_build_progress.py` (`host-python's Python (spec 079) (log: …` → `host-python's Python
  (log: …`); `test_sameness.py` twice (`before spec 092` → `older than the merged release
  record`, a `match=` and a substring as before); `test_scan.py`'s `SET_SUMS_STEP` (the
  workflow's step, `(spec 085)` dropped); `test_several_cores.py` (the `spec 052` substring → the
  line matched against `plugin.REFUSAL` made a pattern, `re.escape` of each part joined by `.+`).
  Each passes by node id (above).
- **Rule (b)** (criterion 8; `reword.py --list-b`), each with the document its words came from:
    - `tests/harness/plugin.py`, the shard refusal: `a shard runs serially: the shards are the
    parallelism` ← spec 063, Decision 4 (shards run serially; the jobs are the parallelism).
  - `tests/harness/sameness.py`, the refusal of an older record: `a release record older than the
    merged release record (…): download the record of a run on a commit whose gather.py writes
    the merged record` ← spec 092 (the judge reads a release record, the merged record
    `gather.py` writes).
  - `tests/harness/sameness.py`, `--claims`' help: `a claim list ([[claim]] tables)` ← spec 092,
    Decision 5 (claim lists are `[[claim]]` tables).
  - `tests/harness/paths.py`, the worktree note: `(a worktree belongs outside the repository)` ←
    constitution §4.14 (a specification's worktree is outside the repository).
  - `tests/harness/scan.py`, the signing ties' rule 14: `not its row in JOB_PERMISSIONS` ← spec
    057, Design (the table of job permissions, held in code as `JOB_PERMISSIONS`).
  - `tests/checks/test_v1_3_data_stack.py`, `_named`: `; the snapshot starts with the stdlib's
    bootstrap and no package` ← spec 069 and the owner's decision 34, in the words of the check's
    own docstring.
  - `tests/checks/test_v1_5_rebuild_from_pins.py`: `not the reproducer's recorded
    TRY_TABLE_SHA256` ← research `2026-10-19-the-try-table-order-in-llvm` (the reduced
    reproducer and its recorded hash).
  - `tests/unit/test_gather.py`, a test id: `(from before a history line named its set)` ← spec
    085 (a history line records its set's `SHA256SUMS` hash).
  - `tests/checks/test_v1_2_hostile_guest.py`, `FAULTHANDLER_CHILD`: `# a session's turn: a turn
    after a late enable` ← spec 055 (bounded sessions: a session's turn).
  The rest are rule (a): the citation and its connector deleted, the sentence standing.
- **The rewording**: `reword.py`, 67 recorded edits in 27 files, applied with no miss
  (`reword-applied.txt`); `reflow.py` split the five strings that passed 100 columns, words
  unchanged; `ruff format` then re-wrapped five files (a literal that now fits one line). The
  inittab comment is one line, as Decision 6 (d) asks.
- **The artifact set** (criterion 9): the builder's run **39589394200** on `5005ccbd`
  (`release`, `workflow_dispatch`): every build, rebuild, verify and judge job green on three
  systems; red only on the gather's **G7** ("the newest acceptance is not on the release's
  set", since `MANIFEST` moved). Its scoreboard (`release-record-1`): **781/873 pass, 0 fail, 85
  gap, 7 blocked**, unit suite 4707/4737 (30 skipped); the comparison run **39572424790**
  (`wave/09`, `111d56f4`, green; `git diff --stat 111d56f4 d8fc73f -- recipes scripts
  downloads/SHA256SUMS .github` empty) reads 780/872, 4679/4709. `sameness.py` between the two
  records with this claim list (`build/112/sameness-ci.txt`), exit 0: `note: explained by
  claims: 112 2` (the new node and the unit count), beside the usual notes (3 checks run on no
  system, 54 Linux fuel rows not compared). **The set:** the two runs' `rebuild-ubuntu-24.04`
  `SHA256SUMS` differ in one line, `MANIFEST`'s; `python.wasm` (`11d7799d…`), the snapshot
  (`e65dfa2d…`) and the zip (`02d3a3b7…`) are byte for byte the base's. The two runs' release
  tarballs, unpacked and compared with `diff -r`, differ in `MANIFEST` lines 267 and 278 (the
  `recipe` lines of `scripts/gen_inittab.py` and `scripts/refuse-python`) and the `SHA256SUMS`
  line for `MANIFEST`, and in nothing else. `SHA256SUMS` of the set: `142bdd38` → `792fb63e`.
- **The fast tier** (criterion 10): with `WASI_PYTHON_ARTIFACTS` a clone (`cp -c -Rp`) of the
  main tree's `build/artifacts`, under the fast slot (`build/slots/fast`, owner 112), `-n 3`.
  That set is wave 10's rebuild (`SHA256SUMS` `d0d91cef`, statsmodels in its `MANIFEST`), not a
  set of this base, so its `MANIFEST` reads stale against this tree in more than the two
  recipe lines (the statsmodels patch and pins, as 097's builder saw with a set of another
  tree). The built commit `5005ccbd` (`fast.log`): **5 failed, 2,641 passed, 49 skipped** in 796 s. The base's content, `b976dcdf`,
  on the same set (`fast-base.log`): **6 failed, 2,640 passed, 49 skipped** in 789 s. The failing nodes differ in one: the
  new check, failing on the base's content and passing on the built commit (`diff` of the sorted
  `FAILED` lines, `failed-base.txt` and `failed-built.txt`). The five both fail are the set's, not
  this tree's: `test_manifest_recipes_match_the_tree` (18 findings, the statsmodels patch among
  them), `test_manifest_pins_match_the_pin_list` (statsmodels' pins),
  `test_packages_carry_their_metadata[plain]` and `[snapshot]` (the set's extra distributions)
  and `test_dotted_builtins_keep_their_import_names[snapshot]` (out of fuel on the larger set).
  `sameness.py build/112/base.json build/112/built.json --claims build/112/claims.toml`
  (`sameness.txt`) prints the one node, `status 'fail' != 'pass'`, and no fuel or bytes row:
  `CTYPES` and the other held programs moved no recorded fuel.
- **Ruff:** `uv run ruff check src tests` and `uv run ruff format --check src tests` clean on
  `5005ccbd`. No file under `src/` changes, so no mypy run.

### For the lane, as built

- **Kind:** parallel-safe by effect, build-class by the letter (`scripts/gen_inittab.py`,
  `scripts/refuse-python` and eight step names of the release workflow; `MANIFEST`'s two recipe
  lines move); a judge change. It touches no file under `src/`, no allowance file, no golden or
  expected file, no guest-run source.
- **The claim list** (TOML, as run):

  ```toml
  [[claim]]
  spec = "112"
  new = [
    "tests/checks/test_rules.py::test_no_string_names_a_context_document",
  ]
  units = 14
  ```

  - 112: **new checks (1 node), passing, no fuel, no bytes:**
    `tests/checks/test_rules.py::test_no_string_names_a_context_document`.
  - 112: **unit rows:** `tests/unit/test_scan.py` gains fourteen rows; one unit id is renamed,
    `tests/unit/test_gather.py::test_each_forgery_is_red[the newest line with no set (from before
    a history line named its set)]` (was `… (from before 085)]`): the suite's count rises by
    fourteen.
  - 112: **retired checks:** none. **Lost passes:** none. **Grown rows:** none (`CTYPES`, the
    one guest program whose check records fuel, keeps its bytes).
  - 112: **the judge hash changes** in `pyproject.toml`, `tests/harness/scan.py`,
    `tests/checks/test_rules.py`, `tests/unit/test_scan.py` and the 22 other files under `tests/`
    whose strings changed.
- **The flags** (paste-safe; no `--accept-growth`):

  ```
  --accept "112: string literals outside src/ (the judge's messages, help and titles, check failure messages, the build's refusal, the release workflow's step names, the generated inittab comment, the goal marker in pyproject.toml, a test id, and the programs checks hold) give their reasons in words; the tests that match a message follow it exactly; no verdict, golden, allowance file or guest-run source changed; MANIFEST's recipe lines for gen_inittab.py and refuse-python move, python.wasm, the snapshot and the zip do not"
  --accept-judge "112: a rules check that no string literal under tests/, scripts/, release/, .github/workflows/ or src/, nor in pyproject.toml, cites a project document (109's forms less paths and bare finding labels, a review by its number, a named finding of any letter), read through ast and tokenize for Python and through non-comment lines elsewhere, docstrings, re patterns and allowance phrases skipped; the judge's allowance files left to their own closer; an allowance of fifteen rows (rule names 2, scanner fixtures 9, gap closers 3, a fuel-recording guest program 1), each with its reason, a stale row failing; fourteen unit rows; ten tests' copies of reworded messages updated exactly, the refusal test matching REFUSAL's whole shape"
  ```

- **Dry-run needs:** none beyond its own run (criterion 9). The check runs where
  `test_rules.py` runs; it reads files only.
- **CHANGELOG line proposed** (the lane's file), under the one unreleased section: *Strings
  speak for themselves (spec 112). The judge's messages, help texts and titles, the `goal`
  marker, the build's refusal, the release workflow's step names and the comment in the
  generated inittab source give their reasons in words, with no specification number, review
  or constitution section; a rules check over string literals holds it, with a rule's own name,
  a scanner's fixture, a gap's closer and one fuel-recording guest program named as the
  exceptions. No behaviour, fuel or binary byte changes; `MANIFEST`'s recipe hashes of two
  `scripts/` files move.*
- **Roadmap:** the "Reserved: 112" line becomes this specification; the closer below it keeps
  the judge's allowance files (comments and strings), the guest's own sources' comments,
  `recipes/`, and `CTYPES`'s `review 033` (Decision 5's `GUEST_FUEL`).

### The builder's self-check

- rebased onto the named base today: built on `d8fc73f`, main's tip; main has not moved
  (`git fetch` at the end: main moved after the build, to `1875d4cd`, wave 10 landed; `git merge-tree` onto it has one conflict, `.github/workflows/release.yml` line 79, main's comment on the step (twenty-eight trees) against this step's new name: take both. The string rule over the merged tree finds only that line's main side, so wave 10 adds no citing string; the rebase is the wave's (criterion 2)).
- CI run: 39589394200 on `5005ccbd`, red only on G7; the Windows criterion is named: the check reads text and runs where
  `test_rules.py` runs.
- every number from a measured run on this base, labelled EXECUTED; no growth list (no artifact
  byte but `MANIFEST`'s recipe lines, no guest fuel).
- "For the lane": the claim list, the exact flags, each reason beginning with the spec number,
  the wave kind (parallel-safe by effect, build-class by the letter, a judge change), dry-run
  needs.
- every new check seen failing first (77 findings on the base's content); the unit rows' fixtures
  assembled from parts; no Windows or Linux branch in the scanner.
- gaps: none; reserved follow-ups: the closer's line widened (Roadmap above).
- `packages.toml`: untouched (no package); README rows: none change.
- CHANGELOG: proposed above, not written (the lane's); no owner question raised.
- `ruff check`, `ruff format --check`: green; mypy: no `src/` change; the fast tier: above.

### Differences from the specification's text, each with its reason

1. **Seen failing is 77, not 75**: the draft's prototype kept one hit per phrase per literal's
   first line, so `sameness.py`'s two `spec 092` in one literal counted once; and the review's
   M1 added the marker line. Every finding is in the table's kinds.
2. **Criterion 5's wider set has four files**: `tests/unit/test_several_cores.py`'s refusal test
   changes code, as the review's L6 asked (a pattern from `REFUSAL` in place of a substring), so
   `same_code.py` allows that one function to differ beyond its strings.
3. **The comparison of criterion 10** runs the fast tier twice on one set that is not this
   base's (the lane's instruction: a clone of the main tree's set, which is wave 10's rebuild),
   the base's content (`b976dcdf`) and the built commit, and compares their failing nodes,
   since against a set of another tree `test_manifest_recipes_match_the_tree` names more than
   the two files.
4. **The scanner's helper for non-Python files is `_uncommented_lines`**, not `_code_lines`
   (the Design's name): `scan.py` already binds `_code_lines` for shell scripts, and
   `test_no_module_level_name_is_bound_twice` refused the second binding.
5. **`string_citation_files(root, later)` takes the patterns to leave out**, and the check passes
   `STRING_RULE_LATER`: the files row can then test both halves.

### Disposition of the pre-build review

The pre-build review (`../reviews/112-strings-speak-for-themselves-spec-2026-10-21.md`, commit
`6d98601c`; verdict "lands once M1 and M2 are written in"): every finding is written in, commit
`68512820`, its Disposition section in the review. A different agent reviews the build.
