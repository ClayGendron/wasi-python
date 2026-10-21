# 112 — Strings speak for themselves: no document cited in a string literal

- **Status:** **drafted 2026-10-21** on `spec/112-strings-speak-for-themselves` from main's
  `d8fc73f`. A different agent reviews it before the build (constitution §5.6: two files under
  `scripts/` change, which the build runs or hashes), and a different one after.
- **Date:** 2026-10-21
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe by effect, build-class by the letter** (§5.7), as spec 109 was. Two
  files under `scripts/` change (one string each: `gen_inittab.py`'s generated C comment and
  `refuse-python`'s refusal) and eight step names of `.github/workflows/release.yml`, so the
  specification is build-class by AGENTS.md's definition. **One artifact's bytes move:**
  `MANIFEST` records the SHA-256 of every tracked file under `scripts/`, so its two `recipe`
  lines for those files change, and with them `SHA256SUMS`'s `MANIFEST` line and the wheel that
  carries the set. `MANIFEST`'s size does not change (a SHA-256 is 64 hex digits either way).
  **`python.wasm`, the snapshot and the stdlib zip keep their bytes** (INFERRED, confirmed by
  criterion 9): the inittab comment stays one line, so no line of the generated `inittab.c`
  moves, and a C comment compiles to nothing; `refuse-python` runs only when a build step calls
  an unpinned Python. **A judge change** (a rules check, its scanner, its unit rows, an
  allowance, and string literals across `tests/`): the lane accepts it with `--accept-judge`.
  No fuel row moves: no check that records fuel has a string that changes.
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
4). With 109's eight forms unchanged over every string, the count is 263 (`measure.py`); the 171
it drops are paths the judge opens and labels such as `S1` (Decision 2). Every one of the 92 is
in one of four kinds:

| kind | hits | literals | files |
|---|---|---|---|
| **A. Output a person reads**: the judge's messages, help and titles; a check's failure message; the build's refusal; the workflow's step names; the generated C comment | 45 | 42 | `plugin.py` 10, `scan.py` 4, `sameness.py` 4, `litter.py` 3, `scoreboard.py` 3, `paths.py` 2, `pins.py` 1, `history.py` 1, `guest.py` 1 (all `tests/harness/`); `test_v1_3_data_stack.py` 2, `test_v1_4_embedding.py` 2, `test_v1_5_rebuild_from_pins.py` 2; `release.yml` 8; `scripts/refuse-python` 1; `scripts/gen_inittab.py` 1 |
| **B. A test's copy of a message in A**, which it matches | 10 | 10 | `test_pins.py` 2, `test_sameness.py` 2, `test_landing_lane.py` 2, `test_patches.py` 1, `test_build_progress.py` 1, `test_several_cores.py` 1, `test_scan.py` 1 (the workflow step it splices) |
| **C. A comment inside a program held as a string**: nine host programs a check runs in a child Python, one guest program | 20 | 10 | `test_v1_4_embedding.py` 10 (four programs), `test_v1_2_hostile_guest.py` 6 (four; `PLANT` is the guest's), `test_landing_lane.py` 2, `test_scipy_build.py` 2 |
| **D. Data**: a rule's own name, a scanner's fixture, a gap's closer | 17 | 14 rows | `test_scan.py` 9, `test_shards.py` 5, `test_landing_lane.py` 1, `test_rules.py` 1, `scan.py` 1 |

A, B and C are reworded: **75 hits**. D stays, one allowance row per phrase (Decision 5). The
read found four more citations the forms do not match, all in kind A, reworded with the rest:
the scoreboard's "(number 89)" and "(number 101)" (the owner's questions), `data_stack`'s
"(decision 34, …)", and `tests/harness/packages.py:560`'s "(Decision 14)". `src/` has none
(EXECUTED, the same reading over every `.py` under `src/`: 0).

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
| `review` | a review followed by a date `YYYY-MM-DD`; a review named by its kind (109's list: build, pre-build, delta, follow-up, security, integration, re-review, confirmation's) |
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
  `release/`), **and every `.py` under `src/`**, less the judge's allowance files (Decision 4).
  `src/` has no citing string today; reading it costs nothing and holds the product's own
  messages, the ones a user of the wheel reads.
- **Python:** through `ast`: every `str` and `bytes` constant, and each f-string's literal parts
  joined (a replacement field read as `{…}`), so `"a " "spec 052"` is read whole. Not read: the
  docstrings (109's), the pattern given to a `re` function (`re.compile(r"\bmemo\b")` is the rule's
  own vocabulary), and the value of an assignment to a name ending in `_ALLOWED` (an allowance
  holds the phrases it admits). A phrase assembled with `+` (`"m" + "emo"`) is two strings, and
  is how a unit row writes a citation it needs (109's practice).
- **Other files:** every line that is not a `#` comment, and the part of a line before a
  trailing ` # `: the complement of 109's reading, so a shell `echo`, a YAML step name and a
  TOML value are read.
- A hit is reported as `path:line: rule: phrase`, the line being where the phrase starts inside
  the literal.

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
fails. Fourteen rows, three reasons as named constants:

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

No other row is added; a reviewer reads any addition.

### 6. How a string is reworded

109's rules, applied to strings:

- **(a)** Delete the citation and its connector: `(spec 062)`, `; spec 089`, `(spec 029,
  Decision 2)`. The sentence stands.
- **(b)** Where the citation was the reason, write the reason in words, drawn from the document
  it cited, which the builder reads; the landing notes list each with its document.
- **(c)** A test that matches a reworded message (kind B) changes to the new text in the same
  way it matched the old: an exact string stays exact, a substring a substring, a `match=` a
  `match=`. No verdict, golden, expected file or progress file changes. The workflow step that
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
| `plugin.py:295` | `a shard runs serially (spec 063, Decision 4)` | `a shard runs serially: the shards are the parallelism` (b) |
| `plugin.py:517`, `REFUSAL`; `test_several_cores.py:434` | `refused: {} ({}; spec 052, Decision 7)`; the test looks for `spec 052` | `refused: {} ({})`; the test looks for `refused:` beside the option |
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
| `scripts/gen_inittab.py:137`, the generated C comment | `/* Each init function runs inside the package context of its dotted name (spec 047). */` | `/* Each init function runs inside the package context of its dotted name. */` |

No check reads a workflow step's name but `test_scan.py`'s splice (EXECUTED, `grep` of the
eight names under `tests/`).

## Intent

Every string a person reads outside the judge's allowance files, and every string a check
holds, gives its reason in words. A rules check over string tokens holds it, beside 109's for
comments and 107's for `src/`, and the only citations left in a string are data, named row by
row: a rule's own name, a scanner's fixture, a gap's closer.

## Design

- **The scanner** (`tests/harness/scan.py`, after 109's block): `STRING_CITATION_RULES`
  (Decision 2), `_python_strings(text)` and `_code_lines(text)` (Decision 3),
  `string_citation_hits(path)` returning `(line, rule, phrase)`, and
  `string_citation_files(root)`: 109's files plus `src/**/*.py`, less the judge's allowance
  files.
- **The check** (`tests/checks/test_rules.py`, after 109's):
  `test_no_string_names_a_context_document`, with `RULE_NAME`, `FIXTURE`, `GAP_DATA`,
  `STRING_CITATION_ALLOWED` and `STRING_RULE_LATER` (the judge's allowance files' patterns and
  the reason of Decision 4). It reports each hit as `path:line: rule: phrase`, and each stale row.
- **The unit rows** (`tests/unit/test_scan.py`, thirteen): one parametrized row per form (nine
  cases: two specification forms, two constitution forms, the memo, a dated review, a review by
  its kind, a question, a named finding of a letter outside 109's six); one row for the carriers
  (a plain string, an implicit concatenation split mid-citation, an f-string's literal part, a
  bytes literal, a shell `echo`, a YAML step name); one negative row (a docstring, a comment, a
  `re.compile` pattern, an `*_ALLOWED` tuple, a `context/` path, a `reviews/` path, a label `S1`,
  a phrase assembled with `+`, a file that does not parse: no hit); one row for the files read
  (`src/` in, the judge's allowance files out); one row for the line reported inside a
  multi-line string. Their fixtures are assembled from parts, so the unit file's own strings are
  never a hit.
- **The rewording:** by hand, kind by kind, from Decision 7's table and Decision 6's rules; 75
  hits in 62 literals across 24 files, plus `packages.py:560`.

## Scope

In: the string literals of `tests/`, `scripts/`, `release/` and `.github/workflows/` (and
`src/`, read and found clean); the check, its scanner, its unit rows, its allowance. Out: the
judge's allowance files (Decision 4: the reserved closer after 0.1.0); comments and docstrings
(109's and 107's checks, unchanged); the guest's own sources' comments (109's `GUEST_INPUT`
rows, unchanged; their strings hold no citation); a bare `Decision N` or `criterion N` with no
specification beside it (Decision 2; `test_history.py`'s three `criterion N OPS` prints and one
comment in a held program keep theirs); `context/`, `CHANGELOG.md` and the roadmap (the lane's).

## Acceptance criteria

1. **Seen failing first:** on the base content, with the check, its scanner, its unit rows and
   its allowance in place and nothing else changed, the check fails with one line per kind A, B
   and C hit (75 by the draft's prototype; the built scanner's count recorded in
   `build/112/seen-failing.txt`), and every allowance row is used.
2. **Measured on the base it builds on:** the population table is re-run by the built scanner
   on the build's base (main, or wave 10's tip if it landed) and the landing notes give the
   counts by kind and file; any hit not in the table is reworded or answered in writing.
3. **Passes on the built commit**, with `STRING_CITATION_ALLOWED` holding only the fourteen rows
   of Decision 5, every one used, and 109's and 107's checks still green.
4. **The unit rows** (thirteen) pass; `tests/unit/test_scan.py` passes whole.
5. **Strings only:** for every Python file changed but the check's own and the scanner's, the
   `ast` dump with every string constant blanked is the same before and after; for the other
   files, the lines that change are the eight step names, the one `echo` and nothing else
   (`build/112/same-code.py`, prints nothing).
6. **No protected file changes:** `git diff --stat <base> -- tests/known_gaps.toml
   'tests/upstream/*.toml' tests/upstream/expected tests/upstream/python context/progress src
   tests/jobs tests/upstream/drive.py tests/upstream/regrtest_drive.py
   tests/upstream/package_drive.py` is empty.
7. **Every kind B test still matches its message:** each test of Decision 7's table passes by
   node id, and the landing notes show each message's old and new text.
8. **Rule (b) traced:** the landing notes list every string written under rule (b) with the
   document it stood on.
9. **The artifact set:** the builder's release workflow run on the built commit builds a set
   whose `python.wasm`, snapshot and stdlib zip have the SHA-256 of main's last dry run on the
   base, and whose `MANIFEST` differs from it only in the `recipe` lines of
   `scripts/gen_inittab.py` and `scripts/refuse-python`; every red line of the run is G7 or one
   the landing notes explain; the run id is in the landing notes.
10. **The fast tier** on the built commit fails exactly the baseline's nodes, and `sameness.py`
    against the base's record prints nothing outside this specification's claims.
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
  units = 13
  ```

  112: **retired checks:** none. **Lost passes:** none. **Rows that grow:** none (no fuel row:
  no check that records fuel changes a string; no bytes row: `MANIFEST` keeps its size). **The
  judge hash changes** in `tests/harness/scan.py`, `tests/checks/test_rules.py`,
  `tests/unit/test_scan.py` and every file under `tests/` whose strings changed.
- **The flags** (paste-safe; no `--accept-growth`):

  ```
  --accept "112: string literals outside src/ (the judge's messages, help and titles, check failure messages, the build's refusal, the release workflow's step names, the generated inittab comment, and the programs checks hold) give their reasons in words; the tests that match a message follow it exactly; no verdict, golden, allowance file or guest-run source changed; MANIFEST's recipe lines for gen_inittab.py and refuse-python move, python.wasm, the snapshot and the zip do not"
  --accept-judge "112: a rules check that no string literal under tests/, scripts/, release/, .github/workflows/ or src/ cites a project document (109's forms less paths and bare finding labels, a named finding of any letter), read through ast for Python and through non-comment lines elsewhere, docstrings, re patterns and allowance tuples skipped; the judge's allowance files left to their own closer; an allowance of fourteen rows (rule names 2, scanner fixtures 9, gap closers 3), each with its reason, a stale row failing; thirteen unit rows; ten tests' copies of reworded messages updated exactly"
  ```

- **CHANGELOG line proposed** (the lane's file), under the one unreleased section: *Strings
  speak for themselves (spec 112). The judge's messages, help texts and titles, the build's
  refusal, the release workflow's step names and the comment in the generated inittab source
  give their reasons in words, with no specification number, review or constitution section; a
  rules check over string literals holds it, with a rule's own name, a scanner's fixture and a
  gap's closer named as the exceptions. No behaviour, fuel or binary byte changes; `MANIFEST`'s
  recipe hashes of two `scripts/` files move.*
- **Roadmap:** the "Reserved: 112" line becomes this specification; the closer below it keeps
  the judge's allowance files (their comments and, by Decision 4, their strings) and the guest's
  own sources' comments.

## One line

Every string a person reads now says why in words, and a check over string literals keeps
document numbers out of them, with a rule's name, a fixture and a gap's closer as the named
exceptions.

## Landing notes

Not built yet. The measurement scripts the counts above come from are in the drafting worktree,
git-ignored: `build/112/measure.py` (109's eight forms over every string: 263 in scope, 450 in
all), `build/112/measure2.py` (the reading of Decisions 2 to 4: 92 in scope, 108 in the judge's
allowance files, 0 in the guest's sources, 0 under `src/`), their outputs `hits-before.tsv` and
`hits-proposed.tsv`, and `lines.py`, which prints each hit with its source line.
