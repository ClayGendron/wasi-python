# 108 — Code speaks for itself: no document cited in a comment outside `src/`

- **Status:** **drafted 2026-10-20**; built on (the landing notes name the commit); reviewed
  before build: none required (judge-only and comments-only; AGENTS.md rule 8), the build review
  follows.
- **Date:** 2026-10-20
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe by effect, build-class by the letter** (§5.7): comments in `scripts/`
  and in `.github/workflows/release.yml` change, so the files are build-class, and no code,
  string literal, artifact byte or recipe step changes. `MANIFEST` records every tracked file
  under `scripts/` by hash, so the next build's `MANIFEST` differs in those `recipe` lines and
  in nothing else. **A judge change** (a rules check, its scanner, its unit rows, and comments
  across `tests/`): the lane accepts it with `--accept-judge`. Files: `AGENTS.md` (one
  parenthesis), `tests/harness/scan.py`, `tests/checks/test_rules.py`, `tests/unit/test_scan.py`,
  the comments and docstrings of the files the landing notes count under `tests/`, `scripts/`,
  `release/` and `.github/workflows/`, this specification.
- **Depends on:** nothing landed beyond main. It **lands last in the stacked chain 102 to 107**
  (the memo of Research, section 8): it is built on `b7a1250` and re-applied on the chain's tip
  before the wave (Decision 7), since every link edits comments in `tests/`. Spec 106's
  Decision 4 does the same job for `src/`; this specification covers `tests/`, `scripts/`,
  `release/` and the workflows only, and touches no file under `src/`.
- **Research it stands on:** `../research/2026-10-20-a-design-review-of-the-runner.md`,
  section 8, its last paragraph: the owner's rule "code speaks for itself" (2026-10-20) and the
  counts it gives (1,143 under `tests/`, 213 under `scripts/`, 4 under `release/`, by a `grep`
  of `spec NNN` over every line). Its own measurements below, each labelled, on `b7a1250`.

## The problem

A comment that says `(spec 052, Decision 7)` tells a reader where a reason was once written and
not what it is. The reader must leave the file, find the document, and hope the decision was not
amended since. The owner's rule (AGENTS.md, "Code speaks for itself"): a code file names no
specification, memo, review, finding ID or `context/` path; the reason is written in words; a
document under `context/` may cite and link the code, so the trace runs from the documents to the
code and never back.

Measured on `b7a1250` (EXECUTED, `uv run python build/108/measure.py`, the scanner of Decision 2
over the files of Decision 3, comments and docstrings only): **1,785 citations** — `tests/`
1,488, `scripts/` 243, `release/` 6, `.github/workflows/` 48. By kind: a specification's number
1,401, a finding identifier 309, a named finding of another letter 20, a `context/` path 22, the
constitution's section sign 13, the word for a research write-up 13, a numbered question 5, a
review followed by a path 2. The memo's `grep` counts every line, string literals included, so
its numbers differ; this specification counts what the rule reads.

## Decisions

### 1. The rule reads comments and docstrings; the judge reads `context/` as data

The rule is about what a reader is told, so it reads prose only: a Python file's comments and
docstrings, and the `#` comments of every other file. Code that reads a document as data (the
rules checks reading `context/specifications/`, the progress harness writing `context/progress/`,
the release's reads) is not a citation and stays. AGENTS.md's bullet gains one parenthesis, "(in
comments and docstrings; the judge reads `context/` as data)", so that it cannot be read as
forbidding those paths in code.

### 2. The check refuses eight forms

`tests/harness/scan.py` gains `context_citation_hits(path)`, which returns `(line, rule, phrase)`
for each match in a file's prose, and `context_citation_files(root)`, the files of Decision 3.
The forms, each a rule name and a regular expression:

| rule | refuses |
|---|---|
| `specification` | `\bspec(?:ification)?s?\s+\d{3}\b`, any case |
| `constitution` | `\bconstitution\s*§`, any case |
| `memo` | `\bmemo\b`, any case |
| `review` | `\breviews?\b` followed by a date `YYYY-MM-DD` or a path (a word then `/`) |
| `question` | `\bquestion\s+\d+\b`, any case |
| `context path` | `\bcontext/[a-z_]+` |
| `finding` | `(?<![A-Za-z0-9_])[CDFLNS]\d{1,2}(?:\.\d+)?(?![A-Za-z0-9_])`, spec 106's |
| `named finding` | a finding of another letter (`M5`, `B1`, `R1`, `P6`, a mutation's `M18`) where `review`, `re-review` or `confirmation` names it |

The last row widens the brief by one form: the High, Medium and other letters are left out of the
bare `finding` row because alone they are also a milestone's or a chip's name (`M2`, `M1`), and
20 such identifiers under `tests/` are a review's (EXECUTED, the scanner's `named finding` rule
on `b7a1250`; `build/108/hits-before.txt` names them). Python prose is read through `tokenize` (comment tokens) and
`ast` (the string token that opens a module, a class or a function); no other string is prose.
Other files: a line whose first non-blank character is `#`, and the part of a line after a ` # `.

The check, `tests/checks/test_rules.py::test_code_outside_src_names_no_context_document`, reports
each hit as `path:line: rule: phrase`.

### 3. The files it reads

Every `.py`, `.sh`, `.toml`, `.yml` and `.yaml` file under `tests/` and `.github/workflows/`, and
every text file under `scripts/` and `release/` (the shell launchers there have no suffix; the
release's `.in` and `.txt` files are read as `#` comments). The workflow is included because its
comments cite specifications 48 times (EXECUTED); `src/` is spec 106's and is not read here.
Fixtures under `tests/fixtures/` with other suffixes (`.ll`, `.expected`, `.txt`) and the upstream
suites' `.ini` files are not code and are not read.

### 4. Three rewriting rules, spec 106's

- **(a)** Delete only the citation and its connector: `(spec 052)`, `, spec 052,`, `per spec
  052`, `the review's F4.2`, `Spec 055, criterion 26: ` at a sentence's head (the next word then
  takes the capital the citation had). The sentence stays.
- **(b)** Where the citation was the whole explanation, write the reason in words, drawn from
  the document it cited, which the builder reads. The landing notes list every such sentence
  with the document it stood on, so the trace moves into this specification.
- **(c)** Delete no sentence. Change no code, string literal, identifier, marker, golden, expected
  file, `tests/known_gaps.toml`, `tests/upstream/*.toml` or `context/progress/`. A string literal
  that cites a document (an assertion message, a message the runner or the judge emits and a test
  matches, a guest program held as a string, a generated file's text) is listed in the landing
  notes for spec 106 or its owner, not changed.

### 5. One allowance tuple, for the judge's own allowance files

`CONTEXT_CITATION_ALLOWED` in `tests/checks/test_rules.py` holds `(path, phrase, reason)`
entries; an entry admits that exact phrase in that file's prose. An entry that admits nothing
fails the check, so the tuple only shrinks. Its entries are exactly the citations in the comments
of `tests/known_gaps.toml` and `tests/upstream/*.toml` (26 entries, 27 hits on `b7a1250`,
EXECUTED): rule (c) and AGENTS.md rule 4 make those files' edits a judge change of their own, so
a comment cleanup does not touch them, and they are cleared when such a change next edits them.
No other entry is added; a reviewer reads any addition.

### 6. String literals stay

Rule (c) keeps every string literal. The literals that cite a document fall in four kinds, which
the landing notes list by file and line: guest programs held as strings (their bytes are the
guest's input, and so its fuel), messages the judge or a build step prints and a check matches,
a generated C comment (`scripts/gen_inittab.py`), and fixtures that a scanner's unit rows read
(their text is the scanner's input). The first two are spec 106's or the owner's to reword with
the code that matches them.

### 7. A reproducible pass: a script, then a read

The mechanical cases are rewritten by a scratch script, `build/108/clean.py` (git-ignored, run
with `uv run python`), which edits only prose spans (the same reading as the check) one line at a
time, by rule (a) alone: a parenthesis that holds only citations, a citation at the head of a
parenthesis or a sentence, a citation after a `;` or `,` that closes a parenthesis, and `per
<citation>`. It never edits the files of rule (c), never leaves a comment empty, and prints each
line it changes. Everything it leaves is read by hand, line by line, under rules (a) and (b); the
landing notes give the hand-pass count and the rule (b) list. Re-applied on the chain's tip, the
commits of this specification's cleanup are dropped, the script is run on the new base, and the
leftovers are read again; the check and its unit rows are re-applied as they are.

### 8. Guest-run sources lose comment bytes, and the fuel stays within the ratchet

`tests/jobs/*.py` and the upstream suites' drivers run inside the guest, so a shorter docstring
is fewer bytes for the guest to parse. The guest's fuel falls by the parse work of the deleted
bytes; the ratchet's tolerance is 1e-4 of a check's fuel. The smallest guest-job fuel in the
accepted record is `test_regex_features_job_matches_native[snapshot]`, 415,030,887 (EXECUTED,
`context/progress/accepted.json`, darwin-arm64), so its tolerance is 41,503 instructions. That
job is run by node id before and after the cleanup, and the landing notes give both numbers.

### 9. No verdict moves

The fast tier runs on the built commit with the frozen `v0.1.0a7` set, and `sameness.py` compares
its record with spec 102's built record (the chain's previous record on this base). The only
differences allowed are this specification's claims: the new check's node and the scanner's unit
rows.

## Intent

Every comment and docstring under `tests/`, `scripts/`, `release/` and the workflows gives its
reason in words. A rules check holds it, beside spec 106's for `src/`, and the only citations left
are in the judge's own allowance files, named one by one.

## Design

- **The scanner:** `CITATION_RULES` (Decision 2's table), `CITATION_SUFFIXES`,
  `_python_prose(text)`, `_hash_comments(text)`, `context_citation_hits(path)`,
  `context_citation_files(root)`, at the end of `tests/harness/scan.py`.
- **The check:** `test_code_outside_src_names_no_context_document` and `CONTEXT_CITATION_ALLOWED`
  in `tests/checks/test_rules.py`, after the specifications' shape checks.
- **The unit rows** (`tests/unit/test_scan.py`): one parametrized row per form (eleven cases:
  two for `specification`, two for `review`, two for `finding`, one for each other form), each
  seen in a Python comment, a Python docstring, a shell comment line and a shell trailing
  comment; one negative row (a `context/` path and a citing literal in code, a `noqa` code and
  words with digits in a comment, a citing string in a shell command, and a file that does not
  parse give no hit); one row for the files read. Their fixtures are assembled from parts, so the
  unit file's own prose is never a hit.
- **The cleanup:** `build/108/clean.py`, then the hand pass, in one commit of comments only.

## Scope

In: the comments and docstrings of `tests/`, `scripts/`, `release/` and `.github/workflows/`;
the check, its scanner, its unit rows; the AGENTS.md parenthesis. Out: `src/` (spec 106),
`recipes/` (other projects' shapes and the guest package, no rule yet), `pyproject.toml`'s
comments, `context/`, every string literal (Decision 6), the judge's allowance files
(Decision 5), `CHANGELOG.md` and the roadmap (the line is proposed in the landing notes).

## Acceptance criteria

1. **Seen failing first:** the check fails on `b7a1250` with the check, its scanner and its
   allowance in place and nothing else changed; the count is kept in `build/108/seen-failing.txt`.
2. **Passes on the built commit**, with `CONTEXT_CITATION_ALLOWED` holding only the entries of
   Decision 5, every one used.
3. **Counts before and after** by tree, from the same scanner, in `build/108/hits-before.txt` and
   `build/108/hits-after.txt`, sorted by file and rule; after: 27, all in the allowance files.
4. **The unit rows** (thirteen) pass; `tests/unit/test_scan.py` passes whole.
5. **Comments only:** for every file the cleanup commit changes, the Python token stream with
   comments removed and docstrings blanked is the same before and after, and for every other
   file the lines that are not `#` comments are the same (a script, `build/108/same-code.py`,
   EXECUTED, prints nothing).
6. **No file of rule (c) changes:** `git diff --stat b7a1250 -- tests/known_gaps.toml
   tests/upstream context/progress src` is empty.
7. **Rule (b) traced:** the landing notes list every sentence written under rule (b) with the
   document it stood on.
8. **The literals reported:** the landing notes list the citing string literals by file and line.
9. **Fuel:** the regex job's two fuel numbers before and after differ by less than the ratchet's
   tolerance (Decision 8).
10. **The fast tier** on the built commit fails exactly the baseline's 83 nodes, and `sameness.py`
    against spec 102's built record prints nothing outside this specification's claims.
11. **Ruff:** `ruff check` and `ruff format --check` are green on `src/` and `tests/`.
12. **AGENTS.md** carries the parenthesis of Decision 1 and no other change.

## For the lane

- **Kind:** parallel-safe by effect, build-class by the letter; a judge change. The chain's last
  entry: re-applied on the chain's tip before the wave (Decision 7).
- **The dispatch:** none of its own; the chain's one dispatch on its final tip.
- **The claim list** and **the flags**: the landing notes, as the build ran them.

## One line

Every comment outside `src/` now says why in words, and a check keeps document numbers out of
code prose, the judge's own allowance files named as the one exception.

## Landing notes

Written at the build.
